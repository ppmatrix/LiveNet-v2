"""Testes da validacao de publicacao AUTH-03."""

from dataclasses import replace
from uuid import uuid4

import pytest

from f066c_authorization import AdministrativeAuthorization
from f066c_authorization_history import (
    reconstruct_authorization_history,
)
from f066c_authorization_transition_file_store import (
    validate_transition_for_publication,
)
from f066c_authorization_transition_record import (
    ApprovalEvidence,
    AuthorizationTransitionRecord,
)
from f066c_authorization_transition_storage import (
    serialize_transition_record,
)


TIMESTAMP = "2026-10-20T08:00:00.000000Z"


@pytest.fixture
def valid_case():
    authorization = AdministrativeAuthorization(
        authorization_id=uuid4(),
        operation="--execute-transfer",
        target="livenetv2-f066c/livenet_f0_test",
        sql_sha256="a" * 64,
        state="prepared",
    )

    history = reconstruct_authorization_history(
        authorization,
        [],
    )

    record = AuthorizationTransitionRecord(
        schema_version=1,
        authorization_id=authorization.authorization_id,
        sequence=1,
        from_state="prepared",
        to_state="authorized",
        operation=authorization.operation,
        sql_sha256=authorization.sql_sha256,
        previous_hash=history.last_hash,
        timestamp=TIMESTAMP,
        operator_id="local-operator",
        reason="Teste",
        approval_evidence=ApprovalEvidence(
            operator_uid=1000,
            approval_method="local_interactive",
            approval_timestamp=TIMESTAMP,
            presented_hash="c" * 64,
        ),
    )

    return authorization, history, record


def test_valid_transition_returns_canonical_payload(valid_case):
    authorization, history, record = valid_case

    result = validate_transition_for_publication(
        authorization, history, record
    )

    assert result == serialize_transition_record(record)


@pytest.mark.parametrize(
    "field,value",
    [
        ("authorization_id", uuid4()),
        ("sequence", 2),
        ("from_state", "consumed"),
        ("to_state", "succeeded"),
        ("operation", "--execute-create-roles"),
        ("sql_sha256", "b" * 64),
        ("previous_hash", "d" * 64),
    ],
)
def test_invalid_transition_rejected(valid_case, field, value):
    authorization, history, record = valid_case

    altered = replace(record, **{field: value})

    with pytest.raises((TypeError, ValueError)):
        validate_transition_for_publication(
            authorization, history, altered
        )


def test_history_uuid_mismatch_rejected(valid_case):
    authorization, history, record = valid_case

    altered = replace(history, authorization_id=str(uuid4()))

    with pytest.raises(ValueError):
        validate_transition_for_publication(
            authorization, altered, record
        )


def test_invalid_record_type_rejected(valid_case):
    authorization, history, _ = valid_case

    with pytest.raises(TypeError):
        validate_transition_for_publication(
            authorization, history, object()
        )


def test_publish_transition_payload_success(tmp_path):
    import os

    from f066c_authorization_transition_file_store import (
        publish_transition_payload,
    )

    directory = tmp_path / "transitions"
    directory.mkdir(mode=0o700)

    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)

    try:
        result = publish_transition_payload(
            fd,
            "000001-authorized.json",
            b"test-payload",
        )
    finally:
        os.close(fd)

    assert result == "000001-authorized.json"
    assert (directory / result).read_bytes() == b"test-payload"
    assert (directory / result).stat().st_mode & 0o777 == 0o600
    assert not list(directory.glob(".tmp-*"))


def test_publish_transition_payload_no_overwrite(tmp_path):
    import os

    from f066c_authorization_transition_file_store import (
        publish_transition_payload,
    )

    directory = tmp_path / "transitions"
    directory.mkdir(mode=0o700)
    target = directory / "000001-authorized.json"
    target.write_bytes(b"original")

    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)

    try:
        with pytest.raises(FileExistsError):
            publish_transition_payload(
                fd,
                target.name,
                b"replacement",
            )
    finally:
        os.close(fd)

    assert target.read_bytes() == b"original"


def test_publish_transition_payload_rejects_invalid_filename(tmp_path):
    import os

    from f066c_authorization_transition_file_store import (
        publish_transition_payload,
    )

    directory = tmp_path / "transitions"
    directory.mkdir(mode=0o700)

    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)

    try:
        with pytest.raises(ValueError):
            publish_transition_payload(
                fd,
                "../escape.json",
                b"payload",
            )
    finally:
        os.close(fd)


def test_publish_transition_payload_rejects_insecure_directory(tmp_path):
    import os

    from f066c_authorization_transition_file_store import (
        publish_transition_payload,
    )

    directory = tmp_path / "transitions"
    directory.mkdir(mode=0o755)

    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)

    try:
        with pytest.raises(PermissionError):
            publish_transition_payload(
                fd,
                "000001-authorized.json",
                b"payload",
            )
    finally:
        os.close(fd)


def test_publish_transition_payload_pre_link_failure(
    tmp_path, monkeypatch
):
    """Uma falha anterior ao link nao publica o destino."""
    import os
    import f066c_authorization_transition_file_store as store

    directory = tmp_path / "transitions"
    directory.mkdir(mode=0o700)
    filename = "000001-authorized.json"

    def fail_write(*args, **kwargs):
        raise OSError("Falha simulada antes da publicacao")

    monkeypatch.setattr(os, "write", fail_write)

    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with pytest.raises(OSError, match="Falha simulada"):
            store.publish_transition_payload(fd, filename, b"payload")
    finally:
        os.close(fd)

    assert not (directory / filename).exists()
    assert not list(directory.glob(".tmp-*"))


def test_publish_transition_payload_post_link_fsync_uncertain(
    tmp_path, monkeypatch
):
    """Falha de fsync apos link torna a durabilidade incerta."""
    import os
    import stat
    import f066c_authorization_transition_file_store as store
    from f066c_authorization_file_store import (
        AuthorizationPublicationUncertain,
    )

    directory = tmp_path / "transitions"
    directory.mkdir(mode=0o700)
    filename = "000001-authorized.json"

    original_fsync = os.fsync
    calls = []

    def controlled_fsync(fd):
        info = os.fstat(fd)
        calls.append("directory" if stat.S_ISDIR(info.st_mode) else "file")
        if stat.S_ISDIR(info.st_mode) and calls.count("directory") == 1:
            raise OSError("Falha simulada de fsync")
        return original_fsync(fd)

    monkeypatch.setattr(os, "fsync", controlled_fsync)

    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with pytest.raises(AuthorizationPublicationUncertain):
            store.publish_transition_payload(fd, filename, b"payload")
    finally:
        os.close(fd)

    assert calls[0] == "file"
    assert (directory / filename).read_bytes() == b"payload"
    assert not list(directory.glob(".tmp-*"))


def test_publish_transition_payload_cleanup_failure_uncertain(
    tmp_path, monkeypatch
):
    """Falha na limpeza apos publicacao e reportada como incerta."""
    import os
    import f066c_authorization_transition_file_store as store
    from f066c_authorization_file_store import (
        AuthorizationPublicationUncertain,
    )

    directory = tmp_path / "transitions"
    directory.mkdir(mode=0o700)
    filename = "000001-authorized.json"

    original_unlink = os.unlink

    def controlled_unlink(path, *args, **kwargs):
        if isinstance(path, str) and path.startswith(".tmp-"):
            raise OSError("Falha simulada de limpeza")
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(os, "unlink", controlled_unlink)

    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with pytest.raises(AuthorizationPublicationUncertain):
            store.publish_transition_payload(fd, filename, b"payload")
    finally:
        os.close(fd)

    assert (directory / filename).read_bytes() == b"payload"


def test_publish_transition_payload_temporary_mode(
    tmp_path, monkeypatch
):
    """O ficheiro temporario tem de ser privado."""
    import os
    import stat
    import f066c_authorization_transition_file_store as store

    directory = tmp_path / "transitions"
    directory.mkdir(mode=0o700)

    original_link = os.link
    observed_modes = []

    def inspect_link(src, dst, *args, **kwargs):
        info = os.stat(
            src,
            dir_fd=kwargs["src_dir_fd"],
            follow_symlinks=False,
        )
        observed_modes.append(stat.S_IMODE(info.st_mode))
        return original_link(src, dst, *args, **kwargs)

    monkeypatch.setattr(os, "link", inspect_link)

    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        store.publish_transition_payload(
            fd, "000001-authorized.json", b"payload"
        )
    finally:
        os.close(fd)

    assert observed_modes == [0o600]
    assert not list(directory.glob(".tmp-*"))


def test_publish_transition_payload_link_result_uncertain(
    tmp_path, monkeypatch
):
    """Um link criado sem confirmacao nao e falha definitiva."""
    import os

    import f066c_authorization_transition_file_store as store

    from f066c_authorization_file_store import (
        AuthorizationPublicationUncertain,
    )

    directory = tmp_path / "transitions"
    directory.mkdir(mode=0o700)

    filename = "000001-authorized.json"
    original_link = os.link

    def link_then_fail(src, dst, *args, **kwargs):
        original_link(src, dst, *args, **kwargs)
        raise OSError("Resultado de link nao confirmado")

    monkeypatch.setattr(os, "link", link_then_fail)

    fd = os.open(
        directory,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
    )

    try:
        with pytest.raises(AuthorizationPublicationUncertain):
            store.publish_transition_payload(
                fd,
                filename,
                b"payload",
            )
    finally:
        os.close(fd)

    assert (directory / filename).read_bytes() == b"payload"
    assert not list(directory.glob(".tmp-*"))


def test_publish_transition_payload_close_failure(
    tmp_path, monkeypatch
):
    """Falha de close antes do link impede a publicacao."""
    import os
    import stat
    import f066c_authorization_transition_file_store as store

    directory = tmp_path / "transitions"
    directory.mkdir(mode=0o700)
    filename = "000001-authorized.json"

    original_close = os.close
    simulated = []

    def controlled_close(fd):
        info = os.fstat(fd)
        if (
            not simulated
            and stat.S_ISREG(info.st_mode)
        ):
            simulated.append(True)
            original_close(fd)
            raise OSError("Falha simulada de close")
        return original_close(fd)

    monkeypatch.setattr(os, "close", controlled_close)

    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with pytest.raises(OSError, match="Falha simulada de close"):
            store.publish_transition_payload(
                fd, filename, b"payload"
            )
    finally:
        os.close(fd)

    assert simulated
    assert not (directory / filename).exists()
    assert not list(directory.glob(".tmp-*"))


def test_publish_transition_payload_write_and_close_failure(
    tmp_path, monkeypatch
):
    """A falha de close nao deve ocultar a falha de escrita."""
    import os
    import stat
    import f066c_authorization_transition_file_store as store

    directory = tmp_path / "transitions"
    directory.mkdir(mode=0o700)
    filename = "000001-authorized.json"

    original_close = os.close
    close_failed = []

    def fail_write(*args, **kwargs):
        raise OSError("Falha principal de escrita")

    def controlled_close(fd):
        info = os.fstat(fd)
        if (
            not close_failed
            and stat.S_ISREG(info.st_mode)
        ):
            close_failed.append(True)
            original_close(fd)
            raise OSError("Falha secundaria de close")
        return original_close(fd)

    monkeypatch.setattr(os, "write", fail_write)
    monkeypatch.setattr(os, "close", controlled_close)

    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with pytest.raises(
            OSError, match="Falha principal de escrita"
        ) as captured:
            store.publish_transition_payload(
                fd, filename, b"payload"
            )
    finally:
        os.close(fd)

    assert close_failed
    assert not (directory / filename).exists()
    assert not list(directory.glob(".tmp-*"))
    assert any(
        "Falha secundaria de close" in note
        for note in getattr(captured.value, "__notes__", [])
    )
