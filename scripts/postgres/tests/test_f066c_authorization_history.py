"""Testes da reconstrucao do historico AUTH-03."""

from dataclasses import replace
from uuid import uuid4

import pytest

from f066c_authorization import AdministrativeAuthorization
from f066c_authorization_chain import (
    initial_authorization_hash,
    transition_record_hash,
)
from f066c_authorization_history import (
    reconstruct_authorization_history,
)
from f066c_authorization_transition_record import (
    ApprovalEvidence,
    AuthorizationTransitionRecord,
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


def make_record(
    authorization,
    sequence,
    from_state,
    to_state,
    previous_hash,
):
    evidence = None

    if to_state == "authorized":
        evidence = ApprovalEvidence(
            operator_uid=1000,
            approval_method="local_interactive",
            approval_timestamp=TIMESTAMP,
            presented_hash="c" * 64,
        )

    return AuthorizationTransitionRecord(
        schema_version=1,
        authorization_id=authorization.authorization_id,
        sequence=sequence,
        from_state=from_state,
        to_state=to_state,
        operation=authorization.operation,
        sql_sha256=authorization.sql_sha256,
        previous_hash=previous_hash,
        timestamp=TIMESTAMP,
        operator_id="local-operator",
        reason="Teste de historico",
        approval_evidence=evidence,
    )


def make_history(final_state="succeeded"):
    authorization = make_authorization()
    previous_hash = initial_authorization_hash(authorization)

    transitions = []

    steps = [
        ("prepared", "authorized"),
        ("authorized", "consumed"),
        ("consumed", final_state),
    ]

    for sequence, (from_state, to_state) in enumerate(steps, 1):
        record = make_record(
            authorization,
            sequence,
            from_state,
            to_state,
            previous_hash,
        )
        transitions.append(record)
        previous_hash = transition_record_hash(record)

    return authorization, transitions


def test_empty_history_is_prepared():
    authorization = make_authorization()

    state = reconstruct_authorization_history(authorization, [])

    assert state.state == "prepared"
    assert state.next_sequence == 1
    assert state.transition_count == 0
    assert state.last_hash == initial_authorization_hash(authorization)


@pytest.mark.parametrize(
    "final_state",
    ("succeeded", "failed", "uncertain"),
)
def test_complete_history(final_state):
    authorization, transitions = make_history(final_state)

    state = reconstruct_authorization_history(
        authorization,
        transitions,
    )

    assert state.state == final_state
    assert state.next_sequence == 4
    assert state.transition_count == 3
    assert state.last_hash == transition_record_hash(transitions[-1])


@pytest.mark.parametrize("count, expected", ((1, "authorized"), (2, "consumed")))
def test_valid_partial_history(count, expected):
    authorization, transitions = make_history()

    state = reconstruct_authorization_history(
        authorization,
        transitions[:count],
    )

    assert state.state == expected
    assert state.next_sequence == count + 1


def test_sequence_gap_rejected():
    authorization, transitions = make_history()
    transitions[1] = replace(transitions[1], sequence=3)

    with pytest.raises(ValueError):
        reconstruct_authorization_history(authorization, transitions)


def test_duplicate_sequence_rejected():
    authorization, transitions = make_history()
    transitions[1] = replace(transitions[1], sequence=1)

    with pytest.raises(ValueError):
        reconstruct_authorization_history(authorization, transitions)


def test_reordered_transitions_rejected():
    authorization, transitions = make_history()
    transitions[0], transitions[1] = transitions[1], transitions[0]

    with pytest.raises(ValueError):
        reconstruct_authorization_history(authorization, transitions)


def test_foreign_uuid_rejected():
    authorization, transitions = make_history()
    transitions[0] = replace(transitions[0], authorization_id=uuid4())

    with pytest.raises(ValueError, match="UUID"):
        reconstruct_authorization_history(authorization, transitions)


def test_operation_mismatch_rejected():
    authorization, transitions = make_history()
    transitions[0] = replace(
        transitions[0],
        operation="--execute-rollback",
    )

    with pytest.raises(ValueError, match="Operacao"):
        reconstruct_authorization_history(authorization, transitions)


def test_sql_hash_mismatch_rejected():
    authorization, transitions = make_history()
    transitions[0] = replace(transitions[0], sql_sha256="b" * 64)

    with pytest.raises(ValueError, match="SQL"):
        reconstruct_authorization_history(authorization, transitions)


def test_modified_previous_hash_rejected():
    authorization, transitions = make_history()
    transitions[1] = replace(
        transitions[1],
        previous_hash="f" * 64,
    )

    with pytest.raises(ValueError, match="encadeamento|Encadeamento"):
        reconstruct_authorization_history(authorization, transitions)


def test_modified_content_breaks_next_link():
    authorization, transitions = make_history()
    transitions[0] = replace(
        transitions[0],
        reason="Conteudo adulterado",
    )

    with pytest.raises(ValueError):
        reconstruct_authorization_history(authorization, transitions)


def test_extra_transition_after_terminal_rejected():
    authorization, transitions = make_history()

    extra = make_record(
        authorization,
        4,
        "succeeded",
        "authorized",
        transition_record_hash(transitions[-1]),
    )

    with pytest.raises(ValueError):
        reconstruct_authorization_history(
            authorization,
            transitions + [extra],
        )


def test_invalid_state_transition_rejected():
    authorization, transitions = make_history()
    transitions[1] = replace(
        transitions[1],
        from_state="prepared",
    )

    with pytest.raises(ValueError):
        reconstruct_authorization_history(authorization, transitions)


def test_invalid_record_type_rejected():
    authorization = make_authorization()

    with pytest.raises(TypeError):
        reconstruct_authorization_history(authorization, [None])


def test_invalid_history_container_rejected():
    authorization = make_authorization()

    with pytest.raises(TypeError):
        reconstruct_authorization_history(authorization, "invalid")


def test_invalid_initial_authorization_rejected():
    authorization = replace(make_authorization(), state="authorized")

    with pytest.raises(ValueError):
        reconstruct_authorization_history(authorization, [])
