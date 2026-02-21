"""Recommendation lifecycle manager: JSON-file backed.

Manages recommendations produced by the anomaly detector and escalation chain.
States: active, stale, dismissed, superseded, resolved.
Deduplicates by type. Handles TTL expiry. Persists to .avt/audit/recommendations.json.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from uuid import uuid4

_PROJECT_DIR = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
_RECOMMENDATIONS_PATH = Path(_PROJECT_DIR) / ".avt" / "audit" / "recommendations.json"

# Default TTL for recommendations (7 days)
DEFAULT_TTL_SECONDS = 7 * 24 * 3600


class RecommendationManager:
    """Manages the lifecycle of audit recommendations."""

    def __init__(self, path: "Path | str | None" = None) -> None:
        self.path = Path(path) if path else _RECOMMENDATIONS_PATH
        self._recs: list[dict] = []
        self._load()

    def _load(self) -> None:
        """Load recommendations from file."""
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text())
                self._recs = data.get("recommendations", [])
            except (json.JSONDecodeError, OSError):
                self._recs = []
        else:
            self._recs = []

    def _save(self) -> None:
        """Save recommendations to file atomically."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        try:
            data = {
                "version": 1,
                "updated_at": time.time(),
                "recommendations": self._recs,
            }
            tmp.write_text(json.dumps(data, indent=2))
            tmp.rename(self.path)
        except OSError:
            try:
                tmp.unlink()
            except OSError:
                pass

    def create_from_anomaly(
        self,
        anomaly: dict,
        suggestion: str = "",
        category: str = "general",
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ) -> "dict | None":
        """Create a recommendation from an anomaly, deduplicating by type.

        If a recommendation of the same type already exists and is active,
        increment its evidence count and reset TTL instead.

        Returns the created/updated recommendation, or None if skipped.
        """
        anomaly_type = anomaly.get("type", "unknown")

        # Check for existing active recommendation of same type
        for rec in self._recs:
            if rec["anomaly_type"] == anomaly_type and rec["status"] == "active":
                rec["evidence_count"] = rec.get("evidence_count", 1) + 1
                rec["last_seen_at"] = time.time()
                rec["expires_at"] = time.time() + ttl_seconds
                rec["latest_metric_values"] = anomaly.get("metric_values", {})
                self._save()
                return rec

        # Create new recommendation
        rec = {
            "id": f"rec-{uuid4().hex[:8]}",
            "created_at": time.time(),
            "last_seen_at": time.time(),
            "expires_at": time.time() + ttl_seconds,
            "status": "active",
            "anomaly_type": anomaly_type,
            "severity": anomaly.get("severity", "info"),
            "description": anomaly.get("description", ""),
            "suggestion": suggestion,
            "category": category,
            "evidence_count": 1,
            "latest_metric_values": anomaly.get("metric_values", {}),
            "dismissed_reason": None,
            "resolved_at": None,
        }
        self._recs.append(rec)
        self._save()
        return rec

    def update_from_escalation(
        self,
        anomaly_type: str,
        suggestion: str,
        analysis: str = "",
        tier: str = "haiku",
    ) -> "dict | None":
        """Update a recommendation with analysis from an escalation tier.

        Returns the updated recommendation, or None if not found.
        """
        for rec in self._recs:
            if rec["anomaly_type"] == anomaly_type and rec["status"] == "active":
                rec["suggestion"] = suggestion
                if analysis:
                    rec["analysis"] = analysis
                rec["escalation_tier"] = tier
                rec["last_seen_at"] = time.time()
                self._save()
                return rec
        return None

    def dismiss(self, rec_id: str, reason: str = "") -> bool:
        """Dismiss a recommendation. Returns True if found."""
        for rec in self._recs:
            if rec["id"] == rec_id:
                rec["status"] = "dismissed"
                rec["dismissed_reason"] = reason
                self._save()
                return True
        return False

    def resolve(self, rec_id: str) -> bool:
        """Mark a recommendation as resolved. Returns True if found."""
        for rec in self._recs:
            if rec["id"] == rec_id:
                rec["status"] = "resolved"
                rec["resolved_at"] = time.time()
                self._save()
                return True
        return False

    def supersede(self, old_id: str, new_id: str) -> bool:
        """Mark a recommendation as superseded by another."""
        for rec in self._recs:
            if rec["id"] == old_id:
                rec["status"] = "superseded"
                rec["superseded_by"] = new_id
                self._save()
                return True
        return False

    def prune_expired(self) -> int:
        """Move expired active recommendations to stale. Returns count pruned."""
        now = time.time()
        pruned = 0
        for rec in self._recs:
            if rec["status"] == "active" and rec.get("expires_at", 0) < now:
                rec["status"] = "stale"
                pruned += 1
        if pruned:
            self._save()
        return pruned

    def get_active(self) -> list[dict]:
        """Get all active recommendations, sorted by evidence count."""
        self.prune_expired()
        active = [r for r in self._recs if r["status"] == "active"]
        active.sort(key=lambda r: r.get("evidence_count", 0), reverse=True)
        return active

    def get_all(self) -> list[dict]:
        """Get all recommendations regardless of status."""
        return list(self._recs)

    def get_by_id(self, rec_id: str) -> "dict | None":
        """Get a single recommendation by ID."""
        for rec in self._recs:
            if rec["id"] == rec_id:
                return rec
        return None

    def get_by_type(self, anomaly_type: str) -> list[dict]:
        """Get recommendations for a specific anomaly type."""
        return [r for r in self._recs if r["anomaly_type"] == anomaly_type]

    @property
    def active_count(self) -> int:
        return sum(1 for r in self._recs if r["status"] == "active")

    @property
    def total_count(self) -> int:
        return len(self._recs)
