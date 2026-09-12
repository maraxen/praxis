#!/usr/bin/env python3
"""Offline drift/tracking gate for the web-repl wheel pipeline.

**Path deviation from the wheel spec, noted deliberately.** The wheel spec's
own file list (``.praxia/docs/specs/260817_spec-wheel-build-plr-upgrade.md``
T14, :319) names this file's location as repo-root ``scripts/`` and scopes
its checks at ``praxis/web-client/src/assets/wheels/``. Both are stale
against the ADR (``.praxia/docs/decisions/260817_repl-layout-and-delivery-
mechanism.md``) Sec 2.1 canonical tree, which places every wheel-pipeline
script under ``web-repl/scripts/`` (alongside the already-built
``build_wheels.py`` / ``build_manifest.py`` / ``inject_shell.py`` this file
imports and reuses) and moves the generated artifacts to
``web-repl/overlay/assets/wheels/``. This file follows the ADR's tree, per
the task brief: "the ADR wins" on any path disagreement.

Four independent checks, each with its own flag, plus a bare-invocation
combined default:

- ``--check-pin`` (R7): ``manifest.json``'s ``wheels[pylabrobot].source_sha``
  equals the ACTUAL ``external/pylabrobot`` submodule HEAD -- catches "pin
  moved, wheels not rebuilt."
- ``--check-manifest`` (R5 / ADR Sec 2.3 D2): every manifest entry's sha256
  and byte count match disk, AND the on-disk ``*.whl`` set bidirectionally
  equals the manifest's filename set (catches a stale/partial manifest and a
  leftover wheel from a prior version).
- ``--check-import-sweep`` (wheel-spec T3's ``pkgutil.walk_packages`` sweep,
  wired into this checker per T14's own instruction): re-verifies the
  wheels ALREADY on disk import cleanly, reusing
  ``build_wheels.verify_wheel_importable`` -- a POST-HOC re-check, not a
  rebuild, so it also catches "the wheel on disk is not the one the last
  successful build produced."
- ``--check-untracked`` (R6 + R8, ADR Sec 4.3 re-specification -- see the
  "NO ALLOWLIST" note below): asserts ZERO ``*.whl`` files are git-tracked
  anywhere in the repo, and ZERO ``manifest.json`` files are git-tracked
  under the browser wheel output directories (the loader's only filename
  seam -- a training-output ``manifest.json`` in a sibling subproject
  cannot shadow it; see backlog #5110), and reports (never silently
  fixes) the dead ``.gitignore`` negation R6 requires removed.

With **no** flags, the combined default runs pin + manifest + import-sweep
(matching every "bare `check_wheel_coherence.py`" invocation in the wheel
spec's own R7 / GATE 3 / GATE 4 verification text). ``--check-untracked`` is
**never** part of the bare default -- it is always explicitly requested,
matching the wheel spec's own R8 verification
(``check_wheel_coherence.py --check-untracked``) and GATE 5(b).

**NO ALLOWLIST -- and why that is a deliberate deviation from one ADR
passage, not an oversight.** ADR Sec 4.3's own closing paragraph on R8
floated an interim design: "the allowlist entry becomes the *generated*
filename in overlay/assets/wheels/." That passage is superseded by the
wheel spec's OWN re-scope pass (applied 2026-08-17, recorded in the ADR's
Sec 9 table: *"R6 and R8 re-specified to zero-tracked-wheels ... replacing
the dead name-scoped allowlist"*) and by R6/R8's actual verification text
(":163", ":169" -- "There is no allowlist, because there is no tracked
wheel to allowlist"). Since NOTHING should ever be git-tracked under either
wheels directory once the 0.1.6-era tracked wheels are untracked (P3.11, a
separate task), an allowlist has nothing left to name. This file implements
the superseding, simpler design: the clean-tree arm is "zero tracked
`.whl` repo-wide; zero tracked `manifest.json` under the browser wheel
output directories" -- no per-name exception. The manifest arm is not
repo-wide: a generic basename plus a sibling Coxswain training
subproject in the same monorepo made a repo-wide check a false
positive (backlog #5110). The ``.whl`` arm stays repo-wide -- tracked
wheels anywhere are a real hygiene violation.

House rules: uv-run only, argparse + logging, narrow runs, fail loud.
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger("check_wheel_coherence")

# --- fixed layout (ADR Sec 2.1 canonical tree) -------------------------------
_THIS_FILE = Path(__file__).resolve()
SCRIPTS_DIR = _THIS_FILE.parent
WEB_REPL_ROOT = SCRIPTS_DIR.parent
REPO_ROOT = WEB_REPL_ROOT.parent
SUBMODULE_DIR = REPO_ROOT / "external" / "pylabrobot"
GITIGNORE_PATH = REPO_ROOT / ".gitignore"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import build_manifest  # noqa: E402 -- path setup must precede this import
import build_wheels  # noqa: E402 -- path setup must precede this import


class CoherenceError(RuntimeError):
    """Raised for a fatal setup problem (e.g. no manifest.json at all).
    Individual check FAILURES are returned as problem-message lists, not
    raised, so one run can report every problem it finds, not just the
    first.
    """


def _git(args: list[str], *, cwd: Path = REPO_ROOT) -> str:
    result = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise CoherenceError(f"git {' '.join(args)} (cwd={cwd}) failed: {result.stderr.strip()}")
    return result.stdout


def _git_ls_files(pattern: str, *, cwd: Path = REPO_ROOT) -> list[str]:
    """A pattern with no ``/`` and a leading ``*`` matches the FULL path at
    any depth (verified against this repo: ``git ls-files '*.whl'`` returns
    nested matches; a bare literal like ``git ls-files 'manifest.json'``
    does NOT -- it matches only a root-level file of that exact name). Use
    the leading-``*`` form everywhere here on purpose.

    ``cwd`` MUST be threaded through to ``_git()`` explicitly -- it used to
    default silently to the module-global ``REPO_ROOT`` regardless of what a
    caller passed, which made ``check_untracked(repo_root=...)``'s override
    a no-op for the actual ``git ls-files`` calls (only the display-path
    computation honoured it). Caught by testing this checker against a
    synthetic scratch repo: the override was accepted but every result still
    reported the REAL repo's tracked files. Fixed so ``check_untracked`` is
    actually exercisable against a scratch tree, per the wheel spec's own
    R7/R8 scratch-clone testing requirement.
    """
    out = _git(["ls-files", pattern], cwd=cwd)
    return [line for line in out.splitlines() if line.strip()]


def _load_manifest(web_repl_root: Path) -> dict:
    manifest_path = web_repl_root / "overlay" / "assets" / "wheels" / "manifest.json"
    if not manifest_path.is_file():
        raise CoherenceError(
            f"{manifest_path} does not exist -- run "
            "`uv run python web-repl/scripts/build_wheels.py` then "
            "`uv run python web-repl/scripts/build_manifest.py` first."
        )
    return json.loads(manifest_path.read_text())


# --- (1) R7: submodule pin vs manifest.source_sha ----------------------------


def check_pin(manifest: dict, *, submodule_dir: Path = SUBMODULE_DIR) -> list[str]:
    problems: list[str] = []
    plr_entries = [w for w in manifest.get("wheels", []) if w.get("package") == "pylabrobot"]
    if not plr_entries:
        problems.append("manifest.json has no 'pylabrobot' wheel entry to check the pin against")
        return problems
    manifest_sha = plr_entries[0].get("source_sha")
    actual_sha = _git(["rev-parse", "HEAD"], cwd=submodule_dir).strip()
    if manifest_sha != actual_sha:
        problems.append(
            "PIN DESYNC (R7): manifest.json wheels[pylabrobot].source_sha="
            f"{manifest_sha!r} but external/pylabrobot HEAD={actual_sha!r} -- the "
            "submodule pin moved (or the wheel predates the current pin) and was "
            "not rebuilt. Run `uv run python web-repl/scripts/build_wheels.py` "
            "then `build_manifest.py` again."
        )
    return problems


# --- (2) R5 / D2: manifest integrity + bidirectional wheel-set equality ------


def check_manifest(manifest: dict, *, web_repl_root: Path = WEB_REPL_ROOT) -> list[str]:
    wheels_dir = web_repl_root / "overlay" / "assets" / "wheels"
    problems = list(build_manifest.verify_manifest(manifest, web_repl_root=web_repl_root))
    disk_names = {p.name for p in wheels_dir.glob("*.whl")}
    manifest_names = {w["filename"] for w in manifest.get("wheels", [])}
    if disk_names != manifest_names:
        problems.append(
            "WHEEL SET MISMATCH (R5, bidirectional): disk-only="
            f"{sorted(disk_names - manifest_names)} manifest-only="
            f"{sorted(manifest_names - disk_names)}"
        )
    return problems


# --- (4) T3: re-verify the wheels already on disk import cleanly ------------

# package -> (top-level import names, native_stubs). Mirrors exactly how
# build_wheels.py itself calls verify_wheel_importable() at build time
# (build_pylabrobot / build_pylibftdi respectively). This is a POST-HOC
# re-check of whatever wheel is currently on disk, never a rebuild.
_IMPORT_SWEEP_SPEC: dict[str, tuple[list[str], bool]] = {
    "pylabrobot": (["pylabrobot"], True),
    "pylibftdi": (["pylibftdi"], False),
}


def check_import_sweep(manifest: dict, *, web_repl_root: Path = WEB_REPL_ROOT) -> list[str]:
    wheels_dir = web_repl_root / "overlay" / "assets" / "wheels"
    problems: list[str] = []
    by_package = {w["package"]: w for w in manifest.get("wheels", [])}
    ftdi_entry = by_package.get("pylibftdi")
    ftdi_wheel = wheels_dir / ftdi_entry["filename"] if ftdi_entry else None

    for package, entry in by_package.items():
        spec = _IMPORT_SWEEP_SPEC.get(package)
        if spec is None:
            logger.info(
                "no import-sweep spec for package %r -- skipping (add one to "
                "_IMPORT_SWEEP_SPEC if this package should be swept)",
                package,
            )
            continue
        names, native_stubs = spec
        wheel_path = wheels_dir / entry["filename"]
        if not wheel_path.is_file():
            # Already reported by check_manifest's D2 pass -- do not double-report.
            continue
        extra = None
        if package == "pylabrobot" and ftdi_wheel is not None and ftdi_wheel.is_file():
            extra = [ftdi_wheel]
        try:
            build_wheels.verify_wheel_importable(
                wheel_path, names, extra_wheels=extra, native_stubs=native_stubs
            )
        except build_wheels.BuildError as exc:
            problems.append(f"IMPORT-SWEEP FAILED (T3) for {package}: {exc}")
    return problems


# --- R6 + R8 (--check-untracked): zero tracked wheels/manifests, no allowlist

_GITIGNORE_NEGATION = "!**/src/assets/wheels/"
_TRACKED_OLD_WHEELS = (
    "praxis/web-client/src/assets/wheels/pylabrobot-0.1.6-py3-none-any.whl",
    "praxis/web-client/src/assets/wheels/pylibftdi-0.0.0-py3-none-any.whl",
)

# R6's intent: manifest.json is the only filename seam for the browser
# wheel loader. A stale tracked copy under either wheels directory would
# shadow the built one. Backlog #5110: git pathspec `*manifest.json`
# matches a PARTIAL basename (so train_manifest.json) AND any path ending
# in the literal 'manifest.json', which pulled in Coxswain training
# artifacts (training/{assemble/out,golden,out}/manifest.json) -- a
# sibling subproject in this monorepo whose outputs cannot shadow the
# loader. Filter candidates by exact basename, then scope to these dirs.
# The .whl arm stays repo-wide and is otherwise untouched.
_WHEEL_MANIFEST_PARENTS = (
    Path("web-repl") / "overlay" / "assets" / "wheels",
    Path("praxis") / "web-client" / "src" / "assets" / "wheels",
)


def _find_gitignore_negation(gitignore_path: Path = GITIGNORE_PATH) -> list[int]:
    """Locate the negation by CONTENT, never by a hardcoded line number --
    removing it (a separate, human/P3.11 action; see check_untracked's
    message) shifts every line after it, which is exactly what made the
    ORIGINAL R6's ``sed -n '22,26p' .gitignore`` assertion wrong the moment
    anyone touched the file above it.
    """
    if not gitignore_path.is_file():
        return []
    lines = gitignore_path.read_text().splitlines()
    return [i + 1 for i, line in enumerate(lines) if line.strip() == _GITIGNORE_NEGATION]


def check_untracked(*, repo_root: Path = REPO_ROOT, gitignore_path: Path = GITIGNORE_PATH) -> list[str]:
    problems: list[str] = []

    tracked_whl = _git_ls_files("*.whl", cwd=repo_root)
    if tracked_whl:
        problems.append(
            f"{len(tracked_whl)} tracked .whl file(s) found (R6/R8 require ZERO, "
            f"repo-wide, no allowlist): {tracked_whl}"
        )

    # Backlog #5110: do not treat a pathspec suffix as a basename. `*` in a
    # git pathspec matches across `/` AND matches a partial basename, so
    # `*manifest.json` hits train_manifest.json plus Coxswain training
    # manifests that cannot shadow the browser wheel loader. Exact-basename
    # filter, then scope to the wheel output directories.
    candidates = _git_ls_files("*manifest.json", cwd=repo_root)
    tracked_manifest = [
        p
        for p in candidates
        if Path(p).name == "manifest.json" and Path(p).parent in _WHEEL_MANIFEST_PARENTS
    ]
    if tracked_manifest:
        problems.append(
            f"{len(tracked_manifest)} tracked manifest.json file(s) found under "
            f"a browser wheel output directory (R6 forbids this -- a stale "
            f"tracked copy would shadow the built loader seam): {tracked_manifest}"
        )

    negation_lines = _find_gitignore_negation(gitignore_path)
    if negation_lines:
        lines_str = ", ".join(str(n) for n in negation_lines)
        rel = gitignore_path.relative_to(repo_root) if gitignore_path.is_relative_to(repo_root) else gitignore_path
        problems.append(
            f"{rel} still contains the dead negation {_GITIGNORE_NEGATION!r} "
            f"(currently line(s) {lines_str} -- located by content, not a hardcoded "
            "line number). R6 requires this gone. NOT fixed by this script: removing "
            "it must land in the SAME COMMIT as `git rm --cached` on the two "
            "currently-tracked old wheels, and this agent is forbidden from touching "
            "the git index. Human/P3.11 action required: (a) `git rm --cached "
            f"{_TRACKED_OLD_WHEELS[0]} {_TRACKED_OLD_WHEELS[1]}`, then commit; (b) in "
            f"that SAME commit, delete line {lines_str} of {rel} "
            f"({_GITIGNORE_NEGATION!r})."
        )

    return problems


# --- CLI -----------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--check-pin", action="store_true", help="R7: pin vs manifest.source_sha.")
    parser.add_argument("--check-manifest", action="store_true", help="R5/D2: manifest vs disk, bidirectional.")
    parser.add_argument("--check-import-sweep", action="store_true", help="T3: re-verify wheels on disk import cleanly.")
    parser.add_argument(
        "--check-untracked",
        action="store_true",
        help="R6/R8: zero tracked .whl repo-wide; zero tracked manifest.json "
        "under the browser wheel output directories. No allowlist. "
        "Never part of the bare default -- always explicit.",
    )
    parser.add_argument(
        "--web-repl-root",
        type=Path,
        default=WEB_REPL_ROOT,
        help="Override web-repl/ root (testing only -- points --check-manifest / "
        "--check-import-sweep / --check-pin at a scratch tree).",
    )
    parser.add_argument(
        "--submodule-dir",
        type=Path,
        default=None,
        help="Override external/pylabrobot dir for --check-pin (testing only).",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Debug-level logging.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    web_repl_root = args.web_repl_root.resolve()
    submodule_dir = (args.submodule_dir or (web_repl_root.parent / "external" / "pylabrobot")).resolve()

    explicit = args.check_pin or args.check_manifest or args.check_import_sweep or args.check_untracked
    run_pin = args.check_pin or not explicit
    run_manifest = args.check_manifest or not explicit
    run_import_sweep = args.check_import_sweep or not explicit
    run_untracked = args.check_untracked  # opt-in only -- see module docstring

    problems: list[str] = []
    manifest: dict | None = None
    try:
        if run_pin or run_manifest or run_import_sweep:
            manifest = _load_manifest(web_repl_root)
        if run_pin:
            problems += check_pin(manifest, submodule_dir=submodule_dir)
        if run_manifest:
            problems += check_manifest(manifest, web_repl_root=web_repl_root)
        if run_import_sweep:
            problems += check_import_sweep(manifest, web_repl_root=web_repl_root)
        if run_untracked:
            problems += check_untracked()
    except CoherenceError as exc:
        logger.error("%s", exc)
        return 1

    if problems:
        for p in problems:
            logger.error("COHERENCE FAIL: %s", p)
        return 1

    ran = [n for n, on in (("pin", run_pin), ("manifest", run_manifest),
                           ("import-sweep", run_import_sweep), ("untracked", run_untracked)) if on]
    logger.info("coherence OK (%s)", ", ".join(ran))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
