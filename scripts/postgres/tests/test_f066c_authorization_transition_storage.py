"""Testes da serializacao estrita dos registos AUTH-03."""

from dataclasses import replace
import json
from uuid import uuid4

import pytest

from f066c_authorization_transition_record import (
    ApprovalEvidence,
    AuthorizationTransitionRecord,
)
from f066c_authorization_transition_storage import (
    MAX_RECORD_BYTES,
    deserialize_transition_record,
    serialize_transition_record,
)


TIMESTAMP = "2026-10-20T08:00:00.000000Z"


def make_record():
    return AuthorizationTransitionRecord(
        schema_version=1,
        authorization_id=uuid4(),
        sequence=1,
        from_state="prepared",
        to_state="authorized",
        operation="--execute-transfer",
        sql_sha256="a" * 64,
        previous_hash="b" * 64,
        timestamp=TIMESTAMP,
        operator_id="local-operator",
        reason="Aprovacao explicita",
        approval_evidence=ApprovalEvidence(
            operator_uid=1000,
            approval_method="local_interactive",
            approval_timestamp=TIMESTAMP,
            presented_hash="c" * 64,
        ),
    )


def test_roundtrip():
    record = make_record()

    restored = deserialize_transition_record(
        serialize_transition_record(record)
    )

    assert restored == record


def test_serialization_is_deterministic():
    record = make_record()

    assert serialize_transition_record(record) == (
        serialize_transition_record(record)
    )


def test_serialization_preserves_utf8():
    record = replace(make_record(), reason="Aprovação explícita")

    payload = serialize_transition_record(record)

    assert "Aprovação explícita".encode("utf-8") in payload


@pytest.mark.parametrize(
    "field",
    (
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
    ),
)
def test_missing_fields_rejected(field):
    data = json.loads(serialize_transition_record(make_record()))
    del data[field]

    with pytest.raises(ValueError):
        deserialize_transition_record(
            json.dumps(data).encode("utf-8")
        )


def test_unknown_field_rejected():
    data = json.loads(serialize_transition_record(make_record()))
    data["unexpected"] = True

    with pytest.raises(ValueError):
        deserialize_transition_record(
            json.dumps(data).encode("utf-8")
        )


def test_duplicate_field_rejected():
    payload = serialize_transition_record(make_record())
    payload = payload.replace(
        b'"sequence":1',
        b'"sequence":1,"sequence":1',
    )

    with pytest.raises(ValueError, match="duplicado"):
        deserialize_transition_record(payload)


def test_duplicate_evidence_field_rejected():
    payload = serialize_transition_record(make_record())
    payload = payload.replace(
        b'"operator_uid":1000',
        b'"operator_uid":1000,"operator_uid":1000',
    )

    with pytest.raises(ValueError, match="duplicado"):
        deserialize_transition_record(payload)


@pytest.mark.parametrize(
    "payload",
    (
        b"[]",
        b"null",
        b"42",
        b'"text"',
        b'{"invalid":true}',
    ),
)
def test_non_record_json_rejected(payload):
    with pytest.raises(ValueError):
        deserialize_transition_record(payload)


def test_non_canonical_whitespace_rejected():
    payload = serialize_transition_record(make_record())

    with pytest.raises(ValueError, match="nao canonica"):
        deserialize_transition_record(payload + b"\n")


def test_non_canonical_key_order_rejected():
    record = make_record()
    canonical = serialize_transition_record(record)
    data = json.loads(canonical)

    reversed_data = {
        key: data[key]
        for key in reversed(list(data))
    }

    payload = json.dumps(
        reversed_data,
        sort_keys=False,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")

    assert payload != canonical

    with pytest.raises(
        ValueError,
        match="Representacao JSON nao canonica",
    ):
        deserialize_transition_record(payload)


def test_invalid_utf8_rejected():
    with pytest.raises(ValueError):
        deserialize_transition_record(b"\xff")


def test_oversized_payload_rejected():
    with pytest.raises(ValueError):
        deserialize_transition_record(b"x" * (MAX_RECORD_BYTES + 1))


def test_non_bytes_payload_rejected():
    with pytest.raises(TypeError):
        deserialize_transition_record("not bytes")


def test_invalid_evidence_fields_rejected():
    data = json.loads(serialize_transition_record(make_record()))
    data["approval_evidence"]["unexpected"] = True

    with pytest.raises(ValueError):
        deserialize_transition_record(
            json.dumps(data).encode("utf-8")
        )


def test_non_finite_json_constant_rejected():
    payload = serialize_transition_record(make_record())
    payload = payload.replace(
        b'"sequence":1',
        b'"sequence":NaN',
    )

    with pytest.raises(ValueError):
        deserialize_transition_record(payload)
