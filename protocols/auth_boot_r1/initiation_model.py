"""R1-PROTO-02: deterministic, in-memory counterexamples and conditional proofs.

NOT an executor, authorization service, persistence implementation or SQL adapter.
Each method is one serialized model event. IDEAL mode explicitly assumes an
atomic authority-check/first-effect boundary which a remote query DOES NOT give.
All identities, receipts, clocks and persistence below are synthetic assumptions.
"""

from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum


class Refused(ValueError):
    pass


class AuthorityState(str, Enum):
    ISSUED = "ISSUED"
    CLAIMED = "CLAIMED"
    CONSUMED = "CONSUMED_FOR_ATTEMPT"


class Stage(str, Enum):
    WAITING = "WAITING"
    STARTED = "STARTED"
    COMMITTED = "COMMITTED_MODEL_ONLY"
    ROLLED_BACK = "ROLLED_BACK_MODEL_ONLY"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN/BLOCKED"


class Mode(str, Enum):
    PRECHECK = "PRECHECK_ONLY_NEGATIVE_CONTROL"
    TARGET_LOCAL = "TARGET_LOCAL_RESERVATION_AND_CHECK"
    IDEAL = "IDEAL_ATOMIC_AUTHORITY_AND_FIRST_EFFECT"


@dataclass(frozen=True)
class Context:
    approval: str = "synthetic-approval"
    attempt: str = "synthetic-attempt"
    executor: str = "synthetic-executor"
    incarnation: str = "incarnation-1"
    session: str = "session-1"
    transaction: str = "transaction-1"
    target: str = "synthetic-target"
    generation: str = "generation-1"
    plan: str = "synthetic-plan-binding"


@dataclass(frozen=True)
class Interval:
    lower: int
    upper: int
    trusted: bool = True


@dataclass(frozen=True)
class Receipt:
    context: Context
    authority_epoch: int
    revocation_epoch: int


@dataclass
class Authority:
    state: AuthorityState = AuthorityState.ISSUED
    holder: Context | None = None
    receipt: Receipt | None = None
    authority_epoch: int = 1
    revocation_epoch: int = 1
    revoked: bool = False
    blocked: bool = False


@dataclass
class Target:
    name: str = "synthetic-target"
    generation: str = "generation-1"
    authority_epoch: int = 1
    revocation_epoch: int = 1
    revoked: bool = False
    # Assumed durable and OUTSIDE rollback of the protected transaction.
    reservations: set[tuple[str, str]] = field(default_factory=set)
    started: set[tuple[str, str]] = field(default_factory=set)
    blocked: bool = False
    locked: bool = False


@dataclass
class Execution:
    context: Context
    mode: Mode
    receipt: Receipt
    stage: Stage = Stage.WAITING


class Model:
    """One approval and attempt; executions may be replayed or cloned.

    effects is an observer's history, not a production ledger or commit proof.
    issued_at=not_before=0, expires_at=900; time units are synthetic seconds.
    Caller schedules events explicitly; no threads, clock reads or I/O.
    """

    def __init__(self):
        self.authority = Authority()
        self.target = Target()
        self.authority_time = Interval(0, 0)
        self.target_time = Interval(0, 0)
        self.approval_authority_epoch = 1
        self.approval_revocation_epoch = 1
        self.connected = True
        self.effects: list[Context] = []

    @staticmethod
    def _window(clock):
        return (clock.trusted and type(clock.lower) is int
                and type(clock.upper) is int and 0 <= clock.lower <= clock.upper < 900)

    def _authority_eligible(self):
        a = self.authority
        if (not self.connected or a.blocked or a.revoked
                or a.authority_epoch != self.approval_authority_epoch
                or a.revocation_epoch != self.approval_revocation_epoch
                or not self._window(self.authority_time)):
            raise Refused("AUTHORITY_INELIGIBLE_OR_UNAVAILABLE")

    def claim(self, context):
        self._authority_eligible()
        if self.authority.state is not AuthorityState.ISSUED:
            raise Refused("CLAIM_ALREADY_TAKEN")
        self.authority.holder = context
        self.authority.state = AuthorityState.CLAIMED

    def consume(self, context):
        self._authority_eligible()
        a = self.authority
        if a.state is not AuthorityState.CLAIMED or a.holder != context:
            raise Refused("CONSUMPTION_REFUSED")
        a.receipt = Receipt(context, a.authority_epoch, a.revocation_epoch)
        a.state = AuthorityState.CONSUMED
        return a.receipt

    def _receipt_matches_authority(self, receipt):
        a = self.authority
        if (a.state is not AuthorityState.CONSUMED or receipt != a.receipt
                or receipt.authority_epoch != a.authority_epoch
                or receipt.revocation_epoch != a.revocation_epoch):
            raise Refused("RECEIPT_NOT_CURRENT")

    def _target_eligible(self, receipt):
        t = self.target
        if (t.blocked or t.revoked or not self._window(self.target_time)
                or receipt.authority_epoch != t.authority_epoch
                or receipt.revocation_epoch != t.revocation_epoch):
            raise Refused("TARGET_LOCAL_CHECK_REFUSED")

    def dispatch(self, receipt, context, mode):
        if type(mode) is not Mode or type(receipt) is not Receipt:
            raise Refused("MODEL_INPUT_REFUSED")
        if context != receipt.context:
            raise Refused("CONTEXT_SUBSTITUTION")
        if (context.target != self.target.name
                or context.generation != self.target.generation or self.target.blocked):
            raise Refused("TARGET_OR_CONTINUITY_REFUSED")
        # Synthetic authenticity is assumed by exact match to the authority.
        # Even this fresh precheck will not suffice after a pause/lock wait.
        self._authority_eligible()
        self._receipt_matches_authority(receipt)
        if mode is not Mode.PRECHECK:
            self._target_eligible(receipt)
            key = (context.approval, context.attempt)
            if key in self.target.reservations:
                raise Refused("ATTEMPT_ALREADY_RESERVED")
            self.target.reservations.add(key)
        return Execution(context, mode, receipt)

    def first_effect(self, execution):
        if execution.stage is not Stage.WAITING:
            raise Refused("NO_AUTOMATIC_CONTINUATION")
        if (self.target.blocked or execution.context.target != self.target.name
                or execution.context.generation != self.target.generation):
            execution.stage = Stage.BLOCKED
            raise Refused("TARGET_OR_CONTINUITY_REFUSED")
        if self.target.locked:
            return False  # queue, not start; caller may advance time/revoke
        try:
            if execution.mode is not Mode.PRECHECK:
                receipt = execution.receipt
                if receipt.context != execution.context:
                    raise Refused("RECEIPT_UNAVAILABLE")
                self._target_eligible(receipt)
                key = (execution.context.approval, execution.context.attempt)
                if key not in self.target.reservations or key in self.target.started:
                    raise Refused("INITIATION_ALREADY_USED_OR_NOT_RESERVED")
                if execution.mode is Mode.IDEAL:
                    # This check AND the append below are ONE model event.
                    # No implementable distributed atomicity is claimed.
                    self._authority_eligible()
                    self._receipt_matches_authority(receipt)
                self.target.started.add(key)
        except Refused:
            execution.stage = Stage.BLOCKED
            raise
        self.effects.append(execution.context)
        execution.stage = Stage.STARTED
        return True

    def finish(self, execution, *, committed, confirmation):
        if execution.stage is not Stage.STARTED:
            raise Refused("EXECUTION_NOT_STARTED")
        if not confirmation:
            execution.stage = Stage.UNKNOWN
        else:
            execution.stage = Stage.COMMITTED if committed else Stage.ROLLED_BACK
        # Neither rollback nor lost confirmation releases a reservation/approval.

    def crash(self, execution):
        if execution.stage is Stage.STARTED:
            execution.stage = Stage.UNKNOWN
        elif execution.stage is Stage.WAITING:
            execution.stage = Stage.BLOCKED
        # Assumption: authoritative state and target reservation survive restart.

    def revoke(self):
        self.authority.revoked = True
        self.authority.revocation_epoch += 1

    def deliver_revocation(self):
        """Explicit delivery event; not automatic, fresh or partition-proof."""
        self.target.revoked = self.authority.revoked
        self.target.authority_epoch = self.authority.authority_epoch
        self.target.revocation_epoch = self.authority.revocation_epoch

    def snapshot(self):
        return deepcopy((self.authority, self.target))

    def restore(self, snapshot):
        """Fail closed: an internally consistent snapshot is not continuity."""
        self.authority, self.target = deepcopy(snapshot)
        self.authority.blocked = self.target.blocked = True

    def unsafe_restore_negative_control(self, snapshot):
        """Deliberately unsafe counterexample: restore without continuity proof."""
        self.authority, self.target = deepcopy(snapshot)

    def unsafe_clone_negative_control(self):
        """A clone with the same identities/state can race the original."""
        clone = deepcopy(self)
        clone.effects = self.effects  # independent observer sees both initiations
        return clone
