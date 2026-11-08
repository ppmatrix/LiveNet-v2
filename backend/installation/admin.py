"""Bounded administrative setup/seed for the standard MVP, not runtime startup."""
import base64
import hashlib
import hmac
from pathlib import Path
import re
import secrets
from uuid import UUID, uuid4

from sqlalchemy import text, select, func
from sqlalchemy.orm import Session

from app.dedicated import _secret
from installation import APPLICATION_TARGET, SECURITY_TARGET, require
from installation.runner import (locked, identity, revisions, validate_tables, Journal,runtime_privileges,migration_privileges)


def scram(password):
    require(re.fullmatch('[A-Za-z0-9_-]{32,256}',password) is not None, 'RANDOM_DATABASE_PASSWORD_REQUIRED')
    salt=secrets.token_bytes(16)
    salted=hashlib.pbkdf2_hmac('sha256',password.encode('ascii'),salt,4096)
    client=hmac.digest(salted,b'Client Key','sha256')
    b64=lambda value:base64.b64encode(value).decode('ascii')
    return f'SCRAM-SHA-256$4096:{b64(salt)}${b64(hashlib.sha256(client).digest())}:{b64(hmac.digest(salted,b"Server Key","sha256"))}'


def backup(settings,output):
    """Ordinary pg_dump, protected local file; no dedicated recovery storage."""
    import os
    import shutil
    import subprocess
    import tempfile
    from installation.config import private_directory
    executable=shutil.which('pg_dump');require(executable is not None,'PG_DUMP_NOT_AVAILABLE')
    output=Path(output);require(output.is_absolute() and not output.exists(),'NEW_ABSOLUTE_BACKUP_PATH_REQUIRED')
    directory=private_directory(output.parent)
    db=settings.values['database'];role=settings.values['roles']['admin']
    password=_secret(settings.values['password_files']['admin'])
    require('\n' not in password and '\r' not in password,'PGPASS_FORMAT')
    escape=lambda value:str(value).replace('\\','\\\\').replace(':','\\:')
    with locked(settings,'admin') as (connection,target):
        connection.begin()
        connection.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')).close()
        snapshot=connection.execute(text('SELECT pg_catalog.pg_export_snapshot()')).scalar_one()
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            pgpass=Path(temporary)/'pgpass'
            fd=os.open(pgpass,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,'w') as out:
                out.write(':'.join(escape(v) for v in (db['host'],db['port'],db['name'],role,password))+'\n')
            env=dict(os.environ);env.pop('PGPASSWORD',None)
            env.update(PGPASSFILE=str(pgpass),PGSSLMODE=db['sslmode'],PGGSSENCMODE='disable')
            if db['sslmode']=='verify-full':env['PGSSLROOTCERT']=db['ca_file']
            fd=os.open(output,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
            try:
                with os.fdopen(fd,'wb') as out:
                    result=subprocess.run([executable,'--format=custom','--no-password','--host',db['host'],
                        '--port',str(db['port']),'--username',role,'--dbname',db['name'],'--snapshot',snapshot],
                        stdout=out,stderr=subprocess.PIPE,env=env,timeout=120)
                    require(result.returncode==0,'BACKUP_FAILED')
                    out.flush();os.fsync(out.fileno())
            except BaseException:
                output.unlink(missing_ok=True);raise
        return dict(state='BACKUP_SAVED',file=str(output),system_identifier=target['sid'])


def provision_state(connection,settings):
    names=settings.values['roles']
    roles={row['name'] for row in connection.execute(text('SELECT rolname AS name FROM pg_catalog.pg_roles WHERE rolname IN (:m,:r)'),dict(m=names['migrator'],r=names['runtime'])).mappings()}
    schemas={row['name']:row['owner'] for row in connection.execute(text("SELECT n.nspname AS name,r.rolname AS owner FROM pg_catalog.pg_namespace n JOIN pg_catalog.pg_roles r ON r.oid=n.nspowner WHERE n.nspname IN ('inventory','audit','security')")).mappings()}
    extension=connection.execute(text("SELECT n.nspname FROM pg_catalog.pg_extension e JOIN pg_catalog.pg_namespace n ON n.oid=e.extnamespace WHERE e.extname='btree_gist'")).scalar_one_or_none()
    return dict(roles=sorted(roles),schemas=schemas,extension=extension)


def provision(settings):
    journal=Journal(settings);require(not journal.marker.exists(),'RECONCILE_PREVIOUS_OPERATION_FIRST')
    with locked(settings,'admin') as (connection,target):
        tx=connection.begin();record=None;sent=False
        try:
            before=provision_state(connection,settings)
            require(not before['roles'],'DATABASE_ROLES_ALREADY_EXIST')
            state=revisions(connection)
            require(state==dict(application='base',security='base'),'PROVISION_EMPTY_DATABASE_ONLY')
            validate_tables(connection,state)
            names=settings.values['roles']
            after=dict(roles=sorted([names['migrator'],names['runtime']]),
                schemas={schema:names['migrator'] for schema in ('inventory','audit','security')},extension='public')
            record=journal.begin('provision',target,before,after)
            # Quiet password-verifier DDL; refuse if administrator cannot enforce it.
            for setting in ("log_statement='none'","log_min_error_statement='panic'",'log_parameter_max_length=0','log_parameter_max_length_on_error=0'):
                connection.execute(text('SET LOCAL '+setting)).close()
            quote=connection.dialect.identifier_preparer.quote
            for role,limit in (('migrator',4),('runtime',10)):
                verifier=scram(_secret(settings.values['password_files'][role]))
                # Locally generated SCRAM alphabet contains no quotes; no plaintext in SQL.
                require("'" not in verifier,'INVALID_SCRAM')
                connection.exec_driver_sql('CREATE ROLE '+quote(names[role])+f" LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS NOINHERIT CONNECTION LIMIT {limit} PASSWORD '"+verifier+"'").close()
            database=quote(settings.values['database']['name']);m=quote(names['migrator']);r=quote(names['runtime'])
            for sql in (
                f'REVOKE CREATE,TEMPORARY ON DATABASE {database} FROM PUBLIC',
                f'GRANT CONNECT ON DATABASE {database} TO {m},{r}',
                'REVOKE CREATE ON SCHEMA public FROM PUBLIC',
                f'GRANT USAGE,CREATE ON SCHEMA public TO {m}',
                'REVOKE EXECUTE ON FUNCTION pg_catalog.pg_control_system() FROM PUBLIC',
                f'GRANT EXECUTE ON FUNCTION pg_catalog.pg_control_system() TO {m}',
                'CREATE EXTENSION IF NOT EXISTS btree_gist WITH SCHEMA public',
            ):connection.execute(text(sql)).close()
            for schema in ('inventory','audit','security'):
                for sql in (f'CREATE SCHEMA IF NOT EXISTS {schema} AUTHORIZATION {m}',
                            f'ALTER SCHEMA {schema} OWNER TO {m}',f'REVOKE ALL ON SCHEMA {schema} FROM PUBLIC'):
                    connection.execute(text(sql)).close()
            require(provision_state(connection,settings)==after,'PROVISION_RESULT_MISMATCH')
            sent=True;journal.finish(record,'COMMIT_INTENT');tx.commit()
            fresh=settings.connect('admin')
            try:
                identity(fresh,settings,'admin')
                require(provision_state(fresh,settings)==after,'PROVISION_RESULT_UNCERTAIN')
            finally:fresh.close()
            journal.finish(record,'CONFIRMED')
            return dict(state='CONFIRMED',operation_id=record['operation_id'])
        except BaseException as exc:
            try:
                if tx.is_active:tx.rollback()
            finally:
                if record is not None:
                    record['exception_class']=type(exc).__name__
                    journal.finish(record,'UNKNOWN' if sent else 'ROLLBACK_REPORTED')
            raise


RUNTIME_GRANTS=(
    'GRANT USAGE ON SCHEMA inventory,audit,security TO {runtime}',
    'GRANT SELECT,INSERT ON TABLE inventory.resources TO {runtime}',
    'GRANT INSERT ON TABLE audit.events TO {runtime}',
    'GRANT SELECT(id,occurred_at) ON TABLE audit.events TO {runtime}',
    'GRANT SELECT ON TABLE security.local_users,security.global_role_grants TO {runtime}',
    # PostgreSQL FOR UPDATE needs UPDATE on at least one column; the existing
    # login service locks the user row. Never grant password/status/role writes.
    'GRANT UPDATE(updated_at) ON TABLE security.local_users TO {runtime}',
    'GRANT SELECT,INSERT ON TABLE security.login_sessions,security.login_throttles TO {runtime}',
    'GRANT UPDATE(last_activity_at,revoked_at) ON TABLE security.login_sessions TO {runtime}',
    'GRANT UPDATE(window_started_at,attempts) ON TABLE security.login_throttles TO {runtime}',
)


def grants_state(connection,settings):
    role=settings.values['roles']['runtime']
    tests={
        'resources_read':"has_table_privilege(:role,'inventory.resources','SELECT')",
        'resources_insert':"has_table_privilege(:role,'inventory.resources','INSERT')",
        'audit_insert':"has_table_privilege(:role,'audit.events','INSERT')",
        'audit_metadata':"has_column_privilege(:role,'audit.events','id','SELECT') AND has_column_privilege(:role,'audit.events','occurred_at','SELECT')",
        'users_read':"has_table_privilege(:role,'security.local_users','SELECT')",
        'users_lock':"has_column_privilege(:role,'security.local_users','updated_at','UPDATE')",
        'grants_read':"has_table_privilege(:role,'security.global_role_grants','SELECT')",
        'sessions_read':"has_table_privilege(:role,'security.login_sessions','SELECT')",
        'sessions_insert':"has_table_privilege(:role,'security.login_sessions','INSERT')",
        'sessions_activity':"has_column_privilege(:role,'security.login_sessions','last_activity_at','UPDATE')",
        'sessions_revoke':"has_column_privilege(:role,'security.login_sessions','revoked_at','UPDATE')",
        'throttle_read':"has_table_privilege(:role,'security.login_throttles','SELECT')",
        'throttle_insert':"has_table_privilege(:role,'security.login_throttles','INSERT')",
        'throttle_update':"has_column_privilege(:role,'security.login_throttles','attempts','UPDATE')",
        'throttle_window':"has_column_privilege(:role,'security.login_throttles','window_started_at','UPDATE')",
        'schemas_usage':"has_schema_privilege(:role,'inventory','USAGE') AND has_schema_privilege(:role,'audit','USAGE') AND has_schema_privilege(:role,'security','USAGE')",
    }
    return dict(connection.execute(text('SELECT '+','.join(sql+' AS '+key for key,sql in tests.items())),dict(role=role)).mappings().one())


def grants(settings):
    journal=Journal(settings);require(not journal.marker.exists(),'RECONCILE_PREVIOUS_OPERATION_FIRST')
    with locked(settings,'admin') as (connection,target):
        tx=connection.begin();record=None;sent=False
        try:
            require(revisions(connection)==dict(application=APPLICATION_TARGET,security=SECURITY_TARGET),'MIGRATE_FIRST')
            runtime_privileges(connection,settings)
            before=grants_state(connection,settings);after={key:True for key in before}
            record=journal.begin('grants',target,before,after)
            name=connection.dialect.identifier_preparer.quote(settings.values['roles']['runtime'])
            for sql in RUNTIME_GRANTS:connection.execute(text(sql.format(runtime=name))).close()
            require(grants_state(connection,settings)==after,'RUNTIME_GRANT_MISMATCH')
            sent=True;journal.finish(record,'COMMIT_INTENT');tx.commit()
            fresh=settings.connect('admin')
            try:
                identity(fresh,settings,'admin')
                require(grants_state(fresh,settings)==after,'RUNTIME_GRANT_UNCERTAIN')
            finally:fresh.close()
            journal.finish(record,'CONFIRMED')
            return dict(state='CONFIRMED',operation_id=record['operation_id'])
        except BaseException as exc:
            try:
                if tx.is_active:tx.rollback()
            finally:
                if record is not None:
                    record['exception_class']=type(exc).__name__
                    journal.finish(record,'UNKNOWN' if sent else 'ROLLBACK_REPORTED')
            raise


def seed_state(connection,record):
    found=connection.execute(text("SELECT count(*) FROM security.local_users WHERE id=CAST(:id AS uuid) AND login=:login AND status='active'"),dict(id=record['user_id'],login=record['login'])).scalar_one()
    count=connection.execute(text("SELECT count(*) FROM security.global_role_grants WHERE user_id=CAST(:id AS uuid) AND role IN ('inventory_reader','inventory_editor') AND scope_type='global' AND scope_id IS NULL"),dict(id=record['user_id'])).scalar_one()
    resource=True
    if record.get('resource_id'):
        resource=connection.execute(text('SELECT count(*) FROM inventory.resources WHERE id=CAST(:id AS uuid)'),dict(id=record['resource_id'])).scalar_one()==1
    return dict(user=found==1,roles=count==2,resource=resource)


def initial_user(settings,login,password,*,resource_name=None):
    from app.security.service import hash_password,normalize_credentials
    from app.security.models import LocalUser,GlobalRoleGrant
    from app.inventory.models import Resource
    from app.audit.service import record_audit_event
    login,password=normalize_credentials(dict(login=login,password=password))
    require(len(password)>=12,'INITIAL_PASSWORD_TOO_SHORT')
    require(resource_name is None or type(resource_name) is str and 0<len(resource_name)<=255,'RESOURCE_NAME')
    journal=Journal(settings);require(not journal.marker.exists(),'RECONCILE_PREVIOUS_OPERATION_FIRST')
    with locked(settings,'migrator') as (connection,target):
        tx=connection.begin();record=None;sent=False;session=None
        try:
            require(revisions(connection)==dict(application=APPLICATION_TARGET,security=SECURITY_TARGET),'MIGRATE_FIRST')
            migration_privileges(connection,settings)
            require(connection.execute(text('SELECT count(*) FROM security.local_users')).scalar_one()==0,'INITIAL_USER_ALREADY_EXISTS')
            user_id=uuid4();resource_id=uuid4() if resource_name is not None else None
            record=journal.begin('initial-user',target,dict(user=False,roles=False,resource=resource_id is None),
                dict(user=True,roles=True,resource=True),user_id=str(user_id),login=login,
                resource_id=None if resource_id is None else str(resource_id))
            session=Session(bind=connection,expire_on_commit=False)
            session.add(LocalUser(id=user_id,login=login,password_hash=hash_password(password),status='active'))
            session.flush()
            for role in ('inventory_reader','inventory_editor'):
                session.add(GlobalRoleGrant(user_id=user_id,role=role,scope_type='global',scope_id=None))
            record_audit_event(session,actor_type='administrator',actor_id=user_id,action='installation.initial_user.created',
                entity_type='security.user',entity_id=user_id,outcome='success',request_id=record['operation_id'])
            if resource_id is not None:
                session.add(Resource(id=resource_id,resource_type='virtual_machine',display_name=resource_name,
                    description=None,attributes={},administrative_state='active'))
                record_audit_event(session,actor_type='administrator',actor_id=user_id,action='inventory.resource.created',
                    entity_type='inventory.resource',entity_id=resource_id,outcome='success',request_id=record['operation_id'])
            session.flush()
            sent=True;journal.finish(record,'COMMIT_INTENT');tx.commit()
            fresh=settings.connect('migrator')
            try:
                identity(fresh,settings,'migrator')
                require(seed_state(fresh,record)==record['after'],'INITIAL_USER_UNCERTAIN')
            finally:fresh.close()
            journal.finish(record,'CONFIRMED')
            return dict(state='CONFIRMED',operation_id=record['operation_id'],user_id=str(user_id),login=login)
        except BaseException as exc:
            try:
                if tx.is_active:tx.rollback()
            finally:
                if record is not None:
                    record['exception_class']=type(exc).__name__
                    journal.finish(record,'UNKNOWN' if sent else 'ROLLBACK_REPORTED')
            raise
        finally:
            if session is not None:session.close()
