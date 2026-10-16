"""Testes estruturais do catálogo de etiquetas INV-05A."""

from sqlalchemy import CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.core.models import Base
from app.core import model_registry
from app.inventory.models import Tag


def test_tag_registered_in_metadata():
    assert model_registry.Tag is Tag
    assert Base.metadata.tables["inventory.tags"] is Tag.__table__


def test_tag_table_identity():
    assert Tag.__tablename__ == "tags"
    assert Tag.__table__.schema == "inventory"


def test_tag_columns():
    assert set(Tag.__table__.columns.keys()) == {
        "id",
        "key",
        "value",
        "description",
        "created_at",
        "updated_at",
    }


def test_tag_primary_key():
    column = Tag.__table__.c.id
    assert column.primary_key
    assert isinstance(column.type, UUID)


def test_tag_required_columns():
    columns = Tag.__table__.c

    for name in ("id", "key", "value", "created_at", "updated_at"):
        assert not columns[name].nullable

    assert columns.description.nullable


def test_tag_string_lengths():
    columns = Tag.__table__.c

    assert columns.key.type.length == 128
    assert columns.value.type.length == 255


def test_tag_unique_key_value():
    constraints = [
        constraint
        for constraint in Tag.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    ]

    assert len(constraints) == 1
    assert constraints[0].name == "uq_tags_key_value"
    assert set(constraints[0].columns.keys()) == {"key", "value"}


def test_tag_check_constraints():
    checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in Tag.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert checks == {
        "ck_tags_key_normalized":
            "key = lower(btrim(key)) AND length(key) > 0",
        "ck_tags_value_normalized":
            "value = btrim(value) AND length(value) > 0",
        "ck_tags_timestamps":
            "updated_at >= created_at",
    }


def test_tag_timestamp_defaults():
    columns = Tag.__table__.c

    for name in ("created_at", "updated_at"):
        column = columns[name]
        assert column.default is not None
        assert column.server_default is not None
        assert column.type.timezone is True
