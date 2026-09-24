"""Spec 260901 §5 / T5 (backlog #4830): fork-drift tests for Fork A (the
coxswain port of `praxis/backend/core/simulation/*`) and Fork B (the
cherry-picked `git_state.py`).

Exactly the five tests named in §5.4 for Forks A and B. Fork C
(`test_mirror_fields_match_operation_node`, §5.3) is explicitly out of scope
here -- its comparison target (`plr_sema/check/graph.py`) does not exist yet
(T8) and lives in its own file, `test_check_graph_mirror_drift.py`.

Fork A (§5.1): `coxswain/src/coxswain/fft/preconditions/` carries six ported
modules in three distinct `PORT PROVENANCE` header forms:
  - single-range verbatim (`method_contracts.py`, `state_models.py`) -- a
    single comment line naming one contiguous upstream range.
  - multi-member partial lift (`failure_modes.py`, `simulation_result.py`,
    `pipeline_models.py`) -- a multi-line block whose members each carry
    their own `#   - <Name>  <file>.py:<start>-<end>` line, disjoint ranges
    into a *differently-named* upstream module.
  - no-range adaptation (`bounds_analyzer.py`) -- a multi-line block with an
    explicit `ADAPTATION` note and no source line range at all.

Only the two verbatim modules get body comparison (§5.1: per-member body
extraction from the fork file needs symbol-range resolution, named as
follow-on work, not round-1 scope). All six get header-parseability
coverage, and the two verbatim modules additionally get a +/-2-line
range-sanity check (that tolerance is incoherent for the other four -- see
§5.5).

Fork B (§5.2): `plr_sema/_provenance/git_state.py` is a cherry-pick from
`/home/marielle/projects/cisternal` (a machine-local, out-of-repo checkout).
Tier 1 (self-consistency, always runs) recomputes the header's recorded
`upstream sha256` over the file with its provenance header stripped -- this
is what actually enforces "DO NOT EDIT". Tier 2 (upstream comparison) skips
with a named reason when `$PLR_SEMA_CISTERNAL_ROOT` (default
`/home/marielle/projects/cisternal`) is absent, and otherwise compares bytes
and asserts the recorded upstream commit is an ancestor of upstream HEAD.

Fork D (260901 T13, backlog #4859): `external/pylabrobot` itself -- a whole
PINNED SUBMODULE, not a ported/cherry-picked file. Motivating incident: the
submodule drifted 53 commits behind upstream `main` (upstream restructured
669 files, relocating the entire function-organized layout wholesale into
`pylabrobot/legacy/`) and NOTHING in this project noticed, six adversarial
review rounds included -- Forks A/B/C all watch something copied INTO this
repo against its source; none of them watch the checked-out dependency
itself against its own origin. Same tier split as Fork B, one class up:
tier 1 (`test_plr_submodule_pin_matches_expected`, always runs, no network)
asserts the submodule's live HEAD equals a declared expected pin. Tier 2
(`test_plr_submodule_distance_from_upstream_main`) fetches `origin/main` and
reports the commit distance, skipping with a named reason
(`"cannot reach origin for external/pylabrobot ..."`) when the fetch fails --
the sandbox blocks the egress proxy, so offline is the COMMON case in CI,
per this task's brief, and a bare fetch failure must never read as a silent
pass.
"""

from __future__ import annotations

import difflib
import hashlib
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

from plr_sema._provenance import git_state

REPO_ROOT = Path(__file__).resolve().parents[2]
PRECONDITIONS_DIR = (
    REPO_ROOT / "coxswain" / "src" / "coxswain" / "fft" / "preconditions"
)
GIT_STATE_PATH = Path(git_state.__file__)

_DEFAULT_CISTERNAL_ROOT = Path("/home/marielle/projects/cisternal")
_CISTERNAL_GIT_STATE_RELPATH = Path("src") / "cisternal" / "telemetry" / "git_state.py"


class HeaderParseError(Exception):
    """A PORT PROVENANCE / CHERRY-PICK PROVENANCE header did not parse to any
    recognized form. Raised, never swallowed -- see §5.4's
    test_port_provenance_headers_are_parseable / test_every_ported_module_is_covered,
    which exist precisely so an unparseable header turns red instead of
    silently dropping its module from coverage."""


# --------------------------------------------------------------------------
# Fork A: PORT PROVENANCE header parsing (three recognized forms)
# --------------------------------------------------------------------------

_PORT_PROVENANCE_MARKER = "# --- PORT PROVENANCE"

_SINGLE_RANGE_RE = re.compile(
    r"^# --- PORT PROVENANCE \(verbatim copy of "
    r"(?P<path>\S+\.py):(?P<start>\d+)-(?P<end>\d+)\)\s*-*\s*$"
)
_BLOCK_START_RE = re.compile(r"^# --- PORT PROVENANCE\s*-{3,}\s*$")
_BLOCK_FENCE_RE = re.compile(r"^#\s*-{3,}\s*$")
_SOURCE_PATH_RE = re.compile(
    r"^#\s*(?:Partial lift from|Copied from)\s+(?P<path>\S+\.py)\b"
)
_MEMBER_RE = re.compile(
    r"^#\s+-\s+(?P<name>\S+)\s+.*?(?P<file>\S+\.py):(?P<start>\d+)-(?P<end>\d+)"
)
_ADAPTATION_RE = re.compile(r"\bADAPTATION\b")


@dataclass(frozen=True)
class SingleRangeHeader:
    """Single-range verbatim form: one comment line, whole file is a
    contiguous copy of upstream_path[start:end] (1-indexed, inclusive)."""

    upstream_path: str
    start: int
    end: int
    header_line_count: int


@dataclass(frozen=True)
class Member:
    name: str
    source_file: str
    start: int
    end: int


@dataclass(frozen=True)
class MultiMemberHeader:
    """Multi-member partial-lift form: a block header naming disjoint
    per-member ranges into a (possibly differently-named) upstream file."""

    upstream_path: str
    members: tuple[Member, ...]
    header_line_count: int


@dataclass(frozen=True)
class AdaptationHeader:
    """No-range adaptation form: a block header naming an upstream file and
    an explicit ADAPTATION note, with no source line range at all."""

    upstream_path: str
    header_line_count: int


ParsedHeader = SingleRangeHeader | MultiMemberHeader | AdaptationHeader


def parse_port_provenance_header(path: Path) -> ParsedHeader:
    """Parse a `PORT PROVENANCE` header. Never silently drops a module:
    raises HeaderParseError, naming the file and the unparsed text, for any
    header that does not match one of the three recognized forms (§5.4)."""
    lines = path.read_text().splitlines()
    if not lines or not lines[0].startswith(_PORT_PROVENANCE_MARKER):
        raise HeaderParseError(f"{path}: no PORT PROVENANCE header on line 1")

    first = lines[0]
    single = _SINGLE_RANGE_RE.match(first)
    if single:
        return SingleRangeHeader(
            upstream_path=single.group("path"),
            start=int(single.group("start")),
            end=int(single.group("end")),
            header_line_count=1,
        )

    if not _BLOCK_START_RE.match(first):
        raise HeaderParseError(
            f"{path}: unrecognized PORT PROVENANCE header form on line 1: "
            f"{first!r}"
        )

    end_idx = None
    for i in range(1, len(lines)):
        if _BLOCK_FENCE_RE.match(lines[i]):
            end_idx = i
            break
    if end_idx is None:
        raise HeaderParseError(
            f"{path}: PORT PROVENANCE block opened on line 1 but no closing "
            f"'# ---...---' fence line was found"
        )

    block = lines[1:end_idx]
    source_path = None
    for line in block:
        m = _SOURCE_PATH_RE.match(line)
        if m:
            source_path = m.group("path")
            break
    if source_path is None:
        raise HeaderParseError(
            f"{path}: PORT PROVENANCE block has no parseable "
            f"'Partial lift from <path>' / 'Copied from <path>' source line:\n"
            + "\n".join(block)
        )

    members = tuple(
        Member(
            name=m.group("name"),
            source_file=m.group("file"),
            start=int(m.group("start")),
            end=int(m.group("end")),
        )
        for m in (_MEMBER_RE.match(line) for line in block)
        if m
    )
    if members:
        return MultiMemberHeader(
            upstream_path=source_path,
            members=members,
            header_line_count=end_idx + 1,
        )

    if any(_ADAPTATION_RE.search(line) for line in block):
        return AdaptationHeader(
            upstream_path=source_path, header_line_count=end_idx + 1
        )

    raise HeaderParseError(
        f"{path}: PORT PROVENANCE block recognized neither a multi-member "
        f"partial-lift form (no '#   - Name  file.py:start-end' line found) "
        f"nor a no-range adaptation form (no 'ADAPTATION' marker found):\n"
        + "\n".join(block)
    )


def _has_port_provenance_marker(path: Path) -> bool:
    try:
        first_line = path.read_text().splitlines()[0]
    except IndexError:
        return False
    return first_line.startswith(_PORT_PROVENANCE_MARKER)


_PRECONDITION_FILES = sorted(
    p for p in PRECONDITIONS_DIR.glob("*.py") if _has_port_provenance_marker(p)
)


def _try_parse(path: Path) -> ParsedHeader | None:
    try:
        return parse_port_provenance_header(path)
    except HeaderParseError:
        return None


_HEADERS_BY_PATH = {p: _try_parse(p) for p in _PRECONDITION_FILES}
_VERBATIM_MODULES = sorted(
    p for p, h in _HEADERS_BY_PATH.items() if isinstance(h, SingleRangeHeader)
)


def _normalize(lines: list[str]) -> list[str]:
    """§5.1: strip trailing whitespace, drop blank lines, on both sides. A
    raw-byte comparison would go permanently red on a formatter run on
    either side -- normalization is what keeps this test meaningful rather
    than muted."""
    return [line.rstrip() for line in lines if line.strip() != ""]


@pytest.mark.parametrize("fork_path", _VERBATIM_MODULES, ids=lambda p: p.name)
def test_coxswain_port_matches_upstream(fork_path: Path) -> None:
    """Spec §5.1/§5.4: parametrized over the two whole-file-verbatim ported
    modules (method_contracts.py, state_models.py), derived from their
    single-range headers -- adding a third whole-file-verbatim module
    requires no edit to this test (DERIVED)."""
    header = _HEADERS_BY_PATH[fork_path]
    assert isinstance(header, SingleRangeHeader), (
        f"{fork_path.name}: expected a single-range verbatim header by "
        f"construction of _VERBATIM_MODULES, got {header!r}"
    )

    upstream_path = REPO_ROOT / header.upstream_path
    assert upstream_path.is_file(), (
        f"{fork_path.name}: header names upstream path "
        f"{header.upstream_path!r}, which does not exist at {upstream_path}"
    )

    upstream_lines = upstream_path.read_text().splitlines()
    upstream_slice = upstream_lines[header.start - 1 : header.end]
    fork_body = fork_path.read_text().splitlines()[header.header_line_count :]

    norm_upstream = _normalize(upstream_slice)
    norm_fork = _normalize(fork_body)

    if norm_upstream != norm_fork:
        diff = "\n".join(
            difflib.unified_diff(
                norm_upstream,
                norm_fork,
                fromfile=f"{header.upstream_path}:{header.start}-{header.end}",
                tofile=str(fork_path.relative_to(REPO_ROOT)),
                lineterm="",
            )
        )
        pytest.fail(
            f"{fork_path.relative_to(REPO_ROOT)} has drifted from upstream "
            f"{header.upstream_path}:{header.start}-{header.end}:\n{diff}"
        )


def test_every_ported_module_is_covered() -> None:
    """Spec §5.1/§5.4: enumerate every file under
    coxswain/src/coxswain/fft/preconditions/ carrying a PORT PROVENANCE
    header -- there are six, not four -- and fail loudly (never skip, never
    silently drop) on any header whose form the parser does not recognize."""
    assert len(_PRECONDITION_FILES) == 6, (
        f"expected exactly 6 ported modules carrying a PORT PROVENANCE "
        f"header under {PRECONDITIONS_DIR}, found {len(_PRECONDITION_FILES)}: "
        f"{[p.name for p in _PRECONDITION_FILES]}"
    )

    failures: list[str] = []
    for path in _PRECONDITION_FILES:
        try:
            parse_port_provenance_header(path)
        except HeaderParseError as exc:
            failures.append(str(exc))
    assert failures == [], (
        "the following ported modules carry a PORT PROVENANCE header that "
        "does not parse to any of the three recognized forms (single-range "
        "verbatim, multi-member partial lift, no-range adaptation):\n"
        + "\n---\n".join(failures)
    )


# Parametrized over a directory scan of marker-carrying files, not over a
# pre-filtered "successfully parsed" list -- so a header that drifts into
# unparseability fails *that specific file's* parametrized instance loudly,
# instead of silently shrinking the parameter list (§5.4 / trap 8).
@pytest.mark.parametrize("fork_path", _PRECONDITION_FILES, ids=lambda p: p.name)
def test_port_provenance_headers_are_parseable(fork_path: Path) -> None:
    """Spec §5.1/§5.4/§5.5: every file under the preconditions dir with a
    PORT PROVENANCE header parses to a valid provenance record and its
    referenced upstream path exists. For the two whole-file-verbatim
    modules, additionally asserts the claimed range's length is within +/-2
    lines of the fork file's non-header body length (catches gross range
    errors). That tolerance is incoherent for the other four
    (multi-member/adaptation) forms and is not applied to them (§5.5)."""
    assert len(_PRECONDITION_FILES) == 6, (
        f"expected exactly 6 ported modules carrying a PORT PROVENANCE "
        f"header under {PRECONDITIONS_DIR}, found {len(_PRECONDITION_FILES)}: "
        f"{[p.name for p in _PRECONDITION_FILES]}"
    )

    header = parse_port_provenance_header(fork_path)

    upstream_path = REPO_ROOT / header.upstream_path
    assert upstream_path.is_file(), (
        f"{fork_path.name}: header references upstream path "
        f"{header.upstream_path!r}, which does not exist at {upstream_path}"
    )

    if isinstance(header, SingleRangeHeader):
        claimed_len = header.end - header.start + 1
        body_len = len(fork_path.read_text().splitlines()) - header.header_line_count
        assert abs(claimed_len - body_len) <= 2, (
            f"{fork_path.name}: header claims range {header.start}-"
            f"{header.end} ({claimed_len} lines) but the fork's non-header "
            f"body is {body_len} lines -- outside the +/-2 tolerance"
        )


# --------------------------------------------------------------------------
# Fork B: cherry-picked git_state.py (§5.2)
# --------------------------------------------------------------------------

_CHERRY_PICK_START_RE = re.compile(r"^# --- CHERRY-PICK PROVENANCE\s*-*\s*$")
_CHERRY_PICK_FENCE_RE = re.compile(r"^#\s*-{3,}\s*$")
_SHA256_FIELD_RE = re.compile(r"^#\s*upstream sha256:\s*(?P<sha>[0-9a-f]{64})\s*$")
_COMMIT_FIELD_RE = re.compile(r"^#\s*upstream commit:\s*(?P<commit>[0-9a-f]{40})\s*$")


@dataclass(frozen=True)
class CherryPickHeader:
    upstream_sha256: str
    upstream_commit: str
    header_line_count: int


def parse_cherry_pick_header(path: Path) -> CherryPickHeader:
    """Parse the CHERRY-PICK PROVENANCE header, locating the header's end by
    its closing fence marker -- never by a hardcoded line count (trap 1: a
    header that gains a line must not silently break the hash)."""
    lines = path.read_text().splitlines()
    if not lines or not _CHERRY_PICK_START_RE.match(lines[0]):
        raise HeaderParseError(f"{path}: no CHERRY-PICK PROVENANCE header on line 1")

    end_idx = None
    for i in range(1, len(lines)):
        if _CHERRY_PICK_FENCE_RE.match(lines[i]):
            end_idx = i
            break
    if end_idx is None:
        raise HeaderParseError(
            f"{path}: CHERRY-PICK PROVENANCE block opened on line 1 but no "
            f"closing '# ---...---' fence line was found"
        )

    sha = commit = None
    for line in lines[1:end_idx]:
        m = _SHA256_FIELD_RE.match(line)
        if m:
            sha = m.group("sha")
        m2 = _COMMIT_FIELD_RE.match(line)
        if m2:
            commit = m2.group("commit")
    if sha is None:
        raise HeaderParseError(f"{path}: no 'upstream sha256:' field in header")
    if commit is None:
        raise HeaderParseError(f"{path}: no 'upstream commit:' field in header")

    return CherryPickHeader(
        upstream_sha256=sha, upstream_commit=commit, header_line_count=end_idx + 1
    )


def _fork_body_bytes(path: Path, header_line_count: int) -> bytes:
    raw_lines = path.read_bytes().splitlines(keepends=True)
    return b"".join(raw_lines[header_line_count:])


def test_git_state_self_consistent() -> None:
    """Spec §5.2 tier 1 (always runs, no cisternal needed): recompute
    sha256 over git_state.py with its provenance header block stripped, and
    assert it matches the header's recorded 'upstream sha256'. This is the
    load-bearing enforcement of the header's 'DO NOT EDIT' -- it catches
    someone editing the local copy, not upstream moving."""
    header = parse_cherry_pick_header(GIT_STATE_PATH)
    body = _fork_body_bytes(GIT_STATE_PATH, header.header_line_count)
    computed = hashlib.sha256(body).hexdigest()
    assert computed == header.upstream_sha256, (
        f"{GIT_STATE_PATH} body sha256 mismatch: header records "
        f"{header.upstream_sha256}, recomputed {computed}. The header says "
        f"DO NOT EDIT -- someone edited the cherry-picked file locally."
    )


def test_git_state_matches_cisternal() -> None:
    """Spec §5.2 tier 2 (skips with a named reason when cisternal is
    absent): compares git_state.py's body bytes against the live cisternal
    checkout's copy, and asserts the header's recorded upstream commit is an
    ancestor of cisternal's current HEAD (a drifted-but-not-rebased pick is
    a different finding from a rebased one). A commit is its own ancestor,
    so this passes today when the recorded commit IS cisternal HEAD -- that
    is correct behavior, not a vacuous test."""
    cisternal_root = Path(
        os.environ.get("PLR_SEMA_CISTERNAL_ROOT", str(_DEFAULT_CISTERNAL_ROOT))
    )
    if not cisternal_root.is_dir():
        pytest.skip(
            f"cisternal checkout not found at {cisternal_root} "
            f"(set $PLR_SEMA_CISTERNAL_ROOT to override)"
        )

    upstream_file = cisternal_root / _CISTERNAL_GIT_STATE_RELPATH
    if not upstream_file.is_file():
        pytest.skip(
            f"cisternal checkout at {cisternal_root} has no "
            f"{_CISTERNAL_GIT_STATE_RELPATH}"
        )

    header = parse_cherry_pick_header(GIT_STATE_PATH)
    fork_body = _fork_body_bytes(GIT_STATE_PATH, header.header_line_count)
    upstream_body = upstream_file.read_bytes()
    assert fork_body == upstream_body, (
        f"{GIT_STATE_PATH} has drifted from {upstream_file} "
        f"(cisternal HEAD's copy of git_state.py)"
    )

    result = subprocess.run(
        [
            "git",
            "-C",
            str(cisternal_root),
            "merge-base",
            "--is-ancestor",
            header.upstream_commit,
            "HEAD",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"recorded upstream commit {header.upstream_commit} is not an "
        f"ancestor of cisternal HEAD (stderr: {result.stderr.strip()})"
    )


# --------------------------------------------------------------------------
# Fork D: the checked-out `external/pylabrobot` submodule against its own
# `origin` (260901 T13, §"the missing check"). See module docstring.
# --------------------------------------------------------------------------

PLR_SUBMODULE_ROOT = REPO_ROOT / "external" / "pylabrobot"

#: The pin recorded 2026-09-01 (this task's recon): 53 commits behind
#: upstream `main`'s `3a50a567f` at measurement time. A hand-typed
#: expectation BY DESIGN -- the whole point of tier 1 is a fixed value to
#: diff the LIVE submodule HEAD against; deriving it from the submodule
#: itself would make the comparison vacuous. Registered as HM-23 in
#: `plr_sema._hand_maintained.REGISTRY` (260901 T13) -- that row's `measure`
#: reads this exact constant, so the two cannot silently drift apart from
#: each other even though nothing imports one from the other (a test module
#: is not importable by `_hand_maintained.py` without the same C7 sys.path
#: shim every other AST-reading row already needs).
EXPECTED_SUBMODULE_PIN = "dd79c4c89bc008629a1c598ea614be5e6067d1f9"

#: Distance (commits behind origin/main) beyond which tier 2 treats the
#: drift as "unexpectedly large" and fails loudly rather than just
#: reporting a number. 53 is the measured distance at T13; growth between
#: pin bumps is normal and expected, so this is not "drift == 0", but a
#: sudden multi-hundred-commit jump (e.g. another silent multi-month gap)
#: is exactly the failure mode this task exists to make visible. 3x the
#: measured distance, rounded up, gives headroom for ordinary drift between
#: intentional re-pins without masking a real regression back to silence.
_UNEXPECTED_DRIFT_THRESHOLD = 200


def test_plr_submodule_pin_matches_expected() -> None:
    """Tier 1 (always runs, no network needed): `external/pylabrobot`'s own
    HEAD must equal `EXPECTED_SUBMODULE_PIN`. This is the load-bearing half
    -- it catches the submodule being re-pinned (intentionally or not)
    without a corresponding update to this constant, the same
    self-consistency contract `test_git_state_self_consistent` enforces for
    the cherry-picked `git_state.py`, one dependency class up (a whole
    pinned submodule, not a single file)."""
    state = git_state.capture_git_state(PLR_SUBMODULE_ROOT)
    assert state.provenance_source == "git", (
        f"expected {PLR_SUBMODULE_ROOT} to be a real git submodule checkout, "
        f"got provenance_source={state.provenance_source!r} -- is the "
        f"submodule initialized?"
    )
    assert state.hash == EXPECTED_SUBMODULE_PIN, (
        f"external/pylabrobot HEAD is {state.hash}, expected "
        f"{EXPECTED_SUBMODULE_PIN} -- the submodule was re-pinned without "
        f"updating EXPECTED_SUBMODULE_PIN in "
        f"plr-sema/tests/test_fork_drift.py (and HM-23's declared value in "
        f"plr_sema._hand_maintained.REGISTRY, which measures this same "
        f"constant). Re-pinning the submodule is out of this task's scope "
        f"(260901 T13) but is a real, expected future event -- when it "
        f"happens, both places update together, in the same reviewable "
        f"commit."
    )


def test_plr_submodule_distance_from_upstream_main() -> None:
    """Tier 2: skips with a named reason when `origin` is unreachable (the
    sandbox blocks the proxy, so offline is the COMMON case in CI -- design
    for it, per this task's brief). When reachable, fetches `origin/main`
    and reports the commit distance between the pinned HEAD and it, failing
    loudly only if that distance clears `_UNEXPECTED_DRIFT_THRESHOLD` --
    ordinary, expected drift between deliberate re-pins is not itself a
    failure; an unexpectedly large jump is."""
    fetch = subprocess.run(
        ["git", "-C", str(PLR_SUBMODULE_ROOT), "fetch", "--quiet", "origin", "main"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if fetch.returncode != 0:
        pytest.skip(
            f"cannot reach origin for external/pylabrobot ('git fetch origin "
            f"main' failed, rc={fetch.returncode}: {fetch.stderr.strip()!r}) "
            f"-- upstream distance is the missing thing this tier would "
            f"otherwise report"
        )

    count = subprocess.run(
        ["git", "-C", str(PLR_SUBMODULE_ROOT), "rev-list", "--count", "HEAD..origin/main"],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    distance = int(count.stdout.strip())
    print(f"\nexternal/pylabrobot is {distance} commit(s) behind origin/main")
    assert distance < _UNEXPECTED_DRIFT_THRESHOLD, (
        f"external/pylabrobot is {distance} commits behind origin/main -- "
        f"beyond the {_UNEXPECTED_DRIFT_THRESHOLD}-commit unexpected-drift "
        f"threshold. This does not by itself mean anything is broken, but it "
        f"is exactly the silent-drift shape that let this submodule fall 53 "
        f"commits behind unnoticed across six adversarial review rounds -- "
        f"raising the threshold requires a reviewable argument, not just "
        f"suppressing the assertion."
    )
