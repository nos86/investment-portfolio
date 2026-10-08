from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.domain import (
    CostMethod,
    InstrumentSnapshot,
    PricePoint,
    QuoteType,
    TransactionType,
    Txn,
    compute_portfolio_snapshot,
    is_valid_isin,
    validate_not_future_trade_date,
    validate_sell_quantity,
)


def D(value: str) -> Decimal:
    return Decimal(value)


def assert_decimal_close(actual: Decimal, expected: Decimal, tol: Decimal = D("0.000001")) -> None:
    assert abs(actual - expected) <= tol


def test_isin_validation() -> None:
    assert is_valid_isin("US0378331005")
    assert is_valid_isin("IE00B4L5Y983")
    assert not is_valid_isin("US0378331004")
    assert not is_valid_isin("BAD")


def test_reject_future_transaction_date() -> None:
    with pytest.raises(ValueError, match="future"):
        validate_not_future_trade_date(date(2026, 1, 3), today=date(2026, 1, 2))


def test_reject_sell_above_holdings() -> None:
    existing = [
        Txn(
            tx_id=1,
            instrument_id=1,
            type=TransactionType.BUY,
            trade_date=date(2026, 1, 1),
            quantity=D("5"),
            unit_price=D("10"),
            currency="EUR",
            fx_units_per_eur=D("1"),
            fees_eur=D("0"),
        )
    ]

    candidate = Txn(
        tx_id=2,
        instrument_id=1,
        type=TransactionType.SELL,
        trade_date=date(2026, 1, 2),
        quantity=D("6"),
        unit_price=D("10"),
        currency="EUR",
        fx_units_per_eur=D("1"),
        fees_eur=D("0"),
    )

    with pytest.raises(ValueError, match="exceeds holdings"):
        validate_sell_quantity(existing, candidate)


def test_average_cost_vs_fifo_expected_values() -> None:
    instruments = {
        1: InstrumentSnapshot(instrument_id=1, quote_type=QuoteType.UNIT, nominal=None),
    }

    transactions = [
        Txn(1, 1, TransactionType.BUY, date(2026, 1, 2), D("10"), D("100"), "EUR", D("1"), D("1")),
        Txn(2, 1, TransactionType.BUY, date(2026, 1, 5), D("10"), D("110"), "EUR", D("1"), D("1")),
        Txn(3, 1, TransactionType.SELL, date(2026, 1, 7), D("8"), D("120"), "EUR", D("1"), D("1")),
        Txn(4, 1, TransactionType.INCOME, date(2026, 1, 8), None, D("50"), "EUR", D("1"), D("0")),
    ]

    prices = {
        1: [PricePoint(instrument_id=1, date=date(2026, 1, 9), close=D("130"), currency="EUR")],
    }

    fx_rates: dict[str, dict[date, Decimal]] = {}

    average_report = compute_portfolio_snapshot(
        instruments,
        prices,
        fx_rates,
        transactions,
        cost_method=CostMethod.AVERAGE_COST,
        valuation_date=date(2026, 1, 9),
    )
    fifo_report = compute_portfolio_snapshot(
        instruments,
        prices,
        fx_rates,
        transactions,
        cost_method=CostMethod.FIFO,
        valuation_date=date(2026, 1, 9),
    )

    average_position = average_report.positions[1]
    fifo_position = fifo_report.positions[1]

    assert average_position.quantity == D("12")
    assert fifo_position.quantity == D("12")

    assert_decimal_close(average_position.realized_pl_eur, D("118.2"))
    assert_decimal_close(fifo_position.realized_pl_eur, D("158.2"))

    assert_decimal_close(average_position.capital_invested_net_eur, D("1261.2"))
    assert_decimal_close(fifo_position.capital_invested_net_eur, D("1301.2"))

    assert_decimal_close(average_position.unrealized_pl_eur, D("298.8"))
    assert_decimal_close(fifo_position.unrealized_pl_eur, D("258.8"))

    assert_decimal_close(average_report.total_return_eur, D("464"))
    assert_decimal_close(fifo_report.total_return_eur, D("464"))


def test_forward_fill_usd_percent_of_nominal_series() -> None:
    instruments = {
        2: InstrumentSnapshot(instrument_id=2, quote_type=QuoteType.PERCENT_OF_NOMINAL, nominal=D("1000")),
    }

    transactions = [
        Txn(1, 2, TransactionType.BUY, date(2026, 1, 1), D("2"), D("95"), "USD", D("1.1"), D("2")),
    ]

    prices = {
        2: [PricePoint(instrument_id=2, date=date(2026, 1, 2), close=D("96"), currency="USD")],
    }
    fx_rates = {
        "USD": {
            date(2026, 1, 1): D("1.1"),
            date(2026, 1, 2): D("1.2"),
            date(2026, 1, 3): D("1.2"),
        }
    }

    report = compute_portfolio_snapshot(
        instruments,
        prices,
        fx_rates,
        transactions,
        valuation_date=date(2026, 1, 3),
    )

    position = report.positions[2]
    assert_decimal_close(position.capital_invested_net_eur, D("1729.272727272727272727272727"))
    assert_decimal_close(position.market_value_eur, D("1600"))
    assert position.used_price_date == date(2026, 1, 2)

    series = report.position_series[2]
    assert [item.day for item in series] == [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)]
    assert series[0].used_price_date is None
    assert series[1].used_price_date == date(2026, 1, 2)
    assert series[2].used_price_date == date(2026, 1, 2)
