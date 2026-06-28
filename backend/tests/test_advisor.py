import httpx
import pytest

from app.schemas import AnalyzeRequest, Overrides
from app.services import geocode as geocode_mod
from app.services.advisor import build_summary, run_analysis
from app.services.geocode import GeoLocation


@pytest.fixture
def patched_geocode(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_geocode(address: str, client: httpx.AsyncClient | None = None) -> GeoLocation:
        return GeoLocation(
            display_name="Москва, Россия",
            lat=55.75,
            lon=37.62,
            country_code="ru",
            country="Россия",
            city="Москва",
        )

    monkeypatch.setattr("app.services.advisor.geocode", fake_geocode)
    monkeypatch.setattr(geocode_mod, "geocode", fake_geocode)


async def test_run_analysis_end_to_end(patched_geocode: None) -> None:
    req = AnalyzeRequest(address="Москва, Тверская 1")
    resp = await run_analysis(req)
    assert resp.location.city == "Москва"
    assert resp.assumptions.currency == "RUB"
    assert resp.assumptions.data_source == "city"
    assert resp.result.recommendation in {"buy", "rent", "neutral"}
    assert len(resp.result.timeline) == resp.assumptions.horizon_years
    assert resp.summary


async def test_overrides_applied(patched_geocode: None) -> None:
    req = AnalyzeRequest(
        address="Москва",
        overrides=Overrides(area_sqm=100, horizon_years=5, mortgage_rate=0.05),
    )
    resp = await run_analysis(req)
    assert resp.assumptions.area_sqm == 100
    assert resp.assumptions.horizon_years == 5
    assert resp.assumptions.mortgage_rate == 0.05
    assert len(resp.result.timeline) == 5


def test_build_summary_variants() -> None:
    assert "покупка выгоднее" in build_summary("buy", 100_000, 10, 3, "RUB").lower()
    assert "аренда выгоднее" in build_summary("rent", 100_000, 10, None, "RUB").lower()
    assert "сопоставим" in build_summary("neutral", 1_000, 10, 1, "RUB").lower()
