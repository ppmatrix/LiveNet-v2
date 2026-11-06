import hashlib
import json
import os
from dataclasses import dataclass

import psycopg


AUTH_SCHEMA = """
CREATE TABLE state (singleton bool PRIMARY KEY DEFAULT true CHECK(singleton),
    head bigint NOT NULL, digest text NOT NULL, quarantined bool NOT NULL DEFAULT false);
INSERT INTO state(head,digest) VALUES (0,'GENESIS');
CREATE TABLE events (seq bigint PRIMARY KEY, digest text NOT NULL, payload jsonb NOT NULL);
CREATE TABLE consumed (approval text PRIMARY KEY, attempt text UNIQUE NOT NULL,
    binding jsonb NOT NULL, seq bigint NOT NULL REFERENCES events(seq));
CREATE TABLE revoked (scope text NOT NULL, subject text NOT NULL, seq bigint NOT NULL,
    PRIMARY KEY(scope,subject));
CREATE TABLE controls (singleton bool PRIMARY KEY DEFAULT true CHECK(singleton),
    epoch integer NOT NULL, policy integer NOT NULL);
INSERT INTO controls(epoch,policy) VALUES (1,1);
"""

REF_SCHEMA = """
CREATE TABLE continuity (namespace text PRIMARY KEY, head bigint NOT NULL,
    digest text NOT NULL, pending jsonb);
CREATE TABLE receipts (namespace text NOT NULL, seq bigint NOT NULL,
    digest text NOT NULL, payload jsonb NOT NULL, PRIMARY KEY(namespace,seq));
CREATE TABLE claims (namespace text NOT NULL, approval text NOT NULL,
    attempt text NOT NULL, PRIMARY KEY(namespace,approval), UNIQUE(namespace,attempt));
"""


@dataclass(frozen=True)
class Approval:
    identifier: str
    issued: int = 100
    not_before: int = 100
    expires: int = 1000
    key: str = "key"
    authority: str = "authority"
    policy: int = 1
    epoch: int = 1
    version: str = "2"


def binding(attempt):
    return dict(request="request", attempt=attempt, participants=["human", "executor"],
                purpose="laboratory", operation="LAB_FIXED_UPDATE", gate="CLOSED",
                environment="disposable", plan="plan", digests=["digest"],
                destination="private-lab", generation=1, executor="executor",
                incarnation="incarnation", session="session", transaction="transaction")


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


class Laboratory:
    def __init__(self, authority_dsn, reference_dsn, namespace):
        self.authority_dsn = authority_dsn
        self.reference_dsn = reference_dsn
        self.namespace = namespace

    def bootstrap(self):
        with psycopg.connect(self.authority_dsn) as authority:
            authority.execute(AUTH_SCHEMA)
        with psycopg.connect(self.reference_dsn) as reference:
            reference.execute("INSERT INTO continuity VALUES (%s,0,'GENESIS',NULL)",
                              (self.namespace,))

    def observe(self, approval):
        with psycopg.connect(self.authority_dsn) as authority:
            row = authority.execute("SELECT attempt,binding,seq FROM consumed WHERE approval=%s",
                                    (approval,)).fetchone()
        return dict(record=row, executable=False, resume=False)

    def request_revocation(self, scope, subject):
        return dict(state="PENDING", effective=False, scope=scope, subject=subject)

    def quarantine(self):
        with psycopg.connect(self.authority_dsn) as authority:
            authority.execute("UPDATE state SET quarantined=true")

    def consistent(self, authority, head, digest):
        previous = "GENESIS"
        expected_consumed = {}
        expected_revoked = {}
        expected_controls = (1, 1)
        events = authority.execute("SELECT seq,digest,payload FROM events ORDER BY seq").fetchall()
        for expected_sequence, (sequence, recorded, payload) in enumerate(events, 1):
            previous = hashlib.sha256((previous + encode(payload)).encode()).hexdigest()
            if sequence != expected_sequence or recorded != previous:
                return False
            if payload['kind'] == 'admit':
                expected_consumed[payload['approval']] = (payload['binding']['attempt'],
                                                         payload['binding'], sequence)
            elif payload['kind'] == 'revoke':
                expected_revoked.setdefault((payload['scope'], payload['subject']), sequence)
            else:
                expected_controls = tuple(payload['controls'])
        consumed = {row[0]: tuple(row[1:]) for row in authority.execute(
            "SELECT approval,attempt,binding,seq FROM consumed").fetchall()}
        revoked = {(row[0], row[1]): row[2] for row in authority.execute(
            "SELECT scope,subject,seq FROM revoked").fetchall()}
        control = authority.execute("SELECT epoch,policy FROM controls").fetchone()
        return (head == len(events) and digest == previous and consumed == expected_consumed
                and revoked == expected_revoked and control == expected_controls)

    def change(self, kind, approval=None, bound=None, scope=None, subject=None,
               lower=200, upper=201, trusted=True, continuous=True,
               crash=None, lose_response=False, fail_ack=False, controls=None,
               evaluated=None, hold=None, clock=None):
        result = dict(state="BLOCKED", executable=False, resume=False)
        reference = None
        authority = None
        reserved = False
        try:
            reference = psycopg.connect(self.reference_dsn, autocommit=True, connect_timeout=2)
            reference.execute("SET statement_timeout='10s'")
            reference.execute("SELECT pg_advisory_lock(hashtextextended(%s,0))", (self.namespace,))
            authority = psycopg.connect(self.authority_dsn, autocommit=True, connect_timeout=2)
            authority.execute("SET statement_timeout='10s'")
            authority.execute("BEGIN")
            head, previous, quarantined = authority.execute(
                "SELECT head,digest,quarantined FROM state FOR UPDATE").fetchone()
            external = reference.execute(
                "SELECT head,digest,pending FROM continuity WHERE namespace=%s",
                (self.namespace,)).fetchone()
            if (quarantined or external is None or external != (head, previous, None)
                    or not self.consistent(authority, head, previous)):
                authority.execute("UPDATE state SET quarantined=true")
                authority.execute("COMMIT")
                return result | dict(reason="CONTINUITY_UNKNOWN")
            if kind == "admit":
                epoch, policy = authority.execute("SELECT epoch,policy FROM controls").fetchone()
                if clock:
                    lower, upper, trusted, continuous = clock()
                if not trusted or not continuous:
                    authority.execute("UPDATE state SET quarantined=true")
                    authority.execute("COMMIT")
                    return result | dict(reason="TIME_UNKNOWN")
                if not (approval.version == "2" and type(approval.version) is str
                        and approval.issued <= approval.not_before < approval.expires
                        and approval.expires - approval.issued <= 900
                        and lower <= upper and lower >= approval.not_before
                        and upper < approval.expires and approval.epoch == epoch
                        and approval.policy == policy and bound
                        and bound.get("attempt")):
                    return result | dict(reason="INELIGIBLE")
                for revoke_scope, revoke_subject in [("approval", approval.identifier),
                        ("key", approval.key), ("authority", approval.authority),
                        ("policy", str(approval.policy))]:
                    if authority.execute("SELECT 1 FROM revoked WHERE scope=%s AND subject=%s",
                                         (revoke_scope, revoke_subject)).fetchone():
                        return result | dict(reason="REVOKED")
                if authority.execute("SELECT 1 FROM consumed WHERE approval=%s OR attempt=%s",
                                     (approval.identifier, bound["attempt"])).fetchone():
                    return result | dict(reason="CONSUMED")
                payload = dict(kind=kind, approval=approval.identifier, binding=bound,
                               epoch=epoch, policy=policy, utc_interval=[lower, upper])
            elif kind == "revoke":
                if scope not in {"approval", "key", "authority", "policy"}:
                    return result | dict(reason="INVALID_SCOPE")
                payload = dict(kind=kind, scope=scope, subject=subject)
            elif kind == "controls":
                current = authority.execute("SELECT epoch,policy FROM controls").fetchone()
                if (not controls or len(controls) != 2 or tuple(controls) == current
                        or any(type(value) is not int for value in controls)
                        or any(value < existing for value, existing in zip(controls, current))):
                    return result | dict(reason="INVALID_CONTROLS")
                payload = dict(kind=kind, controls=list(controls))
            else:
                return result | dict(reason="INVALID_KIND")
            if evaluated:
                evaluated.set()
            if hold:
                if not hold.wait(5):
                    raise TimeoutError("test synchronization")
            sequence = head + 1
            digest = hashlib.sha256((previous + encode(payload)).encode()).hexdigest()
            if crash == "before_reserve":
                os._exit(71)
            with reference.transaction():
                reference.execute("UPDATE continuity SET pending=%s WHERE namespace=%s",
                                  (psycopg.types.json.Jsonb(dict(seq=sequence, digest=digest)),
                                   self.namespace))
                if kind == "admit":
                    reference.execute("INSERT INTO claims VALUES (%s,%s,%s)",
                                      (self.namespace, approval.identifier, bound["attempt"]))
            reserved = True
            if crash == "after_reserve":
                os._exit(72)
            authority.execute("INSERT INTO events VALUES (%s,%s,%s)",
                              (sequence, digest, psycopg.types.json.Jsonb(payload)))
            if kind == "admit":
                authority.execute("INSERT INTO consumed VALUES (%s,%s,%s,%s)",
                    (approval.identifier, bound["attempt"], psycopg.types.json.Jsonb(bound), sequence))
            elif kind == "revoke":
                authority.execute("INSERT INTO revoked VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
                                  (scope, subject, sequence))
            else:
                authority.execute("UPDATE controls SET epoch=%s,policy=%s", controls)
            authority.execute("UPDATE state SET head=%s,digest=%s", (sequence, digest))
            authority.execute("COMMIT")
            if crash == "after_local_commit":
                os._exit(73)
            with reference.transaction():
                reference.execute("INSERT INTO receipts VALUES (%s,%s,%s,%s)",
                    (self.namespace, sequence, digest, psycopg.types.json.Jsonb(payload)))
                reference.execute("UPDATE continuity SET head=%s,digest=%s,pending=NULL WHERE namespace=%s",
                                  (sequence, digest, self.namespace))
            if crash == "after_reference_commit":
                os._exit(74)
            if fail_ack:
                raise RuntimeError("ambiguous reference confirmation")
            receipt = reference.execute("SELECT digest,payload FROM receipts WHERE namespace=%s AND seq=%s",
                                        (self.namespace, sequence)).fetchone()
            if receipt != (digest, payload):
                raise RuntimeError("reference confirmation mismatch")
            if lose_response:
                return result | dict(state="UNKNOWN", reason="RESPONSE_LOST")
            return result | dict(state="ADMITTED" if kind == "admit" else "CONFIRMED",
                                 seq=sequence, digest=digest)
        except Exception as error:
            return result | dict(state="UNKNOWN" if reserved else "BLOCKED",
                                 reason=type(error).__name__)
        finally:
            if authority:
                authority.close()
            if reference:
                reference.close()
