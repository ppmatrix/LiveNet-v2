import os
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker


def get_database_url():
    password_file = os.getenv("DATABASE_PASSWORD_FILE")

    if not password_file:
        raise RuntimeError(
            "DATABASE_PASSWORD_FILE is required"
        )

    password = Path(password_file).read_text().strip()

    return URL.create(
        drivername="postgresql+psycopg",
        username=os.getenv("DATABASE_USER", "livenet"),
        password=password,
        host=os.getenv("DATABASE_HOST", "db"),
        port=int(os.getenv("DATABASE_PORT", "5432")),
        database=os.getenv("DATABASE_NAME", "livenet"),
    )


def create_database_engine():
    return create_engine(
        get_database_url(),
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
    )


def create_session_factory(engine):
    """Create a session factory for an existing SQLAlchemy engine."""
    return sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )


def check_database_connection():
    engine = create_database_engine()

    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            return result.scalar_one() == 1
    finally:
        engine.dispose()
