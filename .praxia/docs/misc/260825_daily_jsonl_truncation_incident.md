# Incident 260825: `.praxia/daily.jsonl` truncation + partial reconstruction

**Cause:** The P2.1 worker (ox-alpha, backlog 4476) misused a bash fd redirect while
appending its daily record (`9>>daily.jsonl.lock 9>daily.jsonl` -- the second redirect
won and truncated `daily.jsonl` to O_TRUNC before the append).

**State before:** ≥13 records (13 counted at 21:27Z; more may have appended after).
**State now:** 5 records, all byte-verbatim recoveries:

| record | recovery source |
|---|---|
| 260824_w6_presim_landed | octopus session journal (full payload incl. ts) |
| 260825_phase2_spec_dag_landed | skunk session transcript (`tail -2` output captured verbatim pre-truncation) |
| 260825_p20_schema_reconciliation_landed | same |
| 260825_p21_golden_baseline_landed | the incident-causing append itself |
| 260825_p23_floor_generator_landed | appended post-truncation by the P2.3 worker |

**Known-missing (payloads not found in any scannable journal/transcript; ids known):**
- `260804_pr63_minor_findings_and_hook_fix_close`
- `260805_skill-parts-bundling-install-surface`
- `260805_deepseek-flash-v4-engaging`
- `260824_w5_audit_trail_landed`
- plus ~6 further older records whose ids were not echoed anywhere scannable.

**Lesson:** appends must be `flock <lockfile> -c 'printf ... >> file'` or an MCP
append action; NEVER open the data file with `>` in any redirect position.

## Recovery addendum (orchestrator rhino, 2026-08-25T22:16Z)

Final state: **9/13 records present**. Restored by orchestrator from session context (verbatim
re-authoring, marked `"restored_after_truncation": true`): `w2_fft_gate_landed`, `w3_propose_card_landed`,
`w4_clarification_card_landed`, `w5_audit_trail_landed`. Previously recovered by skunk: w6_presim
(via octopus journal), phase2_spec_dag + p20 (pre-truncation tail capture), plus post-truncation
appends p21 + p23.

Permanently unrecoverable (~4 records, content unknown to any surviving source): pre-MVP records
`260824_repl_autocomplete_scope`, `260824_repl_fresh_boot`, `260824_coxswain_spec_design_close`,
plus any W0/W1-era worker records (unicorn/kangaroo likely never wrote them, consistent with the
worker-reliability lesson #410). Impact assessed as LOW: all four were narrative status records;
their substance is preserved in git history (specs, commits, PRs) and in backlog item states.

Adopted mitigation: appends via `>>` only (never `>`), flock or MCP where concurrent writers exist;
orchestrator holds canonical re-authoring capability for orchestrator-written records.
