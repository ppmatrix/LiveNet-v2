"""Bloqueio dedicado para autorizacoes administrativas F0.66C.

Nao executa operacoes PostgreSQL nem comandos administrativos.
O ficheiro de bloqueio e permanente e nao deve ser eliminado.
"""

from contextlib import contextmanager
import fcntl
import os
import stat
import sys


LOCK_FILENAME = ".authorization.lock"


def _validate_directory(directory_fd: int) -> None:
    info = os.fstat(directory_fd)

    if not stat.S_ISDIR(info.st_mode):
        raise ValueError("Descritor nao corresponde a diretorio")

    if info.st_uid != os.getuid():
        raise PermissionError("Proprietario inesperado do diretorio")

    if stat.S_IMODE(info.st_mode) != 0o700:
        raise PermissionError("Permissoes inseguras do diretorio")


def _validate_lock_file(info: os.stat_result) -> None:
    if not stat.S_ISREG(info.st_mode):
        raise ValueError("Bloqueio nao corresponde a ficheiro regular")

    if info.st_uid != os.getuid():
        raise PermissionError("Proprietario inesperado do bloqueio")

    if stat.S_IMODE(info.st_mode) != 0o600:
        raise PermissionError("Permissoes inseguras do bloqueio")

    if info.st_nlink != 1:
        raise PermissionError("Numero de links inseguro")


@contextmanager
def acquire_authorization_lock(directory_fd: int):
    """Obtem bloqueio exclusivo com abertura independente por operacao."""

    _validate_directory(directory_fd)

    flags = os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC

    try:
        lock_fd = os.open(
            LOCK_FILENAME,
            flags | os.O_CREAT | os.O_EXCL,
            0o600,
            dir_fd=directory_fd,
        )
    except FileExistsError:
        lock_fd = os.open(
            LOCK_FILENAME,
            flags,
            dir_fd=directory_fd,
        )
    else:
        try:
            os.fsync(lock_fd)
            os.fsync(directory_fd)
        except BaseException:
            os.close(lock_fd)
            raise

    try:
        _validate_lock_file(os.fstat(lock_fd))

        fcntl.flock(lock_fd, fcntl.LOCK_EX)

        try:
            descriptor_info = os.fstat(lock_fd)

            _validate_lock_file(descriptor_info)

            path_info = os.stat(
                LOCK_FILENAME,
                dir_fd=directory_fd,
                follow_symlinks=False,
            )

            if (
                descriptor_info.st_dev,
                descriptor_info.st_ino,
            ) != (
                path_info.st_dev,
                path_info.st_ino,
            ):
                raise PermissionError(
                    "Identidade do ficheiro de bloqueio alterada"
                )

            yield

        finally:
            active_error = sys.exception()
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
            except BaseException as unlock_error:
                if active_error is None:
                    raise
                active_error.add_note(
                    "Falha adicional ao libertar bloqueio: "
                    f"{type(unlock_error).__name__}: {unlock_error}"
                )

    finally:
        active_error = sys.exception()
        try:
            os.close(lock_fd)
        except BaseException as close_error:
            if active_error is None:
                raise
            active_error.add_note(
                "Falha adicional ao fechar descritor de bloqueio: "
                f"{type(close_error).__name__}: {close_error}"
            )
