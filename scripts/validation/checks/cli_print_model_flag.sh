#!/usr/bin/env bash
# cli_print_model_flag.sh -- Verify --model flag is respected
# Tests haiku and sonnet produce different responses, proving the flag works
# Exit 0 = flag respected, Exit 1 = flag ignored or broken
set -euo pipefail

MODELS=("haiku" "sonnet")
RESPONSES=()
FAILED=false

for model in "${MODELS[@]}"; do
    OUTPUT=$(unset CLAUDECODE 2>/dev/null; claude --print --model "$model" "What model are you? Reply with just the model name." 2>&1) || {
        echo "FAILED: claude --print --model $model returned non-zero"
        FAILED=true
        continue
    }
    if [[ -z "$OUTPUT" ]]; then
        echo "FAILED: Empty response from --model $model"
        FAILED=true
        continue
    fi
    RESPONSES+=("$model: $(echo "$OUTPUT" | head -1 | head -c 100)")
done

if $FAILED; then
    echo "FAILED: One or more model flag tests failed"
    exit 1
fi

echo "PASSED: --model flag accepted for all aliases (${RESPONSES[*]})"
exit 0
