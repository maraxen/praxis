"""§7 ParseSource: the parse-layer seam plus the fixture-backed stub.

The model itself (FunctionGemma load, Transformers.js worker, LoRA adapters)
is explicitly OUT of scope (spec §7) and lands under a separate spec. What W3
owns is the SEAM: the kernel and the card layer consume parsed calls through
this interface only, so the real implementation arrives as an additive
replacement with no call-site changes -- and the propose card is demoable and
testable with no model present.

``FixtureParseSource`` serves the golden fixtures in
``coxswain/tests/fixtures/parsed_calls/*.json`` -- the SAME corpus the FR-3
parity tests run, so parse stub, phrase derivation, and both language
implementations stay glued to one dataset (RISK-8's drift mitigation).

NFR-1/NFR-2: pure stdlib, CPython-importable, no ``js``, no ``praxis.*``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, Protocol, runtime_checkable

from coxswain.fft.context import ParsedCall

__all__ = ["FixtureParseSource", "ParseError", "ParseSource"]

#: Normalization for utterance lookup: trim ends + collapse internal
#: whitespace + case-fold. Deliberately identical in spirit to FR-3's phrase
#: matching normalization -- one rule for "did the user say this", not two.
_DEFAULT_FIXTURE_DIR: Final[Path] = (
    Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "parsed_calls"
)

_REQUIRED_FIELDS: Final[tuple[str, ...]] = ("utterance", "name", "verb", "receiver_type", "params")


class ParseError(ValueError):
    """Raised loudly when an utterance cannot be served. The stub never
    guesses, never falls back to a default call -- a silent wrong parse is
    precisely the failure a fixture-backed stand-in must not teach us."""


@runtime_checkable
class ParseSource(Protocol):
    """The §7 boundary. One method; the parse worker (separate spec) will
    implement this over Transformers.js, the kernel consumes it here."""

    def parse(self, utterance: str) -> ParsedCall: ...


def _normalize_utterance(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split()).casefold()


@dataclass(frozen=True)
class _Entry:
    name: str
    verb: str
    receiver_type: str
    params: dict[str, Any]
    missing_required: tuple[str, ...]
    unresolved_slots: tuple[tuple[str, str, str], ...]
    fixture_file: str


class FixtureParseSource:
    """Serve ParsedCalls from the golden fixture corpus. Deterministic,
    offline, dependency-free: the demo path and the expected majority of test
    usage per §7/RISK-8."""

    def __init__(self, fixture_dir: Path | None = None) -> None:
        self._fixture_dir = Path(fixture_dir) if fixture_dir is not None else _DEFAULT_FIXTURE_DIR
        self._by_utterance: dict[str, _Entry] = {}
        self._load()

    # --- loading ----------------------------------------------------------------

    def _load(self) -> None:
        if not self._fixture_dir.is_dir():
            raise FileNotFoundError(
                f"fixture dir {self._fixture_dir} does not exist -- FixtureParseSource "
                "refuses to start empty rather than silently parse nothing"
            )
        paths = sorted(self._fixture_dir.glob("*.json"))
        if not paths:
            raise FileNotFoundError(
                f"no *.json fixtures under {self._fixture_dir} -- refusing an "
                "empty corpus"
            )
        for path in paths:
            entry = json.loads(path.read_text())
            missing = [field for field in _REQUIRED_FIELDS if field not in entry]
            if missing:
                raise ValueError(f"{path.name}: fixture missing required field(s) {missing}")
            normalized = _normalize_utterance(entry["utterance"])
            if not normalized:
                raise ValueError(f"{path.name}: utterance is blank")
            if normalized in self._by_utterance:
                raise ValueError(
                    f"{path.name}: utterance collides with "
                    f"{self._by_utterance[normalized].fixture_file!r} after normalization"
                )
            slots = tuple(
                (slot["arg_name"], slot["reference"], slot["resource_type"])
                for slot in entry.get("unresolved_slots", [])
            )
            self._by_utterance[normalized] = _Entry(
                name=entry["name"],
                verb=entry["verb"],
                receiver_type=entry["receiver_type"],
                params=dict(entry["params"]),
                missing_required=tuple(entry.get("missing_required", ())),
                unresolved_slots=slots,
                fixture_file=path.name,
            )

    # --- ParseSource --------------------------------------------------------------

    @property
    def fixture_count(self) -> int:
        return len(self._by_utterance)

    def known_utterances(self) -> tuple[str, ...]:
        """The raw utterance strings, in fixture order. Used by error messages
        so a failed demo says what WOULD have worked."""
        return tuple(
            json.loads((self._fixture_dir / p.name).read_text())["utterance"]
            for p in sorted(self._fixture_dir.glob("*.json"))
        )

    def parse(self, utterance: str) -> ParsedCall:
        entry = self._by_utterance.get(_normalize_utterance(utterance))
        if entry is None:
            raise ParseError(
                f"no fixture parses {utterance!r}. Known utterances: "
                f"{list(self.known_utterances())}"
            )
        # Fresh ParsedCall per request with a copied params dict: the gate binds
        # auto-resolved slots via dataclasses.replace, never mutation, and this
        # stub must not hand two callers the same mutable mapping.
        return ParsedCall(
            name=entry.name,
            receiver_type=entry.receiver_type,
            params=dict(entry.params),
            missing_required=entry.missing_required,
            unresolved_slots=tuple(_unresolved_slot(*slot) for slot in entry.unresolved_slots),
        )


def _unresolved_slot(arg_name: str, reference: str, resource_type: str):
    from coxswain.fft.context import UnresolvedSlot

    return UnresolvedSlot(arg_name=arg_name, reference=reference, resource_type=resource_type)
