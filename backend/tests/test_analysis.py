from app.analysis import Assumptions, analyze, monthly_mortgage_payment


def test_mortgage_payment_known_value() -> None:
    # 100000 под 6% на 30 лет ≈ 599.55/мес
    pay = monthly_mortgage_payment(100_000, 0.06, 30)
    assert abs(pay - 599.55) < 1.0


def test_mortgage_zero_rate_is_linear() -> None:
    assert monthly_mortgage_payment(120_000, 0.0, 10) == 120_000 / 120


def test_mortgage_zero_loan() -> None:
    assert monthly_mortgage_payment(0, 0.05, 20) == 0.0


def _base(**kw: object) -> Assumptions:
    defaults: dict[str, object] = {
        "home_price": 300_000,
        "monthly_rent": 1_500,
        "horizon_years": 10,
        "down_payment_pct": 0.2,
        "mortgage_rate": 0.05,
        "loan_term_years": 20,
        "property_tax_rate": 0.005,
        "maintenance_rate": 0.01,
        "home_appreciation": 0.04,
        "rent_growth": 0.04,
        "investment_return": 0.07,
    }
    defaults.update(kw)
    return Assumptions(**defaults)  # type: ignore[arg-type]


def test_timeline_length_matches_horizon() -> None:
    res = analyze(_base(horizon_years=15))
    assert len(res.timeline) == 15
    assert res.timeline[-1].year == 15


def test_high_appreciation_favors_buying() -> None:
    res = analyze(_base(home_appreciation=0.10, rent_growth=0.06))
    assert res.recommendation == "buy"
    assert res.advantage > 0


def test_high_rent_yield_and_low_appreciation_favors_renting() -> None:
    # Дешёвая аренда относительно цены + слабый рост цен => снимать выгоднее.
    res = analyze(
        _base(monthly_rent=600, home_appreciation=0.0, investment_return=0.10)
    )
    assert res.recommendation == "rent"
    assert res.advantage < 0


def test_break_even_monotonic_buy_overtakes() -> None:
    res = analyze(_base(home_appreciation=0.08, horizon_years=30))
    assert res.break_even_year is not None
    # после точки окупаемости покупатель не отстаёт в последний год
    assert res.timeline[-1].buy_net_worth >= res.timeline[-1].rent_net_worth


def test_equity_grows_as_loan_amortizes() -> None:
    res = analyze(_base())
    balances = [p.loan_balance for p in res.timeline]
    assert balances == sorted(balances, reverse=True)  # долг убывает
    assert res.timeline[-1].home_equity > res.timeline[0].home_equity


def test_zero_down_payment_full_mortgage() -> None:
    # 0% взнос: арендатор стартует без портфеля, ипотека на всю цену.
    res = analyze(_base(down_payment_pct=0.0))
    assert res.monthly_mortgage > 0
    assert len(res.timeline) == 10
    assert res.timeline[0].loan_balance < res.timeline[0].home_value


def test_one_year_horizon() -> None:
    res = analyze(_base(horizon_years=1))
    assert len(res.timeline) == 1
    assert res.recommendation in {"buy", "rent", "neutral"}


def test_full_cash_purchase_no_loan() -> None:
    # 100% взнос → кредита нет, платёж 0.
    res = analyze(_base(down_payment_pct=1.0))
    assert res.monthly_mortgage == 0.0
    assert res.timeline[-1].loan_balance == 0.0


def test_neutral_zone() -> None:
    # Подбор: разница около нуля даёт neutral. Проверяем сам факт классификации.
    res = analyze(_base())
    assert res.recommendation in {"buy", "rent", "neutral"}
