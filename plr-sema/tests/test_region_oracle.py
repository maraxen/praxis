"""Tests for backlog #4948: real `OperationNode.line_number` values.

`region_oracle.py`'s `(method_name, lineno)` join no longer needs
`_join_key`'s old constant-`0` normalization. Mirrors
`plr-sema/tests/test_tier2.py`'s own `TestOperationIterationJoin`
/ `TestSmallestForFixtureEndToEnd` patterns (in-process, `sys.path`-spliced
imports of the `eval/` scripts) but is kept in its own file: `test_tier2.py`
is owned by a concurrent fixer (#4949) for unrelated reasons, and this
file is scoped exactly to the `two_sites_same_method.py` fixture and the
`_join_key` identity change.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = REPO_ROOT / "plr-sema" / "eval"
FIXTURES_DIR = EVAL_DIR / "fixtures" / "regions"

sys.path.insert(0, str(EVAL_DIR))

import region_oracle  # noqa: E402
from oracle_common import DEFAULT_CONTRACTS, param_names_from_contracts  # noqa: E402
from region_recorder import DuplicateCallSiteError  # noqa: E402

SRC_ROOT = REPO_ROOT / "plr-sema" / "src"
sys.path.insert(0, str(SRC_ROOT))
from plr_sema import check as _check_mod  # noqa: E402
from plr_sema.check import ir as _ir  # noqa: E402
from plr_sema.check._supported_tools import SUPPORTED_TOOLS  # noqa: E402
from plr_sema.verdict import Verdict, join  # noqa: E402

_PARAM_NAMES = param_names_from_contracts(DEFAULT_CONTRACTS.read_text(encoding="utf-8"))
_FIXTURE = FIXTURES_DIR / "two_sites_same_method.py"


def test_fixture_exists() -> None:
    assert _FIXTURE.is_file(), f"missing fixture: {_FIXTURE}"


class TestJoinKeyIsIdentity:
    """`_join_key` must now be a pure pass-through.

    It used to force every lineno to `0`.
    """

    def test_join_key_returns_real_lineno_unchanged(self) -> None:
        assert region_oracle._join_key("pick_up_tips", 5) == ("pick_up_tips", 5)
        assert region_oracle._join_key("aspirate", 42) == ("aspirate", 42)


class TestTwoSitesSameMethodJoinMap:
    """The static join map distinguishes the two `pick_up_tips` call sites.

    By their (now real) line numbers -- one at the function's own top
    level, one inside the `for`-loop body.
    """

    def test_join_map_has_two_distinct_pick_up_tips_entries(self, tmp_path) -> None:
        contracts_json = DEFAULT_CONTRACTS.read_text(encoding="utf-8")
        contracts_payload = json.loads(contracts_json)

        payload = region_oracle._extract_graph_payload(
            _FIXTURE, cache_dir=tmp_path, runner_python=sys.executable,
        )
        # Two `pick_up_tips` operations in the RAW payload, at two
        # different lines -- proves the extractor itself (backlog #4948)
        # gives them distinct, non-zero line numbers before the join is
        # even built.
        pickup_ops = [op for op in payload["operations"] if op["method_name"] == "pick_up_tips"]
        assert len(pickup_ops) == 2
        lines = {op["line_number"] for op in pickup_ops}
        assert len(lines) == 2, f"expected two distinct lines, got {lines}"
        assert 0 not in lines

        _bytecode, _findings, join_map, _static, _proved_trips = region_oracle._static_report(
            payload, contracts_payload, _PARAM_NAMES, _ir, _check_mod,
        )

        pickup_keys = [key for key in join_map if key[0] == "pick_up_tips"]
        assert len(pickup_keys) == 2, f"expected two distinct join keys, got {pickup_keys}"
        # Different keys must map to different operation ids -- the join
        # actually distinguishes the two call sites, not just tolerates
        # two keys that happen to collapse to the same target.
        op_ids = {join_map[key] for key in pickup_keys}
        assert len(op_ids) == 2

    def test_no_duplicate_call_site_error(self, tmp_path) -> None:
        """The two `pick_up_tips` sites must not collide.

        Before #4948, both would have normalized to the SAME
        `(method, 0)` key and raised `DuplicateCallSiteError` here.
        """
        contracts_json = DEFAULT_CONTRACTS.read_text(encoding="utf-8")
        contracts_payload = json.loads(contracts_json)
        payload = region_oracle._extract_graph_payload(
            _FIXTURE, cache_dir=tmp_path, runner_python=sys.executable,
        )
        try:
            region_oracle._static_report(
                payload, contracts_payload, _PARAM_NAMES, _ir, _check_mod,
            )
        except DuplicateCallSiteError as e:  # pragma: no cover - failure path
            msg = f"join collapsed two distinct call sites onto one key: {e}"
            raise AssertionError(msg) from e


class TestTwoSitesSameMethodEndToEnd:
    """`region_oracle.run_fixture` end to end (chatterbox, no hardware).

    The top-level `pick_up_tips` runs clean; the for-loop's own
    `pick_up_tips` (no `drop_tips` in between) raises HasTipError, and the
    static side calls it at the SAME (now-distinguished) key -- zero
    unsound rows.
    """

    def test_second_site_raises_and_is_will_fail_at_its_own_key(self, tmp_path) -> None:
        contracts_json = DEFAULT_CONTRACTS.read_text(encoding="utf-8")
        contracts_payload = json.loads(contracts_json)

        outcome = region_oracle.run_fixture(
            _FIXTURE,
            contracts_payload=contracts_payload,
            param_names=_PARAM_NAMES,
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
        assert outcome.unsound_rows == [], outcome.unsound_rows
