#!/usr/bin/env bash
#
# compile-rules.sh — Compile project rules into an agent prompt preamble
#
# Reads .avt/project-config.json and outputs a formatted rules block
# for injection into subagent prompts. Filters rules by agent role/scope
# and groups them by enforcement level.
#
# Usage:
#   ./scripts/compile-rules.sh <agent-role>
#
# Examples:
#   ./scripts/compile-rules.sh worker
#   ./scripts/compile-rules.sh quality-reviewer
#   ./scripts/compile-rules.sh researcher
#   ./scripts/compile-rules.sh all          # show rules for all scopes
#
# Exit codes:
#   0 — rules compiled successfully (or no rules found)
#   1 — missing argument or invalid config

set -euo pipefail

CONFIG_PATH=".avt/project-config.json"

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <agent-role>" >&2
    echo "  agent-role: worker | quality-reviewer | researcher | steward | all" >&2
    exit 1
fi

ROLE="$1"

if [[ ! -f "$CONFIG_PATH" ]]; then
    echo "No project config found at $CONFIG_PATH" >&2
    exit 0
fi

# Use python to parse JSON and compile rules (available via uv or system python)
python3 -c "
import json
import sys

role = '$ROLE'
config_path = '$CONFIG_PATH'

try:
    with open(config_path, 'r') as f:
        config = json.load(f)
except (json.JSONDecodeError, FileNotFoundError):
    sys.exit(0)

rules = config.get('rules', {}).get('entries', [])
if not rules:
    sys.exit(0)

# Filter enabled rules matching the agent scope
filtered = []
for rule in rules:
    if not rule.get('enabled', False):
        continue
    scopes = rule.get('scope', ['all'])
    if role == 'all' or 'all' in scopes or role in scopes:
        filtered.append(rule)

if not filtered:
    sys.exit(0)

# Group by enforcement level
enforce_rules = [r for r in filtered if r.get('enforcement') == 'enforce']
prefer_rules = [r for r in filtered if r.get('enforcement') == 'prefer']
guide_rules = [r for r in filtered if r.get('enforcement') == 'guide']

print('## Project Rules')
print('These rules govern how work is done in this project. Follow them.')
print()

if enforce_rules:
    print('ENFORCE:')
    for r in enforce_rules:
        print(f\"- {r['statement']}\")
    print()

if prefer_rules:
    print('PREFER (explain if deviating):')
    for r in prefer_rules:
        print(f\"- {r['statement']}\")
    print()

if guide_rules:
    print('GUIDE (follow when practical):')
    for r in guide_rules:
        print(f\"- {r['statement']}\")
    print()
"
