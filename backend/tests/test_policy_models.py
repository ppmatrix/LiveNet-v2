"""Testes estruturais do catálogo de políticas INV-06A."""

from sqlalchemy import Boolean, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.core import model_registry
from app.core.models import Base
from app.inventory.models import Policy


def test_policy_registered_in_metadata():
    assert model_registry.Policy is Policy
    assert Base.metadata.tables["inventory.policies"] is Policy.__table__


def test_policy_table_identity():
    assert Policy.__tablename__ == "policies"
    assert Policy.__table__.schema == "inventory"


def test_policy_columns():
    assert set(Policy.__table__.columns.keys()) == {
        "id",
        "name",
        "policy_type",
        "description",
        "enabled",
        "created_at",
        "updated_at",
        "archived_at",
    }


def test_policy_primary_key():
    column = Policy.__table__.c.id
    assert column.primary_key
    assert isinstance(column.type, UUID)
    assert column.default is not None


def test_policy_nullability():
    columns = Policy.__table__.c

    for name in (
        "id",
        "name",
        "policy_type",
        "enabled",
        "created_at",
        "updated_at",
    ):
        assert not columns[name].nullable

    assert columns.description.nullable
    assert columns.archived_at.nullable


def test_policy_string_lengths():
    columns = Policy.__table__.c

    assert columns.name.type.length == 255
    assert columns.policy_type.type.length == 64


def test_policy_enabled_default():
    column = Policy.__table__.c.enabled

    assert isinstance(column.type, Boolean)
    assert column.default is not None
    assert column.default.arg is True
    assert column.server_default is not None


def test_policy_check_constraints():
    checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in Policy.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert checks == {
        "ck_policies_name_not_empty":
            "length(btrim(name)) > 0",
        "ck_policies_type_normalized":
            "policy_type = lower(btrim(policy_type)) "
            "AND length(policy_type) > 0",
        "ck_policies_timestamps":
            "updated_at >= created_at",
        "ck_policies_archived_at":
            "archived_at IS NULL OR archived_at >= created_at",
    }


def test_policy_no_name_uniqueness():
    unique_constraints = [
        constraint
        for constraint in Policy.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    ]

    assert unique_constraints == []


def test_policy_timestamp_types_and_defaults():
    columns = Policy.__table__.c

    for name in ("created_at", "updated_at", "archived_at"):
        assert columns[name].type.timezone is True

    for name in ("created_at", "updated_at"):
        assert columns[name].default is not None
        assert columns[name].server_default is not None

    assert columns.archived_at.default is None
    assert columns.archived_at.server_default is None
