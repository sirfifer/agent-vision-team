# .avt/ -- Runtime Work Product Directory

**This directory is exclusively for artifacts produced by a deployed Agent Vision Team
installation.** Only AVT system agents (orchestrator, researcher, architect, worker,
quality-reviewer, kg-librarian, project-bootstrapper) operating within the AVT
governance framework write here.

If you are a Claude Code agent working on developing the AVT codebase itself, you are
NOT an AVT system agent. Your output (design docs, research, analysis, implementation
plans) belongs in `docs/`, not here.

## What belongs here

- `project-config.json` -- runtime project configuration
- `session-state.md` -- orchestrator session tracking
- `memory/` -- KG librarian curated institutional memory
- `research-briefs/` -- output from AVT researcher agents executing research prompts
- `research-prompts/` -- research prompt definitions for the researcher agent
- `task-briefs/` -- task briefs created by the orchestrator/architect for workers
- `jobs/` -- job tracking
- `debug/` -- debug captures from hook experiments

## What does NOT belong here

- Design documents about how to build AVT features
- Architecture specs, research, or analysis done as development work on this repo
- Implementation plans for new AVT capabilities
- Any output from a regular Claude Code session working on the codebase

Those go in `docs/design/`, `docs/analysis/`, or `docs/style/`.
