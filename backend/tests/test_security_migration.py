"""Read declarations and build SQLAlchemy metadata only: never call migration
upgrade/downgrade, run Alembic commands, generate DDL or connect to any database.
"""

import ast
from pathlib import Path
import runpy
from unittest.mock import Mock

from alembic.config import Config
from alembic.script import ScriptDirectory
import pytest
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.core.models import Base
from security_migrations.contract import (
    INITIAL_REVISION, SCRIPT_LOCATION, TABLE_NAMES, VERSION_SCHEMA, VERSION_TABLE,
    configure_context, include_name, include_object, security_metadata, validate_configuration,
)


BACKEND = Path(__file__).resolve().parents[1]
MIGRATION = SCRIPT_LOCATION / "versions" / f"{INITIAL_REVISION}_create_security.py"


def config():
    return Config(str(BACKEND / "alembic-security.ini"))


def revision_ast():
    return ast.parse(MIGRATION.read_text())


def declarations():
    """Extract only constructor expressions, without calling either operation.
    This deliberately rejects anything beyond the reviewed SQLAlchemy builders.
    """
    function = next(n for n in revision_ast().body if isinstance(n, ast.FunctionDef) and n.name == "upgrade")
    result = []
    for statement in function.body:
        assert isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call)
        call = statement.value
        assert isinstance(call.func, ast.Attribute) and call.func.value.id == "op"
        assert call.func.attr in {"execute", "create_table", "create_index"}
        for expression in [*call.args, *(kw.value for kw in call.keywords)]:
            for inner in ast.walk(expression):
                if isinstance(inner, ast.Call):
                    assert isinstance(inner.func, ast.Attribute)
                    assert inner.func.value.id in {"sa", "postgresql"}
        namespace = {"sa": sa, "postgresql": postgresql, "__builtins__": {}}
        def value(expression):
            return eval(compile(ast.Expression(expression), str(MIGRATION), "eval"), namespace)
        result.append((call.func.attr, [value(a) for a in call.args],
                       {kw.arg: value(kw.value) for kw in call.keywords}))
    return result


def migration_metadata():
    metadata = sa.MetaData()
    for kind, args, kwargs in declarations():
        if kind == "create_table":
            sa.Table(args[0], metadata, *args[1:], **kwargs)
        elif kind == "create_index":
            name, table_name, columns = args
            table = metadata.tables[f"security.{table_name}"]
            sa.Index(name, *(table.c[c] for c in columns), unique=kwargs["unique"])
    return metadata


def test_single_independent_root_and_head():
    script = ScriptDirectory.from_config(config())
    assert script.get_heads() == [INITIAL_REVISION]
    assert script.get_bases() == [INITIAL_REVISION]
    revisions = list(script.walk_revisions())
    assert len(revisions) == 1
    revision = revisions[0]
    assert revision.down_revision is None
    assert revision.branch_labels == set()
    assert revision.dependencies is None
    assert Path(script.dir).resolve() == SCRIPT_LOCATION
    assert not {"f066a01a7230", "f067a01a7230"} & {r.revision for r in revisions}


def test_configuration_has_no_url_or_application_graph():
    cfg = config()
    validate_configuration(cfg)
    assert cfg.get_main_option("sqlalchemy.url") is None
    assert cfg.get_main_option("version_locations") is None
    assert cfg.get_main_option("version_table") == "alembic_security_version"
    assert cfg.get_main_option("version_table_schema") == "public"


@pytest.mark.parametrize("key,value", [
    ("script_location", str(BACKEND / "migrations")),
    ("version_locations", str(BACKEND / "migrations/versions")),
    ("version_table", "alembic_version"), ("version_table_schema", "security"),
    ("sqlalchemy.url", "postgresql://not-an-operational-url"),
    ("recursive_version_locations", "true"),
])
def test_configuration_rejects_fallback_and_cross_graph_settings(key, value):
    cfg = config()
    cfg.set_main_option(key, value)
    with pytest.raises(RuntimeError):
        validate_configuration(cfg)


def test_metadata_is_copied_and_strictly_security_only():
    before = set(Base.metadata.tables)
    metadata = security_metadata()
    assert metadata is not Base.metadata
    assert set(metadata.tables) == {f"security.{name}" for name in TABLE_NAMES}
    assert set(Base.metadata.tables) == before


@pytest.mark.parametrize("schema", [None, "public", "inventory", "audit", "authorization", "unknown"])
def test_foreign_schemas_and_objects_are_excluded(schema):
    assert not include_name(schema, "schema", {})
    assert not include_name("local_users", "table", {"schema_name": schema})
    table = sa.Table("local_users", sa.MetaData(), sa.Column("id", sa.Integer), schema=schema)
    assert not include_object(table, table.name, "table", True, None)
    assert not include_object(table.c.id, "id", "column", True, None)


def test_expected_security_objects_are_included_but_unknowns_are_not():
    table = security_metadata().tables["security.local_users"]
    assert include_name("security", "schema", {})
    assert include_name("local_users", "table", {"schema_name": "security"})
    assert include_name("login", "column", {"schema_name": "security", "table_name": "local_users"})
    assert include_object(table, table.name, "table", False, None)
    assert include_object(table.c.login, "login", "column", True, table.c.login)
    assert not include_name("unexpected", "table", {"schema_name": "security"})


def test_exact_schema_tables_and_safe_declaration_order():
    calls = declarations()
    assert [args for kind, args, _ in calls if kind == "execute"] == [["CREATE SCHEMA security"]]
    assert [args[0] for kind, args, _ in calls if kind == "create_table"] == [
        "local_users", "login_sessions", "global_role_grants", "login_throttles",
    ]
    assert set(migration_metadata().tables) == {f"security.{name}" for name in TABLE_NAMES}
    assert len([1 for kind, _, _ in calls if kind == "create_index"]) == 1


def test_declarations_match_models_including_constraints_indices_and_server_defaults():
    actual, expected = migration_metadata(), security_metadata()
    for key, model in expected.tables.items():
        table = actual.tables[key]
        assert list(table.columns.keys()) == list(model.columns.keys())
        for name, column in model.columns.items():
            declared = table.c[name]
            assert declared.type._type_affinity == column.type._type_affinity
            assert getattr(declared.type, "length", None) == getattr(column.type, "length", None)
            assert getattr(declared.type, "timezone", None) == getattr(column.type, "timezone", None)
            assert declared.nullable == column.nullable
            assert declared.server_default is column.server_default is None
            assert declared.default is None  # Python defaults remain solely in ORM models.
        assert list(table.primary_key.columns.keys()) == list(model.primary_key.columns.keys())
        def foreign_keys(t):
            return {(f.parent.name, f.target_fullname, f.ondelete, f.onupdate) for f in t.foreign_keys}
        assert foreign_keys(table) == foreign_keys(model)
        def unique(t):
            return {(c.name, tuple(c.columns.keys())) for c in t.constraints if isinstance(c, sa.UniqueConstraint)}
        assert unique(table) == unique(model)
        def checks(t):
            return {(c.name, str(c.sqltext)) for c in t.constraints if isinstance(c, sa.CheckConstraint)}
        assert checks(table) == checks(model)
        assert {(i.name, tuple(i.columns.keys()), i.unique) for i in table.indexes} == {
            (i.name, tuple(i.columns.keys()), i.unique) for i in model.indexes}
        assert all(c.name for c in table.constraints)


def test_downgrade_is_unconditionally_blocked_without_invoking_it():
    function = next(n for n in revision_ast().body if isinstance(n, ast.FunctionDef) and n.name == "downgrade")
    assert len(function.body) == 1 and isinstance(function.body[0], ast.Raise)
    assert function.body[0].exc.func.id == "RuntimeError"
    assert not any(isinstance(n, ast.Attribute) and n.attr.startswith("drop") for n in ast.walk(function))


def test_context_configuration_keeps_external_connection_and_outer_transaction():
    environment = Mock()
    connection = Mock()
    connection.in_transaction.return_value = True
    connection.dialect.name = "postgresql"
    configure_context(environment, config(), connection)
    options = environment.configure.call_args.kwargs
    assert options["connection"] is connection
    assert options["version_table"] == VERSION_TABLE
    assert options["version_table_schema"] == VERSION_SCHEMA
    assert options["transactional_ddl"] is True
    assert options["transaction_per_migration"] is False
    assert options["include_schemas"] is True
    assert set(options["target_metadata"].tables) == {f"security.{name}" for name in TABLE_NAMES}
    connection.execute.assert_not_called()
    connection.commit.assert_not_called()
    environment.run_migrations.assert_not_called()


@pytest.mark.parametrize("fault", ["missing", "no_transaction", "wrong_dialect"])
def test_context_fails_closed(fault):
    connection = Mock()
    connection.in_transaction.return_value = fault != "no_transaction"
    connection.dialect.name = "sqlite" if fault == "wrong_dialect" else "postgresql"
    environment = Mock()
    with pytest.raises(RuntimeError):
        configure_context(environment, config(), None if fault == "missing" else connection)
    environment.configure.assert_not_called()


def test_environment_without_connection_never_runs_migrations(monkeypatch):
    from alembic import context
    monkeypatch.setattr(context, "config", config(), raising=False)
    monkeypatch.setattr(context, "is_offline_mode", lambda: False)
    execute = Mock(side_effect=AssertionError("Migrations prohibited"))
    monkeypatch.setattr(context, "run_migrations", execute)
    with pytest.raises(RuntimeError, match="externa"):
        runpy.run_path(str(SCRIPT_LOCATION / "env.py"))
    execute.assert_not_called()
