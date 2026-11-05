"""Testes PostgreSQL da ancora AUTH-03.

Execucao apenas com ligacao explicita a uma base de testes
isolada e com a migracao f067a01a7230 previamente aplicada.
"""

import os
import re
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.pool import NullPool


pytestmark = pytest.mark.integration

TEST_DATABASE = "livenet_auth03_test"
TEST_REVISION = "f067a01a7230"

INSERT_SQL = text("""
    INSERT INTO authorization.authorization_integrity_anchors (
        authorization_id,
        operation,
        target,
        sql_sha256,
        confirmed_state,
        confirmed_sequence,
        confirmed_hash,
        created_at,
        updated_at
    )
    VALUES (
        :authorization_id,
        :operation,
        :target,
        :sql_sha256,
        :confirmed_state,
        :confirmed_sequence,
        :confirmed_hash,
        :created_at,
        :updated_at
    )
""")


def load_test_configuration(environ):
    """Fail closed, sem expor DSN ou aceitar overrides libpq na query."""
    url = environ.get("AUTH03_ANCHOR_TEST_DATABASE_URL")
    identifier = environ.get("AUTH03_ANCHOR_TEST_SYSTEM_IDENTIFIER", "")
    password_file = environ.get("AUTH03_ANCHOR_TEST_PASSWORD_FILE")
    if not url or not password_file or not re.fullmatch(r"[1-9][0-9]{0,19}", identifier):
        pytest.fail("Configuracao AUTH-03 ausente ou incompleta", pytrace=False)
    if int(identifier) > 2**64 - 1:
        pytest.fail("Identificador AUTH-03 invalido", pytrace=False)
    try:
        parsed = make_url(url)
        valid = (
            parsed.drivername == "postgresql+psycopg"
            and parsed.database == TEST_DATABASE
            and parsed.username
            and parsed.host
            and parsed.host.lower() not in ("localhost", "127.0.0.1", "::1")
            and parsed.port in (None, 5432)
            and parsed.password is None
            and not parsed.query
        )
    except (ValueError, SQLAlchemyError):
        valid = False
    if not valid:
        pytest.fail("Ligacao AUTH-03 nao autorizada", pytrace=False)
    try:
        password = Path(password_file).read_text().strip()
    except (OSError, ValueError):
        pytest.fail("Secret AUTH-03 indisponivel", pytrace=False)
    if not password:
        pytest.fail("Secret AUTH-03 vazio", pytrace=False)
    return parsed.set(password=password), identifier


@contextmanager
def isolated_connection(environ):
    url, expected_identifier = load_test_configuration(environ)
    engine = create_engine(
        url, poolclass=NullPool, echo=False, hide_parameters=True,
        connect_args={"connect_timeout": 5},
    )

    try:
        with engine.connect() as conn:
            transaction = conn.begin()

            try:
                actual = conn.execute(
                    text("SELECT current_database()")
                ).scalar_one()

                if actual != TEST_DATABASE:
                    pytest.fail("Identidade da base de dados inesperada")

                permitted = conn.execute(text(
                    "SELECT pg_catalog.has_function_privilege("
                    "current_user, 'pg_catalog.pg_control_system()', 'EXECUTE')"
                )).scalar_one()
                if not permitted:
                    pytest.fail("Sem EXECUTE em pg_catalog.pg_control_system()", pytrace=False)

                identifier = str(
                    conn.execute(
                        text(
                            "SELECT system_identifier "
                            "FROM pg_catalog.pg_control_system()"
                        )
                    ).scalar_one()
                )

                if identifier != expected_identifier:
                    pytest.fail(
                        "Identificador PostgreSQL nao corresponde "
                        "ao cluster isolado"
                    )

                revision = conn.execute(
                    text(
                        "SELECT version_num "
                        "FROM public.alembic_version"
                    )
                ).scalar_one()

                if revision != TEST_REVISION:
                    pytest.fail(
                        f"Revisao Alembic inesperada: {revision}"
                    )

                yield conn

            finally:
                if transaction.is_active:
                    transaction.rollback()
    except SQLAlchemyError:
        # Erros DBAPI podem incluir credenciais ou parametros; nao os imprimir.
        pytest.fail("Falha PostgreSQL AUTH-03; ligacao/privilegios/revisao por validar", pytrace=False)
    finally:
        engine.dispose()


@pytest.fixture
def connection():
    with isolated_connection(os.environ) as conn:
        yield conn


def valid_record(**overrides):
    record = {
        "authorization_id": uuid4(),
        "operation": "auth03_test_fixture",
        "target": "livenetv2-auth03-test/livenet_auth03_test",
        "sql_sha256": "a" * 64,
        "confirmed_state": "prepared",
        "confirmed_sequence": 0,
        "confirmed_hash": "b" * 64,
        "created_at": "2026-10-20T10:00:00+00:00",
        "updated_at": "2026-10-20T10:00:00+00:00",
    }

    record.update(overrides)
    return record


def test_valid_initial_anchor(connection):
    connection.execute(INSERT_SQL, valid_record())


@pytest.mark.parametrize(
    "changes",
    [
        {"sql_sha256": "invalid"},
        {"confirmed_hash": "INVALID"},
        {"confirmed_state": "unknown"},
        {"confirmed_sequence": -1},
        {"confirmed_state": "authorized", "confirmed_sequence": 0},
        {"confirmed_state": "prepared", "confirmed_sequence": 2},
        {"operation": "   "},
        {"target": "   "},
        {"updated_at": "2026-10-19T10:00:00+00:00"},
    ],
)
def test_invalid_anchor_rejected(connection, changes):
    expected_constraint = {
        "sql_sha256": "ck_auth_anchor_sql_sha256",
        "confirmed_hash": "ck_auth_anchor_confirmed_hash",
        "confirmed_state": "ck_auth_anchor_confirmed_state",
        "confirmed_sequence": "ck_auth_anchor_confirmed_sequence",
        "operation": "ck_auth_anchor_operation_not_empty",
        "target": "ck_auth_anchor_target_not_empty",
        "updated_at": "ck_auth_anchor_timestamps",
    }
    constraint = (
        "ck_auth_anchor_initial_state" if len(changes) == 2
        else expected_constraint[next(iter(changes))]
    )
    with pytest.raises(IntegrityError) as error:
        with connection.begin_nested():
            connection.execute(
                INSERT_SQL,
                valid_record(**changes),
            )
    assert error.value.orig.sqlstate == "23514"
    assert error.value.orig.diag.constraint_name == constraint
    assert connection.execute(text("SELECT 1")).scalar_one() == 1


def test_duplicate_authorization_id_rejected(connection):
    record = valid_record()

    connection.execute(INSERT_SQL, record)

    with pytest.raises(IntegrityError) as error:
        with connection.begin_nested():
            connection.execute(INSERT_SQL, record)
    assert error.value.orig.sqlstate == "23505"
    assert error.value.orig.diag.constraint_name == "authorization_integrity_anchors_pkey"
    assert connection.execute(text("SELECT 1")).scalar_one() == 1


@pytest.mark.parametrize("column", list(valid_record()))
def test_null_rejected(connection, column):
    with pytest.raises(IntegrityError) as error:
        with connection.begin_nested():
            connection.execute(INSERT_SQL, valid_record(**{column: None}))
    assert error.value.orig.sqlstate == "23502"
    assert error.value.orig.diag.column_name == column
    assert connection.execute(text("SELECT 1")).scalar_one() == 1


@pytest.mark.parametrize("column", ["sql_sha256", "confirmed_hash"])
@pytest.mark.parametrize("value", ["", "a" * 63, "g" * 64, "A" * 64])
def test_hash_format_rejected(connection, column, value):
    with pytest.raises(IntegrityError) as error:
        with connection.begin_nested():
            connection.execute(INSERT_SQL, valid_record(**{column: value}))
    assert error.value.orig.diag.constraint_name == f"ck_auth_anchor_{column}"
    assert connection.execute(text("SELECT 1")).scalar_one() == 1


@pytest.mark.parametrize("state", ["authorized", "consumed", "succeeded", "failed", "uncertain"])
def test_valid_later_state(connection, state):
    connection.execute(INSERT_SQL, valid_record(confirmed_state=state, confirmed_sequence=1))


@pytest.mark.parametrize("column", ["operation", "target"])
def test_empty_text_rejected(connection, column):
    with pytest.raises(IntegrityError) as error:
        with connection.begin_nested():
            connection.execute(INSERT_SQL, valid_record(**{column: ""}))
    assert error.value.orig.diag.constraint_name == f"ck_auth_anchor_{column}_not_empty"


def test_timestamp_defaults(connection):
    record = valid_record()
    columns = [column for column in record if column not in ("created_at", "updated_at")]
    result = connection.execute(text(
        "INSERT INTO authorization.authorization_integrity_anchors ("
        + ", ".join(columns) + ") VALUES ("
        + ", ".join(":" + column for column in columns)
        + ") RETURNING created_at, updated_at"
    ), {column: record[column] for column in columns}).one()
    assert result.created_at is not None
    assert result.created_at == result.updated_at


def test_invalid_update_rejected(connection):
    record = valid_record()
    connection.execute(INSERT_SQL, record)
    with pytest.raises(IntegrityError) as error:
        with connection.begin_nested():
            connection.execute(text(
                "UPDATE authorization.authorization_integrity_anchors "
                "SET confirmed_sequence = -1 WHERE authorization_id = :authorization_id"
            ), {"authorization_id": record["authorization_id"]})
    assert error.value.orig.diag.constraint_name == "ck_auth_anchor_confirmed_sequence"
    assert connection.execute(text(
        "SELECT confirmed_sequence FROM authorization.authorization_integrity_anchors "
        "WHERE authorization_id = :authorization_id"
    ), {"authorization_id": record["authorization_id"]}).scalar_one() == 0
