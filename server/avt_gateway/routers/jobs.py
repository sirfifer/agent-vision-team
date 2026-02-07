"""Job submission and management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from ..auth import require_auth
from ..models.jobs import JobSubmission
from ..services.job_runner import get_job_runner

router = APIRouter(prefix="/api/jobs", tags=["jobs"], dependencies=[Depends(require_auth)])


@router.post("")
async def submit_job(body: JobSubmission) -> dict:
    """Submit a new job to the Claude CLI queue."""
    runner = get_job_runner()
    job = await runner.submit(
        prompt=body.prompt,
        agent_type=body.agent_type,
        model=body.model,
    )
    return {"job": job.model_dump()}


@router.get("")
async def list_jobs() -> dict:
    """List all jobs with status."""
    runner = get_job_runner()
    return {"jobs": [j.model_dump() for j in runner.list_jobs()]}


@router.get("/{job_id}")
async def get_job(job_id: str) -> dict:
    """Get job detail."""
    runner = get_job_runner()
    job = runner.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return {"job": job.model_dump()}


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str) -> dict:
    """Cancel a queued or running job."""
    runner = get_job_runner()
    cancelled = await runner.cancel_job(job_id)
    if not cancelled:
        raise HTTPException(status_code=400, detail="Job cannot be cancelled (not found or already completed)")
    return {"success": True, "jobId": job_id}
