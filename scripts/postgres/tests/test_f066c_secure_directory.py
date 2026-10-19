"""Testes de seguranca dos diretorios F0.66C."""

import os
import stat

import pytest

from f066c_secure_directory import (
    create_secure_subdirectories,
    create_secure_subdirectories_at,
    open_authorization_directory,
    open_secure_directory,
)


def test_create_private_hierarchy(tmp_path):
    fd = create_secure_subdirectories(
        tmp_path,
        ("livenet-v2", "f066c-authorizations"),
    )
    try:
        info = os.fstat(fd)
        assert info.st_uid == os.getuid()
        assert stat.S_IMODE(info.st_mode) == 0o700
    finally:
        os.close(fd)


def test_existing_private_hierarchy(tmp_path):
    components = ("livenet-v2", "f066c-authorizations")

    for _ in range(2):
        fd = create_secure_subdirectories(tmp_path, components)
        os.close(fd)


def test_symlink_component_rejected(tmp_path):
    target = tmp_path / "target"
    target.mkdir(mode=0o700)

    (tmp_path / "link").symlink_to(
        target,
        target_is_directory=True,
    )

    with pytest.raises(OSError):
        create_secure_subdirectories(
            tmp_path,
            ("link", "child"),
        )


@pytest.mark.parametrize("mode", (0o770, 0o707, 0o755))
def test_insecure_private_component_rejected(tmp_path, mode):
    child = tmp_path / "child"
    child.mkdir(mode=0o700)
    child.chmod(mode)

    with pytest.raises(PermissionError):
        create_secure_subdirectories(
            tmp_path,
            ("child", "nested"),
        )


@pytest.mark.parametrize(
    "component",
    ("", ".", "..", "a/b", "a" + chr(0) + "b"),
)
def test_invalid_component_rejected(tmp_path, component):
    with pytest.raises(ValueError):
        create_secure_subdirectories(
            tmp_path,
            (component,),
        )


def test_group_writable_ancestor_rejected(tmp_path):
    ancestor = tmp_path / "ancestor"
    ancestor.mkdir(mode=0o700)
    ancestor.chmod(0o770)

    with pytest.raises(PermissionError):
        create_secure_subdirectories(
            ancestor,
            ("child",),
        )


def test_public_writable_ancestor_rejected(tmp_path):
    ancestor = tmp_path / "ancestor"
    ancestor.mkdir(mode=0o700)
    ancestor.chmod(0o707)

    with pytest.raises(PermissionError):
        create_secure_subdirectories(
            ancestor,
            ("child",),
        )


def test_open_private_directory(tmp_path):
    target = tmp_path / "private"
    target.mkdir(mode=0o700)

    fd = open_secure_directory(target)
    try:
        assert stat.S_IMODE(os.fstat(fd).st_mode) == 0o700
    finally:
        os.close(fd)


def test_open_symlink_rejected(tmp_path):
    target = tmp_path / "private"
    target.mkdir(mode=0o700)

    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)

    with pytest.raises(OSError):
        open_secure_directory(link)


def test_open_insecure_directory_rejected(tmp_path):
    target = tmp_path / "private"
    target.mkdir(mode=0o700)
    target.chmod(0o770)

    with pytest.raises(PermissionError):
        open_secure_directory(target)


def test_relative_path_rejected(tmp_path):
    with pytest.raises(ValueError):
        open_secure_directory("relative/path")


def test_symlink_ancestor_rejected(tmp_path):
    target = tmp_path / "trusted"
    target.mkdir(mode=0o700)

    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)

    with pytest.raises(OSError):
        create_secure_subdirectories(link, ("child",))


def test_empty_components_rejected(tmp_path):
    with pytest.raises(ValueError):
        create_secure_subdirectories(tmp_path, ())



def test_authorization_directory_created(tmp_path):
    base = tmp_path / "config"
    base.mkdir(mode=0o700)

    fd = open_authorization_directory(base)
    try:
        assert stat.S_IMODE(os.fstat(fd).st_mode) == 0o700
        assert (base / "livenet-v2" / "f066c-authorizations").is_dir()
    finally:
        os.close(fd)


def test_authorization_directory_rejects_unsafe_base(tmp_path):
    base = tmp_path / "config"
    base.mkdir(mode=0o700)
    base.chmod(0o770)

    with pytest.raises(PermissionError):
        open_authorization_directory(base)


def test_descriptor_preserved_after_creation(tmp_path):
    parent_fd = os.open(
        tmp_path,
        os.O_RDONLY | os.O_DIRECTORY,
    )

    try:
        child_fd = create_secure_subdirectories_at(
            parent_fd,
            ("private",),
        )
        os.close(child_fd)

        assert stat.S_ISDIR(os.fstat(parent_fd).st_mode)
    finally:
        os.close(parent_fd)


def test_descriptor_survives_directory_rename(tmp_path):
    original = tmp_path / "original"
    original.mkdir(mode=0o700)

    parent_fd = os.open(
        original,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
    )

    try:
        renamed = tmp_path / "renamed"
        original.rename(renamed)

        child_fd = create_secure_subdirectories_at(
            parent_fd,
            ("private",),
        )

        os.close(child_fd)

        assert (renamed / "private").is_dir()
        assert not original.exists()
    finally:
        os.close(parent_fd)


def test_descriptor_rejects_symlink(tmp_path):
    target = tmp_path / "target"
    target.mkdir(mode=0o700)

    (tmp_path / "link").symlink_to(
        target,
        target_is_directory=True,
    )

    parent_fd = os.open(
        tmp_path,
        os.O_RDONLY | os.O_DIRECTORY,
    )

    try:
        with pytest.raises(OSError):
            create_secure_subdirectories_at(
                parent_fd,
                ("link",),
            )
    finally:
        os.close(parent_fd)


def test_descriptor_rejects_unsafe_permissions(tmp_path):
    child = tmp_path / "child"
    child.mkdir(mode=0o700)
    child.chmod(0o770)

    parent_fd = os.open(
        tmp_path,
        os.O_RDONLY | os.O_DIRECTORY,
    )

    try:
        with pytest.raises(PermissionError):
            create_secure_subdirectories_at(
                parent_fd,
                ("child",),
            )
    finally:
        os.close(parent_fd)
