"""FR-3 confirmation-phrase derivation and matching -- kernel side.

Mirrored EXACTLY by ``web-repl/shell/coxswain/phrase.js``; both sides must
agree on the same fixtures in ``coxswain/tests/fixtures/parsed_calls/*.json``
(``test_phrase_parity.py`` asserts all three layers: fixture-vs-schema glue,
Python derivation, and a live bun subprocess evaluating ``phrase.js``).

The rules, exhaustively (spec FR-3):

- **verb** -- the schema's ``verb`` field for the call, lowercased. Never the
  raw function name. The verb is supplied by the caller (``execute.py`` reads
  it from ``plr.tool_schema.TOOL_SCHEMA``); this module never guesses one.
- **object phrase** -- a resolved resource or location descriptor, NEVER a
  quantity. Numbers and booleans in target/noun positions raise rather than
  render, so volumes, counts, and units cannot leak into what the user is
  asked to type.
- **multi-target calls** -- first target in as-given order (never sorted,
  never deduplicated) followed by `` +<n-1> more``.
- **length** -- capped at ``PHRASE_MAX_CHARS`` (60). If the assembled phrase
  overflows, the first target's DESCRIPTOR alone is truncated on a word
  boundary and the phrase is REGENERATED from the truncated form, so the
  string a user is asked to type is always exactly the string rendered.

Matching (also FR-3): case-insensitive with collapsed internal whitespace and
trimmed ends. No other normalization -- no punctuation folding, no unicode
folding.

NFR-1/NFR-2: pure stdlib, CPython-importable, no ``js``, no ``praxis.*``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final

__all__ = [
    "NOUN_KEYS",
    "PHRASE_MAX_CHARS",
    "TARGET_KEYS",
    "derive_phrase",
    "normalize_phrase",
    "phrase_matches",
]

#: FR-3 length cap. Mirrored by NFR-7's STRING_CAPS["confirmation_phrase"].
PHRASE_MAX_CHARS: Final[int] = 60

#: Closed key vocabularies for reading a resolved call's params. Order is
#: normative: the FIRST present key wins, which makes descriptor selection
#: deterministic even when several keys are present at once (e.g. a transfer
#: carrying both ``source`` and ``destination`` resolves its object phrase
#: from ``destination`` because it sorts earlier here).
TARGET_KEYS: Final[tuple[str, ...]] = (
    "destination",
    "destinations",
    "target",
    "targets",
    "to",
    "at",
    "location",
    "source",
)

NOUN_KEYS: Final[tuple[str, ...]] = ("what", "noun", "object")

_FIXED_CONNECTOR: Final[str] = " at "
_MULTI_TARGET_TEMPLATE: Final[str] = " +{saved} more"


def _call_fields(call: Any) -> tuple[str, Mapping[str, Any]]:
    """Accept a mapping ({verb, params}) or any object exposing .verb/.params."""
    if isinstance(call, Mapping):
        verb = call.get("verb")
        params = call.get("params", {})
        if not isinstance(verb, str):
            raise ValueError(
                f"derive_phrase requires a schema verb string, got {verb!r} -- "
                "never derive a phrase from a raw function name"
            )
        if params is None:
            params = {}
        if not isinstance(params, Mapping):
            raise ValueError(f"derive_phrase params must be a mapping, got {type(params)!r}")
        return verb, params
    verb = getattr(call, "verb", None)
    params = getattr(call, "params", None)
    if isinstance(verb, str):
        return _call_fields({"verb": verb, "params": params or {}})
    raise ValueError(f"derive_phrase cannot read verb/params off {call!r}")


def _first_present(keys: tuple[str, ...], params: Mapping[str, Any]) -> tuple[str, Any] | None:
    for key in keys:
        value = params.get(key)
        if value is not None:
            return key, value
    return None


def _descriptor(value: Any) -> str:
    """Render ONE target as its resource/location descriptor. Fail loud on
    quantities: a number or boolean in a target slot is a malformed call, not
    something to type at hardware."""
    if isinstance(value, str):
        return value
    # KernelInstance shape (plr.grounding): prefer position, fall back to name.
    if isinstance(value, Mapping):
        position = value.get("position")
        name = value.get("name")
        if isinstance(position, str) and position.strip():
            return position
        if isinstance(name, str) and name.strip():
            return name
        raise ValueError(f"descriptor mapping carries no usable position/name: {value!r}")
    for attr in ("position", "name"):
        candidate = getattr(value, attr, None)
        if isinstance(candidate, str) and candidate.strip():
            return candidate
    raise ValueError(
        f"quantities and booleans never appear in a confirmation phrase "
        f"(FR-3); got descriptor value {value!r}"
    )


def _truncate_words(text: str, budget: int) -> str:
    """Cut *text* to at most *budget* characters on a word boundary. No
    ellipsis: the result is REGENERATED INTO the typed phrase (FR-3), so the
    output must stay exactly typeable."""
    if len(text) <= budget:
        return text
    if budget <= 0:
        raise ValueError(
            f"cannot fit a confirmation phrase within {PHRASE_MAX_CHARS} chars: "
            f"the fixed prefix leaves a non-positive descriptor budget ({budget})"
        )
    head = text[:budget]
    cut = head.rfind(" ")
    if cut <= 0:
        # Single token longer than the budget: a word boundary does not exist,
        # so hard-cut rather than exceed the cap.
        return text[:budget].rstrip()
    return head[:cut].rstrip()


def derive_phrase(call: Any) -> str:
    """Derive the confirmation phrase for a RESOLVED call (FR-3).

    ``call`` carries ``verb`` (schema verb string) and ``params`` (the
    resolved parameter mapping, in declared argument order where ordering
    matters to the caller's fixtures). Pure and deterministic.
    """
    verb, params = _call_fields(call)
    lowered_verb = verb.lower()

    noun_pair = _first_present(NOUN_KEYS, params)
    noun = _descriptor(noun_pair[1]) if noun_pair is not None else ""

    target_pair = _first_present(TARGET_KEYS, params)
    targets = []
    if target_pair is not None:
        raw = target_pair[1]
        items = list(raw) if isinstance(raw, (list, tuple)) else [raw]
        targets = [_descriptor(item) for item in items]

    def assemble(descriptor: str) -> str:
        obj = f"{noun}{_FIXED_CONNECTOR}{descriptor}" if noun else descriptor
        if len(targets) > 1:
            obj += _MULTI_TARGET_TEMPLATE.format(saved=len(targets) - 1)
        return f"{lowered_verb} {obj}"

    if not targets:
        # Nothing locatable to point at: the phrase degrades to the verb alone
        # (irreversible calls always carry a target, so this path is read-tier
        # only and never reaches a confirm field).
        return lowered_verb

    first = targets[0]
    phrase = assemble(first)
    if len(phrase) <= PHRASE_MAX_CHARS:
        return phrase
    fixed_suffix_len = len(phrase) - len(first)
    truncated = _truncate_words(first, PHRASE_MAX_CHARS - fixed_suffix_len)
    regenerated = assemble(truncated)
    assert len(regenerated) <= PHRASE_MAX_CHARS, (
        "regenerated phrase exceeded the cap -- truncation arithmetic regressed"
    )
    return regenerated


def normalize_phrase(value: Any) -> str:
    """FR-3 matching normalization, exhaustively: trim ends, collapse internal
    whitespace to single spaces, case-fold. NOTHING ELSE."""
    if not isinstance(value, str):
        return ""
    return " ".join(value.split()).casefold()


def phrase_matches(typed: Any, required: str) -> bool:
    """True iff the typed phrase matches the required one under FR-3's
    normalization -- and nothing looser."""
    if not isinstance(typed, str) or not isinstance(required, str):
        return False
    return normalize_phrase(typed) == normalize_phrase(required)
