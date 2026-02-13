# Transcript Review Feature: Implementation Plan (Phase B)

*Saved for future reference. Execute only after Phase A experimentation is reviewed and approved.*

## Overview

Add automated post-session transcript review that identifies permission denials and recommends allowlist additions. Triggered by Stop and SubagentStop hooks, toggleable via project config.

## Architecture

```
Session completes (Stop / SubagentStop)
    -> Hook fires: transcript-review.py
    -> Check toggle: .avt/project-config.json -> settings.transcriptReview
    -> Phase 1: Deterministic parse of transcript JSONL
    -> Phase 2: Generate allowlist recommendations
    -> Phase 3: Write report to .avt/transcript-reviews/
    -> Phase 4 (optional): LLM-assisted analysis for ambiguous cases
```

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `scripts/hooks/_transcript_analyzer.py` | Create | Core analysis module (stdlib only) |
| `scripts/hooks/transcript-review.py` | Create | Hook entry point (Stop + SubagentStop) |
| `.claude/settings.json` | Modify | Register Stop + SubagentStop hooks |
| `.avt/project-config.json` | Modify | Add `transcriptReview` toggle |
| `.avt/transcript-reviews/` | Create dir | Report output directory |
| `e2e/scenarios/s15_transcript_review.py` | Create | E2E test scenario |

## Core Module: `_transcript_analyzer.py`

Functions:
- `parse_transcript(jsonl_path)`: Stream-parse JSONL, extract tool_use/tool_result pairs
- `classify_errors(events, allowlist)`: Categorize errors (user_rejected, hook_blocked, tool_error, permission_denied, unknown)
- `generate_recommendations(errors)`: Map denied tools to allowlist patterns
- `load_allowlist(settings_path)`: Load permissions.allow from settings.json

## Hook Entry Point: `transcript-review.py`

Flow:
1. Read hook input from stdin
2. Check toggle in project-config.json (exit if disabled)
3. Check stop_hook_active to prevent infinite loops (Stop hook)
4. Resolve transcript path (agent_transcript_path for SubagentStop)
5. Run deterministic analysis
6. Write report file
7. Output additionalContext (Stop hook only, for user-facing summary)

## Report Format

```json
{
  "session_id": "abc123",
  "agent_type": "worker",
  "timestamp": "2026-02-10T15:30:00Z",
  "total_tool_calls": 45,
  "total_errors": 3,
  "classified_errors": [...],
  "recommendations": [
    { "pattern": "Bash(python3:*)", "occurrences": 2, "confidence": "high" }
  ]
}
```

## Settings Hook Registration

```json
"Stop": [{
  "hooks": [{
    "type": "command",
    "command": "uv run ... transcript-review.py",
    "timeout": 10
  }]
}],
"SubagentStop": [{
  "hooks": [{
    "type": "command",
    "command": "uv run ... transcript-review.py",
    "timeout": 10
  }]
}]
```

## Error Classification (to be refined by Phase A findings)

- `user_rejected`: content matches "user doesn't want to proceed"
- `hook_blocked`: content contains "GOVERNANCE" or "HOLISTIC"
- `tool_error`: content contains "File does not exist", "Exit code"
- `permission_denied`: tool error + tool/command not in allowlist
- `unknown`: everything else

## Allowlist Pattern Generation

| Tool | Pattern |
|------|---------|
| Bash | `Bash(<first-word>:*)` |
| Write | `Write(<project-dir>/**)` |
| Edit | `Edit(<project-dir>/**)` |
| MCP | `mcp__<server>__*` |

Dangerous patterns (rm, sudo, writes outside project) flagged as `review_needed`.

## Testing

- Unit tests with synthetic JSONL transcripts
- E2E scenario (s15_transcript_review.py) using mock transcripts
- Live integration test extending test-permission-behavior.sh

## Aggregate Tracking (stretch)

`.avt/transcript-reviews/_summary.json` accumulates recommendations across sessions. Patterns denied 3+ times promoted to "strongly recommended."
