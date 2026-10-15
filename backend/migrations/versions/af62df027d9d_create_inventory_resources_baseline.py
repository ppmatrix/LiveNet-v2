"""create inventory resources baseline

Revision ID: af62df027d9d
Revises:
Create Date: 2026-10-15 22:06:18.398424

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'af62df027d9d'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the initial inventory schema and resources table."""
    op.execute("CREATE SCHEMA inventory")

    op.create_table(
        "resources",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "resource_type",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "display_name",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "administrative_state",
            sa.String(length=32),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column(
            "attributes",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
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
        sa.Column(
            "archived_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "row_version",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "administrative_state IN "
            "('active', 'maintenance', 'disabled', 'archived')",
            name="ck_resources_administrative_state",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(attributes) = 'object'",
            name="ck_resources_attributes_object",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at",
            name="ck_resources_timestamps",
        ),
        sa.CheckConstraint(
            "row_version >= 1",
            name="ck_resources_row_version",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="inventory",
    )

    op.create_index(
        "ix_resources_type_state",
        "resources",
        ["resource_type", "administrative_state"],
        schema="inventory",
    )


def downgrade() -> None:
    """Remove only the objects created by this revision."""
    op.drop_index(
        "ix_resources_type_state",
        table_name="resources",
        schema="inventory",
    )
    op.drop_table("resources", schema="inventory")
    op.execute("DROP SCHEMA inventory")
