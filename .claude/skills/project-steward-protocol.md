---
name: project-steward-protocol
description: Project Hygiene Protocol for maintaining project organization and conventions
user_invocable: true
---

# Project Hygiene Protocol

The project-steward subagent maintains project organization, naming conventions, and completeness across the codebase.

## What the Steward Monitors

1. **Project-Level Files**: LICENSE, README, CONTRIBUTING, CHANGELOG, CODE_OF_CONDUCT, SECURITY
2. **Naming Conventions**: Consistent casing across files, directories, variables, and types
3. **Folder Organization**: Logical grouping, appropriate depth, no orphaned files
4. **Documentation Completeness**: README sections, API docs, configuration documentation
5. **Cruft Detection**: Unused files, duplicates, outdated configs, dead links
6. **Consistency**: Indentation, line endings, encoding, import ordering

## When to Use the Steward

- **Periodic reviews**: Weekly cruft detection, monthly naming audits, quarterly deep reviews
- **Before releases**: Ensure all project files are complete and up-to-date
- **After major refactoring**: Verify organization still makes sense
- **New project setup**: Establish conventions and create missing essential files

## Spawning the Steward

```
Task tool -> subagent_type: project-steward
prompt: "Perform a full project hygiene review" | "Check naming conventions in src/" | "Verify all essential project files exist"
```

## Steward Outputs

- **Review Reports**: Structured reports with findings categorized by priority
- **KG Entities**: Naming conventions and project structure patterns recorded for future reference
- **Direct Fixes**: Mechanical fixes (renaming, cruft removal) when non-controversial

## Integration with Other Agents

- **Before worker tasks**: Steward can verify project structure before major work begins
- **After kg-librarian**: Steward can review if memory files are properly organized
- **Quality gates**: Steward findings can be included in quality reviews
