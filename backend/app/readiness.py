"""Readiness contract only. No PostgreSQL adapter or connection is installed.

A future trusted checker must perform bounded read-only observations on a fresh
connection. A synthetic checker is useful for tests, never operational evidence.
"""

from dataclasses import dataclass, fields
from time import monotonic

from flask import jsonify


@dataclass(frozen=True)
class RequiredPrivileges:
    """Effective rights for the existing ORM operations, not arbitrary labels."""
    users_select: bool
    grants_select: bool
    sessions_select: bool
    sessions_insert: bool
    sessions_update_activity: bool
    sessions_update_revocation: bool
    throttles_select: bool
    throttles_insert: bool
    throttles_update: bool
    audit_insert: bool
    inventory_select: bool
    users_row_lock: bool
    sessions_row_lock: bool


@dataclass(frozen=True)
class AdministrativePrivileges:
    superuser: bool
    createdb: bool
    createrole: bool
    replication: bool
    bypassrls: bool
    role_membership: bool
    privileged_routine_execute: bool
    user_credential_update: bool
    role_grants_write: bool
    audit_mutation: bool


@dataclass(frozen=True)
class OwnershipPrivileges:
    database: bool
    schemas: bool
    relations: bool
    routines: bool


@dataclass(frozen=True)
class DDLPrivileges:
    database_create: bool
    database_temporary: bool
    public_create: bool
    security_create: bool
    inventory_create: bool
    audit_create: bool
    other_schema_create: bool


@dataclass(frozen=True)
class PrivilegeEvidence:
    target: tuple
    required: RequiredPrivileges
    administrative: AdministrativePrivileges
    ownership: OwnershipPrivileges
    ddl: DDLPrivileges


def _all_fields(value, expected_type, expected_value):
    return (type(value) is expected_type
            and all(getattr(value, f.name) is expected_value for f in fields(expected_type)))


def _same_target(value, expected):
    return (type(value) is tuple and len(value) == 4
            and all(type(v) is str and v for v in (value[0], value[2], value[3]))
            and type(value[1]) is int and value == expected)


def _privileges_valid(evidence, target):
    return (type(evidence) is PrivilegeEvidence
            and _same_target(evidence.target, target)
            and _all_fields(evidence.required, RequiredPrivileges, True)
            and _all_fields(evidence.administrative, AdministrativePrivileges, False)
            and _all_fields(evidence.ownership, OwnershipPrivileges, False)
            and _all_fields(evidence.ddl, DDLPrivileges, False))


@dataclass(frozen=True)
class ReadinessObservation:
    target: tuple  # host, port, database, PostgreSQL user
    observed_at: float  # monotonic observation time, not a client timestamp
    connected: bool
    read_only: bool
    schemas: frozenset
    application_revision: str
    security_revision: str
    privileges: PrivilegeEvidence | None = None


def install_readiness(app, *, target, checker=None):
    @app.get("/api/v1/ready")
    def ready():
        available = False
        if app.config.get("SECURITY_ENABLED") is True and checker is not None:
            try:
                observation = checker()
                available = (
                    type(observation) is ReadinessObservation
                    and _same_target(observation.target, target)
                    and type(observation.observed_at) in (int, float)
                    and 0 <= monotonic() - observation.observed_at <= 5
                    and observation.connected is True and observation.read_only is True
                    and type(observation.schemas) is frozenset
                    and all(type(s) is str for s in observation.schemas)
                    and {"inventory", "audit", "security"} <= observation.schemas
                    and type(observation.application_revision) is str
                    and observation.application_revision == "f066a01a7230"
                    and type(observation.security_revision) is str
                    and observation.security_revision == "b12b01a7230"
                    and _privileges_valid(observation.privileges, target)
                )
            except Exception:
                # Driver errors may contain secrets. No diagnostics in HTTP/logs.
                available = False
        response = jsonify(status="ready" if available else "unavailable")
        response.status_code = 200 if available else 503
        response.headers["Cache-Control"] = "no-store"
        return response
