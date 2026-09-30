"""Spec 260929 §18.8 (`260929_plr-sema-plr1-tip-effect-increment.md`), backlog #5622,
task T59: the drift tests that make the next PLR bump fail in CI rather than in a
precision number.

* **AC-18.7 -- the cross-pin baseline** (`fixtures/channel_effect_baseline.json`,
  generated FROM THE OLD-PIN ARTIFACT by `scripts/gen_channel_effect_baseline.py`).
  Absence is a value (r1, M11): a vanished key fails, a new key fails unless it is
  declared `old: "absent"`, and the divergence counter over the key union must equal
  `len(intended_divergences)`.
* **AC-18.8 -- structural invariants** (a)-(e) over the committed table, each with a
  synthetic counter-table that must fail it. (f) is NOT here: it is pin-scoped (r1, m8)
  and lives with AC-18.2's pin values (`effects_max_depth == 2`) in
  `test_tip_effects_plr1.py`.
* **AC-18.9 -- the behavioural oracle**, against the real PLR 1.0 `TipTracker`: drive
  its public methods and compare `has_tip` with the polarity the table derived. Not
  skippable: PLR is imported at module top, so an unimportable PLR fails collection.
* **§18.8(4) -- the synthetic derivation controls** are AC-18.2's fixtures in
  `test_tip_effects_plr1.py`; the last section here pins that every one of them is still
  present (a deleted control is the failure that would otherwise be silent).

Every check is a pure function (`*_violations`, `run_effect_oracle`, ...) so its
negative control can hand it a broken input, or a broken tracker, and watch it fire:
a check that can only pass is not an instrument (rules/BATHOS.md).

`PLR_SEMA_DRIFT_DATA_DIR` / `PLR_SEMA_DRIFT_SURVEY` point the table+ledger and the
survey somewhere else. They exist for `outputs/plr10_tools/t58/mutation_check.py`, which
regenerates the artifacts from a deliberately mutated derivation into a scratch
directory and re-runs this file against them; nothing else sets them.
"""

from __future__ import annotations

import ast
import copy
import importlib.metadata
import importlib.util
import inspect
import json
import os
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

# Import order is load-bearing (spec §18.8(3); re-verified 260929 in a fresh interpreter):
# `pylabrobot.legacy.tip_tracker` first dies with "cannot import name 'TipTracker' from
# partially initialized module ... (most likely due to a circular import)", so
# `pylabrobot.resources` must come first. isort must not reorder this block.
# isort: off
import pylabrobot.resources  # noqa: F401
from pylabrobot.legacy import tip_tracker as plr_tip_tracker
from pylabrobot.legacy.tip_tracker import TipTracker
from pylabrobot.resources.tip import Tip
from pylabrobot.resources.tip_rack import TipSpot

# isort: on
from plr_sema.derive import DroppedCall, SurveyRecord, _walk_closure, build_index, default_plr_pkg_root, load_survey
from plr_sema.derive.receiver_state import _BRIDGE_SHAPE_RE

PLR_SEMA_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PLR_SEMA_ROOT.parent
FIXTURE_PATH = PLR_SEMA_ROOT / "tests" / "fixtures" / "channel_effect_baseline.json"
GENERATOR_PATH = PLR_SEMA_ROOT / "scripts" / "gen_channel_effect_baseline.py"
SIBLING_TEST_PATH = PLR_SEMA_ROOT / "tests" / "test_tip_effects_plr1.py"
DATA_DIR = Path(os.environ.get("PLR_SEMA_DRIFT_DATA_DIR", PLR_SEMA_ROOT / "data"))
SURVEY_PATH = Path(
    os.environ.get("PLR_SEMA_DRIFT_SURVEY", REPO_ROOT / "training" / "verify" / "data" / "plr_preconditions.json")
)

ABSENT = "absent"
POLARITIES = {"HAS_TIP", "NO_TIP"}


# ---------------------------------------------------------------------------
# Data fixtures. The generator is loaded by path: `scripts/` is not a package.
# ---------------------------------------------------------------------------


def _load_generator():
    spec = importlib.util.spec_from_file_location("gen_channel_effect_baseline", GENERATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def gen():
    return _load_generator()


@pytest.fixture(scope="module")
def table() -> dict:
    return json.loads((DATA_DIR / "derived_contracts.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def ledger() -> dict:
    return json.loads((DATA_DIR / "gap_ledger.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def baseline() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def records() -> list[SurveyRecord]:
    return load_survey(SURVEY_PATH)


def _channel_effects(table: dict) -> dict[str, str]:
    """Every contract carrying a `channel_effect`. Deliberately written here rather than imported
    from the generator, so the two definitions of "carries one" can disagree and be caught."""
    return {k: v["channel_effect"] for k, v in table["contracts"].items() if v.get("channel_effect") is not None}


def _light(table: dict) -> dict:
    """A small stand-in for the table: the receiver state, the diagnostics and only the contracts that
    carry a `channel_effect`. The checks below read nothing else, and deep-copying 18 MB per negative
    control would be waste."""
    return {
        "receiver_state": copy.deepcopy(table["receiver_state"]),
        "receiver_state_diagnostics": copy.deepcopy(table["receiver_state_diagnostics"]),
        "contracts": {k: {"channel_effect": v} for k, v in _channel_effects(table).items()},
        "stamp": copy.deepcopy(table["stamp"]),
    }


# ---------------------------------------------------------------------------
# AC-18.7 -- the cross-pin baseline.
# ---------------------------------------------------------------------------


def drift_problems(fixture: dict, table: dict) -> tuple[list[str], int, int]:
    """`(problems, n_divergences, n_union)` of `table` against the baseline `fixture`, absence being a
    value (r1, M11). `problems` is empty iff the drift test passes."""
    base = fixture["channel_effects"]
    cur = _channel_effects(table)
    intended = fixture["intended_divergences"]
    problems: list[str] = []
    for key, old in base.items():  # Old keys.
        if key not in cur:
            problems.append(f"vanished key {key} (baseline {old})")
        elif key in intended:
            if cur[key] != intended[key]["new"]:
                problems.append(f"{key}: intended -> {intended[key]['new']}, but the table has {cur[key]}")
        elif cur[key] != old:
            problems.append(f"{key}: baseline {old}, table {cur[key]} (undeclared divergence)")
    for key, new in cur.items():  # New keys.
        if key in base:
            continue
        if key not in intended or intended[key]["old"] != ABSENT:
            problems.append(f"new key {key} = {new}, absent from the baseline and not declared `old: absent`")
        elif intended[key]["new"] != new:
            problems.append(f"{key}: declared new {intended[key]['new']}, but the table has {new}")
    for key, spec in intended.items():  # The fixture must be self-consistent.
        if spec["old"] != base.get(key, ABSENT):
            problems.append(f"intended {key}: old={spec['old']!r} but the baseline has {base.get(key, ABSENT)!r}")
    union = set(base) | set(cur)
    n_div = sum(1 for k in union if base.get(k, ABSENT) != cur.get(k, ABSENT))
    if n_div != len(intended):
        problems.append(f"baseline_divergences = {n_div}, but len(intended_divergences) = {len(intended)}")
    return problems, n_div, len(union)


def test_ac_18_7_files_exist_and_the_baseline_is_the_old_pin(baseline: dict, table: dict) -> None:
    assert GENERATOR_PATH.is_file() and FIXTURE_PATH.is_file()
    assert re.fullmatch(r"[0-9a-f]{40}", baseline["source_rev"]), baseline["source_rev"]
    assert baseline["plr_pin"]["hash"].startswith("dd79c4c89"), "the baseline must be the OLD pin's artifact"
    assert baseline["plr_pin"]["hash"] != table["stamp"]["plr"]["hash"], (
        "baseline and table are the same pin: the cross-pin test would be a tautology"
    )
    assert baseline["channel_effects"], "an empty baseline passes everything"
    assert set(baseline["intended_divergences"]) == {"LiquidHandler.load_state"}
    (spec,) = baseline["intended_divergences"].values()
    assert (spec["old"], spec["new"]) == ("HAS_TIP", "widen")
    assert spec["reason"] and spec["reason"] != "unreviewed", "a divergence needs a written reason"


def test_ac_18_7_current_table_matches_the_baseline_except_the_intended_divergence(baseline: dict, table: dict) -> None:
    problems, n_div, n_union = drift_problems(baseline, table)
    print(f"parity = {n_union - n_div}/{n_union}  (baseline_divergences = {n_div}, intended = {len(baseline['intended_divergences'])})")
    assert problems == []
    assert n_div == len(baseline["intended_divergences"]) == 1


def test_ac_18_7_the_two_definitions_of_carrying_a_channel_effect_agree(gen, table: dict) -> None:
    assert gen.extract_channel_effects(table) == _channel_effects(table)
    assert _channel_effects(table), "the table carries no channel_effect at all"


def test_ac_18_7_control_the_baseline_fed_back_as_the_current_table_fails(baseline: dict) -> None:
    """Control: the baseline is genuinely a different table. Feeding the drift test the baseline's OWN values as the
    'current' table has zero divergences, which contradicts the declared one, so it must fail on exactly that."""
    old_as_current = {"contracts": {k: {"channel_effect": v} for k, v in baseline["channel_effects"].items()}}
    problems, n_div, _ = drift_problems(baseline, old_as_current)
    assert n_div == 0 and any("LiquidHandler.load_state" in p for p in problems), problems
    assert any(p.startswith("baseline_divergences = 0") for p in problems), problems


def test_ac_18_7_negative_a_vanished_key_fails(baseline: dict, table: dict) -> None:
    broken = _light(table)
    del broken["contracts"]["LiquidHandler.drop_tips"]
    problems, _, _ = drift_problems(baseline, broken)
    assert any(p.startswith("vanished key LiquidHandler.drop_tips") for p in problems), problems


def test_ac_18_7_negative_a_flipped_drop_tips_fails(baseline: dict, table: dict) -> None:
    broken = _light(table)
    broken["contracts"]["LiquidHandler.drop_tips"]["channel_effect"] = "HAS_TIP"
    problems, _, _ = drift_problems(baseline, broken)
    assert any("LiquidHandler.drop_tips" in p and "undeclared" in p for p in problems), problems


def test_ac_18_7_negative_a_new_key_fails_unless_declared_absent(baseline: dict, table: dict) -> None:
    """(r1, M11) A contract that gains a `channel_effect` and is absent from the baseline fails, unless it is
    listed with `old: absent`, and then only with the declared `new`."""
    key = "LiquidHandler.aspirate"
    assert key not in baseline["channel_effects"], "pick a contract that is really absent from the baseline"
    grown = _light(table)
    grown["contracts"][key] = {"channel_effect": "NO_TIP"}
    problems, n_div, _ = drift_problems(baseline, grown)
    assert any(p.startswith(f"new key {key}") for p in problems), problems
    assert n_div == 2, "the counter must count the new key as a divergence (absence is a value)"

    declared = copy.deepcopy(baseline)
    declared["intended_divergences"][key] = {"old": ABSENT, "new": "NO_TIP", "reason": "synthetic"}
    assert drift_problems(declared, grown)[0] == [], "declaring it `old: absent` is the ONLY way through"

    wrong_new = copy.deepcopy(declared)
    wrong_new["intended_divergences"][key]["new"] = "HAS_TIP"
    assert drift_problems(wrong_new, grown)[0], "a declared `new` that the table does not carry fails"

    wrong_old = copy.deepcopy(declared)
    wrong_old["intended_divergences"][key]["old"] = "widen"
    assert drift_problems(wrong_old, grown)[0], "`old` must be `absent` for a key the baseline lacks"


def test_ac_18_7_negative_the_counter_catches_a_listed_non_divergence(baseline: dict, table: dict) -> None:
    """Listing a key that does not diverge satisfies every per-key rule, and only the counter
    (`baseline_divergences == len(intended_divergences)`) notices."""
    padded = copy.deepcopy(baseline)
    padded["intended_divergences"]["LiquidHandler.drop_tips"] = {"old": "NO_TIP", "new": "NO_TIP", "reason": "synthetic"}
    problems, n_div, _ = drift_problems(padded, table)
    assert n_div == 1 and len(padded["intended_divergences"]) == 2
    assert problems == ["baseline_divergences = 1, but len(intended_divergences) = 2"], problems


def _write(path: Path, contracts: dict[str, str | None], *, pin: str = "p") -> Path:
    payload = {
        "stamp": {"plr": {"hash": pin}, "pylabrobot_version": "x"},
        "contracts": {k: ({} if v is None else {"channel_effect": v}) for k, v in contracts.items()},
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_ac_18_7_the_generator_cli_refuses_what_it_must_refuse(gen, tmp_path: Path) -> None:
    old = _write(tmp_path / "old.json", {"A.x": "HAS_TIP", "A.y": "NO_TIP", "A.z": None}, pin="old")
    cur = _write(tmp_path / "cur.json", {"A.x": "widen", "A.y": "NO_TIP", "A.z": None}, pin="new")
    out = tmp_path / "baseline.json"
    common = ["--from", str(old), "--current", str(cur), "--out", str(out)]

    # An undeclared divergence is refused and writes nothing (T59's stop rule, built in).
    assert gen.main(common) == 1 and not out.exists()
    # A declaration that names the wrong `new`, or a key that does not diverge, is refused too.
    assert gen.main([*common, "--intended-divergences", "A.x=NO_TIP"]) == 1 and not out.exists()
    assert gen.main([*common, "--intended-divergences", "A.x=widen", "A.y=widen"]) == 1 and not out.exists()

    assert gen.main([*common, "--intended-divergences", "A.x=widen", "--divergence-reason", "A.x=because"]) == 0
    written = json.loads(out.read_text(encoding="utf-8"))
    assert written["channel_effects"] == {"A.x": "HAS_TIP", "A.y": "NO_TIP"}
    assert written["intended_divergences"] == {"A.x": {"old": "HAS_TIP", "new": "widen", "reason": "because"}}
    assert written["plr_pin"]["hash"] == "old"
    before = out.read_text(encoding="utf-8")

    # Overwriting is a --rebase, and --rebase without an explicit --intended-divergences exits non-zero.
    assert gen.main(common) == 2, "an existing fixture is not silently overwritten"
    assert gen.main([*common, "--rebase"]) == 2, "--rebase must refuse without --intended-divergences"
    assert out.read_text(encoding="utf-8") == before

    # Rebasing onto the current table: baseline == current, so the only honest declaration is the empty one.
    rebase = ["--from", str(cur), "--current", str(cur), "--out", str(out), "--rebase"]
    assert gen.main([*rebase, "--intended-divergences", "A.x=widen"]) == 1, "a stale declaration is refused"
    assert out.read_text(encoding="utf-8") == before
    assert gen.main([*rebase, "--intended-divergences"]) == 0, "an explicit empty list declares none"
    rebased = json.loads(out.read_text(encoding="utf-8"))
    assert rebased["channel_effects"] == {"A.x": "widen", "A.y": "NO_TIP"} and rebased["intended_divergences"] == {}

    # A new key in the current table is a divergence with `old: absent`, and must be declared as such.
    grown = _write(tmp_path / "grown.json", {"A.x": "HAS_TIP", "A.y": "NO_TIP", "A.n": "NO_TIP"}, pin="new")
    fresh = tmp_path / "fresh.json"
    args = ["--from", str(old), "--current", str(grown), "--out", str(fresh)]
    assert gen.main(args) == 1
    assert gen.main([*args, "--intended-divergences", "A.n=NO_TIP"]) == 0
    assert json.loads(fresh.read_text(encoding="utf-8"))["intended_divergences"]["A.n"]["old"] == ABSENT


# ---------------------------------------------------------------------------
# AC-18.8 -- structural invariants (a)-(e), each with a counter-table.
# ---------------------------------------------------------------------------


def bridged_methods(records: list[SurveyRecord], receiver_state: dict) -> dict[str, set[str]]:
    """`{receiver: {tracker method it bridges}}`. A bridge of a contract entry is a `dropped_calls` entry,
    anywhere in that entry's `delegates_to` closure, matching `self.<channel_attr>[<name>].<m>` for the
    receiver's own `channel_attr` (§18.4.4, r1 m8)."""
    index = build_index(records)
    out: dict[str, set[str]] = {}
    for receiver, rs in receiver_state.items():
        found: set[str] = set()
        for rec in records:
            if rec.class_name != receiver:
                continue
            for visited, _key, _depth in _walk_closure((rec.module, rec.qualname), index):
                if visited is None:
                    continue
                for dropped in visited.dropped_calls:
                    match = _BRIDGE_SHAPE_RE.match(dropped.expr)
                    if match is not None and match.group(1) == rs["channel_attr"]:
                        found.add(match.group(3))
        out[receiver] = found
    return out


def _has_both_polarities(rs: dict) -> bool:
    return POLARITIES <= set(rs["effects"].values())


def invariant_a(table: dict, bridged: dict[str, set[str]]) -> list[str]:
    """`effects` has a HAS_TIP and a NO_TIP whenever some contract entry on the receiver has a bridge."""
    return [
        f"{r}: bridged {sorted(bridged.get(r, ()))} but effects={rs['effects']}"
        for r, rs in table["receiver_state"].items()
        if bridged.get(r) and not _has_both_polarities(rs)
    ]


def invariant_b(table: dict) -> list[str]:
    """`entry_reset` present => both polarities are published (L7's atomicity)."""
    return [
        f"{r}: entry_reset={rs['entry_reset']} but effects={rs['effects']}"
        for r, rs in table["receiver_state"].items()
        if "entry_reset" in rs and not _has_both_polarities(rs)
    ]


def invariant_c(ledger: dict) -> list[str]:
    """The gap ledger's `tip_state` families `tip_loading`/`tip_dropping`/`tip_requiring` are non-empty for
    `LiquidHandler`."""
    block = ledger.get("tip_state", {}).get("LiquidHandler")
    if block is None:
        return ["no tip_state block for LiquidHandler"]
    return [f"LiquidHandler.{fam} is empty" for fam in ("tip_loading", "tip_dropping", "tip_requiring") if not block.get(fam)]


def _is_int(x: Any) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def invariant_d(table: dict) -> list[str]:
    """The §18.4.8 keys are present with the declared types (and `entry_reset`'s shape when present)."""
    out: list[str] = []
    if not table["receiver_state"]:
        out.append("no receivers")
    for r, rs in table["receiver_state"].items():
        for key in ("effects", "effects_unresolved", "effect_backing_fields", "effects_max_depth"):
            if key not in rs:
                out.append(f"{r}: missing {key}")
        eff = rs.get("effects")
        if not isinstance(eff, dict) or not set(eff.values()) <= POLARITIES or not all(isinstance(k, str) for k in eff):
            out.append(f"{r}: effects is not an object<str, HAS_TIP|NO_TIP>")
        for key in ("effects_unresolved", "effect_backing_fields"):
            v = rs.get(key)
            if key in rs and not (isinstance(v, list) and all(isinstance(x, str) for x in v) and v == sorted(v)):
                out.append(f"{r}: {key} is not a sorted array<str>")
        if "effects_max_depth" in rs and not (_is_int(rs["effects_max_depth"]) and rs["effects_max_depth"] >= 0):
            out.append(f"{r}: effects_max_depth is not an int >= 0")
        er = rs.get("entry_reset")
        if "entry_reset" in rs and not (
            isinstance(er, dict) and isinstance(er.get("method"), str) and er.get("post") in ("no_tip", "has_tip")
        ):
            out.append(f"{r}: entry_reset is malformed")
    diag = table.get("receiver_state_diagnostics")
    if not isinstance(diag, dict) or not _is_int(diag.get("n_contracts_depth0_and_deep_coexist")):
        out.append("receiver_state_diagnostics.n_contracts_depth0_and_deep_coexist is missing or not an int")
    return out


def invariant_e(bridged: dict[str, set[str]]) -> list[str]:
    """No method bridged from any receiver begins with `_`."""
    return [f"{r} bridges private {m}" for r, ms in sorted(bridged.items()) for m in sorted(ms) if m.startswith("_")]


@pytest.fixture(scope="module")
def bridged(table: dict, records: list[SurveyRecord]) -> dict[str, set[str]]:
    return bridged_methods(records, table["receiver_state"])


def test_ac_18_8_the_invariants_are_not_vacuous_on_the_real_table(table: dict, bridged: dict[str, set[str]]) -> None:
    """(a) fires only where a bridge exists and (b) only where an entry_reset does; if neither exists the
    invariants pass for the wrong reason."""
    assert bridged["LiquidHandler"], "the survey shows no bridge from LiquidHandler: (a) is vacuous"
    assert any("entry_reset" in rs for rs in table["receiver_state"].values()), "(b) is vacuous"


def test_ac_18_8_a_effects_carry_both_polarities_when_bridged(table: dict, bridged: dict[str, set[str]]) -> None:
    assert invariant_a(table, bridged) == []


def test_ac_18_8_b_entry_reset_implies_both_polarities(table: dict) -> None:
    assert invariant_b(table) == []


def test_ac_18_8_c_the_tip_state_families_are_non_empty(ledger: dict) -> None:
    assert invariant_c(ledger) == []


def test_ac_18_8_d_the_new_keys_have_the_declared_types(table: dict) -> None:
    assert invariant_d(table) == []


def test_ac_18_8_e_no_bridged_method_is_private(bridged: dict[str, set[str]]) -> None:
    assert invariant_e(bridged) == []


def test_ac_18_8_a_counter_table_a_missing_polarity_fails(table: dict, bridged: dict[str, set[str]]) -> None:
    for drop in ("HAS_TIP", "NO_TIP"):
        broken = _light(table)
        broken["receiver_state"]["LiquidHandler"]["effects"] = {
            m: v for m, v in broken["receiver_state"]["LiquidHandler"]["effects"].items() if v != drop
        }
        assert invariant_a(broken, bridged), f"effects without {drop} must fail (a)"
    empty = _light(table)
    empty["receiver_state"]["LiquidHandler"]["effects"] = {}
    assert invariant_a(empty, bridged)
    # Control: (a) is conditional on a bridge, so it must NOT fire for a receiver that bridges nothing.
    assert invariant_a(empty, {"LiquidHandler": set()}) == []


def test_ac_18_8_b_counter_table_entry_reset_without_effects_fails(table: dict) -> None:
    broken = _light(table)
    rs = broken["receiver_state"]["LiquidHandler"]
    assert "entry_reset" in rs
    rs["effects"] = {m: v for m, v in rs["effects"].items() if v == "NO_TIP"}  # the L7 hazard: reset, no add_tip
    assert invariant_b(broken)
    del rs["entry_reset"]
    assert invariant_b(broken) == [], "control: without entry_reset the same effects pass (b)"


@pytest.mark.parametrize("family", ["tip_loading", "tip_dropping", "tip_requiring"])
def test_ac_18_8_c_counter_table_an_empty_family_fails(ledger: dict, family: str) -> None:
    broken = copy.deepcopy(ledger)
    broken["tip_state"]["LiquidHandler"][family] = []
    assert invariant_c(broken) == [f"LiquidHandler.{family} is empty"]
    del broken["tip_state"]["LiquidHandler"]
    assert invariant_c(broken) == ["no tip_state block for LiquidHandler"]


def test_ac_18_8_d_counter_table_wrong_or_missing_keys_fail(table: dict) -> None:
    def broken_with(edit: Callable[[dict], None]) -> list[str]:
        t = _light(table)
        edit(t)
        return invariant_d(t)

    lh = lambda t: t["receiver_state"]["LiquidHandler"]  # noqa: E731
    for key in ("effects", "effects_unresolved", "effect_backing_fields", "effects_max_depth"):
        assert broken_with(lambda t, key=key: lh(t).pop(key)), f"a missing {key} must fail (d)"
    assert broken_with(lambda t: lh(t).update(effects_max_depth=True)), "a bool is not an int"
    assert broken_with(lambda t: lh(t).update(effects_max_depth=-1))
    assert broken_with(lambda t: lh(t).update(effects_max_depth="2"))
    assert broken_with(lambda t: lh(t).update(effects_unresolved="load_state")), "a string is not an array"
    assert broken_with(lambda t: lh(t).update(effects_unresolved=["z", "a"])), "unsorted"
    assert broken_with(lambda t: lh(t).update(effect_backing_fields=[1]))
    assert broken_with(lambda t: lh(t).update(effects={"add_tip": "COPY"}))
    assert broken_with(lambda t: lh(t).update(entry_reset={"method": "setup", "post": "sideways"}))
    assert broken_with(lambda t: t.pop("receiver_state_diagnostics"))
    assert broken_with(lambda t: t["receiver_state_diagnostics"].update(n_contracts_depth0_and_deep_coexist="0"))
    assert broken_with(lambda t: t.update(receiver_state={})), "no receivers at all is not a pass"
    assert broken_with(lambda t: None) == [], "control: the unmodified light table passes (d)"


def test_ac_18_8_e_counter_table_a_private_bridge_fails() -> None:
    assert invariant_e({"LiquidHandler": {"add_tip", "_put"}}) == ["LiquidHandler bridges private _put"]
    assert invariant_e({"LiquidHandler": {"add_tip", "clear"}}) == []


def _rec(qualname: str, dropped: list[str], delegates: tuple[str, ...] = ()) -> SurveyRecord:
    return SurveyRecord(
        qualname=qualname, class_name=qualname.split(".")[0], module="synthetic", file="<synthetic>", lineno=1,
        params=(), findings=(), delegates_to=delegates, unresolved_calls=(),
        dropped_calls=tuple(DroppedCall(expr=e, lineno=1, scope_trail=()) for e in dropped),
    )


def test_ac_18_8_the_bridge_scan_finds_bridges_and_only_bridges() -> None:
    """The instrument behind (a) and (e): it must see a depth-1 bridge through a delegate, and must not count
    a call through a DIFFERENT channel attribute or a call that is not `self.<attr>[..].<m>`-shaped."""
    receiver_state = {"R": {"channel_attr": "head"}}
    seen = bridged_methods(
        [
            _rec("R.op", ["self.head[c].add_tip", "self.head96.pick_up", "self.head[c].sub.x", "head[c].nope"], ("helper",)),
            _rec("R.helper", ["self.head[c]._put"]),
            _rec("Other.op", ["self.head[c].clear"]),
        ],
        receiver_state,
    )
    assert seen == {"R": {"add_tip", "_put"}}, "depth-1 bridge found; other attr, other shapes and other classes ignored"
    assert invariant_e(seen), "and a private one found through a delegate fails (e)"


# ---------------------------------------------------------------------------
# AC-18.9 -- the behavioural oracle, against real PLR 1.0.
# ---------------------------------------------------------------------------


def _tip(name: str = "oracle-tip") -> Tip:
    return Tip(name=name, diameter=5.0, size_z=50.0, has_filter=False, maximal_volume=1000.0, fitting_depth=8.0)


@dataclass
class Rig:
    """A tracker, plus the strong reference to its holder: `TipTracker` keeps its `TipSpot` only through a
    `weakref`, so a dropped spot silently turns a holder-full tracker into a holder-less one."""

    tracker: TipTracker
    holder: TipSpot | None


def new_rig(cls: type[TipTracker], *, holder_full: bool, has_tip: bool = False) -> Rig:
    holder = TipSpot("oracle-spot", size_x=9.0, size_y=9.0, make_tip=_tip) if holder_full else None
    tracker = cls(thing="oracle", holder=holder)
    assert (tracker._holder is holder) and ((tracker._holder is not None) == holder_full), "wrong tracker path"
    if has_tip:
        tracker.add_tip(_tip("pre-state"), commit=True)
    return Rig(tracker, holder)


def _auto_kwargs(cls: type[TipTracker], method: str) -> dict[str, Any]:
    """A real `Tip` for every `Tip`-typed parameter and the default for everything else. A required parameter
    of any other kind FAILS rather than guesses: a new published effect must be given a driver on purpose."""
    kwargs: dict[str, Any] = {}
    for p in list(inspect.signature(getattr(cls, method)).parameters.values())[1:]:
        if p.annotation is Tip:
            kwargs[p.name] = _tip(f"arg-{method}")
        elif p.default is inspect.Parameter.empty:
            raise AssertionError(f"oracle cannot build `{p.name}` for {method}(); extend the driver deliberately")
    return kwargs


#: Witness calls for methods whose arguments are data, not a `Tip`: `(label, kwargs-factory, has_tip after)`.
#: `load_state` is L1's case, "unresolved" because the outcome depends on the data: no tip in, no tip out.
def _serialized_tip_state() -> dict:
    tip = _tip("loaded")
    return {"tip": tip.serialize(), "pending_tip": tip.serialize()}


UNRESOLVED_WITNESSES: dict[str, list[tuple[str, Callable[[], dict], bool]]] = {
    "load_state": [
        ("no tip", lambda: {"state": {"tip": None, "pending_tip": None}}, False),
        ("a serialized tip", lambda: {"state": _serialized_tip_state()}, True),
    ],
}


def run_effect_oracle(cls: type[TipTracker], effects: dict[str, str], *, holder_full: bool) -> list[str]:
    """Drive each `m` in `effects` from the pre-state its own guard admits (`NO_TIP` for a `HAS_TIP` effect, `HAS_TIP`
    for a `NO_TIP` effect), then commit, and return every disagreement between `has_tip` and the derived polarity,
    both after the call and after the commit. `[]` means the oracle agrees. A method with witness calls
    (`UNRESOLVED_WITNESSES`) is driven once per witness: a published polarity must hold for ALL of them."""
    bad: list[str] = []
    for method, polarity in sorted(effects.items()):
        expected = polarity == "HAS_TIP"
        witnesses = UNRESOLVED_WITNESSES.get(method)
        calls = (
            [(label, make_kwargs) for label, make_kwargs, _outcome in witnesses]
            if witnesses
            else [("", lambda method=method: _auto_kwargs(cls, method))]
        )
        for label, make_kwargs in calls:
            rig = new_rig(cls, holder_full=holder_full, has_tip=not expected)
            try:
                getattr(rig.tracker, method)(**make_kwargs())
                after_call = rig.tracker.has_tip
                rig.tracker.commit()
                after_commit = rig.tracker.has_tip
            except Exception as exc:  # noqa: BLE001 -- any raise is a disagreement, reported, not swallowed
                bad.append(f"{method}[{label}] raised {type(exc).__name__}: {exc}")
                continue
            if (after_call, after_commit) != (expected, expected):
                bad.append(f"{method}[{label}]: derived {polarity}, has_tip after call/commit = {after_call}/{after_commit}")
    return bad


def exhibited_outcomes(cls: type[TipTracker], method: str, witnesses: list[tuple[str, Callable[[], dict], bool]], *, holder_full: bool, has_tip: bool) -> set[bool]:
    """The set of `has_tip` values `method` leaves behind across `witnesses`, from one pre-state."""
    out: set[bool] = set()
    for _label, make_kwargs, _expected in witnesses:
        rig = new_rig(cls, holder_full=holder_full, has_tip=has_tip)
        getattr(rig.tracker, method)(**make_kwargs())
        out.add(rig.tracker.has_tip)
    return out


def rollback_witness(cls: type[TipTracker], *, holder_full: bool) -> tuple[bool, bool]:
    """`(has_tip mid-transaction, has_tip after rollback)` for an uncommitted `add_tip` on a `NO_TIP` tracker."""
    rig = new_rig(cls, holder_full=holder_full)
    rig.tracker.add_tip(_tip("uncommitted"), commit=False)
    mid = rig.tracker.has_tip
    rig.tracker.rollback()
    return mid, rig.tracker.has_tip


def fresh_has_tip(cls: type[TipTracker], *, holder_full: bool) -> bool:
    return new_rig(cls, holder_full=holder_full).tracker.has_tip


class _NoopHoldTracker(TipTracker):
    """Broken on purpose: nothing it 'holds' is ever held, so `add_tip`/`remove_tip` never change `has_tip`."""

    def _hold(self, tip):  # noqa: ANN001
        return None


class _NoopRollbackTracker(TipTracker):
    def rollback(self) -> None:
        return None


class _PreloadedTracker(TipTracker):
    def __init__(self, thing, holder=None):  # noqa: ANN001
        super().__init__(thing, holder)
        self.add_tip(_tip("smuggled"), commit=True)


def _flipped(effects: dict[str, str]) -> dict[str, str]:
    return {m: ("NO_TIP" if v == "HAS_TIP" else "HAS_TIP") for m, v in effects.items()}


@pytest.fixture(scope="module")
def lh_state(table: dict) -> dict:
    return table["receiver_state"]["LiquidHandler"]


def test_ac_18_9_the_oracle_runs_against_the_pin_the_table_was_derived_from(table: dict) -> None:
    assert Path(plr_tip_tracker.__file__).resolve() == (default_plr_pkg_root() / "legacy" / "tip_tracker.py").resolve()
    assert importlib.metadata.version("pylabrobot") == table["stamp"]["pylabrobot_version"]
    assert TipTracker.__module__ == "pylabrobot.legacy.tip_tracker"


def test_ac_18_9_the_oracle_is_not_skippable() -> None:
    """PLR is imported at module top: an unimportable PLR fails collection instead of skipping the file. This
    scans THIS file's AST (attribute/name nodes, so the words in strings do not count) for a skip escape hatch."""
    assert _skip_escapes(Path(__file__).read_text(encoding="utf-8")) == []
    assert _skip_escapes("import pytest\npytest.importorskip('pylabrobot')\n") == ["importorskip"]
    assert _skip_escapes("import pytest\n@pytest.mark.skipif(True, reason='x')\ndef test_x(): pass\n") == ["skipif"]
    assert _skip_escapes("try:\n    import pylabrobot\nexcept ImportError:\n    pylabrobot = None\n") == ["ImportError-guard"]


def _skip_escapes(source: str) -> list[str]:
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Attribute) and node.attr in {"skip", "skipif", "importorskip", "xfail"}:
            found.append(node.attr)
        elif isinstance(node, ast.Name) and node.id in {"skip", "skipif", "importorskip", "xfail"}:
            found.append(node.id)
        elif isinstance(node, ast.ExceptHandler) and isinstance(node.type, ast.Name) and node.type.id in {"ImportError", "ModuleNotFoundError"}:
            found.append("ImportError-guard")
    return found


@pytest.mark.parametrize("holder_full", [False, True], ids=["holder-less", "holder-full"])
def test_ac_18_9_every_effects_polarity_matches_has_tip(lh_state: dict, holder_full: bool) -> None:
    """Holder-less is §18.8(3)'s main check; holder-full is r1 m11's, which closes OI-5's polarity half."""
    assert lh_state["effects"], "no published effects: the oracle would agree with an empty table"
    assert run_effect_oracle(TipTracker, lh_state["effects"], holder_full=holder_full) == []


def test_ac_18_9_receivers_that_share_a_tracker_are_all_checked(table: dict) -> None:
    """Every receiver's `effects` is checked, not just `LiquidHandler`'s."""
    for name, rs in table["receiver_state"].items():
        assert run_effect_oracle(TipTracker, rs["effects"], holder_full=False) == [], name


@pytest.mark.parametrize("holder_full", [False, True], ids=["holder-less", "holder-full"])
def test_ac_18_9_negative_the_oracle_fires_on_a_wrong_polarity(lh_state: dict, holder_full: bool) -> None:
    flipped = _flipped(lh_state["effects"])
    bad = run_effect_oracle(TipTracker, flipped, holder_full=holder_full)
    assert {b.split("[")[0] for b in bad} >= set(flipped), "every flipped method must be caught"


@pytest.mark.parametrize("holder_full", [False, True], ids=["holder-less", "holder-full"])
def test_ac_18_9_negative_the_oracle_fires_on_a_tracker_that_does_not_behave(lh_state: dict, holder_full: bool) -> None:
    """The table is right and the TRACKER is wrong (a PLR change): the oracle must notice."""
    bad = run_effect_oracle(_NoopHoldTracker, lh_state["effects"], holder_full=holder_full)
    assert any(b.startswith("add_tip") for b in bad) and any(b.startswith("remove_tip") for b in bad), bad


def test_ac_18_9_unresolved_methods_exhibit_both_outcomes(lh_state: dict) -> None:
    """L1's witness that `effects_unresolved` is genuinely state-dependent: every unresolved method has a
    witness, and the witness shows `has_tip` both False and True, from either pre-state."""
    assert lh_state["effects_unresolved"], "nothing is unresolved: L1's witness has nothing to witness"
    for method in lh_state["effects_unresolved"]:
        assert method in UNRESOLVED_WITNESSES, f"{method} is unresolved and has no witness; add one deliberately"
        for holder_full in (False, True):
            for has_tip in (False, True):
                outcomes = exhibited_outcomes(
                    TipTracker, method, UNRESOLVED_WITNESSES[method], holder_full=holder_full, has_tip=has_tip
                )
                assert outcomes == {False, True}, (method, holder_full, has_tip, outcomes)


def test_ac_18_9_a_method_with_both_outcomes_is_never_published_as_resolved(lh_state: dict) -> None:
    """The converse direction, which is what a derivation that wrongly RESOLVES `load_state` breaks."""
    for method, witnesses in UNRESOLVED_WITNESSES.items():
        outcomes = exhibited_outcomes(TipTracker, method, witnesses, holder_full=False, has_tip=False)
        if outcomes == {False, True}:
            assert method in lh_state["effects_unresolved"] and method not in lh_state["effects"], method


def test_ac_18_9_negative_a_resolved_method_does_not_exhibit_both_outcomes() -> None:
    """Control for the two tests above: the witness discriminates. `clear` is genuinely resolved, and a
    witness list for it exhibits ONE outcome."""
    assert exhibited_outcomes(TipTracker, "clear", [("no args", lambda: {}, False)], holder_full=False, has_tip=True) == {False}
    assert exhibited_outcomes(TipTracker, "clear", [("no args", lambda: {}, False)], holder_full=True, has_tip=True) == {False}


@pytest.mark.parametrize("holder_full", [False, True], ids=["holder-less", "holder-full"])
def test_ac_18_9_a_fresh_tracker_has_no_tip(holder_full: bool) -> None:
    """R-C's `NO_TIP` constructor state."""
    assert fresh_has_tip(TipTracker, holder_full=holder_full) is False
    assert fresh_has_tip(_PreloadedTracker, holder_full=holder_full) is True, "negative control: the check can fail"


@pytest.mark.parametrize("holder_full", [False, True], ids=["holder-less", "holder-full"])
def test_ac_18_9_rollback_after_an_uncommitted_add_tip_leaves_no_tip(holder_full: bool) -> None:
    """(r1, m11) Bounds OI-6: `rollback` DOES change `has_tip` mid-transaction (True before it, False after), so
    COPY's identity reading holds only at operation boundaries."""
    assert rollback_witness(TipTracker, holder_full=holder_full) == (True, False)
    assert rollback_witness(_NoopRollbackTracker, holder_full=holder_full) == (True, True), "negative control"


# ---------------------------------------------------------------------------
# §18.8(4) -- the synthetic derivation controls are AC-18.2's, in test_tip_effects_plr1.py.
# ---------------------------------------------------------------------------

#: AC-18.2's lettered fixtures (a)-(u); the spec lists no others.
AC_18_2_LETTERS = "abcdefghijklmnopqrstu"


def ac_18_2_letters_present(source: str) -> set[str]:
    return {
        m.group(1)
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.FunctionDef)
        for m in [re.match(r"test_ac_18_2_([a-z])_", node.name)]
        if m
    }


def test_synthetic_derivation_controls_are_all_still_present() -> None:
    present = ac_18_2_letters_present(SIBLING_TEST_PATH.read_text(encoding="utf-8"))
    assert set(AC_18_2_LETTERS) - present == set(), "an AC-18.2 synthetic control was deleted"
    # Negative control: the scan reports a missing letter.
    stub = "def test_ac_18_2_a_x(): pass\ndef test_ac_18_2_c_y(): pass\ndef test_unrelated(): pass\n"
    assert ac_18_2_letters_present(stub) == {"a", "c"}
    assert set(AC_18_2_LETTERS) - ac_18_2_letters_present(stub) >= {"b", "u"}
