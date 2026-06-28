from app.services.geocode import GeoLocation
from app.services.market import estimate_for


def _loc(cc: str, city: str | None) -> GeoLocation:
    return GeoLocation(
        display_name="x", lat=0.0, lon=0.0, country_code=cc, country=cc.upper(), city=city
    )


def test_city_match_wins() -> None:
    est = estimate_for(_loc("ru", "Москва"))
    assert est.source == "city"
    assert est.matched_city == "Москва"
    assert est.currency == "RUB"


def test_country_fallback() -> None:
    est = estimate_for(_loc("de", "Kleinstadt"))
    assert est.source == "country"
    assert est.currency == "EUR"


def test_global_fallback_unknown_country() -> None:
    est = estimate_for(_loc("zz", None))
    assert est.source == "global"
    assert est.currency == "USD"


def test_city_normalization_case_insensitive() -> None:
    est = estimate_for(_loc("us", "NEW YORK"))
    assert est.source == "city"
