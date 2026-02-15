---
name: bootstrap-protocol
description: Bootstrap Protocol for onboarding existing codebases into AVT
user_invocable: true
---

# Bootstrap Protocol

The project-bootstrapper subagent onboards an existing, mature codebase into the AVT system by discovering governance artifacts that already exist implicitly in the code and documentation.

## When to Use the Bootstrapper

- **Onboarding an existing project**: The project has code and documentation but no AVT governance artifacts (no KG entities, no vision standards, no architecture docs)
- **Inherited codebase**: Someone is taking over a project and needs to understand its architecture, patterns, and conventions
- **Incremental discovery**: Some governance artifacts exist but there are gaps (e.g., vision standards defined but no architecture docs)

## How to Invoke

```
Task tool -> subagent_type: project-bootstrapper
prompt: "Bootstrap the project at /path/to/codebase"
```

The bootstrapper automatically:
1. Runs a cheap scale assessment (file counts, LOC, package boundaries) in under 5 seconds
2. Classifies the project into a scale tier (Small through Enterprise)
3. Builds a partition map using natural code boundaries
4. Spawns discovery sub-agents in waves (bounded parallelism, up to 15 concurrent)
5. Synthesizes findings into draft artifacts for human review

## What It Produces

| Artifact | Location | Purpose |
|----------|----------|---------|
| **Bootstrap report** | `.avt/bootstrap-report.md` | Primary human review artifact with APPROVE/REJECT/REVISE actions |
| **Vision standard drafts** | `docs/vision/*.md` | One doc per discovered vision standard |
| **Architecture docs** | `docs/architecture/` | Multi-level with Mermaid diagrams: overview, components, patterns, flows |
| **Style guide** | `docs/style/style-guide.md` | Discovered coding conventions |
| **Draft rules** | `.avt/bootstrap-rules-draft.json` | Discovered project rules |

## Human Review Workflow

1. **Read the bootstrap report** (`.avt/bootstrap-report.md`). It contains all discoveries organized by category with confidence levels and source citations.
2. **Review each artifact**: Mark as APPROVE, REJECT, or REVISE. Pay special attention to vision standards since they become immutable once ingested.
3. **After approval**, the bootstrapper (or orchestrator) runs:
   - `ingest_documents("docs/vision/", "vision")` for approved vision standards
   - `ingest_documents("docs/architecture/", "architecture")` for approved architecture docs
   - Merges approved rules from `.avt/bootstrap-rules-draft.json` into `.avt/project-config.json`
4. **Rejected items**: Delete the corresponding draft files
5. **Revised items**: Edit the draft files per feedback, then re-run ingestion

## Scale Handling

The bootstrapper adapts to any codebase size using wave-based bounded parallelism:

| Tier | Source LOC | Estimated Time | Agent Invocations |
|------|-----------|---------------|-------------------|
| Small | < 10K | ~5 min | Inline (no sub-agents) |
| Medium | 10K-100K | ~10 min | ~19 |
| Large | 100K-500K | ~15 min | ~66 |
| Massive | 500K-2M | ~35 min | ~230 |
| Enterprise | 2M+ | ~41 min | ~300 |

## Integration with Other Agents

After bootstrap completes and artifacts are approved:
- **Workers** can now query KG for vision standards and architecture patterns
- **Quality reviewer** can check work against discovered standards
- **Governance reviewer** has vision standards to verify against
- **Architect** has existing patterns to build on
- **KG librarian** can curate the bootstrapped entities
