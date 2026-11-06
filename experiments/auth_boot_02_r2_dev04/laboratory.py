import os
from pathlib import Path
import shutil
import socket
import struct
import subprocess
import tempfile
import uuid

import psycopg
from psycopg import sql

BIN = Path('/usr/lib/postgresql/16/bin')
LOCK = 9704


class Cluster:
    def __init__(self, root, name):
        self.root = root / name
        self.root.mkdir(mode=0o700)
        self.data = self.root / 'data'
        self.socket = self.root / 'socket'
        self.socket.mkdir(mode=0o700)
        self.started = False
        self.command('initdb', '-D', str(self.data), '--no-locale', '--encoding=UTF8',
                     '--auth-local=peer', '--auth-host=reject')
        self.configure()
        self.start()

    def command(self, name, *arguments):
        return subprocess.run([str(BIN / name), *arguments], check=True,
                              capture_output=True, text=True).stdout

    def configure(self):
        with (self.data / 'postgresql.conf').open('a') as output:
            output.write("\nlisten_addresses=''\nunix_socket_directories='" + str(self.socket)
                         + "'\nunix_socket_permissions=0700\nfsync=on\nsynchronous_commit=on"
                         + "\nfull_page_writes=on\nmax_connections=40\n")

    def start(self):
        self.command('pg_ctl', '-D', str(self.data), '-l', str(self.root / 'server.log'), '-w', 'start')
        self.started = True

    def stop(self):
        if self.started:
            self.command('pg_ctl', '-D', str(self.data), '-m', 'fast', '-w', 'stop')
            self.started = False

    def dsn(self, database='postgres', user=None):
        return psycopg.conninfo.make_conninfo(host=str(self.socket), dbname=database,
            user=user or os.environ['USER'], connect_timeout=2, application_name='r2dev04')

    def database(self):
        name = 'lab_' + uuid.uuid4().hex
        with psycopg.connect(self.dsn(), autocommit=True) as connection:
            connection.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
        return self.dsn(name)

    def roles(self, names):
        with psycopg.connect(self.dsn()) as connection:
            for name, login in names:
                connection.execute(sql.SQL('CREATE ROLE {} {} NOSUPERUSER NOCREATEDB NOCREATEROLE '
                    'NOREPLICATION NOBYPASSRLS NOINHERIT').format(sql.Identifier(name),
                    sql.SQL('LOGIN' if login else 'NOLOGIN')))
        with (self.data / 'pg_ident.conf').open('a') as output:
            for name, login in names:
                if login:
                    output.write(f'\nr2dev04 {os.environ["USER"]} {name}\n')
        original = (self.data / 'pg_hba.conf').read_text()
        rules = ''.join(f'local all {name} peer map=r2dev04\n' for name, login in names if login)
        (self.data / 'pg_hba.conf').write_text(rules + original)
        self.command('pg_ctl', '-D', str(self.data), 'reload')


TARGET = """
REVOKE ALL ON SCHEMA public FROM PUBLIC;
CREATE SCHEMA lab AUTHORIZATION effect_owner;
CREATE TABLE lab.payload(id boolean PRIMARY KEY CHECK(id), value integer NOT NULL);
INSERT INTO lab.payload VALUES(true,0);
ALTER TABLE lab.payload OWNER TO effect_owner;
CREATE FUNCTION lab.apply_effect() RETURNS integer LANGUAGE sql SECURITY DEFINER
SET search_path=pg_catalog,lab,pg_temp AS
$$ UPDATE lab.payload SET value=value+1 WHERE id RETURNING value $$;
ALTER FUNCTION lab.apply_effect() OWNER TO effect_owner;
REVOKE ALL ON FUNCTION lab.apply_effect() FROM PUBLIC;
GRANT USAGE ON SCHEMA lab TO executor,broker;
GRANT EXECUTE ON FUNCTION lab.apply_effect() TO broker;
ALTER DEFAULT PRIVILEGES FOR ROLE effect_owner REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
"""

ANCHOR = """
REVOKE ALL ON SCHEMA public FROM PUBLIC;
CREATE SCHEMA control AUTHORIZATION anchor_owner;
CREATE TABLE control.fence(id boolean PRIMARY KEY CHECK(id), epoch bigint, endpoint text);
INSERT INTO control.fence VALUES(true,1,'');
CREATE TABLE control.claims(approval text PRIMARY KEY, epoch bigint, endpoint text);
CREATE TABLE control.audit(sequence bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    kind text, approval text, epoch bigint);
ALTER TABLE control.fence OWNER TO anchor_owner;
ALTER TABLE control.claims OWNER TO anchor_owner;
ALTER TABLE control.audit OWNER TO anchor_owner;
GRANT USAGE ON SCHEMA control TO coordinator,observer;
GRANT SELECT,UPDATE ON control.fence TO coordinator;
GRANT SELECT,INSERT ON control.claims TO coordinator;
GRANT SELECT,INSERT ON control.audit TO coordinator;
GRANT USAGE ON SEQUENCE control.audit_sequence_seq TO coordinator;
GRANT SELECT ON ALL TABLES IN SCHEMA control TO observer;
"""

WITNESS = """
REVOKE ALL ON SCHEMA public FROM PUBLIC;
CREATE TABLE receipts(approval text PRIMARY KEY, epoch bigint, endpoint text, nonce text,
    lower_utc numeric, upper_utc numeric);
REVOKE ALL ON receipts FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO witness_writer,witness_reader;
GRANT INSERT,SELECT ON receipts TO witness_writer;
GRANT SELECT ON receipts TO witness_reader;
"""


class Blocked(Exception):
    pass


def connected_identity(connection):
    pathname = Path(connection.info.host).resolve() / '.s.PGSQL.5432'
    metadata = pathname.stat()
    with socket.fromfd(connection.fileno(), socket.AF_UNIX, socket.SOCK_STREAM) as channel:
        pid, uid, gid = struct.unpack('3i', channel.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
    return dict(database=connection.info.dbname, path=str(pathname), device=metadata.st_dev, inode=metadata.st_ino,
                pid=pid, uid=uid, gid=gid)


def endpoint_identity(dsn):
    with psycopg.connect(dsn, autocommit=True) as connection:
        return connected_identity(connection)


class Lab:
    def __init__(self):
        self.root = Path(tempfile.mkdtemp(prefix='ln-r2d04-')).resolve()
        self.clusters = []
        self.cleaned = False
        self.partitions = set()
        try:
            for name in ('anchor', 'witness', 'target'):
                cluster = Cluster(self.root, name)
                self.clusters.append(cluster)
                setattr(self, name, cluster)
            self.anchor.roles([('anchor_owner', False), ('coordinator', True), ('observer', True), ('executor', True)])
            self.witness.roles([('witness_writer', True), ('witness_reader', True), ('executor', True)])
            self.target.roles([('effect_owner', False), ('broker', True), ('executor', True)])
        except BaseException:
            self.close()
            raise

    def close(self):
        errors = []
        for cluster in reversed(self.clusters):
            try:
                cluster.stop()
            except Exception as error:
                errors.append(repr(error))
        if errors:
            raise RuntimeError(errors)
        if self.root.parent != Path(tempfile.gettempdir()).resolve() or not self.root.name.startswith('ln-r2d04-'):
            raise RuntimeError('cleanup path validation failed')
        shutil.rmtree(self.root)
        self.cleaned = not self.root.exists()

    def physical_clone(self):
        self.target.stop()
        clone = Cluster.__new__(Cluster)
        clone.root = self.root / ('clone_' + uuid.uuid4().hex)
        clone.root.mkdir(mode=0o700)
        clone.data = clone.root / 'data'
        clone.socket = clone.root / 'socket'
        clone.socket.mkdir(mode=0o700)
        clone.started = False
        self.clusters.append(clone)
        try:
            shutil.copytree(self.target.data, clone.data)
            clone.configure()
            self.target.start()
            clone.start()
        except BaseException:
            if not self.target.started:
                self.target.start()
            raise
        return clone


class Boundary:
    def __init__(self, lab):
        self.lab = lab
        self.anchor_admin = lab.anchor.database()
        self.witness_admin = lab.witness.database()
        self.target_admin = lab.target.database()
        for dsn, schema in ((self.anchor_admin, ANCHOR), (self.witness_admin, WITNESS), (self.target_admin, TARGET)):
            with psycopg.connect(dsn) as connection:
                connection.execute(schema)
                database = psycopg.conninfo.conninfo_to_dict(dsn)['dbname']
                connection.execute(sql.SQL('REVOKE ALL ON DATABASE {} FROM PUBLIC').format(sql.Identifier(database)))
                roles = ('coordinator', 'observer', 'executor') if dsn == self.anchor_admin else (
                    ('witness_writer', 'witness_reader', 'executor') if dsn == self.witness_admin else ('broker', 'executor'))
                for role in roles:
                    connection.execute(sql.SQL('GRANT CONNECT ON DATABASE {} TO {}').format(
                        sql.Identifier(database), sql.Identifier(role)))
        self.anchor = psycopg.conninfo.make_conninfo(self.anchor_admin, user='coordinator')
        self.witness = psycopg.conninfo.make_conninfo(self.witness_admin, user='witness_reader')
        self.writer = psycopg.conninfo.make_conninfo(self.witness_admin, user='witness_writer')
        self.target = psycopg.conninfo.make_conninfo(self.target_admin, user='broker')
        self.executor = psycopg.conninfo.make_conninfo(self.target_admin, user='executor')
        self.pins = {name: endpoint_identity(getattr(self, name)) for name in ('anchor', 'witness', 'target')}
        self.target_key = self.key(self.pins['target'])
        with psycopg.connect(self.anchor) as connection:
            connection.execute('UPDATE control.fence SET endpoint=%s', (self.target_key,))

    @staticmethod
    def key(identity):
        return '|'.join(str(identity[name]) for name in ('database', 'path', 'device', 'inode', 'pid', 'uid', 'gid'))

    def connect(self, name, dsn=None):
        if name in self.lab.partitions:
            raise Blocked('endpoint unavailable: ' + name)
        destination = dsn or getattr(self, name)
        connection = psycopg.connect(destination)
        try:
            if connected_identity(connection) != self.pins[name]:
                raise Blocked('endpoint pin mismatch: ' + name)
            expected_user = psycopg.conninfo.conninfo_to_dict(getattr(self, name))['user']
            if connection.execute('SELECT session_user,current_user').fetchone() != (expected_user, expected_user):
                raise Blocked('SQL principal mismatch: ' + name)
            return connection
        except BaseException:
            connection.close()
            raise

    def epoch(self):
        with self.connect('anchor') as connection:
            return connection.execute('SELECT epoch,endpoint FROM control.fence').fetchone()

    def receipt(self, approval, epoch, endpoint, nonce='nonce', lower=100, upper=102):
        with psycopg.connect(self.writer) as connection:
            connection.execute('INSERT INTO receipts VALUES(%s,%s,%s,%s,%s,%s)',
                               (approval, epoch, endpoint, nonce, lower, upper))

    def verify(self, approval, epoch, endpoint, nonce, fixture, clock, window):
        if not fixture:
            raise Blocked('D09 administrative independence and authenticated UTC unproven')
        if clock is None:
            raise Blocked('trusted UTC absent')
        lower, upper = clock
        if lower > upper or lower < window[0] or upper >= window[1]:
            raise Blocked('UTC interval not wholly inside validity window')
        with self.connect('witness') as connection:
            row = connection.execute('SELECT epoch,endpoint,nonce,lower_utc,upper_utc FROM receipts '
                                     'WHERE approval=%s', (approval,)).fetchone()
        if row != (epoch, endpoint, nonce, lower, upper):
            raise Blocked('missing or mismatched witness receipt')

    def execute(self, approval, epoch=1, endpoint=None, nonce='nonce', fixture=False,
                clock=None, window=(90, 110), lose_claim=False, lose_commit=False,
                after_claim=None, effect_ready=None, release=None, rollback=False, target_dsn=None):
        endpoint = endpoint or self.target_key
        self.verify(approval, epoch, endpoint, nonce, fixture, clock, window)
        with self.connect('anchor') as connection:
            connection.execute('SELECT pg_advisory_xact_lock_shared(%s)', (LOCK,))
            if connection.execute('SELECT epoch,endpoint FROM control.fence').fetchone() != (epoch, endpoint):
                raise Blocked('fenced before claim')
            connection.execute('INSERT INTO control.claims VALUES(%s,%s,%s)', (approval, epoch, endpoint))
            connection.execute("INSERT INTO control.audit(kind,approval,epoch) VALUES('claim',%s,%s)", (approval, epoch))
        if lose_claim:
            return 'UNKNOWN'
        if after_claim:
            after_claim()
        with self.connect('anchor') as guard:
            guard.execute('SELECT pg_advisory_xact_lock_shared(%s)', (LOCK,))
            self.guard_pid = guard.info.backend_pid
            if guard.execute('SELECT epoch,endpoint FROM control.fence').fetchone() != (epoch, endpoint):
                raise Blocked('fenced after claim')
            self.verify(approval, epoch, endpoint, nonce, fixture, clock, window)
            with self.connect('target', target_dsn) as target:
                if getattr(self, 'before_sql_ready', None):
                    self.before_sql_ready.set()
                    if not self.before_sql_release.wait(5):
                        raise TimeoutError('release before SQL')
                target.execute('SELECT lab.apply_effect()')
                if effect_ready:
                    effect_ready.set()
                if release and not release.wait(5):
                    raise TimeoutError('release effect')
                if rollback:
                    target.rollback()
            guard.execute("INSERT INTO control.audit(kind,approval,epoch) VALUES('effect_ack',%s,%s)", (approval, epoch))
        return 'UNKNOWN' if lose_commit else 'OBSERVED'

    def takeover(self, endpoint=None, lose_response=False, entered=None):
        with self.connect('anchor') as connection:
            if entered:
                entered.set()
            connection.execute('SELECT pg_advisory_xact_lock(%s)', (LOCK,))
            epoch = connection.execute('UPDATE control.fence SET epoch=epoch+1,endpoint=%s RETURNING epoch',
                (endpoint or self.target_key,)).fetchone()[0]
            connection.execute("INSERT INTO control.audit(kind,epoch) VALUES('fence',%s)", (epoch,))
        return 'UNKNOWN' if lose_response else epoch

    def observe(self):
        observer = psycopg.conninfo.make_conninfo(self.anchor_admin, user='observer')
        with psycopg.connect(observer) as connection:
            epoch, endpoint = connection.execute('SELECT epoch,endpoint FROM control.fence').fetchone()
            claims = connection.execute('SELECT count(*) FROM control.claims').fetchone()[0]
        with psycopg.connect(self.target_admin) as connection:
            effects = connection.execute('SELECT value FROM lab.payload').fetchone()[0]
        return dict(epoch=epoch, endpoint=endpoint, claims=claims, effects=effects, resume=False, executable=False)
