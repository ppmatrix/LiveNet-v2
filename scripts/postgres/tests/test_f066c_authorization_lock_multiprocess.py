"""Teste de exclusao mutua AUTH-03 entre processos independentes."""

import multiprocessing
import os
import queue

from f066c_authorization_lock import acquire_authorization_lock


def _lock_worker(directory, commands, events):
    fd = os.open(
        directory,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
    )

    try:
        events.put("ready")

        if commands.get(timeout=10) != "acquire":
            raise RuntimeError("Comando inicial inesperado")

        with acquire_authorization_lock(fd):
            events.put("acquired")

            if commands.get(timeout=10) != "release":
                raise RuntimeError("Comando de libertacao inesperado")

        events.put("released")
    except BaseException as exc:
        events.put(("error", repr(exc)))
        raise
    finally:
        os.close(fd)


def test_lock_exclusion_between_processes(tmp_path):
    directory = tmp_path / "authorizations"
    directory.mkdir(mode=0o700)

    ctx = multiprocessing.get_context("spawn")

    commands_a = ctx.Queue()
    events_a = ctx.Queue()
    commands_b = ctx.Queue()
    events_b = ctx.Queue()

    process_a = ctx.Process(
        target=_lock_worker,
        args=(str(directory), commands_a, events_a),
    )
    process_b = ctx.Process(
        target=_lock_worker,
        args=(str(directory), commands_b, events_b),
    )

    process_a.start()
    process_b.start()

    try:
        assert events_a.get(timeout=10) == "ready"
        assert events_b.get(timeout=10) == "ready"

        commands_a.put("acquire")
        assert events_a.get(timeout=10) == "acquired"

        commands_b.put("acquire")

        # Enquanto A mantem o bloqueio, B nao pode adquiri-lo.
        try:
            premature = events_b.get(timeout=0.5)
        except queue.Empty:
            premature = None

        assert premature is None, (
            f"Segundo processo adquiriu prematuramente: {premature}"
        )

        commands_a.put("release")
        assert events_a.get(timeout=10) == "released"

        assert events_b.get(timeout=10) == "acquired"

        commands_b.put("release")
        assert events_b.get(timeout=10) == "released"

    finally:
        # Permitir primeiro a terminacao normal dos processos.
        for process in (process_a, process_b):
            process.join(timeout=10)

        # Terminar apenas processos que permaneceram bloqueados.
        for process in (process_a, process_b):
            if process.is_alive():
                process.terminate()
                process.join(timeout=10)

        for communication in (
            commands_a, events_a, commands_b, events_b
        ):
            communication.close()
            communication.join_thread()

    assert process_a.exitcode == 0
    assert process_b.exitcode == 0
