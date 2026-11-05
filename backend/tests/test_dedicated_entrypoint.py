"""DEV-02: local synthetic files and Flask client only; no real services."""

import json
from pathlib import Path
import runpy
import socket
import subprocess
from unittest.mock import Mock
from uuid import uuid4

import pytest

import dedicated_wsgi
from app.dedicated import ConfigurationError
from app.security.models import GlobalRoleGrant, LocalUser
from app.security.service import hash_password
from security_doubles import OfflineStore
from test_trusted_proxy import AUTHORITY, HEADERS


BACKEND = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def no_services(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Real services and database engines are forbidden")

    for name in ("socket", "create_connection", "getaddrinfo"):
        monkeypatch.setattr(socket, name, forbidden)
    for name in ("Popen", "run"):
        monkeypatch.setattr(subprocess, name, forbidden)
    monkeypatch.setattr("app.dedicated.create_engine", forbidden)
    monkeypatch.setattr("app.inventory.routes.create_database_engine", forbidden)
    for key in ("PGHOSTADDR", "PGSERVICE", "PGSERVICEFILE", "PGOPTIONS"):
        monkeypatch.delenv(key, raising=False)


@pytest.fixture
def configuration(tmp_path):
    password = tmp_path / "password"
    password.write_text("synthetic-offline-password")
    password.chmod(0o600)
    csrf = tmp_path / "csrf"
    csrf.write_text("synthetic-offline-csrf-key-never-operational")
    csrf.chmod(0o600)
    values = {
        "ENVIRONMENT": "production", "DATABASE_HOST": "dedicated-db",
        "DATABASE_PORT": 5432, "DATABASE_NAME": "offline_lab", "DATABASE_USER": "app_role",
        "DATABASE_PASSWORD_FILE": str(password), "SECURITY_ENABLED": True,
        "SECURITY_CSRF_KEY_FILE": str(csrf),
        "SECURITY_HTTPS_ORIGIN": "https://" + AUTHORITY,
        "PROXY_ENABLED": True, "PROXY_PEERS": ["172.30.0.2"],
    }
    path = tmp_path / "dedicated.json"
    path.write_text(json.dumps(values))
    path.chmod(0o600)
    return path, values


def write_config(configuration, **changes):
    path, values = configuration
    path.write_text(json.dumps(values | changes))
    return str(path)


def request(client, path, *, method="get", headers=None, **kwargs):
    return getattr(client, method)(
        path, base_url="http://" + AUTHORITY, headers=HEADERS | (headers or {}),
        environ_overrides={"REMOTE_ADDR": "172.30.0.2"}, **kwargs,
    )


def test_import_is_inert_and_factory_is_selected_explicitly(configuration, monkeypatch):
    factory = Mock(side_effect=AssertionError("Import must not construct app"))
    monkeypatch.setattr("app.dedicated.create_dedicated_app", factory)
    # A fresh module namespace without reloading/mutating dedicated_wsgi itself.
    namespace = runpy.run_path(str(BACKEND / "dedicated_wsgi.py"))
    factory.assert_not_called()
    assert "app" not in namespace
    sentinel = object()
    factory.side_effect = None
    factory.return_value = sentinel
    assert namespace["create_app"](str(configuration[0])) is sentinel
    factory.assert_called_once_with(configuration[1])
    assert factory.call_args.kwargs == {}  # No synthetic checker injection.


def test_no_default_configuration_or_environment_fallback(configuration, monkeypatch):
    monkeypatch.setenv("LIVENET_ENV", "development")
    monkeypatch.setenv("DATABASE_NAME", "livenet")
    monkeypatch.setenv("DATABASE_USER", "bootstrap")
    with pytest.raises(TypeError):
        dedicated_wsgi.create_app()
    app = dedicated_wsgi.create_app(str(configuration[0]))
    assert app.debug is False and app.config["SECURITY_ENABLED"] is True


@pytest.mark.parametrize("key", sorted(dedicated_wsgi._REQUIRED_KEYS))
def test_every_setting_is_explicit(configuration, monkeypatch, key):
    path, values = configuration
    monkeypatch.setenv(key, "must-not-be-used")
    values.pop(key)
    path.write_text(json.dumps(values))
    with pytest.raises(ConfigurationError):
        dedicated_wsgi.create_app(str(path))


@pytest.mark.parametrize("changes", [
    {"ENVIRONMENT": "development"}, {"DATABASE_NAME": "livenet"},
    {"DATABASE_HOST": "db-one,db-two"}, {"DATABASE_HOST": "postgresql://other/lab"},
    {"DATABASE_PORT": "5432"}, {"DATABASE_USER": "user@other"},
    {"DATABASE_PASSWORD_FILE": "relative"}, {"SECURITY_CSRF_KEY_FILE": "relative"},
    {"SECURITY_ENABLED": False}, {"SECURITY_ENABLED": 1}, {"PROXY_ENABLED": False},
    {"PROXY_PEERS": []}, {"PROXY_PEERS": ["0.0.0.0/0"]},
    {"SECURITY_HTTPS_ORIGIN": "http://lab.test"},
    {"SECURITY_COOKIE_SECURE": False}, {"readiness_checker": True},
    {"DATABASE_PASSWORD": "forbidden-inline-secret"},
])
def test_rejects_invalid_destinations_and_security_overrides(configuration, changes):
    with pytest.raises(ConfigurationError, match="^Invalid dedicated backend configuration$"):
        dedicated_wsgi.create_app(write_config(configuration, **changes))


@pytest.mark.parametrize("body", [
    "{}", "[]", "null", "not-json", '{"private-marker":',
    '{"SECURITY_ENABLED":false,"SECURITY_ENABLED":true}',
    '{"value":NaN}', '{"value":Infinity}', '{"value":-Infinity}',
    "[" * 1000 + "]" * 1000,
])
def test_invalid_json_is_rejected_without_parser_context(configuration, body):
    path, _ = configuration
    path.write_text(body)
    with pytest.raises(ConfigurationError) as caught:
        dedicated_wsgi.create_app(str(path))
    assert str(caught.value) == "Invalid dedicated backend configuration"
    assert caught.value.__context__ is None


@pytest.mark.parametrize("fault", ["missing", "relative", "permissions", "symlink", "directory",
                                 "fifo", "oversized", "utf8", "owner"])
def test_configuration_file_boundary(configuration, tmp_path, monkeypatch, fault):
    import os

    path, _ = configuration
    if fault == "missing":
        path = tmp_path / "missing"
    elif fault == "relative":
        path = Path("relative.json")
    elif fault == "permissions":
        path.chmod(0o644)
    elif fault == "symlink":
        link = tmp_path / "link"
        link.symlink_to(path)
        path = link
    elif fault == "directory":
        path = tmp_path
    elif fault == "fifo":
        path = tmp_path / "fifo"
        os.mkfifo(path, 0o600)
    elif fault == "oversized":
        path.write_bytes(b" " * 16385)
    elif fault == "utf8":
        path.write_bytes(b"\xff")
    else:
        monkeypatch.setattr(dedicated_wsgi.os, "getuid", lambda: -1)
    with pytest.raises(ConfigurationError):
        dedicated_wsgi.create_app(str(path))


def test_health_readiness_and_proxy_without_postgresql(configuration):
    app = dedicated_wsgi.create_app(str(configuration[0]))
    client = app.test_client()
    response = request(client, "/api/v1/health")
    assert response.status_code == 200
    assert response.json == {"status": "ok", "service": "livenet-api"}
    for _ in range(2):
        response = request(client, "/api/v1/ready")
        assert response.status_code == 503 and response.json == {"status": "unavailable"}
        assert response.headers["Cache-Control"] == "no-store"
    assert client.get("/api/v1/health").status_code == 403
    assert request(client, "/api/v1/auth/me").status_code == 401
    assert request(client, "/api/v1/inventory/resources").status_code == 401


def test_authentication_and_inventory_share_offline_sessions(configuration):
    store = OfflineStore()
    user = LocalUser(id=uuid4(), login="offline-user", status="active",
                     password_hash=hash_password("synthetic-offline-password"))
    store.users[user.id] = user
    store.grants.append(GlobalRoleGrant(user_id=user.id, role="inventory_reader",
                                       scope_type="global", scope_id=None))
    app = dedicated_wsgi.create_app(str(configuration[0]))
    runtime = app.extensions["security"]
    assert runtime._sessions is None
    app.extensions["inventory"]._session_factory = store.factory
    assert runtime.service(runtime.policy()).sessions == app.extensions["inventory"].open_session
    client = app.test_client()
    csrf = request(client, "/api/v1/auth/csrf").json["csrf_token"]
    response = request(client, "/api/v1/auth/login", method="post",
                       headers={"Origin": "https://" + AUTHORITY, "X-CSRF-Token": csrf},
                       json={"login": "offline-user", "password": "synthetic-offline-password"})
    assert response.status_code == 200
    assert request(client, "/api/v1/auth/me").json["user"]["id"] == str(user.id)
    assert request(client, "/api/v1/inventory/resources").status_code == 200
    assert request(client, "/api/v1/ready").status_code == 503
    csrf = request(client, "/api/v1/auth/csrf").json["csrf_token"]
    assert request(client, "/api/v1/auth/logout", method="post",
                   headers={"Origin": "https://" + AUTHORITY,
                            "X-CSRF-Token": csrf}).status_code == 204
    assert request(client, "/api/v1/inventory/resources").status_code == 401


def test_wsgi_settings_do_not_reinterpret_forwarded_headers():
    settings = runpy.run_path(str(BACKEND / "gunicorn_dedicated.conf.py"))
    assert settings["bind"] == "127.0.0.1:8000"
    assert settings["worker_class"] == "sync" and settings["workers"] == 2
    assert settings["secure_scheme_headers"] == {} and settings["forwarded_allow_ips"] == ""
    assert settings["forwarder_headers"] == "" and settings["proxy_protocol"] is False
    assert settings["accesslog"] is None and settings["loglevel"] == "warning"
    assert all(settings[k] is False for k in ("preload_app", "reload", "daemon", "capture_output"))


def test_legacy_entrypoint_still_uses_original_factory(monkeypatch):
    monkeypatch.delenv("LIVENET_ENV", raising=False)
    namespace = runpy.run_path(str(BACKEND / "wsgi.py"))
    client = namespace["app"].test_client()
    assert client.get("/api/v1/health").status_code == 200
    assert client.get("/api/v1/ready").status_code == 404
    assert client.get("/api/v1/auth/me").status_code == 503
