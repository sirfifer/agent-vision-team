"""Project model for multi-project management."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class ProjectStatus(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"


class ProjectInfo(BaseModel):
    id: str  # slug, e.g. "agent-vision-team"
    name: str  # display name
    path: str  # absolute path to project root
    status: ProjectStatus = ProjectStatus.STOPPED
    slot: int  # port allocation slot (0, 1, 2, ...)
    mcp_base_port: int  # base port = 3101 + (slot * 3)

    @property
    def kg_port(self) -> int:
        return self.mcp_base_port

    @property
    def quality_port(self) -> int:
        return self.mcp_base_port + 1

    @property
    def governance_port(self) -> int:
        return self.mcp_base_port + 2

    @property
    def kg_url(self) -> str:
        return f"http://localhost:{self.kg_port}"

    @property
    def quality_url(self) -> str:
        return f"http://localhost:{self.quality_port}"

    @property
    def governance_url(self) -> str:
        return f"http://localhost:{self.governance_port}"
