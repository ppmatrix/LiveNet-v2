"""Validacao e criacao de diretorios seguros F0.66C."""

import os
import stat
from pathlib import Path


def validate_secure_directory(path: Path) -> None:
    """Exige diretorio real, privado e pertencente ao utilizador."""

    path = Path(path)

    info = path.lstat()

    if not stat.S_ISDIR(info.st_mode):
        raise ValueError("Caminho nao e um diretorio real")

    if info.st_uid != os.getuid():
        raise PermissionError("Proprietario do diretorio inesperado")

    if stat.S_IMODE(info.st_mode) != 0o700:
        raise PermissionError("Permissoes do diretorio inseguras")


def ensure_secure_directory(path: Path) -> None:
    """Cria ou valida um diretorio privado.

    Os componentes ancestrais sao inspecionados para
    rejeitar ligacoes simbolicas.
    """

    path = Path(path).absolute()

    for ancestor in (path, *path.parents):
        try:
            info = ancestor.lstat()
        except FileNotFoundError:
            continue

        if stat.S_ISLNK(info.st_mode):
            raise ValueError("Ligacao simbolica no caminho")

        if not stat.S_ISDIR(info.st_mode):
            raise ValueError("Componente do caminho nao e diretorio")

    if path.exists():
        validate_secure_directory(path)
        return

    parent = path.parent

    if not parent.exists():
        ensure_secure_directory(parent)

    try:
        path.mkdir(mode=0o700)
    except FileExistsError:
        pass

    validate_secure_directory(path)



def open_secure_directory(path: Path) -> int:
    """Abre um diretorio privado sem seguir symlinks.

    O chamador e responsavel por fechar o descritor.
    Todos os componentes sao percorridos relativamente
    ao descritor do diretorio anterior.
    """

    path = Path(path)

    if not path.is_absolute():
        raise ValueError("Caminho deve ser absoluto")

    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    flags |= getattr(os, "O_CLOEXEC", 0)

    fd = os.open("/", flags)

    try:
        for component in path.parts[1:]:
            if component in ("", ".", ".."):
                raise ValueError("Componente de caminho invalido")

            next_fd = os.open(
                component,
                flags,
                dir_fd=fd,
            )

            os.close(fd)
            fd = next_fd

        info = os.fstat(fd)

        if info.st_uid != os.getuid():
            raise PermissionError("Proprietario inesperado")

        if stat.S_IMODE(info.st_mode) != 0o700:
            raise PermissionError("Permissoes inseguras")

        return fd

    except BaseException:
        os.close(fd)
        raise



def create_secure_subdirectories(
    trusted_parent: Path,
    components: tuple[str, ...],
) -> int:
    """Cria subdiretorios privados relativos a um ancestral validado.

    O ancestral deve existir, pertencer ao utilizador e nao
    permitir escrita a outros utilizadores. O descritor final
    devolvido deve ser fechado pelo chamador.
    """

    trusted_parent = Path(trusted_parent)

    if not trusted_parent.is_absolute():
        raise ValueError("Ancestral deve ser absoluto")

    if not components:
        raise ValueError("Componentes em falta")

    for component in components:
        if (
            not isinstance(component, str)
            or component in ("", ".", "..")
            or "/" in component
            or chr(0) in component
        ):
            raise ValueError("Componente invalido")

    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    flags |= getattr(os, "O_CLOEXEC", 0)

    fd = os.open("/", flags)

    try:
        for component in trusted_parent.parts[1:]:
            next_fd = os.open(component, flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd

        parent_info = os.fstat(fd)

        if parent_info.st_uid != os.getuid():
            raise PermissionError("Ancestral com proprietario inesperado")

        if parent_info.st_mode & 0o022:
            raise PermissionError(
                "Ancestral permite escrita ao grupo ou a outros"
            )

        for component in components:
            try:
                os.mkdir(component, mode=0o700, dir_fd=fd)
            except FileExistsError:
                pass

            next_fd = os.open(component, flags, dir_fd=fd)
            info = os.fstat(next_fd)

            if (
                info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) != 0o700
            ):
                os.close(next_fd)
                raise PermissionError("Subdiretorio inseguro")

            os.close(fd)
            fd = next_fd

        return fd

    except BaseException:
        os.close(fd)
        raise



def open_authorization_directory(
    private_base: Path,
) -> int:
    """Abre a hierarquia privada de autorizacoes F0.66C.

    O descritor devolvido deve ser fechado pelo chamador.

    A funcao aceita uma base explicita para permitir
    testes isolados em diretorios temporarios.
    """

    private_base = Path(private_base)

    fd = open_secure_directory(private_base)

    try:
        return create_secure_subdirectories_at(
            fd,
            ("livenet-v2", "f066c-authorizations"),
        )
    finally:
        os.close(fd)



def create_secure_subdirectories_at(
    parent_fd: int,
    components: tuple[str, ...],
) -> int:
    """Cria diretorios privados relativamente a um descritor.

    Nao fecha o descritor fornecido pelo chamador.
    O descritor devolvido deve ser fechado pelo chamador.
    """

    if not components:
        raise ValueError("Componentes em falta")

    for component in components:
        if (
            not isinstance(component, str)
            or component in ("", ".", "..")
            or "/" in component
            or chr(0) in component
        ):
            raise ValueError("Componente invalido")

    parent_info = os.fstat(parent_fd)

    if not stat.S_ISDIR(parent_info.st_mode):
        raise ValueError("Descritor nao corresponde a diretorio")

    if parent_info.st_uid != os.getuid():
        raise PermissionError("Proprietario inesperado")

    if stat.S_IMODE(parent_info.st_mode) != 0o700:
        raise PermissionError("Diretorio ancestral inseguro")

    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    flags |= getattr(os, "O_CLOEXEC", 0)

    fd = os.dup(parent_fd)

    try:
        for component in components:
            created = False

            try:
                os.mkdir(component, mode=0o700, dir_fd=fd)
                created = True
            except FileExistsError:
                pass

            next_fd = os.open(
                component,
                flags,
                dir_fd=fd,
            )

            info = os.fstat(next_fd)

            if (
                not stat.S_ISDIR(info.st_mode)
                or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) != 0o700
            ):
                os.close(next_fd)
                raise PermissionError("Subdiretorio inseguro")

            if created:
                try:
                    os.fsync(fd)
                except BaseException:
                    os.close(next_fd)
                    raise

            os.close(fd)
            fd = next_fd

        return fd

    except BaseException:
        os.close(fd)
        raise
