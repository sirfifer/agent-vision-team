# VS Code Extension

## Type

component

## Description

VS Code extension providing IDE integration for the AVT system. Hosts the React dashboard webview, provides tree view providers for entities, findings, and tasks, wraps MCP server communication, and manages file watchers for real-time updates.

## Usage

Activated automatically when a project with `.avt/` directory is opened. Provides commands, tree views, and the dashboard webview panel.

## Internal Structure

```mermaid
graph TD
    Ext["extension.ts<br/>(activate)"]
    MCS["McpClientService"]
    DWP["DashboardWebviewProvider"]
    TVP["TreeViewProviders"]
    CMD["Command Handlers"]
    FWS["FileWatcherService"]
    PCS["ProjectConfigService"]

    Ext --> MCS
    Ext --> DWP
    Ext --> TVP
    Ext --> CMD
    Ext --> FWS
    Ext --> PCS
    DWP --> MCS
    TVP --> MCS
    CMD --> MCS
    FWS --> DWP
```

## Dependencies

- VS Code Extension API
- MCP servers (via SSE)

## Patterns Used

- SSE-Based MCP Connection (P4)
- Provider pattern (VS Code tree views)
- Webview communication (postMessage bridge)
