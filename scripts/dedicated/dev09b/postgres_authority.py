"""Explicit PostgreSQL consumption service; no server, connection creation or issuance.

Deployment MUST supply a separate authority database, authenticated caller/channel,
trusted key/profile policy, clock and an INDEPENDENT continuity interlock. A restored
DB token is insufficient. Proposed schema is not installed by this module. SQL only
runs when a caller invokes a method with an explicitly supplied connection factory.
Receipt authentication reuses an injected authenticated channel, not a new signature
protocol. No response is emitted before the authority transaction commits.
"""
from dataclasses import asdict, dataclass

from sqlalchemy import text

from . import codec as c
from .layers import ExpectationSnapshot
from .model import ApprovalState, SessionBinding


class AuthorityRefused(c.Invalid):
    """Safe fixed diagnostic; never include driver messages or row values."""


class AuthorityUncertain(AuthorityRefused):
    pass


# Schema-qualified, parameterized SQL. One control row serializes consumption,
# checkpoints and revocation. Unique constraints provide additional enforcement.
CONTROL = "SELECT * FROM dev09b_authority.control WHERE singleton = true FOR UPDATE"
APPROVAL = "SELECT * FROM dev09b_authority.approvals WHERE approval_id = CAST(:approval_id AS uuid) FOR UPDATE"
ATTEMPT = "SELECT approval_id FROM dev09b_authority.approvals WHERE attempt_id = CAST(:attempt_id AS uuid)"
CONSUME = """UPDATE dev09b_authority.approvals SET state = 'CONSUMED', session_json = :session_json
 WHERE approval_id = CAST(:approval_id AS uuid) AND state = 'AVAILABLE'"""
NONCE = "INSERT INTO dev09b_authority.nonces (nonce) VALUES (CAST(:nonce AS uuid))"
TIME = "UPDATE dev09b_authority.control SET last_time = :last_time WHERE singleton = true"
REVOKE = """UPDATE dev09b_authority.approvals SET revoked = true,
 state = CASE WHEN state = 'AVAILABLE' THEN 'REVOKED' ELSE state END WHERE approval_id = CAST(:approval_id AS uuid)"""
EXPIRE = "UPDATE dev09b_authority.approvals SET state = 'EXPIRED' WHERE approval_id = CAST(:approval_id AS uuid) AND state = 'AVAILABLE'"
EVENT = "INSERT INTO dev09b_authority.events (attempt_id, event, evidence_sha256) VALUES (CAST(:attempt_id AS uuid), :event, :evidence_sha256)"
IDENTITY = """SELECT current_database() AS database, session_user AS principal, current_user AS effective_principal,
 (pg_catalog.pg_control_system()).system_identifier::text AS system_identifier,
 current_setting('fsync') AS fsync, current_setting('full_page_writes') AS full_page_writes,
 current_setting('synchronous_commit') AS synchronous_commit"""


@dataclass(frozen=True)
class AuthorityDestination:
    database: str
    system_identifier: str
    principal: str


@dataclass(frozen=True)
class Receipt:
    """Only returned by the explicitly trusted channel verifier below."""
    attempt_id: str
    phase: str
    nonce: str


class PostgresConsumptionService:
    """Required injected ports (no permissive defaults):

    connections(): a NEW idle authority connection, never a LiveNet connection.
    trust.public_key(payload, control): trusted issuer/key/policy/revocation lookup;
      must authenticate caller identity and authorize that exact executor too.
    trust.validate_artifacts(snapshot, profile_json): prior approval, source/bundle/
      dependency policy AND exact prepared-profile binding to the fixed snapshot.
    continuity.sample(): independent live indication; .block(): latch ALL future
      admissions across restarts until independent reconciliation (not DB epoch).
    channel.seal(receipt_dict): authenticate response AFTER commit; no synthetic
      fallback. Request transport authentication belongs to the trusted endpoint.

    No load/issue/recovery/reset interface: approvals and policies must be installed
    by separately authorized administration. Status is deliberately not admission.
    """
    def __init__(self, *, connections, destination, trust, clock, continuity, channel):
        self.connections = connections
        self.destination = destination
        self.trust = trust
        self.clock = clock
        self.continuity = continuity
        self.channel = channel
        self.failed = False

    def _quarantine(self):
        self.failed = True
        try: self.continuity.block()
        except BaseException: pass  # local latch stays closed; external implementation must persist

    def _continuity(self, expected):
        try:
            indication = self.continuity.sample(); indication.validate()
            c.require(indication.token == expected)
            return indication
        except BaseException:
            self._quarantine()
            raise AuthorityUncertain('authority.continuity_uncertain') from None

    def _locked(self, action):
        if self.failed:
            raise AuthorityUncertain('authority.quarantined')
        connection = transaction = None
        committing = False
        try:
            connection = self.connections()
            c.require(connection.dialect.name == 'postgresql' and not connection.in_transaction())
            # SQLAlchemy begin() in AUTOCOMMIT mode is only a logical transaction.
            # Refuse it before executing any SQL; a row lock alone would not suffice.
            c.require(connection.get_execution_options().get('isolation_level') != 'AUTOCOMMIT')
            c.require(connection.connection.driver_connection.autocommit is False)
            c.require(connection.get_isolation_level() in ('READ COMMITTED', 'REPEATABLE READ', 'SERIALIZABLE'))
            from migrations.dev09b_inspection_support import check_client_logging
            check_client_logging(connection)
            transaction = connection.begin()
            connection.execute(text("SET LOCAL synchronous_commit = on"))
            connection.execute(text("SET LOCAL statement_timeout = '5000ms'"))
            connection.execute(text("SET LOCAL lock_timeout = '2000ms'"))
            identity = dict(connection.execute(text(IDENTITY)).mappings().one())
            d = self.destination
            c.require(type(d) is AuthorityDestination)
            c.require((identity['database'], identity['system_identifier'], identity['principal']) ==
                      (d.database, d.system_identifier, d.principal))
            c.require(identity['effective_principal'] == d.principal)
            c.require(all(identity[k] == 'on' for k in ('fsync', 'full_page_writes', 'synchronous_commit')))
            control = dict(connection.execute(text(CONTROL)).mappings().one())
            control['continuity_token'] = str(control['continuity_token'])
            c.uuid(control['continuity_token'])
            for key in ('authority_epoch', 'revocation_epoch'): c.integer(control[key], 1)
            c.integer(control['last_time'])
            c.require(control['blocked'] is False)
            indication = self._continuity(control['continuity_token'])
            now = self.clock.sample()
            now.validate()
            c.require(now.lower >= control['last_time'])
            connection.execute(text(TIME), {'last_time': now.lower})
            result = action(connection, control, now)
            # Continuity/time can fail while signature/artifact checks are running.
            self._continuity(indication.token)
            final = self.clock.sample(); final.validate()
            c.require(final.lower >= now.lower)
            if type(result) is dict and 'payload' in result:
                c.require(final.upper < result['payload']['expires_at'])
            connection.execute(text(TIME), {'last_time': final.lower})
            committing = True
            transaction.commit()
            committing = False
            return result
        except BaseException:
            if committing:
                self._quarantine()
                raise AuthorityUncertain('authority.commit_uncertain') from None
            raise AuthorityRefused('authority.transaction_refused') from None
        finally:
            cleanup_failed = False
            if transaction is not None and transaction.is_active:
                try: transaction.rollback()
                except BaseException: cleanup_failed = True
            if connection is not None:
                try: connection.close()
                except BaseException: cleanup_failed = True
            if cleanup_failed:
                self._quarantine()
                raise AuthorityUncertain('authority.cleanup_uncertain') from None

    def _approval(self, db, control, now, approval_id, session, profile_json):
        c.require(type(session) is SessionBinding); session.validate(); c.uuid(approval_id)
        row = dict(db.execute(text(APPROVAL), {'approval_id': approval_id}).mappings().one())
        envelope = c.parse(bytes(row['envelope']))
        p = envelope['payload']; c.validate_payload(p)
        c.require(p['approval_id'] == approval_id and str(row['attempt_id']) == p['attempt_id'])
        # Lookup/policy is external trusted input; signature alone is not authority.
        key = self.trust.public_key(p, control)
        signature = c.verify_envelope(bytes(row['envelope']), key)
        c.require(signature.payload_json == c.canonical(p))
        snap = ExpectationSnapshot(*(bytes(row[k]) for k in
            ('payload', 'target', 'executor', 'plan', 'semantic', 'physical', 'provenance')))
        c.require(snap.payload == signature.payload_json)
        c.validate_layers(snap)  # Unsupported schemas/profiles never become opaque hashes.
        c.require(self.trust.validate_artifacts(snap, profile_json) is None)
        t, e, plan = (c.parse(getattr(snap, k)) for k in ('target', 'executor', 'plan'))
        c.inspect_bindings(p, t, e, plan)
        c.require(t['system_identifier'] != self.destination.system_identifier)
        c.require((session.target_sha256, session.executor_sha256, session.incarnation_id) ==
                  (p['target_binding_sha256'], c.digest('executor', e), e['incarnation_id']))
        c.require((p['authority_epoch'], p['revocation_epoch']) ==
                  (control['authority_epoch'], control['revocation_epoch']))
        c.require(row['revoked'] is False and row['state'] not in ('REVOKED', 'EXPIRED'))
        if now.lower >= p['expires_at']:
            if row['state'] == 'AVAILABLE': db.execute(text(EXPIRE), {'approval_id': approval_id})
            return None, None  # persist terminal expiry, then refuse outside transaction
        c.require(now.lower >= p['not_before'] and now.upper < p['expires_at'])
        # Fresh temporal sample before authority commit; interval must remain valid.
        last = self.clock.sample(); last.validate()
        c.require(last.lower >= now.lower and last.upper < p['expires_at'])
        return row, p

    def consume(self, approval_id, session, nonce, *, profile_json):
        c.uuid(nonce)
        def consume(db, control, now):
            row, p = self._approval(db, control, now, approval_id, session, profile_json)
            if row is None: return None
            c.require(row['state'] == ApprovalState.AVAILABLE.value)
            db.execute(text(NONCE), {'nonce': nonce})
            result = db.execute(text(CONSUME), {'approval_id': approval_id,
                'session_json': c.canonical(asdict(session)).decode('utf8')})
            c.require(result.rowcount == 1)
            return self._receipt(p, session, nonce, 'consume', control, profile_json)
        result = self._locked(consume)
        # Lost response here leaves CONSUMED. No retry/release/fallback.
        if result is None: raise AuthorityRefused('authority.expired')
        return self.channel.seal(result)

    def check(self, attempt_id, phase, session, nonce, *, profile_json):
        c.uuid(attempt_id); c.uuid(nonce)
        c.require(phase in ('first_effect', 'before_commit'))
        def check(db, control, now):
            approval_id = db.execute(text(ATTEMPT), {'attempt_id': attempt_id}).mappings().one()['approval_id']
            row, p = self._approval(db, control, now, approval_id, session, profile_json)
            if row is None: return None
            c.require(row['state'] == 'CONSUMED' and p['attempt_id'] == attempt_id)
            c.require(c.canonical(c.parse(row['session_json'].encode())) == c.canonical(asdict(session)))
            db.execute(text(NONCE), {'nonce': nonce})
            return self._receipt(p, session, nonce, phase, control, profile_json)
        result = self._locked(check)
        if result is None: raise AuthorityRefused('authority.expired')
        return self.channel.seal(result)

    @staticmethod
    def _receipt(p, session, nonce, phase, control, profile_json):
        from hashlib import sha256
        return dict(payload=p, session=asdict(session), nonce=nonce, phase=phase,
                    continuity_token=control['continuity_token'],
                    profile_sha256=sha256(profile_json).hexdigest())

    def revoke(self, approval_id):
        # Segregated authenticated administration only; do not expose to executor.
        c.uuid(approval_id)
        def revoke(db, control, now):
            c.require(self.trust.authorize_revocation(approval_id) is None)
            c.require(db.execute(text(REVOKE), {'approval_id': approval_id}).rowcount == 1)
        self._locked(revoke)

    def record(self, attempt_id, event, evidence_sha256):
        c.uuid(attempt_id); c.digest_text(evidence_sha256)
        c.require(event in ('commit_intent', 'rollback_attempt', 'close', 'independent_reconciliation'))
        def record(db, control, now):
            row = db.execute(text(ATTEMPT), {'attempt_id': attempt_id}).mappings().one()
            c.require(self.trust.authorize_record(attempt_id, event) is None)
            c.require(row['approval_id'] is not None)
            db.execute(text(EVENT), dict(attempt_id=attempt_id, event=event, evidence_sha256=evidence_sha256))
        self._locked(record)


class AuthenticatedAuthorityClient:
    """Explicit authenticated endpoint + trusted channel verifier, fixed expectations.

    No verifier, fixture, digest or naked Receipt is an endpoint. authenticate()
    MUST validate origin/integrity and freshness of the authenticated response.
    The client independently rechecks all bindings, local time and continuity.
    """
    def __init__(self, *, endpoint, verifier, payload, session, profile_json, clock, continuity):
        c.validate_payload(payload); session.validate()
        self.endpoint, self.verifier = endpoint, verifier
        self.payload = c.canonical(payload)
        self.session, self.profile_json = session, profile_json
        self.clock, self.continuity = clock, continuity
        from threading import Lock
        self.seen = set()
        self.consume_attempted = False
        self._consume_lock = Lock()
        self.token = None  # construction performs no continuity/channel/database I/O

    def _accept(self, raw, phase, nonce):
        from hashlib import sha256
        c.uuid(nonce); c.require(nonce not in self.seen); self.seen.add(nonce)
        d = self.verifier.authenticate(raw)
        c.closed(d, {'payload', 'session', 'nonce', 'phase', 'continuity_token', 'profile_sha256'})
        c.require(c.canonical(d['payload']) == self.payload and
                  c.canonical(d['session']) == c.canonical(asdict(self.session)))
        c.require(d['nonce'] == nonce and d['phase'] == phase and d['continuity_token'] == self.token)
        c.require(d['profile_sha256'] == sha256(self.profile_json).hexdigest())
        indication = self.continuity.sample(); indication.validate(); c.require(indication.token == self.token)
        now = self.clock.sample(); now.validate()
        p = c.parse(self.payload)
        c.require(now.lower >= p['not_before'] and now.upper < p['expires_at'])
        return Receipt(p['attempt_id'], phase, nonce)

    def consume(self, approval_id, session, nonce):
        with self._consume_lock:
            c.require(not self.consume_attempted)
            self.consume_attempted = True  # even a lost/refused response cannot retry
        c.require(approval_id == c.parse(self.payload)['approval_id'] and session == self.session)
        indication = self.continuity.sample(); indication.validate()
        self.token = indication.token
        return self._accept(self.endpoint.consume(approval_id, session, nonce, profile_json=self.profile_json), 'consume', nonce)

    def check(self, attempt_id, phase, session, nonce):
        c.require(attempt_id == c.parse(self.payload)['attempt_id'] and session == self.session)
        return self._accept(self.endpoint.check(attempt_id, phase, session, nonce, profile_json=self.profile_json), phase, nonce)

    def record(self, attempt_id, event, evidence_sha256):
        c.require(attempt_id == c.parse(self.payload)['attempt_id'])
        self.endpoint.record(attempt_id, event, evidence_sha256)
