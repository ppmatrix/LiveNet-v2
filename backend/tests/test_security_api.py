from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app import create_app
from app.security.models import GlobalRoleGrant, LocalUser
from app.security.service import AuthenticationService, hash_password, token_hash
from security_doubles import OfflineStore


ORIGIN = "https://lab.test"
AUTH = "/api/v1/auth"
INVENTORY = "/api/v1/inventory/resources"


@pytest.fixture(scope="session")
def password_hash():
    return hash_password("offline-api-password")


@pytest.fixture
def api(password_hash, monkeypatch):
    monkeypatch.setattr("app.inventory.routes.create_database_engine",
                        lambda: pytest.fail("Real database prohibited"))
    store = OfflineStore()
    user = LocalUser(id=uuid4(), login="alice", password_hash=password_hash, status="active")
    store.users[user.id] = user
    store.grants.append(GlobalRoleGrant(user_id=user.id, role="inventory_reader",
                                        scope_type="global", scope_id=None))
    app = create_app("testing", security_config={
        "SECURITY_ENABLED": True, "SECURITY_HTTPS_ORIGIN": ORIGIN,
        "SECURITY_CSRF_KEY": "synthetic-offline-key-not-for-operational-use",
    }, security_session_factory=store.factory, inventory_session_factory=store.factory)
    runtime = app.extensions["security"]
    clock = [datetime.now(timezone.utc)]
    runtime.service = lambda policy: AuthenticationService(store.factory, policy, lambda: clock[0])
    return app, app.test_client(), store, user, clock


def csrf(client):
    response = client.get(AUTH + "/csrf", base_url=ORIGIN)
    assert response.status_code == 200
    return response.json["csrf_token"]


def login(client, **extra):
    token = csrf(client)
    headers = {"Origin": ORIGIN, "X-CSRF-Token": token}
    headers.update(extra.pop("headers", {}))
    return client.post(AUTH + "/login", base_url=ORIGIN,
                       json={"login": "Alice", "password": "offline-api-password"},
                       headers=headers, **extra)


def test_csrf_before_login_does_not_authenticate(api):
    _, client, store, _, _ = api
    csrf(client)
    assert not store.sessions and not store.budgets
    assert client.get(AUTH + "/me", base_url=ORIGIN).status_code == 401
    assert client.get(INVENTORY, base_url=ORIGIN).status_code == 401


def test_reader_cannot_patch_resource_and_patch_requires_csrf(api):
    _,client,_,_,_=api
    assert login(client).status_code==200
    path=INVENTORY+'/'+str(uuid4())
    assert client.patch(path,base_url=ORIGIN,json={}).status_code==403
    response=client.patch(path,base_url=ORIGIN,json={},headers={'Origin':ORIGIN,'X-CSRF-Token':csrf(client)})
    assert response.status_code==403 and response.json['error']['code']=='forbidden'


def test_login_secure_cookie_me_and_logout(api):
    _, client, store, user, _ = api
    response = login(client)
    assert response.status_code == 200
    assert response.json["user"] == {"id": str(user.id), "login": "alice", "roles": ["inventory_reader"]}
    cookies = response.headers.getlist("Set-Cookie")
    for cookie in cookies:
        assert "Secure" in cookie and "HttpOnly" in cookie and "SameSite=Lax" in cookie
        assert "Domain=" not in cookie and "Path=/" in cookie
    cookie = client.get_cookie("__Host-livenet_session", domain="lab.test")
    assert token_hash(cookie.value) in store.sessions
    assert cookie.value not in response.get_data(as_text=True)
    assert client.get(AUTH + "/me", base_url=ORIGIN).json["user"]["id"] == str(user.id)
    csrf_token = csrf(client)
    response = client.post(AUTH + "/logout", base_url=ORIGIN,
                           headers={"Origin": ORIGIN, "X-CSRF-Token": csrf_token})
    assert response.status_code == 204
    assert client.get_cookie("__Host-livenet_session", domain="lab.test") is None
    assert client.get(AUTH + "/me", base_url=ORIGIN).status_code == 401
    assert store.sessions[token_hash(cookie.value)].revoked_at is not None


@pytest.mark.parametrize("headers", [{}, {"Origin": ORIGIN}, {"Origin": "null"},
                                      {"Origin": "https://evil.test"}])
def test_login_csrf_and_origin_required(api, headers):
    _, client, store, _, _ = api
    token = csrf(client)
    if headers.get("Origin") != ORIGIN:
        headers = {**headers, "X-CSRF-Token": token}
    response = client.post(AUTH + "/login", base_url=ORIGIN,
                           json={"login": "alice", "password": "offline-api-password"}, headers=headers)
    assert response.status_code == 403 and not store.sessions and not store.budgets


def test_referer_fallback_and_no_prefix_origin_matching(api):
    _, client, _, _, _ = api
    token = csrf(client)
    response = client.post(AUTH + "/login", base_url=ORIGIN,
                           json={"login": "alice", "password": "offline-api-password"},
                           headers={"Referer": ORIGIN + "/login", "X-CSRF-Token": token})
    assert response.status_code == 200
    assert login(client, headers={"Origin": ORIGIN + ".evil.test"}).status_code == 403


def test_forged_expired_and_rotated_csrf_rejected(api, monkeypatch):
    from itsdangerous.timed import TimestampSigner

    _, client, _, _, _ = api
    with monkeypatch.context() as patch:
        patch.setattr(TimestampSigner, "get_timestamp", lambda self: 1)
        expired = csrf(client)
    response = client.post(AUTH + "/login", base_url=ORIGIN,
                           json={"login": "alice", "password": "offline-api-password"},
                           headers={"Origin": ORIGIN, "X-CSRF-Token": expired})
    assert response.status_code == 403
    old = csrf(client)
    assert login(client).status_code == 200
    client.set_cookie("__Host-livenet_csrf", old, domain="lab.test")
    assert client.post(AUTH + "/logout", base_url=ORIGIN,
                       headers={"Origin": ORIGIN, "X-CSRF-Token": old}).status_code == 403
    client.set_cookie("__Host-livenet_csrf", "forged", domain="lab.test")
    assert client.post(AUTH + "/logout", base_url=ORIGIN,
                       headers={"Origin": ORIGIN, "X-CSRF-Token": "forged"}).status_code == 403


def test_session_fixation_and_existing_session_rotation(api):
    _, client, store, _, _ = api
    fixed = "a" * 43
    client.set_cookie("__Host-livenet_session", fixed, domain="lab.test")
    assert login(client).status_code == 200
    first = client.get_cookie("__Host-livenet_session", domain="lab.test").value
    assert first != fixed and token_hash(fixed) not in store.sessions
    assert login(client).status_code == 200
    second = client.get_cookie("__Host-livenet_session", domain="lab.test").value
    assert second != first
    assert store.sessions[token_hash(first)].revoked_at is not None


def test_reader_editor_and_role_changes_between_requests(api):
    _, client, store, user, _ = api
    assert login(client).status_code == 200
    assert client.get(INVENTORY, base_url=ORIGIN).status_code == 200
    token = csrf(client)
    headers = {"Origin": ORIGIN, "X-CSRF-Token": token}
    body = {"resource_type": "service", "display_name": "Lab API"}
    assert client.post(INVENTORY, base_url=ORIGIN, json=body, headers=headers).status_code == 403
    store.grants[0].role = "inventory_editor"
    response = client.post(INVENTORY, base_url=ORIGIN, json=body, headers=headers)
    assert response.status_code == 201
    assert store.audit[-1].actor_id == user.id
    assert client.get(response.headers["Location"], base_url=ORIGIN).status_code == 200
    store.grants.clear()
    assert client.get(INVENTORY, base_url=ORIGIN).status_code == 403
    assert client.post(INVENTORY, base_url=ORIGIN, json=body, headers=headers).status_code == 403
    assert len(store.resources) == 1


def test_inventory_write_without_csrf_and_inactive_account(api):
    _, client, store, user, _ = api
    store.grants[0].role = "inventory_editor"
    assert login(client).status_code == 200
    assert client.post(INVENTORY, base_url=ORIGIN,
                       json={"resource_type": "service", "display_name": "A"}).status_code == 403
    assert not store.resources
    user.status = "disabled"
    assert client.get(INVENTORY, base_url=ORIGIN).status_code == 401


def test_client_headers_never_supply_identity_or_roles(api):
    _, client, _, _, _ = api
    response = client.get(INVENTORY, base_url=ORIGIN,
                          headers={"X-User-ID": str(uuid4()), "X-Role": "inventory_editor",
                                   "Authorization": "Bearer fake"})
    assert response.status_code == 401


def test_unsupported_scope_not_global(api):
    _, client, store, _, _ = api
    assert login(client).status_code == 200
    store.grants[0].scope_type = "resource"
    store.grants[0].scope_id = uuid4()
    assert client.get(INVENTORY, base_url=ORIGIN).status_code == 403


@pytest.mark.parametrize("failure", ["fail_read", "fail_audit", "fail_flush", "fail_commit"])
def test_persistence_failure_does_not_set_session_cookie(api, failure):
    _, client, store, _, _ = api
    setattr(store, failure, True)
    response = login(client)
    assert response.status_code == 503
    assert client.get_cookie("__Host-livenet_session", domain="lab.test") is None
    assert not store.sessions
    assert "simulated" not in response.get_data(as_text=True)


def test_authenticated_persistence_failure_denies_access(api):
    _, client, store, _, _ = api
    assert login(client).status_code == 200
    store.fail_read = True
    assert client.get(INVENTORY, base_url=ORIGIN).status_code == 503


def test_fail_closed_configuration_and_transport(api):
    app, client, _, _, _ = api
    app.config["SECURITY_CSRF_KEY"] = None
    assert client.get(AUTH + "/csrf", base_url=ORIGIN).status_code == 503
    assert client.get(INVENTORY, base_url=ORIGIN).status_code == 503
    app.config["SECURITY_CSRF_KEY"] = "synthetic-offline-key-not-for-operational-use"
    assert client.get(AUTH + "/csrf", base_url="http://lab.test").status_code == 403
    assert client.get(AUTH + "/csrf", base_url="https://evil.test").status_code == 403


@pytest.mark.parametrize("path,method", [("/csrf", "get"), ("/me", "get"),
                                      ("/login", "post"), ("/logout", "post")])
def test_authentication_disabled_by_default(path, method, monkeypatch):
    monkeypatch.setattr("app.inventory.routes.create_database_engine",
                        lambda: pytest.fail("Real database prohibited"))
    response = getattr(create_app("testing").test_client(), method)(AUTH + path, base_url=ORIGIN)
    assert response.status_code == 503


def test_no_public_registration_or_admin_endpoints(api):
    _, client, _, _, _ = api
    assert client.post(AUTH + "/register", base_url=ORIGIN).status_code == 404
    assert client.post(AUTH + "/users", base_url=ORIGIN).status_code == 404


def test_auth_responses_are_not_cacheable(api):
    _, client, _, _, _ = api
    response = client.get(AUTH + "/csrf", base_url=ORIGIN)
    assert response.headers["Cache-Control"] == "no-store"
    assert "Cookie" in response.headers["Vary"]


def test_logout_audit_failure_keeps_cookie_and_rolls_back(api):
    _, client, store, _, _ = api
    assert login(client).status_code == 200
    cookie = client.get_cookie("__Host-livenet_session", domain="lab.test")
    token = csrf(client)
    store.fail_audit = True
    response = client.post(AUTH + "/logout", base_url=ORIGIN,
                           headers={"Origin": ORIGIN, "X-CSRF-Token": token})
    assert response.status_code == 503
    assert client.get_cookie("__Host-livenet_session", domain="lab.test").value == cookie.value
    assert store.sessions[token_hash(cookie.value)].revoked_at is None


def test_inventory_creation_audit_failure_rolls_back_with_real_identity(api):
    _, client, store, _, _ = api
    store.grants[0].role = "inventory_editor"
    assert login(client).status_code == 200
    token = csrf(client)
    store.fail_audit = True
    response = client.post(INVENTORY, base_url=ORIGIN,
                           json={"resource_type": "service", "display_name": "A"},
                           headers={"Origin": ORIGIN, "X-CSRF-Token": token})
    assert response.status_code == 500
    assert not store.resources


def test_login_failure_is_rate_limited_without_exposing_credentials(api, monkeypatch):
    _, client, store, _, _ = api
    monkeypatch.setattr("app.security.service.verify_password", lambda *args: False)
    for _ in range(5):
        assert login(client).status_code == 401
    assert login(client).status_code == 429
    assert not store.sessions


def test_inventory_missing_resource_still_returns_404(api):
    _, client, _, _, _ = api
    assert login(client).status_code == 200
    assert client.get(INVENTORY + "/" + str(uuid4()), base_url=ORIGIN).status_code == 404


def test_enabled_security_protects_writes_even_with_injected_inventory_policy(api):
    from unittest.mock import Mock
    from app.inventory.access import InventoryIdentity

    app, client, _, user, _ = api
    injected = Mock()
    injected.resolve_identity.return_value = InventoryIdentity(user.id)
    injected.can_create.return_value = True
    app.extensions["inventory"].access = injected
    response = client.post(INVENTORY, base_url=ORIGIN,
                           json={"resource_type": "service", "display_name": "A"})
    assert response.status_code == 401
    injected.can_create.assert_not_called()
