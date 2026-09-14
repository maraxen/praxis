"""Failure-category classification for execution-verify (260828 finding)."""

from __future__ import annotations

import json

import pytest
from pylabrobot.pumps.errors import NotCalibratedError
from pylabrobot.resources.errors import NoTipError

from verify import failure_taxonomy
from verify.dispatcher import DispatchError, UnsupportedCallError
from verify.failure_taxonomy import (
    FAILURE_CATEGORIES,
    POSTCONDITION_MISMATCH,
    TaxonomyArtifactError,
    _load_taxonomy_artifact,
    _plr_exception_class_names,
    _TAXONOMY_PATH,
    classify_check_failure,
    classify_exception,
    plr_exception_taxonomy_git_sha,
)
from verify.grounding import GroundingError


def test_unsupported_call_error_classifies_as_unsupported_tool():
    assert classify_exception(UnsupportedCallError("nope")) == "unsupported_tool"


def test_grounding_error_classifies_as_ungroundable_reference():
    assert classify_exception(GroundingError("bad ref")) == "ungroundable_reference"


def test_bare_dispatch_error_classifies_as_shape_mismatch():
    assert classify_exception(DispatchError("volume list len 3 != 2 targets")) == "shape_mismatch"


def test_unsupported_call_error_not_misclassified_as_shape_mismatch():
    # UnsupportedCallError IS a DispatchError subclass -- the more specific
    # check must win, or every unsupported-tool case would be misfiled.
    exc = UnsupportedCallError("tool has no LH path")
    assert isinstance(exc, DispatchError)
    assert classify_exception(exc) == "unsupported_tool"


def test_real_plr_exception_classifies_as_precondition_state():
    assert classify_exception(NoTipError("Channel 1 does not have a tip.")) == "precondition_state"


def test_unrecognized_exception_classifies_as_harness_internal():
    assert classify_exception(TypeError("unexpected")) == "harness_internal"
    assert classify_exception(RuntimeError("plain runtime error, not ours")) == "harness_internal"


def test_absorbed_plr_exception_in_execution_ok_check_classifies_as_precondition_state():
    # This is the REAL shape verifier.verify() produces: the live exception
    # is absorbed internally and only its formatted string survives in the
    # "execution_ok" check's detail (260828 finding -- a first version of
    # this taxonomy missed this path entirely and misclassified every
    # absorbed PLR exception as postcondition_mismatch).
    checks = [
        {"name": "execution_ok", "passed": False,
         "detail": "execution failed: NoTipError: Channel 1 does not have a tip."},
        {"name": "volumes_delta", "passed": True, "detail": "ok"},
    ]
    assert classify_check_failure(checks) == "precondition_state"


def test_absorbed_dispatch_error_in_execution_ok_check_classifies_as_shape_mismatch():
    checks = [
        {"name": "execution_ok", "passed": False,
         "detail": "execution failed: DispatchError: volume list len 3 != 2 targets"},
    ]
    assert classify_check_failure(checks) == "shape_mismatch"


def test_genuine_postcondition_failure_with_execution_ok_passing():
    checks = [
        {"name": "execution_ok", "passed": True, "detail": "execution completed without error"},
        {"name": "volumes_delta", "passed": False, "detail": "expected -100.0uL, got -50.0uL"},
    ]
    assert classify_check_failure(checks) == POSTCONDITION_MISMATCH


def test_unrecognized_absorbed_exception_name_classifies_as_harness_internal():
    checks = [
        {"name": "execution_ok", "passed": False,
         "detail": "execution failed: SomeBrandNewPLRException: unseen before"},
    ]
    assert classify_check_failure(checks) == "harness_internal"


def test_categories_are_closed_and_include_postcondition_mismatch():
    assert POSTCONDITION_MISMATCH in FAILURE_CATEGORIES
    assert FAILURE_CATEGORIES == {
        "unsupported_tool",
        "ungroundable_reference",
        "shape_mismatch",
        "precondition_state",
        "harness_internal",
        "postcondition_mismatch",
    }


# --- T7: artifact-derived exception-name table (260901) --------------------
#
# `_plr_exception_class_names()` used to introspect exactly two hand-typed
# modules (`pylabrobot.liquid_handling.errors`, `pylabrobot.resources.errors`)
# via `inspect.getmembers`, covering only 11 of PLR's 132 real exception
# classes. It now loads `training/verify/data/plr_exception_taxonomy.json`
# (AST-derived across all 502 vendored PLR source files) instead.


def test_plr_exception_class_names_now_covers_full_ast_survey():
    # NotCalibratedError (pylabrobot.pumps.errors) was invisible to the old
    # two-module allowlist -- it lives in neither
    # pylabrobot.liquid_handling.errors nor pylabrobot.resources.errors.
    names = _plr_exception_class_names()
    assert len(names) > 100  # was 11 before T7; artifact currently has 132
    assert "NotCalibratedError" in names
    # Still covers the pre-existing two-module set -- no regression.
    assert "NoTipError" in names


def test_previously_invisible_plr_exception_now_classifies_as_precondition_state():
    # Concrete before/after: NotCalibratedError absorbed into an
    # "execution_ok" check detail used to fall through to harness_internal
    # (outside the old two-module allowlist); it now correctly resolves to
    # precondition_state via the full AST-derived survey.
    checks = [
        {"name": "execution_ok", "passed": False,
         "detail": "execution failed: NotCalibratedError: pump not calibrated"},
    ]
    assert classify_check_failure(checks) == "precondition_state"


def test_classify_exception_dispatch_is_unaffected_by_artifact_change():
    # classify_exception() dispatches on module-prefix match
    # (module.startswith("pylabrobot.")) and never consults
    # _plr_exception_class_names() at all -- a class outside the old
    # two-module allowlist must classify identically to one inside it.
    assert classify_exception(NotCalibratedError("not calibrated")) == "precondition_state"
    assert classify_exception(NoTipError("no tip")) == "precondition_state"


def test_plr_exception_class_names_matches_artifact_class_count():
    with _TAXONOMY_PATH.open() as fh:
        artifact = json.load(fh)
    assert _plr_exception_class_names() == frozenset(c["name"] for c in artifact["classes"])


def test_plr_exception_taxonomy_git_sha_matches_artifact_stamp():
    with _TAXONOMY_PATH.open() as fh:
        artifact = json.load(fh)
    assert plr_exception_taxonomy_git_sha() == artifact["version"]["git_sha"]
    assert plr_exception_taxonomy_git_sha()  # non-empty


@pytest.fixture
def _clear_taxonomy_cache():
    """Reset the module-level lru_cache memos around artifact-tampering
    tests so earlier/later tests never observe a monkeypatched load."""
    _load_taxonomy_artifact.cache_clear()
    _plr_exception_class_names.cache_clear()
    yield
    _load_taxonomy_artifact.cache_clear()
    _plr_exception_class_names.cache_clear()


def test_missing_taxonomy_artifact_raises_named_error(tmp_path, monkeypatch, _clear_taxonomy_cache):
    monkeypatch.setattr(failure_taxonomy, "_TAXONOMY_PATH", tmp_path / "does_not_exist.json")
    with pytest.raises(TaxonomyArtifactError):
        _load_taxonomy_artifact()


def test_taxonomy_artifact_missing_classes_raises_not_silently_empty(
    tmp_path, monkeypatch, _clear_taxonomy_cache
):
    bad = tmp_path / "malformed.json"
    bad.write_text(json.dumps({"version": {"git_sha": "deadbeef" * 5}, "classes": []}))
    monkeypatch.setattr(failure_taxonomy, "_TAXONOMY_PATH", bad)
    # Must raise, not silently degrade to an empty frozenset (that would be
    # a WORSE regression of the exact bug T7 fixes: 0 names instead of 11).
    with pytest.raises(TaxonomyArtifactError):
        _plr_exception_class_names()


def test_taxonomy_artifact_missing_git_sha_raises(tmp_path, monkeypatch, _clear_taxonomy_cache):
    bad = tmp_path / "unstamped.json"
    bad.write_text(json.dumps({"version": {"git_sha": ""}, "classes": [{"name": "X"}]}))
    monkeypatch.setattr(failure_taxonomy, "_TAXONOMY_PATH", bad)
    with pytest.raises(TaxonomyArtifactError):
        _load_taxonomy_artifact()


def test_taxonomy_artifact_invalid_json_raises(tmp_path, monkeypatch, _clear_taxonomy_cache):
    bad = tmp_path / "invalid.json"
    bad.write_text("{not valid json")
    monkeypatch.setattr(failure_taxonomy, "_TAXONOMY_PATH", bad)
    with pytest.raises(TaxonomyArtifactError):
        _load_taxonomy_artifact()
