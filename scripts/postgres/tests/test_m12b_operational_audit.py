"""VAL1 independent safety assertions. Known defects intentionally FAIL.

No fixes, xfail, PostgreSQL, Docker or migration operation. The failure output
is evidence for the audit report, not a request to repair IMP1 in this phase.
"""

import ast
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock

import pytest

import m12b_security_migration as existing_executor
from m12b_security_adapters import (
    AdministrativeCloser, Binding, CommitUncertain, ContractViolation,
    ExclusivityController, InspectorAdapter, MemoryScenario, MigratorAdapter,
    PostCommitVerifier, RecoveryVerifier,
)
from m12b_security_coordinator import CoordinationFailed, MigrationCoordinator, State


def scenario():
    return MemoryScenario("b" * 64, clock=Mock(return_value=100.0))


def coordinator(world):
    return MigrationCoordinator(inspector=InspectorAdapter(world), migrator=MigratorAdapter(world),
        verifier=PostCommitVerifier(world), closer=AdministrativeCloser(world),
        exclusivity=ExclusivityController(world), recovery=RecoveryVerifier(world))


def test_control_success_is_explicitly_synthetic_and_single_instance_use():
    world = scenario()
    instance = coordinator(world)
    result = instance.simulate()
    assert result.state is State.CLOSED and result.simulated and not result.app_ready
    assert all(s.physical in world.closed for s in world.sessions)
    with pytest.raises(ContractViolation):
        instance.simulate()


@pytest.mark.parametrize("first_outcome", ["success", "uncertain_commit"])
def test_val1_a01_same_operation_cannot_be_retried_with_new_coordinator(first_outcome):
    world = scenario()
    operation = world.binding.operation
    if first_outcome == "success":
        coordinator(world).simulate()
    else:
        world.failures["migration_commit"] = CommitUncertain("synthetic acknowledgement loss")
        with pytest.raises(CoordinationFailed) as caught:
            coordinator(world).simulate()
        assert caught.value.state is State.RECONCILE_REQUIRED
        world.failures.clear()
    assert world.binding.operation is operation
    attempts = world.events.count("migration_commit")
    with pytest.raises((ContractViolation, CoordinationFailed)):
        coordinator(world).simulate()
    assert world.events.count("migration_commit") == attempts


@pytest.mark.parametrize("invalid", ["other_operation", "other_target", "other_digest", "expired"])
def test_val1_a02_issue_does_not_launder_inspection_binding_or_expiry(invalid):
    world = scenario()
    inspector = InspectorAdapter(world)
    observed = inspector.inspect()
    if invalid == "other_operation":
        observed = replace(observed, binding=scenario().binding)
    elif invalid == "other_target":
        wrong = replace(world.binding.target, database="livenet")
        observed = replace(observed, binding=Binding(wrong, object(), "b" * 64))
    elif invalid == "other_digest":
        observed = replace(observed, binding=replace(world.binding, plan_digest="c" * 64))
    else:
        world.clock.return_value = observed.expires_at + 1.0
    with pytest.raises(ContractViolation):
        inspector.consume(inspector.issue(observed))


def test_val1_a03_unlock_failure_still_attempts_physical_session_close():
    world = scenario()
    instance = coordinator(world)
    world.failures["primary_unlock"] = RuntimeError("synthetic unlock failure")
    with pytest.raises(CoordinationFailed) as caught:
        instance.simulate()
    assert caught.value.state is State.RECONCILE_REQUIRED
    assert world.exclusive
    assert instance.inspector.session.physical in world.closed


def test_val1_a03_final_close_failure_does_not_skip_admin_session_cleanup(monkeypatch):
    world = scenario()
    instance = coordinator(world)
    close = world.close

    def failing_final_close(session):
        if session is not None and session is instance.closer.final_session:
            raise RuntimeError("synthetic failure of final verifier close only")
        return close(session)

    monkeypatch.setattr(world, "close", failing_final_close)
    with pytest.raises(CoordinationFailed) as caught:
        instance.simulate()
    assert caught.value.state is State.RECONCILE_REQUIRED and world.exclusive
    assert instance.closer.session.physical in world.closed


@pytest.mark.parametrize("proof_kind", ["recovery", "closed_simulation"])
def test_synthetic_evidence_never_authorizes_existing_executor(proof_kind):
    world = scenario()
    proof = (RecoveryVerifier(world).verify() if proof_kind == "recovery"
             else coordinator(world).simulate())
    assert existing_executor.AUTHORIZATION.execution_enabled is False
    with pytest.raises(existing_executor.Refused):
        existing_executor.require_execution_authorization(proof)


def test_simulation_and_refused_execution_do_not_call_io_boundaries(monkeypatch):
    import socket
    import subprocess
    import psycopg
    import sqlalchemy
    import alembic.command

    forbidden = Mock(side_effect=AssertionError("I/O boundary must not be reached"))
    monkeypatch.setattr(psycopg, "connect", forbidden)
    monkeypatch.setattr(sqlalchemy, "create_engine", forbidden)
    monkeypatch.setattr(alembic.command, "upgrade", forbidden)
    monkeypatch.setattr(alembic.command, "downgrade", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    world = scenario()
    instance = coordinator(world)
    with pytest.raises(existing_executor.Refused):
        instance.execute(None)
    assert world.events == []
    assert instance.simulate().state is State.CLOSED
    forbidden.assert_not_called()


def test_fresh_simulation_contexts_have_different_operation_bindings():
    one, two = scenario(), scenario()
    assert one.binding.operation is not two.binding.operation
    assert coordinator(one).simulate().state is State.CLOSED
    assert coordinator(two).simulate().state is State.CLOSED


@pytest.mark.parametrize("filename", ["m12b_security_adapters.py", "m12b_security_coordinator.py"])
def test_no_operational_cli_or_direct_io_import_in_new_modules(filename):
    source = Path(__file__).resolve().parents[1] / filename
    tree = ast.parse(source.read_text())
    imports = {alias.name.split('.')[0] for node in ast.walk(tree) if isinstance(node, ast.Import)
               for alias in node.names}
    assert not imports & {"psycopg", "sqlalchemy", "alembic", "subprocess", "socket", "os"}
    assert not any(isinstance(n, ast.Name) and n.id == "__name__" for n in ast.walk(tree))
