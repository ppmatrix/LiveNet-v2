"""HTTP/transaction orchestration with simulated trusted integrations only.

These tests do not claim to establish PostgreSQL durability/atomicity.
"""

import json
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy import event, false, true
from sqlalchemy.orm import Session

from app import create_app
from app.audit.models import AuditEvent
from app.inventory.access import InventoryIdentity
from app.inventory.models import Resource


BASE = "/api/v1/inventory/resources"
VALID = {"resource_type": "service", "display_name": "API"}


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setattr("app.inventory.routes.create_database_engine",
                        Mock(side_effect=AssertionError("Real database forbidden")))
    access = Mock()
    access.resolve_identity.return_value = InventoryIdentity(uuid4())
    access.read_scope.return_value = true()
    access.can_create.return_value = True
    access.update_scope.return_value = true()
    session = MagicMock(spec=Session)
    staged, committed = [], []
    session.add.side_effect = staged.append
    session.commit.side_effect = lambda: committed.extend(staged)
    session.rollback.side_effect = staged.clear
    session.__enter__.return_value = session
    session.__exit__.side_effect = lambda *args: session.close() and False

    @contextmanager
    def transaction():
        try:
            yield
            session.commit()
        except Exception:
            session.rollback()
            raise

    session.begin.side_effect = transaction
    factory = Mock(return_value=session)
    app = create_app("testing", inventory_access=access, inventory_session_factory=factory)
    return app.test_client(), access, session, factory, committed


def resource():
    now = datetime.now(timezone.utc)
    return Resource(id=uuid4(), resource_type="service", display_name="API",
                    description=None, administrative_state="active", attributes={},
                    created_at=now, updated_at=now, archived_at=None, row_version=1)


@pytest.mark.parametrize("method,path", [("get", BASE), ("get", BASE + "/" + str(uuid4())),
                                         ("post", BASE)])
@pytest.mark.parametrize("environment", ["testing", "production", "development"])
def test_runtime_default_denies_without_database(monkeypatch, method, path, environment):
    engine = Mock(side_effect=AssertionError("No database initialization"))
    monkeypatch.setattr("app.inventory.routes.create_database_engine", engine)
    client = create_app(environment).test_client()
    response = getattr(client, method)(path, json=VALID,
                                      headers={"X-User-ID": str(uuid4()), "Authorization": "Bearer fake"})
    assert response.status_code == 401
    assert response.json["error"]["code"] == "unauthenticated"
    engine.assert_not_called()


@pytest.mark.parametrize("method,path", [("get", BASE), ("get", BASE + "/" + str(uuid4())),
                                         ("post", BASE)])
def test_missing_identity(api, method, path):
    client, access, _, factory, _ = api
    access.resolve_identity.return_value = None
    assert getattr(client, method)(path, json=VALID).status_code == 401
    factory.assert_not_called()


@pytest.mark.parametrize("method,path", [("get", BASE), ("get", BASE + "/" + str(uuid4())),
                                         ("post", BASE)])
def test_missing_permission(api, method, path):
    client, access, _, factory, _ = api
    access.read_scope.return_value = None
    access.can_create.return_value = False
    assert getattr(client, method)(path, json=VALID).status_code == 403
    factory.assert_not_called()


def test_empty_list(api):
    client, _, session, _, _ = api
    session.scalar.return_value = 0
    session.scalars.return_value.all.return_value = []
    response = client.get(BASE)
    assert response.status_code == 200
    assert response.json == {"items": [], "total": 0, "page": 1, "per_page": 50}
    session.close.assert_called_once()


def test_list_serializes_page(api):
    client, _, session, _, _ = api
    item = resource()
    session.scalar.return_value = 5
    session.scalars.return_value.all.return_value = [item]
    response = client.get(BASE + "?page=2&per_page=2&resource_type=service&administrative_state=active")
    assert response.status_code == 200
    assert response.json["total"] == 5
    assert response.json["items"][0]["id"] == str(item.id)
    assert response.json["page"] == 2 and response.json["per_page"] == 2


def test_detail(api):
    client, _, session, _, _ = api
    item = resource()
    session.scalar.return_value = item
    response = client.get(BASE + "/" + str(item.id))
    assert response.status_code == 200
    assert response.json["id"] == str(item.id)
    session.close.assert_called_once()


@pytest.mark.parametrize("out_of_scope", [False, True])
def test_missing_and_out_of_scope_are_indistinguishable(api, out_of_scope):
    client, access, session, _, _ = api
    if out_of_scope:
        access.read_scope.return_value = false()
    session.scalar.return_value = None
    response = client.get(BASE + "/" + str(uuid4()))
    assert response.status_code == 404
    assert response.json == {"error": {"code": "not_found", "message": "Recurso não encontrado."}}
    session.rollback.assert_called_once()
    session.close.assert_called_once()


def test_creation_and_location(api):
    client, access, session, _, committed = api
    response = client.post(BASE, json=VALID)
    assert response.status_code == 201
    assert response.headers["Location"] == BASE + "/" + response.json["id"]
    assert response.json["administrative_state"] == "active"
    assert response.json["attributes"] == {} and response.json["row_version"] == 1
    assert response.json["created_at"] == response.json["updated_at"]
    assert len(committed) == 2 and isinstance(committed[1], AuditEvent)
    assert committed[1].actor_id == access.resolve_identity.return_value.actor_id
    session.commit.assert_called_once()
    session.rollback.assert_not_called()
    session.close.assert_called_once()


UPDATE = {**VALID, 'description': 'Descrição atualizada', 'administrative_state': 'maintenance', 'row_version': 1}


def test_creation_with_administrative_state(api):
    client, _, _, _, _ = api
    response = client.post(BASE, json={**VALID, 'administrative_state': 'disabled'})
    assert response.status_code == 201 and response.json['administrative_state'] == 'disabled'


def test_edit_persists_fields_and_audit_in_same_transaction(api):
    client, access, session, _, committed = api
    item = resource(); session.scalar.return_value = item
    session.flush.side_effect = lambda: setattr(item, 'row_version', 2)
    response = client.patch(BASE+'/'+str(item.id), json=UPDATE)
    assert response.status_code == 200
    assert response.json['row_version'] == 2
    assert response.json['description'] == UPDATE['description']
    assert response.json['administrative_state'] == 'maintenance'
    assert response.json['attributes'] == {} and response.json['archived_at'] is None
    assert len(committed) == 1 and committed[0].action == 'inventory.resource.updated'
    assert committed[0].actor_id == access.resolve_identity.return_value.actor_id
    session.commit.assert_called_once()


@pytest.mark.parametrize('reason,status', [('anonymous',401),('reader',403),('invalid_scope',500)])
def test_edit_denied_before_opening_session(api, reason, status):
    client, access, _, factory, _ = api
    if reason=='anonymous':access.resolve_identity.return_value=None
    elif reason=='reader':access.update_scope.return_value=None
    else:access.update_scope.return_value=True
    assert client.patch(BASE+'/'+str(uuid4()), json=UPDATE).status_code==status
    factory.assert_not_called()


@pytest.mark.parametrize('reason', ['stale','concurrent_flush','archived','missing','audit_failure'])
def test_edit_failure_rolls_back_without_committed_audit(api, monkeypatch, reason):
    from sqlalchemy.orm.exc import StaleDataError
    client, _, session, _, committed = api
    item=resource(); session.scalar.return_value=item
    status=409
    if reason=='stale':item.row_version=2
    elif reason=='concurrent_flush':session.flush.side_effect=StaleDataError('private')
    elif reason=='archived':item.administrative_state='archived'
    elif reason=='missing':session.scalar.return_value=None;status=404
    else:
        monkeypatch.setattr('app.inventory.service.record_audit_event',Mock(side_effect=RuntimeError('private')))
        status=500
    response=client.patch(BASE+'/'+str(item.id),json=UPDATE)
    assert response.status_code==status
    assert b'private' not in response.data and committed==[]
    session.rollback.assert_called_once()


@pytest.mark.parametrize('patch', [{'row_version':None},{'attributes':{}},{'administrative_state':'archived'}])
def test_edit_invalid_data_before_session(api, patch):
    client, _, _, factory, _=api
    assert client.patch(BASE+'/'+str(uuid4()),json=UPDATE|patch).status_code==400
    factory.assert_not_called()


@pytest.mark.parametrize("failure", ["audit", "flush", "commit", "serialize"])
def test_creation_failure_rolls_back_and_closes(api, monkeypatch, failure):
    client, _, session, _, committed = api
    error = RuntimeError("private database details")
    if failure == "audit":
        monkeypatch.setattr("app.inventory.service.record_audit_event", Mock(side_effect=error))
    elif failure == "serialize":
        monkeypatch.setattr("app.inventory.routes.serialize_resource", Mock(side_effect=error))
    else:
        getattr(session, failure).side_effect = error
    response = client.post(BASE, json=VALID)
    assert response.status_code == 500
    assert response.json["error"]["code"] == "internal_error"
    assert b"private database details" not in response.data
    assert committed == []
    session.rollback.assert_called_once()
    session.close.assert_called_once()


def test_read_failure_rolls_back_and_closes(api):
    client, _, session, _, _ = api
    session.scalar.side_effect = RuntimeError("private")
    assert client.get(BASE).status_code == 500
    session.rollback.assert_called_once()
    session.close.assert_called_once()


@pytest.mark.parametrize("path", [BASE + "/invalid", BASE + "?per_page=101",
                                  BASE + "?scope=global", BASE + "?page=1&page=2"])
def test_invalid_query_or_id_before_session(api, path):
    client, _, _, factory, _ = api
    assert client.get(path).status_code == 400
    factory.assert_not_called()


@pytest.mark.parametrize("payload", [None, [], {**VALID, "scope": "global"},
                                     {**VALID, "attributes": {"ip": "192.0.2.1"}}])
def test_invalid_creation_before_session(api, payload):
    client, _, _, factory, _ = api
    response = client.post(BASE, data=json.dumps(payload), content_type="application/json")
    assert response.status_code == 400
    assert response.json["error"]["code"] == "invalid_request"
    factory.assert_not_called()


@pytest.mark.parametrize("body,content_type,status", [("{", "application/json", 400),
                                                     ("text", "text/plain", 415)])
def test_malformed_or_non_json(api, body, content_type, status):
    client, _, _, factory, _ = api
    response = client.post(BASE, data=body, content_type=content_type)
    assert response.status_code == status and "error" in response.json
    factory.assert_not_called()


def test_broken_identity_integration_fails_closed(api):
    client, access, _, factory, _ = api
    access.resolve_identity.side_effect = RuntimeError("private identity details")
    response = client.get(BASE)
    assert response.status_code == 500
    assert b"private identity" not in response.data
    factory.assert_not_called()


@pytest.mark.parametrize("scope", [True, False, "global"])
def test_invalid_scope_integration_does_not_open_session(api, scope):
    client, access, _, factory, _ = api
    access.read_scope.return_value = scope
    assert client.get(BASE).status_code == 500
    factory.assert_not_called()


def test_truthy_creation_permission_is_not_accepted(api):
    client, access, _, factory, _ = api
    access.can_create.return_value = "yes"
    assert client.post(BASE, json=VALID).status_code == 403
    factory.assert_not_called()


def test_lazy_database_factory_reuses_engine(monkeypatch):
    from app.inventory.routes import InventoryDependencies

    engine, session = Mock(), Mock()
    factory = Mock(return_value=session)
    build_engine = Mock(return_value=engine)
    build_factory = Mock(return_value=factory)
    monkeypatch.setattr("app.inventory.routes.create_database_engine", build_engine)
    monkeypatch.setattr("app.inventory.routes.create_session_factory", build_factory)
    dependencies = InventoryDependencies()
    build_engine.assert_not_called()
    assert dependencies.open_session() is session
    assert dependencies.open_session() is session
    build_engine.assert_called_once_with()
    build_factory.assert_called_once_with(engine)
    assert factory.call_count == 2


@pytest.mark.parametrize("failure", ["audit", "flush"])
def test_real_sqlalchemy_session_rolls_back_pending_objects_without_database(api, monkeypatch, failure):
    _, access, _, _, _ = api
    session = Session()  # Deliberately unbound: cannot connect or execute SQL.
    rolled_back, pending = [], []
    event.listen(session, "after_rollback", lambda _: rolled_back.append(True))
    close = Mock(wraps=session.close)
    monkeypatch.setattr(session, "close", close)

    def fail(*args, **kwargs):
        pending.extend(session.new)
        raise RuntimeError("simulated failure before SQL")

    if failure == "audit":
        monkeypatch.setattr("app.inventory.service.record_audit_event", fail)
    else:
        monkeypatch.setattr(session, "flush", fail)
    client = create_app("testing", inventory_access=access,
                        inventory_session_factory=lambda: session).test_client()
    assert client.post(BASE, json=VALID).status_code == 500
    assert rolled_back == [True]
    assert any(isinstance(item, Resource) for item in pending)
    if failure == "flush":
        assert any(isinstance(item, AuditEvent) for item in pending)
    assert not session.new and not session.in_transaction()
    close.assert_called_once()


@pytest.mark.parametrize("method,path,status", [
    ("put", BASE, 405), ("get", "/api/v1/inventory/unknown", 404),
])
def test_inventory_routing_errors_are_json_without_session(api, method, path, status):
    client, _, _, factory, _ = api
    response = getattr(client, method)(path)
    assert response.status_code == status
    assert response.json["error"]["code"] == "invalid_request"
    if status == 405:
        assert "GET" in response.headers["Allow"]
    factory.assert_not_called()
