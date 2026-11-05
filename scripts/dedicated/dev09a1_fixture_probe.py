"""DEV-09A.1: SQL only in a new disposable cluster and dev09a1_fixture.

Not a migration executor, authorization issuer or readiness checker. No imports
from application migrations/security executors. All passwords are synthetic.
"""
import hashlib
import json
from pathlib import Path
import sys
import time
from uuid import uuid4

import psycopg
from psycopg import sql
import controlled as c

INPUT = Path('/inputs')
CHECKS = []


def check(label, condition):
    if not condition:
        raise AssertionError(label)
    CHECKS.append(label)


def main():
    # Host must verify membership/storage/ports before any SQL or credential use.
    for _ in range(400):
        if (INPUT / 'fixture-start').is_file():
            break
        time.sleep(.05)
    else:
        raise AssertionError('isolation_barrier_not_released')
    config = json.loads((INPUT / 'fixture.json').read_text())
    database, host = config['database'], config['hostname']
    roles = {name: 'lnv2_dev_' + name for name in
             ('admin', 'db_owner', 'migrator', 'runtime', 'inspector')}
    check('synthetic_database_prefix', database.startswith('livenet_v2_dev_'))
    check('run_identity', host.startswith('livenet-dev09a1-'))
    check('ca_bytes', hashlib.sha256((INPUT / 'ca.crt').read_bytes()).hexdigest()
          == config['ca_sha256'])

    def connect(role, **changes):
        values = dict(host=host, port=5432, dbname=database, user=roles[role],
                      password=(INPUT / (role + '.password')).read_text().strip(),
                      sslmode='verify-full', sslrootcert='/inputs/ca.crt',
                      gssencmode='disable', connect_timeout=2,
                      application_name='dev09a1-fixture-only')
        values.update(changes)
        return psycopg.connect(**values, autocommit=True)

    def denied(conn, label, statement):
        try:
            conn.execute(statement)
        except psycopg.Error as error:
            check(label, error.sqlstate == '42501')
        else:
            raise AssertionError(label)

    def no_connection(label, **changes):
        try:
            with connect('runtime', **changes):
                pass
        except psycopg.OperationalError:
            CHECKS.append(label)
        else:
            raise AssertionError(label)

    def empty_application(conn):
        check('application_schemas_absent', conn.execute(
            "SELECT count(*) FROM pg_namespace WHERE nspname IN "
            "('inventory','audit','security','authorization','discovery','monitoring','operations')"
        ).fetchone() == (0,))
        check('both_ledgers_absent', conn.execute(
            "SELECT to_regclass('public.alembic_version'),"
            "to_regclass('public.alembic_security_version')").fetchone() == (None, None))

    with connect('admin') as admin:
        identity = admin.execute('SELECT system_identifier::text FROM '
                                 'pg_catalog.pg_control_system()').fetchone()[0]
        check('independent_control_identity', identity == config['system_identifier'])
        check('historical_cluster_identity_refused', identity not in
              ('7698845469694267426', '7699783234487926818'))
        version = admin.info.server_version
        check('postgresql16', 160000 <= version < 170000)
        check('database_and_admin', admin.execute('SELECT current_database(),current_user')
              .fetchone() == (database, roles['admin']))
        check('tls_on_server', admin.pgconn.ssl_in_use and admin.execute(
            'SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()').fetchone() == (True,))
        empty_application(admin)
        for role in ('db_owner', 'migrator', 'runtime', 'inspector'):
            admin.execute(sql.SQL('CREATE ROLE {} {} NOSUPERUSER NOCREATEDB NOCREATEROLE '
                                 'NOREPLICATION NOBYPASSRLS NOINHERIT PASSWORD {}').format(
                sql.Identifier(roles[role]), sql.SQL('NOLOGIN' if role == 'db_owner' else 'LOGIN'),
                sql.Literal((INPUT / (role + '.password')).read_text().strip())))
        admin.execute(sql.SQL('ALTER DATABASE {} OWNER TO {}').format(
            sql.Identifier(database), sql.Identifier(roles['db_owner'])))
        admin.execute(sql.SQL('REVOKE ALL ON DATABASE {} FROM PUBLIC').format(sql.Identifier(database)))
        for role in ('migrator', 'runtime', 'inspector'):
            admin.execute(sql.SQL('GRANT CONNECT ON DATABASE {} TO {}').format(
                sql.Identifier(database), sql.Identifier(roles[role])))
        admin.execute('REVOKE ALL ON SCHEMA public FROM PUBLIC')
        admin.execute('CREATE SCHEMA dev09a1_fixture AUTHORIZATION lnv2_dev_db_owner')
        admin.execute('GRANT USAGE,CREATE ON SCHEMA dev09a1_fixture TO lnv2_dev_migrator')
        admin.execute('GRANT USAGE ON SCHEMA dev09a1_fixture TO lnv2_dev_runtime,lnv2_dev_inspector')
        admin.execute(sql.SQL('GRANT CREATE ON DATABASE {} TO lnv2_dev_migrator').format(
            sql.Identifier(database)))
        check('btree_gist_available_trusted', admin.execute(
            "SELECT bool_or(trusted) FROM pg_available_extension_versions WHERE name='btree_gist'"
        ).fetchone() == (True,))

    with connect('migrator') as migrator:
        denied(migrator, 'migrator_no_unscoped_public_ddl', 'CREATE TABLE public.denied(id int)')
        denied(migrator, 'migrator_no_createrole', 'CREATE ROLE dev09a1_denied')
        # Independent extension/constraint fixture, NOT any application migration.
        migrator.execute('CREATE EXTENSION btree_gist WITH SCHEMA dev09a1_fixture')
        with connect('admin') as admin:
            admin.execute(sql.SQL('REVOKE CREATE ON DATABASE {} FROM lnv2_dev_migrator').format(
                sql.Identifier(database)))
        migrator.execute('SET search_path=dev09a1_fixture,pg_catalog')
        migrator.execute('CREATE TABLE dev09a1_fixture.ranges '
                         '(key integer, valid int4range, EXCLUDE USING gist (key WITH =,valid WITH &&))')
        migrator.execute("INSERT INTO dev09a1_fixture.ranges VALUES (1,'[1,3)')")
        try:
            migrator.execute("INSERT INTO dev09a1_fixture.ranges VALUES (1,'[2,4)')")
        except psycopg.errors.ExclusionViolation:
            CHECKS.append('btree_gist_exclusion_enforced')
        else:
            raise AssertionError('btree_gist_exclusion_enforced')
        migrator.execute('CREATE SEQUENCE dev09a1_fixture.restricted_sequence')
        migrator.execute('CREATE TABLE dev09a1_fixture.read_target(id uuid PRIMARY KEY,label text NOT NULL)')
        migrator.execute('CREATE TABLE dev09a1_fixture.session_target '
                         '(id uuid PRIMARY KEY,activity integer NOT NULL,immutable text NOT NULL)')
        migrator.execute('CREATE TABLE dev09a1_fixture.audit_target(id uuid PRIMARY KEY,payload jsonb NOT NULL)')
        migrator.execute('INSERT INTO dev09a1_fixture.read_target VALUES (%s,%s)',
                         (uuid4(), 'synthetic DEV09A'))
        migrator.execute('GRANT SELECT ON dev09a1_fixture.read_target TO lnv2_dev_runtime')
        migrator.execute('GRANT SELECT,INSERT ON dev09a1_fixture.session_target TO lnv2_dev_runtime')
        migrator.execute('GRANT UPDATE(activity) ON dev09a1_fixture.session_target TO lnv2_dev_runtime')
        migrator.execute('GRANT INSERT ON dev09a1_fixture.audit_target TO lnv2_dev_runtime')
    with connect('admin') as admin:
        # New, dedicated fixture cluster only; never shared with existing objects.
        admin.execute('REASSIGN OWNED BY lnv2_dev_migrator TO lnv2_dev_db_owner')
        admin.execute('REVOKE ALL ON SCHEMA dev09a1_fixture FROM lnv2_dev_migrator')
        check('migrator_no_memberships', admin.execute(
            "SELECT count(*) FROM pg_auth_members WHERE member="
            "(SELECT oid FROM pg_roles WHERE rolname='lnv2_dev_migrator')").fetchone() == (0,))
    with connect('migrator') as migrator:
        denied(migrator, 'migrator_no_implicit_data_read', 'SELECT * FROM dev09a1_fixture.session_target')
        denied(migrator, 'migrator_create_window_revoked', 'CREATE SCHEMA dev09a1_denied')
        denied(migrator, 'migrator_no_owner_role', 'SET ROLE lnv2_dev_db_owner')

    no_connection('owner_nologin', user=roles['db_owner'],
                  password=(INPUT / 'db_owner.password').read_text().strip())
    no_connection('wrong_ca_refused', sslrootcert='/inputs/wrong-ca.crt')
    no_connection('wrong_hostname_refused', host='wrong.dev09a1', hostaddr=config['db_ip'])
    no_connection('plaintext_refused', sslmode='disable')
    no_connection('wrong_database_refused', dbname='livenet')
    no_connection('wrong_password_refused', password='synthetic-deliberately-wrong')
    with connect('runtime') as runtime:
        check('runtime_no_admin_attributes', runtime.execute(
            'SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls '
            'FROM pg_roles WHERE rolname=current_user').fetchone() == (False,) * 5)
        check('runtime_no_memberships', runtime.execute(
            'SELECT count(*) FROM pg_auth_members WHERE member='
            '(SELECT oid FROM pg_roles WHERE rolname=current_user)').fetchone() == (0,))
        check('runtime_read_only_target', runtime.execute(
            'SELECT label FROM dev09a1_fixture.read_target').fetchone() == ('synthetic DEV09A',))
        row = uuid4()
        runtime.execute('INSERT INTO dev09a1_fixture.session_target VALUES (%s,1,%s)', (row, 'immutable'))
        runtime.execute('UPDATE dev09a1_fixture.session_target SET activity=2 WHERE id=%s', (row,))
        with runtime.transaction():
            check('permitted_row_lock', runtime.execute(
                'SELECT activity FROM dev09a1_fixture.session_target WHERE id=%s FOR UPDATE', (row,)
            ).fetchone() == (2,))
        for label, statement in (
            ('no_schema_create', 'CREATE SCHEMA dev09a1_denied'),
            ('no_public_ddl', 'CREATE TABLE public.denied(id int)'),
            ('no_fixture_ddl', 'CREATE TABLE dev09a1_fixture.denied(id int)'),
            ('no_temporary', 'CREATE TEMP TABLE dev09a1_denied(id int)'),
            ('no_createrole', 'CREATE ROLE dev09a1_denied'),
            ('no_createdb', 'CREATE DATABASE dev09a1_denied'),
            ('no_drop', 'DROP TABLE dev09a1_fixture.read_target'),
            ('no_owner_role', 'SET ROLE lnv2_dev_db_owner'),
            ('no_migrator_role', 'SET ROLE lnv2_dev_migrator'),
            ('no_admin_role', 'SET ROLE lnv2_dev_admin'),
            ('no_sequence_usage', "SELECT nextval('dev09a1_fixture.restricted_sequence')"),
            ('no_sequence_select', 'SELECT last_value FROM dev09a1_fixture.restricted_sequence'),
            ('no_sequence_update', "SELECT setval('dev09a1_fixture.restricted_sequence',2)"),
            ('no_inventory_analogue_write', 'UPDATE dev09a1_fixture.read_target SET label=label'),
            ('no_broad_update', 'UPDATE dev09a1_fixture.session_target SET immutable=immutable'),
            ('no_delete', 'DELETE FROM dev09a1_fixture.session_target'),
            ('no_truncate', 'TRUNCATE dev09a1_fixture.session_target'),
            ('no_audit_read', 'SELECT * FROM dev09a1_fixture.audit_target'),
            ('no_audit_update', 'UPDATE dev09a1_fixture.audit_target SET payload=payload'),
            ('no_audit_delete', 'DELETE FROM dev09a1_fixture.audit_target'),
        ):
            denied(runtime, label, statement)
        audit, rolled = uuid4(), uuid4()
        runtime.execute('INSERT INTO dev09a1_fixture.audit_target VALUES (%s,%s::jsonb)',
                        (audit, '{"synthetic":true}'))
        class Abort(Exception):
            pass
        try:
            with runtime.transaction():
                runtime.execute('INSERT INTO dev09a1_fixture.session_target VALUES (%s,3,%s)', (rolled, 'rollback'))
                runtime.execute('INSERT INTO dev09a1_fixture.audit_target VALUES (%s,%s::jsonb)', (rolled, '{}'))
                raise Abort()
        except Abort:
            pass
        check('transaction_rollback', runtime.execute(
            'SELECT count(*) FROM dev09a1_fixture.session_target WHERE id=%s', (rolled,)).fetchone() == (0,))
    with connect('inspector') as inspector:
        check('inspector_catalog_only', inspector.execute(
            "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
            "WHERE n.nspname='dev09a1_fixture'").fetchone()[0] > 0)
        denied(inspector, 'inspector_no_data', 'SELECT * FROM dev09a1_fixture.read_target')
        denied(inspector, 'inspector_no_write', "INSERT INTO dev09a1_fixture.audit_target VALUES (gen_random_uuid(),'{}')")
    with connect('admin') as admin:
        check('cross_connection_session_persistence', admin.execute(
            'SELECT activity FROM dev09a1_fixture.session_target WHERE id=%s', (row,)).fetchone() == (2,))
        check('cross_connection_audit_persistence', admin.execute(
            'SELECT count(*) FROM dev09a1_fixture.audit_target WHERE id=%s', (audit,)).fetchone() == (1,))
        check('cross_connection_audit_rollback', admin.execute(
            'SELECT count(*) FROM dev09a1_fixture.audit_target WHERE id=%s', (rolled,)).fetchone() == (0,))
        # Independent synthetic DDL and ledgers; never application table shapes
        # or public Alembic tables. Admin is restricted to this new cluster.
        admin.execute('CREATE SCHEMA dev09a1_recovery AUTHORIZATION lnv2_dev_migrator')
        with connect('migrator') as migrator:
            row_priv = migrator.execute(
                'SELECT rolname,rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls,'
                'rolinherit,rolcanlogin FROM pg_roles WHERE rolname=current_user').fetchone()
            memberships = tuple(x[0] for x in migrator.execute(
                'SELECT r.rolname FROM pg_auth_members m JOIN pg_roles r ON r.oid=m.roleid '
                'WHERE m.member=(SELECT oid FROM pg_roles WHERE rolname=current_user)').fetchall())
            check('recovery_migrator_schema_create', migrator.execute(
                "SELECT has_schema_privilege(current_user,'dev09a1_recovery','CREATE')").fetchone() == (True,))
            priv = c.Privileges(*row_priv, memberships, ('schema_create:synthetic',))
            expected_priv = c.Privileges(roles['migrator'],False,False,False,False,False,False,True,(),
                                         ('schema_create:synthetic',))
            target = c.Target('DEV','MVP',database,config['system_identifier'],host,5432,
                config['ca_sha256'],'verify-full',roles['migrator'],config['container_id'],
                config['network_id'],config['image_id'],'tmpfs:'+config['container_id'],True,(),config['run'])
            observed = c.Target('DEV','MVP',migrator.info.dbname,identity,migrator.info.host,
                migrator.info.port,hashlib.sha256((INPUT/'ca.crt').read_bytes()).hexdigest(),
                'verify-full' if migrator.pgconn.ssl_in_use else 'disable',migrator.info.user,
                config['container_id'],config['network_id'],config['image_id'],
                'tmpfs:'+config['container_id'],True,(),config['run'])
            p = c.make_plan(environment='DEV',profile='MVP',application='f066a01a7230',
                            security='b12b01a7230',operation='upgrade')
            record = c.validate_local(p,target,observed,priv,expected_priv,forbidden=())
            check('local_executor_real_observations_still_blocked', record['execution']=='BLOCKED')
            try:
                c.execute(p)
            except c.Refused:
                CHECKS.append('executor_refuses_even_after_local_validation')
            else:
                raise AssertionError('executor_bypass')
            state = c.transition(c.transition(c.Recovery(),'validated'),'begin_application')
            try:
                with migrator.transaction():
                    migrator.execute('CREATE TABLE dev09a1_recovery.interrupted (n integer)')
                    migrator.execute('INSERT INTO dev09a1_recovery.interrupted VALUES (1)')
                    raise Abort()
            except Abort:
                state = c.transition(state,'rollback_confirmed')
            check('transactional_ddl_rollback', admin.execute(
                "SELECT to_regclass('dev09a1_recovery.interrupted')").fetchone() == (None,))
            check('confirmed_rollback_terminal', state.phase=='ROLLED_BACK')
            migrator.execute('CREATE SEQUENCE dev09a1_recovery.nontransactional_counter')
            first = migrator.execute("SELECT nextval('dev09a1_recovery.nontransactional_counter')").fetchone()[0]
            try:
                with migrator.transaction():
                    migrator.execute("SELECT nextval('dev09a1_recovery.nontransactional_counter')")
                    raise Abort()
            except Abort:
                pass
            check('sequence_allocation_not_rolled_back', migrator.execute(
                "SELECT nextval('dev09a1_recovery.nontransactional_counter')").fetchone()[0] == first+2)
            try:
                with migrator.transaction():
                    migrator.execute('CREATE INDEX CONCURRENTLY forbidden ON dev09a1_fixture.read_target(id)')
            except psycopg.errors.ActiveSqlTransaction:
                CHECKS.append('concurrent_index_requires_nontransactional_window')
            else:
                raise AssertionError('nontransactional_ddl_not_rejected')
            state = c.transition(c.transition(c.Recovery(),'validated'),'begin_application')
            with migrator.transaction():
                migrator.execute('CREATE TABLE dev09a1_recovery.fixture_app_ledger (value text)')
                migrator.execute("INSERT INTO dev09a1_recovery.fixture_app_ledger VALUES ('synthetic_a1')")
            state = c.transition(c.transition(state,'commit_requested'),'commit_ack')
            check('chain_boundary_partial_stop', c.transition(state,'fail').phase=='PARTIAL')
            check('first_chain_persists_without_second', admin.execute(
                'SELECT value FROM dev09a1_recovery.fixture_app_ledger').fetchall()==[('synthetic_a1',)]
                and admin.execute("SELECT to_regclass('dev09a1_recovery.fixture_security_ledger')").fetchone()==(None,))
            disconnected = connect('migrator')
            try:
                disconnected.execute('BEGIN')
                disconnected.execute('CREATE TABLE dev09a1_recovery.connection_interrupted (n integer)')
                pid = disconnected.info.backend_pid
                check('terminate_only_fixture_backend', admin.execute('SELECT pg_terminate_backend(%s)',(pid,)).fetchone()==(True,))
                try:
                    disconnected.execute('SELECT 1')
                except psycopg.OperationalError:
                    CHECKS.append('actual_connection_loss_observed')
                else:
                    raise AssertionError('connection_loss_missing')
            finally:
                disconnected.close()
            check('connection_loss_transaction_rollback', admin.execute(
                "SELECT to_regclass('dev09a1_recovery.connection_interrupted')").fetchone()==(None,))
            security_state = c.transition(state,'begin_security')
            check('lost_connection_requires_inspection', c.transition(security_state,'connection_lost').phase=='UNKNOWN')
            with migrator.transaction():
                migrator.execute('CREATE TABLE dev09a1_recovery.fixture_security_ledger (value text)')
                migrator.execute("INSERT INTO dev09a1_recovery.fixture_security_ledger VALUES ('synthetic_s1')")
            committing = c.transition(security_state,'commit_requested')
            unknown = c.transition(committing,'connection_lost')
            check('commit_ack_loss_is_unknown_not_rollback', unknown.phase=='UNKNOWN')
            check('independent_inspection_committed_both', admin.execute(
                'SELECT value FROM dev09a1_recovery.fixture_security_ledger').fetchall()==[('synthetic_s1',)])
            try:
                c.transition(unknown,'begin_security')
            except c.Refused:
                CHECKS.append('no_replay_after_unknown_commit')
            else:
                raise AssertionError('unknown_retry_allowed')
            check('synthetic_revision_drift_blocks', c.transition(state,'revision_drift').phase=='DRIFT')
        empty_application(admin)
        role_rows = admin.execute('SELECT rolname,rolcanlogin,rolsuper,rolcreatedb,rolcreaterole,'
                                 'rolreplication,rolbypassrls FROM pg_roles WHERE rolname=ANY(%s) ORDER BY rolname',
                                 (list(roles.values()),)).fetchall()
    # No connection attempt towards any operational address: inspect routes only.
    defaults = [line for line in Path('/proc/net/route').read_text().splitlines()[1:]
                if line.split()[1] == '00000000']
    check('no_ipv4_default_route', not defaults)
    print(json.dumps({'status': 'PASS', 'checks': CHECKS, 'passed': len(CHECKS),
                      'database': database, 'system_identifier': identity,
                      'server_version_num': version, 'tls': 'verify-full',
                      'roles': role_rows, 'fixture_schema': 'dev09a1_fixture',
                      'application_schemas_and_ledgers': 'ABSENT',
                      'migrations_executed': False, 'readiness_authority': False}))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Never print driver/SQL errors, connection settings, locals or passwords.
        import traceback
        frame = traceback.extract_tb(error.__traceback__)[-1]
        print(json.dumps({'status': 'FAIL', 'type': type(error).__name__,
                          'sqlstate': getattr(error, 'sqlstate', None), 'line': frame.lineno}))
        raise SystemExit(1) from None
