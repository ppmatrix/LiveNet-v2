import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base


def utc_now():
    return datetime.now(timezone.utc)


class Resource(Base):
    """Recurso central do inventário LiveNet v2."""

    __tablename__ = "resources"
    __table_args__ = (
        CheckConstraint(
            "administrative_state IN "
            "('active', 'maintenance', 'disabled', 'archived')",
            name="ck_resources_administrative_state",
        ),
        CheckConstraint(
            "jsonb_typeof(attributes) = 'object'",
            name="ck_resources_attributes_object",
        ),
        CheckConstraint(
            "updated_at >= created_at",
            name="ck_resources_timestamps",
        ),
        CheckConstraint(
            "row_version >= 1",
            name="ck_resources_row_version",
        ),
        Index(
            "ix_resources_type_state",
            "resource_type",
            "administrative_state",
        ),
        {"schema": "inventory"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    resource_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    display_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    administrative_state: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
        server_default=text("'active'"),
    )

    attributes: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )

    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    row_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
    )

    __mapper_args__ = {
        "version_id_col": row_version,
    }
