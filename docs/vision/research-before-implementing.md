# Research Before Implementing

## Statement

Unfamiliar domains shall require investigation by the researcher agent before workers begin implementation. Workers must not implement solutions in domains they have not researched.

## Rationale

Implementing without understanding leads to architectural mistakes that are expensive to fix. The researcher agent exists specifically to investigate unfamiliar APIs, libraries, patterns, and domains before workers build on them. Research briefs are stored in `.avt/research-briefs/` and become institutional memory. This prevents the common failure mode of an AI agent confidently implementing something incorrectly because it lacks domain knowledge.

## Source Evidence

- `CLAUDE.md`: "For unfamiliar domains, spawn the researcher first"
- `.claude/agents/researcher.md`: Full researcher agent definition
- `docs/project-overview.md`: Agent role descriptions
- `.avt/research-briefs/`: Research output directory
