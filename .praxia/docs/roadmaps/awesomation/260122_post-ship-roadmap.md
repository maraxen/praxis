---
title: 'Post-Ship Roadmap - v0.1-alpha'
---

# Post-Ship Roadmap - v0.1-alpha

**Created**: 2026-01-22
**Purpose**: Prioritized work items for after v0.1-alpha merge and ship.
**Status**: Planning

---

## 🚀 Priority 0: Immediate Post-Ship (Week 1)

### P0-1: Jules Environment & Dev Workflow Setup

**Why First**: Enables parallel development velocity for all subsequent work.

- [ ] Create unified Makefile at project root
- [ ] `make dev-browser` / `make dev-lite` / `make dev-production` targets
- [ ] bunx/npx/npm standardization
- [ ] Jules-compatible workspace configuration
- [ ] Document in README.md

**Dependencies**: None
**Estimated Effort**: 1-2 days

---

## 🔧 Priority 1: Architecture & Testing

### P1-1: Connection Mutex (Hardware Exclusivity)

**Why**: Prevents race conditions when Direct Control, Protocol Runner, and JupyterLite all try to connect to the same hardware.

- [ ] Create `HardwareConnectionManager` service
- [ ] Implement connection locks with ownership tracking
- [ ] Add UI indicators for which component owns connection
- [ ] Graceful handoff or error messaging

**Technical Notes**:

- Consider using BroadcastChannel for cross-tab awareness
- Direct Control should release lock on tab blur/close

### P1-2: Browser/Lite/Production Mode Easy Setup

**Why**: Currently requires manual configuration; should be one-command.

- [ ] Detect mode from environment or URL parameter
- [ ] Auto-configure services based on mode
- [ ] Clear visual indicator of current mode
- [ ] Mode switcher in dev tools (dev only)

### P1-3: Pyodide Environment Test Suite (Critical Paths)

**Why**: Ensure all three Pyodide environments (Direct Control, Protocol Runner, JupyterLite) work reliably.

Critical test scenarios:

- [ ] Shim loading verification (WebUSB, WebSerial, WebFTDI)
- [ ] Hardware connection flow
- [ ] Protocol execution end-to-end
- [ ] User interaction (pause/confirm/input)
- [ ] Error handling and recovery

---

## 🎨 Priority 2: Polish & UX

### P2-1: Console Warning Cleanup

**Why**: Current robot connection produces excessive warnings that obscure real issues.

- [ ] Audit console output during connection
- [ ] Move info logs to verbose/debug stream
- [ ] Keep only warnings/errors in default stream
- [ ] Add log level configuration

### P2-2: Close Connection Confirmation Dialog

**Why**: Prevents accidental disconnection during active operations.

- [ ] Add confirmation dialog to close/disconnect action
- [ ] Show active operation status if any
- [ ] Option to force-close with warning

### P2-3: Auto-Setup for Discovered Hardware (Jupyter & Direct Control)

**Why**: Reduce friction - if hardware is discovered, auto-inject initialization code.

- [ ] Query registered machines on environment init
- [ ] Generate setup code for each machine
- [ ] Inject into Jupyter bootstrap or Direct Control init
- [ ] Related: Technical Debt #28

### P2-4: Broadcast Channel Cleanup (Jupyter)

**Why**: Current setup is convoluted and hard to maintain.

- [ ] Audit current BroadcastChannel usage in PlaygroundComponent
- [ ] Simplify registration flow
- [ ] Ensure consistent message routing (worker vs channel)
- [ ] Document the messaging architecture

### P2-5: Single Cloudpickled Function for Jupyter Env

**Why**: Notebook appearance should be clean; initialization code is noisy.

- [ ] Consolidate bootstrap into single pickled function
- [ ] Add validation hooks within function
- [ ] Enable automated testing of environment
- [ ] Expose minimal API for notebook use

### P2-6: Visual Filter Shared Component Tweaks

**Why**: UI polish, but depends on frontend workflow adjustments.

Prerequisites:

- [ ] Adjust frontend polish workflows
- [ ] Update design tokens if needed

Then:

- [ ] Refine filter styling
- [ ] Improve responsive behavior
- [ ] Add animation transitions

### P2-7: Deck Resource State Visual (Guided Setup)

**Why**: Better visual feedback during setup process.

Current → Target:

- Before confirmation: Dashed outline, transparent fill
- After confirmation: Solid outline, filled
- Dynamic updates as user proceeds through steps

### P2-8: Table Mode View Details on Row Click

**Why**: Improved discoverability of item details.

- [ ] Implement row click handler
- [ ] Show detail panel/drawer
- [ ] Maintain table scroll position

### P2-9: Eliminate "Demo Workcell"

**Why**: Replace with proper workcell configuration system.

- [ ] Create "Configure Workcell" button
- [ ] Build workcell configuration menu
- [ ] Workcell creation/editing tool
- [ ] Remove hardcoded demo references

### P2-10: FunctionDataOutput and WellData Audit

**Why**: Proper data visualization infrastructure.

- [ ] Audit current dataviz logic
- [ ] Implement proper FunctionDataOutput handling
- [ ] WellData integration for plate visualizations
- [ ] Document data flow patterns

---

## 📈 Priority 3: Long-Term Roadmap Items

### UI Hints from Tracer/Simulation

**Requires Significant Research & Planning**

Goal: Automatically infer value ranges for inputs using tracer/simulation identified bounds.

Research Questions:

- How to extract bounds from simulation traces?
- How to map bounds to UI constraints?
- How to handle dynamic/conditional bounds?

Implementation:

- [ ] Research phase (recon dispatch)
- [ ] Architecture design
- [ ] Prototype with simple numeric inputs
- [ ] Extend to complex parameter types

### Sliders and Engaging UX for Numeric Variables

**Depends on**: UI Hints from Tracer

- [ ] Design slider component variants
- [ ] Integrate with traced bounds
- [ ] Animation and interaction polish

### ItemizedResource Generalization

**Codebase-wide refactor**

Current: Wells are treated specially throughout codebase
Target: Generic ItemizedResource abstraction

- [ ] Audit all well-specific code
- [ ] Design ItemizedResource interface
- [ ] Phased migration plan
- [ ] Backward compatibility layer

### Generalize Parameter Linking via Symbolic Tracing

**Already tracked as Technical Debt #27**

See debt item for full specification.

---

## 🔄 Ongoing: Test Coverage Expansion

Jules will be instrumental here. Priorities:

1. E2E critical paths
2. Pyodide environment tests
3. Hardware integration tests
4. UI component tests

---

## 📋 Related Documents

- [TECHNICAL_DEBT.md](./TECHNICAL_DEBT.md) - Tracked debt items
- [FINAL_MERGE_PLAN.md](./FINAL_MERGE_PLAN.md) - Pre-merge checklist
- [ROADMAP.md](./ROADMAP.md) - Strategic phases

---

## Revision History

| Date | Changes |
|------|---------|
| 2026-01-22 | Initial creation from orchestration session |
