"""Research prompts and briefs endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_auth
from ..app_state import ProjectState
from ..deps import get_project_state

router = APIRouter(tags=["research"], dependencies=[Depends(require_auth)])


# -- Research Prompts --

@router.get("/research-prompts")
async def list_research_prompts(state: ProjectState = Depends(get_project_state)) -> dict:
    """List all research prompts."""
    return {"prompts": state.project_config.list_research_prompts()}


@router.put("/research-prompts/{prompt_id}")
async def save_research_prompt(prompt_id: str, body: dict, state: ProjectState = Depends(get_project_state)) -> dict:
    """Create or update a research prompt."""
    body["id"] = prompt_id
    state.project_config.save_research_prompt(body)
    return {"success": True, "prompt": body}


@router.delete("/research-prompts/{prompt_id}")
async def delete_research_prompt(prompt_id: str, state: ProjectState = Depends(get_project_state)) -> dict:
    """Delete a research prompt."""
    deleted = state.project_config.delete_research_prompt(prompt_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Research prompt {prompt_id} not found")
    return {"success": True}


@router.post("/research-prompts/{prompt_id}/run")
async def run_research_prompt(prompt_id: str, state: ProjectState = Depends(get_project_state)) -> dict:
    """Run a research prompt (spawns Claude CLI in background)."""
    prompt = None
    for p in state.project_config.list_research_prompts():
        if p.get("id") == prompt_id:
            prompt = p
            break

    if not prompt:
        raise HTTPException(status_code=404, detail=f"Research prompt {prompt_id} not found")

    # Submit as a job via per-project job runner
    runner = state.get_job_runner()
    job = await runner.submit(
        prompt=f"Execute the research prompt in .avt/research-prompts/{prompt_id}.md",
        agent_type="researcher",
        model=prompt.get("modelHint", "sonnet"),
    )

    return {"success": True, "jobId": job.id}


# -- Research Briefs --

@router.get("/research-briefs")
async def list_research_briefs(state: ProjectState = Depends(get_project_state)) -> dict:
    """List all research briefs."""
    return {"briefs": state.project_config.list_research_briefs()}


@router.get("/research-briefs/{brief_path:path}")
async def get_research_brief(brief_path: str, state: ProjectState = Depends(get_project_state)) -> dict:
    """Read a research brief's content."""
    try:
        content = state.project_config.read_research_brief(brief_path)
        return {"briefPath": brief_path, "content": content}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Brief not found: {brief_path}")
