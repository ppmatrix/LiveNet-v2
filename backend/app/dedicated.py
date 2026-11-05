"""Explicit, opt-in factory for a FUTURE dedicated backend; not used by wsgi.py.

No environment-variable discovery, application-database fallback, startup SQL or
account provisioning. Constructing the app does not create an engine/connection.
"""

import os
import re
import stat
from dataclasses import dataclass, field
from ipaddress import ip_address
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import URL

from app import create_app
from app.core.database import create_session_factory
from app.inventory.routes import InventoryDependencies
from app.readiness import install_readiness
from app.security.policy import SecurityPolicy
from app.trusted_proxy import TrustedProxy


class ConfigurationError(ValueError):
    def __init__(self):
        super().__init__("Invalid dedicated backend configuration")


def _database_host(value):
    """One ASCII DNS hostname or unscoped, unbracketed IP; never libpq lists."""
    if (not isinstance(value, str) or not value or not value.isascii()
            or any(ord(c) <= 32 or ord(c) == 127 for c in value)
            or any(c in value for c in ",%[]/@?#=\\\"'")):
        raise ValueError()
    try:
        address = ip_address(value)
    except ValueError:
        pass
    else:
        effective = getattr(address, "ipv4_mapped", None) or address
        if effective.is_unspecified or effective.is_multicast:
            raise ValueError()
        return str(address)
    # Numeric/hex components can be interpreted as legacy IPv4 by resolvers.
    # Reject instead of silently treating an invalid/abbreviated IP as DNS.
    name = value[:-1] if value.endswith(".") else value
    if all(re.fullmatch(r"(?:[0-9]+|0[xX][0-9a-fA-F]+)", p)
           for p in name.split(".")):
        raise ValueError()
    if not name or len(name) > 253 or any(
        not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", label)
        for label in name.split(".")
    ):
        raise ValueError()
    return value.lower()


@dataclass(frozen=True)
class DedicatedSettings:
    database_host: str
    database_port: int
    database_name: str
    database_user: str
    password_file: str = field(repr=False)
    security_enabled: bool = False
    csrf_key_file: str | None = field(default=None, repr=False)
    proxy_enabled: bool = False
    proxy_peers: frozenset = frozenset()
    origin: str = "https://livenet-v2.home.arpa:8443"

    @property
    def target(self):
        return (self.database_host, self.database_port, self.database_name, self.database_user)

    @classmethod
    def from_mapping(cls, values):
        try:
            allowed = {"ENVIRONMENT", "DATABASE_HOST", "DATABASE_PORT", "DATABASE_NAME",
                       "DATABASE_USER", "DATABASE_PASSWORD_FILE", "SECURITY_ENABLED",
                       "SECURITY_CSRF_KEY_FILE", "SECURITY_HTTPS_ORIGIN", "PROXY_ENABLED",
                       "PROXY_PEERS"}
            if not isinstance(values, dict) or set(values) - allowed:
                raise ValueError()
            if values["ENVIRONMENT"] != "production":
                raise ValueError()
            names = [values[k] for k in ("DATABASE_HOST", "DATABASE_NAME", "DATABASE_USER")]
            names[0] = _database_host(names[0])
            if any(not isinstance(v, str) or not v or any(c.isspace() for c in v)
                   or any(ord(c) < 32 or ord(c) == 127 for c in v)
                   or any(c in v for c in "/@?#=\x00") for v in names):
                raise ValueError()
            if names[1] == "livenet":
                raise ValueError()  # This dedicated profile must never use the original DB.
            port = values["DATABASE_PORT"]
            enabled = values.get("SECURITY_ENABLED", False)
            proxy = values.get("PROXY_ENABLED", False)
            if type(port) is not int or not 1 <= port <= 65535:
                raise ValueError()
            if type(enabled) is not bool or type(proxy) is not bool:
                raise ValueError()
            password_file = values["DATABASE_PASSWORD_FILE"]
            csrf_file = values.get("SECURITY_CSRF_KEY_FILE")
            for path in [password_file] + ([csrf_file] if enabled else []):
                if not isinstance(path, str) or not Path(path).is_absolute():
                    raise ValueError()
            origin = values.get("SECURITY_HTTPS_ORIGIN", "https://livenet-v2.home.arpa:8443")
            if origin != "https://livenet-v2.home.arpa:8443":
                raise ValueError()
            peers = values.get("PROXY_PEERS", ())
            if not isinstance(peers, (list, tuple, frozenset)):
                raise ValueError()
            if any(not isinstance(p, str) or "%" in p for p in peers):
                raise ValueError()
            peers = frozenset(str(ip_address(p)) for p in peers)
            if (proxy and not peers) or (not proxy and peers) or (enabled and not proxy):
                raise ValueError()
            return cls(names[0], port, names[1], names[2], password_file, enabled,
                       csrf_file, proxy, peers, origin)
        except (KeyError, TypeError, ValueError):
            raise ConfigurationError() from None


def _secret(path):
    # No symlink following and no world/group-readable credentials.
    descriptor = None
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        info = os.fstat(descriptor)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) & 0o077 or info.st_size > 16384):
            raise ValueError()
        value = os.read(descriptor, 16385).decode().strip()
        if not value or "\x00" in value:
            raise ValueError()
        return value
    except (OSError, TypeError, ValueError, UnicodeError):
        raise ConfigurationError() from None
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _check_libpq_environment():
    # libpq may consult these even with an explicit host/user/db URL. In
    # particular PGHOSTADDR overrides host resolution and PGSERVICE adds options.
    if any(key in os.environ for key in ("PGHOSTADDR", "PGSERVICE", "PGSERVICEFILE", "PGOPTIONS")):
        raise ConfigurationError()


def create_dedicated_app(values, *, readiness_checker=None, database_tls=None):
    from app.postgres_tls import PostgresTLS
    if database_tls is not None and type(database_tls) is not PostgresTLS:
        raise ConfigurationError()
    tls_query = database_tls.query() if database_tls is not None else {}
    settings = DedicatedSettings.from_mapping(values)
    _check_libpq_environment()
    password = _secret(settings.password_file)
    security = {"SECURITY_ENABLED": settings.security_enabled,
                "SECURITY_HTTPS_ORIGIN": settings.origin}
    if settings.security_enabled:
        security["SECURITY_CSRF_KEY"] = _secret(settings.csrf_key_file)
    app = create_app("production", security_config=security)
    if settings.security_enabled:
        try:
            SecurityPolicy.load(app.config)
        except Exception:
            raise ConfigurationError() from None
    url = URL.create("postgresql+psycopg", username=settings.database_user,
                     password=password, host=settings.database_host,
                     port=settings.database_port, database=settings.database_name, query=tls_query)

    # Both security and inventory use one lazy factory, with no DB fallback.
    from threading import Lock
    lock = Lock()
    factory = None

    def open_session():
        nonlocal factory
        _check_libpq_environment()
        if database_tls is not None:
            database_tls.query()  # Recheck the read-only CA mount before using a session.
        with lock:
            if factory is None:
                engine = create_engine(url, pool_pre_ping=True, hide_parameters=True, echo=False)
                factory = create_session_factory(engine)
        return factory()

    app.extensions["inventory"] = InventoryDependencies(
        app.extensions["inventory"].access, open_session)
    app.wsgi_app = TrustedProxy(app.wsgi_app, enabled=settings.proxy_enabled,
                               peers=settings.proxy_peers, authority="livenet-v2.home.arpa:8443")
    install_readiness(app, target=settings.target, checker=readiness_checker)
    return app
