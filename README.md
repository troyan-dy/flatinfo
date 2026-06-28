# flatinfo — снимать или покупать?

Вводишь адрес — сервис говорит, что выгоднее по деньгам за годы жизни: **снимать**
жильё или **купить** в ипотеку. Сравнение честное: учитываем рост цен на недвижимость,
индексацию аренды и доход от альтернативных вложений (если не покупать — первый взнос
можно инвестировать).

## Как это работает

1. **Адрес → координаты.** Бэкенд геокодирует адрес через OpenStreetMap Nominatim,
   достаёт страну и город.
2. **Локация → рыночные оценки.** По стране/городу подбираются ориентиры: цена и
   аренда за м², ставка ипотеки, налог, рост цен и аренды, типичная доходность
   вложений (`app/market_data.py`). Если города нет в базе — берётся профиль страны,
   если и страны нет — глобальный. Честность оценки видна в подписи под расчётом.
3. **Финансовая модель.** Помесячная симуляция по методологии нетто-богатства
   (как в калькуляторе NYT «Is it better to rent or buy»): два человека с одинаковым
   бюджетом — один покупает, другой снимает и инвестирует разницу. Сравниваем итоговый
   капитал через N лет, находим точку окупаемости (`app/analysis.py`).
4. **Вердикт.** `buy` / `rent` / `neutral` + сумма выгоды + график расхождения капитала.
   Любое допущение можно переопределить — расчёт пересчитывается на сервере (SSR).

## Стек

- **Бэкенд:** FastAPI, Pydantic, httpx, loguru. Менеджер пакетов — `uv`.
  Линт/типы/тесты: ruff + mypy + pytest (покрытие ≥85%).
  Кэш ответов — Redis (необязательный: без него сервис просто пересчитывает).
- **Фронтенд:** Next.js 15 (App Router, **SSR**), React 19, TypeScript. График —
  собственный SVG без тяжёлых зависимостей.

## Запуск

```bash
# 1. Бэкенд (http://localhost:8000, /docs — Swagger)
cd backend
uv sync
uv run uvicorn app.main:app --reload

# 2. Фронтенд (http://localhost:3000)
cd frontend
npm install
npm run dev
```

Фронт ходит на бэкенд по `BACKEND_URL` (по умолчанию `http://localhost:8000`).

Бэкенд кэширует ответы `/api/analyze` в Redis по адресу `REDIS_URL`
(по умолчанию `redis://localhost:6379/0`). Redis не запущен — не страшно:
кэш тихо отключается, каждый запрос считается заново. Выключить совсем —
`CACHE_ENABLED=false`; время жизни записи — `CACHE_TTL` (сек, по умолчанию сутки).

Или всё сразу в Docker (compose поднимает и Redis):

```bash
docker compose up --build      # бэк :8000, фронт :3000, redis :6379
```

Короткие команды — в `Makefile`: `make check` (lint+types+test бэка),
`make back`, `make front`, `make dev` (docker).

## Проверки

```bash
cd backend && uv run ruff check . && uv run mypy && uv run pytest -q
cd frontend && npm run typecheck && npm run build
```

## Деплой на сервере

Прод: **https://flatinfo.duckdns.org**. На сервере сервис живёт в Docker compose
(redis + backend + frontend), а наружу смотрит общий **nginx** (reverse-proxy на
:80/:443) с сертификатом Let's Encrypt. Фронтенд и бэкенд публикуют порты только на
loopback (`127.0.0.1:3000` / `:8000`) — снаружи их закрывает nginx, который
разруливает запросы по доменному имени. Так на одном сервере уживается несколько
сайтов: каждый — свой `server`-блок, свой домен и свой внутренний порт.

```
Интернет :443 ──► nginx (TLS, по server_name) ──► 127.0.0.1:3000 (frontend) ──► backend
```

### CI/CD: образы собирает GitHub, сервер их только тянет

Сервер маленький (~1 ГБ RAM, ~10 ГБ диск) — собирать образы на нём дорого. Поэтому
сборка вынесена в **GitHub Actions** ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)):

1. На каждый push/PR гоняются проверки — бэкенд (ruff + mypy + pytest, покрытие ≥85%)
   и фронтенд (typecheck + build).
2. После зелёных проверок **на `master`** собираются и пушатся образы в
   **GHCR** (публичные, авторизация не нужна):
   `ghcr.io/troyan-dy/flatinfo-backend:latest` и `…-frontend:latest`
   (плюс метка с точным commit SHA — для отката).

На сервере используется [`docker-compose.prod.yml`](docker-compose.prod.yml): он не
собирает образы, а **тянет готовые** из GHCR. Фронтенд по-прежнему `output:
"standalone"` — лёгкий рантайм-образ ~200 МБ.

### Первая установка

Нужны Docker + плагин compose, nginx, certbot.

```bash
# 1. Код — нужен один раз, ради compose- и nginx-конфигов (репозиторий публичный)
cd ~ && git clone https://github.com/troyan-dy/flatinfo.git
cd ~/flatinfo

# 2. Поднять контейнеры из готовых образов GHCR (без локальной сборки)
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d

# 3. nginx: подключить конфиг (на старте — без TLS, см. ниже про HTTPS)
ln -s ~/flatinfo/deploy/nginx/flatinfo.conf /etc/nginx/sites-enabled/flatinfo.conf
rm -f /etc/nginx/sites-enabled/default      # убрать дефолтную заглушку nginx
nginx -t && systemctl reload nginx
```

### HTTPS (Let's Encrypt, webroot)

Конфиг [`deploy/nginx/flatinfo.conf`](deploy/nginx/flatinfo.conf) уже содержит TLS-блок
и ссылается на сертификат — поэтому `nginx -t` пройдёт только **после** первого выпуска.
Порядок на чистом сервере:

```bash
# Каталог для ACME-челленджа (его отдаёт nginx по /.well-known/acme-challenge/)
mkdir -p /var/www/certbot

# Первый выпуск через webroot (домен должен A-записью указывать на сервер).
# Конфиг сертботом не правится (без --nginx) — он остаётся источником правды в git.
certbot certonly --webroot -w /var/www/certbot -d flatinfo.duckdns.org \
  --non-interactive --agree-tos -m you@example.com \
  --deploy-hook "systemctl reload nginx"

nginx -t && systemctl reload nginx   # теперь TLS-конфиг валиден
```

Продление автоматическое — таймер `certbot.timer` запускает `certbot renew`; webroot
не требует простоя, `--deploy-hook` перезагружает nginx после обновления сертификата.
Проверить: `certbot renew --dry-run`.

### Файрвол

Наружу открыты только SSH и web; всё остальное (включая loopback-порты контейнеров)
недоступно из интернета:

```bash
ufw allow OpenSSH && ufw allow 'Nginx Full' && ufw --force enable
```

### Авто-деплой (cron)

[`deploy/auto-update.sh`](deploy/auto-update.sh) раз в несколько минут тянет свежие
образы из GHCR и, **только если они изменились**, пересоздаёт контейнеры
(`docker compose -f docker-compose.prod.yml pull && up -d`). Никакой сборки и `git`
на сервере: образы готовит CI. Если образы те же — тихо выходит. Защищён `flock` от
наложения запусков, пишет в `deploy/auto-update.log`.

```bash
crontab -e
```

```cron
PATH=/usr/local/bin:/usr/bin:/bin
*/5 * * * * /root/flatinfo/deploy/auto-update.sh >> /root/flatinfo/deploy/cron.log 2>&1
```

Строка `PATH=...` обязательна — окружение cron урезанное, иначе не найдутся
`docker`/`git`/`flock`. Проверить, что обновления приходят: `tail -f
~/flatinfo/deploy/auto-update.log`.

## Дисклеймер

Рыночные цифры — приблизительные ориентиры, а не онлайн-котировки (бесплатного
глобального API цен на жильё нет). Для точного решения подставьте реальные цену,
аренду и ставку в блоке «Допущения расчёта». Это оценка, а не инвестиционный совет.
