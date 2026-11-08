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
        self.containment = []

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

    def inspect_precommit(self):
        """Explicit same-session inspection; no COMMIT and no cached permission."""
        try:
            c.require(self.ready_to_commit and not self.commit_sent and not self.closed)
            self._bound()
            self._inspecting_commit = True
            try:
                c.require(self.supervision.before_commit(self.connection,self.transaction,self.session,self.plan) is None)
            finally:
                self._inspecting_commit = False
            self._bound()
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
            self.inspect_precommit()
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
        if self.closed and self.connection.closed is True:return
        self.abort()
        self._containing = True
        result=dict(rollback='NOT_ATTEMPTED',close='NOT_ATTEMPTED')
        self.containment.append(result)
        try:
            try:
                self.transaction.rollback();result['rollback']='RETURNED'
            except BaseException as exc:
                result['rollback']='FAILED';result['rollback_exception']=type(exc).__name__;self.state=AttemptState.UNKNOWN
            try:
                self.connection.close();result['close']='RETURNED' if self.connection.closed is True else 'UNCERTAIN'
            except BaseException as exc:
                result['close']='FAILED';result['close_exception']=type(exc).__name__;self.state=AttemptState.UNKNOWN
        finally:
            self._containing = False
            try: self._remove()
            finally: self.close()

    def confirm_persisted(self, snapshot, primary, independent, *, authenticity, independence):
        """Authenticated independent comparison, never a driver-return boolean.

        No evidence is collected/fabricated here. The caller supplies two real
        post-commit collections and explicit trusted origin/independence ports.
        Failure leaves UNKNOWN. Administrative CLOSED/handoff remains separate.
        """
        from dataclasses import asdict
        from .layers import read_snapshot
        from . import detailed_catalog as detail,physical
        c.require(self.used and type(self.authority) is AuthenticatedAuthorityClient)
        c.require(self.state is AttemptState.UNKNOWN and self.commit_sent and self.closed and self.connection.closed is True)
        c.validate_layers(snapshot)
        payload,target,executor,plan,semantic,phys,provenance=read_snapshot(snapshot)
        c.require(snapshot.payload==self.authority.payload and snapshot.plan==self.plan)
        c.require(phys['schema_version']==2 and payload['operation']=='application-base-to-f066a01a7230')
        for evidence in (primary,independent):
            c.require(evidence['phase']=='APP-F066-PERSISTED')
            for key in ('request_id','approval_id','attempt_id'):c.require(evidence[key]==payload[key])
            c.require(c.canonical(evidence['subject_session'])==c.canonical(asdict(self.session)))
        expected=detail.validate_contract(phys,target,semantic,provenance)['APP-F066-PERSISTED']
        comparison=physical.compare_independent_pair(expected,primary,independent,authenticity,independence)
        from .layers import document_hash
        self.authority.record(payload['attempt_id'],'independent_reconciliation',document_hash([primary,independent]))
        _AttemptLifecycle.reconcile(self,AttemptState.COMMITTED_CONFIRMED,independent_confirmed=True)
        return comparison

    def rollback_result(self, **kwargs):
        raise c.Unsupported('Independent operational reconciliation is not a boolean')

    def confirm_rollback(self,snapshot,evidence,*,authenticity,independence,journal):
        """Full independent prefix-zero proof; record outside restored authority.

        Does not remove temporary rights or unblock a window. Record loss and
        all comparison/origin failures leave UNKNOWN and still close locally.
        """
        from . import rollback
        from .evidence import OriginObservation
        from .layers import document_hash
        try:
            c.require(self.used and self.state is AttemptState.UNKNOWN and not self.commit_sent
                      and self.closed and self.connection.closed is True)
            c.validate_layers(snapshot)
            c.require(snapshot.payload==self.authority.payload and snapshot.plan==self.plan)
            comparison=rollback.validate(snapshot,self.session,evidence)
            raw=c.canonical(evidence,maximum_depth=32)
            origin=authenticity.inspect(raw)
            c.require(type(origin) is OriginObservation and origin.authenticated is True
                and origin.classification=='OPERATIONAL' and origin.collector_id==evidence['collector_id']
                and origin.evidence_sha256==document_hash(evidence))
            c.require(independence.confirm(raw) is None)
            c.require(journal.persist(raw) is None)
            _AttemptLifecycle.reconcile(self,AttemptState.ROLLED_BACK_CONFIRMED,independent_confirmed=True)
            return comparison
        except BaseException:
            self.contain()
            raise

    def reconcile(self, *args, **kwargs):
        raise c.Unsupported('Independent operational reconciliation port required')
