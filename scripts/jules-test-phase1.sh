#!/usr/bin/env bash
set -euo pipefail

# Jules Integration — Phase 1 Tests
# Run AFTER applying Phase 1 diffs to jules-phase1 worktree
# Targets: SQLite, Assets, Status enum changes

WT="/Users/mar/Projects/praxis/.agent/.worktrees/jules-phase1"
WC="$WT/praxis/web-client"
LOG="/tmp/jules-integration"
mkdir -p "$LOG"

cd "$WC"

echo "==============================================="
echo "Phase 1 Tests — $(date)"
echo "==============================================="

echo ""
echo "--- 1a. Build check ---"
npx ng build 2>&1 | tail -20 | tee "$LOG/phase1-build.log"
BUILD_EXIT=${PIPESTATUS[0]}
echo "Build exit code: $BUILD_EXIT" >> "$LOG/phase1-build.log"

if [ "$BUILD_EXIT" -ne 0 ]; then
    echo "BUILD FAILED — check $LOG/phase1-build.log"
    exit 1
fi

echo ""
echo "--- 1b. SQLite unit tests ---"
npx vitest run --reporter=verbose src/app/core/services/sqlite/ 2>&1 | tee "$LOG/phase1-sqlite-unit.log"

echo ""
echo "--- 1c. Asset unit tests ---"
npx vitest run --reporter=verbose src/app/features/assets/ 2>&1 | tee "$LOG/phase1-assets-unit.log"

echo ""
echo "--- 1d. Asset inventory E2E ---"
npx playwright test e2e/specs/asset-inventory.spec.ts --reporter=list 2>&1 | tee "$LOG/phase1-assets-e2e.log"

echo ""
echo "==============================================="
echo "Phase 1 Complete — Logs in $LOG/phase1-*.log"
echo "==============================================="
