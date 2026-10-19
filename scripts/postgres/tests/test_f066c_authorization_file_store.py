"""Testes de falhas na persistencia atomica F0.66C."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from f066c_authorization import create_authorization
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

    try:
        yield directory_fd, directory
    finally:
        os.close(directory_fd)


@pytest.fixture
def authorization():
    plan = prepare_execution_plan("--execute-transfer")
    return create_authorization(plan)


def assert_no_files(directory: Path):
    assert list(directory.iterdir()) == []


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
    assert sorted(p.name for p in directory.iterdir()) == [filename]
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
    assert sorted(p.name for p in directory.iterdir()) == [filename]
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
    directory_fd, directory = storage
    import fcntl

    original_flock = fcntl.flock

    def fail_unlock(fd, operation):
        if operation == fcntl.LOCK_UN:
            raise OSError("simulated unlock failure")
        return original_flock(fd, operation)

    with patch(
        "f066c_authorization_file_store.fcntl.flock",
        side_effect=fail_unlock,
    ):
        with pytest.raises(
            AuthorizationPublicationUncertain,
        ) as captured:
            create_authorization_file(directory_fd, authorization)

    assert (directory / captured.value.filename).exists()
