"""Baseline metrics + Wilson intervals (P2.1 deliverable 2, AC-2.1.x, D8).

The THREE promotion-gate numbers (D8), computed per eval split:

- ``exact_match_accuracy``: fraction of examples whose parsed prediction
  agrees with the intent record on ALL axes via
  ``coxswain.plr.intent_record.check_intent_agreement`` -- which derives
  missing_required/unresolved_slots itself through slot_derivation (D11:
  model-predicted slots do not exist and are never scored).

- ``clarify_recall``: of the gold-clarify examples (intent calls empty OR any
  intended call carrying non-empty derived gaps), fraction where the
  prediction routes to a clarification.

- ``clarify_precision``: of the predictions that route to clarification,
  fraction that are truly gold-clarify.

Clarify routing rule (recorded, deterministic, STATIC scope): a prediction is
clarify-routing iff it produced NO parseable call, or ANY parseable call
derives non-empty ``missing_required`` (cue 1 fires without live state).
Both states trigger the same user-facing clarification UX in P2.8/P2.9.

Deliberately OUT of static clarify detection: ``unresolved_slots`` (cue 2).
Every string-valued resource arg derives a slot -- including the concrete,
groundable references of clean-parse calls -- so slots cannot separate
'ambiguous' from 'resolvable' without LIVE kernel state. Cue-2 resolution is
mandatory kernel-side validation before propose (F1-rev2/C-M1) and is
verified at P2.9 integration; here, ambiguous-referent rows contribute to
exact-match passthrough fidelity and carry their derived unresolved_slots in
the sidecar for downstream consumers. This boundary is restated in the
report under ``clarify_scope_note``.

A call to an unknown/excluded verb is NOT clarify-routing: it is a wrong-call
failure (kernel-side validation exits as an error, not a user question).

Wilson score intervals (Wilson 1927) accompany every point estimate at 95%
(z = two-sided normal quantile for 0.975). Chosen over Wald because golden
slices are small (n~60) and proportions near 0/1 are expected for a strong
baseline; Wilson keeps coverage there where Wald collapses.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from coxswain.plr.intent_record import IntentRecord, PredictedCall, check_intent_agreement
from coxswain.plr.slot_derivation import derive_call_gaps

from .fgml_parser import ParseResult, parse_function_calls

__all__ = [
    "Z95",
    "ScoredExample",
    "wilson_interval",
    "proportion_stat",
    "score_example",
    "score_all",
    "build_report",
]

#: Two-sided 95% z quantile (NormalDist().inv_cdf(0.975)), pinned so reports
#: are reproducible without depending on statistics module internals.
Z95 = 1.9596398454794924


def wilson_interval(successes: int, n: int, z: float = Z95) -> tuple[float, float] | None:
    """Wilson score interval for a binomial proportion.

    Returns ``(lo, hi)`` or ``None`` when n == 0 (no data -> no claim).
    Pure arithmetic; unit-tested against hand-computed constants.
    """
    if n <= 0:
        return None
    p = successes / n
    z2 = z * z
    denom = 1.0 + z2 / n
    center = (p + z2 / (2.0 * n)) / denom
    half = (z * math.sqrt(p * (1.0 - p) / n + z2 / (4.0 * n * n))) / denom
    return max(0.0, center - half), min(1.0, center + half)


def proportion_stat(successes: int, n: int) -> dict[str, Any]:
    """Point estimate + Wilson 95% interval in report form."""
    interval = wilson_interval(successes, n)
    return {
        "value": (successes / n) if n else None,
        "successes": successes,
        "n": n,
        "wilson95": list(interval) if interval is not None else None,
    }


@dataclass(frozen=True)
class ScoredExample:
    record_id: str
    ambiguity_class: str
    exact_match: bool
    clarify_expected: bool
    clarify_predicted: bool
    reasons: tuple[str, ...]
    #: Number of function-call spans the parser found (valid OR unknown verb).
    #: Feeds the AC-2.6.3 tripwire: an out-of-surface row must emit ZERO.
    n_calls_emitted: int = 0


def _normalize(value: Any):
    """Canonical comparison form: numeric strings coerce to numbers, lists to
    tuples, nested dicts sort. Applied to BOTH sides before equality."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return ("num", float(value))
    if isinstance(value, str):
        text = value.strip()
        try:
            return ("num", float(int(text)))
        except ValueError:
            pass
        try:
            return ("num", float(text))
        except ValueError:
            return ("str", text)
    if isinstance(value, (list, tuple)):
        return ("list", tuple(_normalize(v) for v in value))
    if isinstance(value, dict):
        return ("dict", tuple(sorted((k, _normalize(v)) for k, v in value.items())))
    return ("other", repr(value))


def _clarify_expected(intent: IntentRecord) -> bool:
    """Gold label (static scope): out-of-surface (zero calls) OR any intended
    call whose DERIVED missing_required is non-empty. Unresolved slots are NOT
    a static clarify signal -- see module docstring (cue 2 needs live state)."""
    if not intent["calls"]:
        return True
    return any(
        bool(derive_call_gaps(call["name"], call["params"]).missing_required)
        for call in intent["calls"]
    )


def score_example(raw_output: str | None, intent: IntentRecord) -> ScoredExample:
    """Score ONE recorded/inferred output against its intent record."""
    record_id = intent["record_id"]
    reasons: list[str] = []
    raw = raw_output if raw_output is not None else ""
    parsed: ParseResult = parse_function_calls(raw)

    valid_calls: list[ParsedCall] = []
    for call in parsed.calls:
        try:
            derive_call_gaps(call.name, call.params)
            valid_calls.append(call)
        except KeyError:
            reasons.append(f"unknown/excluded tool name {call.name!r} (not clarify-routing)")

    predicted = [PredictedCall(name=c.name, params=c.params) for c in valid_calls]
    # A call WAS emitted but every one was an unknown/excluded verb: this is a
    # wrong-call failure. It must NOT pass exact-match as a fake "abstention"
    # and must NOT count as clarify-routing either.
    emitted_only_invalid = bool(parsed.calls) and not valid_calls

    # Static clarify signal ONLY: abstention or cue-1 missing_required.
    # unresolved_slots excluded on purpose (needs live kernel state; see module
    # docstring 'STATIC scope').
    predicted_clarify = (len(predicted) == 0 and not emitted_only_invalid) or any(
        bool(derive_call_gaps(c.name, c.params).missing_required) for c in valid_calls
    )

    expected_clarify = _clarify_expected(intent)

    if emitted_only_invalid:
        exact = False
        reasons.append("emitted call(s) but all to unknown/excluded verbs")
    else:
        try:
            agreement = check_intent_agreement(predicted, intent)
            exact = agreement.overall
            if not exact:
                reasons.extend(agreement.reasons)
        except KeyError as exc:
            exact = False
            reasons.append(f"gap derivation failed (unknown/excluded tool): {exc}")

    return ScoredExample(
        record_id=record_id,
        ambiguity_class=intent.get("ambiguity_class", "unlabeled"),
        exact_match=exact,
        clarify_expected=expected_clarify,
        clarify_predicted=predicted_clarify,
        reasons=tuple(reasons),
        n_calls_emitted=len(parsed.calls),
    )


def score_all(
    outputs: Mapping[str, str],
    intents: Sequence[IntentRecord],
) -> list[ScoredExample]:
    """Score a whole split. Missing outputs count as empty strings
    (abstention path) rather than crashing the run."""
    scored = []
    for intent in intents:
        scored.append(score_example(outputs.get(intent["record_id"], ""), intent))
    return scored


def build_report(
    scored: Sequence[ScoredExample],
    *,
    mode: str,
    base_revision: str,
    inputs: Mapping[str, str],
    labeled_as: str,
    model_label: str | None = None,
) -> dict[str, Any]:
    """Assemble the metric report with Wilson intervals + confusion counts +
    per-class breakdown. Point estimates WITHOUT their interval never ship.

    ``model_label`` names the weights scored (P2.6: arm + checkpoint sha) so a
    report is never mistaken for another checkpoint's.
    """
    n = len(scored)
    exact_hits = sum(1 for s in scored if s.exact_match)

    # AC-2.6.3 clarify tripwire: out-of-surface rows that emitted ANY call.
    # Counted on the raw parse (unknown verbs included) -- a fabricated call
    # to a non-existent tool is exactly the failure the tripwire exists for.
    tripwire = sum(
        1 for s in scored if s.ambiguity_class == "out_of_surface" and s.n_calls_emitted > 0
    )

    tp = sum(1 for s in scored if s.clarify_expected and s.clarify_predicted)
    fn = sum(1 for s in scored if s.clarify_expected and not s.clarify_predicted)
    fp = sum(1 for s in scored if not s.clarify_expected and s.clarify_predicted)
    tn = sum(1 for s in scored if not s.clarify_expected and not s.clarify_predicted)

    per_class: dict[str, dict[str, Any]] = {}
    for cls in sorted({s.ambiguity_class for s in scored}):
        rows = [s for s in scored if s.ambiguity_class == cls]
        per_class[cls] = {
            "n": len(rows),
            "exact_match": proportion_stat(sum(1 for s in rows if s.exact_match), len(rows)),
            "clarify_expected": sum(1 for s in rows if s.clarify_expected),
            "clarify_predicted": sum(1 for s in rows if s.clarify_predicted),
        }

    failures = [
        {"record_id": s.record_id, "class": s.ambiguity_class, "reasons": list(s.reasons)}
        for s in scored
        if not s.exact_match
    ]

    return {
        "report_kind": "praxis-baseline-eval-report",
        "clarify_scope_note": (
            "clarify_expected/predicted cover OUT-OF-SURFACE (abstention) and "
            "MISSING-SLOT (derived missing_required) classes only; ambiguous-referent "
            "detection needs live kernel grounding (cue 2, F1-rev2/C-M1) and is "
            "verified at P2.9 integration, not in this static harness"
        ),
        "mode": mode,
        "labeled_as": labeled_as,
        "base_revision": base_revision,
        "model_label": model_label,
        "inputs": dict(inputs),
        "n_examples": n,
        "exact_match_accuracy": proportion_stat(exact_hits, n),
        "clarify_recall": proportion_stat(tp, tp + fn),
        "clarify_precision": proportion_stat(tp, tp + fp),
        "clarify_confusion": {
            "true_positive": tp, "false_negative": fn,
            "false_positive": fp, "true_negative": tn,
        },
        "tripwire_out_of_surface_tool_calls": tripwire,
        "per_class": per_class,
        "exact_match_failures": failures,
    }
