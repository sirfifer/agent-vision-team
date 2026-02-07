"""FastAPI application for the AVT Gateway."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .auth import require_auth
from .config import config
from .ws.manager import ws_manager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    logger.info("AVT Gateway starting on %s:%d", config.host, config.port)
    logger.info("Project directory: %s", config.project_dir)
    logger.info("API key: %s", config.api_key)

    # Start the WebSocket background poller
    ws_manager.start_poller()

    yield

    # Shutdown
    ws_manager.stop_poller()

    from .app_state import state
    if state.mcp:
        await state.mcp.disconnect()

    logger.info("AVT Gateway stopped")


app = FastAPI(
    title="AVT Gateway",
    description="HTTP/WebSocket API for the Agent Vision Team system",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
from .routers.health import router as health_router
from .routers.dashboard import router as dashboard_router
from .routers.config_router import router as config_router
from .routers.documents import router as documents_router
from .routers.governance import router as governance_router
from .routers.quality import router as quality_router
from .routers.research import router as research_router
from .routers.jobs import router as jobs_router

app.include_router(health_router)
app.include_router(dashboard_router)
app.include_router(config_router)
app.include_router(documents_router)
app.include_router(governance_router)
app.include_router(quality_router)
app.include_router(research_router)
app.include_router(jobs_router)


@app.websocket("/api/ws")
async def websocket_endpoint(ws: WebSocket, token: str | None = None):
    """WebSocket endpoint for real-time dashboard updates.

    Authentication via query param: ws://host/api/ws?token=<api-key>
    """
    if token != config.api_key:
        await ws.close(code=4001, reason="Unauthorized")
        return

    await ws_manager.connect(ws)
    try:
        while True:
            # Keep connection alive; we don't expect client messages
            # but we need to read to detect disconnects
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)
    except Exception:
        ws_manager.disconnect(ws)
