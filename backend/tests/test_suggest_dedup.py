import httpx

from app.services import geocode as geo


def _client(responder: object) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(responder))  # type: ignore[arg-type]


async def test_suggest_dedupes_by_display_name() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        place = {
            "display_name": "Amsterdam, Noord-Holland, Nederland",
            "lat": "52.37",
            "lon": "4.89",
            "address": {"city": "Amsterdam", "country_code": "nl"},
        }
        other = {**place, "display_name": "Other"}
        return httpx.Response(200, json=[place, dict(place), other])

    async with _client(respond) as client:
        res = await geo.suggest("Amsterdam", client=client)
        names = [location.display_name for location in res]
        assert names == ["Amsterdam, Noord-Holland, Nederland", "Other"]
