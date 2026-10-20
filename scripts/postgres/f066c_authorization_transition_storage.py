"""Serializacao estrita dos registos de transicao AUTH-03.

Sem persistencia, aprovacao real ou execucao administrativa.
"""

from dataclasses import asdict
import json
from uuid import UUID

from f066c_authorization_canonical import canonical_json_bytes
from f066c_authorization_transition_record import (
    ApprovalEvidence,
    AuthorizationTransitionRecord,
    validate_transition_record,
)


REQUIRED_FIELDS = frozenset({
    "schema_version",
    "authorization_id",
    "sequence",
    "from_state",
    "to_state",
    "operation",
    "sql_sha256",
    "previous_hash",
    "timestamp",
    "operator_id",
    "reason",
    "approval_evidence",
})

EVIDENCE_FIELDS = frozenset({
    "operator_uid",
    "approval_method",
    "approval_timestamp",
    "presented_hash",
})

MAX_RECORD_BYTES = 8192


def _record_to_dict(record: AuthorizationTransitionRecord) -> dict:
    validate_transition_record(record)

    result = asdict(record)
    result["authorization_id"] = str(record.authorization_id)
    return result


def serialize_transition_record(
    record: AuthorizationTransitionRecord,
) -> bytes:
    """Produz os bytes canonicos de um registo validado."""

    payload = canonical_json_bytes(_record_to_dict(record))

    if len(payload) > MAX_RECORD_BYTES:
        raise ValueError("Registo excede tamanho permitido")

    return payload


def _reject_duplicate_fields(pairs):
    result = {}

    for key, value in pairs:
        if key in result:
            raise ValueError("Campo JSON duplicado")
        result[key] = value

    return result


def deserialize_transition_record(
    payload: bytes,
) -> AuthorizationTransitionRecord:
    """Reconstroi um registo a partir de bytes JSON canonicos."""

    if not isinstance(payload, bytes):
        raise TypeError("Registo deve ser fornecido em bytes")

    if len(payload) > MAX_RECORD_BYTES:
        raise ValueError("Registo excede tamanho permitido")

    try:
        decoded = payload.decode("utf-8", errors="strict")
        data = json.loads(
            decoded,
            object_pairs_hook=_reject_duplicate_fields,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError("Constante JSON nao permitida")
            ),
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("JSON invalido") from exc

    if not isinstance(data, dict):
        raise ValueError("Estrutura JSON invalida")

    if set(data) != REQUIRED_FIELDS:
        raise ValueError("Campos do registo inesperados")

    if type(data["authorization_id"]) is not str:
        raise ValueError("UUID invalido")

    try:
        identifier = UUID(data["authorization_id"])
    except ValueError as exc:
        raise ValueError("UUID invalido") from exc

    if str(identifier) != data["authorization_id"]:
        raise ValueError("UUID nao canonico")

    evidence_data = data["approval_evidence"]

    if evidence_data is None:
        evidence = None
    else:
        if not isinstance(evidence_data, dict):
            raise ValueError("Evidencia de aprovacao invalida")

        if set(evidence_data) != EVIDENCE_FIELDS:
            raise ValueError("Campos de evidencia inesperados")

        evidence = ApprovalEvidence(**evidence_data)

    record = AuthorizationTransitionRecord(
        schema_version=data["schema_version"],
        authorization_id=identifier,
        sequence=data["sequence"],
        from_state=data["from_state"],
        to_state=data["to_state"],
        operation=data["operation"],
        sql_sha256=data["sql_sha256"],
        previous_hash=data["previous_hash"],
        timestamp=data["timestamp"],
        operator_id=data["operator_id"],
        reason=data["reason"],
        approval_evidence=evidence,
    )

    canonical = serialize_transition_record(record)

    if payload != canonical:
        raise ValueError("Representacao JSON nao canonica")

    return record
