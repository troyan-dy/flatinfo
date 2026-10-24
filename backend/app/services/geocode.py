"""Геокодирование адреса через OpenStreetMap Nominatim.

Превращает свободный текст адреса в координаты + структурированный адрес
(страна, город). Результаты кэшируются в памяти (LRU), чтобы не дёргать
бесплатный публичный сервис на каждый повтор и уважать его rate-limit.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

import httpx
from loguru import logger

from app.config import settings
from app.services.throttle import AsyncRateLimiter

# Поля адреса Nominatim, из которых берём «город» — от точного к общему.
_CITY_KEYS = ("city", "town", "village", "municipality", "county", "state")

# Автодополнение: короче — не ищем, больше вариантов — не просим.
_MIN_SUGGEST_LENGTH = 3
_MAX_SUGGEST_LIMIT = 10

# Общий лимитер на все исходящие запросы к геокодеру (geocode + suggest).
_limiter = AsyncRateLimiter(settings.geocoder_min_interval)


@dataclass(frozen=True)
class GeoLocation:
    display_name: str
    lat: float
    lon: float
    country_code: str  # ISO alpha-2, нижний регистр ("ru", "de", ...)
    country: str
    city: str | None


class GeocodeError(Exception):
    """Адрес не удалось геокодировать."""


class _LRUCache(OrderedDict[str, GeoLocation]):
    """Простой LRU поверх OrderedDict — без внешних зависимостей.

    Потокобезопасен в рамках одного event loop. Размер — `settings.geocode_cache_size`.
    """

    def lookup(self, key: str) -> GeoLocation | None:
        location = self.get(key)
        if location is not None:
            self.move_to_end(key)
        return location

    def put(self, key: str, location: GeoLocation) -> None:
        self[key] = location
        self.move_to_end(key)
        while len(self) > settings.geocode_cache_size:
            self.popitem(last=False)


_cache = _LRUCache()


def _parse(place: dict[str, Any]) -> GeoLocation:
    address = place.get("address", {})
    return GeoLocation(
        display_name=place.get("display_name", ""),
        lat=float(place["lat"]),
        lon=float(place["lon"]),
        country_code=(address.get("country_code") or "").lower(),
        country=address.get("country", ""),
        city=next((address[key] for key in _CITY_KEYS if address.get(key)), None),
    )


async def _request(query: str, limit: int, client: httpx.AsyncClient | None) -> Any:
    """Один поиск в Nominatim. Ошибки сети/HTTP — `httpx.HTTPError`."""
    if client is None:
        async with httpx.AsyncClient(timeout=settings.geocoder_timeout) as own_client:
            return await _request(query, limit, own_client)

    await _limiter.wait()
    response = await client.get(
        settings.geocoder_url,
        params={
            "q": query,
            "format": "jsonv2",
            "limit": str(limit),
            "addressdetails": "1",
        },
        headers={"User-Agent": settings.geocoder_user_agent},
    )
    response.raise_for_status()
    return response.json()


async def geocode(address: str, client: httpx.AsyncClient | None = None) -> GeoLocation:
    query = address.strip()
    if not query:
        raise GeocodeError("Пустой адрес")

    cached = _cache.lookup(query.lower())
    if cached is not None:
        return cached

    try:
        places = await _request(query, 1, client)
    except httpx.HTTPError as exc:
        logger.warning("Geocoder request failed: {}", exc)
        raise GeocodeError("Сервис геокодирования недоступен") from exc

    if not places:
        raise GeocodeError(f"Не удалось найти адрес: {address}")

    location = _parse(places[0])
    _cache.put(query.lower(), location)
    return location


async def suggest(
    query: str,
    limit: int = 5,
    client: httpx.AsyncClient | None = None,
) -> list[GeoLocation]:
    """Несколько вариантов адреса для автодополнения. Ошибки → пустой список."""
    text = query.strip()
    if len(text) < _MIN_SUGGEST_LENGTH:
        return []

    try:
        places = await _request(text, max(1, min(limit, _MAX_SUGGEST_LIMIT)), client)
    except httpx.HTTPError as exc:
        logger.warning("Geocoder suggest failed: {}", exc)
        return []

    # Nominatim иногда дублирует (город + граница) — оставляем первый вариант.
    unique: dict[str, GeoLocation] = {}
    for place in places:
        if place.get("lat") and place.get("lon"):
            location = _parse(place)
            unique.setdefault(location.display_name, location)
    return list(unique.values())
