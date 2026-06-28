import time

from app.services.throttle import AsyncRateLimiter


async def test_zero_interval_no_wait() -> None:
    limiter = AsyncRateLimiter(0.0)
    start = time.monotonic()
    for _ in range(5):
        await limiter.wait()
    assert time.monotonic() - start < 0.05


async def test_enforces_min_interval() -> None:
    limiter = AsyncRateLimiter(0.05)
    start = time.monotonic()
    await limiter.wait()  # первый — без ожидания
    await limiter.wait()  # второй — ждёт ~0.05s
    elapsed = time.monotonic() - start
    assert elapsed >= 0.045
