"""Testes estruturais do modelo inventory.group_memberships."""

from sqlalchemy import CheckConstraint
from sqlalchemy.dialects.postgresql import ExcludeConstraint

from app.core.models import Base
from app.inventory.models import GroupMembership


def test_table_registered():
    assert GroupMembership.__table__.fullname == (
        "inventory.group_memberships"
    )
    assert "inventory.group_memberships" in Base.metadata.tables


def test_columns():
    assert set(GroupMembership.__table__.columns.keys()) == {
        "id",
        "group_id",
        "resource_id",
        "membership_source",
        "valid_from",
        "valid_until",
        "created_at",
    }


def test_primary_key():
    table = GroupMembership.__table__
    assert {column.name for column in table.primary_key} == {"id"}


def test_required_columns():
    table = GroupMembership.__table__
    for name in (
        "id",
        "group_id",
        "resource_id",
        "membership_source",
        "valid_from",
        "created_at",
    ):
        assert table.c[name].nullable is False


def test_optional_valid_until():
    assert GroupMembership.__table__.c.valid_until.nullable is True


def test_foreign_keys():
    table = GroupMembership.__table__

    foreign_keys = {
        fk.parent.name: fk.target_fullname
        for fk in table.foreign_keys
    }

    assert foreign_keys == {
        "group_id": "inventory.groups.id",
        "resource_id": "inventory.resources.id",
    }

    assert all(
        fk.ondelete is None
        for fk in table.foreign_keys
    )


def test_source_check():
    checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in GroupMembership.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert checks["ck_group_memberships_source"] == (
        "membership_source IN ('manual', 'rule')"
    )


def test_validity_check():
    checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in GroupMembership.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert checks["ck_group_memberships_validity"] == (
        "valid_until IS NULL OR valid_until > valid_from"
    )


def test_exclusion_constraint():
    exclusions = [
        constraint
        for constraint in GroupMembership.__table__.constraints
        if isinstance(constraint, ExcludeConstraint)
    ]

    assert len(exclusions) == 1
    assert exclusions[0].name == "ex_group_memberships_no_overlap"
    assert exclusions[0].using == "gist"

    expressions = [
        (name or str(expression), operator)
        for expression, name, operator in exclusions[0]._render_exprs
    ]

    assert expressions == [
        ("group_id", "="),
        ("resource_id", "="),
        ("membership_source", "="),
        ("tstzrange(valid_from, valid_until, '[)')", "&&"),
    ]


def test_created_at_default():
    column = GroupMembership.__table__.c.created_at

    assert column.default is not None
    assert column.server_default is not None
