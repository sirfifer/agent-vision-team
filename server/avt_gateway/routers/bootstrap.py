"""Bootstrap endpoints for project scale assessment."""

from __future__ import annotations

import json
import subprocess

from fastapi import APIRouter, Depends, HTTPException

from ..app_state import ProjectState
from ..auth import require_auth
from ..deps import get_project_state

router = APIRouter(tags=["bootstrap"], dependencies=[Depends(require_auth)])


@router.post("/bootstrap/scale-check")
async def bootstrap_scale_check(state: ProjectState = Depends(get_project_state)) -> dict:
    """Run fast scale assessment (~5s) for the project.

    Executes the bootstrap-scale-check.py script against the project directory
    and returns a scale profile with tier classification, file counts, languages,
    and estimated bootstrap time.
    """
    project_path = str(state.project_dir)
    script_path = str(state.project_dir / "scripts" / "bootstrap-scale-check.py")

    try:
        result = subprocess.run(
            ["uv", "run", "python", script_path, project_path],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=project_path,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Scale check timed out")
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="uv or python not found")

    if result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f"Scale check failed: {result.stderr.strip()[:500]}",
        )

    try:
        profile = json.loads(result.stdout)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail=f"Scale check returned invalid JSON: {result.stdout[:200]}",
        )

    if "error" in profile:
        raise HTTPException(status_code=400, detail=profile["error"])

    return {"profile": profile}
