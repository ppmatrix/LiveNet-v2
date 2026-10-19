"""Serializacao de autorizacoes F0.66C, sem acesso ao disco."""

import json
from uuid import UUID

from f066c_authorization import (
    AdministrativeAuthorization,
    ALLOWED_STATES,
    ISOLATED_TARGET,
)
from f066c_admin_operations import ADMIN_OPERATIONS


SCHEMA_VERSION = 1

REQUIRED_FIELDS = frozenset({
    "schema_version",
    "authorization_id",
    "operation",
    "target",
    "sql_sha256",
    "state",
})


def serialize_authorization(
    authorization: AdministrativeAuthorization,
) -> str:
    """Converte uma autorizacao em JSON validado."""

    if not isinstance(authorization, AdministrativeAuthorization):
        raise TypeError("Autorizacao invalida")

    validate_record(authorization)

    record = {
        "schema_version": SCHEMA_VERSION,
        "authorization_id": str(authorization.authorization_id),
        "operation": authorization.operation,
        "target": authorization.target,
        "sql_sha256": authorization.sql_sha256,
        "state": authorization.state,
    }

    return json.dumps(record, sort_keys=True, separators=(",", ":"))


def validate_record(
    authorization: AdministrativeAuthorization,
) -> None:
    """Valida os campos estruturais de uma autorizacao."""

    if not isinstance(authorization.authorization_id, UUID):
        raise ValueError("UUID invalido")

    if authorization.operation not in ADMIN_OPERATIONS:
        raise ValueError("Operacao desconhecida")

    if authorization.target != ISOLATED_TARGET:
        raise ValueError("Destino inesperado")

    digest = authorization.sql_sha256

    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(c not in "0123456789abcdef" for c in digest)
    ):
        raise ValueError("SHA-256 invalido")

    if authorization.state not in ALLOWED_STATES:
        raise ValueError("Estado invalido")


def deserialize_authorization(
    payload: str,
) -> AdministrativeAuthorization:
    """Reconstrói uma autorizacao a partir de JSON estrito."""

    def reject_duplicates(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Campo JSON duplicado")
            result[key] = value
        return result

    record = json.loads(
        payload,
        object_pairs_hook=reject_duplicates,
    )

    if not isinstance(record, dict):
        raise ValueError("Estrutura JSON invalida")

    if set(record) != REQUIRED_FIELDS:
        raise ValueError("Campos JSON inesperados")

    if type(record["schema_version"]) is not int:
        raise ValueError("Versao de esquema invalida")

    if record["schema_version"] != SCHEMA_VERSION:
        raise ValueError("Versao de esquema nao suportada")

    if not isinstance(record["authorization_id"], str):
        raise ValueError("UUID invalido")

    try:
        identifier = UUID(record["authorization_id"])
    except ValueError as exc:
        raise ValueError("UUID invalido") from exc

    authorization = AdministrativeAuthorization(
        authorization_id=identifier,
        operation=record["operation"],
        target=record["target"],
        sql_sha256=record["sql_sha256"],
        state=record["state"],
    )

    validate_record(authorization)

    return authorization
