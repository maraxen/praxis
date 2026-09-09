"""Tests for ``scripts/inject_branding.py`` -- the praxis <head> branding step.

These run against synthetic HTML in ``tmp_path``; nothing here needs a real
``dist/``, a browser, or Pyodide.

Per ADR Sec 2.4 this file must NOT append ``web-repl/overlay/assets/python`` to
``sys.path`` (it shadows the real top-level ``praxis`` package). It does not
need to: ``scripts/`` lives outside that subtree.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_WEB_REPL_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS_DIR = _WEB_REPL_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
  sys.path.insert(0, str(_SCRIPTS_DIR))

import inject_branding  # noqa: E402 -- path setup must precede this import

ANCHOR = '<link id="jupyter-lite-main" rel="preload" href="../build/lab/bundle.js" as="script">'

APP_HTML = f"""<!DOCTYPE html>
<html><head><title>JupyterLite</title>
{ANCHOR}
</head><body></body></html>
"""

ROOT_HTML = """<!DOCTYPE html>
<html><head><title>JupyterLite</title></head><body>redirect shell</body></html>
"""


def _make_dist(tmp_path: Path, *, apps=("lab", "repl"), with_root: bool = True) -> Path:
  """A minimal dist/ tree plus the theme assets the links must resolve to."""
  dist = tmp_path / "dist"
  for app in apps:
    (dist / app).mkdir(parents=True)
    (dist / app / "index.html").write_text(APP_HTML, encoding="utf-8")
  if with_root:
    dist.mkdir(parents=True, exist_ok=True)
    (dist / "index.html").write_text(ROOT_HTML, encoding="utf-8")
  theme = dist / "assets" / "theme"
  theme.mkdir(parents=True)
  (theme / "praxis-theme.css").write_text("/* stub */", encoding="utf-8")
  (theme / "praxis-favicon.svg").write_text("<svg/>", encoding="utf-8")
  return dist


def _run(dist: Path, *extra: str) -> int:
  return inject_branding.main(["--dist", str(dist), *extra])


# --- happy path -------------------------------------------------------------


def test_injects_app_and_root_then_checks_clean(tmp_path: Path) -> None:
  dist = _make_dist(tmp_path)
  assert _run(dist) == 0
  assert _run(dist, "--check") == 0

  lab = (dist / "lab" / "index.html").read_text(encoding="utf-8")
  assert "<title>praxis REPL</title>" in lab
  assert '<link rel="stylesheet" href="../assets/theme/praxis-theme.css">' in lab
  assert '<link rel="icon" type="image/svg+xml" href="../assets/theme/praxis-favicon.svg">' in lab
  # Injected before the anchor, i.e. inside <head>, so it lands before the bundle.
  assert lab.index(inject_branding._BEGIN_MARKER) < lab.index('id="jupyter-lite-main"')


def test_root_shell_uses_dot_slash_prefix(tmp_path: Path) -> None:
  """The root shell is one directory UP from the apps, so `../` would 404."""
  dist = _make_dist(tmp_path)
  assert _run(dist) == 0
  root = (dist / "index.html").read_text(encoding="utf-8")
  assert 'href="./assets/theme/praxis-theme.css"' in root
  assert "../assets/theme" not in root


def test_injection_is_idempotent(tmp_path: Path) -> None:
  """A second run must replace the block, not append a duplicate."""
  dist = _make_dist(tmp_path)
  assert _run(dist) == 0
  once = (dist / "lab" / "index.html").read_text(encoding="utf-8")
  assert _run(dist) == 0
  twice = (dist / "lab" / "index.html").read_text(encoding="utf-8")
  assert once == twice
  assert twice.count(inject_branding._BEGIN_MARKER) == 1
  assert twice.count("<title>") == 1


# --- fail-loud arms ---------------------------------------------------------


def test_missing_anchor_fails_rather_than_guessing(tmp_path: Path) -> None:
  dist = _make_dist(tmp_path, apps=("lab",), with_root=False)
  (dist / "lab" / "index.html").write_text(
    "<html><head><title>x</title></head></html>", encoding="utf-8"
  )
  # No anchor anywhere and no root shell -> nothing discoverable at all.
  assert _run(dist) == 1


def test_duplicated_anchor_is_ambiguous_and_fails(tmp_path: Path) -> None:
  dist = _make_dist(tmp_path, apps=("lab",), with_root=False)
  (dist / "lab" / "index.html").write_text(
    APP_HTML.replace(ANCHOR, ANCHOR + "\n" + ANCHOR), encoding="utf-8"
  )
  assert _run(dist) == 1


def test_check_fails_on_unbranded_dist(tmp_path: Path) -> None:
  dist = _make_dist(tmp_path)
  assert _run(dist, "--check") == 1


def test_check_fails_when_referenced_asset_is_missing(tmp_path: Path) -> None:
  """A <link> to a path that does not exist renders unstyled with no error."""
  dist = _make_dist(tmp_path)
  assert _run(dist) == 0
  (dist / "assets" / "theme" / "praxis-theme.css").unlink()
  assert _run(dist, "--check") == 1


def test_check_fails_when_title_was_reverted(tmp_path: Path) -> None:
  dist = _make_dist(tmp_path)
  assert _run(dist) == 0
  lab = dist / "lab" / "index.html"
  lab.write_text(
    lab.read_text(encoding="utf-8").replace("<title>praxis REPL</title>", "<title>JupyterLite</title>"),
    encoding="utf-8",
  )
  assert _run(dist, "--check") == 1


def test_begin_marker_without_end_marker_fails(tmp_path: Path) -> None:
  dist = _make_dist(tmp_path, apps=("lab",), with_root=False)
  lab = dist / "lab" / "index.html"
  lab.write_text(APP_HTML.replace(ANCHOR, inject_branding._BEGIN_MARKER + "\n" + ANCHOR), encoding="utf-8")
  assert _run(dist) == 1


def test_empty_dist_fails_rather_than_reporting_success(tmp_path: Path) -> None:
  """Branding nothing must not read as a green build."""
  assert _run(tmp_path / "nonexistent") == 1


def test_title_is_html_escaped(tmp_path: Path) -> None:
  dist = _make_dist(tmp_path, apps=("lab",), with_root=False)
  assert _run(dist, "--title", "a<b&c") == 0
  lab = (dist / "lab" / "index.html").read_text(encoding="utf-8")
  assert "<title>a&lt;b&amp;c</title>" in lab


# --- the real repo asset, not a stub ---------------------------------------


def test_theme_css_and_mark_exist_in_overlay() -> None:
  """inject_branding points at these; if they move, the links 404 silently."""
  theme = _WEB_REPL_ROOT / "overlay" / "assets" / "theme"
  assert (theme / "praxis-theme.css").is_file()
  assert (theme / "praxis-mark.svg").is_file()
  assert (theme / "praxis-favicon.svg").is_file()


# --- title handling differs by target class --------------------------------


def test_titleless_root_shell_gets_a_title_in_the_block(tmp_path: Path) -> None:
  """The real generated root shell ships with NO <title> (verified against a
  build). It is the page a visitor to the deployed site lands on, so leaving it
  advertising a bare URL is worse than emitting one."""
  dist = _make_dist(tmp_path, apps=("lab",))
  (dist / "index.html").write_text(
    "<!DOCTYPE html><html><head></head><body>redirect</body></html>", encoding="utf-8"
  )
  assert _run(dist) == 0
  root = (dist / "index.html").read_text(encoding="utf-8")
  assert root.count("<title>") == 1
  assert "<title>praxis REPL</title>" in root
  # It lives INSIDE the marker block, so a re-run replaces rather than stacks.
  assert root.index(inject_branding._BEGIN_MARKER) < root.index("<title>")
  assert _run(dist, "--check") == 0
  assert _run(dist) == 0
  assert (dist / "index.html").read_text(encoding="utf-8").count("<title>") == 1


def test_titleless_app_entry_still_fails(tmp_path: Path) -> None:
  """An app entry losing its <title> means the generated HTML changed shape --
  that must not be papered over."""
  dist = _make_dist(tmp_path, apps=("lab",), with_root=False)
  (dist / "lab" / "index.html").write_text(
    f"<!DOCTYPE html><html><head>{ANCHOR}</head><body></body></html>", encoding="utf-8"
  )
  assert _run(dist) == 1
