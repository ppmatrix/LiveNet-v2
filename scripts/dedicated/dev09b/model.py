"""Abstract offline interfaces and monotonic attempt state machine.

No method dispatches SQL or calls a runner. Checkpoint validity is not validity
at a physical effect. Availability of containment never depends on authority.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from .codec import decimal64, integer, require, uuid


class ApprovalState(str, Enum):
    AVAILABLE = "AVAILABLE"
    CONSUMED = "CONSUMED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"

    @property
    def terminal(self):
        return self is not ApprovalState.AVAILABLE


class AttemptState(str, Enum):
    CONSUMED_NOT_STARTED = "CONSUMED_NOT_STARTED"
    RUNNING = "RUNNING"
    COMMIT_INTENT = "COMMIT_INTENT"
    ABORTING = "ABORTING"
    COMMITTED_CONFIRMED = "COMMITTED_CONFIRMED"
    ROLLED_BACK_CONFIRMED = "ROLLED_BACK_CONFIRMED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class TimeSample:
    lower: int
    upper: int
    trustworthy: bool

    def validate(self):
        integer(self.lower)
        integer(self.upper)
        require(type(self.trustworthy) is bool and self.trustworthy and self.lower <= self.upper)


@dataclass(frozen=True)
class ContinuitySample:
    """Indication from an INDEPENDENT interface, never an epoch in restored DB."""
    token: str
    confirmed: bool

    def validate(self):
        uuid(self.token)
        require(type(self.confirmed) is bool and self.confirmed)


@dataclass(frozen=True)
class SessionBinding:
    target_sha256: str
    executor_sha256: str
    incarnation_id: str
    backend_pid: int
    backend_start: int
    transaction_id: str

    def validate(self):
        from .codec import digest_text
        digest_text(self.target_sha256)
        digest_text(self.executor_sha256)
        uuid(self.incarnation_id)
        integer(self.backend_pid, 1)
        integer(self.backend_start)
        decimal64(self.transaction_id)


@dataclass(frozen=True)
class OfflineObservation:
    """An observation in a simulation, NEVER an operational capability."""
    attempt_id: str
    phase: str
    nonce: str


class Clock(Protocol):
    def sample(self) -> TimeSample: ...


class Continuity(Protocol):
    def sample(self) -> ContinuitySample: ...


class Authority(Protocol):
    def consume(self, approval_id: str, session: SessionBinding, nonce: str) -> OfflineObservation: ...
    def check(self, attempt_id: str, phase: str, session: SessionBinding, nonce: str) -> OfflineObservation: ...
    def status(self, approval_id: str, nonce: str) -> tuple: ...
    def record(self, attempt_id: str, event: str, evidence_sha256: str) -> None: ...


class Executor(Protocol):
    """Future port only. This package implements no operational executor."""
    def prepare(self, plan: bytes) -> SessionBinding: ...
    def run(self, observation: OfflineObservation) -> None: ...
    def abort(self) -> None: ...
    def close(self) -> None: ...


class OfflineAttempt:
    """Local transition model: events only, no calls to an Executor port.

    Authority failures never inhibit abort()/close(). Local UNKNOWN is retained
    even if an authority event cannot be recorded. Confirmation flags represent
    synthetic independent evidence, not real reconciliation.
    """
    def __init__(self, authority: Authority, approval_id, session, nonce):
        session.validate()
        observation = authority.consume(approval_id, session, nonce)
        require(type(observation) is OfflineObservation)
        require(observation.phase == "consume" and observation.nonce == nonce)
        self.authority = authority
        self.session = session
        self.attempt_id = observation.attempt_id
        self.state = AttemptState.CONSUMED_NOT_STARTED
        self.commit_sent = False
        self.closed = False
        self.events = []

    def _checkpoint(self, phase, session, nonce):
        require(not self.closed and session == self.session)
        result = self.authority.check(self.attempt_id, phase, session, nonce)
        require(type(result) is OfflineObservation and result.attempt_id == self.attempt_id
                and result.phase == phase and result.nonce == nonce)
        return result

    def first_effect(self, session, nonce):
        require(self.state is AttemptState.CONSUMED_NOT_STARTED)
        try:
            self._checkpoint("first_effect", session, nonce)
        except Exception:
            self.abort()
            raise
        self.state = AttemptState.RUNNING
        self.events.append("simulated_first_effect")

    def before_commit(self, session, nonce):
        require(self.state is AttemptState.RUNNING)
        try:
            self._checkpoint("before_commit", session, nonce)
            from hashlib import sha256
            evidence = sha256((self.attempt_id + ":commit_intent").encode("ascii")).hexdigest()
            self.authority.record(self.attempt_id, "commit_intent", evidence)
        except Exception:
            self.abort()
            raise
        self.state = AttemptState.COMMIT_INTENT
        self.events.append("simulated_commit_intent")

    def simulate_commit_dispatch(self, session, nonce):
        # Recheck on simulated dispatch as well: no cached observation permits
        # dispatch after time, revocation, session or continuity has changed.
        require(self.state is AttemptState.COMMIT_INTENT)
        try:
            self._checkpoint("before_commit", session, nonce)
        except Exception:
            self.abort()
            raise
        self.commit_sent = True
        self.state = AttemptState.UNKNOWN
        self.events.append("simulated_commit_sent_result_unknown")

    def abort(self):
        # Containment is local, even with unavailable authority/time/continuity.
        if self.state not in {AttemptState.COMMITTED_CONFIRMED, AttemptState.ROLLED_BACK_CONFIRMED}:
            # Containment must not erase an already uncertain result. UNKNOWN
            # can only be resolved by independently confirmed reconciliation.
            self.state = (AttemptState.UNKNOWN if self.commit_sent or self.state is AttemptState.UNKNOWN
                          else AttemptState.ABORTING)
            self.events.append("simulated_rollback_attempt")

    def close(self):
        self.closed = True
        if self.state not in {AttemptState.COMMITTED_CONFIRMED, AttemptState.ROLLED_BACK_CONFIRMED}:
            self.state = AttemptState.UNKNOWN
        self.events.append("simulated_close")

    def rollback_result(self, *, transaction_confirmed, independent_confirmed):
        require(type(transaction_confirmed) is bool and type(independent_confirmed) is bool)
        require(self.state in {AttemptState.ABORTING, AttemptState.UNKNOWN} and not self.commit_sent)
        self.state = (AttemptState.ROLLED_BACK_CONFIRMED if transaction_confirmed and independent_confirmed
                      else AttemptState.UNKNOWN)

    def reconcile(self, outcome, *, independent_confirmed):
        require(self.state is AttemptState.UNKNOWN and independent_confirmed is True)
        require(type(outcome) is AttemptState and outcome in {
            AttemptState.COMMITTED_CONFIRMED, AttemptState.ROLLED_BACK_CONFIRMED})
        self.state = outcome
