"""Unit tests for `tip_mutants`'s m3 lidded-rack class (spec 260929
`260929_plr-sema-plr1-tip-effect-increment.md` §18.9 / AC-18.16, backlog #5622,
task 260929_plr-1.0-migration, T63 step 2a) and its `--classes` filter.

Tiny, in-memory, single-example runs plus a handful of one-corpus-row `main`
runs -- never the benchmark. Every positive control has a paired negative
control that must fail (the instrument is untested otherwise):

* the m3 mutator's runtime effect is checked against the UNMUTATED base (which
  must NOT raise at `:338`);
* the `:338` decline reason is checked as `"observation"` on the lidded row and
  `None` on the unlidded one, so the decline is attributable to the lid;
* `main`'s m3 hard terms are exercised with a genuine pass AND with two
  fault injections (a wrong `:338` SAFE, and a mutator that lids nothing), each
  of which must trip its own violation.
"""

from __future__ import annotations

import copy
import dataclasses
import importlib
import json
import sys
from pathlib import Path

import pytest

_EVAL_DIR = Path(__file__).resolve().parents[1] / "eval"
sys.path.insert(0, str(_EVAL_DIR))

import oracle_common as oc  # noqa: E402
import tip_mutants as tm  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = REPO_ROOT / "training" / "examples"
CONTRACTS_PATH = REPO_ROOT / "plr-sema" / "data" / "derived_contracts.json"

M3 = "m3_lid_on_tip_rack"
SITE_338 = "external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:338:_check_tip_racks_available"


def _example(name: str = "aspirate_dispense_drop") -> dict:
    payload = json.loads((EXAMPLES_DIR / f"{name}.json").read_text(encoding="utf-8"))
    return {k: payload[k] for k in ("call_sequence", "intent_record", "deck_layout")}


def _result(**kw) -> tm.MutantResult:
    base = dict(
        base_id="b", mutant_class=M3, ran=True, error=None, raised_exc_class="ValueError",
        raised_as_expected=True, raising_index=0, static_verdict_at_index="unknown",
        unsound_safe=False, unsound_will_fail_elsewhere=False,
    )
    base.update(kw)
    return tm.MutantResult(**base)


# ---------------------------------------------------------------------------
# the mutator (pure)
# ---------------------------------------------------------------------------


class TestMutator:
    def test_registered_in_the_class_tables(self) -> None:
        assert tm._MUTATORS[M3] is tm.make_m3_lid_on_tip_rack
        assert tm._EXPECTED_EXC[M3] == "ValueError"
        assert M3 in tm._ALL_CLASSES

    def test_lids_the_first_pickups_rack_and_leaves_the_calls_alone(self) -> None:
        ex = _example()
        before = copy.deepcopy(ex)
        mutant = tm.make_m3_lid_on_tip_rack(ex)
        assert mutant is not None
        assert mutant["deck_layout"]["lidded_tip_racks"] == ["tip_rack"]
        assert mutant["call_sequence"] == ex["call_sequence"]
        # the other layout keys survive; the base example is not mutated in place
        assert mutant["deck_layout"]["resources"] == ex["deck_layout"]["resources"]
        assert ex == before

    @pytest.mark.parametrize(
        ("at", "rack"),
        [
            (["rack_b.A1", "rack_b.B1"], "rack_b"),  # list: first element, dotted
            ("rack_c.H12", "rack_c"),  # bare string
            (["rack_d[0]"], "rack_d"),  # bracket form: split before '['
            (["  rack_e .A1"], "rack_e"),  # stripped
        ],
    )
    def test_rack_name_is_the_base_name_of_the_first_pickups_at(self, at, rack) -> None:
        ex = _example()
        ex["call_sequence"][0]["params"]["at"] = at
        mutant = tm.make_m3_lid_on_tip_rack(ex)
        assert mutant is not None and mutant["deck_layout"]["lidded_tip_racks"] == [rack]

    def test_uses_the_FIRST_pickup_not_a_later_one(self) -> None:
        ex = _example()
        ex["call_sequence"].append({"name": "pick_up_tips", "params": {"at": ["other_rack.A1"]}})
        mutant = tm.make_m3_lid_on_tip_rack(ex)
        assert mutant["deck_layout"]["lidded_tip_racks"] == ["tip_rack"]

    def test_none_or_absent_layout_gets_a_fresh_layout_carrying_only_the_lids(self) -> None:
        for layout in (None, "absent"):
            ex = _example()
            if layout is None:
                ex["deck_layout"] = None
            else:
                del ex["deck_layout"]
            mutant = tm.make_m3_lid_on_tip_rack(ex)
            assert mutant is not None
            assert mutant["deck_layout"] == {"lidded_tip_racks": ["tip_rack"]}

    def test_existing_lids_are_kept_and_the_rack_is_added_once(self) -> None:
        ex = _example()
        ex["deck_layout"]["lidded_tip_racks"] = ["tip_rack_2"]
        mutant = tm.make_m3_lid_on_tip_rack(ex)
        assert mutant["deck_layout"]["lidded_tip_racks"] == ["tip_rack_2", "tip_rack"]
        again = tm.make_m3_lid_on_tip_rack(mutant)
        assert again["deck_layout"]["lidded_tip_racks"] == ["tip_rack_2", "tip_rack"]  # no duplicate

    def test_a_DeckLayout_instance_is_carried_over_as_its_dict_form(self) -> None:
        verifier = oc._import_verifier()  # resolves `verify` or `training.verify`, whichever is installed
        DeckLayout = importlib.import_module(verifier.__package__ + ".deck").DeckLayout

        ex = _example()
        ex["deck_layout"] = DeckLayout(resources={"reagent_trough": "Trough"}, seed_volumes={"reagent_trough": 5000.0})
        mutant = tm.make_m3_lid_on_tip_rack(ex)
        assert mutant["deck_layout"]["resources"] == {"reagent_trough": "Trough"}
        assert mutant["deck_layout"]["lidded_tip_racks"] == ["tip_rack"]
        assert DeckLayout(**mutant["deck_layout"]).lidded_tip_racks == ["tip_rack"]  # and it round-trips

    def test_no_pickup_returns_none(self) -> None:
        ex = _example()
        ex["call_sequence"] = [c for c in ex["call_sequence"] if c["name"] != "pick_up_tips"]
        assert tm.make_m3_lid_on_tip_rack(ex) is None

    @pytest.mark.parametrize("at", [None, [], [42], 42, [""], [".A1"], "[0]"])
    def test_unparseable_at_returns_none(self, at) -> None:
        ex = _example()
        ex["call_sequence"][0]["params"]["at"] = at
        assert tm.make_m3_lid_on_tip_rack(ex) is None

    def test_a_pickup_without_params_returns_none(self) -> None:
        ex = _example()
        ex["call_sequence"][0] = {"name": "pick_up_tips"}
        assert tm.make_m3_lid_on_tip_rack(ex) is None


# ---------------------------------------------------------------------------
# the two m3 predicates (pure), with their negative controls
# ---------------------------------------------------------------------------


class TestPredicates:
    def test_raised_at_338_by_message(self) -> None:
        r = _result(runtime_error=("ValueError: Cannot pick up tips from 'tip_rack': something is stacked on top of it.", None))
        assert tm.raised_at_338(r, 0)

    def test_raised_at_338_by_frame(self) -> None:
        frames = [{"file": "x.py", "lineno": 1, "qualname": "LiquidHandler.pick_up_tips"},
                  {"file": "x.py", "lineno": 338, "qualname": "_check_tip_racks_available"}]
        assert tm.raised_at_338(_result(runtime_error=("ValueError: something else", frames)), 0)

    def test_NEGATIVE_a_valueerror_from_elsewhere_does_not_count(self) -> None:
        """A `ValueError` from `pick_up_tips`'s position-uniqueness check (or from `build_setup`) must not count."""
        frames = [{"file": "x.py", "lineno": 1, "qualname": "LiquidHandler.pick_up_tips"}]
        r = _result(runtime_error=("ValueError: Positions must be unique.", frames))
        assert not tm.raised_at_338(r, 0)

    def test_NEGATIVE_wrong_index_wrong_class_unran_or_no_pickup_do_not_count(self) -> None:
        msg = ("ValueError: something is stacked on top of it.", None)
        assert tm.raised_at_338(_result(runtime_error=msg), 0)
        assert not tm.raised_at_338(_result(runtime_error=msg, raising_index=3), 0)  # not at the pickup index
        assert not tm.raised_at_338(_result(runtime_error=msg, raising_index=None), 0)  # deck-build failure: no index
        assert not tm.raised_at_338(_result(runtime_error=msg, raised_exc_class="RuntimeError"), 0)
        assert not tm.raised_at_338(_result(runtime_error=msg, ran=False), 0)
        assert not tm.raised_at_338(_result(runtime_error=msg), None)
        assert not tm.raised_at_338(_result(), 0)  # default runtime_error == (None, None)

    def test_static_338_safe_needs_a_338_sited_safe(self) -> None:
        raised = dict(runtime_error=("ValueError: something is stacked on top of it.", None))
        assert tm.static_338_safe(_result(site_verdicts_at_index={SITE_338: ["unknown", "safe"]}, **raised), 0)

    def test_NEGATIVE_static_338_safe_ignores_other_sites_and_non_safe_verdicts(self) -> None:
        raised = dict(runtime_error=("ValueError: something is stacked on top of it.", None))
        other = "external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:725:LiquidHandler.pick_up_tips"
        assert not tm.static_338_safe(_result(site_verdicts_at_index={other: ["safe"]}, **raised), 0)
        assert not tm.static_338_safe(_result(site_verdicts_at_index={SITE_338: ["unknown"]}, **raised), 0)
        assert not tm.static_338_safe(_result(site_verdicts_at_index={SITE_338: ["will_fail"]}, **raised), 0)
        assert not tm.static_338_safe(_result(site_verdicts_at_index={}, **raised), 0)
        # a :338 SAFE at a row that did NOT raise at :338 is not "wrong": there was nothing to be unsound about
        assert not tm.static_338_safe(_result(site_verdicts_at_index={SITE_338: ["safe"]}), 0)


class TestMutantResultBackwardCompat:
    def test_positional_construction_still_valid_and_new_fields_default(self) -> None:
        r = tm.MutantResult("b", "m1_remove_pickup", True, None, None, False, None, None, False, False)
        assert r.site_verdicts_at_index == {} and r.runtime_error == (None, None)
        # the two new fields are the TRAILING ones, in the order the spec names them
        assert [f.name for f in dataclasses.fields(tm.MutantResult)][-2:] == ["site_verdicts_at_index", "runtime_error"]

    def test_defaults_are_not_shared_between_instances(self) -> None:
        a = tm.MutantResult("a", "m1_remove_pickup", True, None, None, False, None, None, False, False)
        b = tm.MutantResult("b", "m1_remove_pickup", True, None, None, False, None, None, False, False)
        a.site_verdicts_at_index["k"] = ["safe"]
        assert b.site_verdicts_at_index == {}


class TestClassFilter:
    def test_default_is_every_class_in_canonical_order(self) -> None:
        assert tm._resolve_classes(None) == list(tm._ALL_CLASSES)
        assert tm._resolve_classes([]) == list(tm._ALL_CLASSES)

    def test_aliases_full_names_and_comma_lists(self) -> None:
        assert tm._resolve_classes(["m3"]) == [M3]
        assert tm._resolve_classes(["p3a,m1"]) == ["m1_remove_pickup", "p3a_pickup_already_held"]
        assert tm._resolve_classes(["m2_duplicate_pickup", "m2", "m3"]) == ["m2_duplicate_pickup", M3]

    def test_unknown_class_is_an_error_not_a_silent_skip(self) -> None:
        with pytest.raises(ValueError, match="unknown mutant class"):
            tm._resolve_classes(["m9"])
        with pytest.raises(ValueError, match="empty"):
            tm._resolve_classes([","])


# ---------------------------------------------------------------------------
# end to end on ONE inline example (simulator + analyzer)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def m3_row() -> tuple[dict, tm.MutantResult]:
    ex = _example()
    contracts_json = CONTRACTS_PATH.read_text(encoding="utf-8")
    result = tm.run_one_mutant(
        "ex_aspirate_dispense", M3, ex, contracts_json, oc.param_names_from_contracts(contracts_json),
        tm.make_m3_lid_on_tip_rack, tm._EXPECTED_EXC[M3],
    )
    return ex, result


class TestEndToEnd:
    def test_the_simulator_raises_at_338_at_the_pickup_index(self, m3_row) -> None:
        ex, r = m3_row
        pickup = tm._first_pickup_index(ex["call_sequence"])
        assert r.ran and r.error is None, r.error
        assert r.raised_as_expected and r.raised_exc_class == "ValueError"
        assert r.raising_index == pickup
        assert "something is stacked on top of it" in (r.runtime_error[0] or "")
        assert any(f["qualname"] == "_check_tip_racks_available" for f in r.runtime_error[1] or ())
        assert tm.raised_at_338(r, pickup)

    def test_no_338_sited_safe_appears_at_that_index(self, m3_row) -> None:
        ex, r = m3_row
        pickup = tm._first_pickup_index(ex["call_sequence"])
        sites_338 = {s: v for s, v in r.site_verdicts_at_index.items() if s.endswith(":_check_tip_racks_available")}
        assert sites_338, "the :338 site must be reported at the pickup index (site-keyed capture is live)"
        assert all("safe" not in v for v in sites_338.values()), sites_338
        assert not tm.static_338_safe(r, pickup)
        assert not r.unsound_safe and not r.unsound_will_fail_elsewhere

    def test_NEGATIVE_the_unmutated_base_does_not_raise_at_338(self, m3_row) -> None:
        """Without the lid nothing raises: the m3 raise is caused by the mutation, not by the harness."""
        ex, _ = m3_row
        rt = oc.run_runtime(ex)
        assert rt.passed and rt.error is None and rt.exc_class is None

    def test_the_findings_sink_is_restored_and_chain_composed(self) -> None:
        seen: list[str] = []
        prior = oc.FINDINGS_SINK
        oc.FINDINGS_SINK = lambda row_id, findings: seen.append(row_id)
        try:
            contracts_json = CONTRACTS_PATH.read_text(encoding="utf-8")
            tm.run_one_mutant(
                "ex_chain", M3, _example(), contracts_json, oc.param_names_from_contracts(contracts_json),
                tm.make_m3_lid_on_tip_rack, tm._EXPECTED_EXC[M3],
            )
            assert seen == ["ex_aspirate_dispense"]  # the enclosing sink still saw the row (the intent record's id)
            assert oc.FINDINGS_SINK is not prior and callable(oc.FINDINGS_SINK)  # ours is back in place, not the inner one
        finally:
            oc.FINDINGS_SINK = prior

    def test_the_sink_is_restored_to_none_when_there_was_none(self, m3_row) -> None:
        assert oc.FINDINGS_SINK is None

    def test_the_decline_reason_is_observation_on_the_lidded_row_and_none_on_the_unlidded_one(self) -> None:
        """AC-18.16's second assertion: `tip_racks_decline_reason` returns "observation" on m3 rows -- and the
        SAME call on the unlidded base returns None, so the decline is attributable to the lid."""
        from plr_sema.check import ir
        from plr_sema.check import predicate as pred

        ex = _example()
        pickup_call = ir.Call(receiver=0, receiver_type="LiquidHandler", method="pick_up_tips", kwargs={})

        def reason(example: dict) -> str | None:
            rt = oc.run_runtime(example)
            assert rt.plr_observation is not None
            env = oc.observation_env_members(rt.plr_observation, oc.resources_from_example(example))
            ctx = pred._Ctx(
                call=pickup_call, resources_by_slot={}, param_defaults={}, bindings_by_name={}, depth=1,
                channel_kwarg=None, channels=None, env=env, class_hierarchy=None,
                guard_kind="raise_guard", rack_topology_prefix_ok=True, rack_topology_loop_ok=True,
            )
            return pred.tip_racks_decline_reason(ctx)

        assert reason(tm.make_m3_lid_on_tip_rack(ex)) == "observation"
        assert reason(ex) is None


# ---------------------------------------------------------------------------
# main(): the m3 branch and --classes, on one corpus row
# ---------------------------------------------------------------------------


def _corpus_row() -> dict:
    return {
        "messages": [
            {"role": "developer", "content": "sys"},
            {"role": "user", "content": "transfer small"},
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "function": {
                            "name": "transfer",
                            "arguments": {"source": "src.A1", "destination": "dst.B1", "volume_ul": 50},
                        },
                        "type": "function",
                    }
                ],
            },
        ],
        "tools": [],
        "metadata": "train",
    }


@pytest.fixture(scope="module")
def corpus(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("m3corpus") / "corpus.jsonl"
    path.write_text(json.dumps(_corpus_row()) + "\n", encoding="utf-8")
    return path


def _main(corpus: Path, tmp_path: Path, *classes: str) -> tuple[int, dict]:
    report = tmp_path / "report.json"
    argv = ["--corpus", str(corpus), "--report", str(report)]
    if classes:
        argv += ["--classes", *classes]
    rc = tm.main(argv)
    return rc, json.loads(report.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def m3_main_run(corpus: Path, tmp_path_factory: pytest.TempPathFactory) -> tuple[int, dict]:
    return _main(corpus, tmp_path_factory.mktemp("m3main"), "m3")


class TestMain:
    def test_m3_only_run_reports_the_two_keys_and_only_m3(self, m3_main_run) -> None:
        rc, report = m3_main_run
        assert report["classes"] == [M3]
        assert list(report["by_class"]) == [M3]
        s = report["by_class"][M3]
        assert s["n_runtime_raised_at_338"] >= 1
        assert s["n_static_338_safe"] == 0
        assert s["n_ran"] >= 1
        assert report["hard_violations"] == [] and report["gate_passed"] is True and rc == 0
        # no move-family scan was needed, so none was run
        assert report["n_move_corpus_bases"] == 0 and report["n_move_example_bases"] == 0

    def test_p3a_only_run_skips_the_pickup_population(self, corpus: Path, tmp_path: Path) -> None:
        _rc, report = _main(corpus, tmp_path, "p3a")
        assert list(report["by_class"]) == ["p3a_pickup_already_held"]
        assert report["n_corpus_bases"] == 0 and report["n_example_bases"] == 0

    def test_m1_alias_selects_only_m1(self, corpus: Path, tmp_path: Path) -> None:
        _rc, report = _main(corpus, tmp_path, "m1")
        assert list(report["by_class"]) == ["m1_remove_pickup"]

    def test_unknown_class_is_a_usage_error(self, corpus: Path, tmp_path: Path) -> None:
        with pytest.raises(SystemExit):
            _main(corpus, tmp_path, "m9")

    def test_NEGATIVE_a_wrong_338_safe_trips_the_m3_hard_violation(
        self, corpus: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Fault injection: an analyzer that decided `:338` SAFE on a lidded rack. The gate must go red."""
        real = tm.run_one_mutant

        def _poisoned(*args, **kwargs):
            res = real(*args, **kwargs)
            if res.mutant_class == M3:
                res.site_verdicts_at_index = {**res.site_verdicts_at_index, SITE_338: ["safe"]}
            return res

        monkeypatch.setattr(tm, "run_one_mutant", _poisoned)
        rc, report = _main(corpus, tmp_path, "m3")
        assert report["by_class"][M3]["n_static_338_safe"] >= 1
        assert any("static_338_safe_on_m3" in v for v in report["hard_violations"]), report["hard_violations"]
        assert report["gate_passed"] is False and rc == 1

    def test_NEGATIVE_an_m3_that_lids_nothing_trips_runtime_raised_zero(
        self, corpus: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Fault injection: a mutator that returns the base unchanged never raises at `:338`; the vacuous control
        must be reported as a hard violation, not silently pass."""
        monkeypatch.setitem(tm._MUTATORS, M3, lambda example: copy.deepcopy(example))
        rc, report = _main(corpus, tmp_path, "m3")
        assert report["by_class"][M3]["n_runtime_raised_at_338"] == 0
        assert any("runtime_raised_m3 = 0" in v for v in report["hard_violations"]), report["hard_violations"]
        assert report["gate_passed"] is False and rc == 1


# ---------------------------------------------------------------------------
# review MAJOR-1: a crashed static side must never count toward the m3 control
# ---------------------------------------------------------------------------


class TestStaticCrashIsNotAControl:
    def test_a_static_crash_row_is_not_counted_as_raised_at_338(self) -> None:
        """`run_one_mutant`'s except path returns `ran=True, error="static:..."` WITH the runtime error text: the raise is
        real but the analyzer never produced a verdict, so the row must not satisfy `runtime_raised_m3 > 0`."""
        msg = ("ValueError: Cannot pick up tips: something is stacked on top of it.", None)
        assert tm.raised_at_338(_result(runtime_error=msg), 0)  # control: same row, no crash, counts
        crashed = _result(runtime_error=msg, error="static:boom")
        assert crashed.ran and not tm.raised_at_338(crashed, 0)
        poisoned = _result(runtime_error=msg, error="static:boom", site_verdicts_at_index={SITE_338: ["safe"]})
        assert not tm.static_338_safe(poisoned, 0)

    def test_an_analyzer_that_raises_on_every_row_is_reported_as_crashes_and_a_hard_violation(
        self, corpus: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _boom(*_a, **_k):
            raise RuntimeError("analyzer crashed")

        monkeypatch.setattr(oc, "run_static_calls", _boom)
        rc, report = _main(corpus, tmp_path, "m3")
        s = report["by_class"][M3]
        assert s["n_static_error"] >= 1 and s["n_runtime_harness_error"] == 0
        assert s["n_runtime_raised_at_338"] == 0  # the crash did NOT pass the control vacuously
        assert any("runtime_raised_m3 = 0" in v for v in report["hard_violations"]) and rc == 1

    def test_control_the_crash_counters_are_zero_on_a_healthy_run(self, m3_main_run) -> None:
        _rc, report = m3_main_run
        s = report["by_class"][M3]
        assert s["n_static_error"] == 0 and s["n_runtime_harness_error"] == 0
        assert s["n_error"] == s["n_construction_skipped"]  # n_error is crashes + construction skips only
