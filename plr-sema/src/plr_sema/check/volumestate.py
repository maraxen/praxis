"""plr_sema.check.volumestate: the volume-family interval domain (spec
260903 §14, `260903_plr-sema-volume-increment.md`).

**Stdlib only** -- same import boundary as the rest of `check/` (module
docstring of `plr_sema.check`): no `pylabrobot`, no `libcst`, no
`pydantic`. `ast` is permitted (used only to read the tolerance literal out
of a guard's own `condition` string, §14.5's "the 1e-06 tolerance is read
from the guard, not typed"). This module additionally imports
`plr_sema.derive.receiver_state.volume_guard_is_unconditional` -- that
module's own docstring (`receiver_state.py`, immediately above the
function) names T26/T27 as the intended importer, so the recognition test
is implemented exactly once, not re-derived here.

**What this module is.** §14.3's interval domain (`Interval`, `CellId`,
`VolumeWalk`), V0-V5 (§14.5): V0's three pairing clauses (parameter,
local/tip, the `use_channels` length conjunct), V1's pre-state-then-
transfer ordering, V2's pair-by-pair sequential threading, V3's widen, V4's
region-entry/tail widen (wired from `check/__init__.py`, which owns the
region walk), and V5's tip-cell lifecycle (`tips_dirty`). Guard evaluation
(§14.5's truth table) is gated through `volume_guard_is_unconditional`
(§14.6): a conditional guard may emit `SAFE`/`UNKNOWN` but never
`WILL_FAIL`.

**No hand-typed PLR fact (AC-14.2(iii)/(iv)).** Every name this module
would otherwise need to spell out -- the used-volume accessor, the
free-volume accessor, the tracked field, `Container`/`Tip`'s tracker
attribute, the two `volume_state` exception class names, the bridge
parameter names (`resources`/`vols`) -- is read off the contract table's
own `volume_guards` entries (`cell_param`, `amount_param`, `direction`,
`condition`, `caller_scope`, `caller_lineno`, `for_span`, `site`) via
`.get()`/indexing, never spelled out as a string literal in this file. The
**direction** field (`"decreasing"`/`"increasing"`/`None`, §14.4's
direction rule) is what distinguishes the decidable under-draw half from
the permanently-½ over-fill half -- NOT a comparison against either
exception class's own name, which is exactly how this module avoids typing
`"TooLittleLiquidError"`/`"TooLittleVolumeError"` (both on
AC-14.2(iii)'s forbidden list). `test_derive.py::test_ac_14_2_iii_iv_no_
hand_typed_volume_names_ast_scan` enforces this for this file specifically,
same mechanism as `plr_sema.check.ir`'s AC-11.8 scan and `check.tipstate`'s
AC-10.9 scan.

**The seed CALL (§14.8)'s wire shape is still hand-typed; the receiver/
method PAIR is not (260903 T27).** §14.8's normative box specifies the
seed's wire shape VERBATIM: `{"receiver": ..., "receiver_type":
"VolumeTracker", "method": "set_volume", "kwargs": {"volume": <Lit>}}`.
That shape -- and the `"volume"` kwarg name -- is a WIRE CONVENTION this
module still writes down (same status as the IR's own opcode-tag
vocabulary, which AC-14.2(iii)'s narrowed re-check excludes for the
identical reason). What T24 hand-typed IN ADDITION -- `call.receiver_type
!= "VolumeTracker" or call.method != "set_volume"` as a literal pair in
`_apply_seed` -- is a PLR fact ("which class, which method sets a
tracker's volume"), and that residue is gone: P7 (`derive.receiver_state
._volume_setter`) now publishes an additive `"is_volume_setter": true` key
on the SETTER METHOD'S OWN contract entry (`derive.__main__
.build_derived_contracts_payload`, deliberately NOT under the shared
`receiver_state` block `tipstate.evaluate_call` also reads and indexes
unconditionally -- see `_apply_seed`'s own docstring for why that would
have raised `KeyError`), and `_apply_seed` reads `contract.get(
"is_volume_setter")` off the SAME `contract` dict `evaluate_call` already
receives -- no `"VolumeTracker"`/`"set_volume"` literal anywhere in this
file (AC-14.2(iii)'s forbidden list is extended with both strings by
`test_derive.py` so the residue cannot return unnoticed).

**V5's third bullet -- "unmodelled tip movement" -- is derived, not
hand-typed (260903 T27).** §14.5's V5 names three PLR method shapes
(`move_resource`/`move_plate` over a tip rack, a `stamp`, any 96-head
operation) that move a mounted tip without giving the tip family a
modelled effect at all -- there is no derived contract field that flags
"this method moves a tip" the way `channel_effect` flags the first two V5
bullets, and `derive.receiver_state.compute_tip_families` classifies a
method off a tip-state `raise_guard`/`channel_effect`, neither of which
these three methods have (that absence IS why they are "unmodelled"). With
no published classification to fall back to, and no resource-TYPE operand
reachable from a `CALL`'s own kwargs at this IR version (`ir.Ref` carries
only `slot`/`cell`, §11.1.2 -- the tip-rack-type branch never applies), the
fail-closed fallback is structural: any call the VOLUME family has not
already modelled itself (`contract.get("volume_guards")` empty -- this is
what keeps `aspirate`/`dispense` out, since despite having no
`channel_effect` either they ARE modelled, and neither moves a mounted
tip) that references `>=1` resource in its own kwargs sets `tips_dirty`.
No shipped fixture exercises this branch; it is included because the spec
requires it, and its structure -- not a name list -- is disclosed here so
a reviewer can find it without a diff.
"""

from __future__ import annotations

import ast
import dataclasses
import math
from typing import Any

from plr_sema.check import ir, tipstate
from plr_sema.derive.receiver_state import volume_guard_is_unconditional
from plr_sema.verdict import Finding, PlrSite, Verdict

__all__ = [
    "Interval",
    "TOP",
    "CellId",
    "VolumeSnapshot",
    "VolumeWalk",
    "join_walk_states",
    "evaluate_call",
    "region_cells",
]

# ---------------------------------------------------------------------------
# §14.3 -- the abstract state. CellId is either ("container", slot, cell) or
# ("tip", channel) -- plain tuples, matching the spec's own notation
# verbatim, so no new hashable wrapper type is needed for dict keys.
# ---------------------------------------------------------------------------

CellId = tuple  # ("container", slot: int, cell: str | None) | ("tip", channel: int)


@dataclasses.dataclass(frozen=True, slots=True)
class Interval:
    """`[lo, hi]` with `0 <= lo <= hi <= +inf`. `TOP` (below) is `[0, +inf]`
    -- the two are identified, not two different representations (§14.3):
    arithmetic on `math.inf` (`inf - x == inf`, `inf + x == inf`) then makes
    every transfer function correct on `TOP` with no special case.
    """

    lo: float
    hi: float


#: `TOP` is `[0, +inf]` (§14.3) -- the default for any cell the walk has
#: never seen (graph entry) and the result of E4-style widening.
TOP: Interval = Interval(0.0, math.inf)


def _join_interval(a: Interval, b: Interval) -> Interval:
    """The join: `[min(lo), max(hi)]` -- the least upper bound in the
    information order (§14.3), used at a `BRANCH` merge and nowhere else
    (a trip=`None` `LOOP` is handled by V4's blunt widen, not this join --
    see `check/__init__.py`'s wiring and this module's own `region_cells`).
    """
    return Interval(min(a.lo, b.lo), max(a.hi, b.hi))


@dataclasses.dataclass(frozen=True, slots=True)
class VolumeSnapshot:
    """An independent copy of a `VolumeWalk`'s whole live state -- a
    `BRANCH` arm join needs to explore from a shared entry state and then
    merge two independent explorations, mirroring `tipstate.ChannelState
    .copy`/`TipWalk.snapshot`.
    """

    cells: dict[Any, Interval]
    tips_dirty: bool


class VolumeWalk:
    """Threaded through `check_ir`'s region-stack pass alongside
    `tipstate.TipWalk`. A cell never seen defaults to `TOP` (§14.3, read
    lazily via `.get`, never pre-seeded -- same discipline as `TipWalk`).
    `tips_dirty` (§14.5 V5) is a single walk-level monotone flag, not
    per-cell -- the unmodelled movements it guards against are not
    channel-scoped (V5's own closing sentence).
    """

    def __init__(self) -> None:
        self._cells: dict[Any, Interval] = {}
        self.tips_dirty: bool = False

    def get(self, cell: Any) -> Interval:
        return self._cells.get(cell, TOP)

    def set(self, cell: Any, interval: Interval) -> None:
        self._cells[cell] = interval

    def widen(self, cell: Any) -> None:
        """V3/V4: the cell becomes `TOP`. Monotonic, same direction as
        `TipWalk.widen` -- widening can only destroy precision, never
        fabricate one (§14.5's own soundness argument, transposed from
        §10.5).
        """
        self._cells[cell] = TOP

    def pickup(self, cell: Any) -> None:
        """V5, first bullet: a `pick_up_tips`-shaped effect. `[0, 0]` iff
        `tips_dirty` is false; `TOP` otherwise -- the round-1 O4 fix.
        """
        self._cells[cell] = TOP if self.tips_dirty else Interval(0.0, 0.0)

    def drop(self, cell: Any) -> None:
        """V5, second bullet: a `drop_tips`/`discard_tips`-shaped effect.
        The departing cell becomes `TOP` unconditionally; `tips_dirty` is
        set iff the departing interval is not provably `[0, 0]` -- `hi > 0`
        covers `TOP` itself (`hi == +inf > 0`) with no separate branch.
        """
        interval = self.get(cell)
        if interval.hi > 0.0:
            self.tips_dirty = True
        self._cells[cell] = TOP

    def snapshot(self) -> VolumeSnapshot:
        return VolumeSnapshot(cells=dict(self._cells), tips_dirty=self.tips_dirty)

    def restore(self, snapshot: VolumeSnapshot) -> None:
        self._cells = dict(snapshot.cells)
        self.tips_dirty = snapshot.tips_dirty


def join_walk_states(a: VolumeSnapshot, b: VolumeSnapshot) -> VolumeSnapshot:
    """Whole-walk join over every cell mentioned by EITHER side (a cell
    absent from one side is a fresh `TOP` there, same "don't restrict to
    the intersection" discipline as `tipstate.join_walk_states`) plus
    `tips_dirty` OR -- a walk-level fact true if EITHER arm could have made
    it true, mirroring the monotone "never cleared" rule of V5 itself.
    """
    cells = set(a.cells) | set(b.cells)
    merged = {cell: _join_interval(a.cells.get(cell, TOP), b.cells.get(cell, TOP)) for cell in cells}
    return VolumeSnapshot(cells=merged, tips_dirty=a.tips_dirty or b.tips_dirty)


# ---------------------------------------------------------------------------
# §14.5 V0 -- pairing. Two clauses (parameter / local-tip) plus the
# use_channels length conjunct.
# ---------------------------------------------------------------------------


def _ref_seq(value: ir.Value | None) -> list[ir.Ref] | None:
    if isinstance(value, ir.Ref):
        return [value]
    if isinstance(value, ir.Seq) and all(isinstance(item, ir.Ref) for item in value.items):
        return list(value.items)
    return None


def _lit_num_seq(value: ir.Value | None) -> list[float] | None:
    def _num(item: ir.Value) -> float | None:
        if isinstance(item, ir.Lit) and isinstance(item.v, (int, float)) and not isinstance(item.v, bool):
            return float(item.v)
        return None

    if isinstance(value, ir.Lit):
        n = _num(value)
        return None if n is None else [n]
    if isinstance(value, ir.Seq):
        out: list[float] = []
        for item in value.items:
            n = _num(item)
            if n is None:
                return None
            out.append(n)
        return out
    return None


def _int_lit_seq_len(value: ir.Value | None) -> int | None:
    """The `use_channels` conjunct's own reading of its operand: `None`
    unless `value` is a `Seq` of numeric, non-bool integer `Lit`s -- in
    which case its length. `None` means "not a concrete `Seq`", which is
    the "doesn't gate" case (§14.5 V0(c): the conjunct only fires when
    `use_channels` DOES lower to such a `Seq`).
    """
    if not isinstance(value, ir.Seq):
        return None
    for item in value.items:
        if not (isinstance(item, ir.Lit) and isinstance(item.v, int) and not isinstance(item.v, bool)):
            return None
    return len(value.items)


def _resolve_cells(
    call: ir.Call,
    guard: dict[str, Any],
    channel_default_param: dict[str, str],
    channel_kwarg: str | None,
    *,
    poisoned: bool,
) -> list[Any] | None:
    """Cell-only half of V0 -- resolves `cells(op)` regardless of whether
    `amounts(op)` or the `use_channels` conjunct also resolve (used both by
    the full pairing below AND by V3/V4's widen, which needs to know WHICH
    cells to widen even when the guard as a whole cannot be evaluated).
    """
    cell_param = guard.get("cell_param")
    if cell_param is None:
        return None
    if isinstance(cell_param, dict):
        if not cell_param.get("local") or poisoned:
            return None
        channels = tipstate.channels_for_call(call, channel_default_param, channel_kwarg)
        if channels is None:
            return None
        return [("tip", c) for c in channels]
    refs = _ref_seq(call.kwargs.get(cell_param))
    if refs is None:
        return None
    return [("container", ref.slot, ref.cell) for ref in refs]


def _use_channels_conjunct_ok(call: ir.Call, channel_kwarg: str | None, n: int) -> bool:
    if channel_kwarg is None:
        return True
    n_channels = _int_lit_seq_len(call.kwargs.get(channel_kwarg))
    if n_channels is None:
        return True  # not a concrete Seq of numeric Lits -- conjunct does not gate.
    return n_channels == n


def _v0_pairs(
    call: ir.Call,
    guard: dict[str, Any],
    channel_default_param: dict[str, str],
    channel_kwarg: str | None,
    *,
    poisoned: bool,
) -> list[tuple[Any, float]] | None:
    cells = _resolve_cells(call, guard, channel_default_param, channel_kwarg, poisoned=poisoned)
    if cells is None:
        return None
    amount_param = guard.get("amount_param")
    if amount_param is None:
        return None
    amounts = _lit_num_seq(call.kwargs.get(amount_param))
    if amounts is None or len(amounts) != len(cells):
        return None
    if not _use_channels_conjunct_ok(call, channel_kwarg, len(cells)):
        return None
    return list(zip(cells, amounts))


# ---------------------------------------------------------------------------
# §14.5 -- guard evaluation (the T/F/½ table) and V2's per-pair transfer.
# ---------------------------------------------------------------------------


def _tolerance(condition: str | None) -> float:
    """The `1e-06` in a guard's condition is READ, not typed (§14.5's own
    closing note): parse `condition` and pull the right-hand numeric
    literal of its top-level comparison. Any parse failure or unexpected
    shape degrades to `0.0` -- fail-closed in the sense that a smaller
    tolerance only ever makes `fires`/`safe` HARDER to satisfy, never
    easier, so a degrade cannot manufacture a definite verdict from a
    guard shape this module does not recognise.
    """
    if condition is None:
        return 0.0
    try:
        node = ast.parse(condition, mode="eval").body
    except SyntaxError:
        return 0.0
    if isinstance(node, ast.Compare) and len(node.ops) == 1 and len(node.comparators) == 1:
        right = node.comparators[0]
        if isinstance(right, ast.Constant) and isinstance(right.value, (int, float)) and not isinstance(
            right.value, bool
        ):
            return float(right.value)
    return 0.0


def _site_from_guard(guard: dict[str, Any]) -> PlrSite | None:
    site = guard.get("site")
    if site is None:
        return None
    return PlrSite(file=site["file"], lineno=site["lineno"], qualname=site["qualname"])


def _will_fail(operation_id: str, site: PlrSite | None, *, detail: str) -> Finding:
    return Finding(
        verdict=Verdict.WILL_FAIL,
        operation_id=operation_id,
        category="precondition_state",
        plr_site=site,
        reason="",
        detail=detail,
    )


def _safe(operation_id: str, site: PlrSite | None, *, detail: str) -> Finding:
    return Finding(verdict=Verdict.SAFE, operation_id=operation_id, category="", plr_site=site, reason="", detail=detail)


def _volume_state_unknown(operation_id: str, site: PlrSite | None, *, detail: str) -> Finding:
    return Finding(
        verdict=Verdict.UNKNOWN,
        operation_id=operation_id,
        category="",
        plr_site=site,
        reason="volume_state_unknown",
        detail=detail,
    )


def _volume_tracking_unasserted(operation_id: str, site: PlrSite | None, *, detail: str) -> Finding:
    return Finding(
        verdict=Verdict.UNKNOWN,
        operation_id=operation_id,
        category="",
        plr_site=site,
        reason="volume_tracking_unasserted",
        detail=detail,
    )


def _pair_finding(
    operation_id: str,
    guard: dict[str, Any],
    interval: Interval,
    amount: float,
    *,
    env: frozenset[str],
) -> Finding:
    """§14.5's guard-evaluation table, for ONE pair's pre-state interval.
    `direction != "decreasing"` covers both the permanently-½ over-fill
    half (`"increasing"`, §14.2's capacity-is-Top argument -- never
    evaluated against the interval at all, by construction, which is how
    this module avoids needing either exception class's own name) and the
    no-transfer case (`direction is None`, §14.4: "carries its guard but
    no transfer").
    """
    site = _site_from_guard(guard)
    detail = guard.get("condition") or ""
    if guard.get("direction") != "decreasing":
        return _volume_state_unknown(operation_id, site, detail=detail)
    tol = _tolerance(guard.get("condition"))
    fires = (amount - interval.hi) > tol
    safe = (amount - interval.lo) <= tol
    if fires:
        unconditional = volume_guard_is_unconditional(
            guard.get("caller_scope"), guard.get("caller_lineno"), guard.get("for_span"), env
        )
        if unconditional:
            return _will_fail(operation_id, site, detail=detail)
        return _volume_tracking_unasserted(operation_id, site, detail=detail)
    if safe:
        return _safe(operation_id, site, detail=detail)
    return _volume_state_unknown(operation_id, site, detail=detail)


def _evaluate_guard(
    operation_id: str,
    call: ir.Call,
    guard: dict[str, Any],
    walk: VolumeWalk,
    channel_default_param: dict[str, str],
    channel_kwarg: str | None,
    *,
    env: frozenset[str],
    poisoned: bool,
) -> list[Finding]:
    pairs = _v0_pairs(call, guard, channel_default_param, channel_kwarg, poisoned=poisoned)
    if pairs is None:
        # V3: widen every cell V0 COULD still identify (cell-only
        # resolution) even though the full pairing failed -- e.g. amounts
        # unresolved (Top) with cells known, or the use_channels conjunct
        # disagreeing.
        cells = _resolve_cells(call, guard, channel_default_param, channel_kwarg, poisoned=poisoned)
        for cell in cells or ():
            walk.widen(cell)
        site = _site_from_guard(guard)
        return [_volume_state_unknown(operation_id, site, detail=guard.get("condition") or "")]

    direction = guard.get("direction")
    findings: list[Finding] = []
    for cell, amount in pairs:  # V2: threaded pair-by-pair, in list order.
        interval = walk.get(cell)  # V1: evaluate against the PRE-state.
        findings.append(_pair_finding(operation_id, guard, interval, amount, env=env))
        if direction == "decreasing":
            walk.set(cell, Interval(max(0.0, interval.lo - amount), max(0.0, interval.hi - amount)))
        elif direction == "increasing":
            walk.set(cell, Interval(interval.lo + amount, interval.hi + amount))
        # direction is None: guard carries no transfer (§14.4).
    return findings


# ---------------------------------------------------------------------------
# §14.5 V5 -- the tip-cell lifecycle.
# ---------------------------------------------------------------------------

def _mentions_a_resource(value: ir.Value | None) -> bool:
    """True iff `value` resolves `>=1` `ir.Ref` -- a bare `Ref`, or a `Seq`
    containing one at any position (a partially-resolved list still names
    a resource where it has a `Ref` element). `ir.Top`/a non-resource `Lit`
    are both `False`.
    """
    if isinstance(value, ir.Ref):
        return True
    if isinstance(value, ir.Seq):
        return any(_mentions_a_resource(item) for item in value.items)
    return False


def _is_unmodelled_tip_movement(call: ir.Call, contract: dict[str, Any]) -> bool:
    """260903 T27 (spec §14.5 V5's third bullet, round-1 defender's
    `_UNMODELLED_TIP_MOVEMENT_METHODS` residue): un-hand-typed by falling
    back through the tip family's OWN classification, in the order the
    task names.

    1. Nothing published covers `move_resource`/`move_plate`/`stamp` at
       all: `derive.receiver_state.compute_tip_families` only classifies a
       method as `tip_loading`/`tip_requiring`/`tip_dropping` off a
       tip-state `raise_guard` or a `channel_effect` -- and having NEITHER
       is exactly why this call reached this branch (`_apply_v5` only
       calls this helper when `contract.get("channel_effect") is None`).
       There is therefore no published tip-family fact this function could
       read instead for these three methods specifically.
    2. The tip-rack-resource-type fallback the spec's normative box also
       licenses never applies at this IR version: a `CALL.kwargs` value is
       an `ir.Ref`/`ir.Seq`/`ir.Lit`/`ir.Top` (§11.1.2) -- a `Ref` carries
       only `slot`/`cell`, never a resource TYPE, and nothing threads the
       bytecode's own `RESOURCE` type declarations into this per-call
       evaluation. So "the graph carries that type" is false here by
       construction, not by omission.
    3. The remaining, most-conservative fallback: any call the VOLUME
       family has not already modelled itself (`contract.get(
       "volume_guards")` empty -- this is what keeps `aspirate`/`dispense`
       OUT of this branch despite having no `channel_effect` either: they
       ARE modelled, by the volume bridge, and neither one moves a mounted
       tip, which is exactly why AC-14.5(e)'s retip fixture needs
       `tips_dirty` to stay false across an aspirate/dispense pair) that
       references `>=1` resource in its own kwargs sets `tips_dirty` --
       fail-closed, same "assume dirty" direction as the channels-`None`
       branch just above this one in `_apply_v5`.
    """
    if contract.get("volume_guards"):
        return False
    return any(_mentions_a_resource(v) for v in call.kwargs.values())


def _apply_v5(
    call: ir.Call,
    contract: dict[str, Any],
    walk: VolumeWalk,
    channel_default_param: dict[str, str],
    channel_kwarg: str | None,
    *,
    poisoned: bool,
) -> None:
    """§14.5 V5's three bullets, driven by the SAME `channel_effect` the
    tip family itself reads (`tipstate._apply_transfer`) -- `"HAS_TIP"` is
    a `pick_up_tips`-shaped effect, `"NO_TIP"`/`"widen"` are a
    `drop_tips`/`discard_tips`-shaped one (both are a DEPARTURE for the
    volume family's purposes: a `channel_effect == "widen"` bridge -- e.g.
    `discard_tips`, whose exact channels the tip family itself could not
    resolve -- still means the tip is gone). `channel_effect is None`
    falls through to the disclosed third-bullet heuristic.
    """
    effect = contract.get("channel_effect")
    if effect is None:
        if _is_unmodelled_tip_movement(call, contract):
            walk.tips_dirty = True
        return
    channels = None if poisoned else tipstate.channels_for_call(call, channel_default_param, channel_kwarg)
    if effect == "HAS_TIP":
        for c in channels or ():
            walk.pickup(("tip", c))
        return
    # "NO_TIP" or "widen": a departure.
    if channels is None:
        # Can't identify which cell(s) departed, so the "provably [0, 0]"
        # check cannot be made -- fail-closed to "assume dirty".
        walk.tips_dirty = True
        return
    for c in channels:
        walk.drop(("tip", c))


def _apply_seed(call: ir.Call, walk: VolumeWalk, contract: dict[str, Any]) -> None:
    """§14.8's seeding convention (see the module docstring's disclosed-
    exception note): a CALL sets the addressed CONTAINER cell's interval to
    the exact literal, `[v, v]`, iff `contract.get("is_volume_setter")` is
    true -- an additive key `derive.__main__.build_derived_contracts_payload`
    publishes on THIS CALL's own contract entry (the SAME `contract` dict
    `evaluate_call` already receives) iff `call.receiver_type` is P7's
    anchored class AND `call.method` equals that class's published
    `setter`. No `"VolumeTracker"`/`"set_volume"` literal (260903 T27,
    round-1 defender's `_apply_seed` residue) -- deliberately NOT read off
    `receiver_state` (the `receiver_states.get(call.receiver_type)` lookup
    `check/__init__.py` also hands to `tipstate.evaluate_call`, which
    indexes `receiver_state["channel_attr"]` unconditionally whenever it is
    non-`None`; a `{"setter": ...}`-only block keyed under the SAME shared
    dict would reach that indexing and raise `KeyError`) -- seeding is the
    one place a volume arrives as GROUND TRUTH, not as an over-
    approximation built from a guard's transfer function.
    """
    if not contract.get("is_volume_setter"):
        return
    value = call.kwargs.get("volume")
    if isinstance(value, ir.Lit) and isinstance(value.v, (int, float)) and not isinstance(value.v, bool):
        v = float(value.v)
        walk.set(("container", call.receiver, None), Interval(v, v))


def evaluate_call(
    operation_id: str,
    call: ir.Call,
    contract: dict[str, Any],
    receiver_state: dict[str, Any] | None,
    walk: VolumeWalk,
    *,
    env: frozenset[str],
    poisoned: bool,
) -> tuple[Finding, ...]:
    """The per-`CALL` entry point (mirrors `tipstate.evaluate_call`'s
    shape). Runs for EVERY call, not only calls whose contract carries
    `volume_guards` -- V5's lifecycle (`pick_up_tips`/`drop_tips`/
    `discard_tips`) fires on calls that carry NO `volume_guards` at all
    (their contract entries have no bridge; see `derived_contracts.json`),
    and the seed CALL (`_apply_seed`) fires on a `VolumeTracker.set_volume`
    call, which likewise carries no `volume_guards` of its own.
    """
    channel_default_param = (receiver_state or {}).get("channel_default_param", {})
    channel_kwarg = (receiver_state or {}).get("channel_kwarg")

    findings: list[Finding] = []
    for guard in contract.get("volume_guards", ()):
        findings.extend(
            _evaluate_guard(
                operation_id, call, guard, walk, channel_default_param, channel_kwarg, env=env, poisoned=poisoned
            )
        )

    _apply_v5(call, contract, walk, channel_default_param, channel_kwarg, poisoned=poisoned)
    _apply_seed(call, walk, contract)

    return tuple(findings)


# ---------------------------------------------------------------------------
# §14.5 V4 -- region-entry/tail widen. Mirrors tipstate.region_receivers'
# shape (same depth-counted walk), scoped to volume cells.
# ---------------------------------------------------------------------------


def region_cells(
    instructions: tuple[ir.Instruction, ...],
    open_pc: int,
    contracts: dict[str, Any],
    receiver_states: dict[str, Any],
) -> frozenset[Any]:
    """Every `CellId` any volume guard INSIDE the region (`open_pc`'s
    matching `LOOP`/`BRANCH` ... `END`) could resolve to -- a cell-only
    resolution (`_resolve_cells`, ignoring amounts/`use_channels`, which
    govern whether a VERDICT is decidable, not which cell a guard names).
    Used by `check/__init__.py`'s region-entry/tail widen (V4) exactly as
    `tipstate.region_receivers` is used for the tip family's own widen.
    `poisoned` is conservatively `False` here (a coarse, region-wide scan
    has no single call's poisoning state) -- the worst case is widening
    fewer cells than an ideal per-call scan would, never more, which stays
    on the safe (widen, not narrow) side of V4's own crude-widen argument.
    """
    depth = 1
    pc = open_pc + 1
    n = len(instructions)
    cells: set[Any] = set()
    while pc < n and depth > 0:
        instr = instructions[pc]
        if isinstance(instr, (ir.Loop, ir.Branch)):
            depth += 1
        elif isinstance(instr, ir.End):
            depth -= 1
            if depth == 0:
                break
        elif isinstance(instr, ir.Call) and instr.receiver_type is not None:
            contract = contracts.get(f"{instr.receiver_type}.{instr.method}")
            if contract is not None:
                rs = receiver_states.get(instr.receiver_type)
                channel_default_param = (rs or {}).get("channel_default_param", {})
                channel_kwarg = (rs or {}).get("channel_kwarg")
                for guard in contract.get("volume_guards", ()):
                    resolved = _resolve_cells(instr, guard, channel_default_param, channel_kwarg, poisoned=False)
                    if resolved is not None:
                        cells.update(resolved)
        pc += 1
    return frozenset(cells)
