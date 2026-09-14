"""#4982 D2 (sprint 127 band D): `plr-sema/eval/tips_dirty_cost.py`'s
measurement-only ``_no_tips_dirty`` switch.

Two fast, synthetic cases over already-committed volume graph fixtures
(``tests/fixtures/volume_{retip,top}_graph.json``, both already exercised
by `test_check_graph.py`'s AC-14.5 tests):

* ``volume_retip`` -- the round-1 O4 counterexample (`test_check_graph.py::
  test_ac_14_5_e_retip_dirty_tip_never_safe`): disabling `tips_dirty`
  MUST flip the final dispense's tip-side finding from `UNKNOWN`/
  `volume_state_unknown` to a DEFINITE verdict -- empirically `WILL_FAIL`
  here (the second tip really is fresh, so crediting it with `[0, 0]`
  correctly predicts the real `TooLittleLiquidError`; see the test's own
  docstring for why the shipped rule stays fail-closed regardless: it
  also guards a case, not exercised by this fixture, where `tips_dirty`
  was set by an UNMODELLED tip movement rather than a real pickup). This
  is the "costs something" half -- the polarity of the recovered verdict
  is incidental, the loss of ANY definite verdict is what V5 pays for.
* ``volume_top`` -- the amount-unresolved case (`test_check_graph.py::
  test_ac_14_5_c_top_amount_yields_unknown`): the dispense's own `vols`
  lowers to Top, so V0 pairing fails regardless of any interval state:
  disabling `tips_dirty` must NOT change this finding at all (identical
  reason AND verdict) -- unknown for a reason that has nothing to do with
  tip lifecycle, the "still unknown, unseeded/unresolved" half the D2
  report's `n_still_unknown_unseeded` bucket counts.

Both use `plr_sema.check.check_graph` directly (not `check_ir`) -- the
same late-bound `volumestate.VolumeWalk()` construction the monkeypatch
targets, reached identically whether the caller is `check_graph`,
`check_ir`, or `tips_dirty_cost.py`'s own tier-1/tier-2b paths.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PLR_SEMA_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PLR_SEMA_ROOT.parent

sys.path.insert(0, str(REPO_ROOT / "plr-sema" / "eval"))

from tips_dirty_cost import _no_tips_dirty  # noqa: E402

from plr_sema.check import check_graph  # noqa: E402
from plr_sema.verdict import PlrSite, Verdict  # noqa: E402

CONTRACTS_JSON = (PLR_SEMA_ROOT / "data" / "derived_contracts.json").read_text(encoding="utf-8")
_DOES_VOLUME_TRACKING_ENV = frozenset({"does_volume_tracking"})

#: The tip-side `remove_liquid` bridge site both AC-14.5 tests in
#: `test_check_graph.py` key off (`_REMOVE_LIQUID_SITE` there) -- an op
#: also carries many unrelated `guard_predicate_unparsed` findings (every
#: OTHER guard on the same `dispense`/`aspirate` call), so filtering by
#: `operation_id` alone is not enough; this site plus `reason ==
#: "volume_state_unknown"` isolates the ONE volume-family finding V5's
#: tip lifecycle can move.
_REMOVE_LIQUID_SITE = PlrSite(
    file="external/pylabrobot/pylabrobot/resources/volume_tracker.py",
    lineno=92,
    qualname="VolumeTracker.remove_liquid",
)


def _volume_graph(name: str) -> str:
    return (PLR_SEMA_ROOT / "tests" / "fixtures" / f"{name}_graph.json").read_text(encoding="utf-8")


def _findings_at(report, operation_id: str) -> list:
    """The tip-side `remove_liquid` finding(s) at ``operation_id`` --
    NOT every finding at that op (a `dispense`/`aspirate` carries many
    unrelated guards too, see `_REMOVE_LIQUID_SITE`'s docstring)."""
    return [
        f for f in report.findings
        if f.operation_id == operation_id and f.plr_site == _REMOVE_LIQUID_SITE
    ]


class TestNoTipsDirtyFlipsARealFinding:
    """The "costs something" case: `volume_retip`'s final dispense."""

    def test_shipped_is_unknown_volume_state_unknown(self) -> None:
        report = check_graph(_volume_graph("volume_retip"), CONTRACTS_JSON, env=_DOES_VOLUME_TRACKING_ENV)
        findings = _findings_at(report, "op_7")
        assert len(findings) == 1
        assert findings[0].verdict is Verdict.UNKNOWN
        assert findings[0].reason == "volume_state_unknown"

    def test_no_tips_dirty_turns_it_definite(self) -> None:
        """Empirically `WILL_FAIL`, not `SAFE`: with the gate removed,
        `pickup` always credits the second `pick_up_tips` with `[0, 0]`
        (a genuinely fresh tip really does start empty), so the guard
        evaluates "remove 50 from a definitely-empty tip" and correctly
        predicts the real `TooLittleLiquidError` -- this fixture's tip
        really is fresh. The COST tips_dirty pays is real regardless of
        which definite polarity comes back: shipped, this op says
        NOTHING (`UNKNOWN`); with the rule off, it says something
        DEFINITE. The rule stays fail-closed because `tips_dirty` can
        also be set by an UNMODELLED tip movement this fixture does not
        exercise (`_is_unmodelled_tip_movement`), where crediting `[0, 0]`
        would not be grounded in a real `pick_up_tips` at all.
        """
        with _no_tips_dirty():
            report = check_graph(_volume_graph("volume_retip"), CONTRACTS_JSON, env=_DOES_VOLUME_TRACKING_ENV)
        findings = _findings_at(report, "op_7")
        assert len(findings) == 1
        assert findings[0].verdict is Verdict.WILL_FAIL, (
            f"expected a DEFINITE verdict once tips_dirty is disabled, got {findings[0]!r}"
        )

    def test_patch_is_scoped_and_reverts(self) -> None:
        """The monkeypatch must not leak past its own `with` block --
        the SAME graph checked immediately after must reproduce the
        shipped (UNKNOWN) verdict, not the patched one."""
        with _no_tips_dirty():
            patched = check_graph(_volume_graph("volume_retip"), CONTRACTS_JSON, env=_DOES_VOLUME_TRACKING_ENV)
        after = check_graph(_volume_graph("volume_retip"), CONTRACTS_JSON, env=_DOES_VOLUME_TRACKING_ENV)

        assert _findings_at(patched, "op_7")[0].verdict is Verdict.WILL_FAIL
        after_finding = _findings_at(after, "op_7")[0]
        assert after_finding.verdict is Verdict.UNKNOWN
        assert after_finding.reason == "volume_state_unknown"


class TestNoTipsDirtyLeavesUnrelatedUnknownsAlone:
    """The "still unknown, unseeded/unresolved" case: `volume_top`'s
    dispense, whose UNKNOWN comes from an unresolved amount (V0 pairing
    fails outright), never from `tips_dirty`."""

    def test_shipped_and_no_tips_dirty_agree(self) -> None:
        shipped = check_graph(_volume_graph("volume_top"), CONTRACTS_JSON, env=_DOES_VOLUME_TRACKING_ENV)
        with _no_tips_dirty():
            nodirty = check_graph(_volume_graph("volume_top"), CONTRACTS_JSON, env=_DOES_VOLUME_TRACKING_ENV)

        shipped_findings = _findings_at(shipped, "op_5")
        nodirty_findings = _findings_at(nodirty, "op_5")
        assert len(shipped_findings) == 1
        assert len(nodirty_findings) == 1
        assert shipped_findings[0].verdict is Verdict.UNKNOWN
        assert shipped_findings[0].reason == "volume_state_unknown"
        # Identical outcome -- this UNKNOWN has nothing to do with tips_dirty.
        assert nodirty_findings[0].verdict == shipped_findings[0].verdict
        assert nodirty_findings[0].reason == shipped_findings[0].reason


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
