#!/usr/bin/env python3
"""Generate ``web-repl/overlay/assets/wheels/manifest.json`` -- the ONLY
filename seam between hand-written source and the wheels/loose sources the
browser bootstrap fetches.

Per ADR ``.praxia/docs/decisions/260817_repl-layout-and-delivery-mechanism.md``
Sec 2.3 ("the three-detector drift design"), this script is the generator
half of **D2** (``manifest.json`` sha256 over wheels AND loose sources) and
the manifest half of **D1**'s dev-loop escape hatch (``--dev`` writes the
``"dev"`` sentinel into ``praxis_git_sha``). It does not own D1's other half
(the shell injection -- see ``inject_shell.py``) or D3 (the AST
import-coverage test -- a later task).

Manifest shape (ADR Sec 2.3, exact; P2.7a adds the flag-gated ``models``
key -- spec ``260825_coxswain-phase-2-functiongemma-copilot-p.md`` rev2 F3)::

    { "praxis_git_sha": "<superproject sha, or 'dev'>",
      "wheels":  [ {"package": "...", "filename": "...", "version": "...",
                    "source_sha": "...", "sha256": "...", "bytes": 0} ],
      "sources": [ {"path": "assets/shims/web_serial_shim.py", "sha256": "..."},
                   {"path": "assets/python/web_bridge.py",     "sha256": "..."},
                   {"path": "assets/python/praxis/interactive.py", "sha256": "..."} ] }

    # ONLY under --with-models (P2.7a): wheels-shaped entries for the
    # gitignored web-repl/vendor/models/ FunctionGemma ONNX export.
    # Default manifests carry no "models" key whatsoever (AC-11 discipline:
    # a default manifest stays byte-identical for identical inputs).
    "models":  [ {"name": "functiongemma-270m-it-q4f16", "filename": "functiongemma-270m-it-onnx-q4f16/onnx/model_q4f16.onnx",
                  "source_sha": "<hub revision>", "sha256": "...", "bytes": 0} ]

**No source file is ever stamped.** The expected sha256 values live only in
this generated file -- that property is what keeps edit->reload fast:
regenerating a ~15-entry JSON is milliseconds.

House rules: uv-run only, argparse + logging, narrow runs, fail loud.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path

logger = logging.getLogger("build_manifest")

# --- fixed layout, overridable for testing ----------------------------------
_THIS_FILE = Path(__file__).resolve()
DEFAULT_WEB_REPL_ROOT = _THIS_FILE.parents[1]
DEFAULT_REPO_ROOT = _THIS_FILE.parents[2]

# Directories under overlay/assets/ that are walked for the "sources" array.
# ADR Sec 2.1 canonical tree: shims/ and python/ (which nests praxis/ and
# experimental/). wheels/ is handled separately (it is the "wheels" array,
# and it is where manifest.json itself is written).
SOURCE_SUBDIRS = ("shims", "python")

#: FR-12/D2: the Coxswain asset directory is sha-tracked in the manifest ONLY
#: under --with-coxswain (a default build's manifest carries no coxswain entry
#: whatsoever -- AC-11's path-substring clause). These files are static browser
#: assets, not bootstrap-fetched Python sources, so they live in a SEPARATE key
#: the python bootstrap loader never reads -- adding them to `sources` would
#: make transport.py fetch JS/CSS into the Pyodide VFS for nothing.
COXSWAIN_ASSET_SUBDIR = "coxswain"
COXSWAIN_ASSET_SUFFIXES = {".js", ".css"}

#: P2.7a: model entries come from fetch_models.MODEL_FILE_PINS -- the SAME pin
#: table the fetch script verifies downloads against, so the two halves cannot
#: drift about what is expected on disk. Unlike wheels, generation VERIFIES
#: every file's bytes against its pin (fail loud): a silently truncated 426 MB
#: download must never earn a manifest entry.

# Directory names to always skip while walking for sources -- never fetched,
# never part of the contract, and would silently bloat/drift the manifest.
_SKIP_DIR_NAMES = {"__pycache__"}
_SKIP_SUFFIXES = {".pyc", ".pyo"}

DEV_SENTINEL = "dev"

# package -> (build-info-module-relative-path, field name) for extracting a
# wheel's source_sha from its own embedded build-info file. Only pylabrobot
# has one today (written by build_wheels.py's write_build_info()). Anything
# not in this table gets source_sha: null -- e.g. pylibftdi, whose
# provenance is genuinely unknown (wheel spec OQ-6); do not invent one.
_BUILD_INFO_FIELD = {
    "pylabrobot": ("_praxis_build_info.py", "PLR_SOURCE_SHA"),
}
# Anchored, so a stray substring match elsewhere in the file can't be picked
# up, and so it captures the whole hex string rather than one character (the
# wheel spec calls out this exact prior bug for its own BUILD_ID regex).
_FIELD_RE_TMPL = r"^{field}\s*=\s*['\"]([0-9a-f]{{7,40}})['\"]\s*$"


class ManifestError(RuntimeError):
    """Raised for any condition that must fail manifest generation loudly."""


# --- hashing / fs helpers ----------------------------------------------------


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_head(repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


# --- wheels array -------------------------------------------------------------


def _extract_source_sha(wheel_path: Path, package: str) -> str | None:
    """Read the package's own embedded build-info file out of the built wheel
    and pull its source-sha field via an anchored regex (never ``exec`` --
    the manifest generator has no need to run untrusted-by-construction wheel
    contents, and a static read is enough here).

    Returns ``None`` (never a guess) when *package* has no known build-info
    file -- currently true for every wheel except pylabrobot.
    """
    entry = _BUILD_INFO_FIELD.get(package)
    if entry is None:
        return None
    info_basename, field = entry
    pattern = re.compile(_FIELD_RE_TMPL.format(field=re.escape(field)), re.MULTILINE)
    with zipfile.ZipFile(wheel_path) as zf:
        candidates = [n for n in zf.namelist() if n.endswith("/" + info_basename)]
        if not candidates:
            raise ManifestError(
                f"{wheel_path.name}: expected to find a '*/{info_basename}' member "
                f"(package={package!r}) to read {field} from, found none. Member "
                f"list sample: {zf.namelist()[:10]}"
            )
        text = zf.read(candidates[0]).decode("utf-8")
    match = pattern.search(text)
    if match is None:
        raise ManifestError(
            f"{wheel_path.name}: {candidates[0]} did not contain an anchored "
            f"'{field} = \"...\"' assignment -- cannot extract source_sha."
        )
    return match.group(1)


def _parse_wheel_filename(wheel_path: Path) -> tuple[str, str]:
    """Return (package, version) for a wheel filename, preferring the
    ``packaging`` library (already a transitive dependency here) and falling
    back to a manual split against the standard 5-field wheel filename shape
    if it is ever unavailable.
    """
    try:
        from packaging.utils import parse_wheel_filename

        name, version, _build, _tags = parse_wheel_filename(wheel_path.name)
        return name, str(version)
    except Exception as exc:
        logger.debug("packaging.utils.parse_wheel_filename failed (%s); falling back", exc)
    parts = wheel_path.stem.split("-")
    if len(parts) < 5:
        raise ManifestError(
            f"{wheel_path.name}: does not look like a standard "
            "<name>-<version>-<pytag>-<abitag>-<platform>.whl filename"
        )
    return parts[0], parts[1]


def collect_wheels(wheels_dir: Path) -> list[dict]:
    entries = []
    for wheel_path in sorted(wheels_dir.glob("*.whl")):
        package, version = _parse_wheel_filename(wheel_path)
        entries.append(
            {
                "package": package,
                "filename": wheel_path.name,
                "version": version,
                "source_sha": _extract_source_sha(wheel_path, package),
                "sha256": _sha256_file(wheel_path),
                "bytes": wheel_path.stat().st_size,
            }
        )
    return entries


# --- coxswain assets array (flag-gated) -----------------------------------------


def collect_coxswain_assets(overlay_dir: Path) -> list[dict]:
    """sha256 entries for every staged Coxswain browser asset under
    ``overlay/assets/coxswain/`` (*.js / *.css), keyed relative to overlay/
    like the sources entries. Enumerated from disk, never hardcoded."""
    subdir = overlay_dir / "assets" / COXSWAIN_ASSET_SUBDIR
    if not subdir.is_dir():
        raise ManifestError(
            f"--with-coxswain was passed but {subdir} does not exist -- there are "
            "no Coxswain assets to track. Refusing to write an empty claim."
        )
    entries = []
    for path in sorted(subdir.rglob("*")):
        if any(part in _SKIP_DIR_NAMES for part in path.relative_to(subdir).parts[:-1]):
            continue
        if path.suffix.lower() not in COXSWAIN_ASSET_SUFFIXES:
            continue
        rel = path.relative_to(overlay_dir).as_posix()
        entries.append({"path": rel, "sha256": _sha256_file(path)})
    if not entries:
        raise ManifestError(
            f"{subdir} contains no *.js/*.css assets -- refusing to track nothing "
            "under --with-coxswain."
        )
    entries.sort(key=lambda e: e["path"])
    return entries


# --- models array (flag-gated, P2.7a) -------------------------------------------


def collect_models(web_repl_root: Path) -> list[dict]:
    """Wheels-shaped sha256 entries for every pinned FunctionGemma model file
    under ``web-repl/vendor/models/`` (gitignored; fetched by fetch_models.py).
    Verifies each file against fetch_models' upstream pin table at GENERATION
    time -- a drifted/truncated download fails loudly here instead of earning a
    manifest entry it cannot vouch for."""
    import fetch_models  # same directory; sys.path[0] is this script's dir

    models_dir = web_repl_root / "vendor" / "models"
    if not models_dir.is_dir():
        raise ManifestError(
            f"--with-models was passed but {models_dir} does not exist -- run "
            f"scripts/fetch_models.py --models first. Refusing to write a models "
            "array that claims files which are not on disk."
        )
    problems: list[str] = []
    entries = fetch_models.model_manifest_entries()
    by_filename = {e["filename"]: e for e in entries}
    for repo_rel in sorted(fetch_models.MODEL_FILE_PINS):
        filename = f"{fetch_models.MODEL_DIR_NAME}/{repo_rel}"
        entry = by_filename[filename]
        path = fetch_models.model_dest_dir(models_dir) / repo_rel
        if not path.is_file():
            problems.append(f"model file missing on disk: {path}")
            continue
        try:
            fetch_models._verify_digest(path, fetch_models.MODEL_FILE_PINS[repo_rel])
        except fetch_models.FetchError as exc:
            problems.append(str(exc))
            continue
        if entry["sha256"] is None:
            # Plain-text files are pinned upstream by git blob sha1 (the Hub's
            # digest for non-LFS content); the browser contract needs sha256,
            # so take it from the JUST-VERIFIED disk bytes.
            entry["sha256"] = _sha256_file(path)
    if problems:
        raise ManifestError(
            "--with-models: fetched model files fail their upstream pins:\n  "
            + "\n  ".join(problems)
            + "\nRe-run scripts/fetch_models.py --models to repair."
        )
    return [by_filename[f"{fetch_models.MODEL_DIR_NAME}/{r}"] for r in sorted(fetch_models.MODEL_FILE_PINS)]


# --- sources array -------------------------------------------------------------


def collect_sources(overlay_dir: Path) -> list[dict]:
    """Walk ``overlay/assets/{shims,python}`` for every ``*.py`` file and
    return sha256 entries, keyed on a path relative to ``overlay/`` (matching
    the ADR's example: ``assets/shims/web_serial_shim.py``).

    Enumerated from what actually exists on disk -- never a hardcoded list,
    per the task brief: a hardcoded list silently goes stale the moment a
    file is added or removed. A 0-byte file (e.g. ``praxis/__init__.py``,
    ADR Sec 2.4) is included: D2 covers the file's PRESENCE, and presence is
    exactly what a 0-byte sha256 entry proves.
    """
    entries = []
    assets_dir = overlay_dir / "assets"
    for subdir_name in SOURCE_SUBDIRS:
        subdir = assets_dir / subdir_name
        if not subdir.is_dir():
            logger.warning(
                "overlay/assets/%s does not exist yet -- contributing 0 source "
                "entries from it. This is expected before the loose-file move "
                "tasks (ADR Sec 2.1) have run; it is not an error here.",
                subdir_name,
            )
            continue
        for path in sorted(subdir.rglob("*.py")):
            if any(part in _SKIP_DIR_NAMES for part in path.relative_to(subdir).parts[:-1]):
                continue
            if path.suffix in _SKIP_SUFFIXES:
                continue
            if subdir_name == "shims" and path.name == "__init__.py":
                # Shims are imported as bare top-level modules, one at a time,
                # via stages.import_shim_class("web_serial_shim", ...) ->
                # importlib.import_module("web_serial_shim") -- never as
                # `import shims.web_serial_shim` or `from shims import ...`
                # (grep the tree: nothing does). A shims/__init__.py therefore
                # serves no purpose once fetched: transport.py's
                # dest_for_source() strips SHIMS_PREFIX unconditionally, so
                # this path alone would land at the VFS root as bare
                # `__init__.py`, silently turning the bootstrap's own working
                # directory into a Python package. Contrast
                # assets/python/praxis/__init__.py, which IS required (praxis
                # is imported as a real package, ADR Sec 2.4) and is left
                # alone -- this skip is scoped to shims/ only.
                continue
            rel = path.relative_to(overlay_dir).as_posix()
            entries.append({"path": rel, "sha256": _sha256_file(path)})
    # Stable order regardless of directory traversal order across platforms.
    entries.sort(key=lambda e: e["path"])
    return entries


# --- manifest assembly + atomic write ------------------------------------------


def build_manifest(
    *, web_repl_root: Path, repo_root: Path, dev: bool, with_coxswain: bool = False,
    with_models: bool = False,
) -> dict:
    overlay_dir = web_repl_root / "overlay"
    wheels_dir = overlay_dir / "assets" / "wheels"
    if not wheels_dir.is_dir():
        raise ManifestError(
            f"{wheels_dir} does not exist -- run build_wheels.py first "
            "(it produces the *.whl files this manifest describes)."
        )
    wheels = collect_wheels(wheels_dir)
    if not wheels:
        raise ManifestError(
            f"{wheels_dir} exists but contains no *.whl files -- nothing to "
            "manifest. Run build_wheels.py first."
        )
    sources = collect_sources(overlay_dir)
    praxis_git_sha = DEV_SENTINEL if dev else _git_head(repo_root)
    manifest = {
        "praxis_git_sha": praxis_git_sha,
        "wheels": wheels,
        "sources": sources,
    }
    if with_coxswain:
        # Key present ONLY under the flag: a default manifest is byte-identical
        # to its pre-coxswain shape for identical inputs (AC-11/RISK-14).
        manifest["coxswain_assets"] = collect_coxswain_assets(overlay_dir)
    if with_models:
        # P2.7a, same flag-gated discipline: absent (never empty) by default.
        manifest["models"] = collect_models(web_repl_root)
    return manifest


def write_manifest_atomic(manifest: dict, dest: Path) -> None:
    """Write *manifest* to *dest* via a temp file in the SAME directory,
    then ``os.replace`` -- a half-written manifest is a boot failure with a
    confusing signature (ADR Sec 4.3, "preserved verbatim").
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=".manifest-", suffix=".json.tmp", dir=str(dest.parent)
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(manifest, f, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        # mkstemp creates the file 0600 -- this is a static asset meant to be
        # served, not a secret, so widen it to the usual 0644 before the
        # atomic rename publishes it under its real name.
        os.chmod(tmp_path, 0o644)
        os.replace(tmp_path, dest)  # atomic on POSIX and Windows alike
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise
    logger.info("wrote %s (%d wheel(s), %d source(s))", dest, len(manifest["wheels"]), len(manifest["sources"]))


# --- D2 verification (also used by tests) --------------------------------------


def verify_manifest(manifest: dict, *, web_repl_root: Path) -> list[str]:
    """Recompute every entry's sha256/bytes against disk and return a list of
    human-readable mismatch descriptions (empty list == clean). Pure check,
    no mutation -- this is what a boot-time D2 check does, minus the raise.
    """
    overlay_dir = web_repl_root / "overlay"
    wheels_dir = overlay_dir / "assets" / "wheels"
    problems: list[str] = []
    for entry in manifest["wheels"]:
        path = wheels_dir / entry["filename"]
        if not path.is_file():
            problems.append(f"wheel missing on disk: {entry['filename']}")
            continue
        actual_sha = _sha256_file(path)
        if actual_sha != entry["sha256"]:
            problems.append(
                f"wheel sha256 mismatch: {entry['filename']} "
                f"manifest={entry['sha256']} disk={actual_sha}"
            )
        actual_bytes = path.stat().st_size
        if actual_bytes != entry["bytes"]:
            problems.append(
                f"wheel size mismatch: {entry['filename']} "
                f"manifest={entry['bytes']} disk={actual_bytes}"
            )
    for entry in manifest["sources"]:
        path = overlay_dir / entry["path"]
        if not path.is_file():
            problems.append(f"source missing on disk: {entry['path']}")
            continue
        actual_sha = _sha256_file(path)
        if actual_sha != entry["sha256"]:
            problems.append(
                f"source sha256 mismatch: {entry['path']} "
                f"manifest={entry['sha256']} disk={actual_sha}"
            )
    for entry in manifest.get("coxswain_assets", []):
        path = overlay_dir / entry["path"]
        if not path.is_file():
            problems.append(f"coxswain asset missing on disk: {entry['path']}")
            continue
        actual_sha = _sha256_file(path)
        if actual_sha != entry["sha256"]:
            problems.append(
                f"coxswain asset sha256 mismatch: {entry['path']} "
                f"manifest={entry['sha256']} disk={actual_sha}"
            )
    for entry in manifest.get("models", []):
        path = web_repl_root / "vendor" / "models" / entry["filename"]
        if not path.is_file():
            problems.append(f"model missing on disk: {entry['filename']}")
            continue
        actual_sha = _sha256_file(path)
        if actual_sha != entry["sha256"]:
            problems.append(
                f"model sha256 mismatch: {entry['filename']} "
                f"manifest={entry['sha256']} disk={actual_sha}"
            )
        actual_bytes = path.stat().st_size
        if actual_bytes != entry["bytes"]:
            problems.append(
                f"model size mismatch: {entry['filename']} "
                f"manifest={entry['bytes']} disk={actual_bytes}"
            )
    return problems


# --- CLI -----------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--with-coxswain",
        action="store_true",
        help="Also sha-track overlay/assets/coxswain/*.{js,css} under the "
        "manifest's 'coxswain_assets' key. Without this flag the generated "
        "manifest carries no coxswain entries at all (FR-12/AC-11). Must match "
        "the flag passed to build_repl.py.",
    )
    parser.add_argument(
        "--with-models",
        action="store_true",
        help="Also sha-track web-repl/vendor/models/ under the manifest's "
        "'models' key (wheels-shaped; P2.7a). Verifies every pinned file "
        "against its upstream digest first and fails loud on drift. Without "
        "this flag the manifest carries no models key at all.",
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help='Write praxis_git_sha: "dev" instead of the real superproject '
        "HEAD sha -- pairs with inject_shell.py --dev. The D1 assert is "
        'skipped only when BOTH sides read "dev" (an emergent property of '
        "plain string equality, not a special case -- see stages.py "
        "assert_praxis_git_sha).",
    )
    parser.add_argument(
        "--web-repl-root",
        type=Path,
        default=DEFAULT_WEB_REPL_ROOT,
        help="Override web-repl/ root (testing only).",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Override superproject root used for `git rev-parse HEAD` (testing only).",
    )
    parser.add_argument(
        "--print",
        dest="do_print",
        action="store_true",
        help="Print the generated manifest to stdout after writing it.",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Instead of generating, read the existing manifest.json and verify "
        "every sha256/bytes entry against disk (D2, offline). Exits 1 naming "
        "every mismatch.",
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
    dest = web_repl_root / "overlay" / "assets" / "wheels" / "manifest.json"

    if args.verify:
        if not dest.is_file():
            logger.error("%s does not exist -- nothing to verify", dest)
            return 1
        manifest = json.loads(dest.read_text())
        problems = verify_manifest(manifest, web_repl_root=web_repl_root)
        if problems:
            for p in problems:
                logger.error("D2 MISMATCH: %s", p)
            return 1
        logger.info("D2 OK: %d wheel(s), %d source(s) all match disk", len(manifest["wheels"]), len(manifest["sources"]))
        return 0

    try:
        manifest = build_manifest(
            web_repl_root=web_repl_root,
            repo_root=args.repo_root.resolve(),
            dev=args.dev,
            with_coxswain=args.with_coxswain,
            with_models=args.with_models,
        )
        write_manifest_atomic(manifest, dest)
    except ManifestError as exc:
        logger.error("%s", exc)
        return 1

    if args.do_print:
        print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
