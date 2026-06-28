import pytest

from app.config import settings
from app.services import geocode as geo


@pytest.fixture(autouse=True)
def _disable_throttle() -> None:
    """В тестах не ждём интервал между запросами к геокодеру."""
    geo._limiter.min_interval = 0.0


@pytest.fixture(autouse=True)
def _disable_cache() -> None:
    """По умолчанию тесты бегут без Redis. Тесты кэша включают его сами."""
    settings.cache_enabled = False
