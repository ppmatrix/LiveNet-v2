import importlib.util
from pathlib import Path
import shutil
import tempfile
import time

import psycopg
from psycopg import sql

PREVIOUS = Path(__file__).resolve().parents[1] / 'auth_boot_02_r2_dev04' / 'laboratory.py'
SPEC = importlib.util.spec_from_file_location('dev04_laboratory', PREVIOUS)
previous = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(previous)
Cluster = previous.Cluster
Blocked = previous.Blocked

SCHEMA = """
REVOKE ALL ON SCHEMA public FROM PUBLIC;
CREATE SCHEMA resource AUTHORIZATION effect_owner;
CREATE TABLE resource.fence(singleton boolean PRIMARY KEY CHECK(singleton), epoch bigint NOT NULL);
INSERT INTO resource.fence VALUES(true,1);
CREATE TABLE resource.incarnations(principal name PRIMARY KEY, epoch bigint NOT NULL);
INSERT INTO resource.incarnations VALUES('old_writer',1),('new_writer',2);
CREATE TABLE resource.payload(singleton boolean PRIMARY KEY CHECK(singleton), value integer NOT NULL);
INSERT INTO resource.payload VALUES(true,0);
CREATE TABLE resource.effects(approval text PRIMARY KEY, epoch bigint NOT NULL);
ALTER TABLE resource.fence OWNER TO effect_owner;
ALTER TABLE resource.incarnations OWNER TO effect_owner;
ALTER TABLE resource.payload OWNER TO effect_owner;
ALTER TABLE resource.effects OWNER TO effect_owner;
CREATE FUNCTION resource.apply(request_epoch bigint, request_approval text) RETURNS integer
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,resource,pg_temp AS $$
DECLARE active_epoch bigint; principal_epoch bigint; result integer;
BEGIN
 SELECT epoch INTO active_epoch FROM resource.fence WHERE singleton FOR SHARE;
 SELECT epoch INTO principal_epoch FROM resource.incarnations WHERE principal=session_user;
 IF principal_epoch IS NULL OR principal_epoch<>request_epoch OR active_epoch<>request_epoch THEN
  RAISE EXCEPTION 'stale incarnation' USING ERRCODE='42501';
 END IF;
 INSERT INTO resource.effects VALUES(request_approval,request_epoch);
 UPDATE resource.payload SET value=value+1 WHERE singleton RETURNING value INTO result;
 RETURN result;
END $$;
ALTER FUNCTION resource.apply(bigint,text) OWNER TO effect_owner;
REVOKE ALL ON FUNCTION resource.apply(bigint,text) FROM PUBLIC;
GRANT USAGE ON SCHEMA resource TO old_writer,new_writer,executor;
GRANT EXECUTE ON FUNCTION resource.apply(bigint,text) TO old_writer,new_writer;
"""


class Lab:
    def __init__(self):
        self.root = Path(tempfile.mkdtemp(prefix='ln-r2d05-')).resolve()
        self.clusters = []
        self.cleaned = False
        try:
            for name in ('anchor', 'target'):
                cluster = Cluster(self.root, name)
                self.clusters.append(cluster)
                setattr(self, name, cluster)
            self.target.roles([('effect_owner', False), ('old_writer', True), ('new_writer', True), ('executor', True)])
        except BaseException:
            self.close()
            raise

    physical_clone = previous.Lab.physical_clone

    def close(self):
        errors = []
        for cluster in reversed(self.clusters):
            try:
                cluster.stop()
            except Exception as error:
                errors.append(repr(error))
        if errors:
            raise RuntimeError(errors)
        if self.root.parent != Path('/tmp') or not self.root.name.startswith('ln-r2d05-'):
            raise RuntimeError('invalid cleanup root')
        shutil.rmtree(self.root)
        self.cleaned = not self.root.exists()


class Resource:
    def __init__(self, lab):
        self.lab = lab
        self.admin = lab.target.database()
        self.anchor = lab.anchor.database()
        self.partition = False
        self.invocations = 0
        with psycopg.connect(self.admin) as connection:
            connection.execute('ALTER ROLE old_writer LOGIN')
            connection.execute(SCHEMA)
            database = connection.info.dbname
            connection.execute(sql.SQL('REVOKE ALL ON DATABASE {} FROM PUBLIC').format(sql.Identifier(database)))
            connection.execute(sql.SQL('GRANT CONNECT ON DATABASE {} TO old_writer,new_writer,executor').format(
                sql.Identifier(database)))
        with psycopg.connect(self.anchor) as connection:
            connection.execute('CREATE TABLE claims(approval text PRIMARY KEY)')
        self.pin = previous.endpoint_identity(self.admin)

    def connect(self, epoch=1):
        return psycopg.connect(psycopg.conninfo.make_conninfo(self.admin,
            user='old_writer' if epoch == 1 else 'new_writer'))

    def claim(self, approval):
        with psycopg.connect(self.anchor) as connection:
            connection.execute('INSERT INTO claims VALUES(%s)', (approval,))

    def apply(self, connection, epoch, approval, fixture=False):
        if not fixture:
            raise Blocked('D09 and authenticated UTC not demonstrated')
        return connection.execute('SELECT resource.apply(%s,%s)', (epoch, approval)).fetchone()[0]

    def state(self, dsn=None):
        with psycopg.connect(dsn or self.admin, autocommit=True) as connection:
            epoch = connection.execute('SELECT epoch FROM resource.fence').fetchone()[0]
            value = connection.execute('SELECT value FROM resource.payload').fetchone()[0]
            effects = connection.execute('SELECT approval,epoch FROM resource.effects ORDER BY approval').fetchall()
        with psycopg.connect(self.anchor) as connection:
            claims = connection.execute('SELECT count(*) FROM claims').fetchone()[0]
        return dict(epoch=epoch, value=value, effects=effects, claims=claims, resume=False, executable=False)

    def drain(self, expected=1, timeout_ms=1500):
        with psycopg.connect(self.admin) as connection:
            connection.execute(sql.SQL('SET LOCAL lock_timeout={}').format(sql.Literal(str(timeout_ms) + 'ms')))
            changed = connection.execute('UPDATE resource.fence SET epoch=epoch+1 WHERE epoch=%s RETURNING epoch',
                                         (expected,)).fetchone()
            if not changed:
                raise Blocked('epoch conflict')
        return dict(epoch=changed[0], scope='single PostgreSQL resource; transactions drained; process may live',
                    distributed_takeover_confirmed=False)

    def strict_takeover(self, expected=1, dsn=None, lose_ack=False, after_freeze=None):
        self.invocations += 1
        if self.partition:
            raise Blocked('old resource unreachable; cessation unverified')
        with psycopg.connect(dsn or self.admin, autocommit=True) as control:
            identity = previous.connected_identity(control)
            if identity != self.pin:
                raise Blocked('resource identity differs from configured old resource')
            if control.execute('SELECT epoch FROM resource.fence').fetchone()[0] != expected:
                raise Blocked('epoch conflict; reconciliation never authorizes retry')
            control.execute('ALTER ROLE old_writer NOLOGIN')
            if after_freeze:
                after_freeze()
            if self.partition:
                raise Blocked('partition after freeze; no confirmation')
            before = control.execute("SELECT pid,backend_start::text FROM pg_stat_activity WHERE usename='old_writer'").fetchall()
            for pid, backend_start in before:
                if not control.execute('SELECT pg_terminate_backend(%s)', (pid,)).fetchone()[0]:
                    raise Blocked('backend termination not acknowledged')
            deadline = time.monotonic() + 3
            while control.execute("SELECT count(*) FROM pg_stat_activity WHERE usename='old_writer'").fetchone()[0]:
                if time.monotonic() >= deadline:
                    raise Blocked('old backends still visible')
                time.sleep(0.01)
            changed = control.execute('UPDATE resource.fence SET epoch=epoch+1 WHERE epoch=%s RETURNING epoch',
                                      (expected,)).fetchone()
            if not changed:
                raise Blocked('concurrent takeover')
            enabled = control.execute("SELECT rolcanlogin FROM pg_roles WHERE rolname='old_writer'").fetchone()[0]
            remaining = control.execute("SELECT count(*) FROM pg_stat_activity WHERE usename='old_writer'").fetchone()[0]
            if enabled or remaining:
                raise Blocked('cessation check failed')
            receipt = dict(status='LOCAL_RESOURCE_FENCED', epoch=changed[0], resource=identity, terminated=before, old_login=enabled,
                old_backends=remaining, scope='old SQL role on one running PostgreSQL cluster',
                process_cessation_proven=False, distributed_cessation_proven=False,
                distributed_takeover_confirmed=False, executable=False)
            if lose_ack:
                return dict(status='UNKNOWN', resume=False, executable=False)
            return receipt

    def confirm_distributed_reentry(self, receipt):
        raise Blocked('no independent verifier of cessation across all effect resources is configured')

    def clone_dsn(self, cluster):
        return psycopg.conninfo.make_conninfo(self.admin, host=str(cluster.socket))
