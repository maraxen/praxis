"""Deck construction for the P2.2 verify harness.

Wraps DeckFactory.create_setup from
praxis/backend/core/simulation/chatterbox_runner.py (loaded standalone,
SQLAlchemy-free -- see verifier.py) with:

* a declarative, serializable DeckLayout (resources by name + seeded well
  volumes + optional parking holders for gripper/move examples),
* layout INFERENCE from a call sequence (tiny decks by default: one tip rack
  plus exactly the resources the calls reference),
* state snapshotting used by the post-condition checks.

DeckFactory always builds the Hamilton carrier deck (TIP_CAR at rails=1,
PLT_CAR at rails=9) and names resources after their param entries; this
module keeps that behavior and only EXTENDS the returned setup.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import warnings
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from pylabrobot.resources import ResourceHolder

from coxswain.plr.param_namespace import (
    RESOURCE_TYPE_CONTAINER,
    RESOURCE_TYPE_PLATE,
    RESOURCE_TYPE_TIP_SPOT,
    ParamKind,
    params_of,
)

__all__ = [
    "DeckLayout",
    "SetupHandle",
    "build_setup",
    "infer_layout",
    "load_chatterbox_runner",
]

#: Resource type vocabulary accepted in DeckLayout.resources. Values mirror
#: chatterbox_runner's _DECK_PLACEABLE_TYPES.
RESOURCE_TYPES = ("Plate", "TipRack", "Trough", "TubeRack", "Container")

#: Rails used for harness-added parking holders (plate carrier spans ~rails
#: 9-12; tip carrier 1-2; troughs go to rails=21; keep clear of those).
_PARK_RAILS = (5, 7, 13, 15, 17, 23)

_RUNNER_PATH = (
    Path(__file__).resolve().parents[2]
    / "praxis" / "backend" / "core" / "simulation" / "chatterbox_runner.py"
)


def load_chatterbox_runner():
    """Load chatterbox_runner.py standalone by file path.

    Deliberately NOT ``import praxis.backend.core.simulation``: that package's
    __init__ pulls method_contracts/pipeline/simulator and, transitively, the
    SQLAlchemy stack.  The runner module itself is SQLAlchemy-free (verified);
    loading it by path keeps the harness import-light and honors the
    never-modify-praxis/backend constraint (we only read it).
    """
    name = "_p22_chatterbox_runner"
    if name in sys.modules:
        return sys.modules[name]
    if not _RUNNER_PATH.is_file():
        raise ImportError(
            f"chatterbox runner not found at {_RUNNER_PATH} (repo layout change?)"
        )
    spec = importlib.util.spec_from_file_location(name, _RUNNER_PATH)
    if spec is None or spec.loader is None:  # pragma: no cover - packaging bug
        raise ImportError(f"cannot load {_RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # required before exec for dataclass resolution
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name, None)  # don't cache a broken half-module
        raise
    return module


@dataclass
class DeckLayout:
    """Declarative tiny-deck description for one verification."""

    #: name -> resource kind ("Plate", "Trough", ...). The FIRST "TipRack"
    #: entry aliases the factory-built default rack named "tip_rack"; any
    #: further "TipRack" entries get their own physically distinct rack
    #: (#4952 -- they used to all alias the single factory rack regardless
    #: of key, which lost every name but the first).
    resources: dict[str, str] = field(default_factory=dict)
    #: "<name>.<well>" -> initial uL seeded via tracker.set_volume().
    seed_volumes: dict[str, float] = field(default_factory=dict)
    #: Extra empty ResourceHolders placed directly on the deck (move/plate
    #: parking destinations), addressable by bare name in refs.
    holders: list[str] = field(default_factory=list)

    def merged(self, other: "DeckLayout | None") -> "DeckLayout":
        if other is None:
            return self
        return DeckLayout(
            resources={**self.resources, **other.resources},
            seed_volumes={**self.seed_volumes, **other.seed_volumes},
            holders=[*self.holders, *other.holders],
        )


@dataclass
class SetupHandle:
    """Everything the dispatcher and checks need about one built deck."""

    machine: Any  # LiquidHandler
    deck: Any
    backend_name: str
    #: param/resource name -> PLR object (plates, tip_rack, holders, ...)
    resources: dict[str, Any] = field(default_factory=dict)
    runner_module: Any = None

    def mounted_tip_count(self) -> int:
        return sum(1 for t in self.machine.get_mounted_tips() if t is not None)

    def iter_tracked(self):
        """Yield every object carrying a VolumeTracker (wells, tip spots,
        containers) in stable deck order."""
        stack = [self.deck]
        while stack:
            node = stack.pop()
            tracker = getattr(node, "tracker", None)
            if tracker is not None and hasattr(tracker, "get_free_volume"):
                yield node
            stack.extend(getattr(node, "children", []))

    def well_index(self) -> dict[str, Any]:
        return {
            obj.name: obj
            for obj in self.iter_tracked()
            if getattr(obj, "name", None)
        }

    def snapshot(self) -> dict[str, Any]:
        """Full observable state: per-resource tracker state + topology +
        free-volume readings per tracked object (AC-2.2.2 measurement)."""
        return {
            "backend": self.backend_name,
            "mounted_tips": self.mounted_tip_count(),
            "resources": self.deck.serialize_all_state(),
            "topology": self.deck.serialize(),
            "free_volume": {
                obj.name: float(obj.tracker.get_free_volume())
                for obj in self.iter_tracked()
                if getattr(obj, "name", None)
            },
        }

    def free_volume(self, obj: Any) -> float:
        """Free volume of a well/container per AC-2.2.2 measurement rule."""
        return float(obj.tracker.get_free_volume())


def _prefix_classification(name: str) -> tuple[str, str]:
    """The ORIGINAL (pre-#4950) name-prefix rule, kept as the fallback for
    names with no usable usage evidence and as the recorded behaviour for a
    tip/container conflict (see :func:`infer_layout`).  Returns (layout_key,
    kind); the key is always "tip_rack" for TipRack entries produced HERE
    (the prefix rule never had a way to tell two "tip*"-prefixed names
    apart, so it keeps collapsing them onto the single factory-built rack
    -- unlike the usage-based branch in :func:`infer_layout`, which #4952
    fixed to keep each tip-typed base's own name).
    """
    if name in ("tip_rack",) or name.startswith("tip"):
        return "tip_rack", "TipRack"
    if name.endswith("trough"):
        return name, "Trough"
    return name, "Plate"


def _collect_usage(calls: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, bool]]:
    """Classify each referenced base name by how it is USED across the call
    sequence, keyed off the canonical param_namespace table (THE mapping
    dispatcher.py already drives dispatch from -- see its module docstring),
    not name-string guessing:

    * a ref bound to a SYMBOLIC_RESOURCE_REF param whose resource_type is
      "tip_spot" (pick_up_tips.at, drop_tips.destination, discard_tips.at,
      and any future tool sharing that resource_type) -> tip usage.
    * a ref bound to resource_type "container" (aspirate.source,
      dispense.destination, transfer.source/destination) -> container usage,
      further split on whether THIS occurrence carried a "<name>.<tail>"
      well address ("container_dotted") or named the base resource bare
      ("container_bare") -- a bare container ref needs a resource that
      itself carries a volume tracker (PLR's ``Plate`` does not; only its
      wells do), which is exactly the AttributeError('Plate' object has no
      attribute 'tracker') failure class this fix targets.
    * a ref bound to resource_type "plate" (stamp.source/destination) always
      counts as "container_dotted" regardless of literal dot -- stamp needs
      an actual multi-well Plate, never a Trough, so it must never earn the
      bare-container Trough treatment.
    * resource_type "resource"/"lid" (move_resource/move_plate/move_lid) is
      NOT classified here -- those go through the caller's own
      DeckLayout.holders/exclude mechanism (T16d, #4879) before infer_layout
      ever sees them; leave to the prefix-rule fallback if they do.
    """
    usage: dict[str, dict[str, bool]] = {}

    def mark(name: str, *, tip: bool = False, dotted: bool = False, bare: bool = False) -> None:
        slot = usage.setdefault(
            name, {"tip": False, "container_dotted": False, "container_bare": False}
        )
        if tip:
            slot["tip"] = True
        if dotted:
            slot["container_dotted"] = True
        if bare:
            slot["container_bare"] = True

    for call in calls:
        tool = (call or {}).get("name")
        if not isinstance(tool, str):
            continue
        try:
            specs = params_of(tool)
        except KeyError:
            continue  # not a phase-2 canonical tool; no usage evidence available
        params = (call or {}).get("params") or {}
        for spec in specs:
            if spec.kind is not ParamKind.SYMBOLIC_RESOURCE_REF:
                continue
            if spec.resource_type == RESOURCE_TYPE_TIP_SPOT:
                role = "tip"
            elif spec.resource_type == RESOURCE_TYPE_CONTAINER:
                role = "container"
            elif spec.resource_type == RESOURCE_TYPE_PLATE:
                role = "plate"
            else:
                continue
            value = params.get(spec.name)
            if value is None:
                continue
            for name, dotted in _refs_with_tail_flag(value):
                if role == "tip":
                    mark(name, tip=True)
                elif role == "plate":
                    mark(name, dotted=True)
                elif dotted:
                    mark(name, dotted=True)
                else:
                    mark(name, bare=True)
    return usage


def infer_layout(calls: Sequence[Mapping[str, Any]],
                 exclude: set[str] | None = None) -> DeckLayout:
    """Derive a minimal DeckLayout from a call sequence.

    Type is inferred from USAGE first (#4950): a name referenced as a
    pick_up_tips/drop_tips/discard_tips tip-spot target becomes TipRack,
    UNDER ITS OWN NAME (#4952 -- these used to all collapse onto a single
    "tip_rack" key, so every base but one lost its name and grounding a
    call that referenced it by name raised GroundingError; build_setup now
    gives every tip-typed base its own physically distinct rack, aliasing
    only the first onto the factory default); a name referenced (bare, no
    well address) as an aspirate/dispense/transfer container becomes Trough
    (needs its own tracker); a name referenced with a well address stays a
    Plate. A name used BOTH as a tip target and a container/well target is a
    conflict -- today's name-prefix rule is kept verbatim for it (a
    UserWarning records why) rather than guessing, so IT still collapses
    onto "tip_rack" when prefix-classified as one. Names with no usage
    evidence (unknown tools, resource_type "resource"/"lid" refs already
    owned by an explicit DeckLayout.holders, or refs outside a known tool's
    canonical param table) fall back to the same prefix rule.

    Names in ``exclude`` (typically explicit-layout resources/holders) are
    skipped so an explicit DeckLayout fully owns them.
    """
    resources: dict[str, str] = {}
    skip = exclude or set()
    usage = _collect_usage(calls)
    for call in calls:
        for value in (call or {}).get("params", {}).values():
            for name in _names_in(value):
                if name in skip:
                    continue
                info = usage.get(name)
                is_container = info is not None and (
                    info["container_dotted"] or info["container_bare"]
                )
                if info is not None and info["tip"] and is_container:
                    warnings.warn(
                        f"infer_layout: {name!r} is used both as a tip-spot "
                        "target and as an aspirate/dispense/transfer "
                        "container/well in this call sequence -- keeping "
                        "today's name-prefix classification for it rather "
                        "than guessing.",
                        stacklevel=2,
                    )
                    key, kind = _prefix_classification(name)
                    resources.setdefault(key, kind)
                elif info is not None and info["tip"]:
                    # #4952: keep the base's OWN name (build_setup gives it
                    # a physically distinct rack) instead of collapsing
                    # every tip-typed base onto a single "tip_rack" key.
                    resources.setdefault(name, "TipRack")
                elif info is not None and info["container_bare"] and not info["container_dotted"]:
                    resources.setdefault(name, "Trough")
                else:
                    key, kind = _prefix_classification(name)
                    resources.setdefault(key, kind)
    return DeckLayout(resources=resources)


def _names_in(value: Any) -> list[str]:
    """Collect base resource names out of ref strings/lists/dicts."""
    names: list[str] = []
    if isinstance(value, str):
        names.append(_base_name(value))
    elif isinstance(value, Mapping):
        # structured Coordinate payload {"x":..} etc. carries no resource ref
        if set(("x", "y", "z")) & set(value.keys()):
            return []
        for v in value.values():
            names.extend(_names_in(v))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for v in value:
            names.extend(_names_in(v))
    return [n for n in names if n]


def _refs_with_tail_flag(value: Any) -> list[tuple[str, bool]]:
    """Like :func:`_names_in`, but also reports whether EACH occurrence
    carried a "<name>.<tail>" well/spot address (vs. naming the base
    resource bare) -- the signal :func:`_collect_usage` needs to tell a
    dotted well-on-a-Plate ref from a bare whole-container ref.
    """
    out: list[tuple[str, bool]] = []
    if isinstance(value, str):
        base = _base_name(value)
        if base:
            out.append((base, _has_tail(value)))
    elif isinstance(value, Mapping):
        if set(("x", "y", "z")) & set(value.keys()):
            return []
        for v in value.values():
            out.extend(_refs_with_tail_flag(v))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for v in value:
            out.extend(_refs_with_tail_flag(v))
    return out


def _base_name(ref: str) -> str:
    head = ref.split(".", 1)[0]
    return head.split("[", 1)[0].strip()


def _has_tail(ref: str) -> bool:
    """True iff ``ref`` addresses a sub-position ("<name>.<tail>") rather
    than naming its base resource bare."""
    head = ref.split("[", 1)[0]
    return "." in head


def build_setup(
    backend_name: str,
    layout: DeckLayout,
) -> SetupHandle:
    """Build machine + deck via DeckFactory.create_setup, then extend.

    Extension covers what the shared factory deliberately does not know
    about: a physically distinct rack per tip-typed base beyond the
    factory default, Trough placement on a free rail instead of the
    factory's single hardcoded rails=21 (#4952 -- both left over from
    #4950), named parking holders, and seeded starting volumes.
    """
    runner = load_chatterbox_runner()

    # TipRack and Trough entries are placed by THIS function (below), not
    # DeckFactory.create_setup:
    #  * TipRack -- every tip-typed base needs its OWN named rack (#4952:
    #    they used to all alias the single factory-built "tip_rack",
    #    losing every other base's name and turning any later reference to
    #    it into a GroundingError).
    #  * Trough -- the factory always places a Trough at the same
    #    hardcoded rails=21, which collides the moment a call sequence
    #    names more than one bare container.
    # Everything else still goes through create_setup's `needs` path
    # unchanged.
    needs: dict[str, str] = {}
    tip_names: list[str] = []
    trough_names: list[str] = []
    for res_name, kind in layout.resources.items():
        if kind == "TipRack":
            tip_names.append(res_name)
        elif kind == "Trough":
            trough_names.append(res_name)
        else:
            needs[res_name] = kind

    setup = runner.DeckFactory().create_setup(backend_name, needs)

    handle = SetupHandle(
        machine=setup["machine"],
        deck=setup["deck"],
        backend_name=backend_name,
        runner_module=runner,
    )
    deck = handle.deck

    # Factory always builds exactly one physical rack, named "tip_rack" --
    # pipetting calls need SOME rack even when infer_layout found no tip
    # usage at all. Keep "tip_rack" available as a key regardless of
    # whether any tip-typed base happened to be named that.
    handle.resources["tip_rack"] = setup["tip_rack"]

    # Shared free-rail scan for everything build_setup places directly
    # (extra tip racks, troughs, parking holders): rails 1-2 (tip carrier)
    # and ~9-13 (plate carrier) are already taken by DeckFactory. Walk
    # candidates forward and let a ValueError (occupied / doesn't fit)
    # skip to the next one.
    candidates = [r for r in range(1, 28)]
    used_rail = 0

    def _place_on_free_rail(resource: Any, label: str) -> None:
        nonlocal used_rail
        placed = False
        last_err: Exception | None = None
        for rails in candidates[used_rail:]:
            try:
                deck.assign_child_resource(resource, rails=rails)
                used_rail = candidates.index(rails) + 1
                placed = True
                break
            except ValueError as e:  # occupied / doesn't fit -> next candidate
                last_err = e
        if not placed:
            raise RuntimeError(f"no free rails for {label}: {last_err}")

    for i, res_name in enumerate(tip_names):
        if i == 0:
            # First tip-typed base aliases the factory-built rack -- keeps
            # existing callers / frozen P2.x behaviour unchanged for the
            # common single-rack case.
            handle.resources[res_name] = setup["tip_rack"]
            continue
        if deck.has_resource(res_name):
            # e.g. "trash": STARLetDeck already places a built-in Trash
            # resource under this exact name (with_trash=True default).
            # Vendored drop_tips() accepts a Trash directly (param_namespace
            # drop_tips.destination: Sequence[Union[TipSpot, Trash]]), so
            # reuse the deck's own resource instead of trying to place a
            # second, duplicate-named one (which raises
            # "Resource with name 'trash' already defined.").
            handle.resources[res_name] = deck.get_resource(res_name)
            continue
        rack = runner.resolve_resource(res_name, "TipRack")
        _place_on_free_rail(rack, f"tip rack {res_name!r}")
        handle.resources[res_name] = rack

    for res_name in trough_names:
        if deck.has_resource(res_name):
            handle.resources[res_name] = deck.get_resource(res_name)
            continue
        trough = runner.resolve_resource(res_name, "Trough")
        _place_on_free_rail(trough, f"trough {res_name!r}")
        handle.resources[res_name] = trough

    for res_name in needs:
        handle.resources[res_name] = setup[res_name]

    # Parking holders for move-verb destinations, on the SAME free-rail
    # scan so they never collide with the extra tip racks/troughs above.
    for holder_name in layout.holders:
        holder = ResourceHolder(
            name=holder_name, size_x=127.76, size_y=85.48, size_z=14.5
        )
        _place_on_free_rail(holder, f"parking holder {holder_name!r}")
        handle.resources[holder_name] = holder

    # Seed volumes AFTER all assignment (trackers exist from construction).
    for ref, volume_ul in layout.seed_volumes.items():
        wells = ground_ref(ref, handle)
        for well in wells:
            well.tracker.set_volume(float(volume_ul))

    return handle


# Imported late to avoid a circular import (grounding needs SetupHandle-typed
# objects only duck-typed, but build_setup seeds volumes through grounding).
from verify.grounding import ground_ref  # noqa: E402
