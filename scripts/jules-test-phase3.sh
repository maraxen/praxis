#!/usr/bin/env bash
set -euo pipefail

# Jules Integration — Phase 3 Tests
# Run AFTER applying Phase 3 diffs AND merging Phases 1+2 into main
# Targets: Data-viz, execution monitor, deck-view

WT="/Users/mar/Projects/praxis/.agent/.worktrees/jules-phase3"
WC="$WT/praxis/web-client"
LOG="/tmp/jules-integration"
mkdir -p "$LOG"

cd "$WC"

echo "==============================================="
echo "Phase 3 Tests — $(date)"
echo "==============================================="

echo ""
echo "--- 3a. Build check ---"
npx ng build 2>&1 | tail -20 | tee "$LOG/phase3-build.log"
BUILD_EXIT=${PIPESTATUS[0]}
echo "Build exit code: $BUILD_EXIT" >> "$LOG/phase3-build.log"

if [ "$BUILD_EXIT" -ne 0 ]; then
    echo "BUILD FAILED — check $LOG/phase3-build.log"
    exit 1
fi

echo ""
echo "--- 3b. Execution monitor unit tests ---"
npx vitest run --reporter=verbose src/app/features/execution-monitor/ 2>&1 | tee "$LOG/phase3-monitor-unit.log"

echo ""
echo "--- 3c. Data visualization E2E ---"
npx playwright test e2e/specs/data-visualization.spec.ts --reporter=list 2>&1 | tee "$LOG/phase3-dataviz-e2e.log"

echo ""
echo "--- 3d. Viz review E2E ---"
npx playwright test e2e/specs/viz-review.spec.ts --reporter=list 2>&1 | tee "$LOG/phase3-vizreview-e2e.log"

echo ""
echo "--- 3e. Deck view interaction E2E ---"
npx playwright test e2e/specs/interactions/02-deck-view.spec.ts --reporter=list 2>&1 | tee "$LOG/phase3-deckview-e2e.log"

echo ""
echo "==============================================="
echo "Phase 3 Complete — Logs in $LOG/phase3-*.log"
echo "==============================================="
