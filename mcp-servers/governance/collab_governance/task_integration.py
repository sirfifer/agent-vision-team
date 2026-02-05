"""Task integration — direct manipulation of Claude Code Task system files.

This module provides atomic operations on Claude Code's task files to enable
governance-gated task execution. Tasks are stored as JSON files in ~/.claude/tasks/.

Key principle: Implementation tasks are ALWAYS created with a governance review
blocker already in place. This ensures no race condition where a task could be
picked up before governance review.
"""

import json
import os
import time
import fcntl
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field, asdict
import uuid


def _get_task_dir() -> Path:
    """Get the task directory based on CLAUDE_CODE_TASK_LIST_ID or default."""
    task_list_id = os.environ.get("CLAUDE_CODE_TASK_LIST_ID", "default")
    task_dir = Path.home() / ".claude" / "tasks" / task_list_id
    task_dir.mkdir(parents=True, exist_ok=True)
    return task_dir


def _generate_task_id() -> str:
    """Generate a unique task ID."""
    return uuid.uuid4().hex[:8]


@dataclass
class Task:
    """Represents a Claude Code Task."""
    id: str
    subject: str
    description: str = ""
    status: str = "pending"  # pending, in_progress, completed
    owner: Optional[str] = None
    activeForm: str = ""
    blockedBy: list[str] = field(default_factory=list)
    blocks: list[str] = field(default_factory=list)
    createdAt: float = field(default_factory=time.time)
    updatedAt: float = field(default_factory=time.time)

    # Governance-specific metadata (stored in task but not part of Claude schema)
    governance_metadata: dict = field(default_factory=dict)

    def to_claude_dict(self) -> dict:
        """Convert to Claude Code's task JSON format."""
        return {
            "id": self.id,
            "subject": self.subject,
            "description": self.description,
            "status": self.status,
            "owner": self.owner,
            "activeForm": self.activeForm or f"Working on {self.subject}",
            "blockedBy": self.blockedBy,
            "blocks": self.blocks,
            "createdAt": self.createdAt,
            "updatedAt": self.updatedAt,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        """Create a Task from a dictionary."""
        return cls(
            id=data.get("id", _generate_task_id()),
            subject=data.get("subject", ""),
            description=data.get("description", ""),
            status=data.get("status", "pending"),
            owner=data.get("owner"),
            activeForm=data.get("activeForm", ""),
            blockedBy=data.get("blockedBy", []),
            blocks=data.get("blocks", []),
            createdAt=data.get("createdAt", time.time()),
            updatedAt=data.get("updatedAt", time.time()),
            governance_metadata=data.get("governance_metadata", {}),
        )


class TaskFileManager:
    """Manages Claude Code task files with atomic operations."""

    def __init__(self, task_dir: Optional[Path] = None):
        self.task_dir = task_dir or _get_task_dir()
        self.task_dir.mkdir(parents=True, exist_ok=True)

    def _task_path(self, task_id: str) -> Path:
        """Get the path for a task file."""
        return self.task_dir / f"{task_id}.json"

    def _lock_path(self, task_id: str) -> Path:
        """Get the path for a task's lock file."""
        return self.task_dir / f".{task_id}.lock"

    def create_task(self, task: Task) -> Task:
        """Create a new task file atomically."""
        task_path = self._task_path(task.id)
        lock_path = self._lock_path(task.id)

        # Use file locking for atomicity
        with open(lock_path, "w") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                # Write task file
                with open(task_path, "w") as f:
                    json.dump(task.to_claude_dict(), f, indent=2)
                return task
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def read_task(self, task_id: str) -> Optional[Task]:
        """Read a task from file."""
        task_path = self._task_path(task_id)
        if not task_path.exists():
            return None

        with open(task_path, "r") as f:
            data = json.load(f)
            return Task.from_dict(data)

    def update_task(self, task: Task) -> Task:
        """Update an existing task atomically."""
        task.updatedAt = time.time()
        task_path = self._task_path(task.id)
        lock_path = self._lock_path(task.id)

        with open(lock_path, "w") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                with open(task_path, "w") as f:
                    json.dump(task.to_claude_dict(), f, indent=2)
                return task
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def add_blocker(self, task_id: str, blocker_id: str) -> Optional[Task]:
        """Add a blocker to a task atomically."""
        lock_path = self._lock_path(task_id)

        with open(lock_path, "w") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                task = self.read_task(task_id)
                if not task:
                    return None
                if blocker_id not in task.blockedBy:
                    task.blockedBy.append(blocker_id)
                    task.updatedAt = time.time()
                    with open(self._task_path(task_id), "w") as f:
                        json.dump(task.to_claude_dict(), f, indent=2)
                return task
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def remove_blocker(self, task_id: str, blocker_id: str) -> Optional[Task]:
        """Remove a blocker from a task atomically."""
        lock_path = self._lock_path(task_id)

        with open(lock_path, "w") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                task = self.read_task(task_id)
                if not task:
                    return None
                if blocker_id in task.blockedBy:
                    task.blockedBy.remove(blocker_id)
                    task.updatedAt = time.time()
                    with open(self._task_path(task_id), "w") as f:
                        json.dump(task.to_claude_dict(), f, indent=2)
                return task
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def complete_task(self, task_id: str) -> Optional[Task]:
        """Mark a task as completed."""
        task = self.read_task(task_id)
        if not task:
            return None
        task.status = "completed"
        return self.update_task(task)

    def list_tasks(self) -> list[Task]:
        """List all tasks in the task directory."""
        tasks = []
        for task_file in self.task_dir.glob("*.json"):
            if task_file.name.startswith("."):
                continue
            try:
                with open(task_file, "r") as f:
                    data = json.load(f)
                    tasks.append(Task.from_dict(data))
            except (json.JSONDecodeError, IOError):
                continue
        return tasks

    def get_pending_unblocked_tasks(self) -> list[Task]:
        """Get tasks that are pending and have no blockers (available for work)."""
        return [
            t for t in self.list_tasks()
            if t.status == "pending"
            and not t.blockedBy
            and not t.owner
        ]


def create_governed_task_pair(
    subject: str,
    description: str,
    context: str,
    review_type: str = "governance",
    task_dir: Optional[Path] = None,
) -> tuple[Task, Task]:
    """
    Create an implementation task with its governance review task atomically.

    The implementation task is ALWAYS created blocked by the review task.
    This is the core function that ensures no race condition.

    Args:
        subject: The implementation task subject
        description: The implementation task description
        context: Context for the governance review
        review_type: Type of review (governance, security, architecture, etc.)
        task_dir: Optional task directory override

    Returns:
        Tuple of (review_task, implementation_task)
    """
    manager = TaskFileManager(task_dir)

    # Generate IDs upfront
    review_id = f"review-{_generate_task_id()}"
    impl_id = f"impl-{_generate_task_id()}"

    # Create review task FIRST
    review_task = Task(
        id=review_id,
        subject=f"[{review_type.upper()}] Review: {subject}",
        description=f"Governance review required before execution.\n\nContext:\n{context}",
        activeForm=f"Reviewing {subject}",
        blocks=[impl_id],  # This review blocks the implementation
        governance_metadata={
            "review_type": review_type,
            "implementation_task_id": impl_id,
            "context": context,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    # Create implementation task BLOCKED BY review
    impl_task = Task(
        id=impl_id,
        subject=subject,
        description=description,
        activeForm=f"Working on {subject}",
        blockedBy=[review_id],  # Blocked from birth - cannot be picked up
        governance_metadata={
            "review_task_id": review_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    # Write both atomically (review first, then impl)
    # The order matters: review must exist before impl references it
    manager.create_task(review_task)
    manager.create_task(impl_task)

    return review_task, impl_task


def add_additional_review(
    task_id: str,
    review_type: str,
    context: str,
    task_dir: Optional[Path] = None,
) -> Optional[Task]:
    """
    Add an additional review blocker to an existing task.

    Use this when a governance review determines that additional review
    is needed (e.g., security review, architecture review).

    Args:
        task_id: The implementation task to add a blocker to
        review_type: Type of review (security, architecture, etc.)
        context: Context for the new review
        task_dir: Optional task directory override

    Returns:
        The new review task, or None if the implementation task doesn't exist
    """
    manager = TaskFileManager(task_dir)

    # Check implementation task exists
    impl_task = manager.read_task(task_id)
    if not impl_task:
        return None

    # Generate new review ID
    review_id = f"review-{review_type}-{_generate_task_id()}"

    # Create the new review task
    review_task = Task(
        id=review_id,
        subject=f"[{review_type.upper()}] Review: {impl_task.subject}",
        description=f"Additional {review_type} review required.\n\nContext:\n{context}",
        activeForm=f"Performing {review_type} review",
        blocks=[task_id],
        governance_metadata={
            "review_type": review_type,
            "implementation_task_id": task_id,
            "context": context,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    # Create review task
    manager.create_task(review_task)

    # Add blocker to implementation task
    manager.add_blocker(task_id, review_id)

    return review_task


def release_task(
    review_task_id: str,
    verdict: str,
    guidance: str = "",
    task_dir: Optional[Path] = None,
) -> Optional[Task]:
    """
    Complete a review task, releasing the blocked implementation task.

    This is called when governance review is complete. If approved,
    the implementation task becomes available for work.

    Args:
        review_task_id: The review task to complete
        verdict: The review verdict (approved, blocked, needs_human_review)
        guidance: Guidance text for the implementation agent
        task_dir: Optional task directory override

    Returns:
        The updated implementation task, or None if not found
    """
    manager = TaskFileManager(task_dir)

    # Get the review task
    review_task = manager.read_task(review_task_id)
    if not review_task:
        return None

    # Get the implementation task ID from metadata or blocks list
    impl_id = review_task.governance_metadata.get("implementation_task_id")
    if not impl_id and review_task.blocks:
        impl_id = review_task.blocks[0]

    if not impl_id:
        return None

    # Mark review task as completed
    review_task.status = "completed"
    review_task.description += f"\n\n---\nVerdict: {verdict}\nGuidance: {guidance}"
    manager.update_task(review_task)

    # Get implementation task
    impl_task = manager.read_task(impl_id)
    if not impl_task:
        return None

    # If approved, remove the blocker
    if verdict == "approved":
        manager.remove_blocker(impl_id, review_task_id)
        return manager.read_task(impl_id)
    else:
        # Keep blocked - add guidance to description
        impl_task.description += f"\n\n---\n[BLOCKED] {verdict}: {guidance}"
        return manager.update_task(impl_task)


def get_task_governance_status(
    task_id: str,
    task_dir: Optional[Path] = None,
) -> dict:
    """
    Get the governance status for a task.

    Returns information about what reviews are blocking the task
    and their current status.
    """
    manager = TaskFileManager(task_dir)

    task = manager.read_task(task_id)
    if not task:
        return {"error": "Task not found"}

    blockers = []
    for blocker_id in task.blockedBy:
        blocker = manager.read_task(blocker_id)
        if blocker:
            blockers.append({
                "id": blocker.id,
                "subject": blocker.subject,
                "status": blocker.status,
                "review_type": blocker.governance_metadata.get("review_type", "unknown"),
            })

    return {
        "task_id": task_id,
        "subject": task.subject,
        "status": task.status,
        "is_blocked": len(task.blockedBy) > 0,
        "blockers": blockers,
        "can_execute": task.status == "pending" and not task.blockedBy and not task.owner,
    }
