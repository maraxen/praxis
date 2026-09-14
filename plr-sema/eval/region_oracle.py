"""Tier 2b (spec 260903 `260903_plr-sema-real-programs-increment.md`
§12.4.2, backlog #4880/T21): the region-fixture oracle -- EXECUTED ground
truth for `for`/`while`/`if` regions, produced by the instance-level
recorder in :mod:`region_recorder` and compared against the static side
through :func:`plr_sema.check.ir.lower_graph` / `plr_sema.check.check_ir`.

Pipeline per fixture (`plr-sema/eval/fixtures/regions/*.py`):

1. load the module (`LAYOUT`, `protocol`);
2. build a chatterbox deck (`verify.deck.build_setup`) under STRICT + both
   trackers, exactly like `training/verify/verifier.py:104-126`;
3. install a :class:`region_recorder.RegionRecorder` on `setup.machine`,
   `await setup.machine.setup()`, then `await protocol(setup.machine,
   **resources)` -- catching (and recording) the one exception that may
   propagate out;
4. extract the SAME fixture source out of process
   (`extract_runner.py` -- AC-12.16), inject a synthetic `setup` CALL at
   the front of the payload (this file's own `_inject_setup_op` -- see its
   docstring for why: the harness's real `setup()` call happens OUTSIDE
   the fixture source, at a line the extractor never sees, so the graph
   would otherwise never observe a reset at all and #4938's derived
   `entry_reset` effect would never fire), then `lower_graph` -> `check_ir`
   -> relabel;
5. join executed `(method, lineno, visit_index)` to static
   `(operation_id, iteration)` and compare, per spec §12.4.2/AC-12.17.

**The (now-fixed) `OperationNode.line_number` defect, backlog #4948.**
Every operation the extractor emitted used to carry `line_number == 0`
(`computation_graph_extractor.py`'s `_current_line` was initialized once,
in `__init__`, and never assigned again -- this tier's own join was the
first thing to depend on `line_number` being real, which is how the bug
was found). The join was written against the SPEC'S key shape,
`(method_name, lineno)`, from the start, and :func:`_join_key` was the one
place normalizing `lineno` to a constant `0` as a workaround -- see that
function's own docstring for the history. Now that the extractor gives
real line numbers, `_join_key` is an identity pass-through and the join
supports spec §12.4.2's actual rule ("at most one call site per method
per region body"), not just the previous, stronger-than-spec constraint
("at most one call site per PLR method in the whole fixture").
`two_sites_same_method.py` is the fixture that exercises this directly:
two `pick_up_tips` call sites in two different bodies, joined to two
different operations. :func:`_build_join_map` still raises loudly
(`region_recorder.DuplicateCallSiteError`) on a genuine same-body
same-method duplicate.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_EVAL_DIR = Path(__file__).resolve().parent
_BOOTSTRAP_FLAG = "PLR_SEMA_TIER2B_BOOTSTRAPPED"


def _bootstrap_into_training_env() -> None:
    """Same re-exec fix as `tier2_extractor.py`'s own bootstrap (260902,
    `ebd6b76d`'s pattern, duplicated rather than imported for the same
    reason `tier2_extractor.py`'s own docstring gives: an `import
    tier2_extractor` before this guard runs would re-exec into THAT
    script, discarding this script's own argv).
    """
    if os.environ.get(_BOOTSTRAP_FLAG):
        sys.stderr.write(
            "region_oracle: 'verify' still not importable after re-exec; "
            "run `uv sync` in the repo first\n"
        )
        raise SystemExit(3)
    env = dict(os.environ, **{_BOOTSTRAP_FLAG: "1"})
    venv_python = _REPO_ROOT / ".venv" / "bin" / "python"
    script_args = sys.argv[1:]
    if venv_python.is_file():
        argv = [str(venv_python), str(Path(__file__).resolve()), *script_args]
        os.execve(str(venv_python), argv, env)
    uv = shutil.which("uv")
    if uv is None:
        sys.stderr.write("region_oracle: neither .venv/bin/python nor uv found\n")
        raise SystemExit(3)
    argv = [uv, "run", "--offline", "--no-sync", "python",
            str(Path(__file__).resolve()), *script_args]
    os.chdir(_REPO_ROOT)
    os.execve(uv, argv, env)


if importlib.util.find_spec("verify") is None:
    _bootstrap_into_training_env()

import argparse
import asyncio
import contextlib
import dataclasses
import io
import json
import logging
import re
import time
from typing import Any

sys.path.insert(0, str(_EVAL_DIR))

from oracle_common import DEFAULT_CONTRACTS, param_names_from_contracts  # noqa: E402
from region_recorder import (  # noqa: E402
    DuplicateCallSiteError,
    RegionRecorder,
    VisitRecord,
    build_static_join_map,
)

log = logging.getLogger(__name__)

_EXTRACT_RUNNER = _EVAL_DIR / "extract_runner.py"
_FUNCTION_NAME = "protocol"
_RECEIVER_PARAM = "lh"
_SYNTHETIC_SETUP_ID = "op_setup_synthetic"

#: Fixture filename stem prefix -> shape label, for AC-12.17's per-shape
#: coverage report (at least one WILL_FAIL-at-raised-key fixture in each
#: of for/while/if).
_SHAPE_PREFIXES: tuple[tuple[str, str], ...] = (
    ("for_", "for"),
    ("while_", "while"),
    ("if_", "if"),
    ("nested_", "nested"),
    ("range_zero", "range_zero"),
    ("continue_", "continue"),
    ("break_", "break"),
    ("straightline_", "straightline"),
)

#: Fixtures whose EXECUTED iteration count is expected, by design, not to
#: equal a region's proved trip -- `break_fixture.py`'s own docstring
#: explains why (A-EARLY-EXIT: a proved trip of 3 with only 1 real
#: execution). Named here, not inferred, because inferring "this fixture
#: contains a break" would need its own AST scan for a fact the fixture's
#: own docstring already states in prose.
_TRIP_CHECK_EXEMPT: frozenset[str] = frozenset({"break_fixture"})

_ITERATION_RE = re.compile(r"^iteration (\d+): ")


def _shape_of(stem: str) -> str:
    for prefix, shape in _SHAPE_PREFIXES:
        if stem.startswith(prefix):
            return shape
    return "other"


def parse_iteration(detail: str) -> int | None:
    """§12.3.4 point 2: the unrolled iteration index is prefixed to
    ``Finding.detail`` as ``"iteration N: "`` -- parse it back out.
    ``None`` for a finding with no prefix (a fixpoint pass's final-pass
    finding, a branch arm's own finding with no enclosing loop, or a
    straight-line call).
    """
    m = _ITERATION_RE.match(detail)
    return int(m.group(1)) if m else None


def _lazy_ir():
    sys.path.insert(0, str(_REPO_ROOT / "plr-sema" / "src"))
    from plr_sema.check import ir as _ir

    return _ir


def _lazy_check():
    sys.path.insert(0, str(_REPO_ROOT / "plr-sema" / "src"))
    from plr_sema import check as _check
    from plr_sema.check._supported_tools import SUPPORTED_TOOLS
    from plr_sema.verdict import Verdict, join

    return _check, SUPPORTED_TOOLS, Verdict, join


# ---------------------------------------------------------------------------
# Static side: extract -> inject setup -> lower -> check -> relabel
# ---------------------------------------------------------------------------


def _inject_setup_op(payload: dict[str, Any]) -> dict[str, Any]:
    """Prepend a synthetic ``setup`` CALL operation to the extracted
    graph payload -- the graph-payload analogue of what
    ``oracle_common.calls_from_plr_kwargs`` does for the ``lower_calls``
    path (spec 260903 #4938's row: "plr-sema/eval/ prepends the
    scaffolding reset call ... with origin == 'setup'"), adapted here to
    the ``lower_graph`` payload shape because tier 2b goes through
    ``lower_graph``, not ``lower_calls``.

    **Why injection, not a literal ``await lh.setup()`` line in the
    fixture source (§12.4.2's other offered option).** The harness (see
    :func:`run_fixture`) calls ``await setup.machine.setup()`` exactly
    once, OUTSIDE the fixture body, mirroring
    ``training/verify/verifier.py``'s own "DeckFactory setup -> await
    lh.setup() -> execute" run pattern precisely (this file's own
    docstring quotes it). Also writing ``await lh.setup()`` as the
    fixture's own first statement would make it run TWICE at runtime, and
    the recorder would record its harness-side call at the HARNESS's own
    source line, not any line inside the fixture -- a call site the
    static side could never join against regardless. Injecting a
    synthetic op instead keeps the fixture executing setup() exactly once
    (matching the harness's real, single call) while still giving
    ``check_ir``'s E6 (#4938's derived reset effect) a CALL to observe:
    E6 only checks ``call.method == entry_reset.method`` (`"setup"`,
    `derived_contracts.json`'s own `receiver_state.LiquidHandler
    .entry_reset`), never the call's line or position, so a synthetic
    op ahead of every real one is sufficient and never itself compared
    (§12.4.2's join never looks up a `(method_name, lineno)` for
    `"setup"` -- no fixture ever calls it).
    """
    operations = list(payload.get("operations") or ())
    setup_op = {
        "id": _SYNTHETIC_SETUP_ID,
        "line_number": 0,
        "method_name": "setup",
        "receiver_variable": _RECEIVER_PARAM,
        "receiver_type": "LiquidHandler",
        "arguments": {},
        "node_type": "static",
        "preconditions": [],
        "creates_state": [],
        "depends_on_params": [],
        "foreach_source": None, "foreach_body": [], "trip": None,
        "condition_expr": None, "true_branch": [], "false_branch": [],
    }
    new_payload = dict(payload)
    new_payload["operations"] = [setup_op, *operations]
    execution_order = list(payload.get("execution_order") or ())
    if execution_order:
        new_payload["execution_order"] = [_SYNTHETIC_SETUP_ID, *execution_order]
    return new_payload


def _extract_graph_payload(
    fixture_path: Path, *, cache_dir: Path, runner_python: str,
) -> dict[str, Any]:
    out_path = Path(tempfile.mktemp(suffix=".json", dir=str(cache_dir)))
    try:
        proc = subprocess.run(
            [runner_python, str(_EXTRACT_RUNNER), "--source", str(fixture_path),
             "--function", _FUNCTION_NAME, "--out", str(out_path), "--cache-dir", str(cache_dir)],
            capture_output=True, text=True, timeout=60,
        )
        if proc.returncode != 0 or not out_path.is_file():
            raise RuntimeError(
                f"extract_runner failed rc={proc.returncode} stderr={proc.stderr[-2000:]}"
            )
        payload = json.loads(out_path.read_text(encoding="utf-8"))
    finally:
        out_path.unlink(missing_ok=True)
    if "error" in payload:
        raise RuntimeError(f"extractor: {payload['error']}")
    return payload


def _join_key(method: str, lineno: int) -> tuple[str, int]:
    """The join key spec §12.4.2 specifies: `(method_name, lineno)`.

    **History (backlog #4948).** Until `computation_graph_extractor.py`'s
    `OperationNode.line_number` was fixed, this function normalized
    `lineno` to a constant `0` on both sides -- `_current_line` was
    assigned once in `ComputationGraphExtractor.__init__` and never again,
    so every extracted operation carried `line_number == 0`, while
    `sys._getframe(1).f_lineno` on the EXECUTED side
    (`region_recorder.py`) read a real, distinct CPython frame line per
    call site. A literal `(method, real_lineno)` executed key could never
    match a `(method, 0)` static key, so the join degraded to
    `method_name` alone -- safe only because every fixture in
    `plr-sema/eval/fixtures/regions/` upheld a STRONGER constraint than
    spec §12.4.2's own ("at most one call site per method per region
    body"): at most one call site per PLR method in the WHOLE fixture.

    Now that `line_number` is real, this is the identity pass-through the
    docstring above always said it would become -- kept as a named
    function (rather than inlined at both call sites) so a future
    normalization need has one obvious place to live, and so
    `two_sites_same_method.py` (two DIFFERENT `pick_up_tips` call sites in
    two DIFFERENT bodies -- exactly the case the old constant-`0` version
    could never join) has something to test against directly.
    """
    return (method, lineno)


def _build_join_map(bytecode, ir_mod) -> dict[tuple[str, int], str]:
    """``(method_name, lineno) -> operation_id`` over every real (non-
    synthetic-setup, non-``REGION``) ``CALL`` in the bytecode, built from
    ``sideband["span"]``/``sideband["origin"]`` exactly as spec §12.4.2
    directs ("the executed key ... therefore joins to the static key
    (CALL.method, sideband['span'][pc], iteration), and
    sideband['origin'][pc] converts the pc to the graph operation id").
    Raises :class:`region_recorder.DuplicateCallSiteError` (AC-12.17(iii))
    on a genuine collision. Keys are routed through :func:`_join_key` --
    see its docstring for why.
    """
    span = bytecode.sideband.get("span", {})
    origin = bytecode.sideband.get("origin", {})
    triples: list[tuple[str, int, str]] = []
    for pc, instr in enumerate(bytecode.instructions):
        if getattr(instr, "op", None) != "CALL":
            continue
        if instr.method == "setup":
            continue  # the synthetic reset -- never a join target (see _inject_setup_op)
        lineno = span.get(pc)
        if lineno is None:
            continue
        operation_id = origin.get(pc)
        if operation_id is None:
            continue
        method, lineno = _join_key(instr.method, lineno)
        triples.append((method, lineno, operation_id))
    return build_static_join_map(triples)


@dataclasses.dataclass
class StaticVerdicts:
    #: operation_id -> {iteration_or_None: [Finding, ...]}
    by_op: dict[str, dict[int | None, list[Any]]]


def _group_static_findings(findings) -> StaticVerdicts:
    by_op: dict[str, dict[int | None, list[Any]]] = {}
    for f in findings:
        iteration = parse_iteration(f.detail)
        by_op.setdefault(f.operation_id, {}).setdefault(iteration, []).append(f)
    return StaticVerdicts(by_op)


def _verdict_at(static: StaticVerdicts, join_fn, op_id: str, iteration: int):
    """The static verdict to compare one executed visit against.

    An EXPLICIT per-iteration finding group (L1 unroll) wins when present;
    otherwise a NO-PREFIX group (fixpoint's final pass, a branch arm with
    no enclosing loop, or straight-line) is broadcast across every
    executed iteration of that operation -- spec §12.3.4 point 2's own
    reading (a fixpoint's single converged verdict must be sound against
    EVERY real iteration, not just the first). ``None`` when neither
    exists (no static claim at all for this key).
    """
    per_iter = static.by_op.get(op_id)
    if per_iter is None:
        return None
    if iteration in per_iter:
        return join_fn(tuple(per_iter[iteration]))
    if None in per_iter:
        return join_fn(tuple(per_iter[None]))
    return None


def _static_report(
    payload: dict[str, Any], contracts_payload: dict[str, Any], param_names, ir_mod, check_mod,
    *, env: frozenset[str] = frozenset(),
):
    injected = _inject_setup_op(payload)
    bytecode = ir_mod.lower_graph(injected, param_names=param_names)
    contracts = contracts_payload.get("contracts", {})
    receiver_states = contracts_payload.get("receiver_state", {})
    raw_findings = check_mod.check_ir(bytecode, contracts, receiver_states, env=env)
    findings = ir_mod.relabel_findings(raw_findings, bytecode.sideband.get("origin", {}))
    join_map = _build_join_map(bytecode, ir_mod)
    static = _group_static_findings(findings)
    proved_trips = _proved_trip_loops(injected)
    return bytecode, findings, join_map, static, proved_trips


def _proved_trip_loops(payload: dict[str, Any]) -> dict[str, tuple[int, tuple[str, ...]]]:
    """``{region_op_id: (trip, (direct_child_op_id, ...))}`` for every
    ``REGION`` header carrying a proved INTEGER ``trip`` (``for``-shaped
    loops only -- ``while`` always lowers ``trip=None``, spec §12.2.3).
    Used only for the "executed iteration count equals the proved trip"
    check (AC-12.17); direct children only (not recursive) is sufficient
    for every fixture in this tier's set (no doubly-nested proved loop).
    """
    out: dict[str, tuple[int, tuple[str, ...]]] = {}
    for op in payload.get("operations") or ():
        if op.get("node_type") == "region" and isinstance(op.get("trip"), int):
            out[op["id"]] = (op["trip"], tuple(op.get("foreach_body") or ()))
    return out


# ---------------------------------------------------------------------------
# Executed side: load fixture, build deck, install recorder, run
# ---------------------------------------------------------------------------


def _load_fixture_module(path: Path):
    spec = importlib.util.spec_from_file_location(f"region_fixture_{path.stem}", path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"cannot load fixture module {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def _run_fixture_execution(
    protocol_fn, layout_dict: dict[str, Any], supported_tools,
) -> tuple[list[VisitRecord], str | None, bool]:
    """Returns ``(records, raised, volume_tracking_observed)``. 260903
    (spec §14.6, volume increment 5, round-1 O5, T27, backlog #4959): the
    third element is the `does_volume_tracking()` hypothesis, observed from
    INSIDE the window `set_volume_tracking(True)` opens below -- never from
    outside it, which is what a later process-wide observation would have
    raced (the very non-determinism O5 found: the OLD `finally` below
    restored strictness only, so the tracking flags leaked and a
    process-wide read after the first fixture returned `True` regardless of
    which env this fixture's OWN static side should get). The `finally` now
    restores the tracking flags it sets, closing that leak.
    """
    from pylabrobot.liquid_handling.strictness import Strictness, get_strictness, set_strictness
    from pylabrobot.resources import set_tip_tracking, set_volume_tracking
    from pylabrobot.resources.tip_tracker import does_tip_tracking
    from pylabrobot.resources.volume_tracker import does_volume_tracking
    from verify.deck import DeckLayout, build_setup

    layout = DeckLayout(**layout_dict) if layout_dict else DeckLayout()
    setup = build_setup("LiquidHandlerChatterboxBackend", layout)

    old_strictness = get_strictness()
    old_volume_tracking = does_volume_tracking()
    old_tip_tracking = does_tip_tracking()
    recorder = RegionRecorder(setup.machine, supported_tools)
    raised: str | None = None
    volume_tracking_observed = False
    buf = io.StringIO()
    try:
        set_strictness(Strictness.STRICT)
        set_volume_tracking(True)
        set_tip_tracking(True)
        # Observed HERE, inside the window this try just opened -- see the
        # docstring above.
        volume_tracking_observed = does_volume_tracking()
        with contextlib.redirect_stdout(buf):
            await setup.machine.setup()
            recorder.install()
            try:
                import inspect

                sig_params = list(inspect.signature(protocol_fn).parameters)
                kwargs = {
                    name: setup.resources[name]
                    for name in sig_params[1:]  # [0] is always `lh`
                    if name in setup.resources
                }
                try:
                    await protocol_fn(setup.machine, **kwargs)
                except Exception as e:
                    raised = f"{type(e).__name__}: {e}"
            finally:
                recorder.uninstall()
                with contextlib.suppress(Exception):
                    await setup.machine.stop()
    finally:
        set_strictness(old_strictness)
        set_volume_tracking(old_volume_tracking)
        set_tip_tracking(old_tip_tracking)

    return recorder.records, raised, volume_tracking_observed


# ---------------------------------------------------------------------------
# Per-fixture comparison
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class UnsoundRow:
    fixture: str
    method: str
    lineno: int
    visit_index: int
    operation_id: str
    outcome: str
    static_verdict: str


@dataclasses.dataclass
class FixtureOutcome:
    name: str
    shape: str
    status: str  # "compared" | "harness_error"
    detail: str | None = None
    raised: str | None = None
    raised_key: tuple[str, int, int] | None = None
    static_verdict_at_raised: str | None = None
    will_fail_at_raised: bool = False
    unsound_rows: list[UnsoundRow] = dataclasses.field(default_factory=list)
    uncovered_keys: list[tuple[str, int, int]] = dataclasses.field(default_factory=list)
    trip_checks: list[dict[str, Any]] = dataclasses.field(default_factory=list)
    n_operations: int = 0
    n_findings: int = 0


def _volume_slice_summary(outcomes: list[FixtureOutcome]) -> dict[str, int]:
    """260903 (spec §14.9/§14.13 T28, volume increment 5, backlog #4960):
    `{volume_fixtures, volume_unsound, volume_will_fail_fired}` -- a NAMED
    SLICE of `region_fixtures`/`region_unsound`/`region_will_fail_fired`
    restricted to the `volume_*` fixtures, additive to (not a second run
    over) the totals `main` already computes over every outcome. Sliced by
    filename prefix, the same discrimination `_shape_of` already uses for
    its own prefix table, rather than a second AST/contract scan -- these
    are this module's OWN fixtures, so the prefix is a fact about the file
    the module itself wrote, not a guess about fixture content. A standalone
    function (rather than inlined in `main`) so it is testable directly
    against synthetic `FixtureOutcome`s, with no subprocess extraction and
    no chatterbox execution.
    """
    volume_outcomes = [o for o in outcomes if o.name.startswith("volume_")]
    return {
        "volume_fixtures": len(volume_outcomes),
        "volume_unsound": sum(len(o.unsound_rows) for o in volume_outcomes),
        "volume_will_fail_fired": sum(1 for o in volume_outcomes if o.will_fail_at_raised),
    }


def _trip_agreement(
    proved_trips: dict[str, tuple[int, tuple[str, ...]]],
    join_map: dict[tuple[str, int], str],
    executed_by_key: dict[tuple[str, int], list[VisitRecord]],
    fixture_name: str,
) -> list[dict[str, Any]]:
    """One entry per proved-trip loop region: ``{region_id, trip,
    executed}`` -- ``executed`` is the max visit_index observed among the
    region's direct-child call operations, or 0 if none were ever
    visited. `break_fixture` is excluded by name (see
    `_TRIP_CHECK_EXEMPT`'s own docstring).
    """
    if fixture_name in _TRIP_CHECK_EXEMPT:
        return []
    op_id_to_key = {op_id: key for key, op_id in join_map.items()}
    out: list[dict[str, Any]] = []
    for region_id, (trip, children) in proved_trips.items():
        executed = 0
        for child_id in children:
            key = op_id_to_key.get(child_id)
            if key is None:
                continue
            records = executed_by_key.get(key) or []
            executed = max(executed, max((r.visit_index for r in records), default=0))
        out.append({"region_id": region_id, "trip": trip, "executed": executed})
    return out


def run_fixture(
    fixture_path: Path, *, contracts_payload: dict[str, Any], param_names, ir_mod, check_mod,
    supported_tools, join_fn, will_fail_verdict, safe_verdict,
    cache_dir: Path, runner_python: str,
) -> FixtureOutcome:
    name = fixture_path.stem
    shape = _shape_of(name)
    module = _load_fixture_module(fixture_path)
    layout_dict = dict(getattr(module, "LAYOUT", {}) or {})
    protocol_fn = module.protocol

    try:
        records, raised, volume_tracking_observed = asyncio.run(
            _run_fixture_execution(protocol_fn, layout_dict, supported_tools)
        )
    except Exception as e:  # pragma: no cover - defensive, a harness-level failure
        return FixtureOutcome(name, shape, "harness_error", detail=f"execution:{e}")

    try:
        payload = _extract_graph_payload(fixture_path, cache_dir=cache_dir, runner_python=runner_python)
    except Exception as e:
        return FixtureOutcome(name, shape, "harness_error", detail=f"extract:{e}")

    # 260903 (spec §14.6/§14.11, volume increment 5, T27): `env`, built from
    # the executed side's OWN in-window observation above -- the NAME comes
    # from the callable's `__name__`, never a typed string.
    from pylabrobot.resources.volume_tracker import does_volume_tracking

    env = frozenset({does_volume_tracking.__name__}) if volume_tracking_observed else frozenset()

    try:
        bytecode, findings, join_map, static, proved_trips = _static_report(
            payload, contracts_payload, param_names, ir_mod, check_mod, env=env,
        )
    except DuplicateCallSiteError as e:
        return FixtureOutcome(name, shape, "harness_error", detail=f"duplicate_call_site:{e}")
    except Exception as e:
        return FixtureOutcome(name, shape, "harness_error", detail=f"static:{e}")

    executed_by_key: dict[tuple[str, int], list[VisitRecord]] = {}
    for r in records:
        executed_by_key.setdefault(_join_key(r.method, r.lineno), []).append(r)

    outcome = FixtureOutcome(
        name, shape, "compared", raised=raised,
        n_operations=len(payload.get("operations") or ()), n_findings=len(findings),
    )

    for join_key, key_records in executed_by_key.items():
        op_id = join_map.get(join_key)
        for record in key_records:
            # Reported with the record's own REAL lineno (evidence/debug
            # value); the LOOKUP above used the normalized `join_key` --
            # see `_join_key`'s docstring for why the two differ today.
            real_key = (record.method, record.lineno, record.visit_index)
            if op_id is None:
                outcome.uncovered_keys.append(real_key)
                continue
            verdict = _verdict_at(static, join_fn, op_id, record.visit_index)
            if verdict is None:
                outcome.uncovered_keys.append(real_key)
                continue
            unsound = (
                (verdict == safe_verdict and record.outcome.startswith("raised:"))
                or (verdict == will_fail_verdict and record.outcome == "ran_ok")
            )
            if unsound:
                outcome.unsound_rows.append(
                    UnsoundRow(
                        name, record.method, record.lineno, record.visit_index, op_id,
                        record.outcome, verdict.value,
                    )
                )
            if record.outcome.startswith("raised:"):
                outcome.raised_key = real_key
                outcome.static_verdict_at_raised = verdict.value
                outcome.will_fail_at_raised = verdict == will_fail_verdict

    outcome.trip_checks = _trip_agreement(proved_trips, join_map, executed_by_key, name)
    return outcome


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--fixtures", type=Path, required=True, help="directory of *.py region fixtures")
    ap.add_argument("--contracts", type=Path, default=DEFAULT_CONTRACTS)
    ap.add_argument("--report", type=Path, required=True)
    ap.add_argument("--cache-dir", type=Path, default=None)
    ap.add_argument(
        "--runner-python", type=str, default=None,
        help="interpreter to invoke extract_runner.py with (default: this process's own)",
    )
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    ir_mod = _lazy_ir()
    check_mod, supported_tools, verdict_cls, join_fn = _lazy_check()
    contracts_json = args.contracts.read_text(encoding="utf-8")
    contracts_payload = json.loads(contracts_json)
    param_names = param_names_from_contracts(contracts_json)
    runner_python = args.runner_python or sys.executable

    cache_dir = args.cache_dir or Path(tempfile.gettempdir()) / "plr_sema_tier2b_extract"
    cache_dir.mkdir(parents=True, exist_ok=True)

    fixture_paths = sorted(args.fixtures.glob("*.py"))
    if not fixture_paths:
        log.error("no fixtures found under %s", args.fixtures)
        return 3

    t0 = time.monotonic()
    outcomes: list[FixtureOutcome] = []
    for path in fixture_paths:
        outcome = run_fixture(
            path, contracts_payload=contracts_payload, param_names=param_names,
            ir_mod=ir_mod, check_mod=check_mod, supported_tools=supported_tools,
            join_fn=join_fn, will_fail_verdict=verdict_cls.WILL_FAIL, safe_verdict=verdict_cls.SAFE,
            cache_dir=cache_dir, runner_python=runner_python,
        )
        outcomes.append(outcome)
        log.info(
            "%-40s shape=%-12s status=%-14s raised=%s unsound=%d will_fail_at_raised=%s",
            outcome.name, outcome.shape, outcome.status, outcome.raised,
            len(outcome.unsound_rows), outcome.will_fail_at_raised,
        )

    elapsed = time.monotonic() - t0

    region_unsound = sum(len(o.unsound_rows) for o in outcomes)
    region_will_fail_fired = sum(1 for o in outcomes if o.will_fail_at_raised)
    volume_slice = _volume_slice_summary(outcomes)
    volume_fixtures = volume_slice["volume_fixtures"]
    volume_unsound = volume_slice["volume_unsound"]
    volume_will_fail_fired = volume_slice["volume_will_fail_fired"]
    shapes_with_will_fail = {o.shape for o in outcomes if o.will_fail_at_raised}
    per_shape_coverage = {
        shape: (shape in shapes_with_will_fail)
        for shape in ("for", "while", "if")
    }
    trip_mismatches = [
        {"fixture": o.name, **check}
        for o in outcomes
        for check in o.trip_checks
        if check["executed"] != check["trip"]
    ]
    harness_errors = [o for o in outcomes if o.status == "harness_error"]

    summary_flat = {
        # §12.4.4's own 8 named fields (shared sidecar covering tier 2a and
        # tier 2b -- see tier2_extractor.bth.toml). This harness (tier 2b
        # only) does not itself compute the tier-2a-specific fields
        # (bytecode_divergences_extractor/renderer, rows_normalised) --
        # they default to 0 here; tier2_extractor.py's own run publishes
        # the real values for those.
        "rows": len(outcomes),
        "operations": sum(o.n_operations for o in outcomes),
        "bytecode_divergences_extractor": 0,
        "bytecode_divergences_renderer": 0,
        "region_fixtures": len(outcomes),
        "region_unsound": region_unsound,
        "region_will_fail_fired": region_will_fail_fired,
        "rows_normalised": 0,
        # tier-2b-specific fields, additive to §12.4.4's named list.
        "region_trip_mismatches": len(trip_mismatches),
        "region_harness_errors": len(harness_errors),
        "region_uncovered_keys": sum(len(o.uncovered_keys) for o in outcomes),
        "elapsed_seconds": elapsed,
        # 260903 (spec §14.9/§14.13 T28, volume increment 5, backlog #4960):
        # the `volume_*` fixture slice's own counts -- see the comment above
        # this dict's construction for why these are a slice, not a second
        # total.
        "volume_fixtures": volume_fixtures,
        "volume_unsound": volume_unsound,
        "volume_will_fail_fired": volume_will_fail_fired,
    }

    report = {
        "summary_flat": summary_flat,
        "per_shape_coverage": per_shape_coverage,
        "trip_mismatches": trip_mismatches,
        "harness_errors": [{"fixture": o.name, "detail": o.detail} for o in harness_errors],
        "unsound_rows": [
            dataclasses.asdict(row) for o in outcomes for row in o.unsound_rows
        ],
        "fixtures": [
            {
                "name": o.name,
                "shape": o.shape,
                "status": o.status,
                "raised": o.raised,
                "raised_key": o.raised_key,
                "static_verdict_at_raised": o.static_verdict_at_raised,
                "will_fail_at_raised": o.will_fail_at_raised,
                "n_unsound": len(o.unsound_rows),
                "n_uncovered": len(o.uncovered_keys),
                "trip_checks": o.trip_checks,
                "n_operations": o.n_operations,
                "n_findings": o.n_findings,
            }
            for o in outcomes
        ],
    }
    args.report.write_text(json.dumps(report, indent=2))
    log.info("Report written to %s", args.report)

    bth_path = os.environ.get("BTH_RESULTS_PATH")
    if bth_path:
        Path(bth_path).write_text(json.dumps(summary_flat))

    log.info(
        "summary: fixtures=%d region_unsound=%d region_will_fail_fired=%d "
        "per_shape=%s trip_mismatches=%d harness_errors=%d elapsed=%.1fs "
        "volume_fixtures=%d volume_unsound=%d volume_will_fail_fired=%d",
        len(outcomes), region_unsound, region_will_fail_fired, per_shape_coverage,
        len(trip_mismatches), len(harness_errors), elapsed,
        volume_fixtures, volume_unsound, volume_will_fail_fired,
    )

    # AC-12.17: zero unsound rows, at least one WILL_FAIL-at-raised-key
    # fixture per shape (for/while/if), executed-trip agreement for every
    # non-exempt proved-trip fixture, and no harness-level failures.
    ok = (
        region_unsound == 0
        and all(per_shape_coverage.values())
        and not trip_mismatches
        and not harness_errors
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
