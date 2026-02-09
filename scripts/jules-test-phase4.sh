#!/usr/bin/env bash
set -euo pipefail

# Jules Integration — Phase 4 Tests
# Run AFTER applying Phase 4 diffs AND merging Phases 1+2+3 into main
# Targets: Full suite — parameter pipeline, wizard specs, Python worker

WT="/Users/mar/Projects/praxis/.agent/.worktrees/jules-phase4"
WC="$WT/praxis/web-client"
LOG="/tmp/jules-integration"
mkdir -p "$LOG"

cd "$WC"

echo "==============================================="
echo "Phase 4 Tests — $(date)"
echo "==============================================="

echo ""
echo "--- 4a. Build check ---"
npx ng build 2>&1 | tail -20 | tee "$LOG/phase4-build.log"
BUILD_EXIT=${PIPESTATUS[0]}
echo "Build exit code: $BUILD_EXIT" >> "$LOG/phase4-build.log"

if [ "$BUILD_EXIT" -ne 0 ]; then
    echo "BUILD FAILED — check $LOG/phase4-build.log"
    exit 1
fi

echo ""
echo "--- 4b. Full unit test suite ---"
npx vitest run --reporter=verbose 2>&1 | tee "$LOG/phase4-full-unit.log"

echo ""
echo "--- 4c. Full E2E suite ---"
npx playwright test --reporter=list 2>&1 | tee "$LOG/phase4-full-e2e.log"

echo ""
echo "==============================================="
echo "Phase 4 Complete — Logs in $LOG/phase4-*.log"
echo "==============================================="
