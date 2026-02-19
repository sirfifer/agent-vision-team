# Build Only What the Platform Cannot Do

## Statement

Custom infrastructure shall be limited to capabilities that Claude Code genuinely lacks. Every feature must first be evaluated against platform-native alternatives before building custom solutions.

## Rationale

Over-engineering and custom infrastructure introduce maintenance burden, increase complexity, and create divergence from the platform's evolution path. The project follows a strict "platform-native philosophy" where Claude Code's built-in capabilities (subagents, hooks, git worktrees, model routing, task system) are used directly rather than wrapped or replaced. Custom MCP servers exist only because Claude Code does not natively provide persistent knowledge graphs, deterministic quality verification, or transactional governance checkpoints.

## Source Evidence

- `docs/project-overview.md`: Platform-Native Philosophy table listing native vs custom choices
- `CLAUDE.md`: Overall architecture description
- System design: Three MCP servers are the only custom infrastructure
