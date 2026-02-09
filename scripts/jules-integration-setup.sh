#!/usr/bin/env bash
set -euo pipefail

# Jules Integration — Worktree Setup
# Run from: /Users/mar/Projects/praxis
# Creates 4 worktrees, one per phase

PRAXIS="/Users/mar/Projects/praxis"
WT_DIR="$PRAXIS/.agent/.worktrees"
LOG_DIR="/tmp/jules-integration"
mkdir -p "$LOG_DIR"

cd "$PRAXIS"

echo "=== Cleaning up old jules-merge worktree ==="
git worktree remove "$WT_DIR/jules-merge" --force 2>/dev/null || true

echo ""
echo "=== Phase 1: Foundation (SQLite + Status Enum) ==="
git branch -D jules/phase1-foundation 2>/dev/null || true
git checkout -b jules/phase1-foundation main
git checkout main
git worktree add "$WT_DIR/jules-phase1" jules/phase1-foundation

echo ""
echo "=== Phase 2: E2E Infrastructure ==="
git branch -D jules/phase2-e2e-infra 2>/dev/null || true
git checkout -b jules/phase2-e2e-infra main
git checkout main
git worktree add "$WT_DIR/jules-phase2" jules/phase2-e2e-infra

echo ""
echo "=== Phase 3: Data Viz + Execution Flow ==="
git branch -D jules/phase3-dataviz-exec 2>/dev/null || true
git checkout -b jules/phase3-dataviz-exec main
git checkout main
git worktree add "$WT_DIR/jules-phase3" jules/phase3-dataviz-exec

echo ""
echo "=== Phase 4: Parameter Pipeline + Python Worker ==="
git branch -D jules/phase4-params-python 2>/dev/null || true
git checkout -b jules/phase4-params-python main
git checkout main
git worktree add "$WT_DIR/jules-phase4" jules/phase4-params-python

echo ""
echo "=== Attempting diff application (dry-run first) ==="

# Phase 1 diffs
echo ""
echo "--- Phase 1: Dry-run ---"
cd "$WT_DIR/jules-phase1"
git apply --check --stat /tmp/jules_8278805753300944958.diff 2>&1 | tee "$LOG_DIR/phase1-apply-check-8278.log" || echo "CONFLICTS in 8278805753300944958"
git apply --check --stat /tmp/jules_9713938321438428196.diff 2>&1 | tee "$LOG_DIR/phase1-apply-check-9713.log" || echo "CONFLICTS in 9713938321438428196"

# Phase 2 diffs
echo ""
echo "--- Phase 2: Dry-run ---"
cd "$WT_DIR/jules-phase2"
git apply --check --stat /tmp/jules_14767118960293034709.diff 2>&1 | tee "$LOG_DIR/phase2-apply-check-14767.log" || echo "CONFLICTS in 14767118960293034709"
git apply --check --stat /tmp/jules_17912267749298713430.diff 2>&1 | tee "$LOG_DIR/phase2-apply-check-17912.log" || echo "CONFLICTS in 17912267749298713430"

# Phase 3 diffs
echo ""
echo "--- Phase 3: Dry-run ---"
cd "$WT_DIR/jules-phase3"
git apply --check --stat /tmp/jules_1171211522435195679.diff 2>&1 | tee "$LOG_DIR/phase3-apply-check-1171.log" || echo "CONFLICTS in 1171211522435195679"
git apply --check --stat /tmp/jules_11861546015734261396.diff 2>&1 | tee "$LOG_DIR/phase3-apply-check-11861.log" || echo "CONFLICTS in 11861546015734261396"

# Phase 4 diffs
echo ""
echo "--- Phase 4: Dry-run ---"
cd "$WT_DIR/jules-phase4"
git apply --check --stat /tmp/jules_10098379133916241511.diff 2>&1 | tee "$LOG_DIR/phase4-apply-check-10098.log" || echo "CONFLICTS in 10098379133916241511"
git apply --check --stat /tmp/jules_4753493648741835765.diff 2>&1 | tee "$LOG_DIR/phase4-apply-check-4753.log" || echo "CONFLICTS in 4753493648741835765"
git apply --check --stat /tmp/jules_7539407275904149055.diff 2>&1 | tee "$LOG_DIR/phase4-apply-check-7539.log" || echo "CONFLICTS in 7539407275904149055"

cd "$PRAXIS"

echo ""
echo "=== Setup Complete ==="
echo "Worktrees created at:"
echo "  Phase 1: $WT_DIR/jules-phase1"
echo "  Phase 2: $WT_DIR/jules-phase2"
echo "  Phase 3: $WT_DIR/jules-phase3"
echo "  Phase 4: $WT_DIR/jules-phase4"
echo ""
echo "Dry-run logs at: $LOG_DIR/phase*-apply-check-*.log"
echo "Review those logs, then ask me to proceed with actual application + conflict resolution."
