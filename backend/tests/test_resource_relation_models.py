from sqlalchemy import CheckConstraint, UniqueConstraint

from app.core.models import Base
from app.inventory.models import ResourceRelation


def test_relation_registered_in_metadata():
    table = Base.metadata.tables["inventory.resource_relations"]

    assert table is ResourceRelation.__table__
    assert table.schema == "inventory"
    assert len(table.columns) == 11


def test_relation_primary_key():
    table = ResourceRelation.__table__

    assert {
        column.name for column in table.primary_key.columns
    } == {"id"}


def test_relation_foreign_keys():
    table = ResourceRelation.__table__

    foreign_keys = {
        fk.parent.name: fk
        for fk in table.foreign_keys
    }

    assert set(foreign_keys) == {
        "source_resource_id",
        "target_resource_id",
    }

    for fk in foreign_keys.values():
        assert fk.target_fullname == "inventory.resources.id"
        assert fk.ondelete is None


def test_relation_required_columns():
    table = ResourceRelation.__table__

    required = {
        "id",
        "source_resource_id",
        "target_resource_id",
        "relation_type",
        "source_type",
        "evidence",
        "valid_from",
        "created_at",
        "updated_at",
    }

    for name in required:
        assert table.columns[name].nullable is False


def test_relation_optional_columns():
    table = ResourceRelation.__table__

    optional = {
        "source_instance",
        "valid_until",
    }

    for name in optional:
        assert table.columns[name].nullable is True


def test_relation_constraints():
    table = ResourceRelation.__table__

    names = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert names == {
        "ck_resource_relations_no_self",
        "ck_resource_relations_validity",
        "ck_resource_relations_evidence_object",
        "ck_resource_relations_timestamps",
    }


def test_relation_indexes():
    table = ResourceRelation.__table__

    indexes = {
        index.name: tuple(
            column.name for column in index.columns
        )
        for index in table.indexes
    }

    assert indexes == {
        "ix_resource_relations_source_type": (
            "source_resource_id",
            "relation_type",
        ),
        "ix_resource_relations_target_type": (
            "target_resource_id",
            "relation_type",
        ),
        "ix_resource_relations_type_validity": (
            "relation_type",
            "valid_until",
        ),
    }


def test_relation_has_no_global_uniqueness():
    table = ResourceRelation.__table__

    unique_constraints = [
        constraint
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    ]

    assert unique_constraints == []
    assert all(not index.unique for index in table.indexes)


def test_relation_jsonb_default():
    table = ResourceRelation.__table__

    assert table.c.evidence.nullable is False
    assert table.c.evidence.server_default is not None


def test_relation_timestamps():
    table = ResourceRelation.__table__

    assert table.c.created_at.server_default is not None
    assert table.c.updated_at.server_default is not None
    assert table.c.valid_until.nullable is True
