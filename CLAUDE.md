# flatinfo — «снимать или покупать» по адресу

Сервис по адресу жилья отвечает, что выгоднее **по деньгам** за горизонт проживания:
снимать или брать в ипотеку. Бэкенд (FastAPI) считает, фронтенд (Next.js, SSR) показывает.

## Поток

`backend/app/services/advisor.py::run_analysis(req)` — один расчёт:
1. `services/geocode.geocode(address)` — адрес → координаты + страна/город
   (OpenStreetMap Nominatim, LRU-кэш в памяти). Пусто/недоступно → `GeocodeError` → 422.
2. `services/market.estimate_for(location)` — локация → `MarketEstimate`:
   цена/аренда за м², ставки. Уточнение сверху вниз: город (`CITY`) → страна
   (`COUNTRY`) → глобальный профиль (`GLOBAL_FALLBACK`). Поле `source` сообщает
   точность оценки.
3. `services/advisor.build_assumptions(est, overrides)` — собирает `Assumptions`:
   цена = цена_за_м² × площадь, аренда аналогично; пользовательские `overrides`
   перекрывают любые дефолты.
4. `analysis.analyze(assumptions)` — помесячная симуляция нетто-богатства, см. ниже.
5. Ответ `AnalyzeResponse`: локация + допущения + результат + человекочитаемый `summary`.

## Финансовая модель (`backend/app/analysis.py`)

Методология нетто-богатства (как калькулятор NYT). Два человека, **одинаковый бюджет**:
- **Покупатель** тратит кэш на первый взнос + издержки сделки (портфель = 0), платит
  ипотеку/налог/содержание. Жильё дорожает.
- **Арендатор** тот же кэш инвестирует (стартовый портфель), платит аренду.
- **Каждый месяц** у кого расходы ниже — разницу инвестирует под `investment_return`.
  Оба портфеля растут по этой же ставке.
- На конец горизонта: богатство покупателя = портфель + чистый капитал в жилье
  (стоимость − издержки продажи − остаток кредита); арендатора = портфель.

`recommendation`: разница итогового богатства < 3% цены → `neutral`, иначе `buy`/`rent`.
`break_even_year` — первый год, когда покупатель догоняет арендатора (или `None`).
Ставки везде **годовые доли** (0.05 = 5%); месячные считаются геометрически.

## Архитектура

- `backend/app/` — `config.py` (pydantic-settings), `analysis.py` (модель, без I/O),
  `market_data.py` (таблицы стран/городов), `schemas.py` (Pydantic API),
  `api.py` (роуты `/api/health`, `/api/analyze`), `services/` (geocode, market, advisor,
  cache), `main.py` (FastAPI + CORS + lifespan для закрытия пула Redis).
- Кэш ответов: `services/cache.py` — обёртка над `redis.asyncio`. Эндпоинт
  `/api/analyze` кэширует весь `AnalyzeResponse` по ключу `analyze:v1:<sha256>` от
  нормализованного запроса (адрес без регистра + overrides); расчёт детерминирован,
  потому ответ кэшируем целиком. Redis **необязателен**: любая ошибка соединения
  проглатывается (`redis_url`, `cache_enabled`, `cache_ttl` в `config.py`) — сервис
  считает заново. Меняешь формулу/данные так, что старый кэш невалиден → подними
  версию в префиксе ключа (`analyze:v1` → `analyze:v2`).
- `frontend/app/` — `page.tsx` (**server component, SSR**: читает `searchParams`,
  зовёт бэкенд, рендерит вердикт), `NetWorthChart.tsx` (клиентский SVG-график),
  `AssumptionsForm.tsx` (клиентская форма допущений → пуш в URL → пересчёт на сервере).
  `lib/` — `api.ts` (вызов бэкенда), `types.ts`, `format.ts` (деньги/проценты).
- Состояние расчёта живёт **в URL** (`?address=...&mortgage_rate=...`): расчёт всегда
  на сервере, ссылку можно расшарить.

## Команды

```bash
# бэкенд
cd backend && uv sync
uv run uvicorn app.main:app --reload      # http://localhost:8000, /docs
uv run ruff check . && uv run mypy && uv run pytest -q

# фронтенд
cd frontend && npm install
npm run dev                                # http://localhost:3000
npm run typecheck && npm run build
```

## Договорённости

- Комментарии и тексты UI — на русском. Деньги — в локальной валюте страны (символ
  подбирается в `lib/format.ts`).
- Рыночные данные — **оценки**, не котировки. Любую цифру пользователь правит руками;
  это не инвестиционный совет. При добавлении страны/города правим `market_data.py`
  и (если новая валюта) `SYMBOLS` в `lib/format.ts`.
- npm-реестр: при недоступности корпоративного `artifactory.s.o3.ru` ставим из
  публичного (`frontend/.npmrc` → `registry.npmjs.org`).
