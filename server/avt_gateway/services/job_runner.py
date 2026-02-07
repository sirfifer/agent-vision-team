"""Job runner: queues and executes Claude CLI jobs."""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from ..config import config
from ..models.jobs import Job, JobStatus

logger = logging.getLogger(__name__)

# Module-level singleton
_runner: JobRunner | None = None


def get_job_runner() -> JobRunner:
    """Get (or create) the singleton JobRunner."""
    global _runner
    if _runner is None:
        _runner = JobRunner()
    return _runner


class JobRunner:
    """Manages a queue of Claude Code CLI invocations."""

    def __init__(self, max_concurrent: int = 1) -> None:
        self.max_concurrent = max_concurrent
        self._jobs: dict[str, Job] = {}
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._worker_task: asyncio.Task | None = None
        self._jobs_dir = config.avt_root / "jobs"
        self._jobs_dir.mkdir(parents=True, exist_ok=True)

        # Load persisted jobs
        self._load_persisted_jobs()

    async def submit(self, prompt: str, agent_type: str | None = None, model: str = "opus") -> Job:
        """Submit a new job. Returns immediately with the job."""
        job = Job(
            id=str(uuid.uuid4())[:8],
            prompt=prompt,
            agent_type=agent_type,
            model=model,
        )
        self._jobs[job.id] = job
        self._persist_job(job)
        await self._queue.put(job.id)

        # Ensure worker is running
        self._ensure_worker()

        logger.info("Job %s submitted: %s", job.id, prompt[:80])
        return job

    def get_job(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def list_jobs(self) -> list[Job]:
        return sorted(self._jobs.values(), key=lambda j: j.submitted_at, reverse=True)

    async def cancel_job(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if not job:
            return False
        if job.status == JobStatus.RUNNING:
            # Cannot cancel a running subprocess easily; mark as cancelled
            job.status = JobStatus.CANCELLED
            job.completed_at = datetime.now(timezone.utc).isoformat()
            self._persist_job(job)
            return True
        if job.status == JobStatus.QUEUED:
            job.status = JobStatus.CANCELLED
            job.completed_at = datetime.now(timezone.utc).isoformat()
            self._persist_job(job)
            return True
        return False

    # ── Internal ──────────────────────────────────────────────────────────

    def _ensure_worker(self) -> None:
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._worker())

    async def _worker(self) -> None:
        """Background worker that processes jobs from the queue."""
        while True:
            try:
                job_id = await self._queue.get()
                job = self._jobs.get(job_id)
                if not job or job.status == JobStatus.CANCELLED:
                    continue

                await self._execute_job(job)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Worker error: %s", exc)

    async def _execute_job(self, job: Job) -> None:
        """Execute a single job via Claude CLI."""
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(timezone.utc).isoformat()
        self._persist_job(job)

        # Broadcast status update
        await self._broadcast_status(job)

        loop = asyncio.get_running_loop()
        try:
            output = await loop.run_in_executor(None, self._run_claude, job)
            job.output = output
            job.status = JobStatus.COMPLETED
            job.exit_code = 0
        except subprocess.TimeoutExpired:
            job.status = JobStatus.FAILED
            job.error = "Job timed out (10 minutes)"
            job.exit_code = -1
        except Exception as exc:
            job.status = JobStatus.FAILED
            job.error = str(exc)
            job.exit_code = -1

        job.completed_at = datetime.now(timezone.utc).isoformat()
        self._persist_job(job)
        await self._broadcast_status(job)
        logger.info("Job %s completed with status %s", job.id, job.status.value)

    def _run_claude(self, job: Job) -> str:
        """Run Claude CLI synchronously (called from executor)."""
        input_fd, input_path = tempfile.mkstemp(suffix="-input.md", prefix=f"avt-job-{job.id}-")
        output_fd, output_path = tempfile.mkstemp(suffix="-output.md", prefix=f"avt-job-{job.id}-")

        try:
            with open(input_fd, "w") as f:
                f.write(job.prompt)

            cmd = ["claude", "--print", "--model", job.model]

            with open(input_path) as fin, open(output_fd, "w") as fout:
                result = subprocess.run(
                    cmd,
                    stdin=fin,
                    stdout=fout,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=600,  # 10 minute timeout
                    cwd=str(config.project_dir),
                )

            job.exit_code = result.returncode
            output = Path(output_path).read_text()

            if result.returncode != 0 and not output:
                raise RuntimeError(f"Claude CLI exited with code {result.returncode}: {result.stderr}")

            return output

        finally:
            Path(input_path).unlink(missing_ok=True)
            Path(output_path).unlink(missing_ok=True)

    def _persist_job(self, job: Job) -> None:
        """Save job state to disk."""
        path = self._jobs_dir / f"{job.id}.json"
        path.write_text(job.model_dump_json(indent=2))

    def _load_persisted_jobs(self) -> None:
        """Load jobs from disk on startup."""
        for f in self._jobs_dir.iterdir():
            if f.suffix == ".json":
                try:
                    data = json.loads(f.read_text())
                    job = Job(**data)
                    # Mark any previously-running jobs as failed (unclean shutdown)
                    if job.status == JobStatus.RUNNING:
                        job.status = JobStatus.FAILED
                        job.error = "Gateway restarted while job was running"
                        job.completed_at = datetime.now(timezone.utc).isoformat()
                    self._jobs[job.id] = job
                except Exception:
                    pass

    async def _broadcast_status(self, job: Job) -> None:
        """Broadcast job status to WebSocket clients."""
        try:
            from ..ws.manager import ws_manager
            await ws_manager.broadcast("job_status", job.model_dump())
        except Exception:
            pass
