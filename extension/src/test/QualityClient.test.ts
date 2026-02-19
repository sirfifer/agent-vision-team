import * as assert from 'assert';
import { QualityClient } from '../mcp/QualityClient';
import { McpClientService } from '../services/McpClientService';

suite('QualityClient Test Suite', () => {
  let mcpClient: McpClientService;
  let qualityClient: QualityClient;

  setup(() => {
    mcpClient = new McpClientService();
    qualityClient = new QualityClient(mcpClient);
  });

  test('should be instantiated with MCP client', () => {
    assert.ok(qualityClient);
  });

  // Integration tests - require live server
  suite('Integration Tests (requires live server)', () => {
    test.skip('should auto format files', async () => {
      await mcpClient.connect();

      const result = await qualityClient.autoFormat({
        files: ['test.py'],
        language: 'python',
      });

      assert.ok(result.formatted);
      assert.ok(result.unchanged);
    });

    test.skip('should run lint', async () => {
      await mcpClient.connect();

      const result = await qualityClient.runLint({
        files: ['test.py'],
        language: 'python',
      });

      assert.ok(Array.isArray(result.findings));
      assert.ok(typeof result.auto_fixable === 'number');
      assert.ok(typeof result.total === 'number');
    });

    test.skip('should run tests', async () => {
      await mcpClient.connect();

      const result = await qualityClient.runTests({
        scope: 'all',
        language: 'python',
      });

      assert.ok(typeof result.passed === 'number');
      assert.ok(typeof result.failed === 'number');
      assert.ok(typeof result.skipped === 'number');
      assert.ok(Array.isArray(result.failures));
    });

    test.skip('should check coverage', async () => {
      await mcpClient.connect();

      const result = await qualityClient.checkCoverage({
        language: 'python',
      });

      assert.ok(typeof result.percentage === 'number');
      assert.ok(typeof result.target === 'number');
      assert.ok(typeof result.met === 'boolean');
      assert.ok(Array.isArray(result.uncovered_files));
    });

    test.skip('should check all gates', async () => {
      await mcpClient.connect();

      const result = await qualityClient.checkAllGates();

      assert.ok(result.build);
      assert.ok(result.lint);
      assert.ok(result.tests);
      assert.ok(result.coverage);
      assert.ok(result.findings);
      assert.ok(typeof result.all_passed === 'boolean');
    });

    test.skip('should validate all', async () => {
      await mcpClient.connect();

      const result = await qualityClient.validate();

      assert.ok(result.gates);
      assert.ok(typeof result.summary === 'string');
      assert.ok(typeof result.all_passed === 'boolean');
    });

    test.skip('should get trust decision', async () => {
      await mcpClient.connect();

      const result = await qualityClient.getTrustDecision('test-finding-1');

      assert.ok(['BLOCK', 'INVESTIGATE', 'TRACK'].includes(result.decision));
      assert.ok(typeof result.rationale === 'string');
    });

    test.skip('should record dismissal', async () => {
      await mcpClient.connect();

      const result = await qualityClient.recordDismissal(
        'test-finding-1',
        'False positive - test file',
        'human',
      );

      assert.ok(typeof result.recorded === 'boolean');
    });
  });
});
