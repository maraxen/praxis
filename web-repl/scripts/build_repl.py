#!/usr/bin/env python3
"""Fail-loud orchestrator that builds the standalone praxis web REPL site.

Runs ``jupyter lite build`` (as ``uv run python -m jupyterlite_core`` --
**NEVER** the ``jupyter lite`` console script; its shebang points at
``/home/marielle/projects/awesomation/.venv/bin/python`` and exits 127, a
real reproduced failure, not a precaution), then stages ``overlay/``,
``bootstrap/``, and ``shell/`` into the output directory -- none of which
JupyterLite's own build knows anything about -- then regenerates
``manifest.json`` and injects the D1 shell sha, and finally asserts the
result is not hollow.

Per ADR ``.praxia/docs/decisions/260817_repl-layout-and-delivery-mechanism.md``
Sec 4.2: "Only ``overlay/`` reaches ``dist/`` (``build_repl.py --out
web-repl/dist``)" -- an earlier design placed the vendored visualizer at
``web-repl/`` root and no script staged it, so it never reached the page.
This script is where that staging actually happens, for ``overlay/assets/``
AND for the two loose top-level trees a real boot also needs but that live
outside ``overlay/`` on disk: ``bootstrap/`` (fetched by
``praxis_bootstrap.py``'s own two-file self-bootstrap, ADR Sec 2.3's D2
exception -- it cannot be manifest-driven because it IS the code that makes
manifest-driven fetching possible) and ``shell/praxis-shell.js`` (D1's
shell-injected half, deliberately kept outside the JupyterLite asset set).

**Layout decisions this script owns (not yet exercised by any browser run --
see this task's report for the honest boundary this crosses):**

- ``overlay/assets/`` -> ``<out>/assets/`` and ``bootstrap/*.py`` ->
  ``<out>/bootstrap/``, both as siblings of JupyterLite's own ``build/``
  and ``static/`` at the OUTPUT ROOT -- matching the pattern JupyterLite
  itself uses for shared, not-per-app assets (verified: a real build's
  vendored Pyodide lands at ``<out>/static/pyodide/``, not nested under any
  one app). ``praxis_bootstrap.py``'s ``host_root`` parameter is not yet
  wired by any caller (its own docstring: "the minimal external bootstrap
  snippet ... is Phase 5, out of this task's scope") -- this placement is
  this script's best-evidence guess for what that snippet should assume,
  not a proven contract. Flagged for whoever writes that snippet next.
- ``shell/praxis-shell.js`` -> ``<out>/shell/praxis-shell.js``. ONE shared
  copy at the output root, referenced as ``../shell/praxis-shell.js`` from
  every entry's ``index.html`` one directory down. The browser resolves that
  src directly against the page URL (no PageConfig/base-tag machinery has
  loaded when it runs), so the path is forced by arithmetic, not chosen.
  Previously the copy was nested under ``lab/`` with a ``./shell/...`` src,
  so only ``lab/`` could carry the shell -- and ``repl/``, the entry whose
  ``?code=&execute=1`` the smoke harness drives, had none, meaning D1 could
  only ever fail closed there. ``inject_shell.py`` now injects into EVERY
  ``dist/*/index.html`` carrying the anchor, and its own module docstring
  and this one now agree.

**Pyodide mode (ADR Sec 7, U18/U19 -- "whether Pyodide is vendored for
offline operation" -- open there, decided HERE for what this script
actually does):** GATE G5 requires
``grep -rl 'cdn.jsdelivr.net' web-repl/dist | wc -l`` to be **0**. The only
way to get anywhere near that is the vendored copy
(``fetch_pyodide.py``'s output under ``web-repl/vendor/``), passed to
``jupyter lite build`` as ``--PyodideAddon.pyodide_url=vendor/pyodide-<v>.tar.bz2``
-- a LOCAL PATH override that wins over the CDN URL already pinned in
``jupyter_lite_config.json`` (traitlets CLI args beat config-file values).
That file is read, never rewritten (a different task owns it). **Verified
against a real build (2026-08-18): even fully vendored, the string
``cdn.jsdelivr.net`` still appears in 8 files** -- Pyodide's own compiled
``pyodide.mjs`` bakes in ``https://cdn.jsdelivr.net/pyodide/v${ver}/full/``
as micropip's default package-index fallback, and the
``@jupyterlite/pyodide-kernel-extension`` bundle bakes in the same URL as an
unused settings default (``a.pyodideUrl||"https://cdn...`` -- the `||`
never fires once ``pyodideUrl`` is set, which the build's own
``patch:jupyter-lite.json`` step does). Both are dead fallback text inside
third-party compiled artifacts, not a live network call this build makes --
but GATE G5's grep cannot distinguish that from real usage, and this script
does not attempt to patch vendored third-party JS to force the count to
zero (too fragile, and not this task's to fix). Report the real grep result
honestly; do not paper over it. ``--allow-cdn`` exists for local iteration
and makes no attempt to satisfy G5's zero-cdn check.

**Manifest freshness:** this script always regenerates
``overlay/assets/wheels/manifest.json`` via ``build_manifest.py`` before
staging (threading ``--dev`` through if given) -- "wire your half" of ADR
Sec 2.3's D1 escape hatch: ``--dev`` makes BOTH ``build_manifest.py --dev``
(manifest's ``praxis_git_sha: "dev"``) and ``inject_shell.py --dev``
(shell's injected ``"dev"``) fire together, so the boot-time assert is
skipped only when both genuinely read ``"dev"`` -- never weakened for the
real path, where both independently compute the same ``git rev-parse HEAD``.

**``--debug-skip-jupyterlite``:** genuine failure injection for GATE G5, not
a stub. It skips the ``jupyter lite build`` subprocess entirely, leaving
``<out>/build/`` absent -- the SAME structural assertion that guards a real
hollow build (``ls <out>/build/*.js`` must be non-empty) then fires and
exits nonzero with ``BUILD ASSERTION FAILED`` in the message, by construction,
not a special-cased check.

House rules: uv-run only, argparse + logging, narrow runs, fail loud.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import shutil
import subprocess
import time
from pathlib import Path

import fetch_vendored_wheels  # same directory; sys.path[0] is this script's dir
import fetch_pyodide  # same directory; sys.path[0] is this script's dir

logger = logging.getLogger("build_repl")

_THIS_FILE = Path(__file__).resolve()
SCRIPTS_DIR = _THIS_FILE.parent
WEB_REPL_ROOT = SCRIPTS_DIR.parent
REPO_ROOT = WEB_REPL_ROOT.parent

DEFAULT_OUT_DIR = WEB_REPL_ROOT / "dist"
VENDOR_DIR = WEB_REPL_ROOT / "vendor"
CONFIG_PATH = WEB_REPL_ROOT / "jupyter_lite_config.json"
OVERLAY_ASSETS_DIR = WEB_REPL_ROOT / "overlay" / "assets"
BOOTSTRAP_DIR = WEB_REPL_ROOT / "bootstrap"
SHELL_DIR = WEB_REPL_ROOT / "shell"

_BOOTSTRAP_FILES = ("praxis_bootstrap.py", "stages.py", "transport.py")

_SKIP_DIR_NAMES = {"__pycache__"}
_SKIP_FILE_SUFFIXES = {".pyc", ".pyo"}
_SKIP_FILE_NAMES = {".gitkeep"}


class BuildError(RuntimeError):
    """Raised for any condition that must fail this build loudly."""


class BuildAssertionError(BuildError):
    """Raised for a post-build structural check failure -- GATE G5's
    ``--debug-skip-jupyterlite`` expects to see this class's message.
    """


# --- subprocess helpers -------------------------------------------------


def _uv_run(args: list[str], *, cwd: Path, timeout: float, log_path: Path | None = None) -> None:
    """Run ``uv run --project <REPO_ROOT> python <args>`` from *cwd*.

    Captures combined output (long-running steps like ``jupyter lite build``
    print a lot -- house rule: redirect to a log file, grep for signal) and
    writes it to *log_path* if given, always logging a short tail on
    success and the full output on failure.
    """
    cmd = ["uv", "run", "--project", str(REPO_ROOT), "python", *args]
    logger.info("+ %s  (cwd=%s)", " ".join(cmd), cwd)
    t0 = time.monotonic()
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired as exc:
        raise BuildError(f"{' '.join(cmd)} timed out after {timeout}s") from exc
    elapsed = time.monotonic() - t0
    combined = (result.stdout or "") + (result.stderr or "")
    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(combined)
    if result.returncode != 0:
        tail = "\n".join(combined.splitlines()[-80:])
        raise BuildError(
            f"{' '.join(cmd)} FAILED (exit {result.returncode}, {elapsed:.1f}s)."
            + (f" Full log: {log_path}" if log_path else "")
            + f"\n--- last 80 lines ---\n{tail}"
        )
    logger.info("OK (%.1fs)%s", elapsed, f" -- full log: {log_path}" if log_path else "")


# --- step 1: jupyter lite build ------------------------------------------


def resolve_pyodide_arg(*, allow_cdn: bool) -> str | None:
    """Return the ``--PyodideAddon.pyodide_url`` value to pass, or ``None``
    to leave ``jupyter_lite_config.json``'s own (CDN) value in force.

    Note what ``None`` does NOT mean: it does not produce a site that loads
    Pyodide from a CDN at runtime. ``PyodideAddon`` treats ``pyodide_url`` as a
    SOURCE, vendoring whatever it points at into ``static/pyodide/`` and
    rewriting the runtime ``pyodideUrl`` to that local path. Building a genuinely
    CDN-loading site would need a post-build step that rewrites ``pyodideUrl``
    back to the remote URL and deletes ``static/pyodide/`` -- filed as debt, not
    implemented.

    Reuses ``fetch_pyodide.read_pinned_version`` rather than re-parsing the
    config -- one parser for "what version does this build target", not two
    that can drift against each other.
    """
    if allow_cdn:
        logger.warning(
            "--allow-cdn: sourcing Pyodide from the CDN URL pinned in "
            "jupyter_lite_config.json instead of the vendored tarball. The BUILT "
            "SITE still loads Pyodide locally -- PyodideAddon vendors whatever URL "
            "it is given into static/pyodide/ -- so this neither produces a "
            "CDN-loading site nor shrinks the artifact. assert_pyodide_is_local is "
            "skipped in this mode even though it would pass."
        )
        return None
    version = fetch_pyodide.read_pinned_version(CONFIG_PATH)
    vendor_path = VENDOR_DIR / f"pyodide-{version}.tar.bz2"
    if not vendor_path.is_file():
        raise BuildError(
            f"{vendor_path} not found. Run "
            f"`uv run python {SCRIPTS_DIR / 'fetch_pyodide.py'}` first to vendor "
            f"Pyodide {version}, or pass --allow-cdn to build against the CDN "
            "URL instead (GATE G5's zero-cdn.jsdelivr.net check will then fail)."
        )
    logger.info("using vendored Pyodide: %s", vendor_path)
    # Local-path form (not a URL): resolved by PyodideAddon relative to
    # lite_dir, i.e. WEB_REPL_ROOT -- see jupyterlite_pyodide_kernel's own
    # addons/pyodide.py:cache_pyodide(). Verified against a real build.
    return f"vendor/pyodide-{version}.tar.bz2"


# jupyterlite drives its build with doit, which caches per-task state here (next to
# --lite-dir). The cache is NOT inside out_dir, so `rm -rf dist` does not clear it.
DOIT_DB_PATH = WEB_REPL_ROOT / ".jupyterlite.doit.db"


def discard_doit_cache() -> None:
    """Delete doit's task-state cache before every build.

    WHY THIS IS UNCONDITIONAL, not an optimisation to skip:

    PyodideAddon.post_build() writes `litePluginSettings[...].pyodideUrl` into
    jupyter-lite.json from a doit task whose only `file_dep` is the extracted
    `static/pyodide/pyodide.mjs`. When the cache says that dep is unchanged, doit
    skips the task -- but jupyter-lite.json is REGENERATED from scratch by an
    earlier addon in the same build. Skipped patch + regenerated config = a
    jupyter-lite.json with no `pyodideUrl` at all, which silently falls back to the
    kernel schema's default: https://cdn.jsdelivr.net/... (kernel.v0.schema.json).

    The failure is invisible in every way that matters. The build exits 0.
    `dist/static/pyodide/` is fully populated (423 files), so vendoring LOOKS
    successful. The site boots fine -- as long as the CDN is reachable, which it is
    on any developer machine. Measured 260819: a site built this way fetched
    pyodide.mjs, pyodide-lock.json, python_stdlib.zip, pyodide.asm.wasm and ~10
    package wheels from cdn.jsdelivr.net on every single boot, while the vendored
    copy sat unused. Only the --offline gate exposed it.

    `rm -rf dist` does NOT prevent this (verified: a clean dist with a stale cache
    still produced no pyodideUrl), so GATE G5's clean-build line is not sufficient
    on its own and this has to be handled here, in the build itself.
    """
    if DOIT_DB_PATH.exists():
        DOIT_DB_PATH.unlink()
        logger.info("discarded stale doit cache %s", DOIT_DB_PATH)
    # doit may also use dbm-style sidecars depending on backend.
    for sidecar in sorted(WEB_REPL_ROOT.glob(".jupyterlite.doit.db.*")):
        sidecar.unlink()
        logger.info("discarded stale doit cache sidecar %s", sidecar)


def assert_pyodide_is_local(out_dir: Path) -> None:
    """Fail the build if the site would fetch Pyodide from a CDN at runtime.

    This is the assertion that would have caught the silent doit-cache failure
    above on the day it started. It checks the RUNTIME config -- the only thing
    the browser actually reads -- not the presence of the extracted files, which
    is exactly the signal that misled us.
    """
    config_path = out_dir / "jupyter-lite.json"
    if not config_path.is_file():
        raise BuildAssertionError(
            f"BUILD ASSERTION FAILED: {config_path} does not exist."
        )
    settings = (
        json.loads(config_path.read_text())
        .get("jupyter-config-data", {})
        .get("litePluginSettings", {})
        .get("@jupyterlite/pyodide-kernel-extension:kernel", {})
    )
    url = settings.get("pyodideUrl")
    if not url:
        raise BuildAssertionError(
            "BUILD ASSERTION FAILED: jupyter-lite.json sets no `pyodideUrl`, so the "
            "kernel will silently use the schema default "
            "(https://cdn.jsdelivr.net/...) and fetch ~30 MB of Pyodide per boot "
            "regardless of what is in dist/static/pyodide/. Usual cause: a stale "
            f"{DOIT_DB_PATH.name} made doit skip PyodideAddon's patch task -- see "
            "discard_doit_cache()."
        )
    if "://" in url:
        raise BuildAssertionError(
            f"BUILD ASSERTION FAILED: `pyodideUrl` is remote ({url!r}). The site must "
            "load Pyodide from its own origin. Pass --allow-cdn only if you "
            "deliberately want a CDN build."
        )
    if not (out_dir / url.lstrip("./")).is_file():
        raise BuildAssertionError(
            f"BUILD ASSERTION FAILED: `pyodideUrl` is {url!r} but "
            f"{out_dir / url.lstrip('./')} does not exist."
        )
    logger.info("pyodide is local: pyodideUrl=%s", url)


def assert_completion_autocompletion(out_dir: Path) -> None:
    """Fail the build if as-you-type completion did not reach the runtime config.

    JupyterLab plugin settings do NOT travel in `litePluginSettings` -- that key is
    for LITE plugins (the Pyodide kernel). They travel in `settingsOverrides`,
    which jupyterlite_core merges from any `overrides.json` and validates against
    `build/schemas/<ext>/<plugin>.json` (addons/settings.py:54-125).

    Two channels in one file, and each silently ignores a key meant for the other.
    A setting misfiled into `litePluginSettings` yields a site that boots fine,
    completes on Tab, and simply never completes as you type -- indistinguishable
    by eye from the default we are trying to change. So assert on the RUNTIME
    config, which is the only thing the browser reads, not on the source file.
    """
    config_path = out_dir / "jupyter-lite.json"
    if not config_path.is_file():
        raise BuildAssertionError(
            f"BUILD ASSERTION FAILED: {config_path} does not exist."
        )
    plugin = "@jupyterlab/completer-extension:manager"
    overrides = (
        json.loads(config_path.read_text())
        .get("jupyter-config-data", {})
        .get("settingsOverrides", {})
        .get(plugin, {})
    )
    if overrides.get("autoCompletion") is not True:
        raise BuildAssertionError(
            "BUILD ASSERTION FAILED: jupyter-lite.json does not set "
            f"`settingsOverrides[{plugin!r}].autoCompletion = true`, so the REPL "
            "falls back to the schema default (false) and completes only on an "
            "explicit Tab. Usual cause: the key was filed under "
            "`litePluginSettings`, which is the LITE-plugin channel and ignores it."
        )
    schema = (
        out_dir / "build" / "schemas" / "@jupyterlab" / "completer-extension" / "manager.json"
    )
    if not schema.is_file():
        raise BuildAssertionError(
            f"BUILD ASSERTION FAILED: {schema} is missing, so the completer plugin "
            "is not in this build at all and the override above configures nothing."
        )
    logger.info("as-you-type completion enabled: %s.autoCompletion=true", plugin)


def assert_praxis_boot_shipped(out_dir: Path) -> None:
    """Fail the build if the fresh-notebook bootstrap is not reachable.

    `praxis_boot.py` is what lets a brand-new notebook come up in two lines
    (`import praxis_boot` / `await praxis_boot.setup()`). It is importable for
    one specific reason: the kernel mounts the JupyterLite contents drive at
    `/drive`, runs with that as its working directory, and `sys.path` starts
    with `''`. So the file has to be BOTH staged into `files/` and listed in the
    static contents index -- the index is a build artifact, and a file missing
    from it does not appear in the drive no matter what is on disk.

    Both halves are checked because they fail differently and neither is
    visible from the other: a staged-but-unindexed file is invisible to the
    kernel, and an indexed-but-missing file yields `FileNotFoundError:
    /drive/praxis_boot.py` at import. Measured 2026-08-24 -- deleting the staged
    file while the index still listed it produced exactly that second shape.
    """
    staged = out_dir / "files" / "praxis_boot.py"
    if not staged.is_file():
        raise BuildAssertionError(
            f"BUILD ASSERTION FAILED: {staged} does not exist, so a fresh notebook "
            "cannot `import praxis_boot` and every new notebook is back to a "
            "hand-pasted loader fetch. Expected it to be staged from web-repl/files/."
        )

    index_path = out_dir / "api" / "contents" / "all.json"
    if not index_path.is_file():
        raise BuildAssertionError(
            f"BUILD ASSERTION FAILED: {index_path} does not exist, so the contents "
            "index was never generated and the kernel's /drive mount will be empty."
        )
    listed = {
        entry.get("path") for entry in json.loads(index_path.read_text()).get("content", [])
    }
    if "praxis_boot.py" not in listed:
        raise BuildAssertionError(
            "BUILD ASSERTION FAILED: praxis_boot.py is staged but MISSING from the "
            f"contents index {index_path} (which lists {sorted(listed)!r}). The index "
            "is a static build artifact, so an unindexed file never appears in the "
            "kernel's /drive mount and `import praxis_boot` fails despite the file "
            "being present on disk."
        )
    logger.info("fresh-notebook bootstrap shipped: files/praxis_boot.py staged and indexed")


def required_piplite_packages() -> tuple[str, ...]:
    """Runtime deps the browser needs that Pyodide does NOT bundle.

    `disablePyPIFallback: true` makes these unobtainable at runtime, so each must
    be vendored through PipliteAddon.piplite_urls. Read from
    ``web-repl/vendored_wheels.json`` rather than hardcoded here, so the pin table
    and this guard cannot drift into disagreeing about what is required -- the
    same duplicate-source-of-truth defect that made D3 report a covered module as
    uncovered (see test_contract_covers_imports.py).
    """
    return tuple(fetch_vendored_wheels.load_pins().get("required", ()))


def assert_required_piplite_wheels(out_dir: Path) -> None:
    """Fail the build if a required unbundled runtime dep is not vendored.

    `comm` is an ipykernel dependency present in NEITHER pyodide-lock.json nor the
    default piplite index. With `disablePyPIFallback: true` set in jupyter-lite.json,
    a missing wheel cannot be fetched at runtime -- piplite fails without even
    attempting a network request.

    This assertion exists because that failure is otherwise UNATTRIBUTED. Measured
    2026-08-20 by removing comm from piplite_urls and rebuilding: the build passed,
    `--probe` passed, and `--probe --offline` failed only as a bare 120s
    wait_for_function timeout. The kernel died in its Web Worker with the console
    ending at "Loaded micropip" -- no error naming comm, piplite, or any failed
    import, and zero failed requests (nothing ever reached the network to fail).

    Catching it here turns a silent two-minute browser timeout into an immediate
    build error naming the missing package.
    """
    index_path = out_dir / "pypi" / "all.json"
    if not index_path.is_file():
        raise BuildAssertionError(
            f"BUILD ASSERTION FAILED: {index_path} does not exist, so NO wheels are "
            "vendored for piplite. With disablePyPIFallback the kernel cannot fetch "
            f"them at runtime and will die silently in its worker. Required: "
            f"{', '.join(required_piplite_packages())}. Usual cause: "
            "scripts/fetch_vendored_wheels.py did not run, or PipliteAddon.piplite_urls "
            "in web-repl/jupyter_lite_config.json does not point at the fetched "
            "vendor/piplite-wheels/<filename>."
        )
    raw = json.loads(index_path.read_text())
    names = {str(k).lower().replace("_", "-") for k in raw} if isinstance(raw, dict) else set()
    names |= {
        w.name.split("-")[0].lower().replace("_", "-")
        for w in (out_dir / "pypi").glob("*.whl")
    }
    missing = [p for p in required_piplite_packages() if p.lower().replace("_", "-") not in names]
    if missing:
        raise BuildAssertionError(
            f"BUILD ASSERTION FAILED: required piplite wheel(s) not vendored: "
            f"{', '.join(missing)}. Found: {sorted(names) or 'nothing'}. These are not "
            "in pyodide-lock.json and disablePyPIFallback blocks the PyPI fallback, so "
            "the kernel will fail to start OFFLINE with no error naming the cause. Pin "
            "it in web-repl/vendored_wheels.json (name/version/filename/sha256) and add "
            "the matching vendor/piplite-wheels/<filename> path to "
            "PipliteAddon.piplite_urls; scripts/fetch_vendored_wheels.py fetches it. Do "
            "NOT commit the .whl -- R6/R8 require zero tracked wheels repo-wide."
        )
    logger.info("required piplite wheels vendored: %s", ", ".join(required_piplite_packages()))


def run_jupyterlite_build(*, out_dir: Path, pyodide_arg: str | None, log_path: Path) -> None:
    discard_doit_cache()
    args = [
        "-m",
        "jupyterlite_core",
        "build",
        "--lite-dir",
        str(WEB_REPL_ROOT),
        "--output-dir",
        str(out_dir),
    ]
    if pyodide_arg is not None:
        args.append(f"--PyodideAddon.pyodide_url={pyodide_arg}")
    # cwd=WEB_REPL_ROOT so jupyter_lite_config.json (traitlets, auto-loaded
    # from cwd by JupyterLite's own Application convention) is picked up --
    # --lite-dir alone does not do this, it only governs jupyter-lite.json
    # (schema-v0) content resolution.
    _uv_run(args, cwd=WEB_REPL_ROOT, timeout=900, log_path=log_path)


def assert_jupyterlite_output_not_hollow(out_dir: Path) -> None:
    """The one check GATE G5's ``--debug-skip-jupyterlite`` run depends on
    firing, and the one that protects a genuinely hollow real build too --
    same code path either way, no special-casing.
    """
    build_dir = out_dir / "build"
    js_files = sorted(build_dir.glob("*.js")) if build_dir.is_dir() else []
    if len(js_files) < 1:
        raise BuildAssertionError(
            f"BUILD ASSERTION FAILED: {build_dir} has {len(js_files)} *.js "
            "file(s) -- jupyter lite build was skipped or produced a hollow "
            "output. GATE G5 requires `ls dist/build/*.js | wc -l` >= 50 "
            "(the deployed husk this replaces had 0)."
        )
    bundle = build_dir / "lab" / "bundle.js"
    if not bundle.is_file() or bundle.stat().st_size == 0:
        raise BuildAssertionError(
            f"BUILD ASSERTION FAILED: {bundle} is missing or empty -- the "
            "lab app's own bundle did not build correctly."
        )
    logger.info(
        "jupyterlite output OK: %d file(s) under build/, bundle.js is %d bytes",
        len(js_files),
        bundle.stat().st_size,
    )


# --- step 2: manifest regeneration --------------------------------------


def run_build_manifest(*, dev: bool, with_coxswain: bool = False) -> None:
    args = [str(SCRIPTS_DIR / "build_manifest.py")]
    if dev:
        args.append("--dev")
    if with_coxswain:
        args.append("--with-coxswain")
    _uv_run(args, cwd=REPO_ROOT, timeout=60)


# --- step 3: staging overlay/ + bootstrap/ + shell/ into <out> ----------


def _copytree_filtered(src: Path, dst: Path, *, skip=None) -> int:
    """Copy *src* -> *dst* recursively, skipping ``__pycache__``, ``.pyc``/
    ``.pyo``, and ``.gitkeep`` placeholder files. Returns the count of files
    actually copied.

    Directories are created even when every file inside them gets filtered
    out. This was originally load-bearing for ``visualizer-augmentations/``,
    which held only a ``.gitkeep`` until 260819 -- ADR Sec 4.2 #4 requires that
    directory to exist in ``dist/`` under its preserved name, because the
    vendored ``visualizer/index.html`` reaches it by a relative ``<script src>``.
    It now ships a real (no-op) ``index.js``, so that particular directory no
    longer depends on this behaviour, and the build asserts on the FILE rather
    than the directory. The walk is kept anyway: a file-driven
    ``mkdir(parents=True)`` alone would silently drop any future
    empty-of-real-content directory, which is exactly the 404 this prevented.
    """
    count = 0
    for item in sorted(src.rglob("*")):
        rel = item.relative_to(src)
        if any(part in _SKIP_DIR_NAMES for part in rel.parts):
            continue
        if skip is not None and skip(rel):
            continue
        if item.is_dir():
            (dst / rel).mkdir(parents=True, exist_ok=True)
            continue
        if item.suffix in _SKIP_FILE_SUFFIXES or item.name in _SKIP_FILE_NAMES:
            continue
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)
        count += 1
    return count


def stage_overlay(out_dir: Path, *, include_coxswain: bool = False) -> int:
    if not OVERLAY_ASSETS_DIR.is_dir():
        raise BuildError(f"{OVERLAY_ASSETS_DIR} does not exist -- nothing to stage.")
    dst = out_dir / "assets"
    if dst.exists():
        shutil.rmtree(dst)

    def skip(rel: Path) -> bool:
        # FR-12: overlay/assets/coxswain/ reaches dist ONLY under
        # --with-coxswain. A default build stages zero files whose path
        # contains "coxswain" (asserted later by assert_no_coxswain_anywhere).
        if not include_coxswain and "coxswain" in rel.parts:
            return True
        return False

    n = _copytree_filtered(OVERLAY_ASSETS_DIR, dst, skip=skip)
    if n == 0:
        raise BuildAssertionError(
            f"BUILD ASSERTION FAILED: staged 0 files from {OVERLAY_ASSETS_DIR} "
            "-- overlay/assets/ appears empty."
        )
    logger.info(
        "staged %d file(s) from overlay/assets/ -> %s%s",
        n,
        dst,
        " (with coxswain assets)" if include_coxswain else "",
    )
    return n


LOADER_SHA_MARKER = "# PRAXIS-LOADER-SHA-INJECT"
LOADER_MODULES = ("stages.py", "transport.py")


def stamp_loader_shas(bootstrap_py: Path, source_dir: Path) -> dict[str, str]:
    """Stamp the loader modules' sha256 into the STAGED praxis_bootstrap.py.

    praxis_bootstrap.py fetches stages.py and transport.py by hardcoded URL over
    a raw synchronous XHR and executes them. Until this stamp existed, `status
    != 200` was the only check -- and these two files run BEFORE D1 and D2 can
    check anything, because transport.py *is* D2's fetch loop. The manifest
    cannot vouch for its own fetcher, so the expectation has to be baked into
    the one file that runs earlier.

    Rewrites the whole marker line, so stamping is idempotent and a stale value
    cannot survive a rebuild. Fails loudly if the marker is absent -- a silently
    unstamped bootstrap would fail closed at runtime with a confusing
    "no pinned sha256" error, and the build is where that should surface.
    """
    text = bootstrap_py.read_text()
    marker_lines = [ln for ln in text.splitlines() if LOADER_SHA_MARKER in ln]
    if len(marker_lines) != 1:
        raise BuildAssertionError(
            f"BUILD ASSERTION FAILED: expected exactly one {LOADER_SHA_MARKER!r} line "
            f"in {bootstrap_py}, found {len(marker_lines)}. Loader sha pinning cannot "
            "be stamped, and the kernel would refuse to boot rather than run "
            "unverified loader code."
        )

    shas: dict[str, str] = {}
    for name in LOADER_MODULES:
        path = source_dir / name
        if not path.is_file():
            raise BuildError(f"{path} missing -- cannot stamp loader sha256.")
        shas[name] = hashlib.sha256(path.read_bytes()).hexdigest()

    rendered = ", ".join(f'"{n}": "{s}"' for n, s in shas.items())
    bootstrap_py.write_text(
        text.replace(marker_lines[0], f"_LOADER_MODULE_SHA256 = {{{rendered}}}  {LOADER_SHA_MARKER}")
    )
    logger.info("stamped loader sha256 for %s", ", ".join(shas))
    return shas


SOURCE_HOST_ROOT = 'HOST_ROOT = "/"'


def normalize_base_path(value: str) -> str:
    """Return *value* with exactly one leading and one trailing slash."""
    stripped = value.strip().strip("/")
    return "/" if not stripped else f"/{stripped}/"


def apply_base_path(out_dir: Path, base_path: str) -> int:
    """Rewrite the notebooks' absolute HOST_ROOT for a subpath deploy.

    GitHub Pages serves a project site under /<repo>/, so a notebook that fetches
    from "/" reaches the DOMAIN root and 404s on every bootstrap file. HOST_ROOT
    cannot be derived at runtime: the kernel is a Web Worker whose global is
    `self`, not `window`, so there is no document location to read. It has to be
    substituted at build time.

    Rewrites the STAGED copy only -- web-repl/files/*.ipynb stays
    deployment-agnostic, the same discipline stamp_loader_shas() uses for the
    bootstrap. Returns the number of notebooks changed.
    """
    if base_path == "/":
        return 0

    files_dir = out_dir / "files"
    if not files_dir.is_dir():
        raise BuildAssertionError(
            f"BUILD ASSERTION FAILED: {files_dir} does not exist, so --base-path "
            "cannot be applied and the deployed notebooks would fetch from the "
            "domain root."
        )

    replacement = f'HOST_ROOT = "{base_path}"'
    changed = 0
    for notebook in sorted(files_dir.rglob("*.ipynb")):
        text = notebook.read_text()
        # The notebook stores source as JSON string literals, so the quotes are
        # escaped on disk; handle both forms rather than guessing which.
        for needle, sub in (
            (SOURCE_HOST_ROOT, replacement),
            (SOURCE_HOST_ROOT.replace('"', '\\"'), replacement.replace('"', '\\"')),
        ):
            if needle in text:
                text = text.replace(needle, sub)
                changed += 1
        notebook.write_text(text)

    if changed == 0:
        raise BuildAssertionError(
            f"BUILD ASSERTION FAILED: --base-path {base_path} was requested but no "
            f"notebook under {files_dir} contained {SOURCE_HOST_ROOT!r}. The deployed "
            "site would boot, open the notebook, and 404 on its first cell. Either "
            "the notebook changed shape or the substitution needle is stale."
        )
    logger.info("applied base path %s to %d notebook occurrence(s)", base_path, changed)
    return changed


def assert_no_root_host_root(out_dir: Path, base_path: str) -> None:
    """Fail if any staged notebook still fetches from the domain root."""
    if base_path == "/":
        return
    offenders = [
        str(nb)
        for nb in sorted((out_dir / "files").rglob("*.ipynb"))
        if SOURCE_HOST_ROOT in nb.read_text()
        or SOURCE_HOST_ROOT.replace('"', '\\"') in nb.read_text()
    ]
    if offenders:
        raise BuildAssertionError(
            "BUILD ASSERTION FAILED: these staged notebooks still carry "
            f"{SOURCE_HOST_ROOT!r} despite --base-path {base_path}: {offenders}. "
            "They would 404 on their first cell against a subpath deploy."
        )


def _dir_bytes(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def prune_pyodide_bundle(out_dir: Path) -> dict[str, int]:
    """Drop payload from the vendored Pyodide bundle that nothing can reach.

    The bundle is the FULL Pyodide distribution -- 307 WASM wheels covering the
    whole scientific Python stack, plus 62 test-suite tarballs. Measured 260820:
    512 MB, of which a real boot fetches 20 files / 17.9 MB (3.5%). The rest is
    hosting cost: Pages storage, artifact upload on every deploy, and headroom
    against the 1 GB limit.

    It is all vendored because `disablePyPIFallback: true` makes anything not
    hosted UNOBTAINABLE at runtime rather than merely slow -- that is what makes
    GATE G5's offline clause meaningful. So pruning is deliberately conservative:
    only two categories, each provably unreachable.

    1. TEST SUITES. 62 lock entries ending in `-tests` (plus `test`, CPython's
       own suite). Verified: no real package `depends` on any of them, and this
       function re-verifies that on every build rather than trusting the 260820
       measurement -- if upstream ever makes a package depend on its test suite,
       the build fails instead of silently shipping a broken import.
    2. STALE DUPLICATES. A `*.whl` no lock entry references, where a DIFFERENT
       version of the same package IS referenced -- e.g. upstream shipped both
       scipy 1.17.0 and 1.17.1 while the lock names only 1.17.1. Nothing can load
       a file the lock does not name.

    Deliberately NOT pruned: unreferenced non-wheel files (`console.html`,
    `package.json`, `ffi.d.ts`) and `.whl.metadata` siblings of kept wheels --
    micropip reads those for dependency resolution WITHOUT downloading the wheel,
    so they are unreferenced by the lock and still load-bearing. "Unreferenced by
    pyodide-lock.json" is not on its own a safe deletion rule.

    Domain-irrelevant heavyweights (python_flint 70 MB, geospatial, pymupdf) are
    left in place: with no PyPI fallback, pruning one is permanent for that
    deploy, and a protocol author reaching for scipy or pandas is plausible.
    That is a product call, not a build-script call.
    """
    pyodide_dir = out_dir / "static" / "pyodide"
    lock_path = pyodide_dir / "pyodide-lock.json"
    if not lock_path.is_file():
        raise BuildAssertionError(
            f"BUILD ASSERTION FAILED: {lock_path} does not exist; cannot prune."
        )

    before = _dir_bytes(pyodide_dir)
    lock = json.loads(lock_path.read_text())
    packages: dict = lock["packages"]

    test_names = {k for k in packages if k.endswith("-tests") or k == "test"}
    # Upstream's lock mixes separators between keys and `depends`: keys use
    # hyphens (`prompt-toolkit`, `ruamel-yaml`) while depends use underscores or
    # dots (`prompt_toolkit`, `ruamel.yaml`). Comparing raw names would let a
    # dependency written as `scipy_tests` slip past this guard -- the one thing it
    # exists to catch. Normalize both sides.
    def _norm(name: str) -> str:
        return name.lower().replace("_", "-").replace(".", "-")

    normalized_tests = {_norm(n) for n in test_names}
    dependents = sorted(
        {
            name
            for name, meta in packages.items()
            if name not in test_names
            for dep in meta.get("depends", [])
            if _norm(dep) in normalized_tests
        }
    )
    if dependents:
        raise BuildAssertionError(
            "BUILD ASSERTION FAILED: these packages now depend on a test-suite "
            f"package, so pruning would break them: {dependents}. Upstream changed "
            "shape; re-check prune_pyodide_bundle before shipping."
        )

    doomed: set[str] = set()
    for name in test_names:
        doomed.add(packages[name]["file_name"])

    # Stale duplicates: unreferenced wheel whose package has a referenced sibling.
    referenced = {meta["file_name"] for meta in packages.values()}
    referenced_stems = {f.split("-")[0].lower().replace("_", "-") for f in referenced}
    for wheel in pyodide_dir.glob("*.whl"):
        if wheel.name in referenced:
            continue
        stem = wheel.name.split("-")[0].lower().replace("_", "-")
        if stem in referenced_stems:
            doomed.add(wheel.name)

    removed_files = 0
    for filename in sorted(doomed):
        for candidate in (pyodide_dir / filename, pyodide_dir / f"{filename}.metadata"):
            if candidate.is_file():
                candidate.unlink()
                removed_files += 1

    for name in test_names:
        packages.pop(name, None)
    lock_path.write_text(json.dumps(lock))

    after = _dir_bytes(pyodide_dir)
    logger.info(
        "pruned pyodide bundle: %d file(s), %d lock entr(ies) -- %.0f MB -> %.0f MB "
        "(saved %.0f MB)",
        removed_files, len(test_names), before / 1e6, after / 1e6, (before - after) / 1e6,
    )
    return {"before": before, "after": after, "files": removed_files}


def stage_bootstrap(out_dir: Path) -> int:
    dst = out_dir / "bootstrap"
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    for name in _BOOTSTRAP_FILES:
        src = BOOTSTRAP_DIR / name
        if not src.is_file():
            raise BuildError(f"{src} missing -- cannot stage bootstrap/.")
        shutil.copy2(src, dst / name)
    # Stamp the STAGED copy only. The source tree keeps the empty placeholder,
    # so a tree served straight from source fails closed instead of running
    # unverified loader code.
    stamp_loader_shas(dst / "praxis_bootstrap.py", BOOTSTRAP_DIR)
    logger.info("staged %d file(s) from bootstrap/ -> %s", len(_BOOTSTRAP_FILES), dst)
    return len(_BOOTSTRAP_FILES)


def stage_shell(out_dir: Path) -> Path:
    src = SHELL_DIR / "praxis-shell.js"
    if not src.is_file():
        raise BuildError(f"{src} missing -- cannot stage shell/.")
    # ONE shared copy at <out>/shell/, referenced as `../shell/praxis-shell.js`
    # from every entry's index.html. Previously this was nested under lab/,
    # which meant only lab/ could carry the shell -- so repl/, the entry whose
    # `?code=&execute=1` the smoke harness drives, had no shell and D1 could
    # only fail closed there.
    dst_dir = out_dir / "shell"
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / "praxis-shell.js"
    shutil.copy2(src, dst)
    logger.info("staged shell/praxis-shell.js -> %s", dst)
    return dst


COXSWAIN_SHELL_ENTRY = SHELL_DIR / "coxswain-shell.js"
COXSWAIN_JS_MODULES = SHELL_DIR / "coxswain"
_REQUIRED_COXSWAIN_MODULES = (
    "card_state.js",
    "propose_card.js",
    "failure_card.js",
    "phrase.js",
    "text.js",
    "ids.js",
    "vdom.js",
    "envelope.js",
    "timing.js",
)


def stage_coxswain_shell(out_dir: Path) -> int:
    """FR-12's conditional half of the D1 shell path: the Coxswain panel entry
    plus its DOM-free modules land at <out>/shell/coxswain-shell.js and
    <out>/shell/coxswain/ -- ONLY called under --with-coxswain."""
    if not COXSWAIN_SHELL_ENTRY.is_file():
        raise BuildError(f"{COXSWAIN_SHELL_ENTRY} missing -- cannot stage coxswain shell.")
    if not COXSWAIN_JS_MODULES.is_dir():
        raise BuildError(f"{COXSWAIN_JS_MODULES} missing -- cannot stage coxswain modules.")
    missing = [
        name for name in _REQUIRED_COXSWAIN_MODULES if not (COXSWAIN_JS_MODULES / name).is_file()
    ]
    if missing:
        raise BuildError(
            f"{COXSWAIN_JS_MODULES} is missing required module(s): {missing} -- "
            "the panel imports them by relative path, so a partial copy would "
            "404 in the browser."
        )
    dst_shell_dir = out_dir / "shell"
    dst_shell_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(COXSWAIN_SHELL_ENTRY, dst_shell_dir / "coxswain-shell.js")
    dst_modules = dst_shell_dir / "coxswain"
    if dst_modules.exists():
        shutil.rmtree(dst_modules)
    staged = _copytree_filtered(
        COXSWAIN_JS_MODULES,
        dst_modules,
        # Test files never ship: bun discovers them from the source tree, so
        # a copy under dist/ is dead weight on every page load path.
        skip=lambda rel: "__tests__" in rel.parts,
    )
    logger.info(
        "staged coxswain-shell.js + %d module file(s) -> %s", staged, dst_modules
    )
    return staged + 1


# --- step 4: D1 shell injection ------------------------------------------


def _dist_entry_targets(out_dir: Path) -> list[Path]:
    """Every <out>/<entry>/index.html carrying the D1 anchor.

    Explicit --target threading fixes a latent trap: inject_shell.py's own
    default discovery looks at <web-repl-root>/dist, so ANY build_repl.py run
    with a non-default --out used to inject (and --check) the WRONG tree --
    the stale default dist rather than the one just built. Default builds are
    unaffected (their out_dir IS web-repl/dist)."""
    import inject_shell  # same directory; sys.path[0] is this script's dir

    targets = inject_shell.discover_targets(out_dir)
    if not targets:
        raise BuildError(
            f"no */index.html carrying anchor id={inject_shell._ANCHOR_ID!r} found "
            f"under {out_dir} -- refusing to inject nothing."
        )
    return targets


def run_inject_shell(
    *, dev: bool, with_coxswain: bool = False, out_dir: Path | None = None
) -> None:
    # No --target (default dist): inject_shell.py discovers every
    # dist/*/index.html carrying the anchor, so all app entries get the shell,
    # not just lab/. Non-default --out builds thread their OWN entries through
    # explicit --target flags (see _dist_entry_targets).
    args = [str(SCRIPTS_DIR / "inject_shell.py")]
    if dev:
        args.append("--dev")
    if with_coxswain:
        args.append("--with-coxswain")
    if out_dir is not None:
        for target in _dist_entry_targets(out_dir):
            args.extend(["--target", str(target)])
    _uv_run(args, cwd=REPO_ROOT, timeout=60)


def run_inject_shell_check(*, with_coxswain: bool = False, out_dir: Path | None = None) -> None:
    args = [str(SCRIPTS_DIR / "inject_shell.py"), "--check"]
    if with_coxswain:
        args.append("--with-coxswain")
    if out_dir is not None:
        for target in _dist_entry_targets(out_dir):
            args.extend(["--target", str(target)])
    try:
        _uv_run(args, cwd=REPO_ROOT, timeout=60)
    except BuildError as exc:
        raise BuildAssertionError(f"BUILD ASSERTION FAILED: inject_shell.py --check failed: {exc}") from exc


# --- step 5: final completeness assertion --------------------------------


def assert_dist_complete(out_dir: Path, *, with_coxswain: bool = False) -> None:
    required = [
        out_dir / "assets" / "wheels" / "manifest.json",
        out_dir / "assets" / "shims" / "web_serial_shim.py",
        out_dir / "assets" / "shims" / "web_usb_shim.py",
        out_dir / "assets" / "shims" / "web_hid_shim.py",
        out_dir / "assets" / "shims" / "web_ftdi_shim.py",
        out_dir / "assets" / "python" / "web_bridge.py",
        out_dir / "assets" / "python" / "praxis" / "__init__.py",
        out_dir / "assets" / "python" / "praxis" / "interactive.py",
        out_dir / "assets" / "visualizer" / "lib.js",
        out_dir / "assets" / "visualizer" / "index.html",
        out_dir / "assets" / "visualizer-augmentations" / "index.js",
        out_dir / "bootstrap" / "praxis_bootstrap.py",
        out_dir / "bootstrap" / "stages.py",
        out_dir / "bootstrap" / "transport.py",
        out_dir / "shell" / "praxis-shell.js",
        out_dir / "lab" / "index.html",
        out_dir / "repl" / "index.html",
        # The welcome notebook, and the contents index that makes it VISIBLE. Both,
        # because they fail independently: jupyterlite-core's `contents` addon needs
        # jupyter-server (a `dev`-group dep) to index files/, and without it the build
        # either hard-raises or -- in the pre-260819 empty-files/ case -- merely warns.
        # Asserting only on the .ipynb would let a site ship the notebook as an
        # unreachable blob with an empty file browser.
        out_dir / "files" / "welcome.ipynb",
        out_dir / "api" / "contents" / "all.json",
    ]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        raise BuildAssertionError(
            "BUILD ASSERTION FAILED: dist/ is missing required staged path(s):\n  "
            + "\n  ".join(missing)
        )
    wheel_count = len(list((out_dir / "assets" / "wheels").glob("*.whl")))
    if wheel_count == 0:
        raise BuildAssertionError(
            "BUILD ASSERTION FAILED: dist/assets/wheels/ contains zero *.whl files."
        )

    coxswain_required: list[Path] = []
    if with_coxswain:
        # FR-12's flagged half: a --with-coxswain build must actually carry the
        # panel entry, its DOM-free modules, and its stylesheet.
        coxswain_required = [
            out_dir / "shell" / "coxswain-shell.js",
            *(out_dir / "shell" / "coxswain" / name for name in _REQUIRED_COXSWAIN_MODULES),
            out_dir / "assets" / "coxswain" / "coxswain.css",
            # W4: the conditionally-staged highlight subscriber must actually
            # ship, or the injected script tag would 404 in the browser.
            out_dir / "assets" / "coxswain" / "viz_highlight.js",
        ]
    missing_cx = [str(p) for p in coxswain_required if not p.exists()]
    if missing_cx:
        raise BuildAssertionError(
            "BUILD ASSERTION FAILED: --with-coxswain dist/ is missing Coxswain "
            "asset(s):\n  " + "\n  ".join(missing_cx)
        )

    logger.info(
        "dist/ completeness OK (%d wheel(s) staged%s)",
        wheel_count,
        ", coxswain assets present" if with_coxswain else "",
    )


# --- AC-11 assertions (FR-12's enforcement mechanism) ------------------------


def _tracked_augmentation_path() -> Path:
    return OVERLAY_ASSETS_DIR / "visualizer-augmentations" / "index.js"


def assert_augmentation_byte_identity(out_dir: Path) -> None:
    """AC-11 clause 1, asserted in EVERY build mode: a default build's staged
    visualizer-augmentations/index.js is byte-identical (sha256) to the tracked
    source. The augmentation file ships in every build and is NOT modified by
    the Coxswain spec at all; this is the tripwire that catches anyone putting
    Coxswain code back into it (FR-12's whole reason for the byte-identity
    clause). Runs unconditionally because it must hold either way."""
    tracked = _tracked_augmentation_path()
    staged = out_dir / "assets" / "visualizer-augmentations" / "index.js"
    if not tracked.is_file():
        raise BuildError(f"{tracked} missing -- cannot assert byte identity.")
    if not staged.is_file():
        raise BuildAssertionError(
            f"BUILD ASSERTION FAILED: {staged} was not staged, so AC-11's "
            "byte-identity clause cannot hold and every entry page would lose "
            "the visualizer augmentation."
        )
    tracked_sha = hashlib.sha256(tracked.read_bytes()).hexdigest()
    staged_sha = hashlib.sha256(staged.read_bytes()).hexdigest()
    if tracked_sha != staged_sha:
        raise BuildAssertionError(
            f"BUILD ASSERTION FAILED: staged {staged} sha256 {staged_sha} != "
            f"tracked {tracked} sha256 {tracked_sha}. The staging pass rewrote "
            "the augmentation file -- visualizer-augmentations/index.js must be "
            "byte-identical to the tracked source in EVERY build (AC-11)."
        )
    logger.info("visualizer-augmentations/index.js byte-identity OK (%s)", tracked_sha[:12])


def assert_no_coxswain_anywhere(out_dir: Path) -> None:
    """FR-12 / AC-11 first clause for a DEFAULT build: zero paths under out_dir
    contain 'coxswain'. This covers the manifest substring check AND asset/
    shell staging in one structural sweep -- stronger than the manifest-only
    check, because it also catches stray copies anywhere else in dist."""
    offenders = sorted(str(p.relative_to(out_dir)) for p in out_dir.rglob("*coxswain*"))
    if offenders:
        raise BuildAssertionError(
            "BUILD ASSERTION FAILED: this is a DEFAULT build (no --with-coxswain) "
            "but these dist paths contain 'coxswain' (FR-12 requires none):\n  "
            + "\n  ".join(offenders[:20])
        )
    logger.info("default build carries zero coxswain paths (FR-12/AC-11)")


def assert_visualizer_html_free_of_coxswain(out_dir: Path) -> None:
    """AC-11 clause 3, DEFAULT half: a default build's vendored
    visualizer/index.html contains no <script> tag referencing coxswain."""
    html_path = out_dir / "assets" / "visualizer" / "index.html"
    if not html_path.is_file():
        raise BuildAssertionError(
            f"BUILD ASSERTION FAILED: {html_path} does not exist."
        )
    html = html_path.read_text()
    offenders = [
        line.strip()
        for line in html.splitlines()
        if "<script" in line.lower() and "coxswain" in line.lower()
    ]
    if offenders:
        raise BuildAssertionError(
            "BUILD ASSERTION FAILED: a DEFAULT build's visualizer/index.html "
            "references coxswain from a <script> tag (AC-11 clause 3):\n  "
            + "\n  ".join(offenders[:5])
        )
    logger.info("default visualizer/index.html references no coxswain scripts (AC-11)")


def inject_viz_highlight_tag(out_dir: Path) -> None:
    """W4's flagged half of AC-11 clause 3: inject EXACTLY ONE second module
    tag -- <script type=module src="../coxswain/viz_highlight.js"> -- into the
    STAGED dist copy of visualizer/index.html under --with-coxswain.

    The tracked overlay/assets/visualizer/index.html is never touched: it
    ships in every build and must stay coxswain-free. The transformation lives
    in vendor_visualizer.inject_coxswain_highlight_tag so the tag machinery
    (and its sibling-directory constraint) stays in one file."""
    import vendor_visualizer  # same directory; sys.path[0] is this script's dir

    html_path = out_dir / "assets" / "visualizer" / "index.html"
    if not html_path.is_file():
        raise BuildAssertionError(
            f"BUILD ASSERTION FAILED: {html_path} does not exist -- cannot "
            "inject the coxswain highlight tag into a missing document."
    )
    try:
        tagged = vendor_visualizer.inject_coxswain_highlight_tag(html_path.read_text())
    except vendor_visualizer.VendorError as exc:
        raise BuildAssertionError(
            f"BUILD ASSERTION FAILED: coxswain highlight-tag injection failed: {exc}"
        ) from exc
    html_path.write_text(tagged)
    logger.info("injected coxswain viz_highlight <script> tag -> %s", html_path)


def assert_visualizer_html_exactly_one_coxswain_tag(out_dir: Path) -> None:
    """AC-11 clause 3, FLAGGED half: a --with-coxswain build's staged
    visualizer/index.html contains exactly one <script> tag referencing
    coxswain -- the viz_highlight subscriber, beside (never instead of) the
    augmentation tag."""
    html_path = out_dir / "assets" / "visualizer" / "index.html"
    if not html_path.is_file():
        raise BuildAssertionError(f"BUILD ASSERTION FAILED: {html_path} does not exist.")
    offenders = [
        line.strip()
        for line in html_path.read_text().splitlines()
        if "<script" in line.lower() and "coxswain" in line.lower()
    ]
    if len(offenders) != 1:
        raise BuildAssertionError(
            f"BUILD ASSERTION FAILED: a --with-coxswain build's visualizer/index.html "
            f"must carry EXACTLY ONE coxswain <script> tag (AC-11 clause 3), found "
            f"{len(offenders)}:\n  " + "\n  ".join(offenders[:5])
        )
    logger.info("--with-coxswain visualizer/index.html carries exactly one coxswain tag (AC-11)")


# --- CLI -------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help=f"Build output directory (default: {DEFAULT_OUT_DIR}, gitignored).",
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help='Thread the D1 "dev" sentinel through both build_manifest.py --dev '
        "(manifest praxis_git_sha) and inject_shell.py --dev (injected shell "
        "sha) -- ADR Sec 2.3's dev-loop escape hatch. Never weakens the "
        "non-dev path; both scripts independently compute git rev-parse HEAD "
        "when this is not passed.",
    )
    parser.add_argument(
        "--debug-skip-jupyterlite",
        action="store_true",
        help="Failure-injection mode for GATE G5: skip the `jupyter lite "
        "build` subprocess entirely. The post-build structural assertion "
        "then fires for real (dist/build/ is absent), exiting nonzero with "
        "'BUILD ASSERTION FAILED' -- proving the build fails loud rather "
        "than producing a hollow dist/.",
    )
    parser.add_argument(
        "--allow-cdn",
        action="store_true",
        help=(
            "SOURCE Pyodide from the CDN URL pinned in jupyter_lite_config.json "
            "instead of requiring the vendored tarball from fetch_pyodide.py. "
            "This changes where the build FETCHES Pyodide, NOT how the built site "
            "loads it: PyodideAddon vendors whatever URL it is given into "
            "static/pyodide/ and rewrites pyodideUrl to that local path either "
            "way. Measured 260820 -- --allow-cdn produced a byte-comparable 479 MB "
            "site with pyodideUrl=./static/pyodide/pyodide.mjs. It does NOT "
            "produce a CDN-loading site, and it does NOT make the artifact "
            "smaller. For local iteration when the tarball has not been fetched."
        ),
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="Do not remove an existing --out directory before building "
        "(default: remove it first, matching GATE G5's `rm -rf dist`).",
    )
    parser.add_argument(
        "--no-prune-pyodide",
        action="store_true",
        help=(
            "Keep the full vendored Pyodide bundle. By default the build drops the "
            "62 test-suite packages and stale duplicate wheels, which nothing can "
            "reach -- see prune_pyodide_bundle."
        ),
    )
    parser.add_argument(
        "--base-path",
        default="/",
        help=(
            "URL prefix the built site will be served under. Default '/'. Set this "
            "for a subpath deploy (GitHub Pages project sites serve at /<repo>/, so "
            "the praxis site needs '/praxis/'): it rewrites the absolute HOST_ROOT in "
            "the STAGED notebooks, which cannot be derived at runtime because the "
            "kernel is a Web Worker with no document location."
        ),
    )
    parser.add_argument(
        "--with-coxswain",
        action="store_true",
        help="Stage and inject the Coxswain MVP panel (FR-12): overlay/assets/"
        "coxswain/*, shell/coxswain-shell.js + shell/coxswain/*, the manifest's "
        "coxswain_assets sha entries, and the coxswain-shell.js <script "
        "type=module> tag on every entry page. WITHOUT this flag the build "
        "carries zero coxswain paths -- asserted post-build (AC-11), along "
        "with visualizer-augmentations/index.js byte identity in BOTH modes.",
    )
    parser.add_argument(
        "--coxswain-relay-endpoint",
        default=None,
        metavar="URL",
        help="W5: bake a transduction_log relay endpoint into the STAGED copy "
        "of shell/coxswain/relay_config.js, activating the best-effort audit "
        "relay (FR-9's fourth clause). Requires --with-coxswain. WITHOUT this "
        "flag the staged relay_config.js stays at its tracked null endpoint: "
        "the relay is permanently inert and issues ZERO network calls "
        "(AC-10 / RISK-10) -- which §7 accepts as the likely MVP outcome.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Debug-level logging.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    out_dir = args.out.resolve()

    try:
        if not args.no_clean and out_dir.exists():
            logger.info("removing existing %s", out_dir)
            shutil.rmtree(out_dir)

        if args.debug_skip_jupyterlite:
            logger.warning(
                "--debug-skip-jupyterlite: SKIPPING `jupyter lite build` -- "
                "this is deliberate failure injection for GATE G5, not a "
                "real build path."
            )
            out_dir.mkdir(parents=True, exist_ok=True)
        else:
            # Vendor the pinned piplite wheels first: the jupyterlite build reads
            # them through PipliteAddon.piplite_urls, which now points into
            # web-repl/vendor/ (gitignored) rather than at a committed .whl. See
            # fetch_vendored_wheels.py for why the tracked binary was retired.
            fetch_vendored_wheels.fetch_all()
            pyodide_arg = resolve_pyodide_arg(allow_cdn=args.allow_cdn)
            log_path = out_dir.parent / f".{out_dir.name}-jupyterlite-build.log"
            run_jupyterlite_build(out_dir=out_dir, pyodide_arg=pyodide_arg, log_path=log_path)

        assert_jupyterlite_output_not_hollow(out_dir)
        if not args.debug_skip_jupyterlite and not args.allow_cdn:
            assert_pyodide_is_local(out_dir)
        assert_required_piplite_wheels(out_dir)
        if not args.debug_skip_jupyterlite:
            assert_completion_autocompletion(out_dir)
            assert_praxis_boot_shipped(out_dir)

        if not args.debug_skip_jupyterlite and not args.no_prune_pyodide:
            prune_pyodide_bundle(out_dir)

        base_path = normalize_base_path(args.base_path)
        apply_base_path(out_dir, base_path)
        assert_no_root_host_root(out_dir, base_path)

        run_build_manifest(dev=args.dev, with_coxswain=args.with_coxswain)
        stage_overlay(out_dir, include_coxswain=args.with_coxswain)
        stage_bootstrap(out_dir)
        stage_shell(out_dir)
        if args.with_coxswain:
            stage_coxswain_shell(out_dir)

        if args.coxswain_relay_endpoint:
            # W5's only build-script concern: activate the transduction_log
            # relay by rewriting the STAGED relay_config.js. The tracked file
            # stays null, so default builds keep AC-10's zero-network path;
            # the endpoint exists only in THIS dist.
            if not args.with_coxswain:
                raise BuildError(
                    "--coxswain-relay-endpoint requires --with-coxswain: the "
                    "relay ships only alongside Coxswain assets (FR-12)."
                )
            staged = out_dir / "shell" / "coxswain" / "relay_config.js"
            if not staged.parent.is_dir():
                raise BuildError(
                    f"{staged} missing after staging -- cannot bake relay endpoint."
                )
            staged.write_text(
                "// GENERATED by build_repl.py --coxswain-relay-endpoint; edit the"
                " build flag, not this file.\n"
                f"export const RELAY_ENDPOINT = {json.dumps(args.coxswain_relay_endpoint)};\n",
                encoding="utf-8",
            )
            logger.info("baked Coxswain relay endpoint into %s", staged)

        run_inject_shell(dev=args.dev, with_coxswain=args.with_coxswain, out_dir=out_dir)
        run_inject_shell_check(with_coxswain=args.with_coxswain, out_dir=out_dir)

        if args.with_coxswain:
            # W4 / deviation D-C: inject the SECOND module tag into the STAGED
            # visualizer/index.html only. Runs after stage_overlay (which resets
            # assets/ from the tracked, coxswain-free source every build), so
            # this is per-build state and can never leak into a default build.
            inject_viz_highlight_tag(out_dir)

        assert_dist_complete(out_dir, with_coxswain=args.with_coxswain)

        # AC-11: byte identity holds in EVERY mode; the zero-coxswain-path and
        # no-coxswain-script clauses hold in DEFAULT builds; the flagged half of
        # clause 3 (exactly one coxswain tag) is asserted in --with-coxswain
        # builds right after the injection above.
        assert_augmentation_byte_identity(out_dir)
        if not args.with_coxswain:
            assert_no_coxswain_anywhere(out_dir)
            assert_visualizer_html_free_of_coxswain(out_dir)
        else:
            assert_visualizer_html_exactly_one_coxswain_tag(out_dir)

    except BuildAssertionError as exc:
        msg = str(exc)
        if "BUILD ASSERTION FAILED" not in msg:
            msg = f"BUILD ASSERTION FAILED: {msg}"
        logger.error(msg)
        return 1
    except BuildError as exc:
        logger.error("%s", exc)
        return 1

    logger.info("OK -> %s", out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
