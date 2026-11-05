"""Bounded offline orchestration; the real PostgreSQL executor is disabled.

Dependency injection is trusted Python, not a sandbox against malicious callbacks.
No driver is imported and no connection factory is supplied by this package.
"""
from contextlib import contextmanager
from dataclasses import dataclass, field
from threading import Lock
from time import monotonic
from types import MappingProxyType

from .evaluate import evaluate
from .policy import Limits, Policy, Unavailable, canonical, normalize
from .queries import CATALOG


@dataclass(frozen=True)
class Batch:
    rows: tuple
    complete: bool = True


class DisabledPostgresExecutor:
    """No config flag, credentials, fallback, SQL execution or driver implementation."""
    def execute(self, *args, **kwargs):
        raise Unavailable()


class OfflineExecutor:
    """Static synthetic query results only; never operational evidence.

    Keys are (identity label, query name). This object performs no I/O.
    Connection doubles are supplied separately by the trusted test harness.
    """
    def __init__(self, batches):
        self._batches = MappingProxyType(dict(batches))

    def execute(self, connection, subject, query, parameters, *, timeout_ms, deadline):
        return self._batches[(subject, query.name)]


@dataclass
class _Scope:
    lock: object = field(default_factory=Lock)
    invalidated: bool = False


_scopes = {}
_scopes_lock = Lock()
ACL_QUERIES = frozenset({"Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8", "Q9", "Q10", "Q11", "Q12"})


class OfflineReadinessAdapter:
    """Callable checker for G2 tests. Never install this synthetic checker live.

    Factory contract: factory(target=tuple, connect_timeout=float,
    deadline=float) -> NEW connection double. begin() must enforce the supplied
    read-only/repeatable-read/options; rollback()/close() must be independent.
    Deadlines are checked before/after calls. A synchronous hostile callback
    cannot be forcibly interrupted: hard I/O/cancellation belongs to G4.
    """
    def __init__(self, policy, *, runtime_factory, verifier_factory,
                 executor=None, clock=monotonic, limits=Limits()):
        if type(policy) is not Policy or type(limits) is not Limits:
            raise Unavailable()
        self.policy = policy
        self._runtime_factory = runtime_factory
        self._verifier_factory = verifier_factory
        self._executor = executor if executor is not None else DisabledPostgresExecutor()
        self._clock = clock
        self._limits = limits
        key = (policy.target, policy.verifier_role, policy.approved_digest)
        with _scopes_lock:
            self._scope = _scopes.setdefault(key, _Scope())

    @contextmanager
    def _hold_scope(self):
        """Release once; a secondary lock fault must not replace the primary.

        A failed release leaves ownership uncertain. Invalidate this scope,
        without retrying or claiming the underlying lock was recovered.
        """
        if not self._scope.lock.acquire(blocking=False):
            raise Unavailable()
        primary = None
        try:
            yield
        except BaseException as exc:
            primary = exc
            raise
        finally:
            release_failure = None
            try:
                self._scope.lock.release()
            except BaseException as secondary:
                self._scope.invalidated = True
                release_failure = primary if primary is not None else (
                    Unavailable() if isinstance(secondary, Exception) else secondary)
                try:
                    BaseException.add_note(release_failure,
                        "Readiness lock release failed; lock state is unknown; scope invalidated.")
                except BaseException:
                    # Diagnostic metadata is best effort; preserve the primary.
                    pass
            if primary is None and release_failure is not None:
                # Outside the handler: ordinary lock details are not retained
                # as the sanitized exception's cause or context.
                raise release_failure

    def revalidate(self, approved_policy):
        """Explicit trusted revalidation request; never returns positive evidence.

        It clears the latch only for the same complete approved contract. All
        queries are still mandatory on the next call. No HTTP/config endpoint.
        A different approved policy requires a new adapter.
        """
        if type(approved_policy) is not Policy or approved_policy != self.policy:
            raise Unavailable()
        with self._hold_scope():
            self._scope.invalidated = False

    def __call__(self):
        # Must refuse BEFORE invoking arbitrary factories, including defaults.
        if type(self._executor) is not OfflineExecutor:
            raise Unavailable()
        with self._hold_scope():
            connections = []
            failed = False
            observation = None
            started = None
            interruption = None
            try:
                if self._scope.invalidated:
                    raise Unavailable()
                started = self._clock()
                deadline = started + self._limits.global_seconds
                last = started
                size = 0

                def budget():
                    nonlocal last
                    now = self._clock()
                    if type(now) not in (int, float) or not last <= now < deadline:
                        raise Unavailable()
                    last = now
                    return deadline - now

                for factory, role in ((self._runtime_factory, self.policy.target[3]),
                                      (self._verifier_factory, self.policy.verifier_role)):
                    target = (*self.policy.target[:3], role)
                    remaining = budget()
                    call_started = last
                    connect_limit = min(self._limits.connect_seconds, remaining)
                    conn = factory(target=target,
                        connect_timeout=connect_limit, deadline=deadline)
                    if conn is None or any(conn is old for old in connections):
                        raise Unavailable()
                    connections.append(conn)
                    budget()
                    if last - call_started >= connect_limit:
                        raise Unavailable()
                    conn.begin(read_only=True, isolation="REPEATABLE READ", search_path="pg_catalog",
                        statement_timeout_ms=self._limits.statement_ms,
                        lock_timeout_ms=self._limits.lock_ms,
                        idle_transaction_timeout_ms=self._limits.idle_transaction_ms,
                        deadline=deadline)
                    budget()

                def collect(subject, conn, name):
                    nonlocal size
                    remaining = budget()
                    query = CATALOG[name]
                    per_statement = (self._limits.heavy_statement_ms if query.statement_ms == 1000
                                     else self._limits.statement_ms)
                    params = MappingProxyType({"runtime_role": self.policy.target[3],
                                               "verifier_role": self.policy.verifier_role})
                    call_started = last
                    query_limit = min(per_statement, max(1, int(remaining * 1000)))
                    batch = self._executor.execute(conn, subject, query, params,
                        timeout_ms=query_limit, deadline=deadline)
                    budget()
                    if last - call_started >= query_limit / 1000:
                        raise Unavailable()
                    if type(batch) is not Batch or batch.complete is not True:
                        raise Unavailable()
                    rows = normalize(batch.rows, query.max_rows)
                    size += len(canonical(rows).encode())
                    if size > self._limits.max_bytes:
                        raise Unavailable()
                    if name in ACL_QUERIES and canonical(rows) != canonical(dict(self.policy.manifest)[name]):
                        self._scope.invalidated = True
                        raise Unavailable()
                    return rows

                runtime_identity = collect("runtime", connections[0], "Q1")
                verifier_identity = collect("verifier", connections[1], "Q1")
                data = {f"Q{i}": collect("verifier", connections[1], f"Q{i}") for i in range(2, 17)}
                observation = evaluate(self.policy, data, runtime_identity, verifier_identity, started)
                budget()
            except Exception:
                failed = True
            except BaseException as exc:
                # Preserve cancellation; catch only to finish independent cleanup.
                interruption = exc
            finally:
                # Every resource gets independent cleanup attempts, even after errors.
                for conn in reversed(connections):
                    for method in ("rollback", "close"):
                        try:
                            getattr(conn, method)()
                        except Exception:
                            failed = True
                        except BaseException as exc:
                            if interruption is None:
                                interruption = exc
                try:
                    if started is not None:
                        ended = self._clock()
                        if type(ended) not in (int, float) or not started <= ended < started + self._limits.global_seconds:
                            failed = True
                except Exception:
                    failed = True
                except BaseException as exc:
                    if interruption is None:
                        interruption = exc
            if interruption is not None:
                raise interruption
            if failed or observation is None:
                # Outside exception handlers: don't retain a sensitive driver cause.
                raise Unavailable()
            return observation
