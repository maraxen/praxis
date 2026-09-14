"""PLR surface for Coxswain (W2/P2.0): static risk tiers, advisory warnings,
Layer-2b grounding, the canonical param namespace, D11 gap derivation, and the
intent-record contract."""

from coxswain.plr import (
    intent_record,
    param_namespace,
    slot_derivation,
    tool_schema,
)
from coxswain.plr.intent_record import IntentRecord, check_intent_agreement
from coxswain.plr.param_namespace import PARAM_NAMESPACE, ParamKind, ParamSpec
from coxswain.plr.slot_derivation import CallGaps, DerivedSlot, derive_call_gaps
from coxswain.plr.tool_schema import PHASE2_TOOL_NAMES, TOOL_SCHEMA, ToolSpec, tier_of

__all__ = [
    "PARAM_NAMESPACE",
    "PHASE2_TOOL_NAMES",
    "CallGaps",
    "DerivedSlot",
    "IntentRecord",
    "ParamKind",
    "ParamSpec",
    "TOOL_SCHEMA",
    "ToolSpec",
    "check_intent_agreement",
    "derive_call_gaps",
    "intent_record",
    "param_namespace",
    "slot_derivation",
    "tier_of",
    "tool_schema",
]
