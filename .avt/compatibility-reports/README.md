# Compatibility Reports

> **IMPORTANT**: This directory is ONLY for reports produced by the AVT
> compatibility monitor system. If you are a Claude Code agent doing
> development work on the AVT codebase, this directory is not for you.

This directory contains automated Claude Code compatibility check reports.

## Naming Convention

Reports use the format: `cr-YYYY-MM-DD-cc-compat.md`

## Report Lifecycle

- **Daily reports** are written here by the compatibility monitor (ephemeral, gitignored)
- **P0/P1 findings** are also promoted to `docs/reports/` (committed to git)
- Reports accumulate during active use and are cleaned up per retention policy

## Triggering a Check

The compatibility monitor runs automatically via a SessionStart hook when enabled.
Enable it in `.avt/project-config.json`:

```json
{
  "settings": {
    "compatibilityMonitor": {
      "enabled": true
    }
  }
}
```

## Report Template

Reports follow the structure defined in `prompts/claude-code-feature-intelligence-search.md`,
with findings classified as P0 (Critical), P1 (High), P2 (Strategic), P3 (Track).
