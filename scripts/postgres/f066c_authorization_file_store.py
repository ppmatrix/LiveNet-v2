"""Armazenamento atomico de autorizacoes F0.66C.

Sem acesso ao PostgreSQL ou execucao administrativa.
"""

import fcntl
import os
import stat
from uuid import uuid4

from f066c_authorization import AdministrativeAuthorization
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

    fcntl.flock(directory_fd, fcntl.LOCK_EX)

    temporary_created = False
    published = False
    publication_error = None
    cleanup_error = None
    unlock_error = None

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
                raise PermissionError("Ficheiro temporario inseguro")

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
        try:
            if temporary_created:
                try:
                    os.unlink(temporary, dir_fd=directory_fd)
                    os.fsync(directory_fd)
                except OSError as exc:
                    cleanup_error = exc
        finally:
            try:
                fcntl.flock(directory_fd, fcntl.LOCK_UN)
            except OSError as exc:
                unlock_error = exc

    if published and (
        publication_error or cleanup_error or unlock_error
    ):
        raise AuthorizationPublicationUncertain(filename) from (
            publication_error or cleanup_error or unlock_error
        )

    if publication_error:
        raise publication_error

    if cleanup_error:
        raise cleanup_error

    if unlock_error:
        raise unlock_error

    return filename
