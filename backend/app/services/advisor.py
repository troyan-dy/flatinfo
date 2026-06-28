"""Оркестрация: адрес → геокод → рыночные оценки → финансовая модель → ответ."""

from __future__ import annotations

import httpx

from app.analysis import Assumptions, analyze
from app.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    AssumptionsOut,
    LocationOut,
    Overrides,
    ResultOut,
    YearPointOut,
)
from app.services.geocode import geocode
from app.services.market import MarketEstimate, estimate_for

DEFAULT_AREA_SQM = 60.0
DEFAULT_HORIZON_YEARS = 10
DEFAULT_DOWN_PAYMENT_PCT = 0.20
DEFAULT_LOAN_TERM_YEARS = 20
DEFAULT_MAINTENANCE_RATE = 0.012


def _pick(value: float | None, fallback: float) -> float:
    return value if value is not None else fallback


def build_assumptions(est: MarketEstimate, ov: Overrides) -> tuple[Assumptions, AssumptionsOut]:
    area = _pick(ov.area_sqm, DEFAULT_AREA_SQM)
    home_price = ov.home_price if ov.home_price is not None else est.buy_per_sqm * area
    monthly_rent = ov.monthly_rent if ov.monthly_rent is not None else est.rent_per_sqm * area

    horizon = int(_pick(ov.horizon_years, DEFAULT_HORIZON_YEARS))
    down = _pick(ov.down_payment_pct, DEFAULT_DOWN_PAYMENT_PCT)
    mortgage = _pick(ov.mortgage_rate, est.mortgage_rate)
    loan_term = int(_pick(ov.loan_term_years, DEFAULT_LOAN_TERM_YEARS))
    tax = _pick(ov.property_tax_rate, est.property_tax_rate)
    maint = _pick(ov.maintenance_rate, DEFAULT_MAINTENANCE_RATE)
    appr = _pick(ov.home_appreciation, est.home_appreciation)
    rent_g = _pick(ov.rent_growth, est.rent_growth)
    inv = _pick(ov.investment_return, est.investment_return)

    assumptions = Assumptions(
        home_price=home_price,
        monthly_rent=monthly_rent,
        horizon_years=horizon,
        down_payment_pct=down,
        mortgage_rate=mortgage,
        loan_term_years=loan_term,
        property_tax_rate=tax,
        maintenance_rate=maint,
        buy_closing_pct=est.buy_closing_pct,
        sell_closing_pct=est.sell_closing_pct,
        home_appreciation=appr,
        rent_growth=rent_g,
        investment_return=inv,
    )
    out = AssumptionsOut(
        area_sqm=area,
        home_price=home_price,
        monthly_rent=monthly_rent,
        horizon_years=horizon,
        down_payment_pct=down,
        mortgage_rate=mortgage,
        loan_term_years=loan_term,
        property_tax_rate=tax,
        maintenance_rate=maint,
        home_appreciation=appr,
        rent_growth=rent_g,
        investment_return=inv,
        currency=est.currency,
        data_source=est.source,
    )
    return assumptions, out


def _fmt_money(amount: float, currency: str) -> str:
    return f"{round(amount):,}".replace(",", " ") + f" {currency}"


def build_summary(rec: str, advantage: float, horizon: int, be: int | None, currency: str) -> str:
    adv = _fmt_money(abs(advantage), currency)
    if rec == "buy":
        head = f"За {horizon} лет покупка выгоднее примерно на {adv}."
    elif rec == "rent":
        head = f"За {horizon} лет аренда выгоднее примерно на {adv}."
    else:
        head = f"За {horizon} лет разница невелика — варианты сопоставимы (~{adv})."

    if be is None:
        tail = " Покупка не окупается в пределах горизонта — аренда + инвестиции держатся впереди."
    elif be <= 1:
        tail = " Покупка обгоняет аренду уже в первый год."
    else:
        tail = f" Точка окупаемости покупки — около {be}-го года."
    return head + tail


async def run_analysis(
    req: AnalyzeRequest, client: httpx.AsyncClient | None = None
) -> AnalyzeResponse:
    location = await geocode(req.address, client=client)
    est = estimate_for(location)
    assumptions, assumptions_out = build_assumptions(est, req.overrides)
    result = analyze(assumptions)

    result_out = ResultOut(
        recommendation=result.recommendation,
        horizon_years=result.horizon_years,
        buy_net_worth=result.buy_net_worth,
        rent_net_worth=result.rent_net_worth,
        advantage=result.advantage,
        advantage_pct=result.advantage_pct,
        break_even_year=result.break_even_year,
        monthly_mortgage=result.monthly_mortgage,
        total_buy_cost=result.total_buy_cost,
        total_rent_cost=result.total_rent_cost,
        timeline=[
            YearPointOut(
                year=p.year,
                buy_net_worth=p.buy_net_worth,
                rent_net_worth=p.rent_net_worth,
                home_value=p.home_value,
                loan_balance=p.loan_balance,
                home_equity=p.home_equity,
            )
            for p in result.timeline
        ],
    )

    summary = build_summary(
        result.recommendation,
        result.advantage,
        result.horizon_years,
        result.break_even_year,
        est.currency,
    )

    return AnalyzeResponse(
        location=LocationOut(
            display_name=location.display_name,
            lat=location.lat,
            lon=location.lon,
            country=location.country,
            country_code=location.country_code,
            city=location.city,
        ),
        assumptions=assumptions_out,
        result=result_out,
        summary=summary,
    )
