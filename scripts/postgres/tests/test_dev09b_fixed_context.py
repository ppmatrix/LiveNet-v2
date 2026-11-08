"""Source-only compiler tests: literal vectors, no server captures or SQL."""
from pathlib import Path
from copy import deepcopy
from unittest.mock import Mock
import shutil,socket,subprocess
import pytest
from scripts.dedicated.dev09b import fixed_catalog_context as f,codec as c,physical as p,own_settings as helper
from migrations.dev09b_detailed_queries import DETAIL_QUERIES
ROOT=Path(__file__).resolve().parents[3]

@pytest.fixture(autouse=True)
def offline(monkeypatch):
    denied=Mock(side_effect=AssertionError('offline-only'))
    for obj,name in ((socket,'socket'),(socket,'create_connection'),(subprocess,'run'),(subprocess,'Popen')):monkeypatch.setattr(obj,name,denied)


def test_verified_source_closure_and_archive_identity():
    sources,manifest=f.load_sources(ROOT)
    assert len(sources)==15 and set(sources)==f.SOURCE_FILES
    assert manifest['archive_sha256']=='c1575341fa7bd40f5274ea465b34390f4dc64cdd0770af327005caaeb9f6b7ed'
    assert manifest['status']=='CANDIDATE_NOT_APPROVED'


def test_upstream_source_tampering_refuses(tmp_path):
    base=Path(f.SOURCE_MANIFEST).parent
    shutil.copytree(ROOT/base,tmp_path/base)
    path=tmp_path/base/'src/backend/catalog/pg_type.c';path.write_bytes(path.read_bytes()+b'\n')
    with pytest.raises(c.Invalid):f.load_sources(tmp_path)


def test_literal_pg16_deparse_vector_and_keyword_type_qualification():
    facts=f.declarations(ROOT,owner=helper.ADMIN)
    form=next(r for r in facts['deparse']['routines'] if r['name']=='gbt_uuid_consistent')
    assert form['sql']==("CREATE OR REPLACE FUNCTION public.gbt_uuid_consistent(internal, uuid, smallint, oid, internal)\n"
        " RETURNS boolean\n LANGUAGE c\n IMMUTABLE PARALLEL SAFE STRICT\n"
        "AS '$libdir/btree_gist', $function$gbt_uuid_consistent$function$\n")
    assert f.qualified_type(f.ref('pg_catalog','int4'))=='integer'
    assert f.qualified_type(f.ref('pg_catalog','oid'))=='pg_catalog.oid'
    assert f.qualified_type(f.ref('pg_catalog','char'))=='pg_catalog."char"'
    helper_form=next(r for r in facts['deparse']['routines'] if r['name']==helper.IDENTITY[1])
    assert " STABLE SECURITY DEFINER\n SET search_path TO 'pg_catalog'\n" in helper_form['sql']
    assert helper_form['sql'].endswith(" wanted(name)\n$function$\n")


def test_literal_base_type_array_defaults_and_explicit_acl_policy():
    facts=f.declarations(ROOT,owner=helper.ADMIN)
    rows={r['name']:r['properties'] for r in facts['fixed_properties']['type_details']}
    base=rows['gbtreekey8'];array=rows['_gbtreekey8']
    assert (base['typlen'],base['typcategory'],base['typalign'],base['typstorage'],base['typbyval'])==(8,'U','i','p',False)
    assert base['typinput']=='gbtreekey8_in' and base['typacl']==[helper.ADMIN+'=U/'+helper.ADMIN]
    assert array['typlen']==-1 and array['typstorage']=='x' and array['typcategory']=='A'
    assert array['typsubscript']=='array_subscript_handler' and array['typanalyze']=='array_typanalyze'
    assert array['typacl'] is None and array['typelem']==f.ref('public','gbtreekey8','gbtreekey8')
    assert base['typarray']==f.ref('public','_gbtreekey8','gbtreekey8[]')
    # regoperatorout uses visible names; object identification uses qualified
    # input types. Their representation is intentionally distinct.
    op=next(r for r in facts['fixed_properties']['extension_properties'] if r['catalog']=='pg_catalog.pg_operator' and r['properties']['oprleft']['name']=='oid')
    assert op['identity']=='public.<->(pg_catalog.oid,pg_catalog.oid)'
    assert op['properties']['oprcom']['display']=='<->(oid,oid)'


def test_source_baseline_has_helper_and_no_operational_migrator_or_approval():
    inputs,expected=f.querytrial_inputs(ROOT)
    p.validate_snapshot(expected)
    assert inputs['context']['metadata']['role_bindings']['migrator'] is None
    assert inputs['context']['metadata']['request_id'] is None
    assert helper.OBJECT in expected['system_objects'] and helper.ROLE_OBJECT in expected['system_objects']
    assert len(expected['extensions'][0]['members'])==264
    assert expected['ledgers']==[dict(chain=x,presence='ABSENT',revisions=[]) for x in ('application','security')]
    assert expected['distribution']['locale_provider']=='libc' and expected['distribution']['collation']=='en_US.utf8'
    assert all(r['owner']!=helper.PROBE for r in expected['ownership'])
    with pytest.raises(c.Invalid):f.declarations(ROOT,owner='other_admin')


def test_system_routine_input_identity_excludes_out_parameters_consistently():
    for name in ('routine_semantics','system_acl','object_identities'):
        sql=DETAIL_QUERIES[name].sql
        assert "n.nspname='pg_catalog'" in sql and 'pg_catalog.oidvectortypes(p.proargtypes)' in sql
    assert 'CASE WHEN' in DETAIL_QUERIES['routine_semantics'].sql


def test_every_compiled_extension_object_has_a_complete_typed_definition():
    from scripts.dedicated.dev09b import detailed_catalog as d
    for obj in f.declarations(ROOT,owner=helper.ADMIN)['extension_objects']:
        d.artifact_object(obj)


def test_technical_baseline_inputs_are_recompiled_before_collection():
    from scripts.postgres.dev09b_detailed_querytrial import validate_inputs
    inputs,_=f.querytrial_inputs(ROOT)
    raw=c.canonical(inputs,maximum_depth=32)
    assert validate_inputs(raw)['comparison_profile']=='querytrial-prepared-source-baseline-v1'
    for fault in ('helper','role','property','query_selection'):
        bad=deepcopy(inputs)
        if fault=='helper':bad['approved_helpers']=[]
        elif fault=='role':bad['context']['metadata']['role_bindings']['migrator']=helper.ADMIN
        elif fault=='property':bad['context']['fixed_properties']['type_details'].pop()
        else:bad['selections']['system_routines'].pop()
        with pytest.raises(c.Invalid):validate_inputs(c.canonical(bad,maximum_depth=32))


def test_technical_comparison_rejects_extra_objects_and_wrong_types():
    from scripts.dedicated.dev09b import detailed_catalog as d
    inputs,expected=f.querytrial_inputs(ROOT)
    header={k:expected[k] for k in d.HEADER_FIELDS}
    objects=[dict(section=section,**obj) for field,section in d.OBJECT_SECTIONS.items() for obj in expected[field]]
    inventories={k:expected[k] for k in d.LIST_SECTIONS}
    observation=dict(format='DEV09B-PHASE-ROWS-1',header=header,objects=objects,inventories=inventories,
                     subject_session=None,request_id=None,approval_id=None,attempt_id=None)
    assert f.compare_querytrial_baseline(ROOT,inputs,observation)=='SOURCE_BASELINE_EQUAL_TECHNICAL_ONLY'
    bad=deepcopy(observation);bad['objects'].append(dict(section='managed',family='table',identity=['inventory','unexpected'],definition=dict(persistence='p',row_security=False,force_row_security=False)))
    with pytest.raises(c.Invalid):f.compare_querytrial_baseline(ROOT,inputs,bad)
    bad=deepcopy(observation);bad['inventories']['roles'][0]['login']=1
    with pytest.raises(c.Invalid):f.compare_querytrial_baseline(ROOT,inputs,bad)
