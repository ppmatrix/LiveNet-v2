"""Testes de integridade dos elos AUTH-03."""

from dataclasses import replace
from hashlib import sha256
from uuid import uuid4

import pytest

from f066c_authorization import AdministrativeAuthorization
from f066c_authorization_chain import (
    initial_authorization_hash,
    transition_record_hash,
    validate_chain_link,
)
from f066c_authorization_storage import serialize_authorization
from f066c_authorization_transition_record import (
    ApprovalEvidence,
    AuthorizationTransitionRecord,
)
from f066c_authorization_transition_storage import (
    serialize_transition_record,
)


TIMESTAMP = "2026-10-20T08:00:00.000000Z"


def make_authorization():
    return AdministrativeAuthorization(
        authorization_id=uuid4(),
        operation="--execute-transfer",
        target="livenetv2-f066c/livenet_f0_test",
        sql_sha256="a" * 64,
        state="prepared",
    )


def make_transition(authorization, previous_hash):
    return AuthorizationTransitionRecord(
        schema_version=1,
        authorization_id=authorization.authorization_id,
        sequence=1,
        from_state="prepared",
        to_state="authorized",
        operation=authorization.operation,
        sql_sha256=authorization.sql_sha256,
        previous_hash=previous_hash,
        timestamp=TIMESTAMP,
        operator_id="local-operator",
        reason="Teste estrutural",
        approval_evidence=ApprovalEvidence(
            operator_uid=1000,
            approval_method="local_interactive",
            approval_timestamp=TIMESTAMP,
            presented_hash="c" * 64,
        ),
    )


def test_initial_hash_matches_original_serialization():
    authorization = make_authorization()

    expected = sha256(
        serialize_authorization(authorization).encode("utf-8")
    ).hexdigest()

    assert initial_authorization_hash(authorization) == expected


def test_initial_hash_is_deterministic():
    authorization = make_authorization()

    assert initial_authorization_hash(
        authorization
    ) == initial_authorization_hash(authorization)


def test_initial_hash_rejects_non_prepared():
    authorization = replace(make_authorization(), state="authorized")

    with pytest.raises(ValueError):
        initial_authorization_hash(authorization)


def test_initial_hash_rejects_wrong_type():
    with pytest.raises(TypeError):
        initial_authorization_hash(None)


def test_transition_hash_matches_serialized_bytes():
    authorization = make_authorization()
    record = make_transition(
        authorization,
        initial_authorization_hash(authorization),
    )

    expected = sha256(serialize_transition_record(record)).hexdigest()

    assert transition_record_hash(record) == expected


def test_valid_first_chain_link():
    authorization = make_authorization()
    initial_hash = initial_authorization_hash(authorization)
    record = make_transition(authorization, initial_hash)

    validate_chain_link(
        record,
        expected_previous_hash=initial_hash,
    )


def test_modified_previous_hash_rejected():
    authorization = make_authorization()
    initial_hash = initial_authorization_hash(authorization)
    record = make_transition(authorization, "b" * 64)

    with pytest.raises(ValueError, match="divergente"):
        validate_chain_link(
            record,
            expected_previous_hash=initial_hash,
        )


@pytest.mark.parametrize(
    "invalid_hash",
    (
        "",
        "a" * 63,
        "A" * 64,
        "z" * 64,
        None,
        123,
    ),
)
def test_invalid_expected_hash_rejected(invalid_hash):
    authorization = make_authorization()
    record = make_transition(
        authorization,
        initial_authorization_hash(authorization),
    )

    with pytest.raises(ValueError):
        validate_chain_link(
            record,
            expected_previous_hash=invalid_hash,
        )


def test_transition_hash_changes_when_reason_changes():
    authorization = make_authorization()
    record = make_transition(
        authorization,
        initial_authorization_hash(authorization),
    )

    modified = replace(record, reason="Motivo alterado")

    assert transition_record_hash(record) != transition_record_hash(
        modified
    )
