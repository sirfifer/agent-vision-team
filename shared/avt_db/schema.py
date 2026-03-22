"""SurrealDB schema definitions for the AVT unified database.

All tables are defined here and applied on first connection. The schema
covers: Knowledge Graph, Governance, Quality/Trust, Audit, and Context
Reinforcement.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from surrealdb import AsyncSurreal, Surreal

# Schema version. Bump when adding tables/fields/indexes.
SCHEMA_VERSION = 1

# Split into individual statements for clarity and error isolation.
_SCHEMA_STATEMENTS: list[str] = [
    # ================================================================
    # KNOWLEDGE GRAPH
    # ================================================================
    # Entities (schemaless for now to ease migration; tighten in Phase 6)
    """DEFINE TABLE IF NOT EXISTS entity SCHEMALESS""",
    """DEFINE INDEX IF NOT EXISTS entity_name ON entity FIELDS name UNIQUE""",
    """DEFINE INDEX IF NOT EXISTS entity_type_idx ON entity FIELDS entity_type""",
    """DEFINE INDEX IF NOT EXISTS entity_tier_idx ON entity FIELDS protection_tier""",

    # Graph edges between entities
    """DEFINE TABLE IF NOT EXISTS relates_to TYPE RELATION""",

    # ================================================================
    # GOVERNANCE
    # ================================================================
    """DEFINE TABLE IF NOT EXISTS decision SCHEMALESS""",
    """DEFINE INDEX IF NOT EXISTS decision_task ON decision FIELDS task_id""",
    """DEFINE INDEX IF NOT EXISTS decision_agent ON decision FIELDS agent""",

    """DEFINE TABLE IF NOT EXISTS review SCHEMALESS""",
    """DEFINE INDEX IF NOT EXISTS review_decision ON review FIELDS decision_id""",

    """DEFINE TABLE IF NOT EXISTS governed_task SCHEMALESS""",
    """DEFINE INDEX IF NOT EXISTS gt_impl ON governed_task FIELDS implementation_task_id UNIQUE""",
    """DEFINE INDEX IF NOT EXISTS gt_session ON governed_task FIELDS session_id""",

    """DEFINE TABLE IF NOT EXISTS task_review SCHEMALESS""",
    """DEFINE INDEX IF NOT EXISTS tr_impl ON task_review FIELDS implementation_task_id""",
    """DEFINE INDEX IF NOT EXISTS tr_review ON task_review FIELDS review_task_id""",

    """DEFINE TABLE IF NOT EXISTS holistic_review SCHEMALESS""",
    """DEFINE INDEX IF NOT EXISTS hr_session ON holistic_review FIELDS session_id""",

    """DEFINE TABLE IF NOT EXISTS token_usage SCHEMALESS""",
    """DEFINE INDEX IF NOT EXISTS tu_timestamp ON token_usage FIELDS timestamp""",
    """DEFINE INDEX IF NOT EXISTS tu_session ON token_usage FIELDS session_id""",

    # ================================================================
    # QUALITY / TRUST ENGINE
    # ================================================================
    """DEFINE TABLE IF NOT EXISTS finding SCHEMALESS""",

    """DEFINE TABLE IF NOT EXISTS dismissal_history SCHEMALESS""",
    """DEFINE INDEX IF NOT EXISTS dh_finding ON dismissal_history FIELDS finding_id""",

    # ================================================================
    # AUDIT
    # ================================================================
    """DEFINE TABLE IF NOT EXISTS audit_event SCHEMALESS""",
    """DEFINE INDEX IF NOT EXISTS ae_session ON audit_event FIELDS session_id""",
    """DEFINE INDEX IF NOT EXISTS ae_type ON audit_event FIELDS event_type""",

    """DEFINE TABLE IF NOT EXISTS event_count SCHEMALESS""",
    """DEFINE INDEX IF NOT EXISTS ec_pk ON event_count FIELDS bucket, event_type UNIQUE""",

    """DEFINE TABLE IF NOT EXISTS session_summary SCHEMALESS""",
    """DEFINE INDEX IF NOT EXISTS ss_pk ON session_summary FIELDS session_id UNIQUE""",

    """DEFINE TABLE IF NOT EXISTS metric_window SCHEMALESS""",

    """DEFINE TABLE IF NOT EXISTS anomaly SCHEMALESS""",
    """DEFINE INDEX IF NOT EXISTS anom_type ON anomaly FIELDS anomaly_type""",

    # ================================================================
    # CONTEXT REINFORCEMENT
    # ================================================================
    """DEFINE TABLE IF NOT EXISTS session_context SCHEMALESS""",
    """DEFINE INDEX IF NOT EXISTS sc_session ON session_context FIELDS session_id UNIQUE""",

    """DEFINE TABLE IF NOT EXISTS injection_history SCHEMALESS""",
    """DEFINE INDEX IF NOT EXISTS ih_session ON injection_history FIELDS session_id""",

    """DEFINE TABLE IF NOT EXISTS context_route SCHEMALESS""",
    """DEFINE INDEX IF NOT EXISTS cr_route ON context_route FIELDS route_id UNIQUE""",

    # ================================================================
    # SCHEMA VERSION TRACKING
    # ================================================================
    """DEFINE TABLE IF NOT EXISTS schema_meta SCHEMALESS""",
]


async def apply_schema(db: AsyncSurreal) -> None:
    """Apply all schema definitions to an async SurrealDB connection.

    Safe to call multiple times (all statements use IF NOT EXISTS).
    """
    for stmt in _SCHEMA_STATEMENTS:
        await db.query(stmt)
    # Record schema version
    await db.query(
        "UPSERT schema_meta:version SET version = $v, applied_at = time::now()",
        {"v": SCHEMA_VERSION},
    )


def apply_schema_sync(db: Surreal) -> None:
    """Apply all schema definitions to a sync SurrealDB connection.

    Safe to call multiple times (all statements use IF NOT EXISTS).
    """
    for stmt in _SCHEMA_STATEMENTS:
        db.query(stmt)
    db.query(
        "UPSERT schema_meta:version SET version = $v, applied_at = time::now()",
        {"v": SCHEMA_VERSION},
    )
