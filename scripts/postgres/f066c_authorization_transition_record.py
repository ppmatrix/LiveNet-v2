"""Modelo estrutural dos registos de transicao AUTH-03.

Sem persistencia, aprovacao real ou execucao administrativa.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from f066c_admin_operations import ADMIN_OPERATIONS
from f066c_authorization_transition import (
    AuthorizationTransition,
    validate_transition,
)


SCHEMA_VERSION = 1
MAX_OPERATOR_ID_LENGTH = 128
MAX_REASON_LENGTH = 1024


@dataclass(frozen=True)
class ApprovalEvidence:
    operator_uid: int
    approval_method: str
    approval_timestamp: str
    presented_hash: str


@dataclass(frozen=True)
class AuthorizationTransitionRecord:
    schema_version: int
    authorization_id: UUID
    sequence: int
    from_state: str
    to_state: str
    operation: str
    sql_sha256: str
    previous_hash: str
    timestamp: str
    operator_id: str
    reason: str
    approval_evidence: ApprovalEvidence | None


def _validate_sha256(value: str, field: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise ValueError(f"{field} invalido")


def _validate_timestamp(value: str) -> None:
    if not isinstance(value, str):
        raise ValueError("Timestamp invalido")

    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError as exc:
        raise ValueError("Timestamp UTC invalido") from exc

    if parsed.strftime("%Y-%m-%dT%H:%M:%S.%fZ") != value:
        raise ValueError("Timestamp UTC nao canonico")


def _validate_text(value: str, field: str, limit: int) -> None:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > limit
        or value != value.strip()
        or any(ord(char) < 32 or ord(char) == 127 for char in value)
    ):
        raise ValueError(f"{field} invalido")


def validate_transition_record(
    record: AuthorizationTransitionRecord,
) -> None:
    """Valida apenas a estrutura e a transicao declarada."""

    if not isinstance(record, AuthorizationTransitionRecord):
        raise TypeError("Registo de transicao invalido")

    if type(record.schema_version) is not int or record.schema_version != 1:
        raise ValueError("Versao de esquema invalida")

    if not isinstance(record.authorization_id, UUID):
        raise ValueError("UUID invalido")

    if str(record.authorization_id) != str(
        UUID(str(record.authorization_id))
    ):
        raise ValueError("UUID nao canonico")

    transition = AuthorizationTransition(
        authorization_id=record.authorization_id,
        sequence=record.sequence,
        from_state=record.from_state,
        to_state=record.to_state,
    )

    validate_transition(
        transition,
        current_state=record.from_state,
        expected_sequence=record.sequence,
        expected_authorization_id=record.authorization_id,
    )

    if not isinstance(record.from_state, str):
        raise ValueError("Estado anterior invalido")

    if not isinstance(record.to_state, str):
        raise ValueError("Estado seguinte invalido")

    if (
        not isinstance(record.operation, str)
        or record.operation not in ADMIN_OPERATIONS
    ):
        raise ValueError("Operacao administrativa desconhecida")

    _validate_sha256(record.sql_sha256, "sql_sha256")
    _validate_sha256(record.previous_hash, "previous_hash")
    _validate_timestamp(record.timestamp)
    _validate_text(
        record.operator_id,
        "operator_id",
        MAX_OPERATOR_ID_LENGTH,
    )
    _validate_text(record.reason, "reason", MAX_REASON_LENGTH)

    evidence = record.approval_evidence

    if record.to_state == "authorized":
        if not isinstance(evidence, ApprovalEvidence):
            raise ValueError("Evidencia de aprovacao obrigatoria")

        if (
            type(evidence.operator_uid) is not int
            or evidence.operator_uid < 0
        ):
            raise ValueError("UID de operador invalido")

        if (
            not isinstance(evidence.approval_method, str)
            or evidence.approval_method != "local_interactive"
        ):
            raise ValueError("Metodo de aprovacao invalido")

        _validate_timestamp(evidence.approval_timestamp)
        _validate_sha256(evidence.presented_hash, "presented_hash")

        if evidence.approval_timestamp != record.timestamp:
            raise ValueError("Timestamp de aprovacao divergente")
    elif evidence is not None:
        raise ValueError("Evidencia de aprovacao inesperada")
