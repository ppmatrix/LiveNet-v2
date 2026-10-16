"""Testes estruturais das associações temporais INV-05A."""

from sqlalchemy import CheckConstraint, ForeignKeyConstraint
from sqlalchemy.dialects.postgresql import ExcludeConstraint, UUID

from app.core.models import Base
from app.core import model_registry
from app.inventory.models import ResourceTag


def test_resource_tag_registered():
    assert model_registry.ResourceTag is ResourceTag
    assert Base.metadata.tables["inventory.resource_tags"] is ResourceTag.__table__


def test_resource_tag_identity():
    assert ResourceTag.__tablename__ == "resource_tags"
    assert ResourceTag.__table__.schema == "inventory"


def test_resource_tag_columns():
    assert set(ResourceTag.__table__.columns.keys()) == {
        "id",
        "resource_id",
        "tag_id",
        "assignment_source",
        "valid_from",
        "valid_until",
        "created_at",
    }


def test_resource_tag_primary_key():
    column = ResourceTag.__table__.c.id
    assert column.primary_key
    assert isinstance(column.type, UUID)


def test_resource_tag_nullability():
    columns = ResourceTag.__table__.c

    for name in (
        "id",
        "resource_id",
        "tag_id",
        "assignment_source",
        "valid_from",
        "created_at",
    ):
        assert not columns[name].nullable

    assert columns.valid_until.nullable


def test_resource_tag_foreign_keys():
    constraints = [
        constraint
        for constraint in ResourceTag.__table__.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    ]

    assert len(constraints) == 2

    targets = {
        fk.target_fullname
        for constraint in constraints
        for fk in constraint.elements
    }

    assert targets == {
        "inventory.resources.id",
        "inventory.tags.id",
    }

    assert all(constraint.ondelete is None for constraint in constraints)


def test_resource_tag_assignment_source():
    assert ResourceTag.__table__.c.assignment_source.type.length == 32

    checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in ResourceTag.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert checks["ck_resource_tags_source"] == (
        "assignment_source IN ('manual', 'discovery', 'policy')"
    )


def test_resource_tag_validity():
    checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in ResourceTag.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert checks["ck_resource_tags_validity"] == (
        "valid_until IS NULL OR valid_until > valid_from"
    )


def test_resource_tag_exclusion():
    exclusions = [
        constraint
        for constraint in ResourceTag.__table__.constraints
        if isinstance(constraint, ExcludeConstraint)
    ]

    assert len(exclusions) == 1

    constraint = exclusions[0]
    assert constraint.name == "ex_resource_tags_no_overlap"
    assert constraint.using == "gist"

    from sqlalchemy.schema import AddConstraint
    from sqlalchemy.dialects import postgresql

    sql = str(
        AddConstraint(constraint).compile(
            dialect=postgresql.dialect()
        )
    )

    for fragment in (
        "resource_id",
        "tag_id",
        "assignment_source",
        "tstzrange",
        "valid_from",
        "valid_until",
    ):
        assert fragment in sql


def test_resource_tag_indexes():
    indexes = {
        index.name: tuple(column.name for column in index.columns)
        for index in ResourceTag.__table__.indexes
    }

    assert indexes == {
        "ix_resource_tags_resource_valid_until":
            ("resource_id", "valid_until"),
        "ix_resource_tags_tag_valid_until":
            ("tag_id", "valid_until"),
    }


def test_resource_tag_created_at_default():
    column = ResourceTag.__table__.c.created_at

    assert column.default is not None
    assert column.server_default is not None
    assert column.type.timezone is True


def test_resource_tag_temporal_column_types():
    columns = ResourceTag.__table__.c

    assert columns.valid_from.type.timezone is True
    assert columns.valid_until.type.timezone is True
