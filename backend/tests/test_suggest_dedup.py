import httpx

from app.services import geocode as geo


def _client(handler: object) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))  # type: ignore[arg-type]


async def test_suggest_dedupes_by_display_name() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        item = {
            "display_name": "Amsterdam, Noord-Holland, Nederland",
            "lat": "52.37",
            "lon": "4.89",
            "address": {"city": "Amsterdam", "country_code": "nl"},
        }
        return httpx.Response(200, json=[item, dict(item), {**item, "display_name": "Other"}])

    async with _client(handler) as client:
        res = await geo.suggest("Amsterdam", client=client)
        names = [r.display_name for r in res]
        assert names == ["Amsterdam, Noord-Holland, Nederland", "Other"]
