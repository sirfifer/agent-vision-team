# Architecture Overview

## Project Summary

Agent Vision Team (AVT) is a collaborative intelligence platform that coordinates multiple AI agents for software development. It combines Claude Code's native capabilities (subagents, hooks, git worktrees, model routing) with three custom MCP servers (Knowledge Graph, Quality, Governance), a context reinforcement system that maintains agent alignment across long sessions, and an audit agent that passively monitors system health and produces actionable recommendations via tiered LLM analysis.

## System Context

```mermaid
graph TB
    Human[Human Developer]
    CC[Claude Code CLI]
    VSCode[VS Code IDE]

    Human --> CC
    Human --> VSCode

    subgraph AVT System
        Ext[VS Code Extension]
        GW[AVT Gateway]
        Dashboard[React Dashboard]
        KG[Knowledge Graph MCP]
        QS[Quality MCP]
        GOV[Governance MCP]
        Hooks[Hook Scripts]
        Agents[Agent Definitions]
        CR[Context Reinforcement]
        Audit[Audit Agent]
    end

    CC --> Hooks
    CC --> Agents
    VSCode --> Ext
    Ext --> Dashboard
    Ext --> KG
    Ext --> QS
    Ext --> GOV
    GW --> KG
    GW --> QS
    GW --> GOV
    Dashboard --> GW
    Hooks --> CR
    Hooks --> Audit
    CR --> KG
    Dashboard --> Audit

    subgraph External
        Git[Git Repository]
        LLM[Claude API]
        FS[File System]
    end

    CC --> Git
    GOV --> LLM
    KG --> FS
    GOV --> FS
    QS --> FS
```

## Component Map

```mermaid
graph LR
    subgraph Presentation
        Ext[VS Code Extension]
        Dash[React Dashboard]
    end

    subgraph API
        GW[AVT Gateway<br/>FastAPI]
        PM[postMessage<br/>Bridge]
    end

    subgraph Services
        KG[Knowledge Graph<br/>MCP Server]
        QS[Quality<br/>MCP Server]
        GOV[Governance<br/>MCP Server]
        CR[Context Reinforcement<br/>Session Alignment]
        AUD[Audit Agent<br/>Anomaly Detection]
    end

    subgraph Persistence
        JSONL[JSONL<br/>Knowledge Graph]
        SQLite1[SQLite<br/>Governance DB]
        SQLite2[SQLite<br/>Trust Engine DB]
        JSON[JSON Files<br/>Tasks, Config]
        AuditDB[SQLite + JSONL<br/>Audit Statistics]
    end

    subgraph Platform
        Hooks[7 Lifecycle Hooks]
        Agents[8 Agent Definitions]
        Tasks[Task System]
        CI[CI Scripts + Git Hooks]
    end

    Ext --> PM
    Ext --> GW
    Dash --> PM
    Dash --> GW
    GW --> KG
    GW --> QS
    GW --> GOV
    PM --> Ext
    KG --> JSONL
    GOV --> SQLite1
    QS --> SQLite2
    Hooks --> GOV
    Hooks --> CR
    Hooks --> AUD
    CR --> JSONL
    AUD --> AuditDB
    Agents --> KG
    Agents --> QS
    Agents --> GOV
    Tasks --> Hooks
```

## Component Inventory

| Component | Responsibility | Language | Path | Key Patterns |
|-----------|---------------|----------|------|-------------|
| VS Code Extension | IDE integration, webview hosting, MCP client wrappers | TypeScript | `extension/src/` | Provider pattern, command registration |
| React Dashboard | Real-time monitoring UI, dual-mode (VS Code + standalone) | React/TSX | `extension/webview-dashboard/src/` | Context providers, dual-mode transport |
| Knowledge Graph MCP | Persistent institutional memory, tier-protected CRUD | Python | `mcp-servers/knowledge-graph/` | FastMCP, JSONL storage, tier protection |
| Quality MCP | Deterministic quality gates, trust engine | Python | `mcp-servers/quality/` | FastMCP, tool wrapping, SQLite |
| Governance MCP | Decision review, governed tasks, AI reviewer | Python | `mcp-servers/governance/` | FastMCP, SQLite, temp file I/O |
| AVT Gateway | REST API, WebSocket push, job runner | Python | `server/avt_gateway/` | FastAPI, SSE MCP client, routers |
| E2E Test Harness | 14 scenarios, 292+ assertions, parallel execution | Python | `e2e/` | BaseScenario, structural assertions |
| Context Reinforcement | Session context distillation, goal tracking, three-layer injection | Python/Bash | `scripts/hooks/` | Background distillation, atomic writes, file locking |
| Audit Agent | Passive system observer: event emission, anomaly detection, tiered LLM escalation, recommendations | Python | `scripts/hooks/audit/` | Hook piggyback, settle/debounce, fire-and-forget subprocess, TAP guarantee |
| Hook Scripts | Platform-level governance verification + context drift prevention (7 hooks) | Bash/Python | `scripts/hooks/` | JSON stdin/stdout, fast-path, exit codes, additionalContext injection |
| CI Scripts | Unified quality pipeline (lint, typecheck, build, test, coverage) | Bash | `scripts/ci/` | Same scripts locally and in CI |
| GitHub Actions | CI pipeline on every push | YAML | `.github/workflows/ci.yml` | Parallel jobs, matrix strategy, xvfb |
| Git Hooks | Pre-commit (lint staged), pre-push (full pipeline) | Bash | `.husky/` | Husky v9, lint-staged, clear error reporting |

## Key Architectural Decisions

1. **MCP over custom API**: Using Model Context Protocol for all agent-service communication rather than REST or GraphQL
2. **Three-tier protection**: Vision/Architecture/Quality hierarchy enforced at the storage layer, not the API layer
3. **Hook-based governance**: Using Claude Code lifecycle hooks for automatic governance rather than requiring explicit agent cooperation
4. **Dual-mode transport**: Same React dashboard runs in VS Code (postMessage) and standalone (HTTP/WebSocket) with zero component duplication
5. **Temp file I/O**: Claude CLI invocations use temp files instead of CLI args or pipes to avoid buffer limits
6. **Session-scoped holistic review**: Groups of tasks reviewed collectively before any work begins, using timing-based settle detection
7. **Three-layer context reinforcement**: Session context (distilled goals/discoveries), static router (KG-derived vision/architecture), and post-compaction recovery. Background AI calls via `claude --print --model haiku`; synchronous hooks only read files
8. **Scripts-first CI/CD**: All quality checks run via bash scripts in `scripts/ci/`; git hooks and GitHub Actions both call the same scripts, ensuring local and CI behavior are identical
9. **Hook-piggybacked audit**: Passive audit agent driven by existing hook activity (no daemon); tiered LLM escalation (Haiku triage, Sonnet analysis, Opus deep dive) triggered only by detected anomalies
