---
title: 'plr-sema families/cache increment — adversarial round 1, challenger'
description: 'Challenger report on .praxia/docs/specs/260903_plr-sema-families-cache-increment.md (spec_version 12 draft, b89de024): O1 BLOCKER the volume bridge rule does not match LiquidHandler.aspirate at the pin (op is a for-loop variable over the comprehension output, not a P8 comprehension target; Container.tracker is an unannotated Assign P1a cannot see); O2 BLOCKER the does_volume_tracking() env gate cannot reach a bridged guard (scope_trail comes from the callee record, not the caller scope) so AC-13.11 fails and default-env WILL_FAIL is unsound; O3 MAJOR is_disabled is a per-instance property, not a zero-arg call; O4 BLOCKER V0/V2 interval update order unspecified -- two channels on one well in a single call would get a false SAFE under a simultaneous reading (PLR is sequential); O5 MAJOR cache read-through hooked in _check which never sees the contracts string; O6 MINOR inert-name alias resolution needs per-file context. Cache, inert filter, and P9 transfer binding held. Verdict: not implementable until §13.2.4/§13.2.6 are rewritten and measured.'
status: final
task_id: 260903_sema-followups
date: '260903'
confidence: high
sources: 'praxia:spec-challenger (claude-sonnet-5). Spec read in full (1489 lines); plr-sema/src/plr_sema/check/ir.py (full); check/__init__.py (full); derive/receiver_state.py (full); derive/__init__.py:840-960; _hand_maintained.py:1-90,244-290,770-870; verdict.py:100-164; tests/test_hand_maintained_ratchet.py:271-352; PLR at pin dd79c4c89: liquid_handling/liquid_handler.py:960-1120,1273-1372, resources/volume_tracker.py (full), resources/lid.py (full), resources/container.py:1-95, liquid_handling/standard.py:1-90; training/verify/data/plr_preconditions.json:49700-49869,96961-97012; plr-sema/data/derived_contracts.json:159895-159934. Persisted verbatim by the orchestrator: the challenger agent type has no write tool.'
---
# plr-sema families/cache increment — adversarial round 1, challenger

Target: `.praxia/docs/specs/260903_plr-sema-families-cache-increment.md` at `b89de024`. Verbatim report.

---

## Objections

### O1 — BLOCKER — the volume bridge (§13.2.4) cannot derive on the real PLR source it claims to derive on

**Location.** §13.2.4, the "Normative (the volume bridge, a second HM-24 pattern)" box; measured expectation immediately following it; AC-13.9(i).

**Issue.** The rule matches a `dropped_calls` entry of shape `<name>.<field>.<attr>.<method>` where `<name>` must be **"a comprehension target of a P8 match in `K`"**, and `<attr>` must be sent to a P7-anchored class `C` by **"`R`'s P1a map (or the element class `O`'s)"**. Applied to the spec's own worked example, `op.resource.tracker.remove_liquid` in `LiquidHandler.aspirate`, neither condition holds:

1. `<name> = "op"`. P8's comprehension targets for `aspirate` are the `zip`-bound names `r, v, o, fr, lh, t, bav, m` (`liquid_handler.py:1007-1028`). `op` is not one of them — it is the loop variable of a **separate** `for op in aspirations:` statement (`:1031`) that iterates the comprehension's *output list*, not a name bound inside the comprehension. `op` is not "a comprehension target of a P8 match" under any literal reading of P8's own definition (§13.2.4's P8 box: "Record ... the pair `(O.k → aᵢ)`" where `aᵢ` is a zip element — `op` is never a zip element here).
2. `<attr> = "tracker"`. Neither `LiquidHandler` (`R`) nor `SingleChannelAspiration` (`O`) types a `tracker` attribute. `SingleChannelAspiration` is `@dataclass(frozen=True)` with **class-level bare-name annotations** (`resource: Container`, `standard.py:52-60`) — P1a's `_annotated_attributes` (`receiver_state.py:170-181`) only matches `ast.AnnAssign` whose *target* is `self.<name>` (`_is_self_attr`, `:164-167`); a class-level `resource: Container` has target `ast.Name("resource")`, which fails `_is_self_attr` outright. Even generously walking one more hop — `O.resource : Container`, then `Container.tracker` — fails too: `Container.__init__` sets `self.tracker = VolumeTracker(...)` as a **plain `ast.Assign`, not `ast.AnnAssign`** (`container.py:85`), which P1a cannot see under any reading, since P1a is defined only over annotated assignments.

**Evidence.**
- `plr-sema/src/plr_sema/derive/receiver_state.py:295-322` (P8, comprehension targets are the zip names).
- `plr-sema/src/plr_sema/derive/receiver_state.py:170-181,164-167` (P1a, `AnnAssign` + `self.<name>` only).
- `external/pylabrobot/pylabrobot/liquid_handling/standard.py:52-60` (`SingleChannelAspiration`'s bare class-level field annotations).
- `external/pylabrobot/pylabrobot/resources/container.py:85` (`self.tracker = VolumeTracker(...)`, unannotated).
- `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:1007-1035` (the actual `op`-over-`aspirations` for-loop, not a comprehension).

**Counterexample.** A literal implementation of the normative box, run against the pin this document itself cites, produces **zero** matches for `op.resource.tracker.remove_liquid` / `op.tip.tracker.add_liquid` / `op.resource.tracker.add_liquid` / `op.tip.tracker.remove_liquid` — i.e. no `volume_guards` block is emitted for `LiquidHandler.aspirate` or `dispense` at all. AC-13.9(i)'s "measured expectation" (`cell_param: "resources"`, `amount_param: "vols"`, two entries) cannot be reproduced; §13.0's headline deliverable (`WILL_FAIL` at `VolumeTracker.remove_liquid` for a 200µL draw against a 100µL seed) never fires; AC-13.10(a) fails.

**What must change.** The volume-bridge box needs two independent extensions, stated normatively rather than left to a fixer's discretion: (a) a second `<name>`-binding mode — a bare `ast.Name` bound by a `for` loop whose iterable is a P8 match's own list-comprehension target — with a defined rule for what happens when more than one such for-loop exists; (b) a two-hop attribute-type resolution (`O.<field>`'s own type, then *that* type's own attribute) reachable even when the intermediate write is an unannotated `ast.Assign`, since P1a as it exists today structurally cannot see `Container.tracker`. Both need their own measured/published expectation, the same discipline §13.2.4 already demands of P7/P8.

---

### O2 — BLOCKER — the `env`/`does_volume_tracking()` gate (§13.2.6) cannot reach the bridged guard the mechanism is built to gate

**Location.** §13.2.6 normative box ("the env argument"); AC-13.11; the volume-bridge box in §13.2.4 (same mechanism O1 attacks, different failure mode).

**Issue.** §13.2.6 assumes the bridged guard's `scope_trail`/`condition` will mention `does_volume_tracking()` so the evaluator has something to gate `env` against. The bridging mechanism this spec specifies explicitly "mirrors" `compute_channel_bridge` (§10.2.6's precedent), which pulls a bridged guard's `scope_trail` from **the callee's own survey record** (`receiver_state.py:780-796`: `"scope_trail": list(guard.scope_trail)`, sourced from `derive_contract(tracker_module, f"{tracker_class}.{method}", ...)`), never from the caller's enclosing `if` scope. I read `VolumeTracker.remove_liquid`'s own survey record directly:

```
"scope_trail": ["if volume - self.get_used_volume() > 1e-06"]
```

(`training/verify/data/plr_preconditions.json:96975-96977`) — it names only its own guard condition, not `does_volume_tracking()` or `is_disabled`. Those two conjuncts live in `LiquidHandler.aspirate`'s own body, one syntactic level above the dropped call (`liquid_handler.py:1032-1035`), and nothing in §13.2.4's bridge box threads that context onto the bridged guard the way it would for a *resolved* `delegates_to` chain (where the delegate's own survey record already carries the accumulated scope, which is why `dispense`'s inherited `BlowOutVolumeError` guard on `transfer` legitimately does carry `"if does_volume_tracking()"` — that guard is a **direct finding of `dispense`'s own body**, reached through a resolved delegate, not a bridge through an unresolved `dropped_calls` entry).

**Counterexample.** Given the bridge as specified, the volume guard landing on `aspirate`'s contract entry has `condition = "volume - self.get_used_volume() > 1e-06"`, `scope_trail = ["if volume - self.get_used_volume() > 1e-06"]` — no mention of `does_volume_tracking` anywhere. §13.2.6's normative rule ("a volume guard whose scope_trail or condition mentions a zero-argument call f() ... is conditional on f") finds no such call and therefore never marks the guard conditional. Run with the **default** `env = frozenset()` on AC-13.11's own fixture (a) (seed 100, `aspirate(vols=[200])`), the guard's `Cmp` evaluates `T` and — with nothing gating it — the analyzer emits `WILL_FAIL` unconditionally, contradicting AC-13.11's requirement that the default-`env` run yields `UNKNOWN`/`volume_tracking_unasserted`. This is a live, unshipped soundness bug: `WILL_FAIL` would be claimed for a protocol run in which tracking might never have been on and the guard body never executed.

**What must change.** The bridge box must specify how the *caller's* enclosing scope (not the callee's) reaches a bridged guard's `scope_trail` — e.g. accumulate `aspirate`'s own `if does_volume_tracking(): if not ...is_disabled:` nesting onto the bridged entry at derivation time, keyed off the actual textual site of the dropped call inside `aspirate`'s body (which the precondition survey does not currently record for `dropped_calls`, per the flat-string shape confirmed at `plr_preconditions.json:49766-49772`). Until that's specified and measured, AC-13.11 cannot be satisfied by a literal reading of §13.2.4+§13.2.6 together.

---

### O3 — MAJOR — A-TRACKER-ENABLED's discharge mechanism is claimed but not defined: `is_disabled` is not a "zero-argument call"

**Location.** §13.2.6, closing paragraph ("`f`'s other live instance is `not op.resource.tracker.is_disabled`..."); §13.2.7's A-TRACKER-ENABLED row.

**Issue.** The §13.2.6 normative box gates only "a zero-argument call `f()`". `not op.resource.tracker.is_disabled` is a `UnaryOp(Not, Attribute(...))` over a **per-instance property** (`VolumeTracker.is_disabled`, `volume_tracker.py:54-56`) — not a call, and not something with a "name" that can be looked up in `env` the way `does_volume_tracking` can (the harness observes `env` by *calling* a module-level function, §13.2.6's own text — there is no analogous zero-arg callable to call for a per-instance flag). The prose asserts "it is handled by the same rule" without the normative box actually covering it. This is independent of O2: even if O2's scope-threading gap were fixed so this conjunct reached the guard's `scope_trail`, the mechanism as written has no defined behavior for it (permanently unparseable → safe-but-silently-wrong UNKNOWN? Or silently ignored → the exact unsoundness A-TRACKER-ENABLED's own "what breaks if false" column names?).

**What must change.** Either generalize the env rule to cover arbitrary unrecognized boolean conjuncts in scope_trail (not just zero-arg calls), with a stated default (fail-closed: any unrecognized conjunct blocks `WILL_FAIL`), or specify a second, distinct mechanism for per-instance flags and say so explicitly rather than folding it into "the same rule."

---

### O4 — BLOCKER (soundness, untested) — V0/V2's interval update order is unspecified for two channels drawing from one cell in a single operation

**Location.** §13.2.5 V0 ("pairing") and V2 ("exact transfer"); the guard-evaluation table.

**Issue.** PLR explicitly supports (and auto-expands) a single well being aspirated by multiple channels in one call: `liquid_handling/liquid_handler.py:994-999` — "If the user specified a single resource, but multiple channels to use, we will assume they want to space the channels evenly across the resource," setting `resources = [resource] * len(use_channels)`. PLR then processes each paired `op` **sequentially** in `for op in aspirations: ... op.resource.tracker.remove_liquid(op.volume)` (`:1031-1035`), and `remove_liquid` mutates `pending_volume` immediately (`volume_tracker.py:96`), so the second channel's guard, in real execution, is checked against the **already-decremented** volume from the first channel's draw.

V0 does not exclude a `Seq` containing the same `Ref` twice; V2's "For each paired `(cell, a)` with pre-state `[lo, hi]`" does not say whether "pre-state" is the interval **before this whole operation** (all pairs evaluated/transitioned independently against one shared snapshot — simultaneous semantics) or threaded pair-by-pair (sequential semantics matching PLR). V1 ("Guards are evaluated against the pre-state, then the post-state is computed") reads as simultaneous: evaluate every guard first, transition after — which would let two channels drawing from the same well each pass their guard against the *full* pre-operation interval even when their combined draw exceeds it, producing a **false SAFE** (an unsound verdict in exactly the direction the "0 unsound" gates exist to catch).

**Counterexample.** Well seeded to 100µL; `aspirate(resources=[well, well], vols=[60, 60], use_channels=[0,1])`. Real PLR: channel 0 draws 60 (pending 40 left), channel 1's guard checks `60 - 40 > 1e-6` → **raises** `TooLittleLiquidError`. Under a simultaneous reading of V0/V2, both channels' guards are checked against the same `[100,100]` pre-state (`60 - 100 <= 1e-6` for both) → the analyzer would emit `SAFE` for both — an unsound `SAFE` where the real run raises.

**Evidence.** No AC (AC-13.9–13.13) or fixture in §13.2.9's tier-3/tier-2b set exercises a duplicate-cell pairing; all named fixtures are single-channel.

**What must change.** V2 must state explicitly whether pairs are applied against a running (sequential) state or a shared snapshot, and — given real PLR is sequential within one `aspirate`/`dispense` call — the sequential reading is the only sound one; a dedicated fixture (two channels, same well, cumulative over-draw only on the second) must be added to close the gap AC-13.9–13.13 currently leave open.

---

### O5 — MAJOR — the cache's read-through hook is assigned to the wrong function for the data it needs

**Location.** §13.9's #4922 task row ("read-through in `_check` behind `check_graph`'s new keyword-only `cache=None`"); §13.3.2's normative purity/key box.

**Issue.** `cache_key` needs the **raw `contracts_json` string** to compute `contracts_sha` (`ir.py:918-932`, `hashlib.sha256(contracts_json.encode(...))`). `_check` (`check/__init__.py:686-710`) receives only `contracts_payload: dict[str, Any]` — an already-`json.loads`'d object — never the original string. `check_graph` (`:713-733`) is the only function with the raw string in scope. Hooking the read-through inside `_check`, as the task row literally says, either requires threading the raw string down as a new parameter (an unstated signature change to `_check`) or re-serializing `contracts_payload` back to JSON inside `_check` — which is not guaranteed byte-identical to the original file (key ordering/whitespace/float repr), risking a `contracts_sha` that silently diverges from a previously-cached entry's key even when the semantic content is unchanged, which would only cause extra misses (safe) but contradicts the "hit equals a miss" AC-13.5 test design's implicit assumption of a stable, deterministic key across repeated runs against the same file.

**What must change.** State explicitly that the cache lookup happens in `check_graph`, using the `contracts_json` parameter already in its scope, before/around the call into `_check`'s pure body — not inside `_check` itself, which never sees the string.

---

### O6 — MINOR — §13.4.2's derived clause 1 needs per-record file context the existing predicate's signature doesn't carry

**Location.** §13.4.2, normative box ("the head is a module-level import alias resolving to such a member **in the file the dropped_calls entry came from**").

**Issue.** `_is_inert_dropped_receiver_call(call_expr: str) -> bool` (`derive/__init__.py:884-905`) takes only the bare call-expression string. Resolving an import alias "in the file the entry came from" requires the originating `SurveyRecord`'s `file`/`module`, which is available at the call sites (`_dropped_receiver_worklist_from_survey`/`_dropped_receiver_worklist_whole_surface` iterate `rec.dropped_calls` in the context of `rec`) but is not threaded into the predicate today. This is a natural, low-risk extension (pass `rec` or `rec.file` alongside `call_expr`), but the spec doesn't name the signature change, and #4883's task row lists `derive/__init__.py` generically without calling this out — a fixer who reads the normative box in isolation could reasonably build a global (file-independent) import-alias table instead of a per-file one, which is a materially different (and less correct, given aliasing can differ file-to-file) design.

**What must change.** State explicitly that `_is_inert_dropped_receiver_call` gains a `file`/`rec` parameter, or an equivalent, and that alias resolution is per-file.

---

## Adjudication of §13.13's open questions

1. **Per-row ceiling bumps (Q1).** The spec's *mechanical* claim is verified correct: `test_total_declared_within_budget` (`tests/test_hand_maintained_ratchet.py:344-352`) checks `len(live_rows()) <= BUDGET_CAP` — row *count* only, independent of any row's `declared` field — and `test_no_surface_exceeds_its_declared_size` (`:271-283`) enforces per-row ceilings separately. Increment 3 §12.1.2's "zero row headroom makes a sixth pattern a cap conversation" conflates the two, as this document argues. However, given O1/O2, the practical stakes of Q1 are smaller than framed: the HM-24/HM-25 bump exists to pay for P7/P8/the-volume-bridge and P9, and P7/P8/the-bridge do not currently derive anything on the real pin (O1) even if the ceiling is bumped. A reviewer holding the stricter line is not wrong on principle, but the more urgent blocker is that the patterns being paid for don't work yet, independent of what the ceiling says.
2. **Capacity asymmetry / sequencing vs #4922 (Q2).** The "cheap now, expensive later" argument for taking the capacity bump before #4922 populates a cache is weaker than presented: any `IR_VERSION` bump is already a cache-key component (§11.3.3, confirmed at `ir.py:918-939`), so a *future* capacity-operand bump would invalidate the whole cache exactly as completely as one taken now — there is no accumulated "populated cache" cost being avoided by sequencing correctly. This resolves Q2's "strongest argument against this document's own sequencing" as not actually load-bearing.
3. **`env` mechanism (Q3).** (a) is moot pending O2/O3: as specified, the mechanism does not reach the case it claims to gate, so "is it honest" cannot be answered until it is wired to fire at all. (b) is a legitimate, unresolved usability gap: a `WILL_FAIL` finding today carries no record of which hypothesis it rested on. (c) — should A-TRACKER-ENABLED use the same mechanism — O3 shows the "same rule" claim doesn't hold on the current text; this needs a real answer, not a deferral.
4. **Lid non-adoption / #4881a (Q4).** AC-13.4's `null`-condition-is-not-unconditional-failure assertion is a genuine regression guard with real future value (the landmine is real and independently verified: `derived_contracts.json:159918-159933` does carry `"condition": null`). #4881a should stay, reframed as "a regression test for a landmine" rather than "lid family infrastructure."
5. **Invalidation-as-tool (Q5).** Agree with the spec's own reasoning: a diff bug in an automatic path returns a wrong answer; a diff bug in a human-invoked tool wastes a human's time. The asymmetry justifies the design as specified.
6. **REASON_VOCABULARY count (Q6).** Given O2, `volume_tracking_unasserted` risks being a vocabulary member with no working producer on ship day, the same "dead data" concern §13.7 itself raises for `lid_state_unknown` — until O2 is resolved, this question should be treated as blocked, not merely open.

## Verdict

**Implementable as written: no.** §13.2 (the volume family) — the increment's headline deliverable — rests on a bridge-derivation rule (§13.2.4) that does not match on the real PLR source for its own worked example (O1), and even granting a generous reading that patches O1, the `does_volume_tracking()` gating this same bridge is supposed to feed (§13.2.6) is not actually reachable from a bridged guard as the mechanism is specified (O2), which would make AC-13.11 fail and — worse — would ship a live soundness bug (`WILL_FAIL` on programs where tracking may never have been on). §13.3 (the cache) and §13.4 (inert filter) and §13.5 (P9) are comparatively solid: their factual claims against source checked out in every case I verified, and their gaps (O5, O6) are wiring-level, not structural.

**Single most important fix.** Rewrite the §13.2.4 volume-bridge normative box so it actually derives on `LiquidHandler.aspirate`/`dispense` at the current pin — including a defined path from a `for`-loop-bound name (`op`) back to a P8 comprehension, a two-hop attribute-type resolution through an *unannotated* intermediate assignment (`Container.tracker`), and — critically — a defined mechanism for threading the **caller's** enclosing scope (`does_volume_tracking()`, `is_disabled`) onto a guard reached only through `dropped_calls` (as opposed to a resolved `delegates_to` chain, where this already works). Until that rewrite is measured and published against the real derived-contracts output, AC-13.9 through AC-13.13 cannot be satisfied and §13.0's deliverable does not exist.
