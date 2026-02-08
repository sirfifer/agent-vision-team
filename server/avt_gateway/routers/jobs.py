"""Job submission and management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_auth
from ..app_state import ProjectState
from ..deps import get_project_state
from ..models.jobs import JobSubmission

router = APIRouter(prefix="/jobs", tags=["jobs"], dependencies=[Depends(require_auth)])


@router.post("")
async def submit_job(body: JobSubmission, state: ProjectState = Depends(get_project_state)) -> dict:
    """Submit a new job to the Claude CLI queue."""
    runner = state.get_job_runner()
    job = await runner.submit(
        prompt=body.prompt,
        agent_type=body.agent_type,
        model=body.model,
    )
    return {"job": job.model_dump()}


@router.get("")
async def list_jobs(state: ProjectState = Depends(get_project_state)) -> dict:
    """List all jobs with status."""
    runner = state.get_job_runner()
    return {"jobs": [j.model_dump() for j in runner.list_jobs()]}


@router.get("/{job_id}")
async def get_job(job_id: str, state: ProjectState = Depends(get_project_state)) -> dict:
    """Get job detail."""
    runner = state.get_job_runner()
    job = runner.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return {"job": job.model_dump()}


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str, state: ProjectState = Depends(get_project_state)) -> dict:
    """Cancel a queued or running job."""
    runner = state.get_job_runner()
    cancelled = await runner.cancel_job(job_id)
    if not cancelled:
        raise HTTPException(status_code=400, detail="Job cannot be cancelled (not found or already completed)")
    return {"success": True, "jobId": job_id}
