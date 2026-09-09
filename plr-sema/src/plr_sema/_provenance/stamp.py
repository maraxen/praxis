"""plr_sema._provenance.stamp: process-memoized SurveyStamp (spec 260901 §2.2;
``Surface`` parameterization added 260901 T13, backlog #4859).

Supersedes plr_survey_common.plr_version_stamp()'s {git_sha, git_dirty: bool}
pair with a full GitState for both the PLR submodule and the analyzer's own
repo, plus the installed pylabrobot package version if importable.

**T13 -- the analyzed surface is a parameter, not a constant.** Before T13
this module hardcoded ``_PLR_SUBMODULE = external/pylabrobot`` as the ONLY
tree ``survey_stamp()`` could ever describe -- silently coupling every
stamp to whichever PLR checkout happened to be pinned. ``Surface`` makes
"which tree" an explicit, named value: ``(name, tree_path, pin)``. Two
surfaces exist today (see the report for this task): ``DEFAULT_SURFACE``
(``"legacy_pinned"``, our checked-out submodule) and an upstream snapshot
extracted out-of-repo via ``git archive <sha> | tar -x`` (no ``.git``
directory, so ``capture_git_state`` on it degrades to the ``"nogit"``
sentinel -- exactly its documented, never-raising behavior; that's why
``Surface.pin`` exists as an explicit, caller-supplied fact rather than
something this module tries to infer from a tree that structurally cannot
answer "what commit is this" via git).

Normative -- memoization: survey_stamp() is memoized **at most once per
process PER SURFACE** (a module-level dict cache keyed on
``(surface.name, str(surface.tree_path))``, populated on first call for
that key); repeated calls for the SAME surface within the same process
return the cached SurveyStamp rather than re-invoking capture_git_state, but
a call for a DIFFERENT surface computes and caches its own independent
entry. A dirty tree's tree-OID computation costs ~8 subprocesses
(git_state._compute_dirty_content_id), so a SurveyStamp is ~16 subprocesses
total (plr + praxis) if recomputed per call -- the memoization is what keeps
"every emitted event carries the full SurveyStamp" (spec §4.1) affordable.
emit() never shells out; it only serializes whatever SurveyStamp object it
is handed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from plr_sema._provenance.git_state import GitState, capture_git_state

# plr-sema/src/plr_sema/_provenance/stamp.py -> repo root is four parents up.
_REPO_ROOT = Path(__file__).resolve().parents[4]
_PLR_SUBMODULE = _REPO_ROOT / "external" / "pylabrobot"

SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class Surface:
    """One analyzed PLR tree, named (spec 260901 T13): ``(name, tree_path,
    pin)``. ``tree_path`` is whatever directory a survey/derive run should
    scan -- a live submodule checkout (has ``.git``, git-inspectable) or an
    out-of-repo extraction (no ``.git``, degrades to the ``"nogit"``
    sentinel). ``pin`` is an explicit, caller-supplied commit identity for
    the case ``tree_path`` cannot answer that itself (a non-git extraction);
    ``None`` for a live checkout, where ``GitState.hash`` already answers it
    and a second, possibly-stale copy would only invite drift between the
    two. Never inferred, never defaulted to something guessed -- an unset
    ``pin`` on a non-git tree stays ``None`` in the emitted stamp rather than
    silently reporting a wrong or borrowed commit."""

    name: str
    tree_path: Path
    pin: str | None = None


#: The pre-T13 default: our checked-out submodule. Every caller that does
#: not explicitly pass a ``Surface`` gets exactly the behavior this module
#: had before T13 -- same tree, same cache key, same stamp shape (plus the
#: two new, additive ``surface``/``surface_pin`` fields below).
DEFAULT_SURFACE = Surface(name="legacy_pinned", tree_path=_PLR_SUBMODULE, pin=None)


@dataclass(frozen=True, slots=True)
class SurveyStamp:
    """Provenance pin for one analyzer run or emitted event: which PLR tree,
    which analyzer tree, which installed pylabrobot version (spec 260901
    §2.2), and (T13) which named ``Surface`` produced this stamp.

    ``surface``/``surface_pin`` are additive fields with defaults -- every
    pre-T13 call site (``SurveyStamp(plr=..., praxis=..., ...)`` with no
    surface kwargs) keeps constructing exactly as before; every pre-T13
    on-disk artifact still deserializes via ``.get()`` fallbacks in
    ``check/`` and ``derive/`` (see those modules) rather than requiring a
    schema bump for what is a purely additive change.
    """

    plr: GitState
    praxis: GitState
    pylabrobot_version: str | None
    stamped_at: str
    schema_version: int = SCHEMA_VERSION
    #: Surface.name of the tree this stamp was computed against.
    #: "legacy_pinned" for every pre-T13 stamp and for any caller that does
    #: not pass an explicit Surface (DEFAULT_SURFACE's own name).
    surface: str = DEFAULT_SURFACE.name
    #: Surface.pin, carried through verbatim -- see Surface's own docstring
    #: for why this is not inferred from ``plr.hash`` (a non-git extraction
    #: has no ``plr.hash`` to infer it from).
    surface_pin: str | None = None


#: T13: memoized per surface, not globally -- keyed on
#: (surface.name, str(surface.tree_path)). A single global Optional[...]
#: (the pre-T13 shape) would make the SECOND surface's first survey_stamp()
#: call in the same process silently return the FIRST surface's cached
#: stamp -- exactly the bug this task exists to prevent one level up (a
#: hardcoded analyzed surface), reintroduced at the caching layer instead of
#: the constant layer.
_cache: dict[tuple[str, str], SurveyStamp] = {}


def _pylabrobot_version() -> str | None:
    try:
        import pylabrobot
    except ImportError:
        return None
    return getattr(pylabrobot, "__version__", None)


def survey_stamp(surface: Surface = DEFAULT_SURFACE) -> SurveyStamp:
    """Return the process-memoized SurveyStamp for ``surface``, computing it
    on first call for that surface's cache key.

    See module docstring: memoized at most once per process PER SURFACE.
    Callers that need a fresh capture (e.g. tests) must go through
    ``_reset_survey_stamp_cache_for_tests`` first; there is no public way to
    force recomputation for a given key, by design.
    """
    cache_key = (surface.name, str(surface.tree_path))
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached
    stamp = SurveyStamp(
        plr=capture_git_state(surface.tree_path),
        praxis=capture_git_state(_REPO_ROOT),
        pylabrobot_version=_pylabrobot_version(),
        stamped_at=datetime.now(timezone.utc).isoformat(),
        schema_version=SCHEMA_VERSION,
        surface=surface.name,
        surface_pin=surface.pin,
    )
    _cache[cache_key] = stamp
    return stamp


def _reset_survey_stamp_cache_for_tests() -> None:
    """Test-only: clear the memoization cache (ALL surfaces) so the next
    survey_stamp() call for any key recomputes. Not part of the public
    surface."""
    global _cache
    _cache = {}
