"""Governance MCP server — transactional review checkpoints for agent decisions."""

import os

# When run as main module, honor PROJECT_DIR for multi-project data isolation.
# Must happen before module-level instantiation of GovernanceStore/KGClient
# (which use relative paths like .avt/governance.db resolved from cwd).
if __name__ == "__main__" and os.environ.get("PROJECT_DIR"):
    os.chdir(os.environ["PROJECT_DIR"])

from typing import Optional

from fastmcp import FastMCP

from .kg_client import KGClient
from .models import (
    Alternative,
    Confidence,
    Decision,
    DecisionCategory,
    Finding,
    GovernedTaskRecord,
    ReviewType,
    TaskReviewRecord,
    TaskReviewStatus,
    Verdict,
)
from .reviewer import GovernanceReviewer
from .store import GovernanceStore
from .task_integration import (
    create_governed_task_pair,
    add_additional_review,
    release_task as release_task_file,
    get_task_governance_status as get_task_status_from_files,
)

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
        "strengths_summary": review.strengths_summary,
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
        "strengths_summary": review.strengths_summary,
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
        "strengths_summary": review.strengths_summary,
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
    status = store.get_status()
    # Add task governance stats
    task_stats = store.get_task_governance_stats()
    status["task_governance"] = task_stats
    return status


# =============================================================================
# Task Governance Tools — Atomic task creation with governance review blockers
# =============================================================================


@mcp.tool()
def create_governed_task(
    subject: str,
    description: str,
    context: str,
    review_type: str = "governance",
) -> dict:
    """Create an implementation task with its governance review blocker atomically.

    This is the PRIMARY way to create tasks that need governance review. The
    implementation task is ALWAYS created blocked by a review task - it can
    NEVER be picked up by an agent until governance approves it.

    This ensures deterministic governance: no race condition where a task
    could be executed before review.

    Args:
        subject: The implementation task subject (what needs to be done).
        description: Detailed description of the task.
        context: Context for the governance review (why, what constraints, etc.).
        review_type: Type of review - governance, security, architecture, memory, vision.

    Returns:
        {
            implementation_task_id: str,  # The task that will do the work
            review_task_id: str,          # The review task blocking it
            status: "pending_review",
            message: str
        }
    """
    from datetime import datetime, timezone

    # Validate review type
    try:
        r_type = ReviewType(review_type)
    except ValueError:
        r_type = ReviewType.GOVERNANCE

    # Create the task pair atomically via file system
    review_task, impl_task = create_governed_task_pair(
        subject=subject,
        description=description,
        context=context,
        review_type=review_type,
    )

    # Record in governance database for tracking
    governed_task = GovernedTaskRecord(
        implementation_task_id=impl_task.id,
        subject=subject,
        description=description,
        context=context,
        current_status="pending_review",
    )
    store.store_governed_task(governed_task)

    # Create the review record
    task_review = TaskReviewRecord(
        review_task_id=review_task.id,
        implementation_task_id=impl_task.id,
        review_type=r_type,
        status=TaskReviewStatus.PENDING,
        context=context,
    )
    store.store_task_review(task_review)

    # Queue the governance review (async - will be processed by reviewer)
    _queue_governance_review(task_review.id, impl_task.id, context)

    return {
        "implementation_task_id": impl_task.id,
        "review_task_id": review_task.id,
        "review_record_id": task_review.id,
        "status": "pending_review",
        "message": f"Task '{subject}' created and blocked pending {review_type} review.",
    }


@mcp.tool()
def add_review_blocker(
    implementation_task_id: str,
    review_type: str,
    context: str,
) -> dict:
    """Add an additional review blocker to an existing governed task.

    Use this when a governance review determines that additional review
    is needed (e.g., initial review passes but flags need for security review).

    The implementation task will remain blocked until ALL review blockers
    are completed.

    Args:
        implementation_task_id: The implementation task to add a blocker to.
        review_type: Type of review - security, architecture, memory, vision, custom.
        context: Context for the new review.

    Returns:
        {review_task_id, review_record_id, status, message}
    """
    # Validate review type
    try:
        r_type = ReviewType(review_type)
    except ValueError:
        r_type = ReviewType.CUSTOM

    # Add the review via file system
    review_task = add_additional_review(
        task_id=implementation_task_id,
        review_type=review_type,
        context=context,
    )

    if not review_task:
        return {
            "error": f"Implementation task '{implementation_task_id}' not found.",
            "status": "failed",
        }

    # Record in governance database
    task_review = TaskReviewRecord(
        review_task_id=review_task.id,
        implementation_task_id=implementation_task_id,
        review_type=r_type,
        status=TaskReviewStatus.PENDING,
        context=context,
    )
    store.store_task_review(task_review)

    # Queue the review
    _queue_governance_review(task_review.id, implementation_task_id, context)

    return {
        "review_task_id": review_task.id,
        "review_record_id": task_review.id,
        "status": "pending_review",
        "message": f"Added {review_type} review blocker to task '{implementation_task_id}'.",
    }


@mcp.tool()
def complete_task_review(
    review_task_id: str,
    verdict: str,
    guidance: str = "",
    findings: Optional[list[dict]] = None,
    standards_verified: Optional[list[str]] = None,
) -> dict:
    """Complete a governance review, potentially releasing the blocked task.

    Called when a governance review is complete. If the verdict is 'approved'
    AND this is the last blocking review, the implementation task becomes
    available for execution.

    Args:
        review_task_id: The review task ID (from create_governed_task).
        verdict: The review verdict - approved, blocked, needs_human_review.
        guidance: Guidance text for the implementation agent.
        findings: List of findings [{tier, severity, description, suggestion}].
        standards_verified: List of standard names that were verified.

    Returns:
        {
            verdict: str,
            implementation_task_id: str,
            task_released: bool,  # True if task is now available for work
            remaining_blockers: int,
            message: str
        }
    """
    from datetime import datetime, timezone

    # Get the review record
    task_review = store.get_task_review_by_review_task_id(review_task_id)
    if not task_review:
        return {
            "error": f"Review task '{review_task_id}' not found in governance records.",
            "status": "failed",
        }

    # Parse verdict
    try:
        v = Verdict(verdict)
    except ValueError:
        v = Verdict.NEEDS_HUMAN_REVIEW

    # Parse findings
    review_findings = []
    for f in (findings or []):
        review_findings.append(Finding(
            tier=f.get("tier", "quality"),
            severity=f.get("severity", "logic"),
            description=f.get("description", ""),
            suggestion=f.get("suggestion", ""),
            strengths=f.get("strengths", []),
            salvage_guidance=f.get("salvage_guidance", ""),
        ))

    # Update the review record
    task_review.status = TaskReviewStatus(verdict) if verdict in ["approved", "blocked"] else TaskReviewStatus.NEEDS_HUMAN_REVIEW
    task_review.verdict = v
    task_review.guidance = guidance
    task_review.findings = review_findings
    task_review.standards_verified = standards_verified or []
    task_review.completed_at = datetime.now(timezone.utc).isoformat()
    store.update_task_review(task_review)

    # Release the task in the file system
    impl_task = release_task_file(
        review_task_id=review_task_id,
        verdict=verdict,
        guidance=guidance,
    )

    if not impl_task:
        return {
            "error": "Failed to update task files.",
            "status": "failed",
        }

    # Check if task is now unblocked (no more blockers)
    task_status = get_task_status_from_files(task_review.implementation_task_id)
    task_released = task_status.get("can_execute", False)
    remaining_blockers = len(task_status.get("blockers", []))

    # Update governed task status if fully released
    if task_released and verdict == "approved":
        store.update_governed_task_status(
            task_review.implementation_task_id,
            "approved",
            datetime.now(timezone.utc).isoformat(),
        )
    elif verdict == "blocked":
        store.update_governed_task_status(
            task_review.implementation_task_id,
            "blocked",
            None,
        )

    # Record in KG for institutional memory
    kg.record_decision(
        f"task_review_{task_review.id}",
        f"Task review for {task_review.implementation_task_id}: {verdict}",
        verdict,
        "governance-reviewer",
    )

    return {
        "verdict": verdict,
        "implementation_task_id": task_review.implementation_task_id,
        "task_released": task_released,
        "remaining_blockers": remaining_blockers,
        "message": f"Review completed with verdict '{verdict}'. "
                   + ("Task is now available for execution." if task_released else f"{remaining_blockers} review(s) still pending."),
    }


@mcp.tool()
def get_task_review_status(
    implementation_task_id: str,
) -> dict:
    """Get the governance review status for a task.

    Returns information about what reviews are blocking the task,
    their current status, and whether the task can be executed.

    Args:
        implementation_task_id: The implementation task ID.

    Returns:
        {
            task_id, subject, status, is_blocked, can_execute,
            reviews: [{id, type, status, verdict, guidance}],
            message: str
        }
    """
    # Get from file system
    file_status = get_task_status_from_files(implementation_task_id)

    if "error" in file_status:
        return file_status

    # Get review records from database
    reviews = store.get_task_reviews(implementation_task_id)
    governed_task = store.get_governed_task(implementation_task_id)

    review_details = []
    for r in reviews:
        review_details.append({
            "id": r.id,
            "review_task_id": r.review_task_id,
            "type": r.review_type.value,
            "status": r.status.value,
            "verdict": r.verdict.value if r.verdict else None,
            "guidance": r.guidance,
            "created_at": r.created_at,
            "completed_at": r.completed_at,
        })

    return {
        "task_id": implementation_task_id,
        "subject": governed_task.subject if governed_task else file_status.get("subject", ""),
        "status": governed_task.current_status if governed_task else "unknown",
        "is_blocked": file_status.get("is_blocked", True),
        "can_execute": file_status.get("can_execute", False),
        "reviews": review_details,
        "blockers_from_files": file_status.get("blockers", []),
        "message": "Task is available for execution." if file_status.get("can_execute") else "Task is blocked pending review(s).",
    }


@mcp.tool()
def list_governed_tasks(
    status: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """List all governed tasks with their review details.

    Returns the full lifecycle of governed tasks, not just pending ones.
    Use this for dashboard views that need to show completed, approved,
    and blocked tasks alongside pending reviews.

    Args:
        status: Optional filter by status (pending_review, approved, blocked, completed).
        limit: Maximum number of tasks to return (default 50).

    Returns:
        {governed_tasks: [...], total: int}
    """
    tasks = store.get_all_governed_tasks(status=status, limit=limit)
    return {
        "governed_tasks": tasks,
        "total": len(tasks),
    }


@mcp.tool()
def get_pending_reviews() -> dict:
    """Get all pending governance reviews.

    Returns a list of reviews that need attention, ordered by creation time.

    Returns:
        {pending_reviews: [{id, review_task_id, implementation_task_id, type, context, created_at}]}
    """
    reviews = store.get_pending_task_reviews()

    return {
        "pending_reviews": [
            {
                "id": r.id,
                "review_task_id": r.review_task_id,
                "implementation_task_id": r.implementation_task_id,
                "type": r.review_type.value,
                "context": r.context[:200] + "..." if len(r.context) > 200 else r.context,
                "created_at": r.created_at,
            }
            for r in reviews
        ],
        "count": len(reviews),
    }


def _queue_governance_review(review_id: str, impl_task_id: str, context: str) -> None:
    """Queue a governance review for processing.

    This triggers the actual governance review process. For now, this is
    a placeholder that records the review request. The actual review can be:
    1. Triggered manually via complete_task_review()
    2. Processed by a governance-reviewer agent polling get_pending_reviews()
    3. Auto-processed by extending this function

    Args:
        review_id: The governance review record ID
        impl_task_id: The implementation task being reviewed
        context: Context for the review
    """
    # Record that a review was queued (for future async processing)
    # The review_id, impl_task_id, and context are already stored in the
    # task_reviews table, so this function serves as an extension point
    # for future async job queue integration.
    #
    # Future enhancement: Push to a job queue for async processing
    # queue.push({
    #     "review_id": review_id,
    #     "impl_task_id": impl_task_id,
    #     "context": context,
    #     "standards": kg.get_vision_standards(),
    #     "architecture": kg.get_architecture_entities(),
    # })
    pass  # Parameters documented in docstring, used in future async implementation


if __name__ == "__main__":
    mcp.run(transport="sse", port=int(os.environ.get("PORT", "3103")))
