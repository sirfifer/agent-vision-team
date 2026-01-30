"""Data models for the Quality server."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class LintFinding(BaseModel):
    file: str
    line: int
    column: int
    rule: str
    message: str
    severity: str = "warning"
    auto_fixable: bool = False


class TestResult(BaseModel):
    name: str
    status: str  # "passed" | "failed" | "skipped"
    duration_ms: Optional[float] = None
    error: Optional[str] = None


class GateResult(BaseModel):
    name: str
    passed: bool
    detail: Optional[str] = None


class GateResults(BaseModel):
    build: GateResult
    lint: GateResult
    tests: GateResult
    coverage: GateResult
    findings: GateResult
    all_passed: bool = False


class TrustDecision(str, Enum):
    BLOCK = "BLOCK"
    INVESTIGATE = "INVESTIGATE"
    TRACK = "TRACK"


class DismissalRecord(BaseModel):
    finding_id: str
    justification: str
    dismissed_by: str
    timestamp: Optional[str] = None
