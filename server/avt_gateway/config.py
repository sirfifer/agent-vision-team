"""Environment-based configuration for the AVT Gateway."""

from __future__ import annotations

import os
import secrets
from pathlib import Path


class GatewayConfig:
    """Gateway configuration loaded from environment variables."""

    def __init__(self) -> None:
        self.project_dir = Path(os.environ.get("PROJECT_DIR", os.getcwd()))
        self.host = os.environ.get("AVT_GATEWAY_HOST", "0.0.0.0")
        self.port = int(os.environ.get("AVT_GATEWAY_PORT", "8080"))

        # MCP server ports
        self.kg_port = int(os.environ.get("AVT_KG_PORT", "3101"))
        self.quality_port = int(os.environ.get("AVT_QUALITY_PORT", "3102"))
        self.governance_port = int(os.environ.get("AVT_GOVERNANCE_PORT", "3103"))

        # Derived paths
        self.avt_root = self.project_dir / ".avt"
        self.docs_root = self.project_dir / "docs"
        self.claude_dir = self.project_dir / ".claude"

        # API key auth
        self.api_key = os.environ.get("AVT_API_KEY") or self._load_or_create_api_key()

        # CORS origins (comma-separated)
        origins = os.environ.get("AVT_CORS_ORIGINS", "")
        self.cors_origins: list[str] = [o.strip() for o in origins.split(",") if o.strip()] if origins else ["*"]

    @property
    def kg_url(self) -> str:
        return f"http://localhost:{self.kg_port}"

    @property
    def quality_url(self) -> str:
        return f"http://localhost:{self.quality_port}"

    @property
    def governance_url(self) -> str:
        return f"http://localhost:{self.governance_port}"

    def _load_or_create_api_key(self) -> str:
        """Load API key from .avt/api-key.txt or generate a new one."""
        key_path = self.avt_root / "api-key.txt"
        if key_path.exists():
            return key_path.read_text().strip()

        # Generate and persist a new key
        key = secrets.token_urlsafe(32)
        self.avt_root.mkdir(parents=True, exist_ok=True)
        key_path.write_text(key)
        return key


# Singleton
config = GatewayConfig()
