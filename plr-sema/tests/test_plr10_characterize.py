"""Unit tests for plr10_characterize (backlog #5622 measurement instrument).

Tiny synthetic rows only (same style as test_oracle_replay.py); never the full
benchmark. The end-to-end runs are module-scoped so each arm pair runs once.
"""

from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path

import pytest

_EVAL_DIR = Path(__file__).resolve().parents[1] / "eval"
sys.path.insert(0, str(_EVAL_DIR))

import oracle_replay  # noqa: E402
import plr10_characterize as pc  # noqa: E402

SIDECAR_TOML = _EVAL_DIR / "plr10_characterize.bth.toml"


def _chat_row(name: str, arguments: dict, utterance: str) -> dict:
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


#: Executes (pick_up_tips scaffold + transfer) and completes at runtime.
_OK_ROW = _chat_row(
    "transfer", {"source": "src.A1", "destination": "dst.B1", "volume_ul": 50}, "transfer small"
)
#: Executes and RAISES at runtime (TooLittleVolumeError at the transfer).
_RAISING_ROW = _chat_row(
    "transfer", {"source": "src.A1", "destination": "dst.B1", "volume_ul": 100000}, "transfer huge"
)


def _run(tmp_path: Path, rows: list[dict], arm: str = "both") -> tuple[int, Path]:
    corpus = tmp_path / "corpus.jsonl"
    corpus.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    out_dir = tmp_path / "out"
    rc = pc.main(["--corpus", str(corpus), "--out-dir", str(out_dir), "--arm", arm])
    return rc, out_dir


@pytest.fixture(scope="module")
def raising_run(tmp_path_factory: pytest.TempPathFactory) -> Path:
    tmp = tmp_path_factory.mktemp("raising")
    rc, out_dir = _run(tmp, [_OK_ROW, _RAISING_ROW])
    assert rc == 0
    return out_dir


@pytest.fixture(scope="module")
def clean_run(tmp_path_factory: pytest.TempPathFactory) -> Path:
    tmp = tmp_path_factory.mktemp("clean")
    rc, out_dir = _run(tmp, [_OK_ROW])
    assert rc == 0
    return out_dir


class TestPatchRestored:
    def test_seam_restored_after_normal_exit(self) -> None:
        original = oracle_replay.run_static_calls
        with pc.all_safe_static_verdicts():
            assert oracle_replay.run_static_calls is not original
        assert oracle_replay.run_static_calls is original

    def test_seam_restored_after_exception(self) -> None:
        original = oracle_replay.run_static_calls
        with pytest.raises(RuntimeError, match="boom"):
            with pc.all_safe_static_verdicts():
                assert oracle_replay.run_static_calls is not original
                raise RuntimeError("boom")
        assert oracle_replay.run_static_calls is original

    def test_wrapper_forces_only_the_verdict(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake = {
            "op_0": {"verdict": "will_fail", "n_findings": 2, "reasons": ["r"], "scoped_verdict": "unknown"},
            "op_1": {"verdict": "unknown", "n_findings": 0, "reasons": [], "scoped_verdict": None},
        }
        monkeypatch.setattr(oracle_replay, "run_static_calls", lambda *a, **k: (fake, [1]))
        with pc.all_safe_static_verdicts():
            per_op, not_planned = oracle_replay.run_static_calls()
        assert not_planned == [1]
        assert {o: e["verdict"] for o, e in per_op.items()} == {"op_0": "safe", "op_1": "safe"}
        assert per_op["op_0"]["n_findings"] == 2
        assert per_op["op_0"]["scoped_verdict"] == "unknown"
        assert per_op["op_1"]["scoped_verdict"] is None

    def test_bth_results_path_unset_during_arm_and_restored(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BTH_RESULTS_PATH", "/nonexistent/x.json")
        with pc._without_bth_results_path():
            assert "BTH_RESULTS_PATH" not in pc.os.environ
        assert pc.os.environ["BTH_RESULTS_PATH"] == "/nonexistent/x.json"


class TestControlArm:
    def test_all_safe_arm_counts_runtime_raise_unsound_real_arm_does_not(self, raising_run: Path) -> None:
        real = json.loads((raising_run / pc.REAL_REPORT_NAME).read_text())
        all_safe = json.loads((raising_run / pc.ALL_SAFE_REPORT_NAME).read_text())
        assert real["summary_flat"]["unsound"] == 0
        assert all_safe["summary_flat"]["unsound"] >= 1
        assert pc.runtime_raised_ops(all_safe) >= 1
        assert all_safe["summary_flat"]["unsound"] >= pc.runtime_raised_ops(all_safe)
        # Every executed op carries the forced verdict in the control arm.
        for row in all_safe["rows"]:
            assert set(row["static"].values()) <= {"safe"}
        # Same runtime, same denominators on both arms.
        for key in ("rows_executed", "rows_setup_error", "operations_executed"):
            assert real["summary_flat"][key] == all_safe["summary_flat"][key]

    def test_control_fires_true_on_raising_row(self, raising_run: Path) -> None:
        result = json.loads((raising_run / pc.RESULT_NAME).read_text())
        assert result["control_fires"] is True
        assert result["all_safe_unsound"] >= result["runtime_raised_ops_all_safe_arm"] >= 1
        assert result["real_unsound"] == 0

    def test_control_fires_false_when_all_safe_unsound_is_zero(self, clean_run: Path) -> None:
        result = json.loads((clean_run / pc.RESULT_NAME).read_text())
        assert result["all_safe_unsound"] == 0
        assert result["runtime_raised_ops_all_safe_arm"] == 0
        assert result["control_fires"] is False

    def test_build_result_control_fires_boundaries(self) -> None:
        def report(unsound: int, raised: int) -> dict:
            return {
                "summary_flat": {
                    "rows_executed": 1, "rows_setup_error": 0, "operations_executed": 2,
                    "unsound": unsound, "unsound_scoped": 0, "totality_violations": 0,
                    "check_graph_exceptions": 0, "n_operations_scope_verdict_safe": 0,
                    "unknown_rate": 1.0, "crosscheck_agreement": 0.0,
                },
                "agreement_matrix": {"ran_ok": {"safe": 3}, "raised:ValueError": {"safe": raised}},
            }

        real = report(0, 1)
        assert pc.build_result(real, report(0, 0))["control_fires"] is False
        assert pc.build_result(real, report(0, 1))["control_fires"] is False  # raised but not counted
        assert pc.build_result(real, report(1, 2))["control_fires"] is False  # counts fewer than raised
        assert pc.build_result(real, report(2, 2))["control_fires"] is True
        assert pc.build_result(real, report(3, 2))["control_fires"] is True


class TestResultSchema:
    def test_module_schema_matches_sidecar_toml(self) -> None:
        with SIDECAR_TOML.open("rb") as f:
            schema = tomllib.load(f)["result_schema"]
        names = {"bool": bool, "int": int, "float": float}
        assert {k: names[v] for k, v in schema.items()} == pc.RESULT_SCHEMA

    def test_result_json_keys_and_types_match_sidecar(self, raising_run: Path) -> None:
        with SIDECAR_TOML.open("rb") as f:
            schema = tomllib.load(f)["result_schema"]
        result = json.loads((raising_run / pc.RESULT_NAME).read_text())
        assert set(result) == set(schema)
        for key, type_name in schema.items():
            value = result[key]
            if type_name == "bool":
                assert isinstance(value, bool), key
            elif type_name == "int":
                assert isinstance(value, int) and not isinstance(value, bool), key
            else:
                assert type_name == "float"
                assert isinstance(value, float), key

    def test_single_arm_writes_no_result_json(self, tmp_path: Path) -> None:
        rc, out_dir = _run(tmp_path, [_OK_ROW], arm="real")
        assert rc == 0
        assert (out_dir / pc.REAL_REPORT_NAME).is_file()
        assert not (out_dir / pc.ALL_SAFE_REPORT_NAME).exists()
        assert not (out_dir / pc.RESULT_NAME).exists()

    def test_missing_input_is_an_error_not_an_empty_report(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            pc.main(["--corpus", str(tmp_path / "nope.jsonl"), "--out-dir", str(tmp_path / "o")])
