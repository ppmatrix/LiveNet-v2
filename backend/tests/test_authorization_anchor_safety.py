"""Barreiras AUTH-03 verificadas sem drivers, sockets ou PostgreSQL."""

from unittest.mock import Mock

import pytest
from sqlalchemy.exc import MultipleResultsFound, NoResultFound, OperationalError

import test_authorization_anchor_integration as integration


@pytest.fixture
def settings(tmp_path):
    secret = tmp_path / "password"
    secret.write_text("offline-test-secret")
    return {
        "AUTH03_ANCHOR_TEST_DATABASE_URL": "postgresql+psycopg://tester@db/livenet_auth03_test",
        "AUTH03_ANCHOR_TEST_SYSTEM_IDENTIFIER": "1234567890123456789",
        "AUTH03_ANCHOR_TEST_PASSWORD_FILE": str(secret),
    }


@pytest.mark.parametrize("key", [
    "AUTH03_ANCHOR_TEST_DATABASE_URL",
    "AUTH03_ANCHOR_TEST_SYSTEM_IDENTIFIER",
    "AUTH03_ANCHOR_TEST_PASSWORD_FILE",
])
def test_missing_configuration_blocks_before_engine(settings, key, monkeypatch):
    engine = Mock()
    monkeypatch.setattr(integration, "create_engine", engine)
    settings.pop(key)
    with pytest.raises(pytest.fail.Exception):
        with integration.isolated_connection(settings):
            pytest.fail("Nao pode disponibilizar ligacao")
    engine.assert_not_called()


@pytest.mark.parametrize("url", [
    "postgresql+psycopg://tester@db/livenet",
    "postgresql+psycopg://tester@db/livenet_f0_test",
    "postgresql+psycopg://tester@localhost/livenet_auth03_test",
    "postgresql+psycopg://tester@127.0.0.1/livenet_auth03_test",
    "postgresql+psycopg://tester@[::1]/livenet_auth03_test",
    "postgresql+psycopg://tester@db/livenet_auth03_test?dbname=livenet",
    "postgresql+psycopg://tester@db/livenet_auth03_test?host=other",
    "postgresql+psycopg://tester:secret@db/livenet_auth03_test",
    "postgresql+psycopg://tester@db:9999/livenet_auth03_test",
    "sqlite:///livenet_auth03_test", "invalid-url",
])
def test_unsafe_url_rejected(settings, url):
    settings["AUTH03_ANCHOR_TEST_DATABASE_URL"] = url
    with pytest.raises(pytest.fail.Exception, match="nao autorizada"):
        integration.load_test_configuration(settings)


@pytest.mark.parametrize("identifier", ["", "0", "-1", "abc", " 123", str(2**64)])
def test_invalid_identity(settings, identifier):
    settings["AUTH03_ANCHOR_TEST_SYSTEM_IDENTIFIER"] = identifier
    with pytest.raises(pytest.fail.Exception):
        integration.load_test_configuration(settings)


@pytest.mark.parametrize("contents", [None, "  \n"])
def test_unavailable_secret(settings, tmp_path, contents):
    secret = tmp_path / "another-secret"
    if contents is not None:
        secret.write_text(contents)
    settings["AUTH03_ANCHOR_TEST_PASSWORD_FILE"] = str(secret)
    with pytest.raises(pytest.fail.Exception, match="Secret AUTH-03"):
        integration.load_test_configuration(settings)


@pytest.fixture
def engine_mock(monkeypatch):
    engine = Mock()
    conn = engine.connect.return_value.__enter__ = Mock()
    connection = conn.return_value
    engine.connect.return_value.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(integration, "create_engine", Mock(return_value=engine))
    return engine, connection


def query_results(conn, values):
    results = []
    for value in values:
        result = Mock()
        result.scalar_one.return_value = value
        results.append(result)
    conn.execute.side_effect = results
    return results


@pytest.mark.parametrize("values", [
    ["livenet"],
    ["livenet_auth03_test", False],
    ["livenet_auth03_test", True, "999"],
    ["livenet_auth03_test", True, "1234567890123456789", "f066a01a7230"],
])
def test_preflight_failure_rolls_back_without_yield(settings, engine_mock, values):
    engine, conn = engine_mock
    query_results(conn, values)
    yielded = False
    with pytest.raises(pytest.fail.Exception):
        with integration.isolated_connection(settings):
            yielded = True
    assert not yielded
    conn.begin.assert_called_once_with()
    conn.begin.return_value.rollback.assert_called_once_with()
    engine.dispose.assert_called_once_with()
    assert all(str(call.args[0]).startswith("SELECT ") for call in conn.execute.call_args_list)


@pytest.mark.parametrize("body_fails", [False, True])
def test_valid_preflight_always_rolls_back(settings, engine_mock, body_fails):
    engine, conn = engine_mock
    query_results(conn, ["livenet_auth03_test", True, "1234567890123456789", "f067a01a7230"])
    def exercise():
        with integration.isolated_connection(settings) as actual:
            assert actual is conn
            assert conn.execute.call_count == 4
            if body_fails:
                raise RuntimeError("simulated failure")
    if body_fails:
        with pytest.raises(RuntimeError, match="simulated failure"):
            exercise()
    else:
        exercise()
    conn.begin.return_value.rollback.assert_called_once_with()
    conn.commit.assert_not_called()
    engine.dispose.assert_called_once_with()


@pytest.mark.parametrize("stage", ["connect", "query"])
def test_database_errors_are_sanitized(settings, engine_mock, stage):
    engine, conn = engine_mock
    error = OperationalError("secret SQL", {}, Exception("private-password"))
    if stage == "connect":
        engine.connect.side_effect = error
    else:
        conn.execute.side_effect = error
    with pytest.raises(pytest.fail.Exception) as failure:
        with integration.isolated_connection(settings):
            pass
    assert "private-password" not in str(failure.value)
    assert "secret SQL" not in str(failure.value)
    engine.dispose.assert_called_once_with()
    if stage == "query":
        conn.begin.return_value.rollback.assert_called_once_with()


@pytest.mark.parametrize("error_type", [NoResultFound, MultipleResultsFound])
def test_missing_or_multiple_revision_blocks(settings, engine_mock, error_type):
    engine, conn = engine_mock
    results = query_results(conn, ["livenet_auth03_test", True, "1234567890123456789", None])
    results[-1].scalar_one.side_effect = error_type
    with pytest.raises(pytest.fail.Exception, match="revisao por validar"):
        with integration.isolated_connection(settings):
            pytest.fail("Nao pode disponibilizar ligacao")
    conn.begin.return_value.rollback.assert_called_once_with()
    engine.dispose.assert_called_once_with()
