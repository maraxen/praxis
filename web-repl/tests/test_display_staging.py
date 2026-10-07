"""Display modules staging (A6, AC-6): stage_shell copies shell/display/ to
dist/shell/display/, leaving out tests, and assert_dist_complete requires
shell/display/index.js and shell/display/chrome.js.

Same idiom as test_persistence_staging.py. The staging cases build a temporary
shell/ source tree and exercise the production stage_shell (no
re-implementation), so nothing here needs a dist build, a browser or the
network. One case runs stage_shell against the REAL shell/ source into a
temporary dist: that is AC-6's `test -f dist/shell/display/index.js` and
`! test -e dist/shell/display/__tests__` without the wheel/JupyterLite build.

B9 (this file's second revision) adds stale.js and interact.js to the required
list. B8 (third revision) adds the kernel-side package: assert_dist_complete also
requires assets/python/praxis/display/__init__.py (spec section 4, build_repl.py row:
"C6 ... and assets/python/praxis/display/__init__.py, the last from B8"). Without it a
dist could ship a bootstrap whose D13 stage imports a package that is not there, and
the failure would surface only as a runtime praxis:display-error.

C6 (fourth revision, AC-33 local): dock.js joins the display list, and assert_dist_complete
requires the 3D viewer's static page, its vendored three.js, the C4 augmentations and
praxis/viz/viewer3d.py (``_C6_DIST_PATHS``). The last section adds the offline property, all
static: a scanner over the staged viewer assets for load-time external URLs, with negative
controls, and a module-graph closure over the staged page, so no import can miss the dist.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import build_repl  # noqa: E402 -- path setup must precede this import

# What a dist requires under shell/display/. A6: index.js, chrome.js. B9 appends
# stale.js and interact.js; C6 appends dock.js.
_REQUIRED_DISPLAY = ("index.js", "chrome.js", "stale.js", "interact.js", "dock.js")

# The kernel-side package B8 adds (path relative to dist/).
_DISPLAY_PY_INIT = "assets/python/praxis/display/__init__.py"

# What C6 adds to assert_dist_complete besides dock.js (path relative to dist/). The spec names
# the page, its vendored three (webgpu build), the C4 augmentations and viewer3d.py. boot.js
# (the page's module entry) and three.core.min.js (three.webgpu.min.js imports it statically)
# are added here: a dist without either would boot to a blank page offline.
_V3D = "assets/visualizer3d"
_V3D_AUG = "assets/visualizer3d-augmentations"
_C6_DIST_PATHS = (
    f"{_V3D}/index.html",
    f"{_V3D}/boot.js",
    f"{_V3D}/vendor/three.webgpu.min.js",
    f"{_V3D}/vendor/three.core.min.js",
    f"{_V3D_AUG}/socket.js",
    f"{_V3D_AUG}/embed.js",
    f"{_V3D_AUG}/embed.css",
    "assets/python/praxis/viz/viewer3d.py",
)
_OVERLAY_ASSETS = Path(__file__).resolve().parents[1] / "overlay" / "assets"


def _make_shell_source_tree(tmp_path: Path) -> tuple[Path, Path]:
    """A minimal temporary shell/ source tree: praxis-shell.js plus a display/
    dir with the required modules, a __tests__ directory and sibling *.test.js
    files (A5 keeps its bun tests next to the modules), all of which must be
    excluded. Returns (shell_dir, display_dir)."""
    shell_dir = tmp_path / "shell_src"
    shell_dir.mkdir()
    (shell_dir / "praxis-shell.js").write_text("// praxis-shell.js\n")

    src = shell_dir / "display"
    src.mkdir()
    for name in _REQUIRED_DISPLAY:
        (src / name).write_text(f"// {name}\n")

    (src / "chrome.test.js").write_text("// sibling test\n")
    (src / "index.test.js").write_text("// sibling test\n")
    tests_dir = src / "__tests__"
    tests_dir.mkdir()
    (tests_dir / "fakes.js").write_text("// fakes\n")
    (tests_dir / "x.test.js").write_text("// test file\n")
    return shell_dir, src


def _make_dist_dir(tmp_path: Path) -> Path:
    dist = tmp_path / "dist"
    (dist / "shell").mkdir(parents=True)
    return dist


def _write_complete_dist(dist: Path) -> None:
    """Every path assert_dist_complete requires today, display modules included."""
    files = {
        "assets/wheels/manifest.json": "{}",
        "assets/wheels/pkg-1.0.0-py3-none-any.whl": "wheel",
        "assets/shims/web_serial_shim.py": "# shim\n",
        "assets/shims/web_usb_shim.py": "# shim\n",
        "assets/shims/web_hid_shim.py": "# shim\n",
        "assets/shims/web_ftdi_shim.py": "# shim\n",
        "assets/python/web_bridge.py": "# bridge\n",
        "assets/python/praxis/__init__.py": "",
        "assets/python/praxis/interactive.py": "# interactive\n",
        _DISPLAY_PY_INIT: "# display\n",
        "assets/visualizer/lib.js": "// lib\n",
        "assets/visualizer/index.html": "<html></html>",
        "assets/visualizer-augmentations/index.js": "// aug\n",
        "assets/theme/praxis-theme.css": "/* theme */\n",
        "assets/theme/praxis-mark.svg": "<svg></svg>",
        "assets/theme/praxis-favicon.svg": "<svg></svg>",
        "assets/theme/fonts/RobotoFlex-Variable.woff2": "font",
        "assets/theme/fonts/JetBrainsMono-Variable.woff2": "font",
        "bootstrap/praxis_bootstrap.py": "# bootstrap\n",
        "bootstrap/stages.py": "# stages\n",
        "bootstrap/transport.py": "# transport\n",
        "shell/praxis-shell.js": "// shell\n",
        "shell/persistence/codec.js": "// codec\n",
        "shell/persistence/core.js": "// core\n",
        "shell/persistence/panel.js": "// panel\n",
        "shell/device/connect.js": "// connect\n",
        "lab/index.html": "<html></html>",
        "repl/index.html": "<html></html>",
        "files/welcome.ipynb": "{}",
        "api/contents/all.json": "{}",
        **{f"shell/display/{name}": f"// {name}\n" for name in _REQUIRED_DISPLAY},
        **{rel: f"// {rel}\n" for rel in _C6_DIST_PATHS},
    }
    for rel, text in files.items():
        p = dist / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)


def _staged_files(root: Path) -> set[str]:
    return {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}


# --- stage_shell -------------------------------------------------------------


def test_stage_shell_stages_display_modules(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """stage_shell copies display/ with identical bytes, and stages neither
    __tests__/ nor any *.test.js."""
    shell_dir, src = _make_shell_source_tree(tmp_path)
    dist = _make_dist_dir(tmp_path)
    monkeypatch.setattr(build_repl, "SHELL_DIR", shell_dir)

    build_repl.stage_shell(dist)

    dst = dist / "shell" / "display"
    for name in _REQUIRED_DISPLAY:
        assert (dst / name).read_bytes() == (src / name).read_bytes()
    assert not (dst / "__tests__").exists()
    assert _staged_files(dst) == set(_REQUIRED_DISPLAY), (
        "only the shipping modules may be staged (no tests, no fakes)"
    )


def test_stage_shell_removes_stale_display_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A file in dist/shell/display/ from an earlier build, absent from source,
    is removed by stage_shell."""
    shell_dir, _src = _make_shell_source_tree(tmp_path)
    dist = _make_dist_dir(tmp_path)
    dst = dist / "shell" / "display"
    dst.mkdir(parents=True)
    stale = dst / "old.js"
    stale.write_text("// stale file\n")
    stale_nested = dst / "__tests__" / "old.test.js"
    stale_nested.parent.mkdir()
    stale_nested.write_text("// stale nested test\n")
    monkeypatch.setattr(build_repl, "SHELL_DIR", shell_dir)

    build_repl.stage_shell(dist)

    assert not stale.exists(), "stale file must be removed after staging"
    assert not stale_nested.exists(), "stale nested file must be removed after staging"
    for name in _REQUIRED_DISPLAY:
        assert (dst / name).is_file()


def test_stage_shell_removes_stale_display_dir_when_source_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A-10 discipline: with no display/ in source at all, a dist/shell/display/
    left by an earlier build must not survive."""
    shell_dir = tmp_path / "shell_src"
    shell_dir.mkdir()
    (shell_dir / "praxis-shell.js").write_text("// praxis-shell.js\n")
    assert not (shell_dir / "display").exists()

    dist = _make_dist_dir(tmp_path)
    dst = dist / "shell" / "display"
    dst.mkdir(parents=True)
    (dst / "old.js").write_text("// stale file\n")
    monkeypatch.setattr(build_repl, "SHELL_DIR", shell_dir)

    build_repl.stage_shell(dist)

    assert not dst.exists(), "stale display dir must be removed even when source is absent"


def test_stage_shell_real_source_stages_display_without_tests(tmp_path: Path) -> None:
    """AC-6, without the wheel/JupyterLite build: stage the REAL shell/ source.
    `test -f dist/shell/display/index.js` and `! test -e dist/shell/display/__tests__`,
    plus chrome.js and no *.test.js anywhere under display/."""
    dist = _make_dist_dir(tmp_path)

    build_repl.stage_shell(dist)

    dst = dist / "shell" / "display"
    for name in _REQUIRED_DISPLAY:
        assert (dst / name).is_file(), f"dist/shell/display/{name} was not staged"
    assert not (dst / "__tests__").exists()
    leaked = sorted(p for p in _staged_files(dst) if p.endswith(".test.js"))
    assert leaked == [], f"test files must not ship: {leaked}"
    # Bytes match the tracked source (a copy, not a rewrite).
    for name in _REQUIRED_DISPLAY:
        assert (dst / name).read_bytes() == (build_repl.SHELL_DIR / "display" / name).read_bytes()


# --- assert_dist_complete ----------------------------------------------------


def test_assert_dist_complete_passes_with_display_modules(tmp_path: Path) -> None:
    """Positive control: the complete fixture (display modules present) passes,
    so the failures below are attributable to the missing file alone."""
    dist = _make_dist_dir(tmp_path)
    _write_complete_dist(dist)

    build_repl.assert_dist_complete(dist, with_coxswain=False)  # must not raise


@pytest.mark.parametrize("missing", _REQUIRED_DISPLAY)
def test_assert_dist_complete_requires_each_display_module(
    tmp_path: Path, missing: str
) -> None:
    """Negative control: with exactly one display module missing it raises
    BuildAssertionError that names that file (and only that display file)."""
    dist = _make_dist_dir(tmp_path)
    _write_complete_dist(dist)
    (dist / "shell" / "display" / missing).unlink()

    with pytest.raises(build_repl.BuildAssertionError) as exc:
        build_repl.assert_dist_complete(dist, with_coxswain=False)

    msg = str(exc.value)
    assert "missing required staged path" in msg
    assert f"shell/display/{missing}" in msg.replace("\\", "/")
    for present in (n for n in _REQUIRED_DISPLAY if n != missing):
        assert f"shell/display/{present}" not in msg.replace("\\", "/")


def test_stage_shell_real_source_stages_device_module_without_tests(tmp_path: Path) -> None:
    """shell/device/connect.js (the kernel's USER_INTERACTION handler) ships;
    its __tests__/ does not."""
    dist = _make_dist_dir(tmp_path)

    build_repl.stage_shell(dist)

    dst = dist / "shell" / "device"
    assert (dst / "connect.js").read_bytes() == (
        build_repl.SHELL_DIR / "device" / "connect.js"
    ).read_bytes()
    assert not (dst / "__tests__").exists()
    assert _staged_files(dst) == {"connect.js"}


def test_assert_dist_complete_requires_device_connect(tmp_path: Path) -> None:
    """Without connect.js, lh.setup() on a USB machine has no page handler, so the
    build must refuse the dist and name the file."""
    dist = _make_dist_dir(tmp_path)
    _write_complete_dist(dist)
    (dist / "shell" / "device" / "connect.js").unlink()

    with pytest.raises(build_repl.BuildAssertionError) as exc:
        build_repl.assert_dist_complete(dist, with_coxswain=False)

    missing = [line.strip().replace("\\", "/") for line in str(exc.value).splitlines()[1:]]
    assert len(missing) == 1, f"only connect.js may be reported missing: {missing}"
    assert missing[0].endswith("dist/shell/device/connect.js")


def test_assert_dist_complete_requires_display_dir(tmp_path: Path) -> None:
    """Every module missing (no display/ at all) -> every one is named."""
    dist = _make_dist_dir(tmp_path)
    _write_complete_dist(dist)
    for name in _REQUIRED_DISPLAY:
        (dist / "shell" / "display" / name).unlink()
    (dist / "shell" / "display").rmdir()

    with pytest.raises(build_repl.BuildAssertionError) as exc:
        build_repl.assert_dist_complete(dist, with_coxswain=False)

    msg = str(exc.value).replace("\\", "/")
    for name in _REQUIRED_DISPLAY:
        assert f"shell/display/{name}" in msg


def test_assert_dist_complete_requires_the_display_python_package(tmp_path: Path) -> None:
    """B8: with only ``praxis/display/__init__.py`` missing (the fixture is otherwise complete, as the
    positive control above shows) it raises BuildAssertionError naming exactly that file."""
    dist = _make_dist_dir(tmp_path)
    _write_complete_dist(dist)
    (dist / _DISPLAY_PY_INIT).unlink()

    with pytest.raises(build_repl.BuildAssertionError) as exc:
        build_repl.assert_dist_complete(dist, with_coxswain=False)

    msg = str(exc.value).replace("\\", "/")
    assert "missing required staged path" in msg
    assert _DISPLAY_PY_INIT in msg
    # and only that one path is missing
    assert msg.count("\n  ") == 1, msg


def test_assert_dist_complete_requires_the_display_python_package_dir(tmp_path: Path) -> None:
    """No ``praxis/display/`` directory at all: still named."""
    dist = _make_dist_dir(tmp_path)
    _write_complete_dist(dist)
    (dist / _DISPLAY_PY_INIT).unlink()
    (dist / "assets" / "python" / "praxis" / "display").rmdir()

    with pytest.raises(build_repl.BuildAssertionError) as exc:
        build_repl.assert_dist_complete(dist, with_coxswain=False)

    assert _DISPLAY_PY_INIT in str(exc.value).replace("\\", "/")


def test_the_real_overlay_ships_the_display_python_package() -> None:
    """The source tree has what the dist requires: the overlay's ``praxis/display/__init__.py`` exists
    (``stage_overlay`` copies ``overlay/assets/`` wholesale, so this is what lands in dist)."""
    init = (
        Path(__file__).resolve().parents[1] / "overlay" / "assets" / "python" / "praxis" / "display" / "__init__.py"
    )
    assert init.is_file(), init


# --- C6: the 3D viewer paths (AC-33, local) -----------------------------------


def test_c6_positive_control_fixture_is_complete_and_carries_every_c6_path(
    tmp_path: Path,
) -> None:
    """Positive control for the negatives below: the complete fixture holds every C6 path, so a
    raise in a negative case is attributable to the one path that case removed."""
    dist = _make_dist_dir(tmp_path)
    _write_complete_dist(dist)

    for rel in _C6_DIST_PATHS:
        assert (dist / rel).is_file(), rel
    assert (dist / "shell" / "display" / "dock.js").is_file()
    build_repl.assert_dist_complete(dist, with_coxswain=False)  # must not raise


@pytest.mark.parametrize("missing", _C6_DIST_PATHS)
def test_assert_dist_complete_requires_each_c6_path(tmp_path: Path, missing: str) -> None:
    """Negative control: with exactly one C6 path missing it raises BuildAssertionError naming
    that path and nothing else."""
    dist = _make_dist_dir(tmp_path)
    _write_complete_dist(dist)
    (dist / missing).unlink()

    with pytest.raises(build_repl.BuildAssertionError) as exc:
        build_repl.assert_dist_complete(dist, with_coxswain=False)

    msg = str(exc.value).replace("\\", "/")
    assert "missing required staged path" in msg
    assert missing in msg
    assert msg.count("\n  ") == 1, msg


def test_assert_dist_complete_names_every_c6_path_when_none_shipped(tmp_path: Path) -> None:
    """Whole viewer tree absent (an overlay without sprint C): every C6 path is named."""
    dist = _make_dist_dir(tmp_path)
    _write_complete_dist(dist)
    for rel in _C6_DIST_PATHS:
        (dist / rel).unlink()

    with pytest.raises(build_repl.BuildAssertionError) as exc:
        build_repl.assert_dist_complete(dist, with_coxswain=False)

    msg = str(exc.value).replace("\\", "/")
    for rel in _C6_DIST_PATHS:
        assert rel in msg


def _stage_real_overlay(tmp_path: Path) -> Path:
    """The REAL overlay/assets/ through the production stage_overlay, into a temporary dist."""
    dist = _make_dist_dir(tmp_path)
    build_repl.stage_overlay(dist)
    return dist


def test_real_overlay_stages_every_c6_asset_path(tmp_path: Path) -> None:
    """stage_overlay copies overlay/assets/ wholesale, so the C6 paths need no staging change.
    Proven against the real tree, not assumed: each C6 path is a file in the staged dist and is
    byte-identical to its tracked source. dock.js is covered by the stage_shell real-source case."""
    dist = _stage_real_overlay(tmp_path)

    for rel in _C6_DIST_PATHS:
        staged = dist / rel
        assert staged.is_file(), f"{rel} was not staged from the real overlay"
        assert staged.read_bytes() == (_OVERLAY_ASSETS / rel.removeprefix("assets/")).read_bytes()


def test_manifest_collection_picks_up_viewer3d_and_no_vendored_plr_python() -> None:
    """AC-33 / Revision 10: the REAL overlay's manifest `sources` lists viewer3d.py (collect_sources
    walks assets/python recursively) and no path under assets/python/plr_visualizer3d/ (the
    viewer imports the pin's pylabrobot.visualizer3D from the PLR wheel; no PLR Python is vendored)."""
    import build_manifest  # noqa: PLC0415 -- scripts/ is on sys.path from the top of this file

    paths = {e["path"] for e in build_manifest.collect_sources(_OVERLAY_ASSETS.parent)}

    assert "assets/python/praxis/viz/viewer3d.py" in paths
    assert not [p for p in paths if "plr_visualizer3d" in p], sorted(paths)


def test_no_plr_visualizer3d_path_is_staged(tmp_path: Path) -> None:
    dist = _stage_real_overlay(tmp_path)
    assert not (dist / "assets" / "python" / "plr_visualizer3d").exists()
    # relative paths: pytest's tmp_path embeds this test's own name
    assert not [p for p in dist.rglob("*") if "plr_visualizer3d" in p.relative_to(dist).as_posix()]


# --- C6: offline, statically (AC-33: `--probe --offline` stays green) ---------
#
# The real proof is the browser gate (CI's `--probe --offline`). What can be said without a
# browser is that nothing the viewer ships names an external origin at load time, and that every
# file its module graph names is in the dist. Two instruments, each with a negative control.

# Hosts a viewer page must never load from. A hit anywhere in code (comments stripped) fails.
_CDN_HOSTS = (
    "unpkg.com", "cdnjs.cloudflare.com", "jsdelivr.net", "googleapis.com", "gstatic.com",
    "esm.sh", "skypack.dev", "rawgit.com", "githubusercontent.com",
)
_EXT = r"(?:https?:)?//[A-Za-z0-9][A-Za-z0-9.-]*"  # an external origin; protocol-relative too
_LOAD_RULES = {
    # A load-time reference is a tag attribute that fetches, a module specifier, a fetch-like
    # call, or a CSS url()/@import. <a href> and xmlns/namespace strings are navigation or
    # identifiers, not loads, and are deliberately not matched.
    "tag-attr": re.compile(
        rf"<(?:script|link|img|iframe|source|video|audio|embed|object|use|image)\b[^>]*?"
        rf"\b(?:src|href|data|poster|srcset|xlink:href)\s*=\s*[\"']?\s*{_EXT}",
        re.IGNORECASE,
    ),
    "module-specifier": re.compile(rf"\b(?:from|import)\s*\(?\s*[\"']{_EXT}"),
    "fetch-like": re.compile(
        rf"\b(?:fetch|importScripts)\s*\(\s*[\"']{_EXT}"
        rf"|\bnew\s+(?:Worker|SharedWorker|EventSource)\s*\(\s*[\"']{_EXT}"
        rf"|\.open\(\s*[\"'][A-Z]+[\"']\s*,\s*[\"']{_EXT}"
        rf"|\.(?:src|href)\s*=\s*[\"']{_EXT}"
    ),
    "css-url": re.compile(rf"@import\s+(?:url\()?\s*[\"']?{_EXT}|url\(\s*[\"']?{_EXT}", re.IGNORECASE),
    "import-map-value": re.compile(rf"[\"'][\w./@-]*[\"']\s*:\s*[\"']{_EXT}"),
    "cdn-host": re.compile("|".join(re.escape(h) for h in _CDN_HOSTS)),
}


def _strip_comments(text: str, suffix: str) -> str:
    """Drop comments so a URL in documentation or a license header is not a finding. Ignored:
    `/* ... */` and `<!-- ... -->` blocks, and a `//` line comment that starts a line or is set
    off by whitespace on both sides (prose style; a bare `//` inside code or the `://` of a URL is
    kept, which also stops a minified one-liner being eaten after a regex literal). CSS has only
    block comments."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    if suffix in (".html", ".htm"):
        text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    if suffix != ".css":
        text = re.sub(r"(?m)(?:^|(?<=\s))//(?=\s|$).*$", "", text)
    return text


def _offline_violations(root: Path) -> tuple[list[str], list[str]]:
    """Scan every html/js/mjs/css file under root. Returns (violations, scanned relative paths)."""
    violations: list[str] = []
    scanned: list[str] = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        if path.suffix not in (".html", ".htm", ".js", ".mjs", ".css"):
            continue
        rel = path.relative_to(root).as_posix()
        scanned.append(rel)
        code = _strip_comments(path.read_text(encoding="utf-8", errors="replace"), path.suffix)
        for rule, pattern in _LOAD_RULES.items():
            m = pattern.search(code)
            if m:
                violations.append(f"{rel}: {rule}: {m.group(0)[:100]!r}")
    return violations, scanned


_CDN_NEGATIVES = {
    "cdn-script-tag": ("index.html", '<script src="https://unpkg.com/three@0.170/build/three.module.js"></script>'),
    "protocol-relative-link": ("index.html", '<link rel="stylesheet" href="//fonts.example.org/css?f=x">'),
    "external-importmap": ("index.html", '<script type="importmap">{"imports":{"three":"https://example.org/three"}}</script>'),
    "static-import": ("a.js", 'import * as T from "https://example.org/three.js";'),
    "dynamic-import": ("a.js", 'const m = await import("https://example.org/m.js");'),
    "fetch": ("a.js", 'fetch("https://example.org/scene.json").then(r => r.json());'),
    "worker": ("a.js", 'new Worker("https://example.org/w.js");'),
    "src-assignment": ("a.js", 'img.src = "https://example.org/x.png";'),
    "css-import": ("a.css", '@import url("https://example.org/css?family=Roboto");'),
    "css-url": ("a.css", "body { background: url(http://example.org/bg.png); }"),
    "cdn-host-in-code": ("a.js", 'const base = ["https:", "", "cdnjs.cloudflare.com"].join("/");'),
}


def test_offline_scanner_positive_control_ignores_documentation_urls(tmp_path: Path) -> None:
    """URLs that are documentation, not loads, are not findings: block and line comments, a license
    header, an <a href>, an XML namespace string, and relative references."""
    (tmp_path / "ok.js").write_text(
        "/** @license see https://threejs.org/license */\n"
        "// docs: https://github.com/KhronosGroup/glTF/blob/master/README.md\n"
        "const ns = 'http://www.w3.org/1999/xhtml'; // https://unpkg.com/ only in a comment\n"
        'import * as T from "three"; import {a} from "./a.js"; fetch("./scene.json");\n'
    )
    (tmp_path / "ok.html").write_text(
        '<!-- <script src="https://unpkg.com/x.js"></script> -->\n'
        '<a href="https://github.com/x/y">docs</a>\n'
        '<script src="./vendor/gif.js"></script><link href="./main.css" rel="stylesheet">\n'
    )
    (tmp_path / "ok.css").write_text('/* url(https://x.invalid/a.png) */ a { background: url("./img/a.png"); }\n')

    violations, scanned = _offline_violations(tmp_path)

    assert violations == []
    assert sorted(scanned) == ["ok.css", "ok.html", "ok.js"]


@pytest.mark.parametrize("name", sorted(_CDN_NEGATIVES))
def test_offline_scanner_negative_control_flags_each_external_load(tmp_path: Path, name: str) -> None:
    """Each synthetic external load is flagged, so a clean result on the real tree means something."""
    fname, text = _CDN_NEGATIVES[name]
    (tmp_path / fname).write_text(text + "\n")

    violations, _scanned = _offline_violations(tmp_path)

    assert violations, f"{name}: the scanner missed an external load: {text}"


def test_staged_viewer_assets_make_no_external_load(tmp_path: Path) -> None:
    """The REAL staged viewer (page, vendored three.js and loaders, augmentations, dock.js) names no
    external origin at load time, and the scan really looked at the files that matter."""
    dist = _stage_real_overlay(tmp_path)
    build_repl.stage_shell(dist)

    violations: list[str] = []
    scanned: list[str] = []
    roots = (
        dist / "assets" / "visualizer3d",
        dist / "assets" / "visualizer3d-augmentations",
        dist / "shell" / "display",
    )
    for root in roots:
        v, s = _offline_violations(root)
        violations += [f"{root.name}/{x}" for x in v]
        scanned += [f"{root.name}/{x}" for x in s]

    assert violations == []
    for must in (
        "visualizer3d/index.html", "visualizer3d/boot.js", "visualizer3d/vendor/three.webgpu.min.js",
        "visualizer3d/vendor/three.core.min.js", "visualizer3d-augmentations/socket.js",
        "visualizer3d-augmentations/embed.js", "visualizer3d-augmentations/embed.css", "display/dock.js",
    ):
        assert must in scanned, f"the offline scan never looked at {must}"


_SPECIFIER = re.compile(
    r"""(?:\bfrom|\bimport)\s*\(?\s*["']((?:\.{1,2}/)[^"']+|three(?:/addons/[^"']+)?)["']"""
)
_PAGE_REF = re.compile(r"""<(?:script|link)\b[^>]*?\b(?:src|href)\s*=\s*["']([^"'#]+)["']""", re.IGNORECASE)
_IMPORT_MAP = re.compile(r"""<script\s+type=["']importmap["']\s*>(.*?)</script>""", re.DOTALL | re.IGNORECASE)


def _unresolved_page_refs(page: Path) -> list[str]:
    """Every file a page statically names that is not on disk: its own script/link references, and
    the module graph from each of them (relative specifiers, plus `three` and `three/addons/*`
    through the page's import map). External references are reported too. Returns 'from -> spec'."""
    html = _strip_comments(page.read_text(encoding="utf-8"), ".html")
    mapping: dict[str, str] = {}
    for block in _IMPORT_MAP.findall(html):
        mapping.update(json.loads(block).get("imports", {}))
    missing: list[str] = []
    queue = [(page, ref) for ref in _PAGE_REF.findall(html)]
    seen: set[Path] = set()
    while queue:
        origin, spec = queue.pop()
        if spec.startswith(("http:", "https:", "//", "data:")):
            missing.append(f"{origin.name} -> {spec} (external)")
            continue
        if spec == "three":
            target = (page.parent / mapping["three"]).resolve()
        elif spec.startswith("three/addons/"):
            addons = mapping["three/addons/"]
            target = (page.parent / addons / spec.removeprefix("three/addons/")).resolve()
        else:
            target = (origin.parent / spec).resolve()
        if not target.is_file():
            missing.append(f"{origin.name} -> {spec}")
        elif target.suffix in (".js", ".mjs") and target not in seen:
            seen.add(target)
            code = _strip_comments(target.read_text(encoding="utf-8", errors="replace"), ".js")
            queue += [(target, s) for s in _SPECIFIER.findall(code)]
    return missing


def test_page_closure_negative_control_reports_a_missing_module(tmp_path: Path) -> None:
    """A synthetic page whose module graph misses a file (two hops down) and a stylesheet is
    reported, so the clean result on the real page means the graph really resolved."""
    (tmp_path / "vendor").mkdir()
    (tmp_path / "vendor" / "three.js").write_text("export const T = 1;\n")
    (tmp_path / "boot.js").write_text('import "three"; import { x } from "./app.js";\n')
    (tmp_path / "app.js").write_text('import { y } from "./gone.js";\n')
    (tmp_path / "index.html").write_text(
        '<script type="importmap">{"imports":{"three":"./vendor/three.js","three/addons/":"./vendor/"}}</script>'
        '<script type="module" src="./boot.js"></script><link href="./nope.css" rel="stylesheet">'
    )

    missing = _unresolved_page_refs(tmp_path / "index.html")

    assert sorted(missing) == ["app.js -> ./gone.js", "index.html -> ./nope.css"]


def test_staged_viewer_page_module_graph_is_fully_staged(tmp_path: Path) -> None:
    """Every script, stylesheet and ES module the REAL staged viewer page names, transitively, is in
    the dist: the page cannot reach for a file the build dropped, which offline means a blank viewer."""
    dist = _stage_real_overlay(tmp_path)
    page = dist / "assets" / "visualizer3d" / "index.html"

    assert _unresolved_page_refs(page) == []
