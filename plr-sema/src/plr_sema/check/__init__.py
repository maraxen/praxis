"""plr_sema.check: the browser-side checker (spec 260901 §6).

**Packaging fact, not a convention.** ``libcst`` ships a Rust native
extension unavailable under Pyodide; importing ``pylabrobot`` to check a
protocol would defeat the point of a static analyzer that runs before the
environment exists. So `check/` (this package) imports NEITHER -- mechanised
by ``tests/test_import_boundary.py::test_no_pylabrobot_import_under_check``
and demonstrated by poisoning both to ``None`` in ``sys.modules`` (AC-6.1).
It also never imports ``pydantic`` (§6.2) -- see ``check/graph.py``'s stdlib
mirror -- and never shells out (no ``git``, no subprocess): the
``SurveyStamp`` an ``AnalysisReport`` carries is deserialized from whatever
the derived-contracts payload already recorded at build time, not
recomputed.

**Round-1 entry point: ``check_graph(graph_json, contracts_json) ->
AnalysisReport``.** Takes two JSON *strings* (matching the ``_json`` naming
and the fact that this function's whole job starts with ``json.loads`` --
neither argument is a pre-parsed dict). ``graph_json`` is the wire format a
(round-2) ``extract/`` would produce, or -- in round 1 -- the committed
fixture generated out-of-process (§6.2, T8; see
``tests/fixtures/simple_transfer_graph.json`` and
``tests/test_check_graph.py``). ``contracts_json`` is
``plr-sema/data/derived_contracts.json`` (§7.3), the build artifact
``plr_sema.derive`` regenerates from the survey.

**260902 (spec §11, "SEMA-IR, the analyzer's middle"): lower-then-check.**
``check_graph``'s SIGNATURE is unchanged, but its body is now: ``json.loads``
both inputs -> build ``param_names`` from the contract table's additive
``params`` key (§11.2.4) -> :func:`plr_sema.check.ir.lower_graph` -> the new
core, :func:`check_ir` (this module) -> relabel through the bytecode's
``sideband["origin"]`` map (§11.4.3, so ``AnalysisReport.findings``'
``operation_id``s are still real graph operation ids, not instruction
indices) -> ``join`` -> ``AnalysisReport``. ``check/graph.py``'s
``OperationNode``/``ResourceNode``/``ProtocolComputationGraph`` mirror is no
longer read by this runtime path at all (§11.4.2) -- it survives as the
lowering's DOCUMENTED input schema, now total over all 34 upstream fields,
and as the comparison target for Fork C's (now exhaustiveness) drift test.
Every v1 verdict, reason, and the shipped fixture's report are UNCHANGED
(AC-11.6) -- this is purely a middle-of-the-pipe substitution, not a
semantics change.

**Every v1 verdict is UNKNOWN (§0, §7.4's forward hazard).** This module
never constructs a ``SAFE`` or ``WILL_FAIL`` ``Finding`` -- §7.4 names the
soundness fence a future round must build before the first ``SAFE`` is ever
emitted, and this module does not attempt to build it. Findings are produced
purely from *derivation-mechanical* facts (§0.2): which pipeline stage
returned nothing for this operation, never a semantic claim about why.

**Per-operation reason logic (mechanics only, no new classification).
Redefined 260901 T11 -- see "unsupported_tool, redefined" below:**

1. ``op.receiver_type is None`` -> ``receiver_type_unknown`` (no contract
   lookup is even attempted -- there is no key to look up).
2. ``f"{op.receiver_type}.{op.method_name}"`` absent from the contract table
   -> ``unsupported_tool``.
3. Otherwise, the resolved ``DerivedContract`` (§7.2/§7.3) is walked:
   * every recorded gap (``unresolved_delegate`` / ``no_contract_derived``,
     the only two ``plr_sema.derive`` ever emits, §7.2) becomes one Finding
     with that same reason;
   * every guard becomes one ``guard_predicate_unparsed`` Finding (§3.3: "a
     guard condition string could not be turned into a predicate"), which is
     unconditionally true in v1 since no predicate parser exists yet.
     (Round-4 remediation, B4: this used to branch to the more specific
     ``argument_not_static`` when a guard's ``free_vars`` intersected
     ``op.depends_on_params``, but that reason has been withdrawn from
     ``REASON_VOCABULARY`` -- the guard-free-var namespace and the
     protocol-parameter namespace it was meant to intersect are disjoint in
     every shipped fixture, so the branch never fired, and a same-named
     collision would have fired it for no semantic cause. See
     ``plr_sema.verdict.REASON_VOCABULARY``'s docstring for the reinstatement
     path.)
   * an operation whose ``foreach_source``/``foreach_body`` is populated
     additionally gets one ``loop_bounds_unknown`` Finding (§3.3: these
     fields identify the loop construct, never its bounds -- bounds are
     deferred item (d)).

**``unsupported_tool``, redefined (260901 T11).** Before T11, step 2 read
``op.method_name not in SUPPORTED_TOOLS`` -- the analyzer's scope was
identical to the dynamic execution harness's 10-tool capability boundary
(``training.verify.dispatcher.SUPPORTED_TOOLS``), because the derived
contract table only ever held entries for those 10 methods, so the two
checks were redundant. T11 decouples derivation from ``SUPPORTED_TOOLS``
(``plr_sema.derive`` now derives a contract for every one of the whole
survey's 4,770 methods, not just the 10 -- see
``plr_sema.derive.__main__.build_derived_contracts_payload``), so the two
checks are no longer redundant, and keeping the ``SUPPORTED_TOOLS`` gate
would have re-imposed the 10-method scope this whole task exists to remove.
``unsupported_tool`` is therefore now defined purely in terms of the
contract table this module actually has in hand: **"key absent from the
contract table"**, i.e. "not resolvable to any method the whole-surface
derivation analyzed" -- not "outside a hand-maintained 10-name allowlist".
``SUPPORTED_TOOLS`` itself is UNCHANGED and still imported/re-exported here
(``__all__``) for ``test_supported_tools_match_upstream`` (AC-6.5) -- it
remains a real thing, just a DIFFERENT boundary now: the dynamic execution
harness's own capability limit (``verify.dispatcher``), which this static
analyzer no longer shares or gates on.

Because the contract table now spans the whole survey rather than only
finding-bearing methods (T11 item 4's zero-findings decision -- see
``build_derived_contracts_payload``'s docstring), a method the survey
scanned but recorded zero ``PreconditionFinding``s for ("known and
unconstrained") gets a real, present, EMPTY contract entry (``guards: []``,
``gaps: []``) rather than an absent key -- so it resolves via step 3 below,
not ``unsupported_tool``, and falls through to the zero-guards/zero-gaps
fallback described next. ``unsupported_tool`` now fires only for a method
name the whole-survey derivation never saw at all: genuinely not part of
the analyzed PLR surface (a typo, a non-PLR receiver, or PLR relocating/
renaming something between the pin the contracts were derived against and
the graph being checked).

**A resolved contract with zero guards, zero gaps, and no loop now
synthesizes one fallback ``no_contract_derived`` Finding (round-4
remediation, B1/B2/§0(ii); this is also T11's answer for the "known,
zero-own-findings, empty-closure" case above -- 2,178 of the 3,456
zero-finding methods at the current pin).** Before round-4's fix, that
combination fell through to an empty finding list for the operation, and --
if it happened for *every* operation in a graph -- ``join(())`` would
return the pre-fix ``SAFE`` default, a live soundness bug on a reachable
public path (a graph with zero operations reaches it trivially; a
resolved-but-empty contract also reaches it). This never fired against the
pre-T11 ``derived_contracts.json`` (all ten ``SUPPORTED_TOOLS`` entries
carried >=1 guard), which is exactly why it went unnoticed then -- the data
never exercised the gap; it fires routinely now that the whole surface
(including genuinely unconstrained methods) is derived. ``join`` (spec
§3.2) now independently treats the empty multiset as UNKNOWN regardless, so
this fallback is defense in depth, not the sole fix -- see
``plr_sema.verdict.join``'s docstring.
"""

from __future__ import annotations

import dataclasses
import json
from typing import Any

from plr_sema._provenance import SurveyStamp
from plr_sema._provenance.git_state import GitState
from plr_sema.check import cache as cache_mod
from plr_sema.check import ir, predicate, tipstate, volumestate
from plr_sema.check._supported_tools import SUPPORTED_TOOLS
from plr_sema.telemetry import emit_finding
from plr_sema.verdict import AnalysisReport, Finding, PlrSite, SoundnessScope, Verdict, join

__all__ = ["SUPPORTED_TOOLS", "check_graph", "check_ir"]


def _git_state_from_dict(d: dict[str, Any]) -> GitState:
    return GitState(
        hash=d["hash"],
        branch=d["branch"],
        dirty=d["dirty"],
        dirty_content_id=d.get("dirty_content_id"),
        provenance_source=d.get("provenance_source", "git"),
        toplevel=d.get("toplevel"),
    )


def _stamp_from_dict(d: dict[str, Any]) -> SurveyStamp:
    """Reconstruct the ``SurveyStamp`` a derived-contracts payload already
    recorded at build time (§2.2/§7.3) -- ``check/`` never shells out to
    compute a fresh one (module docstring).
    """
    return SurveyStamp(
        plr=_git_state_from_dict(d["plr"]),
        praxis=_git_state_from_dict(d["praxis"]),
        pylabrobot_version=d.get("pylabrobot_version"),
        stamped_at=d["stamped_at"],
        schema_version=d.get("schema_version", 1),
        # T13 (260901, backlog #4859): additive -- absent in any pre-T13
        # payload, defaults to DEFAULT_SURFACE's own name/pin.
        surface=d.get("surface", "legacy_pinned"),
        surface_pin=d.get("surface_pin"),
    )


def _plr_site_from_dict(d: dict[str, Any] | None) -> PlrSite | None:
    if d is None:
        return None
    return PlrSite(file=d["file"], lineno=d["lineno"], qualname=d["qualname"])


# ---------------------------------------------------------------------------
# §3.3/§3.4's AST-resolvable-reason requirement: `Finding(..., reason=...)`
# must resolve to a string literal or a module-level constant reference at
# EACH call site -- a bare local variable or function parameter fails the
# scan (`test_reason_vocabulary_closed_{forward,reverse}`), even if the
# value it carries at runtime is always a REASON_VOCABULARY member. A single
# shared helper taking `reason: str` as a parameter (the natural-looking
# design) would therefore FAIL both tests, since the `reason=reason` inside
# such a helper is exactly the rejected bare-local-variable form. Each
# REASON_VOCABULARY member below gets its own tiny constructor with the
# literal string written directly into its one `Finding(...)` call.
# ---------------------------------------------------------------------------


def _receiver_type_unknown(operation_id: str) -> Finding:
    return Finding(
        verdict=Verdict.UNKNOWN,
        operation_id=operation_id,
        category="",
        plr_site=None,
        reason="receiver_type_unknown",
    )


def _unsupported_tool(operation_id: str) -> Finding:
    return Finding(
        verdict=Verdict.UNKNOWN,
        operation_id=operation_id,
        category="",
        plr_site=None,
        reason="unsupported_tool",
    )


def _no_contract_derived(operation_id: str, *, detail: str = "") -> Finding:
    return Finding(
        verdict=Verdict.UNKNOWN,
        operation_id=operation_id,
        category="",
        plr_site=None,
        reason="no_contract_derived",
        detail=detail,
    )


def _unresolved_delegate(operation_id: str, *, detail: str = "") -> Finding:
    return Finding(
        verdict=Verdict.UNKNOWN,
        operation_id=operation_id,
        category="",
        plr_site=None,
        reason="unresolved_delegate",
        detail=detail,
    )


def _guard_predicate_unparsed(
    operation_id: str, *, plr_site: PlrSite | None, detail: str = ""
) -> Finding:
    return Finding(
        verdict=Verdict.UNKNOWN,
        operation_id=operation_id,
        category="",
        plr_site=plr_site,
        reason="guard_predicate_unparsed",
        detail=detail,
    )


def _loop_bounds_unknown(operation_id: str) -> Finding:
    return Finding(
        verdict=Verdict.UNKNOWN,
        operation_id=operation_id,
        category="",
        plr_site=None,
        reason="loop_bounds_unknown",
    )


#: 260904 (spec §15.4/§15.5/§15.7, increment 6, T31-2): the per-guard
#: evaluator's own Finding constructors -- same §3.3/§3.4 AST-resolvable-
#: reason discipline as every constructor above (a literal string at each
#: `Finding(...)` call site, never a shared `reason: str` parameter).


def _guard_safe(operation_id: str, *, plr_site: PlrSite | None, detail: str) -> Finding:
    return Finding(
        verdict=Verdict.SAFE,
        operation_id=operation_id,
        category="",
        plr_site=plr_site,
        reason="",
        detail=detail,
    )


def _guard_will_fail(operation_id: str, *, plr_site: PlrSite | None, detail: str) -> Finding:
    return Finding(
        verdict=Verdict.WILL_FAIL,
        operation_id=operation_id,
        category="precondition_state",
        plr_site=plr_site,
        reason="",
        detail=detail,
    )


def _guard_operand_unknown(operation_id: str, *, plr_site: PlrSite | None, detail: str) -> Finding:
    return Finding(
        verdict=Verdict.UNKNOWN,
        operation_id=operation_id,
        category="",
        plr_site=plr_site,
        reason="guard_operand_unknown",
        detail=detail,
    )


def _guard_env_dependent(operation_id: str, *, plr_site: PlrSite | None, detail: str) -> Finding:
    return Finding(
        verdict=Verdict.UNKNOWN,
        operation_id=operation_id,
        category="",
        plr_site=plr_site,
        reason="guard_env_dependent",
        detail=detail,
    )


def _finding_from_guard_result(
    operation_id: str,
    guard: dict[str, Any],
    result: "predicate.GuardResult",
) -> Finding:
    """Wraps a :func:`plr_sema.check.predicate.evaluate_guard` result into
    the `Finding` its verdict/reason pair calls for -- one of the tiny
    literal-reason constructors, dispatched by `(result.verdict,
    result.reason)`. `("unknown", "guard_predicate_unparsed")` reuses the
    SAME `_guard_predicate_unparsed` constructor `_finding_from_guard`
    (the pre-T31 blanket path) uses -- `nested Opaque` still means exactly
    what it always meant, just now reached through the evaluator's own
    §15.7 clause 1 rather than unconditionally."""
    plr_site = _plr_site_from_dict(guard.get("site"))
    condition = guard.get("condition")
    detail = condition if condition is not None else "<unconditional>"
    key = (result.verdict, result.reason)
    if key == ("safe", ""):
        return _guard_safe(operation_id, plr_site=plr_site, detail=detail)
    if key == ("will_fail", ""):
        return _guard_will_fail(operation_id, plr_site=plr_site, detail=detail)
    if key == ("unknown", "guard_operand_unknown"):
        return _guard_operand_unknown(operation_id, plr_site=plr_site, detail=detail)
    if key == ("unknown", "guard_env_dependent"):
        return _guard_env_dependent(operation_id, plr_site=plr_site, detail=detail)
    if key == ("unknown", "guard_predicate_unparsed"):
        return _guard_predicate_unparsed(operation_id, plr_site=plr_site, detail=detail)
    return _internal_error(
        operation_id, detail=f"predicate.evaluate_guard returned unrecognized {key!r}"
    )


#: 260902 (spec §10.3.3/§10.8, tip typestate increment): the
#: `channel_state_unknown`/`SAFE`/`WILL_FAIL` `Finding`s this increment adds
#: are constructed by `plr_sema.check.tipstate._finding_for_atom` -- its own
#: tiny, single-literal constructor, same §3.3/§3.4 AST-resolvable-reason
#: discipline as every constructor above, just living in the module that
#: owns the atom evaluator rather than here (§10.3.3's emission table has no
#: natural home among this module's per-*operation*-shaped reasons above,
#: all of which are UNKNOWN-only; tipstate's are the first SAFE/WILL_FAIL
#: constructors in the package).


def _internal_error(operation_id: str, *, detail: str = "") -> Finding:
    """Defensive fallback: a gap reason surfacing from
    ``derived_contracts.json`` that is neither of the two
    ``plr_sema.derive`` ever emits (``no_contract_derived`` /
    ``unresolved_delegate``, §7.2) would itself be a drift between
    ``plr_sema.derive`` and ``plr_sema.check``, not a fact about PLR --
    exactly what ``internal_error`` (§3.3: "analyzer bug; always paired with
    a telemetry emit") exists for.
    """
    return Finding(
        verdict=Verdict.UNKNOWN,
        operation_id=operation_id,
        category="",
        plr_site=None,
        reason="internal_error",
        detail=detail,
    )


def _finding_from_guard(operation_id: str, guard: dict[str, Any]) -> Finding:
    """Every guard becomes a ``guard_predicate_unparsed`` Finding in v1
    (round-4 remediation, B4: the former ``argument_not_static`` branch --
    which fired when a guard's ``free_vars`` intersected
    ``op.depends_on_params`` -- has been withdrawn from ``REASON_VOCABULARY``
    and is no longer constructed anywhere; see the module docstring).

    ``detail`` (round-4 remediation, m5): ``guard["condition"]`` being
    ``None`` means the guard fires UNCONDITIONALLY -- the predicate is
    ``TRUE``, not "no constraint" (§7.2's ``InlinedGuard.condition``: raw,
    unparsed strings, and ``None`` is a real value the survey emits, not a
    missing-field sentinel). The prior ``guard.get("condition") or ""``
    mapped BOTH ``None`` and an empty-string condition to ``detail = ""``,
    making the two indistinguishable in the emitted Finding -- unsound in
    the ``SAFE`` direction, and not merely cosmetic: 379 of 2,814 (13.5%) of
    survey findings, and 9 of the 119 guards in the shipped contract table,
    carry ``condition: null``. ``None`` now maps to the explicit sentinel
    string ``"<unconditional>"`` instead of being collapsed into ``""``.
    """
    plr_site = _plr_site_from_dict(guard.get("site"))
    condition = guard.get("condition")
    detail = condition if condition is not None else "<unconditional>"
    return _guard_predicate_unparsed(operation_id, plr_site=plr_site, detail=detail)


def _findings_for_gap(operation_id: str, gap: Any) -> Finding:
    gap_reason, gap_name = gap[0], gap[1]
    if gap_reason == "unresolved_delegate":
        return _unresolved_delegate(operation_id, detail=gap_name)
    if gap_reason == "no_contract_derived":
        return _no_contract_derived(operation_id, detail=gap_name)
    return _internal_error(
        operation_id, detail=f"unrecognized gap reason {gap_reason!r} for {gap_name!r}"
    )


def _findings_for_guards(
    operation_id: str,
    call: ir.Call,
    contract: dict[str, Any],
    consumed: frozenset[int],
    *,
    receiver_state: dict[str, Any] | None,
    resources_by_slot: dict[int, ir.Resource],
    env: frozenset[str],
    class_hierarchy: dict[str, frozenset[str]] | None,
    poisoned: bool,
    excludes_sites: list[PlrSite] | None,
) -> list[Finding]:
    """260904 (spec §15.4/§15.5/§15.7, increment 6, T31-2): every guard in
    ``contract["guards"]`` the tip family did not already consume is
    evaluated by :mod:`plr_sema.check.predicate` -- the pre-increment-6
    blanket ``guard_predicate_unparsed`` emission (``_finding_from_guard``,
    still used verbatim by nothing downstream of this function) is
    REPLACED, one-for-one, by the evaluator's own verdict/reason. A guard
    the volume family claims is never a `contract["guards"]` entry at all
    (it lives in the separate ``volume_guards`` list, §14.4's own
    ``derive/__main__.py`` disposition), so no additional dispatch/skip
    logic is needed for it here -- the family-dispatch rule §15.2 states is
    already structurally true of this loop.

    ``channel_kwarg``/``channels`` are computed ONCE per call (mirroring
    ``tipstate.evaluate_call``'s own poisoned-gating, §15.3's P3a hook) and
    threaded into every guard's evaluation rather than re-derived per
    guard. A tier-(iii) guard's site is folded into ``excludes_sites``
    (deduplicated) when a collector list was supplied (``None`` -- the
    default -- means "don't bother collecting", #4922's own additive-
    keyword-only precedent).
    """
    channel_kwarg: str | None = None
    channels: tuple[int, ...] | None = None
    if receiver_state is not None and not poisoned:
        channel_kwarg = receiver_state.get("channel_kwarg")
        channels = tipstate.channels_for_call(
            call, receiver_state.get("channel_default_param", {}), channel_kwarg
        )

    findings: list[Finding] = []
    for idx, guard in enumerate(contract.get("guards", ())):
        if idx in consumed:
            continue
        result = predicate.evaluate_guard(
            guard,
            call,
            contract,
            resources_by_slot,
            env=env,
            channel_kwarg=channel_kwarg,
            channels=channels,
            class_hierarchy=class_hierarchy,
            k_reachability_clear=guard.get("reachability_clear"),
        )
        findings.append(_finding_from_guard_result(operation_id, guard, result))
        if result.tier_iii and excludes_sites is not None:
            site = _plr_site_from_dict(guard.get("site"))
            if site is not None and site not in excludes_sites:
                excludes_sites.append(site)
    return findings


def _findings_for_call(
    operation_id: str,
    call: ir.Call,
    contracts: dict[str, Any],
    *,
    inside_loop: bool,
    receiver_states: dict[str, Any],
    resources_by_slot: dict[int, ir.Resource],
    walk: tipstate.TipWalk,
    vwalk: volumestate.VolumeWalk,
    env: frozenset[str],
    poisoned: bool,
    class_hierarchy: dict[str, frozenset[str]] | None = None,
    excludes_sites: list[PlrSite] | None = None,
) -> list[Finding]:
    """The per-``CALL`` body: exactly today's (pre-IR) per-operation logic
    (§11.4.1), re-keyed from an ``OperationNode`` to a ``CALL`` instruction
    -- ``op.receiver_type``/``op.method_name`` become
    ``call.receiver_type``/``call.method``; the loop test
    ``op.foreach_source is not None or op.foreach_body`` becomes "this pc is
    inside an open LOOP region" (``inside_loop``, computed by ``check_ir``'s
    recursive region walk, spec 260903 §12.3 -- true for a CALL nested
    under ANY ancestor LOOP, real or synthetic, regardless of intervening
    BRANCHes; unaffected by §12.3's L1/L2/L3 change to what else happens on
    a LOOP/BRANCH). T11: step 2 is a single contract-table lookup, not a
    ``SUPPORTED_TOOLS`` membership test followed by a second lookup -- see
    the module docstring's "``unsupported_tool``, redefined" section.

    260902 (spec §10, tip typestate increment): ``plr_sema.check.tipstate
    .evaluate_call`` runs BEFORE the ``guard_predicate_unparsed`` loop below
    and returns ``(tip_state_findings, consumed_own_guard_indices)`` --
    every own guard at a consumed index is SKIPPED in the
    ``guard_predicate_unparsed`` emission (§10.3.3: "the emission ...
    REPLACES, one-for-one" the old finding for that same guard), and every
    ``channel_guards`` entry that parsed is an ADDITIVE finding this
    operation never had before (no old finding to replace, since
    ``channel_guards`` did not exist pre-increment).

    260903 (spec §14, volume increment 5): ``plr_sema.check.volumestate
    .evaluate_call`` runs alongside tipstate's, purely ADDITIVELY -- a
    volume guard is never present in ``contract["guards"]``, so there is
    nothing for it to consume/replace. It runs for EVERY resolved contract,
    not only one with a nonempty ``volume_guards`` (V5's tip-cell lifecycle
    fires off ``channel_effect``, which ``pick_up_tips``/``drop_tips``
    contracts carry with no ``volume_guards`` at all).
    """
    if call.receiver_type is None:
        return [_receiver_type_unknown(operation_id)]

    key = f"{call.receiver_type}.{call.method}"
    contract = contracts.get(key)
    if contract is None:
        return [_unsupported_tool(operation_id)]

    tip_findings, consumed = tipstate.evaluate_call(
        operation_id, call, contract, receiver_states.get(call.receiver_type), walk, poisoned=poisoned
    )
    volume_findings = volumestate.evaluate_call(
        operation_id, call, contract, receiver_states.get(call.receiver_type), vwalk, env=env, poisoned=poisoned
    )

    findings: list[Finding] = [
        _findings_for_gap(operation_id, gap) for gap in contract.get("gaps", ())
    ]
    findings.extend(
        _findings_for_guards(
            operation_id,
            call,
            contract,
            consumed,
            receiver_state=receiver_states.get(call.receiver_type),
            resources_by_slot=resources_by_slot,
            env=env,
            class_hierarchy=class_hierarchy,
            poisoned=poisoned,
            excludes_sites=excludes_sites,
        )
    )
    findings.extend(tip_findings)
    findings.extend(volume_findings)
    if inside_loop:
        findings.append(_loop_bounds_unknown(operation_id))
    if not findings:
        # Round-4 remediation (B1/B2/§0(ii)): a resolved contract with zero
        # guards, zero gaps, and no loop must not silently produce an empty
        # finding list -- see the module docstring's note on why this was a
        # live soundness gap, not a deferred one.
        findings.append(
            _no_contract_derived(
                operation_id, detail="contract resolved with zero guards, zero gaps and no loop"
            )
        )
    return findings


#: Spec 260903 §12.3.5: L1's bounded-unroll cap and L2's fixpoint hard-pass
#: cap share one constant. Explicitly NOT a hand-maintained surface under
#: §0.1's classification (zero registry rows in `_hand_maintained.py`) --
#: it is a tuning parameter of THIS analyzer's own walk, every value of
#: which is sound (§12.3.5's own argument), not a fact about PLR that could
#: go stale.
_K = 8


def _is_synthetic_loop(instructions: tuple[ir.Instruction, ...], pc: int) -> bool:
    """Spec 260903 §12.3.3 (L3): a `LOOP` open is the whole-stream synthetic
    wrap iff `ir.lower_graph` emitted `WIDEN(reason="has_loops")`
    immediately before it -- the two are always adjacent by construction
    (`lower_graph`'s own prepend order, §11.4.1/§12.2.6), and no REAL region
    header ever carries that reason (`has_loops`/`has_conditionals` are
    GRAPH-level widen reasons, never a per-operation one, §11.1.4/§11.1.5).
    """
    return (
        pc > 0
        and isinstance(instructions[pc - 1], ir.Widen)
        and instructions[pc - 1].reason == "has_loops"
    )


def _is_synthetic_branch(instructions: tuple[ir.Instruction, ...], pc: int) -> bool:
    """Spec 260903 §12.3.6 (B3): the `BRANCH` analogue of
    :func:`_is_synthetic_loop` -- adjacency to `WIDEN(reason="has_conditionals")`.
    """
    return (
        pc > 0
        and isinstance(instructions[pc - 1], ir.Widen)
        and instructions[pc - 1].reason == "has_conditionals"
    )


def _with_iteration(finding: Finding, iteration: int) -> Finding:
    """Spec 260903 §12.3.4 point 2: L1's unroll iteration index goes into
    `Finding.detail`, prefixed to whatever detail the finding already
    carried (a guard condition, a gap name, or "") -- no new field, no wire
    change. `operation_id` is untouched (stays `str(pc)`, shared by every
    iteration's findings at that pc, §12.3.4 point 2's "conjoin, not
    merge" reading of `join`'s obligation order).
    """
    prefix = f"iteration {iteration}"
    detail = f"{prefix}: {finding.detail}" if finding.detail else prefix
    return dataclasses.replace(finding, detail=detail)


def check_ir(
    bytecode: ir.Bytecode,
    contracts: dict[str, Any],
    receiver_states: dict[str, Any] | None = None,
    *,
    env: frozenset[str] = frozenset(),
    class_hierarchy: dict[str, frozenset[str]] | None = None,
    excludes_sites: list[PlrSite] | None = None,
) -> tuple[Finding, ...]:
    """Spec §11.4.1 (260902) / §12.3 (260903, "region semantics for a
    region with a proved trip"): the analysis core. A structured,
    RECURSIVE walk over ``bytecode.instructions`` -- straight-line runs are
    still visited left to right with a program counter, but a ``LOOP``/
    ``BRANCH`` open is now handled by parsing the region's own boundaries
    (:func:`tipstate.region_bounds`) and recursing, rather than by a flat
    region-stack pass. Every ``CALL`` pc **visited** by the walk receives
    ``>=1`` ``Finding``; ``RESOURCE``/``LOOP``/``BRANCH``/``ELSE``/``END``/
    ``WIDEN`` receive none -- they are context, not obligations. A ``CALL``
    inside the body of a proved-``trip == 0`` ``LOOP`` is never visited at
    all (§12.3.4's ``OBLIGED(graph)`` exclusion (2) -- L1 unrolls
    ``min(0, K) = 0`` times) and therefore never receives a ``Finding``,
    which is what makes ``OBLIGED(graph)``, not ``{op.id for op in
    graph.operations if op.node_type is not REGION}``, the right-hand side
    of AC-6.4/AC-7.2/AC-11.7 (all three amended, §12.3.4).

    ``operation_id`` on every emitted ``Finding`` is still ``str(pc)`` --
    unrolling means one ``CALL`` pc can now be visited more than once, so
    one ``operation_id`` can carry more than one guard's worth of findings
    PER ITERATION; the iteration index is threaded into ``Finding.detail``
    (:func:`_with_iteration`), never into ``operation_id`` itself (§12.3.4
    point 2/3). ``check_graph`` relabels through
    ``bytecode.sideband["origin"]`` before constructing an ``AnalysisReport``.

    260902 (spec §10.5/§11.1.3, tip typestate increment): ``receiver_states``
    (the additive ``receiver_state`` top-level block, §10.2) threads a
    :class:`plr_sema.check.tipstate.TipWalk` through this same walk.
    ``None``/``{}`` (a pre-increment contract table, or a caller that never
    passes it -- AC-10.7/AC-11.12's fail-closed degrade) disables tip-state
    entirely: every receiver type is then simply absent from the mapping,
    so :func:`tipstate.evaluate_call` returns ``E5``'s empty result for
    every call, unchanged from pre-increment behavior.

    260903 (spec §12.3, region semantics): a REAL ``LOOP`` with a proved
    integer ``trip`` is visited ``min(trip, K)`` times, threading state from
    one iteration into the next (L1); if ``trip > K`` every receiver
    mentioned anywhere in the region is widened after the ``K``-th
    iteration (the tail widen). A REAL ``LOOP`` with ``trip is None``
    (an unprovable ``while``, or ``for`` over an un-proved extent) iterates
    to a fixpoint over the per-receiver, per-channel join, emitting
    findings from the FINAL (stabilizing) pass only, with a ``K``-pass hard
    cap that widens on overrun (L2). A REAL ``BRANCH`` walks both arms from
    the SAME entry state and joins the two post-states at the merge (B1);
    ``pred`` is never evaluated (B2). The blanket region-entry-and-exit
    widen of pre-260903 behaviour survives ONLY for a SYNTHETIC region --
    the whole-stream ``WIDEN(has_loops)``/``WIDEN(has_conditionals)`` wrap
    ``ir.lower_graph`` falls back to when the extractor emitted no real
    region (L3/B3). L3 additionally RETIRES the stale increment-2
    compensation that used to widen a ``CALL``'s own receiver merely for
    sitting immediately before a ``LOOP``/``BRANCH`` open -- once region
    headers are real (§12.2.2) that adjacency no longer identifies a region
    OWNER, so the rule fired on an unrelated preceding call and silently
    destroyed a real verdict with no diagnostic (round-1 O3; see
    ``tests/test_tip_typestate.py``'s ``test_ac_10_5a``/``test_ac_10_6_condition_expr_widens``,
    now updated to assert the retirement, and the dedicated
    ``call_before_unowned_region_graph.json`` fixture, AC-12.14(iv)).

    260903 (spec §14, volume increment 5): ``env`` (keyword-only, defaults
    to empty -- the same ``cache=`` precedent #4922 added to
    ``check_graph``'s signature, §14.6's normative box) threads the
    hypothesis set into every ``plr_sema.check.volumestate.evaluate_call``
    call. A ``plr_sema.check.volumestate.VolumeWalk`` (``vwalk``) is
    threaded through this same walk, alongside ``walk`` (the tip family's
    own), with its own region-entry/tail widen (V4) and its own
    branch-merge join (interval hull + ``tips_dirty`` OR) -- see
    ``widen_region``/``walk_branch``/``walk_loop`` below. A trip=``None``
    ``LOOP`` region does NOT run volume cells through the K-pass fixpoint
    join tip state uses (V4: the interval lattice has infinite height, so a
    fixpoint over it is not guaranteed to stabilize within any fixed pass
    count -- see §14.5's own non-termination counterexample) -- volume
    cells mentioned in such a region are widened to Top BOTH on entry and
    again after the (tip-state-only) fixpoint returns, so no precision
    ever survives a real ``while``/unproven ``for`` for the volume family,
    regardless of what happens to actually run inside it.
    """
    receiver_states = receiver_states or {}
    walk = tipstate.TipWalk()
    vwalk = volumestate.VolumeWalk()
    poisoned_slots = tipstate.disabled_receivers(bytecode.instructions, receiver_states)
    findings: list[Finding] = []
    instructions = bytecode.instructions
    n_instr = len(instructions)
    # 260904 (spec §15.4, increment 6, T31-2): the slot -> RESOURCE map
    # E-TYPE's `IsInstance` needs (declared `type`/`element_type` per
    # `Ref.slot`, §15.4's own citation of `ir.py:178-192`) -- built ONCE
    # here, over the same `bytecode.instructions` every RESOURCE op lives
    # in at the front of the stream (`lower_graph`/`lower_calls`), never
    # per-guard.
    resources_by_slot: dict[int, ir.Resource] = {
        instr.slot: instr for instr in instructions if isinstance(instr, ir.Resource)
    }

    def process_call(pc: int, instr: ir.Call, *, inside_loop: bool) -> list[Finding]:
        return list(
            _findings_for_call(
                str(pc),
                instr,
                contracts,
                inside_loop=inside_loop,
                receiver_states=receiver_states,
                resources_by_slot=resources_by_slot,
                walk=walk,
                vwalk=vwalk,
                env=env,
                class_hierarchy=class_hierarchy,
                excludes_sites=excludes_sites,
                poisoned=instr.receiver in poisoned_slots,
            )
        )

    def widen_region_volumes(open_pc: int) -> None:
        for cell in volumestate.region_cells(instructions, open_pc, contracts, receiver_states):
            vwalk.widen(cell)

    def widen_region(open_pc: int) -> None:
        receivers, _end_pc = tipstate.region_receivers(instructions, open_pc)
        for slot in receivers:
            walk.widen(slot)
        widen_region_volumes(open_pc)

    def walk_block(
        pc: int, stop_pc: int, *, inside_loop: bool, record: bool, iteration: int | None = None
    ) -> None:
        """Walk a straight-line run of instructions from ``pc`` to
        ``stop_pc`` (exclusive), recursing into any nested ``LOOP``/
        ``BRANCH`` region encountered. ``record`` gates whether a visited
        ``CALL``'s findings are kept (``False`` during an L2 fixpoint's
        exploratory, non-final passes -- the call is still evaluated for
        its STATE effect on ``walk``, only its findings are discarded).
        """
        while pc < stop_pc:
            instr = instructions[pc]
            if isinstance(instr, ir.Widen) and instr.reason == "depends_on_params":
                # Increment 1 §10.5 rule 3 ("dynamic arguments widen"),
                # unchanged by §12.3: scan forward past any further
                # `Widen`s to find the `Call` this one was computed for,
                # and widen that call's receiver BEFORE its own guards are
                # evaluated -- re-fires independently on every visit of
                # this pc (once per unrolled iteration / fixpoint pass),
                # which is correct: each visit is an independent
                # evaluation of a dynamically-argued call.
                lookahead = pc + 1
                while lookahead < n_instr and isinstance(instructions[lookahead], ir.Widen):
                    lookahead += 1
                if lookahead < n_instr and isinstance(instructions[lookahead], ir.Call):
                    walk.widen(instructions[lookahead].receiver)
                pc += 1
                continue
            if isinstance(instr, ir.Call):
                call_findings = process_call(pc, instr, inside_loop=inside_loop)
                if record:
                    if iteration is not None:
                        call_findings = [_with_iteration(f, iteration) for f in call_findings]
                    findings.extend(call_findings)
                pc += 1
                continue
            if isinstance(instr, ir.Loop):
                end_pc, _else_pc = tipstate.region_bounds(instructions, pc)
                walk_loop(pc, end_pc, record=record)
                pc = end_pc + 1
                continue
            if isinstance(instr, ir.Branch):
                end_pc, else_pc = tipstate.region_bounds(instructions, pc)
                walk_branch(
                    pc, else_pc, end_pc, inside_loop=inside_loop, record=record, iteration=iteration
                )
                pc = end_pc + 1
                continue
            # ir.Resource, ir.Else, any other ir.Widen: never a Finding
            # source and never a state-affecting instruction on their own.
            pc += 1

    def walk_loop(open_pc: int, end_pc: int, *, record: bool) -> None:
        loop = instructions[open_pc]
        assert isinstance(loop, ir.Loop)
        body_start = open_pc + 1
        if _is_synthetic_loop(instructions, open_pc):
            # L3 (§12.3.3): the blanket entry widen survives ONLY here.
            widen_region(open_pc)
            walk_block(body_start, end_pc, inside_loop=True, record=record)
            return
        if loop.trip is None:
            # V4 (§14.5): an unproven trip count means the interval domain
            # (infinite height) is not guaranteed to reach a fixpoint
            # within any fixed pass count -- unlike tip state (height 1),
            # which the fixpoint join below still runs normally. Volume
            # cells mentioned in the region go straight to Top, both
            # before AND after the tip-only fixpoint (a call inside the
            # region can still narrow a cell away from Top during a single
            # pass; the post-widen is what makes "every cell in the region
            # is Top after the region's END" true unconditionally, not
            # just as an artifact of however many passes tip state needed).
            widen_region_volumes(open_pc)
            walk_loop_fixpoint(open_pc, body_start, end_pc, record=record)
            widen_region_volumes(open_pc)
            return
        # L1 (§12.3.3): bounded unroll, min(trip, K) real iterations,
        # threading state from one into the next; findings on every one.
        n = min(loop.trip, _K)
        for i in range(n):
            walk_block(body_start, end_pc, inside_loop=True, record=record, iteration=i + 1)
        if loop.trip > _K:
            # The tail widen (§12.3.5): whatever K is, the remainder is
            # answered by a widen, which asserts nothing -- K can only move
            # findings between definite and UNKNOWN, never make one wrong.
            widen_region(open_pc)

    def walk_loop_fixpoint(open_pc: int, body_start: int, end_pc: int, *, record: bool) -> None:
        # L2 (§12.3.3): iterate sigma_{i+1} = sigma_i JOIN post(body, sigma_i)
        # to a stable loop-head state; findings are kept from the FINAL
        # (stabilizing) pass only -- every earlier pass is evaluated
        # against a state that is not yet a valid over-approximation of the
        # loop head, so a finding from it could assert a definite-failure
        # claim about a program that may take a different path on a later
        # real iteration (§12.3.3's own "not an optimisation" note). A
        # K-pass hard cap widens on overrun rather than looping forever.
        head = walk.snapshot()
        for _pass_index in range(_K):
            walk.restore(head)
            start_len = len(findings)
            walk_block(body_start, end_pc, inside_loop=True, record=record)
            pass_findings = findings[start_len:]
            del findings[start_len:]
            post = walk.snapshot()
            new_head = tipstate.join_walk_states(head, post)
            if new_head == head:
                findings.extend(pass_findings)
                walk.restore(new_head)
                return
            head = new_head
        # Cap reached without stabilizing: no pass is "the final pass" of a
        # converged walk, so none of their findings are trustworthy --
        # fail-closed, same discipline as everywhere else in this module.
        widen_region(open_pc)

    def walk_branch(
        open_pc: int,
        else_pc: int | None,
        end_pc: int,
        *,
        inside_loop: bool,
        record: bool,
        iteration: int | None,
    ) -> None:
        if _is_synthetic_branch(instructions, open_pc) or else_pc is None:
            # B3 (§12.3.6): no arm structure to walk -- widen at entry AND
            # exit, exactly pre-260903 behaviour. `else_pc is None` for a
            # non-synthetic BRANCH should not arise from any well-formed
            # `lower_graph` output (a real region always emits its own
            # ELSE, §12.2.2) -- this fallback keeps the walk total on a
            # malformed/fuzzed stream rather than raising.
            widen_region(open_pc)
            walk_block(
                open_pc + 1, end_pc, inside_loop=inside_loop, record=record, iteration=iteration
            )
            widen_region(open_pc)
            return
        # B1 (§12.3.6): arm-wise walk from the SAME entry state, joined at
        # the merge. A missing arm (empty true_branch/false_branch) simply
        # walks zero instructions, which leaves that arm's state identical
        # to the entry snapshot -- "a missing arm contributes sigma
        # unchanged" falls out of the walk rather than needing a special
        # case. `pred` (B2) is never read.
        entry = walk.snapshot()
        entry_v = vwalk.snapshot()
        walk_block(open_pc + 1, else_pc, inside_loop=inside_loop, record=record, iteration=iteration)
        true_states = walk.snapshot()
        true_v = vwalk.snapshot()
        walk.restore(entry)
        vwalk.restore(entry_v)
        walk_block(else_pc + 1, end_pc, inside_loop=inside_loop, record=record, iteration=iteration)
        false_states = walk.snapshot()
        false_v = vwalk.snapshot()
        walk.restore(tipstate.join_walk_states(true_states, false_states))
        vwalk.restore(volumestate.join_walk_states(true_v, false_v))

    walk_block(0, n_instr, inside_loop=False, record=True)
    return tuple(findings)


def _build_param_names(contracts: dict[str, Any]) -> dict[str, tuple[str, ...]]:
    """§11.2.4: the additive ``params`` key per contract entry
    (``plr_sema.derive``'s ``SurveyRecord.params``), reduced to the shape
    :func:`plr_sema.check.ir.lower_graph`'s ``param_names`` wants. Missing
    or absent ``params`` on an entry (a stale, pre-increment table, §11.2.4)
    degrades to "trust nothing" for that key -- ``.get()``, never a
    KeyError -- rather than raising (AC-11.12).
    """
    return {
        key: tuple(entry.get("params", ()))
        for key, entry in contracts.items()
        if entry.get("params")
    }


def _check(
    bytecode: ir.Bytecode,
    protocol_fqn: str,
    contracts_payload: dict[str, Any],
    *,
    env: frozenset[str] = frozenset(),
    class_hierarchy: dict[str, frozenset[str]] | None = None,
) -> AnalysisReport:
    contracts = contracts_payload.get("contracts", {})
    receiver_states = contracts_payload.get("receiver_state", {})
    stamp = _stamp_from_dict(contracts_payload["stamp"])

    excludes_sites: list[PlrSite] = []
    raw_findings = check_ir(
        bytecode,
        contracts,
        receiver_states,
        env=env,
        class_hierarchy=class_hierarchy,
        excludes_sites=excludes_sites,
    )
    origin = bytecode.sideband.get("origin", {})
    findings = ir.relabel_findings(raw_findings, origin)

    report = AnalysisReport(
        protocol_fqn=protocol_fqn,
        verdict=join(findings),
        findings=findings,
        stamp=stamp,
        # 260904 (spec §15.5, increment 6, T31-2): a pure annotation --
        # `join` above already ran over the flat finding multiset and never
        # reads this. `None` (not an empty `SoundnessScope`) when nothing
        # this analysis run visited was tier (iii), so an old reader that
        # never heard of `scope` sees exactly what it always saw.
        scope=SoundnessScope(excludes_sites=tuple(excludes_sites)) if excludes_sites else None,
    )
    # Round-4 remediation (M2): check_graph now actually emits telemetry --
    # previously nothing under check/ ever called plr_sema.telemetry.emit*,
    # despite §3.3:444's "internal_error ... always paired with a telemetry
    # emit" claim. Emitting every finding here (not just internal_error's)
    # makes that claim true for every reason, not just one -- emit() is a
    # process-global no-op by default (spec §4.1's AC-4.4), so this costs
    # nothing when no sink is attached.
    for finding in report.findings:
        emit_finding(finding, protocol_fqn=report.protocol_fqn, stamp=report.stamp)
    return report


def check_graph(
    graph_json: str,
    contracts_json: str,
    *,
    cache: cache_mod.CacheStore | None = None,
    env: frozenset[str] = frozenset(),
    class_hierarchy: dict[str, frozenset[str]] | None = None,
) -> AnalysisReport:
    """Round-1 entry point (spec §6.2), signature additive since #4922
    (§13.3.3, ``cache=`` keyword-only, defaulting to ``None``).
    ``graph_json``/``contracts_json`` are JSON strings, not pre-parsed
    objects -- both are ``json.loads``'d here and nowhere else. Never
    imports ``libcst``/``pylabrobot``/``pydantic``; never shells out.
    Emits every finding via ``plr_sema.telemetry`` (M2, round-4
    remediation) -- a no-op unless a sink is attached (§4.1), on BOTH the
    hit and the miss path (§13.3.2: a cache hit that skipped the emit would
    make the cache observable and falsify the purity premise the cache
    rests on).

    260902 (spec §11, SEMA-IR): the body is lower-then-check --
    ``json.loads`` both inputs, build ``param_names`` from the contract
    table's additive ``params`` key, :func:`plr_sema.check.ir.lower_graph`,
    :func:`check_ir`, relabel through the origin map, ``join``,
    ``AnalysisReport``. AC-11.6 pins that the shipped fixture's report does
    not move; AC-6.1 through AC-6.7 are untouched.

    #4922 (spec §13.3): with ``cache=None`` (the default), this is exactly
    the pre-#4922 body -- delegates to :func:`_check`, which stays pure and
    unchanged, and touches no file anywhere (AC-13.5). With a
    :class:`plr_sema.check.cache.CacheStore`, the read-through hook lives
    HERE, not in ``_check`` -- this function is the only one holding the
    raw ``contracts_json`` string :func:`plr_sema.check.ir.cache_key`
    hashes; ``_check`` receives only the already-parsed
    ``contracts_payload`` dict. On a hit, the cached PRE-relabel findings
    (§13.3.2's non-obvious half -- ``sideband``/``origin`` is excluded from
    ``bytecode_hash``, so two graphs differing only in operation ids share
    a key and a post-relabel entry would silently return the first graph's
    ids for the second) are relabelled through THIS graph's own
    ``sideband["origin"]``, exactly as a miss would be. On a miss, the
    normal pure computation runs once and its pre-relabel findings are
    stored under the key before relabelling.
    """
    payload = json.loads(graph_json)
    contracts_payload = json.loads(contracts_json)
    contracts = contracts_payload.get("contracts", {})
    param_names = _build_param_names(contracts)
    bytecode = ir.lower_graph(payload, param_names=param_names)

    if cache is None:
        return _check(
            bytecode, payload["protocol_fqn"], contracts_payload, env=env, class_hierarchy=class_hierarchy
        )

    receiver_states = contracts_payload.get("receiver_state", {})
    stamp = _stamp_from_dict(contracts_payload["stamp"])
    bc_hash = ir.bytecode_hash(bytecode)
    # 260903 (spec §14.6/§14.13 T27, backlog #4959): `env` is now threaded
    # into `cache_key` -- a cache entry is keyed by the HYPOTHESIS it was
    # computed under (`cache_key`'s fifth component, #4922's §11.3.3), not
    # just by bytecode/contracts/surface_identity/ir_version. A hit under
    # one `env` is therefore never served under another (AC-14.7's cache
    # clause): the default `env=frozenset()` reproduces every pre-T27 key
    # byte-for-byte (`tuple(sorted(frozenset()))  == ()`, unchanged from
    # #4922's own default), so no existing cache entry is invalidated by
    # this change -- it only PARTITIONS future entries that pass a
    # non-empty `env`, exactly as `ir.cache_key`'s own docstring and
    # §14.14 item 6 already describe.
    key = ir.cache_key(bc_hash, contracts_json, stamp, env=env)

    raw_findings = cache.get(key)
    # 260904 (spec §15.5, increment 6, T31-2): `SoundnessScope` is NOT
    # threaded through `CacheStore` (its value shape is `tuple[Finding,
    # ...]` only, §13.3's own cache-key/value contract, unchanged by this
    # increment) -- a cache HIT therefore reports `scope=None`, a
    # documented gap in the ANNOTATION only. `join`'s own verdict is
    # unaffected (computed from `findings`, which the cache faithfully
    # preserves either way); no soundness claim depends on `scope`.
    excludes_sites: list[PlrSite] | None = None
    if raw_findings is None:
        excludes_sites = []
        raw_findings = check_ir(
            bytecode,
            contracts,
            receiver_states,
            env=env,
            class_hierarchy=class_hierarchy,
            excludes_sites=excludes_sites,
        )
        methods = frozenset(
            instr.method for instr in bytecode.instructions if isinstance(instr, ir.Call)
        )
        cache.put(key, raw_findings, methods=methods)

    origin = bytecode.sideband.get("origin", {})
    findings = ir.relabel_findings(raw_findings, origin)
    report = AnalysisReport(
        protocol_fqn=payload["protocol_fqn"],
        verdict=join(findings),
        findings=findings,
        stamp=stamp,
        scope=SoundnessScope(excludes_sites=tuple(excludes_sites)) if excludes_sites else None,
    )
    for finding in report.findings:
        emit_finding(finding, protocol_fqn=report.protocol_fqn, stamp=report.stamp)
    return report
