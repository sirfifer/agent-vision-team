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


# =============================================================================
# Task Governance Models
# =============================================================================


class ReviewType(str, Enum):
    """Types of governance reviews."""
    GOVERNANCE = "governance"  # Standard governance review
    SECURITY = "security"      # Security-focused review
    ARCHITECTURE = "architecture"  # Architecture review
    MEMORY = "memory"          # Check against past failures/patterns
    VISION = "vision"          # Vision alignment check
    CUSTOM = "custom"          # Custom review type


class TaskReviewStatus(str, Enum):
    """Status of a task governance review."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    APPROVED = "approved"
    BLOCKED = "blocked"
    NEEDS_HUMAN_REVIEW = "needs_human_review"


class TaskReviewRecord(BaseModel):
    """Record of a governance review for a Claude Code task."""
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    review_task_id: str  # The review task in Claude Code's task system
    implementation_task_id: str  # The implementation task being reviewed
    review_type: ReviewType = ReviewType.GOVERNANCE
    status: TaskReviewStatus = TaskReviewStatus.PENDING
    context: str = ""  # Context provided for the review
    verdict: Optional[Verdict] = None
    guidance: str = ""
    findings: list[Finding] = Field(default_factory=list)
    standards_verified: list[str] = Field(default_factory=list)
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    completed_at: Optional[str] = None
    reviewer: str = "governance-reviewer"


class GovernedTaskRecord(BaseModel):
    """Record tracking a governed task and its reviews."""
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    implementation_task_id: str  # Claude Code task ID
    subject: str
    description: str = ""
    context: str = ""  # Original context for governance
    reviews: list[str] = Field(default_factory=list)  # List of TaskReviewRecord IDs
    current_status: str = "pending_review"  # pending_review, approved, blocked
    session_id: str = ""  # Links tasks created in the same session
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    released_at: Optional[str] = None


class HolisticReviewRecord(BaseModel):
    """Record of a holistic review evaluating multiple tasks collectively."""
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    session_id: str
    task_ids: list[str] = Field(default_factory=list)
    task_subjects: list[str] = Field(default_factory=list)
    collective_intent: str = ""
    verdict: Optional[Verdict] = None
    findings: list[Finding] = Field(default_factory=list)
    guidance: str = ""
    standards_verified: list[str] = Field(default_factory=list)
    reviewer: str = "governance-reviewer"
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
