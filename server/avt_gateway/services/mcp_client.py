"""MCP SSE client. Port of extension/src/services/McpClientService.ts."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import httpx

from ..config import config

logger = logging.getLogger(__name__)


class McpSseConnection:
    """A persistent MCP SSE connection to a single FastMCP server.

    Protocol: GET /sse -> session_id -> initialize -> tools/call via POST -> results via SSE
    """

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self._messages_url: str | None = None
        self._client = httpx.AsyncClient(timeout=30.0)
        self._pending: dict[int, asyncio.Future] = {}
        self._next_id = 1
        self._initialized = False
        self._reader_task: asyncio.Task | None = None

    async def connect(self) -> None:
        """Open SSE stream, read session ID, perform MCP handshake."""
        # Open the SSE stream
        self._response = await self._client.send(
            self._client.build_request("GET", f"{self.base_url}/sse"),
            stream=True,
        )
        if self._response.status_code != 200:
            raise ConnectionError(f"SSE connection failed (status {self._response.status_code})")

        # Create a single async iterator for the response stream.
        # Both session ID reading and event reading use this same iterator
        # to avoid the "content already streamed" error.
        self._stream_iter = self._response.aiter_text()

        # Read session ID from the first data line
        session_id = await self._read_session_id()
        self._messages_url = f"{self.base_url}/messages/?session_id={session_id}"
        logger.info("SSE session established: %s", session_id)

        # Start background SSE event reader (continues from the same iterator)
        self._reader_task = asyncio.create_task(self._event_reader())

        # MCP initialize handshake
        await self._initialize()

    async def disconnect(self) -> None:
        """Close the SSE connection."""
        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass
        if hasattr(self, "_response"):
            await self._response.aclose()
        await self._client.aclose()
        self._initialized = False
        # Reject pending requests
        for future in self._pending.values():
            if not future.done():
                future.set_exception(ConnectionError("Connection closed"))
        self._pending.clear()

    async def call_tool(self, name: str, args: dict[str, Any]) -> Any:
        """Call an MCP tool and return the result."""
        if not self._initialized:
            raise RuntimeError("Connection not initialized")

        result = await self._send_request("tools/call", {"name": name, "arguments": args})

        # Unwrap structured content
        if isinstance(result, dict):
            if "structuredContent" in result:
                sc = result["structuredContent"]
                if isinstance(sc, dict) and "result" in sc:
                    return sc["result"]
                return sc
            if "content" in result:
                for item in result.get("content", []):
                    if item.get("type") == "text" and item.get("text"):
                        try:
                            return json.loads(item["text"])
                        except (json.JSONDecodeError, TypeError):
                            return item["text"]
        return result

    # ── Internal ──────────────────────────────────────────────────────────

    async def _read_session_id(self) -> str:
        """Read lines from SSE until we find the session ID."""
        buffer = ""
        async for chunk in self._stream_iter:
            buffer += chunk
            for line in buffer.split("\n"):
                if line.startswith("data:"):
                    data = line[5:].strip()
                    if "session_id=" in data:
                        return data.split("session_id=")[1]
            # Keep only the last incomplete line
            if not buffer.endswith("\n"):
                parts = buffer.rsplit("\n", 1)
                buffer = parts[-1] if len(parts) > 1 else buffer
            else:
                buffer = ""
        raise ConnectionError("SSE stream ended before session ID")

    async def _event_reader(self) -> None:
        """Background task: read SSE events and resolve pending requests.

        Continues reading from the same stream iterator that _read_session_id used.
        """
        current_event_type = ""
        try:
            async for chunk in self._stream_iter:
                for line in chunk.split("\n"):
                    line = line.strip()
                    if line.startswith("event:"):
                        current_event_type = line[6:].strip()
                    elif line.startswith("data:") and current_event_type == "message":
                        data_str = line[5:].strip()
                        try:
                            data = json.loads(data_str)
                            self._handle_response(data)
                        except json.JSONDecodeError:
                            logger.warning("Failed to parse SSE data: %s", data_str[:100])
                        current_event_type = ""
        except (httpx.ReadError, asyncio.CancelledError):
            pass
        except Exception as exc:
            logger.error("SSE reader error: %s", exc)

    def _handle_response(self, data: dict) -> None:
        """Match a response to its pending request."""
        req_id = data.get("id")
        if req_id is not None and req_id in self._pending:
            future = self._pending.pop(req_id)
            if future.done():
                return
            if "error" in data:
                future.set_exception(RuntimeError(data["error"].get("message", str(data["error"]))))
            else:
                future.set_result(data.get("result"))

    async def _initialize(self) -> None:
        """Perform MCP initialize + initialized handshake."""
        await self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "avt-gateway", "version": "0.1.0"},
        })

        # Send initialized notification (no id, no response expected)
        await self._client.post(
            self._messages_url,
            json={"jsonrpc": "2.0", "method": "notifications/initialized"},
        )
        self._initialized = True
        logger.info("MCP session initialized")

    async def _send_request(self, method: str, params: dict) -> Any:
        """Send a JSON-RPC request and wait for its SSE response."""
        if not self._messages_url:
            raise RuntimeError("Not connected")

        req_id = self._next_id
        self._next_id += 1

        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()
        self._pending[req_id] = future

        try:
            resp = await self._client.post(
                self._messages_url,
                json={"jsonrpc": "2.0", "id": req_id, "method": method, "params": params},
            )
            if resp.status_code not in (200, 202):
                self._pending.pop(req_id, None)
                raise RuntimeError(f"POST failed with status {resp.status_code}")

            return await asyncio.wait_for(future, timeout=30.0)
        except asyncio.TimeoutError:
            self._pending.pop(req_id, None)
            raise TimeoutError(f"Request {method} timed out after 30s")
        except Exception:
            self._pending.pop(req_id, None)
            raise


class McpClientService:
    """Manages connections to all 3 MCP servers."""

    def __init__(self) -> None:
        self._kg: McpSseConnection | None = None
        self._quality: McpSseConnection | None = None
        self._governance: McpSseConnection | None = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> None:
        """Connect to all three MCP servers."""
        logger.info("Connecting to MCP servers...")

        servers = [
            ("Knowledge Graph", config.kg_url, "_kg"),
            ("Quality", config.quality_url, "_quality"),
            ("Governance", config.governance_url, "_governance"),
        ]

        failed: list[str] = []
        for name, url, attr in servers:
            try:
                conn = McpSseConnection(url)
                await conn.connect()
                setattr(self, attr, conn)
                logger.info("Connected to %s server", name)
            except Exception as exc:
                failed.append(f"{name} ({url})")
                logger.error("Failed to connect to %s: %s", name, exc)

        if len(failed) == len(servers):
            await self.disconnect()
            raise ConnectionError(f"No MCP servers available. Failed: {', '.join(failed)}")

        if failed:
            await self.disconnect()
            raise ConnectionError(f"Failed to connect to: {', '.join(failed)}. All servers must be running.")

        self._connected = True
        logger.info("Connected to all MCP servers.")

    async def disconnect(self) -> None:
        """Disconnect from all MCP servers."""
        for conn in (self._kg, self._quality, self._governance):
            if conn:
                try:
                    await conn.disconnect()
                except Exception:
                    pass
        self._kg = self._quality = self._governance = None
        self._connected = False

    async def call_tool(self, server: str, tool: str, args: dict[str, Any] | None = None) -> Any:
        """Call a tool on the specified MCP server."""
        conn_map = {
            "knowledge-graph": self._kg,
            "quality": self._quality,
            "governance": self._governance,
        }
        conn = conn_map.get(server)
        if not conn:
            raise RuntimeError(f"Not connected to {server}")

        logger.debug("Calling %s/%s with %s", server, tool, json.dumps(args or {}))
        result = await conn.call_tool(tool, args or {})
        logger.debug("Result from %s/%s: %s", server, tool, str(result)[:200])
        return result
