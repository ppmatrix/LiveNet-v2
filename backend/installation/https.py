"""Bounded, direct HTTPS transport for the standard DEV entrypoint only.

TCP accept never performs TLS. Fixed workers own handshakes and one HTTP request
per connection. Absolute receive deadlines and bounded prebuffering keep slow or
incomplete bodies out of WSGI (and therefore out of application transactions).
No configuration, application factory or Discovery worker is loaded on import.
"""
from dataclasses import dataclass
import io
import json
import logging
from queue import Empty, Queue
import re
import selectors
import signal
import socket
import ssl
from threading import Event, Lock, Thread, current_thread, main_thread
import time

from werkzeug.serving import BaseWSGIServer, DechunkedInput, WSGIRequestHandler

from installation import Refused


LOG = logging.getLogger('livenet.https')


@dataclass(frozen=True)
class Limits:
    workers: int = 4
    backlog: int = 8
    handshake_seconds: float = 5.0
    header_seconds: float = 10.0
    body_seconds: float = 15.0
    write_seconds: float = 10.0
    shutdown_seconds: float = 5.0
    header_bytes: int = 65536
    body_bytes: int = 1048576

    def __post_init__(self):
        for field in ('workers', 'backlog', 'header_bytes', 'body_bytes'):
            if type(getattr(self, field)) is not int or getattr(self, field) <= 0:
                raise ValueError('Invalid HTTPS limits')
        for field in ('handshake_seconds', 'header_seconds', 'body_seconds',
                      'write_seconds', 'shutdown_seconds'):
            value = getattr(self, field)
            if type(value) not in (float, int) or not 0 < value < float('inf'):
                raise ValueError('Invalid HTTPS limits')


class HTTPInputError(Exception):
    def __init__(self, status):
        self.status = status


@dataclass(eq=False)
class Connection:
    sock: socket.socket
    address: tuple
    phase: str = 'handshake'
    deadline: float = 0
    timed_out: bool = False
    transport_error: bool = False
    request_started: float | None = None
    status: int | None = None


class DeadlineInput(io.RawIOBase):
    def __init__(self, server, connection):
        self.server, self.connection = server, connection
        self.received = 0

    def readable(self):
        return True

    def readinto(self, buffer):
        state = self.connection
        state.sock.settimeout(self.server.remaining(state, state.deadline))
        try:
            count = state.sock.recv_into(buffer)
        except TimeoutError:
            self.server.timeout(state, state.phase)
            raise
        self.received += count
        # Includes chunk framing; tiny chunks cannot create unbounded overhead.
        if self.received > self.server.limits.header_bytes + 2 * self.server.limits.body_bytes:
            raise HTTPInputError(413)
        return count


class HeaderInput(io.BufferedReader):
    def __init__(self, raw, maximum):
        super().__init__(raw)
        self.header_remaining = maximum
        self.header_lines = 0

    def readline(self, size=-1):
        if self.raw.connection.phase != 'headers':
            return super().readline(size)
        maximum = self.header_remaining + 1
        result = super().readline(min(size, maximum) if size >= 0 else maximum)
        self.header_remaining -= len(result)
        if self.header_remaining < 0:
            raise HTTPInputError(431)
        if not result and self.header_lines == 0:
            return result  # Peer closed before starting a request.
        self.header_lines += 1
        if not result.endswith(b'\r\n'):
            # http.client accepts EOF as a header terminator and bare LF as a
            # line ending. Neither may turn an incomplete request into WSGI.
            raise HTTPInputError(400)
        return result


class DeadlineOutput(io.BufferedIOBase):
    def __init__(self, server, connection):
        self.server, self.connection = server, connection
        self.deadline = None

    def writable(self):
        return True

    def write(self, value):
        if self.deadline is None:
            self.deadline = time.monotonic() + self.server.limits.write_seconds
        state = self.connection
        try:
            # SSLSocket.sendall in Python 3.12 loops over partial send() calls
            # with the same socket timeout. Recompute our absolute deadline at
            # every partial send instead, including across different writes.
            with memoryview(value).cast('B') as view:
                sent = 0
                while sent < len(view):
                    state.sock.settimeout(self.server.remaining(state, self.deadline, 'write'))
                    count = state.sock.send(view[sent:sent + 65536])
                    if count <= 0:
                        raise ConnectionError('Closed HTTP output')
                    sent += count
        except TimeoutError:
            self.server.timeout(state, 'write')
            raise
        except OSError:
            self.server.transport_error(state, 'write')
            raise
        return len(value)


class _ChunkStream:
    """Keep Werkzeug's decoder, but require CRLF on all chunk framing lines."""
    def __init__(self, stream):
        self.stream = stream

    def read(self, size):
        return self.stream.read(size)

    def readline(self, size):
        line = self.stream.readline(size)
        if not line.endswith(b'\r\n'):
            raise HTTPInputError(400)
        return line


class StrictChunkedInput(DechunkedInput):
    def __init__(self, stream):
        super().__init__(_ChunkStream(stream))

    def read_chunk_len(self):
        line = self._rfile.readline(100)
        if not re.fullmatch(b'[0-9a-fA-F]+\r\n', line):
            raise HTTPInputError(400)
        return int(line[:-2], 16)


class _ClosingIterable:
    def __init__(self, iterable):
        self.iterable, self.closed = iterable, False

    def __iter__(self):
        return iter(self.iterable)

    def close(self):
        if not self.closed:
            self.closed = True
            if hasattr(self.iterable, 'close'):
                self.iterable.close()


class _RequestServer:
    """Per-handler view: track WSGI cleanup without mutating the shared app."""
    def __init__(self, server):
        self.server, self.response = server, None

    def __getattr__(self, name):
        return getattr(self.server, name)

    def app(self, environ, start_response):
        self.response = _ClosingIterable(self.server.app(environ, start_response))
        return self.response

    def close_response(self):
        if self.response is not None:
            self.response.close()


class RequestHandler(WSGIRequestHandler):
    protocol_version = 'HTTP/1.1'

    def setup(self):
        self.connection = self.request
        self.state = self.server.connection_for(self.request)
        self.rfile = HeaderInput(DeadlineInput(self.server, self.state), self.server.limits.header_bytes)
        self.wfile = DeadlineOutput(self.server, self.state)

    def handle(self):
        self.state.phase = 'headers'
        self.state.request_started = time.monotonic()
        self.state.deadline = time.monotonic() + self.server.limits.header_seconds
        self.request_version, self.command, self.requestline = 'HTTP/1.0', None, ''
        try:
            # Exactly one request, even when the client asks for keep-alive.
            self.handle_one_request()
        except HTTPInputError as error:
            self.send_error(error.status)
        except (TimeoutError, ConnectionError, ssl.SSLError, OSError):
            self.connection_dropped(None)
        finally:
            self.close_connection = True

    def handle_expect_100(self):
        # Validate framing and size before inviting the client to send the body.
        return True

    def parse_request(self):
        if not super().parse_request():
            return False
        hosts = self.headers.get_all('Host', [])
        if (self.request_version not in ('HTTP/1.0', 'HTTP/1.1')
                or self.headers.defects or len(hosts) > 1
                or (self.request_version == 'HTTP/1.1' and (len(hosts) != 1 or not hosts[0].strip()))
                or any(not re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+", key)
                       or any((ord(c) < 32 and c != '\t') or ord(c) == 127 for c in value)
                       for key, value in self.headers.items())):
            self.send_error(400)
            return False
        lengths = self.headers.get_all('Content-Length', [])
        transfers = self.headers.get_all('Transfer-Encoding', [])
        self.chunked = bool(transfers)
        if (len(lengths) > 1 or len(transfers) > 1 or (lengths and transfers)
                or (transfers and self.request_version != 'HTTP/1.1')
                or (transfers and transfers[0].lower().strip() != 'chunked')
                or (lengths and not re.fullmatch('[0-9]{1,10}', lengths[0]))):
            self.send_error(400)
            return False
        self.body_length = int(lengths[0]) if lengths else 0
        if self.body_length > self.server.limits.body_bytes:
            self.send_error(413)
            return False
        if (len(self.headers.get_all('Expect', [])) > 1
                or self.headers.get('Expect', '').lower() not in ('', '100-continue')):
            self.send_error(417)
            return False
        return True

    def run_wsgi(self):
        if self.headers.get('Expect', '').lower() == '100-continue':
            self.wfile.write(b'HTTP/1.1 100 Continue\r\n\r\n')
            self.wfile.deadline = None
            del self.headers['Expect']
        self.state.phase = 'body'
        self.state.deadline = time.monotonic() + self.server.limits.body_seconds
        if self.chunked:
            body = StrictChunkedInput(self.rfile).read(self.server.limits.body_bytes + 1)
            if len(body) > self.server.limits.body_bytes:
                raise HTTPInputError(413)
        else:
            body = self.rfile.read(self.body_length)
            if len(body) != self.body_length:
                raise ConnectionError('Incomplete HTTP body')
        network_input = self.rfile
        server = self.server
        scope = _RequestServer(server)
        try:
            # Werkzeug's final input drain now sees memory, never a client socket.
            self.rfile = io.BytesIO(body)
            self.body = body
            self.state.phase = 'application'
            self.server = scope
            super().run_wsgi()
        finally:
            self.rfile.close()
            self.rfile = network_input
            self.server = server
            # Werkzeug's own finally may fail while registering a socket
            # already closed by shutdown, before it can close the iterable.
            scope.close_response()

    def make_environ(self):
        environ = super().make_environ()
        environ['wsgi.input'] = io.BytesIO(self.body)
        if self.chunked:
            environ.pop('HTTP_TRANSFER_ENCODING', None)
            environ['CONTENT_LENGTH'] = str(len(self.body))
            environ['wsgi.input_terminated'] = True
        return environ

    def log_request(self, code='-', size='-'):
        self.state.status = code if isinstance(code, int) else None

    def log_message(self, format, *args):
        # Never log request lines, headers, paths, exception messages or bodies.
        pass

    def connection_dropped(self, error, environ=None):
        self.server.transport_error(self.state)


class DevHTTPSServer(BaseWSGIServer):
    multithread = True

    def __init__(self, host, port, app, context, limits=None):
        self.limits = limits or Limits()
        self.request_queue_size = self.limits.backlog
        self._lock = Lock()
        self._connections = set()
        self._queue = Queue(maxsize=self.limits.workers)
        self._stopping = Event()
        self._stop_requested = False
        self.on_shutdown = None
        self._threads = []
        self._closed = False
        self.shutdown_clean = None
        self._counts = dict(accepted=0, rejected=0, completed=0, peak_active=0,
                            handshake_errors=0, transport_errors=0, timeouts=0)
        self._timeouts = {}
        # Deliberately leave the listener as TCP; TLS belongs to a fixed worker.
        super().__init__(host, port, app, handler=RequestHandler, ssl_context=None)
        self.ssl_context = context
        self.socket.setblocking(False)

    def event(self, name, **fields):
        LOG.info(json.dumps(dict(event=name, **fields), sort_keys=True))

    def snapshot(self):
        with self._lock:
            return dict(self._counts, active=len(self._connections),
                        timeouts_by_phase=dict(self._timeouts))

    def remaining(self, state, deadline, phase=None):
        left = deadline - time.monotonic()
        if left <= 0:
            self.timeout(state, phase or state.phase)
            raise TimeoutError()
        return left

    def timeout(self, state, phase):
        with self._lock:
            if state.timed_out:
                return
            state.timed_out = True
            self._counts['timeouts'] += 1
            self._timeouts[phase] = self._timeouts.get(phase, 0) + 1
        self.event('timeout', phase=phase)

    def transport_error(self, state, phase=None):
        with self._lock:
            if state.timed_out or state.transport_error or self._stopping.is_set():
                return
            state.transport_error = True
            self._counts['transport_errors'] += 1
        self.event('transport_error', phase=phase or state.phase)

    def connection_for(self, sock):
        with self._lock:
            return next(state for state in self._connections if state.sock is sock)

    def process_request(self, request, client_address):
        with self._lock:
            self._counts['accepted'] += 1
            reject = self._stop_requested or self._stopping.is_set() or len(self._connections) >= self.limits.workers
            if reject:
                self._counts['rejected'] += 1
            else:
                state = Connection(request, client_address,
                                   deadline=time.monotonic() + self.limits.handshake_seconds)
                self._connections.add(state)
                self._counts['peak_active'] = max(self._counts['peak_active'], len(self._connections))
                self._queue.put_nowait(state)
        if reject:
            request.close()
            self.event('connection_rejected', **self.snapshot())

    def _worker(self):
        while not self._stopping.is_set() or not self._queue.empty():
            try:
                state = self._queue.get(timeout=.1)
            except Empty:
                continue
            try:
                with self._lock:
                    if self._stop_requested or self._stopping.is_set():
                        continue
                    # No handshake here; atomic ownership transfer for shutdown.
                    state.sock = self.ssl_context.wrap_socket(state.sock, server_side=True,
                                                               do_handshake_on_connect=False)
                state.sock.settimeout(self.remaining(state, state.deadline))
                state.sock.do_handshake()
                self.finish_request(state.sock, state.address)
            except TimeoutError:
                self.timeout(state, state.phase)
            except (OSError, ssl.SSLError):
                if state.phase == 'handshake' and not self._stopping.is_set():
                    with self._lock:
                        self._counts['handshake_errors'] += 1
                    self.event('handshake_error', phase='handshake')
                else:
                    self.transport_error(state)
            except Exception:
                self.event('handler_error', phase=state.phase)
            finally:
                self._close_socket(state.sock)
                with self._lock:
                    self._connections.remove(state)
                    self._counts['completed'] += 1
                if state.request_started is not None:
                    self.event('request_finished', status=state.status,
                               duration_ms=round(1000 * (time.monotonic() - state.request_started), 2))
                self.event('connection_closed', **self.snapshot())
                self._queue.task_done()

    @staticmethod
    def _close_socket(sock):
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        finally:
            sock.close()

    def log(self, type, message, *args):
        # Werkzeug may supply request URLs or exception text. Discard both.
        self.event('wsgi_error')

    def serve_forever(self, poll_interval=.1):
        try:
            for index in range(self.limits.workers):
                thread = Thread(target=self._worker, name=f'livenet-https-{index}', daemon=True)
                thread.start()
                self._threads.append(thread)
            self.event('server_started', workers=self.limits.workers, backlog=self.limits.backlog)
            with selectors.DefaultSelector() as selector:
                selector.register(self.socket, selectors.EVENT_READ)
                while not self._stop_requested:
                    if selector.select(poll_interval) and not self._stop_requested:
                        self._handle_request_noblock()
        finally:
            try:
                if self.on_shutdown is not None:
                    self.on_shutdown()
            finally:
                self.server_close()

    def shutdown(self):
        # May also be called by a signal handler in the serving thread.
        # Python signal handlers may interrupt this thread while it owns an
        # Event/queue/registry lock. A plain flag must be the only operation.
        self._stop_requested = True

    def server_close(self):
        # BaseWSGIServer may call this during construction after a bind failure.
        if self._closed:
            return
        self._closed = True
        self._stop_requested = True
        self._stopping.set()
        self.event('server_stopping')
        super().server_close()
        with self._lock:
            for state in self._connections:
                self._close_socket(state.sock)
        deadline = time.monotonic() + self.limits.shutdown_seconds
        for thread in self._threads:
            if thread is not current_thread():
                thread.join(max(0, deadline - time.monotonic()))
        self.shutdown_clean = not any(t.is_alive() for t in self._threads)
        self.event('server_stopped', clean=self.shutdown_clean, **self.snapshot())


def run_dev_https(host, port, app_factory, certificate, key):
    """Bind first, build exactly one app, then serve without subprocess/reloader."""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(certificate, key)
    server = DevHTTPSServer(host, port, None, context)
    previous = {}
    app = None
    worker_clean = True

    def stop_worker():
        worker = app.extensions.get('discovery', {}).get('worker') if app is not None else None
        if worker is not None:
            worker.stop.set()
            if worker.current_cancel is not None:
                worker.current_cancel.set()
        return worker

    def stop(*_):
        server.shutdown()

    try:
        app = app_factory()
        server.app = app
        server.on_shutdown = stop_worker
        if current_thread() is main_thread():
            for number in (signal.SIGINT, signal.SIGTERM):
                previous[number] = signal.signal(number, stop)
        server.serve_forever()
    finally:
        # Signal only the worker belonging to this app; never create/restart one.
        worker = stop_worker()
        server.server_close()
        if worker is not None:
            if worker.thread is not None:
                worker.thread.join(server.limits.shutdown_seconds)
                worker_clean = not worker.thread.is_alive()
                server.event('discovery_shutdown', clean=worker_clean)
        for number, handler in previous.items():
            signal.signal(number, handler)
    if server.shutdown_clean is False or not worker_clean:
        raise Refused('HTTPS_SHUTDOWN_INCOMPLETE')
