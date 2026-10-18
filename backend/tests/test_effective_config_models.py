"""Testes estruturais do contrato F0.65D-C01."""

from sqlalchemy import (
    CheckConstraint,
    ForeignKeyConstraint,
    PrimaryKeyConstraint,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.core.models import Base
from app.core import model_registry
from app.inventory.models import EffectiveConfig


def test_effective_config_registered():
    assert model_registry.EffectiveConfig is EffectiveConfig
    assert "EffectiveConfig" in model_registry.__all__
    assert Base.metadata.tables["inventory.effective_configs"] is (
        EffectiveConfig.__table__
    )


def test_effective_config_schema_and_columns():
    table = EffectiveConfig.__table__
    assert table.schema == "inventory"
    assert set(table.columns.keys()) == {
        "id",
        "resource_id",
        "policy_type",
        "resolved_config",
        "resolution_trace",
        "calculated_at",
        "revision",
    }


def test_effective_config_nullability():
    table = EffectiveConfig.__table__
    assert all(not column.nullable for column in table.columns)


def test_effective_config_primary_key():
    table = EffectiveConfig.__table__
    pk = next(
        c for c in table.constraints
        if isinstance(c, PrimaryKeyConstraint)
    )
    assert [column.name for column in pk.columns] == ["id"]
    assert isinstance(table.c.id.type, UUID)


def test_effective_config_resource_foreign_key():
    table = EffectiveConfig.__table__
    fks = [
        c for c in table.constraints
        if isinstance(c, ForeignKeyConstraint)
    ]
    assert len(fks) == 1
    fk = fks[0]
    assert [column.name for column in fk.columns] == ["resource_id"]
    assert list(fk.elements)[0].target_fullname == (
        "inventory.resources.id"
    )
    assert fk.ondelete is None


def test_effective_config_unique_resource_policy_type():
    constraints = [
        c for c in EffectiveConfig.__table__.constraints
        if isinstance(c, UniqueConstraint)
    ]
    assert len(constraints) == 1
    assert constraints[0].name == (
        "uq_effective_configs_resource_policy_type"
    )
    assert [c.name for c in constraints[0].columns] == [
        "resource_id",
        "policy_type",
    ]


def test_effective_config_jsonb_columns():
    table = EffectiveConfig.__table__
    assert isinstance(table.c.resolved_config.type, JSONB)
    assert isinstance(table.c.resolution_trace.type, JSONB)
    assert table.c.resolved_config.server_default is None
    assert table.c.resolution_trace.server_default is None


def test_effective_config_check_constraints():
    checks = {
        c.name: str(c.sqltext)
        for c in EffectiveConfig.__table__.constraints
        if isinstance(c, CheckConstraint)
    }
    assert len(checks) == 4
    assert checks == {
        "ck_effective_configs_policy_type_not_empty":
            "length(btrim(policy_type)) > 0",
        "ck_effective_configs_resolved_config_object":
            "jsonb_typeof(resolved_config) = 'object'",
        "ck_effective_configs_resolution_trace_object":
            "jsonb_typeof(resolution_trace) = 'object'",
        "ck_effective_configs_revision_positive":
            "revision > 0",
    }


def test_effective_config_no_calculation_defaults():
    table = EffectiveConfig.__table__
    for name in (
        "policy_type",
        "resolved_config",
        "resolution_trace",
        "calculated_at",
        "revision",
    ):
        column = table.c[name]
        assert column.default is None
        assert column.server_default is None


def test_effective_config_constraint_count():
    assert len(EffectiveConfig.__table__.constraints) == 7
