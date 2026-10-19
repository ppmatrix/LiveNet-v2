"""Testes de serializacao e validacao JSON F0.66C."""

from dataclasses import FrozenInstanceError
import json

import pytest

from f066c_admin_operations import ADMIN_OPERATIONS
from f066c_authorization import create_authorization
from f066c_authorization_storage import (
    deserialize_authorization,
    serialize_authorization,
)
from f066c_execution_plan import prepare_execution_plan


@pytest.fixture
def valid_record():
    plan = prepare_execution_plan("--execute-transfer")
    authorization = create_authorization(plan)
    return json.loads(serialize_authorization(authorization))


@pytest.mark.parametrize("operation", tuple(ADMIN_OPERATIONS))
def test_roundtrip_all_operations(operation):
    plan = prepare_execution_plan(operation)
    original = create_authorization(plan)

    restored = deserialize_authorization(
        serialize_authorization(original)
    )

    assert restored == original


@pytest.mark.parametrize(
    "field,value",
    (
        ("schema_version", 2),
        ("schema_version", True),
        ("authorization_id", "invalid"),
        ("authorization_id", 123),
        ("operation", "--execute-unknown"),
        ("target", "livenetv2/livenet"),
        ("sql_sha256", "invalid"),
        ("sql_sha256", "A" * 64),
        ("state", "invalid"),
    ),
)
def test_invalid_field_rejected(valid_record, field, value):
    valid_record[field] = value

    with pytest.raises((ValueError, TypeError)):
        deserialize_authorization(json.dumps(valid_record))


def test_duplicate_json_field_rejected(valid_record):
    payload = json.dumps(valid_record)
    payload = payload.replace(
        '"state":"prepared"',
        '"state":"prepared","state":"authorized"',
    )

    # json.dumps utiliza espacos por omissao; construir
    # explicitamente o caso duplicado.
    payload = (
        '{"schema_version":1,'
        '"state":"prepared","state":"authorized"}'
    )

    with pytest.raises(ValueError):
        deserialize_authorization(payload)


def test_unknown_field_rejected(valid_record):
    valid_record["unexpected"] = True

    with pytest.raises(ValueError):
        deserialize_authorization(json.dumps(valid_record))


def test_missing_field_rejected(valid_record):
    del valid_record["sql_sha256"]

    with pytest.raises(ValueError):
        deserialize_authorization(json.dumps(valid_record))


@pytest.mark.parametrize("payload", ("[]", "null", "42", '"text"'))
def test_non_object_json_rejected(payload):
    with pytest.raises(ValueError):
        deserialize_authorization(payload)


def test_restored_authorization_is_immutable(valid_record):
    restored = deserialize_authorization(json.dumps(valid_record))

    with pytest.raises(FrozenInstanceError):
        restored.state = "authorized"
