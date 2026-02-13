"""FastAPI application for the AVT Gateway."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

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

    from .app_state import registry
    from .services.project_manager import get_project_manager

    mgr = get_project_manager()

    # Auto-register default project from PROJECT_DIR if no projects exist
    if not mgr.list_projects():
        try:
            project = mgr.add_project(str(config.project_dir))
            logger.info("Auto-registered default project: %s", project.id)
        except Exception as exc:
            logger.warning("Failed to auto-register default project: %s", exc)

    # Auto-start all registered projects
    for project in mgr.list_projects():
        try:
            mgr.start_project(project.id)
            state = registry.register(
                project.id,
                Path(project.path),
                (project.kg_port, project.quality_port, project.governance_port),
            )
            # Give MCP servers a moment to start, then try connecting
            await asyncio.sleep(2)
            try:
                await state.connect_mcp()
                logger.info("MCP connected for project '%s'", project.id)
            except ConnectionError as exc:
                logger.warning("MCP auto-connect failed for '%s': %s (will start degraded)", project.id, exc)
        except Exception as exc:
            logger.warning("Failed to start project '%s': %s", project.id, exc)

    # Start the WebSocket background poller
    ws_manager.start_poller()

    yield

    # Shutdown
    ws_manager.stop_poller()

    # Stop all MCP processes and disconnect clients
    await registry.disconnect_all()
    mgr.stop_all()

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

# -- Global routes (not per-project) --
from .routers.health import router as health_router
from .routers.projects import router as projects_router

app.include_router(health_router)
app.include_router(projects_router)

# -- Per-project routes (mounted under /api/projects/{project_id}) --
from .routers.dashboard import router as dashboard_router
from .routers.config_router import router as config_router
from .routers.documents import router as documents_router
from .routers.governance import router as governance_router
from .routers.quality import router as quality_router
from .routers.research import router as research_router
from .routers.jobs import router as jobs_router
from .routers.bootstrap import router as bootstrap_router

project_api = APIRouter(prefix="/api/projects/{project_id}")
project_api.include_router(dashboard_router)
project_api.include_router(config_router)
project_api.include_router(documents_router)
project_api.include_router(governance_router)
project_api.include_router(quality_router)
project_api.include_router(research_router)
project_api.include_router(jobs_router)
project_api.include_router(bootstrap_router)
app.include_router(project_api)


# Serve SPA static files (for local dev without Nginx)
_static_dir = Path(__file__).parent.parent / "static"
if _static_dir.is_dir():
    app.mount("/assets", StaticFiles(directory=_static_dir / "assets"), name="static-assets")

    @app.get("/", include_in_schema=False)
    async def serve_spa_root():
        """Serve index.html with injected API key for web transport."""
        html = (_static_dir / "index.html").read_text()
        # Inject the API key so the web transport can authenticate
        inject = f'<script>window.__AVT_API_KEY__="{config.api_key}";</script>'
        html = html.replace("</head>", f"{inject}</head>", 1)
        from fastapi.responses import HTMLResponse
        return HTMLResponse(html)

    @app.get("/{path:path}", include_in_schema=False)
    async def serve_spa_fallback(path: str):
        """SPA fallback: serve index.html for non-API routes."""
        file = _static_dir / path
        if file.is_file():
            return FileResponse(file)
        return FileResponse(_static_dir / "index.html")


@app.websocket("/api/ws")
async def websocket_endpoint(ws: WebSocket, token: str | None = None, project: str | None = None):
    """WebSocket endpoint for real-time dashboard updates.

    Authentication via query param: ws://host/api/ws?token=<api-key>&project=<id>
    """
    if token != config.api_key:
        await ws.close(code=4001, reason="Unauthorized")
        return

    await ws_manager.connect(ws, project_id=project)
    try:
        while True:
            # Keep connection alive; we don't expect client messages
            # but we need to read to detect disconnects
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)
    except Exception:
        ws_manager.disconnect(ws)
