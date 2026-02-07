"""Health check endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from ..app_state import state

router = APIRouter(tags=["health"])


@router.get("/api/health")
async def health_check() -> dict:
    """Check Gateway and MCP server health."""
    mcp_connected = state.mcp.is_connected if state.mcp else False
    return {
        "status": "ok" if mcp_connected else "degraded",
        "mcp_connected": mcp_connected,
        "version": "0.1.0",
    }
