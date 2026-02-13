#!/usr/bin/env bash
# ============================================================================
# Experiment: Permission denial behavior in Claude Code transcripts
#
# Tests what happens when Claude tries to use a tool that is not pre-approved
# in non-interactive mode. Captures the transcript JSONL to analyze the
# exact structure of permission denial entries.
#
# Usage:
#   ./scripts/hooks/test-permission-behavior.sh                # Experiment 1
#   ./scripts/hooks/test-permission-behavior.sh --subagent     # Experiment 2
#   ./scripts/hooks/test-permission-behavior.sh --keep         # Preserve workspace
# ============================================================================
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# ── Defaults ────────────────────────────────────────────────────────────────
MODE="direct"
KEEP=false
MODEL="haiku"  # cheapest model for experiments

# ── Parse args ──────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case $1 in
        --subagent)  MODE="subagent"; shift ;;
        --keep)      KEEP=true; shift ;;
        --model)     MODEL="$2"; shift 2 ;;
        *)           echo "Unknown arg: $1"; exit 1 ;;
    esac
done

# ── Workspace setup ─────────────────────────────────────────────────────────
TIMESTAMP=$(date +%s)
WORKSPACE=$(mktemp -d /tmp/avt-perm-exp-XXXXXX)
DEBUG_DIR="${PROJECT_DIR}/.avt/debug"
OUTPUT_FILE="${WORKSPACE}/claude-output.txt"

mkdir -p "$WORKSPACE" "$DEBUG_DIR"

echo "============================================================"
echo "  Permission Behavior Experiment"
echo "============================================================"
echo "  Mode:      ${MODE}"
echo "  Model:     ${MODEL}"
echo "  Workspace: ${WORKSPACE}"
echo ""

if [[ "$MODE" == "direct" ]]; then
    # ── Experiment 1: Direct permission denial ──────────────────────────
    # Run Claude with restricted tools. Prompt asks to use Bash (not allowed).
    # Use --permission-mode dontAsk to auto-deny non-approved tools.
    echo "--- Experiment 1: Permission denial in transcript ---"
    echo ""
    echo "Running Claude with --allowedTools 'Read' and prompt requesting Bash..."
    echo ""

    # Run from a temp dir to avoid loading project hooks
    # Use --no-session-persistence false (default) so transcript is saved
    cd "$WORKSPACE"

    PROMPT="You MUST attempt to run this exact bash command: python3 -c \"print('hello world')\"

Use the Bash tool to execute it. Do not skip this step. After attempting the command, tell me exactly what happened (success or failure) and why."

    claude -p "$PROMPT" \
        --model "$MODEL" \
        --output-format json \
        --permission-mode dontAsk \
        --allowedTools "Read" \
        2>&1 | tee "$OUTPUT_FILE"

    CLAUDE_EXIT=$?

    cd "$PROJECT_DIR"

elif [[ "$MODE" == "subagent" ]]; then
    # ── Experiment 2: Subagent permission propagation ──────────────────
    echo "--- Experiment 2: Subagent permission propagation ---"
    echo ""
    echo "Running Claude with Task tool allowed, prompting to spawn subagent..."
    echo ""

    cd "$WORKSPACE"

    # Allow Task tool so Claude can spawn a subagent, but NOT Bash
    PROMPT="You must spawn a subagent using the Task tool to do the following work:

The subagent should attempt to run this exact bash command: python3 -c \"print('hello from subagent')\"

Use the Task tool with subagent_type 'Bash' to create a task with this prompt:
\"Run this exact bash command using the Bash tool: python3 -c \\\"print('hello from subagent')\\\"\"

After the subagent completes (or fails), tell me exactly what happened."

    claude -p "$PROMPT" \
        --model "$MODEL" \
        --output-format json \
        --permission-mode dontAsk \
        --allowedTools "Read,Task" \
        2>&1 | tee "$OUTPUT_FILE"

    CLAUDE_EXIT=$?

    cd "$PROJECT_DIR"
fi

echo ""
echo "--- Claude exited with code: $CLAUDE_EXIT ---"
echo ""

# ── Find and analyze transcript ─────────────────────────────────────────
echo "============================================================"
echo "  TRANSCRIPT ANALYSIS"
echo "============================================================"
echo ""

# Find the most recent transcript for the temp workspace
# Transcripts are stored at ~/.claude/projects/<encoded-path>/<session-id>.jsonl
ENCODED_WORKSPACE=$(echo "$WORKSPACE" | sed 's|/|-|g')
TRANSCRIPT_DIR="$HOME/.claude/projects/${ENCODED_WORKSPACE}"

echo "Looking for transcript dir: $TRANSCRIPT_DIR"

if [[ -d "$TRANSCRIPT_DIR" ]]; then
    echo "  Found transcript directory"

    # Find the most recent .jsonl file
    TRANSCRIPT=$(ls -t "$TRANSCRIPT_DIR"/*.jsonl 2>/dev/null | head -1)

    if [[ -n "$TRANSCRIPT" && -f "$TRANSCRIPT" ]]; then
        echo "  Transcript: $TRANSCRIPT"
        echo "  Size: $(wc -c < "$TRANSCRIPT") bytes"
        echo ""

        # Extract all tool_use and tool_result entries
        echo "--- Tool interactions ---"
        python3 << PYEOF
import json, sys

transcript_path = "$TRANSCRIPT"
results = []

with open(transcript_path) as f:
    for i, line in enumerate(f):
        try:
            entry = json.loads(line)
        except:
            continue
        t = entry.get('type','')
        msg = entry.get('message', {})
        content = msg.get('content', [])
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            bt = block.get('type','')
            if bt == 'tool_use':
                name = block.get('name','?')
                inp = block.get('input', {})
                tool_id = block.get('id','?')
                print(f"  TOOL_USE  [{name}] id={tool_id}")
                inp_str = json.dumps(inp, indent=2)
                for iline in inp_str.split('\n')[:5]:
                    print(f"    {iline}")
                if len(inp_str.split('\n')) > 5:
                    print(f"    ... ({len(inp_str)} chars total)")
                results.append({'line': i, 'type': 'tool_use', 'name': name, 'id': tool_id, 'input': inp})

            elif bt == 'tool_result':
                tool_id = block.get('tool_use_id','?')
                is_err = block.get('is_error', False)
                content_val = block.get('content','')
                if isinstance(content_val, list):
                    content_str = json.dumps(content_val)
                else:
                    content_str = str(content_val)
                marker = "ERROR" if is_err else "OK"
                print(f"  TOOL_RESULT [{marker}] id={tool_id}")
                print(f"    is_error: {is_err}")
                for rline in content_str[:500].split('\n')[:8]:
                    print(f"    content: {rline}")
                results.append({'line': i, 'type': 'tool_result', 'id': tool_id, 'is_error': is_err, 'content': content_str[:1000]})
                print()

# Write structured results to debug file
debug_path = "$DEBUG_DIR/experiment-${MODE}-transcript-analysis.json"
with open(debug_path, 'w') as f:
    json.dump(results, f, indent=2)
print(f"\nStructured results saved to: {debug_path}")

# Check for error patterns
errors = [r for r in results if r.get('is_error')]
print(f"\nTotal tool interactions: {len(results)}")
print(f"Total errors: {len(errors)}")
if errors:
    print("\n--- Error details ---")
    for err in errors:
        print(f"  Tool ID: {err['id']}")
        print(f"  Content: {err['content'][:300]}")
        print()
PYEOF

        # Also save the raw transcript for later inspection
        cp "$TRANSCRIPT" "$DEBUG_DIR/experiment-${MODE}-raw-transcript.jsonl"
        echo ""
        echo "Raw transcript copied to: $DEBUG_DIR/experiment-${MODE}-raw-transcript.jsonl"

        # Check for subagent transcripts (Experiment 2)
        if [[ "$MODE" == "subagent" ]]; then
            echo ""
            echo "--- Subagent transcripts ---"
            SESSION_ID=$(basename "$TRANSCRIPT" .jsonl)
            SUBAGENT_DIR="$TRANSCRIPT_DIR/$SESSION_ID"
            if [[ -d "$SUBAGENT_DIR" ]]; then
                echo "  Subagent directory: $SUBAGENT_DIR"
                for sa_file in "$SUBAGENT_DIR"/*.jsonl; do
                    [[ -f "$sa_file" ]] || continue
                    echo "  Subagent transcript: $sa_file"
                    echo "  Size: $(wc -c < "$sa_file") bytes"
                    cp "$sa_file" "$DEBUG_DIR/experiment-subagent-agent-transcript.jsonl"

                    echo ""
                    echo "  --- Subagent tool interactions ---"
                    python3 << PYEOF2
import json
with open("$sa_file") as f:
    for i, line in enumerate(f):
        try:
            entry = json.loads(line)
        except:
            continue
        msg = entry.get('message', {})
        content = msg.get('content', [])
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            bt = block.get('type','')
            if bt == 'tool_use':
                print(f"    TOOL_USE [{block.get('name','?')}] id={block.get('id','?')}")
            elif bt == 'tool_result':
                marker = "ERROR" if block.get('is_error') else "OK"
                print(f"    TOOL_RESULT [{marker}] id={block.get('tool_use_id','?')}")
                print(f"      is_error: {block.get('is_error', False)}")
                c = block.get('content','')
                if isinstance(c, list):
                    c = json.dumps(c)
                print(f"      content: {str(c)[:300]}")
                print()
PYEOF2
                done
            else
                echo "  No subagent directory found at: $SUBAGENT_DIR"
                echo "  (Subagent may not have been spawned, or transcripts stored elsewhere)"
            fi
        fi
    else
        echo "  No transcript JSONL found in: $TRANSCRIPT_DIR"
    fi
else
    echo "  Transcript directory not found: $TRANSCRIPT_DIR"
    echo ""
    echo "  Checking for transcripts in alternative locations..."
    # Check the project dir transcripts (if Claude associated with the project)
    for dir in "$HOME/.claude/projects"/*/; do
        LATEST=$(ls -t "$dir"*.jsonl 2>/dev/null | head -1)
        if [[ -n "$LATEST" ]]; then
            MOD_TIME=$(stat -f %m "$LATEST" 2>/dev/null || echo 0)
            if [[ "$MOD_TIME" -ge "$TIMESTAMP" ]]; then
                echo "  Found recent transcript: $LATEST"
                echo "  (modified after experiment started)"
            fi
        fi
    done
fi

echo ""

# ── Summary ─────────────────────────────────────────────────────────────
echo "============================================================"
echo "  SUMMARY"
echo "============================================================"
echo ""
echo "  Mode:       $MODE"
echo "  Exit code:  $CLAUDE_EXIT"
echo "  Workspace:  $WORKSPACE"
echo "  Debug dir:  $DEBUG_DIR"
echo ""

# ── Cleanup ─────────────────────────────────────────────────────────────
if [[ "$KEEP" == "true" ]]; then
    echo "Workspace preserved: $WORKSPACE"
else
    rm -rf "$WORKSPACE"
    echo "Workspace cleaned: $WORKSPACE"
fi

echo ""
echo "Debug files:"
ls -la "$DEBUG_DIR"/experiment-${MODE}-* 2>/dev/null || echo "  (none)"
echo ""
