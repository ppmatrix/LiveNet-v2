"""Local synthetic launcher tests. No Docker, SQL, network, image or real secrets."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import socket
import subprocess

import pytest
import sqlalchemy

from scripts.postgres import dev09b_querytrial_launcher as l
from scripts.postgres.tests.test_dev09b_query_trial import Connection


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def denied(*a,**kw):raise AssertionError('No Docker/process/network/real connections')
    for obj,key in ((socket,'socket'),(socket,'create_connection'),(subprocess,'run'),(subprocess,'Popen'),(sqlalchemy,'create_engine')):
        monkeypatch.setattr(obj,key,denied)
    for key in ('DOCKER_HOST','DOCKER_CONTEXT','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH'):
        monkeypatch.delenv(key,raising=False)


@pytest.fixture
def state(tmp_path,monkeypatch):
    p=tmp_path/'private';p.mkdir(mode=0o700)
    monkeypatch.setenv('DEV09B_QUERYTRIAL_STATE_DIR',str(p))
    return p


def resources(state):
    netid='b'*64;container='c'*64
    image=dict(RepoDigests=[l.DIGEST],Id='sha256:'+'a'*64,Os='linux',Architecture='amd64')
    network=dict(Id=netid,Driver='bridge',Internal=True,Options={},Labels={'com.docker.compose.project':l.PROJECT,'com.docker.compose.network':'backend'})
    volume=dict(CreatedAt='fixture-created',Labels={'com.docker.compose.project':l.PROJECT,'com.docker.compose.volume':'querytrial_data'})
    db=dict(Id=container,Image=image['Id'],State=dict(Running=True),HostConfig=dict(Privileged=False,PortBindings={}),
        Config=dict(Labels={'com.docker.compose.project':l.PROJECT,'com.docker.compose.service':'db','com.docker.compose.project.working_dir':str(l.ROOT)}),
        NetworkSettings=dict(Ports={'5432/tcp':None},Networks={l.NETWORK:dict(NetworkID=netid,IPAddress='172.31.9.2')}),
        Mounts=[dict(Destination='/var/lib/postgresql/data',Type='volume',Name=l.VOLUME),dict(Destination='/run/secrets/querytrial_admin_password',Source=str(state/'admin_password'),RW=False)])
    return image,network,volume,db


def stub_docker(monkeypatch,state):
    image,network,volume,db=resources(state)
    calls=[]
    def command(argv,**kw):
        calls.append((argv,kw))
        if argv[:3]==['docker','context','inspect']:return json.dumps([dict(Endpoints={'docker':dict(Host='unix:///var/run/docker.sock')})])
        if argv[:2]==['docker','info']:return json.dumps(dict(OSType='linux',OperatingSystem='Linux',SecurityOptions=['name=seccomp']))
        if argv[:3]==['docker','image','inspect']:return json.dumps([image])
        if argv[:2]==['docker','ps']:return db['Id']+'\n'
        if argv[:2]==['docker','inspect']:return json.dumps([db])
        if argv[:3]==['docker','network','inspect']:return json.dumps([network])
        if argv[:3]==['docker','volume','inspect']:return json.dumps([volume])
        if argv[:4]==['ip','-j','route','get']:return json.dumps([dict(dev='br-'+network['Id'][:12],prefsrc='172.31.9.1')])
        if 'pg_controldata' in argv:return 'Database system identifier:            123\n'
        if argv[:2]==['docker','exec'] and 'input' in kw:return ''
        raise AssertionError('Unexpected command')
    monkeypatch.setattr(l,'command',command)
    return image,network,volume,db,calls


def test_compose_digest_isolation_and_no_installer():
    c=json.loads((l.ROOT/'compose.dev09b-querytrial.yaml').read_bytes());db=c['services']['db']
    assert c['name']==l.PROJECT and set(c['services'])=={'db'}
    assert db['image']==l.IMAGE and db['pull_policy']=='never' and db['restart']=='no'
    assert 'ports' not in db and 'network_mode' not in db and 'build' not in db
    assert db['networks']==['backend'] and c['networks']['backend']['internal'] is True
    assert not c['networks']['backend'].get('external') and not c['volumes']['querytrial_data'].get('external')
    assert db['environment']['POSTGRES_DB']==l.DATABASE
    assert 'POSTGRES_PASSWORD' not in db['environment']
    assert len(db['volumes'])==1 and '/docker-entrypoint-initdb.d' not in json.dumps(c)
    assert 'CREATE EXTENSION' not in json.dumps(c)


def test_private_secret_creation_and_no_overwrite(state):
    l.make_secrets()
    for name in ('admin_password','probe_password'):
        p=state/name
        assert len(l.password(p))>=32 and p.stat().st_mode & 0o777==0o600
    with pytest.raises(l.Refused,match='SECRETS_ALREADY_EXIST'):l.make_secrets()


def test_unsafe_secret_path_and_permissions(state,monkeypatch,tmp_path):
    monkeypatch.setenv('DEV09B_QUERYTRIAL_STATE_DIR',str(l.ROOT/'secrets/querytrial'))
    with pytest.raises(l.Refused,match='OUTSIDE_GIT'):l.state_dir()
    monkeypatch.setenv('DEV09B_QUERYTRIAL_STATE_DIR',str(state))
    (state/'probe_password').write_text('x'*64)
    with pytest.raises(l.Refused,match='PRIVATE_FILE'):l.password(state/'probe_password')
    (state/'probe_password').unlink()
    (state/'probe_password').symlink_to(tmp_path/'missing')
    with pytest.raises(OSError):l.password(state/'probe_password')


def test_topology_direct_route_and_independent_identifier(state,monkeypatch):
    *_,calls=stub_docker(monkeypatch,state)
    record=l.identify()
    assert record['system_identifier']=='123' and record['channel']=='docker-exec-pg_controldata'
    assert l.checked_record('123')==record
    assert any(argv[:4]==['ip','-j','route','get'] for argv,_ in calls)
    assert not any('psql' in arg for argv,_ in calls for arg in argv)
    with pytest.raises(l.Refused,match='CONFIRMATION'):l.checked_record('124')


@pytest.mark.parametrize('mutation,code',[
    (lambda im,n,v,d:d['HostConfig'].update(PortBindings={'5432/tcp':[{}]}),'ISOLATION'),
    (lambda im,n,v,d:d['NetworkSettings']['Networks'].update(other={}),'NETWORK_ONLY'),
    (lambda im,n,v,d:n.update(Internal=False),'INTERNAL'),
    (lambda im,n,v,d:im.update(RepoDigests=[]),'PINNED'),
    (lambda im,n,v,d:v['Labels'].update({'com.docker.compose.project':'other'}),'PROVENANCE'),
    (lambda im,n,v,d:d['Mounts'][0].update(Type='bind'),'VOLUME'),
])
def test_resource_divergence_refused(state,monkeypatch,mutation,code):
    im,n,v,d,_=stub_docker(monkeypatch,state);mutation(im,n,v,d)
    with pytest.raises(l.Refused,match=code):l.topology(route=True)


@pytest.mark.parametrize('where',['route','context','rootless','desktop'])
def test_no_fallback_for_inaccessible_host_bridge(state,monkeypatch,where):
    stub_docker(monkeypatch,state);original=l.command
    def command(argv,**kw):
        if where=='route' and argv[0]=='ip':return json.dumps([dict(dev='eth0',gateway='192.0.2.1')])
        if where=='context' and argv[:3]==['docker','context','inspect']:return json.dumps([dict(Endpoints={'docker':dict(Host='ssh://other')})])
        if where in {'rootless','desktop'} and argv[:2]==['docker','info']:
            return json.dumps(dict(OSType='linux',OperatingSystem='Docker Desktop' if where=='desktop' else 'Linux',SecurityOptions=['name=rootless'] if where=='rootless' else []))
        return original(argv,**kw)
    monkeypatch.setattr(l,'command',command)
    with pytest.raises(l.Refused):l.topology(route=True)


def test_admin_stdin_only_empty_guard_and_no_schemas_or_extensions(state,monkeypatch):
    l.make_secrets();*_,calls=stub_docker(monkeypatch,state);l.identify()
    l.prepare_admin('123')
    argv,kw=calls[-1];sql=kw['input']
    assert l.password(state/'probe_password') not in sql
    assert l.password(state/'admin_password') not in ' '.join(argv)
    assert 'SCRAM-SHA-256$4096:' in sql and 'SCRAM-SHA-256' not in ' '.join(argv)
    assert 'NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS' in sql
    assert 'system_identifier::pg_catalog.text=\'123\'' in sql and '\\if :target_empty' in sql
    assert 'CREATE SCHEMA' not in sql and 'CREATE EXTENSION' not in sql
    assert 'IF NOT EXISTS' not in sql and '\\quit 3' in sql
    assert '-h /var/run/postgresql -p 5432' in argv[-1]


def test_scram_ascii_password_not_exposed(state,monkeypatch):
    import base64,hmac
    monkeypatch.setattr(l.secrets,'token_bytes',lambda n:b'\x00'*n)
    verifier=l.scram_verifier('x'*64)
    algorithm,iterations,salt,stored,server=verifier.replace('$',':').split(':')
    assert algorithm=='SCRAM-SHA-256' and iterations=='4096'
    salted=hashlib.pbkdf2_hmac('sha256',b'x'*64,base64.b64decode(salt),4096)
    client=hmac.digest(salted,b'Client Key','sha256')
    assert base64.b64decode(stored)==hashlib.sha256(client).digest()
    assert base64.b64decode(server)==hmac.digest(salted,b'Server Key','sha256')


def test_launcher_run_empty_counts_not_operational_and_engine_cleanup(state,monkeypatch):
    l.make_secrets();stub_docker(monkeypatch,state);record=l.identify()
    conn=Connection();conn.identity.update(current_user=l.PROBE,session_user=l.PROBE,address=record['address'])
    engine=SimpleNamespace(connect=lambda:conn,dispose=Mock())
    captured={}
    def create(url,**kwargs):captured.update(url=url,kwargs=kwargs);return engine
    monkeypatch.setattr(sqlalchemy,'create_engine',create)
    result=l.run('123')
    assert result['trial']['status']=='COMPLETED' and result['query_errors']=={}
    assert any(q['status']=='SUCCESS' and q['rows']==0 for q in result['trial']['queries'])
    assert result['trial']['scope']=='QUERY_TRIAL_ONLY'
    assert captured['url'].host==record['address'] and captured['url'].username==l.PROBE
    assert captured['kwargs']['echo'] is False and captured['kwargs']['hide_parameters'] is True
    assert captured['kwargs']['connect_args']['connect_timeout']==5
    assert conn.closed and engine.dispose.call_count==1
    assert l.password(state/'probe_password') not in json.dumps(result)


@pytest.mark.parametrize('sqlstate,expected',[('42501','PERMISSION_DENIED'),('42601','SQL_ERROR'),('42883','SQL_ERROR'),('08006','CONNECTION_ERROR'),(None,'QUERY_FAILED')])
def test_sql_permission_errors_differ_from_successful_empty_results(state,monkeypatch,sqlstate,expected):
    from backend.migrations.dev09b_inspection_queries import QUERIES
    from scripts.postgres.dev09b_query_trial import run_trial,TrialTarget
    conn=Connection()
    class Failure(Exception):
        orig=SimpleNamespace(sqlstate=sqlstate)
    def fail(connection,sql):
        if sql==QUERIES['extension'].sql:raise Failure('password=DO_NOT_LOG')
    conn.callback=fail
    wrapper=l.ObservedConnection(conn)
    report=run_trial(wrapper,TrialTarget('livenet_v2_dev','123','fixture_probe','192.0.2.4'))
    assert report.status=='REFUSED' and wrapper.errors=={'extension':expected}
    assert 'DO_NOT_LOG' not in report.to_json()
    assert any(q.status=='SUCCESS' and q.rows==0 for q in report.queries)
    assert conn.closed


def test_redacted_cli_errors_and_no_env_remote(monkeypatch,capsys):
    monkeypatch.setattr(l,'identify',Mock(side_effect=RuntimeError('password=DO_NOT_LOG')))
    assert l.main(['identify'])==2
    assert 'DO_NOT_LOG' not in capsys.readouterr().out
    monkeypatch.setenv('DOCKER_HOST','ssh://other')
    with pytest.raises(l.Refused,match='DOCKER_ENV_OVERRIDE'):l.command(['docker','image','inspect',l.IMAGE])


def test_check_host_has_no_resource_creation(state,monkeypatch,capsys):
    *_,calls=stub_docker(monkeypatch,state)
    assert l.main(['check-host'])==0
    assert 'LOCAL_NATIVE_HOST_AND_IMAGE_CHECKED' in capsys.readouterr().out
    assert len(calls)==3
    assert all(argv[:2] in (['docker','context'],['docker','info'],['docker','image']) for argv,_ in calls)


def test_connection_failure_is_redacted_and_disposes_engine(state,monkeypatch,capsys):
    l.make_secrets();stub_docker(monkeypatch,state);l.identify()
    def broken():raise RuntimeError('postgresql://user:DO_NOT_LOG@host')
    engine=SimpleNamespace(connect=broken,dispose=Mock())
    monkeypatch.setattr(sqlalchemy,'create_engine',lambda *a,**kw:engine)
    assert l.main(['run','--confirm-system-identifier','123'])==2
    assert engine.dispose.call_count==1 and 'DO_NOT_LOG' not in capsys.readouterr().out
