"""Parallel executor for E2E test scenarios.

Routes scenarios by isolation mode:
- ``"library"`` scenarios run in parallel via ``ThreadPoolExecutor``, each
  receiving its own ``KnowledgeGraph``, ``GovernanceStore``, and
  ``TaskFileManager`` pointed at a per-scenario temp directory.
- ``"http"`` scenarios run serially (they communicate with shared MCP
  servers and cannot safely overlap).

Each library scenario's KnowledgeGraph is pre-populated with the project's
vision and architecture standards so that governance assertions behave
realistically.
"""

from __future__ import annotations

import logging
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import TYPE_CHECKING, Any

# ---------------------------------------------------------------------------
# Path setup — allow direct imports of MCP server packages
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

_KG_PKG = _PROJECT_ROOT / "mcp-servers" / "knowledge-graph"
_GOV_PKG = _PROJECT_ROOT / "mcp-servers" / "governance"

if str(_KG_PKG) not in sys.path:
    sys.path.insert(0, str(_KG_PKG))
if str(_GOV_PKG) not in sys.path:
    sys.path.insert(0, str(_GOV_PKG))

from collab_governance.store import GovernanceStore
from collab_governance.task_integration import TaskFileManager
from collab_kg.graph import KnowledgeGraph

if TYPE_CHECKING:
    from e2e.scenarios.base import BaseScenario, ScenarioResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default vision / architecture standards seeded into every isolated KG
# ---------------------------------------------------------------------------

_DEFAULT_VISION_STANDARDS: list[dict[str, Any]] = [
    {
        "name": "Protocol-Based DI",
        "entityType": "vision_standard",
        "observations": [
            "protection_tier: vision",
            "All services MUST use protocol-based dependency injection",
        ],
    },
    {
        "name": "No Production Singletons",
        "entityType": "vision_standard",
        "observations": [
            "protection_tier: vision",
            "No singletons in production code; test doubles are acceptable",
        ],
    },
    {
        "name": "Public API Integration Tests",
        "entityType": "vision_standard",
        "observations": [
            "protection_tier: vision",
            "Every public API MUST have at least one integration test",
        ],
    },
    {
        "name": "Authorization Required",
        "entityType": "vision_standard",
        "observations": [
            "protection_tier: vision",
            "All data access MUST pass through the authorization layer",
        ],
    },
    {
        "name": "Result-Type Error Handling",
        "entityType": "vision_standard",
        "observations": [
            "protection_tier: vision",
            "Error handling MUST use Result types; thrown exceptions are forbidden outside infrastructure adapters",
        ],
    },
]

_DEFAULT_ARCHITECTURE_PATTERNS: list[dict[str, Any]] = [
    {
        "name": "ServiceRegistry Pattern",
        "entityType": "architectural_standard",
        "observations": [
            "protection_tier: architecture",
            "All services are resolved through a centralized ServiceRegistry at startup",
        ],
    },
    {
        "name": "Async Event Channels",
        "entityType": "architectural_standard",
        "observations": [
            "protection_tier: architecture",
            "Inter-service communication uses async event channels; no direct service-to-service calls in the hot path",
        ],
    },
]


class ParallelExecutor:
    """Execute a batch of E2E scenarios with isolation-mode-aware scheduling.

    Parameters
    ----------
    workspace:
        Root directory for all scenario-specific temp directories.
    max_workers:
        Maximum number of library scenarios to execute in parallel.
    """

    def __init__(self, workspace: Path, max_workers: int = 4) -> None:
        self.workspace = workspace
        self.max_workers = max_workers
        self.workspace.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_scenarios(self, scenarios: list[BaseScenario]) -> list[ScenarioResult]:
        """Execute *scenarios* and return their results.

        Library-mode scenarios are run in parallel; HTTP-mode scenarios
        are run serially afterwards.
        """
        library_scenarios = [s for s in scenarios if s.isolation_mode == "library"]
        http_scenarios = [s for s in scenarios if s.isolation_mode == "http"]

        results: list[ScenarioResult] = []

        # -- Library scenarios: parallel via ThreadPoolExecutor --------
        if library_scenarios:
            logger.info(
                "Running %d library scenario(s) in parallel (max_workers=%d)",
                len(library_scenarios),
                self.max_workers,
            )
            results.extend(self._run_library_parallel(library_scenarios))

        # -- HTTP scenarios: serial ------------------------------------
        if http_scenarios:
            logger.info(
                "Running %d HTTP scenario(s) serially",
                len(http_scenarios),
            )
            results.extend(self._run_http_serial(http_scenarios))

        return results

    # ------------------------------------------------------------------
    # Internal: library-mode parallel execution
    # ------------------------------------------------------------------

    def _run_library_parallel(self, scenarios: list[BaseScenario]) -> list[ScenarioResult]:
        """Run library scenarios concurrently, each with isolated storage."""
        from e2e.scenarios.base import AssertionResult, ScenarioResult

        results: list[ScenarioResult] = []
        future_to_name: dict[Any, str] = {}

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            for scenario in scenarios:
                scenario_dir = self.workspace / scenario.name.replace(" ", "_")
                scenario_dir.mkdir(parents=True, exist_ok=True)
                future = pool.submit(self._run_isolated, scenario, scenario_dir)
                future_to_name[future] = scenario.name

            for future in as_completed(future_to_name):
                name = future_to_name[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as exc:
                    tb = traceback.format_exc()
                    logger.error("Scenario %r raised: %s", name, exc)
                    results.append(
                        ScenarioResult(
                            name=name,
                            passed=0,
                            failed=1,
                            assertions=[
                                AssertionResult(
                                    name="executor",
                                    passed=False,
                                    expected="no error",
                                    actual=str(exc),
                                    error=tb,
                                )
                            ],
                            duration_ms=0,
                            scenario_type="mixed",
                            error=str(exc),
                        )
                    )

        return results

    # ------------------------------------------------------------------
    # Internal: HTTP-mode serial execution
    # ------------------------------------------------------------------

    def _run_http_serial(self, scenarios: list[BaseScenario]) -> list[ScenarioResult]:
        """Run HTTP scenarios one at a time (they share MCP servers)."""
        from e2e.scenarios.base import AssertionResult, ScenarioResult

        results: list[ScenarioResult] = []

        for scenario in scenarios:
            scenario_dir = self.workspace / scenario.name.replace(" ", "_")
            scenario_dir.mkdir(parents=True, exist_ok=True)
            try:
                result = scenario.execute()
                results.append(result)
            except Exception as exc:
                tb = traceback.format_exc()
                logger.error("HTTP scenario %r raised: %s", scenario.name, exc)
                results.append(
                    ScenarioResult(
                        name=scenario.name,
                        passed=0,
                        failed=1,
                        assertions=[
                            AssertionResult(
                                name="executor",
                                passed=False,
                                expected="no error",
                                actual=str(exc),
                                error=tb,
                            )
                        ],
                        duration_ms=0,
                        scenario_type="mixed",
                        error=str(exc),
                    )
                )

        return results

    # ------------------------------------------------------------------
    # Internal: isolated execution of a single library scenario
    # ------------------------------------------------------------------

    def _run_isolated(self, scenario: BaseScenario, scenario_dir: Path) -> ScenarioResult:
        """Create isolated storage instances and execute *scenario*.

        Each scenario receives:
        - ``kg``: a ``KnowledgeGraph`` backed by a per-scenario JSONL file,
          pre-populated with vision and architecture standards.
        - ``gov_store``: a ``GovernanceStore`` backed by a per-scenario
          SQLite database.
        - ``task_mgr``: a ``TaskFileManager`` writing to a per-scenario
          task directory.
        """
        # ---- Knowledge Graph (isolated JSONL) ------------------------
        kg_path = scenario_dir / "knowledge-graph.jsonl"
        kg = KnowledgeGraph(storage_path=str(kg_path))
        self._seed_kg(kg)

        # ---- Governance Store (isolated SQLite) ----------------------
        gov_db_path = scenario_dir / "governance.db"
        gov_store = GovernanceStore(db_path=gov_db_path)

        # ---- Task File Manager (isolated task dir) -------------------
        task_dir = scenario_dir / "tasks"
        task_dir.mkdir(parents=True, exist_ok=True)
        task_mgr = TaskFileManager(task_dir=task_dir)

        # ---- Execute scenario with injected dependencies -------------
        logger.info("Executing scenario %r in %s", scenario.name, scenario_dir)
        result = scenario.execute(
            kg=kg,
            gov_store=gov_store,
            task_mgr=task_mgr,
            scenario_dir=scenario_dir,
        )

        # ---- Cleanup SQLite connection to avoid leaked handles -------
        gov_store.close()

        return result

    # ------------------------------------------------------------------
    # Internal: seed a KG with project-level standards
    # ------------------------------------------------------------------

    @staticmethod
    def _seed_kg(kg: KnowledgeGraph) -> None:
        """Pre-populate *kg* with the canonical vision and architecture standards.

        This ensures every scenario starts with a realistic governance
        baseline that tier-protection and verdict scenarios can exercise.
        """
        kg.create_entities(_DEFAULT_VISION_STANDARDS)
        kg.create_entities(_DEFAULT_ARCHITECTURE_PATTERNS)
