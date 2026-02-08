"""FastAPI dependencies for per-project state resolution."""

from __future__ import annotations

from fastapi import HTTPException, Path

from .app_state import ProjectState, registry


async def get_project_state(
    project_id: str = Path(..., description="Project identifier"),
) -> ProjectState:
    """Resolve project_id path parameter to a ProjectState instance."""
    state = registry.get_or_none(project_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
    return state
