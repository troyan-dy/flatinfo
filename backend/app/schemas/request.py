"""Pydantic-схемы запросов API."""

from __future__ import annotations

from pydantic import BaseModel, Field

MAX_ADDRESS_LENGTH = 300
MIN_AREA_SQM = 5
MAX_AREA_SQM = 1000
MAX_YEARS = 40  # горизонт и срок ипотеки, лет
MAX_COST_RATE = 0.2  # налог/содержание: не больше 20% стоимости в год
MIN_GROWTH_RATE = -0.2  # рост цен/аренды/доходность: не ниже −20% годовых


class Overrides(BaseModel):
    """Необязательные ручные правки допущений. Любое поле может быть None."""

    area_sqm: float | None = Field(default=None, gt=MIN_AREA_SQM, le=MAX_AREA_SQM)
    horizon_years: int | None = Field(default=None, ge=1, le=MAX_YEARS)
    home_price: float | None = Field(default=None, gt=0)
    monthly_rent: float | None = Field(default=None, gt=0)
    down_payment_pct: float | None = Field(default=None, ge=0, le=1)
    mortgage_rate: float | None = Field(default=None, ge=0, le=1)
    loan_term_years: int | None = Field(default=None, ge=1, le=MAX_YEARS)
    property_tax_rate: float | None = Field(default=None, ge=0, le=MAX_COST_RATE)
    maintenance_rate: float | None = Field(default=None, ge=0, le=MAX_COST_RATE)
    home_appreciation: float | None = Field(default=None, ge=MIN_GROWTH_RATE, le=1)
    rent_growth: float | None = Field(default=None, ge=MIN_GROWTH_RATE, le=1)
    investment_return: float | None = Field(default=None, ge=MIN_GROWTH_RATE, le=1)


class AnalyzeRequest(BaseModel):
    address: str = Field(min_length=2, max_length=MAX_ADDRESS_LENGTH)
    overrides: Overrides = Field(default_factory=Overrides)
