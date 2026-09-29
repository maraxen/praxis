"""Extraction-correctness tests for the P2.4 corpus miner (AC-2.4 smoke gate).

Covers synthetic cells with known shapes first, then pins real-corpus
behavior (the 5 notebooks at PLR 1.0.0b1, incl. the modern-API prep demo that
must yield zero LiquidHandler calls, plus the protocols) so drift in the
vendored docs or protocol corpus is caught loudly.
"""

from __future__ import annotations

import json

from overlay_gen.miner import (
    HARDWARE_CONTEXT_ONLY_NOTEBOOKS,
    MinedCall,
    NOTEBOOK_ROOT,
    PROTOCOL_DIR,
    REPO_ROOT,
    _extract_from_code,
    iter_kept_calls,
    mine_notebooks,
    mine_protocols,
)


def kept_of(stats) -> dict[tuple, MinedCall]:
    """Index kept calls by (name, origin-suffix) for assertions."""
    return {(c.name, c.origin): c for c in stats.kept_calls}


# --- synthetic cells --------------------------------------------------------


def test_aspirate_volumes_and_ref():
    stats = _extract_from_code(
        "await lh.aspirate(plate['A1:C1'], vols=[100.0, 50.0, 200.0])", "s", "s#cell0"
    )
    assert not stats.exclusions and stats.unextractable == 0
    (call,) = stats.kept_calls
    assert call.name == "aspirate"
    assert call.receiver_type == "liquid_handler"
    assert call.params["source"] == "plate['A1:C1']"
    assert call.params["volume_ul"] == [100.0, 50.0, 200.0]


def test_expert_kwargs_dropped_but_recorded():
    code = (
        "await lh.pick_up_tips(tip_rack['A1'], use_channels=[1], offsets=[off])\n"
        "await lh.aspirate(plate['A1'], vols=[15], mix=[Mix(volume=50)], flow_rate=20)\n"
    )
    stats = _extract_from_code(code, "s", "s#cell0")
    calls = {c.name: c for c in stats.kept_calls}
    assert set(calls) == {"pick_up_tips", "aspirate"}
    assert calls["pick_up_tips"].params == {"at": ["tip_rack['A1']"]}  # list cardinality per table
    assert "use_channels" in calls["pick_up_tips"].dropped_kwargs
    assert "offsets" in calls["pick_up_tips"].dropped_kwargs
    assert "mix" in calls["aspirate"].dropped_kwargs
    assert "flow_rate" in calls["aspirate"].dropped_kwargs
    # namespace purity: no expert kwarg leaks into params
    assert set(calls["aspirate"].params) <= {"source", "volume_ul"}


def test_non_surface_verbs_counted_then_skipped():
    code = (
        "await lh.setup()\n"
        "await lh.return_tips()\n"
        "await lh.mix(plate['A1'], vols=[50])\n"
        "await lh.aspirate96(plate, volume=10)\n"
        "await lh.dispense(plate['B2'], vols=[30])\n"
    )
    stats = _extract_from_code(code, "s", "s#cell0")
    assert [c.name for c in stats.kept_calls] == ["dispense"]
    reasons = {e.verb: e.reason for e in stats.exclusions}
    assert set(reasons) == {"setup", "return_tips", "mix", "aspirate96"}
    assert "phantom" in reasons["mix"]


def test_discard_tips_bare_call_kept_with_empty_params():
    stats = _extract_from_code("await lh.discard_tips()", "s", "s#cell0")
    (call,) = stats.kept_calls
    assert call.params == {}
    assert call.name == "discard_tips"


def test_scalar_volume_wrapped_to_list_cardinality():
    stats = _extract_from_code("await lh.transfer(src['A1'], tgt['B1'], target_vols=25)", "s", "s#0")
    (call,) = stats.kept_calls
    assert call.name == "transfer"
    assert call.params["volume_ul"] == [25]
    assert call.params["source"] == "src['A1']"
    assert call.params["destination"] == ["tgt['B1']"]  # list cardinality per table


def test_computed_volume_falls_back_to_source_segment():
    stats = _extract_from_code(
        "await liquid_handler.aspirate(plate[dst_well], vols=[volume * 0.8])", "s", "s#0"
    )
    (call,) = stats.kept_calls
    assert call.params["source"] == "plate[dst_well]"
    assert call.params["volume_ul"] == ["volume * 0.8"]


def test_unknown_verb_ignored():
    stats = _extract_from_code("x = foo.bar()", "s", "s#0")
    assert stats.kept_calls == [] and stats.exclusions == []


def test_syntax_error_cell_counted_not_fatal():
    stats = _extract_from_code("await lh.aspirate(", "s", "s#0")
    assert stats.parse_errors == 1 and stats.kept_calls == []


# --- real corpus ------------------------------------------------------------


#: The LH user-guide notebooks that exist at the vendored PLR 1.0.0b1 pin
#: (786ac2c4e), mapped to the number of kept LiquidHandler calls each yields.
#: At the pre-1.0 pin this tree had 16 notebooks / 26 kept calls; the
#: hamilton-star + OT2 notebooks were removed or moved out of
#: ``00_liquid-handling`` and the plate-washer notebook was deleted. A change
#: here means the submodule pin (or the receiver gate) moved -- re-mine on purpose.
_LH_NB = "external/pylabrobot/docs/user_guide/00_liquid-handling/"
EXPECTED_NOTEBOOK_KEPT: dict[str, int] = {
    _LH_NB + "container_no_go_zones.ipynb": 1,
    _LH_NB + "hamilton-prep/prep_basic_demo.ipynb": 0,  # modern Prep device API only
    _LH_NB + "mixing.ipynb": 3,
    _LH_NB + "moving-channels-around.ipynb": 1,
    _LH_NB + "tutorial_tip_inventory_consolidation.ipynb": 2,
}
PREP_NB = _LH_NB + "hamilton-prep/prep_basic_demo.ipynb"


def test_notebook_set_and_kept_counts_pinned():
    reports = mine_notebooks(NOTEBOOK_ROOT)
    assert set(reports) == set(EXPECTED_NOTEBOOK_KEPT)  # loses/gains a notebook -> fails
    assert {src: len(s.kept_calls) for src, s in reports.items()} == EXPECTED_NOTEBOOK_KEPT
    assert all(s.parse_errors == 0 and s.unextractable == 0 for s in reports.values())


def test_prep_basic_demo_modern_api_calls_never_kept():
    """prep.pipettes.* / prep.head8.* share verb names with LiquidHandler but are
    the modern device API: excluded and recorded, never relabelled as LH calls."""
    stats = mine_notebooks(NOTEBOOK_ROOT)[PREP_NB]
    assert stats.kept_calls == []
    modern = [e for e in stats.exclusions if e.reason.startswith("receiver ")]
    by_verb = {}
    for e in modern:
        by_verb[e.verb] = by_verb.get(e.verb, 0) + 1
    # 10 modern pipetting calls + get_mounted_tips + setup/stop of Prep objects.
    assert by_verb == {
        "pick_up_tips": 3,
        "drop_tips": 3,
        "aspirate": 2,
        "dispense": 2,
        "get_mounted_tips": 1,
        "setup": 2,
        "stop": 2,
    }
    assert all("not a legacy LiquidHandler" in e.reason for e in modern)


def _cell_line(nb_rel: str, origin: str) -> str:
    """Source text of the call line an origin ``...#cell<N>@<line>`` points at
    (same magic-stripping as the miner), for an independent receiver check."""
    _, _, tail = origin.partition("#cell")
    cell_no, _, line_no = tail.partition("@")
    nb = json.loads((REPO_ROOT / nb_rel).read_text(encoding="utf-8"))
    code = "".join(nb["cells"][int(cell_no)]["source"])
    lines = [ln for ln in code.splitlines() if not ln.lstrip().startswith(("%", "!"))]
    return lines[int(line_no) - 1]


def test_every_kept_notebook_call_is_on_a_liquid_handler_receiver():
    reports = mine_notebooks(NOTEBOOK_ROOT)
    kept = [c for s in reports.values() for c in s.kept_calls]
    assert len(kept) == sum(EXPECTED_NOTEBOOK_KEPT.values()) == 7
    for call in kept:
        line = _cell_line(call.source, call.origin)
        assert f"lh.{call.name}(" in line, (call.origin, line)
        assert "prep" not in line


def test_hardware_context_only_notebooks_skipped_unparsed():
    reports = mine_notebooks(NOTEBOOK_ROOT)
    skipped = {
        src for src, stats in reports.items() if stats.skip_reason is not None
    }
    # Whatever hardware-context-only notebooks exist on disk at this pin are
    # skipped whole; none of them survive at PLR 1.0.0b1 (the dict is retained
    # for the pre-1.0 pin).
    on_disk = {
        (NOTEBOOK_ROOT / key).relative_to(REPO_ROOT).as_posix()
        for key in HARDWARE_CONTEXT_ONLY_NOTEBOOKS
        if (NOTEBOOK_ROOT / key).is_file()
    }
    assert skipped == on_disk


def test_all_notebooks_present():
    assert len(mine_notebooks(NOTEBOOK_ROOT)) == len(EXPECTED_NOTEBOOK_KEPT) == 5


# --- receiver gate (synthetic) ---------------------------------------------


def test_modern_device_api_receiver_excluded_not_kept():
    code = (
        "prep = Prep(deck=deck)\n"
        "await prep.pipettes.pick_up_tips(tip_spots, use_channels=[0, 1])\n"
        "await prep.pipettes.aspirate(source, piston_volumes=[35.0])\n"
        "await prep.head8.dispense(containers=dest, volume=15.0)\n"
    )
    stats = _extract_from_code(code, "s", "s#0")
    assert stats.kept_calls == []
    assert [e.verb for e in stats.exclusions] == ["pick_up_tips", "aspirate", "dispense"]
    assert all("not a legacy LiquidHandler" in e.reason for e in stats.exclusions)
    assert "prep.pipettes" in stats.exclusions[0].reason


def test_receiver_bound_to_liquid_handler_is_kept_whatever_its_name():
    code = (
        "handler = LiquidHandler(backend=b, deck=d)\n"
        "await handler.aspirate(plate['A1'], vols=[10])\n"
    )
    (call,) = _extract_from_code(code, "s", "s#0").kept_calls
    assert call.name == "aspirate" and call.receiver_type == "liquid_handler"


def test_annotated_liquid_handler_parameter_is_kept():
    code = (
        "async def proto(robot: LiquidHandler | None, other: Prep):\n"
        "    await robot.discard_tips()\n"
        "    await other.discard_tips()\n"
    )
    stats = _extract_from_code(code, "s", "s#0")
    assert [c.name for c in stats.kept_calls] == ["discard_tips"]
    assert len(stats.exclusions) == 1 and "'other'" in stats.exclusions[0].reason


def test_binding_overrides_conventional_name():
    """`lh = Prep(...)` is NOT a LiquidHandler just because it is called lh."""
    stats = _extract_from_code(
        "lh = Prep(deck=deck)\nawait lh.aspirate(plate['A1'], vols=[10])\n", "s", "s#0"
    )
    assert stats.kept_calls == []
    assert "bound to Prep" in stats.exclusions[0].reason


def test_unidentifiable_receiver_excluded_with_reason():
    stats = _extract_from_code("await mystery.aspirate(plate['A1'], vols=[10])", "s", "s#0")
    assert stats.kept_calls == []
    assert "not identifiable as a LiquidHandler" in stats.exclusions[0].reason


def test_binding_from_sibling_cell_is_honoured():
    bindings = {"rig": {"LiquidHandler"}}
    stats = _extract_from_code(
        "await rig.pick_up_tips(tip_rack['A1'])", "s", "s#0", bindings=bindings
    )
    assert [c.name for c in stats.kept_calls] == ["pick_up_tips"]


def test_simple_transfer_protocol_mined():
    reports = mine_protocols(PROTOCOL_DIR)
    rel = "praxis/protocol/protocols/simple_transfer.py"
    stats = reports[rel]
    names = sorted(c.name for c in stats.kept_calls)
    assert names.count("aspirate") == 1 and names.count("dispense") == 1
    assert "return_tips" not in names
    assert {e.verb for e in stats.exclusions} == {"return_tips"}
    call = next(c for c in stats.kept_calls if c.name == "aspirate")
    assert call.origin.startswith(rel + "::simple_transfer@")
    assert call.source == rel


def test_serial_dilution_commented_mix_not_mined():
    reports = mine_protocols(PROTOCOL_DIR)
    rel = "praxis/protocol/protocols/serial_dilution.py"
    verbs = {c.name for c in reports[rel].kept_calls}
    assert "mix" not in verbs  # commented out in source; ast never sees it
    assert verbs == {"pick_up_tips", "aspirate", "dispense"}


def test_protocol_corpus_complete():
    reports = mine_protocols(PROTOCOL_DIR)
    assert len(reports) == 6
    total = sum(len(s.kept_calls) for s in reports.values())
    assert total == 14  # unchanged by the PLR 1.0 bump (protocols use pylabrobot.legacy)


def test_iter_kept_calls_deterministic():
    reports = {**mine_notebooks(NOTEBOOK_ROOT), **mine_protocols(PROTOCOL_DIR)}
    a = [(c.source, c.origin) for c in iter_kept_calls(reports)]
    b = [(c.source, c.origin) for c in iter_kept_calls(reports)]
    assert a == b and len(a) > 10
    assert all(str(REPO_ROOT) not in c.source for c in iter_kept_calls(reports))
