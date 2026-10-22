"""Transactional, shared test double. Never opens an engine or executes SQL.

This models orchestration only; PostgreSQL locking/durability needs M1.2B.
"""

from contextlib import contextmanager
from copy import deepcopy
from datetime import timedelta
from threading import RLock
from types import SimpleNamespace

from sqlalchemy.orm import Session
from sqlalchemy.sql.dml import Insert

from app.audit.models import AuditEvent
from app.inventory.models import Resource
from app.security.models import GlobalRoleGrant, LocalUser, LoginSession


class OfflineStore:
    def __init__(self):
        self.users, self.sessions, self.resources, self.budgets = {}, {}, {}, {}
        self.grants, self.audit, self.statements = [], [], []
        self.window_seconds = 900
        self.closed = self.commits = self.rollbacks = 0
        self.fail_read = self.fail_audit = self.fail_flush = self.fail_commit = False
        self.lock = RLock()

    def factory(self):
        return OfflineSession(self)


class OfflineSession(Session):
    def __init__(self, store):
        super().__init__()  # Unbound even if an unexpected SQL path were reached.
        self.store = store

    @contextmanager
    def begin(self, *args, **kwargs):
        store = self.store
        with store.lock:
            names = ("users", "sessions", "resources", "budgets", "grants", "audit")
            before = deepcopy({name: getattr(store, name) for name in names})
            try:
                yield
                if store.fail_commit:
                    raise RuntimeError("simulated persistence failure")
                store.commits += 1
            except Exception:
                for name, value in before.items():
                    setattr(store, name, value)
                store.rollbacks += 1
                raise

    def scalar(self, statement, *args, **kwargs):
        store = self.store
        store.statements.append(statement)
        if store.fail_read:
            raise RuntimeError("simulated unavailable database")
        params = statement.compile().params
        if isinstance(statement, Insert):
            key, now = params["bucket_hash"], params["window_started_at"]
            start, count = store.budgets.get(key, (now, 0))
            if start <= now - timedelta(seconds=store.window_seconds):
                start, count = now, 0
            store.budgets[key] = (start, count + 1)
            return count + 1
        entity = statement.column_descriptions[0].get("entity")
        if entity is LocalUser:
            return next((u for u in store.users.values() if u.login == params["login_1"]), None)
        if entity is LoginSession:
            return store.sessions.get(params["token_hash_1"])
        if entity is Resource:
            return store.resources.get(params["id_1"])
        return len(store.resources)  # Inventory count.

    def scalars(self, statement, *args, **kwargs):
        self.store.statements.append(statement)
        if self.store.fail_read:
            raise RuntimeError("simulated unavailable database")
        params = statement.compile().params
        entity = statement.column_descriptions[0].get("entity")
        if entity is GlobalRoleGrant:
            values = [g for g in self.store.grants if g.user_id == params["user_id_1"]]
        elif entity is Resource:
            values = sorted(self.store.resources.values(), key=lambda r: (r.created_at, r.id))
        else:
            raise AssertionError("Unexpected offline query")
        return SimpleNamespace(all=lambda: values)

    def get(self, entity, identifier, *args, **kwargs):
        if self.store.fail_read:
            raise RuntimeError("simulated unavailable database")
        assert entity is LocalUser
        return self.store.users.get(identifier)

    def add(self, value, *args, **kwargs):
        if isinstance(value, AuditEvent):
            if self.store.fail_audit:
                raise RuntimeError("simulated audit failure")
            self.store.audit.append(value)
        elif isinstance(value, LoginSession):
            self.store.sessions[value.token_hash] = value
        elif isinstance(value, Resource):
            self.store.resources[value.id] = value
        else:
            raise AssertionError("Unexpected offline write")

    def flush(self, *args, **kwargs):
        if self.store.fail_flush:
            raise RuntimeError("simulated flush failure")

    def close(self):
        self.store.closed += 1
        super().close()
