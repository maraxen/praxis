"""Canonical parameter namespace for the phase-2 copilot surface (P2.0).

THE contract consumed downstream by:

- P2.3/P2.4 coverage-floor + overlay generators (schema-side call shapes),
- the P2.5 training corpus (param vocabulary in FunctionGemma JSONL),
- the D11 deterministic derivation of ``missing_required`` /
  ``unresolved_slots`` (``coxswain.plr.slot_derivation``),
- future dispatch (schema param name -> vendored PLR kwarg).

Fixes C-B2: the fixtures' normalized vocabulary (``source``/``volume_ul``/
``destination``/``wavelength_nm``/``at``/``what``) is now a committed mapping
onto real vendored kwargs instead of an undocumented convention.

NFR-1/NFR-2: pure stdlib data, CPython-importable, no ``js``, no ``praxis.*``.

Ground truth: ``inspect.signature`` against ``external/pylabrobot`` at
submodule HEAD ``dd79c4c89bc008629a1c598ea614be5e6067d1f9`` (PLR 0.2.2),
verified 260825; enforced continuously by
``coxswain/tests/test_tool_schema_parity.py`` which pins that SHA.

Scope policy: this table covers the COPILOT-emittable params only. Expert
kwargs present on vendored signatures (flow rates, offsets, liquid heights,
spread/mix lists, grip directions, ``use_channels``) are OUT of the phase-2
generation surface; dispatch passes vendor defaults for them. Every REQUIRED
vendored kwarg of every included tool IS covered (parity-tested), so the
dispatcher can never be asked to invent an argument.

Recorded decisions baked into rows below:
- ``read_*.at`` holds well POSITIONS relative to the plate already loaded in
  the reader -- index-like, not deck-object references -- hence LITERAL even
  though it is string-valued. The table decides kind; stringiness does not.
- ``transfer.volume_ul`` maps to ``target_vols``: user-stated volumes express
  dispense targets (corpus-B style, e.g. ``simple_transfer.py`` uses
  ``vols=[volume_ul]`` on dispense); the dispatcher wraps a scalar to ``[v]``.
- ``discard_tips.at`` is kept SYMBOLIC (cue-2 grounds the referenced deck
  location) but has no PLR kwarg: the vendored ``discard_tips()`` discards
  mounted tips to the implicit trash. P2.9 hard-case fixtures pin semantics.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Final

from coxswain.plr.tool_schema import PHASE2_TOOL_NAMES

__all__ = [
    "PARAM_NAMESPACE",
    "ParamKind",
    "ParamSpec",
    "params_of",
    "required_params",
    "symbolic_slots",
]

#: Resource-type vocabulary for symbolic slots. Values align with the PLR
#: receiver-side types of the mapped kwarg (Container/Plate/TipSpot/Resource/
#: Lid); grounding resolves them against live kernel objects (FR-7).
RESOURCE_TYPE_CONTAINER = "container"
RESOURCE_TYPE_PLATE = "plate"
RESOURCE_TYPE_LID = "lid"
RESOURCE_TYPE_RESOURCE = "resource"
RESOURCE_TYPE_TIP_SPOT = "tip_spot"


class ParamKind(str, Enum):
    """How a param value is interpreted (D11 slot-classification rule input).

    LITERAL: usable as-is after canonicalization; never an unresolved slot,
    even when string-valued (positions, fixed noun keys, wavelengths).
    SYMBOLIC_RESOURCE_REF: a user-facing reference that must be grounded
    against live kernel objects before dispatch (cue 2 applies).
    """

    LITERAL = "literal"
    SYMBOLIC_RESOURCE_REF = "symbolic_resource_ref"


@dataclass(frozen=True)
class ParamSpec:
    """One row: schema-side name <-> vendored PLR kwarg."""

    #: Canonical schema-side (fixture-vocabulary) name.
    name: str
    #: Vendored kwarg name; None => phrase-only/dispatch-inert metadata.
    plr_arg: str | None
    #: PLR-side type expression, verbatim from the vendored annotation.
    plr_type: str
    #: Required per inspect.signature of the vendored method.
    required: bool
    #: Literal vs symbolic classification (the table decides, not values).
    kind: ParamKind
    #: Grounding resource type; required iff kind is SYMBOLIC_RESOURCE_REF.
    resource_type: str | None = None
    #: How the dispatcher wraps values: scalar passed through, list wrapped.
    cardinality: str = "scalar"
    note: str = ""

    def __post_init__(self) -> None:
        if self.kind is ParamKind.SYMBOLIC_RESOURCE_REF and not self.resource_type:
            raise ValueError(f"symbolic ParamSpec {self.name!r} needs resource_type")
        if self.kind is ParamKind.LITERAL and self.resource_type is not None:
            raise ValueError(f"literal ParamSpec {self.name!r} must not carry resource_type")


def _sym(
    name: str,
    plr_arg: str | None,
    plr_type: str,
    required: bool,
    resource_type: str,
    cardinality: str = "scalar",
    note: str = "",
) -> ParamSpec:
    return ParamSpec(
        name, plr_arg, plr_type, required, ParamKind.SYMBOLIC_RESOURCE_REF,
        resource_type=resource_type, cardinality=cardinality, note=note,
    )


def _lit(
    name: str,
    plr_arg: str | None,
    plr_type: str,
    required: bool,
    cardinality: str = "scalar",
    note: str = "",
) -> ParamSpec:
    return ParamSpec(
        name, plr_arg, plr_type, required, ParamKind.LITERAL,
        cardinality=cardinality, note=note,
    )


# ---------------------------------------------------------------------------
# THE TABLE -- one entry per phase-2-included tool (exactly PHASE2_TOOL_NAMES;
# both directions are parity-tested). Rows are in declaration order; the D11
# derivation reports missing_required in this order.
# ---------------------------------------------------------------------------
PARAM_NAMESPACE: Final[dict[str, tuple[ParamSpec, ...]]] = {
    # --- liquid_handler: pipetting ------------------------------------------
    "aspirate": (
        _sym("source", "resources", "Sequence[Container]", True, RESOURCE_TYPE_CONTAINER,
             note="fixture vocabulary 'source'; dispatcher wraps scalar container refs"),
        _lit("volume_ul", "vols", "List[float]", True, cardinality="list",
             note="dispatcher wraps scalar to [v]"),
    ),
    "dispense": (
        _sym("destination", "resources", "Sequence[Container]", True, RESOURCE_TYPE_CONTAINER,
             note="same vendored kwarg as aspirate; schema name follows utterance role"),
        _lit("volume_ul", "vols", "List[float]", True, cardinality="list"),
    ),
    "transfer": (
        _sym("source", "source", "Well", True, RESOURCE_TYPE_CONTAINER),
        _sym("destination", "targets", "List[Well]", True, RESOURCE_TYPE_CONTAINER,
             cardinality="list"),
        _lit("volume_ul", "target_vols", "Optional[List[float]]", False, cardinality="list",
             note="user-stated volume = dispense target; source_vol/ratios out of surface"),
    ),
    "stamp": (
        _sym("source", "source", "Plate", True, RESOURCE_TYPE_PLATE),
        _sym("destination", "target", "Plate", True, RESOURCE_TYPE_PLATE),
        _lit("volume_ul", "volume", "float", True),
    ),
    # --- liquid_handler: tips -------------------------------------------------
    "pick_up_tips": (
        _sym("at", "tip_spots", "List[TipSpot]", True, RESOURCE_TYPE_TIP_SPOT,
             cardinality="list"),
    ),
    "drop_tips": (
        _sym("destination", "tip_spots", "Sequence[Union[TipSpot, Trash]]", True,
             RESOURCE_TYPE_TIP_SPOT, cardinality="list"),
    ),
    "discard_tips": (
        _lit("what", None, 'Literal["tips"]', False,
             note="phrase noun key (FR-3 descriptor join); dispatch-inert"),
        _sym("at", None, "str", False, RESOURCE_TYPE_TIP_SPOT,
             note="vendored discard_tips() drops mounted tips to implicit trash; "
                  "kept symbolic so cue-2 grounds the location; P2.9 hard-case "
                  "fixtures pin semantics"),
    ),
    # --- liquid_handler: transport -------------------------------------------
    "move_resource": (
        _sym("resource", "resource", "Resource", True, RESOURCE_TYPE_RESOURCE),
        _sym("destination", "to",
             "Union[ResourceStack, ResourceHolder, Resource, Coordinate]", True,
             RESOURCE_TYPE_RESOURCE,
             note="string value grounds as reference; structured Coordinate payload "
                  "counts as grounded literal"),
    ),
    "move_plate": (
        _sym("plate", "plate", "Plate", True, RESOURCE_TYPE_PLATE),
        _sym("destination", "to",
             "Union[ResourceStack, ResourceHolder, Resource, Coordinate]", True,
             RESOURCE_TYPE_RESOURCE),
    ),
    "move_lid": (
        _sym("lid", "lid", "Lid", True, RESOURCE_TYPE_LID),
        _sym("destination", "to", "Union[Liddable, ResourceStack, Coordinate]", True,
             RESOURCE_TYPE_RESOURCE),
    ),
    # --- plate_reader ---------------------------------------------------------
    "read_absorbance": (
        _lit("wavelength_nm", "wavelength", "float", True),
        _lit("at", "wells", "Optional[list[str]]", False, cardinality="list",
             note="well positions within the loaded plate: literal, never a slot"),
    ),
    "read_fluorescence": (
        _lit("excitation_nm", "excitation_wavelength", "float", True),
        _lit("emission_nm", "emission_wavelength", "float", True),
        _lit("focal_height_mm", "focal_height", "float", True),
        _lit("at", "wells", "Optional[list[str]]", False, cardinality="list"),
    ),
    "read_luminescence": (
        _lit("focal_height_mm", "focal_height", "float", True),
        _lit("at", "wells", "Optional[list[str]]", False, cardinality="list"),
    ),
}


# ---------------------------------------------------------------------------
# RECORDED DECISION: copilot-surface include/exclude list for phase 2
# (spec rev2 §5 P2.0, defender R5, recon §1.4). One line of rationale each.
# Exclusions are enforced by tests, not by convention.
# ---------------------------------------------------------------------------
#
# INCLUDED (13 tools, exactly PHASE2_TOOL_NAMES):
#   pick_up_tips / drop_tips / discard_tips   tip lifecycle, single-channel.
#   aspirate / dispense                       core volume ops.
#   transfer / stamp                          multi-target + whole-plate copy.
#   move_resource / move_plate / move_lid     deck transport (gripper verbs).
#   read_absorbance / read_fluorescence / read_luminescence
#       PlateReader machine methods exist in vendored PLR (0.2.2 ships
#       pylabrobot.plate_reading incl. a chatterbox backend): verifiable today.
#
# EXCLUDED from the phase-2 generation surface (kept in TOOL_SCHEMA with tier
# metadata intact where they were already authored):
#   mix, blow_out, touch_tip, dispense_to_waste
#       PHANTOMS: no such methods on vendored LiquidHandler @ dd79c4c89
#       (recon §1.4). Marked experimental+excluded so tier history survives;
#       upstream models these effects via kwargs (mix lists,
#       blow_out_air_volume) rather than methods. Parity test FAILS if
#       upstream ever adds them, forcing conscious re-inclusion.
#   set_temperature, shake, stop_shaking (heater_shaker receiver)
#       Defender R5: methods exist on vendored HeaterShaker, but NO praxis
#       backend wiring exists yet. Excluded until a backend lands; marked
#       experimental. Receiver verification plan: heater_shaker NOT verifiable
#       in phase 2 (AC-2.0.x).
#
# VENDORED-BUT-NEVER-IN-SCHEMA (no TOOL_SCHEMA entry; listed here so the
# decision not to include them is recorded too):
#   pick_up_tips96 / drop_tips96 / aspirate96 / dispense96
#       96-channel family: plate-level semantics and channel-capacity
#       validation differ wholesale; excluded unless promoted (spec DAG P2.0).
#   return_tips
#       Returns mounted tips to their ORIGINAL rack position -- implicit head
#       state drives behavior; hostile to confirm-card UX. Tip-return family
#       excluded unless promoted.
#   move_tips
#       Channel-to-channel tip movement: niche maintenance op, no copilot use
#       case in phase 2.
#   serialize_state / load_state / update_head_state / get_mounted_tips /
#       get_picked_up_resource / probe_* / consolidate_tip_inventory
#       State/query surface: kernel-internal plumbing, not user-facing verbs.
# ---------------------------------------------------------------------------


def params_of(tool_name: str) -> tuple[ParamSpec, ...]:
    """The table rows for one included tool. Raises KeyError for unknown or
    excluded-from-phase-2 tools -- loud by design."""
    return PARAM_NAMESPACE[tool_name]


def required_params(tool_name: str) -> tuple[str, ...]:
    """Schema-side names of required params, in table declaration order."""
    return tuple(spec.name for spec in params_of(tool_name) if spec.required)


def symbolic_slots(tool_name: str) -> tuple[ParamSpec, ...]:
    """The symbolic-resource-reference params of one tool (D11 rule input)."""
    return tuple(
        spec for spec in params_of(tool_name) if spec.kind is ParamKind.SYMBOLIC_RESOURCE_REF
    )
