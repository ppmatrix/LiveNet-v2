"""create inventory group memberships

Revision ID: ba06dd956da9
Revises: da34876e4210
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "ba06dd956da9"
down_revision: Union[str, Sequence[str], None] = "da34876e4210"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Necessária para igualdade UUID/VARCHAR em índices GiST.
    # Não remover automaticamente durante o downgrade.
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    op.create_table(
        "group_memberships",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "group_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("inventory.groups.id"),
            nullable=False,
        ),
        sa.Column(
            "resource_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("inventory.resources.id"),
            nullable=False,
        ),
        sa.Column(
            "membership_source",
            sa.String(32),
            nullable=False,
        ),
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
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "membership_source IN ('manual', 'rule')",
            name="ck_group_memberships_source",
        ),
        sa.CheckConstraint(
            "valid_until IS NULL OR valid_until > valid_from",
            name="ck_group_memberships_validity",
        ),
        postgresql.ExcludeConstraint(
            ("group_id", "="),
            ("resource_id", "="),
            ("membership_source", "="),
            (
                sa.text(
                    "tstzrange(valid_from, valid_until, '[)')"
                ),
                "&&",
            ),
            name="ex_group_memberships_no_overlap",
            using="gist",
        ),
        schema="inventory",
    )


def downgrade() -> None:
    op.drop_table(
        "group_memberships",
        schema="inventory",
    )

    # btree_gist permanece instalada intencionalmente.
