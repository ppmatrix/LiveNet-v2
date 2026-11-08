"""Independent literal source vectors, not captured or operational evidence."""
from pathlib import Path
from copy import deepcopy
from unittest.mock import Mock
import shutil,socket,subprocess
import pytest
from scripts.dedicated.dev09b import application_catalog_context as a,codec as c,physical as p
ROOT=Path(__file__).resolve().parents[3]
ROLES=dict(migrator='declared_migrator',inventory_owner='declared_inventory_owner',audit_owner='declared_audit_owner',security_owner='declared_security_owner',application_ledger_owner='declared_ledger_owner')
BUILD=dict(BLCKSZ=8192,SIZEOF_VOID_P=8,MAXIMUM_ALIGNOF=8)

@pytest.fixture(autouse=True)
def offline(monkeypatch):
    denied=Mock(side_effect=AssertionError('offline-only: no resources/SQL'))
    for obj,name in ((socket,'socket'),(socket,'create_connection'),(subprocess,'run'),(subprocess,'Popen')):monkeypatch.setattr(obj,name,denied)


def maps(phase='APP-F066-PRECOMMIT',**kw):
    kw.setdefault('encoding','UTF8');return a.compile_maps(ROOT,phase=phase,roles=ROLES,**kw)
def col(name,args=[]):return dict(definition=dict(type=dict(name=name,arguments=args)))


def test_complete_source_census_and_prefixes():
    x=maps()
    assert {k:len(v) for k,v in x['deparse'].items()}==dict(constraints=76,indexes=35,index_columns=61,routines=2,triggers=2)
    assert len(x['resolver_objects'])==14 and len(x['type_details'])==28 and len(x['implicit_objects'])==20
    assert len(x['migration_sources'])==13  # 14 total includes the excluded security revision
    assert [len(maps('APP-ENTRY',prerequisite=i)['resolver_objects']) for i in range(5)]==[0,1,5,8,13]
    assert not maps('DEV-BASE')['resolver_objects']


def test_literal_expression_vectors_and_no_unconsumed_tokens():
    types={'state':dict(name='sa.String',arguments=[32]),'n':dict(name='sa.Integer',arguments=[]),
           'confidence':dict(name='sa.Numeric',arguments=[5,4]),'data':dict(name='postgresql.JSONB',arguments=[])}
    for source,expected in [
        ('n >= 1','(n >= 1)'),('n IS NULL OR n > 0','((n IS NULL) OR (n > 0))'),
        ("state = 'global'","((state)::text = 'global'::text)"),
        ("state IN ('active', 'disabled')","((state)::text = ANY ((ARRAY['active'::character varying, 'disabled'::character varying])::text[]))"),
        ('confidence >= 0','(confidence >= (0)::numeric)'),
        ("jsonb_typeof(data) = 'object'","(jsonb_typeof(data) = 'object'::text)"),
        ('length(btrim(state)) > 0','(length(btrim((state)::text)) > 0)')]:
        assert a.expr(source,types)==expected
    for bad in ('n >= 1; DROP TABLE x','n >= 1 garbage','unknown = 1','now() = 1','n IN (0,1)'):
        with pytest.raises(c.Unsupported):a.expr(bad,types)


def test_toast_is_derived_per_table_not_assumed_for_every_varchar():
    assert not a.needs_toast([col('sa.Integer')],encoding='UTF8',build=BUILD)
    assert not a.needs_toast([col('sa.String',[32])],encoding='UTF8',build=BUILD)
    assert a.needs_toast([col('sa.Text')],encoding='UTF8',build=BUILD)
    assert a.needs_toast([col('postgresql.JSONB')],encoding='UTF8',build=BUILD)
    assert not a.needs_toast([col('sa.String',[501])],encoding='UTF8',build=BUILD)
    assert a.needs_toast([col('sa.String',[502])],encoding='UTF8',build=BUILD)
    assert not a.needs_toast([col('sa.Numeric',[5,4])],encoding='UTF8',build=BUILD)
    with pytest.raises(c.Unsupported):a.needs_toast([col('sa.Text')],encoding='LATIN1',build=BUILD)
    bad=deepcopy(BUILD);bad['BLCKSZ']=4096
    with pytest.raises(c.Invalid):a.needs_toast([col('sa.Text')],encoding='UTF8',build=bad)


def test_implicit_names_and_owner_are_source_bound_not_allocated_oid_guesses():
    x=maps();rows={r['name']:r['properties'] for r in x['type_details'] if r['schema']=='public'}
    assert rows['alembic_version']['typrelid']==dict(schema='public',name='alembic_version',display='public.alembic_version')
    assert rows['_alembic_version']['typelem']==dict(schema='public',name='alembic_version',display='alembic_version')
    assert rows['alembic_version']['typarray']==dict(schema='public',name='_alembic_version',display='alembic_version[]')
    assert rows['alembic_version']['typacl'] is rows['_alembic_version']['typacl'] is None
    assert rows['alembic_version']['typowner']['name']==ROLES['migrator']
    closed=maps('APP-F066-CLOSED');row=next(r for r in closed['type_details'] if r['schema']=='inventory')
    assert row['properties']['typowner']['name']==ROLES['inventory_owner']
    assert all(r['identity'][1].startswith('@toast:') for r in x['implicit_objects'])
    assert not any(r['relation']=='alembic_version' for r in x['implicit_objects'])


def test_literal_ledger_constraint_index_and_index_column():
    x=maps('APP-ENTRY',prerequisite=1)
    assert x['deparse']['constraints'][0]['sql']=='PRIMARY KEY (version_num)'
    assert x['deparse']['indexes'][0]['sql']=='CREATE UNIQUE INDEX alembic_version_pkc ON public.alembic_version USING btree (version_num)'
    assert x['deparse']['index_columns']==[dict(schema='public',relation='alembic_version_pkc',name='version_num',position=1,type='character varying(32)',not_null=False,identity='',generated='',default=None)]


def test_source_plpgsql_body_preserves_whitespace_and_trigger_order():
    x=maps();r=next(r for r in x['deparse']['routines'] if r['schema']=='audit')
    assert r['sql'].startswith('CREATE OR REPLACE FUNCTION audit.prevent_event_mutation()\n RETURNS trigger\n LANGUAGE plpgsql\nAS $function$')
    assert '\n        BEGIN\n' in r['sql'] and '$function$\n' in r['sql']
    trigger=next(r for r in x['deparse']['triggers'] if r['schema']=='audit')
    assert trigger['sql']=='CREATE TRIGGER trg_audit_events_immutable BEFORE DELETE OR UPDATE ON audit.events FOR EACH ROW EXECUTE FUNCTION audit.prevent_event_mutation()'


def test_missing_parameters_and_unknown_phase_are_precise():
    with pytest.raises(a.m.MissingParameter,match='application_context.roles'):a.compile_maps(ROOT,phase='APP-F066-PRECOMMIT',roles=None)
    bad=deepcopy(ROLES);bad.pop('migrator')
    with pytest.raises(a.m.MissingParameter,match='application_context.roles.migrator'):a.compile_maps(ROOT,phase='APP-F066-PRECOMMIT',roles=bad)
    with pytest.raises(c.Unsupported):maps('SEC-B12-PRECOMMIT')
    with pytest.raises(c.Invalid):maps('APP-ENTRY',prerequisite=True)


def test_candidate_artifact_tampering_refuses(tmp_path):
    import json
    path=Path(a.MANIFEST);base=path.parent
    shutil.copytree(ROOT/base,tmp_path/base)
    artifact=tmp_path/base/'src/backend/catalog/toasting.c';artifact.write_bytes(artifact.read_bytes()+b'\n')
    with pytest.raises(c.Invalid):a.load(tmp_path)


def test_existing_adapter_format_builder_does_not_modify_input_or_observe():
    from migrations.dev09b_catalog_adapter import source_context
    context=dict(fixed_properties=dict(type_details=[]),deparse={k:[] for k in ('constraints','indexes','index_columns','routines','triggers')},implicit_objects=[])
    old=deepcopy(context)
    actual=source_context(ROOT,context,phase='APP-ENTRY',roles=ROLES,encoding='UTF8',prerequisite=1)
    assert context==old and len(actual['fixed_properties']['type_details'])==2
    assert actual['deparse']['constraints'][0]['sql']=='PRIMARY KEY (version_num)'
    assert not hasattr(actual,'authorize')


def test_v2_dependent_acl_approval_is_limited_and_v1_unchanged():
    from scripts.postgres.tests.test_dev09b_detailed import detailed_fixture
    from scripts.dedicated.dev09b import migration_catalog as m
    parts,_,_=detailed_fixture();target=parts[1];parameters=deepcopy(parts[5]['parameters'])
    fragment=a.compile_maps(ROOT,phase='APP-F066-PRECOMMIT',roles=parameters['roles'],encoding='UTF8')
    parameters['resolver_objects']=fragment['resolver_objects']
    inputs=m.load_repository_sources(ROOT)[:-1]
    expected=p.compile_profile('APP-F066-PRECOMMIT',target,parameters,inputs)
    body=c.parse(expected.json,maximum=len(expected.json))
    dependent=[r for r in body['acls'] if r['family'] in {'composite_type','array_type'}]
    assert len(dependent)==28 and all(r['grants']==[p.grant('PUBLIC','USAGE')] for r in dependent)
    assert all(not r['grants'] for r in body['acls'] if r['family'] in {'table','column','index','constraint','toast'})
    assert all(g['grantee']!='PUBLIC' for r in body['acls'] if r['family']=='schema' for g in r['grants'])
    assert all('runtime' not in r['grantee'] for r in body['database_acl'])
    parameters['schema_version']=1;parameters['distribution'].pop('locale_provider')
    legacy=p.compile_profile('APP-F066-PRECOMMIT',target,parameters,m.load_repository_sources(ROOT))
    old=c.parse(legacy.json,maximum=len(legacy.json))
    assert all(r['grants']==[] for r in old['acls'] if r['family'] in {'composite_type','array_type'})


def test_duplicate_context_and_tampered_migration_refuse(tmp_path):
    context=dict(fixed_properties=dict(type_details=[]),deparse={k:[] for k in ('constraints','indexes','index_columns','routines','triggers')},implicit_objects=[])
    x=a.extend_context(ROOT,context,phase='APP-ENTRY',roles=ROLES,encoding='UTF8',prerequisite=1)
    x['deparse']['constraints'][0]['sql']='different'
    with pytest.raises(c.Invalid):a.extend_context(ROOT,x,phase='APP-ENTRY',roles=ROLES,encoding='UTF8',prerequisite=1)
    # Only the focused source trees are copied; no imports/SQL from migrations.
    for directory in ('scripts/dedicated/dev09b/artifacts/pg16-application','backend/migrations/versions','backend/security_migrations/versions'):
        shutil.copytree(ROOT/directory,tmp_path/directory)
    path=next((tmp_path/'backend/migrations/versions').glob('af62df027d9d_*.py'));path.write_bytes(path.read_bytes()+b'\n')
    with pytest.raises(c.Invalid):a.records_for(tmp_path,'APP-F066-PRECOMMIT',None)


def test_encoding_cannot_be_inferred_and_new_bundle_is_not_approval():
    from scripts.dedicated.dev09b import bundle
    with pytest.raises(a.m.MissingParameter,match='application_context.encoding'):
        a.compile_maps(ROOT,phase='APP-F066-PRECOMMIT',roles=ROLES)
    candidate=bundle.build_application_maps_candidate(ROOT)
    result=bundle.verify_application_maps_candidate(ROOT,candidate)
    assert candidate['status']=='CANDIDATE_NOT_APPROVED' and candidate['operational_authority'] is False
    assert candidate['application_maps']['postgres_execution']=='NOT_PERFORMED'
    assert result.missing_parameters and a.MANIFEST in {r['path'] for r in candidate['sources']}


def test_literal_ledger_rows_use_source_maps_in_real_adapter_with_rowmapping():
    from migrations import dev09b_catalog_adapter as adapter
    from scripts.dedicated.dev09b import detailed_catalog as detail
    from scripts.postgres.tests.test_dev09b_sql_adapter import sql_fixture,identity_link,driver_row,OWNER
    raw,extra,ctx=sql_fixture()
    roles={**ROLES,'migrator':OWNER}
    ctx=adapter.source_context(ROOT,ctx,phase='APP-ENTRY',roles=roles,encoding='UTF8',prerequisite=1)
    for name,kind in [('alembic_version','r'),('alembic_version_pkc','i')]:
        raw['relations'].append(dict(schema='public',name=name,kind=kind,owner=OWNER,persistence='p',row_security=False,force_row_security=False,options=None,partition_bound=None,view=None))
        raw['columns'].append(dict(schema='public',relation=name,name='version_num',position=1,type='character varying(32)',not_null=kind=='r',identity='',generated='',default=None))
        raw['object_acl'] += [dict(family='relation',schema='public',name=name,grantor=OWNER,grantee=OWNER,privilege=privilege,grant_option=False) for privilege in ('SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER')]
        extra['object_identities'].append(identity_link('relation','public',name,'table' if kind=='r' else 'index','public.'+name,direct_namespace=kind=='r'))
    raw['namespace_objects'].append(dict(schema='public',type='table',identity='public.alembic_version'))
    raw['constraints'].append(dict(schema='public',name='alembic_version_pkc',relation='alembic_version',kind='p',validated=True,deferrable=False,initially_deferred=False,definition='PRIMARY KEY (version_num)'))
    raw['indexes'].append(dict(schema='public',name='alembic_version_pkc',valid=True,ready=True,live=True,definition='CREATE UNIQUE INDEX alembic_version_pkc ON public.alembic_version USING btree (version_num)'))
    extra['object_identities'].append(identity_link('constraint','public','alembic_version_pkc','table constraint','alembic_version_pkc on public.alembic_version',relation='alembic_version'))
    extra['relation_types'].append(dict(schema='public',relation='alembic_version',relation_oid=4000,type_oid=4001,row_type='alembic_version',array_oid=4002,array_type='_alembic_version'))
    extra['reference_catalog'] += [dict(catalog=cat,oid=oid,schema='public',name=name,display=display) for cat,oid,name,display in [
        ('pg_class',4000,'alembic_version','public.alembic_version'),('pg_type',4001,'alembic_version','alembic_version'),('pg_type',4002,'_alembic_version','alembic_version[]')]]
    for array in (False,True):
        name='_alembic_version' if array else 'alembic_version'
        # Literal PostgreSQL-facing property vector, independent of the compiler
        # and normalizer. OIDs are synthetic fixture allocations, not target IDs.
        props=dict(typname=name,typnamespace=2200,typowner=10,typlen=-1,typbyval=False,typtype='b' if array else 'c',typcategory='A' if array else 'C',
            typispreferred=False,typisdefined=True,typdelim=',',typrelid=0 if array else 4000,typsubscript='array_subscript_handler' if array else '-',
            typelem=4001 if array else 0,typarray=0 if array else 4002,typinput='array_in' if array else 'record_in',typoutput='array_out' if array else 'record_out',
            typreceive='array_recv' if array else 'record_recv',typsend='array_send' if array else 'record_send',typmodin='-',typmodout='-',typanalyze='array_typanalyze' if array else '-',
            typalign='d',typstorage='x',typnotnull=False,typbasetype=0,typtypmod=-1,typndims=0,typcollation=0,typdefaultbin=None,typdefault=None,typacl=None)
        raw['type_details'].append(dict(schema='public',name=name,properties=props))
        raw['types'].append(dict(schema='public',name=name,owner=OWNER,kind=props['typtype'],category=props['typcategory'],not_null=False,default=None,base='-',element='alembic_version' if array else '-'))
        raw['object_acl'] += [dict(family='type',schema='public',name=name,grantor=OWNER,grantee=who,privilege='USAGE',grant_option=False) for who in (OWNER,'PUBLIC')]
        extra['object_identities'].append(identity_link('type','public',name,'type','public.alembic_version[]' if array else 'public.alembic_version'))
    sqlrows={k:[driver_row(r,True) for r in values] for k,values in raw.items()}
    supplemental={k:[driver_row(r,False) for r in values] for k,values in extra.items()}
    converted=adapter.convert_results(sqlrows,supplemental,ctx,phase='DEV-BASE',collector_id='constructed-source-map-ledger',ledger_rows=dict(application=[],security=None))
    # Conversion only: DEV-BASE acceptance is NOT asserted for a nonempty ledger.
    normalized=detail.normalize_observations(detail.parse(converted.rows_json))
    assert normalized['ledgers'][0]==dict(chain='application',presence='PRESENT',revisions=[])
    assert len([o for o in normalized['managed_objects'] if o['family'] in {'array_type','composite_type'}])==2
    broken=deepcopy(raw);broken['constraints'][0]['definition']='PRIMARY KEY (other_column)'
    with pytest.raises(adapter.h.PrerequisiteRefused,match='UNRECOGNIZED_SQL_DEFINITION'):adapter.convert_results(broken,extra,ctx,phase='DEV-BASE',collector_id='constructed-bad-ledger',ledger_rows=dict(application=[],security=None))


def test_excess_table_grant_is_still_refused_by_existing_phase_comparator():
    from scripts.postgres.tests.test_dev09b_detailed import detailed_fixture
    from scripts.dedicated.dev09b import migration_catalog as m
    parts,_,_=detailed_fixture();target=parts[1];parameters=deepcopy(parts[5]['parameters'])
    fragment=a.compile_maps(ROOT,phase='APP-F066-PRECOMMIT',roles=parameters['roles'],encoding='UTF8')
    parameters['resolver_objects']=fragment['resolver_objects']
    expected=p.compile_profile('APP-F066-PRECOMMIT',target,parameters,m.load_repository_sources(ROOT)[:-1])
    observed=c.parse(expected.json,maximum=len(expected.json))
    table=next(r for r in observed['acls'] if r['family']=='table')
    table['grants']=[p.grant('PUBLIC','SELECT')]
    with pytest.raises(c.Invalid):p.compare_profile(expected,observed)
