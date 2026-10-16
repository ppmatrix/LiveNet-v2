"""create inventory resource relations

Revision ID: 38d641dcd780
Revises: 4f625db33d6d
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "38d641dcd780"
down_revision: Union[str, Sequence[str], None] = "4f625db33d6d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "resource_relations",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            primary_key=True, nullable=False,
        ),
        sa.Column(
            "source_resource_id", postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "target_resource_id", postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("relation_type", sa.String(64), nullable=False),
        sa.Column("source_type", sa.String(64), nullable=False),
        sa.Column("source_instance", sa.String(255), nullable=True),
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
            ["source_resource_id"],
            ["inventory.resources.id"],
        ),
        sa.ForeignKeyConstraint(
            ["target_resource_id"],
            ["inventory.resources.id"],
        ),
        sa.CheckConstraint(
            "source_resource_id <> target_resource_id",
            name="ck_resource_relations_no_self",
        ),
        sa.CheckConstraint(
            "valid_until IS NULL OR valid_until > valid_from",
            name="ck_resource_relations_validity",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(evidence) = 'object'",
            name="ck_resource_relations_evidence_object",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at",
            name="ck_resource_relations_timestamps",
        ),
        schema="inventory",
    )

    op.create_index(
        "ix_resource_relations_source_type",
        "resource_relations",
        ["source_resource_id", "relation_type"],
        schema="inventory",
    )

    op.create_index(
        "ix_resource_relations_target_type",
        "resource_relations",
        ["target_resource_id", "relation_type"],
        schema="inventory",
    )

    op.create_index(
        "ix_resource_relations_type_validity",
        "resource_relations",
        ["relation_type", "valid_until"],
        schema="inventory",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_resource_relations_type_validity",
        table_name="resource_relations",
        schema="inventory",
    )
    op.drop_index(
        "ix_resource_relations_target_type",
        table_name="resource_relations",
        schema="inventory",
    )
    op.drop_index(
        "ix_resource_relations_source_type",
        table_name="resource_relations",
        schema="inventory",
    )
    op.drop_table(
        "resource_relations",
        schema="inventory",
    )
