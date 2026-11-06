from concurrent.futures import ThreadPoolExecutor
import threading
import time
import unittest

import psycopg

from resource_lab import Blocked, Lab, Resource, previous


class Experiments(unittest.TestCase):
    measurements = {}

    @classmethod
    def setUpClass(cls):
        cls.lab = Lab()

    @classmethod
    def tearDownClass(cls):
        cls.lab.close()

    def setUp(self):
        self.resource = Resource(self.lab)

    def effect(self, connection, epoch=1, approval='approval'):
        return self.resource.apply(connection, epoch, approval, fixture=True)

    def assert_denied(self, action):
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):
            action()

    def kill_anchor_session(self):
        anchor = psycopg.connect(self.resource.anchor)
        try:
            with psycopg.connect(self.resource.anchor, autocommit=True) as admin:
                self.assertTrue(admin.execute('SELECT pg_terminate_backend(%s)',
                                             (anchor.info.backend_pid,)).fetchone()[0])
        finally:
            anchor.close()

    def test_normal_gate_closed(self):
        with self.resource.connect() as old:
            with self.assertRaises(Blocked):
                self.resource.apply(old, 1, 'approval')
        self.assertEqual(self.resource.state()['value'], 0)

    def test_live_old_session_after_resource_fence(self):
        with self.resource.connect() as old:
            self.resource.drain()
            self.assert_denied(lambda: self.effect(old))
        self.assertEqual(self.resource.state()['value'], 0)

    def test_old_principal_cannot_claim_new_epoch(self):
        self.resource.drain()
        with self.resource.connect() as old:
            self.assert_denied(lambda: self.effect(old, epoch=2))

    def test_anchor_loss_before_sql_resource_rejects_old(self):
        self.resource.claim('approval')
        anchor = psycopg.connect(self.resource.anchor)
        with psycopg.connect(self.resource.anchor, autocommit=True) as admin:
            admin.execute('SELECT pg_terminate_backend(%s)', (anchor.info.backend_pid,))
        self.resource.drain()
        with self.resource.connect() as old:
            self.assert_denied(lambda: self.effect(old))
        anchor.close()
        state = self.resource.state()
        self.assertEqual((state['claims'], state['value']), (1, 0))
        self.measurements['anchor_loss_before_sql_fixed_locally'] = state

    def test_anchor_loss_after_sql_fence_waits_for_commit(self):
        old = self.resource.connect()
        self.resource.claim('approval')
        anchor = psycopg.connect(self.resource.anchor)
        self.effect(old)
        with psycopg.connect(self.resource.anchor, autocommit=True) as admin:
            admin.execute('SELECT pg_terminate_backend(%s)', (anchor.info.backend_pid,))
        started = threading.Event()
        def takeover():
            started.set()
            return self.resource.drain(timeout_ms=5000)
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(takeover)
                self.assertTrue(started.wait(2))
                self.wait_for_resource_waiter()
                self.assertFalse(future.done())
                old.commit()
                receipt = future.result(timeout=6)
            self.assertEqual(receipt['epoch'], 2)
            self.assert_denied(lambda: self.effect(old, approval='late'))
            self.measurements['anchor_loss_before_commit_drained'] = self.resource.state()
        finally:
            old.close()
            anchor.close()

    def wait_for_resource_waiter(self):
        deadline = time.monotonic() + 3
        with psycopg.connect(self.resource.admin, autocommit=True) as admin:
            while time.monotonic() < deadline:
                waiting = admin.execute("SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() "
                    "AND pid<>pg_backend_pid() AND wait_event_type='Lock' AND query LIKE 'UPDATE resource.fence%'").fetchone()[0]
                if waiting:
                    return
                time.sleep(0.01)
        self.fail('takeover never observed waiting for resource lock')

    def test_unfinished_transaction_blocks_confirmation(self):
        with self.resource.connect() as old:
            self.effect(old)
            with self.assertRaises(psycopg.errors.LockNotAvailable):
                self.resource.drain(timeout_ms=100)
            old.rollback()
        self.assertEqual(self.resource.state()['epoch'], 1)

    def test_repeatable_read_old_snapshot_rejected(self):
        with self.resource.connect() as old:
            old.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
            old.execute('SELECT 1')
            self.resource.drain()
            with self.assertRaises(psycopg.errors.SerializationFailure):
                self.effect(old)

    def test_serializable_old_snapshot_rejected(self):
        with self.resource.connect() as old:
            old.execute('SET TRANSACTION ISOLATION LEVEL SERIALIZABLE')
            old.execute('SELECT 1')
            self.resource.drain()
            with self.assertRaises(psycopg.errors.SerializationFailure):
                self.effect(old)

    def test_strict_cessation_before_sql(self):
        old = self.resource.connect()
        old_pid = old.info.backend_pid
        try:
            self.kill_anchor_session()
            receipt = self.resource.strict_takeover()
            self.assertIn(old_pid, [entry[0] for entry in receipt['terminated']])
            self.assertEqual((receipt['epoch'], receipt['old_login'], receipt['old_backends']), (2, False, 0))
            with self.assertRaises(psycopg.OperationalError):
                self.effect(old)
            with self.assertRaises(psycopg.OperationalError):
                self.resource.connect()
            with self.resource.connect(2) as new:
                self.effect(new, 2, 'new-approval')
            self.measurements['local_cessation_receipt'] = receipt
            self.assertEqual(self.resource.state()['value'], 1)
        finally:
            old.close()

    def test_strict_cessation_after_sql_forces_rollback(self):
        old = self.resource.connect()
        try:
            self.resource.claim('approval')
            self.effect(old)
            self.kill_anchor_session()
            receipt = self.resource.strict_takeover()
            with self.assertRaises(psycopg.OperationalError):
                old.commit()
            state = self.resource.state()
            self.assertEqual((state['epoch'], state['claims'], state['value']), (2, 1, 0))
            self.measurements['strict_abort_before_confirmation'] = dict(receipt=receipt, state=state)
        finally:
            old.close()

    def test_strict_multiple_old_sessions_terminated(self):
        sessions = [self.resource.connect() for unused in range(5)]
        try:
            receipt = self.resource.strict_takeover()
            self.assertEqual(len(receipt['terminated']), 5)
            self.assertEqual(receipt['old_backends'], 0)
        finally:
            for session in sessions:
                session.close()

    def test_partition_before_takeover_blocks(self):
        self.resource.partition = True
        with self.assertRaises(Blocked):
            self.resource.strict_takeover()
        self.assertEqual(self.resource.state()['epoch'], 1)

    def test_partition_after_freeze_requires_explicit_recovery(self):
        def partition():
            self.resource.partition = True
        old = self.resource.connect()
        try:
            with self.assertRaises(Blocked):
                self.resource.strict_takeover(after_freeze=partition)
            self.assertEqual(self.resource.state()['epoch'], 1)
            self.assertEqual(self.resource.invocations, 1)
            self.resource.partition = False
            observed = self.resource.state()
            self.assertFalse(observed['resume'])
            self.assertEqual(self.resource.invocations, 1)
            receipt = self.resource.strict_takeover()
            self.assertEqual(receipt['epoch'], 2)
            self.measurements['explicit_recovery_after_freeze'] = receipt
        finally:
            old.close()

    def test_local_fence_cannot_stop_old_writer_on_partitioned_clone(self):
        clone = self.lab.physical_clone()
        clone_dsn = self.resource.clone_dsn(clone)
        self.resource.pin = previous.endpoint_identity(self.resource.admin)
        with psycopg.connect(psycopg.conninfo.make_conninfo(clone_dsn, user='old_writer')) as old_clone:
            old_clone.execute('SELECT 1')
            self.resource.strict_takeover()
            self.effect(old_clone, 1, 'clone-old')
        self.assertEqual(self.resource.state()['value'], 0)
        self.assertEqual(self.resource.state(clone_dsn)['value'], 1)
        self.measurements['clone_survives_local_cessation_counterexample'] = dict(
            original=self.resource.state(), clone=self.resource.state(clone_dsn), distributed_fencing=False)

    def test_historical_snapshot_revives_old_epoch_and_claim(self):
        clone = self.lab.physical_clone()
        historical = self.resource.clone_dsn(clone)
        self.resource.drain()
        with self.resource.connect(2) as new:
            self.effect(new, 2, 'same-approval')
        with psycopg.connect(psycopg.conninfo.make_conninfo(historical, user='old_writer')) as old_clone:
            self.effect(old_clone, 1, 'same-approval')
        original, restored = self.resource.state(), self.resource.state(historical)
        self.assertEqual((original['value'], restored['value']), (1, 1))
        self.measurements['historical_snapshot_counterexample'] = dict(original=original, historical=restored)

    def test_wrong_resource_receipt_and_clone_endpoint_rejected(self):
        clone = self.lab.physical_clone()
        with self.assertRaises(Blocked):
            self.resource.strict_takeover(dsn=self.resource.clone_dsn(clone))
        self.assertEqual(self.resource.state()['epoch'], 1)

    def test_unreachable_old_resource_cannot_use_cached_receipt(self):
        receipt = self.resource.strict_takeover()
        self.assertEqual(receipt['epoch'], 2)
        self.resource.partition = True
        with self.assertRaises(Blocked):
            self.resource.strict_takeover(expected=2)
        self.assertEqual(self.resource.state()['epoch'], 2)

    def test_lost_takeover_confirmation_never_retries(self):
        response = self.resource.strict_takeover(lose_ack=True)
        self.assertEqual(response['status'], 'UNKNOWN')
        for unused in range(3):
            observed = self.resource.state()
            self.assertEqual(observed['epoch'], 2)
            self.assertFalse(observed['resume'])
        self.assertEqual(self.resource.invocations, 1)
        self.assertEqual(observed['value'], 0)

    def test_lost_effect_commit_confirmation_observation_only(self):
        self.resource.claim('approval')
        with self.resource.connect() as old:
            self.effect(old)
        response = dict(status='UNKNOWN', resume=False)
        observed = self.resource.state()
        self.assertEqual((observed['claims'], observed['value']), (1, 1))
        with self.assertRaises(psycopg.errors.UniqueViolation):
            self.resource.claim('approval')
        self.assertFalse(response['resume'])
        self.measurements['lost_effect_ack'] = dict(response=response, observed=observed)

    def test_rollback_external_claim_survives(self):
        self.resource.claim('approval')
        with self.resource.connect() as old:
            self.effect(old)
            old.rollback()
        self.assertEqual((self.resource.state()['claims'], self.resource.state()['value']), (1, 0))
        with self.assertRaises(psycopg.errors.UniqueViolation):
            self.resource.claim('approval')

    def test_same_approval_concurrency_single_resource(self):
        def attempt():
            try:
                with self.resource.connect() as old:
                    self.effect(old)
                return 'committed'
            except psycopg.errors.UniqueViolation:
                return 'duplicate'
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda unused: attempt(), range(8)))
        self.assertEqual(results.count('committed'), 1)
        self.assertEqual(self.resource.state()['value'], 1)

    def test_direct_dml_and_role_forgery_denied(self):
        attacks = ['UPDATE resource.payload SET value=999', 'UPDATE resource.fence SET epoch=1',
            'DELETE FROM resource.effects', "UPDATE resource.incarnations SET epoch=2",
            'SET ROLE new_writer', 'SET SESSION AUTHORIZATION new_writer',
            'ALTER ROLE old_writer LOGIN', 'ALTER FUNCTION resource.apply(bigint,text) SECURITY INVOKER']
        states = []
        for attack in attacks:
            with self.resource.connect() as old:
                with self.assertRaises(psycopg.errors.InsufficientPrivilege) as caught:
                    old.execute(attack)
                states.append(dict(sql=attack, sqlstate=caught.exception.sqlstate))
        self.measurements['restricted_sql_attacks'] = states

    def test_unprivileged_executor_cannot_call_effect(self):
        with psycopg.connect(psycopg.conninfo.make_conninfo(self.resource.admin, user='executor')) as executor:
            self.assert_denied(lambda: self.effect(executor))

    def test_local_receipt_does_not_prove_python_process_stopped(self):
        running = threading.Event()
        release = threading.Event()
        def incarnation():
            running.set()
            release.wait(5)
            return 'old application still running'
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(incarnation)
            self.assertTrue(running.wait(2))
            receipt = self.resource.strict_takeover()
            self.assertFalse(future.done())
            release.set()
            self.assertEqual(future.result(), 'old application still running')
        self.assertFalse(receipt['process_cessation_proven'])

    def test_superuser_bypasses_resource_boundary(self):
        self.resource.strict_takeover()
        with psycopg.connect(self.resource.admin) as admin:
            admin.execute('UPDATE resource.payload SET value=value+1')
        state = self.resource.state()
        self.assertEqual((state['value'], len(state['effects'])), (1, 0))
        self.measurements['admin_bypass_counterexample'] = state

    def test_direct_function_bypasses_external_consumption_but_not_fence(self):
        with self.resource.connect() as old:
            self.effect(old, approval='unclaimed')
        state = self.resource.state()
        self.assertEqual((state['claims'], state['value']), (0, 1))
        self.measurements['external_consumption_still_trusted_broker'] = state

    def test_prepared_statement_old_epoch_rejected(self):
        with self.resource.connect() as old:
            old.execute("PREPARE delayed AS SELECT resource.apply(1,'delayed')")
            old.commit()
            self.resource.drain()
            self.assert_denied(lambda: old.execute('EXECUTE delayed'))

    def test_savepoint_rollback_does_not_release_external_claim(self):
        self.resource.claim('approval')
        with self.resource.connect() as old:
            old.execute('SAVEPOINT before_effect')
            self.effect(old)
            old.execute('ROLLBACK TO SAVEPOINT before_effect')
        self.assertEqual((self.resource.state()['claims'], self.resource.state()['value']), (1, 0))

    def test_prior_committed_effect_not_retracted_by_cessation(self):
        with self.resource.connect() as old:
            self.effect(old)
        self.resource.strict_takeover()
        self.assertEqual(self.resource.state()['value'], 1)

    def test_resource_restart_preserves_fence_and_freeze(self):
        self.resource.strict_takeover()
        self.lab.target.stop()
        self.lab.target.start()
        self.assertEqual(self.resource.state()['epoch'], 2)
        with self.assertRaises(psycopg.OperationalError):
            self.resource.connect()
        with self.assertRaises(Blocked):
            self.resource.strict_takeover(expected=2)
        self.measurements['restart_requires_explicit_new_pin'] = self.resource.state()

    def test_real_old_resource_outage_no_confirmation(self):
        self.lab.target.stop()
        try:
            with self.assertRaises(psycopg.OperationalError):
                self.resource.strict_takeover()
        finally:
            self.lab.target.start()
        self.assertEqual(self.resource.state()['epoch'], 1)

    def test_reconnection_attempts_during_strict_takeover(self):
        old = self.resource.connect()
        started = threading.Event()
        stop = threading.Event()
        def reconnect():
            attempts = 0
            started.set()
            while not stop.is_set() and attempts < 40:
                try:
                    with self.resource.connect() as candidate:
                        candidate.execute('SELECT 1')
                except psycopg.OperationalError:
                    pass
                attempts += 1
            return attempts
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(reconnect)
                self.assertTrue(started.wait(2))
                receipt = self.resource.strict_takeover()
                stop.set()
                attempts = future.result(timeout=5)
            self.assertEqual(receipt['old_backends'], 0)
            with self.assertRaises(psycopg.OperationalError):
                self.resource.connect()
            self.measurements['reconnection_race'] = dict(attempts=attempts, receipt=receipt)
        finally:
            stop.set()
            old.close()

    def test_local_receipt_cannot_confirm_distributed_reentry(self):
        receipt = self.resource.strict_takeover()
        with self.assertRaises(Blocked):
            self.resource.confirm_distributed_reentry(receipt)
        self.assertFalse(receipt['distributed_takeover_confirmed'])

    def test_forged_cessation_flag_cannot_enable_reentry(self):
        with self.assertRaises(Blocked):
            self.resource.confirm_distributed_reentry(dict(distributed_cessation_proven=True))
