"""Real session-based InventoryAccess; roles are never accepted from clients."""

from flask import g, request
from sqlalchemy import true

from app.inventory.access import InventoryIdentity
from app.security.errors import unavailable
from app.security.policy import SecurityPolicy
from app.security.service import AuthenticationService


class SecurityRuntime:
    def __init__(self, app, session_factory=None):
        self.app = app
        self._sessions = session_factory

    def policy(self):
        return SecurityPolicy.load(self.app.config)

    def service(self, policy):
        factory = (self._sessions if self._sessions is not None
                   else self.app.extensions["inventory"].open_session)
        return AuthenticationService(factory, policy)

    def authenticated(self):
        policy = self.policy()
        policy.check_transport(request)
        if not hasattr(g, "livenet_authenticated_user"):
            try:
                g.livenet_authenticated_user = self.service(policy).authenticate(
                    request.cookies.get(policy.session_cookie),
                )
            except Exception:
                raise unavailable() from None
        return g.livenet_authenticated_user


class SessionInventoryAccess:
    def __init__(self, runtime):
        self.runtime = runtime

    def resolve_identity(self):
        if self.runtime.app.config.get("SECURITY_ENABLED") is not True:
            return None
        user = self.runtime.authenticated()
        return InventoryIdentity(user.id) if user else None

    def read_scope(self, identity):
        user = self.runtime.authenticated()
        if user and user.id == identity.actor_id and user.roles & {"inventory_reader", "inventory_editor"}:
            return true()
        return None

    def can_create(self, identity, data):
        user = self.runtime.authenticated()
        return bool(user and user.id == identity.actor_id and "inventory_editor" in user.roles)
