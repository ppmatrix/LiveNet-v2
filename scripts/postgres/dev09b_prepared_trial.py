"""Prepared-origin local trial candidate. No operational DEV09B authority.

Inert on import. Only an explicit future CLI invocation reads Docker/SQL. Admin
observations are private, target-bound and compared with pre-supplied expectations;
ADMIN_SESSION settings are NEVER promoted to observed probe-session settings.
"""
import argparse
from hashlib import sha256
import json
import re
from pathlib import Path

from scripts.postgres import dev09b_querytrial_launcher as l
from scripts.postgres import dev09b_query_trial as trial
from backend.migrations.dev09b_inspection_support import SETTINGS_NAMES

SQL_PATH=l.ROOT/'scripts/postgres/dev09b_querytrial_schemas.proposed.sql'
RESTRICTED=('shared_preload_libraries','session_preload_libraries')
ADMIN_SQL="""BEGIN TRANSACTION READ ONLY;
SET LOCAL statement_timeout='3s';
SET LOCAL lock_timeout='500ms';
SELECT pg_catalog.json_build_object(
 'database',pg_catalog.current_database(),'system_identifier',s.system_identifier::pg_catalog.text,
 'postmaster_start',pg_catalog.pg_postmaster_start_time()::pg_catalog.text,
 'current_user',current_user,'session_user',session_user,
 'pid',pg_catalog.pg_backend_pid(),'backend_start',a.backend_start::pg_catalog.text,
 'settings',(SELECT pg_catalog.json_agg(pg_catalog.json_build_object('name',name,'setting',setting) ORDER BY name)
             FROM pg_catalog.pg_settings WHERE name IN ('shared_preload_libraries','session_preload_libraries')))
FROM pg_catalog.pg_control_system() s JOIN pg_catalog.pg_stat_activity a ON a.pid=pg_catalog.pg_backend_pid();
ROLLBACK;
"""
META_SQL="""SELECT pg_catalog.current_database() AS database,s.system_identifier::pg_catalog.text AS system_identifier,
 pg_catalog.pg_postmaster_start_time()::pg_catalog.text AS postmaster_start,
 pg_catalog.pg_backend_pid() AS pid,a.backend_start::pg_catalog.text AS backend_start,
 current_user AS current_user,session_user AS session_user,
 (SELECT pg_catalog.json_agg(pg_catalog.json_build_object('name',rolname,'login',rolcanlogin,
 'superuser',rolsuper,'createdb',rolcreatedb,'createrole',rolcreaterole,'replication',rolreplication,
 'bypassrls',rolbypassrls,'inherit',rolinherit) ORDER BY rolname)
 FROM pg_catalog.pg_roles WHERE rolname IN
 ('dev09b_trial_inventory_owner','dev09b_trial_audit_owner','dev09b_trial_security_owner')) AS owners,
 (SELECT COALESCE(pg_catalog.json_agg(pg_catalog.json_build_object('role',pg_catalog.pg_get_userbyid(m.roleid),'member',pg_catalog.pg_get_userbyid(m.member))),'[]'::pg_catalog.json)
 FROM pg_catalog.pg_auth_members m JOIN pg_catalog.pg_roles r ON r.oid=m.roleid OR r.oid=m.member
 WHERE r.rolname IN ('dev09b_trial_inventory_owner','dev09b_trial_audit_owner','dev09b_trial_security_owner')) AS owner_memberships
FROM pg_catalog.pg_control_system() s JOIN pg_catalog.pg_stat_activity a ON a.pid=pg_catalog.pg_backend_pid()"""


def require(value,code):l.require(value,code)


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()


def parse(raw):
    def pairs(items):
        result={}
        for key,value in items:
            require(key not in result,'DUPLICATE_JSON_FIELD');result[key]=value
        return result
    return json.loads(raw,object_pairs_hook=pairs)


def expectations(raw):
    e=parse(raw)
    require(type(e) is dict and set(e)=={'schema_version','status','target','sql_sha256','query_catalog_sha256','admin_settings','probe_settings','schema_owners','extension'},'EXPECTATION_SCHEMA')
    require(type(e['schema_version']) is int and e['schema_version']==1 and e['status']=='PROPOSED_NOT_APPROVED','EXPECTATION_VERSION')
    require(e['target']==dict(project=l.PROJECT,database=l.DATABASE,system_identifier='7705421224394444834',image=l.IMAGE),'EXPECTED_TARGET_REQUIRED')
    for key in ('sql_sha256','query_catalog_sha256'):
        require(type(e[key]) is str and re.fullmatch('[0-9a-f]{64}',e[key]),'EXPECTATION_DIGEST')
    require(e['query_catalog_sha256']==trial.CATALOG_SHA256,'QUERY_CATALOG_DIVERGENCE')
    require(sha256(SQL_PATH.read_bytes()).hexdigest()==e['sql_sha256'],'SQL_BYTES_DIVERGENCE')
    require(type(e['admin_settings']) is dict and set(e['admin_settings'])==set(RESTRICTED),'ADMIN_EXPECTATION_COVERAGE')
    require(type(e['probe_settings']) is dict and set(e['probe_settings'])==set(SETTINGS_NAMES),'PROBE_EXPECTATION_COVERAGE')
    for scope in ('admin_settings','probe_settings'):
        for key,value in e[scope].items():
            require(type(value) is str,'MISSING_EXPECTATION_'+key.upper())
    require(e['probe_settings']['shared_preload_libraries']==e['admin_settings']['shared_preload_libraries'],'SERVER_EXPECTATION_DIVERGENCE')
    require(e['schema_owners']==dict(inventory='dev09b_trial_inventory_owner',audit='dev09b_trial_audit_owner',security='dev09b_trial_security_owner'),'OWNER_EXPECTATIONS')
    require(e['extension']==dict(name='btree_gist',version='1.7',schema='public',owner=l.ADMIN),'EXTENSION_EXPECTATIONS')
    return e


def record_matches(record,e):
    require(record['system_identifier']==e['target']['system_identifier'] and record['image_id']
            and record['channel']=='docker-exec-pg_controldata','RECORD_TARGET_DIVERGENCE')


def settings_map(rows,names,*,nullable):
    require(type(rows) is list,'SETTING_ROWS_REQUIRED')
    result={}
    for row in rows:
        require(type(row) is dict and set(row)=={'name','setting'} and type(row['name']) is str
                and row['name'] in names and row['name'] not in result,'SETTING_NAME_COVERAGE')
        value=row['setting'];require(type(value) is str or nullable and value is None,'SETTING_TYPE')
        result[row['name']]=value
    require(set(result)==set(names),'SETTING_NAME_COVERAGE')
    return result


def compare_admin(evidence,e,record):
    require(type(evidence) is dict and set(evidence)=={'schema_version','scope','channel','operational_authority','record_sha256','expectations_sha256','observation'},'ADMIN_EVIDENCE_SCHEMA')
    require(type(evidence['schema_version']) is int and evidence['schema_version']==1
            and evidence['scope']=='LOCAL_ADMIN_TRIAL_OBSERVATION' and evidence['channel']=='docker-exec-psql'
            and evidence['operational_authority'] is False,'NOT_OPERATIONAL_AUTHORITY')
    require(evidence['record_sha256']==sha256(canonical(record)).hexdigest()
            and evidence['expectations_sha256']==sha256(canonical(e)).hexdigest(),'ADMIN_EVIDENCE_BINDING')
    o=evidence['observation']
    require(type(o) is dict and set(o)=={'database','system_identifier','postmaster_start','current_user','session_user','pid','backend_start','settings'},'ADMIN_OBSERVATION_SCHEMA')
    require(o['database']==l.DATABASE and o['system_identifier']==record['system_identifier']
            and o['current_user']==o['session_user']==l.ADMIN,'ADMIN_TARGET_DIVERGENCE')
    require(type(o['pid']) is int and o['pid']>0 and all(type(o[k]) is str and bool(o[k]) for k in ('postmaster_start','backend_start')),'ADMIN_SESSION_BINDING')
    values=settings_map(o['settings'],RESTRICTED,nullable=False)
    require(values==e['admin_settings'],'ADMIN_SETTINGS_MISMATCH')
    return o


def admin_psql(record,sql):
    l.password(l.state_dir()/'admin_password')  # Private mode/owner, no value emitted.
    shell='unset PGSERVICE PGSERVICEFILE PGOPTIONS PGPASSFILE; PGPASSWORD="$(cat /run/secrets/querytrial_admin_password)"; export PGPASSWORD; exec psql -X -q -A -t -v ON_ERROR_STOP=1 -h /var/run/postgresql -p 5432 -U '+l.ADMIN+' -d '+l.DATABASE
    return l.command(['docker','exec','-i','--user','root',record['container_id'],'sh','-c',shell],input=sql)


def collect_admin(record,e):
    confirmed=record['system_identifier']
    require(l.checked_record(confirmed)==record,'TARGET_CHANGED')
    raw=admin_psql(record,ADMIN_SQL)
    o=parse(raw.strip())
    evidence=dict(schema_version=1,scope='LOCAL_ADMIN_TRIAL_OBSERVATION',channel='docker-exec-psql',operational_authority=False,
        record_sha256=sha256(canonical(record)).hexdigest(),expectations_sha256=sha256(canonical(e)).hexdigest(),observation=o)
    compare_admin(evidence,e,record)
    require(l.checked_record(confirmed)==record,'TARGET_CHANGED')
    return evidence


def apply_preparation(record,e):
    data=SQL_PATH.read_bytes()
    require(sha256(data).hexdigest()==e['sql_sha256'],'SQL_BYTES_DIVERGENCE')
    require(l.checked_record(record['system_identifier'])==record,'TARGET_CHANGED')
    # Fixed reviewed file only; SID is nonsensitive and previously decimal-validated.
    prefix='\\set confirmed_system_identifier '+record['system_identifier']+'\n'
    admin_psql(record,prefix+data.decode())


class CaptureConnection(l.ObservedConnection):
    """Captures selected rows in memory only; runner enforces byte/row limits."""
    selected=frozenset({'identity','settings','schemas','schema_acl','extension','extension_acl','namespace_objects','privileges','memberships'})
    def __init__(self,connection):super().__init__(connection);self.snapshots={}
    def execute(self,statement,**kwargs):
        key=next((k for k,q in trial.QUERIES.items() if q.sql==str(statement)),None)
        result=super().execute(statement,**kwargs)
        if key not in self.selected:return result
        captured=[];self.snapshots.setdefault(key,[]).append(captured)
        class Rows:
            def mappings(self):
                for row in result.mappings():
                    captured.append(trial._row_dict(row));yield row
            def close(self):return result.close()
        return Rows()


def probe_meta(connection):
    connection.begin()
    try:
        for sql in ('SET TRANSACTION READ ONLY','SET LOCAL statement_timeout = 3000','SET LOCAL lock_timeout = 500'):
            connection.execute(trial.text(sql)).close()
        result=connection.execute(trial.text(META_SQL))
        try:rows=[dict(r) for r in result.mappings()]
        finally:result.close()
        require(len(rows)==1,'PROBE_METADATA_CARDINALITY')
        return rows[0]
    finally:connection.rollback()


def compare_prepared(e,record,admin_before,admin_after,meta,snapshots):
    before=compare_admin(admin_before,e,record);after=compare_admin(admin_after,e,record)
    for o in (before,after,meta):
        require(o['database']==l.DATABASE and o['system_identifier']==record['system_identifier']
                and o['postmaster_start']==before['postmaster_start'],'SERVER_CONTINUITY_DIVERGENCE')
    require(type(meta['pid']) is int and meta['pid']>0 and type(meta['backend_start']) is str and bool(meta['backend_start']),'PROBE_SESSION_CHANGED')
    require(meta['current_user']==meta['session_user']==l.PROBE and meta['pid']!=before['pid']
            and meta['pid']!=after['pid'],'INDEPENDENT_PROBE_CONNECTION_REQUIRED')
    identities=snapshots['identity'];require(len(identities)==2,'PROBE_IDENTITY_COVERAGE')
    for values in identities:
        require(len(values)==1 and values[0]['pid']==meta['pid'] and values[0]['backend_start']==meta['backend_start'],'PROBE_SESSION_CHANGED')
    def one(name):
        require(name in snapshots and len(snapshots[name])==1,'PROBE_QUERY_COVERAGE');return snapshots[name][0]
    observed=settings_map(one('settings'),SETTINGS_NAMES,nullable=True)
    for name,value in observed.items():
        if value is None:require(name in RESTRICTED,'UNEXPECTED_SETTING_UNAVAILABLE')
        else:require(value==e['probe_settings'][name],'PROBE_SETTINGS_MISMATCH')
    # No copying admin values into this map. Admin's session_preload is NOT the
    # setting of meta.pid. Shared preload is separately observed at server scope.
    require(meta['owner_memberships']==[],'OWNER_MEMBERSHIP_DIVERGENCE')
    owners=meta['owners'];require(type(owners) is list and len(owners)==3,'OWNER_COVERAGE')
    require({o['name'] for o in owners}==set(e['schema_owners'].values()),'OWNER_COVERAGE')
    for o in owners:
        require(set(o)=={'name','login','superuser','createdb','createrole','replication','bypassrls','inherit'}
                and all(v is False for k,v in o.items() if k!='name'),'OWNER_POWER_DIVERGENCE')
    schema_rows=one('schemas')
    schemas={r['name']:r for r in schema_rows}
    require(len(schemas)==len(schema_rows),'SCHEMA_OWNER_DIVERGENCE')
    for name,owner in e['schema_owners'].items():
        require(name in schemas and schemas[name]['owner']==owner and schemas[name]['owner_login'] is False,'SCHEMA_OWNER_DIVERGENCE')
        require(all(schemas[name][k] is False for k in ('can_create','can_use','grant_create','grant_use')),'SCHEMA_ACL_DIVERGENCE')
    require(all(row['can_create'] is False for row in schemas.values()),'PROBE_POWER_DIVERGENCE')
    schema_acl=one('schema_acl')
    for name,owner in e['schema_owners'].items():
        rights=[r for r in schema_acl if r['name']==name]
        require(len(rights)==2 and {r['privilege'] for r in rights}=={'USAGE','CREATE'}
                and all(r['grantee']==r['grantor']==owner and r['grant_option'] is False for r in rights),'SCHEMA_ACL_DIVERGENCE')
    require(not any(r['schema'] in e['schema_owners'] for r in one('namespace_objects')),'MANAGED_SCHEMA_RESIDUE')
    ext=[r for r in one('extension') if r['name']=='btree_gist']
    require(ext==[e['extension']],'EXTENSION_DIVERGENCE')
    ext_acl=[r for r in one('extension_acl') if r['extension']=='btree_gist']
    require(ext_acl and all(r['grantee']==r['grantor']==l.ADMIN and r['privilege'] in {'EXECUTE','USAGE'} and r['grant_option'] is False for r in ext_acl),'EXTENSION_ACL_DIVERGENCE')
    privileges=one('privileges');require(len(privileges)==1 and all(v is False for v in privileges[0].values()),'PROBE_POWER_DIVERGENCE')
    memberships=one('memberships')
    require(set(e['schema_owners'].values())|{l.ADMIN} <= {r['role'] for r in memberships}
            and all(r[k] is False for r in memberships for k in ('member','inherited','can_set')),'PROBE_MEMBERSHIP_DIVERGENCE')
    return dict(status='LOCAL_PREPARED_TRIAL_MATCHED',operational_authority=False,
        shared_preload_libraries='SERVER_OBSERVATION_MATCHED',
        session_preload_libraries_admin='ADMIN_SESSION_MATCHED_ONLY',
        session_preload_libraries_probe='UNOBSERVED' if observed['session_preload_libraries'] is None else 'PROBE_OBSERVATION_MATCHED',
        probe_unavailable=[n for n in SETTINGS_NAMES if observed[n] is None],
        full_operational_profile_validated=False)


def safe_failure(phase,exc):
    codes={'DUPLICATE_JSON_FIELD','EXPECTATION_SCHEMA','EXPECTATION_VERSION','EXPECTED_TARGET_REQUIRED',
           'EXPECTATION_DIGEST','QUERY_CATALOG_DIVERGENCE','ADMIN_EXPECTATION_COVERAGE','PROBE_EXPECTATION_COVERAGE',
           'SERVER_EXPECTATION_DIVERGENCE','OWNER_EXPECTATIONS','EXTENSION_EXPECTATIONS','SQL_BYTES_DIVERGENCE',
           'RECORD_TARGET_DIVERGENCE','SETTING_ROWS_REQUIRED','SETTING_NAME_COVERAGE','SETTING_TYPE',
           'ADMIN_EVIDENCE_SCHEMA','NOT_OPERATIONAL_AUTHORITY','ADMIN_EVIDENCE_BINDING','ADMIN_OBSERVATION_SCHEMA',
           'ADMIN_TARGET_DIVERGENCE','ADMIN_SESSION_BINDING','ADMIN_SETTINGS_MISMATCH','TARGET_CHANGED',
           'PROBE_METADATA_CARDINALITY','SERVER_CONTINUITY_DIVERGENCE','INDEPENDENT_PROBE_CONNECTION_REQUIRED',
           'PROBE_IDENTITY_COVERAGE','PROBE_SESSION_CHANGED','PROBE_QUERY_COVERAGE','UNEXPECTED_SETTING_UNAVAILABLE',
           'PROBE_SETTINGS_MISMATCH','OWNER_MEMBERSHIP_DIVERGENCE','OWNER_COVERAGE','OWNER_POWER_DIVERGENCE',
           'SCHEMA_OWNER_DIVERGENCE','SCHEMA_ACL_DIVERGENCE','MANAGED_SCHEMA_RESIDUE','EXTENSION_DIVERGENCE',
           'EXTENSION_ACL_DIVERGENCE','PROBE_POWER_DIVERGENCE','PROBE_MEMBERSHIP_DIVERGENCE',
           'SID_CONFIRMATION_REQUIRED','INVALID_TRIAL_ID','REPORT_ALREADY_EXISTS','INDEPENDENT_SID_DIVERGENCE',
           'PROBE_QUERY_TRIAL_REFUSED','STOP_OWNERSHIP_DIVERGENCE','EXPLICIT_SQL_ACTION_REQUIRED','COMMAND_FAILED'}
    codes.update('MISSING_EXPECTATION_'+name.upper() for name in SETTINGS_NAMES)
    code=exc.args[0] if type(exc) is l.Refused and exc.args and type(exc.args[0]) is str and exc.args[0] in codes else 'PREPARED_TRIAL_REFUSED'
    return trial._safe_diagnostic(phase,code,exc)


def execute(expectation_file,confirm,trial_id):
    # Explicit future execution only. NEVER called by import/construction/tests
    # without injected doubles. No start/create/pull/build operation exists here.
    e=expectations(Path(expectation_file).read_bytes())
    require(confirm==e['target']['system_identifier'],'SID_CONFIRMATION_REQUIRED')
    require(re.fullmatch('[a-zA-Z0-9-]{1,32}',trial_id) is not None,'INVALID_TRIAL_ID')
    state=l.state_dir();l.private_dir(state)
    names=[f'prepared-{trial_id}-{suffix}.json' for suffix in ('admin-before','admin-after','report','probe')]
    require(not any((state/name).exists() for name in names),'REPORT_ALREADY_EXISTS')
    record=l.checked_record(confirm)
    record_matches(record,e)
    phase='independent_identity';result=None
    try:
        raw=l.command(['docker','exec','--user','postgres','--env','LC_ALL=C',record['container_id'],'pg_controldata','/var/lib/postgresql/data'])
        require(re.findall(r'^Database system identifier:\s*([1-9][0-9]{0,19})\s*$',raw,re.M)==[confirm],'INDEPENDENT_SID_DIVERGENCE')
        phase='admin_before';before=collect_admin(record,e)
        l.write_new(state/names[0],canonical(before)+b'\n')
        phase='apply_proposed_sql';apply_preparation(record,e)
        phase='independent_probe'
        from sqlalchemy import create_engine
        from sqlalchemy.engine import URL
        from sqlalchemy.pool import NullPool
        engine=create_engine(URL.create('postgresql+psycopg',username=l.PROBE,password=l.password(state/'probe_password'),host=record['address'],port=5432,database=l.DATABASE),
                             echo=False,hide_parameters=True,poolclass=NullPool,connect_args={'connect_timeout':5,'sslmode':'disable','gssencmode':'disable'})
        connection=None
        try:
            connection=CaptureConnection(engine.connect());meta=probe_meta(connection)
            report=trial.run_trial(connection,trial.TrialTarget(l.DATABASE,confirm,l.PROBE,record['address']))
            snapshots=connection.snapshots
            probe_evidence=dict(scope='LOCAL_PROBE_TRIAL_OBSERVATION',operational_authority=False,
                record_sha256=sha256(canonical(record)).hexdigest(),expectations_sha256=sha256(canonical(e)).hexdigest(),
                metadata=meta,observations=snapshots,trial=json.loads(report.to_json()),query_errors=connection.errors)
            l.write_new(state/names[3],canonical(probe_evidence)+b'\n')
            require(report.status=='COMPLETED','PROBE_QUERY_TRIAL_REFUSED')
        finally:
            if connection is not None and connection.closed is False:
                try:connection.rollback()
                finally:connection.close()
            engine.dispose()
        phase='admin_after';after=collect_admin(record,e)
        l.write_new(state/names[1],canonical(after)+b'\n')
        phase='compare';comparison=compare_prepared(e,record,before,after,meta,snapshots)
        result=dict(scope='LOCAL_PREPARED_TRIAL_ONLY',trial=json.loads(report.to_json()),comparison=comparison)
        return result
    except Exception as exc:
        result=dict(scope='LOCAL_PREPARED_TRIAL_ONLY',status='REFUSED',diagnostic=safe_failure(phase,exc))
        # Only fixed phase/code/class; not raw exception messages/rows/settings.
        return result
    finally:
        try:
            obj=l.docker_json('inspect',record['container_id'])[0]
            require(obj['Config']['Labels'].get('com.docker.compose.project')==l.PROJECT,'STOP_OWNERSHIP_DIVERGENCE')
            if obj['State']['Running']:l.command(['docker','stop','--time','10',record['container_id']])
            stopped=l.docker_json('inspect',record['container_id'])[0]['State']['Running'] is False
            if result is not None:result['container_stopped']=stopped
        except Exception:
            if result is not None:result['container_stopped']=False;result['status']='REFUSED'
        if result is not None:l.write_new(state/names[2],canonical(result)+b'\n')


def main(argv=None):
    p=argparse.ArgumentParser(description='Future local prepared trial, never operational DEV09B approval')
    p.add_argument('--expectations',required=True);p.add_argument('--confirm-system-identifier',required=True)
    p.add_argument('--trial-id',required=True);p.add_argument('--apply-proposed-sql',action='store_true')
    p.add_argument('--validate-only',action='store_true')
    args=p.parse_args(argv)
    try:
        if args.validate_only:
            require(not args.apply_proposed_sql,'EXPLICIT_SQL_ACTION_REQUIRED')
            e=expectations(Path(args.expectations).read_bytes())
            require(args.confirm_system_identifier==e['target']['system_identifier'],'SID_CONFIRMATION_REQUIRED')
            print(json.dumps(dict(status='EXPECTATIONS_STRUCTURALLY_VALIDATED',operational_authority=False)))
            return 0
        require(args.apply_proposed_sql,'EXPLICIT_SQL_ACTION_REQUIRED')
        result=execute(args.expectations,args.confirm_system_identifier,args.trial_id)
        print(json.dumps(result,sort_keys=True));return 2 if result.get('status')=='REFUSED' or not result.get('container_stopped') else 0
    except Exception as exc:
        print(json.dumps(dict(status='REFUSED',diagnostic=safe_failure('preflight',exc))))
        return 2


if __name__=='__main__':raise SystemExit(main())
