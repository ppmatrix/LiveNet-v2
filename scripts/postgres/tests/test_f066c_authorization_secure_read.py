"""Testes de leitura segura AUTH-03."""

import os
from pathlib import Path

import pytest

from f066c_authorization_secure_read import read_secure_file


@pytest.fixture
def private_directory(tmp_path: Path):
    directory = tmp_path / "private"
    directory.mkdir(mode=0o700)

    fd = os.open(
        directory,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
    )

    try:
        yield directory, fd
    finally:
        os.close(fd)


def create_file(directory, name="record.json", content=b"valid"):
    path = directory / name
    path.write_bytes(content)
    path.chmod(0o600)
    return path


def test_reads_valid_private_file(private_directory):
    directory, fd = private_directory
    create_file(directory)

    assert read_secure_file(fd, "record.json") == b"valid"


def test_reads_empty_file(private_directory):
    directory, fd = private_directory
    create_file(directory, content=b"")

    assert read_secure_file(fd, "record.json") == b""


def test_rejects_oversized_file(private_directory):
    directory, fd = private_directory
    create_file(directory, content=b"x" * 10)

    with pytest.raises(ValueError):
        read_secure_file(fd, "record.json", max_bytes=9)


def test_accepts_exact_limit(private_directory):
    directory, fd = private_directory
    create_file(directory, content=b"x" * 10)

    assert read_secure_file(
        fd, "record.json", max_bytes=10
    ) == b"x" * 10


@pytest.mark.parametrize(
    "filename",
    ("", ".", "..", "../outside", "a/b", "a\x00b"),
)
def test_rejects_invalid_filename(private_directory, filename):
    _, fd = private_directory

    with pytest.raises(ValueError):
        read_secure_file(fd, filename)


def test_rejects_symlink(private_directory):
    directory, fd = private_directory
    create_file(directory)

    (directory / "link.json").symlink_to("record.json")

    with pytest.raises(OSError):
        read_secure_file(fd, "link.json")


def test_rejects_insecure_permissions(private_directory):
    directory, fd = private_directory
    path = create_file(directory)
    path.chmod(0o644)

    with pytest.raises(PermissionError):
        read_secure_file(fd, "record.json")


def test_rejects_hardlinks(private_directory):
    directory, fd = private_directory
    create_file(directory)
    os.link(directory / "record.json", directory / "copy.json")

    with pytest.raises(PermissionError):
        read_secure_file(fd, "record.json")


def test_rejects_directory_instead_of_file(private_directory):
    directory, fd = private_directory
    (directory / "record.json").mkdir()

    with pytest.raises(ValueError):
        read_secure_file(fd, "record.json")


def test_rejects_insecure_directory(private_directory):
    directory, fd = private_directory
    create_file(directory)
    directory.chmod(0o755)

    with pytest.raises(PermissionError):
        read_secure_file(fd, "record.json")


@pytest.mark.parametrize("limit", (0, -1, True, "8192"))
def test_rejects_invalid_limit(private_directory, limit):
    directory, fd = private_directory
    create_file(directory)

    with pytest.raises(ValueError):
        read_secure_file(fd, "record.json", max_bytes=limit)


def test_rejects_non_directory_descriptor(private_directory):
    directory, fd = private_directory
    path = create_file(directory)

    file_fd = os.open(path, os.O_RDONLY)

    try:
        with pytest.raises(ValueError):
            read_secure_file(file_fd, "record.json")
    finally:
        os.close(file_fd)
