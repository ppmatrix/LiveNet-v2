"""Prepared future READ ONLY trial tested exclusively with constructed SQL rows."""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import pytest

from scripts.postgres import dev09b_detailed_querytrial as t
from scripts.postgres.tests.test_dev09b_sql_adapter import sql_fixture,connection_fixture,ResultDouble


@pytest.fixture(autouse=True)
def no_resources(monkeypatch):
    import socket,subprocess
    denied=Mock(side_effect=AssertionError('No SQL, processes or network'))
    for owner,name in ((socket,'socket'),(socket,'create_connection'),(subprocess,'run'),(subprocess,'Popen')):monkeypatch.setattr(owner,name,denied)


def trial_fixture(context=True):
    raw,extra,ctx=sql_fixture();conn,tx,results,calls=connection_fixture(raw,extra)
    active=[False];closed=[False];setup=[];original_execute=conn.execute
    conn.in_transaction=lambda:active[0]
    conn.get_transaction=lambda:tx
    def begin():active[0]=True;return tx
    conn.begin=begin
    def rollback():active[0]=False
    tx.rollback=rollback;conn.rollback=rollback
    def close():conn.closed=True;closed[0]=True
    conn.close=close
    def execute(sql,parameters=None):
        if str(sql).startswith('SET '):
            setup.append(str(sql));result=ResultDouble([],True);results.append(result);return result
        return original_execute(sql,parameters)
    conn.execute=execute
    inputs=dict(collector_id='constructed-fixture',selections=dict(role_names=[r['name'] for r in extra['role_details']],
                system_routines=['pg_catalog.pg_control_system'],language_names=['plpgsql']),context=ctx if context else None)
    return conn,inputs,raw,extra,results,calls,setup


def test_readonly_capture_conversion_and_containment_without_sql():
    conn,inputs,raw,extra,results,calls,setup=trial_fixture()
    report,batch=t.read_only_trial(conn,inputs,dict(database='livenet_v2_dev',system_identifier='123'))
    assert report['status']=='READ_ONLY_COLLECTION_CONVERSION_RETURNED' and report['identity_before_after']=='MATCH'
    assert report['rollback']==report['close']=='RETURNED' and conn.closed
    assert setup[0]=='SET TRANSACTION READ ONLY' and len(setup)==4
    assert all(r.closed for r in results) and report['operational_authorization'] is False
    assert len(report['queries'])==len(t.ins.QUERIES)+len(t.DETAIL_QUERIES)  # helper not installed/declared


def test_missing_source_context_is_explicit_not_learned_from_rows():
    conn,inputs,raw,extra,results,calls,setup=trial_fixture(context=False)
    report,batch=t.read_only_trial(conn,inputs,dict(system_identifier='123'))
    assert batch is not None and inputs['context'] is None
    assert report['failure_phase']=='conversion' and 'trial.fixed_conversion_context' in report['code']
    assert report['status']=='REFUSED' and report['rollback']==report['close']=='RETURNED'
    assert all(x['status']=='RETURNED' for x in report['queries'].values())


def test_hidden_session_setting_requires_actual_same_session_observation():
    conn,inputs,raw,extra,results,calls,setup=trial_fixture()
    next(r for r in raw['settings'] if r['name']=='session_preload_libraries')['setting']=None
    report,batch=t.read_only_trial(conn,inputs,dict(system_identifier='123'))
    assert report['status']=='READ_ONLY_COLLECTION_CONVERSION_RETURNED'
    assert report['unavailable_settings']==['session_preload_libraries']
    assert report['queries']['detail.own_preload_settings']['count']==2
    assert report['operational_authorization'] is False
    assert report['rollback']==report['close']=='RETURNED'


def test_query_failure_diagnostic_has_no_sql_or_row_values():
    conn,inputs,raw,extra,results,calls,setup=trial_fixture()
    original=conn.execute
    def execute(sql,parameters=None):
        if str(sql)==t.ins.QUERIES['columns'].sql:raise RuntimeError('PRIVATE SQL PARAMETERS PASSWORD')
        return original(sql,parameters)
    conn.execute=execute
    report,batch=t.read_only_trial(conn,inputs,dict(system_identifier='123'))
    assert batch is None and report['failure_phase']=='collection'
    assert report['queries']['columns']==dict(status='REFUSED',exception_class='RuntimeError')
    assert 'PRIVATE' not in json.dumps(report) and 'PASSWORD' not in json.dumps(report)
    assert report['rollback']==report['close']=='RETURNED'


def test_proposed_inputs_are_explicitly_incomplete_and_static_only():
    path=Path('scripts/postgres/dev09b_detailed_querytrial_inputs.proposed.json')
    value=t.validate_inputs(path.read_bytes());assert value['context'] is None
    assert t.main(['validate-only','--inputs',str(path)])==0
    assert set(value['selections'])=={'role_names','system_routines','language_names'}


def test_wrong_target_refuses_before_catalog_queries_and_closes():
    conn,inputs,raw,extra,results,calls,setup=trial_fixture()
    report,batch=t.read_only_trial(conn,inputs,dict(system_identifier='different'))
    assert report['status']=='REFUSED' and batch is None
    assert set(report['queries'])=={'identity_before'}
    assert report['rollback']==report['close']=='RETURNED' and all(r.closed for r in results)


@pytest.mark.parametrize('field,value',[('backend_start',None),('xact_start',False),('pid',True)])
def test_incomplete_collector_identity_refuses_before_catalog(field,value):
    conn,inputs,raw,extra,results,calls,setup=trial_fixture()
    raw['identity'][0][field]=value
    report,batch=t.read_only_trial(conn,inputs,dict(system_identifier='123'))
    assert report['status']=='REFUSED' and batch is None
    assert set(report['queries'])=={'identity_before'}
    assert report['rollback']==report['close']=='RETURNED' and all(r.closed for r in results)


def test_processing_failure_preserves_partial_raw_capture_without_authorization():
    conn,inputs,raw,extra,results,calls,setup=trial_fixture()
    raw['extension_properties'][1]['properties']=None
    partial={}
    report,batch=t.read_only_trial(conn,inputs,dict(system_identifier='123'),raw_capture=partial)
    assert batch is None and report['status']=='REFUSED'
    assert report['queries']['process.extension_properties']==dict(status='REFUSED',exception_class='PrerequisiteRefused')
    assert 'extension_properties' in partial and len(partial)==33
    assert report['rollback']==report['close']=='RETURNED'
    assert report['operational_authorization'] is False


def test_missing_direct_session_observation_never_uses_approved_value():
    conn,inputs,raw,extra,results,calls,setup=trial_fixture()
    next(r for r in raw['settings'] if r['name']=='session_preload_libraries')['setting']=None
    next(r for r in extra['own_preload_settings'] if r['name']=='session_preload_libraries')['setting']=None
    report,batch=t.read_only_trial(conn,inputs,dict(system_identifier='123'))
    assert report['status']=='REFUSED' and report['failure_phase']=='conversion'
    assert report['rollback']==report['close']=='RETURNED'


def test_helper_observation_without_conversion_context_remains_a_capture_only():
    from scripts.postgres.tests.test_dev09b_sql_adapter import helper_sql_fixture
    raw,extra,ctx=helper_sql_fixture();conn,tx,results,calls=connection_fixture(raw,extra)
    active=[False];original=conn.execute
    conn.in_transaction=lambda:active[0]
    def begin():active[0]=True;return tx
    conn.begin=begin
    tx.rollback=lambda:active.__setitem__(0,False)
    conn.rollback=tx.rollback
    conn.close=lambda:setattr(conn,'closed',True)
    def execute(sql,parameters=None):
        if str(sql).startswith('SET '):return ResultDouble([],False)
        return original(sql,parameters)
    conn.execute=execute
    inputs=dict(collector_id='helper-only-fixture',selections=dict(role_names=[r['name'] for r in extra['role_details']],system_routines=['pg_catalog.pg_control_system'],language_names=['plpgsql']),context=None,approved_helpers=ctx['approved_helpers'])
    report,batch=t.read_only_trial(conn,inputs,dict(system_identifier=t.SID))
    assert report['status']=='REFUSED' and report['failure_phase']=='conversion'
    assert report['helper_observed_settings']==['session_preload_libraries','shared_preload_libraries']
    assert 'trial.fixed_conversion_context' in report['code']
    assert report['operational_authorization'] is False and report['rollback']==report['close']=='RETURNED'
    assert len([name for _,name,_ in calls if name=='helper_preload_settings'])==1


def test_safe_specific_conversion_diagnostic_without_row_values():
    conn,inputs,raw,extra,results,calls,setup=trial_fixture()
    raw['object_acl'].append(dict(family='routine',schema='public',name='UNBOUND_PRIVATE_ROW_VALUE',grantor='private',grantee='private',privilege='EXECUTE',grant_option=False))
    report,batch=t.read_only_trial(conn,inputs,dict(system_identifier='123'))
    assert report['status']=='REFUSED' and report['code']=='UNRESOLVED_ROUTINE_ACL'
    assert report['exception_class']=='PrerequisiteRefused' and report['failure_phase']=='conversion'
    assert 'PRIVATE' not in json.dumps(report) and report['rollback']==report['close']=='RETURNED'
