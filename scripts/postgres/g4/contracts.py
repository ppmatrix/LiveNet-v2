"""Pure I1 contracts. Data records, including approval records, grant no authority.

There is intentionally no capability issuer, runner, transport, credential reader,
clock reader or configuration switch. The execution boundary always refuses real
work. Later authenticated gates require a separately reviewed implementation.
"""

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
import re
from types import MappingProxyType


class Verdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"
    OP_ERROR = "OP_ERROR"


class ErrorCode(str, Enum):
    INVALID_CONTRACT = "INVALID_CONTRACT"
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
    PURPOSE_MISMATCH = "PURPOSE_MISMATCH"
    INVALID_TRANSITION = "INVALID_TRANSITION"
    INVALID_DEADLINE = "INVALID_DEADLINE"
    DEADLINE_EXPIRED = "DEADLINE_EXPIRED"
    INVALID_LIMIT = "INVALID_LIMIT"
    TARGET_REFUSED = "TARGET_REFUSED"
    GATE_ABSENT = "GATE_ABSENT"
    EVIDENCE_MISSING = "EVIDENCE_MISSING"
    CONTRACT_VIOLATION = "CONTRACT_VIOLATION"
    OPERATION_FAILED = "OPERATION_FAILED"
    CLEANUP_FAILED = "CLEANUP_FAILED"


class ContractError(ValueError):
    """Fixed diagnostic code only: never retain supplied values or exceptions."""

    def __init__(self, code: ErrorCode = ErrorCode.INVALID_CONTRACT):
        self.code = code if type(code) is ErrorCode else ErrorCode.INVALID_CONTRACT
        super().__init__(self.code.value)


def _require(condition: bool, code: ErrorCode = ErrorCode.INVALID_CONTRACT) -> None:
    if not condition:
        raise ContractError(code)


def _token(value: str) -> None:
    _require(type(value) is str and re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", value) is not None)


def _digest(value: str) -> None:
    _require(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None)


def _uuid(value: str) -> None:
    _require(type(value) is str and re.fullmatch(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", value
    ) is not None and value != "00000000-0000-0000-0000-000000000000")


def _positive_int(value: int, ceiling: int) -> None:
    _require(type(value) is int and 0 < value <= ceiling, ErrorCode.INVALID_LIMIT)


def _finite(value: float) -> bool:
    # Bound before math conversion, including adversarially large Python ints.
    return type(value) in (int, float) and -1e300 <= value <= 1e300 and isfinite(value)


class Purpose(str, Enum):
    RUNTIME = "runtime"
    VERIFIER = "verifier"
    MIGRATOR = "migrator"
    ADMIN = "admin"


@dataclass(frozen=True, slots=True)
class VMGeneration:
    vm_id: int = field(repr=False)
    generation: str = field(repr=False)
    attestation_digest: str = field(repr=False)

    def __post_init__(self) -> None:
        _positive_int(self.vm_id, 2**31 - 1)
        _uuid(self.generation)
        _digest(self.attestation_digest)


@dataclass(frozen=True, slots=True)
class ClusterIdentity:
    system_identifier: str = field(repr=False)
    server_version_num: int

    def __post_init__(self) -> None:
        value = self.system_identifier
        _require(type(value) is str and re.fullmatch(r"[1-9][0-9]{0,19}", value) is not None)
        _require(int(value) <= 2**64 - 1)
        _require(type(self.server_version_num) is int and 160000 <= self.server_version_num < 170000)


@dataclass(frozen=True, slots=True)
class DatabaseIdentity:
    cluster: ClusterIdentity = field(repr=False)
    name: str = field(repr=False)
    oid: int = field(repr=False)

    def __post_init__(self) -> None:
        _require(type(self.cluster) is ClusterIdentity)
        _token(self.name)
        _positive_int(self.oid, 2**32 - 1)


@dataclass(frozen=True, slots=True)
class EnvironmentIdentity:
    environment_id: str = field(repr=False)
    vm: VMGeneration = field(repr=False)
    cluster: ClusterIdentity = field(repr=False)
    database: DatabaseIdentity = field(repr=False)

    def __post_init__(self) -> None:
        _token(self.environment_id)
        _require(re.fullmatch(r"g4-[a-z0-9][a-z0-9_-]*", self.environment_id) is not None)
        _require(type(self.vm) is VMGeneration and type(self.cluster) is ClusterIdentity)
        _require(type(self.database) is DatabaseIdentity)
        _require(self.database.cluster == self.cluster, ErrorCode.IDENTITY_MISMATCH)


@dataclass(frozen=True, slots=True)
class RunIdentity:
    environment: EnvironmentIdentity = field(repr=False)
    run_id: str = field(repr=False)

    def __post_init__(self) -> None:
        _require(type(self.environment) is EnvironmentIdentity)
        _uuid(self.run_id)


@dataclass(frozen=True, slots=True)
class CredentialIdentity:
    """Reference/provenance only. There is no field for credential material."""

    environment: EnvironmentIdentity = field(repr=False)
    purpose: Purpose
    role: str = field(repr=False)
    reference: str = field(repr=False)
    issuer: str = field(repr=False)

    def __post_init__(self) -> None:
        _require(type(self.environment) is EnvironmentIdentity and type(self.purpose) is Purpose)
        for value in (self.role, self.reference, self.issuer):
            _token(value)


@dataclass(frozen=True, slots=True)
class SessionIdentity:
    """Expected or reported session data, never proof of a physical connection."""

    run: RunIdentity = field(repr=False)
    credential: CredentialIdentity = field(repr=False)
    purpose: Purpose
    current_role: str = field(repr=False)
    session_role: str = field(repr=False)
    backend_pid: int = field(repr=False)
    backend_start_us: int = field(repr=False)

    def __post_init__(self) -> None:
        _require(type(self.run) is RunIdentity and type(self.credential) is CredentialIdentity)
        _require(type(self.purpose) is Purpose)
        _require(self.run.environment == self.credential.environment, ErrorCode.IDENTITY_MISMATCH)
        _require(self.purpose is self.credential.purpose, ErrorCode.PURPOSE_MISMATCH)
        _token(self.current_role)
        _token(self.session_role)
        _require(self.current_role == self.session_role == self.credential.role,
                 ErrorCode.IDENTITY_MISMATCH)
        _positive_int(self.backend_pid, 2**31 - 1)
        _positive_int(self.backend_start_us, 2**63 - 1)


def validate_readiness_pair(runtime: SessionIdentity, verifier: SessionIdentity) -> None:
    _require(type(runtime) is SessionIdentity and type(verifier) is SessionIdentity)
    _require(runtime.purpose is Purpose.RUNTIME and verifier.purpose is Purpose.VERIFIER,
             ErrorCode.PURPOSE_MISMATCH)
    _require(runtime.run == verifier.run, ErrorCode.IDENTITY_MISMATCH)
    _require(runtime.credential.role != verifier.credential.role
             and runtime.credential.reference != verifier.credential.reference,
             ErrorCode.IDENTITY_MISMATCH)
    _require(runtime.backend_pid != verifier.backend_pid, ErrorCode.IDENTITY_MISMATCH)


class RequestState(str, Enum):
    RECEIVED = "RECEIVED"
    PREVALIDATING = "PREVALIDATING"
    BLOCKED = "BLOCKED"
    CLOSED = "CLOSED"


class PrevalidationState(str, Enum):
    PENDING = "PENDING"
    VALID = "VALID"
    REJECTED = "REJECTED"


class AuthorizationState(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    REFERENCED = "REFERENCED"
    BLOCKED = "BLOCKED"
    REJECTED = "REJECTED"


class SessionState(str, Enum):
    NEW = "NEW"
    OPEN = "OPEN"
    ATTESTED = "ATTESTED"
    CLOSING = "CLOSING"
    CLOSED = "CLOSED"
    UNKNOWN = "UNKNOWN"


class EvidenceState(str, Enum):
    EMPTY = "EMPTY"
    STREAMING = "STREAMING"
    EOF = "EOF"
    SEALED = "SEALED"
    REJECTED = "REJECTED"


class EvaluationState(str, Enum):
    PENDING = "PENDING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class CancellationState(str, Enum):
    NOT_REQUESTED = "NOT_REQUESTED"
    REQUESTED = "REQUESTED"
    CONFIRMED = "CONFIRMED"
    UNKNOWN = "UNKNOWN"


class CleanupState(str, Enum):
    PENDING = "PENDING"
    ATTEMPTED = "ATTEMPTED"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


class ReconciliationState(str, Enum):
    NOT_REQUIRED = "NOT_REQUIRED"
    REQUIRED = "REQUIRED"
    REVIEWED = "REVIEWED"
    CLOSED = "CLOSED"
    UNRESOLVED = "UNRESOLVED"


class FinalState(str, Enum):
    PENDING = "PENDING"
    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"
    OP_ERROR = "OP_ERROR"


PhaseState = (RequestState | PrevalidationState | AuthorizationState | SessionState
              | EvidenceState | EvaluationState | CancellationState | CleanupState
              | ReconciliationState | FinalState)

# Terminal/unknown states cannot be silently recovered by another data transition.
# These graphs describe contracts, not operational actions or evidence issuance.
_EDGES = MappingProxyType({
    RequestState: frozenset({("RECEIVED", "PREVALIDATING"), ("RECEIVED", "BLOCKED"),
                            ("PREVALIDATING", "BLOCKED"), ("BLOCKED", "CLOSED")}),
    PrevalidationState: frozenset({("PENDING", "VALID"), ("PENDING", "REJECTED")}),
    AuthorizationState: frozenset({("UNVERIFIED", "REFERENCED"), ("UNVERIFIED", "BLOCKED"),
                                  ("UNVERIFIED", "REJECTED"), ("REFERENCED", "BLOCKED"),
                                  ("REFERENCED", "REJECTED")}),
    SessionState: frozenset({("NEW", "OPEN"), ("NEW", "UNKNOWN"), ("OPEN", "ATTESTED"),
                            ("OPEN", "CLOSING"), ("OPEN", "UNKNOWN"), ("ATTESTED", "CLOSING"),
                            ("ATTESTED", "UNKNOWN"), ("CLOSING", "CLOSED"), ("CLOSING", "UNKNOWN")}),
    EvidenceState: frozenset({("EMPTY", "STREAMING"), ("EMPTY", "REJECTED"),
                             ("STREAMING", "EOF"), ("STREAMING", "REJECTED"),
                             ("EOF", "SEALED"), ("EOF", "REJECTED")}),
    EvaluationState: frozenset({("PENDING", "PASSED"), ("PENDING", "FAILED"), ("PENDING", "BLOCKED")}),
    CancellationState: frozenset({("NOT_REQUESTED", "REQUESTED"), ("REQUESTED", "CONFIRMED"),
                                 ("REQUESTED", "UNKNOWN")}),
    CleanupState: frozenset({("PENDING", "ATTEMPTED"), ("ATTEMPTED", "VERIFIED"),
                            ("ATTEMPTED", "FAILED"), ("ATTEMPTED", "UNKNOWN")}),
    ReconciliationState: frozenset({("NOT_REQUIRED", "REQUIRED"), ("REQUIRED", "REVIEWED"),
                                   ("REVIEWED", "CLOSED"), ("REVIEWED", "UNRESOLVED")}),
    # No PASS transition exists in I1: no authenticated operational gate exists.
    FinalState: frozenset({("PENDING", "FAIL"), ("PENDING", "BLOCKED"), ("PENDING", "OP_ERROR")}),
})


def transition(current: PhaseState, following: PhaseState) -> PhaseState:
    _require(type(current) in _EDGES and type(following) is type(current),
             ErrorCode.INVALID_TRANSITION)
    _require((current.value, following.value) in _EDGES[type(current)], ErrorCode.INVALID_TRANSITION)
    return following


@dataclass(frozen=True, slots=True)
class ExecutionLimits:
    """Logical ceilings only. No physical timeout/resource guarantee is made."""

    connect_seconds: float = 2.0
    statement_ms: int = 500
    heavy_statement_ms: int = 1000
    lock_ms: int = 200
    idle_transaction_ms: int = 1000
    logical_seconds: float = 4.0
    canonical_bytes: int = 32 * 1024 * 1024

    def __post_init__(self) -> None:
        for value, ceiling in ((self.connect_seconds, 2.0), (self.logical_seconds, 4.0)):
            _require(_finite(value) and 0 < value <= ceiling,
                     ErrorCode.INVALID_LIMIT)
        for value, ceiling in ((self.statement_ms, 500), (self.heavy_statement_ms, 1000),
                               (self.lock_ms, 200), (self.idle_transaction_ms, 1000),
                               (self.canonical_bytes, 32 * 1024 * 1024)):
            _positive_int(value, ceiling)
        _require(self.lock_ms <= self.statement_ms <= self.heavy_statement_ms,
                 ErrorCode.INVALID_LIMIT)


@dataclass(frozen=True, slots=True)
class EvidenceLimits:
    max_rows: int
    max_bytes: int

    def __post_init__(self) -> None:
        _positive_int(self.max_rows, 262144)
        _positive_int(self.max_bytes, 32 * 1024 * 1024)


@dataclass(frozen=True, slots=True)
class ResourceLimits:
    """Unfixed parameters are explicit None, never unlimited operational defaults."""

    memory_bytes: int | None = None
    ipc_bytes: int | None = None
    frame_bytes: int | None = None

    def __post_init__(self) -> None:
        values = (self.memory_bytes, self.ipc_bytes, self.frame_bytes)
        _require(all(value is None for value in values) or all(value is not None for value in values),
                 ErrorCode.INVALID_LIMIT)
        for value in values:
            if value is not None:
                _positive_int(value, 2**63 - 1)
        if self.memory_bytes is not None:
            _require(self.frame_bytes <= self.ipc_bytes <= self.memory_bytes, ErrorCode.INVALID_LIMIT)


@dataclass(frozen=True, slots=True)
class Deadline:
    """Caller supplies monotonic readings; this type never reads any clock."""

    started: float
    expires: float
    clock_domain: str = field(repr=False)

    def __post_init__(self) -> None:
        _token(self.clock_domain)
        _require(all(_finite(value)
                     for value in (self.started, self.expires)), ErrorCode.INVALID_DEADLINE)
        _require(0 <= self.started < self.expires and self.expires - self.started <= 4,
                 ErrorCode.INVALID_DEADLINE)

    def remaining(self, now: float, *, clock_domain: str) -> float:
        _require(type(clock_domain) is str and clock_domain == self.clock_domain,
                 ErrorCode.INVALID_DEADLINE)
        _require(_finite(now) and now >= self.started,
                 ErrorCode.INVALID_DEADLINE)
        _require(now < self.expires, ErrorCode.DEADLINE_EXPIRED)
        return self.expires - now


@dataclass(frozen=True, slots=True)
class FailureRecord:
    verdict: Verdict
    code: ErrorCode

    def __post_init__(self) -> None:
        _require(type(self.verdict) is Verdict and type(self.code) is ErrorCode)
        expected = {
            ErrorCode.CONTRACT_VIOLATION: Verdict.FAIL,
            ErrorCode.IDENTITY_MISMATCH: Verdict.FAIL,
            ErrorCode.PURPOSE_MISMATCH: Verdict.FAIL,
            ErrorCode.OPERATION_FAILED: Verdict.OP_ERROR,
            ErrorCode.CLEANUP_FAILED: Verdict.OP_ERROR,
            ErrorCode.DEADLINE_EXPIRED: Verdict.OP_ERROR,
        }.get(self.code, Verdict.BLOCKED)
        _require(self.verdict is expected)


@dataclass(frozen=True, slots=True)
class FailureChain:
    primary: FailureRecord
    secondary: tuple[FailureRecord, ...] = ()

    def __post_init__(self) -> None:
        _require(type(self.primary) is FailureRecord and type(self.secondary) is tuple)
        _require(all(type(value) is FailureRecord for value in self.secondary))

    def append(self, failure: FailureRecord) -> "FailureChain":
        _require(type(failure) is FailureRecord)
        return FailureChain(self.primary, (*self.secondary, failure))


@dataclass(frozen=True, slots=True)
class ApprovalCandidate:
    environment: EnvironmentIdentity = field(repr=False)
    source_digest: str = field(repr=False)

    def __post_init__(self) -> None:
        _require(type(self.environment) is EnvironmentIdentity)
        _digest(self.source_digest)


@dataclass(frozen=True, slots=True)
class ExternalApprovalReference:
    """Unauthenticated external reference; signature validation is outside I1."""

    candidate: ApprovalCandidate = field(repr=False)
    reference: str = field(repr=False)
    issuer: str = field(repr=False)

    def __post_init__(self) -> None:
        _require(type(self.candidate) is ApprovalCandidate)
        _token(self.reference)
        _token(self.issuer)


@dataclass(frozen=True, slots=True)
class ApprovedContract:
    """Approval claim only, not a capability; it remains UNVERIFIED in I1."""

    candidate: ApprovalCandidate = field(repr=False)
    approval: ExternalApprovalReference = field(repr=False)
    state: AuthorizationState = field(default=AuthorizationState.UNVERIFIED, init=False)

    def __post_init__(self) -> None:
        _require(type(self.candidate) is ApprovalCandidate and type(self.approval) is ExternalApprovalReference)
        _require(self.approval.candidate == self.candidate, ErrorCode.IDENTITY_MISMATCH)


@dataclass(frozen=True, slots=True)
class ExecutionRequest:
    run: RunIdentity = field(repr=False)
    requested_environment: str = field(repr=False)
    purpose: Purpose

    def __post_init__(self) -> None:
        _require(type(self.run) is RunIdentity and type(self.purpose) is Purpose)
        _token(self.requested_environment)


@dataclass(frozen=True, slots=True)
class AuthorizedExecutionRequest:
    """Claimed authorization data. Construction/deserialization grants nothing."""

    request: ExecutionRequest = field(repr=False)
    contract: ApprovedContract = field(repr=False)
    state: AuthorizationState = field(default=AuthorizationState.BLOCKED, init=False)

    def __post_init__(self) -> None:
        _require(type(self.request) is ExecutionRequest and type(self.contract) is ApprovedContract)
        _require(self.request.run.environment == self.contract.candidate.environment,
                 ErrorCode.IDENTITY_MISMATCH)
        _require(self.request.requested_environment == self.contract.candidate.environment.environment_id,
                 ErrorCode.IDENTITY_MISMATCH)


@dataclass(frozen=True, slots=True)
class BoundaryDecision:
    """I1 can issue only a refusal. Even this result is not an authority token."""

    code: ErrorCode
    verdict: Verdict = field(default=Verdict.BLOCKED, init=False)

    def __post_init__(self) -> None:
        _require(type(self.code) is ErrorCode and self.code in (ErrorCode.GATE_ABSENT, ErrorCode.TARGET_REFUSED))


def execution_boundary(
    request: ExecutionRequest,
    *,
    expected: EnvironmentIdentity,
    authorization: AuthorizedExecutionRequest | None = None,
) -> BoundaryDecision:
    """Pure refusal before I/O. No configuration or approval record opens I1."""
    _require(type(request) is ExecutionRequest and type(expected) is EnvironmentIdentity)
    if request.run.environment != expected or request.requested_environment != expected.environment_id:
        return BoundaryDecision(ErrorCode.TARGET_REFUSED)
    # Deliberately never inspect or trust supplied authorization claims.
    return BoundaryDecision(ErrorCode.GATE_ABSENT)
