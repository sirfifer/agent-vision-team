"""Dashboard data endpoint: aggregates state from all sources."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..app_state import ProjectState
from ..auth import require_auth
from ..deps import get_project_state

router = APIRouter(tags=["dashboard"], dependencies=[Depends(require_auth)])


@router.get("/dashboard")
async def get_dashboard(state: ProjectState = Depends(get_project_state)) -> dict:
    """Get full dashboard state (equivalent of the 'update' message in VS Code)."""
    pc = state.project_config
    fs = state.file_service

    # Base data always available from filesystem
    data: dict = {
        "connectionStatus": "connected" if (state.mcp and state.mcp.is_connected) else "disconnected",
        "serverPorts": {
            "kg": state.mcp_ports[0],
            "quality": state.mcp_ports[1],
            "governance": state.mcp_ports[2],
        },
        "agents": fs.detect_agents(),
        "visionStandards": [],
        "architecturalElements": [],
        "activities": [],
        "tasks": fs.count_tasks(),
        "sessionPhase": fs.read_session_state().get("phase", "inactive"),
        "governedTasks": [],
        "governanceStats": {
            "totalDecisions": 0,
            "approved": 0,
            "blocked": 0,
            "pending": 0,
            "pendingReviews": 0,
            "totalGovernedTasks": 0,
            "needsHumanReview": 0,
        },
        "setupReadiness": pc.get_readiness(),
        "projectConfig": pc.load(),
        "visionDocs": pc.list_docs("vision"),
        "architectureDocs": pc.list_docs("architecture"),
        "researchPrompts": pc.list_research_prompts(),
        "researchBriefs": pc.list_research_briefs(),
        "sessionState": fs.read_session_state(),
        "hookGovernanceStatus": fs.read_hook_governance_status(),
    }

    # If MCP servers are connected, fetch live data
    if state.mcp and state.mcp.is_connected:
        try:
            # KG: vision standards
            vision = await state.mcp.call_tool("knowledge-graph", "get_entities_by_tier", {"tier": "vision"})
            if isinstance(vision, dict):
                data["visionStandards"] = vision.get("entities", [])
            elif isinstance(vision, list):
                data["visionStandards"] = vision
        except Exception:
            pass

        try:
            # KG: architectural elements
            arch = await state.mcp.call_tool("knowledge-graph", "get_entities_by_tier", {"tier": "architecture"})
            if isinstance(arch, dict):
                data["architecturalElements"] = arch.get("entities", [])
            elif isinstance(arch, list):
                data["architecturalElements"] = arch
        except Exception:
            pass

        try:
            # Governance: stats
            status = await state.mcp.call_tool("governance", "get_governance_status")
            if isinstance(status, dict):
                task_gov = status.get("task_governance", {})
                data["governanceStats"] = {
                    "totalDecisions": status.get("total_decisions", 0),
                    "approved": status.get("approved", 0),
                    "blocked": status.get("blocked", 0),
                    "pending": status.get("pending", 0),
                    "pendingReviews": task_gov.get("pending_reviews", status.get("pending_reviews", 0)),
                    "totalGovernedTasks": task_gov.get("total_governed_tasks", status.get("total_governed_tasks", 0)),
                    "needsHumanReview": status.get("needs_human_review", 0),
                }
        except Exception:
            pass

        try:
            # Governance: governed tasks
            tasks = await state.mcp.call_tool("governance", "list_governed_tasks")
            if isinstance(tasks, dict):
                data["governedTasks"] = tasks.get("governed_tasks", [])
        except Exception:
            pass

        try:
            # Governance: decision history
            history = await state.mcp.call_tool("governance", "get_decision_history")
            if isinstance(history, dict):
                data["decisionHistory"] = history.get("decisions", [])
        except Exception:
            pass

        try:
            # Quality: findings
            findings = await state.mcp.call_tool("quality", "get_all_findings")
            if isinstance(findings, dict):
                data["findings"] = findings.get("findings", [])
        except Exception:
            pass

        try:
            # Quality: gate results
            gates = await state.mcp.call_tool("quality", "check_all_gates")
            if isinstance(gates, dict):
                data["qualityGateResults"] = gates
        except Exception:
            pass

    # Job summary for the status bar
    try:
        runner = state.get_job_runner()
        all_jobs = runner.list_jobs()
        data["jobSummary"] = {
            "running": sum(1 for j in all_jobs if j.status.value == "running"),
            "queued": sum(1 for j in all_jobs if j.status.value == "queued"),
            "total": len(all_jobs),
        }
    except Exception:
        data["jobSummary"] = {"running": 0, "queued": 0, "total": 0}

    return data


@router.post("/mcp/connect")
async def connect_mcp(state: ProjectState = Depends(get_project_state)) -> dict:
    """Connect (or reconnect) to MCP servers and return full dashboard data."""
    if state.mcp and state.mcp.is_connected:
        # Already connected; return fresh dashboard data
        return await get_dashboard(state)

    # Disconnect stale client if any
    await state.disconnect_mcp()

    try:
        await state.connect_mcp()
        # Return full dashboard data so the UI updates immediately
        return await get_dashboard(state)
    except ConnectionError as exc:
        state.mcp = None
        raise HTTPException(status_code=503, detail=str(exc))


@router.post("/refresh")
async def refresh(state: ProjectState = Depends(get_project_state)) -> dict:
    """Refresh dashboard data from MCP servers."""
    if not state.mcp or not state.mcp.is_connected:
        raise HTTPException(status_code=503, detail="MCP servers not connected")

    # Just return fresh dashboard data
    return await get_dashboard(state)
