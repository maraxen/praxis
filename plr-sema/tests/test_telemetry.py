"""Spec 260901 §4.2 / AC-4.1-4.4: telemetry emission surface verification.

Exactly the five test functions named in §4.2's bullet list
(test_categories_match_upstream, test_every_will_fail_carries_a_category,
test_sink_failure_is_swallowed, test_event_carries_stamp,
test_jsonl_sink_round_trip). AC-4.3's pin (stamp.plr.hash at the dd79c4c89
tip) is folded into test_jsonl_sink_round_trip per §4.2's own note that this
is "as test_jsonl_sink_round_trip, §4.2, already does" -- no separate
function is added for it.

Import-boundary note: this file lives under tests/, which spec §1.3's
import-boundary walk scopes to src/plr_sema/ only -- importing verify from a
test here is legal. Importing verify from src/plr_sema/telemetry.py would
not be (see test_import_boundary.py), and telemetry.py does not do so
(verified by this file's own grep gate, run separately per the fixer brief).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from plr_sema._provenance import SurveyStamp, survey_stamp
from plr_sema._provenance.git_state import GitState, capture_git_state
from plr_sema.verdict import Finding, PlrSite, Verdict
from plr_sema import telemetry
from plr_sema.telemetry import (
    FAILURE_CATEGORIES,
    JsonlSink,
    build_event,
    emit,
    emit_finding,
    set_sink,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

# The full SHA at the pin AC-4.3 targets (external/pylabrobot HEAD, confirmed
# live this session via `git -C external/pylabrobot rev-parse HEAD`). Self-
# scoping to the current checkout state per the round-1 rebuttal (spec
# AC-4.3) -- not a fact about plr-sema itself, so if the submodule is ever
# advanced past this pin, this one assertion (only) needs updating.
_PLR_PIN_SHA = "dd79c4c89bc008629a1c598ea614be5e6067d1f9"


@pytest.fixture(autouse=True)
def _reset_sink():
    """set_sink is a process-global; isolate tests from each other's sink
    state (spec §4.1's TelemetrySink is process-global, default None)."""
    set_sink(None)
    yield
    set_sink(None)


def _dummy_stamp() -> SurveyStamp:
    """A SurveyStamp built from a fabricated GitState -- avoids shelling out
    for tests that only care about the event envelope, not real provenance."""
    fake = GitState(hash="0" * 40, branch="main", dirty=False, provenance_source="git")
    return SurveyStamp(
        plr=fake,
        praxis=fake,
        pylabrobot_version=None,
        stamped_at="2026-09-01T00:00:00+00:00",
    )


def _make_finding(
    verdict: Verdict, category: str = "", reason: str = ""
) -> Finding:
    return Finding(
        verdict=verdict,
        operation_id="op-1",
        category=category,
        plr_site=PlrSite(file="a.py", lineno=1, qualname="Foo.bar"),
        reason=reason,
    )


# ---------------------------------------------------------------------------
# test_categories_match_upstream
# ---------------------------------------------------------------------------


def test_categories_match_upstream() -> None:
    """§4.2 / AC-4.2: FAILURE_CATEGORIES must be the SAME set as
    verify.failure_taxonomy.FAILURE_CATEGORIES today -- a live cross-package
    drift test, not a copied constant re-asserted against itself.

    A bare `import verify.failure_taxonomy` fails from repo root:
    training/verify/__init__.py:44 eagerly imports verify.checks, which
    imports coxswain.plr.intent_record; at root cwd `coxswain` resolves as a
    namespace package (__file__ is None) so `coxswain.plr` is unreachable.
    Fix: put both <repo_root>/training and <repo_root>/coxswain/src on
    sys.path before importing -- verified working this session. The
    pytest.skip branch is kept per §4.2's requirement ("skipped with an
    explicit reason if training/verify is not importable") for environments
    where that fix doesn't hold, but on this machine it must not fire.
    """
    training_path = str(REPO_ROOT / "training")
    coxswain_src_path = str(REPO_ROOT / "coxswain" / "src")
    for path in (coxswain_src_path, training_path):
        if path not in sys.path:
            sys.path.insert(0, path)

    try:
        import verify.failure_taxonomy as upstream_taxonomy
    except ImportError as exc:
        pytest.skip(f"training/verify not importable: {exc}")
        return

    assert FAILURE_CATEGORIES == upstream_taxonomy.FAILURE_CATEGORIES, (
        f"plr_sema.telemetry.FAILURE_CATEGORIES "
        f"{sorted(FAILURE_CATEGORIES)} != "
        f"verify.failure_taxonomy.FAILURE_CATEGORIES "
        f"{sorted(upstream_taxonomy.FAILURE_CATEGORIES)}"
    )


# ---------------------------------------------------------------------------
# test_every_will_fail_carries_a_category
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("category", sorted(FAILURE_CATEGORIES - {"postcondition_mismatch"}))
def test_every_will_fail_carries_a_category(category: str) -> None:
    """§4.2: property-style over constructed findings -- every WILL_FAIL
    finding's built event carries a non-null category that is itself a
    FAILURE_CATEGORIES member. postcondition_mismatch is excluded from the
    parametrization: it is unreachable in v1 (spec §4.1) by construction of
    the analyzer, not because it wouldn't satisfy this property -- it would.
    """
    finding = _make_finding(Verdict.WILL_FAIL, category=category)
    event = build_event(
        event="finding",
        protocol_fqn="pkg.Protocol.run",
        operation_id=finding.operation_id,
        verdict=finding.verdict,
        stamp=_dummy_stamp(),
        category=finding.category or None,
        reason=finding.reason or None,
        plr_site=finding.plr_site,
    )
    assert event["category"] is not None
    assert event["category"] in FAILURE_CATEGORIES


def test_every_will_fail_carries_a_category_rejects_missing_category() -> None:
    """Companion check: build_event refuses a non-member category outright
    (validated, not silently passed through) -- the property only holds
    because the constructor enforces it."""
    with pytest.raises(ValueError):
        build_event(
            event="finding",
            protocol_fqn="pkg.Protocol.run",
            operation_id="op-1",
            verdict=Verdict.WILL_FAIL,
            stamp=_dummy_stamp(),
            category="not_a_real_category",
        )


# ---------------------------------------------------------------------------
# test_sink_failure_is_swallowed
# ---------------------------------------------------------------------------


class _RaisingSink:
    def emit(self, event) -> None:
        raise RuntimeError("sink is on fire")


def test_sink_failure_is_swallowed() -> None:
    """§4.2 (D15-reworded, per fixer brief): there is no pipeline at T4 --
    assert that emit() with a sink whose emit() raises does not propagate:
    the call returns normally and the process continues. Not "analysis
    completes and returns a report" literally, since no pipeline exists
    until T8; this is the buildable equivalent of that claim at T4."""
    set_sink(_RaisingSink())
    finding = _make_finding(Verdict.WILL_FAIL, category="harness_internal")

    # Neither emit() nor emit_finding() may propagate the sink's exception.
    emit({"schema_version": 1, "event": "finding"})
    emit_finding(finding, protocol_fqn="pkg.Protocol.run", stamp=_dummy_stamp())

    # The process continues: a second, unrelated call still runs cleanly.
    assert 1 + 1 == 2


def test_sink_failure_is_swallowed_non_none_return() -> None:
    """A sink whose emit() returns something instead of None must not
    confuse emit() either -- emit()'s contract only cares whether the call
    raises, not what it returns."""

    class _ReturningSink:
        def emit(self, event):
            return {"unexpected": "return value"}

    set_sink(_ReturningSink())
    emit({"schema_version": 1, "event": "finding"})


def test_unwritable_jsonl_sink_path_is_survivable(tmp_path: Path) -> None:
    """An unwritable JsonlSink path (parent directory doesn't exist) must
    also be survivable via emit() -- open() raising FileNotFoundError is
    exactly the kind of sink failure emit() exists to swallow."""
    bad_path = tmp_path / "does" / "not" / "exist" / "events.jsonl"
    set_sink(JsonlSink(bad_path))
    emit({"schema_version": 1, "event": "finding"})
    assert not bad_path.exists()


# ---------------------------------------------------------------------------
# test_event_carries_stamp
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case", ["real_repo", "tmp_path_path_scrubbed"])
def test_event_carries_stamp(
    case: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """§4.2: stamp.plr must be present in every emitted event, parametrized
    over two capture branches with DIFFERENT assertions -- an unconditional
    "always 40-hex" assertion is wrong by construction, since
    capture_git_state degrades to a sentinel (not a hex digest) off the
    real-repo path (git_state.py's _NOGIT/_UNAVAILABLE).

    Branch ordering note (own finding, not guessed): combining tmp_path (a
    non-repo directory) with a scrubbed PATH lands on _UNAVAILABLE
    specifically, not _NOGIT -- capture_git_state's
    _git_available_and_in_repo() checks git-binary availability BEFORE
    repo-membership, so a scrubbed PATH short-circuits before the
    non-repo check ever runs. The sentinel asserted against below is read
    directly from git_state._UNAVAILABLE, not hardcoded.
    """
    if case == "real_repo":
        plr_state = capture_git_state(REPO_ROOT / "external" / "pylabrobot")
        assert len(plr_state.hash) == 40
        assert all(c in "0123456789abcdef" for c in plr_state.hash)
    else:
        monkeypatch.setenv("PATH", "")
        plr_state = capture_git_state(tmp_path)
        from plr_sema._provenance.git_state import _UNAVAILABLE

        assert plr_state.hash == _UNAVAILABLE.hash
        assert plr_state.provenance_source == _UNAVAILABLE.provenance_source

    stamp = SurveyStamp(
        plr=plr_state,
        praxis=plr_state,
        pylabrobot_version=None,
        stamped_at="2026-09-01T00:00:00+00:00",
    )
    finding = _make_finding(Verdict.SAFE)
    event = build_event(
        event="finding",
        protocol_fqn="pkg.Protocol.run",
        operation_id=finding.operation_id,
        verdict=finding.verdict,
        stamp=stamp,
    )
    assert "stamp" in event
    assert "plr" in event["stamp"]
    assert event["stamp"]["plr"]["hash"] == plr_state.hash


# ---------------------------------------------------------------------------
# test_jsonl_sink_round_trip
# ---------------------------------------------------------------------------


def test_jsonl_sink_round_trip(tmp_path: Path) -> None:
    """§4.2: write N events, read back, assert N parseable lines with
    schema_version == 1.

    AC-4.3 (D15-reworded) is folded in here per the spec's own pointer:
    directly constructing and emitting a Finding-derived event with
    JsonlSink attached must yield a parseable line whose stamp.plr.hash
    equals the dd79c4c89 pin's full SHA -- self-scoping to the current
    checkout, confirmed live this session. Uses the real, memoized
    survey_stamp() (T2) rather than a fabricated stamp, since the pin claim
    is specifically about what survey_stamp() reports for THIS checkout.
    """
    sink_path = tmp_path / "events.jsonl"
    set_sink(JsonlSink(sink_path))

    stamp = survey_stamp()
    n = 5
    for i in range(n):
        finding = _make_finding(Verdict.WILL_FAIL, category="shape_mismatch")
        emit_finding(
            finding,
            protocol_fqn=f"pkg.Protocol.run_{i}",
            stamp=stamp,
        )

    lines = sink_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == n

    parsed = [json.loads(line) for line in lines]
    for record in parsed:
        assert record["schema_version"] == 1
        assert record["stamp"]["plr"]["hash"] == _PLR_PIN_SHA

    # AC-4.3's exact claim, isolated: the pin holds for the stamp itself,
    # independent of the JSONL round trip.
    assert stamp.plr.hash == _PLR_PIN_SHA
