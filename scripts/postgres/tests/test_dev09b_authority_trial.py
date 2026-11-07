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
    call=Mock(return_value='');monkeypatch.setattr(t.q,'command',call)
    t.admin(dict(container_id='trial-id',system_identifier='999'),'BEGIN; SELECT 1; COMMIT;')
    args=call.call_args.args[0];stdin=call.call_args.kwargs['input']
    assert 'ADMIN_IDENTITY_REFUSED' in stdin and '999' in stdin
    assert 'PGPASSWORD' not in ' '.join(args[:-1])
    assert 'cat /run/secrets/authoritytrial_admin_password' in args[-1]
    assert '999' not in ' '.join(args)


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
