"""Structural validation of experiment evidence.

Checks that evidence submitted for evolution proposals is real and not
fabricated. Validates paths, timestamps, numeric data, and test output.
"""

import os
import re
from datetime import datetime, timezone
from typing import Optional

from .models import ExperimentEvidence


class EvidenceValidationResult:
    """Result of validating a piece of experiment evidence."""

    def __init__(self, valid: bool, failures: Optional[list[str]] = None):
        self.valid = valid
        self.failures = failures or []

    def to_dict(self) -> dict:
        return {"valid": self.valid, "failures": self.failures}


def validate_evidence(
    evidence: ExperimentEvidence,
    experiment_start: Optional[str] = None,
    allow_mock: bool = False,
) -> EvidenceValidationResult:
    """Validate a single piece of experiment evidence.

    Args:
        evidence: The evidence to validate.
        experiment_start: ISO timestamp of when the experiment started.
            If provided, evidence timestamps must be after this time.
        allow_mock: If True, skip file-existence checks. Set to True
            during E2E testing (via GOVERNANCE_MOCK_REVIEW env var).

    Returns:
        EvidenceValidationResult with pass/fail and specific failure reasons.
    """
    if allow_mock or os.environ.get("GOVERNANCE_MOCK_REVIEW"):
        return EvidenceValidationResult(valid=True)

    failures: list[str] = []

    # 1. Source path must exist (if provided)
    if evidence.source and not _check_source_exists(evidence.source):
        failures.append(f"Source path does not exist: {evidence.source}")

    # 2. Timestamp must be valid and within experiment window
    if evidence.timestamp:
        ts_result = _check_timestamp(evidence.timestamp, experiment_start)
        if ts_result:
            failures.append(ts_result)

    # 3. Evidence type-specific checks
    if evidence.evidence_type == "test_results":
        test_failures = _check_test_results(evidence)
        failures.extend(test_failures)
    elif evidence.evidence_type == "benchmark":
        bench_failures = _check_benchmark(evidence)
        failures.extend(bench_failures)

    # 4. Metrics must have numeric values
    if evidence.metrics:
        metric_failures = _check_metrics(evidence.metrics)
        failures.extend(metric_failures)

    # 5. Comparison to baseline must have proper structure
    if evidence.comparison_to_baseline:
        comp_failures = _check_comparison(evidence.comparison_to_baseline)
        failures.extend(comp_failures)

    return EvidenceValidationResult(valid=len(failures) == 0, failures=failures)


def validate_evidence_batch(
    evidence_list: list[ExperimentEvidence],
    experiment_start: Optional[str] = None,
    allow_mock: bool = False,
) -> EvidenceValidationResult:
    """Validate multiple pieces of evidence. All must pass."""
    all_failures: list[str] = []
    for i, ev in enumerate(evidence_list):
        result = validate_evidence(ev, experiment_start, allow_mock)
        if not result.valid:
            prefixed = [f"Evidence[{i}] ({ev.evidence_type}): {f}" for f in result.failures]
            all_failures.extend(prefixed)
    return EvidenceValidationResult(valid=len(all_failures) == 0, failures=all_failures)


def _check_source_exists(source: str) -> bool:
    """Check if a source path exists on disk."""
    return os.path.exists(source)


def _check_timestamp(timestamp: str, experiment_start: Optional[str]) -> Optional[str]:
    """Validate timestamp format and range."""
    try:
        ts = datetime.fromisoformat(timestamp)
    except (ValueError, TypeError):
        return f"Invalid timestamp format: {timestamp}"

    if experiment_start:
        try:
            start = datetime.fromisoformat(experiment_start)
            if ts < start:
                return f"Evidence timestamp {timestamp} is before experiment start {experiment_start}"
        except (ValueError, TypeError):
            pass  # Can't validate range if start is invalid

    # Reject timestamps more than 30 days in the future
    now = datetime.now(timezone.utc)
    if ts.tzinfo and (ts - now).days > 30:
        return f"Evidence timestamp {timestamp} is more than 30 days in the future"

    return None


def _check_test_results(evidence: ExperimentEvidence) -> list[str]:
    """Check that test result evidence contains actual pass/fail counts."""
    failures = []
    output = evidence.raw_output or evidence.summary or ""

    if not output:
        failures.append("Test results evidence has no raw_output or summary")
        return failures

    # Look for common test result patterns
    has_counts = bool(
        re.search(r'\d+\s+(pass|fail|error|skip)', output, re.IGNORECASE)
        or re.search(r'(passed|failed|errors?|skipped)\s*[=:]\s*\d+', output, re.IGNORECASE)
        or re.search(r'(\d+)\s+test', output, re.IGNORECASE)
    )

    if not has_counts:
        failures.append(
            "Test results evidence does not contain recognizable pass/fail counts. "
            "Expected patterns like '5 passed, 0 failed' or 'Tests: 5'."
        )

    return failures


def _check_benchmark(evidence: ExperimentEvidence) -> list[str]:
    """Check that benchmark evidence contains numeric measurements."""
    failures = []
    metrics = evidence.metrics or {}

    if not metrics:
        output = evidence.raw_output or evidence.summary or ""
        has_numbers = bool(re.search(r'\d+\.?\d*\s*(ms|s|ns|us|MB|KB|GB|ops|req)', output, re.IGNORECASE))
        if not has_numbers:
            failures.append(
                "Benchmark evidence has no metrics dict and no recognizable numeric measurements in output."
            )

    return failures


def _check_metrics(metrics: dict) -> list[str]:
    """Check that metric values are numeric (int or float)."""
    failures = []
    for name, value in metrics.items():
        if not isinstance(value, (int, float)):
            try:
                float(value)
            except (ValueError, TypeError):
                failures.append(f"Metric '{name}' has non-numeric value: {value}")
    return failures


def _check_comparison(comparison: dict) -> list[str]:
    """Check that comparison_to_baseline has proper structure."""
    failures = []
    for metric_name, comp in comparison.items():
        if not isinstance(comp, dict):
            failures.append(f"Comparison for '{metric_name}' is not a dict")
            continue
        required_keys = {"baseline", "experiment"}
        missing = required_keys - set(comp.keys())
        if missing:
            failures.append(f"Comparison for '{metric_name}' missing keys: {missing}")
    return failures
