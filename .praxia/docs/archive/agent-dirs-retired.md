---
title: 'Legacy .agent directories retired (debt #1293)'
description: Manifest of the 740 files removed or relocated when the three legacy .agent/ directories were retired, with the git commit to restore them from
status: archived
task_id: 260922_debt-1293-docs-migration
archive: none (git history; see Restore)
created: '260922'
source: .agent/, praxis/.agent/, praxis/web-client/.agent/
restore_commit: e0869874af757828ae1be05b71c5e6ddd42de9dd
size_bytes: 12118813
---
# Legacy .agent directories retired (debt #1293)

The three pre-praxia agent-state directories — `.agent/` (725 tracked files),
`praxis/.agent/` (12) and `praxis/web-client/.agent/` (3) — were retired on 2026-09-22.
12 documents were relocated into `.praxia/docs/`; the other 728 files were removed.

## Why removal, and why no tarball

Measured by `scripts/docs/inventory_agent_dirs.py` at the restore commit:

- **Frozen since February 2026.** No file under any of the three roots was edited after
  2026-02-14; the only later commits touching them are the 2026-05-22 migration that
  moved 211 documents *out* (`.praxia/docs/migration-manifest.txt`). That migration was a
  clean move: 0 sources left behind, 0 destinations missing.
- **Nothing reads them.** No CI workflow, build step or product code referenced a
  `.agent/` path. The remaining references were historical docs (left as-is — they are
  records of their time), a handful of live docs (repointed in the same change), and the
  Jules-era scripts under `scripts/` that were already broken because the files they name
  moved out in May (tracked separately as debt #1292).
- **No duplicates to reconcile.** 0 files were byte-identical to anything under
  `.praxia/docs/` (empty files excluded).

The archive convention pairs a manifest with a `.tar.zst`. That is deliberately skipped
here: the full 12.1 MB tree is already in git history, and committing a compressed copy
would add megabytes to every clone permanently for no recoverability gain.

## Restore

```bash
# whole tree
git checkout e0869874af757828ae1be05b71c5e6ddd42de9dd -- .agent praxis/.agent praxis/web-client/.agent
# a single file
git show e0869874af757828ae1be05b71c5e6ddd42de9dd:.agent/<path> > <path>
```

## Relocated (12)

| From | To |
|---|---|
| `praxis/.agent/NEXT_ASSET_WIZARD_DECK_SELECTOR.md` | `plans/260209_asset-wizard-deck-selector.md` |
| `praxis/.agent/TECHNICAL_DEBT.md` | `audits/260209_web-client-technical-debt.md` |
| `praxis/.agent/PRAXIS_e2e_diffs.md` | `audits/260206_e2e-jules-session-review.md` |
| `praxis/.agent/praxis_e2e_diff_report.md` | `audits/260206_e2e-diff-report.md` |
| `praxis/.agent/audits/deep_audit_synthesis_feb2026.md` | `audits/260206_web-client-deep-audit-synthesis.md` |
| `praxis/.agent/audits/jules_1009855817323566566_core_services.md` | `audits/260206_jules-audit-core-services.md` |
| `praxis/.agent/audits/jules_1530702602442313801_resource_index.md` | `audits/260206_jules-audit-resource-index.md` |
| `praxis/.agent/audits/jules_17585661742425938948_core_components.md` | `audits/260206_jules-audit-core-components.md` |
| `praxis/.agent/audits/jules_5981630414686659482_run_protocol.md` | `audits/260206_jules-audit-run-protocol.md` |
| `praxis/.agent/audits/jules_6546155916196685132_asset_wizards.md` | `audits/260206_jules-audit-asset-wizards.md` |
| `praxis/web-client/.agent/plans/opfs-only-refactor.md` | `plans/260126_opfs-only-refactor.md` |
| `praxis/web-client/.agent/reports/deck_layout_coming_soon_investigation.md` | `research/260122_deck-layout-coming-soon-investigation.md` |

Dates are each file's first-add commit date.

## Removed, by top-level entry of `.agent/`

| Entry | Files | Of which `.md` | Last real edit | What it was |
|---|---:|---:|---|---|
| `skills/` | 200 | 96 | 2026-01-28 | Agent skill definitions from the pre-praxia tooling |
| `reports/` | 198 | 1 | 2026-02-06 | Jules diff captures and relative-import scan dumps |
| `staging/` | 113 | 113 | 2026-02-02 | Queued prompts for e2e enhancement, logic audits, ship prompts |
| `tasks/` | 83 | 74 | 2026-02-14 | Task tracking, handoffs and Jules batch records |
| `archive/` | 39 | 2 | 2026-01-28 | Already-archived agent state |
| `prompts/` | 20 | 20 | 2026-02-10 | Dated prompt batches |
| `agents/` | 14 | 14 | 2026-01-21 | Agent definitions |
| `backups/` | 13 | 0 | 2026-01-22 | State snapshots |
| `templates/` | 12 | 12 | 2026-01-21 | Workflow/skill templates |
| `workflows/` | 10 | 8 | 2026-01-22 | Workflow definitions |
| `scripts/` | 8 | 0 | 2026-01-31 | Utility scripts incl. a jules-diff-tool binary |
| other (15 entries) | 15 | 7 | ≤ 2026-02-14 | `README.md`, `orchestration.db`, `agent.db.bak_migration_004`, `schema.sql`, status JSON, single-file dirs |

`praxis/.agent/` and `praxis/web-client/.agent/` lost only their `.migrated` markers and a
stale `workspace.id` once the 12 documents above were relocated.

## Full path list (size in bytes, at the restore commit)

Generated with
`git ls-tree -r --format='%(objectsize) %(path)' e0869874 -- .agent praxis/.agent praxis/web-client/.agent`.
Includes the 12 relocated files at their old paths.

```text
124 .agent/AGENT_STATUS.json
3296 .agent/README.md
1290240 .agent/agent.db.bak_migration_004
5824 .agent/agent_tasks.jsonl
810 .agent/agents/README.md
3242 .agent/agents/deep-researcher.md
2840 .agent/agents/designer.md
16201 .agent/agents/evolving-orchestrator.md
2600 .agent/agents/explorer.md
2889 .agent/agents/fixer.md
725 .agent/agents/flash.md
796 .agent/agents/general.md
1021 .agent/agents/investigator.md
3374 .agent/agents/librarian.md
3097 .agent/agents/multimodal-looker.md
4046 .agent/agents/oracle.md
1611 .agent/agents/recon.md
2141 .agent/agents/summarize.md
0 .agent/archive/.gitkeep
646 .agent/archive/README.md
774587 .agent/archive/archive.tar.gz
2274 .agent/archive/staging_import/pull_diffs.py
206 .agent/archive/tasks-20260127/260125094518147_5d9b.meta.yaml
326 .agent/archive/tasks-20260127/260125094518147_5d9b.tar.zst
206 .agent/archive/tasks-20260127/260125094518766_069b.meta.yaml
326 .agent/archive/tasks-20260127/260125094518766_069b.tar.zst
206 .agent/archive/tasks-20260127/260125094519408_38be.meta.yaml
325 .agent/archive/tasks-20260127/260125094519408_38be.tar.zst
206 .agent/archive/tasks-20260127/260125094519428_9c5c.meta.yaml
325 .agent/archive/tasks-20260127/260125094519428_9c5c.tar.zst
206 .agent/archive/tasks-20260127/260125094535961_282a.meta.yaml
324 .agent/archive/tasks-20260127/260125094535961_282a.tar.zst
206 .agent/archive/tasks-20260127/260125094551425_02bb.meta.yaml
324 .agent/archive/tasks-20260127/260125094551425_02bb.tar.zst
206 .agent/archive/tasks-20260127/260125094552549_e371.meta.yaml
324 .agent/archive/tasks-20260127/260125094552549_e371.tar.zst
206 .agent/archive/tasks-20260127/260125094553573_198d.meta.yaml
326 .agent/archive/tasks-20260127/260125094553573_198d.tar.zst
206 .agent/archive/tasks-20260127/260125094554580_9818.meta.yaml
325 .agent/archive/tasks-20260127/260125094554580_9818.tar.zst
206 .agent/archive/tasks-20260127/260125094555747_08d7.meta.yaml
324 .agent/archive/tasks-20260127/260125094555747_08d7.tar.zst
206 .agent/archive/tasks-20260127/260125094556687_5c28.meta.yaml
325 .agent/archive/tasks-20260127/260125094556687_5c28.tar.zst
206 .agent/archive/tasks-20260127/260125094556725_5c7a.meta.yaml
326 .agent/archive/tasks-20260127/260125094556725_5c7a.tar.zst
206 .agent/archive/tasks-20260127/260125114936823_b8b0.meta.yaml
327 .agent/archive/tasks-20260127/260125114936823_b8b0.tar.zst
206 .agent/archive/tasks-20260127/260125114939246_cfea.meta.yaml
325 .agent/archive/tasks-20260127/260125114939246_cfea.tar.zst
206 .agent/archive/tasks-20260127/260125114941420_c0e8.meta.yaml
324 .agent/archive/tasks-20260127/260125114941420_c0e8.tar.zst
206 .agent/archive/tasks-20260127/260125114944430_8946.meta.yaml
325 .agent/archive/tasks-20260127/260125114944430_8946.tar.zst
206 .agent/archive/tasks-20260127/260125114944613_bfb8.meta.yaml
327 .agent/archive/tasks-20260127/260125114944613_bfb8.tar.zst
1020 .agent/archive/tasks-20260127/README.md
1019 .agent/backups/alembic_20260121/versions/3a1fe0851e06_make_resourceorm_resource_definition_.py
2261 .agent/backups/alembic_20260121/versions/577d92edf9a5_remove_unique_from_name.py
1028 .agent/backups/alembic_20260121/versions/a7f3e8c9d2b1_add_properties_json_to_resource_definition.py
1126 .agent/backups/alembic_20260121/versions/b8c4d5e6f7a2_add_deck_layout_path_to_protocol_defs.py
1615 .agent/backups/alembic_20260121/versions/bb6b6f27cedb_add_maintenance_and_location_columns.py
1212 .agent/backups/alembic_20260121/versions/c9d5e6f7a8b3_add_data_views_json_to_protocol_defs.py
3203 .agent/backups/alembic_20260121/versions/cd193888759e_add_dynamic_filter_columns_to_resource_.py
3769 .agent/backups/alembic_20260121/versions/d1e2f3a4b5c6_add_dimensions_to_resource_definitions.py
1994 .agent/backups/alembic_20260121/versions/e2f3a4b5c6d7_add_computation_graph_to_protocol_defs.py
2817 .agent/backups/alembic_20260121/versions/f3a4b5c6d7e8_add_simulation_cache_to_protocol_defs.py
2327 .agent/backups/alembic_20260121/versions/g4b5c6d7e8f9_add_bytecode_cache_to_protocol_defs.py
1653 .agent/backups/alembic_20260121/versions/h5c6d7e8f9a0_add_required_plr_category_to_assets.py
1229 .agent/backups/alembic_20260121/versions/i6d7e8f9g0h1_add_is_reusable_to_resource_definitions.py
691 .agent/codestyles/README.md
0 .agent/orchestration.db
634 .agent/pipelines/README.md
3149 .agent/prompts/260122_README.md
6067 .agent/prompts/260122_asset_wizard_visual_tweaks.md
9370 .agent/prompts/260122_e2e_test_infrastructure.md
8015 .agent/prompts/260122_global_module_shimming.md
7595 .agent/prompts/260122_hid_shim_implementation.md
4800 .agent/prompts/260122_post_merge_cleanup.md
7069 .agent/prompts/260122_protocol_runner_visual_tweaks.md
7200 .agent/prompts/260122_socket_shim_research.md
7267 .agent/prompts/260122_theme_css_variable_fixes.md
648 .agent/prompts/README.md
2000 .agent/prompts/audit-hardcoded-logic.md
2121 .agent/prompts/debug_browser_mode.md
7719 .agent/prompts/fix-deck-serialization-fqn.md
2250 .agent/prompts/maintenance_audit.md
11977 .agent/prompts/orchestrator_v01alpha_merge.md
3950 .agent/prompts/protocol-wizard-e2e-fix.md
621 .agent/prompts/reuse/README.md
4944 .agent/prompts/reuse/e2e_debug_dispatch.md
3751 .agent/prompts/reuse/p2_status_recon.md
2321 .agent/prompts/reuse/technical_debt_migration.md
658 .agent/references/README.md
577 .agent/reports/README.md
32 .agent/reports/jules_diffs/2026-01-21/10483287677521851158/changes.diff
0 .agent/reports/jules_diffs/2026-01-21/10483287677521851158/files_changed.txt
255 .agent/reports/jules_diffs/2026-01-21/10483287677521851158/metadata.json
32 .agent/reports/jules_diffs/2026-01-21/10938895789890151081/changes.diff
0 .agent/reports/jules_diffs/2026-01-21/10938895789890151081/files_changed.txt
254 .agent/reports/jules_diffs/2026-01-21/10938895789890151081/metadata.json
148 .agent/reports/jules_diffs/2026-01-21/10964805792793165164/changes.diff
43 .agent/reports/jules_diffs/2026-01-21/10964805792793165164/files_changed.txt
254 .agent/reports/jules_diffs/2026-01-21/10964805792793165164/metadata.json
9002 .agent/reports/jules_diffs/2026-01-21/11789340521090048069/changes.diff
51 .agent/reports/jules_diffs/2026-01-21/11789340521090048069/files_changed.txt
255 .agent/reports/jules_diffs/2026-01-21/11789340521090048069/metadata.json
312035 .agent/reports/jules_diffs/2026-01-21/11930790793989115694/changes.diff
264 .agent/reports/jules_diffs/2026-01-21/11930790793989115694/files_changed.txt
250 .agent/reports/jules_diffs/2026-01-21/11930790793989115694/metadata.json
11313 .agent/reports/jules_diffs/2026-01-21/12408408457884280509/changes.diff
258 .agent/reports/jules_diffs/2026-01-21/12408408457884280509/files_changed.txt
261 .agent/reports/jules_diffs/2026-01-21/12408408457884280509/metadata.json
6663 .agent/reports/jules_diffs/2026-01-21/12822272099245934316/changes.diff
509 .agent/reports/jules_diffs/2026-01-21/12822272099245934316/files_changed.txt
260 .agent/reports/jules_diffs/2026-01-21/12822272099245934316/metadata.json
32 .agent/reports/jules_diffs/2026-01-21/13760860730235187004/changes.diff
0 .agent/reports/jules_diffs/2026-01-21/13760860730235187004/files_changed.txt
253 .agent/reports/jules_diffs/2026-01-21/13760860730235187004/metadata.json
32 .agent/reports/jules_diffs/2026-01-21/13802381057024659934/changes.diff
0 .agent/reports/jules_diffs/2026-01-21/13802381057024659934/files_changed.txt
260 .agent/reports/jules_diffs/2026-01-21/13802381057024659934/metadata.json
32 .agent/reports/jules_diffs/2026-01-21/13893348567367483591/changes.diff
0 .agent/reports/jules_diffs/2026-01-21/13893348567367483591/files_changed.txt
261 .agent/reports/jules_diffs/2026-01-21/13893348567367483591/metadata.json
32 .agent/reports/jules_diffs/2026-01-21/14024454940343644634/changes.diff
0 .agent/reports/jules_diffs/2026-01-21/14024454940343644634/files_changed.txt
254 .agent/reports/jules_diffs/2026-01-21/14024454940343644634/metadata.json
10010 .agent/reports/jules_diffs/2026-01-21/14904239789534326926/changes.diff
311 .agent/reports/jules_diffs/2026-01-21/14904239789534326926/files_changed.txt
259 .agent/reports/jules_diffs/2026-01-21/14904239789534326926/metadata.json
37543 .agent/reports/jules_diffs/2026-01-21/15023855711672891138/changes.diff
537 .agent/reports/jules_diffs/2026-01-21/15023855711672891138/files_changed.txt
249 .agent/reports/jules_diffs/2026-01-21/15023855711672891138/metadata.json
3098 .agent/reports/jules_diffs/2026-01-21/15033366457735355048/changes.diff
28 .agent/reports/jules_diffs/2026-01-21/15033366457735355048/files_changed.txt
255 .agent/reports/jules_diffs/2026-01-21/15033366457735355048/metadata.json
72252 .agent/reports/jules_diffs/2026-01-21/15718507772184055229/changes.diff
3919 .agent/reports/jules_diffs/2026-01-21/15718507772184055229/files_changed.txt
256 .agent/reports/jules_diffs/2026-01-21/15718507772184055229/metadata.json
6676 .agent/reports/jules_diffs/2026-01-21/16235462376134233538/changes.diff
69 .agent/reports/jules_diffs/2026-01-21/16235462376134233538/files_changed.txt
250 .agent/reports/jules_diffs/2026-01-21/16235462376134233538/metadata.json
2500 .agent/reports/jules_diffs/2026-01-21/16249831400007417250/changes.diff
35 .agent/reports/jules_diffs/2026-01-21/16249831400007417250/files_changed.txt
255 .agent/reports/jules_diffs/2026-01-21/16249831400007417250/metadata.json
14115 .agent/reports/jules_diffs/2026-01-21/16296747416823548932/changes.diff
32 .agent/reports/jules_diffs/2026-01-21/16860548828576640323/changes.diff
0 .agent/reports/jules_diffs/2026-01-21/16860548828576640323/files_changed.txt
249 .agent/reports/jules_diffs/2026-01-21/16860548828576640323/metadata.json
7585 .agent/reports/jules_diffs/2026-01-21/17486039806276221924/changes.diff
361 .agent/reports/jules_diffs/2026-01-21/17486039806276221924/files_changed.txt
254 .agent/reports/jules_diffs/2026-01-21/17486039806276221924/metadata.json
4233 .agent/reports/jules_diffs/2026-01-21/17528057938872959418/changes.diff
46 .agent/reports/jules_diffs/2026-01-21/17528057938872959418/files_changed.txt
254 .agent/reports/jules_diffs/2026-01-21/17528057938872959418/metadata.json
660 .agent/reports/jules_diffs/2026-01-21/18100194563593856842/changes.diff
60 .agent/reports/jules_diffs/2026-01-21/18100194563593856842/files_changed.txt
254 .agent/reports/jules_diffs/2026-01-21/18100194563593856842/metadata.json
5889 .agent/reports/jules_diffs/2026-01-21/18333554910223635761/changes.diff
41 .agent/reports/jules_diffs/2026-01-21/18333554910223635761/files_changed.txt
261 .agent/reports/jules_diffs/2026-01-21/18333554910223635761/metadata.json
24244 .agent/reports/jules_diffs/2026-01-21/1955602947950537137/changes.diff
479 .agent/reports/jules_diffs/2026-01-21/1955602947950537137/files_changed.txt
250 .agent/reports/jules_diffs/2026-01-21/1955602947950537137/metadata.json
32 .agent/reports/jules_diffs/2026-01-21/2150549182649969367/changes.diff
0 .agent/reports/jules_diffs/2026-01-21/2150549182649969367/files_changed.txt
254 .agent/reports/jules_diffs/2026-01-21/2150549182649969367/metadata.json
32 .agent/reports/jules_diffs/2026-01-21/2352208636936553446/changes.diff
0 .agent/reports/jules_diffs/2026-01-21/2352208636936553446/files_changed.txt
260 .agent/reports/jules_diffs/2026-01-21/2352208636936553446/metadata.json
1338 .agent/reports/jules_diffs/2026-01-21/2357822123779432063/changes.diff
82 .agent/reports/jules_diffs/2026-01-21/2357822123779432063/files_changed.txt
254 .agent/reports/jules_diffs/2026-01-21/2357822123779432063/metadata.json
1553 .agent/reports/jules_diffs/2026-01-21/2675599457561484882/changes.diff
100 .agent/reports/jules_diffs/2026-01-21/2675599457561484882/files_changed.txt
249 .agent/reports/jules_diffs/2026-01-21/2675599457561484882/metadata.json
7021 .agent/reports/jules_diffs/2026-01-21/2946937954468200048/changes.diff
43 .agent/reports/jules_diffs/2026-01-21/2946937954468200048/files_changed.txt
254 .agent/reports/jules_diffs/2026-01-21/2946937954468200048/metadata.json
32 .agent/reports/jules_diffs/2026-01-21/29526032146778939/changes.diff
0 .agent/reports/jules_diffs/2026-01-21/29526032146778939/files_changed.txt
252 .agent/reports/jules_diffs/2026-01-21/29526032146778939/metadata.json
32 .agent/reports/jules_diffs/2026-01-21/3920824328944630087/changes.diff
0 .agent/reports/jules_diffs/2026-01-21/3920824328944630087/files_changed.txt
251 .agent/reports/jules_diffs/2026-01-21/3920824328944630087/metadata.json
32 .agent/reports/jules_diffs/2026-01-21/3994047421780513620/changes.diff
0 .agent/reports/jules_diffs/2026-01-21/3994047421780513620/files_changed.txt
258 .agent/reports/jules_diffs/2026-01-21/3994047421780513620/metadata.json
8970 .agent/reports/jules_diffs/2026-01-21/4091292972154822687/changes.diff
40 .agent/reports/jules_diffs/2026-01-21/4091292972154822687/files_changed.txt
254 .agent/reports/jules_diffs/2026-01-21/4091292972154822687/metadata.json
32 .agent/reports/jules_diffs/2026-01-21/4496427643100343804/changes.diff
0 .agent/reports/jules_diffs/2026-01-21/4496427643100343804/files_changed.txt
249 .agent/reports/jules_diffs/2026-01-21/4496427643100343804/metadata.json
32 .agent/reports/jules_diffs/2026-01-21/4745104234560472030/changes.diff
0 .agent/reports/jules_diffs/2026-01-21/4745104234560472030/files_changed.txt
249 .agent/reports/jules_diffs/2026-01-21/4745104234560472030/metadata.json
8568 .agent/reports/jules_diffs/2026-01-21/4768660011143247829/changes.diff
32 .agent/reports/jules_diffs/2026-01-21/5073788627851519008/changes.diff
0 .agent/reports/jules_diffs/2026-01-21/5073788627851519008/files_changed.txt
249 .agent/reports/jules_diffs/2026-01-21/5073788627851519008/metadata.json
32 .agent/reports/jules_diffs/2026-01-21/5218047969328236860/changes.diff
0 .agent/reports/jules_diffs/2026-01-21/5218047969328236860/files_changed.txt
254 .agent/reports/jules_diffs/2026-01-21/5218047969328236860/metadata.json
7664 .agent/reports/jules_diffs/2026-01-21/5758405153110470721/changes.diff
90 .agent/reports/jules_diffs/2026-01-21/5758405153110470721/files_changed.txt
254 .agent/reports/jules_diffs/2026-01-21/5758405153110470721/metadata.json
15801 .agent/reports/jules_diffs/2026-01-21/5772657439955006749/changes.diff
334 .agent/reports/jules_diffs/2026-01-21/5772657439955006749/files_changed.txt
254 .agent/reports/jules_diffs/2026-01-21/5772657439955006749/metadata.json
32 .agent/reports/jules_diffs/2026-01-21/6083657042709549087/changes.diff
0 .agent/reports/jules_diffs/2026-01-21/6083657042709549087/files_changed.txt
251 .agent/reports/jules_diffs/2026-01-21/6083657042709549087/metadata.json
10902 .agent/reports/jules_diffs/2026-01-21/6138709097205002465/changes.diff
7207 .agent/reports/jules_diffs/2026-01-21/693011006660131583/changes.diff
43 .agent/reports/jules_diffs/2026-01-21/693011006660131583/files_changed.txt
252 .agent/reports/jules_diffs/2026-01-21/693011006660131583/metadata.json
3711 .agent/reports/jules_diffs/2026-01-21/7169150082809541249/changes.diff
264 .agent/reports/jules_diffs/2026-01-21/7169150082809541249/files_changed.txt
254 .agent/reports/jules_diffs/2026-01-21/7169150082809541249/metadata.json
5305 .agent/reports/jules_diffs/2026-01-21/7588975548984364060/changes.diff
162 .agent/reports/jules_diffs/2026-01-21/7588975548984364060/files_changed.txt
259 .agent/reports/jules_diffs/2026-01-21/7588975548984364060/metadata.json
1553 .agent/reports/jules_diffs/2026-01-21/7833557422181935314/changes.diff
100 .agent/reports/jules_diffs/2026-01-21/7833557422181935314/files_changed.txt
253 .agent/reports/jules_diffs/2026-01-21/7833557422181935314/metadata.json
15238 .agent/reports/jules_diffs/2026-01-21/7966319430585451351/changes.diff
567 .agent/reports/jules_diffs/2026-01-21/7966319430585451351/files_changed.txt
260 .agent/reports/jules_diffs/2026-01-21/7966319430585451351/metadata.json
3337 .agent/reports/jules_diffs/2026-01-21/8053431069385739941/changes.diff
69 .agent/reports/jules_diffs/2026-01-21/8053431069385739941/files_changed.txt
254 .agent/reports/jules_diffs/2026-01-21/8053431069385739941/metadata.json
32 .agent/reports/jules_diffs/2026-01-21/8837045210417322035/changes.diff
0 .agent/reports/jules_diffs/2026-01-21/8837045210417322035/files_changed.txt
249 .agent/reports/jules_diffs/2026-01-21/8837045210417322035/metadata.json
6407 .agent/reports/jules_diffs/2026-01-21/9326114167496894643/changes.diff
349 .agent/reports/jules_diffs/2026-01-21/9326114167496894643/files_changed.txt
254 .agent/reports/jules_diffs/2026-01-21/9326114167496894643/metadata.json
16567 .agent/reports/jules_diffs/2026-01-21/954639313672326160/changes.diff
40 .agent/reports/jules_diffs/2026-01-21/954639313672326160/files_changed.txt
252 .agent/reports/jules_diffs/2026-01-21/954639313672326160/metadata.json
7971 .agent/reports/jules_diffs/2026-01-21/9570037443858871469/changes.diff
343 .agent/reports/jules_diffs/2026-01-21/9570037443858871469/files_changed.txt
254 .agent/reports/jules_diffs/2026-01-21/9570037443858871469/metadata.json
28927 .agent/reports/jules_diffs/2026-01-21/9868075249617187364/changes.diff
405 .agent/reports/jules_diffs/2026-01-21/9868075249617187364/files_changed.txt
255 .agent/reports/jules_diffs/2026-01-21/9868075249617187364/metadata.json
3110 .agent/reports/jules_diffs/2026-01-22/11364460311257606943/changes.diff
3110 .agent/reports/jules_diffs/2026-01-22/11364460311257606943/raw_output.txt
4814 .agent/reports/jules_diffs/2026-01-22/12202006395604566414/changes.diff
4814 .agent/reports/jules_diffs/2026-01-22/12202006395604566414/raw_output.txt
4476 .agent/reports/jules_diffs/2026-01-22/13801416353033225445/changes.diff
4476 .agent/reports/jules_diffs/2026-01-22/13801416353033225445/raw_output.txt
5179 .agent/reports/jules_diffs/2026-01-22/13875284861708851694/changes.diff
5179 .agent/reports/jules_diffs/2026-01-22/13875284861708851694/raw_output.txt
3400 .agent/reports/jules_diffs/2026-01-22/14157233637746204824/changes.diff
3400 .agent/reports/jules_diffs/2026-01-22/14157233637746204824/raw_output.txt
9459 .agent/reports/jules_diffs/2026-01-22/1421832921288010966/changes.diff
9459 .agent/reports/jules_diffs/2026-01-22/1421832921288010966/raw_output.txt
3692 .agent/reports/jules_diffs/2026-01-22/17185742660119923694/changes.diff
3692 .agent/reports/jules_diffs/2026-01-22/17185742660119923694/raw_output.txt
6389 .agent/reports/jules_diffs/2026-01-22/18200110524437531926/changes.diff
6389 .agent/reports/jules_diffs/2026-01-22/18200110524437531926/raw_output.txt
4674 .agent/reports/jules_diffs/2026-01-22/2180090074346146281/changes.diff
4674 .agent/reports/jules_diffs/2026-01-22/2180090074346146281/raw_output.txt
6545 .agent/reports/jules_diffs/2026-01-22/2274271914765365175/changes.diff
6545 .agent/reports/jules_diffs/2026-01-22/2274271914765365175/raw_output.txt
950139 .agent/reports/jules_diffs/2026-01-22/2750859863697615554/raw_output.txt
1939 .agent/reports/jules_diffs/2026-01-22/3116099432068743856/changes.diff
1939 .agent/reports/jules_diffs/2026-01-22/3116099432068743856/raw_output.txt
1292 .agent/reports/jules_diffs/2026-01-22/3265714357744918783/changes.diff
1292 .agent/reports/jules_diffs/2026-01-22/3265714357744918783/raw_output.txt
3798 .agent/reports/jules_diffs/2026-01-22/5089217727615940047/changes.diff
3798 .agent/reports/jules_diffs/2026-01-22/5089217727615940047/raw_output.txt
3063 .agent/reports/jules_diffs/2026-01-22/590734515303937167/changes.diff
3063 .agent/reports/jules_diffs/2026-01-22/590734515303937167/raw_output.txt
4887 .agent/reports/jules_diffs/2026-01-22/7247940119796904212/changes.diff
4887 .agent/reports/jules_diffs/2026-01-22/7247940119796904212/raw_output.txt
13243 .agent/reports/jules_diffs/2026-01-22/8242565057258051122/changes.diff
13243 .agent/reports/jules_diffs/2026-01-22/8242565057258051122/raw_output.txt
4524 .agent/reports/jules_diffs/2026-01-22/8685341774290011585/changes.diff
4524 .agent/reports/jules_diffs/2026-01-22/8685341774290011585/raw_output.txt
0 .agent/reports/relative_html_paths.txt
85160 .agent/reports/relative_imports_1.txt
37256 .agent/reports/relative_imports_2.txt
19701 .agent/reports/relative_imports_3.txt
7644 .agent/reports/relative_imports_4.txt
447 .agent/reports/relative_imports_5.txt
0 .agent/reports/relative_imports_6.txt
0 .agent/reports/relative_scss_paths.txt
0 .agent/reports/relative_ts_paths.txt
647 .agent/research/README.md
5115 .agent/roles/oracle.md
11066 .agent/schema.sql
1623 .agent/schemas/oracle_critique.json
3254 .agent/scripts/analyze_diffs.py
3991 .agent/scripts/dispatch-jules-e2e.sh
0 .agent/scripts/jules-diff-tool/.!78914!jules-diff-tool
32 .agent/scripts/jules-diff-tool/go.mod
3346098 .agent/scripts/jules-diff-tool/jules-diff-tool
6202 .agent/scripts/jules-diff-tool/main.go
3114 .agent/scripts/submit_jules.py
1316 .agent/scripts/submit_jules_dispatches.sh
1814 .agent/skills/atomic-git-commit/SKILL.md
8159 .agent/skills/backend-dev-guidelines/SKILL.md
12866 .agent/skills/backend-dev-guidelines/resources/architecture-overview.md
6862 .agent/skills/backend-dev-guidelines/resources/async-and-errors.md
16478 .agent/skills/backend-dev-guidelines/resources/complete-examples.md
5816 .agent/skills/backend-dev-guidelines/resources/configuration.md
4937 .agent/skills/backend-dev-guidelines/resources/database-patterns.md
5169 .agent/skills/backend-dev-guidelines/resources/middleware-guide.md
19930 .agent/skills/backend-dev-guidelines/resources/routing-and-controllers.md
7753 .agent/skills/backend-dev-guidelines/resources/sentry-and-monitoring.md
22299 .agent/skills/backend-dev-guidelines/resources/services-and-repositories.md
5420 .agent/skills/backend-dev-guidelines/resources/testing-guide.md
18038 .agent/skills/backend-dev-guidelines/resources/validation-patterns.md
10174 .agent/skills/frontend-design/LICENSE.txt
4440 .agent/skills/frontend-design/SKILL.md
1086 .agent/skills/git-pushing/SKILL.md
374 .agent/skills/git-pushing/scripts/smart_commit.sh
2553 .agent/skills/jules-remote/INTEGRATION_LOG.md
4054 .agent/skills/jules-remote/SKILL.md
1952 .agent/skills/loki-mode/.github/workflows/claude-code-review.yml
1886 .agent/skills/loki-mode/.github/workflows/claude.yml
4925 .agent/skills/loki-mode/.github/workflows/release.yml
10 .agent/skills/loki-mode/.gitignore
12091 .agent/skills/loki-mode/ACKNOWLEDGEMENTS.md
85919 .agent/skills/loki-mode/CHANGELOG.md
4353 .agent/skills/loki-mode/CLAUDE.md
6622 .agent/skills/loki-mode/CONTEXT-EXPORT.md
9279 .agent/skills/loki-mode/INSTALLATION.md
1079 .agent/skills/loki-mode/LICENSE
18608 .agent/skills/loki-mode/README.md
28553 .agent/skills/loki-mode/SKILL.md
7 .agent/skills/loki-mode/VERSION
15612 .agent/skills/loki-mode/autonomy/.loki/dashboard/index.html
10432 .agent/skills/loki-mode/autonomy/CONSTITUTION.md
7665 .agent/skills/loki-mode/autonomy/README.md
76136 .agent/skills/loki-mode/autonomy/run.sh
3075 .agent/skills/loki-mode/demo/README.md
1341081 .agent/skills/loki-mode/demo/loki-demo.gif
2074 .agent/skills/loki-mode/demo/record-demo.sh
5922 .agent/skills/loki-mode/demo/record-full-demo.sh
9465 .agent/skills/loki-mode/demo/recordings/loki-demo.cast
6541 .agent/skills/loki-mode/demo/run-demo-auto.sh
7758 .agent/skills/loki-mode/demo/run-demo.sh
3347 .agent/skills/loki-mode/demo/vhs-tape.tape
6541 .agent/skills/loki-mode/demo/voice-over-script.md
11897 .agent/skills/loki-mode/docs/COMPETITIVE-ANALYSIS.md
4024 .agent/skills/loki-mode/docs/screenshots/README.md
70209 .agent/skills/loki-mode/docs/screenshots/dashboard-agents.png
54428 .agent/skills/loki-mode/docs/screenshots/dashboard-tasks.png
1809 .agent/skills/loki-mode/examples/api-only.md
2901 .agent/skills/loki-mode/examples/full-stack-demo.md
1439 .agent/skills/loki-mode/examples/simple-todo-app.md
1775 .agent/skills/loki-mode/examples/static-landing-page.md
1794 .agent/skills/loki-mode/examples/todo-app-generated/.loki/CONTINUITY.md
13 .agent/skills/loki-mode/examples/todo-app-generated/.loki/queue/completed.json
13 .agent/skills/loki-mode/examples/todo-app-generated/.loki/queue/dead-letter.json
13 .agent/skills/loki-mode/examples/todo-app-generated/.loki/queue/failed.json
13 .agent/skills/loki-mode/examples/todo-app-generated/.loki/queue/in-progress.json
10631 .agent/skills/loki-mode/examples/todo-app-generated/.loki/queue/pending.json
999 .agent/skills/loki-mode/examples/todo-app-generated/.loki/state/orchestrator.json
21593 .agent/skills/loki-mode/examples/todo-app-generated/E2E_VERIFICATION_REPORT.md
1439 .agent/skills/loki-mode/examples/todo-app-generated/PRD.md
7157 .agent/skills/loki-mode/examples/todo-app-generated/TASK_018_COMPLETION.md
8789 .agent/skills/loki-mode/examples/todo-app-generated/TESTING_DOCUMENTATION.md
6080 .agent/skills/loki-mode/examples/todo-app-generated/TEST_REPORT.md
10860 .agent/skills/loki-mode/examples/todo-app-generated/VERIFICATION_SUMMARY.txt
30 .agent/skills/loki-mode/examples/todo-app-generated/backend/.gitignore
97562 .agent/skills/loki-mode/examples/todo-app-generated/backend/package-lock.json
629 .agent/skills/loki-mode/examples/todo-app-generated/backend/package.json
543 .agent/skills/loki-mode/examples/todo-app-generated/backend/src/db/database.ts
863 .agent/skills/loki-mode/examples/todo-app-generated/backend/src/db/db.ts
123 .agent/skills/loki-mode/examples/todo-app-generated/backend/src/db/index.ts
734 .agent/skills/loki-mode/examples/todo-app-generated/backend/src/db/migrations.ts
187 .agent/skills/loki-mode/examples/todo-app-generated/backend/src/db/schema.sql
1011 .agent/skills/loki-mode/examples/todo-app-generated/backend/src/index.ts
4244 .agent/skills/loki-mode/examples/todo-app-generated/backend/src/routes/todos.ts
594 .agent/skills/loki-mode/examples/todo-app-generated/backend/src/types/index.ts
32768 .agent/skills/loki-mode/examples/todo-app-generated/backend/todos.db-shm
45352 .agent/skills/loki-mode/examples/todo-app-generated/backend/todos.db-wal
795 .agent/skills/loki-mode/examples/todo-app-generated/backend/tsconfig.json
253 .agent/skills/loki-mode/examples/todo-app-generated/frontend/.gitignore
357 .agent/skills/loki-mode/examples/todo-app-generated/frontend/index.html
66765 .agent/skills/loki-mode/examples/todo-app-generated/frontend/package-lock.json
540 .agent/skills/loki-mode/examples/todo-app-generated/frontend/package.json
6112 .agent/skills/loki-mode/examples/todo-app-generated/frontend/src/App.css
1889 .agent/skills/loki-mode/examples/todo-app-generated/frontend/src/App.tsx
1354 .agent/skills/loki-mode/examples/todo-app-generated/frontend/src/api/todos.ts
683 .agent/skills/loki-mode/examples/todo-app-generated/frontend/src/components/ConfirmDialog.tsx
229 .agent/skills/loki-mode/examples/todo-app-generated/frontend/src/components/EmptyState.tsx
1117 .agent/skills/loki-mode/examples/todo-app-generated/frontend/src/components/TodoForm.tsx
847 .agent/skills/loki-mode/examples/todo-app-generated/frontend/src/components/TodoItem.tsx
569 .agent/skills/loki-mode/examples/todo-app-generated/frontend/src/components/TodoList.tsx
1924 .agent/skills/loki-mode/examples/todo-app-generated/frontend/src/hooks/useTodos.ts
732 .agent/skills/loki-mode/examples/todo-app-generated/frontend/src/index.css
236 .agent/skills/loki-mode/examples/todo-app-generated/frontend/src/main.tsx
38 .agent/skills/loki-mode/examples/todo-app-generated/frontend/src/vite-env.d.ts
552 .agent/skills/loki-mode/examples/todo-app-generated/frontend/tsconfig.json
213 .agent/skills/loki-mode/examples/todo-app-generated/frontend/tsconfig.node.json
276 .agent/skills/loki-mode/examples/todo-app-generated/frontend/vite.config.ts
5391 .agent/skills/loki-mode/integrations/vibe-kanban.md
15136 .agent/skills/loki-mode/references/advanced-patterns.md
7772 .agent/skills/loki-mode/references/agent-types.md
23078 .agent/skills/loki-mode/references/agents.md
11801 .agent/skills/loki-mode/references/business-ops.md
9384 .agent/skills/loki-mode/references/core-workflow.md
14020 .agent/skills/loki-mode/references/deployment.md
17564 .agent/skills/loki-mode/references/lab-research-patterns.md
12977 .agent/skills/loki-mode/references/memory-system.md
17153 .agent/skills/loki-mode/references/openai-patterns.md
15417 .agent/skills/loki-mode/references/production-patterns.md
13263 .agent/skills/loki-mode/references/quality-control.md
9496 .agent/skills/loki-mode/references/sdlc-phases.md
9145 .agent/skills/loki-mode/references/task-queue.md
22271 .agent/skills/loki-mode/references/tool-orchestration.md
5168 .agent/skills/loki-mode/scripts/export-to-vibe-kanban.sh
8345 .agent/skills/loki-mode/scripts/loki-wrapper.sh
1831 .agent/skills/loki-mode/scripts/take-screenshots.js
4055 .agent/skills/loki-mode/tests/run-all-tests.sh
9138 .agent/skills/loki-mode/tests/test-agent-timeout.sh
5446 .agent/skills/loki-mode/tests/test-bootstrap.sh
9953 .agent/skills/loki-mode/tests/test-circuit-breaker.sh
10902 .agent/skills/loki-mode/tests/test-state-recovery.sh
10109 .agent/skills/loki-mode/tests/test-task-queue.sh
8606 .agent/skills/loki-mode/tests/test-wrapper.sh
6649 .agent/skills/multi-stage-workflow/SKILL.md
3271 .agent/skills/playwright-skill/.temp-execution-1769456140350.js
16366 .agent/skills/playwright-skill/API_REFERENCE.md
13930 .agent/skills/playwright-skill/SKILL.md
652 .agent/skills/playwright-skill/package.json
5788 .agent/skills/playwright-skill/run.js
5659 .agent/skills/prompt-engineering/SKILL.md
4654 .agent/skills/senior-architect/SKILL.md
1618 .agent/skills/senior-architect/references/architecture_patterns.md
1620 .agent/skills/senior-architect/references/system_design_workflows.md
1616 .agent/skills/senior-architect/references/tech_decision_guide.md
3199 .agent/skills/senior-architect/scripts/architecture_diagram_generator.py
3146 .agent/skills/senior-architect/scripts/dependency_analyzer.py
3136 .agent/skills/senior-architect/scripts/project_architect.py
4495 .agent/skills/senior-fullstack/SKILL.md
1618 .agent/skills/senior-fullstack/references/architecture_patterns.md
1618 .agent/skills/senior-fullstack/references/development_workflows.md
1613 .agent/skills/senior-fullstack/references/tech_stack_guide.md
3154 .agent/skills/senior-fullstack/scripts/code_quality_analyzer.py
3151 .agent/skills/senior-fullstack/scripts/fullstack_scaffolder.py
3141 .agent/skills/senior-fullstack/scripts/project_scaffolder.py
4268 .agent/skills/systematic-debugging/CREATION-LOG.md
9884 .agent/skills/systematic-debugging/SKILL.md
5054 .agent/skills/systematic-debugging/condition-based-waiting-example.ts
3516 .agent/skills/systematic-debugging/condition-based-waiting.md
3650 .agent/skills/systematic-debugging/defense-in-depth.md
1528 .agent/skills/systematic-debugging/find-polluter.sh
5327 .agent/skills/systematic-debugging/root-cause-tracing.md
653 .agent/skills/systematic-debugging/test-academic.md
1900 .agent/skills/systematic-debugging/test-pressure-1.md
2283 .agent/skills/systematic-debugging/test-pressure-2.md
2692 .agent/skills/systematic-debugging/test-pressure-3.md
9867 .agent/skills/test-driven-development/SKILL.md
8251 .agent/skills/test-driven-development/testing-anti-patterns.md
2974 .agent/skills/test-fixing/SKILL.md
11357 .agent/skills/theme-factory/LICENSE.txt
3124 .agent/skills/theme-factory/SKILL.md
124310 .agent/skills/theme-factory/theme-showcase.pdf
544 .agent/skills/theme-factory/themes/arctic-frost.md
519 .agent/skills/theme-factory/themes/botanical-garden.md
496 .agent/skills/theme-factory/themes/desert-rose.md
506 .agent/skills/theme-factory/themes/forest-canopy.md
528 .agent/skills/theme-factory/themes/golden-hour.md
513 .agent/skills/theme-factory/themes/midnight-galaxy.md
549 .agent/skills/theme-factory/themes/modern-minimalist.md
555 .agent/skills/theme-factory/themes/ocean-depths.md
558 .agent/skills/theme-factory/themes/sunset-boulevard.md
547 .agent/skills/theme-factory/themes/tech-innovation.md
9011 .agent/skills/ui-ux-pro-max/SKILL.md
7655 .agent/skills/ui-ux-pro-max/data/charts.csv
12927 .agent/skills/ui-ux-pro-max/data/colors.csv
14342 .agent/skills/ui-ux-pro-max/data/landing.csv
29694 .agent/skills/ui-ux-pro-max/data/products.csv
17401 .agent/skills/ui-ux-pro-max/data/prompts.csv
10416 .agent/skills/ui-ux-pro-max/data/stacks/flutter.csv
11305 .agent/skills/ui-ux-pro-max/data/stacks/html-tailwind.csv
12493 .agent/skills/ui-ux-pro-max/data/stacks/nextjs.csv
14010 .agent/skills/ui-ux-pro-max/data/stacks/nuxt-ui.csv
16539 .agent/skills/ui-ux-pro-max/data/stacks/nuxtjs.csv
9983 .agent/skills/ui-ux-pro-max/data/stacks/react-native.csv
12962 .agent/skills/ui-ux-pro-max/data/stacks/react.csv
11009 .agent/skills/ui-ux-pro-max/data/stacks/svelte.csv
10821 .agent/skills/ui-ux-pro-max/data/stacks/swiftui.csv
11006 .agent/skills/ui-ux-pro-max/data/stacks/vue.csv
40912 .agent/skills/ui-ux-pro-max/data/styles.csv
31878 .agent/skills/ui-ux-pro-max/data/typography.csv
18667 .agent/skills/ui-ux-pro-max/data/ux-guidelines.csv
9111 .agent/skills/ui-ux-pro-max/scripts/core.py
2333 .agent/skills/ui-ux-pro-max/scripts/search.py
5592 .agent/skills/using-git-worktrees/SKILL.md
4201 .agent/skills/verification-before-completion/SKILL.md
1183 .agent/skills/web-design-guidelines/SKILL.md
11357 .agent/skills/webapp-testing/LICENSE.txt
3913 .agent/skills/webapp-testing/SKILL.md
3693 .agent/skills/webapp-testing/scripts/with_server.py
3264 .agent/skills/writing-plans/SKILL.md
569 .agent/stack-config.yaml
7345 .agent/staging/e2e_enhancement/01-execution-controls-improvement-plan.md
8615 .agent/staging/e2e_enhancement/01-execution-controls-report.md
7348 .agent/staging/e2e_enhancement/01-onboarding-improvement-plan.md
8176 .agent/staging/e2e_enhancement/01-onboarding-report.md
13681 .agent/staging/e2e_enhancement/02-asset-management-improvement-plan.md
17762 .agent/staging/e2e_enhancement/02-asset-management-report.md
8859 .agent/staging/e2e_enhancement/03-protocol-execution-improvement-plan.md
16236 .agent/staging/e2e_enhancement/03-protocol-execution-report.md
10293 .agent/staging/e2e_enhancement/04-browser-persistence-improvement-plan.md
10346 .agent/staging/e2e_enhancement/04-browser-persistence-report.md
736 .agent/staging/e2e_enhancement/COMMAND_RULES.md
949 .agent/staging/e2e_enhancement/SHIPPING_READINESS_CRITERIA.md
11935 .agent/staging/e2e_enhancement/asset-forms-interaction-improvement-plan.md
11100 .agent/staging/e2e_enhancement/asset-forms-interaction-report.md
9973 .agent/staging/e2e_enhancement/asset-inventory-improvement-plan.md
11917 .agent/staging/e2e_enhancement/asset-inventory-report.md
8259 .agent/staging/e2e_enhancement/asset-wizard-improvement-plan.md
13855 .agent/staging/e2e_enhancement/asset-wizard-report.md
9980 .agent/staging/e2e_enhancement/asset-wizard-visual-improvement-plan.md
14884 .agent/staging/e2e_enhancement/asset-wizard-visual-report.md
8720 .agent/staging/e2e_enhancement/browser-export-improvement-plan.md
9518 .agent/staging/e2e_enhancement/browser-export-report.md
7811 .agent/staging/e2e_enhancement/capture-remaining-improvement-plan.md
8286 .agent/staging/e2e_enhancement/capture-remaining-report.md
11633 .agent/staging/e2e_enhancement/catalog-workflow-improvement-plan.md
12054 .agent/staging/e2e_enhancement/catalog-workflow-report.md
8993 .agent/staging/e2e_enhancement/data-visualization-improvement-plan.md
11933 .agent/staging/e2e_enhancement/data-visualization-report.md
11427 .agent/staging/e2e_enhancement/deck-setup-improvement-plan.md
8717 .agent/staging/e2e_enhancement/deck-setup-report.md
8912 .agent/staging/e2e_enhancement/execution-browser-improvement-plan.md
9603 .agent/staging/e2e_enhancement/execution-browser-report.md
7243 .agent/staging/e2e_enhancement/functional-asset-selection-improvement-plan.md
8983 .agent/staging/e2e_enhancement/functional-asset-selection-report.md
6417 .agent/staging/e2e_enhancement/ghpages-deployment-improvement-plan.md
9145 .agent/staging/e2e_enhancement/ghpages-deployment-report.md
5078 .agent/staging/e2e_enhancement/health-check-improvement-plan.md
8285 .agent/staging/e2e_enhancement/health-check-report.md
1876 .agent/staging/e2e_enhancement/improvement-plan-template.md
7980 .agent/staging/e2e_enhancement/interactions-01-execution-controls-improvement-plan.md
9291 .agent/staging/e2e_enhancement/interactions-01-execution-controls-report.md
14614 .agent/staging/e2e_enhancement/interactions-02-deck-view-improvement-plan.md
15626 .agent/staging/e2e_enhancement/interactions-02-deck-view-report.md
12026 .agent/staging/e2e_enhancement/interactions-04-error-handling-improvement-plan.md
12708 .agent/staging/e2e_enhancement/interactions-04-error-handling-report.md
10830 .agent/staging/e2e_enhancement/interactive-protocol-improvement-plan.md
14774 .agent/staging/e2e_enhancement/interactive-protocol-report.md
10348 .agent/staging/e2e_enhancement/inventory-dialog-improvement-plan.md
9036 .agent/staging/e2e_enhancement/inventory-dialog-report.md
2792 .agent/staging/e2e_enhancement/jules-dispatch-log.md
14774 .agent/staging/e2e_enhancement/jupyterlite-bootstrap-improvement-plan.md
10705 .agent/staging/e2e_enhancement/jupyterlite-bootstrap-report.md
9431 .agent/staging/e2e_enhancement/jupyterlite-optimization-improvement-plan.md
10184 .agent/staging/e2e_enhancement/jupyterlite-optimization-report.md
7194 .agent/staging/e2e_enhancement/jupyterlite-paths-improvement-plan.md
11209 .agent/staging/e2e_enhancement/jupyterlite-paths-report.md
10544 .agent/staging/e2e_enhancement/low-priority-capture-improvement-plan.md
9917 .agent/staging/e2e_enhancement/low-priority-capture-report.md
7695 .agent/staging/e2e_enhancement/machine-frontend-backend-improvement-plan.md
14310 .agent/staging/e2e_enhancement/machine-frontend-backend-report.md
6832 .agent/staging/e2e_enhancement/medium-priority-capture-improvement-plan.md
9383 .agent/staging/e2e_enhancement/medium-priority-capture-report.md
5427 .agent/staging/e2e_enhancement/mock-removal-verification-improvement-plan.md
7884 .agent/staging/e2e_enhancement/mock-removal-verification-report.md
7580 .agent/staging/e2e_enhancement/monitor-detail-improvement-plan.md
6194 .agent/staging/e2e_enhancement/monitor-detail-report.md
3023 .agent/staging/e2e_enhancement/playground-direct-control-improvement-plan.md
5159 .agent/staging/e2e_enhancement/playground-direct-control-report.md
6504 .agent/staging/e2e_enhancement/protocol-execution-improvement-plan.md
8181 .agent/staging/e2e_enhancement/protocol-execution-report.md
9334 .agent/staging/e2e_enhancement/protocol-execution-wizard-improvement-plan.md
11243 .agent/staging/e2e_enhancement/protocol-execution-wizard-report.md
15417 .agent/staging/e2e_enhancement/protocol-library-improvement-plan.md
12194 .agent/staging/e2e_enhancement/protocol-library-report.md
2121 .agent/staging/e2e_enhancement/report-template.md
8639 .agent/staging/e2e_enhancement/run-protocol-machine-selection-improvement-plan.md
9418 .agent/staging/e2e_enhancement/run-protocol-machine-selection-report.md
10259 .agent/staging/e2e_enhancement/screenshot-recon-improvement-plan.md
15360 .agent/staging/e2e_enhancement/screenshot-recon-report.md
8219 .agent/staging/e2e_enhancement/smoke-improvement-plan.md
9245 .agent/staging/e2e_enhancement/smoke-report.md
6942 .agent/staging/e2e_enhancement/user-journeys-improvement-plan.md
10595 .agent/staging/e2e_enhancement/user-journeys-report.md
10484 .agent/staging/e2e_enhancement/verify-inventory-improvement-plan.md
9947 .agent/staging/e2e_enhancement/verify-inventory-report.md
7991 .agent/staging/e2e_enhancement/verify-logo-fix-improvement-plan.md
8843 .agent/staging/e2e_enhancement/verify-logo-fix-report.md
8003 .agent/staging/e2e_enhancement/viz-review-improvement-plan.md
9291 .agent/staging/e2e_enhancement/viz-review-report.md
9694 .agent/staging/e2e_enhancement/workcell-dashboard-improvement-plan.md
9058 .agent/staging/e2e_enhancement/workcell-dashboard-report.md
2763 .agent/staging/logic-audits/README.md
3338 .agent/staging/ship-prompts/01-fix-createMachine-pageobject.md
2198 .agent/staging/ship-prompts/02-fix-data-visualization-routes.md
2429 .agent/staging/ship-prompts/03-standardize-fixtures.md
2463 .agent/staging/ship-prompts/04-isolate-jupyterlite-specs.md
2214 .agent/staging/ship-prompts/05-cleanup-redundant-specs.md
2955 .agent/staging/ship-prompts/06-empty-state-detection.md
3711 .agent/staging/ship-prompts/07-basehref-unification.md
3235 .agent/staging/ship-prompts/08-deck-serialization-validation.md
3675 .agent/staging/ship-prompts/09-bootstrap-retry-logic.md
3233 .agent/staging/ship-prompts/09-investigate-core-e2e-failures.md
3177 .agent/staging/ship-prompts/10-vidpid-expansion.md
3766 .agent/staging/ship-prompts/11-session-recovery.md
4306 .agent/staging/ship-prompts/12-critical-features-e2e.md
3471 .agent/staging/ship-prompts/13-protocol-simulation-matrix.md
3185 .agent/staging/ship-prompts/14-api-proxy-econnrefused.md
4896 .agent/staging/ship-prompts/15-jupyterlite-machine-instantiation.md
5325 .agent/staging/ship-prompts/16-playground-tab-improvements.md
10647 .agent/staging/ship-prompts/17-pyodide-snapshot-restore.md
5982 .agent/staging/ship-prompts/18-session-recovery-ui.md
6890 .agent/staging/ship-prompts/19-protocol-simulation-matrix-spec.md
7236 .agent/staging/ship-prompts/20-protocol-snapshot-restore.md
267 .agent/status.json
618 .agent/status/README.md
945 .agent/tasks/README.md
4379 .agent/tasks/archive/opfs_only_refactor/PLAN.md
1353 .agent/tasks/handoff_20260125_audit_remediation/DISPATCH_LOG.md
6976 .agent/tasks/handoff_20260125_audit_remediation/README.md
2846 .agent/tasks/handoff_20260125_audit_remediation/prompts/AUDIT-03-execution-controls.md
2280 .agent/tasks/handoff_20260125_audit_remediation/prompts/AUDIT-06-schema-migrations.md
2635 .agent/tasks/handoff_20260125_audit_remediation/prompts/AUDIT-07-jupyterlite-bootstrap.md
3349 .agent/tasks/handoff_20260125_audit_remediation/prompts/AUDIT-09-direct-control.md
2398 .agent/tasks/jules_audit_20260124/DISPATCH_TABLE.md
2217 .agent/tasks/jules_audit_20260124/NEXT_AGENT_HANDOVER.md
1410 .agent/tasks/jules_audit_20260124/README.md
1580 .agent/tasks/jules_audit_20260124/dispatch.sh
20179 .agent/tasks/jules_audit_20260124/dispatch_log.md
2224 .agent/tasks/jules_audit_20260124/prompts/AUDIT-01.md
1980 .agent/tasks/jules_audit_20260124/prompts/AUDIT-02.md
2100 .agent/tasks/jules_audit_20260124/prompts/AUDIT-03.md
1911 .agent/tasks/jules_audit_20260124/prompts/AUDIT-04.md
1731 .agent/tasks/jules_audit_20260124/prompts/AUDIT-05.md
1926 .agent/tasks/jules_audit_20260124/prompts/AUDIT-06.md
1917 .agent/tasks/jules_audit_20260124/prompts/AUDIT-07.md
1983 .agent/tasks/jules_audit_20260124/prompts/AUDIT-08.md
1956 .agent/tasks/jules_audit_20260124/prompts/AUDIT-09.md
1259 .agent/tasks/jules_audit_20260124/prompts/TEST-RUN-01.md
5520 .agent/tasks/jules_batch_20260123/DISPATCH_TABLE.md
8073 .agent/tasks/jules_batch_20260123/NEXT_AGENT_PROMPT.md
1400 .agent/tasks/jules_batch_20260123/README.md
1192 .agent/tasks/jules_batch_20260123/REVIEW_PLAN.md
13909 .agent/tasks/jules_batch_20260123/REVIEW_REPORT.md
3621 .agent/tasks/jules_batch_20260123/SESSION_TRACKING.md
6202 .agent/tasks/jules_batch_20260123/dispatch.sh
3466 .agent/tasks/jules_batch_20260123/dispatch_log.md
488 .agent/tasks/jules_batch_20260123/process_merges.sh
1137 .agent/tasks/jules_batch_20260123/process_reviews.sh
2054 .agent/tasks/jules_batch_20260123/prompts/E2E-AUDIT-01.md
1625 .agent/tasks/jules_batch_20260123/prompts/E2E-NEW-01.md
1321 .agent/tasks/jules_batch_20260123/prompts/E2E-NEW-02.md
1203 .agent/tasks/jules_batch_20260123/prompts/E2E-NEW-03.md
1504 .agent/tasks/jules_batch_20260123/prompts/E2E-RUN-01.md
1005 .agent/tasks/jules_batch_20260123/prompts/E2E-RUN-02.md
1384 .agent/tasks/jules_batch_20260123/prompts/E2E-RUN-03.md
2383 .agent/tasks/jules_batch_20260123/prompts/E2E-VIZ-01.md
1057 .agent/tasks/jules_batch_20260123/prompts/E2E-VIZ-02.md
994 .agent/tasks/jules_batch_20260123/prompts/E2E-VIZ-03.md
911 .agent/tasks/jules_batch_20260123/prompts/E2E-VIZ-04.md
1802 .agent/tasks/jules_batch_20260123/prompts/JLITE-01.md
1685 .agent/tasks/jules_batch_20260123/prompts/JLITE-02.md
1698 .agent/tasks/jules_batch_20260123/prompts/JLITE-03.md
1461 .agent/tasks/jules_batch_20260123/prompts/OPFS-01.md
1572 .agent/tasks/jules_batch_20260123/prompts/OPFS-02.md
1524 .agent/tasks/jules_batch_20260123/prompts/OPFS-03.md
1385 .agent/tasks/jules_batch_20260123/prompts/REFACTOR-01.md
1240 .agent/tasks/jules_batch_20260123/prompts/REFACTOR-02.md
875 .agent/tasks/jules_batch_20260123/prompts/REFACTOR-03.md
1853 .agent/tasks/jules_batch_20260123/prompts/SPLIT-01.md
1565 .agent/tasks/jules_batch_20260123/prompts/SPLIT-02.md
1252 .agent/tasks/jules_batch_20260123/prompts/SPLIT-03.md
1329 .agent/tasks/jules_batch_20260123/prompts/SPLIT-04.md
1356 .agent/tasks/jules_batch_20260123/prompts/SPLIT-05.md
1185 .agent/tasks/jules_batch_20260123/prompts/SPLIT-06.md
2824 .agent/tasks/jules_batch_20260123/review_sessions.sh
517 .agent/tasks/jules_batch_20260123/scripts/apply_task.sh
1537 .agent/tasks/jules_batch_20260123/scripts/setup_worktree.sh
1919 .agent/tasks/jules_batch_20260123/scripts/verify_and_merge.sh
1098 .agent/tasks/jules_batch_20260124/DISPATCH_SUMMARY.md
7760 .agent/tasks/jules_batch_20260124/DISPATCH_TABLE.md
1477 .agent/tasks/jules_batch_20260124/README.md
5345 .agent/tasks/jules_batch_20260124/dispatch.sh
2224 .agent/tasks/jules_batch_20260124/dispatch_log.md
866 .agent/tasks/jules_batch_20260124/prompts/DOC-01.md
1032 .agent/tasks/jules_batch_20260124/prompts/DOC-02.md
1419 .agent/tasks/jules_batch_20260124/prompts/DOC-03.md
1331 .agent/tasks/jules_batch_20260124/prompts/FIX-01.md
1117 .agent/tasks/jules_batch_20260124/prompts/FIX-02.md
1432 .agent/tasks/jules_batch_20260124/prompts/FIX-03.md
1115 .agent/tasks/jules_batch_20260124/prompts/FIX-04.md
1490 .agent/tasks/jules_batch_20260124/prompts/REFACTOR-01.md
1934 .agent/tasks/jules_batch_20260124/prompts/REFACTOR-02.md
1193 .agent/tasks/jules_batch_20260124/prompts/STYLE-01.md
1172 .agent/tasks/jules_batch_20260124/prompts/STYLE-02.md
1181 .agent/tasks/jules_batch_20260124/prompts/STYLE-03.md
1481 .agent/tasks/jules_batch_20260124/prompts/TEST-01.md
1169 .agent/tasks/jules_batch_20260124/prompts/TEST-02.md
1794 .agent/tasks/jules_batch_20260124/prompts/TEST-03.md
846 .agent/templates/README.md
2068 .agent/templates/agent_prompt.md
2832 .agent/templates/artifact.md
635 .agent/templates/backlog_item.md
1184 .agent/templates/handoff.md
1299 .agent/templates/investigation.md
866 .agent/templates/plan.md
759 .agent/templates/prompt_batch.md
1290 .agent/templates/reference_document.md
712 .agent/templates/research.md
649 .agent/templates/reusable_prompt.md
1507 .agent/templates/unified_task.md
803 .agent/workflows/README.md
9661 .agent/workflows/conversation_summary.md
4280 .agent/workflows/document-directory.md
6271 .agent/workflows/frontend-polish.md
3953 .agent/workflows/high-level-review.md
3038 .agent/workflows/jules-morning-checkin.md
5486 .agent/workflows/nighttime-jules-dispatch.md
7186 .agent/workflows/oracle-critique.md
3802 .agent/workflows/scripts/concatenate_session.py
4101 .agent/workflows/scripts/convo_filter.py
46 praxis/.agent/.migrated
1933 praxis/.agent/NEXT_ASSET_WIZARD_DECK_SELECTOR.md
1767 praxis/.agent/PRAXIS_e2e_diffs.md
1119 praxis/.agent/TECHNICAL_DEBT.md
7012 praxis/.agent/audits/deep_audit_synthesis_feb2026.md
980 praxis/.agent/audits/jules_1009855817323566566_core_services.md
1303 praxis/.agent/audits/jules_1530702602442313801_resource_index.md
1335 praxis/.agent/audits/jules_17585661742425938948_core_components.md
1024 praxis/.agent/audits/jules_5981630414686659482_run_protocol.md
1088 praxis/.agent/audits/jules_6546155916196685132_asset_wizards.md
6916 praxis/.agent/praxis_e2e_diff_report.md
36 praxis/.agent/workspace.id
46 praxis/web-client/.agent/.migrated
13465 praxis/web-client/.agent/plans/opfs-only-refactor.md
2958 praxis/web-client/.agent/reports/deck_layout_coming_soon_investigation.md
```
