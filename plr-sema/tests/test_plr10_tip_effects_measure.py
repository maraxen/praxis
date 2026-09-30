"""Unit tests for plr10_tip_effects_measure (backlog #5622, T63 steps 2b/2c; spec 260929 §18.9, AC-18.14/AC-18.16).

Tiny synthetic rows and stub unit runners only -- never the benchmark. Every positive control has a paired negative
control that must fail:

* schema: the module's ``RESULT_SCHEMA`` against the committed sidecar's ``[result_schema]``, ``validate_result`` rejecting
  every way a result can be wrong, and every identifier in the sidecar's ``[outcomes]`` being a schema key;
* the four-way length invariant and the no-Loop assertion must FIRE on a mismatch / a synthetic ``ir.Loop``;
* the ``:338`` attribution and the independent scan must AGREE on every disturber class -- and a deliberately wrong
  independent scan must DISAGREE (so the M8 hard term can fail);
* resumability (AC-18.14 (a)(b)(c) + the negative control), with stub unit runners: a matching unit is reused and NOT
  recomputed, a corrupted output or a changed input forces recomputation, a kill after one unit leaves it reusable, and a
  stamp whose input hash differs from the current run's is NOT reused even with a matching output sha256;
* one real subprocess-runner run (a per-unit timeout kills the unit's process group; a crash is recorded, not raised).
"""

from __future__ import annotations

import copy
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

import pytest

_EVAL_DIR = Path(__file__).resolve().parents[1] / "eval"
sys.path.insert(0, str(_EVAL_DIR))

import oracle_common as oc  # noqa: E402
import plr10_tip_effects_measure as mm  # noqa: E402
from plr_sema.check import ir  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
SIDECAR_TOML = _EVAL_DIR / "plr10_tip_effects_measure.bth.toml"
SCRIPT = _EVAL_DIR / "plr10_tip_effects_measure.py"
EXAMPLES_DIR = REPO_ROOT / "training" / "examples"


def _schema_toml() -> dict[str, str]:
    with SIDECAR_TOML.open("rb") as f:
        return tomllib.load(f)["result_schema"]


# ---------------------------------------------------------------------------
# schema
# ---------------------------------------------------------------------------


class TestSchema:
    def test_module_schema_matches_sidecar_toml_keys_types_and_order(self) -> None:
        names = {"bool": bool, "int": int, "float": float, "str": str}
        toml_schema = {k: names[v] for k, v in _schema_toml().items()}
        assert toml_schema == mm.RESULT_SCHEMA
        assert list(toml_schema) == list(mm.RESULT_SCHEMA)

    def test_every_identifier_in_the_sidecar_outcomes_is_a_schema_key(self) -> None:
        with SIDECAR_TOML.open("rb") as f:
            outcomes = tomllib.load(f)["outcomes"]
        keywords = {"and", "or", "true", "false"}
        used: set[str] = set()
        for branch in outcomes.values():
            cond = re.sub(r"'[^']*'", "", branch["condition"])
            used |= set(re.findall(r"\b[a-z][a-z0-9_]*\b", cond)) - keywords
        assert used, "parsed no identifiers out of the outcome conditions"
        assert used <= set(mm.RESULT_SCHEMA), sorted(used - set(mm.RESULT_SCHEMA))

    def _good(self) -> dict[str, Any]:
        defaults = {bool: True, int: 1, str: "widen"}
        return {k: defaults[t] for k, t in mm.RESULT_SCHEMA.items()}

    def test_validate_result_accepts_a_conforming_result(self) -> None:
        mm.validate_result(self._good())

    def test_validate_result_rejects_missing_extra_and_mistyped_keys(self) -> None:
        good = self._good()
        missing = {k: v for k, v in good.items() if k != "control_fires"}
        with pytest.raises(ValueError, match="missing"):
            mm.validate_result(missing)
        with pytest.raises(ValueError, match="extra"):
            mm.validate_result({**good, "units": {}})
        with pytest.raises(ValueError, match="control_fires"):
            mm.validate_result({**good, "control_fires": 1})  # an int is not a bool
        with pytest.raises(ValueError, match="real_unsound"):
            mm.validate_result({**good, "real_unsound": True})  # a bool is not an int
        with pytest.raises(ValueError, match="real_unsound"):
            mm.validate_result({**good, "real_unsound": 1.0})
        with pytest.raises(ValueError, match="load_state_channel_effect"):
            mm.validate_result({**good, "load_state_channel_effect": None})


# ---------------------------------------------------------------------------
# bytecode (de)serialisation, the four-way invariant, the no-Loop assertion, the captures
# ---------------------------------------------------------------------------


def _synthetic_stream() -> ir.Bytecode:
    return ir.Bytecode(
        ir_version=ir.IR_VERSION,
        instructions=(
            ir.Resource(slot=0, type="LiquidHandler", element_type=None, is_container=False, is_parameter=False, parents=(), grid=None),
            ir.Resource(slot=1, type="Plate", element_type="Well", is_container=True, is_parameter=False, parents=("Deck",), grid=(12, 8)),
            ir.Call(receiver=0, receiver_type="LiquidHandler", method="setup", kwargs={}),
            ir.Widen(reason="has_conditionals"),
            ir.Branch(),
            ir.Call(receiver=0, receiver_type="LiquidHandler", method="aspirate",
                    kwargs={"a": ir.Lit(5), "b": ir.Ref(1, "A1"), "c": ir.Seq((ir.Lit("x"), ir.Top())), "d": ir.Top()}),
            ir.Else(),
            ir.End(),
        ),
        sideband={"origin": {2: "setup", 5: "0"}},
    )


class TestBytecodeJson:
    def test_round_trips_every_instruction_kind(self) -> None:
        bc = _synthetic_stream()
        j = mm.bytecode_to_json(bc)
        assert j["origin"] == {"2": "setup", "5": "0"}
        back = ir.Bytecode(ir.IR_VERSION, mm.instructions_from_json(j["instructions"]))
        assert ir.canonical_text(back) == ir.canonical_text(bc)
        assert back.instructions == bc.instructions

    def test_round_trips_a_real_lowered_tier1_stream(self) -> None:
        payload = json.loads((EXAMPLES_DIR / "aspirate_dispense_drop.json").read_text(encoding="utf-8"))
        example = {k: payload[k] for k in ("call_sequence", "intent_record", "deck_layout")}
        rt = oc.run_runtime(example)
        bc, _ = oc.lower_row_calls(example, rt.plr_kwargs, resources=oc.resources_from_example(example))
        back = ir.Bytecode(ir.IR_VERSION, mm.instructions_from_json(mm.bytecode_to_json(bc)["instructions"]))
        assert ir.canonical_text(back) == ir.canonical_text(bc)
        mm.assert_no_loop("real", bc.instructions)  # NEGATIVE control for the loop assertion: a real stream passes


class TestFourWayInvariant:
    def test_equal_lengths_pass(self) -> None:
        mm.check_four_way(5, 5, 5, 5)
        mm.check_four_way(0, 0, 0, 0)

    @pytest.mark.parametrize("which", range(4))
    @pytest.mark.parametrize("delta", [-1, 1])
    def test_any_single_mismatch_raises(self, which: int, delta: int) -> None:
        counts = [7, 7, 7, 7]
        counts[which] += delta
        with pytest.raises(mm.PositionalCorrelationError, match="positional correlation invariant broken"):
            mm.check_four_way(*counts)

    def test_build_real_payload_raises_when_a_capture_list_is_short(self) -> None:
        report = {
            "rows": [{"record_id": "r1", "no_call_reason": None, "skip_reason": None, "calls": ["pick_up_tips"]}],
            "summary_flat": {},
        }
        caps = mm.RealArmCaptures()
        caps.findings.append(("r1", ()))
        caps.lowered.append(("r1", None, None, [], {}))
        # the env capture never fired (e.g. run_static_calls stopped calling observation_env_members)
        with pytest.raises(mm.PositionalCorrelationError):
            mm.build_real_payload(report, caps)

    def test_ineligible_rows_are_not_counted(self) -> None:
        report = {
            "rows": [
                {"record_id": "n", "no_call_reason": "x", "skip_reason": None, "calls": []},
                {"record_id": "s", "no_call_reason": None, "skip_reason": "y", "calls": []},
            ],
            "summary_flat": {"operations_executed": 0, "rows_executed": 0},
            "n_tip_racks_decided": {"total": 0, "attempted": 0},
            "scope_verdict_by_method": {},
        }
        payload = mm.build_real_payload(report, mm.RealArmCaptures())  # zero eligible rows, zero captures: consistent
        assert payload["captures"] == {"n_eligible": 0, "rows": []}


class TestNoLoopAssertion:
    def test_fires_on_a_synthetic_ir_loop_naming_the_row_and_pc(self) -> None:
        stream = (
            ir.Call(receiver=0, receiver_type="LiquidHandler", method="setup", kwargs={}),
            ir.Loop(trip=None),
            ir.End(),
        )
        with pytest.raises(mm.LoopInTier1Stream, match=r"row 'rowX' pc 1"):
            mm.assert_no_loop("rowX", stream)

    def test_fires_on_a_has_loops_wrap(self) -> None:
        """A synthetic ``has_loops`` wrap lowers to ``Widen(has_loops)`` followed by an ``ir.Loop`` and is caught the same way."""
        stream = (ir.Widen(reason="has_loops"), ir.Loop(trip=None), ir.Call(0, "LiquidHandler", "setup", {}), ir.End())
        with pytest.raises(mm.LoopInTier1Stream, match="pc 1"):
            mm.assert_no_loop("wrapped", stream)

    def test_fires_on_the_persisted_form_too(self) -> None:
        with pytest.raises(mm.LoopInTier1Stream):
            mm.assert_no_loop("p", [{"op": "CALL"}, {"op": "LOOP", "trip": None}])

    def test_a_branch_a_widen_and_calls_are_not_loops(self) -> None:
        mm.assert_no_loop("ok", _synthetic_stream().instructions)

    def test_the_analyses_re_check_it_over_the_persisted_stream(self) -> None:
        row = _row([{"method": "aspirate"}], verdict="safe")
        row["instructions"].insert(1, {"op": "LOOP", "trip": None})
        with pytest.raises(mm.LoopInTier1Stream):
            mm.analyze_338([row], _mini_contracts())
        with pytest.raises(mm.LoopInTier1Stream):
            mm.independent_scan([row], _mini_contracts())


class TestCaptures:
    def test_originals_are_restored_on_normal_exit_and_on_exception(self) -> None:
        originals = (oc.FINDINGS_SINK, oc.LOWERED_SINK, oc.observation_env_members)
        with mm.RealArmCaptures().install():
            assert oc.observation_env_members is not originals[2]
            assert oc.FINDINGS_SINK is not None and oc.LOWERED_SINK is not None
        assert (oc.FINDINGS_SINK, oc.LOWERED_SINK, oc.observation_env_members) == originals
        with pytest.raises(RuntimeError, match="boom"):
            with mm.RealArmCaptures().install():
                raise RuntimeError("boom")
        assert (oc.FINDINGS_SINK, oc.LOWERED_SINK, oc.observation_env_members) == originals

    def test_chain_composed_with_prior_sinks_and_the_env_wrapper_is_transparent(self) -> None:
        seen_f: list[Any] = []
        seen_l: list[Any] = []
        prior = (oc.FINDINGS_SINK, oc.LOWERED_SINK)
        oc.FINDINGS_SINK = lambda rid, fs: seen_f.append(rid)
        oc.LOWERED_SINK = lambda rid, bc, bc1, np, et: seen_l.append(rid)
        try:
            caps = mm.RealArmCaptures()
            with caps.install():
                oc.FINDINGS_SINK("r", ())
                oc.LOWERED_SINK("r", None, None, [], {})
                members = oc.observation_env_members(None, {})  # the real function: no observation -> empty
            assert seen_f == ["r"] and seen_l == ["r"]  # the prior sinks still saw the row
            assert len(caps.findings) == len(caps.lowered) == len(caps.env) == 1
            assert members == frozenset() and caps.env[0] is members  # returned unchanged, appended as-is
        finally:
            oc.FINDINGS_SINK, oc.LOWERED_SINK = prior


# ---------------------------------------------------------------------------
# the :338 attribution and the independent scan (hand-built capture rows)
# ---------------------------------------------------------------------------

SITE_338 = "f.py:338:_check_tip_racks_available"
OBS_OK = ["obs:tip_racks_available=true", "obs:deck_resources_verified=true", "obs:num_channels=8"]


def _mini_contracts(kind: str = "raise_guard", *, receiver_state: bool = True) -> dict[str, Any]:
    site = {"file": "f.py", "lineno": 338, "qualname": "_check_tip_racks_available"}
    g338 = {"site": site, "raises": "ValueError", "condition": "not rack._available_for_tip_handling", "kind": kind}
    top = {"_resource_pickup": "TOP"}
    return {
        "contracts": {
            "LiquidHandler.pick_up_tips": {"guards": [g338], "anchor_net_effects": top},
            "LiquidHandler.setup": {"guards": []},
            "LiquidHandler.aspirate": {"guards": [], "anchor_net_effects": top},
            "LiquidHandler.move_lid": {"guards": [], "anchor_net_effects": {"_resource_pickup": "EMPTY"}},
            "LiquidHandler.pick_up_resource": {"guards": [], "anchor_net_effects": {"_resource_pickup": "HELD"}},
            "LiquidHandler.stripped": {"guards": [{"anchor_field": "_resource_pickup", "site": site}]},
            "Other.foo": {"guards": []},
        },
        "receiver_state": (
            {"LiquidHandler": {"anchor_fields": ["_resource_pickup"]}, "Other": {"anchor_fields": ["_resource_pickup"]}}
            if receiver_state
            else {}
        ),
    }


def _call(method: str, receiver_type: str | None = "LiquidHandler") -> dict[str, Any]:
    return {"op": "CALL", "receiver": 0, "receiver_type": receiver_type, "method": method, "kwargs": {}}


def _row(
    before: list[dict[str, Any]], *, verdict: str = "unknown", env: list[str] | None = None,
    widen_execution_order: bool = False, record_id: str = "row",
) -> dict[str, Any]:
    """A capture row: ``setup``, then ``before`` calls (each ``{"method", "receiver_type"?}``), then ONE ``pick_up_tips`` whose
    ``:338`` finding has ``verdict``."""
    ops = [(b["method"], b.get("receiver_type", "LiquidHandler")) for b in before] + [("pick_up_tips", "LiquidHandler")]
    instructions: list[dict[str, Any]] = []
    if widen_execution_order:
        instructions.append({"op": "WIDEN", "reason": "execution_order"})
    setup_pc = len(instructions)
    instructions.append(_call("setup"))
    origin = {str(setup_pc): "setup"}
    for i, (method, rtype) in enumerate(ops):
        origin[str(len(instructions))] = str(i)
        instructions.append(_call(method, rtype))
    pickup_idx = len(ops) - 1
    return {
        "record_id": record_id,
        "calls": [m for m, _ in ops],
        "not_planned": [],
        "env": list(OBS_OK if env is None else env),
        "findings": [{"op": f"op_{pickup_idx}", "verdict": verdict, "site": SITE_338, "reason": ""}],
        "instructions": instructions,
        "origin": origin,
    }


def _both(rows: list[dict[str, Any]], contracts: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    return mm.analyze_338(rows, contracts), mm.independent_scan(rows, contracts)


@pytest.fixture(scope="module")
def real_contracts() -> dict[str, Any]:
    return json.loads(mm.DEFAULT_CONTRACTS.read_text(encoding="utf-8"))


class TestAttribution:
    def test_a_clean_safe_pickup_is_counted_safe_and_reasonless(self) -> None:
        a, i = _both([_row([{"method": "aspirate"}], verdict="safe")], _mini_contracts())
        assert (a["n_338_pickups_attempted"], a["n_338_pickups_safe"]) == (1, 1)
        assert a["n_338_safe_with_reason"] == 0 and a["n_338_declined_unattributed"] == 0
        assert i["n_pickups_with_preceding_disturber_indep"] == 0

    @pytest.mark.parametrize(
        ("before", "contracts_kw"),
        [
            ([{"method": "move_lid"}], {}),  # (a) derived move family, EMPTY
            ([{"method": "pick_up_resource"}], {}),  # (a) derived move family, HELD
            ([{"method": "aspirate", "receiver_type": None}], {}),  # (b) receiver_type None
            ([{"method": "no_such_method"}], {}),  # (c) no contract
            ([{"method": "foo", "receiver_type": "Other"}], {}),  # (d) a different receiver type, isolated
            ([{"method": "aspirate"}], {"receiver_state": False}),  # (e) no receiver_state
            ([{"method": "stripped"}], {}),  # (f) reads an anchor with no net effect
        ],
    )
    def test_each_disturber_class_is_attributed_topology_prefix_and_agrees_with_the_scan(self, before, contracts_kw) -> None:
        a, i = _both([_row(before)], _mini_contracts(**contracts_kw))
        assert a["n_338_declined_topology_prefix"] == 1, a
        assert i["n_pickups_with_preceding_disturber_indep"] == 1, i
        assert a["n_338_declined_unattributed"] == 0 and a["n_338_pickups_safe"] == 0

    @pytest.mark.parametrize("before", [[], [{"method": "aspirate"}], [{"method": "aspirate"}, {"method": "aspirate"}]])
    def test_neutral_prefixes_are_not_disturbers_on_either_side(self, before) -> None:
        a, i = _both([_row(before, verdict="safe")], _mini_contracts())
        assert a["n_338_declined_topology_prefix"] == 0 and i["n_pickups_with_preceding_disturber_indep"] == 0

    def test_a_disturber_AFTER_the_pickup_is_not_a_prefix_disturber(self) -> None:
        row = _row([])
        row["instructions"].append(_call("move_lid"))
        a, i = _both([row], _mini_contracts())
        assert a["n_338_declined_topology_prefix"] == 0 and i["n_pickups_with_preceding_disturber_indep"] == 0

    def test_execution_order_widen_fails_closed_on_both_sides(self) -> None:
        a, i = _both([_row([{"method": "aspirate"}], widen_execution_order=True)], _mini_contracts())
        assert a["n_338_declined_topology_prefix"] == 1 and i["n_pickups_with_preceding_disturber_indep"] == 1

    def test_first_failing_conjunct_order_kind_observation_deck_prefix(self) -> None:
        bad_obs = [m for m in OBS_OK if "tip_racks" not in m] + ["obs:tip_racks_available=false"]
        bad_deck = [m for m in OBS_OK if "deck_resources" not in m] + ["obs:deck_resources_verified=false"]
        rows = {
            "observation": (_row([{"method": "move_lid"}], env=bad_obs), _mini_contracts()),
            "deck": (_row([{"method": "move_lid"}], env=bad_deck), _mini_contracts()),
            "kind": (_row([{"method": "move_lid"}], env=bad_obs), _mini_contracts("assert_guard")),
            "topology_prefix": (_row([{"method": "move_lid"}]), _mini_contracts()),
        }
        for reason, (row, contracts) in rows.items():
            a = mm.analyze_338([row], contracts)
            assert a[f"n_338_declined_{reason}"] == 1, (reason, a)
            others = {k: v for k, v in a.items() if k.startswith("n_338_declined_") and k != f"n_338_declined_{reason}"}
            assert set(others.values()) == {0}, (reason, others)

    def test_the_independent_scan_is_restricted_to_kind_observation_and_deck_holding(self) -> None:
        """Both sides share the restriction: a disturbed pickup that fails an EARLIER conjunct counts on neither."""
        bad_obs = [m for m in OBS_OK if "tip_racks" not in m]  # observation absent
        a, i = _both([_row([{"method": "move_lid"}], env=bad_obs)], _mini_contracts())
        assert a["n_338_declined_topology_prefix"] == 0 and a["n_338_declined_observation"] == 1
        assert i["n_pickups_with_preceding_disturber_indep"] == 0 and i["_n_scanned"] == 0
        a2, i2 = _both([_row([{"method": "move_lid"}])], _mini_contracts("assert_guard"))
        assert a2["n_338_declined_kind"] == 1 and i2["_n_scanned"] == 0

    def test_unattributed_and_safe_with_reason_are_counted_not_swallowed(self) -> None:
        # a non-SAFE :338 finding whose recomputed reason says "decided": nothing in the accounting explains it
        a, _ = _both([_row([{"method": "aspirate"}], verdict="unknown")], _mini_contracts())
        assert a["n_338_pickups_attempted"] == 1 and a["n_338_declined_unattributed"] == 1
        # a SAFE finding while the recomputed reason is a decline
        bad_obs = [m for m in OBS_OK if "tip_racks" not in m]
        a2, _ = _both([_row([{"method": "aspirate"}], verdict="safe", env=bad_obs)], _mini_contracts())
        assert a2["n_338_safe_with_reason"] == 1 and a2["n_338_pickups_safe"] == 1

    def test_only_planned_pickups_carrying_a_338_finding_are_in_scope(self) -> None:
        row = _row([{"method": "aspirate"}])
        row["findings"] = []  # no :338 finding at all
        a, i = _both([row], _mini_contracts())
        assert a["n_338_pickups_attempted"] == 0 and i["_n_scanned"] == 0
        row2 = _row([{"method": "aspirate"}])
        row2["findings"][0]["site"] = "f.py:9:SomethingElse"
        assert mm.analyze_338([row2], _mini_contracts())["n_338_pickups_attempted"] == 0
        row3 = _row([{"method": "aspirate"}])
        row3["calls"][-1] = "drop_tips"  # a :338 finding on a non-pickup op is out of scope
        assert mm.analyze_338([row3], _mini_contracts())["n_338_pickups_attempted"] == 0

    def test_the_independent_scan_references_none_of_the_analyzers_topology_functions(self) -> None:
        """M8: the scan re-states §18.5.4 and imports NEITHER ``rack_topology_disturbers`` NOR ``tip_racks_decline_reason``
        (nor the clause helper). Checked over the function's AST -- names, attributes and imports -- docstring excluded."""
        import ast
        import inspect
        import textwrap

        tree = ast.parse(textwrap.dedent(inspect.getsource(mm.independent_scan)))
        banned = {"rack_topology_disturbers", "tip_racks_decline_reason", "rack_topology_clauses", "predicate", "plr_sema"}
        seen: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                seen.add(node.id)
            elif isinstance(node, ast.Attribute):
                seen.add(node.attr)
            elif isinstance(node, ast.ImportFrom):
                seen.update([node.module or "", *(a.name for a in node.names)])
            elif isinstance(node, ast.Import):
                seen.update(a.name for a in node.names)
        assert not (seen & banned), sorted(seen & banned)
        # non-vacuity: the analyzer-side function DOES reference them
        analyzer_src = inspect.getsource(mm.analyze_338)
        assert "rack_topology_disturbers" in analyzer_src and "tip_racks_decline_reason" in analyzer_src

    def test_NEGATIVE_a_wrong_independent_scan_disagrees_so_the_m8_term_can_fail(self) -> None:
        """Control: an independent scan that does not know move_lid is a disturber must disagree with the analyzer-side
        attribution -- i.e. the hard term ``n_338_declined_topology_prefix == n_pickups_with_preceding_disturber_indep`` is
        capable of failing."""
        rows = [_row([{"method": "move_lid"}])]
        a = mm.analyze_338(rows, _mini_contracts())
        wrong = _mini_contracts()
        wrong["contracts"]["LiquidHandler.move_lid"]["anchor_net_effects"] = {"_resource_pickup": "TOP"}
        i_wrong = mm.independent_scan(rows, wrong)
        assert a["n_338_declined_topology_prefix"] == 1
        assert i_wrong["n_pickups_with_preceding_disturber_indep"] == 0
        assert a["n_338_declined_topology_prefix"] != i_wrong["n_pickups_with_preceding_disturber_indep"]

    def test_real_positions_are_recovered_through_unplanned_calls(self) -> None:
        """A not-planned index shifts the local->real mapping: op_2 is the FIRST planned call after setup here."""
        row = _row([{"method": "aspirate"}])
        row["calls"] = ["transfer", "aspirate", "pick_up_tips"]  # indices 0 (unplanned), 1, 2
        row["not_planned"] = [0]
        row["origin"] = {"0": "setup", "1": "0", "2": "1"}
        row["findings"][0]["op"] = "op_2"
        assert mm._real_idx_to_pc(row) == {1: 1, 2: 2}
        a, i = _both([row], _mini_contracts())
        assert a["n_338_pickups_attempted"] == 1 and i["_n_scanned"] == 1

    def test_the_site_is_resolved_by_symbol_and_must_be_unique(self) -> None:
        site, kinds = mm.resolve_site_338(_mini_contracts()["contracts"])
        assert site == SITE_338 and kinds == {"LiquidHandler.pick_up_tips": {"raise_guard"}}
        dup = _mini_contracts()
        dup["contracts"]["LiquidHandler.setup"]["guards"] = [
            {"site": {"file": "g.py", "lineno": 1, "qualname": "_check_tip_racks_available"},
             "raises": "ValueError", "condition": "not rack._available_for_tip_handling"}
        ]
        with pytest.raises(RuntimeError, match="matched"):
            mm.resolve_site_338(dup["contracts"])
        with pytest.raises(RuntimeError, match="matched"):
            mm.resolve_site_338({})

    def test_shipped_table_analyzer_and_independent_scan_agree_for_every_liquidhandler_method(self, real_contracts) -> None:
        """M8 over the SHIPPED table: for every ``LiquidHandler.<m>`` as the one call before a pickup, the analyzer-side
        clause and the independent re-statement of §18.5.4 agree; the sweep is non-vacuous (move_lid disturbs, aspirate does not)."""
        site_338, _ = mm.resolve_site_338(real_contracts["contracts"])
        methods = sorted(k.split(".", 1)[1] for k in real_contracts["contracts"] if k.startswith("LiquidHandler."))
        assert {"move_lid", "aspirate", "pick_up_tips"} <= set(methods)
        disturbing: set[str] = set()
        for m in methods:
            row = _row([{"method": m}], verdict="unknown")
            row["findings"][0]["site"] = site_338
            a = mm.analyze_338([row], real_contracts)
            i = mm.independent_scan([row], real_contracts)
            assert a["n_338_declined_topology_prefix"] == i["n_pickups_with_preceding_disturber_indep"], m
            if i["n_pickups_with_preceding_disturber_indep"]:
                disturbing.add(m)
        assert "move_lid" in disturbing and "aspirate" not in disturbing
        assert {"move_lid", "move_plate", "move_resource", "pick_up_resource", "drop_resource"} <= disturbing


# ---------------------------------------------------------------------------
# parity and mutant fields
# ---------------------------------------------------------------------------


class TestParity:
    def test_absence_counts_as_a_value_and_intended_keys_are_excluded_from_matched(self) -> None:
        p = mm.baseline_parity(
            {"A.x": {"channel_effect": "X"}, "C.z": {"channel_effect": "Z"}, "D.q": {}},
            {"channel_effects": {"A.x": "X", "B.y": "Y"}, "intended_divergences": {}},
        )
        # union {A.x, B.y, C.z}: B.y vanished (absent), C.z is new (absent in the baseline)
        assert (p["baseline_divergences"], p["baseline_parity_total"], p["baseline_parity_matched"]) == (2, 3, 1)
        p2 = mm.baseline_parity(
            {"A.x": {"channel_effect": "new"}},
            {"channel_effects": {"A.x": "old"}, "intended_divergences": {"A.x": {"old": "old", "new": "new"}}},
        )
        assert (p2["baseline_divergences"], p2["baseline_intended_divergences"]) == (1, 1)
        assert (p2["baseline_parity_matched"], p2["baseline_parity_total"]) == (0, 1)

    def test_the_committed_baseline_against_the_shipped_table_has_exactly_the_intended_divergence(self, real_contracts) -> None:
        baseline = json.loads(mm.DEFAULT_BASELINE.read_text(encoding="utf-8"))
        p = mm.baseline_parity(real_contracts["contracts"], baseline)
        assert p["baseline_divergences"] == p["baseline_intended_divergences"] == len(baseline["intended_divergences"])
        assert p["_divergent_keys"] == sorted(baseline["intended_divergences"])
        assert p["baseline_parity_matched"] == p["baseline_parity_total"] - p["baseline_divergences"]

    def test_NEGATIVE_an_undeclared_divergence_makes_the_counters_disagree(self, real_contracts) -> None:
        baseline = json.loads(mm.DEFAULT_BASELINE.read_text(encoding="utf-8"))
        tampered = copy.deepcopy(real_contracts["contracts"])
        tampered["LiquidHandler.drop_tips"]["channel_effect"] = "HAS_TIP"
        p = mm.baseline_parity(tampered, baseline)
        assert p["baseline_divergences"] != p["baseline_intended_divergences"]


def _tip_payload(unit: str, *, raised: int = 10, will_fail: int | None = None, unsound: list[str] | None = None,
                 crit_ii: list[str] | None = None, hard: list[str] | None = None, **extra: Any) -> dict[str, Any]:
    cls = mm.TIP_UNIT_CLASS.get(unit, mm.V1_CLASS)
    s = {
        "n_total": raised + 3, "n_construction_skipped": 3, "n_error": 3, "n_static_error": 0,
        "n_runtime_harness_error": 0, "n_ran": raised + 1,
        "n_raised_as_expected": raised,
        "static_verdict_at_raising_index": {"will_fail": raised if will_fail is None else will_fail, "unknown": 0, "safe": 0, "none": 0},
        "unsound_safe_where_simulator_raised": unsound or [],
        "unsound_will_fail_where_simulator_ran_clean": crit_ii or [],
        **extra,
    }
    return {"unit": unit, "class": cls, "report": {"by_class": {cls: s}, "hard_violations": hard or [], "gate_passed": not hard}}


def _all_mutant_payloads() -> dict[str, dict[str, Any]]:
    return {
        "m1": _tip_payload("m1", raised=160),
        "m2": _tip_payload("m2", raised=210),
        "p3a": _tip_payload("p3a", raised=50, will_fail=0, hard=["p3a_pickup_already_held: floor FAILED -- attempted=50 < 60"]),
        "m3": _tip_payload("m3", raised=0, will_fail=0, n_runtime_raised_at_338=7, n_static_338_safe=0),
        "v1": _tip_payload("v1", raised=60),
    }


class TestMutantFields:
    def test_field_mapping_and_denominators(self) -> None:
        f = mm.mutant_fields(_all_mutant_payloads())
        assert (f["m1_attempted"], f["m1_achieved"], f["m1_will_fail_fired"]) == (160, 160, True)
        assert (f["m2_attempted"], f["m2_achieved"], f["m2_will_fail_fired"]) == (210, 210, True)
        assert (f["p3a_attempted"], f["p3a_achieved"]) == (50, 0)
        assert (f["m3_attempted"], f["runtime_raised_m3"], f["static_338_safe_on_m3"]) == (1, 7, 0)  # n_ran, not n_raised
        assert (f["v1_attempted"], f["v1_achieved"], f["v1_gate_passed"]) == (60, 60, True)
        assert f["mutants_unsound"] == f["mutants_criterion_ii"] == 0

    def test_m3_attempted_is_n_ran_not_n_raised(self) -> None:
        p = _all_mutant_payloads()
        p["m3"]["report"]["by_class"]["m3_lid_on_tip_rack"]["n_ran"] = 41
        assert mm.mutant_fields(p)["m3_attempted"] == 41

    def test_the_p3a_floor_violation_is_excluded_but_nothing_else_is(self) -> None:
        f = mm.mutant_fields(_all_mutant_payloads())
        assert f["mutants_hard_violations_excl_p3a_floor"] == 0
        assert f["_p3a_floor_violations"] and f["_hard_violations"]
        p = _all_mutant_payloads()
        p["p3a"]["report"]["hard_violations"].append("p3a_pickup_already_held: criterion (i) VIOLATED -- 1 row(s)")
        p["m1"]["report"]["hard_violations"].append("m1_remove_pickup: criterion (iii) FAILED")
        assert mm.mutant_fields(p)["mutants_hard_violations_excl_p3a_floor"] == 2

    def test_unsoundness_sums_over_every_class_including_p3a_m3_and_v1(self) -> None:
        p = _all_mutant_payloads()
        p["m1"] = _tip_payload("m1", unsound=["a"], crit_ii=["b", "c"])
        p["p3a"] = _tip_payload("p3a", will_fail=0, unsound=["d"])
        p["m3"] = _tip_payload("m3", will_fail=0, crit_ii=["e"], n_runtime_raised_at_338=1, n_static_338_safe=0)
        p["v1"] = _tip_payload("v1", unsound=["f", "g"])
        f = mm.mutant_fields(p)
        assert f["mutants_unsound"] == 4 and f["mutants_criterion_ii"] == 3

    def test_will_fail_fired_is_will_fail_positive_not_achieved_equals_attempted(self) -> None:
        p = _all_mutant_payloads()
        p["m1"] = _tip_payload("m1", raised=160, will_fail=0)
        p["m2"] = _tip_payload("m2", raised=210, will_fail=1)
        f = mm.mutant_fields(p)
        assert f["m1_will_fail_fired"] is False and f["m2_will_fail_fired"] is True

    def test_v1_gate_passed_is_the_reports_own_flag(self) -> None:
        p = _all_mutant_payloads()
        p["v1"] = _tip_payload("v1", hard=["v1_overdraw_dispense: criterion (iii) FAILED"])
        assert mm.mutant_fields(p)["v1_gate_passed"] is False

    def test_a_report_missing_its_class_is_an_error_not_a_zero(self) -> None:
        p = _all_mutant_payloads()
        p["m1"]["report"]["by_class"] = {}
        with pytest.raises(RuntimeError, match="no by_class entry"):
            mm.mutant_fields(p)


# ---------------------------------------------------------------------------
# resumability (AC-18.14 (a)(b)(c) + negative control), with stub unit runners
# ---------------------------------------------------------------------------

INPUTS = {
    "derived_contracts_json": "c" * 64, "corpus": {"corpus.jsonl": "a" * 64}, "sidecar": {"side.jsonl": "b" * 64},
    "crosscheck": {"x1.jsonl": "d" * 64, "x2.jsonl": "e" * 64}, "git_head": "f" * 40,
    "code_diff_sha256": "0" * 64, "mutant_examples_sha256": "1" * 64, "limit": None,
    "pylabrobot_head": "5" * 40, "chatterbox_runner_sha256": "6" * 64,
}


class Stub:
    """A counting stub unit runner."""

    def __init__(self, raise_on: dict[str, BaseException] | None = None) -> None:
        self.calls: list[str] = []
        self.raise_on = raise_on or {}

    def __call__(self, unit: str) -> dict[str, Any]:
        self.calls.append(unit)
        if unit in self.raise_on:
            raise self.raise_on[unit]
        return {"unit": unit, "value": len(self.calls), "blob": list(range(5))}


def _statuses(outcome: mm.UnitsOutcome) -> dict[str, str]:
    return {u: r["status"] for u, r in outcome.records.items()}


class TestStampsAndReuse:
    def test_stamp_records_unit_inputs_and_the_outputs_sha256(self, tmp_path: Path) -> None:
        mm.run_units(tmp_path, INPUTS, Stub())
        for unit in mm.UNITS:
            out, stamp_path = mm.unit_paths(tmp_path, unit)
            stamp = json.loads(stamp_path.read_text())
            assert stamp["unit"] == unit and stamp["inputs"] == INPUTS
            assert stamp["output_sha256"] == mm.sha256_file(out)
            assert {"derived_contracts_json", "corpus", "sidecar", "crosscheck", "git_head"} <= set(stamp["inputs"])

    def test_a_matching_unit_is_REUSED_and_the_runner_is_not_called(self, tmp_path: Path) -> None:  # AC-18.14 (a)
        first = Stub()
        o1 = mm.run_units(tmp_path, INPUTS, first)
        assert first.calls == list(mm.UNITS) and set(_statuses(o1).values()) == {"computed"}
        second = Stub()
        o2 = mm.run_units(tmp_path, INPUTS, second)
        assert second.calls == [], "a unit whose stamp inputs and output sha256 both match must not be recomputed"
        assert set(_statuses(o2).values()) == {"reused"}
        for unit, rec in o2.records.items():
            assert rec["source"] == str(mm.unit_paths(tmp_path, unit)[0].resolve())
            assert rec["output_sha256"] == o1.records[unit]["output_sha256"] and rec["inputs"] == INPUTS

    def test_a_CORRUPTED_output_forces_recompute_of_that_unit_only(self, tmp_path: Path) -> None:  # AC-18.14 (b)
        mm.run_units(tmp_path, INPUTS, Stub())
        out, _ = mm.unit_paths(tmp_path, "m2")
        out.write_text(json.dumps({"unit": "m2", "value": 999, "blob": []}))  # valid JSON, wrong bytes
        again = Stub()
        o = mm.run_units(tmp_path, INPUTS, again)
        assert again.calls == ["m2"]
        assert _statuses(o)["m2"] == "computed" and {v for u, v in _statuses(o).items() if u != "m2"} == {"reused"}
        # ... and the recomputed unit is reusable again (stamp refreshed)
        assert mm.check_reusable(tmp_path, "m2", INPUTS)[0]

    def test_a_truncated_or_deleted_output_forces_recompute(self, tmp_path: Path) -> None:
        mm.run_units(tmp_path, INPUTS, Stub())
        mm.unit_paths(tmp_path, "m1")[0].write_text("{trunc")
        mm.unit_paths(tmp_path, "v1")[0].unlink()
        again = Stub()
        mm.run_units(tmp_path, INPUTS, again)
        assert sorted(again.calls) == ["m1", "v1"]

    def test_a_CHANGED_INPUT_forces_recompute_of_every_unit(self, tmp_path: Path) -> None:  # AC-18.14 (b)
        mm.run_units(tmp_path, INPUTS, Stub())
        changed = {**INPUTS, "derived_contracts_json": "9" * 64}  # a different derived_contracts.json hash
        again = Stub()
        o = mm.run_units(tmp_path, changed, again)
        assert again.calls == list(mm.UNITS) and set(_statuses(o).values()) == {"computed"}

    @pytest.mark.parametrize(
        "field, value",
        [("corpus", {"corpus.jsonl": "0" * 64}), ("sidecar", {}), ("crosscheck", {"x1.jsonl": "d" * 64}),
         ("git_head", "a" * 40), ("code_diff_sha256", "2" * 64), ("mutant_examples_sha256", "3" * 64), ("limit", 3),
         ("pylabrobot_head", "7" * 40), ("chatterbox_runner_sha256", "8" * 64)],
    )
    def test_every_input_field_participates_in_reuse(self, tmp_path: Path, field: str, value: Any) -> None:
        mm.run_units(tmp_path, INPUTS, Stub())
        again = Stub()
        mm.run_units(tmp_path, {**INPUTS, field: value}, again)
        assert again.calls == list(mm.UNITS), field

    def test_NEGATIVE_a_stamp_with_a_different_input_hash_is_not_reused_even_with_a_matching_output_sha(self, tmp_path: Path) -> None:
        """The control: the output file's sha256 matches the stamp, only the stamp's INPUT hash differs from the current run's.
        If the runner is not called, the reuse test is vacuous."""
        stale_inputs = {**INPUTS, "corpus": {"corpus.jsonl": "7" * 64}}
        mm.run_units(tmp_path, stale_inputs, Stub())
        out, stamp_path = mm.unit_paths(tmp_path, "real")
        stamp = json.loads(stamp_path.read_text())
        assert stamp["output_sha256"] == mm.sha256_file(out), "the control's premise: the output hash matches its stamp"
        ok, why = mm.check_reusable(tmp_path, "real", INPUTS)
        assert not ok and "input hashes differ" in why
        probe = Stub()
        mm.run_units(tmp_path, INPUTS, probe, units=("real",))
        assert probe.calls == ["real"], "the runner must be called: a mismatched-input stamp must NOT be reused"

    @pytest.mark.parametrize("damage", ["no_stamp", "stamp_other_unit", "stamp_garbage", "no_output", "output_other_unit"])
    def test_every_way_a_pair_can_be_incomplete_or_wrong_is_not_reusable(self, tmp_path: Path, damage: str) -> None:
        mm.run_units(tmp_path, INPUTS, Stub(), units=("m3",))
        out, stamp_path = mm.unit_paths(tmp_path, "m3")
        assert mm.check_reusable(tmp_path, "m3", INPUTS)[0]
        if damage == "no_stamp":
            stamp_path.unlink()
        elif damage == "stamp_other_unit":
            stamp_path.write_text(json.dumps({**json.loads(stamp_path.read_text()), "unit": "m1"}))
        elif damage == "stamp_garbage":
            stamp_path.write_text("not json")
        elif damage == "no_output":
            out.unlink()
        else:  # a self-consistent pair whose payload names another unit
            out.write_text(json.dumps({"unit": "m1"}))
            stamp_path.write_text(json.dumps({**json.loads(stamp_path.read_text()), "output_sha256": mm.sha256_file(out)}))
        ok, _why = mm.check_reusable(tmp_path, "m3", INPUTS)
        assert not ok, damage

    def test_the_stamp_is_written_only_after_the_output_is_complete(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """A crash while writing the STAMP leaves an output with no stamp -- never a stamp without its output."""
        real_write = mm.write_json_atomic

        def _die_on_stamp(path: Path, obj: Any) -> None:
            if path.name.endswith(".stamp.json"):
                raise OSError("simulated crash before the stamp landed")
            real_write(path, obj)

        monkeypatch.setattr(mm, "write_json_atomic", _die_on_stamp)
        with pytest.raises(OSError, match="simulated"):
            mm.persist_unit(tmp_path, "real", {"unit": "real"}, INPUTS)
        out, stamp = mm.unit_paths(tmp_path, "real")
        assert out.is_file() and not stamp.exists()
        assert not mm.check_reusable(tmp_path, "real", INPUTS)[0]

    def test_a_partial_write_never_replaces_an_existing_output(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        target = tmp_path / "x.json"
        mm.write_json_atomic(target, {"ok": 1})

        def _boom(*_a: Any, **_k: Any) -> None:
            raise OSError("no space")

        monkeypatch.setattr(mm.json, "dump", _boom)
        with pytest.raises(OSError):
            mm.write_json_atomic(target, {"ok": 2})
        assert json.loads(target.read_text()) == {"ok": 1}

    def test_a_payload_naming_another_unit_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="expected 'm1'"):
            mm.persist_unit(tmp_path, "m1", {"unit": "m2"}, INPUTS)


class TestKillAndTimeouts:
    def test_KILL_after_one_unit_leaves_it_intact_and_reusable(self, tmp_path: Path) -> None:  # AC-18.14 (c)
        killed = Stub(raise_on={"all_safe": KeyboardInterrupt()})  # the run dies while the second unit is starting
        with pytest.raises(KeyboardInterrupt):
            mm.run_units(tmp_path, INPUTS, killed)
        assert killed.calls == ["real", "all_safe"]
        out, stamp = mm.unit_paths(tmp_path, "real")
        assert out.is_file() and stamp.is_file() and mm.check_reusable(tmp_path, "real", INPUTS)[0]
        assert not (tmp_path / mm.RESULT_NAME).exists()
        # the dying unit left no reusable pair behind
        assert not mm.check_reusable(tmp_path, "all_safe", INPUTS)[0]
        resumed = Stub()
        o = mm.run_units(tmp_path, INPUTS, resumed)
        assert resumed.calls == list(mm.UNITS[1:]), "the next invocation reuses the finished unit and computes only the rest"
        assert _statuses(o)["real"] == "reused" and all(v == "computed" for u, v in _statuses(o).items() if u != "real")

    def test_a_kill_during_a_RECOMPUTE_leaves_no_stale_stamp_for_that_unit(self, tmp_path: Path) -> None:
        mm.run_units(tmp_path, INPUTS, Stub(), units=("m1",))
        mm.unit_paths(tmp_path, "m1")[0].write_text(json.dumps({"unit": "m1", "value": -1}))  # corrupt
        with pytest.raises(KeyboardInterrupt):
            mm.run_units(tmp_path, INPUTS, Stub(raise_on={"m1": KeyboardInterrupt()}), units=("m1",))
        assert not mm.unit_paths(tmp_path, "m1")[1].exists()

    def test_a_timeout_is_recorded_never_retried_and_the_other_units_still_run(self, tmp_path: Path) -> None:
        stub = Stub(raise_on={"m1": mm.UnitTimeout("m1", 1800.5, 1800.0)})
        o = mm.run_units(tmp_path, INPUTS, stub)
        assert stub.calls.count("m1") == 1, "never retried inside the same invocation"
        assert o.incomplete == ["m1"] and not o.complete
        rec = o.records["m1"]
        assert rec["reason"] == "timeout" and rec["timeout_s"] == 1800.0 and rec["elapsed_s"] == 1800.5
        assert not mm.unit_paths(tmp_path, "m1")[0].exists() and not mm.unit_paths(tmp_path, "m1")[1].exists()
        assert all(mm.check_reusable(tmp_path, u, INPUTS)[0] for u in mm.UNITS if u != "m1")
        # re-invocation recomputes ONLY the incomplete unit
        again = Stub()
        o2 = mm.run_units(tmp_path, INPUTS, again)
        assert again.calls == ["m1"] and o2.complete

    def test_a_crash_is_recorded_as_incomplete_with_its_detail(self, tmp_path: Path) -> None:
        o = mm.run_units(tmp_path, INPUTS, Stub(raise_on={"v1": mm.UnitFailed("v1", "exit code 3; log tail:\nBoom")}))
        assert o.incomplete == ["v1"] and o.records["v1"]["reason"] == "crash" and "Boom" in o.records["v1"]["detail"]


def _args(tmp_path: Path, *extra: str):
    corpus = tmp_path / "corpus.jsonl"
    corpus.write_text("\n")
    return mm.build_parser().parse_args(["--corpus", str(corpus), "--out-dir", str(tmp_path / "out"), *extra])


class TestRunDriver:
    def test_no_result_json_while_any_unit_is_incomplete_and_a_stale_one_is_removed(self, tmp_path: Path) -> None:
        args = _args(tmp_path)
        out = args.out_dir
        out.mkdir(parents=True)
        for name in (mm.RESULT_NAME, mm.DETAIL_NAME):
            (out / name).write_text("{}")  # left over from an earlier, complete invocation
        stub = Stub(raise_on={"m3": mm.UnitTimeout("m3", 5.0, 5.0)})
        rc = mm.run(args, runner=stub, inputs=INPUTS, enforce_clean_tree=False)
        assert rc == 1
        assert not (out / mm.RESULT_NAME).exists() and not (out / mm.DETAIL_NAME).exists()
        incomplete = json.loads((out / mm.INCOMPLETE_NAME).read_text())
        assert incomplete["incomplete"] == ["m3"] and incomplete["units"]["real"]["status"] == "computed"
        # the six finished units persisted as they completed
        assert all(mm.check_reusable(out, u, INPUTS)[0] for u in mm.UNITS if u != "m3")

    def test_a_partial_units_invocation_writes_no_result_even_when_it_completes(self, tmp_path: Path) -> None:
        args = _args(tmp_path, "--units", "real", "m1")
        assert mm.run(args, runner=Stub(), inputs=INPUTS, enforce_clean_tree=False) == 0
        assert not (args.out_dir / mm.RESULT_NAME).exists()

    def test_missing_inputs_and_multi_corpus_mutants_are_errors(self, tmp_path: Path) -> None:
        args = _args(tmp_path)
        args.corpus = [str(tmp_path / "nope.jsonl")]
        with pytest.raises(FileNotFoundError):
            mm.run(args, runner=Stub(), inputs=INPUTS, enforce_clean_tree=False)
        args2 = _args(tmp_path)
        args2.corpus = [args2.corpus[0], args2.corpus[0]]
        with pytest.raises(ValueError, match="exactly one --corpus"):
            mm.run(args2, runner=Stub(), inputs=INPUTS, enforce_clean_tree=False)


class TestCollectInputHashes:
    def test_hashes_track_file_contents_and_are_injectable(self, tmp_path: Path) -> None:
        files = {n: tmp_path / n for n in ("contracts.json", "c.jsonl", "s.jsonl", "x.jsonl")}
        for n, p in files.items():
            p.write_text(n)
        kw: dict[str, Any] = dict(
            corpus=[str(files["c.jsonl"])], sidecar=str(files["s.jsonl"]), crosscheck=[str(files["x.jsonl"])],
            contracts=files["contracts.json"], limit=None, git_head="h" * 40, code_diff_sha256="d", mutant_examples_sha256="m",
        )
        a = mm.collect_input_hashes(**kw)
        assert a["derived_contracts_json"] == mm.sha256_file(files["contracts.json"])
        assert a["corpus"] == {str(files["c.jsonl"]): mm.sha256_file(files["c.jsonl"])}
        assert a["sidecar"] and a["crosscheck"] and a["git_head"] == "h" * 40 and a["limit"] is None
        files["contracts.json"].write_text("changed")
        assert mm.collect_input_hashes(**kw)["derived_contracts_json"] != a["derived_contracts_json"]
        assert mm.collect_input_hashes(**{**kw, "sidecar": None})["sidecar"] == {}

    def test_the_default_git_inputs_resolve_in_this_checkout(self, tmp_path: Path) -> None:
        f = tmp_path / "f"
        f.write_text("x")
        h = mm.collect_input_hashes(corpus=[str(f)], sidecar=None, crosscheck=[], contracts=f, limit=None)
        assert re.fullmatch(r"[0-9a-f]{40}", h["git_head"])
        assert re.fullmatch(r"[0-9a-f]{64}", h["code_diff_sha256"]) and re.fullmatch(r"[0-9a-f]{64}", h["mutant_examples_sha256"])


class TestSubprocessRunner:
    def _run(self, tmp_path: Path, code: str, timeout_s: float, unit: str = "real") -> dict[str, Any]:
        runner = mm.make_subprocess_runner(
            lambda u, worker_out: [sys.executable, "-c", code, str(worker_out)], tmp_path, timeout_s=timeout_s
        )
        return runner(unit)

    def test_payload_round_trip_and_bth_results_path_is_not_inherited(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BTH_RESULTS_PATH", "/should/not/leak.json")
        code = "import json, os, sys; json.dump({'unit': 'real', 'bth': os.environ.get('BTH_RESULTS_PATH')}, open(sys.argv[1], 'w'))"
        payload = self._run(tmp_path, code, 60)
        assert payload == {"unit": "real", "bth": None}
        assert not (tmp_path / mm.UNITS_DIRNAME / "real.worker.json").exists()

    def test_a_unit_that_overruns_its_own_timeout_is_killed_and_recorded(self, tmp_path: Path) -> None:
        marker = tmp_path / "survivor"
        code = f"import time, pathlib; time.sleep(3); pathlib.Path({str(marker)!r}).write_text('alive')"
        with pytest.raises(mm.UnitTimeout) as ei:
            self._run(tmp_path, code, 1.0, unit="m2")
        assert ei.value.unit == "m2" and ei.value.timeout_s == 1.0 and 0.9 < ei.value.elapsed_s < 2.5
        import time as _t

        _t.sleep(4)
        assert not marker.exists(), "the timed-out process must actually be dead"

    def test_a_crash_and_a_silent_exit_are_failures_with_the_log_tail(self, tmp_path: Path) -> None:
        with pytest.raises(mm.UnitFailed, match="exit code 3"):
            self._run(tmp_path, "import sys; print('kaboom-marker'); sys.exit(3)", 30)
        assert "kaboom-marker" in (tmp_path / mm.UNITS_DIRNAME / "real.log").read_text()
        with pytest.raises(mm.UnitFailed, match="wrote no payload"):
            self._run(tmp_path, "pass", 30)


# ---------------------------------------------------------------------------
# end to end on two synthetic rows (in-process runner, then the real subprocess runner)
# ---------------------------------------------------------------------------


def _chat_row(name: str, arguments: dict, utterance: str) -> dict:
    return {
        "messages": [
            {"role": "developer", "content": "sys"},
            {"role": "user", "content": utterance},
            {"role": "assistant", "tool_calls": [{"function": {"name": name, "arguments": arguments}, "type": "function"}]},
        ],
        "tools": [],
        "metadata": "train",
    }


_OK_ROW = _chat_row("transfer", {"source": "src.A1", "destination": "dst.B1", "volume_ul": 50}, "transfer small")
_RAISING_ROW = _chat_row("transfer", {"source": "src.A1", "destination": "dst.B1", "volume_ul": 100000}, "transfer huge")


@pytest.fixture(scope="module")
def tiny_corpus(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("tiny") / "corpus.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in (_OK_ROW, _RAISING_ROW)) + "\n", encoding="utf-8")
    return path


@pytest.fixture(scope="module")
def e2e(tiny_corpus: Path, tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    out = tmp_path_factory.mktemp("e2e") / "out"
    args = mm.build_parser().parse_args(["--corpus", str(tiny_corpus), "--out-dir", str(out)])
    inputs = mm.collect_input_hashes(
        corpus=args.corpus, sidecar=None, crosscheck=[], contracts=args.contracts, limit=None,
        git_head="0" * 40, code_diff_sha256="0" * 64, mutant_examples_sha256="0" * 64,
    )
    counting = Stub()

    def in_process(unit: str) -> dict[str, Any]:
        counting.calls.append(unit)
        return mm.compute_unit(unit, args)

    assert mm.run(args, runner=in_process, inputs=inputs, enforce_clean_tree=False) == 0
    first_calls = list(counting.calls)
    first = json.loads((out / mm.RESULT_NAME).read_text())
    counting.calls.clear()
    assert mm.run(args, runner=in_process, inputs=inputs, enforce_clean_tree=False) == 0
    return {"out": out, "first": first, "first_calls": first_calls, "second_calls": list(counting.calls),
            "second": json.loads((out / mm.RESULT_NAME).read_text())}


class TestEndToEnd:
    def test_result_json_is_exactly_the_sidecar_schema_plus_the_units_block(self, e2e) -> None:
        schema = _schema_toml()
        result = e2e["first"]
        assert set(result) == set(schema) | {"units", "assembly_inputs"}
        for key, type_name in schema.items():
            v = result[key]
            if type_name == "bool":
                assert isinstance(v, bool), key
            elif type_name == "int":
                assert isinstance(v, int) and not isinstance(v, bool), key
            else:
                assert type_name == "str" and isinstance(v, str), key
        assert list(result)[: len(schema)] == list(schema), "schema keys come first, in the sidecar's order"

    def test_units_block_is_provenance_for_all_seven_units(self, e2e) -> None:
        units = e2e["first"]["units"]
        assert list(units) == list(mm.UNITS)
        assert e2e["first_calls"] == list(mm.UNITS)
        for unit, rec in units.items():
            out, stamp = mm.unit_paths(e2e["out"], unit)
            assert rec["status"] == "computed" and rec["source"] == str(out.resolve())
            assert rec["output_sha256"] == mm.sha256_file(out) == json.loads(stamp.read_text())["output_sha256"]
            assert rec["inputs"]["derived_contracts_json"] == mm.sha256_file(mm.DEFAULT_CONTRACTS)

    def test_second_invocation_reuses_all_seven_units_and_reproduces_the_result(self, e2e) -> None:  # AC-18.14 (a), end to end
        assert e2e["second_calls"] == [], "every unit's stamp and output matched: nothing may be recomputed"
        assert {r["status"] for r in e2e["second"]["units"].values()} == {"reused"}
        strip = lambda r: {k: v for k, v in r.items() if k != "units"}  # noqa: E731
        assert strip(e2e["second"]) == strip(e2e["first"])

    def test_the_instrument_is_live_on_the_control_and_the_accounting_holds_by_construction(self, e2e) -> None:
        r = e2e["first"]
        assert r["control_fires"] is True and r["runtime_raised_ops_all_safe_arm"] >= 1  # the negative control can fire
        assert r["real_unsound"] == 0 and r["real_rows_executed"] == 2 and r["real_rows_setup_error"] == 0
        # the accounting identities that are hard terms of the registered outcome, on a corpus that cannot violate them
        assert r["n_338_declined_unattributed"] == 0 and r["n_338_safe_with_reason"] == 0
        assert r["n_338_declined_topology_prefix"] == r["n_pickups_with_preceding_disturber_indep"]
        assert r["n_338_declined_topology_loop"] == 0 and r["n_ops_load_state"] == 0
        assert r["n_338_pickups_attempted"] >= 1
        assert r["runtime_raised_m3"] >= 1 and r["static_338_safe_on_m3"] == 0
        assert r["load_state_channel_effect"] == "widen"
        assert r["baseline_divergences"] == r["baseline_intended_divergences"]
        assert r["real_pick_up_tips_n_ops"] >= 1

    def test_detail_json_carries_the_non_schema_diagnostics(self, e2e) -> None:
        detail = json.loads((e2e["out"] / mm.DETAIL_NAME).read_text())
        assert {"per_method_scope_verdict", "topology_prefix_agreement", "mutants", "baseline", "site_338"} <= set(detail)
        assert detail["topology_prefix_agreement"]["analyzer_side"] == detail["topology_prefix_agreement"]["independent"]

    def test_real_unit_persists_the_three_captures_for_recomputation_from_disk(self, e2e) -> None:
        payload = mm.load_payload(e2e["out"], "real")
        caps = payload["captures"]
        assert caps["n_eligible"] == len(caps["rows"]) == 2
        row = caps["rows"][0]
        assert {"record_id", "calls", "not_planned", "env", "findings", "instructions", "origin"} <= set(row)
        assert any(m.startswith("obs:tip_racks_available=") for m in row["env"])  # the wrapped observation_env_members list
        assert any(i["op"] == "CALL" for i in row["instructions"]) and row["findings"]
        # recomputing the attribution from disk reproduces the published counters
        contracts = json.loads(mm.DEFAULT_CONTRACTS.read_text(encoding="utf-8"))
        again = mm.analyze_338(caps["rows"], contracts)
        for key in ("n_338_pickups_attempted", "n_338_pickups_safe", "n_338_declined_topology_prefix"):
            assert again[key] == e2e["first"][key], key


class TestRealSubprocessRunner:
    def test_two_units_through_real_subprocesses_then_reuse(self, tiny_corpus: Path, tmp_path: Path) -> None:
        out = tmp_path / "out"
        argv = ["--corpus", str(tiny_corpus), "--out-dir", str(out), "--units", "v1", "m3"]
        assert mm.run(mm.build_parser().parse_args(argv), enforce_clean_tree=False) == 0
        for unit in ("v1", "m3"):
            assert (out / mm.UNITS_DIRNAME / f"{unit}.json").is_file() and (out / mm.UNITS_DIRNAME / f"{unit}.stamp.json").is_file()
            assert (out / mm.UNITS_DIRNAME / f"{unit}.log").is_file()
        assert not (out / mm.RESULT_NAME).exists()  # partial invocation
        payload = mm.load_payload(out, "m3")
        assert payload["report"]["by_class"]["m3_lid_on_tip_rack"]["n_runtime_raised_at_338"] >= 1
        stamp_before = (out / mm.UNITS_DIRNAME / "v1.stamp.json").read_text()
        assert mm.run(mm.build_parser().parse_args(argv), enforce_clean_tree=False) == 0
        assert (out / mm.UNITS_DIRNAME / "v1.stamp.json").read_text() == stamp_before, "a reused unit's stamp is untouched"

    def test_the_cli_entry_point_runs_as_a_script_with_a_worker_unit(self, tiny_corpus: Path, tmp_path: Path) -> None:
        worker_out = tmp_path / "w.json"
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--unit", "v1", "--worker-output", str(worker_out), "--corpus", str(tiny_corpus),
             "--out-dir", str(tmp_path / "o")],
            capture_output=True, text=True, timeout=600,
        )
        assert proc.returncode == 0, proc.stderr[-2000:]
        assert json.loads(worker_out.read_text())["unit"] == "v1"


# ---------------------------------------------------------------------------
# review fixes: MAJOR-1 (crashed mutant rows), MAJOR-2 (dirty tree / stamp inputs), MINOR-3/5/6/7
# ---------------------------------------------------------------------------


class TestMutantCrashGate:
    """MAJOR-1: an m3 (or any) class with a crashed row makes the instrument INVALID, never a result."""

    def test_crash_count_separates_crashes_from_construction_skips(self) -> None:
        tip = {"n_error": 5, "n_construction_skipped": 3, "n_static_error": 2, "n_runtime_harness_error": 0}
        assert mm.mutant_crash_count(tip) == 2
        tip_harness = {"n_error": 4, "n_construction_skipped": 3, "n_static_error": 0, "n_runtime_harness_error": 1}
        assert mm.mutant_crash_count(tip_harness) == 1
        # volume_mutants reports no split: analyzer crashes are n_error - n_construction_skipped
        assert mm.mutant_crash_count({"n_error": 5, "n_construction_skipped": 3}) == 2

    def test_NEGATIVE_construction_skips_alone_are_not_crashes(self) -> None:
        """n_error counts every construction-skipped row; a class with only skips must proceed."""
        assert mm.mutant_crash_count({"n_error": 3, "n_construction_skipped": 3, "n_static_error": 0, "n_runtime_harness_error": 0}) == 0
        assert mm.mutant_crash_count({"n_error": 3, "n_construction_skipped": 3}) == 0
        mm.mutant_fields(_all_mutant_payloads())  # the fixture has n_error == n_construction_skipped == 3 everywhere

    @pytest.mark.parametrize("unit", ["m1", "m2", "p3a", "m3", "v1"])
    @pytest.mark.parametrize("counter", ["n_static_error", "n_runtime_harness_error"])
    def test_a_crashed_row_in_any_class_makes_mutant_fields_raise(self, unit: str, counter: str) -> None:
        p = _all_mutant_payloads()
        summary = p[unit]["report"]["by_class"][p[unit]["class"]]
        if unit == "v1":  # volume_mutants has no split counters: derive from n_error
            for k in ("n_static_error", "n_runtime_harness_error"):
                summary.pop(k)
            summary["n_error"] += 1
        else:
            summary[counter] = 1
            summary["n_error"] += 1
        with pytest.raises(mm.MutantAnalyzerError, match=f"unit {unit!r}"):
            mm.mutant_fields(p)

    def _fake_tip_main(self, monkeypatch: pytest.MonkeyPatch, by_class_extra: dict[str, int]):
        import tip_mutants

        def fake_main(argv: list[str]) -> int:
            cls = argv[argv.index("--classes") + 1]
            summary = {"n_total": 4, "n_construction_skipped": 1, "n_error": 1, "n_static_error": 0,
                       "n_runtime_harness_error": 0, "n_ran": 3, "n_raised_as_expected": 3,
                       "static_verdict_at_raising_index": {"will_fail": 3}, **by_class_extra}
            Path(argv[argv.index("--report") + 1]).write_text(
                json.dumps({"by_class": {cls: summary}, "hard_violations": [], "gate_passed": True})
            )
            return 0

        monkeypatch.setattr(tip_mutants, "main", fake_main)

    def test_the_unit_worker_refuses_a_crashed_class_and_the_control_proceeds(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        args = _args(tmp_path)
        self._fake_tip_main(monkeypatch, {"n_static_error": 1, "n_error": 2})
        with pytest.raises(mm.MutantAnalyzerError, match="crashed"):
            mm.compute_tip_mutants("m3", args)
        self._fake_tip_main(monkeypatch, {})  # NEGATIVE control: same shape, zero crashes -> a payload
        assert mm.compute_tip_mutants("m3", args)["unit"] == "m3"

    def test_an_invalid_instrument_at_assembly_is_incomplete_not_a_result(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        args = _args(tmp_path)

        def _boom(*_a: Any, **_k: Any) -> Any:
            raise mm.MutantAnalyzerError("unit 'm3': 1 mutant row(s) crashed")

        monkeypatch.setattr(mm, "assemble_result", _boom)
        rc = mm.run(args, runner=Stub(), inputs=INPUTS, enforce_clean_tree=False)
        assert rc == 1 and not (args.out_dir / mm.RESULT_NAME).exists() and not (args.out_dir / mm.DETAIL_NAME).exists()
        inc = json.loads((args.out_dir / mm.INCOMPLETE_NAME).read_text())
        assert "crashed" in inc["invalid_instrument"] and inc["incomplete"] == []


class TestArmAgreementAndAssemblyProvenance:
    def _payloads(self, e2e) -> dict[str, dict[str, Any]]:
        return {u: mm.load_payload(e2e["out"], u) for u in mm.UNITS}

    def test_control_the_untouched_payloads_assemble_and_record_the_inputs_by_hash(self, e2e) -> None:
        _result, detail = mm.assemble_result(self._payloads(e2e), mm.DEFAULT_CONTRACTS, mm.DEFAULT_BASELINE)
        assert detail["assembly_inputs"]["contracts"] == {
            "path": str(mm.DEFAULT_CONTRACTS), "sha256": mm.sha256_file(mm.DEFAULT_CONTRACTS)}
        assert detail["assembly_inputs"]["baseline"] == {
            "path": str(mm.DEFAULT_BASELINE), "sha256": mm.sha256_file(mm.DEFAULT_BASELINE)}
        assert e2e["first"]["assembly_inputs"] == detail["assembly_inputs"]  # also in result.json's provenance
        assert set(detail["mutant_row_counts"]) == {"m1", "m2", "p3a", "m3", "v1"}

    @pytest.mark.parametrize("key", ["rows_executed", "rows_setup_error", "operations_executed"])
    def test_NEGATIVE_the_arms_must_agree_on_each_runtime_denominator(self, e2e, key: str) -> None:
        p = self._payloads(e2e)
        p["all_safe"]["summary_flat"][key] += 1
        with pytest.raises(mm.ArmDisagreement, match=key):
            mm.assemble_result(p, mm.DEFAULT_CONTRACTS, mm.DEFAULT_BASELINE)

    def test_an_arm_disagreement_makes_the_run_incomplete(self, e2e, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        args = _args(tmp_path)
        payloads = self._payloads(e2e)
        payloads["all_safe"]["summary_flat"]["operations_executed"] += 1
        runner = lambda unit: payloads[unit]  # noqa: E731 -- stub returning the tampered payloads
        rc = mm.run(args, runner=runner, inputs=INPUTS, enforce_clean_tree=False)
        assert rc == 1 and not (args.out_dir / mm.RESULT_NAME).exists()
        assert "operations_executed" in json.loads((args.out_dir / mm.INCOMPLETE_NAME).read_text())["invalid_instrument"]

    def test_direct_indexing_missing_pickup_or_load_state_or_receiver_state_raises(self, e2e) -> None:
        p = self._payloads(e2e)
        no_pick = json.loads(json.dumps(p))
        del no_pick["real"]["scope_verdict_by_method"][mm.PICKUP]
        with pytest.raises(KeyError):
            mm.assemble_result(no_pick, mm.DEFAULT_CONTRACTS, mm.DEFAULT_BASELINE)
        with pytest.raises(KeyError):
            mm.analyze_338([], {"contracts": {}})  # no "receiver_state" key: not defaulted to {}
        with pytest.raises(KeyError):
            mm.independent_scan([], {"contracts": {}})


class TestMissingContractRaises:
    def test_a_338_finding_on_a_call_with_no_contract_raises_instead_of_attributing_kind(self) -> None:
        contracts = _mini_contracts()
        del contracts["contracts"]["LiquidHandler.pick_up_tips"]
        # resolve_site_338 needs a :338 guard somewhere: keep one on another entry
        site = {"file": "f.py", "lineno": 338, "qualname": "_check_tip_racks_available"}
        contracts["contracts"]["LiquidHandler.setup"]["guards"] = [
            {"site": site, "raises": "ValueError", "condition": "not rack._available_for_tip_handling", "kind": "raise_guard"}
        ]
        with pytest.raises(RuntimeError, match="no contract"):
            mm.analyze_338([_row([{"method": "aspirate"}])], contracts)
        with pytest.raises(RuntimeError, match="no contract"):
            mm.independent_scan([_row([{"method": "aspirate"}])], contracts)

    def test_a_contract_without_a_338_guard_raises(self) -> None:
        contracts = _mini_contracts()
        site = {"file": "f.py", "lineno": 338, "qualname": "_check_tip_racks_available"}
        contracts["contracts"]["LiquidHandler.aspirate"]["guards"] = [
            {"site": site, "raises": "ValueError", "condition": "not rack._available_for_tip_handling", "kind": "raise_guard"}
        ]
        contracts["contracts"]["LiquidHandler.pick_up_tips"]["guards"] = []
        with pytest.raises(RuntimeError, match="no :338 guard"):
            mm.analyze_338([_row([{"method": "aspirate"}])], contracts)


def _git_run(cwd: Path, *args: str) -> None:
    subprocess.run(["git", "-c", "commit.gpgsign=false", *args], cwd=cwd, check=True, capture_output=True)


def _init_repo(root: Path) -> Path:
    files = [
        "plr-sema/src/a.py", "plr-sema/eval/b.py", "plr-sema/data/c.json", "training/d.py",
        "praxis/backend/core/simulation/chatterbox_runner.py", "README.md",
    ]
    for rel in files:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(rel)
    _git_run(root, "init", "-q")
    _git_run(root, "config", "user.email", "t@example.com")
    _git_run(root, "config", "user.name", "t")
    _git_run(root, "add", "-A")
    _git_run(root, "commit", "-q", "-m", "init")
    sub = root / "external" / "pylabrobot"
    sub.mkdir(parents=True)
    (sub / "x.txt").write_text("x")
    _git_run(sub, "init", "-q")
    _git_run(sub, "config", "user.email", "t@example.com")
    _git_run(sub, "config", "user.name", "t")
    _git_run(sub, "add", "-A")
    _git_run(sub, "commit", "-q", "-m", "init")
    return root


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    return _init_repo(tmp_path / "repo")


class TestCleanTreeRefusal:
    def test_a_clean_tree_passes(self, repo: Path) -> None:
        mm.check_clean_tree(repo)

    @pytest.mark.parametrize(
        "rel",
        ["plr-sema/src/a.py", "plr-sema/eval/b.py", "plr-sema/data/c.json", "training/d.py",
         "praxis/backend/core/simulation/chatterbox_runner.py"],
    )
    def test_a_dirty_tracked_file_under_a_code_path_is_refused(self, repo: Path, rel: str) -> None:
        (repo / rel).write_text("edited")
        with pytest.raises(mm.DirtyTreeError, match="REFUSING TO RUN") as ei:
            mm.check_clean_tree(repo)
        assert rel in str(ei.value)

    @pytest.mark.parametrize("rel", ["plr-sema/eval/new_module.py", "training/sub/dir/new.py", "plr-sema/src/plr_sema/x.py",
                                     "praxis/backend/core/simulation/other.py"])
    def test_an_UNTRACKED_file_under_a_code_path_is_refused(self, repo: Path, rel: str) -> None:
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text("x")
        with pytest.raises(mm.DirtyTreeError) as ei:
            mm.check_clean_tree(repo)
        assert rel in str(ei.value)  # --untracked-files=all: the file, not just its directory

    @pytest.mark.parametrize("how", ["modified", "untracked"])
    def test_a_dirty_submodule_is_refused(self, repo: Path, how: str) -> None:
        sub = repo / "external" / "pylabrobot"
        (sub / ("x.txt" if how == "modified" else "new.txt")).write_text("dirty")
        with pytest.raises(mm.DirtyTreeError, match="submodule"):
            mm.check_clean_tree(repo)

    def test_an_unreadable_submodule_is_refused_not_ignored(self, tmp_path: Path) -> None:
        root = _init_repo(tmp_path / "r")
        import shutil

        shutil.rmtree(root / "external")
        with pytest.raises(mm.DirtyTreeError, match="failed"):
            mm.check_clean_tree(root)

    def test_unrelated_paths_and_bathos_lock_files_are_allowed(self, repo: Path) -> None:
        for rel in (".claude/settings.json", ".mcp.json", ".praxia/audits.jsonl", "outputs/x/result.json",
                    "plr-sema/eval/plr10_characterize.bth.fd63e9cd-4310.bth.lock.toml",
                    "training/foo.bth.lock.toml", "README.md"):
            (repo / rel).parent.mkdir(parents=True, exist_ok=True)
            (repo / rel).write_text("x")
        mm.check_clean_tree(repo)

    def test_a_lock_file_does_not_mask_a_real_dirty_file(self, repo: Path) -> None:
        (repo / "plr-sema/eval/a.bth.lock.toml").write_text("x")
        (repo / "training/d.py").write_text("edited")
        with pytest.raises(mm.DirtyTreeError) as ei:
            mm.check_clean_tree(repo)
        assert "training/d.py" in str(ei.value) and "bth.lock.toml" not in str(ei.value)

    def test_run_removes_the_stale_result_before_refusing_or_failing_input_checks(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:  # MINOR-5
        args = _args(tmp_path)
        out = args.out_dir
        out.mkdir(parents=True)
        for name in (mm.RESULT_NAME, mm.DETAIL_NAME, mm.INCOMPLETE_NAME):
            (out / name).write_text("{}")

        def _refuse() -> None:
            raise mm.DirtyTreeError("REFUSING TO RUN: test")

        monkeypatch.setattr(mm, "check_clean_tree", _refuse)
        with pytest.raises(mm.DirtyTreeError):
            mm.run(args, runner=Stub(), inputs=INPUTS)
        assert not any((out / n).exists() for n in (mm.RESULT_NAME, mm.DETAIL_NAME, mm.INCOMPLETE_NAME))
        # and a failing INPUT check (tree check off) also leaves nothing stale behind
        (out / mm.RESULT_NAME).write_text("{}")
        args.corpus = [str(tmp_path / "nope.jsonl")]
        with pytest.raises(FileNotFoundError):
            mm.run(args, runner=Stub(), inputs=INPUTS, enforce_clean_tree=False)
        assert not (out / mm.RESULT_NAME).exists()

    def test_the_cli_refuses_with_a_nonzero_exit_and_no_result(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog) -> None:
        corpus = tmp_path / "corpus.jsonl"
        corpus.write_text("\n")
        out = tmp_path / "out"

        def _refuse() -> None:
            raise mm.DirtyTreeError("REFUSING TO RUN: 1 modified/untracked path(s): plr-sema/eval/x.py")

        monkeypatch.setattr(mm, "check_clean_tree", _refuse)
        rc = mm.main(["--corpus", str(corpus), "--out-dir", str(out)])
        assert rc == 2 and not (out / mm.RESULT_NAME).exists()
        assert "REFUSING TO RUN" in caplog.text

    def test_there_is_no_cli_escape_hatch(self) -> None:
        assert "clean" not in " ".join(a for act in mm.build_parser()._actions for a in act.option_strings)


class TestNewStampInputs:
    def test_the_submodule_head_and_the_runner_hash_are_collected_and_injectable(self, tmp_path: Path) -> None:
        f = tmp_path / "f"
        f.write_text("x")
        h = mm.collect_input_hashes(corpus=[str(f)], sidecar=None, crosscheck=[], contracts=f, limit=None)
        assert re.fullmatch(r"[0-9a-f]{40}", h["pylabrobot_head"])
        assert h["chatterbox_runner_sha256"] == mm.sha256_file(mm.CHATTERBOX_RUNNER)
        kw: dict[str, Any] = dict(corpus=[str(f)], sidecar=None, crosscheck=[], contracts=f, limit=None,
                                  git_head="h", code_diff_sha256="d", mutant_examples_sha256="m")
        a = mm.collect_input_hashes(**kw, pylabrobot_head="p1", chatterbox_runner_sha256="c1")
        assert a["pylabrobot_head"] == "p1" and a["chatterbox_runner_sha256"] == "c1"
        assert mm.collect_input_hashes(**kw, pylabrobot_head="p2", chatterbox_runner_sha256="c1") != a
        assert mm.collect_input_hashes(**kw, pylabrobot_head="p1", chatterbox_runner_sha256="c2") != a

    def test_the_code_diff_pathspec_covers_the_simulation_runner_directory(self) -> None:
        assert "praxis/backend/core/simulation" in mm.CODE_PATHS
