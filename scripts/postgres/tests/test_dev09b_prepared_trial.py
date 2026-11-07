"""Prepared-origin trial tests. All Docker, SQL, connections and credentials fake."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import json
import socket
import subprocess

import pytest
import sqlalchemy

from scripts.postgres import dev09b_prepared_trial as p
from scripts.postgres.tests.test_dev09b_query_trial import Connection

ROOT=Path(__file__).resolve().parents[3]


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def denied(*a,**kw):raise AssertionError('No processes, network, Docker, real SQL or engine')
    for owner,name in ((subprocess,'run'),(subprocess,'Popen'),(socket,'socket'),(socket,'create_connection'),(sqlalchemy,'create_engine')):
        monkeypatch.setattr(owner,name,denied)


def fixed():
    e=json.loads((ROOT/'scripts/postgres/dev09b_prepared_expectations.proposed.json').read_bytes())
    # Intent chosen by the test BEFORE any synthetic observation is generated.
    e['probe_settings']['lc_collate']='C';e['probe_settings']['lc_ctype']='C'
    return p.expectations(p.canonical(e))


def record():
    return dict(schema_version=1,channel='docker-exec-pg_controldata',system_identifier='7705421224394444834',
                image_id='sha256:'+'a'*64,container_id='b'*64,network_id='c'*64,address='192.0.2.4',volume=p.l.VOLUME,volume_created='fixture')


def evidence(e,r,pid=42):
    return dict(schema_version=1,scope='LOCAL_ADMIN_TRIAL_OBSERVATION',channel='docker-exec-psql',operational_authority=False,
        record_sha256=sha256(p.canonical(r)).hexdigest(),expectations_sha256=sha256(p.canonical(e)).hexdigest(),
        observation=dict(database=p.l.DATABASE,system_identifier=r['system_identifier'],postmaster_start='fixture-server',
        current_user=p.l.ADMIN,session_user=p.l.ADMIN,pid=pid,backend_start='fixture-admin-'+str(pid),
        settings=[dict(name=k,setting=v) for k,v in e['admin_settings'].items()]))


def fixture():
    e=fixed();r=record();before=evidence(e,r);after=evidence(e,r,43)
    owners=[dict(name=name,login=False,superuser=False,createdb=False,createrole=False,replication=False,bypassrls=False,inherit=False) for name in e['schema_owners'].values()]
    meta=dict(database=p.l.DATABASE,system_identifier=r['system_identifier'],postmaster_start='fixture-server',
              current_user=p.l.PROBE,session_user=p.l.PROBE,pid=123,backend_start='fixture-probe',owners=owners,owner_memberships=[])
    first=dict(pid=123,backend_start='fixture-probe')
    data=dict(identity=[[deepcopy(first)],[deepcopy(first)]],
        settings=[[dict(name=k,setting=None if k in p.RESTRICTED else v) for k,v in e['probe_settings'].items()]],
        schemas=[[dict(name=k,owner=v,owner_login=False,can_create=False,can_use=False,grant_create=False,grant_use=False) for k,v in e['schema_owners'].items()]],
        schema_acl=[[dict(name=k,grantee=v,grantor=v,privilege=right,grant_option=False) for k,v in e['schema_owners'].items() for right in ('USAGE','CREATE')]],
        namespace_objects=[[]],extension=[[deepcopy(e['extension'])]],
        extension_acl=[[dict(extension='btree_gist',grantee=p.l.ADMIN,grantor=p.l.ADMIN,privilege='EXECUTE',grant_option=False)]],
        privileges=[[dict(database_create=False,database_temporary=False,superuser=False)]],
        memberships=[[dict(role=name,member=False,inherited=False,can_set=False) for name in (*e['schema_owners'].values(),p.l.ADMIN)]])
    return e,r,before,after,meta,data


def test_proposed_missing_locales_refuse_before_resources(tmp_path,monkeypatch):
    path=ROOT/'scripts/postgres/dev09b_prepared_expectations.proposed.json'
    with pytest.raises(p.l.Refused,match='MISSING_EXPECTATION_LC_COLLATE'):p.execute(path,'7705421224394444834','04')
    assert json.loads(path.read_bytes())['probe_settings']['lc_collate'] is None


def test_duplicate_json_and_source_tampering_refuse():
    with pytest.raises(p.l.Refused,match='DUPLICATE_JSON_FIELD'):p.expectations(b'{"schema_version":1,"schema_version":1}')
    e=fixed();e['sql_sha256']='0'*64
    with pytest.raises(p.l.Refused,match='SQL_BYTES_DIVERGENCE'):p.expectations(p.canonical(e))
    e=fixed();e['query_catalog_sha256']='0'*64
    with pytest.raises(p.l.Refused,match='QUERY_CATALOG_DIVERGENCE'):p.expectations(p.canonical(e))


def test_local_observation_not_operational_authority_or_probe_session():
    e,r,b,a,m,s=fixture()
    result=p.compare_prepared(e,r,b,a,m,s)
    assert result['status']=='LOCAL_PREPARED_TRIAL_MATCHED' and result['operational_authority'] is False
    assert result['session_preload_libraries_admin']=='ADMIN_SESSION_MATCHED_ONLY'
    assert result['session_preload_libraries_probe']=='UNOBSERVED'
    assert result['probe_unavailable']==list(p.RESTRICTED)
    assert result['full_operational_profile_validated'] is False
    assert all(row['setting'] is None for row in s['settings'][0] if row['name'] in p.RESTRICTED)
    # Divergent declared expectation for probe's own session cannot be satisfied
    # by copying the successful admin-session observation into the probe map.
    e['probe_settings']['session_preload_libraries']='fixture-probe-only-library'
    for admin in (b,a):admin['expectations_sha256']=sha256(p.canonical(e)).hexdigest()
    assert p.compare_prepared(e,r,b,a,m,s)['session_preload_libraries_probe']=='UNOBSERVED'


@pytest.mark.parametrize('mutation,code',[
    (lambda b:b.update(operational_authority=True),'NOT_OPERATIONAL'),
    (lambda b:b.update(scope='OPERATIONAL'),'NOT_OPERATIONAL'),
    (lambda b:b.update(record_sha256='0'*64),'BINDING'),
    (lambda b:b['observation'].update(system_identifier='999'),'TARGET'),
    (lambda b:b['observation']['settings'].pop(),'COVERAGE'),
    (lambda b:b['observation']['settings'][0].update(setting='observed-but-not-expected'),'MISMATCH'),
])
def test_admin_evidence_strict_bindings_and_fixed_expectations(mutation,code):
    e,r,b,a,m,s=fixture();mutation(b)
    with pytest.raises(p.l.Refused,match=code):p.compare_admin(b,e,r)


@pytest.mark.parametrize('mutation,code',[
    (lambda a,m,s:a['observation'].update(postmaster_start='restarted'),'CONTINUITY'),
    (lambda a,m,s:m.update(pid=42),'INDEPENDENT'),
    (lambda a,m,s:s['identity'][1][0].update(pid=999),'SESSION'),
    (lambda a,m,s:s['settings'][0][0].update(setting='changed'),'SETTINGS'),
    (lambda a,m,s:m['owners'][0].update(login=True),'OWNER_POWER'),
    (lambda a,m,s:m.update(owner_memberships=[{}]),'OWNER_MEMBERSHIP'),
    (lambda a,m,s:s['schema_acl'][0].pop(),'ACL'),
    (lambda a,m,s:s['namespace_objects'][0].append(dict(schema='inventory')),'RESIDUE'),
    (lambda a,m,s:s['extension'][0][0].update(version='wrong'),'EXTENSION'),
    (lambda a,m,s:s['extension_acl'][0][0].update(grantee='PUBLIC'),'ACL'),
    (lambda a,m,s:s['privileges'][0][0].update(database_create=True),'POWER'),
])
def test_prepared_comparison_refusals(mutation,code):
    e,r,b,a,m,s=fixture();mutation(a,m,s)
    with pytest.raises(p.l.Refused,match=code):p.compare_prepared(e,r,b,a,m,s)


def test_collection_admin_is_target_bound_readonly_and_stdin_only(monkeypatch):
    e=fixed();r=record();b=evidence(e,r)
    calls=[]
    monkeypatch.setattr(p.l,'checked_record',lambda confirm:r)
    def admin(record,sql):calls.append(sql);return json.dumps(b['observation'])
    monkeypatch.setattr(p,'admin_psql',admin)
    actual=p.collect_admin(r,e)
    assert actual==b
    assert len(calls)==1 and calls[0].startswith('BEGIN TRANSACTION READ ONLY')
    assert calls[0].rstrip().endswith('ROLLBACK;') and 'SET ROLE' not in calls[0]
    assert 'pg_db_role_setting' not in calls[0]  # No inference of another session's value.
    assert all('CREATE' not in sql and 'GRANT' not in sql for sql in calls)


def setup_execution(tmp_path,monkeypatch):
    e,r,b,a,m,s=fixture();tmp_path.chmod(0o700)
    path=tmp_path/'intent.json';path.write_bytes(p.canonical(e))
    monkeypatch.setattr(p.l,'state_dir',lambda:tmp_path)
    monkeypatch.setattr(p.l,'checked_record',lambda confirm:r)
    admin=Mock(side_effect=[b,a]);monkeypatch.setattr(p,'collect_admin',admin)
    apply=Mock();monkeypatch.setattr(p,'apply_preparation',apply)
    commands=[]
    def command(argv,**kw):
        commands.append(argv)
        if 'pg_controldata' in argv:return 'Database system identifier: 7705421224394444834\n'
        if 'stop' in argv:return ''
        raise AssertionError('Unexpected command')
    monkeypatch.setattr(p.l,'command',command)
    inspections=[dict(Config=dict(Labels={'com.docker.compose.project':p.l.PROJECT}),State=dict(Running=True)),dict(State=dict(Running=False))]
    monkeypatch.setattr(p.l,'docker_json',lambda *args:[inspections.pop(0)])
    monkeypatch.setattr(p.l,'password',lambda path:'SYNTHETIC-NOT-AN-OPERATIONAL-CREDENTIAL')
    monkeypatch.setattr(p,'probe_meta',lambda conn:m)
    conn=Connection();conn.identity.update(database=p.l.DATABASE,system_identifier=r['system_identifier'],current_user=p.l.PROBE,session_user=p.l.PROBE,address=r['address'],backend_start=m['backend_start'])
    # Match the real query shapes too; comparison fixture keeps only properties
    # relevant to its predicates, so complete the other fixed fields here.
    for name in p.CaptureConnection.selected:
        if name=='identity':continue
        conn.data[name]=[]
        for value in s[name][0]:
            row={key:False if name=='privileges' else None for key in p.trial.QUERIES[name].fields};row.update(value)
            conn.data[name].append(row)
    engine=SimpleNamespace(connect=lambda:conn,dispose=Mock())
    monkeypatch.setattr(sqlalchemy,'create_engine',lambda *args,**kw:engine)
    return path,admin,apply,commands,engine


def test_complete_orchestration_is_offline_and_preserves_prior_reports(tmp_path,monkeypatch):
    path,admin,apply,commands,engine=setup_execution(tmp_path,monkeypatch)
    old=tmp_path/'trial-report-03.json';old.write_text('preserved')
    result=p.execute(path,'7705421224394444834','04')
    assert result.get('status')!='REFUSED',result
    assert result['container_stopped'] is True and result['comparison']['session_preload_libraries_probe']=='UNOBSERVED'
    assert admin.call_count==2 and apply.call_count==1 and engine.dispose.call_count==1
    assert old.read_text()=='preserved'
    assert (tmp_path/'prepared-04-admin-before.json').stat().st_mode&0o777==0o600
    report=json.loads((tmp_path/'prepared-04-report.json').read_bytes())
    assert 'observation' not in report and 'owners' not in report
    assert any('stop' in argv for argv in commands)


def test_divergence_stops_without_sql_or_repair(tmp_path,monkeypatch):
    path,admin,apply,commands,engine=setup_execution(tmp_path,monkeypatch)
    admin.side_effect=p.l.Refused('ADMIN_SETTINGS_MISMATCH')
    result=p.execute(path,'7705421224394444834','04')
    assert result['status']=='REFUSED' and result['diagnostic']['phase']=='admin_before'
    assert result['diagnostic']['code']=='ADMIN_SETTINGS_MISMATCH'
    assert result['container_stopped'] is True and apply.call_count==0
    assert any('stop' in argv for argv in commands)


def test_validate_only_no_resources_and_no_output_values(tmp_path,monkeypatch,capsys):
    e=fixed();path=tmp_path/'intent.json';path.write_bytes(p.canonical(e))
    assert p.main(['--expectations',str(path),'--confirm-system-identifier','7705421224394444834','--trial-id','04','--validate-only'])==0
    output=capsys.readouterr().out
    assert 'STRUCTURALLY_VALIDATED' in output and 'shared_preload' not in output


def test_sql_failure_stops_and_never_retries_or_inspects(tmp_path,monkeypatch):
    path,admin,apply,commands,engine=setup_execution(tmp_path,monkeypatch)
    apply.side_effect=p.l.Refused('COMMAND_FAILED')
    result=p.execute(path,'7705421224394444834','04')
    assert result['status']=='REFUSED' and result['diagnostic']['phase']=='apply_proposed_sql'
    assert result['container_stopped'] is True
    assert apply.call_count==1 and admin.call_count==1 and engine.dispose.call_count==0
    assert not (tmp_path/'prepared-04-probe.json').exists()


def test_private_probe_evidence_never_fills_admin_values(tmp_path,monkeypatch):
    path,admin,apply,commands,engine=setup_execution(tmp_path,monkeypatch)
    result=p.execute(path,'7705421224394444834','04')
    assert result.get('status')!='REFUSED'
    evidence=json.loads((tmp_path/'prepared-04-probe.json').read_bytes())
    assert evidence['scope']=='LOCAL_PROBE_TRIAL_OBSERVATION' and evidence['operational_authority'] is False
    values={r['name']:r['setting'] for r in evidence['observations']['settings'][0]}
    assert values['shared_preload_libraries'] is None and values['session_preload_libraries'] is None
    assert 'observation' not in result  # No private data in stdout result.
