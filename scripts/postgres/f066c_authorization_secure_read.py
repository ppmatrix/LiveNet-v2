"""Leitura segura de ficheiros de autorizacao AUTH-03.

Sem criacao de ficheiros, persistencia ou execucao administrativa.
"""

import os
import stat


def _validate_regular_file(info: os.stat_result) -> None:
    if not stat.S_ISREG(info.st_mode):
        raise ValueError("Nao corresponde a ficheiro regular")

    if info.st_uid != os.getuid():
        raise PermissionError("Proprietario inesperado")

    if stat.S_IMODE(info.st_mode) != 0o600:
        raise PermissionError("Permissoes inseguras")

    if info.st_nlink != 1:
        raise PermissionError("Numero de links inseguro")


def read_secure_file(
    directory_fd: int,
    filename: str,
    *,
    max_bytes: int = 8192,
) -> bytes:
    """Le um ficheiro privado sem seguir ligacoes simbolicas."""

    directory_info = os.fstat(directory_fd)

    if not stat.S_ISDIR(directory_info.st_mode):
        raise ValueError("Descritor nao corresponde a diretorio")

    if directory_info.st_uid != os.getuid():
        raise PermissionError("Proprietario do diretorio inesperado")

    if stat.S_IMODE(directory_info.st_mode) != 0o700:
        raise PermissionError("Permissoes inseguras do diretorio")

    if (
        not isinstance(filename, str)
        or not filename
        or filename in (".", "..")
        or "/" in filename
        or "\x00" in filename
    ):
        raise ValueError("Nome de ficheiro invalido")

    if type(max_bytes) is not int or max_bytes < 1:
        raise ValueError("Limite de leitura invalido")

    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    flags |= getattr(os, "O_CLOEXEC", 0)

    fd = os.open(filename, flags, dir_fd=directory_fd)

    try:
        before = os.fstat(fd)
        _validate_regular_file(before)

        path_info = os.stat(
            filename,
            dir_fd=directory_fd,
            follow_symlinks=False,
        )

        if (
            before.st_dev,
            before.st_ino,
        ) != (
            path_info.st_dev,
            path_info.st_ino,
        ):
            raise PermissionError("Identidade do ficheiro alterada")

        if before.st_size > max_bytes:
            raise ValueError("Ficheiro excede limite de leitura")

        payload = bytearray()

        while len(payload) <= max_bytes:
            chunk = os.read(
                fd,
                min(4096, max_bytes + 1 - len(payload)),
            )

            if not chunk:
                break

            payload.extend(chunk)

        if len(payload) > max_bytes:
            raise ValueError("Ficheiro excede limite de leitura")

        after = os.fstat(fd)

        if (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ):
            raise PermissionError("Ficheiro alterado durante leitura")

        if len(payload) != before.st_size:
            raise ValueError("Leitura incompleta")

        return bytes(payload)

    finally:
        os.close(fd)
