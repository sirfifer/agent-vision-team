# Research Brief: Permission Behavior & Session Lifecycle Hooks

**Date**: 2026-02-10
**Claude Code Version**: 2.1.22
**Status**: Experimentation complete, findings require design pivot

---

## Executive Summary

Three experiments were run to validate assumptions for an "End-of-Session Transcript Review" feature. The results reveal that **permission restrictions are not enforced in non-interactive (`-p`) mode**, which means the original design premise ("detect permission denials in transcripts") needs to pivot. However, the **Stop and SubagentStop hooks work exactly as documented** and provide full transcript access, making a session review feature technically feasible with an adjusted scope.

---

## Experiment 1: Permission Denial Transcript Patterns

### What Was Tested

Spawned Claude sessions in `-p` mode with various permission configurations, then examined transcripts for denial patterns.

| Test | Flags Used | Result |
|------|-----------|--------|
| dontAsk mode | `--permission-mode dontAsk --allowedTools "Read"` | Bash ran **successfully** |
| disallowedTools | `--disallowedTools "Bash"` | Bash ran **successfully** |
| plan mode | `--permission-mode plan` | Bash ran **successfully** |
| tools restriction | `--tools "Read,Glob,Grep"` | Claude did NOT attempt Bash (tool absent) |

### Key Findings

1. **Permission modes do not restrict tools in `-p` mode.** Neither `dontAsk`, `plan`, nor `disallowedTools` prevented Bash from executing. This matches known GitHub issues (#581, #949, #6631).

2. **`--tools` flag removes tools from the model's context entirely.** When a tool is removed via `--tools`, Claude simply doesn't attempt to use it. There is **no denial entry** in the transcript; the tool just doesn't exist.

3. **The only "denial" pattern found in real transcripts is user rejection in interactive mode:**
   ```
   "The user doesn't want to proceed with this tool use. The tool use was rejected
   (eg. if it was a file edit, the new_string was NOT written to the file).
   STOP what you are doing and wait for the user to tell you how to proceed."
   ```
   This appears with `is_error: true` on the `tool_result` block.

4. **The JSON output includes `permission_denials: []`** which is always empty in non-interactive mode. This field exists in the schema but is only populated during interactive sessions.

5. **Other error types found in transcripts** (from real sessions, not experiments):
   - `<tool_use_error>File does not exist.</tool_use_error>`
   - `<tool_use_error>File has not been read yet. Read it first before writing to it.</tool_use_error>`
   - `<tool_use_error>Sibling tool call errored</tool_use_error>`
   - `File content (61518 tokens) exceeds maximum allowed tokens`
   - `Exit code 1` / `Exit code 127`
   - `<tool_use_error>String to replace not found in file.</tool_use_error>`

### Implication

Permission denials do not meaningfully occur in automated/subagent sessions. The feature cannot rely on detecting "denied" tools in subagent transcripts because denials don't happen in non-interactive mode.

---

## Experiment 2: Subagent Permission Propagation

### What Was Tested

Spawned subagents with various tool restrictions to see if the parent's permissions flow down to children.

| Test | Parent Restriction | Subagent Behavior |
|------|-------------------|-------------------|
| `--agents` tools list `["Read","Glob","Grep"]` | Bash not in agent tools | Subagent **used Bash successfully** |
| `--permission-mode dontAsk` + `--allowedTools "Read,Task"` | Only Read,Task pre-approved | Subagent **used Bash successfully** |
| `--tools "Read,Task"` | Parent physically limited | Subagent **used Bash successfully** |

### Key Findings

1. **Subagents do NOT inherit the parent's tool restrictions.** Even when the parent was limited to `--tools "Read,Task"` (physically removing Bash), the spawned Bash subagent had full Bash access.

2. **Agent tool configuration (`--agents`) is not enforced in `-p` mode.** The tools list in agent definitions acts as documentation/guidance but does not restrict tool availability.

3. **Real subagent transcripts show NO permission errors.** Searched 13 subagent transcripts across multiple sessions; all errors were normal tool failures (file not found, directory read, command exit code), never permission-related.

4. **Subagent behavior when a tool is unavailable:** The subagent simply does not use it. There is no error, no denial; the tool is absent from the model's context. The subagent adapts to available tools.

### Implication

In the AVT system, workers and other subagents operate with full tool access (bounded by the parent's `--dangerously-skip-permissions`). Permission issues won't surface as transcript errors. The only mechanism that blocks subagent tools is the **PreToolUse hook** (which our governance gate uses), and those blocks appear with custom content from the hook, not as standard permission denials.

---

## Experiment 3: Stop & SubagentStop Hook Input Schema

### What Was Tested

Registered minimal Stop and SubagentStop hooks that dump their stdin JSON to files. Ran sessions to capture the actual input schema.

### Stop Hook Input (confirmed across 4 invocations)

```json
{
  "session_id": "uuid-string",
  "transcript_path": "/Users/.../.claude/projects/<encoded-path>/<session-id>.jsonl",
  "cwd": "/current/working/directory",
  "permission_mode": "bypassPermissions",
  "hook_event_name": "Stop",
  "stop_hook_active": false
}
```

**Fields:**
- `session_id`: UUID of the session (consistent across all invocations)
- `transcript_path`: Full absolute path to the session's JSONL transcript (always present)
- `cwd`: Working directory of the session
- `permission_mode`: The active permission mode (e.g., "bypassPermissions", "dontAsk")
- `hook_event_name`: Always "Stop"
- `stop_hook_active`: `false` on first invocation; `true` if Claude is continuing due to a previous Stop hook block (prevents infinite loops)

### SubagentStop Hook Input (confirmed)

```json
{
  "session_id": "uuid-string",
  "transcript_path": "/path/to/main-session.jsonl",
  "cwd": "/current/working/directory",
  "permission_mode": "bypassPermissions",
  "hook_event_name": "SubagentStop",
  "stop_hook_active": false,
  "agent_id": "a666568",
  "agent_transcript_path": "/path/to/<session-id>/subagents/agent-<agent-id>.jsonl"
}
```

**Additional fields (not in Stop):**
- `agent_id`: Short hash identifier for the subagent (e.g., "a666568")
- `agent_transcript_path`: Full path to the subagent's own transcript JSONL

**Missing from research expectations:**
- `agent_type` is NOT present (the research suggested it would be). Only `agent_id` is provided.

### Hook Loading and Registration

- Hooks from `--settings` file are loaded as `flagSettings` (separate from project/user settings)
- The `--settings` flag correctly merges with user settings
- Both Stop and SubagentStop fire in `-p` mode (confirmed)
- Hook lifecycle order: SubagentStart -> PreToolUse(Bash) -> PostToolUse(Bash) -> SubagentStop -> PostToolUse(Task) -> Stop -> SessionEnd

### Debug Log Evidence

```
Getting matching hook commands for SubagentStop with query: undefined
Found 1 hook matchers in settings
Matched 1 unique hooks for query "no match query" (1 before deduplication)
```

---

## Feasibility Assessment

### Can we reliably detect permission denials from transcripts?

**No, not in the way originally envisioned.** Permission denials don't occur in non-interactive/subagent mode. However:

### What CAN we detect from transcripts?

1. **User rejections (interactive sessions only)**: "The user doesn't want to proceed..." pattern with `is_error: true`. These are real permission denials by the user and are the ideal candidates for allowlist recommendations.

2. **PreToolUse hook blocks**: Our governance hooks block tools with custom messages. These appear as `is_error: true` with our hook's content (e.g., "HOLISTIC GOVERNANCE REVIEW IN PROGRESS"). These should be excluded from allowlist recommendations.

3. **Tool execution errors**: Normal errors (file not found, command failed) that indicate issues but not permission problems.

4. **Tool availability gaps**: By comparing the `tool_use` calls an agent attempted against the agent's configured tools list, we could identify tools the agent needed but didn't have. However, when a tool isn't available, the agent simply doesn't try to use it, so this comparison would require analyzing the agent's reasoning text (not deterministic).

### Revised Feature Scope

Given these findings, the feature should focus on:

1. **Interactive session review (Stop hook)**: Analyze the main agent's transcript for `is_error: true` entries with "user rejected" content. Recommend adding these tools to the allowlist. This is the highest-value, most reliable use case.

2. **Subagent error analysis (SubagentStop hook)**: Analyze subagent transcripts for `is_error: true` entries to surface tool execution failures (not permission denials). This helps identify configuration issues, missing files, broken commands, etc.

3. **Governance block analysis**: Separate governance hook blocks from other errors. Track how often the holistic review gate blocks work to identify if it's too aggressive.

4. **Aggregate tool usage patterns**: Track which tools each agent type actually uses across sessions. This helps optimize agent tool configurations over time.

---

## Test Artifacts

All experiment outputs are in `.avt/debug/`:
- `experiment-direct-transcript-analysis.json` (Experiment 1)
- `stop-hook-input-*.json` (Experiment 3, Stop)
- `subagent-stop-hook-input-*.json` (Experiment 3, SubagentStop)

Test scripts:
- `scripts/hooks/test-permission-behavior.sh` (Experiments 1 & 2)
- `scripts/hooks/test-stop-hooks.sh` (Experiment 3)

---

## Recommendations for Phase B

1. **Pivot the feature scope** from "detect permission denials" to "session quality review" covering tool errors, user rejections, and governance blocks.

2. **Focus on interactive sessions first** (Stop hook) since that's where user rejections (the most actionable finding) actually occur.

3. **Use SubagentStop for error aggregation** rather than permission analysis. Track recurring errors across subagent sessions to identify systemic issues.

4. **The `permission_denials` field in JSON output** is worth monitoring. If Claude Code fixes the `-p` mode permission enforcement in a future version, this field would become populated and extremely useful.

5. **Hook schema is stable and well-suited** for this feature. Both Stop and SubagentStop provide `transcript_path` / `agent_transcript_path` for full transcript access.
