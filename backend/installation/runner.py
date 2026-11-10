"""Explicit standard MVP administrative operations. No automatic retry/stamp.

PostgreSQL session lock spans both chains and independent commit confirmation.
All migration DDL/ledger updates share one outer transaction. Local diagnostics
are ordinary private files, not an external authority or independent interlock.
"""
import ast
from contextlib import contextmanager
from copy import deepcopy
from hashlib import sha256
import json
import logging
import os
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text

from installation import APPLICATION_TARGET, APPLICATION_BASELINE, SECURITY_TARGET, STANDARD_ATTR, Refused, require
from installation.config import private_directory

BACKEND = Path(__file__).resolve().parents[1]
LOCK_KEY = int.from_bytes(sha256(b'LiveNet/standard-installation/v1').digest()[:8], 'big', signed=True)
TARGETS = dict(application=APPLICATION_TARGET, security=SECURITY_TARGET)
LEDGERS = dict(application='alembic_version', security='alembic_security_version')
IDENTITY = """SELECT current_database() AS database,session_user::text AS principal,
 current_user::text AS effective_principal,(pg_catalog.pg_control_system()).system_identifier::text AS sid,
 pg_backend_pid() AS pid,(SELECT backend_start::text FROM pg_catalog.pg_stat_activity WHERE pid=pg_backend_pid()) AS started,
 current_setting('server_version_num')::integer AS version"""


def identity(connection, settings, role, *, require_pin=True):
    require(connection.dialect.name == 'postgresql', 'POSTGRESQL_REQUIRED')
    require(connection.engine.echo is False and connection.engine.hide_parameters is True
            and logging.getLogger('sqlalchemy.engine').getEffectiveLevel() > logging.INFO, 'CLIENT_LOGGING_UNSAFE')
    require(connection.connection.driver_connection.autocommit is False, 'AUTOCOMMIT_FORBIDDEN')
    row = dict(connection.execute(text(IDENTITY)).mappings().one())
    values = settings.values
    require(row['database'] == values['database']['name'], 'WRONG_DATABASE')
    require(row['principal'] == row['effective_principal'] == values['roles'][role], 'WRONG_PRINCIPAL')
    pin = values['database']['system_identifier']
    require(not require_pin or pin is not None, 'PIN_SYSTEM_IDENTIFIER_FIRST')
    require(pin is None or row['sid'] == pin, 'WRONG_SYSTEM_IDENTIFIER')
    require(row['version'] >= 160000, 'POSTGRESQL_16_OR_LATER_REQUIRED')
    return row


@contextmanager
def locked(settings, role, *, require_pin=True):
    connection = None
    acquired = False
    try:
        connection = settings.connect(role)
        row = identity(connection, settings, role, require_pin=require_pin)
        acquired = connection.execute(text('SELECT pg_catalog.pg_try_advisory_lock(:key)'), {'key':LOCK_KEY}).scalar_one() is True
        require(acquired, 'CONCURRENT_INSTALLATION')
        connection.rollback()  # Session lock deliberately survives transaction end.
        yield connection, row
    finally:
        if connection is not None:
            try:
                if connection.in_transaction(): connection.rollback()
                if acquired:
                    connection.execute(text('SELECT pg_catalog.pg_advisory_unlock(:key)'), {'key':LOCK_KEY})
                    connection.rollback()
            finally:
                connection.close()  # Also releases the server session lock.


def script_config(chain):
    require(chain in TARGETS, 'UNKNOWN_CHAIN')
    config = Config()
    config.set_main_option('script_location', str(BACKEND/'installation/alembic'))
    versions = BACKEND/('migrations' if chain == 'application' else 'security_migrations')/'versions'
    config.set_main_option('version_locations', str(versions) + (os.pathsep + str(BACKEND/'installation/versions') if chain=='application' else ''))
    config.set_main_option('path_separator', 'os')
    config.set_main_option('version_table', LEDGERS[chain])
    config.set_main_option('version_table_schema', 'public')
    return config


def chain_sources(chain):
    script = ScriptDirectory.from_config(script_config(chain))
    rows = list(reversed(tuple(script.walk_revisions(base='base', head=TARGETS[chain]))))
    require(bool(rows) and rows[0].down_revision is None and rows[-1].revision == TARGETS[chain], 'INVALID_CHAIN')
    require(all(not row.dependencies and not row.branch_labels for row in rows), 'BRANCHED_CHAIN')
    return rows


def revisions(connection):
    result = {}
    for chain, ledger in LEDGERS.items():
        relation = connection.execute(text("SELECT c.relkind FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relname=:name"), {'name':ledger}).scalar_one_or_none()
        if relation is None:
            result[chain] = 'base'
            continue
        require(relation == 'r', 'INVALID_LEDGER_RELATION')
        rows = list(connection.execute(text('SELECT version_num FROM public.'+ledger)).scalars())
        require(len(rows) == 1 and type(rows[0]) is str, 'INVALID_OR_EMPTY_LEDGER')
        require(rows[0] in {row.revision for row in chain_sources(chain)}, 'UNSUPPORTED_REVISION')
        result[chain] = rows[0]
    require(result['security'] == 'base' or result['application'] in {APPLICATION_BASELINE,APPLICATION_TARGET}, 'SECURITY_WITHOUT_APPLICATION')
    return result


def validate_tables(connection, state):
    """Detect dirty bases / missing tables; not a claim of full historic catalog proof."""
    wanted = set()
    for chain, revision in state.items():
        if revision == 'base': continue
        for row in chain_sources(chain):
            tree = ast.parse(Path(row.path).read_text())
            upgrade = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'upgrade')
            for node in ast.walk(upgrade):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'create_table':
                    schema = next(ast.literal_eval(k.value) for k in node.keywords if k.arg == 'schema')
                    wanted.add((schema, ast.literal_eval(node.args[0])))
            if row.revision == revision: break
    found = {(row['schema'], row['name']) for row in connection.execute(text("""SELECT n.nspname AS schema,c.relname AS name
        FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname IN ('inventory','audit','security','discovery') AND c.relkind IN ('r','p','v','m','f')""")).mappings()}
    require(found == wanted, 'CATALOG_TABLES_DO_NOT_MATCH_REVISIONS')


def migration_privileges(connection, settings):
    flags = connection.execute(text("""SELECT r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication OR r.rolbypassrls AS elevated,
      d.datdba=r.oid OR pg_catalog.has_database_privilege(r.oid,d.oid,'CREATE') OR pg_catalog.has_database_privilege(r.oid,d.oid,'TEMP') AS database_power,
      EXISTS(SELECT FROM pg_catalog.pg_auth_members WHERE member=r.oid) AS memberships
      FROM pg_catalog.pg_roles r JOIN pg_catalog.pg_database d ON d.datname=current_database() WHERE r.rolname=current_user""")).mappings().one()
    require(all(value is False for value in flags.values()), 'MIGRATOR_EXCESS_PRIVILEGES')
    runtime_privileges(connection,settings)


def runtime_privileges(connection,settings):
    runtime = settings.values['roles']['runtime']
    row = connection.execute(text("""SELECT r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication OR r.rolbypassrls AS elevated,
      EXISTS(SELECT FROM pg_catalog.pg_auth_members WHERE member=r.oid) AS memberships,
      EXISTS(SELECT FROM pg_catalog.pg_namespace n WHERE n.nspname IN ('inventory','audit','security','discovery','public')
        AND (n.nspowner=r.oid OR pg_catalog.has_schema_privilege(r.oid,n.oid,'CREATE'))) AS ddl,
      pg_catalog.has_database_privilege(r.oid,current_database(),'CREATE') OR pg_catalog.has_database_privilege(r.oid,current_database(),'TEMP') AS database_power,
      EXISTS(SELECT FROM pg_catalog.pg_shdepend WHERE refclassid='pg_catalog.pg_authid'::pg_catalog.regclass AND refobjid=r.oid AND deptype='o') AS ownership
      FROM pg_catalog.pg_roles r WHERE r.rolname=:runtime"""), {'runtime':runtime}).mappings().one()
    require(all(value is False for value in row.values()), 'RUNTIME_EXCESS_PRIVILEGES')


class StandardScope:
    """Explicit substitute for PREPARED-1 only in installation/alembic/env.py."""
    def __init__(self, connection, transaction, settings, chain):
        self.connection, self.transaction, self.settings, self.chain = connection, transaction, settings, chain
        self.ledger = LEDGERS[chain]

    def assert_bound(self, connection):
        require(connection is self.connection and not connection.closed
            and connection.in_transaction() and connection.get_transaction() is self.transaction
            and self.transaction.is_active, 'STANDARD_TRANSACTION_CHANGED')
        identity(connection, self.settings, 'migrator')
        unsigned=LOCK_KEY % (2**64)
        held=connection.execute(text("""SELECT EXISTS(SELECT FROM pg_catalog.pg_locks WHERE locktype='advisory'
            AND pid=pg_backend_pid() AND granted AND objsubid=1
            AND classid::bigint=:high AND objid::bigint=:low)"""),
            dict(high=unsigned >> 32,low=unsigned & 0xffffffff)).scalar_one()
        require(held is True,'STANDARD_MIGRATION_LOCK_REQUIRED')
        migration_privileges(connection,self.settings)

    def require(self, requested, connection):
        self.assert_bound(connection)
        allowed = {'inventory','audit','btree_gist','discovery'} if self.chain == 'application' else {'security'}
        require(requested in allowed, 'WRONG_CHAIN_SCHEMA')
        if requested == 'btree_gist':
            row = connection.execute(text("""SELECT n.nspname AS schema FROM pg_catalog.pg_extension e
                JOIN pg_catalog.pg_namespace n ON n.oid=e.extnamespace WHERE e.extname='btree_gist'""")).scalar_one_or_none()
            require(row == 'public', 'ADMIN_PREPARE_BTREE_GIST')
        else:
            row = connection.execute(text("""SELECT pg_catalog.has_schema_privilege(current_user,n.oid,'USAGE')
                AND pg_catalog.has_schema_privilege(current_user,n.oid,'CREATE') AND n.nspowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user)
                FROM pg_catalog.pg_namespace n WHERE n.nspname=:schema"""), {'schema':requested}).scalar_one_or_none()
            require(row is True, 'ADMIN_PREPARE_SCHEMA')


def apply_chain(connection, transaction, settings, chain):
    config = script_config(chain)
    config.attributes.update(connection=connection, standard_chain=chain)
    scope = StandardScope(connection, transaction, settings, chain)
    config.attributes[STANDARD_ATTR] = scope
    scope.assert_bound(connection)
    command.upgrade(config, TARGETS[chain])
    scope.assert_bound(connection)


class Journal:
    def __init__(self, settings):
        self.directory = private_directory(settings.values['state_dir'])
        self.marker = self.directory/'uncertain.json'

    def write(self, path, value, *, new=False):
        raw = json.dumps(value, sort_keys=True, separators=(',',':')).encode()
        if new:
            fd = os.open(path, os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd,'wb') as output:
                output.write(raw);output.flush();os.fsync(output.fileno())
        else:
            temporary = self.directory/(str(uuid4())+'.tmp')
            self.write(temporary,value,new=True)
            os.replace(temporary,path)
        fd = os.open(self.directory,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)

    def begin(self, kind, identity_row, before, after, **extra):
        require(not self.marker.exists(), 'RECONCILE_PREVIOUS_OPERATION_FIRST')
        record = dict(operation_id=str(uuid4()),kind=kind,state='RUNNING',before=before,after=after,
            database=identity_row['database'],system_identifier=identity_row['sid'],
            backend_pid=identity_row['pid'],backend_start=identity_row['started'],**extra)
        self.write(self.marker,record,new=True)
        return record

    def finish(self, record, state):
        record['state'] = state
        self.write(self.directory/(record['operation_id']+'.json'),record)
        self.write(self.marker,record)
        if state in {'CONFIRMED','RECONCILED_COMMITTED','RECONCILED_ROLLED_BACK'}:
            self.marker.unlink()
            fd=os.open(self.directory,os.O_RDONLY|os.O_DIRECTORY)
            try:os.fsync(fd)
            finally:os.close(fd)


def migrate(settings, *, expected_application, expected_security, chain='all'):
    require(chain in {'all','application','security'}, 'UNKNOWN_CHAIN')
    journal = Journal(settings)
    require(not journal.marker.exists(), 'RECONCILE_PREVIOUS_OPERATION_FIRST')
    record = None
    with locked(settings, 'migrator') as (connection, target):
        transaction = connection.begin()
        sent = False
        try:
            before = revisions(connection)
            require(before == dict(application=expected_application,security=expected_security), 'WRONG_SOURCE_REVISION')
            validate_tables(connection,before)
            migration_privileges(connection,settings)
            after = dict(before)
            for selected in (('application','security') if chain == 'all' else (chain,)):
                if selected == 'security': require(after['application'] in {APPLICATION_BASELINE,APPLICATION_TARGET}, 'APPLICATION_FIRST')
                after[selected] = TARGETS[selected]
            require(before != after, 'ALREADY_AT_TARGET_NO_MIGRATION')
            record = journal.begin('migrate',target,before,after)
            for selected in (('application','security') if chain == 'all' else (chain,)):
                if before[selected] != after[selected]: apply_chain(connection,transaction,settings,selected)
            require(revisions(connection) == after, 'WRONG_RESULT_REVISION')
            validate_tables(connection,after)
            sent = True
            journal.finish(record,'COMMIT_INTENT')
            transaction.commit()
            # New physical session, while the original session lock remains held.
            fresh = settings.connect('migrator')
            try:
                identity(fresh,settings,'migrator')
                require(revisions(fresh) == after, 'COMMIT_RESULT_UNCERTAIN')
                validate_tables(fresh,after)
            finally:fresh.close()
            journal.finish(record,'CONFIRMED')
            return dict(state='CONFIRMED',operation_id=record['operation_id'],revisions=after)
        except BaseException as exc:
            try:
                if transaction.is_active: transaction.rollback()
            finally:
                if record is not None:
                    record['exception_class'] = type(exc).__name__
                    journal.finish(record,'UNKNOWN' if sent else 'ROLLBACK_REPORTED')
            raise


def reconcile(settings):
    journal = Journal(settings)
    require(journal.marker.is_file() and not journal.marker.is_symlink(), 'NO_PENDING_RECONCILIATION')
    record = json.loads(journal.marker.read_text())
    with locked(settings,'admin') as (connection,target):
        require((record['database'],record['system_identifier']) == (target['database'],target['sid']), 'WRONG_RECONCILIATION_TARGET')
        alive = connection.execute(text('SELECT count(*) FROM pg_catalog.pg_stat_activity WHERE pid=:pid AND backend_start::text=:started'),
            dict(pid=record['backend_pid'],started=record['backend_start'])).scalar_one()
        require(alive == 0, 'ORIGINAL_SESSION_STILL_PRESENT')
        if record['kind']=='migrate':
            state=revisions(connection);validate_tables(connection,state)
        else:
            from installation.admin import provision_state,grants_state,seed_state,discovery_schema_state
            require(record['kind'] in {'provision','grants','initial-user','discovery-schema'},'UNKNOWN_OPERATION_KIND')
            if record['kind']=='provision':state=provision_state(connection,settings)
            elif record['kind']=='grants':state=grants_state(connection,settings)
            elif record['kind']=='discovery-schema':state=discovery_schema_state(connection,settings)
            else:state=seed_state(connection,record)
        if state == record['after']: outcome = 'RECONCILED_COMMITTED'
        elif state == record['before']: outcome = 'RECONCILED_ROLLED_BACK'
        else: raise Refused('PARTIAL_OR_UNEXPECTED_STATE_NO_AUTOMATIC_REPAIR')
        journal.finish(record,outcome)
        result=dict(state=outcome,operation_id=record['operation_id'])
        result['revisions' if record['kind']=='migrate' else 'observed']=state
        return result
