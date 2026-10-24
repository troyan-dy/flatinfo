import asyncio
import time

from app.services.throttle import AsyncRateLimiter

_NO_WAIT = 0.05  # сек: «без ожидания» с запасом на планировщик
_MIN_ELAPSED = 0.045  # сек: интервал 0.05 минус погрешность таймера


async def test_zero_interval_no_wait() -> None:
    limiter = AsyncRateLimiter(0)
    start = time.monotonic()
    await asyncio.gather(*(limiter.wait() for _ in range(5)))
    assert time.monotonic() - start < _NO_WAIT


async def test_enforces_min_interval() -> None:
    limiter = AsyncRateLimiter(0.05)
    start = time.monotonic()
    await limiter.wait()  # первый — без ожидания
    await limiter.wait()  # второй — ждёт ~0.05s
    elapsed = time.monotonic() - start
    assert elapsed >= _MIN_ELAPSED
