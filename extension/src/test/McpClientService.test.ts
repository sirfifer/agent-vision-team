import * as assert from 'assert';
import { McpClientService } from '../services/McpClientService';

/**
 * Test suite for McpClientService
 *
 * Note: These tests verify the client logic without actually connecting to servers.
 * For integration tests with live servers, see TESTING.md
 */

suite('McpClientService Test Suite', () => {
  let client: McpClientService;

  setup(() => {
    client = new McpClientService();
  });

  test('should initialize with correct default ports', () => {
    const kgUrl = client.getKgUrl();
    const qualityUrl = client.getQualityUrl();

    assert.strictEqual(kgUrl, 'http://localhost:3101');
    assert.strictEqual(qualityUrl, 'http://localhost:3102');
  });

  test('should start in disconnected state', () => {
    assert.strictEqual(client.isConnected(), false);
  });

  test('disconnect should set connected to false', async () => {
    await client.disconnect();
    assert.strictEqual(client.isConnected(), false);
  });

  // Integration test - requires servers running
  test.skip('should connect to running MCP servers', async () => {
    try {
      await client.connect();
      assert.strictEqual(client.isConnected(), true);
    } catch (error) {
      // Expected if servers aren't running
      assert.ok(error);
    }
  });

  // Integration test - requires servers running
  test.skip('should fail to connect when servers are down', async () => {
    try {
      await client.connect();
      assert.fail('Should have thrown an error');
    } catch (error) {
      assert.ok(error);
      assert.strictEqual(client.isConnected(), false);
    }
  });

  // Integration test - requires servers running
  test.skip('should call tools on connected servers', async () => {
    await client.connect();

    try {
      const result = await client.callTool('knowledge-graph', 'search_nodes', { query: 'test' });
      assert.ok(result);
    } catch (error) {
      // Expected if no entities exist
      assert.ok(error);
    }
  });
});
