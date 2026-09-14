"""Identifier minting per spec §2.1.

Field names and formats here are normative: ``turn_id`` is
``cx-<epoch_ms>-<6 chars base36>`` and is minted once per user command
submission, before any parse or grounding work starts. ``fingerprint_id`` and
``override_id`` are turn-scoped composite keys of the form
``<turn_id>:<gate_seq>:<fp|ovr>``.

This module is dependency-free (NFR-2) and CPython-importable with no browser
bindings (NFR-1).
"""

from __future__ import annotations

import secrets
import time
from typing import Final

_BASE36_ALPHABET: Final[str] = "0123456789abcdefghijklmnopqrstuvwxyz"
_TURN_ID_RANDOM_CHARS: Final[int] = 6


def _random_base36(length: int) -> str:
    return "".join(secrets.choice(_BASE36_ALPHABET) for _ in range(length))


def mint_turn_id() -> str:
    """Mint a conversation-turn identifier: ``cx-<epoch_ms>-<6 base36 chars>``."""
    epoch_ms = time.time_ns() // 1_000_000
    return f"cx-{epoch_ms}-{_random_base36(_TURN_ID_RANDOM_CHARS)}"


def fingerprint_id_for(turn_id: str, gate_seq: int) -> str:
    """Per-fingerprint-capture identifier: ``<turn_id>:<gate_seq>:fp``."""
    return f"{turn_id}:{gate_seq}:fp"


def override_id_for(turn_id: str, gate_seq: int) -> str:
    """Per-override-use identifier: ``<turn_id>:<gate_seq>:ovr``."""
    return f"{turn_id}:{gate_seq}:ovr"
