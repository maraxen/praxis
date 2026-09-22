---
title: 'RECON - Repository Cleanup Audit'
---

# RECON - Repository Cleanup Audit

This report identifies stale files, duplicate information, and consolidation opportunities to improve repository hygiene.

## 1. Stale Files

A number of files in the repository root appear to be temporary, transitional, or obsolete.

| File | Recommendation | Rationale |
| :--- | :--- | :--- |
| `implementation_plan.md` | Archive | This is a detailed plan for a past feature ("State Inspection & Reporting Enhancement") and is now historical. |
| `modified_changes.diff` | Delete | A patch file that appears to have been accidentally committed. |
| `temp_state_size_test.py` | Delete | A temporary, standalone test script. If needed, it should be integrated into the main test suite. |
| `test_resolve_params.py` | Delete | Another orphaned test script. |
| `port_docstrings.py` | Move to `scripts/` | A one-off utility script that fits better in the `scripts` directory. |
| `praxis.db` | Delete & Add to `.gitignore` | A local development SQLite database that should not be tracked in version control. |
| `walkthrough.md` | Move to `docs/getting-started/` | This is user documentation and should be co-located with other guides. |

## 2. Duplicate Content & Consolidation

High-level project management and planning documents are scattered in the root directory. There is an opportunity to consolidate them for clarity.

### Consolidation Recommendations

Create a new directory `docs/project/` and move the following files into it:

- `POST_SHIP.md`
- `ROADMAP.md`
- `RUNWAY.md`
- `TECHNICAL_DEBT.md`
- `VERIFICATION_REPORT.md`

This change will group related project-level documents and declutter the root directory.

## 3. Files to Archive

The `references/` directory contains valuable historical audits and analyses. These are not active documents and are excellent candidates for archival to reduce top-level clutter.

### Archival Recommendations

The entire `references/` directory should be moved to `.agent/archive/references/`. This preserves the content for historical context while removing it from the active project structure.

- `references/machine_sim_audit.md`
- `references/protocol_asset_audit.md`
- `references/qa_interaction_checklist.md`
- `references/resource_error_log.md`
- `references/state_gap_analysis.md`
- `references/styling_audit_report.md`
- `references/suite_comprehensiveness_analysis.md`
- `references/test_plan_v1.md`
- `references/workcell_ui_audit.md`

## Summary of Recommendations

### Files to Delete (4)
- `modified_changes.diff`
- `praxis.db`
- `temp_state_size_test.py`
- `test_resolve_params.py`

### Files to Move/Consolidate (7)
- `port_docstrings.py` -> `scripts/`
- `walkthrough.md` -> `docs/getting-started/`
- `POST_SHIP.md` -> `docs/project/`
- `ROADMAP.md` -> `docs/project/`
- `RUNWAY.md` -> `docs/project/`
- `TECHNICAL_DEBT.md` -> `docs/project/`
- `VERIFICATION_REPORT.md` -> `docs/project/`

### Files to Archive (10)
- `implementation_plan.md` -> `.agent/archive/`
- The entire `references/` directory and its contents.

This list identifies over 10 items and provides clear, actionable recommendations for cleanup.
