"""create inventory tags

Revision ID: 7c4e2a91b605
Revises: 44e7eb855b5a
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "7c4e2a91b605"
down_revision: Union[str, Sequence[str], None] = "44e7eb855b5a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tags",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "key",
            sa.String(128),
            nullable=False,
        ),
        sa.Column(
            "value",
            sa.String(255),
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
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
        sa.CheckConstraint(
            "key = lower(btrim(key)) AND length(key) > 0",
            name="ck_tags_key_normalized",
        ),
        sa.CheckConstraint(
            "value = btrim(value) AND length(value) > 0",
            name="ck_tags_value_normalized",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at",
            name="ck_tags_timestamps",
        ),
        sa.UniqueConstraint(
            "key",
            "value",
            name="uq_tags_key_value",
        ),
        schema="inventory",
    )


def downgrade() -> None:
    op.drop_table(
        "tags",
        schema="inventory",
    )
