"""Testes de falhas na persistencia atomica F0.66C."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from f066c_authorization import create_authorization
from f066c_authorization_file_store import create_authorization_file
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
