"""Unit tests for tier 2 (spec 260903 §12.4, backlog #4880/T21).

**Tier 2a** (§12.4.1): render one executed row -> extract out of process
-> `lower_graph` -> compare bytecode against tier 1's own `lower_calls`
output. AC-12.15 (the two lowerings agree, and the reset agrees too) and
AC-12.16 (the runner is out of process and the import boundary holds) are
the gate.

**Tier 2b** (§12.4.2, T21): the `region_recorder`/`region_oracle` classes
at the bottom of this file -- an instance-level method recorder, the
executed-vs-static `(operation, iteration)` join, and one end-to-end run
of the smallest `for`-shaped region fixture against a real chatterbox
deck. AC-12.17 (executed ground truth for regions) and AC-12.18 (the run
is bathos-tracked) are the gate.

Unlike `plr-sema/tests/test_oracle_replay.py`'s tests, this file freely
imports `praxis` directly (test files are outside AC-12.16's scan scope,
which is `plr-sema/src/` and `plr-sema/eval/` only) so the extractor can
be exercised in-process where that is simpler, alongside a dedicated
subprocess test for the actual out-of-process contract.
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = REPO_ROOT / "plr-sema" / "eval"
SRC_ROOT = REPO_ROOT / "plr-sema" / "src"
RUNNER_MODULE = EVAL_DIR / "extract_runner.py"

sys.path.insert(0, str(EVAL_DIR))

import region_oracle  # noqa: E402
from oracle_common import (  # noqa: E402
    DEFAULT_CONTRACTS,
    calls_from_plr_kwargs,
    lower_row_calls,
    param_names_from_contracts,
    resources_from_example,
)
from region_recorder import (  # noqa: E402
    DuplicateCallSiteError,
    RegionRecorder,
    build_static_join_map,
)
from render_protocol import (  # noqa: E402
    RESIDUAL_UNKNOWN_RESOURCE,
    RESIDUAL_UNRENDERABLE_VALUE_KIND,
    classify_residual_reason,
    render_protocol,
)
from tier2_extractor import _extract_calls, _seq_len, compare_bytecode  # noqa: E402

sys.path.insert(0, str(SRC_ROOT))
from plr_sema import check as _check_mod  # noqa: E402
from plr_sema.check import ir as _ir  # noqa: E402
from plr_sema.check._supported_tools import SUPPORTED_TOOLS  # noqa: E402
from plr_sema.verdict import Verdict, join  # noqa: E402

FIXTURES_DIR = EVAL_DIR / "fixtures" / "regions"

# Real contract param names -- WITHOUT these, `lower_graph`'s §11.2.4 trust
# rule fail-closes every kwarg to `?<i>` (untrusted-by-default), which is
# not what production tier2_extractor.py does (it always loads the same
# table via `param_names_from_contracts`) and would make every kwarg-name
# assertion below meaningless.
_PARAM_NAMES = param_names_from_contracts(DEFAULT_CONTRACTS.read_text(encoding="utf-8"))


def _extract_and_lower(source: str, function_name: str = "protocol"):
    """In-process equivalent of `extract_runner.py`'s own pipeline, for
    tests that only need the RESULT (not the subprocess contract itself --
    see `TestExtractRunnerSubprocess` for that). Returns ``(bc2, payload)``
    -- `compare_bytecode` needs the raw payload too, for its own
    NAME-resolved kwargs comparison (§12.4.1: "resolved by resource NAME
    not slot number").
    """
    from praxis.backend.utils.plr_static_analysis.visitors.computation_graph_extractor import (
        extract_graph_from_source,
    )

    graph = extract_graph_from_source(source, function_name)
    assert graph is not None, f"extractor did not find function {function_name!r} in:\n{source}"
    payload = graph.model_dump(mode="json")
    return _ir.lower_graph(payload, param_names=_PARAM_NAMES), payload


def _lower_graph_from_source(source: str, function_name: str = "protocol"):
    """Convenience wrapper over :func:`_extract_and_lower` for tests that
    only need the bytecode, not the raw payload.
    """
    bc2, _payload = _extract_and_lower(source, function_name)
    return bc2


# A small two-call straight-line row: pick_up_tips (2-well tip_spots Seq)
# then aspirate, on a fresh tip_rack/src pair -- exercises both the
# directional AC-12.15 half and a plain agreement check.
_ROW_EXAMPLE = {
    "call_sequence": [
        {"name": "pick_up_tips", "params": {"at": ["tip_rack.A1", "tip_rack.B1"]}},
        {"name": "aspirate", "params": {"source": "src.A1", "volume_ul": 50}},
    ],
    "deck_layout": {"resources": {"tip_rack": "TipRack", "src": "Plate"}},
}
_ROW_PLR_KWARGS = {
    0: {
        "tip_spots": {
            "k": "seq",
            "items": [
                {"k": "ref", "name": "tip_rack", "cell": "A1"},
                {"k": "ref", "name": "tip_rack", "cell": "B1"},
            ],
        },
    },
    1: {"resource": {"k": "ref", "name": "src", "cell": "A1"}},
}
_ROW_RESOURCE_TYPES = {"tip_rack": "TipRack", "src": "Plate"}


def _render_row():
    resources = resources_from_example(_ROW_EXAMPLE)
    bc1, not_planned = lower_row_calls(
        _ROW_EXAMPLE, _ROW_PLR_KWARGS, resources=resources, param_names=_PARAM_NAMES,
    )
    assert not_planned == []
    calls, _ = calls_from_plr_kwargs(_ROW_EXAMPLE, _ROW_PLR_KWARGS)
    rendered = render_protocol(calls, _ROW_RESOURCE_TYPES)
    return bc1, rendered, calls


# Same shape as `_ROW_EXAMPLE`, but the tip rack's real runtime NAME is
# hyphenated -- backlog #4949 (260903 tier2a followup)'s dominant residual
# class (122/122 in the 260903 full-corpus run, all this one shape).
_HYPHEN_ROW_EXAMPLE = {
    "call_sequence": [
        {"name": "pick_up_tips", "params": {"at": ["tip-rack-1.A1", "tip-rack-1.B1"]}},
        {"name": "aspirate", "params": {"source": "src.A1", "volume_ul": 50}},
    ],
    "deck_layout": {"resources": {"tip-rack-1": "TipRack", "src": "Plate"}},
}
_HYPHEN_ROW_PLR_KWARGS = {
    0: {
        "tip_spots": {
            "k": "seq",
            "items": [
                {"k": "ref", "name": "tip-rack-1", "cell": "A1"},
                {"k": "ref", "name": "tip-rack-1", "cell": "B1"},
            ],
        },
    },
    1: {"resource": {"k": "ref", "name": "src", "cell": "A1"}},
}
_HYPHEN_ROW_RESOURCE_TYPES = {"tip-rack-1": "TipRack", "src": "Plate"}


def _render_hyphen_row():
    resources = resources_from_example(_HYPHEN_ROW_EXAMPLE)
    bc1, not_planned = lower_row_calls(
        _HYPHEN_ROW_EXAMPLE, _HYPHEN_ROW_PLR_KWARGS, resources=resources, param_names=_PARAM_NAMES,
    )
    assert not_planned == []
    calls, _ = calls_from_plr_kwargs(_HYPHEN_ROW_EXAMPLE, _HYPHEN_ROW_PLR_KWARGS)
    rendered = render_protocol(calls, _HYPHEN_ROW_RESOURCE_TYPES)
    return bc1, rendered, calls


class TestDirectionalHalf:
    """AC-12.15's directional half: 'for at least one row the tier-2
    stream's first CALL has method == "setup" and its pick_up_tips CALL
    carries a tip_spots kwarg whose value is a Seq of the same length as
    tier 1's. The directional half is what a comparison that always
    reports "equal" cannot pass.'
    """

    def test_setup_first_and_tip_spots_length_agrees(self):
        bc1, rendered, _calls = _render_row()
        assert not rendered.residuals, rendered.residuals

        bc2 = _lower_graph_from_source(rendered.source)

        raw1 = _extract_calls(bc1, _ir)
        raw2 = _extract_calls(bc2, _ir)

        assert raw1[0]["method"] == "setup"
        assert raw2[0]["method"] == "setup"

        pickup1 = next(c for c in raw1 if c["method"] == "pick_up_tips")
        pickup2 = next(c for c in raw2 if c["method"] == "pick_up_tips")
        len1 = _seq_len(pickup1["kwargs"]["tip_spots"])
        len2 = _seq_len(pickup2["kwargs"]["tip_spots"])
        assert len1 is not None
        assert len1 == len2 == 2


class TestCompareBytecode:
    """AC-12.15's non-directional half: zero extractor-cause divergences
    on a straight-line row that renders and re-extracts cleanly.
    """

    def test_straight_line_row_has_zero_extractor_divergences(self):
        bc1, rendered, calls = _render_row()
        assert not rendered.residuals, rendered.residuals
        bc2, payload = _extract_and_lower(rendered.source)
        divergences = compare_bytecode(
            bc1, bc2, _ir, residuals=list(rendered.residuals), source_lines=rendered.call_lines,
            tier1_wire_calls=calls, tier2_payload=payload,
        )
        extractor_divs = [d for d in divergences if d.cause == "extractor"]
        assert extractor_divs == [], [
            (d.call_index, d.field, d.tier1, d.tier2, d.detail) for d in extractor_divs
        ]

    def test_reset_call_disagreement_is_classified_reset(self):
        """Force a pc-0 method mismatch and confirm it lands in the
        'reset' bucket, not 'extractor' -- the table's fourth row.
        """
        bc1, rendered, calls = _render_row()
        bc2, payload = _extract_and_lower(rendered.source)
        raw2 = _extract_calls(bc2, _ir)
        assert raw2[0]["method"] == "setup"
        # Corrupt tier1's own first call's method name to simulate a
        # reset-agreement failure without touching either lowering.
        import dataclasses

        corrupted_instrs = list(bc1.instructions)
        for idx, instr in enumerate(corrupted_instrs):
            if isinstance(instr, _ir.Call) and instr.method == "setup":
                corrupted_instrs[idx] = dataclasses.replace(instr, method="NOT_SETUP")
                break
        bc1_corrupted = dataclasses.replace(bc1, instructions=tuple(corrupted_instrs))
        divergences = compare_bytecode(
            bc1_corrupted, bc2, _ir, residuals=[], source_lines=rendered.call_lines,
            tier1_wire_calls=calls, tier2_payload=payload,
        )
        reset_divs = [d for d in divergences if d.call_index == 0 and d.field == "method"]
        assert len(reset_divs) == 1
        assert reset_divs[0].cause == "reset"


class TestHyphenatedResourceName:
    """Backlog #4949 (260903 tier2a followup): a resource whose real
    runtime NAME is not a valid Python identifier renders under a
    sanitised, collision-safe parameter name and compares EQUAL to tier 1
    (which only ever sees the original name) once the name mapping is
    threaded into ``compare_bytecode`` -- zero renderer residuals, zero
    extractor-cause divergences.
    """

    def test_hyphenated_name_renders_extracts_and_compares_equal(self):
        bc1, rendered, calls = _render_hyphen_row()
        assert not rendered.residuals, rendered.residuals
        assert "tip_rack_1: TipRack" in rendered.source
        assert "tip-rack-1" not in rendered.source
        assert rendered.name_map["tip-rack-1"] == "tip_rack_1"

        bc2, payload = _extract_and_lower(rendered.source)
        divergences = compare_bytecode(
            bc1, bc2, _ir, residuals=list(rendered.residuals), source_lines=rendered.call_lines,
            tier1_wire_calls=calls, tier2_payload=payload, resource_name_map=rendered.name_map,
        )
        assert divergences == [], [
            (d.call_index, d.field, d.tier1, d.tier2, d.detail) for d in divergences
        ]


class TestRenderProtocol:
    def test_renders_setup_first_and_keyword_args(self):
        calls = [
            {"method": "setup", "kwargs": {}, "receiver": "lh", "receiver_type": "LiquidHandler"},
            {
                "method": "pick_up_tips",
                "kwargs": {
                    "tip_spots": {
                        "k": "seq",
                        "items": [{"k": "ref", "name": "tip_rack", "cell": "A1"}],
                    },
                },
                "receiver": "lh", "receiver_type": "LiquidHandler",
            },
        ]
        rendered = render_protocol(calls, {"tip_rack": "TipRack"})
        assert not rendered.residuals
        assert "async def protocol(lh: LiquidHandler, tip_rack: TipRack):" in rendered.source
        assert "    await lh.setup()" in rendered.source
        assert "    await lh.pick_up_tips(tip_spots=[tip_rack['A1']])" in rendered.source

    def test_unresolvable_resource_becomes_residual_not_a_crash(self):
        calls = [
            {"method": "setup", "kwargs": {}, "receiver": "lh", "receiver_type": "LiquidHandler"},
            {
                "method": "move_resource",
                "kwargs": {"resource": {"k": "ref", "name": "mystery", "cell": None}},
                "receiver": "lh", "receiver_type": "LiquidHandler",
            },
        ]
        # "mystery" is never in resource_types -- the renderer must not
        # invent a type for it.
        rendered = render_protocol(calls, {})
        assert len(rendered.residuals) == 1
        assert rendered.residuals[0].method == "move_resource"
        assert rendered.residuals[0].kwarg == "resource"
        assert "await lh.move_resource()" in rendered.source
        assert classify_residual_reason(rendered.residuals[0].reason) == RESIDUAL_UNKNOWN_RESOURCE

    def test_unresolvable_resource_inside_seq_becomes_residual(self):
        """The same unknown-resource residual, but the ref is NESTED
        inside a `seq` kwarg value rather than the top-level value --
        backlog #4949's `_render_value` fix (name-map membership, not
        `.isidentifier()`) must catch this case too, not just the
        top-level one `render_protocol`'s own pre-check already handled.
        """
        calls = [
            {"method": "setup", "kwargs": {}, "receiver": "lh", "receiver_type": "LiquidHandler"},
            {
                "method": "pick_up_tips",
                "kwargs": {
                    "tip_spots": {
                        "k": "seq",
                        "items": [{"k": "ref", "name": "mystery", "cell": "A1"}],
                    },
                },
                "receiver": "lh", "receiver_type": "LiquidHandler",
            },
        ]
        rendered = render_protocol(calls, {})
        assert len(rendered.residuals) == 1
        assert rendered.residuals[0].kwarg == "tip_spots"
        assert classify_residual_reason(rendered.residuals[0].reason) == RESIDUAL_UNKNOWN_RESOURCE
        assert "await lh.pick_up_tips()" in rendered.source

    def test_unrenderable_value_kind_is_a_classified_residual_not_invented(self):
        """A kwarg value whose `k` is genuinely outside `{lit, ref, seq}`
        (e.g. the extractor's own `top`, a value with no Python literal
        form at all) is dropped and classified as
        `RESIDUAL_UNRENDERABLE_VALUE_KIND` -- never coerced into a literal
        or a ref that would misrepresent it.
        """
        calls = [
            {"method": "setup", "kwargs": {}, "receiver": "lh", "receiver_type": "LiquidHandler"},
            {
                "method": "aspirate",
                "kwargs": {"volume_ul": {"k": "top"}},
                "receiver": "lh", "receiver_type": "LiquidHandler",
            },
        ]
        rendered = render_protocol(calls, {})
        assert len(rendered.residuals) == 1
        assert rendered.residuals[0].kwarg == "volume_ul"
        assert classify_residual_reason(rendered.residuals[0].reason) == RESIDUAL_UNRENDERABLE_VALUE_KIND
        assert "await lh.aspirate()" in rendered.source


class TestExtractRunnerSubprocess:
    """AC-12.16: `extract_runner.py` is invoked as a SUBPROCESS."""

    def test_runner_invoked_as_subprocess_produces_graph(self, tmp_path):
        source = (
            "async def protocol(lh: LiquidHandler, tip_rack: TipRack):\n"
            "    await lh.setup()\n"
            '    await lh.pick_up_tips(tip_spots=[tip_rack["A1"]])\n'
        )
        src_path = tmp_path / "protocol.py"
        src_path.write_text(source, encoding="utf-8")
        out_path = tmp_path / "graph.json"
        cache_dir = tmp_path / "cache"
        proc = subprocess.run(
            [sys.executable, str(RUNNER_MODULE),
             "--source", str(src_path), "--function", "protocol",
             "--out", str(out_path), "--cache-dir", str(cache_dir)],
            capture_output=True, text=True, timeout=60,
        )
        assert proc.returncode == 0, proc.stderr
        payload = json.loads(out_path.read_text(encoding="utf-8"))
        assert "error" not in payload, payload
        methods = [op["method_name"] for op in payload["operations"]]
        assert methods == ["setup", "pick_up_tips"]

    def test_runner_caches_by_source_digest(self, tmp_path):
        source = "async def protocol(lh: LiquidHandler):\n    await lh.setup()\n"
        src_path = tmp_path / "protocol.py"
        src_path.write_text(source, encoding="utf-8")
        cache_dir = tmp_path / "cache"

        def _run(out_name: str) -> subprocess.CompletedProcess:
            return subprocess.run(
                [sys.executable, str(RUNNER_MODULE),
                 "--source", str(src_path), "--function", "protocol",
                 "--out", str(tmp_path / out_name), "--cache-dir", str(cache_dir)],
                capture_output=True, text=True, timeout=60,
            )

        first = _run("graph1.json")
        assert first.returncode == 0, first.stderr
        assert "cache MISS" in first.stderr
        second = _run("graph2.json")
        assert second.returncode == 0, second.stderr
        assert "cache HIT" in second.stderr
        assert (tmp_path / "graph1.json").read_text() == (tmp_path / "graph2.json").read_text()


def _iter_top_level_imports(tree: ast.AST):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node, alias.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                yield node, node.module.split(".")[0]


class TestImportBoundaryEval:
    """AC-12.16: 'an AST import scan of plr-sema/src/ and plr-sema/eval/
    finds no import praxis outside the subprocess argument list' --
    `extract_runner.py` is the one module the subprocess argv names, and
    it is exempted here by name.
    """

    def test_no_praxis_import_outside_runner_module(self):
        offenders: list[str] = []
        for root in (SRC_ROOT, EVAL_DIR):
            for path in sorted(root.rglob("*.py")):
                if path == RUNNER_MODULE:
                    continue
                tree = ast.parse(path.read_text(), filename=str(path))
                for node, top in _iter_top_level_imports(tree):
                    if top == "praxis":
                        offenders.append(f"{path}: {ast.unparse(node)}")
        assert offenders == [], f"AC-12.16 violation: {offenders}"

    def test_runner_module_import_is_praxis(self):
        """Sanity: the exemption above is exercised, not vacuous -- the
        one `import praxis...` it excuses actually exists, and lives
        inside `main()` (not at module scope), per the runner's own
        docstring.
        """
        tree = ast.parse(RUNNER_MODULE.read_text(), filename=str(RUNNER_MODULE))
        tops = {top for _n, top in _iter_top_level_imports(tree)}
        assert "praxis" in tops

        module = ast.parse(RUNNER_MODULE.read_text(), filename=str(RUNNER_MODULE))
        main_fn = next(
            n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == "main"
        )
        module_level_praxis_imports = [
            node for node in module.body
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for _n, top in _iter_top_level_imports(node)
            if top == "praxis"
        ]
        assert module_level_praxis_imports == [], "praxis import must be lazy, inside main(), not module-level"
        praxis_in_main = [
            node for node in ast.walk(main_fn)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for _n, top in _iter_top_level_imports(node)
            if top == "praxis"
        ]
        assert praxis_in_main, "expected the praxis import inside main()"


# ---------------------------------------------------------------------------
# Tier 2b (spec 260903 §12.4.2, backlog #4880/T21, AC-12.17/AC-12.18)
# ---------------------------------------------------------------------------


class _DummyReceiver:
    """A minimal async-method receiver for `RegionRecorder` unit tests --
    no PLR/deck construction needed for the recorder's OWN mechanics
    (visit counter, re-raise, teardown); those are exercised for real by
    `TestSmallestForFixtureEndToEnd` below.
    """

    async def pick_up_tips(self, **kwargs):
        return "picked"

    async def drop_tips(self, **kwargs):
        raise RuntimeError("boom")


class TestRegionRecorderUnit:
    """Recorder unit tests (deliverable 7, bullet 1): visit counter,
    re-raise, and (via `build_static_join_map`) duplicate-key failure.
    """

    def test_visit_counter_increments_per_call_site(self):
        import asyncio

        receiver = _DummyReceiver()
        recorder = RegionRecorder(receiver, ["pick_up_tips", "drop_tips"])
        recorder.install()

        async def _twice():
            for _ in range(2):
                await receiver.pick_up_tips()

        asyncio.run(_twice())
        recorder.uninstall()

        records = [r for r in recorder.records if r.method == "pick_up_tips"]
        assert [r.visit_index for r in records] == [1, 2]
        assert all(r.outcome == "ran_ok" for r in records)
        # Both calls came from the SAME caller line inside `_twice` --
        # the whole point of a per-(method, lineno) monotonic counter.
        assert len({r.lineno for r in records}) == 1

    def test_reraise_is_recorded_and_propagated(self):
        import asyncio

        receiver = _DummyReceiver()
        recorder = RegionRecorder(receiver, ["pick_up_tips", "drop_tips"])
        recorder.install()

        async def _raise():
            await receiver.drop_tips()

        with pytest.raises(RuntimeError, match="boom"):
            asyncio.run(_raise())
        recorder.uninstall()

        assert len(recorder.records) == 1
        record = recorder.records[0]
        assert record.method == "drop_tips"
        assert record.visit_index == 1
        assert record.outcome == "raised:RuntimeError"
        assert recorder.raised is record

    def test_uninstall_restores_original_method(self):
        receiver = _DummyReceiver()
        original = type(receiver).pick_up_tips
        recorder = RegionRecorder(receiver, ["pick_up_tips"])
        recorder.install()
        assert "pick_up_tips" in receiver.__dict__
        recorder.uninstall()
        assert "pick_up_tips" not in receiver.__dict__
        assert type(receiver).pick_up_tips is original

    def test_build_static_join_map_raises_on_duplicate(self):
        with pytest.raises(DuplicateCallSiteError):
            build_static_join_map(
                [("pick_up_tips", 5, "op_1"), ("pick_up_tips", 5, "op_2")]
            )

    def test_build_static_join_map_ok_when_unique(self):
        join_map = build_static_join_map(
            [("pick_up_tips", 5, "op_1"), ("aspirate", 6, "op_2")]
        )
        assert join_map == {("pick_up_tips", 5): "op_1", ("aspirate", 6): "op_2"}


class TestOperationIterationJoin:
    """The `(operation, iteration)` join on one real fixture (deliverable
    7, bullet 2): `for_pickup_no_drop_raises.py`'s two-element `for` gives
    iteration 1 a non-WILL_FAIL verdict and iteration 2 a definite
    WILL_FAIL (HasTipError) for `pick_up_tips`.
    """

    def test_for_pickup_no_drop_raises_join_and_verdict(self, tmp_path):
        contracts_json = DEFAULT_CONTRACTS.read_text(encoding="utf-8")
        contracts_payload = json.loads(contracts_json)
        param_names = param_names_from_contracts(contracts_json)
        fixture_path = FIXTURES_DIR / "for_pickup_no_drop_raises.py"

        payload = region_oracle._extract_graph_payload(
            fixture_path, cache_dir=tmp_path, runner_python=sys.executable,
        )
        _bytecode, findings, join_map, static, _proved_trips = region_oracle._static_report(
            payload, contracts_payload, param_names, _ir, _check_mod,
        )
        assert findings, "expected at least one static finding"

        # #4948: OperationNode.line_number is real now, so the join key carries the
        # fixture's actual source line; look the method up regardless of it.
        op_id = next((v for (m, _ln), v in join_map.items() if m == "pick_up_tips"), None)
        assert op_id is not None, f"join map missing pick_up_tips: {join_map}"

        verdict_1 = region_oracle._verdict_at(static, join, op_id, 1)
        verdict_2 = region_oracle._verdict_at(static, join, op_id, 2)
        assert verdict_2 is Verdict.WILL_FAIL, verdict_2
        assert verdict_1 is not Verdict.WILL_FAIL, verdict_1


class TestSmallestForFixtureEndToEnd:
    """Deliverable 7, bullet 3: the smallest `for`-fixture, run end to end
    (chatterbox, no hardware -- fast) via `region_oracle.run_fixture`.
    Asserts the WILL_FAIL lands at the raised key and `unsound == 0`.
    """

    def test_for_pickup_no_drop_raises_end_to_end(self, tmp_path):
        contracts_json = DEFAULT_CONTRACTS.read_text(encoding="utf-8")
        contracts_payload = json.loads(contracts_json)
        param_names = param_names_from_contracts(contracts_json)
        fixture_path = FIXTURES_DIR / "for_pickup_no_drop_raises.py"

        outcome = region_oracle.run_fixture(
            fixture_path,
            contracts_payload=contracts_payload,
            param_names=param_names,
            ir_mod=_ir,
            check_mod=_check_mod,
            supported_tools=SUPPORTED_TOOLS,
            join_fn=join,
            will_fail_verdict=Verdict.WILL_FAIL,
            safe_verdict=Verdict.SAFE,
            cache_dir=tmp_path,
            runner_python=sys.executable,
        )

        assert outcome.status == "compared", outcome.detail
        assert outcome.raised is not None and "HasTipError" in outcome.raised
        assert outcome.will_fail_at_raised is True, outcome
        assert outcome.unsound_rows == [], outcome.unsound_rows
