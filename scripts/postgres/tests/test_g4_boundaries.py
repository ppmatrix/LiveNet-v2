"""I1-only offline tests. No runner/transport/authentication is implemented.

T07/T30 prove contractual refusal only, not credential/AUTH-03 access or a future
runner's call order. T35 proves current import/construction boundaries, not future
adapters. Socket/process hooks cover selected Python APIs, not arbitrary native I/O.
Run with bytecode, pytest cache and third-party plugin autoload disabled.
"""

import ast
import builtins
from contextlib import contextmanager, nullcontext
from dataclasses import FrozenInstanceError, fields, replace
import importlib
import io
import os
from pathlib import Path
import socket
import subprocess
import sys

import pytest

from scripts.postgres.g4 import contracts as c
from g4_doubles import (
    EXPECTED_CEILINGS, EXPECTED_GATE_REFUSAL, EXPECTED_TARGET_REFUSAL,
    FakeClock, ForbiddenOperations, claimed_authorization, credential,
    environment, request, run, session,
)


@pytest.fixture(autouse=True)
def no_external_operations(monkeypatch):
    """Deny selected Python socket/process APIs during test execution."""
    sentinel = ForbiddenOperations()

    def forbidden(*args, **kwargs):
        sentinel.reject("external")

    for owner, name in ((socket, "socket"), (socket, "create_connection"),
                        (socket, "getaddrinfo"), (subprocess, "Popen"),
                        (subprocess, "run"), (os, "system"), (os, "fork"),
                        (os, "posix_spawn"), (os, "posix_spawnp")):
        if hasattr(owner, name):
            monkeypatch.setattr(owner, name, forbidden)
    yield sentinel
    assert sentinel.attempts == []


def assert_refused(value, expected):
    assert (value.verdict.value, value.code.value) == expected


def test_t07_gate_absent_has_explicit_contractual_refusal():
    result = c.execution_boundary(request(), expected=environment())
    assert_refused(result, EXPECTED_GATE_REFUSAL)


@pytest.mark.parametrize("target", ["auth03", "m12b", "other-environment"])
def test_t30_unapproved_target_has_explicit_contractual_refusal(target):
    result = c.execution_boundary(request(target), expected=environment())
    assert_refused(result, EXPECTED_TARGET_REFUSAL)


def test_t30_wrong_physical_generation_refused():
    expected = environment()
    other = replace(expected, vm=replace(expected.vm, generation="33333333-3333-4333-8333-333333333333"))
    assert_refused(c.execution_boundary(request(), expected=other), EXPECTED_TARGET_REFUSAL)


@pytest.mark.parametrize("claim", [None, True, False, {"approved": True, "enable": True}])
def test_t35_untrusted_authorization_data_never_opens_boundary(claim):
    assert_refused(c.execution_boundary(request(), expected=environment(), authorization=claim),
                   EXPECTED_GATE_REFUSAL)


def test_t35_approval_records_are_distinct_unverified_data():
    claim = claimed_authorization()
    assert type(claim.contract.candidate) is c.ApprovalCandidate
    assert type(claim.contract.approval) is c.ExternalApprovalReference
    assert claim.contract.state is c.AuthorizationState.UNVERIFIED
    assert claim.state is c.AuthorizationState.BLOCKED
    assert_refused(c.execution_boundary(request(), expected=environment(), authorization=claim),
                   EXPECTED_GATE_REFUSAL)
    with pytest.raises((TypeError, c.ContractError)):
        c.ApprovedContract(**{"candidate": {"approved": True}, "approval": True})
    with pytest.raises(ValueError):
        replace(claim.contract, state=c.AuthorizationState.REFERENCED)


def test_t35_enable_and_environment_flags_cannot_authorize(monkeypatch):
    monkeypatch.setenv("G4_ENABLE", "true")
    monkeypatch.setenv("G4_APPROVED", "true")
    with pytest.raises(TypeError):
        c.execution_boundary(request(), expected=environment(), enable=True)
    with pytest.raises(TypeError):
        c.ExecutionRequest(run(), "g4-offline-fixture", c.Purpose.RUNTIME, enable=True)
    assert_refused(c.execution_boundary(request(), expected=environment()), EXPECTED_GATE_REFUSAL)


def _g4_import_references():
    """Capture module, parent-attribute and every original contract-class identity."""
    scripts = sys.modules["scripts"]
    postgres = sys.modules["scripts.postgres"]
    package = sys.modules["scripts.postgres.g4"]
    contracts = sys.modules["scripts.postgres.g4.contracts"]
    assert scripts.postgres is postgres
    assert postgres.g4 is package
    assert package.contracts is contracts
    assert contracts is c
    classes = tuple(value for value in vars(contracts).values()
                    if isinstance(value, type) and value.__module__ == contracts.__name__)
    return (scripts, postgres, package, contracts, scripts.postgres, postgres.g4,
            package.contracts, *classes)


@contextmanager
def _isolated_g4_reimport():
    """Restore both module entries and parent attributes on every exit path."""
    postgres = sys.modules["scripts.postgres"]
    package = sys.modules["scripts.postgres.g4"]
    contracts = sys.modules["scripts.postgres.g4.contracts"]
    with pytest.MonkeyPatch.context() as isolated:
        # Record attributes before importlib replaces the parent's g4 reference.
        isolated.setattr(postgres, "g4", package)
        isolated.setattr(package, "contracts", contracts)
        isolated.delitem(sys.modules, "scripts.postgres.g4.contracts")
        isolated.delitem(sys.modules, "scripts.postgres.g4")
        yield


def test_t35_fresh_imports_and_construction_do_not_perform_operational_io(monkeypatch):
    # Import machinery must read module source; operational file APIs are denied.
    before = _g4_import_references()
    sentinel = ForbiddenOperations()

    def forbidden(*args, **kwargs):
        sentinel.reject("file_or_configuration")

    for owner, name in ((builtins, "open"), (io, "open"), (os, "open"),
                        (os, "getenv"), (Path, "open")):
        monkeypatch.setattr(owner, name, forbidden)
    with _isolated_g4_reimport():
        imported_package = importlib.import_module("scripts.postgres.g4")
        fresh = importlib.import_module("scripts.postgres.g4.contracts")
        assert imported_package.__doc__.startswith("G4 contract foundation")
        assert fresh.ExecutionLimits().canonical_bytes == 33554432
        assert fresh.ResourceLimits().memory_bytes is None
    after = _g4_import_references()
    assert len(after) == len(before)
    assert all(current is original for current, original in zip(after, before))
    assert sentinel.attempts == []


@pytest.mark.parametrize("failure_point", [None, "package", "contracts"])
def test_t35_reimport_restores_all_references_after_success_or_exception(failure_point):
    before = _g4_import_references()
    # A normal cycle after each scenario detects state leaking into the next use.
    for point in (failure_point, None):
        outcome = pytest.raises(RuntimeError, match="simulated import failure") if point else nullcontext()
        with outcome:
            with _isolated_g4_reimport():
                package = importlib.import_module("scripts.postgres.g4")
                assert package is not before[2]
                assert sys.modules["scripts.postgres"].g4 is package
                if point == "package":
                    raise RuntimeError("simulated import failure")
                fresh = importlib.import_module("scripts.postgres.g4.contracts")
                assert fresh is not c
                assert package.contracts is fresh
                assert sys.modules["scripts.postgres.g4.contracts"] is fresh
                assert fresh.EnvironmentIdentity is not c.EnvironmentIdentity
                if point == "contracts":
                    raise RuntimeError("simulated import failure")
        after = _g4_import_references()
        assert len(after) == len(before)
        assert all(current is original for current, original in zip(after, before))
        # Original fixture instances still satisfy the original exact-type checks.
        assert_refused(c.execution_boundary(request(), expected=environment()), EXPECTED_GATE_REFUSAL)


def test_t35_source_has_only_contract_dependencies_and_no_entrypoint():
    directory = Path(__file__).resolve().parents[1] / "g4"
    allowed = {"dataclasses", "enum", "math", "re", "types"}
    for name in ("__init__.py", "contracts.py"):
        tree = ast.parse((directory / name).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(alias.name in allowed for alias in node.names)
            if isinstance(node, ast.ImportFrom):
                assert node.module in allowed and node.level == 0
            if isinstance(node, ast.Name):
                assert node.id not in {"eval", "exec", "open", "__import__"}
        assert not any(isinstance(node, ast.If) and "__name__" in ast.unparse(node.test)
                       for node in tree.body)


@pytest.mark.parametrize("factory", [
    environment, run, lambda: credential(c.Purpose.RUNTIME),
    lambda: session(c.Purpose.RUNTIME, 101), request, claimed_authorization,
    c.ExecutionLimits, lambda: c.EvidenceLimits(1, 1024), c.ResourceLimits,
    lambda: c.Deadline(100.0, 104.0, "fixture_clock"),
    lambda: c.FailureRecord(c.Verdict.BLOCKED, c.ErrorCode.GATE_ABSENT),
    lambda: c.FailureChain(c.FailureRecord(c.Verdict.FAIL, c.ErrorCode.CONTRACT_VIOLATION)),
    lambda: c.BoundaryDecision(c.ErrorCode.GATE_ABSENT),
])
def test_contracts_are_frozen_and_do_not_contain_mutable_fields(factory):
    value = factory()
    first = fields(value)[0].name
    with pytest.raises((FrozenInstanceError, AttributeError)):
        setattr(value, first, None)
    assert not hasattr(value, "__dict__")
    assert all(not isinstance(getattr(value, f.name), (list, dict, set)) for f in fields(value))


@pytest.mark.parametrize("value", ["", " ", "G4", "auth03", "g4-", "g4 bad", "g4-" + "x" * 64, None, True])
def test_environment_identifier_validation(value):
    with pytest.raises(c.ContractError):
        replace(environment(), environment_id=value)


@pytest.mark.parametrize("change", [
    {"vm_id": 0}, {"vm_id": True}, {"generation": "invalid"},
    {"generation": "00000000-0000-0000-0000-000000000000"},
    {"attestation_digest": "A" * 64}, {"attestation_digest": ""},
])
def test_vm_generation_validation(change):
    with pytest.raises(c.ContractError):
        replace(environment().vm, **change)


@pytest.mark.parametrize("sid,version", [
    ("0", 160004), ("0123", 160004), ("-1", 160004), ("1" * 21, 160004),
    (str(2**64), 160004), ("123", 150004), ("123", 170000), ("123", True),
])
def test_cluster_identity_validation(sid, version):
    with pytest.raises(c.ContractError):
        c.ClusterIdentity(sid, version)


def test_incoherent_database_cluster_and_approval_rejected():
    identity = environment()
    other_cluster = c.ClusterIdentity("9876543210123456789", 160004)
    with pytest.raises(c.ContractError, match="IDENTITY_MISMATCH"):
        replace(identity, cluster=other_cluster)
    with pytest.raises(c.ContractError):
        replace(identity.database, oid=True)
    candidate = c.ApprovalCandidate(identity, "c" * 64)
    claim = claimed_authorization()
    with pytest.raises(c.ContractError, match="IDENTITY_MISMATCH"):
        c.ApprovedContract(candidate, claim.contract.approval)
    with pytest.raises(c.ContractError):
        replace(claim, request=request("auth03"))


@pytest.mark.parametrize("factory", [
    lambda: replace(environment().database, name=""),
    lambda: replace(environment().database, name="bad.name"),
    lambda: replace(environment().database, oid=2**32),
    lambda: replace(run(), run_id="not_a_uuid"),
    lambda: replace(credential(c.Purpose.RUNTIME), purpose="runtime"),
    lambda: replace(credential(c.Purpose.RUNTIME), reference=""),
    lambda: replace(credential(c.Purpose.RUNTIME), issuer=""),
    lambda: replace(session(c.Purpose.RUNTIME, 101), backend_start_us=0),
    lambda: replace(session(c.Purpose.RUNTIME, 101), session_role="another_role"),
    lambda: replace(request(), purpose="runtime"),
    lambda: replace(request(), requested_environment=""),
    lambda: c.execution_boundary({"approved": True}, expected=environment()),
])
def test_required_fields_and_untrusted_identity_data_rejected(factory):
    with pytest.raises(c.ContractError):
        factory()


def test_session_and_authorization_cannot_cross_environment_generations():
    identity = environment()
    another = replace(identity, vm=replace(identity.vm, generation="55555555-5555-4555-8555-555555555555"))
    with pytest.raises(c.ContractError, match="IDENTITY_MISMATCH"):
        replace(session(c.Purpose.RUNTIME, 101), run=replace(run(), environment=another))
    with pytest.raises(c.ContractError, match="IDENTITY_MISMATCH"):
        replace(claimed_authorization(), request=replace(request(), run=replace(run(), environment=another)))


@pytest.mark.parametrize("purpose", list(c.Purpose))
def test_all_credential_purposes_are_explicit_and_bound(purpose):
    value = credential(purpose)
    assert value.purpose is purpose
    assert session(purpose, 101).purpose is purpose
    with pytest.raises(c.ContractError, match="PURPOSE_MISMATCH"):
        replace(session(purpose, 101), purpose=next(p for p in c.Purpose if p is not purpose))


def test_readiness_pair_requires_roles_references_run_and_physical_separation():
    runtime, verifier = session(c.Purpose.RUNTIME, 101), session(c.Purpose.VERIFIER, 102)
    assert c.validate_readiness_pair(runtime, verifier) is None
    for invalid in (
        replace(verifier, backend_pid=101),
        replace(verifier, credential=replace(verifier.credential, reference=runtime.credential.reference)),
        replace(verifier, run=replace(verifier.run, run_id="44444444-4444-4444-8444-444444444444")),
        session(c.Purpose.ADMIN, 102),
    ):
        with pytest.raises(c.ContractError):
            c.validate_readiness_pair(runtime, invalid)
    with pytest.raises(c.ContractError):
        replace(runtime, current_role="another_role")


# Literal transition oracles, intentionally independent of the production graph.
@pytest.mark.parametrize("before,after", [
    (c.RequestState.RECEIVED, c.RequestState.PREVALIDATING),
    (c.PrevalidationState.PENDING, c.PrevalidationState.VALID),
    (c.AuthorizationState.UNVERIFIED, c.AuthorizationState.REFERENCED),
    (c.SessionState.OPEN, c.SessionState.ATTESTED),
    (c.EvidenceState.STREAMING, c.EvidenceState.EOF),
    (c.EvidenceState.EOF, c.EvidenceState.SEALED),
    (c.EvaluationState.PENDING, c.EvaluationState.PASSED),
    (c.CancellationState.REQUESTED, c.CancellationState.CONFIRMED),
    (c.CleanupState.ATTEMPTED, c.CleanupState.VERIFIED),
    (c.ReconciliationState.REQUIRED, c.ReconciliationState.REVIEWED),
    (c.FinalState.PENDING, c.FinalState.BLOCKED),
])
def test_valid_transitions_are_pure(before, after):
    assert c.transition(before, after) is after


@pytest.mark.parametrize("before,after", [
    (c.RequestState.RECEIVED, c.RequestState.CLOSED),
    (c.PrevalidationState.REJECTED, c.PrevalidationState.VALID),
    (c.AuthorizationState.BLOCKED, c.AuthorizationState.REFERENCED),
    (c.SessionState.UNKNOWN, c.SessionState.ATTESTED),
    (c.EvidenceState.STREAMING, c.EvidenceState.SEALED),
    (c.EvaluationState.BLOCKED, c.EvaluationState.PASSED),
    (c.CancellationState.UNKNOWN, c.CancellationState.CONFIRMED),
    (c.CleanupState.PENDING, c.CleanupState.VERIFIED),
    (c.ReconciliationState.UNRESOLVED, c.ReconciliationState.CLOSED),
    (c.FinalState.PENDING, c.FinalState.PASS),
    ("PENDING", c.FinalState.PASS), (None, c.FinalState.PASS),
    (c.CleanupState.PENDING, c.EvaluationState.PENDING),
])
def test_invalid_unknown_or_incomplete_states_never_become_success(before, after):
    with pytest.raises(c.ContractError, match="INVALID_TRANSITION"):
        c.transition(before, after)


def test_default_limits_match_literal_ceiling_oracle():
    limits = c.ExecutionLimits()
    assert tuple(getattr(limits, f.name) for f in fields(limits)) == EXPECTED_CEILINGS
    assert c.ResourceLimits() == c.ResourceLimits(None, None, None)
    assert c.ResourceLimits(4096, 2048, 1024).frame_bytes == 1024


@pytest.mark.parametrize("field_name,value", [
    ("connect_seconds", 0), ("connect_seconds", 3), ("connect_seconds", True),
    ("logical_seconds", 5), ("logical_seconds", float("nan")),
    ("logical_seconds", float("inf")), ("logical_seconds", 10**1000),
    ("statement_ms", 501), ("statement_ms", -1), ("statement_ms", 1.0),
    ("heavy_statement_ms", 1001), ("lock_ms", 201),
    ("idle_transaction_ms", 1001), ("canonical_bytes", 33554433),
    ("canonical_bytes", False),
])
def test_invalid_limits_refused(field_name, value):
    with pytest.raises(c.ContractError, match="INVALID_LIMIT"):
        c.ExecutionLimits(**{field_name: value})


@pytest.mark.parametrize("factory", [
    lambda: c.ExecutionLimits(statement_ms=100, lock_ms=200),
    lambda: c.ExecutionLimits(heavy_statement_ms=100),
    lambda: c.EvidenceLimits(0, 1), lambda: c.EvidenceLimits(262145, 1),
    lambda: c.EvidenceLimits(1, -1), lambda: c.ResourceLimits(1024, None, None),
    lambda: c.ResourceLimits(1024, 2048, 512), lambda: c.ResourceLimits(1024, 512, 513),
    lambda: c.ResourceLimits(True, 1, 1),
])
def test_inconsistent_row_byte_and_resource_limits_refused(factory):
    with pytest.raises(c.ContractError, match="INVALID_LIMIT"):
        factory()


def test_deadline_uses_only_injected_clock_readings():
    clock = FakeClock()
    deadline = c.Deadline(100.0, 104.0, clock.domain)
    assert deadline.remaining(clock.reading(), clock_domain=clock.domain) == 3.0
    with pytest.raises(c.ContractError, match="DEADLINE_EXPIRED"):
        deadline.remaining(104.0, clock_domain=clock.domain)
    with pytest.raises(c.ContractError, match="INVALID_DEADLINE"):
        deadline.remaining(101.0, clock_domain="another_clock")


@pytest.mark.parametrize("started,expires", [
    (-1, 1), (1, 1), (2, 1), (0, 5), (True, 2),
    (float("nan"), 2), (0, float("inf")), (0, 10**1000),
])
def test_invalid_deadlines_refused(started, expires):
    with pytest.raises(c.ContractError, match="INVALID_DEADLINE"):
        c.Deadline(started, expires, "fixture_clock")


@pytest.mark.parametrize("now", [99, True, float("nan"), float("inf"), 10**1000])
def test_invalid_clock_readings_refused(now):
    with pytest.raises(c.ContractError, match="INVALID_DEADLINE"):
        c.Deadline(100, 104, "fixture_clock").remaining(now, clock_domain="fixture_clock")


def test_primary_failure_preserved_with_ordered_secondary_failures():
    primary = c.FailureRecord(c.Verdict.FAIL, c.ErrorCode.CONTRACT_VIOLATION)
    cleanup = c.FailureRecord(c.Verdict.OP_ERROR, c.ErrorCode.CLEANUP_FAILED)
    timeout = c.FailureRecord(c.Verdict.OP_ERROR, c.ErrorCode.DEADLINE_EXPIRED)
    original = c.FailureChain(primary)
    result = original.append(cleanup).append(timeout)
    assert result.primary is primary
    assert result.secondary == (cleanup, timeout)
    assert original.secondary == ()
    with pytest.raises(c.ContractError):
        c.FailureChain(primary, [cleanup])


@pytest.mark.parametrize("verdict,code", [
    (c.Verdict.PASS, c.ErrorCode.GATE_ABSENT),
    (c.Verdict.FAIL, c.ErrorCode.EVIDENCE_MISSING),
    (c.Verdict.BLOCKED, c.ErrorCode.OPERATION_FAILED),
    ("FAIL", c.ErrorCode.CONTRACT_VIOLATION),
])
def test_error_classification_cannot_conflate_missing_violation_or_operation(verdict, code):
    with pytest.raises(c.ContractError):
        c.FailureRecord(verdict, code)


def test_identity_representations_and_errors_do_not_disclose_supplied_material():
    marker = "sensitive_marker"
    identity = replace(credential(c.Purpose.RUNTIME), role=marker, reference=marker, issuer=marker)
    assert marker not in repr(identity)
    for name in ("password", "token", "private_key", "secret"):
        with pytest.raises(TypeError) as failure:
            c.CredentialIdentity(environment(), c.Purpose.RUNTIME, "role", "ref", "issuer",
                                 **{name: marker})
        assert marker not in str(failure.value)
    with pytest.raises(c.ContractError) as failure:
        replace(identity, role=marker + " invalid")
    assert marker not in str(failure.value)
    assert marker not in repr(failure.value)
    assert c.ContractError(marker).args == ("INVALID_CONTRACT",)
    assert marker not in repr(claimed_authorization())


def test_sentinels_record_and_refuse_each_forbidden_operation():
    sentinel = ForbiddenOperations()
    for operation in ("credentials", "connect", "process", "auth03"):
        with pytest.raises(AssertionError, match="Forbidden external operation"):
            getattr(sentinel, operation)()
    assert sentinel.attempts == ["credentials", "connect", "process", "auth03"]
