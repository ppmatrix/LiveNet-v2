"""Testes locais de seguranca dos executores F0.66C."""

from pathlib import Path
import subprocess
import sys
import tempfile

import pytest


POSTGRES_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(POSTGRES_DIR))

from f066c_admin_operations import (
    ADMIN_OPERATIONS,
    resolve_admin_operation,
)
from f066c_transaction import compose_transaction


GUARD = POSTGRES_DIR / "f066c_session_guard.sql"


@pytest.mark.parametrize("mode", sorted(ADMIN_OPERATIONS))
def test_approved_sql_composition(mode):
    path = resolve_admin_operation(mode)
    result = compose_transaction(path, GUARD)

    assert result.startswith("BEGIN;\n")
    assert result.rstrip().endswith("COMMIT;")
    assert result.count("DO $f066c_guard$") == 1


@pytest.mark.parametrize(
    "modification",
    [
        "\nEND;\n",
        "\nCOMMIT;\n",
        "\nROLLBACK;\n",
        "\nSAVEPOINT unexpected;\n",
        "\n\\echo unexpected\n",
    ],
)
def test_modified_sql_rejected(modification):
    original = resolve_admin_operation("--execute-create-roles")
    source = original.read_text()

    assert source.count("\nCOMMIT;") == 1
    modified = source.replace(
        "\nCOMMIT;",
        modification + "\nCOMMIT;",
        1,
    )

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / original.name
        path.write_text(modified)

        with pytest.raises(ValueError, match="Integridade SQL"):
            compose_transaction(path, GUARD)



def test_original_guard_accepted():
    operation = resolve_admin_operation("--execute-create-roles")
    result = compose_transaction(operation, GUARD)

    assert result.startswith("BEGIN;\n")
    assert result.count("DO $f066c_guard$") == 1
    assert result.rstrip().endswith("COMMIT;")


@pytest.mark.parametrize(
    "modification",
    [
        b"\\n-- alteracao de teste\\n",
        b"\\nSELECT 1;\\n",
        b" ",
    ],
)
def test_modified_guard_rejected(modification):
    operation = resolve_admin_operation("--execute-create-roles")

    with tempfile.TemporaryDirectory() as directory:
        modified = Path(directory) / GUARD.name
        modified.write_bytes(GUARD.read_bytes() + modification)

        with pytest.raises(
            ValueError,
            match="Integridade SQL da guarda",
        ):
            compose_transaction(operation, modified)


def test_unknown_sql_rejected():
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "unknown.sql"
        path.write_bytes(
            resolve_admin_operation(
                "--execute-create-roles"
            ).read_bytes()
        )

        with pytest.raises(ValueError, match="nao autorizado"):
            compose_transaction(path, GUARD)


@pytest.mark.parametrize(
    "filename",
    [
        "f066c_run_create_roles.sh",
        "f066c_run_ownership.sh",
    ],
)
def test_legacy_executor_blocked(filename):
    result = subprocess.run(
        ["bash", str(POSTGRES_DIR / filename), "--execute-transfer"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 3
    assert "BLOQUEADO:" in result.stderr


def test_direct_admin_execution_blocked():
    result = subprocess.run(
        [
            "bash",
            str(POSTGRES_DIR / "f066c_admin_psql.sh"),
            "--execute-transfer",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "Uso:" in result.stderr


def test_psql_client_security_options():
    executor = (
        POSTGRES_DIR / "f066c_admin_psql.sh"
    ).read_text()

    assert '"-X", "-w"' in executor
    assert '"-v", "ON_ERROR_STOP=1"' in executor
    assert '"-v", "ON_ERROR_ROLLBACK=off"' in executor
    assert '"-v", "AUTOCOMMIT=on"' in executor
    assert '"--entrypoint", "psql"' in executor
    assert '"PGPASSFILE=/run/pgpass"' in executor


@pytest.mark.parametrize("mode", sorted(ADMIN_OPERATIONS))
def test_composed_transaction_boundaries(mode):
    operation = resolve_admin_operation(mode)
    sql = compose_transaction(operation, GUARD)

    lines = sql.splitlines()

    assert lines[0] == "BEGIN;"
    assert lines[-1] == "COMMIT;"
    assert sql.count("DO $f066c_guard$") == 1


def test_direct_administrative_modes_remain_disabled():
    executor = (
        POSTGRES_DIR / "f066c_admin_psql.sh"
    ).read_text()

    assert 'prepare:--execute-*|inspect:--execute-*) ;;' in executor
    assert 'identity|diagnostic|guard-test|rollback-test) ;;' in executor
