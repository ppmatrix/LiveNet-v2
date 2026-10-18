"""Testes estruturais das atribuições de políticas INV-06A."""

from sqlalchemy import CheckConstraint, ForeignKeyConstraint
from sqlalchemy.dialects.postgresql import ExcludeConstraint, UUID
from sqlalchemy.schema import AddConstraint
from sqlalchemy.dialects import postgresql

from app.core import model_registry
from app.core.models import Base
from app.inventory.models import PolicyAssignment


def test_policy_assignment_registered():
    assert model_registry.PolicyAssignment is PolicyAssignment
    assert (
        Base.metadata.tables["inventory.policy_assignments"]
        is PolicyAssignment.__table__
    )


def test_policy_assignment_identity():
    table = PolicyAssignment.__table__
    assert table.schema == "inventory"
    assert table.name == "policy_assignments"


def test_policy_assignment_columns():
    assert set(PolicyAssignment.__table__.columns.keys()) == {
        "id",
        "policy_version_id",
        "scope_type",
        "group_id",
        "resource_id",
        "priority",
        "valid_from",
        "valid_until",
        "created_at",
    }


def test_policy_assignment_primary_key():
    column = PolicyAssignment.__table__.c.id
    assert column.primary_key
    assert isinstance(column.type, UUID)
    assert column.default is not None


def test_policy_assignment_nullability():
    columns = PolicyAssignment.__table__.c

    required = (
        "id",
        "policy_version_id",
        "scope_type",
        "priority",
        "valid_from",
        "created_at",
    )
    for name in required:
        assert not columns[name].nullable

    for name in ("group_id", "resource_id", "valid_until"):
        assert columns[name].nullable


def test_policy_assignment_foreign_keys():
    constraints = [
        constraint
        for constraint in PolicyAssignment.__table__.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    ]

    assert len(constraints) == 3

    actual = {
        next(iter(fk.elements)).target_fullname
        for fk in constraints
    }
    assert actual == {
        "inventory.policy_versions.id",
        "inventory.groups.id",
        "inventory.resources.id",
    }

    assert all(fk.ondelete is None for fk in constraints)


def test_policy_assignment_checks():
    checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in PolicyAssignment.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert set(checks) == {
        "ck_policy_assignments_scope",
        "ck_policy_assignments_validity",
    }

    scope = checks["ck_policy_assignments_scope"]
    assert all(
        expression in scope
        for expression in (
            "scope_type = 'global'",
            "scope_type = 'group'",
            "scope_type = 'resource'",
            "group_id IS NULL",
            "group_id IS NOT NULL",
            "resource_id IS NULL",
            "resource_id IS NOT NULL",
        )
    )

    assert checks["ck_policy_assignments_validity"] == (
        "valid_until IS NULL OR valid_until > valid_from"
    )


def test_policy_assignment_exclusion_constraints():
    exclusions = {
        constraint.name: constraint
        for constraint in PolicyAssignment.__table__.constraints
        if isinstance(constraint, ExcludeConstraint)
    }

    assert set(exclusions) == {
        "ex_policy_assignments_global_overlap",
        "ex_policy_assignments_group_overlap",
        "ex_policy_assignments_resource_overlap",
    }

    expected = {
        "global": {"policy_version_id"},
        "group": {"policy_version_id", "group_id"},
        "resource": {"policy_version_id", "resource_id"},
    }

    for scope, columns in expected.items():
        constraint = exclusions[
            f"ex_policy_assignments_{scope}_overlap"
        ]
        assert constraint.using == "gist"
        assert f"scope_type = '{scope}'" in str(constraint.where)
        assert columns.issubset(set(constraint.columns.keys()))
        compiled = str(
            AddConstraint(constraint).compile(
                dialect=postgresql.dialect()
            )
        )
        assert "tstzrange" in compiled


def test_policy_assignment_timestamps():
    columns = PolicyAssignment.__table__.c

    for name in ("valid_from", "valid_until", "created_at"):
        assert columns[name].type.timezone is True

    assert columns.created_at.default is not None
    assert columns.created_at.server_default is not None
    assert columns.valid_from.default is None
    assert columns.valid_until.default is None


def test_policy_assignment_priority():
    column = PolicyAssignment.__table__.c.priority
    assert not column.nullable
    assert column.default is None
    assert column.server_default is None
