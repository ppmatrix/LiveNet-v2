"""Real PostgreSQL locks/commits over a private Unix socket, never DEV/TCP.

Uses installed PostgreSQL 16 binaries. No image, package or service installation.
The cluster is created by initdb inside pytest's fresh private directory and
stopped only after checking its data directory and original postmaster PID.
"""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy import create_engine,text,MetaData,select,func
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from test_discovery import policy,prohibit_real_detection_sockets
from app.audit.models import AuditEvent
from app.inventory.models import Resource,ResourceIdentifier
from app.inventory.access import InventoryIdentity
from app.discovery.models import Job,Observation,Decision
from app.discovery.service import Repository,Problem,LEADER_KEY
from app.discovery.coordinator import Coordinator
from app.discovery.journal import Journal
from app.discovery.worker import Worker


@pytest.fixture(scope='module')
def postgres(tmp_path_factory):
    binaries=Path('/usr/lib/postgresql/16/bin')
    assert (binaries/'initdb').is_file(),'Installed PostgreSQL 16 required; never download it'
    root=tmp_path_factory.mktemp('discovery-pg');root.chmod(0o700)
    data=root/'data';socket=root/'s';socket.mkdir(mode=0o700)
    env={k:v for k,v in os.environ.items() if not k.startswith('PG')}
    def command(args):
        return subprocess.run(args,env=env,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
    command([str(binaries/'initdb'),'-D',str(data),'-A','trust','-U','discovery_test_bootstrap','--no-locale','-E','UTF8'])
    command([str(binaries/'pg_ctl'),'-D',str(data),'-l',str(root/'server.log'),'-o',
             '-k '+shlex.quote(str(socket))+" -c listen_addresses='' -c fsync=on",'-w','start'])
    pid=(data/'postmaster.pid').read_text().splitlines()[0]
    def engine(user,database):
        return create_engine(URL.create('postgresql+psycopg',username=user,host=str(socket),database=database),
                             poolclass=NullPool,echo=False,hide_parameters=True)
    bootstrap=engine('discovery_test_bootstrap','postgres')
    admin=runtime=None
    try:
        with bootstrap.connect().execution_options(isolation_level='AUTOCOMMIT') as c:
            assert Path(c.execute(text('SHOW data_directory')).scalar_one())==data
            assert c.execute(text('SHOW listen_addresses')).scalar_one()==''
            c.execute(text('CREATE DATABASE discovery_lifecycle_test'))
            c.execute(text('CREATE ROLE discovery_test_runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS'))
        admin=engine('discovery_test_bootstrap','discovery_lifecycle_test')
        runtime=engine('discovery_test_runtime','discovery_lifecycle_test')
        with admin.begin() as c:
            for schema in ('inventory','audit','discovery'):c.execute(text('CREATE SCHEMA '+schema))
            c.execute(text('REVOKE CREATE,TEMP ON DATABASE discovery_lifecycle_test FROM PUBLIC'))
            metadata=MetaData()
            for model in (Resource,ResourceIdentifier,AuditEvent,Job,Observation,Decision):model.__table__.to_metadata(metadata)
            metadata.create_all(c)
            c.execute(text('GRANT USAGE ON SCHEMA inventory,audit,discovery TO discovery_test_runtime'))
            c.execute(text('GRANT SELECT,INSERT ON discovery.jobs,discovery.observations,discovery.decisions TO discovery_test_runtime'))
            c.execute(text('GRANT UPDATE(status,processed,finished_at) ON discovery.jobs TO discovery_test_runtime'))
            c.execute(text('GRANT SELECT ON inventory.resources,inventory.resource_identifiers TO discovery_test_runtime'))
            c.execute(text('GRANT INSERT ON audit.events TO discovery_test_runtime'))
            c.execute(text('GRANT SELECT(id,occurred_at) ON audit.events TO discovery_test_runtime'))
        yield SimpleNamespace(admin=admin,runtime=runtime,socket=socket,root=root,data=data)
    finally:
        if runtime is not None:runtime.dispose()
        if admin is not None:admin.dispose()
        bootstrap.dispose()
        lines=(data/'postmaster.pid').read_text().splitlines()
        assert lines[0]==pid and Path(lines[1])==data
        command([str(binaries/'pg_ctl'),'-D',str(data),'-m','fast','-w','stop'])
        assert not (data/'postmaster.pid').exists()


@pytest.fixture
def pg_store(postgres,tmp_path):
    with postgres.admin.begin() as c:
        assert Path(c.execute(text('SHOW data_directory')).scalar_one())==postgres.data
        c.execute(text('TRUNCATE discovery.decisions,discovery.observations,discovery.jobs,audit.events,inventory.resource_identifiers,inventory.resources'))
    repo=Repository(sessionmaker(bind=postgres.runtime,expire_on_commit=False))
    workers=[]
    def make():
        coord=Coordinator(repo,policy(),Journal(tmp_path/'journal','pg-fixture'))
        worker=Worker(repo,policy(),lambda:postgres.runtime.connect(),Mock(side_effect=AssertionError('No real probes')),coordinator=coord)
        workers.append(worker);return worker
    yield repo,make,InventoryIdentity(uuid4())
    for worker in workers:worker.stop.set()
    for worker in workers:
        if worker.thread is not None:worker.thread.join(5);assert not worker.thread.is_alive()
        else:worker.close()


def test_real_pg_election_has_one_leader_and_no_automatic_failover(pg_store):
    repo,make,_=pg_store;first,second=make(),make()
    first.start();second.start();deadline=time.monotonic()+5
    while any(w.coordinator.state=='STARTING' for w in (first,second)) and time.monotonic()<deadline:time.sleep(.01)
    assert sorted(w.coordinator.state for w in (first,second))==['BLOCKED','READY']
    with repo.transaction() as s:
        assert s.scalar(text("SELECT count(*) FROM pg_locks WHERE locktype='advisory' AND objid=:key AND granted"),dict(key=LEADER_KEY))==1
    for worker in (first,second):worker.probe.assert_not_called()


def test_real_pg_global_admission_lock_serializes_clients(pg_store):
    repo,make,identity=pg_store;worker=make();worker.acquire()
    def submit(_):
        try:return repo.enqueue(policy(max_jobs=1),'10.42.0.1/32',identity,lease=worker.coordinator.lease)
        except Problem as e:return e.code
    with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(submit,range(4)))
    assert sum(isinstance(r,dict) for r in results)==1 and results.count('discovery_busy')==3
    worker.probe.assert_not_called()


def test_real_pg_restricted_runtime_commits_and_confirms_attempt(pg_store):
    repo,make,identity=pg_store;worker=make();worker.acquire()
    worker.probe=Mock(return_value=dict(outcome='no_response',evidence=dict(method='tcp_connect',ports=[])))
    job=worker.coordinator.submit('10.42.0.1-10.42.0.2',identity)
    assert worker.run_one()
    row=repo.job(__import__('uuid').UUID(job['id']))
    assert row['status']=='completed' and row['processed']==2 and len(row['observations'])==2
    assert worker.probe.call_count==2 and worker.coordinator.journal.read('attempt') is None
    assert worker.run_one() is False


def test_real_pg_cli_recovers_dead_child_without_network(postgres,pg_store,tmp_path,monkeypatch,capsys):
    from installation.discovery import journal_for
    from installation.__main__ import main
    repo,_,_=pg_store
    with postgres.admin.connect() as c:sid=c.execute(text('SELECT (pg_control_system()).system_identifier::text')).scalar_one()
    settings=SimpleNamespace(values=dict(database=dict(host='127.0.0.1',port=5432,name='discovery_lifecycle_test',system_identifier=sid,sslmode='disable',ca_file=None),
        roles=dict(admin='discovery_test_bootstrap',runtime='discovery_test_runtime',migrator='unused_test_migrator'),state_dir=str(tmp_path/'state')))
    settings.connect=lambda role:(postgres.admin if role=='admin' else postgres.runtime).connect()
    journal=journal_for(settings)
    program=r'''
import sys,socket
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import sessionmaker
from uuid import uuid4
from app.discovery.service import Repository
from app.discovery.policy import Policy
from app.discovery.journal import Journal
from app.discovery.coordinator import Coordinator
from app.discovery.worker import Worker
from app.inventory.access import InventoryIdentity
def forbidden(*a,**k):raise AssertionError('Real network forbidden')
socket.socket=forbidden
engine=create_engine(URL.create('postgresql+psycopg',username='discovery_test_runtime',host=sys.argv[1],database='discovery_lifecycle_test'),poolclass=NullPool,hide_parameters=True)
repo=Repository(sessionmaker(bind=engine,expire_on_commit=False))
p=Policy.from_mapping(dict(networks=['10.42.0.0/24'],ports=[22],max_targets=1,concurrency=1,target_timeout=.1,job_timeout=1,max_jobs=1))
c=Coordinator(repo,p,Journal(Path(sys.argv[2]),sys.argv[3]))
w=Worker(repo,p,lambda:engine.connect(),forbidden,coordinator=c)
w.acquire();c.submit('10.42.0.1/32',InventoryIdentity(uuid4()))
repo.confirm_running=lambda *a: (_ for _ in ()).throw(RuntimeError('constructed lost COMMIT response'))
try:w.run_one()
except RuntimeError:pass
assert c.state=='BLOCKED' and (c.journal.directory/'attempt.json').exists()
w.close();engine.dispose()
'''
    env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[1]),PYTHONDONTWRITEBYTECODE='1')
    env.pop('LIVENET_DISCOVERY_CONFIG',None)
    subprocess.run([sys.executable,'-B','-c',program,str(postgres.socket),str(journal.directory),journal.binding],env=env,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=15)
    monkeypatch.setattr('installation.__main__.Settings.load',lambda path:settings)
    assert main(['discovery-recover','--config','isolated-fixture','--confirm-reviewed'])==0
    assert json.loads(capsys.readouterr().out)['state']=='RECOVERED'
    with repo.transaction() as s:
        assert s.scalar(select(Job.status))=='interrupted'
        assert s.scalar(select(func.count()).select_from(Observation))==0
        audits=s.scalar(select(func.count()).select_from(AuditEvent))
    # First recovery ran within this pytest PID. A new call must conservatively
    # refuse to assume it is absent; repeated clean recovery is covered separately.
    assert audits==3
