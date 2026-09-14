"""Layer 2b grounding: symbolic-reference resolution against live kernel
objects (FR-7's candidate sets feed cue 2).

READ PATH ONLY: ``resolve()`` never mutates the kernel object registry. It
maps a user-facing reference to 0/1/N named instances; the cue layer turns
``not_found`` into ``clarify:not_found`` and ``ambiguous`` into
``clarify:disambiguate``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable

__all__ = [
    "GroundingStatus",
    "InstanceSource",
    "KernelInstance",
    "GroundingResult",
    "resolve",
]


class GroundingStatus(str, Enum):
    OK = "ok"
    AMBIGUOUS = "ambiguous"
    NOT_FOUND = "not_found"


@dataclass(frozen=True)
class KernelInstance:
    """One live kernel object visible to grounding."""

    name: str
    resource_type: str
    position: str | None = None


@runtime_checkable
class InstanceSource(Protocol):
    """The live-kernel view injected into resolve(). Read-only by contract."""

    def instances(self, resource_type: str) -> list[KernelInstance]: ...


@dataclass(frozen=True)
class GroundingResult:
    status: GroundingStatus
    candidates: tuple[KernelInstance, ...] = ()
    selected: KernelInstance | None = None


def _match(reference: str, instance: KernelInstance) -> bool:
    lowered = reference.strip().lower()
    return lowered == instance.name.lower()


def resolve(
    reference: str,
    *,
    resource_type: str,
    source: InstanceSource,
) -> GroundingResult:
    """Resolve one symbolic reference against live kernel objects.

    Deterministic read path:
    - exactly one name match -> OK with that instance selected;
    - more than one          -> AMBIGUOUS with ALL matches as candidates, in
      the source's declared order (never sorted, per FR-3's as-given rule);
    - zero                   -> NOT_FOUND.

    Raises whatever the injected source raises on malformed responses -- the
    cue layer catches and fails closed (NFR-5)."""
    candidates = tuple(i for i in source.instances(resource_type) if _match(reference, i))
    if not candidates:
        return GroundingResult(status=GroundingStatus.NOT_FOUND)
    if len(candidates) == 1:
        return GroundingResult(
            status=GroundingStatus.OK, candidates=candidates, selected=candidates[0]
        )
    return GroundingResult(status=GroundingStatus.AMBIGUOUS, candidates=candidates)
