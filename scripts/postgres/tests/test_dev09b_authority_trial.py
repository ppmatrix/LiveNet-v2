"""Authority trial preparation only. No Docker, SQL, network, secrets or services."""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from scripts.postgres import dev09b_authority_trial as t
from scripts.dedicated.dev09b import postgres_authority as a
from scripts.postgres.tests.test_dev09b_admission import rig  # modeled SQL transactions ONLY


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    import socket,subprocess
    denied=Mock(side_effect=AssertionError('No external operation in offline test'))
    for owner,name in ((socket,'socket'),(socket,'create_connection'),(subprocess,'run'),(subprocess,'Popen')):
        monkeypatch.setattr(owner,name,denied)
    monkeypatch.setattr(t,'create_engine',denied)


def test_static_pins_and_isolation():
    cfg=t.validate();db=cfg['services']['db']
    assert cfg['name']!=t.q.PROJECT and db['environment']['POSTGRES_DB']!=t.q.DATABASE
    assert cfg['volumes']['authoritytrial_data']['name']!=t.q.VOLUME
    assert db['pull_policy']=='never' and 'ports' not in db and set(db['networks'])=={'backend'}
    assert cfg['networks']['backend']['internal'] is True
    assert t.main(['validate-only'])==0


def test_no_validator_or_admission_bypass():
    source=Path(t.__file__).read_text()
    assert 'monkeypatch' not in source.replace('No monkeypatch','')
    assert 'ApplicationTransport' not in source.replace('or ApplicationTransport','')
    assert 'validate_layers =' not in source and '._approval =' not in source
    assert not hasattr(t,'AdmissionController')
    assert json.loads(t.MARKER)['not_an_approval'] is True


def test_schema_and_admin_acl_are_separate():
    sql=t.ADMIN_SQL.read_text()
    assert '__AUTHORITY_SCHEMA__' in sql and 'SECURITY DEFINER' not in sql
    assert 'GRANT UPDATE(state,session_json)' in sql and 'GRANT UPDATE(state,revoked)' in sql
    assert 'CREATE ROLE dev09b_authority_trial_owner NOLOGIN' in sql
    assert 'REVOKE ALL ON DATABASE dev09b_authority_trial FROM PUBLIC' in sql
    assert 'GRANT CONNECT ON DATABASE' in sql and 'GRANT CREATE' not in sql
    assert 'CREATE EXTENSION' not in sql and 'CREATE DATABASE' not in sql
    assert t.HBA.read_text().endswith('host all all ::/0 reject\n')
    assert not any('migrator' in x for x in t.HBA.read_text().splitlines() if not x.startswith('#'))


def test_admin_requires_same_sid_and_stdin_only(monkeypatch):
    call=Mock(return_value='');monkeypatch.setattr(t,'run_admin_command',call)
    t.admin(dict(container_id='trial-id',system_identifier='999'),'BEGIN;\nSELECT 1;\nCOMMIT;')
    args,stdin,phase,identifiers=call.call_args.args
    assert 'ADMIN_IDENTITY_REFUSED' in stdin and '999' in stdin
    assert 'PGPASSWORD' not in ' '.join(args[:-1])
    assert 'cat /run/secrets/authoritytrial_admin_password' in args[-1]
    assert '999' not in ' '.join(args)
    assert args[args.index('--user')+1]=='root'
    assert ' -w ' in args[-1] and '-h /var/run/postgresql' in args[-1]
    assert identifiers[0]=='S001_BEGIN' and identifiers[-1].endswith('_COMMIT')
    assert '\\echo DEV09B_STATEMENT:S001_BEGIN\n' in stdin


def test_synthetic_seed_has_no_usable_envelope():
    sql=t.seed_sql()
    assert sql.startswith('BEGIN;') and sql.endswith('COMMIT;')
    assert t.MARKER.hex() in sql and "decode('7b7d','hex')" in sql
    assert 'signature_hex' not in sql and 'LiveNet' not in sql
    assert len({t.approval_id(i) for i in range(1,6)})==5


def test_real_storage_sql_uses_original_boundary(rig):
    rig.db.row['envelope']=t.MARKER
    assert t.storage_consume(rig.service,rig.p['approval_id'],t.approval_id(50))=='SYNTHETIC_STORAGE_COMMIT_CONFIRMED'
    assert rig.db.row['state']=='CONSUMED' and a.CONTROL in rig.db.calls and a.CONSUME in rig.db.calls
    assert not rig.sealed  # never an authenticated operational receipt
    with pytest.raises(a.AuthorityRefused):t.storage_consume(rig.service,rig.p['approval_id'],t.approval_id(51))


def test_operational_document_refused_in_storage_trial(rig):
    with pytest.raises(a.AuthorityRefused):t.storage_consume(rig.service,rig.p['approval_id'],t.approval_id(50))
    assert rig.db.row['state']=='AVAILABLE'


def test_failure_disposes_engines_and_preserves_safe_report(monkeypatch):
    record={'system_identifier':'999'};engines={role:SimpleNamespace(dispose=Mock()) for role in t.ROLES}
    writes=[]
    monkeypatch.setattr(t,'checked',lambda confirm:record)
    monkeypatch.setattr(t,'state',lambda:Path('/private-trial-placeholder'))
    monkeypatch.setattr(t.q,'write_new',lambda path,data:writes.append((path.name,data)))
    monkeypatch.setattr(t,'admin',Mock())
    monkeypatch.setattr(t,'engine',lambda record,role:engines[role])
    monkeypatch.setattr(t,'service',lambda *args:None)
    monkeypatch.setattr(t,'scenarios',Mock(side_effect=ValueError('sensitive driver message must not appear')))
    with pytest.raises(ValueError):t.run('999')
    report=json.loads(writes[-1][1])
    assert writes[0][0]=='run-started' and writes[-1][0]=='authority-trial-report-01.json'
    assert report['status']=='REFUSED' and report['exception_class']=='ValueError'
    assert b'sensitive' not in writes[-1][1] and all(e.dispose.called for e in engines.values())


def test_missing_confirmation_cannot_start_admin(monkeypatch):
    monkeypatch.setattr(t,'checked',Mock(side_effect=t.q.Refused('INDEPENDENT_AUTHORITY_SID_REQUIRED')))
    admin=Mock();monkeypatch.setattr(t,'admin',admin)
    with pytest.raises(t.q.Refused):t.prepare(None)
    assert not admin.called


def test_race_waits_for_distinct_active_transactions_and_restores_factory(monkeypatch):
    from threading import Lock
    callbacks={};counter=[0];lock=Lock();arrived=[]
    def factory():
        with lock:counter[0]+=1;pid=counter[0]
        return SimpleNamespace(connection=SimpleNamespace(driver_connection=SimpleNamespace(info=SimpleNamespace(backend_pid=pid))),
                               in_transaction=lambda:True)
    actor=SimpleNamespace(connections=factory)
    monkeypatch.setattr(t.event,'listen',lambda conn,name,fn:callbacks.__setitem__(id(conn),fn))
    def work():
        conn=actor.connections()
        callbacks[id(conn)](conn,None,a.CONTROL,{},None,False)
        arrived.append(conn.connection.driver_connection.info.backend_pid)
    assert t.race([work,work],[actor])==['RETURNED','RETURNED']
    assert sorted(arrived)==[1,2] and actor.connections is factory


def test_race_refuses_reused_backend(monkeypatch):
    callbacks={}
    def factory():
        return SimpleNamespace(connection=SimpleNamespace(driver_connection=SimpleNamespace(info=SimpleNamespace(backend_pid=1))),
                               in_transaction=lambda:True)
    actor=SimpleNamespace(connections=factory)
    monkeypatch.setattr(t.event,'listen',lambda conn,name,fn:callbacks.__setitem__(id(conn),fn))
    def work():
        conn=actor.connections();callbacks[id(conn)](conn,None,a.CONTROL,{},None,False)
    with pytest.raises(t.q.Refused,match='DISTINCT_CONCURRENT_BACKENDS_REQUIRED'):t.race([work,work],[actor])
    assert actor.connections is factory


@pytest.mark.parametrize('stderr',[
    'ERROR: 42601\n',
    'psql:<stdin>:19: ERROR: 42501\n',
    'psql:<stdin>:19: ERROR: 28P01\n'])
def test_safe_sqlstate_and_statement_only(stderr):
    ids=['S001_BEGIN','S002_CREATE_ROLE','S003_COMMIT']
    d=t.admin_diagnostic('administrative_preparation',3,
        'DEV09B_STATEMENT:S002_CREATE_ROLE\nsensitive stdout data\n',
        stderr+'CREATE ROLE secret PASSWORD sensitive_verifier;\n',ids)
    assert d['statement_id']=='S002_CREATE_ROLE' and d['sqlstate']==stderr.strip().split()[-1]
    assert d['phase']=='administrative_preparation' and d['code']=='ADMIN_STATEMENT_FAILED'
    assert 'sensitive' not in json.dumps(d) and 'PASSWORD' not in json.dumps(d)


def test_preconnection_read_failure_never_invents_sqlstate():
    d=t.admin_diagnostic('administrative_preparation',78,'',
        'DEV09B_PRECONNECT:SECRET_UNREADABLE\nprivate message\n',[])
    assert d==dict(phase='administrative_connect',sqlstate=None,statement_id=None,
                   code='ADMIN_SECRET_UNREADABLE',exit_code=78)


def test_non_sqlstate_and_unknown_markers_are_not_promoted():
    d=t.admin_diagnostic('seed',1,'DEV09B_STATEMENT:S999_PASSWORD\n',
        'ERROR: a sensitive message 42601\n', ['S001_BEGIN'])
    assert d['sqlstate'] is None and d['statement_id'] is None


def test_root_channel_separate_password_assignment_and_noninteractive_client(monkeypatch):
    call=Mock();monkeypatch.setattr(t,'run_admin_command',call)
    t.admin(dict(container_id='trial-id',system_identifier='999'),'BEGIN;\nCOMMIT;')
    args,sql,phase,ids=call.call_args.args
    shell=args[-1]
    assert args[args.index('--user')+1]=='root'
    assert 'export PGPASSWORD="$(' not in shell
    assert 'PGPASSWORD="$(cat ' in shell and ' || ' in shell
    assert 'test -r ' in shell and ' -w ' in shell and 'VERBOSITY=sqlstate' in shell
    assert 'PGOPTIONS="-c statement_timeout=5000 -c lock_timeout=2000"' in shell
    assert 'PRIVATE' not in ' '.join(args)
    assert '\\echo DEV09B_STATEMENT:S001_BEGIN\nBEGIN;\n' in sql
    assert 'DO $$ BEGIN IF current_database()' in sql


def test_instrumentation_preserves_do_block_and_password_literal():
    body="DO $$ BEGIN\n IF true THEN RAISE EXCEPTION 'private; data'; END IF;\nEND $$;"
    role="CREATE ROLE test PASSWORD 'SYNTHETIC;TEST';"
    source='BEGIN;\n'+body+'\n'+role+'\nCOMMIT;'
    marked,ids=t.instrument_admin_sql(source)
    recovered='\n'.join(x for x in marked.splitlines() if not x.startswith('\\echo '))+'\n'
    assert recovered==source+'\n' and len(ids)==4
    assert 'SYNTHETIC' not in ''.join(ids) and 'private' not in ''.join(ids)
    assert ids==['S001_BEGIN','S002_DO','S003_CREATE_ROLE','S004_COMMIT']
    seed,ids=t.instrument_admin_sql(t.seed_sql())
    assert [i.split('_',1)[1] for i in ids]==['BEGIN','SET_LOCAL','INSERT_INTO','COMMIT']


def test_subprocess_diagnostic_discards_sensitive_buffers(monkeypatch):
    def failed(*args,**kwargs):
        assert args[0][:3]==['docker','--context','default']
        return SimpleNamespace(returncode=3,stdout='DEV09B_STATEMENT:S002_CREATE_ROLE\n',
            stderr='psql:<stdin>:4: ERROR: 42601\nCREATE ROLE x PASSWORD leaked_verifier;')
    monkeypatch.setattr(t.subprocess,'run',failed)
    with pytest.raises(t.AdminFailure) as error:
        t.run_admin_command(['docker','exec','trial'],'sensitive SQL','seed',['S001_BEGIN','S002_CREATE_ROLE','S003_COMMIT'])
    assert error.value.diagnostic['sqlstate']=='42601'
    assert 'leaked' not in repr(error.value.__dict__) and 'sensitive' not in str(error.value)


def test_timeout_preserves_safe_last_statement_not_raw_output(monkeypatch):
    def timeout(*args,**kwargs):
        raise t.subprocess.TimeoutExpired('private argv',30,
            output=b'DEV09B_STATEMENT:S002_CREATE_ROLE\nprivate output',stderr=b'private stderr')
    monkeypatch.setattr(t.subprocess,'run',timeout)
    with pytest.raises(t.AdminFailure) as error:
        t.run_admin_command(['docker','exec','trial'],'private SQL','seed',['S001_BEGIN','S002_CREATE_ROLE','S003_COMMIT'])
    assert error.value.diagnostic['code']=='ADMIN_TIMEOUT_RESULT_UNCERTAIN'
    assert error.value.diagnostic['statement_id']=='S002_CREATE_ROLE'
    assert error.value.diagnostic['sqlstate'] is None and 'private' not in repr(error.value.__dict__)


def resume_fixture(tmp_path,monkeypatch):
    tmp_path.chmod(0o700)
    monkeypatch.setattr(t,'state',lambda:tmp_path)
    proof=dict(status='READ_ONLY_INSPECTION_RETURNED',container_final='exited',system_identifier='999',observation=dict(
        system_identifier='999',database=t.DATABASE,current_user=t.ADMIN,session_user=t.ADMIN,transaction_read_only='on',
        authority_schema_count=0,authority_relations=[],target_memberships=0,roles=[dict(name=t.ADMIN,login=True,superuser=True)],
        database_owner=t.ADMIN,database_public_privileges=['CONNECT','TEMPORARY'],
        public_schema=dict(owner='pg_database_owner',acl='{pg_database_owner=UC/pg_database_owner,=U/pg_database_owner}')))
    t.q.write_new(tmp_path/'admin-started',b'original marker preserved')
    return proof


def test_explicit_resume_retains_original_marker_and_is_single_use(tmp_path,monkeypatch):
    proof=resume_fixture(tmp_path,monkeypatch)
    t.q.write_new(tmp_path/'diagnostic-inspection-01.json',json.dumps(proof).encode())
    monkeypatch.setattr(t,'checked',lambda sid:dict(system_identifier='999',container_id='trial-id'))
    monkeypatch.setattr(t.q,'password',lambda path:'TEST_ONLY_PASSWORD')
    monkeypatch.setattr(t.q,'scram_verifier',lambda secret:'TEST_ONLY_SCRAM')
    calls=Mock();monkeypatch.setattr(t,'admin',calls)
    # No implicit retry or marker deletion.
    with pytest.raises(FileExistsError):t.prepare('999')
    assert not calls.called
    t.prepare('999',resume_inspection='diagnostic-inspection-01.json')
    assert (tmp_path/'admin-started').read_bytes()==b'original marker preserved'
    assert (tmp_path/'admin-resume-started-diagnostic-inspection-01').is_file()
    sql=calls.call_args.args[1]
    assert sql.index('ADMIN_PRISTINE_REQUIRED')<sql.index('REVOKE ALL ON DATABASE')
    with pytest.raises(FileExistsError):t.prepare('999',resume_inspection='diagnostic-inspection-01.json')
    assert calls.call_count==1


@pytest.mark.parametrize('fault',['sid','partial_schema','roles','grants','read_write','already_run'])
def test_resume_refuses_incomplete_or_divergent_inspection(tmp_path,monkeypatch,fault):
    proof=resume_fixture(tmp_path,monkeypatch)
    if fault=='sid':proof['system_identifier']='888'
    if fault=='partial_schema':proof['observation']['authority_schema_count']=1
    if fault=='roles':proof['observation']['roles'].append(dict(name='unexpected'))
    if fault=='grants':proof['observation']['database_public_privileges']=[]
    if fault=='read_write':proof['observation']['transaction_read_only']='off'
    if fault=='already_run':t.q.write_new(tmp_path/'run-started',b'original')
    t.q.write_new(tmp_path/'diagnostic-inspection-01.json',json.dumps(proof).encode())
    with pytest.raises(t.q.Refused):t.validate_resume_inspection('diagnostic-inspection-01.json',dict(system_identifier='999'))


def test_full_preparation_compiles_fixed_statement_markers_offline(tmp_path,monkeypatch):
    tmp_path.chmod(0o700);monkeypatch.setattr(t,'state',lambda:tmp_path)
    monkeypatch.setattr(t,'checked',lambda sid:dict(system_identifier='999',container_id='trial-id'))
    monkeypatch.setattr(t.q,'password',lambda path:'TEST_PASSWORD')
    monkeypatch.setattr(t.q,'scram_verifier',lambda value:'TEST_VERIFIER')
    calls=Mock();monkeypatch.setattr(t,'run_admin_command',calls)
    t.prepare('999')
    args,sql,phase,ids=calls.call_args.args
    assert len(ids)>30 and len(set(ids))==len(ids)
    assert ids[0]=='S001_BEGIN' and ids[-1].endswith('_COMMIT')
    assert len([i for i in ids if i.endswith('_CREATE_TABLE')])==4
    assert sql.index('ADMIN_IDENTITY_REFUSED')<sql.index('ADMIN_PRISTINE_REQUIRED')<sql.index('REVOKE ALL ON DATABASE')
    assert '__SERVICE_SCRAM__' not in sql and 'TEST_VERIFIER' not in ''.join(ids)
    assert sql.count('\\echo DEV09B_STATEMENT:')==len(ids)


def test_failure_artifact_contains_only_safe_diagnostic(tmp_path,monkeypatch):
    tmp_path.chmod(0o700);monkeypatch.setattr(t,'state',lambda:tmp_path)
    diagnostic=dict(phase='administrative_preparation',sqlstate='42501',statement_id='S002_DO',code='ADMIN_STATEMENT_FAILED',exit_code=3)
    monkeypatch.setattr(t,'run_admin_command',Mock(side_effect=t.AdminFailure(diagnostic)))
    with pytest.raises(t.AdminFailure):t.admin(dict(container_id='trial-id',system_identifier='999'),'BEGIN;\nCOMMIT;')
    files=list(tmp_path.glob('admin-diagnostic-*.json'))
    assert len(files)==1 and files[0].stat().st_mode&0o777==0o600
    assert json.loads(files[0].read_bytes())==diagnostic


def test_success_without_commit_marker_is_uncertain(monkeypatch):
    monkeypatch.setattr(t.subprocess,'run',lambda *a,**k:SimpleNamespace(returncode=0,stdout='DEV09B_STATEMENT:S001_BEGIN\n',stderr=''))
    with pytest.raises(t.AdminFailure) as error:
        t.run_admin_command(['docker','exec','trial'],'SQL','seed',['S001_BEGIN','S002_COMMIT'])
    assert error.value.diagnostic['code']=='ADMIN_COMMIT_CONFIRMATION_MISSING'
    assert error.value.diagnostic['sqlstate'] is None
