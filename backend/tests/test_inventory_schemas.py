from datetime import datetime, timezone
from uuid import uuid4

import pytest
from werkzeug.datastructures import MultiDict

from app.inventory.models import Resource
from app.inventory.schemas import (
    RESOURCE_TYPES, InventoryValidationError, serialize_resource,
    validate_creation, validate_query, validate_resource_id,
)


@pytest.mark.parametrize("resource_type", sorted(RESOURCE_TYPES))
def test_creation_catalogue_and_defaults(resource_type):
    assert validate_creation({"resource_type": resource_type, "display_name": " Host "}) == {
        "resource_type": resource_type, "display_name": "Host",
        "description": None, "attributes": {},
    }


@pytest.mark.parametrize("payload", [
    None, [], "text", 1, True, {},
    {"resource_type": "unknown", "display_name": "A"},
    {"resource_type": [], "display_name": "A"},
    {"resource_type": "service"},
    {"resource_type": "service", "display_name": None},
    {"resource_type": "service", "display_name": "  "},
    {"resource_type": "service", "display_name": "x" * 256},
    {"resource_type": "service", "display_name": 123},
])
def test_invalid_creation(payload):
    with pytest.raises(InventoryValidationError):
        validate_creation(payload)


@pytest.mark.parametrize("key,value", [
    ("description", []), ("description", False),
    ("attributes", None), ("attributes", []), ("attributes", False),
    ("attributes", {"ip": "192.0.2.1"}),
    ("id", str(uuid4())), ("created_at", "2026-01-01"),
    ("updated_at", "2026-01-01"), ("row_version", 2),
    ("administrative_state", "active"), ("archived_at", None),
    ("scope", "global"), ("actor_id", str(uuid4())),
])
def test_disallowed_fields_and_types(key, value):
    with pytest.raises(InventoryValidationError):
        validate_creation({"resource_type": "service", "display_name": "A", key: value})


def test_optional_fields_and_boundary():
    data = validate_creation({"resource_type": "service", "display_name": "x" * 255,
                              "description": "description", "attributes": {}})
    assert len(data["display_name"]) == 255
    assert data["description"] == "description"


def test_query_defaults_and_limits():
    assert validate_query(MultiDict()) == {
        "page": 1, "per_page": 50, "resource_type": None, "administrative_state": None,
    }
    assert validate_query(MultiDict({"page": "2", "per_page": "100"}))["per_page"] == 100


@pytest.mark.parametrize("key,value", [
    ("page", "0"), ("page", "-1"), ("page", "1.5"), ("page", ""),
    ("page", "2147483648"), ("page", "9" * 5000), ("page", "١"),
    ("per_page", "101"), ("per_page", "0"), ("per_page", "abc"),
    ("resource_type", "unknown"), ("administrative_state", "unknown"),
    ("scope", "global"), ("resource_ids", str(uuid4())),
])
def test_invalid_query(key, value):
    with pytest.raises(InventoryValidationError):
        validate_query(MultiDict([(key, value)]))


@pytest.mark.parametrize("key", ["page", "per_page", "resource_type", "administrative_state"])
def test_repeated_query_parameter_rejected(key):
    with pytest.raises(InventoryValidationError):
        validate_query(MultiDict([(key, "1"), (key, "2")]))


@pytest.mark.parametrize("state", ["active", "maintenance", "disabled", "archived"])
def test_valid_filters(state):
    query = validate_query(MultiDict({"resource_type": "service", "administrative_state": state}))
    assert query["resource_type"] == "service"
    assert query["administrative_state"] == state


@pytest.mark.parametrize("value", [None, "invalid", "", 123])
def test_invalid_uuid(value):
    with pytest.raises(InventoryValidationError):
        validate_resource_id(value)


def test_uuid_and_serialization():
    identifier = uuid4()
    assert validate_resource_id(str(identifier)) == identifier
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    resource = Resource(id=identifier, resource_type="service", display_name="API",
                        description=None, attributes={}, administrative_state="active",
                        created_at=now, updated_at=now, archived_at=None, row_version=1)
    result = serialize_resource(resource)
    assert result["id"] == str(identifier)
    assert result["created_at"] == "2026-01-01T00:00:00Z"
    assert result["archived_at"] is None
    assert result["row_version"] == 1
