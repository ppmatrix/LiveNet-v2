"""Network doubles only. SQLite exercises persistence, not PostgreSQL locks/DDL."""
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from threading import RLock,Event,Thread
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4
import errno
import json
import time
import pytest
from sqlalchemy import create_engine,event,MetaData,text,select,true,func
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.attributes import set_committed_value
from datetime import timezone
from app import create_app
from app.audit.models import AuditEvent
from app.inventory.models import Resource,ResourceIdentifier
from app.inventory.access import InventoryIdentity
from app.discovery.models import Job,Observation,Decision
from app.discovery.policy import Policy
from app.discovery.service import Repository,Problem,now
from app.discovery.worker import Worker
from app.discovery.network import probe


@compiles(JSONB,'sqlite')
def json_sqlite(type_,compiler,**kw):return 'JSON'


def policy(**overrides):
    return Policy.from_mapping(dict(networks=['10.42.0.0/24'],ports=[22,443],max_targets=16,concurrency=2,
        target_timeout=.2,job_timeout=2,max_jobs=2)|overrides)


@pytest.fixture
def store(tmp_path):
    engine=create_engine('sqlite:///'+str(tmp_path/'discovery.db'),connect_args={'check_same_thread':False},
        execution_options={'schema_translate_map':{'inventory':None,'audit':None,'discovery':None}})
    @event.listens_for(engine,'connect')
    def functions(connection,record):
        connection.create_function('btrim',1,lambda v:v.strip())
        connection.create_function('jsonb_typeof',1,lambda v:'object' if isinstance(json.loads(v),dict) else 'array')
    metadata=MetaData()
    for model in (Resource,ResourceIdentifier,AuditEvent,Job,Observation,Decision):
        table=model.__table__.to_metadata(metadata)
        for column in table.columns:
            if column.server_default is not None and '::jsonb' in str(column.server_default.arg):column.server_default.arg=text("'{}'")
    metadata.create_all(engine)
    sessions=sessionmaker(bind=engine,expire_on_commit=False)
    @event.listens_for(sessions,'loaded_as_persistent')
    def sqlite_utc(session,instance):
        # SQLite drops tzinfo; preserve the PostgreSQL-aware serializer contract.
        if isinstance(instance,Resource):
            for field in ('created_at','updated_at','archived_at'):
                value=getattr(instance,field)
                if value is not None and value.tzinfo is None:set_committed_value(instance,field,value.replace(tzinfo=timezone.utc))
    lock=RLock()
    class LocalRepository(Repository):
        @contextmanager
        def transaction(self,key=None):
            # SQLite test substitute for PG transaction/row/advisory locks.
            with lock:
                with super().transaction() as session:yield session
    repo=LocalRepository(sessions)
    yield repo,sessions,InventoryIdentity(uuid4())
    engine.dispose()


def observe(repo,identity,ip='10.42.0.1',outcome='responded'):
    job=repo.enqueue(policy(),ip+'/32',identity)
    with repo.transaction() as session:
        o=Observation(id=uuid4(),job_id=__import__('uuid').UUID(job['id']),ip=ip,outcome=outcome,observed_at=now(),
            source_type='tcp_connect',source_instance=job['id'],evidence={'method':'tcp_connect','ports':[{'port':22,'result':'refused'}]})
        session.add(o);identifier=o.id
        session.get(Job,o.job_id).status='completed'
    return identifier


def creation(confirm=False):return dict(mode='create',confirm_distinct=confirm,resource=dict(display_name='Recurso revisto',resource_type='service'))


@pytest.mark.parametrize('target',['0.0.0.0/0','10.42.0.0/24','8.8.8.8/32','127.0.0.1/32','169.254.1.1/32','224.0.0.1/32',
    '10.43.0.1/32','10.42.0.9-10.42.0.1','10.42.0.1-10.42.0.20','::1/128','example.test','10.42.0.1; command','10.42.0.1/24',None])
def test_targets_refused_without_network(target):
    with pytest.raises(ValueError):policy().targets(target)


def test_targets_cidr_range_and_bounds():
    assert policy().targets('10.42.0.0/30')==('10.42.0.1','10.42.0.2')
    assert policy().targets('10.42.0.1 - 10.42.0.2')==('10.42.0.1','10.42.0.2')
    assert policy().targets('10.42.0.2/32')==('10.42.0.2',)


@pytest.mark.parametrize('change',[{'networks':['8.8.8.0/24']},{'networks':['127.0.0.0/8']},{'ports':[0]},
    {'ports':[22,22]},{'max_targets':257},{'concurrency':33},{'max_jobs':5},{'target_timeout':0},{'job_timeout':301}])
def test_invalid_administrator_configuration(change):
    with pytest.raises(ValueError):policy(**change)


def test_tcp_method_without_real_network(monkeypatch):
    socket=Mock();socket.__enter__=lambda self:self;socket.__exit__=lambda *args:False
    socket.connect_ex.side_effect=[errno.ECONNREFUSED,0]
    factory=Mock(return_value=socket);monkeypatch.setattr('app.discovery.network.socket.socket',factory)
    result=probe('10.42.0.1',policy())
    assert result==dict(outcome='responded',evidence=dict(method='tcp_connect',ports=[dict(port=22,result='refused',code='ECONNREFUSED',errno=errno.ECONNREFUSED),dict(port=443,result='connected')]))
    assert socket.connect_ex.call_args_list[0].args==( ('10.42.0.1',22), )
    assert probe('10.42.0.1',policy(),lambda:True)['outcome']=='no_response'
    assert factory.call_count==2


def test_partial_failures_progress_and_observation_history(store):
    repo,sessions,identity=store
    job=repo.enqueue(policy(),'10.42.0.1-10.42.0.3',identity)
    def network(ip,p,cancel,*,deadline=None):
        if ip.endswith('.3'):raise OSError('must not be persisted or logged')
        return dict(outcome='responded' if ip.endswith('.1') else 'no_response',evidence={'method':'tcp_connect','ports':[]})
    worker=Worker(repo,policy(),None,network);assert worker.run_one()
    result=repo.job(__import__('uuid').UUID(job['id']))
    assert result['status']=='completed' and result['processed']==3
    assert {o['outcome'] for o in result['observations']}=={'responded','no_response','error'}
    assert all(o['hostname'] is None and o['confidence'] is None and o['verification_status']=='unverified' for o in result['observations'])
    candidate=next(o for o in result['observations'] if o['outcome']=='responded')
    repo.enqueue(policy(),'10.42.0.1/32',identity);worker.run_one()
    old=repo.candidate(__import__('uuid').UUID(candidate['id']),true())
    assert len(old['previous_observations'])==1
    with repo.transaction() as s:assert s.scalar(select(func.count()).select_from(Resource))==0


def test_cancel_inflight_is_bounded_and_preserves_evidence(store):
    repo,_,identity=store;job=repo.enqueue(policy(),'10.42.0.1-10.42.0.8',identity)
    entered=Event();release=Event();calls=[]
    def network(ip,p,cancel,*,deadline=None):
        calls.append(ip);entered.set();assert release.wait(2)
        return dict(outcome='no_response',evidence={'method':'tcp_connect','ports':[]})
    worker=Worker(repo,policy(),None,network);thread=Thread(target=worker.run_one);thread.start();assert entered.wait(2)
    repo.cancel(__import__('uuid').UUID(job['id']),identity);release.set();thread.join(3);assert not thread.is_alive()
    result=repo.job(__import__('uuid').UUID(job['id']))
    assert result['status']=='cancelled' and 1<=result['processed']<=2 and len(calls)<=2
    assert len(result['observations'])==result['processed']


def test_job_deadline_and_policy_change_do_not_resume(store):
    repo,_,identity=store;p=policy(job_timeout=.1)
    job=repo.enqueue(p,'10.42.0.1-10.42.0.4',identity)
    def network(*args,**kwargs):time.sleep(.15);return dict(outcome='no_response',evidence={'method':'tcp_connect','ports':[]})
    Worker(repo,p,None,network).run_one()
    assert repo.job(__import__('uuid').UUID(job['id']))['status']=='timed_out'
    job=repo.enqueue(policy(),'10.42.0.1/32',identity);network=Mock(side_effect=AssertionError('no traffic'))
    Worker(repo,policy(ports=[22]),None,network).run_one()
    assert repo.job(__import__('uuid').UUID(job['id']))['status']=='interrupted';network.assert_not_called()


def test_admission_limit_under_concurrent_requests(store):
    repo,_,identity=store
    def enqueue(_):
        try:return repo.enqueue(policy(),'10.42.0.1/32',identity)
        except Problem as e:return e.code
    with ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(enqueue,range(8)))
    assert sum(isinstance(r,dict) for r in results)==2
    assert results.count('discovery_busy')==6


def test_concurrent_duplicate_candidate_addition_is_one_resource_and_decision(store):
    repo,_,identity=store;candidate=observe(repo,identity)
    def add(_):return repo.decide(candidate,creation(),identity,true(),lambda *args:True)
    with ThreadPoolExecutor(max_workers=6) as pool:results=list(pool.map(add,range(6)))
    assert len({r['resource']['id'] for r in results})==1
    assert sum(not r['already_decided'] for r in results)==1
    with repo.transaction() as s:
        assert s.scalar(select(func.count()).select_from(Resource))==1
        assert s.scalar(select(func.count()).select_from(Decision))==1
        assert s.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.action=='discovery.candidate.decided'))==1


def test_repeat_requires_manual_review_or_association_preserving_archived(store):
    repo,_,identity=store;first=observe(repo,identity)
    saved=repo.decide(first,creation(),identity,true(),lambda *args:True)['resource']
    with repo.transaction() as s:
        r=s.get(Resource,__import__('uuid').UUID(saved['id']));r.administrative_state='archived';r.archived_at=now()
    second=observe(repo,identity)
    review=repo.candidate(second,true());assert review['possible_matches'][0]['id']==saved['id']
    with pytest.raises(Problem) as e:repo.decide(second,creation(),identity,true(),lambda *args:True)
    assert e.value.code=='discovery_matches_review'
    associated=repo.decide(second,dict(mode='associate',resource_id=saved['id']),identity,true(),lambda *args:True)
    assert associated['resource']['administrative_state']=='archived'
    with repo.transaction() as s:assert s.scalar(select(func.count()).select_from(Resource))==1
    assert repo.candidate(first,true())['decision']['resource_id']==saved['id']


def test_decision_failure_rolls_back_resource_and_decision(store,monkeypatch):
    repo,_,identity=store;candidate=observe(repo,identity)
    monkeypatch.setattr('app.discovery.service.record_audit_event',Mock(side_effect=RuntimeError('audit failure')))
    with pytest.raises(RuntimeError):repo.decide(candidate,creation(),identity,true(),lambda *args:True)
    with repo.transaction() as s:
        assert s.scalar(select(func.count()).select_from(Resource))==0
        assert s.scalar(select(func.count()).select_from(Decision))==0


def test_api_permissions_scope_and_disabled_mode(store):
    repo,sessions,identity=store
    access=SimpleNamespace(resolve_identity=lambda:identity,read_scope=lambda i:true(),can_create=lambda *args:False)
    app=create_app('testing',inventory_access=access,inventory_session_factory=sessions,discovery_policy=policy())
    app.extensions['discovery']['repository']=repo;client=app.test_client();base='/api/v1/discovery'
    assert client.post(base+'/jobs',json={'target':'10.42.0.1/32'}).status_code==403
    assert client.post(base+'/jobs/'+str(uuid4())+'/cancel').status_code==403
    assert client.post(base+'/candidates/'+str(uuid4())+'/decision',json=creation()).status_code==403
    access.can_create=lambda *args:True
    assert client.post(base+'/jobs',json={'target':'8.8.8.8/32'}).status_code==400
    result=client.post(base+'/jobs',json={'target':'10.42.0.1/32'});assert result.status_code==202
    assert client.get(base+'/jobs/'+result.json['id']).json['status']=='queued'
    assert client.get(base+'/jobs').headers['Cache-Control']=='no-store'
    app.extensions['discovery']['policy']=None
    assert client.get(base+'/config').json['enabled'] is False
    assert client.post(base+'/jobs',json={'target':'10.42.0.1/32'}).status_code==503
    access.resolve_identity=lambda:None
    assert client.get(base+'/jobs').status_code==401


def test_different_candidates_same_ip_are_not_auto_merged_or_silently_duplicated(store):
    repo,_,identity=store;candidates=[observe(repo,identity),observe(repo,identity)]
    def decide(candidate):
        try:return repo.decide(candidate,creation(),identity,true(),lambda *args:True)
        except Problem as error:return error.code
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(decide,candidates))
    assert sum(isinstance(r,dict) for r in results)==1
    assert 'discovery_matches_review' in results
    with repo.transaction() as s:
        assert s.scalar(select(func.count()).select_from(Observation))==2
        assert s.scalar(select(func.count()).select_from(Resource))==1


def test_election_refusal_and_restart_preserve_observations_without_network(store):
    repo,_,identity=store;candidate=observe(repo,identity)
    with repo.transaction() as s:s.get(Job,s.get(Observation,candidate).job_id).status='running'
    leader=Mock();leader.execute.return_value.scalar_one.return_value=False
    network=Mock(side_effect=AssertionError('network forbidden'))
    worker=Worker(repo,policy(),lambda:leader,network);worker.loop();network.assert_not_called()
    assert repo.jobs()[0]['status']=='running'
    leader.execute.return_value.scalar_one.return_value=True
    worker.stop.set();worker.loop()
    assert repo.jobs()[0]['status']=='interrupted'
    assert repo.candidate(candidate,true())['id']==str(candidate)
    network.assert_not_called()


def test_production_transactions_use_database_advisory_lock_before_effects():
    from unittest.mock import MagicMock
    session=MagicMock();session.__enter__.return_value=session
    repo=Repository(lambda:session)
    with repo.transaction(701030114):pass
    sql=session.execute.call_args.args[0]
    assert 'pg_advisory_xact_lock' in str(sql)
    assert session.execute.call_args.args[1]=={'key':701030114}


def test_lost_leader_lock_stops_before_new_probe_or_write(store):
    repo,_,identity=store;repo.enqueue(policy(),'10.42.0.1/32',identity)
    connection=Mock();connection.execute.return_value.scalar_one.return_value=False
    network=Mock(side_effect=AssertionError('must not probe'))
    worker=Worker(repo,policy(),None,network);worker.leader_connection=connection
    with pytest.raises(RuntimeError):worker.run_one()
    assert worker.stop.is_set() and repo.jobs()[0]['status']=='queued'
    network.assert_not_called()


def test_full_configured_subnet_has_254_hosts_and_excludes_endpoints():
    p=policy(max_targets=254,concurrency=8,ports=list(range(1001,1007)),target_timeout=1,job_timeout=300)
    addresses=p.targets('10.42.0.0/24')
    assert len(addresses)==254 and addresses[0]=='10.42.0.1' and addresses[-1]=='10.42.0.254'
    assert p.targets('10.42.0.1-10.42.0.254')==addresses
    for target in ('10.42.0.0/32','10.42.0.255/32','10.42.0.0-10.42.0.1','10.42.0.254-10.42.0.255','10.43.0.1/32'):
        with pytest.raises(ValueError):p.targets(target)
    for ports in (list(range(1001,1008)),[[22]],['22'],[True]):
        with pytest.raises(ValueError):policy(ports=ports)


@pytest.mark.parametrize('budget,attempts,elapsed',[(None,6,6),(2.5,3,2.5)])
def test_each_connection_has_own_timeout_bounded_by_job_deadline(monkeypatch,budget,attempts,elapsed):
    clock=[0.0];timeouts=[];ports=[]
    monkeypatch.setattr('app.discovery.network.time.monotonic',lambda:clock[0])
    class Socket:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def settimeout(self,value):self.timeout=value;timeouts.append(value)
        def connect_ex(self,address):
            ports.append(address[1]);clock[0]+=self.timeout
            return errno.ETIMEDOUT
    monkeypatch.setattr('app.discovery.network.socket.socket',lambda *args:Socket())
    p=policy(ports=list(range(1001,1007)),target_timeout=1)
    result=probe('10.42.0.1',p,deadline=budget)
    assert len(ports)==attempts and len(set(ports))==attempts
    assert timeouts==([1]*6 if budget is None else [1,1,.5])
    assert clock[0]==elapsed and result['outcome']=='no_response'
    assert len(result['evidence']['ports'])==attempts


def test_cancellation_stops_remaining_ports_without_retry(monkeypatch):
    calls=[];cancel=Event()
    class Socket:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def settimeout(self,value):assert value<=1
        def connect_ex(self,address):calls.append(address);cancel.set();return errno.ECONNREFUSED
    monkeypatch.setattr('app.discovery.network.socket.socket',lambda *args:Socket())
    result=probe('10.42.0.1',policy(ports=list(range(1001,1007)),target_timeout=1),cancel.is_set)
    assert calls==[('10.42.0.1',1001)] and len(result['evidence']['ports'])==1


def test_eight_target_threads_are_bounded_and_cancellable(store):
    repo,_,identity=store;p=policy(concurrency=8)
    job=repo.enqueue(p,'10.42.0.1-10.42.0.16',identity)
    entered=Event();release=Event();lock=RLock();calls=[];active=[0];maximum=[0];deadlines=[]
    def network(ip,p,cancel,*,deadline=None):
        with lock:
            calls.append(ip);active[0]+=1;maximum[0]=max(maximum[0],active[0]);deadlines.append(deadline)
            if active[0]==8:entered.set()
        assert release.wait(5)
        with lock:active[0]-=1
        return dict(outcome='no_response',evidence={'method':'tcp_connect','ports':[]})
    worker=Worker(repo,p,None,network);thread=Thread(target=worker.run_one);thread.start()
    try:
        assert entered.wait(5)
        repo.cancel(__import__('uuid').UUID(job['id']),identity)
    finally:release.set();thread.join(5)
    assert not thread.is_alive() and maximum[0]==8 and len(calls)==8
    assert deadlines[0] is not None and len(set(deadlines))==1
    assert repo.job(__import__('uuid').UUID(job['id']))['status']=='cancelled'


@pytest.mark.parametrize('number,result,code',[
    (errno.ECONNREFUSED,'refused','ECONNREFUSED'),(errno.ETIMEDOUT,'timeout','ETIMEDOUT'),
    (errno.EAGAIN,'timeout','EAGAIN'),(errno.ENETUNREACH,'unreachable','ENETUNREACH'),
    (errno.EHOSTUNREACH,'unreachable','EHOSTUNREACH'),(errno.EACCES,'local_error','EACCES'),
    (errno.EMFILE,'local_error','EMFILE'),(99999,'error','UNCLASSIFIED_CONNECT_ERROR')])
def test_future_tcp_errors_have_safe_diagnostic_codes(monkeypatch,number,result,code):
    connection=Mock();connection.__enter__=lambda self:self;connection.__exit__=lambda *args:False
    connection.connect_ex.return_value=number
    monkeypatch.setattr('app.discovery.network.socket.socket',Mock(return_value=connection))
    evidence=probe('10.42.0.1',policy(ports=[445]))['evidence']['ports']
    assert evidence==[dict(port=445,result=result,code=code,errno=number)]


@pytest.mark.parametrize('failure,expected',[(PermissionError(errno.EACCES,'private diagnostic must never persist'),
    dict(result='local_error',code='EACCES',errno=errno.EACCES)),
    (OSError(errno.EHOSTUNREACH,'private route information'),dict(result='unreachable',code='EHOSTUNREACH',errno=errno.EHOSTUNREACH)),
    (TimeoutError('private timeout text'),dict(result='timeout',code='SOCKET_TIMEOUT')),
    (OSError('private local path'),dict(result='error',code='OS_ERROR_WITHOUT_ERRNO'))])
def test_socket_exceptions_persist_codes_without_exception_messages(monkeypatch,failure,expected):
    monkeypatch.setattr('app.discovery.network.socket.socket',Mock(side_effect=failure))
    evidence=probe('10.42.0.1',policy(ports=[445]))['evidence']['ports']
    assert evidence==[dict(port=445,**expected)]
    assert 'private' not in json.dumps(evidence)


def test_refused_port_with_other_errors_is_not_whole_target_failure(monkeypatch):
    connection=Mock();connection.__enter__=lambda self:self;connection.__exit__=lambda *args:False
    connection.connect_ex.side_effect=[errno.EACCES,errno.ECONNREFUSED]
    monkeypatch.setattr('app.discovery.network.socket.socket',Mock(return_value=connection))
    result=probe('10.42.0.1',policy())
    assert result['outcome']=='responded'
    assert [p['result'] for p in result['evidence']['ports']]==['local_error','refused']
