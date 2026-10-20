"""Reconstrucao logica do historico de autorizacoes AUTH-03.

Nao consulta ficheiros, nao aprova operacoes e nao executa SQL.
"""

from dataclasses import dataclass
from typing import Sequence

from f066c_authorization import AdministrativeAuthorization
from f066c_authorization_chain import (
    initial_authorization_hash,
    transition_record_hash,
    validate_chain_link,
)
from f066c_authorization_transition import (
    AuthorizationTransition,
    validate_transition,
)
from f066c_authorization_transition_record import (
    AuthorizationTransitionRecord,
)


@dataclass(frozen=True)
class AuthorizationHistoryState:
    authorization_id: str
    state: str
    next_sequence: int
    last_hash: str
    transition_count: int


def reconstruct_authorization_history(
    authorization: AdministrativeAuthorization,
    transitions: Sequence[AuthorizationTransitionRecord],
) -> AuthorizationHistoryState:
    """Valida uma cadeia apresentada e reconstitui o ultimo estado."""

    previous_hash = initial_authorization_hash(authorization)

    if not isinstance(transitions, (tuple, list)):
        raise TypeError("Historico deve ser uma lista ou tuplo")

    current_state = "prepared"
    expected_sequence = 1

    for record in transitions:
        if not isinstance(record, AuthorizationTransitionRecord):
            raise TypeError("Registo de transicao invalido")

        if record.authorization_id != authorization.authorization_id:
            raise ValueError("UUID da transicao divergente")

        if record.operation != authorization.operation:
            raise ValueError("Operacao da transicao divergente")

        if record.sql_sha256 != authorization.sql_sha256:
            raise ValueError("SHA-256 do SQL divergente")

        transition = AuthorizationTransition(
            authorization_id=record.authorization_id,
            sequence=record.sequence,
            from_state=record.from_state,
            to_state=record.to_state,
        )

        validate_transition(
            transition,
            current_state=current_state,
            expected_sequence=expected_sequence,
            expected_authorization_id=authorization.authorization_id,
        )

        validate_chain_link(
            record,
            expected_previous_hash=previous_hash,
        )

        previous_hash = transition_record_hash(record)
        current_state = record.to_state
        expected_sequence += 1

    return AuthorizationHistoryState(
        authorization_id=str(authorization.authorization_id),
        state=current_state,
        next_sequence=expected_sequence,
        last_hash=previous_hash,
        transition_count=len(transitions),
    )
