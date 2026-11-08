"""Constructed PG16 SQL-result fixtures, NOT verified historical captures.

Literal driver-facing rows test conversion independently of PHASE-ROWS output.
Real SQLAlchemy Row/RowMapping objects are built from result metadata without
creating an engine, connection, socket or executing any SQL.
"""
from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from sqlalchemy.engine.row import Row
from sqlalchemy.engine.result import SimpleResultMetaData

from migrations import dev09b_inspection as ins,dev09b_catalog_adapter as a
from migrations.dev09b_inspection_queries import QUERIES
from migrations.dev09b_detailed_queries import DETAIL_QUERIES
from scripts.dedicated.dev09b import detailed_catalog as d,codec as c
from scripts.dedicated.dev09b.model import SessionBinding

ADMIN='fixture_admin';OWNER='fixture_database_owner';INSPECTOR='lnv2_dev_inspector';MIGRATOR='lnv2_dev_migrator'


def driver_row(value,mapping=False):
    metadata=SimpleResultMetaData(list(value))
    row=Row(metadata,None,metadata._key_to_index,tuple(value.values()))
    return row._mapping if mapping else row


def identity_link(family,schema,name,identify_type,identify_identity,arguments='',relation='',direct_namespace=False):
    return dict(family=family,schema=schema,name=name,arguments=arguments,relation=relation,
                identify_type=identify_type,identify_identity=identify_identity,direct_namespace=direct_namespace)


def sql_fixture():
    raw={name:[] for name in QUERIES};extra={name:[] for name in DETAIL_QUERIES}
    raw['identity']=[dict(database='livenet_v2_dev',current_user=INSPECTOR,session_user=INSPECTOR,system_identifier='123',pid=42,
        backend_start='2026-11-07 10:00:00+00',xact_start='2026-11-07 10:01:00+00',virtualxid='4/12',address='172.20.0.2',port=5432,server_version_num=160015)]
    raw['privileges']=[{key:False for key in QUERIES['privileges'].fields}]
    raw['memberships']=[dict(role=ADMIN,member=False,inherited=False,can_set=False)]
    for name,owner in [('inventory','fixture_inventory_owner'),('audit','fixture_audit_owner'),('security','fixture_security_owner'),('public','pg_database_owner')]:
        raw['schemas'].append(dict(name=name,owner=owner,owner_login=False,can_create=False,can_use=False,grant_create=False,grant_use=False))
    next(r for r in raw['schemas'] if r['name']=='public')['can_use']=True
    raw['schema_acl']=[dict(name='public',grantor='pg_database_owner',grantee='PUBLIC',privilege='USAGE',grant_option=False)]
    for schema in raw['schemas']:
        raw['schema_acl'] += [dict(name=schema['name'],grantor=schema['owner'],grantee=schema['owner'],privilege=k,grant_option=False) for k in ('CREATE','USAGE')]
    raw['database_acl']=[dict(name='livenet_v2_dev',owner=OWNER,grantor=OWNER,grantee=who,privilege='CONNECT',grant_option=False) for who in (ADMIN,'fixture_recovery',INSPECTOR,MIGRATOR)]
    raw['extension']=[dict(name='plpgsql',version='1.0',schema='pg_catalog',owner=OWNER),dict(name='btree_gist',version='1.7',schema='public',owner=OWNER)]
    raw['extension_members']=[dict(extension='plpgsql',type='language',schema=None,name='plpgsql',identity='plpgsql',subid=0),
        dict(extension='btree_gist',type='operator class',schema='public',name='fixture_uuid_ops',identity='public.fixture_uuid_ops USING gist',subid=0)]
    opclass=dict(opcmethod=783,opcname='fixture_uuid_ops',opcnamespace=2200,opcowner=10,opcfamily=6000,opcintype=2950,opcdefault=False,opckeytype=0)
    raw['extension_properties']=[dict(extension='plpgsql',identity='plpgsql',catalog='pg_catalog.pg_language',properties=None),
        dict(extension='btree_gist',identity='public.fixture_uuid_ops USING gist',catalog='pg_catalog.pg_opclass',properties=opclass)]
    raw['namespace_objects']=[dict(schema='public',type='operator class',identity='public.fixture_uuid_ops USING gist'),dict(schema='public',type='extension',identity='btree_gist')]
    extra['object_identities']=[identity_link('opclass','public','fixture_uuid_ops','operator class','public.fixture_uuid_ops USING gist',direct_namespace=True),
        identity_link('extension','public','btree_gist','extension','btree_gist',direct_namespace=True),
        identity_link('extension','pg_catalog','plpgsql','extension','plpgsql',direct_namespace=True),
        identity_link('language','','plpgsql','language','plpgsql'),
        identity_link('routine','pg_catalog','pg_control_system','function','pg_catalog.pg_control_system()')]
    settings=dict(search_path='public',session_replication_role='origin',row_security='on',standard_conforming_strings='on',
        shared_preload_libraries='',session_preload_libraries='',local_preload_libraries='',server_encoding='UTF8',lc_collate='en_US.utf8',lc_ctype='en_US.utf8',transaction_isolation='read committed',transaction_read_only='on')
    raw['settings']=[dict(name=k,setting=v) for k,v in settings.items()]
    extra['own_preload_settings']=[dict(name=k,setting='') for k in ('shared_preload_libraries','session_preload_libraries')]
    extra['environment']=[dict(database='livenet_v2_dev',encoding='UTF8',collation='en_US.utf8',ctype='en_US.utf8',locale_provider='c',owner=OWNER)]
    names=[ADMIN,OWNER,'fixture_recovery',INSPECTOR,MIGRATOR,'fixture_inventory_owner','fixture_audit_owner','fixture_security_owner','fixture_application_ledger_owner','fixture_security_ledger_owner','fixture_runtime']
    extra['role_details']=[dict(name=name,login=name in (ADMIN,'fixture_recovery',INSPECTOR),superuser=name in (ADMIN,'fixture_recovery'),createdb=False,createrole=False,replication=False,bypassrls=False,inherit=False) for name in names]
    extra['language_details']=[dict(name='plpgsql',trusted=True,handler='plpgsql_call_handler()',inline='plpgsql_inline_handler(internal)',validator='plpgsql_validator(oid)',owner=OWNER)]
    extra['routine_semantics']=[dict(schema='pg_catalog',name='pg_control_system',arguments='',returns='record',language='internal',body='pg_control_system',volatility='v',strict=False,parallel='u',security_definer=False,config=None,owner=OWNER)]
    extra['system_acl']=[dict(family='routine',schema='pg_catalog',name='pg_control_system',arguments='',owner=OWNER,grantor=OWNER,grantee=INSPECTOR,privilege='EXECUTE',grant_option=False)]
    extra['system_acl'].append({**extra['system_acl'][0],'grantee':OWNER})
    extra['system_acl'] += [dict(family='language',schema='',name='plpgsql',arguments='',owner=OWNER,grantor=OWNER,grantee=who,privilege='USAGE',grant_option=False) for who in (OWNER,'PUBLIC')]
    extra['reference_catalog']=[dict(catalog=cat,oid=oid,schema=schema,name=name,display=display) for cat,oid,schema,name,display in [
        ('pg_am',783,'','gist','gist'),('pg_namespace',2200,'','public','public'),('pg_roles',10,'',OWNER,OWNER),
        ('pg_opfamily',6000,'public','fixture_ops','public.fixture_ops USING gist'),('pg_type',2950,'pg_catalog','uuid','uuid')]]
    for function in ('RI_FKey_check_ins','RI_FKey_check_upd','RI_FKey_noaction_del','RI_FKey_noaction_upd'):
        extra['routine_semantics'].append(dict(schema='pg_catalog',name=function,arguments='',returns='trigger',language='internal',body=function,volatility='v',strict=True,parallel='s',security_definer=False,config=None,owner=OWNER))
        extra['system_acl'] += [dict(family='routine',schema='pg_catalog',name=function,arguments='',owner=OWNER,grantor=OWNER,grantee=who,privilege='EXECUTE',grant_option=False) for who in (OWNER,'PUBLIC')]
        extra['object_identities'].append(identity_link('routine','pg_catalog',function,'function','pg_catalog.'+function+'()'))
    src=[dict(path='fixtures/source-declared-distribution.json',sha256='a'*64)]
    context=dict(metadata=dict(target_binding_sha256='1'*64,parameters_sha256='2'*64,sources=src,image_sha256='3'*64,template_name='template0',
        distribution_sources={k:src for k in ('template_sources','alembic_sources','sqlalchemy_sources')},extension_sources=src,
        role_bindings=dict(migrator=MIGRATOR,inspector=INSPECTOR),request_id=None,approval_id=None,attempt_id=None),
        fixed_properties={},deparse=dict(constraints=[],indexes=[],index_columns=[],routines=[],triggers=[]),implicit_objects=[])
    # A fixed SOURCE declaration (literal symbolic references), independently
    # authored rather than obtained by calling the adapter under test.
    symbolic=dict(opclass)
    symbolic.update(opcmethod=dict(schema='',name='gist',display='gist'),opcnamespace=dict(schema='',name='public',display='public'),
        opcowner=dict(schema='',name=OWNER,display=OWNER),opcfamily=dict(schema='public',name='fixture_ops',display='public.fixture_ops USING gist'),
        opcintype=dict(schema='pg_catalog',name='uuid',display='uuid'),opckeytype=None)
    context['fixed_properties']=dict(session_settings=dict(transaction_isolation='read committed',transaction_read_only='on'),template_extensions=[dict(name='plpgsql',version='1.0',schema='pg_catalog',owner=OWNER)],type_details=[],operator_members=[],extension_properties=[
        dict(extension='btree_gist',identity='public.fixture_uuid_ops USING gist',catalog='pg_catalog.pg_opclass',properties=symbolic),
        dict(extension='plpgsql',identity='plpgsql',catalog='pg_catalog.pg_language',properties=None)])
    for name in a.PROPERTY_QUERIES:context['fixed_properties'][name].sort(key=d.encode)
    return raw,extra,context


def convert(raw,extra,ctx):
    return a.convert_results(raw,extra,ctx,phase='DEV-BASE',collector_id='constructed-pg16-fixture',ledger_rows={'application':None,'security':None})


@pytest.fixture(autouse=True)
def no_external(monkeypatch):
    import socket,subprocess
    denied=Mock(side_effect=AssertionError('offline-only'))
    for owner,name in ((socket,'socket'),(socket,'create_connection'),(subprocess,'run'),(subprocess,'Popen')):monkeypatch.setattr(owner,name,denied)


def test_literal_pg_results_to_typed_phase_rows():
    raw,extra,ctx=sql_fixture();result=convert(raw,extra,ctx);value=d.parse(result.rows_json)
    normalized=d.normalize_observations(value)
    assert normalized['distribution']['locale_provider']=='libc'
    assert normalized['public_owner']=='pg_database_owner'
    assert {tuple(o['identity']) for o in normalized['managed_objects']}=={('inventory',),('audit',),('security',)}
    assert normalized['ledgers']==[dict(chain='application',presence='ABSENT',revisions=[]),dict(chain='security',presence='ABSENT',revisions=[])]
    opclass=normalized['extensions'][0]['members'][0]
    assert opclass['family']=='opclass' and opclass['identity']==['public','fixture_uuid_ops']
    assert dict((p['name'],p['value']) for p in opclass['definition']['properties'])==dict(default=False,family_name='fixture_ops',family_schema='public',input_type='uuid',key_type=None,method='gist')
    assert not hasattr(result,'authorize')


@pytest.mark.parametrize('mapping',[False,True])
def test_actual_sqlalchemy_row_and_rowmapping(mapping):
    raw,extra,ctx=sql_fixture()
    raw={k:[driver_row(r,mapping) for r in values] for k,values in raw.items()}
    extra={k:[driver_row(r,mapping) for r in values] for k,values in extra.items()}
    assert d.parse(convert(raw,extra,ctx).rows_json)['format']=='DEV09B-PHASE-ROWS-1'


@pytest.mark.parametrize('fault',['missing_query','extra_query','missing_supplement','duplicate','duplicate_identity','bool','null_setting','unresolved','extra_object','nonempty_family','fixed_property','missing_property','default_acl'])
def test_complete_coverage_and_refusals(fault):
    raw,extra,ctx=sql_fixture()
    if fault=='missing_query':raw.pop('rules')
    if fault=='extra_query':raw['unknown']=[]
    if fault=='missing_supplement':extra.pop('environment')
    if fault=='duplicate':raw['schemas'].append(deepcopy(raw['schemas'][0]))
    if fault=='duplicate_identity':raw['schemas'].append({**raw['schemas'][0],'owner':'other'})
    if fault=='bool':raw['privileges'][0]['superuser']=0
    if fault=='null_setting':raw['settings'][0]['setting']=None
    if fault=='unresolved':extra['reference_catalog'].pop()
    if fault=='extra_object':raw['namespace_objects'].append(dict(schema='inventory',type='function',identity='inventory.extra()'))
    if fault=='nonempty_family':raw['rules']=[dict(schema='inventory',relation='resources',name='unexpected',definition='unsafe')]
    if fault=='fixed_property':next(r for r in ctx['fixed_properties']['extension_properties'] if r['properties'] is not None)['properties']['opcdefault']=True
    if fault=='missing_property':raw['extension_properties'][1]['properties'].pop('opcdefault')
    if fault=='default_acl':raw['default_acl_objects']=[dict(owner=ADMIN,schema='public',kind='r',entries=0)]
    with pytest.raises((c.Invalid,ins.h.PrerequisiteRefused)):convert(raw,extra,ctx)


def test_all_queries_have_explicit_matrix_consumers():
    assert set(a.MATRIX)==set(QUERIES)
    assert len(a.MATRIX)==33
    assert a.ABSENT and all('absence' in a.MATRIX[k] for k in a.ABSENT)


@pytest.mark.parametrize('raw,expected', [('integer',dict(name='sa.Integer',arguments=[])),('character varying(32)',dict(name='sa.String',arguments=[32])),('numeric(5,4)',dict(name='sa.Numeric',arguments=[5,4]))])
def test_independent_sql_type_examples(raw,expected):assert a.data_type(raw)==expected


def test_unknown_deparse_and_type_never_get_guessed():
    with pytest.raises(c.Unsupported):a.data_type('custom_extension_type')
    with pytest.raises(c.Unsupported):a.default("malicious_function()")


class ResultDouble:
    def __init__(self,values,mapping):self.values=values;self.mapping=mapping;self.closed=False
    def mappings(self):
        for value in self.values:yield driver_row(value,self.mapping)
    def close(self):self.closed=True


def connection_fixture(raw,extra,*,mapping=True,identity_change=False,transaction_change=False):
    tx=SimpleNamespace(is_active=True);results=[];calls=[];identity_count=[0]
    conn=SimpleNamespace(closed=False,dialect=SimpleNamespace(name='postgresql'),_echo=False,
        engine=SimpleNamespace(echo=False,hide_parameters=True,logger=SimpleNamespace(isEnabledFor=lambda level:False)),
        in_transaction=lambda:True,get_transaction=lambda:tx)
    registry={q.sql:('old',name) for name,q in QUERIES.items()}
    registry.update({q.sql:('detail',name) for name,q in DETAIL_QUERIES.items()})
    def execute(sql,parameters):
        kind,name=registry[str(sql)];calls.append((kind,name,parameters))
        data=deepcopy(raw[name] if kind=='old' else extra[name])
        if name=='identity':
            identity_count[0]+=1
            if identity_count[0]==2:
                if identity_change:data[0]['pid']+=1
                if transaction_change:conn.get_transaction=lambda:SimpleNamespace(is_active=True)
        result=ResultDouble(data,mapping);results.append(result);return result
    conn.execute=execute
    return conn,tx,results,calls


@pytest.mark.parametrize('mapping',[False,True])
def test_real_port_collection_preserves_connection_transaction_and_identity(mapping):
    raw,extra,ctx=sql_fixture();conn,tx,results,calls=connection_fixture(raw,extra,mapping=mapping)
    batch=ins.collect_detailed_sql(conn,tx,collector_id='constructed-fixture',role_names=[r['name'] for r in extra['role_details']],
        system_routines=['pg_catalog.pg_control_system'],language_names=['plpgsql'])
    assert len(calls)==len(QUERIES)+len(DETAIL_QUERIES)  # optional helper is not called without a declaration
    assert not any(name=='helper_preload_settings' for kind,name,parameters in calls)
    assert calls[0][1]==calls[-1][1]=='identity' and all(r.closed for r in results)
    converted=a.convert_results(batch.historical,batch.supplemental,ctx,phase='DEV-BASE',collector_id=batch.collector_id,ledger_rows=batch.ledger_rows)
    assert converted.collector_binding_json==c.canonical(raw['identity'][0])
    assert conn.get_transaction() is tx and not conn.closed and tx.is_active
    # OIDs are partitioned by catalog, not broad numeric probes of other objects.
    params=next(parameters for kind,name,parameters in calls if name=='reference_catalog')
    assert params['reference_pg_roles']==[10] and params['reference_pg_type']==[2950]


@pytest.mark.parametrize('fault',['identity','transaction'])
def test_real_port_refuses_collector_changes_and_closes_results(fault):
    raw,extra,ctx=sql_fixture();conn,tx,results,calls=connection_fixture(raw,extra,identity_change=fault=='identity',transaction_change=fault=='transaction')
    with pytest.raises(ins.h.PrerequisiteRefused):ins.collect_detailed_sql(conn,tx,collector_id='constructed-fixture',
        role_names=[r['name'] for r in extra['role_details']],system_routines=['pg_catalog.pg_control_system'],language_names=['plpgsql'])
    assert all(r.closed for r in results)


def test_missing_approval_never_queries_in_real_port():
    raw,extra,ctx=sql_fixture();conn,tx,results,calls=connection_fixture(raw,extra)
    # The old port's mandatory binding checks must precede queries on the new API.
    port=ins.PreparedInspectionPort(conn,tx)
    # Invalid layer object is refused even before any trusted verification/query.
    with pytest.raises(c.Invalid):port.observe_detailed(b'{}',None,phase='DEV-BASE')
    assert not calls and port._failed


def detailed_port_fixture(tmp_path):
    """Source-defined expectations and literal SQL observations, independently built."""
    from hashlib import sha256
    from scripts.postgres.tests.test_dev09b_detailed import detailed_fixture,seal_layers
    from scripts.dedicated.dev09b import physical as physical,layers,profiles
    parts,session,profile=detailed_fixture();raw,extra,ctx=sql_fixture()
    parameters=parts[5]['parameters']
    parameters['btree_gist']['version']='1.7'
    parameters['distribution'].update(template_name='template0',collation='en_US.utf8',ctype='en_US.utf8')
    for obj in parameters['system_objects']:
        if obj['family']=='language':
            values=dict(trusted=True,handler='plpgsql_call_handler()',inline='plpgsql_inline_handler(internal)',validator='plpgsql_validator(oid)')
            obj['definition']={'properties':[dict(name=k,value=v) for k,v in sorted(values.items())]}
        elif obj['identity']==['pg_catalog','pg_control_system','']:obj['definition'].update(body='pg_control_system',volatility='VOLATILE')
    artifact=parts[5]['artifact'];old=artifact['sha256'];body=d.encode(d.artifact_projection(parameters))
    artifact.update(content=body.decode(),sha256=sha256(body).hexdigest())
    for field in ('template_sources','alembic_sources','sqlalchemy_sources'):
        for ref in parameters['distribution'][field]:ref['sha256']=artifact['sha256']
    for ref in parameters['btree_gist']['sources']:ref['sha256']=artifact['sha256']
    for ref in parts[6]['source_inventory']:
        if ref['path']==artifact['path']:ref['sha256']=artifact['sha256']
    inputs=tuple((x['path'],x['content'].encode()) for x in parts[5]['migration_sources'])
    ctx['metadata'].update(target_binding_sha256=parts[0]['target_binding_sha256'],parameters_sha256=layers.document_hash(parameters),
        sources=[dict(path=path,sha256=sha256(content).hexdigest()) for path,content in sorted(inputs)],
        image_sha256=parts[1]['image_sha256'],extension_sources=deepcopy(parameters['btree_gist']['sources']),
        distribution_sources={k:deepcopy(parameters['distribution'][k]) for k in ('template_sources','alembic_sources','sqlalchemy_sources')})
    source=dict(path='fixtures/conversion-declarations.json',sha256=sha256(d.encode(ctx)).hexdigest())
    parts[6]['source_inventory'].append(source);parts[6]['source_inventory'].sort(key=lambda r:r['path'])
    parts[2]['source_inventory_sha256']=layers.document_hash(parts[6]['source_inventory'])
    parts[3]['executor_binding_sha256']=c.digest('executor',parts[2])
    profile_obj=c.parse(profile);profile_obj['btree_gist']['version']='1.7';profile_obj['source_inventory_sha256']=parts[2]['source_inventory_sha256'];profile=c.canonical(profile_obj)
    parts[5]['prepared_profile_sha256']=sha256(profile).hexdigest()
    for key,phase in d.PHASES.items():parts[5][key]=d.catalog_from(physical.compile_profile(phase,parts[1],parameters,inputs),profiles.validator_inventory(d.PROFILE))
    seal_layers(parts);snapshot=layers.freeze_expectations(*parts);c.validate_layers(snapshot)
    material={path:content for path,content in inputs}
    material[artifact['path']]=artifact['content'].encode();material[source['path']]=d.encode(ctx)
    root=Path(__file__).resolve().parents[3]
    for name in profiles.DETAILED_SOURCES:material[name]=(root/name).read_bytes()
    for name,content in material.items():
        path=tmp_path/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(content)
    inventory={**QUERIES,**{'detail.'+k:v for k,v in DETAIL_QUERIES.items()}}
    contract=dict(schema_version=2,profile_sha256=sha256(profile).hexdigest(),snapshot_sha256=sha256(snapshot.physical).hexdigest(),
        query_inventory_sha256=sha256(d.encode({k:dict(sql=q.sql,fields=list(q.fields),maximum=q.maximum) for k,q in inventory.items()})).hexdigest(),
        binding=raw['identity'][0],collector_id='constructed-fixture',context=ctx,conversion_source=source,subject_session=None,
        selections=dict(role_names=[r['name'] for r in extra['role_details']],system_routines=['pg_catalog.pg_control_system'],language_names=['plpgsql']))
    return raw,extra,ctx,snapshot,profile,d.encode(contract)


def test_real_inspection_port_normalizes_and_compares_signed_detailed_layers(tmp_path):
    from hashlib import sha256
    raw,extra,ctx,snapshot,profile,contract_raw=detailed_port_fixture(tmp_path)
    conn,tx,results,calls=connection_fixture(raw,extra)
    contract=d.parse(contract_raw);p=c.parse(profile)
    # Trusted verifier DOUBLE, not operational approval or historical capture.
    verifier=SimpleNamespace(verify=lambda pjson,cjson:ins.InspectionApproval(
        ins.h.ProfileAttestation(sha256(profile).hexdigest(),p['target_sha256'],p['bundle_sha256'],True,'OPERATIONAL'),
        sha256(contract_raw).hexdigest(),ins.digest(contract['binding']),'OFFLINE-TEST-DOUBLE'))
    port=ins.PreparedInspectionPort(conn,tx,profile_verifier=verifier,contract_json=contract_raw,source_root=tmp_path)
    observation=port.observe_detailed(profile,snapshot,phase='DEV-BASE')
    assert observation.collector_id=='constructed-fixture' and observation.collector_binding_json==c.canonical(raw['identity'][0])
    assert not port._failed and conn.get_transaction() is tx and all(r.closed for r in results)


def table_sql_fixture():
    raw,extra,ctx=sql_fixture()
    def relation(name,kind):return dict(schema='inventory',name=name,kind=kind,owner=MIGRATOR,persistence='p',row_security=False,force_row_security=False,options=None,partition_bound=None,view=None)
    raw['relations']=[relation('demo','r'),relation('demo_pkey','i')]
    raw['columns']=[dict(schema='inventory',relation='demo',name='id',position=1,type='integer',not_null=True,identity='',generated='',default=None),
                    dict(schema='inventory',relation='demo_pkey',name='id',position=1,type='integer',not_null=False,identity='',generated='',default=None)]
    raw['constraints']=[dict(schema='inventory',name='demo_pkey',relation='inventory.demo',kind='p',validated=True,deferrable=False,initially_deferred=False,definition='PRIMARY KEY (id)')]
    raw['indexes']=[dict(schema='inventory',name='demo_pkey',definition='CREATE UNIQUE INDEX demo_pkey ON inventory.demo USING btree (id)',valid=True,ready=True,live=True)]
    ctx['deparse']['constraints']=[dict(schema='inventory',name='demo_pkey',sql='PRIMARY KEY (id)',identity=['inventory','demo','demo_pkey'],
        definition=dict(kind='p',columns=['id'],references=[],expression=None,operators=[],using=None,predicate=None,validated=True,deferrable=False,initially_deferred=False))]
    ctx['deparse']['indexes']=[dict(schema='inventory',name='demo_pkey',sql='CREATE UNIQUE INDEX demo_pkey ON inventory.demo USING btree (id)',identity=['inventory','demo_pkey'],
        definition=dict(table='demo',columns=['id'],unique=True,primary=True,method='btree',predicate=None,constraint='demo_pkey',valid=True,ready=True))]
    ctx['deparse']['index_columns']=[dict(schema='inventory',relation='demo_pkey',name='id',position=1,type='integer',not_null=False,identity='',generated='',default=None)]
    extra['relation_types']=[dict(schema='inventory',relation='demo',relation_oid=99,type_oid=100,row_type='demo',array_oid=101,array_type='_demo')]
    props=dict(typname='demo',typnamespace=7000,typowner=20,typlen=-1,typbyval=False,typtype='c',typcategory='C',typispreferred=False,typisdefined=True,
        typdelim=',',typrelid=99,typsubscript='-',typelem=0,typarray=101,typinput='record_in',typoutput='record_out',typreceive='record_recv',typsend='record_send',
        typmodin='-',typmodout='-',typanalyze='-',typalign='d',typstorage='x',typnotnull=False,typbasetype=0,typtypmod=-1,typndims=0,typcollation=0,typdefaultbin=None,typdefault=None,typacl=None)
    array={**props,'typname':'_demo','typtype':'b','typcategory':'A','typrelid':0,'typelem':100,'typarray':0,'typinput':'array_in','typoutput':'array_out','typreceive':'array_recv','typsend':'array_send'}
    raw['types']=[dict(schema='inventory',name='demo',owner=MIGRATOR,kind='c',category='C',not_null=False,default=None,base='-',element='-'),
                  dict(schema='inventory',name='_demo',owner=MIGRATOR,kind='b',category='A',not_null=False,default=None,base='-',element='inventory.demo')]
    raw['type_details']=[dict(schema='inventory',name='demo',properties=props),dict(schema='inventory',name='_demo',properties=array)]
    refs=[dict(catalog=cat,oid=oid,schema=schema,name=name,display=display) for cat,oid,schema,name,display in [
        ('pg_namespace',7000,'','inventory','inventory'),('pg_roles',20,'',MIGRATOR,MIGRATOR),('pg_class',99,'inventory','demo','inventory.demo'),
        ('pg_type',100,'inventory','demo','inventory.demo'),('pg_type',101,'inventory','_demo','inventory.demo[]')]]
    extra['reference_catalog']+=refs
    # Independent fixed-source property declarations use named references. They
    # do not call resolved_properties() or normalize_observations() to generate expectations.
    symbolic={key:dict(schema=schema,name=name,display=display) for key,schema,name,display in [
        ('typnamespace','','inventory','inventory'),('typowner','',MIGRATOR,MIGRATOR),('typrelid','inventory','demo','inventory.demo'),('typarray','inventory','_demo','inventory.demo[]')]}
    fixed_row={**props,**symbolic,'typelem':None,'typbasetype':None,'typcollation':None}
    fixed_array={**array,'typnamespace':symbolic['typnamespace'],'typowner':symbolic['typowner'],'typrelid':None,'typarray':None,
        'typelem':dict(schema='inventory',name='demo',display='inventory.demo'),'typbasetype':None,'typcollation':None}
    ctx['fixed_properties']['type_details']=sorted([dict(schema='inventory',name='demo',properties=fixed_row),dict(schema='inventory',name='_demo',properties=fixed_array)],key=d.encode)
    for relation in ('demo','demo_pkey'):
        raw['object_acl'] += [dict(family='relation',schema='inventory',name=relation,grantor=MIGRATOR,grantee=MIGRATOR,privilege=k,grant_option=False) for k in ('SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER')]
    for typename in ('demo','_demo'):
        raw['object_acl'] += [dict(family='type',schema='inventory',name=typename,grantor=MIGRATOR,grantee=MIGRATOR,privilege='USAGE',grant_option=False)]
    raw['namespace_objects'].append(dict(schema='inventory',type='table',identity='inventory.demo'))
    extra['object_identities'] += [identity_link('relation','inventory','demo','table','inventory.demo',direct_namespace=True),
        identity_link('relation','inventory','demo_pkey','index','inventory.demo_pkey'),
        identity_link('type','inventory','demo','type','inventory.demo'),identity_link('type','inventory','_demo','type','inventory._demo'),
        identity_link('constraint','inventory','demo_pkey','table constraint','demo_pkey on inventory.demo',relation='demo')]
    return raw,extra,ctx


def test_constructed_table_columns_pk_and_index_sql_are_not_roundtrip():
    raw,extra,ctx=table_sql_fixture()
    result=d.normalize_observations(d.parse(convert(raw,extra,ctx).rows_json))
    column=next(o for o in result['managed_objects'] if o['family']=='column')
    assert column['identity']==['inventory','demo','id'] and column['definition']==dict(position=1,type=dict(name='sa.Integer',arguments=[]),nullable=False,default=None,identity='',generated='')
    assert next(o for o in result['managed_objects'] if o['family']=='index')['definition']['primary'] is True
    assert {o['family'] for o in result['managed_objects']}=={'schema','table','column','constraint','index','composite_type','array_type'}
    # Divergent raw parent is refused, not replaced by the source declaration.
    raw['constraints'][0]['relation']='inventory.other'
    with pytest.raises(ins.h.PrerequisiteRefused,match='CONSTRAINT_PARENT_IDENTITY'):convert(raw,extra,ctx)


def test_unlinked_internal_trigger_is_explicitly_refused():
    raw,extra,ctx=sql_fixture()
    raw['triggers']=[dict(schema='inventory',relation='demo',name='RI_ConstraintTrigger_fixture',enabled='O',internal=True,definition='CONSTRUCTED INTERNAL TRIGGER')]
    extra['trigger_semantics']=[dict(schema='inventory',relation='demo',name='RI_ConstraintTrigger_fixture',timing='AFTER',events=['INSERT'],row=True,
        function_schema='pg_catalog',function_name='RI_FKey_check_ins',function_arguments='',enabled='O',internal=True)]
    ctx['deparse']['triggers']=[]
    with pytest.raises(ins.h.PrerequisiteRefused,match='FK_LINK_COVERAGE'):convert(raw,extra,ctx)


@pytest.mark.parametrize('fault',['property_name','member_name'])
def test_extension_identity_and_property_references_cannot_diverge(fault):
    raw,extra,ctx=sql_fixture()
    if fault=='member_name':raw['extension_members'][1]['name']='other_class'
    else:
        raw['extension_properties'][1]['properties']['opcname']='other_class'
        for row in ctx['fixed_properties']['extension_properties']:
            if row['properties'] is not None:row['properties']['opcname']='other_class'
    with pytest.raises(ins.h.PrerequisiteRefused,match='OPCLASS_IDENTITY_REFERENCE'):convert(raw,extra,ctx)


@pytest.mark.parametrize('fault',['schema_effective','schema_owner_login','system_schema_create','template_extension'])
def test_unprojected_sql_properties_are_not_ignored(fault):
    raw,extra,ctx=sql_fixture()
    if fault=='schema_effective':raw['schemas'][0]['can_create']=True
    if fault=='schema_owner_login':raw['schemas'][0]['owner_login']=True
    if fault=='system_schema_create':raw['schemas'].append(dict(name='unmanaged',owner=ADMIN,owner_login=True,can_create=True,can_use=True,grant_create=True,grant_use=True))
    if fault=='template_extension':raw['extension'][0]['version']='unexpected'
    with pytest.raises(ins.h.PrerequisiteRefused):convert(raw,extra,ctx)


@pytest.mark.parametrize('setting',['transaction_isolation','transaction_read_only'])
def test_session_setting_is_checked_against_fixed_declaration(setting):
    raw,extra,ctx=sql_fixture()
    next(r for r in raw['settings'] if r['name']==setting)['setting']='unexpected'
    with pytest.raises(ins.h.PrerequisiteRefused,match='SESSION_SETTINGS_DIVERGENCE'):convert(raw,extra,ctx)


def test_extension_type_query_and_validator_have_matching_property_coverage():
    # Query formerly returned NULL for pg_type members while rows() required
    # a complete pg_type record. The type_details fixture is independently
    # authored in the table conversion test; NULL must remain a refusal.
    assert "WHEN 'pg_catalog.pg_type'::pg_catalog.regclass THEN" in QUERIES['extension_properties'].sql
    with pytest.raises(ins.h.PrerequisiteRefused,match='Incomplete extension properties'):
        ins.rows('extension_properties',[dict(extension='btree_gist',identity='public.fixture_type',catalog='pg_type',properties=None)])


def test_sql_casts_oid_json_strings_without_relaxing_strict_types():
    from migrations.dev09b_inspection_queries import _oid_columns
    for catalog in ('pg_type','pg_operator','pg_opclass','pg_opfamily'):
        assert all("'"+field+"',o."+field+'::pg_catalog.int8' in QUERIES['extension_properties'].sql for field in _oid_columns[catalog].split())
    assert all("'"+field+"',t."+field+'::pg_catalog.int8' in QUERIES['type_details'].sql for field in _oid_columns['pg_type'].split())
    for catalog in ('pg_amop','pg_amproc'):
        assert all("'"+field+"',m."+field+'::pg_catalog.int8' in QUERIES['operator_members'].sql for field in _oid_columns[catalog].split())
    raw,extra,ctx=sql_fixture()
    raw['extension_properties'][1]['properties']['opcowner']='10'  # PG to_jsonb(oid) representation before the SQL fix
    with pytest.raises(ins.h.PrerequisiteRefused):convert(raw,extra,ctx)


def foreign_key_sql_fixture():
    # Literal PostgreSQL-facing data, allocated trigger names intentionally do
    # not resemble the stable source identities produced by the compiler.
    raw,extra,ctx=table_sql_fixture()
    raw['constraints'].append(dict(schema='inventory',name='demo_self_fkey',relation='inventory.demo',kind='f',validated=True,deferrable=False,initially_deferred=False,definition='FOREIGN KEY (id) REFERENCES inventory.demo(id)'))
    ctx['deparse']['constraints'].append(dict(schema='inventory',name='demo_self_fkey',sql='FOREIGN KEY (id) REFERENCES inventory.demo(id)',identity=['inventory','demo','demo_self_fkey'],definition=dict(kind='f',columns=['id'],references=['inventory.demo.id'],expression=None,operators=[],using=None,predicate=None,validated=True,deferrable=False,initially_deferred=False)))
    extra['object_identities'].append(identity_link('constraint','inventory','demo_self_fkey','table constraint','demo_self_fkey on inventory.demo',relation='demo'))
    for number,(function,event,side) in enumerate([('RI_FKey_check_ins','INSERT','c'),('RI_FKey_check_upd','UPDATE','c'),('RI_FKey_noaction_del','DELETE','a'),('RI_FKey_noaction_upd','UPDATE','a')],100):
        name='RI_ConstraintTrigger_'+side+'_'+str(number)
        extra['object_identities'].append(identity_link('trigger','inventory',name,'trigger',name+' on inventory.demo',relation='demo'))
        raw['triggers'].append(dict(schema='inventory',relation='demo',name=name,enabled='O',internal=True,definition='CONSTRUCTED INTERNAL TRIGGER '+str(number)))
        extra['trigger_semantics'].append(dict(schema='inventory',relation='demo',name=name,timing='AFTER',events=[event],row=True,function_schema='pg_catalog',function_name=function,function_arguments='',enabled='O',internal=True))
        extra['fk_trigger_links'].append(dict(schema='inventory',relation='demo',name=name,constraint_schema='inventory',constraint_name='demo_self_fkey',child_schema='inventory',child_relation='demo',parent_schema='inventory',parent_relation='demo',deferrable=False,initially_deferred=False,update_action='a',delete_action='a',match='s',constraint_deferrable=False,constraint_initially_deferred=False,validated=True,opposite_relation=True,no_arguments=True,no_condition=True,no_columns=True,no_transition=True))
    return raw,extra,ctx


def test_real_fk_rows_resolve_four_stable_source_identities():
    raw,extra,ctx=foreign_key_sql_fixture()
    normalized=d.normalize_observations(d.parse(convert(raw,extra,ctx).rows_json))
    triggers=[x for x in normalized['managed_objects'] if x['family']=='trigger']
    assert len(triggers)==4 and all(x['definition']['internal'] is True for x in triggers)
    assert {x['identity'][2] for x in triggers}=={'@fk:inventory.demo.demo_self_fkey:'+k for k in ('check_ins','check_upd','noaction_del','noaction_upd')}


@pytest.mark.parametrize('fault',['missing','extra','action','condition','deferrable','parent','function','event','name','type'])
def test_fk_trigger_completeness_and_binding_refusals(fault):
    raw,extra,ctx=foreign_key_sql_fixture()
    if fault=='missing':
        raw['triggers'].pop();extra['trigger_semantics'].pop();extra['fk_trigger_links'].pop()
    if fault=='extra':extra['fk_trigger_links'].append({**extra['fk_trigger_links'][0],'name':'RI_ConstraintTrigger_c_999'})
    if fault=='action':extra['fk_trigger_links'][0]['delete_action']='c'
    if fault=='condition':extra['fk_trigger_links'][0]['no_condition']=False
    if fault=='deferrable':extra['fk_trigger_links'][0]['deferrable']=True
    if fault=='parent':extra['fk_trigger_links'][0]['parent_relation']='other'
    if fault=='function':extra['trigger_semantics'][0]['function_name']='pg_control_system'
    if fault=='event':extra['trigger_semantics'][0]['events']=['DELETE']
    if fault=='name':raw['triggers'][0]['name']='invented'
    if fault=='type':extra['fk_trigger_links'][0]['validated']=1
    with pytest.raises((ins.h.PrerequisiteRefused,c.Invalid)):convert(raw,extra,ctx)


def test_detailed_prerequisite_port_reuses_real_migration_helper_and_refuses_wrong_prefix(tmp_path):
    from hashlib import sha256
    from scripts.dedicated.dev09b import layers as layers
    from scripts.postgres.tests.test_dev09b_detailed import seal_layers
    raw,extra,ctx,snapshot,profile,contract_raw=detailed_port_fixture(tmp_path)
    parts=list(layers.read_snapshot(snapshot));payload,target,executor,plan,semantic,phys,provenance=parts
    session=SessionBinding(payload['target_binding_sha256'],plan['executor_binding_sha256'],executor['incarnation_id'],42,1,'100')
    raw['identity'][0].update(current_user=MIGRATOR,session_user=MIGRATOR)
    for row in raw['schemas']:
        if row['name'] in {'public','inventory','audit'}:
            row['can_create']=row['can_use']=True
            raw['schema_acl'] += [dict(name=row['name'],grantor=row['owner'],grantee=MIGRATOR,privilege=k,grant_option=False) for k in ('CREATE','USAGE')]
    for row in extra['role_details']:
        if row['name']==MIGRATOR:row['login']=True
    extra['system_acl'].append({**extra['system_acl'][0],'grantee':MIGRATOR})
    for row in raw['settings']:
        if row['name']=='transaction_read_only':row['setting']='off'
    ctx['fixed_properties']['session_settings']['transaction_read_only']='off'
    ctx['metadata'].update({k:payload[k] for k in ('request_id','approval_id','attempt_id')})
    doc=c.parse(profile);doc['btree_gist']['members_sha256']=ins.digest([r for r in raw['extension_members'] if r['extension']=='btree_gist'])
    doc['btree_gist']['acl_sha256']=ins.digest([]);profile=c.canonical(doc);phys['prepared_profile_sha256']=sha256(profile).hexdigest()
    ref=next(r for r in provenance['source_inventory'] if r['path']=='fixtures/conversion-declarations.json')
    ref['sha256']=sha256(d.encode(ctx)).hexdigest();(tmp_path/ref['path']).write_bytes(d.encode(ctx))
    executor['source_inventory_sha256']=layers.document_hash(provenance['source_inventory']);plan['executor_binding_sha256']=c.digest('executor',executor)
    session=SessionBinding(session.target_sha256,plan['executor_binding_sha256'],session.incarnation_id,42,1,'100')
    doc['source_inventory_sha256']=executor['source_inventory_sha256'];profile=c.canonical(doc);phys['prepared_profile_sha256']=sha256(profile).hexdigest()
    seal_layers(parts);snapshot=layers.freeze_expectations(*parts)
    contract=d.parse(contract_raw);contract.update(schema_version=3,profile_sha256=sha256(profile).hexdigest(),snapshot_sha256=sha256(snapshot.physical).hexdigest(),binding=raw['identity'][0],context=ctx,conversion_source=ref,subject_session=asdict(session))
    contracts=tuple(d.encode({**contract,'prerequisite':i}) for i in range(5))
    verifier=SimpleNamespace(verify=lambda pjson,cjson:ins.InspectionApproval(ins.h.ProfileAttestation(sha256(profile).hexdigest(),doc['target_sha256'],doc['bundle_sha256'],True,'OPERATIONAL'),sha256(cjson).hexdigest(),ins.digest(contract['binding']),'OFFLINE-TEST-BOUNDARY'))
    conn,tx,results,calls=connection_fixture(raw,extra)
    port=ins.PreparedInspectionPort(conn,tx,profile_verifier=verifier,source_root=tmp_path,detailed_snapshot=snapshot,detailed_session=session,prerequisite_contracts=contracts)
    context=ins.h.PreparedContext(profile,port)
    ins.h.require_prepared_environment(SimpleNamespace(attributes={'connection':conn,ins.h.ATTR:context}))
    assert port._cursor==1 and not port._failed and conn.get_transaction() is tx
    # A second call with the same empty catalog must NOT pass the post-ledger
    # checkpoint; its expectation is source-derived PRESENT-empty, not observed.
    with pytest.raises(c.Invalid):ins.h.require_prepared_schema('inventory',context=context)
    assert port._failed and all(result.closed for result in results)


def helper_sql_fixture():
    from scripts.dedicated.dev09b import own_settings as policy
    raw,extra,ctx=sql_fixture();declaration=policy.declaration();body=declaration['object']['definition']
    ctx['approved_helpers']=[declaration]
    raw['identity'][0].update(current_user=policy.PROBE,session_user=policy.PROBE,system_identifier=policy.TARGET_SID)
    extra['role_details'].append(dict(name=policy.PROBE,login=True,superuser=False,createdb=False,createrole=False,replication=False,bypassrls=False,inherit=False))
    extra['helper_owner_role']=[deepcopy(policy.OWNER_ROLE)]
    extra['helper_owner_edges']=[deepcopy(policy.OWNER_EDGE)]
    extra['helper_security_flags']=[deepcopy(policy.SECURITY_FLAGS)]
    ctx['metadata']['role_bindings']['inspector']=policy.PROBE
    raw['routines'].append(dict(schema='public',name=policy.IDENTITY[1],arguments='',kind='f',owner=policy.OWNER,security_definer=True,config=body['config'],definition='CONSTRUCTED HELPER DEFINITION'))
    raw['executable_definers']=[dict(schema='public',name=policy.IDENTITY[1],arguments='',owner=policy.OWNER,definition='CONSTRUCTED HELPER DEFINITION')]
    extra['routine_semantics'].append(dict(schema='public',name=policy.IDENTITY[1],arguments='',returns=body['returns'],language='sql',body=body['body'],volatility='s',strict=False,parallel='u',security_definer=True,config=body['config'],owner=policy.OWNER))
    extra['object_identities'].append(identity_link('routine','public',policy.IDENTITY[1],'function','public.'+policy.IDENTITY[1]+'()',direct_namespace=True))
    raw['namespace_objects'].append(dict(schema='public',type='function',identity='public.'+policy.IDENTITY[1]+'()'))
    ctx['deparse']['routines']=[dict(schema='public',name=policy.IDENTITY[1],arguments='',sql='CONSTRUCTED HELPER DEFINITION')]
    for grantee in (policy.OWNER,policy.PROBE):raw['object_acl'].append(dict(family='routine',schema='public',name=policy.IDENTITY[1],grantor=policy.OWNER,grantee=grantee,privilege='EXECUTE',grant_option=False))
    for row in raw['settings']:
        if row['name'] in policy.NAMES:row['setting']=None
    extra['own_preload_settings']=[dict(name=name,setting=None) for name in sorted(policy.NAMES)]
    extra['helper_preload_settings']=[dict(backend_pid=42,name=name,setting='') for name in sorted(policy.NAMES)]
    return raw,extra,ctx


def test_approved_helper_values_are_same_session_observations_not_authorization():
    raw,extra,ctx=helper_sql_fixture();converted=convert(raw,extra,ctx)
    observed=d.normalize_observations(d.parse(converted.rows_json))
    assert observed['distribution']['settings']['session_preload_libraries']==''
    helper=[obj for obj in observed['system_objects'] if obj['identity'][:2]==['public','dev09b_own_preload_settings']]
    assert len(helper)==1 and helper[0]['definition']['security_definer'] is True
    assert not hasattr(converted,'authorize')


@pytest.mark.parametrize('fault',['body','owner','public','other_definer','pid','extra_setting','missing_setting','undeclared','source','extra_grant'])
def test_helper_exception_never_expands_or_fills_uncertainty(fault):
    raw,extra,ctx=helper_sql_fixture()
    if fault=='body':extra['routine_semantics'][-1]['body']='SELECT secret FROM elsewhere'
    if fault=='owner':extra['routine_semantics'][-1]['owner']='other'
    if fault=='public':raw['object_acl'][-1]['grantee']='PUBLIC'
    if fault=='other_definer':raw['executable_definers'].append({**raw['executable_definers'][0],'name':'other'})
    if fault=='pid':extra['helper_preload_settings'][0]['backend_pid']=99
    if fault=='extra_setting':extra['helper_preload_settings'].append(dict(backend_pid=42,name='another_setting',setting=''))
    if fault=='missing_setting':extra['helper_preload_settings'].pop()
    if fault=='undeclared':ctx.pop('approved_helpers')
    if fault=='source':ctx['approved_helpers'][0]['source_sha256']='0'*64
    if fault=='extra_grant':ctx['approved_helpers'][0]['grants'].append(dict(grantee=MIGRATOR,privilege='EXECUTE',grant_option=False))
    with pytest.raises((c.Invalid,ins.h.PrerequisiteRefused)):convert(raw,extra,ctx)


def test_helper_is_verified_before_elevated_call_and_never_called_on_bad_body():
    raw,extra,ctx=helper_sql_fixture();conn,tx,results,calls=connection_fixture(raw,extra)
    ins.collect_detailed_sql(conn,tx,collector_id='helper-fixture',role_names=[r['name'] for r in extra['role_details']],system_routines=['pg_catalog.pg_control_system'],language_names=['plpgsql'],approved_helpers=ctx['approved_helpers'])
    names=[name for _,name,_ in calls]
    assert names.count('helper_preload_settings')==1 and names.index('helper_preload_settings')>names.index('routine_semantics')
    raw,extra,ctx=helper_sql_fixture();extra['routine_semantics'][-1]['body']='UNAPPROVED'
    conn,tx,results,calls=connection_fixture(raw,extra)
    with pytest.raises(c.Invalid):ins.collect_detailed_sql(conn,tx,collector_id='helper-fixture',role_names=[r['name'] for r in extra['role_details']],system_routines=['pg_catalog.pg_control_system'],language_names=['plpgsql'],approved_helpers=ctx['approved_helpers'])
    assert not any(name=='helper_preload_settings' for _,name,_ in calls) and all(r.closed for r in results)


def test_pg_identify_null_function_name_and_qualified_arguments_resolve_by_catalog_link():
    raw,extra,ctx=sql_fixture()
    member=dict(extension='btree_gist',type='function',schema='public',name=None,identity='public.fixture(integer)',subid=0)
    prop=dict(extension='btree_gist',identity=member['identity'],catalog='pg_catalog.pg_proc',properties=None)
    raw['extension_members'].append(member);raw['extension_properties'].append(prop)
    ctx['fixed_properties']['extension_properties'].append(deepcopy(prop));ctx['fixed_properties']['extension_properties'].sort(key=d.encode)
    raw['routines'].append(dict(schema='public',name='fixture',arguments='integer',kind='f',owner=OWNER,security_definer=False,config=None,definition='CONSTRUCTED C FUNCTION DEFINITION'))
    extra['routine_semantics'].append(dict(schema='public',name='fixture',arguments='integer',returns='boolean',language='c',body='fixture_symbol',volatility='i',strict=True,parallel='s',security_definer=False,config=None,owner=OWNER))
    ctx['deparse']['routines']=[dict(schema='public',name='fixture',arguments='integer',sql='CONSTRUCTED C FUNCTION DEFINITION')]
    extra['object_identities'].append(identity_link('routine','public','fixture','function',member['identity'],arguments='integer',direct_namespace=True))
    raw['namespace_objects'].append(dict(schema='public',type='function',identity=member['identity']))
    raw['object_acl'].append(dict(family='routine',schema='public',name='fixtureinteger',grantor=OWNER,grantee=OWNER,privilege='EXECUTE',grant_option=False))
    normalized=d.normalize_observations(d.parse(convert(raw,extra,ctx).rows_json))
    fn=next(x for x in normalized['extensions'][0]['members'] if x['family']=='routine')
    assert fn['identity']==['public','fixture','integer'] and fn['definition']['body']=='fixture_symbol'
    # A NULL name is a real pg_identify representation, not a license to ignore
    # divergent schema/identity bindings.
    member['schema']='other'
    with pytest.raises(ins.h.PrerequisiteRefused,match='UNRESOLVED_EXTENSION_ROUTINE'):convert(raw,extra,ctx)


@pytest.mark.parametrize('family',['schema','system','relation','type'])
def test_nominal_acl_owner_rows_cannot_be_truncated_away(family):
    raw,extra,ctx=table_sql_fixture()
    if family=='schema':raw['schema_acl']=[r for r in raw['schema_acl'] if not (r['name']=='inventory' and r['privilege']=='CREATE')]
    if family=='system':extra['system_acl']=[r for r in extra['system_acl'] if not (r['name']=='pg_control_system' and r['grantee']==OWNER)]
    if family=='relation':raw['object_acl']=[r for r in raw['object_acl'] if not (r['name']=='demo' and r['privilege']=='SELECT')]
    if family=='type':raw['object_acl']=[r for r in raw['object_acl'] if not (r['family']=='type' and r['name']=='_demo')]
    with pytest.raises(ins.h.PrerequisiteRefused,match='ACL_OWNER_COVERAGE'):convert(raw,extra,ctx)


@pytest.mark.parametrize('fault',['login','superuser','createdb','createrole','replication','bypassrls','inherit','limit','expiry','edge_admin','edge_set','edge_inherit','edge_grantor','incoming','probe_member','probe_settings','probe_create','owner_create','owner_settings','owner_extra','settings_excess','type','wrong_target'])
def test_dedicated_helper_owner_and_membership_are_exact(fault):
    raw,extra,ctx=helper_sql_fixture()
    if fault in {'login','superuser','createdb','createrole','replication','bypassrls','inherit'}:extra['helper_owner_role'][0][fault]=True
    elif fault=='limit':extra['helper_owner_role'][0]['connection_limit']=-1
    elif fault=='expiry':extra['helper_owner_role'][0]['valid_until']='2030-01-01'
    elif fault=='edge_admin':extra['helper_owner_edges'][0]['admin']=True
    elif fault=='edge_set':extra['helper_owner_edges'][0]['set']=True
    elif fault=='edge_inherit':extra['helper_owner_edges'][0]['inherit']=False
    elif fault=='edge_grantor':extra['helper_owner_edges'][0]['grantor']='unapproved'
    elif fault=='incoming':extra['helper_owner_edges'].append({**extra['helper_owner_edges'][0],'role':extra['helper_owner_edges'][0]['member'],'member':MIGRATOR})
    elif fault=='probe_member':extra['helper_security_flags'][0]['probe_owner_member']=True
    elif fault=='probe_settings':extra['helper_security_flags'][0]['probe_settings_member']=True
    elif fault=='probe_create':extra['helper_security_flags'][0]['probe_create_public']=True
    elif fault=='owner_create':extra['helper_security_flags'][0]['owner_create_schema']=True
    elif fault=='owner_settings':extra['helper_security_flags'][0]['owner_settings_usage']=False
    elif fault=='owner_extra':extra['helper_security_flags'][0]['owner_extra_dependency']=True
    elif fault=='settings_excess':extra['helper_security_flags'][0]['settings_role_excess']=True
    elif fault=='type':extra['helper_security_flags'][0]['owner_settings_usage']=1
    elif fault=='wrong_target':raw['identity'][0]['system_identifier']='123'
    with pytest.raises((c.Invalid,ins.h.PrerequisiteRefused)):convert(raw,extra,ctx)


def test_privileged_owner_or_membership_divergence_refuses_before_helper_call():
    raw,extra,ctx=helper_sql_fixture();extra['helper_owner_role'][0]['superuser']=True
    conn,tx,results,calls=connection_fixture(raw,extra)
    with pytest.raises(c.Invalid):ins.collect_detailed_sql(conn,tx,collector_id='helper-fixture',role_names=[r['name'] for r in extra['role_details']],system_routines=['pg_catalog.pg_control_system'],language_names=['plpgsql'],approved_helpers=ctx['approved_helpers'])
    assert not any(name=='helper_preload_settings' for _,name,_ in calls) and all(r.closed for r in results)


def test_operator_class_and_family_may_share_identify_text_but_not_catalog():
    raw,extra,ctx=sql_fixture()
    original=next(r for r in raw['extension_members'] if r['type']=='operator class')
    member={**original,'type':'operator family'}
    raw['extension_members'].append(member)
    prop=dict(extension=member['extension'],identity=member['identity'],catalog='pg_catalog.pg_opfamily',properties=dict(
        opfmethod=783,opfname='fixture_uuid_ops',opfnamespace=2200,opfowner=10))
    raw['extension_properties'].append(prop)
    expected=deepcopy(prop)
    expected['properties'].update(opfmethod=dict(schema='',name='gist',display='gist'),opfnamespace=dict(schema='',name='public',display='public'),opfowner=dict(schema='',name=OWNER,display=OWNER))
    ctx['fixed_properties']['extension_properties'].append(expected);ctx['fixed_properties']['extension_properties'].sort(key=d.encode)
    extra['object_identities'].append(identity_link('opfamily','public','fixture_uuid_ops','operator family',member['identity']))
    value=d.normalize_observations(d.parse(convert(raw,extra,ctx).rows_json))
    assert {r['family'] for r in value['extensions'][0]['members']}=={'opclass','opfamily'}
    raw['extension_members'].append(deepcopy(member))
    with pytest.raises(a.h.PrerequisiteRefused,match='Duplicate query row: extension_members'):convert(raw,extra,ctx)


def test_extension_property_catalog_alias_has_its_own_explicit_join():
    sql=QUERIES['extension_properties'].sql
    assert "'pg_catalog.'||catalog.relname AS catalog" in sql
    assert 'JOIN pg_catalog.pg_class catalog ON catalog.oid=d.classid' in sql
    assert "catalog.relnamespace='pg_catalog'::pg_catalog.regnamespace" in sql
    assert 'catalog.relname' not in QUERIES['extension_members'].sql


def test_acl_union_preserves_long_routine_signatures_as_text():
    sql=QUERIES['object_acl'].sql
    assert 'o.relname::pg_catalog.text AS name' in sql
    assert 'o.typname::pg_catalog.text AS name' in sql
    assert 'o.proname::pg_catalog.text || pg_catalog.pg_get_function_identity_arguments(o.oid) AS name' in sql
    raw,extra,ctx=sql_fixture()
    arguments='internal, timestamp with time zone, timestamp without time zone, internal'
    name='long_fixture_support_function'
    label=name+arguments
    assert len(label)>63
    raw['routines'].append(dict(schema='public',name=name,arguments=arguments,kind='f',owner=OWNER,security_definer=False,config=None,definition='CONSTRUCTED LONG SIGNATURE'))
    extra['routine_semantics'].append(dict(schema='public',name=name,arguments=arguments,returns='boolean',language='c',body=name,volatility='i',strict=True,parallel='s',security_definer=False,config=None,owner=OWNER))
    extra['object_identities'].append(identity_link('routine','public',name,'function','public.'+name+'(internal,timestamp with time zone,timestamp without time zone,internal)',arguments=arguments,direct_namespace=True))
    raw['namespace_objects'].append(dict(schema='public',type='function',identity=extra['object_identities'][-1]['identify_identity']))
    ctx['deparse']['routines'].append(dict(schema='public',name=name,arguments=arguments,sql='CONSTRUCTED LONG SIGNATURE'))
    row=dict(family='routine',schema='public',name=label,grantor=OWNER,grantee=OWNER,privilege='EXECUTE',grant_option=False)
    raw['object_acl'].append(row)
    assert convert(raw,extra,ctx).rows_json
    row['name']=label[:63]
    with pytest.raises(a.h.PrerequisiteRefused,match='UNRESOLVED_ROUTINE_ACL'):convert(raw,extra,ctx)


def test_template_extension_function_acl_is_corroborated_independently():
    raw,extra,ctx=sql_fixture()
    identity='pg_catalog.plpgsql_call_handler()'
    extra['routine_semantics'].append(dict(schema='pg_catalog',name='plpgsql_call_handler',arguments='',returns='language_handler',language='c',body='plpgsql_call_handler',volatility='v',strict=False,parallel='u',security_definer=False,config=None,owner=OWNER))
    extra['system_acl'] += [dict(family='routine',schema='pg_catalog',name='plpgsql_call_handler',arguments='',owner=OWNER,grantor=OWNER,grantee=who,privilege='EXECUTE',grant_option=False) for who in (OWNER,'PUBLIC')]
    extra['object_identities'].append(identity_link('routine','pg_catalog','plpgsql_call_handler','function',identity))
    raw['extension_members'].append(dict(extension='plpgsql',type='function',schema='pg_catalog',name=None,identity=identity,subid=0))
    prop=dict(extension='plpgsql',identity=identity,catalog='pg_catalog.pg_proc',properties=None)
    raw['extension_properties'].append(prop);ctx['fixed_properties']['extension_properties'].append(deepcopy(prop));ctx['fixed_properties']['extension_properties'].sort(key=d.encode)
    raw['extension_acl'] += [dict(extension='plpgsql',identity=identity,grantor=OWNER,grantee=who,privilege='EXECUTE',grant_option=False) for who in (OWNER,'PUBLIC')]
    assert convert(raw,extra,ctx).rows_json
    raw['extension_acl'][-1]['grantee']='fixture_runtime'
    with pytest.raises(a.h.PrerequisiteRefused,match='EXTENSION_ACL_DIVERGENCE'):convert(raw,extra,ctx)
