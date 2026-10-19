"""Testes de falhas na persistencia atomica F0.66C."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from f066c_authorization import create_authorization
from f066c_authorization_lock import acquire_authorization_lock
from f066c_authorization_file_store import (
    AuthorizationPublicationUncertain,
    create_authorization_file,
)
from f066c_execution_plan import prepare_execution_plan
from f066c_secure_directory import open_authorization_directory


@pytest.fixture
def storage(tmp_path):
    base = tmp_path / "config"
    base.mkdir(mode=0o700)

    directory_fd = open_authorization_directory(base)
    directory = base / "livenet-v2" / "f066c-authorizations"

    # Criar e sincronizar o bloqueio antes da injecao de falhas.
    with acquire_authorization_lock(directory_fd):
        pass

    try:
        yield directory_fd, directory
    finally:
        os.close(directory_fd)


@pytest.fixture
def authorization():
    plan = prepare_execution_plan("--execute-transfer")
    return create_authorization(plan)


def assert_no_files(directory: Path):
    assert sorted(p.name for p in directory.iterdir()) == [
        ".authorization.lock"
    ]


def test_write_failure_cleanup(storage, authorization):
    directory_fd, directory = storage

    with patch(
        "f066c_authorization_file_store.os.write",
        side_effect=OSError("simulated write failure"),
    ):
        with pytest.raises(OSError, match="simulated write failure"):
            create_authorization_file(
                directory_fd,
                authorization,
            )

    assert_no_files(directory)


def test_file_fsync_failure_cleanup(storage, authorization):
    directory_fd, directory = storage

    original_fsync = os.fsync

    def fail_file_fsync(fd):
        if fd != directory_fd:
            raise OSError("simulated file fsync failure")
        return original_fsync(fd)

    with patch(
        "f066c_authorization_file_store.os.fsync",
        side_effect=fail_file_fsync,
    ):
        with pytest.raises(
            OSError,
            match="simulated file fsync failure",
        ):
            create_authorization_file(
                directory_fd,
                authorization,
            )

    assert_no_files(directory)


def test_link_failure_cleanup(storage, authorization):
    directory_fd, directory = storage

    with patch(
        "f066c_authorization_file_store.os.link",
        side_effect=OSError("simulated link failure"),
    ):
        with pytest.raises(OSError, match="simulated link failure"):
            create_authorization_file(
                directory_fd,
                authorization,
            )

    assert_no_files(directory)



def test_first_directory_fsync_failure(storage, authorization):
    directory_fd, directory = storage
    original_fsync = os.fsync
    calls = 0

    def fail_first_directory_fsync(fd):
        nonlocal calls

        if fd == directory_fd:
            calls += 1
            if calls == 1:
                raise OSError("simulated publication fsync failure")

        return original_fsync(fd)

    with patch(
        "f066c_authorization_file_store.os.fsync",
        side_effect=fail_first_directory_fsync,
    ):
        with pytest.raises(
            AuthorizationPublicationUncertain,
        ) as captured:
            create_authorization_file(
                directory_fd,
                authorization,
            )

    assert captured.value.filename == f"{authorization.authorization_id}.json"

    filename = f"{authorization.authorization_id}.json"

    assert (directory / filename).is_file()
    assert sorted(p.name for p in directory.iterdir()) == [".authorization.lock", filename]
    assert calls == 2


def test_cleanup_directory_fsync_failure(storage, authorization):
    directory_fd, directory = storage
    original_fsync = os.fsync
    calls = 0

    def fail_cleanup_directory_fsync(fd):
        nonlocal calls

        if fd == directory_fd:
            calls += 1
            if calls == 2:
                raise OSError("simulated cleanup fsync failure")

        return original_fsync(fd)

    with patch(
        "f066c_authorization_file_store.os.fsync",
        side_effect=fail_cleanup_directory_fsync,
    ):
        with pytest.raises(
            AuthorizationPublicationUncertain,
        ) as captured:
            create_authorization_file(
                directory_fd,
                authorization,
            )

    assert captured.value.filename == f"{authorization.authorization_id}.json"

    filename = f"{authorization.authorization_id}.json"

    assert (directory / filename).is_file()
    assert sorted(p.name for p in directory.iterdir()) == [".authorization.lock", filename]
    assert calls == 2



def test_write_and_cleanup_failure(storage, authorization):
    directory_fd, directory = storage
    original_unlink = os.unlink

    def fail_temporary_unlink(path, *, dir_fd=None):
        if str(path).startswith(".tmp-"):
            raise OSError("simulated cleanup failure")
        return original_unlink(path, dir_fd=dir_fd)

    with (
        patch(
            "f066c_authorization_file_store.os.write",
            side_effect=OSError("simulated write failure"),
        ),
        patch(
            "f066c_authorization_file_store.os.unlink",
            side_effect=fail_temporary_unlink,
        ),
    ):
        with pytest.raises(OSError) as captured:
            create_authorization_file(directory_fd, authorization)

    assert "simulated write failure" in str(captured.value)
    assert not (directory / f"{authorization.authorization_id}.json").exists()


def test_publication_and_cleanup_failure(storage, authorization):
    directory_fd, directory = storage
    original_fsync = os.fsync
    original_unlink = os.unlink

    def fail_publication_fsync(fd):
        if fd == directory_fd:
            raise OSError("simulated publication fsync failure")
        return original_fsync(fd)

    def fail_temporary_unlink(path, *, dir_fd=None):
        if str(path).startswith(".tmp-"):
            raise OSError("simulated cleanup failure")
        return original_unlink(path, dir_fd=dir_fd)

    with (
        patch(
            "f066c_authorization_file_store.os.fsync",
            side_effect=fail_publication_fsync,
        ),
        patch(
            "f066c_authorization_file_store.os.unlink",
            side_effect=fail_temporary_unlink,
        ),
    ):
        with pytest.raises(
            AuthorizationPublicationUncertain,
        ) as captured:
            create_authorization_file(directory_fd, authorization)

    assert captured.value.filename == f"{authorization.authorization_id}.json"
    assert (directory / captured.value.filename).exists()


def test_unlock_failure_after_publication(storage, authorization):
    """Falha real de LOCK_UN apos publicacao implica resultado incerto."""
    import fcntl

    directory_fd, directory = storage
    original_flock = fcntl.flock

    def fail_unlock(fd, operation):
        if operation == fcntl.LOCK_UN:
            raise OSError("simulated dedicated unlock failure")
        return original_flock(fd, operation)

    with patch(
        "f066c_authorization_lock.fcntl.flock",
        side_effect=fail_unlock,
    ):
        with pytest.raises(
            AuthorizationPublicationUncertain,
        ) as captured:
            create_authorization_file(directory_fd, authorization)

    assert captured.value.filename == (
        f"{authorization.authorization_id}.json"
    )
    assert (directory / captured.value.filename).is_file()
    assert sorted(p.name for p in directory.iterdir()) == [
        ".authorization.lock",
        captured.value.filename,
    ]


def test_publication_uses_dedicated_lock(storage, authorization):
    """A publicacao deve adquirir o bloqueio dedicado."""
    from contextlib import contextmanager
    from unittest.mock import patch

    directory_fd, _ = storage
    acquisitions = []

    @contextmanager
    def tracked_lock(fd):
        acquisitions.append(fd)
        yield

    with patch(
        "f066c_authorization_file_store.acquire_authorization_lock",
        tracked_lock,
        create=True,
    ):
        create_authorization_file(directory_fd, authorization)

    assert acquisitions == [directory_fd]


def test_dedicated_unlock_failure_after_publication(
    storage, authorization
):
    """Falha ao libertar lock apos publicar implica resultado incerto."""
    from contextlib import contextmanager
    from unittest.mock import patch

    directory_fd, directory = storage

    @contextmanager
    def failing_lock(fd):
        yield
        raise OSError("simulated dedicated unlock failure")

    with patch(
        "f066c_authorization_file_store.acquire_authorization_lock",
        failing_lock,
        create=True,
    ):
        with pytest.raises(
            AuthorizationPublicationUncertain,
        ):
            create_authorization_file(directory_fd, authorization)

    filename = f"{authorization.authorization_id}.json"
    assert (directory / filename).exists()



def test_lock_acquisition_failure_no_publication(
    storage, authorization
):
    """Uma falha na aquisicao nao pode criar uma autorizacao."""
    from contextlib import contextmanager

    directory_fd, directory = storage

    @contextmanager
    def failing_acquisition(fd):
        assert fd == directory_fd
        raise OSError("simulated lock acquisition failure")
        yield

    with patch(
        "f066c_authorization_file_store.acquire_authorization_lock",
        failing_acquisition,
    ):
        with pytest.raises(
            OSError,
            match="simulated lock acquisition failure",
        ):
            create_authorization_file(directory_fd, authorization)

    assert sorted(p.name for p in directory.iterdir()) == [
        ".authorization.lock"
    ]



def test_duplicate_publication_preserves_original(
    storage, authorization
):
    """Uma segunda publicacao nao substitui o ficheiro existente."""
    directory_fd, directory = storage

    filename = create_authorization_file(
        directory_fd,
        authorization,
    )

    target = directory / filename

    original_content = target.read_bytes()
    original_stat = target.stat()

    with pytest.raises(FileExistsError):
        create_authorization_file(
            directory_fd,
            authorization,
        )

    current_stat = target.stat()

    assert target.read_bytes() == original_content
    assert current_stat.st_ino == original_stat.st_ino
    assert current_stat.st_dev == original_stat.st_dev

    assert sorted(p.name for p in directory.iterdir()) == [
        ".authorization.lock",
        filename,
    ]



def test_concurrent_duplicate_publication(storage, authorization):
    """Duas publicacoes concorrentes nao substituem a autorizacao."""
    import threading

    from f066c_authorization_storage import deserialize_authorization

    directory_fd, directory = storage

    barrier = threading.Barrier(3, timeout=10)
    results = []
    results_lock = threading.Lock()

    def worker():
        fd = None
        outcome = None

        try:
            fd = os.open(
                directory,
                os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC,
            )

            barrier.wait()

            filename = create_authorization_file(
                fd,
                authorization,
            )
            outcome = ("success", filename)

        except FileExistsError:
            outcome = ("duplicate", None)

        except BaseException as exc:
            outcome = ("error", repr(exc))

        finally:
            if fd is not None:
                os.close(fd)

            with results_lock:
                results.append(outcome)

    threads = [
        threading.Thread(target=worker, daemon=True)
        for _ in range(2)
    ]

    for thread in threads:
        thread.start()

    barrier.wait()

    for thread in threads:
        thread.join(timeout=10)

    assert all(not thread.is_alive() for thread in threads)
    assert len(results) == 2

    assert sorted(result[0] for result in results) == [
        "duplicate",
        "success",
    ], results

    filename = f"{authorization.authorization_id}.json"
    target = directory / filename

    assert target.is_file()

    restored = deserialize_authorization(target.read_text())
    assert restored == authorization

    assert sorted(p.name for p in directory.iterdir()) == [
        ".authorization.lock",
        filename,
    ]



def test_combined_write_and_unlock_failure(storage, authorization):
    """A falha de escrita deve prevalecer sobre a falha de unlock."""
    import fcntl

    directory_fd, directory = storage
    original_flock = fcntl.flock

    def fail_unlock(fd, operation):
        if operation == fcntl.LOCK_UN:
            raise OSError("simulated unlock failure")
        return original_flock(fd, operation)

    with (
        patch(
            "f066c_authorization_file_store.os.write",
            side_effect=OSError("simulated write failure"),
        ),
        patch(
            "f066c_authorization_lock.fcntl.flock",
            side_effect=fail_unlock,
        ),
    ):
        with pytest.raises(OSError) as captured:
            create_authorization_file(directory_fd, authorization)

    assert "simulated write failure" in str(captured.value)
    assert sorted(p.name for p in directory.iterdir()) == [
        ".authorization.lock"
    ]


def test_combined_publication_fsync_and_unlock_failure(
    storage, authorization
):
    """Uma publicacao incerta conserva ambas as falhas."""
    import fcntl

    directory_fd, directory = storage
    original_fsync = os.fsync
    original_flock = fcntl.flock

    def fail_publication_fsync(fd):
        if fd == directory_fd:
            raise OSError("simulated publication fsync failure")
        return original_fsync(fd)

    def fail_unlock(fd, operation):
        if operation == fcntl.LOCK_UN:
            raise OSError("simulated unlock failure")
        return original_flock(fd, operation)

    with (
        patch(
            "f066c_authorization_file_store.os.fsync",
            side_effect=fail_publication_fsync,
        ),
        patch(
            "f066c_authorization_lock.fcntl.flock",
            side_effect=fail_unlock,
        ),
    ):
        with pytest.raises(
            AuthorizationPublicationUncertain,
        ) as captured:
            create_authorization_file(directory_fd, authorization)

    filename = f"{authorization.authorization_id}.json"

    assert captured.value.filename == filename
    assert (directory / filename).is_file()

    details = repr(captured.value.__cause__)
    details += " " + " ".join(
        getattr(captured.value.__cause__, "__notes__", [])
    )

    assert "simulated publication fsync failure" in details
    assert "simulated unlock failure" in details
