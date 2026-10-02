"""The operation glossary for ``praxis.display`` (task B4; spec section 3.5, AC-28).

One name per action, in every Praxis text. This module is the ONLY home of action strings: the
ledger, the error panels and the context resolver ask it for a name, a verb form or a role and never
spell one themselves (AC-28 scans every other ``praxis/display/*.py`` for a literal from this table).

Pure standard library. No PyLabRobot, no IPython, no ``js`` and no other Praxis module, so it imports
in plain CPython and before PLR is on the path.

``ACTIONS`` maps a PLR ``LiquidHandler`` method name to the name shown to the user:

=================  ============  ================
PLR method         name          verb form (fixes)
=================  ============  ================
``pick_up_tips``   Pick up tips  pick up tips
``drop_tips``      Drop tips     drop tips
``return_tips``    Return tips   return tips
``discard_tips``   Discard tips  discard tips
``aspirate``       Aspirate      aspirate
``dispense``       Dispense      dispense
``transfer``       Transfer      transfer
=================  ============  ================

and the six ``*96`` variants (``pick_up_tips96`` ... ``dispense96``) are the same name plus
``" (96 head)"``. The ``*96`` names are used by the ledger and by the 96-head error panels (#5659,
N5659-9): a panel names the op with the ``*96`` name ("Pick up tips (96 head) asked those channels ...")
and writes its fix sentences with the BASE verbs ("aspirate from wells that hold more") plus
``HEAD96_NOUN`` ("on the 96 head"). ``HEAD96_NOUN`` is the one place the words "96 head" are spelled,
``SUFFIX_96`` is derived from it, and it is not one of the section 3.5 ``NOUNS`` (it names the head, not
a thing in a sentence about wells). ``VERBS`` follows the name column for the 96 variants (base verb plus
the suffix): section 3.5 says only "the same".

Keys are the frame names D8's context resolver filters on and the methods ``RunLedger`` shadows, so
they must be real ``LiquidHandler`` method names (a test checks that against the pin).

**Roles.** ``role_of(op)`` says what an op does for the ledger's counts (a tip cycle starts at a
pick-up; liquid is moved by a dispense or a transfer) without the ledger comparing method names.

**Unknown ops** fall back safely: ``action_name`` and ``verb_form`` never raise and never return
markup-interpreting or unbounded text (escaping is the renderer's job, D2).
"""

from __future__ import annotations

from types import MappingProxyType

__all__ = [
    "ACTIONS", "VERBS", "NOUNS", "AVOID", "SUFFIX_96", "HEAD96_NOUN",
    "PICK_UP", "DROP", "ASPIRATE", "DISPENSE", "TRANSFER",
    "action_name", "verb_form", "role_of", "is_96", "plural",
]

HEAD96_NOUN = "96 head"
SUFFIX_96 = f" ({HEAD96_NOUN})"

# Roles (what an op does). Values are opaque tokens: compare with these constants.
PICK_UP = "pick_up"
DROP = "drop"
ASPIRATE = "aspirate"
DISPENSE = "dispense"
TRANSFER = "transfer"

# (PLR method, name in every Praxis text, verb form in fixes, role, has a 96-head variant)
_TABLE = (
    ("pick_up_tips", "Pick up tips", "pick up tips", PICK_UP, True),
    ("drop_tips", "Drop tips", "drop tips", DROP, True),
    ("return_tips", "Return tips", "return tips", DROP, True),
    ("discard_tips", "Discard tips", "discard tips", DROP, True),
    ("aspirate", "Aspirate", "aspirate", ASPIRATE, True),
    ("dispense", "Dispense", "dispense", DISPENSE, True),
    ("transfer", "Transfer", "transfer", TRANSFER, False),
)


def _build():
    actions, verbs, roles, ops96 = {}, {}, {}, set()
    for method, name, verb, role, has_96 in _TABLE:
        actions[method], verbs[method], roles[method] = name, verb, role
        if has_96:
            m96 = f"{method}96"
            actions[m96], verbs[m96], roles[m96] = f"{name}{SUFFIX_96}", f"{verb}{SUFFIX_96}", role
            ops96.add(m96)
    return (
        MappingProxyType(actions), MappingProxyType(verbs), MappingProxyType(roles),
        frozenset(ops96),
    )


ACTIONS, VERBS, _ROLES, _OPS_96 = _build()

# Section 3.5 "Nouns": channel (never "pip" or "pipette"), well, tip, tip rack and deck panel in every
# UI string. "Dock" is an internal name only.
NOUNS = ("channel", "well", "tip", "tip rack", "deck panel")
AVOID = MappingProxyType({"pip": "channel", "pipette": "channel", "dock": "deck panel"})

_NAME_MAX = 80
_UNKNOWN = "unknown action"


def _humanise(op) -> str:
    """A bounded, single-line, readable form of an unknown op name; ``""`` when nothing usable is
    left (so the caller falls back to "unknown action")."""
    if not isinstance(op, str):
        return ""
    text = " ".join(op.replace("_", " ").split())
    text = "".join(ch for ch in text if ch.isprintable())
    if not any(ch.isalnum() for ch in text):
        return ""
    if len(text) > _NAME_MAX:
        text = text[: _NAME_MAX - 1].rstrip() + "…"
    return text


def action_name(op) -> str:
    """The name of *op* in every Praxis text. A known method gives its table name; anything else
    gives a readable sentence-case form of the text, or "Unknown action". Never raises."""
    if isinstance(op, str) and op in ACTIONS:
        return ACTIONS[op]
    text = _humanise(op)
    return text.capitalize() if text else _UNKNOWN.capitalize()


def verb_form(op) -> str:
    """The verb form of *op* for fix sentences ("Pick up tips before you {verb}"). Never raises."""
    if isinstance(op, str) and op in VERBS:
        return VERBS[op]
    return _humanise(op) or _UNKNOWN


def role_of(op):
    """What *op* does for the ledger: ``PICK_UP``, ``DROP``, ``ASPIRATE``, ``DISPENSE`` or
    ``TRANSFER``; ``None`` for anything that is not a glossary action."""
    return _ROLES.get(op) if isinstance(op, str) else None


def is_96(op) -> bool:
    """True for the six 96-head variants; False for everything else, unknown names included."""
    return isinstance(op, str) and op in _OPS_96


def plural(n, noun) -> str:
    """``"8 channels"``, ``"1 tip rack"``: a count with a thousands separator and the noun in the
    plural unless the count is exactly one."""
    return f"{n:,} {noun}" if n == 1 else f"{n:,} {noun}s"
