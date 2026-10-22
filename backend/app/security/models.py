"""M1.2A metadata only. No schema creation or account provisioning on import."""

from datetime import datetime, timezone
from uuid import UUID as PythonUUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base


def utc_now():
    return datetime.now(timezone.utc)


class LocalUser(Base):
    __tablename__ = "local_users"
    __table_args__ = (
        UniqueConstraint("login", name="uq_local_users_login"),
        CheckConstraint("login = lower(btrim(login)) AND length(login) > 0", name="ck_local_users_login"),
        CheckConstraint("status IN ('active', 'disabled')", name="ck_local_users_status"),
        CheckConstraint("updated_at >= created_at", name="ck_local_users_timestamps"),
        {"schema": "security"},
    )
    id: Mapped[PythonUUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    login: Mapped[str] = mapped_column(String(128), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class LoginSession(Base):
    __tablename__ = "login_sessions"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_login_sessions_token_hash"),
        CheckConstraint("token_hash ~ '^[0-9a-f]{64}$'", name="ck_login_sessions_hash"),
        CheckConstraint("last_activity_at >= created_at AND expires_at > created_at", name="ck_login_sessions_times"),
        CheckConstraint("revoked_at IS NULL OR revoked_at >= created_at", name="ck_login_sessions_revoked"),
        {"schema": "security"},
    )
    id: Mapped[PythonUUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[PythonUUID] = mapped_column(ForeignKey("security.local_users.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class GlobalRoleGrant(Base):
    __tablename__ = "global_role_grants"
    __table_args__ = (
        UniqueConstraint("user_id", "role", name="uq_global_role_grants_user_role"),
        CheckConstraint("role IN ('inventory_reader', 'inventory_editor')", name="ck_global_role_grants_role"),
        CheckConstraint("scope_type = 'global' AND scope_id IS NULL", name="ck_global_role_grants_scope"),
        {"schema": "security"},
    )
    id: Mapped[PythonUUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[PythonUUID] = mapped_column(ForeignKey("security.local_users.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(16), nullable=False, default="global")
    scope_id: Mapped[PythonUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class LoginThrottle(Base):
    """Shared fixed-window budgets, including nonexistent logins. No raw IPs."""

    __tablename__ = "login_throttles"
    __table_args__ = (
        CheckConstraint("attempts >= 1", name="ck_login_throttles_attempts"),
        {"schema": "security"},
    )
    bucket_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    window_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False)
