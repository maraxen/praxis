"""The error panel and the exception handler for ``praxis.display`` (task B6; spec D8, D2, D4, D9,
section 3.3, AC-16, AC-13's error-panel case, AC-28).

For the four PyLabRobot errors (``TooLittleLiquidError``, ``TooLittleVolumeError``, ``HasTipError``,
``NoTipError``) the cell shows a panel that says WHICH resource, channel or tip the fault is about and by
how much, instead of PLR's bare message, and still ends in an ``error`` output so the rail shows brick and
Run All stops. Everything else gets IPython's normal traceback, untouched.

**Carrier: the S3-C fallback** (spike S3, run a3458bf2: ``set_custom_exc`` runs its handler and its
``display()`` emits, but the returned traceback does not become the cell's error output and Run All does
not stop). ``install(shell)`` therefore wraps the shell INSTANCE's ``showtraceback`` (an instance
attribute: the IPython and PLR classes are untouched). For one of the four classes the wrapper displays the
panel and then finishes through ``shell._showtraceback(etype, evalue, ["<Name>: <message>"])``, which in
the Pyodide kernel sets ``Interpreter._last_traceback`` (the kernel derives the cell's status from it). The
same wrapper serves a plain cell and a top-level-``await`` cell (both reach ``run_code`` and so
``self.showtraceback``). Any other exception is delegated, arguments unchanged, to the original.
``install`` is idempotent and returns a handle whose ``uninstall()`` restores the shell.

**The panel** (section 3.3): a brick status rail (Praxis CSS on ``.praxis-error``), inside a ``RunLedger``
the line "Step {n} of the run." (``ledger.step_for``, which removes the entry), a heading that states the
fault and names the resource and wells, one body sentence with the COMMITTED numbers (``context.resolve``
sums demand per resource; PLR's own message mixes in pending state), a fix sentence, a drawing of the
labware at committed volume with the offending wells marked in brick by a ring AND a cross (a Well or tip
spot owner only), "PyLabRobot raised ``<Name>: <message>``" verbatim, and the traceback in
``<details>``, ANSI stripped, escaped, tail-capped (D4). "Nothing was aspirated/dispensed" is stated
because a tracker refusal is raised before the backend is called (LH:1269-1274, :1470-1475; the test
spies the backend).

**The 96 head** (#5659; ``261001_nd-next-5659-96head-errors.md`` N5659-6): a context with ``head96`` set
gets its own rows. The row is chosen by ``ctx.container_mode`` and the owner kind, never by whether a well's
parent is a Plate (a one-item Plate is single-container mode). A plate row marks the offending wells, a
tip or channel row states counts and spans and draws nothing, a rack row draws the rack at its COMMITTED
tips (``_drawn_tip``; every error panel that draws a rack does, 1-channel included, N5659-8). A 96 op is
named with the glossary's ``*96`` name ("Pick up tips (96 head)") and fixes use the base verbs; the words
"96 head" come from ``glossary.HEAD96_NOUN``.

**The residue sentence** (#5659 task 8; N5659-11, decision sheet Q4): PLR queues the 96 ops' tracker changes
before its ``try``, so a refusal leaves PENDING changes behind and the next success saves them. When
``ctx.residue`` (found by ``residue.py``, the only module that reads pending state) is non-empty, every 96 ROW
(never the generic panel) adds, after the fix, one sentence naming the wells, tips, channels and rack spots
involved, plus "The drawing shows what was actually done." only where the panel has a drawing. It is a
``div.praxis-summary``, a sibling of the body and fix paragraphs, so the body and the fix stay the only two
``p.praxis-summary``; in ``text/plain`` it is one line between the fix and PLR's line. The 1-channel rows have
no residue layer. The panel reads no pending state itself.

**The generic panel** (no heading template) is "PyLabRobot raised X: message" plus the traceback. It is
shown for every ``None`` from ``resolve`` (no owner, pending residue, a mixed 1-channel / ``*96`` stack, a
NoTip on a 96 op) and for a context no template row covers (no op frame, a trough that overflows on a
dispense, a single container that overflows on a 96 dispense). A resolver that raises degrades to it, and
the handler never raises.

**Stamp** (D2): ``kind`` ``error``, ``rev`` null, ``resource`` the drawn labware (the plate, the trough, the
tip rack) or null for a channel or tip owner and for the generic panel.

**Classes.** Only classes A4's theme has a rule for are emitted (the CSS gate refuses the rest): the
root ``praxis-out praxis-error``, ``praxis-error__title`` (the heading), ``praxis-summary`` (the body, then
the fix, then a 96 row's residue sentence), ``praxis-omitted`` (the step line and the omission sentence), ``praxis-error__plr`` (PLR's line)
and ``svg.details_html``'s ``praxis-details*`` (styled through ``.praxis-error details``).

**Byte cap** (D4): the drawing degrades first (level 1 a block, level 2 omitted with the omission
sentence), never the text; if the escaped text alone is over 64 KiB the traceback shrinks until it fits.
The bundle is validated with ``svg.check_bundle``.

**Action names** come from ``glossary`` only (AC-28): no action string is spelled here. The one fix
sentence that starts with a verb ("Pick up tips before you ...") asks the glossary for it, and the roles
(``PICK_UP`` ...) pick the op.

Plain CPython: no PLR, IPython or ``js`` import at import time. The four classes are resolved inside
``handled_classes`` from ``pylabrobot.resources.errors``, and the default ``display`` is resolved from
``IPython.display`` when a panel is first shown.
"""

from __future__ import annotations

import dataclasses
import functools
import logging
import re
import sys
import traceback

from . import budget, context, glossary, labware, ledger, residue, svg

__all__ = ["handled_classes", "render", "handle", "install", "Installed"]

log = logging.getLogger("praxis.display")

_MESSAGE_MAX = 2048  # chars of PLR's message shown in the verbatim line (an ordinary one is one short line)
_TB_LIMITS = (budget.TRACEBACK_CAP_BYTES, 8192, 4096, 2048, 1024, 256)  # the cap, then what a fit may shrink to
_DEFAULT_SESSION = "unset"
_MARK = "_praxis_errors_install"

# CSI and OSC sequences, then any stray ESC: the traceback and the verbatim line carry no ANSI (D2).
_ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b")


# --------------------------------------------------------------------------- the four classes


@functools.cache
def handled_classes():
    """The four PLR error classes this module makes a panel for, from their non-shim home. Resolved
    when first needed (never at import time); raises ``ImportError`` if PLR is not importable."""
    from pylabrobot.resources.errors import (  # noqa: PLC0415 -- lazy by design (plain-CPython import)
        HasTipError,
        NoTipError,
        TooLittleLiquidError,
        TooLittleVolumeError,
    )

    return (TooLittleLiquidError, TooLittleVolumeError, HasTipError, NoTipError)


def _is_handled(exc) -> bool:
    try:
        return isinstance(exc, handled_classes())
    except Exception:  # noqa: BLE001 -- no PLR (or a hostile __class__): not ours, delegate
        return False


# --------------------------------------------------------------------------- small helpers


def _read(value):
    """A value, or the result of calling a zero-argument provider (read at render time)."""
    try:
        return value() if callable(value) else value
    except Exception:  # noqa: BLE001 -- a broken provider must never break an error display
        log.debug("errors: provider failed", exc_info=True)
        return None


def _session_id(value) -> str:
    value = _read(value)
    return value if isinstance(value, str) and value else _DEFAULT_SESSION


def _exec_number(value):
    value = _read(value)
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _plain(text: str) -> str:
    return _ANSI.sub("", text)


def _str(x) -> str:
    try:
        return str(x)
    except Exception:  # noqa: BLE001 -- a hostile __str__ must not cost the panel
        return "<could not be printed>"


def _message(exc) -> str:
    """PLR's message for the verbatim line: ANSI stripped and bounded (an ordinary one is untouched)."""
    text = _plain(_str(exc))
    return text if len(text) <= _MESSAGE_MAX else text[: _MESSAGE_MAX - 1] + "…"


def _sentence_of(exc) -> str:
    return f"PyLabRobot raised {type(exc).__name__}: {_message(exc)}"


def _disp(name) -> str:
    """A name as DISPLAYED, shortened as labware does, so the text always fits the cap."""
    s = str(name)
    limit = labware.NAME_DISPLAY_MAX
    return s if len(s) <= limit else s[: limit - 1] + "…"


def _amount(x) -> str:
    return svg.fmt_amount(x)


def _span(values) -> str:
    """One number when every value reads the same, else ``lo–hi`` (section 3.3's ``{min}–{max}``)."""
    lo, hi = _amount(min(values)), _amount(max(values))
    return lo if lo == hi else f"{lo}–{hi}"


def _base_op(role):
    """The un-suffixed glossary op that has ``role`` (the one the fix sentences name)."""
    return next(op for op in glossary.ACTIONS if glossary.role_of(op) == role and not glossary.is_96(op))


def _name(role) -> str:
    return glossary.action_name(_base_op(role))


def _verb(role) -> str:
    return glossary.verb_form(_base_op(role))


def _past(role) -> str:
    """"aspirated" / "dispensed": the verb form of the op with its past-tense ending."""
    return f"{_verb(role)}d"


def _drawn_volume(container):
    """The volume the panel draws: COMMITTED (``VolumeTracker.volume``), never pending (D8 "Panel
    drawing"; ``get_used_volume`` includes pending state)."""
    return container.tracker.volume


def _drawn_tip(spot):
    """The tip the panel draws a rack spot with: the COMMITTED tip of the spot's tracker, ``None`` when it
    holds none (``Tip`` presence in the resource tree includes pending operations, N5659-8). Defined next
    to ``_drawn_volume``, which reads committed state for the same reason."""
    from pylabrobot.legacy.tip_tracker import tip_spot_tracker  # noqa: PLC0415 -- lazy by design
    from pylabrobot.resources.errors import NoTipError  # noqa: PLC0415

    try:
        return tip_spot_tracker(spot).get_tip()
    except NoTipError:
        return None


def _kind(resource):
    try:
        return labware.kind_of(resource)
    except TypeError:
        return None


def _in_plate(container) -> bool:
    parent = getattr(container, "parent", None)
    return parent is not None and _kind(parent) == "plate"


# --------------------------------------------------------------------------- templates (section 3.3)


@dataclasses.dataclass(frozen=True)
class _Panel:
    heading: str
    body: str
    fix: str
    resource: str | None  # the stamp's ``resource``: the drawn labware, else None
    figure: tuple | None  # (labware, fault ids) for a drawing
    residue: str = ""  # a 96 row's residue sentence without its drawing clause; "" when there is none


def _volume_panel(exc, ctx):
    """TooLittleLiquid / TooLittleVolume: a well of a plate, another container, or a mounted tip."""
    lack = isinstance(exc, handled_classes()[0])  # (TLL, TLV, HasTip, NoTip)
    role = glossary.role_of(ctx.op)
    verb, past = _verb(role), _past(role)
    if ctx.owner_kind == context.OWNER_TIP:
        if role != (glossary.DISPENSE if lack else glossary.ASPIRATE) or ctx.channel is None:
            return None
        avail, req = _amount(ctx.available), _amount(ctx.requested)
        if lack:
            return _Panel(
                f"The tip on channel {ctx.channel} holds only {avail} µL.",
                f"The {verb} asked for {req} µL. Nothing was {past}.",
                f"{glossary.action_name(ctx.op)} {avail} µL or less, or {_verb(glossary.ASPIRATE)} more first.",
                None, None,
            )
        return _Panel(
            f"The tip on channel {ctx.channel} can't hold {req} µL.",
            f"It has room for {avail} µL. Nothing was {past}.",
            f"{_name(glossary.ASPIRATE)} less, or use larger tips.",
            None, None,
        )
    if ctx.owner_kind != context.OWNER_CONTAINER or role != (glossary.ASPIRATE if lack else glossary.DISPENSE):
        return None
    owner = ctx.owner
    if _in_plate(owner):
        plate = owner.parent
        offenders = [o for o in ctx.offending if _in_plate(o.target) and o.target.parent is plate]
        ids = sorted({o.target.get_identifier() for o in offenders})
        wells = labware.compress_wells(ids)
        avails, reqs = [o.available for o in offenders], [o.requested for o in offenders]
        same = _amount(min(avails)) == _amount(max(avails))
        if lack:
            lead = f"Each well holds {_span(avails)} µL" if same else f"{wells} hold {_span(avails)} µL"
            heading, fix = (
                f"Not enough liquid in {_disp(plate.name)} {wells}.",
                f"Lower `vols` to {_amount(min(avails))} µL or less, or {verb} from wells that hold more.",
            )
        else:
            lead = f"Each well has room for {_span(avails)} µL" if same else f"{wells} have room for {_span(avails)} µL"
            heading, fix = (
                f"Not enough room in {_disp(plate.name)} {wells}.",
                f"Lower `vols`, or {verb} into emptier wells.",
            )
        return _Panel(heading, f"{lead}; the {verb} asked for {_span(reqs)} µL. Nothing was {past}.", fix,
                      plate.name, (plate, frozenset(ids)))
    if not _single_container_has_row(lack):
        return None  # no template row: a container that is not a well of a plate overflowing on a dispense
    channels = sum(1 for r in ctx.resources if r is owner)
    if not channels:
        return None
    return _Panel(
        f"Not enough liquid in {_disp(owner.name)}.",
        f"It holds {_amount(ctx.available)} µL; the {verb} asked for {_amount(ctx.requested)} µL "
        f"across {glossary.plural(channels, 'channel')}. Nothing was {past}.",
        f"Lower `vols`, or {verb} from a container that holds more.",
        owner.name, None,
    )


def _single_container_has_row(lack) -> bool:
    """Is there a template row for a container that is not a well of a plate? Only for a lack of liquid:
    the same container overflowing on a dispense has none (section 3.3), on either path."""
    return lack


def _row_kind(ctx):
    """Which 96 volume row a context calls for: ``"plate"`` (96 wells of one plate, one per channel),
    ``"single"`` (one container for the whole head) or ``None``. By the recorded container mode, never by
    the owner's parent: the only well of a one-item Plate has a Plate as its parent and is still ``single``."""
    return {"per_channel": "plate", "single": "single"}.get(ctx.container_mode)


def _volume_panel96(exc, ctx):
    """TooLittleLiquid / TooLittleVolume on the 96 head: wells of a plate (one per channel), one container,
    or the mounted tips."""
    lack = isinstance(exc, handled_classes()[0])  # (TLL, TLV, HasTip, NoTip)
    role = glossary.role_of(ctx.op)
    verb, past = _verb(role), _past(role)
    if ctx.owner_kind == context.OWNER_TIP:
        if role != (glossary.DISPENSE if lack else glossary.ASPIRATE) or not ctx.offending:
            return None
        avails, asked = [o.available for o in ctx.offending], _amount(ctx.offending[0].requested)
        tips = glossary.plural(len(ctx.offending), "tip")
        if lack:
            return _Panel(
                f"Not enough liquid in {tips} on the {glossary.HEAD96_NOUN}.",
                f"Each holds {_span(avails)} µL; the {verb} asked for {asked} µL on every channel. "
                f"Nothing was {past}.",
                f"{_name(glossary.DISPENSE)} {_amount(min(avails))} µL or less, or "
                f"{_verb(glossary.ASPIRATE)} more first.",
                None, None,
            )
        return _Panel(
            f"Not enough room in {tips} on the {glossary.HEAD96_NOUN}.",
            f"Each has room for {_span(avails)} µL; the {verb} asked for {asked} µL on every channel. "
            f"Nothing was {past}.",
            f"{_name(glossary.ASPIRATE)} less, or use larger tips.",
            None, None,
        )
    if ctx.owner_kind != context.OWNER_CONTAINER or role != (glossary.ASPIRATE if lack else glossary.DISPENSE):
        return None
    owner, kind = ctx.owner, _row_kind(ctx)
    if kind == "plate":
        plate = getattr(owner, "parent", None)
        if plate is None or _kind(plate) != "plate":
            return None
        offenders = [o for o in ctx.offending if getattr(o.target, "parent", None) is plate]
        if not offenders:
            return None
        ids = sorted({o.target.get_identifier() for o in offenders})
        wells = labware.compress_wells(ids)
        avails, reqs = [o.available for o in offenders], [o.requested for o in offenders]
        same = _amount(min(avails)) == _amount(max(avails))
        shared = len({id(r) for r in ctx.resources}) != len(ctx.resources)  # a well under more than one channel
        if lack:
            lead = f"Each well holds {_span(avails)} µL" if same else f"{wells} hold {_span(avails)} µL"
            heading = f"Not enough liquid in {_disp(plate.name)} {wells}."
            fix = f"Lower `volume` to {_amount(min(avails))} µL or less, or {verb} from wells that hold more."
        else:
            lead = f"Each well has room for {_span(avails)} µL" if same else f"{wells} have room for {_span(avails)} µL"
            heading = f"Not enough room in {_disp(plate.name)} {wells}."
            fix = f"Lower `volume`, or {verb} into emptier wells."
        ask = (
            f"{_span(reqs)} µL per well, summed over the channels that share it" if shared
            else f"{_amount(ctx.volumes[0])} µL on every channel"
        )
        return _Panel(heading, f"{lead}; the {verb} asked for {ask}. Nothing was {past}.", fix,
                      plate.name, (plate, frozenset(ids)))
    if kind == "single":
        if not _single_container_has_row(lack):
            return None
        parent = getattr(owner, "parent", None)
        only_well = parent is not None and _kind(parent) == "plate" and parent.num_items == 1
        name = parent.name if only_well else owner.name  # the Plate's name when the container is its only well
        return _Panel(
            f"Not enough liquid in {_disp(name)}.",
            f"It holds {_amount(ctx.available)} µL; the {verb} asked for {_amount(ctx.requested)} µL "
            f"across {glossary.plural(len(ctx.channels), 'channel')}. Nothing was {past}.",
            f"Lower `volume`, or {verb} from a container that holds more.",
            name, None,
        )
    return None


def _tip_panel96(exc, ctx):
    """HasTip on the 96 head: channels that already hold a tip, or rack spots that already have one. NoTip
    has no 96 row (committed state cannot explain it): the generic panel."""
    if not isinstance(exc, handled_classes()[2]):
        return None
    role = glossary.role_of(ctx.op)
    action = glossary.action_name(ctx.action)
    if ctx.owner_kind == context.OWNER_CHANNEL:
        if role != glossary.PICK_UP or not ctx.offending:
            return None
        return _Panel(
            f"The {glossary.HEAD96_NOUN} already holds a tip on {glossary.plural(len(ctx.offending), 'channel')}.",
            f"{action} asked those channels for another.",
            "Drop or discard the tips first.", None, None,
        )
    if ctx.owner_kind == context.OWNER_TIP_SPOT:
        if role != glossary.DROP:
            return None
        rack = getattr(ctx.owner, "parent", None)
        if rack is None or _kind(rack) != "tiprack":
            return None
        ids = sorted({o.target.get_identifier() for o in ctx.offending if getattr(o.target, "parent", None) is rack})
        if not ids:
            return None
        where = f"{_disp(rack.name)} {labware.compress_wells(ids)}"
        heading = f"{where} already has a tip." if len(ids) == 1 else f"{where} already have tips."
        return _Panel(heading, f"{action} asked to put tips there.", "Drop the tips into empty positions.",
                      rack.name, (rack, frozenset(ids)))
    return None


def _tip_panel(exc, ctx):
    """HasTip / NoTip: a channel, or a tip spot of a tip rack."""
    has_tip = isinstance(exc, handled_classes()[2])
    role = glossary.role_of(ctx.op)
    if ctx.owner_kind == context.OWNER_CHANNEL and ctx.channel is not None:
        c = ctx.channel
        if has_tip:
            if role != glossary.PICK_UP:
                return None
            return _Panel(f"Channel {c} already holds a tip.", f"Pick up asked channel {c} for another.",
                          "Drop or discard the tip first.", None, None)
        if role is None or role == glossary.PICK_UP:
            return None
        return _Panel(
            f"Channel {c} has no tip.",
            f"{glossary.action_name(ctx.action)} needs a tip on every channel it uses.",
            f"{_name(glossary.PICK_UP)} before you {glossary.verb_form(ctx.action)}.",
            None, None,
        )
    if ctx.owner_kind == context.OWNER_TIP_SPOT:
        if role != (glossary.DROP if has_tip else glossary.PICK_UP):
            return None
        spot = ctx.owner
        rack = getattr(spot, "parent", None)
        if rack is None or _kind(rack) != "tiprack":
            return None
        ids = frozenset(o.target.get_identifier() for o in ctx.offending if getattr(o.target, "parent", None) is rack)
        where = f"{_disp(rack.name)} {spot.get_identifier()}"
        if has_tip:
            return _Panel(f"{where} already has a tip.",
                          f"{glossary.action_name(ctx.action)} asked to put a tip there.",
                          "Drop the tip into an empty position.", rack.name, (rack, ids))
        return _Panel(f"{where} has no tip.", "Pick up asked for a tip that has already been taken.",
                      "Pick up from a position that still has a tip.", rack.name, (rack, ids))
    return None


# --------------------------------------------------------------------------- the residue sentence (N5659-11)

# The user's wording (decision sheet Q4, accepted 261001); the tests pin it.
_RESIDUE_SENTENCE = (
    "PyLabRobot still records moves that did not happen on {x}; the next step that succeeds will save "
    "them, and the tracked state will be wrong from then on."
)
_RESIDUE_DRAWING = " The drawing shows what was actually done."


def _join(parts) -> str:
    """``"a"``, ``"a and b"``, ``"a, b and c"``."""
    return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]


def _residue_places(items) -> list:
    """What the residue is on, as words, in the order plate wells, other containers, tips, channels, rack
    spots. Wells and spots are named like the headings do (``compress_wells``, at most 96 ids); the only
    well of a one-well Plate is that Plate's name."""
    wells, names, spots = {}, [], {}
    tips = channels = 0
    for item in items:
        target = item.target
        if item.kind == residue.KIND_CONTAINER:
            parent = getattr(target, "parent", None)
            if parent is not None and _kind(parent) == "plate" and parent.num_items > 1:
                wells.setdefault(id(parent), (parent, []))[1].append(target.get_identifier())
            elif parent is not None and _kind(parent) == "plate":
                names.append(_disp(parent.name))
            else:
                names.append(_disp(target.name))
        elif item.kind == residue.KIND_TIP:
            tips += 1
        elif item.kind == residue.KIND_CHANNEL:
            channels += 1
        elif item.kind == residue.KIND_SPOT:
            rack = getattr(target, "parent", None)
            if rack is None:
                names.append(_disp(target.name))
            else:
                spots.setdefault(id(rack), (rack, []))[1].append(target.get_identifier())
    parts = [f"{_disp(plate.name)} {labware.compress_wells(ids)}" for plate, ids in wells.values()]
    parts += names
    if tips:
        parts.append(f"{glossary.plural(tips, 'tip')} on the {glossary.HEAD96_NOUN}")
    if channels:
        parts.append(f"{glossary.plural(channels, 'channel')} of the {glossary.HEAD96_NOUN}")
    parts += [f"{_disp(rack.name)} {labware.compress_wells(ids)}" for rack, ids in spots.values()]
    return parts


def _residue_text(ctx) -> str:
    """The residue sentence for a context, without its drawing clause; ``""`` when it carries no residue."""
    if not ctx.residue:
        return ""
    parts = _residue_places(ctx.residue)
    return _RESIDUE_SENTENCE.format(x=_join(parts)) if parts else ""


def _drawing_clause(drawn: bool) -> str:
    """The clause that points at the drawing, only where there is one."""
    return _RESIDUE_DRAWING if drawn else ""


def _with_residue(panel, ctx):
    """``panel`` with its context's residue sentence. A sentence that cannot be built costs the sentence,
    never the row (it is logged)."""
    if panel is None:
        return None
    try:
        text = _residue_text(ctx)
    except Exception:  # noqa: BLE001 -- the row stays; the hazard note is what degrades
        log.warning("errors: could not build the residue sentence", exc_info=True)
        return panel
    return dataclasses.replace(panel, residue=text) if text else panel


def _panel_for(exc, ctx):
    """The template row for a context, or ``None`` (the generic panel). A context with no op frame (rule
    (d), a tracker used outside a liquid handler) has no op to name, so it is generic too. A 96 row also
    carries its context's residue sentence (the generic panel never does)."""
    if ctx.op is None or ctx.action is None or glossary.role_of(ctx.op) is None:
        return None
    classes = handled_classes()
    if ctx.head96:
        panel = _volume_panel96(exc, ctx) if isinstance(exc, (classes[0], classes[1])) else _tip_panel96(exc, ctx)
        return _with_residue(panel, ctx)
    if isinstance(exc, (classes[0], classes[1])):
        return _volume_panel(exc, ctx)
    return _tip_panel(exc, ctx)


# --------------------------------------------------------------------------- html


def _cap_traceback(text: str, limit: int) -> str:
    if limit > 0:
        try:
            return budget.cap_tail(text, limit)
        except ValueError:
            pass
    return budget.TAIL_MARKER_FORMAT.format(n=text.count("\n") + 1)  # the marker alone: no room for text


def _traceback_text(exc, tb) -> str:
    try:
        text = "".join(traceback.format_exception(type(exc), exc, tb))
    except Exception:  # noqa: BLE001 -- a hostile exception must not cost the panel
        text = f"{type(exc).__name__}: {_str(exc)}\n"
    return _plain(text)


def _figure_html(panel, level) -> str:
    if panel is None or panel.figure is None:
        return ""
    if level >= budget.LEVEL_OMITTED:
        return svg.text_line("p", "praxis-omitted", budget.OMISSION_SENTENCE)
    resource, ids = panel.figure
    try:
        return labware.render_figure(
            resource, level=level, volume_of=lambda c: _drawn_volume(c), fault=set(ids), tip_of=_drawn_tip
        )
    except Exception:  # noqa: BLE001 -- the drawing is the first thing to go, never the text
        log.warning("errors: could not draw %r", getattr(resource, "name", resource), exc_info=True)
        return ""


def _html(exc, panel, step, tb_text, level, tb_limit) -> str:
    plr = "PyLabRobot raised " + svg.el("code", svg.esc_text(f"{type(exc).__name__}: {_message(exc)}"))
    parts = []
    if step is not None:
        parts.append(svg.text_line("p", "praxis-omitted", f"Step {step} of the run."))
    if panel is None:  # the generic panel: PLR's sentence IS the heading
        parts.append(svg.el("p", plr, cls="praxis-error__title"))
    else:
        figure = _figure_html(panel, level)
        parts += [
            svg.text_line("p", "praxis-error__title", panel.heading),
            svg.text_line("p", "praxis-summary", panel.body),
            svg.text_line("p", "praxis-summary", panel.fix),
        ]
        if panel.residue:  # the drawing clause only if a drawing is really on the page at this level
            drawn = panel.figure is not None and level < budget.LEVEL_OMITTED and bool(figure)
            parts.append(svg.text_line("div", "praxis-summary", panel.residue + _drawing_clause(drawn)))
        parts.append(figure)
        parts.append(svg.el("p", plr, cls="praxis-error__plr"))
    parts.append(svg.details_html("Show traceback", _cap_traceback(tb_text, tb_limit)))
    return svg.el("div", "".join(parts), cls="praxis-out praxis-error")


def _fit(exc, panel, step, tb_text):
    """The html within the 64 KiB cap: the drawing degrades first (D4), and only if the escaped text
    alone is over does the traceback shrink."""
    levels = budget.LEVELS if panel is not None and panel.figure is not None else (budget.LEVEL_FULL,)
    for limit in _TB_LIMITS:
        try:
            doc, _level = budget.enforce(lambda lv, limit=limit: _html(exc, panel, step, tb_text, lv, limit), levels)
        except budget.BudgetExceeded:
            continue
        return doc
    return _html(exc, panel, step, tb_text, budget.LEVEL_OMITTED, 0)  # last resort: the marker alone


# --------------------------------------------------------------------------- render


def _resolve(exc, tb, resolver, decks):
    """The context, or ``None`` when there is none or the resolver misbehaves (never raises)."""
    try:
        ctx = (resolver or context.resolve)(exc, tb, decks=decks)
    except Exception:  # noqa: BLE001 -- a resolver that throws degrades to the generic panel
        log.warning("errors: resolver raised; showing the generic panel", exc_info=True)
        return None
    return ctx if isinstance(ctx, context.ErrorContext) else None


def _plain_text(exc, panel, step) -> str:
    lines = [] if step is None else [f"Step {step} of the run."]
    if panel is not None:
        lines += [panel.heading, panel.body, panel.fix]
        if panel.residue:  # text/plain has no drawing of its own: the clause follows the panel's
            lines.append(panel.residue + _drawing_clause(panel.figure is not None))
    lines.append(_sentence_of(exc))
    return "\n".join(lines)


def render(exc, tb=None, *, session=None, exec_count=None, step=None, resolver=None, decks=()):
    """One mimebundle ``(data, metadata)`` for a PLR error (D2): ``data`` holds exactly ``text/html``
    (the panel) and ``text/plain`` (heading, body, fix and PLR's line); ``metadata`` is ``{"praxis":
    stamp}`` with ``kind`` ``error``, ``rev`` null and ``resource`` by owner.

    ``tb`` defaults to ``exc.__traceback__``. ``session`` and ``exec_count`` are values or zero-argument
    callables. ``step`` is the ledger step (``None`` outside a ``RunLedger``). ``resolver`` replaces
    ``context.resolve`` (tests). It reads state and changes none. A context no template covers, or a
    template that fails to build, gives the generic panel.
    """
    tb = tb if tb is not None else getattr(exc, "__traceback__", None)
    step = step if isinstance(step, int) and not isinstance(step, bool) else None
    ctx = _resolve(exc, tb, resolver, decks)
    panel = None
    if ctx is not None:
        try:
            panel = _panel_for(exc, ctx)
        except Exception:  # noqa: BLE001 -- a template that cannot be built degrades to the generic panel
            log.warning("errors: could not build the panel for %s", type(exc).__name__, exc_info=True)
    tb_text = _traceback_text(exc, tb)
    data = {"text/html": _fit(exc, panel, step, tb_text), "text/plain": _plain_text(exc, panel, step)}
    metadata = {"praxis": labware.stamp("error", None if panel is None else panel.resource, None,
                                        _session_id(session), _exec_number(exec_count))}
    svg.check_bundle(data, metadata)
    return data, metadata


# --------------------------------------------------------------------------- handle and install


def _ipython_display():
    from IPython.display import display  # noqa: PLC0415 -- resolved only when a panel is shown

    return display


def _step_for(exc):
    try:
        return ledger.step_for(exc)  # also removes the entry (D9)
    except Exception:  # noqa: BLE001
        return None


def handle(exc, tb=None, *, session=None, exec_count=None, display=None, resolver=None, decks=()):
    """Show the panel for ``exc`` and return its one-line structured traceback, ``["<Name>: <message>"]``
    (D8). Never raises: a failure is logged and the line is returned anyway, so the cell still ends in an
    error. ``display`` defaults to ``IPython.display.display``; it is called ``display(data, raw=True,
    metadata=metadata)``.
    """
    stb = [f"{type(exc).__name__}: {_str(exc)}"]
    step = _step_for(exc)
    try:
        data, metadata = render(exc, tb, session=session, exec_count=exec_count, step=step,
                                resolver=resolver, decks=decks)
        (display or _ipython_display())(data, raw=True, metadata=metadata)
    except Exception:  # noqa: BLE001 -- the error output must survive whatever happens here
        log.warning("errors: could not display the error panel", exc_info=True)
    return stb


def _finish(shell, etype, evalue, stb) -> bool:
    """Finish the way IPython does, ``shell._showtraceback``, which makes the cell an error (the
    Pyodide kernel sets ``Interpreter._last_traceback`` there). False when the shell cannot."""
    finisher = getattr(shell, "_showtraceback", None)
    if not callable(finisher):
        return False
    finisher(etype, evalue, stb)
    return True


class Installed:
    """The handle ``install`` returns. ``uninstall()`` restores the shell; afterwards the wrapper (if
    something else wrapped it again) passes straight through to the original."""

    def __init__(self, shell, original, had_instance_attr):
        self.shell = shell
        self.original = original
        self.had_instance_attr = had_instance_attr
        self.wrapper = None
        self.active = True

    def uninstall(self) -> None:
        if not self.active:
            return
        self.active = False
        attrs = getattr(self.shell, "__dict__", {})
        if attrs.get("showtraceback") is self.wrapper:
            if self.had_instance_attr:
                attrs["showtraceback"] = self.original
            else:
                del attrs["showtraceback"]


def install(shell, *, session=None, exec_count=None, display=None, resolver=None) -> Installed:
    """Wrap ``shell.showtraceback`` (an instance attribute, S3-C) so the four PLR errors get the panel
    and every other exception goes to the original untouched. Idempotent: a second call returns the
    existing handle and registers nothing new. ``session`` and ``exec_count`` are values or zero-argument
    callables (``lambda: get_ipython().execution_count``), read when a panel is built.
    """
    if shell is None:
        raise ValueError("install needs a shell (get_ipython() returned None)")
    attrs = getattr(shell, "__dict__", {})
    existing = getattr(attrs.get("showtraceback"), _MARK, None)
    if existing is not None and existing.active:
        return existing
    installed = Installed(shell, shell.showtraceback, "showtraceback" in attrs)
    original = installed.original

    def showtraceback(*args, **kwargs):
        if not installed.active:
            return original(*args, **kwargs)
        exc = kwargs.get("exc_tuple") or (args[0] if args and args[0] else None) or sys.exc_info()
        try:
            etype, evalue, tb = exc
        except (TypeError, ValueError):
            return original(*args, **kwargs)
        if not _is_handled(evalue):
            return original(*args, **kwargs)
        stb = handle(evalue, tb, session=session, exec_count=exec_count, display=display,
                     resolver=resolver)
        try:
            if _finish(shell, etype, evalue, stb):
                return None
        except Exception:  # noqa: BLE001 -- never lose the error: fall back to the default traceback
            log.warning("errors: could not finish through _showtraceback", exc_info=True)
        return original(*args, **kwargs)

    setattr(showtraceback, _MARK, installed)
    installed.wrapper = showtraceback
    shell.showtraceback = showtraceback
    return installed
