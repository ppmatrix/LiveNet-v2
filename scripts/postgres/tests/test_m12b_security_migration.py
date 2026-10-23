from dataclasses import replace
from unittest.mock import Mock

import pytest

import m12b_security_migration as preparation
from security_migrations.contract import INITIAL_REVISION, TABLE_NAMES, VERSION_SCHEMA, VERSION_TABLE


@pytest.fixture
def target():
    return {"project": preparation.PROJECT, "database": preparation.DATABASE, "host": "db", "port": 5432,
            "system_identifier": preparation.SYSTEM_IDENTIFIER, "migration_user": "livenet_m12b_migrator",
            "application_user": "livenet_m12b_app"}


@pytest.fixture
def plan(target):
    return preparation.prepare_plan(target, confirmed_baseline=preparation.BASELINE)


@pytest.fixture
def before(plan):
    return preparation.ObservedState(
        database=plan.target.database, system_identifier=plan.target.system_identifier,
        current_user=plan.target.migration_user, session_user=plan.target.migration_user,
        server_version_num=160010, application_revisions=(preparation.BASELINE,), security_revisions=(),
        schemas=frozenset({"public", "inventory", "audit"}), relations=preparation.BASELINE_TABLES,
    )


@pytest.mark.parametrize("database", ["livenet", "livenet_f0_test", "livenet_auth03_test", "other"])
def test_reject_other_databases(target, database):
    target["database"] = database
    with pytest.raises(preparation.Refused):
        preparation.prepare_plan(target, confirmed_baseline=preparation.BASELINE)


@pytest.mark.parametrize("key,value", [
    ("project", "livenetv2-auth03-test"), ("host", "localhost"), ("port", 5433), ("port", True),
    ("system_identifier", ""), ("system_identifier", "automatic"), ("system_identifier", None),
    ("system_identifier", "18446744073709551616"),
    ("system_identifier", "1234567890123456789"),
    ("migration_user", "livenet"), ("application_user", "livenet_m12b_migrator"),
    ("database", []),
])
def test_incorrect_target_identity_rejected(target, key, value):
    target[key] = value
    with pytest.raises(preparation.Refused):
        preparation.validate_target(target)


@pytest.mark.parametrize("baseline", [None, "", "head", "f067a01a7230", "other"])
def test_baseline_confirmation_is_explicit(target, baseline):
    with pytest.raises(preparation.Refused):
        preparation.prepare_plan(target, confirmed_baseline=baseline)


def test_incomplete_or_credential_configuration_rejected(target):
    for config in (None, {}, {**target, "password": "not-an-operational-credential"}):
        with pytest.raises(preparation.Refused):
            preparation.validate_target(config)


def test_plan_is_deterministic_and_not_authorization(target, plan):
    other = preparation.prepare_plan(target, confirmed_baseline=preparation.BASELINE)
    assert other == plan
    assert plan.destination == INITIAL_REVISION and plan.source is None
    assert plan.application_revision == preparation.BASELINE
    assert (plan.version_schema, plan.version_table) == ("public", "alembic_security_version")
    assert len(plan.digest) == 64 and plan.required_search_path == ("public",)
    assert all("backend/migrations/" not in name and "auth03" not in name for name, _ in plan.sources)
    contract = preparation.execution_contract(plan)
    assert contract["execution_enabled"] is False
    assert contract["automatic_retry"] is False
    assert contract["operational_approval_required"] is True
    assert contract["application_credentials_are_authorization"] is False


def test_pre_and_post_observations(plan, before):
    assert preparation.validate_observation(plan, before, phase="before") is before
    after = replace(before, security_revisions=(INITIAL_REVISION,),
                    schemas=before.schemas | {"security"}, relations=before.relations |
                    {("security", name) for name in TABLE_NAMES} | {(VERSION_SCHEMA, VERSION_TABLE)})
    assert preparation.validate_observation(plan, after, phase="after") is after


@pytest.mark.parametrize("field,value", [
    ("database", "livenet"), ("system_identifier", "999"),
    ("current_user", "livenet_m12b_app"), ("session_user", "livenet"),
    ("server_version_num", 150000), ("server_version_num", 170000),
    ("application_revisions", ()), ("application_revisions", ("f067a01a7230",)),
    ("application_revisions", (preparation.BASELINE, "f067a01a7230")),
    ("security_revisions", (INITIAL_REVISION,)),
    ("schemas", frozenset({"public", "inventory", "audit", "authorization"})),
    ("schemas", frozenset({"public", "inventory", "audit", "security"})),
    ("relations", frozenset()),
])
def test_pre_observation_divergence_is_rejected(plan, before, field, value):
    with pytest.raises(preparation.Refused):
        preparation.validate_observation(plan, replace(before, **{field: value}), phase="before")


def test_unknown_extra_object_is_rejected(plan, before):
    with pytest.raises(preparation.Refused):
        preparation.validate_observation(plan, replace(before, relations=before.relations | {("public", "unexpected")}), phase="before")


def test_post_requires_revision_and_all_objects(plan, before):
    with pytest.raises(preparation.Refused):
        preparation.validate_observation(plan, before, phase="after")


def test_execution_is_always_blocked_before_any_access(plan):
    connection = Mock(side_effect=AssertionError("No database operations"))
    with pytest.raises(preparation.Refused, match="P1"):
        preparation.execute_security_migration(plan, connection)
    assert not connection.mock_calls


@pytest.mark.parametrize("field,value", [
    ("down_revision", "f066a01a7230"), ("down_revision", "f067a01a7230"),
    ("depends_on", "f066a01a7230"), ("depends_on", "f067a01a7230"),
    ("branch_labels", "application"),
])
def test_application_dependencies_are_rejected(field, value):
    path = next((preparation.ROOT / "backend/security_migrations/versions").glob("*.py"))
    source = path.read_text().replace(f"{field} = None", f"{field} = {value!r}")
    with pytest.raises(preparation.Refused):
        preparation.validate_security_graph([source])


def test_missing_or_multiple_revisions_rejected():
    for sources in ([], ["", ""]):
        with pytest.raises(preparation.Refused):
            preparation.validate_security_graph(sources)
