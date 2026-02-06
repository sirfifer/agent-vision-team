# Project Overview Maintenance

You are updating the project overview document at `docs/project-overview.md`. This document serves as the primary external communication artifact for the Collaborative Intelligence System project — used for websites, slide decks, visualizations, and showcasing the project to stakeholders.

## Your Task

Regenerate `docs/project-overview.md` by analyzing the current state of the entire project. The document must:

1. **Start with the vision** — Lead with COLLABORATIVE_INTELLIGENCE_VISION.md content (principles, philosophy, the team metaphor)
2. **Digest the entire project** — Reflect the actual current state, not outdated information
3. **Be externally focused** — Written for communication, not internal development notes
4. **Be maintainable** — Each regeneration should produce a consistent, high-quality document

## Information Sources to Analyze

### Required Reading
1. `COLLABORATIVE_INTELLIGENCE_VISION.md` — The foundational vision document
2. `ARCHITECTURE.md` — Technical architecture details
3. `CLAUDE.md` — Orchestrator instructions and protocols
4. `.claude/agents/*.md` — All custom subagent definitions
5. `.claude/settings.json` — MCP server and hook configuration

### Current State Assessment
6. `mcp-servers/*/` — Check each server's actual implementation status:
   - `mcp-servers/knowledge-graph/` — KG server capabilities
   - `mcp-servers/quality/` — Quality server capabilities
   - `mcp-servers/governance/` — Governance server capabilities
7. `extension/` — VS Code extension features and status
8. Recent git commits — What's been added/changed recently

### Supporting Context
9. `docs/reports/` — Any intelligence reports that affect the project
10. `.avt/` — Current collaboration workspace state
11. `DOGFOOD-CHECKLIST.md` — Testing/validation status (if exists)

## Document Structure Requirements

The regenerated `docs/project-overview.md` must include these sections in order:

```markdown
# Collaborative Intelligence System

> [Compelling one-line description]

**Last Updated**: [Today's date]

---

## The Vision
[From COLLABORATIVE_INTELLIGENCE_VISION.md — principles, philosophy, team metaphor]

## Architecture at a Glance
[ASCII diagram + component summary]

## Key Components
### 1. Three-Tier Governance Hierarchy
### 2. Three MCP Servers
### 3. Four Custom Subagents
### 4. VS Code Extension

## How It Works
[Task execution flow, three-lens review, transactional governance]

## Technology Stack
[Table of technologies and rationale]

## What Makes This Different
[Platform-native philosophy, earned trust, enabling role]

## Current Status
### Completed
### In Progress
### Planned

## File Structure
[Current project layout]

## Getting Started
[Prerequisites and startup instructions]

## Learn More
[Links to detailed docs]
```

## Quality Standards

1. **Accuracy** — Every capability mentioned must exist in the codebase
2. **Currency** — Status sections must reflect actual current state
3. **Clarity** — Written for someone unfamiliar with the project
4. **Consistency** — Terminology must match the vision document
5. **Completeness** — Cover all major features without overwhelming detail

## Output

After analyzing the project, write the complete updated `docs/project-overview.md` document.

Include a brief summary at the end of your response noting:
- What changed from the previous version (if you can determine this)
- Any inconsistencies discovered between docs and implementation
- Suggestions for project improvements discovered during analysis
