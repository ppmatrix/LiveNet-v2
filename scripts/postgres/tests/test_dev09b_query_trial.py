"""Runner acceptance with synthetic connections only; never execute PostgreSQL."""
from dataclasses import replace
from types import SimpleNamespace
import socket
import subprocess

import pytest
import sqlalchemy
import logging

# Capture before the no-network fixture forbids new application engines.
# This factory is used solely for SQLite in-memory API regression tests.
_SQLITE_ENGINE = sqlalchemy.create_engine

from scripts.postgres import dev09b_query_trial as trial


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def denied(*a,**kw):raise AssertionError('No connections/processes/network in runner tests')
    monkeypatch.setattr(socket,'socket',denied)
    monkeypatch.setattr(socket,'create_connection',denied)
    monkeypatch.setattr(subprocess,'Popen',denied)
    monkeypatch.setattr(subprocess,'run',denied)
    monkeypatch.setattr(sqlalchemy,'create_engine',denied)


def target():return trial.TrialTarget('livenet_v2_dev','123','fixture_probe','192.0.2.4')


class Result:
    def __init__(self,rows):self.rows=rows;self.closed=False
    def mappings(self):return iter(self.rows)
    def close(self):self.closed=True


class Connection:
    def __init__(self):
        self.closed=False;self._echo=False;self.dialect=SimpleNamespace(name='postgresql')
        self.engine=SimpleNamespace(echo=False,hide_parameters=True,logger=SimpleNamespace(isEnabledFor=lambda level:False))
        self.tx=None;self.calls=[];self.results=[];self.callback=None
        self.rollback_error=self.close_error=False
        self.setting=dict(read_only='off',isolation='read committed',statement_ms=0,lock_ms=0,idle_ms=0,search_path='')
        self.data={k:[] for k in trial.QUERIES}
        self.identity=dict(database='livenet_v2_dev',system_identifier='123',current_user='fixture_probe',session_user='fixture_probe',
            pid=123,backend_start='fixture-backend',xact_start='fixture-xact',virtualxid='4/2',address='192.0.2.4',port=5432,server_version_num=160010)
        self.data['identity']=[self.identity]
    def in_transaction(self):return self.tx is not None
    def get_transaction(self):return self.tx
    def begin(self):
        self.calls.append(('begin',None));self.tx=SimpleNamespace(is_active=True);return self.tx
    def execute(self,statement,**options):
        sql=str(statement);self.calls.append(('sql',sql))
        if self.callback:self.callback(self,sql)
        if sql=='SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY':
            self.setting.update(read_only='on',isolation='repeatable read');rows=[]
        elif sql.startswith('SET LOCAL '):
            name,value=sql.removeprefix('SET LOCAL ').split(' = ')
            key={'statement_timeout':'statement_ms','lock_timeout':'lock_ms','idle_in_transaction_session_timeout':'idle_ms','search_path':'search_path'}[name]
            self.setting[key]=value if key=='search_path' else int(value);rows=[]
        else:
            assert options=={'execution_options':{'stream_results':True,'max_row_buffer':128}}
            if sql==trial.CONTROL_SQL:rows=[dict(self.setting)]
            else:rows=self.data[next(k for k,q in trial.QUERIES.items() if q.sql==sql)]
        result=Result(rows);self.results.append(result);return result
    def rollback(self):
        self.calls.append(('rollback',None))
        if self.rollback_error:raise RuntimeError('password=DO_NOT_LOG')
        if self.tx:self.tx.is_active=False
        self.tx=None
    def close(self):
        self.calls.append(('close',None));self.closed=True
        if self.close_error:raise RuntimeError('password=DO_NOT_LOG')


def test_construction_is_inert_and_report_counts_no_data():
    conn=Connection();assert not conn.calls
    q=trial.QUERIES['relations']
    conn.data['relations']=[dict.fromkeys(q.fields,'DO_NOT_LOG')]
    report=trial.run_trial(conn,target())
    assert report.status=='COMPLETED' and report.scope=='QUERY_TRIAL_ONLY'
    assert len(report.queries)==33 and {q.status for q in report.queries}=={'SUCCESS'}
    assert next(q for q in report.queries if q.name=='relations').rows==1
    assert report.identity_after.status=='SUCCESS'
    assert report.rollback==report.close=='RETURNED'
    assert conn.calls[-2:]==[('rollback',None),('close',None)]
    assert all(r.closed for r in conn.results)
    select_sql=[sql for kind,sql in conn.calls if kind=='sql' and sql.startswith('SELECT')]
    assert len(select_sql)==35  # 33 distinct + final identity + settings check
    assert select_sql[1]==trial.QUERIES['identity'].sql
    assert select_sql[-1]==trial.QUERIES['identity'].sql
    assert 'DO_NOT_LOG' not in report.to_json() and '192.0.2.4' not in report.to_json()
    assert 'fixture_probe' not in report.to_json() and 'fixture-backend' not in report.to_json()
    assert not any('COMMIT' in sql or 'alembic_version' in sql for kind,sql in conn.calls if kind=='sql')


@pytest.mark.parametrize('field,value',[('database','other'),('system_identifier','bad'),('user','password=DO_NOT_LOG'),('address','db'),('port',True)])
def test_invalid_config_still_cleans_up_without_sql(field,value):
    conn=Connection()
    report=trial.run_trial(conn,replace(target(),**{field:value}))
    assert report.status=='REFUSED' and all(q.status=='NOT_RUN' for q in report.queries)
    assert not any(k=='sql' for k,_ in conn.calls)
    assert conn.calls[-2:]==[('rollback',None),('close',None)]
    assert 'DO_NOT_LOG' not in report.to_json()


@pytest.mark.parametrize('field,value',[('statement_ms',True),('lock_ms',0),('idle_ms',100),('deadline_ms',130000),('max_total_bytes',2**40)])
def test_invalid_limits_refused(field,value):
    conn=Connection();report=trial.run_trial(conn,target(),replace(trial.TrialLimits(),**{field:value}))
    assert report.reason=='INVALID_LIMITS' and conn.closed
    assert not any(k=='sql' for k,_ in conn.calls)


@pytest.mark.parametrize('key',['read_only','isolation','statement_ms','lock_ms','idle_ms','search_path'])
def test_server_must_confirm_controls(key):
    conn=Connection()
    def mutate(connection,sql):
        if sql==trial.CONTROL_SQL:connection.setting[key]='unsafe'
    conn.callback=mutate
    report=trial.run_trial(conn,target())
    assert report.reason=='READ_ONLY_OR_TIMEOUT_REFUSED'
    assert all(q.status=='NOT_RUN' for q in report.queries)
    assert conn.closed


@pytest.mark.parametrize('key',['database','system_identifier','current_user','session_user','pid','backend_start','xact_start','virtualxid','address','port','server_version_num'])
def test_initial_identity_refusal(key):
    conn=Connection();conn.identity[key]=0 if type(conn.identity[key]) is int else ''
    report=trial.run_trial(conn,target())
    assert report.status=='REFUSED'
    assert report.queries[0].status=='REFUSED'
    assert all(q.status=='NOT_RUN' for q in report.queries[1:])
    assert conn.closed


def test_final_identity_change_refused():
    conn=Connection();calls=0
    def mutate(connection,sql):
        nonlocal calls
        if sql==trial.QUERIES['identity'].sql:
            calls+=1
            if calls==2:connection.identity['virtualxid']='4/3'
    conn.callback=mutate
    report=trial.run_trial(conn,target())
    assert report.status=='REFUSED' and report.identity_after.reason=='IDENTITY_CHANGED'
    assert all(q.status=='SUCCESS' for q in report.queries)
    assert conn.closed


def test_mid_query_failure_redaction_and_no_retry():
    conn=Connection()
    def fail(connection,sql):
        if sql==trial.QUERIES['schemas'].sql:raise RuntimeError('postgresql://secret:DO_NOT_LOG@private')
    conn.callback=fail
    report=trial.run_trial(conn,target())
    assert report.status=='REFUSED'
    assert next(q for q in report.queries if q.name=='schemas').reason=='QUERY_OR_SETUP_ERROR'
    assert sum(sql==trial.QUERIES['schemas'].sql for kind,sql in conn.calls if kind=='sql')==1
    assert any(q.status=='NOT_RUN' for q in report.queries)
    assert 'DO_NOT_LOG' not in report.to_json() and 'private' not in report.to_json()
    assert all(r.closed for r in conn.results)


@pytest.mark.parametrize('which',['rollback','close','both'])
def test_cleanup_failures_still_close_and_refuse(which):
    conn=Connection();conn.rollback_error=which in {'rollback','both'};conn.close_error=which in {'close','both'}
    report=trial.run_trial(conn,target())
    assert report.status=='REFUSED' and report.reason=='CLEANUP_FAILED'
    assert conn.calls[-1]==('close',None) and conn.closed
    assert 'DO_NOT_LOG' not in report.to_json()


def test_rollback_close_after_stream_failure():
    conn=Connection();original=conn.execute
    def execute(statement,**kw):
        result=original(statement,**kw)
        if str(statement)==trial.QUERIES['relations'].sql:
            def interrupted():
                yield dict.fromkeys(trial.QUERIES['relations'].fields,None)
                raise RuntimeError('DO_NOT_LOG')
            result.mappings=interrupted
        return result
    conn.execute=execute
    report=trial.run_trial(conn,target())
    assert report.status=='REFUSED' and all(r.closed for r in conn.results)
    assert report.rollback==report.close=='RETURNED'


def test_row_byte_and_total_limits():
    conn=Connection();q=trial.QUERIES['privileges'];conn.data['privileges']=[dict.fromkeys(q.fields,False)]*2
    report=trial.run_trial(conn,target());assert report.reason=='ROW_LIMIT'
    conn=Connection();conn.data['relations']=[dict.fromkeys(trial.QUERIES['relations'].fields,'x'*100)]
    report=trial.run_trial(conn,target(),replace(trial.TrialLimits(),max_row_bytes=1024));assert report.reason=='BYTE_LIMIT'
    conn=Connection()
    report=trial.run_trial(conn,target(),replace(trial.TrialLimits(),max_total_rows=1));assert report.reason=='ROW_LIMIT'
    conn=Connection()
    report=trial.run_trial(conn,target(),replace(trial.TrialLimits(),max_total_bytes=100));assert report.reason=='BYTE_LIMIT'


def test_deadline_and_transaction_loss():
    conn=Connection();now=[0.0]
    def mutate(connection,sql):
        if sql==trial.QUERIES['relations'].sql:now[0]=61.0
    conn.callback=mutate
    report=trial.run_trial(conn,target(),clock=lambda:now[0]);assert report.reason=='DEADLINE'
    conn=Connection()
    def swap(connection,sql):
        if sql==trial.QUERIES['privileges'].sql:connection.tx=SimpleNamespace(is_active=True)
    conn.callback=swap
    report=trial.run_trial(conn,target());assert report.reason=='TRANSACTION_CHANGED'
    assert report.rollback==report.close=='RETURNED'


def test_existing_transaction_logging_and_catalog_changes_refused(monkeypatch):
    conn=Connection();conn.tx=SimpleNamespace(is_active=True)
    report=trial.run_trial(conn,target());assert report.reason=='TRANSACTION_ALREADY_ACTIVE'
    conn=Connection();conn.engine.echo='debug'
    report=trial.run_trial(conn,target());assert report.reason=='CLIENT_LOGGING_REFUSED'
    altered=dict(trial.QUERIES);q=altered['relations'];altered['relations']=replace(q,sql='DROP TABLE forbidden')
    monkeypatch.setattr(trial,'QUERIES',altered)
    conn=Connection();report=trial.run_trial(conn,target());assert report.reason=='CATALOG_CHANGED'
    assert not any(k=='sql' for k,_ in conn.calls)


def test_partial_count_logger_and_untrusted_exception_text():
    conn=Connection();q=trial.QUERIES['privileges'];conn.data['privileges']=[dict.fromkeys(q.fields,False)]*2
    report=trial.run_trial(conn,target())
    refused=next(q for q in report.queries if q.name=='privileges')
    assert refused.status=='REFUSED' and refused.rows==2 and refused.reason=='ROW_LIMIT'
    conn=Connection();conn.engine.logger.isEnabledFor=lambda level:True
    report=trial.run_trial(conn,target())
    assert report.reason=='CLIENT_LOGGING_REFUSED' and not any(k=='sql' for k,_ in conn.calls)
    conn=Connection()
    def fail(connection,sql):raise trial._Refused('DO_NOT_LOG')
    conn.callback=fail
    report=trial.run_trial(conn,target())
    assert report.reason=='QUERY_OR_SETUP_ERROR' and 'DO_NOT_LOG' not in report.to_json()


def test_interrupt_still_attempts_rollback_and_close():
    conn=Connection()
    def interrupt(connection,sql):raise KeyboardInterrupt()
    conn.callback=interrupt
    with pytest.raises(KeyboardInterrupt):trial.run_trial(conn,target())
    assert conn.calls[-2:]==[('rollback',None),('close',None)]


def test_real_sqlalchemy_connection_logging_api_no_postgres_or_network():
    engine=_SQLITE_ENGINE('sqlite://',echo=False,hide_parameters=True,
                          logging_name='dev09b_querytrial_api_regression')
    try:
        with engine.connect() as connection:
            assert isinstance(connection,sqlalchemy.engine.Connection)
            assert not hasattr(connection,'echo')
            assert connection._echo is False
            trial._check_client_logging(connection)
            engine.hide_parameters=False
            with pytest.raises(trial._Refused,match='CLIENT_LOGGING_REFUSED'):
                trial._check_client_logging(connection)
            engine.hide_parameters=True
            del connection._echo
            try:
                with pytest.raises(trial._Refused,match='CLIENT_LOGGING_REFUSED'):
                    trial._check_client_logging(connection)
            finally:connection._echo=False
    finally:engine.dispose()


@pytest.mark.parametrize('level',[logging.INFO,logging.DEBUG])
def test_real_engine_effective_logging_change_refused(level):
    engine=_SQLITE_ENGINE('sqlite://',echo=False,hide_parameters=True,
                          logging_name='dev09b_querytrial_level_regression')
    logger=engine.logger
    previous=logger.level
    try:
        logger.setLevel(logging.WARNING)
        with engine.connect() as connection:
            assert connection._echo is False
            logger.setLevel(level)
            with pytest.raises(trial._Refused,match='CLIENT_LOGGING_REFUSED'):
                trial._check_client_logging(connection)
        # Also refuse the cached logging switch if the Engine was silenced later.
        with engine.connect() as connection:
            assert connection._echo is True
            logger.setLevel(logging.WARNING)
            with pytest.raises(trial._Refused,match='CLIENT_LOGGING_REFUSED'):
                trial._check_client_logging(connection)
    finally:
        logger.setLevel(previous)
        engine.dispose()


@pytest.mark.parametrize('address',['192.0.2.4','2001:db8::4','2001:0db8:0:0:0:0:0:4'])
def test_real_row_and_rowmapping_identity_types(address):
    engine=_SQLITE_ENGINE('sqlite://',echo=False,hide_parameters=True)
    expected=replace(target(),address='2001:db8::4' if ':' in address else address)
    fixture=Connection().identity.copy();fixture['address']=address
    from sqlalchemy import select,literal,String,Integer
    statement=select(*(literal(v,Integer() if type(v) is int else String()).label(k) for k,v in fixture.items()))
    try:
        with engine.connect() as connection:
            row=connection.execute(statement).one()
            assert isinstance(row,sqlalchemy.engine.Row)
            for item in (row,row._mapping,connection.execute(statement).mappings().one()):
                normalized=trial._row_dict(item)
                assert normalized==fixture
                assert type(normalized['pid']) is int and type(normalized['address']) is str
                trial._binding(normalized,expected)
    finally:engine.dispose()


@pytest.mark.parametrize('address',['192.0.2.4/32','2001:db8::4/128','192.0.2.0/24','2001:db8::/64',
    '192.0.2.4/24','2001:db8::4/64','fe80::1%eth0','localhost','',None,b'192.0.2.4',123])
def test_identity_rejects_masks_networks_zones_and_invalid_types(address):
    conn=Connection();conn.identity['address']=address
    report=trial.run_trial(conn,target())
    assert report.status=='REFUSED' and report.queries[0].status=='REFUSED'
    diagnostic=report.diagnostics[0]
    if type(address) is bytes:
        assert diagnostic==dict(phase='row_serialization',code='ROW_SERIALIZATION_ERROR',exception_class='TypeError')
    else:
        assert diagnostic['phase']=='identity_binding'
        assert diagnostic['code']=='IDENTITY_ADDRESS_INVALID'
    assert all(q.status=='NOT_RUN' for q in report.queries[1:])
    assert conn.closed


def test_invalid_text_exception_class_and_safe_report():
    conn=Connection();conn.identity['address']='secret-password-invalid-address'
    report=trial.run_trial(conn,target())
    assert report.diagnostics[0]==dict(phase='identity_binding',code='IDENTITY_ADDRESS_INVALID',exception_class='ValueError')
    assert 'secret-password' not in report.to_json() and 'SQL' not in report.to_json()


def test_shared_host_sql_and_exact_binding_unchanged():
    from backend.migrations.dev09b_inspection_queries import QUERIES as prepared
    assert 'pg_catalog.host(pg_catalog.inet_server_addr()) AS address' in trial.QUERIES['identity'].sql
    assert trial.QUERIES['identity']==prepared['identity']
    assert all(trial.QUERIES[k]==q for k,q in prepared.items() if k!='identity')
    conn=Connection();conn.identity['address']='2001:db8::4'
    result=trial.run_trial(conn,replace(target(),address='2001:0db8:0:0:0:0:0:4'))
    assert result.status=='COMPLETED'
    conn=Connection();conn.identity['address']='2001:db8::5'
    result=trial.run_trial(conn,replace(target(),address='2001:db8::4'))
    assert result.reason=='IDENTITY_REFUSED'


def test_mapping_serialization_and_stream_diagnostics_are_specific():
    conn=Connection();execute=conn.execute
    def malformed(statement,**kw):
        result=execute(statement,**kw)
        if str(statement)==trial.QUERIES['identity'].sql:result.rows=[object()]
        return result
    conn.execute=malformed
    report=trial.run_trial(conn,target())
    assert report.diagnostics[0]==dict(phase='row_mapping',code='MALFORMED_ROW',exception_class='Refused')
    conn=Connection()
    def fail(*args):raise TypeError('SQL parameters credential DO_NOT_LOG')
    conn.callback=fail
    report=trial.run_trial(conn,target())
    assert report.diagnostics[0]==dict(phase='transaction_control',code='SETUP_PROCESSING_ERROR',exception_class='TypeError')
    assert 'DO_NOT_LOG' not in report.to_json()
