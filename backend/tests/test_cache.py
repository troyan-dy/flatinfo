"""Логика слоя кэша и его подключение в эндпоинте /analyze."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import cache
from app.services.geocode import GeoLocation


def _fake_location() -> GeoLocation:
    return GeoLocation(
        display_name="Berlin, Germany",
        lat=52.52,
        lon=13.40,
        country_code="de",
        country="Germany",
        city="Berlin",
    )


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    async def fake_geocode(address: str, client: httpx.AsyncClient | None = None) -> GeoLocation:
        return _fake_location()

    monkeypatch.setattr("app.services.advisor.geocode", fake_geocode)
    return TestClient(app)


def test_make_key_stable_and_order_independent() -> None:
    k1 = cache.make_key("analyze:v1", {"address": "berlin", "overrides": {"a": 1, "b": 2}})
    k2 = cache.make_key("analyze:v1", {"overrides": {"b": 2, "a": 1}, "address": "berlin"})
    k3 = cache.make_key("analyze:v1", {"address": "munich", "overrides": {"a": 1, "b": 2}})
    assert k1 == k2  # порядок ключей не влияет
    assert k1 != k3  # разные данные → разный ключ
    assert k1.startswith("analyze:v1:")


def test_analyze_cache_hit_skips_recompute(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    cached_body = {
        "location": {
            "display_name": "Cached City",
            "lat": 1.0,
            "lon": 2.0,
            "country": "Germany",
            "country_code": "de",
            "city": "Cached City",
        },
        "assumptions": {
            "area_sqm": 60.0,
            "home_price": 1.0,
            "monthly_rent": 1.0,
            "horizon_years": 10,
            "down_payment_pct": 0.2,
            "mortgage_rate": 0.05,
            "loan_term_years": 20,
            "property_tax_rate": 0.01,
            "maintenance_rate": 0.012,
            "home_appreciation": 0.03,
            "rent_growth": 0.03,
            "investment_return": 0.05,
            "currency": "EUR",
            "data_source": "city",
        },
        "result": {
            "recommendation": "rent",
            "horizon_years": 10,
            "buy_net_worth": 1.0,
            "rent_net_worth": 2.0,
            "advantage": 1.0,
            "advantage_pct": 0.5,
            "break_even_year": None,
            "monthly_mortgage": 1.0,
            "total_buy_cost": 1.0,
            "total_rent_cost": 1.0,
            "timeline": [],
        },
        "summary": "из кэша",
    }

    async def fake_get(key: str) -> dict[str, Any]:
        return cached_body

    async def boom(*args: object, **kwargs: object) -> None:
        raise AssertionError("run_analysis не должен вызываться при попадании в кэш")

    monkeypatch.setattr("app.api.cache.get_json", fake_get)
    monkeypatch.setattr("app.api.run_analysis", boom)

    resp = client.post("/api/analyze", json={"address": "Berlin"})
    assert resp.status_code == 200
    assert resp.json()["summary"] == "из кэша"


def test_analyze_cache_miss_stores_result(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    stored: dict[str, Any] = {}

    async def fake_get(key: str) -> None:
        return None

    async def fake_set(key: str, value: dict[str, Any], ttl: int) -> None:
        stored["key"] = key
        stored["value"] = value
        stored["ttl"] = ttl

    monkeypatch.setattr("app.api.cache.get_json", fake_get)
    monkeypatch.setattr("app.api.cache.set_json", fake_set)

    resp = client.post("/api/analyze", json={"address": "Berlin"})
    assert resp.status_code == 200
    assert stored["key"].startswith("analyze:v1:")
    assert stored["value"]["location"]["city"] == "Berlin"
    assert stored["ttl"] > 0


async def test_cache_disabled_is_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cache.settings, "cache_enabled", False)
    assert await cache.get_json("analyze:v1:whatever") is None
    await cache.set_json("analyze:v1:whatever", {"a": 1}, 60)  # не падает
