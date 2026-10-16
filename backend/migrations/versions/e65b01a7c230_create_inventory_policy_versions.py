"""Create immutable inventory policy versions.

Revision ID: e65b01a7c230
Revises: c4a91e7b205d
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "e65b01a7c230"
down_revision = "c4a91e7b205d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "policy_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("policy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("definition", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint(
            "version > 0",
            name="ck_policy_versions_version_positive",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(definition) = 'object'",
            name="ck_policy_versions_definition_object",
        ),
        sa.ForeignKeyConstraint(
            ["policy_id"],
            ["inventory.policies.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "policy_id",
            "version",
            name="uq_policy_versions_policy_version",
        ),
        schema="inventory",
    )

    op.execute(
        """
        CREATE FUNCTION inventory.prevent_policy_version_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $function$
        BEGIN
            RAISE EXCEPTION
                'inventory.policy_versions is immutable: % is forbidden',
                TG_OP
                USING ERRCODE = '23514';
        END;
        $function$;
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_policy_versions_immutable
        BEFORE UPDATE OR DELETE
        ON inventory.policy_versions
        FOR EACH ROW
        EXECUTE FUNCTION inventory.prevent_policy_version_mutation();
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TRIGGER trg_policy_versions_immutable
        ON inventory.policy_versions;
        """
    )

    op.execute(
        """
        DROP FUNCTION inventory.prevent_policy_version_mutation();
        """
    )

    op.drop_table("policy_versions", schema="inventory")
