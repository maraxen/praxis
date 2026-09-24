"""N1 risk-tiered PLR tool schema (FR-2/AC-8/AC-14).

Every function carries exactly ONE static ``risk_tier`` assigned at
schema-authoring time. Confirmation friction is a pure function of that tier
and nothing else -- tier is provably independent of parameters (AC-8), and the
assignment is floored by test_tier_floor so a mutating-but-read_only entry
cannot bypass the product (AC-14).

This module is THE TIER PATH: per N1-B it must not import ``warnings``
(advisory badges live in ``plr/warnings.py`` and never change a tier). The
import-boundary tests enforce that structurally.

Effect strings reuse the ported method_contracts EffectType vocabulary so
cue-3 precondition evaluation can join both tables without translation.

P2.0 reconciliation (backlog 4475, spec rev2 AC-2.0.x): every entry carries an
``experimental`` flag and a ``phase2_included`` flag. Entries with
``phase2_included=False`` are OUT of the copilot generation surface; the full
include/exclude decision record (with per-entry rationale) lives next to the
canonical namespace table in ``coxswain/plr/param_namespace.py``. Tier
metadata is retained for ALL entries -- exclusion changes what gets
generated, never how a call is confirmed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

from coxswain.schema.types import RiskTier

__all__ = ["PHASE2_TOOL_NAMES", "TOOL_SCHEMA", "ToolSpec", "tier_of"]


@dataclass(frozen=True)
class ToolSpec:
    """One schema entry: static tier + declared effect set + verb."""

    name: str
    verb: str
    receiver_type: str
    risk_tier: RiskTier
    #: Declared effect set; values are method_contracts.EffectType strings.
    effects: frozenset[str] = frozenset()
    #: Destination is waste -> irreversible family (AC-14 assertion 2).
    to_waste: bool = False
    #: P2.0 (D13/R5 reconciliation): true for entries kept only as tiered
    #: metadata -- phantom verbs absent from vendored PLR and verbs whose
    #: praxis backend does not exist yet. Experimental entries are never in
    #: the phase-2 generation surface.
    experimental: bool = False
    #: In the phase-2 copilot surface (schema-driven generation P2.3/P2.4).
    #: Exclusions are recorded decisions -- see param_namespace.py.
    phase2_included: bool = True


def _spec(
    name: str,
    verb: str,
    receiver_type: str,
    tier: RiskTier,
    effects: tuple[str, ...] = (),
    to_waste: bool = False,
    experimental: bool = False,
) -> ToolSpec:
    return ToolSpec(
        name=name,
        verb=verb,
        receiver_type=receiver_type,
        risk_tier=tier,
        effects=frozenset(effects),
        to_waste=to_waste,
        experimental=experimental,
        # experimental=True implies phase-2 exclusion; explicit here so the
        # table reads as data, not as a rule to re-derive.
        phase2_included=not experimental,
    )


TOOL_SCHEMA: Final[dict[str, ToolSpec]] = {
    spec.name: spec
    for spec in (
        # --- read_only: no effects, executes on propose ----------------------
        _spec("read_absorbance", "read", "plate_reader", RiskTier.READ_ONLY),
        _spec("read_fluorescence", "read", "plate_reader", RiskTier.READ_ONLY),
        _spec("read_luminescence", "read", "plate_reader", RiskTier.READ_ONLY),
        # --- irreversible family: waste destinations / dropped tips ----------
        _spec(
            "drop_tips",
            "drop",
            "liquid_handler",
            RiskTier.IRREVERSIBLE,
            ("drops_tips",),
            to_waste=True,
        ),
        _spec(
            "discard_tips",
            "discard",
            "liquid_handler",
            RiskTier.IRREVERSIBLE,
            ("drops_tips",),
            to_waste=True,
        ),
        _spec(
            "dispense_to_waste",
            "discard",
            "liquid_handler",
            RiskTier.IRREVERSIBLE,
            ("dispenses",),
            to_waste=True,
            # Phantom vs vendored HEAD dd79c4c89 (recon §1.4): no such method.
            experimental=True,
        ),
        # --- reversible mutators ---------------------------------------------
        _spec(
            "pick_up_tips",
            "pick up",
            "liquid_handler",
            RiskTier.REVERSIBLE,
            ("loads_tips",),
        ),
        _spec("aspirate", "aspirate from", "liquid_handler", RiskTier.REVERSIBLE, ("aspirates",)),
        _spec("dispense", "dispense to", "liquid_handler", RiskTier.REVERSIBLE, ("dispenses",)),
        _spec("transfer", "transfer to", "liquid_handler", RiskTier.REVERSIBLE, ("transfers",)),
        _spec("stamp", "stamp onto", "liquid_handler", RiskTier.REVERSIBLE, ("transfers",)),
        _spec(
            "mix",
            "mix",
            "liquid_handler",
            RiskTier.REVERSIBLE,
            ("aspirates", "dispenses"),
            # Phantom vs vendored HEAD dd79c4c89 (recon §1.4); upstream models
            # mixing as aspirate/dispense ``mix`` kwarg lists instead.
            experimental=True,
        ),
        _spec(
            "blow_out",
            "blow out",
            "liquid_handler",
            RiskTier.REVERSIBLE,
            # Phantom vs vendored HEAD dd79c4c89 (recon §1.4); modeled via
            # blow_out_air_volume kwargs on aspirate/dispense.
            experimental=True,
        ),
        _spec(
            "touch_tip",
            "touch",
            "liquid_handler",
            RiskTier.REVERSIBLE,
            # Phantom vs vendored HEAD dd79c4c89 (recon §1.4).
            experimental=True,
        ),
        _spec(
            "move_resource",
            "move",
            "liquid_handler",
            RiskTier.REVERSIBLE,
            ("moves_resource",),
        ),
        _spec("move_plate", "move", "liquid_handler", RiskTier.REVERSIBLE, ("moves_resource",)),
        _spec("move_lid", "move", "liquid_handler", RiskTier.REVERSIBLE, ("moves_resource",)),
        _spec(
            "set_temperature",
            "set",
            "heater_shaker",
            RiskTier.REVERSIBLE,
            ("sets_temperature",),
            # Defender R5: methods exist on vendored HeaterShaker but no praxis
            # backend wiring exists yet -- excluded until it does.
            experimental=True,
        ),
        _spec(
            "shake",
            "start",
            "heater_shaker",
            RiskTier.REVERSIBLE,
            ("starts_shaking",),
            experimental=True,
        ),
        _spec(
            "stop_shaking",
            "stop",
            "heater_shaker",
            RiskTier.REVERSIBLE,
            ("stops_shaking",),
            experimental=True,
        ),
    )
}

#: The phase-2 copilot generation surface: exactly the entries with
#: ``phase2_included=True`` (13 of 20). Everything else is tiered metadata
#: only. See param_namespace.py for the full include/exclude record.
PHASE2_TOOL_NAMES: Final[frozenset[str]] = frozenset(
    name for name, spec in TOOL_SCHEMA.items() if spec.phase2_included
)


def _call_name(target: str | Any) -> str:
    """Accept either a bare function name or any call-shaped object/mapping
    exposing ``name`` (AC-8's randomized-parameter surface)."""
    if isinstance(target, str):
        return target
    if isinstance(target, dict):
        return target["name"]
    name = getattr(target, "name", None)
    if name is None:
        raise KeyError(f"cannot determine call name from {target!r}")
    return str(name)


def tier_of(target: str | Any) -> RiskTier:
    """The ONLY tier lookup. Parameters are structurally irrelevant here:
    only the schema entry for the call's name is consulted."""
    return TOOL_SCHEMA[_call_name(target)].risk_tier
