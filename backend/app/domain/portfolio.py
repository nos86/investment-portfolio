from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

ZERO = Decimal("0")
ONE_HUNDRED = Decimal("100")


class CostMethod(str, enum.Enum):
    AVERAGE_COST = "AVERAGE_COST"
    FIFO = "FIFO"


class QuoteType(str, enum.Enum):
    UNIT = "UNIT"
    PERCENT_OF_NOMINAL = "PERCENT_OF_NOMINAL"


class TransactionType(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"
    INCOME = "INCOME"
    FEE = "FEE"


@dataclass(frozen=True)
class InstrumentSnapshot:
    instrument_id: int
    quote_type: QuoteType
    nominal: Decimal | None


@dataclass(frozen=True)
class PricePoint:
    instrument_id: int
    date: date
    close: Decimal
    currency: str


@dataclass(frozen=True)
class Txn:
    tx_id: int
    instrument_id: int
    type: TransactionType
    trade_date: date
    quantity: Decimal | None
    unit_price: Decimal
    currency: str
    fx_units_per_eur: Decimal
    fees_eur: Decimal


@dataclass(frozen=True)
class PositionSnapshot:
    instrument_id: int
    quantity: Decimal
    average_cost_eur: Decimal
    capital_invested_net_eur: Decimal
    market_value_eur: Decimal
    unrealized_pl_eur: Decimal
    unrealized_pl_pct: Decimal
    realized_pl_eur: Decimal
    income_eur: Decimal
    fees_eur: Decimal
    used_price_date: date | None


@dataclass(frozen=True)
class PositionDailyValue:
    day: date
    market_value_eur: Decimal
    capital_invested_net_eur: Decimal
    used_price_date: date | None


@dataclass(frozen=True)
class PortfolioDailyValue:
    day: date
    market_value_eur: Decimal
    capital_invested_net_eur: Decimal


@dataclass(frozen=True)
class PortfolioSnapshot:
    positions: dict[int, PositionSnapshot]
    position_series: dict[int, list[PositionDailyValue]]
    portfolio_series: list[PortfolioDailyValue]
    realized_pl_eur: Decimal
    unrealized_pl_eur: Decimal
    income_eur: Decimal
    fees_eur: Decimal
    total_return_eur: Decimal
    xirr: Decimal | None


@dataclass
class PositionState:
    quantity: Decimal = ZERO
    cost_basis_eur: Decimal = ZERO
    realized_pl_eur: Decimal = ZERO
    income_eur: Decimal = ZERO
    fees_eur: Decimal = ZERO
    fifo_lots: list[tuple[Decimal, Decimal]] | None = None

    def __post_init__(self) -> None:
        if self.fifo_lots is None:
            self.fifo_lots = []


def _sorted_transactions(transactions: list[Txn]) -> list[Txn]:
    return sorted(transactions, key=lambda tx: (tx.trade_date, tx.tx_id))


def _to_eur(amount: Decimal, units_per_eur: Decimal) -> Decimal:
    if units_per_eur <= ZERO:
        raise ValueError("fx units_per_eur must be greater than zero")
    return amount / units_per_eur


def _transaction_gross_eur(tx: Txn, instrument: InstrumentSnapshot) -> Decimal:
    if tx.quantity is None:
        return _to_eur(tx.unit_price, tx.fx_units_per_eur)

    unit_value = tx.unit_price
    if instrument.quote_type == QuoteType.PERCENT_OF_NOMINAL:
        if instrument.nominal is None:
            raise ValueError("nominal is required for PERCENT_OF_NOMINAL instruments")
        unit_value = instrument.nominal * tx.unit_price / ONE_HUNDRED

    gross_in_trade_ccy = tx.quantity * unit_value
    return _to_eur(gross_in_trade_ccy, tx.fx_units_per_eur)


def _consume_fifo_lots(lots: list[tuple[Decimal, Decimal]], quantity: Decimal) -> Decimal:
    remaining = quantity
    consumed_cost = ZERO
    while remaining > ZERO:
        if not lots:
            raise ValueError("sell quantity exceeds holdings")
        lot_qty, lot_cost = lots[0]
        take_qty = min(remaining, lot_qty)
        consumed_cost += lot_cost * (take_qty / lot_qty)

        new_qty = lot_qty - take_qty
        if new_qty == ZERO:
            lots.pop(0)
        else:
            lots[0] = (new_qty, lot_cost * (new_qty / lot_qty))

        remaining -= take_qty
    return consumed_cost


def _get_fx_units_per_eur(currency: str, day: date, fx_rates: dict[str, dict[date, Decimal]]) -> Decimal:
    if currency == "EUR":
        return Decimal("1")

    rates = fx_rates.get(currency)
    if not rates:
        raise ValueError(f"missing FX rates for {currency}")

    valid_days = [candidate for candidate in rates if candidate <= day]
    if not valid_days:
        raise ValueError(f"missing FX rate for {currency} on or before {day.isoformat()}")

    return rates[max(valid_days)]


def _get_price_on_or_before(prices: list[PricePoint], day: date) -> tuple[PricePoint | None, date | None]:
    valid = [price for price in prices if price.date <= day]
    if not valid:
        return None, None
    chosen = max(valid, key=lambda price: price.date)
    return chosen, chosen.date


def _apply_transaction(
    state: PositionState,
    tx: Txn,
    instrument: InstrumentSnapshot,
    cost_method: CostMethod,
    cash_flows: list[tuple[date, Decimal]],
) -> None:
    gross_eur = _transaction_gross_eur(tx, instrument)

    if tx.type == TransactionType.BUY:
        if tx.quantity is None or tx.quantity <= ZERO:
            raise ValueError("BUY requires positive quantity")
        state.quantity += tx.quantity
        state.cost_basis_eur += gross_eur + tx.fees_eur
        if cost_method == CostMethod.FIFO:
            state.fifo_lots.append((tx.quantity, gross_eur + tx.fees_eur))
        state.fees_eur += tx.fees_eur
        cash_flows.append((tx.trade_date, -(gross_eur + tx.fees_eur)))
        return

    if tx.type == TransactionType.SELL:
        if tx.quantity is None or tx.quantity <= ZERO:
            raise ValueError("SELL requires positive quantity")
        if tx.quantity > state.quantity:
            raise ValueError("sell quantity exceeds holdings")

        proceeds_eur = gross_eur - tx.fees_eur
        if cost_method == CostMethod.AVERAGE_COST:
            if state.quantity <= ZERO:
                raise ValueError("cannot sell with zero holdings")
            average_cost = state.cost_basis_eur / state.quantity
            sold_cost = average_cost * tx.quantity
        else:
            sold_cost = _consume_fifo_lots(state.fifo_lots, tx.quantity)

        state.quantity -= tx.quantity
        state.cost_basis_eur -= sold_cost
        state.realized_pl_eur += proceeds_eur - sold_cost
        state.fees_eur += tx.fees_eur
        cash_flows.append((tx.trade_date, proceeds_eur))
        return

    if tx.type == TransactionType.INCOME:
        state.income_eur += gross_eur
        state.fees_eur += tx.fees_eur
        cash_flows.append((tx.trade_date, gross_eur - tx.fees_eur))
        return

    if tx.type == TransactionType.FEE:
        state.fees_eur += gross_eur + tx.fees_eur
        cash_flows.append((tx.trade_date, -(gross_eur + tx.fees_eur)))
        return

    raise ValueError(f"unsupported transaction type: {tx.type}")


def _market_value_eur(
    instrument: InstrumentSnapshot,
    quantity: Decimal,
    day: date,
    prices: list[PricePoint],
    fx_rates: dict[str, dict[date, Decimal]],
) -> tuple[Decimal, date | None]:
    if quantity == ZERO:
        return ZERO, None

    price_point, used_date = _get_price_on_or_before(prices, day)
    if price_point is None:
        return ZERO, None

    px = price_point.close
    if instrument.quote_type == QuoteType.PERCENT_OF_NOMINAL:
        if instrument.nominal is None:
            raise ValueError("nominal is required for PERCENT_OF_NOMINAL instruments")
        px = instrument.nominal * px / ONE_HUNDRED

    units_per_eur = _get_fx_units_per_eur(price_point.currency, day, fx_rates)
    return _to_eur(quantity * px, units_per_eur), used_date


def _day_range(start: date, end: date) -> list[date]:
    current = start
    days: list[date] = []
    while current <= end:
        days.append(current)
        current += timedelta(days=1)
    return days


def _xnpv(rate: Decimal, dated_flows: list[tuple[date, Decimal]]) -> Decimal:
    origin = min(d for d, _ in dated_flows)
    total = ZERO
    one_plus_rate = Decimal("1") + rate
    for flow_day, flow in dated_flows:
        years = Decimal((flow_day - origin).days) / Decimal("365")
        try:
            discount = one_plus_rate**years
        except (InvalidOperation, ValueError):
            return Decimal("Infinity")
        if discount == ZERO:
            return Decimal("Infinity")
        total += flow / discount
    return total


def _compute_xirr(dated_flows: list[tuple[date, Decimal]]) -> Decimal | None:
    if not dated_flows:
        return None
    has_positive = any(flow > ZERO for _, flow in dated_flows)
    has_negative = any(flow < ZERO for _, flow in dated_flows)
    if not (has_positive and has_negative):
        return None

    low = Decimal("-0.9999")
    high = Decimal("10")
    npv_low = _xnpv(low, dated_flows)
    npv_high = _xnpv(high, dated_flows)
    if npv_low == Decimal("Infinity") or npv_high == Decimal("Infinity"):
        return None
    if npv_low * npv_high > ZERO:
        return None

    for _ in range(120):
        mid = (low + high) / Decimal("2")
        npv_mid = _xnpv(mid, dated_flows)
        if abs(npv_mid) < Decimal("0.0000001"):
            return mid
        if npv_mid * npv_low > ZERO:
            low = mid
            npv_low = npv_mid
        else:
            high = mid
    return (low + high) / Decimal("2")


def compute_portfolio_snapshot(
    instruments: dict[int, InstrumentSnapshot],
    prices_by_instrument: dict[int, list[PricePoint]],
    fx_rates: dict[str, dict[date, Decimal]],
    transactions: list[Txn],
    cost_method: CostMethod = CostMethod.AVERAGE_COST,
    valuation_date: date | None = None,
) -> PortfolioSnapshot:
    if valuation_date is None:
        valuation_date = date.today()

    states = {instrument_id: PositionState() for instrument_id in instruments}
    sorted_transactions = _sorted_transactions(transactions)
    dated_cash_flows: list[tuple[date, Decimal]] = []

    for tx in sorted_transactions:
        instrument = instruments.get(tx.instrument_id)
        if instrument is None:
            raise ValueError(f"missing instrument {tx.instrument_id}")
        _apply_transaction(states[tx.instrument_id], tx, instrument, cost_method, dated_cash_flows)

    positions: dict[int, PositionSnapshot] = {}
    first_buy_date: date | None = None

    for tx in sorted_transactions:
        if tx.type == TransactionType.BUY:
            first_buy_date = tx.trade_date if first_buy_date is None else min(first_buy_date, tx.trade_date)

    for instrument_id, state in states.items():
        instrument = instruments[instrument_id]
        market_value, used_price_date = _market_value_eur(
            instrument,
            state.quantity,
            valuation_date,
            prices_by_instrument.get(instrument_id, []),
            fx_rates,
        )
        capital = state.cost_basis_eur
        avg_cost = capital / state.quantity if state.quantity > ZERO else ZERO
        unrealized = market_value - capital
        unrealized_pct = unrealized / capital if capital > ZERO else ZERO
        positions[instrument_id] = PositionSnapshot(
            instrument_id=instrument_id,
            quantity=state.quantity,
            average_cost_eur=avg_cost,
            capital_invested_net_eur=capital,
            market_value_eur=market_value,
            unrealized_pl_eur=unrealized,
            unrealized_pl_pct=unrealized_pct,
            realized_pl_eur=state.realized_pl_eur,
            income_eur=state.income_eur,
            fees_eur=state.fees_eur,
            used_price_date=used_price_date,
        )

    position_series: dict[int, list[PositionDailyValue]] = {instrument_id: [] for instrument_id in instruments}
    portfolio_series: list[PortfolioDailyValue] = []

    if first_buy_date is not None:
        days = _day_range(first_buy_date, valuation_date)

        per_day_states = {instrument_id: PositionState() for instrument_id in instruments}
        tx_cursor = 0

        for day in days:
            while tx_cursor < len(sorted_transactions) and sorted_transactions[tx_cursor].trade_date <= day:
                tx = sorted_transactions[tx_cursor]
                _apply_transaction(
                    per_day_states[tx.instrument_id],
                    tx,
                    instruments[tx.instrument_id],
                    cost_method,
                    cash_flows=[],
                )
                tx_cursor += 1

            day_market_total = ZERO
            day_capital_total = ZERO
            for instrument_id, day_state in per_day_states.items():
                day_market, used_price_date = _market_value_eur(
                    instruments[instrument_id],
                    day_state.quantity,
                    day,
                    prices_by_instrument.get(instrument_id, []),
                    fx_rates,
                )
                position_series[instrument_id].append(
                    PositionDailyValue(
                        day=day,
                        market_value_eur=day_market,
                        capital_invested_net_eur=day_state.cost_basis_eur,
                        used_price_date=used_price_date,
                    )
                )
                day_market_total += day_market
                day_capital_total += day_state.cost_basis_eur

            portfolio_series.append(
                PortfolioDailyValue(
                    day=day,
                    market_value_eur=day_market_total,
                    capital_invested_net_eur=day_capital_total,
                )
            )

    realized_pl = sum(position.realized_pl_eur for position in positions.values())
    unrealized_pl = sum(position.unrealized_pl_eur for position in positions.values())
    income = sum(position.income_eur for position in positions.values())
    fees = sum(position.fees_eur for position in positions.values())

    final_market_value = sum(position.market_value_eur for position in positions.values())
    dated_cash_flows_for_xirr = list(dated_cash_flows)
    if final_market_value != ZERO:
        dated_cash_flows_for_xirr.append((valuation_date, final_market_value))

    return PortfolioSnapshot(
        positions=positions,
        position_series=position_series,
        portfolio_series=portfolio_series,
        realized_pl_eur=realized_pl,
        unrealized_pl_eur=unrealized_pl,
        income_eur=income,
        fees_eur=fees,
        total_return_eur=realized_pl + unrealized_pl + income - fees,
        xirr=_compute_xirr(dated_cash_flows_for_xirr),
    )
