from app.db.base import Base


def test_expected_tables_exist() -> None:
    tables = set(Base.metadata.tables.keys())
    assert tables == {"portfolio", "instrument", "price", "fx_rate", "transaction"}
