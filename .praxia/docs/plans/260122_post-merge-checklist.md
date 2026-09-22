# Post-Merge Checklist

**Status:** 🟡 Pending Merge
**Created:** 2026-01-22
**Purpose:** Track all actions required immediately after `angular_refactor` → `main` merge

---

## 🚀 Immediate Post-Merge Actions (Day 1)

### 1. Project Rename

**Priority:** P0 - First thing
**Prompt:** `.agent/prompts/260122_post_merge_cleanup.md`

- [ ] Decide on new project name
- [ ] Execute rename across all files
- [ ] Verify build passes
- [ ] Commit rename changes

### 2. Branch Cleanup

**Priority:** P0 - Same session as rename
**Prompt:** `.agent/prompts/260122_post_merge_cleanup.md`

- [ ] Audit all branches
- [ ] Delete merged feature branches (via GitHub)
- [ ] Keep only: `main`, `github-pages`
- [ ] Verify no data loss from unmerged branches

### 3. Documentation Audit

**Priority:** P1

- [ ] Update README.md with new name/branding
- [ ] Verify github-pages documentation is current
- [ ] Update any outdated installation instructions
- [ ] Remove development-only notes from public docs

---

## 🧹 Codebase Cleanup (Week 1)

### 4. Remove Development Artifacts

- [ ] Delete `.agent/reports/` excess files (keep last 10 or relevant ones)
- [ ] Archive completed `.agent/tasks/` to `.agent/archive/`
- [ ] Clean up `.agent/prompts/` - archive completed prompts
- [ ] Remove any TODO/FIXME comments that are resolved
- [ ] Delete unused/orphan files

### 5. Console Log Cleanup

- [ ] Audit console.log statements
- [ ] Replace info logs with verbose/debug level
- [ ] Keep only warnings/errors in production
- [ ] Add log level configuration if not present

### 6. Comment/Documentation Cleanup

- [ ] Remove commented-out code blocks
- [ ] Update outdated JSDoc comments
- [ ] Verify all public APIs documented
- [ ] Remove obsolete inline TODOs

---

## 🔒 Release Preparation

### 7. Version Tagging

- [ ] Create `v0.1.0-alpha` tag on main
- [ ] Write release notes
- [ ] Update CHANGELOG.md if exists

### 8. Deployment Verification

- [ ] Verify github-pages builds correctly
- [ ] Test production build: `npm run build`
- [ ] Verify all environment configs correct

---

## 📊 Metrics & Status

### Files to Clean

| Directory | Action | Status |
|:----------|:-------|:-------|
| `.agent/reports/` | Archive old, keep recent | ⬜ |
| `.agent/tasks/` | Archive completed | ⬜ |
| `.agent/prompts/` | Archive completed | ⬜ |
| `.agent/backlog/` | Review, archive resolved | ⬜ |

### Branches to Delete

| Branch | Status | Merged Into | Action |
|:-------|:-------|:------------|:-------|
| (List after audit) | | | |

---

## 🔗 Related Documents

- [POST_SHIP_ROADMAP.md](./POST_SHIP_ROADMAP.md) - Items deferred to after ship
- [FINAL_MERGE_PLAN.md](./FINAL_MERGE_PLAN.md) - Pre-merge checklist
- [TECHNICAL_DEBT.md](./TECHNICAL_DEBT.md) - Tracked debt items

---

## Revision History

| Date | Changes |
|------|---------|
| 2026-01-22 | Initial creation |
