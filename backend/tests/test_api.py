import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.geocode import GeoLocation


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    async def fake_geocode(address: str, client: httpx.AsyncClient | None = None) -> GeoLocation:
        if "fail" in address:
            from app.services.geocode import GeocodeError

            raise GeocodeError("Не удалось найти адрес")
        return GeoLocation(
            display_name="Berlin, Germany",
            lat=52.52,
            lon=13.40,
            country_code="de",
            country="Germany",
            city="Berlin",
        )

    monkeypatch.setattr("app.services.advisor.geocode", fake_geocode)
    return TestClient(app)


def test_health(client: TestClient) -> None:
    assert client.get("/api/health").json() == {"status": "ok"}


def test_analyze_ok(client: TestClient) -> None:
    resp = client.post("/api/analyze", json={"address": "Berlin, Alexanderplatz"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["location"]["city"] == "Berlin"
    assert body["assumptions"]["currency"] == "EUR"
    assert body["result"]["recommendation"] in {"buy", "rent", "neutral"}


def test_analyze_geocode_failure_returns_422(client: TestClient) -> None:
    resp = client.post("/api/analyze", json={"address": "fail-address"})
    assert resp.status_code == 422


def test_analyze_validation_short_address(client: TestClient) -> None:
    resp = client.post("/api/analyze", json={"address": "x"})
    assert resp.status_code == 422
