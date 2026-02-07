"""Shared application state (service singletons)."""

from __future__ import annotations

from .services.project_config import ProjectConfigService
from .services.file_service import FileService
from .services.mcp_client import McpClientService


class AppState:
    """Holds references to service singletons used across routers."""

    def __init__(self) -> None:
        self.project_config = ProjectConfigService()
        self.file_service = FileService()
        self.mcp: McpClientService | None = None


# Singleton
state = AppState()
