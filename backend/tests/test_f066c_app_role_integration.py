"""Integração Inventory + Audit com privilégios de livenet_app.

Executar exclusivamente na instância PostgreSQL isolada F0.66C.
"""

import uuid

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.audit.models import AuditEvent
from app.audit.service import record_audit_event
from app.core.database import get_database_url
from app.inventory.models import Resource


@pytest.mark.integration
def test_inventory_and_audit_with_app_role():
    url = get_database_url()

    if url.database != "livenet_f0_test":
        pytest.fail("F0.66C requires DATABASE_NAME=livenet_f0_test")

    engine = create_engine(url, pool_pre_ping=True)

    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            resource_id = uuid.uuid4()

            try:
                database = connection.execute(
                    text("SELECT current_database()")
                ).scalar_one()

                if database != "livenet_f0_test":
                    pytest.fail("Unexpected database")

                connection.execute(text("SET LOCAL ROLE livenet_app"))

                role = connection.execute(
                    text("SELECT current_user")
                ).scalar_one()

                assert role == "livenet_app"

                session = Session(
                    bind=connection,
                    autoflush=False,
                    expire_on_commit=False,
                    join_transaction_mode="create_savepoint",
                )

                try:
                    with session.begin():
                        session.add(
                            Resource(
                                id=resource_id,
                                resource_type="test_device",
                                display_name="F0.66C app role integration",
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
                            changes={
                                "display_name": "F0.66C app role integration"
                            },
                            context={"test": "f066c_app_role"},
                        )

                    assert event.id is not None

                    stored_resource = connection.execute(
                        select(Resource).where(Resource.id == resource_id)
                    ).first()

                    stored_event = connection.execute(
                        select(AuditEvent).where(
                            AuditEvent.entity_id == resource_id
                        )
                    ).first()

                    assert stored_resource is not None
                    assert stored_event is not None

                finally:
                    session.close()

            finally:
                if transaction.is_active:
                    transaction.rollback()

            residual_resource = connection.execute(
                select(Resource.id).where(Resource.id == resource_id)
            ).first()

            residual_event = connection.execute(
                select(AuditEvent.id).where(
                    AuditEvent.entity_id == resource_id
                )
            ).first()

            assert residual_resource is None
            assert residual_event is None

    finally:
        engine.dispose()
