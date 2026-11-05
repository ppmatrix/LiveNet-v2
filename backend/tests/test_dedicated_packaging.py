"""DEV-04 offline artifact checks and a forwarding-policy oracle.

No Docker/Caddy/Gunicorn is invoked. The oracle interprets ONLY the declared
header allowlist, not Caddy syntax or its HTTP engine. Real validation is pending.
"""

import json
from pathlib import Path
import re
import runpy
import shlex

import pytest
from packaging.requirements import Requirement

import dedicated_wsgi
from app.dedicated import ConfigurationError
# Reuse synthetic-file and no-services pytest fixtures without changing DEV-02.
from test_dedicated_entrypoint import configuration, no_services


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
COMPOSE = ROOT / "compose.dedicated.yaml"
CADDY = ROOT / "infra/dedicated/Caddyfile"
AUTHORITY = "livenet-v2.home.arpa:8443"
CLIENT = "192.0.2.42"
PEER = "172.30.0.2"  # Synthetic test peer only; not a deployment allocation.


@pytest.fixture
def plan():
    # The descriptor deliberately uses JSON syntax, a YAML-compatible subset.
    return json.loads(COMPOSE.read_text())


def docker_instructions():
    return [line for line in (BACKEND / "Dockerfile.dedicated").read_text().splitlines()
            if line and not line.startswith("#")]


def test_image_selects_explicit_factory_and_nonprivileged_identity(plan):
    lines = docker_instructions()
    assert "ARG DEV04_PYTHON_IMAGE" in lines
    assert "FROM ${DEV04_PYTHON_IMAGE}" in lines
    assert "USER 10001:10001" in lines
    command = json.loads(next(line[4:] for line in lines if line.startswith("CMD ")))
    assert command == plan["services"]["backend"]["command"]
    assert command == ["gunicorn", "--config", "/app/gunicorn_container.conf.py",
                       "dedicated_wsgi:create_app('/run/livenet/backend.json')"]
    assert not any("flask run" in line or "wsgi:app" in line for line in lines)
    assert "HEALTHCHECK NONE" in lines  # No synthetic readiness/proxy bypass.


def test_build_copies_only_runtime_sources_and_does_not_import_application():
    lines = docker_instructions()
    copies = [shlex.split(line)[1:-1] for line in lines if line.startswith("COPY ")]
    assert copies == [
        ["requirements-container.lock"],
        ["app"], ["dedicated_wsgi.py", "gunicorn_container.conf.py"],
    ]
    assert all((BACKEND / name).exists() for group in copies for name in group)
    runs = [line for line in lines if line.startswith("RUN ")]
    assert runs == ["RUN pip install --index-url https://pypi.org/simple --only-binary=:all: --require-hashes --no-cache-dir --no-compile -r requirements-container.lock", "RUN pip check"]
    assert not any(line.startswith(("ADD ", "ENTRYPOINT ", "VOLUME ")) for line in lines)
    ignore = (BACKEND / "Dockerfile.dedicated.dockerignore").read_text().splitlines()
    assert ignore == ["**", "!app/**/*.py", "!requirements.txt",
                      "!requirements-dedicated.txt", "!requirements-container.constraints.txt", "!requirements-container.lock",
                      "!dedicated_wsgi.py", "!gunicorn_container.conf.py"]


def test_candidate_constraints_are_exact_and_satisfy_direct_requirements():
    constraints = {}
    for line in (BACKEND / "requirements-container.constraints.txt").read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        req = Requirement(line)
        pins = list(req.specifier)
        assert len(pins) == 1 and pins[0].operator == "==" and "*" not in pins[0].version
        constraints[req.name.lower().replace("_", "-")] = pins[0].version
    for name in ("requirements.txt", "requirements-dedicated.txt"):
        for line in (BACKEND / name).read_text().splitlines():
            if not line or line.startswith(("#", "-r")):
                continue
            req = Requirement(line)
            version = constraints[req.name.lower().replace("_", "-")]
            assert req.specifier.contains(version)
    assert constraints["psycopg"] == constraints["psycopg-binary"]
    assert constraints["gunicorn"] == "23.0.0"


def test_container_settings_preserve_proxy_and_local_configuration():
    current = runpy.run_path(str(BACKEND / "gunicorn_container.conf.py"))
    local = runpy.run_path(str(BACKEND / "gunicorn_dedicated.conf.py"))
    assert current["bind"] == "0.0.0.0:8000" and local["bind"] == "127.0.0.1:8000"
    for name in ("workers", "worker_class", "threads", "timeout", "graceful_timeout",
                 "preload_app", "reload", "daemon", "secure_scheme_headers",
                 "forwarded_allow_ips", "forwarder_headers", "proxy_protocol",
                 "accesslog", "errorlog", "loglevel", "capture_output"):
        assert current[name] == local[name], name
    assert current["worker_tmp_dir"] == "/tmp"


def test_network_graph_isolates_ingress_from_database(plan):
    assert set(plan["services"]) == {"web", "backend", "db"}
    assert set(plan["services"]["web"]["networks"]) == {"edge", "api"}
    assert set(plan["services"]["backend"]["networks"]) == {"api", "data"}
    assert set(plan["services"]["db"]["networks"]) == {"data"}
    assert plan["networks"]["api"]["internal"] is True
    assert plan["networks"]["data"]["internal"] is True
    assert "internal" not in plan["networks"]["edge"]
    assert set(plan["services"]["web"]["networks"]) & set(plan["services"]["db"]["networks"]) == set()
    assert plan["services"]["web"]["networks"]["api"]["ipv4_address"].startswith("${DEV04_CADDY_IPV4:?")


def test_only_https_can_be_published_and_all_services_remain_blocked(plan):
    for name, service in plan["services"].items():
        assert service["profiles"] == ["dev04-blocked"]
        assert service["entrypoint"] == ["/bin/sh", "-c", "exit 78"]
        assert service["restart"] == "no" and service["pull_policy"] == "never"
        assert not any(k in service for k in ("extends", "depends_on", "network_mode", "privileged", "healthcheck"))
        if name != "web":
            assert "ports" not in service
    assert plan["services"]["web"]["ports"] == [{
        "target": 8443, "published": "8443",
        "host_ip": "${DEV04_HTTPS_BIND_IP:?Pending approved host HTTPS address}", "protocol": "tcp",
    }]
    assert "include" not in plan and "secrets" not in plan
    assert set(plan["volumes"]) == {"postgres_data", "caddy_data"}
    assert all(not item.get("external", False) for item in plan["networks"].values())


def test_parameters_have_no_operational_defaults_or_embedded_secrets(plan):
    raw = COMPOSE.read_text()
    params = re.findall(r"\$\{([^}]+)\}", raw)
    assert params and all(re.fullmatch(r"DEV0[45]_[A-Z0-9_]+:\?[^}]+", p) for p in params)
    assert '"livenet"' not in raw and "DATABASE_URL" not in raw
    assert "POSTGRES_PASSWORD" not in plan["services"]["db"]["environment"]
    assert "environment" not in plan["services"]["backend"]
    for service in plan["services"].values():
        for mount in service.get("volumes", []):
            if mount["type"] == "bind":
                assert mount["read_only"] is True
                assert mount["bind"]["create_host_path"] is False
                assert "docker.sock" not in mount["source"]
    backend_mounts = plan["services"]["backend"]["volumes"]
    assert {m["target"] for m in backend_mounts} == {
        "/run/livenet/backend.json", "/run/livenet/runtime_password", "/run/livenet/csrf_key",
    }
    assert all(m["source"].startswith("${DEV04_") for m in backend_mounts)
    assert plan["services"]["backend"]["user"] == "10001:10001"


def test_legacy_deployment_remains_a_separate_path():
    assert '"flask", "--app", "wsgi:app"' in (BACKEND / "Dockerfile").read_text()
    assert "LIVENET_ENV: development" in (ROOT / "compose.backend.yaml").read_text()
    assert '"code":"api_unavailable"' in (ROOT / "infra/web-dev/Caddyfile").read_text()
    assert "respond" in (ROOT / "infra/web-dev/Caddyfile").read_text()


def declared_forwarding(incoming):
    """Small policy oracle, NOT a Caddy parser or an HTTP proxy implementation."""
    source = CADDY.read_text()
    directives = [line.strip() for line in source.splitlines() if line.strip().startswith(("request_header ", "header_up "))]
    expected = ["request_header -Forwarded", "request_header -X-Forwarded-*",
                "header_up Host " + AUTHORITY, "header_up X-Forwarded-Host " + AUTHORITY,
                "header_up X-Forwarded-Proto https",
                "header_up X-Forwarded-For {http.request.remote.host}",
                "header_up X-Forwarded-Port 8443"]
    assert directives == expected
    headers = {k: v for k, v in incoming.items()
               if k.lower() != "forwarded" and not k.lower().startswith("x-forwarded-")}
    headers = {k: v for k, v in headers.items() if k.lower() != "host"}
    for directive in directives[2:]:
        _, name, value = directive.split(" ", 2)
        headers[name] = CLIENT if value == "{http.request.remote.host}" else value
    return headers


def test_caddy_has_separate_api_ui_and_no_trust_or_csrf_rewrites():
    source = CADDY.read_text()
    assert "@api path /api/v1 /api/v1/*" in source
    assert "reverse_proxy backend:8000" in source
    assert "route {" in source
    assert source.index("request_header -Forwarded") < source.index("reverse_proxy backend:8000")
    assert "@ui path / /login /login/ /inventory /inventory/*" in source
    assert "try_files {path} /index.html" in source
    assert "tls internal" in source and "skip_install_trust" in source
    assert not any(word in source for word in ("trusted_proxies", "tls_insecure_skip_verify", "Access-Control-Allow"))
    assert not re.search(r"(?:header_up|request_header)\s+[-+]?\s*(Origin|Referer)\b", source, re.I)
    assert "api_unavailable" not in source  # The legacy refusal lives elsewhere.


@pytest.mark.parametrize("claims", [
    {}, {"X-Forwarded-For": "203.0.113.9, 203.0.113.10"},
    {"Forwarded": "for=attacker;proto=https", "X-Forwarded-Proto": "http"},
    {"x-forwarded-prefix": "/evil", "x-FoRwArDeD-Unknown": "injected"},
    {"Host": "evil.test", "X-Forwarded-Host": "evil.test", "X-Forwarded-Port": "443"},
])
def test_declared_sanitization_is_compatible_with_trusted_proxy(configuration, claims):
    app = dedicated_wsgi.create_app(str(configuration[0]))
    headers = declared_forwarding(claims)
    assert headers["X-Forwarded-For"] == CLIENT
    client = app.test_client()
    response = client.get("/api/v1/health", headers=headers,
                          environ_overrides={"REMOTE_ADDR": PEER})
    assert response.status_code == 200 and response.json == {"status": "ok", "service": "livenet-api"}
    assert client.get("/api/v1/ready", headers=headers,
                      environ_overrides={"REMOTE_ADDR": PEER}).status_code == 503
    assert client.get("/api/v1/health", headers=headers,
                      environ_overrides={"REMOTE_ADDR": "172.30.0.99"}).status_code == 403


def test_origin_and_referer_are_preserved_and_csrf_is_not_bypassed(configuration):
    app = dedicated_wsgi.create_app(str(configuration[0]))
    client = app.test_client()
    headers = declared_forwarding({"Origin": "https://evil.test", "Referer": "https://evil.test/login"})
    assert headers["Origin"] == "https://evil.test" and headers["Referer"] == "https://evil.test/login"
    assert client.post("/api/v1/auth/logout", headers=headers,
                       environ_overrides={"REMOTE_ADDR": PEER}).status_code == 403
    headers = declared_forwarding({"Origin": "https://" + AUTHORITY})
    assert client.post("/api/v1/auth/logout", headers=headers,
                       environ_overrides={"REMOTE_ADDR": PEER}).status_code == 403
    assert client.get("/api/v1/auth/me", headers=headers,
                      environ_overrides={"REMOTE_ADDR": PEER}).status_code == 401


@pytest.mark.parametrize("change", [
    {"DATABASE_NAME": "livenet"}, {"DATABASE_HOST": "db-one,db-two"},
    {"SECURITY_ENABLED": False}, {"PROXY_PEERS": ["172.30.0.0/16"]},
    {"DATABASE_PASSWORD_FILE": "relative"}, {"SECURITY_CSRF_KEY_FILE": "relative"},
])
def test_packaging_does_not_relax_factory_refusals(configuration, change):
    path, values = configuration
    path.write_text(json.dumps(values | change))
    with pytest.raises(ConfigurationError):
        dedicated_wsgi.create_app(str(path))


def test_missing_configuration_still_refuses(tmp_path):
    with pytest.raises(ConfigurationError):
        dedicated_wsgi.create_app(str(tmp_path / "not-provisioned.json"))
