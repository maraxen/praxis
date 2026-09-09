"""Utterance normalization for P2.4 dedup -- parse_source.py:53-56 semantics.

One rule for "did the user say this", not two: trim ends + collapse internal
whitespace + case-fold. Deliberately identical in spirit (and byte-for-byte in
behavior) to ``coxswain.parse_source._normalize_utterance``; the parity is
pinned by a test (training/tests/test_dedup.py::test_normalize_parity_with_coxswain)
rather than by importing a private symbol across the F2 boundary.
"""

from __future__ import annotations

from typing import Any

__all__ = ["normalize_utterance"]


def normalize_utterance(value: Any) -> str:
    """Trim ends, collapse internal whitespace, case-fold. Non-str -> ''."""
    if not isinstance(value, str):
        return ""
    return " ".join(value.split()).casefold()
