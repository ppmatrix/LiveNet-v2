from concurrent.futures import ThreadPoolExecutor
import threading
import unittest

import psycopg

from laboratory import Blocked, Boundary, Lab


class Experiments(unittest.TestCase):
    measurements = {}

    @classmethod
    def setUpClass(cls):
        cls.lab = Lab()

    @classmethod
    def tearDownClass(cls):
        cls.lab.close()

    def setUp(self):
        self.boundary = Boundary(self.lab)

    def ready(self, approval='approval', epoch=1, endpoint=None, **options):
        self.boundary.receipt(approval, epoch, endpoint or self.boundary.target_key, **options)

    def run_effect(self, approval='approval', **options):
        return self.boundary.execute(approval, fixture=True, clock=(100, 102), **options)

    def test_default_gate_no_effect_even_with_receipt(self):
        self.ready()
        with self.assertRaises(Blocked):
            self.boundary.execute('approval', clock=(100, 102))
        self.assertEqual(self.boundary.observe()['claims'], 0)
        self.assertEqual(self.boundary.observe()['effects'], 0)

    def test_verified_fixture_before_effect(self):
        self.ready()
        self.assertEqual(self.run_effect(), 'OBSERVED')
        state = self.boundary.observe()
        self.assertEqual((state['claims'], state['effects']), (1, 1))
        self.measurements['fixture_success'] = state

    def test_missing_receipt_blocks_before_claim(self):
        with self.assertRaises(Blocked):
            self.run_effect()
        self.assertEqual(self.boundary.observe()['claims'], 0)

    def test_receipt_binding_mutations(self):
        self.ready()
        for options in ({'epoch': 2}, {'endpoint': 'copied'}, {'nonce': 'changed'}):
            with self.subTest(options=options), self.assertRaises(Blocked):
                self.run_effect(**options)
        self.assertEqual(self.boundary.observe()['claims'], 0)

    def test_utc_missing_or_interval_invalid(self):
        self.ready()
        for clock in (None, (103, 100), (89, 102), (100, 110), (110, 112)):
            with self.subTest(clock=clock), self.assertRaises(Blocked):
                self.boundary.execute('approval', fixture=True, clock=clock)
        self.assertEqual(self.boundary.observe()['claims'], 0)

    def test_receipt_time_interval_mismatch(self):
        self.ready(lower=99, upper=103)
        with self.assertRaises(Blocked):
            self.run_effect()

    def test_witness_partition_before_claim(self):
        self.ready()
        self.lab.partitions.add('witness')
        try:
            with self.assertRaises(Blocked):
                self.run_effect()
        finally:
            self.lab.partitions.clear()
        self.assertEqual(self.boundary.observe()['claims'], 0)

    def test_witness_rechecked_after_claim(self):
        self.ready()
        try:
            with self.assertRaises(Blocked):
                self.run_effect(after_claim=lambda: self.lab.partitions.add('witness'))
        finally:
            self.lab.partitions.clear()
        state = self.boundary.observe()
        self.assertEqual((state['claims'], state['effects']), (1, 0))

    def test_anchor_partition_after_claim(self):
        self.ready()
        try:
            with self.assertRaises(Blocked):
                self.run_effect(after_claim=lambda: self.lab.partitions.add('anchor'))
        finally:
            self.lab.partitions.clear()
        state = self.boundary.observe()
        self.assertEqual((state['claims'], state['effects']), (1, 0))
        with self.assertRaises(psycopg.errors.UniqueViolation):
            self.run_effect()

    def test_partition_during_takeover_blocks_progress(self):
        self.ready()
        self.lab.partitions.add('anchor')
        try:
            with self.assertRaises(Blocked):
                self.boundary.takeover()
            with self.assertRaises(Blocked):
                self.run_effect()
        finally:
            self.lab.partitions.clear()
        self.assertEqual(self.boundary.observe()['epoch'], 1)

    def test_lost_fence_confirmation_read_does_not_resume(self):
        self.ready()
        self.assertEqual(self.boundary.takeover(lose_response=True), 'UNKNOWN')
        observed = self.boundary.observe()
        self.assertEqual(observed['epoch'], 2)
        self.assertFalse(observed['resume'])
        with self.assertRaises(Blocked):
            self.run_effect()
        self.assertEqual(self.boundary.observe()['claims'], 0)
        self.measurements['lost_fence_ack'] = observed

    def test_old_live_session_fenced(self):
        self.ready()
        with psycopg.connect(self.boundary.target) as old:
            old.execute('SELECT 1')
            self.assertEqual(self.boundary.takeover(), 2)
            with self.assertRaises(Blocked):
                self.run_effect()
            self.assertEqual(old.execute('SELECT 1').fetchone(), (1,))
        self.assertEqual(self.boundary.observe()['effects'], 0)

    def test_fence_between_claim_and_effect(self):
        self.ready()
        with self.assertRaises(Blocked):
            self.run_effect(after_claim=self.boundary.takeover)
        state = self.boundary.observe()
        self.assertEqual((state['claims'], state['effects'], state['epoch']), (1, 0, 2))

    def test_takeover_waits_for_live_guard(self):
        self.ready()
        ready, release, entered = threading.Event(), threading.Event(), threading.Event()
        with ThreadPoolExecutor(max_workers=2) as pool:
            effect = pool.submit(self.run_effect, effect_ready=ready, release=release)
            self.assertTrue(ready.wait(5))
            fence = pool.submit(self.boundary.takeover, entered=entered)
            self.assertTrue(entered.wait(5))
            try:
                with psycopg.connect(self.boundary.anchor_admin) as observer:
                    waiting = False
                    for attempt in range(1000):
                        waiting = observer.execute("SELECT EXISTS(SELECT 1 FROM pg_locks WHERE "
                            "locktype='advisory' AND NOT granted)").fetchone()[0]
                        if waiting:
                            break
                self.assertTrue(waiting)
                self.assertFalse(fence.done())
            finally:
                release.set()
            self.assertEqual(effect.result(timeout=5), 'OBSERVED')
            self.assertEqual(fence.result(timeout=5), 2)
        self.measurements['takeover_waited_for_lock'] = True

    def test_anchor_connection_loss_in_flight_counterexample(self):
        self.ready()
        ready, release = threading.Event(), threading.Event()
        with ThreadPoolExecutor(max_workers=1) as pool:
            effect = pool.submit(self.run_effect, effect_ready=ready, release=release)
            self.assertTrue(ready.wait(5))
            try:
                with psycopg.connect(self.boundary.anchor_admin) as admin:
                    self.assertTrue(admin.execute('SELECT pg_terminate_backend(%s)',
                                                  (self.boundary.guard_pid,)).fetchone()[0])
                self.assertEqual(self.boundary.takeover(), 2)
            finally:
                release.set()
            with self.assertRaises(psycopg.OperationalError):
                effect.result(timeout=5)
        state = self.boundary.observe()
        self.assertEqual((state['epoch'], state['claims'], state['effects']), (2, 1, 1))
        self.measurements['counterexample_guard_loss_old_commit_after_fence'] = state

    def test_anchor_connection_loss_before_sql_counterexample(self):
        self.ready()
        ready, release = threading.Event(), threading.Event()
        self.boundary.before_sql_ready = ready
        self.boundary.before_sql_release = release
        with ThreadPoolExecutor(max_workers=1) as pool:
            effect = pool.submit(self.run_effect)
            self.assertTrue(ready.wait(5))
            try:
                with psycopg.connect(self.boundary.anchor_admin) as admin:
                    self.assertTrue(admin.execute('SELECT pg_terminate_backend(%s)',
                                                  (self.boundary.guard_pid,)).fetchone()[0])
                self.assertEqual(self.boundary.takeover(), 2)
                self.assertEqual(self.boundary.observe()['effects'], 0)
            finally:
                release.set()
            with self.assertRaises(psycopg.OperationalError):
                effect.result(timeout=5)
        state = self.boundary.observe()
        self.assertEqual((state['epoch'], state['claims'], state['effects']), (2, 1, 1))
        self.measurements['counterexample_guard_loss_sql_begins_after_fence'] = state

    def test_claim_ack_lost_no_reconciliation_retry(self):
        self.ready()
        self.assertEqual(self.run_effect(lose_claim=True), 'UNKNOWN')
        state = self.boundary.observe()
        self.assertEqual((state['claims'], state['effects']), (1, 0))
        self.assertFalse(state['resume'])
        with self.assertRaises(psycopg.errors.UniqueViolation):
            self.run_effect()

    def test_commit_ack_lost_no_reconciliation_retry(self):
        self.ready()
        self.assertEqual(self.run_effect(lose_commit=True), 'UNKNOWN')
        state = self.boundary.observe()
        self.assertEqual((state['claims'], state['effects']), (1, 1))
        self.assertFalse(state['resume'])
        with self.assertRaises(psycopg.errors.UniqueViolation):
            self.run_effect()

    def test_rollback_preserves_external_claim(self):
        self.ready()
        self.run_effect(rollback=True)
        state = self.boundary.observe()
        self.assertEqual((state['claims'], state['effects']), (1, 0))
        with self.assertRaises(psycopg.errors.UniqueViolation):
            self.run_effect()

    def test_concurrent_replay_external_claim(self):
        self.ready()
        def attempt():
            try:
                return self.run_effect()
            except psycopg.errors.UniqueViolation:
                return 'CONSUMED'
        with ThreadPoolExecutor(max_workers=8) as pool:
            outcomes = list(pool.map(lambda number: attempt(), range(8)))
        self.assertEqual(outcomes.count('OBSERVED'), 1)
        self.assertEqual(outcomes.count('CONSUMED'), 7)
        self.assertEqual(self.boundary.observe()['effects'], 1)
        self.measurements['concurrent_replay'] = outcomes

    def test_full_physical_clone_old_alive(self):
        self.ready()
        clone = self.lab.physical_clone()
        try:
            database = psycopg.conninfo.conninfo_to_dict(self.boundary.target_admin)['dbname']
            clone_admin = clone.dsn(database)
            clone_broker = clone.dsn(database, 'broker')
            with psycopg.connect(self.boundary.target_admin) as original, psycopg.connect(clone_admin) as copied:
                first = original.execute('SELECT system_identifier FROM pg_control_system()').fetchone()[0]
                second = copied.execute('SELECT system_identifier FROM pg_control_system()').fetchone()[0]
                self.assertEqual(first, second)
            from laboratory import endpoint_identity
            self.boundary.pins['target'] = endpoint_identity(self.boundary.target)
            self.boundary.target_key = self.boundary.key(self.boundary.pins['target'])
            self.boundary.takeover()
            self.ready('new', epoch=2)
            with self.assertRaises(Blocked):
                self.run_effect('new', epoch=2, target_dsn=clone_broker)
            with self.assertRaises(Blocked):
                self.run_effect('approval')
            state = self.boundary.observe()
            self.assertEqual(state['effects'], 0)
            self.ready('fresh', epoch=2)
            self.assertEqual(self.run_effect('fresh', epoch=2), 'OBSERVED')
            with self.assertRaises(psycopg.errors.UniqueViolation):
                self.run_effect('fresh', epoch=2, target_dsn=clone_broker)
            with psycopg.connect(clone_admin) as copied:
                self.assertEqual(copied.execute('SELECT value FROM lab.payload').fetchone()[0], 0)
            self.measurements['physical_clone'] = dict(system_identifier_equal=True,
                old_and_clone_alive=True, cloned_endpoint_rejected=True, old_epoch_rejected=True,
                original_effects=1, clone_effects=0, external_claim_blocks_replay=True,
                copied='entire stopped PostgreSQL data directory including roles and WAL; socket config relocated')
        finally:
            clone.stop()

    def test_admin_and_broker_bypass_are_explicit_limits(self):
        with psycopg.connect(self.boundary.target_admin) as admin:
            admin.execute('UPDATE lab.payload SET value=value+1')
        with psycopg.connect(self.boundary.target) as broker:
            broker.execute('SELECT lab.apply_effect()')
        state = self.boundary.observe()
        self.assertEqual((state['claims'], state['effects']), (0, 2))
        self.measurements['privileged_bypass'] = state

    def test_role_and_ownership_inventory(self):
        with psycopg.connect(self.boundary.target_admin) as admin:
            rows = admin.execute("SELECT rolname,rolsuper,rolcreatedb,rolcreaterole,rolreplication,"
                "rolbypassrls,rolcanlogin FROM pg_roles WHERE rolname IN ('executor','broker','effect_owner') "
                "ORDER BY rolname").fetchall()
            self.assertTrue(all(not any(row[1:6]) for row in rows))
            self.assertFalse(next(row for row in rows if row[0] == 'effect_owner')[6])
            self.assertEqual(admin.execute("SELECT count(*) FROM pg_auth_members WHERE member="
                "(SELECT oid FROM pg_roles WHERE rolname='executor')").fetchone()[0], 0)
            self.assertEqual(admin.execute("SELECT pg_get_userbyid(relowner) FROM pg_class "
                "WHERE oid='lab.payload'::regclass").fetchone()[0], 'effect_owner')
            function = admin.execute("SELECT prosecdef,proconfig,pg_get_userbyid(proowner) "
                "FROM pg_proc WHERE oid='lab.apply_effect()'::regprocedure").fetchone()
            self.assertEqual(function, (True, ['search_path=pg_catalog, lab, pg_temp'], 'effect_owner'))
            self.measurements['roles'] = rows
            self.measurements['function'] = function

    def test_executor_cannot_write_anchor_or_witness(self):
        for dsn, statement in ((self.boundary.anchor_admin, "UPDATE control.fence SET epoch=99"),
                               (self.boundary.witness_admin, "INSERT INTO receipts VALUES('fake',1,'x','n',1,2)")):
            restricted = psycopg.conninfo.make_conninfo(dsn, user='executor')
            with self.subTest(statement=statement), self.assertRaises(psycopg.Error):
                with psycopg.connect(restricted) as connection:
                    connection.execute(statement)

    def test_pin_rejects_other_database_on_same_server(self):
        alternate = psycopg.conninfo.make_conninfo(self.boundary.target, dbname='postgres')
        with self.assertRaises(Blocked):
            self.boundary.connect('target', alternate)

    def test_pin_rejects_alternate_anchor_and_witness(self):
        for name in ('anchor', 'witness'):
            alternate = psycopg.conninfo.make_conninfo(getattr(self.boundary, name), dbname='postgres')
            with self.subTest(name=name), self.assertRaises(Blocked):
                self.boundary.connect(name, alternate)

    def test_pin_rejects_wrong_sql_principal(self):
        with self.assertRaises(Blocked):
            self.boundary.connect('target', self.boundary.executor)

    def test_witness_reader_cannot_forge_receipt(self):
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):
            with psycopg.connect(self.boundary.witness) as connection:
                connection.execute("INSERT INTO receipts VALUES('forged',1,'x','n',100,102)")

    def test_anchor_observer_cannot_advance_fence(self):
        observer = psycopg.conninfo.make_conninfo(self.boundary.anchor_admin, user='observer')
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):
            with psycopg.connect(observer) as connection:
                connection.execute('UPDATE control.fence SET epoch=99')


PROBES = {
    'select': 'SELECT * FROM lab.payload',
    'update': 'UPDATE lab.payload SET value=99',
    'insert': 'INSERT INTO lab.payload VALUES(false,99)',
    'delete': 'DELETE FROM lab.payload',
    'truncate': 'TRUNCATE lab.payload',
    'copy_to': 'COPY lab.payload TO STDOUT',
    'copy_from': 'COPY lab.payload FROM STDIN',
    'owner_table': 'ALTER TABLE lab.payload OWNER TO executor',
    'owner_function': 'ALTER FUNCTION lab.apply_effect() OWNER TO executor',
    'alter_function': "ALTER FUNCTION lab.apply_effect() SET search_path=public",
    'drop_function': 'DROP FUNCTION lab.apply_effect()',
    'direct_function': 'SELECT lab.apply_effect()',
    'role_owner': 'SET ROLE effect_owner',
    'role_broker': 'SET ROLE broker',
    'role_superuser': 'SET ROLE paulo',
    'session_authorization': 'SET SESSION AUTHORIZATION broker',
    'grant_self': 'GRANT broker TO executor',
    'grant_table': 'GRANT UPDATE ON lab.payload TO executor',
    'create_schema': 'CREATE SCHEMA injected',
    'create_public': 'CREATE TABLE public.injected(value integer)',
    'create_lab': 'CREATE TABLE lab.injected(value integer)',
    'create_temp': 'CREATE TEMP TABLE payload(value integer)',
    'create_function': 'CREATE FUNCTION lab.injected() RETURNS integer LANGUAGE sql AS $$ SELECT 1 $$',
    'replace_function': 'CREATE OR REPLACE FUNCTION lab.apply_effect() RETURNS integer LANGUAGE sql AS $$ SELECT 99 $$',
    'create_trigger': 'CREATE TRIGGER injected BEFORE UPDATE ON lab.payload FOR EACH ROW EXECUTE FUNCTION suppress_redundant_updates_trigger()',
    'create_rule': 'CREATE RULE injected AS ON DELETE TO lab.payload DO INSTEAD NOTHING',
    'create_extension': 'CREATE EXTENSION dblink WITH SCHEMA lab',
    'prepared_function': 'PREPARE injected AS SELECT lab.apply_effect(); EXECUTE injected',
    'search_path_function': 'SET search_path=pg_temp,public,lab; SELECT lab.apply_effect()',
    'do_function': 'DO $$ BEGIN PERFORM lab.apply_effect(); END $$',
    'upsert': 'INSERT INTO lab.payload VALUES(true,99) ON CONFLICT(id) DO UPDATE SET value=99',
    'server_file': "SELECT pg_read_file('/etc/hostname')",
    'server_program': "COPY (SELECT 1) TO PROGRAM 'true'",
    'large_object_export': "SELECT lo_export(0,'/tmp/r2dev04-never-created')",
}


def sql_probe(statement):
    def test(self):
        with self.assertRaises(psycopg.Error) as raised:
            with psycopg.connect(self.boundary.executor) as connection:
                connection.execute(statement)
        self.assertEqual(raised.exception.sqlstate, '42501')
        self.assertEqual(self.boundary.observe()['effects'], 0)
        self.measurements.setdefault('sql_probes', []).append(dict(sql=statement,
            sqlstate=raised.exception.sqlstate, reason=str(raised.exception).splitlines()[0]))
    return test


for name, statement in PROBES.items():
    setattr(Experiments, 'test_sql_' + name, sql_probe(statement))
