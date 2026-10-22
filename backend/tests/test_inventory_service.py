"""Offline orchestration/query tests; no engine, SQL execution or DDL."""

from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy import false
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session

from app.audit.models import AuditEvent
from app.inventory.access import InventoryIdentity
from app.inventory.models import Resource
from app.inventory import service


def compiled(statement):
    return statement.compile(dialect=postgresql.dialect())


def test_scope_and_filters_apply_to_count_and_page():
    session = Mock(spec=Session)
    session.scalar.return_value = 3
    session.scalars.return_value.all.return_value = []
    allowed_id = uuid4()
    assert service.list_resources(
        session, Resource.id == allowed_id, page=2, per_page=2,
        resource_type="service", administrative_state="active",
    ) == ([], 3)
    count = compiled(session.scalar.call_args.args[0])
    page = compiled(session.scalars.call_args.args[0])
    for query in (count, page):
        assert allowed_id in query.params.values()
        assert "service" in query.params.values()
        assert "active" in query.params.values()
        assert "WHERE inventory.resources.id =" in str(query)
    assert "LIMIT" not in str(count) and "OFFSET" not in str(count)
    assert "ORDER BY inventory.resources.created_at, inventory.resources.id" in str(page)
    assert "LIMIT" in str(page) and "OFFSET" in str(page)
    assert list(page.params.values()).count(2) == 2


def test_empty_scope_is_not_global_access():
    session = Mock(spec=Session)
    service.list_resources(session, false(), page=1, per_page=50)
    assert "WHERE false" in str(compiled(session.scalar.call_args.args[0]))
    assert "WHERE false" in str(compiled(session.scalars.call_args.args[0]))


def test_detail_has_scope_and_id_in_same_query():
    session = Mock(spec=Session)
    allowed_id, requested_id = uuid4(), uuid4()
    session.scalar.return_value = None
    assert service.get_resource(session, Resource.id == allowed_id, requested_id) is None
    query = compiled(session.scalar.call_args.args[0])
    assert allowed_id in query.params.values()
    assert requested_id in query.params.values()
    assert " AND " in str(query)


@pytest.mark.parametrize("scope", [None, True, False, "global"])
def test_scope_must_be_explicit_sql_predicate(scope):
    session = Mock(spec=Session)
    with pytest.raises(ValueError):
        service.list_resources(session, scope, page=1, per_page=50)
    session.scalar.assert_not_called()


def test_creation_and_real_audit_service_share_session():
    session = Mock(spec=Session)
    identity = InventoryIdentity(uuid4())
    data = {"resource_type": "service", "display_name": "API", "description": None,
            "attributes": {}}
    resource = service.create_resource(session, data, identity)
    added = [call.args[0] for call in session.add.call_args_list]
    assert added[0] is resource
    assert isinstance(added[1], AuditEvent)
    assert added[1].entity_id == resource.id
    assert added[1].actor_id == identity.actor_id
    assert added[1].action == "inventory.resource.created"
    assert resource.administrative_state == "active"
    assert resource.row_version == 1 and resource.archived_at is None
    assert resource.created_at == resource.updated_at
    session.flush.assert_called_once()
    session.commit.assert_not_called()
    session.rollback.assert_not_called()


def test_same_names_do_not_trigger_uniqueness_lookup():
    session = Mock(spec=Session)
    identity = InventoryIdentity(uuid4())
    data = {"resource_type": "service", "display_name": "Same", "description": None,
            "attributes": {}}
    first = service.create_resource(session, data, identity)
    second = service.create_resource(session, data, identity)
    assert first.id != second.id
    assert first.display_name == second.display_name
    session.scalar.assert_not_called()


def test_audit_failure_propagates_to_transaction_owner(monkeypatch):
    session = Mock(spec=Session)
    monkeypatch.setattr(service, "record_audit_event", Mock(side_effect=RuntimeError("audit")))
    with pytest.raises(RuntimeError):
        service.create_resource(session, {"resource_type": "service", "display_name": "A",
                                          "description": None, "attributes": {}},
                                InventoryIdentity(uuid4()))
    session.commit.assert_not_called()
    session.flush.assert_not_called()
