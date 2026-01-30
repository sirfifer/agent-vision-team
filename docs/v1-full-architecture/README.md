# V1 Full Architecture (Archived)

These documents represent the original "full infrastructure" direction for the Collaborative Intelligence System, designed January 27-29, 2026.

This architecture included:
- **Three custom MCP servers**: Communication Hub, Knowledge Graph, Quality
- **VS Code extension as orchestration engine**: Spawning terminals, managing sessions, starting/stopping servers
- **Custom session management**: Extension-driven lifecycle for orchestrator, worker, and quality sessions

## Why Archived

After scaffolding this architecture (all builds passing, 21 tests passing), we discovered that Claude Code's native capabilities (January 2026 — subagents, Task tool, background execution, lifecycle hooks, worktree patterns) already handle most of what the Hub server and extension orchestration layer were designed to do.

Rather than building infrastructure that duplicates the platform, we pivoted to a **platform-native architecture** that:
- Uses Claude Code's native subagent system for orchestration
- Keeps only the Knowledge Graph and Quality MCP servers (unique value the platform doesn't provide)
- Reduces the extension to a monitoring/observability layer
- Uses CLAUDE.md + `.claude/agents/` for declarative orchestration

## Status

These documents are preserved in their final state. They may be revisited if:
- The platform-native approach hits limitations that require custom orchestration infrastructure
- The Hub server's agent registry and message routing prove necessary at scale
- The extension needs to take on active session management beyond monitoring

## Files

- `COLLABORATIVE_INTELLIGENCE_VISION.md` — The original vision document (1,094 lines). All core principles, tier hierarchy, memory architecture, and communication channels.
- `ARCHITECTURE.md` — The engineering architecture (1,430 lines). Full component diagrams, API contracts, extension architecture, data flows, implementation phases.
