"""E2E test harness project generator.

Generates a realistic project workspace by randomly selecting a domain,
filling in vision/architecture templates, and writing out the ``.avt/``
system directory and ``docs/`` project directory structures together with
a seeded ``knowledge-graph.jsonl``.

Usage::

    from pathlib import Path
    from e2e.generator.project_generator import generate_project

    project = generate_project(Path("/tmp/test-workspace"))
    print(project.domain_name, project.vision_standards)

Only the standard library and ``pathlib`` are used -- no external deps.
"""

from __future__ import annotations

import json
import random
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from e2e.generator.domain_templates import DomainTemplate, get_domain_pool


# ---------------------------------------------------------------------------
# Public data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class VisionStandard:
    """A single materialised vision standard ready for the KG."""

    name: str
    statement: str
    tier: str = "vision"


@dataclass(frozen=True, slots=True)
class ArchitecturePattern:
    """A single materialised architecture pattern ready for the KG."""

    name: str
    description: str
    tier: str = "architecture"


@dataclass(slots=True)
class GeneratedProject:
    """All metadata produced by :func:`generate_project`.

    Scenarios and validators consume this to know *what* was generated and
    *where* each artefact lives on disk.
    """

    # Domain identity
    domain_name: str
    domain_prefix: str
    components: list[str]

    # Materialised standards & patterns
    vision_standards: list[dict[str, str]]
    architecture_patterns: list[dict[str, str]]

    # Filesystem paths
    workspace_path: Path
    kg_path: Path
    governance_db_path: Path

    # Convenience: raw domain template used for generation
    _domain_template: DomainTemplate = field(repr=False)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _pick_domain(rng: random.Random) -> DomainTemplate:
    """Select a random domain from the pool."""
    pool = get_domain_pool()
    return pool[rng.randint(0, len(pool) - 1)]


def _fill_template(
    template: str,
    *,
    domain: str,
    prefix: str,
    component: str,
) -> str:
    """Replace ``{domain}``, ``{prefix}``, and ``{component}`` placeholders."""
    return (
        template
        .replace("{domain}", domain)
        .replace("{prefix}", prefix)
        .replace("{component}", component)
    )


def _materialise_vision_standards(
    domain: DomainTemplate,
    rng: random.Random,
) -> list[VisionStandard]:
    """Fill vision templates with a randomly chosen component per template."""
    standards: list[VisionStandard] = []
    archetype_labels = (
        "protocol_di",
        "no_singletons",
        "integration_tests",
        "authorization",
        "result_error_handling",
    )
    for idx, tmpl in enumerate(domain.vision_templates):
        component = domain.components[rng.randint(0, len(domain.components) - 1)]
        statement = _fill_template(
            tmpl,
            domain=domain.name,
            prefix=domain.prefix,
            component=component,
        )
        label = archetype_labels[idx] if idx < len(archetype_labels) else f"custom_{idx}"
        name = f"{domain.prefix}_vision_{label}"
        standards.append(VisionStandard(name=name, statement=statement))
    return standards


def _materialise_architecture_patterns(
    domain: DomainTemplate,
    rng: random.Random,
) -> list[ArchitecturePattern]:
    """Fill architecture templates with a randomly chosen component per template."""
    patterns: list[ArchitecturePattern] = []
    pattern_labels = ("service_registry", "communication", "read_model")
    for idx, tmpl in enumerate(domain.architecture_templates):
        component = domain.components[rng.randint(0, len(domain.components) - 1)]
        description = _fill_template(
            tmpl,
            domain=domain.name,
            prefix=domain.prefix,
            component=component,
        )
        label = pattern_labels[idx] if idx < len(pattern_labels) else f"pattern_{idx}"
        name = f"{domain.prefix}_arch_{label}"
        patterns.append(ArchitecturePattern(name=name, description=description))
    return patterns


# ---------------------------------------------------------------------------
# Filesystem writers
# ---------------------------------------------------------------------------

def _write_directory_structure(workspace: Path) -> dict[str, Path]:
    """Create the ``.avt/``, ``docs/``, and ``.claude/collab/`` directory trees.

    Returns a dict mapping logical names to their created paths.
    """
    dirs: dict[str, Path] = {}

    # .avt directories (system internals)
    for subdir in (
        "task-briefs",
        "memory",
        "research-prompts",
        "research-briefs",
    ):
        p = workspace / ".avt" / subdir
        p.mkdir(parents=True, exist_ok=True)
        dirs[subdir] = p

    # docs/ directories (project-level artifacts)
    for subdir in ("vision", "architecture"):
        p = workspace / "docs" / subdir
        p.mkdir(parents=True, exist_ok=True)
        dirs[subdir] = p

    # .claude/collab for KG and governance DB
    collab = workspace / ".claude" / "collab"
    collab.mkdir(parents=True, exist_ok=True)
    dirs["collab"] = collab

    # .claude/agents (empty, but expected by the system)
    agents = workspace / ".claude" / "agents"
    agents.mkdir(parents=True, exist_ok=True)
    dirs["agents"] = agents

    return dirs


def _write_knowledge_graph(
    kg_path: Path,
    vision_standards: list[VisionStandard],
    architecture_patterns: list[ArchitecturePattern],
) -> None:
    """Write the seeded ``knowledge-graph.jsonl`` file.

    Format matches the KG MCP server's JSONL persistence: one JSON object per
    line with ``type``, ``name``, ``entityType``, and ``observations`` keys.
    """
    lines: list[str] = []

    for vs in vision_standards:
        entity: dict[str, Any] = {
            "type": "entity",
            "name": vs.name,
            "entityType": "vision_standard",
            "observations": [
                f"protection_tier: {vs.tier}",
                f"mutability: human_only",
                vs.statement,
            ],
        }
        lines.append(json.dumps(entity, separators=(",", ":")))

    for ap in architecture_patterns:
        entity = {
            "type": "entity",
            "name": ap.name,
            "entityType": "pattern",
            "observations": [
                f"protection_tier: {ap.tier}",
                ap.description,
            ],
        }
        lines.append(json.dumps(entity, separators=(",", ":")))

    kg_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_project_config(
    workspace: Path,
    domain: DomainTemplate,
) -> None:
    """Write ``.avt/project-config.json`` with sensible defaults."""
    config: dict[str, Any] = {
        "version": 1,
        "setupComplete": True,
        "projectName": domain.name,
        "projectPrefix": domain.prefix,
        "languages": ["python"],
        "metadata": {
            "isOpenSource": False,
            "generatedBy": "e2e-project-generator",
        },
        "settings": {
            "mockTests": False,
            "mockTestsForCostlyOps": True,
            "coverageThreshold": 80,
            "autoGovernance": True,
            "qualityGates": {
                "build": True,
                "lint": True,
                "tests": True,
                "coverage": True,
                "findings": True,
            },
            "kgAutoCuration": True,
        },
        "quality": {
            "testCommands": {"python": "uv run pytest"},
            "lintCommands": {"python": "uv run ruff check"},
            "formatCommands": {"python": "uv run ruff format"},
        },
        "permissions": [],
        "ingestion": {
            "lastVisionIngest": None,
            "lastArchitectureIngest": None,
            "visionDocCount": len(domain.vision_templates),
            "architectureDocCount": len(domain.architecture_templates),
        },
    }
    config_path = workspace / ".avt" / "project-config.json"
    config_path.write_text(
        json.dumps(config, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def _write_session_state(workspace: Path, domain: DomainTemplate) -> None:
    """Write an initial ``.avt/session-state.md``."""
    content = (
        f"# Session State -- {domain.name}\n"
        "\n"
        "## Status\n"
        "\n"
        "Generated by E2E project generator. No work has been started.\n"
    )
    (workspace / ".avt" / "session-state.md").write_text(content, encoding="utf-8")


def _write_memory_stubs(workspace: Path) -> None:
    """Create empty archival memory files expected by the system."""
    memory_dir = workspace / ".avt" / "memory"
    stubs = {
        "architectural-decisions.md": "# Architectural Decisions\n\nNo decisions recorded yet.\n",
        "troubleshooting-log.md": "# Troubleshooting Log\n\nNo entries yet.\n",
        "solution-patterns.md": "# Solution Patterns\n\nNo patterns promoted yet.\n",
        "research-findings.md": "# Research Findings\n\nNo findings recorded yet.\n",
    }
    for filename, content in stubs.items():
        (memory_dir / filename).write_text(content, encoding="utf-8")


def _ensure_governance_db(workspace: Path) -> Path:
    """Create an empty governance DB placeholder.

    The real governance server initialises its own SQLite schema on first
    access. For E2E purposes we just ensure the file exists so that path
    references in ``GeneratedProject`` are valid.
    """
    db_path = workspace / ".claude" / "collab" / "governance.db"
    if not db_path.exists():
        db_path.touch()
    return db_path


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_project(
    workspace: Path,
    *,
    seed: int | None = None,
) -> GeneratedProject:
    """Generate a complete test project in *workspace*.

    Parameters
    ----------
    workspace:
        Root directory for the generated project. Will be created if it does
        not exist. Must be an empty or non-existent directory.
    seed:
        Optional RNG seed for reproducible generation. When ``None`` a random
        seed is used.

    Returns
    -------
    GeneratedProject
        Dataclass containing all metadata needed by E2E scenarios and
        validators.

    Raises
    ------
    FileExistsError
        If *workspace* already contains an ``.avt/`` directory (to prevent
        accidentally overwriting a real project).
    """
    rng = random.Random(seed)

    # Guard against overwriting real projects
    if (workspace / ".avt").exists():
        msg = (
            f"Workspace already contains an .avt/ directory: {workspace}. "
            "Refusing to overwrite. Use a clean directory."
        )
        raise FileExistsError(msg)

    workspace.mkdir(parents=True, exist_ok=True)

    # 1. Pick a domain
    domain = _pick_domain(rng)

    # 2. Materialise templates
    vision_standards = _materialise_vision_standards(domain, rng)
    architecture_patterns = _materialise_architecture_patterns(domain, rng)

    # 3. Write directory structure
    dirs = _write_directory_structure(workspace)

    # 4. Write knowledge graph
    kg_path = dirs["collab"] / "knowledge-graph.jsonl"
    _write_knowledge_graph(kg_path, vision_standards, architecture_patterns)

    # 5. Write project config
    _write_project_config(workspace, domain)

    # 6. Write session state & memory stubs
    _write_session_state(workspace, domain)
    _write_memory_stubs(workspace)

    # 7. Create governance DB placeholder
    governance_db_path = _ensure_governance_db(workspace)

    # 8. Build and return the project descriptor
    return GeneratedProject(
        domain_name=domain.name,
        domain_prefix=domain.prefix,
        components=list(domain.components),
        vision_standards=[
            {"name": vs.name, "statement": vs.statement, "tier": vs.tier}
            for vs in vision_standards
        ],
        architecture_patterns=[
            {"name": ap.name, "description": ap.description, "tier": ap.tier}
            for ap in architecture_patterns
        ],
        workspace_path=workspace,
        kg_path=kg_path,
        governance_db_path=governance_db_path,
        _domain_template=domain,
    )
