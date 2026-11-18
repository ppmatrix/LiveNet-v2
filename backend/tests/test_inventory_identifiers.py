"""INV-ID-01: real isolated PostgreSQL/Unix locks, never operational DB/TCP."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, func, text, true, false
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError, ProgrammingError
from alembic.migration import MigrationContext
from alembic.operations import Operations

from test_discovery_postgres_lifecycle import postgres
from test_discovery import prohibit_real_detection_sockets
from app import create_app
from app.inventory import identifiers as ids
from app.inventory.models import Resource, ResourceIdentifier
from app.inventory.access import InventoryIdentity
from app.inventory.service import ResourceConflict, ArchivedResource
from app.audit.models import AuditEvent
from installation.admin import IDENTIFIER_GRANTS
from test_security_api import api, password_hash, login, csrf, ORIGIN


@pytest.fixture
def store(postgres):
    with postgres.admin.begin() as c:
        assert Path(c.execute(text('SHOW data_directory')).scalar_one())==postgres.data
        c.execute(text('TRUNCATE discovery.decisions,discovery.observations,discovery.jobs,audit.events,inventory.resource_identifiers,inventory.resources'))
        c.execute(text('GRANT UPDATE(row_version,updated_at) ON inventory.resources TO discovery_test_runtime'))
        # Fixture's old broad identifier SELECT is removed to prove column ACLs.
        c.execute(text('REVOKE ALL ON inventory.resource_identifiers FROM discovery_test_runtime'))
        for grant in IDENTIFIER_GRANTS:c.execute(text(grant.format(runtime='discovery_test_runtime')))
    sessions=sessionmaker(bind=postgres.runtime,expire_on_commit=False)
    admin=sessionmaker(bind=postgres.admin,expire_on_commit=False)
    now=datetime.now(timezone.utc);rids=[uuid4(),uuid4(),uuid4()]
    with admin.begin() as s:
        for rid in rids:s.add(Resource(id=rid,resource_type='service',display_name='Isolated fixture',description=None,
            attributes={},administrative_state='active',created_at=now,updated_at=now,row_version=1))
    return SimpleNamespace(sessions=sessions,admin=admin,rids=rids,identity=InventoryIdentity(uuid4()),postgres=postgres)


def data(value='10.42.0.1',ns='lab:test',version=1,**extra):
    return ids.payload(dict(identifier_value=value,namespace=ns,row_version=version)|extra)


def add(store,rid=None,**kwargs):
    with store.sessions.begin() as s:return ids.add(s,rid or store.rids[0],data(**kwargs),store.identity,true(),true())


def close(store,result,version=None):
    with store.sessions.begin() as s:return ids.close(s,UUID(result['identifier']['resource_id']),UUID(result['identifier']['id']),
        {'row_version':version or result['resource_row_version']},store.identity,true())


@pytest.mark.parametrize('value',['1.2.3','010.2.3.4','1.2.3.4/32','1.2.3.4:80','localhost','::1','0x12345678',1,None,'1.2.3.4\n','0.0.0.0','224.0.0.1','255.255.255.255','x'*65])
def test_invalid_ipv4(value):
    with pytest.raises(ids.IdentifierError):ids.ipv4(value)


@pytest.mark.parametrize('value',[None,'','Lab',' lab','lab ','lab/name','lab\n','é','x'*256])
def test_invalid_namespace(value):
    with pytest.raises(ids.IdentifierError):ids.namespace(value)


def test_normalization_and_read_only_fields():
    assert ids.ipv4(' 10.42.0.1 ')== '10.42.0.1'
    for extra in ({'verified_at':None},{'source_type':'discovery'},{'row_version':True},{'confirm_shared':True}):
        with pytest.raises(ids.IdentifierError):data(**extra)


def test_add_close_reassign_and_noop_dates_versions_audits(store):
    first=add(store,value=' 10.42.0.1 ')
    assert first['changed'] and first['identifier']['identifier_value']==' 10.42.0.1 '
    assert first['identifier']['verification_status']=='unverified' and first['identifier']['confidence'] is None
    again=add(store)
    assert not again['changed'] and again['identifier']==first['identifier'] and again['resource_row_version']==2
    ended=close(store,first)
    repeat=close(store,first,version=1)
    assert not repeat['changed'] and repeat['identifier']==ended['identifier']
    new=add(store,version=3)
    assert new['identifier']['id']!=first['identifier']['id']
    assert close(store,first,version=1)['changed'] is False
    with store.admin() as s:
        assert s.scalar(select(func.count()).select_from(AuditEvent))==3
        assert s.get(ResourceIdentifier,UUID(new['identifier']['id'])).valid_until is None


def test_versions_archived_and_other_sources(store):
    first=add(store)
    with pytest.raises(ResourceConflict):add(store,value='10.42.0.2')
    with pytest.raises(ResourceConflict):close(store,first,version=1)
    with store.admin.begin() as s:
        s.get(ResourceIdentifier,UUID(first['identifier']['id'])).source_type='collector'
    with pytest.raises(ids.IdentifierError) as e:close(store,first)
    assert e.value.code=='identifier_read_only'
    with store.admin.begin() as s:s.get(Resource,store.rids[0]).administrative_state='archived'
    with pytest.raises(ArchivedResource):add(store,value='10.42.0.3',version=2)


def test_concurrent_same_tuple_is_one_row_and_event(store):
    with ThreadPoolExecutor(max_workers=6) as pool:results=list(pool.map(lambda _:add(store),range(6)))
    assert len({r['identifier']['id'] for r in results})==1 and sum(r['changed'] for r in results)==1
    with store.admin() as s:
        assert s.scalar(select(func.count()).select_from(ResourceIdentifier))==1
        assert s.scalar(select(func.count()).select_from(AuditEvent))==1


def test_coincidences_confirmation_changes_and_namespaces(store):
    first=add(store)
    with pytest.raises(ids.IdentifierError) as e:add(store,rid=store.rids[1])
    assert e.value.code=='identifier_conflict';revision=e.value.details['conflict_revision']
    second=add(store,rid=store.rids[1],confirm_shared=True,conflict_revision=revision)
    with pytest.raises(ids.IdentifierError) as e:add(store,rid=store.rids[2],confirm_shared=True,conflict_revision=revision)
    assert e.value.code=='conflict_changed'
    close(store,first);close(store,second)
    assert add(store,rid=store.rids[2])['changed']
    assert add(store,rid=store.rids[0],ns='other',version=3)['changed']


def test_concurrent_cross_resource_requires_confirmation(store):
    def submit(rid):
        try:return add(store,rid=rid)['changed']
        except ids.IdentifierError as e:return e.code
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(submit,store.rids[:2]))
    assert sorted(results,key=str)==sorted([True,'identifier_conflict'],key=str)


def test_audit_failure_rolls_back_identifier_and_parent(store,monkeypatch):
    monkeypatch.setattr(ids,'record_audit_event',Mock(side_effect=RuntimeError('constructed audit failure')))
    with pytest.raises(RuntimeError):add(store)
    with store.admin() as s:
        assert s.scalar(select(func.count()).select_from(ResourceIdentifier))==0
        assert s.get(Resource,store.rids[0]).row_version==1


def test_runtime_constraints_and_minimal_grants(store):
    first=add(store)
    with pytest.raises(IntegrityError):
        with store.sessions.begin() as s:
            original=s.get(ResourceIdentifier,UUID(first['identifier']['id']))
            values={c.name:getattr(original,c.name) for c in ResourceIdentifier.__table__.columns};values['id']=uuid4()
            s.add(ResourceIdentifier(**values))
    for statement in ('DELETE FROM inventory.resource_identifiers','UPDATE inventory.resource_identifiers SET normalized_value=normalized_value',
                      'UPDATE inventory.resource_identifiers SET source_type=source_type'):
        with pytest.raises(ProgrammingError):
            with store.postgres.runtime.begin() as c:c.execute(text(statement))
    with store.sessions.begin() as s:
        row=s.get(ResourceIdentifier,UUID(first['identifier']['id']));row.namespace=None
        with pytest.raises(ProgrammingError):s.flush()  # namespace UPDATE is not granted
        s.rollback()


def test_api_scope_payload_history_and_parent_version(store):
    access=SimpleNamespace(resolve_identity=lambda:store.identity,read_scope=lambda i:true(),update_scope=lambda i:true(),can_create=lambda *a:True)
    app=create_app('testing',inventory_access=access,inventory_session_factory=store.sessions)
    client=app.test_client();base='/api/v1/inventory/resources/'+str(store.rids[0])+'/identifiers'
    response=client.post(base,json=dict(identifier_value='10.42.0.1',namespace='lab',row_version=1))
    assert response.status_code==201;first=response.json
    assert client.get(base).json['resource_row_version']==2
    assert client.get(response.headers['Location']).json['identifier']==first['identifier']
    assert client.post(base+'/'+first['identifier']['id']+'/close',json={'row_version':2}).status_code==200
    assert client.get(base).json['total']==0 and client.get(base+'?state=closed').json['total']==1
    access.update_scope=lambda i:None
    assert client.post(base,json={}).status_code==403
    access.read_scope=lambda i:false()
    assert client.get(base).status_code==404
    access.resolve_identity=lambda:None
    assert client.get(base).status_code==401


def test_preflight_and_real_additive_migration(store,monkeypatch):
    from installation.runner import StandardScope
    from installation import STANDARD_ATTR,Refused
    path=Path(__file__).parents[1]/'installation/versions/d002a01a7230_manual_identifiers.py'
    spec=importlib.util.spec_from_file_location('isolated_identifier_migration',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    with store.postgres.admin.begin() as c:
        c.execute(text('DROP INDEX inventory.uq_identifiers_manual_ipv4_open'))
        c.execute(text('ALTER TABLE inventory.resource_identifiers DROP CONSTRAINT ck_identifiers_manual_ipv4_namespace'))
        scope=object.__new__(StandardScope)
        scope.require=lambda schema,connection: (schema=='inventory' and connection is c) or pytest.fail('Wrong migration target')
        ops=Operations(MigrationContext.configure(c))
        proxy=SimpleNamespace(get_context=lambda:SimpleNamespace(config=SimpleNamespace(attributes={STANDARD_ATTR:scope})),get_bind=lambda:c,
            execute=ops.execute,create_check_constraint=ops.create_check_constraint,create_index=ops.create_index)
        monkeypatch.setattr(module,'op',proxy)
        assert not any(ids.legacy_preflight(c).values());module.upgrade()
    first=add(store)
    with store.admin.begin() as s:s.get(ResourceIdentifier,UUID(first['identifier']['id'])).identifier_type='IPv4'
    with store.postgres.admin.connect() as c:assert ids.legacy_preflight(c)['noncanonical_type']==1
    with store.postgres.admin.begin() as c:
        scope=object.__new__(StandardScope);scope.require=lambda schema,connection: (schema=='inventory' and connection is c) or pytest.fail('Wrong migration target')
        ops=Operations(MigrationContext.configure(c))
        monkeypatch.setattr(module,'op',SimpleNamespace(get_context=lambda:SimpleNamespace(config=SimpleNamespace(attributes={STANDARD_ATTR:scope})),get_bind=lambda:c,
            execute=ops.execute,create_check_constraint=ops.create_check_constraint,create_index=ops.create_index))
        with pytest.raises(Refused,match='INV_ID_01_LEGACY_DATA_INCOMPATIBLE'):module.upgrade()
        assert c.execute(text('SELECT count(*) FROM inventory.resource_identifiers')).scalar_one()==1


def test_actual_authentication_csrf_and_editor_scope(store,api):
    from app.security.models import GlobalRoleGrant
    app,client,authstore,user,_=api
    app.extensions['inventory']._session_factory=store.sessions
    base='/api/v1/inventory/resources/'+str(store.rids[0])+'/identifiers'
    assert client.get(base,base_url=ORIGIN).status_code==401
    assert login(client).status_code==200
    body=dict(identifier_value='10.42.0.1',namespace='lab',row_version=1)
    assert client.post(base,base_url=ORIGIN,json=body,headers={'Origin':ORIGIN}).json['error']['code']=='invalid_csrf'
    assert client.post(base,base_url=ORIGIN,json=body,headers={'Origin':ORIGIN,'X-CSRF-Token':csrf(client)}).status_code==403
    authstore.grants.append(GlobalRoleGrant(user_id=user.id,role='inventory_editor',scope_type='global',scope_id=None))
    response=client.post(base,base_url=ORIGIN,json=body,headers={'Origin':ORIGIN,'X-CSRF-Token':csrf(client)})
    assert response.status_code==201
    assert client.get(base,base_url=ORIGIN).headers['Cache-Control']=='no-store'


def test_discovery_only_uses_open_nonmanual_identifier_hints(store):
    from app.discovery.service import Repository
    from app.discovery.models import Observation
    now=datetime.now(timezone.utc);obs=Observation(ip='10.42.0.1')
    first=add(store)
    repo=Repository(store.sessions)
    with store.sessions() as s:assert repo._matches(s,obs,true())[0]==[]
    with store.admin.begin() as s:s.get(ResourceIdentifier,UUID(first['identifier']['id'])).source_type='collector'
    with store.sessions() as s:assert len(repo._matches(s,obs,true())[0])==1
    with store.admin.begin() as s:
        row=s.get(ResourceIdentifier,UUID(first['identifier']['id']));row.valid_until=datetime.now(timezone.utc)
    with store.sessions() as s:assert repo._matches(s,obs,true())[0]==[]


def test_close_audit_rollback_and_temporal_error(store,monkeypatch):
    first=add(store)
    original=ids.record_audit_event
    monkeypatch.setattr(ids,'record_audit_event',Mock(side_effect=RuntimeError('constructed close audit failure')))
    with pytest.raises(RuntimeError):close(store,first)
    monkeypatch.setattr(ids,'record_audit_event',original)
    with store.admin() as s:
        assert s.get(ResourceIdentifier,UUID(first['identifier']['id'])).valid_until is None
        assert s.get(Resource,store.rids[0]).row_version==2
    monkeypatch.setattr(ids,'clock',lambda s:datetime.fromisoformat(first['identifier']['valid_from'].replace('Z','+00:00')))
    with pytest.raises(ids.IdentifierError) as e:close(store,first)
    assert e.value.code=='temporal_conflict'


def test_legacy_report_blocks_duplicates_null_namespace_without_rewrite(store):
    first=add(store)
    with store.postgres.admin.begin() as c:
        c.execute(text('DROP INDEX inventory.uq_identifiers_manual_ipv4_open'))
        c.execute(text('ALTER TABLE inventory.resource_identifiers DROP CONSTRAINT ck_identifiers_manual_ipv4_namespace'))
        c.execute(text("UPDATE inventory.resource_identifiers SET namespace=NULL,identifier_type=' IPv4 '"))
        c.execute(text("INSERT INTO inventory.resource_identifiers SELECT :id,resource_id,identifier_type,identifier_value,normalized_value,namespace,source_type,source_instance,first_seen_at,last_seen_at,verified_at,verification_status,confidence,evidence,valid_from,valid_until,created_at,updated_at FROM inventory.resource_identifiers"),dict(id=uuid4()))
        counts=ids.legacy_preflight(c)
        assert counts['duplicate_active']==1 and counts['invalid_namespace']==2 and counts['noncanonical_type']==2
        c.rollback()  # DDL + constructed bad data never survive this test.


@pytest.mark.parametrize('ns',[None,'Lab',' lab','lab\n','é'])
def test_namespace_check_is_enforced_by_postgresql(store,ns):
    first=add(store)
    with store.admin() as s:
        row=s.get(ResourceIdentifier,UUID(first['identifier']['id']))
        values={c.name:getattr(row,c.name) for c in ResourceIdentifier.__table__.columns}
    values.update(id=uuid4(),namespace=ns)
    with pytest.raises(IntegrityError) as e:
        with store.admin.begin() as s:s.add(ResourceIdentifier(**values))
    assert e.value.orig.diag.constraint_name=='ck_identifiers_manual_ipv4_namespace'


def test_different_concurrent_additions_respect_parent_version(store):
    def submit(address):
        try:return add(store,value=address)['changed']
        except ResourceConflict:return 'version_conflict'
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(submit,['10.42.0.1','10.42.0.2']))
    assert sum(v is True for v in results)==1 and results.count('version_conflict')==1


def test_concurrent_closes_preserve_one_end_and_audit(store):
    first=add(store)
    with ThreadPoolExecutor(max_workers=5) as pool:results=list(pool.map(lambda _:close(store,first),range(5)))
    assert sum(r['changed'] for r in results)==1
    assert len({r['identifier']['valid_until'] for r in results})==1
    assert {r['resource_row_version'] for r in results}=={3}
    with store.admin() as s:assert s.scalar(select(func.count()).select_from(AuditEvent))==2


def test_visible_coincidence_totals_truncation_and_full_revision(store):
    first=add(store,rid=store.rids[1])
    with store.admin.begin() as s:
        sample=s.get(ResourceIdentifier,UUID(first['identifier']['id']))
        values={c.name:getattr(sample,c.name) for c in ResourceIdentifier.__table__.columns}
        hidden=[]
        for i in range(24):
            rid=uuid4();s.add(Resource(id=rid,resource_type='service',display_name='Peer fixture',attributes={},administrative_state='active',
                created_at=sample.created_at,updated_at=sample.updated_at,row_version=1))
            s.add(ResourceIdentifier(**(values|dict(id=uuid4(),resource_id=rid))))
            if i>=22:hidden.append(rid)
    scope=Resource.id.not_in(hidden)
    with store.sessions() as s:
        rows,details=ids.peers(s,store.rids[0],'lab:test','10.42.0.1',scope)
        assert len(rows)==25 and details['visible_total']==23 and details['truncated'] is True
        assert len(details['conflicts'])==20
        assert all(UUID(r['resource_id']) not in hidden for r in details['conflicts'])
        _,all_visible=ids.peers(s,store.rids[0],'lab:test','10.42.0.1',true())
        _,none_visible=ids.peers(s,store.rids[0],'lab:test','10.42.0.1',false())
    assert all_visible['visible_total']==25
    assert none_visible['visible_total']==0 and none_visible['conflicts']==[] and none_visible['truncated'] is False
    assert details['conflict_revision']==all_visible['conflict_revision']==none_visible['conflict_revision']
    # Closing an undisclosed association must still invalidate the full revision.
    with store.admin.begin() as s:
        row=s.scalar(select(ResourceIdentifier).where(ResourceIdentifier.resource_id==hidden[0]));row.valid_until=datetime.now(timezone.utc)
    with pytest.raises(ids.IdentifierError) as error:
        add(store,confirm_shared=True,conflict_revision=details['conflict_revision'])
    assert error.value.code=='conflict_changed'


def test_lost_commit_response_is_reconciled_without_duplicate(store):
    from sqlalchemy import event
    access=SimpleNamespace(resolve_identity=lambda:store.identity,read_scope=lambda i:true(),update_scope=lambda i:true())
    client=create_app('testing',inventory_access=access,inventory_session_factory=store.sessions).test_client()
    def lost(session):raise RuntimeError('constructed response lost after commit')
    event.listen(store.sessions,'after_commit',lost,once=True)
    base='/api/v1/inventory/resources/'+str(store.rids[0])+'/identifiers'
    body=dict(identifier_value='10.42.0.1',namespace='lab',row_version=1)
    assert client.post(base,json=body).status_code==500
    assert client.get(base).json['total']==1
    response=client.post(base,json=body)
    assert response.status_code==200 and response.json['changed'] is False
    with store.admin() as s:assert s.scalar(select(func.count()).select_from(AuditEvent))==1


def test_lock_contention_returns_sanitized_503(store):
    from sqlalchemy import event
    event.listen(store.sessions,'after_begin',lambda s,t,c:c.execute(text("SET LOCAL lock_timeout='50ms'")))
    access=SimpleNamespace(resolve_identity=lambda:store.identity,read_scope=lambda i:true(),update_scope=lambda i:true())
    client=create_app('testing',inventory_access=access,inventory_session_factory=store.sessions).test_client()
    base='/api/v1/inventory/resources/'+str(store.rids[0])+'/identifiers'
    with store.admin.begin() as gate:
        ids.address_lock(gate,'lab','10.42.0.1')
        response=client.post(base,json=dict(identifier_value='10.42.0.1',namespace='lab',row_version=1))
        assert response.status_code==503 and response.json['error']['code']=='operation_busy'
        assert 'SQL' not in response.text


def test_readonly_preflight_cli_uses_only_isolated_database(store,monkeypatch,capsys):
    import json
    from installation.__main__ import main
    with store.postgres.admin.connect() as c:sid=c.execute(text('SELECT (pg_control_system()).system_identifier::text')).scalar_one()
    settings=SimpleNamespace(values={'database':{'name':'discovery_lifecycle_test','system_identifier':sid},'roles':{'admin':'discovery_test_bootstrap'}},
                             connect=lambda role:store.postgres.admin.connect())
    monkeypatch.setattr('installation.__main__.Settings.load',lambda path:settings)
    assert main(['inspect-identifiers','--config','isolated-fixture'])==0
    assert json.loads(capsys.readouterr().out)==dict(state='COMPATIBLE',counts=dict(noncanonical_type=0,invalid_namespace=0,invalid_ipv4=0,duplicate_active=0),read_only=True)
    first=add(store)
    with store.admin.begin() as s:s.get(ResourceIdentifier,UUID(first['identifier']['id'])).identifier_type='IPv4'
    assert main(['inspect-identifiers','--config','isolated-fixture'])==78
    assert json.loads(capsys.readouterr().out)['state']=='BLOCKED'
