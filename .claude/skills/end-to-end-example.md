---
name: end-to-end-example
description: End-to-end example of the full AVT workflow from research through merge
user_invocable: true
---

# End-to-End Example

**Task**: Add authentication to the API

1. **Research first** (for complex/unfamiliar tasks):
   ```
   Spawn a researcher teammate with system prompt from .claude/agents/researcher.md
   Task: "Research authentication approaches for our API. Compare JWT vs
   session-based auth, evaluate libraries, and recommend an approach."
   ```

2. **Query KG for context**:
   ```
   search_nodes("auth")
   get_entities_by_tier("vision")
   ```

3. **Design architecture** (for tasks requiring architectural decisions):
   ```
   Spawn an architect teammate with system prompt from .claude/agents/architect.md
   Task: "Design the authentication architecture for our API. Reference
   the research brief in .avt/research-briefs/. Produce task briefs for workers."
   ```
   The architect submits each decision with intent, expected_outcome, and vision_references. Governance reviews each decision. The architect produces task briefs in `.avt/task-briefs/`.

4. **Create tasks and spawn workers**:
   ```
   Lead creates tasks via TaskCreate for each task brief
   -> PostToolUse hook creates governance pairs -> holistic review runs
   -> Tasks unblock after approval
   Spawn worker teammates with system prompt from .claude/agents/worker.md
   Workers self-claim available tasks from the shared task list
   ```

5. **Worker completes and runs gates**: Worker calls `check_all_gates()` before completion. TaskCompleted hook verifies governance status.

6. **Review work**:
   ```
   Spawn a quality-reviewer teammate with system prompt from
   .claude/agents/quality-reviewer.md
   Task: "Review the diff for task 001-add-auth"
   ```

7. **Address findings**: If findings exist, message the worker teammate directly for resolution

8. **Curate memory**:
   ```
   Spawn a kg-librarian teammate with system prompt from
   .claude/agents/kg-librarian.md
   Task: "Curate the knowledge graph after task 001-add-auth"
   ```

9. **Merge and checkpoint**:
   ```bash
   git merge task/001-add-auth
   git tag checkpoint-001
   ```
