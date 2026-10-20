"""Leitura e validacao fisica de historicos AUTH-03.

Sem aprovacao administrativa nem execucao SQL.
"""

import os
import re
from uuid import UUID

from f066c_authorization_directory_read import (
    open_existing_subdirectory,
)
from f066c_authorization_history import (
    reconstruct_authorization_history,
)
from f066c_authorization_lock import acquire_authorization_lock
from f066c_authorization_secure_read import read_secure_file
from f066c_authorization_storage import deserialize_authorization
from f066c_authorization_transition_storage import (
    deserialize_transition_record,
)


TRANSITION_FILENAME = re.compile(
    r"^([0-9]{6})-(authorized|consumed|succeeded|failed|uncertain)\.json$"
)

MAX_TRANSITIONS = 100


def _read_initial_authorization(directory_fd: int, identifier: UUID):
    filename = f"{identifier}.json"
    payload = read_secure_file(directory_fd, filename)

    authorization = deserialize_authorization(
        payload.decode("utf-8")
    )

    if authorization.authorization_id != identifier:
        raise ValueError("UUID da autorizacao inicial divergente")

    return authorization


def _read_transitions(directory_fd: int, identifier: UUID):
    try:
        transitions_fd = open_existing_subdirectory(
            directory_fd,
            "transitions",
        )
    except FileNotFoundError:
        return []

    try:
        try:
            history_fd = open_existing_subdirectory(
                transitions_fd,
                str(identifier),
            )
        except FileNotFoundError:
            return []

        try:
            names = os.listdir(history_fd)

            if len(names) > MAX_TRANSITIONS:
                raise ValueError("Numero excessivo de transicoes")

            records = []
            expected_sequence = 1

            for filename in sorted(names):
                match = TRANSITION_FILENAME.fullmatch(filename)

                if match is None:
                    raise ValueError(
                        "Nome de ficheiro de transicao inesperado"
                    )

                sequence = int(match.group(1))
                state = match.group(2)

                if sequence != expected_sequence:
                    raise ValueError(
                        "Sequencia fisica de transicoes invalida"
                    )

                payload = read_secure_file(
                    history_fd,
                    filename,
                )

                record = deserialize_transition_record(payload)

                if record.sequence != sequence:
                    raise ValueError(
                        "Sequencia interna divergente"
                    )

                if record.to_state != state:
                    raise ValueError(
                        "Estado do ficheiro divergente"
                    )

                records.append(record)
                expected_sequence += 1

            return records

        finally:
            os.close(history_fd)

    finally:
        os.close(transitions_fd)


def _read_authorization_with_history_locked(
    directory_fd: int,
    authorization_id: UUID,
):
    """Devolve autorizacao e historico sob bloqueio externo.

    O chamador deve possuir o bloqueio exclusivo.
    Esta funcao nao adquire um segundo bloqueio.
    """

    if not isinstance(authorization_id, UUID):
        raise TypeError("UUID da autorizacao invalido")

    authorization = _read_initial_authorization(
        directory_fd,
        authorization_id,
    )

    transitions = _read_transitions(
        directory_fd,
        authorization_id,
    )

    history = reconstruct_authorization_history(
        authorization,
        transitions,
    )

    return authorization, history


def _read_authorization_history_locked(
    directory_fd: int,
    authorization_id: UUID,
):
    """Reconstroi o historico; exige bloqueio externo ja adquirido."""

    _, history = _read_authorization_with_history_locked(
        directory_fd,
        authorization_id,
    )

    return history


def read_authorization_history(
    directory_fd: int,
    authorization_id: UUID,
):
    """Le e valida o historico sob bloqueio exclusivo."""

    if not isinstance(authorization_id, UUID):
        raise TypeError("UUID da autorizacao invalido")

    with acquire_authorization_lock(directory_fd):
        return _read_authorization_history_locked(
            directory_fd,
            authorization_id,
        )
