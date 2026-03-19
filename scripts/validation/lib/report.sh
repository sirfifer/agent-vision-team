#!/usr/bin/env bash
# report.sh -- JSON report generation helpers for validate-platform.sh
# Produces structured JSON output without requiring jq for generation.

set -euo pipefail

# Global state for building the report
declare -a _REPORT_CHECKS=()
declare -a _REPORT_REGRESSIONS=()
declare -a _REPORT_IMPROVEMENTS=()
_REPORT_PASSED=0
_REPORT_FAILED=0
_REPORT_SKIPPED=0
_REPORT_START_TIME=""
_REPORT_TIER=""
_REPORT_VERSION=""

report_init() {
    local tier="$1" version="$2"
    _REPORT_TIER="$tier"
    _REPORT_VERSION="$version"
    _REPORT_START_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    _REPORT_PASSED=0
    _REPORT_FAILED=0
    _REPORT_SKIPPED=0
    _REPORT_CHECKS=()
    _REPORT_REGRESSIONS=()
    _REPORT_IMPROVEMENTS=()
}

# Record a check result
# Usage: report_check <name> <category> <status> <duration_ms> <detail> [critical] [tracking_issue]
report_check() {
    local name="$1"
    local category="$2"
    local status="$3"       # PASSED, FAILED, SKIPPED
    local duration_ms="$4"
    local detail="$5"
    local critical="${6:-true}"
    local tracking_issue="${7:-}"

    case "$status" in
        PASSED)  ((_REPORT_PASSED++)) || true ;;
        FAILED)  ((_REPORT_FAILED++)) || true ;;
        SKIPPED) ((_REPORT_SKIPPED++)) || true ;;
    esac

    local tracking_field=""
    if [[ -n "$tracking_issue" ]]; then
        tracking_field=", \"tracking_issue\": \"$tracking_issue\""
    fi

    local escaped_detail
    escaped_detail=$(printf '%s' "$detail" | sed 's/\\/\\\\/g; s/"/\\"/g; s/\t/\\t/g' | tr '\n' ' ')

    _REPORT_CHECKS+=("{\"name\": \"$name\", \"category\": \"$category\", \"status\": \"$status\", \"duration_ms\": $duration_ms, \"detail\": \"$escaped_detail\", \"critical\": $critical${tracking_field}}")
}

# Record a regression (baseline was PASSED, now FAILED)
report_regression() {
    local name="$1" detail="$2"
    local escaped_detail
    escaped_detail=$(printf '%s' "$detail" | sed 's/\\/\\\\/g; s/"/\\"/g' | tr '\n' ' ')
    _REPORT_REGRESSIONS+=("{\"name\": \"$name\", \"detail\": \"$escaped_detail\"}")
}

# Record an improvement (baseline was FAILED, now PASSED)
report_improvement() {
    local name="$1" detail="$2"
    local escaped_detail
    escaped_detail=$(printf '%s' "$detail" | sed 's/\\/\\\\/g; s/"/\\"/g' | tr '\n' ' ')
    _REPORT_IMPROVEMENTS+=("{\"name\": \"$name\", \"detail\": \"$escaped_detail\"}")
}

# Compute overall status
_report_status() {
    if [[ $_REPORT_FAILED -eq 0 ]]; then
        echo "HEALTHY"
    else
        # Check if any failed checks are critical
        local has_critical_failure=false
        if [[ ${#_REPORT_CHECKS[@]:-0} -gt 0 ]]; then
            for check in "${_REPORT_CHECKS[@]}"; do
                if echo "$check" | grep -q '"status": "FAILED"' && echo "$check" | grep -q '"critical": true'; then
                    has_critical_failure=true
                    break
                fi
            done
        fi
        if $has_critical_failure; then
            echo "CRITICAL"
        else
            echo "DEGRADED"
        fi
    fi
}

# Generate the full JSON report
report_generate() {
    local end_time
    end_time=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    local total=$(( _REPORT_PASSED + _REPORT_FAILED + _REPORT_SKIPPED ))
    local status
    status=$(_report_status)
    local regression_count=0
    if [[ ${#_REPORT_REGRESSIONS[@]:-0} -gt 0 ]]; then
        regression_count=${#_REPORT_REGRESSIONS[@]}
    fi

    # Build checks array
    local checks_json=""
    local first=true
    if [[ ${#_REPORT_CHECKS[@]:-0} -gt 0 ]]; then
        for check in "${_REPORT_CHECKS[@]}"; do
            if $first; then
                checks_json="$check"
                first=false
            else
                checks_json="$checks_json, $check"
            fi
        done
    fi

    # Build regressions array
    local regressions_json=""
    first=true
    if [[ ${#_REPORT_REGRESSIONS[@]:-0} -gt 0 ]]; then
        for reg in "${_REPORT_REGRESSIONS[@]}"; do
            if $first; then
                regressions_json="$reg"
                first=false
            else
                regressions_json="$regressions_json, $reg"
            fi
        done
    fi

    # Build improvements array
    local improvements_json=""
    first=true
    if [[ ${#_REPORT_IMPROVEMENTS[@]:-0} -gt 0 ]]; then
        for imp in "${_REPORT_IMPROVEMENTS[@]}"; do
            if $first; then
                improvements_json="$imp"
                first=false
            else
                improvements_json="$improvements_json, $imp"
            fi
        done
    fi

    cat <<ENDJSON
{
  "run": {
    "timestamp": "$_REPORT_START_TIME",
    "completed": "$end_time",
    "claude_code_version": "$_REPORT_VERSION",
    "tier": "$_REPORT_TIER"
  },
  "summary": {
    "total": $total,
    "passed": $_REPORT_PASSED,
    "failed": $_REPORT_FAILED,
    "skipped": $_REPORT_SKIPPED,
    "regressions": $regression_count,
    "status": "$status"
  },
  "checks": [$checks_json],
  "regressions": [$regressions_json],
  "improvements": [$improvements_json]
}
ENDJSON
}

# Print a human-readable summary table to stderr
report_print_summary() {
    local status
    status=$(_report_status)
    local total=$(( _REPORT_PASSED + _REPORT_FAILED + _REPORT_SKIPPED ))

    echo "" >&2
    echo "========================================" >&2
    echo "  Platform Validation Report" >&2
    echo "  Claude Code $_REPORT_VERSION | Tier: $_REPORT_TIER" >&2
    echo "========================================" >&2
    echo "" >&2

    # Print each check
    if [[ ${#_REPORT_CHECKS[@]:-0} -eq 0 ]]; then
        echo "  (no checks run)" >&2
    fi
    for check in "${_REPORT_CHECKS[@]+"${_REPORT_CHECKS[@]}"}"; do
        [[ -z "$check" ]] && continue
        local name status_val
        name=$(echo "$check" | sed -n 's/.*"name": "\([^"]*\)".*/\1/p')
        status_val=$(echo "$check" | sed -n 's/.*"status": "\([^"]*\)".*/\1/p')
        local icon="?"
        case "$status_val" in
            PASSED)  icon="+" ;;
            FAILED)  icon="X" ;;
            SKIPPED) icon="-" ;;
        esac
        printf "  [%s] %s\n" "$icon" "$name" >&2
    done

    echo "" >&2
    echo "  Passed: $_REPORT_PASSED / $total" >&2
    echo "  Failed: $_REPORT_FAILED" >&2
    echo "  Skipped: $_REPORT_SKIPPED" >&2
    local _reg_count=0
    if [[ ${#_REPORT_REGRESSIONS[@]:-0} -gt 0 ]]; then _reg_count=${#_REPORT_REGRESSIONS[@]}; fi
    echo "  Regressions: $_reg_count" >&2
    echo "  Status: $status" >&2
    echo "========================================" >&2
}
