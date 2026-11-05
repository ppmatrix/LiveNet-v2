"""Independent synthetic pg_dump/pg_restore drill. No migration-executor imports.

Two fresh clusters, independent initdb/CA/password/network and tmpfs only. Never
accepts a DSN, existing container, SQL file, operational backup or credential.
Only pinned local PostgreSQL tools and constant synthetic SQL are executed.
"""
from hashlib import sha256
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import tempfile
import time
import uuid

from dev09a2_target import PG_ID, PG_REF, verify_image

LABEL='livenet.dev09a2'


def checked_backup(data, expected):
    if (type(data) is not bytes or not data.startswith(b'PGDMP') or len(data)<100
        or type(expected) is not str or len(expected)!=64 or sha256(data).hexdigest()!=expected):
        raise ValueError('BACKUP_INTEGRITY_REFUSED')
    return data


def run():
    run_id='livenet-dev09a2-'+uuid.uuid4().hex[:10]
    work=Path(tempfile.mkdtemp(prefix=run_id+'-'))
    containers={};networks={};checks=[];phase='initial';result=None;failure=None;cleanup_errors=[]
    def check(name,condition):
        if not condition:raise ValueError('FIXTURE_CHECK_REFUSED')
        checks.append(name)
    def docker(*args,data=None,allow_failure=False):
        p=subprocess.run(['docker','--host','unix:///var/run/docker.sock',*map(str,args)],
                         input=data,capture_output=True,timeout=90)
        if p.returncode and not allow_failure:raise RuntimeError('DOCKER_PHASE_REFUSED')
        return p
    def output(*args):return docker(*args).stdout.decode().strip()
    def inspect(ident):
        obj=json.loads(output('inspect',ident))[0]
        if obj['Config']['Labels'].get(LABEL)!=run_id:raise ValueError('OWNERSHIP_REFUSED')
        if any(m['Type']=='volume' for m in obj['Mounts']):raise ValueError('UNEXPECTED_VOLUME')
        return obj
    def create(role,*args):
        name=run_id+'-'+role
        ident=output('create','--pull=never','--name',name,'--label',LABEL+'='+run_id,*args)
        containers[ident]=name
        return ident
    def remove(ident):
        inspect(ident)
        docker('rm','-f',ident)
        del containers[ident]
    def openssl(*args):
        p=subprocess.run(['openssl',*map(str,args)],capture_output=True,timeout=30)
        if p.returncode:raise ValueError('SYNTHETIC_PKI_REFUSED')
    def setup(kind):
        nonlocal phase
        phase=kind+'-pki'
        folder=work/kind;folder.mkdir(mode=0o700)
        host=run_id+'-'+kind+'-db'
        database='livenet_v2_dev_'+('restore_' if kind=='restore' else '')+run_id.rsplit('-',1)[1]
        password=secrets.token_urlsafe(36)
        openssl('req','-x509','-newkey','rsa:2048','-nodes','-keyout',folder/'ca.key',
                '-out',folder/'ca.crt','-days','2','-subj','/CN='+run_id+'-'+kind+'-CA',
                '-addext','basicConstraints=critical,CA:TRUE')
        openssl('req','-newkey','rsa:2048','-nodes','-keyout',folder/'server.key',
                '-out',folder/'server.csr','-subj','/CN='+host)
        (folder/'server.ext').write_text('subjectAltName=DNS:'+host+'\nextendedKeyUsage=serverAuth\nbasicConstraints=CA:FALSE\n')
        openssl('x509','-req','-in',folder/'server.csr','-CA',folder/'ca.crt','-CAkey',folder/'ca.key',
                '-CAcreateserial','-out',folder/'server.crt','-days','2','-extfile',folder/'server.ext')
        (folder/'password').write_text(password)
        (folder/'pgpass').write_text(host+':5432:'+database+':lnv2_dev_admin:'+password+'\n')
        for name in ('server.key','password','pgpass','ca.key'):(folder/name).chmod(0o600)
        for name in ('server.crt','ca.crt'):(folder/name).chmod(0o444)
        # Prevent the postgres image's VOLUME from allocating an anonymous volume,
        # including in the network-less ownership helper.
        helper=create(kind+'-owner','--network','none','--user','0:0','--read-only',
            '--cap-drop=ALL','--cap-add=CHOWN','--security-opt=no-new-privileges:true',
            '--tmpfs','/var/lib/postgresql/data:uid=70,gid=70,mode=0700',
            '--mount',f'type=bind,src={folder}/server.key,dst=/owned/server.key',
            '--mount',f'type=bind,src={folder}/password,dst=/owned/password',
            '--mount',f'type=bind,src={folder}/pgpass,dst=/owned/pgpass',
            '--entrypoint','chown',PG_ID,'70:70','/owned/server.key','/owned/password','/owned/pgpass')
        docker('start','-a',helper);check(kind+'_owner_exit',inspect(helper)['State']['ExitCode']==0);remove(helper)
        phase=kind+'-network'
        net=output('network','create','--internal','--label',LABEL+'='+run_id,run_id+'-'+kind+'-data')
        networks[net]=run_id+'-'+kind+'-data'
        obj=json.loads(output('network','inspect',net))[0]
        subnet=obj['IPAM']['Config'][0]['Subnet']
        (folder/'hba').write_text('local all all scram-sha-256\nhostnossl all all 0.0.0.0/0 reject\n'
            'hostnossl all all ::/0 reject\nhostssl '+database+' lnv2_dev_admin '+subnet+' scram-sha-256\n')
        (folder/'hba').chmod(0o444)
        phase=kind+'-initdb'
        args=['--network',net,'--network-alias',host,'--user','70:70','--read-only','--cap-drop=ALL',
              '--security-opt=no-new-privileges:true','--tmpfs','/var/lib/postgresql/data:uid=70,gid=70,mode=0700',
              '--tmpfs','/var/run/postgresql:uid=70,gid=70,mode=0770','--tmpfs','/tmp:mode=1777',
              '-e','POSTGRES_USER=lnv2_dev_admin','-e','POSTGRES_DB='+database,
              '-e','POSTGRES_PASSWORD_FILE=/tls/password',
              '-e','POSTGRES_INITDB_ARGS=--auth-host=scram-sha-256 --auth-local=scram-sha-256']
        for src,dest in [('server.key','server.key'),('server.crt','server.crt'),('ca.crt','ca.crt'),
                         ('password','password'),('pgpass','pgpass'),('hba','hba')]:
            args.extend(['--mount',f'type=bind,src={folder/src},dst=/tls/{dest},readonly'])
        cid=create(kind+'-db',*args,PG_ID,'postgres','-c','ssl=on','-c','ssl_cert_file=/tls/server.crt',
                   '-c','ssl_key_file=/tls/server.key','-c','hba_file=/tls/hba',
                   '-c','log_statement=none','-c','log_min_error_statement=panic')
        docker('start',cid)
        for _ in range(80):
            p=docker('exec',cid,'pg_isready','-q','-U','lnv2_dev_admin','-d',database,allow_failure=True)
            if p.returncode==0:break
            time.sleep(.25)
        else:raise ValueError('CLUSTER_NOT_READY')
        obj=inspect(cid);network=json.loads(output('network','inspect',net))[0]
        check(kind+'_isolation',network['Internal'] and not network['EnableIPv6']
            and set(network['Containers'])=={cid} and len(obj['NetworkSettings']['Networks'])==1
            and not obj['HostConfig']['PortBindings'] and not obj['HostConfig']['PublishAllPorts']
            and not obj['HostConfig']['Privileged'] and obj['Image']==PG_ID
            and '/var/lib/postgresql/data' in obj['HostConfig']['Tmpfs'])
        control=output('exec',cid,'pg_controldata','/var/lib/postgresql/data')
        sid=next(x.split(':',1)[1].strip() for x in control.splitlines() if x.startswith('Database system identifier:'))
        check(kind+'_fresh_sid',sid not in ('7698845469694267426','7699783234487926818'))
        conn='host='+host+' port=5432 dbname='+database+' user=lnv2_dev_admin sslmode=verify-full sslrootcert=/tls/ca.crt gssencmode=disable connect_timeout=3'
        return {'container_id':cid,'network_id':net,'database':database,'hostname':host,
                'system_identifier':sid,'ca_sha256':sha256((folder/'ca.crt').read_bytes()).hexdigest(),
                'conn':conn}
    def sql(cluster,statement,fail=False):
        inspect(cluster['container_id'])
        p=docker('exec','-i','-e','PGPASSFILE=/tls/pgpass',cluster['container_id'],
                 'psql','--no-psqlrc','--quiet','--tuples-only','--no-align','--set','ON_ERROR_STOP=1',
                 '--dbname',cluster['conn'],data=statement.encode(),allow_failure=fail)
        if fail:return p.returncode
        return p.stdout.decode().strip()
    def tools(cluster,tool,*args,data=None):
        inspect(cluster['container_id'])
        return docker('exec','-i','-e','PGPASSFILE=/tls/pgpass',cluster['container_id'],tool,*args,data=data).stdout
    def inspect_identity(cluster):
        identity=sql(cluster,"SELECT current_database()||'|'||current_user||'|'||system_identifier::text "
                     'FROM pg_control_system();')
        check(cluster['database']+'_sql_identity',identity==cluster['database']+'|lnv2_dev_admin|'+cluster['system_identifier'])
        check(cluster['database']+'_postgres16',160000 <= int(sql(cluster,"SELECT current_setting('server_version_num');")) < 170000)
        check(cluster['database']+'_tls',sql(cluster,'SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid();')=='t')
        check(cluster['database']+'_no_application',sql(cluster,"SELECT count(*) FROM pg_namespace WHERE nspname IN "
           "('inventory','audit','security','authorization','discovery','monitoring','operations');")=='0'
           and sql(cluster,"SELECT to_regclass('public.alembic_version') IS NULL AND "
                            "to_regclass('public.alembic_security_version') IS NULL;")=='t')
    snapshot="""SELECT k||'|'||v FROM dev09a2_recovery.synthetic_records ORDER BY k;
SELECT 'app='||count(*) FROM dev09a2_recovery.fixture_application_state;
SELECT 'security='||count(*) FROM dev09a2_recovery.fixture_security_state;
SELECT 'reader='||has_table_privilege('dev09a2_reader','dev09a2_recovery.synthetic_records','SELECT');
SELECT 'reader_write='||has_table_privilege('dev09a2_reader','dev09a2_recovery.synthetic_records','INSERT');
SELECT 'owners='||bool_and(r.rolname='lnv2_dev_admin') FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace JOIN pg_roles r ON r.oid=c.relowner WHERE n.nspname='dev09a2_recovery';
SELECT 'restricted_reader='||(NOT rolcanlogin AND NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole AND NOT rolreplication AND NOT rolbypassrls AND NOT rolinherit) FROM pg_roles WHERE rolname='dev09a2_reader';
"""
    try:
        metadata=json.loads(output('image','inspect',PG_ID))[0];verify_image(metadata)
        check('local_registry_digest_to_platform_id',PG_REF in metadata['RepoDigests'])
        source=setup('source');restore=setup('restore')
        check('independent_cluster_identity',source['system_identifier']!=restore['system_identifier'])
        check('independent_ca_network_container',all(source[k]!=restore[k] for k in ('ca_sha256','network_id','container_id','hostname')))
        for cluster in (source,restore):
            inspect_identity(cluster)
            sql(cluster,'CREATE ROLE dev09a2_reader NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS NOINHERIT;')
        phase='synthetic-before-backup'
        sql(source,"""CREATE SCHEMA dev09a2_recovery;
CREATE TABLE dev09a2_recovery.synthetic_records (k integer PRIMARY KEY,v text NOT NULL);
INSERT INTO dev09a2_recovery.synthetic_records VALUES (1,'synthetic-one'),(2,'synthetic-two');
CREATE TABLE dev09a2_recovery.fixture_application_state (n integer PRIMARY KEY);
CREATE TABLE dev09a2_recovery.fixture_security_state (n integer PRIMARY KEY);
GRANT USAGE ON SCHEMA dev09a2_recovery TO dev09a2_reader;
GRANT SELECT ON dev09a2_recovery.synthetic_records TO dev09a2_reader;
""")
        before=sql(source,snapshot);check('baseline_independent_snapshot',before.startswith('1|synthetic-one\n2|synthetic-two') and 'app=0' in before and 'security=0' in before)
        backup=tools(source,'pg_dump','--format=custom','--no-owner','--dbname',source['conn'])
        backup_digest=sha256(backup).hexdigest();checked_backup(backup,backup_digest)
        check('custom_backup_integrity',len(backup)>100)
        toc=tools(restore,'pg_restore','--list',data=backup).decode()
        check('backup_catalog_has_only_fixture', 'dev09a2_recovery' in toc and 'alembic_version' not in toc and 'alembic_security_version' not in toc)
        try:checked_backup(b'BROKEN'+backup[6:],backup_digest)
        except ValueError:checks.append('corrupt_backup_refused_before_restore')
        else:raise AssertionError('CORRUPT_BACKUP_ACCEPTED')
        phase='synthetic-failures'
        check('before_first_operation_no_change',sql(source,snapshot)==before)
        status=sql(source,"BEGIN; INSERT INTO dev09a2_recovery.synthetic_records VALUES (3,'must-rollback'); SELECT 1/0; COMMIT;",fail=True)
        check('actual_transaction_failure',status!=0)
        check('independent_transaction_rollback_inspection',sql(source,snapshot)==before)
        sql(source,'BEGIN; INSERT INTO dev09a2_recovery.fixture_application_state VALUES (1); COMMIT;')
        partial=sql(source,snapshot)
        check('between_chains_persisted_partial','app=1' in partial and 'security=0' in partial)
        sql(source,'BEGIN; INSERT INTO dev09a2_recovery.fixture_security_state VALUES (1); COMMIT;')
        # Synthetic lost acknowledgement classification, not a wire-failure claim.
        committed=sql(source,snapshot)
        check('commit_unknown_requires_independent_inspection','app=1' in committed and 'security=1' in committed)
        phase='source-unavailable-independent-recovery'
        docker('stop','--time','3',source['container_id'])
        check('source_stopped_before_restore',inspect(source['container_id'])['State']['Running'] is False)
        check('restore_initially_empty',sql(restore,"SELECT to_regnamespace('dev09a2_recovery') IS NULL;")=='t')
        checked_backup(backup,backup_digest)
        tools(restore,'pg_restore','--exit-on-error','--single-transaction','--no-owner','--dbname',restore['conn'],data=backup)
        after=sql(restore,snapshot)
        check('independent_restore_exact_data_and_grants',after==before)
        check('restore_returns_to_preexecution_fixture','app=0' in after and 'security=0' in after)
        check('restore_backup_bytes_unchanged',sha256(backup).hexdigest()==backup_digest)
        inspect_identity(restore)
        result={'status':'PASS','checks':checks,'passed':len(checks),'run':run_id,
                'source':{k:v for k,v in source.items() if k!='conn'},
                'restore':{k:v for k,v in restore.items() if k!='conn'},
                'backup':{'format':'pg_dump custom','sha256':backup_digest,'bytes':len(backup),
                          'snapshot_sha256':sha256(before.encode()).hexdigest(),'integrity':'PASS',
                          'content':'new synthetic fixture only; not operational data','retained':False},
                'recovery_independent_of_source_and_executor':True,
                'limitations':['Same Docker host; not off-host disaster recovery.',
                    'Source commit acknowledgement loss modeled, not wire-level fault injection.',
                    'No application migrations, Alembic ledgers or real role grant matrix tested.',
                    'Custom dump restores database objects; cluster roles prepared independently, not restored from globals.'],
                'postgres_image':PG_ID,'postgres_reference':PG_REF,'migrations_executed':False}
    except Exception as error:
        failure={'status':'FAIL','phase':phase,'type':type(error).__name__,'passed':len(checks)}
    finally:
        for ident in list(reversed(containers)):
            try:remove(ident)
            except Exception:cleanup_errors.append('container:'+ident)
        for ident in list(reversed(networks)):
            try:
                obj=json.loads(output('network','inspect',ident))[0]
                if obj['Labels'].get(LABEL)!=run_id or obj['Containers']:raise ValueError('NETWORK_OWNERSHIP_REFUSED')
                docker('network','rm',ident);del networks[ident]
            except Exception:cleanup_errors.append('network:'+ident)
        try:shutil.rmtree(work)
        except Exception:cleanup_errors.append('synthetic_work_directory')
        for args in (('ps','-aq'),('network','ls','-q')):
            if output(*args,'--filter','label='+LABEL+'='+run_id):cleanup_errors.append('labelled_resource_remaining')
    result=failure or result
    result['cleanup']={'removed':not cleanup_errors,'errors':cleanup_errors,'private_material_removed':not work.exists()}
    print(json.dumps(result,indent=2))
    return 1 if failure or cleanup_errors else 0


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-synthetic',action='store_true',required=True)
    parser.parse_args()
    raise SystemExit(run())
