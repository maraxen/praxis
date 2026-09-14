"""AC-6 (Failure 3 gate): OVERRIDABLE_CUES is a compile-time constant scoped to
cue 3, never configuration, and the per-cue exit payload types structurally
carry override affordance fields only for cue 3 (spec §3.3).
"""

import ast
from dataclasses import fields
from pathlib import Path

import pytest

from coxswain.schema.types import (
    OVERRIDABLE_CUES,
    CompletenessExitPayload,
    ConcurrencyExitPayload,
    GroundingExitPayload,
    PreconditionExitPayload,
    request_override,
)

SRC_ROOT = Path(__file__).resolve().parents[1] / "src" / "coxswain"

OVERRIDE_FIELD_NAMES = {"overridable", "override_prompt", "justification"}

CUE_PAYLOADS = {
    0: ConcurrencyExitPayload,
    1: CompletenessExitPayload,
    2: GroundingExitPayload,
    3: PreconditionExitPayload,
}


def test_overridable_cues_is_exactly_cue_3() -> None:
    assert OVERRIDABLE_CUES == frozenset({3})


def test_overridable_cues_is_final_frozenset_of_int() -> None:
    assert isinstance(OVERRIDABLE_CUES, frozenset)
    assert all(isinstance(c, int) for c in OVERRIDABLE_CUES)


@pytest.mark.parametrize("cue", [0, 1, 2])
def test_request_override_raises_for_non_overridable_cues(cue: int) -> None:
    with pytest.raises(Exception, match="overrid"):
        request_override(
            turn_id="cx-1-abc123",
            gate_seq=0,
            cue=cue,
            justification="because",
            ts=1000.0,
        )


def test_request_override_returns_record_for_cue_3() -> None:
    from coxswain.records import OverrideRecord

    rec = request_override(
        turn_id="cx-1-abc123",
        gate_seq=2,
        cue=3,
        justification="operator confirmed the carrier is correct",
        ts=1000.0,
    )
    assert isinstance(rec, OverrideRecord)
    assert rec.turn_id == "cx-1-abc123"
    assert rec.gate_seq == 2
    assert rec.cue == 3


@pytest.mark.parametrize("cue", [0, 1, 2])
def test_exit_payload_structurally_lacks_override_fields(cue: int) -> None:
    """The structural half of AC-6: cues 0/1/2 payloads cannot render an
    override control 'even by mistake' because the fields do not exist."""
    payload_fields = {f.name for f in fields(CUE_PAYLOADS[cue])}
    assert payload_fields & OVERRIDE_FIELD_NAMES == set()


def test_cue_3_payload_carries_override_affordance_fields() -> None:
    payload_fields = {f.name for f in fields(PreconditionExitPayload)}
    assert OVERRIDE_FIELD_NAMES <= payload_fields


def test_constant_is_a_module_level_literal_never_config() -> None:
    """AST check: OVERRIDABLE_CUES is defined once, at module level, as a
    Final-annotated frozenset literal -- not read from env/config/args."""
    types_py = (SRC_ROOT / "schema" / "types.py").read_text()
    tree = ast.parse(types_py)

    defs = [
        node
        for node in tree.body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "OVERRIDABLE_CUES"
    ]
    assert len(defs) == 1, "OVERRIDABLE_CUES must be defined exactly once"
    annotation_src = ast.unparse(defs[0].annotation)
    assert "Final" in annotation_src
    assert defs[0].value is not None, "must have a literal value, not be lazy"

    # Never parameterized: no function argument named like it anywhere in src.
    for path in SRC_ROOT.rglob("*.py"):
        file_tree = ast.parse(path.read_text())
        for node in ast.walk(file_tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                arg_names = {a.arg for a in node.args.args + node.args.kwonlyargs}
                assert "OVERRIDABLE_CUES" not in arg_names, (
                    f"{path}: OVERRIDABLE_CUES must not become a function "
                    "argument (that would make scope configurable)"
                )


def test_no_env_or_config_reads_anywhere_under_src() -> None:
    """Widening by environment or config file must be structurally impossible.
    The foundation has no env needs at all, so forbid the patterns outright;
    a future legitimate need would require amending this test deliberately."""
    forbidden = ("os.environ", "os.getenv", "getenv(")
    for path in SRC_ROOT.rglob("*.py"):
        text = path.read_text()
        for pattern in forbidden:
            assert pattern not in text, f"{path} contains {pattern}"
