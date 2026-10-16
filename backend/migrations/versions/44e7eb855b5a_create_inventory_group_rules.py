"""create inventory group rules

Revision ID: 44e7eb855b5a
Revises: ba06dd956da9
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "44e7eb855b5a"
down_revision: Union[str, Sequence[str], None] = "ba06dd956da9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "group_rules",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "group_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "rule_definition",
            postgresql.JSONB(),
            nullable=False,
        ),
        sa.Column(
            "enabled",
            sa.Boolean(),
            server_default=sa.text("true"),
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
        sa.CheckConstraint(
            "jsonb_typeof(rule_definition) = 'object'",
            name="ck_group_rules_definition_object",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at",
            name="ck_group_rules_timestamps",
        ),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["inventory.groups.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="inventory",
    )


def downgrade() -> None:
    op.drop_table("group_rules", schema="inventory")
