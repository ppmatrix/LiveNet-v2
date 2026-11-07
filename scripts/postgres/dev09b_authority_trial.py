"""Explicit disposable AUTHORITY STORAGE trial; inert until CLI invocation.

Synthetic storage records are deliberately INVALID DEV09B envelopes. Positive
cases exercise the production _locked transaction boundary and fixed SQL, NOT
public consume() eligibility, authenticated receipts or ApplicationTransport.
No monkeypatch, validator bypass, operational approval, migrator or LiveNet DSN.
A local file interlock / system clock here are trial instrumentation, not approved
operational continuity / time. Fault injection drops a response after commit;
it does not simulate a TCP failure during COMMIT or prove power-loss recovery.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from hashlib import sha256
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
from threading import Barrier, Lock
import time
from types import SimpleNamespace
from uuid import UUID, uuid4

from sqlalchemy import create_engine, text, event
from sqlalchemy.engine import URL
from sqlalchemy.pool import NullPool

from scripts.postgres import dev09b_querytrial_launcher as q
from scripts.dedicated.dev09b import codec as c, postgres_authority as a
from scripts.dedicated.dev09b.model import ContinuitySample, TimeSample, SessionBinding

ROOT=q.ROOT
PROJECT='livenetv2-dev09b-authoritytrial'
DATABASE='dev09b_authority_trial'
ADMIN='dev09b_authority_trial_admin'
ROLES={name:'dev09b_authority_trial_'+name for name in ('service','revoker','observer')}
TOKEN='00000000-0000-0000-0000-000000000384'
MARKER=c.canonical({'classification':'SYNTHETIC_STORAGE_TRIAL','not_an_approval':True})
SESSION=SessionBinding('0'*64,'1'*64,str(UUID(int=3)),1,0,'1')
SCHEMA=ROOT/'scripts/postgres/dev09b_authority_schema.proposed.sql'
ADMIN_SQL=ROOT/'scripts/postgres/dev09b_authoritytrial_admin.proposed.sql'
HBA=ROOT/'scripts/postgres/dev09b_authoritytrial.pg_hba.conf'
COMPOSE=ROOT/'compose.dev09b-authoritytrial.yaml'
# Reviewed candidates only; not approval of bundle, dependencies or operation.
PINS = {'scripts/postgres/dev09b_authority_schema.proposed.sql': '05620cc0efc40f579ec4883d2a42bf9306a5f75016e173c3ca57cf71f402aae2', 'scripts/postgres/dev09b_authoritytrial_admin.proposed.sql': '6287e8a7d304fef0b6f205e948c6384a78383fbfc15cbf63bace3073058b0e41', 'scripts/postgres/dev09b_authoritytrial.pg_hba.conf': '970c0ab6b97edcdc6108d21526d3acf176c722ea8d351a702bf82a9fff76c1e7', 'compose.dev09b-authoritytrial.yaml': 'e3bbf195b1c3fe48a5c73cbec43070f00aa103fa908f8188e158a6e5cbfab0ad'}


def require(value, code):q.require(value,code)


def state():
    raw=os.environ.get('DEV09B_AUTHORITYTRIAL_STATE_DIR','')
    p=Path(raw)
    require(p.is_absolute() and '..' not in p.parts and p!=ROOT and ROOT not in p.parents,'PRIVATE_OUTSIDE_GIT_REQUIRED')
    for parent in (p,*p.parents):require(not parent.is_symlink() and not (parent/'.git').exists(),'PRIVATE_PATH_REFUSED')
    return p


def validate():
    for path,digest in PINS.items():require(sha256((ROOT/path).read_bytes()).hexdigest()==digest,'TRIAL_SOURCE_DIVERGENCE')
    cfg=json.loads(COMPOSE.read_bytes());service=cfg['services']['db']
    require(cfg['name']==PROJECT and service['image']==q.IMAGE and service['pull_policy']=='never','IMAGE_PROJECT_DIVERGENCE')
    require('ports' not in service and set(cfg['networks'])=={'backend'} and cfg['networks']['backend']['internal'] is True,'ISOLATION_DIVERGENCE')
    return cfg


def make_secrets():
    p=state();p.mkdir(parents=True,exist_ok=True,mode=0o700);q.private_dir(p)
    require(not any(p.iterdir()),'NEW_PRIVATE_DIRECTORY_REQUIRED')
    for name in ('admin',*ROLES):q.write_new(p/(name+'_password'),secrets.token_urlsafe(48).encode())


def preflight():
    validate();q.host_image()
    require(not q.command(['docker','ps','-aq','--filter','label=com.docker.compose.project='+PROJECT]).strip(),'PROJECT_COLLISION')
    for kind,name in [('network',PROJECT+'_backend'),('volume',PROJECT+'_data')]:
        rows=q.command(['docker',kind,'ls','--format','{{.Name}}']).splitlines()
        require(name not in rows,'RESOURCE_COLLISION')


def topology():
    validate();image=q.host_image()
    ids=q.command(['docker','ps','-q','--filter','label=com.docker.compose.project='+PROJECT]).split()
    require(len(ids)==1,'ONE_AUTHORITY_CONTAINER_REQUIRED')
    db=q.docker_json('inspect',ids[0])[0]
    labels=db['Config']['Labels']
    require(labels.get('com.docker.compose.service')=='db' and labels.get('com.docker.compose.project.working_dir')==str(ROOT),'PROVENANCE_DIVERGENCE')
    require(db['State']['Running'] is True and db['Image']==image['Id'] and not db['HostConfig'].get('Privileged')
            and not db['HostConfig'].get('PortBindings') and not any(db['NetworkSettings'].get('Ports',{}).values()),'CONTAINER_ISOLATION')
    name=PROJECT+'_backend';require(set(db['NetworkSettings']['Networks'])=={name},'NETWORK_DIVERGENCE')
    net=q.docker_json('network','inspect',name)[0]
    require(net['Internal'] is True and net['Driver']=='bridge' and net['Labels'].get('com.docker.compose.project')==PROJECT
            and len(net['Containers'])==1,'OWNED_ISOLATED_NETWORK_REQUIRED')
    endpoint=db['NetworkSettings']['Networks'][name]
    require(endpoint['NetworkID']==net['Id'],'NETWORK_ID_DIVERGENCE')
    address=str(ipaddress.IPv4Address(endpoint['IPAddress']))
    route=json.loads(q.command(['ip','-j','route','get',address]))
    bridge=net.get('Options',{}).get('com.docker.network.bridge.name') or 'br-'+net['Id'][:12]
    require(len(route)==1 and route[0].get('dev')==bridge and not route[0].get('gateway'),'DIRECT_HOST_ROUTE_REQUIRED')
    mounts={m['Destination']:m for m in db['Mounts']}
    require(set(mounts)=={'/var/lib/postgresql/data','/run/secrets/authoritytrial_admin_password','/etc/postgresql/authoritytrial.pg_hba.conf'},'MOUNT_DIVERGENCE')
    volume=mounts['/var/lib/postgresql/data']
    require(volume['Type']=='volume' and volume['Name']==PROJECT+'_data','VOLUME_DIVERGENCE')
    metadata=q.docker_json('volume','inspect',volume['Name'])[0]
    require(metadata['Labels'].get('com.docker.compose.project')==PROJECT,'VOLUME_PROVENANCE')
    for destination,source in [('/run/secrets/authoritytrial_admin_password',state()/'admin_password'),('/etc/postgresql/authoritytrial.pg_hba.conf',HBA)]:
        require(mounts[destination]['Source']==str(source) and mounts[destination]['RW'] is False,'BIND_SOURCE_DIVERGENCE')
    return dict(container_id=db['Id'],image_id=image['Id'],network_id=net['Id'],address=address,volume=volume['Name'],volume_created=metadata['CreatedAt'])


def identify():
    binding=topology()
    output=q.command(['docker','exec','--user','postgres','--env','LC_ALL=C',binding['container_id'],'pg_controldata','/var/lib/postgresql/data'])
    sid=re.findall(r'^Database system identifier:\s*([1-9][0-9]{0,19})\s*$',output,re.M)
    require(len(sid)==1 and int(sid[0])<=2**64-1,'CONTROL_ID_REQUIRED')
    record=dict(system_identifier=sid[0],channel='docker-pg_controldata-storage-trial-only',**binding)
    q.write_new(state()/'identity.json',(json.dumps(record,sort_keys=True)+'\n').encode())
    print('system_identifier='+sid[0])  # identity only, never credentials/rows


def checked(confirm):
    record=json.loads(q.read_private(state()/'identity.json'))
    require(type(confirm) is str and confirm==record['system_identifier'] and confirm!='7705421224394444834','INDEPENDENT_AUTHORITY_SID_REQUIRED')
    require(all(record[k]==v for k,v in topology().items()),'RESOURCE_CHANGED')
    return record


class AdminFailure(q.Refused):
    """Only closed diagnostics survive; never retain stdout/stderr/SQL in errors."""
    def __init__(self, diagnostic):
        self.diagnostic=diagnostic
        super().__init__(diagnostic['code'])


def instrument_admin_sql(sql):
    # Only our fixed generated scripts: top-level statements start on new lines.
    # DO blocks, literals and schema bodies are preserved byte-for-byte. This is
    # deliberately NOT an arbitrary SQL parser or permission-control mechanism.
    families=('BEGIN','SET LOCAL','DO','REVOKE','CREATE ROLE','CREATE SCHEMA',
              'CREATE TABLE','ALTER SCHEMA','ALTER TABLE','GRANT','INSERT INTO','COMMIT')
    lines=[];identifiers=[]
    for line in sql.splitlines():
        family=next((f for f in families if re.match('^'+f+r'\b',line)),None)
        if family:
            identifier='S%03d_'%(len(identifiers)+1)+family.replace(' ','_')
            identifiers.append(identifier)
            lines.append(r'\echo DEV09B_STATEMENT:'+identifier)
        lines.append(line)
    require(identifiers and identifiers[0].endswith('_BEGIN') and identifiers[-1].endswith('_COMMIT'),'ADMIN_SCRIPT_LAYOUT')
    return '\n'.join(lines)+'\n',identifiers


def admin_diagnostic(phase,returncode,stdout,stderr,identifiers):
    # Ignore all non-whitelisted output, including SQL echoed by a client error.
    markers=re.findall(r'^DEV09B_STATEMENT:(S[0-9]{3}_[A-Z_]+)\s*$',stdout,re.M)
    markers=[m for m in markers if m in identifiers]
    states=re.findall(r'^(?:psql:[^\n]*:\s*)?(?:ERROR|FATAL|PANIC):\s*([0-9A-Z]{5})\s*$',stderr,re.M)
    code='ADMIN_STATEMENT_FAILED' if markers else 'ADMIN_CONNECTION_FAILED'
    if 'DEV09B_PRECONNECT:SECRET_UNREADABLE' in stderr:code='ADMIN_SECRET_UNREADABLE'
    if 'DEV09B_PRECONNECT:SECRET_READ_FAILED' in stderr:code='ADMIN_SECRET_READ_FAILED'
    if len(stdout)>2*1024*1024 or len(stderr)>2*1024*1024:code='ADMIN_OUTPUT_LIMIT'
    return dict(phase=phase if markers else 'administrative_connect',sqlstate=states[-1] if states else None,
                statement_id=markers[-1] if markers else None,code=code,exit_code=returncode)


def run_admin_command(args,sql,phase,identifiers):
    require(not any(os.environ.get(k) for k in ('DOCKER_HOST','DOCKER_CONTEXT','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH')),'DOCKER_ENV_OVERRIDE')
    require(args[:1]==['docker'],'LOCAL_DOCKER_REQUIRED')
    try:
        result=subprocess.run(['docker','--context','default',*args[1:]],input=sql,text=True,
                              stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30,check=False)
    except subprocess.TimeoutExpired as exc:
        def decoded(value):return value.decode('utf8',errors='replace') if isinstance(value,bytes) else value or ''
        diagnostic=admin_diagnostic(phase,None,decoded(exc.stdout),decoded(exc.stderr),identifiers)
        diagnostic['code']='ADMIN_TIMEOUT_RESULT_UNCERTAIN'
        raise AdminFailure(diagnostic) from None
    except OSError:
        raise AdminFailure(dict(phase='administrative_connect',sqlstate=None,statement_id=None,code='ADMIN_PROCESS_FAILED',exit_code=None)) from None
    if result.returncode or len(result.stdout)>2*1024*1024 or len(result.stderr)>2*1024*1024:
        raise AdminFailure(admin_diagnostic(phase,result.returncode,result.stdout,result.stderr,identifiers)) from None
    if ('DEV09B_STATEMENT:'+identifiers[-1]) not in result.stdout.splitlines():
        diagnostic=admin_diagnostic(phase,result.returncode,result.stdout,result.stderr,identifiers)
        diagnostic['code']='ADMIN_COMMIT_CONFIRMATION_MISSING'
        raise AdminFailure(diagnostic) from None


def admin(record,sql,*,phase='administrative_preparation'):
    require(phase in ('administrative_preparation','seed'),'ADMIN_PHASE')
    # Root reads the existing host-owned 0600 bind mount; no chmod/chown, new
    # credential, DB role elevation or grants. Same explicit PostgreSQL admin.
    # Separate assignment propagates cat failure; export would mask its status.
    shell=("unset PGSERVICE PGSERVICEFILE PGOPTIONS PGPASSFILE; "
           "if ! test -r /run/secrets/authoritytrial_admin_password; then "
           "printf 'DEV09B_PRECONNECT:SECRET_UNREADABLE\n' >&2; exit 78; fi; "
           'PGPASSWORD="$(cat /run/secrets/authoritytrial_admin_password)" || '
           "{ printf 'DEV09B_PRECONNECT:SECRET_READ_FAILED\n' >&2; exit 79; }; export PGPASSWORD; "
           'PGOPTIONS="-c statement_timeout=5000 -c lock_timeout=2000"; export PGOPTIONS; '
           "exec psql -X -q -w -v ON_ERROR_STOP=1 -v VERBOSITY=sqlstate "
           "-h /var/run/postgresql -p 5432 -U dev09b_authority_trial_admin -d dev09b_authority_trial")
    c.decimal64(record['system_identifier'])
    guard="DO $$ BEGIN IF current_database() <> 'dev09b_authority_trial' OR session_user <> 'dev09b_authority_trial_admin' OR (SELECT system_identifier::text FROM pg_catalog.pg_control_system()) <> '"+record['system_identifier']+"' THEN RAISE EXCEPTION 'ADMIN_IDENTITY_REFUSED'; END IF; END $$;"
    require('BEGIN;' in sql,'ADMIN_TRANSACTION_REQUIRED')
    sql=sql.replace('BEGIN;','BEGIN;\n'+guard,1)
    sql,identifiers=instrument_admin_sql(sql)
    try:
        run_admin_command(['docker','exec','-i','--user','root',record['container_id'],'sh','-eu','-c',shell],sql,phase,identifiers)
    except AdminFailure as exc:
        q.write_new(state()/('admin-diagnostic-'+str(uuid4())+'.json'),(json.dumps(exc.diagnostic,sort_keys=True)+'\n').encode())
        raise


def validate_resume_inspection(name,record):
    require(type(name) is str and re.fullmatch(r'diagnostic-inspection-[0-9]{2}\.json',name) is not None,'RESUME_INSPECTION_NAME')
    proof=json.loads(q.read_private(state()/name))
    require(proof.get('status')=='READ_ONLY_INSPECTION_RETURNED' and proof.get('container_final')=='exited'
            and proof.get('system_identifier')==record['system_identifier'],'RESUME_INSPECTION_REQUIRED')
    o=proof.get('observation',{})
    require(o.get('system_identifier')==record['system_identifier'] and o.get('database')==DATABASE and
            o.get('current_user')==ADMIN and o.get('session_user')==ADMIN and o.get('transaction_read_only')=='on','RESUME_INSPECTION_BINDING')
    require(o.get('authority_schema_count')==0 and o.get('authority_relations')==[] and o.get('target_memberships')==0
            and o.get('roles')==[dict(name=ADMIN,login=True,superuser=True)] and o.get('database_owner')==ADMIN
            and o.get('database_public_privileges')==['CONNECT','TEMPORARY']
            and o.get('public_schema')==dict(owner='pg_database_owner',acl='{pg_database_owner=UC/pg_database_owner,=U/pg_database_owner}'),'RESUME_PRISTINE_REQUIRED')
    require((state()/'admin-started').is_file() and not (state()/'run-started').exists()
            and not (state()/'quarantine').exists(),'RESUME_STAGE_REQUIRED')
    return 'admin-resume-started-'+name.removesuffix('.json')


def prepare(confirm,*,resume_inspection=None):
    record=checked(confirm);sql=ADMIN_SQL.read_text()
    sql=sql.replace('__AUTHORITY_SCHEMA__',SCHEMA.read_text())
    for role in ROLES:
        verifier=q.scram_verifier(q.password(state()/(role+'_password')))
        require("'" not in verifier and '\n' not in verifier,'SCRAM_ENCODING')
        sql=sql.replace('__'+role.upper()+'_SCRAM__',verifier)
    require('__' not in sql,'ADMIN_PLACEHOLDER')
    marker='admin-started' if resume_inspection is None else validate_resume_inspection(resume_inspection,record)
    # Recheck pristine essentials in the SAME future transaction, before REVOKE.
    # A stale inspection never authorizes repair or overwriting an existing role.
    pristine="""DO $$ BEGIN
 IF EXISTS(SELECT 1 FROM pg_catalog.pg_roles WHERE rolname IN
 ('dev09b_authority_trial_owner','dev09b_authority_trial_service','dev09b_authority_trial_revoker','dev09b_authority_trial_observer'))
 OR EXISTS(SELECT 1 FROM pg_catalog.pg_namespace WHERE nspname='dev09b_authority')
 OR NOT EXISTS(SELECT 1 FROM pg_catalog.pg_database WHERE datname=current_database() AND pg_get_userbyid(datdba)=session_user)
 OR NOT EXISTS(SELECT 1 FROM pg_catalog.pg_namespace WHERE nspname='public' AND pg_get_userbyid(nspowner)='pg_database_owner'
 AND nspacl::text='{pg_database_owner=UC/pg_database_owner,=U/pg_database_owner}')
 OR (SELECT array_agg(x.privilege_type ORDER BY x.privilege_type) FROM pg_catalog.pg_database d
 CROSS JOIN LATERAL aclexplode(COALESCE(d.datacl,acldefault('d',d.datdba))) x
 WHERE d.datname=current_database() AND x.grantee=0) IS DISTINCT FROM ARRAY['CONNECT','TEMPORARY']::text[]
 THEN RAISE EXCEPTION 'ADMIN_PRISTINE_REQUIRED'; END IF;
END $$;"""
    sql=sql.replace('BEGIN;','BEGIN;\n'+pristine,1)
    q.write_new(state()/marker,b'one administrative preparation; no automatic retry\n')
    admin(record,sql)


def engine(record,role):
    url=URL.create('postgresql+psycopg',username=ROLES[role],password=q.password(state()/(role+'_password')),
                   host=record['address'],port=5432,database=DATABASE)
    return create_engine(url,echo=False,hide_parameters=True,poolclass=NullPool,
                         connect_args={'connect_timeout':5,'sslmode':'disable','application_name':PROJECT+'-'+role})


class TrialClock:
    def sample(self):
        t=int(time.time());return TimeSample(t,t,True)  # synthetic trust assumption, not operational time


class TrialContinuity:
    def sample(self):return ContinuitySample(TOKEN,not (state()/'quarantine').exists())
    def block(self):
        p=state()/'quarantine'
        if not p.exists():q.write_new(p,b'BLOCKED: independent reconciliation required\n')


def service(eng,record,role):
    def no_approval(*args):raise c.Unsupported('Storage trial cannot authorize DEV09B')
    return a.PostgresConsumptionService(connections=eng.connect,
        destination=a.AuthorityDestination(DATABASE,record['system_identifier'],ROLES[role]),
        trust=SimpleNamespace(public_key=no_approval,validate_artifacts=no_approval,authorize_revocation=lambda _:None),
        clock=TrialClock(),continuity=TrialContinuity(),channel=SimpleNamespace(seal=no_approval))


def storage_consume(svc,approval_id,nonce):
    """Real storage transaction only. NEVER returns Receipt/OfflineObservation."""
    def action(db,control,now):
        row=db.execute(text(a.APPROVAL),{'approval_id':approval_id}).mappings().one()
        require(bytes(row['envelope'])==MARKER,'SYNTHETIC_STORAGE_RECORD_REQUIRED')
        c.require(row['state']=='AVAILABLE' and row['revoked'] is False)
        db.execute(text(a.NONCE),{'nonce':nonce})
        updated=db.execute(text(a.CONSUME),{'approval_id':approval_id,'session_json':c.canonical(asdict(SESSION)).decode()})
        c.require(updated.rowcount==1)
        return 'SYNTHETIC_STORAGE_COMMIT_CONFIRMED'
    return svc._locked(action)


def approval_id(n):return str(UUID(int=100+n))


def seed_sql():
    # Explicit INVALID documents; cannot be mistaken for signed operational approval.
    values=[]
    for n in range(1,6):
        docs=["decode('"+b.hex()+"','hex')" for b in (MARKER,*([b'{}']*7))]
        values.append("('"+approval_id(n)+"','"+str(UUID(int=300+n))+"','AVAILABLE',"+','.join(docs)+")")
    return "BEGIN;\nSET LOCAL statement_timeout='5s';\nINSERT INTO dev09b_authority.approvals (approval_id,attempt_id,state,envelope,payload,target,executor,plan,semantic,physical,provenance) VALUES "+','.join(values)+";\nCOMMIT;"


def observe(eng,record,identifier):
    # New independently authenticated read-only connection, never producer's tx.
    with eng.connect() as db,db.begin():
        db.execute(text('SET TRANSACTION READ ONLY'))
        db.execute(text("SET LOCAL statement_timeout='5s'"))
        identity=db.execute(text(a.IDENTITY)).mappings().one()
        require(identity['system_identifier']==record['system_identifier'] and identity['database']==DATABASE
                and identity['principal']==ROLES['observer'] and identity['effective_principal']==ROLES['observer'],'OBSERVER_IDENTITY')
        row=db.execute(text('SELECT state,revoked,session_json FROM dev09b_authority.approvals WHERE approval_id=CAST(:id AS uuid)'),{'id':identifier}).mappings().one()
        result=dict(state=row['state'],revoked=row['revoked'],session_bound=row['session_json']==c.canonical(asdict(SESSION)).decode(),
                    nonces=db.execute(text('SELECT count(*) FROM dev09b_authority.nonces')).scalar_one(),
                    events=db.execute(text('SELECT count(*) FROM dev09b_authority.events')).scalar_one())
        db.rollback()
    return result


def race(functions,actors):
    # Both distinct PostgreSQL sessions must have begun their transactions and
    # reached the control-lock statement before either can execute it. A barrier
    # only before connect() could otherwise accidentally test sequential calls.
    barrier=Barrier(len(functions),timeout=10);pids=set();lock=Lock()
    originals={id(actor):(actor,actor.connections) for actor in actors}
    for actor,factory in originals.values():
        def connections(factory=factory):
            conn=factory();arrived=False
            def before(connection,cursor,statement,parameters,context,executemany):
                nonlocal arrived
                if statement==a.CONTROL and not arrived:
                    arrived=True
                    require(connection.in_transaction() is True,'CONCURRENT_TRANSACTION_REQUIRED')
                    with lock:pids.add(connection.connection.driver_connection.info.backend_pid)
                    barrier.wait()
            event.listen(conn,'before_cursor_execute',before)
            return conn
        actor.connections=connections
    def run(fn):
        try:fn();return 'RETURNED'
        except a.AuthorityRefused:return 'REFUSED'
    try:
        with ThreadPoolExecutor(max_workers=len(functions)) as pool:outcomes=list(pool.map(run,functions))
        require(len(pids)==len(functions),'DISTINCT_CONCURRENT_BACKENDS_REQUIRED')
        return outcomes
    finally:
        for actor,factory in originals.values():actor.connections=factory


def scenarios(svc,revoker,observer,record,results=None):
    results=[] if results is None else results
    def consume(n):return storage_consume(svc,approval_id(n),str(uuid4()))
    def read(n):return observe(observer,record,approval_id(n))
    outcomes=race([lambda:consume(1),lambda:consume(1)],[svc]);row=read(1)
    require(sorted(outcomes)==['REFUSED','RETURNED'] and row==dict(state='CONSUMED',revoked=False,session_bound=True,nonces=1,events=0),'CONCURRENT_CONSUMPTION_FAILED')
    results.append(dict(case='two_consumers',outcomes=outcomes,persisted=row))
    outcomes=race([lambda:consume(2),lambda:revoker.revoke(approval_id(2))],[svc,revoker]);row=read(2)
    require(outcomes[1]=='RETURNED' and row['revoked'] is True and row['events']==0,'REVOCATION_RACE_FAILED')
    require((outcomes[0],row['state'],row['nonces']) in {('RETURNED','CONSUMED',2),('REFUSED','REVOKED',1)},'REVOCATION_LINEARIZATION_FAILED')
    # A winning consume must still be refused for progression after revocation.
    def progression(db,control,now):
        r=db.execute(text(a.APPROVAL),{'approval_id':approval_id(2)}).mappings().one()
        c.require(r['revoked'] is False)
    try:svc._locked(progression)
    except a.AuthorityRefused:pass
    else:raise q.Refused('REVOKED_PROGRESSION_ACCEPTED')
    results.append(dict(case='concurrent_revocation',outcomes=outcomes,persisted=row))
    consume(3);row=read(3)
    require(row['state']=='CONSUMED' and row['session_bound'] and row['events']==0,'NO_DISPATCH_FAILED')
    results.append(dict(case='consumed_no_dispatch',persisted=row))
    class LostResponse(Exception):pass
    try:
        consume(4)
        raise LostResponse()  # explicit injection AFTER real storage commit
    except LostResponse:pass
    row=read(4);require(row['state']=='CONSUMED' and row['session_bound'],'LOST_RESPONSE_NOT_DURABLE')
    results.append(dict(case='response_dropped_after_commit',persisted=row))
    for n in (3,4):
        before=read(n)
        try:consume(n)
        except a.AuthorityRefused:pass
        else:raise q.Refused('REPLAY_ACCEPTED')
        require(read(n)==before,'REPLAY_CHANGED_STATE')
    results.append(dict(case='replay',outcome='REFUSED_UNCHANGED'))
    try:svc.consume(approval_id(5),SESSION,str(uuid4()),profile_json=b'SYNTHETIC_STORAGE_TRIAL')
    except a.AuthorityRefused:pass
    else:raise q.Refused('SYNTHETIC_APPROVAL_ACCEPTED')
    require(read(5)['state']=='AVAILABLE','SYNTHETIC_REFUSAL_CHANGED_STATE')
    results.append(dict(case='public_consume_invalid_synthetic_envelope',outcome='REFUSED'))
    return results


def run(confirm):
    record=checked(confirm);q.write_new(state()/'run-started',b'one original storage trial; no automatic retry\n')
    engines={};report={'classification':'SYNTHETIC_STORAGE_TRIAL','operational_authorization':False,'status':'REFUSED','cases':[]}
    try:
        admin(record,seed_sql(),phase='seed')
        engines={role:engine(record,role) for role in ROLES}
        scenarios(service(engines['service'],record,'service'),service(engines['revoker'],record,'revoker'),engines['observer'],record,report['cases'])
        report['status']='STORAGE_CASES_PASSED'
    except BaseException as exc:
        report['exception_class']=type(exc).__name__
        if isinstance(exc,AdminFailure): report['admin_diagnostic']=exc.diagnostic
        if type(exc) is q.Refused: report['code']=str(exc)  # fixed trial diagnostic only
        raise
    finally:
        for eng in engines.values():eng.dispose()
        q.write_new(state()/'authority-trial-report-01.json',(json.dumps(report,sort_keys=True)+'\n').encode())
    return report['status']


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('validate-only','secrets','preflight','identify','prepare-admin','run'))
    parser.add_argument('--confirm-sid')
    parser.add_argument('--resume-inspection',help='Explicit one-shot resume after private pristine READ ONLY inspection; no retry by default')
    args=parser.parse_args(argv)
    try:
        validate()
        require(args.resume_inspection is None or args.action=='prepare-admin','RESUME_ACTION')
        if args.action=='validate-only':print('CANDIDATE_STATIC_CONFIGURATION_VALID')
        elif args.action=='secrets':make_secrets()
        elif args.action=='preflight':preflight()
        elif args.action=='identify':identify()
        elif args.action=='prepare-admin':prepare(args.confirm_sid,resume_inspection=args.resume_inspection)
        elif args.action=='run':print(run(args.confirm_sid))
        return 0
    except Exception as exc:
        # Fixed class only; never driver messages, SQL, parameters or credentials.
        print('AUTHORITY_TRIAL_REFUSED:'+type(exc).__name__)
        if isinstance(exc,AdminFailure): print(json.dumps(exc.diagnostic,sort_keys=True))
        return 1


if __name__=='__main__':raise SystemExit(main())
