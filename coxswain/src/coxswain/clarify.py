"""Deterministic clarification-answer matching and FR-8 re-entry (W4).

Everything here runs on the CLICK path and the TYPED path alike, and neither
may touch a model (FR-8/§7): the matcher works ONLY over the candidate set the
gate already fetched -- the ``GroundingExitPayload.candidates`` a clarify exit
carried out of cue 2 -- using three strategies in a fixed order:

1. **label** -- the candidate's name, compared trimmed/case-insensitively;
2. **position** -- the candidate's position string, likewise;
3. **simple synonym** -- both sides run through one tiny canonicalization
   (leading article dropped, a closed set of location nouns singularized), then
   compared again. This is what makes typed "rail 7" hit position "rails 7".

A strategy that matches zero candidates falls through to the next; a strategy
that matches MORE THAN ONE fails closed to "no answer" rather than guessing
(NFR-5) -- two carriers on "rails 7" cannot be told apart by that answer.

Re-entry (FR-8): an answered slot is bound into the ``ParsedCall`` immutably
(``dataclasses.replace``, mirroring the gate's own convention) and the gate is
re-entered AT THE CUE THAT EXITED. That cue advances only once every slot it
governs is resolved, which is what ``resolve_clarification_loop`` drives: it
consumes user answers until the exited cue completes a pass with zero
unresolved slots (or the answers run out, which simply leaves the turn open --
the card stays up).

NFR-1/NFR-2: pure Python, dependency-free, CPython-importable; no ``js``, no
``praxis.*`` imports, and no parse/model layer imports at all (asserted by
test_clarify_matcher.py structurally).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Any, Final, Sequence

from coxswain.fft.context import GatePassContext, KernelInstance, ParsedCall

__all__ = [
    "CLARIFY_DISPOSITIONS",
    "ClarificationError",
    "MatchResult",
    "answer_disambiguation",
    "answer_incomplete",
    "answer_not_found",
    "match_candidate",
    "reenter_after_clarification",
    "resolve_clarification_loop",
    "select_candidate",
]


class ClarificationError(ValueError):
    """A clarification answer could not be applied. Raised, never swallowed:
    a silently dropped answer would strand the turn open with no card."""


#: Dispositions whose exits are resolved by answering (FR-8). ``clarify:
#: precondition`` is deliberately absent -- cue 3's exit is resolved by the
#: FR-10 override path, never by this module.
CLARIFY_DISPOSITIONS: Final[frozenset[str]] = frozenset(
    {"clarify:disambiguate", "clarify:not_found", "clarify:incomplete"}
)


@dataclass(frozen=True)
class MatchResult:
    """The matcher's verdict: exactly one candidate, or none."""

    candidate: KernelInstance | None
    #: Which strategy produced the hit: "label" | "position" | "synonym";
    #: None when nothing matched uniquely.
    strategy: str | None


# --- normalization + simple synonyms ------------------------------------------

_WS_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[^\w\s]")
_LEADING_ARTICLES: Final[tuple[str, ...]] = ("the", "a", "an")

#: Closed set of singular/plural pairs the synonym strategy canonicalizes.
#: Deliberately small: this is "simple synonym" (spec W4), not an ontology.
_SINGULARS: Final[dict[str, str]] = {
    "rails": "rail",
    "slots": "slot",
    "wells": "well",
    "columns": "column",
    "rows": "row",
    "carriers": "carrier",
    "plates": "plate",
}


def _norm(value: str) -> str:
    """Trim, lowercase, collapse whitespace, drop punctuation."""
    lowered = value.strip().lower()
    return _WS_RE.sub(" ", _PUNCT_RE.sub("", lowered)).strip()


def _canon(value: str) -> str:
    """One canonical form shared by answers AND candidate strings."""
    normed = _norm(value)
    tokens = [t for t in normed.split(" ") if t]
    while tokens and tokens[0] in _LEADING_ARTICLES:
        tokens.pop(0)
    tokens = [_SINGULARS.get(t, t) for t in tokens]
    return " ".join(tokens)


def _norm_eq(answer_norm: str, target: str) -> bool:
    return bool(answer_norm) and answer_norm == _norm(target)


def _canon_eq(answer_canon: str, target: str) -> bool:
    return bool(answer_canon) and answer_canon == _canon(target)


def match_candidate(
    answer: Any, candidates: Sequence[KernelInstance]
) -> MatchResult:
    """Match one user answer against the already-fetched candidate set.

    Strategies run label -> position -> synonym; the first strategy with
    EXACTLY ONE hit wins, any strategy with more than one hit fails closed,
    and a non-string answer simply matches nothing. Label and position are
    normalized-but-literal comparisons; ONLY the synonym strategy applies
    canonicalization, which is what lets "rail 7" name position "rails 7".
    """
    if not isinstance(answer, str):
        return MatchResult(candidate=None, strategy=None)
    norm = _norm(answer)
    canon = _canon(answer)
    if not norm:
        return MatchResult(candidate=None, strategy=None)

    for strategy, field in (("label", "name"), ("position", "position")):
        hits = [
            c
            for c in candidates
            if getattr(c, field, None) and _norm_eq(norm, str(getattr(c, field)))
        ]
        if len(hits) == 1:
            return MatchResult(candidate=hits[0], strategy=strategy)
        if len(hits) > 1:
            # Ambiguous even after normalization: refuse to guess (NFR-5).
            return MatchResult(candidate=None, strategy=None)

    synonym_hits = [
        c
        for c in candidates
        if (c.name and _canon_eq(canon, c.name))
        or (c.position and _canon_eq(canon, c.position))
    ]
    if len(synonym_hits) == 1:
        return MatchResult(candidate=synonym_hits[0], strategy="synonym")
    return MatchResult(candidate=None, strategy=None)


def select_candidate(candidates: Sequence[KernelInstance], index: Any) -> KernelInstance:
    """The click path: pick by position in the as-given payload order (FR-3).

    Bounds/type violations raise loudly -- a click can only ever name a
    candidate the card rendered."""
    if not isinstance(index, int) or isinstance(index, bool):
        raise ClarificationError(f"candidate index must be an int, got {index!r}")
    if index < 0 or index >= len(candidates):
        raise ClarificationError(
            f"candidate index {index} out of range for {len(candidates)} candidate(s)"
        )
    return candidates[index]


def _slot_or_raise(call: ParsedCall, slot: str) -> None:
    if not any(s.arg_name == slot for s in call.unresolved_slots):
        raise ClarificationError(
            f"slot {slot!r} is not an unresolved slot of {call.name!r}; refusing to bind"
        )


# --- answer binding (immutably, off the exit payload only) ----------------------


def _payload_of(prior: Any) -> Any:
    payload = getattr(prior, "payload", None)
    if payload is None:
        raise ClarificationError("prior outcome carries no exit payload")
    return payload


def answer_disambiguation(
    prior: Any, call: ParsedCall, *, index: Any = None, answer: Any = None
) -> ParsedCall:
    """Bind a disambiguation answer (click ``index`` or typed ``answer``) into
    the call. Both forms route through the SAME fetched candidate set."""
    payload = _payload_of(prior)
    slot = getattr(payload, "slot", "")
    candidates = tuple(getattr(payload, "candidates", ()) or ())
    _slot_or_raise(call, slot)

    choice: KernelInstance | None = None
    if index is not None:
        choice = select_candidate(candidates, index)
    elif answer is not None:
        choice = match_candidate(answer, candidates).candidate
    if choice is None:
        raise ClarificationError(f"no candidate resolved for slot {slot!r}")

    return replace(
        call,
        params={**call.params, slot: choice.name},
        unresolved_slots=tuple(s for s in call.unresolved_slots if s.arg_name != slot),
    )


def answer_not_found(prior: Any, call: ParsedCall, *, new_reference: Any) -> ParsedCall:
    """Rephrase the symbolic reference of a ``clarify:not_found`` slot. The new
    phrase is re-grounded by the re-entered cue -- never resolved here."""
    payload = _payload_of(prior)
    slot = getattr(payload, "slot", "")
    _slot_or_raise(call, slot)
    if not isinstance(new_reference, str) or not new_reference.strip():
        raise ClarificationError("a not-found answer requires a non-empty replacement reference")
    return replace(
        call,
        unresolved_slots=tuple(
            s if s.arg_name != slot else replace(s, reference=new_reference.strip())
            for s in call.unresolved_slots
        ),
    )


def answer_incomplete(prior: Any, call: ParsedCall, *, supplies: Any) -> ParsedCall:
    """Supply values for ``clarify:incomplete``'s missing required fields."""
    if not isinstance(supplies, dict) or not supplies:
        raise ClarificationError("an incomplete answer requires at least one {field: value}")
    unknown = sorted(set(supplies) - set(call.missing_required))
    if unknown:
        raise ClarificationError(
            f"field(s) {unknown} were never requested; missing required fields are "
            f"{list(call.missing_required)}"
        )
    params = {**call.params}
    for field, value in supplies.items():
        if not isinstance(value, str) or not value.strip():
            raise ClarificationError(f"value for {field!r} must be a non-empty string")
        params[field] = value.strip()
    return replace(
        call,
        params=params,
        missing_required=tuple(f for f in call.missing_required if f not in supplies),
    )


# --- FR-8 re-entry ---------------------------------------------------------------


def reenter_after_clarification(
    gate: Any, call: ParsedCall, ctx: GatePassContext, *, prior: Any
) -> Any:
    """Re-enter the FFT AT THE CUE THAT EXITED (FR-8), gate_seq incrementing."""
    start_cue = getattr(prior, "exited_cue", None)
    if start_cue is None:
        raise ClarificationError("prior outcome records no exited cue; cannot re-enter")
    return gate.re_enter(call, ctx, start_cue=start_cue)


def resolve_clarification_loop(
    gate: Any,
    ctx: GatePassContext,
    *,
    prior: Any,
    call: ParsedCall,
    answers: Sequence[dict[str, Any]],
) -> list[Any]:
    """Answer-and-re-enter until the exited cue completes a pass with zero
    unresolved slots (FR-8's repeat rule) or the answers run out.

    ``answers`` entries are keyed per disposition: ``{"index": n}`` /
    ``{"answer": "..."}`` for disambiguate, ``{"new_reference": "..."}`` for
    not_found, ``{"supplies": {...}}`` for incomplete. Returns every outcome
    INCLUDING ``prior``, in pass order.
    """
    outcomes: list[Any] = [prior]
    current_call = call
    queue = list(answers)
    while getattr(prior, "disposition", "") in CLARIFY_DISPOSITIONS and queue:
        ans = queue.pop(0)
        disposition = prior.disposition
        if disposition == "clarify:disambiguate":
            current_call = answer_disambiguation(
                prior, current_call, index=ans.get("index"), answer=ans.get("answer")
            )
        elif disposition == "clarify:not_found":
            current_call = answer_not_found(
                prior, current_call, new_reference=ans.get("new_reference")
            )
        else:  # clarify:incomplete
            current_call = answer_incomplete(prior, current_call, supplies=ans.get("supplies"))
        prior = reenter_after_clarification(gate, current_call, ctx, prior=prior)
        outcomes.append(prior)
    return outcomes
