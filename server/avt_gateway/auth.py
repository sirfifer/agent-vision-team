"""API key authentication middleware for the AVT Gateway."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import config

_bearer = HTTPBearer(auto_error=False)


async def require_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> None:
    """Validate Bearer token against the configured API key.

    For WebSocket upgrades, the token can also be passed as a query param: ?token=<key>
    """
    # Check Bearer header first
    if credentials and credentials.credentials == config.api_key:
        return

    # Fall back to query param (for WebSocket connections)
    token = request.query_params.get("token")
    if token == config.api_key:
        return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API key",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def optional_auth_for_ws(
    token: str | None = Query(None),
) -> None:
    """WebSocket-specific auth via query param."""
    if token != config.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing token",
        )
