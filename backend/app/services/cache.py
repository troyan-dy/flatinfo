"""Кэш ответов в Redis.

Необязательный слой: успешный ответ `/api/analyze` детерминирован по запросу
(геокод + рыночные оценки + модель — без случайностей), поэтому его можно
закэшировать целиком. При недоступности Redis сервис продолжает работать без
кэша — любые ошибки соединения проглатываются, расчёт просто выполняется заново.
"""

from __future__ import annotations

import hashlib
import json
from contextlib import suppress
from typing import Any

from loguru import logger
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.config import settings


class _Connection:
    """Ленивый общий клиент Redis и флаг «о недоступности уже предупредили»."""

    def __init__(self) -> None:
        self.redis: Redis | None = None
        self.warned = False

    def client(self) -> Redis | None:
        """Общий клиент. None, если кэш выключен."""
        if not settings.cache_enabled:
            return None
        if self.redis is None:
            self.redis = Redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=settings.cache_socket_timeout,
                socket_timeout=settings.cache_socket_timeout,
            )
        return self.redis

    def warn(self, exc: Exception) -> None:
        """Шумит один раз: недоступный Redis не должен заваливать лог на каждый запрос."""
        if not self.warned:
            logger.warning("Redis недоступен, работаем без кэша: {}", exc)
            self.warned = True

    async def close(self) -> None:
        if self.redis is not None:
            with suppress(RedisError):
                await self.redis.aclose()
            self.redis = None


_connection = _Connection()


def make_key(prefix: str, payload: dict[str, Any]) -> str:
    """Стабильный ключ из полезной нагрузки (порядок полей не важен)."""
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    digest = hashlib.sha256(blob.encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"


async def get_json(key: str) -> dict[str, Any] | None:
    client = _connection.client()
    if client is None:
        return None
    try:
        raw = await client.get(key)
    except RedisError as exc:
        _connection.warn(exc)
        return None
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


async def set_json(key: str, document: dict[str, Any], ttl: int) -> None:
    client = _connection.client()
    if client is None:
        return
    blob = json.dumps(document, ensure_ascii=False, default=str)
    try:
        await client.set(key, blob, ex=ttl)
    except RedisError as exc:
        _connection.warn(exc)


async def close() -> None:
    """Закрыть пул соединений (вызывается на остановке приложения)."""
    await _connection.close()
