"""init portfolio schema

Revision ID: 20261008_0001
Revises: 
Create Date: 2026-10-08 00:00:00.000000

"""

from typing import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261008_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


instrument_type_enum = sa.Enum(
    "FUND", "CERTIFICATE", "ETF", "STOCK", "BOND", "OTHER", name="instrumenttype"
)
quote_type_enum = sa.Enum("UNIT", "PERCENT_OF_NOMINAL", name="quotetype")
transaction_type_enum = sa.Enum("BUY", "SELL", "INCOME", "FEE", name="transactiontype")


def upgrade() -> None:
    instrument_type_enum.create(op.get_bind(), checkfirst=True)
    quote_type_enum.create(op.get_bind(), checkfirst=True)
    transaction_type_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "portfolio",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "instrument",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("isin", sa.String(length=12), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("instrument_type", instrument_type_enum, nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("quote_type", quote_type_enum, nullable=False),
        sa.Column("nominal", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("provider", sa.String(length=128), nullable=False),
        sa.Column("provider_symbol", sa.String(length=128), nullable=True),
        sa.Column("exchange", sa.String(length=64), nullable=True),
        sa.Column("last_price_date", sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("isin"),
    )

    op.create_table(
        "fx_rate",
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("units_per_eur", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.PrimaryKeyConstraint("currency", "date"),
    )

    op.create_table(
        "price",
        sa.Column("instrument_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("close", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.ForeignKeyConstraint(["instrument_id"], ["instrument.id"]),
        sa.PrimaryKeyConstraint("instrument_id", "date"),
    )

    op.create_table(
        "transaction",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("portfolio_id", sa.Integer(), nullable=False),
        sa.Column("instrument_id", sa.Integer(), nullable=False),
        sa.Column("type", transaction_type_enum, nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("unit_price", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("fx_units_per_eur", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("fees_eur", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("note", sa.String(length=1024), nullable=True),
        sa.ForeignKeyConstraint(["instrument_id"], ["instrument.id"]),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolio.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("transaction")
    op.drop_table("price")
    op.drop_table("fx_rate")
    op.drop_table("instrument")
    op.drop_table("portfolio")

    transaction_type_enum.drop(op.get_bind(), checkfirst=True)
    quote_type_enum.drop(op.get_bind(), checkfirst=True)
    instrument_type_enum.drop(op.get_bind(), checkfirst=True)
