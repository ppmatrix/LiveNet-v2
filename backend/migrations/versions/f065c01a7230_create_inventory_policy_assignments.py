"""create inventory policy assignments

Revision ID: f065c01a7230
Revises: e65b01a7c230
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "f065c01a7230"
down_revision = "e65b01a7c230"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "policy_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "policy_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("scope_type", sa.String(32), nullable=False),
        sa.Column(
            "group_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "resource_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column(
            "valid_from",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "valid_until",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["policy_version_id"],
            ["inventory.policy_versions.id"],
        ),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["inventory.groups.id"],
        ),
        sa.ForeignKeyConstraint(
            ["resource_id"],
            ["inventory.resources.id"],
        ),
        sa.CheckConstraint(
            "(scope_type = 'global' AND group_id IS NULL "
            "AND resource_id IS NULL) OR "
            "(scope_type = 'group' AND group_id IS NOT NULL "
            "AND resource_id IS NULL) OR "
            "(scope_type = 'resource' AND group_id IS NULL "
            "AND resource_id IS NOT NULL)",
            name="ck_policy_assignments_scope",
        ),
        sa.CheckConstraint(
            "valid_until IS NULL OR valid_until > valid_from",
            name="ck_policy_assignments_validity",
        ),
        postgresql.ExcludeConstraint(
            ("policy_version_id", "="),
            (
                sa.text(
                    "tstzrange(valid_from, valid_until, '[)')"
                ),
                "&&",
            ),
            where=sa.text("scope_type = 'global'"),
            name="ex_policy_assignments_global_overlap",
            using="gist",
        ),
        postgresql.ExcludeConstraint(
            ("policy_version_id", "="),
            ("group_id", "="),
            (
                sa.text(
                    "tstzrange(valid_from, valid_until, '[)')"
                ),
                "&&",
            ),
            where=sa.text("scope_type = 'group'"),
            name="ex_policy_assignments_group_overlap",
            using="gist",
        ),
        postgresql.ExcludeConstraint(
            ("policy_version_id", "="),
            ("resource_id", "="),
            (
                sa.text(
                    "tstzrange(valid_from, valid_until, '[)')"
                ),
                "&&",
            ),
            where=sa.text("scope_type = 'resource'"),
            name="ex_policy_assignments_resource_overlap",
            using="gist",
        ),
        schema="inventory",
    )


def downgrade() -> None:
    op.drop_table("policy_assignments", schema="inventory")
