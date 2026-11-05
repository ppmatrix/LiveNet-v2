"""Create authorization integrity anchors baseline.

Revision ID: f067a01a7230
Revises: f066a01a7230
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "f067a01a7230"
down_revision = "f066a01a7230"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA authorization")

    op.create_table(
        "authorization_integrity_anchors",
        sa.Column(
            "authorization_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("operation", sa.Text(), nullable=False),
        sa.Column("target", sa.Text(), nullable=False),
        sa.Column("sql_sha256", sa.String(length=64), nullable=False),
        sa.Column("confirmed_state", sa.String(length=16), nullable=False),
        sa.Column("confirmed_sequence", sa.Integer(), nullable=False),
        sa.Column("confirmed_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint(
            "authorization_id",
            name="authorization_integrity_anchors_pkey",
        ),
        sa.CheckConstraint(
            "length(btrim(operation)) > 0",
            name="ck_auth_anchor_operation_not_empty",
        ),
        sa.CheckConstraint(
            "length(btrim(target)) > 0",
            name="ck_auth_anchor_target_not_empty",
        ),
        sa.CheckConstraint(
            "sql_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_auth_anchor_sql_sha256",
        ),
        sa.CheckConstraint(
            "confirmed_hash ~ '^[0-9a-f]{64}$'",
            name="ck_auth_anchor_confirmed_hash",
        ),
        sa.CheckConstraint(
            "confirmed_state IN ("
            "'prepared', 'authorized', 'consumed', "
            "'succeeded', 'failed', 'uncertain')",
            name="ck_auth_anchor_confirmed_state",
        ),
        sa.CheckConstraint(
            "confirmed_sequence >= 0",
            name="ck_auth_anchor_confirmed_sequence",
        ),
        sa.CheckConstraint(
            "(confirmed_sequence = 0) = (confirmed_state = 'prepared')",
            name="ck_auth_anchor_initial_state",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at",
            name="ck_auth_anchor_timestamps",
        ),
        schema="authorization",
    )


def downgrade() -> None:
    op.drop_table(
        "authorization_integrity_anchors",
        schema="authorization",
    )
    op.execute("DROP SCHEMA authorization")
