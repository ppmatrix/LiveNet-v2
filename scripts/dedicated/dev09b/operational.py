"""Offline implementation of Linux local operational ports; never approval.

Control traffic uses AF_UNIX + SO_PEERCRED (kernel authenticated, no shared
executor secret). Target PostgreSQL still requires its separately bound TLS.
Constructors do no I/O. Hosting, identities, approved policy and deployment are
explicit. No retries, credential discovery, grant, reset or approval issuance.
"""
from dataclasses import asdict
from hashlib import sha256
import math
import os
from pathlib import Path
import select
import socket
import stat
import struct
import time
from uuid import uuid4

from . import codec as c
from .model import ContinuitySample, SessionBinding, TimeSample

MAX_FRAME = 16 * 1024 * 1024


def _receive(sock, count):
    result = bytearray()
    while len(result) < count:
        part = sock.recv(count - len(result))
        c.require(bool(part))
        result.extend(part)
    return bytes(result)


def _read(sock):
    size = struct.unpack('!I', _receive(sock, 4))[0]
    c.require(0 < size <= MAX_FRAME)
    return c.parse(_receive(sock, size), maximum=MAX_FRAME,maximum_depth=32)


def _write(sock, value):
    raw = c.canonical(value,maximum_depth=32)
    c.require(0 < len(raw) <= MAX_FRAME)
    sock.sendall(struct.pack('!I', len(raw)) + raw)


def _peer(sock, uid):
    c.integer(uid, 1)  # root is deliberately not an operational caller
    pid, actual, _ = struct.unpack('3i', sock.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
    c.require(pid > 0 and actual == uid)


class LocalRPC:
    """One connection/request, exact server UID, request-bound response, no retry.

    Directory/socket ownership and write restrictions are deployment obligations.
    Peer credentials are checked before sending a profile or session binding.
    No network listener, response signature or authentication boolean is used.
    """
    def __init__(self, path, server_uid, *, timeout=2.0):
        self.path, self.server_uid, self.timeout = str(path), server_uid, timeout

    def call(self, method, arguments):
        request_id = str(uuid4())
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(self.timeout)
            sock.connect(self.path)
            _peer(sock, self.server_uid)
            _write(sock, dict(request_id=request_id, method=method, arguments=arguments))
            response = _read(sock)
        c.closed(response, {'request_id', 'result', 'ok'})
        c.require(response['request_id'] == request_id and response['ok'] is True)
        return response['result']


def serve_one(listener, *, caller_uid, dispatch, timeout=2.0):
    """Serve one authenticated request on an explicitly supplied local listener.

    Service hosts must serialize this function, own their socket exclusively and
    stop on supervision failure. Exceptions are fixed diagnostics, no SQL text.
    No bind/unlink/start occurs here; never replace a live service's socket.
    """
    sock, _ = listener.accept()
    with sock:
        sock.settimeout(timeout)
        _peer(sock, caller_uid)
        request = _read(sock)
        c.closed(request, {'request_id', 'method', 'arguments'})
        c.uuid(request['request_id'])
        try:
            result = dispatch(request['method'], request['arguments'])
        except Exception:
            _write(sock, dict(request_id=request['request_id'], result=None, ok=False))
            return
        _write(sock, dict(request_id=request['request_id'], result=result, ok=True))


class AuthorityRPC:
    """Endpoint + one-use verifier for AuthenticatedAuthorityClient.

    A receipt is accepted only if this instance just obtained that exact object
    over its authenticated socket. Remote record failures propagate too.
    """
    def __init__(self, rpc):
        self.rpc = rpc
        self._pending = {}

    def _receipt(self, method, values, profile_json):
        values['profile_json'] = profile_json.decode('utf8')
        c.require(not self._pending)
        result = self.rpc.call(method, values)
        self._pending[id(result)] = (result, c.canonical(result))
        return result

    def consume(self, approval_id, session, nonce, *, profile_json):
        return self._receipt('consume', dict(approval_id=approval_id,
            session=asdict(session), nonce=nonce), profile_json)

    def check(self, attempt_id, phase, session, nonce, *, profile_json):
        return self._receipt('check', dict(attempt_id=attempt_id, phase=phase,
            session=asdict(session), nonce=nonce), profile_json)

    def authenticate(self, raw):
        pending = self._pending.pop(id(raw), None)
        c.require(pending is not None and pending[0] is raw)
        return c.parse(pending[1], maximum=MAX_FRAME)

    def record(self, attempt_id, event, evidence_sha256):
        c.require(self.rpc.call('record', dict(attempt_id=attempt_id,
            event=event, evidence_sha256=evidence_sha256)) is None)


class LocalReceiptChannel:
    """Only for a service hosted behind serve_one's authenticated local socket."""
    def seal(self, receipt):
        return receipt


class AuthorityDispatch:
    """Expose only the existing PUBLIC service, never revoke/load/reset."""
    def __init__(self, service):
        self.service = service

    def __call__(self, method, arguments):
        fields = {
            'consume': {'approval_id', 'session', 'nonce', 'profile_json'},
            'check': {'attempt_id', 'phase', 'session', 'nonce', 'profile_json'},
            'record': {'attempt_id', 'event', 'evidence_sha256'},
        }
        c.require(method in fields)
        c.closed(arguments, fields[method])
        args = dict(arguments)
        if method != 'record':
            args['session'] = SessionBinding(**args['session'])
            args['session'].validate()
            args['profile_json'] = args['profile_json'].encode('utf8')
        return getattr(self.service, method)(**args)


class AnchoredClock:
    """Short controlled window anchored to an independently approved UTC range.

    Anchor is sampled/provisioned by the supervisor, not inferred from DB state
    or claimed trustworthy from time.time(). Drift bound and maximum lifetime
    are explicit policy. Restart needs a fresh independent anchor/window.
    """
    def __init__(self, lower, upper, *, max_age, drift_ppm, monotonic=time.monotonic):
        TimeSample(lower, upper, True).validate()
        c.integer(max_age, 1, 3600)
        c.integer(drift_ppm, 0, 10000)
        self.lower, self.upper = lower, upper
        self.max_age, self.drift = max_age, drift_ppm / 1000000
        self.monotonic, self.started = monotonic, None

    def start(self):
        c.require(self.started is None)
        self.started = self.monotonic()

    def sample(self):
        c.require(self.started is not None)
        elapsed = self.monotonic() - self.started
        c.require(0 <= elapsed <= self.max_age)
        return TimeSample(self.lower + math.floor(elapsed * (1 - self.drift)),
                          self.upper + math.ceil(elapsed * (1 + self.drift)), True)


class DurableContinuity:
    """Independent supervisor storage outside authority DB/backup/restore.

    A pre-provisioned private directory is consumed once using O_EXCL + fsync.
    Restart with the same directory is refused, including after a clean stop.
    BLOCKED never clears. No initialize/reset/recovery interface. Trusted admin
    coordination and independent recovery are direction B obligations.
    """
    def __init__(self, directory, token):
        c.uuid(token)
        self.directory, self.token = Path(directory), token
        self.active = False

    def start(self):
        c.require(not self.active and self.directory.is_absolute())
        for path in (self.directory, *self.directory.parents):
            c.require(not path.is_symlink())
        info = self.directory.stat()
        c.require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.geteuid()
                  and stat.S_IMODE(info.st_mode) == 0o700)
        self._write_new('STARTED', self.token.encode('ascii'))
        c.require(not (self.directory / 'BLOCKED').exists())
        self.active = True

    def _write_new(self, name, data):
        fd = os.open(self.directory / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            with os.fdopen(fd, 'wb') as out:
                out.write(data)
                out.flush()
                os.fsync(out.fileno())
            directory = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try: os.fsync(directory)
            finally: os.close(directory)
        except BaseException:
            self.active = False
            raise

    def sample(self):
        c.require(self.active and not (self.directory / 'BLOCKED').exists())
        c.require((self.directory / 'STARTED').read_bytes() == self.token.encode('ascii'))
        return ContinuitySample(self.token, True)

    def block(self):
        self.active = False  # latch locally even on I/O failure
        try: self._write_new('BLOCKED', b'BLOCKED\n')
        except FileExistsError: pass


class WindowDispatch:
    """Independent one-shot supervisor for a previously approved exact session.

    observe() MUST use a separate observer connection/process and raise unless
    the fixed target identity, PID/start/xact, TLS and absence of concurrent
    writers still hold. It is never the migrating connection. Administrative
    coordination is an explicit external prerequisite, not advisory-lock proof.
    """
    def __init__(self, *, continuity, clock, session, plan, observe):
        session.validate()
        self.continuity, self.clock = continuity, clock
        self.session, self.plan_hash = asdict(session), sha256(plan).hexdigest()
        self.observe = observe

    def __call__(self, method, arguments):
        if method == 'block':
            c.closed(arguments, set())
            self.continuity.block()
            return None
        c.require(method in {'sample', 'assert_bound', 'time'})
        try:
            if method == 'assert_bound':
                c.closed(arguments, {'session', 'plan_sha256'})
                c.require(arguments['session'] == self.session and arguments['plan_sha256'] == self.plan_hash)
            else:
                c.closed(arguments, set())
            indication = self.continuity.sample()
            now = self.clock.sample()
            c.require(self.observe() is None)
            return asdict(now if method == 'time' else indication)
        except BaseException:
            self.continuity.block()
            raise


def supervise_window(*, listeners, dispatch):
    """Independent process loop, no target SQL in the executor's event hook.

    listeners is a sequence of (already bound socket, exact allowed caller UID).
    Recheck independently while idle; stop and latch on failure. No restart,
    reset, listener replacement, thread or signal-driven recovery is supplied.
    Hosting must separately establish the approved admin coordination window.
    """
    try:
        while True:
            dispatch('sample', {})
            ready, _, _ = select.select([s for s, _ in listeners], [], [], 0.5)
            for listener, uid in listeners:
                if listener in ready:
                    serve_one(listener, caller_uid=uid, dispatch=dispatch)
    finally:
        try: dispatch.continuity.block()
        finally:
            for listener, _ in listeners: listener.close()


class RemoteContinuity:
    def __init__(self, rpc): self.rpc = rpc
    def sample(self):
        result = ContinuitySample(**self.rpc.call('sample', {}))
        result.validate()
        return result
    def block(self): c.require(self.rpc.call('block', {}) is None)


class RemoteClock:
    def __init__(self, rpc): self.rpc = rpc
    def sample(self):
        result = TimeSample(**self.rpc.call('time', {}))
        result.validate()
        return result


class PostgresWindowObserver:
    """Independent fresh READ ONLY connection per observation, no admin SQL.

    Existing trusted admin credential stays ONLY in the supervisor. No new stats
    grant is inferred for the executor/probe. Binding is fixed before dispatch;
    it must include the authenticated numeric/virtual transaction cross-binding.
    Serial hosting prevents one observer seeing another observer connection.
    Unknown sessions (including idle admin sessions) and prepared xacts block.
    """
    def __init__(self, *, connections, binding):
        self.connections, self.binding = connections, dict(binding)

    def __call__(self):
        from sqlalchemy import text
        connection = transaction = None
        try:
            connection = self.connections()
            c.require(not connection.in_transaction() and connection.dialect.name == 'postgresql')
            c.require(connection.connection.driver_connection.autocommit is False)
            transaction = connection.begin()
            connection.execute(text('SET TRANSACTION READ ONLY'))
            connection.execute(text("SET LOCAL statement_timeout = '1500ms'"))
            connection.execute(text("SET LOCAL lock_timeout = '500ms'"))
            identity = connection.execute(text("""SELECT current_database() AS database,
                (pg_catalog.pg_control_system()).system_identifier::text AS system_identifier,
                session_user::text AS principal, current_user::text AS effective_principal,
                pg_backend_pid() AS observer_pid""")).mappings().one()
            for field in ('database', 'system_identifier', 'principal'):
                c.require(identity[field] == self.binding[field])
            c.require(identity['effective_principal'] == self.binding['principal'])
            rows = list(connection.execute(text("""SELECT a.pid, a.usename,
                a.backend_start::text AS backend_start, a.xact_start::text AS xact_start,
                l.virtualtransaction AS virtualxid, s.ssl, s.version AS tls_version
                FROM pg_catalog.pg_stat_activity a
                LEFT JOIN pg_catalog.pg_stat_ssl s ON s.pid=a.pid
                LEFT JOIN pg_catalog.pg_locks l ON l.pid=a.pid AND l.locktype='virtualxid'
                  AND l.mode='ExclusiveLock' AND l.granted
                WHERE a.datname=current_database() AND a.pid<>pg_backend_pid()
                  AND a.backend_type='client backend'""")).mappings())
            c.require({r['pid'] for r in rows} == {self.binding['pid']})
            subject = [r for r in rows if r['pid'] == self.binding['pid']]
            c.require(len(subject) == 1)
            for field in ('pid', 'usename', 'backend_start', 'xact_start', 'virtualxid'):
                c.require(subject[0][field] == self.binding[field])
            c.require(subject[0]['ssl'] is True and subject[0]['tls_version'] in {'TLSv1.2', 'TLSv1.3'})
            c.require(connection.execute(text('SELECT count(*) FROM pg_catalog.pg_prepared_xacts')).scalar_one() == 0)
        finally:
            try:
                if transaction is not None: transaction.rollback()
            finally:
                if connection is not None: connection.close()


class TrialSupervision:
    """Remote exclusivity at every dispatch; existing same-session comparison."""
    def __init__(self, *, rpc, connection, transaction, session, snapshot, plan,
                 profile_json, profile_verifier, precommit_contract, source_root):
        self.rpc, self.connection, self.transaction = rpc, connection, transaction
        self.session, self.plan = session, bytes(plan)
        self.snapshot, self.profile = snapshot, profile_json
        self.verifier, self.contract, self.root = profile_verifier, precommit_contract, source_root

    def assert_bound(self, connection, transaction, session, plan):
        c.require(connection is self.connection and transaction is self.transaction
                  and session == self.session and bytes(plan) == self.plan)
        # No SQL here: called inside before_cursor_execute.
        result = self.rpc.call('assert_bound', dict(session=asdict(session),
            plan_sha256=sha256(plan).hexdigest()))
        indication = ContinuitySample(**result)
        indication.validate()

    def before_commit(self, connection, transaction, session, plan):
        self.assert_bound(connection, transaction, session, plan)
        from migrations.dev09b_inspection import PreparedInspectionPort
        port = PreparedInspectionPort(connection, transaction, profile_verifier=self.verifier,
            contract_json=self.contract, source_root=self.root)
        port.observe_detailed(self.profile, self.snapshot, phase='APP-F066-PRECOMMIT', session=session)
        self.assert_bound(connection, transaction, session, plan)
