import pytest
from flask import Flask, jsonify, request

from app.trusted_proxy import TrustedProxy


AUTHORITY = "livenet-v2.home.arpa:8443"
HEADERS = {"X-Forwarded-Proto": "https", "X-Forwarded-Host": AUTHORITY,
           "X-Forwarded-For": "10.10.77.42"}


def client(enabled=True):
    app = Flask(__name__)

    @app.get("/")
    def observe():
        return jsonify(secure=request.is_secure, host=request.host,
                       client=request.remote_addr, forwarded=request.headers.get("X-Forwarded-For"))

    app.wsgi_app = TrustedProxy(app.wsgi_app, enabled=enabled,
                               peers={"172.30.0.2"}, authority=AUTHORITY)
    return app.test_client()


def test_trusted_socket_peer_restores_https_authority_and_real_client():
    r = client().get("/", base_url="http://" + AUTHORITY, headers=HEADERS,
                     environ_overrides={"REMOTE_ADDR": "172.30.0.2"})
    assert r.status_code == 200
    assert r.json == {"secure": True, "host": AUTHORITY, "client": "10.10.77.42", "forwarded": None}


@pytest.mark.parametrize("peer", ["10.10.77.42", "172.30.0.3", "", "invalid", "::1"])
def test_untrusted_peers_cannot_forge_forwarded_headers(peer):
    assert client().get("/", base_url="http://" + AUTHORITY, headers=HEADERS,
                        environ_overrides={"REMOTE_ADDR": peer}).status_code == 403


@pytest.mark.parametrize("key,value", [
    ("X-Forwarded-Proto", "http"), ("X-Forwarded-Proto", "https,http"),
    ("X-Forwarded-Host", "evil.test:8443"), ("X-Forwarded-Host", "livenet-v2.home.arpa"),
    ("X-Forwarded-Port", "443"), ("X-Forwarded-For", "10.1.1.1, 10.2.2.2"),
    ("X-Forwarded-For", "invalid"), ("Forwarded", "proto=https"),
    ("X-Forwarded-Prefix", "/other"),
])
def test_ambiguous_or_forged_headers_fail_closed(key, value):
    h = dict(HEADERS, **{key: value})
    r = client().get("/", base_url="http://" + AUTHORITY, headers=h,
                     environ_overrides={"REMOTE_ADDR": "172.30.0.2"})
    assert r.status_code == 403 and r.json["error"]["code"] == "invalid_proxy"


@pytest.mark.parametrize("missing", list(HEADERS))
def test_missing_required_proxy_header(missing):
    h = HEADERS.copy(); h.pop(missing)
    assert client().get("/", base_url="http://" + AUTHORITY, headers=h,
                        environ_overrides={"REMOTE_ADDR": "172.30.0.2"}).status_code == 403


def test_original_host_must_also_match_and_proxy_disabled_rejects_forwarding():
    assert client().get("/", base_url="http://evil.test", headers=HEADERS,
                        environ_overrides={"REMOTE_ADDR": "172.30.0.2"}).status_code == 403
    r = client(False).get("/", base_url="http://" + AUTHORITY, headers=HEADERS)
    assert r.status_code == 403
    assert client(False).get("/", base_url="http://" + AUTHORITY).json["secure"] is False
