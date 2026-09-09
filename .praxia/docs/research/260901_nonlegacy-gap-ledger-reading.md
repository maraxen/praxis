---
title: 'plr-sema T14: upstream_nonlegacy gap-ledger reading'
description: 'Gap-ledger reading for the upstream_nonlegacy PLR surface (driver layer, no orchestration): guard-dense families, closure termination, unresolved frontier, dropped-receiver worklist, and the self-containment hypothesis measured directly.'
status: final
task_id: 260901_plr-jit-t14-nonlegacy-product
date: '260901'
confidence: ''
sources: ''
---
# plr-sema T14: upstream_nonlegacy gap-ledger reading

Reads `plr-sema/data/gap_ledger.upstream_nonlegacy.json` and
`plr-sema/data/derived_contracts.upstream_nonlegacy.json` (T13,
`upstream_nonlegacy` surface, pin `3a50a567f`) and the family/depth
cross-tabulations computed by
`plr-sema/scripts/nonlegacy_gap_ledger_reading.py`. Companion to T6's legacy
gap-ledger reading -- same questions, different (driver-layer, no
orchestration) surface. Regenerate the two source artifacts with:

```
uv run python -m plr_sema.derive \
    --survey-json training/verify/data/plr_preconditions.upstream_nonlegacy.json \
    --out plr-sema/data/derived_contracts.upstream_nonlegacy.json \
    --gap-ledger plr-sema/data/gap_ledger.upstream_nonlegacy.json \
    --plr-root <freshly re-extracted upstream_nonlegacy tree> \
    --surface-name upstream_nonlegacy \
    --surface-pin 3a50a567fe537d3a7b8ecdc84858191ee3c19637
```

**The `--plr-root` extraction is not reproducible from a stale directory.**
T13's own extraction (`git archive <sha> | tar -x` into a temp dir, since
the pin predates the `legacy/` restructure and has no `.git` of its own) no
longer exists on disk -- confirmed gone this session. It IS re-derivable
without network access, because `3a50a567f` is an ANCESTOR commit of the
live `external/pylabrobot` submodule's checked-out history:

```
git -C external/pylabrobot archive 3a50a567fe537d3a7b8ecdc84858191ee3c19637 \
    | tar -x -C <fresh tmp dir>
```

A future regeneration that doesn't know this will either fail outright or
(worse) silently substitute a wrong `--plr-root`. This is a real
reproducibility gap in the T13 artifact, out of T14's scope to fix in the
pipeline itself (the fix, if wanted, is a committed extraction script or a
recorded provenance note next to the pin literal), flagged here rather than
worked around.

## Headline facts (T13, restated)

| metric | legacy_pinned | upstream_nonlegacy |
|---|---|---|
| functions scanned | 4,770 | 3,677 |
| finding-bearing | 1,314 | 1,021 |
| contracts with guards (whole pop.) | 1,894 | 1,724 |
| contracts with gaps (whole pop.) | 1,062 | 199 |
| `unresolved_delegate` (finding-bearing closure pop.) | 610 | 158 |
| `LiquidHandler` present | yes | **no** |

`upstream_nonlegacy` has no orchestration layer at all: `machines/` is a
bare `__init__.py`, and `LiquidHandler` exists only under `legacy/` (which
this pin predates entirely -- confirmed: zero `LiquidHandler.*` keys in the
contract table, pinned by
`tests/test_check_graph_nonlegacy.py::test_liquid_handler_is_genuinely_absent_from_this_surface`).
Every `supported_tools`-scoped ledger field is therefore structurally 0/False,
not "0 gaps measured" -- `liquid_handler_present: false` is the flag that
tells the two apart, and it must keep degrading loudly (T13's own fix; T14
adds nothing new here, only relies on it).

## Which families are guard-dense

Every finding-bearing method's own contract carries >=1 guard **by
construction** (a method's own `PreconditionFinding`s always enter its own
contract at depth 0) -- so "guard-dense" cannot mean "has >=1 guard" (that's
100% for every family, vacuously) and must instead mean **volume**: how many
finding-bearing methods a family contributes, and what share of those also
carry a recorded gap. Top 10 by finding-bearing count (of 1,021 total, whole
`pylabrobot.*` top-level package):

| family | finding-bearing | with gaps | gap rate |
|---|---|---|---|
| resources | 184 | 21 | 11.4% |
| revvity | 160 | 16 | 10.0% |
| agilent | 135 | 2 | 1.5% |
| io | 106 | 2 | 1.9% |
| hamilton | 91 | 5 | 5.5% |
| high_res | 43 | 3 | 7.0% |
| brooks | 39 | 0 | 0% |
| azenta | 36 | 0 | 0% |
| molecular_devices | 26 | 1 | 3.8% |
| inheco | 20 | 1 | 5.0% |

`resources` and `revvity` are both the largest contributors AND carry the
highest gap rates -- not a coincidence given both are large, deeply
subclassed hierarchies (`resources` is PLR's whole labware/carrier type
tree; `revvity`'s `celigo` camera driver is one of the largest single-vendor
modules in the survey). `kbiosystems` and `thermo_fisher` (20 finding-bearing
methods each) have disproportionately high gap counts (12 and 13
respectively -- 60%+ gap rate) despite low volume; worth a follow-up look if
anyone extends this reading, not chased further here.

## Where the closure terminates

Guard-depth histogram over the whole finding-bearing population (depth 0 =
own body, depth *n* = inlined from *n* hops of `delegates_to`):

| depth | legacy_pinned | upstream_nonlegacy |
|---|---|---|
| 0 | 2,820 | 1,629 |
| 1 | 1,433 | 707 |
| 2 | 637 | 523 |
| 3 | 219 | 304 |
| 4 | 46 | 144 |
| 5 | 21 | 60 |
| 6 | 3 | 14 |
| 7 | 1 | 1 |

Both surfaces decay geometrically from depth 0, and both bottom out by depth
7 -- closures terminate quickly on both surfaces; there is no meaningful
"legacy's closures just go deeper" effect that would by itself explain a
5x gap-count difference. (`upstream_nonlegacy`'s depth-2/depth-1 ratio,
0.74, is actually slightly SLOWER-decaying than legacy's 0.44 -- once a
non-legacy closure starts delegating, it keeps delegating for a few more
hops on average, if anything.) See "does the self-containment story hold,"
below, for what actually explains the gap-count gap.

## What dominates the unresolved frontier

`top_unresolved.whole_surface` (own-body `unresolved_calls`, 84 distinct
names, 1,021-method population) is headed by:

| call | blocks_methods |
|---|---|
| `send_command` | 21 |
| `validate_payload_length` | 16 |
| `wait_for_idle` | 16 |
| `assign_child_resource` | 12 |
| `set_temperature` | 10 |
| `get_all_items` | 9 |
| `get_resource` | 9 |

No single name dominates the way `send_command` reportedly dominates
legacy's whole-surface unresolved-call population (published as ~78% of
call-node instances there) -- here the top name blocks only 21/1,021 (2.1%)
of methods. The frontier is genuinely spread across transport
(`send_command`, `validate_payload_length`, `wait_for_idle`) and
resource-tree (`assign_child_resource`, `get_all_items`, `get_resource`)
concerns, not concentrated in one call.

## The ranked deferred-item-(e) worklist for this surface

**The existing closure-based worklist (`top_unresolved.dropped_receiver` /
`_unfiltered`) is vacuously empty here, not just small.** Both are built by
walking `delegates_to` closures FROM the `SUPPORTED_TOOLS`/`LiquidHandler`
entry-point set (`_dropped_receiver_worklist_from_survey`); with
`liquid_handler_present is False`, that entry-point set is empty, so both
views return `[]` unconditionally, regardless of how much real
dropped-receiver content this surface's methods actually contain (measured:
607 of 1,021 finding-bearing methods have >=1 dropped call). This is a
silently-vacuous-not-just-small artifact of exactly the class T13/T14's
`liquid_handler_present` flag exists to name -- pinned as a permanent
regression test
(`test_derive.py::test_closure_based_dropped_receiver_views_are_vacuous_on_nonlegacy`).

**Fix shipped this task: `top_unresolved.dropped_receiver_whole_surface` /
`_unfiltered`** (`plr_sema.derive._dropped_receiver_worklist_whole_surface`,
wired into `build_gap_ledger`, both artifacts regenerated additively). Ranks
`dropped_calls` directly over each finding-bearing record's OWN body --
no closure walk, because a surface with no orchestration layer has no
principled notion of "entry point" to walk a closure FROM in the first
place; every driver method is potentially its own caller. Published on
BOTH surfaces (not gated on `liquid_handler_present`), alongside, not
instead of, the closure-based pair -- the two rank different populations
and neither is a strict superset of the other.

Top 12, filtered (`upstream_nonlegacy`):

| call | blocks_methods |
|---|---|
| `asyncio.sleep` | 64 |
| `self.cr.next_command` | 36 |
| `asyncio.get_running_loop` | 29 |
| `time.time` | 29 |
| `capturer.record` | 23 |
| `time.monotonic` | 20 |
| `super().__init__` | 19 |
| `self.io.read` | 18 |
| `loop.run_in_executor` | 17 |
| `bytes.fromhex` | 16 |
| `self._driver.send_command` | 15 |
| `super().assign_child_resource` | 15 |

**The shape is genuinely different from legacy's -- and NOT for the reason
the T14 brief anticipated.** Legacy's headline `dropped_receiver` (the
closure-based, SUPPORTED_TOOLS-scoped view) is dominated by
`self.head[channel].get_tip` (`blocks_methods: 3` at round-5, a small but
concentrated population) because it walks ONLY the 10 tool entry points'
closures -- a narrow, orchestration-scoped lens that isolates tip-state
signal specifically. There is no equivalent lens available here (no entry
points to scope to), so the only non-vacuous worklist for this surface is
the broad own-body view above -- and that same broad view, computed over
LEGACY's own finding-bearing population too (also shipped this task, for
comparison), turns out to have an ALMOST IDENTICAL top-12 shape
(`asyncio.sleep` 57, `time.time` 44, `self.cr.next_command` 34, `super().
__init__` 25, `self.io.write` 19, `bytes.fromhex` 18, ...). **This is
because most of legacy's own 4,770-function survey is the SAME KIND of
device-driver code `upstream_nonlegacy` is entirely made of** -- the
orchestration layer (`LiquidHandler`, `TipTracker`, ...) is a small core
sitting on top of a much larger body of per-vendor driver modules shared
between both trees. The real difference this worklist exposes is not "what
does nonlegacy drop that legacy doesn't" (answer: almost nothing, at the
own-body level) but **"which lens is even available"** -- legacy has BOTH a
narrow, orchestration-scoped lens (tip state) AND this broad one; nonlegacy
has only the broad one, because it has no orchestration layer to scope a
narrow lens to. That absence of a scoping mechanism -- not a different
content shape -- is the finding.

Read past the noise, the real receiver-typestate candidates in
`upstream_nonlegacy`'s own-body worklist are `self.cr.next_command` (36),
`self.io.read`/`self.io.write`/`self.io.setup` (18/14/9), and
`self._driver.send_command` (15) -- device I/O and command/response-cycle
state, the driver-layer analogue of legacy's tip state. `super().__init__`
/ `super().assign_child_resource` (19/15) are a separate, genuine open
question (see "inert-name filtering," below), not noise.

## Inert-name filtering applied, and what was deliberately NOT filtered

**No new hand-typed filter table was introduced.** The existing
`_is_inert_dropped_receiver_call` predicate (`_INERT_RECEIVER_PREFIXES` +
`_INERT_CALL_SUFFIXES`, round-5 T0) was reused as-is for the new
`dropped_receiver_whole_surface` view -- it still removes `logger.*` calls
here, and its removal is real (confirmed: the unfiltered ranking's top row
IS `logger.info` at 93/1,021 blocked methods; the filtered ranking has none).

**But the driver layer's dominant noise source is DIFFERENT from what that
filter was tuned against, and the filter does not catch it.** The
orchestration-layer `_check_args` closure that motivated the existing
filter saturates on `logger`/`inspect`/`warnings`/`args` -- effectively 100%
of that (narrow) population, which is why filtering was load-bearing there.
Nothing in this surface's own-body population saturates that way (the
highest unfiltered entry, `logger.info`, blocks only 93/1,021 = 9.1% of
methods -- nowhere near the ~100% saturation the round-5 filter was built
to fix). Instead the top of the FILTERED ranking is still dominated by
stdlib async/timing/serialization plumbing the existing filter tables don't
name: `asyncio.sleep`/`asyncio.get_running_loop`/`asyncio.wait_for`/
`asyncio.shield`, `time.time`/`time.monotonic`/`loop.time`, `struct.pack`/
`struct.unpack`, `bytes.fromhex`, `contextlib.suppress`. None of these carry
PLR receiver-typestate signal any more than `logger.debug` does.

**Deliberately not filtered further this task**, for two reasons stated
plainly rather than worked around: (1) `_hand_maintained.py`'s ratchet has
only 2 rows of headroom under its cap (22 live rows, cap 24, per T9/T13),
and the two existing inert-filter tables are not even themselves registered
in that ratchet (a pre-existing gap, not introduced here) -- adding a THIRD
hand-typed list to chase this surface's own noise profile would compound,
not fix, that gap, and risks the exact cap-arithmetic mistake trap 3 warns
against; (2) the boundary between "stdlib plumbing" and "real signal" is
genuinely ambiguous for two of the top rows: `super().__init__` and
`super().assign_child_resource` route THROUGH a superclass but ultimately
act on `self`'s own instance -- filtering them as noise would hide a real
phenomenon (constructor/method preconditions that only become visible
through inheritance, invisible to a `self.<name>` receiver check by
construction) rather than remove noise. Recommendation for a follow-up
task, not done here: a `_STDLIB_MODULE_HEADS` predicate (a set of literal
stdlib module names -- `asyncio`, `time`, `struct`, `bytes`, `contextlib`,
`re`, `os`) is defensible on the same "this can never be PLR receiver
state" logic the existing `_INERT_RECEIVER_PREFIXES` list already uses for
`logger`/`warnings`/`inspect`, but needs its own registry row and cap
argument, which is exactly the kind of change trap 3 says to stop and
report rather than push through unilaterally.

## Does "driver code is more self-contained" actually hold?

**Yes, but for a narrower and more specific reason than "delegates less."**
Measured directly, not assumed:

1. **Bare-delegate-name resolution (`resolve()`) never fails on EITHER
   surface.** `no_contract_derived` is 0/1,062 gap-instances on legacy and
   0/384 on `upstream_nonlegacy`, at whole-population scale -- every single
   name appearing in `delegates_to` resolves to a real class-method or
   module-level function in the SAME module on both surfaces (1,007/1,007
   legacy, 860/860 nonlegacy). **100% of every measured gap on both
   surfaces is `unresolved_delegate`** (a call whose callee expression the
   survey's own AST recording rule could not reduce to a bare name at all)
   -- never a resolvable name pointing nowhere. This was not previously
   stated this plainly anywhere the recon for this task found; worth
   folding into the spec's own RISK-1 discussion if a future round touches
   it.
2. **Own-body `unresolved_calls` rate per finding-bearing method is
   genuinely lower on `upstream_nonlegacy`**: 0.114/method vs legacy's
   0.238/method (~2.1x), and the fraction of methods with >=1 such call is
   0.060 vs 0.181 (~3.0x) -- both measured directly from the committed
   survey JSON, not inferred from the gap ledger.
3. `delegates_to` rate per method is NOT lower on nonlegacy (0.842 vs
   0.766 -- if anything slightly HIGHER), and `dropped_calls` rate is
   comparable (1.693 vs 1.543). **The driver layer does not call fewer
   things or delegate less often.** What differs is the SHAPE of the calls
   it makes: driver methods more often call through an expression the
   survey's AST pass CAN reduce to a bare name (landing in `delegates_to`
   or `dropped_calls`, both of which the closure/report can still reason
   about, if not always resolve) rather than one it cannot name at all
   (`unresolved_calls`, the sole source of every gap on both surfaces).
4. Closure depth-decay shape is comparable between surfaces (see "where the
   closure terminates," above) -- the ~5x whole-population gap-count gap
   (199 vs 1,062) is NOT primarily a depth/reach effect. It is the
   per-method `unresolved_calls`-rate difference (~2-3x) compounding
   across a closure structure of similar shape, amplified by the modest
   population-size difference (1,021 vs 1,314 finding-bearing, 1.29x) --
   consistent, not a coincidence, but a narrower mechanism than "delegates
   less."

**Verdict: the explanation in the task brief is directionally correct but
imprecise as originally stated.** "Driver code is more self-contained than
orchestration code that delegates across classes" reads as being about
delegation FREQUENCY or reach; the actual, measured mechanism is about
delegation-expression NAMEABILITY -- driver code's calls are more often
syntactically simple enough for the survey's own AST rule to give them a
bare name in the first place, not that driver code avoids calling out of
its own body.

## Sources / regeneration

- `plr-sema/data/gap_ledger.upstream_nonlegacy.json`,
  `plr-sema/data/derived_contracts.upstream_nonlegacy.json` -- regenerated
  260901 (T14), additive-only diff against the T13-shipped versions (new
  `top_unresolved.dropped_receiver_whole_surface`/`_unfiltered` keys; no
  other field changed except the `stamp.praxis` git-state fields, which
  always move with the committing checkout).
- `plr-sema/scripts/nonlegacy_gap_ledger_reading.py` -- the family-breakdown,
  depth-histogram, and self-containment measurements above (not published
  in the shipped ledger's normative schema; run it directly to reproduce or
  extend).
- `plr-sema/tests/test_check_graph_nonlegacy.py`,
  `plr-sema/tests/test_derive.py` (T14 additions) -- the permanent
  regression coverage backing every claim above about the ledger's shape.
