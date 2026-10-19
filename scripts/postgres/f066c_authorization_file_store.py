"""Armazenamento atomico de autorizacoes F0.66C.

Sem acesso ao PostgreSQL ou execucao administrativa.
"""

import os
import stat
from uuid import uuid4

from f066c_authorization import AdministrativeAuthorization
from f066c_authorization_lock import acquire_authorization_lock
from f066c_authorization_storage import serialize_authorization



class AuthorizationPublicationUncertain(OSError):
    """Publicacao efetuada, mas durabilidade nao confirmada."""

    def __init__(self, filename: str):
        self.filename = filename
        super().__init__(
            f"Durabilidade da autorizacao nao confirmada: {filename}"
        )


def create_authorization_file(
    directory_fd: int,
    authorization: AdministrativeAuthorization,
) -> str:
    """Publica uma autorizacao prepared sem substituir ficheiros."""

    if not isinstance(authorization, AdministrativeAuthorization):
        raise TypeError("Autorizacao invalida")

    if authorization.state != "prepared":
        raise ValueError("Apenas autorizacoes prepared podem ser criadas")

    directory_info = os.fstat(directory_fd)

    if not stat.S_ISDIR(directory_info.st_mode):
        raise ValueError("Descritor nao corresponde a diretorio")

    if directory_info.st_uid != os.getuid():
        raise PermissionError("Proprietario inesperado")

    if stat.S_IMODE(directory_info.st_mode) != 0o700:
        raise PermissionError("Permissoes inseguras")

    payload = serialize_authorization(authorization).encode("utf-8")

    filename = f"{authorization.authorization_id}.json"
    temporary = f".tmp-{uuid4().hex}"

    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | os.O_NOFOLLOW
        | os.O_CLOEXEC
    )

    temporary_created = False
    published = False
    publication_error = None
    cleanup_error = None
    lock_error = None

    try:
        with acquire_authorization_lock(directory_fd):
            try:
                file_fd = os.open(
                    temporary,
                    flags,
                    0o600,
                    dir_fd=directory_fd,
                )
                temporary_created = True

                try:
                    info = os.fstat(file_fd)

                    if (
                        info.st_uid != os.getuid()
                        or stat.S_IMODE(info.st_mode) != 0o600
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
                    os.close(file_fd)

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
                publication_error = exc

            finally:
                if temporary_created:
                    try:
                        os.unlink(temporary, dir_fd=directory_fd)
                        os.fsync(directory_fd)
                    except OSError as exc:
                        cleanup_error = exc

    except OSError as exc:
        lock_error = exc

    if published and (
        publication_error or cleanup_error or lock_error
    ):
        primary_error = (
            publication_error or cleanup_error or lock_error
        )

        for label, additional_error in (
            ("publicacao", publication_error),
            ("limpeza", cleanup_error),
            ("bloqueio", lock_error),
        ):
            if (
                additional_error is not None
                and additional_error is not primary_error
            ):
                primary_error.add_note(
                    f"Falha adicional de {label}: "
                    f"{type(additional_error).__name__}: "
                    f"{additional_error}"
                )

        raise AuthorizationPublicationUncertain(
            filename
        ) from primary_error

    if publication_error:
        raise publication_error

    if cleanup_error:
        raise cleanup_error

    if lock_error:
        raise lock_error

    return filename
