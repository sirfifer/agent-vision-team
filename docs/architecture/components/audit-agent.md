# Audit Agent

## Type

component

## Description

Passive system observer that watches all AVT activity through hook-piggybacked event emission, detects anomalies via threshold-based checks, and produces actionable recommendations through a tiered LLM escalation chain (Haiku triage, Sonnet analysis, Opus deep dive). Uses a "fan belt" architecture: powered by the system's own hook activity, dormant when idle. No daemon, no long-running process.

## Usage

Enabled via `settings.audit.enabled: true` in `.avt/project-config.json`. Once enabled, existing hooks automatically emit audit events. Processing is triggered by settle detection after batches of activity.

## Internal Structure

```mermaid
graph TD
    subgraph Hooks
        H1["governance-task-intercept.py"]
        H2["_holistic-settle-check.py"]
        H3["_run-governance-review.sh"]
        H4["task-completed-gate.sh"]
        H5["teammate-idle-gate.sh"]
        H6["verify-governance-review.sh"]
    end

    subgraph Emission
        EM["emitter.py<br/>emit_audit_event()"]
        EV["events.jsonl<br/>(append-only)"]
        TS[".last-event-ts"]
    end

    subgraph Processing
        SC["_audit-settle-check.py<br/>(5s debounce)"]
        PR["_audit-process.py<br/>(file lock + checkpoint)"]
        ST["stats.py<br/>StatsAccumulator"]
        AN["anomaly.py<br/>AnomalyDetector"]
        RM["recommendations.py<br/>RecommendationManager"]
    end

    subgraph Escalation
        ES["_audit-escalate.py"]
        T1["Tier 1: Haiku<br/>Quick triage"]
        T2["Tier 2: Sonnet<br/>Pattern analysis"]
        T3["Tier 3: Opus<br/>Strategic deep dive"]
    end

    subgraph Dashboard
        AP["AuditPanel.tsx"]
        DW["DashboardWebviewProvider.ts"]
    end

    H1 --> EM
    H2 --> EM
    H3 --> EM
    H4 --> EM
    H5 --> EM
    H6 --> EM
    EM --> EV
    EM --> TS
    H1 --> SC
    SC --> PR
    PR --> ST
    PR --> AN
    AN --> RM
    AN --> ES
    ES --> T1
    T1 --> T2
    T2 --> T3
    DW --> EV
    DW --> RM
    AP --> DW
```

## Event Types

| Category | Events | Source Hook |
|----------|--------|------------|
| **Governance** | `governance.task_pair_created`, `governance.holistic_review_completed`, `governance.holistic_review_skipped`, `governance.individual_review_completed`, `governance.plan_exit_attempted` | governance-task-intercept, _holistic-settle-check, _run-governance-review, verify-governance-review |
| **Task** | `task.completion_attempted` | task-completed-gate |
| **Agent** | `agent.idle_blocked` | teammate-idle-gate |

## Processing Pipeline

1. **Event emission** (~0.5ms): Hooks call `emit_audit_event()`, which appends to `events.jsonl` and updates `.last-event-ts`. Wrapped in try/except pass (TAP guarantee).
2. **Settle detection** (5s): `governance-task-intercept.py` spawns `_audit-settle-check.py` as a detached subprocess. It sleeps 5s, checks if newer events arrived, and spawns the processor only if quiet.
3. **Processing** (~5ms typical): `_audit-process.py` acquires a file lock, reads events since the last checkpoint, updates rolling statistics in SQLite, and runs anomaly detection.
4. **Anomaly detection**: Five threshold checks (block rate, gate block rate, idle blocks, reinforcement skip rate, event rate spike). Pure Python arithmetic, no LLM.
5. **Recommendation creation**: Anomalies produce recommendations (deduplicated by type, TTL-based expiry, JSON-file lifecycle).
6. **Escalation** (only on warning+ anomalies): Three tiers of detached subprocesses, each spawning the next only if warranted.

## Anomaly Checks

| Check | Threshold | Severity |
|-------|-----------|----------|
| High governance block rate | > 50% per session | warning |
| High gate block rate | > 50% with min 3 gates | warning |
| Repeated idle blocks | 3+ in one batch | info |
| High reinforcement skip rate | > 70% with min 3 events | warning |
| Event rate spike | > 3x rolling baseline | info |

## Observation Directives

Five editable directives in `directives.json`:
- `setting-correlation`: Detect setting value / outcome correlations
- `prompt-effectiveness`: Detect when prompts are not producing intended outcomes
- `range-adequacy`: Detect when setting ranges are too narrow or wide
- `governance-health`: Monitor overall governance pipeline health
- `coverage-gaps`: Detect expected events that never fire

## Recommendation Lifecycle

```
active -> stale     (TTL expired, auto-pruned)
active -> dismissed (user dismisses with reason)
active -> superseded (newer recommendation covers same area)
active -> resolved  (condition addressed)
```

Evidence count increments on re-detection; TTL resets each time.

## Storage

All under `.avt/audit/` (gitignored):

| File | Format | Purpose |
|------|--------|---------|
| `events.jsonl` | JSONL (append-only) | Source of truth for all audit events |
| `statistics.db` | SQLite (WAL mode) | Rolling aggregates: event_counts, session_summaries, metric_windows, anomalies |
| `recommendations.json` | JSON | Active and historical recommendations |
| `checkpoint.json` | JSON | Last-processed byte offset into events.jsonl |
| `.last-event-ts` | Text (epoch float) | Settle coordination between concurrent checkers |
| `.processor-lock` | File lock (fcntl) | Prevents concurrent processor runs |

## Dependencies

- Python 3.9+ (no external dependencies beyond stdlib)
- Claude CLI (`claude --print`) for escalation tiers
- SQLite3 (stdlib)

## Patterns Used

- Network TAP (passive, non-intrusive observation)
- Fan Belt (driven by existing system activity, dormant when idle)
- Settle/Debounce (same pattern as governance holistic review, but 5s instead of 3s)
- Fire-and-Forget Subprocess (`subprocess.Popen(start_new_session=True)`)
- TAP Guarantee (all audit code wrapped in `try/except: pass`)
- Temp File I/O (for `claude --print` invocations in escalation)
