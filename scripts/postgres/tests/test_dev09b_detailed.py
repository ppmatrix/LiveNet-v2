"""Signed public API integration; all SQL/transport effects modelled offline.

Actual RFC8032 Ed25519 signatures and HMAC-authenticated in-process test channel.
Artifact catalogs below are SYNTHETIC fixtures, not operational declarations.
No cryptographic/layer/profile validator is patched, no approval service started.
"""
from copy import deepcopy
from dataclasses import asdict,replace
from hashlib import sha256
import hmac
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from sqlalchemy import create_engine

from scripts.dedicated.dev09b import codec as c, layers as l, physical as p, profiles
from scripts.dedicated.dev09b import migration_catalog as m, detailed_catalog as d, postgres_authority as a
from scripts.dedicated.dev09b.admission import AdmissionController
from scripts.dedicated.dev09b.doubles import MemoryClock,IndependentContinuityDouble
from scripts.dedicated.dev09b.model import AttemptState
from scripts.postgres.tests.test_dev09b_offline import fixture,uid
from scripts.postgres.tests.test_dev09b_physical import params
from scripts.postgres.tests.test_dev09b_admission import DatabaseModel

ROOT=Path(__file__).resolve().parents[3]
KEY=Ed25519PrivateKey.from_private_bytes(bytes.fromhex('9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60'))
PK=bytes.fromhex('d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a')


def properties(obj,values):obj['definition']={'properties':[dict(name=k,value=v) for k,v in sorted(values.items())]}


def signed(parts):
    payload=parts[0]
    return c.canonical(dict(payload=payload,signature_hex=KEY.sign(c.signed_bytes(payload)).hex()))


def seal_layers(parts):
    payload,target,executor,plan,semantic,physical,provenance=parts
    for phase in ('before','after'):plan['expected_'+phase+'_sha256']=l.expected_hash(semantic,physical,phase)
    payload['execution_plan_sha256']=c.digest('plan',plan)
    global_doc=dict(schema_version=1,**{k+'_sha256':c.digest(k,v) for k,v in
                    (('semantic',semantic),('physical',physical),('provenance',provenance))})
    payload['global_digest_sha256']=c.digest('global',global_doc)
    return parts


def detailed_fixture():
    payload,target,executor,plan,session=fixture()
    inputs=m.load_repository_sources(ROOT)[:-1]
    extracted=m.extract_sources(inputs,application_only=True)
    parameters=params(target,extracted);parameters['schema_version']=2
    parameters['distribution']['locale_provider']='libc'
    parameters['resolver_objects'].pop('public.alembic_security_version')
    for obj in parameters['system_objects']:
        if obj['family']=='language':properties(obj,dict(trusted=True,handler='fixture_handler',inline='fixture_inline',validator='fixture_validator'))
    for obj in parameters['btree_gist']['members']:
        properties(obj,dict(method='gist',family_schema='public',family_name='fixture_ops',input_type='uuid',key_type=None,default=False))
    for table,objs in parameters['resolver_objects'].items():
        schema,name=table.split('.')
        for obj in objs:
            values=dict(parent=table,kind='c',category='C') if obj['family']=='composite_type' else dict(parent=table,kind='b',category='A',element_schema=schema,element_name=name)
            properties(obj,values)
        # Explicit TEST resolver declarations, never names guessed for a real DB.
        for kind in ('r','i'):
            obj=m.object_record('toast',['pg_toast',schema+'_'+name,kind],{})
            properties(obj,dict(parent=table,kind=kind,persistence='p',options=None));objs.append(obj)
        objs[:]=p.sort_objects(objs)
    # Literal PG16 bootstrap facts, independently checked against the fixed BKI
    # by test_dev09b_fixed_sources; never obtained from SQL observations.
    for function in ('RI_FKey_check_ins','RI_FKey_check_upd','RI_FKey_noaction_del','RI_FKey_noaction_upd'):
        obj=m.object_record('routine',['pg_catalog',function,''],dict(returns='trigger',language='internal',body=function,
            security_definer=False,volatility='VOLATILE',strict=True,parallel='SAFE',config=[]))
        parameters['system_objects'].append(obj)
        parameters['system_ownership'].append(dict(family='routine',identity=obj['identity'],owner=parameters['roles']['database_owner']))
        parameters['system_acls'].append(dict(family='routine',identity=obj['identity'],grants=[p.grant('PUBLIC','EXECUTE')]))
    parameters['system_objects']=p.sort_objects(parameters['system_objects'])
    for key in ('system_ownership','system_acls'):parameters[key].sort(key=lambda x:(x['family'],tuple(x['identity'])))
    for row in parameters['system_acls']:
        if row['family']=='language':row['grants']=[p.grant('PUBLIC','USAGE')]
    artifact_raw=d.encode(d.artifact_projection(parameters))
    artifact=dict(path='fixtures/detailed-artifact.json',content=artifact_raw.decode(),sha256=sha256(artifact_raw).hexdigest())
    refs=[dict(path=artifact['path'],sha256=artifact['sha256'])]
    for key in ('template_sources','alembic_sources','sqlalchemy_sources'):parameters['distribution'][key]=deepcopy(refs)
    parameters['btree_gist']['sources']=deepcopy(refs)
    chain=[]
    previous=None
    for (path,raw),revision in zip(inputs,l.APP_REVISIONS):
        chain.append(dict(chain='application',revision=revision,down_revision=previous,source_path=path,source_sha256=sha256(raw).hexdigest()));previous=revision
    from scripts.postgres.tests.test_dev09b_layers import revision_state
    semantic=dict(schema_version=1,operation=payload['operation'],installation_chain=chain,
        before={ch:revision_state(ch,None) for ch in ('application','security')},
        after={ch:revision_state(ch,'f066a01a7230' if ch=='application' else None) for ch in ('application','security')})
    sources={item['source_path']:item['source_sha256'] for item in chain}
    sources.update({artifact['path']:artifact['sha256']});sources.update(profiles.DETAILED_SOURCES)
    provenance=dict(schema_version=1,producer_id='synthetic-fixture',producer_version='v2',producer_sha256='f'*64,
        source_inventory=[dict(path=k,sha256=v) for k,v in sorted(sources.items())],
        tool_inventory=[dict(name='test-artifact-resolver',version='v1',artifact_sha256=artifact['sha256'])],generation_id=uid(400))
    executor['source_inventory_sha256']=l.document_hash(provenance['source_inventory'])
    plan['executor_binding_sha256']=c.digest('executor',executor)
    plan['migration_sources_sha256']=l.document_hash(chain)
    profile=dict(profile='DEV09B-PREPARED-1',operation=payload['operation'],target_sha256=payload['target_binding_sha256'],
        bundle_sha256='e'*64,database=target['database_name'],system_identifier=target['system_identifier'],migrator=target['migrator_role'],
        schema_owners={k:parameters['roles'][k+'_owner'] for k in ('inventory','audit','security')},
        btree_gist=dict(version=parameters['btree_gist']['version'],schema='public',owner=parameters['btree_gist']['owner'],members_sha256='a'*64,acl_sha256='b'*64),
        source_inventory_sha256=executor['source_inventory_sha256'])
    raw_profile=c.canonical(profile)
    physical=dict(schema_version=2,target_binding_sha256=payload['target_binding_sha256'],
        privilege_plan_sha256=plan['privilege_plan_sha256'],exclusivity_plan_sha256=plan['exclusivity_plan_sha256'],
        parameters=parameters,artifact=artifact,migration_sources=[dict(path=path,content=raw.decode()) for path,raw in inputs],
        prepared_profile_sha256=sha256(raw_profile).hexdigest())
    for key,phase in d.PHASES.items():
        physical[key]=d.catalog_from(p.compile_profile(phase,target,parameters,inputs),profiles.validator_inventory(d.PROFILE))
    parts=seal_layers([payload,target,executor,plan,semantic,physical,provenance])
    return parts,replace(session,executor_sha256=c.digest('executor',executor)),raw_profile


def rows(snapshot,payload,session=None):
    # TEST collector converts independently held fixture observations into the
    # closed row protocol. Production normalizer takes NO expected argument.
    return dict(format='DEV09B-PHASE-ROWS-1',header={k:deepcopy(snapshot[k]) for k in d.HEADER_FIELDS},
        objects=[dict(section=section,**deepcopy(o)) for field,section in d.OBJECT_SECTIONS.items() for o in snapshot[field]],
        inventories={k:deepcopy(snapshot[k]) for k in d.LIST_SECTIONS},
        subject_session=asdict(session) if session else None,
        **{k:payload[k] if session else None for k in ('request_id','approval_id','attempt_id')})


class TestChannel:
    """Test-only authenticated channel, not an operational receipt protocol."""
    __test__=False
    key=b'public-test-key-for-offline-channel-only'
    def seal(self,value):
        body=c.canonical(value);self.latest=hmac.digest(self.key,body,'sha256')+body
        return self.latest
    def authenticate(self,raw):
        c.require(type(raw) is bytes and len(raw)>32 and hmac.compare_digest(raw[:32],hmac.digest(self.key,raw[32:],'sha256')))
        return c.parse(raw[32:])


def environment(parts,session,profile,*,unchecked_stored_bytes=False):
    payload,target,executor,plan,semantic,physical,provenance=parts
    snap=(l.ExpectationSnapshot(*(c.canonical(v,maximum_depth=32 if i==5 else 8) for i,v in enumerate(parts)))
          if unchecked_stored_bytes else l.freeze_expectations(*parts))
    db=DatabaseModel(payload,target,executor,plan)
    for key in ('payload','target','executor','plan','semantic','physical','provenance'):db.row[key]=getattr(snap,key)
    db.row['envelope']=signed(parts)
    fixed=l.document_hash(provenance)
    def key(p,control):
        c.require((p['issuer_id'],p['key_id'],p['trust_policy_version'])==('fixture-issuer','fixture-key','fixture-policy'))
        return PK
    def artifacts(s,raw):
        c.require(s.provenance==snap.provenance and l.document_hash(c.parse(s.provenance))==fixed)
        c.require(raw==profile)
    clock=MemoryClock();continuity=IndependentContinuityDouble(uid(900));continuity.block=Mock()
    channel=TestChannel()
    svc=a.PostgresConsumptionService(connections=db.connect,destination=a.AuthorityDestination('authority_dev','999','authority_service'),
        trust=SimpleNamespace(public_key=key,validate_artifacts=artifacts,authorize_record=lambda *a:None),clock=clock,continuity=continuity,channel=channel)
    def client():return a.AuthenticatedAuthorityClient(endpoint=svc,verifier=channel,payload=payload,session=session,profile_json=profile,clock=clock,continuity=continuity)
    return SimpleNamespace(db=db,snapshot=snap,service=svc,client=client,channel=channel)


@pytest.fixture(scope='module')
def fixture_data():return detailed_fixture()


def test_valid_layers_and_prepared_origin_distinct_from_entry(fixture_data):
    parts,session,profile=deepcopy(fixture_data)
    snap=l.freeze_expectations(*parts);c.validate_layers(snap)
    physical=parts[5];params=physical['parameters'];migrator=params['roles']['migrator']
    origin=physical['before']['detailed_catalog']['snapshot'];entry=physical['entry']['detailed_catalog']['snapshot']
    assert not any(a['grantee']==migrator for a in origin['public_acl'])
    assert {a['privilege'] for a in entry['public_acl'] if a['grantee']==migrator}=={'CREATE','USAGE'}
    assert not next(r for r in origin['roles'] if r['name']==migrator)['login']
    assert next(r for r in entry['roles'] if r['name']==migrator)['login']
    assert origin['ledgers']==entry['ledgers']
    for key,phase in d.PHASES.items():
        obs=rows(physical[key]['detailed_catalog']['snapshot'],parts[0],None if key=='before' else session)
        result=d.compare_observations(snap,phase,obs,session=None if key=='before' else session)
        assert result.phase==phase


def test_real_signed_public_consumption_to_transport_without_sql(fixture_data,monkeypatch):
    from migrations import dev09b_prerequisites as h
    from scripts.postgres import dev09b_application_transport as transport
    parts,session,profile=deepcopy(fixture_data);e=environment(parts,session,profile)
    original_layers=c.validate_layers;original_signature=c.verify_envelope
    # A real SQLAlchemy connection/events API with an in-memory driver, but no
    # SQL is executed: manually emit the event at the mocked Alembic boundary.
    engine=create_engine('sqlite://',hide_parameters=True);conn=engine.connect();tx=conn.begin()
    monkeypatch.setattr(conn.dialect,'name','postgresql')
    conn.connection.driver_connection.autocommit=False
    physical=parts[5];observed={'value':rows(physical['entry']['detailed_catalog']['snapshot'],parts[0],session)}
    def bound(cn,tr,ss,plan):
        assert cn is conn and tr is tx and ss==session
        phase=observed['value']['header']['phase']
        d.compare_observations(e.snapshot,phase,observed['value'],session=ss)
    def precommit(cn,tr,ss,plan):
        d.compare_observations(e.snapshot,'APP-F066-PRECOMMIT',observed['value'],session=ss)
    ctl=AdmissionController(authority=e.client(),session=session,connection=conn,transaction=tx,
        supervision=SimpleNamespace(assert_bound=bound,before_commit=precommit),plan=c.canonical(parts[3]))
    port=SimpleNamespace(assert_connection=lambda cn:c.require(cn is conn))
    context=h.PreparedContext(profile,port);called=[]
    def upgrade(config,revision,sql=False):
        assert e.db.row['state']=='CONSUMED' and revision=='f066a01a7230' and sql is False
        conn.dispatch.before_cursor_execute(conn,None,'OFFLINE_FIRST_EFFECT',{},None,False)
        called.append(revision)
        observed['value']=rows(physical['precommit']['detailed_catalog']['snapshot'],parts[0],session)
    monkeypatch.setattr(transport.command,'upgrade',upgrade)
    work=transport.ApplicationTransport(conn,tx,context)
    try:
        work.apply_once(ctl)
        assert called==['f066a01a7230'] and ctl.ready_to_commit and tx.is_active
        assert c.validate_layers is original_layers and c.verify_envelope is original_signature
        # Same public API, fresh client/nonce: durable consumed state blocks replay.
        with pytest.raises(a.AuthorityRefused):e.client().consume(parts[0]['approval_id'],session,uid(5001))
        assert len(e.db.nonces)==2  # consume + first-effect checkpoint
        assert not e.db.events  # no COMMIT/reconciliation inside transport
    finally:
        ctl.contain();engine.dispose()


@pytest.mark.parametrize('fault',['truncated','extra','grant','bool_int','binding','phase','locale','artifact','missing','security'])
def test_signed_but_invalid_contract_refused_by_public_api(fixture_data,fault):
    parts,session,profile=deepcopy(fixture_data)
    if fault=='truncated':parts[5]['after']['detailed_catalog']['snapshot']['managed_objects'].pop()
    if fault=='extra':parts[5]['after']['detailed_catalog']['snapshot']['managed_objects'].append(m.object_record('schema',['extra'],{}))
    if fault=='grant':
        grants=parts[5]['entry']['detailed_catalog']['snapshot']['database_acl']
        grants.append(p.grant(parts[5]['parameters']['roles']['migrator'],'CREATE'))
        grants.sort(key=lambda x:(x['grantee'],x['privilege']))
    if fault=='bool_int':parts[5]['entry']['detailed_catalog']['snapshot']['roles'][0]['login']=1
    if fault=='binding':parts[5]['entry']['detailed_catalog']['snapshot']['target_binding_sha256']='a'*64
    if fault=='phase':parts[5]['entry']=deepcopy(parts[5]['before'])
    if fault=='locale':parts[5]['parameters']['distribution'].pop('locale_provider')
    if fault=='artifact':parts[5]['artifact']['content']='{"opaque":"document"}'
    if fault=='missing':parts[5]['parameters']['resolver_objects'].pop('inventory.resources')
    if fault=='security':parts[4]['operation']='security-base-to-b12b01a7230'
    # Independently form correct digests/signature for INVALID stored content.
    # Do not pre-validate it in the fixture: the PUBLIC API must reject it.
    for phase in ('before','after'):parts[3]['expected_'+phase+'_sha256']=l.expected_hash(parts[4],parts[5],phase)
    parts[0]['execution_plan_sha256']=c.digest('plan',parts[3])
    domains={k:sha256(b'LiveNet/DEV09B-1/'+k.encode()+b'\0'+c.canonical(v,maximum_depth=32)).hexdigest()
             for k,v in (('semantic',parts[4]),('physical',parts[5]),('provenance',parts[6]))}
    parts[0]['global_digest_sha256']=c.digest('global',dict(schema_version=1,**{k+'_sha256':v for k,v in domains.items()}))
    e=environment(parts,session,profile,unchecked_stored_bytes=True)
    c.verify_envelope(e.db.row['envelope'],PK)  # cryptographically VALID negative fixture
    with pytest.raises(a.AuthorityRefused):e.client().consume(parts[0]['approval_id'],session,uid(5000))
    assert e.db.row['state']=='AVAILABLE'


@pytest.mark.parametrize('fault',['truncated','extra','grant','session','duplicate','wrong_format'])
def test_observation_normalization_refuses_incomplete_or_divergent_rows(fixture_data,fault):
    parts,session,profile=deepcopy(fixture_data);snap=l.freeze_expectations(*parts)
    obs=rows(parts[5]['entry']['detailed_catalog']['snapshot'],parts[0],session)
    if fault=='truncated':obs['objects'].pop()
    if fault=='extra':obs['objects'].append(dict(section='managed',**m.object_record('schema',['extra'],{})))
    if fault=='grant':obs['inventories']['database_acl'].append(p.grant('PUBLIC','CREATE'))
    if fault=='session':obs['subject_session']['backend_pid']+=1
    if fault=='duplicate':obs['objects'].append(deepcopy(obs['objects'][0]))
    if fault=='wrong_format':obs['format']='raw-query-rows'
    with pytest.raises(c.Invalid):d.compare_observations(snap,'APP-ENTRY',obs,session=session)


def test_old_profiles_and_security_remain_unsupported(fixture_data):
    parts,session,profile=fixture_data;snap=l.freeze_expectations(*parts)
    for old in (*profiles.PROFILES,*profiles.PREPARED_PROFILES):
        with pytest.raises(c.Unsupported):profiles.require_complete_profile(old,snapshot=snap)
    with pytest.raises(c.Unsupported):profiles.require_complete_profile(d.PROFILE)
    with pytest.raises(c.Unsupported):p.compile_profile('SEC-B12-PRECOMMIT',parts[1],parts[5]['parameters'],tuple((x['path'],x['content'].encode()) for x in parts[5]['migration_sources']))


@pytest.mark.parametrize('field',['locale_provider','template_name'])
def test_missing_distribution_parameter_identifies_path(fixture_data,field):
    parts,session,profile=deepcopy(fixture_data);parts[5]['parameters']['distribution'].pop(field)
    with pytest.raises(m.MissingParameter,match='target_profile.distribution.'+field):
        d.validate_contract(parts[5],parts[1],parts[4],parts[6])


def test_missing_resolver_identifies_table(fixture_data):
    parts,session,profile=deepcopy(fixture_data);parts[5]['parameters']['resolver_objects'].pop('inventory.resources')
    with pytest.raises(m.MissingParameter,match='target_profile.resolver_objects.inventory.resources'):
        d.validate_contract(parts[5],parts[1],parts[4],parts[6])


def test_observation_order_normalizes_without_losing_duplicates(fixture_data):
    parts,session,profile=fixture_data;snap=l.freeze_expectations(*parts)
    obs=rows(parts[5]['entry']['detailed_catalog']['snapshot'],parts[0],session)
    obs['objects'].reverse()
    for values in obs['inventories'].values():values.reverse()
    assert d.compare_observations(snap,'APP-ENTRY',obs,session=session).phase=='APP-ENTRY'


def test_actual_signature_tampering_refused_before_consumption(fixture_data):
    parts,session,profile=deepcopy(fixture_data);e=environment(parts,session,profile)
    env=c.parse(e.db.row['envelope']);env['payload']['executor_id']='different-executor'
    e.db.row['envelope']=c.canonical(env)
    with pytest.raises(a.AuthorityRefused):e.client().consume(parts[0]['approval_id'],session,uid(6000))
    assert e.db.row['state']=='AVAILABLE'


def test_client_authentication_tampering_does_not_release_consumption(fixture_data):
    parts,session,profile=deepcopy(fixture_data);e=environment(parts,session,profile)
    client=e.client()
    assert client.consume(parts[0]['approval_id'],session,uid(6000)).attempt_id==parts[0]['attempt_id']
    raw=e.channel.latest
    assert e.channel.authenticate(raw)['nonce']==uid(6000)  # same bytes succeed first
    with pytest.raises(c.Invalid):e.channel.authenticate(raw[:-1]+b'X')
    assert e.db.row['state']=='CONSUMED'


def test_opaque_artifact_hash_is_insufficient(fixture_data):
    parts,session,profile=deepcopy(fixture_data)
    # Coincident digest/projection of an incomplete opclass still must refuse.
    obj=parts[5]['parameters']['btree_gist']['members'][0]
    properties(obj,dict(method='gist'))
    raw=d.encode(d.artifact_projection(parts[5]['parameters']))
    artifact=parts[5]['artifact'];old=artifact['sha256']
    artifact.update(content=raw.decode(),sha256=sha256(raw).hexdigest())
    for s in parts[6]['source_inventory']:
        if s['path']==artifact['path']:s['sha256']=artifact['sha256']
    for refs in [*(parts[5]['parameters']['distribution'][k] for k in ('template_sources','alembic_sources','sqlalchemy_sources')),parts[5]['parameters']['btree_gist']['sources']]:
        for ref in refs:
            if ref['sha256']==old:ref['sha256']=artifact['sha256']
    with pytest.raises(m.MissingParameter,match='artifact.opclass.'):
        d.validate_contract(parts[5],parts[1],parts[4],parts[6])


@pytest.mark.parametrize('fault',['clock','revocation','continuity','trust'])
def test_structural_cache_never_caches_eligibility(fixture_data,fault):
    from scripts.dedicated.dev09b.model import TimeSample,ContinuitySample
    parts,session,profile=deepcopy(fixture_data);e=environment(parts,session,profile)
    c.validate_layers(e.snapshot)  # warm pure structural cache before loss of eligibility
    if fault=='clock':e.service.clock.value=TimeSample(200,200,True)
    if fault=='revocation':e.db.row['revoked']=True
    if fault=='continuity':e.service.continuity.value=ContinuitySample(uid(900),False)
    if fault=='trust':e.service.trust.public_key=lambda *a:(_ for _ in ()).throw(c.Invalid('revoked key'))
    with pytest.raises(c.Invalid):e.client().consume(parts[0]['approval_id'],session,uid(6500))
    assert e.db.row['state']!='CONSUMED'


def test_artifact_provenance_is_required_independently_of_matching_content(fixture_data):
    parts,session,profile=deepcopy(fixture_data)
    parts[6]['source_inventory']=[s for s in parts[6]['source_inventory'] if s['path']!=parts[5]['artifact']['path']]
    with pytest.raises(c.Invalid):d.validate_contract(parts[5],parts[1],parts[4],parts[6])
