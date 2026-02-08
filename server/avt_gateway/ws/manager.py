"""WebSocket connection manager with per-project background polling."""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections per project and broadcasts events."""

    def __init__(self) -> None:
        # project_id -> list of WebSocket connections
        self._connections: dict[str, list[WebSocket]] = {}
        # reverse lookup: ws -> project_id
        self._ws_project: dict[int, str] = {}
        self._poller_task: asyncio.Task | None = None

    async def connect(self, ws: WebSocket, project_id: str | None = None) -> None:
        await ws.accept()
        pid = project_id or "_default"
        if pid not in self._connections:
            self._connections[pid] = []
        self._connections[pid].append(ws)
        self._ws_project[id(ws)] = pid
        total = sum(len(conns) for conns in self._connections.values())
        logger.info("WebSocket client connected for project '%s' (%d total)", pid, total)

    def disconnect(self, ws: WebSocket) -> None:
        pid = self._ws_project.pop(id(ws), "_default")
        if pid in self._connections:
            if ws in self._connections[pid]:
                self._connections[pid].remove(ws)
            if not self._connections[pid]:
                del self._connections[pid]
        total = sum(len(conns) for conns in self._connections.values())
        logger.info("WebSocket client disconnected (%d total)", total)

    async def broadcast(self, event_type: str, data: dict, project_id: str | None = None) -> None:
        """Broadcast an event to all connected clients for a specific project."""
        pid = project_id or "_default"
        connections = self._connections.get(pid, [])
        if not connections:
            return

        message = json.dumps({"type": event_type, "data": data})
        disconnected: list[WebSocket] = []

        for ws in connections:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)

        for ws in disconnected:
            self.disconnect(ws)

    def _has_active_connections(self) -> bool:
        return any(len(conns) > 0 for conns in self._connections.values())

    def start_poller(self) -> None:
        """Start the background polling task."""
        if self._poller_task is None or self._poller_task.done():
            self._poller_task = asyncio.create_task(self._poll_loop())
            logger.info("Background poller started")

    def stop_poller(self) -> None:
        """Stop the background polling task."""
        if self._poller_task and not self._poller_task.done():
            self._poller_task.cancel()
            logger.info("Background poller stopped")

    async def _poll_loop(self) -> None:
        """Poll governance/task state every 5 seconds per project and broadcast changes."""
        from ..app_state import registry

        # Per-project last-known state for change detection
        last_stats: dict[str, dict] = {}
        last_tasks: dict[str, list] = {}

        while True:
            try:
                await asyncio.sleep(5)

                if not self._has_active_connections():
                    continue

                # Iterate over projects that have active WS connections
                for pid, connections in list(self._connections.items()):
                    if not connections:
                        continue

                    state = registry.get_or_none(pid)
                    if not state or not state.mcp or not state.mcp.is_connected:
                        continue

                    # Poll governance status
                    try:
                        stats = await state.mcp.call_tool("governance", "get_governance_status")
                        if isinstance(stats, dict) and stats != last_stats.get(pid):
                            last_stats[pid] = stats
                            await self.broadcast("governance_stats", stats, project_id=pid)
                    except Exception:
                        pass

                    # Poll governed tasks
                    try:
                        tasks_result = await state.mcp.call_tool("governance", "list_governed_tasks")
                        if isinstance(tasks_result, dict):
                            tasks = tasks_result.get("governed_tasks", [])
                            if tasks != last_tasks.get(pid):
                                last_tasks[pid] = tasks
                                await self.broadcast("governed_tasks", {"tasks": tasks}, project_id=pid)
                    except Exception:
                        pass

                    # Poll job status updates
                    try:
                        runner = state.get_job_runner()
                        for job in runner.list_jobs():
                            if job.status.value in ("queued", "running"):
                                await self.broadcast("job_status", job.model_dump(), project_id=pid)
                    except Exception:
                        pass

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Poller error: %s", exc)
                await asyncio.sleep(5)


# Singleton
ws_manager = ConnectionManager()
