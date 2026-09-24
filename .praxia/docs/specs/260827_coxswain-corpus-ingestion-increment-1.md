---
title: "Coxswain corpus ingestion — Increment 1 (facts-only admission ledger + drift audit + gap gate)"
description: "Implementable spec for the FIRST of four sequenced increments of LEDGERED THREE-AXIS INGESTION: training/ingest/ with sources.py (21-row committed SourceRegistry), licenses.py (mechanical SPDX->tier verification), recipes.py (recipes.yml parser), eval_split.py (committed holdout index + leak gate), audit.py (BLOCKING canonical-table drift detector), gap.py (PRE-REGISTERED coverage-gap gate). Facts-only, tier-0, fully offline, teacher-independent."
status: draft
spec_version: 8
task_id: 260827_corpus_ingestion_spec
date: '260827'
confidence: high
sources: ".praxia/docs/specs/260827_coxswain-corpus-ingestion-strategy-turni.md (contemplex 5b59d8e9); .praxia/docs/research/260827_real-world-pylabrobot-dependent-repos-as-corpus-derivation-candidates.md; audit 260827_corpus_ingestion_spec_challenge_round1 (spec-challenger, verdict not_ready); audit 260827_corpus_ingestion_spec_challenge_round2 (spec-challenger, verdict not_ready); audit 260827_corpus_ingestion_spec_challenge_round3 (spec-challenger, verdict not_ready); audit 260827_corpus_ingestion_spec_challenge_round4 (spec-challenger, verdict not_ready); audit 260827_corpus_ingestion_spec_challenge_round5 (spec-challenger, verdict has_gaps); audit 260827_corpus_ingestion_spec_challenge_round6 (spec-challenger, verdict has_gaps); audit 260827_corpus_ingestion_spec_challenge_round7 (spec-challenger, verdict has_gaps — TERMINAL round, no round 8 planned)"
---

# Specification: Coxswain corpus ingestion, Increment 1

> **Revision 8 — the terminal revision. The adversarial loop closes here.** Supersedes revision 7
> in place. Seven adversarial rounds are recorded, and their blocking-finding counts are the whole
> argument for stopping: **13 → 4 → 3 → 3 → 1 → 1 → 1**, with rounds 4–7 reopening *nothing* and
> round 7 finding **no design defect of any kind** — its single blocking finding is a missing test
> for a mechanism it independently re-derived as correct. Round 7 recommended applying its fixes as
> revision 8 and terminating the loop without a round 8; this revision does that. §0.9 is round 7's
> record. Six adversarial rounds preceded it:
> round 1 (`260827_corpus_ingestion_spec_challenge_round1`, **not_ready**, 13 blocking + 15
> warning) produced revision 2; round 2
> (`260827_corpus_ingestion_spec_challenge_round2`, **not_ready**, 4 blocking + 15 warning)
> re-verified revision 2's fixes against live repo state — 11 of 13 survived contact — and
> produced revision 3; round 3
> (`260827_corpus_ingestion_spec_challenge_round3`, **not_ready**, 3 blocking + 9 warning)
> re-derived revision 3's four blocking dispositions from the files rather than taking them on
> trust — R2-B1's nine-finding census, R2-B3's classifier and R2-B4d's shallow-clone ordering all
> reproduced exactly — and produced revision 4; round 4
> (`260827_corpus_ingestion_spec_challenge_round4`, **not_ready**, 3 blocking + 10 warning)
> verified **all three** of round 3's dispositions against live data — the nine-finding census
> reproduced a *third* time, and no prior disposition needed reopening — and produced revision 5;
> round 5 (`260827_corpus_ingestion_spec_challenge_round5`, **has_gaps**, **1 blocking** + 4
> warning + 4 suggestion) verified **all three** of round 4's dispositions against live data — a
> *fourth* consecutive round with zero reopenings — and found a single new blocking defect, which
> produced revision 6; round 6
> (`260827_corpus_ingestion_spec_challenge_round6`, **has_gaps**, **1 blocking** + 2 warning + 1
> suggestion) verified round 5's disposition and explicitly confirmed **nothing was reopened from
> any prior round** — a *fifth* consecutive clean round — and found one blocking defect of a single
> shape: revision 6's exception-hierarchy fix had landed in §7.1 and **nowhere else**. That produced
> revision 7. §0 records every disposition from all seven rounds; **§0.1–§0.3 are round
> 1's record, §0.4 is round 2's, §0.5 is round 3's, §0.6 is round 4's, §0.7 is round 5's, §0.8 is
> round 6's — all preserved verbatim as history — and §0.9 is round 7's.** Nothing else in this
> document should be read without §0: several sections changed *because* a mechanism did not
> survive contact with the live data structures, and the reasoning for the replacement lives in
> §0, not in the prose.
>
> **Round 2's standing lesson, stated once here because it recurs in five findings:** every
> number, table and set in this spec that describes the *live* cookbook or the *live* canonical
> tables must be derived by a command, not hand-listed. Revision 2 hand-listed a receiver table
> (W10), a blocking-finding count (R2-B1), an exclusion-table size (W8), a lineage key set (W3)
> and a `unmatched_cell_keys` expectation (W9) — four of the five were wrong against the file
> they described. Where revision 3 must state such a set, it either derives it in-line from
> evidence quoted at the point of use, or names the `--emit-*` command that produces it.
>
> **Round 3's standing lesson, and it is a different one:** a mechanism that is *derived* can
> still be **inert** — correct about the file and incapable of detecting the thing it was built to
> detect. All three of round 3's blocking findings have that shape: a per-subject fingerprint that
> varies correctly by subject but cannot change under any edit it must survive (R3-B1); a census
> pin with no home a gate can read (R3-B2); a "computed" file whose emitter cannot compute the
> only part of it that matters (R3-B3). Revision 4's rule, added to revision 3's: for every
> mechanism, **name the event it detects and the observation that would fire** — and if no such
> observation exists, say so and hand the job to a mechanism that has one, rather than restating
> the property in stronger words.
>
> **Round 4's standing lesson, and it is the cheapest one yet: a correct mechanism is not a
> runnable one.** Round 4 reopened nothing. Every semantic disposition from rounds 1–3 held against
> the live files. What it found instead were three **plumbing** defects, each of which would have
> stopped a fixer dead on day one while the design above it was sound: an unconditional reader
> invariant that made four of this spec's own test fixtures unimplementable (R4-B1); an
> entry-point shape stated one way in §7.1 and invoked another way by every AC, gate row and task
> (R4-B2); and a hash whose input was interpreter-version-dependent, feeding a helper the spec
> never defined (R4-B3). Revision 5's rule, added to the three above: **every command line, file
> path, function signature and hash input in this document is a promise a fixer will execute
> literally.** If two places spell the same thing differently, one of them is wrong — and the one
> that appears once (§7.1's layout note) loses to the one that appears fifteen times (the ACs), not
> the other way round. Design review catches inert mechanisms; only *transcription* review catches
> these, so read the command lines as carefully as the arguments.
>
> **Round 5's standing lesson, and it is the sharpest form of round 3's: a fix is not a detector.**
> Round 5 reopened nothing — a fourth consecutive round confirming the census, the receiver map and
> the digest architecture against live data. Its single blocking finding is that revision 5
> *corrected* the entry-point shape (R4-B2) and then installed **nothing that observes it**: the
> five hand-copied `if __name__ == "__main__":` guards became the one link in the chain that no
> specified test crosses, so R4-B2's own failure mode — `audit --gate` exiting 0 having checked
> nothing — survived its own fix as an unobserved possibility. Revision 6's rule, added to the four
> above: **when a fix takes the form "the spec now says X", ask which test goes red if the
> implementation says not-X.** If the answer is "none", the fix is a paragraph, not a mechanism.
> The three related warnings are the same shape one level down — a second unchecked home for a
> committed count (R5-W1), an exit code the spec never accounted for arriving from `argparse`'s own
> defaults (R5-W2), and a probe whose stated conclusion is stronger than the input it tests
> (R5-W3) — and R5-W4 is its limit case: a regression test for a bug that **cannot be observed
> behaviourally on the interpreters most people run**, which is why revision 6 replaces it with a
> structural remedy rather than a better test (§5.2).
>
> **Round 6's standing lesson, and it is about how a fixer reads, not about what the spec argues:
> a fix belongs at every declaration site, not only in the section that argues for it.** Round 6
> reopened nothing — a fifth consecutive clean round. Its single blocking finding is that revision
> 6 diagnosed a circular import in `cli.py`, designed the exception hierarchy that removes it, and
> wrote that design into **§7.1 only** — while §2.1, §3.1, §5.7, §6.1, Task 1 and Task 3 kept the
> pre-fix spelling, including a `CookbookUnavailable` **defined in `recipes.py`** in flat
> contradiction of §7.1's `cli.py`. A fixer works through this document **module by module**: they
> open §3.1 to write `recipes.py` and never see §7.1's argument. So the corrected design was, at
> the six places it had to be obeyed, still the defect. Revision 7's rule, added to the five above:
> **after fixing a cross-cutting fact, grep the document for every name the fix touches and check
> each hit, before claiming the fix landed.** A design stated once and contradicted five times is
> the same failure mode as R4-B2's entry-point shape — one authority, many transcriptions — and it
> is now the *second* time it has cost a round. §0.8's C1 row records the grep as part of the fix,
> not as a review step, for that reason.
>
> **Round 7's standing lesson, and it is round 5's rule applied to the one place the spec had
> exempted itself: a *deliberate exception* needs a detector more than a rule does.** Round 7
> reopened nothing — a sixth consecutive clean round — and found **no design defect**. Its single
> blocking finding is that revision 7's most carefully-argued decision, keeping `EvalSplitLeak`
> *outside* `cli.IngestError` so `--check-leak` can return **6**, was verified only *statically*
> (`not issubclass(...)`) while the runtime contract it depends on — the handler's `try/except` —
> existed nowhere as code and was tested nowhere at all. Every `--check-leak` invocation in the
> document used the clean sidecar and expected 0, so an implementation with no `try/except` would
> have leaked an uncaught traceback as exit **1** with the entire suite green, and G5 would report
> "measurement error" on a real eval-split leak. Revision 8's rule, added to the six above: **when
> the spec argues that some class or code path is a deliberate exception to a package-wide rule,
> the exception's own runtime behaviour is the thing that must be driven end-to-end** — the rule it
> is excepted from already has detectors; the exception has only the paragraph that argued for it.
> Round 7's three warnings are the same shape one level down (a table row that omits a required
> argument, a normative rule stated as a glob that one of its six instances does not match, and a
> "row-for-row" claim about a table row that expands to six cases), and revision 8 is a **closing**
> revision: it adds one test, one normative code block, one `out_required_for` tuple, three
> module-level names the blocks it added could not be written without, and four transcription
> corrections. Nothing below re-decides anything, and no round 8 is planned.

---

## 0. Revision log (rev 1 → rev 2)

**Numbering note.** The audit record's finding array and the dispatch brief disagree on the
identifiers of four tail findings (the brief's C21/C25 are the record's C24/C28; the brief cites a
C17/C26/C27 whose text is not present in the retrieved record). Rows below are keyed by
**substance** and carry every identifier under which the finding was cited. Three findings
(C26, C27, and the brief's C17 beyond what could be reconstructed) had no retrievable text; see
§0.3.

### 0.1 Blocking findings — dispositions

| # | Substance | Disposition | Fix |
|---|---|---|---|
| **C1** | `PARAM_NAMESPACE` is `dict[str, tuple[ParamSpec, ...]]`; rev 1's `value_form` indexed it as `[verb][pname]`, and `mix`/`blow_out`/`touch_tip` are in the sidecar's `distinct_verbs` | **ACCEPTED in full** | §6.2 rewritten. A module-level `_PARAM_INDEX: dict[(verb, name), ParamSpec]` flattens the tuple; lookup is `.get()` with an explicit miss branch; keying is on `ParamSpec.**name**` (proven by the sidecar's own params — see §6.2's evidence note), never `plr_arg`; verbs outside `PARAM_NAMESPACE` are handled by the miss branch and **counted** in `unmapped_params` (F5). No `params_of()` call anywhere in `gap.py`. |
| **C2** | AC-1.8's "no write whose path can resolve outside `OUT_DIR`" is mutually unsatisfiable with `write_report(out_dir)` + AC-1.10's temp dirs, and "provably rooted" is not AST-decidable | **ACCEPTED; rev 1's mechanism replaced, not narrowed** | §5.6. Three-part replacement: (a) `ingest/io.py::write_artifact()` is the package's **only** writer, and it *raises* at runtime when the resolved target falls inside any protected root; (b) the AST scan's property changes to a decidable one — "no write primitive appears in any ingest module except `io.py`"; (c) a byte-level canary hashes the four canonical artifacts before/after a full pipeline run into a temp dir. Temp dirs are legal, canonical tables are unwritable, and the scan now proves something. |
| **C3** | `finding_id` hashes identity only, so an adjudication survives a material verdict flip — PM-3 reconstructed inside PM-3's own fix | **ACCEPTED; treated as the review's most severe finding** | §5.2/§5.5. `finding_id` keeps its identity-only hash (the anti-churn property is real and worth keeping). A **second** hash, `adjudicable_digest`, covers the decision-determining projection: verdict, blocking, the sorted set of *distinct* evidence classes, and a **per-subject** canonical-table fingerprint. The adjudication entry must carry `adjudicated_digest`; the gate passes only on equality. A flip from `NO_EVIDENCE` to `CONTESTED` changes the digest and blocks; an unrelated recipe addition does not. |
| **C4** | "exactly four phantoms" has no machine-readable derivation — 7 entries carry `experimental=True` and the phantom/no-backend distinction lives only in a Python comment | **ACCEPTED** | §5.3. `data/experimental_partition.json` commits the 4/3 split with a per-verb reason, and its loader **asserts** `phantom ∪ no_backend == {n for n, s in TOOL_SCHEMA.items() if s.experimental}` with the two sets disjoint. An 8th experimental entry appearing upstream fails the load loudly instead of silently changing "exactly four." A new advisory `no_backend_verb` finding kind emits one row per no-backend verb so the other three are counted, not dropped (F5). |
| **C5** | `recipes.yml` paths are bare scalars containing `#`; a `#`-stripping reader silently truncates anchors. The file also has a 12-line comment header and blank lines rev 1 never mentioned. The PyYAML alternative violates F3 | **ACCEPTED; the PyYAML branch removed as illegal, not deferred** | §3.1. Exact grammar pinned (comment ⟺ first non-space char is `#`; inline `#` is never a comment); every line is accounted for as record/blank/comment and the totals must reconcile; **every parsed `path` is validated against `^[a-z0-9_/]+\.qmd#[a-z0-9-]+$`**, so a truncated anchor is a hard error rather than silent corruption. The "fixer picks PyYAML or a reader" choice is deleted: PyYAML is a third-party import and F3 forbids it — rev 1 offered an option the constraints already excluded. |
| **C6** | D1 cannot distinguish "licenses are genuinely bad" from "clones are not on this machine": `NOT_CLONED`, `SHA_MISMATCH`, `NONE`, `AMBIGUOUS` all collapse to tier 0 | **ACCEPTED** | §2.4/§2.6. A **measurement-validity axis** is separated from the license axis. `unresolvable_count` counts rows whose license is *unknown* (`NOT_CLONED`/`SHA_MISMATCH`). D1 becomes three-way: exit **0** (proceed), exit **3** (STOP — a real licensing verdict, only when the missing measurements *cannot* change the outcome), exit **5** (INCONCLUSIVE — provision the clones and re-run; **not** a descend signal). |
| **C7** | `license_rules.json` decides D1 — the higher-consequence, first-running gate — with none of `GAP_THRESHOLDS`' pre-registration armour | **ACCEPTED** | §2.5. `LICENSE_RULES_VERSION` + `LICENSE_RULES_SHA256` pinned in `versions.py`; the loader raises when the file's hash disagrees; both are recorded in `license_report.json`; verdict→tier mapping moves **into code** so data can never grant a tier; rule additions require `added_in_version` + `justification` and surface in the report's `rules_added_since_v1`. Same visible-git-diff property `GAP_THRESHOLDS` has, applied to the gate that runs first. |
| **C8** | T3's "apis names no `PHASE2_TOOL_NAMES` member" does not say whether `lh.drop_tips` counts; raw-token matching would misread anchors like `#drop-return-discard` | **ACCEPTED** (record marks blocking; brief lists as warning — treated as blocking) | §6.4. Matching is defined exactly: over `ApiToken.member` of **method-shaped tokens only**, exact case-sensitive string equality against `PHASE2_TOOL_NAMES`; never substring; never over `path` or `title`. `lh.drop_tips` → member `drop_tips` → in-surface. Two worked examples pinned as unit tests. |
| **C9** | `*Backend where the module is a liquid-handler backend` is undecidable from `recipes.yml`; `ThermocyclerChatterboxBackend`/`IncubatorChatterboxBackend` are live counterexamples | **ACCEPTED** | §3.3. Wildcards deleted. `receiver_aliases.json` becomes an **exact** table with `default: "other"`; unmapped receivers emit an advisory `unmapped_receiver` finding (F5); Task 3's gate requires **zero** unmapped receivers across the current 91 recipes, so the table is complete today. Safety argument recorded: because unmapped → `other` and both blocking receiver kinds require `liquid_handler`/`plate_reader`, an unmapped receiver can only under-report, never fabricate, a blocking finding. |
| **C10** | "committed list equals the rule recomputed" makes recomputation authoritative, inverting PM-4; no monotonicity rule, so a path can un-leak backward into training | **ACCEPTED in full** | §4.4. The committed list is authoritative, full stop. The recompute check is demoted to a subordinate consistency check whose failure message forbids regeneration, and is relaxed to `committed ⊇ recomputed` (widening the holdout is always safe; every extra path carries a reason). **Monotonicity** is added as a hard invariant via an append-only `held_out_ever` set: `held_out_ever ∩ current_paths ⊆ held_out_paths`. A path that has ever been held out and still exists can never return to training. |
| **C11** | `assert_no_leak` has no caller, no test, and no AC — an unenforced MUST, the same unowned-obligation shape PM-3 describes | **ACCEPTED** | §4.5 + AC-1.13 + gate **G5**. The leak check becomes a real gate that **runs today** (`python -m ingest.eval_split --check-leak <sidecar>`) over the committed 188-row sidecar, wired into §9's gate table and Task 8's suite. It is green now because no row is recipe-derived; it turns red the moment Increment 3 lands a leaked row, with nobody having to remember to add it. It is **fail-closed**: a row claiming cookbook lineage without a `recipe_path` is a leak by definition. It keys on `held_out_ever`, which is what makes the monotonicity invariant load-bearing rather than decorative. |
| **C12** | T1's threshold was chosen after computing its value (5) and, since Increment 1 adds no naturalness rows, cannot fail. Disclosure is not pre-registration | **ACCEPTED; rev 1's T1 gate removed** | §6.4/§6.5. T1 is **demoted from a gate to a pinned invariant**: the report must reproduce exactly 5 zero-naturalness LH verbs and exactly the pinned five names, else exit 1 (measurement error — the implementation or the corpus disagrees with the hand-derivation). The PROCEED decision now rests on **T2 ∧ T3 only**, the two thresholds whose values were genuinely not computed at authoring time. Rationale and the rejected alternative are in §6.5. |
| **C13** | No rollback for the audit's *success* case: `action=edit_table_by_hand` invalidates the 188-row corpus, the 43-cell matrix and the golden fixtures, with no regeneration or retraction path stated | **ACCEPTED** | §5.7 + AC-1.14. A committed `data/canonical_tables_fingerprint.json` pins the fingerprint the current committed corpus artifacts were built under; `test_ingest_downstream_fingerprint.py` goes **red** the instant a canonical table changes, and its failure message is the regeneration checklist (four named artifacts, in order). Adjudications with `action: edit_table_by_hand` must carry an `impact` block (`tables_touched`, `invalidated_artifacts`, `regeneration_backlog_ref`), all required and validated by the gate. |

### 0.2 Warning findings — dispositions

| # | Substance | Disposition | Where |
|---|---|---|---|
| **C14** | `gap.py` → `assemble.build.CLASS_MAP` transitively imports `subprocess`; AC-1.11 scans only `training/ingest/` so the purity gate passes while F3's property is false | **ACCEPTED, fixed differently than the obvious way** | §7.3. The obvious fix — extract `CLASS_MAP` to a dependency-free `assemble/classes.py` — **does not work**: `assemble/__init__.py` re-imports `.build`, so any `assemble.*` import still pulls `subprocess` in. Recorded so the next reviewer does not re-propose it. Instead: (a) the scan goes **transitive**; (b) the one leaky edge is allowlisted in `data/import_closure_allowlist.json` with its reason (`assemble.build` imports `subprocess` for `plr_source_sha()`, never called from ingest); (c) a **runtime** proof — the full pipeline runs with `subprocess.run` patched to raise — which is strictly stronger than any AST scan. |
| **C15** | `training/conftest.py` is a docstring only; `python -m ingest.*` (used by 6 of 12 ACs) fails from the repo root until a reinstall adds `ingest*` | **ACCEPTED** | New **AC-1.0** + Task 1. The reinstall is an explicit, gated step, and every `python -m ingest.*` command in this spec is declared to presume it. |
| **C16** | `tier_ceiling: 0` on the H6 rows is applied inside `effective_tier`, which D1 counts — so "pure license axis, admission ignored" is self-contradictory; `cheshire-drivers`' ceiling is never stated, inviting double-counting of the AGPL cap | **ACCEPTED** | §2.4/§2.6. The self-contradictory phrase is deleted; D1's semantics are restated correctly (license verdict **and** non-license ceiling both apply, because a contamination-capped row cannot carry material regardless of licence; *admission* is what is ignored, and only because no row can be admitted before Increment 2). Both counts are reported. `cheshire-drivers` gets an explicit `tier_ceiling: 2`, and invariant I6 now requires `tier_ceiling_reason` to begin with a non-license prefix, making a license reason in the ceiling field a load error. |
| **C17** (brief) | `extractor_kind`/`admission_argument` coupling seam with Increment 2 | **ACCEPTED as reconstructed** (finding text unavailable; see §0.3) | §2.1/§2.5. Rev 1's invariant I5 (`extractor_kind is NONE` **iff** `admission_argument is None`) forced all 20 pending rows to erase extractability information the research doc already has, and made Increment 2 rewrite two coupled fields. Decoupled: `extractor_kind` is an observed property, admission is a decision, and a new closed `admission_state` enum (`ADMITTED`/`PENDING_RECON`/`REJECTED_PERMANENT`) replaces the null/empty-string overload. §2.7 states exactly which fields Increment 2 may change. |
| **C18/C19** | 168 of 188 rows have no `lineage.cell_id`, so the fallback attributes almost everything; rows can land on cell_ids outside the 43-cell matrix with no defined handling (F5); the generic out-of-surface cell is `verb: null` in the matrix but `verb: ""` in the corpus | **ACCEPTED** | §6.1. The fallback is now explicitly the *dominant* path (with the 20/168 split stated); off-matrix cell keys are collected into `unmatched_cell_keys` and **counted**, never dropped; the `None`/`""` mismatch is handled by an explicit normalization step with both forms named. |
| **C20** | `floor_gen` writes `10.0`, `overlay_gen` writes `20` — the type-name fallback makes *provenance* a shape, so T1 and T2 are near-collinear | **ACCEPTED, with an integrity counter-measure** | §6.2/§6.4. `bool` → `"bool"`; every other `int`/`float` → `"number"`. Because collapsing numbers makes T2 *easier* to pass (a self-serving direction), the report emits **both** `T2_collapsed` and `T2_strict`, and the decision rule takes the **STOP-side answer whenever they disagree**. Directional disclosure in §6.5. |
| **C21/C24** | Root-only LICENSE scan; the cookbook's real project root is `cookbook/` (README, SPEC, .gitignore all live there), so a maintainer's `cookbook/LICENSE` would report `NONE` forever | **ACCEPTED** | §2.5. Per-row `license_scan_dirs` (default `[]`; cookbook `["cookbook"]`); a license found in two scanned dirs with differing hashes ⇒ `AMBIGUOUS`; `license_path` in the report names which directory won. Task 9's issue text asks for the file at the repo root. |
| **C22** | AC-1.4 is unfalsifiable for any total classifier | **ACCEPTED** | §3.2/AC-1.4. Replaced by two falsifiable properties: (a) the five predicates are evaluated **independently** and the implementation raises unless exactly one is true (an overlapping-predicate bug fails; totality-by-fallthrough no longer satisfies the AC); (b) a committed per-kind histogram pins the current classification so a silent reclassification of 40 tokens fails the suite. The histogram is labelled a **regression pin, not a pre-registered threshold**. |
| **C23** | AC-1.12's `due ≤ 2026-09-10` never goes red after the date passes, so LICENSE-4 stays unenforced; Task 9's URL-required gate contradicts AC-1.12's either/or | **ACCEPTED** | §2.8/AC-1.12. The date becomes a live deadline: with no issue URL, the test requires `license_request_due >= today` and goes **red** on 2026-09-11. Slipping it requires an append-only `license_request_due_extensions` entry (≤30 days, with a reason) — visible, not silent. Task 9 satisfies the URL branch; the either/or is preserved. |
| **C25/C28** | Task 0's `ls ~/projects/repos \| wc -l >= 21` passes at 20 of 21 cloned, because `~/projects/repos/pylabrobot` already exists and is explicitly *not* a registry row | **ACCEPTED** | Task 0 gate replaced by `python -m ingest.licenses --verify-clones`, which is per-row and exact (each of the 21 `clone_path`s has a `.git`, and its resolved HEAD equals `pinned_sha`), printing every miss. No directory counting anywhere. |

### 0.3 Findings not addressed, and why

- **C26, C27, and any part of the brief's C17 beyond the coupling seam.** These identifiers appear
  in the dispatch brief and/or the audit summary's counts but **their text is not present in the
  retrieved audit record** (`transduction_query(scope="task", …, phase="audit", expand=true)`
  returned 21 finding objects covering C1–C16, C18–C20, C22–C24 and C28 by substance). Revising
  against a paraphrase would be worse than declaring the gap. The brief characterises C26 as an
  Increment 1/2 boundary concern; §2.7 now states the boundary explicitly as a field-level
  change table, which is the best available generic answer. **A second adversarial round should
  re-raise C26/C27 verbatim.**
- **Deliberate non-fixes** are in §12, not here.

### 0.4 Round 2 dispositions (rev 2 → rev 3)

Round 2 (`260827_corpus_ingestion_spec_challenge_round2`, verdict **not_ready**) re-verified
revision 2's thirteen fixes against live repo state. It confirmed eleven line-by-line (C1's
`_PARAM_INDEX` keying, C4's 4/3 partition against the live seven `experimental=True` entries,
C5's 12 + 364 + 91 = 467-line reconciliation and the `path` regex over all 91 values, C8's pinned
T3 cases, C10's absence of a bootstrap problem, C12's T1 hand-derivation, C14's transitive
closure, C15's still-missing `ingest*`, C21/C24 and C25/C28 against the live clone layout) and
found four blocking defects plus fifteen warnings.

**Reading §0.1–§0.3 alongside this section.** Those tables record round 1's dispositions **as they
were made**, and they are preserved verbatim — including the parts round 2 overturned. Where a
round-1 row and a round-2 row describe the same mechanism, **the round-2 row is authoritative**.
The overlaps, so nobody has to reconstruct them: C20 → **W2** (the STOP-side rule is withdrawn);
C2's "decidable AST property" → **W7** (relabelled a lint); C3's `subject_table_fingerprint` →
**R2-B2** (defined); C4's census discipline → **R2-B1** (applied to the blocking set, where
revision 2 did not apply it); C22 → **R2-B3** (the assertion made reachable); C25/C28 → **R2-B4c**
(exit split); C9's alias table → **W10** (rebuilt); C11's G5 → **W3** (given something to check);
C13's fingerprint → **W1** (bound to artifacts).

#### Blocking — dispositions

| # | Substance | Disposition | Fix |
|---|---|---|---|
| **R2-B1** | The blocking-finding census is wrong against live data. Five real `SURFACE_ADJACENT` findings exist (`lh.use_channels`, `lh.use_tips`, `lh.head`, `lh.clear_head_state`, `lh.probe_tip_presence_via_pickup` — recipes.yml 152/212/232/392/467), none in `TOOL_SCHEMA`, none in `NON_SURFACE_VERB_REASONS`. Task 6 seeds only the 4 phantoms and asserts `--gate` exits 0, which AC-1.7 makes unsatisfiable; §5.2's "all seven blocking findings" is C4's unbacked-constant defect relocated into C3's fix | **ACCEPTED in full; `SURFACE_ADJACENT` stays blocking** | New **§5.4.1** derives the complete blocking census per kind from the live file, with the derivation shown so it is checkable: **4 `phantom_verb` + 5 `surface_adjacent` + 0 `receiver_drift` + 0 `param_misattributed` = 9**. Every subject is named with its evidence lines and its anticipated reading. Task 6 seeds **nine** adjudications; §5.4's bounded-blocking argument is re-derived with a *structural* bound (≤ 27, the distinct LH/PR-receiver member set) instead of an asserted "small"; AC-1.6 gains a `blocking_census` regression pin so the count can never again be a literal in prose. Making the five advisory was considered and rejected in §5.4.1 — they are the highest-signal output the audit can produce, and demoting them to dodge five hand-written adjudications is PM-2's waived-gate failure by another route. |
| **R2-B2** | `Finding.subject` is never defined for any kind, yet it feeds `finding_id`, `adjudicable_digest`, `subject_table_fingerprint()` and the keys of the hand-authored adjudications file. `subject_table_fingerprint` has no meaning when `subject` is not a `TOOL_SCHEMA` key — which per R2-B1 is the majority of the blocking set | **ACCEPTED in full** | **§5.2** gains an explicit **ten-row subject table** (one row per `FindingKind`, with the exact string and a worked example) and a closed `ReceiverType` enum that gives the dotted kinds a stable, alias-spelling-independent subject. **§5.7** redefines the fingerprint as `subject_table_fingerprint(kind, subject)` — the signature had to take `kind`, because nothing else can parse the subject — over three declared cases, and it hashes **the lookup result including misses**, not the found rows. That is what kills the "empty projection hashes to a constant" hazard: `liquid_handler.use_channels` hashes a record containing its own name and three explicit `False` memberships, so it is subject-distinct *and* it changes the moment any of the three tables gains the member. A `table_scope: "none"` case exists for the two subjects that genuinely depend on no table, and an assertion forbids any **blocking** kind from using it — so the constant-hash case is structurally unreachable where it would matter. |
| **R2-B3** | The exactly-one-predicate assertion is unreachable for every possible input, because `OTHER` is written as the exact complement of the other four. AC-1.4(1)'s falsifiability claim is false and Task 3's "synthetic ambiguous token" does not exist — C22 re-shaped, not fixed. `""` also classifies silently as `OTHER` | **ACCEPTED; the first of the two offered fixes, plus the second** | **§3.2** replaces `OTHER`'s complement with **four positive patterns** (`_MIXED_SNAKE`, `_UPPER_SNAKE`, `_DIGIT_LED`, `_PUNCT_TOKEN`), each disjoint from `IDENT`/`CLASSISH` by first-character or alphabet, with the disjointness argument written out. The classifier is now **partial**: `""` matches nothing and raises, which makes the zero-hit branch genuinely reachable — and it is exactly the branch a trailing comma in `apis` produces, so the sub-issue is fixed by the same change. **AC-1.4(1)** now states which branch is reachable how: zero-hit by a real token, multi-hit **only** by a defective predicate table, which Task 3 induces by monkeypatch rather than by a nonexistent token. The reclassification is behaviour-preserving over the current 91 recipes (worked through in §3.2). |
| **R2-B4** | AC-1.3's exit 5 (INCONCLUSIVE on missing clones) and the new G0b `--verify-clones` hard-fail contradict each other; and `load_recipes`' default path is never stated while AC-1.4/1.5/1.6/1.7/1.9/1.13 and Tasks 3–8 all read an out-of-repo, **shallow**, `main`-tracking clone, with `recipes_yml_sha256` pinning its mutable bytes | **ACCEPTED in full, all four parts** | (a) **§3.1** states `default_recipes_path()` — derived from the registry row's `clone_path`, so the out-of-repo path is stated in exactly one place and that place is already a committed, invariant-checked field. (b) New **§7.5** promotes exit **5 = INCONCLUSIVE** from a D1 special case to a **package-wide convention** and gives a per-command table of the absent-clone behaviour, gated by new **AC-1.16**; `audit --gate` in particular exits 5, never 0 — an unmeasurable audit must not pass. (c) **G0b splits** the two failures it conflated: absent clone → 5, present-but-wrong-SHA → 1, with a `--require-all` flag that turns 5 into 1 for Task 0, where provisioning *is* the deliverable. C25/C28's per-row exactness is untouched. (d) **§4.4** reorders its assertions so the **commit-SHA pin runs first** and the byte pin is explicitly subordinate; the two failures now carry different diagnoses ("the clone moved" vs "the working tree is dirty"), and §4.3/§6.4 restate what AC-1.10's determinism claim does and does not cover. |

#### Warnings — dispositions

| # | Substance | Disposition | Where |
|---|---|---|---|
| **W1** | `canonical_tables_fingerprint.json` hashes only the table, so AC-1.14's tripwire is silenced by editing one hex string | **ACCEPTED** | §5.7 + AC-1.14. The file now binds the sha256 of all **five** downstream artifacts alongside the fingerprint, and AC-1.14 asserts both halves. Silencing is still possible — nothing is unsilenceable — but it now requires writing a false claim about five named files in a reviewable diff, which is what C13 asked for. (Also corrects rev 2's "four-artifact checklist": it is four *stages*, five *files*, and a different four than §5.6(c)'s canonical *tables*.) |
| **W2** | `T2_collapsed ≥ T2_strict` always, so "take the STOP-side answer" makes `T2_strict` — the provenance-leaking reading C20 objected to — the effective gate authority | **ACCEPTED; the decision rule changed, not the framing alone** | §6.4/§6.5. The algebraic fact is stated (disagreement can only ever be `collapsed` passes / `strict` fails — i.e. **exactly** the self-serving direction). `T2_collapsed` becomes the sole gate authority; `T2_strict` is retained as a robustness probe; and disagreement is neither PROCEED nor STOP but a new exit **7 = CONTESTED**, requiring a spec revision with the disagreement on the table. Rev 2's false claim that collapsing "removes the leak" at the decision point is deleted. |
| **W3** | G5 keys on `lineage.source_id`/`recipe_path`, which do not exist in the live sidecar and are owned by Increment 3 — so G5 can stay green forever. §12.6 mislabels this a corpus limitation | **ACCEPTED; reframed and made partly enforceable now** | §4.5 + new `data/lineage_contract.json` + AC-1.17. The real defect is an **unenforced cross-increment field-name contract**, so Increment 1 enforces the half it can: G5 asserts every sidecar row's lineage key set is a subset of a committed vocabulary, and **any new lineage key fails the gate** until it is written down. That converts "Increment 3 might name it differently" from a hope into a red gate, and it makes G5 non-vacuous **today** (it now has a live assertion over all 188 rows). §12.6 is relabelled. Round 2's own key list was also incomplete — see the W3 note in §4.5. |
| **W4** | `Evidence` is declared `(recipe_path, token_raw, token_kind, receiver_type)` but `_adjudicable_view` reads `e.member_is_in_surface` (never declared) and `e.receiver_type` for non-DOTTED tokens (which have no receiver) | **ACCEPTED** | §5.2. `Evidence` is fully declared with eight fields including `member_is_in_surface`; `ReceiverType` is a closed enum whose `NONE` member is the receiver type of every non-DOTTED token, so the projection is computable for every evidence row. |
| **W5** | Phantom-evidence case policy unpinned: §5.3 counts CLASSISH `Mix` as evidence for `mix` while exact case-sensitivity is pinned only for T3 | **ACCEPTED** | §5.1 gains a **package-wide case policy** paragraph, and §5.3 replaces the unstated conflation with an explicit **two-stage evidence rule**: primary matches are exact and case-sensitive; CLASSISH casefold matches are *corroborating*, carry `match_mode: classish_casefold`, and can support `KWARG_ONLY` but never `CONTESTED`. `match_mode` joins the `evidence_classes` tuple, so the digest tracks it. |
| **W6** | `unmapped_params` is tuple-keyed but declared a JSON object (`json.dumps(sort_keys=True)` raises); `INVERSE_CLASS_MAP` is used but never defined | **ACCEPTED** | §6.2/§6.3 pin the serializer (`f"{verb}\|{pname}"`, both halves identifier-shaped so the separator cannot occur inside either) and §6.1 defines `INVERSE_CLASS_MAP` from the live `CLASS_MAP` with an injectivity assertion. |
| **W7** | §5.6(b)'s write-primitive ban list omits `os.makedirs`, `Path.unlink`, `tempfile.*`, and others | **ACCEPTED, with the over-claim withdrawn** | §5.6(b). The list is extended (twenty-odd primitives, `shutil.*` and `tempfile.*` wholesale), **and (b) is relabelled a lint whose completeness is not claimed**. Rev 2 called it "a syntactic fact with a crisp answer", which is true of each rule and false of the set. The proof is (c), the byte canary; (b) is the cheap early warning. `tempfile` is banned outright because temp dirs are supplied by the caller. |
| **W8** | `NON_SURFACE_VERB_REASONS` has 28 entries, not 29 | **ACCEPTED** | §5.1 and §11 corrected to **28**, with the count now also derived (`len()`) wherever code reads it. |
| **W9** | §6.1's "`unmatched_cell_keys` is expected to be non-empty" is false — all 188 rows map into the 43 cells | **ACCEPTED** | §6.1 states the correct expectation (**empty**) with the reason, and pins it as a **regression pin** in Task 7's suite — the same category as `token_histogram.json` and `T1_INVARIANT`, and explicitly not a threshold. §12.5 is rewritten around the distinction between "0 → non-0 is worth seeing" and "N > k justifies spending". |
| **W10** | `receiver_aliases.json`'s example names 10 receivers that never appear and omits ~25 that do; `backends/chatterbox.py` and `manifest.json`/`config.json` parse as DOTTED with method-shaped members | **ACCEPTED in full** | §3.3's table is **rebuilt against the real 91-recipe DOTTED receiver set** — 31 receivers, enumerated, of which exactly three map to `liquid_handler` and **none** to `plate_reader`. Task 3's gate is strengthened from one-directional to **two-way equality** (no unmapped receivers *and* no unused entries), so a hand-listed table can never again drift from the file it describes. The three method-shaped-but-not-methods (`…chatterbox.py` → member `py`, `manifest.json`/`config.json` → member `json`) are worked through as the safety-asymmetry example. |
| **W11** | Task 3 asserts `ThermocyclerChatterboxBackend` → CLASSISH *with `receiver_type` other*, but CLASSISH tokens have no receiver | **ACCEPTED** | Task 3's assertion is corrected to `receiver=None, receiver_type=NONE, method_shaped=False`, and a **separate** assertion (`Liddable.has_lid`) now carries C9's actual concern: a DOTTED token whose receiver is not a liquid handler produces no blocking finding even though its member is in neither table. |
| **W12** | `PROTECTED_ROOTS` calls `training/ingest/data/` "hand-authored, never generated" while four files in it are fixer-computed | **ACCEPTED** | New §5.6(d) splits the directory into **six hand-authored** and **four computed-then-committed** files, names the `--emit-*` subcommand that produces each computed one into a caller-supplied `--out`, and states that landing it in `data/` is a human `cp` in a reviewed commit. All four have a gate that re-derives them (AC-1.4, AC-1.5, AC-1.14, Task 3's two-way equality), so the manual step is verified, not trusted. `PROTECTED_ROOTS`' comment is corrected. |
| **W13** | I6's `other:` prefix lets a license reason be smuggled into `tier_ceiling_reason` — the double-count C16 closed | **ACCEPTED** | §2.2 I6. `other:` is deleted; the prefix set is closed (`contamination:`/`vendored:`/`consent:`/`stale:`/`duplicate:`) and lives in `sources.py`, not in data. A **negative** clause is added: the reason may not contain `licen*` or word-boundary `mit`/`bsd`/`gpl`/`agpl`/`lgpl`/`apache`/`spdx`/`copyleft`/`proprietary`. |
| **W14** | §7.3's closure categories must be read to include `training/src/praxis_training/*`, reached via `assemble/build.py:35` | **ACCEPTED** | §7.3(b) states five explicit categories including `praxis_training.*` with its path and its entry edge, and enumerates the **observed** closure today. Round 2's verification that the allowlist's "exactly one entry" claim is true is recorded there. |
| **W15** | `shape_key(verb, call, stats)` never uses `verb` | **ACCEPTED; parameter dropped, not documented** | §6.2. The signature becomes `shape_key(call, stats)`. Keeping it "for compatibility" would preserve a parameter whose only possible wrong value (`row["verb"]`) is precisely the bug §6.2 warns about; removing it makes that bug unrepresentable. |

#### §12 re-examination

Round 2 confirmed items 1, 2, 4, 5, 7 and 8 as genuinely non-blocking; they are unchanged apart
from a note recording the confirmation. **Item 6 is relabelled** from a corpus limitation to an
unenforced cross-increment field-name contract (W3), with the residual risk stated precisely now
that `lineage_contract.json` closes the "renamed field slips past" half of it. **Item 3 now says
explicitly that it is what makes W3 possible** — Increment 1 cannot bind Increment 2's or
Increment 3's field names, and every finding of that shape traces back to it. Three items are
added (9, 10, 11) for limitations this revision introduces or newly exposes.

### 0.5 Round 3 dispositions (rev 3 → rev 4)

Round 3 (`260827_corpus_ingestion_spec_challenge_round3`, verdict **not_ready**) re-derived
revision 3's four blocking dispositions from the live files rather than taking them on trust.
**Three of the four reproduced exactly** and are recorded here as verified, because a verified
mechanism is as much a part of the record as a defective one:

- **R2-B1's census is verified in full.** The 26 distinct method-shaped members on
  `lh`/`LiquidHandler`/`STARBackend` receivers partition as 8 `TOOL_SCHEMA` + 13
  `NON_SURFACE_VERB_REASONS` + the 5 named `surface_adjacent` subjects; `receiver_drift = 0` and
  `param_misattributed = 0` — which round 2 asserted but never derived — are both confirmed, the
  latter by checking all three IDENT tokens that hit `PARAM_NAMESPACE`'s 25-member name∪plr_arg
  union (`target_vols`@147, `vols`@427/437, `resource`@327) against the second clause.
- **R2-B3 is verified by exhaustive classification** of the full live token inventory: the four
  positive `OTHER` shapes are disjoint from `IDENT`/`CLASSISH` and jointly exhaustive over every
  non-empty token, and no live token raises.
- **R2-B4d is sound and does not assume a full clone:** §4.4's assertion 0 compares only against
  the clone's *resolved HEAD*, never against an arbitrary historical SHA, which is the one
  operation a shallow clone cannot serve.
- **§0.1–§0.4 are consistent with verbatim preservation** — no rev-3 vocabulary appears in
  §0.1–§0.3, and five rows stating positions revision 3 overturns elsewhere were left standing.
  A byte-diff is impossible (the spec is untracked and no rev-2 copy survives), so this is
  evidence, not proof.

**Reading §0.1–§0.4 alongside this section.** Same rule as before, extended by one step: where a
round-3 row and an earlier row describe the same mechanism, **the round-3 row is authoritative**.
The overlaps: R2-B2's `subject_table_fingerprint` → **R3-B1** (its anti-staleness half is
withdrawn for one kind); R2-B1's census pin → **R3-B2** (given a home); C9/W10's receiver table →
**R3-B3** (reclassified hand-authored); W12's file split → **R3-W5** (recounted, and the count
changed again because of R3-B2 and R3-B3); R2-B3 → **R3-W1** (its reachability story corrected
without reopening the fix); W10 → **R3-W2** (the same illustrative-table defect, recurring inside
R2-B2's fix).

**§0's own heading is left reading "(rev 1 → rev 2)" deliberately.** It is part of round 1's
record and round 3 used it as evidence that §0.1–§0.3 had not been rewritten. Correcting it would
destroy a checkable preservation signal to fix a cosmetic staleness; the sub-headings (§0.4, §0.5)
carry the real scope.

#### Blocking — dispositions

| # | Substance | Disposition | Fix |
|---|---|---|---|
| **R3-B1** | `subject_table_fingerprint` is table-**inert** for all 5 `surface_adjacent` findings — 5 of the 9 blocking set. §5.7's sole worked justification of the anti-staleness property is impossible: adding `use_channels` to `NON_SURFACE_VERB_REASONS` does not flip `in_non_surface` on a *surviving* finding, it **deletes** the finding (§5.4 requires absence from both tables), and a deleted finding leaves a stale *adjudication*, which §5.5 reports as a warning. Task 5's third gate bullet cannot be made green | **ACCEPTED; the claim is withdrawn for this kind, not restated** | **§5.7** gains a per-kind **table-sensitivity table** stating, for each of the ten kinds, whether any canonical-table edit changes its slice *while the finding still exists*. For `surface_adjacent` (and advisory `unknown_method`) the answer is **no**, and the reason is structural, not an oversight: existence of the finding *is* the assertion that all three memberships are `False`. What replaces it is named rather than implied — the detectable event for this kind is **disappearance**, owned by AC-1.14 (any canonical-table edit) and by the census pin (a cookbook-side disappearance, which AC-1.14 cannot see). One degenerate edit that *would* flip the slice (adding a `PARAM_NAMESPACE` key for a non-`TOOL_SCHEMA` verb) is recorded and explicitly **not** leaned on. **Task 5's bullet 3 is replaced** by two tests: the disappearance path for `surface_adjacent`, and a real staleness test on `phantom_verb`, where the property genuinely holds. |
| **R3-B2** | The `blocking_census` pin has no defined storage location: AC-1.6 puts it in a *test literal*, AC-1.7 requires the **gate** to read it, and neither §7.1's `versions.py` inventory nor §5.6(d)'s file table has a slot. `census_drift` is therefore unimplementable, and any home a fixer invents is R2-B1's own hand-listed-constant shape | **ACCEPTED; the home is named** | New computed data file **`training/ingest/data/blocking_census.json`**, emitted by `audit --emit-census --out <dir>` and landed by §5.6(d)'s copy-and-review workflow — the same path every other computed file takes. **One source of truth:** the gate reads the file to print `census_drift`; `test_ingest_audit_findings.py` asserts *observed == the committed file*, and holds no literal of its own. A loader invariant (`set(census) == {k.value for k in BLOCKING_KINDS}`) makes promoting a kind to blocking without updating the file a loud failure. §5.4.1's derivation stays as the reviewer's check on the committed file, explicitly labelled non-authoritative. Recorded in §5.6(d), §7.1, §7.5, AC-1.6, AC-1.7, Tasks 5 and 6. |
| **R3-B3** | §5.6(d) labels `receiver_aliases.json` **computed** via `recipes --emit-receiver-aliases`, but C9 establishes that liquid_handler-vs-other is **undecidable from `recipes.yml`**; the two-way-equality gate is a **key-set** check that says nothing about values. A fixer following §5.6(d) literally emits an all-`other` map, key-set equality still passes, and `surface_adjacent` silently drops from 5 to 0 — because both blocking receiver kinds require `liquid_handler`/`plate_reader` | **ACCEPTED in full; the file is reclassified** | **§5.6(d)** reclassifies `receiver_aliases.json` as **hand-authored (values) with a mechanically-derivable key set**, and the emitter is redefined as a **merge proposal** (`recipes --emit-receiver-alias-keys`): it preserves every existing value, adds newly observed keys as `other` under a `needs_review` list, and never silently completes the map. §5.6(d)'s blanket claim *"every computed file has a gate that re-derives it"* is **false and is deleted** — the column is relabelled *"what checks it, and how strongly"* with the strength named per row (R3-W9). The all-`other` hole gets a **direct** guard rather than resting on the census alone: Task 3 pins the three `liquid_handler` values by name, and §3.3 rule 5 states the value-attribution rule and the interaction with `surface_adjacent`'s count explicitly. |

#### Warnings — dispositions

| # | Substance | Disposition | Where |
|---|---|---|---|
| **R3-W1** | AC-1.4(1)'s "reached by a real token (a trailing comma in an `apis` field)" is false: `split_apis` raises on any empty token *before* the classifier runs, so no pipeline input reaches the branch | **ACCEPTED** | AC-1.4(1) and §3.2. Both branches are now stated as reachable **by direct unit call only** — one via `""`, one via monkeypatch — and the trailing-comma pipeline claim is deleted. The consequence R3-W1 names is stated rather than hidden: for every *producible* input the exactly-one assertion is satisfied by construction, which is correct for a provably disjoint predicate set and is why the test targets the implementation, not the input. AC-1.4(3)'s "that is information to record" is likewise corrected — no live token raises. |
| **R3-W2** | 4 of §5.2's 10 "example (from the live cookbook)" values are fictional: `plate_reader.aspirate` (0 plate_reader receivers exist), `vols` (verified not to misattribute), `aspirate:flow_rates` (line 122 names no in-surface verb), `backends/chatterbox` (it *is* in §3.3's table) | **ACCEPTED** | §5.2. The column is split into **`example`** and **`occurs today?`**, every live example is cited with its `recipes.yml` line, and the three kinds with a live count of **0** carry a constructed example labelled as such. Two examples are replaced with verified real ones: `param_candidate` → **`aspirate:backend_kwargs`** (line 277, where `STARBackend.aspirate` supplies the in-surface verb), and `param_misattributed`'s `vols` is kept but relabelled a **near-miss that does not fire**, with the reason. |
| **R3-W3** | Task 6's "prints `census_drift` without failing when a tenth blocking finding is injected" is self-contradictory: a new blocking finding has no adjudication, so §5.5 rule 1 exits 2 regardless of drift | **ACCEPTED** | Task 6. The fixture is inverted to **drift-down** (a temp `recipes.yml` with the `lh.use_channels` recipe removed → 8 findings, all 8 adjudicated), the expected result is stated explicitly as **exit 0 plus a `census_drift` line**, and the task text records that this is the direction AC-1.7's own rationale calls dangerous — and, post-R3-B1, the *only* detector of a cookbook-side `surface_adjacent` disappearance. |
| **R3-W4** | §7.5's table omits `audit --emit-fingerprint` and `eval_split --emit-lineage-contract`, yet AC-1.16 and Task 8 assert against "every command in §7.5's table"; and `recipes --count` appears in §7.5 but is defined nowhere | **ACCEPTED** | §7.5. Three emitter rows added (`audit --emit-fingerprint`, `audit --emit-census` from R3-B2, `eval_split --emit-lineage-contract`), all **0** when the clone is absent, with the reason stated per row. `recipes --count` is **deleted** rather than defined: the row now names the two `recipes` emitters exactly, which is what makes Task 3's "each `recipes` subcommand exits 5" a definite obligation. |
| **R3-W5** | Four places disagree about the same `data/` split (§5.6(d) 5+5, §7.1 5+5, §0.4's W12 row "six and four", §12.11's heading "four" over five filenames), and §5.5 calls `audit_adjudications.json` the *only* hand-authored artifact besides the registry | **ACCEPTED** | Recounted **after** R3-B2 and R3-B3, which both change it: **eleven files — six hand-authored** (`sources`, `license_rules`, `experimental_partition`, `audit_adjudications`, `import_closure_allowlist`, `receiver_aliases`) **and five computed** (`lineage_contract`, `token_histogram`, `eval_split`, `canonical_tables_fingerprint`, `blocking_census`). §5.6(d), §7.1 and §12.11 are reconciled to exactly that; §5.5's "only hand-authored artifact" sentence is corrected to the accurate claim (it is the only one *authored against the audit's own output*). §0.4's W12 row is preserved unmodified and superseded here. |
| **R3-W6** | `subject_table_fingerprint(kind, subject)` never states how `_param_slice(tok, verb)`'s and Case A's arguments are recovered from the single `subject` string — the same implicit-parsing gap R2-B2 exists to close | **ACCEPTED** | §5.7 gains an explicit **dispatch function** with the parse rule written out per kind: `param_candidate` → `subject.split(":", 1)` → `(verb, tok)`; `param_misattributed` → `(None, subject)`; dotted kinds → `subject.split(".", 1)` → `(receiver_type, member)`, with the argument that the split is unambiguous (no `ReceiverType` value contains a `.`, and every `member` is `[a-z_][a-z0-9_]*`) stated rather than assumed. |
| **R3-W7** | §5.7's `scope="none"` guard is a bare `assert` (removed under `python -O`) and lives inside `_no_table_slice` rather than at the dispatch point; §6.1's `CLASS_MAP` injectivity check has the same shape | **ACCEPTED for both** | §5.7's guard becomes a **raised `AuditError` at the dispatch point**, so a kind mis-routed to *any* wrong case fails, not just one routed to Case C. §6.1's injectivity check becomes a raised `GapError`, and `GapError` joins §7.1's `gap.py` inventory. Both now match the house style every other invariant in this spec uses (§5.3's partition loader, §3.1's reader). |
| **R3-W8** | The `SURFACE_ADJACENT`/`file_backlog_item` deferral is **confirmed correct and correctly scoped** — but `action_ref` is only required to be a non-empty string, and no §12 item names who closes the five open `NON_SURFACE_VERB_REASONS` gaps | **ACCEPTED; the judgment recorded, the residual closed** | Round 3's adjudication that the deferral is honest (PM-3 asks for ownership, not remediation; AC-1.14 makes an in-increment table edit structurally fail, so `file_backlog_item` is *forced*, not chosen) is recorded verbatim in §5.4.1. The residual gets two fixes: §5.5 constrains `action_ref` (and `regeneration_backlog_ref`) to a **closed prefix grammar** validated at gate time, with resolvability declared **unverified by design** and the reason (no backlog reader; F3 forbids `subprocess`); and new **§12.12** names the downstream owner and timing of the five backlog items. |
| **R3-W9** | §5.6(d) says AC-1.17 "re-derives" `lineage_contract.json`; AC-1.17 is a **subset** check, so a contract carrying unused or pre-added keys passes | **ACCEPTED** | §5.6(d)'s column is relabelled *"what checks it, and how strongly"* and every row states whether its check is a **re-derivation**, a **subset/one-way** constraint, or a **key-set-only** constraint (the `receiver_aliases.json` case from R3-B3). The relabel is what makes R3-B3's row expressible at all — under the old column heading there was no way to say "checked, but not the part that matters". |

#### §12 re-examination (round 3)

Round 3 raised no objection to items 1–11. **Item 11 is rewritten** for the recount (R3-W5) and for
`receiver_aliases.json`'s reclassification (R3-B3), which removes it from the copy-in-by-hand set
and changes the item's own justification. **Item 12 is new** (R3-W8): the ownership and timing of
the five `NON_SURFACE_VERB_REASONS` backlog items, plus the explicit statement that `action_ref`
resolvability is unverified by design. **Item 13 is new** (R3-B1): the per-kind asymmetry of the
digest's anti-staleness property, recorded as a limitation rather than buried in §5.7, because it
is the thing a round-4 reviewer should check first.

### 0.6 Round 4 dispositions (rev 4 → rev 5)

Round 4 (`260827_corpus_ingestion_spec_challenge_round4`, verdict **not_ready**, 3 blocking + 10
warning) is the first round that **reopened nothing**. All three of round 3's blocking
dispositions and all nine of its warnings were re-checked against live repo state and **verified
fixed**:

- **R3-B1's table-sensitivity claim is verified structurally.** `param_namespace.py:47` imports
  `PHASE2_TOOL_NAMES` and `PARAM_NAMESPACE`'s 13 keys are exactly those names — all `TOOL_SCHEMA`
  keys — so §5.7's argument that `in_param_namespace` is `False` for any member absent from
  `TOOL_SCHEMA` is correct against the live file, and `surface_adjacent`'s slice is genuinely
  invariant rather than merely undisproven.
- **R3-B2's `blocking_census.json` and R3-B3's `receiver_aliases.json` reclassification both hold**,
  and the nine-finding census reproduced a **third** time from the live files: 26 distinct
  method-shaped members on `lh`/`LiquidHandler`/`STARBackend` receivers = 8 `TOOL_SCHEMA` + 13
  `NON_SURFACE_VERB_REASONS` + 5 `surface_adjacent`; the 31 DOTTED receivers derived independently
  match §3.3 exactly; 3 map to `liquid_handler`, 0 to `plate_reader`.
- **R3-W5's file-count recurrence is closed.** 6 hand-authored + 5 computed = 11 now agrees across
  §0.5, §5.6(d), §7.1, §12.11, §5.5 and Task 6, **and** matches the per-task data-file creation
  lists exactly (Task 1: 1, Task 2: 1, Task 3: 2, Task 4: 2, Task 5: 2, Task 6: 1, Task 8: 2 = 11).
- **R3-W4's §7.5 table is complete.** Its 14 rows cover every subcommand defined anywhere in the
  spec, and `recipes --count` is deleted with no residual reference — so Task 8's parametrization
  over the table is a finite, checkable obligation.

**Reading §0.1–§0.5 alongside this section.** Same rule, extended one more step: where a round-4
row and an earlier row describe the same mechanism, **the round-4 row is authoritative**. Round 4's
overlaps are narrower than any prior round's, because it overturned no design: §3.1's reader
invariant list → **R4-B1** (one bullet scoped, the rest unchanged); §7.1's one-line CLI note →
**R4-B2** (corrected to match the ACs, which are unchanged); §5.2's `finding_id` expression →
**R4-B3** (serialization pinned; the identity-only *property* C3 chose is untouched); §5.7's
table-sensitivity table → **R4-W8** (recounted, one example corrected); §3.3 rule 5's "two
independent detectors" → **R4-W2** (independence re-scoped, both detectors kept).

**§0's own heading is still left reading "(rev 1 → rev 2)" deliberately** — round 3 used it as
evidence that §0.1–§0.3 had not been rewritten, round 4 re-used the same signal, and revision 5
preserves it for the same reason. The sub-headings carry the real scope.

#### Blocking — dispositions

| # | Substance | Disposition | Fix |
|---|---|---|---|
| **R4-B1** | §3.1 lists "exactly 91 records" among the reader invariants "all raising `RecipesError`", unconditionally and for every path. Task 3 parses a small path-truncation fixture, Task 5 appends a recipe to a temp `recipes.yml` **twice** (including the `lh.mix` test the spec calls "the test that proves the fix"), and Task 6 removes a recipe (rev 4's own R3-W3 drift-down fixture). All three route through `load_recipes()` and would raise on the count before the property under test is ever reached. No carve-out exists anywhere | **ACCEPTED; the constant is re-homed, not merely scoped** | **§3.1.** The reader's invariant list is now exactly the set of properties that hold for **any** well-formed input — per-record keys, scalar quoting, `chapter` range, the `path` regex, the line-accounting reconciliation — so every fixture in this spec parses. The record **count** is not a grammar property at all; it is a **pin about the live cookbook**, in the same category as `token_histogram.json`, and it moves into that file as a new `n_recipes` field (no new data file; the 6+5=11 reconciliation is preserved). `load_recipes()` holds **no count literal**; AC-1.4(2)'s existing exact histogram comparison over the default path is what catches a truncated cookbook, alongside §4.4's `recipes_yml_sha256`. Each of Task 3/5/6's fixtures is re-confirmed consistent under the corrected rule at the point of use. |
| **R4-B2** | §7.1 says `cli.py`/`__main__.py` hold "argparse subcommands, mirroring `floor_gen/cli.py`", whose live precedent is `python -m floor_gen <subcommand>` — never `python -m floor_gen.<module>`. But **every** AC (1.2/1.3/1.6/1.7/1.9/1.13/1.15/1.17), all five §9 gate rows, and Tasks 0/2/4/6/7 invoke `python -m ingest.<module> --flag`. Under §7.1's reading, `python -m ingest.audit --gate` imports a module with no `__main__` guard, ignores `--gate`, and exits **0** having checked nothing — a blocking gate that passes vacuously. Compounding: AC-1.0 gates `python -m ingest --help` at **Task 1**, while `cli.py`/`__main__.py` were created in **Task 6**, so Tasks 2–5's gates invoked a CLI that did not yet exist | **ACCEPTED in full; the majority spelling wins and §7.1 is corrected to it** | **§7.1** (rewritten), **§7.5** (a stated invocation form), **Task 1** and **Task 6**. The package is **module-per-command**: each of `licenses.py`, `recipes.py`, `eval_split.py`, `audit.py`, `gap.py` owns its own `argparse` parser and its own `if __name__ == "__main__":` block. There is **no shared subcommand dispatcher** and the "mirrors `floor_gen/cli.py`" claim is deleted as false. `cli.py` survives with a different and smaller job — shared exit-code constants and the one `CookbookUnavailable` → exit 5 wrapper every module routes through (§7.5's convention implemented once, not five times) — and `__main__.py` becomes a **signpost**: `python -m ingest --help` lists the five module commands and exits 0, and never dispatches. **Both move from Task 6 to Task 1**, with the package scaffold, which is what makes AC-1.0 satisfiable at Task 1 and Tasks 2–7's gates runnable when they run. |
| **R4-B3** | `finding_id = sha256(f"{kind}\|{subject}\|{AUDIT_RULES_VERSION}")[:16]` interpolates a `class FindingKind(str, Enum)` member: `f"{kind}"` yields `"phantom_verb"` on 3.10/3.12 but `"FindingKind.PHANTOM_VERB"` on 3.11. Twelve lines below, `_adjudicable_view` correctly uses `f.kind.value` — so the spec contradicts itself and `finding_id`'s definition is **interpreter-version-dependent**, which is R2-B2's "two disjoint key spaces" hazard arriving via Python version instead of via two implementers. Separately, **`canonical_json` is used by both `canonical_tables_fingerprint()` and `subject_table_fingerprint()` and defined nowhere**; §7.4 pins artifact serialization only. Both hash outputs are hand-copied into committed files that AC-1.7 and AC-1.14 require exact equality against | **ACCEPTED in full, both halves** | **§5.2.** (a) `finding_id` stops interpolating anything: it hashes `canonical_json({"kind": kind.value, "subject": subject, "rules_version": AUDIT_RULES_VERSION})`, matching `_adjudicable_view`'s already-correct `.value` usage. Every hash input in the spec was swept for the same bug — the only other enum reaching a hash payload is `_projection()`'s `receiver_type`, and it is **verified safe**: live `ToolSpec.receiver_type` is a plain `str` (`tool_schema.py:41`), not an enum. §5.2 property 3's "since `finding_id` hashes `kind\|subject`" parenthetical is corrected. (b) **`canonical_json` is defined explicitly** at its first use site in §5.2, with its four arguments each justified, and cross-referenced from §5.7 and §7.4 — including the deliberate statement that hash serialization and **artifact** serialization (§7.4) are different on purpose. |

#### Warnings — dispositions

| # | Substance | Disposition | Where |
|---|---|---|---|
| **R4-W1** | `receiver_aliases.json`'s first-run bootstrap is undefined: the emitter "reads the existing committed file", but Task 3 is where the file is first created | **ACCEPTED** | §3.3 rule 5 + §5.6(d). Task 3's hand transcription of §3.3's table **is** the bootstrap; the emitter is a second-run-onward tool and is never needed to create the file. Running it with no committed file present is now a defined, loud failure (`RecipesError`, exit 1) rather than an all-`other` map with 31 `needs_review` entries — which would be a generator for exactly the file C9 proves cannot be generated. |
| **R4-W2** | §3.3 rule 5's "two independent detectors" over-claims: Task 5 emits the census **from** Task 3's alias map, so a mis-authored map yields `surface_adjacent: 0` in both the observation and the committed pin, and AC-1.6 stays green | **ACCEPTED; the framing corrected, both detectors kept** | §3.3 rule 5. The three guards are now ordered **by when they can fire**: Task 3's three-value pin is the **only** one that fires on an initial authoring error; §5.4.1's written derivation is a reviewer's check on the committed census; the census pin catches a **later regression** only. The word "independent" is deleted where it was false and stated precisely where it is true. |
| **R4-W3** | AC-1.7's "exits 2 otherwise" is unqualified by §7.5's exit 5 — R2-B4b's shape recurring in the AC that owns the blocking gate | **ACCEPTED** | AC-1.7. The exit-5 clone-absent case is stated inline, and exit **1** (an unreadable or absent census file, R4-W10) with it, so the AC now enumerates every code `audit --gate` can return. |
| **R4-W4** | Task 8 says the README documents "all seven exit codes (0/1/2/4/5/6/7)"; §9 defines **eight** — exit 3 (D1's licensing STOP) is missing | **ACCEPTED** | Task 8. Corrected to **eight (0/1/2/3/4/5/6/7)**, with exit 3 named. |
| **R4-W5** | No injection points are stated for `gate()` / `run_audit()` / `load_blocking_census()` / the adjudications loader, though Tasks 5 and 6 require substituting them | **ACCEPTED** | §5.5 gains the four signatures with `Path \| None` defaults, and a stated testing convention: injection is **Python-level only** — tests call the function, the CLI exposes **no** path flags, so AC-1.7's "no `--force`, no bypass" is preserved. The monkeypatch targets Tasks 3/5/6 use are named there too. |
| **R4-W6** | Task 5 monkeypatches `TOOL_SCHEMA["mix"].receiver_type`, but `ToolSpec` is `@dataclass(frozen=True)` — attribute assignment raises `FrozenInstanceError` | **ACCEPTED** | §5.5's injection note + Task 5. The technique becomes `monkeypatch.setitem(TOOL_SCHEMA, "mix", dataclasses.replace(TOOL_SCHEMA["mix"], receiver_type="plate_reader"))`. Verified live: `TOOL_SCHEMA`, `PARAM_NAMESPACE` and `NON_SURFACE_VERB_REASONS` are all plain `dict`s, so `setitem` is visible through any import form; `PHASE2_TOOL_NAMES` is a `frozenset` materialized at import and does **not** follow a `setitem`, which is recorded so no test leans on it. |
| **R4-W7** | `param_candidate`'s subject `f"{verb}:{tok}"` is ambiguous when a recipe names ≥2 in-surface verbs (live: recipes.yml 207, 432, 452) | **ACCEPTED** | §5.2's subject row + §5.4's `PARAM_CANDIDATE` bullet. The rule is the **full cross product**: one finding per (in-surface verb, IDENT token) pair, with "in-surface verb of a recipe" defined by §6.4's T3 matching rule. Line 432 is worked through as the live case. |
| **R4-W8** | §12.13's "table sensitivity for six" miscounts (the table is 5 yes + 1 partial + 4 no), and `param_misattributed`'s `plr_arg` example would **delete** the finding rather than stale it | **ACCEPTED** | §5.7's table + §12.13. Recounted to **five, plus one partial**. `param_misattributed`'s row now cites `kind`/`required` as the unconditional examples and states exactly when `name`/`plr_arg` is one and when it deletes the finding instead. |
| **R4-W9** | The `python -O` test has no stated mechanism — asserts cannot be disabled inside a running interpreter, and the only mechanism is a subprocess the spec bans | **ACCEPTED; replaced with something stronger, not dropped** | §7.3(a) + Task 5. The `-O` subprocess is deleted. §7.3(a)'s direct-ban AST scan — which already walks every ingest module — gains `ast.Assert`, making "no bare `assert` anywhere in `training/ingest/`" a **static, complete, package-wide** property instead of a single-path behavioural probe. Task 5's existing `pytest.raises(AuditError)` already fails on an `AssertionError`, so the two together cover both halves. |
| **R4-W10** | §5.5 never mentions reading the census, and a **missing** `blocking_census.json` has no defined gate behaviour | **ACCEPTED** | §5.5 + AC-1.7 + §9's G2 row. The gate's evaluation order is stated (clone → census → findings), and an absent/unreadable/invalid census is exit **1** — a measurement error, loudly distinct from a census *mismatch* (advisory `census_drift`, exit unaffected), from exit 2 (a real unadjudicated finding) and from exit 5 (no cookbook). The file is committed in-repo, so its absence is never an environment condition the way a missing clone is. |

#### §12 re-examination (round 4)

Round 4 raised no objection to items 1–13. **Item 11 gains one line** for `token_histogram.json`'s
new `n_recipes` field (R4-B1) — the file set is unchanged at eleven. **Item 13 is corrected** for
R4-W8's recount. **Item 14 is new** (R4-B2): the package deliberately has no unified CLI, and
`python -m ingest` is a signpost rather than a dispatcher.

### 0.7 Round 5 dispositions (rev 5 → rev 6)

Round 5 (`260827_corpus_ingestion_spec_challenge_round5`, verdict **has_gaps**, 1 blocking + 4
warning + 4 suggestion) is the **fourth consecutive round to reopen nothing**. All three of round
4's blocking dispositions were re-verified against live repo state and found fixed, and nine of
ten warnings were spot-checked with two verified in depth:

- **R4-B1's re-homing holds.** `load_recipes()` carries no count check; `token_histogram.json`
  gained `n_recipes` with its version bumped to `"2"`; Task 3/5/6's fixtures are re-confirmed at
  their points of use. Round 5 walked the truncation case independently and found it caught twice
  over (AC-1.4(2)'s `n_recipes` comparison **and** §4.4's byte pin), both clone-gated, which is
  correct — no clone means no file to truncate. `recipes.yml` still has exactly **91** `- title:`
  records, a **fourth** independent reproduction.
- **R4-B2's module-per-command form is consistent across all 49 `python -m ingest` occurrences.**
  Every functional invocation is the module form; the six space-form occurrences are AC-1.0's
  `--help` and five explicit negative statements. `cli.py`/`__main__.py` genuinely land in Task 1
  and are genuinely gone from Task 6.
- **R4-B3 is verified in both halves, including the live sweep.** `canonical_json` is complete for
  byte-reproducibility; every payload was independently checked serializable and deterministic
  (`_projection()` never touches `ToolSpec.effects`, a `frozenset` that would raise); and
  `tool_schema.py:41`'s `receiver_type: str` on a frozen dataclass is confirmed a plain `str`.
- **R4-W9's `ast.Assert` ban is a real static mechanism** riding the existing AST walk, and
  §7.3's explicit scope paragraph closes the pytest false-positive risk **by construction**.
- **R4-W5's keyword-only injection genuinely prevents a `--force`-shaped bypass** rather than
  relocating it, because reaching the keyword requires editing the test suite in a reviewed diff.

**Reading §0.1–§0.6 alongside this section.** Same rule, extended one final step: where a round-5
row and an earlier row describe the same mechanism, **the round-5 row is authoritative**. Round 5's
overlaps are the narrowest yet, and every one of them is a *residual* of a round-4 fix rather than
an overturning of it: R4-B2's entry-point shape → **R5-B1** (the shape is right; nothing observed
it) and **R5-W3** (the probe is weaker than its stated conclusion); R4-B1's "ONE home" claim →
**R5-W1** (a second, unchecked home was already in §4.3); R4-B2's new normative `argparse`
template → **R5-W2** (its usage-error path collides with §9's exit 2); R4-B3's serialization pin →
**R5-W4** (the regression test named for it could not be written, and no behavioural test can
exist on 3.10/3.12 — see §5.2, where the remedy becomes structural).

**§0's own heading is still left reading "(rev 1 → rev 2)" deliberately** — rounds 3, 4 and 5 each
re-used it as evidence that §0.1–§0.3 had not been rewritten, and revision 6 preserves it for the
same reason. §0.4's W12 row still says "six hand-authored and four computed", the superseded count;
round 5 confirmed that standing row as the preservation signal working as designed. The
sub-headings carry the real scope.

#### Blocking — disposition

| # | Substance | Disposition | Fix |
|---|---|---|---|
| **R5-B1** | Rev 5 made the `__main__` guard hand-copied boilerplate in five modules and *simultaneously* made in-process testing an explicit package rule (§5.5, §7.4, §7.5, Task 6, Task 8). The guard line is therefore the one link in the chain **no specified test crosses**. Omit it from `audit.py` and `python -m ingest.audit --gate` imports the module, ignores `--gate`, and exits **0** — verbatim R4-B2's scenario — while every specified test, AC-1.0 and Task 1's probe all stay green, because those only exercise `__main__.py`. Sharpest for `audit --gate`, the one gate whose CLI form writes **no artifact**, so nothing catches it incidentally. AC-1.7's literal contract is untestable as specified | **ACCEPTED; a detector is installed, and the probe is made structural as well as behavioural** | **Task 8** gains `test_ingest_entrypoints.py`: `runpy.run_module(f"ingest.{m}", run_name="__main__")` parametrized over the five command modules, asserting `SystemExit` fires with the expected code — in-process, no subprocess, so F3 and §7.3 are untouched (the ban is scoped to `training/ingest/**.py`; the test lives in `training/tests/`). Two assertions per module: no-args → `EXIT_USAGE` (which exists because of R5-W2), and for `audit` specifically `--gate` with the clone absent → **5**, which is AC-1.7's contract observed end-to-end for the first time. **A missing guard produces no `SystemExit` at all**, so the failure is loud and names the module. §7.1, §7.5, §5.5 and AC-1.7 each gain the cross-reference, per round 3's standing rule: name the event the mechanism detects and the observation that would fire. |

#### Warnings — dispositions

| # | Substance | Disposition | Where |
|---|---|---|---|
| **R5-W1** | R4-B1's "the count's ONE home" is false against §4.3: `eval_split.json` has carried `n_recipes: 91` since an earlier revision and **none** of §4.4's six assertions checks it. Two committed homes for one fact — one exact-compared, one an unchecked hand-copied literal about live cookbook data, which is the shape R4-B1's fix existed to consolidate away | **ACCEPTED; cross-checked rather than deleted, and a second instance of the same defect is fixed with it** | §3.2, §4.3, §4.4, §5.6(d). New **§4.4 assertion 6** ties `eval_split.json`'s `n_recipes` to `token_histogram.json`'s and `n_held_out` to `len(held_out_paths)` — the *second* instance, one field over, which round 5 did not name and which had the identical shape. Both are **clone-independent** (both files are committed in-repo), so assertion 6 runs on a checkout with no clones. §3.2's comment is corrected to the accurate claim: one **derived** home, every other copy pinned to it. The assertion count moves **6 → 7** everywhere it appears. |
| **R5-W2** | §7.1's normative template uses `add_mutually_exclusive_group(required=True)` + `parse_args()`; `argparse`'s usage-error path calls `sys.exit(2)` **before** any handler runs, colliding with §9's exit 2 = "unadjudicated blocking finding". §7.5 argues at length that `audit --gate` must never return an unearned 2, and this reintroduces exactly that through a door the spec never closed | **ACCEPTED; the collision is removed, not documented** | §7.1, §7.5, §9, Task 1, Task 8. `cli.py` owns `IngestArgumentParser`, which overrides **`error()`** — not `exit_on_error=False`, which does not cover missing-required-argument and would have left the hole half-open — to raise `UsageError`, which `cli.run` maps to **exit 64** (`sysexits.h` `EX_USAGE`). §9's vocabulary is restated precisely: **eight decision codes 0–7, plus one non-decision code 64** that is deliberately outside the range any gate wrapper reads. `--help` still exits 0. **Writing `cli.py` as normative code exposed a second day-one defect rev 5 had left standing**: `cli.run` was specified to map four typed errors that live in the five command modules, each of which imports `cli` — a circular import that would have failed on the first `python -m ingest.audit`. `cli.py` now owns the error **roots** (`IngestError`/`CookbookUnavailable`/`UsageError`) and the modules subclass them, with `recipes.py` re-exporting `CookbookUnavailable` so §7.1's inventory stays literally true. |
| **R5-W3** | Task 1's probe (`python -m ingest licenses` exits 1) tests only a **malformed** dispatcher call. A hybrid — a real dispatcher in `__main__.py` plus the five guards — that maps its own usage errors to 1 passes the probe while `python -m ingest licenses --report` also works. The probe falsifies only dispatchers that exit 0 or leave `argparse`'s 2 in place | **ACCEPTED; a well-formed probe **and** a structural one are added** | Task 1 + §7.3(a) + §7.1. (i) The malformed probe stays. (ii) A **well-formed** probe is added: `python -m ingest licenses --report` exits 1 **and writes nothing** — the test snapshots `training/ingest/out/` and asserts it is byte-identical after, which is what a real dispatcher would fail. (iii) §7.3(a) gains a **third** static rule: `ingest/__main__.py` contains zero imports of any of the five command modules. A dispatcher must import a handler; a signpost must not. That makes "the two spellings can never both appear to work" structural rather than behavioural, and the signpost's five-command list is literal text for exactly this reason. |
| **R5-W4** | Task 5's `compute_finding_id` regression test cannot be written against §5.2's signature (passing "its `.value`" — a plain `str` — makes `kind.value` raise `AttributeError`), and even coerced it does not test what it names: under the *old* buggy code the two spellings agree on 3.10/3.12 and differ only on 3.11, so the test is itself interpreter-version-dependent — the property R4-B3 was eliminating. The likely fixer response (widen to `str \| FindingKind`) reopens R2-B2's two-key-spaces hazard | **ACCEPTED; and the deeper problem it exposes is stated rather than patched** | §5.2 + Task 5. Round 5's probe asks which of two version-independent pins is intended; the honest answer is that **neither closes the class**, because `f"{kind}"` is *behaviourally correct* on 3.10 and 3.12 — no test on those interpreters can see it. So the remedy becomes structural: subjects are built by `dotted_subject()`/`param_subject()` (string concatenation, `.value` applied in exactly one place) instead of by f-strings, so **no enum interpolation survives anywhere in the identity path**; `compute_finding_id` gains an explicit `isinstance` guard raising `AuditError`, and widening it to `str \| FindingKind` is named and forbidden. Task 5's bullet is replaced by three assertions that fire on **every** interpreter: a byte pin on the canonical payload, the `AuditError` on a plain-`str` `kind`, and a full-run sweep asserting no `b"FindingKind."`/`b"ReceiverType."` reaches any payload or subject. |

#### Suggestions — dispositions

| # | Substance | Disposition | Where |
|---|---|---|---|
| **R5-S1** | §5.5's `gate()` docstring says the `__main__` block is `raise SystemExit(gate())` "and nothing else"; §7.1's normative template is `raise SystemExit(_main())` → `cli.run` → handler. Both written in rev 5, contradicting each other on three lines | **ACCEPTED** | §5.5. The docstring names the full chain (`_main()` → `cli.run()` → `gate()`) and points at Task 8's `runpy` test as the thing that proves the chain exists. |
| **R5-S2** | Four places still instruct the implementer in the vocabulary §7.3(a) now statically bans ("the loader **asserts**") | **ACCEPTED, and one more instance found** | AC-1.6, §5.6(d) (two rows) and §5.3's evidence-asymmetry sentence, which round 5 did not name and has the same shape. All now read "raises `AuditError` unless". Task 5's phrasing was already correct. |
| **R5-S3** | Undefined precedence for `recipes --emit-receiver-alias-keys` when the clone is absent (exit 5) **and** the committed file is absent (exit 1) — both true on a CI checkout during Task 3 | **ACCEPTED** | §3.3 rule 5, §5.6(d), §7.5, Task 3. **Clone check first**, for §5.5's stated reason: do not tell an operator to author a file when the command could not have run anyway. Same ordering as `audit --gate`'s clone → census. |
| **R5-S4** | Whether the ten `FindingKind`s are mutually exclusive per token is never stated, and R4-W7's cross product makes the overlap concrete at recipes.yml:432 | **ACCEPTED; verified live and stated with its safety argument** | §5.4. The kinds are **not** a partition of tokens. Verified at recipes.yml:432: `sorted` and `use_channels` each yield an advisory `unknown_method` (`none.sorted`, `none.use_channels`) **and** participate in the four `param_candidate` findings the cross product produces against `lh.aspirate`/`lh.dispense`. Every live overlap is **advisory-to-advisory**; the four blocking kinds are mutually exclusive per subject by construction, so no token is ever double-counted in the blocking census. Recorded as §12 item 15. |

#### §12 re-examination (round 5)

Round 5 raised no objection to items 1–14. **Item 11 is unchanged** (the file set stays at eleven;
R5-W1 adds an assertion, not a file). **Item 15 is new** (R5-S4): the advisory finding kinds are
not a partition of tokens, so the `unknown_method` ranking and the `param_candidate` table
deliberately overlap.

### 0.8 Round 6 dispositions (rev 6 → rev 7)

Round 6 (`260827_corpus_ingestion_spec_challenge_round6`, verdict **has_gaps**, 1 blocking + 2
warning + 1 suggestion) is the **fifth consecutive round to reopen nothing**. It re-verified round
5's disposition (R5-B1's `test_ingest_entrypoints.py` is a real detector: a missing guard produces
no `SystemExit` at all, so `pytest.raises` fails and names the module) and explicitly confirmed
that no disposition from rounds 1–5 needed revisiting.

All four findings are **one shape at four scales**: a fact stated correctly in one section and
either contradicted, duplicated, or omitted at the sites a fixer actually reads. Round 6 found no
design defect at all. That is worth stating plainly, because it changes what this revision is:
revision 7 is a **transcription** revision, and every one of its edits either propagates §7.1's
existing design outward or deletes a competing copy of it. Nothing below re-decides anything.

**Reading §0.1–§0.7 alongside this section.** Same rule, extended one more step: where a round-6
row and an earlier row describe the same mechanism, **the round-6 row is authoritative**. Round 6's
overlaps are narrower still, and all three are *residuals of revision 6's own edits* rather than
overturnings: R5-W2's exception hierarchy → **C1** (designed in §7.1, never propagated) and
**C2** (`UsageError` declared twice inside the section that designed it); R5-W2's new exit-64
boundary → **C3** (a flag whose enforcement side of that boundary was never stated, and which only
became consequential *because* revision 6 drew the boundary).

**§0's own heading is still left reading "(rev 1 → rev 2)" deliberately** — rounds 3, 4, 5 and now
6 each re-used it as evidence that §0.1–§0.3 had not been rewritten, and revision 7 preserves it
for the same reason. §0.4's W12 row still says "six hand-authored and four computed", the
superseded count, and it is likewise preserved: rounds 5 and 6 both confirmed that standing row as
the preservation signal working as designed. The sub-headings carry the real scope.

#### Blocking — disposition

| # | Substance | Disposition | Fix |
|---|---|---|---|
| **C1** | Revision 6's exception-hierarchy fix (roots `IngestError`/`CookbookUnavailable`/`UsageError` owned by `cli.py`; the per-module classes subclassing `cli.IngestError`; `recipes.py` re-*exporting* `CookbookUnavailable`) was written into **§7.1 only**. Every normative declaration site kept the pre-fix spelling: §2.1 `class RegistryError(ValueError)`, §5.7 `class AuditError(ValueError)`, §6.1 `class GapError(ValueError)`, and — the load-bearing contradiction — §3.1's `class CookbookUnavailable(RecipesError)` **defined in `recipes.py`**, against §7.1's `class CookbookUnavailable(IngestError)` defined in `cli.py`. Two files claimed the same class with two different bases. Task 1's `cli.py` deliverable list omitted both roots; Task 3's list still assigned `CookbookUnavailable` to `recipes.py`. A fixer reading any one module's section in isolation reproduces **exactly** the circular import R5-W2 existed to remove | **ACCEPTED in full; propagated to every site, and the hierarchy is now stated as a table rather than as prose** | **§7.1** gains the **single normative hierarchy table** — every error class in the package, its defining module, its base, and its exit mapping — and every other site now points at it instead of restating it. Declaration sites corrected: **§2.1** (`RegistryError(cli.IngestError)`), **§3.1** (`RecipesError(cli.IngestError)`; `CookbookUnavailable` **imported and re-exported**, with the `__all__` line written out and the redeclaration explicitly forbidden), **§5.7** (`AuditError(cli.IngestError)`), **§6.1** (`GapError(cli.IngestError)`). **Task 1**'s `cli.py` deliverable now names `IngestError` and `CookbookUnavailable` as deliverables; **Task 3**'s names the re-export, not a definition. **Two classes the round-6 brief did not name were found by the full grep the fix required** and are now in the table: `io.py`'s `ProtectedPathError` **joins** the hierarchy (it was `RuntimeError`, so a protected-path write escaped `cli.run` as an uncaught traceback instead of exit 1), and `eval_split.py`'s `EvalSplitLeak` is **deliberately excluded and marked so** — it maps to exit **6**, and subclassing `IngestError` would have made `cli.run` silently remap G5's leak verdict to 1. That exclusion is the reason the table lists non-members as well as members. **Task 8** gains the detector: an import-time test asserting `issubclass(X, cli.IngestError)` for the five members and `not issubclass(EvalSplitLeak, cli.IngestError)`, plus a `ProtectedPathError` → 1 exit assertion, so "the hierarchy is what §7.1 says" is now observed rather than asserted (round 3's standing rule; §7.1's table names the event and the observation). |

#### Warnings — dispositions

| # | Substance | Disposition | Where |
|---|---|---|---|
| **C2** | §7.1 declares `UsageError` **twice**, ~35 lines apart, in two normative code blocks, with two different bases: `class UsageError(Exception)` in the `cli.py` parser block and `class UsageError(IngestError)` in the hierarchy block. Same "declared twice, disagreeing" shape as R5-S1, recurring inside the section revision 6 restructured. The surrounding prose is true only under the second | **ACCEPTED; the earlier declaration deleted, not annotated** | §7.1. The parser block no longer declares any exception — it carries a one-line pointer to the hierarchy block below it, which is now the **only** place in the document where any of the three roots is declared. The docstring's content (*"a malformed command line. NOT a measurement, NOT a verdict."*) moves onto the surviving declaration rather than being lost with the stray one. The prose at the end of the block — *"letting it fall through to `IngestError` → 1 is the right answer for a bug"* — is re-checked and correct under the surviving declaration, and it is now the sentence that **requires** `UsageError` to subclass `IngestError`, so the two cannot drift apart again silently. |
| **C3** | §7.5's six `--emit-*` rows omit the `--out` flag that §7.1's template, §5.6(d)'s file-by-file table and §4.3 all supply when invoking the same commands, and `--out`'s enforcement was unspecified: required (→ **64**) or handler-validated (→ **1**)? Those land on opposite sides of the exit-64/decision-code boundary revision 6 had just drawn, so the ambiguity became consequential in this revision. AC-1.16 and Task 8 parametrize row-for-row against §7.5, so an incomplete row breaks the parametrization | **ACCEPTED; `--out` is required, enforced by the parser, and the ordering against the clone check is stated** | §7.1, §7.5, Task 8. `--out` is **required with every `--emit-*` flag and with no other flag** — `--gate`/`--report`/`--check-descend` must keep working without it, which is why plain `required=True` is wrong. `cli.IngestArgumentParser` gains an `out_required_for=` constructor argument and enforces it **inside `parse_args`, through `self.error()`**, so a missing `--out` funnels to `UsageError` → **64** exactly like any other usage error, with no second mechanism. **Ordering, stated because both conditions can hold at once:** `parse_args` runs inside `cli.run` *before* the handler, and every clone check lives in a handler — so a missing `--out` **always** wins, and `audit --emit-census` with neither `--out` nor a clone exits **64**, not 5. All six of §7.5's rows now carry `--out <dir>` literally, and a seventh row is added for the 64 case so the parametrized test has a row to point at. |

#### Suggestions — dispositions

| # | Substance | Disposition | Where |
|---|---|---|---|
| **C4** | §7.1's `sources.py` inventory line lists only `SourceRow, Genre, ExtractorKind, AdmissionState, load_registry` — missing `RegistryError`, `by_id` and `registry_path`, all three declared in §2.1 and all three used elsewhere in the spec (`by_id` by §3.1's `default_recipes_path()`). Every other module's inventory line carries its error class plus its full public surface | **ACCEPTED** | §7.1. The line is completed. The omission mattered slightly more than a typo: `RegistryError` is one of the five classes C1 re-bases, so an inventory that did not mention it was one more place the hierarchy was invisible. |

#### §12 re-examination (round 6)

Round 6 raised no objection to items 1–15, and item 14 (*"the package has no unified CLI"*) was
specifically re-read while tracing C1 through `cli.py` — the finding is that `cli.py`'s **content**
was under-propagated, not that the no-dispatcher choice was wrong. **No item is added**: C1–C4 are
all defects with fixes, none of them a limitation being accepted. The file set stays at eleven
(item 11); `cli.py` and `__main__.py` remain code, not data.

### 0.9 Round 7 dispositions (rev 7 → rev 8) — FINAL

Round 7 (`260827_corpus_ingestion_spec_challenge_round7`, verdict **has_gaps**, 1 blocking + 3
warning + 3 suggestion) is the **sixth consecutive round to reopen nothing**, and it is the
**terminal** round: it found **no design defect of any kind**, re-derived revision 7's most
contested decision (`EvalSplitLeak`'s exclusion from `cli.IngestError`) independently and confirmed
it *correct*, and recommended applying its findings as revision 8 and closing the adversarial loop
without a round 8. This revision does that.

**What the blocking finding actually is, because it is not the usual shape.** C1 is not "the design
is wrong" and not even "the design is stated in one place and contradicted in five" (round 6's
shape). It is: *the design is right, stated consistently at three sites, and rests entirely on one
runtime contract that no test drives and no code block states.* Task 4 already had three leak
fixtures, but every one of them tests `check_corpus_for_leak`/`assert_no_leak` — functions that
return messages and raise, and therefore cannot observe an exit code — while every `--check-leak`
invocation in the document used the clean 188-row sidecar and expected 0. So the whole
`EvalSplitLeak` → 6 mechanism had, at the CLI level, exactly zero assertions. A handler written
`assert_no_leak(rows); return 0` would let the class escape as an uncaught traceback → exit **1**,
G5 would report "measurement error" on a real eval-split leak, and the suite would be green.

**Reading §0.1–§0.8 alongside this section.** Same rule, extended one last step: where a round-7
row and an earlier row describe the same mechanism, **the round-7 row is authoritative**. Round 7's
overlaps are all residuals of revision 7's own edits: revision 7's hierarchy table → **C1** (the
one row of it with no behavioural observation) and **C5** (an assertion stated against a value the
table does not literally contain); revision 7's `--out` fix → **C3** (the rule stated as a glob one
of its six instances does not match) and **C4** (the row added to carry it is the only row of that
table that is not 1-to-1 with a test case); revision 7's §7.3(a) rule 4 → **C6** (added without the
cross-reference its matched-pair rule 3 already had).

**§0's own heading is still left reading "(rev 1 → rev 2)" deliberately** — rounds 3–7 each re-used
it as evidence that §0.1–§0.3 had not been rewritten, and revision 8 preserves it for the last
time, along with §0.4's superseded "six hand-authored and four computed" W12 row. Both are the
preservation signal working as designed; the sub-headings carry the real scope.

#### Blocking — disposition

| # | Substance | Disposition | Fix |
|---|---|---|---|
| **C1** | The `EvalSplitLeak` → exit-6 mechanism is asserted in prose at three sites (§7.1's hierarchy table, §4.5, AC-1.13) and **tested nowhere**: no test anywhere drives a leaking input through `--check-leak` and asserts 6. Task 4's three leak fixtures all exercise the *library* functions; every CLI-level `--check-leak` in the document uses the clean 188-row sidecar and expects 0. Task 8's hierarchy test compounds it asymmetrically — the newly-rebased `ProtectedPathError` gets a full end-to-end assertion (driven through `cli.run`, returns 1) while `EvalSplitLeak` gets only a static `not issubclass(...)`, on exactly the class whose runtime contract is the unverified one. A handler written `assert_no_leak(rows); return 0` with no `try/except` — plausible, since `assert_no_leak` is named as an assert-style raiser and its catch was specified only in a trailing code comment — lets the class escape as an uncaught traceback → interpreter exit **1**, so G5 reports a measurement error on a real leak with every specified test green | **ACCEPTED in full; the test is added, and (with C7) so is the code it verifies** | **Task 4** gains the exit-6 assertion: the existing **type-2** fixture (a `train`-split row on a held-out path) is written to a `tmp_path` sidecar and driven through the CLI entry point — `eval_split._main(["--check-leak", str(fixture)]) == 6`, **exactly 6, not merely non-zero** (the defect's own symptom is non-zero), with a clean `tmp_path` fixture through the same call returning **0** so the test distinguishes "6 on a leak" from "6 on everything". In-process via `_main`, so F3 and §7.3 are untouched. **§4.5** gains the handler as normative code (C7) and names the event and the observation, per round 3's standing rule. **§7.1**'s `EvalSplitLeak` row, **AC-1.13** and **§9**'s G5 row each gain the cross-reference; **Task 8**'s assertion 3 now states explicitly that it is the *static* half and points at Task 4 for the behavioural half — which is the asymmetry against `ProtectedPathError` that round 7 named, closed. |

#### Warnings — dispositions

| # | Substance | Disposition | Where |
|---|---|---|---|
| **C2** | §7.5's `eval_split --check-leak` row omits its required `<sidecar>` argument, which §9's row, AC-1.13 and Task 4 all supply — the identical defect class C3 (round 6) had just fixed for `--out`, in a table that is parametrized row-for-row. Also unstated: is the sidecar a required positional or does it have a committed default (§4.5's `--emit-lineage-contract` shows no sidecar arg, implying a default pattern)? And the row's expected code, "0 or 6", is two values where every other row states one | **ACCEPTED in all three parts — and the argument-shape question has a *third* answer, because both of the two offered would have broken a row this document already commits to** | §4.5, §7.1, §7.5, §9, AC-1.17, Task 4. The row now reads `eval_split --check-leak training/assemble/out/corpus_p25_sidecar.jsonl` and expects a single **0**. **The sidecar is `--check-leak`'s own required argument** — `g.add_argument("--check-leak", type=Path, dest="sidecar", metavar="SIDECAR")` — **not** a required bare positional (which `--emit` and `--emit-lineage-contract` would then also be demanded to supply, flipping their §7.5 rows from 0 to 64) and **not** a defaulted `nargs="?"` positional (which would push "did you give me a path?" into the handler, a second usage-error path `cli.py`'s single `error()` funnel exists to prevent, and would let G5 run against a path nobody typed). Omitting the path is `argparse`'s "expected one argument" → `error()` → `UsageError` → **64**, one funnel, no special case. *Writing that down exposed one genuinely unstated thing:* `--emit-lineage-contract` reads the sidecar too and its §7.5 row carries no path, so it resolves one from a new **`SIDECAR_RELPATH` / `default_sidecar_path()`** (mirroring `recipes.py`'s `RECIPES_RELPATH`/`default_recipes_path()`) — that is the "committed default" round 7 asked about, and `--check-leak` deliberately does **not** use it, because the gate must be runnable against a fixture (Task 4's C1 test) and must show its input at the call site. The **6** case is not deleted, it is **relocated to where a fixture-driven case belongs**: Task 4's C1 test. §9's G5 row keeps both codes, and the distinction is now stated — §9 is a *gate* table listing a gate's possible verdicts, §7.5 is a *behaviour* table stating one invocation's answer. |
| **C3** | The rule "`--out` is required with every `--emit-*` flag" is a **glob**, and one of the six emitter flags — `eval_split`'s — is spelled bare **`--emit`**, which the glob does not match. Compounding: Task 3 and §7.1's template both state their `out_required_for=(...)` tuple explicitly, but Task 4 (which owns `eval_split`) states none — so the one module whose flag name breaks the pattern is also the one with no tuple to catch a fixer's misreading. Applying the rule literally yields `out_required_for=("emit_lineage_contract",)`, and `eval_split --emit` with no `--out` then reaches the handler instead of exiting 64, contradicting §7.5's row for it | **ACCEPTED; the rule is restated over an enumerated set and every tuple is stated at its module** | §7.1 (three sites: the layout line, the template comment, the `--out` paragraph), §7.5, Task 4. The wording is now "**required with each of the six emitter flags**", never a pattern, and §7.1 gains a four-row table giving every module's tuple — `recipes.py` `("emit_histogram", "emit_receiver_alias_keys")`, `audit.py` `("emit_census", "emit_fingerprint")`, **`eval_split.py` `("emit", "emit_lineage_contract")`** with the bare `"emit"` called out as the exception, and `licenses.py`/`gap.py` `()`. **Task 4** states its tuple with the same call-out, matching Task 3. The template's comment now says *copy the tuple from the table, do not re-derive it by globbing*. |
| **C4** | §7.5's exit-64 row (added rev 7) has a **condition** in its command column rather than a literal invocation, so it expands 1 row → 6 test cases while every other row is 1-to-1 — yet AC-1.16 and Task 8 both claim the table is tested "row-for-row" / "parametrized like the rest", which is literally false for that row. Round 7 confirmed the cardinality **is** recoverable three independent ways, so this is an imprecise claim, not a functional gap | **ACCEPTED; both remedies applied, since they are cheap and complementary** | §7.5, AC-1.16, Task 8. (i) The row's command column now **enumerates the six commands literally** (`recipes --emit-histogram` · `recipes --emit-receiver-alias-keys` · `audit --emit-census` · `audit --emit-fingerprint` · `eval_split --emit` · `eval_split --emit-lineage-contract`), so the expansion is read rather than inferred, and the row flags itself as the one that is not 1-to-1. (ii) The resulting total is **stated as a number** at all three sites: **19 parametrized cases over 15 rows** — thirteen command rows × 1, plus six for the exit-64 row, plus zero for the `pytest -k ingest` row (which is AC-1.16's suite-level assertion, not a case) — with an `len(CASES) == 19` assertion in the test so a row added to §7.5 without a case fails loudly. Same discipline as the README/`EXIT_*` set-equality test. |

#### Suggestions — dispositions

All three accepted and applied; none deferred.

| # | Substance | Disposition | Where |
|---|---|---|---|
| **C5** | Task 8's hierarchy assertion 1 says "`X.__module__` equals the module §7.1's table names", but that table names **files** (`io.py`, `sources.py`) while `__module__` is a **dotted import path** (`ingest.io`, `ingest.sources`). Trivially derivable, but stated as an equality against a value that does not literally exist as written | **ACCEPTED** | Task 8, §7.1. Task 8's assertion 1 becomes a five-row table pairing each class with its expected `__module__` spelled out — `ingest.sources`, `ingest.recipes`, `ingest.audit`, `ingest.gap`, `ingest.io` (the import root is bare `ingest`, §7.2) — and §7.1's companion paragraph says the same in one clause. |
| **C6** | The `cli.py`-imports-nothing rule is stated at two scopes with inconsistent cross-referencing: §7.1's rule 2 does not mention §7.3(a) rule 4 that statically enforces it, while §7.1's matched-pair rule about `__main__.py`'s import ban **does** cite its §7.3(a) rule 3. And a code comment at `cli.py`'s declaration site scopes the rule to "no command module" (five files) where the rule text and §7.3(a) scope it package-wide | **ACCEPTED, both halves** | §7.1. Rule 2 gains the cross-reference **and** the reason it is stated (one of a matched pair citing its enforcement and the other not is how a reader concludes the second is only a convention). The code comment is widened to the package-wide scope — *"imports NOTHING from this package — not just no command module"* — with a note that narrow-then-broad is safe but two scopes for one rule is how round 6's hierarchy came apart. |
| **C7** | The `EvalSplitLeak` → 6 handler is the only exit-code mapping in the package existing solely as prose plus a trailing comment; every other mapping (`cli.run`, `IngestArgumentParser.parse_args`, the five-module `_main` template) has a normative code block. Since C1 adds the missing *test*, adding the missing *code* strengthens it | **ACCEPTED; and defining it surfaced one helper that had to be defined with it** | §4.5, §7.1, Task 4. §4.5 gains the normative `_check_leak` block (`try: assert_no_leak(rows) / except EvalSplitLeak: print(exc, file=sys.stderr); return 6 / return 0`) plus three notes on what is load-bearing in it: the `except` is what makes the exclusion *safe* rather than merely deliberate; `return 6` not `raise SystemExit(6)`, because `_main` is the only place `SystemExit` is raised (§7.1's template); stderr + exit code, matching every gate in §9. **Writing it exposed an undefined helper** — the block needs a sidecar reader and none was named anywhere, which is R4-B3's defect class exactly — so `load_sidecar_rows` is now **defined** in §4.5, added to §7.1's inventory and to Task 4's deliverables, with the one property that matters pinned: **its I/O failures raise `cli.IngestError` → 1, never `EvalSplitLeak`**, because 6 means "a leak was found" and a file that could not be read found nothing. §7.1's inventory also now records that `eval_split.py` declares **no** `cli.IngestError` subclass at all, which was true before and stated nowhere. |

#### §12 re-examination (round 7)

Round 7 raised no objection to items 1–15. **No item is added**: C1–C7 are all defects with fixes,
none a limitation being accepted. The file set stays at eleven (item 11) — C7 adds a *function*
(`load_sidecar_rows`) and C2 adds a constant plus a resolver (`SIDECAR_RELPATH`,
`default_sidecar_path()`), all three module-level names in `eval_split.py`, **no data file**. Item
14 (*"the package has no unified CLI"*) is untouched.

#### Termination of the adversarial loop

**No round 8 is planned, and this section records why rather than leaving it to be inferred.** The
blocking-finding series is **13 → 4 → 3 → 3 → 1 → 1 → 1**; rounds 4, 5, 6 and 7 reopened nothing;
rounds 6 and 7 found **no design defect at all**, only transcription and observation gaps. Round 7
assessed this as the terminal round on that basis and recommended dispatch after revision 8. The
convergence argument is not "we ran out of findings" — it is that the *kind* of finding changed
twice and has now bottomed out: rounds 1–3 found design defects, rounds 4–5 found plumbing and
missing detectors, rounds 6–7 found propagation and precision. A round 8 would be looking for the
next tier down, and there is no evidence a tier down exists. **This spec is now for a fixer, not for
another challenger.** If implementation surfaces a defect — which it may, and rounds 4 and 5 both
argued that day-one contact is a different reviewer than a reading is — that is a revision driven by
evidence from the code, not another adversarial pass over the prose.

---

## Overview

Build `training/ingest/` as a facts-only (license tier 0), fully offline, teacher-independent
admission ledger that (a) commits a 21-row source registry with mechanically verified license
tiers, (b) audits `coxswain.plr`'s hand-derived canonical tables against the plr-cookbook's
execution-verified API index and **blocks** downstream generation until every discrepancy is
adjudicated in writing, and (c) measures the existing corpus's coverage gap against
**pre-registered** thresholds that authorize or cancel Increments 2-4.

This is the exact scope the brainstorm's INVEST-gate resolution assigned to Increment 1
(`[REJECT] INVEST gate — S (Small) on the winner`): *"INCREMENT 1 = THE RUNNER-UP'S EXACT SCOPE
(sources.py registry + licenses.py + audit.py + gap.py; facts-only, tier 0, no code derivation,
no parsers beyond recipes.yml)."* It is a proper **prefix** of the winner: nothing built here is
discarded if the descend rule stops the plan at the end of Increment 1.

### Explicitly out of scope (named so this spec cannot creep back to the full architecture)

| Deferred to | What |
|---|---|
| **Increment 2** | `recon.py` — the AST recon pass over all 21 sources; the UNKNOWN-verb bucket over *extracted calls*; observed-value-format calibration against `floor_gen/value_formats.py` (ORTHOGONAL-6); admission arguments for the 20 repos, authored **on the recon evidence** (TRIAGE-2/TRIAGE-5). |
| **Increment 3** | `cookbook.py`'s `.qmd` parsers (recipe fences, `## Title {#anchor}` back-matching, ```` ```{python} ```` cells, `# <n>` annotation glosses, setup-cell labware bindings / UNIT-5); `route.py` (ROUTE-1/2/4/5, three-way + HOLD); the floor_gen matrix-diff; golden-fixture harvest (ORTHOGONAL-5). |
| **Increment 4** | `provenance.py`'s full F9 per-corpus-row schema; tier-1/tier-2 extraction into `overlay_gen`; G4 teacher NL variant generation (the only teacher-dependent stage — F8). |
| **Never (this phase)** | Any `overlay_gen`/`floor_gen` *integration*. Increment 1 **reads** their committed artifacts and **writes nothing** into either. |

### Non-negotiable inheritances

Every design choice below cites the brainstorm decision or FIXED constraint it satisfies. Nothing
in the brainstorm's Decision Log (ACCEPT/REJECT/MERGE/DEFER) or Problem Frame (F1-F8, H1-H6) is
re-litigated here.

- **F2** — `training/ingest/` lives under `training/`; imports `coxswain.plr.*`; nothing in
  `coxswain/`, `praxis.backend.*`, or a browser bundle imports it back.
- **F3** — pure stdlib + `coxswain.plr` + sibling `training/` packages. **No `subprocess`, no
  `import` of any third-party clone, no execution of any cloned file.** Clones are read-only text.
  Rev 2 makes this claim *provable* rather than asserted — see §7.3, which also records the one
  transitive edge that revision 1's scan silently missed.
- **F5** — every exclusion is a counted row with a recorded reason; nothing is silently dropped.
  Rev 2 adds four new counted buckets that revision 1 would have dropped: `unmapped_params`,
  `unmatched_cell_keys`, `unmapped_receiver`, and the three `no_backend_verb` findings. **Rev 3
  extends F5 from data to schema:** an undeclared *lineage key* (§4.5) and an undeclared *DOTTED
  receiver* (§3.3 rule 2) are now counted-and-failed rather than absorbed, which is the same
  discipline applied to the shape of the input instead of to its contents.
- **F6** — every generated artifact is byte-identical on re-run from the same inputs. No
  timestamps inside the deterministic payload (see §7.4, which fixes a live F6 hazard in
  `overlay_gen/out/mined_calls_smoke.json`'s top-level `generated_utc`).
- **F7** — the 21 clones live under `~/projects/repos/`, never vendored into praxis. Enforced by
  a registry validator, not by convention.
- **F8** — zero teacher calls. Increment 1 completes with the backend still blocked.
- **LICENSE-6** — Increment 1 delivers its full value if all 21 sources land at tier 0 (they
  currently would: see §2.6).

---

## 1. Acceptance Criteria

Each criterion is a command that exits 0 or a committed artifact that a reviewer can diff.

> **Every `python -m ingest.*` command below presumes AC-1.0.** Revision 1 assumed the module was
> importable; it is not, until `ingest*` is added to `packages.find` **and** the editable install
> is refreshed (C15).

**AC-1.0 (bootstrap)** After Task 1,
`uv run --package training python -c "import ingest, sys; sys.exit(0)"` exits 0 **from the repo
root**, and `uv run --package training python -m ingest --help` exits 0. Task 1's `packages.find`
edit is not sufficient on its own: setuptools writes a static editable finder, so the task also
runs `uv sync --reinstall-package training` and the gate is the two commands above, run from
`/home/marielle/projects/praxis`, not from `training/`.
*Rev 5 (R4-B2): the second command needs an `ingest/__main__.py` to exist, and revision 4 created
one in **Task 6** — five tasks after the AC that gates it, and after four other tasks whose own
gates invoke the CLI. `__main__.py` and `cli.py` are now **Task 1** deliverables (§7.1).
`python -m ingest` prints a signpost listing the five module commands and exits 0; it **does not
dispatch**, and `python -m ingest licenses --report` exits 1 naming the
`python -m ingest.licenses --report` form. Every other `python -m ingest.<module>` command in this
spec is a module entry point with its own `__main__` guard, never a subcommand of this one.*

**AC-1.1** `training/ingest/data/sources.json` contains exactly 21 rows (cookbook + the 20
repos from the research doc's §0+§2 union), loads through `ingest.sources.load_registry()`
without raising, and every row passes the ten structural invariants in §2.2. The
`admission_state` census is exactly **1 `ADMITTED`, 18 `PENDING_RECON`, 2 `REJECTED_PERMANENT`**.

**AC-1.2** `uv run --package training python -m ingest.licenses --report` writes
`training/ingest/out/license_report.json` and `training/ingest/out/SOURCES.md` and exits 0.
Every one of the 21 rows carries a `license_verdict` ∈ the closed enum of §2.4, an `observed_sha`
(or an explicit null with `NOT_CLONED`), a `license_tier`, a `tier_ceiling`, and an
`effective_tier` ∈ {0,1,2}. The report carries `license_rules_version` and
`license_rules_sha256` matching `versions.py` (§2.5).

**AC-1.3 (descend rule D1, pre-registered, three-way — C6)**
`uv run --package training python -m ingest.licenses --check-descend` exits:

| exit | condition | meaning |
|---|---|---|
| **0** | `tier1_plus_effective_count >= 4` | PROCEED |
| **5** | `tier1_plus_effective_count < 4` **and** `tier1_plus_effective_count + unresolvable_count >= 4` | **INCONCLUSIVE** — the unmeasured rows could still change the answer. Provision the missing clones and re-run. **Not a descend signal.** |
| **3** | `tier1_plus_effective_count < 4` **and** `tier1_plus_effective_count + unresolvable_count < 4` | **STOP** — a real licensing verdict, robust to every missing measurement |

All three counts are single top-level integer fields in the report; reading them is a `jq`, not an
analysis. *(Satisfies: `[REJECT] INVEST gate` DESCEND RULES — "after INCREMENT 1, if fewer than
four sources clear tier 1, STOP". The three-way split is the rev-2 fix for C6: revision 1 could
not tell a licensing verdict from an unprovisioned machine, and would have fired STOP — killing
Increments 2-4 — on any checkout without the clones.)*

> **Rev 3 (R2-B4):** exit 5 is no longer D1's private convention. §7.5 promotes it to a
> package-wide INCONCLUSIVE code with a per-command table, which is what removes the
> contradiction round 2 found between this AC and AC-1.15's gate.

**AC-1.4 (falsifiable classifier — C22, repaired R2-B3; count re-homed R4-B1)**
`ingest.recipes.load_recipes()` returns, **against the default cookbook path**, exactly
`data/token_histogram.json`'s `n_recipes` rows — **91** today. *Rev 5 (R4-B1): revision 4 stated
this as an unconditional `load_recipes()` invariant raising `RecipesError` for every path, which
made four of this spec's own synthetic fixtures unparseable (§3.1 tabulates them). The reader now
performs no count check at all; the count is a committed pin about the live cookbook, checked by
clause (2) below.* And `ingest.recipes.classify_api_token()`:
1. evaluates all five `TokenKind` predicates **independently** — each a **positive** pattern, with
   `OTHER` no longer the complement of the other four (§3.2) — and raises `RecipesError` unless
   exactly one is true. **Both failure branches are reachable by a direct unit call, and neither
   is reachable from the pipeline:** the **zero-hit** branch by calling
   `classify_api_token("")` directly; the **multi-hit** branch by monkeypatching `_PREDICATES`.
   Task 3's gate exercises both that way.
   *Rev 4 (R3-W1): revision 3 claimed the zero-hit branch was "reached by a real token — `""`,
   which is what a trailing comma in an `apis` field produces". That is **false**, and it is false
   because of revision 3's own second fix: `split_apis` raises `RecipesError` on any empty token
   **before** the classifier is ever called (§3.2), so no `recipes.yml` content can reach the
   branch. The consequence is worth stating rather than hiding: **for every producible input the
   exactly-one assertion is satisfied by construction.** That is the correct state of affairs for a
   provably disjoint, positively-defined predicate set — the assertion is a claim about the
   *implementation*, not about the input — and it is why both tests target the implementation
   directly. What C22/R2-B3 actually bought is real and unchanged: `OTHER` is no longer a
   catch-all, so a token matching no shape is a **loud** failure instead of a silent `OTHER`.*
2. reproduces `training/ingest/data/token_histogram.json` — the committed per-kind count **and
   `n_recipes`** over the current `recipes.yml` — exactly. This is a **regression pin**, not a
   pre-registered threshold: it is computed by the fixer and its purpose is to make a silent
   reclassification a red test. *Rev 5 (R4-B1): `n_recipes` is new in this file and it is the home
   of the "exactly 91" claim, which previously lived as a literal inside the reader. Keeping it
   here means the count is checked by the same exact comparison as everything else the emitter
   produces, and a truncated cookbook is a red test rather than an exception raised in the middle
   of an unrelated fixture.*
3. classifies **every** token of the current 91 recipes without raising. Round 3 verified this
   exhaustively against the live file: the four positive `OTHER` shapes are jointly exhaustive over
   every non-empty, dot-free, whitespace-free token, so **no live token raises** and this criterion
   holds today by exhaustion rather than by luck. *Rev 4 (R3-W1): revision 3 added "any token that
   raises is information to record, not a regression to route around" — a true policy attached to
   an empty set. It is kept as a **forward** rule for a future cookbook, and relabelled as such:
   if a later `recipes.yml` introduces a token that raises, that token is a finding about the
   tokenizer's shape vocabulary, and the fix is a new positive shape with its own disjointness
   argument, never a widened catch-all.*

**AC-1.5 (eval split — committed data is authoritative, C10)**
`training/ingest/data/eval_split.json` is committed, holds **paths only** (no titles), and
`uv run --package training pytest training/tests/test_ingest_eval_split.py` passes the **seven**
assertions 0–6 of §4.4 (rev 3 adds assertion 0, the commit-SHA pin — R2-B4d; **rev 6 adds
assertion 6**, the two committed-counter equalities — R5-W1) — including the
**monotonicity** invariant
`held_out_ever ∩ current_paths ⊆ held_out_paths`. No assertion in this suite treats a recomputed
list as authoritative over the committed one.

**AC-1.6 (audit census, machine-derived — C4)**
`uv run --package training python -m ingest.audit --report` writes
`training/ingest/out/audit_report.json` + `audit_findings.jsonl`. The report contains exactly
`len(PHANTOM_VERBS)` = **4** `phantom_verb` findings (`mix`, `blow_out`, `touch_tip`,
`dispense_to_waste`) and exactly `len(NO_BACKEND_VERBS)` = **3** `no_backend_verb` findings, where
both sets come from `data/experimental_partition.json` and **the loader raises `AuditError`
unless** their union equals
the live `{name for name, spec in TOOL_SCHEMA.items() if spec.experimental}` (currently 7) with
empty intersection (§5.3; rev 6, R5-S2 — the word "asserts" is avoided package-wide now that
§7.3(a) statically bans `ast.Assert` under `training/ingest/`). Every `phantom_verb` finding carries a `verdict` from the §5.3 enum, its
cookbook evidence tokens, and an `adjudicable_digest`.
The report also carries an **observed** `blocking_census` object — `{kind: count}` over the kinds
in `BLOCKING_KINDS` — and `test_ingest_audit_findings.py` asserts it equals the `census` object of
the committed **`training/ingest/data/blocking_census.json`** (§5.6d), which currently holds
`{"phantom_verb": 4, "surface_adjacent": 5, "receiver_drift": 0, "param_misattributed": 0}`
(derived in §5.4.1, emitted by `audit --emit-census`). Like `token_histogram.json` this is a
**regression pin, not a threshold**: no decision reads it, and its only job is to make R2-B1's
failure mode — a census asserted in prose that disagrees with the file — a red test instead of an
unsatisfiable gate.
*Rev 4 (R3-B2): revision 3 put the pin in a **test literal** while AC-1.7 required the **gate** to
read it. A gate binary cannot read a Python test file, `versions.py` had no census constant, and
`data/` had no slot — so `census_drift` was unimplementable, and any home a fixer improvised
(a dict hard-coded in `audit.py` about live cookbook data) would have been R2-B1's own
hand-listed-constant defect a second time. There is now exactly **one** source of truth, produced
by the same `--emit-*`/copy-and-review workflow as every other computed file: the gate reads the
file, the test compares the observation to the file, and the test holds **no literal of its own**.*
*(Satisfies: `[ACCEPT] ORTHOGONAL-2` — "specifically stress-tests the four recorded phantom
verbs … against the cookbook's Mix recipe". Revision 1 asserted "exactly four" against a table
where seven entries are `experimental=True` and the distinction lives only in a comment;
revision 2 fixed that and then asserted "seven blocking findings" against a cookbook that
produces nine.)*

**AC-1.7 (G2 blocking, PM-3, digest-bound — C3, census-complete R2-B1)**
`uv run --package training python -m ingest.audit --gate` exits **0** iff every finding with
`blocking: true` has an entry in `training/ingest/data/audit_adjudications.json` that satisfies
§5.5's completeness rule **and** whose `adjudicated_digest` equals the finding's current
`adjudicable_digest`; exits **2** when that condition fails, listing every failing `finding_id`
with a reason of `missing` | `incomplete` | `stale_digest` (printing both digests for the last).
There is no `--force`, no `--advisory`, no environment-variable bypass, and **no path flag** —
§5.5's test injection is Python-keyword-only for exactly this reason (R4-W5).

**Every code this gate can return, because "exits 2 otherwise" was never the whole story
(rev 5, R4-W3 / R4-W10).** Revision 4 wrote an unqualified *"exits 2 otherwise"* here while §7.5,
§9's G2 row and Task 6 all agreed the gate must exit **5** with the clone absent — R2-B4b's shape
recurring in the AC that owns the blocking gate, and the one place a fixer is most likely to read
and stop. The complete set, in §5.5's evaluation order:

| exit | condition |
|---|---|
| **5** | the cookbook clone is absent (`CookbookUnavailable`) — **never 0, never 2**: an audit that could not be run must not pass its gate, and must not report a blocking failure it did not measure (§7.5) |
| **1** | `data/blocking_census.json` is absent, unreadable, or fails its `BLOCKING_KINDS` loader invariant — a measurement error about a **committed in-repo** file, distinct from a census *mismatch*, which is advisory (R4-W10) |
| **2** | a blocking finding is `missing` / `incomplete` / `stale_digest` |
| **0** | all blocking findings adjudicated at their current digest — possibly with advisory `census_drift` lines printed |

**And one code that is not a gate answer at all (rev 6, R5-W2).** A malformed invocation — a typo,
a missing flag — returns **64** (`cli.EXIT_USAGE`) from the CLI layer *before* `gate()` runs. That
is new: until revision 6 `argparse`'s own `error()` path exited **2**, which is this AC's code for
*"a blocking finding is unadjudicated"* — so a typo would have reported contested canonical tables.
Exit 64 can never be confused with a row above because it is outside §9's 0–7 range entirely.

**And this AC's literal contract is observed end-to-end for the first time in rev 6 (R5-B1).**
*"`python -m ingest.audit --gate` exits N"* is a claim about the **command**, while every test that
checked it drove `audit.gate(...)` **in-process** — so the `if __name__ == "__main__":` block that
connects the two was, until this revision, untested. A fixer who omitted it from `audit.py` shipped
a blocking gate that exits 0 unconditionally with the whole suite green (§7.1). Task 8's
`test_ingest_entrypoints.py` now runs `runpy.run_module("ingest.audit", run_name="__main__")` with
`--gate` and the clone absent, and asserts `SystemExit(5)`.

Against the current `recipes.yml` this requires **nine** adjudications, enumerated with their
subjects in §5.4.1. The gate loads `data/blocking_census.json` (§5.6d) and prints one loud
`census_drift kind=<k> pinned=<n> observed=<m>` line per disagreeing kind, but **does not fail on
it** — the dangerous direction (a blocking finding *disappearing*, which would shrink the gate's
scope while it stayed green, since stale adjudications are warnings by §5.5) is owned by the
pinned test, where changing the file is a reviewed diff. Putting that authority in the gate
instead would make legitimate cookbook growth a hard failure, which is the
recomputation-as-authority inversion C10 rejected.

**Rev 4 (R3-B1): the census pin is load-bearing, not decorative, and this is where to say why.**
For `surface_adjacent` — 5 of the 9 blocking findings — the `adjudicable_digest` **cannot** go
stale under any canonical-table edit that leaves the finding in existence (§5.7's
table-sensitivity table derives this). The only detectable event for those five is
**disappearance**, and it has two causes with two different detectors: a canonical-table edit,
caught by **AC-1.14**; and a cookbook-side change (the recipe is removed upstream), which AC-1.14
cannot see at all. **The census pin is the sole detector of the second case**, which is why it
needed a real home (R3-B2) rather than a test literal, and why Task 6's drift test exercises
drift-*down* (R3-W3).

**AC-1.8 (no auto-patch, PM-3, decidable — C2)**
`uv run --package training pytest training/tests/test_ingest_never_patches_tables.py` passes all
three properties of §5.6: the single-writer AST property, the parametrized
`ProtectedPathError` refusals, and the byte-canary over the four canonical **tables**
(`tool_schema.py`, `param_namespace.py`, `ambiguity_matrix.json`, `miner.py` — not to be confused
with §5.7's five downstream **artifacts**) across a full pipeline run into a temp dir.

**AC-1.9 (G1 gate, PM-2; T2 authority corrected — W2)**
`uv run --package training python -m ingest.gap --gate` compares the computed report against the
thresholds **committed in `training/ingest/versions.py::GAP_THRESHOLDS`** (§6.4) and exits 0
(PROCEED to Increment 2), 4 (STOP, descend to floor_gen), **7** if T2's collapsed and strict
readings disagree on pass/fail (CONTESTED — neither PROCEED nor STOP; §6.4), or **1** if the T1
invariant does not reproduce (§6.4 — a measurement error, not a decision). `GAP_THRESHOLDS` is a
frozen mapping whose values are fixed by this spec and whose `GAP_THRESHOLDS_VERSION` must be
bumped in the same commit as any change to them.
*Rev 3 (W2): revision 2 resolved a collapsed/strict disagreement by "taking the STOP-side answer",
which — since `T2_collapsed ≥ T2_strict` always — silently installed `T2_strict`, the
provenance-leaking reading, as the gate authority. Exit 7 replaces that with an outcome that
authorizes nothing.*

**AC-1.10 (F6 determinism)**
`uv run --package training pytest training/tests/test_ingest_determinism.py` passes: each of the
five generated artifacts is produced twice into **two distinct temp dirs** and the sha256 of each
pair is equal. Temp-dir writes are legal by §5.6's construction; this AC and AC-1.8 are no longer
in contradiction.

**AC-1.11 (F3 purity, transitive — C14)**
`uv run --package training pytest training/tests/test_ingest_import_purity.py` passes all three
properties of §7.3: the **direct bans** (**four** AST-decidable rules over one walk — the banned
imports; zero `ast.Assert` nodes anywhere under `training/ingest/`, R4-W9; zero imports of a
command module from `ingest/__main__.py`, rev 6 / R5-W3; and zero imports of *any* sibling ingest
module from `ingest/cli.py`, rev 7 / C1, which is what keeps §7.1's exception hierarchy sound),
the **transitive** closure check against
`data/import_closure_allowlist.json`, and the runtime `subprocess.run`-patched pipeline run. Three
*properties*, **four** *rules inside the first property* — the counts are independent and both are
stated because revision 5 grew the second one without saying so, and revision 7 grew it again.

**AC-1.12 (LICENSE-4, live deadline — C23)** The cookbook row carries a non-empty
`license_request_issue_url` **or** a `license_request_due` that parses as `YYYY-MM-DD` **and is
not in the past**. `test_ingest_registry.py` asserts this, so on 2026-09-11 with no issue filed
the suite goes **red**. Extending the date requires an append-only
`license_request_due_extensions` entry (`{from, to, reason}`, `to - from ≤ 30 days`).
*(Satisfies: `[ACCEPT] LICENSE-3` — "written into the plan with a date because unwritten human
actions never happen". Revision 1's `due ≤ 2026-09-10` was satisfied *forever* by any past date,
which is the opposite of a deadline.)*

**AC-1.13 (G5 eval-leak gate, live — C11)**
`uv run --package training python -m ingest.eval_split --check-leak training/assemble/out/corpus_p25_sidecar.jsonl`
exits **0** today and exits **6** on any leak, per §4.5. The command is in §9's gate table and in
Task 8's suite, so it runs on every CI pass from Increment 1 onward — the obligation is owned by
a gate, not by a docstring.
*Rev 8 (C1): the second half of that sentence — "exits **6** on any leak" — was asserted in three
places (§7.1's hierarchy table, §4.5, here) and **tested nowhere**, because every `--check-leak`
invocation in this document used the clean committed sidecar and expected 0. It now has a test:
Task 4 writes the type-2 leak fixture to a `tmp_path` sidecar and asserts
`eval_split._main(["--check-leak", str(fixture)]) == 6`. This AC is satisfied only when **both**
halves run — the 0 against the committed 188-row sidecar and the 6 against the fixture — and the
`assert_no_leak` → `except EvalSplitLeak` → `return 6` handler that makes the second half possible
is normative code in §4.5.*

**AC-1.14 (canonical-table downstream invalidation — C13, bound to artifacts W1)**
`uv run --package training pytest training/tests/test_ingest_downstream_fingerprint.py` passes
**two** assertions: (i) the live canonical-tables fingerprint (§5.7) equals
`data/canonical_tables_fingerprint.json`'s `fingerprint`; (ii) the live sha256 of each of the
**five** downstream artifacts named in that file's `built_artifacts` map equals its committed
value. Editing `tool_schema.py` or `param_namespace.py` turns (i) red; regenerating any downstream
artifact without re-running the fingerprint turns (ii) red. The assertion message is the
four-stage, five-file regeneration checklist.
*Rev 3 (W1): with only (i), the tripwire was silenced by editing one hex string. With (ii) it is
still silenceable — nothing is — but silencing requires asserting, in a reviewable diff, that
five specific committed files were built under a table they were not.*

**AC-1.15 (clone verification, per-row — C25/C28; two-outcome R2-B4c)**
`uv run --package training python -m ingest.licenses --verify-clones` checks **each of the 21**
registry rows for an existing `<clone_path>/.git` whose resolved HEAD equals `pinned_sha`, prints
every failing `source_id` with which of the two failures it hit, and exits:

| exit | condition |
|---|---|
| **0** | all 21 present and at `pinned_sha` |
| **5** | every failure is an **absent** clone (measurement not taken — consistent with AC-1.3's exit 5 and §7.5's package-wide convention) |
| **1** | at least one clone is **present but at the wrong SHA** (a measured disagreement, and a real error regardless of what else is missing) |

`--require-all` turns exit 5 into exit 1. Task 0 uses it, because there provisioning *is* the
deliverable; G0b in §9 does not, because a CI checkout without `~/projects/repos/` is not a
defect. No command in this spec counts directories.
*Rev 3 (R2-B4c): revision 2's unconditional exit 1 contradicted AC-1.3's whole point — a machine
without the clones would pass D1's INCONCLUSIVE branch and then hard-fail the gate immediately
above it in the same table.*

**AC-1.16 (clone-absent behaviour, defined per command — R2-B4b)**
On a checkout with **no** `~/projects/repos/plr-cookbook`, every command in §7.5's table exits
with the code that table states, and
`uv run --package training pytest training/tests/ -k ingest` reports **zero failures and zero
errors**: tests that require the clone `skip` with a reason naming the missing path, and every
test that does not require it still runs. A test asserts this directly by monkeypatching
`default_recipes_path()` to a nonexistent path and driving each subcommand.
*Live state 2026-08-27: 19 of the 21 registry clones are absent on this machine, so this is the
common case, not the edge case.*
*Rev 7 (C3): every emitter row of §7.5's table is invoked with `--out <tmp_path>`, as the table
now spells it, and the table's final row — the same commands with `--out` **omitted** → **64** —
is driven too. That row is the only one whose expected code is identical in both of the table's
columns, and asserting it under this AC (the clone-absent one) is what pins the ordering: `--out`
is checked in `parse_args`, before any handler runs, so the missing clone never gets a say.*
*Rev 8 (C4): "every command in §7.5's table" is **19 parametrized cases over 15 rows**, not 15 —
thirteen command rows contribute one case each, the `--out`-omitted row expands to **six** (one per
emitter command, now enumerated in the row itself), and the `pytest -k ingest` row is this AC's own
suite-level assertion rather than a case. The count is stated because "row-for-row" stopped being
literally true when revision 7 added a row that is a condition over six commands; assert
`len(CASES) == 19` so a row added without a case fails loudly.*
*Rev 8 (C2): the `eval_split --check-leak` row now carries the sidecar path the flag itself requires
(`--check-leak PATH`, §4.5) and a single expected code (**0**), so it is invocable and
parametrizable like every other row.*

**AC-1.17 (lineage field contract — W3)**
`uv run --package training python -m ingest.eval_split --check-leak
training/assemble/out/corpus_p25_sidecar.jsonl` (the path is `--check-leak`'s own required
argument, rev 8 C2) additionally
asserts that the union of `lineage` keys over all sidecar rows is a **subset** of
`data/lineage_contract.json`'s `known_keys ∪ reserved_cookbook_keys`, and exits **6** with reason
`contract_violation` naming every unknown key otherwise. This is what makes G5 non-vacuous today
(§4.5): it has a live assertion over all 188 committed rows even though no row can currently leak.

---

## 2. `sources.py` + `licenses.py` — the admission ledger

### 2.1 The `SourceRegistry` row shape

Registry is **committed data + a loud loader**, mirroring the house pattern already established
by `training/floor_gen/matrix.py` ↔ `training/floor_gen/data/ambiguity_matrix.json` (data file,
`load_*()` that validates against the live canonical tables, `MatrixError` raised loudly).

`training/ingest/data/sources.json`:

```jsonc
{
  "registry_version": "2",
  "sources": [
    {
      "source_id":           "chory-lab__plr-cookbook",   // stable slug: <owner>__<repo>
      "repo_url":            "https://github.com/chory-lab/plr-cookbook",
      "clone_path":          "~/projects/repos/plr-cookbook",
      "pinned_sha":          "<40 lowercase hex>",
      "genre":               "cookbook",                  // TRIAGE-3, closed enum
      "extractor_kind":      "recipes_yml",               // OBSERVED property (C17)
      "admission_state":     "admitted",                  // DECISION, closed enum (C17)
      "admission_argument":  "Only execution-verified, human-task-phrased, machine-indexed source in the pool (H1); it is simultaneously the drift-audit input (ORTHOGONAL-2), the out-of-surface anchor supply (H2), and the eval-split source (ORTHOGONAL-1).",
      "rejection_reason":    "",
      "tier_ceiling":        2,                           // NON-license cap only (C16)
      "tier_ceiling_reason": "",
      "license_scan_dirs":   ["cookbook"],                // C21/C24: extra roots to scan
      "stars":               0,
      "last_push":           "2026-08-26",
      "license_request_issue_url": "",
      "license_request_due": "2026-09-10",
      "license_request_due_extensions": [],
      "notes":               ""
    }
  ]
}
```

Python surface, `training/ingest/sources.py`:

```python
class Genre(str, Enum):            # TRIAGE-3: genre is an EXPLANATION, never a score
    COOKBOOK = "cookbook"
    WET_LAB_PROTOCOL = "wet_lab_protocol"
    ORCHESTRATION_PLATFORM = "orchestration_platform"
    HARDWARE_BACKEND = "hardware_backend"
    LABWARE_DATA = "labware_data"
    PROTOCOL_FORMAT = "protocol_format"
    NOVELTY_DEMO = "novelty_demo"
    LLM_ADJACENT = "llm_adjacent"
    UNCLEAR = "unclear"

class ExtractorKind(str, Enum):    # OBSERVED extractability, independent of admission (C17)
    RECIPES_YML = "recipes_yml"
    QMD = "qmd"
    NOTEBOOK = "notebook"
    PYTHON = "python"
    NONE = "none"                  # no machine-extractable text unit AT ALL

class AdmissionState(str, Enum):   # the DECISION axis (C17)
    ADMITTED = "admitted"
    PENDING_RECON = "pending_recon"        # TRIAGE-5 default-out, resolvable by Increment 2
    REJECTED_PERMANENT = "rejected_permanent"   # H6 contamination class; Increment 2 may not flip

@dataclass(frozen=True)
class SourceRow:
    source_id: str
    repo_url: str
    clone_path: str
    pinned_sha: str
    genre: Genre
    extractor_kind: ExtractorKind
    admission_state: AdmissionState
    admission_argument: str        # non-empty iff ADMITTED
    rejection_reason: str          # non-empty iff not ADMITTED
    tier_ceiling: int              # 0 | 1 | 2  -- NON-license cap only
    tier_ceiling_reason: str
    license_scan_dirs: tuple[str, ...] = ()
    stars: int = 0
    last_push: str = ""            # YYYY-MM-DD
    license_request_issue_url: str = ""
    license_request_due: str = ""
    license_request_due_extensions: tuple[Mapping[str, str], ...] = ()
    notes: str = ""

#: rev 7 (C1): the base is `cli.IngestError`, NOT ValueError -- §7.1's hierarchy table
#: is normative and this is one of its five per-module rows. `cli.py` declares the roots
#: and imports nothing from this package, so `from . import cli` here does not cycle.
class RegistryError(cli.IngestError): ...      # -> exit 1 via cli.run

def load_registry(path: Path | None = None) -> tuple[SourceRow, ...]: ...
def registry_path() -> Path: ...
def by_id(source_id: str) -> SourceRow: ...
```

### 2.2 Load-time invariants

`load_registry()` raises `RegistryError` (loudly, matching `MatrixError`'s style) on any of:

| # | Invariant | Constraint it enforces |
|---|---|---|
| I1 | exactly 21 rows; `source_id` unique | brainstorm's "21 rows (cookbook + 20 repos)" |
| I2 | `pinned_sha` matches `^[0-9a-f]{40}$` | LICENSE-1 "pinned SHA" |
| I3 | `clone_path` starts with `~/projects/repos/` **and** its `expanduser().resolve()` is not under the praxis repo root | **F7** |
| I4 | `admission_state is ADMITTED` ⟺ `admission_argument != ""`; `admission_state != ADMITTED` ⟺ `rejection_reason != ""` | **TRIAGE-5** reject-by-default, on a closed enum instead of a null/empty overload (**C17**) |
| I5 | `admission_state is ADMITTED` ⇒ `extractor_kind is not NONE` (one direction only) | you cannot admit a source you cannot extract from — but a *pending* source keeps its observed extractability (**C17**) |
| I6 | `tier_ceiling in (0,1,2)`; `tier_ceiling < 2` ⇒ `tier_ceiling_reason` starts with one of the **closed** prefix set `CEILING_PREFIXES = ("contamination:", "vendored:", "consent:", "stale:", "duplicate:")` **and** contains neither the casefolded substring `licen` nor a word-boundary match of `mit\|bsd\|gpl\|agpl\|lgpl\|apache\|spdx\|copyleft\|proprietary\|unlicensed` | three-axis separation: the cap is *stated*, and a **license** reason in the ceiling field is a load error, which is what stops the AGPL cap being counted twice (**C16**). **W13:** revision 2's open `other:` prefix left the smuggling path C16 closed wide open — any license rationale prefixed `other:` passed. `CEILING_PREFIXES` lives in `sources.py`, not in a data file, so adding a prefix is a code diff, exactly as `VERDICT_TIER` is (**C7**). The word-boundary form is required because `mit`/`bsd` as bare substrings match `permit`, `submit`, `limit`, `transmit` |
| I7 | `last_push` parses as `YYYY-MM-DD` | maintenance-risk tiebreak only, never a primary key (`[REJECT] TRIAGE-1`) |
| I8 | the cookbook row satisfies AC-1.12's live-deadline rule | **LICENSE-4** (**C23**) |
| I9 | every `license_scan_dirs` entry is a relative path with no `..` segment | **C21/C24**; a scan dir must stay inside the clone |
| I10 | `license_request_due_extensions` is append-only-shaped: each entry has `{from, to, reason}`, `to > from`, `to - from ≤ 30 days`, and entries are chronologically non-overlapping | **C23** — slipping a deadline is visible |

### 2.3 Admission state at Increment 1 — a deliberate decision

**Exactly one row (the cookbook) is `ADMITTED` at the end of Increment 1. Eighteen rows are
`PENDING_RECON` with `rejection_reason` = `"not yet admitted: awaiting Increment 2 recon
measurement (TRIAGE-2/TRIAGE-4)"`. Two rows are `REJECTED_PERMANENT`.**

Rationale, and it is load-bearing: `[ACCEPT] TRIAGE-2 + TRIAGE-4 + TRIAGE-3 + TRIAGE-5` makes
triage *"an offline MEASUREMENT rather than a judgment"*, and the measurement is `recon.py`,
which is Increment 2. Authoring 20 admission arguments now, before the recon counts exist,
would be exactly the vibe-based triage that decision rejected, dressed up as a data file.
Reject-by-default is not a placeholder here — it is the correct terminal state of Increment 1.

**What changed in rev 2 (C17):** revision 1 coupled `extractor_kind is NONE` to
`admission_argument is None`, which forced all 20 non-cookbook rows to record `extractor_kind:
"none"` — erasing extractability facts the research doc already establishes (most of these repos
are plainly `python`), and guaranteeing Increment 2 would have to rewrite two coupled fields in
lockstep. Extractability is an **observed property of the source**; admission is a **decision
about the source**. They are now independent, with only the one-directional I5 linking them.

Two rows are `REJECTED_PERMANENT` for a **different and permanent** reason, per `H6` and
`[REJECT] NL-5`, and their `rejection_reason` says so verbatim:

- `GreenTilden__oolitic-plr` — "H6 contamination class: LLM-for-PLR-codegen project; mining it
  risks training on another model's output. Distinct from 'low activity'."
- `vanallenlab__agentic-ai-codebase` — "H6 contamination class: LLM-agent-to-lab-automation
  bridge; its PLR call sites are prompt scaffolding, not protocol code."

Both also carry `tier_ceiling: 0` with `tier_ceiling_reason: "contamination: H6 …"` so that even
a permissive LICENSE cannot promote them.

### 2.4 The 21 rows, with their stated ceilings

Cookbook (1): `chory-lab/plr-cookbook` — `tier_ceiling: 2`, `license_scan_dirs: ["cookbook"]`.

The 20 repos are the deduplicated union of the research doc's §0 table (11 unique after removing
the two rows that duplicate §2) and its §2 table (9 unique). **`tier_ceiling` is stated for every
row** (C16): it is 2 unless a *non-license* cap applies, and only the two H6 rows carry a cap.

| # | source_id | genre | stars | tier_ceiling | notes |
|---|---|---|---|---|---|
| 1 | `deepmodeling__Uni-Lab-OS` | orchestration_platform | 175 | 2 | TRIAGE-4 layer distance 1-2: call sites are registry adapters |
| 2 | `Cheshire-Labs__orca` | orchestration_platform | 24 | 2 | |
| 3 | `Cheshire-Labs__swarm-client` | orchestration_platform | 0 | 2 | |
| 4 | `Cheshire-Labs__cheshire-drivers` | hardware_backend | 0 | **2** | AGPL — the cap is applied **once**, on the license axis (`COPYLEFT ⇒ license_tier 0`). Its ceiling is 2 precisely so the AGPL cap is not double-counted (**C16**) |
| 5 | `Pioneer-Research-Labs__ngs_library_prep` | wet_lab_protocol | 12 | 2 | most protocol-real source in the pool (E's forcing beat) |
| 6 | `SLKS99__PyFluent` | hardware_backend | 12 | 2 | |
| 7 | `qte77__so101-biolab-automation` | wet_lab_protocol | 3 | 2 | |
| 8 | `ivoryos-ai__IvoryOS-PyLabRobot-Integration` | orchestration_platform | 0 | 2 | |
| 9 | `aicell-lab__hamilton-control` | hardware_backend | 0 | 2 | |
| 10 | `GreenTilden__oolitic-plr` | llm_adjacent | 0 | **0** | `REJECTED_PERMANENT`, H6 |
| 11 | `vanallenlab__agentic-ai-codebase` | llm_adjacent | 2 | **0** | `REJECTED_PERMANENT`, H6 |
| 12 | `Koeng101__pylabrobot-protobuf` | protocol_format | 0 | 2 | |
| 13 | `Tetsuwan-Scientific__plr-sandbox` | unclear | 0 | 2 | |
| 14 | `jt05610__python-graphmix` | protocol_format | 2 | 2 | stale 2024-06 |
| 15 | `norle__plr-gui` | orchestration_platform | 0 | 2 | |
| 16 | `rickwierenga__plr-game-of-life` | novelty_demo | 1 | 2 | |
| 17 | `rickwierenga__lwdb` | labware_data | 0 | 2 | ORTHOGONAL-4: plausible-but-refusable request supply |
| 18 | `LuHesketh__GSOC-2023-LabOP` | protocol_format | 0 | 2 | |
| 19 | `OrthoDim__Cereal-Delusion` | unclear | 0 | 2 | |
| 20 | `evnkm__basic_viz` | unclear | 0 | 2 | |

`external/pylabrobot` is **not** a registry row: it is vendored read-only ground truth (F7) and
already an `overlay_gen` source root. The incidental standalone clone at
`~/projects/repos/pylabrobot` is likewise **not** a row — which is exactly why Task 0's gate can
never be a directory count (**C25/C28**).

### 2.5 `licenses.py` — mechanical verification

```python
class LicenseTier(IntEnum):
    FACTS_ONLY = 0     # API names, verb frequencies, param names, task vocabulary, counts
    STRUCTURE  = 1     # normalized MinedCall rows: literal values, symbolic refs, ordering
    EXPRESSION = 2     # verbatim harvested NL used as anchor utterances

class LicenseVerdict(str, Enum):
    PERMISSIVE   = "permissive"     # MIT / BSD-2 / BSD-3 / Apache-2.0
    COPYLEFT     = "copyleft"       # (A)GPL / LGPL — HARD tier-0 cap
    NONE         = "none"           # no license file at the pinned SHA, in any scanned dir
    AMBIGUOUS    = "ambiguous"      # file present; 0 or >1 detection rules matched
    SHA_MISMATCH = "sha_mismatch"   # clone is not at pinned_sha        -> UNRESOLVABLE
    NOT_CLONED   = "not_cloned"     # clone_path absent                 -> UNRESOLVABLE

#: C6: the measurement-validity axis, orthogonal to the license axis.
UNRESOLVABLE: Final[frozenset[LicenseVerdict]] = frozenset(
    {LicenseVerdict.SHA_MISMATCH, LicenseVerdict.NOT_CLONED}
)

#: C7: verdict -> tier lives in CODE. The data file supplies DETECTION only, so a
#: rule edit can never grant a tier.
VERDICT_TIER: Final[Mapping[LicenseVerdict, int]] = MappingProxyType({
    LicenseVerdict.PERMISSIVE: 2, LicenseVerdict.COPYLEFT: 0, LicenseVerdict.NONE: 0,
    LicenseVerdict.AMBIGUOUS: 0, LicenseVerdict.SHA_MISMATCH: 0, LicenseVerdict.NOT_CLONED: 0,
})

@dataclass(frozen=True)
class LicenseFinding:
    source_id: str
    pinned_sha: str
    observed_sha: str | None
    license_path: str | None        # clone-relative, e.g. "LICENSE" or "cookbook/LICENSE"
    license_sha256: str | None
    spdx_id: str | None
    verdict: LicenseVerdict
    license_tier: int               # VERDICT_TIER[verdict]  -- the pure license axis
    tier_ceiling: int               # the registry row's NON-license cap
    effective_tier: int             # min(license_tier, tier_ceiling)
    unresolvable: bool              # verdict in UNRESOLVABLE   (C6)
    shallow: bool | None            # .git/shallow present; None iff clone absent  (R2-B4d)
    reason: str                     # human-readable, always non-empty

def verify(row: SourceRow) -> LicenseFinding: ...
def verify_all() -> tuple[LicenseFinding, ...]: ...
def write_report(findings, out_dir: Path) -> Path: ...          # writes via ingest.io (§5.6)
def write_sources_manifest(findings, out_dir: Path) -> Path: ...  # LICENSE-5
def check_descend(findings) -> tuple[int, int, int]: ...        # AC-1.3: (exit, effective, unresolvable)
def verify_clones(rows) -> tuple[str, ...]: ...                 # AC-1.15: failing source_ids
```

**Detection is substring-based and deliberately not fuzzy.** `training/ingest/data/license_rules.json`
holds `{"license_rules_version": "1", "rules": [{spdx_id, all_of, none_of, verdict,
added_in_version, justification}]}`. A license file is normalized (collapse all whitespace runs
to one space, casefold) and matched against every rule. **0 matches or >1 match ⇒ `AMBIGUOUS` ⇒
tier 0.** Minimum rule set (all `added_in_version: "1"`):

| spdx_id | `all_of` (normalized, casefolded) | `none_of` | verdict |
|---|---|---|---|
| MIT | `permission is hereby granted, free of charge`, `the software is provided "as is"` | | permissive |
| BSD-3-Clause | `redistributions of source code must retain`, `neither the name of` | | permissive |
| BSD-2-Clause | `redistributions of source code must retain` | `neither the name of` | permissive |
| Apache-2.0 | `apache license`, `version 2.0, january 2004` | | permissive |
| AGPL-3.0-only | `gnu affero general public license` | | copyleft |
| GPL-3.0-only | `gnu general public license`, `version 3` | `affero`, `lesser` | copyleft |
| GPL-2.0-only | `gnu general public license`, `version 2` | `affero`, `lesser` | copyleft |
| LGPL-3.0-only | `gnu lesser general public license` | | copyleft |

**Pre-registration of the rules, mirroring `GAP_THRESHOLDS` (C7).** D1 is the *first* gate to run
and the highest-consequence one — it can kill Increments 2-4 — yet revision 1 gave the file that
decides it no version, no hash pin, and no record in the report. A single added ISC rule after
seeing a STOP would have flipped D1 invisibly. Rev 2:

1. `versions.py` pins `LICENSE_RULES_VERSION: Final[str] = "1"` and
   `LICENSE_RULES_SHA256: Final[str] = "<hex of the committed file's bytes>"`.
2. `load_license_rules()` raises `RegistryError` if the file's hash or embedded version
   disagrees — so editing the rules without bumping both constants fails the suite.
3. `license_report.json` records `license_rules_version`, `license_rules_sha256`, and
   `rules_added_since_v1` (a list of `{spdx_id, added_in_version, justification}`), so a reader
   sees post-hoc additions without reading git history.
4. **Task ordering discipline:** the commit adding `license_rules.json` must precede the first
   commit that runs `--check-descend` against real clones (checked by the reviewer, as for
   `GAP_THRESHOLDS`).
5. Tier assignment is `VERDICT_TIER` in code; the data file cannot express a tier.

**Where the license file is looked for (C21/C24).** Candidate filenames: `LICENSE`, `LICENSE.md`,
`LICENSE.txt`, `LICENCE`, `LICENCE.md`, `LICENCE.txt`, `COPYING`, `COPYING.md`. Candidate
directories: the clone root **plus each entry of the row's `license_scan_dirs`**. Revision 1
scanned the root only — but the cookbook clone's root holds just `.gitignore`, `.github/` and
`cookbook/`, and its README/SPEC/.gitignore all live under `cookbook/`, so a maintainer
responding to Task 9 would most plausibly add `cookbook/LICENSE`, which revision 1 would have
reported as `NONE` at tier 0 permanently. If a license file is found in more than one scanned
directory with **differing sha256** ⇒ `AMBIGUOUS`; identical bytes in two locations resolve to
the root-most path. `license_path` records which file was used. (A *nested* LICENSE deeper than a
declared scan dir still governs a vendored subtree and is not scanned.)

**SHA verification without `subprocess` (F3).** `licenses.py` reads `<clone>/.git/HEAD`; if it
holds a 40-hex SHA (detached), that is `observed_sha`; if it holds `ref: refs/heads/<x>`,
resolve via `<clone>/.git/refs/heads/<x>`, falling back to a line-scan of
`<clone>/.git/packed-refs`. `observed_sha != pinned_sha` ⇒ `SHA_MISMATCH` ⇒ **unresolvable**,
tier 0, and a loud line in the report. No `git` invocation anywhere in `training/ingest/`.

> **Known hazard, stated so a fixer does not rediscover it:** both existing clones under
> `~/projects/repos/` are **shallow** (`.git/shallow` present). A shallow clone contains only
> the tip commit, so `pinned_sha` must be the SHA the clone actually resolves to, recorded at
> first clone; it cannot be an arbitrary historical SHA. Task 0 records it; a later re-clone
> landing on a different SHA is a *registry edit with a recorded reason*, never a silent update.
>
> **Rev 3 (R2-B4d) — the shallowness is measured and reported, not just noted.** `verify()` sets
> `shallow: true` when `<clone>/.git/shallow` exists, `false` when the clone is present without
> it, and `null` when the clone is absent; `license_report.json` carries the field per row and
> `--verify-clones` prints it. That matters because the cookbook clone is shallow **and tracking
> `main`**, so its working tree can move under the pipeline on any re-clone. The determinism
> consequence is handled where it bites — §4.4's assertion ordering — not here.

### 2.6 `license_report.json` and what D1 actually counts

```jsonc
{
  "registry_version": "2",
  "ingest_version": "0.1.0",
  "license_rules_version": "1",
  "license_rules_sha256": "<hex>",
  "rules_added_since_v1": [],
  "counts": {"by_verdict": {...}, "by_license_tier": {"0": 0, "1": 0, "2": 0},
             "by_effective_tier": {"0": 0, "1": 0, "2": 0}},
  "tier1_plus_license_count":   0,   // license axis alone, ceiling NOT applied
  "tier1_plus_effective_count": 0,   // ceiling applied  <- D1 READS THIS
  "unresolvable_count":         0,   // NOT_CLONED + SHA_MISMATCH  (C6)
  "descend_rule_D1": {
    "threshold": 4,
    "decision": "PROCEED | STOP | INCONCLUSIVE",
    "exit_code": 0,
    "rule": "PROCEED iff tier1_plus_effective_count >= 4; INCONCLUSIVE (exit 5) iff below threshold but tier1_plus_effective_count + unresolvable_count >= 4; else STOP (exit 3).",
    "unresolvable_source_ids": []
  },
  "findings": [ /* LicenseFinding, sorted by source_id */ ]
}
```

**Which count D1 reads, restated correctly (C16).** Revision 1 said D1 read "the pure license
axis, ceiling applied, admission ignored" — which is self-contradictory, because the two H6 rows'
`tier_ceiling: 0` is a *contamination* (admission-flavoured) cap that `effective_tier` applies.
The correct statement:

> D1 counts rows that **could carry tier-≥1 material into a later increment**. Both the license
> verdict and the non-license ceiling apply, because a contamination-capped row cannot carry
> material whatever its licence says. What D1 ignores is **admission** — the recon-measured
> argument — and only because no row can be admitted before Increment 2, so an admission-aware
> count would be ≤ 1 by construction and would fire STOP on every possible outcome.

Both counts are reported so a reader can see the difference the ceilings make.

**Expected value today, disclosed:** the cookbook has **no LICENSE file at repo root** (verified
2026-08-27: the clone root contains only `.gitignore`, `.github/`, and `cookbook/`) ⇒ `NONE` ⇒
tier 0. `cheshire-drivers` is AGPL ⇒ `COPYLEFT` ⇒ license tier 0 (its ceiling stays 2). The
remaining 18 are unmeasured **and, on a machine without the clones, unresolvable** — which is
exactly why AC-1.3 has an exit 5. **If the D1 gate fires a genuine STOP (exit 3), that is the
plan working, not failing** — it is PM-1's warning sign detected, and `LICENSE-6` guarantees the
delivered value (the drift audit, the surface-expansion name ranking, the gap report, the eval
split) survives it intact.

`SOURCES.md` (LICENSE-5) is generated, never hand-edited, with a `<!-- GENERATED … do not edit -->`
banner and a test asserting regeneration is byte-identical. At Increment 1 it is generated from
the license report rather than from provenance rows (there are no corpus rows yet) — a
deliberate narrowing of LICENSE-5, recorded here so Increment 4 knows to widen it.

### 2.7 The Increment 1 → Increment 2 field boundary (C17, and the brief's C26 as best reconstructed)

Increment 2's recon pass owns exactly these registry mutations, and no others:

| Field | May Increment 2 change it? | Rule |
|---|---|---|
| `admission_state` | **Yes**, `PENDING_RECON → ADMITTED` or `→ REJECTED_PERMANENT` only | `REJECTED_PERMANENT` is terminal; Increment 2 may not un-reject an H6 row |
| `admission_argument` / `rejection_reason` | **Yes**, in the same commit as `admission_state` | I4 keeps them consistent |
| `extractor_kind` | **No** | It is an observed property recorded at Increment 1; a correction is a registry edit with its own reason, not a recon output |
| `genre` | **No** | TRIAGE-3: genre explains a measurement, it is not produced by one |
| `tier_ceiling` / `tier_ceiling_reason` | **No** | Non-license caps are policy, not measurement |
| `pinned_sha` | **No** | A re-clone is its own recorded registry edit (§2.5's hazard note) |
| `registry_version` | **Yes**, bumped whenever any row changes | |

`test_ingest_registry.py` cannot enforce a future increment's discipline, and this spec does not
pretend otherwise — the table is a boundary statement for Increment 2's spec to inherit, which is
the correct scope for a boundary. What *is* enforced now is that the fields are structurally
independent, so honouring the boundary is possible; revision 1's coupling made it impossible.

### 2.8 LICENSE-4's deadline mechanics (C23)

```python
def license_request_ok(row: SourceRow, today: date) -> bool:
    if row.license_request_issue_url:
        return row.license_request_issue_url.startswith("https://github.com/")
    if not row.license_request_due:
        return False
    return date.fromisoformat(row.license_request_due) >= today
```

`today` is injected by the test (`date.today()`), never read inside any writer — so this
introduces **no** non-determinism into any generated artifact (F6 intact). The test is
deliberately time-dependent: a deadline that cannot expire is not a deadline, and revision 1's
`due <= 2026-09-10` was satisfied permanently by any past date. On 2026-09-11 with no issue
filed, `test_ingest_registry.py` goes red and the remedy is either Task 9 or a reviewed
extension entry.

---

## 3. `recipes.py` — the only parser in Increment 1

`cookbook/recipes.yml` is a **YAML data file, not code** (`[ACCEPT] Extraction units` — UNIT-3:
*"the single highest-value/lowest-cost artifact in the entire pool and it is not code"*), so
parsing it creates no derivative work and is tier-0-legal for any license verdict.

### 3.1 The reader — exact grammar, and why PyYAML is not an option (C5)

```python
@dataclass(frozen=True)
class Recipe:
    title: str          # tier-2 expression — NEVER written to any ingest OUTPUT (see below)
    path: str           # "part1/04_pipetting.qmd#mix"  <- the tier-0 identifier
    chapter: int        # 1..18
    line_no: int        # file line of this record's "- title:" line (deterministic sort key)
    apis_raw: str       # verbatim comma-separated string, as authored
    api_tokens: tuple[ApiToken, ...]

#: rev 7 (C1): base is `cli.IngestError`, NOT ValueError. §7.1's hierarchy table is
#: normative for every error class in this package; this module declares exactly one.
class RecipesError(cli.IngestError): ...       # -> exit 1 via cli.run

#: CookbookUnavailable is DECLARED IN cli.py AND RE-EXPORTED HERE -- never redeclared.
#: `class CookbookUnavailable(RecipesError)` (what revisions 2-6 of this section said)
#: is the defect, not the design: cli.run must catch it to map it to 5, so declaring it
#: here forces cli.py to import recipes.py, while recipes.py already imports cli.py for
#: EXIT_*/run -- a circular import that fails on the first `python -m ingest.recipes`.
#: The re-export keeps `from ingest.recipes import CookbookUnavailable` working in every
#: test that already spells it that way, and Task 8 asserts OBJECT IDENTITY
#: (`recipes.CookbookUnavailable is cli.CookbookUnavailable`), which a redeclaration
#: fails and a name-only check would not.
from .cli import CookbookUnavailable           # noqa: F401  -- re-export, see §7.1
__all__ = [..., "CookbookUnavailable", "RecipesError"]
# cli.CookbookUnavailable's meaning, restated here because this is where it is raised:
#   the cookbook clone is not on this machine. A MEASUREMENT-VALIDITY failure, never a
#   data failure -- every caller maps it to exit 5, never to 0/1/2/4 (§7.5).

#: R2-B4a: the ONE place the out-of-repo path is stated -- and it is not stated
#: here either, it is derived from the registry row that already carries it and
#: already passes invariant I3.
RECIPES_RELPATH: Final[str] = "cookbook/recipes.yml"

def default_recipes_path() -> Path:
    row = sources.by_id("chory-lab__plr-cookbook")
    return Path(row.clone_path).expanduser() / RECIPES_RELPATH
    # -> /home/<user>/projects/repos/plr-cookbook/cookbook/recipes.yml

def load_recipes(path: Path | None = None) -> tuple[Recipe, ...]:
    """`path or default_recipes_path()`. Raises CookbookUnavailable if the file
    does not exist; RecipesError for every parse failure.

    R4-B1: this function enforces NO record-count invariant, for ANY path. It is
    a grammar, and it must parse a two-record synthetic fixture as readily as the
    live cookbook -- four of this spec's own tests depend on that. "91" is a fact
    about the pinned cookbook, not a property of the grammar; its home is
    data/token_histogram.json's `n_recipes` (see below)."""
```

**Why the default is derived and not a literal (R2-B4a).** Revision 2 wrote
`load_recipes(path: Path | None = None)` and never said what `None` meant, while six acceptance
criteria and Tasks 3–8 all depended on the answer. Hardcoding
`~/projects/repos/plr-cookbook/cookbook/recipes.yml` would put the same out-of-repo path in two
places (here and `sources.json`) with nothing keeping them equal. Deriving it from the registry
row means F7's invariant I3 (`clone_path` starts with `~/projects/repos/` and resolves outside the
praxis repo) already governs it, and moving the clone is a one-field registry edit.

**When the clone is absent** — the common case; 19 of 21 registry clones are absent on this
machine as of 2026-08-27 — `load_recipes()` raises `CookbookUnavailable`, and every caller's exit
behaviour is fixed by **§7.5**, not left to the fixer. That is the second half of R2-B4.

**The file is not a bare list of records.** Verified 2026-08-27: it opens with a 12-line `#`
comment header and separates records with blank lines. Every line must be classified; the reader
raises `RecipesError` on anything it cannot classify, and never skips (F5).

| Line shape | Handling |
|---|---|
| first non-space char is `#` | **comment** — skipped, counted in `n_comment_lines` |
| empty / whitespace-only | **blank** — skipped, counted in `n_blank_lines` |
| `- title: <scalar>` | starts a record; records `line_no` |
| `  path: <scalar>` / `  chapter: <int>` / `  apis: <scalar>` | record fields |
| anything else | `RecipesError` |

**`#` is a comment only at the start of a line.** This is a deliberate, stated narrowing of YAML,
and it is the whole point of C5: every one of the 91 `path` values is a **bare scalar containing
`#`** (`part1/01_robot_on_screen.qmd#first-robot`). A reader that strips `#`-to-end-of-line — the
obvious way to write a comment stripper — truncates every anchor **silently**, producing 91
recipes that all look plausible and are all wrong. (Real YAML agrees with the narrow rule here,
because no `#` in this file is preceded by whitespace; the narrowing is safe *and* it is what a
naive implementation gets wrong.)

**Error-proofing that makes the failure impossible rather than documented:** every parsed `path`
is validated against `^[a-z0-9_/]+\.qmd#[a-z0-9-]+$`. A truncated anchor fails the regex and
raises. A silently-corrupted parse is therefore not a reachable state.

Additional reader invariants, all raising `RecipesError`. **Every one of them is a property of the
grammar, true of any well-formed input of any size** — which is what makes the reader usable
against a synthetic fixture (R4-B1, below):

- each record has exactly the four keys, each exactly once;
- scalars: a value beginning `"` must end `"` (unescaping only `\"` and `\\`); otherwise the value
  is the verbatim text with trailing whitespace stripped;
- `chapter` parses as an int in 1..18;
- `n_record_lines + n_blank_lines + n_comment_lines == total lines in file` — the reconciliation
  that proves nothing was skipped.

#### The record count is a pin about the cookbook, not a reader invariant (rev 5, R4-B1)

Revision 4 listed **"exactly 91 records"** among the invariants above — unconditionally, for every
path `load_recipes()` is given. That made four of this spec's own tests unimplementable, and they
are not peripheral tests:

| test | fixture | what the count check did to it |
|---|---|---|
| Task 3's truncation fixture | a small temp file whose `path` a `#`-stripping reader would truncate | raised on the count before the *anchor* assertion — the C5 regression test — could run |
| Task 5's `finding_id` stability test | the live file **plus one** appended recipe (92) | raised before any digest was computed |
| Task 5's `lh.mix` digest test | the live file **plus one** appended recipe (92) | same — and the spec calls this "the test that proves the fix" for C3 |
| Task 6's `census_drift` test | the live file **minus** `lh.use_channels` (90) | raised before the gate ran — this is revision 4's *own* R3-W3 fix |

**The resolution is not a carve-out; it is a re-homing.** A carve-out ("check the count only when
`path is None`") would work, but it would leave a literal `91` inside `recipes.py` describing live
cookbook data — which is precisely R2-B1's hand-listed-constant defect, and precisely what R3-B2
went to the trouble of removing from `versions.py` and from a test literal. So:

1. **`load_recipes()` holds no count literal and performs no count check**, for any path. Its
   contract is the grammar and nothing else.
2. **The count's home is `data/token_histogram.json`**, which gains an `n_recipes` field alongside
   its per-kind counts. It is emitted by `recipes --emit-histogram` and landed by §5.6(d)'s
   copy-and-review workflow — the same path every other computed file takes. **No new file**, so
   §5.6(d)'s six-hand-authored + five-computed reconciliation is unchanged.
3. **AC-1.4(2)'s existing exact comparison is the check.** It already recomputes the whole
   histogram over the default path and compares it to the committed file; with `n_recipes` in that
   file, a truncated or extended cookbook is a red test with no new mechanism.

**What still catches a truncated cookbook, named rather than assumed.** The count check was
justified by truncation, so its removal needs the replacement stated:

| corruption | detector |
|---|---|
| a truncated **anchor** (`…qmd#mix` → `…qmd`) — C5's actual hazard | the `path` regex, per record, unchanged and still unconditional |
| a file truncated at a **record boundary** | AC-1.4(2)'s `n_recipes` comparison, and §4.4 assertion 1's `recipes_yml_sha256` byte pin, which fires first and says "the working tree is dirty" |
| the clone **moving** to a new upstream tip | §4.4 assertion 0's `source_sha` pin, which fires before assertion 1 (R2-B4d) |

Two of those three already existed and were doing the work; the reader's count was a third, weaker
copy of a check §4.4 makes better — and it was the copy that broke the fixtures.

#### Why PyYAML is excluded, and why no title reaches an output

**PyYAML is not an alternative.** Revision 1 offered "adding PyYAML to `training/pyproject.toml`
is the acceptable alternative; the fixer picks one." It is not acceptable: F3 fixes the
dependency set to stdlib + `coxswain.plr` + sibling `training/` packages, and AC-1.11's purity
scan would fail on the import. Revision 1 offered a choice its own constraints had already
excluded, and pushed the decision onto the fixer. The hand-rolled reader is **mandatory**.

**Tier-0 discipline on outputs:** `Recipe.title` is available in-process, but **no generated
artifact under `training/ingest/out/` may contain a recipe title verbatim** while the cookbook
sits at tier 0. Titles are expression; `path` is an identifier. `test_ingest_no_titles_in_outputs.py`
greps all five generated artifacts for every one of the 91 titles and fails on any hit.

### 3.2 The `apis` field is not a list of API names — the load-bearing parsing fact

`apis` is a **comma-separated string** whose tokens are heterogeneous. Verified samples:

```
"LiquidHandler, LiquidHandlerChatterboxBackend, STARLetDeck, setup, stop"
"lh.summary, deck.get_all_children"
"nest_1_troughplate_195000uL_Vb, cor_96_wellplate_360uL_Fb, naming convention"
"Mix, mix, surface_following_distance"
"backend_kwargs, STARBackend.aspirate, jet, blow_out, lld_mode, surface_following_distance"
"asyncio.gather, setup, stop"
"docstring, catalog, corning, alpaqua"
"Thermocycler, ThermocyclerChatterboxBackend, Incubator, IncubatorChatterboxBackend, run_pcr_profile"
```

Any implementation that treats these as method names will produce a garbage audit. The
tokenizer is a **total, closed, mutually-exclusive classifier** — `OTHER` is a real bucket that
gets counted, not a silent drop (F5):

```python
class TokenKind(str, Enum):
    DOTTED   = "dotted"    # lh.summary / STARBackend.aspirate / asyncio.gather
    IDENT    = "ident"     # setup / mix / blow_out / surface_following_distance
    CLASSISH = "classish"  # LiquidHandler / Mix / Visualizer
    PROSE    = "prose"     # "naming convention" / "async with"
    OTHER    = "other"     # cor_96_wellplate_360uL_Fb, __setitem__ edge cases

#: C22 + R2-B3: five INDEPENDENT, POSITIVE predicates. Exactly one must hold.
#: OTHER is NOT the complement of the other four -- that is what made revision 2's
#: assertion unreachable for every possible input (R2-B3). The classifier is
#: therefore PARTIAL, and the zero-hit branch is a real, reachable state.
_WS       = re.compile(r"\s")
_IDENT    = re.compile(r"[a-z_][a-z0-9_]*")
_CLASSISH = re.compile(r"[A-Z][A-Za-z0-9]*")

#: OTHER's four positive shapes, each drawn from a token this file actually contains.
_MIXED_SNAKE = re.compile(r"[a-z_][A-Za-z0-9_]*[A-Z][A-Za-z0-9_]*")  # cor_96_wellplate_360uL_Fb
_UPPER_SNAKE = re.compile(r"[A-Z][A-Za-z0-9]*_[A-Za-z0-9_]*")        # LOG_LEVEL_IO
_DIGIT_LED   = re.compile(r"[0-9][A-Za-z0-9_]*")                     # 96, 2segments
_PUNCT_TOKEN = re.compile(r"[^\s.]*[^\s.A-Za-z0-9_][^\s.]*")         # multi-channel, try/except,
                                                                     # plate[A1:H1], column-major
_OTHER_SHAPES = (_MIXED_SNAKE, _UPPER_SNAKE, _DIGIT_LED, _PUNCT_TOKEN)

_PREDICATES = {
    TokenKind.PROSE:    lambda t: bool(_WS.search(t)),
    TokenKind.DOTTED:   lambda t: "." in t and not _WS.search(t),
    TokenKind.IDENT:    lambda t: bool(_IDENT.fullmatch(t)),
    TokenKind.CLASSISH: lambda t: bool(_CLASSISH.fullmatch(t)),
    TokenKind.OTHER:    lambda t: (
        not _WS.search(t) and "." not in t
        and any(r.fullmatch(t) for r in _OTHER_SHAPES)
    ),
}

def split_apis(apis_raw: str, recipe_path: str) -> tuple[str, ...]:
    """Comma-split + strip. An EMPTY token (a trailing or doubled comma) raises
    here with the recipe named, rather than reaching the classifier and producing
    a confusing 'matched 0 kinds'. R2-B3's second half."""
    parts = [p.strip() for p in apis_raw.split(",")]
    if any(p == "" for p in parts):
        raise RecipesError(f"{recipe_path}: empty token in apis: {apis_raw!r}")
    return tuple(parts)

def classify_api_token(raw: str) -> ApiToken:
    t = raw.strip()
    hits = [k for k, p in _PREDICATES.items() if p(t)]
    if len(hits) != 1:                       # <- the assertion, now REACHABLE both ways
        raise RecipesError(f"token {t!r} matched {len(hits)} kinds: {hits}")
    ...
```

**Why revision 2's assertion could never fire, and why this one can (R2-B3).** Under revision 2,
`OTHER` was written as the literal complement of the other four predicates, so the case analysis
closed with no gaps and no overlaps for *every possible string*: a token containing whitespace
fired `PROSE` only (`IDENT`/`CLASSISH`/`DOTTED`/`OTHER` all excluded whitespace); a
whitespace-free token containing `.` fired `DOTTED` only; and everything else fired exactly one of
`IDENT`/`CLASSISH`/`OTHER` by construction. `len(hits) != 1` was unreachable, AC-1.4(1) asserted a
falsifiability it did not have, and Task 3's gate asked for a "synthetic ambiguous token" that
cannot exist. That is C22's defect — an unfalsifiable property — reproduced inside C22's own fix.

**Disjointness of the positive predicates, argued rather than asserted.** `PROSE` and the other
four are separated by the presence of whitespace; `DOTTED` and `IDENT`/`CLASSISH`/`OTHER` by the
presence of `.` (none of the four `_OTHER_SHAPES` admits a `.`: three restrict to
`[A-Za-z0-9_]` and `_PUNCT_TOKEN` excludes `.` in all three of its character classes). Within the
dot-free, whitespace-free set the three remaining predicates are separated by **first character
and alphabet**: `IDENT` starts `[a-z_]` and admits no uppercase; `CLASSISH` starts `[A-Z]` and
admits no underscore; `_MIXED_SNAKE` starts `[a-z_]` but *requires* an uppercase (excluding
`IDENT`, and excluded from `CLASSISH` by its first character); `_UPPER_SNAKE` starts `[A-Z]` but
*requires* an underscore (excluding `CLASSISH`, and excluded from `IDENT` by its first character);
`_DIGIT_LED` starts `[0-9]`, which neither `IDENT` nor `CLASSISH` nor the other three shapes
admit; `_PUNCT_TOKEN` requires a character outside `[A-Za-z0-9_]`, which no other pattern admits.

**The classifier is now partial, and that is the point.** `""` matches nothing: no whitespace, no
`.`, no `IDENT`/`CLASSISH` (both need ≥1 character), and every `_OTHER_SHAPES` pattern needs ≥1
character. It raises. That is the fix for revision 2's silent empty-token behaviour — a bucket
that absorbed the one input the reader should complain loudest about.

**What the two guards do to each other, stated because revision 3 got it wrong (R3-W1).**
`split_apis` raises on an empty token **before** `classify_api_token` is ever called, so the two
halves of R2-B3's fix are ordered: the pipeline can never deliver `""` to the classifier, and
revision 3's claim that the zero-hit branch is "reached by a real token — a trailing comma in an
`apis` field" is therefore false. Both branches are reachable **only by a direct unit call**: the
zero-hit branch by `classify_api_token("")`, the multi-hit branch by monkeypatching `_PREDICATES`.
That means **for every producible input, `len(hits) != 1` cannot fire.**

That is the correct outcome, not a regression to C22, and the difference is worth being exact
about. C22's defect was an *unfalsifiable property*: revision 2 asserted "an overlapping- or
zero-predicate bug fails the AC" while `OTHER`'s complement definition made both branches
unreachable **even for a defective predicate table** — the assertion could not detect the bug it
named. Rev 3's positive shapes fix precisely that: a defective table *is* now detectable, and the
monkeypatch test detects it. What remains true — and is true of every well-formed total function —
is that a *correct* implementation over *valid* input never trips its own invariant. The honest
statement is that `len(hits) != 1` is an assertion about the **implementation**, tested against the
implementation; the assertion about the **input** is `split_apis`' empty-token guard, which is
tested against input (`split_apis("a,,b", …)` raises, naming the recipe). Two different claims,
two different tests, and revision 3 conflated them into one false sentence.

The independent, input-facing payoff of the positive `OTHER` survives untouched: a token matching
no shape is a loud `RecipesError` naming the token, where revision 2 would have filed it silently
under `OTHER` and moved on.

**Behaviour-preserving over the current file.** Every token in the 91 recipes that revision 2's
complement-`OTHER` absorbed is matched by one of the four positive shapes:
`cor_96_wellplate_360uL_Fb` / `nest_1_troughplate_195000uL_Vb` / `hamilton_96_tiprack_50uL_NTR` →
`_MIXED_SNAKE`; `LOG_LEVEL_IO` → `_UPPER_SNAKE`; `multi-channel` / `column-major` /
`contributing-new-resources` / `multi-dispense` / `try/except` / `plate[A1:H1]` → `_PUNCT_TOKEN`.
Tokens that *look* like they moved do not: `alpaqua_96_plateadapter_magnum_flx` is all-lowercase
and was, and remains, `IDENT`; `__subclasses__` and `_check_args` are `IDENT` under both;
`LCFS`, `USB`, `HID`, `FTDI` are `CLASSISH` under both. The committed
`token_histogram.json` is therefore expected to be unchanged.

**Round 3 verified this by exhaustive classification of the live token inventory, and the result
is stronger than "behaviour-preserving" (rev 4).** The four positive shapes are not only disjoint
from `IDENT`/`CLASSISH` but **jointly exhaustive** over every non-empty token: any dot-free,
whitespace-free token starting `[a-z_]` is `IDENT` or `_MIXED_SNAKE`; starting `[A-Z]` is
`CLASSISH` or `_UPPER_SNAKE`; starting `[0-9]` is `_DIGIT_LED`; and anything containing a
non-`[A-Za-z0-9_]` character is `_PUNCT_TOKEN`. **No live token raises**, and every spot-check held
(`alpaqua_96_plateadapter_magnum_flx` → `IDENT`; `__setitem__` / `__subclasses__` / `_check_args` →
`IDENT`; `backends/chatterbox.py` → `DOTTED` only). AC-1.4(3) is therefore satisfied today by
exhaustion, and its "a token that raises is information to record" clause is a **forward** rule for
a future cookbook rather than a live expectation — see AC-1.4(3), where revision 3's phrasing is
corrected.

```python
class ReceiverType(str, Enum):
    """CLOSED receiver vocabulary (W4/W11). NONE is not a gap in the alias table --
    it is the receiver type of a token that HAS no receiver, which is every
    non-DOTTED token. OTHER is a DOTTED token whose receiver is not one of ours."""
    LIQUID_HANDLER = "liquid_handler"
    PLATE_READER   = "plate_reader"
    HEATER_SHAKER  = "heater_shaker"
    OTHER          = "other"    # receiver present, maps to `other` (§3.3)
    NONE           = "none"     # NO receiver: IDENT / CLASSISH / PROSE / OTHER tokens

@dataclass(frozen=True)
class ApiToken:
    raw: str
    kind: TokenKind
    receiver: str | None          # DOTTED only: everything before the LAST '.'; else None
    receiver_type: ReceiverType   # NONE whenever receiver is None  (W4)
    member: str                   # DOTTED -> after last '.'; IDENT/CLASSISH -> the token; else ""

def method_shaped(t: ApiToken) -> bool:
    """The ONLY tokens comparable to TOOL_SCHEMA (used by §5.4 and §6.4/T3)."""
    return (t.kind is TokenKind.IDENT) or (
        t.kind is TokenKind.DOTTED and bool(re.fullmatch(r"[a-z_][a-z0-9_]*", t.member))
    )
```

**`receiver_type` is total, and `NONE` is what makes it so (W4).** Revision 2 declared
`receiver: str | None` with the comment "DOTTED only" and then had `_adjudicable_view` (§5.2) read
`e.receiver_type` on evidence rows for non-DOTTED tokens, where no such value existed — so the
digest projection was not computable as written. A closed five-member enum with an explicit
`NONE` makes every token carry a receiver type, and it keeps the two distinct failure meanings
apart: `OTHER` means "we saw a receiver and it is not one we model"; `NONE` means "there was no
receiver to see". Collapsing them would have made an unmapped receiver indistinguishable from a
bare identifier in the digest.

`data/token_histogram.json` commits the per-kind counts **and `n_recipes`** over the current
`recipes.yml` (AC-1.4). It is a **regression pin**: computed by the fixer, reviewed once, and
thereafter a silent reclassification — or a change in the number of recipes — is a red test. It is
explicitly *not* a pre-registered threshold and no gate reads it.

```jsonc
{
  "token_histogram_version": "2",          // bumped by rev 5's n_recipes addition
  "n_recipes": 91,                          // R4-B1: the count's one DERIVED home (R5-W1)
  "counts": {"dotted": 0, "ident": 0, "classish": 0, "prose": 0, "other": 0}
}
```

*The per-kind values are left as `0` placeholders **on purpose**: they are computed by
`recipes --emit-histogram` and transcribing a guess here would be the hand-listed-constant defect
the header banner's standing rule forbids. `n_recipes` is written out because it is derived in
§4.2 and §5.4.1 from the same reading of the file, and rounds 4 and 5 verified it a third and
fourth time.*

**"One home" is a claim about *derivation*, not about *occurrences* — rev 6 says which (R5-W1).**
Revision 5's comment on this field read *"the count's ONE home"*, and it was false as written:
`eval_split.json` (§4.3) has carried `n_recipes: 91` since an earlier revision, and none of §4.4's
assertions looked at it. So the fix for R4-B1 left the count with **two** committed homes — one
exact-compared against the live file by AC-1.4(2), one an unchecked hand-copied literal about live
cookbook data, which is precisely the shape R4-B1's fix existed to consolidate away. The accurate
claim, and the one revision 6 makes true:

- **This file is the count's only *derived* home.** `recipes --emit-histogram` computes it from the
  parsed cookbook; AC-1.4(2) re-derives and compares exactly.
- **Every other committed copy is *pinned to this one*, never independently authored.** There is
  exactly one such copy — `eval_split.json`'s `n_recipes` — and **§4.4 assertion 6** (new in rev 6)
  asserts it equals this file's value. Both files are committed in-repo, so that assertion runs
  with no clone present.
- **No third copy may be added without an assertion tying it here.** The rule that makes the first
  two bullets stable is the one the header banner already states: a number describing the live
  cookbook is derived once and compared everywhere else.

Deleting `eval_split.json`'s field was the cheaper fix and was rejected: that file is the standing
record of *what the split was computed against*, and a reader of it should not have to open a
second file to learn the denominator. One assertion buys the redundancy honestly.

### 3.3 Receiver classification — an exact table, no wildcards (C9)

Revision 1 wrote `` `*Backend` where the module is a liquid-handler backend → liquid_handler``.
That condition is **undecidable from `recipes.yml`**, which contains no module information, and
line 32 of the file supplies two direct counterexamples in one recipe:
`ThermocyclerChatterboxBackend, IncubatorChatterboxBackend`. A `*Backend ⇒ liquid_handler`
implementation would classify both as liquid handlers and feed fabricated `RECEIVER_DRIFT` /
`SURFACE_ADJACENT` findings — both **blocking** — into G2.

`training/ingest/data/receiver_aliases.json` is therefore an **exact** map. **Revision 3 rebuilds
it against the real file (W10).** Revision 2's illustrative table named ten receivers that never
appear as a DOTTED receiver anywhere in the 91 recipes (`LiquidHandlerChatterboxBackend`, `STAR`,
`pr`, `PlateReader`, `hs`, `HeaterShaker`, `Thermocycler`, `ThermocyclerChatterboxBackend`,
`Incubator`, `IncubatorChatterboxBackend` — all of them appear only as **CLASSISH** tokens, which
by construction have no receiver) and omitted twenty-eight that do. The complete set, derived from
every DOTTED token in the file:

```jsonc
{
  "receiver_aliases_version": "2",
  "default": "other",
  "exact": {
    "lh": "liquid_handler", "LiquidHandler": "liquid_handler", "STARBackend": "liquid_handler",

    "ChannelizedError": "other", "Deck": "other", "F": "other",
    "ItemizedResource": "other", "Liddable": "other", "Plate": "other",
    "Resource": "other", "ResourceStack": "other", "TipRack": "other", "TipSpot": "other",
    "asyncio": "other", "backends/chatterbox": "other", "capturer": "other",
    "config": "other", "csv": "other", "datetime": "other", "deck": "other",
    "functools": "other", "itertools": "other", "liquid_handling": "other",
    "logger": "other", "manifest": "other", "pylabrobot": "other", "random": "other",
    "resources": "other", "resources.utils": "other", "tracker": "other", "utils": "other"
  }
}
```

**Exactly 31 receivers; exactly three map to `liquid_handler`; none maps to `plate_reader`.**
That last fact is load-bearing and was invisible in revision 2: the cookbook never uses a
plate-reader receiver in dotted form, so of the two blocking receiver-dependent kinds, only the
`liquid_handler` half can fire at all today.

Rules:

1. A DOTTED token's `receiver` is looked up in `exact`; a miss maps to `default` (`other`) and
   emits an advisory `unmapped_receiver` finding, one per distinct unmapped receiver (F5). A
   non-DOTTED token has no receiver and takes `ReceiverType.NONE` without consulting the map.
2. **Task 3's gate is a two-way equality over the KEY SET (strengthened in rev 3, W10; scoped
   correctly in rev 4, R3-B3):** `set(exact) == {t.receiver for t in tokens if t.kind is DOTTED}`.
   Revision 2 required only zero *unmapped* receivers, which a table with ten fictional entries
   satisfies — and did. Requiring equality also forbids **unused** entries, because a dead entry is
   an unfalsifiable claim about a file we can read. The equality is asserted in the **test**, not
   at load time: at load time the advisory path applies, so the package still runs against a newer
   cookbook. **This check says nothing whatever about the values** — see rule 5.
3. **Three tokens are method-shaped without being methods, and they are the worked example for
   why (3)'s asymmetry matters.** `backends/chatterbox.py` (recipe line 377) is whitespace-free and
   contains `.`, so it is `DOTTED` with receiver `backends/chatterbox` and member `py`;
   `manifest.json` and `config.json` (line 312) are `DOTTED` with receiver `manifest`/`config` and
   member `json`. All three members are lowercase identifiers, so `method_shaped()` is **true** for
   all three. They are nonetheless harmless: their receivers map to `other`, so they can only
   produce advisory `UNKNOWN_METHOD` rows, never a blocking finding.
4. **Safety asymmetry, recorded:** both blocking receiver-dependent finding kinds
   (`RECEIVER_DRIFT`, `SURFACE_ADJACENT`) require `liquid_handler` or `plate_reader`. Since an
   unmapped receiver becomes `other`, a gap in the table can only ever **under-report** a blocking
   finding — never fabricate one. Combined with (2), the failure mode is a visible advisory row
   rather than a spurious G2 block, which is the direction that keeps PM-2's "gate so expensive
   it gets waived" failure away.
5. **The VALUES are hand-authored, and only the KEYS are derivable (rev 4, R3-B3).** This is C9
   restated as an operational rule rather than as a design note, because revision 3 stated C9 in
   §3.3 and then contradicted it in §5.6(d) by calling the whole file "computed". `recipes.yml`
   carries **no module information**, so nothing in it can decide that `lh`, `LiquidHandler` and
   `STARBackend` are liquid handlers while `Deck`, `Plate` and `Liddable` are not. A value is
   assigned by a **human** reading the receiver's type from vendored PLR at
   `dd79c4c89bc008629a1c598ea614be5e6067d1f9` (or from the cookbook prose around the recipe), and
   recorded once.
   - **What rule 2 does and does not catch.** Rule 2 is a key-set equality. A file whose 31 keys
     are exactly right and whose 31 values are all `other` **passes rule 2 unchanged**. It also
     silently drives `surface_adjacent` from 5 to 0 (the kind requires `liquid_handler` or
     `plate_reader`, and `receiver_drift`'s 0 stays 0), which is the safety asymmetry of rule 4
     turned into a hazard: under-reporting is safe when it is *visible*, and here it would not be.
   - **The guards, ordered by when each one can fire (rev 5, R4-W2).** Revision 4 called the next
     two bullets *"two independent detectors"*. **They are not independent at authoring time**, and
     the difference decides which one actually protects the file:

     | # | guard | fires on an **initial** all-`other` authoring error? | fires on a **later** value regression? |
     |---|---|---|---|
     | 1 | **Task 3's three-value pin** — `exact["lh"] == exact["LiquidHandler"] == exact["STARBackend"] == "liquid_handler"`, and no other key maps to `liquid_handler` or `plate_reader` | **yes — and it is the only one that does** | yes |
     | 2 | **§5.4.1's written derivation** — a reviewer re-runs it against the committed census | yes, if a human performs it | n/a (it is a review step, not a test) |
     | 3 | **`blocking_census.json`'s `surface_adjacent: 5`** (§5.6d) | **no** | yes |

     **Why guard 3 cannot see the initial error.** Task 3 authors the alias map; Task 5 emits the
     census **from** it (`audit --emit-census` counts findings the map produces). An all-`other`
     map at Task 3 therefore yields `surface_adjacent: 0` in the observation **and** `0` in the
     file that observation is committed to — and AC-1.6, which asserts observed == committed and
     deliberately holds no literal of its own (R3-B2), stays **green**. The census is a regression
     detector, not an authoring detector: it pins whatever was true when it was emitted.
     That makes Task 3's three-line value pin the **first and only** line of defence at authoring
     time, which is why it is stated as a task gate item rather than left to the census.
   - **The emitter is a merge proposal, never an overwrite** — see §5.6(d)'s
     `recipes --emit-receiver-alias-keys` contract.
   - **Task 3's hand transcription IS the bootstrap (rev 5, R4-W1).** The emitter reads *the
     existing committed file*, and Task 3 is where that file first exists — so its first version
     is not emitted at all: a human transcribes the 31-row table above, assigns the three
     `liquid_handler` values, and commits it. The emitter is a **second-run-onward** tool, for the
     day a newer cookbook adds or drops a receiver. Running
     `recipes --emit-receiver-alias-keys` with no committed file present raises `RecipesError`
     naming the missing path and exits 1; it does **not** emit a 31-key map with every value
     `other` and every key in `needs_review`. That would be a generator for precisely the file
     C9 proves cannot be generated, and it would hand a fixer an artifact that passes rule 2's
     key-set equality while carrying no information — R3-B3's failure mode with a bootstrap
     wrapper around it.
   - **When both conditions hold, the clone check wins (rev 6, R5-S3).** The bullet above and
     §7.5's row describe two failures that are **simultaneously true during this very task** on a
     checkout with no `~/projects/repos/`: the cookbook clone is absent (→ exit 5) *and* the
     committed file does not exist yet (→ exit 1). The emitter checks the clone **first** and
     exits 5, matching `audit --gate`'s clone → census ordering and §5.5's stated reason: exit 1
     here tells a human to hand-transcribe a 31-row table, and issuing that instruction from a
     command that could not have run is worse than issuing no instruction at all.

---

## 4. `eval_split.py` — RESOLVED: this belongs in Increment 1

### 4.1 The decision and its reasoning

**The eval-split file is produced and committed in Increment 1.** The brainstorm left this
ambiguous (`[MERGE] ORTHOGONAL-1` and PM-4 both require it; neither says when). Resolving it
into Increment 1:

1. **It has no other input.** The split needs `recipes.yml` and nothing else.
2. **PM-4's failure mode is a conflict of interest, and Increment 1 is the only increment
   without one.** If the split is authored in Increment 3, the same person is simultaneously
   deciding what to hold out and consuming the remainder as training anchors.
3. **The cost is ~40 LOC plus one data file**, against a failure whose signature — per the
   pre-mortem — is *"every naturalness number reported after that date is inflated with nobody
   able to tell."*
4. **The counter-argument is real but weaker:** Increment 1 produces no training rows, so there
   is nothing to leak into yet. But an unused holdout index costs nothing, and a *missing* one
   at the moment it is first needed costs the eval. Rev 2 strengthens this: §4.5's leak gate runs
   **now**, over the real committed sidecar, so the mechanism is proven live rather than parked.

### 4.2 The split rule — seedless, and that is a deliberate strengthening

The brainstorm's ORTHOGONAL-1 says "seeded, committed, chapter-stratified"; PM-4's mitigation —
the later and more specific decision — says the split must be *"COMMITTED AS DATA … never
recomputed from a seed over a mutable input set."* **This spec drops the seed**, because PM-4
identifies the seed itself as the hazard and "committed" as the part that binds.

```
For each chapter c with n_c recipes:
    n_held(c) = 0                                    if n_c < 3
              = max(1, round_half_even(0.20 * n_c))  otherwise
Within chapter c, sort recipes by (path, line_no) ascending; hold out the LAST n_held(c).
```

**Sort key changed in rev 2:** revision 1 sorted by `(path, title)`, which made the rule depend on
tier-2 expression. `line_no` is a tier-0 file fact, is total (no ties possible), and keeps the
rule deterministic even if two recipes ever shared a path. Path uniqueness is asserted separately
(§4.4) rather than assumed by the sort.

Against the current `recipes.yml` (91 recipes; per-chapter counts 1:6, 2:4, 3:4, 4:7, 5:8, 6:3,
7:6, 8:9, 9:7, 10:5, 11:4, 12:5, 13:2, 14:2, 15:1, 16:2, 17:8, 18:8) this holds out **18 of 91
(19.8%)**, with chapters 13/14/15/16 contributing 0 because they are below the `n_c < 3` floor.

### 4.3 `training/ingest/data/eval_split.json`

```jsonc
{
  "eval_split_version": "1",
  "source_id": "chory-lab__plr-cookbook",
  "source_sha": "<40-hex, = registry pinned_sha>",
  "recipes_yml_sha256": "<hex of the parsed file's bytes>",
  "rule": "per chapter: n_held = 0 if n < 3 else max(1, round_half_even(0.20*n)); within chapter sort by (path, line_no) asc, hold out the LAST n_held",
  "n_recipes": 91,             // PINNED to token_histogram.json's n_recipes -- assertion 6 (R5-W1)
  "n_held_out": 18,            // PINNED to len(held_out_paths)               -- assertion 6 (R5-W1)
  "held_out_paths": ["part1/01_robot_on_screen.qmd#setup-stop", "..."],
  "held_out_extra": {},        // path -> reason, for entries added beyond the rule (§4.4)
  "held_out_ever": ["..."],    // APPEND-ONLY union across all versions  (C10 monotonicity)
  "retired_paths": {}          // path -> version in which it vanished from recipes.yml
}
```

**Paths only. No titles** — the file itself must be tier-0 clean (§3.1).

**Neither counter is an independent claim, and rev 6 says so at the point of use (R5-W1).**
`n_recipes` and `n_held_out` are convenience fields for a human reading this file; both are
**derived from something else in the repository and checked against it** by §4.4 assertion 6.
`n_recipes` is pinned to `token_histogram.json`'s `n_recipes` (§3.2, the count's one derived home);
`n_held_out` is pinned to `len(held_out_paths)` in this same file. Round 5 found the first of those
unchecked; the second had the identical shape one field over and is fixed with it. Neither
assertion needs a clone — both `data/` files are committed in-repo — so they run everywhere,
including the checkout with no `~/projects/repos/` that §7.5 describes as this machine's normal
state.

**`source_sha` outranks `recipes_yml_sha256`, and rev 3 says so (R2-B4d).** The cookbook clone is
**shallow and tracking `main`**, so its working tree can move to a new tip on any re-clone.
Revision 2 pinned only `recipes_yml_sha256` — the bytes of a mutable out-of-repo file — which
makes a re-clone look identical to a hand-edit and undermines the reproducibility claim
AC-1.4's histogram and AC-1.10 both lean on. The commit SHA is the authoritative pin (it is
already in `sources.json` as `pinned_sha` and mirrored here as `source_sha`); the byte hash is a
**subordinate** check that catches a dirty or hand-edited working tree at a SHA that did not move.
§4.4's assertion order encodes exactly that precedence, so the two failures produce two different
diagnoses instead of one confusing one.

### 4.4 Authority and change control (C10)

PM-4's mitigation is that the committed list is **data**, not a recomputation. Revision 1's
AC-1.5 asserted "the committed list equals the §4.2 rule recomputed against the current
`recipes.yml`", which makes the recomputation authoritative and inverts the mitigation: an
upstream `recipes.yml` change legitimately moves rows out of the holdout, and the suite goes green
again as soon as someone regenerates. The assertions, in evaluation order (rev 3 inserts
assertion 0 and demotes 1 — R2-B4d; **rev 6 appends assertion 6 — R5-W1**, so this suite has
**seven** assertions, 0–6):

0. **`source_sha` equals the registry's `pinned_sha` *and* the clone's resolved HEAD.** If the
   HEAD disagrees, the test fails *first* and its message is: *"the cookbook clone moved (shallow
   clone tracking `main`). This is an input change, not a corruption. Re-pin `pinned_sha` in
   `sources.json` with a recorded reason (§2.5), then follow the re-split procedure."* If the
   clone is absent, this assertion and 1–3 **skip** per §7.5; assertions 4, 5 and 6 still run,
   because they read only committed data.
   *Rev 4: round 3 checked whether this assertion silently assumes a **full** clone — it does not.
   It compares `source_sha` against the registry's `pinned_sha` and against the clone's **resolved
   HEAD** only; it never resolves an arbitrary historical SHA, which is the one operation a shallow
   clone cannot serve. Verified live: `.git/shallow` is present, `.git/HEAD` holds
   `ref: refs/heads/main`, and a **loose** `.git/refs/heads/main` exists — so §2.5's
   HEAD → refs → packed-refs chain resolves without `git`. Note that `packed-refs` holds only
   `refs/remotes/origin/main`, so a naive packed-refs scan for `refs/heads/main` finds nothing; the
   loose ref is what makes the chain work here, and §2.5's ordering (refs/heads **first**) is what
   makes it correct.*
1. **`recipes_yml_sha256` matches the file on disk.** Reached only when assertion 0 held, so its
   message can be specific: *"recipes.yml changed at an unchanged HEAD — the working tree is dirty
   or the file was edited in place. Do NOT regenerate eval_split.json to make this pass. Follow
   §4.4's re-split procedure: bump `eval_split_version`, recompute, and verify the monotonicity
   invariant."* This check is **subordinate to 0**: bytes can only diverge from a fixed SHA by an
   edit, and an edit is a worse diagnosis than a moved clone, not a milder one.
2. **Every `held_out_paths` entry exists in the current `recipes.yml`.**
3. **`held_out_paths ⊇ rule_recompute(recipes.yml)`**, and every path in
   `held_out_paths \ rule_recompute` has an entry in `held_out_extra`. Widening a holdout is
   always safe (it only shrinks training); narrowing it is what PM-4 forbids. This check's role is
   to catch an implementation bug or an unrecorded hand-edit — **it is subordinate; the committed
   list wins.**
4. **Monotonicity: `held_out_ever ∩ current_paths ⊆ held_out_paths`.** A path that has ever been
   held out and still exists in the source can never return to training. This is the invariant
   revision 1 lacked entirely, and it is what makes a re-split safe.
5. **`held_out_paths ⊆ held_out_ever`**, `retired_paths` accounts for exactly
   `held_out_ever \ current_paths`, and every `path` in the file is unique across the 91 recipes.
6. **Neither committed counter is an independent claim (new in rev 6 — R5-W1).** Two equalities,
   both over committed in-repo data only, so this assertion runs with **no clone present**:
   - `eval_split.json["n_recipes"] == json.loads((DATA / "token_histogram.json").read_text())["n_recipes"]`
     — the eval split may not disagree with the count's one derived home (§3.2). Failure message:
     *"eval_split.json and token_histogram.json disagree about the recipe count. token_histogram.json
     is authoritative — it is re-derived from the cookbook by AC-1.4(2). Update eval_split.json (and
     if the cookbook really changed, follow the re-split procedure)."*
   - `eval_split.json["n_held_out"] == len(eval_split.json["held_out_paths"])` — a pure
     internal-consistency check on one file.

   *Why this exists.* Round 5 found `n_recipes: 91` sitting in this file unchecked by assertions
   0–5, one revision after R4-B1 re-homed the same constant *out* of `recipes.py` on the grounds
   that a hand-copied literal about live cookbook data is a defect. It was the same defect, in the
   file next door, and nothing would have caught it: when the cookbook grows to 95, AC-1.4(2) turns
   `token_histogram.json` red until it is updated, while this file would go on asserting 91 with
   nothing looking. `n_held_out` had the identical shape — round 5 did not name it, and it is fixed
   here because finding one instance of a class and fixing only the named one is how R2-B1 became
   R4-B1 became R5-W1. **Ordering note:** `token_histogram.json` is created in Task 3 and this file
   in Task 4, so the dependency runs forward and Task 4's suite can read it.

**Re-split procedure** (the only sanctioned way to change the file): bump `eval_split_version`,
update `source_sha` **and** `recipes_yml_sha256` (in that order — a `source_sha` change is the
event, a byte change is its consequence), recompute the rule, **union** the result with
`held_out_ever ∩ current_paths`, move vanished paths into `retired_paths`, refresh `n_recipes`
**from the re-emitted `token_histogram.json`** and `n_held_out` from the new
`len(held_out_paths)` (rev 6, R5-W1 — neither is retyped from memory), and commit — one
reviewable diff in which any narrowing is structurally impossible.

**What AC-1.10's determinism claim does and does not cover (R2-B4d).** AC-1.10 runs each writer
twice against the *same* on-disk inputs inside one test session, so a mutable upstream file cannot
affect it: determinism is a property of the code given fixed inputs, and it holds. What a shallow
`main`-tracking clone threatens is **reproducibility across time** — the same command run next
month against a re-cloned cookbook producing different bytes — and that is not a determinism
failure but an *input change*. Assertion 0 is what makes an input change loud instead of silent.
Revision 2 conflated the two and claimed byte-pinning gave it both.

### 4.5 The leak gate — an obligation with an owner (C11)

Revision 1 defined `assert_no_leak()` with a docstring saying *"Increments 3 and 4 MUST call
this"* and gave it no caller, no test, and no AC. That is the unowned-obligation shape PM-3 exists
to prevent, reproduced inside PM-4's mitigation.

```python
#: rev 7 (C1): this is the ONE error class in the package that deliberately does NOT
#: subclass `cli.IngestError`, and §7.1's hierarchy table lists it for that reason.
#: `cli.run`'s catch-all clause maps every IngestError to exit 1; a leak is a DECISION
#: worth exit 6 (§9's G5), produced by `--check-leak`'s own handler catching this and
#: returning 6. Rebasing it on IngestError -- the "consistent" edit -- would let the
#: catch-all silently remap the only non-zero code the eval-leak gate can emit.
class EvalSplitLeak(RuntimeError): ...     # NOT cli.IngestError. Handler returns 6.

def is_held_out(recipe_path: str) -> bool: ...

def check_corpus_for_leak(sidecar_rows: Iterable[Mapping[str, Any]]) -> tuple[str, ...]:
    """Return one message per leaking row. Empty tuple => clean. FAIL-CLOSED:

    1. a row whose lineage.source_id == "chory-lab__plr-cookbook" and which carries NO
       lineage.recipe_path is a leak (unattributable recipe-derived material);
    2. a row with split == "train" whose lineage.recipe_path is in held_out_ever is a leak;
    3. (W3) a row carrying any lineage key outside data/lineage_contract.json's
       known_keys | reserved_cookbook_keys is a CONTRACT VIOLATION, reported as a leak.

    Keying on held_out_ever rather than held_out_paths is what makes §4.4's monotonicity
    invariant load-bearing: a path cannot escape the check by being dropped from the
    current holdout."""

def assert_no_leak(sidecar_rows) -> None:
    """Raise EvalSplitLeak listing every offending row. Called by --check-leak (G5)."""

# rev 8 (C7): the handler block below needs a reader, so the reader is DEFINED here
# rather than assumed -- R4-B3's lesson (a normative block that calls a helper the
# spec never defined is a block a fixer cannot write).
def load_sidecar_rows(path: Path) -> tuple[Mapping[str, Any], ...]:
    """Read a JSONL sidecar into a tuple of row mappings, in file order.

    A missing, unreadable or unparseable sidecar is a MEASUREMENT error, never a leak:
    it raises `cli.IngestError` -- the root class itself, because eval_split.py declares
    no subclass of it (§7.1's table lists none for this module) -- which `cli.run` maps
    to exit 1. It must NEVER raise EvalSplitLeak: 6 means "a leak was found", and a file
    that could not be read found nothing."""
```

**The `--check-leak` handler, as normative code, because a trailing comment was not enough (rev 8,
C1/C7).** Until this revision the `EvalSplitLeak` → **6** mapping existed in this document only as
prose (§7.1's hierarchy table, §7.5, AC-1.13) and as the comment above the class — while *every
other* exit mapping in the package has a normative code block (`cli.run`,
`IngestArgumentParser.parse_args`, the five-module `_main` template). That asymmetry is not
cosmetic: `assert_no_leak` is named as an assert-style raiser, so the plausible handler is
`assert_no_leak(rows); return 0` with **no `try/except` at all** — and because `EvalSplitLeak` sits
deliberately outside `cli.run`'s hierarchy, it would then escape as an **uncaught traceback**,
which the interpreter reports as exit **1**. G5 would say "measurement error" on a real leak. The
`try/except` *is* the mechanism; here it is:

```python
# eval_split.py -- the subcommand group and the --check-leak handler. NORMATIVE.
g = p.add_mutually_exclusive_group(required=True)
g.add_argument("--check-leak", type=Path, dest="sidecar", metavar="SIDECAR")
g.add_argument("--emit", action="store_true")
g.add_argument("--emit-lineage-contract", action="store_true")
# ... and out_required_for=("emit", "emit_lineage_contract") on the parser (§7.1, C3)

def _check_leak(args) -> int:
    rows = load_sidecar_rows(args.sidecar)          # the path --check-leak carried
    try:
        assert_no_leak(rows)
    except EvalSplitLeak as exc:
        print(exc, file=sys.stderr)                 # gate output IS the interface (§7.4)
        return 6
    return 0
```

***The sidecar rides on `--check-leak` itself; it is NOT a bare positional and it has NO default
(rev 8, C2).*** Round 7 asked which of those two it was, and the answer is neither — both would
break a row this document already commits to. A **required bare positional** would be demanded by
`--emit` and `--emit-lineage-contract` too, whose §7.5 rows carry no sidecar and expect **0**; they
would start exiting 64. A **`nargs="?"` positional with a default** would push "did you give me a
path?" into the handler, creating a second usage-error path — the exact duplication `cli.py`'s
single `error()` funnel exists to prevent — and would let G5 run against a path nobody typed.
`--check-leak PATH` gives one flag, one argument, one funnel: omit the path and `argparse`'s
"expected one argument" goes through `IngestArgumentParser.error()` → `UsageError` → **64**, like
every other malformed command line in the package. `dest="sidecar"` is spelled explicitly so
`args.sidecar` reads as it should, and membership in the group is still decided by *which* action
fired, not by dest truthiness.

*`--emit-lineage-contract` reads the sidecar too (its `known_keys` is the observed union over the
188 committed rows), and its §7.5 row carries no path — so it resolves one from
`SIDECAR_RELPATH = "training/assemble/out/corpus_p25_sidecar.jsonl"` via `default_sidecar_path()`,
mirroring `recipes.py`'s `RECIPES_RELPATH`/`default_recipes_path()`. That constant is the "committed
default" round 7 asked about, and the point of the paragraph above is that **`--check-leak`
deliberately does not use it**: the contract emitter describes a fixed corpus, while the gate must
be able to run against a fixture (Task 4's exit-6 test does exactly that) and must show its input at
the call site.*

Three properties of that block are load-bearing and none of them is inferable from the class
declaration alone. (i) The `except` clause is what keeps `EvalSplitLeak`'s exclusion from
`cli.IngestError` *safe* rather than merely *deliberate* — without it the exclusion is strictly
worse than membership, because a member at least gets mapped to a defined code. (ii) `return 6`,
not `raise SystemExit(6)`: the handler returns an int to `cli.run`, which returns it to `_main`,
which is the only place `SystemExit` is raised (§7.1's template). (iii) The message goes to
**stderr** and the exit code carries the verdict, matching every other gate in §9.

**Named as round 3's standing rule requires — the event, and the observation that fires.** The
event is *a `--check-leak` handler with no `try/except`, or one that re-raises*. The observation is
**Task 4's exit-6 assertion**: `eval_split._main(["--check-leak", str(leaking_fixture)])` returns
exactly **6**, driven through the CLI entry point rather than against `check_corpus_for_leak`
directly. Round 7's finding was that no test anywhere drove a *leaking* input through the CLI — all
four fixtures below test the library functions, and every `--check-leak` invocation in the document
used the clean 188-row sidecar and expected 0 — so the entire exclusion design rested on an
untested handler contract. Task 8's `test_ingest_error_hierarchy.py` keeps its static
`not issubclass(...)` check; the two together are the same pairing `ProtectedPathError` already
had (static base + end-to-end exit), which is the asymmetry round 7 named.

**Rule 3 is rev 3's fix for the reason rules 1 and 2 could never fire (W3).** Rules 1 and 2 key on
`lineage.source_id` and `lineage.recipe_path`. **Neither field exists in the live sidecar.** A
coverage row's lineage is `{cell_id, gap_fields, generator_version, matrix_ambiguity_class,
matrix_version, prompt_version, source_file, teacher_model_version}`; a naturalness row's is a
*different* set adding `origin`, `receiver_type` and `source_notebook_or_protocol`; a golden row's
adds `authoring_note`. Those names are chosen by `assemble` and by Increment 3, which §12.3
already concedes Increment 1 cannot constrain — so if Increment 3 names its cookbook attribution
`qmd_anchor` or `recipe`, G5 stays green forever while the leak it exists to catch walks past. That
is not "a limitation of the corpus", which is how revision 2's §12.6 labelled it; it is an
**unenforced cross-increment field-name contract**, and the difference matters because a contract
can be enforced from this side and a corpus cannot.

`training/ingest/data/lineage_contract.json`:

```jsonc
{
  "lineage_contract_version": "1",
  "known_keys": ["..."],                   // the observed union over the 188 committed rows
  "reserved_cookbook_keys": ["source_id", "recipe_path"],
  "note": "Any lineage key outside these two sets fails G5. Adding a key is a reviewed diff to this file; that diff is the moment someone must decide whether the new field carries cookbook attribution.",
  "vocabulary_collisions": {
    "receiver_type": "The naturalness rows' lineage carries a key literally named `receiver_type`. It is UNRELATED to ingest.recipes.ReceiverType (§3.2), which is a closed enum over cookbook DOTTED receivers. Same word, different vocabularies, no conversion between them."
  }
}
```

*The `vocabulary_collisions` block is rev 4's, added because round 3 hit the collision while
spot-checking W3 and had to reason it out. A name that means two things in one repo is a
context-window trap for the next reader; writing it down where both readers land is cheaper than
renaming a committed corpus field.*

`known_keys` is **computed, never hand-listed** — `python -m ingest.eval_split
--emit-lineage-contract --out <dir>` produces it and §5.6(d)'s copy-and-review workflow lands it.
Hand-listing is exactly what produced W10, and round 2's own eight-key list for this finding was
itself incomplete (it described a coverage row and missed the naturalness and golden keys), which
is the same failure a third time. Do not trust any hand-written key list in this document,
including the sentence above; run the emitter.

**What this buys, stated precisely.** It does not make Increment 3 name the field `recipe_path`.
It makes Increment 3 **unable to add any lineage key at all** without a red gate and a reviewed
diff to a file whose `note` asks the one question that matters. The residual risk — Increment 3
adds `recipe_path`, updates the contract, and populates it wrongly — is real and is §12.6.

**Enforcement, not exhortation.** `python -m ingest.eval_split --check-leak <sidecar.jsonl>` is
gate **G5** in §9's table and runs in Task 8's suite over
`training/assemble/out/corpus_p25_sidecar.jsonl`. **The sidecar is `--check-leak`'s OWN required
argument — `--check-leak PATH` — not a bare positional and not defaulted** (rev 8, C2; the shape and
the reasoning are two paragraphs above). `--check-leak` with no path is a usage error → **64**, like
any other. §7.5's row and §9's G5 row both spell the path literally, because the file G5 reads lives
under `training/assemble/`, another sub-pipeline's output directory, and a gate whose input is
invisible at the call site is a gate nobody re-reads. Rules 1 and 2 are trivially green today (no row
carries cookbook lineage) but **rule 3 is a live assertion over all 188 rows right now**, which is
what makes G5 more than a parked helper — revision 2's version had no assertion that could
evaluate to anything at all against the committed corpus. G5 turns red the first time Increment 3
lands a leaked row *or* an undeclared lineage key, **without anyone having to remember to wire it
up.**

`training/tests/test_ingest_eval_split.py` covers `check_corpus_for_leak` directly with four
synthetic fixtures: a clean corpus, a train-split row on a held-out path (leak type 2), a
cookbook-lineage row with no `recipe_path` (leak type 1), and a row carrying an undeclared
lineage key `qmd_anchor` (contract violation, type 3 — the Increment-3-renames-the-field case).

**Those four test the functions; one of them is additionally driven through the CLI (rev 8, C1).**
The type-2 fixture — a train-split row on a held-out path — is written to a `tmp_path` sidecar and
passed to `eval_split._main(["--check-leak", str(fixture)])`, which must return **exactly 6**. That
is the only assertion in this document that observes the handler block above; the other four stop
at `check_corpus_for_leak`/`assert_no_leak`, which return messages and raise respectively and
therefore cannot see an exit code at all. Task 4 owns it.

---

## 5. `audit.py` — the drift detector (FIRST DELIVERABLE, BLOCKING)

*Satisfies: `[ACCEPT] ORTHOGONAL-2` (promoted to first deliverable), `[ACCEPT] Pre-mortem
mitigations` PM-3, and F1 (the audit never widens the surface; it can only cause a human to
change a table by hand).*

### 5.1 What it diffs

Left side: the 91 recipes' `apis` tokens, classified per §3.2 — *"an independent,
execution-verified statement of what the API actually is"*, pinned to PLR **0.2.2**.
Right side: `coxswain.plr.tool_schema.TOOL_SCHEMA` (20 entries, 13 in `PHASE2_TOOL_NAMES`),
`coxswain.plr.param_namespace.PARAM_NAMESPACE` (13 verbs), and
`overlay_gen.miner.NON_SURFACE_VERB_REASONS` (**28** recorded exclusions — rev 3 corrects
revision 2's 29, W8; the live dict at `training/overlay_gen/miner.py:71-108` holds 4 phantoms +
3 heater-shaker + 5 of the 96-channel family + `return_tips` + `move_tips` + 6 state/query +
4 manual-channel + 4 lifecycle = 28) — all hand-derived from vendored HEAD
`dd79c4c89bc008629a1c598ea614be5e6067d1f9`. Every count in this paragraph is read as a `len()` in
code; none is a literal anywhere in `ingest/`.

**Every finding carries both readings.** No finding may be emitted with a single interpretation:
the version skew (cookbook @ 0.2.2 vs vendored HEAD) makes any difference ambiguous by
construction, and collapsing that ambiguity is exactly what `[ACCEPT] ORTHOGONAL-2` forbids.

**Case policy, pinned once for the whole package (W5).** *Every* comparison between a cookbook
token and a canonical-table key — in `audit.py`, in `gap.py`, in T3's matching rule (§6.4), and in
every evidence-collection site — is **exact and case-sensitive**. Nothing is casefolded anywhere.
Revision 2 pinned this for T3 only, while §5.3 simultaneously counted the CLASSISH token `Mix` as
evidence for the verb `mix` — which exact matching forbids. The two statements could not both be
implemented, and which one a fixer chose would silently change `evidence_classes`, therefore
`adjudicable_digest`, therefore every hand-authored `adjudicated_digest` in the committed
adjudications file. §5.3 resolves it with an explicit two-stage rule rather than by relaxing the
policy: casefold matching exists, is **labelled** in the evidence row, and can never on its own
produce the `CONTESTED` verdict.

### 5.2 Finding shape, and the two hashes (C3)

```python
class MatchMode(str, Enum):                 # W5: how a token was matched to a subject
    EXACT             = "exact"             # case-sensitive string equality (the default)
    CLASSISH_CASEFOLD = "classish_casefold" # CLASSISH token whose casefold equals the verb

@dataclass(frozen=True)
class Evidence:                             # W4: fully declared; rev 2 read two undeclared fields
    recipe_path: str
    token_raw: str
    token_kind: TokenKind
    receiver: str | None                    # None for every non-DOTTED token
    receiver_type: ReceiverType             # NONE for every non-DOTTED token (§3.2)
    member: str
    member_is_in_surface: bool              # member in PHASE2_TOOL_NAMES, exact + case-sensitive
    match_mode: MatchMode

#: R4-B3: the hash serializer, DEFINED. Revision 4 used this helper in three
#: places and defined it in none, while AC-1.7 and AC-1.14 require exact
#: equality against hand-copied outputs of it. Every argument is load-bearing:
#:   sort_keys=True   -- dict insertion order must not reach the digest
#:   separators       -- no incidental whitespace; the compact form is canonical
#:   ensure_ascii=True-- the byte string cannot depend on a non-ASCII payload's
#:                       encoding, and every payload here is ASCII anyway
#:   allow_nan=False  -- a NaN is a loud failure, not non-standard `NaN` bytes
#: It returns BYTES, because sha256 takes bytes. This is deliberately NOT
#: §7.4's artifact serializer (indent=1, ensure_ascii=False): artifacts are for
#: humans to diff, hash inputs are for byte-stability. See §7.4.
def canonical_json(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")

def _sha16(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj)).hexdigest()[:16]

#: R4-B3: NO f-string interpolation of an Enum anywhere in a hash input.
#: f"{kind}" on `class FindingKind(str, Enum)` yields "phantom_verb" on 3.10 and
#: 3.12 but "FindingKind.PHANTOM_VERB" on 3.11 -- an interpreter-version-dependent
#: key space, which is R2-B2's hazard arriving by a route no reviewer of two
#: implementers would catch. Always `.value`, always through canonical_json.
#:
#: R5-W4: the payload is a NAMED function so a test can pin its exact bytes
#: without rebuilding the dict (a second construction would be a second key
#: space -- R2-B2 again). The isinstance guard makes the widening a fixer is
#: most likely to reach for (`kind: str | FindingKind`) a LOUD failure.
def _finding_id_payload(kind: FindingKind, subject: str) -> dict[str, str]:
    if not isinstance(kind, FindingKind):
        raise AuditError(
            "compute_finding_id takes a FindingKind member, not "
            f"{type(kind).__name__}. Widening this parameter to `str | FindingKind` "
            "creates two key spaces for one finding (R2-B2); coerce at the call site."
        )
    return {"kind": kind.value, "subject": subject,
            "rules_version": AUDIT_RULES_VERSION}

def compute_finding_id(kind: FindingKind, subject: str) -> str:
    return _sha16(_finding_id_payload(kind, subject))

#: R5-W4: the TWO subject builders. Subjects are concatenated, never f-string
#: interpolated, so `.value` is applied in exactly one place per kind family and
#: no enum can reach a subject as "ReceiverType.LIQUID_HANDLER". §5.2's subject
#: table below is written in terms of these, not in terms of f-strings.
def dotted_subject(receiver_type: ReceiverType, member: str) -> str:
    return receiver_type.value + "." + member      # receiver_drift / surface_adjacent /
                                                   # unknown_method
def param_subject(in_surface_verb: str, token: str) -> str:
    return in_surface_verb + ":" + token           # param_candidate

@dataclass(frozen=True)
class Finding:
    finding_id: str          # compute_finding_id(kind, subject)   -- identity only (C3)
    adjudicable_digest: str  # _sha16(_adjudicable_view(self))
    kind: FindingKind
    subject: str             # EXACTLY as defined by the table below  (R2-B2)
    blocking: bool
    verdict: str                       # "" for kinds without a verdict enum
    evidence: tuple[Evidence, ...]
    reading_table_is_wrong: str
    reading_api_moved: str
    verdict_hint: str                  # mechanical classification; NEVER a decision

def _adjudicable_view(f: Finding) -> dict[str, Any]:
    """EXACTLY the projection a human adjudicates. Not the raw evidence list."""
    return {
        "kind": f.kind.value,
        "subject": f.subject,
        "rules_version": AUDIT_RULES_VERSION,
        "verdict": f.verdict,
        "blocking": f.blocking,
        # distinct evidence CLASSES, sorted; counts and recipe paths deliberately excluded
        "evidence_classes": sorted({
            (e.token_kind.value, e.receiver_type.value, e.member_is_in_surface,
             e.match_mode.value)
            for e in f.evidence
        }),
        # R2-B2: takes the KIND, because nothing else can parse the subject
        "subject_table_fingerprint": subject_table_fingerprint(f.kind, f.subject),   # §5.7
    }
```

**The serialization was the last unpinned thing in the digest chain, and it is pinned now (rev 5,
R4-B3).** Two defects, both in the same three lines, both of which survive design review because
they look like notation rather than behaviour:

1. **`f"{kind}"` on a `str`-mixin Enum is interpreter-version-dependent.** Revision 4 wrote
   `finding_id: sha256(f"{kind}|{subject}|{AUDIT_RULES_VERSION}")[:16]`. For
   `class FindingKind(str, Enum)`, `format()` resolves to the **value** on 3.10 and on 3.12 but to
   `"FindingKind.PHANTOM_VERB"` on **3.11** — the one release where `str`-mixin `__format__`
   behaves like `Enum.__str__`. Twelve lines below, `_adjudicable_view` already used
   `f.kind.value`, so the document contradicted itself; worse, the *hash* half was the one that
   varied. That is **R2-B2's "two disjoint key spaces" hazard arriving via the interpreter**
   instead of via two implementers — and it is harder to catch, because both implementers write
   the same code and only one of them gets the same answer. `audit_adjudications.json`'s keys are
   hand-copied `finding_id`s and AC-1.7 requires exact equality, so a fixer on 3.11 would produce
   a file that fails G2 on every other machine, with nothing in the failure message pointing at
   Python's version. **Rule: no Enum is ever interpolated into a hash input. Always `.value`,
   always inside `canonical_json`.** The sweep found exactly one other enum reaching a hash
   payload — `_projection()`'s `receiver_type` — and it is safe for a reason worth recording
   rather than assuming: the live `ToolSpec.receiver_type` is a plain `str`
   (`tool_schema.py:41`), not an enum at all.
2. **`canonical_json` was used three times and defined zero times.** It is the input to
   `adjudicable_digest`, to `canonical_tables_fingerprint()` and to `subject_table_fingerprint()`,
   and §7.4 pinned only *artifact* serialization — so key order, separator choice and encoding
   were all a fixer's guess, on three values that get hand-copied into
   `audit_adjudications.json` and `canonical_tables_fingerprint.json` and then compared for exact
   equality by AC-1.7 and AC-1.14. It is defined above, its arguments justified individually, and
   §7.4 now states explicitly that the artifact serializer and the hash serializer differ **on
   purpose** and why.

**What did *not* change: `finding_id` is still identity-only.** C3's decision — identity in one
hash, decision-relevant projection in a second — is untouched. R4-B3 is about how the identity is
*spelled*, not about what it contains, and switching from an f-string to a structured payload
changes no property C3 argued for. It does retire one small argument that was load-bearing under
the old spelling: with `kind` and `subject` as separate JSON members there is no separator for a
subject to smuggle, so cross-kind collisions are impossible by construction rather than by an
argument about `|` (see property 3 below).

**R4-B3's fix had no detector on the interpreters most people run, and rev 6 says so instead of
pretending otherwise (R5-W4).** Revision 5 attached a regression test to R4-B3 in Task 5: *"a unit
test asserts `compute_finding_id` is unchanged across a `FindingKind` passed as the member versus
its `.value`."* Round 5 found that test unwritable against the signature above — passing "its
`.value`" hands `compute_finding_id` a plain `str`, and `kind.value` on a `str` raises
`AttributeError` before any equality is evaluated. Coercing it to run does not rescue it, and the
reason is the uncomfortable one:

> **Under the old buggy spelling, `f"{kind}"` produces the *correct* string on 3.10 and on 3.12.**
> The divergence exists only on 3.11. A behavioural test therefore passes on two of the three
> interpreters *whether or not the bug is present* — which makes the test itself
> interpreter-version-dependent, the exact property R4-B3 was eliminating. There is no behavioural
> test that can close this class. Round 5's own probe offers two candidate pins; neither is
> interpreter-independent for the `f"{kind}"` case specifically, and saying which one is "intended"
> would have been answering a narrower question than the one the finding raises.

So the remedy is **structural**, in the same move R4-W9 made when it replaced the unwritable
`python -O` probe with a static ban:

1. **No enum is interpolated anywhere in the identity path, because there are no interpolations
   left in it.** `_finding_id_payload` builds a dict; `dotted_subject` and `param_subject`
   concatenate strings with `.value` applied in exactly one place each. A reader checks three short
   functions rather than trusting a lint over an undecidable dataflow question. This also closes a
   hazard round 5 did not name: the *subject* strings were f-string-built too
   (`f"{receiver_type.value}.{member}"`), so a dropped `.value` there would have produced
   `ReceiverType.LIQUID_HANDLER.use_channels` on 3.11 — the same two-key-space failure one field
   over from the one R4-B3 fixed, in the string that keys `audit_adjudications.json`.
2. **The parameter stays `FindingKind` and the widening is forbidden in code, not in prose.**
   `_finding_id_payload` raises `AuditError` on a non-member. Round 5 predicted the likely fixer
   response to the broken test — widen to `str | FindingKind` — and that response reopens R2-B2's
   two-key-spaces hazard: `compute_finding_id("phantom_verb", …)` and
   `compute_finding_id(FindingKind.PHANTOM_VERB, …)` would agree today and diverge the first time
   someone passes a typo'd string. A typed error at the boundary makes the widening a red test.
3. **The tests that replace the unwritable one all fire on every interpreter** — a byte pin on
   `canonical_json(_finding_id_payload(...))`, the `AuditError` above, and a full-run sweep
   asserting no `b"FindingKind."` or `b"ReceiverType."` reaches any payload or subject. Task 5
   states all three. The sweep is *vacuous on 3.10/3.12 and live on 3.11*, and it is labelled that
   way there rather than being presented as universal coverage.

**What `subject` holds, per kind (R2-B2).** Revision 2 never said, for any kind — yet `subject` is
the input to `finding_id`, to `adjudicable_digest`, to `subject_table_fingerprint()`, and it is
the **key of the hand-authored `audit_adjudications.json`**. Two implementers would have produced
two disjoint key spaces, and the committed adjudications would have matched neither reliably. The
table is exhaustive over the ten `FindingKind`s:

| kind | `subject` is | example | occurs today? |
|---|---|---|---|
| `phantom_verb` | the verb name — a `TOOL_SCHEMA` key | `mix` | **yes**, 4 (§5.4.1) |
| `no_backend_verb` | the verb name — a `TOOL_SCHEMA` key | `shake` | **yes**, 3 (§5.3) |
| `schema_unmentioned` | the verb name — a `TOOL_SCHEMA` key | `stamp` | **yes** — `stamp` is a `TOOL_SCHEMA` key with zero occurrences in the 91 recipes (verified) |
| `receiver_drift` | `dotted_subject(observed_receiver_type, member)` | `plate_reader.aspirate` — **constructed** | **no, 0 today.** §3.3 verified that *no* receiver maps to `plate_reader`, so this example cannot be produced from the live file. It shows the subject *format*, which is what the table is for |
| `surface_adjacent` | `dotted_subject(receiver_type, member)` | `liquid_handler.use_channels` (line 152) | **yes**, 5 (§5.4.1) |
| `unknown_method` | `dotted_subject(receiver_type, member)` | `other.get_top_item` (line 192, `ResourceStack.get_top_item`), `none.pick_up_resource` (lines 397, 447 — a bare IDENT, hence `ReceiverType.NONE`) | **yes**, both |
| `param_misattributed` | the bare param token | `vols` — a **near-miss that does not fire** | **no, 0 today.** `vols` clears the first clause (it is `aspirate`/`dispense`'s `plr_arg`) and fails the second: lines 427/437 name no in-surface verb at all (§5.4.1). Kept because it is the closest live case and shows why the second clause matters |
| `param_candidate` | `param_subject(in_surface_verb, ident_token)` — **one finding per (verb, token) pair**, see the multi-verb rule below | `aspirate:backend_kwargs` (line 277: `"backend_kwargs, STARBackend.aspirate, jet, blow_out, lld_mode, surface_following_distance"` — `STARBackend.aspirate` supplies the in-surface verb; `backend_kwargs` is neither of `aspirate`'s declared `source`/`volume_ul` nor its `resources`/`vols`) | **yes** |
| `unclassified_token` | the raw `OTHER`-kind token, verbatim | `cor_96_wellplate_360uL_Fb` | **yes** |
| `unmapped_receiver` | the raw receiver string, verbatim | `pr` — **constructed** | **no, 0 today, and 0 by gate.** §3.3 rule 2's two-way equality *requires* zero unmapped receivers, so a live example is structurally impossible while the gate is green. The kind exists for the first cookbook that adds a receiver, which is the moment the advisory row is the point |

**Why this column was split (rev 4, R3-W2).** Revision 3's single column was headed *"example
(from the live cookbook)"* and four of its ten entries could not be produced from it:
`plate_reader.aspirate` (no `plate_reader` receiver exists), `vols` (verified not to misattribute),
`aspirate:flow_rates` (line 122 names no in-surface verb, so nothing makes it a *candidate*), and
`backends/chatterbox` (which §3.3's rebuilt table *contains*, so it is by definition not
unmapped). That is W10's defect — an illustrative table wrong about the file it describes —
recurring inside R2-B2's own fix, and against the header banner's derive-never-hand-list rule. Two
examples are now real and cited by line; the three kinds whose live count is **0** say so, because
"here is an example" and "here is the shape a subject takes" are different claims and only the
second one was ever true for them.

**`param_candidate` when a recipe names two or more in-surface verbs (rev 5, R4-W7).** The subject
`param_subject(in_surface_verb, ident_token)` presumes the recipe supplies *one* in-surface verb. Three live
recipes supply two or more, so the presumption is false and the rule has to be stated:

- **"In-surface verb of a recipe"** is defined exactly once, by §6.4's T3 matching rule: the set of
  distinct `ApiToken.member` values over the recipe's **method-shaped** tokens that are in
  `PHASE2_TOOL_NAMES`, compared **exact and case-sensitive** (§5.1). Nothing else counts — not
  `CLASSISH` tokens, not `path`, not `title`.
- **The rule is the full cross product: one finding per (in-surface verb, IDENT token) pair.** For
  a recipe with *v* in-surface verbs and *t* qualifying IDENT tokens, the audit emits *v · t*
  `param_candidate` findings, each with its own subject, its own `finding_id` and its own
  evidence row. There is **no** "pick the first verb" or "pick the nearest verb" rule, because
  `recipes.yml` has no ordering semantics — `apis` is an unordered comma-separated set (§3.2) and
  any positional rule would be reading structure into a string that has none.
- **Live case, worked (recipes.yml:432).**
  `"itertools.groupby, sorted, lh.aspirate, lh.dispense, use_channels, multi-dispense"` →
  in-surface verbs `{aspirate, dispense}` (both `lh.`-receivered, both method-shaped, both in
  `PHASE2_TOOL_NAMES`); qualifying IDENT tokens `{sorted, use_channels}` (`itertools.groupby` is
  DOTTED, `multi-dispense` is `_PUNCT_TOKEN` → `OTHER`). Four findings:
  `aspirate:sorted`, `aspirate:use_channels`, `dispense:sorted`, `dispense:use_channels`.
  Lines 207 and 452 also name two-plus in-surface verbs but produce **no** `param_candidate` at
  all — 207's non-verb tokens are `CLASSISH`/`_PUNCT_TOKEN`, and 452 is five DOTTED tokens with no
  IDENT among them — so the cross product is empty there, which is the rule working, not an
  exception to it.
- **Why the cross product rather than a disambiguation rule.** `param_candidate` is **advisory**
  (§5.4), so multiplicity costs a few extra rows in a ranked advisory table and costs the blocking
  census — and therefore the adjudication load — exactly nothing. A disambiguation rule would have
  to make a claim the file does not support (that `use_channels` is a candidate parameter of
  `aspirate` rather than of `dispense`) in order to avoid an output that is merely slightly
  longer. The multiplicity is also the honest reading: with two verbs present, both readings are
  live and the advisory table should show both.
- **F6 consequence, stated because R4-W7 raises it.** The subject set is a deterministic function
  of the file (a cross product over two sorted sets), and §7.4 sorts `audit_findings.jsonl` by
  `finding_id`, so the artifact is byte-identical on re-run. Multiplicity does not threaten
  determinism; an *implicit* verb choice would have, because two implementers would choose
  differently.

Three properties this shape was chosen for, each of which a plausible alternative loses:

1. **The dotted kinds key on `receiver_type`, not on the raw receiver.** `lh.head` and
   `LiquidHandler.head` are the *same* question — "is `head` a liquid-handler surface API?" — and
   must be one finding with one adjudication. Keying on the raw receiver would split them into two
   and force the same rationale to be written twice.
2. **`param_misattributed` keys on the bare token, not on `(token, declaring_verb)`.** `vols` is
   declared by both `aspirate` and `dispense`; `source` by `aspirate`, `transfer` and `stamp`.
   A pair key would emit two or three findings about one token and one decision.
3. **The separator differs by kind on purpose** (`.` for receiver-qualified members, `:` for
   verb-qualified params). Since `finding_id` hashes a **structured** payload whose `kind` and
   `subject` are separate JSON members, cross-kind collisions are impossible by construction —
   there is no delimiter for a subject to smuggle. *Rev 5 (R4-B3): revision 4 said "since
   `finding_id` hashes `kind|subject`", which was true of its `f"{kind}|{subject}|…"` expression
   and made the claim rest on an argument about separators — one that a subject containing `|`
   would have to be checked against, and `unclassified_token`'s subject is a raw `OTHER` token,
   which `_PUNCT_TOKEN` permits `|` in. The structured hash removes the question rather than
   answering it.* The different separators are for the *human* reading the adjudications file, who
   should be able to tell `liquid_handler.use_channels` from `aspirate:backend_kwargs` at a glance.

**Why two hashes, and why revision 1's single hash was the review's most severe finding.**

`finding_id` hashes identity only (kind + subject + rules version). That property is worth
keeping: re-running after the cookbook adds an unrelated recipe must not churn ids and invalidate
every committed adjudication. But revision 1 stopped there, and identity-only means the
adjudication is bound to *the finding's name*, not to *what was adjudicated*. Concretely: `mix` is
adjudicated today as `NO_EVIDENCE`-adjacent `KWARG_ONLY` ("our phantom claim is supported"). The
cookbook adds one recipe naming `lh.mix`. The finding flips to `CONTESTED` — *"the cookbook
asserts it as a method on a receiver we model; our phantom claim is DISPUTED"* — the most
consequential outcome the audit can produce. `finding_id` is unchanged, the stale adjudication
still matches, `--gate` exits 0, and corpus generation proceeds on a table the audit has just
disputed. That is PM-3's failure — a discrepancy that "sat in a report nobody owned" —
reconstructed inside PM-3's own mitigation.

`adjudicable_digest` fixes it by covering the decision-determining projection:

- **`verdict` and `blocking`** — a flip changes the digest, so the adjudication goes stale and the
  gate blocks with reason `stale_digest`.
- **`evidence_classes`** — the *distinct set* of (token kind, receiver type, in-surface) triples,
  which is exactly what the verdict function reads. Adding a second bare-IDENT mention of `mix`
  changes nothing (the class is already present) — the anti-churn property survives. Adding the
  *first* DOTTED `lh.mix` adds a new class and invalidates — correctly, because it is exactly the
  evidence that changes the reading. Recipe paths and counts are excluded so that unrelated
  cookbook growth is inert.
- **`subject_table_fingerprint`** — the canonical-table **lookup result** for this subject,
  misses included (§5.7). If a human acts on an adjudication by editing `mix`'s `TOOL_SCHEMA` row,
  `mix`'s adjudication goes stale and must be re-made against the new table; every *other*
  finding's adjudication survives, because the fingerprint is per-subject rather than global. (A
  global fingerprint would have worked too, but would force re-adjudicating **all nine** blocking
  findings — §5.4.1's census, not revision 2's "seven" — after any table edit: churn without
  information.)
  **Rev 4 (R3-B1) — this bullet's scope, stated exactly.** The fingerprint is subject-distinct for
  **all ten** kinds, and it goes stale under a table edit for **some** of them. `phantom_verb` —
  the example above — is one where it does. `surface_adjacent` is one where it **does not**, and
  that is 5 of the 9 blocking findings: a `surface_adjacent` finding exists *precisely because*
  all three memberships are `False`, so the edit that would flip one of them **deletes the
  finding** instead of staling it. §5.7's table-sensitivity table gives the per-kind answer and
  names what detects the deletion instead (AC-1.14 and the census pin). Revision 3 claimed the
  anti-staleness property for the whole digest and worked its only example on the one kind where
  the claim is vacuous.
- **`match_mode`** (rev 3, W5) — so that a subject whose only evidence is a CLASSISH casefold
  match is digest-distinguishable from one with an exact match. Without it, §5.3's `Mix`/`mix`
  distinction would be invisible to the digest, and a change in the case policy would silently
  revalidate a stale adjudication.

Evidence carries `recipe_path`, never `title` (§3.1).

### 5.3 The phantom/no-backend partition — machine-derived (C4)

Revision 1 asserted `audit.py` emits *"exactly four `phantom_verb` findings, always"*. But
`tool_schema.py` carries `experimental=True` on **seven** entries — the four phantoms plus
`set_temperature`, `shake`, `stop_shaking` (heater-shaker verbs excluded for a *no-backend*
reason, not a phantom one) — and the distinction between the two groups exists **only in a Python
comment**. "Exactly four" was therefore an unbacked constant that would silently become wrong the
moment upstream marked an eighth entry experimental.

`training/ingest/data/experimental_partition.json`:

```jsonc
{
  "experimental_partition_version": "1",
  "phantom": {
    "mix": "no such method on vendored LiquidHandler @ dd79c4c89; upstream models mixing via aspirate/dispense mix kwarg lists",
    "blow_out": "no such method; modeled via blow_out_air_volume kwargs",
    "touch_tip": "no such method vs vendored HEAD",
    "dispense_to_waste": "no such method vs vendored HEAD"
  },
  "no_backend": {
    "set_temperature": "vendored HeaterShaker method exists; no praxis backend wiring (defender R5)",
    "shake": "same",
    "stop_shaking": "same"
  }
}
```

Loader invariants (raise `AuditError`):

- `set(phantom) & set(no_backend) == {}`;
- `set(phantom) | set(no_backend) == {n for n, s in TOOL_SCHEMA.items() if s.experimental}`;
- every key is also present in `overlay_gen.miner.NON_SURFACE_VERB_REASONS` (a second, independent
  table agreeing on the exclusion).

`PHANTOM_VERBS` and `NO_BACKEND_VERBS` are then derived, and AC-1.6's counts are `len()` calls
rather than literals. An eighth `experimental=True` entry appearing upstream **fails the load**,
which is F5's "nothing silently dropped" applied to the audit's own census.

`audit.py` emits one `phantom_verb` finding per `PHANTOM_VERBS` member (blocking, always, even
when the evidence set is empty) and one advisory `no_backend_verb` finding per `NO_BACKEND_VERBS`
member (so the other three experimental entries are counted, not invisible).

```python
class PhantomVerdict(str, Enum):
    CONTESTED   = "contested"     # >=1 DOTTED token <recv>.<verb> where receiver_type is
                                  # liquid_handler or plate_reader => the cookbook asserts it
                                  # as a METHOD on a receiver we model. Our phantom claim is
                                  # DISPUTED. blocking = True.
    KWARG_ONLY  = "kwarg_only"    # appears only as bare IDENT or CLASSISH, or as an IDENT
                                  # co-occurring with kwarg-shaped siblings => consistent with
                                  # "upstream models this via kwargs, not a method".
                                  # Our phantom claim is SUPPORTED. blocking = True.
    NO_EVIDENCE = "no_evidence"   # absent from all 91 recipes. blocking = True:
                                  # "no evidence" is not "confirmed".
```

**Phantom-verb evidence collection is a two-stage rule (W5).** The package-wide case policy
(§5.1) is exact and case-sensitive, so the CLASSISH token `Mix` does **not** equal the verb `mix`
and cannot be swept in as evidence by string equality. Revision 2's §5.3 nonetheless counted it,
with no rule stated. Rev 3 states the rule instead of relaxing the policy:

1. **Primary matches — exact, case-sensitive.** Every token whose `member` equals the verb name
   exactly. These carry `match_mode: exact` and they alone determine the verdict.
2. **Corroborating matches — CLASSISH casefold.** A `CLASSISH` token whose casefold equals the
   verb's casefold is recorded as evidence with `match_mode: classish_casefold`. Because a CLASSISH
   token has no receiver (`ReceiverType.NONE`, §3.2), it can never assert method-hood on a receiver
   we model, so a corroborating match can support `KWARG_ONLY` and can **never** produce
   `CONTESTED`. That asymmetry is **enforced in code by a raised `AuditError`**, not left to the
   verdict function's shape. *(Rev 6, R5-S2: revision 5 wrote "asserted in code" here. §7.3(a) now
   statically bans `ast.Assert` under `training/ingest/`, so the word is load-bearing and this
   sentence is one of the four places it still read as an instruction to write a bare `assert`.)*

No other casefolding exists anywhere in the package.

**Expected verdicts against the current `recipes.yml`, stated here so a fixer can write the test
first** (all four pinned in `training/tests/test_ingest_audit_phantoms.py`):

| verb | cookbook evidence | expected verdict |
|---|---|---|
| `mix` | recipe `part1/04_pipetting.qmd#mix`, `apis: "Mix, mix, surface_following_distance"` — `mix` is IDENT (**primary**, `exact`); `Mix` is CLASSISH (**corroborating**, `classish_casefold`); sibling `surface_following_distance` is a known kwarg. **No `lh.mix` anywhere.** | `KWARG_ONLY` |
| `blow_out` | recipe `part2/12_hardware.qmd#backend-kwargs`, `apis: "backend_kwargs, STARBackend.aspirate, jet, blow_out, lld_mode, surface_following_distance"` — bare IDENT among kwargs; and `part1/04_pipetting.qmd#flow-height` names `blow_out_air_volume` | `KWARG_ONLY` |
| `touch_tip` | absent from all 91 recipes | `NO_EVIDENCE` |
| `dispense_to_waste` | absent from all 91 recipes | `NO_EVIDENCE` |

The mechanical answer is that the cookbook's own evidence is **consistent with the phantom
classification** — but `verdict_hint` is a hint. The adjudication (§5.5) is where a human writes
down which reading applies, and `KWARG_ONLY`/`NO_EVIDENCE` are `blocking: true` for exactly the
reason PM-3 gives: a finding that agrees with us still needs an owner who says so in writing.

### 5.4 The other finding kinds, and the bounded blocking set

```python
class FindingKind(str, Enum):
    PHANTOM_VERB       = "phantom_verb"        # §5.3, exactly len(PHANTOM_VERBS), ALWAYS blocking
    RECEIVER_DRIFT     = "receiver_drift"      # blocking
    SURFACE_ADJACENT   = "surface_adjacent"    # blocking
    PARAM_MISATTRIBUTED= "param_misattributed" # blocking
    UNKNOWN_METHOD     = "unknown_method"      # advisory
    SCHEMA_UNMENTIONED = "schema_unmentioned"  # advisory
    PARAM_CANDIDATE    = "param_candidate"     # advisory
    UNCLASSIFIED_TOKEN = "unclassified_token"  # advisory (F5: OTHER-kind tokens, counted)
    NO_BACKEND_VERB    = "no_backend_verb"     # advisory (C4: the 3 non-phantom experimentals)
    UNMAPPED_RECEIVER  = "unmapped_receiver"   # advisory (C9: receiver outside the exact map)

#: The ONE place blocking-ness is declared. `Finding.blocking` is membership in this
#: set, never a per-finding boolean a caller can set. §5.7's scope="none" guard and
#: AC-1.6's blocking_census both read it.
BLOCKING_KINDS: Final[frozenset[FindingKind]] = frozenset({
    FindingKind.PHANTOM_VERB, FindingKind.RECEIVER_DRIFT,
    FindingKind.SURFACE_ADJACENT, FindingKind.PARAM_MISATTRIBUTED,
})
```

- **`RECEIVER_DRIFT` (blocking)** — a method-shaped DOTTED token `X.v` where `v ∈ TOOL_SCHEMA` but
  `X`'s `receiver_type` (§3.3 exact map) differs from `TOOL_SCHEMA[v].receiver_type`.
  **0 today** (§5.4.1).
- **`SURFACE_ADJACENT` (blocking)** — a method-shaped member absent from both `TOOL_SCHEMA` and
  `NON_SURFACE_VERB_REASONS` **whose receiver_type is `liquid_handler` or `plate_reader`**.
  **5 today**, all five named in §5.4.1 — revision 2 accounted for none of them.
- **`PARAM_MISATTRIBUTED` (blocking)** — an IDENT token equal to some `ParamSpec.plr_arg` or
  `ParamSpec.name` in `PARAM_NAMESPACE`, appearing in a recipe that names a *different*
  in-surface verb and never the declaring one. **0 today** (§5.4.1).
- **`UNKNOWN_METHOD` (advisory)** — every method-shaped member in neither table **whose
  `receiver_type` is not `liquid_handler`/`plate_reader`** (those are `SURFACE_ADJACENT`'s, above);
  a bare `IDENT` qualifies, with `ReceiverType.NONE` (§3.2), which is why `none.pick_up_resource`
  is a live subject (§5.2). Reported with its recipe frequency and ranked descending, this table
  **is** `ORTHOGONAL-3`'s surface-expansion roadmap, delivered by Increment 1 at zero marginal
  cost. *Rev 6 (R5-S4): "every **other** method-shaped member" was the old wording, and "other"
  was undefined with respect to the param kinds — see the partition note below.*
- **`SCHEMA_UNMENTIONED` (advisory)** — `TOOL_SCHEMA` verbs with zero cookbook mentions.
- **`PARAM_CANDIDATE` (advisory)** — IDENT tokens co-occurring with an in-surface verb that are
  not that verb's declared `name`/`plr_arg`. **One finding per (in-surface verb, IDENT token)
  pair** — the full cross product, with "in-surface verb of a recipe" defined by §6.4's T3
  matching rule and the live two-verb case worked through in §5.2 (rev 5, R4-W7). Advisory, so the
  multiplicity costs rows in a ranked table and costs the blocking census nothing.

**The ten kinds are NOT a partition of tokens, and rev 6 says so where the advisory tables are
described (R5-S4).** Whether one token can produce findings of several kinds was never stated, and
R4-W7's cross product made the overlap concrete. **It can, and it does today.** Verified live at
`recipes.yml:432` — `"itertools.groupby, sorted, lh.aspirate, lh.dispense, use_channels,
multi-dispense"`:

| token | kind(s) it produces | subject(s) |
|---|---|---|
| `sorted` | `unknown_method` **and** `param_candidate` ×2 | `none.sorted`; `aspirate:sorted`, `dispense:sorted` |
| `use_channels` | `unknown_method` **and** `param_candidate` ×2 | `none.use_channels`; `aspirate:use_channels`, `dispense:use_channels` |
| `itertools.groupby` | `unknown_method` only | `other.groupby` |
| `multi-dispense` | `unclassified_token` only | `multi-dispense` |

So a reader of the ranked `unknown_method` table and a reader of the `param_candidate` table are
looking at the same two tokens from two angles **by design**: the first asks *"is this a verb our
surface should model?"*, the second asks *"is this a parameter of a verb our surface already
models?"*, and a bare identifier co-occurring with in-surface verbs is a legitimate candidate for
both readings. Neither table is a subset of the other and neither de-duplicates against the other.

**Why this costs the blocking census nothing.** Every overlap that exists today is
**advisory-to-advisory**. The four **blocking** kinds are mutually exclusive per subject by
construction, and the exclusivity is structural rather than enforced: `receiver_drift` requires the
member to be **in** `TOOL_SCHEMA` while `surface_adjacent` requires it in **neither** canonical
table (so no member can satisfy both); `param_misattributed` ranges over IDENT tokens that match a
`ParamSpec`, which by §5.4's second clause requires the recipe to name a *different* in-surface
verb; and `phantom_verb` is emitted **per `TOOL_SCHEMA` verb**, not per token, so it is not in the
per-token space at all. No token is ever counted twice in `blocking_census.json`, and §5.4.1's
derivation is unaffected. Recorded as §12 item 15.

**Why the blocking set is bounded, and why that is not a weakening of PM-3.** Blocking is
restricted to findings whose resolution *could change a canonical table row* — the four
phantoms plus three small, high-signal classes. Making all ~200+ advisory tokens blocking would
recreate PM-2's failure in mirror image: a gate so expensive that the first person to hit it
waives it, after which G2 is decoration. The advisory classes are still **counted, ranked, and
committed** (F5).

### 5.4.1 The complete blocking census over the current `recipes.yml` (R2-B1)

Revision 2 asserted "seven blocking findings" in §5.2 and seeded four adjudications in Task 6.
Both are wrong against the live file, and the combination made AC-1.7 **unsatisfiable**: the AC
requires an adjudication for every blocking finding, and the task that seeds them provided fewer
than exist. This is C4's unbacked-constant defect — "exactly four phantoms", asserted against a
table that says seven — relocated into C3's own fix, which is precisely the shape round 1 punished.

The census below is **derived**, kind by kind, from the DOTTED tokens of the 91 recipes against
the live `TOOL_SCHEMA` (20 entries), `NON_SURFACE_VERB_REASONS` (28 entries) and `PARAM_NAMESPACE`
(13 verbs). The derivation is shown so a reviewer can check it against the file rather than
against this document's word.

**`phantom_verb` — 4, machine-derived from `experimental_partition.json` (§5.3).**
`mix`, `blow_out`, `touch_tip`, `dispense_to_waste`.

**`surface_adjacent` — 5.** The kind fires on a method-shaped member absent from *both* tables
whose `receiver_type` is `liquid_handler` or `plate_reader`. Per §3.3, exactly three receivers map
to `liquid_handler` (`lh`, `LiquidHandler`, `STARBackend`) and **none** to `plate_reader`, so the
candidate set is every distinct member appearing after one of those three. Subtracting the
members that *are* in a table (`aspirate`, `dispense`, `transfer`, `move_plate`, `move_lid`,
`drop_tips`, `discard_tips`, `pick_up_tips` from `TOOL_SCHEMA`; `summary`, `setup`, `stop`,
`return_tips`, `get_mounted_tips`, `probe_tip_inventory`, `consolidate_tip_inventory`,
`move_tips`, `prepare_for_manual_channel_operation`, `move_channel_x/y/z`, `update_head_state`
from `NON_SURFACE_VERB_REASONS`) leaves exactly:

| # | subject | evidence (recipes.yml lines) | why it is in neither table | anticipated reading |
|---|---|---|---|---|
| 1 | `liquid_handler.use_channels` | 152 (`lh.use_channels`) | a real vendored context-manager method; `param_namespace.py`'s scope note calls `use_channels` an out-of-surface expert kwarg but `NON_SURFACE_VERB_REASONS` never records the *method* | `table_is_wrong` — the exclusion table has a gap |
| 2 | `liquid_handler.use_tips` | 232 (`lh.use_tips`) | real vendored async context manager; no exclusion recorded | `table_is_wrong` |
| 3 | `liquid_handler.probe_tip_presence_via_pickup` | 212, 252 | the exclusion table records `probe_tip_inventory` and `consolidate_tip_inventory` but not this sibling | `table_is_wrong` |
| 4 | `liquid_handler.clear_head_state` | 467 | the table records `update_head_state` but not its counterpart | `table_is_wrong` |
| 5 | `liquid_handler.head` | 392, 467 | `head` is an **attribute**, not a method — but `method_shaped()` cannot tell them apart from `recipes.yml`, which carries no call syntax | `token_is_not_a_method` (§5.5's new reading) |

The anticipated readings are **guidance, not pins.** §5.3 pins *verdicts*, which are mechanical;
readings are the human's contribution and Task 6 is where they are written. What is pinned is the
kind, the subject, the evidence and `blocking: true`.

**`receiver_drift` — 0.** The kind requires a DOTTED token `X.v` with `v ∈ TOOL_SCHEMA` and
`receiver_type(X) != TOOL_SCHEMA[v].receiver_type`. Every such token in the file has an `lh`,
`LiquidHandler` or `STARBackend` receiver against a `liquid_handler` schema entry —
`STARBackend.aspirate` (line 277) is the only non-`lh` case and it agrees. The bare IDENT
`move_plate` (line 332), `pick_up_tips`/`drop_tips`/`aspirate`/`dispense` (line 387) are not
DOTTED and so cannot drift.

**`param_misattributed` — 0.** The kind requires a bare IDENT equal to a `ParamSpec.name` or
`plr_arg`, in a recipe that names a *different* in-surface verb and never the declaring one. Three
tokens clear the first clause and all three fail the second: `target_vols` (line 147) appears
alongside `lh.transfer`, which **is** its declaring verb; `vols` (lines 427, 437) and `resource`
(line 327) appear in recipes that name **no** in-surface verb at all.

**Total: 9 blocking findings.** `audit_report.json` records the **observed** `blocking_census`
`{"phantom_verb": 4, "surface_adjacent": 5, "receiver_drift": 0, "param_misattributed": 0}`, and
the same object is committed to **`training/ingest/data/blocking_census.json`** (§5.6d) where the
gate can read it. AC-1.6's test asserts observed == committed; it holds no literal of its own.

`training/ingest/data/blocking_census.json` (computed, §5.6d):

```jsonc
{
  "blocking_census_version": "1",
  "audit_rules_version": "1",
  "derived_under_source_sha": "<the registry pinned_sha at emit time>",  // PROVENANCE ONLY
  "census": {"phantom_verb": 4, "surface_adjacent": 5,
             "receiver_drift": 0, "param_misattributed": 0}
}
```

`load_blocking_census()` raises `AuditError` unless `set(census) == {k.value for k in
BLOCKING_KINDS}` — so promoting a kind to blocking (or demoting one) without updating this file is
a loud failure, not a missing row. **Only `census` and `audit_rules_version` are asserted by any
test.** `derived_under_source_sha` is there so a human reading a `census_drift` line can tell which
cookbook the pin was taken against; asserting it would make every legitimate upstream move a red
test, which is the recomputation-as-authority inversion C10 rejected.

**Round 3 re-derived this entire census from the live files and it reproduced exactly** — the
26 distinct method-shaped members on the three `liquid_handler` receivers partition as 8
`TOOL_SCHEMA` + 13 `NON_SURFACE_VERB_REASONS` + these 5; the 24 `lh.` / 2 `LiquidHandler.` /
1 `STARBackend.` member counts match; and `receiver_drift = 0` and `param_misattributed = 0`,
which revision 2 asserted without deriving, were both confirmed against the file. The three prose
counts above are therefore a **derivation a reviewer can re-run**, not the authority: the committed
`blocking_census.json` is the authority, and this subsection is how you check it.

**The structural bound, which is what §5.4's "bounded" claim should have rested on.** The blocking
set is bounded above by `|PHANTOM_VERBS|` (4, machine-derived) plus the number of distinct
method-shaped members appearing on a `liquid_handler`/`plate_reader` receiver — **at most 27** in
the current file (24 distinct `lh.` members, 2 `LiquidHandler.`, 1 `STARBackend.`) — plus the
distinct param tokens, of which the whole `PARAM_NAMESPACE` union contains 25. It is bounded by
the *cookbook's* size against tables of fixed size, not by an assertion that the number is small.
Revision 2 said "three small, high-signal classes" and left "small" unquantified, which is how a
five-member class stayed invisible through a whole revision.

**Why `SURFACE_ADJACENT` stays blocking, considered and decided.** Demoting it to advisory would
make the census 4 and Task 6's four seeded adjudications correct as written — which is a reason to
distrust the move, not to make it. These five are the highest-signal output the audit can produce:
each is a real vendored liquid-handler API that the execution-verified cookbook teaches and that
*neither* canonical table mentions, which is exactly the drift `[ACCEPT] ORTHOGONAL-2` promoted
the audit to first deliverable to detect. Demoting a finding class to avoid writing five
rationales is PM-2's waived-gate failure arriving through the spec instead of through a person.
Nine hand-written adjudications is a tractable one-session load and it is the load PM-3 asks for.

**None of the five is expected to be resolved by editing a table inside Increment 1.** The
anticipated action for all five is `file_backlog_item`, not `edit_table_by_hand`: adding names to
`NON_SURFACE_VERB_REASONS` changes the canonical-tables fingerprint (§5.7 hashes
`sorted(NON_SURFACE_VERB_REASONS)`), which turns AC-1.14 red and demands a regeneration Increment 1
cannot perform (floor_gen and overlay_gen are teacher-gated, F8). The audit's job here is to make
the gap **owned and visible**, not to close it.

**Round 3 was asked directly whether that deferral is a defeated gate, and adjudicated it
HONEST AND CORRECTLY SCOPED (rev 4, R3-W8).** The finding is recorded here rather than
paraphrased, because "we deferred it and the reviewer agreed" is exactly the sentence a later
reader should be able to check:

- PM-3's mitigation is **ownership in writing**, not remediation. An adjudication that says "this
  is a real gap, here is the backlog item" discharges PM-3; one that says nothing does not.
- `file_backlog_item` is **forced, not chosen for convenience.** AC-1.14 makes an in-increment
  canonical-table edit structurally fail — the fingerprint goes red, and silencing it requires
  asserting in a reviewable diff that five named artifacts were built under a table they were not
  (§5.7). The F8 teacher gate blocks the regeneration that would legitimise the edit. So the
  convenient path is closed by mechanisms that exist for other reasons.
- The gap can be neither **closed nor widened silently**: `blocking_census.json` pins
  `surface_adjacent: 5`, and AC-1.14 fires on any table edit.
- §5.4.1 above considers and rejects the genuinely convenient alternative (demote the kind to
  advisory), on the grounds that it would make Task 6's four seeded adjudications correct — which
  is a reason to distrust the move rather than to make it.

**The residual is warning-level and is closed in two places, not waved at.** Round 3's remaining
objection was that `action_ref` is an unvalidated free string and that no §12 item named who
closes the five backlog items — so "owned and visible" rested on one human writing one unchecked
string once. §5.5 now constrains `action_ref` to a closed prefix grammar and states plainly that
its *resolvability* is unverified by design; **§12.12** names the downstream owner and the timing.

### 5.5 G2 — the gate mechanics

`training/ingest/data/audit_adjudications.json` (committed, hand-authored — one of the **six**
hand-authored files in `data/` per §5.6(d), and the only one authored **against the audit's own
output** rather than against the world):

*Rev 4 (R3-W5): revision 3 called this "the only hand-authored artifact in Increment 1 besides the
registry", which contradicts §5.6(d)'s own table — `license_rules.json`,
`experimental_partition.json`, `import_closure_allowlist.json` and (per R3-B3)
`receiver_aliases.json` are all hand-authored too. The distinctive property is the one now stated:
every other hand-authored file records a fact about an external artifact, while this one records a
human's decision about a finding this package produced.*

```jsonc
{
  "audit_rules_version": "1",
  "adjudications": {
    "<finding_id>": {
      "adjudicated_digest": "<adjudicable_digest at the time of adjudication>",   // C3
      "reading": "table_is_wrong | api_moved_0_2_2_to_head | cookbook_token_not_an_api | token_is_not_a_method | confirms_current_table",
      "rationale": "<>= 40 chars, states which of the two readings applies and why>",
      "action": "none | file_backlog_item | edit_table_by_hand",
      "action_ref": "<backlog id / commit sha, empty iff action == none>",
      "impact": {                                    // REQUIRED iff action == edit_table_by_hand (C13)
        "tables_touched": ["coxswain/src/coxswain/plr/tool_schema.py"],
        "invalidated_artifacts": ["training/assemble/out/corpus_p25.jsonl", "..."],
        "regeneration_backlog_ref": "<backlog id>"
      },
      "adjudicated_by": "<name>",
      "adjudicated_on": "YYYY-MM-DD"
    }
  }
}
```

**`token_is_not_a_method` is new in rev 3 (R2-B1).** It reads: *"the member names a real vendored
attribute, property or module rather than a callable verb; `method_shaped()` cannot distinguish
them from `recipes.yml`, which carries no call syntax."* It exists because `liquid_handler.head`
needs it and none of the four existing readings fits: `head` **is** a real API (so
`cookbook_token_not_an_api` is false), it has not moved between 0.2.2 and HEAD (so
`api_moved_…` is false), our table is not wrong to omit an attribute from a *verb* table (so
`table_is_wrong` is false), and the current table does not positively confirm anything about it
(so `confirms_current_table` is false). Forcing one of the four would have recorded a false
statement in a file whose whole purpose is to record true ones. The same reading will apply to
`manifest.json` → member `json` and `backends/chatterbox.py` → member `py` when a future cookbook
puts one of them on a modelled receiver; today they are advisory (§3.3 rule 3).

**The gate's evaluation order, and what happens at each step (rev 5, R4-W10).** Revision 4's §5.5
described three completeness checks and exit 2, and never mentioned loading the census at all —
even though AC-1.7 and §9's G2 row both require `--gate` to read `data/blocking_census.json` and
print `census_drift`. A missing census file therefore had no defined behaviour, which on a fresh
checkout mid-Task-5 (the file is created there) means an unhandled `FileNotFoundError` or, worse,
a `KeyError` deep inside the drift comparison. The order is:

| # | step | failure behaviour |
|---|---|---|
| 1 | `load_recipes()` → `run_audit()` | `CookbookUnavailable` → exit **5**, printing `default_recipes_path()` (§7.5). Nothing below runs. |
| 2 | `load_blocking_census()` | file **absent**, unreadable, not JSON, or failing the `set(census) == {k.value for k in BLOCKING_KINDS}` loader invariant → `AuditError` → exit **1**, naming the path and the `audit --emit-census --out <dir>` command that produces it. |
| 3 | census **comparison** | a disagreement is **not** a failure: one `census_drift kind=<k> pinned=<n> observed=<m>` line per disagreeing kind on stdout, and evaluation continues (AC-1.7's rationale — legitimate cookbook growth must not hard-fail the gate). |
| 4 | adjudication completeness, below | any failure → exit **2**. |
| 5 | all four passed | exit **0**. |

**Why an absent census is exit 1 and an absent clone is exit 5.** Exit 5 means *the measurement
could not be taken*, and it is reserved for conditions that are legitimately absent on a clean
machine — §7.5's whole point is that 19 of 21 clones are missing here and that is not a defect.
`blocking_census.json` is **committed in-repo**: any checkout that has the spec's code has it.
Its absence is a broken working tree or an incomplete Task 5, i.e. exactly §9's definition of
exit 1 — "the implementation or an input disagrees with a pinned expectation". Returning 5 would
tell a CI operator to provision clones they already have; returning 0 would let the gate pass
without the drift detector that R3-B2 exists to provide, which is the silent-pass shape this whole
section is built against.

**Injection points, so Tasks 5 and 6 are writable (rev 5, R4-W5).** Revision 4 required tests to
drive `--gate` against a temp `recipes.yml` and a mutated adjudications file, while `gate()`,
`run_audit()`, `load_blocking_census()` and the adjudications loader had no stated signature.
They do now, and all four take the same shape as `load_recipes(path)` and `load_registry(path)`:

```python
def run_audit(recipes_path: Path | None = None) -> AuditResult: ...
def load_adjudications(path: Path | None = None) -> Mapping[str, Mapping[str, Any]]: ...
def load_blocking_census(path: Path | None = None) -> Mapping[str, int]: ...

def gate(recipes_path: Path | None = None,
         adjudications_path: Path | None = None,
         census_path: Path | None = None,
         out: TextIO = sys.stdout) -> int:
    """Returns the exit code; never calls sys.exit().

    The full chain is `__main__` -> _main() -> cli.run(_dispatch, parser, argv)
    -> gate(), and every link returns an int rather than exiting, so every
    'exits N' obligation in this spec is testable in-process as
    `gate(...) == N`.  The CHAIN ITSELF -- specifically the
    `if __name__ == "__main__": raise SystemExit(_main())` line, which no
    in-process test crosses -- is exercised by Task 8's
    test_ingest_entrypoints.py via runpy (R5-B1).
    """
```

*Rev 6 (R5-S1): revision 5 wrote "the `__main__` block is `raise SystemExit(gate())` and nothing
else", while §7.1's normative template — added in the same revision — is `raise
SystemExit(_main())` with `_main()` building a parser and calling `cli.run`. Both were right about
their own half and wrong about each other's; the docstring now names the whole chain, which is
also the thing R5-B1's test walks.*

**The injection is Python-level only, and that is the load-bearing half.** The CLI exposes **no**
`--recipes-path`, `--adjudications-path` or `--census-path` flag — §7.5's fourteen-row table is
complete as written and gains no rows. Tests call `audit.gate(recipes_path=tmp_yml, …)` directly.
This is what keeps AC-1.7's *"there is no `--force`, no `--advisory`, and no environment-variable
bypass"* true: a path flag on a blocking gate is a bypass with a different name — anyone can point
it at an adjudications file they wrote for the purpose. A keyword argument reachable only from
Python is not, because reaching it means editing the test suite in a reviewed diff.

**Monkeypatch targets, named once for all three tasks that need them.** Verified live 2026-08-27:

| target | technique | why |
|---|---|---|
| `coxswain.plr.tool_schema.TOOL_SCHEMA` | `monkeypatch.setitem(TOOL_SCHEMA, "mix", dataclasses.replace(TOOL_SCHEMA["mix"], receiver_type="plate_reader"))` | **`ToolSpec` is `@dataclass(frozen=True)`** (`tool_schema.py:35`), so `TOOL_SCHEMA["mix"].receiver_type = …` raises `FrozenInstanceError` (R4-W6). `TOOL_SCHEMA` itself is a plain `dict`, so `setitem` mutates the object every importer shares — it works through `from … import TOOL_SCHEMA` as well as through the module. |
| `overlay_gen.miner.NON_SURFACE_VERB_REASONS` | `monkeypatch.setitem(NON_SURFACE_VERB_REASONS, "use_channels", "<reason>")` | plain `dict` (`miner.py:71`); same reasoning |
| `coxswain.plr.param_namespace.PARAM_NAMESPACE` | `monkeypatch.setitem` | plain `dict` (`param_namespace.py:142`) |
| `ingest.audit.BLOCKING_KINDS` | `monkeypatch.setattr(audit, "BLOCKING_KINDS", frozenset({...}))` | a module-local `Final[frozenset]`; `subject_table_fingerprint` reads it at call time |
| `ingest.recipes.default_recipes_path` | `monkeypatch.setattr(recipes, "default_recipes_path", lambda: Path("/nonexistent"))` | AC-1.16's clone-absent driver |
| `ingest.recipes._PREDICATES` | `monkeypatch.setitem` | R2-B3's multi-hit branch |

⚠️ **`PHASE2_TOOL_NAMES` does not follow a `setitem`.** It is a `frozenset` materialized at import
from `TOOL_SCHEMA` (`tool_schema.py:194`), so patching `TOOL_SCHEMA` leaves it stale. No test in
this spec needs it to move — Task 5's only `TOOL_SCHEMA` patch is on `mix`, which is
`experimental` and therefore not in `PHASE2_TOOL_NAMES` under either the real or the patched
table — but a future test that needs both must patch both, and this is where that is written down.

`--gate` exits 0 iff, for every finding with `blocking: true`:

1. an entry exists (else reason `missing`);
2. `reading` is in the enum, `rationale` is ≥ 40 characters, `adjudicated_by` and
   `adjudicated_on` are non-empty, **`action_ref` matches `ACTION_REF_RE` whenever
   `action != "none"` and is empty when `action == "none"`**, and the `impact` block is present and
   complete — with `regeneration_backlog_ref` also matching `ACTION_REF_RE` — whenever
   `action == "edit_table_by_hand"` (else reason `incomplete`);
3. **`entry.adjudicated_digest == finding.adjudicable_digest`** (else reason `stale_digest`, and
   the gate prints both digests plus a one-line diff of the projection fields that changed).

Otherwise exit **2**, printing every failing `finding_id` with its reason. Stale adjudications
(ids no longer produced) are reported as warnings, never as failures, and never auto-deleted.
**These three checks are step 4 of the order above**; exit 2 is reachable only once the cookbook
was read (step 1) and a valid census was loaded (step 2), so a 2 always means what it says — a
blocking finding was measured and is unadjudicated — and never "something upstream was missing".

**`action_ref`'s grammar, and the honest statement of what it does not prove (rev 4, R3-W8).**

```python
#: Closed prefix set, in audit.py -- not in a data file, for the same reason
#: CEILING_PREFIXES is in sources.py (W13): adding a reference form is a code diff.
ACTION_REF_RE: Final[re.Pattern[str]] = re.compile(
    r"^(backlog:[a-z0-9][a-z0-9_-]*"          # backlog:coxswain-nsvr-use-channels
    r"|commit:[0-9a-f]{40}"                   # commit:<40 hex>
    r"|issue:https://github\.com/[\w.-]+/[\w.-]+/issues/\d+)$"
)
```

Revision 3 required only that `action_ref` be a **non-empty string**, so `action_ref: "x"`
satisfied the gate — and because the five `surface_adjacent` adjudications can never go stale
(R3-B1), that one unchecked string was the entire load-bearing content of "the gap is owned".
The grammar makes a *typo* and an *empty gesture* distinguishable from a reference.

**What it still does not prove, stated rather than implied:** the gate does **not** verify that
`backlog:<id>` resolves to a real backlog item, and it never will inside Increment 1. There is no
backlog reader in `training/ingest/`, F3 forbids `subprocess`, and reaching a backlog service would
break the offline guarantee that AC-1.16 and §7.5 exist to protect. **Resolvability is unverified
by design**, the same status `regeneration_backlog_ref` has always had; §12.12 records it as a
limitation with a named owner rather than leaving it as an unstated assumption.

### 5.6 No auto-patch — the decidable version (C2)

Revision 1's AC-1.8 required an AST scan to prove that no write's "path argument is not provably
rooted at the module-level constant `OUT_DIR`". Three problems, all fatal: `write_report(findings,
out_dir: Path)` takes the root as a **parameter**, so no AST scan can root it; AC-1.10 *requires*
writes into temp dirs; and "provably rooted" is not an AST-decidable property in the first place.
The two ACs were mutually unsatisfiable and the scan proved nothing.

Rev 2 separates the property we actually want (*ingest can never write to a canonical table*)
from the mechanism, and enforces it three ways:

**(a) One writer, checked at runtime.** `training/ingest/io.py`:

```python
PROTECTED_ROOTS: Final[tuple[str, ...]] = (
    "coxswain/",                       # tool_schema.py, param_namespace.py
    "training/floor_gen/data/",        # ambiguity_matrix.json
    "training/overlay_gen/",           # miner.py + its out/
    "training/assemble/out/",          # the 188-row corpus + manifest
    "training/golden/",                # golden fixtures
    "training/ingest/data/",           # committed GATE INPUTS: never written by any ingest
                                       # command, hand-authored OR computed. See (d).  (W12)
    "external/",                       # vendored PLR
)

#: rev 7 (C1): base is `cli.IngestError`, NOT RuntimeError -- §7.1's hierarchy table.
#: Round 6's C1 named four sites; the full grep its fix required found this fifth one.
#: As a bare RuntimeError it escaped `cli.run` entirely, so an attempted write into a
#: protected root surfaced as an uncaught traceback instead of the exit 1 §9 defines for
#: "the implementation disagrees with a pinned expectation" -- which is exactly what it
#: is. `io.py` importing `cli` does not cycle: cli.py imports nothing from this package.
class ProtectedPathError(cli.IngestError): ...     # -> exit 1 via cli.run

def write_artifact(out_dir: Path, name: str, payload: str | bytes) -> Path:
    """The ONLY function in training/ingest/ that opens a file for writing or creates a
    directory. Resolves out_dir/name; raises ProtectedPathError if the resolved target is
    inside REPO_ROOT and under any PROTECTED_ROOTS prefix. Temp dirs are outside REPO_ROOT
    and therefore always legal."""
```

**(b) An AST lint — cheap early warning, completeness NOT claimed (W7).**
`test_ingest_never_patches_tables.py` scans every module under `training/ingest/` and fails if any
module **other than `io.py`** contains a call resolving to any of:

```
open / io.open / os.open / os.fdopen        with a mode containing w | a | x | +
Path.open                                    with a mode containing w | a | x | +
Path.write_text  Path.write_bytes  Path.mkdir  Path.touch  Path.unlink  Path.rmdir
Path.rename      Path.replace      Path.symlink_to  Path.hardlink_to   Path.chmod
os.makedirs  os.mkdir  os.rmdir  os.remove  os.unlink  os.rename  os.replace
os.truncate  os.symlink  os.link  os.chmod
shutil.*        (the whole module)
tempfile.*      (the whole module)
json.dump  pickle.dump  csv.writer  csv.DictWriter
```

`tempfile` is banned outright rather than exempted: temp directories are **supplied by the
caller** (pytest's `tmp_path`, or `--out`), so no ingest module has any reason to create one, and
allowing it would open a hole the rest of the list closes.

**Revision 2 over-claimed this property and rev 3 withdraws the claim.** It called (b) "a
syntactic fact with a crisp answer" — true of each individual rule, false of the *set*: an
AST blacklist over an open-ended standard library is necessarily incomplete, and round 2 found
nine omissions in the first version of the list. (b) is a **lint**: it catches the accident and
the careless edit cheaply. It is not the proof. The proof is (c), which observes the property
directly and does not care how a write was spelled. Recorded as §12.9 so the next reviewer does
not have to rediscover that the list is a heuristic.

**(c) A byte-level canary — the strongest evidence, and the cheapest.** The same test hashes
`coxswain/src/coxswain/plr/tool_schema.py`, `coxswain/src/coxswain/plr/param_namespace.py`,
`training/floor_gen/data/ambiguity_matrix.json` and `training/overlay_gen/miner.py`, runs the
**entire** pipeline (`licenses --report`, `audit --report`, `audit --gate`, `gap --gate`) into a
`tmp_path`, and re-hashes. Any inequality fails. This directly observes the property the AC is
about, rather than approximating it.

`write_artifact` also makes AC-1.10 trivially satisfiable: determinism runs pass two distinct
`tmp_path`s and compare hashes, with no tension against (a)-(c).

**(d) How the committed files in a protected root get produced (W12; recounted and corrected in
rev 4 — R3-B2, R3-B3, R3-W5, R3-W9).** `PROTECTED_ROOTS` includes `training/ingest/data/`, which
revision 2 annotated *"committed inputs are hand-authored, never generated"* — while several files
in that directory are described elsewhere in this spec as computed by the fixer. Both statements
cannot hold. The reconciliation, over **eleven** files — **six hand-authored, five computed**:

| file | origin | how it is produced | what checks it, **and how strongly** |
|---|---|---|---|
| `sources.json` | hand-authored | Task 1 | **shape only** — I1–I10 validate structure and cross-field consistency, never content |
| `license_rules.json` | hand-authored | Task 2 | **byte pin** — `LICENSE_RULES_SHA256` (§2.5) proves the file has not changed, not that its rules are right |
| `experimental_partition.json` | hand-authored | Task 5 | **re-derivation of the key set** — the loader **raises `AuditError` unless** `phantom ∪ no_backend` equals the live `experimental=True` set with empty intersection (§5.3); the *reasons* are unchecked prose |
| `audit_adjudications.json` | hand-authored | Task 6 | **re-derivation of the key set + digest equality** — G2 itself (§5.5): every blocking `finding_id` must be present at its current digest |
| `import_closure_allowlist.json` | hand-authored | Task 8 | **re-derivation** — §7.3(b)'s closure scan recomputes the closure and fails on any un-allowlisted leaky edge |
| **`receiver_aliases.json`** | **hand-authored (values) / mechanically-derivable (keys)** — R3-B3 | Task 3, **by hand — that transcription is the bootstrap** (R4-W1); thereafter assisted by `recipes --emit-receiver-alias-keys --out <dir>` (a **merge proposal**, see below), which **raises** rather than bootstrapping when no committed file exists | **KEY SET ONLY** — §3.3 rule 2's two-way equality re-derives the 31 keys and says **nothing** about the values. The values are checked by Task 3's direct three-value pin, which is the **only** guard that fires on an initial authoring error; `blocking_census.json` catches a later regression only (§3.3 rule 5's ordered table — rev 5, R4-W2) |
| `lineage_contract.json` | **computed** | `eval_split --emit-lineage-contract --out <dir>` | **subset constraint, not a re-derivation** — AC-1.17 asserts observed lineage keys ⊆ `known_keys ∪ reserved_cookbook_keys`, so a contract carrying unused or pre-added keys passes (R3-W9). That is the intended strength: the gate exists to catch a *new* key, not to forbid a spare one |
| `token_histogram.json` | **computed** | `recipes --emit-histogram --out <dir>` | **re-derivation** — AC-1.4(2) recomputes the histogram and compares exactly. **Rev 5 (R4-B1): this file also now carries `n_recipes`**, which is where the "exactly 91" claim lives after it was removed from `load_recipes()`'s invariant list for making four of the spec's own fixtures unparseable. Same check, one more field; no new file. **Rev 6 (R5-W1): this is the count's only *derived* home**, and the one other committed copy (`eval_split.json`'s `n_recipes`) is pinned to it by §4.4 assertion 6 rather than authored independently |
| `eval_split.json` | **computed** | `eval_split --emit --out <dir>` | **one-way (deliberately) on the path list; exact on the counters** — §4.4's assertion 3 is `committed ⊇ recomputed`, because C10 forbids making the recomputation authoritative; assertions 0/1/2/4/5 constrain the rest, and **assertion 6 (rev 6, R5-W1) pins this file's `n_recipes` to `token_histogram.json`'s and its `n_held_out` to `len(held_out_paths)`**, so neither counter is an unchecked second home for a fact derived elsewhere |
| `canonical_tables_fingerprint.json` | **computed** | `audit --emit-fingerprint --out <dir>` | **re-derivation of both halves** — AC-1.14 recomputes the fingerprint *and* each of the five artifact hashes |
| **`blocking_census.json`** | **computed** — R3-B2 | `audit --emit-census --out <dir>` | **re-derivation** — AC-1.6 recomputes the census from the live cookbook and compares exactly; the loader additionally **raises `AuditError` unless** `set(census) == {k.value for k in BLOCKING_KINDS}` |

**Revision 3's blanket claim is deleted, because it was false for one row (R3-W9/R3-B3).** It read:
*"every computed file has a gate in the right-hand column that re-derives it and fails on
disagreement, so a stale or mis-copied file is a red test, not a silent wrong input."* Two of the
checks are not re-derivations (`lineage_contract.json`'s subset test, `eval_split.json`'s
deliberate one-way containment), and one — `receiver_aliases.json` — re-derives only the half of
the file that carries no information. Under the old column heading there was no way to *say* that,
which is how the defect survived a revision. The column now names the strength of each check, and
the two rows whose check is weaker than re-derivation say why the weakness is intended.

**The `receiver_aliases.json` emitter is a merge proposal, never an overwrite (R3-B3).**
`recipes --emit-receiver-alias-keys --out <dir>` reads the **existing committed** file and the live
DOTTED receiver set, and emits:

```jsonc
{
  "receiver_aliases_version": "<existing version>",
  "default": "other",
  "exact": { /* every existing key at its EXISTING value, plus every newly
                observed key at "other" */ },
  "needs_review": ["<newly added key>", "..."],   // human must assign a real value
  "unused": ["<committed key no longer observed>", "..."]  // human must delete or justify
}
```

It **never** changes an existing value, **never** deletes a key, and **never** emits a file whose
`needs_review` is silently empty when new keys were found. A fixer who runs it and copies the
result without reading `needs_review` gets a file that still passes §3.3 rule 2 (the keys are
right) and fails Task 3's value pin if they guessed wrong about a liquid handler — which is the
point. Revision 3 called this command `--emit-receiver-aliases` and described it as producing the
file outright; C9 says that is impossible, and §3.3 rule 5 now says so at the point of use.

**And it has no first run (rev 5, R4-W1).** "Reads the existing committed file" presumes one
exists, and Task 3 is where it first does — so the emitter's bootstrap behaviour was undefined at
exactly the point R3-B3 identified as hazardous. It is defined now by **not existing**: with no
committed `receiver_aliases.json`, the command raises `RecipesError` naming the missing path and
exits 1. The first version is a **human transcription** of §3.3's 31-row table, where the three
`liquid_handler` values are assigned by a person reading vendored PLR — which is the whole content
of R3-B3's reclassification. The tempting alternative (emit all 31 keys as `other`, list all 31 in
`needs_review`) is rejected for the reason C9 gives: it is a generator for a file that cannot be
generated, and it produces an artifact that passes rule 2's key-set equality while carrying no
information. What kept this out of blocking is that §3.3's table supplies the initial content in
full, by transcription — so a fixer following this spec has the file, and only a fixer following
the *emitter* had a hole.

**And when both failures apply, the clone check runs first (rev 6, R5-S3).** During Task 3 on a
checkout with no clones, the absent clone (exit **5**, §7.5) and the absent committed file (exit
**1**, above) are both true. **5 wins**, on the same principle §5.5 states for `audit --gate`'s
clone → census order: an exit 1 from this command is an instruction to hand-author §3.3's 31-row
table, and it should not be issued by a command that never reached the data it would have merged
against.

**No ingest command ever writes into `data/`.** Each of the six emitters (§7.1's tuple table names
them; five are spelled `--emit-<something>` and `eval_split`'s is bare `--emit`) writes to a
caller-supplied
`--out` (a temp dir, or `out/`), and landing the result in `data/` is a **human `cp` in a reviewed
commit**. That is deliberate rather than awkward: the point of the protected root is that a gate's
committed input can only change through a diff someone signed, which is exactly the property
`GAP_THRESHOLDS` has and for the same reason (PM-2). The manual step is not *trusted* either —
every file above has a check, and the column now states exactly how much each check proves, so a
reader can tell "this is re-derived" from "this is shape-checked" without inferring it.

### 5.7 Canonical-table fingerprints and the `edit_table_by_hand` consequence protocol (C13)

Revision 1 offered `action: edit_table_by_hand` as an adjudication outcome and specified no
consequence for taking it. But editing `tool_schema.py` or `param_namespace.py` invalidates the
188-row corpus, the 43-cell matrix, and the golden fixtures — an audit *success* whose blast
radius revision 1 left undescribed. There was, in the reviewer's phrasing, no rollback for the
success case.

**The fingerprint.** Over a *decision-relevant projection only*, so that a comment or `note` edit
does not invalidate anything:

```python
def _projection() -> dict[str, Any]:
    return {
        #: R4-B3 sweep: `s.receiver_type` is verified to be a plain `str` on the
        #: live ToolSpec (tool_schema.py:41), NOT an enum -- so it needs no
        #: `.value` and carries none of finding_id's version-dependence. Every
        #: other enum reaching a hash payload in this spec is already `.value`d
        #: (p.kind.value here; f.kind.value, e.*.value in §5.2's projection).
        "tools": {n: {"receiver_type": s.receiver_type, "experimental": s.experimental,
                      "phase2_included": s.phase2_included}
                  for n, s in sorted(TOOL_SCHEMA.items())},
        "params": {v: [{"name": p.name, "plr_arg": p.plr_arg, "kind": p.kind.value,
                        "required": p.required}
                       for p in specs]
                   for v, specs in sorted(PARAM_NAMESPACE.items())},
        "non_surface": sorted(NON_SURFACE_VERB_REASONS),
    }

def canonical_tables_fingerprint() -> str: ...      # _sha16(_projection())  -- §5.2's helper

#: R2-B2: takes the KIND, because the subject's shape is kind-dependent (§5.2) and
#: nothing else can parse it. Hashes the LOOKUP RESULT, misses included -- not the
#: found rows -- which is what stops a not-in-any-table subject hashing to a constant.
def subject_table_fingerprint(kind: FindingKind, subject: str) -> str: ...
```

**`subject_table_fingerprint`, defined over three cases (R2-B2).** Revision 2 defined it as *"the
same [projection], restricted to rows about `subject`"*, which has no meaning for a subject that
is not a `TOOL_SCHEMA` key — and per §5.4.1 that is **five of the nine** blocking findings. The
three cases:

**The dispatch, with the subject-parsing rule written out (rev 4, R3-W6).** Revision 3 gave the
function the signature `(kind, subject)` and then defined `_param_slice(tok, verb)` and a Case A
that needs `member` — without ever saying how those are recovered from the single `subject`
string. R2-B2 exists *because* leaving subject parsing implicit produced two disjoint key spaces,
so leaving the inverse implicit repeats the defect one level down:

```python
#: rev 7 (C1): base is `cli.IngestError`, NOT ValueError -- §7.1's hierarchy table.
class AuditError(cli.IngestError): ...     # -> exit 1; already raised by §5.3's loader

_VERB_KINDS     = frozenset({FindingKind.PHANTOM_VERB, FindingKind.NO_BACKEND_VERB,
                             FindingKind.SCHEMA_UNMENTIONED})       # subject IS the verb
_DOTTED_KINDS   = frozenset({FindingKind.RECEIVER_DRIFT, FindingKind.SURFACE_ADJACENT,
                             FindingKind.UNKNOWN_METHOD})           # "<receiver_type>.<member>"
_PARAM_KINDS    = frozenset({FindingKind.PARAM_MISATTRIBUTED, FindingKind.PARAM_CANDIDATE})
_NO_TABLE_KINDS = frozenset({FindingKind.UNCLASSIFIED_TOKEN, FindingKind.UNMAPPED_RECEIVER})

#: W7/R3-W7: a RAISE at import, not a bare assert -- `python -O` strips asserts, and
#: a kind added to FindingKind without a scope must fail loudly, not silently take
#: whichever branch `else` happens to be.
_SCOPED = _VERB_KINDS | _DOTTED_KINDS | _PARAM_KINDS | _NO_TABLE_KINDS
if _SCOPED != set(FindingKind):
    raise AuditError(f"kinds with no declared table scope: {set(FindingKind) - _SCOPED}")

_RECEIVER_TYPE_VALUES: Final[frozenset[str]] = frozenset(r.value for r in ReceiverType)

def subject_table_fingerprint(kind: FindingKind, subject: str) -> str:
    if kind in _VERB_KINDS:
        sl = _verb_slice(subject)                       # subject IS the verb
    elif kind in _DOTTED_KINDS:
        recv, sep, member = subject.partition(".")      # == subject.split(".", 1)
        if not sep or recv not in _RECEIVER_TYPE_VALUES:
            raise AuditError(
                f"{kind.value}: subject {subject!r} is not '<receiver_type>.<member>'")
        sl = _verb_slice(member)
    elif kind is FindingKind.PARAM_CANDIDATE:
        verb, sep, tok = subject.partition(":")         # == subject.split(":", 1)
        if not sep:
            raise AuditError(f"param_candidate: subject {subject!r} is not '<verb>:<token>'")
        sl = _param_slice(tok, verb)
    elif kind is FindingKind.PARAM_MISATTRIBUTED:
        sl = _param_slice(subject, None)                # no declaring verb, by design (§5.2)
    else:                                               # kind in _NO_TABLE_KINDS
        sl = _no_table_slice(kind, subject)
    #: R3-W7: the scope="none" guard moved HERE, from inside _no_table_slice, and
    #: became a raise. At the dispatch point it also catches a blocking kind
    #: mis-routed to Case A or B, which the old placement could not see.
    if sl["scope"] == "none" and kind in BLOCKING_KINDS:
        raise AuditError(f"{kind.value} is blocking and must not use scope=none")
    return _sha16(sl)                           # §5.2's helper; canonical_json is DEFINED there
```

**Why each split is unambiguous, argued rather than assumed.** For the dotted kinds, no
`ReceiverType` value contains a `.` (`liquid_handler`, `plate_reader`, `heater_shaker`, `other`,
`none`) and every `member` reaching a dotted kind is method-shaped, i.e. matches
`[a-z_][a-z0-9_]*` (§3.2), so the **first** `.` is the separator and the receiver half is
additionally validated against the closed enum — a subject like `backends/chatterbox.py` (a *raw
receiver*, not a `receiver_type`) therefore raises rather than silently producing a slice for the
verb `py`. For `param_candidate`, the verb is a `TOOL_SCHEMA` key and the token is an `IDENT`, so
neither half can contain a `:` and the first one is the separator.

**Case A — the subject resolves to a verb.** Kinds `phantom_verb`, `no_backend_verb`,
`schema_unmentioned` (subject *is* the verb) and `receiver_drift`, `surface_adjacent`,
`unknown_method` (the verb is the `member` half of `<receiver_type>.<member>`). The slice is a
**membership record over all three tables, misses included**:

```python
def _verb_slice(v: str) -> dict[str, Any]:
    proj = _projection()
    return {
        "scope": "verb", "verb": v,
        "in_tool_schema":      v in proj["tools"],
        "tool_row":            proj["tools"].get(v),      # None on a miss
        "in_param_namespace":  v in proj["params"],
        "param_rows":          proj["params"].get(v),     # None on a miss
        "in_non_surface":      v in NON_SURFACE_VERB_REASONS,
    }
```

This is the whole answer to "what does the empty projection hash to, and is a constant hash
acceptable". It is **not** a constant and the empty case does not arise: `liquid_handler.head`
hashes a record containing the string `head` and three explicit `False` flags, which is distinct
from `liquid_handler.use_channels`' record and distinct again from `mix`'s. **Subject-distinctness
holds for all ten kinds**, and revision 2's "rows about the subject" formulation — which would have
hashed (nearly) the empty set for every not-in-any-table subject alike — is genuinely repaired.

#### Table sensitivity is a per-kind property, and for one blocking kind it is absent (rev 4, R3-B1)

Revision 3 continued the paragraph above with a second claim: that `_verb_slice` *"preserves
exactly the anti-staleness property C3 built the digest for — a `SURFACE_ADJACENT` finding exists
because its member is in none of the three tables, so if someone adjudicates it and then adds the
member to `NON_SURFACE_VERB_REASONS`, `in_non_surface` flips, the digest changes, and the
adjudication goes `stale_digest`."* **That scenario cannot happen, and it was the only worked
example offered for the property.** §5.4 defines `SURFACE_ADJACENT` as a member absent from *both*
`TOOL_SCHEMA` and `NON_SURFACE_VERB_REASONS`, so adding the member to either table does not flip a
flag on a surviving finding — it **deletes the finding**. What is left behind is a stale
*adjudication*, and §5.5 reports those "as warnings, never as failures". Nothing goes red by way
of the digest. The claim was not merely unproven; it was about an unreachable state.

Two claims must therefore be separated, and revision 3 ran them together:

- **Subject-distinctness** — different subjects hash differently. True for every kind. This is what
  kills R2-B2's constant-hash hazard, and it is intact.
- **Table sensitivity (anti-staleness)** — some canonical-table edit changes the slice *while the
  finding continues to exist*. True for **some** kinds only, and the exceptions are structural.

The per-kind answer, derived from each kind's own existence condition:

| kind | case | blocking? | an edit that changes the slice with the finding surviving | sensitive? |
|---|---|---|---|---|
| `phantom_verb` | A | **yes** | subject is a `TOOL_SCHEMA` key and the finding is emitted **unconditionally** from `experimental_partition.json` (§5.3), so editing its `receiver_type` or `phase2_included` changes `tool_row` with the finding intact | **yes** |
| `receiver_drift` | A | **yes** | subject's member is a `TOOL_SCHEMA` key; editing `experimental`/`phase2_included` changes `tool_row` without resolving the drift. (Editing `receiver_type` to agree *deletes* the finding — correctly, because that is the drift being fixed) | **yes** |
| `param_misattributed` | B | **yes** | the finding requires the token to equal some `ParamSpec.name`/`plr_arg`, so at least one such row exists; editing that row's **`kind` or `required`** changes `rows_by_verb` with the finding intact. *Rev 5 (R4-W8): revision 4 also listed `plr_arg`, which is wrong in the same way R3-B1's original example was wrong — editing `plr_arg` away from the token removes the row from the slice, and if it was the **only** matching row the finding's own existence condition fails and it is **deleted**, not staled. `name`/`plr_arg` are examples of sensitivity only when a second row still matches the token (e.g. `vols`, declared by both `aspirate` and `dispense`). `kind`/`required` are unconditional, which is why they are the ones stated.* | **yes** |
| **`surface_adjacent`** | A | **yes** | **none** — see below | **NO** |
| `schema_unmentioned` | A | no | subject is a `TOOL_SCHEMA` key; the finding depends on cookbook mentions, not on the row's fields | yes |
| `no_backend_verb` | A | no | same as `phantom_verb` | yes |
| `unknown_method` | A | no | same structural inertness as `surface_adjacent` (member in neither table) | no |
| `param_candidate` | B | no | only when the token matches some *other* verb's `ParamSpec`; when it matches nothing, adding it to the named verb deletes the finding | partial |
| `unclassified_token` | C | no | none, **by design** — nothing to look up | no |
| `unmapped_receiver` | C | no | none, **by design** | no |

**The tally, stated so it cannot be mis-cited again (rev 5, R4-W8).** The column reads **five
`yes`, one `partial`, four `no`** — `yes` for `phantom_verb`, `receiver_drift`,
`param_misattributed`, `schema_unmentioned`, `no_backend_verb`; `partial` for `param_candidate`;
`no` for `surface_adjacent`, `unknown_method`, `unclassified_token`, `unmapped_receiver`. Revision
4 summarized this as *"table sensitivity for six"* in §12.13, counting `param_candidate`'s
`partial` as a `yes` — which is the one row where the answer depends on the token: sensitive when
the token matches some *other* verb's `ParamSpec`, and **deleting** rather than staling when it
matches nothing and is then added to the named verb. Rounding a conditional up to a `yes` is how
R3-B1's original defect was phrased in the first place, so the summary now says **five, plus one
partial**, and §12.13 is corrected to match.

**Restricting to the blocking kinds, which is the number that decides anything:** of the four
blocking kinds, **three are sensitive and one (`surface_adjacent`) is not** — and that one carries
5 of the 9 live blocking findings, so *by finding count* the digest's table sensitivity covers 4
of 9. That framing is the one AC-1.7's census-pin rationale rests on, and it is worth having both
numbers in view: the per-kind count flatters the mechanism, the per-finding count does not.

**Why `surface_adjacent` is structurally inert.** Its existence condition *is* two of the three
memberships the slice records. `in_tool_schema` and `in_non_surface` are `False` **because the
finding exists** — flip either and the finding is gone. `in_param_namespace` is `False` for a
third, independent reason: `PARAM_NAMESPACE`'s keys are drawn from `PHASE2_TOOL_NAMES ⊆
TOOL_SCHEMA` (it imports `PHASE2_TOOL_NAMES` directly), so a member absent from `TOOL_SCHEMA` is
absent from `PARAM_NAMESPACE` too, and `tool_row`/`param_rows` are both `None` in consequence.
Every field of the slice is therefore pinned: `_verb_slice` for these five varies only in `verb`,
which makes it subject-distinct and invariant under every edit it would need to survive.

*One degenerate edit does flip the slice with the finding surviving, and it is recorded so a
reviewer does not have to rediscover it and so nobody builds on it: adding a `PARAM_NAMESPACE` key
for a verb that is **not** in `TOOL_SCHEMA` would set `in_param_namespace: True` while leaving the
`surface_adjacent` condition satisfied. `PARAM_NAMESPACE` is keyed by phase-2 tool names and
imports `PHASE2_TOOL_NAMES`; such an entry is an inconsistent table state that no legitimate edit
produces. **The property is not claimed on this basis.***

**What detects a `surface_adjacent` change instead.** The detectable event for these five is
**disappearance**, and it has two causes with two different detectors — which is the reason the
census pin needed a real home (R3-B2) rather than a literal inside a test file:

| cause of disappearance | detector | strength |
|---|---|---|
| the member is added to `TOOL_SCHEMA` or `NON_SURFACE_VERB_REASONS` | **AC-1.14** — the canonical-tables fingerprint goes red on *any* table edit, and silencing it requires falsifying five artifact hashes in a reviewable diff (§5.7 consequence 1) | strong; fires before the audit is even consulted |
| the cookbook drops the recipe (upstream change; no table edit) | **`blocking_census.json`** — AC-1.6's test goes red when observed `surface_adjacent` ≠ 5, and `audit --gate` prints `census_drift` | the **only** detector; AC-1.14 cannot see a cookbook-side change at all |

**Task 5's third gate bullet is replaced accordingly.** Revision 3 asked for a test in which
monkeypatching `NON_SURFACE_VERB_REASONS` to include `use_channels` changes
`liquid_handler.use_channels`' `adjudicable_digest`. That test cannot be made green — it asserts a
property that does not hold — so Task 5 now tests the two properties that do: the **disappearance**
path for `surface_adjacent`, and a **real** staleness test on `phantom_verb`, where the mechanism
works. Writing a test around a false property and then relaxing it until it passes is how an
inert mechanism gets a green tick, which is exactly what this revision is trying to avoid.

**Case B — the subject is a param token.** Kinds `param_misattributed` (subject is the bare
token) and `param_candidate` (subject is `<verb>:<token>`). The slice is every `ParamSpec` row,
across **all** verbs, whose `name` or `plr_arg` equals the token — which is the well-defined
answer to "which verb's rows does that even mean?": all of them that mention it, keyed by verb, so
that a change to `aspirate`'s `vols` row invalidates a `vols` adjudication and a change to an
unrelated verb's rows does not.

```python
def _param_slice(tok: str, verb: str | None) -> dict[str, Any]:
    proj = _projection()
    hits = {v: [r for r in rows if r["name"] == tok or r["plr_arg"] == tok]
            for v, rows in proj["params"].items()}
    return {"scope": "param", "token": tok, "declaring_verb": verb,
            "rows_by_verb": {v: r for v, r in sorted(hits.items()) if r},
            "declared_anywhere": any(hits.values())}
```

*`tok` and `verb` are recovered from the single `subject` string by the dispatch above (R3-W6):
`param_candidate` splits on the first `:`, and `param_misattributed` passes `verb=None` because
§5.2 deliberately keys it on the bare token — `vols` is declared by both `aspirate` and `dispense`,
and a pair key would emit two findings about one decision.*

**Case C — the subject depends on no canonical table at all.** Kinds `unclassified_token` (a raw
`OTHER` token) and `unmapped_receiver` (a raw receiver string). Neither has anything to look up,
and pretending otherwise would be Case A's constant-hash trap by another name. The slice is
explicit about that:

```python
def _no_table_slice(kind, subject) -> dict[str, Any]:
    return {"scope": "none", "kind": kind.value, "subject": subject}
```

It is subject-distinct (the subject is in the payload) but it is genuinely **table-independent**,
so a canonical-table edit does not invalidate it. That is correct for these two kinds and would be
wrong for any other, so it is guarded rather than trusted — and **rev 4 fixes both defects in how
revision 3 wrote that guard (R3-W7)**. Revision 3 had:

```python
assert kind not in BLOCKING_KINDS, f"{kind} is blocking and must not use scope=none"   # WRONG
```

Two problems. First, a bare `assert` is **stripped under `python -O`**, so the structural
protection R2-B2 leans on — *"the constant-hash case is structurally unreachable where it would
matter"* — is compiled out of an optimized run, and every other invariant in this spec raises a
typed error instead (§5.3's partition loader, §3.1's reader, §2.2's registry). Second, it lived
**inside `_no_table_slice`**, so it could only catch a blocking kind routed to Case *C*; a kind
mis-routed to Case A or B would sail past it. The guard now raises `AuditError` **at the dispatch
point** (see `subject_table_fingerprint` above), where it sees the resolved slice's `scope` for
every kind, and it is joined by a module-level totality check that raises when a new `FindingKind`
is added without a declared scope.

Both `scope: "none"` kinds are advisory, so the guard holds today by construction; it exists so
that promoting a kind to blocking without giving it a table scope fails immediately and loudly,
rather than silently producing a digest that no table edit can ever stale. **Note the limit of what
it buys, given R3-B1:** it forbids a *constant* digest for a blocking kind. It does not — and
cannot — guarantee that a blocking kind's Case A slice is table-*sensitive*, which is why
`surface_adjacent` passes this guard and is still inert. The table above is where that question is
answered, per kind.

**Three consequences, each with an owner:**

1. **`data/canonical_tables_fingerprint.json`** commits the fingerprint under which the current
   committed corpus artifacts were built, **the sha256 of each of those artifacts**, and the
   regeneration checklist:

   ```jsonc
   {
     "canonical_tables_fingerprint_version": "2",
     "fingerprint": "<16 hex from canonical_tables_fingerprint()>",
     "built_artifacts": {                        // W1: five files, sha256 each
       "training/out/corpus_p23_smoke.jsonl":              "<sha256>",
       "training/overlay_gen/out/overlay_smoke.jsonl":     "<sha256>",
       "training/assemble/out/corpus_p25.jsonl":           "<sha256>",
       "training/assemble/out/corpus_p25_sidecar.jsonl":   "<sha256>",
       "training/assemble/out/manifest.json":              "<sha256>"
     },
     "regeneration_order": ["floor_gen", "overlay_gen", "assemble", "ingest"]
   }
   ```

   `AC-1.14`'s test compares **both** halves to live values and goes **red** on any table edit *or*
   any unaccompanied downstream regeneration. Its assertion message is the checklist itself, in
   dependency order: `training/out/corpus_p23_smoke.jsonl` (floor_gen) →
   `training/overlay_gen/out/overlay_smoke.jsonl` (overlay_gen) →
   `training/assemble/out/{corpus_p25.jsonl, corpus_p25_sidecar.jsonl, manifest.json}` (assemble)
   → `training/ingest/out/*` (re-run all ingest gates). **Four stages, five files** — revision 2
   called this "the four-artifact checklist", conflating the stage count with the file count and
   with §5.6(c)'s different four (the canonical *tables*: `tool_schema.py`, `param_namespace.py`,
   `ambiguity_matrix.json`, `miner.py`). All five files were verified present 2026-08-27.
   Increment 1 does **not** perform the regeneration — floor_gen and overlay_gen are teacher-gated
   (F8) — it makes the need visible and blocking instead of silent.

   *Why the artifact hashes are in the file (W1).* With only `fingerprint`, the tripwire was
   silenced by editing one hex string — a one-token diff that says nothing false out loud. With
   `built_artifacts`, silencing requires editing six hashes and thereby asserting, in a reviewable
   diff, that five specific committed files were built under a table they were not. The tripwire is
   still not unsilenceable; nothing enforced by a committed constant ever is. It is now
   *unsilenceable-without-lying*, which is the property C13 asked for and revision 2 did not
   deliver.
2. **The `impact` block** (§5.5) is required for any `edit_table_by_hand` adjudication, so the
   person who chooses that action names the invalidated artifacts and files the regeneration
   backlog item *before* the gate will pass.
3. **Per-subject digest staleness** (§5.2) forces re-adjudication of the edited subject after the
   edit, closing the loop.

---

## 6. `gap.py` — the coverage-gap report, with PRE-REGISTERED thresholds

*Satisfies: `[MERGE] ORTHOGONAL-7` (promoted from rival to first gate) and `[ACCEPT] Pre-mortem
mitigations` PM-2.*

### 6.1 Inputs and cell attribution

| Input | Path | What it supplies |
|---|---|---|
| Matrix | `training/floor_gen/data/ambiguity_matrix.json` via `floor_gen.matrix.load_matrix()` | 43 cells + each cell's own committed `examples_per_cell` |
| Corpus sidecar | `training/assemble/out/corpus_p25_sidecar.jsonl` | 188 rows: `record_id`, `provenance`, `ambiguity_class`, `verb`, `calls[].params`, `lineage.cell_id` |
| Assembly manifest | `training/assemble/out/manifest.json` | cross-check totals; `gap.py` asserts its recomputed per-class counts equal `manifest.counts.by_class` and raises on mismatch |
| Class alias map | `assemble.build.CLASS_MAP` (imported, never re-declared) | `none↔clean_parse`, `missing-slot↔missing_slot`, `ambiguous-referent↔ambiguous_referent`, `out-of-surface↔out_of_surface` |
| Recipes | `ingest.recipes.load_recipes()` | out-of-surface anchor supply |

> **Hazard, pinned:** the matrix's class vocabulary is hyphenated and the corpus's is underscored,
> and `none → clean_parse` is **not** an identity rename. `gap.py` must import
> `assemble.build.CLASS_MAP` rather than re-deriving it. (That import has a transitive-purity
> consequence — see §7.3, which is where C14 is resolved.)

**Cell attribution rule (C18/C19).** Verified 2026-08-27: **only 20 of the 188 sidecar rows carry
`lineage.cell_id`** — the coverage rows. The other 168 (golden + naturalness) do not, so the
fallback is not an edge case, it is the **dominant path** and must be specified as such.

```python
#: W6: rev 2 used this and never defined it. CLASS_MAP is hyphenated -> underscored
#: (verified at assemble/build.py:76), so the inverse is underscored -> hyphenated.
#: Checked injective at import, because a non-injective CLASS_MAP would make the
#: inverse silently lossy rather than loudly wrong.
#: R3-W7: a RAISE, not a bare `assert` -- `python -O` strips asserts, and this is a
#: load-bearing invariant about an imported table this package does not own. Matches
#: the house style of every other invariant here (AuditError, RegistryError,
#: RecipesError, and coxswain.plr's MatrixError -- which is a style precedent only,
#: not a base class: it is not this package's).
#: rev 7 (C1): base is `cli.IngestError`, NOT ValueError -- §7.1's hierarchy table.
class GapError(cli.IngestError): ...       # -> exit 1 via cli.run

if len(set(CLASS_MAP.values())) != len(CLASS_MAP):
    raise GapError(f"CLASS_MAP is not injective: {CLASS_MAP!r}")
INVERSE_CLASS_MAP: Final[Mapping[str, str]] = MappingProxyType(
    {v: k for k, v in CLASS_MAP.items()}
)
# -> {"clean_parse": "none", "missing_slot": "missing-slot",
#     "ambiguous_referent": "ambiguous-referent", "out_of_surface": "out-of-surface"}

def cell_key(row) -> str:
    cid = (row.get("lineage") or {}).get("cell_id")
    if cid:
        return cid                                    # 20 of 188 rows
    verb = row.get("verb") or ""                      # C19: corpus uses "", matrix uses None
    klass = INVERSE_CLASS_MAP[row["ambiguity_class"]]  # underscored -> hyphenated
    if klass == "out-of-surface" and not verb:
        return "generic__out-of-surface"               # the matrix's verb=None sentinel cell
    return f"{verb}__{klass}"
```

**Off-matrix keys are counted, never dropped (F5).** A computed `cell_key` outside the 43
committed cell ids goes into `gap_report.json`'s `unmatched_cell_keys` (key → row count) and is
excluded from the per-cell table.

**`unmatched_cell_keys` is expected to be EMPTY (rev 3 corrects revision 2 — W9).** Revision 2
asserted it "is expected to be non-empty: the naturalness rows include verbs and class
combinations the matrix does not enumerate." That is false against the committed corpus: every one
of the 188 rows maps into one of the 43 cells. The 80 naturalness rows are all `clean_parse` over
five verbs (`aspirate` 21, `dispense` 23, `pick_up_tips` 27, `drop_tips` 6, `discard_tips` 3), so
they key to `<verb>__none`, all five of which the matrix enumerates; the out-of-surface golden
rows carry `verb: ""` and key to the `generic__out-of-surface` sentinel; the 20 coverage rows carry
an explicit `lineage.cell_id` and never reach the fallback at all.

It stays **reported, not gated** (§12.5) — but the value is pinned to `{}` as a **regression pin**
in Task 7's suite, in the same category as `token_histogram.json` and `T1_INVARIANT`. The
distinction §12.5 now turns on: *"0 → non-0 is a change worth seeing"* is a regression pin and is
legitimate; *"N > k means ingestion is justified"* is a threshold and would be the post-hoc
gate-setting C12 punished. The pin also does real work as a measurement-pipeline check: a fixer
whose `INVERSE_CLASS_MAP` direction or `verb`-normalization is wrong gets a non-empty map and a
red test, instead of a plausible-looking report.

### 6.2 Metric definitions — corrected against the live types (C1, C20)

**The bug rev 1 shipped.** `PARAM_NAMESPACE` is `dict[str, tuple[ParamSpec, ...]]`
(`param_namespace.py:142`) — a verb-keyed dict of **tuples**, not a nested name-keyed dict.
Revision 1's `PARAM_NAMESPACE[verb][pname].kind` raises `TypeError: tuple indices must be
integers` on the first row it touches. Worse, `manifest.json`'s `distinct_verbs` includes `mix`,
`blow_out` and `touch_tip`, none of which are keys of `PARAM_NAMESPACE` at all, so the naive
`params_of(verb)` repair raises `KeyError` — deliberately, per its own docstring ("Raises KeyError
for unknown or excluded-from-phase-2 tools — loud by design").

**Which key.** The sidecar's `calls[].params` keys are **schema-side names**: line 1 of
`corpus_p25_sidecar.jsonl` carries `{"source": "plate_2_A3", "volume_ul": 10.0}`, and
`aspirate`'s `ParamSpec.plr_arg`s are `resources`/`vols`. `overlay_gen.miner`'s `MinedCall`
docstring confirms it: *"`params` keys are schema-side names from PARAM_NAMESPACE"*. The index is
therefore keyed on **`ParamSpec.name`**. Revision 1 left this ambiguous, and the reviewer is right
that the choice silently changes T2: keying on `plr_arg` would miss every lookup and route all
values through the fallback branch, making every param's form a bare type name.

```python
_PARAM_INDEX: Final[Mapping[tuple[str, str], ParamSpec]] = MappingProxyType({
    (verb, spec.name): spec
    for verb, specs in PARAM_NAMESPACE.items()
    for spec in specs
})

_SUBSCRIPT = re.compile(r"\w+\[[^\]]+\]")
_SLICE     = re.compile(r"\w+\[[^\]]*:[^\]]*\]")
_ATTR      = re.compile(r"\w+(\.\w+)+")

def value_form(verb: str, pname: str, v: Any, stats: GapStats) -> str:
    spec = _PARAM_INDEX.get((verb, pname))          # C1: total lookup, never raises
    if spec is None:
        stats.unmapped_params[(verb, pname)] += 1   # F5: counted, not dropped
    if spec is not None and spec.kind is ParamKind.SYMBOLIC_RESOURCE_REF and isinstance(v, str):
        if _SLICE.fullmatch(v):     return "slice"      # plate["A1":"A6"]  (before subscript)
        if _SUBSCRIPT.fullmatch(v): return "subscript"  # plate["A1"]
        if "(" in v:                return "call"
        if _ATTR.fullmatch(v):      return "attr"       # deck.trash
        if " " in v:                return "phrase"     # "the same well"
        return "name"                                   # plate_2_A3
    if isinstance(v, bool):         return "bool"       # before the numeric branch
    if isinstance(v, (int, float)): return "number"     # C20: collapses 10.0 and 20
    if isinstance(v, list):
        inner = "|".join(sorted({value_form(verb, pname, m, stats) for m in v}))
        return f"list[{inner}]" + ("+multi" if len(v) > 1 else "")
    return type(v).__name__

#: W15: the `verb` parameter is GONE, not documented. Its only possible wrong value
#: (row["verb"]) is precisely the bug the note below warns about; removing the
#: parameter makes that bug unrepresentable rather than merely discouraged.
def shape_key(call: Mapping[str, Any], stats: GapStats) -> tuple:
    return (call["name"], tuple(sorted(
        (p, value_form(call["name"], p, val, stats)) for p, val in call["params"].items()
    )))

#: W6: unmapped_params is (verb, pname)-tuple-keyed IN PROCESS and string-keyed ON
#: DISK. json.dumps(sort_keys=True) raises TypeError on tuple keys, so the serializer
#: is stated rather than left to the fixer -- and it interacts with F6's byte-identity
#: requirement, so it must be deterministic too.
def _serialize_unmapped(c: Counter[tuple[str, str]]) -> dict[str, int]:
    return {f"{verb}|{pname}": n for (verb, pname), n in sorted(c.items())}
```

The `|` separator is safe: both halves are Python identifiers by construction (a verb is a
`TOOL_SCHEMA`/call `name`, a param is a `params` dict key), so neither can contain `|`, and the
round-trip is unambiguous.

Notes on the corrections:

- **Slice before subscript** — `plate["A1":"A6"]` matches both patterns; revision 1's ordering
  tested subscript first and would have labelled every slice a subscript.
- **`verb` for lookup is `call["name"]`, not `row["verb"]`.** The 21 out-of-surface rows carry
  `"calls": []`, so no shape is computed for them at all and `mix`/`blow_out`/`touch_tip` never
  reach the index in practice — but the `.get()` guard is mandatory anyway, because a future
  corpus can carry a call named `mix` and a `KeyError` there would take down the whole gate.
- **`bool` before `int`** — Python's `isinstance(True, int)` is `True`.
- **Numeric collapsing (C20, framing corrected in rev 3 — W2).** `floor_gen` writes `10.0`;
  `golden` and `overlay_gen` write `20`. Under revision 1's `type(v).__name__` fallback, `"float"`
  vs `"int"` made **provenance itself a shape**, so "distinct param shapes" partly counted which
  generator produced a row — leaving T1 (a provenance count) and T2 (a shape count)
  near-collinear, and "T1 ∧ T2 ∧ T3" not three independent checks. Collapsing to `"number"`
  removes the leak **from the collapsed measure**. Revision 2 then said it "removes the leak" full
  stop, which is false at the decision point: under revision 2's "take the STOP-side answer"
  rule, the *strict* reading — the leaking one — was the effective authority whenever the two
  disagreed. §6.4/§6.5 replace that rule; the collapsing itself is unchanged and remains correct.

**Thin cell:** `rows(cell) < cell.examples_per_cell`. The threshold is **not invented here** — it
is the number the matrix already committed for that cell (currently 3 for all 43).

### 6.3 Report shape — `training/ingest/out/gap_report.json`

```jsonc
{
  "ingest_version": "0.1.0",
  "gap_thresholds_version": "1",
  "matrix_version": "1",
  "corpus_manifest_sha256": "<hex>",
  "recipes_yml_sha256": "<hex>",
  "cells": [
    {"cell_id": "move_lid__missing-slot", "verb": "move_lid", "ambiguity_class": "missing-slot",
     "examples_per_cell": 3, "rows": 0, "rows_by_provenance": {"coverage":0,"golden":0,"naturalness":0},
     "thin": true, "empty": true}
  ],
  "unmatched_cell_keys": {},          // C18: off-matrix keys, counted (F5). EMPTY today (W9)
  "unmapped_params": {},              // C1: absent from PARAM_NAMESPACE (F5). Keys are
                                      // "<verb>|<param>" strings, never tuples (W6)
  "verbs": [
    {"verb": "transfer", "in_surface": true, "receiver_type": "liquid_handler",
     "rows_total": 12, "rows_naturalness": 0,
     "distinct_param_shapes_collapsed": 2, "distinct_param_shapes_strict": 2, "shapes": ["..."]}
  ],
  "recipe_anchor_supply": {"out_of_surface_recipes": 0, "distinct_chapters": 0, "in_surface_recipes": 0},
  "metrics": {"T1_zero_naturalness_lh_verbs": 0, "T1_verbs": [],
              "T2_low_shape_lh_verbs_collapsed": 0, "T2_low_shape_lh_verbs_strict": 0,
              "T3_out_of_surface_anchors": 0, "T3_chapters": 0,
              "thin_cells": 0, "empty_cells": 0,
              "thin_cells_note": "REPORTED, NOT GATED — see §6.4"},
  "invariants": {"T1": {"expected": 5, "expected_verbs": ["move_lid","move_plate","move_resource","stamp","transfer"],
                        "observed": 5, "holds": true}},
  "gate": {"thresholds": { /* verbatim GAP_THRESHOLDS */ },
           "per_threshold": {"T2": {"value": 0, "required": 5, "op": ">=", "pass": false}, "...": {}},
           "t2_normalization_sensitive": false,
           "decision": "PROCEED | STOP | CONTESTED",
           "decision_rule": "PROCEED iff T2_collapsed AND T3 both pass (T1 is an invariant, not a gate — §6.5). If T2's collapsed and strict readings disagree on pass/fail, the decision is CONTESTED (exit 7) — neither PROCEED nor STOP."}
}
```

### 6.4 THE PRE-REGISTERED THRESHOLDS

Committed in `training/ingest/versions.py` as a frozen mapping, **written before the report ever
runs**, and changeable only by a diff that also bumps `GAP_THRESHOLDS_VERSION`:

```python
GAP_THRESHOLDS_VERSION: Final[str] = "2"      # rev 2: T1 demoted to an invariant (C12)
GAP_THRESHOLDS: Final[Mapping[str, int]] = MappingProxyType({
    "T2_low_shape_lh_verbs_min":      5,   # of 10, "low" = < 3 distinct param shapes
    "T2_shape_floor":                 3,   # = matrix examples_per_cell
    "T3_out_of_surface_anchors_min": 25,   # recipes naming no in-surface verb
    "T3_distinct_chapters_min":       8,
})
#: NOT a threshold: a pinned expectation the report must reproduce, else exit 1 (C12).
T1_INVARIANT: Final[Mapping[str, Any]] = MappingProxyType({
    "count": 5,
    "verbs": ("move_lid", "move_plate", "move_resource", "stamp", "transfer"),
})
```

**T1 — now a pinned invariant, not a gate (C12).** Count the phase-2 verbs with **zero**
`provenance == "naturalness"` rows over the **10 liquid-handler** verbs. `gap.py` computes it and
asserts it equals `T1_INVARIANT` — both the count (5) and the exact verb set — exiting **1** on
disagreement. Rationale is in §6.5; the short version is that a threshold chosen after computing
its value, over an input Increment 1 does not change, carries no decision information, and PM-2
calls that decoration. As an invariant it does real work: it is a measurement-pipeline check
against a hand-derived expectation, and it fails loudly if the implementation or the corpus
disagrees with §6.5's hand computation.

**T2 — param-shape diversity deficit.** Count the 10 liquid-handler verbs with
`distinct_param_shapes < 3`. The floor of 3 is the matrix's own `examples_per_cell`, not a new
number. **PROCEED requires ≥ 5**, read off `T2_collapsed`. Computed **both ways** — `collapsed`
(numbers unified, §6.2's principled measure, **the gate authority**) and `strict` (revision 1's
type-name behaviour, retained as a robustness probe) — and if the two readings produce different
gate outcomes, `t2_normalization_sensitive: true` and the decision is **CONTESTED (exit 7)**.

**Why the STOP-side rule had to go (W2), with the algebra written out.** Collapsing `int`/`float`
into `"number"` can only *reduce* a verb's distinct-shape count, which can only *raise* the count
of verbs below the floor, so **`T2_collapsed ≥ T2_strict` always**. Since the threshold is a
`>=`, "take the STOP-side answer" means "take the smaller count" means "read `T2_strict`" —
installing the provenance-leaking measure C20 objected to as the effective gate authority in
exactly the case where the answer matters. Revision 2 introduced that rule as an integrity
counter-measure against a self-serving normalization and it inverted into the opposite.

The algebra also says something useful: because the inequality is one-directional, a disagreement
can *only* ever be "collapsed passes, strict fails" — i.e. disagreement occurs **exactly** in the
self-serving direction and never in the conservative one. So the anti-self-serving property
revision 2 wanted is obtainable without handing authority to the leaking measure: make the
disagreement itself the outcome. Exit 7 authorizes nothing, descends nothing, and cannot be
resolved by re-running — resolving it requires picking a reading in a spec revision with a bumped
`GAP_THRESHOLDS_VERSION`, with the disagreement on the table, which is the same reviewable-diff
discipline PM-2 asks of the thresholds themselves.

*Why this is ingestion-shaped:* `floor_gen` synthesizes values from `value_formats.py`'s
hand-pinned conventions, so raising N yields more rows of one dialect, never a new shape.

**T3 — out-of-surface anchor supply (H2's premise, made falsifiable). Matching rule pinned
(C8).** A recipe is an **out-of-surface anchor** iff:

```
none of its method_shaped(token) tokens has token.member ∈ PHASE2_TOOL_NAMES
```

with these clauses, each of which the reviewer correctly flagged as under-specified and each of
which changes the count:

- matching is over `ApiToken.member` — so `lh.drop_tips` has member `drop_tips`, which **is** in
  `PHASE2_TOOL_NAMES`, so that recipe is **in-surface**, not an anchor;
- exact, case-sensitive string equality. Never substring, never prefix;
- only method-shaped tokens participate. `CLASSISH` (`Mix`, `LiquidHandler`), `PROSE`
  (`naming convention`) and `OTHER` (`cor_96_wellplate_360uL_Fb`) tokens are never matched
  against `PHASE2_TOOL_NAMES`;
- **only the `apis` field is scanned.** Neither `path` nor `title` is ever tokenized — so
  `part2/08_tips.qmd#drop-return-discard` cannot make a recipe look in-surface (or
  out-of-surface) through its anchor text. This is the specific failure the reviewer identified,
  and it is now structurally impossible rather than merely unintended.

**PROCEED requires ≥ 25 anchors across ≥ 8 chapters.** The 25 is derived, not invented: the
matrix holds 8 out-of-surface cells at `examples_per_cell: 3` = 24 anchor slots, so 25 is "enough
real anchors to replace every hand-invented `off_surface_request` seed once over."

Two pinned unit tests (`test_ingest_gap.py`): `part1/01_robot_on_screen.qmd#summary`
(`"lh.summary, deck.get_all_children"` — both method-shaped, neither member in
`PHASE2_TOOL_NAMES`) **is** an anchor; a synthetic recipe with `apis: "lh.drop_tips"` is **not**.

*This rule has a second consumer, and stating it here keeps the definition singular (rev 5,
R4-W7).* §5.2's `param_candidate` needs **"the in-surface verbs of a recipe"**, which is the
positive form of the same predicate: `{t.member for t in recipe.api_tokens if method_shaped(t)
and t.member in PHASE2_TOOL_NAMES}`. T3 asks whether that set is empty; `param_candidate`
enumerates it. One definition, one implementation, two callers — which matters because a recipe
can name **two or more** in-surface verbs (recipes.yml 207, 432, 452) and §5.2's
`param_subject(verb, token)` would otherwise have had to invent a tie-break. It does not: it takes
the full cross product over this set.

**Decision rule: PROCEED iff `T2_collapsed` ∧ T3. CONTESTED (exit 7) if the two T2 readings
disagree. Otherwise STOP** and route the measured deficit to `floor_gen` — which is precisely
PM-2's counterfactual: *"the gap was two cells, and floor_gen could have filled two cells
deterministically in an afternoon."*

**`thin_cells` and `empty_cells` are REPORTED BUT NOT GATED, deliberately.** A thin in-surface
cell is a floor_gen problem: `floor_gen --limit` higher fixes it without any new source. Gating
on thin-cell count would let ingestion be justified by a deficit ingestion is not needed for —
the exact sunk-discovery fallacy `[MERGE] ORTHOGONAL-7` was accepted to prevent. `gap_report.json`
states this in `thin_cells_note`.

**G1 is a one-shot decision over frozen inputs, and is treated as one.** All of G1's inputs — the
188-row sidecar, the manifest, the matrix, `recipes.yml` — are committed artifacts that Increment 1
does not modify. Re-running the gate cannot change its answer unless an input changes, so the
report records `corpus_manifest_sha256` and `recipes_yml_sha256`, is committed with its decision,
and **a STOP is not re-litigated by re-running**: reversing it requires a spec revision with a
bumped `GAP_THRESHOLDS_VERSION` and a written rationale, which is a reviewable diff.

### 6.5 Disclosure — what was known when these numbers were chosen

PM-2's requirement is that thresholds be committed before the report decides anything. This
subsection exists so the adversarial reviewer can check for tuning rather than take it on trust,
and rev 2 rewrites it because the reviewer's audit of it was correct.

**T1 (was a gate, now an invariant — C12).** Its value was computed by hand from the committed
`manifest.json` **before** the threshold was chosen: 5 of the 10 liquid-handler verbs
(`transfer`, `stamp`, `move_resource`, `move_plate`, `move_lid`) have zero naturalness rows;
`aspirate` 21, `dispense` 23, `pick_up_tips` 27, `drop_tips` 6, `discard_tips` 3 have some.
Revision 1 then picked a threshold of 4 and argued from the observed value ("passes with a margin
of 1"). Two things are wrong with that and the reviewer named both:

1. It is post-hoc. A threshold selected with the value in hand is a rationalization, and PM-2's
   mitigation exists precisely to forbid it. Disclosure does not repair it.
2. Increment 1 adds **no naturalness rows**, so T1 over the committed sidecar is a **constant**.
   The "gate" could not fail. A gate that cannot fail is decoration, which is the failure PM-2
   named in the first place.

**Rejected alternative, recorded so it is not re-proposed:** re-derive T1's threshold from a
principle instead of the value — e.g. "PROCEED requires that more than half the LH surface is
unmined (≥ 6 of 10)", which is principled *and* currently fails. It is still contaminated: any
line I draw today is drawn knowing the value is 5, and picking the one that flips the outcome is
no better than picking the one that preserves it. **The honest move is to stop calling T1 a
decision.** It becomes an invariant: the implementation must reproduce 5 and the exact five verb
names. That preserves everything T1 was actually good for — validating the metric pipeline against
an independent hand-derivation, per the standing rule that a new metric is sanity-checked against
ground truth before any conclusion rests on it — and removes an authority it never had.

**T2 was NOT computed** and is not computed at the time of writing. Its evaluation requires
executing §6.2's shape function over 188 sidecar rows, which has not been done. It is therefore
genuinely blind pre-registration: from the author's epistemic position the gate can fail.
**Directional disclosure (C20, counter-measure corrected in rev 3 — W2):** collapsing `int`/`float`
into `"number"` can only ever *decrease* a verb's distinct-shape count, which can only *increase*
the low-shape count, which makes T2 **easier** to pass — i.e. more likely to authorize spending.
That is the self-serving direction, so it does not get to stand on the normalization's merits
alone. Revision 2's counter-measure — emit both readings and take the STOP-side answer — was
**self-defeating**: since `T2_collapsed ≥ T2_strict` identically, the STOP side *is* the strict
reading, so the rule quietly restored revision 1's provenance-leaking measure as the authority in
precisely the disputed cases. Rev 3 keeps both readings, makes `T2_collapsed` the authority, and
makes disagreement a third outcome (exit 7, CONTESTED) that authorizes nothing. The
anti-self-serving property survives — a normalization that flips the outcome still cannot buy a
PROCEED — without the inversion. The normalization was specified for an independent reason (it
removes a provenance leak that made T1 and T2 near-collinear), before T2's value was known in
either form, and that remains true.

**T3 was NOT computed.** H2 asserts chapters 10-18 (37 recipes) plus chapters 1-3 (14 recipes) are
almost entirely out-of-surface, so T3 is expected to pass comfortably. **T3 is therefore a premise
check, not a discriminator: if T3 FAILS, H2 was wrong and the plan's central rationale — "the
cookbook's dominant yield is out-of-surface anchors" — has collapsed, which is worth far more than
a gate that merely passes.** C8's matching rule is now pinned in §6.4 *before* the count is taken,
which is what makes this pre-registration rather than a number chosen along with the rule that
produces it.

**Also computed before authoring, and deliberately not gated:** thin cells 23 of 43; empty cells
6 of 43 (`move_resource__missing-slot`, `move_lid__missing-slot`, and the four out-of-surface
cells `dispense_to_waste`, `set_temperature`, `shake`, `stop_shaking`). 53% thin looks like an
overwhelming mandate for ingestion and is in fact an overwhelming mandate for running floor_gen at
full scale, which is a different and cheaper project.

---

## 7. Package layout, imports, and determinism

### 7.1 Layout

```
training/ingest/
    __init__.py
    versions.py          INGEST_VERSION, REGISTRY_VERSION, AUDIT_RULES_VERSION,
                         GAP_THRESHOLDS_VERSION, GAP_THRESHOLDS, T1_INVARIANT,
                         EVAL_SPLIT_VERSION, LICENSE_RULES_VERSION, LICENSE_RULES_SHA256
    io.py                write_artifact, ProtectedPathError, PROTECTED_ROOTS   [ONLY writer]
    sources.py           SourceRow, Genre, ExtractorKind, AdmissionState, RegistryError,
                         load_registry, registry_path, by_id                   (rev 7, C4)
    licenses.py          LicenseTier, LicenseVerdict, LicenseFinding, verify_all,
                         write_report, write_sources_manifest, check_descend, verify_clones
                           -- raises sources.RegistryError; declares no error class of its own
    recipes.py           Recipe, ApiToken, TokenKind, ReceiverType, RecipesError,
                         CookbookUnavailable (RE-EXPORTED from cli.py, defined there),
                         RECIPES_RELPATH, default_recipes_path,
                         load_recipes, split_apis, classify_api_token, method_shaped
    eval_split.py        EvalSplit, load_split, is_held_out, check_corpus_for_leak,
                         assert_no_leak, EvalSplitLeak, load_lineage_contract,
                         load_sidecar_rows, SIDECAR_RELPATH,
                         default_sidecar_path                         (rev 8, C7/C2)
                           -- declares NO cli.IngestError subclass; its one error class
                              (EvalSplitLeak) is the hierarchy's deliberate non-member,
                              and its I/O errors raise cli.IngestError directly (§4.5)
                           -- SIDECAR_RELPATH is used by --emit-lineage-contract ONLY;
                              --check-leak takes its path as --check-leak PATH and has
                              NO default, deliberately (§4.5)
    audit.py             Finding, FindingKind, Evidence, MatchMode, PhantomVerdict,
                         AuditError, ACTION_REF_RE, BLOCKING_KINDS, run_audit, gate,
                         canonical_json, compute_finding_id (R4-B3),
                         canonical_tables_fingerprint, subject_table_fingerprint,
                         load_blocking_census, load_adjudications (R4-W5)
    gap.py               CellGap, VerbGap, GapStats, GapError, INVERSE_CLASS_MAP,
                         run_gap, gate
    cli.py               SHARED CLI PLUMBING ONLY -- NOT a subcommand dispatcher.
                         EXIT_* constants (§9's eight DECISION codes 0-7 plus EXIT_USAGE
                         = 64, R5-W2), IngestArgumentParser (overrides error() so
                         argparse's own sys.exit(2) can never impersonate a gate verdict,
                         and enforces --out for the SIX EMITTER FLAGS -- rev 7, C3; the
                         six are enumerated in this section, and one of them is spelled
                         bare `--emit`, so do not glob on `--emit-*` -- rev 8, C3),
                         the error ROOTS IngestError / CookbookUnavailable / UsageError
                         (DEFINED HERE, never in a command module, or cli.py's error->exit
                         mapping would import them back and cycle), and
                         `run(handler, parser, argv)`, which owns
                         parse_args and maps
                         CookbookUnavailable -> 5, UsageError -> 64, and every other
                         IngestError subclass -> 1, printing the missing path. The
                         COMPLETE class list, its bases and its exits are the normative
                         table below -- read that table, not this line, and note it lists
                         the one error class that is deliberately OUTSIDE the hierarchy
                         (eval_split.EvalSplitLeak -> 6).  Every module's __main__ block
                         routes through run(), so §7.5's convention is implemented once
                         instead of five times.                                [Task 1]
    __main__.py          `python -m ingest` -- a SIGNPOST, not a dispatcher: --help (or
                         no args) prints the five module commands and exits 0; any other
                         argument exits 1 naming the module form. AC-1.0 gates this.
                         Imports NONE of the five command modules -- §7.3(a) rule 3
                         enforces that statically, which is what makes "there is no
                         dispatcher" structural rather than behavioural (R5-W3). It does
                         not use IngestArgumentParser either: its two branches are hand-
                         written, so 64 never appears here.                [Task 1]
    data/                HAND-AUTHORED (6, §5.6d): sources.json, license_rules.json,
                         audit_adjudications.json, experimental_partition.json,
                         import_closure_allowlist.json, receiver_aliases.json
                           -- receiver_aliases.json's VALUES are hand-assigned; only its
                              KEY SET is mechanically derivable (R3-B3, §3.3 rule 5)
                         COMPUTED-THEN-COMMITTED (5, §5.6d): eval_split.json,
                         canonical_tables_fingerprint.json, token_histogram.json,
                         lineage_contract.json, blocking_census.json        [COMMITTED]
    out/                 license_report.json, SOURCES.md, audit_report.json,
                         audit_findings.jsonl, gap_report.json              [COMMITTED, generated]
```

*Rev 4 (R3-W5): revision 3's layout implied a 5+5 split, §5.6(d)'s table gave a different 5+5,
§0.4's W12 row said "six and four", and §12.11 said "four" over five filenames. The authoritative
count is **6 hand-authored + 5 computed = 11**, and it changed for two substantive reasons rather
than by recounting: `blocking_census.json` is new (R3-B2) and `receiver_aliases.json` moved from
computed to hand-authored (R3-B3). §5.6(d), this layout and §12.11 now agree; §0.4 is preserved as
history and superseded by §0.5.*

*`versions.py` deliberately gains **no** census constant. The census is a fact about the live
cookbook, so it belongs in `data/` behind the copy-and-review workflow (§5.6d), not beside the
pre-registered thresholds — a hard-coded census in `versions.py` or `audit.py` would be exactly
R2-B1's hand-listed constant returning through the door its own fix opened. **Rev 5 adds the same
reasoning for the recipe count**: `RECIPE_COUNT = 91` does not appear in `versions.py` or in
`recipes.py` either; it is `token_histogram.json`'s `n_recipes` (R4-B1, §3.1).*

#### The entry-point shape, stated once and obeyed everywhere (rev 5, R4-B2)

**`python -m ingest.<module> <flags>` — module-per-command. There is no shared subcommand
dispatcher, and `python -m ingest <subcommand>` is not a thing.**

Each of `licenses.py`, `recipes.py`, `eval_split.py`, `audit.py`, `gap.py` owns its own
`argparse.ArgumentParser`, its own flags, and its own guard:

```python
# tail of every one of the five command modules -- five copies, deliberately
def _main(argv: Sequence[str] | None = None) -> int:
    p = cli.IngestArgumentParser(            # NOT argparse.ArgumentParser
        prog="python -m ingest.audit",
        out_required_for=("emit_census", "emit_fingerprint"),   # rev 7, C3
    )
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--report", action="store_true")
    g.add_argument("--gate", action="store_true")
    g.add_argument("--emit-census", action="store_true")
    g.add_argument("--emit-fingerprint", action="store_true")
    p.add_argument("--out", type=Path)        # REQUIRED with this module's EMITTER flags
                                              # and with nothing else. The authority is
                                              # out_required_for above -- copy that tuple
                                              # from your module's row in the table below,
                                              # do NOT re-derive it by globbing --emit-*
                                              # (eval_split's flag is bare --emit, rev 8 C3)
    ...
    return cli.run(_dispatch, p, argv)        # cli.run owns parse_args, so UsageError
                                              # is caught in ONE place, not five

if __name__ == "__main__":
    raise SystemExit(_main())
```

**The last two lines are the ones with a detector now, and revision 5's did not have one (rev 6,
R5-B1).** Revision 5 corrected the entry-point *shape* and installed nothing that observes it —
while, in the same revision, making "tests drive handlers **in-process**" an explicit package rule
(§5.5's injection note, §7.4's gate-output paragraph, §7.5's per-row exits, Task 6's "every
assertion drives `audit.gate(...)` in-process"). Every one of those rules is right, and together
they left the `if __name__ == "__main__":` block as **the one link in the chain no test crossed**.
Omit it from `audit.py` and `python -m ingest.audit --gate` imports the module, runs its body,
ignores `--gate` and exits **0** — R4-B2's failure verbatim, surviving inside R4-B2's own fix,
with every specified test green. It is sharpest here because `audit --gate` is the only gate whose
CLI form writes **no artifact**: Task 2's "writes both artifacts" and Task 7's "writes
`gap_report.json`" would catch a missing guard incidentally, and §9's G2 row has nothing to fall
back on.

**Named as round 3's standing rule requires — the event, and the observation that fires.** The
event is *a command module reaching `__main__` without a guard*. The observation is Task 8's
`test_ingest_entrypoints.py`: `runpy.run_module(f"ingest.{m}", run_name="__main__")` over all five
modules, asserting `SystemExit` with the expected code. A missing guard produces **no `SystemExit`
at all** — `run_module` returns a namespace — so the test fails on the `pytest.raises` itself and
names the module. It stays in-process (no subprocess), so F3 and §7.3 are untouched; `runpy` is
banned *inside* `training/ingest/`, not in a test that drives it from outside (§7.3(a)'s scope
paragraph). The five copies of these two lines are still deliberate; what changed is that copying
them wrong is now a red test rather than a silent pass.

**All five parsers use `add_mutually_exclusive_group(required=True)`, and that is now
load-bearing.** It was a stylistic choice in revision 5; from revision 6 it is what makes
"invoke the module with no arguments" a uniform, artifact-free, clone-independent probe with one
expected answer (`EXIT_USAGE`) across all five. `gap.py` currently has a single subcommand
(`--gate`) and its group therefore has one member — keep the group anyway rather than defaulting
`--gate` to true, because a module that does something useful with no arguments cannot be probed
this way, and `gap --gate` is a decision gate that should never run by accident.

**Why the parser is `cli.IngestArgumentParser` and not `argparse.ArgumentParser` (rev 6, R5-W2).**
Revision 5 promoted a bare `argparse` parser to normative code and, in the same revision, §9
declared a **closed** package-wide exit vocabulary in which **2 means "unadjudicated blocking
finding"**. Those two statements are incompatible, and the incompatibility is `argparse`'s, not
ours: on any usage error — no flag at all (the group is `required=True`), a mistyped flag, an
unrecognized argument — `ArgumentParser.error()` prints usage and calls `sys.exit(2)` **before
`cli.run` or any handler is reached**. So `python -m ingest.audit` with a typo exits **2**,
byte-identical to a real G2 drift failure, and a CI wrapper keyed on `exit == 2` reports contested
canonical tables when what actually happened was a misspelled flag. §7.5 spends a paragraph arguing
that `audit --gate` must never return an unearned 2 — *"returning 2 would be indistinguishable from
a real drift failure"* — and `argparse`'s default reintroduces exactly that through a door revision
5 did not know was open.

```python
# cli.py
EXIT_USAGE: Final[int] = 64     # sysexits.h EX_USAGE. Deliberately OUTSIDE 0-7 (§9).

# IngestError / CookbookUnavailable / UsageError are DECLARED ONCE, in the hierarchy
# block below in this same file. Rev 7 (C2) deleted a second, disagreeing declaration
# of UsageError that stood here: it read `class UsageError(Exception)` while the block
# below read `class UsageError(IngestError)`, and the prose at the end of this section
# is only true of the second.

class IngestArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, out_required_for: Sequence[str] = (), **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._out_required_for = tuple(out_required_for)   # dest names, e.g. "emit_census"

    def error(self, message: str) -> NoReturn:          # argparse's ONLY error funnel
        raise UsageError(f"{self.prog}: {message}\n\n{self.format_usage()}")

    # rev 7, C3. Signature MIRRORS argparse.ArgumentParser.parse_args exactly -- do not
    # rename the first parameter to `argv`: argparse itself calls parse_args(args=...,
    # namespace=...) by keyword internally, and a renamed override raises TypeError.
    def parse_args(self, args=None, namespace=None):
        ns = super().parse_args(args, namespace)
        for dest in self._out_required_for:
            if getattr(ns, dest, False) and getattr(ns, "out", None) is None:
                self.error(f"--out is required with --{dest.replace('_', '-')}")
        return ns                                       # -> self.error -> UsageError -> 64

def run(handler, parser, argv=None) -> int:
    try:
        args = parser.parse_args(argv)                  # includes the --out check above,
    except UsageError as exc:                           # so 64 precedes every clone check
        print(exc, file=sys.stderr)
        return EXIT_USAGE
    try:
        return handler(args)
    except CookbookUnavailable as exc:                  # -> 5, §7.5. MUST precede the next
        ...                                             #    clause; it is a subclass
    except IngestError as exc:                          # every other member of the table
        ...                                             # below  -> 1
```

**The exception hierarchy has to live in `cli.py`, or `cli.py` cannot be imported (rev 6).** This
is not a new decision so much as a hole revision 5 left when it gave `cli.run` the job of mapping
*"`AuditError`/`RecipesError`/`RegistryError`/`GapError` → 1"* (revision 5's wording; the live list
is the table below, and rev 7 adds `io.ProtectedPathError` to it): those classes live in the
command and support modules, every one of which imports `cli` for `EXIT_*` and `run()`, so a
`cli.py` that
imports them back is a **circular import** and the package does not load. A fixer meets this on the
first `python -m ingest.audit --report`, which is the same day-one class of defect as R4-B1's
unparseable fixtures and R4-B2's missing guard. The resolution costs two classes and no
indirection:

```python
# cli.py -- the package's error ROOTS. cli.py imports NOTHING from this package --
# not just no command module, but no sibling ingest module at all (io.py and
# versions.py included). §7.3(a) rule 4 enforces that statically. (Rev 8, C6:
# this comment used to read "no command module", a narrower scope than the rule
# it was restating; narrow-then-broad is safe, but two scopes for one rule is
# how §7.1's hierarchy came apart in round 6.)
class IngestError(Exception): ...                 # -> exit 1
class CookbookUnavailable(IngestError): ...       # -> exit 5, checked FIRST (§7.5)
class UsageError(IngestError):                    # -> exit 64, caught before the handler
    """A malformed command line. NOT a measurement, NOT a verdict."""
```

##### The complete exception hierarchy, as a table, because prose was not enough (rev 7, C1)

**This table is the single normative statement of the package's error classes. Every other section
of this document that names one of them defers to it, and none of them redeclares one.** Revision
6 stated this design in the paragraph above and *only* there; §2.1, §3.1, §5.7, §6.1, Task 1 and
Task 3 all kept the pre-fix spelling, and §3.1 in particular declared `CookbookUnavailable` in
`recipes.py` with base `RecipesError` — so a fixer writing `recipes.py` from §3.1 rebuilt the exact
circular import this design removes (round 6, C1). A table is harder to half-apply than a sentence,
and it is the artifact Task 8's hierarchy test is written against.

| class | defined in | base | `cli.run` maps it to |
|---|---|---|---|
| `IngestError` | **`cli.py`** | `Exception` | **1** — the catch-all clause, last |
| `CookbookUnavailable` | **`cli.py`** | `IngestError` | **5** — its `except` clause is **first** (§7.5) |
| `UsageError` | **`cli.py`** | `IngestError` | **64** — caught around `parse_args` only, never around the handler |
| `RegistryError` | `sources.py` | **`cli.IngestError`** | 1 (§2.1; also raised by `licenses.py`, which declares no error class of its own) |
| `RecipesError` | `recipes.py` | **`cli.IngestError`** | 1 (§3.1) |
| `AuditError` | `audit.py` | **`cli.IngestError`** | 1 (§5.7, §5.3) |
| `GapError` | `gap.py` | **`cli.IngestError`** | 1 (§6.1) |
| `ProtectedPathError` | `io.py` | **`cli.IngestError`** | 1 (§5.6a) — **rev 7**: it was `RuntimeError`, so a protected-path write escaped `run()` as an uncaught traceback rather than the measurement error it is |
| `EvalSplitLeak` | `eval_split.py` | `RuntimeError` — **deliberately NOT `IngestError`** | **nothing.** It never reaches `cli.run`: `--check-leak`'s handler catches it and **returns 6** (§9's G5). Making it an `IngestError` would let the catch-all clause remap G5's leak verdict to 1, silently deleting the only exit code the eval-leak gate can produce. **The handler's `try/except` is normative code in §4.5, and Task 4 drives a leaking fixture through `_main` asserting exactly 6 (rev 8, C1)** — without both, this row's exclusion is *worse* than membership, because a handler with no `try/except` lets the leak escape as an uncaught traceback → exit **1**, the very outcome the exclusion exists to prevent |
| `MatrixError` | **not ours** — `coxswain.plr` | — | out of scope; §2.2 and §6.1 cite it as a *style* precedent for raising loudly, never as a base class |

Three rules follow from the table and are stated so a fixer does not have to infer them:

1. **`recipes.py` does not declare `CookbookUnavailable`; it re-exports it.** Literally
   `from .cli import CookbookUnavailable` plus an `__all__` entry, so §7.1's inventory line stays
   true and every `from ingest.recipes import CookbookUnavailable` in the tests keeps working
   (§3.1). A `class CookbookUnavailable(RecipesError)` anywhere is the defect, not the design.
2. **The import direction is one-way and total.** `cli.py` imports nothing from this package —
   no sibling ingest module of any kind, not merely no *command* module — while
   `sources.py`, `io.py`, `recipes.py`, `eval_split.py`, `audit.py` and `gap.py` all import `cli`.
   That is what makes the hierarchy expressible at all — the reason the roots cannot live in the
   command modules is that `cli.run`'s `except` clauses would have to import them back.
   **§7.3(a) rule 4 enforces this statically** (rev 8, C6): zero `ast.Import`/`ast.ImportFrom`
   nodes naming a sibling ingest module in `cli.py`, in any spelling. The cross-reference is stated
   here because rule 4 and §7.3(a)'s rule 3 (`__main__.py`'s import ban) are the same shape and the
   layout block above already carries rule 3's — one of a matched pair citing its enforcement and
   the other not is how a reader concludes the second is only a convention.
3. **The `except` ordering in `run()` is load-bearing.** `CookbookUnavailable` is a subclass of
   `IngestError`, so its clause must come first or every absent clone reports exit 1 instead of 5 —
   R2-B4's original contradiction re-entering through Python's MRO. `run()` catches `UsageError`
   around `parse_args` only: a handler that raises it would be a bug, and letting it fall through
   to `IngestError` → 1 is the right answer for a bug — which is *why* `UsageError` subclasses
   `IngestError` rather than `Exception`, and the sentence you are reading is false under any other
   base.

**Named as round 3's standing rule requires — the event, and the observation that fires.** The
event is *a module declaring one of these classes with the wrong base, or in the wrong file*.
The observation is Task 8's `test_ingest_error_hierarchy.py`: it asserts
`issubclass(X, cli.IngestError)` for all five per-module classes, asserts each one's
`__module__` is the module the table's second column names — **as a dotted import path**
(`ingest.sources`, `ingest.recipes`, `ingest.audit`, `ingest.gap`, `ingest.io`), since that column
shows *filenames* and `__module__` is never a filename (rev 8, C5; Task 8 spells the five out) —
asserts `not issubclass(eval_split.EvalSplitLeak, cli.IngestError)`, and asserts
`recipes.CookbookUnavailable is cli.CookbookUnavailable` — object identity, which a redeclaration
in `recipes.py` fails even though a name-only check would pass. A behavioural companion drives
`io.write_artifact` at a protected path through `cli.run` and asserts **1**. Round 6's finding was
that revision 6's fix had no such observation anywhere, so five sections could contradict it and
the suite stayed green.

**Override `error()`, not `exit_on_error=False` — and the difference is the whole fix.** `argparse`
gained an `exit_on_error` constructor flag in 3.9, and it is the obvious-looking answer. It is
**incomplete**: it converts only the errors raised from argument *conversion* into
`argparse.ArgumentError`, and leaves the checks performed after parsing — a missing
`required=True` mutually-exclusive group, an unrecognized argument — going through `error()` to
`sys.exit(2)` regardless. A fixer who reaches for it closes half the hole and cannot tell which
half. `error()` is the single funnel every usage failure passes through, so overriding it is both
sufficient and complete. **`--help` is unaffected:** `-h` routes through `parser.exit(0)`, not
through `error()`, so it still prints help and exits 0, which is what AC-1.0 gates for
`__main__.py` and what a user expects from every module.

**`--out` is required with each of the six emitter flags, and it is the parser that enforces it
(rev 7, C3; wording corrected rev 8, C3).** Revision 6 wrote `p.add_argument("--out", type=Path)`
with the comment *"required by the
`--emit-*` flags"* and stopped there, leaving the mechanism unstated — and the two candidate
mechanisms land on **opposite sides of the boundary revision 6 had just drawn**: parser-enforced
means a missing `--out` is a usage error → **64**, handler-validated means it is a measurement
error → **1**. Before revision 6 there was no 64 and the question did not arise; drawing the
boundary is what made the silence consequential. It is parser-enforced, for the same reason
`error()` is overridden rather than each module checking its own argv: one funnel, five modules.

Plain `required=True` is **wrong** and must not be used — `--gate`, `--report`, `--check-descend`
and `--check-leak` all run with no `--out` and write nothing, so an unconditional requirement would
break every gate in §9. The requirement is conditional on the flag, which `argparse` cannot express
declaratively, which is why `IngestArgumentParser` takes `out_required_for=` and checks it in
`parse_args` **through `self.error()`** — the same funnel, so there is no second error path and no
second exit code to keep consistent.

***The six emitter flags, named, because "`--emit-*`" is a glob and one of the six does not match
it (rev 8, C3).*** Revision 7 stated the rule as a pattern over flag names. Five of the six flags
fit that pattern; `eval_split`'s does not — it is spelled bare **`--emit`**. A fixer applying the
rule literally writes `out_required_for=("emit_lineage_contract",)` for `eval_split.py`, and
`python -m ingest.eval_split --emit` with no `--out` then reaches the handler instead of exiting
64, contradicting §7.5's row for it — a silent hole in exactly the module whose flag name was the
reason to look. The rule is therefore stated over an **enumerated set**, not a pattern, and each
module's tuple is stated at its own task as well:

| module | `out_required_for=` | flags it covers | stated at |
|---|---|---|---|
| `recipes.py` | `("emit_histogram", "emit_receiver_alias_keys")` | `--emit-histogram`, `--emit-receiver-alias-keys` | Task 3 |
| `audit.py` | `("emit_census", "emit_fingerprint")` | `--emit-census`, `--emit-fingerprint` | the template above |
| `eval_split.py` | `("emit", "emit_lineage_contract")` | **`--emit`** (bare — the exception), `--emit-lineage-contract` | Task 4 |
| `licenses.py`, `gap.py` | `()` — the default | none; neither module has an emitter | — |

Values are `argparse` **dest** names (underscored), not flag spellings, because that is what
`getattr(ns, dest)` reads. Six flags, **three non-empty tuples** across five command modules, and
§7.5's exit-64 row expands to exactly these six commands.

**Ordering, stated because both conditions can be true at once.** `cli.run` calls `parse_args`
*before* the handler, and every clone check lives in a handler. So the `--out` check **always
fires first**: `python -m ingest.audit --emit-census` with neither `--out` nor a cookbook clone
exits **64**, not 5. This is the third two-condition ordering the spec pins (after `audit --gate`'s
clone → census, R4-W10, and `recipes --emit-receiver-alias-keys`' clone → committed-file, R5-S3),
and unlike those two it is not a judgment call: it falls out of `run()`'s structure, and stating it
here is what stops a fixer from "fixing" it by moving the check into the handler. §7.5's table
carries the row.

**Why 64 and not a ninth low code.** §9's codes 0–7 are **decisions** — a gate ran and produced an
answer, or declared it could not. A malformed command line is not a decision about anything, and
giving it a number inside the same range invites a wrapper to interpret it as one. `sysexits.h`'s
`EX_USAGE` is the long-standing convention for exactly this, it is far outside the range any gate
consumer reads, and it makes the honest statement §9 now carries: **eight decision codes, plus one
code that says "no decision was reached because the command line was wrong."**

**What revision 4 said, and why it was a silent-pass defect rather than a style disagreement.**
§7.1 read *"`cli.py` / `__main__.py` argparse subcommands, mirroring `floor_gen/cli.py`"*. The
live precedent is unambiguous: `training/floor_gen/__main__.py` is four lines delegating to
`floor_gen.cli.main`, and `cli.py:169` is `parser.add_subparsers(dest="command", required=True)`
with `generate` / `batches` / `regenerate` — so the mirrored form is **`python -m floor_gen
<subcommand>`**, never `python -m floor_gen.<module>`. Under that reading,
`python -m ingest.audit --gate` imports `ingest/audit.py` as `__main__`, finds no
`if __name__ == "__main__":` block, runs the module body, ignores `--gate` entirely, and **exits
0**. A blocking gate that passes vacuously is PM-2's waived gate and PM-3's unowned obligation at
the same time — arrived at not by anyone deciding to waive anything, but by two sections of this
document spelling one command differently.

**Why the module-per-command form wins, and it is not a close call.** The dispatcher form appears
**once**, in a single parenthetical in §7.1. The module form appears in AC-1.0's sibling ACs
1.2/1.3/1.6/1.7/1.9/1.13/1.15/1.17, in all five of §9's gate rows, in all fourteen rows of §7.5's
table, and in Tasks 0/2/4/6/7 — upwards of thirty invocations. The banner's rule applies: when two
places spell the same thing differently, the one that appears once loses.

**What `cli.py` is for, now that it is not a dispatcher.** §7.5's convention — *every* command
maps `CookbookUnavailable` to exit 5 and prints `default_recipes_path()` plus the `git clone` line
— is one rule that five modules must obey identically. Writing it five times is five chances to
write it four ways. `cli.run(handler, parser, argv)` is the single implementation: it parses,
calls the handler, returns its int, and converts the package's typed errors to exit codes. The
`argparse` *surface* stays per-module (each command's flags are its own business); only the
parser **class**, the error→exit mapping and the `EXIT_*` constants are shared. This is the one
genuine thing the dispatcher design was buying, kept without the entry-point shape that broke
every gate.

*Rev 6 (R5-W2) moved `parse_args` inside `run()`.* Revision 5 had each module call
`p.parse_args(argv)` itself and hand the result to `cli.run`, which put the usage-error path
**outside** the one function that owns exit codes — five modules, five chances to handle
`UsageError` four ways, which is the identical argument this paragraph already makes about
`CookbookUnavailable`. Passing the parser instead of the parsed args costs nothing and puts every
exit code the package can produce behind one `try`.

**What `__main__.py` is for.** AC-1.0 gates `python -m ingest --help` exiting 0, and that AC is
worth keeping: it is the cheapest possible proof that `ingest` is importable as a package from the
repo root after Task 1's editable reinstall (C15). So `__main__.py` exists, prints the five module
commands with a one-line description each, and exits 0. It **never dispatches** — passing it a
subcommand name exits 1 with a message naming the `python -m ingest.<module>` form. A dispatcher
here would re-create exactly the ambiguity this section removes, by making two spellings work.

*Rev 6 (R5-W3): "never dispatches" now has three observations behind it, where revision 5 had one
and it was weaker than its stated conclusion.* (i) The **malformed** probe stays: `python -m ingest
licenses` exits 1. (ii) A **well-formed** probe is added: `python -m ingest licenses --report` —
the invocation a real dispatcher would service — exits 1 **and leaves `training/ingest/out/`
byte-identical**, which a dispatcher could not do because `licenses --report` writes two artifacts.
(iii) The **structural** fact, which is the one that actually closes it: §7.3(a)'s third ban proves
`__main__.py` imports none of the five command modules, so it cannot dispatch to any of them on
*any* input. Two spellings can never both appear to work because only one of them has a handler
reachable from the file. `__main__.py` is also the one place in the package that does **not** use
`cli.IngestArgumentParser`: its two branches (`--help`/no args → signpost, exit 0; anything else →
redirect, exit 1) are hand-written, so R5-W2's exit **64** never appears here and the redirect's
exit 1 stays the unambiguous signal Task 1 tests for.

**The ordering defect, and its fix.** AC-1.0 is gated at **Task 1**, while revision 4 created
`cli.py` and `__main__.py` in **Task 6** — so AC-1.0 was unsatisfiable when Task 1 ran, and Tasks
2–5's gates (`licenses --report`, `recipes --emit-histogram`, `eval_split --check-leak`,
`audit --emit-census`) each invoked CLI machinery that did not exist yet. Both files move to
**Task 1**, with the package scaffold. That is also the right home on the merits: `cli.py` holds
the exit-code vocabulary, which every later module imports, and a scaffold task is where shared
plumbing belongs.

### 7.2 Packaging and importability (C15)

`training/pyproject.toml` gains `"ingest*"` in `[tool.setuptools.packages.find].include`.
**Extend the `include` list; do not replace the block** — the file's own comment says so
explicitly, and four parallel sub-pipelines share it.

Import path is bare `ingest` (not `training.ingest`), matching `floor_gen` / `overlay_gen` /
`assemble`. **`training/conftest.py` does not put `training/` on `sys.path`** — it is a docstring
only; what makes `import floor_gen` work under pytest is pytest's rootdir-conftest `sys.path`
insertion, which is a *pytest* behaviour and does nothing for a bare `python -m`. Six of this
spec's acceptance criteria invoke `python -m ingest.*`, so Task 1 must **also** refresh the
editable install (`uv sync --reinstall-package training`); setuptools bakes a static package
mapping into the editable finder, so a `packages.find` edit alone leaves `ingest` unimportable.
**AC-1.0 gates exactly this**, run from the repo root.

### 7.3 F3 purity, proven transitively (C14)

Revision 1's AC-1.11 scanned only `training/ingest/` and whitelisted "a sibling `training/`
package" — while `gap.py` is *required* by §6.1 to import `assemble.build.CLASS_MAP`, and
`training/assemble/build.py:27` is `import subprocess` (used by `plr_source_sha()` to shell out to
`git submodule status`). So the purity gate passed while F3's stated property was false.

**The obvious fix does not work, and is recorded here so it is not re-proposed.** Extracting
`CLASS_MAP` into a dependency-free `training/assemble/classes.py` does not help: `assemble/__init__.py`
does `from .build import (...)`, so importing *any* `assemble.*` submodule executes the package
`__init__` and pulls `subprocess` in regardless. Removing that re-export would change another
sub-pipeline's public surface for this spec's convenience, which is out of scope.

The property that actually matters is **no subprocess ever executes**, and it is provable:

**(a) Direct bans — three of them, one AST walk.** No module under `training/ingest/` may
`import subprocess`, `os.system`, `eval`, `exec`, `importlib`, or `runpy`. AST-decidable; unchanged
from revision 1.

**And, new in rev 5 (R4-W9): no module under `training/ingest/` may contain a bare `assert`
statement** — zero `ast.Assert` nodes, over the same walk. This is a *purity* ban only by
adjacency; it lives here because it is the same shape (an AST-decidable statement-level ban over
the same module set) and a second walk over the same files would be waste. AC-1.11's "three
properties" is unchanged — this is a second rule inside property (a), not a fourth property.

*Why it replaced a test that could not be written.* Revision 4's Task 5 asked for *"a second test
[that] runs the same case under `python -O` semantics (`assert` disabled)"*, to prove R3-W7's
`scope="none"` guard survives optimization. **There is no such mechanism.** `-O` is decided at
interpreter start; asserts cannot be disabled inside a running process, so the only implementation
is a `subprocess` call — which §7.3 itself bans in ingest modules, and which the spec never scoped
for tests. Meanwhile the property being probed is *"this guard is a raise, not an assert"*, and
that is a **static** property of the source, provable completely and cheaply. The AST ban is
strictly stronger than the `-O` probe in three ways: it covers **every** invariant in the package
rather than one code path (§5.7's dispatch guard, §5.7's `_SCOPED` totality check, §6.1's
`CLASS_MAP` injectivity check, §5.3's partition loader, §3.1's reader, §2.2's registry); it fails
at lint time rather than at the one moment someone runs `-O`; and it needs no subprocess. Round 3
identified the `-O` hazard correctly (R3-W7) and revision 4 fixed the two guards it named — this
makes the *house rule* those fixes established mechanically enforced, so the next invariant added
cannot regress to an `assert`.

**And, new in rev 6 (R5-W3): `ingest/__main__.py` imports none of the five command modules** —
zero `ast.Import`/`ast.ImportFrom` nodes naming `ingest.licenses`, `ingest.recipes`,
`ingest.eval_split`, `ingest.audit` or `ingest.gap` (in any spelling: absolute, relative `.audit`,
or `importlib` — which (a)'s first ban already forbids outright). This is the **third** rule inside
property (a), over the same walk; AC-1.11's "three properties" is still unchanged.

*Why a static rule and not another behavioural probe.* §7.1 asserts that the package has **no**
subcommand dispatcher, and revision 5 tried to observe that with one behavioural probe: `python -m
ingest licenses` exits 1. Round 5 showed the probe does not support its own conclusion (R5-W3) — it
tests a *malformed* dispatcher call, and a hybrid (a real dispatcher in `__main__.py` **plus** the
five module guards) that maps its own usage errors to 1 passes it while `python -m ingest licenses
--report` also works. Task 1 now adds the well-formed probe too, but the general problem with
behavioural probes here is that "no dispatcher exists" is a claim about *every* possible
invocation, and no finite set of invocations proves it. The structural fact does: **a dispatcher
must import a handler.** A file that imports none of the five cannot dispatch to any of them, on
any input, and that is decidable from the AST in one pass. The signpost's five-command list is
therefore **literal text**, deliberately not derived by importing the modules to read their
docstrings — the small duplication is what buys the property.

**And, new in rev 7 (C1): `ingest/cli.py` imports no other module of this package** — zero
`ast.Import`/`ast.ImportFrom` nodes naming any sibling ingest module, in any spelling. This is the
**fourth** rule inside property (a), over the same walk; AC-1.11's "three properties" is *still*
unchanged, because these are rules within property (a), not new properties.

*Why this one is worth an AST rule rather than a comment.* §7.1's exception hierarchy exists for
exactly one reason: `cli.run` must catch the per-module error classes, so `cli.py` cannot import
them, so the roots have to live in `cli.py`. That argument is only sound while the import direction
stays one-way, and the direction is currently protected by nothing but a comment — the same
condition round 6 found the whole hierarchy in. A fixer adding, say, `from . import recipes` to
`cli.py` for a default path re-creates R5-W2's circular import, and the symptom is an
`ImportError` on the first `python -m ingest.<anything>` rather than a failing assertion that
names the cause. One AST rule on one file converts a day-one runtime failure into a lint. It is
the same shape as the `__main__.py` ban above and rides the same walk.

*Scope, stated because it is easy to over-apply.* All four bans cover `training/ingest/**.py`
only; the third narrows further to the single file `training/ingest/__main__.py` and the fourth to
`training/ingest/cli.py` — every other ingest module imports its siblings freely and must
(`audit.py` reads `recipes.py`; all of them read `cli.py`).
`training/tests/**` is untouched by any of them — a test suite is supposed to `assert`, and pytest
rewrites those asserts anyway; and Task 8's entry-point test (R5-B1) uses `runpy`, which is banned
**inside** `training/ingest/` and perfectly legal in a test that drives it from outside.

**(b) Transitive closure, allowlisted.** The test computes the transitive import closure of the
ingest modules and asserts every member falls into one of five **explicitly named** categories
(rev 3 spells them out — W14; revision 2 wrote "stdlib, `coxswain.*`, a `training/` sibling",
which a reader has to *guess* covers the fourth):

1. **stdlib** — the Python standard library.
2. **`coxswain.*`** — the canonical tables and their dependencies.
3. **A `training/` sibling top-level package** — `floor_gen`, `overlay_gen`, `assemble`, `verify`.
   These live at `training/<name>/` and are on the path via `packages.find`'s `where = ["src", "."]`.
4. **`praxis_training.*`** — which lives at **`training/src/praxis_training/`**, *not* at
   `training/praxis_training/`, and is reached transitively via
   `training/assemble/build.py:35`'s `from praxis_training.golden_build.corpus import
   DECLARED_ARRAY_PARAMS, DEVELOPER_SCAFFOLD`. This edge is real and revision 2 never named it.
   Round 2 verified the modules it pulls (`praxis_training`, `praxis_training.golden_build`,
   `praxis_training.golden_build.corpus`) import only stdlib + `coxswain.plr.*`, so the edge is
   clean — but "clean" and "categorized" are different properties, and only the second is a
   spec's job.
5. **Allowlisted** — any module in the closure that itself imports a banned name must be present
   in `data/import_closure_allowlist.json` with a reason.

The **observed** closure today is `assemble`, `assemble.build`, `assemble.scaffold`,
`praxis_training`, `praxis_training.golden_build`, `praxis_training.golden_build.corpus`,
`floor_gen.matrix`, `overlay_gen.miner`, and `coxswain.plr.*`. Round 2 confirmed that the
allowlist's "exactly one entry today" claim is **true** against that closure. The file:

```jsonc
{"allowlist": [
  {"module": "assemble.build",
   "imports": ["subprocess"],
   "reason": "plr_source_sha() shells out to `git submodule status`; ingest imports only CLASS_MAP and never calls it. Reached transitively via assemble/__init__.py, which re-exports build.",
   "proof": "test_ingest_import_purity.py::test_no_subprocess_executes"}
]}
```

A *new* leaky edge appearing in the closure fails the test until someone writes it down — which is
the F5 discipline applied to imports.

**(c) Runtime proof, stronger than any scan.** `test_no_subprocess_executes` runs the full
pipeline (`licenses --report`, `audit --report`, `audit --gate`, `gap --gate`) into a `tmp_path`
with `subprocess.run`, `subprocess.Popen`, `subprocess.call` and `os.system` patched to raise, and
asserts the run completes. This observes the property directly; (a) and (b) exist to keep it
cheap to reason about.

### 7.4 Determinism (F6, AC-1.10)

Every JSON artifact is written with `json.dumps(obj, indent=1, sort_keys=True,
ensure_ascii=False)` + a trailing newline, through `io.write_artifact`; every JSONL artifact is
sorted by its id field. **No `datetime.now()`, no `generated_utc`, no absolute paths, no
`os.environ` inside any payload.**

**This is the ARTIFACT serializer, and it is deliberately not the HASH serializer (rev 5,
R4-B3).** §5.2 defines `canonical_json` — `sort_keys=True, separators=(",", ":"),
ensure_ascii=True, allow_nan=False`, encoded to bytes — and it is the input to `finding_id`,
`adjudicable_digest`, `canonical_tables_fingerprint()` and `subject_table_fingerprint()`. The two
differ on `indent` and on `ensure_ascii` because they are for different readers: an artifact is
diffed by a human, so it is indented and left in UTF-8; a hash input is never read, so it is
compact and ASCII-escaped, which removes any dependence on a payload's encoding from the digest.
`sort_keys=True` is common to both and is the one property neither can do without. Revision 4 pinned
this paragraph and left `canonical_json` undefined, so the *committed* half of the contract had a
spec and the *hashed* half — the half AC-1.7 and AC-1.14 require exact equality against — did not. Run metadata a human wants (wall time, host) goes to
`logging`/stderr, never into the file. The one date-sensitive check in this spec (AC-1.12's
deadline, §2.8) lives in a **test** and injects `today`, so no artifact byte depends on the clock.

*This deliberately does not copy `overlay_gen/out/mined_calls_smoke.json`, whose top-level
`"generated_utc": "2026-08-27T15:14:19Z"` makes that artifact non-reproducible; the new package
must not inherit the defect.*

**Reports are committed.** `floor_gen` already commits its `out/` smoke corpus and `assemble`
commits its manifest; the five ingest artifacts follow suit so a reviewer diffs the *change* in
the audit and the gap, not just the code that produced them.

**Diagnostics:** the repo standard is `tracing` for Rust; this is Python, so use
`logging.getLogger(__name__)`, never `print`, except in **gate output** — the failing-`finding_id`
list, the `census_drift` lines, and the clone-absent remedy — where the text on stdout *is* the
interface alongside the exit code. *Rev 5 (R4-B2): revision 4 located that exception in `cli.py`,
which under the corrected §7.1 holds only the exit-code mapping and the error roots. Gate output is
written by the gate itself (`audit.gate(..., out=sys.stdout)`, §5.5), which is what makes it
assertable in-process without capturing a subprocess.* *Rev 6 (R5-B1): "assertable in-process" is
still the right design and it is exactly what left the `__main__` guard unobserved — every rule in
this spec pushed tests one layer below the command line, so nothing ever executed the command line.
Task 8's `test_ingest_entrypoints.py` closes that one layer with `runpy`, still without a
subprocess.*

### 7.5 Behaviour when the clones are absent — exit 5 is a package-wide convention (R2-B4)

Revision 2 introduced exit **5 = INCONCLUSIVE** as C6's fix for one command (`--check-descend`),
so that a machine without `~/projects/repos/` could not fire a false licensing STOP and kill
Increments 2–4. It then introduced the G0b `--verify-clones` gate as C25/C28's fix, hard-failing
at exit 1 on **exactly that same condition**, and placed it unconditionally in §9's gate table one
row above D1. The two fixes contradicted each other, and the contradiction was wider than D1:
AC-1.4, AC-1.5, AC-1.6, AC-1.7, AC-1.9, AC-1.13's suite and Tasks 3–8 all read `recipes.yml` from
an out-of-repo clone whose default path revision 2 never stated (§3.1 now does) and whose absence
had no defined behaviour anywhere.

**The resolution is to stop treating 5 as D1's private code.** Exit 5 means *"the measurement
could not be taken"* for every command in the package, and it is never a descend signal, never a
pass, and never a failure of the thing being measured. That is the same measurement-validity axis
C6 separated from the license axis, generalized to the whole surface.

**Live state, 2026-08-27:** `~/projects/repos/` contains `plr-cookbook` and `pylabrobot` only —
**19 of the 21 registry clones are absent**, and `pylabrobot` is explicitly not a registry row.
The absent-clone path is the common case on this machine, not an edge case, and every command
below has been assigned a behaviour rather than left to discover one.

**How to read the `command` column (rev 5, R4-B2):** `licenses --report` abbreviates
`uv run --package training python -m ingest.licenses --report`. The left-hand token is a **module**
under `ingest`, never a subcommand of a dispatcher — `python -m ingest licenses --report` is not a
supported form and `python -m ingest` does not dispatch (§7.1). Every row's "exit" is the int
returned by that module's handler, which its `__main__` block passes to `SystemExit`, and which a
test asserts in-process (§5.5's injection note).

*Rev 7 (C3): the six emitter rows now carry `--out <dir>` literally, as §7.1's template,
§5.6(d)'s file-by-file table and §4.5 already did.* Until this revision they were the only place in
the document that showed these commands invoked **without** it, and the flag's enforcement side was
unstated — which stopped mattering the moment revision 6 drew the exit-64 boundary, because
"required by the parser" and "validated by the handler" now produce different exit codes (64 vs 1)
for the same mistake. `--out` is **required with each of the six emitter flags and with no other
flag** — enumerated, not globbed, because `eval_split`'s is spelled bare `--emit` (§7.1's tuple
table, rev 8, C3) — it
is enforced inside `parse_args`, and the table has a row for the omission. This matters here
specifically because AC-1.16 and Task 8's `test_ingest_offline.py` are parametrized over this table
**row-for-row**: a row that does not spell the command exactly is a test that cannot be written
from it.

***Rev 8 (C2): the `eval_split --check-leak` row gains the path its flag requires*** (`--check-leak
PATH` — §4.5 settles the shape: the flag's own argument, not a bare positional, not defaulted) — it
was the last row in the table whose command was not literally invocable, the identical defect class
C3 had just fixed for `--out`. Its expected code is now a **single** value (**0**, the committed
sidecar,
which is clean) rather than "0 or 6": every other row of this table states one code, and a row that
states two cannot be parametrized. The **6** case is real and is now tested — by Task 4's exit-6
assertion against a leaking `tmp_path` fixture (§4.5), which is where a fixture-driven case belongs.
§9's G5 row keeps both codes because it is a *gate* table describing a gate's possible verdicts;
this is a *behaviour* table describing one invocation's answer, and the difference is the whole
reason both tables exist.

***Rev 8 (C4): the parametrization is 19 cases over 15 rows, and it is worth writing the number
down.*** "Row-for-row" was literally true of this table until revision 7 added the exit-64 row,
which is a **condition** over six commands rather than one command — so the mapping is no longer
1-to-1 and a reader checking the claim finds it false. The honest statement: **thirteen command
rows contribute one case each; the exit-64 row expands to six (one per emitter command, now
enumerated in the row itself); the `pytest -k ingest` row is not a case at all** — it is AC-1.16's
suite-level assertion, made once. **13 + 6 = 19 parametrized cases.** State the number in the test
(a `len(CASES) == 19` assertion costs one line) so that a future row added to this table without a
corresponding case fails loudly, which is the same discipline the README exit-code test applies to
§9's vocabulary.

*Rev 6 (R5-B1): "which its `__main__` block passes to `SystemExit`" was, until this revision, the
only unobserved step in that sentence.* Every row below is tested by calling the handler in
process; nothing tested that the handler is reachable from the command line at all. Task 8's
`test_ingest_entrypoints.py` now closes it by executing each module **as** `__main__` via
`runpy.run_module`, so a module whose guard is missing fails loudly instead of exiting 0 (§7.1).
*Rev 6 (R5-W2): this table is about **decisions**, and it is complete for them.* A malformed
command line — a missing required flag, a typo — is not a row here: it returns **64**
(`cli.EXIT_USAGE`), which is deliberately outside §9's 0–7 range precisely so that it cannot be
mistaken for one of these answers. Before revision 6 it returned `argparse`'s default **2**, which
collided with "unadjudicated blocking finding" and would have made a typo look like contested
canonical tables.

| command | clones present | cookbook clone absent |
|---|---|---|
| `licenses --report` | 0 | **0** — an absent clone is a `NOT_CLONED` verdict, which is *data*. The report is the artifact that records the absence. |
| `licenses --check-descend` | 0 or 3 | **5** (C6, unchanged) |
| `licenses --verify-clones` | 0 | **5** if every failure is an absent clone; **1** if any present clone is at the wrong SHA; `--require-all` forces 1 (AC-1.15) |
| `recipes --emit-histogram --out <dir>` | 0 | **5**, printing `default_recipes_path()` and the `git clone` line |
| `recipes --emit-receiver-alias-keys --out <dir>` | 0, or **1** if no committed `data/receiver_aliases.json` exists (R4-W1: the emitter has no bootstrap mode) | **5**, same message (§5.6d's merge proposal needs the live receiver set). **The clone check runs first (rev 6, R5-S3)**: with *both* the clone and the committed file absent — the live state during Task 3 on a checkout with no `~/projects/repos/` — this exits **5**, not 1 |
| `audit --report` | 0 | **5** |
| `audit --gate` | 0, 2, or **1** if `data/blocking_census.json` is absent/unreadable/invalid (R4-W10) | **5** — never 0, never 2. **An audit that could not be run must not pass its gate**, and it must not report a blocking failure it did not measure either. The clone check is step 1, *before* the census load, so a checkout missing both reports 5 and not 1. |
| `audit --emit-census --out <dir>` | 0 | **5** — the census is a count over the live cookbook (R3-B2) |
| `audit --emit-fingerprint --out <dir>` | 0 | **0** — reads only the three canonical tables (§5.7's `_projection()`) and the five committed artifacts; the cookbook is not an input (R3-W4) |
| `gap --gate` | 0, 4, 7 or 1 | **5** — T3 reads `recipes.yml`, so no decision is available |
| `eval_split --check-leak training/assemble/out/corpus_p25_sidecar.jsonl` | **0** | **0, unaffected** — it reads only `eval_split.json` and the sidecar, both committed in-repo. It does **not** read `recipes.yml`. The sidecar is `--check-leak`'s **own required argument** (`--check-leak PATH`), not a bare positional and not defaulted (§4.5), so this row spells it as every other row spells its flags. Both columns describe the **committed** sidecar, which is clean today; a *leaking* sidecar returns **6**, and that is Task 4's exit-6 test, not a row of this table (rev 8, C2) |
| `eval_split --emit --out <dir>` | 0 | **5** |
| `eval_split --emit-lineage-contract --out <dir>` | 0 | **0** — reads only the committed sidecar, exactly as `--check-leak` does (R3-W4) |
| **the six emitter commands with `--out` omitted** (rev 7, C3) — enumerated literally in rev 8 (C4) so the row's cardinality is read, not inferred: `recipes --emit-histogram` · `recipes --emit-receiver-alias-keys` · `audit --emit-census` · `audit --emit-fingerprint` · `eval_split --emit` · `eval_split --emit-lineage-contract` | **64** (six cases) | **64** (six cases) — identical in both columns, and that is the point: `--out` is enforced by `cli.IngestArgumentParser` inside `parse_args`, which `cli.run` calls **before** the handler, while every clone check lives in a handler. So the missing flag always wins and the answer does not depend on the clone (§7.1). Not a decision — 64 is outside §9's 0–7 range. **This is the one row of this table that is not 1-to-1 with a test case**; see the case count below |
| `pytest -k ingest` | all pass | **all pass**: clone-dependent tests `skip` with a reason naming the missing path; everything else runs (AC-1.16) |

*Rev 4 (R3-W4): revision 3's table omitted `audit --emit-fingerprint` and
`eval_split --emit-lineage-contract` while AC-1.16 asserts against "every command in §7.5's table"
and Task 8's `test_ingest_offline.py` asserts "every subcommand exits per §7.5's table" — so two
real subcommands had no expected exit and the test could not be written. §7.1's blanket rule
("every subcommand maps `CookbookUnavailable` to exit 5") **implies** 0 for both, since neither
raises it; but the table is the artifact the test is written against, so implication is not enough.
`audit --emit-census` (R3-B2) is added here for the same reason, and it **does** exit 5 — it counts
findings over the live cookbook.*

*`recipes --count` is **deleted**, not defined. Revision 3 listed it in this table and nowhere
else; Task 3 delivers only the emitters. The row now names the two `recipes` subcommands exactly,
which is what makes Task 3's "each `recipes` subcommand exits 5" a checkable obligation rather than
an open-ended one.*

**The second two-condition command, and its order (rev 6, R5-S3).** R4-W10 fixed the precedence for
`audit --gate` (clone absent → **5** *before* census absent → 1) and stated the reason. Revision 5
then created a second command with two simultaneously-satisfiable failure conditions and never said
which fires: `recipes --emit-receiver-alias-keys` exits **5** with the clone absent and **1** with
no committed `receiver_aliases.json` (R4-W1), and **both are true during Task 3 on a CI checkout** —
the file has not been transcribed yet and the clones are not there. The order is the same as
`audit --gate`'s, for the same reason §5.5 gives: **clone check first.** Exit 1 here means "go
author the 31-row table by hand from §3.3", which is a substantial human task; telling an operator
to perform it when the command could not have run anyway is the same error as telling a CI machine
to regenerate a census file it already has. Provision the clone, re-run, and *then* be told the
file is missing — by which point the message is actionable.

**The third two-condition case, and unlike the first two it is not a judgment call (rev 7, C3).**
A missing `--out` and a missing clone can hold simultaneously on any of the four clone-dependent
emitters — `recipes --emit-histogram`, `recipes --emit-receiver-alias-keys`,
`audit --emit-census`, `eval_split --emit` — and on a fresh checkout both *are* true. The answer is
**64**, and it is settled by structure rather than by preference: `cli.run` calls `parse_args`
(which carries the `--out` check) before it calls the handler (which carries the clone check), so
there is no ordering to choose. It is written down anyway for one reason — so that a fixer who
finds it surprising does not "fix" it by moving the `--out` check into the handler, which would
turn a usage error into a measurement error and put a 1 where §9 says 64 belongs.

**Why `audit --gate` exits 5 rather than 2.** Exit 2 means "a blocking finding is unadjudicated",
which is a claim about the cookbook. Without the cookbook there is no such claim to make, and
returning 2 would be indistinguishable from a real drift failure — turning "provision your
clones" into "the canonical tables are contested". Exit 5 says the true thing.

**Why G0b's stricter behaviour is preserved for Task 0 and relaxed for CI.** Task 0's deliverable
*is* the provisioning, so an absent clone there is a task failure and `--require-all` makes it
exit 1. A CI checkout without `~/projects/repos/` has not failed at anything, so the default
exit 5 applies. The per-row exactness C25/C28 demanded is untouched: no command counts
directories, every miss is printed with its `source_id`, and a present-but-wrong-SHA clone is a
hard exit 1 in **both** modes, because that is a measurement that *was* taken and disagreed.

---

## 8. Fixer Tasks

Tasks are sequenced; each is scoped to one session and depends only on committed outputs of
earlier tasks.

### Task 0: Clone the 20 repos and pin their SHAs

Clone each of the 20 registry repos into `~/projects/repos/<repo>` (**outside** the praxis repo,
F7), record the resolved 40-hex SHA of each clone's HEAD, and write those SHAs into
`training/ingest/data/sources.json`. Cloning is a shell action performed *by the fixer*, not by
any module in `training/ingest/` (F3 forbids `subprocess` inside the package). Prefer full clones
over `--depth 1` so a future increment can pin a historical SHA; if disk pressure forces shallow,
record `"notes": "shallow clone"` on the row. `plr-cookbook` is already cloned — read its SHA from
`.git`, do not re-clone. `~/projects/repos/pylabrobot` already exists and is **not** a registry
row.

**Files**: `~/projects/repos/*` (create), `training/ingest/data/sources.json` (create)
**Gate (C25/C28, R2-B4c)**: `uv run --package training python -m ingest.licenses --verify-clones
--require-all` exits 0 — per-row, exact: each of the **21** `clone_path`s has a `.git` whose
resolved HEAD equals the row's `pinned_sha`. Revision 1's `ls ~/projects/repos | wc -l >= 21`
passed at 20 of 21 cloned, because the pre-existing non-row `pylabrobot` directory made up the
count. **`--require-all` is required here and only here**: provisioning is this task's deliverable,
so an absent clone is a task failure (exit 1), whereas §9's G0b runs without the flag because a
CI checkout without `~/projects/repos/` has failed at nothing (exit 5, §7.5). Also record
`shallow: true` in each row's `notes` where `.git/shallow` exists.
**Scope estimate**: ~0 LOC + 20 clones

### Task 1: `sources.py` + the committed registry + importability + the CLI plumbing

Package scaffold (`__init__.py`, `versions.py`, `io.py`, `data/`, `out/`), the `SourceRow`
dataclass, the three enums, `load_registry()` with all ten invariants I1-I10 raising
`RegistryError`, and the 21-row `sources.json` populated per §2.3/§2.4 (cookbook `ADMITTED`; 18
`PENDING_RECON`; 2 `REJECTED_PERMANENT` with `tier_ceiling: 0`; every row's `tier_ceiling` stated;
`cheshire-drivers` explicitly 2). Add `"ingest*"` to `training/pyproject.toml` **and run
`uv sync --reinstall-package training`**.

**Plus the CLI plumbing, moved here from Task 6 (rev 5, R4-B2).** `cli.py` delivers, in full:

- the `EXIT_*` constants — §9's eight decision codes **plus `EXIT_USAGE = 64`** (rev 6, R5-W2);
- **the three exception ROOTS: `IngestError`, `CookbookUnavailable(IngestError)` and
  `UsageError(IngestError)`** (rev 7, C1). *These are `cli.py` deliverables, not `recipes.py`'s or
  `audit.py`'s.* Revision 6 designed the hierarchy in §7.1 and then listed only
  `EXIT_*`/`IngestArgumentParser`/`UsageError`/`run()` here — so this task, read on its own,
  produced a `cli.py` with no `IngestError` for `run()` to catch and no `CookbookUnavailable` for
  `recipes.py` to re-export, and the fixer's only way out was to declare them in the command
  modules, which is the circular import R5-W2 removed. **§7.1's hierarchy table is the checklist
  for this bullet**;
- `IngestArgumentParser` — overriding `error()` (§7.1: **not** `exit_on_error=False`) and taking
  `out_required_for=` so `--out` is enforced inside `parse_args` for **each of the six emitter
  flags** — an enumerated set, not a `--emit-*` glob, because `eval_split`'s flag is bare `--emit`;
  §7.1's tuple table gives all three non-empty tuples (rev 7, C3; rev 8, C3);
- `run(handler, parser, argv)` — the single implementation of §7.5's `CookbookUnavailable` → 5
  mapping, the `UsageError` → 64 mapping and the `IngestError` → 1 mapping.

Plus `__main__.py`, the signpost that makes `python -m ingest --help` exit 0. **Neither file is a
subcommand dispatcher** (§7.1). Revision 4 created both in Task 6, which made AC-1.0 unsatisfiable
at the task that gates it and left Tasks 2–5's gates invoking machinery that did not exist yet.

`sources.py`'s `RegistryError` is delivered here too, and it subclasses **`cli.IngestError`**, not
`ValueError` — the first of §7.1's five per-module rows, and the reason `cli.py` must exist by the
end of this task rather than at Task 6.

**Files**: `training/ingest/{__init__,versions,io,sources,cli,__main__}.py`,
`training/ingest/data/sources.json`,
`training/pyproject.toml` (modify), `training/tests/test_ingest_registry.py` (create)
*(one `data/` file — `sources.json`; §5.6(d)'s eleven-file reconciliation is per-task and
unchanged, since `cli.py`/`__main__.py` are code, not data.)*
**Gate**: AC-1.0's two commands exit 0 **from the repo root** — including
`python -m ingest --help`, which now has a `__main__.py` to satisfy it; **the three
no-dispatcher probes below**; then
`uv run --package training pytest training/tests/test_ingest_registry.py` — 21 rows, the 1/18/2
`admission_state` census, every invariant has a negative test asserting `RegistryError`, and
AC-1.12's live-deadline branch is exercised with both a future and a past `today`; **plus
`issubclass(sources.RegistryError, cli.IngestError)` and a `cli.run` round-trip mapping a raised
`RegistryError` to exit 1** (rev 7, C1 — the same assertion Task 8 makes for all five per-module
classes, made here for the first one so the hierarchy is observed at the task that introduces it
rather than five tasks later)

**The no-dispatcher probes, and why one was not enough (rev 6, R5-W3).** Revision 5 gated a single
probe — *"`python -m ingest licenses` (the dispatcher spelling) exits **1**, so the two spellings
can never both appear to work"* — and the conclusion does not follow from the input. That probe
passes a bare subcommand token with **no action flag**, so it is a *malformed* dispatcher call, and
a hybrid implementation (a real dispatcher in `__main__.py` **plus** the five module guards) that
maps its own usage errors to 1 returns 1 for it and passes — while `python -m ingest licenses
--report` works too, which is exactly the two-spellings state R4-B2 exists to forbid. R5-W2 makes
that hybrid *more* likely, not less, by giving a fixer a reason to think about usage-error codes.
Three probes, in increasing strength:

1. **Malformed (kept):** `python -m ingest licenses` exits **1**, with a message naming the
   `python -m ingest.licenses` form.
2. **Well-formed (new):** `python -m ingest licenses --report` — the invocation a working
   dispatcher would *service* — exits **1** and **writes nothing**. The test snapshots the
   `{name: sha256}` map of `training/ingest/out/` (empty at this task; two files from Task 2
   onward), runs the command, and asserts the map is unchanged. A dispatcher cannot pass this:
   `licenses --report` writes `license_report.json` and `SOURCES.md` (AC-1.2). Note the expected
   code is **1**, not R5-W2's **64** — `__main__.py` is hand-written and does not use
   `cli.IngestArgumentParser` (§7.1), precisely so that this signal stays unambiguous.
3. **Structural (new, and the one that actually closes it):** §7.3(a)'s third ban — `__main__.py`
   contains **zero** imports of the five command modules — asserted in Task 8's purity suite. No
   finite set of invocations can prove "no dispatcher exists for *any* input"; "this file cannot
   reach a handler" can, and does, in one AST pass.

**Scope estimate**: ~280 LOC + ~280 lines of data

### Task 2: `licenses.py`, the pinned rule set, and the three-way descend rule

The two enums plus `UNRESOLVABLE`/`VERDICT_TIER`, `LicenseFinding`, the substring rule table in
`data/license_rules.json` with its version + hash pin in `versions.py`, root **plus
`license_scan_dirs`** candidate scanning, subprocess-free `.git` SHA resolution (HEAD → refs →
packed-refs), `effective_tier = min(license_tier, tier_ceiling)`, `write_report`,
`write_sources_manifest`, `check_descend` (0/3/5) and `verify_clones`.

**Files**: `training/ingest/licenses.py`, `training/ingest/data/license_rules.json`,
`training/tests/test_ingest_licenses.py` (create)
**Gate**: `--report` exits 0 and writes both artifacts; `--check-descend` exits 0, 3 or 5 per
AC-1.3 with a synthetic fixture driving **each** of the three outcomes (in particular: a fixture
with zero clones present must exit **5**, not 3); the suite includes synthetic license fixtures
for MIT / Apache-2.0 / AGPL / no-file / two-files-in-different-scan-dirs / SHA-mismatch; a test
asserts editing `license_rules.json` without bumping `LICENSE_RULES_SHA256` raises; a test asserts
the cookbook row resolves to `NONE` ⇒ tier 0 **and** that a planted `cookbook/LICENSE` fixture is
found (C21/C24)
**Scope estimate**: ~340 LOC

### Task 3: `recipes.py` — the exact reader + the falsifiable classifier

The line-oriented reader of §3.1 with its line-accounting reconciliation and the `path` regex
validator, `default_recipes_path()`, **`RecipesError(cli.IngestError)` — the module's one declared
error class** — `Recipe` (with `line_no`), `ApiToken`
+ the closed `ReceiverType` enum, `split_apis()` with its empty-token guard, the five
**independent positive** `TokenKind` predicates with the exactly-one assertion, the **exact,
hand-authored** receiver alias map (§3.3 rule 5 — the *values* are a human's judgment; the emitter
proposes keys only), exactly two subcommands — **`--emit-histogram`** and
**`--emit-receiver-alias-keys`** (the merge-proposal contract of §5.6d) — and `method_shaped()`.
*Rev 4 (R3-W4): `recipes --count` is not part of this task and has been removed from §7.5; these
two are the complete `recipes` subcommand set, which is what makes the clone-absent gate item
below finite.* Both take a **required `--out <dir>`**, declared to the parser via
`out_required_for=("emit_histogram", "emit_receiver_alias_keys")` (rev 7, C3; §7.1) — omitting it
exits **64**, before any clone check.

***`CookbookUnavailable` is NOT a deliverable of this task (rev 7, C1).*** It is declared in
`cli.py` at Task 1 (§7.1's hierarchy table). What `recipes.py` delivers is the **re-export** —
literally `from .cli import CookbookUnavailable` plus the `__all__` entry — so that
`from ingest.recipes import CookbookUnavailable` keeps working everywhere this spec already spells
it that way. Revisions 2–6 listed the class itself here while §7.1 said it lives in `cli.py`; a
fixer working module-by-module would have declared `class CookbookUnavailable(RecipesError)` from
this line and rebuilt R5-W2's circular import (`cli.run` must catch it → `cli` imports `recipes` →
`recipes` already imports `cli` for `EXIT_*`/`run`). `load_recipes()` still *raises* it; raising an
imported class is the normal case, not an exception to it.

**Files**: `training/ingest/recipes.py`, `training/ingest/data/{receiver_aliases,token_histogram}.json`,
`training/tests/test_ingest_recipes.py` (create)
**Gate**: `load_recipes()` over the default path returns `token_histogram.json`'s `n_recipes`
rows — **91** today, and the count lives in that file, not in `recipes.py` (rev 5, R4-B1);
**a small synthetic fixture whose `path` would be truncated by a `#`-stripping reader is asserted
to parse intact**, and a fixture with a genuinely malformed path is asserted to raise
`RecipesError`; the line-accounting identity holds on the real file; the histogram — per-kind
counts **and** `n_recipes` — matches.

*Rev 5 (R4-B1): the truncation fixture is **a handful of records, not 91**, and that is now legal.
Revision 4's `load_recipes()` raised `RecipesError` on any input that was not exactly 91 records,
so this fixture — the direct regression test for C5, the highest-consequence parsing defect in the
spec — could not be written at all. The reader performs no count check for any path (§3.1); the
fixture is two or three records exercising the `#`-in-`path` case and nothing else.*

Plus these, restated in rev 3:

- **the exactly-one assertion, both branches (R2-B3)** — (i) `classify_api_token("")` raises
  naming **zero** matched kinds, which is the branch a trailing comma in `apis` reaches and which
  revision 2's complement-`OTHER` silently absorbed; (ii) with `_PREDICATES` **monkeypatched** so
  `IDENT` and `CLASSISH` both return `True`, `classify_api_token("setup")` raises naming two
  kinds. Revision 2's gate asked for "a synthetic ambiguous token", which cannot exist for a
  provably disjoint predicate set — the monkeypatch is how you test that an assertion about the
  *implementation* is live;
- **`split_apis("a,,b", …)` raises `RecipesError` naming the recipe**, not the token;
- pinned classifications for the eight §3.2 samples: `Mix→CLASSISH`, `mix→IDENT`,
  `STARBackend.aspirate→DOTTED` with `receiver="STARBackend"`, `receiver_type=LIQUID_HANDLER`,
  `member="aspirate"`; `"naming convention"→PROSE`; `cor_96_wellplate_360uL_Fb→OTHER` via
  `_MIXED_SNAKE`;
- **corrected (W11):** `ThermocyclerChatterboxBackend→CLASSISH` with **`receiver=None`,
  `receiver_type=NONE`, `method_shaped()=False`**. Revision 2 asserted `receiver_type` *other*
  here, which contradicts its own §3.2 type design — CLASSISH tokens have no receiver at all.
  C9's actual concern gets its own assertion: `Liddable.has_lid→DOTTED`,
  `receiver_type=OTHER`, `method_shaped()=True`, and **no `SURFACE_ADJACENT` finding**, even
  though `has_lid` is in neither canonical table;
- **the three method-shaped-but-not-methods (W10):** `backends/chatterbox.py→DOTTED` with
  `receiver="backends/chatterbox"`, `member="py"`; `manifest.json`/`config.json→DOTTED` with
  `member="json"` — all three `method_shaped()=True`, all three `receiver_type=OTHER`, none
  blocking;
- **two-way receiver-map equality over the KEY SET (W10):** `set(receiver_aliases["exact"]) ==
  {t.receiver for t in tokens if t.kind is DOTTED}`, i.e. **zero unmapped receivers AND zero
  unused entries**, over the 31 receivers §3.3 enumerates. Revision 2's one-directional gate was
  satisfied by a table containing ten receivers that appear nowhere in the file;
- **the three `liquid_handler` VALUES pinned by name (new in rev 4 — R3-B3):**
  `exact["lh"] == exact["LiquidHandler"] == exact["STARBackend"] == "liquid_handler"`, **and** no
  other key maps to `liquid_handler` or `plate_reader`. This is the assertion the key-set equality
  above cannot make. Without it a table with all 31 keys correct and all 31 values `other` passes
  every gate in revision 3 while silently driving `surface_adjacent` from 5 to 0 — and both
  blocking receiver-dependent kinds require exactly those two values (§3.3 rules 4–5). Three lines
  of test against a hand-authored table, guarding the audit's highest-signal output;
- **the emitter is a merge proposal, not a generator (R3-B3):** a test runs
  `--emit-receiver-alias-keys` against a synthetic recipe set containing one **new** DOTTED
  receiver and asserts the emitted file (i) preserves all three `liquid_handler` values verbatim,
  (ii) adds the new key with value `"other"`, and (iii) names it in `needs_review`. A second test
  asserts a **removed** receiver lands in `unused` rather than being dropped. `--emit-*` writing
  into `data/` is impossible by §5.6(a) regardless;
- **the emitter has no bootstrap mode, and a test pins that (rev 5, R4-W1):** with the clone
  **present** and no committed `receiver_aliases.json`, `--emit-receiver-alias-keys` raises
  `RecipesError` naming the
  missing path and exits **1**. It must **not** emit a 31-key all-`other` map with every key in
  `needs_review` — that file would pass rule 2's key-set equality while carrying zero information,
  which is R3-B3's exact failure mode wearing a bootstrap label. The file's first version is this
  task's hand transcription of §3.3's table, with the three `liquid_handler` values assigned by a
  human; the emitter is a second-run-onward tool;
- **and a third fixture pins the precedence when both conditions hold (rev 6, R5-S3):** clone
  absent **and** no committed `receiver_aliases.json` — which is this task's own starting state on
  a checkout with no `~/projects/repos/` — exits **5**, not 1. The clone check runs first, for
  §5.5's reason: exit 1 here is an instruction to hand-author §3.3's 31-row table, and a command
  that never reached the cookbook has not earned the right to issue it. Same ordering as
  `audit --gate`'s clone → census;
- **clone-absent behaviour (AC-1.16):** with `default_recipes_path()` monkeypatched to a
  nonexistent path, `load_recipes()` raises `CookbookUnavailable` and **both** `recipes`
  subcommands (`--emit-histogram --out <tmp>`, `--emit-receiver-alias-keys --out <tmp>`) exit 5,
  per §7.5 — including `--emit-receiver-alias-keys` with no committed file present, per the bullet
  above;
- **the re-export is asserted by identity, not by name (rev 7, C1):**
  `recipes.CookbookUnavailable is cli.CookbookUnavailable` **and**
  `issubclass(recipes.RecipesError, cli.IngestError)` **and**
  `not issubclass(recipes.CookbookUnavailable, recipes.RecipesError)`. The first is the one that
  matters: a fixer who declares the class here instead of importing it still satisfies every
  `from ingest.recipes import CookbookUnavailable` in the suite, and only object identity
  distinguishes the re-export from the redeclaration that reopens the circular import. The third
  pins the base that changed between revisions, so the old spelling cannot come back quietly;
- **`--out` is enforced by the parser (rev 7, C3):** `--emit-histogram` with no `--out` exits
  **64** and writes nothing — asserted with the clone both present and absent, since the answer is
  64 either way.

**Scope estimate**: ~340 LOC

### Task 4: `eval_split.py` + the committed holdout index + the leak gate

The §4.2 rule (sorting by `(path, line_no)`), `eval_split.json` generated once and committed
(paths only, with `held_out_ever`), `is_held_out`, `check_corpus_for_leak`/`assert_no_leak`,
`load_sidecar_rows` (rev 8, C7 — its I/O failures raise `cli.IngestError` → 1, **never**
`EvalSplitLeak`), `SIDECAR_RELPATH` / `default_sidecar_path()` (rev 8, C2 — used by
`--emit-lineage-contract` only), the
`--check-leak` / `--emit` / `--emit-lineage-contract` subcommands,
`data/lineage_contract.json`, and the **seven** assertions 0–6 of §4.4.

***The `--check-leak` handler is a deliverable in its own right, and §4.5 gives it as normative
code (rev 8, C1/C7).*** It is `try: assert_no_leak(rows) / except EvalSplitLeak: print(exc,
file=sys.stderr); return 6 / return 0`. Writing it as `assert_no_leak(rows); return 0` — the
shape the function's name invites — lets `EvalSplitLeak` escape as an uncaught traceback (it is
deliberately **not** a `cli.IngestError`, §7.1's table), which the interpreter reports as exit
**1**, so G5 would report a measurement error on a real leak. **The sidecar is `--check-leak`'s own
required argument** (`g.add_argument("--check-leak", type=Path, dest="sidecar",
metavar="SIDECAR")`), not a bare positional — a bare one would be demanded by `--emit` and
`--emit-lineage-contract` too, whose §7.5 rows carry none — and it has no default; `SIDECAR_RELPATH`
/ `default_sidecar_path()` exist for `--emit-lineage-contract` alone (§4.5).

***This module's `out_required_for` tuple, stated explicitly because its flag names break the
`--emit-*` pattern (rev 8, C3).*** `eval_split.py`'s parser is constructed with
`out_required_for=("emit", "emit_lineage_contract")`. Note the **bare `"emit"`**: `eval_split`'s
emitter flag is spelled `--emit`, not `--emit-<something>`, so a fixer applying §7.1's rule by
literal glob against `--emit-*` writes `("emit_lineage_contract",)` and `eval_split --emit` with no
`--out` then reaches the handler instead of exiting **64**, contradicting §7.5's row for it. Of the
six emitter flags in the package this is the only one whose name does not fit the pattern, which is
exactly why this task states its tuple rather than leaving it to be derived (Task 3 states its own
for the same reason).

**Files**: `training/ingest/eval_split.py`,
`training/ingest/data/{eval_split,lineage_contract}.json`,
`training/tests/test_ingest_eval_split.py` (create)
**Gate**: the **seven** §4.4 assertions pass — including **assertion 6** (rev 6, R5-W1:
`n_recipes` equals `token_histogram.json`'s, `n_held_out` equals `len(held_out_paths)`), with two
negative fixtures that perturb each counter by one and assert the suite goes red, since an
equality nobody has seen fail is an equality nobody has seen run; **a test mutating a temp copy of `recipes.yml` at an
unchanged HEAD asserts the suite fails on assertion 1 (bytes), and a test moving the resolved HEAD
asserts it fails on assertion 0 (SHA) *first*** — proving the tripwire is live **and correctly
ordered**, which is R2-B4d's fix; a monotonicity test constructs a v2 split that drops a
previously-held path and asserts it is **rejected**; the **four** `check_corpus_for_leak` fixtures
(clean / train-row-on-held-path / cookbook-lineage-without-recipe_path / **undeclared lineage key
`qmd_anchor`**, W3) behave as specified;
`python -m ingest.eval_split --check-leak training/assemble/out/corpus_p25_sidecar.jsonl` exits 0
**and its lineage-contract assertion evaluates over all 188 rows** (AC-1.17 — it must be shown to
run, not merely to pass); and with the cookbook clone absent, **`--check-leak` and
`--emit-lineage-contract` are both unaffected (exit 0 and 0 respectively) while `--emit` exits
5**, per §7.5's rows — all three now stated there, where revision 3 left `--emit-lineage-contract`
undefined (R3-W4).

**Plus, new in rev 8 (C1) — the exit-6 assertion, which is the one assertion in this spec that
observes the `EvalSplitLeak` → 6 contract at all:**

- the **type-2 fixture** (a `train`-split row whose `lineage.recipe_path` is in `held_out_ever` —
  reuse the one already required above, written out to a `tmp_path` JSONL) is passed through the
  CLI entry point: `eval_split._main(["--check-leak", str(fixture)]) == 6`, **exactly 6**, not
  merely non-zero. Asserting "non-zero" would pass under the defect this test exists to catch,
  because the defect's symptom *is* a non-zero code (1, from an uncaught traceback);
- a **clean** `tmp_path` fixture through the same call returns **0**, so the test distinguishes
  "the handler returns 6 on a leak" from "the handler returns 6 on everything";
- both drive `_main` (in-process, no subprocess — F3 and §7.3 are untouched; `runpy` would work
  equally and Task 8 uses it, but `_main` is the cheaper call here and the fixtures are local).
  **`_main`'s argument is `argv` *without* the program name** — §7.1's template hands it straight
  to `parse_args` — so the list is `["--check-leak", str(fixture)]`, not
  `["ingest.eval_split", "--check-leak", …]`; Task 8's `runpy` form sets `sys.argv` and therefore
  *does* carry the prog token, and the two must not be cargo-culted into each other.
  **Why the CLI level and not `assert_no_leak`:** the four fixtures above already cover the
  library, and the untested link was never the detection logic — it was the handler's `try/except`,
  which only an invocation that produces an *exit code* can see (§4.5).

**Scope estimate**: ~230 LOC + 2 data files

### Task 5: `audit.py` — findings, the two hashes, and the fingerprints

All ten `FindingKind`s with **§5.2's subject table implemented literally** (R2-B2) — **including
`param_candidate`'s (verb, token) cross product for multi-verb recipes** (rev 5, R4-W7; a unit
test pins recipes.yml:432's four subjects) — the fully declared `Evidence` + `MatchMode` (W4/W5),
**`canonical_json` and `_sha16` as the package's single hash serializer** (rev 5, R4-B3 — no Enum
is ever interpolated into a hash input) **plus `_finding_id_payload`, `dotted_subject` and
`param_subject`** (rev 6, R5-W4 — the identity path contains no f-strings at all, so the
interpolation hazard is unrepresentable rather than merely tested against),
`compute_finding_id` (identity) **and** `adjudicable_digest`
(§5.2), `load_adjudications` / `load_blocking_census` / `gate` with §5.5's `Path | None` injection
signatures (rev 5, R4-W5),
`canonical_tables_fingerprint()` / `subject_table_fingerprint(kind, subject)` over §5.7's
three cases **with the explicit dispatch + subject-parse rules and the `AuditError` scope guard**
(R3-W6/R3-W7), `data/experimental_partition.json` with its three loader invariants, the mandatory
four `phantom_verb` + three `no_backend_verb` findings, the observed `blocking_census` plus
**`audit --emit-census`** and `load_blocking_census()` with its `BLOCKING_KINDS` key invariant
(R3-B2), both readings on every finding, and the `audit_report.json` + `audit_findings.jsonl`
writers (through `io.write_artifact`).

**Files**: `training/ingest/audit.py`, `training/ingest/data/experimental_partition.json`,
`training/ingest/data/blocking_census.json` (create — emitted by `--emit-census --out <tmp>`, then
copied in by hand per §5.6d),
`training/tests/test_ingest_audit_phantoms.py`, `training/tests/test_ingest_audit_findings.py`
**Gate**: the four §5.3 table rows asserted verbatim, **including `Mix`'s
`match_mode=classish_casefold` and `mix`'s `match_mode=exact`** (W5); the partition loader
asserted to **raise** when a synthetic 8th `experimental=True` entry is injected (C4);

**the three interpreter-independent hash-identity assertions that replace rev 5's unwritable one
(rev 6, R5-W4)** — revision 5 asked for *"a unit test asserting `compute_finding_id` is unchanged
across a `FindingKind` passed as the member versus its `.value`"*, which cannot be written (a plain
`str` has no `.value`, so it raises `AttributeError`) and would not have tested the 3.11 divergence
if it could (§5.2 works through why **no** behavioural test can — `f"{kind}"` is correct on
3.10/3.12). The three that fire everywhere:
  1. **byte pin on the canonical payload** —
     `canonical_json(_finding_id_payload(FindingKind.PHANTOM_VERB, "mix"))` equals
     `b'{"kind":"phantom_verb","rules_version":"1","subject":"mix"}'` verbatim (keys in
     `sort_keys` order: `kind` < `rules_version` < `subject`). The test calls the **same** payload
     builder the implementation does, so it cannot drift into a second construction; what it pins
     is that the enum reaches the bytes as its value and nothing else does. If `AUDIT_RULES_VERSION`
     is ever bumped this test goes red — correctly, because bumping it re-keys every `finding_id`
     and therefore invalidates every key in `audit_adjudications.json`;
  2. **`compute_finding_id("phantom_verb", "mix")` raises `AuditError`** — a plain `str` `kind` is
     rejected at the boundary, so the widening to `str | FindingKind` that R5-W4 predicts a fixer
     would reach for is a red test rather than a silent second key space (R2-B2);
  3. **a full-run sweep** — over every finding a real `run_audit()` produces, assert
     `b"FindingKind."` and `b"ReceiverType."` appear in **no** `canonical_json` payload and in **no**
     `subject`. *Labelled honestly: this assertion is vacuous on 3.10/3.12 and live on 3.11.* It
     costs three lines and is the only thing in the suite that would catch a future
     `f"{receiver_type}.{member}"` typo in a subject builder, which is the same defect one field
     over from R4-B3's.

Continuing the gate list:
`finding_id` asserted **unchanged** when an unrelated recipe is appended to a temp `recipes.yml`;
`adjudicable_digest` asserted **unchanged** for that same append, and asserted **changed** when a
synthetic `lh.mix` recipe flips `mix` from `KWARG_ONLY` to `CONTESTED` (C3 — this is the test that
proves the fix);

> **Rev 5 (R4-B1): both append fixtures are 92-record files, and revision 4 made them
> unimplementable.** `load_recipes()` raised `RecipesError` on anything but exactly 91 records, so
> the temp file with one appended recipe failed at the reader — including the `lh.mix` case this
> spec calls "the test that proves the fix" for the review's most severe finding. The reader now
> performs no count check for any path (§3.1); these two fixtures need no exemption because there
> is no longer a rule to be exempt from. `finding_id` and `adjudicable_digest` are computed from
> the parsed recipes, so nothing else about the tests changes.

plus, new in rev 3:

- **the observed `blocking_census` equals the committed `data/blocking_census.json`'s `census`
  object** (R3-B2 — the test holds **no literal of its own**; the committed file, whose expected
  content `{"phantom_verb": 4, "surface_adjacent": 5, "receiver_drift": 0,
  "param_misattributed": 0}` §5.4.1 derives, is the single source of truth), **and**
  `load_blocking_census()` **raises `AuditError`** on a fixture whose `census` keys are not exactly
  `{k.value for k in BLOCKING_KINDS}`;
- the five `surface_adjacent` subjects are asserted **by name** (`liquid_handler.` +
  `use_channels` / `use_tips` / `head` / `clear_head_state` / `probe_tip_presence_via_pickup`)
  with their §5.4.1 evidence lines (R2-B1);
- **`subject_table_fingerprint` is subject-distinct for not-in-any-table subjects** — the five
  `surface_adjacent` subjects produce five **different** digests, which is the direct test that
  R2-B2's constant-hash hazard is closed;
- **staleness is tested where it exists, and disappearance where it does not (rev 4, R3-B1).**
  Revision 3's bullet here asked for `NON_SURFACE_VERB_REASONS` monkeypatched to include
  `use_channels`, asserting `liquid_handler.use_channels`' `adjudicable_digest` **changes**. That
  test cannot be made green: adding the member deletes the finding rather than staling it (§5.7).
  It is replaced by two tests:
  1. **the real staleness path, on `phantom_verb`** — with `TOOL_SCHEMA` monkeypatched so `mix`'s
     `receiver_type` is `plate_reader`, `mix`'s `adjudicable_digest` **changes** (its `tool_row`
     moved) while `liquid_handler.use_channels`' does **not**. This is the per-subject property C3
     built the digest for, tested on a kind where it holds.
     **The technique is `setitem` + `dataclasses.replace`, not attribute assignment (rev 5,
     R4-W6):**
     ```python
     monkeypatch.setitem(
         tool_schema.TOOL_SCHEMA, "mix",
         dataclasses.replace(tool_schema.TOOL_SCHEMA["mix"], receiver_type="plate_reader"),
     )
     ```
     `ToolSpec` is `@dataclass(frozen=True)` (`tool_schema.py:35`), so revision 4's
     `TOOL_SCHEMA["mix"].receiver_type = "plate_reader"` raises `FrozenInstanceError` and the test
     could not run. `TOOL_SCHEMA` is a plain `dict`, so `setitem` is visible through
     `from … import TOOL_SCHEMA` as well as through the module — see §5.5's monkeypatch table,
     which also records that `PHASE2_TOOL_NAMES` does **not** follow a `setitem` (irrelevant here,
     because `mix` is `experimental` and absent from it under both the real and patched tables);
  2. **the disappearance path, on `surface_adjacent`** — with `NON_SURFACE_VERB_REASONS`
     monkeypatched to include `use_channels`, assert (i) no `surface_adjacent` finding with subject
     `liquid_handler.use_channels` is produced at all, and (ii) the observed
     `blocking_census["surface_adjacent"]` is **4**, so the AC-1.6 comparison against the committed
     file goes red. Both halves are asserted, because (i) alone would pass for a finding that
     merely changed shape;
- **`_verb_slice` is asserted INVARIANT for a `surface_adjacent` subject under an unrelated table
  edit** (the same `setitem` + `dataclasses.replace` patch of `TOOL_SCHEMA["mix"]` as above —
  R4-W6; assert `subject_table_fingerprint(SURFACE_ADJACENT, "liquid_handler.use_tips")` is
  unchanged). This
  pins R3-B1's finding as a **known, tested property** rather than an accident a later revision
  might silently "fix" by widening the slice — which would re-churn every adjudication on every
  unrelated table edit, the exact cost §5.2 rejected a global fingerprint to avoid;
- **the scope guard is a raise, at the dispatch point (R3-W7)** — a test uses
  `monkeypatch.setattr(audit, "BLOCKING_KINDS", …)` to promote `unclassified_token` into the
  blocking set, then asserts `subject_table_fingerprint` raises **`AuditError`**. The
  `pytest.raises(AuditError)` is itself the discriminator: a bare `assert` would raise
  `AssertionError` and fail the test.
  *Rev 5 (R4-W9): revision 4 asked for "a second test [that] runs the same case under `python -O`
  semantics (`assert` disabled)". **That test cannot be written** — `-O` is fixed at interpreter
  start and cannot be toggled inside a running process; the only mechanism is a subprocess, which
  §7.3 bans in ingest modules and never scoped for tests. It is replaced by **§7.3(a)'s AST ban on
  `ast.Assert` across every module under `training/ingest/`**, which proves the property
  statically, completely, and for every invariant in the package rather than for this one code
  path. The behavioural half stays here; the `-O` half moves to a lint that is strictly stronger.*
- **subject parsing is exercised at its edges (R3-W6)** — `subject_table_fingerprint(SURFACE_ADJACENT,
  "backends/chatterbox.py")` raises `AuditError` (the receiver half is not a `ReceiverType` value),
  and `subject_table_fingerprint(PARAM_CANDIDATE, "flow_rates")` raises (no `:`).

**Scope estimate**: ~500 LOC

### Task 6: The G2 gate — digest-bound adjudications, exit codes, no-auto-patch proof

`data/audit_adjudications.json` seeded with **all nine** blocking adjudications written by a human
(§5.4.1's census: 4 `phantom_verb` + 5 `surface_adjacent`; each carrying its `adjudicated_digest`),
`ingest.audit --gate` with §5.5's three-part completeness rule and exit code 2, and the
three-property test of AC-1.8/§5.6.

**Revision 2 seeded four and asserted `--gate` exits 0 (R2-B1).** That gate was unsatisfiable:
AC-1.7 requires an adjudication for every blocking finding and the cookbook produces nine. The
five new ones are `liquid_handler.` + `use_channels` / `use_tips` / `head` / `clear_head_state` /
`probe_tip_presence_via_pickup`. Four are anticipated as `reading: table_is_wrong`, one
(`head`) as `reading: token_is_not_a_method`, and **all five as `action: file_backlog_item`, not
`edit_table_by_hand`** — editing `NON_SURFACE_VERB_REASONS` inside Increment 1 would change the
canonical-tables fingerprint and demand a regeneration Increment 1 cannot perform (§5.4.1). The
readings themselves are the human's to write; what this task inherits is the subject list.

**Each of the five `action_ref`s must match `ACTION_REF_RE` (rev 4, R3-W8)** — in practice
`backlog:<id>` for a backlog item that the human **actually files**, one per subject. The gate
checks the *grammar*, not the *existence*, and §12.12 records who closes them. Filing five real
items is the whole content of "the gap is owned"; five well-formed strings pointing at nothing
would satisfy every mechanism in this spec and none of PM-3's purpose.

**Files**: `training/ingest/audit.py` (modify),
`training/ingest/data/audit_adjudications.json` (create),
`training/tests/test_ingest_audit_gate.py`, `training/tests/test_ingest_never_patches_tables.py`
*(rev 5, R4-B2: `cli.py` and `__main__.py` are **gone from this task** — they moved to Task 1,
because AC-1.0 gates `python -m ingest --help` at Task 1 and Tasks 2–5's own gates invoke the
CLI. Creating them here left five earlier gates calling machinery that did not exist.)*
**Gate**: every assertion below drives `audit.gate(...)` in-process and compares its **returned
int** (§5.5's injection note) — *and the one thing that arrangement cannot observe, namely whether
`python -m ingest.audit --gate` reaches `gate()` at all, is covered by Task 8's
`test_ingest_entrypoints.py` (rev 6, R5-B1). Neither task's coverage is complete without the
other's, which is why the cross-reference is stated in both.* `--gate` exits 0 with the seeded
**nine-entry** file; exits 2 with
any one adjudication removed (`missing`); exits 2 with a rationale shortened below 40 chars
(`incomplete`); **exits 2 with an `action_ref` of `"x"` on a `file_backlog_item` adjudication
(`incomplete` — R3-W8's grammar), and 0 with `backlog:coxswain-nsvr-use-channels`**; exits 2 with
a correct-but-stale `adjudicated_digest` (`stale_digest`); and **exits 5, not 0 or 2, when the
cookbook clone is absent** (§7.5). Plus, new in rev 5:

- **exit 1, not 0 and not 2, when `data/blocking_census.json` is absent (R4-W10)** — three
  fixtures: the file missing entirely, the file present but not valid JSON, and the file present
  with a `census` whose key set is not `{k.value for k in BLOCKING_KINDS}` (which is
  `load_blocking_census()`'s own loader invariant, R3-B2). All three exit 1 with the path and the
  `audit --emit-census` remedy named. A fourth fixture pins the **ordering**: with the cookbook
  clone absent *and* the census file missing, the gate exits **5**, because the clone check is
  step 1 — otherwise a CI machine without clones would be told to regenerate a file it already
  has;

Plus, corrected in rev 4:

- **the `census_drift` test drives drift DOWN, and its expected exit is 0 (R3-W3).** Revision 3
  asked the gate to "print `census_drift` without failing when a tenth blocking finding is
  injected". That fixture cannot produce the asserted outcome: a newly injected blocking finding
  has **no adjudication**, so §5.5 rule 1 returns reason `missing` and the gate exits **2** —
  the test would fail for a reason unrelated to the drift it was written to observe. The fixture
  is inverted: run against a temp `recipes.yml` with the `lh.use_channels` recipe (line 152)
  **removed**, so the observed census is `surface_adjacent: 4`, all eight surviving blocking
  findings are adjudicated, and the assertion is **exit 0 plus a
  `census_drift kind=surface_adjacent pinned=5 observed=4` line on stdout**.
  Drift-down is the direction AC-1.7's own rationale calls dangerous, and — since a
  `surface_adjacent` adjudication can never go `stale_digest` (§5.7/R3-B1) — it is the **only**
  observation that catches a cookbook-side disappearance at all. Testing the harmless direction
  while the dangerous one went untested is how this stayed invisible for a revision.
  *Rev 5 (R4-B1): this fixture is a **90-record** temp file, and revision 4's own reader invariant
  ("exactly 91 records, raising `RecipesError`") would have raised on it before the gate ran —
  killing revision 4's own fix for R3-W3 at the first line. §3.1's reader now performs no count
  check for any path, so the fixture is legal; the drifted census is observed by counting findings,
  which is where a census belongs. The finding this fixture removes is exactly one blocking finding
  (`lh.use_channels`'s `apis` field names a single token, verified live at recipes.yml:152), so the
  other eight adjudications stay digest-stable and exit 0 is the correct expectation.*

The no-patch test asserts the single-writer AST lint, `ProtectedPathError` for each of the seven
protected roots — **including `training/ingest/data/`, which §5.6(d) confirms no command may
write, for all eleven files in it** — and byte-equality of the four canonical **tables** across a
full pipeline run into `tmp_path`
**Scope estimate**: ~310 LOC + nine hand-written adjudications + five filed backlog items

### Task 7: `gap.py` + the pre-registered thresholds

`GAP_THRESHOLDS` + `T1_INVARIANT` in `versions.py` **committed first, in its own commit, before
`gap.py` can run**, then the sidecar reader, §6.2's corrected shape function (flattened
`_PARAM_INDEX`, `.get()` guard, slice-before-subscript, bool-before-number, numeric collapsing,
**`shape_key(call, stats)` without the unused `verb` parameter** — W15), `INVERSE_CLASS_MAP` with
its injectivity check — **a raised `GapError`, never a bare `assert`** (R3-W7; rev 6, R5-S2 makes
the phrasing consistent with §7.3(a)'s static ban) — the §6.1 cell-attribution rule with `unmatched_cell_keys`, the
`_serialize_unmapped` string-keying (W6), the manifest cross-check, `gap_report.json`, and
`--gate` with exit codes 0/4/**7**/1.

**Files**: `training/ingest/versions.py` (modify), `training/ingest/gap.py`,
`training/tests/test_ingest_gap.py` (create)
**Gate**: `--gate` exits 0, 4, 7 or 1 and writes `gap_report.json`; the test asserts recomputed
per-class counts equal `manifest.counts.by_class` (137/13/17/21); **a direct unit test drives
`value_form` over a `mix` call and a synthetic `(verb, param)` pair absent from
`PARAM_NAMESPACE`, asserting no exception and a `unmapped_params` increment (C1)**; a test asserts
`10.0` and `20` produce the same form (C20); the two T3 matching cases of §6.4 are pinned (C8);
synthetic-corpus fixtures drive the gate to PROCEED, STOP, T1-invariant-violation, **and
CONTESTED — a fixture in which `T2_collapsed` passes while `T2_strict` fails must exit 7, not 4
and not 0 (W2)**; plus, new in rev 3:

- **`json.dumps(report, sort_keys=True)` round-trips** — the regression test for W6's
  `TypeError: keys must be str`, which revision 2's tuple-keyed `unmapped_params` would have
  raised on the first real run, taking down the whole gate;
- **`unmatched_cell_keys == {}`** over the committed 188-row sidecar, as a labelled **regression
  pin** (W9). Revision 2 expected non-empty; a fixer who reproduced that expectation would have
  shipped an inverted `INVERSE_CLASS_MAP` and called the result correct;
- **exit 5 when the cookbook clone is absent** (§7.5), since T3 reads `recipes.yml`;
- **the commit adding `GAP_THRESHOLDS` must precede the commit adding `gap.py` in `git log`**
  (checked by the reviewer, per PM-2)

**Scope estimate**: ~390 LOC

### Task 8: Cross-cutting gates

`test_ingest_determinism.py` (AC-1.10, two distinct temp dirs),
`test_ingest_import_purity.py` (AC-1.11's three properties incl. the runtime
`subprocess`-patched run, **and — new in rev 5, R4-W9 — property (a)'s second ban: zero
`ast.Assert` nodes in any module under `training/ingest/`**, which is what replaces the
unwritable `python -O` test and makes the package's "typed errors, never bare asserts" house rule
mechanical rather than aspirational, **and — new in rev 6, R5-W3 — property (a)'s third ban:
`ingest/__main__.py` imports none of the five command modules**, which is what makes "there is no
dispatcher" structural rather than behavioural, **and — new in rev 7, C1 — property (a)'s fourth
ban: `ingest/cli.py` imports no sibling ingest module**, which is what keeps the one-way import
direction §7.1's exception hierarchy depends on from being re-broken by a plausible edit),
**`test_ingest_entrypoints.py` (new in rev 6, R5-B1 — see below)**,
**`test_ingest_error_hierarchy.py` (new in rev 7, C1 — see below)**,
`test_ingest_no_titles_in_outputs.py` (§3.1),
`test_ingest_downstream_fingerprint.py` (AC-1.14) with the committed
`data/canonical_tables_fingerprint.json`, `data/import_closure_allowlist.json`, the G5
`--check-leak` invocation over the committed sidecar (AC-1.13), and a
`training/ingest/README.md` documenting the gate order, the exit codes, and the descend rules.

**Files**: `training/tests/test_ingest_{determinism,import_purity,entrypoints,error_hierarchy,no_titles_in_outputs,downstream_fingerprint,offline}.py`
(create), `training/ingest/data/{canonical_tables_fingerprint,import_closure_allowlist}.json`
(create), `training/ingest/README.md` (create)
**Gate**: `uv run --package training pytest training/tests/ -k ingest` — all green; plus, new in
rev 3:

- a test that mutates a copy of the canonical projection and asserts the fingerprint test
  **fails**, proving AC-1.14's tripwire is live;
- **and a second that leaves the projection alone but perturbs one byte of
  `training/assemble/out/manifest.json`, asserting AC-1.14 still fails** — this is W1's fix, and
  the test that revision 2's single-hash file could not have passed;
- **`test_ingest_entrypoints.py` — the `__main__` guards are executed, not assumed (new in rev 6,
  R5-B1).** Every other test in this spec drives a handler **in-process** (§5.5's injection note,
  §7.4, §7.5, Task 6's "every assertion drives `audit.gate(...)` in-process"), which is correct and
  which left the `if __name__ == "__main__": raise SystemExit(_main())` block as the one link in
  the chain that **no test crossed**. Omit it from `audit.py` and `python -m ingest.audit --gate`
  imports the module, ignores the flag and exits **0** — R4-B2's failure mode surviving inside
  R4-B2's own fix, with every specified test, AC-1.0 and Task 1's probes all still green (those
  exercise `__main__.py`, which is a different file). Two assertions, both **in-process** — no
  subprocess, so F3 and §7.3 are untouched:
  1. **Parametrized over all five command modules** (`licenses`, `recipes`, `eval_split`, `audit`,
     `gap`): with `monkeypatch.setattr(sys, "argv", [f"ingest.{m}"])` (no flags),
     `pytest.raises(SystemExit)` around `runpy.run_module(f"ingest.{m}", run_name="__main__")`, and
     the raised code equals **`cli.EXIT_USAGE`** (64, R5-W2) — every module's parser has a
     `required=True` group, so no-flags is a usage error for all five. **A missing guard raises
     nothing at all** (`run_module` returns a namespace), so the failure is `DID NOT RAISE` and
     names the module in the parametrize id. This is one line of test per module and it is the
     detector R4-B2's fix never had.
  2. **`audit --gate` end-to-end, which is AC-1.7's contract observed for the first time.** With
     `default_recipes_path()` monkeypatched to a nonexistent path and
     `sys.argv = ["ingest.audit", "--gate"]`, `runpy.run_module("ingest.audit",
     run_name="__main__")` raises `SystemExit(5)` per §7.5. `audit --gate` is the sharpest case
     because it is the only gate whose CLI form writes **no artifact** — Task 2's "writes both
     artifacts" and Task 7's "writes `gap_report.json`" would catch a missing guard incidentally,
     and §9's G2 row has nothing to fall back on. Exit 5 (not 0, not 2) also proves the guard is
     wired to the *handler* and not merely present: a guard that ran the wrong function would
     return 64 or 0.

  *Two mechanics worth writing down, because both are easy to get wrong.* (a) `runpy` is banned
  **inside** `training/ingest/` by §7.3(a) and is perfectly legal here — §7.3's scope paragraph
  limits all four bans to `training/ingest/**.py`, and `training/tests/**` is explicitly
  untouched. (b) `run_module(..., run_name="__main__")` executes the module body a **second** time
  in a fresh namespace, so the copy under test re-imports `ingest.recipes` from `sys.modules` and
  therefore **sees** the monkeypatched `default_recipes_path` — which is why §5.5's monkeypatch
  table specifies patching the module attribute (`monkeypatch.setattr(recipes,
  "default_recipes_path", …)`) rather than rebinding a name the test imported. A second execution
  of these five modules has no side effects: they define constants and functions and read data
  files lazily, and §5.6(a) makes writing into `data/` impossible regardless;
- **`test_ingest_error_hierarchy.py` — §7.1's hierarchy table is checked, not trusted (new in rev
  7, C1).** Round 6's blocking finding was that revision 6 designed the exception hierarchy in
  §7.1 and left **five other sections and two tasks** stating the pre-fix spelling, with §3.1
  declaring `CookbookUnavailable` in `recipes.py` in flat contradiction of §7.1 — and nothing in
  the suite could tell. Four assertions: **three import-time, and one (assertion 4) behavioural**
  (rev 8 — revision 7 said "all import-time, all one line", which was never true of assertion 4,
  and the precision matters because assertion 3's missing behavioural companion is exactly what
  round 7 found):
  1. **Parametrized over the five per-module classes**, with their expected `__module__` values
     written out as the **dotted import paths** they actually are (rev 8, C5 — §7.1's table names
     *files*, `sources.py`/`io.py`, and `X.__module__` is never a filename, so the parametrize list
     is spelled here rather than left as "whatever the table says"; the import root is bare
     `ingest`, §7.2):

     | class | expected `X.__module__` |
     |---|---|
     | `sources.RegistryError` | `ingest.sources` |
     | `recipes.RecipesError` | `ingest.recipes` |
     | `audit.AuditError` | `ingest.audit` |
     | `gap.GapError` | `ingest.gap` |
     | `io.ProtectedPathError` | `ingest.io` |

     Each case asserts `issubclass(X, cli.IngestError)` **and** `X.__module__ == <expected>`. The
     second half is what catches a class declared in the wrong file, which is the form the
     defect actually took.
  2. **`recipes.CookbookUnavailable is cli.CookbookUnavailable`** — object identity. A
     redeclaration in `recipes.py` satisfies every `from ingest.recipes import
     CookbookUnavailable` in the suite and fails only this, which is why the assertion is `is` and
     not `issubclass`.
  3. **`not issubclass(eval_split.EvalSplitLeak, cli.IngestError)`** — the deliberate non-member.
     Without this, the "consistent" edit (rebase it like the other five) would route a leak through
     `cli.run`'s catch-all and turn §9's G5 exit **6** into a 1, silently, with G5 still "passing"
     its own tests. A negative assertion is the only kind that can protect a deliberate exception.
     ***This assertion is static, and its behavioural half lives in Task 4 (rev 8, C1).*** Revision
     7 gave the newly-rebased `ProtectedPathError` both halves — assertion 4 below drives it through
     `cli.run` and asserts 1 — and gave `EvalSplitLeak` only this one, which is backwards: the
     rebased class is protected by a rule the other four members share, while the *excluded* class
     depends on a handler contract nothing else in the package repeats. Task 4 now drives a leaking
     sidecar fixture through `eval_split._main(["--check-leak", …])` and asserts exactly **6**;
     §4.5 states the handler as normative code. Read the two together: this assertion says the class
     stays outside the hierarchy, Task 4's says the handler that makes that safe exists.
  4. **`ProtectedPathError` → 1 end-to-end:** a handler that calls `io.write_artifact` against a
     `PROTECTED_ROOTS` path, driven through `cli.run`, returns **1** rather than propagating an
     uncaught traceback — which is what it did while the class was a bare `RuntimeError`;
- `test_ingest_offline.py` (AC-1.16): with `default_recipes_path()` pointed at a nonexistent
  path, every subcommand exits per §7.5's table and `pytest -k ingest` reports **zero failures and
  zero errors**, only skips. The suite must be shown to be green on a checkout with no
  `~/projects/repos/` at all — which is 19 of 21 clones' actual state today. **The test is
  parametrized over §7.5's table row-for-row (rev 4, R3-W4)**, which is what makes the table's
  completeness load-bearing: it must include the three clone-independent emitters that exit **0**
  (`audit --emit-fingerprint`, `eval_split --emit-lineage-contract`, and `eval_split --check-leak`)
  as well as the ones that exit 5, because "this command is unaffected by the missing clone" is an
  assertion worth making, not an omission. *Rev 7 (C3): the six emitter rows now spell `--out
  <dir>` and the test supplies a `tmp_path` for it; the table's new final row — the six emitter
  commands with `--out` omitted → **64**, in both columns — is parametrized too, and it is the one
  row whose expected value is the same with and without the clone, which is the assertion that pins
  the ordering (`parse_args` before handler, §7.1).* ***Rev 8 (C4): "row-for-row" is 1-to-1 for
  every row except that one, which is a condition over six commands — so the parametrization is
  **19 cases over 15 rows**: thirteen command rows × 1, plus **six** for the `--out`-omitted row,
  plus zero for the `pytest -k ingest` row (that row is the suite-level assertion this bullet's
  second clause already makes, not a case). Assert `len(CASES) == 19` in the test, so a row added
  to §7.5 without a case fails loudly — the same discipline the README exit-code test below applies
  to §9's vocabulary.*** *Rev 8 (C2): `eval_split --check-leak` is parametrized with the committed
  sidecar path its row now spells, expecting a single **0**; the leaking-input → **6** case is
  Task 4's, against a `tmp_path` fixture, and is deliberately not a row here;*
- `README.md` documents the gate order, **all eight decision exit codes (0/1/2/3/4/5/6/7) plus the
  one non-decision code, 64 = malformed command line** (rev 6, R5-W2 — listed under its own
  heading, so a reader cannot mistake it for a gate answer), and §7.5's
  clone-absent table at the point of use, in the **module-per-command** invocation form
  (`python -m ingest.<module> <flags>`, §7.1 — never `python -m ingest <subcommand>`).
  *Rev 5 (R4-W4): revision 4 said "all seven exit codes (0/1/2/4/5/6/7)" while §9 defines eight.
  The missing one is **3 — STOP, licensing**, which is D1's terminal verdict and the single most
  consequential code in the package: it is the one that kills Increments 2–4. A README that
  documented every code except that one would be a README about the cheap failures.*
- **a test asserts the README's exit-code list matches §9's vocabulary** — the codes are
  parsed out of `README.md` and compared to the `EXIT_*` constants in `cli.py` (§7.1), so the two
  cannot drift the way the prose did. Cheap, and it is the same discipline §7.5's row-for-row
  parametrization applies one paragraph above. *Rev 6 (R5-W2): the comparison is over **nine**
  constants now — the eight decision codes plus `EXIT_USAGE = 64` — and the test asserts set
  equality in both directions, so adding a constant to `cli.py` without documenting it fails just
  as loudly as documenting one that does not exist.*

**Scope estimate**: ~320 LOC

### Task 9: LICENSE-4 — open the cookbook licensing issue

Open an issue on `chory-lab/plr-cookbook` requesting an explicit license (or written permission
for training-corpus derivation), **asking for the file at the repository root** (C21/C24: the
project's content lives under `cookbook/`, so an unqualified request is likely to produce
`cookbook/LICENSE`; `license_scan_dirs` already covers that case, but the root is the
unambiguous ask). Write the issue URL into the cookbook row's `license_request_issue_url`.
A **human action with a due date of 2026-09-10**, written into the plan *"because unwritten human
actions never happen."*

**Files**: `training/ingest/data/sources.json` (modify)
**Gate**: the cookbook row's `license_request_issue_url` is a non-empty
`https://github.com/chory-lab/plr-cookbook/issues/<n>`; AC-1.12's assertion passes on the URL
branch. If the date passes without the issue, AC-1.12 goes red — which is the intended
enforcement, not a bug (§2.8).
**Scope estimate**: ~1 line + one issue

---

## 9. Gate order and exit codes

**Exit-code vocabulary, package-wide.** `0` proceed · `1` measurement error (the implementation or
an input disagrees with a pinned expectation) · `2` unadjudicated blocking finding · `3` STOP,
licensing · `4` STOP, coverage · **`5` INCONCLUSIVE — the measurement could not be taken (§7.5)**
· `6` eval leak or lineage-contract violation · `7` CONTESTED — two readings of one metric
disagree. **5 is never a descend signal and never a pass.** That is **eight** codes; Task 8's
README documents all eight, including **3**, which revision 4's task text omitted (R4-W4).

**Those eight are *decisions*, and there is exactly one code that is not (rev 6, R5-W2).** A
malformed command line — a missing required flag, a typo, an unrecognized argument — exits
**`64`** (`cli.EXIT_USAGE`, `sysexits.h`'s `EX_USAGE`), deliberately far outside the 0–7 range any
gate wrapper reads. Until revision 6 it exited **2**, not by anyone's decision but because
`argparse.ArgumentParser.error()` calls `sys.exit(2)` before a handler is ever reached — so
`python -m ingest.audit` with a typo was byte-indistinguishable from *"the canonical tables are
contested and nobody has adjudicated it"*, in the one gate §7.5 spends a paragraph protecting from
exactly that confusion. §7.1 states the mechanism (`cli.IngestArgumentParser` overrides `error()`;
`exit_on_error=False` is **not** sufficient and why, plus the exception hierarchy that keeps
`cli.py` importable). **So: eight decision codes, 0–7, plus one
non-decision code, 64.** The vocabulary is still closed; revision 5's claim that it was closed at
eight was true of what the spec intended and false of what the spec's own normative template would
have produced.

**Every command below is `uv run --package training python -m ingest.<module> <flags>`** — a
module under `ingest`, never a subcommand of a dispatcher (§7.1, R4-B2). `python -m ingest` itself
prints a signpost and exits 0; it dispatches nothing.

*Rev 6 (R5-B1): every row of this table is a claim about a **command**, and until this revision
every test behind those claims called a **function**. The `if __name__ == "__main__":` block that
joins the two is now executed by Task 8's `test_ingest_entrypoints.py` (`runpy.run_module(...,
run_name="__main__")` over all five modules), so a gate row can no longer be green in the suite and
vacuous at the command line.*

| Gate | Command | Exit 0 | Non-zero |
|---|---|---|---|
| **G0** license verification | `python -m ingest.licenses --report` | all 21 rows verified | 1 (I/O / registry / rules-pin error). An absent clone is **not** an error here — it is a `NOT_CLONED` verdict in the report |
| **G0b** clone verification | `python -m ingest.licenses --verify-clones` | all 21 clones at `pinned_sha` | **5** if every failure is an absent clone; **1** if any present clone is at the wrong SHA. `--require-all` forces 1 and is used by Task 0 only (AC-1.15, R2-B4c) |
| **D1** descend rule | `python -m ingest.licenses --check-descend` | `tier1_plus_effective_count >= 4` → continue | **3** → STOP (real licensing verdict); **5** → INCONCLUSIVE, provision clones and re-run — **not** a descend signal |
| **G2** drift audit | `python -m ingest.audit --gate` | all **nine** blocking findings (§5.4.1) adjudicated **at their current digest**; may still print advisory `census_drift` lines (read from `data/blocking_census.json`, R3-B2) without failing | **2** → no downstream generation (`missing` / `incomplete` / `stale_digest`); **5** → cookbook clone absent, audit not run; **1** → `data/blocking_census.json` absent, unreadable, or failing its `BLOCKING_KINDS` loader invariant (rev 5, R4-W10 — a committed in-repo file, so its absence is a measurement error, not an environment condition) |
| **G1** gap gate | `python -m ingest.gap --gate` | PROCEED to Increment 2 | **4** → STOP, descend to floor_gen; **7** → T2's two readings disagree (CONTESTED — resolve by spec revision, not by re-running); **1** → T1 invariant violated (measurement error); **5** → cookbook clone absent |
| **G5** eval-leak gate | `python -m ingest.eval_split --check-leak training/assemble/out/corpus_p25_sidecar.jsonl` (the path is `--check-leak`'s **own required argument**, no default — rev 8, C2) | no held-out path in training, no unattributed cookbook lineage, **no undeclared lineage key** | **6** → leak or `contract_violation`, listing every offending `record_id` / key, returned by the handler's `except EvalSplitLeak` clause (§4.5's normative block; Task 4 asserts it). Unaffected by clone absence: it reads only committed in-repo data |

G1 is numbered after G2 in the brainstorm's ordering but runs last here: the audit is the FIRST
DELIVERABLE (`[ACCEPT] ORTHOGONAL-2`), and a canonical-table bug would invalidate the gap
report's verb/param accounting. **G3 and G4 are out of scope for Increment 1** — G3 needs the
matrix-diff (Increment 3) and G4 needs the blocked teacher backend (F8). **G5 is new in rev 2**
(C11): it runs from Increment 1 onward, and in rev 3 it stops being merely *green* and becomes
*live* — its lineage-contract assertion (W3) evaluates over all 188 committed rows today, so the
leak obligation has both an owner and something to check.

**Round 2's contradiction, and where it is resolved.** Revision 2's G0b row read "1, listing every
miss" while D1's row read "5 → INCONCLUSIVE, provision clones and re-run" — the same missing
clones, two rows apart, one killing the run and one explicitly not. §7.5 resolves it by making 5
the package-wide code for an untaken measurement and by splitting G0b's two genuinely different
failures (absent vs wrong-SHA). Nothing about C25/C28's per-row exactness is relaxed.

---

## 10. Risks

| Risk | Likelihood | Mitigation / Rollback |
|---|---|---|
| **PM-1 recurrence:** D1 fires a genuine STOP and Increments 2-4 are dead. | **High** — the cookbook has no root LICENSE and `cheshire-drivers` is AGPL. | This is the plan working. Increment 1 still delivers the drift audit, the surface-expansion ranking, the gap report, and the eval split — all tier-0-legal. `LICENSE-6` is the acceptance criterion. Rollback: none needed; stop at Task 9. |
| **D1 fires on an unprovisioned machine** and kills the plan for an environment reason. | Medium — CI or a fresh checkout has no `~/projects/repos/`. | **Rev 2 fix (C6):** exit **5** INCONCLUSIVE is distinct from exit 3 STOP, and only fires when the unmeasured rows could change the outcome. §9 states plainly that 5 is not a descend signal. |
| **PM-2 recurrence:** a threshold is raised after seeing a STOP. | Medium | Thresholds live in `versions.py` behind `GAP_THRESHOLDS_VERSION`; Task 7 requires the threshold commit to precede `gap.py`'s. **Rev 2 (C7)** extends the same armour to `license_rules.json` — version + sha pin + report record — because D1 runs first and matters more. **Rev 2 (C12)** removes T1, whose threshold was post-hoc. |
| **PM-3 recurrence:** a blocking finding is adjudicated, then materially changes, and the stale adjudication keeps the gate green. | **Was high in rev 1** | **Rev 2 fix (C3):** `adjudicable_digest` binds the adjudication to the verdict + evidence classes + per-subject table fingerprint it was made against; a flip yields `stale_digest` and exit 2. Task 5's `lh.mix` test proves it. |
| **PM-4 recurrence:** eval paths leak into training. | Low, high damage | Committed path list is authoritative (§4.4), monotonicity invariant forbids un-holding-out, `recipes_yml_sha256` tripwire fires first on any upstream change, and **G5 runs today** (§4.5) rather than waiting for a future increment to call a helper. |
| **The gap metric crashes on the real corpus** because `PARAM_NAMESPACE` is not the shape the code assumes. | **Was certain in rev 1** | **Rev 2 fix (C1):** flattened `_PARAM_INDEX`, total `.get()` lookup, `unmapped_params` counter, keying pinned to `ParamSpec.name` with evidence, and a direct unit test over a `mix` call. |
| **The recipes reader silently truncates every anchor** by treating `#` as a comment. | **High if unguarded** | Grammar pinned to line-initial `#` only; every `path` validated against a regex, so truncation raises rather than corrupts; a dedicated fixture in Task 3's gate. |
| **A `*Backend` heuristic fabricates blocking findings** on Thermocycler/Incubator receivers. | **Was high in rev 1** | Exact alias table, zero-unmapped gate over the current 91 recipes, and the recorded safety asymmetry (unmapped → `other` can only under-report). |
| **`apis` tokenizer produces a garbage audit** by treating prose/class/labware tokens as method names. | High if unguarded | Classifier is total, closed, and **mutually exclusive with a live assertion** (C22); `OTHER` is a counted bucket; eight verbatim samples pinned. |
| **Class-vocabulary drift** (`none` vs `clean_parse`) mis-attributes rows to cells. | Medium | `gap.py` imports `assemble.build.CLASS_MAP`; a private copy is banned; the manifest cross-check (137/13/17/21) fails loudly. The transitive-purity cost of that import is handled in §7.3, not ignored. |
| **A canonical-table edit silently invalidates the 188-row corpus.** | Low, catastrophic | **Rev 2 fix (C13):** `canonical_tables_fingerprint.json` + AC-1.14's red test carrying the four-stage, five-file regeneration checklist, plus the required `impact` block on any `edit_table_by_hand` adjudication. **Rev 3 (W1)** binds the five artifacts' own sha256s into the file, so the tripwire cannot be silenced by editing one hex string. |
| **`audit.py` or a well-meaning follow-up patches a canonical table.** | Low, catastrophic | **Rev 2 (C2):** single-writer choke point with runtime `ProtectedPathError`, a decidable single-writer AST property, and a byte canary over the four artifacts. |
| **F3 violation via a transitive import.** | **Was live in rev 1** | **Rev 2 (C14):** transitive closure scan + a one-entry allowlist with a reason + a runtime `subprocess`-patched pipeline run. |
| **`python -m ingest.*` does not work**, so six ACs are unrunnable. | **Was certain in rev 1** | **Rev 2 (C15):** AC-1.0 gates importability from the repo root and Task 1 performs the editable reinstall. |
| **F6 violation:** a timestamp lands in a report. | Medium | §7.4 bans `datetime.now()` in payloads; AC-1.10 runs each writer twice into distinct temp dirs; the one date-dependent check lives in a test with an injected `today`. |
| **Scope creep back to the full architecture.** | Medium | The out-of-scope table names each deferred module; §2.7 states the Increment 1/2 field boundary; `training/ingest/README.md` repeats both at the point of use. |
| **`training/pyproject.toml` merge conflict.** | Low | The file's own comment mandates *extending* `include`; Task 1 adds exactly `"ingest*"`. |
| **A gate is unsatisfiable because a count asserted in prose disagrees with the file it describes.** | **Was certain in rev 2** — Task 6 seeded 4 adjudications against a 9-finding census | **Rev 3 (R2-B1):** §5.4.1 derives the census per kind with the derivation shown, AC-1.6 pins it as a regression pin, and the structural bound replaces "small". The standing rule in the header banner — derive, never hand-list — is the general form. |
| **Two implementers produce two different `finding_id` key spaces**, so the committed adjudications match neither. | **Was certain in rev 2** — `subject` was undefined for all ten kinds | **Rev 3 (R2-B2):** §5.2's ten-row subject table plus §5.7's three fingerprint cases. |
| **A fresh checkout or CI runner hard-fails G0b for an environment reason**, contradicting D1's own INCONCLUSIVE branch. | **Was certain in rev 2** — 19 of 21 clones absent on this machine | **Rev 3 (R2-B4):** §7.5's package-wide exit 5, a per-command behaviour table, G0b's absent/wrong-SHA split, and AC-1.16 asserting the suite is green with no clones at all. |
| **A shallow `main`-tracking cookbook clone moves under the pipeline**, and a byte-hash mismatch is misdiagnosed as file corruption. | Medium | **Rev 3 (R2-B4d):** §4.4 assertion 0 pins the commit SHA and runs *before* the byte pin, so the two failures carry different messages; §2.5 reports `shallow` per row. |
| **A metric's normalization silently becomes the gate authority** through a rule meant to guard against it. | **Was live in rev 2** | **Rev 3 (W2):** the `T2_collapsed ≥ T2_strict` algebra is written out, `T2_collapsed` is the authority, and disagreement is exit 7 (CONTESTED), which authorizes nothing. |
| **A future increment renames a lineage field and G5 stays green forever.** | Medium, high damage | **Rev 3 (W3):** `lineage_contract.json` fails G5 on **any** undeclared lineage key, so the rename is a red gate rather than a silent bypass. Residual risk (a correctly-named but wrongly-populated field) is §12.6. |
| **A `surface_adjacent` finding disappears — upstream drops the recipe — and its adjudication silently stops covering anything**, shrinking G2's scope while it stays green. | **Was live in rev 3** — the digest cannot go stale for this kind, and stale adjudications are warnings | **Rev 4 (R3-B1/R3-B2):** §5.7's table-sensitivity table states per kind whether the digest can go stale at all, and names the replacement detector where it cannot. Disappearance by table edit is caught by AC-1.14; disappearance by cookbook change is caught **only** by the census pin, which is why R3-B2 gave it a real home and Task 6 tests drift *down*. |
| **The census pin is unimplementable**, so `census_drift` is never printed and AC-1.7's stated behaviour does not exist. | **Was certain in rev 3** — the pin lived in a test literal the gate cannot read | **Rev 4 (R3-B2):** `data/blocking_census.json`, emitted by `audit --emit-census`, landed by §5.6(d)'s copy-and-review workflow, read by the gate, and compared against the observation by AC-1.6's test — which holds no literal of its own. A loader invariant ties its key set to `BLOCKING_KINDS`. |
| **A mechanically "computed" `receiver_aliases.json` is emitted all-`other`**, key-set equality passes, and 5 of the 9 blocking findings vanish without a red test. | **Was live in rev 3** — §5.6(d) told a fixer to generate a file C9 proves cannot be generated | **Rev 4 (R3-B3):** the file is reclassified **hand-authored (values) / derivable (keys)**; the emitter becomes a merge proposal that never overwrites a value and flags new keys for review; §3.3 rule 5 states the value rule and the `surface_adjacent` interaction; Task 3 pins the three `liquid_handler` values by name; and §5.6(d)'s false "every computed file is re-derived" claim is deleted in favour of a per-row strength column. **Rev 5 (R4-W2)** corrects the residual over-claim: the census is *not* an independent detector at authoring time (Task 5 emits it from Task 3's map), so §3.3 rule 5 now orders the three guards by when each can fire and names Task 3's value pin as the only one that catches an initial error. |
| **A reader invariant makes the spec's own test fixtures unparseable**, so four tests — including the two the spec names as proving its most severe fix — cannot be written, and a fixer either deletes them or ships a carve-out nobody reviewed. | **Was certain in rev 4** — "exactly 91 records" was unconditional and four fixtures are 2, 90 or 92 records | **Rev 5 (R4-B1):** §3.1's invariant list is reduced to properties true of *any* well-formed input, and the count moves to `token_histogram.json`'s `n_recipes`, checked by AC-1.4(2)'s existing exact comparison. Truncation stays caught, by three detectors that already existed (the `path` regex, `n_recipes`, and §4.4's byte + SHA pins). Each of Task 3/5/6's fixtures is re-confirmed at its point of use. |
| **A blocking gate passes vacuously** because the spec spells its invocation two ways: `python -m ingest.audit --gate` imports a module with no `__main__` guard, ignores the flag, and exits 0. | **Was certain in rev 4** — §7.1 specified a dispatcher, ~30 other invocations specified module-per-command | **Rev 5 (R4-B2):** §7.1 is corrected to the module-per-command form the ACs, gate rows, §7.5 table and tasks already use, and the false "mirrors `floor_gen/cli.py`" claim is deleted. `cli.py` keeps the one thing the dispatcher bought (§7.5's exit-5 mapping, implemented once); `__main__.py` becomes a non-dispatching signpost; both move to **Task 1**, closing the ordering hole where AC-1.0 and Tasks 2–5's gates invoked a CLI that did not yet exist. Task 1 gates that the dispatcher spelling exits **1**, so two spellings can never both appear to work. |
| **A digest is interpreter-version-dependent**, so the hand-committed adjudication keys match on the machine that wrote them and nowhere else. | **Was certain in rev 4** — `f"{kind}"` on a `str`-mixin Enum yields the value on 3.10/3.12 and `FindingKind.PHANTOM_VERB` on 3.11 | **Rev 5 (R4-B3):** `finding_id` hashes a structured `canonical_json` payload with `kind.value`, matching `_adjudicable_view`'s already-correct usage; every hash input in the spec was swept (the only other enum reaching a payload is `_projection()`'s `receiver_type`, verified a plain `str` on the live `ToolSpec`); and **`canonical_json` is defined** — four arguments, each justified — at its first use site, with §7.4 stating why hash serialization deliberately differs from artifact serialization. **Rev 6 (R5-W4)** closes the half rev 5 could not test: no behavioural test can see this bug on 3.10/3.12, where the buggy spelling is *correct*, so the identity path drops f-strings entirely (`_finding_id_payload`, `dotted_subject`, `param_subject`) and the hazard becomes unrepresentable rather than probed. The same sweep found the *subject* builders had the identical exposure, one field over from the one R4-B3 fixed. |
| **A blocking gate passes vacuously a second time** — the entry-point *shape* is right, but a fixer omits the `if __name__ == "__main__":` line from `audit.py`, so `python -m ingest.audit --gate` imports the module, ignores the flag and exits **0**, with the entire specified suite green. | **Was live in rev 5** — every test drove handlers in-process by explicit rule, and nothing executed a module as `__main__` | **Rev 6 (R5-B1):** Task 8's `test_ingest_entrypoints.py` runs `runpy.run_module(f"ingest.{m}", run_name="__main__")` over all five command modules (no-args → `EXIT_USAGE`) and drives `audit --gate` with the clone absent → `SystemExit(5)`. A missing guard raises **nothing**, so the failure is `DID NOT RAISE` and names the module. In-process, no subprocess, so F3 and §7.3 are untouched. The lesson generalizes: R4-B2's fix corrected a sentence and installed no detector, which is why the header banner's rev-6 rule asks what goes red if the implementation disagrees. |
| **A typo on the command line reports "the canonical tables are contested."** `argparse.ArgumentParser.error()` exits **2** before any handler runs, and 2 is §9's code for an unadjudicated blocking finding. | **Was certain in rev 5** — the normative §7.1 template used a bare `argparse` parser with a `required=True` group | **Rev 6 (R5-W2):** `cli.IngestArgumentParser` overrides `error()` (not `exit_on_error=False`, which leaves missing-required-argument going to `sys.exit(2)`), `cli.run` owns `parse_args`, and usage errors return **64** (`EX_USAGE`) — outside §9's 0–7 decision range by design. `--help` still exits 0. |

---

## 11. References

- **Adversarial review (binding on this revision):** `transduction_query(scope="task",
  task_id="260827_corpus_ingestion_spec", payload={phase:"audit"})`, audit_ids
  `260827_corpus_ingestion_spec_challenge_round1` (verdict `not_ready`, 13 blocking + 15 warning →
  revision 2, dispositions in §0.1–§0.3),
  `260827_corpus_ingestion_spec_challenge_round2` (verdict `not_ready`, 4 blocking + 15 warning →
  revision 3, dispositions in §0.4), and
  `260827_corpus_ingestion_spec_challenge_round3` (verdict `not_ready`, 3 blocking + 9 warning →
  revision 4, dispositions in §0.5), and
  `260827_corpus_ingestion_spec_challenge_round4` (verdict `not_ready`, 3 blocking + 10 warning →
  revision 5, dispositions in §0.6), and
  `260827_corpus_ingestion_spec_challenge_round5` (verdict `has_gaps`, **1 blocking** + 4 warning +
  4 suggestion → this revision, dispositions in §0.7). Round 3 **verified** R2-B1's census, R2-B3's
  classifier and R2-B4d's assertion ordering against the live files; round 4 verified **all three**
  of round 3's dispositions plus the census a third time, and **reopened nothing** — its three
  blockers are transcription defects (a reader invariant, an entry-point spelling, a hash input),
  not design defects; round 5 verified **all three** of round 4's dispositions, reproduced the
  91-record count a **fourth** time, re-confirmed `ToolSpec.receiver_type` as a plain `str` and
  `PHASE2_TOOL_NAMES` as a `frozenset` live, and **also reopened nothing** — its single blocker is
  that revision 5's fix for R4-B2 installed no observation of itself. Those verifications are
  recorded at their point of use (§5.4.1, §3.2, §4.4, §5.7, §7.1) as well as in §0.5–§0.7.
  **The convergence is monotonic across five rounds: 13 → 4 → 3 → 3 → 1 blocking.**
- **Brainstorm / decision record (binding):**
  `.praxia/docs/specs/260827_coxswain-corpus-ingestion-strategy-turni.md` — contemplex session
  `5b59d8e9`. Load-bearing entries cited above: `[REJECT] INVEST gate` (Increment 1 scope +
  descend rules), `[ACCEPT] ORTHOGONAL-2` (drift audit, first deliverable, four phantoms),
  `[ACCEPT] LICENSE-3` (tier ladder, LICENSE-1/4/5/6), `[ACCEPT] TRIAGE-2+3+4+5` (measured
  triage, reject-by-default), `[MERGE] ORTHOGONAL-7` (gap report as gate), `[MERGE]
  ORTHOGONAL-1` (eval split), `[ACCEPT] Pre-mortem mitigations PM-2/PM-3/PM-4`, `[REJECT] NL-5`
  + `H6` (LLM-adjacent rejection class), `[REJECT] TRIAGE-1` (stars are a tiebreak, never a key).
- **Source survey:**
  `.praxia/docs/research/260827_real-world-pylabrobot-dependent-repos-as-corpus-derivation-candidates.md`
- **Canonical tables (read-only inputs, never written):**
  `coxswain/src/coxswain/plr/tool_schema.py` (20 entries, 13 in `PHASE2_TOOL_NAMES`, **seven**
  `experimental=True` — four phantoms + three heater-shaker no-backend;
  **`ToolSpec` is `@dataclass(frozen=True)` at :35** and `receiver_type` is a plain **`str`** at
  :41 — the first fact decides Task 5's monkeypatch technique (R4-W6), the second is why
  `_projection()` needs no `.value` on it (R4-B3); `TOOL_SCHEMA` at :80 is a plain `dict` and
  `PHASE2_TOOL_NAMES` at :194 is a `frozenset` **materialized at import**, so it does not follow a
  `setitem` on the dict),
  `coxswain/src/coxswain/plr/param_namespace.py:142` (`PARAM_NAMESPACE:
  dict[str, tuple[ParamSpec, ...]]`, 13 verbs; `params_of()` raises `KeyError` for excluded
  tools), both pinned to vendored PLR HEAD `dd79c4c89bc008629a1c598ea614be5e6067d1f9`.
- **Existing generators (read-only inputs):**
  `training/floor_gen/matrix.py` + `training/floor_gen/data/ambiguity_matrix.json` (43 cells;
  `MatrixCell.verb: str | None`, `None` only for `generic__out-of-surface`),
  `training/overlay_gen/miner.py:71-108` (`NON_SURFACE_VERB_REASONS` — **28** entries, not 29;
  `_KNOWN_VERBS`, `MinedCall`, `MinedExclusion`),
  `training/assemble/build.py` (`CLASS_MAP` at :76 — hyphenated → underscored; `import
  subprocess` at :27; `from praxis_training.golden_build.corpus import …` at :35, the edge §7.3(b)
  category 4 names),
  `training/assemble/__init__.py` (re-exports `.build` — the reason §7.3's extraction fix fails),
  `training/assemble/out/{manifest.json,corpus_p25_sidecar.jsonl}` (188 rows; 20 carry
  `lineage.cell_id`; 12 carry `verb: ""`; 21 carry `calls: []`; **lineage key sets differ by
  provenance** — coverage rows carry `{cell_id, gap_fields, generator_version,
  matrix_ambiguity_class, matrix_version, prompt_version, source_file, teacher_model_version}`,
  naturalness rows add `origin`/`receiver_type`/`source_notebook_or_protocol`, golden rows add
  `authoring_note`; the authoritative union is computed by `--emit-lineage-contract`, §4.5).
- **Cookbook source:** `~/projects/repos/plr-cookbook/cookbook/recipes.yml` (91 recipes, 18
  chapters, 12-line comment header, bare-scalar `path` values containing `#`; **31 distinct DOTTED
  receivers**, of which 3 map to `liquid_handler` and 0 to `plate_reader`, §3.3); repo root has
  **no LICENSE file** as of 2026-08-27 and its content lives under `cookbook/`. The clone is
  **shallow and tracks `main`** — see §2.5's hazard note and §4.4's assertion 0.
- **Downstream context:** `.praxia/docs/specs/260825_p25_slice_gate.md`,
  `.praxia/docs/specs/260825_p25_provisional_thresholds.md`,
  `.praxia/docs/decisions/260827_teacher-backend-gemini-3-7-flash-for-full-scale-floor_gen-overlay_gen-pass.md`.

---

## 12. Known limitations, deliberately unaddressed

Recorded so the next adversarial round can see what was triaged out and why, rather than
rediscovering it. **Round 2 re-examined every item**: 1, 2, 4, 5, 7 and 8 were confirmed genuinely
non-blocking and are unchanged; 3 and 6 are rewritten below; 9, 10 and 11 are new in rev 3.
**Round 3 raised no objection to items 1–11**; item 11 is rewritten for the recount and for
`receiver_aliases.json`'s reclassification, and **items 12 and 13 are new in rev 4** — 12 for the
unverifiable `action_ref` and the ownership of the five backlog items (R3-W8), 13 for the
per-kind asymmetry of the digest's anti-staleness property (R3-B1), which is the item a round-4
reviewer should read first.
**Round 4 raised no objection to items 1–13**; item 11 gains a line for `token_histogram.json`'s
`n_recipes` (R4-B1), **item 13's count is corrected** from "six" to "five, plus one partial"
(R4-W8), and **item 14 is new in rev 5** (R4-B2): the package deliberately has no unified CLI,
which is a real ergonomic cost and the item a round-5 reviewer should weigh first, because it is
the only round-4 fix that chose consistency with this document over consistency with the
neighbouring package.
**Round 5 raised no objection to items 1–14** — including item 14, which it was invited to weigh
and did not contest; **item 15 is new in rev 6** (R5-S4): the advisory finding kinds are not a
partition of tokens, which is the item a round-6 reviewer should read first, because it is the only
place in this spec where two committed output tables deliberately describe the same input twice.

1. **AC-1.12's deadline test is time-dependent and therefore not hermetic.** A CI run on
   2026-09-11 goes red with no code change. This is intended (§2.8): the alternative — a check
   that cannot expire — is what C23 objected to. Accepted cost: one class of "the suite broke and
   nobody touched it" incident per missed deadline, with a documented remedy (file the issue, or
   record a ≤30-day extension).
2. **`data/token_histogram.json` and `T1_INVARIANT` are post-hoc-computed values.** Both are
   labelled **regression pins / invariants, never thresholds**, and no gate decision reads them
   as authority. They are in the same category as a golden-file test. Calling them
   pre-registration would be the exact confusion C12 punished.
3. **The Increment 1 → 2 field boundary (§2.7) is a statement, not an enforced constraint.**
   Increment 1 cannot mechanically prevent Increment 2 from editing `genre`. What Increment 1 does
   is make honouring the boundary *possible* (by decoupling the fields, C17) and write the rule
   down for the next spec to inherit. An enforced version would need a registry diff-checker with
   a per-field allowlist, which is Increment 2's cost to pay, on Increment 2's evidence.
   **Rev 3 note (round 2's W3):** this item is the *general* form of which item 6 is a specific
   case, and saying so is the point. Increment 1 cannot bind a later increment's field names,
   which is exactly why G5's rules 1 and 2 key on fields that do not exist. Every finding of this
   shape traces back here. What §4.5 demonstrates is the workaround available in general: a
   later increment cannot be made to *choose* a name, but it can be made **unable to add a name
   silently**. Increment 2's spec should apply the same trick to the registry — commit the field
   vocabulary, fail on an undeclared field — rather than relying on §2.7 being read.
4. **The transitive-purity allowlist (§7.3) admits one real leak.** `assemble.build` imports
   `subprocess`. The runtime patched-run test proves it never executes during an ingest run, but
   the *import* remains in the closure. The clean fix (splitting `CLASS_MAP` out of a package
   whose `__init__` re-exports `build`) changes another sub-pipeline's public surface and is
   deliberately out of scope. Filed as a note for whoever next touches `assemble`.
5. **`unmatched_cell_keys` is reported but not *gated*, though it is *pinned*.** Rev 3 draws the
   distinction round 2's W9 forced: pinning the current value (`{}`, §6.1) as a **regression pin**
   is legitimate — it says "0 → non-0 is a change worth seeing" and no decision reads it. Choosing
   a **threshold** ("N > k justifies ingestion") would be the post-hoc gate-setting C12 objected
   to, and it stays out. The manifest cross-check already catches the mis-attribution failure that
   would matter most. Increment 2, which will have recon counts, is the right place to *gate* it.
   *(Revision 2 recorded the opposite expectation — non-empty — which was wrong against the file;
   the deferral survives the correction, the expectation did not.)*
6. **G5's field-name contract with Increment 3 is enforceable only in one direction.** Round 2
   (W3) correctly rejected revision 2's framing of this as "a limitation of the corpus". The
   corpus is not the problem: the problem is that G5's leak rules key on `lineage.source_id` and
   `lineage.recipe_path`, **neither of which exists in the live sidecar**, and both of which are
   named by `assemble`/Increment 3 — which item 3 concedes Increment 1 cannot constrain. So
   revision 2's G5 could have stayed green forever simply by Increment 3 choosing `qmd_anchor`.
   `lineage_contract.json` (§4.5) closes the half that is closeable: **no new lineage key can
   appear without failing G5**, so a rename is a red gate and a reviewed diff rather than a silent
   bypass, and G5 gains a live assertion over all 188 rows today. **The residual, stated
   precisely:** Increment 3 could add `recipe_path` to the contract, satisfy the gate, and then
   populate it incorrectly or incompletely — a *value* error rather than a *name* error, which no
   Increment 1 mechanism can reach. Increment 3's spec inherits that obligation, and the right
   place to discharge it is a positive assertion on its own side (every cookbook-derived row
   carries a `recipe_path` that resolves to one of the 91 recipes), not another guard here.
7. **`SOURCES.md` is generated from the license report, not from provenance rows.** A deliberate
   narrowing of LICENSE-5 (§2.6), because there are no corpus rows yet. Increment 4 must widen it.
8. **The 20 non-cookbook rows' `extractor_kind` values are authored from the research doc, not
   measured.** They are observations from a survey, not from a parse. Increment 2's recon pass
   will confirm or contradict them, and §2.7 forbids it from silently editing them — a
   contradiction is a registry edit with a recorded reason. Nothing in Increment 1 depends on
   these values being right.
9. **§5.6(b)'s AST write-primitive list is a lint, not a proof, and its completeness is not
   claimed.** Round 2 (W7) found nine omissions in revision 2's list; rev 3 extended it and
   withdrew the claim rather than pretending the next list is complete. An AST blacklist over an
   open-ended standard library cannot be — a module could reach a write through `getattr`, a
   C extension, or a primitive nobody thought of. The property is proved by §5.6(c)'s byte canary,
   which observes the four canonical tables before and after a full pipeline run and does not care
   how a write was spelled; (b) exists because it is cheap and catches the accident early. Anyone
   tempted to strengthen this should strengthen (c)'s coverage instead — more files hashed is
   worth more than more names blacklisted.
10. **`method_shaped()` cannot distinguish a method from an attribute or a module.**
    `recipes.yml` records API *names*, not call syntax, so `lh.head` (an attribute) and
    `lh.use_tips` (a method) are indistinguishable to the classifier, as are `manifest.json` →
    member `json` and `backends/chatterbox.py` → member `py` (§3.3 rule 3). One of §5.4.1's five
    blocking findings — `liquid_handler.head` — exists purely because of this, which is why §5.5
    gained the `token_is_not_a_method` reading rather than forcing a false one. Resolving it
    mechanically would require parsing the cookbook's `.qmd` code fences for call syntax, which is
    Increment 3's `cookbook.py` and explicitly out of scope here. The cost is bounded and visible:
    a small number of adjudications whose written answer is "this token is not a verb".
11. **Five `data/` files are computed and then copied in by hand (§5.6d), and one more is a
    hand-authored file whose *keys* a command proposes.** No ingest command may write into a
    protected root, so `token_histogram.json`, `eval_split.json`,
    `canonical_tables_fingerprint.json`, `lineage_contract.json` and `blocking_census.json` are
    emitted to `--out` and moved by a human, and `receiver_aliases.json`'s key set arrives the same
    way as a merge proposal. That is a manual step in an otherwise mechanical pipeline and it will
    occasionally be forgotten.
    **Rev 4 recount and correction (R3-W5, R3-B2, R3-B3):** the numbers here were wrong three ways
    at once — this item said "four" and listed five; §0.4's W12 row said "six and four"; §5.6(d)
    and §7.1 said 5+5. The authoritative split is now **six hand-authored + five computed = 11**,
    and it changed for substantive reasons, not by recounting: `blocking_census.json` is new
    (R3-B2), and `receiver_aliases.json` moved to hand-authored because C9 makes its values
    uncomputable (R3-B3).
    **Why the manual step is still accepted, stated more carefully than revision 3 stated it:**
    revision 3 justified it with "every one of the five has a gate that re-derives it", which
    §5.6(d) now shows is false — two checks are weaker than re-derivation *by design*
    (`lineage_contract.json`'s subset test, `eval_split.json`'s deliberately one-way containment)
    and one is key-set-only (`receiver_aliases.json`). The accurate justification: **every one of
    the eleven has a stated check whose strength is written down**, so a stale or mis-copied file
    surfaces as a red test *to the extent that column claims* and no further — and the
    alternative, letting a command write its own gate input, is exactly the property PM-2 and C2
    were built to forbid.
    **Rev 5 (R4-B1):** `token_histogram.json` gains an `n_recipes` field, the new home of the
    "exactly 91 recipes" claim after §3.1's reader stopped enforcing it. The **file set is
    unchanged at eleven** and so is this item's manual-step cost; one existing computed file
    carries one more field, checked by the same exact comparison as everything else in it.
    `receiver_aliases.json`'s first version is now explicitly a hand transcription rather than an
    emitter run (R4-W1), which does not change the count either — it was already the
    hand-authored row this item's second sentence describes.
12. **`action_ref` and `regeneration_backlog_ref` are grammar-checked, never resolved — and the
    five `NON_SURFACE_VERB_REASONS` backlog items have a named owner outside Increment 1
    (R3-W8).** §5.5's `ACTION_REF_RE` proves a reference is *well-formed*; nothing in this package
    proves it *exists*. It cannot: there is no backlog reader in `training/ingest/`, F3 forbids
    `subprocess`, and reaching a backlog service would break the offline guarantee §7.5 and
    AC-1.16 exist to protect. Resolvability is therefore **unverified by design**.
    **Owner and timing of the five items.** Task 6 files one backlog item per `surface_adjacent`
    subject (`use_channels`, `use_tips`, `head`, `clear_head_state`,
    `probe_tip_presence_via_pickup`). Their owner is **whoever next edits
    `training/overlay_gen/miner.py`'s `NON_SURFACE_VERB_REASONS`**, and their closure is a
    **prerequisite of that edit**, not an independent errand — because AC-1.14 turns any such edit
    red until the four-stage, five-file regeneration is done. The earliest increment that can
    perform that regeneration is **Increment 3** (floor_gen + overlay_gen at full scale, once the
    F8 teacher gate opens), so Increment 3's spec inherits them, exactly as §12.6 hands it the
    lineage-value obligation. Four of the five are expected to resolve as `table_is_wrong` (add the
    exclusion with a reason); `head` is expected to resolve as `token_is_not_a_method` (no table
    change at all, item 10).
    **What is *not* claimed:** nothing in Increment 1 verifies the items were filed. The gate
    checks that a well-formed reference was written down by a named human on a named date. That is
    PM-3's ask — ownership in writing — and it is the ceiling of what an offline gate can reach.
13. **The `adjudicable_digest`'s anti-staleness property is per-kind, and it is absent for
    `surface_adjacent` — 5 of the 9 blocking findings (R3-B1).** §5.7's table-sensitivity table
    derives this: a `surface_adjacent` finding exists *because* all three table memberships are
    `False`, so the edit that would flip one deletes the finding rather than staling it. This is
    recorded as a limitation rather than left in §5.7 because it is the first thing a round-4
    reviewer should re-check, and because the honest framing matters: the digest delivers
    **subject-distinctness for all ten kinds** and **table sensitivity for five, plus one partial**
    — and revision 3 claimed both for all ten while working its only example on the one blocking
    kind where the second claim is vacuous. *Rev 5 (R4-W8): revision 4 wrote "for six" here,
    counting `param_candidate`'s **partial** row as a `yes`. §5.7's table reads 5 yes + 1 partial
    + 4 no, and `param_candidate` is partial precisely because its sensitivity depends on the
    token — sensitive when the token matches another verb's `ParamSpec`, **deleting** the finding
    when it matches nothing and is then added to the named verb. Rounding a conditional up to a
    `yes` is the same move that produced R3-B1 in the first place, inside the item written to
    record R3-B1. The number that decides anything is narrower still: of the four **blocking**
    kinds three are sensitive, and by finding count the digest's table sensitivity covers **4 of
    the 9** live blocking findings.* The compensating detectors are named (AC-1.14 for a table-edit
    disappearance, the census pin for a cookbook-side one) and both are tested (Task 5, Task 6),
    so the gap is covered — but by a *different* mechanism than the one whose name suggests it,
    and a reader who assumes the digest covers everything will mis-locate the next failure.
    **The rejected alternative, recorded so it is not re-proposed:** widen `_verb_slice` to hash
    the whole `_projection()` for these kinds. That restores table sensitivity and destroys the
    per-subject property C3 built the digest for — every unrelated table edit would stale all nine
    adjudications. §5.2 rejected a global fingerprint for exactly that reason, and re-introducing
    it for one kind buys a detection that AC-1.14 already provides more strongly.
14. **The package has no unified CLI, and `python -m ingest` dispatches nothing (rev 5, R4-B2).**
    Five modules each own an `argparse` parser and a `__main__` guard; `__main__.py` is a signpost
    that prints the five commands and exits 0. That is a real ergonomic cost — there is no
    `ingest --help` listing every flag in one place, no shared `--verbose`, and five parsers to
    keep stylistically consistent — and it is **not** the shape the sibling `floor_gen` package
    uses, so a reader who knows that package will expect a dispatcher and not find one.
    **Why the cost is accepted rather than paid down.** Every acceptance criterion, every §9 gate
    row, every §7.5 table row and five of the ten tasks are written in the
    `python -m ingest.<module> <flags>` form — thirty-odd invocations against one parenthetical
    that said otherwise. Converting them all to a dispatcher would be a large mechanical diff
    across the document's most load-bearing sentences, for an ergonomic gain, at the exact moment
    the review record says transcription errors are the live failure mode. The one thing the
    dispatcher was genuinely buying — a single implementation of §7.5's `CookbookUnavailable` → 5
    rule — is kept as `cli.py::run()`, which every module routes through.
    **What is not claimed:** that the module form is *better*. It is the form this spec actually
    specifies in thirty places, and consistency with the tests, gates and tasks is worth more here
    than consistency with a sibling package. Increment 2, which adds `recon.py` and will want a
    sixth command, is the right place to reconsider — and if it does, the migration is a
    dispatcher that delegates to the same five handlers, with the module forms kept working.
    *Rev 6: round 5 was pointed at this item explicitly and raised no objection to it. The one
    thing it did find in this area is R5-W3 — that revision 5's proof of "no dispatcher exists"
    was a single behavioural probe weaker than its stated conclusion — which is now closed by
    §7.3(a)'s third static ban rather than by revisiting the choice recorded here.*
    *Rev 7: round 6 re-read this item while tracing C1 through `cli.py` and again raised no
    objection. Its finding was that `cli.py`'s **contents** — the exception roots — were declared
    in §7.1 and contradicted in five other sections, not that the no-dispatcher choice was wrong.
    The cost recorded here is unchanged; what changed is that `cli.py` now carries a §7.3(a) ban
    (it may import no sibling ingest module), so the one-way import direction that makes this
    design work is a lint rather than a comment.*
15. **The ten `FindingKind`s are not a partition of tokens, and two advisory tables overlap by
    design (rev 6, R5-S4).** A single `apis` token can produce findings of several kinds at once.
    Live today at `recipes.yml:432`: the bare IDENTs `sorted` and `use_channels` each yield one
    advisory `unknown_method` finding (`none.sorted`, `none.use_channels` — receiver
    `ReceiverType.NONE`, §3.2) **and** participate in the four advisory `param_candidate` findings
    that R4-W7's cross product produces against `lh.aspirate`/`lh.dispense`. §5.4 tabulates the
    line and states the rule at the point of use.
    **Why it is a limitation rather than a defect.** The `unknown_method` ranking is
    ORTHOGONAL-3's surface-expansion roadmap and the `param_candidate` table is a parameter-naming
    roadmap; the same identifier is a legitimate candidate for both readings, and de-duplicating
    would silently drop a real signal from one of the two tables — F5's exact prohibition. What is
    genuinely a cost: a reader summing rows across advisory tables will double-count tokens, and
    nothing in the reports flags the overlap per row.
    **What is *not* at risk.** Every live overlap is advisory-to-advisory. The four blocking kinds
    are mutually exclusive per subject by construction (§5.4 gives the four structural reasons), so
    `blocking_census.json` cannot double-count and §5.4.1's nine-finding derivation is unaffected.
    Increment 2, which will have recon-extracted call sites, is the right place to *rank* the two
    tables against each other — with evidence about which reading was correct — rather than to
    merge them here on a guess.
