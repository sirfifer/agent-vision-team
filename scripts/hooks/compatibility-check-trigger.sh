#!/usr/bin/env bash
# SessionStart hook: check if a Claude Code compatibility monitor run is due.
#
# Fires on session start events. Checks if the compatibility monitor is
# enabled and whether enough time has passed since the last check. If a
# check is due, injects additionalContext telling the orchestrator to
# spawn a researcher teammate.
#
# Exit codes:
#   0 = always (never block session start)

set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
CONFIG_PATH="${PROJECT_DIR}/.avt/project-config.json"
COMPAT_DIR="${PROJECT_DIR}/.avt/compatibility-monitor"
LAST_RUN_TS="${COMPAT_DIR}/.last-run-ts"

# Read hook input from stdin (required by hook protocol)
HOOK_INPUT=$(cat)

# Check if compatibility monitor is enabled
if ! command -v python3 &>/dev/null; then
    exit 0
fi

RESULT=$(python3 -c "
import json, time, sys
from pathlib import Path

project_dir = '$PROJECT_DIR'
config_path = Path(project_dir) / '.avt' / 'project-config.json'
last_run_path = Path(project_dir) / '.avt' / 'compatibility-monitor' / '.last-run-ts'

# Load config
import os
env_enabled = os.environ.get('AVT_COMPAT_MONITOR_ENABLED')
enabled = False
interval_hours = 24

if config_path.exists():
    try:
        cfg = json.loads(config_path.read_text())
        compat = cfg.get('settings', {}).get('compatibilityMonitor', {})
        enabled = compat.get('enabled', False)
        interval_hours = compat.get('check_interval_hours', 24)
    except Exception:
        pass

# Env var override
if env_enabled is not None:
    enabled = env_enabled.lower() in ('1', 'true', 'yes')

if not enabled:
    sys.exit(0)

# Check last run timestamp
now = time.time()
last_run = 0
last_run_display = 'never'

if last_run_path.exists():
    try:
        last_run = float(last_run_path.read_text().strip())
        from datetime import datetime, timezone
        last_run_display = datetime.fromtimestamp(last_run, tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    except (ValueError, OSError):
        pass

elapsed_hours = (now - last_run) / 3600

if elapsed_hours < interval_hours:
    sys.exit(0)

# A check is due
msg = (
    'COMPATIBILITY MONITOR: A Claude Code compatibility check is due '
    f'(last run: {last_run_display}). Spawn a researcher teammate '
    'with the research prompt at .avt/research-prompts/rp-cc-compatibility.md '
    'to check for platform changes affecting AVT.'
)
json.dump({'additionalContext': msg}, sys.stdout)
" 2>/dev/null) || true

if [ -n "$RESULT" ]; then
    echo "$RESULT"
fi

exit 0
