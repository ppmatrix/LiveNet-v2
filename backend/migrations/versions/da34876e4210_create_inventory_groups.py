"""create inventory groups

Revision ID: da34876e4210
Revises: 38d641dcd780
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "da34876e4210"
down_revision: Union[str, Sequence[str], None] = "38d641dcd780"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "groups",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.String(255),
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "group_type",
            sa.String(32),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "archived_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.CheckConstraint(
            "group_type IN ('static', 'dynamic')",
            name="ck_groups_type",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at",
            name="ck_groups_timestamps",
        ),
        schema="inventory",
    )

    op.create_index(
        "uq_groups_active_name",
        "groups",
        ["name"],
        unique=True,
        schema="inventory",
        postgresql_where=sa.text("archived_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_groups_active_name",
        table_name="groups",
        schema="inventory",
    )

    op.drop_table(
        "groups",
        schema="inventory",
    )
