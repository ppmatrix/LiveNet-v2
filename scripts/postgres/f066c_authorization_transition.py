"""Regras logicas de transicao de autorizacoes F0.66C.

Sem persistencia, acesso externo ou execucao administrativa.
"""

from dataclasses import dataclass
from uuid import UUID

from f066c_authorization import ALLOWED_STATES


ALLOWED_TRANSITIONS = {
    "prepared": frozenset({"authorized"}),
    "authorized": frozenset({"consumed"}),
    "consumed": frozenset({"succeeded", "failed", "uncertain"}),
    "succeeded": frozenset(),
    "failed": frozenset(),
    "uncertain": frozenset(),
}


@dataclass(frozen=True)
class AuthorizationTransition:
    authorization_id: UUID
    sequence: int
    from_state: str
    to_state: str


def validate_transition(
    transition: AuthorizationTransition,
    *,
    current_state: str,
    expected_sequence: int,
    expected_authorization_id: UUID | None = None,
) -> None:
    """Valida uma transicao sem alterar o estado existente."""

    if not isinstance(transition, AuthorizationTransition):
        raise TypeError("Transicao de autorizacao invalida")

    if not isinstance(transition.authorization_id, UUID):
        raise ValueError("Identificador de autorizacao invalido")

    if expected_authorization_id is not None:
        if not isinstance(expected_authorization_id, UUID):
            raise ValueError("UUID esperado invalido")
        if transition.authorization_id != expected_authorization_id:
            raise ValueError("Autorizacao da transicao divergente")

    if type(transition.sequence) is not int or transition.sequence < 1:
        raise ValueError("Sequencia de transicao invalida")

    if (
        type(expected_sequence) is not int
        or expected_sequence < 1
        or transition.sequence != expected_sequence
    ):
        raise ValueError("Sequencia de transicao inesperada")

    if current_state not in ALLOWED_STATES:
        raise ValueError("Estado atual desconhecido")

    if transition.from_state != current_state:
        raise ValueError("Estado anterior divergente")

    if transition.to_state not in ALLOWED_TRANSITIONS[current_state]:
        raise ValueError("Transicao de estado nao permitida")
