"""WebSocket connection manager with background polling."""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and broadcasts events."""

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []
        self._poller_task: asyncio.Task | None = None

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.append(ws)
        logger.info("WebSocket client connected (%d total)", len(self._connections))

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self._connections:
            self._connections.remove(ws)
        logger.info("WebSocket client disconnected (%d total)", len(self._connections))

    async def broadcast(self, event_type: str, data: dict) -> None:
        """Broadcast an event to all connected clients."""
        message = json.dumps({"type": event_type, "data": data})
        disconnected: list[WebSocket] = []

        for ws in self._connections:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)

        for ws in disconnected:
            self.disconnect(ws)

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
        """Poll governance/task state every 5 seconds and broadcast changes."""
        from ..app_state import state

        last_stats: dict | None = None
        last_tasks: list | None = None

        while True:
            try:
                await asyncio.sleep(5)

                if not self._connections:
                    continue

                if not state.mcp or not state.mcp.is_connected:
                    continue

                # Poll governance status
                try:
                    stats = await state.mcp.call_tool("governance", "get_governance_status")
                    if isinstance(stats, dict) and stats != last_stats:
                        last_stats = stats
                        await self.broadcast("governance_stats", stats)
                except Exception:
                    pass

                # Poll governed tasks
                try:
                    tasks_result = await state.mcp.call_tool("governance", "list_governed_tasks")
                    if isinstance(tasks_result, dict):
                        tasks = tasks_result.get("governed_tasks", [])
                        if tasks != last_tasks:
                            last_tasks = tasks
                            await self.broadcast("governed_tasks", {"tasks": tasks})
                except Exception:
                    pass

                # Poll job status updates
                from ..services.job_runner import get_job_runner
                runner = get_job_runner()
                for job in runner.list_jobs():
                    if job.status.value in ("queued", "running"):
                        await self.broadcast("job_status", job.model_dump())

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Poller error: %s", exc)
                await asyncio.sleep(5)


# Singleton
ws_manager = ConnectionManager()
