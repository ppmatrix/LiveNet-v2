"""Create inventory effective configs.

Revision ID: f065d01a7230
Revises: f065c01a7230
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "f065d01a7230"
down_revision = "f065c01a7230"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "effective_configs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "resource_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "policy_type",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "resolved_config",
            postgresql.JSONB(),
            nullable=False,
        ),
        sa.Column(
            "resolution_trace",
            postgresql.JSONB(),
            nullable=False,
        ),
        sa.Column(
            "calculated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "revision",
            sa.Integer(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name="effective_configs_pkey",
        ),
        sa.ForeignKeyConstraint(
            ["resource_id"],
            ["inventory.resources.id"],
        ),
        sa.UniqueConstraint(
            "resource_id",
            "policy_type",
            name="uq_effective_configs_resource_policy_type",
        ),
        sa.CheckConstraint(
            "length(btrim(policy_type)) > 0",
            name="ck_effective_configs_policy_type_not_empty",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(resolved_config) = 'object'",
            name="ck_effective_configs_resolved_config_object",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(resolution_trace) = 'object'",
            name="ck_effective_configs_resolution_trace_object",
        ),
        sa.CheckConstraint(
            "revision > 0",
            name="ck_effective_configs_revision_positive",
        ),
        schema="inventory",
    )


def downgrade() -> None:
    op.drop_table(
        "effective_configs",
        schema="inventory",
    )
