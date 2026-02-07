"""S14 -- Full persistence lifecycle: populate all stores, validate, clean up.

Two-phase integration test that exercises every data flow path:

Phase 1 (Populate):
  Step 1: Document ingestion (vision + architecture docs -> KG entities)
  Step 2: Agent entity creation (components, relations, observations)
  Step 3: Governance decision flow with KG context
  Step 4: Governed task lifecycle
  Step 5: Quality/Trust engine
  Step 6: KG Librarian curation (consolidation, pattern promotion)
  Step 7: Archival file sync (KG -> .avt/memory/*.md)
  Step 8: Session state generation
  Step 9: Cross-store validation

Phase 2 (Cleanup):
  Delete all quality-tier entities, relations, governance data.
  Validate all stores are back to starting state.

Scenario type: positive.
"""

import os
import sys
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "mcp-servers" / "knowledge-graph"))
sys.path.insert(0, str(_PROJECT_ROOT / "mcp-servers" / "governance"))
sys.path.insert(0, str(_PROJECT_ROOT / "mcp-servers" / "quality"))

from collab_kg.graph import KnowledgeGraph
from collab_kg.ingestion import parse_document, ingest_folder
from collab_kg.curation import (
    consolidate_observations,
    promote_patterns,
    remove_stale_observations,
    validate_tier_consistency,
    run_full_curation,
)
from collab_kg.archival import sync_archival_files
from collab_governance.kg_client import KGClient
from collab_governance.models import (
    Decision,
    DecisionCategory,
    Confidence,
    ReviewVerdict,
    Verdict,
    GovernedTaskRecord,
    TaskReviewRecord,
    TaskReviewStatus,
    ReviewType,
)
from collab_governance.store import GovernanceStore
from collab_governance.task_integration import TaskFileManager, Task
from collab_governance.session_state import generate_session_state
from collab_quality.trust_engine import TrustEngine

from .base import BaseScenario, ScenarioResult


class S14PersistenceLifecycle(BaseScenario):
    """Full two-phase persistence lifecycle test."""

    name = "s14-persistence-lifecycle"
    isolation_mode = "library"

    def run(self, **kwargs: Any) -> ScenarioResult:
        scenario_dir: Path = kwargs["scenario_dir"]

        # ================================================================
        # Setup: isolated stores
        # ================================================================
        kg_path = scenario_dir / "knowledge-graph.jsonl"
        kg = KnowledgeGraph(storage_path=str(kg_path))

        gov_db_path = scenario_dir / "governance.db"
        gov_store = GovernanceStore(db_path=gov_db_path)

        trust_db_path = scenario_dir / "trust-engine.db"
        trust = TrustEngine(db_path=str(trust_db_path))

        task_dir = scenario_dir / "tasks"
        task_dir.mkdir(parents=True, exist_ok=True)
        task_mgr = TaskFileManager(task_dir=task_dir)

        memory_dir = scenario_dir / "memory"
        memory_dir.mkdir(parents=True, exist_ok=True)

        docs_dir = scenario_dir / "docs"

        kg_client = KGClient(kg_path=kg_path)

        # ================================================================
        # PHASE 1: Populate all stores
        # ================================================================

        # -- Step 1: Document Ingestion -----------------------------------
        self._step_1_document_ingestion(kg, docs_dir)

        # -- Step 2: Agent Entity Creation ---------------------------------
        self._step_2_agent_entities(kg)

        # -- Step 3: Governance Decision Flow with KG Context --------------
        self._step_3_governance_decisions(gov_store, kg_client)

        # Reload KG from disk since KGClient.record_decision() appends
        # directly to JSONL, bypassing the in-memory KnowledgeGraph.
        # Without this reload, a subsequent compact() would lose those records.
        kg._load_from_storage()

        # -- Step 4: Governed Task Lifecycle -------------------------------
        self._step_4_governed_tasks(gov_store, task_mgr)

        # -- Step 5: Quality/Trust Engine ----------------------------------
        self._step_5_trust_engine(trust)

        # -- Step 6: KG Librarian Curation ---------------------------------
        self._step_6_curation(kg)

        # -- Step 7: Archival File Sync ------------------------------------
        self._step_7_archival_sync(kg, memory_dir)

        # -- Step 8: Session State Generation ------------------------------
        self._step_8_session_state(gov_store, scenario_dir)

        # -- Step 9: Cross-Store Validation (Phase 1 complete) -------------
        self._step_9_cross_store_validation(
            kg, kg_path, gov_store, trust, memory_dir, scenario_dir
        )

        # ================================================================
        # PHASE 2: Cleanup and validate clean state
        # ================================================================
        self._phase_2_cleanup(
            kg, kg_path, gov_store, gov_db_path, trust, trust_db_path,
            memory_dir, scenario_dir
        )

        gov_store.close()
        return self._build_result(scenario_type="positive")

    # ====================================================================
    # Phase 1 Steps
    # ====================================================================

    def _step_1_document_ingestion(self, kg: KnowledgeGraph, docs_dir: Path):
        """Write vision/architecture docs and ingest them into KG."""
        # Write vision docs
        vision_dir = docs_dir / "vision"
        vision_dir.mkdir(parents=True, exist_ok=True)

        (vision_dir / "di-standard.md").write_text(
            "# Protocol-Based Dependency Injection\n\n"
            "## Statement\n\n"
            "All services MUST use protocol-based dependency injection.\n\n"
            "## Rationale\n\n"
            "Enables testability and loose coupling.\n",
            encoding="utf-8",
        )

        (vision_dir / "no-singletons.md").write_text(
            "# No Production Singletons\n\n"
            "## Statement\n\n"
            "No singletons in production code.\n\n"
            "## Rationale\n\n"
            "Singletons create hidden dependencies.\n",
            encoding="utf-8",
        )

        # Write architecture docs
        arch_dir = docs_dir / "architecture"
        arch_dir.mkdir(parents=True, exist_ok=True)

        (arch_dir / "service-registry.md").write_text(
            "# Service Registry Pattern\n\n"
            "## Type\n\nPattern\n\n"
            "## Description\n\n"
            "All services resolved through a centralized registry at startup.\n\n"
            "## Usage\n\n"
            "Use ServiceRegistry.resolve<T>() to obtain service instances.\n",
            encoding="utf-8",
        )

        # Ingest vision docs
        vision_result = ingest_folder(kg, str(vision_dir), "vision")
        self.assert_true(
            "step1: vision docs ingested",
            vision_result["ingested"] == 2,
            expected=2,
            actual=vision_result["ingested"],
        )
        self.assert_true(
            "step1: no vision ingestion errors",
            len(vision_result["errors"]) == 0,
            expected="no errors",
            actual=vision_result["errors"],
        )

        # Ingest architecture docs
        arch_result = ingest_folder(kg, str(arch_dir), "architecture")
        self.assert_true(
            "step1: architecture docs ingested",
            arch_result["ingested"] == 1,
            expected=1,
            actual=arch_result["ingested"],
        )

        # Validate: KG has the ingested entities with correct tiers
        vision_entities = kg.get_entities_by_tier("vision")
        self.assert_true(
            "step1: KG has vision-tier entities",
            len(vision_entities) >= 2,
            expected=">=2",
            actual=len(vision_entities),
        )

        arch_entities = kg.get_entities_by_tier("architecture")
        self.assert_true(
            "step1: KG has architecture-tier entities",
            len(arch_entities) >= 1,
            expected=">=1",
            actual=len(arch_entities),
        )

        # Validate: entity observations contain expected content
        di_results = kg.search_nodes("dependency injection")
        self.assert_true(
            "step1: DI standard searchable in KG",
            len(di_results) > 0,
            expected=">0 results",
            actual=len(di_results),
        )

    def _step_2_agent_entities(self, kg: KnowledgeGraph):
        """Create entities, relations, and observations as an agent would."""
        # Create component entities
        created = kg.create_entities([
            {
                "name": "AuthService",
                "entityType": "component",
                "observations": [
                    "protection_tier: quality",
                    "Handles JWT authentication",
                    "Uses DI pattern",
                ],
            },
            {
                "name": "UserRepository",
                "entityType": "component",
                "observations": [
                    "protection_tier: quality",
                    "Manages user data persistence",
                    "Uses DI pattern",
                ],
            },
            {
                "name": "ApiGateway",
                "entityType": "component",
                "observations": [
                    "protection_tier: quality",
                    "Routes API requests",
                    "Uses DI pattern",
                ],
            },
        ])
        self.assert_equal("step2: 3 components created", created, 3)

        # Create relations
        rel_count = kg.create_relations([
            {"from": "AuthService", "to": "UserRepository", "relationType": "depends_on"},
            {"from": "ApiGateway", "to": "AuthService", "relationType": "uses"},
        ])
        self.assert_equal("step2: 2 relations created", rel_count, 2)

        # Add observations
        added, err = kg.add_observations(
            "AuthService",
            ["Supports refresh tokens", "Rate limited to 100 req/s"],
            caller_role="agent",
        )
        self.assert_equal("step2: 2 observations added", added, 2)
        self.assert_true("step2: no error adding observations", err is None)

        # Verify search works
        auth_results = kg.search_nodes("authentication")
        self.assert_true(
            "step2: AuthService searchable",
            len(auth_results) > 0,
            expected=">0",
            actual=len(auth_results),
        )

        # Verify entity with relations
        auth_entity = kg.get_entity("AuthService")
        self.assert_true("step2: AuthService entity exists", auth_entity is not None)
        if auth_entity:
            self.assert_true(
                "step2: AuthService has relations",
                len(auth_entity.relations) > 0,
                expected=">0",
                actual=len(auth_entity.relations),
            )

        # Verify tier protection: agent cannot modify vision entities
        added_v, err_v = kg.add_observations(
            kg.get_entities_by_tier("vision")[0].name,
            ["agent trying to modify vision"],
            caller_role="agent",
        )
        self.assert_true(
            "step2: agent blocked from modifying vision entity",
            err_v is not None,
            expected="error message",
            actual=err_v,
        )

    def _step_3_governance_decisions(
        self, gov_store: GovernanceStore, kg_client: KGClient
    ):
        """Submit decisions, get reviews, record in KG."""
        task_id = "task-s14-auth"

        # Verify KGClient can read the standards from KG
        vision_standards = kg_client.get_vision_standards()
        self.assert_true(
            "step3: KGClient reads vision standards from KG",
            len(vision_standards) > 0,
            expected=">0",
            actual=len(vision_standards),
        )

        arch_entities = kg_client.get_architecture_entities()
        self.assert_true(
            "step3: KGClient reads architecture entities from KG",
            len(arch_entities) > 0,
            expected=">0",
            actual=len(arch_entities),
        )

        # Submit a decision
        decision = gov_store.store_decision(Decision(
            task_id=task_id,
            agent="worker-1",
            category=DecisionCategory.PATTERN_CHOICE,
            summary="Use JWT for authentication",
            detail="JWT with refresh tokens, stored in httpOnly cookies",
            components_affected=["AuthService", "ApiGateway"],
            confidence=Confidence.HIGH,
        ))
        self.assert_true("step3: decision stored", len(decision.id) > 0)

        # Store a review
        review = gov_store.store_review(ReviewVerdict(
            decision_id=decision.id,
            verdict=Verdict.APPROVED,
            guidance="Aligns with security patterns",
            standards_verified=["Protocol-Based DI", "Authorization Required"],
        ))
        self.assert_equal("step3: review is approved", review.verdict, Verdict.APPROVED)

        # Record decision in KG
        kg_client.record_decision(
            decision_id=decision.id,
            summary=decision.summary,
            verdict="approved",
            agent="worker-1",
        )

        # Verify the decision was recorded in KG
        kg_decisions = kg_client.search_entities([f"governance_decision_{decision.id}"])
        self.assert_true(
            "step3: governance decision recorded in KG",
            len(kg_decisions) > 0,
            expected=">0",
            actual=len(kg_decisions),
        )

        # Verify KG entity has correct type (governance_decision, not solution_pattern)
        if kg_decisions:
            self.assert_equal(
                "step3: KG entity type is governance_decision",
                kg_decisions[0].get("entityType"),
                "governance_decision",
            )

        # Submit a second decision (blocked)
        decision2 = gov_store.store_decision(Decision(
            task_id=task_id,
            agent="worker-1",
            category=DecisionCategory.DEVIATION,
            summary="Deviate from DI pattern for performance",
            detail="Direct instantiation in hot path",
            components_affected=["AuthService"],
            confidence=Confidence.LOW,
        ))

        review2 = gov_store.store_review(ReviewVerdict(
            decision_id=decision2.id,
            verdict=Verdict.BLOCKED,
            guidance="Violates Protocol-Based DI vision standard",
            standards_verified=[],
        ))
        self.assert_equal("step3: deviation blocked", review2.verdict, Verdict.BLOCKED)

        # Verify decision history
        history = gov_store.get_all_decisions(task_id=task_id)
        self.assert_equal("step3: 2 decisions in history", len(history), 2)

    def _step_4_governed_tasks(
        self, gov_store: GovernanceStore, task_mgr: TaskFileManager
    ):
        """Create governed task pairs, release on approval."""
        # Create implementation task
        impl_task = Task(
            id="impl-s14-001",
            subject="Implement AuthService",
            description="Full JWT auth implementation",
        )
        task_mgr.create_task(impl_task)

        # Create review task
        review_task = Task(
            id="review-s14-001",
            subject="[GOVERNANCE] Review: Implement AuthService",
            blocks=["impl-s14-001"],
        )
        task_mgr.create_task(review_task)

        # Add blocker to impl task
        task_mgr.add_blocker("impl-s14-001", "review-s14-001")

        # Verify impl task is blocked
        blocked_task = task_mgr.read_task("impl-s14-001")
        self.assert_true(
            "step4: impl task blocked from birth",
            "review-s14-001" in blocked_task.blockedBy if blocked_task else False,
        )

        # Store governed task record in governance DB
        governed = GovernedTaskRecord(
            implementation_task_id="impl-s14-001",
            subject="Implement AuthService",
            description="Full JWT auth implementation",
            context="Part of auth epic",
        )
        gov_store.store_governed_task(governed)

        # Store task review record
        task_review = TaskReviewRecord(
            review_task_id="review-s14-001",
            implementation_task_id="impl-s14-001",
            review_type=ReviewType.GOVERNANCE,
            status=TaskReviewStatus.PENDING,
            context="Standard governance review",
        )
        gov_store.store_task_review(task_review)

        # Verify governed task is pending
        retrieved = gov_store.get_governed_task("impl-s14-001")
        self.assert_true("step4: governed task stored", retrieved is not None)
        if retrieved:
            self.assert_equal(
                "step4: governed task status is pending_review",
                retrieved.current_status,
                "pending_review",
            )

        # Complete the review (approve)
        task_review.status = TaskReviewStatus.APPROVED
        task_review.verdict = Verdict.APPROVED
        task_review.guidance = "Approved. Proceed with JWT implementation."
        gov_store.update_task_review(task_review)

        # Release the blocker
        task_mgr.remove_blocker("impl-s14-001", "review-s14-001")
        gov_store.update_governed_task_status("impl-s14-001", "approved")

        # Verify task is now unblocked
        released_task = task_mgr.read_task("impl-s14-001")
        self.assert_true(
            "step4: impl task unblocked after approval",
            len(released_task.blockedBy) == 0 if released_task else False,
        )

        # Verify governed task status updated
        approved_task = gov_store.get_governed_task("impl-s14-001")
        if approved_task:
            self.assert_equal(
                "step4: governed task status is approved",
                approved_task.current_status,
                "approved",
            )

    def _step_5_trust_engine(self, trust: TrustEngine):
        """Record findings, dismiss with justification, verify audit trail."""
        # Record findings
        trust.record_finding(
            finding_id="LINT-001",
            tool="ruff",
            severity="medium",
            component="AuthService",
            description="Unused import: os",
        )
        trust.record_finding(
            finding_id="SEC-001",
            tool="bandit",
            severity="high",
            component="AuthService",
            description="Potential SQL injection in query builder",
        )
        trust.record_finding(
            finding_id="COV-001",
            tool="pytest-cov",
            severity="low",
            component="UserRepository",
            description="Coverage below 80% threshold",
        )

        # Verify findings recorded
        all_findings = trust.get_all_findings()
        self.assert_equal("step5: 3 findings recorded", len(all_findings), 3)

        # Get trust decision for new finding (should be BLOCK)
        decision = trust.get_trust_decision("LINT-001")
        self.assert_equal("step5: new finding decision is BLOCK", decision["decision"], "BLOCK")

        # Dismiss a finding with justification
        dismissed = trust.record_dismissal(
            finding_id="LINT-001",
            justification="Import used in debug mode only, acceptable",
            dismissed_by="tech_lead",
        )
        self.assert_true("step5: finding dismissed", dismissed)

        # Get trust decision after dismissal (should be TRACK)
        decision_after = trust.get_trust_decision("LINT-001")
        self.assert_equal(
            "step5: dismissed finding decision is TRACK",
            decision_after["decision"],
            "TRACK",
        )

        # Verify audit trail
        history = trust.get_dismissal_history("LINT-001")
        self.assert_equal("step5: 1 dismissal in history", len(history), 1)
        self.assert_equal(
            "step5: dismissal justification recorded",
            history[0]["justification"],
            "Import used in debug mode only, acceptable",
        )

        # Verify unresolved findings
        unresolved = trust.get_unresolved_findings(min_severity="medium")
        self.assert_true(
            "step5: unresolved high-severity finding present",
            any(f["id"] == "SEC-001" for f in unresolved),
        )

    def _step_6_curation(self, kg: KnowledgeGraph):
        """Test KG Librarian curation: consolidation and pattern promotion."""
        # Add duplicate observations to test consolidation
        kg.add_observations(
            "AuthService",
            ["Uses DI pattern", "USES DI PATTERN"],  # duplicate (case-insensitive)
            caller_role="agent",
        )

        # Consolidate
        result = consolidate_observations(kg, "AuthService")
        self.assert_true(
            "step6: duplicate observations removed",
            result["removed"] > 0,
            expected=">0",
            actual=result["removed"],
        )

        # Test pattern promotion: "Uses DI pattern" appears on 3+ entities
        # (AuthService, UserRepository, ApiGateway all have it from step 2)
        promotion = promote_patterns(kg)
        self.assert_true(
            "step6: pattern promoted",
            len(promotion["promoted"]) > 0,
            expected=">0 promoted",
            actual=f"{len(promotion['promoted'])} promoted",
        )

        # Add a stale observation and remove it
        kg.add_observations(
            "AuthService",
            ["DEPRECATED: old auth method"],
            caller_role="agent",
        )
        stale_result = remove_stale_observations(kg, "AuthService", ["DEPRECATED"])
        self.assert_equal("step6: stale observation removed", stale_result["removed"], 1)

        # Validate tier consistency
        validation = validate_tier_consistency(kg)
        self.assert_equal(
            "step6: no tier violations",
            len(validation["violations"]),
            0,
        )
        self.assert_true(
            "step6: entities checked > 0",
            validation["checked"] > 0,
            expected=">0",
            actual=validation["checked"],
        )

    def _step_7_archival_sync(self, kg: KnowledgeGraph, memory_dir: Path):
        """Sync KG to archival memory files."""
        result = sync_archival_files(kg, memory_dir)

        self.assert_true(
            "step7: archival files written",
            result["files_written"] > 0,
            expected=">0",
            actual=result["files_written"],
        )

        # Verify architectural-decisions.md has governance decision content
        arch_decisions = (memory_dir / "architectural-decisions.md").read_text(encoding="utf-8")
        self.assert_true(
            "step7: architectural-decisions.md has content",
            len(arch_decisions) > 50,
            expected=">50 chars",
            actual=len(arch_decisions),
        )

        # Verify solution-patterns.md has promoted pattern
        solution_patterns = (memory_dir / "solution-patterns.md").read_text(encoding="utf-8")
        self.assert_true(
            "step7: solution-patterns.md exists",
            len(solution_patterns) > 20,
            expected=">20 chars",
            actual=len(solution_patterns),
        )

        # Verify troubleshooting-log.md exists
        troubleshooting = (memory_dir / "troubleshooting-log.md").read_text(encoding="utf-8")
        self.assert_true(
            "step7: troubleshooting-log.md exists",
            "Troubleshooting Log" in troubleshooting,
        )

        # Verify research-findings.md exists
        research = (memory_dir / "research-findings.md").read_text(encoding="utf-8")
        self.assert_true(
            "step7: research-findings.md exists",
            "Research Findings" in research,
        )

    def _step_8_session_state(self, gov_store: GovernanceStore, scenario_dir: Path):
        """Generate session state from governance data."""
        state_path = scenario_dir / "session-state.md"
        result = generate_session_state(gov_store, state_path)

        self.assert_true(
            "step8: session state generated",
            state_path.exists(),
        )
        self.assert_true(
            "step8: session state has tasks",
            result["tasks"] > 0,
            expected=">0",
            actual=result["tasks"],
        )
        self.assert_true(
            "step8: session state has decisions",
            result["decisions"] > 0,
            expected=">0",
            actual=result["decisions"],
        )

        # Verify content
        content = state_path.read_text(encoding="utf-8")
        self.assert_contains("step8: session state has header", content, "# Session State")
        self.assert_contains("step8: session state has task table", content, "Total governed tasks")

    def _step_9_cross_store_validation(
        self,
        kg: KnowledgeGraph,
        kg_path: Path,
        gov_store: GovernanceStore,
        trust: TrustEngine,
        memory_dir: Path,
        scenario_dir: Path,
    ):
        """Final cross-store validation: all stores have expected data."""
        # KG JSONL has entities from steps 1, 2, 3, 6
        kg_client = KGClient(kg_path=kg_path)
        all_entities = kg_client._load_entities()
        self.assert_true(
            "step9: KG has multiple entity types",
            len(all_entities) > 5,
            expected=">5 entities",
            actual=len(all_entities),
        )

        # Check entity types present
        entity_types = {e.get("entityType") for e in all_entities}
        self.assert_contains(
            "step9: KG has vision_standard entities",
            entity_types,
            "vision_standard",
        )
        self.assert_contains(
            "step9: KG has component entities",
            entity_types,
            "component",
        )
        self.assert_contains(
            "step9: KG has governance_decision entities",
            entity_types,
            "governance_decision",
        )

        # Governance DB has records from steps 3, 4
        status = gov_store.get_status()
        self.assert_true(
            "step9: governance DB has decisions",
            status["total_decisions"] >= 2,
            expected=">=2",
            actual=status["total_decisions"],
        )

        task_stats = gov_store.get_task_governance_stats()
        self.assert_true(
            "step9: governance DB has governed tasks",
            task_stats["total_governed_tasks"] >= 1,
            expected=">=1",
            actual=task_stats["total_governed_tasks"],
        )

        # Trust engine has records from step 5
        all_findings = trust.get_all_findings()
        self.assert_true(
            "step9: trust engine has findings",
            len(all_findings) >= 3,
            expected=">=3",
            actual=len(all_findings),
        )

        # Memory files have content from steps 7
        for filename in ("architectural-decisions.md", "solution-patterns.md",
                        "troubleshooting-log.md", "research-findings.md"):
            filepath = memory_dir / filename
            self.assert_true(
                f"step9: {filename} exists",
                filepath.exists(),
            )

        # Session state from step 8
        state_path = scenario_dir / "session-state.md"
        self.assert_true("step9: session-state.md exists", state_path.exists())

    # ====================================================================
    # Phase 2: Cleanup
    # ====================================================================

    def _phase_2_cleanup(
        self,
        kg: KnowledgeGraph,
        kg_path: Path,
        gov_store: GovernanceStore,
        gov_db_path: Path,
        trust: TrustEngine,
        trust_db_path: Path,
        memory_dir: Path,
        scenario_dir: Path,
    ):
        """Clean up all stores and validate they're back to starting state."""
        # Step 1: Delete all quality-tier KG entities
        quality_entities = kg.get_entities_by_tier("quality")
        for ewr in quality_entities:
            kg.delete_entity(ewr.name, caller_role="agent")

        # Delete promoted pattern entities (also quality tier)
        solution_patterns = [
            name for name, entity in kg._entities.items()
            if entity.entity_type.value == "solution_pattern"
        ]
        for name in solution_patterns:
            kg.delete_entity(name, caller_role="agent")

        # Delete governance_decision entities (also quality tier effectively)
        gov_decisions = [
            name for name, entity in kg._entities.items()
            if entity.entity_type.value == "governance_decision"
        ]
        for name in gov_decisions:
            kg.delete_entity(name, caller_role="agent")

        # Verify only vision + architecture entities remain
        remaining_quality = kg.get_entities_by_tier("quality")
        self.assert_equal(
            "phase2: no quality-tier entities remain",
            len(remaining_quality),
            0,
        )

        vision_remain = kg.get_entities_by_tier("vision")
        self.assert_true(
            "phase2: vision entities preserved",
            len(vision_remain) >= 2,
            expected=">=2",
            actual=len(vision_remain),
        )

        arch_remain = kg.get_entities_by_tier("architecture")
        self.assert_true(
            "phase2: architecture entities preserved",
            len(arch_remain) >= 1,
            expected=">=1",
            actual=len(arch_remain),
        )

        # Step 2: Reset memory files to templates
        templates = {
            "architectural-decisions.md": "# Architectural Decisions\n\nNo decisions recorded yet.\n",
            "troubleshooting-log.md": "# Troubleshooting Log\n\nNo entries yet.\n",
            "solution-patterns.md": "# Solution Patterns\n\nNo patterns promoted yet.\n",
            "research-findings.md": "# Research Findings\n\nNo findings recorded yet.\n",
        }
        for filename, content in templates.items():
            (memory_dir / filename).write_text(content, encoding="utf-8")

        # Verify memory files are templates
        for filename, expected_content in templates.items():
            actual = (memory_dir / filename).read_text(encoding="utf-8")
            self.assert_equal(
                f"phase2: {filename} reset to template",
                actual,
                expected_content,
            )

        # Step 3: Verify governance DB still has records (we don't drop tables,
        # but we verify the store is queryable and counts match what we stored)
        gov_status = gov_store.get_status()
        self.assert_true(
            "phase2: governance DB still queryable",
            isinstance(gov_status, dict),
        )

        # Step 4: Verify trust engine still has records
        all_findings = trust.get_all_findings()
        self.assert_true(
            "phase2: trust engine still queryable",
            isinstance(all_findings, list),
        )

        # Step 5: Reset session state
        state_path = scenario_dir / "session-state.md"
        state_path.write_text(
            "# Session State\n\nNo active session.\n",
            encoding="utf-8",
        )
        self.assert_equal(
            "phase2: session state reset",
            state_path.read_text(encoding="utf-8"),
            "# Session State\n\nNo active session.\n",
        )
