# Compatibility Monitor Design

**Date**: 2026-03-23
**Status**: Implemented

## Problem

AVT depends heavily on Claude Code features (hooks, Agent Teams, MCP servers, `claude --print`, Task system, settings.json schema) that are actively evolving. Changes can break AVT, require accommodation, or present new opportunities. Monitoring is currently manual and ad-hoc.

## Solution

An automated, opt-in system that runs at least daily while AVT is active, using the existing researcher agent to search for Claude Code changes and compare them against the dependency manifest.

## Architecture

```
SessionStart hook
    |
    v
compatibility-check-trigger.sh
    |
    |-- checks enabled? (.avt/project-config.json)
    |-- checks interval? (.avt/compatibility-monitor/.last-run-ts)
    |
    v (if check is due)
additionalContext -> orchestrator
    |
    v
orchestrator spawns researcher teammate
    with .avt/research-prompts/rp-cc-compatibility.md
    |
    |-- loads platform-deps.yaml (28 dependencies)
    |-- queries KG for baseline (delta detection)
    |-- executes searches from intelligence search playbook
    |-- classifies findings (P0-P3)
    |
    v
Output (three tiers):
    Nothing found -> timestamp update only
    P2/P3 only   -> .avt/compatibility-reports/ (ephemeral)
    P0/P1        -> .avt/ + docs/reports/ (promoted, committed)
                    + additionalContext notification to orchestrator
    |
    v (if impending changes detected)
CronCreate -> adaptive follow-up in 4-6 hours
```

## Design Decisions

### Why the Existing Researcher Agent (Not a New Agent)

The researcher agent already has WebSearch, WebFetch, KG, and Governance tools. Its periodic/maintenance mode is designed for exactly this use case. A new agent would duplicate capabilities and add maintenance overhead.

### Why SessionStart Hook (Not CronCreate Alone)

CronCreate is session-scoped and auto-expires after 3 days. If the user starts new sessions daily, cron jobs from yesterday are gone. The SessionStart hook ensures a check is triggered at least once per session when the interval has elapsed. CronCreate is used for adaptive follow-ups within a session.

### Why No Matcher on SessionStart

The existing `compact` matcher fires only on compaction events. We need the compatibility check to fire on cold session starts too. Using no matcher (fires on all SessionStart events) with timestamp-based deduplication in the script handles both cases.

### Why Two-Tier Report Storage (Ephemeral + Promotion)

Daily reports that find nothing important should not clutter git history. But critical findings (P0/P1) should be permanently recorded. The ephemeral tier in `.avt/compatibility-reports/` catches everything; the promotion tier in `docs/reports/` preserves important findings.

### Why Delta Detection via KG

Re-reporting the same findings daily would be noise. By recording findings as KG observations on the `Claude Code Platform` entity, subsequent checks can filter out already-known items and only report genuinely new changes.

## Configuration

In `.avt/project-config.json` under `settings.compatibilityMonitor`:

| Key | Default | Description |
|-----|---------|-------------|
| `enabled` | `false` | Master switch. One field change to turn on. |
| `check_interval_hours` | `24` | Minimum hours between checks |
| `model_hint` | `"sonnet"` | Model for the researcher agent |
| `adaptive_followups` | `true` | Allow CronCreate follow-ups for pending changes |
| `notification_threshold` | `"P1"` | Minimum priority for orchestrator notification |

Environment variable override: `AVT_COMPAT_MONITOR_ENABLED=true`

## Existing Assets Leveraged

| Asset | Purpose |
|-------|---------|
| `scripts/validation/platform-deps.yaml` | Canonical dependency manifest (28 deps, 7 categories) |
| `prompts/claude-code-feature-intelligence-search.md` | Search queries, classification matrix, report template |
| `.claude/agents/researcher.md` | Agent definition with WebSearch/WebFetch/KG tools |
| `scripts/hooks/audit/config.py` | Config loader pattern |
| `scripts/hooks/post-compaction-reinject.sh` | SessionStart hook pattern |

## Implementation Files

```
scripts/hooks/compatibility/
    __init__.py
    config.py                    # Config loader (project-config.json cascade)
    monitor.py                   # Core: deps loading, classification, reporting
    tests/
        __init__.py
        test_config.py           # 12 tests: defaults, overrides, env vars, malformed
        test_monitor.py          # 37 tests: classify, delta, report, followup, write

scripts/hooks/compatibility-check-trigger.sh  # SessionStart hook (timestamp gating)

.avt/research-prompts/rp-cc-compatibility.md  # Automated research prompt

.avt/compatibility-reports/                   # Ephemeral report output (gitignored)
    README.md
    .gitkeep

.avt/compatibility-monitor/                   # Runtime state (gitignored)
    .last-run-ts                              # Epoch timestamp of last check
```

## Priority Classification

| Priority | Criteria | Output |
|----------|----------|--------|
| P0 | Confirmed breaking change | Report + promoted + notification |
| P1 | Likely breaking, or confirmed deprecation | Report + promoted + notification |
| P2 | Confirmed/likely opportunity, or rumored conflict | Report only (ephemeral) |
| P3 | General intelligence, ecosystem tracking | Report only (ephemeral) |

## Adaptive Follow-up Triggers

| Signal | Delay | Rationale |
|--------|-------|-----------|
| "release candidate", "coming soon", "will be released" | 4h (conflict) / 6h (opportunity) | Catch the actual release |
| Unconfirmed breaking change (confidence: Likely) | 4h | Verify or debunk |
| No signals | No follow-up | Next SessionStart check is sufficient |

## Test Coverage

49 unit tests covering:
- Config loader: defaults, project config override, env var override, malformed input
- Finding classification: all P0/P1/P2/P3 paths
- Delta detection: title match, source match, case insensitivity, empty inputs
- Report generation: headers, sections, summaries, action items, empty reports
- Timestamp management: creation, overwrite, directory creation
- Follow-up scheduling: pending announcements, unconfirmed breaks, no signals
- Report writing: ephemeral location, P0/P1 promotion, naming convention
- Dependency manifest loading: YAML parsing, missing files, structure validation
