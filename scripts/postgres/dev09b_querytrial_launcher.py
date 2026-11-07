"""Explicit CLI for a disposable SELECT trial; inert on import.

No Docker creation/start/stop API here. Compose lifecycle commands are separate.
Credentials and identity records live outside Git. Docker native/rootful Linux
bridge routing is checked, never assumed from the hostname `db`. TCP is isolated
bridge + SCRAM, without TLS; this is NOT the operational DEV09B executor/profile.
"""
import argparse
import base64
import hashlib
import hmac
import ipaddress
import json
import os
from pathlib import Path
import platform
import re
import secrets
import stat
import subprocess

ROOT = Path(__file__).resolve().parents[2]
PROJECT = 'livenetv2-dev09b-querytrial'
NETWORK = PROJECT + '_backend'
VOLUME = PROJECT + '_data'
IMAGE = 'postgres:16-alpine@sha256:f4610795587492cd4fb887c2dc3de301b813278bb6f616992061141b5f15ac36'
DIGEST = 'postgres@' + IMAGE.split('@')[1]
DATABASE = 'livenet_v2_dev'
ADMIN = 'dev09b_trial_admin'
PROBE = 'dev09b_trial_probe'


class Refused(Exception):
    pass


def require(value, code):
    if not value:raise Refused(code)


def command(args, *, input=None):
    # SQL/password verifiers only go through stdin; errors/output never printed.
    require(not any(os.environ.get(k) for k in ('DOCKER_HOST','DOCKER_CONTEXT','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH')), 'DOCKER_ENV_OVERRIDE')
    if args[0]=='docker':args=['docker','--context','default',*args[1:]]
    result = subprocess.run(args,input=input,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                            timeout=30,check=False)
    require(result.returncode==0 and len(result.stdout)<=2*1024*1024, 'COMMAND_FAILED')
    return result.stdout


def docker_json(*args):
    return json.loads(command(['docker',*args]))


def state_dir():
    raw = os.environ.get('DEV09B_QUERYTRIAL_STATE_DIR')
    require(raw is not None, 'STATE_DIR_REQUIRED')
    p = Path(raw)
    require(p.is_absolute() and '..' not in p.parts and p!=ROOT and ROOT not in p.parents, 'STATE_DIR_OUTSIDE_GIT_REQUIRED')
    for parent in (p,*p.parents):
        require(not parent.is_symlink(), 'SYMLINK_STATE')
        require(not (parent/'.git').exists(), 'STATE_DIR_OUTSIDE_GIT_REQUIRED')
    return p


def private_dir(p):
    st=p.stat()
    require(stat.S_ISDIR(st.st_mode) and st.st_uid==os.getuid() and stat.S_IMODE(st.st_mode)==0o700, 'PRIVATE_DIRECTORY_REQUIRED')


def write_new(p,data):
    private_dir(p.parent)
    fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())


def read_private(p):
    private_dir(p.parent)
    fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(fd,'rb') as f:
        st=os.fstat(f.fileno())
        require(stat.S_ISREG(st.st_mode) and st.st_uid==os.getuid() and st.st_nlink==1
                and stat.S_IMODE(st.st_mode)==0o600 and st.st_size<=16384, 'PRIVATE_FILE_REQUIRED')
        return f.read(16385)


def password(p):
    raw=read_private(p)
    require(re.fullmatch(rb'[A-Za-z0-9_-]{32,128}',raw) is not None,'INVALID_PASSWORD_FILE')
    return raw.decode('ascii')


def make_secrets():
    p=state_dir()
    p.mkdir(parents=True,mode=0o700,exist_ok=True)
    private_dir(p)
    require(not (p/'admin_password').exists() and not (p/'probe_password').exists(), 'SECRETS_ALREADY_EXIST')
    for name in ('admin_password','probe_password'):
        write_new(p/name,secrets.token_urlsafe(48).encode('ascii'))


def native_context():
    require(platform.system()=='Linux', 'NATIVE_LINUX_REQUIRED')
    ctx=docker_json('context','inspect','default')
    require(len(ctx)==1 and ctx[0]['Endpoints']['docker']['Host'] in {'unix:///var/run/docker.sock','unix:///run/docker.sock'}, 'LOCAL_ROOTFUL_DOCKER_REQUIRED')
    info=docker_json('info','--format','{{json .}}')
    require(info['OSType']=='linux' and 'desktop' not in info.get('OperatingSystem','').lower()
            and not any('rootless' in str(x).lower() for x in info.get('SecurityOptions',[])), 'NATIVE_ROOTFUL_DOCKER_REQUIRED')


def host_image():
    native_context()
    image=docker_json('image','inspect',IMAGE)[0]
    require(DIGEST in image['RepoDigests'] and image['Os']=='linux' and image['Architecture']=='amd64', 'PINNED_IMAGE_REQUIRED')
    return image


def topology(*, route):
    image=host_image()
    ids=command(['docker','ps','-q','--filter','label=com.docker.compose.project='+PROJECT,
                 '--filter','label=com.docker.compose.service=db']).split()
    require(len(ids)==1, 'EXACTLY_ONE_TRIAL_DB_REQUIRED')
    db=docker_json('inspect',ids[0])[0]
    labels=db['Config']['Labels']
    require(labels.get('com.docker.compose.project')==PROJECT and labels.get('com.docker.compose.service')=='db'
            and labels.get('com.docker.compose.project.working_dir')==str(ROOT), 'CONTAINER_PROVENANCE')
    require(db['Image']==image['Id'] and db['State']['Running'] is True
            and db['HostConfig'].get('Privileged') is False and not db['HostConfig'].get('PortBindings')
            and not any(db['NetworkSettings'].get('Ports',{}).values()), 'CONTAINER_ISOLATION')
    require(set(db['NetworkSettings']['Networks'])=={NETWORK}, 'TRIAL_NETWORK_ONLY')
    network=docker_json('network','inspect',NETWORK)[0]
    require(network['Driver']=='bridge' and network['Internal'] is True
            and network['Labels'].get('com.docker.compose.project')==PROJECT
            and network['Labels'].get('com.docker.compose.network')=='backend', 'INTERNAL_OWNED_BRIDGE_REQUIRED')
    endpoint=db['NetworkSettings']['Networks'][NETWORK]
    require(endpoint['NetworkID']==network['Id'], 'NETWORK_CHANGED')
    address=str(ipaddress.IPv4Address(endpoint['IPAddress']))
    mounts=[m for m in db['Mounts'] if m['Destination']=='/var/lib/postgresql/data']
    require(len(mounts)==1 and mounts[0]['Type']=='volume' and mounts[0]['Name']==VOLUME, 'OWNED_DATA_VOLUME_REQUIRED')
    require(all(m['Destination'] in {'/var/lib/postgresql/data','/run/secrets/querytrial_admin_password'} for m in db['Mounts']), 'EXTRA_MOUNT')
    mounts_secret=[m for m in db['Mounts'] if m['Destination']=='/run/secrets/querytrial_admin_password']
    require(len(mounts_secret)==1 and mounts_secret[0]['RW'] is False
            and mounts_secret[0]['Source']==str(state_dir()/'admin_password'), 'ADMIN_SECRET_MOUNT')
    volume=docker_json('volume','inspect',VOLUME)[0]
    require(volume['Labels'].get('com.docker.compose.project')==PROJECT
            and volume['Labels'].get('com.docker.compose.volume')=='querytrial_data', 'VOLUME_PROVENANCE')
    if route:
        routes=json.loads(command(['ip','-j','route','get',address]))
        bridge=network.get('Options',{}).get('com.docker.network.bridge.name') or 'br-'+network['Id'][:12]
        require(len(routes)==1 and routes[0].get('dev')==bridge and not routes[0].get('gateway'), 'NO_DIRECT_HOST_BRIDGE_ROUTE')
    return dict(container_id=db['Id'],image_id=image['Id'],network_id=network['Id'],address=address,
                volume=VOLUME,volume_created=volume['CreatedAt'])


def identify():
    p=state_dir();private_dir(p)
    binding=topology(route=False)
    output=command(['docker','exec','--user','postgres','--env','LC_ALL=C',binding['container_id'],
                    'pg_controldata','/var/lib/postgresql/data'])
    found=re.findall(r'^Database system identifier:\s*([1-9][0-9]{0,19})\s*$',output,re.M)
    require(len(found)==1 and int(found[0])<=2**64-1, 'CONTROL_ID_UNAVAILABLE')
    record=dict(schema_version=1,channel='docker-exec-pg_controldata',system_identifier=found[0],**binding)
    write_new(p/'identity.json',(json.dumps(record,sort_keys=True)+'\n').encode())
    return record


def checked_record(confirm):
    p=state_dir()
    record=json.loads(read_private(p/'identity.json'))
    require(type(confirm) is str and re.fullmatch(r'[1-9][0-9]{0,19}',confirm) is not None
            and confirm==record['system_identifier'] and record['schema_version']==1
            and record['channel']=='docker-exec-pg_controldata', 'INDEPENDENT_ID_CONFIRMATION_REQUIRED')
    actual=topology(route=True)
    require(all(record[k]==v for k,v in actual.items()), 'RECORDED_TARGET_CHANGED')
    return record


def scram_verifier(secret):
    # ASCII-only random password; no SASLprep ambiguity. Never emitted/logged.
    salt=secrets.token_bytes(16)
    salted=hashlib.pbkdf2_hmac('sha256',secret.encode('ascii'),salt,4096)
    client=hmac.digest(salted,b'Client Key','sha256')
    stored=hashlib.sha256(client).digest();server=hmac.digest(salted,b'Server Key','sha256')
    b64=lambda v:base64.b64encode(v).decode('ascii')
    return f'SCRAM-SHA-256$4096:{b64(salt)}${b64(stored)}:{b64(server)}'


def prepare_admin(confirm):
    record=checked_record(confirm)
    password(state_dir()/'admin_password')  # Verify private owner/mode before root reads the mount.
    verifier=scram_verifier(password(state_dir()/'probe_password'))
    # Fail if role already exists; no password rotation/retry/reset path.
    sql=fr"""SELECT (pg_catalog.current_database()='{DATABASE}' AND system_identifier::pg_catalog.text='{confirm}'
AND NOT EXISTS (SELECT 1 FROM pg_catalog.pg_namespace WHERE pg_catalog.substr(nspname,1,3)<>'pg_' AND nspname NOT IN ('public','information_schema'))
AND NOT EXISTS (SELECT 1 FROM pg_catalog.pg_depend d JOIN pg_catalog.pg_namespace n ON n.oid=d.refobjid WHERE d.refclassid='pg_catalog.pg_namespace'::pg_catalog.regclass AND n.nspname='public')
AND NOT EXISTS (SELECT 1 FROM pg_catalog.pg_extension WHERE extname<>'plpgsql')) AS target_empty FROM pg_catalog.pg_control_system() \gset
\if :target_empty
BEGIN;
SET LOCAL log_statement='none';
SET LOCAL log_min_error_statement='panic';
SET LOCAL log_parameter_max_length_on_error=0;
CREATE ROLE {PROBE} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 1 PASSWORD '{verifier}';
REVOKE ALL ON DATABASE {DATABASE} FROM PUBLIC;
GRANT CONNECT ON DATABASE {DATABASE} TO {PROBE};
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION pg_catalog.pg_control_system() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION pg_catalog.pg_control_system() TO {PROBE};
ALTER ROLE {PROBE} SET default_transaction_read_only=on;
ALTER ROLE {PROBE} SET statement_timeout='3s';
ALTER ROLE {PROBE} SET lock_timeout='500ms';
ALTER ROLE {PROBE} SET idle_in_transaction_session_timeout='10s';
ALTER ROLE {PROBE} SET search_path=pg_catalog,public;
COMMIT;
\else
\quit 3
\endif
"""
    shell='unset PGSERVICE PGSERVICEFILE PGOPTIONS PGPASSFILE; PGPASSWORD="$(cat /run/secrets/querytrial_admin_password)"; export PGPASSWORD; exec psql -X -q -A -t -v ON_ERROR_STOP=1 -h /var/run/postgresql -p 5432 -U '+ADMIN+' -d '+DATABASE
    command(['docker','exec','-i','--user','root',record['container_id'],'sh','-c',shell],input=sql)
    return {'status':'ADMIN_PREPARATION_RETURNED','schemas_or_extensions_installed':False}


def error_kind(exc):
    code=getattr(getattr(exc,'orig',None),'sqlstate',None)
    if code=='42501':return 'PERMISSION_DENIED'
    if type(code) is str and code.startswith('42'):return 'SQL_ERROR'
    if type(code) is str and code.startswith('08'):return 'CONNECTION_ERROR'
    return 'QUERY_FAILED'


class ObservedConnection:
    """Add sanitized error categories without changing the existing runner."""
    def __init__(self,connection):self.connection=connection;self.errors={}
    def __getattr__(self,name):return getattr(self.connection,name)
    def execute(self,statement,**kwargs):
        from scripts.postgres.dev09b_query_trial import QUERIES
        key=next((k for k,q in QUERIES.items() if q.sql==str(statement)),'setup')
        try:result=self.connection.execute(statement,**kwargs)
        except Exception as exc:
            self.errors[key]=error_kind(exc);raise
        owner=self
        class Rows:
            def mappings(self):
                try:yield from result.mappings()
                except Exception as exc:
                    owner.errors[key]=error_kind(exc);raise
            def close(self):return result.close()
        return Rows()


def run(confirm):
    # Only this explicit CLI path opens a connection; no DSN/password CLI flags.
    from sqlalchemy import create_engine
    from sqlalchemy.engine import URL
    from sqlalchemy.pool import NullPool
    from scripts.postgres.dev09b_query_trial import run_trial,TrialTarget
    record=checked_record(confirm)
    secret=password(state_dir()/'probe_password')
    url=URL.create('postgresql+psycopg',username=PROBE,password=secret,host=record['address'],port=5432,database=DATABASE)
    engine=create_engine(url,echo=False,hide_parameters=True,poolclass=NullPool,
                         connect_args={'connect_timeout':5,'sslmode':'disable','gssencmode':'disable'})
    try:
        connection=ObservedConnection(engine.connect())
        report=run_trial(connection,TrialTarget(DATABASE,confirm,PROBE,record['address']))
        return dict(trial=json.loads(report.to_json()),query_errors=connection.errors)
    finally:engine.dispose()


def main(argv=None):
    parser=argparse.ArgumentParser(description='Disposable DEV09B query trial; never migrations')
    parser.add_argument('action',choices=('check-host','secrets','identify','prepare-admin','run'))
    parser.add_argument('--confirm-system-identifier')
    args=parser.parse_args(argv)
    try:
        if args.action=='check-host':host_image();result={'status':'LOCAL_NATIVE_HOST_AND_IMAGE_CHECKED'}
        elif args.action=='secrets':make_secrets();result={'status':'PRIVATE_SECRETS_CREATED'}
        elif args.action=='identify':result=identify()
        elif args.action=='prepare-admin':result=prepare_admin(args.confirm_system_identifier)
        else:result=run(args.confirm_system_identifier)
        print(json.dumps(result,sort_keys=True))
        return 2 if args.action=='run' and result['trial']['status']!='COMPLETED' else 0
    except Exception as exc:
        # No credentials, SQL, Docker/driver stderr or exception repr.
        known={'DOCKER_ENV_OVERRIDE','COMMAND_FAILED','STATE_DIR_REQUIRED','STATE_DIR_OUTSIDE_GIT_REQUIRED',
               'SYMLINK_STATE','PRIVATE_DIRECTORY_REQUIRED','PRIVATE_FILE_REQUIRED','INVALID_PASSWORD_FILE',
               'SECRETS_ALREADY_EXIST','NATIVE_LINUX_REQUIRED','LOCAL_ROOTFUL_DOCKER_REQUIRED',
               'NATIVE_ROOTFUL_DOCKER_REQUIRED','PINNED_IMAGE_REQUIRED','EXACTLY_ONE_TRIAL_DB_REQUIRED',
               'CONTAINER_PROVENANCE','CONTAINER_ISOLATION','TRIAL_NETWORK_ONLY','INTERNAL_OWNED_BRIDGE_REQUIRED',
               'NETWORK_CHANGED','OWNED_DATA_VOLUME_REQUIRED','EXTRA_MOUNT','ADMIN_SECRET_MOUNT',
               'VOLUME_PROVENANCE','NO_DIRECT_HOST_BRIDGE_ROUTE','CONTROL_ID_UNAVAILABLE',
               'INDEPENDENT_ID_CONFIRMATION_REQUIRED','RECORDED_TARGET_CHANGED'}
        reason=exc.args[0] if type(exc) is Refused and exc.args and type(exc.args[0]) is str and exc.args[0] in known else 'QUERYTRIAL_LAUNCHER_REFUSED'
        print(json.dumps({'status':'REFUSED','reason':reason}))
        return 2


if __name__=='__main__':raise SystemExit(main())
