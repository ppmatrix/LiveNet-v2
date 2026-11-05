"""Real SQL in DEV-06 scratch schema ONLY. No app schemas, migrations or ledgers.

Executed inside the dedicated disposable network by dev06_check.py. Credentials
are synthetic files, never DSNs/arguments/logs. This is not a readiness checker.
"""
import json
from pathlib import Path
import sys
from uuid import uuid4

import psycopg
from psycopg import sql

INPUT = Path('/inputs')
CONFIG = json.loads((INPUT/'probe.json').read_text())
ROLES = ('admin','owner','migrator','runtime','inspector')


def connect(role, **changes):
    options = dict(host='db',port=5432,dbname='dev06_synthetic',user='dev06_'+role,
                   password=(INPUT/(role+'.password')).read_text().strip(),
                   sslmode='verify-full',sslrootcert='/inputs/ca.crt',gssencmode='disable',
                   connect_timeout=2,application_name='dev06-independent-probe')
    options.update(changes)
    return psycopg.connect(**options,autocommit=True)


def refused(connection,statement,state='42501'):
    try:
        connection.execute(statement)
    except psycopg.Error as error:
        assert error.sqlstate==state, 'Unexpected SQLSTATE in scratch privilege test'
    else:
        raise AssertionError('Forbidden scratch SQL unexpectedly succeeded')


def no_connection(**changes):
    try:
        with connect('runtime',**changes):
            pass
    except psycopg.OperationalError:
        return
    raise AssertionError('Unsafe PostgreSQL connection unexpectedly succeeded')


def setup():
    with connect('admin') as admin:
        identity=admin.execute('SELECT system_identifier::text FROM pg_catalog.pg_control_system()').fetchone()[0]
        assert identity==CONFIG['system_identifier'], 'Physical PostgreSQL identity mismatch'
        assert admin.pgconn.ssl_in_use
        server_version=int(admin.info.server_version)
        assert 160000 <= server_version < 170000
        assert admin.execute('SELECT current_database(),current_user').fetchone()==('dev06_synthetic','dev06_admin')
        for role in ROLES[1:]:
            password=(INPUT/(role+'.password')).read_text().strip()
            admin.execute(sql.SQL('CREATE ROLE {} {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS NOINHERIT PASSWORD {}').format(
                sql.Identifier('dev06_'+role),sql.SQL('NOLOGIN' if role=='owner' else 'LOGIN'),sql.Literal(password)))
        admin.execute('ALTER DATABASE dev06_synthetic OWNER TO dev06_owner')
        admin.execute('REVOKE ALL ON DATABASE dev06_synthetic FROM PUBLIC')
        admin.execute('GRANT CONNECT ON DATABASE dev06_synthetic TO dev06_migrator,dev06_runtime,dev06_inspector')
        admin.execute('REVOKE ALL ON SCHEMA public FROM PUBLIC')
        admin.execute('GRANT dev06_owner TO dev06_migrator WITH INHERIT FALSE, SET TRUE')
    with connect('migrator') as migrator:
        migrator.execute('SET ROLE dev06_owner')
        migrator.execute('CREATE SCHEMA dev06_probe AUTHORIZATION dev06_owner')
        migrator.execute('CREATE SEQUENCE dev06_probe.restricted_sequence')
        migrator.execute('CREATE TABLE dev06_probe.read_target (id uuid PRIMARY KEY,label text NOT NULL)')
        migrator.execute('CREATE TABLE dev06_probe.write_target (id uuid PRIMARY KEY,activity integer NOT NULL,immutable text NOT NULL)')
        migrator.execute('CREATE TABLE dev06_probe.audit_target (id uuid PRIMARY KEY,payload jsonb NOT NULL)')
        migrator.execute('INSERT INTO dev06_probe.read_target VALUES (%s,%s)',(uuid4(),'synthetic fixture'))
        migrator.execute('GRANT USAGE ON SCHEMA dev06_probe TO dev06_runtime,dev06_inspector')
        migrator.execute('GRANT SELECT ON dev06_probe.read_target TO dev06_runtime')
        migrator.execute('GRANT SELECT,INSERT ON dev06_probe.write_target TO dev06_runtime')
        migrator.execute('GRANT UPDATE(activity) ON dev06_probe.write_target TO dev06_runtime')
        migrator.execute('GRANT INSERT ON dev06_probe.audit_target TO dev06_runtime')
        migrator.execute('RESET ROLE')
    print(json.dumps({'phase':'setup','tls':True,'identity':True,'system_identifier':identity,
                      'server_version_num':server_version,'schema':'dev06_probe','migrations_executed':False}))


def checks():
    no_connection(user='dev06_owner',password=(INPUT/'owner.password').read_text().strip())
    no_connection(sslrootcert='/inputs/wrong-ca.crt')
    no_connection(host='wrong.db',hostaddr=CONFIG['db_ip'])
    no_connection(sslmode='disable')
    no_connection(port=1)
    with connect('runtime') as runtime:
        assert runtime.pgconn.ssl_in_use
        assert runtime.execute('SELECT ssl FROM pg_catalog.pg_stat_ssl WHERE pid=pg_backend_pid()').fetchone()==(True,)
        assert runtime.execute('SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls FROM pg_roles WHERE rolname=current_user').fetchone()==(False,False,False,False,False)
        assert runtime.execute('SELECT count(*) FROM pg_auth_members WHERE member=(SELECT oid FROM pg_roles WHERE rolname=current_user)').fetchone()==(0,)
        assert runtime.execute('SELECT label FROM dev06_probe.read_target').fetchone()==('synthetic fixture',)
        row=uuid4();runtime.execute('INSERT INTO dev06_probe.write_target VALUES (%s,1,%s)',(row,'immutable'))
        runtime.execute('UPDATE dev06_probe.write_target SET activity=2 WHERE id=%s',(row,))
        for statement in ('CREATE TABLE public.forbidden(id int)','CREATE TABLE dev06_probe.forbidden(id int)',
                          'CREATE TEMP TABLE forbidden(id int)','CREATE ROLE dev06_forbidden','CREATE DATABASE dev06_forbidden',
                          'ALTER TABLE dev06_probe.read_target ADD COLUMN forbidden int','DROP TABLE dev06_probe.read_target',
                          "SELECT nextval('dev06_probe.restricted_sequence')",
                          'SELECT last_value FROM dev06_probe.restricted_sequence',
                          "SELECT setval('dev06_probe.restricted_sequence',2)",
                          'SET ROLE dev06_owner','UPDATE dev06_probe.read_target SET label=label',
                          'UPDATE dev06_probe.write_target SET immutable=immutable',
                          'DELETE FROM dev06_probe.write_target','TRUNCATE dev06_probe.write_target',
                          'SELECT * FROM dev06_probe.audit_target',
                          'SELECT * FROM dev06_probe.read_target FOR UPDATE'):
            refused(runtime,statement)
        with runtime.transaction():
            assert runtime.execute('SELECT activity FROM dev06_probe.write_target WHERE id=%s FOR UPDATE',(row,)).fetchone()==(2,)
        audit=uuid4();runtime.execute('INSERT INTO dev06_probe.audit_target VALUES (%s,%s::jsonb)',(audit,'{"synthetic":true}'))
        for statement in ('UPDATE dev06_probe.audit_target SET payload=payload','DELETE FROM dev06_probe.audit_target'):
            refused(runtime,statement)
        rolled=uuid4()
        class Rollback(Exception): pass
        try:
            with runtime.transaction():
                runtime.execute('INSERT INTO dev06_probe.write_target VALUES (%s,3,%s)',(rolled,'rollback'))
                runtime.execute('INSERT INTO dev06_probe.audit_target VALUES (%s,%s::jsonb)',(rolled,'{}'))
                raise Rollback()
        except Rollback: pass
        assert runtime.execute('SELECT count(*) FROM dev06_probe.write_target WHERE id=%s',(rolled,)).fetchone()==(0,)
    with connect('admin') as admin:
        assert admin.execute('SELECT count(*) FROM dev06_probe.audit_target WHERE id=%s',(audit,)).fetchone()==(1,)
        assert admin.execute('SELECT count(*) FROM dev06_probe.audit_target WHERE id=%s',(rolled,)).fetchone()==(0,)
        assert admin.execute('SELECT activity FROM dev06_probe.write_target WHERE id=%s',(row,)).fetchone()==(2,)
        assert admin.execute("SELECT count(*) FROM pg_namespace WHERE nspname IN ('security','inventory','audit')").fetchone()==(0,)
        assert admin.execute("SELECT to_regclass('public.alembic_version'),to_regclass('public.alembic_security_version')").fetchone()==(None,None)
        assert admin.execute("SELECT count(*) FROM pg_roles WHERE rolname='dev06_forbidden'").fetchone()==(0,)
        expected=CONFIG['system_identifier']
        actual=admin.execute('SELECT system_identifier::text FROM pg_catalog.pg_control_system()').fetchone()[0]
        assert actual==expected and actual!=str(int(expected)+1)
    with connect('inspector') as inspector:
        assert inspector.execute("SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='dev06_probe'").fetchone()[0] >=3
        refused(inspector,'SELECT * FROM dev06_probe.read_target')
        refused(inspector,'INSERT INTO dev06_probe.audit_target VALUES (gen_random_uuid(),\'{}\')')
    print(json.dumps({'phase':'checks','tls_positive':True,'owner_nologin':True,'tls_negative':['wrong-ca','wrong-hostname','plaintext','connection-failure'],
                      'scratch_privileges':True,'sequence_rights_refused':True,'cross_connection_persistence':True,'atomic_rollback':True,
                      'app_schemas_absent':True,'readiness_authority':False}))


def attest():
    with connect('admin') as admin:
        rows=admin.execute('SELECT s.ssl,host(a.client_addr) FROM pg_stat_activity a JOIN pg_stat_ssl s ON a.pid=s.pid WHERE a.usename=%s',('dev06_runtime',)).fetchall()
        wanted=CONFIG['backend_ip']
        app=[ssl for ssl,address in rows if address==wanted]
        assert app and all(app), 'No TLS application connection independently observed'
        assert admin.execute("SELECT count(*) FROM pg_namespace WHERE nspname IN ('security','inventory','audit')").fetchone()==(0,)
    print(json.dumps({'phase':'attest','real_application_tls':True,'app_persistence_blocked':True}))


if __name__=='__main__':
    try:
        {'setup':setup,'checks':checks,'attest':attest}[sys.argv[1]]()
    except Exception as error:
        import traceback
        last=traceback.extract_tb(error.__traceback__)[-1]
        print(json.dumps({'type':type(error).__name__,'sqlstate':getattr(error,'sqlstate',None),
                          'line':last.lineno,'check':str(error) if isinstance(error,AssertionError) else None}),file=sys.stderr)
        # Driver/SQL diagnostics can contain credentials. Never print them.
        raise SystemExit('DEV-06 PostgreSQL probe failed (diagnostics suppressed)') from None
