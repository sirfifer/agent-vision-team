#!/bin/bash
#
# Build Extension
# Builds the VS Code extension and verifies the output
#

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== Building Extension ==="
echo ""

cd "$PROJECT_ROOT/extension"

echo "Running build..."
npm run build

echo ""

# Verify build output
if [ -f "out/extension.js" ]; then
    SIZE=$(ls -lh out/extension.js | awk '{print $5}')
    echo "✓ Build successful"
    echo "  Output: out/extension.js ($SIZE)"
else
    echo "✗ Build failed"
    echo "  Expected file not found: out/extension.js"
    exit 1
fi

echo ""
echo "Extension ready for testing."
