"""FIX1 adversarial evidence tests: no DB, secrets, sockets or operational auth."""
from dataclasses import fields, replace
from time import monotonic

import pytest
from flask import Flask

from app.readiness import (
    AdministrativePrivileges, DDLPrivileges, OwnershipPrivileges, PrivilegeEvidence,
    ReadinessObservation, RequiredPrivileges, install_readiness,
)


TARGET = ("dedicated-db", 5432, "offline_lab", "app_role")


def complete_privileges(target=TARGET):
    return PrivilegeEvidence(
        target, RequiredPrivileges(**{f.name: True for f in fields(RequiredPrivileges)}),
        AdministrativePrivileges(**{f.name: False for f in fields(AdministrativePrivileges)}),
        OwnershipPrivileges(**{f.name: False for f in fields(OwnershipPrivileges)}),
        DDLPrivileges(**{f.name: False for f in fields(DDLPrivileges)}),
    )


def complete_observation():
    return ReadinessObservation(TARGET, monotonic(), True, True,
                                frozenset({"inventory", "audit", "security"}),
                                "f066a01a7230", "b12b01a7230", complete_privileges())


def response(observation, *, enabled=True):
    app = Flask(__name__)
    # This flag drives the readiness contract only; no auth runtime is installed.
    app.config["SECURITY_ENABLED"] = enabled
    install_readiness(app, target=TARGET, checker=lambda: observation)
    return app.test_client().get("/api/v1/ready")


def assert_unavailable(observation):
    r = response(observation)
    assert r.status_code == 503
    assert r.json == {"status": "unavailable"}
    assert r.headers["Cache-Control"] == "no-store"


def test_complete_synthetic_observation_only_is_ready():
    r = response(complete_observation())
    assert r.status_code == 200 and r.json == {"status": "ready"}
    assert response(complete_observation(), enabled=False).status_code == 503


@pytest.mark.parametrize("field", [f.name for f in fields(RequiredPrivileges)])
@pytest.mark.parametrize("value", [False, None, "UNKNOWN", "true", 1, {}, frozenset()])
def test_every_required_capability_needs_exact_true(field, value):
    obs = complete_observation()
    evidence = replace(obs.privileges, required=replace(obs.privileges.required, **{field: value}))
    assert_unavailable(replace(obs, privileges=evidence))


NEGATIVE_FIELDS = [(name, f.name) for name, cls in [
    ("administrative", AdministrativePrivileges), ("ownership", OwnershipPrivileges), ("ddl", DDLPrivileges)
] for f in fields(cls)]


@pytest.mark.parametrize("section,field", NEGATIVE_FIELDS)
@pytest.mark.parametrize("value", [True, None, "UNKNOWN", "false", 0, {}, frozenset()])
def test_every_forbidden_capability_needs_exact_false(section, field, value):
    obs = complete_observation()
    group = replace(getattr(obs.privileges, section), **{field: value})
    evidence = replace(obs.privileges, **{section: group})
    assert_unavailable(replace(obs, privileges=evidence))


@pytest.mark.parametrize("section", ["required", "administrative", "ownership", "ddl"])
@pytest.mark.parametrize("value", [None, {}, (), frozenset(), True, "UNKNOWN"])
def test_empty_partial_untyped_sections_are_not_proof(section, value):
    obs = complete_observation()
    assert_unavailable(replace(obs, privileges=replace(obs.privileges, **{section: value})))


@pytest.mark.parametrize("value", [None, {}, frozenset({"security_select", "superuser"}), True, "UNKNOWN"])
def test_missing_or_label_only_evidence_is_rejected(value):
    assert_unavailable(replace(complete_observation(), privileges=value))


@pytest.mark.parametrize("target", [("other", 5432, "offline_lab", "app_role"),
                                   ("dedicated-db", 5432, "offline_lab", "bootstrap"),
                                   ("dedicated-db", 5432.0, "offline_lab", "app_role"),
                                   list(TARGET), None])
def test_privilege_evidence_binding_cannot_disagree_with_observation(target):
    obs = complete_observation()
    assert_unavailable(replace(obs, privileges=replace(obs.privileges, target=target)))


@pytest.mark.parametrize("field,value", [
    ("observed_at", monotonic() - 60), ("observed_at", monotonic() + 60),
    ("observed_at", float("nan")), ("observed_at", float("inf")), ("observed_at", True),
    ("target", ("other", 5432, "offline_lab", "app_role")),
    ("schemas", frozenset({"inventory", "security"})), ("schemas", ["inventory", "audit", "security"]),
    ("application_revision", "f067a01a7230"), ("security_revision", "wrong"),
    ("connected", False), ("read_only", False), ("read_only", "true"),
])
def test_invalid_observation_is_unavailable(field, value):
    assert_unavailable(replace(complete_observation(), **{field: value}))


def test_omitted_privilege_evidence_and_absent_observation():
    obs = complete_observation()
    assert_unavailable(ReadinessObservation(obs.target, obs.observed_at, obs.connected,
                       obs.read_only, obs.schemas, obs.application_revision, obs.security_revision))
    assert_unavailable(None)


def test_partial_negative_mapping_and_contradictory_superuser_are_rejected():
    obs = complete_observation()
    assert_unavailable(replace(obs, privileges=replace(obs.privileges,
                       administrative={"superuser": False})))
    # Every positive capability remains true; superuser nevertheless vetoes success.
    assert_unavailable(replace(obs, privileges=replace(obs.privileges,
                       administrative=replace(obs.privileges.administrative, superuser=True))))


def test_callback_exception_is_sanitized_and_never_repaired():
    app = Flask(__name__); app.config["SECURITY_ENABLED"] = True
    calls = []
    def failing():
        calls.append("read-only-observation")
        raise RuntimeError("synthetic-sensitive-detail")
    install_readiness(app, target=TARGET, checker=failing)
    r = app.test_client().get("/api/v1/ready")
    assert r.status_code == 503 and r.json == {"status": "unavailable"}
    assert b"sensitive" not in r.data and calls == ["read-only-observation"]
