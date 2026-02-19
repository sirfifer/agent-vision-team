# AVT Gateway

## Type

component

## Description

FastAPI backend providing REST API access to all three MCP servers, WebSocket push notifications, and a job runner for remote/asynchronous operations. Serves as the API layer for the standalone dashboard mode.

## Usage

External clients (React Dashboard in standalone mode) connect via HTTP REST endpoints and WebSocket. The gateway proxies requests to MCP servers using SSE-based MCP connections.

## Internal Structure

```mermaid
graph TD
    App["FastAPI App<br/>(app.py)"]
    Routers["14 Routers<br/>(routers/)"]
    Services["10 Services<br/>(services/)"]
    WS["WebSocket<br/>(ws/)"]
    MCP["MCP SSE Client<br/>(mcp_client.py)"]
    Jobs["Job Runner<br/>(jobs/)"]

    App --> Routers
    App --> WS
    Routers --> Services
    Services --> MCP
    Jobs --> Services
    MCP --> |SSE| KG["KG Server"]
    MCP --> |SSE| QS["Quality Server"]
    MCP --> |SSE| GOV["Governance Server"]
```

## Dependencies

- `fastapi`: Web framework
- `uvicorn`: ASGI server
- SSE client for MCP server communication

## Patterns Used

- SSE-Based MCP Connection (P4)
- Router/Service layering
