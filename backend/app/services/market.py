"""Подбор рыночных оценок (цена/аренда за м², экономические ставки) по локации.

Логика уточнения сверху вниз:
1. Город известен → берём цена/аренда за м² из CITY, ставки — из профиля страны.
2. Город неизвестен, но страна есть → всё из профиля страны.
3. Страна неизвестна → глобальный запасной профиль.

`source` сообщает фронту, насколько точечная оценка ("city"/"country"/"global"),
чтобы честно подписать степень достоверности.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.market_data import CITY, COUNTRY, GLOBAL_FALLBACK
from app.services.geocode import GeoLocation


@dataclass(frozen=True)
class MarketEstimate:
    currency: str
    buy_per_sqm: float
    rent_per_sqm: float
    mortgage_rate: float
    property_tax_rate: float
    home_appreciation: float
    rent_growth: float
    investment_return: float
    buy_closing_pct: float
    sell_closing_pct: float
    source: str  # "city" | "country" | "global"
    matched_city: str | None
    matched_country: str | None


def _normalize(name: str) -> str:
    return name.strip().lower()


def _city_prices(location: GeoLocation) -> tuple[float, float] | None:
    """Цена и аренда за м² из CITY, если город известен базе."""
    if not location.city:
        return None
    return CITY.get((location.country_code, _normalize(location.city)))


def _source(country_code: str, city_prices: tuple[float, float] | None) -> str:
    if city_prices is not None:
        return "city"
    if country_code in COUNTRY:
        return "country"
    return "global"


def _country_label(location: GeoLocation) -> str | None:
    if location.country:
        return location.country
    if location.country_code:
        return location.country_code.upper()
    return None


def estimate_for(location: GeoLocation) -> MarketEstimate:
    profile = COUNTRY.get(location.country_code, GLOBAL_FALLBACK)
    city_prices = _city_prices(location)
    buy, rent = city_prices or (profile.buy_per_sqm, profile.rent_per_sqm)
    return MarketEstimate(
        currency=profile.currency,
        buy_per_sqm=buy,
        rent_per_sqm=rent,
        mortgage_rate=profile.mortgage_rate,
        property_tax_rate=profile.property_tax_rate,
        home_appreciation=profile.home_appreciation,
        rent_growth=profile.rent_growth,
        investment_return=profile.investment_return,
        buy_closing_pct=profile.buy_closing_pct,
        sell_closing_pct=profile.sell_closing_pct,
        source=_source(location.country_code, city_prices),
        matched_city=None if city_prices is None else location.city,
        matched_country=_country_label(location),
    )
