"""Synthetic DB-API/SQLAlchemy doubles only; no PostgreSQL execution proof."""
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json
import socket
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from backend.migrations import dev09b_prerequisites as h
from backend.migrations import dev09b_inspection as i
from backend.migrations.dev09b_inspection_queries import QUERIES, LEDGER_SQL
from scripts.dedicated.dev09b import codec as c


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*a,**kw):raise AssertionError('No network')
    monkeypatch.setattr(socket,'socket',denied)
    monkeypatch.setattr(socket,'create_connection',denied)


class Result:
    def __init__(self,data):self.data=deepcopy(data);self.closed=False
    def mappings(self):return iter(self.data)
    def close(self):self.closed=True


class Connection:
    def __init__(self,binding,point):
        self.binding=binding;self.point=point;self.calls=[];self.results=[]
        self.transaction=SimpleNamespace(is_active=True)
        self.closed=False;self.dialect=SimpleNamespace(name='postgresql')
        self._echo=False;self.engine=SimpleNamespace(echo=False,hide_parameters=True,logger=SimpleNamespace(isEnabledFor=lambda level:False))
        self.identity_calls=0;self.mutation=None
    def in_transaction(self):return True
    def get_transaction(self):return self.transaction
    def execute(self,statement):
        sql=str(statement);self.calls.append(sql)
        if self.mutation:self.mutation(self,sql)
        if sql==QUERIES['identity'].sql:
            self.identity_calls+=1;data=[self.binding]
        elif sql in LEDGER_SQL.values():
            chain=next(k for k,v in LEDGER_SQL.items() if v==sql)
            data=[{'version_num':v} for v in self.point['ledgers'][chain]['revisions']]
        else:
            name=next(k for k,q in QUERIES.items() if q.sql==sql)
            data=self.point['queries'][name]
        result=Result(data);self.results.append(result);return result


class VerifierDouble:
    """Simulates a trusted boundary for algorithm tests, NOT an authenticator."""
    def __init__(self):self.calls=0;self.mutate=lambda r:r
    def verify(self,raw,contract_raw):
        self.calls+=1;p=h.decode_profile(raw);contract=c.parse(contract_raw,maximum=len(contract_raw))
        return self.mutate(i.InspectionApproval(h.ProfileAttestation(sha256(raw).hexdigest(),p['target_sha256'],p['bundle_sha256'],True,'OPERATIONAL'),
                    sha256(contract_raw).hexdigest(),i.digest(contract['binding']),'SYNTHETIC-VERIFIER-DOUBLE'))


def setup(tmp_path,security=False):
    source=tmp_path/'fixture.py';source.write_text('# Synthetic source only\n')
    inventory=[dict(path='fixture.py',sha256=sha256(source.read_bytes()).hexdigest())]
    profile=dict(profile=h.PROFILE,operation='security-base-to-b12b01a7230' if security else 'application-base-to-f066a01a7230',
        target_sha256='a'*64,bundle_sha256='b'*64,database='livenet_v2_dev',system_identifier='123',migrator='fixture_migrator',
        source_inventory_sha256=i.digest(inventory),schema_owners={s:'fixture_'+s+'_owner' for s in h.SCHEMAS},
        btree_gist=dict(version='1.7',schema='public',owner='fixture_admin',members_sha256='c'*64,acl_sha256='d'*64))
    binding=dict(database=profile['database'],current_user=profile['migrator'],session_user=profile['migrator'],system_identifier='123',pid=123,
        backend_start='fixture-start',xact_start='fixture-xact',virtualxid='4/1',address='192.0.2.1',port=5432,server_version_num=160010)
    queries={k:[] for k in QUERIES if k!='identity'}
    queries['privileges']=[dict.fromkeys(QUERIES['privileges'].fields,False)]
    allowed={'security','public'} if security else {'inventory','audit','public'}
    queries['schemas']=[dict(name=s,owner=profile['schema_owners'].get(s,'fixture_admin'),owner_login=False,
             can_create=s in allowed,can_use=s in allowed,grant_create=False,grant_use=False) for s in ('audit','inventory','public','security')]
    queries['settings']=[dict(name=n,setting='fixture') for n in ('search_path','session_replication_role','row_security','standard_conforming_strings','shared_preload_libraries','session_preload_libraries','local_preload_libraries','server_encoding','lc_collate','lc_ctype','transaction_isolation','transaction_read_only')]
    for row in queries['settings']:
        row['setting']={'search_path':'public','session_replication_role':'origin','row_security':'on','standard_conforming_strings':'on'}.get(row['name'],'fixture')
    queries['extension']=[dict(name='btree_gist',version='1.7',schema='public',owner='fixture_admin')]
    queries['extension_members']=[dict(extension='btree_gist',type='function',schema='public',name='fixture_fn',identity='public.fixture_fn()',subid=0)]
    profile['btree_gist']['members_sha256']=i.digest(queries['extension_members'])
    profile['btree_gist']['acl_sha256']=i.digest([])
    order=['environment','security'] if security else ['environment','inventory','btree_gist','btree_gist','audit']
    revs=[['f066a01a7230']]*2 if security else [None,[],['da34876e4210'],['7c4e2a91b605'],['f065d01a7230']]
    points=[]
    for index,name in enumerate(order):
        q=deepcopy(queries)
        states={'application':dict(presence='ABSENT' if revs[index] is None else 'PRESENT',revisions=revs[index] or []),
                'security':dict(presence='PRESENT' if security and index else 'ABSENT',revisions=[])}
        for chain,state in states.items():
            if state['presence']=='PRESENT':
                q['relations'].append(dict(schema='public',name='alembic_version' if chain=='application' else 'alembic_security_version',
                    kind='r',owner='fixture_owner',persistence='p',row_security=False,force_row_security=False,options=None,partition_bound=None,view=None))
        points.append(dict(requested=name,queries={k:i.rows(k,v) for k,v in q.items()},ledgers=states))
    raw=c.canonical(profile)
    contract=dict(schema_version=1,profile_sha256=sha256(raw).hexdigest(),binding=binding,source_inventory=inventory,checkpoints=points,
        query_inventory_sha256=i.digest({k:dict(sql=q.sql,fields=list(q.fields),maximum=q.maximum) for k,q in QUERIES.items()}))
    return raw,contract


def port(tmp_path,security=False):
    raw,contract=setup(tmp_path,security)
    conn=Connection(deepcopy(contract['binding']),deepcopy(contract['checkpoints'][0]));verifier=VerifierDouble()
    adapter=i.PreparedInspectionPort(conn,conn.transaction,profile_verifier=verifier,contract_json=c.canonical(contract),source_root=tmp_path)
    return raw,contract,conn,verifier,adapter


def test_import_construction_missing_verifier_and_no_side_effects(tmp_path):
    raw,contract=setup(tmp_path)
    connection=Mock();tx=Mock()
    adapter=i.PreparedInspectionPort(connection,tx)
    assert not connection.mock_calls and not tx.mock_calls
    raw,contract,conn,v,adapter=port(tmp_path)
    adapter._verifier=None
    with pytest.raises(h.MissingParameter,match='trusted_profile_verifier'):adapter.observe(raw,'environment')
    assert not conn.calls


def test_all_application_checkpoints_and_complete_readonly_queries(tmp_path):
    raw,contract,conn,v,adapter=port(tmp_path)
    for point in contract['checkpoints']:
        conn.point=deepcopy(point)
        observed=adapter.observe(raw,point['requested'])
        h.validate_observation(h.decode_profile(raw),observed,point['requested'])
    assert all(result.closed for result in conn.results)
    assert all(sql.lstrip().startswith('SELECT') for sql in conn.calls)
    assert all('LIMIT ' not in sql and 'pg_current_xact_id(' not in sql for sql in conn.calls)
    assert conn.get_transaction() is adapter._transaction
    with pytest.raises(h.PrerequisiteRefused,match='exhausted'):adapter.observe(raw,'environment')


@pytest.mark.parametrize('key',['database','system_identifier','pid','backend_start','xact_start','virtualxid','address','port','current_user','session_user'])
def test_binding_changes_rejected(tmp_path,key):
    raw,contract,conn,v,adapter=port(tmp_path)
    conn.binding[key]='192.0.2.2' if key=='address' else 999 if type(conn.binding[key]) is int else 'changed'
    with pytest.raises(h.PrerequisiteRefused,match='changed'):adapter.observe(raw,'environment')
    assert len(conn.calls)==1


def test_binding_changes_during_query_and_no_retry(tmp_path):
    raw,contract,conn,v,adapter=port(tmp_path)
    def change(connection,sql):
        if sql==QUERIES['settings'].sql:connection.binding['virtualxid']='changed'
    conn.mutation=change
    with pytest.raises(h.PrerequisiteRefused,match='changed'):adapter.observe(raw,'environment')
    count=len(conn.calls)
    with pytest.raises(h.PrerequisiteRefused,match='no automatic retry'):adapter.observe(raw,'environment')
    assert len(conn.calls)==count


def test_connection_and_transaction_swap(tmp_path):
    raw,contract,conn,v,adapter=port(tmp_path)
    with pytest.raises(h.PrerequisiteRefused,match='Connection changed'):adapter.assert_connection(Mock())
    conn.transaction=SimpleNamespace(is_active=True)
    with pytest.raises(h.PrerequisiteRefused,match='Transaction changed'):adapter.observe(raw,'environment')
    assert not conn.calls


@pytest.mark.parametrize('family',list(QUERIES.keys()-{'identity'}))
def test_each_catalog_family_divergence_is_refused(tmp_path,family):
    raw,contract,conn,v,adapter=port(tmp_path)
    conn.point['queries'][family].append(dict.fromkeys(QUERIES[family].fields,'extra'))
    with pytest.raises((h.PrerequisiteRefused,c.Invalid)):adapter.observe(raw,'environment')
    assert all(result.closed for result in conn.results)


def test_missing_family_and_observation_cannot_repair_expectations(tmp_path):
    raw,contract,conn,v,adapter=port(tmp_path)
    contract['checkpoints'][0]['queries'].pop('types')
    adapter._contract_json=c.canonical(contract)
    with pytest.raises(c.Invalid):adapter.observe(raw,'environment')
    assert not conn.calls


@pytest.mark.parametrize('change',[lambda r:True,lambda r:replace(r,contract_sha256='0'*64),
    lambda r:replace(r,binding_sha256='0'*64),lambda r:replace(r,attestation=replace(r.attestation,classification='SYNTHETIC')),
    lambda r:replace(r,attestation=replace(r.attestation,operationally_authenticated=False))])
def test_hash_label_or_synthetic_verification_cannot_authenticate(tmp_path,change):
    raw,contract,conn,v,adapter=port(tmp_path);v.mutate=change
    with pytest.raises(h.PrerequisiteRefused):adapter.observe(raw,'environment')
    assert not conn.calls


def test_security_requires_catalog_ledger_and_independent_f066(tmp_path):
    raw,contract,conn,v,adapter=port(tmp_path,True)
    with pytest.raises(h.MissingParameter,match='independent_f066'):adapter.observe(raw,'environment')
    raw,contract,conn,v,adapter=port(tmp_path,True)
    class IndependentDouble:
        def confirm(self,p,catalog):
            return i.BaselineConfirmation('a'*64,sha256(catalog).hexdigest(),'f066a01a7230','SYNTHETIC-BOUNDARY-DOUBLE')
    adapter._baseline=IndependentDouble()
    assert adapter.observe(raw,'environment')['prior_application_confirmed'] is True
    conn.point=deepcopy(contract['checkpoints'][1])
    assert adapter.observe(raw,'security')['prior_application_confirmed'] is True


def test_forged_f066_boolean_and_ledger_failure(tmp_path):
    raw,contract,conn,v,adapter=port(tmp_path,True)
    adapter._baseline=SimpleNamespace(confirm=lambda *args:True)
    with pytest.raises(h.PrerequisiteRefused,match='Independent f066'):adapter.observe(raw,'environment')
    raw,contract,conn,v,adapter=port(tmp_path,True)
    conn.point['ledgers']['application']['revisions']=[]
    with pytest.raises(h.PrerequisiteRefused,match='Ledger divergence'):adapter.observe(raw,'environment')


def test_incomplete_row_strict_bool_and_sources(tmp_path):
    raw,contract,conn,v,adapter=port(tmp_path)
    conn.point['queries']['privileges'][0]['superuser']=0
    with pytest.raises(h.PrerequisiteRefused):adapter.observe(raw,'environment')
    raw,contract,conn,v,adapter=port(tmp_path)
    conn.point['queries']['schemas'][0].pop('owner')
    with pytest.raises(h.PrerequisiteRefused,match='Incomplete row'):adapter.observe(raw,'environment')
    raw,contract,conn,v,adapter=port(tmp_path)
    (tmp_path/'fixture.py').write_text('modified')
    with pytest.raises(h.PrerequisiteRefused,match='Source inventory'):adapter.observe(raw,'environment')
    assert not conn.calls


def test_query_failure_closes_and_blocks_retry(tmp_path):
    raw,contract,conn,v,adapter=port(tmp_path)
    def fail(*args):raise RuntimeError('Synthetic query failure')
    conn.mutation=fail
    with pytest.raises(RuntimeError,match='Synthetic query failure'):adapter.observe(raw,'environment')
    with pytest.raises(h.PrerequisiteRefused,match='no automatic retry'):adapter.observe(raw,'environment')


def test_missing_contract_or_source_root_rejects_before_queries(tmp_path):
    raw,contract,conn,v,adapter=port(tmp_path)
    adapter._contract_json=None
    with pytest.raises(h.MissingParameter,match='fixed_inspection_contract'):adapter.observe(raw,'environment')
    assert not conn.calls
    raw,contract,conn,v,adapter=port(tmp_path)
    adapter._root=None
    with pytest.raises(h.MissingParameter,match='source_root'):adapter.observe(raw,'environment')
    assert not conn.calls


def test_transaction_loss_mid_collection_and_stream_failure(tmp_path):
    raw,contract,conn,v,adapter=port(tmp_path)
    def mutate(connection,sql):
        if sql==QUERIES['privileges'].sql:connection.transaction.is_active=False
    conn.mutation=mutate
    with pytest.raises(h.PrerequisiteRefused,match='Transaction changed'):adapter.observe(raw,'environment')
    assert all(x.closed for x in conn.results)
    raw,contract,conn,v,adapter=port(tmp_path)
    execute=conn.execute
    def broken(statement):
        result=execute(statement)
        if str(statement)==QUERIES['schemas'].sql:
            def interrupted():
                yield result.data[0]
                raise RuntimeError('Synthetic interrupted stream')
            result.mappings=interrupted
        return result
    conn.execute=broken
    with pytest.raises(RuntimeError,match='interrupted stream'):adapter.observe(raw,'environment')
    assert all(x.closed for x in conn.results)


def test_overflow_truncation_and_repeated_checkpoint(tmp_path):
    raw,contract,conn,v,adapter=port(tmp_path)
    conn.point['queries']['privileges']*=2
    with pytest.raises(h.PrerequisiteRefused,match='Oversized query'):adapter.observe(raw,'environment')
    assert all(x.closed for x in conn.results)
    raw,contract,conn,v,adapter=port(tmp_path)
    conn.point['queries']['schemas'].pop()
    with pytest.raises(h.PrerequisiteRefused,match='mismatch'):adapter.observe(raw,'environment')
    raw,contract,conn,v,adapter=port(tmp_path)
    adapter.observe(raw,'environment')
    before=len(conn.calls)
    with pytest.raises(h.PrerequisiteRefused,match='checkpoint'):adapter.observe(raw,'environment')
    assert len(conn.calls)==before


def test_opaque_extension_properties_are_not_a_catalog_schema():
    row=dict(extension='btree_gist',identity='public.fixture_operator',catalog='pg_operator',properties={'sha256':'a'*64})
    with pytest.raises(h.PrerequisiteRefused,match='Incomplete extension properties'):
        i.rows('extension_properties',[row])


@pytest.mark.parametrize('kind',['echo','cached','logger','missing'])
def test_port_refuses_unsafe_or_uninspectable_logging_before_sql(tmp_path,kind):
    raw,contract,conn,v,adapter=port(tmp_path)
    if kind=='echo':conn.engine.echo=True
    elif kind=='cached':conn._echo=True
    elif kind=='logger':conn.engine.logger.isEnabledFor=lambda level:True
    else:del conn._echo
    with pytest.raises(h.PrerequisiteRefused,match='CLIENT_LOGGING_REFUSED'):
        adapter.observe(raw,'environment')
    assert conn.calls==[] and v.calls==0


@pytest.mark.parametrize('address',['192.0.2.1','2001:db8::1'])
def test_port_host_literal_binding_and_host_sql(tmp_path,address):
    raw,contract,conn,v,adapter=port(tmp_path)
    contract['binding']['address']=address
    conn.binding['address']=address
    adapter._contract_json=c.canonical(contract)
    assert 'pg_catalog.host(pg_catalog.inet_server_addr()) AS address' in QUERIES['identity'].sql
    adapter.observe(raw,'environment')


@pytest.mark.parametrize('address',['192.0.2.1/32','2001:db8::1/128','192.0.2.0/24','2001:db8::/64','fe80::1%eth0','bad'])
def test_port_rejects_network_and_zone_in_fixed_binding(tmp_path,address):
    raw,contract,conn,v,adapter=port(tmp_path)
    contract['binding']['address']=address
    adapter._contract_json=c.canonical(contract)
    with pytest.raises(h.PrerequisiteRefused,match='IDENTITY_ADDRESS_INVALID'):
        adapter.observe(raw,'environment')
    assert conn.calls==[]


def test_port_real_sqlalchemy_row_and_rowmapping(tmp_path):
    from sqlalchemy import create_engine,select,literal,Integer,String
    raw,contract,conn,v,adapter=port(tmp_path)
    engine=create_engine('sqlite://',echo=False,hide_parameters=True)
    binding=contract['binding']
    statement=select(*(literal(value,Integer() if type(value) is int else String()).label(key) for key,value in binding.items()))
    try:
        with engine.connect() as real:
            i.support.check_client_logging(real)
            row=real.execute(statement).one()
            for value in (row,row._mapping,real.execute(statement).mappings().one()):
                conn.binding=value
                assert adapter._collect('identity')==[binding]
    finally:engine.dispose()


# Fixed independently of the production constant: losing a requirement must fail.
TWELVE_SETTINGS = {
    'search_path','session_replication_role','row_security','standard_conforming_strings',
    'shared_preload_libraries','session_preload_libraries','local_preload_libraries',
    'server_encoding','lc_collate','lc_ctype','transaction_isolation','transaction_read_only',
}
EIGHT_VISIBLE_GUCS = TWELVE_SETTINGS - {
    'lc_collate','lc_ctype','shared_preload_libraries','session_preload_libraries',
}


def setting_records():
    return [dict(name=name,setting='fixture') for name in sorted(TWELVE_SETTINGS)]


def test_settings_twelve_names_and_distinct_locale_sources():
    assert set(i.support.SETTINGS_NAMES)==TWELVE_SETTINGS
    assert len(i.support.SETTINGS_NAMES)==12
    sql=QUERIES['settings'].sql
    import re
    wanted=re.search(r'FROM \(VALUES (.*?)\) AS wanted\(name\)',sql).group(1)
    assert re.findall(r"\('([a-z_]+)'\)",wanted)==list(i.support.SETTINGS_NAMES)
    assert "WHEN 'lc_collate' THEN db.datcollate" in sql
    assert "WHEN 'lc_ctype' THEN db.datctype" in sql
    assert 'LEFT JOIN pg_catalog.pg_settings' in sql and 'CROSS JOIN pg_catalog.pg_database' in sql
    assert 'COALESCE' not in sql and 'pg_read_all_settings' not in sql
    result=i.rows('settings',setting_records())
    assert {r['name'] for r in result}==TWELVE_SETTINGS
    # An actual empty string is a valid setting; it is distinct from unavailable.
    result[0]['setting']=''
    assert i.support.settings_inventory(result)[result[0]['name']]==''


@pytest.mark.parametrize('missing',sorted(TWELVE_SETTINGS))
def test_settings_each_missing_name_refuses(missing):
    values=[r for r in setting_records() if r['name']!=missing]
    with pytest.raises(h.PrerequisiteRefused,match='SETTINGS_COVERAGE_INCOMPLETE'):
        i.rows('settings',values)


@pytest.mark.parametrize('duplicate',sorted(TWELVE_SETTINGS))
def test_settings_duplicate_name_refuses_even_different_values(duplicate):
    values=setting_records()+[dict(name=duplicate,setting='different')]
    with pytest.raises(h.PrerequisiteRefused,match='SETTINGS_DUPLICATE'):
        i.rows('settings',values)


def test_settings_original_eight_and_restricted_nulls_never_confirm():
    original=[r for r in setting_records() if r['name'] in EIGHT_VISIBLE_GUCS]
    assert len(original)==8
    with pytest.raises(h.PrerequisiteRefused,match='SETTINGS_COVERAGE_INCOMPLETE'):
        i.rows('settings',original)
    nominal=setting_records()
    for r in nominal:
        if r['name'] in {'shared_preload_libraries','session_preload_libraries'}:r['setting']=None
    assert len(nominal)==12
    with pytest.raises(h.MissingParameter,match='trusted_observation') as error:
        i.rows('settings',nominal)
    assert 'shared_preload_libraries' in str(error.value) and 'session_preload_libraries' in str(error.value)


def test_settings_unavailable_and_wrong_types_are_not_empty_values():
    values=setting_records();values[0]['setting']=None
    with pytest.raises(h.MissingParameter):i.rows('settings',values)
    values=setting_records();values[0]['setting']=False
    with pytest.raises(h.PrerequisiteRefused):i.rows('settings',values)
