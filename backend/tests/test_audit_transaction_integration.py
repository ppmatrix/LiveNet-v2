"""Testes de integração transacional Inventory + Audit.

Executar exclusivamente contra a base isolada livenet_f0_test.
"""

import uuid

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.audit.models import AuditEvent
from app.audit.service import record_audit_event
from app.core.database import get_database_url
from app.inventory.models import Resource


@pytest.fixture
def database_connection():
    url = get_database_url()

    if url.database != "livenet_f0_test":
        pytest.fail(
            "Integration tests require DATABASE_NAME=livenet_f0_test"
        )

    engine = create_engine(url, pool_pre_ping=True)
    connection = engine.connect()
    outer_transaction = connection.begin()

    try:
        yield connection
    finally:
        if outer_transaction.is_active:
            outer_transaction.rollback()
        connection.close()
        engine.dispose()


def test_inventory_and_audit_same_transaction(database_connection):
    resource_id = uuid.uuid4()

    session = Session(
        bind=database_connection,
        autoflush=False,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    try:
        with session.begin():
            resource = Resource(
                id=resource_id,
                resource_type="test_device",
                display_name="F0.66B transaction test",
                administrative_state="active",
                attributes={},
            )
            session.add(resource)

            event = record_audit_event(
                session,
                actor_type="system",
                action="inventory.resource.created",
                entity_type="inventory.resource",
                entity_id=resource_id,
                outcome="success",
                changes={"display_name": "F0.66B transaction test"},
                context={"test": "f066b3"},
            )

        assert event.id is not None

        stored_resource = database_connection.execute(
            select(Resource).where(Resource.id == resource_id)
        ).first()

        stored_event = database_connection.execute(
            select(AuditEvent).where(AuditEvent.entity_id == resource_id)
        ).first()

        assert stored_resource is not None
        assert stored_event is not None

    finally:
        session.close()


def test_audit_database_failure_rolls_back_inventory(database_connection):
    """Uma falha de auditoria reverte a alteração de Inventory."""
    from sqlalchemy.exc import DataError

    resource_id = uuid.uuid4()

    session = Session(
        bind=database_connection,
        autoflush=False,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    try:
        with pytest.raises(DataError):
            with session.begin():
                session.add(
                    Resource(
                        id=resource_id,
                        resource_type="test_device",
                        display_name="F0.66B rollback test",
                        administrative_state="active",
                        attributes={},
                    )
                )

                event = record_audit_event(
                    session,
                    actor_type="system",
                    action="inventory.resource.created",
                    entity_type="inventory.resource",
                    entity_id=resource_id,
                    outcome="success",
                    changes={"display_name": "F0.66B rollback test"},
                )

                # Provoca uma violação real de VARCHAR(32) no PostgreSQL.
                # Apenas para testar o rollback da transação.
                event.outcome = "x" * 33

                session.flush()

        stored_resource = database_connection.execute(
            select(Resource.id).where(Resource.id == resource_id)
        ).first()

        stored_event = database_connection.execute(
            select(AuditEvent.id).where(AuditEvent.entity_id == resource_id)
        ).first()

        assert stored_resource is None
        assert stored_event is None

    finally:
        session.close()


def test_inventory_database_failure_rolls_back_audit(database_connection):
    """Uma falha de Inventory reverte o evento de auditoria."""
    from sqlalchemy.exc import IntegrityError

    resource_id = uuid.uuid4()

    session = Session(
        bind=database_connection,
        autoflush=False,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    try:
        with pytest.raises(IntegrityError):
            with session.begin():
                event = record_audit_event(
                    session,
                    actor_type="system",
                    action="inventory.resource.created",
                    entity_type="inventory.resource",
                    entity_id=resource_id,
                    outcome="success",
                    changes={"display_name": "F0.66B domain failure test"},
                )

                # Persiste primeiro o evento na transação.
                session.flush()
                assert event.id is not None

                # Provoca uma violação real de uma restrição Inventory.
                session.add(
                    Resource(
                        id=resource_id,
                        resource_type="test_device",
                        display_name="F0.66B domain failure test",
                        administrative_state="invalid_state",
                        attributes={},
                    )
                )

                session.flush()

        stored_resource = database_connection.execute(
            select(Resource.id).where(Resource.id == resource_id)
        ).first()

        stored_event = database_connection.execute(
            select(AuditEvent.id).where(AuditEvent.entity_id == resource_id)
        ).first()

        assert stored_resource is None
        assert stored_event is None

    finally:
        session.close()
