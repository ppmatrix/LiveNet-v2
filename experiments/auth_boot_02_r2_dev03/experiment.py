from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import uuid

import psycopg
from psycopg import sql

PRIOR = Path(__file__).resolve().parent.parent / 'auth_boot_02_r2_dev02'
sys.path.insert(0, str(PRIOR))
from harness import Cluster
from laboratory import Approval, Laboratory, REF_SCHEMA, binding


TARGET_SCHEMA = """
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
CREATE TABLE fence(singleton boolean PRIMARY KEY CHECK(singleton),
    epoch bigint NOT NULL, incarnation text NOT NULL, generation text NOT NULL);
CREATE TABLE starts(approval text PRIMARY KEY, attempt text UNIQUE NOT NULL,
    epoch bigint NOT NULL, incarnation text NOT NULL, generation text NOT NULL,
    backend integer NOT NULL, transaction_id bigint NOT NULL, digest text NOT NULL);
CREATE TABLE payload(singleton boolean PRIMARY KEY CHECK(singleton), value integer NOT NULL);
INSERT INTO payload VALUES(true,0);
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO target_service;
GRANT SELECT ON fence TO target_service;
GRANT SELECT,INSERT ON starts TO target_service;
GRANT SELECT,UPDATE ON payload TO target_service;
"""


@dataclass(frozen=True)
class Ticket:
    approval: str
    attempt: str
    epoch: int
    incarnation: str
    generation: str
    backend: int
    transaction_id: int
    digest: str


class Session:
    def __init__(self, lab):
        self.lab = lab
        self.connection = psycopg.connect(lab.service_dsn, autocommit=True)
        self.connection.execute('BEGIN')
        self.backend, self.transaction_id = self.connection.execute(
            'SELECT pg_backend_pid(),txid_current()').fetchone()
        self.epoch, self.incarnation, self.generation = self.connection.execute(
            'SELECT epoch,incarnation,generation FROM fence').fetchone()
        self.ticket = None

    def close(self):
        self.connection.close()


class Boundary:
    def __init__(self, harness, authority=None, target=None):
        self.harness = harness
        self.authority = authority or harness.authority()
        self.target_dsn = target or harness.target.database()
        self.service_dsn = psycopg.conninfo.make_conninfo(self.target_dsn, user='target_service')
        self.worker_dsn = psycopg.conninfo.make_conninfo(self.target_dsn, user='executor')
        if target is None:
            with psycopg.connect(self.target_dsn) as connection:
                connection.execute(TARGET_SCHEMA)
                connection.execute('INSERT INTO fence VALUES(true,1,%s,%s)',
                                   (uuid.uuid4().hex, uuid.uuid4().hex))

    def session(self):
        return Session(self)

    def admit(self, session, approval='approval', attempt=None, d09_assumed=False,
              lose_response=False, **options):
        if not d09_assumed:
            return None, dict(state='BLOCKED', reason='D09_UNDEMONSTRATED', executable=False)
        attempt = attempt or uuid.uuid4().hex
        bound = binding(attempt) | dict(destination=session.generation,
            generation=session.generation, incarnation=session.incarnation,
            session=str(session.backend), transaction=str(session.transaction_id),
            target_epoch=session.epoch)
        result = self.authority.change('admit', Approval(approval), bound,
                                       lose_response=lose_response, **options)
        if result['state'] != 'ADMITTED':
            return None, result
        ticket = Ticket(approval, attempt, session.epoch, session.incarnation,
                        session.generation, session.backend, session.transaction_id,
                        result['digest'])
        session.ticket = ticket
        return ticket, result

    def initiate(self, session, ticket, crash=None, rollback=False, savepoint=False,
                 lose_response=False, claimed=None, proceed=None, effect_ready=None,
                 effect_proceed=None, fail_claim_ack=False):
        if ticket is None:
            return 'BLOCKED'
        if session.ticket != ticket:
            return 'BLOCKED_BINDING'
        connection = session.connection
        identity = connection.execute('SELECT pg_backend_pid(),txid_current()').fetchone()
        if identity != (ticket.backend, ticket.transaction_id):
            return 'BLOCKED_BINDING'
        if crash == 'before_claim':
            os._exit(81)
        try:
            with psycopg.connect(self.service_dsn) as durable:
                durable.execute('SELECT pg_advisory_xact_lock_shared(9703)')
                current = durable.execute(
                    'SELECT epoch,incarnation,generation FROM fence').fetchone()
                if current != (ticket.epoch, ticket.incarnation, ticket.generation):
                    return 'FENCED'
                durable.execute('INSERT INTO starts VALUES(%s,%s,%s,%s,%s,%s,%s,%s)',
                                tuple(getattr(ticket, field) for field in ticket.__dataclass_fields__))
        except psycopg.errors.UniqueViolation:
            return 'CONSUMED'
        if claimed:
            claimed.set()
        if crash == 'after_claim':
            os._exit(82)
        if fail_claim_ack:
            return 'UNKNOWN'
        if proceed and not proceed.wait(5):
            raise TimeoutError('claim synchronization')
        connection.execute('SELECT pg_advisory_xact_lock_shared(9703)')
        current = connection.execute(
            'SELECT epoch,incarnation,generation FROM fence').fetchone()
        if current != (ticket.epoch, ticket.incarnation, ticket.generation):
            connection.execute('ROLLBACK')
            return 'FENCED'
        if savepoint:
            connection.execute('SAVEPOINT effect')
        connection.execute('UPDATE payload SET value=value+1 WHERE singleton')
        if effect_ready:
            effect_ready.set()
        if effect_proceed and not effect_proceed.wait(5):
            raise TimeoutError('effect synchronization')
        if crash == 'after_effect':
            os._exit(83)
        if savepoint:
            connection.execute('ROLLBACK TO SAVEPOINT effect')
        connection.execute('ROLLBACK' if rollback else 'COMMIT')
        if crash == 'after_commit':
            os._exit(84)
        return 'UNKNOWN' if lose_response else 'OBSERVED'

    def fence(self):
        with psycopg.connect(self.target_dsn) as connection:
            connection.execute('SELECT pg_advisory_xact_lock(9703)')
            return connection.execute('UPDATE fence SET epoch=epoch+1,incarnation=%s '
                'RETURNING epoch,incarnation,generation', (uuid.uuid4().hex,)).fetchone()

    def observe(self):
        with psycopg.connect(self.target_dsn) as connection:
            return dict(starts=connection.execute('SELECT count(*) FROM starts').fetchone()[0],
                        effects=connection.execute('SELECT value FROM payload').fetchone()[0],
                        executable=False, resume=False)


class Harness:
    def __init__(self):
        self.root = Path(tempfile.mkdtemp(prefix='ln-r2d03-')).resolve()
        self.clusters = []
        self.cleaned = False
        try:
            for name in ('authority_cluster', 'reference', 'target'):
                cluster = Cluster(self.root, name)
                self.clusters.append(cluster)
                setattr(self, name, cluster)
            self.configure_roles(self.reference, ('reference_service', 'reference_reader',
                                                  'authority_client', 'executor'))
            self.configure_roles(self.target, ('target_service', 'executor'))
            self.reference_dsn = self.reference.database()
            with psycopg.connect(self.reference_dsn) as connection:
                connection.execute(REF_SCHEMA)
                connection.execute('REVOKE CREATE ON SCHEMA public FROM PUBLIC')
                connection.execute('REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC')
                connection.execute('GRANT USAGE ON SCHEMA public TO reference_reader')
                connection.execute('GRANT SELECT ON ALL TABLES IN SCHEMA public TO reference_reader')
                connection.execute('GRANT USAGE ON SCHEMA public TO reference_service')
                connection.execute('GRANT SELECT,INSERT,UPDATE ON ALL TABLES IN SCHEMA public '
                                   'TO reference_service')
            self.reference_service_dsn = psycopg.conninfo.make_conninfo(
                self.reference_dsn, user='reference_service')
        except BaseException:
            self.close()
            raise

    def configure_roles(self, cluster, roles):
        with psycopg.connect(cluster.dsn()) as connection:
            for role in roles:
                connection.execute(sql.SQL('CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB '
                    'NOCREATEROLE NOREPLICATION').format(sql.Identifier(role)))
        with (cluster.data / 'pg_ident.conf').open('a') as mapping:
            for role in roles:
                mapping.write(f'\nr2dev03 {os.environ["USER"]} {role}\n')
        original = (cluster.data / 'pg_hba.conf').read_text()
        rules = ''.join(f'local all {role} peer map=r2dev03\n' for role in roles)
        (cluster.data / 'pg_hba.conf').write_text(rules + original)
        cluster.command('pg_ctl', '-D', str(cluster.data), 'reload')

    def authority(self):
        authority = Laboratory(self.authority_cluster.database(), self.reference_service_dsn,
                               uuid.uuid4().hex)
        authority.bootstrap()
        return authority

    def clone_authority(self, authority, dump=None):
        return Laboratory(self.authority_cluster.restore(dump if dump is not None else
            self.authority_cluster.dump(authority.authority_dsn)), authority.reference_dsn,
            authority.namespace)

    def close(self):
        errors = []
        for cluster in reversed(self.clusters):
            try:
                cluster.stop()
            except Exception as error:
                errors.append(repr(error))
        if errors:
            raise RuntimeError(errors)
        if self.root.parent != Path(tempfile.gettempdir()).resolve() or not self.root.name.startswith('ln-r2d03-'):
            raise RuntimeError('cleanup path validation failed')
        shutil.rmtree(self.root)
        self.cleaned = not self.root.exists()


def crash_worker(boundary, stage):
    session = boundary.session()
    ticket, result = boundary.admit(session, d09_assumed=True)
    if result['state'] != 'ADMITTED':
        raise RuntimeError(result)
    boundary.initiate(session, ticket, crash=stage)
