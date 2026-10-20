"""Testes das regras logicas de transicao F0.66C."""

from dataclasses import FrozenInstanceError, replace
from uuid import uuid4

import pytest

from f066c_authorization_transition import (
    AuthorizationTransition,
    validate_transition,
)


@pytest.mark.parametrize(
    "previous,next_state",
    (
        ("prepared", "authorized"),
        ("authorized", "consumed"),
        ("consumed", "succeeded"),
        ("consumed", "failed"),
        ("consumed", "uncertain"),
    ),
)
def test_allowed_transitions(previous, next_state):
    transition = AuthorizationTransition(
        authorization_id=uuid4(),
        sequence=1,
        from_state=previous,
        to_state=next_state,
    )

    validate_transition(
        transition,
        current_state=previous,
        expected_sequence=1,
    )


@pytest.mark.parametrize(
    "previous,next_state",
    (
        ("prepared", "consumed"),
        ("prepared", "succeeded"),
        ("authorized", "succeeded"),
        ("consumed", "authorized"),
        ("succeeded", "authorized"),
        ("failed", "authorized"),
        ("uncertain", "authorized"),
        ("uncertain", "consumed"),
    ),
)
def test_forbidden_transitions(previous, next_state):
    transition = AuthorizationTransition(
        authorization_id=uuid4(),
        sequence=1,
        from_state=previous,
        to_state=next_state,
    )

    with pytest.raises(ValueError):
        validate_transition(
            transition,
            current_state=previous,
            expected_sequence=1,
        )


def test_transition_is_immutable():
    transition = AuthorizationTransition(
        authorization_id=uuid4(),
        sequence=1,
        from_state="prepared",
        to_state="authorized",
    )

    with pytest.raises(FrozenInstanceError):
        transition.to_state = "consumed"


@pytest.mark.parametrize("sequence", (0, -1, True, "1"))
def test_invalid_sequence_rejected(sequence):
    transition = AuthorizationTransition(
        authorization_id=uuid4(),
        sequence=sequence,
        from_state="prepared",
        to_state="authorized",
    )

    with pytest.raises(ValueError):
        validate_transition(
            transition,
            current_state="prepared",
            expected_sequence=1,
        )


def test_unexpected_sequence_rejected():
    transition = AuthorizationTransition(
        authorization_id=uuid4(),
        sequence=2,
        from_state="prepared",
        to_state="authorized",
    )

    with pytest.raises(ValueError):
        validate_transition(
            transition,
            current_state="prepared",
            expected_sequence=1,
        )


def test_divergent_previous_state_rejected():
    transition = AuthorizationTransition(
        authorization_id=uuid4(),
        sequence=1,
        from_state="authorized",
        to_state="consumed",
    )

    with pytest.raises(ValueError):
        validate_transition(
            transition,
            current_state="prepared",
            expected_sequence=1,
        )


def test_invalid_authorization_id_rejected():
    transition = AuthorizationTransition(
        authorization_id="invalid",
        sequence=1,
        from_state="prepared",
        to_state="authorized",
    )

    with pytest.raises(ValueError):
        validate_transition(
            transition,
            current_state="prepared",
            expected_sequence=1,
        )


def test_unknown_current_state_rejected():
    transition = AuthorizationTransition(
        authorization_id=uuid4(),
        sequence=1,
        from_state="unknown",
        to_state="authorized",
    )

    with pytest.raises(ValueError):
        validate_transition(
            transition,
            current_state="unknown",
            expected_sequence=1,
        )


def test_modified_transition_rejected():
    transition = AuthorizationTransition(
        authorization_id=uuid4(),
        sequence=1,
        from_state="prepared",
        to_state="authorized",
    )

    modified = replace(transition, to_state="consumed")

    with pytest.raises(ValueError):
        validate_transition(
            modified,
            current_state="prepared",
            expected_sequence=1,
        )



def test_divergent_authorization_id_rejected():
    transition = AuthorizationTransition(
        authorization_id=uuid4(),
        sequence=1,
        from_state="prepared",
        to_state="authorized",
    )

    with pytest.raises(ValueError):
        validate_transition(
            transition,
            current_state="prepared",
            expected_sequence=1,
            expected_authorization_id=uuid4(),
        )


@pytest.mark.parametrize("expected_sequence", (0, -1, True, "1"))
def test_invalid_expected_sequence_rejected(expected_sequence):
    transition = AuthorizationTransition(
        authorization_id=uuid4(),
        sequence=1,
        from_state="prepared",
        to_state="authorized",
    )

    with pytest.raises(ValueError):
        validate_transition(
            transition,
            current_state="prepared",
            expected_sequence=expected_sequence,
        )
