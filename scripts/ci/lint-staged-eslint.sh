#!/usr/bin/env bash
# Wrapper for lint-staged to run ESLint from the extension directory.
# lint-staged passes absolute file paths as arguments.
set -euo pipefail
cd "$(dirname "$0")/../../extension"
npx eslint --fix "$@"
