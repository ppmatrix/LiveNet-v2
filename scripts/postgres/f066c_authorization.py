"""Modelo de autorizacao administrativa F0.66C.

Sem persistencia, acesso externo ou execucao SQL.
"""

from dataclasses import dataclass
from hashlib import sha256
from uuid import UUID, uuid4

from f066c_admin_operations import ADMIN_OPERATIONS
from f066c_execution_plan import AdministrativeExecutionPlan


ISOLATED_TARGET = "livenetv2-f066c/livenet_f0_test"

ALLOWED_STATES = frozenset({
    "prepared",
    "authorized",
    "consumed",
    "succeeded",
    "failed",
    "uncertain",
})


@dataclass(frozen=True)
class AdministrativeAuthorization:
    authorization_id: UUID
    operation: str
    target: str
    sql_sha256: str
    state: str


def create_authorization(
    plan: AdministrativeExecutionPlan,
) -> AdministrativeAuthorization:
    """Cria uma autorizacao preparada, sem a confirmar."""

    if not isinstance(plan, AdministrativeExecutionPlan):
        raise TypeError("Plano administrativo invalido")

    if (
        plan.operation not in ADMIN_OPERATIONS
        or plan.sql_filename != ADMIN_OPERATIONS[plan.operation]
    ):
        raise ValueError("Operacao ou ficheiro SQL nao autorizado")

    if not isinstance(plan.sql_sha256, str) or not all(
        char in '0123456789abcdef' for char in plan.sql_sha256
    ) or len(plan.sql_sha256) != 64:
        raise ValueError("Identidade SHA-256 invalida")

    expected = sha256(plan.sql.encode("utf-8")).hexdigest()

    if plan.sql_sha256 != expected:
        raise ValueError("Identidade do plano divergente")

    return AdministrativeAuthorization(
        authorization_id=uuid4(),
        operation=plan.operation,
        target=ISOLATED_TARGET,
        sql_sha256=plan.sql_sha256,
        state="prepared",
    )


def validate_authorization(
    authorization: AdministrativeAuthorization,
    plan: AdministrativeExecutionPlan,
) -> None:
    """Valida a correspondencia entre autorizacao e plano."""

    if not isinstance(authorization, AdministrativeAuthorization):
        raise TypeError("Autorizacao invalida")

    if not isinstance(plan, AdministrativeExecutionPlan):
        raise TypeError("Plano administrativo invalido")

    if not isinstance(authorization.authorization_id, UUID):
        raise ValueError("Identificador de autorizacao invalido")

    if (
        not isinstance(authorization.sql_sha256, str)
        or len(authorization.sql_sha256) != 64
        or any(
            char not in '0123456789abcdef'
            for char in authorization.sql_sha256
        )
    ):
        raise ValueError("SHA-256 da autorizacao invalido")

    if (
        plan.operation not in ADMIN_OPERATIONS
        or plan.sql_filename != ADMIN_OPERATIONS[plan.operation]
    ):
        raise ValueError("Operacao ou ficheiro SQL nao autorizado")

    if authorization.target != ISOLATED_TARGET:
        raise ValueError("Destino administrativo inesperado")

    if authorization.operation != plan.operation:
        raise ValueError("Operacao administrativa divergente")

    if authorization.sql_sha256 != plan.sql_sha256:
        raise ValueError("Identidade do plano divergente")

    if authorization.state not in ALLOWED_STATES:
        raise ValueError("Estado de autorizacao invalido")

    if authorization.state != "prepared":
        raise ValueError("Autorizacao nao esta no estado preparado")

    expected = sha256(
        plan.sql.encode("utf-8")
    ).hexdigest()

    if plan.sql_sha256 != expected:
        raise ValueError("Conteudo do plano divergente")
