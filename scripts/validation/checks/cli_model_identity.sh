#!/usr/bin/env bash
# cli_model_identity.sh -- Identify which model version an alias resolves to
# Usage: cli_model_identity.sh <model_alias>
# Always exits 0 (informational); the detail field captures the identity
set -euo pipefail

MODEL="${1:?Usage: cli_model_identity.sh <model_alias>}"

OUTPUT=$(unset CLAUDECODE 2>/dev/null; claude --print --model "$MODEL" "What is your exact model name and version? Reply with only the model identifier, nothing else." 2>/dev/null) || {
    echo "FAILED: claude --print --model $MODEL returned non-zero exit code"
    exit 1
}

# Extract model identity from response
IDENTITY=$(echo "$OUTPUT" | head -1 | tr -d '\n')

if [[ -z "$IDENTITY" ]]; then
    echo "FAILED: No model identity returned for alias '$MODEL'"
    exit 1
fi

echo "INFO: '$MODEL' resolves to: $IDENTITY"
exit 0
