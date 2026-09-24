#!/usr/bin/env python3
"""D6 static gesture-invariant checker (backlog #4296, spec
``.praxia/docs/specs/260922_repl-persistence-ladder.md`` D6 / T5).

**The invariant.** Every gesture-requiring call --
``storage.persist()``, ``pickDirectory(...)``, ``showDirectoryPicker(...)``
and ``handle.requestPermission(...)`` -- must sit inside a synchronous,
non-``async`` NAMED function (a plain ``function`` declaration/expression or
an object-literal method shorthand -- never an arrow function) whose name
matches ``^on[A-Z]\\w*Click$``. Between that function's opening ``{`` and the
call there must be no ``await``, no ``.then(`` and no ``async`` token.
Synchronous conditionals that read already-cached state (for example
``if (!pickDirectory) return``) are allowed, because they do not yield to the
event loop and so do not spend the click's transient user-activation window.

This mirrors P5.7's rule for ``requestDevice`` (D6, D2): "zero ``await``
between the click handler's opening brace and the first gesture call."

Also enforced (B-11): no scanned file may contain the literal string
``__praxis_test_force_prompt`` -- that switch is a smoke-harness-only escape
hatch (``scripts/repl_smoke.py``) and must never ship in product code.

**Parse approach and its known limit.** This is a small brace-matching
tokenizer over a hand-stripped ("comments and string/template literals
blanked to same-length whitespace, preserving line breaks") copy of the
source -- not a real JS parser. Two limits follow directly from that choice,
by design (see D6's own row in the spec: "beyond a token scan; the Unit
level catches it"):

1. **Template-literal ``${...}`` interpolations are opaque.** The whole
   backtick-to-backtick span is blanked, so a gesture call written inside a
   template-literal expression would not be seen at all. None of the actual
   call sites in this codebase are written that way.
2. **Only the literal tokens ``await``, ``.then(`` and ``async`` are
   detected between a function's opening brace and the call.** A call to
   some *other* asynchronous helper function (one that itself awaits
   something, but is invoked here by a plain, synchronous-looking call
   expression) is invisible to a token scan -- there is nothing async-shaped
   in the calling function's own text. Catching that needs runtime evidence,
   which is exactly what the Unit level (bun tests, activation flag) and the
   Browser level (real ``page.click()``, ``inClickDispatch``) are for (D6's
   three-level table). This script only proves the *textual* shape.

Usage::

    uv run python web-repl/scripts/check_gesture_invariant.py
    uv run python web-repl/scripts/check_gesture_invariant.py --root /tmp/some/dir

With no ``--root``, scans ``web-repl/shell/persistence/*.js`` (excluding any
``__tests__`` directory). Exit 0 if the invariant holds everywhere and the
forbidden string is absent; exit 1 otherwise, with ``file:line: rule:
detail`` printed for every violation found.
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("check_gesture_invariant")

# --- fixed layout ------------------------------------------------------------
_THIS_FILE = Path(__file__).resolve()
SCRIPTS_DIR = _THIS_FILE.parent
WEB_REPL_ROOT = SCRIPTS_DIR.parent
REPO_ROOT = WEB_REPL_ROOT.parent
DEFAULT_SCAN_ROOTS = [WEB_REPL_ROOT / "shell" / "persistence"]

EXCLUDED_DIR_NAME = "__tests__"

# D6: the gesture-requiring call list. `\.persist\(` deliberately does NOT
# match `.persisted(` -- there is no "(" immediately after "persist" in that
# spelling, so the literal substring never occurs. `pickDirectory` is in the
# list per Revision 1 A-3: core.js never names `showDirectoryPicker` itself,
# it only ever calls the injected `pickDirectory`, so leaving it out would
# make the checker falsely green (D6).
GESTURE_CALLS: dict[str, re.Pattern[str]] = {
    "storage.persist()": re.compile(r"\.persist\("),
    "pickDirectory()": re.compile(r"\bpickDirectory\("),
    "showDirectoryPicker()": re.compile(r"\bshowDirectoryPicker\("),
    "handle.requestPermission()": re.compile(r"\.requestPermission\("),
}

FORBIDDEN_STRING = "__praxis_test_force_prompt"

ON_CLICK_NAME_RE = re.compile(r"^on[A-Z]\w*Click$")
CONTROL_KEYWORDS = {"if", "for", "while", "switch", "catch", "with"}
ASYNC_BEFORE_CALL_RE = re.compile(r"(?<![\w$])await(?![\w$])|(?<![\w$])async(?![\w$])|\.then\(")

# Tokens of interest for the brace/paren matcher: identifiers/keywords, `=>`,
# and the four bracket characters. Everything else (operators, numbers,
# punctuation) is irrelevant to "what function am I in" and is skipped.
TOKEN_RE = re.compile(r"=>|[A-Za-z_$][\w$]*|[(){}]")


# --- comment/string/template-literal stripping -------------------------------


def strip_comments_and_strings(text: str) -> str:
    """Return a same-length, same-newline-positions copy of ``text`` with
    ``//...``/``/*...*/`` comments and ``'...'``/``"..."``/`` `...` ``
    string/template literals blanked to spaces, so gesture-call regexes and
    the brace tokenizer only ever see real code (never comment prose quoting
    a call, or a string containing one). Known limit: a template literal's
    ``${...}`` interpolation is blanked along with the rest of the literal
    (see the module docstring).
    """
    out = list(text)
    n = len(text)
    i = 0
    while i < n:
        c = text[i]
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            j = i
            while j < n and text[j] != "\n":
                out[j] = " "
                j += 1
            i = j
        elif c == "/" and i + 1 < n and text[i + 1] == "*":
            j = i
            while j < n:
                if text[j] != "\n":
                    out[j] = " "
                if text[j] == "*" and j + 1 < n and text[j + 1] == "/":
                    if text[j + 1] != "\n":
                        out[j + 1] = " "
                    j += 2
                    break
                j += 1
            i = j
        elif c in ("'", '"', "`"):
            quote = c
            j = i
            out[j] = " "
            j += 1
            while j < n and text[j] != quote:
                if text[j] == "\\" and j + 1 < n:
                    if text[j] != "\n":
                        out[j] = " "
                    j += 1
                    if j < n and text[j] != "\n":
                        out[j] = " "
                    j += 1
                    continue
                if text[j] != "\n":
                    out[j] = " "
                j += 1
            if j < n:
                out[j] = " "  # closing quote/backtick
                j += 1
            i = j
        else:
            i += 1
    return "".join(out)


# --- tokenizer + brace/paren matcher -----------------------------------------


def tokenize(clean: str) -> list[tuple[str, str, int]]:
    """Return ``(kind, text, start_offset)`` for every token of interest in
    ``clean`` (already comment/string-stripped).
    """
    tokens: list[tuple[str, str, int]] = []
    for m in TOKEN_RE.finditer(clean):
        text = m.group(0)
        if text == "=>":
            kind = "ARROW"
        elif text == "(":
            kind = "LPAREN"
        elif text == ")":
            kind = "RPAREN"
        elif text == "{":
            kind = "LBRACE"
        elif text == "}":
            kind = "RBRACE"
        else:
            kind = "ID"
        tokens.append((kind, text, m.start()))
    return tokens


@dataclass
class Frame:
    start: int  # offset of the opening `{`
    is_function: bool
    is_async: bool
    is_arrow: bool
    name: str | None


def classify_brace(
    tokens: list[tuple[str, str, int]],
    i: int,
    matching_open_paren: dict[int, int],
) -> Frame:
    """Classify the `{` at token index ``i``: is it a function body (a named
    `function` declaration/expression, an anonymous `function`, an
    object/class method-shorthand, or an arrow function), or just a plain
    block (`if`/`for`/`while`/`catch`/`try`/object literal/etc.)?
    """
    pos = tokens[i][2]
    is_function = False
    is_async = False
    is_arrow = False
    name: str | None = None

    if i > 0:
        prev_kind, _prev_text, _prev_pos = tokens[i - 1]
        if prev_kind == "ARROW":
            is_function = True
            is_arrow = True
        elif prev_kind == "RPAREN":
            open_idx = matching_open_paren.get(i - 1)
            if open_idx is not None and open_idx - 1 >= 0:
                before_kind, before_text, _ = tokens[open_idx - 1]
                if before_kind == "ID" and before_text in CONTROL_KEYWORDS:
                    is_function = False
                elif before_kind == "ID" and before_text == "function":
                    # anonymous `function () { ... }`
                    is_function = True
                elif before_kind == "ID":
                    if (
                        open_idx - 2 >= 0
                        and tokens[open_idx - 2][0] == "ID"
                        and tokens[open_idx - 2][1] == "function"
                    ):
                        # named `function NAME() { ... }`
                        is_function = True
                        name = before_text
                        if (
                            open_idx - 3 >= 0
                            and tokens[open_idx - 3][0] == "ID"
                            and tokens[open_idx - 3][1] == "async"
                        ):
                            is_async = True
                    else:
                        # method shorthand: `NAME(...) { ... }`
                        is_function = True
                        name = before_text
                        if (
                            open_idx - 2 >= 0
                            and tokens[open_idx - 2][0] == "ID"
                            and tokens[open_idx - 2][1] == "async"
                        ):
                            is_async = True

    return Frame(start=pos, is_function=is_function, is_async=is_async, is_arrow=is_arrow, name=name)


@dataclass
class Violation:
    path: Path
    line: int
    rule: str
    detail: str

    def format(self) -> str:
        return f"{self.path}:{self.line}: {self.rule}: {self.detail}"


def _line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def check_gesture_calls(path: Path, raw_text: str) -> list[Violation]:
    """Apply the D6 invariant's four rules to every gesture call found in
    ``raw_text`` (D6: enclosing function is named, non-async, non-arrow,
    ``on[A-Z]\\w*Click``; nothing async-shaped precedes the call in it).
    """
    clean = strip_comments_and_strings(raw_text)
    tokens = tokenize(clean)

    matches: list[tuple[int, str]] = []
    for label, pattern in GESTURE_CALLS.items():
        for m in pattern.finditer(clean):
            matches.append((m.start(), label))
    matches.sort(key=lambda pair: pair[0])

    violations: list[Violation] = []
    stack: list[Frame] = []
    paren_stack: list[int] = []
    matching_open_paren: dict[int, int] = {}
    ti = 0

    for call_pos, label in matches:
        while ti < len(tokens) and tokens[ti][2] < call_pos:
            kind, _text, pos = tokens[ti]
            if kind == "LPAREN":
                paren_stack.append(ti)
            elif kind == "RPAREN":
                if paren_stack:
                    open_idx = paren_stack.pop()
                    matching_open_paren[ti] = open_idx
            elif kind == "LBRACE":
                stack.append(classify_brace(tokens, ti, matching_open_paren))
            elif kind == "RBRACE":
                if stack:
                    stack.pop()
            ti += 1

        line = _line_of(raw_text, call_pos)
        frame = next((f for f in reversed(stack) if f.is_function), None)

        if frame is None:
            violations.append(
                Violation(
                    path,
                    line,
                    "no-enclosing-function",
                    f"{label} has no enclosing named on*Click function",
                )
            )
            continue

        if frame.is_arrow:
            violations.append(
                Violation(
                    path,
                    line,
                    "arrow-function",
                    f"{label} sits inside an arrow function, not a named on*Click function",
                )
            )
        if frame.is_async:
            violations.append(
                Violation(
                    path,
                    line,
                    "async-function",
                    f"{label}'s enclosing function {frame.name!r} is declared async",
                )
            )
        if frame.name is None or not ON_CLICK_NAME_RE.match(frame.name):
            violations.append(
                Violation(
                    path,
                    line,
                    "bad-name",
                    f"{label}'s enclosing function name {frame.name!r} does not match on*Click",
                )
            )

        between = clean[frame.start : call_pos]
        async_match = ASYNC_BEFORE_CALL_RE.search(between)
        if async_match:
            violations.append(
                Violation(
                    path,
                    line,
                    "async-before-call",
                    f"{label} is preceded by {async_match.group(0)!r} in the same function body",
                )
            )

    return violations


def check_forbidden_string(path: Path, raw_text: str) -> list[Violation]:
    """B-11: the smoke-harness-only forced-prompt switch must never ship in
    product code under the scanned roots.
    """
    violations: list[Violation] = []
    for i, line in enumerate(raw_text.splitlines(), start=1):
        if FORBIDDEN_STRING in line:
            violations.append(
                Violation(
                    path,
                    i,
                    "forbidden-string",
                    f"{FORBIDDEN_STRING!r} must not appear in product code (B-11)",
                )
            )
    return violations


def iter_scan_files(roots: list[Path]) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.js")):
            if EXCLUDED_DIR_NAME in path.parts:
                continue
            files.append(path)
    return files


def check_tree(roots: list[Path]) -> list[Violation]:
    violations: list[Violation] = []
    for path in iter_scan_files(roots):
        raw_text = path.read_text(encoding="utf-8")
        violations += check_gesture_calls(path, raw_text)
        violations += check_forbidden_string(path, raw_text)
    return violations


# --- CLI ----------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument(
        "--root",
        dest="roots",
        type=Path,
        action="append",
        default=None,
        help="Directory to scan (repeatable). Defaults to "
        "web-repl/shell/persistence. Testing hook for pointing at a "
        "scratch tree of fixtures.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Debug-level logging.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    roots = [r.resolve() for r in args.roots] if args.roots else DEFAULT_SCAN_ROOTS
    files = iter_scan_files(roots)
    if not files:
        logger.warning("No .js files found under %s", ", ".join(str(r) for r in roots))

    violations = check_tree(roots)

    if violations:
        for v in violations:
            logger.error(v.format())
        logger.error("%d gesture-invariant violation(s) found.", len(violations))
        return 1

    logger.info("D6 gesture invariant holds over %d file(s).", len(files))
    return 0


if __name__ == "__main__":
    sys.exit(main())
