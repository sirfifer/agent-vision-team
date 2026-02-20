---
globs:
  - ".avt/**"
  - ".avt/*"
---

# .avt/ is a Runtime-Only Directory

The `.avt/` directory is exclusively for artifacts produced by a **deployed Agent Vision Team installation**. Only AVT system agents (orchestrator, researcher, architect, worker, quality-reviewer, kg-librarian, project-bootstrapper) operating within the AVT governance framework write here.

**You are NOT an AVT system agent.** You are a Claude Code agent working on developing the AVT codebase. Your output belongs in `docs/`, not `.avt/`.

## Where your work goes instead

- Design documents, research, architecture specs: `docs/design/`
- Analysis, experiments, investigations: `docs/analysis/`
- Style guides, format specs, templates: `docs/style/`
- Implementation code: the appropriate source directory

## Never write to these directories

- `.avt/research-briefs/` -- only AVT researcher agents write here
- `.avt/research-prompts/` -- only AVT researcher agents consume these
- `.avt/task-briefs/` -- only AVT orchestrator/architect agents write here
- `.avt/memory/` -- only the AVT KG librarian writes here
