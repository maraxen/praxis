"""plr_sema.check.tipstate: per-channel tip typestate (spec 260902 §10,
`260902_plr-sema-tip-typestate-increment.md`).

**Stdlib only** -- same import boundary as the rest of `check/` (module
docstring of `plr_sema.check`): no `pylabrobot`, no `libcst`, no
`pydantic`. `ast` is permitted (stdlib, used only to parse a guard's own
`condition` string into one of the three atom productions, §10.3.1 --
`derive/` already relies on the same distinction).

**What this module is.** §10.1's three-element lattice (`TipState`), §10.1.3's
channel-set derivation over an already-lowered `ir.Call.kwargs` (§11.9's
amendment: "lowers to a `Seq`", not "`ast.literal_eval`s to a list"),
§10.3's atom parser and evaluator, and §10.4's transfer functions (E1-E5).
`plr_sema.check.__init__.check_ir` threads a :class:`TipWalk` through its
existing region-stack pass over `bytecode.instructions` and calls
:func:`evaluate_call` once per `CALL`, in place of (for the guards this
module claims) or alongside (for `channel_guards`, which have no
`guard_predicate_unparsed` twin to replace) the pre-increment
`guard_predicate_unparsed` emission.

**Exactly one `Finding` per guard, never per operation (§10.3.3).** This
module never aggregates; `plr_sema.verdict.join` still does that, unchanged.

**No hand-typed PLR fact.** Every name this module reads (`channel_attr`,
`bool_view`'s `attr`/`field`, `state_fields`, `channel_default_param`,
`channel_default_disablers`, and, as of 260903 P9 (spec §13.5), `channel_kwarg`
and a `channel_guards` entry's own `bound_channels`) comes from the
`receiver_state`/`channel_guards` blocks `plr_sema.derive.receiver_state`
computed at build time (§10.2/§13.5.2) -- this module only reads them via
`.get()`, never types a PLR name itself (AC-10.9/AC-13.15(iii)'s AST
literal scan enforces this for this file specifically, same mechanism as
`plr_sema.check.ir`'s own AC-11.8 scan).
"""

from __future__ import annotations

import ast
import dataclasses
from enum import Enum
from typing import Any

from plr_sema.check import ir
from plr_sema.verdict import Finding, PlrSite, Verdict

__all__ = [
    "TipState",
    "join_tip",
    "ChannelState",
    "TipWalk",
    "channels_for_call",
    "evaluate_call",
    "region_receivers",
    "region_bounds",
    "join_channel_state",
    "join_walk_states",
    "disabled_receivers",
]


# ---------------------------------------------------------------------------
# §10.1.1 -- the lattice. Three elements, no bottom (main spec §Open
# decisions 1's reservation; this increment constructs neither branches nor
# an emptiness-detecting transfer function, so nothing needs one).
# ---------------------------------------------------------------------------


class TipState(Enum):
    NO_TIP = "NO_TIP"
    HAS_TIP = "HAS_TIP"
    TOP = "top"


def join_tip(a: TipState, b: TipState) -> TipState:
    """§10.1.1's join table: `NO_TIP up NO_TIP = NO_TIP`, `HAS_TIP up
    HAS_TIP = HAS_TIP`, everything else (including `TOP` with anything) is
    `TOP` -- the information order, never confused with `plr_sema.verdict
    .join`'s obligation order (§10.1.2).
    """
    return a if a is b else TipState.TOP


def fold_channels(channels: tuple[int, ...] | None, state_of: Any) -> TipState:
    """§10.3.2: `s = the join folded over op's channel set` -- `NO_TIP` iff
    every channel is `NO_TIP`, `HAS_TIP` iff every channel is `HAS_TIP`,
    `TOP` otherwise (including when `channels` is `None`, i.e. rule 4's
    `channels = Top`, §10.1.3).
    """
    if channels is None or not channels:
        return TipState.TOP
    states = {state_of(c) for c in channels}
    if states == {TipState.NO_TIP}:
        return TipState.NO_TIP
    if states == {TipState.HAS_TIP}:
        return TipState.HAS_TIP
    return TipState.TOP


# ---------------------------------------------------------------------------
# §10.1.3/§10.1.4 -- per-receiver abstract state.
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class ChannelState:
    """`(default, exact)` (§10.1.3): `default` is `TOP` at graph entry and
    is only ever LOWERED by an exact-channel transfer function that
    provably applies to every channel -- nothing in this increment does
    that, so `default` stays `TOP` for the whole walk (precision comes
    entirely from `exact`).
    """

    default: TipState = TipState.TOP
    exact: dict[int, TipState] = dataclasses.field(default_factory=dict)

    def get(self, channel: int) -> TipState:
        return self.exact.get(channel, self.default)

    def copy(self) -> "ChannelState":
        """Spec 260903 §12.3.3 (L2)/§12.3.6 (B1): both the fixpoint and the
        branch join need to explore a pass/arm from a given entry state and
        then either discard it or merge it with a sibling exploration --
        neither is expressible as an in-place mutation of the one live
        state map, so both need an independent copy.
        """
        return ChannelState(default=self.default, exact=dict(self.exact))


class TipWalk:
    """Per-receiver-slot `ChannelState`, threaded through `check_ir`'s
    region-stack pass. A slot never seen defaults to a fresh
    `ChannelState()` (`default=TOP, exact={}`) -- §10.1.3's "TOP at graph
    entry", read lazily rather than pre-seeded, since the set of receiver
    slots is only known once `RESOURCE`/`CALL` instructions are walked.
    """

    def __init__(self) -> None:
        self._states: dict[int, ChannelState] = {}

    def _cs(self, slot: int) -> ChannelState:
        cs = self._states.get(slot)
        if cs is None:
            cs = ChannelState()
            self._states[slot] = cs
        return cs

    def state(self, slot: int, channel: int) -> TipState:
        return self._cs(slot).get(channel)

    def widen(self, slot: int) -> None:
        """E4 (§10.4): the whole receiver is widened -- `sigma' =
        (default=TOP, exact={})`. Monotonic: widening can only destroy a
        verdict, never create a wrong one (§10.5's soundness argument).
        """
        self._states[slot] = ChannelState()

    def apply_exact(self, slot: int, channels: tuple[int, ...], effect: TipState) -> None:
        """E2 (§10.4): `sigma'.exact[c] = e` for each `c` in `channels`;
        channels outside the set are unchanged.
        """
        cs = self._cs(slot)
        for c in channels:
            cs.exact[c] = effect

    def reset(self, slot: int, default: TipState) -> None:
        """E6 (spec 260903 §12.1.4): `sigma' = ChannelState(default=<post>,
        exact={})` -- the reset effect's post-state is a claim about EVERY
        channel of the slot (§12.1.4 consequence 1: "precision arrives on
        channels nobody named"), so unlike `apply_exact` it replaces the
        whole slot state rather than updating individual channels. This is
        the first and only producer of `ChannelState.default`
        (§10.1.3/§12.1.4) -- everywhere else it stays `TOP`. `widen` still
        wipes it back to `TOP` (E4, §12.1.4 consequence 2): a reset is not
        "sticky" against a later widen.
        """
        self._states[slot] = ChannelState(default=default, exact={})

    def snapshot(self) -> dict[int, "ChannelState"]:
        """Spec 260903 §12.3.3/§12.3.6: an independent copy of every
        receiver slot's state, for a fixpoint pass or a branch arm to
        explore from without mutating the walk other explorations share.
        """
        return {slot: cs.copy() for slot, cs in self._states.items()}

    def restore(self, states: "dict[int, ChannelState]") -> None:
        """Replace the whole live state with an (independently copied)
        snapshot -- used to rewind to a fixpoint pass's head state, or to
        install a branch's joined post-state.
        """
        self._states = {slot: cs.copy() for slot, cs in states.items()}


def join_channel_state(a: ChannelState, b: ChannelState) -> ChannelState:
    """Spec 260903 §12.3.6 (B1)/§12.3.3 (L2): the per-receiver half of a
    join -- `default`s join directly (§10.1.1's `join_tip`), and each
    channel's EFFECTIVE state (`.get`, which falls back to `default`) joins
    over the UNION of both sides' explicit `exact` keys, never just one
    side's keys -- a channel exact on only one side still joins against the
    OTHER side's `default`, not against a missing key (which would silently
    drop that channel's information instead of widening it correctly).
    """
    default = join_tip(a.default, b.default)
    channels = set(a.exact) | set(b.exact)
    exact = {c: join_tip(a.get(c), b.get(c)) for c in channels}
    return ChannelState(default=default, exact=exact)


def join_walk_states(
    a: "dict[int, ChannelState]", b: "dict[int, ChannelState]"
) -> "dict[int, ChannelState]":
    """Whole-walk join over every receiver slot mentioned by EITHER side.
    A slot absent from one side is a slot that side's walk never touched --
    the same thing as a fresh `ChannelState()` (`TipWalk._cs`'s own lazy
    default), not information to drop by restricting to the intersection.
    """
    slots = set(a) | set(b)
    return {
        slot: join_channel_state(a.get(slot, ChannelState()), b.get(slot, ChannelState()))
        for slot in slots
    }


# ---------------------------------------------------------------------------
# §10.1.3 -- channel-set derivation over an already-lowered ir.Value
# (§11.9's amendment: "lowers to a Seq", not "ast.literal_eval's to a
# list").
# ---------------------------------------------------------------------------


def _int_seq(value: ir.Value | None) -> tuple[int, ...] | None:
    """Rule 1 (explicit): `value` is a `Seq` of `Lit` integers -> the exact
    tuple. `bool` is excluded even though `isinstance(True, int)` is `True`
    in Python -- a channel list is never boolean-valued in any real
    payload, and this keeps the rule from silently accepting one.
    """
    if not isinstance(value, ir.Seq):
        return None
    out: list[int] = []
    for item in value.items:
        if not (isinstance(item, ir.Lit) and isinstance(item.v, int) and not isinstance(item.v, bool)):
            return None
        out.append(item.v)
    return tuple(out)


def channels_for_call(
    call: ir.Call, channel_default_param: dict[str, str], channel_kwarg: str | None = None
) -> tuple[int, ...] | None:
    """§10.1.3, rules 1/3/4 (rule 2 -- the instance-default disabler -- is
    enforced structurally by :func:`disabled_receivers`'s pre-scan, which
    forces this function to be skipped entirely for a poisoned receiver;
    see `evaluate_call`). Returns the exact channel tuple, or `None` for
    `channels = Top` (rule 4).

    `channel_kwarg` -- the keyword PLR itself uses to select channels
    explicitly (§13.5.2/AC-13.15(iii): read from `receiver_state`'s own
    derived `channel_kwarg`, never hand-typed as `"use_channels"` here --
    that string is one of AC-13.15(iii)'s forbidden literals). `None`
    (a pre-P9 contract table, or a receiver whose P3a matches disagree on
    the name) degrades rule 1 to "never explicit", matching the pre-P9
    behaviour only for a receiver this fact cannot be derived for.
    """
    explicit = _int_seq(call.kwargs.get(channel_kwarg)) if channel_kwarg is not None else None
    if explicit is not None:
        return explicit
    param = channel_default_param.get(call.method)
    if param is not None:
        value = call.kwargs.get(param)
        if isinstance(value, ir.Seq):
            return tuple(range(len(value.items)))
    return None


def disabled_receivers(instructions: tuple[ir.Instruction, ...], receiver_states: dict[str, dict[str, Any]]) -> frozenset[int]:
    """§10.1.3 rule 2 / §10.4 E4 condition 4: a whole-program pre-scan --
    any `CALL` whose `method` is a `channel_default_disablers` member for
    its `receiver_type` poisons that receiver SLOT permanently, regardless
    of where in the stream the disabler call sits (the PLR fact this models
    -- `self._default_use_channels` -- is set by a context manager the
    analyzer cannot see the extent of, main spec §10.1.3). Enforced
    structurally: :func:`channels_for_call` is simply never invoked for a
    poisoned slot (`evaluate_call` checks membership first), so a poisoned
    receiver's channel set is `Top` for EVERY operation on it, matching
    "permanently".
    """
    poisoned: set[int] = set()
    for instr in instructions:
        if not isinstance(instr, ir.Call) or instr.receiver_type is None:
            continue
        rs = receiver_states.get(instr.receiver_type)
        if rs is None:
            continue
        if instr.method in rs.get("channel_default_disablers", ()):
            poisoned.add(instr.receiver)
    return frozenset(poisoned)


def region_receivers(instructions: tuple[ir.Instruction, ...], open_pc: int) -> tuple[frozenset[int], int]:
    """§11.1.3/§11.4.1's region-entry widening: given the pc of a `LOOP`/
    `BRANCH` open instruction, returns `(receiver slots mentioned anywhere
    in the region, the pc of the matching END)`. Handles nesting (a region
    inside the region) via a depth counter over `LOOP`/`BRANCH` opens vs.
    `END`s -- `ELSE` never changes depth (§11.1.3: it separates the two
    arms of the SAME open `BRANCH`).
    """
    depth = 1
    receivers: set[int] = set()
    pc = open_pc + 1
    n = len(instructions)
    while pc < n and depth > 0:
        instr = instructions[pc]
        if isinstance(instr, (ir.Loop, ir.Branch)):
            depth += 1
        elif isinstance(instr, ir.End):
            depth -= 1
            if depth == 0:
                break
        elif isinstance(instr, ir.Call):
            receivers.add(instr.receiver)
        pc += 1
    return frozenset(receivers), pc


def region_bounds(instructions: tuple[ir.Instruction, ...], open_pc: int) -> tuple[int, int | None]:
    """Spec 260903 §12.3.3/§12.3.6: sibling to :func:`region_receivers` --
    same nesting-depth walk from a `LOOP`/`BRANCH` open, but returns
    boundaries for a STRUCTURAL (recursive) walk rather than the
    region-entry widen set. Returns `(the pc of the matching END, the pc of
    the matching ELSE at the SAME nesting depth)`. `ELSE` is only ever
    `None` for a `LOOP`, or for an unterminated/malformed `BRANCH` in a
    fuzzed stream (`lower_graph` always emits one for every real or
    synthetic-with-real-arms `BRANCH` it constructs; a genuinely missing
    `ELSE` cannot arise from well-formed output, but the walker must stay
    total rather than raise on adversarial input, spec §12's own
    `check_graph` "never raises" property).
    """
    depth = 1
    pc = open_pc + 1
    n = len(instructions)
    else_pc: int | None = None
    while pc < n and depth > 0:
        instr = instructions[pc]
        if isinstance(instr, (ir.Loop, ir.Branch)):
            depth += 1
        elif isinstance(instr, ir.End):
            depth -= 1
            if depth == 0:
                break
        elif isinstance(instr, ir.Else) and depth == 1:
            else_pc = pc
        pc += 1
    return pc, else_pc


# ---------------------------------------------------------------------------
# §10.3.1 -- the atom parser. Two shapes: an OWN guard's condition (must
# name the channel-scoped path `self.<channel_attr>[<idx>].<...>`), and a
# CHANNEL guard's condition (channel-scope already established by its
# `via` field, so a bare `self.<...>` suffices, §10.3.1 criterion 3).
# ---------------------------------------------------------------------------

# (kind, is_none) -- kind is "bool_view" (is_none always None) or
# "null_check" (is_none True/False).
_Atom = tuple[str, "bool | None"]


def _is_self_attr(node: ast.expr, name: str | None = None) -> bool:
    if not (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "self"):
        return False
    return name is None or node.attr == name


def _null_check(node: ast.expr, state_fields: frozenset[str], base_ok: Any) -> _Atom | None:
    if not (isinstance(node, ast.Compare) and len(node.ops) == 1 and len(node.comparators) == 1):
        return None
    op = node.ops[0]
    if not isinstance(op, (ast.Is, ast.IsNot)):
        return None
    right = node.comparators[0]
    if not (isinstance(right, ast.Constant) and right.value is None):
        return None
    left = node.left
    if isinstance(left, ast.Attribute) and left.attr in state_fields and base_ok(left.value):
        return ("null_check", isinstance(op, ast.Is))
    return None


def _parse_atom(condition: str | None, *, bool_view_attr: str, state_fields: frozenset[str], base_ok: Any) -> _Atom | None:
    """Shared parser core. `base_ok(node.value)` decides whether the
    Attribute's RECEIVER expression is acceptable (channel-scoped for an
    own guard, or bare `self` for a channel guard) -- the only difference
    between the two call sites below.
    """
    if condition is None:
        return None
    try:
        node = ast.parse(condition, mode="eval").body
    except SyntaxError:
        return None
    if isinstance(node, ast.Attribute) and node.attr == bool_view_attr and base_ok(node.value):
        return ("bool_view", None)
    return _null_check(node, state_fields, base_ok)


def _is_channel_subscript(node: ast.expr, channel_attr: str) -> bool:
    return (
        isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Attribute)
        and isinstance(node.value.value, ast.Name)
        and node.value.value.id == "self"
        and node.value.attr == channel_attr
    )


def parse_own_atom(
    condition: str | None, *, channel_attr: str, bool_view_attr: str, state_fields: frozenset[str]
) -> _Atom | None:
    """§10.3.1 criterion 3, own-guard half: the path begins
    `self.<channel_attr>[<name>]`, e.g. `self.head[channel].has_tip`.
    """
    return _parse_atom(
        condition,
        bool_view_attr=bool_view_attr,
        state_fields=state_fields,
        base_ok=lambda base: _is_channel_subscript(base, channel_attr),
    )


def parse_bridge_atom(condition: str | None, *, bool_view_attr: str, state_fields: frozenset[str]) -> _Atom | None:
    """§10.3.1 criterion 3, channel-guard half: channel scope is already
    established by the guard's `via` field, so a bare `self.<...>`
    suffices, e.g. `self._tip is None` (from `TipTracker.get_tip`, reached
    via `self.head[channel].get_tip`).
    """
    return _parse_atom(
        condition,
        bool_view_attr=bool_view_attr,
        state_fields=state_fields,
        base_ok=lambda base: isinstance(base, ast.Name) and base.id == "self",
    )


def atom_truth(atom: _Atom, s: TipState) -> str:
    """§10.3.2's truth table. Returns `"T"`, `"F"`, or `"half"`."""
    if s is TipState.TOP:
        return "half"
    kind, is_none = atom
    if kind == "bool_view":
        return "T" if s is TipState.HAS_TIP else "F"
    # null_check
    if is_none:
        return "T" if s is TipState.NO_TIP else "F"
    return "T" if s is TipState.HAS_TIP else "F"


def _finding_for_atom(operation_id: str, guard_json: dict[str, Any], atom: _Atom, s: TipState) -> Finding:
    """§10.3.3's fires -> Finding table. `guard.kind == "raise_guard"` is a
    precondition of calling this (checked by the caller, §10.3.1 criterion
    1) -- `fires` is exactly the atom's truth value.
    """
    truth = atom_truth(atom, s)
    site_json = guard_json.get("site")
    site = PlrSite(file=site_json["file"], lineno=site_json["lineno"], qualname=site_json["qualname"]) if site_json else None
    detail = guard_json.get("condition") or ""
    if truth == "T":
        return Finding(
            verdict=Verdict.WILL_FAIL, operation_id=operation_id, category="precondition_state", plr_site=site, reason="", detail=detail
        )
    if truth == "F":
        return Finding(verdict=Verdict.SAFE, operation_id=operation_id, category="", plr_site=site, reason="", detail=detail)
    return Finding(
        verdict=Verdict.UNKNOWN, operation_id=operation_id, category="", plr_site=site, reason="channel_state_unknown", detail=detail
    )


# ---------------------------------------------------------------------------
# §10.4 -- the transfer function, and the per-CALL entry point.
# ---------------------------------------------------------------------------

#: §12.1.3's `"post"` wire values -> `TipState`. Built from `TipState`'s own
#: member values (`.value.lower()`), never a hand-typed literal -- one of
#: those values is the PLR bool-view attribute name `has_tip`
#: (`TipTracker.has_tip`, AC-10.9/AC-12.1(ii)'s forbidden-literal scan), so
#: it must be DERIVED here, not spelled out. Read only through this table
#: (never a hand-typed comparison against the string in-line at the call
#: site) so a stale/unrecognised `post` value degrades to `TOP` --
#: fail-closed, the same direction as E5/AC-10.7.
_POST_TO_TIPSTATE: dict[str, TipState] = {s.value.lower(): s for s in (TipState.NO_TIP, TipState.HAS_TIP)}


def _apply_transfer(
    call: ir.Call,
    channels: tuple[int, ...] | None,
    contract: dict[str, Any],
    walk: TipWalk,
    *,
    poisoned: bool,
) -> None:
    """E1's second half (§10.4): applied AFTER guards are evaluated against
    the pre-state. `contract["channel_effect"]` is `None` (E3, no bridge),
    `"HAS_TIP"`/`"NO_TIP"` (a single agreed depth-0 effect), or `"widen"`
    (E4.2 deep-only or E4.3 conflicting-depth-0 -- both collapse to the
    same transfer-function outcome, `derive.receiver_state
    .compute_channel_bridge`'s own docstring).
    """
    if poisoned:
        return  # rule 2/E4 condition 4: permanently Top; nothing to apply.
    effect = contract.get("channel_effect")
    if effect is None:
        return  # E3.
    if effect == "widen":
        walk.widen(call.receiver)
        return
    if channels is None:
        # E4 condition 1: a tracker-mutating bridge exists but channels(op)
        # is Top.
        walk.widen(call.receiver)
        return
    walk.apply_exact(call.receiver, channels, TipState.HAS_TIP if effect == "HAS_TIP" else TipState.NO_TIP)


def evaluate_call(
    operation_id: str,
    call: ir.Call,
    contract: dict[str, Any],
    receiver_state: dict[str, Any] | None,
    walk: TipWalk,
    *,
    poisoned: bool,
) -> tuple[tuple[Finding, ...], frozenset[int]]:
    """The per-`CALL` entry point. Returns `(tip_state_findings,
    consumed_own_guard_indices)` -- the second element is the set of
    indices into `contract["guards"]` whose `guard_predicate_unparsed`
    emission the caller (`plr_sema.check._findings_for_call`) must SKIP,
    because this function already emitted the real `WILL_FAIL`/`SAFE`/
    `channel_state_unknown` `Finding` in its place (§10.3.3: "the emission
    above REPLACES, one-for-one, the `guard_predicate_unparsed` finding").

    E5 (§10.4): `receiver_state is None` (no P2 anchor for this receiver
    type, or `receiver_type is None`) -> `((), frozenset())`, no
    involvement at all.
    """
    if receiver_state is None:
        return (), frozenset()

    channel_attr = receiver_state["channel_attr"]
    bool_view_attr = receiver_state["bool_view"]["attr"]
    state_fields = frozenset(receiver_state.get("state_fields", ()))
    channel_default_param = receiver_state.get("channel_default_param", {})
    channel_kwarg = receiver_state.get("channel_kwarg")

    channels = None if poisoned else channels_for_call(call, channel_default_param, channel_kwarg)

    # §10.3.1 criterion 4, GATING (not a fold-to-Top input): "op's channel
    # set is exact ... and every channel in it has a state that is not
    # Top." An INEXACT channel set (rule 4, `channels is None`) means the
    # guard is not tip-state-interpretable AT ALL -- it falls through to
    # the old `guard_predicate_unparsed` finding, UNCHANGED (AC-10.4: the
    # shipped fixture's operations never resolve an exact channel set, so
    # zero `channel_state_unknown` findings are produced, not "produced
    # with reason=Top"). Only once the channel SET is known exact does the
    # evaluator proceed to FOLD the per-channel STATES (§10.3.2) -- and
    # THAT fold can still legitimately yield Top (disagreeing or
    # individually-Top channel states), which IS when `channel_state_unknown`
    # fires. Conflating "channel set inexact" with "folded state is Top"
    # was an earlier draft's bug; the two are different gates at different
    # points of §10.3.
    findings: list[Finding] = []
    consumed: set[int] = set()

    if channels is not None:
        s = fold_channels(channels, lambda c: walk.state(call.receiver, c))

        for idx, guard in enumerate(contract.get("guards", ())):
            if guard.get("kind") != "raise_guard":
                continue
            atom = parse_own_atom(
                guard.get("condition"), channel_attr=channel_attr, bool_view_attr=bool_view_attr, state_fields=state_fields
            )
            if atom is None:
                continue
            consumed.add(idx)
            findings.append(_finding_for_atom(operation_id, guard, atom, s))

    # 260903 (spec §13.5.2, P9): the channel_guards loop runs INDEPENDENTLY
    # of the `channels is not None` gate above -- a `channel_guards` entry
    # carrying a derived `bound_channels` record is interpretable off ITS
    # OWN bound channel set even when the OPERATION's own `channels_for_call`
    # is Top (exactly `transfer`'s case, §13.5.1: no P3a idiom of its own,
    # no explicit `use_channels` either). §10.3.1 criterion 4 is re-read,
    # per guard, to accept `bound_channels` in place of the operation's own
    # channel set. Rule 4 (P3b disabler poisoning) is re-applied HERE, via
    # the pre-existing `poisoned` pre-scan, AFTER `bound_channels` was
    # already computed at derive time -- §13.5.2's own ordering requirement
    # ("checked after 2 and 3, never before"): a poisoned receiver ignores
    # `bound_channels` and falls back to the operation's own (poisoned ->
    # `None`) channel set, same as a guard with no `bound_channels` at all.
    used_bound_channels = False
    for guard in contract.get("channel_guards", ()):
        if guard.get("kind") != "raise_guard":
            continue
        bound = None if poisoned else guard.get("bound_channels")
        if bound is not None:
            guard_channels = tuple(bound.get("channels", ()))
            if not guard_channels:
                guard_channels = None
            else:
                used_bound_channels = True
        else:
            guard_channels = channels
        if guard_channels is None:
            continue
        s_g = fold_channels(guard_channels, lambda c: walk.state(call.receiver, c))
        atom = parse_bridge_atom(guard.get("condition"), bool_view_attr=bool_view_attr, state_fields=state_fields)
        if atom is None:
            continue
        findings.append(_finding_for_atom(operation_id, guard, atom, s_g))

    _apply_transfer(call, channels, contract, walk, poisoned=poisoned)

    # 260903 (spec §13.5.2's last paragraph / AC-13.15(ii)): E2 is NOT
    # extended -- a bound channel set makes a channel_guards entry
    # EVALUABLE, it does not give the CALL a tip effect, so `_apply_transfer`
    # above (driven entirely by `contract["channel_effect"]`, unchanged by
    # P9) still applies E3's no-op for a delegate-only method like
    # `transfer`. But having just read receiver state THROUGH a delegate
    # via `bound_channels`, this call demonstrably reaches into a delegate
    # this analyzer does not otherwise model the post-state of -- E4.2's
    # widen (a "delegate-only method" bridge) applies to the receiver
    # afterward, same as it would if `channel_effect` had come back
    # `"widen"` on its own. Scoped to the E3 case (`channel_effect is None`)
    # only: if the contract table already resolved a real HAS_TIP/NO_TIP/
    # widen effect for this call, that (unrelated) fact governs unchanged.
    if used_bound_channels and not poisoned and contract.get("channel_effect") is None:
        walk.widen(call.receiver)

    # E6 (spec 260903 §12.1.4, the reset effect): AFTER the call's own
    # guards have been evaluated against the pre-state (the loop above)
    # and after E1-E4's own transfer (`_apply_transfer`, whose bridge
    # `channel_effect` for a reset method such as `setup` is `None` -- E3,
    # no bridge -- so there is nothing for E6 to be racing against here),
    # a CALL whose method is the derived `entry_reset.method` sets the
    # receiver's WHOLE state to `ChannelState(default=post, exact={})`.
    # Read through `.get()` with an empty default (`receiver_state` may be
    # a pre-increment table with no `entry_reset` key at all, AC-12.2(c)):
    # this degrades to a no-op, unconditionally on `channels`/`poisoned`
    # -- the reset is a fact about the CALL itself, not about a channel
    # set `setup()` never takes.
    entry_reset = receiver_state.get("entry_reset")
    if entry_reset is not None and call.method == entry_reset.get("method"):
        walk.reset(call.receiver, _POST_TO_TIPSTATE.get(entry_reset.get("post"), TipState.TOP))

    return tuple(findings), frozenset(consumed)
