"""Etapa 209D.24: testes exclusivamente offline, sem Docker/PostgreSQL."""

from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest
from sqlalchemy.exc import OperationalError

import auth03_alembic_executor as executor

from scripts.postgres.tests.dev09b_historical_fixtures import historical_tree, historical_auth

PRIVATE_READ = executor.private_read


@pytest.fixture
def historical_executor(tmp_path, monkeypatch):
    return historical_auth(historical_tree(tmp_path), monkeypatch)


@pytest.fixture(autouse=True)
def no_external_io(monkeypatch):
    monkeypatch.setattr(executor, "create_engine", Mock(side_effect=AssertionError("PostgreSQL real proibido")))
    monkeypatch.setattr(executor.subprocess, "run", Mock(side_effect=AssertionError("Docker real proibido")))
    monkeypatch.setattr(executor, "private_read", Mock(side_effect=AssertionError("Secret real proibido")))
    for key in tuple(executor.os.environ):
        if key.startswith(("PG", "DATABASE_", "F066C_", "AUTH03_")):
            monkeypatch.delenv(key)


@pytest.fixture
def config():
    return {
        "project": executor.PROJECT, "database": executor.DATABASE,
        "system_identifier": executor.SYSTEM_IDENTIFIER,
        "username": "livenet", "host": executor.DB_CONTAINER,
        "container_id": "a" * 64, "network_id": "b" * 64,
        "executor_id": "c" * 64, "db_image_id": "sha256:" + "d" * 64,
        "executor_image_id": "sha256:" + "e" * 64,
        "volume_created_at": "2026-10-20T12:00:00Z", "uid": 10001, "gid": 10001,
    }


@pytest.mark.parametrize("key,value", [
    ("database", "livenet"), ("database", "livenet_f0_test"),
    ("system_identifier", "7698100764292259880"),
    ("project", "livenetv2-f066c"), ("host", "db"),
    ("host", "localhost"), ("username", "postgres"), ("uid", 0),
    ("container_id", "short"), ("db_image_id", "postgres:16-alpine"),
])
def test_configuration_rejects_other_identity(config, key, value):
    config[key] = value
    with pytest.raises(executor.Refused):
        executor.validate_config(config)


@pytest.mark.parametrize("key", list(json.loads((executor.ROOT / "scripts/postgres/auth03_executor.example.json").read_text())))
def test_incomplete_configuration(config, key):
    del config[key]
    with pytest.raises(executor.Refused):
        executor.validate_config(config)


def test_unknown_configuration_field(config):
    config["password"] = "do-not-log"
    with pytest.raises(executor.Refused):
        executor.validate_config(config)


@pytest.mark.parametrize("operation", list(executor.MUTATIONS) + ["sql", "upgrade", "head", "base"])
def test_operations_block_before_external_access(config, operation):
    with pytest.raises(executor.Refused):
        executor.host_run(operation, config)
    executor.subprocess.run.assert_not_called()
    executor.create_engine.assert_not_called()
    executor.private_read.assert_not_called()


@pytest.mark.parametrize("operation", list(executor.MUTATIONS))
def test_valid_future_plans_still_cannot_execute(operation):
    source, target = executor.MUTATIONS[operation]
    plan = executor.migration_plan(operation, source, target)
    with pytest.raises(executor.Refused, match="bloqueadas"):
        executor.invoke_migration(Mock(), plan)


@pytest.mark.parametrize("source,target", [(executor.PREVIOUS, "head"), (executor.AUTH03, "base"),
                                         (None, executor.AUTH03), (executor.AUTH03, executor.AUTH03)])
def test_arbitrary_targets_and_unexpected_sources_rejected(source, target):
    with pytest.raises(executor.Refused):
        executor.migration_plan("upgrade-auth03", source, target)


def test_alembic_configuration_never_has_production_url(monkeypatch):
    monkeypatch.setenv("DATABASE_NAME", "livenet")
    connection = Mock()
    config = executor.alembic_config(connection)
    assert config.attributes["connection"] is connection
    assert config.attributes["auth03_require_external_connection"] is True
    assert config.get_main_option("sqlalchemy.url") is None
    with pytest.raises(executor.Refused):
        executor.alembic_config(None)


def test_env_guard_prevents_fallback(monkeypatch):
    from alembic import context
    import app.core.database as database
    from alembic.config import Config
    import runpy

    config = Config()
    config.attributes["auth03_require_external_connection"] = True
    monkeypatch.setattr(context, "config", config, raising=False)
    monkeypatch.setattr(context, "is_offline_mode", lambda: False)
    fallback = Mock(side_effect=AssertionError("Fallback de producao"))
    monkeypatch.setattr(database, "get_database_url", fallback)
    with pytest.raises(RuntimeError, match="externa explicita"):
        runpy.run_path(str(executor.ROOT / "backend/migrations/env.py"))
    fallback.assert_not_called()


def test_env_uses_exact_external_connection(monkeypatch):
    from alembic import context
    import app.core.database as database
    from alembic.config import Config
    import runpy

    from migrations.dev09b_prerequisites import MissingParameter

    config = Config()
    connection = Mock()
    connection.in_transaction.return_value = True
    connection.dialect.name = "postgresql"
    config.attributes.update(connection=connection, auth03_require_external_connection=True)
    monkeypatch.setattr(context, "config", config, raising=False)
    monkeypatch.setattr(context, "is_offline_mode", lambda: False)
    configure = Mock()
    monkeypatch.setattr(context, "configure", configure)
    monkeypatch.setattr(context, "begin_transaction", MagicMock())
    run_migrations = Mock()
    monkeypatch.setattr(context, "run_migrations", run_migrations)
    fallback = Mock(side_effect=AssertionError("Fallback de producao"))
    monkeypatch.setattr(database, "get_database_url", fallback)
    with pytest.raises(MissingParameter, match="dev09b_prepared_context"):
        runpy.run_path(str(executor.ROOT / "backend/migrations/env.py"))
    configure.assert_not_called()
    run_migrations.assert_not_called()
    fallback.assert_not_called()


@pytest.fixture
def docker_snapshot(config):
    def labels(key, value):
        return {"com.docker.compose.project": executor.PROJECT, "com.docker.compose." + key: value}
    base = {
        "HostConfig": {"PortBindings": {}, "Privileged": False, "NetworkMode": executor.NETWORK},
        "NetworkSettings": {"Ports": {"5432/tcp": None}, "Networks": {
            executor.NETWORK: {"NetworkID": config["network_id"], "IPAddress": "172.25.0.2"}}},
        "State": {"Running": True, "Health": {"Status": "healthy"}},
    }
    secret = {"Type": "bind", "Source": str(executor.ROOT / "secrets/auth03_db_password.txt"),
              "Destination": "/run/secrets/db_password", "RW": False}
    db = deepcopy(base)
    db.update({"Id": config["container_id"], "Image": config["db_image_id"], "Name": "/" + executor.DB_CONTAINER,
               "Config": {"Image": "postgres:16-alpine", "Labels": labels("service", "db"), "Env": [
                   "POSTGRES_DB=" + executor.DATABASE, "POSTGRES_USER=livenet",
                   "POSTGRES_PASSWORD_FILE=/run/secrets/db_password"]},
               "Mounts": [{"Type": "volume", "Name": executor.VOLUME, "Destination": "/var/lib/postgresql/data"}, secret]})
    runner = deepcopy(base)
    runner.update({"Id": config["executor_id"], "Image": config["executor_image_id"],
                   "Name": "/" + executor.PROJECT + "-executor-1",
                   "Config": {"User": "10001:10001", "Labels": labels("service", "executor"), "Env": []},
                   "Mounts": [{**secret, "Destination": executor.SECRET}]})
    runner["HostConfig"].update({"ReadonlyRootfs": True, "CapDrop": ["ALL"],
                                 "SecurityOpt": ["no-new-privileges:true"]})
    network = {"Id": config["network_id"], "Name": executor.NETWORK, "Internal": True,
               "Driver": "bridge", "Labels": labels("network", "auth03_backend"),
               "Containers": {config["container_id"]: {}, config["executor_id"]: {}}}
    volume = {"Name": executor.VOLUME, "Driver": "local", "Options": None,
              "CreatedAt": config["volume_created_at"], "Labels": labels("volume", "auth03_postgres_data")}
    return db, network, volume, runner


def test_valid_docker_snapshot(config, docker_snapshot):
    assert executor.validate_docker(config, *docker_snapshot) == "172.25.0.2"


@pytest.mark.parametrize("fault", ["project", "port", "network", "network_member", "volume", "secret", "socket", "root", "image"])
def test_docker_preflight_faults(config, docker_snapshot, fault):
    db, network, volume, runner = docker_snapshot
    if fault == "project":
        db["Config"]["Labels"]["com.docker.compose.project"] = "livenetv2"
    elif fault == "port":
        db["HostConfig"]["PortBindings"] = {"5432/tcp": [{"HostPort": "5432"}]}
    elif fault == "network":
        network["Internal"] = False
    elif fault == "network_member":
        network["Containers"]["unknown"] = {}
    elif fault == "volume":
        volume["CreatedAt"] = "changed"
    elif fault == "secret":
        db["Mounts"][1]["Source"] = "/secrets/db_password.txt"
    elif fault == "socket":
        runner["Mounts"].append({"Type": "bind", "Destination": "/var/run/docker.sock"})
    elif fault == "root":
        runner["Config"]["User"] = "0:0"
    elif fault == "image":
        db["Image"] = "sha256:" + "f" * 64
    with pytest.raises(executor.Refused):
        executor.validate_docker(config, db, network, volume, runner)


def result(value, method="scalar_one"):
    mock = Mock()
    getattr(mock, method).return_value = value
    return mock


def database_results(identifier=executor.SYSTEM_IDENTIFIER, revisions=None, relations=None, schemas=None):
    values = [result((executor.DATABASE, "livenet", "livenet", "172.25.0.2", 5432, 160010), "one"),
              result(True), result(identifier), result(revisions is not None)]
    if revisions is not None:
        revision_result = Mock()
        revision_result.scalars.return_value.all.return_value = revisions
        values.append(revision_result)
    values.append(result(relations or [], "all"))
    schema_result = Mock()
    schema_result.scalars.return_value.all.return_value = schemas or ["public"]
    values.append(schema_result)
    return values


def test_empty_database_identity(config):
    conn = Mock()
    conn.execute.side_effect = database_results()
    assert executor.read_database_state(conn, config, "172.25.0.2")["revision"] is None


@pytest.mark.parametrize("postgres_address", ["172.26.0.2", "172.26.0.2/32"])
def test_session_ipv4_normalization(config, postgres_address):
    conn = Mock()
    values = database_results()
    values[0] = result((executor.DATABASE, "livenet", "livenet", postgres_address, 5432, 160010), "one")
    conn.execute.side_effect = values
    assert executor.read_database_state(conn, config, "172.26.0.2")["revision"] is None


@pytest.mark.parametrize("postgres_address,docker_address", [
    ("172.26.0.3", "172.26.0.2"),
    ("172.26.0.20/32", "172.26.0.2"),
    ("172.26.0.3/24", "172.26.0.2"),
    ("invalid", "172.26.0.2"),
    ("172.26.0.2/33", "172.26.0.2"),
    (None, "172.26.0.2"),
    ("::1", "172.26.0.2"),
    ("::ffff:172.26.0.2/128", "172.26.0.2"),
    ("172.26.0.2/32", "::ffff:172.26.0.2"),
    ("172.26.0.2/32", "invalid"),
])
def test_session_rejects_invalid_or_different_address(config, postgres_address, docker_address):
    conn = Mock()
    conn.execute.return_value = result(
        (executor.DATABASE, "livenet", "livenet", postgres_address, 5432, 160010), "one"
    )
    with pytest.raises(executor.Refused):
        executor.read_database_state(conn, config, docker_address)
    assert conn.execute.call_count == 1


@pytest.mark.parametrize("index,value", [
    (0, "livenet"), (1, "postgres"), (2, "postgres"), (4, 5433), (5, 160011),
])
def test_session_other_identity_checks_remain_strict(config, index, value):
    row = [executor.DATABASE, "livenet", "livenet", "172.26.0.2/32", 5432, 160010]
    row[index] = value
    conn = Mock()
    conn.execute.return_value = result(tuple(row), "one")
    with pytest.raises(executor.Refused, match="Identidade da sessao PostgreSQL inesperada"):
        executor.read_database_state(conn, config, "172.26.0.2")
    assert conn.execute.call_count == 1


@pytest.mark.parametrize("fault", ["database", "system_identifier", "multiple", "unknown_revision", "empty_version", "objects", "schemas", "privilege"])
def test_postgres_preflight_rejects_faults(config, fault):
    values = database_results()
    if fault == "database":
        values[0] = result(("livenet", "livenet", "livenet", "172.25.0.2", 5432, 160010), "one")
    elif fault == "system_identifier":
        values[2] = result("wrong")
    elif fault == "multiple":
        values = database_results(revisions=[executor.PREVIOUS, executor.AUTH03])
    elif fault == "unknown_revision":
        values = database_results(revisions=["unexpected"])
    elif fault == "empty_version":
        values = database_results(revisions=[])
    elif fault == "objects":
        values = database_results(relations=[("public", "leftover")])
    elif fault == "schemas":
        values = database_results(schemas=["public", "authorization"])
    elif fault == "privilege":
        values[1] = result(False)
    conn = Mock()
    conn.execute.side_effect = values
    with pytest.raises(executor.Refused):
        executor.read_database_state(conn, config, "172.25.0.2")


@pytest.fixture
def runner_io(config, monkeypatch):
    engine = Mock()
    conn = Mock()
    engine.connect.return_value.__enter__ = Mock(return_value=conn)
    engine.connect.return_value.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(executor, "create_engine", Mock(return_value=engine))
    monkeypatch.setattr(executor, "private_read", Mock(return_value=b"test-password-only"))
    monkeypatch.setattr(executor, "verify_bundle", lambda: "bundle")
    evidence = {"issued_at": executor.time.time(), "db_ipv4": "172.25.0.2", "bundle_sha256": "bundle"}
    return engine, conn, evidence


@pytest.mark.parametrize("fault", [False, True])
def test_runner_read_always_rolls_back(config, runner_io, fault):
    engine, conn, evidence = runner_io
    if fault:
        conn.execute.side_effect = OperationalError("private SQL", {}, Exception("password"))
        with pytest.raises(OperationalError):
            executor.runner_read("inspect", config, evidence)
    else:
        conn.execute.side_effect = database_results()
        executor.runner_read("inspect", config, evidence)
    conn.begin.return_value.rollback.assert_called_once()
    conn.commit.assert_not_called()
    engine.dispose.assert_called_once()
    _, kwargs = executor.create_engine.call_args
    assert kwargs["hide_parameters"] and not kwargs["echo"]
    assert "default_transaction_read_only=on" in kwargs["connect_args"]["options"]


@pytest.mark.parametrize("fault", ["expired", "bundle", "environment"])
def test_runner_blocks_before_secret_or_connection(config, runner_io, monkeypatch, fault):
    _, _, evidence = runner_io
    if fault == "expired":
        evidence["issued_at"] -= 31
    elif fault == "bundle":
        evidence["bundle_sha256"] = "tampered"
    else:
        monkeypatch.setenv("PGSERVICE", "production")
    with pytest.raises(executor.Refused):
        executor.runner_read("inspect", config, evidence)
    executor.private_read.assert_not_called()
    executor.create_engine.assert_not_called()


def test_preflight_failure_stops_before_exec(config, monkeypatch):
    monkeypatch.setattr(executor, "host_preflight", Mock(side_effect=executor.Refused("Falha preflight")))
    with pytest.raises(executor.Refused):
        executor.host_run("inspect", config)
    executor.subprocess.run.assert_not_called()


def test_changed_ip_stops_before_exec(config, monkeypatch):
    monkeypatch.setattr(executor, "host_preflight", Mock(side_effect=[
        {"db_ipv4": "172.25.0.2", "bundle_sha256": "same"},
        {"db_ipv4": "172.25.0.3", "bundle_sha256": "same"},
    ]))
    with pytest.raises(executor.Refused, match="alterado"):
        executor.host_run("inspect", config)
    executor.subprocess.run.assert_not_called()


def test_credentials_and_external_errors_not_printed(config, monkeypatch, capsys):
    monkeypatch.setattr(executor, "private_read", Mock(return_value=json.dumps(config).encode()))
    monkeypatch.setattr(executor, "host_preflight", Mock(side_effect=RuntimeError("PASSWORD-do-not-print")))
    assert executor.main(["--config", "dummy", "inspect"]) == 2
    output = capsys.readouterr()
    assert not output.out and "PASSWORD" not in output.err and "Traceback" not in output.err


def test_cli_mutations_cannot_be_enabled_by_config_or_environment(monkeypatch, capsys):
    monkeypatch.setenv("AUTH03_EXECUTE", "1")
    assert executor.main(["--config", "nonexistent", "upgrade-baseline"]) == 2
    executor.private_read.assert_not_called()
    assert "bloqueadas" in capsys.readouterr().err


def test_verified_manifest_and_tampering(tmp_path):
    with pytest.raises(executor.Refused, match="Historical AUTH-03 bundle incompatible"):
        executor.verify_bundle()
    # Um manifesto vazio nao pode retirar fontes do conjunto verificado.
    target = tmp_path / executor.MANIFEST
    target.parent.mkdir(parents=True)
    target.write_text("{}")
    with pytest.raises(executor.Refused):
        executor.verify_bundle(tmp_path)


def test_future_lock_conflict_and_wrong_source(config, monkeypatch):
    conn = Mock()
    plan = executor.migration_plan("upgrade-auth03", executor.PREVIOUS, executor.AUTH03)
    with pytest.raises(executor.Refused, match="Historical AUTH-03 bundle incompatible"):
        executor.future_transaction_preflight(conn, plan, config, "172.25.0.2")
    conn.execute.assert_not_called()


def test_historical_2f86582_lock_conflict_and_wrong_source(config, monkeypatch, historical_executor):
    old = historical_executor
    conn = Mock()
    conn.execute.return_value.scalar_one.return_value = False
    plan = old.migration_plan("upgrade-auth03", old.PREVIOUS, old.AUTH03)
    with pytest.raises(old.Refused, match="em curso"):
        old.future_transaction_preflight(conn, plan, config, "172.25.0.2")
    conn.execute.return_value.scalar_one.return_value = True
    monkeypatch.setattr(old, "read_database_state", lambda *args: {"revision": None})
    with pytest.raises(old.Refused, match="origem"):
        old.future_transaction_preflight(conn, plan, config, "172.25.0.2")


def test_historical_2f86582_verified_manifest_and_tampering(historical_executor):
    old = historical_executor
    assert len(old.verify_bundle()) == 64
    source = old.ROOT / "backend/alembic.ini"
    source.write_bytes(source.read_bytes() + b"\n# tampered fixture\n")
    with pytest.raises(old.Refused, match="Integridade"):
        old.verify_bundle()


def test_historical_2f86582_env_exact_connection(monkeypatch, historical_executor):
    from alembic import context
    from alembic.config import Config
    import app.core.database as database
    import runpy

    connection = Mock()
    config = Config()
    config.attributes.update(connection=connection, auth03_require_external_connection=True)
    monkeypatch.setattr(context, "config", config, raising=False)
    monkeypatch.setattr(context, "is_offline_mode", lambda: False)
    configure = Mock()
    monkeypatch.setattr(context, "configure", configure)
    monkeypatch.setattr(context, "begin_transaction", MagicMock())
    monkeypatch.setattr(context, "run_migrations", Mock())
    fallback = Mock(side_effect=AssertionError("No database fallback"))
    monkeypatch.setattr(database, "get_database_url", fallback)
    runpy.run_path(str(historical_executor.ROOT / "backend/migrations/env.py"))
    assert configure.call_args.kwargs["connection"] is connection
    fallback.assert_not_called()


def test_scope_is_specific_and_does_not_authorize(config):
    plan = executor.migration_plan("upgrade-auth03", executor.PREVIOUS, executor.AUTH03)
    scope = executor.authorization_scope(plan, config, "digest")
    assert scope["system_identifier"] == executor.SYSTEM_IDENTIFIER
    assert scope["operation"] == "upgrade-auth03" and scope["source"] == executor.PREVIOUS
    assert "approved" not in scope and "password" not in scope


@pytest.mark.parametrize("fault", ["permissions", "symlink", "hardlink", "oversize"])
def test_private_file_refusals(tmp_path, fault):
    path = tmp_path / "offline-secret"
    path.write_bytes(b"fixture-only")
    path.chmod(0o600)
    if fault == "permissions":
        path.chmod(0o644)
    elif fault == "symlink":
        link = tmp_path / "link"
        link.symlink_to(path)
        path = link
    elif fault == "hardlink":
        (tmp_path / "other-link").hardlink_to(path)
    with pytest.raises((executor.Refused, OSError)):
        PRIVATE_READ(path, 1 if fault == "oversize" else 100)


def test_private_file_success(tmp_path):
    path = tmp_path / "fixture"
    path.write_bytes(b"offline-data")
    path.chmod(0o600)
    assert PRIVATE_READ(path) == b"offline-data"


@pytest.mark.parametrize("expected", ["empty", executor.AUTH03])
def test_verify_revision_uses_explicit_expected_value(config, runner_io, expected):
    _, conn, evidence = runner_io
    conn.execute.side_effect = database_results()
    if expected == "empty":
        assert executor.runner_read("verify-revision", config, evidence, expected)["revision"] is None
    else:
        with pytest.raises(executor.Refused, match="esperada"):
            executor.runner_read("verify-revision", config, evidence, expected)
        conn.begin.return_value.rollback.assert_called_once()


def test_read_inspection_transport_contains_no_password(config, monkeypatch):
    evidence = {"db_ipv4": "172.25.0.2", "bundle_sha256": "digest", "issued_at": executor.time.time()}
    monkeypatch.setattr(executor, "host_preflight", Mock(return_value=evidence))
    run = Mock(return_value=Mock(returncode=0, stdout=json.dumps({"revision": None, "relations": []})))
    monkeypatch.setattr(executor.subprocess, "run", run)
    assert executor.host_run("inspect", config)["revision"] is None
    assert run.call_args.args[0][:4] == ["docker", "exec", "-i", config["executor_id"]]
    assert "password" not in run.call_args.kwargs["input"]
    assert run.call_args.kwargs["check"] is False


def test_preflight_only_does_not_run_postgres(config, monkeypatch):
    monkeypatch.setattr(executor, "host_preflight", Mock(return_value={}))
    assert executor.host_run("preflight", config)["postgresql"] == "not-contacted"
    executor.subprocess.run.assert_not_called()
    executor.create_engine.assert_not_called()


def test_baseline_revision_is_accepted(config):
    conn = Mock()
    conn.execute.side_effect = database_results(revisions=[executor.PREVIOUS],
                                              schemas=["public", "inventory", "audit"])
    assert executor.read_database_state(conn, config, "172.25.0.2")["revision"] == executor.PREVIOUS
