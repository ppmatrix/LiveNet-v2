"""Persistent local authentication. All writes are transactional and audited.

No process-local rate limiter, automatic provisioning or credential logging.
"""

import hashlib
import hmac
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import case, select
from sqlalchemy.dialects.postgresql import insert
from werkzeug.security import check_password_hash, generate_password_hash

from app.audit.service import record_audit_event
from app.security.errors import SecurityError
from app.security.models import GlobalRoleGrant, LocalUser, LoginSession, LoginThrottle


SCRYPT = "scrypt:32768:8:1"
ROLES = frozenset({"inventory_reader", "inventory_editor"})


def hash_password(password):
    if not isinstance(password, str) or not 1 <= len(password) <= 1024 or "\0" in password:
        raise ValueError("Invalid password")
    return generate_password_hash(password, method=SCRYPT)


def verify_password(stored_hash, password):
    if not isinstance(stored_hash, str) or not stored_hash.startswith(SCRYPT + "$"):
        hash_password(password)  # Comparable work for missing/unsupported credentials.
        return False
    try:
        return check_password_hash(stored_hash, password)
    except (ValueError, TypeError):
        return False


def normalize_credentials(payload):
    if not isinstance(payload, dict) or set(payload) != {"login", "password"}:
        raise SecurityError(400, "invalid_request", "Pedido inválido.")
    login, password = payload["login"], payload["password"]
    if (not isinstance(login, str) or len(login) > 128
            or not re.fullmatch(r"[a-z0-9][a-z0-9_.@-]{0,127}", login.strip().lower())
            or not isinstance(password, str) or not 1 <= len(password) <= 1024
            or "\0" in password):
        raise SecurityError(400, "invalid_request", "Pedido inválido.")
    return login.strip().lower(), password


def token_hash(token):
    if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        return None
    return hashlib.sha256(token.encode("ascii")).hexdigest()


@dataclass(frozen=True)
class AuthenticatedUser:
    id: UUID
    login: str
    roles: frozenset

    def public(self):
        return {"id": str(self.id), "login": self.login, "roles": sorted(self.roles)}


class AuthenticationService:
    def __init__(self, session_factory, policy, clock=None):
        self.sessions = session_factory
        self.policy = policy
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def _audit(self, session, action, user_id=None, entity_id=None, reason=None):
        return record_audit_event(
            session, actor_type="user" if user_id else "anonymous", actor_id=user_id,
            action=action, entity_type="security.session", entity_id=entity_id,
            outcome="failure" if action.endswith("failed") else "success",
            context={} if reason is None else {"reason": reason},
        )

    def _roles(self, session, user_id):
        grants = session.scalars(select(GlobalRoleGrant).where(
            GlobalRoleGrant.user_id == user_id, GlobalRoleGrant.scope_type == "global",
            GlobalRoleGrant.scope_id.is_(None),
        )).all()
        return frozenset(g.role for g in grants if g.scope_type == "global"
                         and g.scope_id is None and g.role in ROLES)

    def _find_session(self, session, token):
        digest = token_hash(token)
        if digest is None:
            return None
        return session.scalar(select(LoginSession).where(
            LoginSession.token_hash == digest,
        ).with_for_update())

    def _revoke(self, session, login_session, now, reason):
        if login_session.revoked_at is None:
            login_session.revoked_at = max(now, login_session.created_at)
            self._audit(session, "security.session.revoked", login_session.user_id,
                        login_session.id, reason)

    def _budget(self, login, source):
        now = self.clock()
        cutoff = now - timedelta(seconds=self.policy.window_seconds)
        permitted = True
        with self.sessions() as session:
            with session.begin():
                for kind, value, limit in (("login", login, self.policy.login_limit),
                                            ("source", source, self.policy.source_limit)):
                    bucket = hmac.new(self.policy.csrf_key.encode(),
                                      ("rate:" + kind + ":" + value).encode(), hashlib.sha256).hexdigest()
                    expired = LoginThrottle.window_started_at <= cutoff
                    statement = insert(LoginThrottle).values(
                        bucket_hash=bucket, window_started_at=now, attempts=1,
                    ).on_conflict_do_update(
                        index_elements=[LoginThrottle.bucket_hash],
                        set_={"window_started_at": case((expired, now), else_=LoginThrottle.window_started_at),
                              "attempts": case((expired, 1), else_=LoginThrottle.attempts + 1)},
                    ).returning(LoginThrottle.attempts)
                    attempts = session.scalar(statement)
                    if type(attempts) is not int or attempts < 1:
                        raise RuntimeError("Invalid persistent login budget")
                    permitted = permitted and attempts <= limit
                if not permitted:
                    self._audit(session, "security.login.failed", reason="rate_limited")
        return permitted

    def login(self, login, password, source, old_token=None):
        if not self._budget(login, source):
            raise SecurityError(429, "login_limited", "Autenticação temporariamente limitada.")
        result = None
        with self.sessions() as session:
            with session.begin():
                user = session.scalar(select(LocalUser).where(LocalUser.login == login).with_for_update())
                valid = verify_password(user.password_hash if user else None, password)
                if not valid or user.status != "active":
                    self._audit(session, "security.login.failed", reason="invalid_credentials")
                else:
                    now = self.clock()
                    old = self._find_session(session, old_token)
                    if old is not None:
                        self._revoke(session, old, now, "login_rotation")
                    token = secrets.token_urlsafe(32)
                    login_session = LoginSession(
                        token_hash=token_hash(token), user_id=user.id, created_at=now,
                        last_activity_at=now,
                        expires_at=now + timedelta(seconds=self.policy.absolute_seconds),
                    )
                    # IDs are needed for audit before flush; no server-side generation.
                    login_session.id = uuid4()
                    session.add(login_session)
                    self._audit(session, "security.login.succeeded", user.id, login_session.id)
                    session.flush()
                    result = (AuthenticatedUser(user.id, user.login, self._roles(session, user.id)), token)
        if result is None:
            raise SecurityError(401, "invalid_credentials", "Credenciais inválidas.")
        return result

    def authenticate(self, token):
        if token_hash(token) is None:
            return None
        result = None
        with self.sessions() as session:
            with session.begin():
                login_session = self._find_session(session, token)
                if login_session is None or login_session.revoked_at is not None:
                    return None
                user = session.get(LocalUser, login_session.user_id)
                now = self.clock()
                if (user is None or user.status != "active" or now < login_session.last_activity_at
                        or now >= login_session.expires_at
                        or now >= login_session.created_at + timedelta(seconds=self.policy.absolute_seconds)
                        or now - login_session.last_activity_at >= timedelta(seconds=self.policy.idle_seconds)):
                    self._revoke(session, login_session, now, "inactive_or_expired")
                else:
                    login_session.last_activity_at = now
                    result = AuthenticatedUser(user.id, user.login, self._roles(session, user.id))
        return result

    def logout(self, token):
        with self.sessions() as session:
            with session.begin():
                login_session = self._find_session(session, token)
                if login_session is not None and login_session.revoked_at is None:
                    self._revoke(session, login_session, self.clock(), "logout")
                    self._audit(session, "security.logout.succeeded", login_session.user_id, login_session.id)
