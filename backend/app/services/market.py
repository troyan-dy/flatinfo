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

from app.market_data import CITY, COUNTRY, GLOBAL_FALLBACK, CountryProfile
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


def estimate_for(location: GeoLocation) -> MarketEstimate:
    cc = location.country_code
    profile: CountryProfile = COUNTRY.get(cc, GLOBAL_FALLBACK)
    source = "country" if cc in COUNTRY else "global"

    buy = profile.buy_per_sqm
    rent = profile.rent_per_sqm
    matched_city: str | None = None

    if location.city:
        key = (cc, _normalize(location.city))
        if key in CITY:
            buy, rent = CITY[key]
            source = "city"
            matched_city = location.city

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
        source=source,
        matched_city=matched_city,
        matched_country=location.country or (cc.upper() if cc else None),
    )
