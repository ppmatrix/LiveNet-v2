"""Manual IPv4 declarations. No discovery, DNS or socket operations."""
from datetime import timezone
import hashlib
from ipaddress import IPv4Address
import json
import re
from uuid import uuid4

from sqlalchemy import select, func, text

from app.audit.service import record_audit_event
from .models import Resource, ResourceIdentifier as Identifier
from .service import ArchivedResource, ResourceConflict
from .schemas import _timestamp
from .identifier_contract import NAMESPACE_PATTERN


class IdentifierError(Exception):
    def __init__(self, status, code, details=None):
        self.status, self.code, self.details = status, code, details


def ipv4(value):
    if (not isinstance(value, str) or not 1 <= len(value) <= 64
            or any(ord(c) < 32 or ord(c) > 126 for c in value)):
        raise IdentifierError(400, 'invalid_ipv4')
    try:
        address = IPv4Address(value.strip(' '))
        if address.is_unspecified or address.is_multicast or str(address) == '255.255.255.255':
            raise ValueError()
        return str(address)
    except ValueError:
        raise IdentifierError(400, 'invalid_ipv4') from None


def namespace(value):
    if not isinstance(value, str) or re.fullmatch(NAMESPACE_PATTERN, value, flags=re.ASCII) is None:
        raise IdentifierError(400, 'invalid_namespace')
    return value


def payload(value, *, close=False):
    required = {'row_version'} if close else {'row_version', 'identifier_value', 'namespace'}
    optional = set() if close else {'confirm_shared', 'conflict_revision'}
    if not isinstance(value, dict) or not required <= set(value) or set(value) - required - optional:
        raise IdentifierError(400, 'invalid_request')
    version = value['row_version']
    if type(version) is not int or not 1 <= version < 2147483647:
        raise IdentifierError(400, 'invalid_request')
    if close:
        return {'row_version': version}
    normalized = ipv4(value['identifier_value']); ns = namespace(value['namespace'])
    confirm = value.get('confirm_shared', False); revision = value.get('conflict_revision')
    if (type(confirm) is not bool or (confirm and (not isinstance(revision, str) or re.fullmatch('[0-9a-f]{64}', revision) is None))
            or (not confirm and revision is not None)):
        raise IdentifierError(400, 'invalid_request')
    return dict(value, normalized_value=normalized, namespace=ns, confirm_shared=confirm, conflict_revision=revision)


def public(row):
    return dict(id=str(row.id), resource_id=str(row.resource_id), identifier_type=row.identifier_type,
        identifier_value=row.identifier_value, normalized_value=row.normalized_value, namespace=row.namespace,
        source_type=row.source_type, source_instance=row.source_instance,
        verification_status=row.verification_status, verified_at=_timestamp(row.verified_at),
        confidence=float(row.confidence) if row.confidence is not None else None, evidence=row.evidence,
        first_seen_at=_timestamp(row.first_seen_at), last_seen_at=_timestamp(row.last_seen_at),
        valid_from=_timestamp(row.valid_from), valid_until=_timestamp(row.valid_until),
        created_at=_timestamp(row.created_at), updated_at=_timestamp(row.updated_at),
        state='active' if row.valid_until is None else 'closed')


def resource(session, identifier, scope, *, lock=False):
    query = select(Resource).where(Resource.id == identifier, scope)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    row = session.scalar(query)
    if row is None:
        raise IdentifierError(404, 'not_found')
    return row


def editable(row):
    if row.archived_at is not None or row.administrative_state == 'archived':
        raise ArchivedResource()


def address_lock(session, ns, address):
    key = int.from_bytes(hashlib.sha256(json.dumps(['LiveNet/INV-ID-01', ns, address], separators=(',', ':')).encode()).digest()[:8], 'big', signed=True)
    session.execute(text('SELECT pg_catalog.pg_advisory_xact_lock(:key)'), {'key': key})


def clock(session):
    return session.scalar(select(func.clock_timestamp()))


def aware(value):
    return value.replace(tzinfo=value.tzinfo or timezone.utc)


def version(row, expected, *, noop=False):
    if expected > row.row_version or (not noop and expected != row.row_version):
        raise ResourceConflict()


def bump(row, when):
    if row.row_version >= 2147483646 or aware(when) < aware(row.updated_at):
        raise IdentifierError(409, 'temporal_conflict')
    row.row_version += 1
    row.updated_at = when


def result(row, parent, changed):
    return dict(identifier=public(row), resource_row_version=parent.row_version, changed=changed)


def matches(ns, address):
    return (Identifier.identifier_type.in_(('ipv4', 'IPv4')), Identifier.namespace == ns,
            Identifier.normalized_value == address)


def peers(session, parent_id, ns, address, read_scope):
    rows = list(session.scalars(select(Identifier).where(*matches(ns, address),
        Identifier.resource_id != parent_id, Identifier.valid_until.is_(None)).order_by(Identifier.id)))
    revision = hashlib.sha256(json.dumps([str(r.id) for r in rows], separators=(',', ':')).encode()).hexdigest()
    visible = set(session.scalars(select(Resource.id).where(read_scope, Resource.id.in_({r.resource_id for r in rows})))) if rows else set()
    # Never disclose UUIDs outside the read scope. The current roles are global;
    # granular RBAC must revisit the existence side channel of conflict refusal.
    authorized = [dict(resource_id=str(r.resource_id), identifier_id=str(r.id)) for r in rows if r.resource_id in visible]
    return rows, dict(conflict_revision=revision, conflicts=authorized[:20],
                      visible_total=len(authorized), truncated=len(authorized)>20)


def add(session, resource_id, data, identity, scope, read_scope):
    ns, address = data['namespace'], data['normalized_value']
    address_lock(session, ns, address)
    parent = resource(session, resource_id, scope, lock=True); editable(parent)
    active = list(session.scalars(select(Identifier).where(Identifier.resource_id == resource_id,
        *matches(ns, address), Identifier.source_type == 'manual', Identifier.valid_until.is_(None))))
    if len(active) > 1:
        raise IdentifierError(409, 'identifier_conflict')
    if active:
        version(parent, data['row_version'], noop=True)
        return result(active[0], parent, False)
    version(parent, data['row_version'])
    others, details = peers(session, resource_id, ns, address, read_scope)
    if data['confirm_shared'] and data['conflict_revision'] != details['conflict_revision']:
        raise IdentifierError(409, 'conflict_changed', details)
    if others and not data['confirm_shared']:
        raise IdentifierError(409, 'identifier_conflict', details)
    when = clock(session)
    last_end = session.scalar(select(func.max(Identifier.valid_until)).where(*matches(ns, address), Identifier.source_type == 'manual'))
    if last_end is not None and aware(when) < aware(last_end):
        raise IdentifierError(409, 'temporal_conflict')
    row = Identifier(id=uuid4(), resource_id=resource_id, identifier_type='ipv4',
        identifier_value=data['identifier_value'], normalized_value=address, namespace=ns,
        source_type='manual', source_instance=str(identity.actor_id), first_seen_at=when, last_seen_at=when,
        verification_status='unverified', verified_at=None, confidence=None,
        evidence={'method':'manual_declaration'}, valid_from=when, valid_until=None, created_at=when, updated_at=when)
    session.add(row); bump(parent, when)
    record_audit_event(session, actor_type=identity.actor_type, actor_id=identity.actor_id,
        action='inventory.identifier.added', entity_type='inventory.resource_identifier', entity_id=row.id,
        outcome='success', changes=dict(resource_id=str(resource_id), namespace=ns, normalized_value=address,
            valid_from=_timestamp(when), resource_row_version=parent.row_version),
        context=dict(shared_address_confirmed=bool(others), conflict_revision=details['conflict_revision'] if others else None))
    session.flush()
    return result(row, parent, True)


def close(session, resource_id, identifier_id, data, identity, scope):
    resource(session, resource_id, scope)
    initial = session.scalar(select(Identifier).where(Identifier.id == identifier_id, Identifier.resource_id == resource_id))
    if initial is None:
        raise IdentifierError(404, 'not_found')
    if initial.source_type != 'manual' or initial.identifier_type not in ('ipv4', 'IPv4'):
        raise IdentifierError(409, 'identifier_read_only')
    if initial.namespace is None:
        raise IdentifierError(409, 'identifier_conflict')
    key = (initial.namespace, initial.normalized_value)
    address_lock(session, *key)
    parent = resource(session, resource_id, scope, lock=True); editable(parent)
    row = session.scalar(select(Identifier).where(Identifier.id == identifier_id, Identifier.resource_id == resource_id)
                         .with_for_update().execution_options(populate_existing=True))
    if row is None:raise IdentifierError(404, 'not_found')
    if row.source_type != 'manual' or row.identifier_type not in ('ipv4','IPv4') or (row.namespace,row.normalized_value) != key:
        raise IdentifierError(409, 'identifier_read_only')
    version(parent, data['row_version'], noop=row.valid_until is not None)
    if row.valid_until is not None:
        return result(row, parent, False)
    when = clock(session)
    if aware(when) <= aware(row.valid_from):
        raise IdentifierError(409, 'temporal_conflict')
    row.valid_until = when; row.updated_at = when; bump(parent, when)
    record_audit_event(session, actor_type=identity.actor_type, actor_id=identity.actor_id,
        action='inventory.identifier.closed', entity_type='inventory.resource_identifier', entity_id=row.id,
        outcome='success', changes=dict(resource_id=str(resource_id), namespace=row.namespace,
            normalized_value=row.normalized_value, before={'valid_until':None}, after={'valid_until':_timestamp(when)},
            resource_row_version=parent.row_version))
    session.flush()
    return result(row, parent, True)


def list_rows(session, resource_id, scope, *, state='active', page=1, per_page=20, ns=None):
    parent = resource(session, resource_id, scope)
    filters = [Identifier.resource_id == resource_id, Identifier.identifier_type.in_(('ipv4','IPv4'))]
    if state != 'all':filters.append(Identifier.valid_until.is_(None) if state == 'active' else Identifier.valid_until.is_not(None))
    if ns is not None:filters.append(Identifier.namespace == ns)
    total = session.scalar(select(func.count()).select_from(Identifier).where(*filters))
    rows = session.scalars(select(Identifier).where(*filters).order_by(Identifier.created_at.desc(), Identifier.id)
                           .offset((page-1)*per_page).limit(per_page))
    return dict(items=[public(r) for r in rows], total=total, page=page, per_page=per_page, resource_row_version=parent.row_version)


def legacy_preflight(connection):
    """SELECT only; report counts, never rewrite legacy identifiers."""
    rows = connection.execute(text("SELECT resource_id,identifier_type,identifier_value,normalized_value,namespace,source_type,valid_until FROM inventory.resource_identifiers WHERE lower(btrim(identifier_type))='ipv4'")).mappings()
    counts = dict(noncanonical_type=0, invalid_namespace=0, invalid_ipv4=0, duplicate_active=0)
    seen = set()
    for r in rows:
        if r['identifier_type'] != 'ipv4':counts['noncanonical_type'] += 1
        try:normalized = ipv4(r['identifier_value'])
        except IdentifierError:normalized = None
        if normalized != r['normalized_value']:counts['invalid_ipv4'] += 1
        if r['source_type'] != 'manual':continue
        try:namespace(r['namespace'])
        except IdentifierError:counts['invalid_namespace'] += 1
        if r['valid_until'] is None:
            key = (r['resource_id'],r['namespace'],r['normalized_value'])
            if key in seen:counts['duplicate_active'] += 1
            seen.add(key)
    return counts
