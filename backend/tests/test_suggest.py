import httpx

from app.services import geocode as geo


def _client(handler: object) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))  # type: ignore[arg-type]


async def test_suggest_returns_multiple() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[
                {
                    "display_name": "Москва, Россия",
                    "lat": "55.75",
                    "lon": "37.62",
                    "address": {"city": "Москва", "country_code": "ru"},
                },
                {
                    "display_name": "Московская область",
                    "lat": "55.5",
                    "lon": "38.0",
                    "address": {"state": "Московская область", "country_code": "ru"},
                },
            ],
        )

    async with _client(handler) as client:
        res = await geo.suggest("Моск", client=client)
        assert len(res) == 2
        assert res[0].city == "Москва"


async def test_suggest_too_short_returns_empty() -> None:
    res = await geo.suggest("Мо")
    assert res == []


async def test_suggest_http_error_returns_empty() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    async with _client(handler) as client:
        res = await geo.suggest("Берлин", client=client)
        assert res == []


async def test_suggest_skips_items_without_coords() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[
                {"display_name": "no coords", "address": {"country_code": "ru"}},
                {
                    "display_name": "ok",
                    "lat": "1",
                    "lon": "2",
                    "address": {"country_code": "ru"},
                },
            ],
        )

    async with _client(handler) as client:
        res = await geo.suggest("test", client=client)
        assert len(res) == 1
        assert res[0].display_name == "ok"
