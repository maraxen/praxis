# wt-20260909-172820 Internal Docs

## Daily
- [260912_overnight-decisions](daily/260912_overnight-decisions.md) — Every decision the 260912 L5 loop made without a human gate: the REPL-refocus staleness dispositions, the #5110 selection, and the praxia debt filings.
- [260121_jules-session-triage](daily/260121_jules-session-triage.md)
- [260121_orchestrator-session-summary-20260121](daily/260121_orchestrator-session-summary-20260121.md)
- [260121_summary](daily/260121_summary.md)
- [260121_v01alpha-status-20260121](daily/260121_v01alpha-status-20260121.md)
- [260120_orchestration](daily/260120_orchestration.md)
- [260101_development-matrix](daily/260101_development-matrix.md)

## Handoffs
- [260131_e2e-autonomous-handoff](handoffs/260131_e2e-autonomous-handoff.md)
- [260131_ship-coordination-handoff](handoffs/260131_ship-coordination-handoff.md)
- [260129_jules-stage1-prompts](handoffs/260129_jules-stage1-prompts.md)
- [260129_praxis-handoff](handoffs/260129_praxis-handoff.md)
- [260128_e2e-database-seeding-handoff](handoffs/260128_e2e-database-seeding-handoff.md)
- [260128_e2e-stabilization-handoff](handoffs/260128_e2e-stabilization-handoff.md) — E2E Test Suite Stabilization - Session Handoff
- [260122_v01alpha-debug-handoff-20260121](handoffs/260122_v01alpha-debug-handoff-20260121.md)
- [260122_v01alpha-orchestrator-handoff-20260121-1845](handoffs/260122_v01alpha-orchestrator-handoff-20260121-1845.md)
- [260121_final-merge-handoff](handoffs/260121_final-merge-handoff.md)
- [260121_jules-handover-20260121](handoffs/260121_jules-handover-20260121.md)

## Plans
- [260912_repl-gate-manifest-scope-sprint136](plans/260912_repl-gate-manifest-scope-sprint136.md) — Sprint 136 plan and record: the repl.yml GATE G7 false positive that skipped all ten browser gates on the 4-PR stack, its two-defect root cause, the surface-dispatch fixer run, and the differential verification.
- [260824_repl-autocomplete-scope](plans/260824_repl-autocomplete-scope.md) — Scope and outcome for as-you-type completion in the JupyterLite PLR REPL; the planned jedi preload proved unnecessary
- [260817_praxis-repl-refocus-execution-plan](plans/260817_praxis-repl-refocus-execution-plan.md) — Dependency-ordered 8-phase execution plan composed from three adversarially-reviewed specs and five executed spikes, with per-phase gates, audit strategy, rollback, and an unproven-assumptions ledger.
- [260210_final-mvp-implementation-strategy](plans/260210_final-mvp-implementation-strategy.md)
- [260210_final-protocol-execution-fix-plan](plans/260210_final-protocol-execution-fix-plan.md)
- [260210_protocol-playground-fix-plan](plans/260210_protocol-playground-fix-plan.md)
- [260209_asset-wizard-deck-selector](plans/260209_asset-wizard-deck-selector.md) — Plan for adding a deck-selection step to the asset wizard, written ahead of the Feb 2026 E2E debugging wave
- [260131_ship-work-plan](plans/260131_ship-work-plan.md)
- [260128_e2e-test-suite-hardening-plan](plans/260128_e2e-test-suite-hardening-plan.md)
- [260126_opfs-only-refactor](plans/260126_opfs-only-refactor.md) — Plan to make OPFS the only browser-mode persistence layer, removing the legacy sql.js + IndexedDB path
- [260122_post-merge-checklist](plans/260122_post-merge-checklist.md)
- [260122_post-ship](plans/260122_post-ship.md)
- [260122_web-hid-shim](plans/260122_web-hid-shim.md)
- [260121_connection-persistence-tests](plans/260121_connection-persistence-tests.md)
- [260121_final-merge-plan](plans/260121_final-merge-plan.md)
- [260121_jules-integration-plan](plans/260121_jules-integration-plan.md)
- [260116_runway](plans/260116_runway.md)
- [260115_test-plan-v1](plans/260115_test-plan-v1.md)

## Specs
- [260914_first-run-auto-setup](specs/260914_first-run-auto-setup.md) — Spec for bootstrapping PyLabRobot automatically on every Pyodide kernel start, fail-closed and visible, with no user-typed setup
- [260825_copilot-pipeline-challenger](specs/260825_copilot-pipeline-challenger.md) — CHALLENGER-role findings against 260825_coxswain-phase-2-functiongemma-copilot-p.md. All file:line claims in the spec were re-verified against the tree on repl-fresh-boot; findings are ranked blocker/major/minor with cites and concrete fixes. No wholesale rewrite proposed.
- [260825_copilot-pipeline-defender](specs/260825_copilot-pipeline-defender.md) — DEFENDER counter-role review of 260825_coxswain-phase-2-functiongemma-copilot-p.md: steelman of D1-D10, robustness audit of load-bearing-but-fragile claims, critical-path feasibility re-verified against the tree, and resilience judgment of §8 counters. All repo cites re-verified 260825 on branch repl-fresh-boot.
- [260825_coxswain-phase-2-functiongemma-copilot-p](specs/260825_coxswain-phase-2-functiongemma-copilot-p.md) — Spec for the synthetic-data pipeline, functiongemma-270m-it fine-tune, browser serving via Transformers.js/WebGPU behind --with-coxswain, and ParseSource integration. REV 2: reconciled from challenger (2 blockers, 7 majors, 8 minors) and defender (11 robustness findings) reviews of 260825.
- [260824_coxswain-mvp-ux-spec](specs/260824_coxswain-mvp-ux-spec.md) — Implementable specification for the Coxswain propose/confirm, clarification, FFT-gate-extension and audit-trail surfaces: formalizes the eight negotiable UX axes (N1-N8) resolved in brainstorm session 48789b43 against the locked architecture (F1-F10), with fixer-ready work-item decomposition, correlation-ID contract, structural safety constraints mandated by the pre-mortem, and a risk table. Revised 260824 to close the adversarial review cycle (audits 260824_coxswain_spec_challenge / _defense) — see the Revision Log.
- [260824_coxswain-ux-open-design-axes-task-id-260](specs/260824_coxswain-ux-open-design-axes-task-id-260.md)
- [260817_spec-visualizer-transport-shim](specs/260817_spec-visualizer-transport-shim.md) — Adversarially-reviewed spec for the praxis REPL refocus (visualizer); converged=True after 1 round(s), verdict REVISE.
- [260817_spec-web-repl-extraction](specs/260817_spec-web-repl-extraction.md) — Adversarially-reviewed spec for the praxis REPL refocus (web-repl); converged=True after 1 round(s), verdict REVISE.
- [260817_spec-wheel-build-plr-upgrade](specs/260817_spec-wheel-build-plr-upgrade.md) — Adversarially-reviewed spec for the praxis REPL refocus (build-pipeline); converged=True after 2 round(s), verdict ACCEPT.
- [260122_inventory-wizard-design-spec](specs/260122_inventory-wizard-design-spec.md)

## Actuation Surfaces

## Audits
- [260912_sprint136-audit](audits/260912_sprint136-audit.md) — Sonnet praxia:reviewer report for commit e995de31, persisted verbatim: soundness answer, six-dimension scores, and the two non-blocking staleness suggestions with their resolution.
- [260209_web-client-technical-debt](audits/260209_web-client-technical-debt.md) — Web-client debt entries from Feb 2026, starting with replacing DeckCatalogService's hardcoded deck-type matching with programmatic PyLabRobot detection
- [260206_e2e-diff-report](audits/260206_e2e-diff-report.md) — File-by-file report of the 32-file E2E change set from the Feb 2026 Jules sessions
- [260206_e2e-jules-session-review](audits/260206_e2e-jules-session-review.md) — Final status review of the Jules E2E sessions for backlog #380/#426
- [260206_e2e-verification-feb03](audits/260206_e2e-verification-feb03.md)
- [260206_hardware-discovery-audit](audits/260206_hardware-discovery-audit.md)
- [260206_jules-audit-asset-wizards](audits/260206_jules-audit-asset-wizards.md) — Jules deep audit of the asset wizards (Feb 3, 2026; quality score 4/10)
- [260206_jules-audit-core-components](audits/260206_jules-audit-core-components.md) — Jules deep audit of the Docs and StateInspector core components (Feb 3, 2026; quality score 6.5/10)
- [260206_jules-audit-core-services](audits/260206_jules-audit-core-services.md) — Jules deep audit of the web-client core services (Feb 3, 2026; quality score 6/10)
- [260206_jules-audit-resource-index](audits/260206_jules-audit-resource-index.md) — Jules deep audit of the resource and index components (Feb 3, 2026; quality score 4/10)
- [260206_jules-audit-run-protocol](audits/260206_jules-audit-run-protocol.md) — Jules deep audit of the run-protocol feature (Feb 3, 2026; quality score 4/10)
- [260206_python-worker-audit](audits/260206_python-worker-audit.md)
- [260206_web-client-deep-audit-synthesis](audits/260206_web-client-deep-audit-synthesis.md) — Synthesis of 15+ Jules deep-audit sessions over the Angular web client (Feb 3, 2026)
- [260131_01-data-models](audits/260131_01-data-models.md)
- [260131_02-asset-wizard](audits/260131_02-asset-wizard.md)
- [260131_03-protocol-execution](audits/260131_03-protocol-execution.md)
- [260131_04-constraints](audits/260131_04-constraints.md)
- [260131_05-github-pages](audits/260131_05-github-pages.md)
- [260131_06-jupyterlite](audits/260131_06-jupyterlite.md)
- [260131_07-hardware-discovery](audits/260131_07-hardware-discovery.md)
- [260131_08-serialization](audits/260131_08-serialization.md)
- [260131_09-recommendations](audits/260131_09-recommendations.md)
- [260131_10-import-export](audits/260131_10-import-export.md)
- [260131_11-error-handling](audits/260131_11-error-handling.md)
- [260131_12-session-recovery](audits/260131_12-session-recovery.md)
- [260131_13-memory-management](audits/260131_13-memory-management.md)
- [260131_14-port-persistence](audits/260131_14-port-persistence.md)
- [260131_15-storage-quotas](audits/260131_15-storage-quotas.md)
- [260131_comprehensive-logic-audit](audits/260131_comprehensive-logic-audit.md)
- [260131_critical-features](audits/260131_critical-features.md)
- [260131_e2e-persistent-bugs](audits/260131_e2e-persistent-bugs.md)
- [260131_e2e-static-analysis](audits/260131_e2e-static-analysis.md)
- [260131_final-ship](audits/260131_final-ship.md)
- [260129_code-smells-audit](audits/260129_code-smells-audit.md)
- [260129_complexity-audit](audits/260129_complexity-audit.md)
- [260129_dead-code-audit](audits/260129_dead-code-audit.md)
- [260129_e2e-coverage-audit](audits/260129_e2e-coverage-audit.md)
- [260129_e2e-failures-audit-260129](audits/260129_e2e-failures-audit-260129.md)
- [260129_e2e-file-audits](audits/260129_e2e-file-audits.md)
- [260129_feature-architecture-audit](audits/260129_feature-architecture-audit.md)
- [260129_service-layer-audit](audits/260129_service-layer-audit.md)
- [260128_e2e-status](audits/260128_e2e-status.md)
- [260125_audit-01-run-protocol](audits/260125_audit-01-run-protocol.md)
- [260125_audit-03-protocol-execution](audits/260125_audit-03-protocol-execution.md)
- [260125_audit-06-persistence](audits/260125_audit-06-persistence.md)
- [260125_audit-07-jupyterlite](audits/260125_audit-07-jupyterlite.md)
- [260125_audit-08-ghpages-config](audits/260125_audit-08-ghpages-config.md)
- [260125_audit-09-direct-control](audits/260125_audit-09-direct-control.md)
- [260125_build-errors](audits/260125_build-errors.md)
- [260125_index](audits/260125_index.md)
- [260125_plan-for-remediation](audits/260125_plan-for-remediation.md)
- [260123_jupyterlite-ghpages-audit](audits/260123_jupyterlite-ghpages-audit.md)
- [260123_opfs-pyodide-audit](audits/260123_opfs-pyodide-audit.md)
- [260123_visual-audit-data-playground](audits/260123_visual-audit-data-playground.md)
- [260123_visual-audit-run-protocol](audits/260123_visual-audit-run-protocol.md)
- [260123_visual-audit-settings-workcell](audits/260123_visual-audit-settings-workcell.md)
- [260122_css-theming-audit](audits/260122_css-theming-audit.md)
- [260122_io-transport-audit](audits/260122_io-transport-audit.md)
- [260121_component-audit-assets](audits/260121_component-audit-assets.md)
- [260121_component-audit-playground](audits/260121_component-audit-playground.md)
- [260121_dependency-audit](audits/260121_dependency-audit.md)
- [260121_extracted-plr-audit](audits/260121_extracted-plr-audit.md)
- [260121_v01alpha-final-review-20260121](audits/260121_v01alpha-final-review-20260121.md)
- [260120_verification-report](audits/260120_verification-report.md)
- [260115_machine-sim-audit](audits/260115_machine-sim-audit.md)
- [260115_protocol-asset-audit](audits/260115_protocol-asset-audit.md)
- [260115_resource-error-log](audits/260115_resource-error-log.md)
- [260115_state-gap-analysis](audits/260115_state-gap-analysis.md)
- [260115_styling-audit-report](audits/260115_styling-audit-report.md)
- [260115_suite-comprehensiveness-analysis](audits/260115_suite-comprehensiveness-analysis.md)
- [260115_workcell-ui-audit](audits/260115_workcell-ui-audit.md)
- [260107_technical-debt](audits/260107_technical-debt.md)
- [251225_technical-debt](audits/251225_technical-debt.md)
- [251222_pyodide-integration-audit](audits/251222_pyodide-integration-audit.md)

## Research
- [260825_copilot-pipeline-recon](research/260825_copilot-pipeline-recon.md) — Verification of the 260824 scoping doc claims against current code, filling gaps for the next phase spec: tool-schema extraction seams, Chatterbox execution verification, protocol fixtures, PLR docs corpus, web-repl serving substrate, parse-source seam, and artifact-size constraints.
- [260825_functiongemma-training-serving-research](research/260825_functiongemma-training-serving-research.md) — Fine-tuning and browser-serving google/functiongemma-270m-it for a PyLabRobot lab-automation copilot
- [260824_gemma-finetuned-plr-voice-text-copilot-scoping](research/260824_gemma-finetuned-plr-voice-text-copilot-scoping.md) — Scoping assessment for a Gemma model fine-tuned to translate voice/text lab instructions into validated PyLabRobot calls inside the JupyterLite Playground rebase: training-data sourcing, browser deployment feasibility, clarification UX, and build-location recommendation.
- [260817_g2-spike-battery-verdict](research/260817_g2-spike-battery-verdict.md) — Adjudication of the five G2 criteria from spikes S-A/S-B/S-C/S-D/S-E/S-F, with independent spot-check output; overall PARTIAL-GO.
- [260817_spike-evidence-repl-refocus](research/260817_spike-evidence-repl-refocus.md) — Five executed browser/CPython spikes grounding the refocus specs; every finding tagged ran/read with verbatim commands and output.
- [260817_standalone-web-repl-extraction-shell-and-brainstorm](research/260817_standalone-web-repl-extraction-shell-and-brainstorm.md)
- [260817_visualizer-transport-shim-and-augmentati-2-brainstorm](research/260817_visualizer-transport-shim-and-augmentati-2-brainstorm.md)
- [260817_visualizer-transport-shim-and-augmentati-brainstorm](research/260817_visualizer-transport-shim-and-augmentati-brainstorm.md)
- [260817_wheel-build-plr-upgrade-and-version-cohe-2-brainstorm](research/260817_wheel-build-plr-upgrade-and-version-cohe-2-brainstorm.md)
- [260817_wheel-build-plr-upgrade-and-version-cohe-brainstorm](research/260817_wheel-build-plr-upgrade-and-version-cohe-brainstorm.md)
- [260131_asset-wizard-filtering-logic-recon](research/260131_asset-wizard-filtering-logic-recon.md)
- [260131_e2e-timeout-investigation](research/260131_e2e-timeout-investigation.md)
- [260131_file-splitting-report](research/260131_file-splitting-report.md)
- [260131_simulated-machine-instantiation-recon](research/260131_simulated-machine-instantiation-recon.md)
- [260129_data-viz-e2e-investigation](research/260129_data-viz-e2e-investigation.md)
- [260123_opfs-hardware-review](research/260123_opfs-hardware-review.md)
- [260122_asset-selection-analysis](research/260122_asset-selection-analysis.md)
- [260122_backend-categories-investigation](research/260122_backend-categories-investigation.md)
- [260122_deck-layout-coming-soon-investigation](research/260122_deck-layout-coming-soon-investigation.md) — Found the coming-soon message for non-Hamilton decks intentional: slot-based layout editing was unimplemented
- [260122_docs-404-investigation](research/260122_docs-404-investigation.md)
- [260122_frontend-backend-type-architecture](research/260122_frontend-backend-type-architecture.md)
- [260122_inventory-search-investigation](research/260122_inventory-search-investigation.md)
- [260122_inventory-wizard-recon](research/260122_inventory-wizard-recon.md)
- [260122_investigation-selective-transfer-params](research/260122_investigation-selective-transfer-params.md)
- [260122_jules-dispatch-recon-20260122](research/260122_jules-dispatch-recon-20260122.md)
- [260122_machine-args-configuration-investigation](research/260122_machine-args-configuration-investigation.md)
- [260122_machine-type-filtering-investigation](research/260122_machine-type-filtering-investigation.md)
- [260122_on-the-fly-definitions-investigation](research/260122_on-the-fly-definitions-investigation.md)
- [260122_oracle-asset-wizard-investigation](research/260122_oracle-asset-wizard-investigation.md)
- [260122_recon-asset-wizard-visual](research/260122_recon-asset-wizard-visual.md)
- [260122_recon-changelog-setup](research/260122_recon-changelog-setup.md)
- [260122_recon-documentation](research/260122_recon-documentation.md)
- [260122_recon-e2e-coverage](research/260122_recon-e2e-coverage.md)
- [260122_recon-e2e-infrastructure](research/260122_recon-e2e-infrastructure.md)
- [260122_recon-gitignore](research/260122_recon-gitignore.md)
- [260122_recon-global-shimming-status](research/260122_recon-global-shimming-status.md)
- [260122_recon-guided-setup-states](research/260122_recon-guided-setup-states.md)
- [260122_recon-hid-shim-status](research/260122_recon-hid-shim-status.md)
- [260122_recon-logo-branding](research/260122_recon-logo-branding.md)
- [260122_recon-playwright-jules](research/260122_recon-playwright-jules.md)
- [260122_recon-protocol-runner-visual](research/260122_recon-protocol-runner-visual.md)
- [260122_recon-repo-cleanup](research/260122_recon-repo-cleanup.md)
- [260122_recon-root-markdown](research/260122_recon-root-markdown.md)
- [260122_recon-socket-shim-status](research/260122_recon-socket-shim-status.md)
- [260122_recon-theme-variables](research/260122_recon-theme-variables.md)
- [260122_recon-versioning-strategy](research/260122_recon-versioning-strategy.md)
- [260122_relative-paths-recon-20260122](research/260122_relative-paths-recon-20260122.md)
- [260122_research-infinite-consumables](research/260122_research-infinite-consumables.md)
- [260122_resource-vs-machine-flow-investigation](research/260122_resource-vs-machine-flow-investigation.md)
- [260122_simulation-backend-dropdown-bug](research/260122_simulation-backend-dropdown-bug.md)
- [260122_simulation-selection-investigation](research/260122_simulation-selection-investigation.md)
- [260121_extracted-browser-interrupt](research/260121_extracted-browser-interrupt.md)
- [260121_extracted-geometry-heuristics](research/260121_extracted-geometry-heuristics.md)
- [260121_extracted-machine-registration](research/260121_extracted-machine-registration.md)

## Decisions
- [260817_repl-layout-and-delivery-mechanism](decisions/260817_repl-layout-and-delivery-mechanism.md) — ADR resolving the path collision between the three refocus specs by deciding what ships as a wheel and what ships as loose fetched files; includes the single-class-object invariant, the three-detector drift design, and the per-spec re-scope tables that Phase 3's gate checks.

## Preregistration

## Reference
- [260130_playwright-angular-best-practices-2026](reference/260130_playwright-angular-best-practices-2026.md)
- [260122_shared-array-buffer](reference/260122_shared-array-buffer.md)
- [260121_alembic-migration-guide](reference/260121_alembic-migration-guide.md)
- [260121_hardware-testing-guide](reference/260121_hardware-testing-guide.md)
- [260118_frontend-polish](reference/260118_frontend-polish.md)
- [260115_machine-sim-audit](reference/260115_machine-sim-audit.md)
- [260115_qa-interaction-checklist](reference/260115_qa-interaction-checklist.md)
- [260115_state-gap-analysis](reference/260115_state-gap-analysis.md)
- [260115_ui-guide](reference/260115_ui-guide.md)
- [260114_installation-browser](reference/260114_installation-browser.md)
- [260114_installation-lite](reference/260114_installation-lite.md)
- [260114_installation-production](reference/260114_installation-production.md)
- [260114_update-archive](reference/260114_update-archive.md)
- [260107_hardware-matrix](reference/260107_hardware-matrix.md)
- [260107_notes](reference/260107_notes.md)
- [260105_protocol-inference-sharp-bits](reference/260105_protocol-inference-sharp-bits.md)
- [260102_browser-script](reference/260102_browser-script.md)
- [260101_architecture](reference/260101_architecture.md)
- [251230_assets](reference/251230_assets.md)
- [251230_backend](reference/251230_backend.md)
- [251230_browser-mode](reference/251230_browser-mode.md)
- [251230_cli-commands](reference/251230_cli-commands.md)
- [251230_cmms-interface-design-research](reference/251230_cmms-interface-design-research.md)
- [251230_code-style](reference/251230_code-style.md)
- [251230_configuration](reference/251230_configuration.md)
- [251230_contributing](reference/251230_contributing.md)
- [251230_data-visualization](reference/251230_data-visualization.md)
- [251230_execution-flow](reference/251230_execution-flow.md)
- [251230_frontend](reference/251230_frontend.md)
- [251230_hardware-discovery](reference/251230_hardware-discovery.md)
- [251230_installation](reference/251230_installation.md)
- [251230_lims-ux-pattern-analysis](reference/251230_lims-ux-pattern-analysis.md)
- [251230_overview](reference/251230_overview.md)
- [251230_protocols](reference/251230_protocols.md)
- [251230_quickstart](reference/251230_quickstart.md)
- [251230_rest-api](reference/251230_rest-api.md)
- [251230_scientific-software-complexity-abstraction](reference/251230_scientific-software-complexity-abstraction.md)
- [251230_services](reference/251230_services.md)
- [251230_state-management](reference/251230_state-management.md)
- [251230_testing](reference/251230_testing.md)
- [251230_troubleshooting](reference/251230_troubleshooting.md)
- [251230_websocket-api](reference/251230_websocket-api.md)
- [251222_general](reference/251222_general.md)
- [251222_html-css](reference/251222_html-css.md)
- [251222_javascript](reference/251222_javascript.md)
- [251222_product-guidelines](reference/251222_product-guidelines.md)
- [251222_product](reference/251222_product.md)
- [251222_python](reference/251222_python.md)
- [251222_tech-stack](reference/251222_tech-stack.md)
- [251222_typescript](reference/251222_typescript.md)
- [251222_workflow](reference/251222_workflow.md)

## Roadmaps

### awesomation
- [260122_post-ship-roadmap](roadmaps/awesomation/260122_post-ship-roadmap.md)
- [251230_roadmap](roadmaps/awesomation/251230_roadmap.md)

### pre-ship-cleanup
- [260120_roadmap](roadmaps/pre-ship-cleanup/260120_roadmap.md)

## Archive
- [agent-dirs-retired](archive/agent-dirs-retired.md) — Manifest of the 740 files removed or relocated when the three legacy .agent/ directories were retired, with the git commit to restore them from

## Misc
- [260126_e2e-new-02](misc/260126_e2e-new-02.md)
- [260126_e2e-new-03](misc/260126_e2e-new-03.md)
- [260126_e2e-viz-01](misc/260126_e2e-viz-01.md)
- [260126_e2e-viz-02](misc/260126_e2e-viz-02.md)
- [260126_e2e-viz-03](misc/260126_e2e-viz-03.md)
- [260126_e2e-viz-04](misc/260126_e2e-viz-04.md)
- [260126_jlite-01](misc/260126_jlite-01.md)
- [260126_jlite-03](misc/260126_jlite-03.md)
- [260126_opfs-01](misc/260126_opfs-01.md)
- [260126_opfs-03](misc/260126_opfs-03.md)
- [260126_refactor-01](misc/260126_refactor-01.md)
- [260126_refactor-02](misc/260126_refactor-02.md)
- [260126_refactor-03](misc/260126_refactor-03.md)
- [260126_split-01](misc/260126_split-01.md)
- [260126_split-02](misc/260126_split-02.md)
- [260126_split-04](misc/260126_split-04.md)
- [260126_split-05](misc/260126_split-05.md)
- [260126_split-06](misc/260126_split-06.md)
- [260114_compressed-archive](misc/260114_compressed-archive.md)

## Superpowers
> Skill outputs live in `.praxia/docs/superpowers/plans/` and `.praxia/docs/superpowers/specs/.
- [plans](superpowers/plans/) — brainstorming + writing-plans outputs
- [specs](superpowers/specs/) — specification outputs

