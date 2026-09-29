---
title: 'plr-sema tip-effect derivation under PLR 1.0 TipTracker (recon for #5622)'
description: Why tip effects vanish at PLR 1.0 and the minimal derived rule set (backing-field alias, arg-classified helper following >=2 hops, constructor seeding) that recovers all 11 old channel_effects; _check_tip_racks_available needs a new observation key + D6 row
status: draft
task_id: 260929_plr-1.0-migration
date: '260929'
confidence: 'high on mechanics (source + dynamic probe); medium on design choices'
sources: 'PLR 1.0.0b1 786ac2c4e pylabrobot/legacy/{tip_tracker.py,liquid_handling/liquid_handler.py}; PLR 0.2.2 dd79c4c89 resources/tip_tracker.py; plr-sema/src/plr_sema/derive/receiver_state.py'
---
# plr-sema tip-effect derivation under PLR 1.0 TipTracker (recon for #5622)

Recon for backlog #5622 (branch `plr-sema-1.0-recovery`). Context: at PLR
1.0.0b1 every tip-state verdict is UNKNOWN; the pre-registered
characterisation (bathos run `fd63e9cd`, `outputs/plr-sema/plr10_char_260929/`)
measured 0 scope-SAFE operations (216 at dd79c4c89) with soundness intact.

> **Provenance.** Numbers marked *(exploratory)* come from un-preregistered
> prototype scripts under `outputs/plr10_tools/recon5622/` (not tracked). They
> show feasibility and shape only; the increment must re-measure under a
> bathos sidecar before any of them is cited.

## Why the effects vanished

- **Old scan** (`receiver_state.py` `_effects` :903, `_classify_write` :889):
  depth 0, only `ast.Assign` to `self.<state_field>` in the tracker method's own
  body; `None` -> NO_TIP, `self.<state field>` -> ambiguous, else HAS_TIP.
  Attribution to LiquidHandler methods is `compute_channel_bridge` (:1483) via
  the `self.head[c].<method>` dropped-call shape.
- **1.0 TipTracker** (`legacy/tip_tracker.py`): `_pending_tip` is a read-only
  property returning `self._carried` (holder-less) or the holder's tree child;
  `_tip` is a property whose setter writes `_before`. `add_tip` (:154) ->
  `_hold` (:74) -> `_put` (:80) -> `self._carried = tip` (:86); `remove_tip`
  (:167) is `_hold(None)`. Nothing non-test assigns `_pending_tip`/`_tip`.
- So "follow same-class property setters + helpers, **one level**" is NOT
  sufficient: setters are irrelevant, the path is **two helper hops**, and the
  written field `_carried` is not a state field.
- LiquidHandler still calls the tracker directly on `self.head[channel]`
  (`pick_up_tips` :761 `add_tip`, `drop_tips` :909 `remove_tip`), with the same
  commit/rollback pattern; the 96-head variants use `head96` and had no
  `channel_effect` at the old pin either.

## Minimal derived rule set (no hand-typed tables)

- **R-A backing-field alias:** write targets = state fields ∪ every field `X`
  that a state-field property getter returns as bare `return self.X`. At 1.0
  that is exactly `{_carried}`. Must NOT alias `_before` (would make `commit`
  HAS_TIP).
- **R-B helper following with argument classification:** for same-class
  `self.<h>(args)`, classify args (`None` -> NO_TIP, `self.<state field>` ->
  ambiguous, bound caller name -> inherited, else HAS_TIP), bind to callee
  params, collect callee writes to R-A targets, recurse with a call-stack cycle
  guard (pattern at `receiver_state.py:686`). Depth >= 2, preferably unbounded.
  Follow only calls with >= 1 argument: following zero-arg `self.commit()`
  poisons `add_tip`/`remove_tip` at the OLD pin *(exploratory)*.
- **R-C entry reset:** seed `_constructor_state` with the backing fields; 1.0
  `__init__` `self._carried = None` restores `entry_reset = {setup, no_tip}`.
- **R-D hygiene:** don't publish underscore-private helpers (`_hold`, `_put`) in
  `effects`.
- **No resource-tree modelling needed:** every `head`/`head96` tracker is built
  holder-less (`liquid_handler.py:418, 421, 469, 476`); `_put`'s tree branch has
  the same polarity anyway.
- *(exploratory)* R-A + unbounded R-B + R-C recovers **11/11** old-pin
  `channel_effect` values exactly (pick_up_tips HAS_TIP, drop_tips NO_TIP,
  load_state HAS_TIP, 8 `widen`), contract table otherwise identical; one-hop
  recovers 1/11; no alias recovers 0; the unpatched re-run reproduces the
  committed 1.0 table (negative control).
- **Atomicity:** effects and `entry_reset` must land together. Entry reset
  without `add_tip`/`remove_tip` effects would judge a repeated `pick_up_tips`
  SAFE against NO_TIP (reasoned from `tipstate.py:586`, not run).

## `_check_tip_racks_available` (`liquid_handler.py:332-338`)

Raises `ValueError` when a rack behind the tip spots has a lid or is not the
top of a z-`ResourceStack` (`TipRack._available_for_tip_handling`,
`resources/tip_rack.py:355-363`). Called in `pick_up_tips` :721, `drop_tips`
:872, `pick_up_tips96` :1706, `drop_tips96` :1787. It is already a derived
depth-1 guard, but its predicate is `Not(Opaque(...))`, which is
`guard_predicate_unparsed` and therefore always UNKNOWN. It does **not** map onto the existing
deck-membership rule: the wire has no children/lid field. Smallest decidable
shape, mirroring D6:

1. one new closed observation key (the harness asserts that every TipRack on the
   observed deck is `_available_for_tip_handling`), touching `test_cache` and
   `training/tests/test_verify_postconditions.py`;
2. a fourth `D6_SITE_RULES` row
   `("_check_tip_racks_available", "ValueError", "not rack._available_for_tip_handling")`
   that returns False only;
3. HM-26 goes 3 -> 4 (registry, `test_check_graph`, ratchet).

**Soundness caveat:** a deck-build fact doesn't cover a later `move_lid` /
`move_plate` / `move_resource`. Either add a "no move-family call in the
sequence" conjunct or state the assumption. Without this rule tip ops cannot
reach SAFE even after the effects are recovered.

## Drift tests (no hand-listed methods)

1. A cross-pin baseline fixture of `{Class.method: channel_effect}` from the
   old-pin artifact, generated by a committed script with `--rebase`. A key
   still present must keep its value, and a vanished key fails.
2. Structural checks: `effects` has both a HAS_TIP and a NO_TIP entry; a present
   `entry_reset` implies non-empty `effects`; the `tip_dropping`/`tip_loading`
   families are non-empty. Optionally publish `effects_unresolved`.
3. A behavioural oracle: drive the public tracker methods on a holder-less
   TipTracker and compare has_tip before/after with the derived polarity.
   Import `pylabrobot.resources` before `pylabrobot.legacy.tip_tracker`
   (circular import otherwise).
4. Synthetic derivation controls. Positive: an `add -> _hold -> _put -> _carried`
   chain derives an effect. Negatives: a zero-arg ambiguous helper must not
   poison its caller, a `_before`-style store must not alias, and a no-write
   tracker gives `{}`.

## Other things that will bite

- **A spurious `receiver_state["TipTracker"]` receiver, new at 1.0.**
  `self._carried: Optional["Tip"]` types to `Tip`, and `Tip.has_collar_height`
  is anchor-shaped. It is harmless unless a call has
  `receiver_type == "TipTracker"`.
- **`load_state` HAS_TIP parity reproduces an old unsoundness.**
  `load_state({tip: None, ...})` leaves no tip at runtime. The options are
  parity plus a ticket, or classifying conditional-None locals as ambiguous.
- **No change:** `rollback` (now `raise RuntimeError`, never bridged), volume
  tracking (`volume_guards` identical, the VolumeTracker callback is intact),
  the tip exceptions (`HasTipError`/`NoTipError`), and the deprecation paths
  (no control-flow effect).
- **Possible harness leak:** the module-level `_spot_trackers` dict keyed by
  `id(spot)` could leak state across rows if spots are ever reused. This is
  reasoned from source, not observed.

## Decisions for the increment spec

1. `load_state`: keep parity or fix it.
2. Whether to suppress the spurious `TipTracker` receiver.
3. The `:338` rule: whether to add the move-family conjunct or state the
   assumption.
4. Helper-following depth: unbounded (recommended) or a fixed bound.

