"""Shared SurrealDB persistence layer for Agent Vision Team.

Usage:
    from avt_db import get_connection, get_sync_connection

    # Async (MCP servers, gateway)
    db = await get_connection()
    result = await db.query("SELECT * FROM entity WHERE protection_tier = 'vision'")

    # Sync (hook scripts)
    db = get_sync_connection()
    result = db.query("SELECT * FROM entity WHERE name = $name", {"name": "AuthService"})
"""

from .connection import get_connection, get_sync_connection, close_connection

__all__ = [
    "get_connection",
    "get_sync_connection",
    "close_connection",
]
