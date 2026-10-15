import pytest

from app.core.database import (
    get_database_url,
    check_database_connection,
)


def test_database_password_file_required(monkeypatch):
    monkeypatch.delenv(
        "DATABASE_PASSWORD_FILE",
        raising=False,
    )

    with pytest.raises(
        RuntimeError,
        match="DATABASE_PASSWORD_FILE is required",
    ):
        get_database_url()


def test_database_url_from_secret(monkeypatch, tmp_path):
    secret = tmp_path / "db_password.txt"
    secret.write_text("test-password\n")

    monkeypatch.setenv(
        "DATABASE_PASSWORD_FILE",
        str(secret),
    )
    monkeypatch.setenv("DATABASE_HOST", "db")
    monkeypatch.setenv("DATABASE_PORT", "5432")
    monkeypatch.setenv("DATABASE_NAME", "livenet")
    monkeypatch.setenv("DATABASE_USER", "livenet")

    url = get_database_url()

    assert url.drivername == "postgresql+psycopg"
    assert url.username == "livenet"
    assert url.password == "test-password"
    assert url.host == "db"
    assert url.port == 5432
    assert url.database == "livenet"


def test_database_connection_success(monkeypatch):
    class FakeResult:
        def scalar_one(self):
            return 1

    class FakeConnection:
        def execute(self, statement):
            return FakeResult()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class FakeEngine:
        disposed = False

        def connect(self):
            return FakeConnection()

        def dispose(self):
            self.disposed = True

    engine = FakeEngine()

    monkeypatch.setattr(
        "app.core.database.create_database_engine",
        lambda: engine,
    )

    assert check_database_connection() is True
    assert engine.disposed is True


def test_database_connection_disposes_on_error(monkeypatch):
    class FakeEngine:
        disposed = False

        def connect(self):
            raise RuntimeError("Connection failed")

        def dispose(self):
            self.disposed = True

    engine = FakeEngine()

    monkeypatch.setattr(
        "app.core.database.create_database_engine",
        lambda: engine,
    )

    with pytest.raises(
        RuntimeError,
        match="Connection failed",
    ):
        check_database_connection()

    assert engine.disposed is True
