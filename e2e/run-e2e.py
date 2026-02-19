#!/usr/bin/env python3
"""E2E test orchestrator for the Collaborative Intelligence System.

Usage::

    # From the project root:
    uv run python e2e/run-e2e.py --workspace /tmp/avt-e2e

    # Or via the shell wrapper:
    ./e2e/run-e2e.sh

The orchestrator:

1. Generates a unique, randomised project via the project generator.
2. Instantiates every registered scenario.
3. Runs them through the ``ParallelExecutor`` (library-mode in parallel,
   HTTP-mode serially).
4. Generates a JSON report and prints a human-readable summary.
5. Exits with code 0 if every scenario passed, 1 otherwise.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup — ensure the e2e package and MCP server packages are importable
# ---------------------------------------------------------------------------

_E2E_ROOT = Path(__file__).resolve().parent
_PROJECT_ROOT = _E2E_ROOT.parent

if str(_E2E_ROOT) not in sys.path:
    sys.path.insert(0, str(_E2E_ROOT))
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
if str(_PROJECT_ROOT / "mcp-servers" / "knowledge-graph") not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "mcp-servers" / "knowledge-graph"))
if str(_PROJECT_ROOT / "mcp-servers" / "governance") not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "mcp-servers" / "governance"))
if str(_PROJECT_ROOT / "mcp-servers" / "quality") not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "mcp-servers" / "quality"))

from e2e.generator.project_generator import generate_project
from e2e.parallel.executor import ParallelExecutor
from e2e.scenarios.base import BaseScenario, ScenarioResult

# ---------------------------------------------------------------------------
# Scenario imports
# ---------------------------------------------------------------------------
# Each scenario module exposes a single class inheriting from BaseScenario.
from e2e.scenarios.s01_kg_tier_protection import KGTierProtectionScenario
from e2e.scenarios.s02_governance_decision_flow import GovernanceDecisionFlowScenario
from e2e.scenarios.s03_governed_task_lifecycle import GovernedTaskLifecycleScenario
from e2e.scenarios.s04_vision_violation import S04VisionViolation
from e2e.scenarios.s05_architecture_deviation import S05ArchitectureDeviation
from e2e.scenarios.s06_quality_gates import S06QualityGates
from e2e.scenarios.s07_trust_engine import S07TrustEngine
from e2e.scenarios.s08_multi_blocker_task import S08MultiBlockerTask
from e2e.scenarios.s09_scope_change_detection import S09ScopeChangeDetection
from e2e.scenarios.s10_completion_guard import S10CompletionGuard
from e2e.scenarios.s11_hook_based_governance import HookBasedGovernanceScenario
from e2e.scenarios.s12_cross_server_integration import S12CrossServerIntegration
from e2e.scenarios.s13_hook_pipeline_at_scale import HookPipelineAtScaleScenario
from e2e.scenarios.s14_persistence_lifecycle import S14PersistenceLifecycle
from e2e.validation.report_generator import generate_report, print_summary

# Registry of all scenario classes to instantiate.
ALL_SCENARIO_CLASSES: list[type[BaseScenario]] = [
    KGTierProtectionScenario,
    GovernanceDecisionFlowScenario,
    GovernedTaskLifecycleScenario,
    S04VisionViolation,
    S05ArchitectureDeviation,
    S06QualityGates,
    S07TrustEngine,
    S08MultiBlockerTask,
    S09ScopeChangeDetection,
    S10CompletionGuard,
    HookBasedGovernanceScenario,
    S12CrossServerIntegration,
    HookPipelineAtScaleScenario,
    S14PersistenceLifecycle,
]

# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

logger = logging.getLogger("e2e")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the E2E test suite for the Collaborative Intelligence System.",
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        required=True,
        help="Root directory for the generated project and scenario isolation.",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="Maximum parallel threads for library-mode scenarios (default: 4).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="RNG seed for reproducible project generation.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        default=False,
        help="Enable verbose (DEBUG-level) logging.",
    )
    # --keep is handled by the shell wrapper; accept and ignore here.
    parser.add_argument(
        "--keep",
        action="store_true",
        default=False,
        help=argparse.SUPPRESS,
    )
    return parser.parse_args(argv)


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(name)-20s  %(levelname)-7s  %(message)s",
        datefmt="%H:%M:%S",
    )


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns 0 on success, 1 on any scenario failure."""
    args = _parse_args(argv)
    _setup_logging(args.verbose)

    workspace: Path = args.workspace.resolve()
    project_dir = workspace / "project"

    # ------------------------------------------------------------------
    # 1. Generate a unique project
    # ------------------------------------------------------------------
    logger.info("Generating project in %s ...", project_dir)
    project = generate_project(project_dir, seed=args.seed)
    logger.info(
        "Generated domain: %s  (prefix=%s, components=%s)",
        project.domain_name,
        project.domain_prefix,
        project.components,
    )

    # ------------------------------------------------------------------
    # 2. Instantiate all scenarios
    # ------------------------------------------------------------------
    scenarios: list[BaseScenario] = []
    for cls in ALL_SCENARIO_CLASSES:
        scenario = cls(project=project, workspace=workspace)
        scenarios.append(scenario)
        logger.debug("Registered scenario: %s (mode=%s)", scenario.name, scenario.isolation_mode)

    logger.info("Registered %d scenario(s)", len(scenarios))

    # ------------------------------------------------------------------
    # 3. Run via ParallelExecutor
    # ------------------------------------------------------------------
    executor = ParallelExecutor(workspace=workspace, max_workers=args.max_workers)
    t0 = time.monotonic()
    results: list[ScenarioResult] = executor.run_scenarios(scenarios)
    elapsed = time.monotonic() - t0
    logger.info("Execution completed in %.2fs", elapsed)

    # ------------------------------------------------------------------
    # 4. Generate report
    # ------------------------------------------------------------------
    report_path = workspace / "e2e-report.json"
    generate_report(
        results,
        suite_name=f"E2E: {project.domain_name}",
        json_path=report_path,
        print_to_console=False,
    )
    logger.info("JSON report written to %s", report_path)

    # ------------------------------------------------------------------
    # 5. Print summary
    # ------------------------------------------------------------------
    print_summary(
        results,
        suite_name=f"E2E: {project.domain_name}",
        report_path=report_path,
    )

    # ------------------------------------------------------------------
    # 6. Exit with appropriate code
    # ------------------------------------------------------------------
    all_passed = all(r.success for r in results)
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
