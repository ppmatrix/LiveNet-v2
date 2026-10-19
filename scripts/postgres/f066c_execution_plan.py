"""Preparacao de planos administrativos F0.66C sem efeitos externos."""

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from f066c_admin_operations import resolve_admin_operation
from f066c_transaction import compose_transaction


@dataclass(frozen=True)
class AdministrativeExecutionPlan:
    operation: str
    sql_filename: str
    sql: str
    sql_sha256: str


def prepare_execution_plan(operation: str) -> AdministrativeExecutionPlan:
    """Valida e prepara uma operacao administrativa autorizada."""

    sql_path = resolve_admin_operation(operation)
    guard_path = Path(__file__).resolve().parent / (
        "f066c_session_guard.sql"
    )

    composed_sql = compose_transaction(sql_path, guard_path)

    return AdministrativeExecutionPlan(
        operation=operation,
        sql_filename=sql_path.name,
        sql=composed_sql,
        sql_sha256=sha256(composed_sql.encode('utf-8')).hexdigest(),
    )
