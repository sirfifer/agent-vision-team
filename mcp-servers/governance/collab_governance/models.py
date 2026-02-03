"""Pydantic models for governance decisions, reviews, and verdicts."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
import uuid


class DecisionCategory(str, Enum):
    PATTERN_CHOICE = "pattern_choice"
    COMPONENT_DESIGN = "component_design"
    API_DESIGN = "api_design"
    DEVIATION = "deviation"
    SCOPE_CHANGE = "scope_change"


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Verdict(str, Enum):
    APPROVED = "approved"
    BLOCKED = "blocked"
    NEEDS_HUMAN_REVIEW = "needs_human_review"


class Alternative(BaseModel):
    option: str
    reason_rejected: str


class Decision(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    task_id: str
    sequence: int = 0
    agent: str
    category: DecisionCategory
    summary: str
    detail: str = ""
    components_affected: list[str] = Field(default_factory=list)
    alternatives_considered: list[Alternative] = Field(default_factory=list)
    confidence: Confidence = Confidence.HIGH
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class Finding(BaseModel):
    tier: str
    severity: str
    description: str
    suggestion: str = ""


class ReviewVerdict(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    decision_id: Optional[str] = None
    plan_id: Optional[str] = None
    verdict: Verdict
    findings: list[Finding] = Field(default_factory=list)
    guidance: str = ""
    standards_verified: list[str] = Field(default_factory=list)
    reviewer: str = "governance-reviewer"
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class GovernanceRecord(BaseModel):
    """Combined decision + review for history queries."""

    decision: Decision
    review: Optional[ReviewVerdict] = None
