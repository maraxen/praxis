"""Per-turn gate context and its injected sources (W2, spec §4.x).

Everything a gate pass needs besides the parsed call lives here: who asked
(the ``turn_id``/``session_id``/``card_revision`` trio that every §2.4 record
stamps), the two cue-side sources named by the spec -- the §4.5
``ConcurrencyProbe`` and the Layer-2b grounding view -- the live kernel state
cue 3 evaluates against, and the audit seam every decision is written through.

NFR-1/NFR-2: pure Python, dependency-free, CPython-importable, no ``js``, no
``praxis.*``. ``KernelInstance`` is re-exported verbatim from
``coxswain.plr.grounding`` so there is exactly one instance shape in the tree.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from coxswain.fft.concurrency import ConcurrencyProbe
from coxswain.fft.preconditions.state_models import SimulationState
from coxswain.plr.grounding import KernelInstance

__all__ = [
    "AuditSink",
    "GatePassContext",
    "GroundingSource",
    "KernelInstance",
    "MapInstanceSource",
    "ParsedCall",
    "UnresolvedSlot",
]


# --- Parsed-call shapes -------------------------------------------------------


@dataclass(frozen=True)
class UnresolvedSlot:
    """One argument the parser left symbolic: ``reference`` is the user's
    phrase, to be grounded against live kernel objects of ``resource_type``
    (FR-7)."""

    arg_name: str
    reference: str
    resource_type: str


@dataclass(frozen=True)
class ParsedCall:
    """The parse-layer output the gate consumes (§7's ParseSource boundary).

    ``missing_required`` drives cue 1 and ``unresolved_slots`` drives cue 2;
    both default to empty so a fully-formed call needs no extra ceremony.
    Frozen by contract: the gate binds auto-resolved slots with
    ``dataclasses.replace``, never mutation."""

    name: str
    receiver_type: str
    params: dict[str, Any] = field(default_factory=dict)
    missing_required: tuple[str, ...] = ()
    unresolved_slots: tuple[UnresolvedSlot, ...] = ()


# --- Injected sources ---------------------------------------------------------


@runtime_checkable
class GroundingSource(Protocol):
    """Layer-2b candidate lookup behind cue 2 (FR-7). Read path only.

    Returns the candidate instances for one symbolic reference, in the
    source's declared order (FR-3's as-given rule -- never sorted here). An
    empty tuple means not found; the cue maps cardinality 0/1/N to
    ``clarify:not_found`` / auto-resolve / ``clarify:disambiguate``."""

    def resolve_slot(self, reference: str, resource_type: str) -> tuple[KernelInstance, ...]: ...


class MapInstanceSource:
    """Fixture-backed GroundingSource over a plain mapping of
    ``(reference, resource_type) -> instances``.

    Reference keys are matched case-insensitively (a user typing ``plate A``
    and ``Plate A`` mean the same thing); instance order inside each bucket is
    preserved as given. This is the deterministic stand-in for the live-kernel
    registry that Production Mode injects; the cue layer cannot tell the
    difference, which is the point."""

    def __init__(self, mapping: dict[tuple[str, str], list[KernelInstance]]) -> None:
        self._buckets: dict[tuple[str, str], tuple[KernelInstance, ...]] = {
            (reference.strip().lower(), resource_type): tuple(instances)
            for (reference, resource_type), instances in mapping.items()
        }

    def resolve_slot(self, reference: str, resource_type: str) -> tuple[KernelInstance, ...]:
        return self._buckets.get((reference.strip().lower(), resource_type), ())


@runtime_checkable
class AuditSink(Protocol):
    """The fail-closed audit seam (NFR-5, FR-9).

    Every write returns a durability claim: True iff durably recorded. False,
    or a raise, means the store is unavailable and the gate must stop with
    ``blocked:audit_unavailable`` -- never continue past a failed write.
    W5's async writer adds the ``KERNEL_RTT_TIMEOUT_MS`` ack window on top of
    this shape; the gate treats False and raise identically either way."""

    def record(self, decision: Any) -> bool: ...

    def record_override(self, record: Any) -> bool: ...

    def record_fingerprint(self, fingerprint: Any) -> bool: ...


# --- Per-turn context ---------------------------------------------------------


@dataclass(frozen=True)
class GatePassContext:
    """One gate pass's inputs. Immutable by design: a pass is a pure sweep of
    cues over these values, and the confirm-time recheck gets a fresh context
    rather than mutating this one."""

    turn_id: str
    session_id: str
    card_revision: int
    #: §4.5 cue-0 signal source. ``None`` from ``is_active()`` blocks.
    probe: ConcurrencyProbe
    #: Live kernel state cue 3 evaluates against and the digest digests.
    kernel_state: SimulationState
    #: Layer-2b candidate source for cue 2.
    instance_source: GroundingSource
    #: Audit seam; the gate falls back to its constructor sink when unset.
    audit: AuditSink | None = None
    #: Pass timestamp (seconds). Records stamp this, keeping tests deterministic.
    ts: float = 0.0
