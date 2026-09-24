---
title: 'Praxis Development Roadmap'
---

# Praxis Development Roadmap

**Last Updated**: 2026-01-13
**Purpose**: High-level strategic phases and milestones for release planning.

---

## Current Status

**Phase**: Pre-Alpha Stabilization
**Target Release**: v0.1.0-alpha

---

## Strategic Phases

### Phase 1: v0.1.0-alpha (Current Focus)

**Goal**: Browser-mode application fully functional with real hardware connectivity.

#### Core Functionality (Must Work)

- [ ] **Hardware Discovery & Connection** (Browser Mode)
  - WebSerial/WebUSB device enumeration working
  - Plate Reader validated (may need debugging after recent changes)
  - Hamilton Starlet validated
  - Connection persistence across sessions
- [ ] **Protocol Execution on Hardware** (Browser Mode)
  - Execute protocols on connected hardware from browser
  - State tracking during execution
  - Pause/resume/cancel flows
- [x] **Playground Fully Operational**
  - [x] Loads without manual intervention (no reload kernel / dismiss loading)
  - [🟡] Interactive hardware control working (In Progress)
  - [x] Asset inventory integration functional
- [ ] **Protocol Workflow Complete**
  - [x] Well selection triggering correctly
  - [x] Asset filtering to appropriate PLR classes
  - [x] End-to-end protocol run flow
- [x] **Model Unification (SQLModel)**
  - [x] Integrated SQLModel for unified domain models
  - [x] Removed legacy ORM/Pydantic duplication
  - [x] Implemented Soft Foreign Keys for Table-Per-Class inheritance

#### Agentic Development Tools (Internal)

- [ ] **Structured Agentic Multi-Stage Workflow**
  - Implement Inspect -> Plan -> Execute lifecycle
  - Integrate with Development Matrix and Roadmap

#### Bug Fixes Required (Prerequisites)

These issues from the development matrix must be resolved:

- [x] Protocol well selection not triggering
- [x] Playground initialization flow (WebSerial error)
- [x] Asset filtering to appropriate PLR class
- [x] Simulated backend clarity / demo naming cleanup
- [x] Asset management UX issues (backend selector, filters, registry)
- [x] Data visualization axis selects responding
- [x] Documentation accuracy (API docs, dead links, [x] Execution Flow Diagram)
- [x] UI polish items ([x] Duplicate Clear Button, [x] filter styling, [x] name truncation)

#### Quality Gates

- [ ] All P1 bugs resolved
- [ ] Hardware connectivity validated (Plate Reader + Hamilton Starlet)
- [ ] Happy path E2E tests passing
- [ ] Documentation reviewed and navigable

---

### Phase 2: v0.1.0-beta

**Goal**: Production mode validation and expanded testing.

**Core Requirements**:

- [ ] Production mode fully validated and documented
- [ ] Maintenance tracking system complete
- [ ] Import/export tested and documented
- [ ] Additional hardware backends as needed

**Quality Gates**:

- [ ] Production deployment guide complete
- [ ] Performance benchmarks documented

---

### Phase 3: v0.2.0

**Goal**: Enhanced user experience and advanced features.

**Potential Features**:

- [ ] Advanced protocol scheduling
- [ ] Multi-workcell support
- [ ] Cost optimization for consumables
- [ ] Device calibration profiles

---

## Long-Term Vision (v1.0+)

- **Flight Checklists & Interactive Error Recovery**: Interactive pre-run checks (hardware, reagents, placement) and robust error recovery workflows.
- **Extensibility Architecture**: Plugin system with 4 pillars — labware libraries (JSON/YAML), vendor instrument extensions, theming, and sandboxed application mods. See [extensibility.md](./backlog/extensibility.md).
- Real-time collaboration for protocol editing
- Advanced discrete event simulation scheduling
- Cloud deployment options
- Integration with external LIMS systems
- AI-assisted protocol generation

---

## Related Documents

- [DEVELOPMENT_MATRIX.md](./DEVELOPMENT_MATRIX.md) - Current iteration work items
- [backlog/](./backlog/) - Detailed issue tracking
