"""Project manager: manages multi-project lifecycle and MCP server processes."""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from pathlib import Path

from ..models.project import ProjectInfo, ProjectStatus

logger = logging.getLogger(__name__)

# Base port for the first project's MCP servers (KG, Quality, Governance)
MCP_BASE_PORT = 3101
# Number of MCP server ports per project
PORTS_PER_PROJECT = 3

# Global registry path
_REGISTRY_DIR = Path.home() / ".avt"
_REGISTRY_PATH = _REGISTRY_DIR / "projects.json"

# Path to MCP server packages (relative to this repo root)
_REPO_ROOT = Path(__file__).parent.parent.parent.parent  # server/ -> repo root
_MCP_SERVERS = {
    "kg": _REPO_ROOT / "mcp-servers" / "knowledge-graph",
    "quality": _REPO_ROOT / "mcp-servers" / "quality",
    "governance": _REPO_ROOT / "mcp-servers" / "governance",
}
_MCP_MODULES = {
    "kg": "collab_kg.server",
    "quality": "collab_quality.server",
    "governance": "collab_governance.server",
}


def _slugify(name: str) -> str:
    """Convert a project path or name to a URL-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug or "project"


class ProjectManager:
    """Manages project registry and MCP server process groups."""

    def __init__(self) -> None:
        self._projects: dict[str, ProjectInfo] = {}
        # pid tracking: project_id -> {"kg": pid, "quality": pid, "governance": pid}
        self._processes: dict[str, dict[str, subprocess.Popen]] = {}
        self._load_registry()

    # ── Registry persistence ─────────────────────────────────────────────

    def _load_registry(self) -> None:
        """Load project registry from ~/.avt/projects.json."""
        if _REGISTRY_PATH.exists():
            try:
                data = json.loads(_REGISTRY_PATH.read_text())
                for entry in data.get("projects", []):
                    project = ProjectInfo(**entry)
                    # Reset status to stopped on load (processes died with gateway)
                    project.status = ProjectStatus.STOPPED
                    self._projects[project.id] = project
                logger.info("Loaded %d projects from registry", len(self._projects))
            except Exception as exc:
                logger.warning("Failed to load project registry: %s", exc)

    def _save_registry(self) -> None:
        """Persist project registry to ~/.avt/projects.json."""
        _REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
        data = {"projects": [p.model_dump() for p in self._projects.values()]}
        _REGISTRY_PATH.write_text(json.dumps(data, indent=2))

    # ── Port allocation ──────────────────────────────────────────────────

    def _next_slot(self) -> int:
        """Find the next available port slot."""
        used_slots = {p.slot for p in self._projects.values()}
        slot = 0
        while slot in used_slots:
            slot += 1
        return slot

    # ── Project CRUD ─────────────────────────────────────────────────────

    def list_projects(self) -> list[ProjectInfo]:
        """List all registered projects."""
        return list(self._projects.values())

    def get_project(self, project_id: str) -> ProjectInfo | None:
        """Get a project by ID."""
        return self._projects.get(project_id)

    def add_project(self, path: str, name: str | None = None) -> ProjectInfo:
        """Register a new project directory."""
        project_path = Path(path).resolve()
        if not project_path.is_dir():
            raise ValueError(f"Path does not exist or is not a directory: {path}")

        # Derive ID and name
        display_name = name or project_path.name
        project_id = _slugify(display_name)

        # Ensure unique ID
        base_id = project_id
        counter = 2
        while project_id in self._projects:
            # Check if it's the same path (re-add)
            if self._projects[project_id].path == str(project_path):
                return self._projects[project_id]
            project_id = f"{base_id}-{counter}"
            counter += 1

        slot = self._next_slot()
        project = ProjectInfo(
            id=project_id,
            name=display_name,
            path=str(project_path),
            slot=slot,
            mcp_base_port=MCP_BASE_PORT + (slot * PORTS_PER_PROJECT),
        )
        self._projects[project_id] = project
        self._save_registry()
        logger.info(
            "Added project '%s' at %s (slot %d, ports %d-%d)",
            project_id,
            path,
            slot,
            project.kg_port,
            project.governance_port,
        )
        return project

    def remove_project(self, project_id: str) -> None:
        """Unregister a project, stopping its MCP servers if running."""
        if project_id not in self._projects:
            raise KeyError(f"Project not found: {project_id}")

        self.stop_project(project_id)
        del self._projects[project_id]
        self._save_registry()
        logger.info("Removed project '%s'", project_id)

    # ── MCP process lifecycle ────────────────────────────────────────────

    def start_project(self, project_id: str) -> ProjectInfo:
        """Start MCP server processes for a project."""
        project = self._projects.get(project_id)
        if not project:
            raise KeyError(f"Project not found: {project_id}")

        if project.status == ProjectStatus.RUNNING:
            return project

        project.status = ProjectStatus.STARTING
        processes: dict[str, subprocess.Popen] = {}

        port_map = {
            "kg": project.kg_port,
            "quality": project.quality_port,
            "governance": project.governance_port,
        }

        try:
            for server_name, port in port_map.items():
                server_dir = _MCP_SERVERS[server_name]
                module = _MCP_MODULES[server_name]

                # Run from the MCP server package directory (so uv finds pyproject.toml),
                # but set PROJECT_DIR so the server chdir's to the project for data isolation.
                env = {
                    **os.environ,
                    "PORT": str(port),
                    "PROJECT_DIR": str(project.path),
                }
                proc = subprocess.Popen(
                    ["uv", "run", "python", "-m", module],
                    cwd=str(server_dir),
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                )
                processes[server_name] = proc
                logger.info(
                    "Started %s MCP server for '%s' on port %d (pid %d)", server_name, project_id, port, proc.pid
                )

            self._processes[project_id] = processes
            project.status = ProjectStatus.RUNNING
            self._save_registry()
            return project

        except Exception as exc:
            # Clean up any started processes
            for proc in processes.values():
                try:
                    proc.terminate()
                except Exception:
                    pass
            project.status = ProjectStatus.ERROR
            self._save_registry()
            raise RuntimeError(f"Failed to start MCP servers for '{project_id}': {exc}")

    def stop_project(self, project_id: str) -> ProjectInfo | None:
        """Stop MCP server processes for a project."""
        project = self._projects.get(project_id)
        if not project:
            return None

        processes = self._processes.pop(project_id, {})
        for server_name, proc in processes.items():
            try:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=2)
                logger.info("Stopped %s MCP server for '%s' (pid %d)", server_name, project_id, proc.pid)
            except Exception as exc:
                logger.warning("Error stopping %s for '%s': %s", server_name, project_id, exc)

        project.status = ProjectStatus.STOPPED
        self._save_registry()
        return project

    def stop_all(self) -> None:
        """Stop all running MCP server processes (called on gateway shutdown)."""
        for project_id in list(self._processes.keys()):
            self.stop_project(project_id)

    def check_health(self, project_id: str) -> dict[str, bool]:
        """Check if MCP processes are still alive for a project."""
        processes = self._processes.get(project_id, {})
        health: dict[str, bool] = {}
        for server_name, proc in processes.items():
            health[server_name] = proc.poll() is None  # None means still running
        return health


# Module-level singleton
_manager: ProjectManager | None = None


def get_project_manager() -> ProjectManager:
    """Get (or create) the singleton ProjectManager."""
    global _manager
    if _manager is None:
        _manager = ProjectManager()
    return _manager
