"""Project configuration endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..app_state import ProjectState
from ..auth import require_auth
from ..deps import get_project_state

router = APIRouter(tags=["config"], dependencies=[Depends(require_auth)])


@router.get("/config")
async def get_config(state: ProjectState = Depends(get_project_state)) -> dict:
    """Get project configuration."""
    return state.project_config.load()


@router.put("/config")
async def save_config(config: dict, state: ProjectState = Depends(get_project_state)) -> dict:
    """Save project configuration."""
    state.project_config.save(config)
    return {"success": True}


@router.get("/config/permissions")
async def get_permissions(state: ProjectState = Depends(get_project_state)) -> dict:
    """Get current permissions."""
    cfg = state.project_config.load()
    return {"permissions": cfg.get("permissions", [])}


@router.put("/config/permissions")
async def save_permissions(body: dict, state: ProjectState = Depends(get_project_state)) -> dict:
    """Save permissions and sync to .claude/settings.local.json."""
    permissions = body.get("permissions", [])
    state.project_config.sync_permissions(permissions)

    # Also save to project config
    cfg = state.project_config.load()
    cfg["permissions"] = permissions
    state.project_config.save(cfg)

    return {"success": True}


@router.get("/setup/readiness")
async def get_readiness(state: ProjectState = Depends(get_project_state)) -> dict:
    """Get setup readiness status."""
    return state.project_config.get_readiness()
