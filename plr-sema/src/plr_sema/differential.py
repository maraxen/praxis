"""plr_sema.differential: the differential-test harness (spec 260901 §8, T10,
backlog #4836).

Compares the **45 hand-written ``MethodContract`` instances** (currently
``praxis/backend/core/simulation/method_contracts.py``, the ``legacy_pinned``
surface only -- T13 (51446375) made the analyzed surface a parameter and
``upstream_nonlegacy`` has no orchestration layer, hence no hand-written
contracts to differ against, §8's own scope) against ``DerivedContract``s for
the same qualnames (§7.2), classifying every pair into one of four kinds.

**Never imports ``praxis`` (§1.3/AC-1.2).** The hand contracts are loaded by
**AST-reading** the file named by a required ``--contracts-path PATH`` (D19,
round-6 remediation R1) -- ``ast.parse`` + a walk for
``Call(func=Name("MethodContract"))``, exactly the same shape ``--survey-json``
/ ``--taxonomy-json`` already use elsewhere in this package. See
``load_hand_contracts``.

**The requires_tips bridge is the weakest link in the whole spec (§8.1's own
words)** -- a heuristic string/name-mention test, not semantics. Two
independent signals are computed per resolved contract, over its WHOLE
transitive ``delegates_to`` closure (``derive_contract``, §7.2):

* ``_guard_credits_tip_required`` -- the mechanical condition-mention clause
  (D13/R2): a guard's own ``mentions_params`` overlaps
  ``tip_bearing_params(qualname)``, itself defined as the survey record's own
  ``params`` filtered by an HM-19 ``_NAME_KEYWORD_CATEGORIES`` keyword mapped
  to ``tip_state`` (today: ``"Tip"``) -- reused directly from
  ``scripts/survey_plr_exceptions.py``, not a second hand-typed copy (round-6
  remediation R2 -- the old ``MethodContract``-field-based definition is
  provably ``∅`` for all 45, see that function's docstring). This is the
  fallback for ``raises is None`` (assert) and the ``"<dynamic:"``-prefixed
  sentinel (D18, trap 1) -- both cases are structurally excluded from the
  clause below and fall through here.
* ``_guard_credits_tip_absence`` -- the raises-based clause (D13), consulting
  ``InlinedGuard.kind`` (C4) to fix the ``HasTipError``/``pick_up_tips``
  polarity inversion documented in §8.1: a ``"raise_guard"`` raising a
  ``tip_state``-categorized exception (per ``--taxonomy-json``) fires when its
  own ``condition`` is TRUE and blocks the call -- i.e. it forbids the state
  the condition describes. The one instance measured at the current pin
  (``HasTipError`` on ``LiquidHandler.pick_up_tips``) forbids tip PRESENCE, so
  this clause credits ``requires_tips=False``, never ``True``.

Combining these two signals with the hand contract's own ``requires_tips``
boolean (§8.4: only ``requires_tips``/``requires_tips_count`` are compared --
the abstractions align there and nowhere else) gives ``classify_contract``'s
four-way outcome. **This exact hand/derived -> kind mapping is this task's
own design, not given verbatim by the spec** (§8.1/§8.2 specify the four
kinds and their meanings, and the two bridge clauses, but not the truth
table combining them) -- see ``classify_contract``'s docstring for the table
and the reasoning behind each cell.

``(module, qualname)`` resolution (round-6 remediation R5): PascalCase
``receiver_type`` (``heater_shaker`` -> ``HeaterShaker``), then apply D22's
"UNIQUE module among indexed survey records whose ``class_name == X``"
lookup, generalized here from ``plr_sema.derive``'s ``LiquidHandler``-only
form to any class name (T10's population, all 45 hand contracts, is wider
than ``SUPPORTED_TOOLS``, D22's only prior population). Two dispositions
D22 itself does not specify are classified ``hand_only``, not aborted:
a class resolving to >1 module (``module_ambiguous``) and a class resolving
to exactly one module that lacks the named method (``method_absent``). A
third, defensive disposition (``class_absent`` -- the PascalCased
``receiver_type`` has no survey record at all) is not observed at the
current pin (R5 measures 29 resolve + 13 method-absent + 3 module-ambiguous
= 45, no class-absent case) but is handled rather than assumed unreachable,
matching ``derive_contract``'s own totality discipline (AC-7.2: never raise).

**Gap noted, not worked around (task brief instruction): the spec's own
§8.3 verification command omits ``--survey-json``.** ``tip_bearing_params``
needs the survey record's own ``params`` field (R2), which is not carried by
the ``derived_contracts.json`` build artifact (its guards carry
``free_vars``/``mentions_params`` per FINDING, not the defining method's
full parameter list) -- so this CLI reads the survey JSON directly (the same
``training/verify/data/plr_preconditions.json`` ``derive/`` already reads)
via a required ``--survey-json PATH``, in addition to ``--taxonomy-json`` and
``--contracts-path``. This is additive to the shown gate command, not a
deviation from D19's own "required path flag, AST/JSON-read, never imported"
pattern -- see this task's own report for the full account.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from plr_sema._provenance import SurveyStamp, survey_stamp
from plr_sema.derive import (
    InlinedGuard,
    SurveyRecord,
    build_index,
    derive_contract,
    load_survey,
)
from plr_sema.derive import _stamp_to_dict  # noqa: SLF001 - same-package reuse, see derive/__main__.py
from plr_sema.verdict import PlrSite

__all__ = [
    "SCHEMA_VERSION",
    "HandContract",
    "Disagreement",
    "load_hand_contracts",
    "load_taxonomy",
    "tip_state_keywords",
    "tip_bearing_params",
    "classify_contract",
    "build_report",
]

SCHEMA_VERSION = 1

#: differential.py lives at src/plr_sema/differential.py -- repo root is
#: three parents up (matches plr_sema._hand_maintained's own REPO_ROOT, the
#: other top-level-under-src/plr_sema module that needs it).
_REPO_ROOT = Path(__file__).resolve().parents[3]

_TIP_STATE_CATEGORY = "tip_state"

Qualkey = tuple[str, str]


# ---------------------------------------------------------------------------
# §8.1 -- the four-kind Disagreement record, verbatim from the spec's own
# code block.
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Disagreement:
    qualname: str
    kind: Literal["hand_only", "derived_only", "conflict", "agree"]
    hand: str  # rendered hand-written claim
    derived: str  # rendered derived evidence
    plr_sites: tuple[PlrSite, ...]


# ---------------------------------------------------------------------------
# Loading the 45 hand contracts -- AST-read, never imported (D19/R1).
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class HandContract:
    """One AST-recovered ``MethodContract(...)`` call's keyword values.
    Only ``requires_tips``/``requires_tips_count`` are interpreted by the
    bridge (§8.4); ``raw`` carries every other keyword, literal-evaluated
    where possible, for rendering only."""

    method_name: str
    receiver_type: str
    requires_tips: bool = False
    requires_tips_count: int | None = None
    raw: dict[str, Any] = field(default_factory=dict)


def load_hand_contracts(path: str | Path) -> list[HandContract]:
    """AST-read every ``MethodContract(...)`` call in ``path`` (D19, round-6
    remediation R1) -- never ``import``s the file, so this stays outside
    §1.3/AC-1.2's ``praxis``-import boundary regardless of where ``path``
    points. All 21 ``MethodContract`` fields are keyword-only literals at
    the current pin (no ``EffectType.*`` enum-member arguments appear in any
    of the 45 calls) -- a keyword whose value is not ``ast.literal_eval``-able
    degrades to its unparsed source text in ``raw`` rather than aborting the
    whole load, since AC-8.1 requires every hand contract to be classified,
    not just the ones with fully-literal keyword sets."""
    tree = ast.parse(Path(path).read_text(encoding="utf-8"), filename=str(path))
    contracts: list[HandContract] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
            continue
        if node.func.id != "MethodContract":
            continue
        raw: dict[str, Any] = {}
        for kw in node.keywords:
            if kw.arg is None:
                continue  # **kwargs form -- not used by any of the 45, defensive
            try:
                raw[kw.arg] = ast.literal_eval(kw.value)
            except ValueError:
                raw[kw.arg] = ast.unparse(kw.value)
        contracts.append(
            HandContract(
                method_name=raw["method_name"],
                receiver_type=raw["receiver_type"],
                requires_tips=bool(raw.get("requires_tips", False)),
                requires_tips_count=raw.get("requires_tips_count"),
                raw=raw,
            )
        )
    return contracts


# ---------------------------------------------------------------------------
# §8.1 -- (module, qualname) resolution, generalized D22 (round-6 remediation
# R5). PascalCase + "unique module among class_name == X" lookup, with the
# two dispositions D22 itself never specifies (>1 module; method absent)
# classified hand_only rather than raised.
# ---------------------------------------------------------------------------


def _pascal_case(receiver_type: str) -> str:
    """``heater_shaker`` -> ``HeaterShaker`` (R5's "two-line mechanical
    transform")."""
    return "".join(part.capitalize() for part in receiver_type.split("_"))


# ---------------------------------------------------------------------------
# §8.1's tip_bearing_params (D13/R2) -- reuses HM-19's own
# _NAME_KEYWORD_CATEGORIES table (scripts/survey_plr_exceptions.py), the
# SAME sys.path-shim mechanism tests/test_hand_maintained_ratchet.py already
# uses to import it. Adds no registry row (R2's own text): this is a reuse
# of an already-registered hand-maintained surface, not a second copy of it.
# ---------------------------------------------------------------------------


def tip_state_keywords() -> tuple[str, ...]:
    """The keyword(s) HM-19's own ``_NAME_KEYWORD_CATEGORIES`` maps to
    ``"tip_state"`` (today: ``("Tip",)``) -- imported directly from
    ``scripts/survey_plr_exceptions.py``, never re-typed here."""
    scripts_dir = str(_REPO_ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    import survey_plr_exceptions  # local import: only reachable once scripts/ is on sys.path

    return tuple(
        keyword
        for category, keyword in survey_plr_exceptions._NAME_KEYWORD_CATEGORIES
        if category == _TIP_STATE_CATEGORY
    )


def tip_bearing_params(rec: SurveyRecord, tip_keywords: tuple[str, ...]) -> frozenset[str]:
    """``tip_bearing_params(qualname)`` (D13/R2): the survey record's own
    ``params`` whose names contain, case-insensitively, one of
    ``tip_keywords``. At the current pin (``tip_keywords == ("Tip",)``) this
    matches ``tip_spots``/``tip_rack`` -- narrow, not ``∅`` (R2)."""
    return frozenset(p for p in rec.params if any(kw.lower() in p.lower() for kw in tip_keywords))


def load_taxonomy(path: str | Path) -> dict[str, str]:
    """Load ``plr_exception_taxonomy.json`` (required ``--taxonomy-json``,
    D19) into a bare ``{class_name: category}`` map -- the ``category``
    field is already computed upstream (``scripts/survey_plr_exceptions.py``
    via ``_NAME_KEYWORD_CATEGORIES``/``_MODULE_SUBSTRING_CATEGORIES``); this
    function does not recompute it."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return {c["name"]: c.get("category", "uncategorized") for c in payload["classes"]}


# ---------------------------------------------------------------------------
# The two bridge clauses (§8.1).
# ---------------------------------------------------------------------------


def _guard_credits_tip_absence(guard: InlinedGuard, taxonomy: dict[str, str]) -> bool:
    """Raises-based clause, polarity-fixed (D13). A ``"raise_guard"`` fires
    when its own ``condition`` is TRUE and blocks the call -- i.e. it
    forbids the state ``condition`` describes. The one instance measured at
    the current pin (``HasTipError`` on ``pick_up_tips``) forbids tip
    PRESENCE, so a raise_guard raising a ``tip_state`` exception credits
    ``requires_tips=False``, never ``True``. ``guard.kind`` is checked
    explicitly rather than assumed: an ``"assert"`` finding structurally
    never carries a ``raises`` value (``raises=None``, trap 1), so this
    branch is unreachable for asserts by construction, not by convention --
    the explicit check documents that instead of relying on it silently."""
    if guard.raises is None or guard.is_dynamic_raise:
        return False
    if taxonomy.get(guard.raises) != _TIP_STATE_CATEGORY:
        return False
    return guard.kind == "raise_guard"


def _guard_credits_tip_required(guard: InlinedGuard, tip_params: frozenset[str]) -> bool:
    """Mechanical condition-mention clause (D13/R2): ``guard.free_vars`` (the
    ``InlinedGuard`` name for a finding's ``mentions_params``) overlaps
    ``tip_bearing_params(qualname)``. This is the fallback for
    ``raises is None`` and the ``"<dynamic:"``-prefixed sentinel (D18, trap
    1) -- both fall through to this clause structurally, since neither is
    matchable against ``plr_exception_taxonomy.json``'s class-name keys --
    and is evaluated independently of ``_guard_credits_tip_absence`` for
    every guard: the two clauses are not mutually exclusive over one guard,
    only over what each can independently contribute."""
    return bool(set(guard.free_vars) & tip_params)


# ---------------------------------------------------------------------------
# classify_contract -- the four-way outcome. NOTE: the mapping table below
# is this task's own design; §8.1/§8.2 specify the four kinds and the two
# bridge clauses but not the truth table combining hand.requires_tips with
# the two derived signals. See the module docstring's "Gap noted" paragraph
# and this task's report for the reasoning.
# ---------------------------------------------------------------------------


def classify_contract(
    hand: HandContract,
    records: list[SurveyRecord],
    index: dict[Qualkey, SurveyRecord],
    taxonomy: dict[str, str],
    tip_keywords: tuple[str, ...],
    *,
    stamp: SurveyStamp,
) -> tuple[Disagreement, str]:
    """Classify one hand contract. Returns ``(Disagreement, disposition)``;
    ``disposition`` is one of ``"resolved"``, ``"class_absent"``,
    ``"module_ambiguous"``, ``"method_absent"`` -- reported separately from
    ``Disagreement.kind`` since the spec's ``Disagreement`` shape (§8.1) has
    no field for it, but R5's own tally (29 resolve / 13 method-absent / 3
    module-ambiguous) is a real, reportable measurement.

    **The requires_tips truth table (this task's own design):**

    | hand.requires_tips | derived_required | derived_absent | kind          |
    |---------------------|-------------------|-----------------|---------------|
    | True                | True              | (any)           | agree         |
    | True                | False             | True            | conflict      |
    | True                | False             | False           | hand_only     |
    | False               | True              | (any)           | derived_only  |
    | False               | False             | (any)           | agree         |

    Reasoning: ``derived_required`` is the only signal that can corroborate
    a POSITIVE ``requires_tips=True`` claim: it directly means "found a
    guard mentioning a tip-bearing parameter". ``derived_absent`` means "found
    a guard that forbids tip presence" -- direct evidence AGAINST a True
    claim (a real contradiction, hence ``conflict`` when hand says True and
    only this signal fires), and *consistent with* (not proof of) a False
    claim or silence, hence folded into ``agree`` on the False side rather
    than invented as a fifth kind. When hand says False and NEITHER signal
    fires, that is still ``agree`` -- vacuously, since "not required" is the
    correct reading of an un-set default field and derivation found nothing
    to contradict it (§8.4's own framing of what a meaningful ``agree`` is,
    extended here).
    """
    expected_class = _pascal_case(hand.receiver_type)
    hand_label = f"{hand.receiver_type}.{hand.method_name}"
    modules = sorted({rec.module for rec in records if rec.class_name == expected_class})

    if not modules:
        return (
            Disagreement(
                qualname=hand_label,
                kind="hand_only",
                hand=_render_hand(hand),
                derived=f"no survey class_name == {expected_class!r} at this pin (class_absent)",
                plr_sites=(),
            ),
            "class_absent",
        )
    if len(modules) > 1:
        return (
            Disagreement(
                qualname=hand_label,
                kind="hand_only",
                hand=_render_hand(hand),
                derived=(
                    f"{expected_class!r} resolves to {len(modules)} modules "
                    f"({', '.join(modules)}); D22 refuses to pick one (module_ambiguous)"
                ),
                plr_sites=(),
            ),
            "module_ambiguous",
        )

    module = modules[0]
    qualname = f"{expected_class}.{hand.method_name}"
    key: Qualkey = (module, qualname)
    if key not in index:
        return (
            Disagreement(
                qualname=qualname,
                kind="hand_only",
                hand=_render_hand(hand),
                derived=f"{qualname!r} not found in module {module!r} at this pin (method_absent)",
                plr_sites=(),
            ),
            "method_absent",
        )

    rec = index[key]
    contract = derive_contract(module, qualname, index, stamp=stamp)
    tip_params = tip_bearing_params(rec, tip_keywords)
    required_evidence = [g for g in contract.guards if _guard_credits_tip_required(g, tip_params)]
    absent_evidence = [g for g in contract.guards if _guard_credits_tip_absence(g, taxonomy)]
    derived_required = bool(required_evidence)
    derived_absent = bool(absent_evidence)

    if hand.requires_tips:
        if derived_required:
            kind: Literal["hand_only", "derived_only", "conflict", "agree"] = "agree"
            sites = tuple(g.site for g in required_evidence)
        elif derived_absent:
            kind = "conflict"
            sites = tuple(g.site for g in absent_evidence)
        else:
            kind = "hand_only"
            sites = ()
    else:
        if derived_required:
            kind = "derived_only"
            sites = tuple(g.site for g in required_evidence)
        else:
            kind = "agree"
            sites = tuple(g.site for g in absent_evidence) if derived_absent else ()

    derived_str = (
        f"tip_bearing_params={sorted(tip_params)}, "
        f"requires_tips-required guards={len(required_evidence)}, "
        f"requires_tips-absent guards={len(absent_evidence)}, "
        f"gaps={len(contract.gaps)}"
    )
    return (
        Disagreement(
            qualname=qualname,
            kind=kind,
            hand=_render_hand(hand),
            derived=derived_str,
            plr_sites=sites,
        ),
        "resolved",
    )


def _render_hand(hand: HandContract) -> str:
    parts = [f"requires_tips={hand.requires_tips}"]
    if hand.requires_tips_count is not None:
        parts.append(f"requires_tips_count={hand.requires_tips_count}")
    return f"{hand.receiver_type}.{hand.method_name}(" + ", ".join(parts) + ")"


# ---------------------------------------------------------------------------
# Report assembly (§8.3's `--report`).
# ---------------------------------------------------------------------------


def _plr_site_to_json(site: PlrSite) -> dict[str, Any]:
    return {"file": site.file, "lineno": site.lineno, "qualname": site.qualname}


def _disagreement_to_json(d: Disagreement) -> dict[str, Any]:
    return {
        "qualname": d.qualname,
        "kind": d.kind,
        "hand": d.hand,
        "derived": d.derived,
        "plr_sites": [_plr_site_to_json(s) for s in d.plr_sites],
    }


def build_report(
    results: list[tuple[Disagreement, str]],
    stamp: SurveyStamp,
    *,
    total_hand_contracts: int,
) -> dict[str, Any]:
    """Assemble the `--report` JSON payload: per-kind counts (AC-8.1's four
    kinds), the resolution-disposition breakdown (R5's 29/13/3 tally, as
    measured -- not hardcoded), and every classified contract."""
    kinds = Counter(d.kind for d, _disposition in results)
    dispositions = Counter(disposition for _d, disposition in results)
    return {
        "schema_version": SCHEMA_VERSION,
        "stamp": _stamp_to_dict(stamp),
        "total_hand_contracts": total_hand_contracts,
        "counts": {
            "agree": kinds.get("agree", 0),
            "hand_only": kinds.get("hand_only", 0),
            "derived_only": kinds.get("derived_only", 0),
            "conflict": kinds.get("conflict", 0),
        },
        "resolution": {
            "resolved": dispositions.get("resolved", 0),
            "class_absent": dispositions.get("class_absent", 0),
            "module_ambiguous": dispositions.get("module_ambiguous", 0),
            "method_absent": dispositions.get("method_absent", 0),
        },
        "disagreements": [_disagreement_to_json(d) for d, _disposition in results],
    }


# ---------------------------------------------------------------------------
# CLI (§8.3).
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m plr_sema.differential", description=__doc__
    )
    parser.add_argument(
        "--survey-json",
        type=Path,
        required=True,
        help=(
            "Path to plr_preconditions.json (required, no default -- D19). "
            "Not present in the spec's own §8.3 command line; required here "
            "because tip_bearing_params (D13/R2) needs the survey record's "
            "own params field, which derived_contracts.json does not carry "
            "-- see this module's docstring."
        ),
    )
    parser.add_argument(
        "--taxonomy-json",
        type=Path,
        required=True,
        help="Path to plr_exception_taxonomy.json (required -- D19).",
    )
    parser.add_argument(
        "--contracts-path",
        type=Path,
        required=True,
        help=(
            "Path to the hand-written MethodContract source file, AST-read, "
            "never imported (required -- D19/R1)."
        ),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Write the full JSON report to this path. Always prints a summary to stderr.",
    )
    args = parser.parse_args(argv)

    records = load_survey(args.survey_json)
    index = build_index(records)
    hand_contracts = load_hand_contracts(args.contracts_path)
    taxonomy = load_taxonomy(args.taxonomy_json)
    tip_keywords = tip_state_keywords()
    stamp = survey_stamp()

    results = [
        classify_contract(hc, records, index, taxonomy, tip_keywords, stamp=stamp)
        for hc in hand_contracts
    ]
    report = build_report(results, stamp, total_hand_contracts=len(hand_contracts))

    counts = report["counts"]
    print(
        f"{len(hand_contracts)} hand contracts classified: "
        f"agree={counts['agree']} hand_only={counts['hand_only']} "
        f"derived_only={counts['derived_only']} conflict={counts['conflict']}",
        file=sys.stderr,
    )
    print(f"resolution: {report['resolution']}", file=sys.stderr)

    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote {args.report}", file=sys.stderr)
    else:
        print(json.dumps(report, indent=2, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
