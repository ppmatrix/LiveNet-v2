"""Integridade dos elos da cadeia de autorizacoes AUTH-03.

Sem acesso ao disco, aprovacao ou execucao administrativa.
"""

from hashlib import sha256

from f066c_authorization import AdministrativeAuthorization
from f066c_authorization_storage import (
    serialize_authorization,
    validate_record,
)
from f066c_authorization_transition_record import (
    AuthorizationTransitionRecord,
)
from f066c_authorization_transition_storage import (
    serialize_transition_record,
)


def initial_authorization_hash(
    authorization: AdministrativeAuthorization,
) -> str:
    """Calcula o hash da representacao original AUTH-02B."""

    if not isinstance(authorization, AdministrativeAuthorization):
        raise TypeError("Autorizacao inicial invalida")

    validate_record(authorization)

    if authorization.state != "prepared":
        raise ValueError("Autorizacao inicial nao esta preparada")

    payload = serialize_authorization(authorization).encode("utf-8")
    return sha256(payload).hexdigest()


def transition_record_hash(
    record: AuthorizationTransitionRecord,
) -> str:
    """Calcula o hash dos bytes canonicos da transicao."""

    return sha256(serialize_transition_record(record)).hexdigest()


def validate_chain_link(
    record: AuthorizationTransitionRecord,
    *,
    expected_previous_hash: str,
) -> None:
    """Confirma que a transicao referencia o hash esperado."""

    serialize_transition_record(record)

    if (
        not isinstance(expected_previous_hash, str)
        or len(expected_previous_hash) != 64
        or any(
            character not in "0123456789abcdef"
            for character in expected_previous_hash
        )
    ):
        raise ValueError("Hash anterior esperado invalido")

    if record.previous_hash != expected_previous_hash:
        raise ValueError("Encadeamento SHA-256 divergente")
