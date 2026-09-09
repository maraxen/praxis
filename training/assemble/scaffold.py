"""Exact developer-turn scaffold template (P2.5 deliverable 3, D6-rev2).

The template FILE ``developer_scaffold_template.txt`` is the committed,
byte-authoritative artifact: a documentation header followed by a BEGIN
marker; everything after that marker IS the verbatim scaffold and nothing may
follow it. This module only LOADS it -- the bytes live in the file, not here.

DATE/TIMESTAMP INJECTION OMITTED (stated explicitly per D6-rev2 / C-m3): the
mobile-actions preamble ("Current date and time given in ...", "Day of week
is ...") is deliberately absent from this template. The corpus therefore
contains no time-dependent bytes, which is also what keeps regeneration
idempotent.
"""

from __future__ import annotations

from pathlib import Path

__all__ = [
    "BEGIN_MARKER",
    "SCAFFOLD_TEMPLATE_NAME",
    "SCAFFOLD_VERSION",
    "scaffold_template_bytes",
    "scaffold_template_path",
    "scaffold_template_text",
]

#: Committed template file (relative to this package).
SCAFFOLD_TEMPLATE_NAME = "developer_scaffold_template.txt"

#: Marker line: everything AFTER it (exclusive) is the verbatim scaffold.
BEGIN_MARKER = "# --- BEGIN VERBATIM SCAFFOLD (bytes below are the template; file ends inside it) ---"

#: Recorded scaffold identity, mirroring golden manifest's `scaffold` field.
SCAFFOLD_VERSION = "functiongemma-native/research-s2a-developer-scaffold/no-date-injection(D6-rev2)"


def scaffold_template_path() -> Path:
    return Path(__file__).resolve().parent / SCAFFOLD_TEMPLATE_NAME


def _split_template(raw: bytes) -> bytes:
    marker_line = (BEGIN_MARKER + "\n").encode("utf-8")
    idx = raw.find(marker_line)
    if idx < 0:
        raise AssertionError(f"scaffold template missing BEGIN marker: {scaffold_template_path()}")
    body = raw[idx + len(marker_line):]
    if not body:
        raise AssertionError("scaffold template has empty body after BEGIN marker")
    return body


def scaffold_template_bytes() -> bytes:
    """The EXACT committed scaffold bytes (header stripped)."""
    return _split_template(scaffold_template_path().read_bytes())


def scaffold_template_text() -> str:
    return scaffold_template_bytes().decode("utf-8")
