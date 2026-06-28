"""Геокодирование адреса через OpenStreetMap Nominatim.

Превращает свободный текст адреса в координаты + структурированный адрес
(страна, город). Результаты кэшируются в памяти (LRU), чтобы не дёргать
бесплатный публичный сервис на каждый повтор и уважать его rate-limit.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass

import httpx
from loguru import logger

from app.config import settings


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


# Простой LRU поверх OrderedDict — без внешних зависимостей и потокобезопасно
# в рамках одного event loop.
_cache: OrderedDict[str, GeoLocation] = OrderedDict()


def _cache_get(key: str) -> GeoLocation | None:
    if key in _cache:
        _cache.move_to_end(key)
        return _cache[key]
    return None


def _cache_put(key: str, value: GeoLocation) -> None:
    _cache[key] = value
    _cache.move_to_end(key)
    while len(_cache) > settings.geocode_cache_size:
        _cache.popitem(last=False)


def _pick_city(address: dict[str, str]) -> str | None:
    for key in ("city", "town", "village", "municipality", "county", "state"):
        if address.get(key):
            return address[key]
    return None


def _parse(item: dict) -> GeoLocation:
    address = item.get("address", {})
    return GeoLocation(
        display_name=item.get("display_name", ""),
        lat=float(item["lat"]),
        lon=float(item["lon"]),
        country_code=(address.get("country_code") or "").lower(),
        country=address.get("country", ""),
        city=_pick_city(address),
    )


async def geocode(address: str, client: httpx.AsyncClient | None = None) -> GeoLocation:
    query = address.strip()
    if not query:
        raise GeocodeError("Пустой адрес")

    cached = _cache_get(query.lower())
    if cached is not None:
        return cached

    params = {
        "q": query,
        "format": "jsonv2",
        "limit": "1",
        "addressdetails": "1",
    }
    headers = {"User-Agent": settings.geocoder_user_agent}

    own_client = client is None
    client = client or httpx.AsyncClient(timeout=settings.geocoder_timeout)
    try:
        resp = await client.get(settings.geocoder_url, params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as exc:
        logger.warning("Geocoder request failed: {}", exc)
        raise GeocodeError("Сервис геокодирования недоступен") from exc
    finally:
        if own_client:
            await client.aclose()

    if not data:
        raise GeocodeError(f"Не удалось найти адрес: {address}")

    location = _parse(data[0])
    _cache_put(query.lower(), location)
    return location
