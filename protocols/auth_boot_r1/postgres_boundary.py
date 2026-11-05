"""R1-PROTO-03: local PostgreSQL boundary hypotheses, NOT a DB implementation.

No SQL is executed. Each method is a deterministic event in memory. Commit,
unique-key waiting and durability are modeled, not verified against PostgreSQL.
The counterexample class is deliberately unsafe and must never serve a gate.
"""

from dataclasses import dataclass

from protocols.auth_boot_r1.initiation_model import Context, Refused


@dataclass(frozen=True)
class Marker:
    authority: str
    context: Context


class WouldWait(Refused):
    """Another transaction has a conflicting, uncommitted unique key."""


class MarkerStudy:
    """One reservation per synthetic transaction, two global uniqueness keys.

    A committed marker is BURNED, not proof of initiation/commit/authorization.
    No release, update, resume or retry interface exists. A model restart reuses
    committed state; snapshot/clone continuity is outside this local guarantee.
    """

    def __init__(self):
        self.committed: list[Marker] = []
        self.pending: dict[str, Marker] = {}

    @staticmethod
    def _conflicts(left, right):
        return (left.authority == right.authority
                and (left.context.approval == right.context.approval
                     or left.context.attempt == right.context.attempt))

    def reserve(self, transaction, marker):
        if transaction in self.pending:
            raise Refused("TRANSACTION_ALREADY_HAS_RESERVATION")
        if any(self._conflicts(marker, old) for old in self.committed):
            raise Refused("DURABLY_BURNED")
        if any(self._conflicts(marker, old) for old in self.pending.values()):
            raise WouldWait("UNCOMMITTED_UNIQUE_CONFLICT")
        self.pending[transaction] = marker

    def commit(self, transaction):
        self.committed.append(self.pending.pop(transaction))

    def rollback(self, transaction):
        self.pending.pop(transaction, None)

    def crash(self):
        self.pending.clear()  # committed durability is an explicit assumption


class CheckEffectCounterexample:
    """Even an in-server check/row lock need not coincide with first effect.

    Synthetic time and authority-request/local-application distinction are
    explicit. This does NOT redefine when R1 revocation is effective.
    """

    def __init__(self):
        self.now = 0
        self.transaction_started_at = 0
        self.row_lock_held = False
        self.revocation_requested = False
        self.target_revoked = False
        self.checked = False
        self.effects = 0

    def check(self, *, transaction_timestamp=False):
        observed = self.transaction_started_at if transaction_timestamp else self.now
        if self.target_revoked or not (0 <= observed < 900):
            raise Refused("LOCAL_CHECK_FAILED")
        self.checked = True

    def request_revocation(self):
        self.revocation_requested = True

    def try_apply_revocation_at_target(self):
        if self.row_lock_held:
            return False
        if self.revocation_requested:
            self.target_revoked = True
        return self.target_revoked

    def first_effect_after_check(self):
        if not self.checked:
            raise Refused("NO_CHECK")
        # Deliberately no new check: a pause/lock wait can intervene even after
        # clock_timestamp() inside a routine, trigger or preceding SQL statement.
        self.effects += 1
