"""SVG and HTML primitives for ``praxis.display`` (task B1; spec D2, D3, D4, D14).

Pure standard library. No PyLabRobot, no IPython, no ``js``, no import of any other Praxis
module, and nothing here reads a browser or a kernel at import time, so the module imports in
plain CPython and the tests need no Pyodide.

**Escaping (D2).** Resource names and every other interpolated string are user-controlled, and
live outputs are trusted HTML. ``esc_text`` and ``esc_attr`` are the ONLY escape helpers, both
exactly ``html.escape(s, quote=True)``, and every interpolated string goes through one of them.
``attrs`` escapes every attribute value itself and refuses unsafe attribute names, so an
attribute cannot be broken out of. ``el`` takes ``inner`` as ALREADY-SAFE markup: build it from
``esc_text`` or from other helpers here, never from a raw string.

**What may be emitted (D2, D14).** No ``<script>``, no ``<style>`` element, no event-handler
attribute, no link or source attribute, and only the ``data-*`` names in ``ALLOWED_DATA_ATTRS``.
``check_output_html`` and ``check_bundle`` enforce that and are meant to be called by every
later display task's tests (and cheaply at runtime). ``image/svg+xml`` is never a mimebundle
key.

**Class-only text (S2).** On an untrusted reopen the sanitizer keeps only ``class`` on
``table``, ``details`` and ``summary``, and strips the SVG, ``style``, ``aria-label`` and every
``data-*``. ``text_line`` and ``details_html`` therefore emit class-only elements: the text they
carry stays meaningful with nothing but ``class``.

Numbers are formatted compactly and deterministically (``num``: at most two decimals, half up;
``num_ceil`` rounds UP, used wherever rounding down would break a floor from D5).
"""

from __future__ import annotations

import html as _html
import math
import re
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal, localcontext
from html.parser import HTMLParser

__all__ = [
    "ALLOWED_DATA_ATTRS", "ALLOWED_MIME", "STAMP_KINDS", "UnsafeHtmlError",
    "esc_text", "esc_attr", "num", "num_ceil", "fmt_amount",
    "attrs", "el", "path_el", "text_el", "text_line", "details_html",
    "circle_path", "rect_path", "cross_path",
    "check_output_html", "check_bundle",
]

# The only ``data-*`` names an output may carry. ``data-praxis-cell-state`` and
# ``data-praxis-exec`` are written by the shell onto cell DOM nodes, never inside an output.
ALLOWED_DATA_ATTRS = frozenset({"data-praxis-res", "data-praxis-grid", "data-praxis-minw"})

# A mimebundle carries exactly these (D2). ``image/svg+xml`` is deliberately absent.
ALLOWED_MIME = ("text/html", "text/plain")

STAMP_KINDS = frozenset({"plate", "tiprack", "container", "deck", "ledger", "error"})
_STAMP_KEYS = frozenset({"v", "kind", "resource", "rev", "session", "exec"})

_ATTR_NAME = re.compile(r"[A-Za-z_:][A-Za-z0-9_:.-]*")
_TAG_NAME = re.compile(r"[A-Za-z][A-Za-z0-9]*")
_CLASS = re.compile(r"[A-Za-z0-9_-]+(?: [A-Za-z0-9_-]+)*")
_DENIED_ATTRS = frozenset({"href", "src", "srcdoc", "xlink:href", "formaction", "action"})
_DENIED_TAGS = frozenset({
    "script", "style", "iframe", "frame", "frameset", "object", "embed", "applet", "link",
    "meta", "base", "foreignobject", "img", "video", "audio", "source", "form", "input",
    "button", "textarea", "select", "template",
})
_ANCHORS = frozenset({"start", "middle", "end"})


class UnsafeHtmlError(ValueError):
    """An output, attribute, tag or bundle broke a D2/D14 emission rule."""


# --------------------------------------------------------------------------- escaping


def esc_text(s) -> str:
    """Escape *s* for an HTML text position. Exactly ``html.escape(s, quote=True)``."""
    return _html.escape(str(s), quote=True)


def esc_attr(s) -> str:
    """Escape *s* for a double-quoted attribute value. Exactly ``html.escape(s, quote=True)``."""
    return _html.escape(str(s), quote=True)


# --------------------------------------------------------------------------- numbers


def _quantize(x, exp: str, rounding) -> Decimal:
    f = float(x)
    if not math.isfinite(f):
        raise ValueError(f"not a finite number: {x!r}")
    with localcontext() as ctx:
        ctx.prec = 60
        return Decimal(repr(f)).quantize(Decimal(exp), rounding=rounding)


def _plain(d: Decimal, group: bool = False) -> str:
    s = format(d, ",f" if group else "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


def num(x) -> str:
    """Compact coordinate: at most two decimals, half up, no trailing zeros, never ``-0``."""
    return _plain(_quantize(x, "0.01", ROUND_HALF_UP))


def num_ceil(x) -> str:
    """Like ``num`` but rounds UP to two decimals, so the value never shrinks (D5 floors)."""
    return _plain(_quantize(x, "0.01", ROUND_CEILING))


def fmt_amount(x) -> str:
    """Sentence number (section 3.2): thousands separator, at most one decimal, half up."""
    return _plain(_quantize(x, "0.1", ROUND_HALF_UP), group=True)


def _nums(*vals) -> str:
    """Space-separated ``num`` values; a space before a minus sign is dropped (SVG grammar)."""
    return " ".join(num(v) for v in vals).replace(" -", "-")


# --------------------------------------------------------------------------- attributes and elements


def _attr_name(key: str) -> str:
    if not isinstance(key, str):
        raise TypeError(f"attribute name must be str, got {type(key).__name__}")
    name = "class" if key == "cls" else key.replace("_", "-")
    if not _ATTR_NAME.fullmatch(name):
        raise ValueError(f"malformed attribute name: {key!r}")
    low = name.lower()
    if low.startswith("on") or low in _DENIED_ATTRS or low.endswith(":href"):
        raise ValueError(f"attribute not allowed in an output: {name!r}")
    if low.startswith("data-") and name not in ALLOWED_DATA_ATTRS:
        raise ValueError(f"data attribute not allowed in an output: {name!r}")
    return name


def attrs(**kw) -> str:
    """Attribute string, one leading space per attribute, in the order given.

    ``_`` in a name becomes ``-`` (``stroke_width`` -> ``stroke-width``); ``cls`` is ``class``.
    Values: ``str`` is escaped with ``esc_attr``, ``int``/``float`` go through ``num``, ``None``
    is omitted, ``bool`` is rejected. Names that are malformed, start with ``on``, are a link or
    source attribute, are a ``data-*`` outside ``ALLOWED_DATA_ATTRS``, or collide after
    normalisation raise ``ValueError``.
    """
    out: list[str] = []
    seen: set[str] = set()
    for key, value in kw.items():
        name = _attr_name(key)
        if name.lower() in seen:
            raise ValueError(f"duplicate attribute after normalisation: {name!r}")
        seen.add(name.lower())
        if value is None:
            continue
        if isinstance(value, bool):
            raise TypeError(f"attribute {name!r}: bool is not a value; pass a string")
        if isinstance(value, str):
            text = value
        elif isinstance(value, (int, float)):
            text = num(value)
        else:
            raise TypeError(f"attribute {name!r}: unsupported value type {type(value).__name__}")
        if name == "class" and not _CLASS.fullmatch(text):
            raise ValueError(f"malformed class value: {text!r}")
        out.append(f' {name}="{esc_attr(text)}"')
    return "".join(out)


def _check_tag(tag: str) -> str:
    if not isinstance(tag, str) or not _TAG_NAME.fullmatch(tag):
        raise ValueError(f"malformed tag name: {tag!r}")
    if tag.lower() in _DENIED_TAGS:
        raise ValueError(f"tag not allowed in an output: {tag!r}")
    return tag


def el(tag: str, inner: str = "", **kw) -> str:
    """``<tag ...>inner</tag>``. *inner* is ALREADY-SAFE markup (see the module docstring)."""
    _check_tag(tag)
    if not isinstance(inner, str):
        raise TypeError("inner must be str")
    return f"<{tag}{attrs(**kw)}>{inner}</{tag}>"


def path_el(d: str, **kw) -> str:
    """One self-closing ``<path>``; ``d`` is escaped like any attribute value."""
    return f"<path{attrs(d=d, **kw)}/>"


def text_el(x, y, s, size_units, *, anchor: str | None = None, **kw) -> str:
    """SVG ``<text>`` with its font size in USER UNITS (D5: ``12.5 / s_n`` mm).

    The size is rounded UP to two decimals so that ``size * s_min >= 11`` is never lost to
    rounding. *s* is escaped.
    """
    size = float(size_units)
    if not math.isfinite(size) or size <= 0:
        raise ValueError(f"font size must be a positive finite number, got {size_units!r}")
    if anchor is not None and anchor not in _ANCHORS:
        raise ValueError(f"anchor must be one of {sorted(_ANCHORS)}, got {anchor!r}")
    head = attrs(x=x, y=y, font_size=num_ceil(size), text_anchor=anchor, **kw)
    return f"<text{head}>{esc_text(s)}</text>"


def text_line(tag: str, cls: str, s) -> str:
    """A class-only text element (survives S2's sanitizer): ``<tag class=cls>escaped</tag>``."""
    return el(tag, esc_text(s), cls=cls)


def details_html(summary, body, *, cls: str = "praxis-details") -> str:
    """``<details><summary>..</summary><pre>..</pre></details>``, class-only, both texts escaped.

    S2: only ``class`` survives on ``details``/``summary`` after an untrusted reopen, so
    nothing here depends on any other attribute.
    """
    if not isinstance(cls, str) or not _CLASS.fullmatch(cls):
        raise ValueError(f"malformed class value: {cls!r}")
    return el(
        "details",
        el("summary", esc_text(summary), cls=f"{cls}-summary")
        + el("pre", esc_text(body), cls=f"{cls}-body"),
        cls=cls,
    )


# --------------------------------------------------------------------------- path builders
#
# Each returns ONE subpath (a ``d`` fragment); join fragments to build the single ``<path>``
# per state that D4 asks for. Coordinates are in the caller's user units (mm).


def _finite(name: str, v) -> float:
    f = float(v)
    if not math.isfinite(f):
        raise ValueError(f"{name} must be finite, got {v!r}")
    return f


def circle_path(cx, cy, r) -> str:
    """A circle as two arcs (one subpath): from the left point, +2r along x and back."""
    cx, cy, r = _finite("cx", cx), _finite("cy", cy), _finite("r", r)
    if r <= 0:
        raise ValueError(f"radius must be positive, got {r!r}")
    return (
        f"M{_nums(cx - r, cy)}"
        f"a{_nums(r, r, 0, 1, 0, 2 * r, 0)}"
        f"a{_nums(r, r, 0, 1, 0, -2 * r, 0)}z"
    )


def rect_path(x, y, w, h, rx=0) -> str:
    """A rectangle (one subpath), absolute coordinates; corner radius ``rx`` clamped to the box."""
    x, y, w, h = (_finite(n, v) for n, v in (("x", x), ("y", y), ("w", w), ("h", h)))
    rx = _finite("rx", rx)
    if w <= 0 or h <= 0:
        raise ValueError(f"width and height must be positive, got {w!r} x {h!r}")
    if rx < 0:
        raise ValueError(f"corner radius must not be negative, got {rx!r}")
    r = min(rx, w / 2, h / 2)
    x2, y2 = x + w, y + h
    if r == 0:
        return f"M{_nums(x, y)}H{num(x2)}V{num(y2)}H{num(x)}z"
    arc = f"A{_nums(r, r, 0, 0, 1)}"
    return (
        f"M{_nums(x + r, y)}H{num(x2 - r)}{arc} {_nums(x2, y + r)}"
        f"V{num(y2 - r)}{arc} {_nums(x2 - r, y2)}"
        f"H{num(x + r)}{arc} {_nums(x, y2 - r)}"
        f"V{num(y + r)}{arc} {_nums(x + r, y)}z"
    ).replace(" -", "-")


def cross_path(cx, cy, half) -> str:
    """An X mark: two diagonal line subpaths spanning ``cx +- half`` by ``cy +- half``."""
    cx, cy, half = _finite("cx", cx), _finite("cy", cy), _finite("half", half)
    if half <= 0:
        raise ValueError(f"half-size must be positive, got {half!r}")
    return (
        f"M{_nums(cx - half, cy - half)}L{_nums(cx + half, cy + half)}"
        f"M{_nums(cx - half, cy + half)}L{_nums(cx + half, cy - half)}"
    )


# --------------------------------------------------------------------------- output guards


class _Guard(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.problems: list[str] = []

    def handle_starttag(self, tag, attr_list):
        if tag.lower() in _DENIED_TAGS:
            self.problems.append(f"element <{tag}>")
        for name, _ in attr_list:
            low = name.lower()
            if low.startswith("on"):
                self.problems.append(f"event-handler attribute {name!r}")
            elif low in _DENIED_ATTRS or low.endswith(":href"):
                self.problems.append(f"link/source attribute {name!r}")
            elif low.startswith("data-") and name not in ALLOWED_DATA_ATTRS:
                self.problems.append(f"data attribute {name!r}")


_RAW_SCRIPT_STYLE = re.compile(r"<\s*(?:script|style)", re.IGNORECASE)


def check_output_html(doc: str) -> None:
    """Raise ``UnsafeHtmlError`` unless *doc* obeys D2/D14.

    Rejected: any ``<script>``/``<style>`` (also as raw text), the other denied elements
    (frames, objects, links, images, forms), event-handler attributes, link/source attributes,
    and any ``data-*`` outside ``ALLOWED_DATA_ATTRS``. Escaped user text is fine.
    """
    if not isinstance(doc, str):
        raise TypeError("html must be str")
    if _RAW_SCRIPT_STYLE.search(doc):
        raise UnsafeHtmlError("raw <script> or <style> in output html")
    guard = _Guard()
    guard.feed(doc)
    guard.close()
    if guard.problems:
        raise UnsafeHtmlError("; ".join(sorted(set(guard.problems))))


def _is_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _check_stamp(stamp) -> None:
    if not isinstance(stamp, dict):
        raise UnsafeHtmlError("stamp is not an object")
    keys = set(stamp)
    if keys != _STAMP_KEYS:
        raise UnsafeHtmlError(
            f"stamp keys must be {sorted(_STAMP_KEYS)}; missing {sorted(_STAMP_KEYS - keys)}, "
            f"extra {sorted(keys - _STAMP_KEYS)}"
        )
    if not _is_int(stamp["v"]) or stamp["v"] != 1:
        raise UnsafeHtmlError(f"stamp v must be 1, got {stamp['v']!r}")
    kind = stamp["kind"]
    if not isinstance(kind, str) or kind not in STAMP_KINDS:
        raise UnsafeHtmlError(f"stamp kind must be one of {sorted(STAMP_KINDS)}, got {kind!r}")
    resource, rev = stamp["resource"], stamp["rev"]
    if resource is not None and not isinstance(resource, str):
        raise UnsafeHtmlError("stamp resource must be a string or null")
    if rev is not None and (not _is_int(rev) or rev < 0):
        raise UnsafeHtmlError("stamp rev must be a non-negative integer or null")
    if not isinstance(stamp["session"], str) or not stamp["session"]:
        raise UnsafeHtmlError("stamp session must be a non-empty string")
    ex = stamp["exec"]
    if ex is not None and (not _is_int(ex) or ex < 0):
        raise UnsafeHtmlError("stamp exec must be a non-negative integer or null")
    # D2 "values by kind": a ledger has no resource and no rev; an error has no rev.
    if kind == "ledger" and (resource is not None or rev is not None):
        raise UnsafeHtmlError("a ledger stamp has resource null and rev null")
    if kind == "error" and rev is not None:
        raise UnsafeHtmlError("an error stamp has rev null")


def check_bundle(data, metadata) -> None:
    """Raise ``UnsafeHtmlError`` unless ``(data, metadata)`` is a well-formed D2 mimebundle.

    ``data`` has exactly the keys ``text/html`` and ``text/plain`` (no ``image/svg+xml``, no
    script MIME), the html passes ``check_output_html`` and the plain text is non-empty. The
    stamp is read like the shell's ``stampOf``: ``metadata["praxis"]``, else
    ``metadata["text/html"]["praxis"]`` (the S3-B carrier), and must have exactly the keys
    ``v kind resource rev session exec`` with legal values.
    """
    if not isinstance(data, dict) or set(data) != set(ALLOWED_MIME):
        raise UnsafeHtmlError(
            f"bundle data keys must be exactly {list(ALLOWED_MIME)}, got "
            f"{sorted(data) if isinstance(data, dict) else type(data).__name__}"
        )
    if not isinstance(data["text/plain"], str) or not data["text/plain"]:
        raise UnsafeHtmlError("text/plain must be a non-empty string")
    check_output_html(data["text/html"])
    if not isinstance(metadata, dict):
        raise UnsafeHtmlError("metadata is not an object")
    stamp = metadata.get("praxis")
    if stamp is None:
        carrier = metadata.get("text/html")
        stamp = carrier.get("praxis") if isinstance(carrier, dict) else None
    if stamp is None:
        raise UnsafeHtmlError("no stamp at metadata['praxis'] or metadata['text/html']['praxis']")
    _check_stamp(stamp)
