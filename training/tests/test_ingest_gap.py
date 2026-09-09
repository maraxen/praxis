"""Tests for `ingest.gap` — the G1 coverage-gap gate (§6, Task 7).

Drives `gap.run_gap()`/`gap.gate()` in-process, mirroring test_ingest_audit_gate.py's
path-injection convention (§5.5): no CLI path flags exist for these, tests call the
functions directly.

Synthetic-corpus fixtures use a single unmapped param name ("x") on every call so
`value_form`'s classification is driven purely by Python TYPE (bool / int / float /
str / NoneType), independent of PARAM_NAMESPACE -- which exercises the same
`spec is None` / `unmapped_params` path C1 added, for free, on every fixture.
"""

import json
from collections import Counter
from pathlib import Path

from ingest import cli, gap, recipes
from ingest.versions import T1_INVARIANT

from coxswain.plr.tool_schema import PHASE2_TOOL_NAMES, TOOL_SCHEMA

LH_VERBS = tuple(sorted(
    name for name in PHASE2_TOOL_NAMES if TOOL_SCHEMA[name].receiver_type == "liquid_handler"
))
T1_ZERO_VERBS = frozenset(T1_INVARIANT["verbs"])
T1_NONZERO_VERBS = frozenset(LH_VERBS) - T1_ZERO_VERBS


# ============================================================================
# Synthetic-corpus fixture builders
# ============================================================================


def _calls_single(verb: str) -> list[dict]:
    """1 distinct shape under BOTH collapsed and strict readings."""
    return [{"name": verb, "params": {"x": 10}}]


def _calls_diverse(verb: str) -> list[dict]:
    """3 distinct shapes under BOTH readings (bool/str/NoneType -- none of
    which the `collapse` flag affects), i.e. NOT low under either reading."""
    return [
        {"name": verb, "params": {"x": True}},
        {"name": verb, "params": {"x": "hello"}},
        {"name": verb, "params": {"x": None}},
    ]


def _calls_asymmetric(verb: str) -> list[dict]:
    """2 distinct COLLAPSED shapes (int+float both -> "number"; LOW, <3) vs
    3 distinct STRICT shapes (int, float, str all distinct; NOT low, >=3) --
    the W2 asymmetry that can only ever run collapsed-passes/strict-fails,
    never the reverse (§6.4's algebra)."""
    return [
        {"name": verb, "params": {"x": 10}},
        {"name": verb, "params": {"x": 10.0}},
        {"name": verb, "params": {"x": "z"}},
    ]


def _rows_for_verb(verb: str, calls: list[dict], provenance: str) -> list[dict]:
    return [
        {
            "record_id": f"{verb}-{i}",
            "ambiguity_class": "clean_parse",
            "verb": verb,
            "calls": [call],
            "provenance": provenance,
            "split": "train",
            "lineage": {},
        }
        for i, call in enumerate(calls)
    ]


def _synthetic_rows(shape_by_verb: dict[str, str]) -> list[dict]:
    """Build a synthetic 10-LH-verb corpus. `shape_by_verb[verb]` selects
    'single' | 'diverse' | 'asymmetric'; provenance always follows T1_INVARIANT's
    zero/nonzero split, so every fixture built this way holds T1 by construction."""
    builders = {
        "single": _calls_single,
        "diverse": _calls_diverse,
        "asymmetric": _calls_asymmetric,
    }
    rows = []
    for verb, shape in shape_by_verb.items():
        calls = builders[shape](verb)
        provenance = "golden" if verb in T1_ZERO_VERBS else "naturalness"
        rows.extend(_rows_for_verb(verb, calls, provenance))
    return rows


def _write_corpus(tmp_path: Path, rows: list[dict]) -> tuple[Path, Path]:
    sidecar_path = tmp_path / "sidecar.jsonl"
    sidecar_path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")

    by_class = Counter(r["ambiguity_class"] for r in rows)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({"counts": {"by_class": dict(by_class)}}))

    return sidecar_path, manifest_path


def _gate_on_synthetic(tmp_path: Path, shape_by_verb: dict[str, str]) -> tuple[int, dict]:
    rows = _synthetic_rows(shape_by_verb)
    sidecar_path, manifest_path = _write_corpus(tmp_path, rows)
    out_dir = tmp_path / "out"
    code = gap.gate(sidecar_path=sidecar_path, manifest_path=manifest_path, out_dir=out_dir)
    report = json.loads((out_dir / "gap_report.json").read_text())
    return code, report


# ============================================================================
# --gate against LIVE data
# ============================================================================


class TestGateAgainstLiveData:
    def test_gate_writes_report_and_exits_a_decision_code(self, tmp_path):
        """--gate against live data exits one of 0/1/4/7 and writes gap_report.json."""
        out_dir = tmp_path / "out"
        code = gap.gate(out_dir=out_dir)
        assert code in (
            cli.EXIT_OK, cli.EXIT_MEASUREMENT_ERROR,
            cli.EXIT_STOP_COVERAGE, cli.EXIT_CONTESTED,
        )
        report_path = out_dir / "gap_report.json"
        assert report_path.exists()
        report = json.loads(report_path.read_text())
        assert report["gate"]["decision"] in ("PROCEED", "STOP", "CONTESTED")

    def test_gate_exits_5_when_cookbook_absent(self, tmp_path):
        """Exit 5, no report written, when the cookbook clone is absent (§7.5) --
        T3 reads recipes.yml, so no decision is available."""
        nonexistent = tmp_path / "no_such_clone" / "cookbook" / "recipes.yml"
        out_dir = tmp_path / "out"
        code = gap.gate(recipes_path=nonexistent, out_dir=out_dir)
        assert code == cli.EXIT_INCONCLUSIVE
        assert not (out_dir / "gap_report.json").exists()


# ============================================================================
# Manifest cross-check (C18) — recomputed per-class counts against the real,
# committed manifest.json
# ============================================================================


class TestManifestCrossCheck:
    def test_recomputed_per_class_counts_match_manifest(self):
        sidecar_rows = gap.load_sidecar_rows(gap.default_sidecar_path())
        manifest = gap.load_manifest(gap.default_manifest_path())
        recomputed = Counter(row["ambiguity_class"] for row in sidecar_rows)

        assert dict(recomputed) == manifest["counts"]["by_class"]
        # §6's own worked expectation, confirmed against the live manifest directly
        # rather than trusted blindly.
        assert dict(recomputed) == {
            "clean_parse": 137,
            "missing_slot": 13,
            "ambiguous_referent": 17,
            "out_of_surface": 21,
        }


# ============================================================================
# value_form / shape_key — direct unit tests (C1, C20)
# ============================================================================


class TestValueForm:
    def test_mix_call_no_exception_and_unmapped_increment(self):
        """`mix` is NOT a PARAM_NAMESPACE key at all (it's experimental) --
        value_form must not raise, and must count the miss (C1)."""
        stats = gap.GapStats()
        form = gap.value_form("mix", "duration_s", 5, stats)
        assert isinstance(form, str)
        assert stats.unmapped_params[("mix", "duration_s")] == 1

    def test_synthetic_param_absent_from_verbs_namespace_no_exception(self):
        """`aspirate` IS a PARAM_NAMESPACE key, but this param name is not one
        of its declared ParamSpecs -- still a total lookup, never raises."""
        stats = gap.GapStats()
        form = gap.value_form("aspirate", "totally_made_up_param", "whatever", stats)
        assert isinstance(form, str)
        assert stats.unmapped_params[("aspirate", "totally_made_up_param")] == 1

    def test_numeric_collapsing_10_0_and_20_same_form(self):
        """C20: 10.0 and 20 collapse to the SAME form under the default
        (collapsed) reading."""
        stats = gap.GapStats()
        form_float = gap.value_form("aspirate", "volume_ul", 10.0, stats)
        form_int = gap.value_form("aspirate", "volume_ul", 20, stats)
        assert form_float == "number"
        assert form_int == "number"
        assert form_float == form_int

    def test_bool_before_number_branch(self):
        """isinstance(True, int) is True in Python -- bool must win."""
        stats = gap.GapStats()
        assert gap.value_form("aspirate", "volume_ul", True, stats) == "bool"

    def test_strict_reading_does_not_collapse_numeric_types(self):
        """collapse=False reproduces revision-1's type(v).__name__ behaviour
        for numbers: int and float are DISTINCT under strict."""
        stats = gap.GapStats()
        strict_float = gap.value_form("aspirate", "volume_ul", 10.0, stats, collapse=False)
        strict_int = gap.value_form("aspirate", "volume_ul", 20, stats, collapse=False)
        assert strict_float == "float"
        assert strict_int == "int"
        assert strict_float != strict_int

    def test_slice_before_subscript(self):
        """plate["A1":"A6"] matches both the slice and subscript regexes --
        slice must be checked first."""
        stats = gap.GapStats()
        # aspirate.source is SYMBOLIC_RESOURCE_REF
        assert gap.value_form("aspirate", "source", 'plate["A1":"A6"]', stats) == "slice"
        assert gap.value_form("aspirate", "source", 'plate["A1"]', stats) == "subscript"


# ============================================================================
# T3 — out-of-surface anchor matching (C8), the two pinned cases
# ============================================================================


class TestT3AnchorMatching:
    def test_real_recipe_lh_summary_and_deck_get_all_children_is_an_anchor(self):
        """part1/01_robot_on_screen.qmd#summary: 'lh.summary, deck.get_all_children'
        -- both method-shaped, neither member in PHASE2_TOOL_NAMES -- IS an anchor."""
        cookbook = recipes.load_recipes()
        target = next(
            r for r in cookbook if r.path == "part1/01_robot_on_screen.qmd#summary"
        )
        assert target.apis_raw == "lh.summary, deck.get_all_children"
        assert recipes.in_surface_verbs(target) == frozenset()

    def test_synthetic_lh_drop_tips_is_not_an_anchor(self):
        """A synthetic recipe with apis: 'lh.drop_tips' -- drop_tips IS in
        PHASE2_TOOL_NAMES -- is NOT an anchor."""
        token = recipes.classify_api_token("lh.drop_tips")
        synthetic = recipes.Recipe(
            title="synthetic", path="synthetic.qmd#x", chapter=1, line_no=1,
            apis_raw="lh.drop_tips", api_tokens=(token,),
        )
        assert recipes.in_surface_verbs(synthetic) == frozenset({"drop_tips"})


# ============================================================================
# Determinism / regression pins
# ============================================================================


class TestDeterminismAndRegressionPins:
    def test_report_json_roundtrips_with_sort_keys(self):
        """Regression test for W6's TypeError: keys must be str -- a tuple-keyed
        unmapped_params would raise on the first real json.dumps(sort_keys=True)."""
        result = gap.run_gap()
        report = gap.build_report(result)
        text = json.dumps(report, sort_keys=True)
        assert json.loads(text) == report

    def test_unmatched_cell_keys_empty_on_real_corpus(self):
        """W9's regression pin: every one of the 188 committed rows maps into one
        of the 43 committed cells. A non-empty result here means the
        INVERSE_CLASS_MAP direction or verb-normalization is wrong -- investigate,
        don't accept whatever value is observed."""
        result = gap.run_gap()
        assert result.unmatched_cell_keys == {}


# ============================================================================
# Synthetic-corpus fixtures driving the gate to all FOUR outcomes
# ============================================================================


class TestGateOutcomes:
    def test_proceed(self, tmp_path):
        """All 10 LH verbs LOW-diversity under both readings (deficit found,
        >=5/10) + real cookbook's ample anchor supply (76 anchors / 18 chapters,
        both well over threshold) -> PROCEED (0)."""
        shape_by_verb = {v: "single" for v in LH_VERBS}
        code, report = _gate_on_synthetic(tmp_path, shape_by_verb)

        assert report["invariants"]["T1"]["holds"] is True
        assert report["metrics"]["T2_low_shape_lh_verbs_collapsed"] == 10
        assert report["metrics"]["T2_low_shape_lh_verbs_strict"] == 10
        assert report["gate"]["t2_normalization_sensitive"] is False
        assert report["gate"]["decision"] == "PROCEED"
        assert code == cli.EXIT_OK

    def test_stop(self, tmp_path):
        """All 10 LH verbs DIVERSE under both readings (no deficit, 0/10 low)
        -> T2_collapsed fails its >=5 floor -> STOP (4), regardless of T3."""
        shape_by_verb = {v: "diverse" for v in LH_VERBS}
        code, report = _gate_on_synthetic(tmp_path, shape_by_verb)

        assert report["invariants"]["T1"]["holds"] is True
        assert report["metrics"]["T2_low_shape_lh_verbs_collapsed"] == 0
        assert report["metrics"]["T2_low_shape_lh_verbs_strict"] == 0
        assert report["gate"]["t2_normalization_sensitive"] is False
        assert report["gate"]["decision"] == "STOP"
        assert code == cli.EXIT_STOP_COVERAGE

    def test_contested(self, tmp_path):
        """All 10 LH verbs ASYMMETRIC: T2_collapsed passes (10 >= 5, deficit
        found) while T2_strict fails (0 < 5, no deficit found) -- must exit
        exactly 7, not 4 and not 0 (W2)."""
        shape_by_verb = {v: "asymmetric" for v in LH_VERBS}
        code, report = _gate_on_synthetic(tmp_path, shape_by_verb)

        assert report["invariants"]["T1"]["holds"] is True
        assert report["metrics"]["T2_low_shape_lh_verbs_collapsed"] == 10
        assert report["metrics"]["T2_low_shape_lh_verbs_strict"] == 0
        assert report["gate"]["per_threshold"]["T2_collapsed"]["pass"] is True
        assert report["gate"]["per_threshold"]["T2_strict"]["pass"] is False
        assert report["gate"]["t2_normalization_sensitive"] is True
        assert report["gate"]["decision"] == "CONTESTED"
        assert code == cli.EXIT_CONTESTED
        assert code != cli.EXIT_STOP_COVERAGE
        assert code != cli.EXIT_OK

    def test_t1_invariant_violation(self, tmp_path):
        """Every LH verb given a naturalness row (breaking the classic 5-verb
        zero-naturalness pattern entirely: observed count 0, not 5) -> exit 1,
        NOT 0/4/7 -- a measurement-pipeline disagreement, not a decision."""
        rows = []
        for verb in LH_VERBS:
            calls = _calls_single(verb)
            rows.extend(_rows_for_verb(verb, calls, provenance="naturalness"))
        sidecar_path, manifest_path = _write_corpus(tmp_path, rows)
        out_dir = tmp_path / "out"

        code = gap.gate(sidecar_path=sidecar_path, manifest_path=manifest_path, out_dir=out_dir)

        assert code == cli.EXIT_MEASUREMENT_ERROR
        # The report IS still written -- Task 7's contract: "writes gap_report.json
        # in every case except a true measurement failure before any report can be
        # built", and a T1 disagreement happens AFTER the report content is built.
        report_path = out_dir / "gap_report.json"
        assert report_path.exists()
        report = json.loads(report_path.read_text())
        assert report["invariants"]["T1"]["holds"] is False
        assert report["invariants"]["T1"]["observed"] == 0
        assert report["invariants"]["T1"]["expected"] == 5
