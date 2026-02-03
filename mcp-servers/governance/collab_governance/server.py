"""Governance MCP server — transactional review checkpoints for agent decisions."""

from typing import Optional

from fastmcp import FastMCP

from .kg_client import KGClient
from .models import (
    Alternative,
    Confidence,
    Decision,
    DecisionCategory,
    Verdict,
)
from .reviewer import GovernanceReviewer
from .store import GovernanceStore

mcp = FastMCP("Collab Intelligence Governance")

store = GovernanceStore()
kg = KGClient()
reviewer = GovernanceReviewer()


@mcp.tool()
def submit_decision(
    task_id: str,
    agent: str,
    category: str,
    summary: str,
    detail: str = "",
    components_affected: Optional[list[str]] = None,
    alternatives_considered: Optional[list[dict]] = None,
    confidence: str = "high",
) -> dict:
    """Submit a decision for governance review. Blocks until review completes.

    Called by agents before implementing any key decision. The tool stores the
    decision, loads vision/architecture standards from the KG, runs an AI review
    via claude --print, and returns the verdict.

    Args:
        task_id: The task this decision belongs to.
        agent: Name of the calling agent (e.g. "worker-1").
        category: One of: pattern_choice, component_design, api_design, deviation, scope_change.
        summary: Brief summary of the decision.
        detail: Detailed explanation of the decision.
        components_affected: List of component names affected by this decision.
        alternatives_considered: List of {option, reason_rejected} dicts.
        confidence: One of: high, medium, low.

    Returns:
        {verdict, decision_id, findings, guidance, standards_verified}
        verdict is one of: approved, blocked, needs_human_review
    """
    components = components_affected or []
    alts = [
        Alternative(option=a.get("option", ""), reason_rejected=a.get("reason_rejected", ""))
        for a in (alternatives_considered or [])
    ]

    decision = Decision(
        task_id=task_id,
        agent=agent,
        category=DecisionCategory(category),
        summary=summary,
        detail=detail,
        components_affected=components,
        alternatives_considered=alts,
        confidence=Confidence(confidence),
    )

    # 1. Store the decision
    decision = store.store_decision(decision)

    # 2. Load standards from KG
    vision_standards = kg.get_vision_standards()
    architecture = kg.get_architecture_entities()
    if components:
        architecture += kg.search_entities(components)

    # 3. Auto-flag deviations and scope changes for human review
    if decision.category in (DecisionCategory.DEVIATION, DecisionCategory.SCOPE_CHANGE):
        from .models import ReviewVerdict, Verdict

        review = ReviewVerdict(
            decision_id=decision.id,
            verdict=Verdict.NEEDS_HUMAN_REVIEW,
            findings=[],
            guidance=f"Category '{decision.category.value}' requires human review.",
            standards_verified=[s.get("name", "") for s in vision_standards],
        )
        store.store_review(review)
        kg.record_decision(decision.id, summary, "needs_human_review", agent)
        return {
            "verdict": "needs_human_review",
            "decision_id": decision.id,
            "findings": [],
            "guidance": review.guidance,
            "standards_verified": review.standards_verified,
        }

    # 4. Run AI review via claude --print
    review = reviewer.review_decision(decision, vision_standards, architecture)
    review.decision_id = decision.id

    # 5. Store the review
    store.store_review(review)

    # 6. Record in KG for institutional memory
    kg.record_decision(decision.id, summary, review.verdict.value, agent)

    # 7. Return the verdict
    return {
        "verdict": review.verdict.value,
        "decision_id": decision.id,
        "findings": [f.model_dump() for f in review.findings],
        "guidance": review.guidance,
        "standards_verified": review.standards_verified,
    }


@mcp.tool()
def submit_plan_for_review(
    task_id: str,
    agent: str,
    plan_summary: str,
    plan_content: str,
    components_affected: Optional[list[str]] = None,
) -> dict:
    """Submit a complete plan for governance review before presenting to human.

    Called before an agent presents a plan. Reviews the plan against all vision
    and architecture standards, checking all prior decisions for the task.

    Args:
        task_id: The task this plan belongs to.
        agent: Name of the calling agent.
        plan_summary: Brief summary of the plan.
        plan_content: Full plan content (markdown).
        components_affected: List of component names the plan touches.

    Returns:
        {verdict, review_id, findings, guidance, decisions_reviewed, standards_verified}
    """
    components = components_affected or []

    # Load all context
    decisions = store.get_decisions_for_task(task_id)
    prior_reviews = store.get_reviews_for_task(task_id)
    vision_standards = kg.get_vision_standards()
    architecture = kg.get_architecture_entities()
    if components:
        architecture += kg.search_entities(components)

    # Run full plan review
    review = reviewer.review_plan(
        task_id=task_id,
        plan_summary=plan_summary,
        plan_content=plan_content,
        decisions=decisions,
        reviews=prior_reviews,
        vision_standards=vision_standards,
        architecture=architecture,
    )

    # Store
    store.store_review(review)

    # Record in KG
    kg.record_decision(
        f"plan_{task_id}",
        f"Plan review for {task_id}: {plan_summary[:100]}",
        review.verdict.value,
        agent,
    )

    return {
        "verdict": review.verdict.value,
        "review_id": review.id,
        "findings": [f.model_dump() for f in review.findings],
        "guidance": review.guidance,
        "decisions_reviewed": len(decisions),
        "standards_verified": review.standards_verified,
    }


@mcp.tool()
def submit_completion_review(
    task_id: str,
    agent: str,
    summary_of_work: str,
    files_changed: Optional[list[str]] = None,
) -> dict:
    """Submit completed work for final governance check.

    Called when a worker finishes its task. Verifies all decisions were reviewed,
    no blocked decisions remain unresolved, and the work aligns with standards.

    Args:
        task_id: The task being completed.
        agent: Name of the completing agent.
        summary_of_work: Summary of what was done.
        files_changed: List of files that were modified.

    Returns:
        {verdict, review_id, unreviewed_decisions, findings, guidance}
    """
    changed = files_changed or []
    decisions = store.get_decisions_for_task(task_id)
    reviews = store.get_reviews_for_task(task_id)
    vision_standards = kg.get_vision_standards()

    # Check for unreviewed decisions
    reviewed_ids = {r.decision_id for r in reviews if r.decision_id}
    unreviewed = [d for d in decisions if d.id not in reviewed_ids]

    if unreviewed:
        from .models import ReviewVerdict, Verdict

        review = ReviewVerdict(
            plan_id=task_id,
            verdict=Verdict.BLOCKED,
            findings=[],
            guidance=f"{len(unreviewed)} decision(s) were never reviewed: "
            + ", ".join(d.summary[:50] for d in unreviewed),
            standards_verified=[],
        )
        store.store_review(review)
        return {
            "verdict": "blocked",
            "review_id": review.id,
            "unreviewed_decisions": [d.id for d in unreviewed],
            "findings": [],
            "guidance": review.guidance,
        }

    # Check for unresolved blocks
    if store.has_unresolved_blocks(task_id):
        from .models import ReviewVerdict, Verdict

        review = ReviewVerdict(
            plan_id=task_id,
            verdict=Verdict.BLOCKED,
            findings=[],
            guidance="There are unresolved blocked decisions for this task.",
            standards_verified=[],
        )
        store.store_review(review)
        return {
            "verdict": "blocked",
            "review_id": review.id,
            "unreviewed_decisions": [],
            "findings": [],
            "guidance": review.guidance,
        }

    # Run final AI review
    review = reviewer.review_completion(
        task_id=task_id,
        summary_of_work=summary_of_work,
        files_changed=changed,
        decisions=decisions,
        reviews=reviews,
        vision_standards=vision_standards,
    )
    store.store_review(review)

    return {
        "verdict": review.verdict.value,
        "review_id": review.id,
        "unreviewed_decisions": [],
        "findings": [f.model_dump() for f in review.findings],
        "guidance": review.guidance,
    }


@mcp.tool()
def get_decision_history(
    task_id: Optional[str] = None,
    agent: Optional[str] = None,
    verdict: Optional[str] = None,
) -> dict:
    """Get history of decisions and their review verdicts.

    Args:
        task_id: Filter by task ID.
        agent: Filter by agent name.
        verdict: Filter by verdict (approved, blocked, needs_human_review).

    Returns:
        {decisions: [{id, summary, verdict, timestamp, ...}]}
    """
    decisions = store.get_all_decisions(
        task_id=task_id, agent=agent, verdict=verdict
    )
    return {"decisions": decisions}


@mcp.tool()
def get_governance_status() -> dict:
    """Get current governance overview for the dashboard.

    Returns:
        {total_decisions, approved, blocked, needs_human_review, pending, recent_activity}
    """
    return store.get_status()


if __name__ == "__main__":
    mcp.run(transport="sse", port=3103)
