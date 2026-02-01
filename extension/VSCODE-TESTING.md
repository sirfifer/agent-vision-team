# VS Code Extension Testing Guide

Step-by-step guide to test the Collab Intelligence extension in VS Code.

## Prerequisites

1. **VS Code installed**
2. **Node.js and npm installed**
3. **MCP servers ready** (will start during testing)

## Step 1: Prepare Extension

```bash
cd extension
npm install
npm run build
```

Expected output: "Build complete."

## Step 2: Start MCP Servers

Open two terminals:

**Terminal 1: Knowledge Graph Server**
```bash
cd mcp-servers/knowledge-graph
uv run python -m collab_kg.server
```

Expected: Server starts on port 3101

**Terminal 2: Quality Server**
```bash
cd mcp-servers/quality
uv run python -m collab_quality.server
```

Expected: Server starts on port 3102

## Step 3: Launch Extension Development Host

1. Open the `extension/` folder in VS Code
2. Press **F5** (or Run → Start Debugging)
3. A new VS Code window opens titled **"[Extension Development Host]"**

## Step 4: Open Test Workspace

In the Extension Development Host window:

1. Open the `agent-vision-team` folder (the parent directory)
2. The extension should activate automatically (it detects `.claude/collab/`)

## Step 5: Verify Extension Activated

Check these indicators:

1. **Activity Bar**: Look for "Collab Intelligence" icon (should appear)
2. **Status Bar** (bottom): Should show "$(shield) Collab: Active" or "Inactive"
3. **Output Panel**: View → Output → Select "Extension Host" - check for activation messages

## Step 6: Test Memory Browser

1. Click the "Collab Intelligence" icon in Activity Bar
2. Expand the **"Memory Browser"** section
3. You should see three tier groups:
   - Vision Standards (immutable) (0)
   - Architecture (human-approved) (0)
   - Quality (automated) (0)

**Test Refresh**:
- Click the refresh icon in Memory Browser header
- Extension fetches entities from KG server

**Test Search**:
- Click the search icon in Memory Browser header
- Enter a search query (e.g., "test")
- Results appear in the tree

## Step 7: Test Findings Panel

1. In the sidebar, expand **"Findings"** section
2. Should show quality findings (may be empty initially)

**Test Refresh**:
- Click refresh icon in Findings header
- Extension fetches lint results from Quality server

## Step 8: Test Tasks Panel

1. In the sidebar, expand **"Tasks"** section
2. Should show task briefs from `.claude/collab/task-briefs/`
3. Should see "example-001-add-feature.md"

**Test Auto-Refresh**:
- Create a new file in `.claude/collab/task-briefs/test-task.md`
- Tasks panel should auto-update

## Step 9: Test Commands

Open Command Palette (Cmd+Shift+P / Ctrl+Shift+P):

1. **"Collab Intelligence: Connect to MCP Servers"**
   - Should connect and update status bar

2. **"Collab Intelligence: Refresh Memory Browser"**
   - Should re-fetch KG entities

3. **"Collab Intelligence: Refresh Findings Panel"**
   - Should re-fetch quality findings

4. **"Collab Intelligence: Search Memory"**
   - Opens input box for search query

5. **"Collab Intelligence: Validate All Quality Gates"**
   - Runs validation and shows notification

6. **"Collab Intelligence: View Dashboard"**
   - Opens dashboard webview

## Step 10: Test with Actual Data

### Populate Knowledge Graph

In the Extension Development Host, open the integrated terminal:

```bash
# Create a test entity via curl
curl -X POST http://localhost:3101/mcp/call \
  -H "Content-Type: application/json" \
  -d '{
    "method": "tools/call",
    "params": {
      "name": "create_entities",
      "arguments": {
        "entities": [{
          "name": "test_vision_standard",
          "entityType": "vision_standard",
          "observations": ["protection_tier: vision", "All tests must pass before commit"]
        }]
      }
    }
  }'
```

**Verify**:
- Refresh Memory Browser
- "Vision Standards" should show (1)
- Expand to see "test_vision_standard"

### Trigger Quality Findings

```bash
# Run lint on a test file
curl -X POST http://localhost:3102/mcp/call \
  -H "Content-Type: application/json" \
  -d '{
    "method": "tools/call",
    "params": {
      "name": "run_lint",
      "arguments": {
        "files": ["mcp-servers/quality/collab_quality/server.py"],
        "language": "python"
      }
    }
  }'
```

**Verify**:
- Refresh Findings Panel
- Should show lint findings

## Expected Behavior

### When Servers Are Running

- Status bar: "Collab: Active" (green)
- Memory Browser loads entities
- Findings Panel loads findings
- All refresh commands work

### When Servers Are NOT Running

- Status bar: "Collab: Inactive" (gray)
- Warning notification: "MCP servers not available"
- Tree views show empty
- Refresh commands fail with error

### Connection States

1. **Initial Load**: Extension auto-connects on activation
2. **Manual Connect**: Use "Connect to MCP Servers" command
3. **Reconnect**: If servers restart, use connect command again

## Debugging

### View Extension Logs

1. **Output Panel**: View → Output → "Extension Host"
2. Look for messages like:
   - "Connecting to MCP servers..."
   - "Connected to MCP servers."
   - "Calling knowledge-graph/search_nodes..."

### Common Issues

**Extension doesn't activate**:
- Check: Does workspace have `.claude/collab/` directory?
- Fix: Ensure you opened the `agent-vision-team` folder

**"MCP servers not available" warning**:
- Check: Are both servers running on ports 3101 and 3102?
- Fix: Start servers in separate terminals
- Verify: `curl http://localhost:3101/health`

**Memory Browser shows empty**:
- Check: Are there entities in the KG?
- Fix: Populate with test data (see Step 10)

**Findings Panel shows empty**:
- Check: Have you run lint?
- Fix: Run lint via curl (see Step 10) or refresh

**Status bar shows "Error"**:
- Check: Extension Host output for error messages
- Fix: Restart servers, reload extension window

### Reload Extension

If you make changes to extension code:
1. **Rebuild**: `npm run build` in extension directory
2. **Reload**: In Extension Development Host, press Cmd+R / Ctrl+R
3. Extension reloads with new code

## Manual Testing Checklist

- [ ] Extension activates on workspace open
- [ ] Status bar shows correct health status
- [ ] Memory Browser shows tier groups
- [ ] Memory Browser refresh works
- [ ] Memory Browser search works
- [ ] Findings Panel shows findings
- [ ] Findings Panel refresh works
- [ ] Tasks Panel shows task briefs
- [ ] Tasks Panel auto-refreshes on file changes
- [ ] "Connect to MCP Servers" command works
- [ ] "Validate All Quality Gates" command works
- [ ] "View Dashboard" command opens webview
- [ ] Tooltips show entity observations
- [ ] Status bar updates on server state changes

## Next Steps

After successful testing:

1. **Package Extension**: `npm install -g @vscode/vsce && vsce package`
2. **Install Locally**: Extensions → ... → Install from VSIX
3. **Use in Real Workspace**: Open any project with `.claude/collab/` structure

## Troubleshooting Tips

**TypeError in MCP calls**:
- Check server response format matches client expectations
- Verify tool names match server implementations

**Tree views don't update**:
- Check if `refresh()` or `_onDidChangeTreeData.fire()` is called
- Verify data is actually fetched from servers

**Commands not appearing**:
- Check `package.json` contributes section
- Verify command IDs match registration in `extension.ts`

**Status bar not visible**:
- Check if `statusBar.show()` is called
- Verify status bar items are created and registered

## Success Criteria

Extension is working if:
1. ✅ Connects to MCP servers automatically
2. ✅ Displays KG entities grouped by tier
3. ✅ Shows quality findings from lint
4. ✅ Lists task briefs from filesystem
5. ✅ All commands execute without errors
6. ✅ Status bar reflects actual server state
7. ✅ Refresh buttons update data
8. ✅ Search functionality works
