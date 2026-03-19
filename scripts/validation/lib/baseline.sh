#!/usr/bin/env bash
# baseline.sh -- Regression baseline management for validate-platform.sh
# Compares current results against stored baselines to detect regressions.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESULTS_DIR="$SCRIPT_DIR/../results"
BASELINES_FILE="$RESULTS_DIR/baselines.json"
HISTORY_FILE="$RESULTS_DIR/history.jsonl"
ALERTS_FILE="$RESULTS_DIR/alerts.jsonl"

# Ensure results directory exists
mkdir -p "$RESULTS_DIR"

# Save current run results as the new baseline
baseline_save() {
    local report_json="$1"
    echo "$report_json" > "$BASELINES_FILE"
    echo "Baseline saved to $BASELINES_FILE" >&2
}

# Append a run summary to history
history_append() {
    local report_json="$1"
    # Extract summary line
    local timestamp version tier total passed failed status
    timestamp=$(echo "$report_json" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['run']['timestamp'])" 2>/dev/null || echo "unknown")
    version=$(echo "$report_json" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['run']['claude_code_version'])" 2>/dev/null || echo "unknown")
    tier=$(echo "$report_json" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['run']['tier'])" 2>/dev/null || echo "unknown")
    total=$(echo "$report_json" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['summary']['total'])" 2>/dev/null || echo 0)
    passed=$(echo "$report_json" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['summary']['passed'])" 2>/dev/null || echo 0)
    failed=$(echo "$report_json" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['summary']['failed'])" 2>/dev/null || echo 0)
    status=$(echo "$report_json" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['summary']['status'])" 2>/dev/null || echo "UNKNOWN")

    local history_line="{\"timestamp\": \"$timestamp\", \"version\": \"$version\", \"tier\": \"$tier\", \"total\": $total, \"passed\": $passed, \"failed\": $failed, \"status\": \"$status\"}"
    echo "$history_line" >> "$HISTORY_FILE"
}

# Compare a check result against baseline and detect regression/improvement
# Returns: "regression", "improvement", "consistent", or "new"
baseline_compare() {
    local check_name="$1"
    local current_status="$2"

    if [[ ! -f "$BASELINES_FILE" ]]; then
        echo "new"
        return
    fi

    local baseline_status
    baseline_status=$(python3 -c "
import json, sys
try:
    with open('$BASELINES_FILE') as f:
        data = json.load(f)
    for check in data.get('checks', []):
        if check['name'] == '$check_name':
            print(check['status'])
            sys.exit(0)
    print('NOT_FOUND')
except Exception:
    print('ERROR')
" 2>/dev/null || echo "ERROR")

    if [[ "$baseline_status" == "NOT_FOUND" || "$baseline_status" == "ERROR" ]]; then
        echo "new"
    elif [[ "$baseline_status" == "PASSED" && "$current_status" == "FAILED" ]]; then
        echo "regression"
    elif [[ "$baseline_status" == "FAILED" && "$current_status" == "PASSED" ]]; then
        echo "improvement"
    else
        echo "consistent"
    fi
}

# Write an alert for critical failures
alert_write() {
    local check_name="$1"
    local detail="$2"
    local severity="${3:-critical}"

    local timestamp
    timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    local escaped_detail
    escaped_detail=$(printf '%s' "$detail" | sed 's/\\/\\\\/g; s/"/\\"/g' | tr '\n' ' ')

    local alert_line="{\"timestamp\": \"$timestamp\", \"severity\": \"$severity\", \"check\": \"$check_name\", \"detail\": \"$escaped_detail\"}"
    echo "$alert_line" >> "$ALERTS_FILE"
}

# Show recent history
history_show() {
    local count="${1:-30}"
    if [[ ! -f "$HISTORY_FILE" ]]; then
        echo "No history found." >&2
        return
    fi

    echo "" >&2
    echo "Last $count validation runs:" >&2
    echo "---" >&2
    tail -n "$count" "$HISTORY_FILE" | while IFS= read -r line; do
        local ts version status passed total
        ts=$(echo "$line" | python3 -c "import sys,json; print(json.load(sys.stdin)['timestamp'])" 2>/dev/null || echo "?")
        version=$(echo "$line" | python3 -c "import sys,json; print(json.load(sys.stdin)['version'])" 2>/dev/null || echo "?")
        status=$(echo "$line" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])" 2>/dev/null || echo "?")
        passed=$(echo "$line" | python3 -c "import sys,json; print(json.load(sys.stdin)['passed'])" 2>/dev/null || echo "?")
        total=$(echo "$line" | python3 -c "import sys,json; print(json.load(sys.stdin)['total'])" 2>/dev/null || echo "?")
        printf "  %s  v%s  %s/%s  %s\n" "$ts" "$version" "$passed" "$total" "$status" >&2
    done
}
