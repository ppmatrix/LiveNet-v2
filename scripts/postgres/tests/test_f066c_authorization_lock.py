"""Testes de seguranca do bloqueio dedicado AUTH-02B."""

import fcntl
import os
import stat
import subprocess
import sys
import threading
import time

import pytest

from f066c_authorization_lock import acquire_authorization_lock


@pytest.fixture
def directory_fd(tmp_path):
    directory = tmp_path / "authorizations"
    directory.mkdir(mode=0o700)

    fd = os.open(
        directory,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
    )

    try:
        yield fd, directory
    finally:
        os.close(fd)


def test_lock_creation_and_permissions(directory_fd):
    fd, directory = directory_fd

    with acquire_authorization_lock(fd):
        path = directory / ".authorization.lock"
        info = path.stat(follow_symlinks=False)

        assert stat.S_ISREG(info.st_mode)
        assert stat.S_IMODE(info.st_mode) == 0o600
        assert info.st_uid == os.getuid()
        assert info.st_nlink == 1


def test_lock_persists_after_release(directory_fd):
    fd, directory = directory_fd

    with acquire_authorization_lock(fd):
        first = (directory / ".authorization.lock").stat()

    with acquire_authorization_lock(fd):
        second = (directory / ".authorization.lock").stat()

    assert (first.st_dev, first.st_ino) == (
        second.st_dev,
        second.st_ino,
    )


def test_independent_open_cannot_acquire_lock(directory_fd):
    fd, directory = directory_fd

    with acquire_authorization_lock(fd):
        second_fd = os.open(
            directory / ".authorization.lock",
            os.O_RDWR | os.O_NOFOLLOW,
        )

        try:
            with pytest.raises(BlockingIOError):
                fcntl.flock(
                    second_fd,
                    fcntl.LOCK_EX | fcntl.LOCK_NB,
                )
        finally:
            os.close(second_fd)


def test_symlink_lock_rejected(directory_fd, tmp_path):
    fd, directory = directory_fd
    target = tmp_path / "target"
    target.write_text("do not modify")

    (directory / ".authorization.lock").symlink_to(target)

    with pytest.raises((OSError, PermissionError, ValueError)):
        with acquire_authorization_lock(fd):
            pytest.fail("Bloqueio simbolico aceite")

    assert target.read_text() == "do not modify"


def test_insecure_permissions_rejected(directory_fd):
    fd, directory = directory_fd
    path = directory / ".authorization.lock"
    path.touch(mode=0o644)
    path.chmod(0o644)

    with pytest.raises(PermissionError):
        with acquire_authorization_lock(fd):
            pytest.fail("Permissoes inseguras aceites")


def test_hardlinked_lock_rejected(directory_fd):
    fd, directory = directory_fd
    path = directory / ".authorization.lock"
    path.touch(mode=0o600)

    os.link(path, directory / "second-link")

    with pytest.raises((PermissionError, ValueError)):
        with acquire_authorization_lock(fd):
            pytest.fail("Ficheiro com multiplos links aceite")



def test_concurrent_independent_opens(directory_fd):
    fd, directory = directory_fd
    entered = threading.Event()
    release = threading.Event()
    second_entered = threading.Event()
    errors = []

    def first_worker():
        try:
            with acquire_authorization_lock(fd):
                entered.set()
                if not release.wait(timeout=5):
                    raise TimeoutError("Primeira operacao bloqueada")
        except BaseException as exc:
            errors.append(exc)

    def second_worker():
        try:
            if not entered.wait(timeout=5):
                raise TimeoutError("Primeira operacao nao iniciou")

            with acquire_authorization_lock(fd):
                second_entered.set()
        except BaseException as exc:
            errors.append(exc)

    first = threading.Thread(target=first_worker)
    second = threading.Thread(target=second_worker)

    first.start()
    second.start()

    try:
        assert entered.wait(timeout=5)
        assert not second_entered.wait(timeout=0.2)
    finally:
        release.set()
        first.join(timeout=5)
        second.join(timeout=5)

    assert not first.is_alive()
    assert not second.is_alive()
    assert not errors
    assert second_entered.is_set()


def test_shared_directory_descriptor_exclusion(directory_fd):
    fd, directory = directory_fd
    duplicate = os.dup(fd)

    try:
        with acquire_authorization_lock(fd):
            result = []

            def worker():
                with acquire_authorization_lock(duplicate):
                    result.append("entered")

            thread = threading.Thread(target=worker)
            thread.start()

            try:
                time.sleep(0.2)
                assert result == []
            finally:
                # O desbloqueio ocorre ao sair do contexto.
                pass

        thread.join(timeout=5)

        assert not thread.is_alive()
        assert result == ["entered"]

    finally:
        os.close(duplicate)


def test_concurrent_lock_creation(directory_fd):
    fd, directory = directory_fd
    barrier = threading.Barrier(4)
    errors = []
    identities = []

    def worker():
        try:
            barrier.wait(timeout=5)

            with acquire_authorization_lock(fd):
                info = (
                    directory / ".authorization.lock"
                ).stat(follow_symlinks=False)

                identities.append((info.st_dev, info.st_ino))
        except BaseException as exc:
            errors.append(exc)

    threads = [
        threading.Thread(target=worker)
        for _ in range(4)
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join(timeout=5)

    assert all(not thread.is_alive() for thread in threads)
    assert not errors
    assert len(identities) == 4
    assert len(set(identities)) == 1




def test_independent_process_lock_exclusion(directory_fd):
    import select

    fd, directory = directory_fd

    child_code = """
import os
import sys

from f066c_authorization_lock import acquire_authorization_lock

directory_fd = os.open(
    sys.argv[1],
    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
)

try:
    print("READY", flush=True)

    with acquire_authorization_lock(directory_fd):
        print("ACQUIRED", flush=True)
finally:
    os.close(directory_fd)
"""

    module_directory = str(
        __import__("pathlib").Path(
            __import__("f066c_authorization_lock").__file__
        ).resolve().parent
    )

    environment = os.environ.copy()
    environment["PYTHONPATH"] = module_directory

    process = None

    try:
        with acquire_authorization_lock(fd):
            process = subprocess.Popen(
                [sys.executable, "-u", "-c", child_code, str(directory)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=environment,
            )

            readable, _, _ = select.select(
                [process.stdout],
                [],
                [],
                5,
            )

            assert readable, "Subprocesso nao produziu READY"
            assert process.stdout.readline().strip() == "READY"

            readable, _, _ = select.select(
                [process.stdout],
                [],
                [],
                0.3,
            )

            assert not readable, (
                "Subprocesso produziu saida antes do desbloqueio"
            )

            assert process.poll() is None, (
                "Subprocesso terminou enquanto aguardava bloqueio"
            )

        stdout, stderr = process.communicate(timeout=5)

        assert process.returncode == 0, stderr
        assert stdout.strip() == "ACQUIRED"

    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.communicate(timeout=5)



def test_lock_inode_replacement_rejected(directory_fd):
    """Rejeita substituicao do lock durante a aquisicao."""
    from unittest.mock import patch

    fd, directory = directory_fd
    lock_path = directory / ".authorization.lock"

    # Criar previamente o ficheiro de bloqueio.
    with acquire_authorization_lock(fd):
        pass

    original_flock = fcntl.flock
    replaced = False

    def replace_before_lock(lock_fd, operation):
        nonlocal replaced

        if operation == fcntl.LOCK_EX and not replaced:
            replaced = True

            replacement = directory / ".replacement.lock"
            replacement.write_bytes(b"")
            replacement.chmod(0o600)

            os.replace(replacement, lock_path)

        return original_flock(lock_fd, operation)

    with patch(
        "f066c_authorization_lock.fcntl.flock",
        side_effect=replace_before_lock,
    ):
        with pytest.raises(
            PermissionError,
            match=(
                "Identidade do ficheiro de bloqueio alterada"
                "|Numero de links inseguro"
            ),
        ):
            with acquire_authorization_lock(fd):
                pytest.fail("Substituicao do inode aceite")

    assert replaced
    assert lock_path.is_file()



def test_lock_file_fsync_failure_recovery(directory_fd):
    from unittest.mock import patch

    fd, directory = directory_fd
    original_fsync = os.fsync

    def fail_file_fsync(target_fd):
        if target_fd != fd:
            raise OSError("simulated lock file fsync failure")
        return original_fsync(target_fd)

    with patch(
        "f066c_authorization_lock.os.fsync",
        side_effect=fail_file_fsync,
    ):
        with pytest.raises(
            OSError,
            match="simulated lock file fsync failure",
        ):
            with acquire_authorization_lock(fd):
                pytest.fail("Aquisicao aceite apos falha de fsync")

    lock_path = directory / ".authorization.lock"
    assert lock_path.is_file()

    before = lock_path.stat(follow_symlinks=False)

    with acquire_authorization_lock(fd):
        after = lock_path.stat(follow_symlinks=False)

    assert (before.st_dev, before.st_ino) == (
        after.st_dev, after.st_ino
    )


def test_lock_directory_fsync_failure_recovery(directory_fd):
    from unittest.mock import patch

    fd, directory = directory_fd
    original_fsync = os.fsync

    def fail_directory_fsync(target_fd):
        if target_fd == fd:
            raise OSError("simulated lock directory fsync failure")
        return original_fsync(target_fd)

    with patch(
        "f066c_authorization_lock.os.fsync",
        side_effect=fail_directory_fsync,
    ):
        with pytest.raises(
            OSError,
            match="simulated lock directory fsync failure",
        ):
            with acquire_authorization_lock(fd):
                pytest.fail("Aquisicao aceite apos falha de fsync")

    lock_path = directory / ".authorization.lock"
    assert lock_path.is_file()

    before = lock_path.stat(follow_symlinks=False)

    with acquire_authorization_lock(fd):
        after = lock_path.stat(follow_symlinks=False)

    assert (before.st_dev, before.st_ino) == (
        after.st_dev, after.st_ino
    )



def test_unlock_failure_preserves_body_error(directory_fd):
    """Uma falha de unlock nao deve ocultar a falha original."""
    from unittest.mock import patch

    fd, _ = directory_fd
    original_flock = fcntl.flock

    def fail_unlock(lock_fd, operation):
        if operation == fcntl.LOCK_UN:
            raise OSError("simulated unlock failure")
        return original_flock(lock_fd, operation)

    with patch(
        "f066c_authorization_lock.fcntl.flock",
        side_effect=fail_unlock,
    ):
        with pytest.raises(
            OSError,
            match="simulated body failure",
        ):
            with acquire_authorization_lock(fd):
                raise OSError("simulated body failure")


def test_unlock_failure_without_body_error(directory_fd):
    """Uma falha de unlock deve ser comunicada ao chamador."""
    from unittest.mock import patch

    fd, _ = directory_fd
    original_flock = fcntl.flock

    def fail_unlock(lock_fd, operation):
        if operation == fcntl.LOCK_UN:
            raise OSError("simulated unlock failure")
        return original_flock(lock_fd, operation)

    with patch(
        "f066c_authorization_lock.fcntl.flock",
        side_effect=fail_unlock,
    ):
        with pytest.raises(
            OSError,
            match="simulated unlock failure",
        ):
            with acquire_authorization_lock(fd):
                pass



def test_unlock_failure_records_note(directory_fd):
    """A excecao original conserva a nota sobre falha de unlock."""
    from unittest.mock import patch

    fd, _ = directory_fd
    original_flock = fcntl.flock

    def fail_unlock(lock_fd, operation):
        if operation == fcntl.LOCK_UN:
            raise OSError("simulated unlock failure")
        return original_flock(lock_fd, operation)

    with patch(
        "f066c_authorization_lock.fcntl.flock",
        side_effect=fail_unlock,
    ):
        with pytest.raises(
            OSError,
            match="simulated body failure",
        ) as captured:
            with acquire_authorization_lock(fd):
                raise OSError("simulated body failure")

    assert any(
        "simulated unlock failure" in note
        for note in getattr(captured.value, "__notes__", [])
    )


def test_close_failure_preserves_body_error(directory_fd):
    """Falha de close nao deve ocultar a excecao da operacao."""
    from unittest.mock import patch

    fd, _ = directory_fd
    original_close = os.close

    def fail_close(target_fd):
        if target_fd != fd:
            original_close(target_fd)
            raise OSError("simulated close failure")
        return original_close(target_fd)

    with patch(
        "f066c_authorization_lock.os.close",
        side_effect=fail_close,
    ):
        with pytest.raises(
            OSError,
            match="simulated body failure",
        ):
            with acquire_authorization_lock(fd):
                raise OSError("simulated body failure")



def test_simultaneous_unlock_and_close_failure(directory_fd):
    """A falha de unlock prevalece sobre a falha posterior de close."""
    from unittest.mock import patch

    fd, _ = directory_fd
    original_flock = fcntl.flock
    original_close = os.close

    def fail_unlock(lock_fd, operation):
        if operation == fcntl.LOCK_UN:
            raise OSError("simulated unlock failure")
        return original_flock(lock_fd, operation)

    def fail_close(target_fd):
        original_close(target_fd)
        if target_fd != fd:
            raise OSError("simulated close failure")

    with patch(
        "f066c_authorization_lock.fcntl.flock",
        side_effect=fail_unlock,
    ), patch(
        "f066c_authorization_lock.os.close",
        side_effect=fail_close,
    ):
        with pytest.raises(
            OSError,
            match="simulated unlock failure",
        ) as captured:
            with acquire_authorization_lock(fd):
                pass

    assert any(
        "simulated close failure" in note
        for note in getattr(captured.value, "__notes__", [])
    )


def test_simultaneous_body_unlock_and_close_failure(directory_fd):
    """A falha original conserva as duas notas de diagnostico."""
    from unittest.mock import patch

    fd, _ = directory_fd
    original_flock = fcntl.flock
    original_close = os.close

    def fail_unlock(lock_fd, operation):
        if operation == fcntl.LOCK_UN:
            raise OSError("simulated unlock failure")
        return original_flock(lock_fd, operation)

    def fail_close(target_fd):
        original_close(target_fd)
        if target_fd != fd:
            raise OSError("simulated close failure")

    with patch(
        "f066c_authorization_lock.fcntl.flock",
        side_effect=fail_unlock,
    ), patch(
        "f066c_authorization_lock.os.close",
        side_effect=fail_close,
    ):
        with pytest.raises(
            OSError,
            match="simulated body failure",
        ) as captured:
            with acquire_authorization_lock(fd):
                raise OSError("simulated body failure")

    notes = getattr(captured.value, "__notes__", [])

    assert any("simulated unlock failure" in note for note in notes)
    assert any("simulated close failure" in note for note in notes)
