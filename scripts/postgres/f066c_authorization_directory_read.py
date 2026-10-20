"""Abertura segura e exclusivamente de leitura de diretorios AUTH-03."""

import os
import stat


def open_existing_subdirectory(
    parent_fd: int,
    component: str,
) -> int:
    """Abre um subdiretorio existente, sem o criar.

    O chamador deve fechar o descritor devolvido.
    """

    if (
        not isinstance(component, str)
        or component in ("", ".", "..")
        or "/" in component
        or "\x00" in component
    ):
        raise ValueError("Componente de diretorio invalido")

    parent_info = os.fstat(parent_fd)

    if not stat.S_ISDIR(parent_info.st_mode):
        raise ValueError("Descritor ancestral nao e diretorio")

    if parent_info.st_uid != os.getuid():
        raise PermissionError("Proprietario ancestral inesperado")

    if stat.S_IMODE(parent_info.st_mode) != 0o700:
        raise PermissionError("Permissoes ancestrais inseguras")

    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    flags |= getattr(os, "O_CLOEXEC", 0)

    fd = os.open(component, flags, dir_fd=parent_fd)

    try:
        info = os.fstat(fd)

        if not stat.S_ISDIR(info.st_mode):
            raise ValueError("Componente nao e diretorio")

        if info.st_uid != os.getuid():
            raise PermissionError("Proprietario inesperado")

        if stat.S_IMODE(info.st_mode) != 0o700:
            raise PermissionError("Permissoes inseguras")

        path_info = os.stat(
            component,
            dir_fd=parent_fd,
            follow_symlinks=False,
        )

        if (
            info.st_dev,
            info.st_ino,
        ) != (
            path_info.st_dev,
            path_info.st_ino,
        ):
            raise PermissionError("Identidade do diretorio alterada")

        return fd

    except BaseException:
        os.close(fd)
        raise
