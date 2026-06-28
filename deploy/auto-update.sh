#!/usr/bin/env bash
#
# Авто-деплой: тянет master с GitHub и, если код изменился, пересобирает и
# пересоздаёт контейнеры compose. redis эфемерный (тома нет) — пересоздание
# безопасно, всё пересчитается. Запускается из cron раз в несколько минут.
# Идемпотентен: если новых коммитов нет — тихо выходит, ничего не трогая.
#
set -euo pipefail

# Директория проекта = на уровень выше папки deploy/, где лежит этот скрипт.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

BRANCH="master"
LOG="$SCRIPT_DIR/auto-update.log"
LOCK="$SCRIPT_DIR/.auto-update.lock"

log() { echo "[$(date '+%F %T')] $*" >>"$LOG"; }

# Защита от наложения запусков: если предыдущий ещё идёт (долгая сборка) — выходим.
exec 9>"$LOCK"
if ! flock -n 9; then
  log "previous run still in progress, skip"
  exit 0
fi

# Тянем с GitHub, не меняя рабочую копию.
git fetch --quiet origin "$BRANCH"

LOCAL="$(git rev-parse HEAD)"
REMOTE="$(git rev-parse "origin/$BRANCH")"

# Код не изменился — обычный случай, выходим тихо (лог не засоряем).
if [ "$LOCAL" = "$REMOTE" ]; then
  exit 0
fi

log "update detected: ${LOCAL:0:7} -> ${REMOTE:0:7}"

# Только fast-forward — никаких случайных merge-коммитов на сервере.
git pull --ff-only --quiet origin "$BRANCH"

# Пересобрать образы и пересоздать изменившиеся сервисы (backend/frontend/redis).
log "rebuilding and restarting containers..."
docker compose up -d --build >>"$LOG" 2>&1

log "done, now at $(git rev-parse --short HEAD)"

# Подчистить висячие образы от прошлых сборок, чтобы не копился мусор.
docker image prune -f >>"$LOG" 2>&1 || true
