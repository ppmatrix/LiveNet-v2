"""Validacao para publicacao de transicoes AUTH-03.

Sem escrita fisica, PostgreSQL ou execucao administrativa.
"""

from uuid import UUID

from f066c_authorization import AdministrativeAuthorization
from f066c_authorization_history import AuthorizationHistoryState
from f066c_authorization_transition import (
    AuthorizationTransition,
    validate_transition,
)
from f066c_authorization_transition_record import (
    AuthorizationTransitionRecord,
)
from f066c_authorization_transition_storage import (
    serialize_transition_record,
)


def validate_transition_for_publication(
    authorization: AdministrativeAuthorization,
    history: AuthorizationHistoryState,
    record: AuthorizationTransitionRecord,
) -> bytes:
    """Valida a proxima transicao e devolve os bytes canonicos."""

    if not isinstance(authorization, AdministrativeAuthorization):
        raise TypeError("Autorizacao invalida")

    if not isinstance(history, AuthorizationHistoryState):
        raise TypeError("Historico invalido")

    if not isinstance(record, AuthorizationTransitionRecord):
        raise TypeError("Registo de transicao invalido")

    payload = serialize_transition_record(record)

    if authorization.state != "prepared":
        raise ValueError("Autorizacao inicial nao esta prepared")

    if not isinstance(authorization.authorization_id, UUID):
        raise TypeError("UUID da autorizacao invalido")

    if history.authorization_id != str(authorization.authorization_id):
        raise ValueError("UUID do historico divergente")

    if record.operation != authorization.operation:
        raise ValueError("Operacao divergente")

    if record.sql_sha256 != authorization.sql_sha256:
        raise ValueError("SHA-256 SQL divergente")

    if record.previous_hash != history.last_hash:
        raise ValueError("Hash anterior divergente")

    transition = AuthorizationTransition(
        authorization_id=record.authorization_id,
        sequence=record.sequence,
        from_state=record.from_state,
        to_state=record.to_state,
    )

    validate_transition(
        transition,
        current_state=history.state,
        expected_sequence=history.next_sequence,
        expected_authorization_id=authorization.authorization_id,
    )

    return payload


def publish_transition_payload(
    directory_fd: int,
    filename: str,
    payload: bytes,
) -> str:
    """Publica bytes canonicos sob bloqueio externo ja adquirido.

    Nao adquire bloqueios nem executa SQL.
    """
    import os
    import re
    import stat
    import sys
    from uuid import uuid4

    from f066c_authorization_file_store import (
        AuthorizationPublicationUncertain,
    )

    if not isinstance(filename, str) or not re.fullmatch(
        r"[0-9]{6}-(authorized|consumed|succeeded|failed|uncertain)\.json",
        filename,
    ):
        raise ValueError("Nome de transicao invalido")

    if not isinstance(payload, bytes) or not payload:
        raise ValueError("Payload invalido")

    info = os.fstat(directory_fd)

    if not stat.S_ISDIR(info.st_mode):
        raise ValueError("Descritor nao corresponde a diretorio")

    if info.st_uid != os.getuid():
        raise PermissionError("Proprietario inesperado")

    if stat.S_IMODE(info.st_mode) != 0o700:
        raise PermissionError("Permissoes inseguras")

    temporary = f".tmp-{uuid4().hex}"
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | os.O_NOFOLLOW
        | os.O_CLOEXEC
    )

    created = False
    published = False
    link_attempted = False
    errors = []

    try:
        file_fd = os.open(
            temporary,
            flags,
            0o600,
            dir_fd=directory_fd,
        )
        created = True

        try:
            temporary_info = os.fstat(file_fd)

            if (
                not stat.S_ISREG(temporary_info.st_mode)
                or temporary_info.st_uid != os.getuid()
                or stat.S_IMODE(temporary_info.st_mode) != 0o600
                or temporary_info.st_nlink != 1
            ):
                raise PermissionError(
                    "Ficheiro temporario inseguro"
                )

            offset = 0
            while offset < len(payload):
                written = os.write(file_fd, payload[offset:])
                if written <= 0:
                    raise OSError("Escrita incompleta")
                offset += written

            os.fsync(file_fd)
        finally:
            active_error = sys.exception()

            try:
                os.close(file_fd)
            except BaseException as close_error:
                if active_error is None:
                    raise

                active_error.add_note(
                    "Falha adicional ao fechar ficheiro temporario: "
                    f"{type(close_error).__name__}: {close_error}"
                )

        link_attempted = True

        os.link(
            temporary,
            filename,
            src_dir_fd=directory_fd,
            dst_dir_fd=directory_fd,
            follow_symlinks=False,
        )
        published = True

        os.fsync(directory_fd)

    except OSError as exc:
        errors.append(exc)

    finally:
        if created:
            try:
                os.unlink(temporary, dir_fd=directory_fd)
                os.fsync(directory_fd)
            except OSError as exc:
                errors.append(exc)

    if errors:
        primary_error = errors[0]

        for additional_error in errors[1:]:
            primary_error.add_note(
                "Falha adicional: "
                f"{type(additional_error).__name__}: "
                f"{additional_error}"
            )

        if published or (
            link_attempted
            and not isinstance(primary_error, FileExistsError)
        ):
            raise AuthorizationPublicationUncertain(
                filename
            ) from primary_error

        raise primary_error

    return filename
