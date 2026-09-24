"""Unit tests for oracle_replay tier 1 (backlog #4879).

Tests the common infrastructure (row_to_verifier_inputs, lower_calls-based
static analysis, compare) without running the full corpus. Smoke test on
training/examples.

260902 (spec §11, SEMA-IR): ``adapt_graph`` is deleted. The corpus path now
lowers PLR-named, already-grounded kwargs through
``plr_sema.check.ir.lower_calls`` (``ir_value_of``, ``run_static_calls`` --
see ``oracle_common.py``'s module docstring) instead of adapting a call
sequence into a §6.2 graph payload. ``TestAdaptGraph``/
``TestPLRNamedArguments`` below are rewritten accordingly (renamed to
reflect what they now test).
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "eval"))

from oracle_common import (
    RuntimeOutcome,
    _PRIME_PLATE,
    _normalize_well_refs,
    _underscore_ref_base_counts,
    calls_from_plr_kwargs,
    compare,
    content_digest,
    extract_first_call,
    ir_value_of,
    lower_row_calls,
    param_names_from_contracts,
    resources_from_example,
    row_to_verifier_inputs,
    run_runtime,
    run_static_calls,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = REPO_ROOT / "training" / "examples"
CONTRACTS_PATH = REPO_ROOT / "plr-sema" / "data" / "derived_contracts.json"
FIXTURES_DIR = REPO_ROOT / "plr-sema" / "tests" / "fixtures"


class TestRowToVerifierInputs:
    """Tests for parsing corpus rows into verifier inputs."""

    def test_synthetic_chat_row(self):
        """Parse a synthetic chat-format row (single call extracted, scaffolded)."""
        # Note: corpus rows have only 1 call per row; it gets scaffolded
        row = {
            "messages": [
                {"role": "developer", "content": "You are a model..."},
                {"role": "user", "content": "Transfer 50 microliters from A1 to B1"},
                {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "function": {
                                "name": "transfer",
                                "arguments": {
                                    "source": "src.A1",
                                    "destination": "dst.B1",
                                    "volume_ul": 50,
                                },
                            },
                            "type": "function",
                        },
                    ],
                },
            ],
            "tools": [],
            "metadata": "train",
        }

        call_seq, intent, layout, skip_reason, no_call_reason = row_to_verifier_inputs(
            row, source_file="test", line=1
        )

        # Transfer gets scaffolded with one pick_up_tips prefix
        assert len(call_seq) == 2
        assert call_seq[0]["name"] == "pick_up_tips"
        assert call_seq[1]["name"] == "transfer"
        # #4939 follow-up (260903): record_id is a content digest over
        # (utterance, RAW tool call), not "{source_file}:{line}" -- stable
        # across corpus reordering. "line" is a display-only field now.
        expected_digest = content_digest(
            "Transfer 50 microliters from A1 to B1",
            {"name": "transfer", "params": {"source": "src.A1", "destination": "dst.B1", "volume_ul": 50}},
        )
        assert intent["record_id"] == f"test:{expected_digest}"
        assert intent["utterance"] == "Transfer 50 microliters from A1 to B1"
        assert intent["source"] == "synthetic"
        assert intent["expected_effects"] == []
        assert layout is not None  # scaffold adds seed volumes
        assert "seed_volumes" in layout
        assert "resources" in layout
        assert skip_reason is None  # transfer is executable
        assert no_call_reason is None  # has a tool call

    def test_real_corpus_row(self):
        """Parse the actual first row from corpus_p25.jsonl."""
        corpus_file = REPO_ROOT / "training" / "assemble" / "out" / "corpus_p25.jsonl"
        if not corpus_file.exists():
            pytest.skip("corpus_p25.jsonl not found")

        with open(corpus_file) as f:
            row = json.loads(f.readline())

        call_seq, intent, layout, skip_reason, no_call_reason = row_to_verifier_inputs(
            row, source_file="corpus_p25", line=1
        )

        # Should have extracted a call sequence (or be marked as no_call/skipped)
        assert isinstance(call_seq, list)
        if no_call_reason is None and skip_reason is None:
            assert len(call_seq) > 0
            # Each call should have name and params
            for call in call_seq:
                assert "name" in call
                assert "params" in call
        # Intent record should match the structure. #4939 follow-up
        # (260903): record_id is a content digest over the row's own
        # (utterance, raw tool call), recomputed the same way here.
        expected_utterance, expected_call = extract_first_call(row)
        expected_digest = content_digest(expected_utterance, expected_call)
        assert intent["record_id"] == f"corpus_p25:{expected_digest}"
        assert intent["source"] == "synthetic"
        assert len(intent["calls"]) == len(call_seq)


class TestIrValueOf:
    """Tests for `ir_value_of` (§11.2.2) -- the harvest-time mapping from a
    bound PLR object to IR value JSON, replacing `adapt_graph`'s old
    `repr`-based harvest.
    """

    def test_scalars_and_none(self):
        assert ir_value_of(100) == {"k": "lit", "v": 100}
        assert ir_value_of(100.0) == {"k": "lit", "v": 100.0}
        assert ir_value_of("A1") == {"k": "lit", "v": "A1"}
        assert ir_value_of(None) == {"k": "lit", "v": None}
        assert ir_value_of(True) == {"k": "lit", "v": True}

    def test_list_lowers_to_seq_of_lits(self):
        assert ir_value_of([1, 2, 3]) == {
            "k": "seq",
            "items": [{"k": "lit", "v": 1}, {"k": "lit", "v": 2}, {"k": "lit", "v": 3}],
        }

    def test_unresolvable_object_is_top(self):
        class _Opaque:
            pass

        assert ir_value_of(_Opaque()) == {"k": "top"}

    def test_plr_resource_with_parent_is_name_keyed_ref(self):
        from pylabrobot.resources import Coordinate, Plate, Well

        plate = Plate(
            "plate_1", size_x=10, size_y=10, size_z=10, ordered_items={},
        )
        well = Well("well_1", size_x=1, size_y=1, size_z=1)
        plate.assign_child_resource(well, location=Coordinate.zero())
        value = ir_value_of(well)
        assert value == {"k": "ref", "name": "plate_1", "cell": "well_1"}

    def test_plr_top_level_resource_is_ref_with_no_cell(self):
        from pylabrobot.resources import Plate

        plate = Plate("plate_2", size_x=10, size_y=10, size_z=10, ordered_items={})
        value = ir_value_of(plate)
        assert value == {"k": "ref", "name": "plate_2", "cell": None}


class TestResourcesAndCallsFromExample:
    """Tests for `resources_from_example`/`calls_from_plr_kwargs` -- the
    `lower_calls`-path replacements for `adapt_graph`.
    """

    def test_resources_from_example_field_set(self):
        example = {
            "deck_layout": {
                "resources": {"tip_rack": "TipRack", "src": "Plate", "dst": "Plate"},
            },
        }
        resources = resources_from_example(example)
        assert resources["lh"]["type"] == "LiquidHandler"
        assert resources["tip_rack"]["type"] == "TipRack"
        assert resources["src"]["type"] == "Plate"
        assert resources["dst"]["type"] == "Plate"
        for decl in resources.values():
            assert "is_container" in decl
            assert "is_parameter" in decl
            assert "parents" in decl

    def test_calls_from_plr_kwargs_skips_not_planned(self):
        example = {
            "call_sequence": [
                {"name": "pick_up_tips", "params": {"at": ["tip_rack.A1"]}},
                {"name": "transfer", "params": {"source": "src.A1", "destination": "dst.B1", "volume_ul": 50}},
            ],
        }
        plr_kwargs = {0: {"tip_spots": {"k": "seq", "items": [{"k": "ref", "name": "tip_rack", "cell": "A1"}]}}}
        calls, not_planned = calls_from_plr_kwargs(example, plr_kwargs)
        assert not_planned == [1]
        # §12.1.6 (#4938): calls[0] is UNCONDITIONALLY the scaffolding's
        # setup() reset -- the real (planned) calls follow it.
        assert len(calls) == 2
        assert calls[0]["method"] == "setup"
        assert calls[0]["kwargs"] == {}
        assert calls[0]["receiver"] == "lh"
        assert calls[0]["receiver_type"] == "LiquidHandler"
        assert calls[1]["method"] == "pick_up_tips"
        assert calls[1]["kwargs"] == plr_kwargs[0]
        assert calls[1]["receiver"] == "lh"
        assert calls[1]["receiver_type"] == "LiquidHandler"

    def test_calls_from_plr_kwargs_prepends_setup_even_when_nothing_planned(self):
        """A row where nothing was planned (rows_setup_error, per
        oracle_replay.py's `_is_setup_error`) still gets the prepend --
        harmless, since `not_planned_indices`/`n_operations_executed` (what
        `_is_setup_error` keys off) never read `calls`.
        """
        example = {"call_sequence": [{"name": "pick_up_tips", "params": {"at": ["tip_rack.A1"]}}]}
        calls, not_planned = calls_from_plr_kwargs(example, {})
        assert not_planned == [0]
        assert len(calls) == 1
        assert calls[0]["method"] == "setup"


class TestResourceTypeCapture:
    """§12.4.1 (#4880): `resource_type_of`/`resource_types_from_kwargs` --
    the tier-2a renderer's only source of truth for what PLR class to
    annotate a rendered protocol's resource parameters with, read from the
    REAL bound object rather than guessed from `deck_layout` (which only
    ever carries the scaffolding's own additions).
    """

    def test_resource_type_of_top_level_resource(self):
        from pylabrobot.resources import Resource

        from oracle_common import resource_type_of

        r = Resource(name="tip_rack", size_x=10, size_y=10, size_z=10)
        assert resource_type_of(r) == ("tip_rack", "Resource")

    def test_resource_type_of_cell_resolves_to_parent_name_and_class(self):
        from pylabrobot.resources import Coordinate, Resource, Well

        from oracle_common import resource_type_of

        parent = Resource(name="plate", size_x=10, size_y=10, size_z=10)
        well = Well(name="A1", size_x=1, size_y=1, size_z=1)
        parent.assign_child_resource(well, location=Coordinate(0, 0, 0))
        # The PARENT's name/class, not the well's -- mirrors ir_value_of's
        # own "parent wins" identity rule.
        assert resource_type_of(well) == ("plate", "Resource")

    def test_resource_type_of_non_resource_is_none(self):
        from oracle_common import resource_type_of

        assert resource_type_of(50) is None
        assert resource_type_of("A1") is None
        assert resource_type_of(None) is None

    def test_resource_types_from_kwargs_walks_lists(self):
        from pylabrobot.resources import Coordinate, Resource, Well

        from oracle_common import resource_types_from_kwargs

        tip_rack = Resource(name="tip_rack", size_x=10, size_y=10, size_z=10)
        a1 = Well(name="A1", size_x=1, size_y=1, size_z=1)
        b1 = Well(name="B1", size_x=1, size_y=1, size_z=1)
        tip_rack.assign_child_resource(a1, location=Coordinate(0, 0, 0))
        tip_rack.assign_child_resource(b1, location=Coordinate(0, 1, 0))
        kwargs = {"tip_spots": [a1, b1], "use_channels": [0, 1]}
        assert resource_types_from_kwargs(kwargs) == {"tip_rack": "Resource"}


class TestCompare:
    """Tests for soundness comparisons."""

    def test_unsound_safe_raised(self):
        """Safe + raised = UNSOUND."""
        example = {
            "call_sequence": [{"name": "pick_up_tips", "params": {"at": ["tr.A1"]}}],
            "intent_record": {},
        }
        rt = RuntimeOutcome(
            error="NoTipError: no tip mounted",
            exc_class="NoTipError",
            failing_index=0,
            planned_indices=[0],
            passed=False,
        )
        st = {
            "op_0": {
                "verdict": "safe",
                "n_findings": 0,
                "reasons": [],
            }
        }

        rows = compare(example, rt, st)
        assert len(rows) == 1
        assert rows[0]["unsound"] is True

    def test_unsound_willfail_ran_ok(self):
        """will_fail + ran_ok = UNSOUND."""
        example = {
            "call_sequence": [{"name": "aspirate", "params": {"source": "p.A1", "volume_ul": 50}}],
            "intent_record": {},
        }
        rt = RuntimeOutcome(
            error=None,
            exc_class=None,
            failing_index=None,
            planned_indices=[0],
            passed=True,
        )
        st = {
            "op_0": {
                "verdict": "will_fail",
                "n_findings": 1,
                "reasons": ["too_much_volume"],
            }
        }

        rows = compare(example, rt, st)
        assert len(rows) == 1
        assert rows[0]["unsound"] is True

    def test_sound_safe_ran_ok(self):
        """Safe + ran_ok = sound."""
        example = {
            "call_sequence": [{"name": "move_plate", "params": {"plate": "p1", "to": "l1"}}],
            "intent_record": {},
        }
        rt = RuntimeOutcome(
            error=None,
            exc_class=None,
            failing_index=None,
            planned_indices=[0],
            passed=True,
        )
        st = {
            "op_0": {
                "verdict": "safe",
                "n_findings": 0,
                "reasons": [],
            }
        }

        rows = compare(example, rt, st)
        assert len(rows) == 1
        assert rows[0]["unsound"] is False

    def test_unknown_no_constraint(self):
        """Unknown + anything = no constraint."""
        example = {
            "call_sequence": [{"name": "some_op", "params": {}}],
            "intent_record": {},
        }
        rt = RuntimeOutcome(
            error="SomeError: message",
            exc_class="SomeError",
            failing_index=0,
            planned_indices=[0],
            passed=False,
        )
        st = {
            "op_0": {
                "verdict": "unknown",
                "n_findings": 5,
                "reasons": ["some_reason"],
            }
        }

        rows = compare(example, rt, st)
        assert len(rows) == 1
        assert rows[0]["unsound"] is False


class TestRowCategories:
    """Tests for row categorization: no_call, skipped, executed."""

    def test_no_call_row(self):
        """Clarification turn with no tool_calls."""
        row = {
            "messages": [
                {"role": "user", "content": "What's the tip height?"},
                {"role": "assistant", "content": "The tip height is 10mm."},
            ],
            "tools": [],
            "metadata": "train",
        }

        call_seq, intent, layout, skip_reason, no_call_reason = row_to_verifier_inputs(
            row, source_file="test", line=1
        )

        assert no_call_reason == "no_tool_calls"
        assert skip_reason is None
        assert len(call_seq) == 0
        assert intent["calls"] == []

    def test_skipped_row(self):
        """Call that _precondition_plan refuses (e.g., transfer without volume_ul)."""
        row = {
            "messages": [
                {"role": "user", "content": "Transfer from A1 to B1"},
                {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "function": {
                                "name": "transfer",
                                "arguments": {
                                    "source": "src.A1",
                                    "destination": "dst.B1",
                                    # missing volume_ul
                                },
                            },
                            "type": "function",
                        },
                    ],
                },
            ],
            "tools": [],
            "metadata": "train",
        }

        call_seq, intent, layout, skip_reason, no_call_reason = row_to_verifier_inputs(
            row, source_file="test", line=1
        )

        assert no_call_reason is None
        assert skip_reason is not None  # transfer without volume_ul is skipped
        assert len(call_seq) == 0


class TestPLRNamedArguments:
    """Tests for PLR-named argument handling through the lower_calls path
    (§11.2.2/§11.2.4) -- the direct successor to adapt_graph's old
    plr_kwargs handling, now via run_static_calls + lower_calls's trust
    rule rather than a graph payload's `arguments` dict.
    """

    def test_run_static_calls_uses_plr_named_kwargs(self):
        """A planned call's IR-value-JSON kwargs (PLR-named by
        construction, §11.2.2) reach `lower_calls`; a real PLR parameter
        name is trusted and surfaces in the CALL's kwargs unmangled when
        `param_names` covers it.
        """
        example = {
            "call_sequence": [
                {"name": "pick_up_tips", "params": {"at": ["tip_rack.A1"]}},
            ],
            "deck_layout": {"resources": {"tip_rack": "TipRack"}},
        }
        plr_kwargs = {
            0: {
                "tip_spots": {"k": "seq", "items": [{"k": "ref", "name": "tip_rack", "cell": "A1"}]},
                "use_channels": {"k": "seq", "items": [{"k": "lit", "v": 0}]},
            },
        }
        contracts_json = json.dumps(
            {
                "contracts": {
                    "LiquidHandler.pick_up_tips": {
                        "guards": [],
                        "gaps": [],
                        "params": ["tip_spots", "use_channels"],
                    }
                }
            }
        )
        param_names = param_names_from_contracts(contracts_json)
        st, not_planned = run_static_calls(example, plr_kwargs, contracts_json, param_names=param_names)
        assert not_planned == []
        assert st["op_0"]["verdict"] == "unknown"
        # zero guards/zero gaps/no loop -> the totality fallback finding.
        assert "no_contract_derived" in st["op_0"]["reasons"]

    def test_run_static_calls_not_planned_index_gets_empty_entry(self):
        example = {
            "call_sequence": [
                {"name": "pick_up_tips", "params": {"at": ["tip_rack.A1"]}},
                {"name": "transfer", "params": {"source": "src.A1", "destination": "dst.B1", "volume_ul": 50}},
            ],
        }
        plr_kwargs = {0: {"tip_spots": {"k": "seq", "items": []}}}
        contracts_json = json.dumps({"contracts": {}})
        st, not_planned = run_static_calls(example, plr_kwargs, contracts_json)
        assert not_planned == [1]
        assert st["op_1"] == {"verdict": "unknown", "n_findings": 0, "reasons": []}


class TestSetupPrepend:
    """§12.1.6 / AC-12.3 (#4938 real-programs increment): the corpus
    lowering carries the scaffolding's real `setup()` reset as the first
    CALL, with the sentinel origin "setup", and every OTHER CALL's origin
    is unchanged from a lowering that never saw the prepend at all -- the
    exact `record_id` join to P2.5's recorded results is not shifted by
    one.
    """

    def test_first_call_is_setup_empty_kwargs_sentinel_origin(self):
        example = {
            "call_sequence": [
                {"name": "pick_up_tips", "params": {"at": ["tip_rack.A1"]}},
                {"name": "aspirate", "params": {"source": "src.A1", "volume_ul": 50}},
            ],
            "deck_layout": {"resources": {"tip_rack": "TipRack", "src": "Plate"}},
        }
        plr_kwargs = {
            0: {"tip_spots": {"k": "seq", "items": [{"k": "ref", "name": "tip_rack", "cell": "A1"}]}},
            1: {"resource": {"k": "ref", "name": "src", "cell": "A1"}},
        }
        resources = resources_from_example(example)
        bc, not_planned = lower_row_calls(example, plr_kwargs, resources=resources)
        assert not_planned == []

        sys.path.insert(0, str(REPO_ROOT / "plr-sema" / "src"))
        from plr_sema.check import ir as _ir

        call_instrs = [(pc, instr) for pc, instr in enumerate(bc.instructions) if isinstance(instr, _ir.Call)]
        assert [instr.method for _pc, instr in call_instrs] == ["setup", "pick_up_tips", "aspirate"]
        setup_pc, setup_instr = call_instrs[0]
        assert setup_instr.kwargs == {}
        assert bc.sideband["origin"][setup_pc] == "setup"

    def test_other_origins_unchanged_from_a_lowering_without_the_prepend(self):
        """The origin VALUE sequence assigned to the real calls (in call
        order) is identical whether or not the setup CALL is prepended --
        only its own pc position shifts, never the numbering of the real
        calls after it.
        """
        example = {
            "call_sequence": [
                {"name": "pick_up_tips", "params": {"at": ["tip_rack.A1"]}},
                {"name": "aspirate", "params": {"source": "src.A1", "volume_ul": 50}},
            ],
            "deck_layout": {"resources": {"tip_rack": "TipRack", "src": "Plate"}},
        }
        plr_kwargs = {
            0: {"tip_spots": {"k": "seq", "items": [{"k": "ref", "name": "tip_rack", "cell": "A1"}]}},
            1: {"resource": {"k": "ref", "name": "src", "cell": "A1"}},
        }
        resources = resources_from_example(example)
        bc, _not_planned = lower_row_calls(example, plr_kwargs, resources=resources)

        sys.path.insert(0, str(REPO_ROOT / "plr-sema" / "src"))
        from plr_sema.check import ir as _ir

        # Origin values in pc-ascending order, WITH the prepend.
        with_setup = [v for _pc, v in sorted(bc.sideband["origin"].items())]
        assert with_setup == ["setup", "0", "1"]

        # The same two real calls, lowered directly (no prepend at all) --
        # exactly the pre-increment shape.
        real_calls = [
            {"method": "pick_up_tips", "kwargs": plr_kwargs[0], "receiver": "lh", "receiver_type": "LiquidHandler"},
            {"method": "aspirate", "kwargs": plr_kwargs[1], "receiver": "lh", "receiver_type": "LiquidHandler"},
        ]
        bc_no_setup = _ir.lower_calls(real_calls, resources=resources)
        without_setup = [v for _pc, v in sorted(bc_no_setup.sideband["origin"].items())]
        assert without_setup == ["0", "1"]

        # Same values (with "setup" stripped), in the same order.
        assert [v for v in with_setup if v != "setup"] == without_setup

    def test_compare_alignment_not_shifted_by_setup_pc(self):
        """Tier-1's `compare` alignment (`run_static_calls` -> `compare`)
        never misindexes because of the prepended setup pc: every real
        `call_sequence` index gets its OWN `op_<i>` entry, and no
        `"op_setup"` (or any non-`op_`-prefixed key) leaks into the
        returned per-op dict for downstream consumers (e.g.
        `tip_mutants.py`'s `int(oid.split("_", 1)[1])`) to choke on.
        """
        example = {
            "call_sequence": [
                {"name": "pick_up_tips", "params": {"at": ["tip_rack.A1"]}},
                {"name": "aspirate", "params": {"source": "src.A1", "volume_ul": 50}},
                {"name": "drop_tips", "params": {"at": ["tip_rack.A1"]}},
            ],
            "deck_layout": {"resources": {"tip_rack": "TipRack", "src": "Plate"}},
        }
        plr_kwargs = {
            0: {"tip_spots": {"k": "seq", "items": [{"k": "ref", "name": "tip_rack", "cell": "A1"}]}},
            2: {"tip_spots": {"k": "seq", "items": [{"k": "ref", "name": "tip_rack", "cell": "A1"}]}},
        }
        contracts_json = json.dumps({"contracts": {}})
        st, not_planned = run_static_calls(example, plr_kwargs, contracts_json)
        assert not_planned == [1]
        assert set(st.keys()) == {"op_0", "op_1", "op_2"}
        for oid in st:
            assert oid.startswith("op_")
            int(oid.split("_", 1)[1])  # never raises -- no "op_setup" leak
        rt = RuntimeOutcome(
            error=None, exc_class=None, failing_index=None, planned_indices=[0, 2], passed=True
        )
        rows = compare(example, rt, st)
        assert [r["index"] for r in rows] == [0, 1, 2]
        assert [r["method"] for r in rows] == ["pick_up_tips", "aspirate", "drop_tips"]


class TestT16dSidecarGating:
    """Regression tests for the T16d (#4879) root-cause fixes: ambiguity_class
    gating, move_*/holders wiring, and naturalness mined-call normalization.
    Each test replays a REAL joined corpus row, looked up by the sidecar's
    own stable ``record_id`` (content, e.g. "cov-0080-dispense__missing-slot-00")
    rather than a hardcoded line number, and asserts our outcome now matches
    P2.5's recorded outcome.

    #4939 follow-up (260903): this class previously hardcoded the LINE
    NUMBER each target record_id was verified to sit at in the 260902
    900-row corpus. The 260902->260903 corpus regrew to 1427 rows via
    MID-FILE insertion (natural-phrasing lane, assembly 0.1.4/0.1.5), which
    shifted every row after the insertion point to a new line number and
    broke all 5 of these hardcoded constants (each one now silently fetched
    an unrelated row and failed its own ``srow["record_id"] == ...``
    assertion). corpus_p25.jsonl and corpus_p25_sidecar.jsonl remain
    line-paired companion files (same assembler pass writes both), so
    ``_row_and_sidecar_by_id`` still uses a single positional scan under
    the hood -- it just scans for the target id instead of trusting a
    remembered line number.
    """

    CORPUS_FILE = REPO_ROOT / "training" / "assemble" / "out" / "corpus_p25.jsonl"
    SIDECAR_FILE = REPO_ROOT / "training" / "assemble" / "out" / "corpus_p25_sidecar.jsonl"
    FLOOR_FILE = REPO_ROOT / "training" / "out" / "corpus_p23_floor.jsonl"
    OVERLAY_FILE = REPO_ROOT / "training" / "overlay_gen" / "out" / "overlay_full.jsonl"

    @staticmethod
    def _row_and_sidecar_by_id(record_id: str):
        """(corpus_row, sidecar_row, line_no) for the sidecar row whose OWN
        ``record_id`` field equals ``record_id`` -- found by content, not by
        a remembered line number. Raises (not skips) if the id is gone
        entirely, since that's a real regression, not a missing-fixture
        skip condition (see ``_require_files``).
        """
        with open(TestT16dSidecarGating.CORPUS_FILE) as cf, open(TestT16dSidecarGating.SIDECAR_FILE) as sf:
            for line_no, (corpus_line, sidecar_line) in enumerate(zip(cf, sf), 1):
                srow = json.loads(sidecar_line)
                if srow.get("record_id") == record_id:
                    return json.loads(corpus_line), srow, line_no
        raise AssertionError(f"record_id {record_id!r} not found in {TestT16dSidecarGating.SIDECAR_FILE}")

    def _require_files(self):
        for p in (self.CORPUS_FILE, self.SIDECAR_FILE):
            if not p.exists():
                pytest.skip(f"{p} not found")

    def test_missing_slot_dispense_is_skipped_not_keyerror(self):
        """cov-0080-dispense__missing-slot-00: dispense with volume_ul
        deliberately omitted. Pre-fix, _precondition_plan indexed
        params["volume_ul"] unconditionally and KeyError-crashed (17 rows,
        all missing_slot). floor_gen never reaches _precondition_plan for
        non-"none" ambiguity classes (exec_verify.py cls != "none" gate) --
        floor's own record has execution_verify=None (never executed,
        verified 260902). Post-fix: skipped before _precondition_plan runs,
        no exception.
        """
        self._require_files()
        row, srow, line_no = self._row_and_sidecar_by_id("cov-0080-dispense__missing-slot-00")
        call_seq, intent, layout, skip_reason, no_call_reason = row_to_verifier_inputs(
            row, source_file="corpus_p25", line=line_no,
            ambiguity_class=srow["ambiguity_class"], sidecar_record_id=srow["record_id"],
            provenance=srow["provenance"],
        )
        assert no_call_reason is None
        assert skip_reason is not None
        assert "missing_slot" in skip_reason
        assert call_seq == []

    def test_ambiguous_referent_aspirate_is_skipped(self):
        """cov-0030-aspirate__ambiguous-referent-00: a deliberately-vague
        ref. Pre-fix, this executed and usually raised GroundingError
        (spurious -- floor_gen's own harness never runs ambiguous-referent
        cells at all). Post-fix: skipped.
        """
        self._require_files()
        row, srow, line_no = self._row_and_sidecar_by_id("cov-0030-aspirate__ambiguous-referent-00")
        call_seq, intent, layout, skip_reason, no_call_reason = row_to_verifier_inputs(
            row, source_file="corpus_p25", line=line_no,
            ambiguity_class=srow["ambiguity_class"], sidecar_record_id=srow["record_id"],
            provenance=srow["provenance"],
        )
        assert no_call_reason is None
        assert skip_reason is not None
        assert "ambiguous_referent" in skip_reason
        assert call_seq == []

    def test_move_resource_holders_fix_matches_p25_passed(self):
        """cov-0455-move_resource__none-00: "Move hotel_stack_1 to
        reservoir_1." Pre-fix, oracle_common never computed
        DeckLayout.holders, so infer_layout() defaulted both names to a bare
        Plate and PLR raised "RuntimeError: Can only drop Lid resources onto
        Plate 'reservoir_1'." on every move_resource/move_plate/move_lid row
        (45/45 crosscheck disagreements against floor, all this one shape).
        floor_gen.exec_verify computes holders via _resource_type_holders
        (exec_verify.py:126-145); oracle_common now mirrors it. P2.5 recorded
        passed=True for this record_id; assert we now agree.
        """
        self._require_files()
        if not self.FLOOR_FILE.exists():
            pytest.skip(f"{self.FLOOR_FILE} not found")
        row, srow, line_no = self._row_and_sidecar_by_id("cov-0455-move_resource__none-00")
        call_seq, intent, layout, skip_reason, no_call_reason = row_to_verifier_inputs(
            row, source_file="corpus_p25", line=line_no,
            ambiguity_class=srow["ambiguity_class"], sidecar_record_id=srow["record_id"],
            provenance=srow["provenance"],
        )
        assert skip_reason is None and no_call_reason is None
        assert layout is not None and layout.get("holders") == ["hotel_stack_1", "reservoir_1"]
        rt = run_runtime({"call_sequence": call_seq, "intent_record": intent, "deck_layout": layout})
        with open(self.FLOOR_FILE) as f:
            floor_by_id = {json.loads(l)["record_id"]: json.loads(l) for l in f}
        p25_row = floor_by_id[srow["record_id"]]
        p25_passed = p25_row["execution_verify"]["passed"]
        assert p25_passed is True
        assert rt.error is None, f"expected ran_ok (matches P2.5 passed={p25_passed}), got {rt.error!r}"

    def test_naturalness_ungroundable_mined_expr_is_skipped(self):
        """ovl-0740a87130: pick_up_tips at a loop-variable slice
        (source_tip_spots[i:i + batch_size]) -- not a literal, statically
        groundable ref. overlay_gen's own harness never executes this
        (execution_verify=None, confirmed 260902); pre-fix, oracle_common fed
        the raw expression straight into the dispatcher. Post-fix: skipped
        via overlay_gen._normalize_params, matching overlay_gen's own gate.
        """
        self._require_files()
        row, srow, line_no = self._row_and_sidecar_by_id("ovl-0740a87130")
        assert srow["provenance"] == "naturalness"
        call_seq, intent, layout, skip_reason, no_call_reason = row_to_verifier_inputs(
            row, source_file="corpus_p25", line=line_no,
            ambiguity_class=srow["ambiguity_class"], sidecar_record_id=srow["record_id"],
            provenance=srow["provenance"],
        )
        assert no_call_reason is None
        assert skip_reason is not None
        assert "variable/computed value" in skip_reason
        assert call_seq == []

    def test_naturalness_bracket_ref_normalizes_and_matches_p25_passed(self):
        """ovl-05a03ba41d: dispense(destination='plate["C1"]', ...) -- a
        literal bracket-subscript mined ref. Pre-fix, this opaque
        un-normalized name typed as a bare Plate via infer_layout, producing
        "'Plate' object has no attribute 'tracker'" / TypeError (the
        remaining naturalness disagreement classes). Post-fix: normalized to
        'plate.C1' via overlay_gen._normalize_ref before _precondition_plan,
        matching overlay_gen's own execution_verify_call. overlay recorded
        passed=True for this id; assert we now agree.
        """
        self._require_files()
        if not self.OVERLAY_FILE.exists():
            pytest.skip(f"{self.OVERLAY_FILE} not found")
        row, srow, line_no = self._row_and_sidecar_by_id("ovl-05a03ba41d")
        call_seq, intent, layout, skip_reason, no_call_reason = row_to_verifier_inputs(
            row, source_file="corpus_p25", line=line_no,
            ambiguity_class=srow["ambiguity_class"], sidecar_record_id=srow["record_id"],
            provenance=srow["provenance"],
        )
        assert skip_reason is None and no_call_reason is None
        dispense_call = [c for c in call_seq if c["name"] == "dispense"][0]
        assert dispense_call["params"]["destination"] == "plate.C1"
        rt = run_runtime({"call_sequence": call_seq, "intent_record": intent, "deck_layout": layout})
        with open(self.OVERLAY_FILE) as f:
            overlay_by_id = {json.loads(l)["id"]: json.loads(l) for l in f}
        p25_row = overlay_by_id[srow["record_id"]]
        p25_passed = p25_row["execution_verify"]["passed"]
        assert p25_passed is True
        assert rt.error is None, f"expected ran_ok (matches overlay passed={p25_passed}), got {rt.error!r}"


class TestSmokeOnExamples:
    """Smoke test: run the full pipeline on training/examples."""

    @pytest.mark.skipif(not EXAMPLES_DIR.exists(), reason="examples dir missing")
    def test_full_pipeline_on_examples(self):
        """Run runtime + static (lower_calls + check_ir, §11.2.2) + compare
        on all examples.
        """
        contracts_json = CONTRACTS_PATH.read_text()
        param_names = param_names_from_contracts(contracts_json)

        results = []
        for example_file in sorted(EXAMPLES_DIR.glob("*.json")):
            example = json.loads(example_file.read_text())
            if "call_sequence" not in example or "intent_record" not in example:
                continue

            rt = run_runtime(example)
            st, not_planned = run_static_calls(example, rt.plr_kwargs, contracts_json, param_names=param_names)
            assert not_planned == [], f"{example_file.name}: unexpected not-planned indices {not_planned}"
            rows = compare(example, rt, st)

            results.append({
                "file": example_file.name,
                "n_ops": len(rows),
                "unsound": sum(r["unsound"] for r in rows),
                "rows": rows,
            })

        # Per spike output: 4 examples, 10 ops, 0 unsound
        assert len(results) == 4
        assert sum(r["n_ops"] for r in results) == 10
        assert sum(r["unsound"] for r in results) == 0


def _chat_row(name: str, arguments: dict, utterance: str = "test utterance") -> dict:
    """Minimal chat-format corpus row with one tool call (corpus_p25.jsonl shape)."""
    return {
        "messages": [
            {"role": "developer", "content": "sys"},
            {"role": "user", "content": utterance},
            {
                "role": "assistant",
                "tool_calls": [
                    {"function": {"name": name, "arguments": arguments}, "type": "function"},
                ],
            },
        ],
        "tools": [],
        "metadata": "train",
    }


class TestUnderscoreRefBaseCounts:
    """Tests for _underscore_ref_base_counts (§12.4.3's self-consistency signal)."""

    def test_repeated_base_counted(self):
        counts = _underscore_ref_base_counts(
            {"at": ["filter_tip_box_D1", "filter_tip_box_D2", "filter_tip_box_D3"]}
        )
        assert counts["filter_tip_box"] == 3

    def test_distinct_bases_each_counted_once(self):
        counts = _underscore_ref_base_counts(
            {"source": "plate_A_H12", "destination": "plate_B_A1"}
        )
        assert counts == {"plate_A": 1, "plate_B": 1}

    def test_non_matching_shape_not_counted(self):
        # "col1"/"slot2" have no A-H row letter -- not a well-ref shape at all.
        counts = _underscore_ref_base_counts(
            {"destination": "assay_plate_col1", "other": "disposal_rack_slot2"}
        )
        assert counts == {}


class TestNormalizeWellRefs:
    """Tests for _normalize_well_refs (§12.4.3, AC-12.19)."""

    def test_declared_via_precondition_plan_resources_normalizes(self):
        """AC-12.19's worked example, using the ONE base _precondition_plan
        actually declares (``_PRIME_PLATE``): a dispense whose destination
        happens to share that base normalises and its skip_reason stays
        None (dispense is executable either way -- the point is the REF
        got rewritten before _precondition_plan/deck_layout ever saw it).
        """
        ref = f"{_PRIME_PLATE}_A1"
        call = {"name": "dispense", "params": {"destination": ref, "volume_ul": 50}}
        new_call, rewritten = _normalize_well_refs(call)
        assert rewritten == [ref]
        assert new_call["params"]["destination"] == f"{_PRIME_PLATE}.A1"
        # Original call object is untouched (defensive copy, not a mutation).
        assert call["params"]["destination"] == ref

    def test_self_consistent_repeat_normalizes(self):
        """4 tip-spot refs in one pick_up_tips.at list, all on the same
        undeclared base -- internal repetition is its own declaration
        (§12.4.3(b))."""
        call = {
            "name": "pick_up_tips",
            "params": {"at": ["filter_tip_box_D1", "filter_tip_box_D2"]},
        }
        new_call, rewritten = _normalize_well_refs(call)
        assert sorted(rewritten) == ["filter_tip_box_D1", "filter_tip_box_D2"]
        assert new_call["params"]["at"] == ["filter_tip_box.D1", "filter_tip_box.D2"]

    def test_undeclared_single_occurrence_left_verbatim(self):
        """AC-12.19's contrast case: foo_A1 with no foo declared anywhere
        (not in _precondition_plan's resources, not repeated) stays
        exactly as it is."""
        call = {"name": "aspirate", "params": {"source": "foo_A1", "volume_ul": 10}}
        new_call, rewritten = _normalize_well_refs(call)
        assert rewritten == []
        assert new_call is call  # identical object, not even a copy
        assert new_call["params"]["source"] == "foo_A1"

    def test_non_well_shaped_ref_left_untouched(self):
        call = {"name": "drop_tips", "params": {"destination": "trash"}}
        new_call, rewritten = _normalize_well_refs(call)
        assert rewritten == []
        assert new_call["params"]["destination"] == "trash"


class TestRowToVerifierInputsNormalization:
    """Integration tests: §12.4.3's normalisation wired into
    row_to_verifier_inputs (AC-12.19)."""

    def test_declared_base_resolves_and_executes(self):
        ref = f"{_PRIME_PLATE}_A1"
        row = _chat_row("dispense", {"destination": ref, "volume_ul": 50})
        call_seq, intent, layout, skip_reason, no_call_reason = row_to_verifier_inputs(
            row, source_file="test", line=1
        )
        assert no_call_reason is None
        assert skip_reason is None
        assert intent["normalized_refs"] == [ref]
        real_call = call_seq[-1]
        assert real_call["name"] == "dispense"
        assert real_call["params"]["destination"] == f"{_PRIME_PLATE}.A1"

    def test_undeclared_base_left_verbatim_keeps_current_outcome(self):
        row = _chat_row("aspirate", {"source": "foo_A1", "volume_ul": 10})
        call_seq, intent, layout, skip_reason, no_call_reason = row_to_verifier_inputs(
            row, source_file="test", line=1
        )
        assert no_call_reason is None
        assert skip_reason is None  # aspirate has everything _precondition_plan needs
        assert intent["normalized_refs"] == []
        real_call = call_seq[-1]
        assert real_call["params"]["source"] == "foo_A1"  # untouched

    def test_no_call_row_has_no_normalized_refs(self):
        row = {
            "messages": [
                {"role": "developer", "content": "sys"},
                {"role": "user", "content": "what can you do?"},
                {"role": "assistant", "content": "I can pipette."},
            ],
            "tools": [],
            "metadata": "train",
        }
        call_seq, intent, layout, skip_reason, no_call_reason = row_to_verifier_inputs(
            row, source_file="test", line=1
        )
        assert no_call_reason == "no_tool_calls"
        assert intent["normalized_refs"] == []


class TestByteIdentityInvariant:
    """AC-12.19: grounding.py and every file under training/assemble/out/
    are byte-identical before and after normalisation -- this is a LOADER
    reading of an ambiguous ref, not a corpus/grounding-grammar rewrite.
    """

    def _tracked_files(self) -> list[Path]:
        grounding = REPO_ROOT / "training" / "verify" / "grounding.py"
        assemble_out = REPO_ROOT / "training" / "assemble" / "out"
        files = [grounding]
        if assemble_out.is_dir():
            files.extend(sorted(p for p in assemble_out.rglob("*") if p.is_file()))
        return files

    def _hashes(self, files: list[Path]) -> dict[str, str]:
        return {
            str(f): hashlib.sha256(f.read_bytes()).hexdigest()
            for f in files
            if f.exists()
        }

    def test_normalization_does_not_touch_grounding_or_assemble_out(self):
        files = self._tracked_files()
        assert files, "expected grounding.py + training/assemble/out/* to exist"
        before = self._hashes(files)

        # Exercise every normalisation path: declared-via-resources,
        # self-consistent repeat, and undeclared/verbatim -- plus a full
        # row_to_verifier_inputs pass, so any accidental write during
        # normalisation would be caught here.
        _normalize_well_refs(
            {"name": "dispense", "params": {"destination": f"{_PRIME_PLATE}_A1", "volume_ul": 50}}
        )
        _normalize_well_refs(
            {"name": "pick_up_tips", "params": {"at": ["filter_tip_box_D1", "filter_tip_box_D2"]}}
        )
        _normalize_well_refs({"name": "aspirate", "params": {"source": "foo_A1", "volume_ul": 10}})
        row_to_verifier_inputs(
            _chat_row("dispense", {"destination": f"{_PRIME_PLATE}_A1", "volume_ul": 50}),
            source_file="test", line=1,
        )

        after = self._hashes(self._tracked_files())
        assert after == before


class TestVolumeMutantWiring:
    """T28 (spec 260903 §14.9, `260903_plr-sema-volume-increment.md`,
    backlog #4960): the shared `run_one_mutant` refactor (mutator/
    expected-exception as arguments, not module globals) and
    `volume_mutants.py`'s own `v1_overdraw_dispense` mutator. Fast,
    in-memory, single-example -- no corpus scan (§14.13 T28's own
    ``uv run pytest ... -q`` gate line names this file precisely because it
    must stay fast).
    """

    def _base_example(self) -> dict:
        payload = json.loads((EXAMPLES_DIR / "aspirate_dispense_drop.json").read_text(encoding="utf-8"))
        return {
            "call_sequence": payload["call_sequence"],
            "intent_record": payload["intent_record"],
            "deck_layout": payload["deck_layout"],
        }

    def test_run_one_mutant_is_the_same_function_object_in_both_modules(self) -> None:
        """`volume_mutants.py` reuses `tip_mutants.run_one_mutant` verbatim
        rather than re-implementing the runtime-then-static harness --
        the refactor's whole point (§14.9's normative paragraph).
        """
        import tip_mutants
        import volume_mutants

        assert volume_mutants.run_one_mutant is tip_mutants.run_one_mutant
        assert volume_mutants.MutantResult is tip_mutants.MutantResult

    def test_make_v1_overdraw_dispense_mutates_only_the_last_dispense_volume(self) -> None:
        import volume_mutants

        example = self._base_example()
        mutant = volume_mutants.make_v1_overdraw_dispense(example)
        assert mutant is not None

        dispense_idx = next(
            i for i, c in enumerate(example["call_sequence"]) if c["name"] == "dispense"
        )
        orig_volume = example["call_sequence"][dispense_idx]["params"]["volume_ul"]
        mut_volume = mutant["call_sequence"][dispense_idx]["params"]["volume_ul"]
        assert mut_volume > orig_volume

        # every other call, and the deck layout/seeds, are carried
        # unchanged -- §14.9's own argument for why the state a mutant
        # over-draws against must come from the UNMUTATED call.
        for i, call in enumerate(example["call_sequence"]):
            if i != dispense_idx:
                assert mutant["call_sequence"][i] == call
        assert mutant["deck_layout"] == example["deck_layout"]

    def test_make_v1_overdraw_dispense_none_without_a_dispense_call(self) -> None:
        import volume_mutants

        example = self._base_example()
        example["call_sequence"] = [c for c in example["call_sequence"] if c["name"] != "dispense"]
        assert volume_mutants.make_v1_overdraw_dispense(example) is None

    def test_v1_overdraw_dispense_fires_will_fail_at_the_raised_index(self) -> None:
        """End-to-end over ONE synthetic example (not the corpus): the
        mutated dispense raises `TooLittleLiquidError`, and the static side
        -- run under the runtime's OWN observed `env` (T27/T28) -- reports
        `WILL_FAIL` at that exact index, with neither unsoundness flag set.
        """
        import volume_mutants

        example = self._base_example()
        contracts_json = CONTRACTS_PATH.read_text(encoding="utf-8")
        param_names = param_names_from_contracts(contracts_json)

        result = volume_mutants.run_one_mutant(
            "ex_aspirate_dispense",
            "v1_overdraw_dispense",
            example,
            contracts_json,
            param_names,
            volume_mutants.make_v1_overdraw_dispense,
            volume_mutants._EXPECTED_EXC["v1_overdraw_dispense"],
        )

        assert result.ran, result.error
        assert result.error is None, result.error
        assert result.raised_as_expected, (result.raised_exc_class, result.error)
        assert result.static_verdict_at_index == "will_fail", result
        assert not result.unsound_safe
        assert not result.unsound_will_fail_elsewhere


class TestTier2bVolumeSidecarFields:
    """T28 (spec 260903 §14.9/§14.13, backlog #4960): `region_oracle
    ._volume_slice_summary`'s sidecar computation -- `volume_fixtures`/
    `volume_unsound`/`volume_will_fail_fired` are a NAMED SLICE of the
    `region_*` totals restricted to `volume_*`-prefixed fixtures. Tested
    against synthetic `FixtureOutcome`s, never a real fixture run (no
    subprocess extraction, no chatterbox execution) -- fast.
    """

    def _outcome(self, name: str, *, will_fail_at_raised: bool, n_unsound: int = 0):
        import region_oracle

        unsound_rows = [
            region_oracle.UnsoundRow(name, "dispense", 1, 1, "op_0", "ran_ok", "will_fail")
            for _ in range(n_unsound)
        ]
        return region_oracle.FixtureOutcome(
            name=name, shape=region_oracle._shape_of(name), status="compared",
            will_fail_at_raised=will_fail_at_raised, unsound_rows=unsound_rows,
        )

    def test_slice_counts_only_volume_prefixed_fixtures(self) -> None:
        import region_oracle

        outcomes = [
            self._outcome("volume_straightline", will_fail_at_raised=True),
            self._outcome("volume_second_iteration", will_fail_at_raised=True),
            self._outcome("volume_collective_exhaustion", will_fail_at_raised=True),
            self._outcome("volume_retip", will_fail_at_raised=False),  # UNKNOWN, not WILL_FAIL
            self._outcome("for_pickup_no_drop_raises", will_fail_at_raised=True),  # NOT a volume_* fixture
        ]
        summary = region_oracle._volume_slice_summary(outcomes)
        assert summary == {"volume_fixtures": 4, "volume_unsound": 0, "volume_will_fail_fired": 3}

    def test_slice_propagates_unsound_rows(self) -> None:
        import region_oracle

        outcomes = [
            self._outcome("volume_straightline", will_fail_at_raised=True, n_unsound=2),
            self._outcome("straightline_clean", will_fail_at_raised=False, n_unsound=5),  # NOT volume_*
        ]
        summary = region_oracle._volume_slice_summary(outcomes)
        assert summary["volume_fixtures"] == 1
        assert summary["volume_unsound"] == 2  # the non-volume_* fixture's 5 are excluded
        assert summary["volume_will_fail_fired"] == 1

    def test_empty_outcomes_yield_zeroed_slice(self) -> None:
        import region_oracle

        assert region_oracle._volume_slice_summary([]) == {
            "volume_fixtures": 0, "volume_unsound": 0, "volume_will_fail_fired": 0,
        }


class TestTier2ExtractorSidecarSchema:
    """T28 (spec 260903 §14.13): `tier2_extractor.bth.toml`'s
    `[result_schema]` carries the three new volume sidecar fields.
    """

    def test_bth_toml_declares_volume_sidecar_fields(self) -> None:
        try:
            import tomllib
        except ModuleNotFoundError:  # pragma: no cover - py<3.11 fallback
            import tomli as tomllib  # type: ignore[no-redef]

        toml_path = REPO_ROOT / "plr-sema" / "eval" / "tier2_extractor.bth.toml"
        payload = tomllib.loads(toml_path.read_text(encoding="utf-8"))
        schema = payload["result_schema"]
        assert schema["volume_fixtures"] == "int"
        assert schema["volume_unsound"] == "int"
        assert schema["volume_will_fail_fired"] == "int"


class TestO1ElementTypes:
    """260904 (spec §15.4, O1, T30b): the operand observation. Default-off
    byte-identical unless a caller opts in; the new per-element walk; the
    heterogeneous-parent fail-closed rule (C11b).
    """

    def test_element_types_from_kwargs_singleton_parent(self):
        from pylabrobot.resources import Coordinate, Resource, Well

        from oracle_common import element_type_singletons, element_types_from_kwargs

        tip_rack = Resource(name="tip_rack", size_x=10, size_y=10, size_z=10)
        a1 = Well(name="A1", size_x=1, size_y=1, size_z=1)
        b1 = Well(name="B1", size_x=1, size_y=1, size_z=1)
        tip_rack.assign_child_resource(a1, location=Coordinate(0, 0, 0))
        tip_rack.assign_child_resource(b1, location=Coordinate(0, 1, 0))

        raw = element_types_from_kwargs({"tip_spots": [a1, b1]})
        assert raw == {"tip_rack": {"Well"}}
        assert element_type_singletons(raw) == {"tip_rack": "Well"}

    def test_element_types_from_kwargs_heterogeneous_parent_is_none(self):
        """C11b's fail-closed rule: a parent whose children span more than
        one generic class reduces to `element_type: None`, never
        first-element-wins."""
        from pylabrobot.resources import Container, Coordinate, Resource, Well

        from oracle_common import element_type_singletons, element_types_from_kwargs

        deck = Resource(name="deck", size_x=100, size_y=100, size_z=100)
        container = Container(name="container", size_x=10, size_y=10, size_z=10)
        well = Well(name="A1", size_x=1, size_y=1, size_z=1)
        deck.assign_child_resource(container, location=Coordinate(0, 0, 0))
        deck.assign_child_resource(well, location=Coordinate(20, 0, 0))

        raw = element_types_from_kwargs({"resources": [container, well]})
        assert raw == {"deck": {"Container", "Well"}}
        assert element_type_singletons(raw) == {"deck": None}

    def test_element_types_from_kwargs_no_parent_contributes_nothing(self):
        from pylabrobot.resources import Resource

        from oracle_common import element_types_from_kwargs

        top = Resource(name="tip_rack", size_x=10, size_y=10, size_z=10)
        assert element_types_from_kwargs({"tip_spots": [top]}) == {}

    def test_resources_from_example_threads_resource_and_element_type(self):
        example = {"deck_layout": {"resources": {"tip_rack": "TipRack"}}}
        resources = resources_from_example(
            example,
            resource_types={"tip_rack": "TipRack", "extra": "Plate"},
            element_types={"tip_rack": "TipSpot"},
        )
        assert resources["tip_rack"]["type"] == "TipRack"
        assert resources["tip_rack"]["element_type"] == "TipSpot"
        assert resources["extra"]["type"] == "Plate"
        assert "element_type" not in resources["extra"]

    def test_resources_from_example_default_off_unchanged(self):
        example = {"deck_layout": {"resources": {"tip_rack": "TipRack"}}}
        assert resources_from_example(example) == resources_from_example(
            example, resource_types=None, element_types=None
        )

    def test_run_static_calls_observe_element_types_default_off_byte_identical(self):
        """The default-off switch (§15.4, O1): passing `resource_types`/
        `element_types` alongside `observe_element_types=False` (the
        default) must be IGNORED -- byte-identical to a caller that never
        knew the parameters existed at all."""
        example = {
            "call_sequence": [
                {"name": "pick_up_tips", "params": {"at": ["tip_rack.A1"]}},
            ],
            "deck_layout": {"resources": {"tip_rack": "TipRack"}},
        }
        plr_kwargs = {
            0: {
                "tip_spots": {"k": "seq", "items": [{"k": "ref", "name": "tip_rack", "cell": "A1"}]},
                "use_channels": {"k": "seq", "items": [{"k": "lit", "v": 0}]},
            },
        }
        contracts_json = json.dumps(
            {
                "contracts": {
                    "LiquidHandler.pick_up_tips": {
                        "guards": [],
                        "gaps": [],
                        "params": ["tip_spots", "use_channels"],
                    }
                }
            }
        )
        param_names = param_names_from_contracts(contracts_json)

        baseline = run_static_calls(example, plr_kwargs, contracts_json, param_names=param_names)
        with_ignored_data = run_static_calls(
            example,
            plr_kwargs,
            contracts_json,
            param_names=param_names,
            observe_element_types=False,
            resource_types={"tip_rack": "SomethingElse"},
            element_types={"tip_rack": "TipSpot"},
        )
        assert baseline == with_ignored_data


# ---------------------------------------------------------------------------
# #4979 (T32, spec 260904 §15.10): additive report fields -- excludes_sites
# threading, n_findings_decided/n_findings_by_reason, rows_excused_by_scope
# (annotation only), residual_reason_sets_by_method, and
# n_decided_via_env_ref_shortcircuit's documented null.
# ---------------------------------------------------------------------------


class TestExcludesSitesThreading:
    """`run_static_calls`'s new `excludes_sites` kwarg (oracle_common.py),
    threaded verbatim to `check_ir`'s own collector."""

    def test_default_none_byte_identical_to_omitting_it(self):
        """A caller that never knew the parameter existed (every pre-T32
        caller) must see byte-identical behaviour -- mirrors the O1
        default-off test above."""
        example = {
            "call_sequence": [
                {"name": "pick_up_tips", "params": {"at": ["tip_rack.A1"]}},
            ],
            "deck_layout": {"resources": {"tip_rack": "TipRack"}},
        }
        plr_kwargs = {
            0: {
                "tip_spots": {"k": "seq", "items": [{"k": "ref", "name": "tip_rack", "cell": "A1"}]},
            },
        }
        contracts_json = json.dumps(
            {
                "contracts": {
                    "LiquidHandler.pick_up_tips": {
                        "guards": [],
                        "gaps": [],
                        "params": ["tip_spots"],
                    }
                }
            }
        )
        param_names = param_names_from_contracts(contracts_json)

        baseline = run_static_calls(example, plr_kwargs, contracts_json, param_names=param_names)
        explicit_none = run_static_calls(
            example, plr_kwargs, contracts_json, param_names=param_names, excludes_sites=None,
        )
        assert baseline == explicit_none

    def test_tier_iii_guard_populates_the_passed_list(self):
        """A guard with `raises` starting `"<dynamic:"` (tier (iii),
        `is_dynamic_raise`) folds its site into whatever list the caller
        passed -- one list per `run_static_calls` invocation (one per ROW),
        never per operation, matching `AnalysisReport.scope`'s own shape."""
        example = {
            "call_sequence": [
                {"name": "pick_up_tips", "params": {"at": ["tip_rack.A1"]}},
            ],
            "deck_layout": {"resources": {"tip_rack": "TipRack"}},
        }
        plr_kwargs = {
            0: {
                "tip_spots": {"k": "seq", "items": [{"k": "ref", "name": "tip_rack", "cell": "A1"}]},
            },
        }
        contracts_json = json.dumps(
            {
                "contracts": {
                    "LiquidHandler.pick_up_tips": {
                        "guards": [
                            {
                                "site": {
                                    "file": "external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py",
                                    "lineno": 576,
                                    "qualname": "LiquidHandler.pick_up_tips",
                                },
                                "condition": "error is not None",
                                "predicate": {"node": "TRUE"},
                                "kind": "raise_guard",
                                "raises": "<dynamic:error>",
                                "depth": 0,
                                "scope_trail": [],
                                "free_vars": [],
                                "bindings": [],
                            }
                        ],
                        "gaps": [],
                        "params": ["tip_spots"],
                    }
                }
            }
        )
        param_names = param_names_from_contracts(contracts_json)
        collected: list = []
        st, _not_planned = run_static_calls(
            example, plr_kwargs, contracts_json, param_names=param_names, excludes_sites=collected,
        )
        assert st["op_0"]["verdict"] == "unknown"
        assert "guard_env_dependent" in st["op_0"]["reasons"]
        assert len(collected) == 1
        assert collected[0].lineno == 576
        assert collected[0].qualname == "LiquidHandler.pick_up_tips"


class TestT32AdditiveReportFields:
    """End-to-end: `oracle_replay.main()`'s new report fields
    (#4979, T32, spec 260904 §15.10)."""

    def _run_main(self, tmp_path, rows):
        import oracle_replay

        corpus_path = tmp_path / "corpus.jsonl"
        corpus_path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
        report_path = tmp_path / "report.json"
        rc = oracle_replay.main(["--corpus", str(corpus_path), "--report", str(report_path)])
        return rc, json.loads(report_path.read_text())

    def test_new_fields_present_and_well_typed(self, tmp_path):
        row = _chat_row(
            "pick_up_tips",
            {"tip_spots": ["tip_rack.A1"]},
            utterance="pick up a tip",
        )
        rc, report = self._run_main(tmp_path, [row])

        assert "n_findings_decided" in report
        assert isinstance(report["n_findings_decided"], int)
        assert isinstance(report["n_findings_decided_by_site"], dict)
        assert isinstance(report["n_findings_by_reason"], dict)
        # §15.9 block (4): null -- GuardResult exposes no
        # decided_via_shortcircuit field this increment (documented, not
        # a placeholder oversight).
        assert report["n_decided_via_env_ref_shortcircuit"] is None
        assert isinstance(report["rows_excused_by_scope"], dict)
        assert isinstance(report["rows_excused_by_scope"]["count"], int)
        assert isinstance(report["rows_excused_by_scope"]["examples"], list)
        assert isinstance(report["residual_reason_sets_by_method"], dict)

        # summary_flat carries the two gate-relevant scalars too.
        assert report["summary_flat"]["n_findings_decided"] == report["n_findings_decided"]
        assert report["summary_flat"]["rows_excused_by_scope"] == report["rows_excused_by_scope"]["count"]

        # Every row dict publishes its own excludes_sites annotation.
        for r in report["rows"]:
            assert "excludes_sites" in r
            assert isinstance(r["excludes_sites"], list)

    def test_rows_excused_by_scope_is_annotation_only_no_gate_effect(self, tmp_path):
        """A pure annotation: `unsound`/exit code are computed exactly as
        before (`oracle_common.compare`, unmodified predicate) regardless
        of what `rows_excused_by_scope` measures."""
        row = _chat_row(
            "pick_up_tips",
            {"tip_spots": ["tip_rack.A1"]},
            utterance="pick up a tip",
        )
        rc, report = self._run_main(tmp_path, [row])
        # rc is decided solely by unsound/check_graph_exceptions -- verify
        # the documented formula still holds with the new fields present.
        expected_rc = 1 if (report["summary_flat"]["unsound"] > 0 or report["summary_flat"]["check_graph_exceptions"] > 0) else 0
        assert rc == expected_rc
