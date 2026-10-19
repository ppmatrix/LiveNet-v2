"""Armazenamento atomico de autorizacoes F0.66C.

Sem acesso ao PostgreSQL ou execucao administrativa.
"""

import fcntl
import os
import stat
from uuid import uuid4

from f066c_authorization import AdministrativeAuthorization
from f066c_authorization_storage import serialize_authorization


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

        return filename

    finally:
        try:
            if temporary_created:
                os.unlink(temporary, dir_fd=directory_fd)
                os.fsync(directory_fd)
        finally:
            fcntl.flock(directory_fd, fcntl.LOCK_UN)
