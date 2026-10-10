# Guida rapida: schema portafoglio e motore di calcolo EUR

Questo documento spiega come usare il lavoro introdotto nel backend senza dover leggere tutto il codice.

## 1) Cosa è stato aggiunto

### Schema database (Alembic + SQLAlchemy)

Tabelle principali:

- `portfolio`
- `instrument`
- `price`
- `fx_rate`
- `transaction`

Comandi utili:

```bash
cd backend
uv run alembic upgrade head
```

File di riferimento:

- Modelli ORM: `backend/app/db/models.py`
- Migrazione iniziale: `backend/alembic/versions/20261008_0001_init_portfolio_schema.py`

## 2) Regole dati importanti

- Tutti i calcoli economici sono in **EUR**.
- Transazioni supportate: `BUY`, `SELL`, `INCOME`, `FEE`.
- Metodi di costo supportati:
  - `CostMethod.AVERAGE_COST` (default)
  - `CostMethod.FIFO`
- `quote_type` supportati:
  - `UNIT`
  - `PERCENT_OF_NOMINAL` (valore = `quantity * nominal * price / 100`)
- Prezzi e cambi sono valutati con logica **on-or-before** (forward-fill sullo storico giornaliero).

## 3) Validazioni disponibili

In `backend/app/domain/validation.py`:

- `is_valid_isin(isin)` → valida formato + check digit ISIN
- `validate_not_future_trade_date(trade_date)` → blocca date future
- `validate_sell_quantity(existing_transactions, sell_transaction)` → blocca SELL superiori alla quantità detenuta alla data dell’ordine

## 4) Come usare il motore di calcolo

Entry point: `compute_portfolio_snapshot` in `backend/app/domain/portfolio.py`.

Esempio minimale:

```python
from datetime import date
from decimal import Decimal

from app.domain import (
    CostMethod,
    InstrumentSnapshot,
    PricePoint,
    QuoteType,
    TransactionType,
    Txn,
    compute_portfolio_snapshot,
)

instruments = {
    1: InstrumentSnapshot(
        instrument_id=1,
        quote_type=QuoteType.UNIT,
        nominal=None,
    ),
}

transactions = [
    Txn(
        tx_id=1,
        instrument_id=1,
        type=TransactionType.BUY,
        trade_date=date(2026, 1, 2),
        quantity=Decimal("10"),
        unit_price=Decimal("100"),
        currency="EUR",
        fx_units_per_eur=Decimal("1"),
        fees_eur=Decimal("1"),
    ),
]

prices_by_instrument = {
    1: [
        PricePoint(
            instrument_id=1,
            date=date(2026, 1, 9),
            close=Decimal("103"),
            currency="EUR",
        )
    ]
}

fx_rates = {}  # per EUR non servono cambi; per altre valute inserire storico {ccy: {date: units_per_eur}}

snapshot = compute_portfolio_snapshot(
    instruments=instruments,
    prices_by_instrument=prices_by_instrument,
    fx_rates=fx_rates,
    transactions=transactions,
    cost_method=CostMethod.AVERAGE_COST,
    valuation_date=date(2026, 1, 9),
)

position = snapshot.positions[1]
print(position.market_value_eur)
print(snapshot.total_return_eur)
```

## 5) Cosa restituisce il calcolo

`PortfolioSnapshot` include:

- `positions`: metriche correnti per strumento (`quantity`, `average_cost_eur`, `market_value_eur`, P/L realizzato/non realizzato, `used_price_date`, ecc.)
- `position_series`: serie giornaliera per strumento da primo BUY a data di valutazione
- `portfolio_series`: serie giornaliera aggregata di portafoglio
- aggregati di portafoglio:
  - `realized_pl_eur`
  - `unrealized_pl_eur`
  - `income_eur`
  - `fees_eur`
  - `total_return_eur`
  - `xirr` (se calcolabile)

## 6) Verifica rapida

```bash
cd backend
uv run pytest
uv run ruff check .
```

Test principali: `backend/tests/test_portfolio_domain.py`
