import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Numeric,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    true,
    text,
)
from sqlalchemy.dialects.postgresql import ExcludeConstraint, JSONB, UUID
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


class ResourceIdentifier(Base):
    """Identificador contextual e temporal de um recurso."""

    __tablename__ = "resource_identifiers"
    __table_args__ = (
        CheckConstraint(
            "last_seen_at >= first_seen_at",
            name="ck_resource_identifiers_seen_order",
        ),
        CheckConstraint(
            "valid_until IS NULL OR valid_until > valid_from",
            name="ck_resource_identifiers_validity",
        ),
        CheckConstraint(
            "jsonb_typeof(evidence) = 'object'",
            name="ck_resource_identifiers_evidence_object",
        ),
        CheckConstraint(
            "confidence IS NULL OR "
            "(confidence >= 0 AND confidence <= 1)",
            name="ck_resource_identifiers_confidence",
        ),
        Index(
            "ix_resource_identifiers_lookup",
            "identifier_type",
            "normalized_value",
            "namespace",
        ),
        Index(
            "ix_resource_identifiers_resource_validity",
            "resource_id",
            "valid_until",
        ),
        Index(
            "ix_resource_identifiers_source",
            "source_type",
            "source_instance",
        ),
        {"schema": "inventory"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    resource_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("inventory.resources.id"),
        nullable=False,
    )

    identifier_type: Mapped[str] = mapped_column(
        String(64), nullable=False,
    )

    identifier_value: Mapped[str] = mapped_column(
        Text, nullable=False,
    )

    normalized_value: Mapped[str] = mapped_column(
        Text, nullable=False,
    )

    namespace: Mapped[str | None] = mapped_column(
        String(255), nullable=True,
    )

    source_type: Mapped[str] = mapped_column(
        String(64), nullable=False,
    )

    source_instance: Mapped[str | None] = mapped_column(
        String(255), nullable=True,
    )

    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    verification_status: Mapped[str] = mapped_column(
        String(32), nullable=False,
    )

    confidence: Mapped[float | None] = mapped_column(
        Numeric(5, 4),
        nullable=True,
    )

    evidence: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    valid_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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


class ResourceRelation(Base):
    """Relação tipada, dirigida e temporal entre recursos."""

    __tablename__ = "resource_relations"
    __table_args__ = (
        CheckConstraint(
            "source_resource_id <> target_resource_id",
            name="ck_resource_relations_no_self",
        ),
        CheckConstraint(
            "valid_until IS NULL OR valid_until > valid_from",
            name="ck_resource_relations_validity",
        ),
        CheckConstraint(
            "jsonb_typeof(evidence) = 'object'",
            name="ck_resource_relations_evidence_object",
        ),
        CheckConstraint(
            "updated_at >= created_at",
            name="ck_resource_relations_timestamps",
        ),
        Index(
            "ix_resource_relations_source_type",
            "source_resource_id",
            "relation_type",
        ),
        Index(
            "ix_resource_relations_target_type",
            "target_resource_id",
            "relation_type",
        ),
        Index(
            "ix_resource_relations_type_validity",
            "relation_type",
            "valid_until",
        ),
        {"schema": "inventory"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    source_resource_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("inventory.resources.id"),
        nullable=False,
    )

    target_resource_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("inventory.resources.id"),
        nullable=False,
    )

    relation_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    source_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    source_instance: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    evidence: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    valid_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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


class Group(Base):
    """Grupo estático ou dinâmico de recursos."""

    __tablename__ = "groups"
    __table_args__ = (
        CheckConstraint(
            "group_type IN ('static', 'dynamic')",
            name="ck_groups_type",
        ),
        CheckConstraint(
            "updated_at >= created_at",
            name="ck_groups_timestamps",
        ),
        Index(
            "uq_groups_active_name",
            "name",
            unique=True,
            postgresql_where=text("archived_at IS NULL"),
        ),
        {"schema": "inventory"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    group_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
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



class GroupMembership(Base):
    """Associação temporal de um recurso a um grupo."""

    __tablename__ = "group_memberships"
    __table_args__ = (
        CheckConstraint(
            "membership_source IN ('manual', 'rule')",
            name="ck_group_memberships_source",
        ),
        CheckConstraint(
            "valid_until IS NULL OR valid_until > valid_from",
            name="ck_group_memberships_validity",
        ),
        ExcludeConstraint(
            ("group_id", "="),
            ("resource_id", "="),
            ("membership_source", "="),
            (
                text(
                    "tstzrange("
                    "valid_from, valid_until, '[)'"
                    ")"
                ),
                "&&",
            ),
            name="ex_group_memberships_no_overlap",
            using="gist",
        ),
        {"schema": "inventory"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("inventory.groups.id"),
        nullable=False,
    )

    resource_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("inventory.resources.id"),
        nullable=False,
    )

    membership_source: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    valid_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )


class GroupRule(Base):
    """Definição declarativa de uma regra de grupo dinâmico."""

    __tablename__ = "group_rules"
    __table_args__ = (
        CheckConstraint(
            "jsonb_typeof(rule_definition) = 'object'",
            name="ck_group_rules_definition_object",
        ),
        CheckConstraint(
            "updated_at >= created_at",
            name="ck_group_rules_timestamps",
        ),
        {"schema": "inventory"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("inventory.groups.id"),
        nullable=False,
    )

    rule_definition: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    enabled: Mapped[bool] = mapped_column(
        nullable=False,
        default=True,
        server_default=text("true"),
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


class Tag(Base):
    """Etiqueta normalizada do inventário LiveNet v2."""

    __tablename__ = "tags"
    __table_args__ = (
        CheckConstraint(
            "key = lower(btrim(key)) AND length(key) > 0",
            name="ck_tags_key_normalized",
        ),
        CheckConstraint(
            "value = btrim(value) AND length(value) > 0",
            name="ck_tags_value_normalized",
        ),
        CheckConstraint(
            "updated_at >= created_at",
            name="ck_tags_timestamps",
        ),
        UniqueConstraint(
            "key",
            "value",
            name="uq_tags_key_value",
        ),
        {"schema": "inventory"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    key: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    value: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
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


class ResourceTag(Base):
    """Associação temporal de uma etiqueta a um recurso."""

    __tablename__ = "resource_tags"
    __table_args__ = (
        CheckConstraint(
            "assignment_source IN ('manual', 'discovery', 'policy')",
            name="ck_resource_tags_source",
        ),
        CheckConstraint(
            "valid_until IS NULL OR valid_until > valid_from",
            name="ck_resource_tags_validity",
        ),
        ExcludeConstraint(
            ("resource_id", "="),
            ("tag_id", "="),
            ("assignment_source", "="),
            (
                text(
                    "tstzrange("
                    "valid_from, valid_until, '[)'"
                    ")"
                ),
                "&&",
            ),
            name="ex_resource_tags_no_overlap",
            using="gist",
        ),
        Index(
            "ix_resource_tags_resource_valid_until",
            "resource_id",
            "valid_until",
        ),
        Index(
            "ix_resource_tags_tag_valid_until",
            "tag_id",
            "valid_until",
        ),
        {"schema": "inventory"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    resource_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("inventory.resources.id"),
        nullable=False,
    )

    tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("inventory.tags.id"),
        nullable=False,
    )

    assignment_source: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    valid_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )


class Policy(Base):
    """Catálogo de políticas do inventário LiveNet v2."""

    __tablename__ = "policies"
    __table_args__ = (
        CheckConstraint(
            "length(btrim(name)) > 0",
            name="ck_policies_name_not_empty",
        ),
        CheckConstraint(
            "policy_type = lower(btrim(policy_type)) "
            "AND length(policy_type) > 0",
            name="ck_policies_type_normalized",
        ),
        CheckConstraint(
            "updated_at >= created_at",
            name="ck_policies_timestamps",
        ),
        CheckConstraint(
            "archived_at IS NULL OR archived_at >= created_at",
            name="ck_policies_archived_at",
        ),
        {"schema": "inventory"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    policy_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
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



class PolicyVersion(Base):
    """Versão imutável de uma política do inventário."""

    __tablename__ = "policy_versions"
    __table_args__ = (
        CheckConstraint(
            "version > 0",
            name="ck_policy_versions_version_positive",
        ),
        CheckConstraint(
            "jsonb_typeof(definition) = 'object'",
            name="ck_policy_versions_definition_object",
        ),
        UniqueConstraint(
            "policy_id",
            "version",
            name="uq_policy_versions_policy_version",
        ),
        {"schema": "inventory"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("inventory.policies.id"),
        nullable=False,
    )

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    definition: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
