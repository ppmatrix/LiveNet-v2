"""No PostgreSQL: fixed-SQL transaction model + real SQLite SQLAlchemy events.

The model serializes transactions with a Python lock. It is NOT a proof of PG
locking, constraints, fsync, crash recovery, admin segregation or exclusivity.
All keys, channel authentication, profile/trust and supervision are TEST doubles.
"""
import copy
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
from threading import Lock
from uuid import UUID
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine, text

from scripts.dedicated.dev09b import codec as c
from scripts.dedicated.dev09b import postgres_authority as a
from scripts.dedicated.dev09b.admission import AdmissionController
from scripts.dedicated.dev09b.doubles import MemoryClock, IndependentContinuityDouble
from scripts.dedicated.dev09b.model import AttemptState, ContinuitySample, TimeSample, OfflineObservation
from scripts.postgres.tests.test_dev09b_offline import fixture, uid


REAL_VALIDATE_LAYERS = c.validate_layers
REAL_VERIFY_ENVELOPE = c.verify_envelope


class Rows:
    def __init__(self, row=None, rowcount=1): self.row, self.rowcount = row, rowcount
    def mappings(self): return self
    def one(self):
        assert self.row is not None
        return copy.deepcopy(self.row)


class DatabaseModel:
    def __init__(self, p, t, e, plan):
        self.lock = Lock()
        self.control = dict(blocked=False, continuity_token=uid(900), last_time=0, authority_epoch=1, revocation_epoch=1)
        self.row = dict(approval_id=p['approval_id'], attempt_id=p['attempt_id'], state='AVAILABLE', revoked=False,
            envelope=c.canonical(dict(payload=p, signature_hex='0'*128)),
            **{k: c.canonical(v) for k, v in dict(payload=p, target=t, executor=e, plan=plan,
                semantic={}, physical={}, provenance={}).items()}, session_json=None)
        self.nonces = set(); self.events = []; self.calls = []; self.fail_commit = False
        self.commits = 0

    def connect(self):
        db = self
        class Connection:
            dialect = SimpleNamespace(name='postgresql')
            closed = False
            _echo = False
            engine = SimpleNamespace(echo=False, hide_parameters=True, logger=SimpleNamespace(isEnabledFor=lambda x: False))
            connection = SimpleNamespace(driver_connection=SimpleNamespace(autocommit=False))
            def get_execution_options(self): return {}
            def get_isolation_level(self): return 'READ COMMITTED'
            def in_transaction(self): return hasattr(self, 'tx') and self.tx.is_active
            def begin(self):
                db.lock.acquire()
                self.snapshot = copy.deepcopy((db.control, db.row, db.nonces, db.events))
                conn = self
                class Tx:
                    is_active = True
                    def commit(self):
                        self.is_active = False; db.commits += 1; db.lock.release()
                        if db.fail_commit: raise OSError('simulated response lost AFTER commit')
                    def rollback(self):
                        db.control, db.row, db.nonces, db.events = conn.snapshot
                        self.is_active = False; db.lock.release()
                self.tx = Tx(); return self.tx
            def close(self): self.closed = True
            def execute(self, statement, parameters=None):
                sql = str(statement); v = parameters or {}; db.calls.append(sql)
                if sql.startswith('SET LOCAL '): return Rows()
                if sql == a.IDENTITY: return Rows(dict(database='authority_dev', system_identifier='999',
                    principal='authority_service', effective_principal='authority_service', fsync='on', full_page_writes='on', synchronous_commit='on'))
                if sql == a.CONTROL: return Rows(db.control)
                if sql == a.APPROVAL:
                    return Rows(db.row if v['approval_id'] == db.row['approval_id'] else None)
                if sql == a.ATTEMPT:
                    return Rows(dict(approval_id=db.row['approval_id']) if v['attempt_id'] == db.row['attempt_id'] else None)
                if sql == a.TIME: db.control['last_time'] = v['last_time']; return Rows()
                if sql == a.NONCE:
                    if v['nonce'] in db.nonces: raise ValueError('modeled unique violation')
                    db.nonces.add(v['nonce']); return Rows()
                if sql == a.CONSUME:
                    count = int(db.row['state'] == 'AVAILABLE')
                    if count: db.row.update(state='CONSUMED', session_json=v['session_json'])
                    return Rows(rowcount=count)
                if sql == a.REVOKE:
                    db.row['revoked'] = True
                    if db.row['state'] == 'AVAILABLE': db.row['state'] = 'REVOKED'
                    return Rows()
                if sql == a.EXPIRE: db.row['state'] = 'EXPIRED'; return Rows()
                if sql == a.EVENT: db.events.append(v); return Rows()
                raise AssertionError('Unexpected SQL in model')
        return Connection()


@pytest.fixture
def rig(monkeypatch):
    p, target, executor, plan, session = fixture()
    clock = MemoryClock(); continuity = IndependentContinuityDouble(uid(900))
    # Extra explicitly modeled durable continuity interlock. No DB token fallback.
    blocked = []
    continuity.block = lambda: blocked.append(True)
    original_sample = continuity.sample
    continuity.sample = lambda: ContinuitySample(uid(900), False) if blocked else original_sample()
    db = DatabaseModel(p, target, executor, plan)
    sealed = {}; lost = []
    class ChannelDouble:
        def seal(self, receipt):
            if lost: raise OSError('lost authenticated response')
            token = str(len(sealed)).encode(); sealed[token] = copy.deepcopy(receipt); return token
        def authenticate(self, token): return copy.deepcopy(sealed[token])
    channel = ChannelDouble()
    trust = SimpleNamespace(public_key=Mock(return_value=b'k'*32), validate_artifacts=Mock(return_value=None),
        authorize_revocation=Mock(return_value=None), authorize_record=Mock(return_value=None))
    # Explicit substitutions ONLY in test: exercise lifecycle/storage, not crypto or
    # full profile approval. Real code always calls existing strict validators.
    monkeypatch.setattr(c, 'verify_envelope', lambda raw, key: c.SignatureObservation(c.canonical(c.parse(raw)['payload'])))
    monkeypatch.setattr(c, 'validate_layers', Mock())
    service = a.PostgresConsumptionService(connections=db.connect,
        destination=a.AuthorityDestination('authority_dev','999','authority_service'), trust=trust,
        clock=clock, continuity=continuity, channel=channel)
    profile = b'fixed-approved-profile-test-double'
    def client():
        return a.AuthenticatedAuthorityClient(endpoint=service, verifier=channel, payload=p, session=session,
            profile_json=profile, clock=clock, continuity=continuity)
    return SimpleNamespace(p=p,target=target,executor=executor,plan=plan,session=session,db=db,
        clock=clock,continuity=continuity,blocked=blocked,service=service,channel=channel,lost=lost,
        client=client,profile=profile,trust=trust,sealed=sealed)


def consume(r, nonce=1001): return r.client().consume(r.p['approval_id'],r.session,uid(nonce))


def test_one_atomic_consumption_under_modeled_concurrency(rig):
    def run(n):
        try: consume(rig,n); return True
        except a.AuthorityRefused: return False
    with ThreadPoolExecutor(max_workers=8) as pool: results=list(pool.map(run,range(1001,1017)))
    assert results.count(True)==1 and rig.db.row['state']=='CONSUMED'
    assert len(rig.db.nonces)==1 and rig.db.row['session_json']==c.canonical(asdict(rig.session)).decode()
    assert a.CONTROL in rig.db.calls and 'FOR UPDATE' in a.CONTROL


def test_lost_receipt_is_spent_without_dispatch_or_retry(rig):
    rig.lost.append(True)
    with pytest.raises(OSError): consume(rig)
    assert rig.db.row['state']=='CONSUMED'
    rig.lost.clear()
    with pytest.raises(a.AuthorityRefused): consume(rig,1002)
    assert not rig.db.events


def test_commit_uncertain_latches_independent_continuity(rig):
    rig.db.fail_commit=True
    with pytest.raises(a.AuthorityUncertain,match='commit_uncertain'): consume(rig)
    assert rig.db.row['state']=='CONSUMED' and rig.blocked
    rig.db.fail_commit=False
    with pytest.raises(c.Invalid): consume(rig,1002)
    assert not rig.sealed


@pytest.mark.parametrize('fault',['expired','not_yet','revoked','time','continuity','epoch','session','schema','trust','profile'])
def test_refusals_never_emit_receipt(rig,monkeypatch,fault):
    if fault=='expired': rig.clock.value=TimeSample(200,200,True)
    if fault=='not_yet': rig.clock.value=TimeSample(99,99,True)
    if fault=='revoked': rig.service.revoke(rig.p['approval_id'])
    if fault=='time': rig.clock.value=TimeSample(100,100,False)
    if fault=='continuity': rig.continuity.sample=lambda: ContinuitySample(uid(901),True)
    if fault=='epoch': rig.db.control['revocation_epoch']=2
    if fault=='session': rig.session=replace(rig.session,incarnation_id=uid(777))
    if fault=='schema': monkeypatch.setattr(c,'validate_layers',Mock(side_effect=c.Unsupported('incomplete')))
    if fault=='trust': rig.trust.public_key.side_effect=c.Invalid('untrusted')
    if fault=='profile': rig.trust.validate_artifacts.side_effect=c.Invalid('profile binding')
    with pytest.raises(c.Invalid): consume(rig)
    assert rig.db.row['state']!='CONSUMED' and not rig.sealed
    if fault=='expired': assert rig.db.row['state']=='EXPIRED'
    if fault=='continuity': assert rig.service.failed and rig.blocked


@pytest.mark.parametrize('phase',['first_effect','before_commit'])
def test_revocation_time_and_session_checked_after_consumption(rig,phase):
    client=rig.client();client.consume(rig.p['approval_id'],rig.session,uid(1001))
    rig.service.revoke(rig.p['approval_id'])
    assert rig.db.row['state']=='CONSUMED'
    with pytest.raises(a.AuthorityRefused): client.check(rig.p['attempt_id'],phase,rig.session,uid(1002))


@pytest.mark.parametrize('field',['nonce','phase','session','payload','profile_sha256','continuity_token'])
def test_authenticated_but_cross_bound_response_rejected(rig,field):
    client=rig.client();raw=rig.service.consume(rig.p['approval_id'],rig.session,uid(1001),profile_json=rig.profile)
    d=rig.sealed[raw]
    if field=='session': d[field]['backend_pid']=True
    elif field=='payload': d[field]['operation']='security-base-to-b12b01a7230'
    else:d[field]='wrong'
    with pytest.raises(c.Invalid):client._accept(raw,'consume',uid(1001))


def controller(r,conn,tx,supervision=None):
    return AdmissionController(authority=r.client(),session=r.session,connection=conn,transaction=tx,
        supervision=supervision or SimpleNamespace(assert_bound=Mock(return_value=None),before_commit=Mock(return_value=None)),plan=c.canonical(r.plan))


def sqlite_connection():
    # REAL Connection/events API, no network. This does not simulate PostgreSQL DDL.
    engine=create_engine('sqlite://',hide_parameters=True)
    conn=engine.connect();tx=conn.begin()
    return engine,conn,tx


def dispatch(r,ctl,conn,tx,body):
    ctl.dispatch_original(operation=r.p['operation'],connection=conn,transaction=tx,profile_json=r.profile,body=body)


def test_original_dispatch_and_external_commit_remains_unknown(rig):
    engine,conn,tx=sqlite_connection();ctl=controller(rig,conn,tx)
    try:
        dispatch(rig,ctl,conn,tx,lambda:conn.execute(text('select 1')))
        assert rig.db.row['state']=='CONSUMED' and ctl.state is AttemptState.RUNNING and tx.is_active
        assert not rig.db.events
        ctl.commit_once()
        assert ctl.state is AttemptState.UNKNOWN and ctl.commit_sent and not tx.is_active and conn.closed
        assert rig.db.events[0]['event']=='commit_intent'
        with pytest.raises(c.Unsupported):ctl.reconcile(AttemptState.COMMITTED_CONFIRMED,independent_confirmed=True)
    finally:conn.close();engine.dispose()


def test_consumed_without_dispatch_on_supervision_loss(rig):
    engine,conn,tx=sqlite_connection()
    supervisor=SimpleNamespace(assert_bound=Mock(side_effect=[None,c.Invalid('lost exclusive window')]))
    ctl=controller(rig,conn,tx,supervisor);body=Mock()
    try:
        with pytest.raises(c.Invalid):dispatch(rig,ctl,conn,tx,body)
        assert rig.db.row['state']=='CONSUMED' and not body.called and conn.closed
        assert ctl.state is AttemptState.UNKNOWN
    finally:engine.dispose()


def test_authority_loss_before_statement_rolls_back_and_closes(rig):
    engine,conn,tx=sqlite_connection();ctl=controller(rig,conn,tx)
    def body():
        rig.trust.public_key.side_effect=OSError('authority unavailable')
        conn.execute(text('select 1'))
    try:
        with pytest.raises(c.Invalid):dispatch(rig,ctl,conn,tx,body)
        assert conn.closed and not tx.is_active and rig.db.row['state']=='CONSUMED'
        assert ctl.state is AttemptState.UNKNOWN
    finally:engine.dispose()


def test_revocation_before_commit_never_commits(rig):
    engine,conn,tx=sqlite_connection();ctl=controller(rig,conn,tx)
    try:
        dispatch(rig,ctl,conn,tx,lambda:conn.execute(text('select 1')))
        rig.service.revoke(rig.p['approval_id'])
        with pytest.raises(c.Invalid):ctl.commit_once()
        assert not ctl.commit_sent and conn.closed and ctl.state is AttemptState.UNKNOWN
    finally:engine.dispose()


@pytest.mark.parametrize('command',['COMMIT','/* comment */ END','ROLLBACK','BEGIN','PREPARE TRANSACTION \'x\''])
def test_raw_transaction_commands_refused(rig,command):
    engine,conn,tx=sqlite_connection();ctl=controller(rig,conn,tx)
    try:
        with pytest.raises(c.Invalid):dispatch(rig,ctl,conn,tx,lambda:conn.execute(text(command)))
        assert conn.closed and rig.db.row['state']=='CONSUMED'
    finally:engine.dispose()


def test_offline_observation_cannot_dispatch(rig):
    engine,conn,tx=sqlite_connection();ctl=controller(rig,conn,tx)
    ctl.authority=SimpleNamespace(consume=lambda *a:OfflineObservation(rig.p['attempt_id'],'consume',uid(1)))
    body=Mock()
    try:
        with pytest.raises(c.Invalid):dispatch(rig,ctl,conn,tx,body)
        assert not body.called and rig.db.row['state']=='AVAILABLE'
    finally:engine.dispose()


def test_actual_application_transport_calls_integrated_controller(rig,monkeypatch):
    from scripts.postgres import dev09b_application_transport as transport
    from migrations import dev09b_prerequisites as h
    engine,conn,tx=sqlite_connection()
    # Transport's PG dialect requirement is exercised in its existing tests. The
    # event path here uses real SQLite connection; never invokes migration SQL.
    monkeypatch.setattr(conn.dialect,'name','postgresql')
    # Configure the REAL SQLite driver's transaction mode explicitly. This is
    # an event-wiring model, not proof of PostgreSQL transaction behavior.
    conn.connection.driver_connection.autocommit=False
    port=SimpleNamespace(assert_connection=Mock())
    context=h.PreparedContext(rig.profile,port)
    monkeypatch.setattr(h,'decode_profile',lambda raw:dict(operation=rig.p['operation']))
    called=[]
    def upgrade(config,revision,sql):
        assert config.attributes['connection'] is conn and tx.is_active
        called.append(revision);conn.execute(text('select 1'))
    monkeypatch.setattr(transport.command,'upgrade',upgrade)
    ctl=controller(rig,conn,tx)
    try:
        transport.ApplicationTransport(conn,tx,context).apply_once(ctl)
        assert called==['f066a01a7230'] and tx.is_active and ctl.ready_to_commit
        ctl.contain();assert conn.closed
    finally:engine.dispose()


def test_real_uuid_types_from_psycopg(rig):
    rig.db.control['continuity_token']=UUID(uid(900))
    rig.db.row['attempt_id']=UUID(rig.p['attempt_id'])
    assert consume(rig).attempt_id==rig.p['attempt_id']


def test_real_complete_layer_validator_cannot_be_bypassed_by_digest(rig,monkeypatch):
    monkeypatch.setattr(c,'validate_layers',REAL_VALIDATE_LAYERS)
    with pytest.raises(a.AuthorityRefused):consume(rig)
    assert rig.db.row['state']=='AVAILABLE' and not rig.sealed


def test_real_signature_validator_cannot_be_bypassed_by_trust_key(rig,monkeypatch):
    monkeypatch.setattr(c,'verify_envelope',REAL_VERIFY_ENVELOPE)
    with pytest.raises(a.AuthorityRefused):consume(rig)
    assert rig.db.row['state']=='AVAILABLE' and not rig.sealed


@pytest.mark.parametrize('phase',['first_effect','before_commit'])
@pytest.mark.parametrize('fault',['expired','time','continuity','epoch','session','incarnation','lost'])
def test_each_checkpoint_failure_never_returns_receipt(rig,phase,fault):
    client=rig.client();client.consume(rig.p['approval_id'],rig.session,uid(1001))
    session=rig.session
    if fault=='expired':rig.clock.value=TimeSample(200,200,True)
    if fault=='time':rig.clock.value=TimeSample(100,100,False)
    if fault=='continuity':rig.continuity.value=ContinuitySample(uid(900),False)
    if fault=='epoch':rig.db.control['authority_epoch']=2
    if fault=='session':session=replace(session,transaction_id='5678')
    if fault=='incarnation':session=replace(session,incarnation_id=uid(800))
    if fault=='lost':rig.lost.append(True)
    with pytest.raises((c.Invalid,OSError)):client.check(rig.p['attempt_id'],phase,session,uid(1002))
    assert rig.db.row['state']=='CONSUMED'


def test_no_response_before_database_commit(rig):
    original=rig.channel.seal
    def seal(receipt):
        assert rig.db.commits==1 and rig.db.row['state']=='CONSUMED'
        assert rig.db.lock.acquire(blocking=False)
        rig.db.lock.release()
        return original(receipt)
    rig.channel.seal=seal
    consume(rig)


def test_database_collision_and_unsafe_logging_refused(rig,monkeypatch):
    rig.service.destination=replace(rig.service.destination,system_identifier='123')
    with pytest.raises(a.AuthorityRefused):consume(rig)
    assert rig.db.row['state']=='AVAILABLE'
    rig.service.destination=replace(rig.service.destination,system_identifier='999')
    from migrations.dev09b_inspection_support import InspectionInputError
    monkeypatch.setattr('migrations.dev09b_inspection_support.check_client_logging',
        Mock(side_effect=InspectionInputError('CLIENT_LOGGING_REFUSED')))
    with pytest.raises(a.AuthorityRefused):consume(rig,1002)


def test_second_statement_rechecks_authority(rig):
    engine,conn,tx=sqlite_connection();ctl=controller(rig,conn,tx)
    completed=[]
    def body():
        conn.execute(text('select 1'));completed.append(1)
        rig.service.revoke(rig.p['approval_id'])
        conn.execute(text('select 2'));completed.append(2)
    try:
        with pytest.raises(c.Invalid):dispatch(rig,ctl,conn,tx,body)
        assert completed==[1] and conn.closed and not ctl.commit_sent
    finally:engine.dispose()


def test_direct_commit_and_savepoint_inside_transport_refused(rig):
    engine,conn,tx=sqlite_connection();ctl=controller(rig,conn,tx)
    try:
        with pytest.raises(c.Invalid):dispatch(rig,ctl,conn,tx,lambda:tx.commit())
        assert not ctl.commit_sent and conn.closed
    finally:engine.dispose()


def test_lost_consume_response_closes_without_body(rig):
    engine,conn,tx=sqlite_connection();ctl=controller(rig,conn,tx);body=Mock()
    rig.lost.append(True)
    try:
        with pytest.raises(OSError):dispatch(rig,ctl,conn,tx,body)
        assert not body.called and rig.db.row['state']=='CONSUMED' and conn.closed
        with pytest.raises(c.Invalid):dispatch(rig,ctl,conn,tx,body)
    finally:engine.dispose()


def test_commit_response_lost_stays_unknown(rig,monkeypatch):
    engine,conn,tx=sqlite_connection();ctl=controller(rig,conn,tx)
    try:
        dispatch(rig,ctl,conn,tx,lambda:conn.execute(text('select 1')))
        # Same real SQLAlchemy transaction API, failure at send/return boundary.
        monkeypatch.setattr(type(tx),'commit',Mock(side_effect=OSError('lost commit result')))
        with pytest.raises(OSError):ctl.commit_once()
        assert ctl.commit_sent and ctl.state is AttemptState.UNKNOWN and conn.closed
    finally:engine.dispose()


def test_no_retry_on_client_after_lost_response(rig):
    client=rig.client();rig.lost.append(True)
    with pytest.raises(OSError):client.consume(rig.p['approval_id'],rig.session,uid(1001))
    count=len(rig.db.calls)
    with pytest.raises(c.Invalid):client.consume(rig.p['approval_id'],rig.session,uid(1002))
    assert len(rig.db.calls)==count


def test_missing_precommit_inspection_prevents_commit(rig):
    engine,conn,tx=sqlite_connection()
    ctl=controller(rig,conn,tx,SimpleNamespace(assert_bound=Mock(return_value=None)))
    try:
        dispatch(rig,ctl,conn,tx,lambda:conn.execute(text('select 1')))
        with pytest.raises(AttributeError):ctl.commit_once()
        assert not ctl.commit_sent and conn.closed
    finally:engine.dispose()


def test_precommit_inspection_uses_same_connection(rig):
    engine,conn,tx=sqlite_connection();seen=[]
    def inspect(cn,tr,session,plan):
        assert cn is conn and tr is tx
        seen.append(cn.execute(text('select 1')).scalar_one())
    ctl=controller(rig,conn,tx,SimpleNamespace(assert_bound=Mock(return_value=None),before_commit=inspect))
    try:
        dispatch(rig,ctl,conn,tx,lambda:conn.execute(text('select 1')))
        ctl.commit_once()
        assert seen==[1] and ctl.commit_sent and ctl.state is AttemptState.UNKNOWN
    finally:conn.close();engine.dispose()


def test_false_policy_result_cannot_authorize(rig):
    rig.trust.validate_artifacts.return_value=False
    with pytest.raises(a.AuthorityRefused):consume(rig)
    assert rig.db.row['state']=='AVAILABLE'


def test_synthetic_authenticated_body_cannot_authorize(rig):
    rig.channel.authenticate=lambda token:OfflineObservation(rig.p['attempt_id'],'consume',uid(1001))
    with pytest.raises(c.Invalid):consume(rig)
    assert rig.db.row['state']=='CONSUMED'


@pytest.mark.parametrize('fault',['option','driver','isolation'])
def test_autocommit_or_unverified_transaction_mode_refused(rig,fault):
    factory=rig.service.connections
    def connect():
        conn=factory()
        if fault=='option':conn.get_execution_options=lambda:dict(isolation_level='AUTOCOMMIT')
        if fault=='driver':conn.connection=SimpleNamespace(driver_connection=SimpleNamespace(autocommit=True))
        if fault=='isolation':conn.get_isolation_level=lambda:'UNKNOWN'
        return conn
    rig.service.connections=connect
    with pytest.raises(a.AuthorityRefused):consume(rig)
    assert not rig.db.calls and not rig.sealed and rig.db.row['state']=='AVAILABLE'


def test_expired_consumed_approval_stays_terminal_and_advances_clock(rig):
    client=rig.client();client.consume(rig.p['approval_id'],rig.session,uid(1001))
    rig.clock.value=TimeSample(200,200,True)
    with pytest.raises(a.AuthorityRefused):client.check(rig.p['attempt_id'],'first_effect',rig.session,uid(1002))
    assert rig.db.row['state']=='CONSUMED' and rig.db.control['last_time']==200
    rig.clock.value=TimeSample(100,100,True)
    with pytest.raises(a.AuthorityRefused):client.check(rig.p['attempt_id'],'first_effect',rig.session,uid(1003))


def test_authority_cleanup_failure_cannot_emit_receipt(rig):
    factory=rig.service.connections
    def connect():
        conn=factory();conn.close=Mock(side_effect=OSError('close failed'));return conn
    rig.service.connections=connect
    with pytest.raises(a.AuthorityUncertain,match='cleanup_uncertain'):consume(rig)
    assert rig.db.row['state']=='CONSUMED' and rig.blocked and not rig.sealed


def test_construction_does_not_inspect_or_connect(rig):
    rig.service.connections=Mock(side_effect=AssertionError('must not connect'))
    rig.continuity.sample=Mock(side_effect=AssertionError('must not inspect'))
    rig.client()  # no I/O until consume
    assert not rig.service.connections.called and not rig.continuity.sample.called


def test_cancellation_during_body_still_rolls_back_and_closes(rig):
    engine,conn,tx=sqlite_connection();ctl=controller(rig,conn,tx)
    def body():
        conn.execute(text('select 1'))
        raise KeyboardInterrupt()
    try:
        with pytest.raises(KeyboardInterrupt):dispatch(rig,ctl,conn,tx,body)
        assert conn.closed and not tx.is_active and rig.db.row['state']=='CONSUMED'
        assert ctl.state is AttemptState.UNKNOWN
    finally:engine.dispose()


def test_cancellation_during_authority_commit_is_uncertain(rig):
    factory=rig.service.connections
    def connect():
        conn=factory();begin=conn.begin
        def wrapped():
            tx=begin();commit=tx.commit
            def interrupted():commit();raise KeyboardInterrupt()
            tx.commit=interrupted;return tx
        conn.begin=wrapped;return conn
    rig.service.connections=connect
    with pytest.raises(a.AuthorityUncertain):consume(rig)
    assert rig.db.row['state']=='CONSUMED' and rig.blocked and not rig.sealed


def test_cancellation_during_target_commit_stays_unknown(rig,monkeypatch):
    engine,conn,tx=sqlite_connection();ctl=controller(rig,conn,tx)
    try:
        dispatch(rig,ctl,conn,tx,lambda:conn.execute(text('select 1')))
        monkeypatch.setattr(type(tx),'commit',Mock(side_effect=KeyboardInterrupt()))
        with pytest.raises(KeyboardInterrupt):ctl.commit_once()
        assert conn.closed and ctl.commit_sent and ctl.state is AttemptState.UNKNOWN
    finally:engine.dispose()


def test_failed_close_retains_guards_on_quarantined_connection(rig,monkeypatch):
    engine,conn,tx=sqlite_connection();ctl=controller(rig,conn,tx);close=conn.close
    try:
        dispatch(rig,ctl,conn,tx,lambda:conn.execute(text('select 1')))
        monkeypatch.setattr(conn,'close',Mock(side_effect=OSError('close unavailable')))
        ctl.contain()
        assert ctl.state is AttemptState.UNKNOWN and ctl._listeners and not conn.closed
        with pytest.raises(c.Invalid):conn.execute(text('select 2'))
    finally:
        close();ctl._remove();engine.dispose()


def test_explicit_precommit_reads_stay_guarded_and_do_not_commit(rig):
    engine,conn,tx=sqlite_connection();queries=[]
    supervision=SimpleNamespace(assert_bound=Mock(return_value=None),before_commit=lambda *args:queries.append(conn.execute(text('select 1')).scalar()))
    ctl=controller(rig,conn,tx,supervision)
    try:
        ctl.dispatch_original(operation=rig.p['operation'],connection=conn,transaction=tx,profile_json=rig.profile,body=lambda:conn.execute(text('select 1')))
        ctl.inspect_precommit()
        assert queries==[1] and tx.is_active and not ctl.commit_sent
        ctl.contain()
    finally:conn.close();engine.dispose()


def test_precommit_supervision_failure_contains_without_authority_fallback(rig):
    engine,conn,tx=sqlite_connection()
    supervision=SimpleNamespace(assert_bound=Mock(return_value=None),before_commit=Mock(side_effect=OSError('private failure not logged')))
    ctl=controller(rig,conn,tx,supervision)
    try:
        ctl.dispatch_original(operation=rig.p['operation'],connection=conn,transaction=tx,profile_json=rig.profile,body=lambda:conn.execute(text('select 1')))
        with pytest.raises(OSError):ctl.inspect_precommit()
        assert conn.closed and not ctl.commit_sent and ctl.state is AttemptState.UNKNOWN
    finally:conn.close();engine.dispose()


def test_containment_is_idempotent_after_actual_connection_close(rig):
    engine,conn,tx=sqlite_connection();ctl=controller(rig,conn,tx)
    try:
        ctl.dispatch_original(operation=rig.p['operation'],connection=conn,transaction=tx,profile_json=rig.profile,body=lambda:conn.execute(text('select 1')))
        ctl.contain();events=list(ctl.events);ctl.contain()
        assert ctl.events==events and conn.closed and ctl.state is AttemptState.UNKNOWN
    finally:conn.close();engine.dispose()
