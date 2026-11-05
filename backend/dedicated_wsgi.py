"""DEV-02 explicit Gunicorn factory; importing this module creates no app.

Only an absolute, owner-private JSON file supplied as a factory argument is read.
No environment discovery, database fallback or readiness checker is installed.
"""

import json
import os
from pathlib import Path
import stat

from app.dedicated import ConfigurationError, create_dedicated_app


_MAX_CONFIG_BYTES = 16384
_REQUIRED_KEYS = frozenset({
    "ENVIRONMENT", "DATABASE_HOST", "DATABASE_PORT", "DATABASE_NAME",
    "DATABASE_USER", "DATABASE_PASSWORD_FILE", "SECURITY_ENABLED",
    "SECURITY_CSRF_KEY_FILE", "SECURITY_HTTPS_ORIGIN", "PROXY_ENABLED", "PROXY_PEERS",
})


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError()
        result[key] = value
    return result


def _constant(value):
    raise ValueError()


def _load_config(config_path, *, required_keys=_REQUIRED_KEYS):
    descriptor = None
    try:
        if type(config_path) is not str or not Path(config_path).is_absolute():
            raise ValueError()
        descriptor = os.open(config_path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        info = os.fstat(descriptor)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) & 0o077
                or info.st_size > _MAX_CONFIG_BYTES):
            raise ValueError()
        raw = os.read(descriptor, _MAX_CONFIG_BYTES + 1)
        if len(raw) > _MAX_CONFIG_BYTES:
            raise ValueError()
        values = json.loads(raw.decode("utf-8"), object_pairs_hook=_object,
                            parse_constant=_constant)
        if (type(values) is not dict or set(values) != required_keys
                or values["SECURITY_ENABLED"] is not True
                or values["PROXY_ENABLED"] is not True):
            raise ValueError()
        return values
    except (OSError, ValueError, TypeError, UnicodeError, RecursionError):
        pass
    finally:
        if descriptor is not None:
            os.close(descriptor)
    # Outside the handler: parser/path diagnostics must not survive as context.
    raise ConfigurationError()


def create_app(config_path):
    """Build the secure dedicated app, without connecting or making it ready.

    Gunicorn target: dedicated_wsgi:create_app('/absolute/private/config.json').
    Configuration contents and secret paths must never be printed or logged.
    """
    return create_dedicated_app(_load_config(config_path))


def create_tls_app(config_path):
    """Explicit TLS entrypoint; preserves create_app and never supplies a checker.

    Gunicorn target: dedicated_wsgi:create_tls_app('/run/livenet/backend.json').
    The two extra JSON keys are mandatory; there is no environment CA fallback.
    """
    from app.postgres_tls import InvalidTLS, PostgresTLS
    tls_keys = frozenset({'DATABASE_SSLMODE','DATABASE_SSLROOTCERT_FILE'})
    values = _load_config(config_path, required_keys=_REQUIRED_KEYS | tls_keys)
    try:
        tls = PostgresTLS.from_mapping({key: values.pop(key) for key in tls_keys})
        return create_dedicated_app(values, database_tls=tls)
    except InvalidTLS:
        pass
    raise ConfigurationError()
