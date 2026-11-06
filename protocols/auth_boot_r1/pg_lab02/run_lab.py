"""R1-PG-LAB-02: real isolated experiments, never production enforcement.

Reuses LAB-01 lifecycle checks verbatim; its r1-pg-lab01-* temporary directory
prefix is retained. No existing cluster, credentials, Docker or TCP is used.
Session locks are ephemeral; persistent identity-bound burns are separate.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pg_lab01.run_lab import Lab as IsolatedLab


HERE = Path(__file__).resolve().parent


class Lab02(IsolatedLab):
    def __init__(self):
        super().__init__()
        self.next_key = 1

    def prepare02(self, caller, approval, *, ttl=30):
        caller.execute('BEGIN')
        xid = caller.execute('SELECT txid_current()::text').fetchone()[0]
        with closing(self.connect('lab_writer')) as writer:
            writer.execute('''INSERT INTO lab.burn VALUES
                (%s,%s,%s,%s,%s,'fixed-update-v1','lab-generation-1',1,
                 clock_timestamp()-interval '1 second',
                 clock_timestamp()+%s*interval '1 second')''',
                (approval, approval, caller.info.user, caller.info.backend_pid, xid, ttl))
            writer.execute('INSERT INTO lab02.guard_key VALUES (%s,%s)',
                           (approval, self.next_key))
        self.next_key += 1

    @staticmethod
    def call02(caller, approval, expected=0):
        return caller.execute('SELECT lab02.fixed_update(%s,%s,10)',
                              (approval, expected)).fetchone()[0]

    def run(self):
        self.start('main')
        with closing(self.connect()) as owner:
            owner.execute((HERE.parent / 'pg_lab01' / 'schema.sql').read_text())
            self.record('isolation', postgres=owner.execute('SHOW server_version').fetchone()[0],
                        tcp=False, private_socket=True, all_data_new=True)

        # Reproduce exactly the two relevant LAB-01 problems, not its full suite.
        with closing(self.connect()) as c, closing(self.connect('lab_caller')) as a:
            self.prepare(a, 'old-savepoint')
            a.execute('SAVEPOINT before_entry')
            assert self.call(a, 'old-savepoint') == 1
            a.execute('ROLLBACK TO SAVEPOINT before_entry')
            assert self.call(a, 'old-savepoint') == 1
            a.execute('ROLLBACK')
            self.record('baseline_savepoint_reproduced', successful_entries=2)

            self.prepare(a, 'old-expiry', ttl=.6)
            c.execute('BEGIN')
            c.execute('SELECT * FROM lab.cell WHERE id=1 FOR UPDATE')
            with ThreadPoolExecutor(max_workers=1) as pool:
                work = pool.submit(self.call, a, 'old-expiry')
                self.wait(lambda: c.execute('SELECT %s=ANY(pg_blocking_pids(%s))',
                                           (c.info.backend_pid,a.info.backend_pid)).fetchone()[0])
                self.wait(lambda: c.execute("SELECT clock_timestamp()>=expires_at FROM lab.burn WHERE approval='old-expiry'").fetchone()[0])
                c.execute('ROLLBACK')
                assert work.result(timeout=4) == 1
            a.execute('COMMIT')
            self.record('baseline_expiry_reproduced', mutation_after_expiry=True)
            self.reset_cell(c)

            schema = (HERE / 'schema.sql').read_text()
            c.execute(schema)
            # Admin-only injection creates a deliberate post-check wait. The
            # normal function has NO client-selectable pause or unlock option.
            function = schema[schema.index('CREATE FUNCTION'):schema.index('ALTER FUNCTION')]
            function = function.replace('lab02.fixed_update', 'lab02.fault_after_check')
            function = function.replace('-- LAB02_ADMIN_FAULT_AFTER_CHECK',
                                        'PERFORM pg_advisory_lock(92002,1);')
            c.execute(function)
            c.execute('ALTER FUNCTION lab02.fault_after_check(text,integer,integer) OWNER TO lab_gate')
            c.execute('REVOKE ALL ON FUNCTION lab02.fault_after_check(text,integer,integer) FROM PUBLIC')
            self.refused(lambda: a.execute("SELECT lab.fixed_update('old',0,1)"), '42501')
            self.refused(lambda: a.execute("SELECT lab02.fault_after_check('old',0,1)"), '42501')
            self.record('unsafe_legacy_and_fault_entrypoints_denied', passed=True)
            assert c.execute('''SELECT count(*) FROM pg_proc p
                JOIN pg_namespace n ON n.oid=p.pronamespace
                WHERE n.nspname='pg_catalog'
                  AND (p.proname LIKE 'pg_advisory_%%' OR p.proname LIKE 'pg_try_advisory_%%')
                  AND has_function_privilege('lab_caller',p.oid,'EXECUTE')''').fetchone()[0] == 0

        # Savepoint retry, direct advisory unlocks, DISCARD and new transaction.
        with closing(self.connect()) as c, closing(self.connect('lab_caller')) as a:
            self.prepare02(a, 'guard-savepoint')
            # A malicious caller owns pg_temp and can grant SELECT to the gate.
            # A fake empty pg_locks must NEVER hide the real session marker.
            a.execute('''CREATE TEMP TABLE pg_locks
                (locktype text,pid integer,classid oid,objid oid,objsubid integer,granted boolean)''')
            a.execute('GRANT SELECT ON pg_temp.pg_locks TO lab_gate')
            a.execute('SET LOCAL search_path=pg_temp,public')
            a.execute('SAVEPOINT before_entry')
            assert self.call02(a, 'guard-savepoint') == 1
            a.execute('ROLLBACK TO SAVEPOINT before_entry')
            self.refused(lambda: self.call02(a, 'guard-savepoint'))
            a.execute('ROLLBACK TO SAVEPOINT before_entry')
            for query in (
                'SELECT pg_advisory_unlock_all()',
                'SELECT pg_advisory_unlock(92001,1)',
                'SELECT pg_advisory_unlock(1::bigint)',
                'SELECT pg_advisory_unlock_shared(92001,1)',
                'SELECT pg_try_advisory_lock(92001,1)',
            ):
                self.refused(lambda: a.execute(query), '42501')
                a.execute('ROLLBACK TO SAVEPOINT before_entry')
            self.refused(lambda: a.execute('DISCARD ALL'), '25001')
            a.execute('ROLLBACK TO SAVEPOINT before_entry')
            self.refused(lambda: self.call02(a, 'guard-savepoint'))
            a.execute('ROLLBACK')
            assert c.execute('SELECT row_version FROM lab.cell').fetchone()[0] == 0
            a.execute('DISCARD ALL')  # allowed OUTSIDE transaction, clears guard
            self.refused(lambda: self.call02(a, 'guard-savepoint'))  # old xid binding
            self.record('savepoint_and_unlock_bypasses_refused', passed=True,
                        discard_after_rollback_cannot_reuse_burn=True,
                        malicious_temp_pg_locks_cannot_hide_entry=True,
                        caller_has_no_advisory_api_execute_privilege=True)

            self.refused(lambda: a.execute('UPDATE lab.cell SET value=99'), '42501')
            self.refused(lambda: a.execute('UPDATE lab02.guard_key SET lock_key=999'), '42501')
            self.refused(lambda: a.execute('SET ROLE lab_gate'), '42501')
            self.refused(lambda: a.execute('SET SESSION AUTHORIZATION lab_gate'), '42501')
            self.record('direct_dml_marker_and_role_bypasses_refused', passed=True)

            # Normal corrected path, then reentry after full commit.
            self.prepare02(a, 'normal')
            assert self.call02(a, 'normal') == 1
            a.execute('COMMIT')
            self.refused(lambda: self.call02(a, 'normal'))
            self.reset_cell(c)
            self.record('normal_update_and_post_commit_replay_refused', passed=True)

            # Busy business and policy locks: NOWAIT refuses before final check.
            for table in ('cell', 'policy'):
                label = 'busy-' + table
                self.prepare02(a, label, ttl=.6)
                c.execute('BEGIN')
                c.execute('SELECT * FROM lab.' + table + ' WHERE id=1 FOR UPDATE')
                self.refused(lambda: self.call02(a, label), '55P03')
                a.execute('ROLLBACK')
                c.execute('ROLLBACK')
                assert c.execute('SELECT row_version FROM lab.cell').fetchone()[0] == 0
                assert c.execute('SELECT count(*) FROM lab.burn WHERE approval=%s',(label,)).fetchone()[0] == 1
                self.record(label + '_refused_without_wait', passed=True)

            for label, revoked in (('expired',False), ('revoked',True)):
                self.prepare02(a, label, ttl=30 if revoked else -.1)
                if revoked:
                    c.execute('UPDATE lab.policy SET epoch=2,revoked=true')
                self.refused(lambda: self.call02(a, label))
                a.execute('ROLLBACK')
                self.reset_cell(c)
                self.record(label + '_before_final_check_refused', passed=True)

        # Three sessions: two bound callers + independent administrative observer.
        with closing(self.connect()) as c, closing(self.connect('lab_caller')) as a, \
             closing(self.connect('lab_caller')) as b:
            self.prepare02(a, 'concurrent-a')
            self.prepare02(b, 'concurrent-b')
            assert self.call02(a, 'concurrent-a') == 1  # keeps exclusive table lock
            with ThreadPoolExecutor(max_workers=1) as pool:
                result = pool.submit(self.refused, lambda: self.call02(b,'concurrent-b'), '55P03')
                assert result.result(timeout=3) == '55P03'
            b.execute('ROLLBACK')
            a.execute('COMMIT')
            assert c.execute('SELECT row_version FROM lab.cell').fetchone()[0] == 1
            self.refused(lambda: self.call02(b,'concurrent-a'))  # backend binding
            assert c.execute("SELECT count(*) FROM lab.burn WHERE approval IN ('concurrent-a','concurrent-b')").fetchone()[0] == 2
            self.reset_cell(c)
            self.record('three_session_concurrency_and_cross_backend_replay', passed=True,
                        committed_updates=1, both_burns_preserved=True)

        # Counterexample retained: no relation-lock wait is needed to pause
        # AFTER the final check. Injection is callable only by trusted lab admin.
        with closing(self.connect()) as c, closing(self.connect()) as a:
            self.prepare02(a, 'admin-postcheck-pause', ttl=.6)
            c.execute('SELECT pg_advisory_lock(92002,1)')
            with ThreadPoolExecutor(max_workers=1) as pool:
                work = pool.submit(lambda: a.execute("SELECT lab02.fault_after_check('admin-postcheck-pause',0,10)").fetchone()[0])
                self.wait(lambda: c.execute('SELECT %s=ANY(pg_blocking_pids(%s))',
                                           (c.info.backend_pid,a.info.backend_pid)).fetchone()[0])
                self.wait(lambda: c.execute("SELECT clock_timestamp()>=expires_at FROM lab.burn WHERE approval='admin-postcheck-pause'").fetchone()[0])
                c.execute('SELECT pg_advisory_unlock(92002,1)')
                assert work.result(timeout=4) == 1
            a.execute('COMMIT')
            assert c.execute('SELECT row_version FROM lab.cell').fetchone()[0] == 1
            self.record('admin_only_postcheck_pause_counterexample', mutation_after_expiry=True,
                        normal_caller_can_enable_injection=False,
                        strict_gap002_satisfied=False)

        # Actual unclean restart loses advisory state, but keeps burned context.
        self.stop('main', 'immediate')
        self.launch('main')
        with closing(self.connect()) as c, closing(self.connect('lab_caller')) as a:
            assert c.execute("SELECT count(*) FROM lab.burn WHERE approval='normal'").fetchone()[0] == 1
            self.refused(lambda: self.call02(a, 'normal'))
            self.record('restart_retains_burn_and_rejects_old_context', passed=True,
                        historical_restore_or_clone_safety_proven=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-isolated-lab', action='store_true', required=True)
    parser.parse_args()
    lab = Lab02()
    result = {'task':'R1-PG-LAB-02','temporary_root':str(lab.root)}
    try:
        lab.run()
        result['status'] = 'COMPLETED_WITH_RESIDUAL_EXPIRY_COUNTEREXAMPLE'
    except Exception as error:
        result['status'] = 'FAILED'
        result['error'] = type(error).__name__ + ': ' + str(error)
        raise
    finally:
        try:
            lab.cleanup()
            result['cleanup'] = 'CONFIRMED_REMOVED'
        finally:
            result['cases'] = lab.results
            print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
