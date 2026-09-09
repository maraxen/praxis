"""Systematic classification of execution-verify failures (P2.2 harness).

Both ``floor_gen.exec_verify`` and ``overlay_gen.exec_verify`` already catch
every exception a call sequence can raise and format it as a free-text
``f"{type(exc).__name__}: {exc}"`` string. That string already carries the
raising exception's real class name -- this module turns that into a small,
CLOSED set of semantic categories, classified structurally by exception
TYPE/MODULE (never by parsing message TEXT -- same "table decides kind, not
stringiness" discipline as ``coxswain.plr.slot_derivation``'s D11 rule).

Why categories, not a flat rejection count (260828 finding): running
floor_gen/overlay_gen at real scale for the first time surfaced that a flat
"rejected_execution" count conflates several structurally different signals:

* a REAL bug in our own harness/synth code (``shape_mismatch``) -- should
  trend toward zero; any nonzero count here after a bug-fixing pass is a
  strong signal something in OUR code is still wrong.
* a mined/generated call referencing something that doesn't exist on the
  deck at all (``ungroundable_reference``) -- usually a miner/synth
  reference-construction bug, occasionally a genuinely bad teacher value.
* a call that is well-formed and correctly grounded, but the harness's
  SYNTHESIZED, single-call (or short-prefix) setup didn't establish the
  physical/deck STATE the real call sequence assumes (``precondition_state``,
  e.g. ``NoTipError`` on a call that needs more channels than the synthetic
  prefix armed) -- tells us about a structural limitation of ISOLATED-call
  verification, not a defect in the mined/generated call itself.
* a call that ran to completion without raising, but our own post-condition
  checks (tip/volume-delta) caught a real semantic mismatch between what the
  call claims and what actually happened (``postcondition_mismatch``) --
  the highest-value category for catching real generation defects.
* a tool with no LiquidHandler-chatterbox execution path at all
  (``unsupported_tool``) -- a scope boundary, not a defect signal.
* anything else (``harness_internal``) -- a bug in the verify/exec_verify
  plumbing itself, not signal about the generated or mined data.

TWO surviving-evidence shapes, TWO entry points (260828 finding, discovered
live: a first version of this module only handled shape #1 below and
silently misclassified every real PLR precondition failure as
``postcondition_mismatch``):

1. A LIVE exception object -- ``execution_verify_call`` in both floor_gen
   and overlay_gen catches genuinely-escaped exceptions (a harness/deck-build
   failure that occurs OUTSIDE ``verifier.verify()``'s own internal
   try/except, e.g. ``run_verify_sync`` itself blowing up). Use
   :func:`classify_exception`.

2. A STRING only -- ``verifier.verify()`` (verify/verifier.py's ``_execute``
   call) catches every exception from actual call dispatch/execution
   INTERNALLY, formats it as ``f"{type(e).__name__}: {e}"``, and reports it
   via the ``"execution_ok"`` named check (verify/checks.py's
   ``run_all_checks``) rather than re-raising -- so a real ``NoTipError``
   from mid-execution NEVER reaches a live ``except`` block; only its
   formatted string survives by the time a caller sees the result. Use
   :func:`classify_check_failure` on the checks list.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Sequence

__all__ = [
    "FAILURE_CATEGORIES",
    "POSTCONDITION_MISMATCH",
    "TaxonomyArtifactError",
    "classify_exception",
    "classify_check_failure",
    "plr_exception_taxonomy_git_sha",
]

#: AST-derived survey of every real PLR Exception subclass across all vendored
#: PLR source files (scripts/survey_plr_exceptions.py or equivalent -- see
#: `.praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md` T7), located
#: relative to this file (never cwd) so it resolves regardless of invocation
#: directory.
_TAXONOMY_PATH = Path(__file__).resolve().parent / "data" / "plr_exception_taxonomy.json"

#: Closed set of failure categories. Anchor tests assert this stays in sync
#: with the classifiers' actual return values.
FAILURE_CATEGORIES: frozenset[str] = frozenset({
    "unsupported_tool",
    "ungroundable_reference",
    "shape_mismatch",
    "precondition_state",
    "harness_internal",
    "postcondition_mismatch",
})

#: Used by callers directly; exported so call sites never hand-spell the string.
POSTCONDITION_MISMATCH = "postcondition_mismatch"


class TaxonomyArtifactError(RuntimeError):
    """``training/verify/data/plr_exception_taxonomy.json`` is missing,
    unreadable, not valid JSON, or missing a required field.

    Raised loudly rather than degrading silently: a malformed/truncated
    artifact must not fall back to an empty exception-name set, which would
    revert the exact ``classify_check_failure`` misclassification bug T7
    fixes (name lookups against those two hand-typed modules -> 11 names)
    but *worse* -- 0 names, so every absorbed PLR exception would misclassify
    as ``harness_internal`` instead of just the 121 currently-missed ones.
    """


@lru_cache(maxsize=1)
def _load_taxonomy_artifact() -> dict[str, Any]:
    """Load and validate the AST-derived PLR exception-class survey.

    Cached (module-level memo via ``lru_cache``) so a 132-entry JSON file is
    parsed once per process, not on every :func:`classify_check_failure`
    call. Loading is lazy -- nothing here runs at import time -- so a
    missing/malformed artifact cannot make ``verify`` unimportable; it only
    raises when a caller actually needs the exception-name table.

    Validates against the artifact's *own* existing stamp shape
    (``version.git_sha`` / ``version.git_dirty`` / ``version.pylabrobot_version``
    plus a non-empty ``classes`` array) -- **not** ``plr_sema``'s ``SurveyStamp``
    (spec §2.2). The spec's "stamped by §2.2" phrasing predates this artifact;
    ``training/`` must not gain a ``plr_sema`` import to satisfy it (see T7
    report). This is a deliberate, flagged deviation from the literal spec
    text, validating the shape that actually exists on disk instead.
    """
    try:
        raw = _TAXONOMY_PATH.read_text()
    except OSError as exc:
        raise TaxonomyArtifactError(
            f"could not read PLR exception taxonomy artifact at {_TAXONOMY_PATH}: {exc}"
        ) from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise TaxonomyArtifactError(
            f"PLR exception taxonomy artifact at {_TAXONOMY_PATH} is not valid JSON: {exc}"
        ) from exc

    version = data.get("version") if isinstance(data, dict) else None
    git_sha = version.get("git_sha") if isinstance(version, dict) else None
    if not git_sha:
        raise TaxonomyArtifactError(
            f"PLR exception taxonomy artifact at {_TAXONOMY_PATH} is missing a non-empty "
            "version.git_sha stamp -- refusing to trust an unstamped artifact."
        )

    classes = data.get("classes") if isinstance(data, dict) else None
    if not classes:
        raise TaxonomyArtifactError(
            f"PLR exception taxonomy artifact at {_TAXONOMY_PATH} has an empty or missing "
            "'classes' array -- refusing to silently degrade to an empty exception-name set."
        )

    return data


@lru_cache(maxsize=1)
def _plr_exception_class_names() -> frozenset[str]:
    """Every real vendored-PLR Exception subclass's __name__, keyed off the
    AST-derived survey artifact (:func:`_load_taxonomy_artifact`) rather than
    hand-typed ``inspect.getmembers`` over two hand-picked modules. That
    two-module walk covered only 11 of the 132 real PLR exception classes
    (92% invisible) -- see the T7 spec item / module docstring shape #2.
    Cached: computed once per process from the cached artifact load."""
    data = _load_taxonomy_artifact()
    return frozenset(entry["name"] for entry in data["classes"])


def plr_exception_taxonomy_git_sha() -> str:
    """The ``external/pylabrobot`` git SHA the loaded exception taxonomy was
    surveyed against (``version.git_sha`` in the artifact).

    Queryable, not enforced: this module never compares the recorded SHA
    against the live ``external/pylabrobot`` checkout itself, and loading
    never hard-fails on a mismatch. ``verify`` is imported inside harness
    runs, and a stale-but-usable taxonomy (classifying against yesterday's
    PLR exception set) is better than an unimportable module. A caller who
    cares whether the artifact is stale should compare this value against
    their own ``git -C external/pylabrobot rev-parse HEAD`` and decide what
    to do about a mismatch (e.g. log a warning, re-run the survey script) --
    that policy belongs to the caller, not baked into this loader.
    """
    return _load_taxonomy_artifact()["version"]["git_sha"]


def classify_exception(exc: BaseException) -> str:
    """Classify a LIVE exception object escaping to a caller's own
    try/except (harness/deck-build failures OUTSIDE verifier.verify()'s
    internal absorption -- see module docstring shape #1).

    Structural, not string-based: dispatches on the exception TYPE's module
    and MRO, never on ``str(exc)``.
    """
    module = type(exc).__module__

    if module.startswith("verify."):
        from verify.dispatcher import DispatchError, UnsupportedCallError
        from verify.grounding import GroundingError

        if isinstance(exc, UnsupportedCallError):
            return "unsupported_tool"
        if isinstance(exc, GroundingError):
            return "ungroundable_reference"
        if isinstance(exc, DispatchError):
            return "shape_mismatch"
        return "harness_internal"

    if module.startswith("pylabrobot."):
        return "precondition_state"

    return "harness_internal"


def classify_check_failure(checks: Sequence[Mapping[str, Any]]) -> str:
    """Classify a FAILED result from ``verify()``'s checks list (module
    docstring shape #2): dispatch/execution exceptions are absorbed inside
    ``verify()`` and surface only as the ``"execution_ok"`` named check's
    ``detail`` string (``"execution failed: {ClassName}: {message}"``) --
    the original exception object is gone by this point.

    If ``execution_ok`` itself failed, extract the absorbed exception's
    class name from its detail text and classify by NAME against a table
    built from real introspection (:func:`_plr_exception_class_names`) plus
    our own harness exception names -- never by parsing the message that
    follows the class name. If ``execution_ok`` passed but some OTHER named
    check failed (volumes/tips/moves/effects/slot_agreement), the call
    genuinely executed and a real physical-effect mismatch was caught:
    ``postcondition_mismatch``.
    """
    by_name = {c["name"]: c for c in checks}
    execution_ok = by_name.get("execution_ok")
    if execution_ok is None or execution_ok["passed"]:
        return POSTCONDITION_MISMATCH

    detail = execution_ok.get("detail") or ""
    # detail format: "execution failed: {ClassName}: {message...}"
    prefix = detail.split("execution failed: ", 1)[-1]
    class_name = prefix.split(":", 1)[0].strip()

    our_names = {"DispatchError": "shape_mismatch", "UnsupportedCallError": "unsupported_tool",
                 "GroundingError": "ungroundable_reference"}
    if class_name in our_names:
        return our_names[class_name]
    if class_name in _plr_exception_class_names():
        return "precondition_state"
    return "harness_internal"
