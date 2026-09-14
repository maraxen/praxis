"""N1-B advisory parameter warnings.

Warnings are BADGES on the propose card and nothing else: they NEVER change a
risk tier and NEVER change which friction path applies (FR-2). This module is
deliberately unreachable from the tier path (``plr/tool_schema.py`` must not
import it -- enforced by test_tier_static).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

from coxswain.records import STRING_CAPS, truncate_to_cap

__all__ = [
    "LARGE_VOLUME_THRESHOLD_UL",
    "MULTI_TARGET_MIN",
    "WarningBadge",
    "compute_warnings",
]

#: Advisory threshold above which a volume earns the large_volume badge.
#: Chosen near the practical single-channel working maximum; advisory only --
#: it can never influence a tier (that would be N1-B regression).
LARGE_VOLUME_THRESHOLD_UL: Final[float] = 900.0

#: A list-valued destination longer than this earns multi_plate.
MULTI_TARGET_MIN: Final[int] = 2

_VOLUME_KEYS: Final[tuple[str, ...]] = ("vol", "volume")
_MULTI_TARGET_KEYS: Final[tuple[str, ...]] = ("targets", "destinations")


@dataclass(frozen=True)
class WarningBadge:
    """One advisory badge. ``message`` is capped at NFR-7's warning_badge_text
    cap kernel-side before persistence or render."""

    kind: str
    message: str


def _badge(kind: str, message: str) -> WarningBadge:
    return WarningBadge(kind=kind, message=truncate_to_cap(message, STRING_CAPS["warning_badge_text"]))


def compute_warnings(call_name: str, params: dict[str, Any]) -> tuple[WarningBadge, ...]:
    """Pure, advisory-only computation over resolved parameters.

    Deterministic in ``(call_name, params)``; emits nothing for well-behaved
    inputs. Never raises on unexpected param shapes -- a badge computation
    that could fail execution would be a safety bug."""
    badges: list[WarningBadge] = []

    for key in _VOLUME_KEYS:
        value = params.get(key)
        if isinstance(value, int | float) and value > LARGE_VOLUME_THRESHOLD_UL:
            badges.append(
                _badge(
                    "large_volume",
                    f"{key}={value:.0f} uL exceeds {LARGE_VOLUME_THRESHOLD_UL:.0f} uL",
                )
            )
            break

    for key in _MULTI_TARGET_KEYS:
        value = params.get(key)
        if isinstance(value, list | tuple) and len(value) >= MULTI_TARGET_MIN:
            badges.append(_badge("multi_plate", f"{len(value)} destinations selected"))
            break

    return tuple(badges)
