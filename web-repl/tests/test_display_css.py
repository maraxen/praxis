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
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_WEB_REPL_ROOT = Path(__file__).resolve().parents[1]
_THEME_DIR = _WEB_REPL_ROOT / "overlay" / "assets" / "theme"
_CSS = _THEME_DIR / "praxis-theme.css"
_DIST_THEMES = _WEB_REPL_ROOT / "dist" / "build" / "themes" / "@jupyterlab"

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


# --- the Light sheet must win the cascade in command mode (D1, AC-7) -----------------
#
# JupyterLab's own stylesheet makes the active, selected code cell TRANSPARENT in
# command mode, at specificity (0,6,0). The Light sheet rule above has to out-rank
# it or the cell shows the steel ground, not the white sheet (first real-browser D1
# run on CI: `light_sheet` measured rgba(0, 0, 0, 0)). This is a text check, so it
# carries a small specificity calculator and selector matcher, and both are
# exercised on synthetic input below (positive and negative controls).

_IDENT = re.compile(r"-?[_a-zA-Z][-\w]*")
_LEGACY_PSEUDO_ELEMENTS = {":before", ":after", ":first-line", ":first-letter"}


def _compound_list(selector: str) -> list[str]:
  """Compounds of a selector that uses descendant combinators only (raises on `>`, `+`, `~`)."""
  if re.search(r"[>+~]", re.sub(r"\[[^\]]*\]|\([^)]*\)", "", selector)):
    raise ValueError(f"only descendant combinators are supported: {selector!r}")
  return [c for c in _split_top_level(selector, " ") if c]


def _simple_selectors(compound: str) -> list[tuple]:
  out, i = [], 0
  while i < len(compound):
    ch = compound[i]
    if ch == "[":
      j = compound.index("]", i)
      out.append(("attr", compound[i + 1 : j]))
      i = j + 1
    elif ch == ":":
      m = re.compile(r"::?" + _IDENT.pattern).match(compound, i)
      if not m:
        raise ValueError(f"bad pseudo in {compound!r}")
      name, i, arg = m.group(0), m.end(), None
      if i < len(compound) and compound[i] == "(":
        depth, j = 0, i
        while True:
          depth += {"(": 1, ")": -1}.get(compound[j], 0)
          if depth == 0:
            break
          j += 1
        arg, i = compound[i + 1 : j], j + 1
      out.append(("pseudo", name, arg))
    elif ch in ".#":
      m = _IDENT.match(compound, i + 1)
      if not m:
        raise ValueError(f"bad selector in {compound!r}")
      out.append(("class" if ch == "." else "id", m.group(0)))
      i = m.end()
    elif ch == "*":
      out.append(("universal",))
      i += 1
    else:
      m = _IDENT.match(compound, i)
      if not m:
        raise ValueError(f"bad selector in {compound!r}")
      out.append(("type", m.group(0)))
      i = m.end()
  return out


def _specificity(selector: str) -> tuple[int, int, int]:
  """(ids, classes+attributes+pseudo-classes, types+pseudo-elements).

  `:not(X)` and `:is(X)` count as their most specific argument, `:where()` as zero.
  """
  a = b = c = 0
  for compound in _compound_list(selector):
    for s in _simple_selectors(compound):
      if s[0] == "id":
        a += 1
      elif s[0] in ("class", "attr"):
        b += 1
      elif s[0] == "type":
        c += 1
      elif s[0] == "pseudo":
        _, name, arg = s
        if name.startswith("::") or name in _LEGACY_PSEUDO_ELEMENTS:
          c += 1
        elif name in (":not", ":is", ":matches", ":any"):
          best = max((_specificity(x) for x in _split_top_level(arg or "", ",")), default=(0, 0, 0))
          a, b, c = a + best[0], b + best[1], c + best[2]
        elif name != ":where":
          b += 1
  return (a, b, c)


def _el(tag: str, classes: str = "", **attrs: str) -> dict:
  return {"tag": tag, "classes": set(classes.split()), "attrs": {k.replace("_", "-"): v for k, v in attrs.items()}}


def _compound_matches(compound: str, el: dict) -> bool:
  """Whether one compound matches one element. Pseudo-elements never match an element, and a
  pseudo-class that needs runtime state (`:hover`, `:focus-visible`) is treated as not matching."""
  for s in _simple_selectors(compound):
    kind = s[0]
    if kind == "type" and s[1] != el["tag"]:
      return False
    if kind == "class" and s[1] not in el["classes"]:
      return False
    if kind == "id" and el["attrs"].get("id") != s[1]:
      return False
    if kind == "attr":
      name, _, value = s[1].partition("=")
      if name.strip() not in el["attrs"] or (value and el["attrs"][name.strip()] != value.strip("'\" ")):
        return False
    if kind == "pseudo":
      _, name, arg = s
      parts = _split_top_level(arg or "", ",")
      if name == ":not":
        if any(_compound_matches(p, el) for p in parts):
          return False
      elif name in (":is", ":matches", ":any"):
        if not any(_compound_matches(p, el) for p in parts):
          return False
      elif name != ":where":
        return False
  return True


def _matches(selector: str, chain: list[dict]) -> bool:
  """`chain` runs outermost to subject; descendant combinators, with backtracking."""
  compounds = _compound_list(selector)

  def fit(ci: int, ei: int) -> bool:  # compounds[ci] must match chain[ei] or an ancestor of it
    if ci < 0:
      return True
    for k in range(ei, -1, -1):
      if _compound_matches(compounds[ci], chain[k]) and fit(ci - 1, k - 1):
        return True
      if ci == len(compounds) - 1:  # the subject compound is pinned to the last element
        return False
    return False

  return fit(len(compounds) - 1, len(chain) - 1)


_CMD = "jp-Notebook jp-mod-commandMode"
_CELL = "jp-Cell jp-CodeCell jp-Notebook-cell jp-mod-active jp-mod-selected"


def _cell_chain(theme: str = "JupyterLab Light", notebook: str = _CMD, cell: str = _CELL) -> list[dict]:
  return [
    _el("body", data_jp_theme_name=theme),
    _el("div", notebook),
    _el("div", "jp-WindowedPanel-outer"),
    _el("div", cell),
  ]


# JupyterLab core CSS (web-repl/dist/build/jlab_core.*.js, 260828 dist), verbatim selectors
# that give a cell a background, with the values they set.
_JL_COMMAND_SELECTED = ".jp-Notebook.jp-mod-commandMode .jp-Cell.jp-mod-active.jp-mod-selected:not(.jp-mod-multiSelected)"
_JL_COMMAND_MULTI = ".jp-Notebook.jp-mod-commandMode .jp-Cell.jp-mod-selected"
_JL_CELL_BACKGROUNDS = [
  (".jp-Cell", "transparent"),
  (_JL_COMMAND_MULTI, "var(--jp-notebook-multiselected-color)"),
  (_JL_COMMAND_SELECTED, "transparent"),
]
_SHEET_VALUE = "var(--jp-layout-color0)"


def _cell_background(rules: list[_Rule], chain: list[dict]) -> tuple[tuple, str] | None:
  """Highest-specificity `background` among `rules` matching the cell (later wins a tie)."""
  best = None
  for rule in rules:
    if "background" not in rule.decls:
      continue
    for sel in rule.selectors:
      if _matches(sel, chain):
        cand = (_specificity(sel), rule.decls["background"])
        best = cand if best is None or cand[0] >= best[0] else best
  return best


def _jl_cell_background(chain: list[dict]) -> tuple[tuple, str] | None:
  return _cell_background([_Rule(sel, f"background: {val}") for sel, val in _JL_CELL_BACKGROUNDS], chain)


def _sheet_wins(rules: list[_Rule], chain: list[dict]) -> bool:
  """The sheet is painted on the cell. Strictly greater than JupyterLab's rule: whether
  the overlay loads before or after the core CSS is not visible to a text check, so a tie
  is not trusted."""
  ours, theirs = _cell_background(rules, chain), _jl_cell_background(chain)
  return ours is not None and ours[1] == _SHEET_VALUE and (theirs is None or ours[0] > theirs[0])


_OLD_SHEET_RULE = f"""
{_LIGHT} .jp-Notebook .jp-CodeCell,
{_LIGHT} .jp-Notebook .jp-CodeCell.jp-mod-active.jp-mod-selected {{ background: {_SHEET_VALUE}; }}
"""
_FIXED_SHEET_RULE = f"""
{_LIGHT} .jp-Notebook .jp-CodeCell,
{_LIGHT} .jp-Notebook.jp-mod-commandMode .jp-CodeCell.jp-mod-active.jp-mod-selected:not(.jp-mod-multiSelected)
  {{ background: {_SHEET_VALUE}; }}
"""
# Exactly JupyterLab's specificity (0,6,0): no theme-name element, six class-level parts.
_TIED_SELECTOR = "[data-jp-theme-name='JupyterLab Light'] .jp-Notebook.jp-mod-commandMode .jp-CodeCell.jp-mod-active:not(.jp-mod-multiSelected)"
_TIED_SHEET_RULE = f"{_TIED_SELECTOR} {{ background: {_SHEET_VALUE}; }}"
_WRONG_THEME_RULE = f"""
body[data-jp-theme-name='JupyterLab Dark'] .jp-Notebook.jp-mod-commandMode .jp-CodeCell.jp-mod-active.jp-mod-selected:not(.jp-mod-multiSelected)
  {{ background: {_SHEET_VALUE}; }}
"""


@pytest.mark.parametrize(
  ("selector", "expected"),
  [
    ("a", (0, 0, 1)),
    (".a.b", (0, 2, 0)),
    ("#i .c", (1, 1, 0)),
    (":not(.a)", (0, 1, 0)),
    (":is(.a, #b .c)", (1, 1, 0)),
    (":where(.a)", (0, 0, 0)),
    ("[x='y z']", (0, 1, 0)),
    ("a::before", (0, 0, 2)),
    ("a:hover", (0, 1, 1)),
    (_JL_COMMAND_SELECTED, (0, 6, 0)),
    (_JL_COMMAND_MULTI, (0, 4, 0)),
    (f"{_LIGHT} .jp-Notebook .jp-CodeCell.jp-mod-active.jp-mod-selected", (0, 5, 1)),
    (f"{_LIGHT} .jp-Notebook.jp-mod-commandMode .jp-CodeCell.jp-mod-active.jp-mod-selected:not(.jp-mod-multiSelected)", (0, 7, 1)),
    ("body:is([data-jp-theme-name='JupyterLab Dark'], [data-jp-theme-name='JupyterLab Light']) .jp-Notebook .jp-CodeCell", (0, 3, 1)),
  ],
)
def test_specificity_calculator_controls(selector: str, expected: tuple[int, int, int]) -> None:
  """Known values from the CSS spec (and a mismatch would show the calculator is not constant)."""
  assert _specificity(selector) == expected


def test_selector_matcher_controls() -> None:
  """Positive: JupyterLab's command-mode rule matches the active, selected cell. Negative: it
  does not match in edit mode, for a multi-selected cell, or an unrelated element."""
  assert _matches(_JL_COMMAND_SELECTED, _cell_chain())
  assert not _matches(_JL_COMMAND_SELECTED, _cell_chain(notebook="jp-Notebook jp-mod-editMode"))
  assert not _matches(_JL_COMMAND_SELECTED, _cell_chain(cell=_CELL + " jp-mod-multiSelected"))
  assert _matches(_JL_COMMAND_MULTI, _cell_chain(cell=_CELL + " jp-mod-multiSelected"))
  assert not _matches(_JL_COMMAND_SELECTED, _cell_chain()[:2])
  assert _matches(f"{_LIGHT} .jp-CodeCell", _cell_chain())
  assert not _matches(f"{_LIGHT} .jp-CodeCell", _cell_chain(theme="JupyterLab Dark"))
  assert not _matches(".jp-CodeCell::before", _cell_chain()), "a pseudo-element is not the cell"
  assert not _matches(".jp-CodeCell:hover", _cell_chain()), "state-dependent pseudo-classes do not match"


def test_sheet_check_passes_on_the_fixed_rule_and_fails_on_every_negative_control() -> None:
  chain = _cell_chain()
  assert _sheet_wins(_parse(_FIXED_SHEET_RULE), chain), "positive control: the fixed selector must win"
  for name, css in {
    "current selector (0,5,1) < (0,6,0)": _OLD_SHEET_RULE,
    "tie at (0,6,0)": _TIED_SHEET_RULE,
    "wrong theme attribute": _WRONG_THEME_RULE,
  }.items():
    assert not _sheet_wins(_parse(css), chain), f"negative control passed: {name}"
  assert _specificity(_TIED_SELECTOR) == (0, 6, 0)


def test_light_sheet_beats_jupyterlabs_transparent_active_cell_in_command_mode() -> None:
  """The active, selected cell, in command mode, reads the white sheet (D1 `light_sheet`)."""
  chain = _cell_chain()
  ours, theirs = _cell_background(_rules(), chain), _jl_cell_background(chain)
  assert theirs == ((0, 6, 0), "transparent"), theirs  # the rule this has to beat
  assert ours is not None and ours[1] == _SHEET_VALUE, ours
  assert ours[0] > theirs[0], f"sheet selector {ours[0]} does not beat JupyterLab's {theirs[0]}"


@pytest.mark.parametrize(
  "chain",
  [
    _cell_chain(notebook="jp-Notebook jp-mod-editMode"),
    _cell_chain(cell="jp-Cell jp-CodeCell jp-Notebook-cell"),
    _cell_chain(cell="jp-Cell jp-CodeCell jp-Notebook-cell jp-mod-active"),
  ],
  ids=["edit-mode-active", "idle-cell", "active-not-selected"],
)
def test_light_sheet_shows_in_the_other_cell_states(chain: list[dict]) -> None:
  assert _sheet_wins(_rules(), chain)


def test_light_sheet_leaves_multi_select_to_jupyterlab() -> None:
  """A multi-selected cell keeps JupyterLab's highlight: no sheet selector out-ranks its (0,4,0) rule."""
  chain = _cell_chain(cell=_CELL + " jp-mod-multiSelected")
  theirs = _jl_cell_background(chain)
  assert theirs == ((0, 4, 0), "var(--jp-notebook-multiselected-color)"), theirs
  ours = _cell_background(_rules(), chain)
  assert ours is None or ours[0] < theirs[0], f"sheet {ours} hides the multi-select highlight"
  # Negative control: the old second selector matched this state at (0,5,1) and did hide it.
  old = _cell_background(_parse(_OLD_SHEET_RULE), chain)
  assert old is not None and old[0] > theirs[0]


def test_dark_theme_has_no_cell_background() -> None:
  """Dark deliberately keeps JupyterLab's transparent sheet: no cell background rule reaches it."""
  assert _cell_background(_rules(), _cell_chain(theme="JupyterLab Dark")) is None


def test_no_important_anywhere_in_the_file() -> None:
  """Repo style: the cascade is won by specificity, never `!important`. Control: it fires."""
  assert "!important" not in _strip_comments(_CSS.read_text(encoding="utf-8"))
  assert "!important" in _strip_comments("a { background: red !important }")


def test_jupyterlab_rules_quoted_here_are_in_the_bundled_core_css() -> None:
  """Re-confirms the quoted JupyterLab selectors against the built dist (skipped when absent)."""
  bundles = sorted((_WEB_REPL_ROOT / "dist" / "build").glob("jlab_core.*.js"))
  if not bundles:
    pytest.skip("web-repl/dist/build/jlab_core.*.js absent: build with build_repl.py to confirm")
  text = " ".join(bundles[0].read_text(encoding="utf-8").replace("\\n", " ").split())
  for selector, _ in _JL_CELL_BACKGROUNDS[1:]:
    assert selector in text, selector


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


def test_blue_means_volume_only() -> None:
  """No `.praxis-*` output/panel rule uses moonstone (liquid) or moonstone ink. The rail's
  `ran` and `stale` marks (section 3.1) are the only chrome that does, and they are not `.praxis-*`."""
  for rule in _rules():
    if ".praxis-" not in rule.selector_text:
      continue
    for prop, value in rule.decls.items():
      assert "moonstone" not in value, f"{rule.selector_text}: {prop}: {value}"
      assert _MOONSTONE.lower() not in value.lower() and _MOON_INK.lower() not in value.lower()
