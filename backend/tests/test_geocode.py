import httpx
import pytest

from app.services import geocode as geo


@pytest.fixture(autouse=True)
def clear_cache() -> None:
    geo._cache.clear()


def _client(handler: object) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))  # type: ignore[arg-type]


async def test_geocode_parses_and_caches() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(
            200,
            json=[
                {
                    "display_name": "Москва, Россия",
                    "lat": "55.75",
                    "lon": "37.62",
                    "address": {
                        "city": "Москва",
                        "country": "Россия",
                        "country_code": "ru",
                    },
                }
            ],
        )

    async with _client(handler) as client:
        loc = await geo.geocode("Москва, Тверская 1", client=client)
        assert loc.city == "Москва"
        assert loc.country_code == "ru"
        assert loc.lat == 55.75
        # второй вызов берётся из кэша — запрос не уходит
        await geo.geocode("Москва, Тверская 1", client=client)
    assert calls["n"] == 1


async def test_geocode_empty_address_raises() -> None:
    with pytest.raises(geo.GeocodeError):
        await geo.geocode("   ")


async def test_geocode_not_found_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[])

    async with _client(handler) as client:
        with pytest.raises(geo.GeocodeError):
            await geo.geocode("nowhere-xyz", client=client)


async def test_geocode_http_error_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    async with _client(handler) as client:
        with pytest.raises(geo.GeocodeError):
            await geo.geocode("boom", client=client)


async def test_geocode_city_fallback_fields() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[
                {
                    "display_name": "Some village",
                    "lat": "1.0",
                    "lon": "2.0",
                    "address": {"village": "Малое", "country_code": "ru"},
                }
            ],
        )

    async with _client(handler) as client:
        loc = await geo.geocode("деревня", client=client)
        assert loc.city == "Малое"
        assert loc.country == ""


async def test_cache_eviction(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "geocode_cache_size", 2)
    geo._cache.clear()
    for i in range(3):
        geo._cache_put(f"k{i}", object())  # type: ignore[arg-type]
    assert len(geo._cache) == 2
    assert "k0" not in geo._cache
