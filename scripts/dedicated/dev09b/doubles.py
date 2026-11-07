"""ONLY in-memory synthetic doubles. No durability or operational admission.

Thread locks model linearization within ONE process. They do not establish
PostgreSQL concurrency, crash durability, independent administration or C4.
Fixture approvals are loaded, never operationally issued or signed here.
"""
from threading import Lock

from .codec import (canonical, parse, validate_payload, require, uuid, digest_text, integer,
                    inspect_bindings, digest, validate_plan)
from .model import (ApprovalState, ContinuitySample, TimeSample, SessionBinding,
                    OfflineObservation)


class MemoryClock:
    def __init__(self, lower=100, upper=100, trustworthy=True):
        self.value = TimeSample(lower, upper, trustworthy)

    def sample(self):
        return self.value


class IndependentContinuityDouble:
    """Stored separately from the restorable authority model, not an epoch."""
    def __init__(self, token):
        self.value = ContinuitySample(token, True)

    def sample(self):
        return self.value


class MemoryAuthority:
    def __init__(self, *, clock, continuity, authority_epoch=1, revocation_epoch=1):
        integer(authority_epoch, 1)
        integer(revocation_epoch, 1)
        self.authority_epoch = authority_epoch
        self.revocation_epoch = revocation_epoch
        self.clock = clock
        self.continuity = continuity
        sample = continuity.sample()
        sample.validate()
        self.continuity_token = sample.token
        self.continuity_blocked = False
        self.available = True
        self.lock = Lock()
        self._approvals = {}
        self._attempts = {}
        self._revoked = set()
        self._revoked_identities = set()
        self._unusable = set()
        self._nonces = set()
        self._last_time = None
        self._events = []

    def load_fixture(self, payload, target, executor, plan):
        """Trusted synthetic fixture setup, NOT approval verification/issuance."""
        validate_payload(payload)
        inspect_bindings(payload, target, executor, plan)
        with self.lock:
            self._continuity()
            require(payload["authority_epoch"] == self.authority_epoch
                    and payload["revocation_epoch"] == self.revocation_epoch)
            key = payload["approval_id"]
            require(key not in self._approvals)
            # Store an immutable snapshot so later caller mutation cannot change bindings.
            self._approvals[key] = [canonical(payload), ApprovalState.AVAILABLE, None,
                                    digest("executor", executor), executor["incarnation_id"]]

    def _continuity(self):
        require(self.available)
        try:
            sample = self.continuity.sample()
            sample.validate()
            require(sample.token == self.continuity_token)
        except Exception:
            self.continuity_blocked = True
            raise
        require(not self.continuity_blocked)

    def _eligible(self, key):
        self._continuity()
        require(key in self._approvals and key not in self._unusable)
        raw, state, session = self._approvals[key][:3]
        p = parse(raw)
        require(p["authority_epoch"] == self.authority_epoch
                and p["revocation_epoch"] == self.revocation_epoch)
        require(not any((kind, p[field]) in self._revoked_identities for kind, field in
                        (("key", "key_id"), ("issuer", "issuer_id"), ("policy", "trust_policy_version"))))
        require(key not in self._revoked and state not in {ApprovalState.REVOKED, ApprovalState.EXPIRED})
        t = self.clock.sample()
        t.validate()
        require(self._last_time is None or t.lower >= self._last_time)
        self._last_time = t.lower
        if t.upper >= p["expires_at"]:
            if t.lower >= p["expires_at"] and state is ApprovalState.AVAILABLE:
                self._approvals[key][1] = ApprovalState.EXPIRED
            require(False)
        require(t.lower >= p["not_before"])
        return p

    def _nonce(self, nonce):
        uuid(nonce)
        require(nonce not in self._nonces)
        self._nonces.add(nonce)

    def consume(self, approval_id, session, nonce):
        with self.lock:
            self._nonce(nonce)
            p = self._eligible(approval_id)
            require(type(session) is SessionBinding)
            session.validate()
            require(session.target_sha256 == p["target_binding_sha256"])
            require(session.executor_sha256 == self._approvals[approval_id][3]
                    and session.incarnation_id == self._approvals[approval_id][4])
            require(self._approvals[approval_id][1] is ApprovalState.AVAILABLE)
            require(p["attempt_id"] not in self._attempts)
            self._approvals[approval_id][1:3] = [ApprovalState.CONSUMED, session]
            self._attempts[p["attempt_id"]] = approval_id
            return OfflineObservation(p["attempt_id"], "consume", nonce)

    def check(self, attempt_id, phase, session, nonce):
        with self.lock:
            self._nonce(nonce)
            require(phase in {"first_effect", "before_commit"} and attempt_id in self._attempts)
            key = self._attempts[attempt_id]
            p = self._eligible(key)
            require(p["attempt_id"] == attempt_id and self._approvals[key][1] is ApprovalState.CONSUMED)
            require(session == self._approvals[key][2])
            return OfflineObservation(attempt_id, phase, nonce)

    def status(self, approval_id, nonce):
        with self.lock:
            require(self.available and approval_id in self._approvals)
            self._nonce(nonce)
            # Status is deliberately not a continuity/admission check or permission.
            row = self._approvals[approval_id]
            return (row[1], approval_id in self._revoked, approval_id in self._unusable)

    def record(self, attempt_id, event, evidence_sha256):
        with self.lock:
            require(self.available and attempt_id in self._attempts)
            require(event in {"commit_intent", "rollback_attempt", "close", "independent_reconciliation"})
            digest_text(evidence_sha256)
            self._events.append((attempt_id, event, evidence_sha256))

    def revoke_fixture(self, approval_id):
        with self.lock:
            require(approval_id in self._approvals)
            self._revoked.add(approval_id)
            if self._approvals[approval_id][1] is ApprovalState.AVAILABLE:
                self._approvals[approval_id][1] = ApprovalState.REVOKED

    def revoke_identity_fixture(self, kind, identity):
        """Synthetic revocation indication, not a trust-store implementation."""
        from .codec import identifier
        require(kind in {"key", "issuer", "policy"})
        identifier(identity)
        with self.lock:
            self._revoked_identities.add((kind, identity))

    def reconcile_fixture(self, *, complete):
        """Explicit synthetic reconciliation; never a self-issued continuity claim."""
        require(type(complete) is bool)
        with self.lock:
            require(self.available and self.continuity_blocked)
            sample = self.continuity.sample()
            sample.validate()
            if not complete:
                # Independent new continuity is mandatory; a local epoch bump
                # alone is insufficient. Retire the WHOLE prior epoch, including
                # approvals missing from a restored/incomplete fixture store.
                require(sample.token != self.continuity_token)
                self._unusable.update(self._approvals)
                self.authority_epoch += 1
            # Restored records alone cannot provide this independent indication.
            self.continuity_token = sample.token
            self.continuity_blocked = False


class MemoryExecutor:
    """Records simulated calls only. Never opens a session or dispatches work."""
    def __init__(self, session):
        session.validate()
        self.session = session
        self.events = []

    def prepare(self, plan):
        validate_plan(parse(plan))
        self.events.append("synthetic_prepare")
        return self.session

    def run(self, observation):
        require(type(observation) is OfflineObservation)
        self.events.append("synthetic_run")

    def abort(self):
        self.events.append("synthetic_rollback")

    def close(self):
        self.events.append("synthetic_close")
