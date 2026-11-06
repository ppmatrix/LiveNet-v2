from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import multiprocessing
import os
from pathlib import Path
import threading
import time
import unittest

import psycopg
from psycopg import sql

from experiment import Boundary, Harness, Laboratory, crash_worker


class Experiments(unittest.TestCase):
    measurements = {}

    @classmethod
    def setUpClass(cls):
        cls.harness = Harness()

    @classmethod
    def tearDownClass(cls):
        cls.harness.close()

    def setUp(self):
        self.lab = Boundary(self.harness)
        self.sessions = []

    def tearDown(self):
        for session in self.sessions:
            session.close()

    def admitted(self, lab=None, approval='approval', **options):
        lab = lab or self.lab
        session = lab.session()
        self.sessions.append(session)
        ticket, result = lab.admit(session, approval=approval, d09_assumed=True, **options)
        self.assertEqual(result['state'], 'ADMITTED', result)
        self.assertFalse(result['executable'])
        return session, ticket

    def counts(self, starts, effects, lab=None):
        self.assertEqual((lab or self.lab).observe(),
                         dict(starts=starts, effects=effects, executable=False, resume=False))

    def denied(self, dsn, command):
        with psycopg.connect(dsn, autocommit=True) as connection:
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                connection.execute(command)

    def test_default_d09_blocks(self):
        session = self.lab.session()
        self.sessions.append(session)
        ticket, result = self.lab.admit(session)
        self.assertIsNone(ticket)
        self.assertEqual(result['reason'], 'D09_UNDEMONSTRATED')
        self.counts(0, 0)

    def test_first_start_and_replay(self):
        session, ticket = self.admitted()
        self.assertEqual(self.lab.initiate(session, ticket), 'OBSERVED')
        self.assertEqual(self.lab.initiate(session, ticket), 'BLOCKED_BINDING')
        self.counts(1, 1)

    def test_rollback_does_not_release_claim(self):
        session, ticket = self.admitted()
        self.assertEqual(self.lab.initiate(session, ticket, rollback=True), 'OBSERVED')
        self.counts(1, 0)
        self.assertEqual(self.lab.initiate(session, ticket), 'BLOCKED_BINDING')

    def test_savepoint_does_not_release_claim(self):
        session, ticket = self.admitted()
        self.assertEqual(self.lab.initiate(session, ticket, savepoint=True), 'OBSERVED')
        self.counts(1, 0)
        self.assertEqual(self.lab.initiate(session, ticket), 'BLOCKED_BINDING')

    def test_preexisting_savepoint_does_not_duplicate(self):
        session, ticket = self.admitted()
        session.connection.execute('SAVEPOINT before_effect')
        session.connection.execute('ROLLBACK TO SAVEPOINT before_effect')
        self.assertEqual(self.lab.initiate(session, ticket), 'OBSERVED')
        self.counts(1, 1)

    def test_session_reconnection_blocked(self):
        session, ticket = self.admitted()
        session.close()
        replacement = self.lab.session()
        self.sessions.append(replacement)
        self.assertEqual(self.lab.initiate(replacement, ticket), 'BLOCKED_BINDING')
        self.counts(0, 0)

    def test_transaction_replacement_blocked(self):
        session, ticket = self.admitted()
        session.connection.execute('ROLLBACK')
        session.connection.execute('BEGIN')
        self.assertEqual(self.lab.initiate(session, ticket), 'BLOCKED_BINDING')
        self.counts(0, 0)

    def test_ticket_binding_mutations_blocked(self):
        session, ticket = self.admitted()
        for field, value in (('approval', 'forged'), ('attempt', 'forged'),
                             ('epoch', 99), ('incarnation', 'forged'),
                             ('generation', 'forged'), ('digest', 'forged'),
                             ('backend', 1), ('transaction_id', 1)):
            self.assertEqual(self.lab.initiate(session, replace(ticket, **{field: value})),
                             'BLOCKED_BINDING')
        self.counts(0, 0)

    def test_concurrent_replay_same_live_session(self):
        session, ticket = self.admitted()
        barrier = threading.Barrier(8)
        def replay(index):
            barrier.wait(5)
            return self.lab.initiate(session, ticket)
        with ThreadPoolExecutor(8) as pool:
            results = list(pool.map(replay, range(8)))
        self.assertEqual(results.count('OBSERVED'), 1)
        self.assertTrue(all(value in ('OBSERVED', 'CONSUMED', 'BLOCKED_BINDING')
                            for value in results))
        self.counts(1, 1)
        self.measurements['concurrent_replay'] = results

    def test_unique_approval_and_attempt_on_target(self):
        session, ticket = self.admitted()
        self.lab.initiate(session, ticket)
        for duplicate in (replace(ticket, attempt='different'),
                          replace(ticket, approval='different')):
            with psycopg.connect(self.lab.service_dsn) as connection:
                with self.assertRaises(psycopg.errors.UniqueViolation):
                    connection.execute('INSERT INTO starts VALUES(%s,%s,%s,%s,%s,%s,%s,%s)',
                        tuple(getattr(duplicate, field) for field in duplicate.__dataclass_fields__))
        self.counts(1, 1)

    def test_executor_direct_update_denied(self):
        self.denied(self.lab.worker_dsn, 'UPDATE payload SET value=value+1')
        self.counts(0, 0)

    def test_executor_cannot_erase_or_forge_claim(self):
        for command in ('DELETE FROM starts', 'TRUNCATE starts',
                        "INSERT INTO starts VALUES('a','b',1,'c','d',1,1,'e')",
                        'ALTER TABLE starts DISABLE TRIGGER ALL'):
            self.denied(self.lab.worker_dsn, command)

    def test_executor_cannot_rotate_fence_or_create_function(self):
        for command in ('UPDATE fence SET epoch=epoch+1', 'SET ROLE target_service',
                        "CREATE FUNCTION public.bypass() RETURNS integer LANGUAGE SQL AS 'SELECT 1'"):
            self.denied(self.lab.worker_dsn, command)

    def test_reference_runtime_roles_cannot_rewrite_continuity(self):
        for role in ('executor', 'authority_client', 'reference_reader'):
            dsn = psycopg.conninfo.make_conninfo(self.harness.reference_dsn, user=role)
            for command in ('UPDATE continuity SET head=0', 'DELETE FROM claims',
                            'TRUNCATE receipts', 'SET ROLE target_service'):
                if command == 'SET ROLE target_service':
                    continue
                self.denied(dsn, command)
        dsn = psycopg.conninfo.make_conninfo(self.harness.reference_dsn, user='reference_reader')
        with psycopg.connect(dsn) as connection:
            self.assertIsNotNone(connection.execute('SELECT count(*) FROM continuity').fetchone())

    def test_privileged_target_bypass_counterexample(self):
        session, ticket = self.admitted()
        self.lab.initiate(session, ticket)
        with psycopg.connect(self.lab.service_dsn) as connection:
            connection.execute('UPDATE payload SET value=value+1')
        self.counts(1, 2)
        self.measurements['privileged_bypass'] = self.lab.observe()

    def test_reference_same_os_user_impersonation_counterexample(self):
        with psycopg.connect(self.harness.reference_dsn) as connection:
            self.assertTrue(connection.execute(
                'SELECT rolsuper FROM pg_roles WHERE rolname=current_user').fetchone()[0])
        self.measurements['administrative_segregation'] = 'SQL roles only; same OS administrator can bypass'

    def test_service_roles_have_no_administrative_membership(self):
        for dsn, tables in ((self.lab.service_dsn, ('starts', 'fence')),
                            (self.harness.reference_service_dsn, ('claims', 'continuity'))):
            for table in tables:
                self.denied(dsn, 'TRUNCATE ' + table)
            with psycopg.connect(dsn, autocommit=True) as connection:
                rights = connection.execute('SELECT rolsuper,rolcreaterole,rolcreatedb,rolreplication '
                                            'FROM pg_roles WHERE rolname=current_user').fetchone()
                self.assertEqual(rights, (False, False, False, False))
                with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                    connection.execute(sql.SQL('SET ROLE {}').format(sql.Identifier(os.environ['USER'])))

    def test_fence_old_live_session(self):
        old, ticket = self.admitted()
        self.lab.fence()
        self.assertEqual(self.lab.initiate(old, ticket), 'FENCED')
        self.counts(0, 0)
        fresh, fresh_ticket = self.admitted(approval='fresh-human-approved-request')
        self.assertEqual(self.lab.initiate(fresh, fresh_ticket), 'OBSERVED')
        self.counts(1, 1)

    def test_fence_between_claim_and_effect(self):
        session, ticket = self.admitted()
        claimed, proceed = threading.Event(), threading.Event()
        with ThreadPoolExecutor(1) as pool:
            future = pool.submit(self.lab.initiate, session, ticket,
                                 claimed=claimed, proceed=proceed)
            try:
                self.assertTrue(claimed.wait(5))
                self.lab.fence()
            finally:
                proceed.set()
            self.assertEqual(future.result(5), 'FENCED')
        self.counts(1, 0)

    def test_fence_waits_for_inflight_effect(self):
        session, ticket = self.admitted()
        ready, proceed, fence_started = threading.Event(), threading.Event(), threading.Event()
        def rotate():
            fence_started.set()
            return self.lab.fence()
        with ThreadPoolExecutor(2) as pool:
            operation = pool.submit(self.lab.initiate, session, ticket,
                                    effect_ready=ready, effect_proceed=proceed)
            try:
                self.assertTrue(ready.wait(5))
                rotation = pool.submit(rotate)
                self.assertTrue(fence_started.wait(5))
                time.sleep(0.1)
                self.assertFalse(rotation.done())
            finally:
                proceed.set()
            self.assertEqual(operation.result(5), 'OBSERVED')
            self.assertEqual(rotation.result(5)[0], 2)
        self.assertIn(self.lab.initiate(session, ticket), ('BLOCKED_BINDING', 'FENCED'))
        self.counts(1, 1)

    def test_concurrent_cloned_authority_same_reference(self):
        cloned = self.harness.clone_authority(self.lab.authority)
        other = Boundary(self.harness, authority=cloned, target=self.lab.target_dsn)
        barrier = threading.Barrier(12)
        def compete(index):
            boundary = self.lab if index % 2 else other
            session = boundary.session()
            try:
                barrier.wait(5)
                ticket, result = boundary.admit(session, d09_assumed=True)
                outcome = boundary.initiate(session, ticket) if ticket else 'BLOCKED'
                return result['state'], outcome
            finally:
                session.close()
        with ThreadPoolExecutor(12) as pool:
            results = list(pool.map(compete, range(12)))
        self.assertEqual(sum(state == 'ADMITTED' for state, _ in results), 1)
        self.counts(1, 1)
        self.measurements['clone_race_12_sessions'] = results

    def test_stale_authority_snapshot_quarantined(self):
        dump = self.harness.authority_cluster.dump(self.lab.authority.authority_dsn)
        self.admitted()
        stale = self.harness.clone_authority(self.lab.authority, dump)
        other = Boundary(self.harness, authority=stale, target=self.lab.target_dsn)
        session = other.session()
        self.sessions.append(session)
        ticket, result = other.admit(session, approval='new', d09_assumed=True)
        self.assertIsNone(ticket)
        self.assertEqual(result['reason'], 'CONTINUITY_UNKNOWN')

    def test_copied_reference_shared_target_still_one_start(self):
        auth_dump = self.harness.authority_cluster.dump(self.lab.authority.authority_dsn)
        ref_dump = self.harness.reference.dump(self.harness.reference_dsn)
        cloned = self.harness.clone_authority(self.lab.authority, auth_dump)
        cloned.reference_dsn = self.harness.reference.restore(ref_dump)
        other = Boundary(self.harness, authority=cloned, target=self.lab.target_dsn)
        session, ticket = self.admitted()
        twin, twin_ticket = self.admitted(other)
        self.assertEqual(self.lab.initiate(session, ticket), 'OBSERVED')
        self.assertEqual(other.initiate(twin, twin_ticket), 'CONSUMED')
        self.counts(1, 1)
        self.measurements['copied_reference_shared_target'] = 'two admissions, one target start'

    def test_copied_reference_and_target_split_brain_counterexample(self):
        auth_dump = self.harness.authority_cluster.dump(self.lab.authority.authority_dsn)
        ref_dump = self.harness.reference.dump(self.harness.reference_dsn)
        target_dump = self.harness.target.dump(self.lab.target_dsn)
        cloned = self.harness.clone_authority(self.lab.authority, auth_dump)
        cloned.reference_dsn = self.harness.reference.restore(ref_dump)
        target = self.harness.target.restore(target_dump)
        with psycopg.connect(target) as connection:
            connection.execute('GRANT USAGE ON SCHEMA public TO target_service')
            connection.execute('GRANT SELECT ON fence TO target_service')
            connection.execute('GRANT SELECT,INSERT ON starts TO target_service')
            connection.execute('GRANT SELECT,UPDATE ON payload TO target_service')
        other = Boundary(self.harness, authority=cloned, target=target)
        session, ticket = self.admitted()
        twin, twin_ticket = self.admitted(other)
        self.lab.initiate(session, ticket)
        other.initiate(twin, twin_ticket)
        self.counts(1, 1)
        self.counts(1, 1, other)
        self.measurements['full_clone_counterexample'] = [self.lab.observe(), other.observe()]

    def test_reference_unavailable_before_admission_blocks(self):
        original = self.lab.authority.reference_dsn
        self.lab.authority.reference_dsn = psycopg.conninfo.make_conninfo(
            original, host=str(self.harness.root / 'nonexistent'))
        session = self.lab.session()
        self.sessions.append(session)
        try:
            ticket, result = self.lab.admit(session, d09_assumed=True)
        finally:
            self.lab.authority.reference_dsn = original
        self.assertIsNone(ticket)
        self.assertEqual(result['state'], 'BLOCKED')
        self.counts(0, 0)

    def test_reference_partition_after_confirmed_admission(self):
        session, ticket = self.admitted()
        self.harness.reference.stop()
        try:
            self.assertEqual(self.lab.initiate(session, ticket), 'OBSERVED')
        finally:
            self.harness.reference.start()
        self.counts(1, 1)

    def test_target_unavailable_no_effect_or_automatic_retry(self):
        session, ticket = self.admitted()
        self.harness.target.stop('immediate')
        try:
            with self.assertRaises(psycopg.OperationalError):
                self.lab.initiate(session, ticket)
        finally:
            self.harness.target.start()
        self.counts(0, 0)
        replacement = self.lab.session()
        self.sessions.append(replacement)
        self.assertEqual(self.lab.initiate(replacement, ticket), 'BLOCKED_BINDING')

    def test_lost_admission_confirmation_consumed_without_ticket(self):
        session = self.lab.session()
        self.sessions.append(session)
        ticket, result = self.lab.admit(session, d09_assumed=True, lose_response=True)
        self.assertIsNone(ticket)
        self.assertEqual(result['state'], 'UNKNOWN')
        observed = self.lab.authority.observe('approval')
        self.assertIsNotNone(observed['record'])
        self.assertFalse(observed['resume'])
        self.assertEqual(self.lab.initiate(session, ticket), 'BLOCKED')
        self.counts(0, 0)

    def test_lost_target_confirmation_observation_cannot_resume(self):
        session, ticket = self.admitted()
        self.assertEqual(self.lab.initiate(session, ticket, lose_response=True), 'UNKNOWN')
        self.counts(1, 1)
        self.assertFalse(self.lab.observe()['resume'])
        self.assertEqual(self.lab.initiate(session, ticket), 'BLOCKED_BINDING')

    def test_lost_claim_confirmation_blocks_effect_and_replay(self):
        session, ticket = self.admitted()
        self.assertEqual(self.lab.initiate(session, ticket, fail_claim_ack=True), 'UNKNOWN')
        self.counts(1, 0)
        self.assertEqual(self.lab.initiate(session, ticket), 'CONSUMED')
        self.counts(1, 0)

    def test_pending_reference_confirmation_never_dispatches(self):
        session = self.lab.session()
        self.sessions.append(session)
        ticket, result = self.lab.admit(session, d09_assumed=True, fail_ack=True)
        self.assertIsNone(ticket)
        self.assertEqual(result['state'], 'UNKNOWN')
        self.counts(0, 0)

    def test_fence_does_not_release_authority_consumption(self):
        session, ticket = self.admitted()
        self.lab.fence()
        replacement = self.lab.session()
        self.sessions.append(replacement)
        fresh_ticket, result = self.lab.admit(replacement, d09_assumed=True)
        self.assertIsNone(fresh_ticket)
        self.assertEqual(result['reason'], 'CONSUMED')
        self.assertEqual(self.lab.initiate(session, ticket), 'FENCED')
        self.counts(0, 0)

    def test_real_process_crash_boundaries(self):
        results = {}
        for stage, expected_code, starts, effects in (
                ('before_claim', 81, 0, 0), ('after_claim', 82, 1, 0),
                ('after_effect', 83, 1, 0), ('after_commit', 84, 1, 1)):
            boundary = Boundary(self.harness)
            process = multiprocessing.get_context('spawn').Process(
                target=crash_worker, args=(boundary, stage))
            process.start()
            process.join(15)
            if process.is_alive():
                process.terminate()
                process.join(5)
                self.fail('crash child timed out')
            self.assertEqual(process.exitcode, expected_code)
            self.counts(starts, effects, boundary)
            self.assertIsNotNone(boundary.authority.observe('approval')['record'])
            replacement = boundary.session()
            self.sessions.append(replacement)
            ticket, result = boundary.admit(replacement, d09_assumed=True)
            self.assertIsNone(ticket)
            self.assertEqual(result['reason'], 'CONSUMED')
            results[stage] = dict(exit_code=process.exitcode, **boundary.observe())
        self.measurements['real_process_crashes'] = results

    def test_wal_recovery_preserves_claim_fence_and_consumption(self):
        session, ticket = self.admitted()
        self.lab.initiate(session, ticket, rollback=True)
        fence = self.lab.fence()
        for cluster in self.harness.clusters:
            cluster.stop('immediate')
        for cluster in self.harness.clusters:
            cluster.start()
        self.counts(1, 0)
        with psycopg.connect(self.lab.target_dsn) as connection:
            self.assertEqual(connection.execute(
                'SELECT epoch,incarnation,generation FROM fence').fetchone(), fence)
        self.assertIsNotNone(self.lab.authority.observe('approval')['record'])
        replacement = self.lab.session()
        self.sessions.append(replacement)
        self.assertEqual(self.lab.initiate(replacement, ticket), 'BLOCKED_BINDING')

    def test_revocation_after_admission_does_not_retroactively_cancel(self):
        session, ticket = self.admitted()
        result = self.lab.authority.change('revoke', scope='approval', subject='approval')
        self.assertEqual(result['state'], 'CONFIRMED')
        self.assertEqual(self.lab.initiate(session, ticket), 'OBSERVED')
        self.counts(1, 1)

    def test_untrusted_time_blocks(self):
        session = self.lab.session()
        self.sessions.append(session)
        ticket, result = self.lab.admit(session, d09_assumed=True, trusted=False)
        self.assertIsNone(ticket)
        self.assertEqual(result['reason'], 'TIME_UNKNOWN')

    def test_private_resources_and_durability(self):
        for cluster in self.harness.clusters:
            self.assertEqual(os.stat(cluster.socket).st_mode & 0o777, 0o700)
            with psycopg.connect(cluster.dsn()) as connection:
                values = {key: connection.execute('SHOW ' + key).fetchone()[0]
                          for key in ('listen_addresses', 'unix_socket_permissions',
                                      'fsync', 'synchronous_commit', 'full_page_writes')}
            self.assertEqual(values, dict(listen_addresses='', unix_socket_permissions='0700',
                                        fsync='on', synchronous_commit='on', full_page_writes='on'))
        self.measurements['private_resources'] = dict(clusters=3, socket_mode='0700', tcp=False,
                                                    fsync=True, synchronous_commit=True)
