"""Кэш ответов в Redis.

Необязательный слой: успешный ответ `/api/analyze` детерминирован по запросу
(геокод + рыночные оценки + модель — без случайностей), поэтому его можно
закэшировать целиком. При недоступности Redis сервис продолжает работать без
кэша — любые ошибки соединения проглатываются, расчёт просто выполняется заново.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from loguru import logger
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.config import settings

_redis: Redis | None = None
_warned = False


def _client() -> Redis | None:
    """Ленивый общий клиент. None, если кэш выключен."""
    global _redis
    if not settings.cache_enabled:
        return None
    if _redis is None:
        _redis = Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=settings.cache_socket_timeout,
            socket_timeout=settings.cache_socket_timeout,
        )
    return _redis


def _warn(exc: Exception) -> None:
    # Шумит один раз: недоступный Redis не должен заваливать лог на каждый запрос.
    global _warned
    if not _warned:
        logger.warning("Redis недоступен, работаем без кэша: {}", exc)
        _warned = True


def make_key(prefix: str, payload: dict[str, Any]) -> str:
    """Стабильный ключ из полезной нагрузки (порядок полей не важен)."""
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    digest = hashlib.sha256(blob.encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"


async def get_json(key: str) -> dict[str, Any] | None:
    client = _client()
    if client is None:
        return None
    try:
        raw = await client.get(key)
    except RedisError as exc:
        _warn(exc)
        return None
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


async def set_json(key: str, value: dict[str, Any], ttl: int) -> None:
    client = _client()
    if client is None:
        return
    try:
        await client.set(key, json.dumps(value, ensure_ascii=False, default=str), ex=ttl)
    except RedisError as exc:
        _warn(exc)


async def close() -> None:
    """Закрыть пул соединений (вызывается на остановке приложения)."""
    global _redis
    if _redis is not None:
        try:
            await _redis.aclose()
        except RedisError:
            pass
        _redis = None
