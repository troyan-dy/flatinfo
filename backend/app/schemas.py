"""Pydantic-схемы запроса/ответа API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Overrides(BaseModel):
    """Необязательные ручные правки допущений. Любое поле может быть None."""

    area_sqm: float | None = Field(default=None, gt=5, le=1000)
    horizon_years: int | None = Field(default=None, ge=1, le=40)
    home_price: float | None = Field(default=None, gt=0)
    monthly_rent: float | None = Field(default=None, gt=0)
    down_payment_pct: float | None = Field(default=None, ge=0, le=1)
    mortgage_rate: float | None = Field(default=None, ge=0, le=1)
    loan_term_years: int | None = Field(default=None, ge=1, le=40)
    property_tax_rate: float | None = Field(default=None, ge=0, le=0.2)
    maintenance_rate: float | None = Field(default=None, ge=0, le=0.2)
    home_appreciation: float | None = Field(default=None, ge=-0.2, le=1)
    rent_growth: float | None = Field(default=None, ge=-0.2, le=1)
    investment_return: float | None = Field(default=None, ge=-0.2, le=1)


class AnalyzeRequest(BaseModel):
    address: str = Field(min_length=2, max_length=300)
    overrides: Overrides = Field(default_factory=Overrides)


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
    result: ResultOut
    summary: str  # человекочитаемый вывод на русском
