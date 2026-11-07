"""Shared pure input/logging checks for DEV09B inspection and the query trial.

No connection creation, SQL, authority or import-time inspection. Missing logging
API refuses; host literals never admit networks or IPv6 zone identifiers.
"""
from collections.abc import Mapping
from ipaddress import ip_address
import logging

from sqlalchemy.engine import Row


class InspectionInputError(ValueError):
    def __init__(self,code):
        self.code=code
        super().__init__(code)


def row_mapping(item):
    if isinstance(item,Row):item=item._mapping
    if not isinstance(item,Mapping):raise InspectionInputError('MALFORMED_ROW')
    return dict(item)


def host_address(value):
    if type(value) is not str or '/' in value or '%' in value:
        raise InspectionInputError('IDENTITY_ADDRESS_INVALID')
    try:return ip_address(value)
    except ValueError as exc:raise InspectionInputError('IDENTITY_ADDRESS_INVALID') from exc


def check_client_logging(connection):
    # SQLAlchemy 2.1 Connection caches Engine._should_log_info() in _echo;
    # the Engine logger may have changed since the connection was created.
    try:
        engine=connection.engine
        safe=((engine.echo is False or engine.echo is None)
              and engine.hide_parameters is True and connection._echo is False
              and logging.getLogger('sqlalchemy.engine').isEnabledFor(logging.INFO) is False
              and engine.logger.isEnabledFor(logging.INFO) is False
              and engine.logger.isEnabledFor(logging.DEBUG) is False)
    except (AttributeError,TypeError):raise InspectionInputError('CLIENT_LOGGING_REFUSED') from None
    if not safe:raise InspectionInputError('CLIENT_LOGGING_REFUSED')


# Ten GUCs plus two fixed database locale attributes, same twelve requirements.
SETTINGS_NAMES = (
    'search_path','session_replication_role','row_security','standard_conforming_strings',
    'shared_preload_libraries','session_preload_libraries','local_preload_libraries',
    'server_encoding','lc_collate','lc_ctype','transaction_isolation','transaction_read_only',
)


def settings_inventory(values):
    """Closed nominal coverage; NULL is unavailable, never an empty setting.

    Hidden superuser-only GUCs require a separately authorized trusted source.
    This helper never substitutes expected values or grants pg_read_all_settings.
    """
    if type(values) is not list:raise InspectionInputError('SETTINGS_COVERAGE_INCOMPLETE')
    result={}
    for row in values:
        if type(row) is not dict or set(row)!={'name','setting'}:
            raise InspectionInputError('SETTINGS_ROW_INVALID')
        name=row['name']
        if type(name) is not str or name not in SETTINGS_NAMES:
            raise InspectionInputError('SETTINGS_COVERAGE_INCOMPLETE')
        if name in result:raise InspectionInputError('SETTINGS_DUPLICATE')
        result[name]=row['setting']
    if set(result)!=set(SETTINGS_NAMES):raise InspectionInputError('SETTINGS_COVERAGE_INCOMPLETE')
    unavailable=tuple(name for name in SETTINGS_NAMES if result[name] is None)
    if unavailable:
        error=InspectionInputError('SETTINGS_VALUE_UNAVAILABLE')
        error.names=unavailable  # Only names from the closed whitelist, no values.
        raise error
    if not all(type(v) is str for v in result.values()):
        raise InspectionInputError('SETTINGS_VALUE_INVALID')
    return result
