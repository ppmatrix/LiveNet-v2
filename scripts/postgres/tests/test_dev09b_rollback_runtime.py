"""Offline constructed evidence/driver/hosting tests; no grants or PostgreSQL."""
from copy import deepcopy
from dataclasses import asdict
from hashlib import sha256
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from scripts.dedicated.dev09b import codec as c,detailed_catalog as d,layers,own_settings as h
from scripts.dedicated.dev09b import rollback as r,containment as ct,tls,hosting
from scripts.dedicated.dev09b.admission import AdmissionController
from scripts.dedicated.dev09b.model import AttemptState
from scripts.dedicated.dev09b.evidence import OriginObservation
from scripts.dedicated.dev09b.postgres_authority import AuthenticatedAuthorityClient
from scripts.postgres.tests.test_dev09b_detailed import detailed_fixture


def rollback_fixture():
    parts,session,profile=detailed_fixture();snapshot=layers.freeze_expectations(*parts)
    authority=AuthenticatedAuthorityClient(endpoint=Mock(),verifier=None,payload=parts[0],session=session,
        profile_json=profile,clock=None,continuity=None)
    ctl=AdmissionController(authority=authority,session=session,connection=SimpleNamespace(closed=True),
        transaction=None,supervision=None,plan=snapshot.plan)
    ctl.used=True;ctl.closed=True;ctl.state=AttemptState.UNKNOWN
    evidence=dict(schema_version=1,kind='ROLLBACK-BASELINE-V1',collector_id='constructed-independent',
        **{key:parts[0][key] for key in ('target_binding_sha256','request_id','approval_id','attempt_id')},
        subject_session=asdict(session),snapshot=d.parse(r.expected_baseline(snapshot).json),
        migrator_sessions=0,prepared_transactions=0)
    class ModelOrigin:
        def inspect(self,raw):
            value=d.parse(raw)
            return OriginObservation(layers.document_hash(value),value['collector_id'],'OPERATIONAL',True)
    return ctl,snapshot,evidence,ModelOrigin(),SimpleNamespace(confirm=Mock(return_value=None)),SimpleNamespace(persist=Mock(return_value=None))


def test_independent_rollback_records_before_confirming_without_authority():
    ctl,snapshot,evidence,origin,independence,journal=rollback_fixture()
    ctl.authority.endpoint.record.side_effect=OSError('authority unavailable')
    journal.persist.side_effect=lambda raw:c.require(ctl.state is AttemptState.UNKNOWN)
    ctl.confirm_rollback(snapshot,evidence,authenticity=origin,independence=independence,journal=journal)
    assert ctl.state is AttemptState.ROLLED_BACK_CONFIRMED
    assert not ctl.authority.endpoint.record.called
    with pytest.raises(c.Invalid):ctl.confirm_rollback(snapshot,evidence,authenticity=origin,independence=independence,journal=journal)


@pytest.mark.parametrize('fault',['catalog','session','attempt','live_session','prepared','bool','origin','independence','journal','committed'])
def test_rollback_uncertainty_never_promotes_or_releases(fault):
    ctl,snapshot,evidence,origin,independence,journal=rollback_fixture()
    if fault=='catalog':evidence['snapshot']['managed_objects'].pop()
    if fault=='session':evidence['subject_session']['transaction_id']='888'
    if fault=='attempt':evidence['attempt_id']='00000000-0000-0000-0000-000000000888'
    if fault=='live_session':evidence['migrator_sessions']=1
    if fault=='prepared':evidence['prepared_transactions']=1
    if fault=='bool':evidence['migrator_sessions']=False
    if fault=='origin':origin=SimpleNamespace(inspect=lambda raw:OriginObservation('0'*64,evidence['collector_id'],'SYNTHETIC',False))
    if fault=='independence':independence.confirm.return_value=True  # booleans are not this trusted port
    if fault=='journal':journal.persist.side_effect=OSError('lost independent journal ack')
    if fault=='committed':ctl.commit_sent=True
    with pytest.raises((c.Invalid,OSError)):
        ctl.confirm_rollback(snapshot,evidence,authenticity=origin,independence=independence,journal=journal)
    assert ctl.state is AttemptState.UNKNOWN and ctl.connection.closed


def test_helper_policy_v1_is_immutable_v2_is_explicit_and_narrow():
    v1=h.declaration();v2=h.trial_declaration()
    assert v1['grants']==[dict(grantee=h.PROBE,privilege='EXECUTE',grant_option=False)]
    assert h.callers(v1)=={h.PROBE} and h.callers(v2)=={h.PROBE,h.MIGRATOR}
    assert v2['object']==v1['object'] and v2['owner_membership']==v1['owner_membership']
    for value in (v1,v2):h.validate(value)
    bad=deepcopy(v2);bad['grants'][0]['grant_option']=True
    with pytest.raises(c.Invalid):h.validate(bad)
    bad=deepcopy(v2);bad['grants'].append(dict(grantee='PUBLIC',privilege='EXECUTE',grant_option=False))
    with pytest.raises(c.Invalid):h.validate(bad)


def test_helper_migrator_observation_requires_explicit_v2():
    from scripts.postgres.tests.test_dev09b_sql_adapter import helper_sql_fixture
    historical,supplemental,context=helper_sql_fixture()
    historical['identity'][0]['current_user']=h.MIGRATOR
    historical['identity'][0]['session_user']=h.MIGRATOR
    historical['object_acl'].append(dict(family='routine',schema='public',name='dev09b_own_preload_settings',
        grantor=h.OWNER,grantee=h.MIGRATOR,privilege='EXECUTE',grant_option=False))
    h.verify_observed(historical,supplemental,h.trial_declaration())
    with pytest.raises(c.Invalid):h.verify_observed(historical,supplemental,h.declaration())


def test_containment_attempts_all_phases_even_when_first_commit_is_uncertain(monkeypatch):
    calls=[]
    def action(connections,target,callback,**kw):
        calls.append(callback)
        if len(calls)==1:raise OSError('NOLOGIN commit lost')
    monkeypatch.setattr(ct,'admin_action',action)
    monkeypatch.setattr(ct,'verify_target',lambda *a:dict(login=False,sessions=0))
    result=ct.contain_target(None,{})
    assert len(calls)==3 and result['disable_login']=='UNCERTAIN'
    assert result['terminate_sessions']==result['revoke']=='RETURNED'


def test_supervisor_block_does_not_remove_containment_endpoint(monkeypatch):
    continuity=SimpleNamespace(block=Mock(),sample=Mock(side_effect=OSError('storage missing')))
    dep=SimpleNamespace(target={},policy={})
    host=hosting.SupervisorHost(dep,continuity,Mock(),None,None)
    host.tick();assert host.failed
    monkeypatch.setattr(ct,'contain_target',lambda *a:dict(disable_login='RETURNED'))
    assert host.executor_dispatch('contain',{})==dict(disable_login='RETURNED',window_block='DURABLE')
    assert continuity.block.call_count>=2


def test_same_volume_never_counts_as_independent_storage(tmp_path,monkeypatch):
    monkeypatch.setattr(os.path,'ismount',lambda path:True)
    conf=dict(mountpoint=str(tmp_path),device=tmp_path.stat().st_dev,
        authority_and_target_storage_paths=[str(tmp_path),str(tmp_path)],excluded_from_authority_restore=True,
        restore_exclusion_reference='CONSTRUCTED TEST REFERENCE')
    with pytest.raises(c.Invalid):hosting.verify_storage(conf)


def test_listener_minimum_acl_and_no_automatic_socket_replacement(tmp_path):
    caller=os.geteuid()+1
    os.setxattr(tmp_path,'system.posix_acl_access',hosting.acl_bytes(7,[caller],1))
    path=tmp_path/'listener.sock'
    listener=hosting.bind_listener(path,caller)
    try:
        assert os.getxattr(path,'system.posix_acl_access')==hosting.acl_bytes(6,[caller],6)
        with pytest.raises(c.Invalid):hosting.bind_listener(path,caller)
    finally:listener.close()
    assert path.exists()


def test_root_policy_boundary_refuses_repo_or_unprivileged_proposal(tmp_path):
    path=tmp_path/'policy.json';raw=b'{}';path.write_bytes(raw)
    with pytest.raises(c.Invalid):hosting.read_policy(path,sha256(raw).hexdigest())


@pytest.mark.parametrize('fault',[None,'certificate','ca'])
def test_verify_full_and_pin_use_same_driver_and_close_on_mismatch(tmp_path,monkeypatch,fault):
    import psycopg
    password=tmp_path/'password';password.write_bytes(b'PRIVATE');password.chmod(0o600)
    ca=tmp_path/'ca';ca.write_bytes(b'CONSTRUCTED CA BYTES - not a certificate')
    endpoint=dict(tls_server_name='dev09b-querytrial.internal',host='192.0.2.10',port=5432,
        database_name=h.DATABASE,ca_file=str(ca),ca_sha256=sha256(ca.read_bytes()).hexdigest(),
        server_certificate_sha256=sha256(b'CONSTRUCTED DER').hexdigest())
    if fault=='ca':endpoint['ca_sha256']='0'*64
    if fault=='certificate':endpoint['server_certificate_sha256']='0'*64
    driver=SimpleNamespace(close=Mock())
    connect=Mock(return_value=driver);monkeypatch.setattr(psycopg,'connect',connect)
    native=SimpleNamespace(der=Mock(return_value=b'CONSTRUCTED DER'))
    factory=tls.PinnedConnections(endpoint=endpoint,principal=h.MIGRATOR,password_file=password,native=native)
    if fault:
        with pytest.raises(c.Invalid):factory._driver()
        assert driver.close.called == (fault=='certificate')
    else:
        assert factory._driver() is driver
        native.der.assert_called_once_with(driver)
        kwargs=connect.call_args.kwargs
        assert kwargs['sslmode']=='verify-full' and kwargs['host']=='dev09b-querytrial.internal'
        assert kwargs['sslrootcert']==str(ca) and kwargs['gssencmode']=='disable'
        assert not driver.close.called


def test_native_certificate_provider_resolves_only_pinned_loaded_dependencies():
    import psycopg
    import psycopg_binary.pq
    paths={line.split()[-1] for line in Path('/proc/self/maps').read_text().splitlines() if 'psycopg_binary.libs/' in line}
    refs=dict(extension=Path(psycopg_binary.pq.__file__).resolve())
    for kind in ('libpq','libssl','libcrypto'):
        matches=[Path(path) for path in paths if Path(path).name.startswith(kind+'-')]
        assert len(matches)==1
        refs[kind]=matches[0]
    refs={key:dict(path=str(path),sha256=sha256(path.read_bytes()).hexdigest()) for key,path in refs.items()}
    provider=tls.NativePeerCertificate(refs)
    assert callable(provider.der)  # no PGconn pointer/connection was fabricated
    refs['libpq']['sha256']='0'*64
    with pytest.raises(c.Invalid):tls.NativePeerCertificate(refs)


def test_cli_refuses_unapproved_input_before_any_operational_dispatch(tmp_path,monkeypatch,capsys):
    from scripts.postgres import dev09b_operational_cli as cli
    path=tmp_path/'proposal.json';path.write_bytes(b'{}')
    execute=Mock();monkeypatch.setattr(cli,'executor',execute)
    assert cli.main(['executor','--policy',str(path),'--policy-sha256',sha256(b'{}').hexdigest()])==78
    assert not execute.called and 'REFUSED' in capsys.readouterr().out


def test_extension_preflight_does_not_require_or_grant_internal_support_rights():
    from scripts.dedicated.dev09b.extension_privileges import inspect
    values={key:True for key in ('public_usage','inventory_create','uuid_usage','varchar_usage','text_usage',
        'timestamptz_usage','range_usage','range_constructor','now_function')}
    values.update(opclasses=2,internal_uuid_storage_usage=False,internal_text_storage_usage=False)
    connection=Mock();connection.execute.return_value.mappings.return_value.one.return_value=values
    assert inspect(connection)==values
    assert len(connection.execute.call_args_list)==1
    values['range_constructor']=False
    with pytest.raises(c.Invalid):inspect(connection)


def test_final_cleanup_comparison_does_not_accept_remaining_temporary_rights():
    from scripts.dedicated.dev09b.trial_policy import cleaned_snapshot
    ctl,snapshot,evidence,*_=rollback_fixture()
    evidence['kind']='ROLLBACK-CLEANED-V1'
    target=layers.read_snapshot(snapshot)[1]
    with pytest.raises(c.Invalid):r.validate(snapshot,ctl.session,evidence,cleaned=True)
    evidence['snapshot']=cleaned_snapshot(evidence['snapshot'],target['migrator_role'])
    r.validate(snapshot,ctl.session,evidence,cleaned=True)
    evidence['snapshot']['public_acl'].append(dict(grantee=target['migrator_role'],privilege='CREATE',grant_option=False))
    with pytest.raises(c.Invalid):r.validate(snapshot,ctl.session,evidence,cleaned=True)


def test_executor_always_requests_containment_after_connection_failure(monkeypatch):
    from scripts.postgres import dev09b_operational_cli as cli
    policy=dict(accounts=dict(executor=dict(uid=123),supervisor=dict(uid=456)),
        sockets=dict(supervisor_executor='/missing'))
    dep=SimpleNamespace(policy=policy,connections=Mock(side_effect=OSError('PRIVATE')))
    calls=[]
    class RPC:
        def __init__(self,*args,**kwargs):pass
        def call(self,method,args):calls.append(method);raise OSError('unavailable')
    monkeypatch.setattr(cli,'LocalRPC',RPC);monkeypatch.setattr(cli,'assert_account',lambda a:None)
    result=cli.executor(dep)
    assert result['state']=='UNKNOWN' and calls==['contain','verify_final']
    assert 'PRIVATE' not in str(result)


def test_inert_recovery_identity_gets_no_connect_grant():
    from scripts.dedicated.dev09b import physical as p
    parts,*_=detailed_fixture();target=parts[1];physical=parts[5]
    params=deepcopy(physical['parameters'])
    recovery=params['roles']['recovery']
    for role in params['administrative_roles']:
        if role['name']==recovery:role['login']=False
    inputs=d.migration_inputs(physical,parts[4],parts[6])
    expected=p.compile_profile('APP-ENTRY',target,params,inputs,prerequisite=0)
    assert not any(row['grantee']==recovery for row in d.parse(expected.json)['database_acl'])


def test_existing_admin_database_owner_alias_adds_no_duplicate_role_or_acl():
    from scripts.dedicated.dev09b import physical as p
    parts,*_=detailed_fixture();physical=parts[5];params=deepcopy(physical['parameters'])
    params['roles']['database_owner']=params['roles']['admin']
    expected=p.compile_profile('APP-ENTRY',parts[1],params,d.migration_inputs(physical,parts[4],parts[6]),prerequisite=0)
    observed=d.parse(expected.json);admin=params['roles']['admin']
    assert sum(role['name']==admin for role in observed['roles'])==1
    assert not any(row['grantee']==admin for row in observed['database_acl'])
    params['roles']['runtime']=admin
    with pytest.raises(c.Invalid):p.validate_parameters(params,parts[1])


def test_containment_bootstrap_needs_no_approval_profile_or_authority():
    policy=dict(connections=dict(admin=dict(principal=h.ADMIN,endpoint=dict(database_name=h.DATABASE))))
    dep=hosting.ContainmentDeployment(policy)
    assert dep.target==dict(system_identifier=h.TARGET_SID,database_name=h.DATABASE,migrator_role=h.MIGRATOR)


def test_containment_still_runs_when_interlock_write_fails(monkeypatch):
    continuity=SimpleNamespace(block=Mock(side_effect=OSError('storage unavailable')))
    host=hosting.SupervisorHost(SimpleNamespace(target={},policy={}),continuity,Mock(),None,None)
    monkeypatch.setattr(ct,'contain_target',lambda *a:dict(disable_login='RETURNED'))
    assert host.executor_dispatch('contain',{})==dict(disable_login='RETURNED',window_block='UNCERTAIN')
    assert host.failed


def test_authority_bootstrap_refuses_nonroot_before_connections():
    from scripts.postgres.dev09b_authority_bootstrap import bootstrap
    dep=SimpleNamespace(connections=Mock())
    with pytest.raises(c.Invalid):bootstrap(dep)
    assert not dep.connections.called


@pytest.mark.parametrize('wrong_sid',[False,True])
def test_authority_bootstrap_wires_existing_schema_without_reset_or_fixture(tmp_path,monkeypatch,wrong_sid):
    from scripts.postgres import dev09b_authority_bootstrap as b
    root=Path(__file__).resolve().parents[3]
    schema=root/'scripts/postgres/dev09b_authority_schema.proposed.sql'
    policy=dict(authority_destination=dict(database=b.DATABASE,principal=b.SERVICE,system_identifier='9000'),
        files=dict(authority_schema=dict(path=str(schema),sha256=sha256(schema.read_bytes()).hexdigest())),
        source_root=str(root),continuity_token='00000000-0000-0000-0000-000000000123')
    tx=SimpleNamespace(is_active=False,commit=Mock(),rollback=Mock())
    conn=Mock();conn.in_transaction.return_value=False;conn.begin.return_value=tx
    statements=[]
    def execute(sql,parameters=None):
        statements.append(str(sql))
        result=Mock()
        result.mappings.return_value.one.return_value=dict(database=b.DATABASE,principal=b.ADMIN,
            effective_principal=b.ADMIN,sid='wrong' if wrong_sid else '9000')
        return result
    conn.execute.side_effect=execute
    dep=SimpleNamespace(policy=policy,target=dict(system_identifier=h.TARGET_SID),connections=lambda name:lambda:conn,
        envelope=b'CONSTRUCTED MODEL BYTES - no approval',snapshot=SimpleNamespace(**{key:b'MODEL' for key in ('payload','target','executor','plan','semantic','physical','provenance')}),
        payload=dict(approval_id='00000000-0000-0000-0000-000000000124',attempt_id='00000000-0000-0000-0000-000000000125',authority_epoch=1,revocation_epoch=1))
    monkeypatch.setattr(b.os,'geteuid',lambda:0)
    if wrong_sid:
        with pytest.raises(c.Invalid):b.bootstrap(dep)
        assert not conn.exec_driver_sql.called and not tx.commit.called
    else:
        result=b.bootstrap(dep)
        assert result['status']=='SIGNED_APPROVAL_LOADED_SERVICE_STILL_NOLOGIN'
        conn.exec_driver_sql.assert_called_once_with(schema.read_text())
        assert sum(sql.startswith('INSERT INTO') for sql in statements)==2
        assert not any(sql.startswith(('UPDATE','DELETE','ALTER ROLE')) or 'ON CONFLICT' in sql for sql in statements)
        tx.commit.assert_called_once()
    conn.close.assert_called_once()
