from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import multiprocessing
import threading
import unittest

import psycopg

from harness import Harness
from laboratory import Approval, Laboratory, binding


def process_change(authority, reference, namespace, identifier, attempt, crash=None, queue=None):
    result = Laboratory(authority, reference, namespace).change(
        'admit', Approval(identifier), binding(attempt), crash=crash)
    if queue is not None:
        queue.put(result)


def crash_revocation(authority, reference, namespace):
    Laboratory(authority, reference, namespace).change('revoke', scope='approval',
                                                      subject='approval', crash='after_local_commit')


class Experiments(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.harness = Harness()
        cls.measurements = {}

    @classmethod
    def tearDownClass(cls):
        cls.harness.close()

    def setUp(self):
        self.lab = self.harness.laboratory()

    def admit(self, lab=None, identifier='approval', attempt='attempt', **options):
        return (lab or self.lab).change('admit', Approval(identifier), binding(attempt), **options)

    def state(self, lab=None):
        with psycopg.connect((lab or self.lab).authority_dsn) as connection:
            return connection.execute('SELECT head,digest,quarantined FROM state').fetchone()

    def test_thread_contention(self):
        barrier = threading.Barrier(24)
        def contender(index):
            barrier.wait()
            return self.admit(attempt=f'attempt-{index}')
        with ThreadPoolExecutor(24) as pool:
            results = list(pool.map(contender, range(24)))
        self.assertEqual(sum(item['state'] == 'ADMITTED' for item in results), 1)
        self.assertEqual(self.state()[0], 1)
        self.measurements['threads'] = dict(contenders=24, admissions=1)

    def test_process_contention(self):
        context = multiprocessing.get_context('spawn')
        queue = context.Queue()
        processes = [context.Process(target=process_change, args=(self.lab.authority_dsn,
            self.lab.reference_dsn, self.lab.namespace, 'approval', f'p-{index}', None, queue))
            for index in range(8)]
        for process in processes:
            process.start()
        for process in processes:
            process.join(15)
            self.assertEqual(process.exitcode, 0)
        results = [queue.get(timeout=3) for process in processes]
        self.assertEqual(sum(item['state'] == 'ADMITTED' for item in results), 1)
        self.measurements['processes'] = dict(contenders=8, admissions=1)

    def test_revocation_before_all_scopes(self):
        for scope, subject in [('approval', 'approval'), ('key', 'key'),
                               ('authority', 'authority'), ('policy', '1')]:
            with self.subTest(scope=scope):
                lab = self.harness.laboratory()
                revoked = lab.change('revoke', scope=scope, subject=subject)
                self.assertEqual(revoked['seq'], 1)
                self.assertEqual(self.admit(lab)['reason'], 'REVOKED')

    def test_revocation_after_does_not_release(self):
        admitted = self.admit()
        revoked = self.lab.change('revoke', scope='approval', subject='approval')
        self.assertEqual((admitted['seq'], revoked['seq']), (1, 2))
        self.assertIsNotNone(self.lab.observe('approval')['record'])
        self.assertEqual(self.admit(attempt='new')['state'], 'BLOCKED')

    def test_revocation_races_persistent_order(self):
        orders = []
        for index in range(12):
            lab = self.harness.laboratory()
            barrier = threading.Barrier(2)
            def admit():
                barrier.wait()
                return self.admit(lab)
            def revoke():
                barrier.wait()
                return lab.change('revoke', scope='approval', subject='approval')
            with ThreadPoolExecutor(2) as pool:
                admission = pool.submit(admit)
                revocation = pool.submit(revoke)
                admitted, revoked = admission.result(), revocation.result()
            if admitted['state'] == 'ADMITTED':
                self.assertLess(admitted['seq'], revoked['seq'])
            else:
                self.assertEqual(admitted['reason'], 'REVOKED')
                self.assertEqual(revoked['seq'], 1)
            orders.append([admitted['state'], revoked['seq']])
        self.measurements['revocation_races'] = orders

    def test_revocation_pending_is_not_effective(self):
        self.assertEqual(self.lab.request_revocation('approval', 'approval')['effective'], False)
        self.assertEqual(self.admit()['state'], 'ADMITTED')

    def test_lost_admission_response_consumed(self):
        self.assertEqual(self.admit(lose_response=True)['state'], 'UNKNOWN')
        observed = self.lab.observe('approval')
        self.assertIsNotNone(observed['record'])
        self.assertFalse(observed['executable'])
        self.assertFalse(observed['resume'])
        self.assertEqual(self.admit(attempt='retry')['reason'], 'CONSUMED')

    def test_lost_revocation_response_remains_effective(self):
        result = self.lab.change('revoke', scope='approval', subject='approval', lose_response=True)
        self.assertEqual(result['state'], 'UNKNOWN')
        self.assertEqual(self.admit()['reason'], 'REVOKED')

    def crash(self, stage, code):
        context = multiprocessing.get_context('spawn')
        process = context.Process(target=process_change, args=(self.lab.authority_dsn,
            self.lab.reference_dsn, self.lab.namespace, 'approval', 'attempt', stage))
        process.start()
        process.join(15)
        self.assertEqual(process.exitcode, code)

    def test_crash_before_reservation_no_admission(self):
        self.crash('before_reserve', 71)
        self.assertIsNone(self.lab.observe('approval')['record'])
        self.assertEqual(self.admit()['state'], 'ADMITTED')

    def test_crash_after_reference_reservation_quarantines(self):
        self.crash('after_reserve', 72)
        self.assertIsNone(self.lab.observe('approval')['record'])
        self.assertEqual(self.admit()['reason'], 'CONTINUITY_UNKNOWN')
        self.assertTrue(self.state()[2])
        self.assertEqual(self.admit(identifier='fresh')['state'], 'BLOCKED')

    def test_crash_after_local_commit_consumed_blocked(self):
        self.crash('after_local_commit', 73)
        self.assertIsNotNone(self.lab.observe('approval')['record'])
        self.assertEqual(self.admit()['reason'], 'CONTINUITY_UNKNOWN')

    def test_crash_after_reference_commit_no_reissue(self):
        self.crash('after_reference_commit', 74)
        self.assertIsNotNone(self.lab.observe('approval')['record'])
        self.assertEqual(self.admit()['reason'], 'CONSUMED')

    def test_revocation_crash_order_unknown_blocks_new_admissions(self):
        context = multiprocessing.get_context('spawn')
        process = context.Process(target=crash_revocation,
            args=(self.lab.authority_dsn, self.lab.reference_dsn, self.lab.namespace))
        process.start()
        process.join(15)
        self.assertEqual(process.exitcode, 73)
        self.assertEqual(self.admit(identifier='unrelated')['reason'], 'CONTINUITY_UNKNOWN')
        with psycopg.connect(self.lab.authority_dsn) as connection:
            self.assertEqual(connection.execute('SELECT scope,subject,seq FROM revoked').fetchone(),
                             ('approval', 'approval', 1))

    def test_ambiguous_confirmation_blocks_delivery(self):
        result = self.admit(fail_ack=True)
        self.assertEqual(result['state'], 'UNKNOWN')
        self.assertFalse(result['executable'])
        self.assertEqual(self.admit()['reason'], 'CONSUMED')

    def test_historical_snapshot_shared_current_reference(self):
        dump = self.harness.authority.dump(self.lab.authority_dsn)
        self.assertEqual(self.admit()['state'], 'ADMITTED')
        restored = self.harness.clone(self.lab, dump)
        self.assertEqual(self.admit(restored)['reason'], 'CONTINUITY_UNKNOWN')
        self.assertTrue(self.state(restored)[2])
        self.measurements['historical_snapshot'] = dict(stale_head=0, reference_head=1,
                                                       new_admissions=0, quarantined=True)

    def test_concurrent_identical_clones_shared_reference(self):
        clone = self.harness.clone(self.lab)
        barrier = threading.Barrier(2)
        def contender(lab):
            barrier.wait()
            return self.admit(lab)
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(contender, [self.lab, clone]))
        self.assertEqual(sum(item['state'] == 'ADMITTED' for item in results), 1)
        self.assertIn('CONTINUITY_UNKNOWN', [item.get('reason') for item in results])
        self.measurements['identical_clones'] = dict(admissions=1, blocked=1,
                                                    same_binding=True, same_namespace=True)

    def test_clones_different_approvals_one_branch_advances(self):
        clone = self.harness.clone(self.lab)
        barrier = threading.Barrier(2)
        def contender(pair):
            lab, identifier = pair
            barrier.wait()
            return self.admit(lab, identifier=identifier, attempt=identifier)
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(contender, [(self.lab, 'first'), (clone, 'second')]))
        self.assertEqual(sum(item['state'] == 'ADMITTED' for item in results), 1)
        self.assertIn('CONTINUITY_UNKNOWN', [item.get('reason') for item in results])

    def test_stale_branch_cannot_repair_by_epoch(self):
        clone = self.harness.clone(self.lab)
        self.admit()
        self.assertEqual(clone.change('controls', controls=(2, 2))['reason'], 'CONTINUITY_UNKNOWN')
        self.assertEqual(self.admit(clone, identifier='new')['state'], 'BLOCKED')

    def test_full_reference_clone_split_brain_counterexample(self):
        authority_dump = self.harness.authority.dump(self.lab.authority_dsn)
        reference_dump = self.harness.reference.dump(self.lab.reference_dsn)
        isolated_reference = self.harness.reference.restore(reference_dump)
        clone = Laboratory(self.harness.authority.restore(authority_dump), isolated_reference,
                           self.lab.namespace)
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(lambda lab: self.admit(lab), [self.lab, clone]))
        self.assertEqual(sum(item['state'] == 'ADMITTED' for item in results), 2)
        self.measurements['split_brain_counterexample'] = dict(admissions=2,
            reason='both branches have a copied reference; expected limitation')

    def test_reference_unavailable_no_fallback(self):
        self.harness.reference.stop('immediate')
        try:
            self.assertEqual(self.admit()['state'], 'BLOCKED')
            self.assertIsNone(self.lab.observe('approval')['record'])
        finally:
            self.harness.reference.start()
        self.assertEqual(self.admit()['state'], 'ADMITTED')

    def test_restart_both_clusters_preserves_all_state(self):
        bound = binding('attempt')
        self.assertEqual(self.lab.change('admit', Approval('approval'), bound)['state'], 'ADMITTED')
        self.lab.change('revoke', scope='key', subject='key')
        self.lab.change('controls', controls=(2, 3))
        before = self.state()
        self.harness.authority.stop('immediate')
        self.harness.reference.stop('immediate')
        self.harness.authority.start()
        self.harness.reference.start()
        self.assertEqual(self.state(), before)
        self.assertEqual(self.lab.observe('approval')['record'][1], bound)
        self.assertEqual(self.admit()['state'], 'BLOCKED')
        with psycopg.connect(self.lab.authority_dsn) as connection:
            self.assertEqual(connection.execute('SELECT epoch,policy FROM controls').fetchone(), (2, 3))
            self.assertEqual(connection.execute('SELECT count(*) FROM revoked').fetchone()[0], 1)
        self.assertEqual(self.lab.change('admit', Approval('new', key='other', epoch=2, policy=3),
                                        binding('new'))['seq'], 4)

    def test_pending_survives_postgres_crash_restart(self):
        self.crash('after_local_commit', 73)
        for cluster in self.harness.clusters:
            cluster.stop('immediate')
            cluster.start()
        self.assertEqual(self.admit()['reason'], 'CONTINUITY_UNKNOWN')

    def test_reference_rollback_detected(self):
        snapshot = self.harness.reference.dump(self.lab.reference_dsn)
        self.admit()
        rolled_back = self.harness.reference.restore(snapshot)
        lab = Laboratory(self.lab.authority_dsn, rolled_back, self.lab.namespace)
        self.assertEqual(self.admit(lab, identifier='new')['reason'], 'CONTINUITY_UNKNOWN')

    def test_journal_corruption_detected(self):
        self.admit()
        with psycopg.connect(self.lab.authority_dsn) as connection:
            connection.execute("UPDATE events SET payload='{}'")
        self.assertEqual(self.admit(identifier='new')['reason'], 'CONTINUITY_UNKNOWN')

    def test_materialized_consumption_tampering_detected(self):
        self.admit()
        with psycopg.connect(self.lab.authority_dsn) as connection:
            connection.execute('DELETE FROM consumed')
        self.assertEqual(self.admit()['reason'], 'CONTINUITY_UNKNOWN')

    def test_attempt_binding_is_durable_and_untransferable(self):
        self.admit()
        original = self.lab.observe('approval')['record']
        for field in binding('attempt'):
            changed = binding('attempt')
            changed[field] = 'changed'
            self.assertEqual(self.lab.change('admit', Approval('approval'), changed)['state'], 'BLOCKED')
        self.assertEqual(self.lab.observe('approval')['record'], original)
        self.assertEqual(self.admit(identifier='different')['state'], 'BLOCKED')

    def test_controls_cannot_regress(self):
        self.assertEqual(self.lab.change('controls', controls=(2, 3))['state'], 'CONFIRMED')
        for values in [(1, 3), (2, 2), (2, 3), (True, 4)]:
            self.assertEqual(self.lab.change('controls', controls=values)['reason'], 'INVALID_CONTROLS')

    def test_target_direct_sql_bypass_counterexample(self):
        target = self.harness.authority.database()
        self.assertEqual(self.admit()['state'], 'ADMITTED')
        with psycopg.connect(target) as connection:
            connection.execute('CREATE TABLE lab_target (value integer NOT NULL)')
            connection.execute('INSERT INTO lab_target VALUES (0)')
        for initiation in range(2):
            with psycopg.connect(target) as connection:
                connection.execute('UPDATE lab_target SET value=value+1')
        with psycopg.connect(target) as connection:
            self.assertEqual(connection.execute('SELECT value FROM lab_target').fetchone()[0], 2)
        self.assertEqual(self.admit()['reason'], 'CONSUMED')
        self.measurements['target_counterexample'] = dict(admissions=1, direct_sql_updates=2,
                                                          target_exclusivity_demonstrated=False)

    def test_utc_boundaries_and_invalid_interval(self):
        for lower, upper, expected in [(100, 100, 'ADMITTED'), (999, 1000, 'BLOCKED'),
                                        (99, 100, 'BLOCKED'), (201, 200, 'BLOCKED')]:
            with self.subTest(lower=lower, upper=upper):
                lab = self.harness.laboratory()
                self.assertEqual(self.admit(lab, lower=lower, upper=upper)['state'], expected)

    def test_unknown_time_persistent_quarantine(self):
        for options in [dict(trusted=False), dict(continuous=False)]:
            lab = self.harness.laboratory()
            self.assertEqual(self.admit(lab, **options)['reason'], 'TIME_UNKNOWN')
            self.assertEqual(self.admit(lab)['state'], 'BLOCKED')

    def test_invalid_version_epochs_policy_duration(self):
        for changes in [dict(version='1'), dict(version=2), dict(epoch=2),
                        dict(policy=2), dict(expires=1001), dict(not_before=1000)]:
            with self.subTest(changes=changes):
                result = self.lab.change('admit', replace(Approval('approval'), **changes), binding('attempt'))
                self.assertEqual(result['reason'], 'INELIGIBLE')

    def test_commit_may_follow_expiration(self):
        evaluated, release = threading.Event(), threading.Event()
        interval = [999, 999, True, True]
        with ThreadPoolExecutor(1) as pool:
            result = pool.submit(self.admit, clock=lambda: tuple(interval), evaluated=evaluated, hold=release)
            self.assertTrue(evaluated.wait(5))
            interval[:2] = [1001, 1001]
            release.set()
            self.assertEqual(result.result()['state'], 'ADMITTED')
        self.measurements['expiry'] = 'Injected interval at A only; no authenticated clock or physical deadline'

    def test_expiry_during_reference_lock_wait(self):
        acquired, release, clock_read = threading.Event(), threading.Event(), threading.Event()
        interval = [999, 999, True, True]
        def blocker():
            with psycopg.connect(self.lab.reference_dsn, autocommit=True) as reference:
                reference.execute('SELECT pg_advisory_lock(hashtextextended(%s,0))', (self.lab.namespace,))
                acquired.set()
                self.assertTrue(release.wait(5))
        def clock():
            clock_read.set()
            return tuple(interval)
        with ThreadPoolExecutor(2) as pool:
            blocked = pool.submit(blocker)
            self.assertTrue(acquired.wait(5))
            attempt = pool.submit(self.admit, clock=clock)
            self.assertFalse(clock_read.wait(0.1))
            interval[:2] = [1000, 1000]
            release.set()
            blocked.result()
            self.assertEqual(attempt.result()['reason'], 'INELIGIBLE')

    def test_no_executable_capability_or_automatic_resume(self):
        result = self.admit()
        self.assertFalse(result['executable'])
        self.assertFalse(result['resume'])
        self.assertFalse(self.lab.observe('approval')['resume'])

    def test_caller_rollback_savepoint_does_not_release(self):
        with psycopg.connect(self.lab.authority_dsn) as caller:
            caller.execute('CREATE TEMP TABLE caller(value integer)')
            caller.execute('SAVEPOINT before_admission')
            self.assertEqual(self.admit()['state'], 'ADMITTED')
            caller.execute('ROLLBACK TO SAVEPOINT before_admission')
            caller.rollback()
        self.assertEqual(self.admit(attempt='retry')['reason'], 'CONSUMED')

    def test_socket_and_durability_configuration(self):
        config = []
        for cluster in self.harness.clusters:
            with psycopg.connect(cluster.dsn()) as connection:
                settings = {name: connection.execute('SELECT current_setting(%s)', (name,)).fetchone()[0]
                            for name in ['listen_addresses', 'unix_socket_permissions', 'fsync',
                                         'synchronous_commit', 'full_page_writes']}
                self.assertEqual(settings['listen_addresses'], '')
                self.assertEqual(settings['unix_socket_permissions'], '0700')
                for name in ['fsync', 'synchronous_commit', 'full_page_writes']:
                    self.assertEqual(settings[name], 'on')
                self.assertEqual(connection.execute('SELECT inet_server_addr()').fetchone(), (None,))
                config.append(settings)
                self.measurements['postgres_version'] = connection.execute('SELECT version()').fetchone()[0]
        self.measurements['postgres_settings'] = config


if __name__ == '__main__':
    unittest.main(verbosity=2)
