#!/bin/bash
# Dispatch E2E Enhancement tasks to Jules
# Captures session IDs and logs task mappings

set -e

STAGING_DIR=".agent/staging/e2e_enhancement"
LOG_FILE=".agent/staging/e2e_enhancement/jules-dispatch-log.md"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Initialize log file
cat > "$LOG_FILE" << EOF
# Jules E2E Enhancement Dispatch Log
**Dispatched:** $TIMESTAMP

## Session Mapping

| Session ID | Spec File | Status |
|------------|-----------|--------|
EOF

# Common context for all tasks
PRIOR_WORK="## Prior Work Completed
- Worker-DB import migration done (all specs now import from worker-db.fixture)
- Silent catch blocks enhanced with diagnostic logging
- New POMs created: PlaygroundPage, JupyterlitePage, InventoryDialogPage, wizard.helper.ts
- Existing POMs available: WizardPage, AssetsPage, MonitorPage, ProtocolPage, WelcomePage, SettingsPage"

# Function to dispatch a single task
dispatch_task() {
    local plan_file="$1"
    local spec_name=$(basename "$plan_file" | sed 's/-improvement-plan.md//')
    
    # Determine the actual spec file path
    local spec_file="praxis/web-client/e2e/specs/${spec_name}.spec.ts"
    
    # Handle interactions/ subdirectory
    if [[ "$spec_name" == interactions-* ]]; then
        local inner_name="${spec_name#interactions-}"
        spec_file="praxis/web-client/e2e/specs/interactions/${inner_name}.spec.ts"
    fi
    
    echo "Dispatching: $spec_name..."
    
    # Build the session prompt
    local prompt="Title: E2E Fix: ${spec_name}.spec.ts - Full improvement plan execution

$PRIOR_WORK

## File to Modify
$spec_file

## Requirements
Execute ALL phases from the improvement plan piped below.
Use existing POMs from e2e/page-objects/ where applicable.
Import test/expect from '../fixtures/worker-db.fixture' (already done, verify it's correct).

## Acceptance Criteria
- grep -c 'waitForTimeout' $spec_file = 0 (or justified with comment if unavoidable)
- grep -c 'force: true' $spec_file = 0 (or justified with comment if unavoidable)
- TypeScript compiles: npx tsc --noEmit
- Target baseline score improvement is achieved

## Full Improvement Plan (piped from stdin):
---
"

    # Dispatch to Jules and capture output (pipe combined header+content to stdin)
    local output
    output=$({
        echo "$prompt"
        cat "$plan_file"
    } | jules remote new 2>&1) || {
        echo "  ⚠️  Failed to dispatch $spec_name"
        echo "| FAILED | $spec_name | Error during dispatch |" >> "$LOG_FILE"
        return 1
    }
    
    # Extract session ID (long number at end of URL)
    local session_id
    session_id=$(echo "$output" | grep -oE '[0-9]{15,}' | tail -1)
    
    if [ -n "$session_id" ]; then
        echo "  ✓ Session ID: $session_id"
        echo "| $session_id | $spec_name | QUEUED |" >> "$LOG_FILE"
    else
        echo "  ⚠️  Could not extract session ID"
        echo "  Output: $output"
        echo "| UNKNOWN | $spec_name | Check manually |" >> "$LOG_FILE"
    fi
    
    # Small delay to avoid rate limiting
    sleep 2
}

# Main execution
echo "========================================"
echo "Jules E2E Enhancement Dispatch"
echo "========================================"
echo ""

# Get all improvement plan files
plans=$(find "$STAGING_DIR" -name "*-improvement-plan.md" -type f | sort)
total=$(echo "$plans" | wc -l | tr -d ' ')

echo "Found $total improvement plans to dispatch"
echo ""

count=0
for plan in $plans; do
    ((count++))
    echo "[$count/$total] $(basename "$plan")"
    dispatch_task "$plan"
    echo ""
done

echo "========================================"
echo "Dispatch complete!"
echo "Log file: $LOG_FILE"
echo "========================================"

# Append summary
cat >> "$LOG_FILE" << EOF

## Summary
- **Total dispatched:** $count
- **Timestamp:** $TIMESTAMP

## Next Steps
1. Monitor with: \`jules remote list --session 2>&1 | cat\`
2. Pull completed: \`jules remote pull --session <id> --apply\`
3. Review changes before committing
EOF
