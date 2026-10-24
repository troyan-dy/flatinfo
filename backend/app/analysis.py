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

MONTHS_IN_YEAR = 12

# Нейтральная зона: разница итогового богатства меньше 3% цены — «не принципиально».
NEUTRAL_ZONE_PCT = 0.03


@dataclass(frozen=True)
class Assumptions:
    """Все параметры расчёта. Ставки — годовые доли (0.05 = 5%)."""

    home_price: float  # цена покупки эквивалентного жилья
    monthly_rent: float  # рыночная аренда того же жилья в месяц
    horizon_years: int  # сколько лет планируется жить

    down_payment_pct: float = 0.2  # первоначальный взнос, доля цены
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
        return float(0)
    payments = term_years * MONTHS_IN_YEAR
    rate = annual_rate / MONTHS_IN_YEAR
    if rate == 0:
        return loan / payments
    growth = (1 + rate) ** payments
    return loan * rate * growth / (growth - 1)


def _monthly_rate(annual: float) -> float:
    """Эффективная месячная ставка из годовой (геометрически)."""
    return (1 + annual) ** (1 / MONTHS_IN_YEAR) - 1


class _Simulation:
    """Помесячная симуляция богатства покупателя и арендатора с одинаковым бюджетом."""

    def __init__(self, assumptions: Assumptions) -> None:
        self._terms = assumptions
        down_payment = assumptions.home_price * assumptions.down_payment_pct
        buy_closing = assumptions.home_price * assumptions.buy_closing_pct
        self._loan_balance = assumptions.home_price - down_payment
        self.payment = monthly_mortgage_payment(
            self._loan_balance,
            assumptions.mortgage_rate,
            assumptions.loan_term_years,
        )

        self._loan_rate = assumptions.mortgage_rate / MONTHS_IN_YEAR
        self._appreciation = _monthly_rate(assumptions.home_appreciation)
        self._rent_growth = _monthly_rate(assumptions.rent_growth)
        self._investment = _monthly_rate(assumptions.investment_return)

        # Старт: покупатель потратил кэш на взнос+сделку, портфель 0.
        # Арендатор этот же кэш оставил себе и инвестирует.
        self._buy_portfolio = float(0)
        self._rent_portfolio = down_payment + buy_closing

        self._home_value = assumptions.home_price
        self._rent = assumptions.monthly_rent

        self.total_buy_cost = down_payment + buy_closing
        self.total_rent_cost = float(0)

        self.timeline: list[YearPoint] = []
        self.break_even_year: int | None = None

    def run(self) -> None:
        """Прогнать все месяцы горизонта, снимая точку на конец каждого года."""
        for month in range(1, self._terms.horizon_years * MONTHS_IN_YEAR + 1):
            self._step()
            if month % MONTHS_IN_YEAR == 0:
                self._snapshot(month // MONTHS_IN_YEAR)

    def _step(self) -> None:
        buy_out = self._owner_outflow()
        rent_out = self._rent

        self.total_buy_cost += buy_out
        self.total_rent_cost += rent_out
        self._invest_difference(buy_out - rent_out)

        # рост стоимости жилья и индексация аренды
        self._home_value *= 1 + self._appreciation
        self._rent *= 1 + self._rent_growth

    def _owner_outflow(self) -> float:
        """Расходы покупателя в этом месяце: ипотека + налог + содержание."""
        mortgage_out, principal = self._mortgage_month()
        tax = self._home_value * self._terms.property_tax_rate / MONTHS_IN_YEAR
        upkeep = self._home_value * self._terms.maintenance_rate / MONTHS_IN_YEAR
        self._loan_balance -= principal
        return mortgage_out + tax + upkeep

    def _mortgage_month(self) -> tuple[float, float]:
        """Платёж по ипотеке за месяц и погашенная им часть тела долга."""
        balance = self._loan_balance
        if balance > 0:
            interest = balance * self._loan_rate
            principal = min(max(0, self.payment - interest), balance)
            return interest + principal, principal
        return float(0), min(0, balance)

    def _invest_difference(self, diff: float) -> None:
        """Тот, кто платит меньше, инвестирует разницу. Оба портфеля растут."""
        growth = 1 + self._investment
        self._buy_portfolio *= growth
        self._rent_portfolio *= growth
        if diff > 0:
            # покупка дороже → арендатор инвестирует экономию
            self._rent_portfolio += diff
        else:
            # аренда дороже → покупатель инвестирует экономию
            self._buy_portfolio -= diff

    def _snapshot(self, year: int) -> None:
        """Снимок на конец года: чистый капитал в жилье после продажи и долга."""
        sell_cost = self._home_value * self._terms.sell_closing_pct
        equity = self._home_value - sell_cost - self._loan_balance
        buy_net_worth = self._buy_portfolio + equity
        self.timeline.append(
            YearPoint(
                year=year,
                buy_net_worth=buy_net_worth,
                rent_net_worth=self._rent_portfolio,
                home_value=self._home_value,
                loan_balance=max(float(0), self._loan_balance),
                home_equity=equity,
            ),
        )
        if self.break_even_year is None and buy_net_worth >= self._rent_portfolio:
            self.break_even_year = year


def analyze(assumptions: Assumptions) -> AnalysisResult:
    """Сравнить итоговое богатство покупателя и арендатора на горизонте."""
    simulation = _Simulation(assumptions)
    simulation.run()

    final = simulation.timeline[-1]
    advantage = final.buy_net_worth - final.rent_net_worth
    advantage_pct = advantage / assumptions.home_price if assumptions.home_price else float(0)

    if abs(advantage_pct) < NEUTRAL_ZONE_PCT:
        recommendation = "neutral"
    elif advantage > 0:
        recommendation = "buy"
    else:
        recommendation = "rent"

    return AnalysisResult(
        recommendation=recommendation,
        horizon_years=assumptions.horizon_years,
        buy_net_worth=final.buy_net_worth,
        rent_net_worth=final.rent_net_worth,
        advantage=advantage,
        advantage_pct=advantage_pct,
        break_even_year=simulation.break_even_year,
        monthly_mortgage=simulation.payment,
        total_buy_cost=simulation.total_buy_cost,
        total_rent_cost=simulation.total_rent_cost,
        timeline=simulation.timeline,
    )
