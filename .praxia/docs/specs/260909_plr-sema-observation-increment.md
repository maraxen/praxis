---
title: "plr-sema increment 7 — the observation record: tier (ii), the delegate→caller argument map, and the first scoped joined verdict"
description: "Seventh post-corpus increment to the plr-sema pre-corpus specification, taking increment 6 section 15.13's deferred tier-(ii) row and section 15.6's Q2 defer. The headline the user substituted into this increment on 260907 -- **the first joined SAFE on a real executed operation of the frozen tier-1 benchmark** -- is measured against the after-ledger and reported as **NOT REACHABLE in increment 7**, for a reason this document names, sizes and site-identifies rather than discovers at a gate: `_check_args`'s two guards, liquid_handler.py lines 375 and 383, sit on ALL 544 executed operations, and deciding either requires modelling five comprehensions over `inspect.signature`, a set-difference term, a set-display term and the residual `**kwargs` key set -- five productions and a per-row ceiling spend, sized at ~350 LOC and refused here as increment 8's. What increment 7 DOES ship, stated as narrowly as the ledger forces: the observation record (backend class, num_channels, head channel key set), taken inside the verifier's window and returned by the executed side on increment 5 section 14.6's O5 pattern, entering the cache key as `obs:key=value` members of the existing fifth `env` component; the derived backend surface (per (class, method) parameter names, has-var-keyword, has-var-positional, constant-return value), derived over the derive package's own PLR function index with NO hand-typed base-class name; the delegate->caller argument map at depth 1, `self.`-receiver-only, singleton-call-only, fail-closed to Top on every other shape; four E-ENV resolution rules that turn `self.head`, `self.backend.<attr>` and `self.backend.<method>` from unconditional half/Top into real values; the reopening of increment 6 section 15.13's membership deciding case under all three of its stated conditions; a refinement of A-C13 that binds a single-name quantifier target element-wise over a concrete Seq (additive `target` field on Filtered/AllOf/AnyOf, absent => None => today's behaviour); a monotonic quantifier clause that decides AllOf over a Top seq when the body is T under Top-bound targets; the LIFT of E-UNCOND(4)'s depth >= 1 WILL_FAIL forbiddance under three new normative preconditions; Q1's scoped joined verdict as a second, additive `scope_verdict` report field computed by the UNCHANGED join over the findings whose site is not in `scope.excludes_sites`, with the unscoped `verdict` staying UNKNOWN and `schema_version` staying 1; and the fence's site-keyed narrowing, built on a ~3-line `traceback.extract_tb(...)[-1]` frame capture, publishing a SECOND counter `unsound_scoped` beside the unmodified `unsound` whose definition does not change. Measured prediction, per site, for the gate candidate `pick_up_tips` (223 ops): liquid_handler.py line 409 flips to SAFE on 223 (and on up to 384 across five methods), line 514 flips to SAFE on 223 via the constant-return derivation, line 321 flips to SAFE ONLY under user decision D2 (a deck-membership observation plus a fifth named assumption A-DECK-OBJECT, recommended YES on the argument that the tier-1 fence checks it on 288 real operations), :375 and :383 do NOT flip, :576 stays tier (iii) and annotated. So `pick_up_tips`'s residual falls from SIX guard_env_dependent sites to TWO (three without D2), `n_findings_decided` is predicted 1,563 -> >= 2,170, and `scope_verdict` is predicted UNKNOWN on every one of the 544 executed operations -- **GATE: predicted NO-GO, with the obstruction named in advance**. Five user decision hooks are surfaced with recommendations and never spent in the text: D1 (lift E-UNCOND(4), recommend YES), D2 (A-DECK-OBJECT + the deck observation, recommend YES), D3 (nothing -- the derived surface introduces no hand-typed fact, recorded as a non-decision so the round can attack it), D4 (HM-25 declared 9 -> 10 for the E-ENV path-shape table, recommend YES), D5 (model `_check_args` in this increment, recommend NO). REASON_VOCABULARY stays 12 of 12 and `live_rows()` stays 24 of BUDGET_CAP 24; no registry row is added and no thirteenth reason is proposed. Increment 6 section 15.16.3 R1's owed adversarial review is restated here as five numbered claims (R1-C1..R1-C5) so the round can attack them, together with the interaction between the refined E-UNCOND(5) and this increment's depth-1 WILL_FAIL."
status: draft
spec_version: 1
amends: 260901_plr-sema-pre-corpus-spec.md
task_id: 260909_sema-observation
date: '260909'
confidence: medium
sources: "Increment 6 read in FULL as the structural model and as the text this document extends: .praxia/docs/specs/260904_plr-sema-predicate-increment.md (frontmatter 1-11; preamble 13-105; section 15.0 108-223; section 15.1 226-423; section 15.2 426-707; section 15.3 710-840; section 15.4 843-1312; section 15.5 1315-1448; section 15.6 1451-1504; section 15.7 1507-1646; section 15.8 1649-1797; section 15.9 1800-2086; section 15.10 2089-2201; section 15.11 2204-2446; section 15.12 2449-2531; section 15.13 2534-2617; section 15.14 2620-2694; section 15.15 2697-2711; section 15.16 2714-2841; References 2844-2855). Increment 5 section 14.6 read in full as the environment-member precedent every legitimacy argument here is stated against: .praxia/docs/specs/260903_plr-sema-volume-increment.md:602-741 (the conditional-guard rule 619-636, R1 638-673, the TWO FAILED is_disabled discharges 675-689, the env argument 691-698, O5 -- observed inside the window, returned by the executed side 700-723, the consequence 725-741). Main spec: .praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md:574-581 (the join table), :2514-2524 (the deferred rows, (c) at 2518, (e) at 2520, (f) at 2524), :2526-2534 (the boundary summary), :3316-3345 (Open decisions 3, the additive direction at 3322-3326). Increment 1: .praxia/docs/specs/260902_plr-sema-tip-typestate-increment.md:744-754 (the named-assumption table -- A-SINGLE 751, A-COMPLETES 752, A-COMMIT 753, A-ENABLED 754). PLR at submodule pin dd79c4c89, every line below read THIS pass: external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:155-203 (the receiver fields at 158-166, `setup` and the head construction at 187-197), :300-321 (`_assert_resources_exist`), :323-389 (`_check_args` in full -- the AsyncMock early return 347-350, `inspect.signature` 353-359, `non_default`/`missing` 369-375, the **kwargs early return 377-378, `extra`/`strictness` 380-389), :391-409 (`_compute_spread_offsets`, `_make_sure_channels_exist`), :488-524 (pick_up_tips' body), :541-556, :575-576; external/pylabrobot/pylabrobot/liquid_handling/strictness.py:1-24 (the module-global and its two accessors); external/pylabrobot/pylabrobot/liquid_handling/backends/backend.py:1-60 and :175-188 (`LiquidHandlerBackend`, the abstract `can_pick_up_tip`); external/pylabrobot/pylabrobot/liquid_handling/backends/chatterbox.py:30-79 and :232-243 (`__init__`, `num_channels`, `pick_up_tips`, `can_pick_up_tip`); external/pylabrobot/pylabrobot/liquid_handling/backends/serializing_backend.py:236-242; external/pylabrobot/pylabrobot/resources/resource.py:160-174 (`__eq__`) and :566-589 (`get_resource` and its ResourceNotFoundError). The six direct LiquidHandlerBackend subclasses enumerated by ripgrep over the whole PLR tree at the pin and each class line read: external/pylabrobot/pylabrobot/liquid_handling/backends/opentrons_backend.py:80, external/pylabrobot/pylabrobot/liquid_handling/backends/chatterbox.py:24, external/pylabrobot/pylabrobot/liquid_handling/backends/tecan/EVO_backend.py:56, external/pylabrobot/pylabrobot/liquid_handling/backends/serializing_backend.py:26, external/pylabrobot/pylabrobot/liquid_handling/backends/hamilton/base.py:46, external/pylabrobot/pylabrobot/liquid_handling/backends/hamilton/tcp_backend.py:66; the eight can_pick_up_tip definitions likewise, of which exactly two are a single return of a constant. Analyzer source, each citation verified against the file this pass: plr-sema/src/plr_sema/check/ir.py:170-204 and :905-953; plr-sema/src/plr_sema/verdict.py:125-199, :250-275, :278-323; plr-sema/src/plr_sema/check/__init__.py:400-470, :600-639, :920-990; plr-sema/src/plr_sema/check/predicate.py:262-295, :597-658, :666-679, :765-800, :818-888; plr-sema/src/plr_sema/derive/__init__.py:454-528; plr-sema/src/plr_sema/derive/bindings.py:113-124,158,215,279-304,690-737,778-815; plr-sema/src/plr_sema/derive/receiver_state.py:1275-1308; plr-sema/src/plr_sema/_hand_maintained.py:36-49, :648-667, :890-1019; plr-sema/eval/oracle_common.py:398,415-439,446,463,551,623,767-786. Harness: training/verify/verifier.py:95-200; training/verify/deck.py:130-163. Lint, read in full so every citation and every task row in this document is written against the checker rather than against a memory of it: plr-sema/scripts/check_spec_citations.py:1-80,100-213; plr-sema/scripts/check_spec_crossrefs.py:45-199; plr-sema/tests/test_spec_lint.py:20-51,205-258. The instrument and its companions, read this pass: outputs/plr-sema/unknown_ledger_260909_after.json:2-19,29-38,41-45,90-94,136-148,177-188,217-223,257-261,2119-2156,2158-2169; outputs/plr-sema/oracle_replay_260909_inc6.json:2-30,105-137,138-199; outputs/plr-sema/predicate_mutants_260909_inc6.json:2-58; outputs/plr-sema/t30_measured_260908.json:28555-28610. plr-sema/data/derived_contracts.json read for its FOUR top-level keys only (`contracts`, `receiver_state`, `schema_version`, `stamp`). Not read this pass and therefore cited BY SYMBOL rather than by line throughout: plr-sema/eval/predicate_mutants.py, plr-sema/eval/region_oracle.py, plr-sema/eval/unknown_ledger.py, plr-sema/src/plr_sema/derive/predicate_ast.py, plr-sema/src/plr_sema/check/tipstate.py."
---

# Increment 7: the observation record

> **This document amends `.praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md` by reference** and
> adds §16 to that document's numbering, exactly as increment 6 adds §15. It takes increment 6 §15.6's
> Q2 defer — *"tier (ii) ships as increment 7"* — together with the four items §15.13 named as
> increment 7's by name: the delegate→caller argument map, the `EnvRef` path lookup against an
> observation, the site-keyed soundness-fence narrowing, and the membership deciding case with its
> three reopening conditions.
>
> **What this increment ships, stated as narrowly as the after-ledger forces.** The observation record
> and its cache-key partition; the derived backend surface; the delegate→caller argument map; four
> `E-ENV` resolution rules; two quantifier clauses; the scoped joined verdict; and the fence's
> site-keyed narrowing. On the frozen benchmark this turns **two** of the gate candidate's six
> `guard_env_dependent` sites into `SAFE` — `liquid_handler.py:409` and `:514` — and a **third**
> (`:321`) iff the user takes decision **D2**.
>
> **What it does NOT ship, and this is the document's central finding.** *The first joined `SAFE` on a
> real executed operation is not reached in increment 7 either.* The obstruction is not tier (ii), not
> the grammar and not the fence: it is `_check_args`, whose two guards
> (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:369-375`, `:377-383`) sit on
> **all 544** executed operations of the frozen benchmark
> (`outputs/plr-sema/unknown_ledger_260909_after.json:41-45`, `:90-94`) and whose conditions name
> locals bound by five comprehensions over `inspect.signature` reflection, a set difference and a set
> display. Deciding either one needs five new productions and a per-row ceiling spend. §16.1 sizes it,
> §16.15 puts it as **D5** with a recommendation of **NO**, and §16.10 states the gate prediction both
> ways so the round can falsify either branch.
>
> **This is the second consecutive increment to report its own headline unreachable, and the document
> says so in its own words rather than leaving it to a gate.** Increment 6 §15.5 discovered the tier-(iii)
> coupling *after* the plan had committed to a headline; the user substituted it into this increment on
> 260907 (`.praxia/docs/specs/260904_plr-sema-predicate-increment.md:1436-1447`). Increment 7 reports
> the same class of finding **before** any code is written, from the ledger the previous increment
> produced, and with the obstruction reduced from "tier (ii), somewhere" to two named lines of one
> named PLR function. That is the difference this document is claiming, and it is the only claim about
> the headline it makes.
>
> **Registry arithmetic, with the one spend it proposes and never takes.** `REASON_VOCABULARY` stays
> at **12 of 12** — no thirteenth reason is proposed and none is needed (§16.8). `live_rows()` stays
> **24** against `BUDGET_CAP = 24` (`plr-sema/src/plr_sema/_hand_maintained.py:43`) — **no row is
> added**, so no cap conversation opens. One **per-row ceiling spend** is proposed: HM-25 `declared`
> **9 → 10**, for §16.5's `EnvRef` path-shape table, which is genuinely hand-maintained surface and
> which increment 6 §15.4's `E-ENV` box forbade outright *"in this increment"* precisely so this
> increment would have to argue for it. That is **D4**, recommended **YES**, and it is the user's, not
> the sprint's.

---

## 16.0 The instrument and the claim

**The instrument is the after-ledger increment 6 closed with**, `outputs/plr-sema/unknown_ledger_260909_after.json`,
produced by the unmodified `plr-sema/eval/unknown_ledger.py` against the frozen benchmark
`tier1-sidecar-gated-dd79c4c89` at PLR pin `dd79c4c89`
(`outputs/plr-sema/unknown_ledger_260909_after.json:2-19`). Its numbers, verbatim: **544 executed
operations**, 544 with `n_ops_unknown` equal to `n_ops_executed`, **5,157 findings**, **53 clusters**
(`outputs/plr-sema/unknown_ledger_260909_after.json:29-38`). By reason: `guard_env_dependent` 4,138,
`guard_predicate_unparsed` 495, `volume_state_unknown` 194, `unresolved_delegate` 186,
`guard_operand_unknown` 144.

**The per-operation residual histogram is five rows, and every row begins with `guard_env_dependent`**
(`outputs/plr-sema/unknown_ledger_260909_after.json:2119-2156`):

| per-op reason set | ops | note |
|---|---|---|
| `{guard_env_dependent}` | **223** | `pick_up_tips` — the gate candidate, and the only set with no coverage gap in it |
| `{guard_env_dependent, guard_predicate_unparsed, volume_state_unknown}` | 117 | `aspirate` 77 + `dispense` 40 — the unseeded volume cell plus `:116` |
| `{guard_env_dependent, guard_predicate_unparsed, unresolved_delegate}` | 93 | the `move_*` family — **deferred row (e)** (`.praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md:2520`), out of scope by construction |
| `{guard_env_dependent, guard_predicate_unparsed}` | 58 | `stamp` 27 + `drop_tips` 31 |
| `{guard_env_dependent, guard_operand_unknown, guard_predicate_unparsed}` | 53 | `discard_tips` 34 + `transfer` 19 |

**The gate candidate is `pick_up_tips`, 223 operations, and the ledger identifies it without argument.**
It is the one method whose residual reason set is a singleton, and it is the method increment 6 §15.9
named in advance and T35 confirmed cell for cell. The per-method residual sets in the replay report
agree: `pick_up_tips` is `decidable+guard_env_dependent` on 223 of 223
(`outputs/plr-sema/oracle_replay_260909_inc6.json:138-199`), and every other method carries at least
one further reason.

### 16.0.1 The six sites, and why they are coupled

`pick_up_tips`'s residual is exactly six `guard_env_dependent` guard sites, all in
`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py` at pin `dd79c4c89`. Their cluster
sizes, read off the ledger:

| site | condition (verbatim from the ledger) | `n_findings` / `n_ops_blocked` | ledger anchor |
|---|---|---|---|
| `:375` | `len(missing) > 0` | 544 / 544 | `outputs/plr-sema/unknown_ledger_260909_after.json:41-45` |
| `:383` | `strictness == Strictness.STRICT` | 544 / 544 | `outputs/plr-sema/unknown_ledger_260909_after.json:90-94` |
| `:409` | `not len(invalid_channels) == 0` | 384 / 384 | `outputs/plr-sema/unknown_ledger_260909_after.json:136-148` |
| `:321` | `not resource_from_deck == resource` | 288 / 288 | `outputs/plr-sema/unknown_ledger_260909_after.json:177-188` |
| `:514` | `not all((self.backend.can_pick_up_tip(channel, tip) for channel, tip in zip(use_channels, tips)))` | 223 / 223 | `outputs/plr-sema/unknown_ledger_260909_after.json:217-223` |
| `:576` | `error is not None` | 223 / 223 | `outputs/plr-sema/unknown_ledger_260909_after.json:257-261` |

**Every one of the six blocks every one of the 223 `pick_up_tips` operations.** The three that also
reach other methods carry the same reason there: `:409`'s `per_method` breakdown is `pick_up_tips` 223,
`aspirate` 77, `discard_tips` 34, `drop_tips` 31, `transfer` 19 — summing to 384 — and `:321`'s is
`pick_up_tips` 223, `discard_tips` 34, `drop_tips` 31, summing to 288
(`outputs/plr-sema/unknown_ledger_260909_after.json:136-148`, `:177-188`). Both sums close, which the
ledger's own `consistency` invariant 3 asserts for every cluster.

> **Normative (the coupling, and why no subset of the six is a deliverable).** `join` is unchanged
> (`plr-sema/src/plr_sema/verdict.py:313-323`) and is still the only function that aggregates: one
> `UNKNOWN` finding makes the operation `UNKNOWN`. **A joined verdict is therefore an all-or-nothing
> property of the six**, and every cluster in the ledger reports `n_ops_sole_blocker` 0. The
> consequence is normative for how this increment is measured: a metric of the form "clusters removed"
> or "findings converted" can move by 607 while `scope_verdict` stays `UNKNOWN` on all 544 operations.
> §16.10's gate is therefore stated over **`scope_verdict` per operation**, and that is the only
> number in this document allowed to decide GO.

### 16.0.2 The claim

**The claim, stated as narrowly as increment 5 and increment 6 each stated their own.** Increment 7
makes two of the six sites `SAFE` on every operation that carries them, a third `SAFE` iff the user
takes D2, and annotates the sixth out of the PLR-precondition scope as increment 6 already does. It
gives `AnalysisReport` a second, additive verdict field that says what the analyzer knows *within that
scope*, so that when the two `_check_args` sites are finally decided the joined result is a field that
already exists and already has a fence behind it, rather than a representation invented at the moment
it first becomes non-trivial. **It does not produce a joined `SAFE`-within-scope on any operation of
the frozen benchmark, and §16.1 is the whole argument for that sentence.**

---

## 16.1 The six sites, and what each one needs

> **Normative (how to read this table).** "Decidable this increment" is a **prediction** in exactly
> increment 6 §15.1's sense: the measured column is §16.10's, produced by T46, and where the two
> disagree the measurement wins and the divergence is recorded rather than absorbed. A `Y` cell is a
> claim that this document specifies every mechanism the site needs; an `N` cell names what is missing
> and sizes it.

| site | guard | depth | the fact it needs | from where | decidable? | resolves to |
|---|---|---|---|---|---|---|
| `:375` | `len(missing) > 0` | 1 | `missing = non_default − backend_kws`, over five comprehensions and `inspect.signature` | a model of `_check_args` (§16.1.1) | **N** — D5 | ½ / `guard_env_dependent` |
| `:383` | `strictness == Strictness.STRICT` | 1 | the enclosing `len(extra) > 0 and len(vars_keyword) == 0` at `:381`, or the `**kwargs` early return at `:377-378` | the same model | **N** — D5 | ½ / `guard_env_dependent` |
| `:409` | `not len(invalid_channels) == 0` | 1 | `channels ← use_channels` (§16.4) + `self.head`'s key set (§16.2/§16.5) + element-wise membership (§16.5) | the observation + the argument map | **Y** | `SAFE` on 223 (up to 384) |
| `:321` | `not resource_from_deck == resource` | 1 | deck membership by name **and** a structural `Resource.__eq__` the IR cannot represent | an observation + a fifth named assumption | **Y iff D2** | `SAFE` on 288, else ½ |
| `:514` | `not all(... can_pick_up_tip ... zip(use_channels, tips))` | 0 | the backend method's **body**, plus a monotonic quantifier clause over a ⊤ `Zip` | the derived backend surface (§16.3) | **Y** | `SAFE` on 223 |
| `:576` | `error is not None` | 0 | nothing — tier (iii), derived by `is_dynamic_raise` | already shipped | **n/a** | one `UNKNOWN` + `excludes_sites` |

### 16.1.1 `:375` and `:383` — the obstruction, sized

`_check_args` is read in full at `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:323-389`
and its call site inside `pick_up_tips` at `:541-546`, which passes the bound backend method
`self.backend.pick_up_tips`, the entry point's `backend_kwargs`, `default={"ops", "use_channels"}`,
and `strictness=get_strictness()`.

**`:375`'s condition names `missing`, and every step of `missing`'s derivation is outside every
mechanism this document ships.** `missing = non_default - backend_kws`
(`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:369-375`) is an `ast.BinOp` set
difference — increment 6 §15.13 refuses arithmetic `BinOp` terms and G1 has no set-difference
production. `non_default` is a set comprehension over `args.items()`; `args` is itself two chained
dict comprehensions over `sig.parameters.items()`, and `sig = inspect.signature(method)` is reflection
over a **runtime object** (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:353-359`).
`backend_kws = set(backend_kwargs.keys())` is a `set(...)` over a `.keys()` call on a parameter the IR
does not model at all: `pick_up_tips`'s own `**backend_kwargs` is the residual of the caller's kwargs
after the named parameters, and `lower_calls` renames untrusted kwargs to `?<j>`
(`plr-sema/src/plr_sema/check/ir.py:194-204` is the `Call` shape that carries them). §15.3's α binds a
`ast.ListComp` with a bare-`ast.Name` `iter` naming a parameter of `K`; none of these four
comprehensions matches that shape, and β binds only a length.

**`:383` has two independent routes and both need the same facts.** Route (a) is `E-SCOPE`: `:383`
sits inside `if len(extra) > 0 and len(vars_keyword) == 0:` at
`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:377-383`, so an `F` on that entry
returns `SAFE` for the guard without deciding `strictness` at all — but `vars_keyword` is the third of
the five comprehensions. Route (b) is the early return: `if len(vars_keyword) > 0: return set()` at
`:377-378` means the function returns before `:381` whenever the backend method accepts `**kwargs` —
which the chatterbox one does
(`external/pylabrobot/pylabrobot/liquid_handling/backends/chatterbox.py:63`) — and the survey's
`scope_trail` records nothing about an early return, exactly as increment 6 §15.6 flagged. Route (b)
would also need a new derived caller-side clause. **Both routes bottom out on `Len(vars_keyword)`.**

> **Normative (`strictness` decides nothing, restated and now with a second reason).** Increment 6
> §15.6 established that adding `strictness` to `env` converts a ½ into a ½ because the enclosing
> scope entry is tier-(ii) backend. A second, independent reason is recorded here: even with the
> process-global observed, `Strictness.STRICT` on the comparison's right-hand side is an
> `ast.Attribute` chain rooted at the **module-level name** `Strictness`
> (`external/pylabrobot/pylabrobot/liquid_handling/strictness.py:5-10`), not at `self`, so it is not an
> `EnvRef` under G7 and it resolves to ⊤ as an ordinary `Attr` term. Deciding `:383` from the left-hand
> side alone is therefore impossible **whatever `env` carries**, and an enum-constant `Term` production
> would be a further production this document does not adopt. **`strictness` is refused as an
> observation member by name in §16.2**, and this box is the reason.

> **Normative (the size of D5, stated before the decision rather than after it).** Deciding `:375` and
> `:383` requires, at minimum: **(1)** a `set(<x>.keys())` `Term`; **(2)** a set-difference `BinOp`
> `Term` over two resolved `Seq`s; **(3)** a set-display `Term` (`{"ops", "use_channels"}` at the call
> site); **(4)** an `E-SIG` rule resolving the three comprehension shapes PLR writes over
> `inspect.signature(<t>).parameters.items()` — the `VAR_KEYWORD` filter, the
> `default == inspect.Parameter.empty` filter, and the `arg not in default_args` filter — against
> §16.3's derived backend surface; and **(5)** a representation of the residual `**kwargs` key set,
> computable from the call's own kwargs minus the contract table's `params` key. Sized at **~350 LOC**
> plus a further HM-25 ceiling spend, because (4) is three syntactic patterns over how PLR is written.
> **It is one increment's work, it is the whole of the remaining distance to the headline, and it is
> `D5`, recommended NO (§16.15).**

### 16.1.2 `:409` — decidable, and the three mechanisms it needs

`_make_sure_channels_exist` is three lines
(`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:405-409`): `invalid_channels = [c
for c in channels if c not in self.head]`, then `if not len(invalid_channels) == 0: raise ValueError`.

Under increment 6's shipped machinery the guard already parses without an `Opaque` node: α binds
`invalid_channels` to `Filtered(Var("channels"), Cmp(Var("c"), "not in", EnvRef(("self", "head"), None)))`,
G3 rewrites `len(Filtered) == 0` as `Not(AnyOf(seq, pred))`, and the outer `not` cancels it, so the
guard's truth is exactly *"∃ a channel not in `self.head`"*. Three things stop it deciding, and this
increment supplies all three:

1. **`channels` never binds.** It is `_make_sure_channels_exist`'s own parameter at `depth == 1`, and
   increment 6's `E-CALL(depth)` forbids resolving it against the entry point's kwargs. §16.4's
   delegate→caller argument map binds it from the positional call
   `self._make_sure_channels_exist(use_channels)` at
   `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:520-522`, after which
   `use_channels` resolves in `pick_up_tips`'s own namespace through the P3a hook — `channels_for_call`
   returned non-`None` on **every** executed `pick_up_tips` operation at T30, and `:502`'s own
   dependence on that resolution is measured decided at 223/223
   (`outputs/plr-sema/oracle_replay_260909_inc6.json:109-125`).
2. **`self.head` is ⊤.** §16.5's rule **R-HEAD** resolves `EnvRef(("self", "head"), None)` to the
   observed key set of the receiver's `head` dict (§16.2), a `Seq` this document declares **complete**.
3. **Membership decides nothing.** Increment 6 §15.13 deleted the deciding case with three explicit
   reopening conditions. §16.5 satisfies all three and §16.5.4 states which clause answers which.

Additionally, `AnyOf` must bind `c` element-wise, which the shipped evaluator does not do
(`plr-sema/src/plr_sema/check/predicate.py:597-606` evaluates the body **once** with every
comprehension-bound name at ⊤). §16.5.5 refines that.

### 16.1.3 `:321` — the deck, and what `SAFE` there would actually assert

`_assert_resources_exist` loops over `resources` and, per resource, looks the deck up **by name** and
compares (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:305-321`). Two facts about
PLR make this site much harder than "deck membership", and both were read at the pin this pass.

**Fact 1: the lookup raises before the guard is reached.** `Resource.get_resource` returns `self` on a
name match, recurses into `children`, and otherwise raises `ResourceNotFoundError`
(`external/pylabrobot/pylabrobot/resources/resource.py:566-589`). So *"the resource is not on the
deck"* does **not** make `:321` fire; it makes `:318` raise a different exception at a site the
contract table carries no guard for. A membership observation therefore decides a **different** raise
from the one `:321` names.

**Fact 2: the comparison is structural, and the IR cannot represent it.** `Resource.__eq__` compares
name, all three absolute sizes, location, category **and children**
(`external/pylabrobot/pylabrobot/resources/resource.py:160-170`). The IR's `Resource` value carries
`slot`, `type`, `element_type`, `is_container`, `is_parameter`, `parents` and `grid` and **no name at
all** (`plr-sema/src/plr_sema/check/ir.py:178-191`) — let alone geometry, location or children. Since
the lookup key is `resource.name`, the name half of `__eq__` is `True` by construction; what remains is
a geometry-and-children comparison between two objects the analyzer models as one slot index.

> **Normative (what a `SAFE` at `:321` asserts, and what would have to be assumed).** A `SAFE` at
> `:321` asserts: *the object this call passes at this slot is structurally equal to the deck's object
> of that name*. No observation available to this analyzer establishes it without observing the guard's
> own answer, and no derivation establishes it at all. It is therefore an **assumption**, and this
> document names it rather than smuggling it:
>
> **A-DECK-OBJECT** — *a resource the program passes to a `LiquidHandler` operation is the deck's own
> object of that name.*
>
> **What breaks if it is false:** a program that constructs a second `Resource` with a name already on
> the deck and passes it gets a `SAFE` where PLR raises `ValueError` — a false `SAFE`, the unsound
> direction. **What checks it:** the tier-1 fence, unmodified
> (`plr-sema/eval/oracle_common.py:767-786`), on **288 real operations** — every `SAFE` at `:321` on an
> operation that raised is counted. **How it compares to what the analyzer already assumes:** it is
> strictly narrower than **A-SINGLE**, which claims one receiver variable denotes one instance for the
> whole graph with no aliasing, and it is partly self-discharging under **A-COMPLETES** in exactly
> A-ENABLED's manner — a completed preceding operation on the same resource implies that operation's
> own `_assert_resources_exist` passed; the four-row table is at
> `.praxia/docs/specs/260902_plr-sema-tip-typestate-increment.md:749-754`.
>
> **Adding a fifth named assumption is a USER decision, not the sprint's.** It is **D2** (§16.15),
> recommended **YES**, and §16.10 states the gate prediction both with and without it.

The two alternatives are recorded so D2 is a choice between named options rather than a single ask.
**(a) Add `name` to `ir.Resource`.** That is a wire change and an `IR_VERSION` bump
(`plr-sema/src/plr_sema/check/ir.py:170-191`, `:905-915`), it re-keys every cached entry, and it still
does not decide `__eq__` — it decides only the name half, which is already `True` by construction. It
buys nothing D2 does not, at strictly higher cost. **Rejected, and recorded as rejected.**
**(b) Leave `:321` at ½.** `pick_up_tips`'s residual falls to **three** sites instead of two,
`n_findings_decided` gains 607 instead of 895, and `:321` remains the third-largest single cluster in
the ledger. Nothing else changes; the headline is out of reach either way (§16.1.1).

### 16.1.4 `:514` — decidable from the backend's method body

The condition is `not all(self.backend.can_pick_up_tip(channel, tip) for channel, tip in
zip(use_channels, tips))` (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:506-514`),
which increment 6 parses to
`Not(AllOf(Zip((Var("use_channels"), Var("tips"))), EnvRef(("self", "backend", "can_pick_up_tip"), (Var("channel"), Var("tip")))))`.

**The `Zip` cannot resolve, and this increment does not make it resolve.** Increment 6's `Zip` rule is
⊤ unless **every** item resolves to a concrete `Seq`; `tips = [tip_spot.get_tip() for tip_spot in
tip_spots]` at `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:504` is a
*projecting* comprehension that α rejects, so `tips` is ⊤ and the `Zip` is ⊤. That stays true here.

**What decides the guard is the body, not the sequence.** The chatterbox backend's `can_pick_up_tip`
body is exactly `return True`
(`external/pylabrobot/pylabrobot/liquid_handling/backends/chatterbox.py:241-242`). If the `EnvRef`
resolves to the constant `True` **independently of its arguments** — which is what a constant-return
body means — then `AllOf` over a ⊤ sequence of a uniformly-`T` body is `T` (§16.5.5's monotonic
clause), `Not(T)` is `F`, and the `raise_guard` does not fire: **`SAFE`**. The measured population of
constant-return `can_pick_up_tip` bodies across the whole PLR tree at the pin is **2 of 8** —
`external/pylabrobot/pylabrobot/liquid_handling/backends/chatterbox.py:241-242` and
`external/pylabrobot/pylabrobot/liquid_handling/backends/serializing_backend.py:241-242` — while the
abstract base is a docstring-only `@abstractmethod`
(`external/pylabrobot/pylabrobot/liquid_handling/backends/backend.py:183-187`) and the remaining five
are multi-statement. §16.3 publishes the whole-surface count rather than this one.

---

## 16.2 The observation record

> **This section's every legitimacy argument is stated against increment 5 §14.6**
> (`.praxia/docs/specs/260903_plr-sema-volume-increment.md:602-741`), which is the only precedent in
> the analyzer for reading anything outside the extracted graph, and which recorded **two failed
> discharges** so the question would not be re-opened without new facts
> (`.praxia/docs/specs/260903_plr-sema-volume-increment.md:675-689`). Each field below is argued
> against both, individually and by name.

### 16.2.1 The record

> **Normative (O2 — the observation record).** The executed side returns **one additive result key**,
> `plr_observation`, a JSON object with exactly the fields below and no others. Every field is taken
> **inside** the verifier's window and **returned by** the executed side; nothing is observed from
> outside it. This is increment 5's O5 pattern verbatim
> (`.praxia/docs/specs/260903_plr-sema-volume-increment.md:700-723`), and `volume_tracking_observed`
> (`training/verify/verifier.py:110-128`, returned at `:184-200`) is the shipped instance of it.
>
> | field | type | where it is taken | what it decides |
> |---|---|---|---|
> | `backend_class` | `str` | `type(setup.machine.backend).__name__`, after `build_setup` and before `_execute` | selects the row of §16.3's derived surface |
> | `num_channels` | `int` | `setup.machine.backend.num_channels`, same point | published; **decides nothing on its own** — see the box below |
> | `head_channels` | `list[int]` | `sorted(setup.machine.head)`, **after** `await setup.machine.setup()` and before `_execute` | R-HEAD (§16.5) — the key set `:409` reads |
> | `deck_resource_names` | `list[str]` | the `topology` key of `before = setup.snapshot()` | **D2 only** — R-DECK (§16.5) |
>
> **Placement is normative, not incidental.** `head_channels` must be read **after**
> `await setup.machine.setup()` (`training/verify/verifier.py:130-134`), because the receiver's head
> dict is empty until PLR's own setup builds it — declared at
> `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:155-166` and filled at `:187-197` —
> and **before** `_execute`, because a failed operation may leave
> the trackers rolled back. `deck_resource_names` is read off `before`, which
> `training/verify/verifier.py:116-119` already takes immediately after seeding.

> **Normative (the record is CLOSED, and these are refused BY NAME).** A field absent from the table
> above is not observed. Refusing them by name is what keeps the record from growing one
> convenience at a time:
>
> - **`strictness`** — refused. §16.1.1's box: it decides nothing alone and `Strictness.STRICT` is not
>   a `Term`. Increment 6 §15.6 reached the same conclusion by a different route; two independent
>   arguments now stand behind the refusal.
> - **per-well seeded volumes** — refused. That is the well-seeding observation increment 6 §15.13
>   defers, it belongs to the volume family's `volume_state_unknown` cell, and admitting it here would
>   move a number this increment's gate does not read.
> - **lid topology** — refused. Increment 4 §13.1's disposition stands and `:116`/`:117` are not on the
>   gate candidate.
> - **`head96`** and **`_default_use_channels`** — refused. Neither appears in any guard on any of the
>   544 executed operations; admitting a field no guard reads is exactly the surface growth §9.4 exists
>   to prevent.
> - **anything read from `after`** — refused, categorically. `after = setup.snapshot()` is taken
>   *after* execution (`training/verify/verifier.py:142`); a fact read from it is a fact about the
>   outcome, and conditioning a static verdict on the outcome is not an observation, it is the answer.
> - **the value of any guard's own condition** — refused, categorically, for the same reason.

### 16.2.2 The legitimacy argument, per field

Increment 5's two failed discharges are: *(i) a single `env` member would be a quantified claim dressed
as an observation*, because a deck carries one tracker per well and per tip and no single fact stands
for "every tracker relevant to this guard was enabled"; and *(ii) "no `.disable()` appears in the
program" is sound only if the analyzed graph is the whole world*
(`.praxia/docs/specs/260903_plr-sema-volume-increment.md:675-689`).

| field | against (i) — is it quantified? | against (ii) — does it assume the graph is the world? |
|---|---|---|
| `backend_class` | No. One process, one `LiquidHandler`, one `backend` attribute assigned once at construction (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:155-158`). It is a single value, exactly `does_volume_tracking()`'s shape. | No. It is read *from* the executed object, not inferred from the absence of something in the graph. |
| `num_channels` | No. A single `int` off a single backend instance (`external/pylabrobot/pylabrobot/liquid_handling/backends/chatterbox.py:59-61`). | No, same. |
| `head_channels` | **This is the field to attack, and the attack is answered by observing the key set rather than deriving it.** Deriving `range(num_channels)` from `:197` would be a claim about how `head` is *built*; observing `sorted(self.head)` is a claim about what it *contains* at one instant. The set is finite, enumerated, and returned. | No. |
| `deck_resource_names` (**D2**) | Borderline, and the border is where D2 sits. The set is finite and enumerated, so it is not quantified over unseen instances — but it decides only the `get_resource` half of `:321`, and the `__eq__` half needs **A-DECK-OBJECT**. §16.1.3 is the argument; D2 is the decision. | No for the observation; **yes for the assumption**, which is why the assumption is named, published in the assumption table with its breakage column, and fence-checked on 288 operations. |

> **Normative (a third failure mode increment 5 did not have to name, because it had one member).**
> An observation that is a **function of the guard being decided** is refused however it is taken. The
> test is mechanical: could the harness compute this field only by evaluating the same expression the
> guard evaluates? If yes, it is the answer, not an observation. `head_channels` passes (the guard
> evaluates a membership test *against* the key set; the field is the key set). A hypothetical
> `assert_resources_exist_passed` fails. This test is what makes the closed list above a rule rather
> than a preference.

### 16.2.3 The cache key

> **Normative (O2 enters `env`; the tuple gains no component).** The observation is encoded as
> `obs:<key>=<value>` **string members of the existing `env` frozenset**, not as a sixth `cache_key`
> component. `cache_key` stays exactly five-tuple-shaped
> (`plr-sema/src/plr_sema/check/ir.py:918-953`), `check_ir`'s and `check_graph`'s keyword-only `env=`
> parameters are unchanged (`plr-sema/src/plr_sema/check/__init__.py:616-624`, `:968-975`), and the
> `tuple(sorted(env))` encoding keeps the key JSON-round-trippable and order-independent by
> construction — the two properties `cache_key`'s own docstring names.
>
> **Why not a sixth component.** A sixth element changes the key's **arity**, which every caller, every
> persisted store and every test that unpacks a key sees; the existing `env` slot was added for exactly
> this purpose and already carries a runtime-observed environment set. Extending it costs no signature
> change, no `IR_VERSION` bump, and preserves the property that a caller passing no observation gets a
> key **byte-identical** to today's.
>
> **Canonical encoding, so two runs of the same observation produce the same set.** Values are rendered
> as: a `str` verbatim; an `int` in base 10; a list as its **sorted** members joined by `,`. So the
> benchmark's own members are exactly
> `obs:backend_class=LiquidHandlerChatterboxBackend`, `obs:num_channels=8`,
> `obs:head_channels=0,1,2,3,4,5,6,7`.
>
> **The `obs:` prefix is load-bearing and is reserved.** `E-UNCOND` way (2) tests a bare zero-argument
> callee **name** against `env` (`plr-sema/src/plr_sema/check/predicate.py:765-770`). A member
> containing `:` and `=` can never equal a Python identifier, so no `obs:` member can satisfy way (2)
> and **no observation can manufacture reachability**. No member without the prefix is ever added by
> this increment, and `does_volume_tracking` — the one existing member — is untouched.

> **Normative (the fail-closed default, stated as a property rather than as an intention).** With no
> `obs:` member in `env`, **every** rule in §16.5 declines and every `EnvRef` is ½ in predicate
> position and ⊤ in term position, which is increment 6's `E-ENV` unchanged
> (`plr-sema/src/plr_sema/check/predicate.py:262-278`, `:646-658`). Therefore: every existing test,
> every shipped fixture, the graph lane, and any caller that does not thread an observation are
> **behaviourally identical to today by construction**, not by test. AC-16.1 asserts this directly, and
> it is the one assertion in this increment that a stubbed implementation cannot fake.

---

## 16.3 The derived backend surface

> **Normative (S1 — the table).** For every `(class, method)` pair in the derive package's own PLR
> function index, the surface records:
>
> | key | derivation | fail-closed default |
> |---|---|---|
> | `params` | the parameter names after `self`, excluding `*args`/`**kwargs`, that have **no** default | `[]` never guessed; a method whose AST does not parse is **absent** from the table |
> | `has_var_keyword` | some parameter is `**kwargs` | absent ⇒ unknown ⇒ every rule reading it declines |
> | `has_var_positional` | some parameter is `*args` | as above |
> | `constant_return` | present **iff** the body is **exactly one** `ast.Return` whose `value` is an `ast.Constant`; the value is that constant, JSON-encoded | absent ⇒ no constant-return rule fires |
>
> **`constant_return`'s shape test is deliberately the narrowest that decides `:514`.** Exactly one
> statement, that statement an `ast.Return`, its value an `ast.Constant`. A docstring **counts as a
> statement**, so a docstring-plus-return body is **not** admitted — which is what keeps the rule from
> becoming "the first return wins". Anything wider — two statements, a conditional return, a return of
> a name — is a dataflow pass by another name (increment 4 §13.12) and is refused.

> **Normative (the surface is keyed on PLR's own index and introduces NO hand-typed fact — the round-1
> correction of increment 6 §15.6, applied in advance).** The table is built over
> `build_plr_function_index` (`plr-sema/src/plr_sema/derive/receiver_state.py:1275-1308`), the
> `(module, qualname, lineno) → AST` map the derive package **already** builds over every module-level
> function and every class method in the PLR tree. **The base class name `LiquidHandlerBackend` appears
> nowhere in the derivation**, and neither does any method list: the table is not "backend classes", it
> is "classes", and the selection that keeps it small is itself derived — a `(class, method)` pair is
> emitted **iff** `method` occurs as the last segment of some admitted `EnvRef` path in the regenerated
> contract table, or as a key of some class's own parameter set reachable from one. That test reads the
> contract table, which is derived; it reads no literal.
>
> **This is the difference between a derivation and a benchmark-local hack, and increment 6 §15.6 named
> it in exactly these terms**: *"deriving over one benchmark backend would produce a fact that cannot
> enter the shipped contract table (which is keyed on PLR's own surface, not on a harness choice)"*.
> The harness choice enters at **one** point and one only: §16.2's `backend_class`, which **selects a
> row** of a table derived over the whole surface. Selection is not derivation.

**The published selection, as a measured fact for the reader and not as an input to anything.** At the
pin there are exactly **six** direct `LiquidHandlerBackend` subclasses, enumerated by ripgrep over the
whole PLR tree and each `class` line read this pass:
`OpentronsOT2Backend` (`external/pylabrobot/pylabrobot/liquid_handling/backends/opentrons_backend.py:80`),
`LiquidHandlerChatterboxBackend` (`external/pylabrobot/pylabrobot/liquid_handling/backends/chatterbox.py:24`),
`TecanLiquidHandler` (`external/pylabrobot/pylabrobot/liquid_handling/backends/tecan/EVO_backend.py:56`),
`SerializingBackend` (`external/pylabrobot/pylabrobot/liquid_handling/backends/serializing_backend.py:26`),
`HamiltonLiquidHandler` (`external/pylabrobot/pylabrobot/liquid_handling/backends/hamilton/base.py:46`),
and `HamiltonTCPBackend` (`external/pylabrobot/pylabrobot/liquid_handling/backends/hamilton/tcp_backend.py:66`).
Three carry `metaclass=ABCMeta`. **The one method the gate reads, `can_pick_up_tip`, has eight
definitions in the tree, of which exactly two are a single `return <Constant>`** — chatterbox's and
`SerializingBackend`'s (`external/pylabrobot/pylabrobot/liquid_handling/backends/serializing_backend.py:236-242`).
T41 publishes the whole-surface counts and this paragraph is a prediction for it to falsify.

> **Normative (where it lives: an additive top-level key of the shipped contract document).**
> `plr-sema/data/derived_contracts.json` has exactly four top-level keys today — `contracts`,
> `receiver_state`, `schema_version` and `stamp`. The surface is a **fifth**, `backend_surface`. It is
> **not** a separate file, and the reason is the cache: `contracts_sha` is
> `sha256(contracts_json)` over the whole document
> (`plr-sema/src/plr_sema/check/ir.py:918-953`), so an additive top-level key participates in the cache
> key automatically and a regeneration cools the cache by design, exactly as increment 6 §15.8 records
> for `predicate` and `param_defaults`. A separate file would be a fact the cache key does not cover,
> which is a correctness event dressed as a packaging choice.

> **Normative (registry: ZERO).** §16.3 adds no registry row, no per-row ceiling, and no vocabulary
> member. Its derivation is an AST shape test over PLR's own recorded surface, in the same class as
> `is_dynamic_raise` (`plr-sema/src/plr_sema/derive/__init__.py:516-520`) and `reachability_clear`
> (`plr-sema/src/plr_sema/derive/bindings.py:778-815`), both of which increment 6 established cost
> nothing. **This is recorded as a NON-decision (`D3`) precisely so the round can attack it**: if a
> reviewer can name one literal PLR fact this section hand-types, the claim is false and the section
> owes a row. The candidates a reviewer should check first are the base-class name (absent by the box
> above), the method list (absent, derived from the contract table), and `constant_return`'s shape
> (an `ast` node-class test, not a PLR idiom).

---

## 16.4 The delegate→caller argument map

Increment 6 §15.4's `E-CALL(depth)` forbids the resolution outright and §15.12's sizing note prices
building it at **~90 LOC over a new derived field with its own measured selection and its own registry
argument**, deferring it here by name. Without it `channels`, `resources` and `backend_kwargs` never
bind and `:409`, `:321` and `:875` are permanently ½.

> **Normative (M1 — the mapped call shape, and the closed list of what is refused).** For an entry
> point `K` and a delegate `D` reached by a `delegates_to` edge, the map binds `D`'s own parameter
> names to caller-side `Term`s **iff every one** of the following holds; on any failure the map for
> that `(K, D)` pair is **absent**, and an absent map resolves every free name of every guard at
> `depth >= 1` to ⊤ — today's behaviour exactly.
>
> 1. **`self.` receiver only.** The call is an `ast.Call` whose `func` is
>    `ast.Attribute(value=ast.Name("self"), attr=D)`. A module-level delegate — `_check_no_lid`, called
>    bare — is **not** mapped. This is P9's own restriction (`plr-sema/src/plr_sema/derive/receiver_state.py`,
>    `_delegate_channel_bindings`), adopted rather than widened.
> 2. **Called exactly once in `K`'s body.** P9's shipped singleton test, adopted verbatim. A delegate
>    called twice has two argument vectors and one guard record; binding either would be a choice the
>    record cannot express.
> 3. **Positional and keyword arguments, both mapped, by `D`'s own `ast.arguments`.** Positional by
>    index against `D`'s parameter list after `self`; keyword by name. This is the half P9 lacks —
>    it reads `call.keywords` only, while PLR calls every delegate that matters **positionally**
>    (`self._assert_resources_exist(tip_spots)` and `self._make_sure_channels_exist(use_channels)` at
>    `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:520-522`).
> 4. **No `ast.Starred`, no `**` unpacking, no `*args`/`**kwargs` on `D`.** Fail-closed: the mapping
>    would be positionally ambiguous.
> 5. **Every argument expression parses as a `Term`.** An argument that does not is bound to nothing
>    and its parameter resolves ⊤; the other parameters still bind. Partial maps are admitted because a
>    guard reads one name, not the vector.
> 6. **One level only.** The map is built for `depth == 1` guards. **A guard at `depth >= 2` resolves
>    every free name to ⊤**, unconditionally. Transitive composition compounds every one of the
>    conditions above and `SurveyRecord.delegates` is a bare `set[str]` that records no call site at
>    all; the general case is a call graph, not a map.

> **Normative (the wire representation, additive, on the `reachability_clear` precedent).**
> `InlinedGuard` — ten fields in the landed dataclass, `condition`, `predicate`, `scope_trail`,
> `raises`, `kind`, `free_vars`, `site`, `depth`, `bindings`, `reachability_clear`
> (`plr-sema/src/plr_sema/derive/__init__.py:505-514`) — gains an **eleventh**, `caller_args`:
>
> ```
> caller_args: dict[str, Any] | None = None     # D's parameter name -> a predicate_ast Term, JSON-encoded
> ```
>
> The value type is the **existing** `Term` JSON, so `to_json`/`from_json` need no new node kind and
> the round-trip is the one `predicate_ast` already ships. **Absent ⇒ `None` ⇒ fail-closed**, which is
> `bindings`'s default and `reachability_clear`'s, and which is what makes the field safe to add
> without a coordinated regeneration. It is computed in `derive/bindings.py`, beside
> `compute_local_bindings_for_guard` (`plr-sema/src/plr_sema/derive/bindings.py:690-737`) and
> `compute_reachability_clear` (`plr-sema/src/plr_sema/derive/bindings.py:778-815`), by a new
> `compute_caller_args(K, D)` — the module that already owns every "read `K`'s AST at
> guard-construction time" derivation, and the one entry point this increment extends.

> **Normative (M2 — how a mapped name resolves, and the ordering that prevents a double resolution).**
> For a guard at `depth == 1` whose free `Var(name)` is a parameter of `D`: **(1)** if `caller_args`
> has an entry for `name`, evaluate that `Term` **in the caller `K`'s own context** — the entry point's
> `call.kwargs`, `param_defaults`, α/β bindings and the P3a `channels_for_call` hook, with `E-CALL(5)`'s
> parameter-rebinding clause applying **in `K`**, not in `D`; **(2)** otherwise the existing rules —
> `channels_for_call` for the derived channel term, or an α/β binding in `D`'s own body over `D`'s own
> parameters; **(3)** otherwise ⊤.
>
> **Step (1) is a substitution, not a second evaluation context.** The `Term` is the caller's syntax
> and it is resolved once, against the caller. This is what closes the hazard increment 6 §15.3's
> closing paragraph names — *"α's terms would be matched in the delegate's parameter namespace and
> evaluated against the entry point's `call.kwargs`, a substitution nothing in the repo records"* —
> because the substitution is now recorded, per guard, on the wire.
>
> **The name-coincidence exposure is closed in the same stroke and its count must go to zero.**
> Increment 6 block (2) published `name_coincidence_exposure_count` at **936**: depth-≥1 free names that
> *would* have resolved by name coincidence had `E-CALL(depth)` not forbidden it. Under M2 a
> depth-1 name resolves **only** through `caller_args`, so a coincidence cannot resolve anything.
> §16.10 requires the count to be republished and asserted **0** for `depth == 1`; a non-zero value
> means step (1) fell through to a namespace it should not have seen.

> **Normative (D1 — `E-UNCOND(4)` is LIFTED at `depth == 1`, under three preconditions and no fewer).**
> Increment 6's `E-UNCOND(4)` forbids `WILL_FAIL` at `depth >= 1` outright, and its stated reason is
> structural: *"an inlined guard's reachability depends on the call site in the entry point, and
> `InlinedGuard` records nothing about it"*. This increment records it. A guard at `depth == 1` may
> emit `WILL_FAIL` **iff all three hold**, and otherwise yields ½ with `guard_env_dependent` exactly as
> today:
>
> 1. **The delegate's own body is clear.** `reachability_clear` is `True` for the guard, computed
>    against `D` by `compute_reachability_clear` (`plr-sema/src/plr_sema/derive/bindings.py:778-815`) —
>    the field increment 6 T36 already derives and wires. No change.
> 2. **The call site is reached.** A **new** additive derived pair on `InlinedGuard`:
>    `caller_reachability_clear: bool | None`, `compute_reachability_clear(K, call_lineno)` for the
>    delegate's own call statement in `K`; and `caller_scope_trail: tuple[str, ...] | None`, the
>    survey's own trail for that statement. `E-UNCOND`'s ways (1)–(3) must satisfy **every** entry of
>    `caller_scope_trail`, and `caller_reachability_clear` must be `True`. Both absent ⇒ `None` ⇒
>    blocked.
> 3. **The map is total for this guard.** Every free `Var` of the guard's α/β-substituted predicate
>    that is a parameter of `D` has a `caller_args` entry that resolves to a non-⊤ value. A guard
>    firing on a ⊤ operand cannot fire, so this is implied by the predicate evaluating `T` — it is
>    stated anyway, because "implied" is what an implementer skips.
>
> **`depth >= 2` is untouched: still no `WILL_FAIL`, ever, this increment.**
>
> **Why lift it at all, stated as the cost of not lifting.** Without the lift this increment adds
> **no** `WILL_FAIL` population whatsoever: `:409` and `:321` are the only two sites it newly decides
> and both are at `depth == 1`, so every new verdict would be in the `SAFE` direction and the mutant
> class (§16.11) could not exercise a single one of them. An increment that adds only `SAFE` verdicts
> and no way to fire them is an increment whose new machinery is tested in one direction. **That is the
> argument, and it is a testability argument, not a precision one.**
>
> **Why it is the riskiest clause in the document.** `WILL_FAIL` is the direction that produces a false
> positive on a clean operation; `join` propagates one to the whole operation
> (`plr-sema/src/plr_sema/verdict.py:313-323`) and `compare` scores
> `verdict == "will_fail" and outcome == "ran_ok"` as unsound
> (`plr-sema/eval/oracle_common.py:767-786`). Round 1 of increment 6 filed six blockers in this
> direction. **`D1` is a user decision (§16.15), recommended YES**, and it is named here as the first
> candidate for the adversarial pass alongside increment 6's own R1 (§16.15 Q6).

---

## 16.5 `E-ENV` resolution

Increment 6's `E-ENV` makes every `EnvRef` **½ in predicate position and ⊤ in term position,
unconditionally, under every state, for every path, with no lookup table**
(`plr-sema/src/plr_sema/check/predicate.py:262-278` for the term half, `:646-658` for the predicate
half). Its own text names the reason: *"a rule that matched paths would be a hand-maintained surface,
which §15.8 argues this production is not."*

> **Normative (the concession, made once and made plainly).** §16.5 **is** a path-shape table, it **is**
> hand-maintained surface, and increment 6's `E-ENV` box is superseded exactly and only in this
> increment's scope. There are four admitted shapes and no fifth; **every path not matching one of them
> stays ½ in predicate position and ⊤ in term position**, which is `E-ENV` unchanged. The registry
> consequence is §16.9's and is **D4**, HM-25 `declared` 9 → 10, recommended YES and never spent in
> this text.

### 16.5.1 R-HEAD — `self.head`

> **Normative.** `EnvRef(("self", "head"), None)` — `args is None`, i.e. a read and not a call —
> resolves, in **term** position, to `Seq((Lit(c₀), …, Lit(cₙ₋₁)))` where the `cᵢ` are the members of
> the observation's `head_channels`, in ascending order. **The `Seq` is declared COMPLETE** (§16.5.4).
> In **predicate** position `self.head` stays ½: a dict is not a truth value and no guard at this pin
> uses it as one.
>
> **Declines to ⊤ when:** no `obs:head_channels` member is present; or the observation's
> `backend_class` is absent (an observation must be complete to be used at all — a partial record is
> refused wholesale, so a reader cannot get a resolution from half a record).
>
> **What it does not cover.** `self.head[channel]` — subscripted — is `Opaque` by increment 6 G7's
> closed negative list and stays so. `self.head96` is not admitted. The path is `("self", "head")`
> exactly, length 2, nothing else.

### 16.5.2 R-ATTR — `self.backend.<attr>`

> **Normative.** `EnvRef(("self", "backend", a), None)` resolves, in term position, to `Lit(v)` where
> `v` is the observation's value for `a` **iff** `a` is a field of §16.2's record — at this pin exactly
> `num_channels`. Every other `a` resolves ⊤. In predicate position an admitted `EnvRef` of this shape
> evaluates to the Kleene truth of `Lit(v)` — `T` for a truthy constant, `F` for a falsy one — and an
> unadmitted one stays ½.
>
> **This rule decides nothing at this pin and is shipped anyway, which is a claim to check rather than
> to trust.** No guard on any of the 544 executed operations reads `self.backend.num_channels`: `:409`
> reads `self.head`, and `:197`'s `range(self.backend.num_channels)` is a *construction* site, not a
> guard. R-ATTR exists because `head_channels` and `num_channels` must agree or the observation is
> internally inconsistent, and §16.10 publishes `n_resolved_by_rule` per rule so a reader can see that
> R-ATTR's is **0** rather than take this paragraph's word for it. A non-zero count is not a failure;
> it is a number to inspect before the verdicts are accepted.

### 16.5.3 R-CONST — `self.backend.<method>(…)`

> **Normative.** `EnvRef(("self", "backend", m), args)` with `args is not None` — a call — resolves,
> **independently of `args`**, to `Lit(v)` in term position and to the Kleene truth of `v` in predicate
> position, **iff** §16.3's derived surface records a `constant_return` value `v` for
> `(backend_class, m)` under the observed `backend_class`. Otherwise ⊤ / ½.
>
> **Argument-independence is the whole of the soundness argument and must be stated as such.** A method
> whose body is exactly `return <Constant>` returns that constant for **every** argument vector, so its
> value is a function of neither `args` nor of how many times it is called. That is why the rule may
> fire when the enclosing `Zip` is ⊤ (§16.1.4): the analyzer is not claiming to know the sequence, it
> is claiming the body does not read it. **An implementation that resolved `args` first and declined on
> a ⊤ argument would pass every other fixture in AC-16.5 and fail this one**, which is that
> criterion's stub-defeating half.
>
> **The MRO is not walked, and that is deliberate.** The lookup is `(backend_class, m)` exactly. A
> method inherited rather than overridden is **absent** from the observed class's row and resolves ⊤.
> Walking the MRO would require a class-hierarchy fact the production evaluator does not carry —
> increment 6 §15.16.3 R2(b) records `class_hierarchy` as `None` in production — and would silently
> widen the rule's reach at the first refactor. Fail-closed.

### 16.5.4 The membership deciding case, reopened under all three of its conditions

Increment 6 §15.13 **deleted** the membership deciding case and recorded three explicit reopening
conditions. Each is discharged here, in order, and none is waived.

> **Normative (i) — a complete-`Seq` `Term` exists.** §16.5.1's R-HEAD produces one. **No literal
> container production is added**: `_parse_term` still has no `ast.List`/`ast.Tuple` branch and this
> increment adds none, so the only complete `Seq` reachable by any membership `Cmp` in the whole
> contract table is an `E-ENV` resolution.

> **Normative (ii) — an `ir.Seq` is a LOWER BOUND, except where this section says otherwise.** This is
> the statement increment 6 required and could not make. **A general `ir.Seq` — one resolved from
> `call.kwargs`, from a `param_defaults` entry, or from an α/β binding — is a lower bound on the
> sequence's membership and NEVER decides a `not in` to `T`.** The **one** exception is a `Seq`
> produced by an `E-ENV` rule that this section declares complete, of which there is currently exactly
> one, R-HEAD, and the completeness is a property of the *observation* — `head_channels` is the
> enumerated key set of a dict read at one instant, not an inference from how the dict was built.
>
> **The distinction lives in the evaluator, not on the wire.** `ir.Seq` gains **no field** and
> `IR_VERSION` does not move. The rule is stated at the `Cmp` node: *a membership `Cmp` decides only
> when its right operand is an `EnvRef` resolved by a rule §16.5 declares complete.* A membership
> `Cmp` whose right operand is a `Var` resolving to an `ir.Seq` is ½, **unconditionally**, exactly as
> increment 6 leaves it.

> **Normative (iii) — the population is measured and every decision is counted.**
> `n_membership_cmp` over the whole contract table is **48**
> (`outputs/plr-sema/t30_measured_260908.json:28561-28610`). §16.10 additionally publishes
> `n_membership_decided` — per site, per operation and whole-table — beside
> `n_decided_via_env_ref_shortcircuit`, and predicts it **384** (one guard, `:409`, on 384 operations)
> under R-HEAD and **0** everywhere else. A membership decision at any other site is the number to
> inspect before T46's verdicts are accepted.

> **Normative (the semantics, once all three hold).** `Cmp(t, "in", S)` where `S` is a complete `Seq`
> of `Lit`s and `t` resolves to a `Lit` is `T` iff the literal is a member, `F` otherwise;
> `Cmp(t, "not in", S)` is its exact negation. If `t` is ⊤, or `S` is not complete, or either operand
> is anything else, the result is ½. **No other comparator gains a case and `_CMP_OPS` is unchanged.**

### 16.5.5 The two quantifier clauses

`:409` and `:514` each need one, and they are independent.

> **Normative (Q-BIND — element-wise binding over a concrete `Seq`; a REFINEMENT of increment 6's
> A-C13).** A-C13 states that a name bound by an `AllOf`/`AnyOf` comprehension target resolves to ⊤ and
> is **never** resolved against `call.kwargs`, and the shipped evaluator implements it by evaluating the
> body **once** with every such name at ⊤ (`plr-sema/src/plr_sema/check/predicate.py:597-606`). The
> "never against `call.kwargs`" half is **unchanged and remains normative** — it closes a real
> name-collision hazard. What is refined is the other half:
>
> **When the quantifier's `seq` resolves to a concrete `Seq` of `n` elements AND the quantifier records
> a single-name `target`, the target binds to each element in turn and the quantifier is the Kleene
> fold over the `n` evaluations** — `AllOf` is `F` if any is `F`, `T` if all are `T`, else ½; `AnyOf` is
> `T` if any is `T`, `F` if all are `F`, else ½. When `seq` is ⊤, or the target is absent, or the target
> is a tuple (the `Zip` case), the body is evaluated once with every target at ⊤, exactly as today.
>
> **This requires the target name, which increment 6 deliberately did not record — and reversing that
> is a decision this box takes explicitly rather than by omission.** G8(1) states the tuple-target
> correspondence is *"recorded nowhere and… deliberately not reconstructible downstream — no node gains
> a field"*, on the ground that every such name was ⊤ anyway. Under Q-BIND that ground is gone for the
> single-name case. **`Filtered`, `AllOf` and `AnyOf` each gain an additive `target: str | None`**,
> written by `parse` for a bare-`ast.Name` comprehension target and `None` for a tuple target — so the
> `Zip` correspondence stays unrecorded and G8(1)'s sentence stays true where it was made. Absent ⇒
> `None` ⇒ today's behaviour, the same additive default as `bindings` and `reachability_clear`.
>
> **Soundness.** Element-wise evaluation is the ordinary semantics of a comprehension; the ⊤-once
> evaluation is a sound over-approximation of it (⊤ is the least informative binding, so a definite
> value under ⊤ is definite under every refinement). Q-BIND therefore only ever replaces a ½ with a
> definite value that the exact semantics also gives. **It cannot produce a value the exact semantics
> does not.**

> **Normative (Q-MONO — a definite body decides over a ⊤ sequence, in exactly two of four cells).**
> Let `p` be the quantifier's body evaluated with every comprehension target at ⊤. Then, for a `seq`
> that resolves to ⊤:
>
> | | `p` is `T` | `p` is `F` | `p` is ½ |
> |---|---|---|---|
> | `AllOf(seq, p)` | **`T`** | ½ | ½ |
> | `AnyOf(seq, p)` | ½ | **`F`** | ½ |
>
> **The two decided cells are the ones that are also true of the empty sequence**, which is the whole
> argument: `all(...)` over an empty sequence is `True` and `any(...)` over an empty sequence is
> `False`, so an unknown length cannot falsify either. The two ½ cells are the ones the empty sequence
> falsifies — `AllOf` over an empty ⊤ seq with an `F` body is `T`, not `F` — and they stay ½ **by
> rule**, which is increment 6 A-C3's own "never vacuously `T`" clause preserved in both directions.
> A `seq` that resolves to a concrete `Seq` is governed by Q-BIND, not by this table; the two rules do
> not overlap.
>
> **This is the clause that decides `:514`**, and it decides it without resolving the `Zip`: `p` is
> R-CONST's `T`, the seq is ⊤, `AllOf` is `T`, `Not` is `F`, the `raise_guard` does not fire.

### 16.5.6 R-DECK — `self.deck.get_resource(<name>)`, conditional on D2

> **Normative (CONDITIONAL — this rule ships iff the user takes D2, and is absent otherwise).**
> `Cmp(EnvRef(("self", "deck", "get_resource"), (t,)), "==", u)` — the exact shape at
> `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:318-321`, where `t` is
> `Attr(u, "name")` for the *same* term `u` — evaluates **`T`** iff `u` resolves to a `Ref` whose slot
> carries a resource whose name is a member of the observation's `deck_resource_names`, and **½**
> otherwise. It **never** evaluates `F`: a name absent from the deck makes `get_resource` raise
> `ResourceNotFoundError` at `external/pylabrobot/pylabrobot/resources/resource.py:566-589` **before**
> the comparison, so the guard at `:321` is not the site that fires and a `WILL_FAIL` there would name
> the wrong statement.
>
> **The `T` branch rests on A-DECK-OBJECT (§16.1.3) and on nothing else.** The observation supplies
> membership; the assumption supplies the structural equality `Resource.__eq__` demands
> (`external/pylabrobot/pylabrobot/resources/resource.py:160-170`) and the IR cannot represent
> (`plr-sema/src/plr_sema/check/ir.py:178-191`). **Both halves must be stated wherever this rule is
> stated**; a version of this box that mentions only the observation is the version this document
> exists to prevent.
>
> **Matching `u` requires a name.** The comparison's left operand names `u.name` and the IR carries no
> name, so the rule is keyed by **slot**: `u` resolves to a `Ref` with a slot, and the observation is
> threaded to the evaluator as a **per-slot** boolean built by the harness that also built the
> RESOURCE instructions (`resources_from_example`, `plr-sema/eval/oracle_common.py:463`), which knows
> both the slot index and the name. In the graph lane, where no such harness exists, the rule declines
> and `:321` is ½ — a lane asymmetry recorded here rather than discovered, exactly as increment 6
> §15.4's O1 disclosure records its own.

---

## 16.6 Q1 — the scoped joined verdict

Increment 6 §15.5 established the representation's two halves and left the third. Tier (iii) is derived
from `is_dynamic_raise` (`plr-sema/src/plr_sema/check/predicate.py:796-800`); it emits **one**
`Finding`, `UNKNOWN`/`guard_env_dependent`, and folds its site into `AnalysisReport.scope.excludes_sites`
(`plr-sema/src/plr_sema/check/__init__.py:409-470` collects them, `:920-955` constructs the report,
`plr-sema/src/plr_sema/verdict.py:261-275` is the `SoundnessScope` type and `:298-310` the optional
field). It also **rejected, as unsound and must-not-implement, emitting tier (iii) as `SAFE` with a
marker**, because `join` would then claim the backend did not raise — A-COMPLETES applied to the
current operation (`.praxia/docs/specs/260902_plr-sema-tip-typestate-increment.md:752`).

**The consequence is structural and is not negotiable: under the unchanged `join`, `pick_up_tips` can
never join to `SAFE`, even with every tier-(ii) site discharged.** Every liquid-handling operation
carries a re-raise, the re-raise emits `UNKNOWN`, and one `UNKNOWN` makes the operation `UNKNOWN`
(`plr-sema/src/plr_sema/verdict.py:313-323`). So the question Q1 asks is not *"can we get a joined
`SAFE`"* but *"what is the honest name for what the analyzer does know."*

> **Normative (the representation: a SECOND, additive report field, computed by the UNCHANGED `join`).**
> `AnalysisReport` gains one optional field beside `scope`:
>
> ```
> scope_verdict: Verdict | None = None
> ```
>
> computed as `join(tuple(f for f in findings if f.plr_site not in scope.excludes_sites))` — the
> **same** function, the **same** table, over a **sub-multiset** of the same findings. `verdict` is
> untouched, is still `join(findings)`, and on every operation carrying a re-raise is still `UNKNOWN`.
> `scope_verdict` is `None` whenever `scope` is `None`, so **no report that never saw a tier-(iii)
> guard gains one** and every pre-increment-7 report is bit-identical.
>
> **`join` is not modified, not overloaded and not called with a flag.** It stays the one function in
> the package permitted to aggregate, its own docstring's claim stays true, and the filtering happens
> at the one call site in `_check` (`plr-sema/src/plr_sema/check/__init__.py:920-955`) where
> `excludes_sites` is already in hand. An implementation that taught `join` about scope would be the
> configuration `SoundnessScope`'s own docstring refuses.

> **Normative (wire and schema).** `schema_version` stays **1**
> (`plr-sema/src/plr_sema/verdict.py:298-310`). This is an additive optional field with a `None`
> default, which is the additive direction main spec Open decisions 3 records
> (`.praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md:3322-3326`): only **old readers** break on
> new reports, and they do not break here because they never read the field. No `IR_VERSION` bump; the
> IR is untouched.

> **Normative (what `scope_verdict == SAFE` asserts, and the four things it does not).**
>
> **It asserts:** *every PLR precondition guard this analyzer evaluated for this operation, other than
> those named in `scope.excludes_sites`, does not fire against this call, under the observation
> recorded in `env`.*
>
> **It does NOT assert:**
> 1. **that the operation completes.** A-COMPLETES is not discharged and is not implicated: the field
>    says nothing about the backend, which is exactly what `excludes_sites` names.
> 2. **that the backend accepts the call.** `:576` and its three siblings are precisely the excluded
>    sites.
> 3. **that a guard the analyzer never derived does not fire.** It cannot: a coverage gap emits an
>    `UNKNOWN` `Finding` — `guard_predicate_unparsed`, `unresolved_delegate` or `no_contract_derived` —
>    which is **inside** the sub-multiset and blocks `SAFE` under `join`'s third row. This is a property
>    of the construction, not a caveat, and it is why the field can be built from `join` at all.
> 4. **anything under a different observation.** The verdict is a function of `env`, which is the fifth
>    `cache_key` component (`plr-sema/src/plr_sema/check/ir.py:918-953`). A reader who wants the
>    unconditional claim reads `verdict`.

> **Normative (how `compare` scores it: TWO counters, neither replacing the other).**
> `oracle_common.compare` reads `st[oid]["verdict"]` and computes
> `unsound = (verdict == "safe" and outcome.startswith("raised")) or (verdict == "will_fail" and outcome == "ran_ok")`
> (`plr-sema/eval/oracle_common.py:767-786`). **That predicate, that field and that counter are
> unmodified and their definition does not change.** The static side additionally publishes
> `scoped_verdict` per operation, and `compare` additionally emits `unsound_scoped`, computed by the
> **same** predicate over `scoped_verdict` and then narrowed by §16.7's frame capture. Both counters are
> published; the gate reads both; neither is derived from the other.
>
> **The alternative — replacing `verdict` with `scoped_verdict` in the fence — is REJECTED and must not
> be implemented.** It would silently retire the only number that has been at 0 across five increments.

---

## 16.7 The fence

Increment 6 §15.5 left the tier-1 unsoundness predicate **unmodified**, deleted the draft's
`exc_class → site` narrowing outright, and moved the frame capture that would make a site-keyed
narrowing honest to this increment by name. The reason it moved rather than shipped is recorded there:
`TypeError` is raised at four PLR precondition sites **and** re-raised at `:576`, so an
exception-class-keyed narrowing excuses precisely the rows the fence exists to catch.

> **Normative (F1 — the frame capture).** `verify()` gains one additive result key beside
> `volume_tracking_observed` (`training/verify/verifier.py:184-200`):
>
> ```
> error_frame: {"file": str, "lineno": int, "qualname": str} | None
> ```
>
> set from `traceback.extract_tb(e.__traceback__)[-1]` at **both** `except` handlers — the inner one
> that catches an operation failure and the outer one that catches a harness/deck failure
> (`training/verify/verifier.py:130-144`) — and `None` when `error` is `None`. `file` is made relative
> to the repo root; `qualname` is the frame's function name. **Three lines per handler**, exactly the
> size increment 6 §15.13 recorded. `error` itself, `f"{type(e).__name__}: {e}"`, is unchanged, and so
> is `exc_class`, which `run_runtime` still splits off it
> (`plr-sema/eval/oracle_common.py:415-439`).

> **Normative (F2 — the narrowing, and it is site-keyed and nothing else).** A row is excused from
> `unsound_scoped` **iff all three** hold:
>
> 1. the row's `scoped_verdict` is `safe` and its `outcome` starts with `raised`;
> 2. `error_frame` is present; and
> 3. `(error_frame.file, error_frame.lineno)` matches a `PlrSite` in that report's
>    `scope.excludes_sites`.
>
> **Everything else is counted.** In particular a `scoped_verdict == "safe"` row whose raising frame is
> a **PLR precondition** site is counted as unsound, and **that is the failure this increment
> introduces for the first time.** No increment before this one could produce it: increments 1–5 could
> not reach a joined `SAFE` at all and increment 6 §15.5 proved it structurally unreachable. It is
> named here so a non-zero `unsound_scoped` at T46 is read as this document's own prediction failing,
> not as an instrument fault.
>
> **`exc_class` appears nowhere in the comparison path**, exactly as increment 6 §15.10 requires and
> for the same reason. The narrowing keys on the **frame**, which is a fact about where the exception
> was raised, not on the class, which is not.

> **Normative (F3 — the unscoped fence is untouched, and its untouchedness is asserted rather than
> assumed).** `unsound` stays exactly `plr-sema/eval/oracle_common.py:767-786`, over `verdict`, with no
> narrowing, no excuse and no frame test. `rows_excused_by_scope` — increment 6's pure annotation,
> measured **0** at T36 (`outputs/plr-sema/oracle_replay_260909_inc6.json:2-21`) — keeps its definition
> and gains a sibling, `rows_excused_by_frame`, for F2's own count. AC-16.8 asserts that the two
> unscoped numbers are byte-identical to the `260909_inc6` run.

> **Normative (F4 — tier 2b parity).** `region_oracle._run_fixture_execution` gains the identical
> capture inside its own `try`, and its region comparison gains the identical narrowing. Increment 5
> §14.6 records tier 2b's execution-order asymmetry as a live hazard — the executed side runs first and
> a process-global leaks — so a fence that narrowed on tier 1 and not on tier 2b would make the two
> lanes incomparable at exactly the point the comparison matters.

---

## 16.8 Reasons

> **Normative: `REASON_VOCABULARY` does NOT change. It stays at 12 of 12, HM-14's `declared` stays 12,
> and no thirteenth member is proposed.** The vocabulary is
> `plr-sema/src/plr_sema/verdict.py:147-199` and HM-14 is `REASON_VOCABULARY`'s own registry row
> (`plr-sema/src/plr_sema/_hand_maintained.py:648-667`), `CAPPED` at `declared=12` with **zero
> headroom** after increment 6 spent it.
>
> **Every give-up point this increment adds folds into an existing member, mechanically:**
>
> | new give-up point | member | why it is that member and not a new one |
> |---|---|---|
> | no observation present | `guard_env_dependent` | ≥ 1 free name resolves to state outside the call — the member's **first** clause, verbatim |
> | an `EnvRef` path §16.5 does not admit | `guard_env_dependent` | same clause; the shape is recognised and the environment is not read |
> | `caller_args` absent or partial at `depth == 1` | `guard_env_dependent` | the member already covers "the guard's reachability is not established — `depth >= 1`", and it equally covers a name that does not resolve |
> | a membership `Cmp` over a non-complete `Seq` | `guard_env_dependent` | the operand resolved; the *completeness* is the missing environment fact |
> | a quantifier over a ⊤ seq with a ½ body | whatever §15.7's ordered procedure already assigns | unchanged; this increment adds no clause to that procedure |
>
> **§15.7's ordered reason procedure is unchanged in every clause and in its order**: `contains_opaque`
> ⇒ `guard_predicate_unparsed`; else an operand of this call is ⊤ ⇒ `guard_operand_unknown`; else
> `contains_env_ref` and still undecided ⇒ `guard_env_dependent`; else the residual rules
> (`plr-sema/src/plr_sema/check/predicate.py:666-679` is the shipped operand test the second clause
> reads). **The gate's two zero-conditions are relaxed by nothing in this increment**, and §16.10
> republishes both counts so a reader can check rather than trust.

> **Normative (the one thing that would need a thirteenth member, named so it is a decision and not a
> discovery).** If a future increment wants to distinguish *"the observation was absent"* from *"the
> observation was present and the path is not admitted"*, that is a thirteenth reason and it is the cap
> conversation. This increment deliberately does **not** want that distinction: §16.10 publishes
> `n_resolved_by_rule` and `n_declined_by_rule` per rule, which carries the same information as a
> measurement without spending a wire slot on it. That is the trade, stated so it can be disputed.

---

## 16.9 Registry

**New rows: zero. Retired rows: zero. `REASON_VOCABULARY` members: zero.** `live_rows()`
(`plr-sema/src/plr_sema/_hand_maintained.py:1015-1019`) is **24** against `BUDGET_CAP = 24`
(`plr-sema/src/plr_sema/_hand_maintained.py:43`) before and after; headroom **0**, unchanged. HM-24
stays at `declared` 3 and HM-14 stays at `declared` 12.

> **Normative (the ONE proposed spend, and it is the user's: HM-25 `declared` 9 → 10 — `D4`).**
> §16.5's four path-shape rules — R-HEAD, R-ATTR, R-CONST, R-DECK — are a **table of PLR path shapes**,
> which is precisely the thing increment 6 §15.4's `E-ENV` box forbade *"in this increment"* on the
> ground that it would be hand-maintained surface. It is. The row is **HM-25**, whose `what` already
> books `EnvRef` itself along with `Zip`, the membership comparators, α, β, P3a, P7, P8 and P9
> (`plr-sema/src/plr_sema/_hand_maintained.py:933-1011`), and whose `breaks_when` already records
> *"Fails LOUDLY here (unlike HM-24)"* with the published-count criterion this increment's §16.10
> satisfies. **One entry, one further ceiling unit, no second row, no cap conversation.**
>
> **Why one unit and not four.** The four rules are one pattern with four instances — *"an `EnvRef`
> path admitted against the observation record"* — in exactly the sense that P3a is one pattern with
> one instance and α is one pattern with three. Booking four would inflate the row to make the
> arithmetic look conservative, which is the mirror image of the gaming §9.4 forbids.
>
> **The measure must move with the `what`, on increment 6 A-C6's own precedent.** `_measure_hm25`
> measures HM-25 by **importing the symbols that implement its patterns**, so it fails loudly if any is
> deleted. Naming the path-shape table in the `what` without adding a measured symbol would leave a
> live pattern the measure cannot see — HM-24's *silent* criterion, which is the failure mode this row
> is chosen to avoid. **Normative for T43's registry spend: `_measure_hm25` must additionally import
> the path-rule symbol.** And the same contingency increment 6 wrote applies verbatim: **if the
> measured count would exceed 10, T43 STOPS and surfaces a further spend to the user rather than
> raising `declared` on its own authority.**

> **Normative (three things that cost NOTHING, each argued rather than asserted).**
>
> 1. **§16.3's derived backend surface.** An AST shape test over PLR's own recorded surface, keyed on
>    the derive package's existing function index, introducing no literal (§16.3's own box). Same class
>    as `is_dynamic_raise` and `reachability_clear`.
> 2. **§16.4's argument map.** A shape test over `ast.Call`/`ast.arguments`, fail-closed on every
>    unrecognised shape, adopting P9's two existing restrictions rather than inventing any. It is a
>    Python-language construct, which is verbatim increment 5 §14.11's accepted argument for B2 and P1c
>    and increment 6 §15.8's reason 3 for α and β.
> 3. **§16.6's `scope_verdict` and §16.7's frame capture.** A filter over an existing field and a
>    stdlib call. No pattern, no table, no literal.
>
> **Each is stated so a reviewer can break it.** The strongest available objection is against (2): P9
> is itself booked on HM-25, so the argument map is arguably the same pattern family. The reply is that
> P9 books a **channel-argument** shape — *"a keyword argument at a `self.<delegate>(...)` call site
> holding an int-constant display"* — i.e. a shape recognised for its *content*, whereas the argument
> map recognises no content at all: it maps positions to parameters and refuses everything else. If the
> round rejects that distinction, the disposition is a **second** unit on the same row and the ask
> becomes 9 → 11; it is not a new row either way.

---

## 16.10 Measured sets and the gate

### 16.10.1 What T46 publishes

> **Normative.** The measured report publishes, over the frozen benchmark and the regenerated contract
> table:
>
> 1. **Per `E-ENV` rule** (R-HEAD, R-ATTR, R-CONST, and R-DECK when D2 is taken):
>    `n_resolved_by_rule` and `n_declined_by_rule`, whole-table and per executed operation. **This is
>    the block that makes §16.5's reach inspectable**, and it is the analogue of increment 6 block
>    (6)'s `n_env_ref_refused_plr_layer`: a reader who suspects a rule is a sink for arbitrary paths
>    reads its own counts rather than this document.
> 2. **`n_membership_decided`**, per site and whole-table, with the site list, discharging §16.5.4's
>    reopening condition (iii).
> 3. **The argument map's complete measured selection**: every `(K, D)` pair mapped, its call site's
>    `lineno`, the parameter→`Term` pairs, and — separately — the count of `(K, D)` pairs **refused**,
>    broken down by which of M1's six conditions refused it. Plus `name_coincidence_exposure_count` at
>    `depth == 1`, asserted **0** (§16.4's M2 box).
> 4. **§16.3's surface**: the number of `(class, method)` rows, the number with `constant_return`, and
>    the per-method breakdown for `can_pick_up_tip` against this document's predicted **2 of 8**.
> 5. **Per executed operation**: `verdict`, `scope_verdict`, the residual reason set, and the list of
>    non-excluded sites carrying an `UNKNOWN`. **The gate number is computable from this block alone,
>    without reading this document.**
> 6. **The fence**: `unsound` (unscoped, unmodified), `unsound_scoped`, `rows_excused_by_scope`,
>    `rows_excused_by_frame`, and — for every excused row — the captured frame, so an excuse can be
>    audited one row at a time.
> 7. **The after-ledger delta** against `outputs/plr-sema/unknown_ledger_260909_after.json`, on
>    `n_findings_by_reason`, `n_clusters` and `per_op_reason_set_histogram`, with `consistency.ok` true.

### 16.10.2 The gate

> **Normative (the GO condition).**
>
> > **GO iff ≥ 1 executed real operation reaches `scope_verdict == SAFE`, with tier-1 `unsound == 0`
> > under the unmodified predicate AND `unsound_scoped == 0` under §16.7's narrowing.**
>
> NO-GO otherwise: publish the counts and the structural reason in §16.16, keep everything landed (it
> is a strict information gain on the contract table and on the ledger either way), and bring the
> decision to the user.
>
> **Why the gate is not stated over reasons, as increment 6's was.** Increment 6's gate had to be
> stated over reasons because it could not reach a joined verdict at all and needed a proxy that was
> not self-satisfying. This increment ships the joined field, so the gate is stated over the field
> itself — which is stronger, because it cannot be met by a relabelling. **Every reason count is still
> published**, and §16.10.3's per-site table is what makes a NO-GO diagnosable rather than merely
> recorded.

### 16.10.3 The prediction, per site and per method

> **Normative (this table is a PREDICTION for T46 to falsify, cell by cell, and a divergence in either
> direction is recorded rather than absorbed.)** Counts are the ledger's frozen population.

**`pick_up_tips` — the gate candidate, 223 operations:**

| site | today | predicted after increment 7 | by what |
|---|---|---|---|
| `:498` | `SAFE` on **216** of 223 | unchanged, 216 | O1-conditional; the 7 are increment 6's own disclosed residual |
| `:502` | `SAFE` 223 | unchanged | G4 + `channels_for_call` |
| `:522` | `SAFE` 223 | unchanged | G2 + β + `E-CALL(β)` |
| `:535` | decided 223 | unchanged | the tip family |
| `:409` | ½ 223 | **`SAFE` 223** | §16.4 M1 + R-HEAD + §16.5.4 + Q-BIND |
| `:514` | ½ 223 | **`SAFE` 223** | §16.3 `constant_return` + R-CONST + Q-MONO |
| `:321` | ½ 223 | **`SAFE` 223 iff D2**, else ½ 223 | R-DECK + A-DECK-OBJECT |
| `:375` | ½ 223 | **½ 223 — no change** | needs D5 |
| `:383` | ½ 223 | **½ 223 — no change** | needs D5 |
| `:576` | `UNKNOWN` + `excludes_sites` | unchanged | tier (iii), derived |
| **`scope_verdict`** | — | **`UNKNOWN` on all 223** | `:375` and `:383` are inside the scope and are `UNKNOWN` |

**Every other method, so the round can falsify the whole table and not one row of it:**

| method | ops | which of this increment's sites it carries | predicted `scope_verdict` | why NO-GO |
|---|---|---|---|---|
| `aspirate` | 77 | `:409` (via `self._make_sure_channels_exist(use_channels)` at `:980`) | `UNKNOWN` | `:375`/`:383`; plus `:116` (`guard_predicate_unparsed`) and the unseeded volume cell |
| `dispense` | 40 | none of the three | `UNKNOWN` | `:375`/`:383`; `:116`; volume |
| `drop_tips` | 31 | `:409` (via `:665`), `:321` (D2) | `UNKNOWN` | `:375`/`:383`; `:657` and `:666` (§15.1.2) |
| `discard_tips` | 34 | `:409`, `:321` (D2) | `UNKNOWN` | `:375`/`:383`; `:822`'s rebinding; `guard_operand_unknown` |
| `transfer` | 19 | `:409` (inherited) | `UNKNOWN` | `:375`/`:383`; `:990`/`:1202` need γ; `:116` |
| `stamp` | 27 | none | `UNKNOWN` | `:375`/`:383`; branch-bound `containers` |
| `move_*` | 93 | none | `UNKNOWN` | `unresolved_delegate` — deferred row (e), out of scope by construction |

> **A qualification this document owes on `:409`'s reach, stated rather than buried.** `:409` clears on
> `pick_up_tips`'s 223 with high confidence: `channels_for_call` is measured non-`None` on every
> executed `pick_up_tips` operation and `:502`'s dependence on the same resolution is measured decided
> at 223/223 (`outputs/plr-sema/oracle_replay_260909_inc6.json:109-125`). On the other **161** — 77
> `aspirate`, 34 `discard_tips`, 31 `drop_tips`, 19 `transfer` — it clears only if the caller-side
> `use_channels` resolves in each of those methods, which no number anywhere covers and which
> `E-CALL(5)`'s parameter-rebinding clause may block (`aspirate` rebinds `use_channels` at `:958`,
> above its delegate call at `:980`). **The prediction is therefore 223 certain and up to 384**, and
> T46 must publish the per-method count. A hedged cell is unfalsifiable, so this one is split into an
> exact claim and a named uncertainty rather than written as a range.

**Aggregate predictions, each a single number T46 either matches or does not:**

- `n_findings_decided` **1,563 → ≥ 2,170** without D2 (`:409` 384 + `:514` 223), **≥ 2,458** with D2
  (+ `:321` 288). Today's value and its per-site breakdown are at
  `outputs/plr-sema/oracle_replay_260909_inc6.json:109-125`.
- `guard_env_dependent` **4,138 → ≈ 3,531** without D2, **≈ 3,243** with it.
- `n_clusters` **53 → 51** without D2, **50** with it.
- `guard_predicate_unparsed` **495 → 495, unchanged** — this increment adds no production to the
  grammar and touches no coverage gap. **A movement in this number means something unintended
  happened.**
- `unknown_rate` **1.0 → 1.0**, and `scope_verdict == SAFE` on **0** operations. Both are predicted, and
  recording them here is what stops a 1.0 at close being read as "the increment did nothing".

### 16.10.4 The anti-gaming counter

> **Normative (which productions and observations flip which sites — the falsification map).** The gate
> is stated over a field this increment introduces, so the burden is on this box.
>
> | mechanism | flips | does NOT flip | published counter |
> |---|---|---|---|
> | the observation alone (§16.2) | nothing | everything | `n_resolved_by_rule` all zero without §16.5 |
> | R-HEAD + membership + Q-BIND | `:409` only | `:321`, `:375`, `:383`, `:514`, `:116`, `:657`, `:2030` | `n_membership_decided`, predicted 384 at exactly one site |
> | R-CONST + Q-MONO | `:514` only | every guard whose body is not a constant-return backend method | `n_resolved_by_rule[R-CONST]`, predicted 223 |
> | the argument map alone (§16.4) | nothing by itself | — it binds names; it decides no guard | the refusal breakdown by M1 condition |
> | R-DECK + A-DECK-OBJECT (D2) | `:321` only | everything else | `n_resolved_by_rule[R-DECK]`, predicted 288 |
> | `scope_verdict` (§16.6) | **no site at all** | — it is a `join` over a subset | `scope_verdict` per op, predicted `UNKNOWN` on 544 |
>
> **The two cheap ways to pass this gate, both named and both REFUSED.**
>
> 1. **Put `:375` and `:383` into `excludes_sites`.** They are tier (ii) by §15.1's definition — a
>    property of the backend's signature — so a reader could argue they belong in a scope that already
>    excludes backend outcomes. **Refused.** `excludes_sites` is **derived**, from
>    `guard.is_dynamic_raise` and from nothing else
>    (`plr-sema/src/plr_sema/check/predicate.py:796-800`); it is not a site list and admitting one is
>    the configuration increment 6 §15.1's derived-tier box exists to prevent. Both guards raise
>    `TypeError` **from the PLR layer**, on real programs, for a real reason, and a scope that excluded
>    them would make `scope_verdict == SAFE` mean strictly less than "no PLR precondition fires" while
>    still being reported under that name. **This is the move that would have bought the headline, and
>    the reason it is refused is not cost.**
> 2. **Compute `scope_verdict` by anything other than the unchanged `join`.** Refused by §16.6's own
>    normative box. A `scope_verdict` that treated an `UNKNOWN` as absorbing-except-when-convenient
>    would pass this gate on the first operation that reached it.
>
> **The cheapest falsification of this whole document is one number**: `scope_verdict == SAFE` on ≥ 1
> operation at T46 without D5 having been taken. If that happens, §16.1.1's obstruction argument is
> wrong and this document's central claim fails.

---

## 16.11 The oracle and the mutants

**Tier 1 re-run is the gate, under the UNMODIFIED unsoundness predicate.** Baseline, from the T36 run
this document is written against: `rows_executed` **343** over `operations_executed` **548**,
`unsound` **0**, `crosscheck_joined` **191/191** at agreement 1.0, `rows_setup_error` **0**,
`n_findings_decided` **1,563**, `rows_excused_by_scope` **0**
(`outputs/plr-sema/oracle_replay_260909_inc6.json:2-21`). Every one of those numbers is re-measured and
any movement is attributed before the run is accepted.

**Non-regression, exact, from the same close:** m1 199/199, m2 289/289, v1 67/67 at the raised index,
tier 2b 16 fixtures with `region_unsound` 0 / `region_will_fail_fired` 7 / `volume_will_fail_fired` 3.
**The rule that could move tier 2b is Q-MONO**, by converting a previously-`UNKNOWN` guard to `SAFE`
inside an executed region; it is named here so a movement there is attributed rather than investigated.

> **Normative (p2 — the depth-1 `WILL_FAIL` mutant class, and it has exactly ONE mutator).**
> `plr-sema/eval/predicate_mutants.py` — the p1 producer, whose three mutators measured
> 288/288, 16/16 and 0/288 with **0 unsound** in every class at T36
> (`outputs/plr-sema/predicate_mutants_260909_inc6.json:2-58`) — is extended by:
>
> **(a) `p2a_channel_out_of_range`.** Mutate a planned `pick_up_tips` call's `use_channels` to contain
> an index `>= ` the observed `num_channels`. PLR raises `ValueError` at
> `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:405-409`; the static side must emit
> `WILL_FAIL` **at the raised index**. Floor: **≥ 1 achieved with 0 unsound in both directions.**
>
> **This is the only mutator that exercises D1's lift, and that is exactly why it is the class's
> point.** `:409` is at `depth == 1`; without D1 it can never emit `WILL_FAIL` and (a) reports 0
> achieved. **If D1 is declined, this class is withdrawn together with its acceptance criterion rather
> than left to report 0** — increment 6 §15.16.3's own lesson, that a class which can only ever report
> 0 is a publication and not a gate.

> **Normative (a second mutator on `:321` is NOT constructible, and the reason is a fact about PLR).**
> The obvious dual — pass a resource that is not on the deck — does **not** make `:321` fire. It makes
> `Resource.get_resource` raise `ResourceNotFoundError` at
> `external/pylabrobot/pylabrobot/resources/resource.py:566-589`, one line earlier and at a site the
> contract table carries no guard for. Constructing a resource that *is* on the deck by name and
> unequal by `Resource.__eq__` requires building a second object with matching name and mismatched
> geometry, which the mutator API (which mutates a planned call's kwargs) cannot express.
> **Consequence, stated as a property of the site: `:321` can only ever produce `SAFE`**, its `T`
> branch is unreachable by construction (§16.5.6), and the only instrument that checks it is the
> tier-1 fence on 288 real operations. That is a real argument **for** D2 rather than against it, and it
> is also the reason D2's own acceptance criterion is a fence assertion and not a mutant floor.

---

## 16.12 Acceptance criteria

- **AC-16.1 (the observation record, its closure, and the fail-closed identity).** `verify()` returns
  `plr_observation` with exactly the four fields of §16.2.1 and no others, taken at the two normative
  points; a fixture asserts `head_channels` is non-empty **after** `machine.setup()` and that reading it
  before returns the empty dict, which is the placement half. `env` carries the three `obs:` members in
  the canonical encoding, and a round-trip fixture asserts that two runs producing the same observation
  produce the **same** `env` set regardless of iteration order. **The stub-defeating half is the
  identity assertion**: with `env` empty, `check_ir` over the shipped fixtures produces findings
  **byte-identical** to the pre-increment-7 run, asserted as an equality over the whole finding tuple
  and not as a count — an implementation that resolved an `EnvRef` from a default rather than from the
  observation passes every other fixture and fails this one. A second fixture asserts a **partial**
  observation (`head_channels` present, `backend_class` absent) is refused wholesale and resolves
  nothing.
- **AC-16.2 (the derived backend surface, measured and keyed on PLR's own index).**
  `plr-sema/data/derived_contracts.json` gains the `backend_surface` top-level key; its complete
  measured selection is published, including the whole-tree count of `can_pick_up_tip` definitions and
  the count of those with a `constant_return`, asserted **2** at this pin with the two files named. A
  grep over the derive package asserts the literal string `LiquidHandlerBackend` occurs **nowhere** in
  the surface's derivation — that is the no-hand-typed-fact claim of §16.3 made checkable, and it is
  this criterion's stub-defeating half. Four shape fixtures, one apiece: a single `return True` body is
  admitted; a **docstring-plus-return** body is **not**; a two-statement body is not; a `return <Name>`
  body is not.
- **AC-16.3 (the delegate→caller argument map binds, is measured, and fails closed).** The complete
  `(K, D, param, Term)` selection is published with `self._make_sure_channels_exist(use_channels)` and
  `self._assert_resources_exist(tip_spots)` (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:520-522`)
  asserted present **by name**, and the refusal count broken down by which of M1's six conditions
  refused each pair. Six fail-closed fixtures, one per condition: a module-level delegate binds
  nothing; a delegate called twice binds nothing; an `ast.Starred` argument binds nothing; a delegate
  with `**kwargs` binds nothing; an argument that does not parse as a `Term` binds **only that
  parameter** to nothing while the others still bind; and a `depth == 2` guard binds nothing.
  `name_coincidence_exposure_count` at `depth == 1` is asserted **0**. The partial-map fixture and the
  depth-2 fixture are the stub-defeating halves.
- **AC-16.4 (depth-1 `WILL_FAIL` only under all three preconditions — CONDITIONAL on D1).** A depth-1
  guard evaluating `T` with `reachability_clear` true, `caller_reachability_clear` true, an
  `E-UNCOND`-satisfied `caller_scope_trail` and a total map yields `Verdict.WILL_FAIL` with
  `category == "precondition_state"`; the same guard yields `UNKNOWN`/`guard_env_dependent` under each
  of **five** perturbations, one fixture apiece: `reachability_clear` false; `caller_reachability_clear`
  false; `caller_reachability_clear` **absent** (⇒ `None` ⇒ blocked); an unsatisfied
  `caller_scope_trail` entry; and one free name resolving to ⊤. A sixth asserts `depth == 2` is still
  forbidden unconditionally. **The absent-field fixture and the depth-2 fixture are the stub-defeating
  halves.** If D1 is declined this criterion is withdrawn together with its task row rather than left
  unsatisfied.
- **AC-16.5 (the four `E-ENV` rules resolve exactly what §16.5 says and nothing else).** Positive, one
  apiece: R-HEAD resolves `self.head` to the observed complete `Seq`; R-ATTR resolves
  `self.backend.num_channels` to `Lit(8)`; R-CONST resolves
  `self.backend.can_pick_up_tip(<⊤>, <⊤>)` to `Lit(True)` **with both arguments at ⊤**, which is
  argument-independence made checkable and is this criterion's stub-defeating half. Negative, one
  apiece: `self.head96` is ⊤; `self.head[channel]` is `Opaque` unchanged; `self.backend.<m>` for an `m`
  with no `constant_return` is ⊤; `self.backend.<m>` **inherited** rather than defined on the observed
  class is ⊤ (the no-MRO-walk rule); and any path not in §16.5's four shapes is ½/⊤. Whole-table:
  `n_resolved_by_rule` is published per rule and R-ATTR's is asserted **0** at this pin.
- **AC-16.6 (the membership case and the two quantifier clauses).** Membership: a `not in` against an
  R-HEAD-resolved complete `Seq` decides; a `not in` against a `Var` resolving to an ordinary `ir.Seq`
  is **½**, asserted **not** `T` — the `ir.Seq`-is-a-lower-bound rule made checkable, and the
  stub-defeating half of this group. Q-BIND: `AnyOf` over a concrete `Seq` with a recorded single-name
  `target` binds element-wise and returns `F` when every element's body is `F`; the same node with
  `target` **absent** returns ½; a **tuple** target returns ½. Q-MONO: all four cells of §16.5.5's
  table are asserted individually, with `AllOf(⊤, F)` asserted **½** and `AnyOf(⊤, T)` asserted **½** —
  the two vacuity cells, which are the second stub-defeating half.
- **AC-16.7 (the scoped joined verdict).** `AnalysisReport.scope_verdict` is `None` whenever `scope` is
  `None`; equals `join` over the non-excluded findings otherwise; `verdict` is asserted **unchanged**
  on the whole shipped fixture set; `schema_version` is asserted **1**; and `join` itself is asserted
  called with a plain tuple and no keyword, by AST scan of the call site. One fixture constructs a
  report whose only `UNKNOWN` is a tier-(iii) finding and asserts `verdict == UNKNOWN` **and**
  `scope_verdict == SAFE` simultaneously — the two-fields-two-claims property. A second constructs one
  whose non-excluded findings include a `guard_predicate_unparsed` and asserts `scope_verdict ==
  UNKNOWN`, which is §16.6's claim (3) made checkable and this criterion's stub-defeating half.
- **AC-16.8 (the fence: the frame capture, the narrowing, and the untouched unscoped counter).**
  `verify()` returns `error_frame` with `file`/`lineno`/`qualname` for a raising row and `None`
  otherwise, from both handlers; a fixture asserts the captured frame for a `pick_up_tips` row that
  raises inside `_make_sure_channels_exist` names that function's own `qualname`, not the entry point's.
  `unsound` and `rows_excused_by_scope` are asserted **byte-identical** to
  `outputs/plr-sema/oracle_replay_260909_inc6.json:2-21`. `unsound_scoped` is published with
  `rows_excused_by_frame`, and every excused row's captured frame is published beside it. A fixture
  asserts that a `scope_verdict == "safe"` row raising at a **PLR precondition** frame is counted as
  `unsound_scoped` and **not** excused — the failure this increment introduces, asserted positively,
  which is the stub-defeating half. Tier 2b carries the identical capture and narrowing.
- **AC-16.9 (tier 1 — 0 unsound in both counters, and the decided-findings floor).** The
  sidecar-gated replay reports `unsound == 0` under the unmodified predicate,
  `unsound_scoped == 0`, `rows_setup_error == 0`, `rows_executed == 343`, crosscheck 191/191 at
  agreement 1.0. **The gated number is `n_findings_decided`**, per PLR site, with a floor of
  **≥ 2,170** — 1,563 plus `:409`'s 384 plus `:514`'s 223, derived from §16.10.3's own prediction
  rather than asserted — rising to **≥ 2,458** if D2 is taken. `guard_predicate_unparsed` is asserted
  **unchanged at 495**, which is the cheapest falsification of the claim that this increment touches no
  coverage gap. **The stub-defeating half: an implementation that threads the observation but reaches
  no atom scores `n_findings_decided == 1,563` and fails.**
- **AC-16.10 (non-regression, and the depth-1 mutant).** m1 199/199, m2 289/289, v1 67/67 at the raised
  index with 0 unsound, tier 2b at 16 fixtures with `region_unsound == 0` and
  `region_will_fail_fired >= 7` and `volume_will_fail_fired == 3`. p1's three mutators re-measured at
  288/288, 16/16 and 0/288 with 0 unsound — **unchanged**, which is what proves the E-UNCOND(4) lift did
  not disturb the depth-0 population. p2a is published with a floor of **≥ 1** achieved `WILL_FAIL` at
  the raised index and **0 unsound in both directions**, or is withdrawn with AC-16.4 if D1 is declined.
- **AC-16.11 (the measured sets are published and the gate is decided by them).** All seven blocks of
  §16.10.1 are present and non-null in the report; the GO/NO-GO is recorded against the published
  per-operation `scope_verdict`; and **the gate number is asserted computable from the JSON alone,
  without reading this document.** §16.10.3's per-site table is reproduced against the measurement cell
  by cell, and any divergence is recorded in §16.16 rather than absorbed. `:409`'s per-method count is
  published against the 223-certain / up-to-384 split.
- **AC-16.12 (this document is machine-checked).** `plr-sema/tests/test_spec_lint.py` gains a constant
  for this file and parametrises it into both live-spec tests; `.praxia/docs/INDEX.md` is regenerated;
  and `uv run pytest plr-sema/tests/test_spec_lint.py -q` is **actually run** with its result recorded
  — the citation checker reporting **zero** failing violations over this file and the AC-gating half of
  the cross-reference checker reporting zero, with the other seven specs unchanged at zero.
- **AC-16.13 (deck membership — CONDITIONAL, only if the user takes D2).** R-DECK ships with the
  per-slot observation; **A-DECK-OBJECT is added to increment 1 §10.6.3's named-assumption table with
  its own "what breaks if it is false" column**, and a test asserts the table has five rows. R-DECK is
  asserted to evaluate `T` or ½ and **never** `F`, by exhaustive fixture over both branches — the
  ResourceNotFoundError argument made checkable. `:321` is asserted `SAFE` on 288 operations with
  `unsound == 0` and `unsound_scoped == 0`. **If D2 is declined this criterion is withdrawn together
  with its task row rather than left unsatisfied.**
- **AC-16.14 (`_check_args` — CONDITIONAL, only if the user takes D5).** The five productions of
  §16.1.1's sizing box land with their own measured selections; `:375` and `:383` are asserted `SAFE`
  by name on 544 operations; `scope_verdict == SAFE` is asserted on ≥ 1 executed operation with both
  fence counters at 0. **If D5 is declined — which is this document's recommendation — this criterion
  is withdrawn together with its task row and becomes increment 8's.**

---

## 16.13 Task rows

> **Normative (the ordering, and it is forced by the same gate discipline increment 5 §14.0 and
> increment 6 §15.12 both impose).** **T40, T41 and T42 must land and publish their measured selections
> before T43 resolves a single `EnvRef`.** A landed resolution rule without a published observation and
> a published surface can construct a definite verdict whose basis nobody has inspected, which is the
> configuration §16.10's measured blocks (1)–(4) exist to prevent. **T44, T45 and T46 must land in that
> order**: a `scope_verdict` without a fence behind it is a `SAFE` nobody is checking.

> **Normative (why every AC is gated exactly once, and where the conditional rows sit).** The
> cross-reference lint reads the **gate cell only** — column 4 of a row matching `TASK_ROW_RE`
> (`plr-sema/scripts/check_spec_crossrefs.py:52-62`, with the gate cell taken as `cells[3]` and the
> `ac_multiply_gated`/`ac_ungated` checks at `plr-sema/scripts/check_spec_crossrefs.py:139-156`). An
> AC named in a scope cell, in a box, or in prose is documentation and not a gate. **AC-16.4, AC-16.13
> and AC-16.14 are gated on rows T42, T48 and T49 respectively, each of which is conditional on a user
> decision** — the same construction increment 6 used for AC-15.12 on T34, and the reason a declined
> decision withdraws the criterion **with** its row rather than leaving it unsatisfied.

| task | scope | files | gate | ~LOC | depends on | model |
|---|---|---|---|---|---|---|
| **T40** | **The observation record and its cache-key partition (§16.2).** `verify()` gains the additive `plr_observation` result key with exactly the four fields of §16.2.1, taken at the two normative points — `head_channels` after `machine.setup()` and before `_execute`, `deck_resource_names` off `before` — and returned by the executed side, never observed from outside the window; the harness reads it and builds the `obs:<key>=<value>` members in the canonical encoding; `env` is threaded unchanged through `check_ir`/`check_graph`; the `obs:` prefix is reserved and asserted never to satisfy `E-UNCOND` way (2); the closed refusal list is enforced by a test that fails if `plr_observation` grows a fifth key. **No resolution rule, no evaluator change, no verdict moves** — with `env` carrying the new members and §16.5 unlanded, every finding is byte-identical | modify `training/verify/verifier.py`, `training/verify/deck.py`, `plr-sema/eval/oracle_common.py`, `plr-sema/eval/region_oracle.py`, `plr-sema/tests/test_cache.py`, `training/tests/test_verify_postconditions.py` | `uv sync --all-packages`; `uv run pytest training/tests/test_verify_postconditions.py -q`; `uv run pytest plr-sema/tests/test_cache.py -q` (no test may pin a literal `cache_key`, and the empty-`env` key is asserted unchanged) — satisfying **AC-16.1** | ~180 | — | Sonnet — the fail-closed identity property is the whole of this row's value and it is asserted as an equality over findings, not as a count |
| **T41** | **The derived backend surface (§16.3).** A per-`(class, method)` table over `build_plr_function_index` recording non-default parameter names after `self`, `has_var_keyword`, `has_var_positional`, and `constant_return` under the exactly-one-`ast.Return`-of-an-`ast.Constant` shape test (a docstring counts as a statement); the selection derived from the contract table's own admitted `EnvRef` paths, with **no** literal base-class name and no method list anywhere in the derivation; published as the additive fifth top-level key `backend_surface` of `plr-sema/data/derived_contracts.json`, which regenerates and cools the cache by design; the complete measured selection published, including the whole-tree `can_pick_up_tip` count against the predicted 2 of 8 | modify `plr-sema/src/plr_sema/derive/__init__.py`, `plr-sema/src/plr_sema/derive/receiver_state.py`, `plr-sema/src/plr_sema/derive/__main__.py`, `plr-sema/data/derived_contracts.json` (regenerated), `plr-sema/tests/test_derive.py` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_derive.py -q`; `uv run pytest plr-sema/tests/test_cache.py -q`; then regenerate the contract table — satisfying **AC-16.2** | ~150 | — | Sonnet — the no-hand-typed-fact claim is checked by a grep assertion, and that assertion is the row's registry argument made executable |
| **T42** | **The delegate→caller argument map and the depth-1 lift (§16.4).** `compute_caller_args(K, D)` in `derive/bindings.py` under M1's six conditions, fail-closed on every other shape; the additive `caller_args` field on `InlinedGuard` carrying existing `Term` JSON, absent ⇒ `None`; M2's resolution ordering, with the caller-side `Term` evaluated in `K`'s context and `E-CALL(5)` applying in `K`; the additive `caller_reachability_clear` and `caller_scope_trail` pair; **D1's lift of `E-UNCOND(4)` at `depth == 1` under all three preconditions, and `depth >= 2` untouched**; the complete measured selection and the M1-condition refusal breakdown published; `name_coincidence_exposure_count` at depth 1 re-measured and asserted 0 | modify `plr-sema/src/plr_sema/derive/bindings.py`, `plr-sema/src/plr_sema/derive/__init__.py`, `plr-sema/src/plr_sema/derive/__main__.py`, `plr-sema/src/plr_sema/check/predicate.py`, `plr-sema/data/derived_contracts.json` (regenerated), `plr-sema/tests/test_derive.py`, `plr-sema/tests/test_check_graph.py` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_derive.py -q`; `uv run pytest plr-sema/tests/test_check_graph.py -q`; `uv run pytest plr-sema/tests/test_cache.py -q` — satisfying **AC-16.3** and **AC-16.4** (the latter conditional on **D1**; declined ⇒ this row ships the map without the lift and AC-16.4 is withdrawn with it) | ~170 | T41 | Sonnet — **the lift is the one clause in this increment that can produce a false positive on a clean operation**, and increment 6 round 1 filed six blockers in this direction |
| **T43** | **`E-ENV` resolution, the membership case and the two quantifier clauses (§16.5), with the registry spend.** R-HEAD, R-ATTR and R-CONST in `check/predicate.py`, each declining to today's ½/⊤ on an absent or partial observation; the membership deciding case reopened under §16.5.4's three conditions, with the `ir.Seq`-is-a-lower-bound rule stated in the evaluator and **no field added to `ir.Seq`**; **Q-BIND**, with the additive `target` (a `str`, or `None`) on `Filtered`/`AllOf`/`AnyOf`, written by `parse` for a bare-`ast.Name` target and `None` for a tuple target, absent ⇒ today's behaviour; **Q-MONO**, all four cells; per-rule `n_resolved_by_rule`/`n_declined_by_rule` and `n_membership_decided` published. **The approved HM-25 `declared` 9 → 10 spend (D4), filed as ONE further unit inside the existing entry whose `what` now also names the path-shape table, and `_measure_hm25` importing the path-rule symbol — stopping and asking the user if the measured count would exceed 10** | modify `plr-sema/src/plr_sema/check/predicate.py`, `plr-sema/src/plr_sema/derive/predicate_ast.py`, `plr-sema/src/plr_sema/derive/__main__.py`, `plr-sema/data/derived_contracts.json` (regenerated), `plr-sema/src/plr_sema/_hand_maintained.py`, `plr-sema/tests/test_hand_maintained_ratchet.py`, and the fixtures under `plr-sema/tests/fixtures/` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_check_graph.py -q`; `uv run pytest plr-sema/tests/test_hand_maintained_ratchet.py -q`; `uv run pytest plr-sema/tests/test_tip_typestate.py -q`; `uv run pytest plr-sema/tests/test_derive.py -q` — satisfying **AC-16.5** and **AC-16.6** | ~200 | **T40 + T41 + T42**, each with its measured selection published | Sonnet — four rules, one refinement of a shipped clause and one new clause, all in the `SAFE` direction; the two vacuity cells of Q-MONO are what stand between it and a false `SAFE` |
| **T44** | **Q1's scoped joined verdict (§16.6).** `AnalysisReport.scope_verdict`, computed at the one `_check` call site by the **unchanged** `join` over the findings whose `plr_site` is not in `scope.excludes_sites`; `None` whenever `scope` is `None`; `verdict` untouched; `schema_version` asserted 1; the static side publishes `scoped_verdict` per operation beside `verdict`. **`join` is not modified, not overloaded and not called with a flag**, asserted by AST scan of the call site | modify `plr-sema/src/plr_sema/verdict.py`, `plr-sema/src/plr_sema/check/__init__.py`, `plr-sema/eval/oracle_common.py`, `plr-sema/tests/test_verdict.py`, `plr-sema/tests/test_check_graph.py` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_verdict.py -q`; `uv run pytest plr-sema/tests/test_check_graph.py -q` — satisfying **AC-16.7** | ~90 | T43 | Sonnet — small, and the smallness is the point: the field is a filter plus a call to a function this row does not touch |
| **T45** | **The fence (§16.7).** The `traceback.extract_tb(...)[-1]` capture at both `verify()` handlers and in `region_oracle._run_fixture_execution`, returned as the additive `error_frame` key; F2's site-keyed narrowing, applied to `unsound_scoped` only; `rows_excused_by_frame` published with every excused row's captured frame; **`unsound` and `rows_excused_by_scope` unmodified in definition and asserted byte-identical to the `260909_inc6` run**; `exc_class` asserted absent from the comparison path | modify `training/verify/verifier.py`, `plr-sema/eval/oracle_common.py`, `plr-sema/eval/region_oracle.py`, `plr-sema/tests/test_oracle_replay.py`, `training/tests/test_verify_postconditions.py` | `uv sync --all-packages`; `uv run pytest training/tests/test_verify_postconditions.py -q`; `uv run pytest plr-sema/tests/test_oracle_replay.py -q` — satisfying **AC-16.8** | ~120 | T44 | Sonnet — the row exists so that the first `scope_verdict == SAFE`, whenever it arrives, arrives with an instrument already behind it rather than one built to explain it |
| **T46** | **The oracle, the mutants and the gate (§16.10, §16.11).** Tier-1 re-run under the unmodified predicate with both counters published; `n_findings_decided` per PLR site against the ≥ 2,170 floor; the after-ledger with `consistency.ok` and its published delta; §16.10.1's seven measured blocks; §16.10.3's per-site prediction table reproduced cell by cell with every divergence recorded; `plr-sema/eval/predicate_mutants.py` extended with p2a; the m1/m2/v1/tier-2b non-regression set re-measured; **the GO/NO-GO recorded against the published per-operation `scope_verdict`, computable from the JSON alone** | modify `plr-sema/eval/oracle_replay.py`, `plr-sema/eval/predicate_mutants.py`, `plr-sema/eval/unknown_ledger.py`, `plr-sema/eval/tip_mutants.py`, `plr-sema/tests/test_oracle_replay.py` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_oracle_replay.py -q`; then the tier-1 replay with its three standard flags, `unknown_ledger.py` into `outputs/plr-sema/unknown_ledger_2609XX_after.json`, `predicate_mutants.py`, `tip_mutants.py`, `volume_mutants.py` and `region_oracle.py` into `outputs/plr-sema/*_2609XX_inc7.json`, publishing the delta against the `260909_inc6` set — satisfying **AC-16.9**, **AC-16.10** and **AC-16.11** | ~220 | T45 | Sonnet — every published number is a measurement, and this row is where §16.1.1's central claim is either confirmed or falsified by one number |
| **T47** | Lint and index: register this file in `plr-sema/tests/test_spec_lint.py` and parametrise it into both live-spec tests; regenerate `.praxia/docs/INDEX.md`; **actually run the lint and record the result** | modify `plr-sema/tests/test_spec_lint.py`; regenerate `.praxia/docs/INDEX.md` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_spec_lint.py -q` — satisfying **AC-16.12** | ~6 | — | Haiku |
| **T48** | **CONDITIONAL on D2 — do not start without the user's answer.** Deck membership: the per-slot `deck_resource_names` observation threaded from `resources_from_example`; R-DECK, evaluating `T` or ½ and never `F`; **A-DECK-OBJECT added to increment 1 §10.6.3's named-assumption table with its own breakage column**, taking the table from four rows to five | modify `training/verify/verifier.py`, `plr-sema/eval/oracle_common.py`, `plr-sema/src/plr_sema/check/predicate.py`, `.praxia/docs/specs/260902_plr-sema-tip-typestate-increment.md`, `plr-sema/tests/test_check_graph.py` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_check_graph.py -q`; then re-run the tier-1 replay and re-measure — satisfying **AC-16.13** | ~110 | T43 | Sonnet — the assumption, not the observation, is what this row spends, and the fence on 288 operations is the only thing that checks it |
| **T49** | **CONDITIONAL on D5 — do not start; this document recommends NO and sizes it as increment 8's.** The `_check_args` model: a `set(<x>.keys())` `Term`, a set-difference `BinOp` `Term`, a set-display `Term`, the `E-SIG` rule over §16.3's surface for the three `inspect.signature` comprehension shapes, and the residual `**kwargs` key-set representation — each with its own measured selection and its own registry argument, plus a further HM-25 ceiling spend | modify `plr-sema/src/plr_sema/derive/predicate_ast.py`, `plr-sema/src/plr_sema/derive/bindings.py`, `plr-sema/src/plr_sema/check/predicate.py`, `plr-sema/src/plr_sema/_hand_maintained.py`, `plr-sema/data/derived_contracts.json` (regenerated) | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_derive.py -q`; `uv run pytest plr-sema/tests/test_check_graph.py -q`; then the full tier-1 replay and the whole non-regression set — satisfying **AC-16.14** | ~350 | increment 8 | Sonnet |

**Sizing note, stated honestly and with the one number that is a guess flagged as one.** T40 at ~180
is mostly harness plumbing and its own identity test. T41 at ~150 is one AST pass plus a selection
rule plus publication. T42 at ~170 is increment 6 §15.12's own ~90 LOC estimate for the map, plus ~50
for the two additive reachability fields and their round-trip, plus ~30 for the lift's three
preconditions. T43 at ~200 is the largest: ~60 for the three rules, ~30 for the membership case, ~50
for Q-BIND including the `target` field and its `parse` half, ~15 for Q-MONO, ~45 for the published
counters. **T46 at ~220 is the guess**: the measured blocks are new code but the re-runs are wall-clock,
and increment 6's comparable row came in at ~300 with a comparison path this one does not add.
**Total for the unconditional rows: ~1,146 LOC across seven rows, which is three sessions.** T48 adds
~110; T49 adds ~350 and is not budgeted here. **T43 at ~200 splits cleanly** at the three resolution
rules versus the quantifier clauses, and it is the row to split first if a session boundary falls
inside it. **Do not split T43 from T40/T41/T42 in the other direction**: a landed resolution rule
without published observation and surface selections is the configuration the ordering box exists to
prevent.

---

## 16.14 Not in this increment

- **`_check_args`.** The two guards on all 544 operations, sized at ~350 LOC and five productions in
  §16.1.1's box. **This is the only item on this list that costs the headline**, and it is D5.
- **The γ loop idiom, the bounded literal-display loop.** Increment 6 §15.13 deferred it here to be
  revisited *"alongside the pred-aware `BRANCH`"*. **Decision: it stays out**, and the argument is not
  cost. γ is a loop-recognition rule in increment 5 §14.6 R1's territory, and this increment already
  takes one clause in R1's own risk direction — D1's lift of `E-UNCOND(4)`, which newly permits
  `WILL_FAIL` on a population that could not previously emit one. Taking two reachability-widening
  rules in one increment puts them in the same measurement and makes a regression in either
  unattributable. Its beneficiaries, `aspirate` and `dispense`, are not gate candidates for three
  independent further reasons (`:116`, the unseeded volume cell, and `:375`/`:383`), so γ buys no
  operation anything this increment could report.
- **The `pred`-aware `BRANCH`** (increment 3 §12.3.6 B2). The same evaluator serves it; unchanged.
- **The lid topology** (`:116`/`:117`) **and the general `Identity(Term, Term)`.** Increment 4 §13.1's
  disposition stands. `:116`'s `lidded is resource` is an object-identity relation the IR models
  nowhere; §16.5 admits four **path** shapes and no relation. Admitting `Identity` would make four more
  methods GO candidates, which is precisely why it is refused here rather than there.
- **Tuple-display comparison** (`:2030`) and **arithmetic `BinOp` terms** (`:2211`,
  `volume_tracker.py:91`). Open decision 2's resolution stands unchanged; the latter is also the
  volume family's by the dispatch rule.
- **A fourth idiom for loop-append bindings** (`tips = []` then `tips.append(...)`) and for
  `n = len(<param>)`. Both are still a general dataflow pass by another name, and `tips` staying ⊤ is
  what §16.5.5's Q-MONO is built to work around rather than to hide.
- **The well-seeding observation** that would move `volume_state_unknown`. Refused by name in §16.2.1;
  it belongs to the volume family and to a gate this increment's does not read.
- **Replacing §8's hand-written-contract bridge.** §8 is not gating (AC-8.3); the debt is recorded, not
  discharged, exactly as increment 6 §15.13 records it.
- **Deferred row (e), the `move_*` family's `unresolved_delegate` gap**
  (`.praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md:2520`). 93 operations, 17% of the benchmark,
  outside every mechanism here. None of §16.5's rules touches a `<none>`-sited delegate gap.
- **Precision targets, deferred row (f)**
  (`.praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md:2524`). AC-16.9's floor is a floor against a
  null result, not a target.
- **A thirteenth `REASON_VOCABULARY` member.** §16.8's box names the one distinction that would need
  one and declines it in favour of a published counter.
- **A new registry row.** `live_rows()` stays 24 against `BUDGET_CAP` 24. Every mechanism here is
  either derived (§16.3, §16.4, §16.6, §16.7) or files onto the existing HM-25 entry (§16.5, D4).
- **#4923 / #4924** — decision hooks only, unchanged.

---

## 16.15 The questions, their dispositions, and every user decision hook

### Q1 — what is a joined `SAFE` *within scope*, and how is it represented?

**DISPOSED by §16.6: a second, additive `scope_verdict` field, computed by the unchanged `join` over
the findings whose site is not in `scope.excludes_sites`, with the unscoped `verdict` staying
`UNKNOWN`.** `schema_version` stays 1 on the additive-field rule
(`.praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md:3322-3326`). It asserts that no PLR
precondition guard the analyzer evaluated, outside the excluded sites, fires against this call under
the recorded observation; it asserts nothing about completion (A-COMPLETES,
`.praxia/docs/specs/260902_plr-sema-tip-typestate-increment.md:752`), nothing about the backend, and
nothing under a different observation. `compare` scores it with a **second** counter, `unsound_scoped`,
beside the unmodified `unsound` (`plr-sema/eval/oracle_common.py:767-786`), and neither replaces the
other. **The alternative considered and rejected: emitting tier (iii) as `SAFE` with a marker** —
increment 6 §15.5 already rejected it as unsound and must-not-implement, and nothing here reopens it.

### Q2 — is `:321` decidable without a name on `ir.Resource`?

**DISPOSED by §16.1.3: only under a named assumption, and that is a user decision.** A membership
observation decides the `ResourceNotFoundError` half and not the `__eq__` half; `Resource.__eq__` is
structural over name, geometry, location, category and children
(`external/pylabrobot/pylabrobot/resources/resource.py:160-170`) and the IR's `Resource` carries none
of those (`plr-sema/src/plr_sema/check/ir.py:178-191`). Adding `name` to `ir.Resource` costs an
`IR_VERSION` bump and decides only the half that is already true by construction; **rejected on
those grounds and recorded as rejected.** The remaining options are the assumption (**D2**) or ½.

### Q3 — is a depth-1 `WILL_FAIL` permitted?

**DISPOSED by §16.4's D1 box: recommended YES, under three preconditions and no fewer** — the
delegate's `reachability_clear`, a new `caller_reachability_clear` plus an `E-UNCOND`-satisfied
`caller_scope_trail`, and a total argument map for the guard's free names. `depth >= 2` stays forbidden
unconditionally. **The cost of declining is that this increment adds no `WILL_FAIL` population at all**
and its two new decidable sites are exercised in one direction only; the cost of taking it is a clause
in the false-positive direction, fenced by tier 1 on 544 operations and by p2a.

### Q4 — what shape does the observation take in the cache key?

**DISPOSED by §16.2.3: `obs:<key>=<value>` members of the existing fifth `env` component, not a sixth
component.** The tuple's arity is a wire fact every caller and every persisted key sees; `env` exists
for exactly this and its `tuple(sorted(env))` encoding already guarantees the two properties
`cache_key`'s docstring requires (`plr-sema/src/plr_sema/check/ir.py:918-953`). The `obs:` prefix is
reserved so no member can satisfy `E-UNCOND` way (2), which is what prevents an observation from
manufacturing reachability.

### Q5 — what may the headline claim?

**DISPOSED, and this is the disposition the sprint most needs: the headline the user substituted into
increment 7 on 260907 is NOT reachable in increment 7, and the sprint may not report a joined `SAFE`.**
What it may report is: two of the gate candidate's six residual sites decided, a third under D2, the
scoped verdict representation shipped with a fence behind it, and the remaining distance reduced to
**two named lines of one named PLR function** with a sized route to closing them. **The user is owed
this before the work starts and not at a gate**, which is the one respect in which this document
improves on increment 6's own late discovery of the same class of finding. §16.10.4's last paragraph
states the cheapest falsification of the claim.

### Q6 — increment 6 §15.16.3 R1's owed adversarial review

**Increment 6's E-UNCOND(5) refinement — "an earlier `ast.Raise` or `assert` does not block a depth-0
empty-trail `WILL_FAIL`" — was measured (0 unsound on tier 1 and on all three p1 classes,
`outputs/plr-sema/predicate_mutants_260909_inc6.json:2-58`) and never attacked.** It is restated here as
five numbered claims so the round can attack them individually rather than the paragraph as a whole.

> **R1-C1.** Let `G` be a depth-0 guard whose `scope_trail[1:]` is empty, whose predicate evaluates
> `T`, and for which `compute_reachability_clear` returns `True`
> (`plr-sema/src/plr_sema/derive/bindings.py:778-815`). Then `K` contains no `ast.Return` at a lower
> `lineno`, `G` is not lexically enclosed by an `ast.Try`/`ast.With`, and `K` contains no earlier
> `ast.Break`/`ast.Continue`.
>
> **R1-C2.** Under R1-C1, exactly two executions of `K` are possible with respect to any earlier
> `ast.Raise` or `assert` `R`: either `R` fires, or it does not.
>
> **R1-C3.** If `R` fires, the operation raises at `R` and does not complete.
>
> **R1-C4.** If `R` does not fire, control is not diverted anywhere else — clause (1) forbids an
> earlier return, clause (2) a swallowing handler or context manager, clause (3) a break or continue —
> so control reaches `G`, whose predicate is `T`, so `G` fires and the operation raises.
>
> **R1-C5.** `WILL_FAIL` is a claim about the **operation**, not the site: `join` propagates one
> `WILL_FAIL` finding to the whole report (`plr-sema/src/plr_sema/verdict.py:313-323`) and `compare`
> scores the operation's index, `verdict == "will_fail"` against `outcome == "ran_ok"`, never the
> identity of the raising statement (`plr-sema/eval/oracle_common.py:767-786`). Therefore, by R1-C3 and
> R1-C4, the published claim is true in both branches and no hypothesis about `R` is taken.

**The three attacks a round should try first, named by this document rather than left to be found.**
**(1)** R1-C4's "not diverted anywhere else" is a claim about `K`'s **statements**, but a called
function can raise, be caught by a handler *outside* `K`, and return control nowhere — which does not
falsify R1-C5 (the operation still fails) but does mean the enumeration in R1-C2 is not exhaustive as
worded. **(2)** `compute_reachability_clear`'s clause (3) is conservative but its clause (1) is a
whole-body `lineno` scan that does **not** check whether the return is on a path that can precede the
guard, so it can only block, never permit — the safe direction, but it means R1-C1's antecedent is
narrower than the argument needs and the argument is therefore not tight. **(3)** `enclosed_by_try_or_with`
tests `K`'s own ancestors; a `try` in a **caller** does not appear, which is sound for R1-C5's
operation-level claim and would not be for a site-level one.

> **The interaction with this increment, stated because it is the question the round will ask.**
> **D1's depth-1 lift does not weaken R1 and does not rest on it.** R1 governs the **empty-trail**
> clause (5), which is consulted only for `depth == 0` guards; D1 adds an independent depth-1 path
> whose preconditions include `reachability_clear` for the delegate **and** the caller-side pair, so a
> depth-1 guard passes through clause (5)'s logic **twice**, once per body, and each pass is
> conservative. **The one place they touch** is that a depth-1 guard whose delegate body has an
> empty trail now reaches clause (5) at all, where before `E-UNCOND(4)` cut it off earlier — so R1's
> soundness argument is load-bearing for a population it has never been measured on. **AC-16.4's five
> perturbation fixtures are what pin that**, and p1's three mutators being re-measured **unchanged**
> at 288/288, 16/16 and 0/288 (AC-16.10) is what shows the depth-0 population did not move.

### The user decision hooks, together, each with this document's recommendation

| id | the decision | what it costs | what declining costs | recommendation |
|---|---|---|---|---|
| **D1** | Lift `E-UNCOND(4)`'s `depth >= 1` `WILL_FAIL` forbiddance at depth 1 only, under §16.4's three preconditions | one clause in the false-positive direction, on a population increment 6 round 1 filed six blockers about | this increment adds **no** `WILL_FAIL` population; `:409` and `:321` are exercised in the `SAFE` direction only; p2a is withdrawn | **YES** — a new decision procedure tested in one direction is a new decision procedure half tested, and both the tier-1 fence on 544 operations and p2a check it |
| **D2** | Admit **A-DECK-OBJECT** as a fifth named assumption, plus the `deck_resource_names` observation, so `:321` decides | the analyzer's assumption set grows from four to five for the first time since increment 1 | `pick_up_tips`'s residual falls to **three** sites instead of two; `n_findings_decided` gains 607 instead of 895; the third-largest cluster in the ledger stays | **YES** — it is strictly narrower than A-SINGLE, partly self-discharging under A-COMPLETES exactly as A-ENABLED is, and fence-checked on 288 real operations; and `:321` can only ever produce `SAFE` (§16.11), so the fence is the whole of its exposure |
| **D3** | *(a NON-decision, recorded so the round can attack it)* §16.3's derived backend surface introduces **no** hand-typed PLR fact and therefore needs no row | nothing | — | **No decision is asked.** If a reviewer names one literal PLR fact §16.3 hand-types, the claim is false and the section owes a row against a full `BUDGET_CAP`, which **is** a cap conversation. The three candidates to check are named in §16.3's own box |
| **D4** | HM-25 `declared` **9 → 10**, for §16.5's four-shape `EnvRef` path table | one per-row ceiling unit; `live_rows()` and `BUDGET_CAP` both unchanged at 24; no cap conversation | §16.5 cannot ship, and with it `:409`, `:514` and `:321`; the increment reduces to plumbing | **YES** — it is genuinely hand-maintained surface and this document says so first rather than being told; HM-25 is the loud-failure row and §16.10's per-rule counters are the loud test; and increment 6 spent 8 → 9 on exactly this row for exactly this reason |
| **D5** | Model `_check_args` in **this** increment, landing the headline | ~350 LOC, five new productions each with its own soundness argument, and a further HM-25 ceiling spend, on top of the seven rows already budgeted; the first joined `SAFE` would rest on the largest single pile of new machinery in the analyzer's history, in the `SAFE` direction | the headline slips a second time, to increment 8 | **NO** — but the branch is priced, and if the user wants the headline this sprint, T49 is written and the gate prediction is stated both ways. What makes NO the recommendation is that increment 8 would land the same model with §16.2–§16.7's apparatus already in place and the fence already site-keyed to catch it |

---

## 16.16 Implementation record

*(Column shape mirrors increment 5 §14.17 and increment 6 §15.15. No row is started; the whole table is
prospective. First-column ids are deliberately unbolded so the cross-reference lint's task-row pattern
does not read this table's cells as gate cells.)*

| row | commit | what landed | measured vs the spec's expectation | divergences |
|---|---|---|---|---|
| T40 | — | — | — | — |
| T41 | — | — | — | — |
| T42 | — | — | — | — |
| T43 | — | — | — | — |
| T44 | — | — | — | — |
| T45 | — | — | — | — |
| T46 | — | — | — | — |
| T47 | — | — | — | — |
| T48 | — | — | — | — |
| T49 | — | — | — | — |

---

## References

- Main specification (amended): `.praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md` — §3.2's join
  table (`:574-581`), the deferred rows (`:2514-2524`, with (c) at `:2518`, (e) at `:2520` and (f) at
  `:2524`), the boundary summary (`:2526-2534`), and Open decisions 3's additive direction
  (`:3316-3345`).
- Increment 1: `.praxia/docs/specs/260902_plr-sema-tip-typestate-increment.md` — §10.6.3's named
  assumption table (`:744-754`), which A-DECK-OBJECT would extend from four rows to five, and
  A-COMPLETES (`:752`), which §16.6 names as the claim `scope_verdict` does **not** make.
- Increment 3: `.praxia/docs/specs/260903_plr-sema-real-programs-increment.md` — §12.3.6 B2, the
  `pred`-aware `BRANCH`, still deferred.
- Increment 4: `.praxia/docs/specs/260903_plr-sema-families-cache-increment.md` — §13.1 (the lid
  disposition, unchanged), §13.12 (the general dataflow pass §16.3's `constant_return` shape test and
  §16.4's map both decline).
- Increment 5: `.praxia/docs/specs/260903_plr-sema-volume-increment.md` — §14.6 in full
  (`:602-741`), the precedent every legitimacy argument in §16.2 is stated against: the
  conditional-guard rule (`:619-636`), R1 (`:638-673`), the two failed `is_disabled` discharges
  (`:675-689`), the `env` argument (`:691-698`), and O5's observed-inside-the-window,
  returned-by-the-executed-side rule (`:700-723`).
- Increment 6: `.praxia/docs/specs/260904_plr-sema-predicate-increment.md` — §15.1's tiers, §15.2's
  grammar and G7/G8, §15.3's α/β, §15.4's `E-CALL`/`E-TYPE`/`E-SCOPE`/`E-UNCOND`/`E-ENV`, §15.5's Q1
  and the unmodified fence, §15.6's Q2 defer, §15.7's ordered reason procedure, §15.8's registry
  arithmetic, §15.9's gate and anti-gaming box, §15.12's sizing of the delegate map, §15.13's five
  refused productions with their reopening conditions, and §15.16.3 R1, whose review is owed and is
  restated in §16.15 Q6.
- The instrument: `outputs/plr-sema/unknown_ledger_260909_after.json`, with
  `outputs/plr-sema/oracle_replay_260909_inc6.json`,
  `outputs/plr-sema/predicate_mutants_260909_inc6.json` and
  `outputs/plr-sema/t30_measured_260908.json` as companions.
