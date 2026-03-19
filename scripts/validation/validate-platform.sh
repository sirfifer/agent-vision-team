#!/usr/bin/env bash
# validate-platform.sh -- Platform dependency validation runner for AVT
#
# Hard-validates every Claude Code platform feature that AVT depends on.
# This tests the PLATFORM, not our code on top of it.
#
# Usage:
#   ./validate-platform.sh [OPTIONS]
#
# Options:
#   --tier quick|standard|full  Run checks up to this tier (default: standard)
#   --category <name>           Run only checks in this category
#   --check <name>              Run a single named check
#   --baseline                  Record current results as new baseline
#   --json                      Output machine-readable JSON only (no table)
#   --critical-only             Only run checks marked critical
#   --history                   Show trend for last 30 runs
#   --schedule                  Install launchd plist for periodic runs
#   --quiet                     Suppress per-check output (summary only)
#
# Tiers:
#   quick     (~5s)    Model aliases, version, MCP config, imports
#   standard  (~60s)   Hook firing, task system, MCP access, nested sessions
#   full      (~5min)  Agent Teams spawn, teammate MCP, teammate hooks

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
CHECKS_DIR="$SCRIPT_DIR/checks"
LIB_DIR="$SCRIPT_DIR/lib"

# Source libraries
source "$LIB_DIR/report.sh"
source "$LIB_DIR/baseline.sh"

# Defaults
TIER="standard"
CATEGORY=""
SINGLE_CHECK=""
SAVE_BASELINE=false
JSON_ONLY=false
CRITICAL_ONLY=false
SHOW_HISTORY=false
INSTALL_SCHEDULE=false
QUIET=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --tier)       TIER="$2"; shift 2 ;;
        --category)   CATEGORY="$2"; shift 2 ;;
        --check)      SINGLE_CHECK="$2"; shift 2 ;;
        --baseline)   SAVE_BASELINE=true; shift ;;
        --json)       JSON_ONLY=true; shift ;;
        --critical-only) CRITICAL_ONLY=true; shift ;;
        --history)    SHOW_HISTORY=true; shift ;;
        --schedule)   INSTALL_SCHEDULE=true; shift ;;
        --quiet)      QUIET=true; shift ;;
        -h|--help)
            sed -n '2,/^$/s/^# \{0,1\}//p' "$0"
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

# Handle --history
if $SHOW_HISTORY; then
    history_show 30
    exit 0
fi

# Handle --schedule
if $INSTALL_SCHEDULE; then
    PLIST_DIR="$HOME/Library/LaunchAgents"
    PLIST_FILE="$PLIST_DIR/com.avt.platform-validation.plist"
    mkdir -p "$PLIST_DIR"

    cat > "$PLIST_FILE" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.avt.platform-validation</string>
    <key>ProgramArguments</key>
    <array>
        <string>$SCRIPT_DIR/validate-platform.sh</string>
        <string>--tier</string>
        <string>quick</string>
        <string>--json</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>6</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>$SCRIPT_DIR/results/scheduled-latest.json</string>
    <key>StandardErrorPath</key>
    <string>$SCRIPT_DIR/results/scheduled-latest.log</string>
    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>
</dict>
</plist>
PLIST

    launchctl unload "$PLIST_FILE" 2>/dev/null || true
    launchctl load "$PLIST_FILE"
    echo "Scheduled daily quick validation at 6:00 AM." >&2
    echo "Plist: $PLIST_FILE" >&2
    echo "Results: $SCRIPT_DIR/results/scheduled-latest.json" >&2
    exit 0
fi

# Tier ordering for comparison
tier_level() {
    case "$1" in
        quick)    echo 1 ;;
        standard) echo 2 ;;
        full)     echo 3 ;;
        *)        echo 0 ;;
    esac
}

# Check if a tier is included in the current run
tier_included() {
    local check_tier="$1"
    local check_level
    check_level=$(tier_level "$check_tier")
    local run_level
    run_level=$(tier_level "$TIER")
    [[ $check_level -le $run_level ]]
}

# Get Claude Code version
get_claude_version() {
    claude --version 2>/dev/null | head -1 | sed 's/[^0-9.]//g' || echo "unknown"
}

# Run a single check script
# Usage: run_check <check_name> <check_script> <category> <critical> [args...]
run_check() {
    local name="$1"
    local script="$2"
    local category="$3"
    local critical="$4"
    shift 4

    if [[ ! -x "$CHECKS_DIR/$script" ]]; then
        report_check "$name" "$category" "SKIPPED" 0 "Check script not found: $script" "$critical"
        if ! $QUIET && ! $JSON_ONLY; then
            printf "  [-] %-45s SKIPPED (script not found)\n" "$name" >&2
        fi
        return
    fi

    local start_ms
    start_ms=$(python3 -c "import time; print(int(time.time()*1000))")

    local output=""
    local exit_code=0
    output=$("$CHECKS_DIR/$script" "$@" 2>&1) || exit_code=$?

    local end_ms
    end_ms=$(python3 -c "import time; print(int(time.time()*1000))")
    local duration_ms=$(( end_ms - start_ms ))

    local status="PASSED"
    if [[ $exit_code -ne 0 ]]; then
        status="FAILED"
    fi

    # Extract detail from output (first line)
    local detail
    detail=$(echo "$output" | head -1)
    [[ -z "$detail" ]] && detail="exit code $exit_code"

    report_check "$name" "$category" "$status" "$duration_ms" "$detail" "$critical"

    # Check for regression
    local comparison
    comparison=$(baseline_compare "$name" "$status")
    case "$comparison" in
        regression)
            report_regression "$name" "Was PASSED in baseline, now FAILED: $detail"
            if [[ "$critical" == "true" ]]; then
                alert_write "$name" "REGRESSION: $detail" "critical"
            fi
            ;;
        improvement)
            report_improvement "$name" "Was FAILED in baseline, now PASSED: $detail"
            ;;
    esac

    # Print progress
    if ! $QUIET && ! $JSON_ONLY; then
        local icon="?"
        case "$status" in
            PASSED) icon="+" ;;
            FAILED) icon="X" ;;
        esac
        local suffix=""
        if [[ "$comparison" == "regression" ]]; then
            suffix=" ** REGRESSION **"
        elif [[ "$comparison" == "improvement" ]]; then
            suffix=" (improved)"
        fi
        printf "  [%s] %-45s %s (%dms)%s\n" "$icon" "$name" "$status" "$duration_ms" "$suffix" >&2
    fi
}

# ============================================================================
# Main execution
# ============================================================================

CLAUDE_VERSION=$(get_claude_version)

if ! $JSON_ONLY; then
    echo "" >&2
    echo "AVT Platform Dependency Validation" >&2
    echo "Claude Code $CLAUDE_VERSION | Tier: $TIER" >&2
    echo "---" >&2
fi

report_init "$TIER" "$CLAUDE_VERSION"

# ---- Quick Tier ----
if tier_included "quick"; then
    if ! $JSON_ONLY; then echo "" >&2; echo "  [Quick Tier]" >&2; fi

    # Model resolution
    if [[ -z "$CATEGORY" || "$CATEGORY" == "model_resolution" ]]; then
        if [[ -z "$SINGLE_CHECK" || "$SINGLE_CHECK" == "model_alias_haiku" ]]; then
            run_check "model_alias_haiku" "cli_model_check.sh" "model_resolution" "true" "haiku"
        fi
        if [[ -z "$SINGLE_CHECK" || "$SINGLE_CHECK" == "model_alias_sonnet" ]]; then
            run_check "model_alias_sonnet" "cli_model_check.sh" "model_resolution" "true" "sonnet"
        fi
        if [[ -z "$SINGLE_CHECK" || "$SINGLE_CHECK" == "model_alias_opus" ]]; then
            run_check "model_alias_opus" "cli_model_check.sh" "model_resolution" "true" "opus"
        fi
        if [[ -z "$SINGLE_CHECK" || "$SINGLE_CHECK" == "model_identity_haiku" ]]; then
            if ! $CRITICAL_ONLY; then
                run_check "model_identity_haiku" "cli_model_identity.sh" "model_resolution" "false" "haiku"
            fi
        fi
        if [[ -z "$SINGLE_CHECK" || "$SINGLE_CHECK" == "model_identity_sonnet" ]]; then
            if ! $CRITICAL_ONLY; then
                run_check "model_identity_sonnet" "cli_model_identity.sh" "model_resolution" "false" "sonnet"
            fi
        fi
        if [[ -z "$SINGLE_CHECK" || "$SINGLE_CHECK" == "model_identity_opus" ]]; then
            if ! $CRITICAL_ONLY; then
                run_check "model_identity_opus" "cli_model_identity.sh" "model_resolution" "false" "opus"
            fi
        fi
    fi

    # CLI functionality
    if [[ -z "$CATEGORY" || "$CATEGORY" == "cli" ]]; then
        if [[ -z "$SINGLE_CHECK" || "$SINGLE_CHECK" == "claude_version_check" ]]; then
            run_check "claude_version_check" "version_check.sh" "cli" "true" "2.1.33"
        fi
        if [[ -z "$SINGLE_CHECK" || "$SINGLE_CHECK" == "claude_print_works" ]]; then
            run_check "claude_print_works" "cli_print_check.sh" "cli" "true"
        fi
        if [[ -z "$SINGLE_CHECK" || "$SINGLE_CHECK" == "claude_print_model_flag" ]]; then
            run_check "claude_print_model_flag" "cli_print_model_flag.sh" "cli" "true"
        fi
    fi

    # MCP config
    if [[ -z "$CATEGORY" || "$CATEGORY" == "mcp" ]]; then
        if [[ -z "$SINGLE_CHECK" || "$SINGLE_CHECK" == "mcp_user_scope_config" ]]; then
            run_check "mcp_user_scope_config" "mcp_config_check.sh" "mcp" "true"
        fi
        if [[ -z "$SINGLE_CHECK" || "$SINGLE_CHECK" == "mcp_server_importable" ]]; then
            run_check "mcp_server_importable" "mcp_import_check.sh" "mcp" "true"
        fi
        if [[ -z "$SINGLE_CHECK" || "$SINGLE_CHECK" == "mcp_tool_search_active" ]]; then
            if ! $CRITICAL_ONLY; then
                run_check "mcp_tool_search_active" "mcp_tool_search_check.sh" "mcp" "false"
            fi
        fi
    fi

    # Environment
    if [[ -z "$CATEGORY" || "$CATEGORY" == "environment" ]]; then
        if [[ -z "$SINGLE_CHECK" || "$SINGLE_CHECK" == "settings_env_override" ]]; then
            if ! $CRITICAL_ONLY; then
                run_check "settings_env_override" "env_override_check.sh" "environment" "false"
            fi
        fi
    fi
fi

# ---- Standard Tier ----
if tier_included "standard"; then
    if ! $JSON_ONLY; then echo "" >&2; echo "  [Standard Tier]" >&2; fi

    # CLI
    if [[ -z "$CATEGORY" || "$CATEGORY" == "cli" ]]; then
        if [[ -z "$SINGLE_CHECK" || "$SINGLE_CHECK" == "nested_session_detection" ]]; then
            run_check "nested_session_detection" "nested_session_check.sh" "cli" "true"
        fi
    fi

    # Hooks
    if [[ -z "$CATEGORY" || "$CATEGORY" == "hooks" ]]; then
        if [[ -z "$SINGLE_CHECK" || "$SINGLE_CHECK" == "hook_post_tool_use_fires" ]]; then
            run_check "hook_post_tool_use_fires" "hook_fire_check.sh" "hooks" "true" "PostToolUse" "TaskCreate"
        fi
        if [[ -z "$SINGLE_CHECK" || "$SINGLE_CHECK" == "hook_pre_tool_use_fires" ]]; then
            run_check "hook_pre_tool_use_fires" "hook_fire_check.sh" "hooks" "true" "PreToolUse" "Write"
        fi
        if [[ -z "$SINGLE_CHECK" || "$SINGLE_CHECK" == "hook_session_start_compact" ]]; then
            run_check "hook_session_start_compact" "hook_fire_check.sh" "hooks" "true" "SessionStart" "compact"
        fi
        if [[ -z "$SINGLE_CHECK" || "$SINGLE_CHECK" == "hook_exit_code_blocking" ]]; then
            run_check "hook_exit_code_blocking" "hook_exit_code_check.sh" "hooks" "true"
        fi
        if [[ -z "$SINGLE_CHECK" || "$SINGLE_CHECK" == "hook_subagent_inheritance" ]]; then
            run_check "hook_subagent_inheritance" "hook_subagent_check.sh" "hooks" "true"
        fi
    fi

    # MCP access
    if [[ -z "$CATEGORY" || "$CATEGORY" == "mcp" ]]; then
        if [[ -z "$SINGLE_CHECK" || "$SINGLE_CHECK" == "mcp_direct_session_access" ]]; then
            run_check "mcp_direct_session_access" "mcp_session_access_check.sh" "mcp" "true" "direct"
        fi
        if [[ -z "$SINGLE_CHECK" || "$SINGLE_CHECK" == "mcp_subagent_access" ]]; then
            run_check "mcp_subagent_access" "mcp_session_access_check.sh" "mcp" "true" "subagent"
        fi
    fi

    # Tasks
    if [[ -z "$CATEGORY" || "$CATEGORY" == "tasks" ]]; then
        if [[ -z "$SINGLE_CHECK" || "$SINGLE_CHECK" == "task_create_produces_files" ]]; then
            run_check "task_create_produces_files" "task_create_check.sh" "tasks" "true"
        fi
        if [[ -z "$SINGLE_CHECK" || "$SINGLE_CHECK" == "task_blocked_by_works" ]]; then
            run_check "task_blocked_by_works" "task_blocked_by_check.sh" "tasks" "true"
        fi
    fi

    # Agent Teams (standard checks)
    if [[ -z "$CATEGORY" || "$CATEGORY" == "agent_teams" ]]; then
        if [[ -z "$SINGLE_CHECK" || "$SINGLE_CHECK" == "agent_teams_env_var" ]]; then
            run_check "agent_teams_env_var" "agent_teams_env_check.sh" "agent_teams" "true"
        fi
        if [[ -z "$SINGLE_CHECK" || "$SINGLE_CHECK" == "agent_defs_as_teammates" ]]; then
            if ! $CRITICAL_ONLY; then
                run_check "agent_defs_as_teammates" "agent_defs_teammate_check.sh" "agent_teams" "false"
            fi
        fi
    fi

    # Environment
    if [[ -z "$CATEGORY" || "$CATEGORY" == "environment" ]]; then
        if [[ -z "$SINGLE_CHECK" || "$SINGLE_CHECK" == "auto_memory_loading" ]]; then
            if ! $CRITICAL_ONLY; then
                run_check "auto_memory_loading" "auto_memory_check.sh" "environment" "false"
            fi
        fi
    fi
fi

# ---- Full Tier ----
if tier_included "full"; then
    if ! $JSON_ONLY; then echo "" >&2; echo "  [Full Tier]" >&2; fi

    # Agent Teams (full checks)
    if [[ -z "$CATEGORY" || "$CATEGORY" == "agent_teams" ]]; then
        if [[ -z "$SINGLE_CHECK" || "$SINGLE_CHECK" == "agent_teams_task_sharing" ]]; then
            run_check "agent_teams_task_sharing" "agent_teams_task_check.sh" "agent_teams" "true"
        fi
        if [[ -z "$SINGLE_CHECK" || "$SINGLE_CHECK" == "agent_teams_mcp_access" ]]; then
            run_check "agent_teams_mcp_access" "agent_teams_mcp_check.sh" "agent_teams" "true"
        fi
        if [[ -z "$SINGLE_CHECK" || "$SINGLE_CHECK" == "agent_teams_hook_inheritance" ]]; then
            run_check "agent_teams_hook_inheritance" "agent_teams_hook_check.sh" "agent_teams" "true"
        fi
    fi

    # Hooks (full checks)
    if [[ -z "$CATEGORY" || "$CATEGORY" == "hooks" ]]; then
        if [[ -z "$SINGLE_CHECK" || "$SINGLE_CHECK" == "hook_teammate_idle_fires" ]]; then
            run_check "hook_teammate_idle_fires" "hook_fire_check.sh" "hooks" "true" "TeammateIdle"
        fi
        if [[ -z "$SINGLE_CHECK" || "$SINGLE_CHECK" == "hook_task_completed_fires" ]]; then
            run_check "hook_task_completed_fires" "hook_fire_check.sh" "hooks" "true" "TaskCompleted"
        fi
    fi
fi

# ============================================================================
# Generate report
# ============================================================================

REPORT_JSON=$(report_generate)

# Save to history
history_append "$REPORT_JSON"

# Save baseline if requested
if $SAVE_BASELINE; then
    baseline_save "$REPORT_JSON"
fi

# Output
if $JSON_ONLY; then
    echo "$REPORT_JSON"
else
    report_print_summary
    echo "" >&2
    echo "Full JSON report written to history." >&2
    if $SAVE_BASELINE; then
        echo "Baseline saved." >&2
    fi
fi

# Exit with appropriate code
FAILED_COUNT=$(echo "$REPORT_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['summary']['failed'])" 2>/dev/null || echo 0)
if [[ "$FAILED_COUNT" -gt 0 ]]; then
    # Check if any critical failures
    HAS_CRITICAL=$(echo "$REPORT_JSON" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for c in data['checks']:
    if c['status'] == 'FAILED' and c.get('critical', True):
        print('yes')
        sys.exit(0)
print('no')
" 2>/dev/null || echo "no")
    if [[ "$HAS_CRITICAL" == "yes" ]]; then
        exit 2  # Critical failure
    else
        exit 1  # Non-critical failure
    fi
fi
exit 0
