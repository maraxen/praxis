# Orchestration Learning Log

> Persistent memory for agent orchestration strategies, lessons, and evolution.

---

## 🎯 Purpose

To improve orchestration quality over time by tracking:
1. **Lessons Learned**: What went wrong/right in specific sessions.
2. **Delegation Patterns**: Which subagents handle specific tasks best.
3. **Evolution**: How the orchestration strategy changes based on evidence.

---

## 🔄 Process

### When to Update
- **Post-Session**: At the end of every significant session, review what happened.
- **After Failure**: If an agent got stuck, hallucinated, or broke the build.
- **After Success**: If a complex coordination worked perfectly.
- **After Surprise**: If an agent did something unexpected (good or bad).

### How to Update
1. **Add Lesson**: Add a row to the "Lessons Learned" table.
2. **Refine Patterns**: Update "Delegation Patterns" if a strategy is confirmed or debunked.
3. **Log Evolution**: If you change your global strategy (e.g., "Always use Oracle for planning"), add an entry to "Evolution Log".

### Integration
- **Start of Session**: Read this file to load the latest strategies into context.
- **End of Session**: Append new lessons before closing.

---

## 📚 Lessons Learned

| Date | Context | Outcome | Lesson | Action |
|------|---------|---------|--------|--------|
| 2024-01-15 | Debugging complex race condition | 🔴 Failure | Explorer agent got lost traversing too many files | Use `grep` tool first to narrow scope before dispatching Explorer |
| 2024-01-20 | Refactoring auth middleware | 🟢 Success | Atomic Git Commit skill prevented large breaking changes | Enforce `atomic-git-commit` for all refactoring tasks |
| 2024-01-22 | UI Polish for dashboard | 🟡 Partial | Designer agent created good CSS but broke React logic | Decouple logic and view: Have Designer output CSS/HTML, then Fixer integrate it |
| 2026-01-20 | E2E Testing Pyodide Output | 🟡 Partial | `console.log` listeners failed to catch Python stdout because stdout was piped to UI only | In E2E tests, check the UI output area (`.jp-OutputArea-output`) for Python logs, not the browser console |

---

## 🤝 Delegation Patterns

### ✅ Effective Strategies

**Pattern: The "Architect-Builder" Loop**
- **Use Case**: New feature implementation
- **Flow**:
  1. **Oracle**: Designs the interface and data model (writes `plan.md`).
  2. **User**: Approves plan.
  3. **Fixer**: Implements one component at a time.
  4. **Explorer**: Verifies file placement.
- **Why it works**: Prevents "coding into a corner" by establishing the plan first.

**Pattern: The "Research-First" Debug**
- **Use Case**: Obscure error messages
- **Flow**:
  1. **Librarian**: Searches docs/web for error text.
  2. **Explorer**: Locates relevant code.
  3. **Fixer**: Applies fix based on Librarian's findings.
- **Why it works**: Prevents Fixer from guessing/hallucinating fixes.

### ❌ Anti-Patterns

**Pattern: "The Hero Agent"**
- **Description**: Asking one agent (e.g., Fixer) to "Analyze, Plan, and Fix" a complex issue.
- **Failure Mode**: Agent gets overwhelmed, loses context, or makes shallow fixes.
- **Correction**: Split into specialized subtasks.

**Pattern: "Blind Handoff"**
- **Description**: Passing a task to an agent without providing file paths or recent context.
- **Failure Mode**: Agent wastes steps searching or hallucinates files.
- **Correction**: Always provide `file_paths` and `summary` in the dispatch prompt.

---

## 🤖 Agent Performance Notes

- **Explorer**:
  - *Strength*: fast at mapping directory structures.
  - *Weakness*: Can miss semantic connections if not given keywords.
- **Librarian**:
  - *Strength*: Good at synthesizing docs.
  - *Weakness*: Can be too verbose. Ask for "bullet points".
- **Oracle**:
  - *Strength*: High-level reasoning.
  - *Weakness*: Tends to over-engineer if not constrained.
- **Fixer**:
  - *Strength*: Code syntax and small logic.
  - *Weakness*: Often ignores system-wide implications. Needs supervision.

---

## 🧬 Evolution Log

### [2024-01-10] Initial System Setup
- **Trigger**: Project Initialization
- **Change**: Established basic 5-agent role structure (Explorer, Librarian, Oracle, Designer, Fixer).

### [2024-01-25] Documentation First Policy
- **Trigger**: Several sessions wasted due to outdated docs.
- **Change**: Added rule: "Librarian must verify documentation matches code before planning begins."
