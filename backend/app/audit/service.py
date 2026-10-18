"""Serviço de escrita transacional de eventos de auditoria."""

import json
import uuid

from sqlalchemy.orm import Session

from app.audit.models import AuditEvent


SENSITIVE_KEYS = frozenset({
    "password",
    "passwd",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "api_key",
    "private_key",
    "authorization",
    "credential",
    "credentials",
})


def _validate_required_string(name, value, max_length):
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")

    if not value.strip():
        raise ValueError(f"{name} must not be empty")

    if len(value) > max_length:
        raise ValueError(f"{name} exceeds {max_length} characters")


def _validate_optional_uuid(name, value):
    if value is not None and not isinstance(value, uuid.UUID):
        raise ValueError(f"{name} must be a UUID or None")


def _validate_sensitive_keys(value, path):
    if isinstance(value, dict):
        for key, nested in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path} keys must be strings")

            normalized = key.lower().replace("-", "_")

            if normalized in SENSITIVE_KEYS:
                raise ValueError(
                    f"sensitive field not permitted: {path}.{key}"
                )

            _validate_sensitive_keys(nested, f"{path}.{key}")

    elif isinstance(value, (list, tuple)):
        for index, nested in enumerate(value):
            _validate_sensitive_keys(nested, f"{path}[{index}]")


def _validate_json_object(name, value):
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a JSON object")

    _validate_sensitive_keys(value, name)

    try:
        serialized = json.dumps(value, allow_nan=False)
        return json.loads(serialized)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(
            f"{name} must contain valid JSON-compatible values"
        ) from exc


def record_audit_event(
    session: Session,
    *,
    actor_type: str,
    action: str,
    entity_type: str,
    outcome: str,
    actor_id: uuid.UUID | None = None,
    entity_id: uuid.UUID | None = None,
    correlation_id: uuid.UUID | None = None,
    request_id: str | None = None,
    changes: dict | None = None,
    context: dict | None = None,
) -> AuditEvent:
    """Adiciona um evento à sessão sem controlar a transação."""

    if not isinstance(session, Session):
        raise TypeError("session must be a SQLAlchemy Session")

    for name, value, limit in (
        ("actor_type", actor_type, 32),
        ("action", action, 128),
        ("entity_type", entity_type, 128),
        ("outcome", outcome, 32),
    ):
        _validate_required_string(name, value, limit)

    for name, value in (
        ("actor_id", actor_id),
        ("entity_id", entity_id),
        ("correlation_id", correlation_id),
    ):
        _validate_optional_uuid(name, value)

    if request_id is not None:
        if not isinstance(request_id, str) or len(request_id) > 128:
            raise ValueError("request_id must be a string of at most 128 characters")

    changes_data = {} if changes is None else changes
    context_data = {} if context is None else context

    changes_data = _validate_json_object("changes", changes_data)
    context_data = _validate_json_object("context", context_data)

    event = AuditEvent(
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        correlation_id=correlation_id,
        request_id=request_id,
        outcome=outcome,
        changes=changes_data,
        context=context_data,
    )

    session.add(event)
    return event
