"""Testes estruturais do modelo inventory.group_rules."""

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.core.models import Base
from app.inventory.models import GroupRule


def test_group_rule_registered():
    assert Base.metadata.tables["inventory.group_rules"] is GroupRule.__table__


def test_group_rule_schema_and_name():
    assert GroupRule.__table__.schema == "inventory"
    assert GroupRule.__tablename__ == "group_rules"


def test_group_rule_columns():
    assert set(GroupRule.__table__.columns.keys()) == {
        "id",
        "group_id",
        "rule_definition",
        "enabled",
        "created_at",
        "updated_at",
    }


def test_group_rule_primary_key():
    column = GroupRule.__table__.c.id
    assert column.primary_key
    assert isinstance(column.type, UUID)
    assert not column.nullable


def test_group_rule_foreign_key():
    column = GroupRule.__table__.c.group_id
    assert isinstance(column.type, UUID)
    assert not column.nullable

    foreign_keys = list(column.foreign_keys)
    assert len(foreign_keys) == 1
    assert isinstance(foreign_keys[0], ForeignKey)
    assert foreign_keys[0].target_fullname == "inventory.groups.id"
    assert foreign_keys[0].ondelete is None


def test_group_rule_definition():
    column = GroupRule.__table__.c.rule_definition
    assert isinstance(column.type, JSONB)
    assert not column.nullable


def test_group_rule_enabled():
    column = GroupRule.__table__.c.enabled
    assert isinstance(column.type, Boolean)
    assert not column.nullable
    assert column.default.arg is True
    assert str(column.server_default.arg).lower() == "true"


def test_group_rule_timestamps():
    for name in ("created_at", "updated_at"):
        column = GroupRule.__table__.c[name]
        assert isinstance(column.type, DateTime)
        assert column.type.timezone is True
        assert not column.nullable
        assert column.default is not None
        assert column.server_default is not None


def test_group_rule_constraints():
    constraints = {
        constraint.name: constraint
        for constraint in GroupRule.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert set(constraints) == {
        "ck_group_rules_definition_object",
        "ck_group_rules_timestamps",
    }

    assert (
        str(constraints["ck_group_rules_definition_object"].sqltext)
        == "jsonb_typeof(rule_definition) = 'object'"
    )
    assert (
        str(constraints["ck_group_rules_timestamps"].sqltext)
        == "updated_at >= created_at"
    )


def test_group_rule_no_unique_constraint():
    assert not any(
        constraint.__class__.__name__ == "UniqueConstraint"
        for constraint in GroupRule.__table__.constraints
    )
    assert not any(index.unique for index in GroupRule.__table__.indexes)
