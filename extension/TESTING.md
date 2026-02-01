# Testing Guide - Collab Intelligence Extension

This document describes the testing strategy, test coverage, and how to run tests for the Collab Intelligence VS Code extension.

## Test Strategy

### 1. Unit Tests
Test individual components in isolation without external dependencies.

**Scope**:
- MCP Client Service (without live servers)
- Tree View Providers (data grouping, updates)
- Model classes
- Utility functions

**Location**: `src/test/*.test.ts`

### 2. Integration Tests
Test components with live MCP servers.

**Scope**:
- MCP tool calling with real servers
- End-to-end data flows
- Extension activation with live workspace

**Location**: `src/test/*.test.ts` (marked with `test.skip`)

### 3. Manual Testing
UI interactions and visual verification.

**Scope**:
- TreeView rendering
- Status bar updates
- Command execution
- Webview dashboard

## Running Tests

### Prerequisites

```bash
cd extension
npm install
```

### Run All Tests

```bash
npm test
```

This runs:
1. TypeScript compilation (`npm run pretest`)
2. All unit tests (integration tests skipped by default)

### Run Specific Test Suite

```bash
# Via VS Code Test Explorer
# Or target specific files:
npm test -- --grep "McpClientService"
```

### Run Integration Tests

Integration tests require live MCP servers.

**Step 1: Start MCP Servers**

```bash
# Terminal 1
cd mcp-servers/knowledge-graph
uv run python -m collab_kg.server

# Terminal 2
cd mcp-servers/quality
uv run python -m collab_quality.server
```

**Step 2: Enable Integration Tests**

Edit `src/test/*.test.ts` and remove `.skip` from integration test cases:

```typescript
// Before:
test.skip('should connect to running MCP servers', async () => {
  // ...
});

// After:
test('should connect to running MCP servers', async () => {
  // ...
});
```

**Step 3: Run Tests**

```bash
npm test
```

## Test Coverage

### McpClientService.test.ts

**Unit Tests** (no server required):
- ✅ `should initialize with correct default ports`
- ✅ `should start in disconnected state`
- ✅ `disconnect should set connected to false`

**Integration Tests** (requires live servers):
- ⏸️ `should connect to running MCP servers`
- ⏸️ `should fail to connect when servers are down`
- ⏸️ `should call tools on connected servers`

**Coverage**: 3 unit tests, 3 integration tests (skipped)

### MemoryTreeProvider.test.ts

**Unit Tests**:
- ✅ `should start with empty entities`
- ✅ `should group entities by tier`
- ✅ `should handle entities without tier`
- ✅ `should update entities on refresh`

**Coverage**: 4 tests, 100% of provider logic

### KnowledgeGraphClient.test.ts

**Unit Tests**:
- ✅ `should be instantiated with MCP client`

**Integration Tests** (requires live server):
- ⏸️ `should create entities`
- ⏸️ `should create relations`
- ⏸️ `should add observations`
- ⏸️ `should search nodes`
- ⏸️ `should get entity by name`
- ⏸️ `should get entities by tier`
- ⏸️ `should validate tier access`

**Coverage**: 1 unit test, 7 integration tests (skipped)

### QualityClient.test.ts

**Unit Tests**:
- ✅ `should be instantiated with MCP client`

**Integration Tests** (requires live server):
- ⏸️ `should auto format files`
- ⏸️ `should run lint`
- ⏸️ `should run tests`
- ⏸️ `should check coverage`
- ⏸️ `should check all gates`
- ⏸️ `should validate all`
- ⏸️ `should get trust decision`
- ⏸️ `should record dismissal`

**Coverage**: 1 unit test, 8 integration tests (skipped)

## Manual Testing Checklist

### Extension Activation

- [ ] Open workspace with `.claude/collab/` directory
- [ ] Extension activates automatically
- [ ] Activity bar shows "Collab Intelligence" icon
- [ ] Status bar shows "Collab: Inactive" (if servers not running)
- [ ] No errors in Output → Extension Host

### MCP Server Connection

**Without Servers**:
- [ ] Extension shows warning: "MCP servers not available"
- [ ] Status bar shows "Collab: Inactive"

**With Servers**:
- [ ] Start both MCP servers (ports 3101, 3102)
- [ ] Extension auto-connects
- [ ] Status bar changes to "Collab: Active"
- [ ] Memory Browser loads entities
- [ ] Findings Panel loads findings

### Memory Browser TreeView

- [ ] Shows 3 tier groups: Vision, Architecture, Quality
- [ ] Each tier shows entity count
- [ ] Expanding tier shows entities
- [ ] Entity item shows type and observation/relation counts
- [ ] Hovering over entity shows tooltip with observations and relations
- [ ] Refresh button re-fetches data from server
- [ ] Search button prompts for query
- [ ] Search results update tree view

### Findings Panel TreeView

- [ ] Shows quality findings
- [ ] Findings grouped by severity or component
- [ ] Refresh button re-fetches from server
- [ ] Finding items show file, line, message

### Tasks Panel TreeView

- [ ] Shows task brief files from `.claude/collab/task-briefs/`
- [ ] Adding new task brief auto-refreshes view
- [ ] Modifying task brief auto-refreshes view
- [ ] Deleting task brief removes from view

### Commands

- [ ] **Refresh Memory Browser**: Re-fetches KG entities
- [ ] **Refresh Findings Panel**: Re-fetches quality findings
- [ ] **Refresh Tasks Panel**: Reloads task briefs
- [ ] **Search Memory**: Opens input box, searches KG, updates view
- [ ] **View Dashboard**: Opens dashboard webview
- [ ] **Validate All Quality Gates**: Shows notification with results
- [ ] **Connect to MCP Servers**: Manually connects, updates status bar

### Status Bar

- [ ] Shows health: Active (green), Inactive (gray), Error (red)
- [ ] Shows finding count: "N findings"
- [ ] Shows phase: "Phase: active/inactive"
- [ ] Clicking opens dashboard (if implemented)

## Writing New Tests

### Unit Test Template

```typescript
import * as assert from 'assert';
import { MyClass } from '../path/to/MyClass';

suite('MyClass Test Suite', () => {
  let instance: MyClass;

  setup(() => {
    instance = new MyClass();
  });

  test('should do something', () => {
    const result = instance.method();
    assert.strictEqual(result, expected);
  });

  teardown(() => {
    // Cleanup
  });
});
```

### Integration Test Template

```typescript
suite('Integration Tests (requires live server)', () => {
  test.skip('should interact with server', async () => {
    await mcpClient.connect();
    const result = await client.method();
    assert.ok(result);
  });
});
```

**Important**: Mark integration tests with `test.skip` so they don't run by default.

## Test Data Setup

### Populate Test KG Data

```typescript
// Via KG client
await kgClient.createEntities([
  {
    name: 'test_vision',
    entityType: 'vision_standard',
    observations: ['protection_tier: vision', 'All tests must pass'],
  },
  {
    name: 'test_arch',
    entityType: 'pattern',
    observations: ['protection_tier: architecture', 'Use DI pattern'],
  },
  {
    name: 'test_quality',
    entityType: 'component',
    observations: ['protection_tier: quality', 'Needs refactoring'],
  },
]);
```

### Populate Test Quality Data

```typescript
// Via Quality client
await qualityClient.runLint({
  files: ['src/test/fixtures/bad-code.py'],
  language: 'python',
});
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Extension Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Install dependencies
        run: cd extension && npm install
      - name: Run unit tests
        run: cd extension && npm test
```

**Note**: Integration tests require MCP servers, so they're skipped in CI by default.

## Troubleshooting Tests

### "Cannot find module 'vscode'"
**Cause**: VS Code API not available in test environment
**Fix**: Tests must run in VS Code Extension Development Host
**Solution**: Use `@vscode/test-electron` for integration tests

### "Connection refused to localhost:3101"
**Cause**: MCP servers not running
**Fix**: Start servers before running integration tests

### "Test timeout"
**Cause**: Server taking too long to respond
**Fix**: Increase timeout in test setup:
```typescript
setup(function() {
  this.timeout(10000); // 10 seconds
});
```

### "Module not found" during npm test
**Cause**: TypeScript compilation failed
**Fix**: Run `npm run build` manually to see compilation errors

## Test Metrics

**Target Coverage**: 80% for testable code

**Current Coverage**:
- Unit tests: 100% of provider logic, client initialization
- Integration tests: Defined but skipped (require live servers)
- Manual tests: Checklist covers all UI interactions

**Excluded from Coverage**:
- VS Code API interactions (mocked in tests)
- Webview rendering (manual testing)
- File system watchers (integration tests)

## See Also

- [README.md](./README.md) - Extension documentation
- [../../mcp-servers/knowledge-graph/README.md](../../mcp-servers/knowledge-graph/README.md) - KG server documentation
- [../../mcp-servers/quality/README.md](../../mcp-servers/quality/README.md) - Quality server documentation
- [../../.claude/VALIDATION.md](../../.claude/VALIDATION.md) - System validation guide
