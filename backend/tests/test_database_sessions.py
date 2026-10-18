"""Tests for SQLAlchemy session and transaction infrastructure."""

import pytest
from sqlalchemy import Column, Integer, MetaData, Table, create_engine, select
from sqlalchemy.orm import Session

from app.core.database import create_session_factory


@pytest.fixture
def database():
    engine = create_engine("sqlite+pysqlite:///:memory:")

    metadata = MetaData()
    records = Table(
        "session_test_records",
        metadata,
        Column("id", Integer, primary_key=True),
    )
    metadata.create_all(engine)

    try:
        yield engine, records
    finally:
        engine.dispose()


def test_session_factory_configuration(database):
    engine, _ = database
    factory = create_session_factory(engine)

    assert factory.kw["bind"] is engine
    assert factory.kw["autoflush"] is False
    assert factory.kw["expire_on_commit"] is False

    with factory() as session:
        assert isinstance(session, Session)
        assert session.get_bind() is engine

    assert not session.is_active or not session.in_transaction()


def test_transaction_commit(database):
    engine, records = database
    factory = create_session_factory(engine)

    with factory.begin() as session:
        session.execute(records.insert().values(id=1))

    with engine.connect() as connection:
        result = connection.execute(select(records.c.id)).scalars().all()

    assert result == [1]


def test_transaction_rollback(database):
    engine, records = database
    factory = create_session_factory(engine)

    with pytest.raises(RuntimeError, match="simulated failure"):
        with factory.begin() as session:
            session.execute(records.insert().values(id=2))
            raise RuntimeError("simulated failure")

    with engine.connect() as connection:
        result = connection.execute(select(records.c.id)).scalars().all()

    assert result == []


def test_session_closed_after_transaction(database):
    engine, records = database
    factory = create_session_factory(engine)

    with factory.begin() as session:
        session.execute(records.insert().values(id=3))

    assert not session.in_transaction()

    with engine.connect() as connection:
        result = connection.execute(select(records.c.id)).scalars().all()

    assert result == [3]
