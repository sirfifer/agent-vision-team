#!/usr/bin/env bash
# version_check.sh -- Verify Claude Code version meets minimum requirement
# Usage: version_check.sh <minimum_version>
# Exit 0 = meets minimum, Exit 1 = below minimum
set -euo pipefail

MINIMUM="${1:?Usage: version_check.sh <minimum_version>}"

VERSION=$(claude --version 2>/dev/null | head -1 | sed 's/[^0-9.]//g') || {
    echo "FAILED: Could not get Claude Code version"
    exit 1
}

if [[ -z "$VERSION" ]]; then
    echo "FAILED: Claude Code version string is empty"
    exit 1
fi

# Compare versions using sort -V
HIGHER=$(printf '%s\n%s' "$MINIMUM" "$VERSION" | sort -V | tail -1)
if [[ "$HIGHER" == "$VERSION" || "$VERSION" == "$MINIMUM" ]]; then
    echo "PASSED: Claude Code $VERSION >= minimum $MINIMUM"
    exit 0
else
    echo "FAILED: Claude Code $VERSION < minimum $MINIMUM"
    exit 1
fi
