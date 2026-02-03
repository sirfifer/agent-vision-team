# Dogfooding Test Runbook

Complete guide for testing the Collab Intelligence VS Code extension using the dogfooding methodology.

## Quick Start (One Command)

```bash
./scripts/dogfood-test.sh
```

This master script will:
1. Build the extension
2. Start MCP servers
3. Populate test data
4. Prompt you to test in VS Code
5. Clean up when done

## Manual Step-by-Step

### Prerequisites

- VS Code installed
- Node.js and npm installed
- Python and uv installed
- Project dependencies installed:
  ```bash
  cd mcp-servers/knowledge-graph && uv sync
  cd mcp-servers/quality && uv sync
  cd extension && npm install
  ```

### Step 1: Build Extension

```bash
./scripts/build-extension.sh
```

**Expected Output**:
```
=== Building Extension ===

Running build...
Build complete.

✓ Build successful
  Output: out/extension.js (234K)

Extension ready for testing.
```

### Step 2: Start MCP Servers

```bash
./scripts/start-mcp-servers.sh
```

**Expected Output**:
```
=== Starting MCP Servers for Dogfood Testing ===

Starting Knowledge Graph server on port 3101...
  PID: 12345
  Log: /tmp/kg-server.log

Starting Quality server on port 3102...
  PID: 12346
  Log: /tmp/quality-server.log

Verifying server health...
  ✓ Knowledge Graph server: HEALTHY (port 3101)
  ✓ Quality server: HEALTHY (port 3102)

=== MCP Servers Started Successfully ===
```

**Troubleshooting**:
- If health check fails, check logs: `tail -f /tmp/kg-server.log` or `/tmp/quality-server.log`
- Ensure ports 3101 and 3102 are not in use: `lsof -i :3101` and `lsof -i :3102`

### Step 3: Populate Test Data

```bash
./scripts/populate-test-data.sh
```

**Expected Output**:
```
=== Populating Test Data ===

Creating vision-tier test entity...
  ✓ Vision entity created
Creating architecture-tier test entity...
  ✓ Architecture entity created
Creating quality-tier test entity...
  ✓ Quality entity created

=== Test Data Populated Successfully ===

Entities created:
  - test_vision_standard (vision tier)
  - test_arch_component (architecture tier)
  - test_quality_note (quality tier)
```

**Troubleshooting**:
- If creation fails, verify servers are running: `curl http://localhost:3101/health`
- Check you have `jq` installed: `brew install jq` (macOS)

### Step 4: Launch Extension in VS Code

1. **Open VS Code in extension directory**:
   ```bash
   cd extension
   code .
   ```

2. **Launch Extension Development Host**:
   - Press **F5** (or Run → Start Debugging)
   - Wait for new window titled "[Extension Development Host]"

3. **Open test workspace**:
   - In Extension Development Host: File → Open Folder
   - Navigate to `agent-vision-team` (parent directory)
   - Click Open

4. **Verify extension activated**:
   - Activity Bar: "Collab Intelligence" icon appears
   - Status Bar: "Collab: Active" (green)
   - No error notifications

### Step 5: Complete Checklist

Open `DOGFOOD-CHECKLIST.md` and work through all verification items.

**Key areas to test**:
- Extension activation
- Memory Browser (3 tiers, test entities)
- Findings Panel
- Tasks Panel
- All 7 commands
- Status bar
- Error handling

### Step 6: Cleanup

```bash
./scripts/stop-mcp-servers.sh
```

**Expected Output**:
```
Stopping MCP servers...
  ✓ Knowledge Graph server stopped
  ✓ Quality server stopped

Servers stopped.
```

---

## Individual Script Usage

### build-extension.sh

**Purpose**: Builds the extension and verifies output

**Usage**:
```bash
./scripts/build-extension.sh
```

**Output**: Confirms `out/extension.js` exists and shows file size

### start-mcp-servers.sh

**Purpose**: Starts both MCP servers with health checks

**Usage**:
```bash
./scripts/start-mcp-servers.sh
```

**Output**: Server PIDs, logs, and health status

**Options**: None

**Cleanup**: Use `stop-mcp-servers.sh` or `kill <PID>`

### stop-mcp-servers.sh

**Purpose**: Stops all running MCP servers

**Usage**:
```bash
./scripts/stop-mcp-servers.sh
```

**Output**: Confirmation of stopped servers

### populate-test-data.sh

**Purpose**: Adds test entities to Knowledge Graph

**Usage**:
```bash
./scripts/populate-test-data.sh
```

**Prerequisites**: Servers must be running

**Output**: Confirmation of created entities (3 total)

**Note**: Safe to run multiple times (creates duplicate entities)

### dogfood-test.sh

**Purpose**: Orchestrates full test cycle

**Usage**:
```bash
./scripts/dogfood-test.sh
```

**Interactive**: Prompts you to test in VS Code, then waits for cleanup

---

## Troubleshooting

### Extension doesn't activate

**Symptom**: No icon in Activity Bar

**Possible Causes**:
1. Workspace doesn't contain `.claude/collab/` directory
2. Extension not built: `./scripts/build-extension.sh`
3. VS Code cache issue: Reload window (Cmd+R / Ctrl+R)

**Fix**:
```bash
# Verify workspace structure
ls -la .claude/collab/

# Rebuild extension
./scripts/build-extension.sh

# Reload VS Code window
```

### "MCP servers not available" error

**Symptom**: Status bar shows "Inactive" or error notification

**Possible Causes**:
1. Servers not started
2. Servers crashed
3. Wrong ports

**Fix**:
```bash
# Check if servers running
curl http://localhost:3101/health
curl http://localhost:3102/health

# Restart servers
./scripts/stop-mcp-servers.sh
./scripts/start-mcp-servers.sh

# Check logs
tail -f /tmp/kg-server.log
tail -f /tmp/quality-server.log
```

### Memory Browser shows empty tiers

**Symptom**: All tier groups show (0)

**Possible Causes**:
1. Test data not populated
2. MCP server connection failed
3. Refresh needed

**Fix**:
```bash
# Populate test data
./scripts/populate-test-data.sh

# In VS Code, click refresh button in Memory Browser
# Or use Command Palette: "Collab Intelligence: Refresh Memory Browser"
```

### Extension crashes or freezes

**Symptom**: Extension Host becomes unresponsive

**Fix**:
1. Check Output panel (Output → "Extension Host") for errors
2. Reload window: Cmd+R / Ctrl+R
3. If persistent, rebuild: `./scripts/build-extension.sh` and restart

### Build fails

**Symptom**: `npm run build` errors

**Possible Causes**:
1. Dependencies not installed
2. TypeScript compilation errors

**Fix**:
```bash
cd extension
npm install
npm run build

# Check for TypeScript errors
npx tsc --noEmit
```

### Port already in use

**Symptom**: Server fails to start with "port already in use"

**Fix**:
```bash
# Find process using port
lsof -i :3101  # For KG server
lsof -i :3102  # For Quality server

# Kill the process
kill <PID>

# Or use stop script
./scripts/stop-mcp-servers.sh
```

---

## Testing Iterations

### Fast Iteration Cycle (Development)

For quick testing during development:

1. Make code changes in `extension/src/`
2. Rebuild: `npm run build` (in extension directory)
3. In Extension Development Host: **Cmd+R / Ctrl+R** (reload window)
4. Test changes
5. Repeat

**No need to**:
- Restart MCP servers (unless server code changed)
- Re-populate data (persists across reloads)
- Close/reopen VS Code

### Full Test Cycle (Validation)

For comprehensive validation:

1. Run `./scripts/dogfood-test.sh`
2. Complete full `DOGFOOD-CHECKLIST.md`
3. Document issues
4. Fix issues
5. Repeat until all items pass

---

## Adding New Test Scenarios

To add new tests to the checklist:

1. **Edit** `DOGFOOD-CHECKLIST.md`
2. **Add section** for new feature
3. **List verification items** with [ ] checkboxes
4. **Update** this RUNBOOK with any new scripts needed

Example:
```markdown
## New Feature Test

- [ ] Feature appears in UI
- [ ] Feature functions correctly
- [ ] No console errors

**Notes**:
_____________________________________________________________________________
```

---

## When to Add ExTester Automation

Consider adding automated UI tests (ExTester) when:

1. **Manual testing takes >30 minutes per cycle**
2. **Need CI/CD integration** for automated validation
3. **Team grows** beyond 1-2 developers
4. **Regression testing required** for frequent releases

**Setup** (when needed):
```bash
cd extension
npm install --save-dev vscode-extension-tester @types/mocha @types/chai
```

**Cost**: ~2-3 days setup overhead

**Current Recommendation**: Defer automation. Manual process is sufficient.

---

## Maintenance

### Weekly

- [ ] Run full dogfood test cycle
- [ ] Update checklist with any new features
- [ ] Check for MCP server updates

### After Significant Changes

- [ ] Run full test cycle
- [ ] Update test data if entity schema changed
- [ ] Update scripts if server ports changed

### Before Releases

- [ ] Complete full checklist (all items must pass)
- [ ] Test packaged installation (`.vsix`)
- [ ] Verify on clean VS Code installation

---

## Resources

- **Extension Documentation**: [extension/README.md](extension/README.md)
- **Extension Testing Guide**: [extension/TESTING.md](extension/TESTING.md)
- **VS Code Testing Guide**: [extension/VSCODE-TESTING.md](extension/VSCODE-TESTING.md)
- **Phase 3 Status**: [.claude/PHASE3-STATUS.md](.claude/PHASE3-STATUS.md)
- **Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)

---

## Quick Reference

```bash
# Full test cycle
./scripts/dogfood-test.sh

# Individual steps
./scripts/build-extension.sh
./scripts/start-mcp-servers.sh
./scripts/populate-test-data.sh
./scripts/stop-mcp-servers.sh

# Check server health
curl http://localhost:3101/health  # KG
curl http://localhost:3102/health  # Quality

# View logs
tail -f /tmp/kg-server.log
tail -f /tmp/quality-server.log

# Reload extension in Dev Host
# Press: Cmd+R (macOS) or Ctrl+R (Windows/Linux)
```
