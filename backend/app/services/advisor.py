"""Оркестрация: адрес → геокод → рыночные оценки → финансовая модель → ответ."""

from __future__ import annotations

import httpx

from app.analysis import AnalysisResult, Assumptions, analyze
from app.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    AssumptionsOut,
    LocationOut,
    Overrides,
    ResultOut,
    YearPointOut,
)
from app.services.geocode import GeoLocation, geocode
from app.services.market import MarketEstimate, estimate_for

DEFAULT_AREA_SQM = 60.0
DEFAULT_HORIZON_YEARS = 10
DEFAULT_DOWN_PAYMENT_PCT = 0.2
DEFAULT_LOAN_TERM_YEARS = 20
DEFAULT_MAINTENANCE_RATE = 0.012


def _pick(override: float | None, fallback: float) -> float:
    return fallback if override is None else override


def build_assumptions(est: MarketEstimate, ov: Overrides) -> tuple[Assumptions, AssumptionsOut]:
    """Допущения расчёта: рыночные оценки, перекрытые ручными правками."""
    area = _pick(ov.area_sqm, DEFAULT_AREA_SQM)
    assumptions = Assumptions(
        home_price=_pick(ov.home_price, est.buy_per_sqm * area),
        monthly_rent=_pick(ov.monthly_rent, est.rent_per_sqm * area),
        horizon_years=int(_pick(ov.horizon_years, DEFAULT_HORIZON_YEARS)),
        down_payment_pct=_pick(ov.down_payment_pct, DEFAULT_DOWN_PAYMENT_PCT),
        mortgage_rate=_pick(ov.mortgage_rate, est.mortgage_rate),
        loan_term_years=int(_pick(ov.loan_term_years, DEFAULT_LOAN_TERM_YEARS)),
        property_tax_rate=_pick(ov.property_tax_rate, est.property_tax_rate),
        maintenance_rate=_pick(ov.maintenance_rate, DEFAULT_MAINTENANCE_RATE),
        buy_closing_pct=est.buy_closing_pct,
        sell_closing_pct=est.sell_closing_pct,
        home_appreciation=_pick(ov.home_appreciation, est.home_appreciation),
        rent_growth=_pick(ov.rent_growth, est.rent_growth),
        investment_return=_pick(ov.investment_return, est.investment_return),
    )
    out = AssumptionsOut(
        area_sqm=area,
        home_price=assumptions.home_price,
        monthly_rent=assumptions.monthly_rent,
        horizon_years=assumptions.horizon_years,
        down_payment_pct=assumptions.down_payment_pct,
        mortgage_rate=assumptions.mortgage_rate,
        loan_term_years=assumptions.loan_term_years,
        property_tax_rate=assumptions.property_tax_rate,
        maintenance_rate=assumptions.maintenance_rate,
        home_appreciation=assumptions.home_appreciation,
        rent_growth=assumptions.rent_growth,
        investment_return=assumptions.investment_return,
        currency=est.currency,
        data_source=est.source,
    )
    return assumptions, out


def _fmt_money(amount: float, currency: str) -> str:
    grouped = format(round(amount), ",").replace(",", " ")
    return f"{grouped} {currency}"


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


def _location_out(location: GeoLocation) -> LocationOut:
    return LocationOut(
        display_name=location.display_name,
        lat=location.lat,
        lon=location.lon,
        country=location.country,
        country_code=location.country_code,
        city=location.city,
    )


def _result_out(outcome: AnalysisResult) -> ResultOut:
    return ResultOut(
        recommendation=outcome.recommendation,
        horizon_years=outcome.horizon_years,
        buy_net_worth=outcome.buy_net_worth,
        rent_net_worth=outcome.rent_net_worth,
        advantage=outcome.advantage,
        advantage_pct=outcome.advantage_pct,
        break_even_year=outcome.break_even_year,
        monthly_mortgage=outcome.monthly_mortgage,
        total_buy_cost=outcome.total_buy_cost,
        total_rent_cost=outcome.total_rent_cost,
        timeline=[
            YearPointOut(
                year=point.year,
                buy_net_worth=point.buy_net_worth,
                rent_net_worth=point.rent_net_worth,
                home_value=point.home_value,
                loan_balance=point.loan_balance,
                home_equity=point.home_equity,
            )
            for point in outcome.timeline
        ],
    )


async def run_analysis(
    req: AnalyzeRequest,
    client: httpx.AsyncClient | None = None,
) -> AnalyzeResponse:
    """Полный расчёт по адресу: геокод → рыночные оценки → модель → ответ API."""
    location = await geocode(req.address, client=client)
    est = estimate_for(location)
    assumptions, assumptions_out = build_assumptions(est, req.overrides)
    outcome = analyze(assumptions)
    return AnalyzeResponse(
        location=_location_out(location),
        assumptions=assumptions_out,
        result=_result_out(outcome),
        summary=build_summary(
            outcome.recommendation,
            outcome.advantage,
            outcome.horizon_years,
            outcome.break_even_year,
            est.currency,
        ),
    )
