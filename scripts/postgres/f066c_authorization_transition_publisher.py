"""Coordenacao da publicacao local de transicoes AUTH-03.

Nao aprova autorizacoes, nao consulta a ancora independente
e nao executa operacoes administrativas ou SQL.
"""

import os
import sys
from uuid import UUID

from f066c_authorization_file_store import AuthorizationPublicationUncertain
from f066c_authorization_history_reader import (
    _read_authorization_with_history_locked,
)
from f066c_authorization_lock import acquire_authorization_lock
from f066c_authorization_transition_file_store import (
    publish_transition_payload,
    validate_transition_for_publication,
)
from f066c_authorization_transition_record import (
    AuthorizationTransitionRecord,
)
from f066c_secure_directory import create_secure_subdirectories_at


def publish_authorization_transition(
    directory_fd: int,
    authorization_id: UUID,
    record: AuthorizationTransitionRecord,
) -> str:
    """Publica uma transicao local sob bloqueio exclusivo.

    A publicacao local nao constitui autorizacao administrativa.
    O estado deve ser confirmado por uma ancora independente
    antes de qualquer execucao administrativa.
    """

    if not isinstance(authorization_id, UUID):
        raise TypeError("UUID da autorizacao invalido")

    if not isinstance(record, AuthorizationTransitionRecord):
        raise TypeError("Registo de transicao invalido")

    if record.authorization_id != authorization_id:
        raise ValueError("UUID da transicao divergente")

    publication_completed = False

    try:
        with acquire_authorization_lock(directory_fd):
            authorization, history = (
                _read_authorization_with_history_locked(
                    directory_fd,
                    authorization_id,
                )
            )

            payload = validate_transition_for_publication(
                authorization,
                history,
                record,
            )

            history_fd = create_secure_subdirectories_at(
                directory_fd,
                ("transitions", str(authorization_id)),
            )

            try:
                filename = (
                    f"{record.sequence:06d}-{record.to_state}.json"
                )

                result = publish_transition_payload(
                    history_fd,
                    filename,
                    payload,
                )
                publication_completed = True
                return result
            finally:
                primary_error = sys.exception()

                try:
                    os.close(history_fd)
                except OSError as close_error:
                    if primary_error is not None:
                        primary_error.add_note(
                            "Falha adicional ao fechar o diretorio "
                            "de historico: "
                            f"{type(close_error).__name__}: "
                            f"{close_error}"
                        )
                    else:
                        raise AuthorizationPublicationUncertain(
                            "Falha ao fechar o diretorio de historico "
                            "apos a publicacao; resultado incerto"
                        ) from close_error

    except Exception as exc:
        if isinstance(exc, AuthorizationPublicationUncertain):
            raise

        if publication_completed:
            raise AuthorizationPublicationUncertain(
                "Falha apos publicacao local concluida; "
                "resultado operacional incerto"
            ) from exc

        raise
