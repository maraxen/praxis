# wt-20260909-172820 Internal Docs

## Daily
- [260912_overnight-decisions](daily/260912_overnight-decisions.md) — Every decision the 260912 L5 loop made without a human gate: the REPL-refocus staleness dispositions, the #5110 selection, and the praxia debt filings.
- [260121_jules-session-triage](daily/260121_jules-session-triage.md) — Jules Session Triage - 2026-01-21 11:10 AM
- [260121_orchestrator-session-summary-20260121](daily/260121_orchestrator-session-summary-20260121.md) — Orchestrator Session Summary - 2026-01-21
- [260121_summary](daily/260121_summary.md) — Jules Diff Extraction - 2026-01-21
- [260121_v01alpha-status-20260121](daily/260121_v01alpha-status-20260121.md) — V0.1-Alpha Merge Status Report
- [260120_orchestration](daily/260120_orchestration.md) — Orchestration Learning Log
- [260101_development-matrix](daily/260101_development-matrix.md) — Development Matrix

## Handoffs
- [260131_e2e-autonomous-handoff](handoffs/260131_e2e-autonomous-handoff.md) — Autonomous E2E Stabilization Handoff
- [260131_ship-coordination-handoff](handoffs/260131_ship-coordination-handoff.md) — Praxis Ship Readiness - Coordination Handoff
- [260129_jules-stage1-prompts](handoffs/260129_jules-stage1-prompts.md) — Jules Stage 1 Dispatch Prompts
- [260129_praxis-handoff](handoffs/260129_praxis-handoff.md) — Praxis E2E Remediation Handoff
- [260128_e2e-database-seeding-handoff](handoffs/260128_e2e-database-seeding-handoff.md) — E2E Database Seeding Issue - Handoff
- [260128_e2e-stabilization-handoff](handoffs/260128_e2e-stabilization-handoff.md) — E2E Test Suite Stabilization - Session Handoff
- [260122_v01alpha-debug-handoff-20260121](handoffs/260122_v01alpha-debug-handoff-20260121.md) — v0.1-alpha Debug Handoff
- [260122_v01alpha-orchestrator-handoff-20260121-1845](handoffs/260122_v01alpha-orchestrator-handoff-20260121-1845.md) — v0.1-Alpha Orchestrator Handoff
- [260121_final-merge-handoff](handoffs/260121_final-merge-handoff.md) — FINAL MERGE HANDOFF - v0.1-alpha
- [260121_jules-handover-20260121](handoffs/260121_jules-handover-20260121.md) — Jules Integration Handover - 2026-01-21

## Plans
- [260912_repl-gate-manifest-scope-sprint136](plans/260912_repl-gate-manifest-scope-sprint136.md) — Sprint 136 plan and record: the repl.yml GATE G7 false positive that skipped all ten browser gates on the 4-PR stack, its two-defect root cause, the surface-dispatch fixer run, and the differential verification.
- [260824_repl-autocomplete-scope](plans/260824_repl-autocomplete-scope.md) — Scope and outcome for as-you-type completion in the JupyterLite PLR REPL; the planned jedi preload proved unnecessary
- [260817_praxis-repl-refocus-execution-plan](plans/260817_praxis-repl-refocus-execution-plan.md) — Dependency-ordered 8-phase execution plan composed from three adversarially-reviewed specs and five executed spikes, with per-phase gates, audit strategy, rollback, and an unproven-assumptions ledger.
- [260210_final-mvp-implementation-strategy](plans/260210_final-mvp-implementation-strategy.md) — FINAL MVP IMPLEMENTATION STRATEGY
- [260210_final-protocol-execution-fix-plan](plans/260210_final-protocol-execution-fix-plan.md) — FINAL PROTOCOL EXECUTION & PLAYGROUND FIX PLAN
- [260210_protocol-playground-fix-plan](plans/260210_protocol-playground-fix-plan.md) — Protocol Execution & Playground Fix Plan
- [260209_asset-wizard-deck-selector](plans/260209_asset-wizard-deck-selector.md) — Plan for adding a deck-selection step to the asset wizard, written ahead of the Feb 2026 E2E debugging wave
- [260131_ship-work-plan](plans/260131_ship-work-plan.md) — Ship Work Plan
- [260128_e2e-test-suite-hardening-plan](plans/260128_e2e-test-suite-hardening-plan.md) — E2E Test Suite Debug & Realistic User Interaction Plan
- [260126_opfs-only-refactor](plans/260126_opfs-only-refactor.md) — Plan to make OPFS the only browser-mode persistence layer, removing the legacy sql.js + IndexedDB path
- [260122_post-merge-checklist](plans/260122_post-merge-checklist.md) — Post-Merge Checklist
- [260122_post-ship](plans/260122_post-ship.md) — Post-Ship Roadmap (v0.1-Alpha+)
- [260122_web-hid-shim](plans/260122_web-hid-shim.md) — WebHID Shim Implementation Plan
- [260121_connection-persistence-tests](plans/260121_connection-persistence-tests.md) — Browser Mode Connection Persistence Tests
- [260121_final-merge-plan](plans/260121_final-merge-plan.md) — FINAL MERGE PLAN - v0.1-alpha (Praxis)
- [260121_jules-integration-plan](plans/260121_jules-integration-plan.md) — Jules Integration Plan - 2026-01-21
- [260116_runway](plans/260116_runway.md) — 🛫 Launch Runway: Project "Praxis"
- [260115_test-plan-v1](plans/260115_test-plan-v1.md) — Interaction Test Plan v1

## Specs
- [260914_first-run-auto-setup](specs/260914_first-run-auto-setup.md) — Spec for bootstrapping PyLabRobot automatically on every Pyodide kernel start, fail-closed and visible, with no user-typed setup
- [260825_copilot-pipeline-challenger](specs/260825_copilot-pipeline-challenger.md) — CHALLENGER-role findings against 260825_coxswain-phase-2-functiongemma-copilot-p.md. All file:line claims in the spec were re-verified against the tree on repl-fresh-boot; findings are ranked blocker/major/minor with cites and concrete fixes. No wholesale rewrite proposed.
- [260825_copilot-pipeline-defender](specs/260825_copilot-pipeline-defender.md) — DEFENDER counter-role review of 260825_coxswain-phase-2-functiongemma-copilot-p.md: steelman of D1-D10, robustness audit of load-bearing-but-fragile claims, critical-path feasibility re-verified against the tree, and resilience judgment of §8 counters. All repo cites re-verified 260825 on branch repl-fresh-boot.
- [260825_coxswain-phase-2-functiongemma-copilot-p](specs/260825_coxswain-phase-2-functiongemma-copilot-p.md) — Spec for the synthetic-data pipeline, functiongemma-270m-it fine-tune, browser serving via Transformers.js/WebGPU behind --with-coxswain, and ParseSource integration. REV 2: reconciled from challenger (2 blockers, 7 majors, 8 minors) and defender (11 robustness findings) reviews of 260825.
- [260824_coxswain-mvp-ux-spec](specs/260824_coxswain-mvp-ux-spec.md) — Implementable specification for the Coxswain propose/confirm, clarification, FFT-gate-extension and audit-trail surfaces: formalizes the eight negotiable UX axes (N1-N8) resolved in brainstorm session 48789b43 against the locked architecture (F1-F10), with fixer-ready work-item decomposition, correlation-ID contract, structural safety constraints mandated by the pre-mortem, and a risk table. Revised 260824 to close the adversarial review cycle (audits 260824_coxswain_spec_challenge / _defense) — see the Revision Log.
- [260824_coxswain-ux-open-design-axes-task-id-260](specs/260824_coxswain-ux-open-design-axes-task-id-260.md) — Brainstorm: Coxswain UX open design axes (task_id 260824_coxswain_spec_design): eight negotiable design decisions for the FunctionGemma-270m-it-powered voice/text-to-PyLabRobot copilot injected into web-repl — confirmation-friction tiering (N1), editable propose/confirm cards (N2), staleness handling / handshake-hash formalization (N3), sandbox pre-simulation reuse from praxis/backend/core/simulation (N4), propose/confirm card disclosure depth (N5), FFT gate audit-trail format (N6), expert-override escape hatch (N7), and visual disambiguation ghosting on the Visualizer (N8). Architecture (F1-F10) is locked; this session covers only the negotiable UX/behavior axes given the hidden constraints (H1-H4: inline-edit responsiveness budget, automation-bias tiebreak toward friction/disclosure, N4 reuse is a genuine unknown requiring an explicit recon-check-or-defer choice, and copy/interaction/accessibility discipline).
- [260817_spec-visualizer-transport-shim](specs/260817_spec-visualizer-transport-shim.md) — Adversarially-reviewed spec for the praxis REPL refocus (visualizer); converged=True after 1 round(s), verdict REVISE.
- [260817_spec-web-repl-extraction](specs/260817_spec-web-repl-extraction.md) — Adversarially-reviewed spec for the praxis REPL refocus (web-repl); converged=True after 1 round(s), verdict REVISE.
- [260817_spec-wheel-build-plr-upgrade](specs/260817_spec-wheel-build-plr-upgrade.md) — Adversarially-reviewed spec for the praxis REPL refocus (build-pipeline); converged=True after 2 round(s), verdict ACCEPT.
- [260122_inventory-wizard-design-spec](specs/260122_inventory-wizard-design-spec.md) — Inventory Wizard Redesign Spec

## Actuation Surfaces

## Audits
- [260912_sprint136-audit](audits/260912_sprint136-audit.md) — Sonnet praxia:reviewer report for commit e995de31, persisted verbatim: soundness answer, six-dimension scores, and the two non-blocking staleness suggestions with their resolution.
- [260209_web-client-technical-debt](audits/260209_web-client-technical-debt.md) — Web-client debt entries from Feb 2026, starting with replacing DeckCatalogService's hardcoded deck-type matching with programmatic PyLabRobot detection
- [260206_e2e-diff-report](audits/260206_e2e-diff-report.md) — File-by-file report of the 32-file E2E change set from the Feb 2026 Jules sessions
- [260206_e2e-jules-session-review](audits/260206_e2e-jules-session-review.md) — Final status review of the Jules E2E sessions for backlog #380/#426
- [260206_e2e-verification-feb03](audits/260206_e2e-verification-feb03.md) — E2E Verification Report - Feb 03, 2026 (Run 2)
- [260206_hardware-discovery-audit](audits/260206_hardware-discovery-audit.md) — Audit: praxis/web-client/src/app/core/services/hardware-discovery.service.ts
- [260206_jules-audit-asset-wizards](audits/260206_jules-audit-asset-wizards.md) — Jules deep audit of the asset wizards (Feb 3, 2026; quality score 4/10)
- [260206_jules-audit-core-components](audits/260206_jules-audit-core-components.md) — Jules deep audit of the Docs and StateInspector core components (Feb 3, 2026; quality score 6.5/10)
- [260206_jules-audit-core-services](audits/260206_jules-audit-core-services.md) — Jules deep audit of the web-client core services (Feb 3, 2026; quality score 6/10)
- [260206_jules-audit-resource-index](audits/260206_jules-audit-resource-index.md) — Jules deep audit of the resource and index components (Feb 3, 2026; quality score 4/10)
- [260206_jules-audit-run-protocol](audits/260206_jules-audit-run-protocol.md) — Jules deep audit of the run-protocol feature (Feb 3, 2026; quality score 4/10)
- [260206_python-worker-audit](audits/260206_python-worker-audit.md) — Audit: python_runtime
- [260206_web-client-deep-audit-synthesis](audits/260206_web-client-deep-audit-synthesis.md) — Synthesis of 15+ Jules deep-audit sessions over the Angular web client (Feb 3, 2026)
- [260131_01-data-models](audits/260131_01-data-models.md) — Data Models Audit
- [260131_02-asset-wizard](audits/260131_02-asset-wizard.md) — Asset Wizard Audit
- [260131_03-protocol-execution](audits/260131_03-protocol-execution.md) — Protocol Execution Audit
- [260131_04-constraints](audits/260131_04-constraints.md) — Constraint Validation Audit
- [260131_05-github-pages](audits/260131_05-github-pages.md) — GitHub Pages Pathing Audit
- [260131_06-jupyterlite](audits/260131_06-jupyterlite.md) — JupyterLite Bootstrap Audit
- [260131_07-hardware-discovery](audits/260131_07-hardware-discovery.md) — Hardware Discovery Audit
- [260131_08-serialization](audits/260131_08-serialization.md) — Serialization Audit
- [260131_09-recommendations](audits/260131_09-recommendations.md) — Recommendations & Future Audits
- [260131_10-import-export](audits/260131_10-import-export.md) — Import/Export & OPFS VFS Audit
- [260131_11-error-handling](audits/260131_11-error-handling.md) — Error Boundary Handling Audit
- [260131_12-session-recovery](audits/260131_12-session-recovery.md) — Session & Run Recovery Audit
- [260131_13-memory-management](audits/260131_13-memory-management.md) — Pyodide Memory Management Audit
- [260131_14-port-persistence](audits/260131_14-port-persistence.md) — WebSerial Port Persistence Audit
- [260131_15-storage-quotas](audits/260131_15-storage-quotas.md) — Storage Quotas Audit
- [260131_comprehensive-logic-audit](audits/260131_comprehensive-logic-audit.md) — Comprehensive Logic Audit Report
- [260131_critical-features](audits/260131_critical-features.md) — Critical Features Inventory
- [260131_e2e-persistent-bugs](audits/260131_e2e-persistent-bugs.md) — E2E Persistent Bugs - Full Audit
- [260131_e2e-static-analysis](audits/260131_e2e-static-analysis.md) — E2E Static Analysis - Redundant/Outdated Tests
- [260131_final-ship](audits/260131_final-ship.md) — Praxis Ship-Ready Verification Results
- [260129_code-smells-audit](audits/260129_code-smells-audit.md) — Code Smells Audit: praxis/web-client/src/
- [260129_complexity-audit](audits/260129_complexity-audit.md) — Code Complexity Analysis
- [260129_dead-code-audit](audits/260129_dead-code-audit.md) — Dead Code Audit: `praxis/web-client/src`
- [260129_e2e-coverage-audit](audits/260129_e2e-coverage-audit.md) — E2E Spec Coverage Audit
- [260129_e2e-failures-audit-260129](audits/260129_e2e-failures-audit-260129.md) — E2E Test Failure Audit Report (260129)
- [260129_e2e-file-audits](audits/260129_e2e-file-audits.md) — E2E File Audits
- [260129_feature-architecture-audit](audits/260129_feature-architecture-audit.md) — Feature Module Architecture Audit
- [260129_service-layer-audit](audits/260129_service-layer-audit.md) — Service Layer Audit
- [260128_e2e-status](audits/260128_e2e-status.md) — E2E Test Status Report - Praxis
- [260125_audit-01-run-protocol](audits/260125_audit-01-run-protocol.md) — AUDIT-01: Run Protocol & Wizard
- [260125_audit-03-protocol-execution](audits/260125_audit-03-protocol-execution.md) — AUDIT-03: Protocol Library & Execution Monitor
- [260125_audit-06-persistence](audits/260125_audit-06-persistence.md) — AUDIT-06: Browser Persistence (OPFS/SQLite)
- [260125_audit-07-jupyterlite](audits/260125_audit-07-jupyterlite.md) — AUDIT-07: JupyterLite Integration
- [260125_audit-08-ghpages-config](audits/260125_audit-08-ghpages-config.md) — AUDIT-08: GitHub Pages Deployment Configuration
- [260125_audit-09-direct-control](audits/260125_audit-09-direct-control.md) — AUDIT-09: Direct Control Feature
- [260125_build-errors](audits/260125_build-errors.md) — Build Error Report - 2026-01-24
- [260125_index](audits/260125_index.md) — Praxis GH-Pages Shipping Readiness Audits
- [260125_plan-for-remediation](audits/260125_plan-for-remediation.md) — Handoff: Addressing Critical Audit Blockers
- [260123_jupyterlite-ghpages-audit](audits/260123_jupyterlite-ghpages-audit.md) — JupyterLite GH-Pages Simulation Audit
- [260123_opfs-pyodide-audit](audits/260123_opfs-pyodide-audit.md) — OPFS + Pyodide Integration Audit
- [260123_visual-audit-data-playground](audits/260123_visual-audit-data-playground.md) — Visual Audit Report: Data & Playground
- [260123_visual-audit-run-protocol](audits/260123_visual-audit-run-protocol.md) — Visual Audit - Run Protocol Pages
- [260123_visual-audit-settings-workcell](audits/260123_visual-audit-settings-workcell.md) — Visual Audit - Settings & Workcell
- [260122_css-theming-audit](audits/260122_css-theming-audit.md) — Hardcoded CSS Audit Report
- [260122_io-transport-audit](audits/260122_io-transport-audit.md) — Recon Report: pylabrobot.io Transport Audit for Browser Mode
- [260121_component-audit-assets](audits/260121_component-audit-assets.md) — Component Audit: Assets & Protocols
- [260121_component-audit-playground](audits/260121_component-audit-playground.md) — Component Audit: Playground & Run Protocol
- [260121_dependency-audit](audits/260121_dependency-audit.md) — Dependency Audit Report
- [260121_extracted-plr-audit](audits/260121_extracted-plr-audit.md) — PLR Category Architecture Audit - Extraction Report
- [260121_v01alpha-final-review-20260121](audits/260121_v01alpha-final-review-20260121.md) — V0.1-Alpha Final Review - 2026-01-21 14:15
- [260120_verification-report](audits/260120_verification-report.md) — Final System Verification Report
- [260115_machine-sim-audit](audits/260115_machine-sim-audit.md) — Machine Simulation Architecture Audit & Refactor Proposal
- [260115_protocol-asset-audit](audits/260115_protocol-asset-audit.md) — Protocol Asset Audit
- [260115_resource-error-log](audits/260115_resource-error-log.md) — Resource Management Error Log & Audit
- [260115_state-gap-analysis](audits/260115_state-gap-analysis.md) — State Inspection & Simulation Reporting Gap Analysis
- [260115_styling-audit-report](audits/260115_styling-audit-report.md) — Styling Audit Report
- [260115_suite-comprehensiveness-analysis](audits/260115_suite-comprehensiveness-analysis.md) — Test Suite Comprehensiveness Analysis
- [260115_workcell-ui-audit](audits/260115_workcell-ui-audit.md) — Workcell Interface & Deck View Audit
- [260107_technical-debt](audits/260107_technical-debt.md) — Technical Debt / Missing Features
- [251225_technical-debt](audits/251225_technical-debt.md) — Technical Debt

## Research
- [260825_copilot-pipeline-recon](research/260825_copilot-pipeline-recon.md) — Verification of the 260824 scoping doc claims against current code, filling gaps for the next phase spec: tool-schema extraction seams, Chatterbox execution verification, protocol fixtures, PLR docs corpus, web-repl serving substrate, parse-source seam, and artifact-size constraints.
- [260825_functiongemma-training-serving-research](research/260825_functiongemma-training-serving-research.md) — Fine-tuning and browser-serving google/functiongemma-270m-it for a PyLabRobot lab-automation copilot
- [260824_gemma-finetuned-plr-voice-text-copilot-scoping](research/260824_gemma-finetuned-plr-voice-text-copilot-scoping.md) — Scoping assessment for a Gemma model fine-tuned to translate voice/text lab instructions into validated PyLabRobot calls inside the JupyterLite Playground rebase: training-data sourcing, browser deployment feasibility, clarification UX, and build-location recommendation.
- [260817_g2-spike-battery-verdict](research/260817_g2-spike-battery-verdict.md) — Adjudication of the five G2 criteria from spikes S-A/S-B/S-C/S-D/S-E/S-F, with independent spot-check output; overall PARTIAL-GO.
- [260817_spike-evidence-repl-refocus](research/260817_spike-evidence-repl-refocus.md) — Five executed browser/CPython spikes grounding the refocus specs; every finding tagged ran/read with verbatim commands and output.
- [260817_standalone-web-repl-extraction-shell-and-brainstorm](research/260817_standalone-web-repl-extraction-shell-and-brainstorm.md) — Brainstorm: Standalone web-repl extraction, shell, and notebook persistence for praxis REPL refocus (task_id 260817_praxis_repl_refocus): what is the right boundary for a standalone PyLabRobot JupyterLite artifact, what replaces the Angular shell (theme + device-auth user-gesture dialog + iframe host), how to make savable notebooks actually true, whether a build step is still needed, and what happens to Direct Control.
- [260817_visualizer-transport-shim-and-augmentati-2-brainstorm](research/260817_visualizer-transport-shim-and-augmentati-2-brainstorm.md) — Brainstorm: Visualizer transport shim and augmentation API for the praxis JupyterLite/PLR REPL refocus: design the Python-side transport seam, the augmentation API shape, CDN vendoring, the first concrete augmentation, and upstream-drift detection.
- [260817_visualizer-transport-shim-and-augmentati-brainstorm](research/260817_visualizer-transport-shim-and-augmentati-brainstorm.md) — Brainstorm: Visualizer transport shim and augmentation API for the praxis JupyterLite REPL refocus: how to drive the PyLabRobot Konva visualizer from an in-browser Pyodide kernel with no websocket server, and what shape the augmentation API should take, given proven-by-execution spike results (renderer is a pure function of injected JSON; 4 vis.js spans are the entire network coupling; a second Konva overlay layer attaches with zero lib.js edits).
- [260817_wheel-build-plr-upgrade-and-version-cohe-2-brainstorm](research/260817_wheel-build-plr-upgrade-and-version-cohe-2-brainstorm.md) — Brainstorm: Wheel build, PLR upgrade, and version coherence for the praxis JupyterLite REPL refocus: what mechanism makes version drift between the PLR submodule pin, the built browser wheel, the hardcoded TypeScript/Python filenames, and the jupyterlite piplite index structurally impossible; who builds the wheel and when (local dev vs CI vs committed artifact); what the three-Python policy should be (venv 3.14.6 / ty 3.12 / pyodide 3.13); and how to shape the PLR import surface so the next upstream reorg is localized.
- [260817_wheel-build-plr-upgrade-and-version-cohe-brainstorm](research/260817_wheel-build-plr-upgrade-and-version-cohe-brainstorm.md) — Brainstorm: Wheel build, PLR upgrade, and version coherence for the praxis JupyterLite REPL refocus: what mechanism makes drift between the PLR submodule pin, the built browser wheel, the hardcoded TypeScript filenames, and the piplite/wheel index structurally impossible; who builds the wheel and when (local dev vs CI vs committed artifact); and what the Python-version policy should be across venv 3.14.6 / ty 3.12 / package.json pyodide ^0.29.0 / in-browser CPython 3.14.2.
- [260131_asset-wizard-filtering-logic-recon](research/260131_asset-wizard-filtering-logic-recon.md) — Asset Wizard Definition Filtering Logic Audit
- [260131_e2e-timeout-investigation](research/260131_e2e-timeout-investigation.md) — E2E Timeout Cluster Investigation
- [260131_file-splitting-report](research/260131_file-splitting-report.md) — web-client File Splitting Candidates Report
- [260131_simulated-machine-instantiation-recon](research/260131_simulated-machine-instantiation-recon.md) — Simulated Machine Instantiation Recon Report
- [260129_data-viz-e2e-investigation](research/260129_data-viz-e2e-investigation.md) — Data Visualization E2E Investigation
- [260123_opfs-hardware-review](research/260123_opfs-hardware-review.md) — Hardware Discovery Under OPFS
- [260122_asset-selection-analysis](research/260122_asset-selection-analysis.md) — Asset Selection Logic & Status Report
- [260122_backend-categories-investigation](research/260122_backend-categories-investigation.md) — Investigation Report: Backend Categories in Inventory
- [260122_deck-layout-coming-soon-investigation](research/260122_deck-layout-coming-soon-investigation.md) — Found the coming-soon message for non-Hamilton decks intentional: slot-based layout editing was unimplemented
- [260122_docs-404-investigation](research/260122_docs-404-investigation.md) — Docs 404 Investigation
- [260122_frontend-backend-type-architecture](research/260122_frontend-backend-type-architecture.md) — Research Report: Frontend and Backend Type Architecture
- [260122_inventory-search-investigation](research/260122_inventory-search-investigation.md) — Inventory Search Logic Investigation - Root Cause Analysis
- [260122_inventory-wizard-recon](research/260122_inventory-wizard-recon.md) — Recon Report: Inventory Wizard Analysis
- [260122_investigation-selective-transfer-params](research/260122_investigation-selective-transfer-params.md) — Investigation Report: Selective Transfer Parameter Persistence
- [260122_jules-dispatch-recon-20260122](research/260122_jules-dispatch-recon-20260122.md) — Jules Dispatch Log - Recon-Based Tasks
- [260122_machine-args-configuration-investigation](research/260122_machine-args-configuration-investigation.md) — Investigation Report: Per-Machine Argument Configuration
- [260122_machine-type-filtering-investigation](research/260122_machine-type-filtering-investigation.md) — Machine Type Filtering Investigation Report
- [260122_on-the-fly-definitions-investigation](research/260122_on-the-fly-definitions-investigation.md) — Investigation: On-the-Fly Simulation Definition Creation
- [260122_oracle-asset-wizard-investigation](research/260122_oracle-asset-wizard-investigation.md) — Oracle Advisory: Asset Wizard Investigation Report
- [260122_recon-asset-wizard-visual](research/260122_recon-asset-wizard-visual.md) — Recon report: asset wizard visual grid sizing
- [260122_recon-changelog-setup](research/260122_recon-changelog-setup.md) — RECON - CHANGELOG.md Setup Research
- [260122_recon-documentation](research/260122_recon-documentation.md) — Documentation Reconnaissance Report
- [260122_recon-e2e-coverage](research/260122_recon-e2e-coverage.md) — E2E Test Coverage Reconnaissance Report
- [260122_recon-e2e-infrastructure](research/260122_recon-e2e-infrastructure.md) — RECON Report: E2E Test Infrastructure
- [260122_recon-gitignore](research/260122_recon-gitignore.md) — Reconnaissance Report: .gitignore Audit
- [260122_recon-global-shimming-status](research/260122_recon-global-shimming-status.md) — RECON Report: Global Module Shimming Status
- [260122_recon-guided-setup-states](research/260122_recon-guided-setup-states.md) — Reconnaissance Report: Guided Setup Visual State Transitions
- [260122_recon-hid-shim-status](research/260122_recon-hid-shim-status.md) — Reconnaissance Report: WebHID Transport Shim Status
- [260122_recon-logo-branding](research/260122_recon-logo-branding.md) — RECONNAISSANCE REPORT: Praxis Logo and Gradient Branding
- [260122_recon-playwright-jules](research/260122_recon-playwright-jules.md) — RECON Report: Playwright Usage for Jules
- [260122_recon-protocol-runner-visual](research/260122_recon-protocol-runner-visual.md) — RECON Report: Protocol Runner Visual Audit
- [260122_recon-repo-cleanup](research/260122_recon-repo-cleanup.md) — RECON - Repository Cleanup Audit
- [260122_recon-root-markdown](research/260122_recon-root-markdown.md) — Root Markdown Files Audit Report
- [260122_recon-socket-shim-status](research/260122_recon-socket-shim-status.md) — RECON Report: Socket/TCP Transport Shim Status
- [260122_recon-theme-variables](research/260122_recon-theme-variables.md) — RECON Report: Theme CSS Variable Audit
- [260122_recon-versioning-strategy](research/260122_recon-versioning-strategy.md) — Reconnaissance Report: Versioning Strategy and Roadmap
- [260122_relative-paths-recon-20260122](research/260122_relative-paths-recon-20260122.md) — Web Client Relative Path Audit Report
- [260122_research-infinite-consumables](research/260122_research-infinite-consumables.md) — Research Report: Infinite Consumables & Resource Depletion
- [260122_resource-vs-machine-flow-investigation](research/260122_resource-vs-machine-flow-investigation.md) — Investigation: Add Resource vs. Add Machine Flow in Playground
- [260122_simulation-backend-dropdown-bug](research/260122_simulation-backend-dropdown-bug.md) — Report: Simulation Backend Dropdown Bug Fix
- [260122_simulation-selection-investigation](research/260122_simulation-selection-investigation.md) — Simulation Selection Investigation
- [260121_extracted-browser-interrupt](research/260121_extracted-browser-interrupt.md) — Browser Interrupt Logic Extraction (TD-801)
- [260121_extracted-geometry-heuristics](research/260121_extracted-geometry-heuristics.md) — Extracted Geometry Heuristics Code (TD-702)
- [260121_extracted-machine-registration](research/260121_extracted-machine-registration.md) — Backend Machine Registration Work Extraction Report

## Decisions
- [260817_repl-layout-and-delivery-mechanism](decisions/260817_repl-layout-and-delivery-mechanism.md) — ADR resolving the path collision between the three refocus specs by deciding what ships as a wheel and what ships as loose fetched files; includes the single-class-object invariant, the three-detector drift design, and the per-spec re-scope tables that Phase 3's gate checks.

## Preregistration

## Reference
- [260130_playwright-angular-best-practices-2026](reference/260130_playwright-angular-best-practices-2026.md) — Playwright + Angular Best Practices (2026)
- [260122_shared-array-buffer](reference/260122_shared-array-buffer.md) — Known Issue: SharedArrayBuffer is not defined
- [260121_alembic-migration-guide](reference/260121_alembic-migration-guide.md) — Alembic Migration Workflow Guide
- [260121_hardware-testing-guide](reference/260121_hardware-testing-guide.md) — WebSerial Hardware-in-the-Loop (HITL) Testing Guide
- [260118_frontend-polish](reference/260118_frontend-polish.md) — Frontend Polish Pipeline
- [260115_machine-sim-audit](reference/260115_machine-sim-audit.md) — Machine Simulation Architecture Audit
- [260115_qa-interaction-checklist](reference/260115_qa-interaction-checklist.md) — QA Interaction Checklist
- [260115_state-gap-analysis](reference/260115_state-gap-analysis.md) — State Inspection & Simulation Reporting Gap Analysis
- [260115_ui-guide](reference/260115_ui-guide.md) — Frontend UI/UX Guide & Style System
- [260114_installation-browser](reference/260114_installation-browser.md) — Browser Mode Installation
- [260114_installation-lite](reference/260114_installation-lite.md) — Lite Mode Installation
- [260114_installation-production](reference/260114_installation-production.md) — Production Mode Installation
- [260114_update-archive](reference/260114_update-archive.md) — Update Archive Workflow
- [260107_hardware-matrix](reference/260107_hardware-matrix.md) — PyLabRobot Hardware Communication Matrix
- [260107_notes](reference/260107_notes.md) — Development Notes
- [260105_protocol-inference-sharp-bits](reference/260105_protocol-inference-sharp-bits.md) — Protocol Inference: Sharp Bits & Gotchas
- [260102_browser-script](reference/260102_browser-script.md) — Praxis Demo Script
- [260101_architecture](reference/260101_architecture.md) — Application Architecture: Runtime Modes
- [251230_assets](reference/251230_assets.md) — Assets
- [251230_backend](reference/251230_backend.md) — Backend Components
- [251230_browser-mode](reference/251230_browser-mode.md) — Browser Mode
- [251230_cli-commands](reference/251230_cli-commands.md) — CLI Commands
- [251230_cmms-interface-design-research](reference/251230_cmms-interface-design-research.md) — **The Interface of Reliability: A Comprehensive Analysis of Industrial Asset Management UI/UX Paradigms (2025 Edition)**
- [251230_code-style](reference/251230_code-style.md) — Code Style Guide
- [251230_configuration](reference/251230_configuration.md) — Configuration
- [251230_contributing](reference/251230_contributing.md) — Contributing
- [251230_data-visualization](reference/251230_data-visualization.md) — Data Visualization
- [251230_execution-flow](reference/251230_execution-flow.md) — Execution Flow
- [251230_frontend](reference/251230_frontend.md) — Frontend Components
- [251230_hardware-discovery](reference/251230_hardware-discovery.md) — Hardware Discovery
- [251230_installation](reference/251230_installation.md) — Installation Overview
- [251230_lims-ux-pattern-analysis](reference/251230_lims-ux-pattern-analysis.md) — **Comparative Analysis of User Experience Architectures in Leading Laboratory Information Management Systems (2024-2025)**
- [251230_overview](reference/251230_overview.md) — Architecture Overview
- [251230_protocols](reference/251230_protocols.md) — Protocols
- [251230_quickstart](reference/251230_quickstart.md) — Quick Start
- [251230_rest-api](reference/251230_rest-api.md) — REST API Reference
- [251230_scientific-software-complexity-abstraction](reference/251230_scientific-software-complexity-abstraction.md) — **Architecting the Glass Box: Progressive Disclosure and Complexity Management in Scientific Software Ecosystems**
- [251230_services](reference/251230_services.md) — Service Layer Reference
- [251230_state-management](reference/251230_state-management.md) — State Management
- [251230_testing](reference/251230_testing.md) — Testing Guide
- [251230_troubleshooting](reference/251230_troubleshooting.md) — Troubleshooting
- [251230_websocket-api](reference/251230_websocket-api.md) — WebSocket API
- [251222_general](reference/251222_general.md) — General Code Style Principles
- [251222_html-css](reference/251222_html-css.md) — Google HTML/CSS Style Guide Summary
- [251222_javascript](reference/251222_javascript.md) — Google JavaScript Style Guide Summary
- [251222_product-guidelines](reference/251222_product-guidelines.md) — Product Guidelines: PyLabPraxis
- [251222_product](reference/251222_product.md) — Product Guide: PyLabPraxis
- [251222_python](reference/251222_python.md) — Google Python Style Guide Summary
- [251222_tech-stack](reference/251222_tech-stack.md) — Technology Stack: PyLabPraxis
- [251222_typescript](reference/251222_typescript.md) — Google TypeScript Style Guide Summary
- [251222_workflow](reference/251222_workflow.md) — Project Workflow

## Roadmaps

### awesomation
- [260122_post-ship-roadmap](roadmaps/awesomation/260122_post-ship-roadmap.md) — Post-Ship Roadmap - v0.1-alpha
- [251230_roadmap](roadmaps/awesomation/251230_roadmap.md) — Praxis Development Roadmap

### pre-ship-cleanup
- [260120_roadmap](roadmaps/pre-ship-cleanup/260120_roadmap.md) — Project Roadmap

## Archive
- [agent-dirs-retired](archive/agent-dirs-retired.md) — Manifest of the 740 files removed or relocated when the three legacy .agent/ directories were retired, with the git commit to restore them from

## Misc
- [260126_e2e-new-02](misc/260126_e2e-new-02.md) — Jules session diff E2E-NEW-02 (session 16282140182043530519)
- [260126_e2e-new-03](misc/260126_e2e-new-03.md) — Jules session diff E2E-NEW-03 (session 8998018472489986175)
- [260126_e2e-viz-01](misc/260126_e2e-viz-01.md) — Jules session diff E2E-VIZ-01 (session 14797227623251883605)
- [260126_e2e-viz-02](misc/260126_e2e-viz-02.md) — Jules session diff E2E-VIZ-02 (session 12590817473184387784)
- [260126_e2e-viz-03](misc/260126_e2e-viz-03.md) — Jules session diff E2E-VIZ-03 (session 16182069641460709376)
- [260126_e2e-viz-04](misc/260126_e2e-viz-04.md) — Jules session diff E2E-VIZ-04 (session 9885909361909918124)
- [260126_jlite-01](misc/260126_jlite-01.md) — Jules session diff JLITE-01 (session 3622468687667268403)
- [260126_jlite-03](misc/260126_jlite-03.md) — Jules session diff JLITE-03 (session 14542845870678146245)
- [260126_opfs-01](misc/260126_opfs-01.md) — Jules session diff OPFS-01 (session 9221878143682473760)
- [260126_opfs-03](misc/260126_opfs-03.md) — Jules session diff OPFS-03 (session 14808794888910746056)
- [260126_refactor-01](misc/260126_refactor-01.md) — Jules session diff REFACTOR-01 (session 235373965227071886)
- [260126_refactor-02](misc/260126_refactor-02.md) — Jules session diff REFACTOR-02 (session 3806881592450903343)
- [260126_refactor-03](misc/260126_refactor-03.md) — Jules session diff REFACTOR-03 (session 13019827227538808257)
- [260126_split-01](misc/260126_split-01.md) — Jules session diff SPLIT-01 (session 9828431918057321321)
- [260126_split-02](misc/260126_split-02.md) — Jules session diff SPLIT-02 (session 1174395877673969907)
- [260126_split-04](misc/260126_split-04.md) — Jules session diff SPLIT-04 (session 8806860709165683043)
- [260126_split-05](misc/260126_split-05.md) — Jules session diff SPLIT-05 (session 7027017935549180084)
- [260126_split-06](misc/260126_split-06.md) — Jules session diff SPLIT-06 (session 2939224647793981217)
- [260114_compressed-archive](misc/260114_compressed-archive.md) — Compressed Archive Index

## Superpowers
> Skill outputs live in `.praxia/docs/superpowers/plans/` and `.praxia/docs/superpowers/specs/.
- [plans](superpowers/plans/) — brainstorming + writing-plans outputs
- [specs](superpowers/specs/) — specification outputs

