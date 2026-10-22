from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql

from app.config import Config
from app.security.errors import SecurityError
from app.security.models import GlobalRoleGrant, LocalUser, LoginSession, LoginThrottle
from app.security.policy import SecurityPolicy
from app.security.service import AuthenticationService, hash_password, normalize_credentials, token_hash, verify_password
from security_doubles import OfflineStore


@pytest.fixture(scope="session")
def encoded_password():
    return hash_password("synthetic-password-only-for-offline-tests")


@pytest.fixture
def auth(encoded_password):
    config = {key: getattr(Config, key) for key in dir(Config) if key.startswith("SECURITY_")}
    config.update(SECURITY_ENABLED=True, SECURITY_HTTPS_ORIGIN="https://lab.test",
                  SECURITY_CSRF_KEY="offline-test-key-never-an-operational-secret")
    policy = SecurityPolicy.load(config)
    store = OfflineStore()
    user = LocalUser(id=uuid4(), login="alice", password_hash=encoded_password, status="active")
    store.users[user.id] = user
    store.grants.append(GlobalRoleGrant(user_id=user.id, role="inventory_reader",
                                        scope_type="global", scope_id=None))
    clock = [datetime(2026, 10, 23, 12, tzinfo=timezone.utc)]
    service = AuthenticationService(store.factory, policy, lambda: clock[0])
    return service, store, user, clock


def log_in(service, **kwargs):
    return service.login("alice", "synthetic-password-only-for-offline-tests", "192.0.2.1", **kwargs)


def test_scrypt_hash_and_verification(encoded_password):
    assert encoded_password.startswith("scrypt:")
    assert verify_password(encoded_password, "synthetic-password-only-for-offline-tests")
    assert not verify_password(encoded_password, "wrong")
    assert not verify_password("pbkdf2:invalid", "wrong")
    assert hash_password("same-input") != hash_password("same-input")


@pytest.mark.parametrize("value", [None, "", 123, "x" * 1025, "a\0b"])
def test_invalid_password_hash_input(value):
    with pytest.raises(ValueError):
        hash_password(value)


@pytest.mark.parametrize("payload", [None, [], {}, {"login": "a", "password": "x", "role": "editor"},
                                     {"login": [], "password": "x"},
                                     {"login": "a", "password": None}])
def test_invalid_login_payload(payload):
    with pytest.raises(SecurityError) as error:
        normalize_credentials(payload)
    assert error.value.code == 400


def test_normalized_login():
    assert normalize_credentials({"login": " Alice ", "password": " x "}) == ("alice", " x ")


def test_login_persists_only_hash_and_safe_audit(auth):
    service, store, user, _ = auth
    principal, token = log_in(service)
    assert principal.id == user.id and principal.roles == {"inventory_reader"}
    assert len(token) == 43 and token not in store.sessions
    stored = store.sessions[token_hash(token)]
    assert stored.token_hash == token_hash(token)
    assert not hasattr(stored, "token")
    assert stored.expires_at - stored.created_at == timedelta(hours=12)
    assert store.audit[-1].action == "security.login.succeeded"
    for event in store.audit:
        assert token not in repr((event.changes, event.context))
        assert "synthetic-password" not in repr((event.changes, event.context))
    assert store.closed == 2


@pytest.mark.parametrize("condition", ["unknown", "wrong", "disabled"])
def test_invalid_credentials_are_generic_and_audited(auth, condition):
    service, store, user, _ = auth
    login, password = "alice", "synthetic-password-only-for-offline-tests"
    if condition == "unknown":
        login = "missing"
    elif condition == "wrong":
        password = "wrong"
    else:
        user.status = "disabled"
    with pytest.raises(SecurityError) as error:
        service.login(login, password, "192.0.2.1")
    assert error.value.code == 401 and error.value.description == "Credenciais inválidas."
    assert not store.sessions
    assert store.audit[-1].action == "security.login.failed"


def test_session_activity_does_not_extend_absolute_expiry(auth):
    service, store, _, clock = auth
    _, token = log_in(service)
    expiry = store.sessions[token_hash(token)].expires_at
    clock[0] += timedelta(minutes=29)
    assert service.authenticate(token) is not None
    assert store.sessions[token_hash(token)].last_activity_at == clock[0]
    assert store.sessions[token_hash(token)].expires_at == expiry


def test_absolute_cap_is_enforced_even_if_stored_expiry_is_longer(auth):
    service, store, _, clock = auth
    _, token = log_in(service)
    row = store.sessions[token_hash(token)]
    row.expires_at += timedelta(days=1)
    clock[0] += timedelta(hours=12)
    row.last_activity_at = clock[0]
    assert service.authenticate(token) is None


@pytest.mark.parametrize("condition", ["idle", "absolute", "revoked", "disabled", "clock_backwards"])
def test_session_invalidation(auth, condition):
    service, store, user, clock = auth
    _, token = log_in(service)
    row = store.sessions[token_hash(token)]
    if condition == "idle":
        clock[0] += timedelta(minutes=30)
    elif condition == "absolute":
        clock[0] += timedelta(hours=12)
        row.last_activity_at = clock[0]
    elif condition == "revoked":
        row.revoked_at = clock[0]
    elif condition == "disabled":
        user.status = "disabled"
    else:
        clock[0] -= timedelta(seconds=1)
    assert service.authenticate(token) is None
    assert store.sessions[token_hash(token)].revoked_at is not None


def test_logout_is_persistent_and_idempotent(auth):
    service, store, _, _ = auth
    _, token = log_in(service)
    service.logout(token)
    events = len(store.audit)
    assert service.authenticate(token) is None
    service.logout(token)
    assert len(store.audit) == events
    assert any(e.action == "security.logout.succeeded" for e in store.audit)


def test_login_rotates_existing_session(auth):
    service, store, _, _ = auth
    _, old = log_in(service)
    _, new = log_in(service, old_token=old)
    assert new != old
    assert service.authenticate(old) is None
    assert service.authenticate(new) is not None
    assert any(e.context.get("reason") == "login_rotation" for e in store.audit)


def test_roles_are_reloaded_and_unsupported_scopes_denied(auth):
    service, store, user, _ = auth
    _, token = log_in(service)
    store.grants[:] = [GlobalRoleGrant(user_id=user.id, role="inventory_editor",
                                       scope_type="group", scope_id=uuid4())]
    assert service.authenticate(token).roles == frozenset()
    store.grants[:] = [GlobalRoleGrant(user_id=user.id, role="inventory_editor",
                                       scope_type="global", scope_id=None)]
    assert service.authenticate(token).roles == {"inventory_editor"}
    store.grants.clear()
    assert service.authenticate(token).roles == frozenset()


def test_persistent_rate_budget_shared_across_service_instances(auth, monkeypatch):
    service, store, _, clock = auth
    monkeypatch.setattr("app.security.service.verify_password", lambda *args: False)
    for _ in range(5):
        with pytest.raises(SecurityError) as error:
            service.login("alice", "wrong", "192.0.2.1")
        assert error.value.code == 401
    other = AuthenticationService(store.factory, service.policy, lambda: clock[0])
    with pytest.raises(SecurityError) as error:
        other.login("alice", "wrong", "192.0.2.2")
    assert error.value.code == 429
    statement = store.statements[0].compile(dialect=postgresql.dialect())
    assert "ON CONFLICT" in str(statement) and "RETURNING" in str(statement)
    assert "CASE WHEN" in str(statement)
    clock[0] += timedelta(seconds=900)
    with pytest.raises(SecurityError) as error:
        other.login("alice", "wrong", "192.0.2.1")
    assert error.value.code == 401


def test_source_budget_limits_distributed_logins(auth, monkeypatch):
    service, _, _, _ = auth
    monkeypatch.setattr("app.security.service.verify_password", lambda *args: False)
    for i in range(50):
        with pytest.raises(SecurityError) as error:
            service.login(f"missing{i}", "wrong", "192.0.2.1")
        assert error.value.code == 401
    with pytest.raises(SecurityError) as error:
        service.login("another", "wrong", "192.0.2.1")
    assert error.value.code == 429


@pytest.mark.parametrize("failure", ["fail_read", "fail_audit", "fail_flush", "fail_commit"])
def test_login_persistence_failure_never_returns_permission(auth, failure):
    service, store, _, _ = auth
    setattr(store, failure, True)
    with pytest.raises(RuntimeError):
        log_in(service)
    assert not store.sessions
    assert store.rollbacks >= 1 and store.closed >= 1


def test_logout_audit_failure_rolls_back_revocation(auth):
    service, store, _, _ = auth
    _, token = log_in(service)
    store.fail_audit = True
    with pytest.raises(RuntimeError):
        service.logout(token)
    assert store.sessions[token_hash(token)].revoked_at is None


def test_models_have_security_schema_fks_and_no_plain_tokens():
    for model in (LocalUser, LoginSession, GlobalRoleGrant, LoginThrottle):
        assert model.__table__.schema == "security"
    assert {fk.target_fullname for fk in LoginSession.__table__.foreign_keys} == {"security.local_users.id"}
    assert {fk.target_fullname for fk in GlobalRoleGrant.__table__.foreign_keys} == {"security.local_users.id"}
    assert "token" not in LoginSession.__table__.columns
    assert "password" not in LocalUser.__table__.columns
