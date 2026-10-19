#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-}"

if [[ "$#" -ne 1 ]]; then
    echo "Uso: $0 identity|diagnostic|guard-test|rollback-test" >&2
    exit 2
fi

case "$MODE" in
    identity|diagnostic|guard-test|rollback-test) ;;
    prepare:--execute-*|inspect:--execute-*) ;;
    *)
        echo "Uso: $0 identity|diagnostic|guard-test|rollback-test" >&2
        exit 2
        ;;
esac

cd "$(dirname "$0")/../.."

./scripts/postgres/f066c_preflight_docker.sh

F066C_MODE="$MODE" python3 - <<'PY'
from pathlib import Path
import os
import subprocess
import sys
import tempfile

sys.path.insert(
    0, str(Path("scripts/postgres").resolve())
)

from f066c_admin_operations import resolve_admin_operation
from f066c_execution_plan import prepare_execution_plan
from f066c_integrity import load_verified_guard

host = "livenetv2-f066c-db-1"
database = "livenet_f0_test"
username = "livenet"
network = "livenetv2-f066c_f066c_backend"
mode = os.environ["F066C_MODE"]

if mode.startswith(("prepare:", "inspect:")):
    inspect = mode.startswith("inspect:")
    operation = mode.split(":", 1)[1]

    try:
        sql_path = resolve_admin_operation(operation)
    except (ValueError, FileNotFoundError) as exc:
        raise SystemExit(f"FAIL: {exc}")

    print(f"PASS: operacao autorizada: {operation}")
    print(f"PASS: SQL identificado: {sql_path.name}")
    if inspect:
        try:
            plan = prepare_execution_plan(operation)
        except (ValueError, UnicodeError, FileNotFoundError) as exc:
            raise SystemExit(f'FAIL: plano administrativo: {exc}')
        if plan.sql_filename != sql_path.name:
            raise SystemExit('FAIL: ficheiro SQL inesperado')
        if not plan.sql.startswith('BEGIN;\n'):
            raise SystemExit('FAIL: transacao inicial inesperada')
        if not plan.sql.rstrip().endswith('COMMIT;'):
            raise SystemExit('FAIL: transacao final inesperada')
        print('PASS: integridade SHA-256 verificada')
        print('PASS: guarda inserida na transacao')
        print('PASS: composicao sem execucao SQL')
    else:
        print("PASS: modo de preparacao sem execucao SQL")

    raise SystemExit(0)

if mode in ("guard-test", "rollback-test"):
    guard_path = Path("scripts/postgres/f066c_session_guard.sql")
    try:
        guard_sql = load_verified_guard(guard_path)
    except (ValueError, UnicodeError) as exc:
        raise SystemExit(f'FAIL: guarda SQL: {exc}')

password_path = Path("secrets/db_password.txt")
password = password_path.read_text().rstrip("\r\n")

if not password or "\n" in password or "\r" in password:
    raise SystemExit("FAIL: formato do segredo invalido")

escaped = password.replace("\\", "\\\\").replace(":", "\\:")

with tempfile.TemporaryDirectory(prefix="livenet-f066c-") as directory:
    pgpass = Path(directory) / "pgpass"
    pgpass.write_text(
        f"{host}:5432:{database}:{username}:{escaped}\n"
    )
    pgpass.chmod(0o600)

    command = [
        "docker", "run", "--rm",
        "--network", network,
        "--user", f"{os.getuid()}:{os.getgid()}",
        "--mount",
        f"type=bind,source={pgpass.resolve()},"
        "target=/run/pgpass,readonly",
        "-e", "PGPASSFILE=/run/pgpass",
        "--entrypoint", "psql",
        "postgres:16-alpine",
        "-X", "-w",
        "-v", "ON_ERROR_STOP=1",
        "-v", "ON_ERROR_ROLLBACK=off",
        "-v", "AUTOCOMMIT=on",
        "-h", host,
        "-p", "5432",
        "-U", username,
        "-d", database,
        "-c",
        """
        SELECT CASE
            WHEN current_user = 'livenet'
             AND session_user = 'livenet'
             AND current_database() = 'livenet_f0_test'
             AND inet_client_addr() IS NOT NULL
            THEN 'PASS'
            ELSE 'FAIL'
        END;
        """,
    ]

    if mode == "rollback-test":
        test_path = Path(
            "scripts/postgres/f066c_rollback_failure_test.sql"
        )
        test_sql = test_path.read_text()

        expected_fragments = (
            "CREATE TABLE inventory.f066c_rollback_probe",
            "INSERT INTO inventory.f066c_rollback_probe",
            "RAISE EXCEPTION",
            "ERRCODE = 'P0001'",
        )

        if any(test_sql.count(fragment) != 1
               for fragment in expected_fragments):
            raise SystemExit("FAIL: SQL de teste inesperado")

        sql = (
            "BEGIN;\n"
            + guard_sql
            + "\n"
            + test_sql
        )

        verification_base_command = command[:-2].copy()
        command = command[:-2] + ["-A", "-t", "-f", "-"]
        command.insert(2, "-i")

        result = subprocess.run(
            command,
            input=sql,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0:
            raise SystemExit(
                "FAIL: excecao intencional nao ocorreu"
            )

        expected_error = (
            "F0.66C: falha intencional para validar rollback"
        )

        error_lines = [
            line.strip()
            for line in result.stderr.splitlines()
            if "ERROR:" in line or "FATAL:" in line
        ]

        if len(error_lines) != 1:
            raise SystemExit(
                "FAIL: quantidade inesperada de erros PostgreSQL: "
                + repr(error_lines)
            )

        if not (
            error_lines[0].startswith("psql:")
            and "ERROR:" in error_lines[0]
            and expected_error in error_lines[0]
        ):
            raise SystemExit(
                "FAIL: erro PostgreSQL diferente do esperado: "
                + error_lines[0]
            )

        output_lines = [
            line.strip()
            for line in result.stdout.splitlines()
        ]

        markers = (
            "F066C_CREATE_COMPLETED",
            "F066C_INSERT_COMPLETED",
        )

        for marker in markers:
            if output_lines.count(marker) != 1:
                raise SystemExit(
                    f"FAIL: marcador ausente ou duplicado: {marker}"
                )

        if output_lines.index(markers[0]) >= output_lines.index(markers[1]):
            raise SystemExit("FAIL: ordem dos marcadores inesperada")

        print("PASS: CREATE TABLE executado")
        print("PASS: INSERT confirmado")
        print("PASS: excecao intencional identificada")
        print("PASS: execucao interrompida antes de COMMIT")

        verification_sql = """
SELECT CASE
    WHEN current_user = 'livenet'
     AND session_user = 'livenet'
     AND current_database() = 'livenet_f0_test'
     AND inet_client_addr() IS NOT NULL
     AND to_regclass('inventory.f066c_rollback_probe') IS NULL
    THEN 'PASS'
    ELSE 'FAIL'
END;
"""

        verification_command = verification_base_command + [
            "-A", "-t", "-c", verification_sql
        ]

        verification = subprocess.run(
            verification_command,
            capture_output=True,
            text=True,
            check=False,
        )

        if verification.returncode != 0:
            raise SystemExit(
                "FAIL: verificacao independente: "
                + verification.stderr.strip()
            )

        if verification.stdout.strip() != "PASS":
            raise SystemExit(
                "FAIL: tabela persistiu ou identidade inesperada"
            )

        print("PASS: segunda ligacao autenticada")
        print("PASS: tabela inexistente apos rollback")
        raise SystemExit(0)

    if mode == "guard-test":
        sql = (
            "BEGIN READ ONLY;\n"
            + guard_sql
            + "\nSELECT 'F066C_GUARD_EXECUTED';\n"
            + "ROLLBACK;\n"
        )

        command = command[:-2] + ["-A", "-t", "-f", "-"]
        command.insert(2, "-i")

        result = subprocess.run(
            command,
            input=sql,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            raise SystemExit(
                f"FAIL: guarda administrativa ({result.returncode}): "
                f"{result.stderr.strip()}"
            )

        if result.stdout.splitlines().count(
            "F066C_GUARD_EXECUTED"
        ) != 1:
            raise SystemExit(
                "FAIL: confirmacao da guarda inesperada"
            )

        print("PASS: guarda executada na sessao autenticada")
        print("PASS: SQL posterior autorizado pela guarda")
        raise SystemExit(0)

    if mode == "diagnostic":
        sql = """
SELECT rolname,
       rolcanlogin,
       rolsuper,
       rolcreatedb,
       rolcreaterole,
       rolreplication,
       rolbypassrls
FROM pg_roles
WHERE rolname IN ('livenet_app', 'livenet_migrator')
  AND current_user = 'livenet'
  AND session_user = 'livenet'
  AND current_database() = 'livenet_f0_test'
  AND inet_client_addr() IS NOT NULL
ORDER BY rolname;
"""
        command = command[:-2] + ["-A", "-t", "-F", "|", "-f", "-"]
        command.insert(2, "-i")
        result = subprocess.run(
            command,
            input=sql,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise SystemExit(
                f"FAIL: diagnostico autenticado ({result.returncode}): "
                f"{result.stderr.strip()} {result.stdout.strip()}"
            )
        lines = [
            line.strip()
            for line in result.stdout.splitlines()
            if line.strip()
        ]

        expected = {
            "livenet_app",
            "livenet_migrator",
        }

        observed = set()

        for line in lines:
            fields = [field.strip() for field in line.split("|")]

            if len(fields) != 7:
                raise SystemExit("FAIL: formato de diagnostico inesperado")

            name, *attributes = fields

            if name not in expected or name in observed:
                raise SystemExit("FAIL: identidade de role inesperada")

            if attributes != ["f"] * 6:
                raise SystemExit(
                    f"FAIL: atributos administrativos inesperados: {name}"
                )

            observed.add(name)

        if observed != expected:
            raise SystemExit("FAIL: conjunto de roles inesperado")

        print("PASS: duas roles esperadas identificadas")
        print("PASS: LOGIN e privilegios administrativos desativados")
        print("PASS: diagnostico na mesma sessao autenticada")
        raise SystemExit(0)

    command.extend(["-A", "-t"])

    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise SystemExit(
            f"FAIL: autenticacao administrativa ({result.returncode}): "
            f"{result.stderr.strip()}"
        )

    if result.stdout.strip() != "PASS":
        raise SystemExit(
            "FAIL: identidade PostgreSQL inesperada"
        )

print("PASS: identidade PostgreSQL autenticada e validada")
PY
