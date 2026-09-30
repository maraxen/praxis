"""Text invariants on the notebook-display rules appended to praxis-theme.css (A4, AC-4).

No browser needed. These check the stylesheet's *text*: that the status rail is
keyed on all five cell states, that prompts take no space, that the Light
ground/sheet/syntax palette is in place, that the `.praxis-out` mapping follows
D3, and that the file's load-bearing header rules (scope every `--jp-*`
override by theme name, leave High Contrast alone, add no animation) still hold
for the new rules. Whether the rules *look* right is verified by the D1 and
D1-dark scenarios (AC-7) on CI.

`test_theme_staging.py` owns the older invariants for the file as a whole; the
cases here repeat the three that the new rules could break, against a parser
that is itself exercised on synthetic CSS (positive AND negative controls), so a
parser that silently matches nothing cannot make a check pass.

CONFIRMED `--jp-mirror-editor-*` TOKEN NAMES (task A4, D10). Read from the
bundled themes at ``web-repl/dist/build/themes/@jupyterlab/theme-{light,dark}-extension/index.css``
(the 260828 dist, JupyterLab 4 / JupyterLite 0.8.1) and from the highlight
style in ``jlab_core`` that consumes them. Both themes define all 24:

  atom attribute bracket builtin comment def error header hr keyword link meta
  number operator property punctuation qualifier quote string-2 string tag
  variable-2 variable-3 variable            (each as ``--jp-mirror-editor-<name>-color``)

The CodeMirror 6 highlight style reads these 19: meta header keyword atom number
def builtin variable-2 punctuation property operator comment string string-2
bracket tag attribute quote link. It has no "function call" tag, so the design's
"call" colour goes on `def` (function definitions), `builtin` (print, len, ...)
and `property` (the ``lh.pick_up_tips`` of a method call), and `meta`.

This test does not append ``web-repl/overlay/assets/python`` to ``sys.path``
(ADR Sec 2.4).

CLASS COVERAGE (task B-css, backlog #5669). The reprs of B2 (labware), B3 (deck) and B4 (ledger,
glossary) emit a class vocabulary of their own (``praxis-name*``, ``praxis-summary``, ``praxis-fig``,
``praxis-ledger__*``, ``sv-*``, ...). Two checks keep the stylesheet complete against it:

* a STATIC one that scans the string literals of ``praxis/display/*.py`` (no PyLabRobot, always runs), and
* a RENDERED one that draws real outputs from the design fixture under the PLR 1.0.0b1 pin and collects
  every ``class`` value in the HTML. It skips, with an explicit reason, when the interpreter's PLR is not
  the pin (run with ``PYTHONPATH=<PLR 1.0.0b1 source>`` prepended).

Both assert that every emitted ``praxis-*`` / ``sv-*`` class appears in some selector of
``praxis-theme.css``, and are themselves exercised on synthetic input: a class with no rule must FAIL.
"""

from __future__ import annotations

import asyncio
import importlib
import importlib.util
import re
import sys
import types
from pathlib import Path

import pytest

_WEB_REPL_ROOT = Path(__file__).resolve().parents[1]
_THEME_DIR = _WEB_REPL_ROOT / "overlay" / "assets" / "theme"
_CSS = _THEME_DIR / "praxis-theme.css"
_DIST_THEMES = _WEB_REPL_ROOT / "dist" / "build" / "themes" / "@jupyterlab"

_DISPLAY_DIR = _WEB_REPL_ROOT / "overlay" / "assets" / "python" / "praxis" / "display"
_FIXTURE_PATH = _WEB_REPL_ROOT / "design" / "notebook-display" / "make_fixture.py"
_PKG = "_praxis_display_css_under_test"

_LIGHT = "body[data-jp-theme-name='JupyterLab Light']"

# The design's colours (DESIGN.md "Color" and "Syntax").
_STEEL = "#EEF1F4"
_SHEET = "#FFFFFF"
_INK = "#1D2935"
_INK_SOFT = "#56636F"
_RAIL = "#C9D2DA"
_MOONSTONE = "#73A9C2"
_MOON_INK = "#2F6882"
_ROSE = "#ED7A9B"
_ROSE_INK = "#B8436A"
_BRICK = "#B3402A"

# Hexes a `.praxis-*` rule may carry literally (section 4: moonstone, rose, rose ink, brick).
_ALLOWED_LITERAL_HEXES = {_MOONSTONE, _ROSE, _ROSE_INK, _BRICK}

# Confirmed against the bundled themes (see the docstring). The test reads the
# dist too when it is present; this constant is what keeps the check alive when
# it is not (a fresh worktree has no dist).
_CONFIRMED_MIRROR_TOKENS = frozenset(
  f"--jp-mirror-editor-{name}-color"
  for name in (
    "atom attribute bracket builtin comment def error header hr keyword link meta "
    "number operator property punctuation qualifier quote string-2 string tag "
    "variable-2 variable-3 variable"
  ).split()
)

_CELL_STATES = ("not-run", "ran", "running", "error", "stale")

_NAMED_COLOURS = {
  "white", "black", "red", "green", "blue", "gray", "grey", "orange", "yellow",
  "purple", "pink", "brown", "cyan", "magenta", "navy", "teal", "silver",
}  # fmt: skip


# --- a small CSS reader (its controls are at the bottom of this section) -----


def _strip_comments(text: str) -> str:
  return re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)


def _split_top_level(text: str, sep: str) -> list[str]:
  """Split on `sep` outside parentheses and brackets (`:is(a, b)`, `[x='a,b']`)."""
  parts, depth, quote, buf = [], 0, "", []
  for ch in text:
    if quote:
      buf.append(ch)
      if ch == quote:
        quote = ""
      continue
    if ch in "'\"":
      quote = ch
    elif ch in "([":
      depth += 1
    elif ch in ")]":
      depth -= 1
    elif ch == sep and depth == 0:
      parts.append("".join(buf).strip())
      buf = []
      continue
    buf.append(ch)
  tail = "".join(buf).strip()
  if tail:
    parts.append(tail)
  return parts


class _Rule:
  def __init__(self, selector_text: str, body: str) -> None:
    self.selector_text = " ".join(selector_text.split())
    self.selectors = [" ".join(s.split()) for s in _split_top_level(selector_text, ",")]
    self.decls: dict[str, str] = {}
    for decl in _split_top_level(body, ";"):
      if ":" in decl:
        prop, _, value = decl.partition(":")
        self.decls[prop.strip()] = " ".join(value.split())

  def __repr__(self) -> str:  # pragma: no cover - failure messages only
    return f"<{self.selector_text} {{ {self.decls} }}>"


def _parse(css: str) -> list[_Rule]:
  """Flat rules (no nested blocks; this file has no @media/@supports)."""
  rules = []
  for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", _strip_comments(css)):
    rules.append(_Rule(m.group(1).strip(), m.group(2)))
  return rules


def _rules() -> list[_Rule]:
  return _parse(_CSS.read_text(encoding="utf-8"))


def _rules_where(pred) -> list[_Rule]:
  return [r for r in _rules() if pred(r)]


def _effective(selector: str, prop: str, rules: list[_Rule] | None = None) -> str | None:
  """Last value `prop` takes in rules whose selector list contains `selector` exactly."""
  value = None
  for rule in rules if rules is not None else _rules():
    if selector in rule.selectors and prop in rule.decls:
      value = rule.decls[prop]
  return value


def _colour_literals(value: str) -> list[str]:
  """Colour literals in a declaration value: hex, rgb/hsl functions, named colours."""
  found = re.findall(r"#[0-9a-fA-F]{3,8}\b", value)
  found += re.findall(r"\b(?:rgb|rgba|hsl|hsla|hwb|lab|lch|oklab|oklch)\(", value)
  found += [w for w in re.findall(r"\b[a-z]+\b", re.sub(r"var\([^)]*\)", "", value)) if w in _NAMED_COLOURS]
  return found


def _animation_violations(css: str) -> list[str]:
  css = _strip_comments(css)
  bad = []
  if "@keyframes" in css:
    bad.append("@keyframes")
  for prop in ("transition", "animation"):
    if re.search(rf"(^|[;{{\s]){prop}(-[a-z-]+)?\s*:", css):
      bad.append(prop)
  return bad


def _colour_violations(rules: list[_Rule]) -> list[str]:
  """Colours in `.praxis-*` rules that are neither a token nor a DESIGN hex."""
  bad = []
  for rule in rules:
    if ".praxis-" not in rule.selector_text:
      continue
    for prop, value in rule.decls.items():
      for lit in _colour_literals(value):
        if lit.upper() not in _ALLOWED_LITERAL_HEXES:
          bad.append(f"{rule.selector_text} {{ {prop}: {value} }} -> {lit}")
  return bad


# --- controls on the reader itself -------------------------------------------


def test_reader_parses_the_real_file_and_a_synthetic_one() -> None:
  """Positive control: the parser sees rules at all, and reads a known synthetic block."""
  # The file had 15 rules before A4; a reader that finds fewer is dropping some.
  assert len(_rules()) >= 15, "parsed too few rules from praxis-theme.css -- the reader is broken"
  synthetic = _parse("/* c */ a, :is(b, c) > d { color: #fff; --x: 1 }")
  assert synthetic[0].selectors == ["a", ":is(b, c) > d"]
  assert synthetic[0].decls == {"color": "#fff", "--x": "1"}


def test_animation_check_fires_on_synthetic_animation() -> None:
  """Negative control: the check must be able to fail."""
  assert _animation_violations(".a { transition: all 1s }") == ["transition"]
  assert _animation_violations(".a { animation-name: x }") == ["animation"]
  assert _animation_violations("@keyframes k { from { top: 0 } }") == ["@keyframes"]
  assert _animation_violations("/* animation: none */ .a { color: red }") == []


def test_colour_check_fires_on_synthetic_bad_colour() -> None:
  """Negative control for the colour rule: a stray hex, rgb() and a keyword are all flagged."""
  bad = _colour_violations(_parse(".praxis-x { color: #123456; background: rgba(0,0,0,.1); fill: red }"))
  assert len(bad) == 3, bad
  ok = _colour_violations(
    _parse(".praxis-x { color: var(--jp-content-font-color0); border-color: #B3402A; fill: none }")
  )
  assert ok == []


# --- header rules, restated for the new rules ---------------------------------


def test_no_animation_anywhere_in_the_file() -> None:
  """NFR-6: this file adds zero transitions and zero keyframes (D10)."""
  assert _animation_violations(_CSS.read_text(encoding="utf-8")) == []


def test_high_contrast_and_light_flag_are_not_named() -> None:
  css = _strip_comments(_CSS.read_text(encoding="utf-8"))
  assert "High Contrast" not in css
  assert "data-jp-theme-light" not in css


def test_every_jp_override_is_scoped_to_a_theme_name() -> None:
  """No `--jp-*` declaration outside `body[data-jp-theme-name=...]` / the pre-theme first paint.

  A bare `:root`, `html` or unscoped selector loses to JupyterLab's runtime theme CSS.
  """
  offenders = []
  for rule in _rules():
    if not any(p.startswith("--jp-") for p in rule.decls):
      continue
    for sel in rule.selectors:
      if not (sel.startswith("body[data-jp-theme-name=") or sel.startswith("body:not([data-jp-theme-name])")):
        offenders.append(sel)
  assert not offenders, f"--jp-* declared under selectors that lose the cascade: {offenders}"


def test_light_jp_overrides_carry_the_light_name_only() -> None:
  """Every `--jp-mirror-editor-*` override, and every layout override that replaces cream,
  sits under the Light body selector alone (D10: the syntax palette is Light only)."""
  for rule in _rules():
    if any(p.startswith("--jp-mirror-editor-") for p in rule.decls):
      assert rule.selectors == [_LIGHT], f"mirror-editor tokens outside Light only: {rule.selectors}"


# --- tokens ---------------------------------------------------------------------


@pytest.mark.parametrize(
  ("token", "hex_"),
  [
    ("--praxis-moonstone", _MOONSTONE),
    ("--praxis-moonstone-ink", _MOON_INK),
    ("--praxis-rose", _ROSE),
    ("--praxis-rose-ink", _ROSE_INK),
    ("--praxis-brick", _BRICK),
  ],
)
def test_brand_constants_exist_on_root(token: str, hex_: str) -> None:
  """Brand constants live on :root (nothing in JupyterLab defines them, so no cascade fight)."""
  value = _effective(":root", token)
  assert value is not None, f"{token} is not declared on :root"
  assert value.upper() == hex_, f"{token} is {value}, DESIGN.md says {hex_}"


def test_praxis_tokens_are_not_jp_tokens_on_root() -> None:
  """`:root` carries no `--jp-*` (repeats the header rule against the new constants)."""
  for rule in _rules():
    if ":root" in rule.selectors:
      assert not [p for p in rule.decls if p.startswith("--jp-")], rule


# --- the status rail ------------------------------------------------------------

_CHROME_SCOPE_RE = re.compile(r"JupyterLab Dark'\].*JupyterLab Light'\]|JupyterLab Light'\].*JupyterLab Dark'\]")


def _rail_rule(state: str) -> _Rule | None:
  """The `::before` rail rule keyed on `data-praxis-cell-state=<state>`."""
  for rule in _rules():
    for sel in rule.selectors:
      if f"[data-praxis-cell-state='{state}']" in sel and sel.endswith("::before"):
        return rule
  return None


@pytest.mark.parametrize("state", _CELL_STATES)
def test_rail_has_a_rule_for_every_cell_state(state: str) -> None:
  assert _rail_rule(state) is not None, (
    f"no `[data-praxis-cell-state='{state}']::before` rail rule (section 3.1; chrome.js sets the attribute)"
  )


def test_rail_colours_match_section_3_1() -> None:
  """not run: rail grey (`--jp-border-color1`, AC-7 dark); ran: moonstone ink; running: rose;
  error: brick; stale: dashed moonstone ink."""

  def bg(state: str) -> str:
    rule = _rail_rule(state)
    assert rule is not None, state
    return rule.decls.get("background", "")

  assert bg("not-run") == "var(--jp-border-color1)"
  assert bg("ran") == "var(--praxis-moonstone-ink)"
  assert bg("running") == "var(--praxis-rose)"
  assert bg("error") == "var(--praxis-brick)"
  stale = bg("stale")
  assert stale.startswith("repeating-linear-gradient(") and "var(--praxis-moonstone-ink)" in stale, stale


def test_rail_is_three_px_on_code_cells_only() -> None:
  base = _rules_where(lambda r: any(s.endswith(".jp-CodeCell::before") for s in r.selectors))
  assert base, "no base `.jp-CodeCell::before` rail rule"
  decls = {}
  for rule in base:
    decls.update(rule.decls)
  assert decls.get("width") == "3px"
  assert decls.get("content") in {"''", '""'}
  assert decls.get("position") == "absolute"


def test_stale_also_uses_jupyterlabs_native_dirty_hook() -> None:
  """S1: `jp-mod-dirty` on the cell is a native CSS hook for `stale`. It must yield to
  `running` (precedence running > stale) and to `not-run` (an edited cell that never ran
  stays not-run), which are model states only chrome.js can see."""
  native = _rules_where(lambda r: any("jp-mod-dirty" in s and s.endswith("::before") for s in r.selectors))
  assert native, "no rail rule on `.jp-mod-dirty` (S1's native stale hook)"
  for rule in native:
    for sel in (s for s in rule.selectors if "jp-mod-dirty" in s):
      assert ":not([data-praxis-cell-state='running'])" in sel, sel
      assert ":not([data-praxis-cell-state='not-run'])" in sel, sel
  assert native[-1].decls.get("background", "").startswith("repeating-linear-gradient(")


def test_error_is_not_keyed_on_the_stderr_mime() -> None:
  """S1 recorded `error` as the CSS feature `mime:application/vnd.jupyter.stderr`, but that
  mime is also every plain stderr stream (warnings), which is not an error. `error` is keyed
  on `data-praxis-cell-state='error'` only; no rail rule may use the stderr mime."""
  for rule in _rules():
    for sel in rule.selectors:
      if sel.endswith("::before") and ".jp-CodeCell" in sel:
        assert "vnd.jupyter.stderr" not in sel, sel


def test_chrome_rules_apply_to_dark_and_light_and_not_high_contrast() -> None:
  chrome = _rules_where(
    lambda r: any(
      "data-praxis-cell-state" in s or "jp-InputPrompt" in s or "jp-OutputPrompt" in s
      for s in r.selectors
    )
  )
  assert chrome, "no chrome rules"
  for rule in chrome:
    for sel in rule.selectors:
      assert _CHROME_SCOPE_RE.search(sel) and "High" not in sel, (
        f"chrome selector must name both Dark and Light: {sel}"
      )


def test_exec_count_sits_on_the_rail_from_data_praxis_exec() -> None:
  """The count is `attr(data-praxis-exec)` (chrome.js writes it) in 12.5px ink-soft."""
  rules = _rules_where(lambda r: r.decls.get("content") == "attr(data-praxis-exec)")
  assert rules, "no rule renders `attr(data-praxis-exec)`"
  decls = rules[-1].decls
  assert decls.get("font-size") == "12.5px"
  assert decls.get("color") == "var(--jp-content-font-color2)"


# --- prompts ----------------------------------------------------------------------


@pytest.mark.parametrize("prompt", [".jp-InputPrompt", ".jp-OutputPrompt", ".jp-OutputArea-prompt"])
def test_prompts_take_no_space(prompt: str) -> None:
  """AC-7 `prompts_take_no_space`: each prompt's width is <= 1 px, in every cell."""
  rules = _rules_where(lambda r: any(s.endswith(prompt) for s in r.selectors))
  merged: dict[str, str] = {}
  for rule in rules:
    if any("body:is(" in s for s in rule.selectors):
      merged.update(rule.decls)
  assert merged, f"no scoped rule for {prompt}"
  assert merged.get("width") in {"0", "0px"}, merged
  assert merged.get("flex") in {"0 0 0", "0 0 0px"}, merged
  assert merged.get("padding") in {"0", "0px"}, merged
  assert merged.get("margin") in {"0", "0px"}, merged
  assert merged.get("border") in {"0", "none", "0px"}, merged


def test_dirty_prompt_bullet_is_removed() -> None:
  """JupyterLab paints a warn-coloured bullet in the prompt of a dirty cell (`::before`)."""
  rules = _rules_where(lambda r: any(s.endswith(".jp-InputPrompt::before") for s in r.selectors))
  assert rules and rules[-1].decls.get("content") == "none"


def test_outputs_are_inset_under_their_code_with_one_hairline() -> None:
  rules = _rules_where(lambda r: any(s.endswith(".jp-Cell-outputWrapper") for s in r.selectors))
  merged: dict[str, str] = {}
  for rule in rules:
    merged.update(rule.decls)
  assert merged.get("border-top") == "1px solid var(--jp-border-color1)", merged


# --- Light ground, sheet and syntax palette (D10) ---------------------------------


def test_light_carries_the_steel_ground_and_white_sheet() -> None:
  """Cream is replaced. The effective values (last declaration wins) are steel and white."""
  assert (_effective(_LIGHT, "--jp-layout-color1") or "").upper() == _STEEL
  assert (_effective(_LIGHT, "--jp-layout-color0") or "").upper() == _SHEET
  cream = {"#FFFDF5", "#FBF9E6", "#F5F2D1", "#ECE9C4"}
  for i in range(5):
    value = (_effective(_LIGHT, f"--jp-layout-color{i}") or "").upper()
    assert value and value not in cream, f"--jp-layout-color{i} is still cream: {value}"


def test_light_ground_and_sheet_are_applied_to_the_notebook_and_its_cells() -> None:
  ground = _rules_where(lambda r: f"{_LIGHT} .jp-Notebook" in r.selectors)
  assert ground and ground[-1].decls.get("background") == "var(--jp-layout-color1)", ground
  sheet = _rules_where(lambda r: f"{_LIGHT} .jp-Notebook .jp-CodeCell" in r.selectors)
  assert sheet and sheet[-1].decls.get("background") == "var(--jp-layout-color0)", sheet


def test_light_ink_and_rail_tokens() -> None:
  """D3 maps ink, ink soft and rail onto these tokens, so Light must set them to the design's."""
  assert (_effective(_LIGHT, "--jp-content-font-color0") or "").upper() == _INK
  assert (_effective(_LIGHT, "--jp-content-font-color2") or "").upper() == _INK_SOFT
  assert (_effective(_LIGHT, "--jp-border-color1") or "").upper() == _RAIL


@pytest.mark.parametrize(
  ("token", "hex_"),
  [
    ("keyword", "#2F6882"),
    ("atom", "#2F6882"),
    ("string", "#A63D61"),
    ("string-2", "#A63D61"),
    ("number", "#8A5A00"),
    ("def", "#7B4FA0"),
    ("builtin", "#7B4FA0"),
    ("property", "#7B4FA0"),
    ("comment", "#56636F"),
  ],
)
def test_light_syntax_palette(token: str, hex_: str) -> None:
  value = _effective(_LIGHT, f"--jp-mirror-editor-{token}-color")
  assert value is not None, f"--jp-mirror-editor-{token}-color not set under Light"
  assert value.upper() == hex_


def test_mirror_editor_tokens_used_are_confirmed_names() -> None:
  """A token name JupyterLab does not define is a silent no-op, so every name overridden here
  must be one of the confirmed names."""
  used = {p for r in _rules() for p in r.decls if p.startswith("--jp-mirror-editor-")}
  assert used, "no --jp-mirror-editor-* overrides at all"
  assert used <= _CONFIRMED_MIRROR_TOKENS, sorted(used - _CONFIRMED_MIRROR_TOKENS)


def test_confirmed_mirror_token_names_against_the_bundled_themes() -> None:
  """Re-confirms the constant against the built dist. Skipped with a reason when the dist is
  absent (it is a build output; a fresh checkout or worktree does not have it)."""
  light = _DIST_THEMES / "theme-light-extension" / "index.css"
  dark = _DIST_THEMES / "theme-dark-extension" / "index.css"
  if not (light.is_file() and dark.is_file()):
    pytest.skip(f"{_DIST_THEMES} absent: build with build_repl.py to confirm token names against the bundle")
  for path in (light, dark):
    defined = set(re.findall(r"(--jp-mirror-editor-[a-z0-9-]+-color)\s*:", path.read_text(encoding="utf-8")))
    assert _CONFIRMED_MIRROR_TOKENS <= defined, (path, sorted(_CONFIRMED_MIRROR_TOKENS - defined))
    used = {p for r in _rules() for p in r.decls if p.startswith("--jp-mirror-editor-")}
    assert used <= defined, (path, sorted(used - defined))


# --- .praxis-out token mapping (D3) -------------------------------------------------


def _out_rules() -> list[_Rule]:
  return _rules_where(lambda r: any(s.startswith(".praxis-out") for s in r.selectors))


def _mapped(attr: str, hex_: str) -> str | None:
  """The token a `.praxis-out [<attr>='<hex>']` rule maps that colour to."""
  prop = attr
  for rule in _out_rules():
    for sel in rule.selectors:
      if f"[{attr}='{hex_}' i]" in sel:
        return rule.decls.get(prop)
  return None


@pytest.mark.parametrize("attr", ["fill", "stroke"])
@pytest.mark.parametrize(
  ("hex_", "token"),
  [
    (_SHEET, "var(--jp-layout-color0)"),
    (_INK, "var(--jp-content-font-color0)"),
    (_INK_SOFT, "var(--jp-content-font-color2)"),
    (_RAIL, "var(--jp-border-color1)"),
  ],
)
def test_praxis_out_maps_structural_colours_to_tokens(attr: str, hex_: str, token: str) -> None:
  assert _mapped(attr, hex_) == token, f"`.praxis-out [{attr}='{hex_}' i]` should set {attr}: {token}"


def test_praxis_out_leaves_the_brand_constants_alone() -> None:
  """Only moonstone (liquid), rose (attention) and brick (error marks) stay brand constants."""
  for rule in _out_rules():
    for sel in rule.selectors:
      for hex_ in (_MOONSTONE, _ROSE, _BRICK):
        assert hex_.lower() not in sel.lower(), f"{sel} remaps a brand constant"


def test_praxis_out_error_text_uses_the_error_token() -> None:
  rules = _rules_where(lambda r: any(s.startswith(".praxis-out .praxis-error__title") for s in r.selectors))
  assert rules and rules[-1].decls.get("color") == "var(--jp-error-color1)"


def test_praxis_out_is_not_theme_scoped() -> None:
  """D3: outputs follow Dark, Light and High Contrast 'without the stylesheet naming any
  theme', so no `.praxis-out` selector mentions a theme."""
  for rule in _out_rules():
    for sel in rule.selectors:
      assert "data-jp-theme" not in sel, sel


# --- the stale notice, error panel, readout, focus ring, deck panel --------------------


def _has(selector: str) -> _Rule:
  rules = _rules_where(lambda r: selector in r.selectors)
  assert rules, f"no rule for `{selector}`"
  merged = _Rule(selector, "")
  for r in rules:
    merged.decls.update(r.decls)
  return merged


def test_error_panel_has_a_brick_rail() -> None:
  panel = _has(".praxis-error")
  assert panel.decls.get("border-left") == "3px solid var(--praxis-brick)", panel
  _has(".praxis-error__title")
  _has(".praxis-error__plr")


def test_traceback_accents_are_brick_and_use_the_code_face() -> None:
  rules = _rules_where(lambda r: any("vnd.jupyter.stderr" in s and "jp-OutputArea-output" in s for s in r.selectors))
  assert rules, "no restyle of JupyterLab's error output (section 3.1 Tracebacks)"
  merged: dict[str, str] = {}
  for r in rules:
    merged.update(r.decls)
  assert merged.get("border-left") == "3px solid var(--praxis-brick)", merged
  assert merged.get("font-family") == "var(--praxis-code-font)", merged


def test_stale_notice_is_a_rose_marked_note() -> None:
  notice = _has(".praxis-stale")
  assert "var(--praxis-rose)" in notice.decls.get("border-left", ""), notice
  assert notice.decls.get("color") == "var(--jp-content-font-color2)"


def test_hover_readout_is_positioned_by_the_shell_and_never_takes_the_pointer() -> None:
  readout = _has(".praxis-readout")
  assert readout.decls.get("position") == "fixed"
  assert readout.decls.get("pointer-events") == "none"
  assert "box-shadow" not in readout.decls, "the design has no drop shadows"


def test_focus_ring_and_focused_output_are_rose() -> None:
  ring = _has(".praxis-focus-ring")
  assert ring.decls.get("stroke") == "var(--praxis-rose)"
  assert ring.decls.get("fill") == "none"
  focus = _has(".jp-OutputArea-output.is-focus")
  assert "var(--praxis-rose)" in focus.decls.get("outline", ""), focus
  keyboard = _rules_where(lambda r: any(s.startswith(".praxis-out") and "focus-visible" in s for s in r.selectors))
  assert keyboard and "var(--praxis-rose)" in keyboard[-1].decls.get("outline", "")


@pytest.mark.parametrize(
  "selector",
  [
    ".praxis-deck-panel",
    ".praxis-deck-panel__header",
    ".praxis-deck-panel__title",
    ".praxis-deck-panel__footer",
    ".praxis-deck-panel__motion",
  ],
)
def test_deck_panel_header_and_footer_are_styled(selector: str) -> None:
  _has(selector)


def test_deck_panel_header_and_footer_are_divided_by_hairlines() -> None:
  assert _has(".praxis-deck-panel__header").decls.get("border-bottom") == "1px solid var(--jp-border-color1)"
  assert _has(".praxis-deck-panel__footer").decls.get("border-top") == "1px solid var(--jp-border-color1)"


# --- colour discipline ------------------------------------------------------------------


def test_praxis_rules_use_tokens_or_the_design_hexes_only() -> None:
  """Section 4: every colour in a `.praxis-*` rule is `var(--jp-*)`, `var(--praxis-*)` or one
  of the DESIGN hexes for moonstone, rose, rose ink or brick."""
  assert [r for r in _rules() if ".praxis-" in r.selector_text], "no `.praxis-*` rules to check"
  assert _colour_violations(_rules()) == []


def test_praxis_var_references_resolve() -> None:
  """A `var(--praxis-*)` that nothing declares is a silent no-op."""
  css = _strip_comments(_CSS.read_text(encoding="utf-8"))
  declared = set(re.findall(r"(--praxis-[\w-]+)\s*:", css))
  used = set(re.findall(r"var\((--praxis-[\w-]+)", css))
  assert used <= declared, sorted(used - declared)


# The only selectors that may carry moonstone (liquid): the ledger's volume bar and the drawn liquid.
_VOLUME_SELECTOR_MARKS = ("praxis-ledger__bar", "sv-liquid")


def _blue_violations(rules: list[_Rule]) -> list[str]:
  """Moonstone in a `.praxis-*` / `.sv-*` rule whose selectors are not all volume marks; moonstone ink
  (text/links/done state) is never allowed there."""
  bad = []
  for rule in rules:
    if ".praxis-" not in rule.selector_text and ".sv-" not in rule.selector_text:
      continue
    volume_only = all(any(mark in sel for mark in _VOLUME_SELECTOR_MARKS) for sel in rule.selectors)
    for prop, value in rule.decls.items():
      low = value.lower()
      if "moonstone-ink" in low or _MOON_INK.lower() in low:
        bad.append(f"{rule.selector_text}: {prop}: {value} (moonstone ink)")
      elif ("moonstone" in low or _MOONSTONE.lower() in low) and not volume_only:
        bad.append(f"{rule.selector_text}: {prop}: {value} (blue that is not volume)")
  return bad


def test_blue_means_volume_only() -> None:
  """No `.praxis-*` / `.sv-*` rule uses moonstone (liquid) or moonstone ink, except the ledger's volume
  bar and the drawn liquid (`.sv-liquid`). The rail's `ran` and `stale` marks (section 3.1) are the only
  chrome that uses moonstone ink, and they are not `.praxis-*`."""
  assert _blue_violations(_rules()) == []


def test_blue_check_fires_on_synthetic_non_volume_blue() -> None:
  """Negative control: blue on a summary, and moonstone ink on the bar, are both flagged; the bar
  and the liquid in plain moonstone are not (positive control)."""
  bad = _blue_violations(_parse(
    ".praxis-summary { color: var(--praxis-moonstone) } "
    ".praxis-ledger__bar rect { fill: var(--praxis-moonstone-ink) } "
    ".praxis-out .sv-plate { stroke: #73A9C2 }"
  ))
  assert len(bad) == 3, bad
  assert _blue_violations(_parse(
    ".praxis-ledger__bar rect { fill: var(--praxis-moonstone) } "
    ".praxis-out .sv-liquid { fill: var(--praxis-moonstone) }"
  )) == []


# --- class coverage: every class the display reprs emit has a rule (task B-css) -----------------

_EMITTED_CLASS_RE = re.compile(r"(?:praxis|sv)-[A-Za-z0-9_-]+")
# A class literal in Python source: a quoted string of one or more space-separated praxis-/sv- classes.
# `data-praxis-res` does not match (the quote is followed by `data`), and an f-string class such as
# `f"praxis-{kind}"` does not match either (the `{` breaks the literal); those are listed below.
_LITERAL_CLASSES_RE = re.compile(r"""["']((?:(?:praxis|sv)-[A-Za-z0-9_-]+)(?: (?:praxis|sv)-[A-Za-z0-9_-]+)*)["']""")

# Classes built by f-strings in the display modules: the output root per kind (labware.render_html,
# deck.render_html, ledger.render_html) and the ledger row status (ledger._row_html). The rendered
# check proves each is actually emitted; this list keeps the static check honest about them.
_FAMILY_CLASSES = (
  "praxis-plate", "praxis-tiprack", "praxis-container", "praxis-deck", "praxis-ledger",
  "praxis-ledger__row--ok", "praxis-ledger__row--in-flight", "praxis-ledger__row--error",
  "praxis-details-summary", "praxis-details-body",  # svg.details_html: f"{cls}-summary" / "-body"
)  # fmt: skip

# Classes the shell or a later task owns; they carry rules of their own already (A4) and are not
# checked against the reprs. None of them starts with `praxis-`/`sv-` and is emitted by B2-B4, so the
# set is empty today; it exists so an exception has to be written down here.
_SHELL_OWNED: frozenset[str] = frozenset()


def _selector_classes(rules: list[_Rule]) -> set[str]:
  """Every `.praxis-*` / `.sv-*` class named by any selector (attribute values are stripped first,
  so `[fill='#FFF']` cannot masquerade as a class)."""
  found: set[str] = set()
  for rule in rules:
    for sel in rule.selectors:
      bare = re.sub(r"\[[^\]]*\]", "", sel)
      found.update(re.findall(r"\.((?:praxis|sv)-[A-Za-z0-9_-]+)", bare))
  return found


def _uncovered(emitted: set[str], rules: list[_Rule]) -> list[str]:
  """Emitted `praxis-*` / `sv-*` classes with no selector in *rules* (shell-owned ones excluded)."""
  have = _selector_classes(rules)
  return sorted(c for c in emitted if _EMITTED_CLASS_RE.fullmatch(c) and c not in have and c not in _SHELL_OWNED)


def _classes_in_html(html: str) -> set[str]:
  found: set[str] = set()
  for value in re.findall(r'\bclass="([^"]*)"', html):
    found.update(value.split())
  return found


def _static_emitted_classes() -> set[str]:
  """Class literals in `praxis/display/*.py`, plus the f-string families."""
  found: set[str] = set(_FAMILY_CLASSES)
  for path in sorted(_DISPLAY_DIR.glob("*.py")):
    for group in _LITERAL_CLASSES_RE.findall(path.read_text(encoding="utf-8")):
      found.update(group.split())
  return found


def test_coverage_check_fires_on_a_class_with_no_rule() -> None:
  """Negative control: a class no selector names is reported; positive control: one that a rule
  names (alone, in a list, after a descendant combinator, or with a state suffix) is not."""
  rules = _parse(".praxis-a { color: red } .x .praxis-b, .praxis-c:hover > .sv-d { color: red }")
  assert _uncovered({"praxis-a", "praxis-b", "praxis-c", "sv-d"}, rules) == []
  assert _uncovered({"praxis-a", "praxis-missing", "sv-missing"}, rules) == ["praxis-missing", "sv-missing"]
  # A class named only inside an attribute value is not a rule for that class.
  attr_only = _parse(".praxis-out [data-x='praxis-ghost'] { color: red }")
  assert _uncovered({"praxis-ghost"}, attr_only) == ["praxis-ghost"]
  # A prefix is not the class: `.praxis-name__title` does not cover `praxis-name`.
  assert _uncovered({"praxis-name"}, _parse(".praxis-name__title { color: red }")) == ["praxis-name"]


def test_coverage_check_fails_when_a_real_rule_is_removed() -> None:
  """Mutation control on the real file: dropping every rule that names one class uncovers exactly it."""
  rules = _rules()
  target = "praxis-ledger__bar"
  assert target in _selector_classes(rules), "the bar has no rule at all"
  mutated = [r for r in rules if not any(f".{target}" in s for s in r.selectors)]
  assert _uncovered({target}, mutated) == [target]
  assert _uncovered({target}, rules) == []


def test_static_extractor_finds_the_classes_the_modules_emit() -> None:
  """Positive control for the extractor: it sees known literals (a scan that finds nothing would pass
  the coverage test vacuously), and does not mistake a data attribute for a class."""
  found = _static_emitted_classes()
  for known in ("praxis-name", "praxis-name__title", "praxis-summary", "praxis-omitted", "praxis-fig",
                "praxis-res", "praxis-item", "praxis-ledger__bar", "praxis-ledger__row--child",
                "praxis-ledger__nest", "sv-changed", "sv-fault", "sv-fault-x", "sv-liquid", "sv-label--soft"):
    assert known in found, f"static scan missed {known}"
  assert not any(c.startswith("data-") for c in found)
  assert _LITERAL_CLASSES_RE.findall('a = "data-praxis-res"') == []
  assert _LITERAL_CLASSES_RE.findall('cls="praxis-x praxis-y"') == ["praxis-x praxis-y"]
  assert _LITERAL_CLASSES_RE.findall('cls=f"praxis-{kind}"') == []


def test_every_class_named_in_the_display_modules_has_a_rule() -> None:
  """STATIC (always runs, no PyLabRobot): each class literal in `praxis/display/*.py` is a selector."""
  missing = _uncovered(_static_emitted_classes(), _rules())
  assert not missing, f"emitted with no rule in praxis-theme.css: {missing}"


def _plr_pin_problem() -> str | None:
  try:
    import pylabrobot  # noqa: PLC0415 -- optional; the static check above does not need it
  except ImportError as exc:  # pragma: no cover - depends on the interpreter
    return f"pylabrobot is not importable ({exc})"
  version = str(getattr(pylabrobot, "__version__", ""))
  if not version.startswith("1.0.0b1"):
    return (
      f"PyLabRobot {version!r} at {pylabrobot.__file__} is not the 1.0.0b1 pin; "
      "run with PYTHONPATH=<PLR 1.0.0b1 source> prepended"
    )
  return None


def _display_package() -> None:
  """praxis/display loaded by path under a synthetic package (no `__init__`, `sys.path` untouched)."""
  if _PKG not in sys.modules:
    module = types.ModuleType(_PKG)
    module.__path__ = [str(_DISPLAY_DIR)]
    module.__package__ = _PKG
    sys.modules[_PKG] = module


def _render_real_outputs() -> dict[str, str]:
  """Real outputs from the design fixture (PLR 1.0.0b1): a plate with changed and fault wells, a tip
  rack, a bare well, the deck, a finished run ledger with an error row and children, a ledger caught
  mid-op (an `in-flight` row), a row-capped ledger, and the details helper; each at every ladder level."""
  _display_package()
  spec = importlib.util.spec_from_file_location("_praxis_css_make_fixture", _FIXTURE_PATH)
  fx = importlib.util.module_from_spec(spec)
  sys.modules["_praxis_css_make_fixture"] = fx
  spec.loader.exec_module(fx)
  labware = importlib.import_module(f"{_PKG}.labware")
  deck_mod = importlib.import_module(f"{_PKG}.deck")
  ledger = importlib.import_module(f"{_PKG}.ledger")
  budget = importlib.import_module(f"{_PKG}.budget")
  svg = importlib.import_module(f"{_PKG}.svg")

  async def build() -> dict[str, str]:
    deck, lh = await fx.assemble()
    source, assay, tips = deck.get_resource("source"), deck.get_resource("assay"), deck.get_resource("tips_300")
    out: dict[str, str] = {}

    # A run: the fixture's three column transfers, then an over-aspirate that raises (an error row).
    run = ledger.RunLedger(lh, show=False)
    with run:
      await fx.run_transfers(lh, deck)
      await lh.pick_up_tips(tips["A4:H4"])
      try:
        await lh.aspirate(assay["A1:H1"], vols=[80.0] * 8)
      except Exception:  # noqa: BLE001 -- the failing row is the point
        pass
    for level in budget.LEVELS:
      out[f"ledger@{level}"] = run.render_html(level)
    out["ledger-capped"] = run.render_html(budget.LEVEL_OMITTED, max_rows=2)

    # A ledger caught while an op is still running (an `in-flight` row).
    live = ledger.RunLedger(lh, show=False)
    original = lh.backend.aspirate

    async def spy(*args, **kwargs):
      out["ledger-in-flight"] = live.render_html()
      return await original(*args, **kwargs)

    lh.backend.aspirate = spy
    with live:
      await lh.aspirate(source["A1:H1"], vols=[10.0] * 8)
    lh.backend.aspirate = original

    for level in budget.LEVELS:
      out[f"plate@{level}"] = labware.render_html(assay, level=level, changed=["A1"], fault=["B1"])
      out[f"tiprack@{level}"] = labware.render_html(tips, level=level, changed=["A1"], fault=["B1"])
      out[f"deck@{level}"] = deck_mod.render_html(deck, level=level)
    out["well"] = labware.render_html(assay.get_item("A1"))
    out["details"] = svg.details_html("Show traceback", "x")
    return out

  return asyncio.run(build())


def test_every_class_the_real_outputs_emit_has_a_rule() -> None:
  """RENDERED: draw real B2/B3/B4 outputs with the design fixture and check every `praxis-*` /
  `sv-*` class in the HTML is a selector in the theme. Needs the PLR 1.0.0b1 pin."""
  problem = _plr_pin_problem()
  if problem:
    pytest.skip(f"{problem}. The static coverage check still ran.")
  rendered = _render_real_outputs()
  emitted: set[str] = set()
  for html in rendered.values():
    emitted |= _classes_in_html(html)

  # Positive control: the collector saw every family, so a broken render cannot pass by being empty.
  for known in ("praxis-out", "praxis-plate", "praxis-tiprack", "praxis-container", "praxis-deck",
                "praxis-ledger", "praxis-name__model", "praxis-omitted", "praxis-fig", "praxis-res",
                "praxis-item", "praxis-ledger__bar", "praxis-ledger__nest", "praxis-ledger__err",
                "praxis-ledger__status", "praxis-ledger__more", "praxis-ledger__after-label",
                "praxis-ledger__row--in-flight", "praxis-ledger__row--error", "praxis-ledger__row--ok",
                "praxis-ledger__row--child", "praxis-ledger__row--cycle", "sv-changed", "sv-fault",
                "sv-fault-x", "sv-label--soft", "sv-rail--major", "praxis-details-body"):
    assert known in emitted, f"the rendered collector never saw {known}; classes seen: {sorted(emitted)}"

  missing = _uncovered(emitted, _rules())
  assert not missing, f"rendered with no rule in praxis-theme.css: {missing}"
  # Every class the static scan knows is also either rendered here or a documented f-string family.
  # (The static set is what a later output may emit; the rendered set is what does today.)
  assert _uncovered(emitted | _static_emitted_classes(), _rules()) == []


def test_rendered_coverage_fails_against_a_stylesheet_without_the_bar_rules() -> None:
  """Negative control at the level of the real render: the same rendered classes, checked against the
  real rules minus the ledger bar's, are reported uncovered."""
  problem = _plr_pin_problem()
  if problem:
    pytest.skip(problem)
  emitted: set[str] = set()
  for html in _render_real_outputs().values():
    emitted |= _classes_in_html(html)
  stripped = [r for r in _rules() if not any("praxis-ledger__bar" in s for s in r.selectors)]
  assert _uncovered(emitted, stripped) == ["praxis-ledger__bar"]


# --- the emitted vocabulary, property by property ---------------------------------------------

_INK_VAR = "var(--jp-content-font-color0)"
_SOFT_VAR = "var(--jp-content-font-color2)"
_RAIL_VAR = "var(--jp-border-color1)"


def test_name_line_is_a_baseline_row_that_wraps() -> None:
  line = _has(".praxis-name")
  assert line.decls.get("display") == "flex"
  assert line.decls.get("align-items") == "baseline"
  assert line.decls.get("flex-wrap") == "wrap"
  assert line.decls.get("gap") == "12px"


def test_resource_name_is_condensed_semibold_in_the_ui_face_not_the_code_face() -> None:
  """DESIGN "Type": resource names are Roboto Flex on the width axis (`font-stretch`), weight 600,
  18 px. JetBrains Mono is code only, so no name-line rule may set the code face."""
  title = _has(".praxis-name__title")
  assert title.decls.get("font-weight") == "600"
  assert title.decls.get("font-size") == "18px"
  stretch = title.decls.get("font-stretch", "")
  assert stretch.endswith("%") and float(stretch[:-1]) <= 50, f"resource name is not condensed: {stretch!r}"
  for sel in (".praxis-name", ".praxis-name__title", ".praxis-name__type", ".praxis-name__model", ".praxis-summary"):
    assert "code" not in _has(sel).decls.get("font-family", ""), sel
    assert "mono" not in _has(sel).decls.get("font-family", "").lower(), sel


def test_type_and_model_are_ink_soft_and_the_model_is_condensed_but_less() -> None:
  for sel in (".praxis-name__type", ".praxis-name__model"):
    rule = _has(sel)
    assert rule.decls.get("color") == _SOFT_VAR, sel
    assert rule.decls.get("font-size") == "14px", sel
  model = float(_has(".praxis-name__model").decls["font-stretch"].rstrip("%"))
  title = float(_has(".praxis-name__title").decls["font-stretch"].rstrip("%"))
  assert title < model < 100, (title, model)


def test_summary_sentence_is_body_ink_at_prose_measure() -> None:
  summary = _has(".praxis-summary")
  assert summary.decls.get("max-width") == "72ch"
  assert summary.decls.get("font-size") == "14px"
  assert summary.decls.get("color") == _INK_VAR
  assert summary.decls.get("margin", "").startswith("8px 0 0")


def test_omitted_notice_is_quiet_ink_soft_never_rose_or_brick() -> None:
  omitted = _has(".praxis-omitted")
  assert omitted.decls.get("color") == _SOFT_VAR
  assert "rose" not in str(omitted.decls) and "brick" not in str(omitted.decls)


def test_figure_wrapper_scrolls_horizontally_instead_of_shrinking() -> None:
  """D5: below `s_min` the figure scrolls; the wrapper also carries this inline, which an untrusted
  reopen loses, so the class must say it too."""
  fig = _has(".praxis-fig")
  assert fig.decls.get("overflow-x") == "auto"
  assert fig.decls.get("max-width") == "100%"
  assert _has(".praxis-fig svg").decls.get("display") == "block"


@pytest.mark.parametrize(
  "selector", [".praxis-plate", ".praxis-tiprack", ".praxis-container", ".praxis-deck", ".praxis-ledger"]
)
def test_output_roots_are_capped_at_the_design_content_width(selector: str) -> None:
  """DESIGN "Layout": content max 880 px (also D5's design width)."""
  assert _effective(selector, "max-width") == "880px", selector


def test_resource_groups_are_clickable() -> None:
  for selector in (".praxis-out .praxis-res", ".praxis-out .praxis-item"):
    assert _has(selector).decls.get("cursor") == "pointer", selector


def test_deck_item_hover_and_focus_are_colour_only_and_rose() -> None:
  """Hover outlines a deck item in rose ink, focus in rose (the prototype's `[data-res]:hover` and
  `.is-focus`). Colour only: the drawing's stroke widths are in user units (mm) and set by the
  emitter, so a px width here would be wrong by the drawing scale. A labware figure is the resource
  itself, so focus is not repeated on it."""
  hover = [r for r in _rules() if any(".praxis-item:hover" in s for s in r.selectors)]
  focus = [r for r in _rules() if any(".praxis-item.is-focus" in s or ".is-focus > .sv-plate" in s for s in r.selectors)]
  assert hover and focus
  assert hover[-1].decls.get("stroke") == "var(--praxis-rose-ink)"
  assert focus[-1].decls.get("stroke") == "var(--praxis-rose)"
  for rule in hover + focus:
    assert "stroke-width" not in rule.decls, rule
    for sel in rule.selectors:
      assert ".praxis-deck" in sel, f"deck items only: {sel}"


# -- the ledger table ---------------------------------------------------------------------------


def test_ledger_table_is_a_collapsed_full_width_grid() -> None:
  table = _has(".praxis-ledger__table")
  assert table.decls.get("border-collapse") == "collapse"
  assert table.decls.get("width") == "100%"
  assert table.decls.get("max-width") == "720px"
  assert table.decls.get("font-size") == "14px"


def test_ledger_header_is_ink_soft_over_a_hairline() -> None:
  th = _has(".praxis-ledger__th")
  assert th.decls.get("color") == _SOFT_VAR
  assert th.decls.get("border-bottom") == f"1px solid {_RAIL_VAR}"
  assert th.decls.get("font-weight") == "500"
  assert _has(".praxis-ledger__th:last-child").decls.get("text-align") == "right"


def test_a_new_tip_cycle_gets_a_hairline_above_it_except_the_first_row() -> None:
  cycle = _has(".praxis-ledger__row--cycle > td")
  assert cycle.decls.get("border-top") == f"1px solid {_RAIL_VAR}"
  first = _has(".praxis-ledger__row--cycle:first-child > td")
  assert first.decls.get("border-top") == "0"


def test_child_rows_are_indented_by_the_cell_not_only_by_the_arrow_glyph() -> None:
  """B4 emits a literal arrow (`praxis-ledger__nest`) so the text reads with no CSS. With CSS the
  act cell of a child row also gets a real indent, and the glyph goes quiet (ink soft)."""
  indent = _has(".praxis-ledger__row--child > .praxis-ledger__act").decls.get("padding-left", "")
  assert indent.endswith("px") and float(indent[:-2]) >= 12, f"child rows have no indent: {indent!r}"
  base = _has(".praxis-ledger__act").decls.get("padding-left", "0px")
  assert float(indent[:-2]) > float(base.rstrip("px") or 0)
  assert _has(".praxis-ledger__nest").decls.get("color") == _SOFT_VAR


def test_ledger_columns_are_aligned_and_tabular() -> None:
  assert _has(".praxis-ledger__step").decls.get("text-align") == "right"
  assert _has(".praxis-ledger__step").decls.get("color") == _SOFT_VAR
  assert _has(".praxis-ledger__ch").decls.get("text-align") == "right"
  assert _has(".praxis-ledger__ch").decls.get("color") == _SOFT_VAR
  assert _has(".praxis-ledger__vol").decls.get("white-space") == "nowrap"
  assert _has(".praxis-ledger__where").decls.get("font-stretch") == "80%"


def _bar_fill(row_class: str | None) -> str | None:
  """The fill the bar's `rect` gets: bare, or inside a row of the given status."""
  selector = ".praxis-ledger__bar rect" if row_class is None else f".praxis-ledger__row--{row_class} .praxis-ledger__bar rect"
  return _effective(selector, "fill")


def test_ledger_bar_is_blue_for_volume_rose_for_attention_brick_for_error() -> None:
  """Blue means volume only: the bar (a volume) is moonstone when the op is done. The op that is
  still running is rose (look here), and the op that failed is brick; brick also has the row's
  `error: ...` text, so an error is never colour alone."""
  assert _bar_fill(None) == "var(--praxis-moonstone)"
  assert _bar_fill("ok") == "var(--praxis-moonstone)"
  assert _bar_fill("in-flight") == "var(--praxis-rose)"
  assert _bar_fill("error") == "var(--praxis-brick)"


def test_ledger_bar_sits_inline_next_to_its_number() -> None:
  bar = _has(".praxis-ledger__bar")
  assert bar.decls.get("display") == "inline-block"
  assert bar.decls.get("vertical-align") == "middle"
  assert bar.decls.get("margin-right") == "8px"


def test_ledger_status_marks_are_rose_and_brick_rules_on_the_first_cell() -> None:
  assert "var(--praxis-rose)" in _has(".praxis-ledger__row--in-flight > td:first-child").decls.get("box-shadow", "")
  assert "var(--praxis-brick)" in _has(".praxis-ledger__row--error > td:first-child").decls.get("box-shadow", "")
  assert _has(".praxis-ledger__err").decls.get("color") == "var(--jp-error-color1)"
  assert _has(".praxis-ledger__status").decls.get("color") == _SOFT_VAR


def test_ledger_after_state_and_row_cap_notice_are_quiet_text() -> None:
  assert _has(".praxis-ledger__after-label").decls.get("color") == _SOFT_VAR
  assert _has(".praxis-ledger__more").decls.get("color") == _SOFT_VAR
  assert _has(".praxis-ledger__after").decls.get("margin-top") == "18px"


# -- the SVG vocabulary (keyed on class where it survives; colours already mapped by attribute) --


@pytest.mark.parametrize(
  ("selector", "prop", "token"),
  [
    (".praxis-out .sv-changed", "stroke", "var(--praxis-rose)"),
    (".praxis-out .sv-fault", "stroke", "var(--praxis-brick)"),
    (".praxis-out .sv-fault-x", "stroke", "var(--praxis-brick)"),
    (".praxis-out .sv-liquid", "fill", "var(--praxis-moonstone)"),
    (".praxis-out .sv-plate", "stroke", _INK_VAR),
    (".praxis-out .sv-plate", "fill", "var(--jp-layout-color0)"),
    (".praxis-out .sv-well", "stroke", _RAIL_VAR),
    (".praxis-out .sv-tip", "stroke", _INK_VAR),
    (".praxis-out .sv-tip-ring", "stroke", _INK_VAR),
    (".praxis-out .sv-tip-gone", "stroke", _RAIL_VAR),
    (".praxis-out .sv-carrier", "stroke", _RAIL_VAR),
    (".praxis-out .sv-fixture", "stroke", _RAIL_VAR),
    (".praxis-out .sv-block", "fill", _RAIL_VAR),
    (".praxis-out .sv-rail", "stroke", _RAIL_VAR),
    (".praxis-out .sv-rail--major", "stroke", _SOFT_VAR),
    (".praxis-out .sv-ruler", "stroke", _SOFT_VAR),
    (".praxis-out .sv-grid", "fill", _SOFT_VAR),
    (".praxis-out .sv-label", "fill", _INK_VAR),
    (".praxis-out .sv-label--soft", "fill", _SOFT_VAR),
  ],
)
def test_sv_classes_map_to_tokens(selector: str, prop: str, token: str) -> None:
  assert _effective(selector, prop) == token, f"`{selector}` should set {prop}: {token}"


@pytest.mark.parametrize("selector", [".praxis-out .sv-changed", ".praxis-out .sv-fault", ".praxis-out .sv-fault-x"])
def test_marks_are_outlines_not_fills(selector: str) -> None:
  assert _effective(selector, "fill") == "none"


def test_svg_text_faces_follow_the_design() -> None:
  """Grid numbers 500 condensed 80%; carrier and labware names 600 at the name line's condensed width."""
  grid = _has(".praxis-out .sv-grid")
  assert grid.decls.get("font-weight") == "500" and grid.decls.get("font-stretch") == "80%"
  label = _has(".praxis-out .sv-label")
  assert label.decls.get("font-weight") == "600"
  assert label.decls.get("font-stretch") == _has(".praxis-name__title").decls.get("font-stretch")
  for sel in (".praxis-out .sv-grid", ".praxis-out .sv-label"):
    assert _has(sel).decls.get("font-family") == "var(--jp-ui-font-family)", sel


def test_svg_class_rules_set_no_stroke_width_or_dash() -> None:
  """Stroke widths and dashes are emitted in user units (mm) at the figure's scale; a px value in
  the stylesheet would be off by the drawing scale. Only colour, fill and face come from CSS."""
  for rule in _rules():
    if any(".sv-" in s for s in rule.selectors):
      for prop in ("stroke-width", "stroke-dasharray", "vector-effect", "font-size"):
        assert prop not in rule.decls, f"{rule.selector_text} sets {prop}"


# -- the details helper's default classes ---------------------------------------------------------


def test_details_helper_defaults_are_a_quiet_folded_block() -> None:
  assert _has(".praxis-details-summary").decls.get("cursor") == "pointer"
  assert _has(".praxis-details-summary").decls.get("color") == "var(--jp-content-link-color)"
  body = _has(".praxis-details-body")
  assert body.decls.get("font-family") == "var(--praxis-code-font)"
  assert body.decls.get("overflow-x") == "auto"


# -- discipline for every new rule ----------------------------------------------------------------


def _emitted_vocabulary_rules() -> list[_Rule]:
  return [r for r in _rules() if any(re.search(r"\.(?:praxis|sv)-", s) for s in r.selectors)]


def test_new_rules_name_no_theme_and_are_keyed_on_a_class() -> None:
  """D3: outputs follow every theme without the stylesheet naming one; S2: class-keyed."""
  for rule in _emitted_vocabulary_rules():
    for sel in rule.selectors:
      assert "data-jp-theme" not in sel, sel
      assert not sel.startswith("body"), sel


def test_no_rule_for_the_vocabulary_removes_a_focus_outline() -> None:
  """Visible focus rings are preserved: nothing on a `.praxis-*` / `.sv-*` rule turns an outline off."""
  for rule in _emitted_vocabulary_rules():
    assert rule.decls.get("outline") not in {"none", "0", "0px"}, rule
    assert rule.decls.get("outline-style") != "none", rule
    assert rule.decls.get("outline-width") not in {"0", "0px"}, rule
  bad = _parse(".praxis-x:focus { outline: none }")
  assert [r for r in bad if r.decls.get("outline") in {"none", "0", "0px"}], "control: the check can fire"


def test_new_rules_do_not_touch_the_chrome_hooks_a7_measures() -> None:
  """D1 / D1-dark read the notebook ground, the code-cell sheet, the rail `::before`, the count
  `::after` and the prompt widths (A4's rules). No `.praxis-*` / `.sv-*` rule may select them."""
  chrome = ("jp-Notebook", "jp-CodeCell", "jp-InputPrompt", "jp-OutputPrompt", "jp-OutputArea-prompt", "::before", "::after")
  for rule in _emitted_vocabulary_rules():
    for sel in rule.selectors:
      if sel.startswith((".praxis-focus-ring", ".praxis-deck-panel", ".praxis-stale", ".praxis-error", ".praxis-readout")):
        continue  # A4's own
      for hook in chrome:
        assert hook not in sel, f"`{sel}` touches {hook}"


def test_vocabulary_declares_no_transition_or_animation() -> None:
  """Restates NFR-6 against the vocabulary's own rules (the whole-file check is above)."""
  css = "\n".join(f"{r.selector_text} {{ {'; '.join(f'{k}: {v}' for k, v in r.decls.items())} }}" for r in _emitted_vocabulary_rules())
  assert _animation_violations(css) == []


@pytest.mark.xfail(
  strict=True,
  reason=(
    "The vendored Roboto Flex has no width axis: VENDOR_MANIFEST.json's source_css asks Google Fonts for "
    "`opsz,wght` only (fvar axes measured: opsz 8-144, wght 100-1000), and the @font-face declares "
    "`font-stretch: 100%`. `font-stretch: 25%` on resource names is therefore a no-op until the font is "
    "re-vendored with `wdth` (scripts/vendor_fonts.py). Remove this marker when it is."
  ),
)
def test_vendored_roboto_flex_has_the_width_axis_the_names_ask_for() -> None:
  manifest = (_THEME_DIR / "fonts" / "VENDOR_MANIFEST.json").read_text(encoding="utf-8")
  entry = next(e for e in __import__("json").loads(manifest)["entries"] if e["file"] == "RobotoFlex-Variable.woff2")
  assert "wdth" in entry["source_css"], entry["source_css"]
