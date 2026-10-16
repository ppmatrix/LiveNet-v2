"""create inventory policies

Revision ID: c4a91e7b205d
Revises: 9e1b7c42a630
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c4a91e7b205d"
down_revision: Union[str, Sequence[str], None] = "9e1b7c42a630"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "policies",
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
            "policy_type",
            sa.String(64),
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
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
            "length(btrim(name)) > 0",
            name="ck_policies_name_not_empty",
        ),
        sa.CheckConstraint(
            "policy_type = lower(btrim(policy_type)) "
            "AND length(policy_type) > 0",
            name="ck_policies_type_normalized",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at",
            name="ck_policies_timestamps",
        ),
        sa.CheckConstraint(
            "archived_at IS NULL OR archived_at >= created_at",
            name="ck_policies_archived_at",
        ),
        schema="inventory",
    )


def downgrade() -> None:
    op.drop_table(
        "policies",
        schema="inventory",
    )
