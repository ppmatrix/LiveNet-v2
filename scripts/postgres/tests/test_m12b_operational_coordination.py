"""IMP1 fault matrix. Every adapter is a concrete in-memory fake."""

from dataclasses import replace
from unittest.mock import Mock

import pytest

import m12b_security_migration as existing_executor
from m12b_security_adapters import (
    AdministrativeCloser, BOOTSTRAP, CommitUncertain, ContractViolation,
    ExclusivityController, InspectorAdapter, MemoryScenario, MigratorAdapter,
    PostCommitVerifier, RecoveryVerifier,
)
from m12b_security_coordinator import CoordinationFailed, MigrationCoordinator, ORDER, State


def setup():
    world = MemoryScenario("b" * 64, clock=Mock(return_value=100.0))
    coordinator = MigrationCoordinator(inspector=InspectorAdapter(world), migrator=MigratorAdapter(world),
        verifier=PostCommitVerifier(world), closer=AdministrativeCloser(world),
        exclusivity=ExclusivityController(world), recovery=RecoveryVerifier(world))
    return world, coordinator


def test_complete_flow_retains_lock_until_administrative_closure():
    world, coordinator = setup()
    result = coordinator.simulate()
    assert result.state is State.CLOSED and result.history == ORDER
    assert result.simulated and not result.app_ready
    assert world.owner == "livenet_m12b_security_owner"
    assert world.create_revoked and world.memberships_revoked
    assert not world.exclusive and not world.lock_held
    assert all(s.physical in world.closed for s in world.sessions)
    steps = world.events
    assert steps.index("migration_commit") < steps.index("postcommit") < steps.index("ownership")
    assert steps.index("revocation") < steps.index("final_verify") < steps.index("primary_unlock")
    assert steps.index("primary_unlock") < steps.index("release_window")
    assert len({s.physical for s in world.sessions}) == len(world.sessions) == 5


@pytest.mark.parametrize("phase,expected", [
    ("recovery", State.BLOCKED), ("exclusivity", State.BLOCKED), ("inspect", State.BLOCKED),
    ("migration_begin", State.BLOCKED), ("handoff_accept", State.ROLLED_BACK),
    ("migration_work", State.ROLLED_BACK), ("migration_commit", State.RECONCILE_REQUIRED),
    ("postcommit", State.RECONCILE_REQUIRED), ("ownership", State.RECONCILE_REQUIRED),
    ("revocation", State.RECONCILE_REQUIRED), ("administrative_commit", State.RECONCILE_REQUIRED),
    ("final_verify", State.RECONCILE_REQUIRED), ("primary_unlock", State.RECONCILE_REQUIRED),
    ("release_window", State.RECONCILE_REQUIRED),
])
def test_failures_at_each_phase_are_sanitized_and_never_closed(phase, expected):
    world, coordinator = setup()
    world.failures[phase] = RuntimeError("sensitive driver text must stay hidden")
    with pytest.raises(CoordinationFailed) as caught:
        coordinator.simulate()
    assert caught.value.state is expected
    assert coordinator.state is expected and State.CLOSED not in coordinator.history
    assert "sensitive" not in str(caught.value) and caught.value.__suppress_context__
    assert world.events.count("migration_work") <= 1
    with pytest.raises(ContractViolation):
        coordinator.simulate()
    if phase not in ("recovery", "exclusivity"):
        assert world.exclusive


@pytest.mark.parametrize("state", ORDER[1:])
def test_failure_at_every_state_boundary_cannot_skip_to_closed(state):
    world, coordinator = setup()
    world.failures["state:" + state.value] = RuntimeError("boundary fault")
    with pytest.raises(CoordinationFailed):
        coordinator.simulate()
    assert coordinator.state is not State.CLOSED
    assert "release_window" not in world.events


def test_commit_uncertain_blocks_ownership_and_retry():
    world, coordinator = setup()
    world.failures["migration_commit"] = CommitUncertain("simulated lost acknowledgement")
    with pytest.raises(CoordinationFailed) as caught:
        coordinator.simulate()
    assert caught.value.state is State.RECONCILE_REQUIRED
    assert "ownership" not in world.events and "migration_rollback" not in world.events
    assert world.exclusive


def test_rollback_failure_requires_reconciliation():
    world, coordinator = setup()
    world.failures.update(migration_work=RuntimeError(), migration_rollback=RuntimeError())
    with pytest.raises(CoordinationFailed) as caught:
        coordinator.simulate()
    assert caught.value.state is State.RECONCILE_REQUIRED


@pytest.mark.parametrize("step", ["close:livenet_m12b_migrator", "close:livenet_m12b_bootstrap",
                                  "close:livenet_m12b_inspector"])
def test_resource_close_failure_never_releases_window(step):
    world, coordinator = setup()
    world.failures[step] = RuntimeError("close failed")
    with pytest.raises(CoordinationFailed) as caught:
        coordinator.simulate()
    assert caught.value.state is State.RECONCILE_REQUIRED
    assert world.exclusive and "release_window" not in world.events


@pytest.mark.parametrize("step,value", [("handoff_fingerprint", "c" * 64),
                                        ("primary_lock", False), ("transaction_lock", False)])
def test_fingerprint_and_lock_loss_block_before_commit(step, value):
    world, coordinator = setup()
    world.overrides[step] = value
    with pytest.raises(CoordinationFailed):
        coordinator.simulate()
    assert "migration_work" not in world.events
    assert not world.committed and coordinator.state is not State.CLOSED


@pytest.mark.parametrize("at", [State.HANDOFF_ACCEPTED, State.MIGRATION_COMMITTED,
                               State.POSTCOMMIT_VERIFIED, State.OWNERSHIP_TRANSFERRED,
                               State.TEMP_PRIVILEGES_REVOKED, State.FINAL_VERIFIED])
def test_exclusivity_loss_is_checked_throughout_cycle(at):
    world, coordinator = setup()
    original = world.step

    def step(name, result=None):
        answer = original(name, result)
        if name == "state:" + at.value:
            world.overrides["exclusive_continuity"] = False
        return answer

    world.step = step
    with pytest.raises(CoordinationFailed):
        coordinator.simulate()
    assert world.exclusive and "release_window" not in world.events
    assert coordinator.state is not State.CLOSED


def test_lost_primary_lock_during_postcommit_prevents_ownership():
    world, coordinator = setup()
    original = world.step

    def step(name, result=None):
        if name == "postcommit":
            world.lock_held = False
        return original(name, result)

    world.step = step
    with pytest.raises(CoordinationFailed) as caught:
        coordinator.simulate()
    assert caught.value.state is State.RECONCILE_REQUIRED
    assert "ownership" not in world.events and world.exclusive


@pytest.mark.parametrize("fault", ["fingerprint", "transaction_lock"])
def test_precommit_reinspection_or_lock_loss_prevents_commit(fault):
    world, coordinator = setup()
    original = world.step

    def step(name, result=None):
        if name == "migration_work":
            if fault == "fingerprint":
                world.fingerprint = "c" * 64
            else:
                world.transaction_lock_held = False
        return original(name, result)

    world.step = step
    with pytest.raises(CoordinationFailed) as caught:
        coordinator.simulate()
    assert caught.value.state is State.ROLLED_BACK
    assert "migration_commit" not in world.events and not world.committed


def test_bootstrap_cannot_replace_migrator():
    world, coordinator = setup()
    original = world.step

    def step(name, result=None):
        if name == "migration_identity":
            return replace(result, role=BOOTSTRAP)
        return original(name, result)

    world.step = step
    with pytest.raises(CoordinationFailed):
        coordinator.simulate()
    assert "migration_work" not in world.events


@pytest.mark.parametrize("fault", ["durability", "final_acl", "final_owner", "app_dml", "closure", "final_fingerprint"])
def test_forged_or_incomplete_postcommit_evidence_is_rejected(fault):
    world, coordinator = setup()
    original = world.step

    def step(name, result=None):
        if name == "durability" and fault == "durability":
            return replace(result, session=result.committed_session)
        if name == "closure" and fault == "closure":
            return replace(result, create_revoked=False)
        if name == "final":
            fields = {"final_acl": {"acl_valid": False}, "final_owner": {"owner": BOOTSTRAP},
                      "app_dml": {"app_dml_enabled": True}, "final_fingerprint": {"fingerprint": "c" * 64}}
            if fault in fields:
                return replace(result, **fields[fault])
        return original(name, result)

    world.step = step
    with pytest.raises(CoordinationFailed) as caught:
        coordinator.simulate()
    assert caught.value.state is State.RECONCILE_REQUIRED
    assert "release_window" not in world.events


def test_recovery_unavailable_prevents_even_opening_inspector():
    world, coordinator = setup()
    world.overrides["recovery_proof"] = None
    with pytest.raises(CoordinationFailed) as caught:
        coordinator.simulate()
    assert caught.value.state is State.BLOCKED
    assert world.sessions == [] and not world.exclusive


@pytest.mark.parametrize("field,value", [("application_revision", "f067a01a7230"),
    ("security_revision", "b12b01a7230"), ("authorization_present", True),
    ("unexpected_objects", True)])
def test_unexpected_observed_initial_state_blocks_every_adapter(field, value):
    world, coordinator = setup()
    world.overrides["precheck"] = replace(world.precheck(), **{field: value})
    with pytest.raises(CoordinationFailed) as caught:
        coordinator.simulate()
    assert caught.value.state is State.BLOCKED
    assert world.sessions == [] and "recovery" not in world.events


def test_premature_commit_is_not_reported_as_rollback():
    world, coordinator = setup()
    original = world.step

    def step(name, result=None):
        if name == "migration_work":
            world.committed = True
            world.transaction = False
            raise RuntimeError("adapter committed early")
        return original(name, result)

    world.step = step
    with pytest.raises(CoordinationFailed) as caught:
        coordinator.simulate()
    assert caught.value.state is State.RECONCILE_REQUIRED
    assert "migration_rollback" not in world.events


@pytest.mark.parametrize("phase", ["migration_identity", "precommit"])
def test_unexpected_transaction_end_without_commit_ack_requires_reconciliation(phase):
    world, coordinator = setup()
    original = world.step

    def step(name, result=None):
        if name == phase:
            world.transaction = False
        return original(name, result)

    world.step = step
    with pytest.raises(CoordinationFailed) as caught:
        coordinator.simulate()
    assert caught.value.state is State.RECONCILE_REQUIRED
    assert "migration_rollback" not in world.events and "ownership" not in world.events


def test_closed_transition_requires_every_preceding_phase():
    _, coordinator = setup()
    with pytest.raises(ContractViolation):
        coordinator._advance(State.CLOSED)
    assert coordinator.state is State.PRECHECK


def test_even_sequential_transitions_cannot_fake_a_complete_closure():
    _, coordinator = setup()
    for state in ORDER[1:-1]:
        coordinator._advance(state)
    with pytest.raises(ContractViolation):
        coordinator._advance(State.CLOSED)


@pytest.mark.parametrize("phase,elapsed", [("migration_begin", 5.001), ("postcommit", 31.0)])
def test_expiration_blocks_handoff_or_postcommit_closure(phase, elapsed):
    world, coordinator = setup()
    original = world.step

    def step(name, result=None):
        if name == phase:
            world.clock.return_value += elapsed
        return original(name, result)

    world.step = step
    with pytest.raises(CoordinationFailed):
        coordinator.simulate()
    if phase == "migration_begin":
        assert "migration_work" not in world.events
        assert coordinator.state is State.ROLLED_BACK
    else:
        assert coordinator.state is State.RECONCILE_REQUIRED
        assert "ownership" not in world.events


def test_lost_external_barrier_is_not_hidden_by_a_still_valid_proof():
    world, coordinator = setup()
    original = world.step

    def step(name, result=None):
        if name == "migration_begin":
            world.exclusive = False
        return original(name, result)

    world.step = step
    with pytest.raises(CoordinationFailed):
        coordinator.simulate()
    assert "migration_work" not in world.events


def test_administrative_commit_uncertainty_does_not_claim_rollback():
    world, coordinator = setup()
    world.failures["administrative_commit"] = CommitUncertain("lost acknowledgement")
    with pytest.raises(CoordinationFailed) as caught:
        coordinator.simulate()
    assert caught.value.state is State.RECONCILE_REQUIRED
    assert "administrative_rollback" not in world.events
    assert "final_verify" not in world.events and world.exclusive


def test_ownership_staging_rolls_back_if_revocation_fails_before_admin_commit():
    world, coordinator = setup()
    world.failures["revocation"] = RuntimeError()
    with pytest.raises(CoordinationFailed):
        coordinator.simulate()
    assert "administrative_rollback" in world.events
    assert world.owner == "livenet_m12b_migrator" and not world.create_revoked


def test_inspector_identity_is_not_replaceable_by_bootstrap():
    world, coordinator = setup()
    original = world.step

    def step(name, result=None):
        if name == "inspection":
            return replace(result, session=replace(result.session, role=BOOTSTRAP))
        return original(name, result)

    world.step = step
    with pytest.raises(CoordinationFailed):
        coordinator.simulate()
    assert "migration_begin" not in world.events


def test_simulation_does_not_create_an_operational_entry_point(monkeypatch):
    world, coordinator = setup()
    # Even a deliberately replaced gate in this test cannot make IMP1 execute I/O.
    monkeypatch.setattr(existing_executor, 'require_execution_authorization', Mock())
    with pytest.raises(ContractViolation, match="apenas simulacao"):
        coordinator.execute(None)
    assert world.events == []


def test_different_world_or_arbitrary_adapter_is_not_accepted():
    world, coordinator = setup()
    parts = dict(inspector=coordinator.inspector, migrator=coordinator.migrator,
        verifier=coordinator.verifier, closer=coordinator.closer,
        exclusivity=coordinator.exclusivity, recovery=coordinator.recovery)
    for replacement in (Mock(), MigratorAdapter(MemoryScenario("c" * 64))):
        with pytest.raises(ContractViolation):
            MigrationCoordinator(**{**parts, "migrator": replacement})
    assert world.events == []


def test_execution_enabled_false_blocks_before_any_adapter_or_proof():
    world, coordinator = setup()
    assert existing_executor.AUTHORIZATION.execution_enabled is False
    with pytest.raises(existing_executor.Refused, match="bloqueada"):
        coordinator.execute(None)
    assert world.events == [] and coordinator.state is State.PRECHECK


def new_coordinator(world):
    return MigrationCoordinator(inspector=InspectorAdapter(world), migrator=MigratorAdapter(world),
        verifier=PostCommitVerifier(world), closer=AdministrativeCloser(world),
        exclusivity=ExclusivityController(world), recovery=RecoveryVerifier(world))


def test_fix1_shared_registry_terminal_success_blocks_new_coordinator_and_old_evidence():
    from m12b_security_adapters import OperationStatus
    world, first = setup()
    first.simulate()
    assert world.registry.lookup(world.binding).status is OperationStatus.CLOSED
    world.overrides["handoff_issue"] = first.inspector._issued
    events = tuple(world.events)
    with pytest.raises(CoordinationFailed) as caught:
        new_coordinator(world).simulate()
    assert caught.value.state is State.BLOCKED
    assert tuple(world.events) == events


def test_fix1_uncertain_operation_requires_explicit_reconciliation_and_never_reopens():
    from m12b_security_adapters import OperationStatus, Reconciliation
    world, first = setup()
    world.failures["migration_commit"] = CommitUncertain("lost ack")
    with pytest.raises(CoordinationFailed):
        first.simulate()
    assert world.registry.lookup(world.binding).status is OperationStatus.RECONCILE_REQUIRED
    world.failures.clear()
    with pytest.raises(CoordinationFailed) as caught:
        new_coordinator(world).simulate()
    assert caught.value.state is State.RECONCILE_REQUIRED
    world.registry.reconcile(Reconciliation(world.binding, "simulated-independent-assessment", "confirmed_not_committed"))
    assert world.registry.lookup(world.binding).status is OperationStatus.RECONCILED
    with pytest.raises(CoordinationFailed) as caught:
        new_coordinator(world).simulate()
    assert caught.value.state is State.BLOCKED
    assert world.events.count("migration_commit") == 1


def test_fix1_genuinely_new_operation_can_share_the_registry():
    from m12b_security_adapters import OperationStatus
    world, first = setup()
    first.simulate()
    other = MemoryScenario("b" * 64, clock=world.clock, registry=world.registry)
    assert other.binding.operation is not world.binding.operation
    assert new_coordinator(other).simulate().state is State.CLOSED
    assert world.registry.lookup(world.binding).status is OperationStatus.CLOSED
    assert world.registry.lookup(other.binding).status is OperationStatus.CLOSED


def test_fix1_old_evidence_is_rejected_even_for_a_registered_new_operation():
    world, first = setup()
    first.simulate()
    other = MemoryScenario("b" * 64, clock=world.clock, registry=world.registry)
    other.overrides["handoff_issue"] = first.inspector._issued
    with pytest.raises(CoordinationFailed):
        new_coordinator(other).simulate()
    assert "migration_commit" not in other.events


@pytest.mark.parametrize("failure", ["empty_replacement", "missing_record", "unavailable", "lookup_exception"])
def test_fix1_missing_or_unreadable_registry_is_never_permission_to_retry(monkeypatch, failure):
    from m12b_security_adapters import OperationRegistry
    world, first = setup()
    first.simulate()
    events = tuple(world.events)
    if failure == "empty_replacement":
        world.registry = OperationRegistry()
    elif failure == "missing_record":
        world.registry._records.clear()
    elif failure == "unavailable":
        world.registry.available = False
    else:
        monkeypatch.setattr(world.registry, "lookup", Mock(side_effect=RuntimeError("synthetic-sensitive-registry")))
    with pytest.raises(CoordinationFailed) as caught:
        new_coordinator(world).simulate()
    assert caught.value.state is State.RECONCILE_REQUIRED
    assert tuple(world.events) == events
    assert "synthetic-sensitive" not in str(caught.value)


def test_fix1_claim_is_exclusive_and_not_reusable_between_coordinators():
    from m12b_security_adapters import OperationStatus
    world, first = setup()
    world.registry.claim(world.binding)
    with pytest.raises(CoordinationFailed) as caught:
        first.simulate()
    assert caught.value.state is State.RECONCILE_REQUIRED
    assert world.registry.lookup(world.binding).status is OperationStatus.RUNNING
    assert world.events == []


def test_fix1_registry_finalization_failure_cannot_declare_closed(monkeypatch):
    world, instance = setup()
    monkeypatch.setattr(world.registry, "finish", Mock(side_effect=RuntimeError("synthetic-sensitive-finish")))
    with pytest.raises(CoordinationFailed) as caught:
        instance.simulate()
    assert caught.value.state is State.RECONCILE_REQUIRED
    assert State.CLOSED not in instance.history
    assert any(i.operation == "operation_registry.finish" for i in caught.value.cleanup_failures)


def test_fix1_workflow_error_is_preserved_when_multiple_cleanup_actions_fail():
    world, instance = setup()
    primary = RuntimeError("synthetic-sensitive-workflow")
    world.failures.update(migration_work=primary, migration_rollback=ValueError("synthetic-sensitive-rollback"),
                          primary_unlock=RuntimeError("synthetic-sensitive-unlock"),
                          **{"close:livenet_m12b_inspector": RuntimeError("synthetic-sensitive-close")})
    with pytest.raises(CoordinationFailed) as caught:
        instance.simulate()
    error = caught.value
    assert error.original_error is primary and error.state is State.RECONCILE_REQUIRED
    assert {i.operation for i in error.cleanup_failures} == {
        "migration.rollback", "inspector.unlock", "inspector.close"}
    assert "synthetic-sensitive" not in str(error) + repr(error) + repr(error.cleanup_failures)
    assert world.events.count("primary_unlock") == 1
    assert world.events.count("close:livenet_m12b_inspector") == 1
    assert world.exclusive


@pytest.mark.parametrize("phase", ["migration_commit", "revocation", "administrative_commit"])
def test_fix1_cleanup_after_uncertain_commit_or_administrative_failure(phase):
    world, instance = setup()
    primary = CommitUncertain("synthetic-sensitive") if "commit" in phase else RuntimeError("synthetic-sensitive")
    world.failures[phase] = primary
    with pytest.raises(CoordinationFailed) as caught:
        instance.simulate()
    assert caught.value.original_error is primary
    assert caught.value.state is State.RECONCILE_REQUIRED
    assert all(s.physical in world.closed for s in world.sessions)
    assert world.exclusive and "release_window" not in world.events


def test_fix1_multiple_administrative_close_failures_are_attempted_independently(monkeypatch):
    world, instance = setup()
    close = world.close
    attempts = []

    def fail_admin_close(session):
        if session is not None and session.role == BOOTSTRAP:
            attempts.append(session.physical)
            raise RuntimeError("synthetic-sensitive-administrative")
        return close(session)

    monkeypatch.setattr(world, "close", fail_admin_close)
    with pytest.raises(CoordinationFailed) as caught:
        instance.simulate()
    assert attempts == [instance.closer.final_session.physical, instance.closer.session.physical]
    assert {i.operation for i in caught.value.cleanup_failures} == {
        "administrative.final_close", "administrative.close"}
    assert instance.inspector.session.physical in world.closed and world.exclusive


def test_fix1_second_migrator_role_close_failure_does_not_duplicate_attempts(monkeypatch):
    world, instance = setup()
    step = world.step
    attempts = []

    def fail_second_close(name, result=None):
        if name == "close:livenet_m12b_migrator":
            attempts.append(name)
            if len(attempts) == 2:
                raise RuntimeError("postcommit verifier close failure")
        return step(name, result)

    monkeypatch.setattr(world, "step", fail_second_close)
    with pytest.raises(CoordinationFailed) as caught:
        instance.simulate()
    assert caught.value.state is State.RECONCILE_REQUIRED
    assert len(attempts) == 2  # One migration session, one distinct verifier; no third attempt.
    assert instance.inspector.session.physical in world.closed and world.exclusive


def test_fix1_unconfirmed_window_release_is_never_closed():
    world, instance = setup()
    world.failures["release_receipt"] = RuntimeError("synthetic missing release acknowledgement")
    with pytest.raises(CoordinationFailed) as caught:
        instance.simulate()
    assert caught.value.state is State.RECONCILE_REQUIRED
    assert State.CLOSED not in instance.history


def test_fix1_untyped_empty_storage_cannot_authorize_a_simulation():
    world, _ = setup()
    world.registry = Mock()
    with pytest.raises(ContractViolation):
        new_coordinator(world)
    assert world.events == []


def test_fix1_replacing_storage_after_coordinator_creation_requires_reconciliation():
    from m12b_security_adapters import OperationRegistry
    world, instance = setup()
    world.registry = OperationRegistry()
    with pytest.raises(CoordinationFailed) as caught:
        instance.simulate()
    assert caught.value.state is State.RECONCILE_REQUIRED and world.events == []


def test_fix1_storage_identity_is_retained_during_the_operation(monkeypatch):
    from m12b_security_adapters import OperationRegistry, OperationStatus
    world, instance = setup()
    registry = world.registry
    step = world.step

    def switch_registry(name, result=None):
        if name == "migration_work":
            world.registry = OperationRegistry()
        return step(name, result)

    monkeypatch.setattr(world, "step", switch_registry)
    with pytest.raises(CoordinationFailed) as caught:
        instance.simulate()
    assert caught.value.state is State.RECONCILE_REQUIRED
    assert "migration_commit" not in world.events
    assert registry.lookup(world.binding).status is OperationStatus.RECONCILE_REQUIRED
