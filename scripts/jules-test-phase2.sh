#!/usr/bin/env bash
set -euo pipefail

# Jules Integration — Phase 2 Tests
# Run AFTER applying Phase 2 diffs AND merging Phase 1 into main
# Targets: Run-protocol, wizard, navigation, fixtures

WT="/Users/mar/Projects/praxis/.agent/.worktrees/jules-phase2"
WC="$WT/praxis/web-client"
LOG="/tmp/jules-integration"
mkdir -p "$LOG"

cd "$WC"

echo "==============================================="
echo "Phase 2 Tests — $(date)"
echo "==============================================="

echo ""
echo "--- 2a. Build check ---"
npx ng build 2>&1 | tail -20 | tee "$LOG/phase2-build.log"
BUILD_EXIT=${PIPESTATUS[0]}
echo "Build exit code: $BUILD_EXIT" >> "$LOG/phase2-build.log"

if [ "$BUILD_EXIT" -ne 0 ]; then
    echo "BUILD FAILED — check $LOG/phase2-build.log"
    exit 1
fi

echo ""
echo "--- 2b. Run-protocol unit tests ---"
npx vitest run --reporter=verbose src/app/features/run-protocol/ 2>&1 | tee "$LOG/phase2-run-proto-unit.log"

echo ""
echo "--- 2c. Wizard interaction E2E ---"
npx playwright test e2e/specs/interactions/ --reporter=list 2>&1 | tee "$LOG/phase2-interactions-e2e.log"

echo ""
echo "==============================================="
echo "Phase 2 Complete — Logs in $LOG/phase2-*.log"
echo "==============================================="
