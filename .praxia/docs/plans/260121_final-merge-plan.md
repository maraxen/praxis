---
title: 'FINAL MERGE PLAN - v0.1-alpha (Praxis)'
---

# FINAL MERGE PLAN - v0.1-alpha (Praxis)

**Status**: APPROVED
**Date**: 2026-01-21
**Objective**: Prepare `angular_refactor` for merge into `main` release `v0.1-alpha`.

---

## 🛑 Principles

1. **No Hardcoded Vendor Lock-in**: Move away from Hamilton-only hardcoding. Use DB-driven positioning inference.
2. **Browser-Native Demos**: Simulation mode must work visually and functionally (no crashes, realistic data mocks).
3. **Deck Visibility**: Auto-placement must work in the wizard.
4. **Research First**: Complex architectural changes (Deck Abstraction) start with a research dispatch.

---

## 🗓 Phase 1: FAST INTEGRATION (Immediate)

*Goal: Clear the queue of completed Jules work and extracted logic.*

| ID | Task | Source | Target | Status |
|----|------|--------|--------|--------|
| **1.1** | **Apply Docstrings** | Session `1571850777...` | **Antigravity** (Pull) | *Queue* |
| **1.2** | **Pause/Resume Protocol** | Session `1748603980...` | **Antigravity** (Fixer) | *Ready* |
| **1.3** | **PLR Category Audit** | `extracted_plr_audit.md` | **Antigravity** (Fixer) | *Ready* |
| **1.4** | **Error Boundaries** | Session `7169150...` | **Jules** (`--apply`) | *Ready* |
| **1.5** | **Browser Interrupt** | `extracted_browser_interrupt.md` | **Antigravity** (Fixer) | *Ready* |
| **1.6** | **Geometry Heuristics** | `extracted_geometry_heuristics.md` | **Antigravity** (Fixer) | *Ready* |

---

## 🔬 Phase 2: DEEP RESEARCH (Concurrent with Phase 1)

*Goal: Design the solutions for the complex "must-haves" to avoid "patch" coding.*

### 2.1 Research: Multi-Vendor Deck & Positioning Architecture

**Context**: We need to support Opentrons and others, not just Hamilton. Logic should infer the positioning system from the database.
**Questions to Answer**:

- How to store rail definitions / slot coordinates generically in DB?
- How to associate a Machine -> Deck Definition -> Positioning System (Cartesian vs. Rails)?
- How to migrate `DeckCatalogService` hardcoding to a `DeckConfigurationService` backed by DB?
- Evaluate `hardware_discovery.py` and existing scaffolding.

### 2.2 Research: Browser-Mode Simulation Spec

**Context**: Browser demos are critical. Need realistic data flow, not `MOCK_DATA`.
**Questions to Answer**:

- How to define simulation contracts in Protocol definitions?
- How to generate realistic "fake" data for Plate Readers?
- How to handle liquid transfers in simulation (state tracking without hardware)?

### 2.3 Research: Standardized Tracers for Linked Indices

**Context**: Protocols need to trace source/dest well linkage.
**Questions to Answer**:

- How to implement `requires_linked_indices` using tracers?
- How to enforce this validation in the `ProtocolExecutionService`?

---

## 🛠 Phase 3: ARCHITECTURAL IMPLEMENTATION

*Goal: Build the "Proper" v0.1 features based on research.*

| ID | Task | Dependency | Risk |
|----|------|------------|------|
| **3.1** | **Generic Deck Service** | Research 2.1 | H |
| **3.2** | **Deck Auto-Placement** | Task 3.1 | M |
| **3.3** | **Infinite Consumables (Browser)** | None | L |
| **3.4** | **Linked Indices (Tracers)** | Research 2.3 | M |
| **3.5** | **Simulated Data Spec** | Research 2.2 | M |

**Feature Details**:

- **3.2 Auto-Placement**: Ensure wizard renders items in correct slots based on Protocol `deck_configuration`.
- **3.3 Infinite Consumables**: In `Browser` mode, `AssetService` should allow "Infinite" reuse of a consumable (e.g., TipRack) without depleting the DB count.

---

## ✅ Phase 4: POLISH & MERGE

*Goal: Final verification.*

1. **JSDoc Audit**: Ensure new services are documented.
2. **Repo Cleanup**: Remove orphan files.
3. **E2E Trace**: Run full Protocol Library -> Deck Setup -> Run Protocol -> Results flow.
4. **Merge**: `angular_refactor` -> `main`.

---

## 🚀 Execution Strategy

1. **Dispatch Phase 1 items** (Integration) immediately to clear the board.
2. **Dispatch Phase 2 items** (Research) in parallel.
3. **Review Research Findings** -> Create detailed specs for Phase 3.
4. **Execute Phase 3**.
