"""Fixed image artifacts and source compiler only; no SQL or resources."""
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock
import socket,subprocess
import pytest
from scripts.dedicated.dev09b import fixed_catalog_sources as f,migration_catalog as m,codec as c,physical as p
from scripts.postgres.tests.test_dev09b_detailed import detailed_fixture,rows

ROOT=Path(__file__).resolve().parents[3]

@pytest.fixture(autouse=True)
def offline(monkeypatch):
    denied=Mock(side_effect=AssertionError('offline-only'))
    for obj,name in ((socket,'socket'),(socket,'create_connection'),(subprocess,'run'),(subprocess,'Popen')):monkeypatch.setattr(obj,name,denied)


def test_exact_source_closure_and_independent_fk_function_facts():
    sources,manifest=f.load_sources(ROOT)
    assert set(sources)==f.FILES and manifest['status']=='CANDIDATE_NOT_APPROVED'
    functions=f.builtin_routines(sources['postgres.bki'],['RI_FKey_check_ins','RI_FKey_check_upd','RI_FKey_noaction_del','RI_FKey_noaction_upd'])
    assert len(functions)==4
    for fn in functions:
        assert fn['identity'][0]=='pg_catalog' and fn['identity'][2]==''
        assert fn['definition']==dict(returns='trigger',language='internal',body=fn['identity'][1],security_definer=False,
            volatility='VOLATILE',strict=True,parallel='SAFE',config=[])


def test_extension_all_statements_consumed_and_parallel_upgrade_order():
    sources,_=f.load_sources(ROOT);facts=f.extension_declarations(sources)
    assert len(facts['routines'])==188 and len(facts['types'])==6
    assert len(facts['classes'])==len(facts['families'])==26 and len(facts['operators'])==12
    byname={tuple(x['identity']):x['definition'] for x in facts['routines']}
    assert byname['public','gbt_uuid_consistent','internal, uuid, smallint, oid, internal']['parallel']=='SAFE'
    # 1.7 is installed AFTER the 1.6 parallel-safe upgrade; do not incorrectly
    # apply that earlier ALTER to newly created bool support functions.
    assert byname['public','gbt_bool_consistent','internal, boolean, smallint, oid, internal']['parallel']=='UNSAFE'
    assert byname['public','gbtreekey2_in','cstring']['parallel']=='SAFE'
    bad=dict(sources);bad[f.EXTENSION_FILES[-1]]+=b'\nDROP SCHEMA inventory;\n'
    with pytest.raises(c.Unsupported):f.extension_declarations(bad)


def test_tampered_artifact_fails_before_parsing(tmp_path):
    import shutil
    base=Path(f.MANIFEST).parent
    shutil.copytree(ROOT/base,tmp_path/base)
    path=tmp_path/base/'postgres.bki';path.write_bytes(path.read_bytes()+b'\n')
    with pytest.raises(c.Invalid):f.load_sources(tmp_path)


def test_no_unknown_build_macro_is_resolved_by_assumption():
    raw=(ROOT/Path(f.MANIFEST).parent/'postgres.bki').read_bytes()
    catalogs=f.bki_catalogs(raw)
    assert any(r['typlen']=={'build_constant':'NAMEDATALEN'} for r in catalogs['pg_type'])
    with pytest.raises(c.Invalid):f.bki_catalogs(raw.replace(b'NAMEDATALEN',b'UNKNOWN_BUILD_SIZE'))


def test_exact_five_prerequisites_derived_from_source_prefixes():
    parts,session,_=detailed_fixture();target=parts[1];parameters=parts[5]['parameters']
    inputs=m.load_repository_sources(ROOT)[:-1]
    checkpoints=[p.compile_profile('APP-ENTRY',target,parameters,inputs,prerequisite=i) for i in range(5)]
    decoded=[c.parse(x.json,maximum=len(x.json)) for x in checkpoints]
    assert [s['ledgers'][0] for s in decoded]==[
        dict(chain='application',presence='ABSENT',revisions=[]),dict(chain='application',presence='PRESENT',revisions=[]),
        dict(chain='application',presence='PRESENT',revisions=['da34876e4210']),
        dict(chain='application',presence='PRESENT',revisions=['7c4e2a91b605']),
        dict(chain='application',presence='PRESENT',revisions=['f065d01a7230'])]
    assert sum(x['family']=='table' for x in decoded[0]['managed_objects'])==0
    assert sum(x['family']=='table' for x in decoded[1]['managed_objects'])==1
    assert not any(x['identity'][:2]==['audit','events'] for x in decoded[-1]['managed_objects'])
    full=p.compile_profile('APP-F066-PRECOMMIT',target,parameters,inputs)
    body=c.parse(full.json,maximum=len(full.json));internal=[x for x in body['managed_objects'] if x['family']=='trigger' and x['definition']['internal']]
    assert len(internal)==52
    for expected,value in zip(checkpoints,decoded):
        p.compare_profile(expected,value)
        bad=deepcopy(value);bad['ledgers'][0]['revisions']=['f066a01a7230']
        with pytest.raises(c.Invalid):p.compare_profile(expected,bad)


def test_application_candidate_integrity_never_claims_profile_or_lock_approval():
    from scripts.dedicated.dev09b import bundle
    candidate=bundle.build_application_candidate(ROOT)
    checked=bundle.verify_application_candidate(ROOT,candidate)
    assert candidate['status']=='CANDIDATE_NOT_APPROVED' and candidate['operational_authority'] is False
    assert candidate['physical_profile_state']=='INCOMPLETE_TARGET_DECLARATIONS'
    assert 'dependencies.cryptography.approved_transitive_lock' in checked.missing_parameters
    assert len(candidate['source_declarations']['foreign_key_triggers'])==52
    assert any(x['path']==f.MANIFEST for x in candidate['sources'])
    bad=deepcopy(candidate);bad['status']='APPROVED'
    with pytest.raises(c.Invalid):bundle.verify_application_candidate(ROOT,bad)


def test_helper_design_source_hash_and_body_are_exact_and_administration_not_implied():
    from hashlib import sha256
    from scripts.dedicated.dev09b import own_settings as policy
    raw=(ROOT/policy.SOURCE).read_bytes();assert sha256(raw).hexdigest()==policy.SOURCE_SHA256
    assert policy.BODY in raw.decode()
    assert 'GRANT EXECUTE ON FUNCTION public.dev09b_own_preload_settings() TO dev09b_trial_probe;' in raw.decode()
    assert 'CREATE ROLE dev09b_trial_settings_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE' in raw.decode()
    assert 'GRANT pg_read_all_settings TO dev09b_trial_settings_owner WITH ADMIN FALSE, INHERIT TRUE, SET FALSE;' in raw.decode()
    assert 'GRANT CREATE' not in raw.decode() and 'ALTER FUNCTION public.dev09b_own_preload_settings() OWNER TO dev09b_trial_settings_owner;' in raw.decode()
    source=policy.declaration();policy.validate(source)
    source['grants'][0]['grantee']='PUBLIC'
    with pytest.raises(c.Invalid):policy.validate(source)


def test_dedicated_owner_installation_guards_and_historical_bytes():
    import re
    from hashlib import sha256
    from scripts.dedicated.dev09b import own_settings as policy
    sql=(ROOT/policy.SOURCE).read_text()
    assert sha256((ROOT/'scripts/postgres/dev09b_own_settings.admin-owner.historical.sql').read_bytes()).hexdigest()=='eb857604454124a2165528225568199990d5fad673f0e264f36a77bcb22ea478'
    assert sql.index('CREATE ROLE')<sql.index('CREATE FUNCTION')<sql.index('ALTER FUNCTION')<sql.index('COMMIT;')
    assert "has_schema_privilege(probe_oid,public_oid,'CREATE')" in sql
    assert "WHERE member=probe_oid" in sql and "pg_has_role(probe_oid,owner_oid,'MEMBER')" in sql
    assert "pg_has_role(probe_oid,settings_oid,'MEMBER')" in sql
    assert 'SET LOCAL search_path=pg_catalog' in sql
    assert 'pg_catalog.pg_db_role_setting WHERE setrole=owner_oid' in sql
    # Verify the catalog used in the guard against the fixed PG16 bootstrap
    # schema: rolconfig is not a pg_authid column (role settings are separate).
    bki=(ROOT/Path(f.MANIFEST).parent/'postgres.bki').read_text()
    auth=re.search(r'create pg_authid .*?\n \(\n(.*?)\n \)',bki,re.S).group(1)
    assert 'rolpassword = text' in auth and 'rolconfig' not in auth
    assert 'rolconfig' not in sql
    assert sql.count('GRANT EXECUTE ON FUNCTION')==1 and 'GRANT CREATE' not in sql


def test_extension_members_resolve_without_server_oid_or_capture():
    sources,_=f.load_sources(ROOT)
    families=f.extension_member_declarations(sources)
    assert len(families)==26 and sum(len(x['members']) for x in families)==385
    byname={x['identity'][1]:x for x in families}
    oid=byname['gist_oid_ops']
    assert oid['input_type']==['pg_catalog','oid'] and oid['storage_type']==['public','gbtreekey8']
    member={(r['kind'],r['number']):r for r in oid['members']}
    assert member['operator',1]['reference']==['pg_catalog','<','oid','oid']
    assert member['operator',15]['reference']==['public','<->','oid','oid']
    assert member['operator',15]['ordering_family']==['pg_catalog','oid_ops','btree']
    assert member['function',1]['reference']==['public','gbt_oid_consistent','internal, oid, smallint, oid, internal']
    assert all(x['default'] is True for x in families)
    assert all(r['left'] and r['right'] for x in families for r in x['members'])


def test_extension_member_missing_reference_or_duplicate_is_not_ignored():
    sources,_=f.load_sources(ROOT)
    original=sources[f.EXTENSION_FILES[0]]
    bad=dict(sources);bad[f.EXTENSION_FILES[0]]=original.replace(b'gbt_oid_consistent (',b'unknown_oid_consistent (')
    with pytest.raises(c.Unsupported,match='Unresolved source support function'):f.extension_member_declarations(bad)
    # Keep a syntactically valid declaration but remove its built-in operator.
    bad=dict(sources);bad['postgres.bki']=sources['postgres.bki'].replace(b"'<'",b"'UNKNOWN_OPERATOR'")
    assert bad['postgres.bki']!=sources['postgres.bki']
    with pytest.raises(c.Unsupported,match='Unresolved source operator'):f.extension_member_declarations(bad)
    bad=dict(sources)
    import re
    clause=re.search(rb'OPERATOR\s+1\s+<\s*,',original).group(0)
    bad[f.EXTENSION_FILES[0]]=original.replace(clause,clause+b' '+clause,1)
    with pytest.raises(c.Invalid):f.extension_member_declarations(bad)
