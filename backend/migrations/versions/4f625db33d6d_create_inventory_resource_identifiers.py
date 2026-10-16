"""create inventory resource identifiers

Revision ID: 4f625db33d6d
Revises: af62df027d9d
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "4f625db33d6d"
down_revision: Union[str, Sequence[str], None] = "af62df027d9d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "resource_identifiers",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            primary_key=True, nullable=False,
        ),
        sa.Column(
            "resource_id", postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("identifier_type", sa.String(64), nullable=False),
        sa.Column("identifier_value", sa.Text(), nullable=False),
        sa.Column("normalized_value", sa.Text(), nullable=False),
        sa.Column("namespace", sa.String(255), nullable=True),
        sa.Column("source_type", sa.String(64), nullable=False),
        sa.Column("source_instance", sa.String(255), nullable=True),
        sa.Column(
            "first_seen_at", sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at", sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "verified_at", sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "verification_status", sa.String(32),
            nullable=False,
        ),
        sa.Column(
            "confidence", sa.Numeric(5, 4),
            nullable=True,
        ),
        sa.Column(
            "evidence", postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "valid_from", sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "valid_until", sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["resource_id"],
            ["inventory.resources.id"],
        ),
        sa.CheckConstraint(
            "last_seen_at >= first_seen_at",
            name="ck_resource_identifiers_seen_order",
        ),
        sa.CheckConstraint(
            "valid_until IS NULL OR valid_until > valid_from",
            name="ck_resource_identifiers_validity",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(evidence) = 'object'",
            name="ck_resource_identifiers_evidence_object",
        ),
        sa.CheckConstraint(
            "confidence IS NULL OR "
            "(confidence >= 0 AND confidence <= 1)",
            name="ck_resource_identifiers_confidence",
        ),
        schema="inventory",
    )

    op.create_index(
        "ix_resource_identifiers_lookup",
        "resource_identifiers",
        ["identifier_type", "normalized_value", "namespace"],
        schema="inventory",
    )

    op.create_index(
        "ix_resource_identifiers_resource_validity",
        "resource_identifiers",
        ["resource_id", "valid_until"],
        schema="inventory",
    )

    op.create_index(
        "ix_resource_identifiers_source",
        "resource_identifiers",
        ["source_type", "source_instance"],
        schema="inventory",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_resource_identifiers_source",
        table_name="resource_identifiers",
        schema="inventory",
    )
    op.drop_index(
        "ix_resource_identifiers_resource_validity",
        table_name="resource_identifiers",
        schema="inventory",
    )
    op.drop_index(
        "ix_resource_identifiers_lookup",
        table_name="resource_identifiers",
        schema="inventory",
    )
    op.drop_table(
        "resource_identifiers",
        schema="inventory",
    )
