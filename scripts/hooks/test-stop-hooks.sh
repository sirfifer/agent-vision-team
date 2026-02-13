#!/usr/bin/env bash
# ============================================================================
# Experiment 3: Verify Stop and SubagentStop hook input schema
#
# Registers minimal hooks that dump their stdin JSON to debug files,
# then runs Claude sessions to trigger them.
#
# Usage:
#   ./scripts/hooks/test-stop-hooks.sh              # Run both tests
#   ./scripts/hooks/test-stop-hooks.sh --stop-only   # Only test Stop hook
#   ./scripts/hooks/test-stop-hooks.sh --keep         # Preserve workspace
# ============================================================================
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# ── Defaults ────────────────────────────────────────────────────────────────
MODE="both"
KEEP=false
MODEL="haiku"

# ── Parse args ──────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case $1 in
        --stop-only)    MODE="stop"; shift ;;
        --subagent-only) MODE="subagent"; shift ;;
        --keep)         KEEP=true; shift ;;
        --model)        MODEL="$2"; shift 2 ;;
        *)              echo "Unknown arg: $1"; exit 1 ;;
    esac
done

# ── Workspace setup ─────────────────────────────────────────────────────────
TIMESTAMP=$(date +%s)
WORKSPACE=$(mktemp -d /tmp/avt-stop-hook-exp-XXXXXX)
DEBUG_DIR="${PROJECT_DIR}/.avt/debug"

mkdir -p "$WORKSPACE" "$DEBUG_DIR"

echo "============================================================"
echo "  Stop/SubagentStop Hook Schema Experiment"
echo "============================================================"
echo "  Mode:      ${MODE}"
echo "  Model:     ${MODEL}"
echo "  Workspace: ${WORKSPACE}"
echo ""

# ── Create hook dump scripts ────────────────────────────────────────────────
# These minimal scripts just capture stdin JSON to a file

STOP_DUMP="${WORKSPACE}/dump-stop-hook.sh"
cat > "$STOP_DUMP" << 'HOOKEOF'
#!/usr/bin/env bash
# Dump Stop hook input to a debug file
INPUT=$(cat)
TIMESTAMP=$(date +%s)
DEBUG_DIR="${CLAUDE_PROJECT_DIR:-.}/.avt/debug"
mkdir -p "$DEBUG_DIR"
echo "$INPUT" | python3 -c "
import json, sys
try:
    data = json.loads(sys.stdin.read())
    with open('${DEBUG_DIR}/stop-hook-input-${TIMESTAMP}.json', 'w') as f:
        json.dump(data, f, indent=2)
    # Also append to a combined log
    with open('${DEBUG_DIR}/stop-hook-inputs.jsonl', 'a') as f:
        f.write(json.dumps(data) + '\n')
except Exception as e:
    with open('${DEBUG_DIR}/stop-hook-error.txt', 'a') as f:
        f.write(f'Error: {e}\nRaw input: {repr(sys.stdin.read())}\n')
"
# Always exit 0 so we don't block Claude from stopping
exit 0
HOOKEOF
chmod +x "$STOP_DUMP"

SUBAGENT_STOP_DUMP="${WORKSPACE}/dump-subagent-stop-hook.sh"
cat > "$SUBAGENT_STOP_DUMP" << 'HOOKEOF'
#!/usr/bin/env bash
# Dump SubagentStop hook input to a debug file
INPUT=$(cat)
TIMESTAMP=$(date +%s)
DEBUG_DIR="${CLAUDE_PROJECT_DIR:-.}/.avt/debug"
mkdir -p "$DEBUG_DIR"
echo "$INPUT" | python3 -c "
import json, sys
try:
    data = json.loads(sys.stdin.read())
    with open('${DEBUG_DIR}/subagent-stop-hook-input-${TIMESTAMP}.json', 'w') as f:
        json.dump(data, f, indent=2)
    with open('${DEBUG_DIR}/subagent-stop-hook-inputs.jsonl', 'a') as f:
        f.write(json.dumps(data) + '\n')
except Exception as e:
    with open('${DEBUG_DIR}/subagent-stop-hook-error.txt', 'a') as f:
        f.write(f'Error: {e}\nRaw: {repr(sys.stdin.read())}\n')
"
exit 0
HOOKEOF
chmod +x "$SUBAGENT_STOP_DUMP"

# ── Create settings with hooks ──────────────────────────────────────────────
SETTINGS_FILE="${WORKSPACE}/test-settings.json"

# Escape paths for JSON
STOP_DUMP_ESC=$(echo "$STOP_DUMP" | sed 's/"/\\"/g')
SUBAGENT_STOP_DUMP_ESC=$(echo "$SUBAGENT_STOP_DUMP" | sed 's/"/\\"/g')

cat > "$SETTINGS_FILE" << SETTINGSEOF
{
  "permissions": {
    "allow": [
      "Read",
      "Bash(echo:*)",
      "Bash(ls:*)",
      "Bash(python3:*)",
      "Task"
    ]
  },
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "${STOP_DUMP_ESC}",
            "timeout": 5
          }
        ]
      }
    ],
    "SubagentStop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "${SUBAGENT_STOP_DUMP_ESC}",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
SETTINGSEOF

echo "Settings file: $SETTINGS_FILE"
echo "Stop hook dump: $STOP_DUMP"
echo "SubagentStop hook dump: $SUBAGENT_STOP_DUMP"
echo ""

# ── Clear previous debug files ──────────────────────────────────────────────
rm -f "$DEBUG_DIR"/stop-hook-input-*.json "$DEBUG_DIR"/stop-hook-inputs.jsonl
rm -f "$DEBUG_DIR"/subagent-stop-hook-input-*.json "$DEBUG_DIR"/subagent-stop-hook-inputs.jsonl
rm -f "$DEBUG_DIR"/stop-hook-error.txt "$DEBUG_DIR"/subagent-stop-hook-error.txt

# ── Test 1: Stop hook (main agent) ─────────────────────────────────────────
if [[ "$MODE" == "both" || "$MODE" == "stop" ]]; then
    echo "============================================================"
    echo "  Test 1: Stop hook on main agent"
    echo "============================================================"
    echo ""

    export CLAUDE_PROJECT_DIR="$PROJECT_DIR"

    cd "$WORKSPACE"

    PROMPT="Say hello and run: echo 'stop hook test'"

    echo "Running Claude with Stop hook registered..."
    claude -p "$PROMPT" \
        --model "$MODEL" \
        --output-format text \
        --settings "$SETTINGS_FILE" \
        --dangerously-skip-permissions \
        2>&1 | tee "${WORKSPACE}/stop-test-output.txt"

    STOP_EXIT=$?
    cd "$PROJECT_DIR"

    echo ""
    echo "Claude exit: $STOP_EXIT"
    echo ""

    # Check if Stop hook fired
    echo "--- Stop hook results ---"
    if ls "$DEBUG_DIR"/stop-hook-input-*.json 1>/dev/null 2>&1; then
        echo "  Stop hook FIRED. Input captured."
        LATEST_STOP=$(ls -t "$DEBUG_DIR"/stop-hook-input-*.json | head -1)
        echo "  File: $LATEST_STOP"
        echo ""
        echo "  --- Hook input schema ---"
        python3 -c "
import json
with open('$LATEST_STOP') as f:
    data = json.load(f)
print(json.dumps(data, indent=2))
print()
print('Top-level keys:', list(data.keys()))
for key in data:
    val = data[key]
    print(f'  {key}: type={type(val).__name__}, value={str(val)[:200]}')
"
    elif [[ -f "$DEBUG_DIR/stop-hook-error.txt" ]]; then
        echo "  Stop hook fired but had an error:"
        cat "$DEBUG_DIR/stop-hook-error.txt"
    else
        echo "  Stop hook did NOT fire."
        echo "  (No debug files found in $DEBUG_DIR)"
    fi
    echo ""
fi

# ── Test 2: SubagentStop hook ───────────────────────────────────────────────
if [[ "$MODE" == "both" || "$MODE" == "subagent" ]]; then
    echo "============================================================"
    echo "  Test 2: SubagentStop hook on subagent"
    echo "============================================================"
    echo ""

    export CLAUDE_PROJECT_DIR="$PROJECT_DIR"
    export CLAUDE_CODE_ENABLE_TASKS="true"
    export CLAUDE_CODE_TASK_LIST_ID="stop-hook-exp-${TIMESTAMP}"

    cd "$WORKSPACE"

    PROMPT="Create a task using the Task tool with subagent_type 'Bash'. The task prompt should be: 'Run echo hello-from-subagent and report the result'. Wait for it to complete."

    echo "Running Claude with SubagentStop hook registered..."
    claude -p "$PROMPT" \
        --model "$MODEL" \
        --output-format text \
        --settings "$SETTINGS_FILE" \
        --dangerously-skip-permissions \
        2>&1 | tee "${WORKSPACE}/subagent-stop-test-output.txt"

    SUBAGENT_EXIT=$?
    cd "$PROJECT_DIR"

    echo ""
    echo "Claude exit: $SUBAGENT_EXIT"
    echo ""

    # Check if SubagentStop hook fired
    echo "--- SubagentStop hook results ---"
    if ls "$DEBUG_DIR"/subagent-stop-hook-input-*.json 1>/dev/null 2>&1; then
        echo "  SubagentStop hook FIRED. Input captured."
        LATEST_SA=$(ls -t "$DEBUG_DIR"/subagent-stop-hook-input-*.json | head -1)
        echo "  File: $LATEST_SA"
        echo ""
        echo "  --- Hook input schema ---"
        python3 -c "
import json
with open('$LATEST_SA') as f:
    data = json.load(f)
print(json.dumps(data, indent=2))
print()
print('Top-level keys:', list(data.keys()))
for key in data:
    val = data[key]
    print(f'  {key}: type={type(val).__name__}, value={str(val)[:200]}')
"
    elif [[ -f "$DEBUG_DIR/subagent-stop-hook-error.txt" ]]; then
        echo "  SubagentStop hook fired but had an error:"
        cat "$DEBUG_DIR/subagent-stop-hook-error.txt"
    else
        echo "  SubagentStop hook did NOT fire."
        echo "  (No debug files found in $DEBUG_DIR)"
    fi
    echo ""

    # Also check if Stop hook fired for the main agent
    echo "--- Stop hook (main agent during subagent test) ---"
    STOP_COUNT=$(ls "$DEBUG_DIR"/stop-hook-input-*.json 2>/dev/null | wc -l | tr -d ' ')
    echo "  Stop hook files: $STOP_COUNT"
    echo ""
fi

# ── Summary ─────────────────────────────────────────────────────────────
echo "============================================================"
echo "  SUMMARY"
echo "============================================================"
echo ""
echo "  Debug files:"
ls -la "$DEBUG_DIR"/stop-hook-* "$DEBUG_DIR"/subagent-stop-hook-* 2>/dev/null || echo "  (none)"
echo ""

# ── Cleanup ─────────────────────────────────────────────────────────────
if [[ "$KEEP" == "true" ]]; then
    echo "Workspace preserved: $WORKSPACE"
else
    rm -rf "$WORKSPACE"
    echo "Workspace cleaned: $WORKSPACE"
fi

# Clean up task directory
TASK_DIR="${HOME}/.claude/tasks/stop-hook-exp-${TIMESTAMP}"
if [[ -d "$TASK_DIR" ]]; then
    rm -rf "$TASK_DIR"
    echo "Task directory cleaned: $TASK_DIR"
fi
