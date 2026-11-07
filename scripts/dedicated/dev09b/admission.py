"""Original-attempt admission integrated with ApplicationTransport.

Trusted injected supervision is required, not implemented by an advisory lock or
an offline evidence flag. This is not a sandbox against a malicious executor/raw
DBAPI escape. Only the attested original source body is eligible. COMMIT remains
an explicit controller operation AFTER transport returns; confirmation belongs to
an independent reconciler. No automatic retry, release, or synthetic fallback.
"""
from uuid import uuid4
import re

from sqlalchemy import event

from . import codec as c
from .model import _AttemptLifecycle, AttemptState, SessionBinding
from .postgres_authority import AuthenticatedAuthorityClient, Receipt


class AdmissionController(_AttemptLifecycle):
    """Construction is inert. One call consumes before installing dispatch guards.

    supervision.assert_bound(connection, transaction, session, plan_bytes) must
    confirm live exclusive window and exact session/transaction/incarnation;
    unavailable/uncertain -> exception. It MUST NOT execute on the guarded
    connection inside SQLAlchemy event callbacks (no recursive SQL). A separate
    supervision.before_commit(connection, transaction, session, plan_bytes) must
    authenticate complete PRECOMMIT evidence against the fixed expectations; its
    same-session SELECTs are guarded too. It returns None or raises, never a bool.
    A supervision implementation and independent reconciliation remain required.
    """
    _event_prefix = 'admission_'

    def __init__(self, *, authority, session, connection, transaction, supervision, plan):
        self.authority = authority
        self.session = session
        self.connection, self.transaction = connection, transaction
        self.supervision, self.plan = supervision, bytes(plan)
        self.used = False
        self.ready_to_commit = False
        self._committing = False
        self._containing = False
        self._inspecting_commit = False
        self._listeners = []
        self.state = AttemptState.UNKNOWN
        self.commit_sent = False
        self.closed = False
        self.events = []

    def _validate_observation(self, observation, phase, nonce):
        c.require(type(observation) is Receipt and observation.phase == phase and observation.nonce == nonce)

    def _bound(self):
        conn = self.connection
        c.require(type(self.session) is SessionBinding); self.session.validate()
        c.require(conn.closed is False and conn.in_transaction() is True and
                  conn.get_transaction() is self.transaction and self.transaction.is_active is True)
        from migrations.dev09b_inspection_support import check_client_logging
        check_client_logging(conn)
        c.require(self.supervision.assert_bound(conn, self.transaction, self.session, self.plan) is None)

    def _listen(self, name, callback):
        event.listen(self.connection, name, callback)
        self._listeners.append((name, callback))

    def _remove(self):
        # If close failed, retain guards on the quarantined connection: UNKNOWN
        # must not leave an open, unguarded target session behind.
        if self.connection.closed is not True: return
        for name, callback in self._listeners:
            event.remove(self.connection, name, callback)
        self._listeners.clear()

    def _guard_statement(self, conn, cursor, statement, parameters, context, executemany):
        self._bound()
        c.require((not self.ready_to_commit or self._inspecting_commit) and not self._committing)
        # Trusted attested migrations only. Refuse transaction commands even if
        # sent as text; this is not a generic PostgreSQL SQL sandbox/parser.
        prefix = re.sub(r'/\*.*?\*/|--[^\n]*(?:\n|$)', ' ', statement, flags=re.S).lstrip().upper()
        if self._inspecting_commit: c.require(re.match(r'SELECT\b', prefix) is not None)
        c.require(not re.match(r'(COMMIT|END|ROLLBACK|ABORT|BEGIN|START|PREPARE)\b', prefix))
        if self.state is AttemptState.CONSUMED_NOT_STARTED:
            self.first_effect(self.session, str(uuid4()))
        else:
            c.require(self.state is AttemptState.RUNNING)
            # Includes read-only Alembic/preflight statements: an intentionally
            # stricter checkpoint on EACH statement, not a cached early check.
            self._checkpoint('first_effect', self.session, str(uuid4()))
        self._bound()

    def _transaction_guard(self, *args, **kwargs):
        c.require(self._committing or self._containing)

    def dispatch_original(self, *, operation, connection, transaction, profile_json, body):
        c.require(not self.used); self.used = True
        try:
            c.require(type(self.authority) is AuthenticatedAuthorityClient)
            c.require(connection is self.connection and transaction is self.transaction)
            plan = c.parse(self.plan); c.validate_plan(plan)
            payload = c.parse(self.authority.payload)
            c.require(operation == plan['operation'] == payload['operation'])
            c.require(c.digest('plan', plan) == payload['execution_plan_sha256'])
            c.require(profile_json == self.authority.profile_json and self.authority.session == self.session)
            self._bound()
            _AttemptLifecycle.__init__(self, self.authority, payload['approval_id'], self.session, str(uuid4()))
            # After consumption, failure here still leaves the approval spent.
            self._bound()
            self._listen('before_cursor_execute', self._guard_statement)
            for name in ('commit', 'rollback', 'begin', 'savepoint', 'rollback_savepoint',
                         'release_savepoint', 'begin_twophase', 'prepare_twophase',
                         'commit_twophase', 'rollback_twophase'):
                self._listen(name, self._transaction_guard)
            body()
            self._bound()
            c.require(self.state is AttemptState.RUNNING)  # no body/no effects is not success
            self.ready_to_commit = True
        except BaseException:
            self.contain()
            raise

    def commit_once(self):
        """Outside ApplicationTransport. UNKNOWN before sending, even on return.

        Does not call any independent confirmation port or declare success.
        A repeated call is refused. No authority outage inhibits containment.
        """
        try:
            c.require(self.ready_to_commit and not self.commit_sent and not self.closed)
            self._bound()
            # Explicit trusted PRECOMMIT inspection/exclusivity port. This is not
            # the independent PERSISTED/CLOSED confirmation or a boolean flag.
            self._inspecting_commit = True
            try:
                c.require(self.supervision.before_commit(self.connection, self.transaction,
                                                         self.session, self.plan) is None)
            finally:
                self._inspecting_commit = False
            self.before_commit(self.session, str(uuid4()))
            self._mark_commit_dispatch(self.session, str(uuid4()))
            self._committing = True
            self.transaction.commit()
        except BaseException:
            self.contain()
            raise
        finally:
            self._committing = False
        # Close the borrowed session even after driver success; no further SQL
        # is admitted while independent outcome remains UNKNOWN. Administrative
        # closure of temporary powers still belongs to supervised reconciliation.
        try:
            self.connection.close()
        finally:
            self._remove()
            self.close()
        # No confirmation from a driver return value.

    def contain(self):
        """Always try rollback AND close, including with unavailable authority."""
        self.abort()
        self._containing = True
        try:
            try: self.transaction.rollback()
            except BaseException: self.state = AttemptState.UNKNOWN
            try: self.connection.close()
            except BaseException: self.state = AttemptState.UNKNOWN
        finally:
            self._containing = False
            try: self._remove()
            finally: self.close()

    def rollback_result(self, **kwargs):
        raise c.Unsupported('Independent operational reconciliation is not a boolean')

    def reconcile(self, *args, **kwargs):
        raise c.Unsupported('Independent operational reconciliation port required')
