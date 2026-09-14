"""Hardened extractor for FunctionGemma NATIVE call syntax (D3, research §1/§6).

Target grammar (the model's bespoke token syntax -- NOT JSON):

    <start_function_call>call:name{arg:<escape>value<escape>,arg2:<escape>v2<escape>}<end_function_call>

Hardening rules (each one exists because a greedy 270M decode WILL hit it):

1. Multiple call spans in one output are all extracted (parallel calling is
   a trained workflow).
2. A span missing its ``<end_function_call>`` (stop-token loss / truncation)
   still parses; the truncation is recorded as a non-fatal note.
3. Values are delimited by ``<escape>`` markers: commas, braces and colons
   inside them never break splitting (char-level scanner, no naive regex
   split on `{`/`}`/`,`).
4. Bare (unescaped) values are tolerated and whitespace-trimmed; numeric-
   looking values coerce to int then float (documented harness normalization;
   the scorer normalizes BOTH sides again before equality).
5. A span without the ``call:`` prefix or with an unparseable name is
   SKIPPED and reported in ``errors`` -- it must not silently vanish, and
   must not crash scoring either.
6. Duplicate keys inside one call: LAST occurrence wins (dict semantics),
   recorded as a note.
7. Empty argument body ``{}`` yields empty params.
8. Anything outside spans is ignored; zero spans -> empty result (which the
   scorer treats as abstention -> clarify path).

Pure stdlib; input string is never mutated; no model imports here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

__all__ = ["ParsedCall", "ParseResult", "parse_function_calls"]

START = "<start_function_call>"
END = "<end_function_call>"
ESC = "<escape>"

_SPAN_RE = re.compile(re.escape(START) + r"(.*?)(" + re.escape(END) + "|$)", re.DOTALL)
_NAME_RE = re.compile(r"^\s*call:\s*([A-Za-z_][A-Za-z0-9_.\-]*)\s*\{")


@dataclass(frozen=True)
class ParsedCall:
    name: str
    params: dict


@dataclass(frozen=True)
class ParseResult:
    calls: list[ParsedCall]
    errors: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _find_body(span: str) -> tuple[str | None, str | None]:
    """Return ``(body, error)`` for the brace-delimited arg region of one span,
    escape-aware: braces inside <escape>...</escape> are literal text."""
    m = _NAME_RE.match(span)
    if not m:
        return None, f"span lacks 'call:<name>{{' prefix: {span[:60]!r}"
    start = m.end()  # just past the opening '{'
    depth = 0
    i = start
    in_escape = False
    while i < len(span):
        if in_escape:
            if span.startswith(ESC, i):
                in_escape = False
                i += len(ESC)
                continue
            i += 1
            continue
        if span.startswith(ESC, i):
            in_escape = True
            i += len(ESC)
            continue
        ch = span[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            if depth == 0:
                return span[start:i], None
            depth -= 1
        i += 1
    # Unterminated braces (truncation): take everything we have.
    return span[start:], "unterminated parameter block (truncated?); recovered best-effort"


def _split_top_level(body: str) -> list[str]:
    """Split on commas that sit outside <escape> regions and nested structures."""
    parts: list[str] = []
    buf: list[str] = []
    i = 0
    in_escape = False
    depth = 0
    while i < len(body):
        if in_escape:
            if body.startswith(ESC, i):
                in_escape = False
                buf.append(ESC)  # kept verbatim; stripped by _strip_escapes
                i += len(ESC)
                continue
            buf.append(body[i])
            i += 1
            continue
        if body.startswith(ESC, i):
            in_escape = True
            buf.append(ESC)
            i += len(ESC)
            continue
        ch = body[i]
        if ch in "{[":
            depth += 1
        elif ch in "}]":
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append("".join(buf))
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    tail = "".join(buf).strip()
    if tail:
        parts.append(tail)
    return parts


def _coerce(value: str):
    """Numeric-looking strings become numbers (harness normalization)."""
    text = value.strip()
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text


def _strip_escapes(value: str) -> str:
    text = value.strip()
    if text.startswith(ESC) and text.endswith(ESC) and len(text) >= 2 * len(ESC):
        inner = text[len(ESC):-len(ESC)]
        # Keep interior content verbatim (may itself contain ESC pairs only
        # by degenerate model output; strip those too for robustness).
        return inner.replace(ESC, "")
    return text


def _decode_value(raw: str) -> object:
    """Decode one argument value the way the FunctionGemma chat template's
    ``format_argument`` macro encodes it (checkpoint ``chat_template.jinja``):

    - ``<escape>text<escape>``           -> scalar (existing path: strip, coerce)
    - ``[v1,v2,...]``                     -> list, each element decoded recursively
    - ``{k1:v1,k2:v2}``                   -> dict (tool-call arguments render nested
                                            keys UNescaped; escaped keys tolerated)
    - anything else                       -> scalar path (bare numbers, bare text)

    Brackets inside ``<escape>`` spans are literal, so a whole-escaped value
    is checked FIRST and never mistaken for a container (260902 fix; before
    it a list came back as one string and failed every list-valued row).
    """
    text = raw.strip()
    if text.startswith(ESC) and text.endswith(ESC) and len(text) >= 2 * len(ESC):
        return _coerce(_strip_escapes(text))
    if len(text) >= 2 and text[0] == "[" and text[-1] == "]":
        inner = text[1:-1]
        if not inner.strip():
            return []
        return [_decode_value(item) for item in _split_top_level(inner) if item.strip()]
    if len(text) >= 2 and text[0] == "{" and text[-1] == "}":
        inner = text[1:-1]
        out: dict[str, object] = {}
        for item in _split_top_level(inner):
            if not item.strip():
                continue
            pair = _parse_pair(item)
            if pair is None:
                return _coerce(_strip_escapes(text))  # not a mapping after all: keep as text
            out[pair[0]] = pair[1]
        return out
    return _coerce(_strip_escapes(text))


def _parse_pair(part: str) -> tuple[str, object] | None:
    """One ``key:value`` pair; colon split at top level (outside escapes).
    Keys may be bare or ``<escape>``-wrapped; values go through
    :func:`_decode_value`."""
    i = 0
    in_escape = False
    while i < len(part):
        if in_escape:
            if part.startswith(ESC, i):
                in_escape = False
                i += len(ESC)
                continue
            i += 1
            continue
        if part.startswith(ESC, i):
            in_escape = True
            i += len(ESC)
            continue
        if part[i] == ":":
            key = _strip_escapes(part[:i])
            raw_value = part[i + 1:]
            if not key:
                return None
            return key, _decode_value(raw_value)
        i += 1
    return None


def parse_function_calls(raw: str) -> ParseResult:
    """Extract every ``<start_function_call>...<end_function_call>`` span."""
    calls: list[ParsedCall] = []
    errors: list[str] = []
    notes: list[str] = []

    for m in _SPAN_RE.finditer(raw):
        span = m.group(1)
        if not m.group(2):  # END marker absent (regex matched via `$`)
            notes.append("span without <end_function_call> (truncated); parsed best-effort")
        body, body_err = _find_body(span)
        name_m = _NAME_RE.match(span)
        if body is None or name_m is None:
            errors.append(body_err or f"unparsable span: {span[:60]!r}")
            continue
        if body_err:
            notes.append(f"call:{name_m.group(1)}: {body_err}")
        params: dict = {}
        for part in _split_top_level(body):
            if not part.strip():
                continue
            pair = _parse_pair(part)
            if pair is None:
                errors.append(f"unparsable argument fragment: {part[:60]!r}")
                continue
            key, value = pair
            if key in params:
                notes.append(f"call:{name_m.group(1)}: duplicate key {key!r}; last wins")
            params[key] = value
        calls.append(ParsedCall(name=name_m.group(1), params=params))

    return ParseResult(calls=calls, errors=errors, notes=notes)
