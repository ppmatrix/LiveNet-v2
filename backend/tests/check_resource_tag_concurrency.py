"""Teste PostgreSQL de concorrência F0.64B (execução manual)."""

import os
import threading
import time
import uuid

import psycopg

from app.core.database import get_database_url


EXPECTED_DB = "livenet_f0_test"

if os.environ.get("DATABASE_NAME") != EXPECTED_DB:
    raise RuntimeError("Base de dados de teste obrigatória")

url = get_database_url()
if url.database != EXPECTED_DB:
    raise RuntimeError("Destino PostgreSQL inesperado")

connection_params = {
    "host": url.host,
    "port": url.port,
    "dbname": url.database,
    "user": url.username,
    "password": url.password,
}

resource_id = uuid.uuid4()
tag_id = uuid.uuid4()
first_id = uuid.uuid4()
second_id = uuid.uuid4()

first_inserted = threading.Event()
second_started = threading.Event()
allow_commit = threading.Event()
results = {}
errors = []


def connect():
    conn = psycopg.connect(**connection_params, connect_timeout=5)
    actual = conn.execute(
        "SELECT current_database()"
    ).fetchone()[0]

    if actual != EXPECTED_DB:
        conn.close()
        raise RuntimeError(f"Base inesperada: {actual}")

    conn.execute("SET statement_timeout = '8s'")
    conn.execute("SET lock_timeout = '5s'")
    return conn


def first_transaction():
    try:
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO inventory.resource_tags
                (id, resource_id, tag_id, assignment_source, valid_from)
                VALUES (%s, %s, %s, 'manual', '2026-01-01')
                """,
                (first_id, resource_id, tag_id),
            )
            first_inserted.set()

            if not allow_commit.wait(timeout=5):
                raise RuntimeError("Timeout de sincronização T1")

            conn.commit()
            results["first"] = "committed"
    except Exception as exc:
        errors.append(f"T1: {exc}")
        first_inserted.set()


def second_transaction():
    try:
        if not first_inserted.wait(timeout=5):
            raise RuntimeError("T1 não iniciou")

        with connect() as conn:
            second_started.set()
            try:
                conn.execute(
                    """
                    INSERT INTO inventory.resource_tags
                    (id, resource_id, tag_id, assignment_source, valid_from)
                    VALUES (%s, %s, %s, 'manual', '2026-02-01')
                    """,
                    (second_id, resource_id, tag_id),
                )
                results["second"] = "unexpected_success"
            except psycopg.errors.ExclusionViolation:
                results["second"] = "exclusion_violation"
                conn.rollback()
    except Exception as exc:
        errors.append(f"T2: {exc}")
        second_started.set()


with connect() as setup:
    setup.execute(
        """
        INSERT INTO inventory.resources
        (id, resource_type, display_name)
        VALUES (%s, 'host', 'F0.64B Concurrency Test')
        """,
        (resource_id,),
    )
    setup.execute(
        """
        INSERT INTO inventory.tags (id, key, value)
        VALUES (%s, 'test-concurrency', %s)
        """,
        (tag_id, str(tag_id)),
    )
    setup.commit()

try:
    t1 = threading.Thread(target=first_transaction)
    t2 = threading.Thread(target=second_transaction)

    t1.start()
    t2.start()

    if not first_inserted.wait(timeout=5):
        raise RuntimeError("T1 não inseriu")

    if not second_started.wait(timeout=5):
        raise RuntimeError("T2 não iniciou")

    # Dar tempo a T2 para encontrar a associação não confirmada.
    time.sleep(0.5)

    if not t2.is_alive():
        raise RuntimeError(
            "T2 terminou antes do COMMIT de T1; "
            "bloqueio concorrente não confirmado"
        )

    print("PASS 1: segunda transação permanece pendente")

    # Confirmar T1 para resolver o conflito temporal.
    allow_commit.set()

    t1.join(timeout=10)
    t2.join(timeout=10)

    if t1.is_alive() or t2.is_alive():
        raise RuntimeError("Threads não terminaram")

    if errors:
        raise RuntimeError("; ".join(errors))

    assert results.get("first") == "committed", results
    assert results.get("second") == "exclusion_violation", results

    print("PASS 2: primeira transação confirmada")
    print("PASS 3: associação concorrente rejeitada")
    print("RESULTADO: 3/3 TESTES APROVADOS")

finally:
    allow_commit.set()

    with connect() as cleanup:
        cleanup.execute(
            "DELETE FROM inventory.resource_tags WHERE resource_id = %s",
            (resource_id,),
        )
        cleanup.execute(
            "DELETE FROM inventory.tags WHERE id = %s",
            (tag_id,),
        )
        cleanup.execute(
            "DELETE FROM inventory.resources WHERE id = %s",
            (resource_id,),
        )
        cleanup.commit()
        print("CLEANUP: dados temporários eliminados")
