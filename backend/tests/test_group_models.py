import uuid

from sqlalchemy import CheckConstraint
from sqlalchemy.dialects import postgresql

from app.core.models import Base
from app.inventory.models import Group


def test_group_registered_in_metadata():
    table = Base.metadata.tables["inventory.groups"]

    assert table is Group.__table__
    assert table.schema == "inventory"
    assert len(table.columns) == 7


def test_group_column_names():
    assert set(Group.__table__.columns.keys()) == {
        "id",
        "name",
        "description",
        "group_type",
        "created_at",
        "updated_at",
        "archived_at",
    }


def test_group_primary_key():
    table = Group.__table__

    assert [column.name for column in table.primary_key.columns] == ["id"]
    assert isinstance(table.c.id.type, postgresql.UUID)


def test_group_required_columns():
    table = Group.__table__

    for name in (
        "id",
        "name",
        "group_type",
        "created_at",
        "updated_at",
    ):
        assert table.c[name].nullable is False


def test_group_optional_columns():
    table = Group.__table__

    assert table.c.description.nullable is True
    assert table.c.archived_at.nullable is True


def test_group_check_constraints():
    constraints = {
        constraint.name: str(constraint.sqltext)
        for constraint in Group.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert constraints == {
        "ck_groups_type": "group_type IN ('static', 'dynamic')",
        "ck_groups_timestamps": "updated_at >= created_at",
    }


def test_group_partial_unique_index():
    indexes = list(Group.__table__.indexes)

    assert len(indexes) == 1

    index = indexes[0]

    assert index.name == "uq_groups_active_name"
    assert index.unique is True
    assert [column.name for column in index.columns] == ["name"]

    predicate = index.dialect_options["postgresql"]["where"]
    assert str(predicate) == "archived_at IS NULL"


def test_group_defaults():
    table = Group.__table__

    assert table.c.id.default is not None
    assert table.c.created_at.server_default is not None
    assert table.c.updated_at.server_default is not None


def test_group_uuid_generated_by_application():
    group = Group(
        name="Grupo de teste",
        group_type="static",
    )

    assert group.name == "Grupo de teste"
    assert group.group_type == "static"

    # O default UUID é aplicado pelo SQLAlchemy durante o INSERT.
    assert group.id is None


def test_group_model_supports_archival():
    group = Group(
        id=uuid.uuid4(),
        name="Grupo arquivável",
        group_type="dynamic",
    )

    assert group.archived_at is None
    assert group.description is None
