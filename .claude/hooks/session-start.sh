#!/bin/bash
# SessionStart-хук для облачных сессий Claude Code: ставит зависимости бэкенда
# (uv) и фронтенда (npm), чтобы сразу работали ruff/mypy/pytest и tsc/next build.
# Локально ничего не делает. Идемпотентен: повторный запуск — быстрый no-op.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"

# Бэкенд: uv сам скачает Python 3.14 из requires-python, если его нет в системе.
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
  if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
    echo "export PATH=\"$HOME/.local/bin:\$PATH\"" >> "$CLAUDE_ENV_FILE"
  fi
fi
(cd "$ROOT/backend" && uv sync --frozen)

# Фронтенд: npm install (а не ci) — переиспользует node_modules из кэша контейнера.
(cd "$ROOT/frontend" && npm install --no-audit --no-fund)
