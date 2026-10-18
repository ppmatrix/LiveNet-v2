"""Testes unitários do serviço centralizado de auditoria."""

import uuid
from unittest.mock import Mock

import pytest
from sqlalchemy.orm import Session

from app.audit.models import AuditEvent
from app.audit.service import record_audit_event


@pytest.fixture
def session():
    return Mock(spec=Session)


def test_record_audit_event(session):
    actor_id = uuid.uuid4()
    entity_id = uuid.uuid4()

    event = record_audit_event(
        session,
        actor_type="user",
        actor_id=actor_id,
        action="inventory.resource.updated",
        entity_type="inventory.resource",
        entity_id=entity_id,
        outcome="success",
        changes={"name": {"old": "A", "new": "B"}},
        context={"source": "test"},
    )

    assert isinstance(event, AuditEvent)
    assert event.actor_id == actor_id
    assert event.entity_id == entity_id
    assert event.action == "inventory.resource.updated"
    assert event.changes["name"]["new"] == "B"
    assert event.context == {"source": "test"}

    session.add.assert_called_once_with(event)
    session.commit.assert_not_called()
    session.flush.assert_not_called()
    session.rollback.assert_not_called()


@pytest.mark.parametrize(
    "field,value",
    [
        ("actor_type", ""),
        ("actor_type", "   "),
        ("actor_type", "x" * 33),
        ("action", ""),
        ("action", "x" * 129),
        ("entity_type", ""),
        ("entity_type", "x" * 129),
        ("outcome", ""),
        ("outcome", "x" * 33),
    ],
)
def test_invalid_required_fields(session, field, value):
    arguments = {
        "actor_type": "system",
        "action": "test.action",
        "entity_type": "test.entity",
        "outcome": "success",
    }
    arguments[field] = value

    with pytest.raises(ValueError):
        record_audit_event(session, **arguments)

    session.add.assert_not_called()


@pytest.mark.parametrize(
    "field",
    ["actor_id", "entity_id", "correlation_id"],
)
def test_invalid_uuid(session, field):
    with pytest.raises(ValueError):
        record_audit_event(
            session,
            actor_type="system",
            action="test.action",
            entity_type="test.entity",
            outcome="success",
            **{field: "not-a-uuid"},
        )

    session.add.assert_not_called()


@pytest.mark.parametrize(
    "payload",
    [
        {"password": "example"},
        {"nested": {"api_key": "example"}},
        {"items": [{"access_token": "example"}]},
        {"authorization": "Bearer example"},
    ],
)
def test_sensitive_changes_rejected(session, payload):
    with pytest.raises(ValueError, match="sensitive field"):
        record_audit_event(
            session,
            actor_type="system",
            action="test.action",
            entity_type="test.entity",
            outcome="success",
            changes=payload,
        )

    session.add.assert_not_called()


def test_sensitive_context_rejected(session):
    with pytest.raises(ValueError, match="sensitive field"):
        record_audit_event(
            session,
            actor_type="system",
            action="test.action",
            entity_type="test.entity",
            outcome="success",
            context={"nested": {"private_key": "example"}},
        )

    session.add.assert_not_called()


def test_default_json_objects(session):
    event = record_audit_event(
        session,
        actor_type="system",
        action="test.action",
        entity_type="test.entity",
        outcome="success",
    )

    assert event.changes == {}
    assert event.context == {}


def test_invalid_session():
    with pytest.raises(TypeError):
        record_audit_event(
            object(),
            actor_type="system",
            action="test.action",
            entity_type="test.entity",
            outcome="success",
        )


@pytest.mark.parametrize(
    "payload",
    [
        {"value": object()},
        {"value": {1, 2, 3}},
        {"value": float("nan")},
        {"value": float("inf")},
        {"value": float("-inf")},
    ],
)
def test_invalid_json_values_rejected(session, payload):
    with pytest.raises(ValueError, match="JSON-compatible"):
        record_audit_event(
            session,
            actor_type="system",
            action="test.action",
            entity_type="test.entity",
            outcome="success",
            changes=payload,
        )

    session.add.assert_not_called()


def test_changes_are_independent_from_input(session):
    changes = {
        "resource": {
            "name": "original",
            "properties": ["a", "b"],
        }
    }

    event = record_audit_event(
        session,
        actor_type="system",
        action="test.action",
        entity_type="test.entity",
        outcome="success",
        changes=changes,
    )

    changes["resource"]["name"] = "modified"
    changes["resource"]["properties"].append("c")

    assert event.changes == {
        "resource": {
            "name": "original",
            "properties": ["a", "b"],
        }
    }


def test_context_is_independent_from_input(session):
    context = {"metadata": {"source": "original"}}

    event = record_audit_event(
        session,
        actor_type="system",
        action="test.action",
        entity_type="test.entity",
        outcome="success",
        context=context,
    )

    context["metadata"]["source"] = "modified"

    assert event.context == {
        "metadata": {"source": "original"}
    }


def test_nested_sensitive_context_rejected(session):
    with pytest.raises(ValueError, match="sensitive field"):
        record_audit_event(
            session,
            actor_type="system",
            action="test.action",
            entity_type="test.entity",
            outcome="success",
            context={
                "metadata": {
                    "items": [
                        {"api_key": "example"}
                    ]
                }
            },
        )

    session.add.assert_not_called()
