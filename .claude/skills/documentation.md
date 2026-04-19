---
name: documentation
description: Documentation Protocol for maintaining project documentation across all tiers when changes occur
user_invocable: true
---

# Documentation Protocol

This skill codifies the process of keeping project documentation accurate, complete, and in sync with code changes. It applies whenever a significant change, feature addition, or architectural evolution occurs.

## First-Class Documents

These documents are first-class citizens and must be reviewed for updates with every significant change:

| Document | Path | Purpose | Update Trigger |
|----------|------|---------|----------------|
| **Project Overview** | `docs/project-overview.md` | External-facing story of the project: architecture, capabilities, status, maturity | Any significant feature, milestone, or architectural change |
| **CLAUDE.md** | `CLAUDE.md` | Orchestrator instructions, MCP server config, protocols | New tools, workflows, configuration options, agent changes |
| **ARCHITECTURE.md** | `ARCHITECTURE.md` | Engineering-level architecture specification | Structural changes, new components, pattern changes |

## Documentation Tiers

### Tier 1: Always Update (every significant change)

1. **Project Overview** (`docs/project-overview.md`)
   - Update the `Last Updated` date
   - Update affected sections (architecture diagram, server descriptions, technology stack, current status, related docs)
   - Add new milestones to the "Current Status" section
   - Update test assertion counts if tests changed
   - This document communicates progress and maturity externally; it is used for articles, website updates, and stakeholder communication

2. **CLAUDE.md**
   - Update if new tools, configuration options, or workflows were added
   - Keep under 300 lines; move detailed protocols to skills

### Tier 2: Update When Affected

3. **Component READMEs** (e.g., `mcp-servers/*/README.md`, `shared/*/README.md`)
   - Update when the component's API, storage, configuration, or behavior changes
   - Include new modules in module tables

4. **Design Documents** (`docs/design/`)
   - Create a new design doc for significant architectural decisions
   - Update existing design docs if the design evolves

5. **Skills** (`.claude/skills/`)
   - Update if the protocol or workflow the skill documents has changed
   - Create new skills for new repeatable processes

### Tier 3: Update When Relevant

6. **Agent definitions** (`.claude/agents/`)
   - Update when agent responsibilities, tools, or workflows change

7. **Settings and configuration**
   - `.claude/settings.json`: new permissions, hooks, env vars
   - `.avt/project-config.json`: new project rules or settings

## Documentation Checklist

When completing a significant change, review this checklist:

```
[ ] Project Overview updated (docs/project-overview.md)
    [ ] Last Updated date
    [ ] Affected architecture/capability sections
    [ ] Current Status section (new milestone)
    [ ] Technology Stack (if new tech introduced)
    [ ] Related Documentation links
[ ] CLAUDE.md updated (if new config/tools/workflows)
[ ] Component READMEs updated (if component changed)
[ ] Design doc created/updated (if architectural decision)
[ ] Skills updated (if protocol changed)
[ ] Agent definitions updated (if agent roles changed)
```

## What Counts as "Significant"

Not every commit needs documentation updates. Use this guide:

**Always update docs for:**
- New features or capabilities
- New storage backends, APIs, or integrations
- Architectural decisions or pattern changes
- New agents, skills, or hooks
- Major bug fixes that change behavior
- New test suites or validation approaches

**Skip docs for:**
- Single-line bug fixes
- Code formatting or linting changes
- Internal refactoring with no behavior change
- Test-only changes (unless adding a new test suite)
- Dependency version bumps (unless they change behavior)

## Writing Style for Documentation

- Lead with what changed and why, not how
- Use tables for structured comparisons
- Include configuration examples (env vars, flags)
- Reference related docs with relative links
- Keep the project overview readable by someone outside the project
- No em dashes (project style rule)

## Integration with Other Agents

- **Quality Reviewer**: Can flag missing documentation as a finding
- **Project Steward**: Monitors documentation completeness
- **KG Librarian**: Syncs significant changes to archival memory files
- **Orchestrator**: Should invoke `/documentation` after completing significant work to verify documentation is complete
