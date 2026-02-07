"""Job submission and status models."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobSubmission(BaseModel):
    prompt: str
    agent_type: str | None = None
    model: str = "opus"


class Job(BaseModel):
    id: str
    prompt: str
    agent_type: str | None = None
    model: str = "opus"
    status: JobStatus = JobStatus.QUEUED
    submitted_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: str | None = None
    completed_at: str | None = None
    output: str = ""
    exit_code: int | None = None
    error: str | None = None
