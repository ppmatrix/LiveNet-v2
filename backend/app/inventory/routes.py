"""M1.1 HTTP API. Disabled for real use until identity/RBAC is integrated.

Dependencies are installed by trusted Python application setup, not by clients
or environment flags. Denied requests never initialize a database engine.

GET /resources accepts page (default 1), per_page (default 50, maximum 100),
resource_type and administrative_state. It returns items/total/page/per_page.
GET /resources/<id> hides nonexistent and unauthorized rows behind the same 404.
POST /resources returns the resource and Location after resource + audit commit.
PATCH /resources/<id> accepts the four editable fields and row_version; a stale
version returns 409. Archive/unarchive is excluded. Editing requires a SQL scope.
Input errors use 400/415, missing identity 401, denied permission 403, and internal
failures a sanitized 500. No mutation retry or idempotent POST is implemented;
a lost commit response requires reconciliation, not blind client repetition.
"""

from threading import Lock

from flask import Blueprint, current_app, jsonify, request, url_for
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.orm.exc import StaleDataError
from werkzeug.exceptions import HTTPException

from app.core.database import create_database_engine, create_session_factory
from app.security.errors import SecurityError
from app.inventory.access import DenyInventoryAccess, InventoryIdentity
from app.inventory import service
from app.inventory.schemas import (
    InventoryValidationError, serialize_resource, validate_creation,
    validate_query, validate_resource_id, validate_update,
)


inventory_bp = Blueprint("inventory", __name__)


@inventory_bp.errorhandler(service.ResourceConflict)
@inventory_bp.errorhandler(StaleDataError)
def handle_version_conflict(error):
    return _error(409, "version_conflict", "O recurso foi alterado. Consulte a versão atual antes de guardar.")


@inventory_bp.errorhandler(service.ArchivedResource)
def handle_archived_resource(error):
    return _error(409, "resource_archived", "Não é permitida a edição de recursos arquivados.")


class InventoryDependencies:
    def __init__(self, access=None, session_factory=None):
        self.access = access if access is not None else DenyInventoryAccess()
        self._session_factory = session_factory
        self._lock = Lock()

    def open_session(self):
        with self._lock:
            if self._session_factory is None:
                engine = create_database_engine()
                self._session_factory = create_session_factory(engine)
        return self._session_factory()


class InventoryHTTPError(Exception):
    def __init__(self, status, code, message):
        self.status, self.code, self.message = status, code, message


def _error(status, code, message):
    return jsonify(error={"code": code, "message": message}), status


@inventory_bp.errorhandler(InventoryHTTPError)
def handle_api_error(error):
    return _error(error.status, error.code, error.message)


@inventory_bp.errorhandler(InventoryValidationError)
def handle_validation_error(error):
    return _error(400, "invalid_request", str(error))


@inventory_bp.errorhandler(Exception)
def handle_unexpected_error(error):
    if isinstance(error, SecurityError):
        return _error(error.code, error.error_code, error.description)
    if isinstance(error, HTTPException):
        response = error.get_response()
        response.data = current_app.json.dumps({"error": {
            "code": "invalid_request", "message": "Pedido inválido.",
        }})
        response.content_type = "application/json"
        return response
    current_app.logger.error("Inventory operation failed")
    return _error(500, "internal_error", "Não foi possível concluir a operação.")


@inventory_bp.app_errorhandler(HTTPException)
def handle_inventory_routing_error(error):
    # Flask resolves 404/405 before selecting a blueprint. Keep other domains'
    # existing HTTP contracts while returning JSON for inventory routing errors.
    prefix = "/api/v1/inventory"
    if request.path == prefix or request.path.startswith(prefix + "/"):
        return handle_unexpected_error(error)
    return error


def _caller():
    dependencies = current_app.extensions["inventory"]
    identity = dependencies.access.resolve_identity()
    if identity is None:
        raise InventoryHTTPError(401, "unauthenticated", "Autenticação necessária.")
    if not isinstance(identity, InventoryIdentity):
        raise RuntimeError("Invalid identity integration")
    return dependencies, identity


def _read_scope(dependencies, identity):
    scope = dependencies.access.read_scope(identity)
    if scope is None:
        raise InventoryHTTPError(403, "forbidden", "Operação não permitida.")
    if not isinstance(scope, ColumnElement):
        raise RuntimeError("Invalid scope integration")
    return scope


@inventory_bp.get("/resources")
def list_resources():
    dependencies, identity = _caller()
    scope = _read_scope(dependencies, identity)
    query = validate_query(request.args)
    with dependencies.open_session() as session:
        with session.begin():
            items, total = service.list_resources(session, scope, **query)
            payload = {"items": [serialize_resource(item) for item in items],
                       "total": total, "page": query["page"], "per_page": query["per_page"]}
    return jsonify(payload)


@inventory_bp.get("/resources/<resource_id>")
def get_resource(resource_id):
    dependencies, identity = _caller()
    scope = _read_scope(dependencies, identity)
    identifier = validate_resource_id(resource_id)
    with dependencies.open_session() as session:
        with session.begin():
            resource = service.get_resource(session, scope, identifier)
            if resource is None:
                raise InventoryHTTPError(404, "not_found", "Recurso não encontrado.")
            payload = serialize_resource(resource)
    return jsonify(payload)


@inventory_bp.post("/resources")
def create_resource():
    dependencies, identity = _caller()
    if not request.is_json:
        raise InventoryHTTPError(415, "unsupported_media_type", "É necessário application/json.")
    data = validate_creation(request.get_json())
    if dependencies.access.can_create(identity, data) is not True:
        raise InventoryHTTPError(403, "forbidden", "Operação não permitida.")
    with dependencies.open_session() as session:
        with session.begin():
            resource = service.create_resource(session, data, identity)
            payload = serialize_resource(resource)
    response = jsonify(payload)
    response.status_code = 201
    response.headers["Location"] = url_for("inventory.get_resource", resource_id=payload["id"])
    return response


@inventory_bp.patch("/resources/<resource_id>")
def update_resource(resource_id):
    dependencies, identity = _caller()
    scope = dependencies.access.update_scope(identity)
    if scope is None:
        raise InventoryHTTPError(403, "forbidden", "Operação não permitida.")
    if not isinstance(scope, ColumnElement):
        raise RuntimeError("Invalid edit scope integration")
    identifier = validate_resource_id(resource_id)
    if not request.is_json:
        raise InventoryHTTPError(415, "unsupported_media_type", "É necessário application/json.")
    data = validate_update(request.get_json())
    with dependencies.open_session() as session:
        with session.begin():
            resource = service.update_resource(session, scope, identifier, data, identity)
            if resource is None:
                raise InventoryHTTPError(404, "not_found", "Recurso não encontrado.")
            payload = serialize_resource(resource)
    return jsonify(payload)
