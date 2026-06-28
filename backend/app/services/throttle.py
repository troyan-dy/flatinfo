"""Асинхронный троттлер: не чаще N запросов в секунду к внешнему сервису.

Nominatim (публичный) требует не больше 1 запроса в секунду. Кэш и дебаунс на
клиенте снимают большую часть нагрузки, но финальный предохранитель держим здесь —
сериализуем исходящие запросы с минимальным интервалом между ними.
"""

from __future__ import annotations

import asyncio
import time


class AsyncRateLimiter:
    def __init__(self, min_interval: float) -> None:
        self.min_interval = min_interval
        self._lock = asyncio.Lock()
        self._last = 0.0

    async def wait(self) -> None:
        if self.min_interval <= 0:
            return
        async with self._lock:
            now = time.monotonic()
            delay = self._last + self.min_interval - now
            if delay > 0:
                await asyncio.sleep(delay)
            self._last = time.monotonic()
