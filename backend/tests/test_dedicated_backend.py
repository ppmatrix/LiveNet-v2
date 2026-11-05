"""Synthetic secrets/observations only; any attempted engine construction fails."""
from dataclasses import replace
from time import monotonic

import pytest

from app import create_app
from app.dedicated import ConfigurationError, DedicatedSettings, create_dedicated_app
from app.readiness import ReadinessObservation
from test_readiness_contract import complete_privileges
from test_trusted_proxy import AUTHORITY, HEADERS


@pytest.fixture
def settings(tmp_path, monkeypatch):
    for name in ("PGHOSTADDR", "PGSERVICE", "PGSERVICEFILE", "PGOPTIONS"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr("app.dedicated.create_engine",
                        lambda *a, **kw: pytest.fail("Database engine forbidden"))
    monkeypatch.setattr("app.inventory.routes.create_database_engine",
                        lambda: pytest.fail("Application fallback forbidden"))
    password = tmp_path / "synthetic-password"
    password.write_text("synthetic-offline-only")
    password.chmod(0o600)
    key = tmp_path / "synthetic-csrf"
    key.write_text("synthetic-offline-key-for-tests-only-123456789")
    key.chmod(0o600)
    return {"ENVIRONMENT": "production", "DATABASE_HOST": "dedicated-db",
            "DATABASE_PORT": 5432, "DATABASE_NAME": "offline_lab", "DATABASE_USER": "app_role",
            "DATABASE_PASSWORD_FILE": str(password), "SECURITY_CSRF_KEY_FILE": str(key)}


def enabled(values):
    return dict(values, SECURITY_ENABLED=True, PROXY_ENABLED=True, PROXY_PEERS=["172.30.0.2"])


def get(client, path, *, headers=None, method="get"):
    return getattr(client, method)(path, base_url="http://" + AUTHORITY,
                                  headers=HEADERS | (headers or {}),
                                  environ_overrides={"REMOTE_ADDR": "172.30.0.2"})


def observation(settings):
    return ReadinessObservation(DedicatedSettings.from_mapping(settings).target, monotonic(),
                                True, True, frozenset({"inventory", "audit", "security"}),
                                "f066a01a7230", "b12b01a7230",
                                complete_privileges(DedicatedSettings.from_mapping(settings).target))


def test_default_auth_disabled_and_no_database_or_readiness_check(settings):
    app = create_dedicated_app(settings, readiness_checker=lambda: pytest.fail("Checker forbidden"))
    assert app.config["SECURITY_ENABLED"] is False and app.debug is False
    c = app.test_client()
    assert c.get("/api/v1/auth/me").status_code == 503
    assert c.get("/api/v1/inventory/resources").status_code == 401
    assert c.get("/api/v1/ready").status_code == 503
    assert c.get("/api/v1/health").json == {"status": "ok", "service": "livenet-api"}


@pytest.mark.parametrize("key,value", [
    ("ENVIRONMENT", "development"), ("ENVIRONMENT", "testing"),
    ("DATABASE_NAME", "livenet"), ("DATABASE_HOST", ""), ("DATABASE_USER", "user@host"),
    ("DATABASE_PORT", "5432"), ("DATABASE_PORT", True), ("DATABASE_PORT", 0),
    ("DATABASE_PASSWORD_FILE", "relative"), ("SECURITY_ENABLED", "true"),
    ("PROXY_ENABLED", "true"), ("PROXY_PEERS", ["0.0.0.0/0"]),
    ("PROXY_PEERS", "172.30.0.2"), ("PROXY_PEERS", [1]),
    ("SECURITY_HTTPS_ORIGIN", "https://livenet-v2.home.arpa"),
    ("SECURITY_COOKIE_SECURE", False),
])
def test_invalid_configuration_is_explicit_and_sanitized(settings, key, value):
    with pytest.raises(ConfigurationError, match="^Invalid dedicated backend configuration$"):
        create_dedicated_app(dict(settings, **{key: value}))


@pytest.mark.parametrize("key", ["ENVIRONMENT", "DATABASE_HOST", "DATABASE_PORT",
                                 "DATABASE_NAME", "DATABASE_USER", "DATABASE_PASSWORD_FILE"])
def test_required_settings_no_environment_fallback(settings, monkeypatch, key):
    monkeypatch.setenv(key, "must-not-be-used")
    settings.pop(key)
    with pytest.raises(ConfigurationError):
        create_dedicated_app(settings)


@pytest.mark.parametrize("fault", ["missing", "readable", "symlink", "empty", "short_key", "no_key", "no_proxy"])
def test_required_secrets_and_proxy_boundary(settings, tmp_path, fault):
    values = enabled(settings)
    path = tmp_path / "synthetic-password"
    if fault == "missing": path.unlink()
    elif fault == "readable": path.chmod(0o644)
    elif fault == "symlink":
        link = tmp_path / "link"; link.symlink_to(path)
        values["DATABASE_PASSWORD_FILE"] = str(link)
    elif fault == "empty": path.write_text("")
    elif fault == "short_key": (tmp_path / "synthetic-csrf").write_text("short")
    elif fault == "no_key": values.pop("SECURITY_CSRF_KEY_FILE")
    else: values.update(PROXY_ENABLED=False, PROXY_PEERS=[])
    with pytest.raises(ConfigurationError): create_dedicated_app(values)


def test_proxy_csrf_origin_referer_and_secure_cookies(settings):
    c = create_dedicated_app(enabled(settings)).test_client()
    r = get(c, "/api/v1/auth/csrf")
    assert r.status_code == 200
    cookie = r.headers["Set-Cookie"]
    assert cookie.startswith("__Host-livenet_csrf=")
    assert all(x in cookie for x in ["Secure", "HttpOnly", "Path=/", "SameSite=Lax"])
    assert "Domain=" not in cookie
    assert get(c, "/api/v1/auth/me").status_code == 401
    token = r.json["csrf_token"]
    path = "/api/v1/auth/logout"
    assert get(c, path, method="post", headers={"X-CSRF-Token": token, "Origin": "https://evil.test"}).status_code == 403
    assert get(c, path, method="post", headers={"Origin": "https://" + AUTHORITY}).status_code == 403
    # Replace the service only after invalid requests have been proven to avoid DB.
    runtime = c.application.extensions["security"]
    seen = []
    class Service:
        def logout(self, token): seen.append(token)
    runtime.service = lambda policy: Service()
    assert get(c, path, method="post", headers={"X-CSRF-Token": token,
               "Referer": "https://" + AUTHORITY + "/inventory"}).status_code == 204
    assert seen == [None]


def test_readiness_requires_real_adapter_to_be_installed(settings):
    c = create_dedicated_app(enabled(settings)).test_client()
    r = get(c, "/api/v1/ready")
    assert r.status_code == 503 and r.json == {"status": "unavailable"}
    assert r.headers["Cache-Control"] == "no-store"


@pytest.mark.parametrize("fault", ["target", "stale", "future", "nan", "connected", "read_only",
                                 "schemas", "application", "security", "privileges", "untyped", "exception"])
def test_readiness_rejects_incomplete_stale_or_failed_observations(settings, fault):
    obs = observation(settings)
    changes = {"target": {"target": ("other", 5432, "db", "user")},
               "stale": {"observed_at": monotonic() - 10}, "future": {"observed_at": monotonic() + 10},
               "nan": {"observed_at": float("nan")}, "connected": {"connected": False},
               "read_only": {"read_only": False}, "schemas": {"schemas": frozenset({"inventory"})},
               "application": {"application_revision": "f067a01a7230"},
               "security": {"security_revision": ""}, "privileges": {"privileges": frozenset()}}
    def checker():
        if fault == "exception": raise RuntimeError("sensitive-driver-diagnostic")
        return {} if fault == "untyped" else replace(obs, **changes[fault])
    c = create_dedicated_app(enabled(settings), readiness_checker=checker).test_client()
    r = get(c, "/api/v1/ready")
    assert r.status_code == 503 and r.json == {"status": "unavailable"}
    assert b"sensitive" not in r.data


def test_synthetic_readiness_contract_success_only_in_offline_test(settings):
    calls = []
    def checker():
        calls.append("read-only-observation")
        return observation(settings)
    c = create_dedicated_app(enabled(settings), readiness_checker=checker).test_client()
    assert get(c, "/api/v1/ready").json == {"status": "ready"}
    assert calls == ["read-only-observation"]


def test_explicit_database_target_is_lazy_shared_and_never_uses_environment(settings, monkeypatch):
    from unittest.mock import Mock
    monkeypatch.setenv("DATABASE_NAME", "livenet")
    monkeypatch.setenv("DATABASE_USER", "bootstrap")
    engine = Mock()
    engine_factory = Mock(return_value=engine)
    session = Mock()
    session_factory = Mock(return_value=session)
    monkeypatch.setattr("app.dedicated.create_engine", engine_factory)
    maker = Mock(return_value=session_factory)
    monkeypatch.setattr("app.dedicated.create_session_factory", maker)
    app = create_dedicated_app(settings)
    engine_factory.assert_not_called()
    deps = app.extensions["inventory"]
    assert deps.open_session() is session and deps.open_session() is session
    engine_factory.assert_called_once()
    url = engine_factory.call_args.args[0]
    assert (url.host, url.port, url.database, url.username) == ("dedicated-db", 5432, "offline_lab", "app_role")
    assert engine_factory.call_args.kwargs == {"pool_pre_ping": True, "hide_parameters": True, "echo": False}
    maker.assert_called_once_with(engine)


@pytest.mark.parametrize("host,canonical", [
    ("db", "db"), ("db-one", "db-one"), ("db.lab.test", "db.lab.test"),
    ("DB.LAB.TEST", "db.lab.test"), ("db.lab.test.", "db.lab.test."),
    ("172.28.0.2", "172.28.0.2"), ("2001:0db8:0:0::2", "2001:db8::2"),
    ("::1", "::1"), ("::ffff:172.28.0.2", "::ffff:ac1c:2"),
    ("a" * 63 + ".test", "a" * 63 + ".test"),
])
def test_fix1_single_host_reaches_final_driver_parameters(settings, monkeypatch, host, canonical):
    from sqlalchemy.dialects.postgresql.psycopg import PGDialect_psycopg
    from unittest.mock import Mock
    engine = Mock()
    engine_factory = Mock(return_value=engine)
    maker = Mock(return_value=Mock(return_value=Mock()))
    monkeypatch.setattr("app.dedicated.create_engine", engine_factory)
    monkeypatch.setattr("app.dedicated.create_session_factory", maker)
    app = create_dedicated_app(dict(settings, DATABASE_HOST=host))
    engine_factory.assert_not_called()
    app.extensions["inventory"].open_session()
    args, params = PGDialect_psycopg().create_connect_args(engine_factory.call_args.args[0])
    assert args == []
    assert params == {"host": canonical, "port": 5432, "dbname": "offline_lab",
                      "user": "app_role", "password": "synthetic-offline-only"}
    assert app.extensions["security"]._sessions is None  # Same explicit inventory session source.


@pytest.mark.parametrize("host", [
    "db-one,db-two", "db-one,,db-two", ",", "127.0.0.1,", ",127.0.0.1", "",
    " db", "db ", "db other", "db\t", "db\n", "db\r", "db\x00", "db\x1f", "db\x7f",
    "-db", "db-", "db..test", ".db", "db..", "db_test", "db:5432", "[::1]",
    "postgresql://db/lab", "host=db", "db;host=other", "db\\other", "db'other",
    "/tmp", "@socket", "fe80::1%eth0", "999.1.1.1", "127.1", "127.0.0.01",
    "127.0.0.1.", "2130706433", "0x7f000001", "0177.0.0.1", "0x7f.1", "0x7f000001.",
    "a" * 64 + ".test", ".".join(["a" * 63] * 4), "déb.local", "hostaddr=127.0.0.1",
    "db?host=other", "db#other", "0.0.0.0", "::", "224.0.0.1", "ff02::1",
    "::ffff:0.0.0.0", "::ffff:224.0.0.1", None, 123, ["db"],
])
def test_fix1_rejects_host_lists_injections_and_ambiguity_before_engine(settings, host):
    with pytest.raises(ConfigurationError):
        create_dedicated_app(dict(settings, DATABASE_HOST=host))


@pytest.mark.parametrize("key,value", [
    ("DATABASE_NAME", "host=other"), ("DATABASE_USER", "user=postgres"),
    ("DATABASE_NAME", "postgresql://other/livenet"),
    ("DATABASE_USER", "app\x01"), ("DATABASE_NAME", "lab\x7f"),
    ("DATABASE_PORT", "5432,5433"),
])
def test_fix1_other_fields_cannot_embed_connection_parameters(settings, key, value):
    with pytest.raises(ConfigurationError):
        create_dedicated_app(dict(settings, **{key: value}))


@pytest.mark.parametrize("key", ["PGHOSTADDR", "PGSERVICE", "PGSERVICEFILE", "PGOPTIONS"])
def test_fix1_rejects_ambient_libpq_routing_or_session_overrides(settings, monkeypatch, key):
    monkeypatch.setenv(key, "synthetic-not-used")
    with pytest.raises(ConfigurationError): create_dedicated_app(settings)


@pytest.mark.parametrize("key", ["PGHOSTADDR", "PGSERVICE", "PGSERVICEFILE", "PGOPTIONS"])
def test_fix1_rechecks_ambient_overrides_before_lazy_session(settings, monkeypatch, key):
    app = create_dedicated_app(settings)
    monkeypatch.setenv(key, "synthetic-not-used")
    with pytest.raises(ConfigurationError): app.extensions["inventory"].open_session()


def test_real_security_flow_with_offline_store_through_proxy(settings):
    from uuid import uuid4
    from app.security.models import LocalUser, GlobalRoleGrant
    from app.security.service import hash_password
    from security_doubles import OfflineStore
    store = OfflineStore()
    user = LocalUser(id=uuid4(), login="offline-user", status="active",
                     password_hash=hash_password("synthetic-offline-password"))
    store.users[user.id] = user
    store.grants.append(GlobalRoleGrant(user_id=user.id, role="inventory_reader",
                                       scope_type="global", scope_id=None))
    app = create_dedicated_app(enabled(settings))
    app.extensions["inventory"]._session_factory = store.factory
    c = app.test_client()
    csrf = get(c, "/api/v1/auth/csrf").json["csrf_token"]
    response = c.post("/api/v1/auth/login", base_url="http://" + AUTHORITY,
                      headers=HEADERS | {"Origin": "https://" + AUTHORITY, "X-CSRF-Token": csrf},
                      environ_overrides={"REMOTE_ADDR": "172.30.0.2"},
                      json={"login": "offline-user", "password": "synthetic-offline-password"})
    assert response.status_code == 200 and response.json["user"]["roles"] == ["inventory_reader"]
    session_cookie = next(v for v in response.headers.getlist("Set-Cookie") if v.startswith("__Host-livenet_session="))
    assert all(v in session_cookie for v in ["Secure", "HttpOnly", "SameSite=Lax", "Path=/"])
    assert "Domain=" not in session_cookie
    assert get(c, "/api/v1/auth/me").json["user"]["id"] == str(user.id)
    new_csrf = get(c, "/api/v1/auth/csrf").json["csrf_token"]
    assert get(c, "/api/v1/auth/logout", method="post", headers={"Origin": "https://" + AUTHORITY,
               "X-CSRF-Token": new_csrf}).status_code == 204
    assert get(c, "/api/v1/auth/me").status_code == 401


def test_existing_factory_contract_unchanged():
    c = create_app("testing").test_client()
    assert c.get("/api/v1/health").status_code == 200
    assert c.get("/api/v1/ready").status_code == 404
    assert c.get("/api/v1/auth/me").status_code == 503
