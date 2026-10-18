"""Modelos de auditoria centralizada do LiveNet v2."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Index,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base


def utc_now():
    return datetime.now(timezone.utc)


class AuditEvent(Base):
    """Evento imutável de auditoria centralizada."""

    __tablename__ = "events"

    __table_args__ = (
        CheckConstraint(
            "length(btrim(actor_type)) > 0",
            name="ck_audit_events_actor_type_not_empty",
        ),
        CheckConstraint(
            "length(btrim(action)) > 0",
            name="ck_audit_events_action_not_empty",
        ),
        CheckConstraint(
            "length(btrim(entity_type)) > 0",
            name="ck_audit_events_entity_type_not_empty",
        ),
        CheckConstraint(
            "length(btrim(outcome)) > 0",
            name="ck_audit_events_outcome_not_empty",
        ),
        CheckConstraint(
            "jsonb_typeof(changes) = 'object'",
            name="ck_audit_events_changes_object",
        ),
        CheckConstraint(
            "jsonb_typeof(context) = 'object'",
            name="ck_audit_events_context_object",
        ),
        Index(
            "ix_audit_events_occurred_at",
            "occurred_at",
        ),
        Index(
            "ix_audit_events_entity",
            "entity_type",
            "entity_id",
            "occurred_at",
        ),
        Index(
            "ix_audit_events_correlation",
            "correlation_id",
        ),
        {"schema": "audit"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )

    actor_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    action: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    entity_type: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    correlation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    request_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    outcome: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    changes: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    context: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
