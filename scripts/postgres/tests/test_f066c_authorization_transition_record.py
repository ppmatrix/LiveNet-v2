"""Testes estruturais dos registos de transicao AUTH-03."""

from dataclasses import FrozenInstanceError, replace
from uuid import uuid4

import pytest

from f066c_authorization_transition_record import (
    ApprovalEvidence,
    AuthorizationTransitionRecord,
    validate_transition_record,
)


TIMESTAMP = "2026-10-20T08:00:00.000000Z"
DIGEST = "a" * 64


def make_record(**changes):
    record = AuthorizationTransitionRecord(
        schema_version=1,
        authorization_id=uuid4(),
        sequence=1,
        from_state="prepared",
        to_state="authorized",
        operation="--execute-transfer",
        sql_sha256=DIGEST,
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
    return replace(record, **changes)


def test_valid_authorization_record():
    validate_transition_record(make_record())


def test_record_is_immutable():
    record = make_record()
    with pytest.raises(FrozenInstanceError):
        record.to_state = "consumed"


@pytest.mark.parametrize(
    "changes",
    (
        {"schema_version": 2},
        {"schema_version": True},
        {"authorization_id": "invalid"},
        {"sequence": 0},
        {"sequence": True},
        {"from_state": "consumed"},
        {"to_state": "consumed"},
        {"operation": "--execute-unknown"},
        {"sql_sha256": "invalid"},
        {"previous_hash": "A" * 64},
        {"timestamp": "2026-02-30T08:00:00.000000Z"},
        {"timestamp": "2026-10-20T08:00:00Z"},
        {"operator_id": ""},
        {"operator_id": "x" * 129},
        {"reason": "invalid\nreason"},
        {"reason": "x" * 1025},
        {"approval_evidence": None},
    ),
)
def test_invalid_record_rejected(changes):
    with pytest.raises((ValueError, TypeError)):
        validate_transition_record(make_record(**changes))


@pytest.mark.parametrize(
    "changes",
    (
        {"operator_uid": -1},
        {"operator_uid": True},
        {"approval_method": "automatic"},
        {"approval_timestamp": "invalid"},
        {"presented_hash": "invalid"},
    ),
)
def test_invalid_approval_evidence_rejected(changes):
    record = make_record()
    evidence = replace(record.approval_evidence, **changes)

    with pytest.raises(ValueError):
        validate_transition_record(
            replace(record, approval_evidence=evidence)
        )


@pytest.mark.parametrize(
    "final_state",
    ("succeeded", "failed", "uncertain"),
)
def test_valid_final_states_without_approval_evidence(final_state):
    record = make_record(
        from_state="consumed",
        to_state=final_state,
        approval_evidence=None,
    )
    validate_transition_record(record)


def test_valid_consumed_state_without_approval_evidence():
    record = make_record(
        from_state="authorized",
        to_state="consumed",
        approval_evidence=None,
    )
    validate_transition_record(record)


def test_unexpected_approval_evidence_rejected():
    record = make_record(
        from_state="authorized",
        to_state="consumed",
    )

    with pytest.raises(ValueError):
        validate_transition_record(record)


def test_approval_timestamp_must_match_record_timestamp():
    record = make_record()
    evidence = replace(
        record.approval_evidence,
        approval_timestamp="2026-10-20T08:00:01.000000Z",
    )

    with pytest.raises(ValueError):
        validate_transition_record(
            replace(record, approval_evidence=evidence)
        )



def test_approval_evidence_is_immutable():
    record = make_record()

    with pytest.raises(FrozenInstanceError):
        record.approval_evidence.operator_uid = 2000


@pytest.mark.parametrize(
    "changes",
    (
        {"from_state": None},
        {"from_state": 123},
        {"to_state": None},
        {"to_state": 123},
        {"operation": None},
        {"operation": 123},
        {"operation": []},
    ),
)
def test_invalid_field_types_rejected(changes):
    with pytest.raises((ValueError, TypeError)):
        validate_transition_record(make_record(**changes))


@pytest.mark.parametrize(
    "method",
    (None, 123, [], {}),
)
def test_invalid_approval_method_types_rejected(method):
    record = make_record()
    evidence = replace(
        record.approval_evidence,
        approval_method=method,
    )

    with pytest.raises((ValueError, TypeError)):
        validate_transition_record(
            replace(record, approval_evidence=evidence)
        )
