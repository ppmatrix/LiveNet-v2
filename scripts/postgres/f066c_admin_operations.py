"""Registo fechado de operacoes administrativas F0.66C.

Este modulo apenas identifica e valida ficheiros SQL.
Nao executa comandos, nao abre ligacoes e nao altera bases de dados.
"""

from pathlib import Path


ADMIN_OPERATIONS = {
    "--execute-create-roles": "f066c_create_roles.sql",
    "--execute-transfer": "f066c_transfer_ownership.sql",
    "--execute-rollback": "f066c_rollback_ownership.sql",
    "--execute-grant-app": "f066c_grant_app_privileges.sql",
    "--execute-revoke-app": "f066c_revoke_app_privileges.sql",
    "--execute-revoke-public-functions": (
        "f066c_revoke_public_function_execute.sql"
    ),
    "--execute-restore-public-functions": (
        "f066c_restore_public_function_execute.sql"
    ),
}


def resolve_admin_operation(mode: str) -> Path:
    """Devolve o caminho de uma operacao administrativa autorizada."""

    if mode not in ADMIN_OPERATIONS:
        raise ValueError(f"Operacao administrativa nao autorizada: {mode}")

    directory = Path(__file__).resolve().parent
    path = directory / ADMIN_OPERATIONS[mode]

    if not path.is_file():
        raise FileNotFoundError(
            f"Ficheiro SQL administrativo inexistente: {path.name}"
        )

    return path
