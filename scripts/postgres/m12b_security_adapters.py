"""IMP1: typed, in-memory adapters. No SQL, connections, credentials or CLI.

Proofs describe a simulation, not operational authorization or authenticated
evidence. Inspection and handoff have issuing-object checks; operation claims
are recorded in a shared synchronous in-memory registry.
"""

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from time import monotonic
from typing import Callable


INSPECTOR = "livenet_m12b_inspector"
MIGRATOR = "livenet_m12b_migrator"
BOOTSTRAP = "livenet_m12b_bootstrap"
OWNER = "livenet_m12b_security_owner"
PRIMARY_LOCK = (1295073858, 6601)
TRANSACTION_LOCK = (1295073858, 6602)
HANDOFF_TTL = 5.0


class ContractViolation(ValueError):
    """Fixed contract messages only; never relay adapter/driver errors."""


class CommitUncertain(ContractViolation):
    pass


class OperationStatus(str, Enum):
    REGISTERED = "REGISTERED"
    RUNNING = "RUNNING"
    CLOSED = "CLOSED"
    BLOCKED = "BLOCKED"
    ROLLED_BACK = "ROLLED_BACK"
    RECONCILE_REQUIRED = "RECONCILE_REQUIRED"
    RECONCILED = "RECONCILED"


class RegistryRefused(ContractViolation):
    def __init__(self, reconciliation_required):
        self.reconciliation_required = reconciliation_required
        super().__init__("Registo indisponivel, desconhecido ou operacao ja utilizada")


@dataclass(frozen=True)
class CleanupIssue:
    operation: str
    error_type: str


class CleanupError(ContractViolation):
    def __init__(self, original_error, issues):
        self.original_error = original_error
        self.issues = tuple(issues)
        super().__init__("Limpeza incompleta; reconciliacao obrigatoria")


class _Cleanup:
    """Attempt each cleanup once, retaining failures without printing details."""

    def _init_cleanup(self):
        self._cleanup_attempted = set()
        self._cleanup_issues = []
        self._cleanup_original = None

    def _cleanup_once(self, name, action):
        if name in self._cleanup_attempted:
            return
        self._cleanup_attempted.add(name)
        try:
            action()
        except Exception as error:
            if self._cleanup_original is None:
                self._cleanup_original = error
            self._cleanup_issues.append(CleanupIssue(name, type(error).__name__))

    def _finish_cleanup(self):
        if self._cleanup_issues:
            raise CleanupError(self._cleanup_original, self._cleanup_issues) from None


def require(condition, message="Contrato offline divergente"):
    if not condition:
        raise ContractViolation(message)


def yes(value):
    return value is True


@dataclass(frozen=True)
class Target:
    project: str = "livenetv2-m12b-test"
    database: str = "livenet_m12b_test"
    system_identifier: str = "7699783234487926818"
    baseline: str = "f066a01a7230"
    revision: str = "b12b01a7230"
    host: str = "db"
    port: int = 5432


@dataclass(frozen=True)
class Binding:
    target: Target
    operation: object
    plan_digest: str


@dataclass(frozen=True)
class OperationClaim:
    binding: Binding
    authority: object


@dataclass(frozen=True)
class OperationRecord:
    binding: Binding
    status: OperationStatus
    claim: OperationClaim | None = None


@dataclass(frozen=True)
class Reconciliation:
    binding: Binding
    reference: str
    outcome: str


class OperationRegistry:
    """Shared synchronous fake ledger; no durable or cross-process guarantee.

    A missing record never means permission. Only explicit registration of a
    new operation creates REGISTERED; reconciliation never reopens it.
    """

    def __init__(self):
        self._records = {}
        self._authority = object()
        self.available = True
        self.reconciliations = {}

    def _available(self):
        if self.available is not True:
            raise RegistryRefused(True)

    def new_binding(self, target: Target, plan_digest: str) -> Binding:
        self._available()
        require(type(target) is Target and target == Target() and type(target.port) is int)
        require(type(plan_digest) is str and len(plan_digest) == 64
                and all(c in "0123456789abcdef" for c in plan_digest))
        binding = Binding(target, object(), plan_digest)
        self._records[binding.operation] = OperationRecord(binding, OperationStatus.REGISTERED)
        return binding

    def lookup(self, binding: Binding) -> OperationRecord:
        self._available()
        record = self._records.get(binding.operation)
        if record is None or record.binding is not binding:
            raise RegistryRefused(True)
        return record

    def claim(self, binding: Binding) -> OperationClaim:
        record = self.lookup(binding)
        if record.status is not OperationStatus.REGISTERED:
            raise RegistryRefused(record.status in (OperationStatus.RUNNING, OperationStatus.RECONCILE_REQUIRED))
        claim = OperationClaim(binding, self._authority)
        self._records[binding.operation] = OperationRecord(binding, OperationStatus.RUNNING, claim)
        return claim

    def finish(self, claim: OperationClaim, status: OperationStatus):
        require(type(claim) is OperationClaim and claim.authority is self._authority)
        record = self.lookup(claim.binding)
        require(record.claim is claim and record.status is OperationStatus.RUNNING)
        require(type(status) is OperationStatus and status in (
            OperationStatus.CLOSED, OperationStatus.BLOCKED, OperationStatus.ROLLED_BACK,
            OperationStatus.RECONCILE_REQUIRED))
        self._records[claim.binding.operation] = OperationRecord(claim.binding, status, claim)

    def reconcile(self, evidence: Reconciliation):
        require(type(evidence) is Reconciliation)
        record = self.lookup(evidence.binding)
        require(record.status is OperationStatus.RECONCILE_REQUIRED)
        require(type(evidence.reference) is str and bool(evidence.reference.strip()))
        require(evidence.outcome in ("confirmed_committed", "confirmed_not_committed"))
        self.reconciliations[evidence.binding.operation] = evidence
        self._records[evidence.binding.operation] = OperationRecord(
            evidence.binding, OperationStatus.RECONCILED, record.claim)


@dataclass(frozen=True)
class Session:
    role: str
    pid: int
    physical: object


@dataclass(frozen=True)
class Proof:
    binding: Binding
    issued_at: float
    expires_at: float


@dataclass(frozen=True)
class PrecheckProof(Proof):
    application_revision: str
    security_revision: str | None
    authorization_present: bool
    unexpected_objects: bool


@dataclass(frozen=True)
class ExclusivityProof(Proof):
    writer_controls: tuple[str, ...]
    admission_controls: tuple[str, ...]
    sessions_checked: bool
    sessions_accounted: bool
    external_writers_blocked: bool
    continuity: object


@dataclass(frozen=True)
class RecoveryProof(Proof):
    drill_reference: str
    independent_channel: str
    demonstrated: bool
    bootstrap_session_only: bool


@dataclass(frozen=True)
class InspectionProof(Proof):
    session: Session
    fingerprint: str
    lock_key: tuple[int, int]
    lock_held: bool


@dataclass(frozen=True)
class HandoffProof(InspectionProof):
    pass


@dataclass(frozen=True)
class CommitProof(Proof):
    session: Session
    transaction_lock: tuple[int, int]
    committed: bool


@dataclass(frozen=True)
class PrecommitProof(Proof):
    session: Session
    application_revision: str
    security_revision: str
    physical_valid: bool


@dataclass(frozen=True)
class DurabilityProof(Proof):
    session: Session
    committed_session: Session
    durable: bool
    physical_valid: bool
    fingerprint: str
    owner: str


@dataclass(frozen=True)
class OwnershipProof(Proof):
    session: Session
    owner: str
    staged: bool


@dataclass(frozen=True)
class ClosureProof(Proof):
    session: Session
    owner: str
    committed: bool
    create_revoked: bool
    memberships_revoked: bool


@dataclass(frozen=True)
class FinalProof(Proof):
    session: Session
    owner: str
    ownership_valid: bool
    acl_valid: bool
    baseline_preserved: bool
    app_dml_enabled: bool
    fingerprint: str


@dataclass(frozen=True)
class ReleaseProof(Proof):
    released: bool


@dataclass(frozen=True)
class AdapterContract:
    role: str
    capabilities: tuple[str, ...]
    transaction: str
    statement_seconds: int
    lock_seconds: int
    lifecycle: str
    errors: tuple[str, ...] = ("identity", "timeout", "state", "close", "lock",
                              "evidence", "commit_uncertain", "rollback")


@dataclass
class MemoryScenario:
    """Fake world shared by dependency-injected adapters; performs no I/O.

    overrides are observation faults, failures are exception faults. Both are
    simulation inputs, never a way to authorize the existing executor.
    """

    plan_digest: str
    target: Target = field(default_factory=Target)
    clock: Callable[[], float] = monotonic
    overrides: dict = field(default_factory=dict)
    failures: dict = field(default_factory=dict)
    events: list = field(default_factory=list)
    registry: OperationRegistry = field(default_factory=OperationRegistry)

    def __post_init__(self):
        require(type(self.target) is Target and self.target == Target())
        require(type(self.target.port) is int)
        require(type(self.plan_digest) is str and len(self.plan_digest) == 64
                and all(c in "0123456789abcdef" for c in self.plan_digest))
        require(type(self.registry) is OperationRegistry)
        self.binding = self.registry.new_binding(self.target, self.plan_digest)
        self.sessions = []
        self.closed = set()
        self.lock_held = False
        self.exclusive = False
        self.continuity = object()
        self.transaction = False
        self.transaction_lock_held = False
        self.commit_attempted = False
        self.work_validated = False
        self.committed = False
        self.admin_pending = False
        self.admin_commit_attempted = False
        self.owner = MIGRATOR
        self.create_revoked = False
        self.memberships_revoked = False
        self.fingerprint = "a" * 64
        self.final_proof = None

    def stamp(self, ttl=30.0):
        now = self.clock()
        return self.binding, now, now + ttl

    def precheck(self) -> PrecheckProof:
        return self.step("precheck", PrecheckProof(*self.stamp(), self.target.baseline, None, False, False))

    def check(self, proof, kind, ttl=30.0):
        require(type(proof) is kind)
        now = self.clock()
        require(proof.binding is self.binding)
        require(all(type(v) in (int, float) and isfinite(v)
                    for v in (now, proof.issued_at, proof.expires_at)))
        require(0 < proof.expires_at - proof.issued_at <= ttl)
        require(proof.issued_at <= now <= proof.expires_at, "Evidencia expirada")

    def step(self, name, result=None):
        self.events.append(name)
        if name in self.failures:
            raise self.failures[name]
        return self.overrides.get(name, result)

    def session(self, role):
        session = Session(role, 100 + len(self.sessions), object())
        self.sessions.append(session)
        return session

    def check_session(self, session, role):
        require(type(session) is Session and session.role == role)
        require(any(session is s for s in self.sessions))
        require(session.physical not in self.closed)

    def close(self, session):
        if session is not None and session.physical not in self.closed:
            self.step("close:" + session.role)
            self.closed.add(session.physical)


class InspectorAdapter(_Cleanup):
    contract = AdapterContract(INSPECTOR, ("catalog", "id_counts", "baseline", "primary_lock"),
                               "repeatable_read_read_only", 5, 1, "one_session_until_final")

    def __init__(self, scenario: MemoryScenario):
        self._init_cleanup()
        self.world = scenario
        self.session = None
        self._issued = None
        self._used = False
        self._inspection = None

    def inspect(self) -> InspectionProof:
        self.world.step("inspect")
        require(self.session is None)
        self.session = self.world.session(INSPECTOR)
        self.world.lock_held = True
        self._inspection = self.world.step("inspection", InspectionProof(*self.world.stamp(), self.session,
                                           self.world.fingerprint, PRIMARY_LOCK, True))
        return self._inspection

    def continuity(self):
        require(self.world.step("primary_lock", self.world.lock_held) is True,
                "Lock primario perdido")
        self.world.check_session(self.session, INSPECTOR)

    def issue(self, inspection: InspectionProof) -> HandoffProof:
        self.world.check(inspection, InspectionProof)
        require(inspection is self._inspection, "Inspecao nao emitida por esta autoridade")
        self.world.check_session(inspection.session, INSPECTOR)
        require(inspection.session is self.session and inspection.lock_key == PRIMARY_LOCK
                and yes(inspection.lock_held))
        require(type(inspection.fingerprint) is str and len(inspection.fingerprint) == 64
                and all(c in "0123456789abcdef" for c in inspection.fingerprint)
                and inspection.fingerprint == self.world.fingerprint)
        self.continuity()
        require(self._issued is None and not self._used)
        binding, now, end = self.world.stamp(HANDOFF_TTL)
        issued = HandoffProof(binding, now, min(end, inspection.expires_at), inspection.session,
                              inspection.fingerprint, PRIMARY_LOCK, True)
        self.world.check(issued, HandoffProof, HANDOFF_TTL)
        self._issued = issued
        return self.world.step("handoff_issue", self._issued)

    def consume(self, proof: HandoffProof) -> None:
        require(proof is self._issued and not self._used, "Handoff forjado ou repetido")
        self._used = True  # A failed consumption cannot be retried either.
        self.world.check(proof, HandoffProof, HANDOFF_TTL)
        self.continuity()
        require(proof.session is self.session and proof.lock_key == PRIMARY_LOCK and yes(proof.lock_held))
        require(self.world.step("handoff_fingerprint", self.world.fingerprint) == proof.fingerprint)
        self.world.check(proof, HandoffProof, HANDOFF_TTL)
        self.continuity()
        self.world.step("handoff_accept")

    def verify_unchanged(self, fingerprint: str) -> None:
        self.continuity()
        require(self.world.step("protected_fingerprint", self.world.fingerprint) == fingerprint)
        self.continuity()

    def close(self):
        if self.session is not None:
            def unlock():
                self.world.step("primary_unlock")
                self.world.lock_held = False
            self._cleanup_once("inspector.unlock", unlock)
            self._cleanup_once("inspector.close", lambda: self.world.close(self.session))
            if self.session.physical in self.world.closed:
                self.world.lock_held = False
        self._finish_cleanup()


class MigratorAdapter(_Cleanup):
    contract = AdapterContract(MIGRATOR, ("security_revision_only", "own_ledger", "transaction_lock"),
                               "read_committed_outer_transaction", 30, 3, "new_session_no_retry")

    def __init__(self, scenario: MemoryScenario):
        self._init_cleanup()
        self.world = scenario
        self.session = None

    def begin(self) -> Session:
        self.world.step("migration_begin")
        self.session = self.world.session(MIGRATOR)
        self.world.transaction = True
        self.world.transaction_lock_held = self.world.step("transaction_lock", True)
        return self.world.step("migration_identity", self.session)

    def work(self) -> PrecommitProof:
        require(self.world.transaction and self.session is not None)
        self.world.step("migration_work")  # In-memory model, never invokes Alembic.
        return self.world.step("precommit", PrecommitProof(*self.world.stamp(), self.session,
                               self.world.target.baseline, self.world.target.revision, True))

    def commit(self) -> CommitProof:
        require(self.world.transaction and self.world.work_validated and self.session is not None)
        self.world.commit_attempted = True
        self.world.step("migration_commit")
        self.world.committed = True
        self.world.transaction = False
        self.world.transaction_lock_held = False
        return self.world.step("commit_receipt", CommitProof(*self.world.stamp(), self.session,
                               TRANSACTION_LOCK, True))

    def rollback(self):
        require(not self.world.commit_attempted and not self.world.committed)
        self.world.step("migration_rollback")
        self.world.transaction = False
        self.world.transaction_lock_held = False

    def close(self):
        if self.session is not None:
            self._cleanup_once("migrator.close", lambda: self.world.close(self.session))
        if self.session is not None and self.session.physical in self.world.closed:
            self.world.transaction = False
            self.world.transaction_lock_held = False
        self._finish_cleanup()


class PostCommitVerifier(_Cleanup):
    contract = AdapterContract(MIGRATOR, ("catalog", "both_ledgers", "empty_security"),
                               "repeatable_read_read_only", 5, 1, "new_physical_session")

    def __init__(self, scenario: MemoryScenario):
        self._init_cleanup()
        self.world = scenario
        self.session = None

    def verify(self, receipt: CommitProof) -> DurabilityProof:
        require(self.world.committed and not self.world.transaction)
        require(receipt.session.physical in self.world.closed)
        self.world.step("postcommit")
        self.session = self.world.session(MIGRATOR)
        return self.world.step("durability", DurabilityProof(*self.world.stamp(), self.session,
                               receipt.session, True, True, self.world.fingerprint, MIGRATOR))

    def close(self):
        if self.session is not None:
            self._cleanup_once("postcommit.close", lambda: self.world.close(self.session))
        self._finish_cleanup()


class AdministrativeCloser(_Cleanup):
    contract = AdapterContract(BOOTSTRAP, ("stage_ownership", "close_temporary_privileges", "final_catalog"),
                               "atomic_administrative_closure", 30, 3, "separate_final_read_only_session")

    def __init__(self, scenario: MemoryScenario):
        self._init_cleanup()
        self.world = scenario
        self.session = self.final_session = None

    def transfer(self, durability: DurabilityProof) -> OwnershipProof:
        require(self.world.committed and yes(durability.durable))
        self.world.step("ownership")
        self.session = self.world.session(BOOTSTRAP)
        self.world.admin_pending = True
        return self.world.step("ownership_receipt", OwnershipProof(*self.world.stamp(), self.session, OWNER, True))

    def revoke(self) -> ClosureProof:
        require(self.world.admin_pending)
        self.world.step("revocation")
        self.world.admin_commit_attempted = True
        self.world.step("administrative_commit")
        self.world.admin_pending = False
        self.world.owner = OWNER
        self.world.create_revoked = self.world.memberships_revoked = True
        return self.world.step("closure", ClosureProof(*self.world.stamp(), self.session, OWNER, True, True, True))

    def verify_final(self) -> FinalProof:
        require(self.world.owner == OWNER and self.world.create_revoked and self.world.memberships_revoked)
        self.world.step("final_verify")
        self.final_session = self.world.session(BOOTSTRAP)
        proof = FinalProof(*self.world.stamp(), self.final_session, OWNER, True, True, True, False,
                           self.world.fingerprint)
        self.world.final_proof = self.world.step("final", proof)
        return self.world.final_proof

    def rollback(self):
        if self.world.admin_pending and not self.world.admin_commit_attempted:
            self.world.step("administrative_rollback")
            self.world.admin_pending = False

    def close(self):
        if self.final_session is not None:
            self._cleanup_once("administrative.final_close", lambda: self.world.close(self.final_session))
        if self.session is not None:
            self._cleanup_once("administrative.close", lambda: self.world.close(self.session))
        self._finish_cleanup()


class ExclusivityController:
    """Synthetic barrier observations; no HBA, ACL, Docker or real lock actions."""

    contract = AdapterContract("external_control", ("writers", "admission", "sessions", "continuity"),
                               "outside_database_transaction", 5, 1, "retained_on_failure")

    def __init__(self, scenario: MemoryScenario):
        self.world = scenario
        self.proof = None

    def verify(self) -> ExclusivityProof:
        self.world.step("exclusivity")
        self.proof = self.world.step("exclusive_proof", ExclusivityProof(*self.world.stamp(),
            ("simulated-writer-control",), ("simulated-admission-control",), True, True, True,
            self.world.continuity))
        self.check()
        self.world.exclusive = True
        return self.proof

    def check(self):
        proof = self.world.step("exclusive_continuity", self.proof)
        self.world.check(proof, ExclusivityProof)
        require(proof is self.proof and proof.continuity is self.world.continuity)
        require(type(proof.writer_controls) is tuple and type(proof.admission_controls) is tuple)
        require(bool(proof.writer_controls) and bool(proof.admission_controls))
        require(all(type(v) is str and v.strip() for v in (*proof.writer_controls, *proof.admission_controls)))
        require(all(yes(v) for v in (proof.sessions_checked, proof.sessions_accounted,
                                     proof.external_writers_blocked)))

    def release(self, final: FinalProof) -> ReleaseProof:
        self.check()
        self.world.check(final, FinalProof)
        require(final is self.world.final_proof and self.world.exclusive)
        require(not self.world.lock_held and all(s.physical in self.world.closed for s in self.world.sessions))
        self.world.step("release_window")
        self.world.exclusive = False
        return self.world.step("release_receipt", ReleaseProof(*self.world.stamp(), True))


class RecoveryVerifier:
    contract = AdapterContract("independent_recovery", ("drill_attestation",), "read_only_evidence", 5, 1,
                               "no_bootstrap_session_substitution")

    def __init__(self, scenario: MemoryScenario):
        self.world = scenario

    def verify(self) -> RecoveryProof:
        self.world.step("recovery")
        proof = self.world.step("recovery_proof", RecoveryProof(*self.world.stamp(),
            "simulated-independent-drill", "simulated-infrastructure-channel", True, False))
        self.world.check(proof, RecoveryProof)
        require(yes(proof.demonstrated) and proof.bootstrap_session_only is False)
        require(type(proof.drill_reference) is str and bool(proof.drill_reference.strip()))
        require(type(proof.independent_channel) is str and bool(proof.independent_channel.strip()))
        return proof
