"""Testes de abertura segura de diretorios AUTH-03."""

import os

import pytest

from f066c_authorization_directory_read import (
    open_existing_subdirectory,
)


@pytest.fixture
def parent(tmp_path):
    path = tmp_path / "private"
    path.mkdir(mode=0o700)

    fd = os.open(
        path,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
    )

    try:
        yield path, fd
    finally:
        os.close(fd)


def test_opens_existing_directory(parent):
    path, fd = parent
    (path / "transitions").mkdir(mode=0o700)

    child_fd = open_existing_subdirectory(fd, "transitions")

    try:
        assert os.fstat(child_fd).st_ino == (
            path / "transitions"
        ).stat().st_ino
    finally:
        os.close(child_fd)


def test_does_not_create_missing_directory(parent):
    path, fd = parent

    with pytest.raises(FileNotFoundError):
        open_existing_subdirectory(fd, "transitions")

    assert not (path / "transitions").exists()


@pytest.mark.parametrize(
    "component",
    ("", ".", "..", "../outside", "a/b", "a\x00b", None),
)
def test_rejects_invalid_component(parent, component):
    _, fd = parent

    with pytest.raises(ValueError):
        open_existing_subdirectory(fd, component)


def test_rejects_symlink(parent):
    path, fd = parent
    (path / "real").mkdir(mode=0o700)
    (path / "transitions").symlink_to("real")

    with pytest.raises(OSError):
        open_existing_subdirectory(fd, "transitions")


def test_rejects_insecure_child_permissions(parent):
    path, fd = parent
    child = path / "transitions"
    child.mkdir(mode=0o755)

    with pytest.raises(PermissionError):
        open_existing_subdirectory(fd, "transitions")


def test_rejects_insecure_parent_permissions(parent):
    path, fd = parent
    (path / "transitions").mkdir(mode=0o700)
    path.chmod(0o755)

    with pytest.raises(PermissionError):
        open_existing_subdirectory(fd, "transitions")


def test_rejects_regular_file(parent):
    path, fd = parent
    (path / "transitions").write_text("not a directory")

    with pytest.raises((OSError, ValueError)):
        open_existing_subdirectory(fd, "transitions")


def test_rejects_non_directory_parent(parent):
    path, _ = parent
    file_path = path / "file"
    file_path.write_text("test")

    fd = os.open(file_path, os.O_RDONLY)

    try:
        with pytest.raises(ValueError):
            open_existing_subdirectory(fd, "transitions")
    finally:
        os.close(fd)
