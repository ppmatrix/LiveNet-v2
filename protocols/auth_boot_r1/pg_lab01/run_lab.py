"""R1-PG-LAB-01 real PostgreSQL lab; only disposable resources owned by this run.

Explicit --run-isolated-lab required. Uses existing PG16 binaries and psycopg;
never installs, uses Docker, contacts TCP or imports LiveNet application code.
Local trust is restricted by an owner-only directory/socket, not an OS security
boundary against this same UID/root. DB role tests exercise SQL privileges only.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import time
import uuid

import psycopg


BIN = Path('/usr/lib/postgresql/16/bin')
HERE = Path(__file__).resolve().parent


class Lab:
    def __init__(self):
        # Pre-resource checks. No default DSN, PGDATA, local service or password.
        if os.getuid() == 0:
            raise RuntimeError('Refuse root')
        for name in ('initdb', 'pg_ctl', 'postgres'):
            if not os.access(BIN / name, os.X_OK):
                raise RuntimeError('Missing PostgreSQL binary')
        self.env = {k: v for k, v in os.environ.items()
                    if not k.startswith(('PG', 'DATABASE_', 'LD_'))}
        # libpq also reads this process's environment; never inherit PG service,
        # password, host or options from an existing installation.
        for key in tuple(os.environ):
            if key.startswith('PG'):
                del os.environ[key]
        self.token = uuid.uuid4().hex
        self.root = Path(tempfile.mkdtemp(prefix='r1-pg-lab01-', dir='/tmp'))
        os.chmod(self.root, 0o700)
        self.marker = self.root / 'OWNED_BY_R1_PG_LAB01'
        self.marker.write_text(self.token)
        os.chmod(self.marker, 0o600)
        self.passfile = self.root / 'empty-lab-passfile'
        self.passfile.write_text('')
        os.chmod(self.passfile, 0o600)
        self.clusters = {}
        self.results = []

    def command(self, *args):
        return subprocess.run([str(a) for a in args], env=self.env,
                              capture_output=True, text=True, check=True, timeout=30)

    def start(self, name, source=None):
        if name not in ('main', 'clone') or name in self.clusters:
            raise RuntimeError('Unexpected cluster name/reuse')
        data, sock = self.root / (name + '-data'), self.root / (name + '-socket')
        if data.exists() or sock.exists():
            raise RuntimeError('Refuse existing resource')
        sock.mkdir(mode=0o700)
        self.clusters[name] = (data, sock)
        if source is None:
            self.command(BIN / 'initdb', '-D', data, '-U', 'lab_owner',
                         '-A', 'trust', '--encoding=UTF8', '--no-locale', '--no-instructions')
        else:
            if source != self.root / 'historical-snapshot':
                raise RuntimeError('Unexpected snapshot source')
            shutil.copytree(source, data)
        self.launch(name)

    def launch(self, name):
        data, sock = self.clusters[name]
        options = (f"-c listen_addresses='' -c unix_socket_directories='{sock}' "
                   "-c unix_socket_permissions=0700 -c port=5432 "
                   "-c fsync=on -c synchronous_commit=on -c full_page_writes=on "
                   "-c max_connections=12 -c shared_buffers=16MB "
                   "-c logging_collector=off -c log_min_messages=log")
        self.command(BIN / 'pg_ctl', '-D', data, '-l', self.root / (name + '.log'),
                     '-o', options, '-w', 'start')
        with closing(self.connect(cluster=name)) as c:
            assert c.execute('SHOW listen_addresses').fetchone()[0] == ''
            assert c.execute('SHOW unix_socket_directories').fetchone()[0] == str(sock)
            assert Path(c.execute('SHOW data_directory').fetchone()[0]) == data
            assert c.execute('SELECT inet_server_addr() IS NULL').fetchone()[0]
            assert c.execute('SHOW fsync').fetchone()[0] == 'on'
            assert c.execute('SHOW synchronous_commit').fetchone()[0] == 'on'

    def connect(self, role='lab_owner', cluster='main', autocommit=True):
        return psycopg.connect(host=str(self.clusters[cluster][1]), port=5432,
                               dbname='postgres', user=role, connect_timeout=3,
                               password='', passfile=str(self.passfile), sslmode='disable',
                               options='-c statement_timeout=6000 -c lock_timeout=5000',
                               autocommit=autocommit)

    def stop(self, name, mode='fast'):
        data, _ = self.clusters[name]
        status = subprocess.run([str(BIN / 'pg_ctl'), '-D', str(data), 'status'],
                                env=self.env, capture_output=True, timeout=5)
        if status.returncode == 0:
            self.command(BIN / 'pg_ctl', '-D', data, '-m', mode, '-w', 'stop')
        elif status.returncode != 3:
            raise RuntimeError('Cannot establish owned cluster status')

    def record(self, name, **facts):
        self.results.append({'case': name, **facts})

    def wait(self, predicate):
        end = time.monotonic() + 4
        while time.monotonic() < end:
            if predicate():
                return
            time.sleep(.01)
        raise AssertionError('Barrier not reached')

    def prepare(self, caller, approval, *, ttl=30, attempt=None, cluster='main'):
        caller.execute('BEGIN')
        xid = caller.execute('SELECT txid_current()::text').fetchone()[0]
        with closing(self.connect('lab_writer', cluster)) as writer:
            writer.execute('''INSERT INTO lab.burn VALUES
                (%s,%s,'lab_caller',%s,%s,'fixed-update-v1','lab-generation-1',1,
                 clock_timestamp() - interval '1 second',
                 clock_timestamp() + %s * interval '1 second')''',
                (approval, attempt or approval, caller.info.backend_pid, xid, ttl))

    @staticmethod
    def call(caller, approval, expected=0, value=10):
        return caller.execute('SELECT lab.fixed_update(%s,%s,%s)',
                              (approval, expected, value)).fetchone()[0]

    @staticmethod
    def refused(action, expected_state=None):
        try:
            action()
        except psycopg.Error as error:
            if expected_state is not None:
                assert error.sqlstate == expected_state, error.sqlstate
            return error.sqlstate
        raise AssertionError('Expected refusal')

    def reset_cell(self, owner):
        owner.execute('UPDATE lab.cell SET value=0,row_version=0')
        owner.execute('UPDATE lab.policy SET epoch=1,revoked=false')

    def run(self):
        self.start('main')
        with closing(self.connect()) as owner:
            owner.execute((HERE / 'schema.sql').read_text())
            version = owner.execute('SELECT version()').fetchone()[0]
            system_id = owner.execute('SELECT system_identifier::text FROM pg_control_system()').fetchone()[0]
        self.record('isolation', version=version, tcp=False, socket_mode='0700',
                    directory_mode=oct(stat.S_IMODE(self.root.stat().st_mode)),
                    existing_resources_reused=False)

        # Historical stopped copy BEFORE any approvals: only this task's files.
        self.stop('main')
        shutil.copytree(self.clusters['main'][0], self.root / 'historical-snapshot')
        self.launch('main')

        with closing(self.connect()) as c, closing(self.connect('lab_caller')) as a, \
             closing(self.connect(autocommit=False)) as b:
            self.refused(lambda: a.execute('UPDATE lab.cell SET value=999'), '42501')
            self.refused(lambda: a.execute('SELECT * FROM lab.burn'), '42501')
            with closing(self.connect('lab_writer')) as writer:
                self.refused(lambda: writer.execute('DELETE FROM lab.burn'), '42501')
            self.record('sql_privilege_bypass_refused', passed=True)

            # Three sessions: B holds a unique key, C conflicts, A observes.
            b.execute('''INSERT INTO lab.burn VALUES ('race','race','lab_caller',0,'0',
                'fixed-update-v1','lab-generation-1',1,clock_timestamp(),
                clock_timestamp()+interval '30 seconds')''')
            with ThreadPoolExecutor(max_workers=1) as pool:
                pending = pool.submit(self.refused, lambda: c.execute('''INSERT INTO lab.burn
                    VALUES ('race','race','lab_caller',0,'0','fixed-update-v1',
                    'lab-generation-1',1,clock_timestamp(),clock_timestamp()+interval '30 seconds')'''), '23505')
                self.wait(lambda: a.execute('SELECT cardinality(pg_blocking_pids(%s))>0',
                                           (c.info.backend_pid,)).fetchone()[0])
                b.commit()
                assert pending.result(timeout=4) == '23505'
            assert c.execute("SELECT count(*) FROM lab.burn WHERE approval='race'").fetchone()[0] == 1
            self.record('concurrent_unique_marker', passed=True, committed_markers=1)
            self.refused(lambda: c.execute('''INSERT INTO lab.burn
                SELECT 'new-approval',attempt,caller,backend_pid,transaction_id,
                       plan,generation,epoch,not_before,expires_at
                FROM lab.burn WHERE approval='race' '''), '23505')
            self.record('duplicate_attempt_under_new_approval_refused', passed=True)

            # Three-session gate race: A passes check then waits on C's cell row;
            # B replays with the wrong session identity/backend/transaction.
            self.prepare(a, 'three-session')
            c.execute('BEGIN')
            c.execute('SELECT * FROM lab.cell WHERE id=1 FOR UPDATE')
            with ThreadPoolExecutor(max_workers=1) as pool:
                pending = pool.submit(self.call, a, 'three-session')
                self.wait(lambda: c.execute('SELECT %s=ANY(pg_blocking_pids(%s))',
                                           (c.info.backend_pid, a.info.backend_pid)).fetchone()[0])
                self.refused(lambda: self.call(b, 'three-session'))
                b.rollback()
                c.execute('ROLLBACK')
                assert pending.result(timeout=4) == 1
            a.execute('COMMIT')
            assert c.execute('SELECT row_version FROM lab.cell').fetchone()[0] == 1
            self.record('three_session_fixed_update', passed=True, changed_rows=1)

            for label, expected in (('replay', 0), ('wrong-version', 999)):
                self.reset_cell(c)
                self.prepare(a, label)
                if label == 'replay':
                    self.call(a, label)
                    a.execute('COMMIT')
                    a.execute('BEGIN')
                self.refused(lambda: self.call(a, label, expected))
                a.execute('ROLLBACK')
                self.record(label + '_refused', passed=True)

            self.reset_cell(c)
            self.prepare(a, 'rollback')
            self.call(a, 'rollback')
            a.execute('ROLLBACK')
            assert c.execute('SELECT row_version FROM lab.cell').fetchone()[0] == 0
            assert c.execute("SELECT count(*) FROM lab.burn WHERE approval='rollback'").fetchone()[0] == 1
            self.record('protected_rollback_preserves_separate_burn', passed=True)

            # Important negative control: same transaction + savepoint permits a
            # second initiation when transaction-local start state is reverted.
            self.prepare(a, 'savepoint')
            a.execute('SAVEPOINT before_effect')
            self.call(a, 'savepoint')
            a.execute('ROLLBACK TO SAVEPOINT before_effect')
            self.call(a, 'savepoint')
            a.execute('COMMIT')
            text = (self.root / 'main.log').read_text()
            assert text.count('R1_LAB_CHECK savepoint') == 2
            self.record('savepoint_reinitiation_counterexample', guarantee_satisfied=False,
                        successful_function_calls=2, final_committed_row_version=1)

            # Expired/revoked BEFORE local check: safely refused.
            for label in ('expired-before-check', 'revoked-before-check'):
                self.reset_cell(c)
                self.prepare(a, label, ttl=-.1 if label.startswith('expired') else 30)
                if label.startswith('revoked'):
                    c.execute('UPDATE lab.policy SET revoked=true,epoch=2')
                self.refused(lambda: self.call(a, label))
                a.execute('ROLLBACK')
                assert c.execute('SELECT row_version FROM lab.cell').fetchone()[0] == 0
                self.record(label, passed=True)

            # BEFORE-check wait versus AFTER-check wait: actual PostgreSQL locks.
            for label, lock_table, should_succeed in (
                ('expiry-during-policy-lock', 'policy', False),
                ('expiry-after-check-before-tuple', 'cell', True),
            ):
                self.reset_cell(c)
                self.prepare(a, label, ttl=.7)
                c.execute('BEGIN')
                c.execute('SELECT * FROM lab.' + lock_table + ' WHERE id=1 FOR UPDATE')
                with ThreadPoolExecutor(max_workers=1) as pool:
                    action = self.call if should_succeed else lambda *args: self.refused(lambda: self.call(*args))
                    pending = pool.submit(action, a, label)
                    self.wait(lambda: c.execute('SELECT %s=ANY(pg_blocking_pids(%s))',
                                               (c.info.backend_pid, a.info.backend_pid)).fetchone()[0])
                    self.wait(lambda: c.execute("SELECT clock_timestamp() >= expires_at FROM lab.burn WHERE approval=%s",
                                               (label,)).fetchone()[0])
                    c.execute('ROLLBACK')
                    outcome = pending.result(timeout=4)
                a.execute('COMMIT' if should_succeed else 'ROLLBACK')
                assert c.execute('SELECT row_version FROM lab.cell').fetchone()[0] == int(should_succeed)
                self.record(label, expected_counterexample=should_succeed,
                            effect_after_expiry=should_succeed, result=str(outcome))

            self.reset_cell(c)
            self.prepare(a, 'revocation-pending')
            c.execute('BEGIN')
            c.execute('SELECT * FROM lab.cell WHERE id=1 FOR UPDATE')
            with ThreadPoolExecutor(max_workers=2) as pool:
                work = pool.submit(self.call, a, 'revocation-pending')
                self.wait(lambda: c.execute('SELECT %s=ANY(pg_blocking_pids(%s))',
                                           (c.info.backend_pid, a.info.backend_pid)).fetchone()[0])
                b.execute('ROLLBACK')
                revoke = pool.submit(b.execute, 'UPDATE lab.policy SET revoked=true,epoch=2')
                self.wait(lambda: c.execute('SELECT %s=ANY(pg_blocking_pids(%s))',
                                           (a.info.backend_pid, b.info.backend_pid)).fetchone()[0])
                c.execute('ROLLBACK')
                assert work.result(timeout=4) == 1
                a.execute('COMMIT')
                revoke.result(timeout=4)
                b.commit()
            assert c.execute('SELECT revoked FROM lab.policy').fetchone()[0]
            self.record('local_revocation_application_order', passed=True,
                        request_precedes_effect=True, applied_only_after_protected_commit=True,
                        remote_authority_ordering_proven=False)

        # Send COMMIT, flush it, close without consuming its result.
        with closing(self.connect()) as owner:
            self.reset_cell(owner)
        uncertain = self.connect('lab_caller')
        self.prepare(uncertain, 'lost-confirmation')
        self.call(uncertain, 'lost-confirmation')
        lost_pid = uncertain.info.backend_pid
        uncertain.pgconn.send_query(b'COMMIT')
        assert uncertain.pgconn.flush() == 0
        uncertain.close()
        with closing(self.connect()) as observer:
            self.wait(lambda: observer.execute('SELECT NOT EXISTS (SELECT 1 FROM pg_stat_activity WHERE pid=%s)',
                                              (lost_pid,)).fetchone()[0])
            version = observer.execute('SELECT row_version FROM lab.cell').fetchone()[0]
            assert version in (0, 1)
            assert observer.execute("SELECT count(*) FROM lab.burn WHERE approval='lost-confirmation'").fetchone()[0] == 1
        self.record('commit_confirmation_not_consumed', passed=True, observer_row_version=version,
                    caller_result='UNKNOWN/BLOCKED', automatic_retry=False)

        self.stop('main', 'immediate')
        self.launch('main')
        with closing(self.connect()) as owner:
            assert owner.execute("SELECT count(*) FROM lab.burn WHERE approval='lost-confirmation'").fetchone()[0] == 1
        self.record('unclean_server_restart_marker_persistence', passed=True,
                    power_loss_or_storage_failure_proven=False)

        # An old, clean physical copy omits later burns and retains system ID.
        self.stop('main')
        self.start('clone', self.root / 'historical-snapshot')
        with closing(self.connect(cluster='clone')) as observer:
            assert observer.execute('SELECT system_identifier::text FROM pg_control_system()').fetchone()[0] == system_id
            assert observer.execute("SELECT count(*) FROM lab.burn WHERE approval='three-session'").fetchone()[0] == 0
        with closing(self.connect('lab_caller', 'clone')) as caller:
            self.prepare(caller, 'three-session', cluster='clone')
            assert self.call(caller, 'three-session') == 1
            caller.execute('COMMIT')
        self.record('historical_clone_counterexample', missing_later_burn=True,
                    same_system_identifier=True, same_approval_can_be_reburned=True,
                    external_authority_or_quarantine_implemented=False)

    def cleanup(self):
        # Never delete data while an owned server may still be running.
        for name in tuple(self.clusters):
            self.stop(name)
        if (self.root.parent != Path('/tmp') or self.root.is_symlink()
                or self.root.stat().st_uid != os.getuid()
                or self.marker.read_text() != self.token):
            raise RuntimeError('Cleanup ownership check failed; retain resources')
        shutil.rmtree(self.root)
        assert not self.root.exists()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-isolated-lab', action='store_true', required=True)
    args = parser.parse_args()
    lab = Lab()
    result = {'task': 'R1-PG-LAB-01', 'temporary_root': str(lab.root)}
    try:
        lab.run()
        result['status'] = 'COMPLETED_WITH_EXPECTED_COUNTEREXAMPLES'
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
