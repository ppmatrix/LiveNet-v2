"""IMP1 contracts: pure in-memory fakes, no database or environment discovery."""

from dataclasses import replace
from unittest.mock import Mock

import pytest

from m12b_security_adapters import (
    AdministrativeCloser, Binding, ContractViolation, ExclusivityController,
    HANDOFF_TTL, InspectorAdapter, MemoryScenario, MigratorAdapter,
    PostCommitVerifier, RecoveryVerifier, Target,
)


@pytest.fixture
def world():
    return MemoryScenario("b" * 64, clock=Mock(return_value=100.0))


@pytest.mark.parametrize("field,value", [
    ("project", "livenetv2"), ("database", "livenet"), ("system_identifier", "1"),
    ("baseline", "f067a01a7230"), ("revision", "head"), ("host", "other"), ("port", 5433),
])
def test_wrong_environment_is_rejected_before_any_event(field, value):
    with pytest.raises(ContractViolation):
        MemoryScenario("b" * 64, target=replace(Target(), **{field: value}))


@pytest.mark.parametrize("adapter", [InspectorAdapter, MigratorAdapter, PostCommitVerifier,
                                     AdministrativeCloser, ExclusivityController, RecoveryVerifier])
def test_explicit_adapter_contract_and_construction_do_not_open_anything(world, adapter):
    instance = adapter(world)
    contract = instance.contract
    assert contract.role and contract.capabilities and contract.transaction and contract.lifecycle
    assert contract.statement_seconds > 0 and contract.lock_seconds > 0
    assert {"identity", "timeout", "state", "close"} <= set(contract.errors)
    assert world.events == world.sessions == []


def test_single_use_handoff_rejects_copy_replay_and_second_issue(world):
    inspector = InspectorAdapter(world)
    evidence = inspector.issue(inspector.inspect())
    with pytest.raises(ContractViolation):
        inspector.consume(replace(evidence))
    inspector.consume(evidence)
    with pytest.raises(ContractViolation):
        inspector.consume(evidence)
    with pytest.raises(ContractViolation):
        inspector.issue(inspector.inspect())


@pytest.mark.parametrize("elapsed,accepted", [(0, True), (5, True), (5.00001, False), (-0.1, False)])
def test_ttl_boundaries(world, elapsed, accepted):
    inspector = InspectorAdapter(world)
    evidence = inspector.issue(inspector.inspect())
    assert evidence.expires_at - evidence.issued_at == HANDOFF_TTL
    world.clock.return_value += elapsed
    if accepted:
        inspector.consume(evidence)
    else:
        with pytest.raises(ContractViolation):
            inspector.consume(evidence)


def test_failed_consumption_is_also_single_use(world):
    inspector = InspectorAdapter(world)
    evidence = inspector.issue(inspector.inspect())
    world.overrides["handoff_fingerprint"] = "c" * 64
    with pytest.raises(ContractViolation):
        inspector.consume(evidence)
    world.overrides.clear()
    with pytest.raises(ContractViolation):
        inspector.consume(evidence)


def test_slow_reinspection_expires_before_acceptance(world):
    inspector = InspectorAdapter(world)
    evidence = inspector.issue(inspector.inspect())
    world.clock.side_effect = [101.0, 106.0]
    with pytest.raises(ContractViolation):
        inspector.consume(evidence)
    assert "handoff_accept" not in world.events


@pytest.mark.parametrize("field,value", [
    ("writer_controls", ()), ("admission_controls", ()), ("sessions_checked", False),
    ("sessions_accounted", False), ("external_writers_blocked", False),
    ("sessions_checked", 1), ("continuity", object()),
])
def test_empty_activity_or_advisory_lock_alone_is_not_exclusivity(world, field, value):
    controller = ExclusivityController(world)
    proof = controller.verify()
    controller.proof = replace(proof, **{field: value})
    with pytest.raises(ContractViolation):
        controller.check()


@pytest.mark.parametrize("field,value", [
    ("demonstrated", False), ("bootstrap_session_only", True),
    ("drill_reference", ""), ("independent_channel", ""),
])
def test_recovery_requires_independent_demonstrated_drill(world, field, value):
    adapter = RecoveryVerifier(world)
    proof = adapter.verify()
    world.overrides["recovery_proof"] = replace(proof, **{field: value})
    with pytest.raises(ContractViolation):
        adapter.verify()


@pytest.mark.parametrize("bad_time", [float("nan"), float("inf"), True])
def test_nonfinite_and_boolean_times_fail_closed(world, bad_time):
    proof = RecoveryVerifier(world).verify()
    world.overrides["recovery_proof"] = replace(proof, expires_at=bad_time)
    with pytest.raises(ContractViolation):
        RecoveryVerifier(world).verify()


def test_evidence_from_other_operation_even_same_target_is_rejected(world):
    other = MemoryScenario("b" * 64, clock=world.clock)
    proof = RecoveryVerifier(other).verify()
    world.overrides["recovery_proof"] = proof
    with pytest.raises(ContractViolation):
        RecoveryVerifier(world).verify()
    assert proof.binding.target == world.binding.target
    assert proof.binding.operation is not world.binding.operation


def test_replaced_target_or_plan_binding_is_rejected(world):
    proof = RecoveryVerifier(world).verify()
    for binding in (replace(world.binding, plan_digest="c" * 64),
                    Binding(replace(Target(), database="livenet"), object(), "b" * 64)):
        world.overrides["recovery_proof"] = replace(proof, binding=binding)
        with pytest.raises(ContractViolation):
            RecoveryVerifier(world).verify()


def test_no_final_release_without_independent_final_observation(world):
    controller = ExclusivityController(world)
    controller.verify()
    with pytest.raises(ContractViolation):
        controller.release(True)
    assert world.exclusive
    assert "release_window" not in world.events


@pytest.mark.parametrize("field,value", [
    ("lock_held", False), ("lock_key", (1, 2)), ("fingerprint", "not-a-hash"),
    ("fingerprint", "c" * 64), ("expires_at", float("nan")),
])
def test_fix1_issue_checks_fields_even_on_issued_inspection(world, monkeypatch, field, value):
    step = world.step

    def altered_observation(name, result=None):
        if name == "inspection":
            result = replace(result, **{field: value})
        return step(name, result)

    monkeypatch.setattr(world, "step", altered_observation)
    inspector = InspectorAdapter(world)
    observed = inspector.inspect()
    with pytest.raises(ContractViolation):
        inspector.issue(observed)


@pytest.mark.parametrize("invalid", [None, True, {}, "inspection"])
def test_fix1_issue_rejects_missing_or_untyped_fields(world, invalid):
    inspector = InspectorAdapter(world)
    inspector.inspect()
    with pytest.raises(ContractViolation):
        inspector.issue(invalid)


def test_fix1_handoff_cannot_outlive_source_inspection(world):
    inspector = InspectorAdapter(world)
    observed = inspector.inspect()
    world.clock.return_value = observed.expires_at - 0.5
    proof = inspector.issue(observed)
    assert proof.expires_at == observed.expires_at
    assert proof.expires_at - proof.issued_at == 0.5
    world.clock.return_value += 0.6
    with pytest.raises(ContractViolation):
        inspector.consume(proof)


def test_fix1_copied_inspection_is_not_an_issued_observation(world):
    inspector = InspectorAdapter(world)
    observed = inspector.inspect()
    with pytest.raises(ContractViolation):
        inspector.issue(replace(observed))
    inspector.consume(inspector.issue(observed))


def test_fix1_unlock_failure_closes_once_and_retains_original(world):
    from m12b_security_adapters import CleanupError
    inspector = InspectorAdapter(world)
    inspector.inspect()
    original = RuntimeError("synthetic-sensitive-unlock")
    world.failures["primary_unlock"] = original
    for _ in range(2):
        with pytest.raises(CleanupError) as caught:
            inspector.close()
        assert caught.value.original_error is original
        assert "synthetic-sensitive" not in str(caught.value)
    assert world.events.count("primary_unlock") == 1
    assert world.events.count("close:livenet_m12b_inspector") == 1
    assert inspector.session.physical in world.closed and not world.lock_held


def test_fix1_a_second_unlock_fault_is_unreachable_after_successful_close(world, monkeypatch):
    inspector = InspectorAdapter(world)
    inspector.inspect()
    step = world.step
    calls = []

    def fail_second_unlock(name, result=None):
        if name == "primary_unlock":
            calls.append(name)
            if len(calls) == 2:
                raise RuntimeError("second unlock must not execute")
        return step(name, result)

    monkeypatch.setattr(world, "step", fail_second_unlock)
    inspector.close()
    inspector.close()
    assert calls == ["primary_unlock"]


def test_fix1_unlock_and_close_failures_are_both_recorded_without_retry(world):
    from m12b_security_adapters import CleanupError
    inspector = InspectorAdapter(world)
    inspector.inspect()
    first = RuntimeError("synthetic-sensitive-first")
    world.failures.update(primary_unlock=first, **{"close:livenet_m12b_inspector": ValueError("synthetic-sensitive-second")})
    for _ in range(2):
        with pytest.raises(CleanupError) as caught:
            inspector.close()
        assert caught.value.original_error is first
        assert {i.operation for i in caught.value.issues} == {"inspector.unlock", "inspector.close"}
        assert "synthetic-sensitive" not in repr(caught.value.issues)
    assert world.events.count("primary_unlock") == 1
    assert world.events.count("close:livenet_m12b_inspector") == 1
    assert world.lock_held  # Neither release nor physical closure was confirmed.
