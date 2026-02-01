import { CollabConfig, loadConfig } from '../utils/config';
import { logSystem } from '../utils/logger';

export class McpClientService {
  private config: CollabConfig;
  private connected = false;
  private kgUrl: string;
  private qualityUrl: string;

  constructor() {
    this.config = loadConfig();
    this.kgUrl = `http://localhost:${this.config.servers['knowledge-graph'].port}`;
    this.qualityUrl = `http://localhost:${this.config.servers.quality.port}`;
  }

  async connect(): Promise<void> {
    logSystem('Connecting to MCP servers...');
    try {
      // Test connectivity to both servers
      await this.ping(this.kgUrl);
      await this.ping(this.qualityUrl);
      this.connected = true;
      logSystem('Connected to MCP servers.');
    } catch (error) {
      logSystem(`Failed to connect to MCP servers: ${error}`);
      this.connected = false;
      throw error;
    }
  }

  async disconnect(): Promise<void> {
    logSystem('Disconnecting from MCP servers...');
    this.connected = false;
    logSystem('Disconnected from MCP servers.');
  }

  isConnected(): boolean {
    return this.connected;
  }

  getKgUrl(): string {
    return this.kgUrl;
  }

  getQualityUrl(): string {
    return this.qualityUrl;
  }

  private async ping(url: string): Promise<void> {
    const response = await fetch(`${url}/health`);
    if (!response.ok) {
      throw new Error(`Server at ${url} is not healthy`);
    }
  }

  async callTool(server: 'knowledge-graph' | 'quality', tool: string, args: Record<string, unknown>): Promise<unknown> {
    const url = server === 'knowledge-graph' ? this.kgUrl : this.qualityUrl;

    logSystem(`Calling ${server}/${tool} with ${JSON.stringify(args)}`);

    try {
      const response = await fetch(`${url}/mcp/call`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          method: 'tools/call',
          params: {
            name: tool,
            arguments: args,
          },
        }),
      });

      if (!response.ok) {
        throw new Error(`Tool call failed: ${response.statusText}`);
      }

      const result = await response.json();

      if (result.error) {
        throw new Error(`Tool error: ${result.error.message}`);
      }

      return result.result;
    } catch (error) {
      logSystem(`Tool call failed: ${error}`);
      throw error;
    }
  }
}
