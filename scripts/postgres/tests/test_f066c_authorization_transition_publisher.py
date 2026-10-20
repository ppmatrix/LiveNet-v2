"""Testes do coordenador local de transicoes AUTH-03.

Nao concede autorizacoes administrativas nem executa SQL.
"""

import os
from uuid import uuid4

from f066c_authorization import AdministrativeAuthorization
from f066c_authorization_chain import initial_authorization_hash
from f066c_authorization_history_reader import (
    read_authorization_history,
)
from f066c_authorization_storage import serialize_authorization
from f066c_authorization_transition_record import (
    ApprovalEvidence,
    AuthorizationTransitionRecord,
)


TIMESTAMP = "2026-10-20T08:00:00.000000Z"


def test_publish_first_authorized_transition(tmp_path):
    """Publica a primeira transicao num historico preparado."""
    from f066c_authorization_transition_publisher import (
        publish_authorization_transition,
    )

    directory = tmp_path / "authorizations"
    directory.mkdir(mode=0o700)

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

    record = AuthorizationTransitionRecord(
        schema_version=1,
        authorization_id=authorization.authorization_id,
        sequence=1,
        from_state="prepared",
        to_state="authorized",
        operation=authorization.operation,
        sql_sha256=authorization.sql_sha256,
        previous_hash=initial_authorization_hash(authorization),
        timestamp=TIMESTAMP,
        operator_id="test-operator",
        reason="Teste local de persistencia",
        approval_evidence=ApprovalEvidence(
            operator_uid=os.getuid(),
            approval_method="local_interactive",
            approval_timestamp=TIMESTAMP,
            presented_hash="c" * 64,
        ),
    )

    fd = os.open(
        directory,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
    )

    try:
        filename = publish_authorization_transition(
            fd,
            authorization.authorization_id,
            record,
        )

        assert filename == "000001-authorized.json"

        history = read_authorization_history(
            fd,
            authorization.authorization_id,
        )

        assert history.state == "authorized"
        assert history.next_sequence == 2
        assert history.transition_count == 1

        expected = (
            directory
            / "transitions"
            / str(authorization.authorization_id)
            / filename
        )

        assert expected.is_file()
        assert expected.stat().st_mode & 0o777 == 0o600

    finally:
        os.close(fd)



def test_publication_fsync_failure_is_uncertain(
    tmp_path, monkeypatch
):
    """Falha apos publicacao nao pode ser tratada como sucesso."""
    import pytest

    from f066c_authorization_file_store import (
        AuthorizationPublicationUncertain,
    )
    from f066c_authorization_transition_publisher import (
        publish_authorization_transition,
    )

    directory = tmp_path / "authorizations"
    directory.mkdir(mode=0o700)

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

    record = AuthorizationTransitionRecord(
        schema_version=1,
        authorization_id=authorization.authorization_id,
        sequence=1,
        from_state="prepared",
        to_state="authorized",
        operation=authorization.operation,
        sql_sha256=authorization.sql_sha256,
        previous_hash=initial_authorization_hash(authorization),
        timestamp=TIMESTAMP,
        operator_id="test-operator",
        reason="Teste de falha de sincronizacao",
        approval_evidence=ApprovalEvidence(
            operator_uid=os.getuid(),
            approval_method="local_interactive",
            approval_timestamp=TIMESTAMP,
            presented_hash="c" * 64,
        ),
    )

    fd = os.open(
        directory,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
    )

    original_fsync = os.fsync
    injected = []

    def fail_history_directory_fsync(target_fd):
        info = os.fstat(target_fd)

        if (
            not injected
            and os.path.isdir(
                f"/proc/self/fd/{target_fd}"
            )
            and info.st_ino
            == (directory / "transitions" /
                str(authorization.authorization_id)).stat().st_ino
        ):
            injected.append(True)
            raise OSError("Falha simulada apos publicacao")

        return original_fsync(target_fd)

    try:
        # Prepara os diretorios antes da injecao da falha.
        history_directory = (
            directory / "transitions" /
            str(authorization.authorization_id)
        )
        transitions_directory = directory / "transitions"
        transitions_directory.mkdir(mode=0o700)
        history_directory.mkdir(mode=0o700)

        assert transitions_directory.stat().st_mode & 0o777 == 0o700
        assert history_directory.stat().st_mode & 0o777 == 0o700

        monkeypatch.setattr(
            os, "fsync", fail_history_directory_fsync
        )

        with pytest.raises(
            AuthorizationPublicationUncertain
        ):
            publish_authorization_transition(
                fd,
                authorization.authorization_id,
                record,
            )

        assert injected

        expected = history_directory / "000001-authorized.json"
        assert expected.is_file()

        # A falha nao deixou o bloqueio permanentemente retido.
        history = read_authorization_history(
            fd,
            authorization.authorization_id,
        )
        assert history.state == "authorized"

    finally:
        os.close(fd)



def test_duplicate_transition_is_rejected(tmp_path):
    """A mesma transicao nao pode ser publicada duas vezes."""
    import pytest

    from f066c_authorization_transition_publisher import (
        publish_authorization_transition,
    )

    directory = tmp_path / "authorizations"
    directory.mkdir(mode=0o700)

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

    record = AuthorizationTransitionRecord(
        schema_version=1,
        authorization_id=authorization.authorization_id,
        sequence=1,
        from_state="prepared",
        to_state="authorized",
        operation=authorization.operation,
        sql_sha256=authorization.sql_sha256,
        previous_hash=initial_authorization_hash(authorization),
        timestamp=TIMESTAMP,
        operator_id="test-operator",
        reason="Teste de duplicacao",
        approval_evidence=ApprovalEvidence(
            operator_uid=os.getuid(),
            approval_method="local_interactive",
            approval_timestamp=TIMESTAMP,
            presented_hash="c" * 64,
        ),
    )

    fd = os.open(
        directory,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
    )

    try:
        filename = publish_authorization_transition(
            fd,
            authorization.authorization_id,
            record,
        )

        path = (
            directory
            / "transitions"
            / str(authorization.authorization_id)
            / filename
        )

        original_bytes = path.read_bytes()
        original_inode = path.stat().st_ino

        with pytest.raises(ValueError):
            publish_authorization_transition(
                fd,
                authorization.authorization_id,
                record,
            )

        assert path.read_bytes() == original_bytes
        assert path.stat().st_ino == original_inode

        history = read_authorization_history(
            fd,
            authorization.authorization_id,
        )

        assert history.state == "authorized"
        assert history.transition_count == 1
        assert history.next_sequence == 2

    finally:
        os.close(fd)



def test_concurrent_duplicate_transition_is_rejected(tmp_path):
    """Duas tentativas concorrentes nao publicam duas transicoes."""
    import threading
    from concurrent.futures import ThreadPoolExecutor

    from f066c_authorization_transition_publisher import (
        publish_authorization_transition,
    )

    directory = tmp_path / "authorizations"
    directory.mkdir(mode=0o700)

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

    record = AuthorizationTransitionRecord(
        schema_version=1,
        authorization_id=authorization.authorization_id,
        sequence=1,
        from_state="prepared",
        to_state="authorized",
        operation=authorization.operation,
        sql_sha256=authorization.sql_sha256,
        previous_hash=initial_authorization_hash(authorization),
        timestamp=TIMESTAMP,
        operator_id="test-operator",
        reason="Teste de concorrencia",
        approval_evidence=ApprovalEvidence(
            operator_uid=os.getuid(),
            approval_method="local_interactive",
            approval_timestamp=TIMESTAMP,
            presented_hash="c" * 64,
        ),
    )

    barrier = threading.Barrier(2, timeout=5)

    def attempt():
        fd = os.open(
            directory,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
        )

        try:
            barrier.wait(timeout=5)

            return publish_authorization_transition(
                fd,
                authorization.authorization_id,
                record,
            )
        finally:
            os.close(fd)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(attempt)
            for _ in range(2)
        ]

        results = []
        errors = []

        for future in futures:
            try:
                results.append(future.result(timeout=10))
            except Exception as exc:
                errors.append(exc)

    assert results == ["000001-authorized.json"]
    assert len(errors) == 1
    assert isinstance(errors[0], ValueError)

    history_directory = (
        directory
        / "transitions"
        / str(authorization.authorization_id)
    )

    assert sorted(
        item.name for item in history_directory.iterdir()
    ) == ["000001-authorized.json"]

    fd = os.open(
        directory,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
    )

    try:
        history = read_authorization_history(
            fd,
            authorization.authorization_id,
        )

        assert history.state == "authorized"
        assert history.transition_count == 1
        assert history.next_sequence == 2
    finally:
        os.close(fd)



def test_publication_uncertain_survives_directory_close_failure(
    tmp_path, monkeypatch
):
    """Falha de limpeza nao deve ocultar publicacao incerta."""
    import pytest
    import f066c_authorization_transition_publisher as publisher

    from f066c_authorization_file_store import (
        AuthorizationPublicationUncertain,
    )

    directory = tmp_path / "authorizations"
    directory.mkdir(mode=0o700)

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

    record = AuthorizationTransitionRecord(
        schema_version=1,
        authorization_id=authorization.authorization_id,
        sequence=1,
        from_state="prepared",
        to_state="authorized",
        operation=authorization.operation,
        sql_sha256=authorization.sql_sha256,
        previous_hash=initial_authorization_hash(authorization),
        timestamp=TIMESTAMP,
        operator_id="test-operator",
        reason="Teste de preservacao de excecao",
        approval_evidence=ApprovalEvidence(
            operator_uid=os.getuid(),
            approval_method="local_interactive",
            approval_timestamp=TIMESTAMP,
            presented_hash="c" * 64,
        ),
    )

    fd = os.open(
        directory,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
    )

    original_close = os.close
    injected = []

    def uncertain_publish(history_fd, filename, payload):
        raise AuthorizationPublicationUncertain(
            "Publicacao simulada de resultado incerto"
        )

    def failing_close(target_fd):
        history_directory = (
            directory
            / "transitions"
            / str(authorization.authorization_id)
        )

        target_info = os.fstat(target_fd)

        if history_directory.is_dir():
            history_info = history_directory.stat()

            if (
                not injected
                and target_info.st_dev == history_info.st_dev
                and target_info.st_ino == history_info.st_ino
            ):
                injected.append(True)
                original_close(target_fd)
                raise OSError(
                    "Falha simulada no fecho do diretorio de historico"
                )

        return original_close(target_fd)

    monkeypatch.setattr(
        publisher,
        "publish_transition_payload",
        uncertain_publish,
    )
    monkeypatch.setattr(
        publisher.os,
        "close",
        failing_close,
    )

    try:
        with pytest.raises(
            AuthorizationPublicationUncertain
        ):
            publisher.publish_authorization_transition(
                fd,
                authorization.authorization_id,
                record,
            )
    finally:
        monkeypatch.setattr(publisher.os, "close", original_close)
        original_close(fd)

    assert injected, "A falha de fecho nao foi injetada"



def test_successful_publication_with_directory_close_failure(
    tmp_path, monkeypatch
):
    """O fecho falhado nao pode ser apresentado como sucesso."""
    import pytest
    import f066c_authorization_transition_publisher as publisher

    directory = tmp_path / "authorizations"
    directory.mkdir(mode=0o700)

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

    record = AuthorizationTransitionRecord(
        schema_version=1,
        authorization_id=authorization.authorization_id,
        sequence=1,
        from_state="prepared",
        to_state="authorized",
        operation=authorization.operation,
        sql_sha256=authorization.sql_sha256,
        previous_hash=initial_authorization_hash(authorization),
        timestamp=TIMESTAMP,
        operator_id="test-operator",
        reason="Teste de falha de fecho apos publicacao",
        approval_evidence=ApprovalEvidence(
            operator_uid=os.getuid(),
            approval_method="local_interactive",
            approval_timestamp=TIMESTAMP,
            presented_hash="c" * 64,
        ),
    )

    fd = os.open(
        directory,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
    )

    original_close = os.close
    injected = []

    def failing_close(target_fd):
        history_directory = (
            directory
            / "transitions"
            / str(authorization.authorization_id)
        )

        target_info = os.fstat(target_fd)

        if history_directory.is_dir():
            history_info = history_directory.stat()

            if (
                not injected
                and target_info.st_dev == history_info.st_dev
                and target_info.st_ino == history_info.st_ino
            ):
                injected.append(True)
                original_close(target_fd)
                raise OSError(
                    "Falha simulada no fecho apos publicacao"
                )

        return original_close(target_fd)

    monkeypatch.setattr(publisher.os, "close", failing_close)

    try:
        from f066c_authorization_file_store import (
            AuthorizationPublicationUncertain,
        )

        with pytest.raises(
            AuthorizationPublicationUncertain
        ) as captured:
            publisher.publish_authorization_transition(
                fd,
                authorization.authorization_id,
                record,
            )

        assert isinstance(captured.value.__cause__, OSError)
        assert (
            "Falha simulada no fecho apos publicacao"
            in str(captured.value.__cause__)
        )
    finally:
        monkeypatch.setattr(publisher.os, "close", original_close)
        original_close(fd)

    assert injected, "A falha de fecho nao foi injetada"

    history_directory = (
        directory
        / "transitions"
        / str(authorization.authorization_id)
    )

    assert (
        history_directory / "000001-authorized.json"
    ).is_file()

    verify_fd = os.open(
        directory,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
    )

    try:
        history = read_authorization_history(
            verify_fd,
            authorization.authorization_id,
        )

        assert history.state == "authorized"
        assert history.transition_count == 1
        assert history.next_sequence == 2
    finally:
        os.close(verify_fd)



def test_successful_publication_with_unlock_failure_is_uncertain(
    tmp_path, monkeypatch
):
    """Uma falha de unlock apos publicacao exige resultado incerto."""
    import fcntl
    import pytest

    import f066c_authorization_lock as lock_module
    from f066c_authorization_file_store import (
        AuthorizationPublicationUncertain,
    )
    from f066c_authorization_transition_publisher import (
        publish_authorization_transition,
    )

    directory = tmp_path / "authorizations"
    directory.mkdir(mode=0o700)

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

    record = AuthorizationTransitionRecord(
        schema_version=1,
        authorization_id=authorization.authorization_id,
        sequence=1,
        from_state="prepared",
        to_state="authorized",
        operation=authorization.operation,
        sql_sha256=authorization.sql_sha256,
        previous_hash=initial_authorization_hash(authorization),
        timestamp=TIMESTAMP,
        operator_id="test-operator",
        reason="Teste de falha de desbloqueio",
        approval_evidence=ApprovalEvidence(
            operator_uid=os.getuid(),
            approval_method="local_interactive",
            approval_timestamp=TIMESTAMP,
            presented_hash="c" * 64,
        ),
    )

    original_flock = fcntl.flock
    injected = []

    def fail_unlock(lock_fd, operation):
        if operation == fcntl.LOCK_UN and not injected:
            injected.append(True)
            # Libertar realmente o bloqueio antes de simular o erro.
            original_flock(lock_fd, operation)
            raise OSError("Falha simulada no desbloqueio")

        return original_flock(lock_fd, operation)

    monkeypatch.setattr(
        lock_module.fcntl,
        "flock",
        fail_unlock,
    )

    fd = os.open(
        directory,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
    )

    try:
        with pytest.raises(
            AuthorizationPublicationUncertain
        ) as captured:
            publish_authorization_transition(
                fd,
                authorization.authorization_id,
                record,
            )

        assert injected
        assert isinstance(captured.value.__cause__, OSError)
        assert (
            "Falha simulada no desbloqueio"
            in str(captured.value.__cause__)
        )

        expected = (
            directory
            / "transitions"
            / str(authorization.authorization_id)
            / "000001-authorized.json"
        )
        assert expected.is_file()

    finally:
        os.close(fd)



def test_directory_creation_fsync_failure_prevents_publication(
    tmp_path, monkeypatch
):
    """Falha de fsync na criacao impede publicar a transicao."""
    import pytest
    import f066c_secure_directory as secure_directory

    from f066c_authorization_transition_publisher import (
        publish_authorization_transition,
    )
    from f066c_authorization_history_reader import (
        read_authorization_history,
    )

    directory = tmp_path / "authorizations"
    directory.mkdir(mode=0o700)

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

    record = AuthorizationTransitionRecord(
        schema_version=1,
        authorization_id=authorization.authorization_id,
        sequence=1,
        from_state="prepared",
        to_state="authorized",
        operation=authorization.operation,
        sql_sha256=authorization.sql_sha256,
        previous_hash=initial_authorization_hash(authorization),
        timestamp=TIMESTAMP,
        operator_id="test-operator",
        reason="Teste de falha de fsync na criacao de diretorio",
        approval_evidence=ApprovalEvidence(
            operator_uid=os.getuid(),
            approval_method="local_interactive",
            approval_timestamp=TIMESTAMP,
            presented_hash="c" * 64,
        ),
    )

    fd = os.open(
        directory,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
    )

    original_fsync = os.fsync
    injected = []

    def fail_initial_directory_fsync(target_fd):
        info = os.fstat(target_fd)
        parent_info = directory.stat()

        if (
            not injected
            and info.st_dev == parent_info.st_dev
            and info.st_ino == parent_info.st_ino
            and (directory / "transitions").is_dir()
        ):
            injected.append(True)
            raise OSError(
                "Falha simulada no fsync de criacao de diretorio"
            )

        return original_fsync(target_fd)

    try:
        # Criar antecipadamente o lock para que o seu fsync
        # nao interfira com a falha que pretendemos testar.
        from f066c_authorization_lock import (
            acquire_authorization_lock,
        )

        with acquire_authorization_lock(fd):
            pass

        monkeypatch.setattr(
            secure_directory.os,
            "fsync",
            fail_initial_directory_fsync,
        )

        with pytest.raises(
            OSError,
            match="Falha simulada no fsync de criacao de diretorio",
        ):
            publish_authorization_transition(
                fd,
                authorization.authorization_id,
                record,
            )

        assert injected

    finally:
        monkeypatch.setattr(
            secure_directory.os,
            "fsync",
            original_fsync,
        )

    try:
        expected = (
            directory
            / "transitions"
            / str(authorization.authorization_id)
            / "000001-authorized.json"
        )

        assert not expected.exists()

        history = read_authorization_history(
            fd,
            authorization.authorization_id,
        )

        assert history.state == "prepared"
        assert history.transition_count == 0
        assert history.next_sequence == 1

    finally:
        os.close(fd)



def test_successful_publication_with_lock_close_failure_is_uncertain(
    tmp_path, monkeypatch
):
    """Falha no fecho do lock apos publicacao exige incerteza."""
    import pytest

    import f066c_authorization_lock as lock_module
    from f066c_authorization_file_store import (
        AuthorizationPublicationUncertain,
    )
    from f066c_authorization_transition_publisher import (
        publish_authorization_transition,
    )

    directory = tmp_path / "authorizations"
    directory.mkdir(mode=0o700)

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

    record = AuthorizationTransitionRecord(
        schema_version=1,
        authorization_id=authorization.authorization_id,
        sequence=1,
        from_state="prepared",
        to_state="authorized",
        operation=authorization.operation,
        sql_sha256=authorization.sql_sha256,
        previous_hash=initial_authorization_hash(authorization),
        timestamp=TIMESTAMP,
        operator_id="test-operator",
        reason="Teste de falha no fecho do bloqueio",
        approval_evidence=ApprovalEvidence(
            operator_uid=os.getuid(),
            approval_method="local_interactive",
            approval_timestamp=TIMESTAMP,
            presented_hash="c" * 64,
        ),
    )

    fd = os.open(
        directory,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
    )

    # Criar o bloqueio antes de injetar a falha.
    with lock_module.acquire_authorization_lock(fd):
        pass

    lock_info = (directory / ".authorization.lock").stat()
    original_close = os.close
    injected = []

    def fail_lock_close(target_fd):
        info = os.fstat(target_fd)

        if (
            not injected
            and info.st_dev == lock_info.st_dev
            and info.st_ino == lock_info.st_ino
        ):
            injected.append(True)
            original_close(target_fd)
            raise OSError(
                "Falha simulada no fecho do bloqueio"
            )

        return original_close(target_fd)

    monkeypatch.setattr(
        lock_module.os,
        "close",
        fail_lock_close,
    )

    try:
        with pytest.raises(
            AuthorizationPublicationUncertain
        ) as captured:
            publish_authorization_transition(
                fd,
                authorization.authorization_id,
                record,
            )

        assert injected
        assert isinstance(captured.value.__cause__, OSError)
        assert (
            "Falha simulada no fecho do bloqueio"
            in str(captured.value.__cause__)
        )

    finally:
        monkeypatch.setattr(
            lock_module.os,
            "close",
            original_close,
        )

    try:
        expected = (
            directory
            / "transitions"
            / str(authorization.authorization_id)
            / "000001-authorized.json"
        )

        assert expected.is_file()

    finally:
        os.close(fd)
