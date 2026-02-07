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
    ARCHITECTURE_EVOLUTION = "architecture_evolution"
    EXPERIMENT_PROPOSAL = "experiment_proposal"
    EXPERIMENT_RESULT = "experiment_result"


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
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    released_at: Optional[str] = None


# =============================================================================
# Architectural Evolution Models
# =============================================================================


class EvolutionStatus(str, Enum):
    """Lifecycle states for an evolution proposal."""
    PROPOSED = "proposed"
    EXPERIMENTING = "experimenting"
    VALIDATED = "validated"
    PRESENTED = "presented"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_MORE_EVIDENCE = "needs_more_evidence"


class ExperimentEvidence(BaseModel):
    """A single piece of evidence from an architectural experiment."""
    evidence_type: str  # test_results, benchmark, production_metrics, code_review
    source: str = ""  # Path to test/benchmark output or metric source
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    raw_output: str = ""  # Actual output (truncated if needed)
    summary: str = ""  # Human-readable summary
    metrics: dict = Field(default_factory=dict)  # {metric_name: value}
    comparison_to_baseline: dict = Field(default_factory=dict)  # {metric: {baseline, experiment, improvement}}


class EvolutionProposal(BaseModel):
    """A proposal to evolve an architectural entity based on its intent.

    Evolution proposals enable agents to challenge existing architecture when they
    believe a better approach exists for achieving the same intent. The proposal
    must reference the target entity's structured metadata and include a concrete
    experiment plan with validation criteria.
    """
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    target_entity: str  # The architecture entity to evolve
    original_intent: str = ""  # Current intent (for reference)
    proposed_change: str  # What the agent wants to change
    rationale: str  # Why this better serves the intent
    experiment_plan: str = ""  # How to validate with real evidence
    validation_criteria: list[str] = Field(default_factory=list)  # Measurable success criteria
    status: EvolutionStatus = EvolutionStatus.PROPOSED
    worktree_branch: str = ""  # Git branch for the experiment
    evidence: list[ExperimentEvidence] = Field(default_factory=list)
    proposing_agent: str = ""
    decision_id: Optional[str] = None  # Link to governance decision
    review_verdict: Optional[str] = None  # Final verdict
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
