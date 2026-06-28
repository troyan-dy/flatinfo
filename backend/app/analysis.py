"""Финансовая модель «снимать vs покупать».

Сравнение честное, по методологии нетто-богатства (как в калькуляторе NYT
«Is it better to rent or buy»): два человека с одинаковым бюджетом — один покупает,
другой снимает и инвестирует разницу. Сравниваем итоговое богатство через N лет.

Ключевая идея: тот, у кого в данном месяце расходы НИЖЕ, разницу инвестирует под
ставку альтернативной доходности. Покупатель стартует с нулевым портфелем (деньги
ушли в первый взнос), арендатор — с портфелем, равным сэкономленному первому взносу
и расходам на сделку. В конце горизонта к богатству покупателя добавляется чистый
капитал в недвижимости (стоимость минус расходы на продажу и остаток кредита).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Assumptions:
    """Все параметры расчёта. Ставки — годовые доли (0.05 = 5%)."""

    home_price: float  # цена покупки эквивалентного жилья
    monthly_rent: float  # рыночная аренда того же жилья в месяц
    horizon_years: int  # сколько лет планируется жить

    down_payment_pct: float = 0.20  # первоначальный взнос, доля цены
    mortgage_rate: float = 0.09  # ставка по ипотеке, годовых
    loan_term_years: int = 20  # срок ипотеки

    property_tax_rate: float = 0.005  # налог на недвижимость, % стоимости в год
    maintenance_rate: float = 0.01  # содержание/ремонт/страховка, % стоимости в год
    buy_closing_pct: float = 0.01  # издержки на покупку, % цены (разово)
    sell_closing_pct: float = 0.03  # издержки на продажу, % цены продажи (разово)

    home_appreciation: float = 0.04  # рост цены жилья, годовых
    rent_growth: float = 0.05  # рост арендной платы, годовых
    investment_return: float = 0.08  # доходность альтернативных вложений, годовых


@dataclass(frozen=True)
class YearPoint:
    """Снимок богатства на конец года — для графика."""

    year: int
    buy_net_worth: float
    rent_net_worth: float
    home_value: float
    loan_balance: float
    home_equity: float


@dataclass(frozen=True)
class AnalysisResult:
    recommendation: str  # "buy" | "rent" | "neutral"
    horizon_years: int
    buy_net_worth: float  # итоговое богатство покупателя
    rent_net_worth: float  # итоговое богатство арендатора
    advantage: float  # положительное => в пользу покупки
    advantage_pct: float  # advantage относительно цены жилья
    break_even_year: int | None  # с какого года покупка обгоняет аренду (None — никогда)
    monthly_mortgage: float
    total_buy_cost: float  # суммарные платежи покупателя за горизонт
    total_rent_cost: float  # суммарная аренда за горизонт
    timeline: list[YearPoint]


def monthly_mortgage_payment(loan: float, annual_rate: float, term_years: int) -> float:
    """Аннуитетный месячный платёж."""
    if loan <= 0:
        return 0.0
    n = term_years * 12
    r = annual_rate / 12
    if r == 0:
        return loan / n
    return loan * r * (1 + r) ** n / ((1 + r) ** n - 1)


def _monthly_rate(annual: float) -> float:
    """Эффективная месячная ставка из годовой (геометрически)."""
    return (1 + annual) ** (1 / 12) - 1


def analyze(a: Assumptions) -> AnalysisResult:
    months = a.horizon_years * 12

    down_payment = a.home_price * a.down_payment_pct
    buy_closing = a.home_price * a.buy_closing_pct
    loan0 = a.home_price - down_payment
    payment = monthly_mortgage_payment(loan0, a.mortgage_rate, a.loan_term_years)

    loan_r = a.mortgage_rate / 12
    appr_m = _monthly_rate(a.home_appreciation)
    rent_g_m = _monthly_rate(a.rent_growth)
    inv_m = _monthly_rate(a.investment_return)

    # Старт: покупатель потратил кэш на взнос+сделку, портфель 0.
    # Арендатор этот же кэш оставил себе и инвестирует.
    buy_portfolio = 0.0
    rent_portfolio = down_payment + buy_closing

    loan_balance = loan0
    home_value = a.home_price
    rent = a.monthly_rent

    total_buy_cost = down_payment + buy_closing
    total_rent_cost = 0.0

    timeline: list[YearPoint] = []
    break_even_year: int | None = None

    for m in range(1, months + 1):
        # --- расходы покупателя в этом месяце ---
        interest = loan_balance * loan_r
        principal = max(0.0, payment - interest) if loan_balance > 0 else 0.0
        principal = min(principal, loan_balance)
        mortgage_out = (interest + principal) if loan_balance > 0 else 0.0
        tax = home_value * a.property_tax_rate / 12
        upkeep = home_value * a.maintenance_rate / 12
        buy_out = mortgage_out + tax + upkeep
        loan_balance -= principal

        # --- расходы арендатора в этом месяце ---
        rent_out = rent

        total_buy_cost += buy_out
        total_rent_cost += rent_out

        # Тот, кто платит меньше, инвестирует разницу. Оба портфеля растут.
        buy_portfolio *= 1 + inv_m
        rent_portfolio *= 1 + inv_m
        diff = buy_out - rent_out
        if diff > 0:
            # покупка дороже → арендатор инвестирует экономию
            rent_portfolio += diff
        else:
            # аренда дороже → покупатель инвестирует экономию
            buy_portfolio += -diff

        # рост стоимости жилья и индексация аренды
        home_value *= 1 + appr_m
        rent *= 1 + rent_g_m

        # --- снимок на конец каждого года ---
        if m % 12 == 0:
            sell_cost = home_value * a.sell_closing_pct
            equity = home_value - sell_cost - loan_balance
            buy_nw = buy_portfolio + equity
            rent_nw = rent_portfolio
            timeline.append(
                YearPoint(
                    year=m // 12,
                    buy_net_worth=buy_nw,
                    rent_net_worth=rent_nw,
                    home_value=home_value,
                    loan_balance=max(0.0, loan_balance),
                    home_equity=equity,
                )
            )
            if break_even_year is None and buy_nw >= rent_nw:
                break_even_year = m // 12

    final = timeline[-1]
    advantage = final.buy_net_worth - final.rent_net_worth
    advantage_pct = advantage / a.home_price if a.home_price else 0.0

    # Нейтральная зона: разница меньше 3% стоимости жилья — «не принципиально».
    if abs(advantage_pct) < 0.03:
        recommendation = "neutral"
    elif advantage > 0:
        recommendation = "buy"
    else:
        recommendation = "rent"

    return AnalysisResult(
        recommendation=recommendation,
        horizon_years=a.horizon_years,
        buy_net_worth=final.buy_net_worth,
        rent_net_worth=final.rent_net_worth,
        advantage=advantage,
        advantage_pct=advantage_pct,
        break_even_year=break_even_year,
        monthly_mortgage=payment,
        total_buy_cost=total_buy_cost,
        total_rent_cost=total_rent_cost,
        timeline=timeline,
    )
