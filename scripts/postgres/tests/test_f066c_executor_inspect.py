"""Testes do percurso inspect sem Docker nem PostgreSQL."""

from pathlib import Path
import shutil
import subprocess

import pytest

SOURCE = Path(__file__).resolve().parents[1]

OPERATIONS = (
    "--execute-create-roles",
    "--execute-transfer",
    "--execute-rollback",
    "--execute-grant-app",
    "--execute-revoke-app",
    "--execute-revoke-public-functions",
    "--execute-restore-public-functions",
)

REQUIRED_FILES = (
    "f066c_admin_psql.sh",
    "f066c_admin_operations.py",
    "f066c_execution_plan.py",
    "f066c_transaction.py",
    "f066c_integrity.py",
    "f066c_session_guard.sql",
    "f066c_create_roles.sql",
    "f066c_transfer_ownership.sql",
    "f066c_rollback_ownership.sql",
    "f066c_grant_app_privileges.sql",
    "f066c_revoke_app_privileges.sql",
    "f066c_revoke_public_function_execute.sql",
    "f066c_restore_public_function_execute.sql",
)


@pytest.fixture
def isolated_executor(tmp_path):
    target = tmp_path / "scripts" / "postgres"
    target.mkdir(parents=True)

    for filename in REQUIRED_FILES:
        shutil.copy2(SOURCE / filename, target / filename)

    preflight = target / "f066c_preflight_docker.sh"
    preflight.write_text(
        "#!/usr/bin/env bash\n"
        "echo 'PASS: preflight simulado'\n"
    )
    preflight.chmod(0o700)

    # Sem credenciais: qualquer tentativa de continuar para
    # a autenticacao deve falhar.
    return target / "f066c_admin_psql.sh"


@pytest.mark.parametrize("operation", OPERATIONS)
def test_inspect_modes(isolated_executor, operation):
    result = subprocess.run(
        ["bash", str(isolated_executor), f"inspect:{operation}"],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "PASS: integridade SHA-256 verificada" in result.stdout
    assert "PASS: guarda inserida na transacao" in result.stdout
    assert "PASS: composicao sem execucao SQL" in result.stdout


def test_unknown_operation_rejected(isolated_executor):
    result = subprocess.run(
        ["bash", str(isolated_executor), "inspect:--execute-unknown"],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    assert result.returncode != 0
    assert "FAIL:" in result.stderr


def test_direct_execution_rejected(isolated_executor):
    result = subprocess.run(
        ["bash", str(isolated_executor), "--execute-transfer"],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    assert result.returncode != 0


def _run_with_forbidden_docker(isolated_executor, tmp_path, mode):
    import os

    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()

    marker = tmp_path / "docker-invoked"

    docker = fake_bin / "docker"
    docker.write_text(
        "#!/usr/bin/env bash\\n"
        f"touch '{marker}'\\n"
        "echo 'FAIL: Docker nao autorizado' >&2\\n"
        "exit 99\\n"
    )
    docker.chmod(0o700)

    environment = os.environ.copy()
    environment["PATH"] = str(fake_bin) + os.pathsep + environment["PATH"]

    result = subprocess.run(
        ["bash", str(isolated_executor), mode],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
        env=environment,
    )

    return result, marker


def test_inspect_does_not_invoke_docker(isolated_executor, tmp_path):
    result, marker = _run_with_forbidden_docker(
        isolated_executor,
        tmp_path,
        "inspect:--execute-transfer",
    )

    assert result.returncode == 0, result.stderr
    assert not marker.exists()
    assert "PASS: composicao sem execucao SQL" in result.stdout


def test_prepare_does_not_invoke_docker(isolated_executor, tmp_path):
    result, marker = _run_with_forbidden_docker(
        isolated_executor,
        tmp_path,
        "prepare:--execute-transfer",
    )

    assert result.returncode == 0, result.stderr
    assert not marker.exists()
    assert "PASS: modo de preparacao sem execucao SQL" in result.stdout
