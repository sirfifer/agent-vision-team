# Research Brief: Passive Audit Agent Design

**Question**: How should we design a non-blocking audit agent that observes the entire AVT system, correlates cause and effect, and produces ongoing statistics and recommendations?
**Date**: 2026-02-19
**Sources**: AWS Prescriptive Guidance, OpenTelemetry GenAI conventions, AgentMonitor (arXiv), AlertGuardian (ASE 2025), Google SRE, Prometheus lifecycle, Cloudflare alert observability, LangSmith/Arize/Langfuse architectures, disler/claude-code-hooks-multi-agent-observability, Event Sourcing/CQRS patterns

## Context

The AVT system has governance hooks, a knowledge graph, quality gates, and context reinforcement mechanisms. All of these produce events and affect agent behavior. What is missing is a unified, passive observer that watches everything, correlates what happened with what resulted, and produces actionable intelligence over time, without ever blocking or interfering with the system it observes.

## Core Design Principle: The Network TAP

The hardware networking world solved non-intrusive observation decades ago with the Network TAP (Test Access Point). A TAP sits on a link, copies all traffic to a monitoring port, and the original traffic is completely unaffected. If the TAP fails, the network continues operating.

This is the foundational metaphor. The audit agent:
- Receives copies of events, never sits in any critical path
- If it crashes, every other part of AVT continues unimpaired
- Processes events out-of-band on copied data
- Cannot write to governance.db, knowledge-graph.jsonl, or any operational store
- Has its own isolated storage

Nothing depends on it. It depends on everything (as a reader).

## Architecture

### Event Emission Layer

The AVT system already emits events through hooks. The audit agent adds a lightweight event emitter that appends structured events to an append-only log. Every hook, MCP tool call, and governance action writes one event record.

```
Existing hooks (holistic-review-gate, governance-task-intercept, etc.)
  |
  |-- [existing behavior unchanged]
  |
  +-- append to .avt/audit/events.jsonl  (new, ~0.5ms per write)
```

Each event is a single JSON line:

```json
{
  "id": "evt-a1b2c3",
  "ts": "2026-02-19T15:30:00.123Z",
  "session_id": "sess-xyz",
  "agent": "worker-001",
  "source": "hook:governance-task-intercept",
  "type": "governance.task_pair_created",
  "data": {
    "impl_task_id": "impl-abc",
    "review_task_id": "review-def",
    "standards_checked": ["protocol-based-DI", "no-singletons"]
  },
  "context": {
    "tool_call_count": 12,
    "context_remaining_pct": 45,
    "active_settings": {
      "contextReinforcement.enabled": true,
      "contextReinforcement.toolCallThreshold": 8
    }
  }
}
```

Key properties:
- **Append-only**: No updates, no deletes. Events are immutable facts.
- **Self-contained**: Each event carries its own context (settings snapshot, session state). The audit agent never needs to query the operational system to understand an event.
- **Cheap**: A single `open(append) + write + close` per event. No indexing, no transactions, no network calls.

### Event Types

| Category | Events | Source |
|----------|--------|--------|
| **Governance** | task_pair_created, decision_submitted, verdict_returned, review_completed, holistic_review_started, holistic_review_completed | governance hooks, governance MCP |
| **Quality** | gate_checked, gate_passed, gate_failed, finding_created, finding_dismissed | quality MCP |
| **Context** | reinforcement_triggered, reinforcement_skipped (debounce/dedup/cap), compaction_detected, post_compaction_reinjected, injection_content, session_context_distilled, session_context_updated, session_context_injected, distillation_spawned, distillation_refreshed, goal_completed, discovery_added | context reinforcement hook, compaction hook, `_distill-session-context.py`, `_update-session-context.py` |
| **KG** | entity_created, entity_modified, observation_added, tier_violation_attempted | KG MCP |
| **Agent** | agent_spawned, agent_completed, agent_failed, task_started, task_completed | Task tool usage |
| **Session** | session_started, session_compacted, session_ended, context_threshold_crossed | session lifecycle |

### The Audit Agent Process

The audit agent is a separate, long-lived process (not a subagent inside a Claude session). It runs alongside the MCP servers:

```
Terminal 4: Audit agent
cd mcp-servers/audit
uv run python -m collab_audit.agent
```

Or managed by the AVT Gateway in headless mode (auto-started alongside the other MCP servers).

It consists of three cooperating components:

```
events.jsonl (append-only)
      |
      v
[1. Event Processor]  -- reads new events via file watch / polling
      |
      |-- builds causal graph in memory
      |-- updates rolling statistics
      |-- checks anomaly triggers
      |
      v
[2. Analyzer]  -- runs periodically or on anomaly detection
      |
      |-- correlates cause-effect chains
      |-- detects patterns across sessions
      |-- generates/updates recommendations
      |-- prunes stale recommendations
      |
      v
[3. Dashboard Server]  -- lightweight HTTP server
      |
      |-- serves audit dashboard (separate from main AVT dashboard)
      |-- exposes statistics API
      |-- recommendation management UI
```

### Why Not a Claude Subagent?

Subagents are expensive, consume context, and are session-bound. The audit agent needs to:
- Run continuously across sessions (not tied to one orchestrator session)
- Process events cheaply (most work is counting, correlating, aggregating)
- Use LLM reasoning only for specific analytical tasks, not for event processing

The architecture uses Python for the event processor and statistical engine (cheap, fast), and spawns Claude subagents (Sonnet/Haiku) only for specific analytical tasks:

| Task | Model | When |
|------|-------|------|
| Event ingestion, counting, correlation | Python (no LLM) | Every event |
| Anomaly detection (threshold-based) | Python (no LLM) | Every event batch |
| Pattern analysis across sessions | Sonnet | Periodic (hourly/daily) |
| Recommendation generation | Sonnet | On anomaly or periodic |
| Recommendation staleness check | Haiku | Periodic (every 4 hours) |
| Causal chain summarization | Haiku | On demand (dashboard request) |
| Deep forensic analysis | Sonnet | On explicit request |

This keeps costs minimal. The vast majority of work is pure Python. LLM calls happen only when human-language reasoning is needed.

## Audit Levels

Inspired by logging frameworks but adapted for observability scope:

| Level | What's Captured | Storage Growth | Default |
|-------|----------------|---------------|---------|
| **SUMMARY** | Session-level aggregates: pass/fail counts, health score, recommendation count. One record per session. | ~1 KB/session | |
| **STANDARD** | All events with basic payloads. Governance decisions, quality gates, hook triggers, context injections. Causal links between events. | ~50 KB/session | Yes |
| **DETAILED** | Full event payloads including tool call arguments, injection content, governance guidance text, finding details. | ~500 KB/session |  |
| **FORENSIC** | Above plus full causal chain reconstruction, decision lineage graphs, raw hook I/O, settings diffs between events. Replay capability. | ~2 MB/session |  |

### Ring Buffer for Efficient Detail Capture

At STANDARD level, the processor maintains an in-memory ring buffer of the last 100 events at DETAILED fidelity. Under normal conditions, these are never persisted. When an anomaly is detected (governance block, quality gate failure, vision violation), the ring buffer flushes its contents to produce a detailed causal context around the anomaly. This gives forensic-level detail around problems without forensic-level storage costs.

This pattern comes from kernel crash dump design and Cloudflare's alert observability system.

### Level Configuration

```json
{
  "audit": {
    "enabled": true,
    "level": "STANDARD",
    "ringBufferSize": 100,
    "anomalyFlush": true,
    "retention": {
      "events": "30d",
      "recommendations": "90d",
      "statistics": "365d"
    }
  }
}
```

Levels can be changed at runtime without restarting the audit agent. Changing from STANDARD to FORENSIC starts capturing full payloads immediately; changing back stops capturing them but does not delete what was already captured.

## Cause-Effect Correlation

### The Causal Graph

The audit agent maintains a directed graph where nodes are events and edges are causal relationships. Edges are inferred from:

1. **Temporal proximity + session identity**: Events in the same session within a short window are candidates for causal links.
2. **Explicit references**: A `verdict_returned` event references the `decision_submitted` event by task_id. A `gate_failed` event references the `task_completed` event that triggered it.
3. **Settings lineage**: When a setting changes and subsequent behavior differs from the pre-change baseline, the setting change is linked as a cause.

Example causal chain:

```
[session_started]
  -> [agent_spawned: worker-003]
    -> [governance.task_pair_created: impl-abc / review-def]
      -> [governance.verdict_returned: approved, standards: protocol-based-DI]
        -> [context.reinforcement_triggered: route=vision-di, tokens=380]
          -> [quality.gate_checked: lint=pass, test=pass]
            -> [task_completed: impl-abc]
```

When something breaks, the graph enables questions like:
- "The quality gate failed. What governance decision preceded it? What context was injected (or not)?"
- "Context reinforcement was skipped (debounce). Did the subsequent work show drift symptoms?"
- "This setting was changed 3 sessions ago. How have governance approval rates changed since?"

### Correlation Queries

The audit agent exposes these queries via its API:

```
GET /api/audit/chain/{event_id}          -> full causal chain for an event
GET /api/audit/impact/{setting_key}      -> downstream effect of a setting change
GET /api/audit/pattern/{pattern_type}    -> recurring patterns (e.g., "block-then-retry")
GET /api/audit/drift/{session_id}        -> drift indicators for a session
```

## Statistics

### Ongoing Metrics (SRE Golden Signals Adapted)

| Signal | Agent Metric | Computation |
|--------|-------------|-------------|
| **Latency** | Governance review time, quality gate time, hook execution time | p50, p95, p99 per event type |
| **Traffic** | Events per minute, tool calls per session, governance decisions per hour | Rolling averages, trend detection |
| **Errors** | Governance rejection rate, quality gate failure rate, hook interception misses | Rate per window, comparison to baseline |
| **Saturation** | Context window utilization at decision points, concurrent task count | High-water marks, threshold alerts |

### Derived Metrics

| Metric | What It Measures | Why It Matters |
|--------|-----------------|----------------|
| **First-pass approval rate** | % of governance decisions approved without revision | Low rate suggests unclear task briefs or misaligned workers |
| **Context reinforcement effectiveness** | Quality gate pass rate in sessions with reinforcement vs. without | Validates that the reinforcement system helps |
| **Recommendation resolution time** | Time from recommendation creation to resolution | Indicates whether recommendations are actionable |
| **Drift correlation score** | Correlation between tool call count and governance rejection rate within sessions | Empirical measurement of context drift in this project |
| **Settings impact score** | Change in downstream metrics after a setting change | Helps tune settings with evidence |
| **Hook reliability** | % of expected hook fires that actually occurred | Detects hook failures or misconfigurations |

### Statistical Storage

Rolling aggregates stored in `.avt/audit/statistics.db` (SQLite, separate from all operational databases):

- Per-session summaries
- Per-day aggregates
- Per-week trends
- Per-setting-change impact records

## Recommendation System

### Recommendation Structure

```json
{
  "id": "rec-2026-02-19-001",
  "created": "2026-02-19T16:00:00Z",
  "updated": "2026-02-19T18:30:00Z",
  "status": "active",
  "type": "setting_tune",
  "priority": "medium",
  "title": "Consider lowering toolCallThreshold from 8 to 6",
  "analysis": "Over the last 5 sessions, governance rejection rate increases 23% after tool call 6. Current threshold (8) delays reinforcement past the observed drift onset.",
  "evidence": {
    "sessions_analyzed": 5,
    "correlation_coefficient": 0.78,
    "supporting_events": ["evt-a1b2c3", "evt-d4e5f6"]
  },
  "action": {
    "setting": "contextReinforcement.toolCallThreshold",
    "current_value": 8,
    "suggested_value": 6,
    "expected_impact": "~15% reduction in post-threshold governance rejections"
  },
  "ttl_days": 14,
  "staleness_check": "2026-02-20T16:00:00Z",
  "resolution": null
}
```

### Recommendation Types

| Type | Trigger | TTL | Example |
|------|---------|-----|---------|
| **setting_tune** | Statistical correlation between a setting value and a downstream metric | 14 days | "Lower toolCallThreshold to 6" |
| **pattern_detected** | Recurring causal chain that suggests a systemic issue | 30 days | "Workers consistently fail quality gates after holistic review delays > 10s" |
| **anomaly** | Sudden deviation from baseline metrics | 7 days | "Governance rejection rate spiked 3x in today's session" |
| **coverage_gap** | Expected events not observed | 7 days | "No context reinforcement events in last 3 sessions despite being enabled" |
| **stale_config** | Setting that has not been reviewed since the system changed around it | 30 days | "jaccardThreshold has been 0.15 since install; 40% of reinforcement attempts are skipped due to low match scores" |
| **vision_drift** | Governance decisions increasingly reference the same vision standard as a blocker | indefinite | "3 of last 5 governance blocks cite 'protocol-based-DI'; workers may need updated task briefs" |

### Recommendation Lifecycle

```
DETECTED
  |
  v
PENDING  (waiting for correlation/confirmation across multiple events)
  |
  v
ACTIVE  (confirmed with evidence, visible on dashboard)
  |
  +---> PARTIALLY_RESOLVED  (condition improved but not fully addressed)
  |       |
  |       +---> ACTIVE  (regressed)
  |       +---> RESOLVED
  |
  +---> RESOLVED  (condition fully addressed, auto-detected or manually marked)
  |
  +---> STALE  (TTL expired; audit agent re-evaluates relevance)
  |       |
  |       +---> ARCHIVED  (no longer relevant, moved to history)
  |       +---> ACTIVE  (re-confirmed as still relevant with updated evidence)
  |
  +---> SUPERSEDED  (replaced by a newer, more specific recommendation)
  |
  +---> DISMISSED  (human explicitly marked as not actionable, with reason)
```

### Self-Auditing of Recommendations

The audit agent periodically (every 4 hours, using Haiku) reviews its own active recommendations:

1. **Staleness check**: Is the triggering condition still present? Re-run the statistical query that produced the recommendation. If the correlation no longer holds, mark STALE.
2. **Partial resolution check**: Has the relevant metric improved? If the recommendation said "lower threshold to 6" and the threshold is now 7, mark PARTIALLY_RESOLVED with updated analysis.
3. **Supersession check**: Has a newer recommendation been generated that covers the same setting or pattern? If so, mark the older one SUPERSEDED.
4. **Relevance check**: Have the settings, architecture, or agent configurations changed in ways that make the recommendation moot? If `contextReinforcement.enabled` was set to false, all reinforcement-related recommendations become irrelevant.

This self-auditing runs as a background task using Haiku for the relevance reasoning and Python for the statistical re-queries.

### Engaging Recommendations

The dashboard provides three actions for each active recommendation:

- **Apply**: For setting_tune recommendations, this shows a confirmation dialog with the suggested change and applies it to `.avt/project-config.json`. The audit agent then tracks the downstream effect as a natural experiment.
- **Acknowledge**: Mark as reviewed but not acted on. Requires a brief reason. Resets the staleness timer.
- **Dismiss**: Mark as not actionable. Requires a reason. Moved to history. The audit agent will not regenerate the same recommendation unless new evidence emerges.

Recommendations that sit unengaged past their TTL are flagged with a visual indicator on the dashboard. They are not auto-dismissed; the audit agent re-evaluates them and either re-confirms (with updated evidence and a nudge) or archives them.

## Dashboard

### Separate View, Not Separate Application

The audit dashboard is a separate route/tab within the existing AVT web dashboard, not a separate application. In VS Code, it would be a separate panel/view. It shares authentication and project context but has its own UI.

### Dashboard Sections

**1. Health Overview (always visible)**

A compact strip showing current health:
- Session count (today/week)
- Overall approval rate (governance)
- Quality gate pass rate
- Active recommendation count (by priority)
- Current audit level

**2. Statistics View**

Time-series charts for the golden signals (latency, traffic, errors, saturation) plus the derived metrics. Configurable time window (session, day, week, month). Comparison mode: overlay two time periods to see trends.

**3. Recommendations View**

List of active recommendations sorted by priority, then by age. Each recommendation shows:
- Title and type badge
- Age and TTL remaining (visual progress bar)
- Evidence summary (expandable)
- Action buttons (Apply / Acknowledge / Dismiss)

Filter by: type, priority, status, age.

**4. Event Stream (DETAILED+ levels only)**

Real-time scrolling event feed with filters by event type, agent, session. Expanding an event shows its causal chain and linked recommendations.

**5. Causal Explorer (FORENSIC level only)**

Interactive directed graph visualization. Click an event to see its causes and effects. Highlight a setting to see all events it influenced. Time slider to replay event sequences.

### API

The audit dashboard is backed by a lightweight API (part of the audit agent process or served by the AVT Gateway):

```
GET  /api/audit/health                    -> health overview
GET  /api/audit/stats?window=7d           -> statistics for time window
GET  /api/audit/recommendations           -> active recommendations
POST /api/audit/recommendations/{id}/apply      -> apply a recommendation
POST /api/audit/recommendations/{id}/ack        -> acknowledge
POST /api/audit/recommendations/{id}/dismiss    -> dismiss (requires reason)
GET  /api/audit/events?type=governance&limit=50 -> filtered event stream
GET  /api/audit/chain/{event_id}                -> causal chain
GET  /api/audit/config                          -> current audit settings
PUT  /api/audit/config                          -> update audit settings (level, retention, etc.)
```

## Integration with AVT

### What the Audit Agent Reads (Event Sources)

| Source | How | What |
|--------|-----|------|
| Hook emissions | Append to events.jsonl from existing hooks (one added line per hook) | Governance intercepts, holistic reviews, context reinforcement |
| Governance MCP | Events emitted by governance server on each tool call | Decisions, verdicts, task pairs, plan reviews |
| Quality MCP | Events emitted by quality server on gate checks | Gate results, findings, dismissals |
| KG MCP | Events emitted by KG server on mutations | Entity changes, tier violations, observation additions |
| Session state | File watch on .avt/session-state.md | Session progress, task transitions |
| Settings | File watch on .avt/project-config.json | Setting changes (triggers impact tracking) |

### What the Audit Agent Writes (Its Own Storage Only)

| Store | Location | Purpose |
|-------|----------|---------|
| Events (raw) | `.avt/audit/events.jsonl` | Append-only event log |
| Statistics | `.avt/audit/statistics.db` | SQLite, rolling aggregates |
| Recommendations | `.avt/audit/recommendations.json` | Active and historical recommendations |
| Causal graph | `.avt/audit/causal-graph.db` | SQLite, event relationships |

All under `.avt/audit/`. Completely separate from `.claude/collab/` (operational stores).

### Adding Event Emission to Existing Hooks

Each existing hook gets one additional line at the end:

```python
# At the end of governance-task-intercept.py:
emit_audit_event("governance.task_pair_created", {
    "impl_task_id": impl_id,
    "review_task_id": review_id,
    "standards_checked": standards
})
```

Where `emit_audit_event` is a fire-and-forget function that appends to `events.jsonl`:

```python
def emit_audit_event(event_type: str, data: dict) -> None:
    """Append audit event. Fire-and-forget: failures are silently ignored."""
    try:
        event = {
            "id": f"evt-{uuid4().hex[:8]}",
            "ts": datetime.utcnow().isoformat() + "Z",
            "session_id": os.environ.get("CLAUDE_SESSION_ID", "unknown"),
            "type": event_type,
            "data": data,
        }
        with open(".avt/audit/events.jsonl", "a") as f:
            f.write(json.dumps(event) + "\n")
    except Exception:
        pass  # Never fail the calling hook
```

The `try/except` with bare `pass` is intentional and correct here. The audit emission must never cause the operational hook to fail. This is the TAP guarantee.

### MCP Server Event Emission

Each MCP server gets a similar emitter. For the governance server:

```python
# In collab_governance/server.py, after each tool handler:
audit.emit("governance.decision_submitted", {"task_id": task_id, "category": category, ...})
audit.emit("governance.verdict_returned", {"task_id": task_id, "verdict": verdict, ...})
```

The emitter module is shared across servers but each server emits its own event types.

## Model Usage Strategy

| Component | Model | Rationale |
|-----------|-------|-----------|
| Event Processor | Python (no LLM) | Pure data: parse JSON, update counters, build graph edges. No reasoning needed. |
| Threshold Anomaly Detection | Python (no LLM) | Comparing numbers to thresholds. Statistical correlation (Pearson, Spearman). |
| Pattern Analysis | Sonnet | Identifying non-obvious patterns across sessions. Needs reasoning about sequences and contexts. |
| Recommendation Generation | Sonnet | Writing clear, actionable recommendations with evidence summaries. |
| Staleness/Relevance Check | Haiku | Simple yes/no: "Is this condition still present? Is this recommendation still relevant?" |
| Causal Chain Summarization | Haiku | Summarizing a chain of events into a human-readable narrative. Structured input, structured output. |
| Forensic Deep Dive | Sonnet | Detailed root cause analysis. Needs full reasoning capability. |

### Parallelism

When the analyzer runs its periodic cycle:
1. Staleness checks for all active recommendations can run in parallel (each is independent, each uses Haiku)
2. Pattern analysis across different event categories can run in parallel
3. Recommendation generation for independent anomalies can run in parallel

The audit agent uses Python's `concurrent.futures.ThreadPoolExecutor` for LLM call parallelism, bounded to 4 concurrent calls to avoid rate limits.

## Operational Characteristics

### Performance Budget

| Operation | Budget | Mechanism |
|-----------|--------|-----------|
| Event emission (per hook) | < 1ms | Append-only file write, no sync |
| Event processing (per event) | < 5ms | In-memory graph update, counter increment |
| Anomaly check (per event batch) | < 50ms | Threshold comparison on in-memory stats |
| Periodic analysis (hourly) | < 30s | 2-4 Sonnet calls in parallel |
| Staleness review (4-hourly) | < 15s | N parallel Haiku calls (one per recommendation) |
| Dashboard API response | < 100ms | Read from pre-computed projections |

### Failure Modes

| Failure | Impact on AVT | Recovery |
|---------|--------------|----------|
| Audit agent crashes | Zero. All hooks, governance, quality, KG continue. | Restart agent. It picks up from last processed event in events.jsonl. |
| events.jsonl write fails | One event lost. Hook continues normally. | Tolerable. Ring buffer may capture it anyway. |
| statistics.db corrupted | Lose aggregates. Events still intact. | Rebuild from events.jsonl (it is the source of truth). |
| LLM call fails | Recommendation generation delayed. | Retry on next periodic cycle. |
| Dashboard server down | No UI. All data collection continues. | Restart. Dashboard reads from pre-computed data. |

### Storage Management

- **events.jsonl**: Rotated daily. Older files compressed and retained per retention policy (default 30 days).
- **statistics.db**: Aggregates are compact. Hourly granularity for the last 7 days, daily for 30 days, weekly for 365 days.
- **recommendations.json**: Active recommendations in a single file. Archived recommendations in `.avt/audit/archive/`.

## Settings

Added to `.avt/project-config.json` under `settings.audit`:

```json
{
  "settings": {
    "audit": {
      "enabled": false,
      "level": "STANDARD",
      "ringBufferSize": 100,
      "anomalyFlush": true,
      "periodicAnalysisInterval": "1h",
      "stalenessCheckInterval": "4h",
      "retention": {
        "events": "30d",
        "recommendations": "90d",
        "statistics": "365d"
      },
      "recommendations": {
        "autoStalenessCheck": true,
        "defaultTTL": {
          "setting_tune": "14d",
          "pattern_detected": "30d",
          "anomaly": "7d",
          "coverage_gap": "7d",
          "stale_config": "30d",
          "vision_drift": "indefinite"
        }
      },
      "models": {
        "pattern_analysis": "sonnet",
        "recommendation_generation": "sonnet",
        "staleness_check": "haiku",
        "causal_summary": "haiku",
        "forensic_analysis": "sonnet"
      },
      "maxConcurrentLLMCalls": 4
    }
  }
}
```

These follow the same cascade pattern as the context reinforcement settings: installation defaults, global config overrides, project config overrides. `enabled` defaults to `false` so the audit agent is opt-in.

## Design Influences

### AWS Observer Agent Pattern

AWS documents a canonical [Observer and Monitoring Agent](https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-patterns/observer-and-monitoring-agents.html) pattern: a passive, non-invasive event listener that perceives, interprets, and conditionally escalates. It never initiates behavior. This maps directly to our design.

### Event Sourcing + CQRS

The events.jsonl file is an event store. The audit agent builds its own read-optimized projections (statistics.db, causal-graph.db, recommendations.json) from this stream. The write model (AVT operations) and read model (audit analysis) are completely decoupled.

### Prometheus Alert Lifecycle

The recommendation lifecycle (DETECTED, PENDING, ACTIVE, PARTIALLY_RESOLVED, RESOLVED, STALE, ARCHIVED, SUPERSEDED, DISMISSED) is adapted from [Prometheus Alertmanager](https://prometheus.io/docs/alerting/latest/alertmanager/). Added: PARTIALLY_RESOLVED (for when a condition improves but is not fully addressed) and SUPERSEDED (for when a newer recommendation replaces an older one).

### Cloudflare Alert Observability

Cloudflare's approach to [combating alert fatigue](https://blog.cloudflare.com/alerts-observability/) informed the self-auditing design. Their key insight: stale silences (analogous to stale recommendations) accumulate and create blind spots. Actively pruning and re-evaluating recommendations is as important as generating them.

### AlertGuardian (ASE 2025)

[AlertGuardian](https://yuxiaoba.github.io/files/ASE25/AlertGuardian.pdf) achieves 93-95% alert reduction through RAG-based correlation and multi-agent iterative feedback. Informs our approach of correlating related findings and deduplicating recommendations rather than surfacing raw events.

### AgentMonitor (arXiv 2408.14972)

[AgentMonitor](https://arxiv.org/abs/2408.14972) wraps agents externally (like PEFT wrappers) to capture inputs/outputs without modifying internals. Their statistical prediction capability (predicting task success from intermediate observations, 0.89 Spearman correlation) suggests our audit agent could eventually predict governance outcomes from early-session signals.

### Google SRE Golden Signals

The four golden signals (latency, traffic, errors, saturation) adapted for agent systems provide the statistical backbone. SLO-based thinking (defining what "healthy" looks like numerically) makes anomaly detection concrete rather than subjective.

### OpenTelemetry GenAI Conventions

The [OTel GenAI semantic conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/) define standard schemas for agent spans, events, and metrics. Adopting these conventions means our audit data is portable to any OTel-compatible backend (Grafana, Datadog, Arize) if needed later, without locking into a custom schema.

### Existing Claude Code Observability Projects

[disler/claude-code-hooks-multi-agent-observability](https://github.com/disler/claude-code-hooks-multi-agent-observability) demonstrates the hook-to-SQLite-to-WebSocket-to-dashboard pipeline for Claude Code. [ColeMurray/claude-code-otel](https://github.com/ColeMurray/claude-code-otel) demonstrates the OTel-to-Grafana pipeline. Both validate that hook-based event emission is the right integration point.

## Implementation Status (2026-02-20)

The audit agent has been implemented using a **hook piggyback / fan belt architecture** rather than the long-running process described above. Key differences from the original design:

### Architecture Change: Hook Piggyback (No Daemon)

Instead of a separate long-running process, the implementation uses the system's own hook activity to drive audit processing. When the system is active, hooks fire and piggyback audit event emission. When the system is idle, nothing audit-related runs. This eliminates process management, auto-start/stop logic, and the dashboard server component.

**Processing flow**: Hook fires -> `emit_audit_event()` appends to events.jsonl (~0.5ms) -> spawns settle checker (detached subprocess) -> settle checker waits 5s -> if no newer events, spawns processor -> processor reads new events, updates stats, checks anomalies -> if anomaly found, spawns escalation chain.

### Tiered LLM Escalation (Not Periodic Analysis)

Instead of periodic Sonnet analysis on a schedule, the implementation uses a three-tier escalation chain triggered only by detected anomalies:

| Tier | Model | When | Cost |
|------|-------|------|------|
| **Tier 1** | Haiku | Warning+ anomaly detected | ~$0.005 |
| **Tier 2** | Sonnet | Haiku says "emerging pattern" | ~$0.03 |
| **Tier 3** | Opus | Sonnet says "significant milestone" | ~$0.15 |

Each tier is a detached subprocess that spawns the next only if warranted. ~85% of trigger events complete in ~5ms with no LLM call.

### Observation Directives (Editable JSON)

A `directives.json` file defines what to look for without code changes. Each directive specifies watch patterns, tier-specific questions, and recommendation types. New directives can be added by editing this file.

### Dashboard Integration

The dashboard is an **Audit tab** in the existing React webview (not a separate application or route). It shows a health strip, active recommendations with dismiss actions, and a recent events feed. The extension reads pre-computed data directly from `.avt/audit/` files.

### Simplified Recommendation Lifecycle

States: `active -> stale/dismissed/superseded/resolved`. No `PENDING` or `PARTIALLY_RESOLVED` states. TTL-based expiry with evidence count deduplication.

### What Was Not Implemented (Deferred)

- **Causal graph**: The causal-graph.db and chain/impact/pattern/drift API endpoints. Statistical correlation is sufficient for v1.
- **Ring buffer**: Events are always written at STANDARD level. Anomaly-triggered detail flush deferred.
- **MCP server event emission**: Events are emitted from hooks only, not from MCP server tool handlers. Hook coverage is sufficient for v1.
- **Audit levels**: Only STANDARD level implemented. SUMMARY, DETAILED, and FORENSIC deferred.
- **Self-auditing of recommendations**: Periodic Haiku staleness checks deferred. TTL-based expiry handles the basic case.
- **OTel export**: Custom JSONL format only.
- **Apply action for recommendations**: Dashboard has Dismiss only. Apply (auto-tune settings) deferred.

### Implementation Files

```
scripts/hooks/audit/              # Shared audit library
    __init__.py
    emitter.py                    # emit_audit_event() (fire-and-forget, TAP guarantee)
    config.py                     # Load audit settings from project-config.json
    directives.json               # 5 observation directives (editable)
    stats.py                      # StatsAccumulator (SQLite rolling aggregates)
    anomaly.py                    # AnomalyDetector (5 threshold checks)
    recommendations.py            # RecommendationManager (JSON-file lifecycle)
    escalation.py                 # Tiered LLM chain (claude --print + temp file I/O)
    prompts.py                    # Prompt builders + directive matching
    tests/                        # 53 unit tests (emitter, stats, anomaly, recommendations, prompts)

scripts/hooks/_audit-settle-check.py  # Background settle checker (5s, longer than governance 3s)
scripts/hooks/_audit-process.py       # Processor (file lock, checkpoint, anomaly check)
scripts/hooks/_audit-escalate.py      # Escalation chain runner (Haiku -> Sonnet -> Opus)

extension/webview-dashboard/src/components/audit/AuditPanel.tsx  # Dashboard Audit tab
extension/src/providers/DashboardWebviewProvider.ts              # 4 audit message handlers
extension/webview-dashboard/src/types.ts                         # Audit types

.avt/audit/                       # Runtime storage (gitignored)
    events.jsonl                  # Append-only event log
    statistics.db                 # SQLite rolling aggregates
    recommendations.json          # Active recommendations
    checkpoint.json               # Last-processed byte offset
    .last-event-ts                # Settle coordination timestamp
    .processor-lock               # File-based exclusion lock
```

### Hooks Modified (Event Emission Added)

| Hook | Event emitted |
|------|--------------|
| `governance-task-intercept.py` | `governance.task_pair_created` + spawns settle checker |
| `_holistic-settle-check.py` | `governance.holistic_review_completed` / `governance.holistic_review_skipped` |
| `_run-governance-review.sh` | `governance.individual_review_completed` |
| `task-completed-gate.sh` | `task.completion_attempted` |
| `teammate-idle-gate.sh` | `agent.idle_blocked` |
| `verify-governance-review.sh` | `governance.plan_exit_attempted` |

## Open Questions (Updated)

1. ~~**OTel adoption depth**~~: Deferred. Using custom JSONL format for v1.

2. ~~**Multi-project isolation**~~: Deferred. Single project per installation.

3. ~~**Dashboard technology**~~: Resolved. Integrated as a tab in the existing React dashboard.

4. **Predictive capabilities**: Still open. AgentMonitor showed 0.89 Spearman correlation. Could build on the statistical foundation in statistics.db.

5. ~~**Event emission in subagents**~~: Resolved. Events use absolute paths via `CLAUDE_PROJECT_DIR` environment variable.

6. **Causal graph**: Deferred from v1. Would enable "why did this happen?" queries. The event log contains the raw data; the correlation engine is the missing piece.

7. **MCP server event emission**: Should governance/quality/KG servers emit their own audit events? Currently only hooks emit. Server-side emission would capture API calls not triggered by hooks.

## Sources

### Architectural Patterns
- [Observer and Monitoring Agents (AWS Prescriptive Guidance)](https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-patterns/observer-and-monitoring-agents.html)
- [Event Sourcing Pattern (Microsoft Azure)](https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing)
- [Write-Ahead Log (Martin Fowler)](https://martinfowler.com/articles/patterns-of-distributed-systems/write-ahead-log.html)
- [Network TAP (Wikipedia)](https://en.wikipedia.org/wiki/Network_tap)

### AI Agent Observability
- [AgentMonitor (arXiv 2408.14972)](https://arxiv.org/abs/2408.14972)
- [OpenTelemetry GenAI Agent Spans](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/)
- [AI Agent Observability: Evolving Standards (OpenTelemetry Blog)](https://opentelemetry.io/blog/2025/ai-agent-observability/)
- [State of AI Agents (LangChain)](https://www.langchain.com/state-of-agent-engineering)

### Observability Platforms
- [LangSmith Observability](https://www.langchain.com/langsmith/observability)
- [Arize Phoenix](https://arize.com/docs/phoenix)
- [Langfuse](https://langfuse.com/docs/observability/overview)
- [Datadog LLM Observability](https://www.datadoghq.com/product/llm-observability/)

### Claude Code Observability Implementations
- [disler/claude-code-hooks-multi-agent-observability](https://github.com/disler/claude-code-hooks-multi-agent-observability)
- [ColeMurray/claude-code-otel](https://github.com/ColeMurray/claude-code-otel)
- [Claude Code Monitoring with OTel (SigNoz)](https://signoz.io/blog/claude-code-monitoring-with-opentelemetry/)

### SRE and Alert Management
- [Monitoring Distributed Systems (Google SRE)](https://sre.google/sre-book/monitoring-distributed-systems/)
- [Minimizing On-Call Burnout Through Alerts Observability (Cloudflare)](https://blog.cloudflare.com/alerts-observability/)
- [Monitoring Our Monitoring (Cloudflare)](https://blog.cloudflare.com/monitoring-our-monitoring/)
- [AlertGuardian (ASE 2025)](https://yuxiaoba.github.io/files/ASE25/AlertGuardian.pdf)
- [Prometheus Alert Lifecycle](https://prometheus.io/docs/alerting/latest/alertmanager/)

### Security and Governance Frameworks
- [Agentic AI Security Scoping Matrix (AWS)](https://aws.amazon.com/blogs/security/the-agentic-ai-security-scoping-matrix-a-framework-for-securing-autonomous-ai-systems/)
- [Audit Trails for Accountability in LLMs (arXiv)](https://arxiv.org/html/2601.20727)
- [Traceability in Agentic AI (NexaStack)](https://www.nexastack.ai/blueprints/agentic-ai-traceability/)
