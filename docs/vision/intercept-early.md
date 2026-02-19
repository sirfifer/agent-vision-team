# Intercept Early, Redirect Early

## Statement

Every implementation task shall be governed from creation. Governance review must complete and approve a task before any implementation work begins on that task.

## Rationale

Catching misalignment after implementation is expensive; catching it before work begins is nearly free. The PostToolUse hook on TaskCreate automatically pairs every task with a governance review, adds a `blockedBy` relationship, and queues an async review. The PreToolUse gate on Write/Edit/Bash/Task prevents mutation during holistic review. This ensures no work proceeds without governance validation, enabling safe multi-agent parallelism.

## Source Evidence

- `scripts/hooks/governance-task-intercept.py`: PostToolUse hook implementation
- `scripts/hooks/holistic-review-gate.sh`: PreToolUse gate
- `CLAUDE.md`: Task Governance Protocol section
- `docs/project-overview.md`: Core principle description
