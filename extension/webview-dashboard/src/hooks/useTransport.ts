/**
 * Transport abstraction: VS Code webview postMessage vs HTTP+WebSocket.
 *
 * Detects the runtime environment and provides the appropriate transport.
 * In VS Code: uses acquireVsCodeApi().postMessage (existing behavior)
 * In browser: sends HTTP requests to the Gateway API + WebSocket for server-push events
 */

import type { WebviewMessage, ExtensionMessage } from '../types';

export interface Transport {
  postMessage(message: unknown): void;
  getState(): unknown;
  setState(state: unknown): void;
}

// ── VS Code transport ────────────────────────────────────────────────────

declare function acquireVsCodeApi(): {
  postMessage(message: unknown): void;
  getState(): unknown;
  setState(state: unknown): void;
};

let vscodeApi: Transport | undefined;

function createVsCodeTransport(): Transport {
  if (!vscodeApi) {
    vscodeApi = acquireVsCodeApi();
  }
  return vscodeApi;
}

// ── Web transport ────────────────────────────────────────────────────────

/** Message type to HTTP endpoint mapping */
const MESSAGE_ROUTES: Record<string, { method: string; path: string; bodyKey?: string }> = {
  connect:              { method: 'POST', path: '/api/mcp/connect' },
  refresh:              { method: 'POST', path: '/api/refresh' },
  validate:             { method: 'POST', path: '/api/quality/validate' },
  checkSetup:           { method: 'GET',  path: '/api/setup/readiness' },
  saveProjectConfig:    { method: 'PUT',  path: '/api/config', bodyKey: 'config' },
  openSettings:         { method: 'GET',  path: '/api/config' },
  savePermissions:      { method: 'PUT',  path: '/api/config/permissions' },
  listVisionDocs:       { method: 'GET',  path: '/api/documents/vision' },
  listArchDocs:         { method: 'GET',  path: '/api/documents/architecture' },
  listResearchPrompts:  { method: 'GET',  path: '/api/research-prompts' },
  listResearchBriefs:   { method: 'GET',  path: '/api/research-briefs' },
  requestGovernedTasks: { method: 'GET',  path: '/api/governance/tasks' },
  requestFindings:      { method: 'GET',  path: '/api/quality/findings' },
};

function getApiBase(): string {
  // In production, the API is at the same origin (behind nginx)
  // In dev, use the AVT_API_BASE env var or default to localhost:8080
  return (window as any).__AVT_API_BASE__ || '';
}

function getApiKey(): string {
  return (window as any).__AVT_API_KEY__ || '';
}

function createWebTransport(): Transport {
  const apiBase = getApiBase();
  const apiKey = getApiKey();
  let ws: WebSocket | null = null;

  // Connect WebSocket for server-push events
  function connectWs() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsBase = apiBase ? new URL(apiBase).host : window.location.host;
    const wsUrl = `${protocol}//${wsBase}/api/ws?token=${apiKey}`;

    ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        // Dispatch as a window message event (same as VS Code postMessage)
        window.dispatchEvent(new MessageEvent('message', { data: mapWsEvent(msg) }));
      } catch {
        // ignore parse errors
      }
    };

    ws.onclose = () => {
      // Reconnect after 3 seconds
      setTimeout(connectWs, 3000);
    };

    ws.onerror = () => {
      ws?.close();
    };
  }

  // Map WebSocket server events to the ExtensionMessage types the dashboard expects
  function mapWsEvent(msg: { type: string; data: any }): ExtensionMessage | null {
    switch (msg.type) {
      case 'dashboard_update':
        return { type: 'update', data: msg.data };
      case 'governance_stats':
        return { type: 'governanceStats', stats: msg.data };
      case 'governed_tasks':
        return { type: 'governedTasks', tasks: msg.data.tasks || msg.data };
      case 'job_status':
        // Jobs are a new feature; broadcast as activity for now
        return { type: 'activityAdd', entry: {
          id: msg.data.id,
          timestamp: msg.data.completed_at || msg.data.started_at || msg.data.submitted_at,
          agent: 'job-runner',
          type: 'status',
          summary: `Job ${msg.data.id}: ${msg.data.status}`,
        }};
      default:
        // Pass through as-is for types that match exactly
        return msg as any;
    }
  }

  // Start WebSocket connection
  connectWs();

  // Map postMessage calls to HTTP requests
  async function sendToApi(message: any) {
    const type = message.type as string;
    const route = MESSAGE_ROUTES[type];

    if (route) {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (apiKey) {
        headers['Authorization'] = `Bearer ${apiKey}`;
      }

      const url = `${apiBase}${route.path}`;
      const init: RequestInit = {
        method: route.method,
        headers,
      };

      if (route.method !== 'GET') {
        if (route.bodyKey) {
          init.body = JSON.stringify(message[route.bodyKey]);
        } else {
          init.body = JSON.stringify(message);
        }
      }

      try {
        const resp = await fetch(url, init);
        const data = await resp.json();
        // Dispatch response as a window message event
        const responseMsg = mapApiResponse(type, data);
        if (responseMsg) {
          window.dispatchEvent(new MessageEvent('message', { data: responseMsg }));
        }
      } catch (err) {
        console.error(`API call failed for ${type}:`, err);
      }
      return;
    }

    // Handle specific messages that need custom routing
    switch (type) {
      case 'createVisionDoc':
        await apiPost(`/api/documents/vision`, { name: message.name, content: message.content });
        break;
      case 'createArchDoc':
        await apiPost(`/api/documents/architecture`, { name: message.name, content: message.content });
        break;
      case 'ingestDocs':
        await apiPost(`/api/documents/${message.tier}/ingest`, {});
        break;
      case 'saveResearchPrompt':
        await apiPut(`/api/research-prompts/${message.prompt.id}`, message.prompt);
        break;
      case 'deleteResearchPrompt':
        await apiDelete(`/api/research-prompts/${message.id}`);
        break;
      case 'runResearchPrompt':
        await apiPost(`/api/research-prompts/${message.id}/run`, {});
        break;
      case 'formatDocContent':
        await apiPost(`/api/documents/${message.tier}/format`, {
          rawContent: message.rawContent,
          requestId: message.requestId,
        });
        break;
      case 'dismissFinding':
        await apiPost(`/api/quality/findings/${message.findingId}/dismiss`, {
          justification: message.justification,
          dismissedBy: message.dismissedBy,
        });
        break;
      case 'readResearchBrief':
        await apiGet(`/api/research-briefs/${encodeURIComponent(message.briefPath)}`);
        break;
      default:
        console.log('Unhandled message type:', type, message);
    }
  }

  async function apiGet(path: string) {
    const headers: Record<string, string> = {};
    if (apiKey) headers['Authorization'] = `Bearer ${apiKey}`;
    try {
      const resp = await fetch(`${apiBase}${path}`, { headers });
      return await resp.json();
    } catch (err) {
      console.error('API GET failed:', path, err);
    }
  }

  async function apiPost(path: string, body: any) {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (apiKey) headers['Authorization'] = `Bearer ${apiKey}`;
    try {
      const resp = await fetch(`${apiBase}${path}`, { method: 'POST', headers, body: JSON.stringify(body) });
      return await resp.json();
    } catch (err) {
      console.error('API POST failed:', path, err);
    }
  }

  async function apiPut(path: string, body: any) {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (apiKey) headers['Authorization'] = `Bearer ${apiKey}`;
    try {
      const resp = await fetch(`${apiBase}${path}`, { method: 'PUT', headers, body: JSON.stringify(body) });
      return await resp.json();
    } catch (err) {
      console.error('API PUT failed:', path, err);
    }
  }

  async function apiDelete(path: string) {
    const headers: Record<string, string> = {};
    if (apiKey) headers['Authorization'] = `Bearer ${apiKey}`;
    try {
      const resp = await fetch(`${apiBase}${path}`, { method: 'DELETE', headers });
      return await resp.json();
    } catch (err) {
      console.error('API DELETE failed:', path, err);
    }
  }

  /** Map API response to ExtensionMessage that the DashboardContext expects */
  function mapApiResponse(messageType: string, data: any): ExtensionMessage | null {
    switch (messageType) {
      case 'refresh':
      case 'connect':
        return { type: 'update', data };
      case 'checkSetup':
        return { type: 'setupReadiness', readiness: data };
      case 'openSettings':
        return { type: 'projectConfig', config: data };
      case 'listVisionDocs':
        return { type: 'visionDocs', docs: data.docs || [] };
      case 'listArchDocs':
        return { type: 'architectureDocs', docs: data.docs || [] };
      case 'listResearchPrompts':
        return { type: 'researchPrompts', prompts: data.prompts || [] };
      case 'listResearchBriefs':
        return { type: 'researchBriefsList', briefs: data.briefs || [] };
      case 'requestGovernedTasks':
        return { type: 'governedTasks', tasks: data.tasks || [] };
      case 'requestFindings':
        return { type: 'findingsUpdate', findings: data.findings || [] };
      case 'validate':
        return null; // Quality validation results shown via dashboard update
      default:
        return null;
    }
  }

  return {
    postMessage: sendToApi,
    getState: () => {
      try {
        const saved = localStorage.getItem('avt-dashboard-state');
        return saved ? JSON.parse(saved) : undefined;
      } catch {
        return undefined;
      }
    },
    setState: (state: unknown) => {
      try {
        localStorage.setItem('avt-dashboard-state', JSON.stringify(state));
      } catch {
        // ignore
      }
    },
  };
}

// ── Factory ──────────────────────────────────────────────────────────────

let transport: Transport | undefined;

export function useTransport(): Transport {
  if (!transport) {
    try {
      // Try VS Code first
      transport = createVsCodeTransport();
    } catch {
      // Not in VS Code; use web transport
      transport = createWebTransport();
    }
  }
  return transport;
}
