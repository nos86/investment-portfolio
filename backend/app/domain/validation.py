from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.domain.portfolio import TransactionType, Txn


def is_valid_isin(isin: str) -> bool:
    if len(isin) != 12 or not isin.isalnum() or not isin[:2].isalpha():
        return False

    transformed = ""
    for char in isin.upper():
        if char.isdigit():
            transformed += char
        elif char.isalpha():
            transformed += str(ord(char) - 55)
        else:
            return False

    total = 0
    parity = len(transformed) % 2
    for idx, ch in enumerate(transformed):
        digit = int(ch)
        if idx % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit

    return total % 10 == 0


def validate_not_future_trade_date(trade_date: date, today: date | None = None) -> None:
    effective_today = today or date.today()
    if trade_date > effective_today:
        raise ValueError("transaction date cannot be in the future")


def validate_sell_quantity(
    existing_transactions: list[Txn],
    sell_transaction: Txn,
) -> None:
    if sell_transaction.type != TransactionType.SELL:
        return

    qty = Decimal("0")
    relevant_transactions = sorted(
        [
            tx
            for tx in existing_transactions
            if tx.instrument_id == sell_transaction.instrument_id and tx.trade_date <= sell_transaction.trade_date
        ],
        key=lambda tx: (tx.trade_date, tx.tx_id),
    )

    for tx in relevant_transactions:
        if tx.type == TransactionType.BUY:
            if tx.quantity is None:
                raise ValueError("BUY requires quantity")
            qty += tx.quantity
        elif tx.type == TransactionType.SELL:
            if tx.quantity is None:
                raise ValueError("SELL requires quantity")
            qty -= tx.quantity

    if sell_transaction.quantity is None:
        raise ValueError("SELL requires quantity")
    if sell_transaction.quantity > qty:
        raise ValueError("sell quantity exceeds holdings at trade date")
