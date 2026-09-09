"""Spec 260901 §3.4 / AC-3.1-3.4: verdict/finding/report record shape.

The six test functions named in §3.4's bullet list
(test_join_truth_table, test_no_bool_protocol,
test_will_fail_requires_category, test_unknown_requires_reason,
test_reason_vocabulary_closed, test_report_round_trips_json).
test_join_truth_table and test_reason_vocabulary_closed's real behavior
inflate the *collected* count above six via parametrization / internal
sub-checks -- the *named* function count stays six, matching AC-3.1's "all
six test_verdict.py tests pass." **Round-4 remediation (M7) adds one more,
un-named-in-§3.4 function, `test_join_absorbs_across_shared_operation_id`**,
covering a case none of the six named tests' parametrization ever reaches
(two findings sharing one `operation_id`) -- AC-3.1 is unaffected (it is
still satisfied by the six named functions all passing), this is additive.
**260901 (§Open decisions 1) adds one more, `test_from_wire_maps_
unrecognized_string_to_unknown`**, covering the new consumer rule
(`Verdict.from_wire`); also additive, per AC-3.1's note (§3.6, R15) that a
hard-coded test count is not the gate -- "all tests pass" is.
"""

from __future__ import annotations

import ast
import dataclasses
import itertools
import json
from pathlib import Path

import pytest
from plr_sema._provenance import SurveyStamp
from plr_sema._provenance.git_state import GitState
from plr_sema.verdict import (
    REASON_VOCABULARY,
    AnalysisReport,
    Finding,
    PlrSite,
    Verdict,
    join,
)

SRC_ROOT = Path(__file__).resolve().parents[1] / "src" / "plr_sema"


# ---------------------------------------------------------------------------
# test_join_truth_table
# ---------------------------------------------------------------------------

_VERDICTS = (Verdict.SAFE, Verdict.WILL_FAIL, Verdict.UNKNOWN)


def _all_multisets_up_to_2() -> list[tuple[Verdict, ...]]:
    multisets: list[tuple[Verdict, ...]] = []
    for size in (0, 1, 2):
        multisets.extend(itertools.combinations_with_replacement(_VERDICTS, size))
    return multisets


# Spec §3.4 says "parametrized over all 7 non-trivial multisets of <=2
# findings", but the arithmetic gives 10: 1 empty + 3 singletons + 6
# unordered pairs (3 distinct-verdict pairs + 3 same-verdict pairs) = 10.
# There is no natural way to pick "the 7" the spec author may have meant, so
# per the task brief this enumerates all 10 -- a strict superset of any
# 7-element subset -- and cannot be wrong for being too thorough. Flagged as
# a spec discrepancy in the fixer's report rather than silently resolved.
_MULTISETS = _all_multisets_up_to_2()


# Round-4 remediation (M7, fix 2): a literal, hand-written
# (input_verdicts -> expected_verdict) table, replacing the prior
# `_expected_verdict` re-implementation of join()'s own absorption logic --
# a wrong `join` body used to be able to turn this test red only by
# accident of both implementations agreeing; a literal table asserts the
# spec's table directly. Keys are exactly the 10 tuples `_MULTISETS`
# produces (itertools.combinations_with_replacement over
# (SAFE, WILL_FAIL, UNKNOWN), sizes 0/1/2), so a plain dict lookup covers
# every parametrized case with no ordering ambiguity. The empty key mapping
# to UNKNOWN is B1/B2's fix, not SAFE (spec §3.2, round-4 remediation).
_EXPECTED_JOIN_TABLE: dict[tuple[Verdict, ...], Verdict] = {
    (): Verdict.UNKNOWN,
    (Verdict.SAFE,): Verdict.SAFE,
    (Verdict.WILL_FAIL,): Verdict.WILL_FAIL,
    (Verdict.UNKNOWN,): Verdict.UNKNOWN,
    (Verdict.SAFE, Verdict.SAFE): Verdict.SAFE,
    (Verdict.SAFE, Verdict.WILL_FAIL): Verdict.WILL_FAIL,
    (Verdict.SAFE, Verdict.UNKNOWN): Verdict.UNKNOWN,
    (Verdict.WILL_FAIL, Verdict.WILL_FAIL): Verdict.WILL_FAIL,
    (Verdict.WILL_FAIL, Verdict.UNKNOWN): Verdict.WILL_FAIL,
    (Verdict.UNKNOWN, Verdict.UNKNOWN): Verdict.UNKNOWN,
}


def _expected_verdict(verdicts: tuple[Verdict, ...]) -> Verdict:
    return _EXPECTED_JOIN_TABLE[verdicts]


def _finding_for(verdict: Verdict, index: int) -> Finding:
    """Build a minimally-valid Finding of the given verdict for join()
    exercising -- category/reason are populated only as required by
    __post_init__ (AC-3.3), never both at once for a SAFE finding.
    """
    if verdict is Verdict.WILL_FAIL:
        return Finding(
            verdict=verdict,
            operation_id=f"op{index}",
            category="precondition_state",
            plr_site=None,
            reason="",
        )
    if verdict is Verdict.UNKNOWN:
        return Finding(
            verdict=verdict,
            operation_id=f"op{index}",
            category="",
            plr_site=None,
            reason="no_contract_derived",
        )
    return Finding(
        verdict=verdict, operation_id=f"op{index}", category="", plr_site=None, reason=""
    )


@pytest.mark.parametrize(
    "verdicts",
    _MULTISETS,
    ids=[("+".join(v.value for v in m) or "empty") for m in _MULTISETS],
)
def test_join_truth_table(verdicts: tuple[Verdict, ...]) -> None:
    """Spec §3.2's join table, exhaustively, over all 10 multisets of size
    <=2 (see module-level note above on the 7-vs-10 discrepancy).
    """
    findings = tuple(_finding_for(v, i) for i, v in enumerate(verdicts))
    assert join(findings) == _expected_verdict(verdicts)


def test_join_absorbs_across_shared_operation_id() -> None:
    """Round-4 remediation (M7); docstring corrected 260901 (§Open decisions
    3 -- an independent outside analysis, spot-verified, found this
    docstring had the verdict on its own test backwards). None of the
    parametrized `test_join_truth_table` cases ever share an `operation_id`
    -- `_finding_for` sets `operation_id=f"op{index}"`, so every multiset of
    size 2 carries two DISTINCT operation ids. This test pins the case where
    they don't: a SAFE finding and a WILL_FAIL finding on the SAME
    operation absorb to WILL_FAIL, exactly like two findings on different
    operations would.

    This is CORRECT behavior, not a known-unsound stopgap -- v1 emits
    exactly one Finding per guard (verified,
    `check._findings_for_operation`, e.g. 9 findings for `aspirate`), so two
    findings sharing an `operation_id` are two INDEPENDENT obligations
    (guard A, guard B) that correctly conjoin: if guard B definitely fires,
    the operation definitely fails regardless of guard A being provably
    satisfied. `research_a_d.md`'s R3 proposal -- group `join`'s input by
    `operation_id` and Kleene-join within the group -- would turn this
    correct WILL_FAIL into UNKNOWN, masking a definite guard failure behind
    a satisfied sibling guard; that is unsound in the SAFE direction and
    must NOT be implemented. The case R3's authors were actually worried
    about -- the SAME guard evaluated under two mutually exclusive path
    conditions -- is distinguished from this (two DIFFERENT guards, same
    operation) by `plr_site`, not by `operation_id`, and should never reach
    `join` at all: a forward analysis merges abstract states over incoming
    paths (the information order) upstream of emission, and evaluates each
    guard once against the merged state. See `join`'s own docstring and
    spec §3.2/§Open decisions 3 for the full obligation-vs-information-order
    distinction this test's correctness rests on.
    """
    same_op_findings = (
        _finding_for(Verdict.SAFE, index=1),
        Finding(
            verdict=Verdict.WILL_FAIL,
            operation_id="op1",
            category="precondition_state",
            plr_site=None,
            reason="",
        ),
    )
    assert {f.operation_id for f in same_op_findings} == {"op1"}
    assert join(same_op_findings) == Verdict.WILL_FAIL


# ---------------------------------------------------------------------------
# test_from_wire_maps_unrecognized_string_to_unknown
# ---------------------------------------------------------------------------


def test_from_wire_maps_unrecognized_string_to_unknown() -> None:
    """260901, §Open decisions 1: a consumer that meets a Verdict string it
    does not recognize must map it to UNKNOWN -- always sound, since
    widening what a consumer knows can only lose precision, never fabricate
    a false SAFE/WILL_FAIL claim. This is what makes a future Verdict
    member (e.g. UNREACHABLE, whenever/wherever it lands) a non-breaking
    addition for compliant consumers, without committing to its semantics
    today. Covers: the reserved-but-unused "unreachable" string specifically
    (the concrete near-term case this rule was written for), an arbitrary
    unrecognized string (the general case), and confirms recognized strings
    still round-trip to their own member (the rule only WIDENS, it never
    changes behavior for known values).
    """
    assert Verdict.from_wire("unreachable") is Verdict.UNKNOWN
    assert Verdict.from_wire("some_future_member_nobody_has_invented_yet") is Verdict.UNKNOWN
    assert Verdict.from_wire("") is Verdict.UNKNOWN
    assert Verdict.from_wire("safe") is Verdict.SAFE
    assert Verdict.from_wire("will_fail") is Verdict.WILL_FAIL
    assert Verdict.from_wire("unknown") is Verdict.UNKNOWN

    # Contrast: the plain Enum constructor still raises -- `from_wire` is an
    # opt-in widening, not a change to `Verdict(...)`'s own behavior. Both
    # `plr_sema.verdict.join` and this package's own test round-trip helpers
    # legitimately want the strict form (an unrecognized value there is a
    # programming/serialization bug, not version skew from an external
    # consumer), so `Verdict(...)` is deliberately left unchanged.
    with pytest.raises(ValueError):
        Verdict("unreachable")


# ---------------------------------------------------------------------------
# test_no_bool_protocol
# ---------------------------------------------------------------------------


def test_no_bool_protocol() -> None:
    """Spec §3.1/§3.4: none of Verdict, Finding, AnalysisReport may define a
    truthiness override, and no def with that dunder name may exist
    anywhere under src/plr_sema/. Deliberately not a runtime `assert not
    report` check -- a dataclass is truthy by default, so that would fail
    for the wrong reason (spec §3.4).
    """
    dunder = "__" + "bool__"
    for cls in (Verdict, Finding, AnalysisReport):
        assert dunder not in cls.__dict__, f"{cls.__name__} must not define {dunder}"

    offenders: list[str] = []
    for path in sorted(SRC_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == dunder:
                offenders.append(f"{path}:{node.lineno}")
    assert offenders == [], f"{dunder} defined at: {offenders}"


# ---------------------------------------------------------------------------
# test_will_fail_requires_category / test_unknown_requires_reason
# ---------------------------------------------------------------------------


def test_will_fail_requires_category() -> None:
    """Spec AC-3.3 (WILL_FAIL side): empty category raises ValueError; a
    real category is accepted.
    """
    with pytest.raises(ValueError):
        Finding(
            verdict=Verdict.WILL_FAIL,
            operation_id="op1",
            category="",
            plr_site=None,
            reason="",
        )
    Finding(
        verdict=Verdict.WILL_FAIL,
        operation_id="op1",
        category="precondition_state",
        plr_site=None,
        reason="",
    )


def test_unknown_requires_reason() -> None:
    """Spec AC-3.3, exactly: `reason=""` and `reason="not_a_real_reason"`
    both raise ValueError. (Omitting reason entirely raises TypeError for a
    missing required argument before __post_init__ ever runs -- a dataclass
    mechanic, not the case under test here, per AC-3.3's own note.)
    """
    with pytest.raises(ValueError):
        Finding(
            verdict=Verdict.UNKNOWN,
            operation_id="op1",
            category="",
            plr_site=None,
            reason="",
        )
    with pytest.raises(ValueError):
        Finding(
            verdict=Verdict.UNKNOWN,
            operation_id="op1",
            category="",
            plr_site=None,
            reason="not_a_real_reason",
        )
    Finding(
        verdict=Verdict.UNKNOWN,
        operation_id="op1",
        category="",
        plr_site=None,
        reason="no_contract_derived",
    )


# ---------------------------------------------------------------------------
# test_reason_vocabulary_closed
# ---------------------------------------------------------------------------

_UNRESOLVED = object()
_VALIDATED = object()  # reason=vocabulary_reason(...): dynamic, validated form


def _module_level_constants(tree: ast.Module) -> dict[str, object]:
    """Module-level `NAME = <literal>` / `NAME: T = <literal>` bindings,
    resolved to their literal value -- the only form of non-literal
    `reason=` argument spec §3.3 recognizes as resolvable.
    """
    consts: dict[str, object] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    consts[target.id] = node.value.value
        elif (
            isinstance(node, ast.AnnAssign)
            and node.value is not None
            and isinstance(node.value, ast.Constant)
            and isinstance(node.target, ast.Name)
        ):
            consts[node.target.id] = node.value.value
    return consts


def _is_finding_call(call: ast.Call) -> bool:
    func = call.func
    if isinstance(func, ast.Name):
        return func.id == "Finding"
    if isinstance(func, ast.Attribute):
        return func.attr == "Finding"
    return False


def _resolve_reason_kwarg(call: ast.Call, module_consts: dict[str, object]) -> object:
    """Return the resolved literal reason= value, _UNRESOLVED if a
    `reason=` argument is present but not a string literal or a
    module-level-constant reference, or None if there is no `reason=`
    keyword argument on this call at all (not a site under test).
    """
    for kw in call.keywords:
        if kw.arg != "reason":
            continue
        value_node = kw.value
        if isinstance(value_node, ast.Constant) and isinstance(value_node.value, str):
            return value_node.value
        if isinstance(value_node, ast.Name) and value_node.id in module_consts:
            resolved = module_consts[value_node.id]
            if isinstance(resolved, str):
                return resolved
        # Increment 4 §13.3 (sprint 122): the ONE dynamic form §3.3 admits --
        # `reason=vocabulary_reason(<expr>)`, the validator in verdict.py that
        # raises on any non-member, so a deserialised (cache) Finding can never
        # carry a reason outside the vocabulary. It resolves to no member of
        # its own (it adds nothing to the reverse-direction count).
        if isinstance(value_node, ast.Call):
            f = value_node.func
            fname = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else None
            if fname == "vocabulary_reason":
                return _VALIDATED
        return _UNRESOLVED
    return None


def _resolve_verdict_kwarg(call: ast.Call) -> str | None:
    """260902 (spec §10.8's amendment): resolve the SAME call site's
    `verdict=` argument to the bare attribute name (`"SAFE"`, `"WILL_FAIL"`,
    `"UNKNOWN"`, ...) when it is the literal form `Verdict.<MEMBER>` --
    `None` for any other shape (no `verdict=` kwarg, or an unresolvable
    one), which the caller treats as "not exempt" (the pre-260902 rule).
    """
    for kw in call.keywords:
        if kw.arg != "verdict":
            continue
        value_node = kw.value
        if (
            isinstance(value_node, ast.Attribute)
            and isinstance(value_node.value, ast.Name)
            and value_node.value.id == "Verdict"
        ):
            return value_node.attr
        return None
    return None


def _find_finding_reason_sites(source: str, filename: str) -> list[tuple[ast.Call, object]]:
    """260902 (spec §10.8's amendment): a call site whose `verdict=`
    resolves to `Verdict.SAFE`/`Verdict.WILL_FAIL` is EXEMPT from
    membership -- but only when its `reason=` is exactly the empty-string
    literal. A `SAFE`/`WILL_FAIL` site whose `reason=` is anything else
    (unresolvable, or a non-empty string) is NOT exempt and is collected as
    a normal site, so it still fails the membership check below -- the
    exemption narrows what counts as compliant, it does not widen what the
    scan can see. `Verdict.UNKNOWN`, or an unresolvable `verdict=`, keeps
    the pre-260902 rule unchanged.
    """
    tree = ast.parse(source, filename=filename)
    consts = _module_level_constants(tree)
    sites: list[tuple[ast.Call, object]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _is_finding_call(node):
            resolved = _resolve_reason_kwarg(node, consts)
            if resolved is None:
                continue
            verdict_kind = _resolve_verdict_kwarg(node)
            if verdict_kind in ("SAFE", "WILL_FAIL") and resolved == "":
                continue  # exempt (§10.8): SAFE/WILL_FAIL with reason=""
            sites.append((node, resolved))
    return sites


def test_reason_vocabulary_closed_forward() -> None:
    """Spec §3.3/§3.4, forward direction: every `Finding(..., reason=...)`
    construction site in src/plr_sema/ resolves to a REASON_VOCABULARY
    member.

    Forward (unconditional): every `Finding(..., reason=...)` construction
    site in src/plr_sema/ resolves to a REASON_VOCABULARY member; an
    unresolvable form (bare local variable, computed expression) FAILS the
    scan rather than being skipped over -- demonstrated first against two
    synthetic snippets below, since src/plr_sema/ has zero construction
    sites at T3 and so cannot exercise the rejection path itself.

    Reverse (conditional on >=1 real site existing): every
    REASON_VOCABULARY member is reachable from >=1 construction site. At T3
    there are zero `Finding(...)` construction sites anywhere in
    src/plr_sema/ (plr_sema.derive, which will construct them, is T6+), so
    this direction is unarmed and the test explicitly skips rather than
    passing vacuously -- see §3.3's own warning that a one-directional
    check "would pass vacuously against any natural implementation." It
    arms itself automatically once T6/T8 add construction sites.
    """
    # -- Evidence that the forward check REJECTS, not ignores, unresolvable
    # reason= forms (a bare local variable, and a computed expression).
    bare_local_var = (
        "def _make():\n"
        "    local_var = 'whatever'\n"
        "    Finding(verdict=Verdict.UNKNOWN, operation_id='op', category='',"
        " plr_site=None, reason=local_var)\n"
    )
    bare_sites = _find_finding_reason_sites(bare_local_var, "<synthetic:bare-var>")
    assert len(bare_sites) == 1
    assert bare_sites[0][1] is _UNRESOLVED

    computed_expr = (
        "Finding(verdict=Verdict.UNKNOWN, operation_id='op', category='',"
        " plr_site=None, reason='no_' + 'contract_derived')\n"
    )
    computed_sites = _find_finding_reason_sites(computed_expr, "<synthetic:computed>")
    assert len(computed_sites) == 1
    assert computed_sites[0][1] is _UNRESOLVED

    module_const_ref = (
        "_MY_REASON = 'no_contract_derived'\n"
        "Finding(verdict=Verdict.UNKNOWN, operation_id='op', category='',"
        " plr_site=None, reason=_MY_REASON)\n"
    )
    const_sites = _find_finding_reason_sites(module_const_ref, "<synthetic:const>")
    assert len(const_sites) == 1
    assert const_sites[0][1] == "no_contract_derived"

    # -- 260902 (spec §10.8's amendment): a SAFE/WILL_FAIL site with
    # reason="" is EXEMPT (zero sites collected) -- but the SAME shape with
    # a non-empty reason is NOT exempt and is still collected as a site
    # (which would fail the membership check below, since "some_reason" is
    # not a REASON_VOCABULARY member). UNKNOWN keeps the pre-260902 rule
    # unchanged (a bare reason="" would be collected and fail membership --
    # not exercised here since Finding.__post_init__ itself already forbids
    # an empty reason on UNKNOWN, so no real call site could reach it).
    safe_exempt = (
        "Finding(verdict=Verdict.SAFE, operation_id='op', category='',"
        " plr_site=None, reason='')\n"
    )
    assert _find_finding_reason_sites(safe_exempt, "<synthetic:safe-exempt>") == []

    will_fail_exempt = (
        "Finding(verdict=Verdict.WILL_FAIL, operation_id='op', category='precondition_state',"
        " plr_site=None, reason='')\n"
    )
    assert _find_finding_reason_sites(will_fail_exempt, "<synthetic:will-fail-exempt>") == []

    safe_non_empty_reason = (
        "Finding(verdict=Verdict.SAFE, operation_id='op', category='',"
        " plr_site=None, reason='some_reason')\n"
    )
    non_exempt_sites = _find_finding_reason_sites(safe_non_empty_reason, "<synthetic:safe-non-empty>")
    assert len(non_exempt_sites) == 1
    assert non_exempt_sites[0][1] == "some_reason"

    # -- The real forward scan over src/plr_sema/. Unconditional: with zero
    # construction sites at T3 this is vacuously true, which is honest --
    # the rejection path above is what carries the evidence today.
    offenders, _reachable, _total = _scan_src_reason_sites()
    assert offenders == [], f"Spec §3.3 violation(s): {offenders}"


def _scan_src_reason_sites() -> tuple[list[str], set[str], int]:
    """Shared scan over src/plr_sema/ backing both directions of §3.3's
    closure check. Returns (offenders, reachable_reasons, total_sites).
    """
    offenders: list[str] = []
    reachable: set[str] = set()
    total_sites = 0
    for path in sorted(SRC_ROOT.rglob("*.py")):
        for call_node, resolved in _find_finding_reason_sites(path.read_text(), str(path)):
            total_sites += 1
            if resolved is _VALIDATED:
                continue  # §13.3: reason=vocabulary_reason(...), validated at runtime
            if resolved is _UNRESOLVED:
                offenders.append(f"{path}:{call_node.lineno}: unresolvable reason= form")
            elif resolved not in REASON_VOCABULARY:
                offenders.append(
                    f"{path}:{call_node.lineno}: reason={resolved!r} not in REASON_VOCABULARY"
                )
            else:
                reachable.add(resolved)
    return offenders, reachable, total_sites


def test_reason_vocabulary_closed_reverse() -> None:
    """Spec §3.3/§3.4, reverse direction: every REASON_VOCABULARY member is
    reachable from >=1 `Finding(...)` construction site in src/plr_sema/.

    Split out from the forward direction deliberately. At T3 there are zero
    construction sites (plr_sema.derive, which will make them, is T6+), so
    this direction is unarmed and skips explicitly rather than passing
    vacuously -- §3.3 warns that a one-directional check "would pass
    vacuously against any natural implementation". Keeping it in the same
    function as the forward check would mask that check's genuine pass
    behind this skip marker. It arms itself once T6/T8 add sites.
    """
    offenders, reachable, total_sites = _scan_src_reason_sites()
    assert offenders == [], f"Spec §3.3 violation(s): {offenders}"
    if total_sites == 0:
        pytest.skip(
            "reverse vocabulary check unarmed: src/plr_sema/ contains zero "
            "Finding(...) construction sites yet (plr_sema.derive lands in "
            "T6+). The forward direction, test_reason_vocabulary_closed_"
            "forward, is unconditional and passed. This skip must disappear "
            "automatically once T6/T8 add construction sites."
        )
    unreached = REASON_VOCABULARY - reachable
    assert not unreached, f"REASON_VOCABULARY members with no construction site: {unreached}"


# ---------------------------------------------------------------------------
# test_report_round_trips_json
# ---------------------------------------------------------------------------


def _plr_site_from_dict(d: dict) -> PlrSite:
    return PlrSite(file=d["file"], lineno=d["lineno"], qualname=d["qualname"])


def _git_state_from_dict(d: dict) -> GitState:
    return GitState(**d)


def _stamp_from_dict(d: dict) -> SurveyStamp:
    return SurveyStamp(
        plr=_git_state_from_dict(d["plr"]),
        praxis=_git_state_from_dict(d["praxis"]),
        pylabrobot_version=d["pylabrobot_version"],
        stamped_at=d["stamped_at"],
        schema_version=d["schema_version"],
    )


def _finding_from_dict(d: dict) -> Finding:
    return Finding(
        verdict=Verdict(d["verdict"]),
        operation_id=d["operation_id"],
        category=d["category"],
        plr_site=_plr_site_from_dict(d["plr_site"]) if d["plr_site"] is not None else None,
        reason=d["reason"],
        detail=d["detail"],
        evidence=tuple(_plr_site_from_dict(s) for s in d["evidence"]),
    )


def _report_from_dict(d: dict) -> AnalysisReport:
    return AnalysisReport(
        protocol_fqn=d["protocol_fqn"],
        verdict=Verdict(d["verdict"]),
        findings=tuple(_finding_from_dict(f) for f in d["findings"]),
        stamp=_stamp_from_dict(d["stamp"]),
        schema_version=d["schema_version"],
    )


def test_report_round_trips_json() -> None:
    """Spec §3.4/AC-3.4 (reworded, D15): an AnalysisReport constructed
    directly -- no pipeline run, since T3 has no working pipeline (that's
    AC-6.6, gated in T8) -- serializes to JSON and deserializes
    field-identically.

    Three concrete conversion traps exercised here: (1) `findings` and
    `evidence` are tuples, which come back from a json.loads round-trip as
    lists and must be converted back; (2) `stamp` is a SurveyStamp nesting
    two GitState dataclasses, which asdict recurses into and the
    reconstructor must too; (3) `verdict` (on both the report and each
    Finding) is a str-subclassing Verdict, which json.dumps emits as a bare
    string and reconstruction must map back through Verdict(...).
    """
    stamp = SurveyStamp(
        plr=GitState(hash="a" * 40, branch="main", dirty=False),
        praxis=GitState(
            hash="b" * 40,
            branch="coxswain-p2-pipeline",
            dirty=True,
            dirty_content_id="c" * 40,
        ),
        pylabrobot_version="0.1.0",
        stamped_at="2026-09-01T00:00:00+00:00",
    )
    site = PlrSite(
        file="external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py",
        lineno=42,
        qualname="LiquidHandler._check_containers",
    )
    finding = Finding(
        verdict=Verdict.UNKNOWN,
        operation_id="op1",
        category="",
        plr_site=site,
        reason="no_contract_derived",
        detail="no derived contract entry for this method",
        evidence=(site,),
    )
    report = AnalysisReport(
        protocol_fqn="my.package.my_protocol",
        verdict=join((finding,)),
        findings=(finding,),
        stamp=stamp,
    )

    payload = json.dumps(dataclasses.asdict(report))
    parsed = json.loads(payload)
    reconstructed = _report_from_dict(parsed)

    assert reconstructed == report
