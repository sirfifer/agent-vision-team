"""Per-project application state and registry.

Replaces the former module-level singleton with a registry of per-project
state objects, enabling multi-project management through a single gateway.
"""

from __future__ import annotations

import logging
from pathlib import Path

from .services.project_config import ProjectConfigService
from .services.file_service import FileService

logger = logging.getLogger(__name__)


class ProjectState:
    """Holds service instances for a single project context."""

    def __init__(self, project_dir: Path, mcp_ports: tuple[int, int, int]) -> None:
        self.project_dir = project_dir
        self.mcp_ports = mcp_ports  # (kg_port, quality_port, governance_port)
        self.project_config = ProjectConfigService(project_dir)
        self.file_service = FileService(project_dir)
        # MCP client and job runner are initialized lazily
        self.mcp = None  # McpClientService | None
        self._job_runner = None  # JobRunner | None

    @property
    def kg_url(self) -> str:
        return f"http://localhost:{self.mcp_ports[0]}"

    @property
    def quality_url(self) -> str:
        return f"http://localhost:{self.mcp_ports[1]}"

    @property
    def governance_url(self) -> str:
        return f"http://localhost:{self.mcp_ports[2]}"

    def get_job_runner(self):
        """Lazily create the per-project job runner."""
        if self._job_runner is None:
            from .services.job_runner import JobRunner
            self._job_runner = JobRunner(project_dir=self.project_dir)
        return self._job_runner

    async def connect_mcp(self) -> None:
        """Connect to this project's MCP servers."""
        from .services.mcp_client import McpClientService
        self.mcp = McpClientService(
            kg_url=self.kg_url,
            quality_url=self.quality_url,
            governance_url=self.governance_url,
        )
        await self.mcp.connect()
        logger.info("MCP connected for project at %s", self.project_dir)

    async def disconnect_mcp(self) -> None:
        """Disconnect this project's MCP client."""
        if self.mcp:
            await self.mcp.disconnect()
            self.mcp = None


class ProjectStateRegistry:
    """Registry of per-project state objects."""

    def __init__(self) -> None:
        self._states: dict[str, ProjectState] = {}

    def get(self, project_id: str) -> ProjectState:
        """Get project state by ID. Raises KeyError if not found."""
        if project_id not in self._states:
            raise KeyError(f"Project not registered: {project_id}")
        return self._states[project_id]

    def get_or_none(self, project_id: str) -> ProjectState | None:
        """Get project state by ID, returning None if not found."""
        return self._states.get(project_id)

    def register(
        self, project_id: str, project_dir: Path, ports: tuple[int, int, int]
    ) -> ProjectState:
        """Register a new project state. Returns existing if already registered."""
        if project_id in self._states:
            return self._states[project_id]
        state = ProjectState(project_dir, ports)
        self._states[project_id] = state
        logger.info("Registered project state: %s -> %s (ports %s)", project_id, project_dir, ports)
        return state

    def remove(self, project_id: str) -> None:
        """Remove a project state."""
        self._states.pop(project_id, None)

    def list_ids(self) -> list[str]:
        """List all registered project IDs."""
        return list(self._states.keys())

    async def disconnect_all(self) -> None:
        """Disconnect all MCP clients (called on shutdown)."""
        for state in self._states.values():
            await state.disconnect_mcp()


# Module-level singleton registry
registry = ProjectStateRegistry()
