import pytest

from app import create_app


def test_development_config():
    app = create_app("development")

    assert app.config["DEBUG"] is True
    assert app.config["TESTING"] is False


def test_testing_config():
    app = create_app("testing")

    assert app.config["TESTING"] is True
    assert app.config["DEBUG"] is False


def test_production_config():
    app = create_app("production")

    assert app.config["DEBUG"] is False
    assert app.config["TESTING"] is False


def test_invalid_config():
    with pytest.raises(ValueError):
        create_app("invalid")


def test_default_environment(monkeypatch):
    monkeypatch.delenv("LIVENET_ENV", raising=False)

    app = create_app()

    assert app.config["DEBUG"] is False
    assert app.config["TESTING"] is False


def test_environment_variable_selection(monkeypatch):
    monkeypatch.setenv("LIVENET_ENV", "production")

    app = create_app()

    assert app.config["DEBUG"] is False
    assert app.config["TESTING"] is False


def test_invalid_environment_variable(monkeypatch):
    monkeypatch.setenv("LIVENET_ENV", "invalid")

    with pytest.raises(ValueError, match="Invalid LIVENET_ENV"):
        create_app()
