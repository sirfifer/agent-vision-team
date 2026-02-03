import { CollabConfig, loadConfig } from '../utils/config';
import { logSystem } from '../utils/logger';

/**
 * A persistent MCP SSE connection to a single server.
 * Protocol: GET /sse → session_id → initialize → tools/call via POST → results via SSE
 */
class McpSseConnection {
  private baseUrl: string;
  private messagesUrl: string | null = null;
  private reader: ReadableStreamDefaultReader<Uint8Array> | null = null;
  private pendingRequests: Map<number, { resolve: (v: unknown) => void; reject: (e: Error) => void }> = new Map();
  private nextId = 1;
  private initialized = false;
  private sseController: AbortController | null = null;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  async connect(): Promise<void> {
    this.sseController = new AbortController();
    const response = await fetch(`${this.baseUrl}/sse`, { signal: this.sseController.signal });
    if (!response.ok) {
      throw new Error(`SSE connection failed (status ${response.status})`);
    }

    this.reader = response.body!.getReader();

    // Read the endpoint event to get session_id
    const sessionId = await this.readSessionId();
    this.messagesUrl = `${this.baseUrl}/messages/?session_id=${sessionId}`;
    logSystem(`SSE session established: ${sessionId}`);

    // Start background reader for SSE events
    this.startEventReader();

    // MCP initialize handshake
    await this.initialize();
  }

  disconnect(): void {
    this.sseController?.abort();
    this.reader = null;
    this.messagesUrl = null;
    this.initialized = false;
    this.pendingRequests.forEach(({ reject }) => reject(new Error('Connection closed')));
    this.pendingRequests.clear();
  }

  private async readSessionId(): Promise<string> {
    const decoder = new TextDecoder();
    let buffer = '';

    while (this.reader) {
      const { done, value } = await this.reader.read();
      if (done) {
        throw new Error('SSE stream ended before session');
      }

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');

      for (const line of lines) {
        if (line.startsWith('data:')) {
          const data = line.slice(5).trim();
          if (data.includes('session_id=')) {
            return data.split('session_id=')[1];
          }
        }
      }
    }
    throw new Error('Reader closed before session');
  }

  private startEventReader(): void {
    const decoder = new TextDecoder();
    let buffer = '';
    let currentEventType = '';

    const read = async () => {
      try {
        while (this.reader) {
          const { done, value } = await this.reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // Process complete lines
          while (buffer.includes('\n')) {
            const newlineIdx = buffer.indexOf('\n');
            const line = buffer.slice(0, newlineIdx).trim();
            buffer = buffer.slice(newlineIdx + 1);

            if (line.startsWith('event:')) {
              currentEventType = line.slice(6).trim();
            } else if (line.startsWith('data:') && currentEventType === 'message') {
              const data = line.slice(5).trim();
              try {
                const parsed = JSON.parse(data);
                this.handleResponse(parsed);
              } catch {
                logSystem(`Failed to parse SSE data: ${data.slice(0, 100)}`);
              }
              currentEventType = '';
            }
          }
        }
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        if (!msg.includes('abort')) {
          logSystem(`SSE reader error: ${msg}`);
        }
      }
    };

    // Fire and forget — runs in background
    read();
  }

  private handleResponse(data: { id?: number; result?: unknown; error?: { message: string } }): void {
    if (data.id !== undefined && this.pendingRequests.has(data.id)) {
      const pending = this.pendingRequests.get(data.id)!;
      this.pendingRequests.delete(data.id);

      if (data.error) {
        pending.reject(new Error(data.error.message));
      } else {
        pending.resolve(data.result);
      }
    }
  }

  private async initialize(): Promise<void> {
    // Send initialize request
    await this.sendRequest('initialize', {
      protocolVersion: '2024-11-05',
      capabilities: {},
      clientInfo: { name: 'collab-intelligence-vscode', version: '0.1.0' },
    });

    // Send initialized notification (no id, no response expected)
    await fetch(this.messagesUrl!, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        jsonrpc: '2.0',
        method: 'notifications/initialized',
      }),
    });

    this.initialized = true;
    logSystem('MCP session initialized');
  }

  async sendRequest(method: string, params: Record<string, unknown>): Promise<unknown> {
    if (!this.messagesUrl) {
      throw new Error('Not connected');
    }

    const id = this.nextId++;

    return new Promise((resolve, reject) => {
      // Set up timeout
      const timeout = setTimeout(() => {
        this.pendingRequests.delete(id);
        reject(new Error(`Request ${method} timed out after 10s`));
      }, 10000);

      this.pendingRequests.set(id, {
        resolve: (v) => { clearTimeout(timeout); resolve(v); },
        reject: (e) => { clearTimeout(timeout); reject(e); },
      });

      // POST the request
      fetch(this.messagesUrl!, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          jsonrpc: '2.0',
          id,
          method,
          params,
        }),
      }).then(r => {
        if (r.status !== 202 && r.status !== 200) {
          this.pendingRequests.delete(id);
          clearTimeout(timeout);
          reject(new Error(`POST failed with status ${r.status}`));
        }
      }).catch(err => {
        this.pendingRequests.delete(id);
        clearTimeout(timeout);
        reject(err);
      });
    });
  }

  async callTool(name: string, args: Record<string, unknown>): Promise<unknown> {
    if (!this.initialized) {
      throw new Error('Connection not initialized');
    }

    const result = await this.sendRequest('tools/call', { name, arguments: args }) as {
      content?: Array<{ type: string; text?: string }>;
      structuredContent?: unknown;
    };

    // Prefer structuredContent if available
    if (result.structuredContent !== undefined) {
      const sc = result.structuredContent as Record<string, unknown>;
      // Server wraps results in { result: ... } — unwrap if present
      if (sc.result !== undefined) {
        return sc.result;
      }
      return sc;
    }

    // Fall back to parsing text content
    if (result.content) {
      const textContent = result.content.find(c => c.type === 'text');
      if (textContent?.text) {
        try {
          return JSON.parse(textContent.text);
        } catch {
          return textContent.text;
        }
      }
    }

    return result;
  }
}

export class McpClientService {
  private config: CollabConfig;
  private connected = false;
  private kgUrl: string;
  private qualityUrl: string;
  private governanceUrl: string;
  private kgConnection: McpSseConnection | null = null;
  private qualityConnection: McpSseConnection | null = null;
  private governanceConnection: McpSseConnection | null = null;

  constructor() {
    this.config = loadConfig();
    this.kgUrl = `http://localhost:${this.config.servers['knowledge-graph'].port}`;
    this.qualityUrl = `http://localhost:${this.config.servers.quality.port}`;
    this.governanceUrl = `http://localhost:${this.config.servers.governance.port}`;
  }

  async connect(): Promise<void> {
    logSystem('Connecting to MCP servers...');
    try {
      this.kgConnection = new McpSseConnection(this.kgUrl);
      await this.kgConnection.connect();

      this.qualityConnection = new McpSseConnection(this.qualityUrl);
      await this.qualityConnection.connect();

      this.governanceConnection = new McpSseConnection(this.governanceUrl);
      await this.governanceConnection.connect();

      this.connected = true;
      logSystem('Connected to all MCP servers.');
    } catch (error) {
      logSystem(`Failed to connect to MCP servers: ${error}`);
      this.disconnect();
      throw error;
    }
  }

  async disconnect(): Promise<void> {
    logSystem('Disconnecting from MCP servers...');
    this.kgConnection?.disconnect();
    this.qualityConnection?.disconnect();
    this.governanceConnection?.disconnect();
    this.kgConnection = null;
    this.qualityConnection = null;
    this.governanceConnection = null;
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

  getGovernanceUrl(): string {
    return this.governanceUrl;
  }

  async callTool(server: 'knowledge-graph' | 'quality' | 'governance', tool: string, args: Record<string, unknown>): Promise<unknown> {
    const connectionMap: Record<string, McpSseConnection | null> = {
      'knowledge-graph': this.kgConnection,
      quality: this.qualityConnection,
      governance: this.governanceConnection,
    };
    const connection = connectionMap[server];
    if (!connection) {
      throw new Error(`Not connected to ${server}. Run "Connect to MCP Servers" first.`);
    }

    logSystem(`Calling ${server}/${tool} with ${JSON.stringify(args)}`);

    try {
      const result = await connection.callTool(tool, args);
      logSystem(`Result from ${server}/${tool}: ${JSON.stringify(result).slice(0, 200)}`);
      return result;
    } catch (error) {
      logSystem(`Tool call failed: ${error}`);
      throw error;
    }
  }
}
