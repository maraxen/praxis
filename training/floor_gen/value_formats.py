"""Pinned value-format conventions (juror finding b: unpinned value formats).

Every structured call the synthesizer emits obeys THESE formats, the prompt
text states them to the teacher, and the manifest records them verbatim so a
corpus consumer never has to guess:

- volumes: floats in microliters (uL), e.g. ``50.0``; always JSON numbers,
  never strings, never integers-without-decimal-point at the type level.
- well references: ``"A1"``-style UPPERCASE ``<row letter A-H><column 1-12>``.
- deck resource names: lowercase snake_case stable ids (``plate_1``,
  ``tip_rack_2_A4``, ``reservoir_1``) that grounding can resolve against live
  kernel objects.
- vague (ambiguous) references: short natural noun phrases (``the plate``),
  used ONLY in ambiguous-referent cells so D11 derives an unresolved slot.
"""

from __future__ import annotations

import re
from typing import Final

__all__ = [
    "VAGUE_REF_POOLS",
    "VALUE_FORMAT_CONVENTIONS",
    "WELL_RE",
    "canonical_volume",
    "canonical_well",
]

#: 96-well plate positions: row letter A-H, column 1-12, uppercase, no padding.
WELL_RE: Final[re.Pattern[str]] = re.compile(r"^([A-H])(10|11|12|[1-9])$")

_VAGUE_REFS_RAW: Final[dict[str, tuple[str, ...]]] = {
    "container": ("the same well", "the source well", "the destination well"),
    "plate": ("the plate",),
    "lid": ("the lid",),
    "resource": ("the reservoir", "the carrier"),
    "tip_spot": ("the tip rack",),
}

#: Vague natural-language references per grounding resource type. Exported as
#: plain dict for prompt text + manifest recording.
VAGUE_REF_POOLS: Final[dict[str, tuple[str, ...]]] = {
    k: tuple(v) for k, v in _VAGUE_REFS_RAW.items()
}


def canonical_well(ref: str) -> str:
    """Validate + return a well reference in pinned ``A1`` style. Loud on junk."""
    if not isinstance(ref, str):
        raise ValueError(f"well reference must be str, got {type(ref)!r}")
    stripped = ref.strip().upper()
    if not WELL_RE.match(stripped):
        raise ValueError(f"{ref!r} is not an A1-style 96-well position")
    return stripped


def canonical_volume(value: float) -> float:
    """Validate + return a volume as a positive finite float (uL)."""
    out = float(value)
    if out != out or out in (float("inf"), float("-inf")):
        raise ValueError(f"volume must be finite, got {value!r}")
    if out <= 0:
        raise ValueError(f"volume must be positive, got {value!r}")
    return out


#: The recorded conventions block, embedded into manifests verbatim.
VALUE_FORMAT_CONVENTIONS: Final[dict[str, object]] = {
    "volumes": {
        "unit": "uL",
        "json_type": "float",
        "rule": "positive finite floats; spoken/written as 'microliters' in utterances",
        "example": 50.0,
    },
    "well_references": {
        "style": "uppercase <row A-H><col 1-12>, e.g. A1 / B12",
        "regex": WELL_RE.pattern,
        "example": "B3",
    },
    "deck_resource_names": {
        "style": "lowercase snake_case stable ids resolvable by grounding",
        "examples": ["plate_1_A3", "tip_rack_2_A4", "reservoir_1"],
    },
    "ambiguous_references": {
        "style": "short vague noun phrases; only in ambiguous-referent cells",
        "examples": list(VAGUE_REF_POOLS["plate"]) + list(VAGUE_REF_POOLS["container"]),
    },
}
