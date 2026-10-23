"""Initial security schema. Independent root, no data or AUTH-03 dependency.

Python defaults remain in M1.2A models; no server defaults are introduced here.
Downgrade is deliberately blocked pending a separately reviewed recovery plan.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "b12b01a7230"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE SCHEMA security")
    op.create_table(
        "local_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("login", sa.String(128), nullable=False),
        sa.Column("password_hash", sa.String(512), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_security_local_users"),
        sa.UniqueConstraint("login", name="uq_local_users_login"),
        sa.CheckConstraint("login = lower(btrim(login)) AND length(login) > 0", name="ck_local_users_login"),
        sa.CheckConstraint("status IN ('active', 'disabled')", name="ck_local_users_status"),
        sa.CheckConstraint("updated_at >= created_at", name="ck_local_users_timestamps"),
        schema="security",
    )
    op.create_table(
        "login_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_security_login_sessions"),
        sa.ForeignKeyConstraint(["user_id"], ["security.local_users.id"],
                                name="fk_security_login_sessions_user_id_local_users"),
        sa.UniqueConstraint("token_hash", name="uq_login_sessions_token_hash"),
        sa.CheckConstraint("token_hash ~ '^[0-9a-f]{64}$'", name="ck_login_sessions_hash"),
        sa.CheckConstraint("last_activity_at >= created_at AND expires_at > created_at", name="ck_login_sessions_times"),
        sa.CheckConstraint("revoked_at IS NULL OR revoked_at >= created_at", name="ck_login_sessions_revoked"),
        schema="security",
    )
    op.create_index("ix_security_login_sessions_user_id", "login_sessions", ["user_id"],
                    unique=False, schema="security")
    op.create_table(
        "global_role_grants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("scope_type", sa.String(16), nullable=False),
        sa.Column("scope_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_security_global_role_grants"),
        sa.ForeignKeyConstraint(["user_id"], ["security.local_users.id"],
                                name="fk_security_global_role_grants_user_id_local_users"),
        sa.UniqueConstraint("user_id", "role", name="uq_global_role_grants_user_role"),
        sa.CheckConstraint("role IN ('inventory_reader', 'inventory_editor')", name="ck_global_role_grants_role"),
        sa.CheckConstraint("scope_type = 'global' AND scope_id IS NULL", name="ck_global_role_grants_scope"),
        schema="security",
    )
    op.create_table(
        "login_throttles",
        sa.Column("bucket_hash", sa.String(64), nullable=False),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("bucket_hash", name="pk_security_login_throttles"),
        sa.CheckConstraint("attempts >= 1", name="ck_login_throttles_attempts"),
        schema="security",
    )


def downgrade():
    raise RuntimeError("Downgrade security bloqueado: exige plano de recuperacao revisto e autorizacao separada")
