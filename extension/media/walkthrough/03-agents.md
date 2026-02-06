## The Agent Team

| Agent | Role | What It Does |
|-------|------|-------------|
| **Orchestrator** | Coordinator | Decomposes complex tasks, spawns workers, enforces quality review, manages the governance hierarchy |
| **Worker** | Implementer | Executes scoped task briefs, submits decisions to governance before implementing key choices |
| **Quality Reviewer** | Reviewer | Evaluates diffs through vision alignment, architectural conformance, and quality compliance |
| **KG Librarian** | Curator | Consolidates observations, promotes recurring solutions to patterns, removes stale entries |
| **Governance Reviewer** | Gatekeeper | AI-powered review of decisions and plans against vision and architecture standards |
| **Researcher** | Investigator | Gathers intelligence for architectural decisions, monitors external dependencies for changes |
| **Project Steward** | Maintainer | Ensures naming conventions, folder organization, documentation completeness, and project hygiene |

### How they interact

```
         Orchestrator
        /     |      \
   Worker  Researcher  KG Librarian
      |                    |
Quality Reviewer    Project Steward
      |
Governance Reviewer
```

The Orchestrator coordinates all agents. Workers implement,
reviewers validate, and the librarian maintains memory.
Agent definitions live in `.claude/agents/`.
