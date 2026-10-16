"""create inventory resource tags

Revision ID: 9e1b7c42a630
Revises: 7c4e2a91b605
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "9e1b7c42a630"
down_revision: Union[str, Sequence[str], None] = "7c4e2a91b605"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Necessária para igualdade UUID/VARCHAR em índices GiST.
    # Preservar a extensão durante o downgrade.
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    op.create_table(
        "resource_tags",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "resource_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("inventory.resources.id"),
            nullable=False,
        ),
        sa.Column(
            "tag_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("inventory.tags.id"),
            nullable=False,
        ),
        sa.Column(
            "assignment_source",
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
            "assignment_source IN ('manual', 'discovery', 'policy')",
            name="ck_resource_tags_source",
        ),
        sa.CheckConstraint(
            "valid_until IS NULL OR valid_until > valid_from",
            name="ck_resource_tags_validity",
        ),
        postgresql.ExcludeConstraint(
            ("resource_id", "="),
            ("tag_id", "="),
            ("assignment_source", "="),
            (
                sa.text(
                    "tstzrange(valid_from, valid_until, '[)')"
                ),
                "&&",
            ),
            name="ex_resource_tags_no_overlap",
            using="gist",
        ),
        schema="inventory",
    )

    op.create_index(
        "ix_resource_tags_resource_valid_until",
        "resource_tags",
        ["resource_id", "valid_until"],
        schema="inventory",
    )

    op.create_index(
        "ix_resource_tags_tag_valid_until",
        "resource_tags",
        ["tag_id", "valid_until"],
        schema="inventory",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_resource_tags_tag_valid_until",
        table_name="resource_tags",
        schema="inventory",
    )

    op.drop_index(
        "ix_resource_tags_resource_valid_until",
        table_name="resource_tags",
        schema="inventory",
    )

    op.drop_table(
        "resource_tags",
        schema="inventory",
    )

    # btree_gist permanece instalada intencionalmente.
