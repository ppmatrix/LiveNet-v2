"""Inventory operations. The caller owns the session and transaction."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.sql.elements import ColumnElement

from app.audit.service import record_audit_event
from app.inventory.models import Resource


def _scoped_query(scope):
    if not isinstance(scope, ColumnElement):
        raise ValueError("Explicit SQL authorization scope required")
    return select(Resource).where(scope)


def list_resources(session, scope, *, page, per_page,
                   resource_type=None, administrative_state=None):
    query = _scoped_query(scope)
    if resource_type is not None:
        query = query.where(Resource.resource_type == resource_type)
    if administrative_state is not None:
        query = query.where(Resource.administrative_state == administrative_state)
    total = session.scalar(select(func.count()).select_from(query.subquery()))
    items = session.scalars(
        query.order_by(Resource.created_at, Resource.id)
        .offset((page - 1) * per_page).limit(per_page)
    ).all()
    return items, total


def get_resource(session, scope, resource_id):
    return session.scalar(_scoped_query(scope).where(Resource.id == resource_id))


def create_resource(session, data, identity):
    now = datetime.now(timezone.utc)
    resource = Resource(
        id=uuid4(), resource_type=data["resource_type"],
        display_name=data["display_name"], description=data["description"],
        attributes=dict(data["attributes"]), administrative_state="active",
        created_at=now, updated_at=now, archived_at=None, row_version=1,
    )
    session.add(resource)
    record_audit_event(
        session, actor_type=identity.actor_type, actor_id=identity.actor_id,
        action="inventory.resource.created", entity_type="inventory.resource",
        entity_id=resource.id, outcome="success",
        changes={"resource_type": resource.resource_type,
                 "display_name": resource.display_name,
                 "administrative_state": resource.administrative_state},
    )
    session.flush()
    return resource
