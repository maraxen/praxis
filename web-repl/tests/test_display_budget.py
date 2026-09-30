"""Browserless tests for ``praxis/display/budget.py`` (task B1, backlog #5632): the D4 byte
cap, its degradation ladder, and ``cap_tail``. Closes the pure half of AC-13; B3 adds the
fixture-deck and 20x1536-well-plate cases against real labware, B6 the 200-frame error panel.

Spec: ``260929_notebook-display-epic.md`` D4. At most 65,536 bytes of UTF-8 ``text/html`` per
output. Ladder, in order (the drawing degrades first, text is never dropped to save a drawing):
level 1 draws every labware as a filled block and drops ``data-praxis-grid`` for blocked
labware; level 2 omits the drawing and shows name line + sentence +
"Drawing omitted: it would exceed 64 KiB.". A traceback is capped at 16 KiB, the TAIL kept,
the head replaced by one line "... N earlier lines omitted" (the ellipsis is U+2026).

The renderer here is a FAKE built from ``svg.py`` primitives (the ladder is the unit under
test, not labware). The modules are loaded by path under synthetic names;
``web-repl/overlay/assets/python`` is never put on ``sys.path`` (ADR 260817 Sec 2.4).

Controls: ``cap_tail`` is judged by an independent verifier, which is itself run against a
naive head-truncation and a wrong-N variant and must reject both; ``enforce`` is judged against
call logs, which a size-blind implementation cannot satisfy.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import random
import re
import sys
from pathlib import Path

import pytest

_DISPLAY_DIR = (
    Path(__file__).resolve().parents[1]
    / "overlay" / "assets" / "python" / "praxis" / "display"
)
_BUDGET_PATH = _DISPLAY_DIR / "budget.py"
_SVG_PATH = _DISPLAY_DIR / "svg.py"

CAP = 65_536
TB_CAP = 16_384
ELLIPSIS = "…"


def _load(path: Path, name: str):
    if name in sys.modules:
        return sys.modules[name]
    if not path.is_file():
        pytest.fail(f"{path.relative_to(path.parents[5])} does not exist yet")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def budget():
    return _load(_BUDGET_PATH, "_praxis_display_budget_under_test")


@pytest.fixture(scope="module")
def svg():
    return _load(_SVG_PATH, "_praxis_display_svg_under_test_b")


def _imports_of(source: str) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.add((node.module or "").split(".")[0] if node.level == 0 else "<relative>")
    return names


def _size(s: str) -> int:
    return len(s.encode("utf-8"))


def test_module_imports_only_the_standard_library(budget):
    imports = _imports_of(_BUDGET_PATH.read_text())
    assert imports <= set(sys.stdlib_module_names) | {"__future__"}, imports
    assert not (imports & {"js", "pyodide", "IPython", "pylabrobot", "praxis", "<relative>"})


# --------------------------------------------------------------------------- constants and sizing


def test_constants_are_the_d4_numbers(budget):
    assert budget.MAX_HTML_BYTES == CAP == 64 * 1024
    assert budget.TRACEBACK_CAP_BYTES == TB_CAP == 16 * 1024
    assert (budget.LEVEL_FULL, budget.LEVEL_BLOCKS, budget.LEVEL_OMITTED) == (0, 1, 2)
    assert tuple(budget.LEVELS) == (0, 1, 2)
    assert budget.OMISSION_SENTENCE == "Drawing omitted: it would exceed 64 KiB."
    assert budget.TAIL_MARKER_FORMAT.format(n=7) == f"{ELLIPSIS} 7 earlier lines omitted"


@pytest.mark.parametrize("s, n", [("", 0), ("a", 1), ("µ", 2), ("€", 3), ("\U0001f9ea", 4),
                                  ("µL wells", 9), ("a\nb", 3)])
def test_html_bytes_counts_utf8_bytes_not_characters(budget, s, n):
    assert budget.html_bytes(s) == n == _size(s)


def test_html_bytes_survives_a_lone_surrogate_and_overcounts(budget):
    s = "ok\ud800"
    assert budget.html_bytes(s) >= 3   # never raises; 3 bytes for the surrogate, never fewer


# --------------------------------------------------------------------------- enforce: the ladder


def _fake(sizes: dict[int, int]):
    """A renderer whose output at each level is exactly sizes[level] bytes; logs its calls."""
    calls: list[int] = []

    def render(level: int) -> str:
        calls.append(level)
        return f"<p>{level}</p>" + "x" * (sizes[level] - len(f"<p>{level}</p>"))

    return render, calls


def test_a_render_that_fits_at_level_0_is_returned_untouched_and_called_once(budget):
    render, calls = _fake({0: 1_000, 1: 100, 2: 10})
    html, level = budget.enforce(render)
    assert level == 0 and _size(html) == 1_000 and html.startswith("<p>0</p>")
    assert calls == [0]


def test_an_oversize_level_0_steps_to_level_1_and_stops(budget):
    render, calls = _fake({0: CAP + 1, 1: 5_000, 2: 10})
    html, level = budget.enforce(render)
    assert level == 1 and html.startswith("<p>1</p>")
    assert calls == [0, 1]


def test_level_2_is_used_only_when_level_1_is_also_over(budget):
    render, calls = _fake({0: CAP * 3, 1: CAP + 1, 2: 300})
    html, level = budget.enforce(render)
    assert level == 2 and html.startswith("<p>2</p>")
    assert calls == [0, 1, 2]


def test_the_cap_is_inclusive_65536_fits_and_65537_does_not(budget):
    render, calls = _fake({0: CAP, 1: 1, 2: 1})
    assert budget.enforce(render)[1] == 0
    render, calls = _fake({0: CAP + 1, 1: 1, 2: 1})
    assert budget.enforce(render)[1] == 1


def test_the_cap_counts_bytes_so_multibyte_text_reaches_it_sooner(budget):
    fits = "€" * (CAP // 3)                      # 65,535 bytes
    over = "€" * (CAP // 3 + 1)                  # 65,538 bytes
    assert _size(fits) <= CAP < _size(over) and len(over) < CAP
    assert budget.enforce(lambda level: fits)[1] == 0
    html, level = budget.enforce(lambda level: over if level == 0 else "short")
    assert (html, level) == ("short", 1)


def test_exhausting_the_ladder_raises_and_names_the_sizes(budget):
    render, calls = _fake({0: CAP * 2, 1: CAP + 10, 2: CAP + 1})
    with pytest.raises(budget.BudgetExceeded) as exc:
        budget.enforce(render)
    assert calls == [0, 1, 2]
    assert issubclass(budget.BudgetExceeded, ValueError)
    msg = str(exc.value)
    assert str(CAP + 1) in msg and str(CAP) in msg


def test_the_result_is_never_over_the_cap(budget):
    rng = random.Random(7)
    for _ in range(200):
        sizes = {lv: rng.choice([10, CAP - 1, CAP, CAP + 1, CAP * 4]) for lv in (0, 1, 2)}
        render, _ = _fake(sizes)
        try:
            html, level = budget.enforce(render)
        except budget.BudgetExceeded:
            assert min(sizes.values()) > CAP
        else:
            assert _size(html) <= CAP
            assert level == min(lv for lv in (0, 1, 2) if sizes[lv] <= CAP)   # first that fits


def test_custom_levels_are_tried_in_the_given_order(budget):
    render, calls = _fake({0: 10, 1: 10, 2: 10})
    assert budget.enforce(render, levels=(1, 2))[1] == 1
    assert calls == [1]
    render, calls = _fake({0: 10, 1: 10, 2: 10})
    assert budget.enforce(render, levels=(2,))[1] == 2


@pytest.mark.parametrize("levels", [(), [], (5,), (0, 0), (2, 1), (0, 3), (-1,), (True,), ("1",)])
def test_levels_must_be_ascending_known_levels(budget, levels):
    render, _ = _fake({0: 1, 1: 1, 2: 1})
    with pytest.raises(ValueError):
        budget.enforce(render, levels=levels)


def test_a_renderer_exception_propagates_and_stops_the_ladder(budget):
    calls: list[int] = []

    def render(level):
        calls.append(level)
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        budget.enforce(render)
    assert calls == [0]


def test_a_non_string_render_is_rejected(budget):
    with pytest.raises(TypeError):
        budget.enforce(lambda level: b"bytes")


def test_enforce_is_deterministic(budget):
    render, _ = _fake({0: CAP + 5, 1: 400, 2: 10})
    assert budget.enforce(render) == budget.enforce(render)


# --------------------------------------------------------------------------- the ladder with svg.py primitives


def _plate_names(n: int) -> list[str]:
    return [f"plate_{i:03d}" for i in range(n)]


def _fake_deck_renderer(svg, budget, plates: int, wells: int = 1536):
    """A fake deck: full detail is one path of `wells` circles plus a per-plate grid attribute;
    level 1 is one filled block per plate with NO grid; level 2 is name lines, the sentence and
    the omission line. Mirrors D4's ladder without any PLR."""
    names = _plate_names(plates)

    def plate_full(i, name):
        d = "".join(svg.circle_path(2.25 * (k % 48) + 3, 2.25 * (k // 48) + 3, 0.85) for k in range(wells))
        grid = json.dumps({"ids": [f"W{k}" for k in range(wells)], "v": [k % 7 for k in range(wells)]})
        return svg.el("g", svg.path_el(d, fill="none", stroke="#1D2935"),
                      data_praxis_res=name, data_praxis_grid=grid)

    def plate_block(i, name):
        return svg.el("g", svg.path_el(svg.rect_path(3 * i, 0, 2.5, 8), fill="#C9CDD1"),
                      data_praxis_res=name)

    def render(level: int) -> str:
        lines = "".join(svg.text_line("p", "praxis-name", n) for n in names)
        sentence = svg.text_line("p", "praxis-sentence", f"{plates} pieces of labware.")
        if level == budget.LEVEL_FULL:
            body = "".join(plate_full(i, n) for i, n in enumerate(names))
        elif level == budget.LEVEL_BLOCKS:
            body = "".join(plate_block(i, n) for i, n in enumerate(names))
        else:
            body = svg.text_line("p", "praxis-note", budget.OMISSION_SENTENCE)
        drawing = svg.el("svg", body, viewBox="0 0 100 10") if level != budget.LEVEL_OMITTED else body
        return svg.el("div", lines + sentence + drawing)

    return render


def test_twenty_1536_well_plates_degrade_to_blocks_and_drop_the_grid(svg, budget):
    render = _fake_deck_renderer(svg, budget, plates=20)
    assert _size(render(0)) > CAP        # the premise: full detail is over the cap
    html, level = budget.enforce(render)
    assert level == budget.LEVEL_BLOCKS
    assert _size(html) <= CAP
    assert "data-praxis-grid" not in html            # level 1 drops the grid
    assert html.count("data-praxis-res") == 20       # ...but every plate is still findable
    assert budget.OMISSION_SENTENCE not in html      # the drawing is still there at level 1
    assert "<svg" in html


def test_the_same_deck_at_level_0_when_small_keeps_its_grid(svg, budget):
    render = _fake_deck_renderer(svg, budget, plates=1, wells=96)
    html, level = budget.enforce(render)
    assert level == budget.LEVEL_FULL and "data-praxis-grid" in html and _size(html) <= CAP


def test_summary_only_level_carries_the_omission_sentence_and_stays_under_the_cap(svg, budget):
    # 1,500 plates: blocks exceed the cap, the name lines and sentence (level 2) do not.
    render = _fake_deck_renderer(svg, budget, plates=1_500, wells=1)
    assert _size(render(1)) > CAP and _size(render(2)) <= CAP
    html, level = budget.enforce(render)
    assert level == budget.LEVEL_OMITTED
    assert _size(html) <= CAP
    assert budget.OMISSION_SENTENCE in html
    assert "<svg" not in html and "data-praxis-grid" not in html
    assert "plate_000" in html and "plate_1499" in html      # text is never dropped for a drawing
    assert "1500 pieces of labware." in html


def test_every_level_of_the_fake_is_valid_for_the_cap_or_reported(svg, budget):
    for plates in (1, 5, 20, 200, 1_500):
        render = _fake_deck_renderer(svg, budget, plates=plates, wells=1_536 if plates <= 20 else 1)
        try:
            html, level = budget.enforce(render)
        except budget.BudgetExceeded:
            pytest.fail(f"{plates} plates exhausted the ladder")
        assert _size(html) <= CAP, (plates, level)


# --------------------------------------------------------------------------- cap_tail


def _frame_text(frames: int, pad: int = 60) -> str:
    """A synthetic traceback: 2 lines per frame, a header, and a final exception line."""
    lines = ["Traceback (most recent call last):"]
    for i in range(frames):
        lines.append(f'  File "/lab/pkg/module_{i:03d}.py", line {i + 10}, in step_{i:03d}')
        lines.append("    " + f"call_{i:03d}(" + "a" * pad + ")")
    lines.append("KeyError: 'assay'")
    return "\n".join(lines) + "\n"


def _verify_tail(orig: str, out: str, limit: int) -> None:
    """Independent verifier. Raises AssertionError unless *out* is a correct cap_tail of *orig*
    whose last line is kept whole (the single-giant-line case has its own test)."""
    assert _size(out) <= limit
    trailing = "\n" if orig.endswith("\n") else ""
    lines = (orig[:-1] if trailing else orig).split("\n")
    assert out.endswith(trailing)
    head, sep, rest = (out[:-1] if trailing else out).partition("\n")
    m = re.fullmatch(rf"{ELLIPSIS} (\d+) earlier lines omitted", head)
    assert m, head
    n = int(m.group(1))
    kept = rest.split("\n") if sep else []
    assert n >= 1
    assert kept == lines[n:], "not the untouched tail, or N is wrong"
    # maximal: one more line (with its marker) would not fit
    cand = f"{ELLIPSIS} {n - 1} earlier lines omitted\n" + "\n".join(lines[n - 1:]) + trailing
    assert _size(cand) > limit, "a longer tail would still have fit"


def test_cap_tail_on_a_200_frame_traceback_keeps_the_tail_within_16_kib(budget):
    tb = _frame_text(200)
    assert _size(tb) > 3 * TB_CAP
    out = budget.cap_tail(tb, TB_CAP)
    _verify_tail(tb, out, TB_CAP)
    first, _, _ = out.partition("\n")
    n = int(first.split()[1])
    assert first == f"{ELLIPSIS} {n} earlier lines omitted"
    assert n > 0
    assert out.rstrip("\n").endswith("KeyError: 'assay'")      # the last line survives
    assert "module_199" in out and "module_000" not in out


def test_cap_tail_default_limit_is_16_kib(budget):
    tb = _frame_text(200)
    assert budget.cap_tail(tb) == budget.cap_tail(tb, TB_CAP)


def test_text_within_the_cap_is_returned_unchanged(budget):
    tb = _frame_text(3)
    assert budget.cap_tail(tb, TB_CAP) is tb or budget.cap_tail(tb, TB_CAP) == tb
    exact = "x" * TB_CAP
    assert budget.cap_tail(exact, TB_CAP) == exact
    assert budget.cap_tail("", TB_CAP) == ""


def test_one_byte_over_the_cap_is_truncated(budget):
    text = "\n".join(["a" * 99] * 165)          # 165*99 + 164 = 16,499 bytes
    assert _size(text) > TB_CAP
    _verify_tail(text, budget.cap_tail(text, TB_CAP), TB_CAP)
    boundary = ("a" * 99 + "\n") * 163 + "b" * (TB_CAP - 163 * 100)
    assert _size(boundary) == TB_CAP
    assert budget.cap_tail(boundary, TB_CAP) == boundary
    assert _size(budget.cap_tail(boundary + "c", TB_CAP)) <= TB_CAP


def test_n_counts_the_omitted_lines_exactly(budget):
    text = "\n".join(f"line {i}" for i in range(1_000))
    out = budget.cap_tail(text, 400)
    first, _, rest = out.partition("\n")
    kept = rest.split("\n")
    assert first == f"{ELLIPSIS} {1000 - len(kept)} earlier lines omitted"
    assert kept[-1] == "line 999" and kept == [f"line {i}" for i in range(1000 - len(kept), 1000)]


def test_multibyte_lines_are_measured_in_bytes(budget):
    tb = "\n".join(f"€€€ frame {i} \U0001f9ea" for i in range(2_000))
    out = budget.cap_tail(tb, 1_000)
    _verify_tail(tb, out, 1_000)
    out.encode("utf-8")       # valid


def test_a_single_line_longer_than_the_cap_is_cut_at_a_character_boundary(budget):
    text = "first\n" + "€" * 10_000            # last line is 30,000 bytes
    out = budget.cap_tail(text, 500)
    assert _size(out) <= 500
    head, _, tail = out.partition("\n")
    assert head == f"{ELLIPSIS} 1 earlier lines omitted"
    assert tail and set(tail) == {"€"}
    assert out.encode("utf-8").decode("utf-8") == out


def test_a_trailing_newline_is_preserved_only_when_present(budget):
    tb = _frame_text(200)
    assert budget.cap_tail(tb, TB_CAP).endswith("\n")
    assert not budget.cap_tail(tb.rstrip("\n"), TB_CAP).endswith("\n")


def test_cap_tail_is_correct_over_many_shapes_including_digit_boundaries(budget):
    rng = random.Random(1)
    for _ in range(300):
        n_lines = rng.choice([2, 9, 10, 11, 99, 100, 101, 999, 1000, 1001])
        lines = ["x" * rng.randint(0, 40) for _ in range(n_lines)]
        text = "\n".join(lines) + rng.choice(["", "\n"])
        limit = rng.choice([100, 257, 1_000, 3_000])
        if _size(text) <= limit:
            assert budget.cap_tail(text, limit) == text
            continue
        _verify_tail(text, budget.cap_tail(text, limit), limit)


def test_the_verifier_is_not_vacuous_it_rejects_naive_truncation_and_a_wrong_n(budget):
    """Controls: head-truncation (no marker), a wrong N, an over-budget output, a lost tail."""
    tb = _frame_text(200)
    good = budget.cap_tail(tb, TB_CAP)
    _verify_tail(tb, good, TB_CAP)                                    # positive control
    naive = tb[-TB_CAP:]
    with pytest.raises(AssertionError):
        _verify_tail(tb, naive, TB_CAP)
    first, _, rest = good.partition("\n")
    n = int(first.split()[1])
    with pytest.raises(AssertionError):
        _verify_tail(tb, f"{ELLIPSIS} {n + 1} earlier lines omitted\n{rest}", TB_CAP)
    with pytest.raises(AssertionError):
        _verify_tail(tb, good + "y" * TB_CAP, TB_CAP)
    with pytest.raises(AssertionError):                               # dropped the last line
        _verify_tail(tb, good.rstrip("\n").rsplit("\n", 1)[0] + "\n", TB_CAP)
    with pytest.raises(AssertionError):                               # kept the HEAD, not the tail
        head_kept = "\n".join(tb.split("\n")[: len(rest.split("\n"))])
        _verify_tail(tb, f"{first}\n{head_kept}\n", TB_CAP)


@pytest.mark.parametrize("limit", [0, 1, 5, 10])
def test_a_limit_too_small_for_the_marker_is_an_error(budget, limit):
    with pytest.raises(ValueError):
        budget.cap_tail("a\nb\nc\n" * 100, limit)


def test_cap_tail_rejects_non_text_and_bad_limits(budget):
    with pytest.raises(TypeError):
        budget.cap_tail(b"bytes", TB_CAP)
    for bad in (-1, 1.5, True, None):
        with pytest.raises((ValueError, TypeError)):
            budget.cap_tail("x", bad)


def test_cap_tail_is_deterministic(budget):
    tb = _frame_text(120)
    assert budget.cap_tail(tb, 5_000) == budget.cap_tail(tb, 5_000)


# --------------------------------------------------------------------------- staging


def test_budget_module_reaches_the_dist_manifest_walk():
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    spec = importlib.util.spec_from_file_location("_bm_under_test_budget", scripts / "build_manifest.py")
    bm = importlib.util.module_from_spec(spec)
    sys.modules["_bm_under_test_budget"] = bm
    spec.loader.exec_module(bm)
    overlay = Path(__file__).resolve().parents[1] / "overlay"
    assert "assets/python/praxis/display/budget.py" in {e["path"] for e in bm.collect_sources(overlay)}
