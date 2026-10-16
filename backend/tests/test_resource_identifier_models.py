from sqlalchemy import CheckConstraint, UniqueConstraint

from app.core.models import Base
from app.inventory.models import ResourceIdentifier


def test_identifier_registered_in_metadata():
    table = Base.metadata.tables["inventory.resource_identifiers"]

    assert table is ResourceIdentifier.__table__
    assert table.schema == "inventory"
    assert len(table.columns) == 18


def test_identifier_primary_key():
    table = ResourceIdentifier.__table__

    assert {
        column.name for column in table.primary_key.columns
    } == {"id"}


def test_identifier_foreign_key():
    table = ResourceIdentifier.__table__

    foreign_keys = list(table.foreign_keys)

    assert len(foreign_keys) == 1
    assert foreign_keys[0].target_fullname == "inventory.resources.id"
    assert foreign_keys[0].ondelete is None


def test_identifier_required_columns():
    table = ResourceIdentifier.__table__

    required = {
        "id",
        "resource_id",
        "identifier_type",
        "identifier_value",
        "normalized_value",
        "source_type",
        "first_seen_at",
        "last_seen_at",
        "verification_status",
        "evidence",
        "valid_from",
        "created_at",
        "updated_at",
    }

    for name in required:
        assert table.columns[name].nullable is False


def test_identifier_constraints():
    table = ResourceIdentifier.__table__

    names = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert {
        "ck_resource_identifiers_seen_order",
        "ck_resource_identifiers_validity",
        "ck_resource_identifiers_evidence_object",
        "ck_resource_identifiers_confidence",
    }.issubset(names)


def test_identifier_indexes():
    indexes = {
        index.name: tuple(
            column.name for column in index.columns
        )
        for index in ResourceIdentifier.__table__.indexes
    }

    assert indexes == {
        "ix_resource_identifiers_lookup": (
            "identifier_type",
            "normalized_value",
            "namespace",
        ),
        "ix_resource_identifiers_resource_validity": (
            "resource_id",
            "valid_until",
        ),
        "ix_resource_identifiers_source": (
            "source_type",
            "source_instance",
        ),
    }


def test_identifier_has_no_global_unique_constraint():
    table = ResourceIdentifier.__table__

    unique_constraints = [
        constraint
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    ]

    assert unique_constraints == []

    assert all(
        not index.unique
        for index in table.indexes
    )


def test_identifier_numeric_confidence():
    column = ResourceIdentifier.__table__.c.confidence

    assert column.type.precision == 5
    assert column.type.scale == 4
    assert column.nullable is True
