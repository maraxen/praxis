"""Guards on the praxis theme overlay: it must stay committed, self-contained,
and it must keep winning the cascade against JupyterLab's own theme CSS.

No browser needed -- these are text/filesystem invariants. The visual result is
verified separately by the smoke gates and a manual pass.

Per ADR Sec 2.4 this file must NOT append ``web-repl/overlay/assets/python`` to
``sys.path``.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

_WEB_REPL_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT = _WEB_REPL_ROOT.parent
_THEME_DIR = _WEB_REPL_ROOT / "overlay" / "assets" / "theme"
_FONTS_DIR = _THEME_DIR / "fonts"
_CSS = _THEME_DIR / "praxis-theme.css"


def _css_text() -> str:
  return _CSS.read_text(encoding="utf-8")


def _css_rules() -> str:
  """CSS with /* comments */ stripped.

  Selector assertions must run against this, not the raw text: this file
  documents at length WHY it avoids `data-jp-theme-light` and the high-contrast
  theme, so a naive substring check against the raw source matches the prose
  explaining the rule and fails on a correct stylesheet.
  """
  return re.sub(r"/\*.*?\*/", "", _CSS.read_text(encoding="utf-8"), flags=re.DOTALL)


# --- the assets exist and are committed -------------------------------------


def test_theme_assets_present() -> None:
  for name in ("praxis-theme.css", "praxis-mark.svg", "praxis-favicon.svg"):
    assert (_THEME_DIR / name).is_file(), f"missing {name}"


def test_fonts_and_licenses_present() -> None:
  manifest = json.loads((_FONTS_DIR / "VENDOR_MANIFEST.json").read_text(encoding="utf-8"))
  assert manifest["entries"], "manifest lists zero entries -- a vacuous manifest"
  for entry in manifest["entries"]:
    assert (_FONTS_DIR / entry["file"]).is_file(), f"missing {entry['file']}"
  # OFL requires the licence ship alongside the fonts.
  licences = list(_FONTS_DIR.glob("OFL-*.txt"))
  assert len(licences) >= 2, f"expected an OFL per family, found {licences}"


@pytest.mark.parametrize(
  "rel",
  [
    "praxis-theme.css",
    "praxis-mark.svg",
    "praxis-favicon.svg",
    "fonts/RobotoFlex-Variable.woff2",
    "fonts/JetBrainsMono-Variable.woff2",
    "fonts/VENDOR_MANIFEST.json",
  ],
)
def test_theme_assets_are_not_gitignored(rel: str) -> None:
  """ADR Sec 5.4 hazard: bare patterns (dist/, wheels/, lib/) match at ANY
  depth, so a vendored subtree can be silently un-tracked and ship as a dead
  page.

  NOTE the exact invocation: ``git check-ignore -q`` WITHOUT ``-v``. With
  ``-v`` the command also matches NEGATION rules and exits 0 for a file that is
  not ignored at all, which inverts this assertion into a permanent pass.
  """
  proc = subprocess.run(
    ["git", "check-ignore", "-q", str((_THEME_DIR / rel).relative_to(_REPO_ROOT))],
    cwd=_REPO_ROOT,
    check=False,
  )
  assert proc.returncode == 1, f"{rel} is gitignored -- it would never reach dist/"


# --- self-containment (GATE G5 / offline boot) ------------------------------


def test_css_references_no_remote_urls() -> None:
  """A CDN font would break offline boot AND make a Google outage a red build."""
  css = _css_rules()
  assert "http://" not in css
  assert "https://" not in css
  assert "//fonts.googleapis" not in css


def test_every_css_url_resolves_on_disk() -> None:
  for ref in re.findall(r"url\(\s*([^)\s]+)\s*\)", _css_rules()):
    cleaned = ref.strip("'\"")
    assert (_THEME_DIR / cleaned).resolve().is_file(), f"CSS references missing {cleaned}"


def test_font_faces_cover_declared_files() -> None:
  css = _css_text()
  manifest = json.loads((_FONTS_DIR / "VENDOR_MANIFEST.json").read_text(encoding="utf-8"))
  for entry in manifest["entries"]:
    if entry.get("kind") == "license":
      continue
    assert entry["file"] in css, f"{entry['file']} vendored but never referenced by the CSS"


# --- cascade correctness ----------------------------------------------------


def test_jp_tokens_are_not_defined_on_bare_root() -> None:
  """The load-bearing invariant.

  JupyterLab's themes define --jp-* on ``:root`` in CSS injected at RUNTIME,
  i.e. after this stylesheet's static <link>. At equal specificity the later
  rule wins, so any --jp-* override sitting in a bare ``:root`` block here is
  dead on arrival. Overrides must be scoped to ``body[...]`` (0,1,1) to beat
  ``:root`` (0,1,0).
  """
  for block in re.findall(r"(^|\})\s*:root\s*\{(.*?)\}", _css_rules(), re.DOTALL):
    body = block[1]
    offenders = re.findall(r"(--jp-[\w-]+)\s*:", body)
    assert not offenders, (
      f"--jp-* tokens defined in a bare :root block will lose the cascade to "
      f"JupyterLab's runtime theme CSS: {offenders}"
    )


def test_high_contrast_theme_is_left_alone() -> None:
  """Repainting the high-contrast theme would destroy its accessibility promise."""
  rules = _css_rules()
  assert "JupyterLab Dark High Contrast" not in rules
  # Scoping by data-jp-theme-light would catch high-contrast too, since it also
  # reports "false" -- so that attribute must not be used for palette scoping.
  assert "data-jp-theme-light" not in rules


def test_both_retinted_themes_are_scoped_by_name() -> None:
  rules = _css_rules()
  assert "body[data-jp-theme-name='JupyterLab Dark']" in rules
  assert "body[data-jp-theme-name='JupyterLab Light']" in rules


def test_no_animation_is_introduced() -> None:
  """Same NFR-6 posture as coxswain.css: the floor is met by construction, so
  prefers-reduced-motion needs no exceptions. Adding motion here silently
  breaks that argument."""
  css = _css_rules()
  assert "@keyframes" not in css
  assert not re.search(r"^\s*transition\s*:", css, re.MULTILINE)
  assert not re.search(r"^\s*animation\s*:", css, re.MULTILINE)


def test_scrollbar_thumb_stays_a_bare_rgb_triplet() -> None:
  """JupyterLab consumes this token INSIDE rgba(); a hex value silently
  disables the scrollbar thumb rather than erroring."""
  for match in re.findall(r"--jp-scrollbar-thumb-color\s*:\s*([^;]+);", _css_rules()):
    assert re.fullmatch(r"\s*\d+\s*,\s*\d+\s*,\s*\d+\s*", match), (
      f"expected a bare 'r, g, b' triplet, got {match!r}"
    )


def test_brand_hexes_match_the_canonical_source() -> None:
  """styles.scss is the canonical design-language source; drift here means the
  REPL and the Angular client stop being the same brand."""
  css = _css_text()
  assert "#ED7A9B" in css, "rose pompadour ($rose-pompadour, styles.scss:13)"
  assert "#73A9C2" in css, "moonstone blue ($moonstone-blue, styles.scss:14)"
