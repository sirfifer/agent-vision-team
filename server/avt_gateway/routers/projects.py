"""Project management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth import require_auth
from ..services.project_manager import get_project_manager

router = APIRouter(prefix="/api/projects", tags=["projects"], dependencies=[Depends(require_auth)])


class AddProjectRequest(BaseModel):
    path: str
    name: str | None = None


@router.get("")
async def list_projects() -> dict:
    """List all registered projects."""
    mgr = get_project_manager()
    return {"projects": [p.model_dump() for p in mgr.list_projects()]}


@router.post("")
async def add_project(req: AddProjectRequest) -> dict:
    """Register a new project directory."""
    mgr = get_project_manager()
    try:
        project = mgr.add_project(req.path, req.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"project": project.model_dump()}


@router.delete("/{project_id}")
async def remove_project(project_id: str) -> dict:
    """Remove a project from the registry."""
    mgr = get_project_manager()
    try:
        mgr.remove_project(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"removed": project_id}


@router.post("/{project_id}/start")
async def start_project(project_id: str) -> dict:
    """Start MCP servers for a project and connect."""
    mgr = get_project_manager()
    try:
        project = mgr.start_project(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    # Register project state and connect MCP client
    from ..app_state import registry
    from pathlib import Path
    state = registry.register(
        project_id,
        Path(project.path),
        (project.kg_port, project.quality_port, project.governance_port),
    )

    try:
        await state.connect_mcp()
    except ConnectionError as exc:
        # MCP servers may need a moment to start; return partial success
        pass

    return {"project": project.model_dump()}


@router.post("/{project_id}/stop")
async def stop_project(project_id: str) -> dict:
    """Stop MCP servers for a project."""
    mgr = get_project_manager()
    project = mgr.stop_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

    # Disconnect MCP and remove state
    from ..app_state import registry
    state = registry.get_or_none(project_id)
    if state:
        await state.disconnect_mcp()
        registry.remove(project_id)

    return {"project": project.model_dump()}


@router.get("/{project_id}/health")
async def project_health(project_id: str) -> dict:
    """Check MCP server health for a project."""
    mgr = get_project_manager()
    project = mgr.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
    return {"health": mgr.check_health(project_id), "status": project.status.value}
