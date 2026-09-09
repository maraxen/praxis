"""Extraction-correctness tests for the P2.4 corpus miner (AC-2.4 smoke gate).

Covers synthetic cells with known shapes first, then pins real-corpus
behavior (hamilton-star/basic.ipynb, OT2 notebooks, protocols) so drift in
the vendored docs or protocol corpus is caught loudly.
"""

from __future__ import annotations

import json

import pytest

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


def test_hamilton_basic_notebook_mined():
    rel = "external/pylabrobot/docs/user_guide/00_liquid-handling/hamilton-star/basic.ipynb"
    reports = mine_notebooks(NOTEBOOK_ROOT)
    stats = reports[rel]
    names = sorted(c.name for c in stats.kept_calls)
    assert names == [
        "aspirate",
        "aspirate",
        "dispense",
        "dispense",
        "drop_tips",
        "pick_up_tips",
    ]
    asp = next(c for c in stats.kept_calls if c.name == "aspirate")
    assert asp.params["volume_ul"] == [100.0, 50.0, 200.0]


def test_ot2_simulator_use_channels_dropped():
    rel = "external/pylabrobot/docs/user_guide/00_liquid-handling/opentrons/ot2/ot2-simulator.ipynb"
    reports = mine_notebooks(NOTEBOOK_ROOT)
    stats = reports[rel]
    picks = [c for c in stats.kept_calls if c.name == "pick_up_tips"]
    assert len(picks) == 2
    assert any(c.dropped_kwargs == ("use_channels",) for c in picks)
    assert all("use_channels" not in c.params for c in stats.kept_calls)


def test_hello_world_discard_and_exclusions():
    rel = "external/pylabrobot/docs/user_guide/00_liquid-handling/opentrons/ot2/hello-world.ipynb"
    reports = mine_notebooks(NOTEBOOK_ROOT)
    names = [c.name for c in reports[rel].kept_calls]
    assert "discard_tips" in names
    excl = {e.verb for e in reports[rel].exclusions}
    assert "return_tips" in excl


def test_hardware_context_only_notebooks_skipped_unparsed():
    reports = mine_notebooks(NOTEBOOK_ROOT)
    assert len(reports) == 16  # every notebook accounted for
    skipped = {
        src: stats.skip_reason
        for src, stats in reports.items()
        if stats.skip_reason is not None
    }
    assert len(skipped) == len(HARDWARE_CONTEXT_ONLY_NOTEBOOKS)
    probing = [
        src for src in skipped if "z-probing" in src or "core-grippers" in src
    ]
    assert len(probing) >= 2


@pytest.mark.parametrize("notebook_count", [16])
def test_all_notebooks_present(notebook_count):
    nb = json.loads((NOTEBOOK_ROOT / "hamilton-star" / "basic.ipynb").read_text())
    assert any(c["cell_type"] == "code" for c in nb["cells"])
    assert len(mine_notebooks(NOTEBOOK_ROOT)) == notebook_count


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
    assert total > 0


def test_iter_kept_calls_deterministic():
    reports = {**mine_notebooks(NOTEBOOK_ROOT), **mine_protocols(PROTOCOL_DIR)}
    a = [(c.source, c.origin) for c in iter_kept_calls(reports)]
    b = [(c.source, c.origin) for c in iter_kept_calls(reports)]
    assert a == b and len(a) > 10
    assert all(str(REPO_ROOT) not in c.source for c in iter_kept_calls(reports))
