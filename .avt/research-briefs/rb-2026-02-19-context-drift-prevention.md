# Research Brief: Context Drift Prevention for AVT

**Question**: How should we implement context drift prevention with tunable per-project settings?
**Date**: 2026-02-19
**Sources**: 6 research papers, 12 industry blog posts, 8 open-source implementations, 3 parallel research agents

## Context

A community post described a 764-line PreToolUse hook that detects context drift in Claude Code sessions by analyzing thinking blocks and injecting relevant context via `additionalContext`. The approach uses a static 62-route JSON context router, fires after 8+ tool calls, injects up to 500 tokens, and includes debounce/dedup safeguards.

We evaluated this approach against published research and expert consensus to determine what to adopt, what to modify, and what to skip for our multi-agent system.

## The Problem: Expert Consensus

Context drift is well-documented across multiple research groups. Key terminology:

| Term | Source | Definition |
|------|--------|------------|
| Context Drift | Dongre et al. (2025) | Gradual divergence from goal-consistent behavior across turns |
| Context Rot | Chroma Research (2025) | Performance degradation as input tokens increase, even within the context window |
| Agent Drift | Rath (2026) | Progressive degradation of agent behavior over extended interaction sequences |
| Lost in the Middle | Liu et al. (2024, MIT Press) | Models perform best with info at beginning/end of context, ~30% worse in the middle |

**Root causes are architectural, not behavioral**: transformer self-attention creates n-squared pairwise relationships that get stretched thin as context grows. RoPE (Rotary Position Embedding) introduces long-term decay favoring tokens at sequence boundaries. Small errors compound autoregressively in multi-turn interactions.

### When Drift Starts

There is no single validated threshold. Research suggests drift is continuous and token-volume-dependent:

| Threshold | Source | Finding |
|-----------|--------|---------|
| ~32k tokens | Chroma/NoLiMa | 11 of 12 models drop below 50% of short-context performance |
| 73 interactions (median) | Agent Drift paper | Median onset in multi-agent systems |
| ~100k tokens | Gemini Pokemon agent | Context distraction: agent favors repeating history over novel planning |
| ~128k tokens | Manus production | Trigger point for summarization/compaction |

The blog post's "8 tool calls" figure is reasonable as a heuristic: at 2-4k tokens per tool call, 8 calls accumulate 16-32k tokens, which aligns with Chroma's finding that significant degradation begins around 32k. But it is really about accumulated token volume, not a magic call count.

### What Works (Layered Approach)

No single technique solves the problem. Expert consensus favors layered mitigation:

1. **Persistent artifacts on disk** (highest reliability): CLAUDE.md files survive compaction because they are re-read from disk. Progress files, decision logs, and plan documents persist independently of context.

2. **Hook-based deterministic injection** (high reliability): SessionStart with `compact` matcher for post-compaction re-injection. PreToolUse `additionalContext` for per-tool-call reminders.

3. **Context hygiene** (prevention): Minimum necessary tokens per model call. Observation masking over summarization (JetBrains NeurIPS 2025: masking matched or beat LLM summarization in 4/5 settings while being cheaper). Limit visible tools to ~20.

4. **Monitoring and thresholds** (detection): Track remaining context percentage. Trigger intervention at configurable thresholds.

5. **Sub-agent isolation** (structural): Fresh contexts for discrete tasks. Anthropic showed 90.2% improvement despite 15x more total tokens.

### What Does NOT Work (Anti-patterns)

1. **Over-injection**: Every new token depletes the model's attention budget. More context is often worse, not better.
2. **LLM Summarization smoothing over failures**: JetBrains found simple observation masking beat expensive LLM summarization because summaries paraphrase away the severity of failures.
3. **Static large system prompts**: Each MCP server's tool definitions consume context. 16.3% of window can be consumed before a conversation even starts.
4. **Compaction as a solution**: Auto-compaction is lossy. Post-compaction compliance drops to ~60-70% because paraphrased instructions lose precision.

### The "Drift No More?" Optimistic Finding

Dongre et al. (2025) challenged the assumption that drift accumulates unboundedly. Their research shows drift is a **bounded stochastic process with restoring forces**, not inevitable monotonic decay. Simple reminder interventions reliably reduce divergence. This supports our approach: periodic, targeted reminders are sufficient; we do not need complex real-time drift detection.

### Google Research: Prompt Repetition Works

Leviathan et al. (Google, 2025) demonstrated that simply repeating prompts consistently improves performance across all tested models, winning 47 of 70 benchmark-model combinations with zero losses. The mechanism: causal attention is left-to-right, so repetition allows every token to attend to every other. Minimal latency cost since repetition only affects the parallelizable prefill stage.

This directly validates the concept of periodic context re-injection.

## Options Evaluated

### Option A: Full Thinking Block Analysis (Blog Post Approach)

- **How it works**: PreToolUse hook extracts keywords from Claude's extended thinking blocks, matches against a 62-route static JSON router, injects matched context via `additionalContext`.
- **Pros**: Theoretically the most precise signal of cognitive state. Only injects context when the agent is actively thinking about a topic.
- **Cons**: Extended thinking blocks are not reliably available in all hook contexts. No published research validates thinking block analysis for drift prevention specifically. Adds parsing complexity. The 62-route static JSON requires manual maintenance.
- **Integration effort**: High (thinking block parsing, route file maintenance).
- **Risks**: Fragile dependency on thinking block availability. False negatives when drift occurs without keyword signals.

### Option B: Periodic UserPromptSubmit Re-injection (Rotating Reminders)

- **How it works**: UserPromptSubmit hook tracks prompt count, injects rotating context reminders every N prompts via `additionalContext`. Different reminder "slots" cycle through vision standards, architecture patterns, and project rules.
- **Pros**: Simple, proven pattern (documented in John Lindquist's gist, used by ContextStream). Fires on every user prompt. Aligns with Google's prompt repetition research.
- **Cons**: Fires only on user prompts, not during autonomous multi-tool sequences. Not responsive to what the agent is currently thinking about. Fixed injection regardless of need.
- **Integration effort**: Low (~100 lines).
- **Risks**: Wastes tokens when agent is not drifting. Does not help during long autonomous runs.

### Option C: Hybrid PreToolUse + SessionStart (Recommended)

- **How it works**: Three complementary hooks working together:
  1. **SessionStart (`compact` matcher)**: Re-injects critical context after every compaction event. Fires reliably because CLAUDE.md is re-read from disk but additional behavioral context (project rules, current task focus) is not.
  2. **PreToolUse (`Write|Edit`)**: After a configurable tool call threshold, injects relevant context from a KG-derived router via `additionalContext`. Uses tool call count (not thinking block analysis) as the trigger. Simple keyword matching against tool_input for relevance.
  3. **KG-derived context router**: Generated from existing KG entities + project rules. No manual maintenance of a separate route file.
- **Pros**: Leverages our existing infrastructure (KG, project rules, hook stack). Proven mechanisms (additionalContext, SessionStart compact matcher). KG-derived router stays in sync automatically. Multiple layers of protection. All tunable.
- **Cons**: More moving parts than Option B. Router generation adds a build step. PreToolUse on Write|Edit adds latency (~50ms when active, ~1ms under threshold).
- **Integration effort**: Medium (~300 lines total across 2 hooks + router generator).
- **Risks**: Must coexist with existing holistic-review-gate. Tool call count is a proxy for token accumulation, not a direct measure.

### Option D: StatusLine-Based Token Monitoring

- **How it works**: Monitor `context_window.remaining_percentage` from StatusLine. Trigger increasingly aggressive context injection as the window fills.
- **Pros**: Directly measures the actual resource (context window usage) rather than using a proxy (tool call count).
- **Cons**: StatusLine is not available in hook context (it is a UI feature). Would require a separate monitoring mechanism. More complex architecture.
- **Integration effort**: High (custom monitoring daemon).
- **Risks**: StatusLine data may not be accessible programmatically from hooks.

## Analysis

### Blog Post Claims vs. Expert Consensus

| Claim | Blog Post | Expert Consensus | Verdict |
|-------|-----------|-----------------|---------|
| 8 tool calls threshold | Fixed at 8 | Token-dependent; 8 is reasonable at ~2-4k/call but should be tunable | **Adopt as default, make tunable** |
| 500 token injection | Fixed at 500 | 200-500 tokens is the sweet spot; more can hurt | **Adopt as default, make tunable** |
| Thinking block analysis | "Clearest signal" | No published validation for drift prevention; promising but unproven | **Skip for v1, revisit later** |
| Static 62-route JSON | Manual maintenance | Dynamic/KG-derived routing is trending | **Replace with KG-derived router** |
| 30-second debounce | Fixed | No published guidance; engineering judgment | **Adopt, make tunable** |
| Jaccard dedup | Novel approach | No comparison published; prevents redundancy | **Adopt (proven engineering pattern)** |
| Max 10 injections/session | Fixed cap | No published guidance; prevents over-injection | **Adopt, make tunable** |

### Why Option C (Hybrid) Is Recommended

1. **Covers the compaction gap**: SessionStart with `compact` matcher addresses the biggest threat (post-compaction context loss), which the blog post's approach does not address at all.

2. **Uses existing infrastructure**: Our KG already has vision standards, architecture patterns, and project rules. Generating a router from these sources keeps it accurate without maintenance.

3. **Aligns with research**: Google's prompt repetition paper validates periodic re-injection. The "Drift No More?" paper shows simple reminders work. JetBrains shows observation masking (lightweight intervention) beats heavy summarization.

4. **Appropriately scoped**: Does not attempt thinking block analysis (unproven) or real-time token monitoring (complex). Uses proven mechanisms with proven safeguards.

5. **Fully tunable**: Every parameter has a sensible default and a safe range, exposed through the existing settings infrastructure.

## Recommendation: Implement Option C with Tunable Settings

### Implementation Components

#### Component 1: Context Router Generator

A script that reads KG JSONL + project-config.json and produces a compact JSON router:

```json
{
  "generated": "2026-02-19T15:00:00Z",
  "routes": [
    {
      "id": "vision-di",
      "keywords": ["dependency", "injection", "DI", "protocol", "service", "registry"],
      "context": "VISION: All services use protocol-based dependency injection. No singletons in production code.",
      "tier": "vision",
      "source": "kg:protocol-based-DI",
      "scope": ["worker", "architect"]
    },
    {
      "id": "rule-no-mocks",
      "keywords": ["test", "mock", "stub", "fake", "spy"],
      "context": "RULE [enforce]: Write real integration and unit tests. Never use mocks, stubs, or fakes.",
      "tier": "rule",
      "source": "rule:no-mocks",
      "scope": ["worker", "quality-reviewer"]
    }
  ]
}
```

Generated by: `scripts/generate-context-router.py` (reads `.claude/collab/knowledge-graph.jsonl` + `.avt/project-config.json`)
Regenerated: on demand, or automatically when KG/rules change.
Output: `.avt/context-router.json`

#### Component 2: PreToolUse Context Reinforcement Hook

`scripts/hooks/context-reinforcement.py`

**Behavior**:
1. Read tool call counter from `.avt/.session-calls-{session_id}` (increment on every call)
2. If counter < threshold (default 8): increment, exit 0 with no output. Cost: ~1ms.
3. If counter >= threshold:
   - Read `.avt/context-router.json`
   - Extract keywords from `tool_input` (the tool's input parameters, not thinking blocks)
   - Match keywords against router routes using Jaccard similarity
   - Check debounce: skip if last injection was < debounce_seconds ago
   - Check dedup: skip if this route was already injected (tracked in `.avt/.injection-history-{session_id}`)
   - Check cap: skip if max_injections_per_session reached
   - If all checks pass: return JSON with `additionalContext` containing matched context
4. Filter routes by agent scope if available

**Safeguards** (all tunable):
- `toolCallThreshold`: default 8, range 3-25
- `maxTokensPerInjection`: default 400, range 100-800
- `debounceSeconds`: default 30, range 10-120
- `maxInjectionsPerSession`: default 10, range 3-30
- `jaccardThreshold`: default 0.15, range 0.05-0.50

#### Component 3: SessionStart Compact Matcher Hook

`scripts/hooks/post-compaction-reinject.sh`

**Behavior**: Fires after every compaction event. Reads `.avt/context-router.json` and injects all vision-tier routes (compact format, ~200 tokens total) plus the current task focus from `.avt/session-state.md`.

This addresses the single biggest context loss event (compaction) that the blog post's approach does not cover.

#### Component 4: Settings Schema Extension

Add a `contextReinforcement` section to `.avt/project-config.json`:

```json
{
  "settings": {
    "contextReinforcement": {
      "enabled": true,
      "toolCallThreshold": 8,
      "maxTokensPerInjection": 400,
      "debounceSeconds": 30,
      "maxInjectionsPerSession": 10,
      "jaccardThreshold": 0.15,
      "postCompactionReinject": true,
      "routerAutoRegenerate": true
    }
  }
}
```

### Settings Architecture: Per-Project with Global Defaults

#### The Cascade Pattern

Following the nil-means-inherit pattern (used by GitLab, VS Code, Docker Compose):

```
Installation Defaults (hardcoded in schema)
    |
    v
Global Config (~/.avt/global-config.json)  -- optional, overrides installation defaults
    |
    v
Project Config (.avt/project-config.json)  -- optional per-field, overrides global
```

Each field in the project config can be:
- **Present**: Overrides the global/installation default
- **Absent/null**: Inherits from the global default (nil-means-inherit)

#### Global Config Location

`~/.avt/global-config.json` (user home directory, outside any project):

```json
{
  "version": 1,
  "contextReinforcement": {
    "enabled": true,
    "toolCallThreshold": 10,
    "maxTokensPerInjection": 500
  }
}
```

Only fields that differ from installation defaults need to be present.

#### Effective Settings Resolution

```python
def get_effective_settings(
    installation_defaults: dict,
    global_config: dict | None,
    project_config: dict | None,
) -> dict:
    """Merge: installation -> global -> project. None fields inherit."""
    effective = {**installation_defaults}
    if global_config:
        for key, value in global_config.items():
            if value is not None:
                effective[key] = value
    if project_config:
        for key, value in project_config.items():
            if value is not None:
                effective[key] = value
    return effective
```

#### API Endpoints (Web Dashboard)

```
GET  /api/settings/defaults                      -> installation defaults
GET  /api/settings/global                        -> global overrides
PUT  /api/settings/global                        -> update global overrides

GET  /api/projects/{id}/settings                 -> effective (merged) settings
GET  /api/projects/{id}/settings/overrides       -> project-level overrides only
PUT  /api/projects/{id}/settings                 -> update project overrides
DELETE /api/projects/{id}/settings/{key}          -> reset setting to default

GET  /api/settings/schema                        -> JSON Schema with metadata
```

The primary GET endpoint returns effective values with source metadata:

```json
{
  "contextReinforcement.toolCallThreshold": {
    "value": 12,
    "source": "project",
    "default": 8,
    "globalValue": 10
  },
  "contextReinforcement.debounceSeconds": {
    "value": 30,
    "source": "installation_default",
    "default": 30
  }
}
```

#### UI Presentation

Both VS Code extension and web dashboard should:
1. Show **effective values** as the primary view
2. Mark overridden values with a visual indicator (colored bar, "(custom)" label)
3. Show the inherited value when hovering/expanding an overridden field
4. Provide per-field "Reset to Default" that removes the project override
5. For numeric thresholds: pair sliders with text inputs, show the default as a tick mark
6. Group context reinforcement settings under a dedicated section with a master enable/disable toggle

#### VS Code Extension Settings

Add to `extension/package.json` under `contributes.configuration`:

```json
{
  "avt.contextReinforcement.enabled": {
    "type": "boolean",
    "default": true,
    "scope": "resource",
    "description": "Enable automatic context reinforcement to prevent drift in long sessions."
  },
  "avt.contextReinforcement.toolCallThreshold": {
    "type": "integer",
    "default": 8,
    "minimum": 3,
    "maximum": 25,
    "scope": "resource",
    "description": "Number of tool calls before context reinforcement activates. Lower values reinforce earlier but use more tokens."
  }
}
```

Using `"scope": "resource"` allows per-workspace override of user-level defaults, matching VS Code's standard cascade.

#### Web Dashboard Settings Panel

Add a "Context Reinforcement" section to the existing SettingsPanel component:

- **Master toggle**: "Enable Context Reinforcement" (checkbox)
- **Tool Call Threshold**: Slider (3-25) + text input, default marker at 8
- **Max Tokens Per Injection**: Slider (100-800) + text input, default marker at 400
- **Debounce (seconds)**: Slider (10-120) + text input, default marker at 30
- **Max Injections Per Session**: Slider (3-30) + text input, default marker at 10
- **Jaccard Threshold**: Slider (0.05-0.50) + text input, default marker at 0.15
- **Post-Compaction Reinject**: Checkbox, default on
- **Auto-Regenerate Router**: Checkbox, default on
- **"Reset All to Defaults"** button at the bottom of the section

Each field shows "(default)" or "(from global)" when not overridden at the project level, and a small "reset" icon when overridden.

For the multi-project web dashboard: each project's settings page shows the effective (merged) values with per-field source indicators. The "Global Defaults" page (under system settings) shows and edits `~/.avt/global-config.json`.

### Integration with Existing Hook Stack

```
PreToolUse on Write|Edit|Bash|Task
  |-- holistic-review-gate.sh       (existing, ~1ms fast path, can block with exit 2)
  |-- context-reinforcement.py      (new, ~1ms under threshold, ~50ms when active)

SessionStart on compact
  |-- post-compaction-reinject.sh    (new, ~10ms, injects vision context after compaction)
```

The hooks coexist without conflict:
- holistic-review-gate uses exit code 2 to block (gates work)
- context-reinforcement uses additionalContext to advise (injects reminders)
- post-compaction-reinject uses additionalContext to restore (re-anchors after compaction)

### Hook Registration

Add to `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit|Bash|Task",
        "hooks": [
          { "type": "command", "command": "python3 scripts/hooks/holistic-review-gate.py" },
          { "type": "command", "command": "python3 scripts/hooks/context-reinforcement.py" }
        ]
      }
    ],
    "SessionStart": [
      {
        "matcher": "compact",
        "hooks": [
          { "type": "command", "command": "bash scripts/hooks/post-compaction-reinject.sh" }
        ]
      }
    ]
  }
}
```

## Open Questions

1. **Thinking block analysis for v2?** The blog post's approach of analyzing thinking blocks is theoretically sound but unproven for drift prevention. Should we plan a v2 that adds keyword extraction from thinking blocks as a refinement to the tool-input matching?

2. **PostCompact hook**: Currently the most-requested missing feature in Claude Code (issues #14258, #17237). When it ships, we should switch the compaction re-injection from SessionStart `compact` matcher to PostCompact for more reliable timing.

3. **Router regeneration trigger**: Should the context router regenerate automatically when the KG changes (via a PostToolUse hook on KG MCP calls), or only on explicit command?

4. **Token counting**: The `maxTokensPerInjection` setting uses an estimate (~4 tokens per word). Should we implement proper tokenization for precise counting, or is the estimate sufficient?

5. **Scope filtering in headless multi-project mode**: When the gateway manages multiple projects, each project's hooks need isolated session tracking. The session_id in the hook input should be sufficient, but needs verification.

## Sources

### Research Papers
- [Lost in the Middle (Liu et al., 2024)](https://arxiv.org/abs/2307.03172)
- [Context Rot (Chroma Research, 2025)](https://research.trychroma.com/context-rot)
- [Agent Drift (Rath, 2026)](https://arxiv.org/abs/2601.04170)
- [Drift No More? (Dongre et al., 2025)](https://arxiv.org/abs/2510.07777)
- [Prompt Repetition (Google Research, 2025)](https://arxiv.org/abs/2512.14982)
- [The Complexity Trap (JetBrains/NeurIPS 2025)](https://github.com/JetBrains-Research/the-complexity-trap)

### Industry
- [Effective Context Engineering (Anthropic)](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Effective Harnesses for Long-Running Agents (Anthropic)](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- [Context Engineering (Spotify/Honk)](https://engineering.atspotify.com/2025/11/context-engineering-background-coding-agents-part-2)
- [Context Engineering for AI Agents (Manus)](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus)
- [How Long Contexts Fail (Drew Breunig)](https://www.dbreunig.com/2025/06/22/how-contexts-fail-and-how-to-fix-them.html)
- [The Context Window Problem (Factory.ai)](https://factory.ai/news/context-window-problem)

### Tools and Implementations
- [Claude Code Hooks Reference](https://code.claude.com/docs/en/hooks)
- [claude-code-hooks-mastery](https://github.com/disler/claude-code-hooks-mastery)
- [Continuous-Claude-v3](https://github.com/parcadei/Continuous-Claude-v3)
- [ContextStream](https://github.com/contextstream/claude-code)
- [claude-mem](https://github.com/thedotmack/claude-mem)
- [claude-cognitive](https://github.com/GMaN1911/claude-cognitive)
- [Auto-Refresh Context Every N Prompts (Lindquist gist)](https://gist.github.com/johnlindquist/23fac87f6bc589ddf354582837ec4ecc)

### Settings Patterns
- [VS Code Contribution Points](https://code.visualstudio.com/api/references/contribution-points)
- [GitLab Cascading Settings](https://docs.gitlab.com/development/cascading_settings/)
- [Vercel Project Settings](https://vercel.com/docs/project-configuration/project-settings)
- [Docker Compose Merge](https://docs.docker.com/compose/how-tos/multiple-compose-files/merge/)
