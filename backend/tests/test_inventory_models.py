from sqlalchemy import CheckConstraint, Index

from app.core.models import Base
from app.inventory.models import Resource


def test_resource_registered_in_metadata():
    assert "inventory.resources" in Base.metadata.tables
    assert Resource.__table__.schema == "inventory"


def test_resource_primary_key():
    primary_keys = {
        column.name
        for column in Resource.__table__.primary_key.columns
    }

    assert primary_keys == {"id"}


def test_resource_required_columns():
    required = {
        "id",
        "resource_type",
        "display_name",
        "administrative_state",
        "attributes",
        "created_at",
        "updated_at",
        "row_version",
    }

    for name in required:
        assert Resource.__table__.columns[name].nullable is False


def test_resource_constraints():
    names = {
        constraint.name
        for constraint in Resource.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert {
        "ck_resources_administrative_state",
        "ck_resources_attributes_object",
        "ck_resources_timestamps",
        "ck_resources_row_version",
    }.issubset(names)


def test_resource_indexes():
    names = {
        index.name
        for index in Resource.__table__.indexes
        if isinstance(index, Index)
    }

    assert "ix_resources_type_state" in names


def test_resource_optimistic_versioning():
    assert (
        Resource.__mapper__.version_id_col
        is Resource.__table__.c.row_version
    )
