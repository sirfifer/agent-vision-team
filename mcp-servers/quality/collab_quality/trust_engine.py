"""Tool Trust Engine — classifies findings and tracks dismissals."""

from .models import TrustDecision, DismissalRecord


class TrustEngine:
    def __init__(self) -> None:
        self._dismissals: list[DismissalRecord] = []
        # TODO: Initialize SQLite for persistent storage

    def get_trust_decision(self, finding_id: str) -> dict:
        """Determine trust classification for a finding."""
        # TODO: Look up finding history, apply trust heuristics
        # Default: all findings are trusted (BLOCK)
        return {
            "decision": TrustDecision.BLOCK.value,
            "rationale": "Default: all tool findings presumed legitimate until proven otherwise.",
        }

    def record_dismissal(
        self,
        finding_id: str,
        justification: str,
        dismissed_by: str,
    ) -> bool:
        """Record a finding dismissal with required justification."""
        if not justification.strip():
            return False

        record = DismissalRecord(
            finding_id=finding_id,
            justification=justification,
            dismissed_by=dismissed_by,
        )
        self._dismissals.append(record)
        # TODO: Persist to SQLite
        return True

    def get_dismissal_history(self, finding_id: str) -> list[DismissalRecord]:
        """Get dismissal history for a finding."""
        return [d for d in self._dismissals if d.finding_id == finding_id]
