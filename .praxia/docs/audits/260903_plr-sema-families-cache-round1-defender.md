---
title: 'plr-sema families/cache increment — adversarial round 1, defender'
description: 'Defender adjudication of the round-1 challenger on the spec_version 12 draft (b89de024): O1 CONCEDE (the volume-bridge box does not match LiquidHandler.aspirate/dispense at the pin under any literal reading -- op is a for-loop variable over the comprehension OUTPUT, P1a misses dataclass class-level annotations and Container.__init__''s unannotated self.tracker; three new mechanisms needed, not one -- recommend re-scoping the volume family to increment 5); O2 CONCEDE (dropped_calls is a flat string list with zero scope context; compute_channel_bridge sources scope_trail from the CALLEE; live unshipped soundness bug); O3 CONCEDE (is_disabled is a @property; downstream of O2); O4 CONCEDE (PLR is sequential per paired op; one V2 sentence + one two-channel/one-well fixture); O5 CONCEDE (cache hook belongs in check_graph, which holds the contracts string); O6 CONCEDE (per-file alias resolution needs a rec/file parameter). Q1 verified mechanically in the spec''s favour: row-count cap and per-row ceilings are separate ratchet tests. Verdict needs_revision: ship cache (#4922), inert filter (#4883), P9 transfer binding (#4946) this round; HM-25 5->6 for P9 only; REASON_VOCABULARY stays 8; volume family + HM-24/HM-25 remainder to increment 5.'
status: final
task_id: 260903_sema-followups
date: '260903'
confidence: high
sources: 'praxia:spec-defender (claude-sonnet-5). Spec read in full; challenger report read in full. Code verified at b89de024: plr-sema/src/plr_sema/derive/receiver_state.py:1-60, :150-350 (P1a/P2/P3a), :515-589 (_constructor_state, _entry_reset), :700-804 (compute_channel_bridge); derive/__init__.py:855-950; check/__init__.py:675-734; check/ir.py:895-939; tests/test_hand_maintained_ratchet.py:260-353. PLR at pin dd79c4c89: liquid_handling/liquid_handler.py:960-1038, :1273-1372; liquid_handling/standard.py:40-90; resources/container.py:55-94; resources/volume_tracker.py (full). training/verify/data/plr_preconditions.json:49700-49869, :96955-97014. Persisted verbatim by the orchestrator: the defender agent type has no write tool.'
---
# plr-sema families/cache increment — adversarial round 1, defender

Target: `.praxia/docs/specs/260903_plr-sema-families-cache-increment.md` at `b89de024`. Challenger: `.praxia/docs/audits/260903_plr-sema-families-cache-round1-challenger.md` (`684f86de`). Verbatim defense.

---

## Per-objection verdicts

### O1 — BLOCKER as filed — **CONCEDED. Not resolvable by a bounded, single extension — recommend re-scope, not in-place patch**

**Verified against the real pin, three independent ways, matching the challenger's counterexample exactly.**

1. **`op` is not a P8 comprehension target.** `LiquidHandler.aspirate`'s comprehension (`liquid_handler.py:1007-1028`) zip-binds `r, v, o, fr, lh, t, bav, m` at `:1018-1027`; its result list is assigned to `aspirations` at `:1007`. The dropped-call head `op` comes from a **separate** statement, `for op in aspirations:` (`:1031`), which iterates the comprehension's *output list*, not its per-element bound names. Read literally, the volume-bridge box's "`<name>` is a comprehension target of a P8 match in `K`" requires `<name> ∈ {r, v, o, fr, lh, t, bav, m}`. `op` is none of those. No implementation of the box as written can match `op.resource.tracker.remove_liquid`.
2. **`SingleChannelAspiration.resource` is invisible to P1a as specified.** `standard.py:51-60` — `SingleChannelAspiration` is `@dataclass(frozen=True)` with `resource: Container` as a **class-level bare-name annotation**. `_annotated_attributes` (`receiver_state.py:170-181`) walks every `ast.AnnAssign` and keeps only those whose target passes `_is_self_attr` (`:164-167`). A dataclass field's target is `ast.Name("resource")`, not `ast.Attribute(value=Name("self"), attr="resource")`. It fails `_is_self_attr` unconditionally. §13.2.4's own hedge — "R's P1a map (**or the element class O's**)" — does not rescue this: P1a is defined once, over one predicate, and that predicate structurally excludes every dataclass field in the codebase.
3. **`Container.tracker` is invisible to P1a for a second, independent reason.** `container.py:85` — `self.tracker = VolumeTracker(thing=..., max_volume=self.max_volume)` is a plain `ast.Assign`, never `ast.AnnAssign`. `_annotated_attributes` only walks `ast.AnnAssign` nodes (`receiver_state.py:177`). Even if (2) were fixed, the *second* hop — `Container.tracker → VolumeTracker` — still fails, because the write that would establish it is unannotated.

**On the two-hop question.** `_constructor_state` (landed for #4938, `receiver_state.py:523-563`) does **not** directly supply a general "unannotated write" reader: it walks `__init__` for writes to a caller-supplied, already-known field-name set and classifies value shapes; it does not record which class a constructor call instantiates. But its **architecture** is the right precedent: it already walks both `ast.Assign` and `ast.AnnAssign` in a class's own `__init__` (`:547-555`). A new pass in the same family — P1c: for every `self.<name> = <ClassName>(...)` in `C.__init__`, record `<name> → <ClassName>` from the call's `func` — would close gap (3). It does **not** close gaps (1) or (2), which are structurally different problems with no existing precedent in `derive/`.

**Why this argues for re-scope rather than a "text + one extension" fix.** The document's own discipline (§13.2.4: "Measured expectation... which the fixer must reproduce and publish, not assume") means each of these three gaps needs its own normative box *and* its own measured/published expectation. Three new pieces of specified machinery, one without codebase precedent, stacked under a mechanism (§13.2.6, O2) with its own equally serious gap. Bounded — nothing is missing from the world — so `needs_revision`, not `needs_recon`. But not small, and §13.0 stakes the increment's headline deliverable on it.

**Recommendation.** Re-scope §13.2 out of this increment. File its two derivation gaps (this, and O2's scope-threading gap) as the **first task** of increment 5, each with its own normative box and measured expectation before any `Finding` machinery. Ship §13.3 (cache), §13.4 (inert filter) and §13.5 (P9) this round — none is implicated by O1.

### O2 — BLOCKER as filed — **CONCEDED. A live, unshipped soundness bug, and it compounds the O1 recommendation**

**Verified.** `compute_channel_bridge` — the shipped mechanism §13.2.4 says the volume bridge "mirrors" — sources a bridged guard's `scope_trail` from `guard.scope_trail` (`receiver_state.py:787`), populated by `derive_contract(receiver_state.tracker_module, f"{receiver_state.tracker_class}.{method}", index, stamp=stamp)` (`:777-779`) — from the **callee's own** contract entry, never the caller's enclosing scope. `VolumeTracker.remove_liquid`'s own survey record: `scope_trail: ["if volume - self.get_used_volume() > 1e-06"]` (`plr_preconditions.json:96975-96977`).

**Does the survey record carry any scope info for `dropped_calls` today?** No. `LiquidHandler.aspirate`'s `dropped_calls` (`plr_preconditions.json:49766-49772`) is a bare list of strings — no line number, no enclosing-scope trail. The survey's `findings` entries (direct guards in the method's own body) do carry `scope_trail` — verified by contrast: `dispense`'s own `BlowOutVolumeError` guard carries `["if self._blow_out_air_volume is None", ..., "if does_volume_tracking()"]` (`:49808-49814`). The survey *can* express this scope for direct findings; it never attaches it to a `dropped_calls` entry, by construction.

**Survey-side change or derive-side?** `derive/receiver_state.py`'s module docstring (`:1-12`) states P1-P4 are "a stdlib-`ast` pass over every PLR class body" — `derive/` already re-parses PLR source directly. A **derive-side** pass that locates the `dropped_calls`-matching call site inside the caller's own AST and accumulates its enclosing `if`/`for` conjuncts is architecturally available without touching `scripts/survey_plr_preconditions.py`. Smaller blast radius than a survey schema change, but still a wholly new pass that must be specified and measured like P7/P8.

**Counterexample confirmed as filed.** With the mechanism as literally specified, the bridged guard's `scope_trail` on `aspirate`'s entry mentions no `does_volume_tracking`; §13.2.6's env box never marks it conditional; under the default `env = frozenset()`, AC-13.11's fixture (a) emits `WILL_FAIL` unconditionally rather than `UNKNOWN`/`volume_tracking_unasserted` — a `WILL_FAIL` for a protocol whose tracking hypothesis was never asserted.

**Not independently fixable from O1.** A fixed bridge with no scope-threading is still unsound; a fixed scope-threading mechanism has nothing to bridge without a fixed matcher. Both must land together. Reinforces re-scope.

### O3 — MAJOR as filed — **CONCEDED, downstream of O2's fix**

**Verified.** `VolumeTracker.is_disabled` (`volume_tracker.py:54-56`) is a `@property`; the call site `not op.resource.tracker.is_disabled` (`liquid_handler.py:1033`) is `ast.UnaryOp(Not, Attribute(...))` — no `ast.Call`. §13.2.6's box requires "a zero-argument call `f()`". **Fail-closed** ("any unrecognised boolean conjunct in a volume guard's scope_trail blocks `WILL_FAIL`") is sufficient text for O3 in isolation, but has nothing to apply to until O2's threading mechanism exists — they must land together.

### O4 — BLOCKER (soundness) as filed — **CONCEDED. Small, independently landable**

**Verified at the pin.** `liquid_handler.py:1031-1035` is an ordinary sequential `for op in aspirations:` loop; each iteration's `remove_liquid` mutates `self.pending_volume -= volume` synchronously (`volume_tracker.py:96`) before the next iteration. The multi-channel expansion is real: `:997-999` sets `resources = [resource] * len(use_channels)`. V0/V2 do not state whether pairs apply against one shared pre-operation snapshot or thread pair-by-pair; V1 reads as simultaneous, which against PLR's sequential order yields the challenger's false `SAFE` (well 100 µL, `aspirate(vols=[60,60], use_channels=[0,1])` on one well).

**Minimal fix.** One normative sentence in V2: pairs are applied to a state threaded pair-by-pair in the order `cells(op)`/`amounts(op)` list them, mirroring PLR's own `for op in aspirations` sequencing (`liquid_handler.py:1031`), not against a shared snapshot. Plus one fixture: two channels, same well, safe individually, unsafe cumulatively on the second. Independent of O1/O2; lands whenever the volume family ships.

### O5 — MAJOR as filed — **CONCEDED. One-sentence relocation**

**Verified.** `cache_key(bc_hash, contracts_json: str, stamp, *, ir_version=IR_VERSION)` (`ir.py:918-932`) hashes the **raw string**. `_check(bytecode, protocol_fqn, contracts_payload: dict)` (`check/__init__.py:686-710`) receives only the parsed dict. `check_graph(graph_json: str, contracts_json: str)` (`:713-733`) is the only function holding the raw string. §13.9's #4922 row places the hook where its data does not exist.

**Minimal fix.** Relocate the read-through to `check_graph`, using its own `contracts_json` parameter, wrapped around the call into `_check`'s unchanged pure body. Pure wiring; §13.3.2's purity/pre-relabel argument stands.

### O6 — MINOR as filed — **CONCEDED. One-parameter signature note**

**Verified.** `_is_inert_dropped_receiver_call(call_expr: str) -> bool` (`derive/__init__.py:884-905`) takes only the string. Its caller `_dropped_receiver_worklist_from_survey` (`:908-947`) has `rec` (with `.file`) and `key` in scope at `:940` but does not pass them. **Minimal fix.** Add a `file: str` (or `rec: SurveyRecord`) parameter; alias resolution per-file.

---

## Answering the settle-list

- **O1** — not derivable with a single bounded extension; three independently-new mechanisms. **Re-scope §13.2 to increment 5**, first task = the derivation, three normative boxes each with a measured expectation.
- **O2/O3** — the survey carries zero scope context for `dropped_calls`; attach caller scope via a survey schema change (praxis-side) or a derive-side AST pass (narrower). Fail-closed is sufficient text for O3 but inert until O2 lands.
- **O4** — sequential confirmed; one sentence + one fixture.
- **O5/O6** — pure wiring; one sentence each.
- **Q1** — `test_total_declared_within_budget` (`test_hand_maintained_ratchet.py:344-352`) checks `len(live_rows()) <= BUDGET_CAP` (row **count**); `test_no_surface_exceeds_its_declared_size` (`:270-283`) enforces `measure() <= declared` **per row**. Increment 3's "zero row headroom makes a sixth pattern a cap conversation" conflates the two, as §13.2.4 argues. The spec's mechanical reading is correct; it does not rescue O1/O2.

---

## Severity table (pre → post)

| id | challenger severity | defender disposition | post-defense severity | fix class |
|---|---|---|---|---|
| O1 | BLOCKER | CONCEDED — three new mechanisms | blocking until re-scoped or three measured boxes land | design ×3 + re-scope |
| O2 | BLOCKER | CONCEDED — live soundness bug | blocking; must land with O1 | new mechanism + revised AC-13.11 |
| O3 | MAJOR | CONCEDED, downstream of O2 | inert until O2 | one-sentence fail-closed rule |
| O4 | BLOCKER (soundness) | CONCEDED | major but small, independent | one V2 sentence + one fixture |
| O5 | MAJOR | CONCEDED | minor once fixed | one-sentence relocation |
| O6 | MINOR | CONCEDED | trivial once fixed | one-sentence signature note |

---

## Convergence judgment

**Implementable as written: no — confirmed on O1 and O2.** Neither is `needs_recon`: every fact is in hand. But O1 and O2 compound tightly enough that patching in place is the wrong sizing. **`needs_revision`.**

**Recommendation on the volume family: re-scope, do not patch in place.** Defer §13.2 in its entirety to increment 5 whose first task is "derive the volume bridge, provably, on the real pin" — O1's three sub-gaps and O2's scope-threading gap, each with its own normative box and measured expectation. Do not carry HM-24 (1→2) or the P7/P8 portion of HM-25 (5→7) this round. **This round's HM-25 bump becomes 5→6, for P9 alone**; HM-24 stays at 1; `REASON_VOCABULARY` stays 8 of 12 (volume reasons ship with the volume family).

**Ship this round:** §13.3 (#4922) with O5's relocation; §13.4 (#4883) with O6's signature note; §13.5 (#4946, P9) unmodified — the only item that moves an already-missed gate (m1 84/101 → ≥92/101).

**Ordered remediation items:**

1. §13.2 entire + §13.0's headline paragraph (O1+O2) → new increment 5; first task three volume-bridge sub-boxes (for-loop-over-comprehension-output binding; dataclass-annotation P1a extension; P1c constructor-call typing precedented by `_constructor_state`); second task the caller-scope-threading mechanism (survey field vs derive-side pass — pick one).
2. §13.2.5 V0-V2 (O4) → sequential pair-threading sentence + two-channel/one-well fixture, folded into increment 5.
3. §13.2.6 (O3) → fail-closed generalisation, folded into increment 5.
4. §13.9's #4922 row + §13.3 (O5) → hook in `check_graph`. This round.
5. §13.4.2 + #4883 row (O6) → `file`/`rec` parameter, per-file aliases. This round.
6. §13.7 arithmetic → HM-25 5→6 (P9 only), HM-24 stays 1, REASON_VOCABULARY stays 8; increment 5 carries the remainder when the volume derivation measures its own patterns.
7. §13.13 Q1–Q6 → Q1 settled mechanically in the spec's favour, scoped down by item 1; Q2 resolved against the spec's framing (`ir_version` is already a key component, no sequencing cost is avoided); Q3(a)/(c) moot until items 1–3; Q6 resolved by item 6.

None requires information not in hand. `needs_recon` is not warranted.
