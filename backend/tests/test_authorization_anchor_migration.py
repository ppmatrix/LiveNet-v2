"""Testes estruturais offline da migracao AUTH-03."""

import importlib.util
from pathlib import Path
from unittest.mock import Mock

import pytest
import sqlalchemy as sa


REVISION = "f067a01a7230"
PREVIOUS_REVISION = "f066a01a7230"

MIGRATION_FILE = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "versions"
    / f"{REVISION}_create_authorization_integrity_anchors.py"
)

TABLE_NAME = "authorization_integrity_anchors"
SCHEMA = "authorization"

EXPECTED_COLUMNS = {
    "authorization_id",
    "operation",
    "target",
    "sql_sha256",
    "confirmed_state",
    "confirmed_sequence",
    "confirmed_hash",
    "created_at",
    "updated_at",
}

EXPECTED_CHECKS = {
    "ck_auth_anchor_operation_not_empty",
    "ck_auth_anchor_target_not_empty",
    "ck_auth_anchor_sql_sha256",
    "ck_auth_anchor_confirmed_hash",
    "ck_auth_anchor_confirmed_state",
    "ck_auth_anchor_confirmed_sequence",
    "ck_auth_anchor_initial_state",
    "ck_auth_anchor_timestamps",
}


@pytest.fixture
def migration():
    spec = importlib.util.spec_from_file_location(
        "test_authorization_anchor_revision",
        MIGRATION_FILE,
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def upgrade_calls(migration, monkeypatch):
    operations = Mock()
    monkeypatch.setattr(migration, "op", operations)

    migration.upgrade()

    return operations


def test_revision_chain(migration):
    assert migration.revision == REVISION
    assert migration.down_revision == PREVIOUS_REVISION
    assert migration.branch_labels is None
    assert migration.depends_on is None


def test_upgrade_creates_dedicated_schema(upgrade_calls):
    upgrade_calls.execute.assert_called_once_with(
        "CREATE SCHEMA authorization"
    )


def test_upgrade_creates_expected_table(upgrade_calls):
    upgrade_calls.create_table.assert_called_once()

    args, kwargs = upgrade_calls.create_table.call_args

    assert args[0] == TABLE_NAME
    assert kwargs["schema"] == SCHEMA


def test_upgrade_declares_expected_columns(upgrade_calls):
    args, _ = upgrade_calls.create_table.call_args

    columns = [
        item for item in args[1:]
        if isinstance(item, sa.Column)
    ]

    assert {column.name for column in columns} == EXPECTED_COLUMNS
    assert all(not column.nullable for column in columns)


def test_upgrade_declares_uuid_primary_key(upgrade_calls):
    args, _ = upgrade_calls.create_table.call_args

    primary_keys = [
        item for item in args[1:]
        if isinstance(item, sa.PrimaryKeyConstraint)
    ]

    assert len(primary_keys) == 1
    assert primary_keys[0].name == (
        "authorization_integrity_anchors_pkey"
    )
    # Associar as constraints a uma tabela SQLAlchemy em memoria.
    # O Mock de op.create_table nao realiza esta associacao.
    table = sa.Table(
        TABLE_NAME,
        sa.MetaData(),
        *args[1:],
        schema=SCHEMA,
    )

    assert list(table.primary_key.columns.keys()) == [
        "authorization_id"
    ]
    assert isinstance(
        table.c.authorization_id.type,
        sa.dialects.postgresql.UUID,
    )


def test_upgrade_declares_expected_checks(upgrade_calls):
    args, _ = upgrade_calls.create_table.call_args

    checks = {
        item.name: str(item.sqltext)
        for item in args[1:]
        if isinstance(item, sa.CheckConstraint)
    }

    assert set(checks) == EXPECTED_CHECKS

    assert "confirmed_sequence = 0" in checks[
        "ck_auth_anchor_initial_state"
    ]
    assert "confirmed_state = 'prepared'" in checks[
        "ck_auth_anchor_initial_state"
    ]
    assert "updated_at >= created_at" in checks[
        "ck_auth_anchor_timestamps"
    ]


def test_upgrade_creates_schema_before_table(upgrade_calls):
    calls = upgrade_calls.mock_calls

    assert calls[0].args == ("CREATE SCHEMA authorization",)
    assert calls[0][0] == "execute"
    assert calls[1][0] == "create_table"


def test_downgrade_drops_table_before_schema(migration, monkeypatch):
    operations = Mock()
    monkeypatch.setattr(migration, "op", operations)

    migration.downgrade()

    operations.drop_table.assert_called_once_with(
        TABLE_NAME,
        schema=SCHEMA,
    )
    operations.execute.assert_called_once_with(
        "DROP SCHEMA authorization"
    )

    calls = operations.mock_calls
    assert calls[0][0] == "drop_table"
    assert calls[1][0] == "execute"
