"""P2.6 eval-revision jury brief (task 260903_p26d_eval_revision_brief).

Pure, deterministic COUNTERFACTUAL analysis over three FROZEN artefacts --
the recorded generation dumps (checkpoints A / A2 / A3), the pinned 228-row
eval split (``corpus_p25_sidecar.jsonl`` filtered to ``split == "eval"``),
and the ``baseline_eval`` scorer itself (``metrics.score_example`` /
``check_intent_agreement`` / ``derive_call_gaps`` / ``parse_function_calls``,
all IMPORTED, never edited) -- to QUANTIFY what three jury-proposed eval
revisions would change. This module applies NOTHING to the frozen scorer; it
only measures. See ``.praxia/docs/audits/260903_p26c-oos-natural-decision.md``
sections 5-6 for the jury items' original wording.

Three jury items, each a counterfactual re-score of the SAME frozen dumps:

**J1 -- unknown-verb emission as abstention.** Today, a generation whose
emitted call(s) are ALL to a verb outside the tool schema (e.g.
``read_sample``) is scored as a genuine wrong-call: it fails exact-match and,
on an out-of-surface row, counts toward the AC-2.6.3 tripwire (the raw parse
count is > 0). The counterfactual: treat such a generation as if it had
abstained (zero calls) for BOTH exact-match and tripwire purposes. Realised
by :func:`score_example_cf` with ``Policy(j1_abstain_unknown_verb=True)``;
when the row is not "all-unknown-verb", behaviour is identical to today.

**J2 -- ambiguous-referent vague-span policy.** Ambiguous-referent gold rows
carry exactly one (rarely two) argument whose gold value is a natural-language
span ("the plate", "there", "the tip rack") rather than a groundable id; the
exact-match rule demands the LITERAL string. Three policies compared, applied
ONLY to calls of gold rows with ``ambiguity_class == "ambiguous_referent"``,
and ONLY to the arguments the gold record's own derivation marks as
``SYMBOLIC_RESOURCE_REF`` (D11's ``unresolved_slots``, computed via
``derive_call_gaps`` on the GOLD params -- never guessed):

- (a) ``literal`` -- today: exact string equality, no relaxation.
- (b) ``normalized`` -- case-fold, strip ONE leading article (the/a/an),
  collapse internal whitespace, then compare.
- (c) ``any_span`` -- the predicted value is accepted iff it is present and
  non-empty (a real span was produced at all, regardless of content). Per
  the docstring: since EVERY ``SYMBOLIC_RESOURCE_REF`` argument of a gold
  ambiguous-referent call is marked unresolved (not only the vague one), this
  policy is deliberately permissive on any such argument of that call, not
  only the "correct" vague one -- a known over-generosity, reported not
  hidden (see the module's ``caveats`` in the CLI markdown output).

**J3 -- golden id grammar.** Golden (hand-authored) eval rows write resource
ids fully underscore-joined (``source_plate_A1``, ``tube_rack_B3``); the
floor/coverage rows use the dotted well grammar (``plate_1.D1``). A "pure
grammar transform" is defined conservatively (:func:`_dotted_form`): a
trailing ``_XN``/`.XN`` well suffix (one letter + 1-2 digits) is normalised
to a leading-dot form; two strings are a pure-transform pair iff both have a
dotted form and those dotted forms are equal. No lookup table, no guessing:
anything the regex cannot parse on BOTH sides is left a genuine miss.

**Combined** = J1 + J2(b, normalized) + J3(pure-transform) together, per
checkpoint, checked against the (unchanged) promotion thresholds.

Reuse discipline: the exact-match RULE for the "no policy" case is never
duplicated -- :func:`score_example_cf` calls ``metrics.score_example``
directly when every policy is off (guarantees byte-identical reproduction of
the committed reports). Aggregation (Wilson intervals, tripwire, per-class,
confusion) is never duplicated either -- every report here is built by
feeding freshly-constructed ``metrics.ScoredExample`` rows through the real,
frozen ``metrics.build_report``.

CLI::

    python -m praxis_training.finetune.eval_revision_brief \\
        --out-json training/eval/reports/260903_eval_revision_brief.json
"""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from coxswain.plr.intent_record import IntentRecord, PredictedCall, check_intent_agreement
from coxswain.plr.slot_derivation import derive_call_gaps

from praxis_training.baseline_eval import metrics
from praxis_training.baseline_eval.fgml_parser import ParsedCall, parse_function_calls
from praxis_training.baseline_eval.metrics import ScoredExample, build_report
from praxis_training.finetune.p26c_predictions import TRIPWIRE3

__all__ = [
    "Policy",
    "OFF",
    "J1_ONLY",
    "J2_NORMALIZED",
    "J2_ANY_SPAN",
    "J3_ONLY",
    "COMBINED",
    "CHECKPOINTS",
    "GOLD_NATIVE_PATH",
    "GOLD_SIDECAR_PATH",
    "PROMOTION_THRESHOLDS",
    "load_gold_eval",
    "load_dump_outputs",
    "score_example_cf",
    "report_for_policy",
    "diagnose_ref_only_row",
    "j1_analysis",
    "j2_analysis",
    "j3_analysis",
    "combined_analysis",
    "tripwire3_sanity",
    "build_brief",
    "render_markdown",
    "main",
]

# --------------------------------------------------------------------------
# Constants (overridable by the CLI)
# --------------------------------------------------------------------------

GOLD_NATIVE_PATH = Path("training/assemble/out/corpus_p25.jsonl")
GOLD_SIDECAR_PATH = Path("training/assemble/out/corpus_p25_sidecar.jsonl")

#: checkpoint -> (dump path, committed report path)
CHECKPOINTS: Mapping[str, Mapping[str, Path]] = {
    "A": {
        "dump": Path("training/eval/outputs/260902_p26_dump_A.json"),
        "report": Path("training/eval/reports/260902_p26_rescore_A.json"),
    },
    "A2": {
        "dump": Path("training/eval/outputs/260902_p26b_dump_A2.json"),
        "report": Path("training/eval/reports/260902_p26b_A.json"),
    },
    "A3": {
        "dump": Path("training/eval/outputs/260903_p26c_dump_A3.json"),
        "report": Path("training/eval/reports/260903_p26c_A3.json"),
    },
}

#: Unchanged promotion anchors (``praxis_training.finetune.promotion.THRESHOLDS``),
#: restated here as plain floats so this module has no import-time coupling to
#: that module's CLI surface.
PROMOTION_THRESHOLDS: Mapping[str, float] = {"T_acc": 0.80, "T_clr_recall": 0.70, "T_clr_prec": 0.90}

_ARTICLE_RE = re.compile(r"^(the|a|an)\s+")
_WS_RE = re.compile(r"\s+")
_WELL_SUFFIX_RE = re.compile(r"^(?P<prefix>.+)[._](?P<well>[A-Za-z]\d{1,2})$")


# --------------------------------------------------------------------------
# Policy
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Policy:
    """One counterfactual configuration. ``j2_mode`` is one of
    ``"literal"`` (off), ``"normalized"`` (J2b), ``"any_span"`` (J2c).
    """

    j1_abstain_unknown_verb: bool = False
    j2_mode: str = "literal"
    j3_pure_transform: bool = False

    @property
    def is_noop(self) -> bool:
        return not self.j1_abstain_unknown_verb and self.j2_mode == "literal" and not self.j3_pure_transform

    def label(self) -> str:
        if self.is_noop:
            return "today (no revision)"
        bits = []
        if self.j1_abstain_unknown_verb:
            bits.append("J1")
        if self.j2_mode != "literal":
            bits.append(f"J2({self.j2_mode})")
        if self.j3_pure_transform:
            bits.append("J3")
        return "+".join(bits)


OFF = Policy()
J1_ONLY = Policy(j1_abstain_unknown_verb=True)
J2_NORMALIZED = Policy(j2_mode="normalized")
J2_ANY_SPAN = Policy(j2_mode="any_span")
J3_ONLY = Policy(j3_pure_transform=True)
COMBINED = Policy(j1_abstain_unknown_verb=True, j2_mode="normalized", j3_pure_transform=True)


# --------------------------------------------------------------------------
# Loading (gold split + recorded dumps)
# --------------------------------------------------------------------------


def _read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{idx + 1}: invalid JSON ({exc})") from exc
    return rows


def load_gold_eval(sidecar_path: Path = GOLD_SIDECAR_PATH) -> list[IntentRecord]:
    """The pinned 228-row eval split: sidecar rows with ``split == "eval"``,
    in file order. The sidecar row shape (record_id/utterance/calls/...)
    already satisfies the ``IntentRecord`` contract the scorer expects.
    """
    rows = _read_jsonl(sidecar_path)
    return [row for row in rows if row.get("split") == "eval"]  # type: ignore[misc]


def load_dump_outputs(dump_path: Path) -> dict[str, str]:
    """Recorded-outputs artifact -> ``{record_id: raw_output}``. Reads the
    same JSON shape ``baseline_eval.runner`` writes/reads, but standalone
    (no artifact_kind/base_revision validation) since this module only
    QUANTIFIES against already-committed, already-validated dumps.
    """
    blob = json.loads(dump_path.read_text(encoding="utf-8"))
    outputs: dict[str, str] = {}
    for entry in blob.get("outputs", []):
        rid = entry.get("record_id")
        if rid:
            outputs[rid] = entry.get("raw_output", "")
    return outputs


# --------------------------------------------------------------------------
# J2/J3 primitives
# --------------------------------------------------------------------------


def _normalize_vague(value: str) -> str:
    """J2(b): case-fold, strip ONE leading article (the/a/an), collapse
    internal whitespace. Pure string transform, unit-tested on known pairs.
    """
    text = value.strip().casefold()
    text = _ARTICLE_RE.sub("", text, count=1)
    text = _WS_RE.sub(" ", text).strip()
    return text


def _dotted_form(value: str) -> str | None:
    """J3: canonical dotted form of a trailing well-locator reference, or
    ``None`` if ``value`` does not end in a recognisable ``<prefix><sep><well>``
    shape (one letter + 1-2 digits). Conservative BY DESIGN: no lookup table,
    no guessing -- ``plate_1`` (missing well) and ``plate["A1"]`` (bracket
    syntax) both return ``None`` rather than a fabricated guess.
    """
    m = _WELL_SUFFIX_RE.match(value.strip())
    if not m:
        return None
    return f"{m.group('prefix')}.{m.group('well')}"


def _is_pure_transform_pair(gold: str, pred: str) -> bool:
    if gold == pred:
        return False  # not a mismatch at all
    dg, dp = _dotted_form(gold), _dotted_form(pred)
    return dg is not None and dp is not None and dg == dp


def _slot_arg_names(call_name: str, gold_params: Mapping[str, Any]) -> set[str]:
    """Argument names the GOLD params derive as ``SYMBOLIC_RESOURCE_REF`` for
    this call (D11, via the real ``derive_call_gaps`` -- never guessed).
    """
    try:
        gaps = derive_call_gaps(call_name, gold_params)
    except KeyError:
        return set()
    return {s.arg_name for s in gaps.unresolved_slots}


def _snap_predicted(
    predicted: Sequence[PredictedCall],
    intent: IntentRecord,
    policy: Policy,
) -> list[PredictedCall]:
    """Return a copy of ``predicted`` with SYMBOLIC_RESOURCE_REF argument
    values snapped to the gold's own value wherever the active policy deems
    the predicted/gold pair equivalent. Only touches slot arguments that are
    (a) both present, (b) both strings, (c) currently different. Everything
    else -- non-slot params, missing keys, extra keys, sequence/name
    mismatches -- passes through untouched, so the real (frozen)
    ``check_intent_agreement`` still enforces every other axis exactly as
    today.
    """
    intended = intent["calls"]
    if len(predicted) != len(intended):
        return list(predicted)
    out: list[PredictedCall] = []
    for p, i in zip(predicted, intended):
        if p.name != i["name"]:
            out.append(p)
            continue
        slot_args = _slot_arg_names(i["name"], i["params"])
        new_params = dict(p.params)
        for key in slot_args:
            gold_val = i["params"].get(key)
            pred_val = p.params.get(key)
            if not isinstance(gold_val, str) or not isinstance(pred_val, str):
                continue
            if gold_val == pred_val:
                continue
            equivalent = False
            if policy.j2_mode != "literal" and intent.get("ambiguity_class") == "ambiguous_referent":
                if policy.j2_mode == "normalized":
                    equivalent = _normalize_vague(gold_val) == _normalize_vague(pred_val)
                elif policy.j2_mode == "any_span":
                    equivalent = pred_val.strip() != ""
            if not equivalent and policy.j3_pure_transform:
                equivalent = _is_pure_transform_pair(gold_val, pred_val)
            if equivalent:
                new_params[key] = gold_val
        out.append(PredictedCall(name=p.name, params=new_params))
    return out


def _maximal_snap(predicted: Sequence[PredictedCall], intent: IntentRecord) -> tuple[list[PredictedCall], list[dict[str, str]]]:
    """Snap EVERY differing (string, string) slot-argument pair to the gold
    value, unconditionally, and report every pair snapped. Used only for
    diagnosis (:func:`diagnose_ref_only_row`): "would this row exact-match if
    ALL of its reference-string arguments were considered equivalent" --
    never used to compute a reported accuracy number.
    """
    intended = intent["calls"]
    if len(predicted) != len(intended):
        return list(predicted), []
    out: list[PredictedCall] = []
    pairs: list[dict[str, str]] = []
    for p, i in zip(predicted, intended):
        if p.name != i["name"]:
            out.append(p)
            continue
        slot_args = _slot_arg_names(i["name"], i["params"])
        new_params = dict(p.params)
        for key in slot_args:
            gold_val = i["params"].get(key)
            pred_val = p.params.get(key)
            if not isinstance(gold_val, str) or not isinstance(pred_val, str):
                continue
            if gold_val == pred_val:
                continue
            pairs.append({"arg_name": key, "gold_reference": gold_val, "predicted_reference": pred_val})
            new_params[key] = gold_val
        out.append(PredictedCall(name=p.name, params=new_params))
    return out, pairs


# --------------------------------------------------------------------------
# Counterfactual row scorer
# --------------------------------------------------------------------------


def _valid_and_invalid(raw: str) -> tuple[list[ParsedCall], bool]:
    """Parse ``raw`` and split calls into (valid, all-invalid?) via the same
    ``derive_call_gaps``-based check ``metrics.score_example`` uses.
    """
    parsed = parse_function_calls(raw)
    valid: list[ParsedCall] = []
    for c in parsed.calls:
        try:
            derive_call_gaps(c.name, c.params)
            valid.append(c)
        except KeyError:
            pass
    emitted_only_invalid = bool(parsed.calls) and not valid
    return valid, emitted_only_invalid


def score_example_cf(raw_output: str | None, intent: IntentRecord, policy: Policy) -> ScoredExample:
    """One row, one policy. Delegates to the REAL, frozen
    ``metrics.score_example`` whenever ``policy.is_noop`` (guarantees J1/J2/J3
    all OFF reproduces today's committed reports byte-for-byte); otherwise
    reuses the same parser (``parse_function_calls``) and gap-derivation
    (``derive_call_gaps``) the frozen scorer uses, and the frozen
    ``check_intent_agreement`` for the final verdict -- only the SET of
    predicted calls (J1) and the snapped argument values fed into it (J2/J3)
    differ from today's path.
    """
    if policy.is_noop:
        return metrics.score_example(raw_output, intent)

    record_id = intent["record_id"]
    reasons: list[str] = []
    raw = raw_output if raw_output is not None else ""
    parsed = parse_function_calls(raw)

    valid_calls: list[ParsedCall] = []
    for c in parsed.calls:
        try:
            derive_call_gaps(c.name, c.params)
            valid_calls.append(c)
        except KeyError:
            reasons.append(f"unknown/excluded tool name {c.name!r} (not clarify-routing)")

    emitted_only_invalid = bool(parsed.calls) and not valid_calls
    treated_as_abstention = policy.j1_abstain_unknown_verb and emitted_only_invalid
    predicted_calls = [] if treated_as_abstention else valid_calls
    effective_emitted_only_invalid = emitted_only_invalid and not treated_as_abstention
    # AC-2.6.3 tripwire counts the RAW parse count; under J1's abstention
    # treatment an all-unknown-verb emission counts as ZERO calls emitted.
    n_calls_emitted = 0 if treated_as_abstention else len(parsed.calls)

    predicted_pcs = [PredictedCall(name=c.name, params=c.params) for c in predicted_calls]
    predicted_clarify = (len(predicted_pcs) == 0 and not effective_emitted_only_invalid) or any(
        bool(derive_call_gaps(c.name, c.params).missing_required) for c in predicted_calls
    )
    expected_clarify = metrics._clarify_expected(intent)  # reused, not reimplemented (precedent: failure_breakdown._normalize)

    if effective_emitted_only_invalid:
        exact = False
        reasons.append("emitted call(s) but all to unknown/excluded verbs")
    else:
        adjusted = _snap_predicted(predicted_pcs, intent, policy)
        try:
            agreement = check_intent_agreement(adjusted, intent)
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
        n_calls_emitted=n_calls_emitted,
    )


def report_for_policy(
    outputs: Mapping[str, str],
    intents: Sequence[IntentRecord],
    policy: Policy,
    *,
    model_label: str | None = None,
) -> dict[str, Any]:
    """A full ``metrics.build_report``-shaped report for one (checkpoint,
    policy) pair, built from freshly-scored rows via ``score_example_cf``.
    Aggregation (Wilson intervals, tripwire, per-class, confusion) is the
    REAL frozen ``build_report`` -- not reimplemented.
    """
    scored = [score_example_cf(outputs.get(i["record_id"], ""), i, policy) for i in intents]
    return build_report(
        scored,
        mode="counterfactual",
        base_revision="eval_revision_brief:counterfactual",
        inputs={"policy": policy.label()},
        labeled_as=f"COUNTERFACTUAL RE-SCORE ({policy.label()}) -- NOT a scorer change, quantification only",
        model_label=model_label,
    )


def diagnose_ref_only_row(
    raw_output: str | None,
    intent: IntentRecord,
) -> list[dict[str, str]] | None:
    """``None`` if this row exact-matches TODAY, or if it still misses after
    every reference-string argument is maximally (unconditionally) snapped to
    gold -- i.e. the row's failure has some OTHER cause. Otherwise, the list
    of ``{arg_name, gold_reference, predicted_reference}`` pairs that were the
    row's ONLY discrepancy (J3's "fails ONLY because of a reference-string
    mismatch" test).
    """
    today = metrics.score_example(raw_output, intent)
    if today.exact_match:
        return None
    raw = raw_output if raw_output is not None else ""
    valid_calls, emitted_only_invalid = _valid_and_invalid(raw)
    if emitted_only_invalid:
        return None
    predicted_pcs = [PredictedCall(name=c.name, params=c.params) for c in valid_calls]
    if len(predicted_pcs) != len(intent["calls"]):
        return None
    adjusted, pairs = _maximal_snap(predicted_pcs, intent)
    if not pairs:
        return None
    try:
        agreement = check_intent_agreement(adjusted, intent)
    except KeyError:
        return None
    if not agreement.overall:
        return None
    return pairs


# --------------------------------------------------------------------------
# Per-jury-item analyses
# --------------------------------------------------------------------------


def _stat(report: Mapping[str, Any], key: str) -> dict[str, Any]:
    s = report[key]
    return {"value": s["value"], "successes": s["successes"], "n": s["n"]}


def _headline(report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "exact_match_accuracy": _stat(report, "exact_match_accuracy"),
        "clarify_recall": _stat(report, "clarify_recall"),
        "clarify_precision": _stat(report, "clarify_precision"),
        "tripwire": report["tripwire_out_of_surface_tool_calls"],
    }


def _flips(today: Mapping[str, str], intents_by_id: Mapping[str, IntentRecord], policy: Policy) -> list[dict[str, Any]]:
    """record_ids whose exact-match verdict flips under ``policy`` vs today,
    either direction.
    """
    out = []
    for rid, intent in intents_by_id.items():
        raw = today.get(rid, "")
        before = metrics.score_example(raw, intent).exact_match
        after = score_example_cf(raw, intent, policy).exact_match
        if before != after:
            out.append({"record_id": rid, "before": before, "after": after})
    return sorted(out, key=lambda r: r["record_id"])


def j1_analysis(outputs_by_ckpt: Mapping[str, Mapping[str, str]], intents: Sequence[IntentRecord]) -> dict[str, Any]:
    intents_by_id = {i["record_id"]: i for i in intents}
    result: dict[str, Any] = {}
    for ckpt, outputs in outputs_by_ckpt.items():
        today_report = report_for_policy(outputs, intents, OFF)
        cf_report = report_for_policy(outputs, intents, J1_ONLY)
        flips = _flips(outputs, intents_by_id, J1_ONLY)
        gos05 = intents_by_id.get("golden-out-surface-05")
        gos05_clears = (
            score_example_cf(outputs.get("golden-out-surface-05", ""), gos05, J1_ONLY).exact_match
            if gos05 is not None
            else None
        )
        result[ckpt] = {
            "today": _headline(today_report),
            "counterfactual": _headline(cf_report),
            "flipped_record_ids": flips,
            "golden_out_surface_05_clears": gos05_clears,
        }
    return result


def j2_analysis(outputs_by_ckpt: Mapping[str, Mapping[str, str]], intents: Sequence[IntentRecord]) -> dict[str, Any]:
    ambig_intents = [i for i in intents if i.get("ambiguity_class") == "ambiguous_referent"]
    ambig_ids = {i["record_id"] for i in ambig_intents}
    intents_by_id = {i["record_id"]: i for i in intents}
    n_ambig = len(ambig_intents)
    result: dict[str, Any] = {}
    for ckpt, outputs in outputs_by_ckpt.items():
        per_policy: dict[str, Any] = {}
        for name, policy in (("literal", OFF), ("normalized", J2_NORMALIZED), ("any_span", J2_ANY_SPAN)):
            rep = report_for_policy(outputs, intents, policy)
            ambig_hits = sum(
                1
                for rid in ambig_ids
                if score_example_cf(outputs.get(rid, ""), intents_by_id[rid], policy).exact_match
            )
            per_policy[name] = {
                "ambiguous_referent_exact_match": {"successes": ambig_hits, "n": n_ambig},
                "total_exact_match_accuracy": _stat(rep, "exact_match_accuracy"),
                "tripwire": rep["tripwire_out_of_surface_tool_calls"],
            }
        moved_b = _flips(outputs, {rid: intents_by_id[rid] for rid in ambig_ids}, J2_NORMALIZED)
        moved_c = _flips(outputs, {rid: intents_by_id[rid] for rid in ambig_ids}, J2_ANY_SPAN)

        def _pairs_for(rid: str) -> list[dict[str, Any]]:
            intent = intents_by_id[rid]
            valid, invalid = _valid_and_invalid(outputs.get(rid, ""))
            if invalid or len(valid) != len(intent["calls"]):
                return []
            out = []
            for p, i in zip(valid, intent["calls"]):
                if p.name != i["name"]:
                    continue
                for key in _slot_arg_names(i["name"], i["params"]):
                    gv, pv = i["params"].get(key), p.params.get(key)
                    if isinstance(gv, str) and isinstance(pv, str) and gv != pv:
                        out.append({"arg_name": key, "gold_reference": gv, "predicted_reference": pv})
            return out

        result[ckpt] = {
            "policies": per_policy,
            "moved_rows_normalized_b": [{"record_id": f["record_id"], "pairs": _pairs_for(f["record_id"])} for f in moved_b],
            "moved_rows_any_span_c": [{"record_id": f["record_id"], "pairs": _pairs_for(f["record_id"])} for f in moved_c],
        }
    return result


def j3_analysis(outputs_by_ckpt: Mapping[str, Mapping[str, str]], intents: Sequence[IntentRecord]) -> dict[str, Any]:
    intents_by_id = {i["record_id"]: i for i in intents}
    golden_ids = [i["record_id"] for i in intents if i["record_id"].startswith("golden")]
    result: dict[str, Any] = {}
    for ckpt, outputs in outputs_by_ckpt.items():
        ref_only_rows: dict[str, list[dict[str, str]]] = {}
        for rid in golden_ids:
            pairs = diagnose_ref_only_row(outputs.get(rid, ""), intents_by_id[rid])
            if pairs is not None:
                ref_only_rows[rid] = pairs
        pure_rows: dict[str, list[dict[str, Any]]] = {}
        for rid, pairs in ref_only_rows.items():
            annotated = [
                p | {"pure_transform": _is_pure_transform_pair(p["gold_reference"], p["predicted_reference"])}
                for p in pairs
            ]
            if all(p["pure_transform"] for p in annotated):
                pure_rows[rid] = annotated
        cf_report = report_for_policy(outputs, intents, J3_ONLY)
        result[ckpt] = {
            "golden_ref_mismatch_only_rows": {rid: pairs for rid, pairs in ref_only_rows.items()},
            "golden_ref_mismatch_only_count": len(ref_only_rows),
            "pure_transform_rows": pure_rows,
            "pure_transform_count": len(pure_rows),
            "counterfactual_accuracy_if_pure_transforms_were_hits": _stat(cf_report, "exact_match_accuracy"),
        }
    return result


def combined_analysis(outputs_by_ckpt: Mapping[str, Mapping[str, str]], intents: Sequence[IntentRecord]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for ckpt, outputs in outputs_by_ckpt.items():
        rep = report_for_policy(outputs, intents, COMBINED)
        acc = rep["exact_match_accuracy"]["value"]
        rec = rep["clarify_recall"]["value"]
        prec = rep["clarify_precision"]["value"]
        trip = rep["tripwire_out_of_surface_tool_calls"]
        promotes = (
            acc is not None and acc >= PROMOTION_THRESHOLDS["T_acc"]
            and prec is not None and prec >= PROMOTION_THRESHOLDS["T_clr_prec"]
            and rec is not None and rec >= PROMOTION_THRESHOLDS["T_clr_recall"]
            and trip == 0
        )
        result[ckpt] = {
            "headline": _headline(rep),
            "thresholds": dict(PROMOTION_THRESHOLDS),
            "would_promote": promotes,
        }
    return result


def tripwire3_sanity(report_path: Path) -> dict[str, Any]:
    """Sanity check (deliverable 2.iii): the frozen ``TRIPWIRE3`` row list
    (``p26c_predictions.py``) against a committed report's own
    ``exact_match_failures`` -- every TRIPWIRE3 id must appear there (it is,
    by definition, a row A2/A3 got wrong).
    """
    rep = json.loads(report_path.read_text(encoding="utf-8"))
    failed_ids = {row["record_id"] for row in rep.get("exact_match_failures", [])}
    present = {rid: (rid in failed_ids) for rid in TRIPWIRE3}
    return {
        "tripwire3_ids": list(TRIPWIRE3),
        "present_in_failures": present,
        "all_present": all(present.values()),
    }


# --------------------------------------------------------------------------
# Top-level assembly + rendering
# --------------------------------------------------------------------------


def build_brief(
    *,
    checkpoints: Mapping[str, Mapping[str, Path]] = CHECKPOINTS,
    sidecar_path: Path = GOLD_SIDECAR_PATH,
) -> dict[str, Any]:
    intents = load_gold_eval(sidecar_path)
    outputs_by_ckpt = {ckpt: load_dump_outputs(paths["dump"]) for ckpt, paths in checkpoints.items()}

    today: dict[str, Any] = {}
    for ckpt, outputs in outputs_by_ckpt.items():
        today[ckpt] = _headline(report_for_policy(outputs, intents, OFF))

    tripwire3_check = {ckpt: tripwire3_sanity(paths["report"]) for ckpt, paths in checkpoints.items()}

    return {
        "report_kind": "praxis-eval-revision-brief",
        "task_id": "260903_p26d_eval_revision_brief",
        "n_examples": len(intents),
        "checkpoints": sorted(checkpoints),
        "today": today,
        "j1_unknown_verb_abstention": j1_analysis(outputs_by_ckpt, intents),
        "j2_ambiguous_referent_vague_span": j2_analysis(outputs_by_ckpt, intents),
        "j3_golden_id_grammar": j3_analysis(outputs_by_ckpt, intents),
        "combined": combined_analysis(outputs_by_ckpt, intents),
        "tripwire3_sanity": tripwire3_check,
        "promotion_thresholds": dict(PROMOTION_THRESHOLDS),
    }


def _fmt_stat(stat: Mapping[str, Any]) -> str:
    if stat["value"] is None:
        return "n/a"
    return f"{stat['value']:.3f} ({stat['successes']}/{stat['n']})"


def render_markdown(brief: Mapping[str, Any]) -> str:
    lines = ["# P2.6 eval-revision jury brief", ""]
    lines.append("| checkpoint | acc (today) | J1 acc | J2b acc | J2c acc | J3 acc | combined acc | combined tripwire | promotes? |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for ckpt in brief["checkpoints"]:
        today = brief["today"][ckpt]
        j1 = brief["j1_unknown_verb_abstention"][ckpt]["counterfactual"]
        j2b = brief["j2_ambiguous_referent_vague_span"][ckpt]["policies"]["normalized"]
        j2c = brief["j2_ambiguous_referent_vague_span"][ckpt]["policies"]["any_span"]
        j3 = brief["j3_golden_id_grammar"][ckpt]
        comb = brief["combined"][ckpt]
        lines.append(
            f"| {ckpt} | {_fmt_stat(today['exact_match_accuracy'])} "
            f"| {_fmt_stat(j1['exact_match_accuracy'])} "
            f"| {_fmt_stat(j2b['total_exact_match_accuracy'])} "
            f"| {_fmt_stat(j2c['total_exact_match_accuracy'])} "
            f"| {_fmt_stat(j3['counterfactual_accuracy_if_pure_transforms_were_hits'])} "
            f"| {_fmt_stat(comb['headline']['exact_match_accuracy'])} "
            f"| {comb['headline']['tripwire']} "
            f"| {'YES' if comb['would_promote'] else 'no'} |"
        )
    lines.append("")
    lines.append("## J1 flips (unknown-verb-as-abstention)")
    for ckpt in brief["checkpoints"]:
        flips = brief["j1_unknown_verb_abstention"][ckpt]["flipped_record_ids"]
        clears = brief["j1_unknown_verb_abstention"][ckpt]["golden_out_surface_05_clears"]
        lines.append(f"- {ckpt}: {len(flips)} flip(s) {[f['record_id'] for f in flips]}; golden-out-surface-05 clears: {clears}")
    lines.append("")
    lines.append("## J3 pure-transform rows (golden misses)")
    for ckpt in brief["checkpoints"]:
        j3 = brief["j3_golden_id_grammar"][ckpt]
        lines.append(
            f"- {ckpt}: {j3['golden_ref_mismatch_only_count']} golden row(s) fail ONLY on a reference-string mismatch; "
            f"{j3['pure_transform_count']} of those are a pure grammar transform: {list(j3['pure_transform_rows'])}"
        )
    lines.append("")
    lines.append("No policy is recommended here; this brief only quantifies.")
    return "\n".join(lines) + "\n"


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m praxis_training.finetune.eval_revision_brief")
    p.add_argument("--sidecar", type=Path, default=GOLD_SIDECAR_PATH)
    p.add_argument("--out-json", type=Path, default=None)
    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    brief = build_brief(sidecar_path=args.sidecar)
    md = render_markdown(brief)
    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(brief, indent=2) + "\n", encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
