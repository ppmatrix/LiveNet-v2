"""Testes locais do plano de execucao administrativa F0.66C."""

from dataclasses import FrozenInstanceError
from pathlib import Path
import sys

import pytest

POSTGRES_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(POSTGRES_DIR))

import f066c_execution_plan as execution_plan
from f066c_admin_operations import ADMIN_OPERATIONS


@pytest.mark.parametrize("operation", sorted(ADMIN_OPERATIONS))
def test_all_approved_operations_prepare(operation):
    plan = execution_plan.prepare_execution_plan(operation)

    assert plan.operation == operation
    assert plan.sql_filename == ADMIN_OPERATIONS[operation]
    assert plan.sql.startswith("BEGIN;\n")
    assert plan.sql.rstrip().endswith("COMMIT;")
    assert plan.sql.count("DO $f066c_guard$") == 1


def test_execution_plan_is_immutable():
    operation = "--execute-transfer"
    plan = execution_plan.prepare_execution_plan(operation)

    with pytest.raises(FrozenInstanceError):
        plan.operation = "--execute-rollback"


def test_unknown_operation_is_rejected():
    with pytest.raises(ValueError):
        execution_plan.prepare_execution_plan("--execute-unknown")


def test_modified_sql_is_rejected(tmp_path, monkeypatch):
    operation = "--execute-transfer"
    original = POSTGRES_DIR / ADMIN_OPERATIONS[operation]
    modified = tmp_path / original.name

    modified.write_bytes(original.read_bytes() + b"\\n-- alterado")

    monkeypatch.setattr(
        execution_plan,
        "resolve_admin_operation",
        lambda selected: modified,
    )

    with pytest.raises(ValueError, match="Integridade SQL divergente"):
        execution_plan.prepare_execution_plan(operation)


def test_modified_guard_is_rejected(tmp_path, monkeypatch):
    operation = "--execute-transfer"
    original_guard = POSTGRES_DIR / "f066c_session_guard.sql"
    modified_guard = tmp_path / original_guard.name

    modified_guard.write_bytes(
        original_guard.read_bytes() + b"\\n-- alterado"
    )

    original_compose = execution_plan.compose_transaction

    def compose_with_modified_guard(sql_path, guard_path):
        return original_compose(sql_path, modified_guard)

    monkeypatch.setattr(
        execution_plan,
        "compose_transaction",
        compose_with_modified_guard,
    )

    with pytest.raises(
        ValueError,
        match="Integridade SQL da guarda divergente",
    ):
        execution_plan.prepare_execution_plan(operation)


def test_plan_preparation_has_no_external_execution(monkeypatch):
    import subprocess

    def forbidden(*args, **kwargs):
        raise AssertionError("Execucao externa proibida")

    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)

    plan = execution_plan.prepare_execution_plan("--execute-transfer")

    assert plan.operation == "--execute-transfer"


@pytest.mark.parametrize(
    "operation",
    (
        "--execute-create-roles",
        "--execute-transfer",
        "--execute-rollback",
        "--execute-grant-app",
        "--execute-revoke-app",
        "--execute-revoke-public-functions",
        "--execute-restore-public-functions",
    ),
)
def test_plan_sql_sha256_matches_content(operation):
    from hashlib import sha256
    from f066c_execution_plan import prepare_execution_plan

    plan = prepare_execution_plan(operation)

    expected = sha256(plan.sql.encode("utf-8")).hexdigest()

    assert plan.sql_sha256 == expected
    assert len(plan.sql_sha256) == 64


def test_plan_sql_sha256_is_immutable():
    from dataclasses import FrozenInstanceError
    from f066c_execution_plan import prepare_execution_plan

    plan = prepare_execution_plan("--execute-transfer")

    with pytest.raises(FrozenInstanceError):
        plan.sql_sha256 = "0" * 64
