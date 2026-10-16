"""Testes estruturais das versões de políticas INV-06A."""

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.core import model_registry
from app.core.models import Base
from app.inventory.models import PolicyVersion


def test_policy_version_registered_in_metadata():
    assert model_registry.PolicyVersion is PolicyVersion
    assert Base.metadata.tables["inventory.policy_versions"] is PolicyVersion.__table__


def test_policy_version_table_identity():
    assert PolicyVersion.__tablename__ == "policy_versions"
    assert PolicyVersion.__table__.schema == "inventory"


def test_policy_version_columns():
    assert set(PolicyVersion.__table__.columns.keys()) == {
        "id",
        "policy_id",
        "version",
        "definition",
        "created_at",
        "created_by",
    }


def test_policy_version_primary_key():
    column = PolicyVersion.__table__.c.id
    assert column.primary_key
    assert isinstance(column.type, UUID)
    assert column.default is not None


def test_policy_version_nullability():
    columns = PolicyVersion.__table__.c

    for name in ("id", "policy_id", "version", "definition", "created_at"):
        assert not columns[name].nullable

    assert columns.created_by.nullable


def test_policy_version_foreign_key():
    constraints = [
        constraint
        for constraint in PolicyVersion.__table__.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    ]

    assert len(constraints) == 1
    fk = constraints[0]
    assert list(fk.columns.keys()) == ["policy_id"]
    assert next(iter(fk.elements)).target_fullname == "inventory.policies.id"
    assert fk.ondelete is None


def test_policy_version_unique_constraint():
    constraints = [
        constraint
        for constraint in PolicyVersion.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    ]

    assert len(constraints) == 1
    assert constraints[0].name == "uq_policy_versions_policy_version"
    assert set(constraints[0].columns.keys()) == {"policy_id", "version"}


def test_policy_version_check_constraints():
    checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in PolicyVersion.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert checks == {
        "ck_policy_versions_version_positive": "version > 0",
        "ck_policy_versions_definition_object":
            "jsonb_typeof(definition) = 'object'",
    }


def test_policy_version_definition_jsonb():
    column = PolicyVersion.__table__.c.definition

    assert isinstance(column.type, JSONB)
    assert column.default is None
    assert column.server_default is None


def test_policy_version_created_at():
    column = PolicyVersion.__table__.c.created_at

    assert column.type.timezone is True
    assert column.default is not None
    assert column.server_default is not None


def test_policy_version_created_by():
    column = PolicyVersion.__table__.c.created_by

    assert isinstance(column.type, UUID)
    assert not column.foreign_keys
    assert column.default is None
