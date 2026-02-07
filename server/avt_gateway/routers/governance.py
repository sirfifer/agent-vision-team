"""Governance endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_auth
from ..app_state import state

router = APIRouter(prefix="/api/governance", tags=["governance"], dependencies=[Depends(require_auth)])


@router.get("/tasks")
async def get_governed_tasks() -> dict:
    """Get all governed tasks."""
    if not state.mcp or not state.mcp.is_connected:
        raise HTTPException(status_code=503, detail="MCP servers not connected")

    try:
        result = await state.mcp.call_tool("governance", "list_governed_tasks")
        if isinstance(result, dict):
            return {"tasks": result.get("governed_tasks", [])}
        return {"tasks": []}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/status")
async def get_governance_status() -> dict:
    """Get governance dashboard summary."""
    if not state.mcp or not state.mcp.is_connected:
        raise HTTPException(status_code=503, detail="MCP servers not connected")

    try:
        result = await state.mcp.call_tool("governance", "get_governance_status")
        return result if isinstance(result, dict) else {}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/decisions")
async def get_decision_history() -> dict:
    """Get governance decision history."""
    if not state.mcp or not state.mcp.is_connected:
        raise HTTPException(status_code=503, detail="MCP servers not connected")

    try:
        result = await state.mcp.call_tool("governance", "get_decision_history")
        if isinstance(result, dict):
            return {"decisions": result.get("decisions", [])}
        return {"decisions": []}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
