"""SELECT-only DEV09B trial, never a migration or operational approval.

Caller hands over exclusive ownership of an idle SQLAlchemy Connection with
client/driver tracing disabled, echo=False and hide_parameters=True. This module
never creates an engine/connection, accepts a DSN/password, or retries. The
connection is rolled back and closed on every path, including invalid inputs.
A cleanup method returning is a client observation, not independent recovery
confirmation. No server, network or filesystem access happens on import.
"""
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import re
from time import monotonic

from sqlalchemy import text
from backend.migrations.dev09b_inspection_queries import QUERIES
from backend.migrations import dev09b_inspection_support as support

# Fixed catalog: HOST() identity plus twelve named settings from GUC/database sources.
CATALOG_SHA256 = '5739c8347f97d77348baea592f659410feb6cd898605477a37347c4c39ce0d9c'
CONTROL_SQL = """SELECT pg_catalog.current_setting('transaction_read_only') AS read_only,
 pg_catalog.current_setting('transaction_isolation') AS isolation,
 (SELECT setting::pg_catalog.int4 FROM pg_catalog.pg_settings WHERE name='statement_timeout') AS statement_ms,
 (SELECT setting::pg_catalog.int4 FROM pg_catalog.pg_settings WHERE name='lock_timeout') AS lock_ms,
 (SELECT setting::pg_catalog.int4 FROM pg_catalog.pg_settings WHERE name='idle_in_transaction_session_timeout') AS idle_ms,
 pg_catalog.current_setting('search_path') AS search_path"""


@dataclass(frozen=True)
class TrialTarget:
    database: str
    system_identifier: str
    user: str
    address: str
    port: int = 5432


@dataclass(frozen=True)
class TrialLimits:
    statement_ms: int = 3000
    lock_ms: int = 500
    idle_ms: int = 10000
    deadline_ms: int = 60000
    max_row_bytes: int = 262144
    max_query_bytes: int = 16777216
    max_total_bytes: int = 67108864
    max_total_rows: int = 262144


@dataclass(frozen=True)
class QueryOutcome:
    name: str
    status: str
    rows: int | None  # Observed rows; REFUSED may be a partial count.
    reason: str | None = None


@dataclass(frozen=True)
class TrialReport:
    scope: str
    status: str
    queries: tuple
    identity_after: QueryOutcome | None
    rollback: str
    close: str
    reason: str | None
    diagnostics: tuple = ()

    def to_json(self):
        # Only fixed labels, counts and statuses; no rows, exceptions or bindings.
        return json.dumps(asdict(self), sort_keys=True, separators=(',', ':'))


_REASONS = frozenset('INVALID_CONFIGURATION INVALID_LIMITS CATALOG_CHANGED IDENTITY_REFUSED CONNECTION_REFUSED CLIENT_LOGGING_REFUSED TRANSACTION_ALREADY_ACTIVE TRANSACTION_CHANGED DEADLINE ROW_LIMIT MALFORMED_ROW BYTE_LIMIT READ_ONLY_OR_TIMEOUT_REFUSED IDENTITY_CHANGED IDENTITY_ADDRESS_INVALID'.split())


class _Refused(Exception):
    pass


def _require(condition, code):
    if not condition:raise _Refused(code)


def _row_dict(item):
    try:return support.row_mapping(item)
    except support.InspectionInputError as exc:raise _Refused(exc.code) from None


def _host_address(value,code):
    try:return support.host_address(value)
    except support.InspectionInputError as exc:raise _Refused(code) from exc.__cause__


def _safe_diagnostic(phase,reason,exc):
    specific={'row_mapping':'ROW_MAPPING_ERROR','row_serialization':'ROW_SERIALIZATION_ERROR',
              'identity_binding':'IDENTITY_PROCESSING_ERROR','query_execute':'QUERY_EXECUTION_ERROR',
              'query_stream':'QUERY_STREAM_ERROR'}
    original=exc.__cause__ if type(exc) is _Refused and exc.__cause__ is not None else exc
    allowed={'ValueError','TypeError','KeyError','AttributeError','OverflowError','RuntimeError',
             'ProgrammingError','OperationalError','InterfaceError','DataError','IntegrityError',
             'TimeoutError','StatementError','InvalidRequestError'}
    cls='Refused' if type(original) is _Refused else type(original).__name__
    if cls not in allowed and cls!='Refused':cls='Exception'
    return dict(phase=phase,code=reason if reason!='QUERY_OR_SETUP_ERROR' else specific.get(phase,'SETUP_PROCESSING_ERROR'),exception_class=cls)


def _configuration(target, limits):
    _require(type(target) is TrialTarget and type(limits) is TrialLimits, 'INVALID_CONFIGURATION')
    _require(target.database == 'livenet_v2_dev', 'INVALID_CONFIGURATION')
    _require(type(target.system_identifier) is str and re.fullmatch(r'[1-9][0-9]{0,19}',target.system_identifier)
             and int(target.system_identifier) <= 2**64-1, 'INVALID_CONFIGURATION')
    _require(type(target.user) is str and re.fullmatch(r'[a-z_][a-z0-9_]{0,62}',target.user), 'INVALID_CONFIGURATION')
    _require(type(target.address) is str, 'INVALID_CONFIGURATION')
    _host_address(target.address,'INVALID_CONFIGURATION')  # No DNS or networks.
    _require(type(target.port) is int and 1 <= target.port <= 65535, 'INVALID_CONFIGURATION')
    bounds = dict(statement_ms=10000,lock_ms=1000,idle_ms=30000,deadline_ms=120000,
                  max_row_bytes=262144,max_query_bytes=16777216,max_total_bytes=67108864,max_total_rows=262144)
    for k,maximum in bounds.items():
        _require(type(getattr(limits,k)) is int and 0 < getattr(limits,k) <= maximum, 'INVALID_LIMITS')
    _require(limits.lock_ms <= limits.statement_ms < limits.idle_ms and limits.statement_ms <= limits.deadline_ms, 'INVALID_LIMITS')
    inventory = {k:dict(sql=q.sql,fields=list(q.fields),maximum=q.maximum) for k,q in QUERIES.items()}
    _require(len(QUERIES)==33 and next(iter(QUERIES))=='identity' and sha256(json.dumps(inventory,sort_keys=True,separators=(',',':')).encode()).hexdigest()==CATALOG_SHA256,
             'CATALOG_CHANGED')


def _binding(row, target):
    for k in ('pid','port','server_version_num'):
        _require(type(row[k]) is int and row[k] > 0, 'IDENTITY_REFUSED')
    for k in ('backend_start','xact_start','virtualxid'):
        _require(type(row[k]) is str and bool(row[k]), 'IDENTITY_REFUSED')
    _require((row['database'],row['system_identifier'],row['current_user'],row['session_user']) ==
             (target.database,target.system_identifier,target.user,target.user), 'IDENTITY_REFUSED')
    actual=_host_address(row['address'],'IDENTITY_ADDRESS_INVALID')
    expected=_host_address(target.address,'INVALID_CONFIGURATION')
    _require(actual==expected
             and row['port']==target.port and 160000 <= row['server_version_num'] < 170000, 'IDENTITY_REFUSED')


def _check_client_logging(connection):
    try:support.check_client_logging(connection)
    except support.InspectionInputError as exc:raise _Refused(exc.code) from None


def run_trial(connection, target, limits=TrialLimits(), *, clock=monotonic):
    """Run only when separately authorized. Returns a sanitized diagnostic report.

    33 distinct catalog queries; identity runs again at the end. The extra setup
    SELECT verifies READ ONLY/timeouts. No ledger SELECT, DDL or Alembic path.
    Existing transactions are refused; the handed-over connection is still closed.
    """
    outcomes = {name:QueryOutcome(name,'NOT_RUN',None) for name in QUERIES}
    after = None
    reason = None
    rollback = close = 'NOT_ATTEMPTED'
    current = None
    tx = None
    total_rows = total_bytes = 0
    last_count = 0
    phase='configuration'
    diagnostics=[]
    try:
        _configuration(target,limits)
        _require(connection is not None and connection.closed is False and connection.dialect.name=='postgresql', 'CONNECTION_REFUSED')
        phase='client_logging'
        _check_client_logging(connection)
        _require(connection.in_transaction() is False, 'TRANSACTION_ALREADY_ACTIVE')
        start = clock()
        phase='transaction_begin'
        tx = connection.begin()

        def bound():
            _require(connection.closed is False and connection.get_transaction() is tx and tx.is_active is True, 'TRANSACTION_CHANGED')
            remaining = limits.deadline_ms - int((clock()-start)*1000)
            _require(remaining > 0, 'DEADLINE')
            return remaining

        def control(sql):
            nonlocal phase
            phase='transaction_control'
            bound()
            result = connection.execute(text(sql))
            result.close()

        # Fixed control statements; only validated bounded integers interpolate.
        control('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
        control(f'SET LOCAL statement_timeout = {limits.statement_ms}')
        control(f'SET LOCAL lock_timeout = {limits.lock_ms}')
        control(f'SET LOCAL idle_in_transaction_session_timeout = {limits.idle_ms}')
        control('SET LOCAL search_path = pg_catalog, public')

        def collect(sql, fields, maximum, capture=False):
            nonlocal total_rows,total_bytes,last_count,phase
            last_count = 0
            remaining = bound()
            control(f'SET LOCAL statement_timeout = {min(limits.statement_ms,remaining)}')
            count = size = 0
            captured = None
            phase='query_execute'
            result = connection.execute(text(sql), execution_options={'stream_results':True,'max_row_buffer':128})
            try:
                phase='query_stream'
                for item in result.mappings():
                    bound()
                    phase='row_mapping'
                    row = _row_dict(item)
                    count += 1
                    last_count = count
                    total_rows += 1
                    _require(count <= maximum and total_rows <= limits.max_total_rows, 'ROW_LIMIT')
                    _require(set(row)==set(fields), 'MALFORMED_ROW')
                    phase='row_serialization'
                    raw = json.dumps(row,ensure_ascii=True,allow_nan=False,separators=(',',':')).encode()
                    size += len(raw)
                    total_bytes += len(raw)
                    _require(len(raw)<=limits.max_row_bytes and size<=limits.max_query_bytes
                             and total_bytes<=limits.max_total_bytes, 'BYTE_LIMIT')
                    if capture:captured = row
                    phase='query_stream'
                bound()
            finally:
                result.close()
            return count,captured

        # The remaining per-query timeout is adjusted before each SELECT.
        # Compare control settings against that adjusted value too.
        control_statement_ms = min(limits.statement_ms,bound())
        count,settings = collect(CONTROL_SQL,('read_only','isolation','statement_ms','lock_ms','idle_ms','search_path'),1,True)
        phase='settings_validation'
        _require(count==1 and settings['read_only']=='on' and settings['isolation']=='repeatable read'
                 and type(settings['statement_ms']) is int and 0 < settings['statement_ms'] <= control_statement_ms
                 and type(settings['lock_ms']) is int and settings['lock_ms']==limits.lock_ms
                 and type(settings['idle_ms']) is int and settings['idle_ms']==limits.idle_ms
                 and settings['search_path']=='pg_catalog, public', 'READ_ONLY_OR_TIMEOUT_REFUSED')
        first = None
        for name,q in QUERIES.items():
            current = name
            count,row = collect(q.sql,q.fields,q.maximum,name=='identity')
            if name=='identity':
                _require(count==1, 'IDENTITY_REFUSED')
                phase='identity_binding'
                _binding(row,target)
                first = row
            outcomes[name] = QueryOutcome(name,'SUCCESS',count)
            current = None
        current = 'identity_after'
        q = QUERIES['identity']
        count,last = collect(q.sql,q.fields,q.maximum,True)
        _require(count==1 and last==first and all(type(last[k]) is type(first[k]) for k in first), 'IDENTITY_CHANGED')
        phase='identity_binding'
        _binding(last,target)
        after = QueryOutcome('identity_after','SUCCESS',count)
        current = None
    except Exception as exc:
        # Never preserve arbitrary exception text, repr, SQLSTATE/driver details,
        # connection/target repr or query rows in the returned diagnostic report.
        reason = exc.args[0] if type(exc) is _Refused and exc.args and type(exc.args[0]) is str and exc.args[0] in _REASONS else 'QUERY_OR_SETUP_ERROR'
        diagnostics.append(_safe_diagnostic(phase,reason,exc))
        if current=='identity_after':after = QueryOutcome(current,'REFUSED',last_count,reason)
        elif current is not None:outcomes[current] = QueryOutcome(current,'REFUSED',last_count,reason)
    finally:
        try:
            connection.rollback()
            rollback = 'RETURNED'
        except Exception as exc:
            rollback = 'FAILED'
            diagnostics.append(_safe_diagnostic('rollback','CLEANUP_FAILED',exc))
        finally:
            try:
                connection.close()
                close = 'RETURNED'
            except Exception as exc:
                close = 'FAILED'
                diagnostics.append(_safe_diagnostic('close','CLEANUP_FAILED',exc))
    if rollback!='RETURNED' or close!='RETURNED':reason = reason or 'CLEANUP_FAILED'
    return TrialReport('QUERY_TRIAL_ONLY', 'COMPLETED' if reason is None else 'REFUSED',
                       tuple(outcomes.values()),after,rollback,close,reason,tuple(diagnostics))
