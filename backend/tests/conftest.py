import pytest

from app.services import geocode as geo


@pytest.fixture(autouse=True)
def _disable_throttle() -> None:
    """В тестах не ждём интервал между запросами к геокодеру."""
    geo._limiter.min_interval = 0.0
