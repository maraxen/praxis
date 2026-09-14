"""N5-B categorization: Matches / Conflicts / Omissions for clarification
cards (W4, FR-7).

The derivation reads ONLY the Layer 2/3 output a clarify exit already carries
-- a ``GroundingExitPayload``'s candidates, slot and message -- plus nothing
else: no kernel reads, no model call, no new grounding lookups. It exists for
clarification cards ONLY; FR-7 scopes it away from the propose/confirm card,
and test_categorize.py asserts structurally that neither the kernel's propose-
path modules nor the propose-card JS sources reference this module at all.

Derivation rules (deterministic, closed over the payload):

- ``matches``   -- one line per candidate, AS GIVEN (FR-3's order rule):
  ``"<name> on <position>"``, or bare ``<name>`` when the instance has no
  position. Empty unless candidates exist.
- ``conflicts`` -- how the candidates differ from EACH OTHER on a categorized
  attribute (position spread -> "They occupy different locations."; resource-
  type spread -> likewise). When every categorized attribute is identical the
  section stays empty rather than fabricating a conflict. For a not_found exit
  (no candidates) the kernel's own message IS the conflict: it states exactly
  where the utterance clashed with the world.
- ``omissions`` -- what the utterance left unspecified: the slot cue 2 was
  asking about ("You did not say which source."). Not derived when there is no
  slot to name.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

__all__ = ["Categorization", "categorize_grounding"]


@dataclass(frozen=True)
class Categorization:
    """The N5-B sections, each a tuple of render-ready strings."""

    matches: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()
    omissions: tuple[str, ...] = ()


_POSITION_CONFLICT: Final[str] = "They occupy different locations."
_TYPE_CONFLICT: Final[str] = "They are different kinds of resource."


def _humanize_slot(slot: str) -> str:
    return str(slot).replace("_", " ").strip()


def _candidate_lines(candidates: tuple[Any, ...]) -> tuple[str, ...]:
    lines: list[str] = []
    for c in candidates:
        name = getattr(c, "name", "")
        position = getattr(c, "position", None)
        lines.append(f"{name} on {position}" if position else str(name))
    return tuple(lines)


def _conflict_lines(candidates: tuple[Any, ...]) -> tuple[str, ...]:
    positions = {getattr(c, "position", None) for c in candidates}
    types = {getattr(c, "resource_type", None) for c in candidates}
    conflicts: list[str] = []
    if len(positions) > 1:
        conflicts.append(_POSITION_CONFLICT)
    if len(types) > 1:
        conflicts.append(_TYPE_CONFLICT)
    return tuple(conflicts)


def categorize_grounding(payload: Any) -> Categorization:
    """Derive Matches / Conflicts / Omissions from one grounding exit payload.

    Raises ValueError loudly on an unusable payload (neither candidates nor a
    message): a card that cannot be categorized must fail loud, never render
    three empty sections as if nothing were ambiguous (NFR-5)."""
    if payload is None:
        raise ValueError("categorize_grounding requires an exit payload")
    raw_candidates = tuple(getattr(payload, "candidates", ()) or ())
    message = getattr(payload, "message", "") or ""
    slot = getattr(payload, "slot", "") or ""

    if not raw_candidates and not message:
        raise ValueError(
            "exit payload carries neither candidates nor a message; "
            "there is nothing to categorize"
        )

    matches = _candidate_lines(raw_candidates) if raw_candidates else ()
    if raw_candidates:
        conflicts = _conflict_lines(raw_candidates)
    elif message:
        # not_found: the kernel's explanation of the clash with the world.
        conflicts = (str(message),)
    else:
        conflicts = ()

    omissions = (f"You did not say which {_humanize_slot(slot)}.",) if slot else ()
    return Categorization(matches=matches, conflicts=conflicts, omissions=omissions)
