"""Document CRUD and ingestion endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth import require_auth
from ..app_state import state

router = APIRouter(prefix="/api/documents", tags=["documents"], dependencies=[Depends(require_auth)])


class CreateDocRequest(BaseModel):
    name: str
    content: str


@router.get("/{tier}")
async def list_docs(tier: str) -> dict:
    """List documents in a tier (vision or architecture)."""
    if tier not in ("vision", "architecture"):
        raise HTTPException(status_code=400, detail="Tier must be 'vision' or 'architecture'")
    docs = state.project_config.list_docs(tier)
    return {"docs": docs}


@router.post("/{tier}")
async def create_doc(tier: str, body: CreateDocRequest) -> dict:
    """Create a document in the specified tier."""
    if tier not in ("vision", "architecture"):
        raise HTTPException(status_code=400, detail="Tier must be 'vision' or 'architecture'")
    doc = state.project_config.create_doc(tier, body.name, body.content)
    return {"doc": doc}


@router.post("/{tier}/ingest")
async def ingest_docs(tier: str) -> dict:
    """Ingest documents from a tier into the Knowledge Graph."""
    if tier not in ("vision", "architecture"):
        raise HTTPException(status_code=400, detail="Tier must be 'vision' or 'architecture'")

    if not state.mcp or not state.mcp.is_connected:
        raise HTTPException(status_code=503, detail="MCP servers not connected")

    try:
        result = await state.mcp.call_tool("knowledge-graph", "ingest_documents", {"tier": tier})
        return {"result": result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/{tier}/format")
async def format_doc(tier: str, body: dict) -> dict:
    """Format document content using Claude CLI."""
    raw_content = body.get("rawContent", "")
    if len(raw_content) > 100_000:
        raise HTTPException(status_code=413, detail="Content exceeds 100KB limit")

    # Import here to avoid circular dependency
    from ..services.claude_cli import format_document
    try:
        formatted = await format_document(tier, raw_content)
        return {"success": True, "formattedContent": formatted}
    except Exception as exc:
        return {"success": False, "error": str(exc)}
