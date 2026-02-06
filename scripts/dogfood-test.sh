#!/bin/bash
#
# Dogfood Test Script
# Orchestrates the full dogfooding test cycle for the Collab Intelligence extension
#

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "========================================================"
echo "  Collab Intelligence Extension - Dogfood Test Cycle"
echo "========================================================"
echo ""

# Step 1: Build Extension
echo "Step 1: Building extension..."
bash "$PROJECT_ROOT/scripts/build-extension.sh"
echo ""

# Step 2: Start MCP Servers
echo "Step 2: Starting MCP servers..."
bash "$PROJECT_ROOT/scripts/start-mcp-servers.sh"
echo ""

# Step 3: Populate Test Data
echo "Step 3: Populating test data..."
bash "$PROJECT_ROOT/scripts/populate-test-data.sh"
echo ""

# Step 4: Manual Testing Instructions
echo "========================================================"
echo "Step 4: Manual Testing"
echo "========================================================"
echo ""
echo "The extension is now ready for testing. Follow these steps:"
echo ""
echo "1. Open VS Code in the extension directory:"
echo "   cd $PROJECT_ROOT/extension"
echo "   code ."
echo ""
echo "2. In VS Code, press F5 to launch Extension Development Host"
echo ""
echo "3. In the Extension Development Host window:"
echo "   - File → Open Folder"
echo "   - Navigate to: $PROJECT_ROOT"
echo "   - Click Open"
echo ""
echo "4. The extension should activate automatically"
echo "   (it detects the .avt/ directory)"
echo ""
echo "5. Complete the checklist in:"
echo "   $PROJECT_ROOT/DOGFOOD-CHECKLIST.md"
echo ""
echo "6. When done, press ENTER to cleanup..."
read -r

# Step 5: Cleanup
echo ""
echo "Step 5: Cleanup..."
bash "$PROJECT_ROOT/scripts/stop-mcp-servers.sh"
echo ""
echo "========================================================"
echo "  Dogfood Test Cycle Complete"
echo "========================================================"
echo ""
echo "Review your checklist results in DOGFOOD-CHECKLIST.md"
