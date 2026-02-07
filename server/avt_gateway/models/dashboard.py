"""Dashboard data models matching the webview TypeScript types."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Entity(BaseModel):
    name: str
    entityType: str
    observations: list[str] = []
    relations: list[dict] = []


class AgentStatus(BaseModel):
    id: str
    name: str
    role: str
    status: str
    currentTask: str | None = None
    lastActivity: str | None = None
    governedTaskId: str | None = None
    blockedBy: list[str] | None = None


class ActivityEntry(BaseModel):
    id: str
    timestamp: str
    agent: str
    type: str
    tier: str | None = None
    summary: str
    detail: str | None = None
    governanceRef: str | None = None


class TaskReviewInfo(BaseModel):
    id: str
    reviewType: str
    status: str
    verdict: str | None = None
    guidance: str | None = None
    createdAt: str
    completedAt: str | None = None


class GovernedTask(BaseModel):
    id: str
    implementationTaskId: str
    subject: str
    status: str
    reviews: list[TaskReviewInfo] = []
    createdAt: str
    releasedAt: str | None = None


class GovernanceStats(BaseModel):
    totalDecisions: int = 0
    approved: int = 0
    blocked: int = 0
    pending: int = 0
    pendingReviews: int = 0
    totalGovernedTasks: int = 0


class GateResult(BaseModel):
    name: str
    passed: bool
    detail: str | None = None


class QualityGateResults(BaseModel):
    build: GateResult
    lint: GateResult
    tests: GateResult
    coverage: GateResult
    findings: GateResult
    all_passed: bool
    timestamp: str | None = None


class DecisionHistoryEntry(BaseModel):
    id: str
    taskId: str
    agent: str
    category: str
    summary: str
    confidence: str
    verdict: str | None = None
    guidance: str
    createdAt: str


class TrustFinding(BaseModel):
    id: str
    tool: str
    severity: str
    component: str | None = None
    description: str
    createdAt: str
    status: str


class SessionState(BaseModel):
    phase: str
    lastCheckpoint: str | None = None
    activeWorktrees: list[str] | None = None
    driftStatus: dict | None = None


class HookGovernanceStatus(BaseModel):
    totalInterceptions: int = 0
    lastInterceptionAt: str | None = None
    recentInterceptions: list[dict] = []


class DocumentInfo(BaseModel):
    name: str
    path: str
    title: str | None = None


class ResearchBriefInfo(BaseModel):
    name: str
    path: str
    modifiedAt: str


class SetupReadiness(BaseModel):
    isComplete: bool = False
    hasVisionDocs: bool = False
    hasArchitectureDocs: bool = False
    hasProjectConfig: bool = False
    hasKgIngestion: bool = False
    visionDocCount: int = 0
    architectureDocCount: int = 0


class IngestionResult(BaseModel):
    tier: str
    ingested: int
    entities: list[str] = []
    errors: list[str] = []
    skipped: list[str] = []


class DashboardData(BaseModel):
    connectionStatus: str = "disconnected"
    serverPorts: dict = Field(default_factory=lambda: {"kg": 3101, "quality": 3102, "governance": 3103})
    agents: list[AgentStatus] = []
    visionStandards: list[Entity] = []
    architecturalElements: list[Entity] = []
    activities: list[ActivityEntry] = []
    tasks: dict = Field(default_factory=lambda: {"active": 0, "total": 0})
    sessionPhase: str = "inactive"
    governedTasks: list[GovernedTask] = []
    governanceStats: GovernanceStats = Field(default_factory=GovernanceStats)
    qualityGateResults: QualityGateResults | None = None
    decisionHistory: list[DecisionHistoryEntry] | None = None
    findings: list[TrustFinding] | None = None
    hookGovernanceStatus: HookGovernanceStatus | None = None
    sessionState: SessionState | None = None
    setupReadiness: SetupReadiness | None = None
    projectConfig: dict | None = None
    visionDocs: list[DocumentInfo] | None = None
    architectureDocs: list[DocumentInfo] | None = None
    researchPrompts: list[dict] | None = None
    researchBriefs: list[ResearchBriefInfo] | None = None
