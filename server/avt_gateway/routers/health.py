"""Health check endpoint (global, not per-project)."""

from __future__ import annotations

from fastapi import APIRouter

from ..services.project_manager import get_project_manager

router = APIRouter(tags=["health"])


@router.get("/api/health")
async def health_check() -> dict:
    """Check Gateway health and list project statuses."""
    mgr = get_project_manager()
    projects = mgr.list_projects()
    running = sum(1 for p in projects if p.status.value == "running")
    return {
        "status": "ok" if running > 0 else "degraded",
        "version": "0.1.0",
        "projects": {
            "total": len(projects),
            "running": running,
        },
    }
