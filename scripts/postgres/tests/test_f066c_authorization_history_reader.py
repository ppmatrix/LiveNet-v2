"""Testes do leitor fisico de historicos AUTH-03."""

import os
from dataclasses import replace
from uuid import uuid4

import pytest

from f066c_authorization import AdministrativeAuthorization
from f066c_authorization_chain import (
    initial_authorization_hash,
)
from f066c_authorization_history_reader import (
    read_authorization_history,
)
from f066c_authorization_storage import serialize_authorization
from f066c_authorization_transition_record import (
    ApprovalEvidence,
    AuthorizationTransitionRecord,
)
from f066c_authorization_transition_storage import (
    serialize_transition_record,
)


TIMESTAMP = "2026-10-20T08:00:00.000000Z"


@pytest.fixture
def storage(tmp_path):
    directory = tmp_path / "authorizations"
    directory.mkdir(mode=0o700)

    fd = os.open(
        directory,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
    )

    authorization = AdministrativeAuthorization(
        authorization_id=uuid4(),
        operation="--execute-transfer",
        target="livenetv2-f066c/livenet_f0_test",
        sql_sha256="a" * 64,
        state="prepared",
    )

    initial = directory / f"{authorization.authorization_id}.json"
    initial.write_text(serialize_authorization(authorization))
    initial.chmod(0o600)

    try:
        yield directory, fd, authorization
    finally:
        os.close(fd)


def add_transition(directory, authorization, *, sequence=1,
                   state="authorized", previous_hash=None):
    history = (
        directory / "transitions" / str(authorization.authorization_id)
    )
    transitions_root = directory / "transitions"
    transitions_root.mkdir(mode=0o700, exist_ok=True)
    history.mkdir(mode=0o700, exist_ok=True)

    evidence = None

    if state == "authorized":
        evidence = ApprovalEvidence(
            operator_uid=1000,
            approval_method="local_interactive",
            approval_timestamp=TIMESTAMP,
            presented_hash="c" * 64,
        )

    record = AuthorizationTransitionRecord(
        schema_version=1,
        authorization_id=authorization.authorization_id,
        sequence=sequence,
        from_state="prepared",
        to_state=state,
        operation=authorization.operation,
        sql_sha256=authorization.sql_sha256,
        previous_hash=(
            previous_hash
            if previous_hash is not None
            else initial_authorization_hash(authorization)
        ),
        timestamp=TIMESTAMP,
        operator_id="local-operator",
        reason="Teste",
        approval_evidence=evidence,
    )

    path = history / f"{sequence:06d}-{state}.json"
    path.write_bytes(serialize_transition_record(record))
    path.chmod(0o600)

    return path


def test_prepared_without_transitions_directory(storage):
    _, fd, authorization = storage

    result = read_authorization_history(
        fd, authorization.authorization_id
    )

    assert result.state == "prepared"
    assert result.transition_count == 0


def test_prepared_with_empty_transitions_directory(storage):
    directory, fd, authorization = storage
    history = directory / "transitions" / str(authorization.authorization_id)
    transitions_root = directory / "transitions"
    transitions_root.mkdir(mode=0o700)
    history.mkdir(mode=0o700)

    result = read_authorization_history(
        fd, authorization.authorization_id
    )

    assert result.state == "prepared"


def test_valid_authorized_transition(storage):
    directory, fd, authorization = storage
    add_transition(directory, authorization)

    result = read_authorization_history(
        fd, authorization.authorization_id
    )

    assert result.state == "authorized"
    assert result.transition_count == 1


def test_missing_initial_authorization(storage):
    directory, fd, authorization = storage
    (directory / f"{authorization.authorization_id}.json").unlink()

    with pytest.raises(FileNotFoundError):
        read_authorization_history(
            fd, authorization.authorization_id
        )


def test_initial_uuid_mismatch(storage):
    directory, fd, authorization = storage
    path = directory / f"{authorization.authorization_id}.json"

    altered = replace(authorization, authorization_id=uuid4())
    path.write_text(serialize_authorization(altered))
    path.chmod(0o600)

    with pytest.raises(ValueError, match="UUID"):
        read_authorization_history(
            fd, authorization.authorization_id
        )


def test_missing_first_sequence(storage):
    directory, fd, authorization = storage
    add_transition(directory, authorization, sequence=2)

    with pytest.raises(ValueError):
        read_authorization_history(
            fd, authorization.authorization_id
        )


def test_unexpected_filename(storage):
    directory, fd, authorization = storage
    add_transition(directory, authorization)
    history = directory / "transitions" / str(authorization.authorization_id)
    (history / "unexpected.txt").write_text("unexpected")

    with pytest.raises(ValueError):
        read_authorization_history(
            fd, authorization.authorization_id
        )


def test_internal_sequence_mismatch(storage):
    directory, fd, authorization = storage
    path = add_transition(directory, authorization, sequence=2)
    renamed = path.with_name("000001-authorized.json")
    path.rename(renamed)

    with pytest.raises(ValueError):
        read_authorization_history(
            fd, authorization.authorization_id
        )


def test_filename_state_mismatch(storage):
    directory, fd, authorization = storage
    path = add_transition(directory, authorization)
    path.rename(path.with_name("000001-consumed.json"))

    with pytest.raises(ValueError):
        read_authorization_history(
            fd, authorization.authorization_id
        )


def test_symlink_transition_file_rejected(storage):
    directory, fd, authorization = storage
    path = add_transition(directory, authorization)
    link = path.with_name("000002-consumed.json")
    link.symlink_to(path.name)

    with pytest.raises((OSError, ValueError)):
        read_authorization_history(
            fd, authorization.authorization_id
        )


def test_insecure_transition_directory_rejected(storage):
    directory, fd, authorization = storage
    add_transition(directory, authorization)
    history = directory / "transitions" / str(authorization.authorization_id)
    history.chmod(0o755)

    with pytest.raises(PermissionError):
        read_authorization_history(
            fd, authorization.authorization_id
        )


def test_invalid_uuid_type_rejected(storage):
    _, fd, _ = storage

    with pytest.raises(TypeError):
        read_authorization_history(fd, "invalid")


def test_transition_file_with_insecure_permissions(storage):
    directory, fd, authorization = storage
    path = add_transition(directory, authorization)
    path.chmod(0o644)

    with pytest.raises(PermissionError):
        read_authorization_history(
            fd, authorization.authorization_id
        )


def test_transition_file_with_hardlink(storage):
    directory, fd, authorization = storage
    path = add_transition(directory, authorization)
    os.link(path, path.with_name("duplicate-link"))

    with pytest.raises((PermissionError, ValueError)):
        read_authorization_history(
            fd, authorization.authorization_id
        )


def test_initial_file_symlink_rejected(storage):
    directory, fd, authorization = storage
    initial = directory / f"{authorization.authorization_id}.json"
    backup = directory / "original.json"

    initial.rename(backup)
    initial.symlink_to(backup.name)

    with pytest.raises(OSError):
        read_authorization_history(
            fd, authorization.authorization_id
        )


def test_initial_file_insecure_permissions(storage):
    directory, fd, authorization = storage
    initial = directory / f"{authorization.authorization_id}.json"
    initial.chmod(0o644)

    with pytest.raises(PermissionError):
        read_authorization_history(
            fd, authorization.authorization_id
        )


def test_transitions_directory_symlink_rejected(storage):
    directory, fd, authorization = storage
    real = directory / "real-transitions"
    real.mkdir(mode=0o700)

    (directory / "transitions").symlink_to(real.name)

    with pytest.raises(OSError):
        read_authorization_history(
            fd, authorization.authorization_id
        )


def test_history_directory_symlink_rejected(storage):
    directory, fd, authorization = storage
    root = directory / "transitions"
    root.mkdir(mode=0o700)

    real = root / "real"
    real.mkdir(mode=0o700)

    (root / str(authorization.authorization_id)).symlink_to(
        real.name
    )

    with pytest.raises(OSError):
        read_authorization_history(
            fd, authorization.authorization_id
        )


def test_last_transition_mutation_not_detected_without_anchor(storage):
    """Limite conhecido: ultimo registo sem ancora externa."""

    directory, fd, authorization = storage
    path = add_transition(directory, authorization)

    payload = path.read_bytes()
    path.write_bytes(payload.replace(b"Teste", b"Outro"))
    path.chmod(0o600)

    result = read_authorization_history(
        fd, authorization.authorization_id
    )

    assert result.state == "authorized"
    assert result.transition_count == 1


def test_excessive_transition_files_rejected(storage):
    directory, fd, authorization = storage
    path = add_transition(directory, authorization)
    history = path.parent

    for number in range(2, 102):
        extra = history / f"{number:06d}-consumed.json"
        extra.write_bytes(b"{}")
        extra.chmod(0o600)

    with pytest.raises(ValueError, match="excessivo"):
        read_authorization_history(
            fd, authorization.authorization_id
        )


def test_locked_reader_valid_prepared_history(storage):
    """A leitura interna reconstroi um historico prepared."""
    from f066c_authorization_history_reader import (
        _read_authorization_history_locked,
    )

    _, fd, authorization = storage

    result = _read_authorization_history_locked(
        fd,
        authorization.authorization_id,
    )

    assert result.state == "prepared"
    assert result.transition_count == 0
    assert result.next_sequence == 1


def test_locked_reader_does_not_reacquire_lock(storage, monkeypatch):
    """A leitura interna nao deve adquirir outro bloqueio."""
    import f066c_authorization_history_reader as reader

    directory, fd, authorization = storage
    add_transition(directory, authorization)

    def forbidden_lock(*args, **kwargs):
        raise AssertionError("Bloqueio adquirido novamente")

    monkeypatch.setattr(
        reader,
        "acquire_authorization_lock",
        forbidden_lock,
    )

    result = reader._read_authorization_history_locked(
        fd,
        authorization.authorization_id,
    )

    assert result.state == "authorized"
    assert result.transition_count == 1


def test_locked_reader_rejects_invalid_uuid(storage):
    """A interface interna mantem a validacao do UUID."""
    from f066c_authorization_history_reader import (
        _read_authorization_history_locked,
    )

    _, fd, _ = storage

    with pytest.raises(TypeError):
        _read_authorization_history_locked(
            fd,
            "invalid",
        )



def test_locked_reader_returns_authorization_and_prepared_history(storage):
    """A interface interna devolve autorizacao e historico prepared."""
    from f066c_authorization_history_reader import (
        _read_authorization_with_history_locked,
    )
    from f066c_authorization_lock import acquire_authorization_lock

    _, fd, authorization = storage

    with acquire_authorization_lock(fd):
        loaded, history = _read_authorization_with_history_locked(
            fd,
            authorization.authorization_id,
        )

    assert loaded == authorization
    assert history.authorization_id == str(authorization.authorization_id)
    assert history.state == "prepared"
    assert history.next_sequence == 1
    assert history.transition_count == 0


def test_locked_reader_returns_authorization_and_authorized_history(storage):
    """A interface interna devolve ambos apos uma transicao valida."""
    from f066c_authorization_history_reader import (
        _read_authorization_with_history_locked,
    )
    from f066c_authorization_lock import acquire_authorization_lock

    directory, fd, authorization = storage
    add_transition(directory, authorization)

    with acquire_authorization_lock(fd):
        loaded, history = _read_authorization_with_history_locked(
            fd,
            authorization.authorization_id,
        )

    assert loaded == authorization
    assert history.state == "authorized"
    assert history.next_sequence == 2
    assert history.transition_count == 1
