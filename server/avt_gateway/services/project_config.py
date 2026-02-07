"""Project configuration service. Port of extension/src/services/ProjectConfigService.ts."""

from __future__ import annotations

import json
import re
from pathlib import Path

from ..config import config


# Default project configuration (mirrors extension/src/models/ProjectConfig.ts)
DEFAULT_QUALITY_CONFIG = {
    "testCommands": {
        "python": "uv run pytest",
        "typescript": "npm run test",
        "javascript": "npm run test",
    },
    "lintCommands": {
        "python": "uv run ruff check",
        "typescript": "npm run lint",
        "javascript": "npm run lint",
    },
    "buildCommands": {
        "typescript": "npm run build",
        "javascript": "npm run build",
    },
    "formatCommands": {
        "python": "uv run ruff format",
        "typescript": "npx prettier --write",
        "javascript": "npx prettier --write",
    },
}

DEFAULT_PROJECT_SETTINGS = {
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
}

DEFAULT_PROJECT_CONFIG = {
    "version": 1,
    "setupComplete": False,
    "languages": [],
    "metadata": {"isOpenSource": False},
    "settings": DEFAULT_PROJECT_SETTINGS,
    "quality": DEFAULT_QUALITY_CONFIG,
    "permissions": [],
    "ingestion": {
        "lastVisionIngest": None,
        "lastArchitectureIngest": None,
        "visionDocCount": 0,
        "architectureDocCount": 0,
    },
}


class ProjectConfigService:
    """Manages project configuration, documents, and research prompts."""

    def __init__(self, project_dir: Path | None = None) -> None:
        self.project_dir = project_dir or config.project_dir
        self.avt_root = self.project_dir / ".avt"
        self.docs_root = self.project_dir / "docs"
        self.config_path = self.avt_root / "project-config.json"
        self.claude_settings_path = self.project_dir / ".claude" / "settings.local.json"

    # ── Config ────────────────────────────────────────────────────────────

    def load(self) -> dict:
        """Load project configuration, merging with defaults for missing fields."""
        if not self.config_path.exists():
            return {**DEFAULT_PROJECT_CONFIG}

        try:
            raw = self.config_path.read_text()
            cfg = json.loads(raw)
            # Merge with defaults
            merged = {**DEFAULT_PROJECT_CONFIG, **cfg}
            merged["settings"] = {**DEFAULT_PROJECT_SETTINGS, **cfg.get("settings", {})}
            merged["quality"] = {**DEFAULT_QUALITY_CONFIG, **cfg.get("quality", {})}
            merged["ingestion"] = {**DEFAULT_PROJECT_CONFIG["ingestion"], **cfg.get("ingestion", {})}
            return merged
        except (json.JSONDecodeError, OSError):
            return {**DEFAULT_PROJECT_CONFIG}

    def save(self, cfg: dict) -> None:
        """Save project configuration with atomic write."""
        self.avt_root.mkdir(parents=True, exist_ok=True)
        tmp_path = self.config_path.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(cfg, indent=2))
        tmp_path.rename(self.config_path)

    # ── Setup readiness ───────────────────────────────────────────────────

    def get_readiness(self) -> dict:
        """Check setup readiness status."""
        vision_dir = self.docs_root / "vision"
        arch_dir = self.docs_root / "architecture"

        has_vision = self._has_docs(vision_dir)
        has_arch = self._has_docs(arch_dir)
        has_config = self.config_path.exists()

        cfg = self.load()
        has_ingest = cfg.get("ingestion", {}).get("lastVisionIngest") is not None

        vision_count = self._count_docs(vision_dir)
        arch_count = self._count_docs(arch_dir)

        return {
            "hasVisionDocs": has_vision,
            "hasArchitectureDocs": has_arch,
            "hasProjectConfig": has_config,
            "hasKgIngestion": has_ingest,
            "isComplete": has_vision and has_arch and has_config and has_ingest,
            "visionDocCount": vision_count,
            "architectureDocCount": arch_count,
        }

    # ── Documents ─────────────────────────────────────────────────────────

    def list_docs(self, tier: str) -> list[dict]:
        """List markdown documents in a tier folder."""
        folder = self.docs_root / tier
        if not folder.exists():
            return []

        docs = []
        for f in sorted(folder.iterdir()):
            if f.suffix == ".md" and f.name.lower() != "readme.md":
                docs.append({"name": f.name, "path": str(f.relative_to(self.project_dir))})
        return docs

    def create_doc(self, tier: str, name: str, content: str) -> dict:
        """Create a document in the specified tier folder."""
        folder = self.docs_root / tier
        folder.mkdir(parents=True, exist_ok=True)

        filename = self._sanitize_filename(name) + ".md"
        filepath = folder / filename
        filepath.write_text(content)
        return {"name": filename, "path": str(filepath.relative_to(self.project_dir))}

    # ── Permissions ───────────────────────────────────────────────────────

    def sync_permissions(self, permissions: list[str]) -> None:
        """Sync permissions to .claude/settings.local.json."""
        claude_dir = self.claude_settings_path.parent
        claude_dir.mkdir(parents=True, exist_ok=True)

        settings: dict = {}
        if self.claude_settings_path.exists():
            try:
                settings = json.loads(self.claude_settings_path.read_text())
            except (json.JSONDecodeError, OSError):
                pass

        settings["permissions"] = {"allow": permissions}

        tmp = self.claude_settings_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(settings, indent=2))
        tmp.rename(self.claude_settings_path)

    # ── Research prompts ──────────────────────────────────────────────────

    @property
    def _prompts_registry(self) -> Path:
        return self.avt_root / "research-prompts.json"

    @property
    def _prompts_dir(self) -> Path:
        return self.avt_root / "research-prompts"

    @property
    def _briefs_dir(self) -> Path:
        return self.avt_root / "research-briefs"

    def list_research_prompts(self) -> list[dict]:
        if not self._prompts_registry.exists():
            return []
        try:
            return json.loads(self._prompts_registry.read_text())
        except (json.JSONDecodeError, OSError):
            return []

    def save_research_prompt(self, prompt: dict) -> None:
        prompts = self.list_research_prompts()
        idx = next((i for i, p in enumerate(prompts) if p.get("id") == prompt.get("id")), -1)
        if idx >= 0:
            prompts[idx] = prompt
        else:
            prompts.append(prompt)

        self.avt_root.mkdir(parents=True, exist_ok=True)
        tmp = self._prompts_registry.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(prompts, indent=2))
        tmp.rename(self._prompts_registry)

    def delete_research_prompt(self, prompt_id: str) -> bool:
        prompts = self.list_research_prompts()
        filtered = [p for p in prompts if p.get("id") != prompt_id]
        if len(filtered) == len(prompts):
            return False

        tmp = self._prompts_registry.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(filtered, indent=2))
        tmp.rename(self._prompts_registry)

        # Remove prompt file
        prompt_file = self._prompts_dir / f"{prompt_id}.md"
        if prompt_file.exists():
            prompt_file.unlink()
        return True

    # ── Research briefs ───────────────────────────────────────────────────

    def list_research_briefs(self) -> list[dict]:
        if not self._briefs_dir.exists():
            return []

        briefs = []
        for f in sorted(self._briefs_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            if f.suffix == ".md" and f.name.lower() != "readme.md":
                stat = f.stat()
                briefs.append({
                    "name": f.name,
                    "path": str(f.relative_to(self.project_dir)),
                    "modifiedAt": str(stat.st_mtime),
                })
        return briefs

    def read_research_brief(self, brief_path: str) -> str:
        """Read a research brief file. Path is relative to project root."""
        full_path = self.project_dir / brief_path
        if not full_path.exists():
            raise FileNotFoundError(f"Brief not found: {brief_path}")
        return full_path.read_text()

    # ── Session state ─────────────────────────────────────────────────────

    def read_session_state(self) -> dict:
        """Read session state from .avt/session-state.md."""
        state_path = self.avt_root / "session-state.md"
        if not state_path.exists():
            return {"phase": "inactive"}

        content = state_path.read_text()
        # Parse simple key-value from markdown
        phase = "inactive"
        for line in content.splitlines():
            if line.startswith("## Phase:"):
                phase = line.split(":", 1)[1].strip().lower()
                break
        return {"phase": phase}

    # ── Helpers ────────────────────────────────────────────────────────────

    def _has_docs(self, folder: Path) -> bool:
        if not folder.exists():
            return False
        return any(
            f.suffix == ".md" and f.name.lower() != "readme.md"
            for f in folder.iterdir()
        )

    def _count_docs(self, folder: Path) -> int:
        if not folder.exists():
            return 0
        return sum(
            1 for f in folder.iterdir()
            if f.suffix == ".md" and f.name.lower() != "readme.md"
        )

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        return re.sub(r"^-|-$", "", re.sub(r"[^a-z0-9]+", "-", name.lower()))
