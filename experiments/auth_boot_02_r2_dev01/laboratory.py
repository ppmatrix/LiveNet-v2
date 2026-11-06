"""R2-DEV-01 internal state-machine laboratory; no operational wire format."""

from contextlib import closing, contextmanager
from dataclasses import asdict, dataclass
import fcntl
import hashlib
import hmac
import json
from pathlib import Path
import sqlite3
from typing import Callable
import uuid


GENESIS = "0" * 64


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(encode(value).encode("utf-8")).hexdigest()


def connect(path):
    connection = sqlite3.connect(path, timeout=20, isolation_level=None)
    connection.execute("PRAGMA synchronous=FULL")
    connection.execute("PRAGMA journal_mode=DELETE")
    return connection


@dataclass(frozen=True)
class Binding:
    request_id: str
    attempt_id: str
    approver_id: str
    requester_id: str
    purpose: str
    operation: str
    gate: str
    environment: str
    execution_plan_sha256: str
    global_digest_sha256: str
    target_binding_sha256: str
    audience: str
    vm_generation_id: str
    executor_id: str
    executor_incarnation: str
    protected_session: str
    protected_transaction: str


@dataclass(frozen=True)
class Approval:
    approval_id: str
    binding: Binding
    issuer_id: str = "lab-authority"
    key_id: str = "lab-key"
    trust_policy_version: str = "lab-policy"
    authority_epoch: int = 1
    revocation_epoch: int = 1
    issued_at: int = 100
    not_before: int = 100
    expires_at: int = 200
    protocol_version: str = "2"


@dataclass(frozen=True)
class TimeInterval:
    lower: int
    upper: int
    trusted: bool = True
    continuous: bool = True


@dataclass(frozen=True)
class Outcome:
    status: str
    reason: str
    sequence: int | None = None
    admission: dict | None = None
    executable: bool = False


class Uncertain(Exception):
    pass


class WitnessDouble:
    """Separate durable SQLite copy and test HMAC; not independent administration."""

    def __init__(self, path, key):
        self.path = Path(path).resolve()
        self.key = key

    def provision(self, store_id, instance):
        with closing(connect(self.path)) as connection:
            connection.execute("CREATE TABLE checkpoint (document TEXT NOT NULL)")
            connection.execute("CREATE TABLE events (sequence INTEGER PRIMARY KEY, event TEXT NOT NULL)")
            connection.execute("INSERT INTO checkpoint VALUES (?)", (encode({
                "store_id": store_id, "instance": instance,
                "sequence": 0, "digest": GENESIS,
            }),))

    def checkpoint(self):
        with closing(connect(self.path)) as connection:
            row = connection.execute("SELECT document FROM checkpoint").fetchone()
            if row is None:
                raise Uncertain("witness checkpoint absent")
            checkpoint = json.loads(row[0])
            return checkpoint, self.sign(checkpoint)

    def sign(self, value):
        return hmac.new(self.key, encode(value).encode("utf-8"), hashlib.sha256).hexdigest()

    def record(self, store_id, instance, event):
        with closing(connect(self.path)) as connection:
            connection.execute("BEGIN IMMEDIATE")
            checkpoint = json.loads(connection.execute("SELECT document FROM checkpoint").fetchone()[0])
            if (checkpoint["store_id"] != store_id or checkpoint["instance"] != instance
                    or checkpoint["sequence"] + 1 != event["sequence"]
                    or checkpoint["digest"] != event["previous"]):
                raise Uncertain("witness order or incarnation mismatch")
            checkpoint.update(sequence=event["sequence"], digest=digest(event))
            connection.execute("INSERT INTO events VALUES (?, ?)", (event["sequence"], encode(event)))
            connection.execute("UPDATE checkpoint SET document = ?", (encode(checkpoint),))
            connection.commit()
        return checkpoint, self.sign(checkpoint)


class Authority:
    def __init__(self, path, witness, instance, clock: Callable[[], TimeInterval], verification_key):
        self.path = Path(path).resolve()
        self.witness = witness
        self.instance = instance
        self.clock = clock
        self.verification_key = verification_key
        if self.path == witness.path:
            raise ValueError("authority and witness must use different files")

    @classmethod
    def create(cls, path, witness, instance, clock, verification_key):
        path = Path(path).resolve()
        if path.exists() or witness.path.exists():
            raise ValueError("provisioning must never overwrite existing stores")
        authority = cls(path, witness, instance, clock, verification_key)
        state = {
            "store_id": str(uuid.uuid4()), "instance": instance,
            "authority_epoch": 1, "revocation_epoch": 1,
            "policy": "lab-policy", "approvals": {}, "admissions": {},
            "revocations": [], "last_lower": None,
        }
        with closing(connect(path)) as connection:
            connection.execute("CREATE TABLE state (document TEXT NOT NULL, quarantined INTEGER NOT NULL)")
            connection.execute("CREATE TABLE events (sequence INTEGER PRIMARY KEY, event TEXT NOT NULL)")
            connection.execute("INSERT INTO state VALUES (?, 0)", (encode(state),))
        witness.provision(state["store_id"], instance)
        return authority

    @contextmanager
    def locked(self):
        with self.path.with_suffix(".lock").open("a+b") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            connection = connect(self.path)
            try:
                connection.execute("BEGIN IMMEDIATE")
                yield connection
            finally:
                if connection.in_transaction:
                    connection.rollback()
                connection.close()
                fcntl.flock(lock, fcntl.LOCK_UN)

    def verify_ack(self, acknowledgement, expected):
        checkpoint, signature = acknowledgement
        expected_signature = hmac.new(
            self.verification_key, encode(checkpoint).encode("utf-8"), hashlib.sha256
        ).hexdigest()
        if checkpoint != expected or not hmac.compare_digest(signature, expected_signature):
            raise Uncertain("unconfirmed or unauthenticated witness")

    def checked_state(self, connection, observation=False):
        row = connection.execute("SELECT document, quarantined FROM state").fetchone()
        if row is None or (row[1] and not observation):
            raise Uncertain("quarantined; human reconciliation required")
        state = json.loads(row[0])
        previous = GENESIS
        sequence = 0
        final_state = None
        for recorded_sequence, serialized in connection.execute("SELECT sequence, event FROM events ORDER BY sequence"):
            event = json.loads(serialized)
            if recorded_sequence != sequence + 1 or event["sequence"] != recorded_sequence or event["previous"] != previous:
                raise Uncertain("broken authoritative history")
            sequence = recorded_sequence
            previous = digest(event)
            final_state = event["state"]
        if final_state is not None and final_state != state:
            raise Uncertain("state differs from essential evidence")
        if state["instance"] != self.instance:
            raise Uncertain("instance continuity unknown")
        expected = {"store_id": state["store_id"], "instance": self.instance,
                    "sequence": sequence, "digest": previous}
        self.verify_ack(self.witness.checkpoint(), expected)
        return state, sequence, previous

    def block(self, connection, reason):
        connection.rollback()
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("UPDATE state SET quarantined = 1")
        connection.commit()
        return Outcome("UNKNOWN/BLOCKED", reason)

    def transition(self, decide, fault=None):
        try:
            with self.locked() as connection:
                try:
                    state, sequence, previous = self.checked_state(connection)
                    decision = decide(state, sequence + 1)
                    if isinstance(decision, Outcome):
                        return decision
                    kind, details, result = decision
                    event = {"sequence": sequence + 1, "previous": previous,
                             "kind": kind, "details": details, "state": state}
                    connection.execute("UPDATE state SET document = ?", (encode(state),))
                    connection.execute("INSERT INTO events VALUES (?, ?)", (sequence + 1, encode(event)))
                    if fault is not None:
                        fault("before_commit")
                    connection.commit()
                    if fault is not None:
                        fault("after_commit")
                    acknowledgement = self.witness.record(state["store_id"], self.instance, event)
                    self.verify_ack(acknowledgement, {
                        "store_id": state["store_id"], "instance": self.instance,
                        "sequence": sequence + 1, "digest": digest(event),
                    })
                    if fault is not None:
                        fault("after_witness")
                    return result
                except (Uncertain, sqlite3.Error, OSError, ValueError, KeyError, TypeError) as error:
                    return self.block(connection, str(error))
        except (sqlite3.Error, OSError) as error:
            return Outcome("UNKNOWN/BLOCKED", str(error))

    def issue(self, approval):
        def decide(state, sequence):
            values = (approval.issued_at, approval.not_before, approval.expires_at,
                      approval.authority_epoch, approval.revocation_epoch)
            if approval.protocol_version != "2":
                return Outcome("DENIED", "version separation")
            if (any(type(value) is not int for value in values)
                    or not approval.issued_at <= approval.not_before < approval.expires_at
                    or approval.expires_at - approval.issued_at > 900):
                return Outcome("DENIED", "invalid validity or epoch values")
            document = asdict(approval)
            if any(not isinstance(value, str) or not value for value in document["binding"].values()):
                return Outcome("DENIED", "incomplete immutable binding")
            if approval.binding.operation != "LAB_FIXED_UPDATE":
                return Outcome("DENIED", "outside fixed laboratory operation")
            existing = state["approvals"].get(approval.approval_id)
            if existing is not None:
                return Outcome("DENIED", "approval ID already registered" if existing == document else "approval ID conflict")
            state["approvals"][approval.approval_id] = document
            return "ISSUED", {"approval_id": approval.approval_id}, Outcome("RECORDED", "issued", sequence)
        return self.transition(decide)

    def admit(self, approval_id, binding, fault=None):
        def decide(state, sequence):
            approval = state["approvals"].get(approval_id)
            if approval is None:
                return Outcome("DENIED", "unknown approval")
            if approval_id in state["admissions"]:
                return Outcome("DENIED", "consumed; query cannot renew permission")
            if approval["binding"] != asdict(binding):
                return Outcome("DENIED", "immutable binding mismatch")
            if (approval["authority_epoch"] != state["authority_epoch"]
                    or approval["revocation_epoch"] != state["revocation_epoch"]
                    or approval["trust_policy_version"] != state["policy"]):
                return Outcome("DENIED", "epoch or policy mismatch")
            for revocation in state["revocations"]:
                field = {"approval": "approval_id", "key": "key_id", "authority": "issuer_id", "policy": "trust_policy_version"}[revocation["scope"]]
                if approval[field] == revocation["subject"]:
                    return Outcome("DENIED", "revocation precedes A")
            interval = self.clock()
            if (not isinstance(interval, TimeInterval) or not interval.trusted or not interval.continuous
                    or type(interval.lower) is not int or type(interval.upper) is not int
                    or interval.lower > interval.upper
                    or (state["last_lower"] is not None and interval.lower < state["last_lower"])):
                raise Uncertain("time or temporal continuity unknown")
            if interval.lower < approval["not_before"] or interval.upper >= approval["expires_at"]:
                return Outcome("DENIED", "outside [L,U] eligibility at A")
            admission = {"approval_id": approval_id, "binding": asdict(binding),
                         "sequence": sequence, "interval": asdict(interval),
                         "authority_epoch": state["authority_epoch"],
                         "revocation_epoch": state["revocation_epoch"],
                         "policy": state["policy"], "consumed": True}
            state["last_lower"] = interval.lower
            state["admissions"][approval_id] = admission
            return "ADMITTED", admission, Outcome("ADMITTED", "durable and witnessed laboratory admission", sequence, admission)
        return self.transition(decide, fault)

    def revoke(self, scope, subject, fault=None):
        if scope not in {"approval", "key", "authority", "policy"} or not subject:
            return Outcome("DENIED", "invalid revocation scope")
        def decide(state, sequence):
            revocation = {"scope": scope, "subject": subject, "sequence": sequence}
            state["revocations"].append(revocation)
            return "REVOKED", revocation, Outcome("EFFECTIVE", "revocation committed and witnessed", sequence)
        return self.transition(decide, fault)

    def request_revocation(self, scope, subject):
        return Outcome("PENDING", "request only; not effective")

    def change_control(self, authority_epoch, revocation_epoch, policy):
        def decide(state, sequence):
            if (type(authority_epoch) is not int or type(revocation_epoch) is not int
                    or authority_epoch < state["authority_epoch"]
                    or revocation_epoch < state["revocation_epoch"]
                    or not isinstance(policy, str) or not policy):
                return Outcome("DENIED", "control rollback or invalid policy")
            state.update(authority_epoch=authority_epoch, revocation_epoch=revocation_epoch, policy=policy)
            return "CONTROL_CHANGED", {"authority_epoch": authority_epoch, "revocation_epoch": revocation_epoch, "policy": policy}, Outcome("RECORDED", "control change", sequence)
        return self.transition(decide)

    def status(self, approval_id):
        try:
            with self.locked() as connection:
                try:
                    state, sequence, previous = self.checked_state(connection, observation=True)
                    admission = state["admissions"].get(approval_id)
                    return Outcome("OBSERVED" if admission else "NOT_ADMITTED", "observation only; no retry or resumption", sequence, admission)
                except (Uncertain, sqlite3.Error, OSError, ValueError, KeyError, TypeError) as error:
                    return Outcome("UNKNOWN/BLOCKED", str(error))
        except (sqlite3.Error, OSError) as error:
            return Outcome("UNKNOWN/BLOCKED", str(error))
