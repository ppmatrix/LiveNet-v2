"""Create audit events baseline.

Revision ID: f066a01a7230
Revises: f065d01a7230
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "f066a01a7230"
down_revision = "f065d01a7230"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA audit")

    op.create_table(
        "events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "actor_type",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "actor_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "action",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column(
            "entity_type",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column(
            "entity_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "correlation_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "request_id",
            sa.String(length=128),
            nullable=True,
        ),
        sa.Column(
            "outcome",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "changes",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "context",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name="audit_events_pkey",
        ),
        sa.CheckConstraint(
            "length(btrim(actor_type)) > 0",
            name="ck_audit_events_actor_type_not_empty",
        ),
        sa.CheckConstraint(
            "length(btrim(action)) > 0",
            name="ck_audit_events_action_not_empty",
        ),
        sa.CheckConstraint(
            "length(btrim(entity_type)) > 0",
            name="ck_audit_events_entity_type_not_empty",
        ),
        sa.CheckConstraint(
            "length(btrim(outcome)) > 0",
            name="ck_audit_events_outcome_not_empty",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(changes) = 'object'",
            name="ck_audit_events_changes_object",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(context) = 'object'",
            name="ck_audit_events_context_object",
        ),
        schema="audit",
    )

    op.create_index(
        "ix_audit_events_occurred_at",
        "events",
        ["occurred_at"],
        schema="audit",
    )

    op.create_index(
        "ix_audit_events_entity",
        "events",
        ["entity_type", "entity_id", "occurred_at"],
        schema="audit",
    )

    op.create_index(
        "ix_audit_events_correlation",
        "events",
        ["correlation_id"],
        schema="audit",
    )

    op.execute("""
        CREATE FUNCTION audit.prevent_event_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY INVOKER
        AS $$
        BEGIN
            RAISE EXCEPTION
                'audit.events is immutable: % not permitted',
                TG_OP;
        END;
        $$;
    """)

    op.execute("""
        CREATE TRIGGER trg_audit_events_immutable
        BEFORE UPDATE OR DELETE ON audit.events
        FOR EACH ROW
        EXECUTE FUNCTION audit.prevent_event_mutation();
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER trg_audit_events_immutable "
        "ON audit.events"
    )

    op.execute(
        "DROP FUNCTION audit.prevent_event_mutation()"
    )

    op.drop_index(
        "ix_audit_events_correlation",
        table_name="events",
        schema="audit",
    )

    op.drop_index(
        "ix_audit_events_entity",
        table_name="events",
        schema="audit",
    )

    op.drop_index(
        "ix_audit_events_occurred_at",
        table_name="events",
        schema="audit",
    )

    op.drop_table("events", schema="audit")
    op.execute("DROP SCHEMA audit")
