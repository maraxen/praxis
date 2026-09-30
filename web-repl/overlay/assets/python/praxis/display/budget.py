"""The D4 byte cap, its degradation ladder, and ``cap_tail`` (task B1; spec D4, AC-13).

Pure standard library: no PyLabRobot, no IPython, no ``js``, no other Praxis module.

**Cap.** At most ``MAX_HTML_BYTES`` = 65,536 bytes of UTF-8 ``text/html`` per output, counting
everything (the SVG, the ``data-praxis-grid`` descriptors, the ledger table, an error panel's
traceback).

**Ladder** (the drawing always degrades first; text is never dropped to save a drawing):

* ``LEVEL_FULL`` (0): the normal render.
* ``LEVEL_BLOCKS`` (1): every labware drawn as a filled block, and ``data-praxis-grid`` dropped
  for blocked labware.
* ``LEVEL_OMITTED`` (2): the drawing omitted: name line, sentence and ``OMISSION_SENTENCE``.

``enforce`` owns the loop and the byte count; the renderer owns what each level draws. If even
the last level is over the cap ``BudgetExceeded`` is raised rather than emit an over-cap or a
truncated (unbalanced) document; the renderer must keep its text (names included) small enough
for level 2 to fit.

**Traceback cap.** ``cap_tail`` keeps the TAIL of a traceback within 16 KiB and replaces the
head with one line, ``"... N earlier lines omitted"`` (the ellipsis is U+2026).
"""

from __future__ import annotations

__all__ = [
    "MAX_HTML_BYTES", "TRACEBACK_CAP_BYTES", "LEVEL_FULL", "LEVEL_BLOCKS", "LEVEL_OMITTED",
    "LEVELS", "OMISSION_SENTENCE", "TAIL_MARKER_FORMAT", "BudgetExceeded",
    "html_bytes", "enforce", "cap_tail",
]

MAX_HTML_BYTES = 65_536
TRACEBACK_CAP_BYTES = 16_384

LEVEL_FULL = 0
LEVEL_BLOCKS = 1
LEVEL_OMITTED = 2
LEVELS = (LEVEL_FULL, LEVEL_BLOCKS, LEVEL_OMITTED)

OMISSION_SENTENCE = "Drawing omitted: it would exceed 64 KiB."
TAIL_MARKER_FORMAT = "… {n} earlier lines omitted"


class BudgetExceeded(ValueError):
    """Every level tried was over ``MAX_HTML_BYTES``."""


def html_bytes(s: str) -> int:
    """UTF-8 byte length of *s*. A lone surrogate counts as 3 bytes rather than raising, so the
    count can only overstate."""
    return len(s.encode("utf-8", "surrogatepass"))


def _check_levels(levels) -> tuple:
    levels = tuple(levels)
    if not levels:
        raise ValueError("levels must not be empty")
    for lv in levels:
        if isinstance(lv, bool) or not isinstance(lv, int) or lv not in LEVELS:
            raise ValueError(f"unknown level {lv!r}; levels are {LEVELS}")
    if any(b <= a for a, b in zip(levels, levels[1:])):
        raise ValueError(f"levels must be strictly ascending, got {levels}")
    return levels


def enforce(render_fn, levels=LEVELS):
    """Render at each level in order and return ``(html, level)`` for the first render within
    ``MAX_HTML_BYTES`` (inclusive). ``render_fn(level) -> str``. A renderer exception
    propagates. ``BudgetExceeded`` if no level fits."""
    sizes: dict[int, int] = {}
    for level in _check_levels(levels):
        doc = render_fn(level)
        if not isinstance(doc, str):
            raise TypeError(f"render_fn({level}) returned {type(doc).__name__}, not str")
        n = html_bytes(doc)
        if n <= MAX_HTML_BYTES:
            return doc, level
        sizes[level] = n
    raise BudgetExceeded(
        f"render is over the {MAX_HTML_BYTES}-byte cap at every level tried "
        f"(bytes by level: {sizes})"
    )


def cap_tail(text: str, limit: int = TRACEBACK_CAP_BYTES) -> str:
    """Keep the tail of *text* within *limit* UTF-8 bytes.

    Text already within the limit is returned unchanged. Otherwise the result is the marker line
    ``"... N earlier lines omitted"`` followed by the LAST lines of *text*, as many as fit, where
    ``N`` is the number of lines dropped. Lines split on ``"\\n"`` only, and a trailing newline
    is preserved when present. If even the last line alone does not fit, its tail is kept, cut
    at a character boundary, and ``N`` counts the lines wholly before it. ``ValueError`` if
    *limit* cannot hold the marker plus one byte.
    """
    if not isinstance(text, str):
        raise TypeError("text must be str")
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise TypeError("limit must be an int")
    if limit < 0:
        raise ValueError("limit must not be negative")
    if html_bytes(text) <= limit:
        return text

    trailing = "\n" if text.endswith("\n") else ""
    lines = (text[:-1] if trailing else text).split("\n")
    total = len(lines)
    fixed = len(trailing)

    def marker_cost(n: int) -> int:
        return html_bytes(TAIL_MARKER_FORMAT.format(n=n)) + 1 + fixed  # marker + "\n" + trailing

    # Keep lines[i:] for the smallest i >= 1 that fits. Cost is non-increasing in i (each step
    # drops >= 1 byte of tail and grows the marker by at most one digit), so scan from the tail.
    best = None
    tail_bytes = -1  # bytes of lines[i:] joined by "\n"; -1 offsets the first join
    for i in range(total - 1, 0, -1):
        tail_bytes += html_bytes(lines[i]) + 1
        if marker_cost(i) + tail_bytes <= limit:
            best = i
        else:
            break
    if best is not None:
        return TAIL_MARKER_FORMAT.format(n=best) + "\n" + "\n".join(lines[best:]) + trailing

    # Not even the last line fits whole: keep its tail.
    n = total - 1
    budget = limit - marker_cost(n)
    if budget < 1:
        raise ValueError(f"limit {limit} is too small for the omission marker plus any text")
    kept: list[str] = []
    used = 0
    for ch in reversed(lines[-1]):
        b = html_bytes(ch)
        if used + b > budget:
            break
        kept.append(ch)
        used += b
    return TAIL_MARKER_FORMAT.format(n=n) + "\n" + "".join(reversed(kept)) + trailing
