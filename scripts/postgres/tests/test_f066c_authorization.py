"""Testes do modelo de autorizacao administrativa F0.66C."""

from dataclasses import FrozenInstanceError, replace
from uuid import UUID

import pytest

from f066c_admin_operations import ADMIN_OPERATIONS
from f066c_authorization import (
    ISOLATED_TARGET,
    create_authorization,
    validate_authorization,
)
from f066c_execution_plan import prepare_execution_plan


@pytest.mark.parametrize("operation", tuple(ADMIN_OPERATIONS))
def test_authorization_for_approved_operation(operation):
    plan = prepare_execution_plan(operation)
    authorization = create_authorization(plan)

    assert isinstance(authorization.authorization_id, UUID)
    assert authorization.operation == operation
    assert authorization.target == ISOLATED_TARGET
    assert authorization.sql_sha256 == plan.sql_sha256
    assert authorization.state == "prepared"

    validate_authorization(authorization, plan)


def test_authorizations_have_distinct_identifiers():
    plan = prepare_execution_plan("--execute-transfer")

    first = create_authorization(plan)
    second = create_authorization(plan)

    assert first.authorization_id != second.authorization_id


def test_authorization_is_immutable():
    plan = prepare_execution_plan("--execute-transfer")
    authorization = create_authorization(plan)

    with pytest.raises(FrozenInstanceError):
        authorization.state = "authorized"


@pytest.mark.parametrize(
    "changes",
    (
        {"target": "livenetv2/livenet"},
        {"operation": "--execute-grant-app"},
        {"sql_sha256": "0" * 64},
        {"state": "authorized"},
        {"state": "consumed"},
        {"state": "invalid"},
        {"authorization_id": "invalid"},
    ),
)
def test_modified_authorization_rejected(changes):
    plan = prepare_execution_plan("--execute-transfer")
    authorization = create_authorization(plan)

    modified = replace(authorization, **changes)

    with pytest.raises(ValueError):
        validate_authorization(modified, plan)


@pytest.mark.parametrize(
    "changes",
    (
        {"operation": "--execute-unknown"},
        {"sql_filename": "unknown.sql"},
        {"sql_sha256": "0" * 64},
        {"sql": "BEGIN;\\nSELECT 1;\\nCOMMIT;\\n"},
    ),
)
def test_modified_plan_rejected_on_creation(changes):
    plan = prepare_execution_plan("--execute-transfer")
    modified = replace(plan, **changes)

    with pytest.raises(ValueError):
        create_authorization(modified)


def test_authorization_cannot_be_used_for_another_plan():
    plan = prepare_execution_plan("--execute-transfer")
    other = prepare_execution_plan("--execute-grant-app")

    authorization = create_authorization(plan)

    with pytest.raises(ValueError):
        validate_authorization(authorization, other)
