"""Singleton SurrealDB connection manager.

Provides both async and sync connection access to a single SurrealDB
embedded instance at .avt/avt.db. The sync interface is for hook scripts
that have a ~1ms budget and cannot run an event loop.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Optional

from surrealdb import AsyncSurreal, Surreal

_PROJECT_DIR = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
_DB_DIR = Path(_PROJECT_DIR) / ".avt"
_DB_PATH = _DB_DIR / "avt.db"

_NAMESPACE = "avt"
_DATABASE = "main"

_async_instance: Optional[AsyncSurreal] = None
_sync_instance: Optional[Surreal] = None
_schema_applied = False


def _get_db_url() -> str:
    """Build the surrealkv:// URL for the embedded database."""
    _DB_DIR.mkdir(parents=True, exist_ok=True)
    return f"surrealkv://{_DB_PATH}"


async def get_connection() -> AsyncSurreal:
    """Get or create the async SurrealDB connection (for MCP servers, gateway).

    Returns a connected AsyncSurreal instance using the avt namespace/database.
    The connection is cached as a singleton.
    """
    global _async_instance, _schema_applied
    if _async_instance is None:
        _async_instance = AsyncSurreal(_get_db_url())
        await _async_instance.connect()
        await _async_instance.use(_NAMESPACE, _DATABASE)
        if not _schema_applied:
            from .schema import apply_schema
            await apply_schema(_async_instance)
            _schema_applied = True
    return _async_instance


def get_sync_connection() -> Surreal:
    """Get or create the sync SurrealDB connection (for hook scripts).

    Returns a connected Surreal instance. Pre-warmed on first call
    and cached for subsequent calls.
    """
    global _sync_instance, _schema_applied
    if _sync_instance is None:
        _sync_instance = Surreal(_get_db_url())
        _sync_instance.connect()
        _sync_instance.use(_NAMESPACE, _DATABASE)
        if not _schema_applied:
            from .schema import apply_schema_sync
            apply_schema_sync(_sync_instance)
            _schema_applied = True
    return _sync_instance


async def close_connection() -> None:
    """Close all open connections. Used in tests and shutdown."""
    global _async_instance, _sync_instance, _schema_applied
    if _async_instance is not None:
        try:
            await _async_instance.close()
        except Exception:
            pass
        _async_instance = None
    if _sync_instance is not None:
        try:
            _sync_instance.close()
        except Exception:
            pass
        _sync_instance = None
    _schema_applied = False


def reset_for_testing(project_dir: Optional[str] = None) -> None:
    """Reset module state for test isolation.

    Args:
        project_dir: Override the project directory (and thus DB path).
    """
    global _async_instance, _sync_instance, _schema_applied, _PROJECT_DIR, _DB_DIR, _DB_PATH
    _async_instance = None
    _sync_instance = None
    _schema_applied = False
    if project_dir:
        _PROJECT_DIR = project_dir
        _DB_DIR = Path(_PROJECT_DIR) / ".avt"
        _DB_PATH = _DB_DIR / "avt.db"
