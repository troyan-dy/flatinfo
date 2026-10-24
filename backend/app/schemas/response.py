"""Pydantic-схемы ответов API."""

from __future__ import annotations

from pydantic import BaseModel


class Suggestion(BaseModel):
    display_name: str
    lat: float
    lon: float
    city: str | None


class LocationOut(BaseModel):
    display_name: str
    lat: float
    lon: float
    country: str
    country_code: str
    city: str | None


class AssumptionsOut(BaseModel):
    area_sqm: float
    home_price: float
    monthly_rent: float
    horizon_years: int
    down_payment_pct: float
    mortgage_rate: float
    loan_term_years: int
    property_tax_rate: float
    maintenance_rate: float
    home_appreciation: float
    rent_growth: float
    investment_return: float
    currency: str
    data_source: str  # "city" | "country" | "global"


class YearPointOut(BaseModel):
    year: int
    buy_net_worth: float
    rent_net_worth: float
    home_value: float
    loan_balance: float
    home_equity: float


class ResultOut(BaseModel):
    recommendation: str
    horizon_years: int
    buy_net_worth: float
    rent_net_worth: float
    advantage: float
    advantage_pct: float
    break_even_year: int | None
    monthly_mortgage: float
    total_buy_cost: float
    total_rent_cost: float
    timeline: list[YearPointOut]


class AnalyzeResponse(BaseModel):
    location: LocationOut
    assumptions: AssumptionsOut
    # Имя поля — часть публичного JSON-контракта /api/analyze (фронт читает `result`).
    result: ResultOut  # noqa: WPS110
    summary: str  # человекочитаемый вывод на русском
