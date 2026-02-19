# Dual-Mode Transport

## Type

pattern

## Description

The React Dashboard operates in two modes with zero component duplication. In VS Code mode, it communicates via the webview `postMessage` API. In standalone mode, it communicates via HTTP REST and WebSocket through the AVT Gateway. The `useTransport` hook abstracts this difference.

## Structure

```mermaid
graph TB
    Dashboard["React Dashboard"]
    UT["useTransport()"]

    subgraph VS Code Mode
        PM["postMessage API"]
        Ext["Extension Host"]
        MCP1["MCP Servers<br/>(direct)"]
    end

    subgraph Standalone Mode
        HTTP["HTTP/REST"]
        WS["WebSocket"]
        GW["AVT Gateway"]
        MCP2["MCP Servers<br/>(via SSE)"]
    end

    Dashboard --> UT
    UT -->|VS Code| PM
    PM --> Ext
    Ext --> MCP1

    UT -->|Standalone| HTTP
    UT -->|Standalone| WS
    HTTP --> GW
    WS --> GW
    GW --> MCP2
```

## Key Properties

- Environment detection is automatic (checks for VS Code API availability)
- Same React components in both modes
- Transport abstraction in `useTransport.ts`
- VS Code mode: synchronous postMessage round-trips
- Standalone mode: async HTTP with WebSocket push for real-time updates
