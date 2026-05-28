#!/bin/bash
set -euo pipefail

# Dynamically find Playwright-installed Chromium
if [ -z "${PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH:-}" ]; then
  CHROMIUM_PATH=$(find "$HOME/.cache/ms-playwright" -maxdepth 3 -name "chrome" -type f 2>/dev/null | head -1)
  if [ -n "$CHROMIUM_PATH" ]; then
    export PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH="$CHROMIUM_PATH"
  fi
fi

exec npx -y "@playwright/mcp@latest" "$@"
