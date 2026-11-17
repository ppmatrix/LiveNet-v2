"""Real TLS on temporary loopback ports; synthetic apps/stores, never DEV DB.

No LiveNet process, private configuration or certificate is read by these tests.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from http.client import HTTPResponse
from http.cookies import SimpleCookie
import json
import logging
import os
from pathlib import Path
import socket
import ssl
import subprocess
import sys
from threading import Event, Thread
import time
from unittest.mock import Mock
from uuid import uuid4

from flask import Flask, request
import pytest

from installation.https import DevHTTPSServer, Limits, run_dev_https


def eventually(predicate, seconds=3):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(.01)
    assert predicate()


@pytest.fixture(autouse=True)
def no_operational_dependencies(monkeypatch):
    monkeypatch.delenv('LIVENET_DISCOVERY_CONFIG', raising=False)
    monkeypatch.setattr('installation.config.Settings.connect',
                        lambda *a, **k: pytest.fail('Database connections prohibited'))
    monkeypatch.setattr('app.discovery.worker.Worker.start',
                        lambda *a, **k: pytest.fail('Discovery workers prohibited'))


@pytest.fixture(scope='module')
def certificates(tmp_path_factory):
    directory = tmp_path_factory.mktemp('dev-https-certificates')
    certificate, key = directory/'test.crt', directory/'test.key'
    subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
                    '-keyout', str(key), '-out', str(certificate), '-days', '1',
                    '-subj', '/CN=localhost', '-addext', 'subjectAltName=DNS:localhost,IP:127.0.0.1'],
                   check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certificate, key)
    client = ssl.create_default_context(cafile=str(certificate))
    return context, client, certificate, key


@pytest.fixture
def application():
    app = Flask('https-transport-tests')
    app.extensions['body_calls'] = []

    @app.get('/api/v1/health')
    def health():
        return {'status': 'ok'}

    @app.post('/body')
    def body():
        value = request.get_data()
        app.extensions['body_calls'].append(value)
        return {'bytes': len(value)}

    return app


@pytest.fixture
def servers(certificates, application):
    running = []

    def start(app=None, **overrides):
        limits = replace(Limits(), handshake_seconds=.5, header_seconds=.5,
                         body_seconds=.5, write_seconds=.5, shutdown_seconds=1,
                         header_bytes=2048, body_bytes=8192)
        limits = replace(limits, **overrides)
        server = DevHTTPSServer('127.0.0.1', 0, app or application, certificates[0], limits)
        assert server.port != 8443
        thread = Thread(target=server.serve_forever, name='isolated-https-acceptor')
        running.append((server, thread))
        thread.start()
        eventually(lambda: len(server._threads) == limits.workers)
        return server

    yield start
    for server, thread in running:
        server.shutdown()
        thread.join(3)
        assert not thread.is_alive()
        eventually(lambda: not any(t.is_alive() for t in server._threads))
        assert server.snapshot()['active'] == 0


def raw_client(server):
    sock = socket.create_connection(('127.0.0.1', server.port), timeout=2)
    sock.settimeout(2)
    return sock


def tls_client(server, certificates, receive_buffer=None):
    raw = raw_client(server)
    if receive_buffer:
        raw.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, receive_buffer)
    return certificates[1].wrap_socket(raw, server_hostname='localhost')


def exchange(server, certificates, raw):
    with tls_client(server, certificates) as sock:
        sock.sendall(raw)
        response = HTTPResponse(sock)
        response.begin()
        return response.status, response.getheaders(), response.read()


def healthy(server, certificates):
    started = time.monotonic()
    code, _, body = exchange(server, certificates,
                            b'GET /api/v1/health HTTP/1.1\r\nHost: localhost\r\n\r\n')
    elapsed = time.monotonic() - started
    assert code == 200 and json.loads(body)['status'] == 'ok'
    assert elapsed < 2
    return elapsed


@pytest.mark.parametrize('hello', [b'', b'\x16\x03\x01\x00\x80\x01\x00'])
def test_abandoned_and_partial_tls_do_not_block_accept(servers, certificates, hello):
    server = servers()
    with raw_client(server) as bad:
        started = time.monotonic()
        if hello:
            bad.sendall(hello)
        eventually(lambda: server.snapshot()['active'] == 1)
        healthy(server, certificates)
        eventually(lambda: server.snapshot()['timeouts_by_phase'].get('handshake') == 1)
        assert bad.recv(1) == b''
        assert time.monotonic() - started < server.limits.handshake_seconds + 1
    eventually(lambda: server.snapshot()['active'] == 0)


@pytest.mark.parametrize('phase,partial', [
    ('headers', b'GET /api/v1/health HTTP/1.1\r\nHost: localhost\r\nX-Incomplete:'),
    ('body', b'POST /body HTTP/1.1\r\nHost: localhost\r\nContent-Length: 20\r\n\r\nabc'),
])
def test_incomplete_http_does_not_block_other_requests(servers, certificates, application, phase, partial):
    server = servers()
    with tls_client(server, certificates) as bad:
        bad.sendall(partial)
        healthy(server, certificates)
        eventually(lambda: server.snapshot()['timeouts_by_phase'].get(phase) == 1)
    eventually(lambda: server.snapshot()['active'] == 0)
    assert not application.extensions['body_calls']


@pytest.mark.parametrize('phase,prefix', [
    ('headers', b'GET /api/v1/health HTTP/1.1\r\nHost: localhost\r\nX-Slow: '),
    ('body', b'POST /body HTTP/1.1\r\nHost: localhost\r\nContent-Length: 100\r\n\r\n'),
    ('body', b'POST /body HTTP/1.1\r\nHost: localhost\r\nTransfer-Encoding: chunked\r\n\r\n64\r\n'),
])
def test_absolute_deadlines_defeat_byte_trickling(servers, certificates, phase, prefix):
    server = servers()
    with tls_client(server, certificates) as bad:
        bad.sendall(prefix)
        start = time.monotonic()
        # Each byte arrives much sooner than the configured timeout.
        while time.monotonic() - start < .9:
            try:
                bad.sendall(b'x')
            except OSError:
                break
            if server.snapshot()['timeouts_by_phase'].get(phase):
                break
            healthy(server, certificates)
            time.sleep(.04)
        eventually(lambda: server.snapshot()['timeouts_by_phase'].get(phase) == 1)
        assert time.monotonic() - start < 1.2
    eventually(lambda: server.snapshot()['active'] == 0)


def test_truncated_body_and_unexpected_disconnect_never_enter_wsgi(servers, certificates, application):
    server = servers()
    for payload in (b'', b'POST /body HTTP/1.1\r\nHost: localhost\r\nContent-Length: 50\r\n\r\nx'):
        client = tls_client(server, certificates)
        if payload:
            client.sendall(payload)
        client.close()
        eventually(lambda: server.snapshot()['active'] == 0)
    assert application.extensions['body_calls'] == []
    healthy(server, certificates)


def test_concurrent_requests_within_capacity(servers, certificates):
    server = servers()
    with ThreadPoolExecutor(max_workers=4) as pool:
        elapsed = list(pool.map(lambda _: healthy(server, certificates), range(4)))
    assert max(elapsed) < 2
    eventually(lambda: server.snapshot()['active'] == 0)
    assert server.snapshot()['peak_active'] <= 4


def test_saturation_is_bounded_and_capacity_returns_after_timeouts(servers, certificates):
    server = servers()
    baseline_fds = len(list(Path('/proc/self/fd').iterdir()))
    for round_ in range(3):
        clients = [raw_client(server) for _ in range(server.limits.workers)]
        try:
            eventually(lambda: server.snapshot()['active'] == server.limits.workers)
            with raw_client(server) as rejected:
                assert rejected.recv(1) == b''
            eventually(lambda: server.snapshot()['rejected'] == round_ + 1)
            eventually(lambda: server.snapshot()['active'] == 0)
        finally:
            for client in clients:
                client.close()
        healthy(server, certificates)
        eventually(lambda: server.snapshot()['active'] == 0)
    assert len(server._threads) == server.limits.workers
    assert server.snapshot()['peak_active'] == server.limits.workers
    assert server.snapshot()['accepted'] == server.snapshot()['completed'] + server.snapshot()['rejected']
    assert len(list(Path('/proc/self/fd').iterdir())) <= baseline_fds + 1


def test_slow_response_reader_has_absolute_write_timeout(servers, certificates):
    def large_response(environ, start_response):
        if environ['PATH_INFO']=='/api/v1/health':
            start_response('200 OK', [('Content-Type', 'application/json')])
            return [b'{"status":"ok"}']
        start_response('200 OK', [('Content-Type', 'application/octet-stream')])
        return (b'x' * 65536 for _ in range(4096))
    server = servers(large_response)
    with tls_client(server, certificates, receive_buffer=4096) as bad:
        bad.sendall(b'GET /large HTTP/1.1\r\nHost: localhost\r\n\r\n')
        healthy(server, certificates)
        eventually(lambda: server.snapshot()['timeouts_by_phase'].get('write') == 1)
        eventually(lambda: server.snapshot()['active'] == 0)


@pytest.mark.parametrize('headers,status', [
    (b'Content-Length: 8193\r\n', 413),
    (b'Content-Length: 1\r\nContent-Length: 1\r\n', 400),
    (b'Transfer-Encoding: chunked\r\nContent-Length: 1\r\n', 400),
    (b'Transfer-Encoding: gzip\r\n', 400),
    (b'Content-Length: -1\r\n', 400),
    (b'X-Large: '+b'x'*2500+b'\r\n', 431),
])
def test_request_bounds_and_ambiguous_framing(servers, certificates, application, headers, status):
    server = servers()
    code, _, _ = exchange(server, certificates,
                          b'POST /body HTTP/1.1\r\nHost: localhost\r\n'+headers+b'\r\n')
    assert code == status
    assert not application.extensions['body_calls']
    healthy(server, certificates)


def test_chunked_body_and_expect_continue(servers, certificates, application):
    server = servers()
    code, _, body = exchange(server, certificates,
        b'POST /body HTTP/1.1\r\nHost: localhost\r\nTransfer-Encoding: chunked\r\n\r\n3\r\nabc\r\n0\r\n\r\n')
    assert code == 200 and json.loads(body)['bytes'] == 3
    with tls_client(server, certificates) as sock:
        sock.sendall(b'POST /body HTTP/1.1\r\nHost: localhost\r\nContent-Length: 3\r\nExpect: 100-continue\r\n\r\n')
        assert sock.recv(1024) == b'HTTP/1.1 100 Continue\r\n\r\n'
        sock.sendall(b'xyz')
        response = HTTPResponse(sock); response.begin()
        assert response.status == 200 and json.loads(response.read())['bytes'] == 3
    assert application.extensions['body_calls'] == [b'abc', b'xyz']


def test_chunked_size_and_framing_overhead_are_bounded(servers, certificates, application):
    server = servers(body_bytes=32)
    payload = b'21\r\n'+b'x'*33+b'\r\n0\r\n\r\n'
    status, _, _ = exchange(server, certificates,
        b'POST /body HTTP/1.1\r\nHost: localhost\r\nTransfer-Encoding: chunked\r\n\r\n'+payload)
    assert status == 413 and not application.extensions['body_calls']
    prefix=b'POST /body HTTP/1.1\r\nHost: localhost\r\nTransfer-Encoding: chunked\r\n\r\n'
    status, _, _ = exchange(server, certificates, prefix+(b'1\r\nx\r\n'*32)+b'0\r\n\r\n')
    assert status == 200 and application.extensions['body_calls']==[b'x'*32]
    # Long, valid hex lengths decoding to one byte: wire size is independently bounded.
    padded=(b'0'*88+b'1\r\nx\r\n')*32+b'0\r\n\r\n'
    status, _, _ = exchange(server, certificates, prefix+padded)
    assert status == 413 and len(application.extensions['body_calls'])==1


def test_invalid_tls_is_classified_without_losing_capacity(servers, certificates, caplog):
    caplog.set_level(logging.INFO, logger='livenet.https')
    server = servers()
    with raw_client(server) as bad:
        bad.sendall(b'GET /not-tls HTTP/1.1\r\n\r\n')
        eventually(lambda: server.snapshot()['handshake_errors'] == 1)
    eventually(lambda: server.snapshot()['active'] == 0)
    assert 'handshake_error' in caplog.text
    healthy(server, certificates)


def test_shutdown_cancels_pending_sockets_and_fixed_workers(servers, certificates, caplog):
    caplog.set_level(logging.INFO, logger='livenet.https')
    server = servers(handshake_seconds=10, header_seconds=10)
    clients = [raw_client(server), tls_client(server, certificates)]
    try:
        clients[1].sendall(b'GET / HTTP/1.1\r\nX:')
        eventually(lambda: server.snapshot()['active'] == 2)
        start = time.monotonic()
        server.shutdown()
        eventually(lambda: not any(t.is_alive() for t in server._threads))
        assert time.monotonic() - start < 1.5
        assert server.snapshot()['active'] == 0
        eventually(lambda: any('server_stopped' in r.message for r in caplog.records))
        events = [json.loads(r.message) for r in caplog.records if r.name == 'livenet.https']
        assert next(e for e in events if e['event'] == 'server_stopped')['clean'] is True
    finally:
        for client in clients:
            client.close()


def test_shutdown_reports_an_application_that_outlives_grace(servers, certificates, caplog):
    caplog.set_level(logging.INFO, logger='livenet.https')
    entered, release = Event(), Event()
    def blocked(environ, start_response):
        entered.set()
        release.wait(3)
        start_response('200 OK', [('Content-Length','0')])
        return []
    server = servers(blocked, shutdown_seconds=.1)
    client = tls_client(server, certificates)
    try:
        client.sendall(b'GET / HTTP/1.1\r\nHost: localhost\r\n\r\n')
        assert entered.wait(1)
        server.shutdown()
        eventually(lambda: any('server_stopped' in r.message for r in caplog.records))
        events = [json.loads(r.message) for r in caplog.records if r.name == 'livenet.https']
        assert next(e for e in events if e['event'] == 'server_stopped')['clean'] is False
    finally:
        release.set()
        client.close()
    eventually(lambda: server.snapshot()['active'] == 0)


def test_diagnostics_never_include_request_or_exception_values(servers, certificates, caplog):
    caplog.set_level(logging.INFO, logger='livenet.https')
    secret = 'synthetic-password-cookie-token-discovery-value'
    def broken(environ, start_response):
        raise RuntimeError(secret)
    server = servers(broken)
    status, _, _ = exchange(server, certificates,
        ('GET /private?token='+secret+' HTTP/1.1\r\nHost: localhost\r\nCookie: '+secret+'\r\n\r\n').encode())
    assert status == 500
    eventually(lambda: server.snapshot()['active'] == 0)
    assert secret not in caplog.text
    assert 'wsgi_error' in caplog.text and 'request_finished' in caplog.text


def test_real_https_standard_security_inventory_and_disabled_discovery(servers, certificates, tmp_path):
    from test_standard_runtime import configuration
    from installation.runtime import create_standard_app
    from app.security.models import LocalUser, GlobalRoleGrant
    from app.security.service import hash_password
    from security_doubles import OfflineStore
    config, _ = configuration(tmp_path)
    store = OfflineStore()
    user = LocalUser(id=uuid4(), login='operator', password_hash=hash_password('offline-https-password'), status='active')
    store.users[user.id] = user
    store.grants.append(GlobalRoleGrant(user_id=user.id, role='inventory_editor', scope_type='global', scope_id=None))
    app = create_standard_app(config)
    app.extensions['inventory']._session_factory = store.factory
    app.extensions['security']._sessions = store.factory
    server = servers(app, body_bytes=1048576)
    cookies = {}
    origin = 'https://product.test:9443'
    def call(path, method='GET', data=None, headers=None):
        payload = json.dumps(data).encode() if data is not None else b''
        values = {'Host':'product.test:9443', 'Cookie':'; '.join(k+'='+v for k,v in cookies.items()), **(headers or {})}
        if data is not None:
            values.update({'Content-Type':'application/json','Content-Length':str(len(payload))})
        raw = (method+' '+path+' HTTP/1.1\r\n'+''.join(k+': '+v+'\r\n' for k,v in values.items())+'\r\n').encode()+payload
        code, response_headers, body = exchange(server, certificates, raw)
        for k,v in response_headers:
            if k.lower()=='set-cookie':
                parsed=SimpleCookie();parsed.load(v)
                for name,item in parsed.items():cookies[name]=item.value
        content_type = next((v for k,v in response_headers if k.lower()=='content-type'), '')
        return code, response_headers, json.loads(body) if body and 'application/json' in content_type else body
    assert call('/login')[0] == 200
    assert call('/api/v1/inventory/resources')[0] == 401
    token = call('/api/v1/auth/csrf')[2]['csrf_token']
    code, login_headers, _ = call('/api/v1/auth/login','POST',{'login':'operator','password':'offline-https-password'}, {'Origin':origin,'X-CSRF-Token':token})
    assert code == 200
    session_cookie = next(v for k,v in login_headers if k.lower()=='set-cookie' and v.startswith('__Host-livenet_session='))
    assert 'Secure' in session_cookie and 'HttpOnly' in session_cookie and 'SameSite=Lax' in session_cookie
    _, headers, _ = call('/api/v1/auth/me')
    assert call('/api/v1/auth/me')[0] == 200
    assert call('/api/v1/inventory/resources','POST',{})[0] == 403
    token = call('/api/v1/auth/csrf')[2]['csrf_token']
    assert call('/api/v1/auth/login','POST',{'login':'operator','password':'x'*17000}, {'Origin':origin,'X-CSRF-Token':token})[0] == 413
    assert call('/api/v1/inventory/resources','POST',{}, {'Origin':'https://wrong.test','X-CSRF-Token':token})[0] == 403
    code, _, body = call('/api/v1/inventory/resources','POST',{'resource_type':'service','display_name':'Offline HTTPS'}, {'Origin':origin,'X-CSRF-Token':token})
    assert code == 201
    assert call('/api/v1/inventory/resources')[2]['total'] == 1
    assert call('/api/v1/discovery/config')[2]['enabled'] is False
    assert call('/api/v1/discovery/jobs')[0] == 503
    assert call('/api/v1/auth/csrf',headers={'Host':'wrong.test'})[0] == 403
    assert call('/api/v1/auth/csrf',headers={'X-Forwarded-Proto':'https'})[0] == 403
    assert app.extensions['discovery']['worker'] is None
    assert call('/api/v1/auth/logout','POST',headers={'Origin':origin,'X-CSRF-Token':token})[0] == 204
    assert call('/api/v1/auth/me')[0] == 401


def test_runner_constructs_one_app_and_stops_only_its_worker(certificates, monkeypatch):
    fake = Mock()
    fake.limits.shutdown_seconds = .1
    fake.serve_forever.return_value = None
    worker = Mock()
    worker.thread.is_alive.return_value = False
    app = Mock(extensions={'discovery':{'worker':worker}})
    factory = Mock(return_value=app)
    monkeypatch.setattr('installation.https.DevHTTPSServer', Mock(return_value=fake))
    run_dev_https('127.0.0.1', 0, factory, certificates[2], certificates[3])
    factory.assert_called_once_with()
    fake.serve_forever.assert_called_once_with()
    worker.stop.set.assert_called_once_with()
    worker.start.assert_not_called()
    worker.current_cancel.set.assert_called_once_with()


def test_bind_failure_does_not_construct_app_or_worker(certificates):
    factory = Mock()
    with socket.socket() as occupied:
        occupied.bind(('127.0.0.1', 0))
        occupied.listen()
        port = occupied.getsockname()[1]
        assert port != 8443
        with pytest.raises(SystemExit):
            run_dev_https('127.0.0.1', port, factory, certificates[2], certificates[3])
    factory.assert_not_called()


def test_incomplete_worker_shutdown_is_reported_as_failure(certificates, monkeypatch, capsys):
    from installation.__main__ import main
    fake = Mock()
    fake.limits.shutdown_seconds = .1
    fake.shutdown_clean = True
    worker = Mock()
    worker.thread.is_alive.return_value = True
    app = Mock(extensions={'discovery':{'worker':worker}})
    monkeypatch.setattr('installation.https.DevHTTPSServer', Mock(return_value=fake))
    monkeypatch.setattr('installation.__main__.Settings.load', lambda path: object())
    monkeypatch.setattr('installation.__main__.serve', lambda *args:
                        run_dev_https('127.0.0.1', 0, lambda: app, certificates[2], certificates[3]))
    assert main(['serve','--config','unused-test-configuration']) == 78
    assert json.loads(capsys.readouterr().out)['code'] == 'HTTPS_SHUTDOWN_INCOMPLETE'


# Final review regressions: these exercise gaps not covered by the initial suite.
def test_partial_ssl_sends_share_one_absolute_deadline(servers, certificates, monkeypatch):
    original = ssl.SSLSocket.send
    def partial(sock, data, flags=0):
        if sock.server_side:
            time.sleep(.015)
            return original(sock, data[:1], flags)
        return original(sock, data, flags)
    monkeypatch.setattr(ssl.SSLSocket, 'send', partial)
    server = servers(write_seconds=.15)
    with tls_client(server, certificates) as client:
        started = time.monotonic()
        client.sendall(b'GET /api/v1/health HTTP/1.1\r\nHost: localhost\r\n\r\n')
        eventually(lambda: server.snapshot()['timeouts_by_phase'].get('write') == 1, seconds=.8)
        assert time.monotonic() - started < .8
    eventually(lambda: server.snapshot()['active'] == 0)


@pytest.mark.parametrize('headers', [
    b'Content-Length : 3\r\n',
    b'Content-Length: 3\r\n ignored-fold\r\n',
    b'Transfer-Encoding: chunked\r\n folded\r\n',
    b'Broken header\r\nContent-Length: 3\r\n',
    b'X-Control: \x00\r\nContent-Length: 3\r\n',
    b'Host: another.test\r\nContent-Length: 3\r\n',
])
def test_malformed_headers_never_reach_wsgi(servers, certificates, application, headers):
    server = servers()
    status, _, _ = exchange(server, certificates,
        b'POST /body HTTP/1.1\r\nHost: localhost\r\n'+headers+b'\r\nabc')
    assert status == 400
    assert not application.extensions['body_calls']


@pytest.mark.parametrize('payload', [
    b'+3\r\nabc\r\n0\r\n\r\n',
    b'0x3\r\nabc\r\n0\r\n\r\n',
    b'3\nabc\n0\n\n',
])
def test_non_http_chunk_framing_never_reaches_wsgi(servers, certificates, application, payload):
    server = servers()
    status, _, _ = exchange(server, certificates,
        b'POST /body HTTP/1.1\r\nHost: localhost\r\nTransfer-Encoding: chunked\r\n\r\n'+payload)
    assert status == 400
    assert not application.extensions['body_calls']


def test_pipelined_request_is_never_executed(servers, certificates, application):
    server = servers()
    status, _, _ = exchange(server, certificates,
        b'GET /api/v1/health HTTP/1.1\r\nHost: localhost\r\nConnection: keep-alive\r\n\r\n'
        b'POST /body HTTP/1.1\r\nHost: localhost\r\nContent-Length: 3\r\n\r\nabc')
    assert status == 200
    eventually(lambda: server.snapshot()['active'] == 0)
    assert not application.extensions['body_calls']


def test_shutdown_always_closes_wsgi_iterable(servers, certificates):
    entered, release, closed = Event(), Event(), Event()
    class Body:
        def __iter__(self):
            entered.set()
            release.wait(3)
            yield b'ok'
        def close(self):
            closed.set()
    def app(environ, start_response):
        start_response('200 OK', [('Content-Length','2')])
        return Body()
    server = servers(app, shutdown_seconds=.1)
    client = tls_client(server, certificates)
    try:
        client.sendall(b'GET / HTTP/1.1\r\nHost: localhost\r\n\r\n')
        assert entered.wait(1)
        server.shutdown()
        eventually(lambda: server.shutdown_clean is False)
        release.set()
        eventually(lambda: server.snapshot()['active'] == 0)
        assert closed.is_set()
    finally:
        release.set()
        client.close()


def test_partial_pool_start_failure_closes_started_threads(certificates, application, monkeypatch):
    count = 0
    class FailingThread(Thread):
        def start(self):
            nonlocal count
            count += 1
            if count == 2:
                raise RuntimeError('synthetic thread capacity exhausted')
            super().start()
    monkeypatch.setattr('installation.https.Thread', FailingThread)
    server = DevHTTPSServer('127.0.0.1', 0, application, certificates[0])
    assert server.port != 8443
    with pytest.raises(RuntimeError, match='synthetic thread capacity exhausted'):
        server.serve_forever()
    assert server.socket.fileno() == -1
    assert not any(t.is_alive() for t in server._threads)


@pytest.mark.parametrize('lock_name', ['server', 'worker'])
@pytest.mark.parametrize('signal_name', ['SIGINT', 'SIGTERM'])
def test_real_signal_during_held_event_lock_exits_child(certificates, tmp_path, lock_name, signal_name):
    # Only this newly created test child receives a signal. No operational app,
    # configuration, DB, worker thread or equipment is used.
    program = r'''
import os, signal, sys
from pathlib import Path
from threading import Event
from types import SimpleNamespace
import installation.https as transport
Base = transport.DevHTTPSServer
class Server(Base):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        assert self.port != 8443
        Path(sys.argv[3]).write_text(str(self.port))
    def process_request(self, request, address):
        event = self._stopping if sys.argv[4]=='server' else self.app.extensions['discovery']['worker'].stop
        with event._cond:
            os.kill(os.getpid(), getattr(signal, sys.argv[5]))
        super().process_request(request, address)
class App:
    extensions = {'discovery': {'worker': SimpleNamespace(stop=Event(), current_cancel=None, thread=None)}}
    def __call__(self, environ, start_response):
        start_response('200 OK', [('Content-Length','0')])
        return []
transport.DevHTTPSServer = Server
transport.run_dev_https('127.0.0.1', 0, App, sys.argv[1], sys.argv[2])
'''
    port_file = tmp_path/'isolated-port'
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1',
               PYTHONPATH=str(Path(__file__).resolve().parents[1]))
    env.pop('LIVENET_DISCOVERY_CONFIG', None)
    child = subprocess.Popen([sys.executable, '-B', '-c', program,
                              str(certificates[2]), str(certificates[3]), str(port_file), lock_name, signal_name],
                             env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        eventually(port_file.exists)
        with socket.create_connection(('127.0.0.1', int(port_file.read_text())), timeout=1):
            assert child.wait(timeout=2) == 0
    finally:
        if child.poll() is None:
            child.kill()
        child.communicate(timeout=2)


@pytest.mark.parametrize('fault', ['untrusted_certificate', 'wrong_hostname'])
def test_tls_verification_rejects_invalid_trust_or_hostname(servers, certificates, fault):
    server = servers()
    context = ssl.create_default_context() if fault=='untrusted_certificate' else certificates[1]
    hostname = 'localhost' if fault=='untrusted_certificate' else 'wrong.test'
    raw = raw_client(server)
    try:
        with pytest.raises(ssl.SSLCertVerificationError):
            context.wrap_socket(raw, server_hostname=hostname)
    finally:
        raw.close()
    eventually(lambda: server.snapshot()['active']==0)
    healthy(server, certificates)


def test_wsgi_iterable_closes_exactly_once_on_success(servers, certificates):
    closed = []
    class Body:
        def __iter__(self):
            return iter([b'ok'])
        def close(self):
            closed.append(True)
    def app(environ, start_response):
        start_response('200 OK', [('Content-Length','2')])
        return Body()
    server = servers(app)
    status, _, body = exchange(server, certificates, b'GET / HTTP/1.1\r\nHost: localhost\r\n\r\n')
    assert status==200 and body==b'ok'
    eventually(lambda: server.snapshot()['active']==0)
    assert closed==[True]


@pytest.mark.parametrize('tail', [b'Content-Length: 0\r\n', b'Content-Length: 0'])
def test_eof_before_header_terminator_never_reaches_wsgi(servers, certificates, application, tail):
    server = servers()
    with tls_client(server, certificates) as client:
        client.sendall(b'POST /body HTTP/1.1\r\nHost: localhost\r\n'+tail)
        client.shutdown(socket.SHUT_WR)
        eventually(lambda: server.snapshot()['active']==0)
    assert application.extensions['body_calls']==[]


@pytest.mark.parametrize('raw', [
    b'POST /body HTTP/1.1\r\nContent-Length: 0\r\n\r\n',
    b'POST /body HTTP/1.1\r\nHost: \r\nContent-Length: 0\r\n\r\n',
    b'POST /body HTTP/1.1\nHost: localhost\r\nContent-Length: 0\r\n\r\n',
])
def test_request_envelope_is_unambiguous(servers, certificates, application, raw):
    server = servers()
    assert exchange(server, certificates, raw)[0]==400
    assert application.extensions['body_calls']==[]
