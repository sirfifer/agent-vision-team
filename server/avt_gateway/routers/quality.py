"""Quality server endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..app_state import ProjectState
from ..auth import require_auth
from ..deps import get_project_state

router = APIRouter(prefix="/quality", tags=["quality"], dependencies=[Depends(require_auth)])


class DismissRequest(BaseModel):
    justification: str
    dismissedBy: str


@router.post("/validate")
async def validate_all(state: ProjectState = Depends(get_project_state)) -> dict:
    """Run full quality validation."""
    if not state.mcp or not state.mcp.is_connected:
        raise HTTPException(status_code=503, detail="MCP servers not connected")

    try:
        result = await state.mcp.call_tool("quality", "validate")
        return result if isinstance(result, dict) else {"result": result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/findings")
async def get_findings(status: str | None = None, state: ProjectState = Depends(get_project_state)) -> dict:
    """Get all quality findings, optionally filtered by status."""
    if not state.mcp or not state.mcp.is_connected:
        raise HTTPException(status_code=503, detail="MCP servers not connected")

    try:
        args: dict = {}
        if status:
            args["status"] = status
        result = await state.mcp.call_tool("quality", "get_all_findings", args)
        if isinstance(result, dict):
            return {"findings": result.get("findings", [])}
        return {"findings": []}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/findings/{finding_id}/dismiss")
async def dismiss_finding(
    finding_id: str, body: DismissRequest, state: ProjectState = Depends(get_project_state)
) -> dict:
    """Dismiss a quality finding with justification."""
    if not state.mcp or not state.mcp.is_connected:
        raise HTTPException(status_code=503, detail="MCP servers not connected")

    try:
        await state.mcp.call_tool(
            "quality",
            "record_dismissal",
            {
                "finding_id": finding_id,
                "justification": body.justification,
                "dismissed_by": body.dismissedBy,
            },
        )
        return {"success": True, "findingId": finding_id}
    except Exception as exc:
        return {"success": False, "findingId": finding_id, "error": str(exc)}


@router.get("/gates")
async def get_gate_results(state: ProjectState = Depends(get_project_state)) -> dict:
    """Get quality gate results."""
    if not state.mcp or not state.mcp.is_connected:
        raise HTTPException(status_code=503, detail="MCP servers not connected")

    try:
        result = await state.mcp.call_tool("quality", "check_all_gates")
        return result if isinstance(result, dict) else {}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
