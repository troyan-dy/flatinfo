#!/usr/bin/env bash
#
# Авто-деплой: тянет свежие образы из GHCR и, ТОЛЬКО если они изменились,
# пересоздаёт контейнеры из docker-compose.prod.yml. Сборки на сервере больше
# нет — образы собирает GitHub Actions (.github/workflows/ci.yml). redis
# эфемерный (тома нет) — пересоздание безопасно, всё пересчитается.
#
# Запускается из cron раз в несколько минут. Идемпотентен: образы не менялись —
# тихо выходит, ничего не трогая. git здесь не используется: docker-compose.prod.yml
# кладётся на сервер один раз при установке (git clone), дальше нужны лишь образы.
#
set -euo pipefail

# Директория проекта = на уровень выше папки deploy/, где лежит этот скрипт.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

COMPOSE=(docker compose -f docker-compose.prod.yml)
LOG="$SCRIPT_DIR/auto-update.log"
LOCK="$SCRIPT_DIR/.auto-update.lock"

log() { echo "[$(date '+%F %T')] $*" >>"$LOG"; }

# Защита от наложения запусков: если предыдущий pull ещё идёт — выходим.
exec 9>"$LOCK"
if ! flock -n 9; then
  log "previous run still in progress, skip"
  exit 0
fi

# Имена образов из compose-файла и их текущие локальные ID — снимок «до».
images="$("${COMPOSE[@]}" config --images)"
before="$(docker image inspect --format '{{.Id}}' $images 2>/dev/null | sort || true)"

# Тянем свежие образы из реестра (тихо).
"${COMPOSE[@]}" pull --quiet >>"$LOG" 2>&1

after="$(docker image inspect --format '{{.Id}}' $images 2>/dev/null | sort || true)"

# Образы не изменились — обычный случай, выходим тихо (лог не засоряем).
if [ "$before" = "$after" ]; then
  exit 0
fi

log "new images pulled, recreating containers..."
"${COMPOSE[@]}" up -d >>"$LOG" 2>&1
log "done"

# Подчистить висячие образы от прошлых версий, чтобы не копился мусор на диске.
docker image prune -f >>"$LOG" 2>&1 || true
