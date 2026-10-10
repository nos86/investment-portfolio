from __future__ import annotations

import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class InstrumentType(str, enum.Enum):
    FUND = "FUND"
    CERTIFICATE = "CERTIFICATE"
    ETF = "ETF"
    STOCK = "STOCK"
    BOND = "BOND"
    OTHER = "OTHER"


class QuoteType(str, enum.Enum):
    UNIT = "UNIT"
    PERCENT_OF_NOMINAL = "PERCENT_OF_NOMINAL"


class TransactionType(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"
    INCOME = "INCOME"
    FEE = "FEE"


class Portfolio(Base):
    __tablename__ = "portfolio"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class Instrument(Base):
    __tablename__ = "instrument"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    isin: Mapped[str] = mapped_column(String(12), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    instrument_type: Mapped[InstrumentType] = mapped_column(Enum(InstrumentType), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    quote_type: Mapped[QuoteType] = mapped_column(Enum(QuoteType), nullable=False)
    nominal: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    provider: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_symbol: Mapped[str | None] = mapped_column(String(128), nullable=True)
    exchange: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_price_date: Mapped[date | None] = mapped_column(Date, nullable=True)


class Price(Base):
    __tablename__ = "price"

    instrument_id: Mapped[int] = mapped_column(ForeignKey("instrument.id"), primary_key=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    close: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    source: Mapped[str] = mapped_column(String(128), nullable=False)


class FxRate(Base):
    __tablename__ = "fx_rate"

    currency: Mapped[str] = mapped_column(String(3), primary_key=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    units_per_eur: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)


class Transaction(Base):
    __tablename__ = "transaction"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolio.id"), nullable=False)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instrument.id"), nullable=False)
    type: Mapped[TransactionType] = mapped_column(Enum(TransactionType), nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    fx_units_per_eur: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    fees_eur: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    note: Mapped[str | None] = mapped_column(String(1024), nullable=True)
