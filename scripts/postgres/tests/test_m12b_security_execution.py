"""Offline doubles only. No SQL, Alembic operation, database or Docker is run."""

from dataclasses import replace
from unittest.mock import Mock

import pytest
import sqlalchemy as sa

import m12b_security_migration as executor
from security_migrations.contract import security_metadata, TABLE_NAMES


@pytest.fixture
def plan():
    return executor.prepare_plan({
        "project": executor.PROJECT, "database": executor.DATABASE, "host": "db", "port": 5432,
        "system_identifier": executor.SYSTEM_IDENTIFIER, "migration_user": "livenet_m12b_migrator",
        "application_user": "livenet_m12b_app",
    }, confirmed_baseline=executor.BASELINE)


@pytest.fixture
def identity():
    return dict(database=executor.DATABASE, current_user="livenet_m12b_migrator",
                session_user="livenet_m12b_migrator", port=5432, server_version_num=160015,
                system_identifier=executor.SYSTEM_IDENTIFIER, search_path="public", read_only="off")


@pytest.mark.parametrize("field,value", [
    ("database", "livenet"), ("current_user", "livenet_m12b_bootstrap"),
    ("session_user", "livenet_m12b_app"), ("system_identifier", "123"),
    ("port", 5433), ("server_version_num", 150000),
    ("search_path", "pg_catalog, public"), ("search_path", '"$user", public'),
])
def test_live_identity_reader_rejects_divergence(plan, identity, field, value):
    connection = Mock()
    connection.dialect.name = "postgresql"
    connection.in_transaction.return_value = True
    connection.execute.return_value.mappings.return_value.one.return_value = {**identity, field: value}
    with pytest.raises(executor.Refused):
        executor.identify_postgresql(connection, plan)


def test_identity_reader_and_missing_transaction(plan, identity):
    connection = Mock()
    connection.dialect.name = "postgresql"
    connection.in_transaction.return_value = True
    connection.execute.return_value.mappings.return_value.one.return_value = identity
    assert executor.identify_postgresql(connection, plan) == identity
    connection.in_transaction.return_value = False
    with pytest.raises(executor.Refused):
        executor.identify_postgresql(connection, plan)


def test_reader_collects_real_adapter_results_with_no_security_ledger(plan, identity):
    connection = Mock()
    connection.dialect.name = 'postgresql'
    connection.in_transaction.return_value = True
    response = Mock()
    response.mappings.return_value.one.return_value = identity
    schemas, relations, ledger = Mock(), Mock(), Mock()
    schemas.scalars.return_value = ['public','inventory','audit']
    relations.__iter__ = Mock(return_value=iter(executor.BASELINE_TABLES))
    ledger.scalars.return_value = [executor.BASELINE]
    connection.execute.side_effect = [response, schemas, relations, ledger]
    observed = executor.read_database_state(connection, plan)
    assert executor.validate_observation(plan, observed, phase='before') == observed
    assert connection.execute.call_count == 4


def test_reader_reads_security_ledger_only_when_present(plan, identity):
    connection = Mock()
    connection.dialect.name = 'postgresql'
    connection.in_transaction.return_value = True
    response = Mock()
    response.mappings.return_value.one.return_value = identity
    schemas, relations, ledger, security = Mock(), Mock(), Mock(), Mock()
    schemas.scalars.return_value = ['public','inventory','audit','security']
    tables = executor.BASELINE_TABLES | {('security',n) for n in TABLE_NAMES} | {('public',executor.VERSION_TABLE)}
    relations.__iter__ = Mock(return_value=iter(tables))
    ledger.scalars.return_value = [executor.BASELINE]
    security.scalars.return_value = [executor.INITIAL_REVISION]
    connection.execute.side_effect = [response, schemas, relations, ledger, security]
    observed = executor.read_database_state(connection, plan)
    executor.validate_observation(plan, observed, phase='after')
    assert connection.execute.call_count == 5


def test_lock_rejection():
    connection = Mock()
    connection.execute.return_value.scalar_one.return_value = False
    with pytest.raises(executor.Refused):
        executor.acquire_migration_lock(connection)


@pytest.mark.parametrize("unsafe", [True, False])
def test_privileges_are_fail_closed(unsafe):
    connection = Mock()
    connection.execute.return_value.mappings.return_value.one.return_value = dict.fromkeys(
        ['limited_role','no_memberships','create_schema','create_ledger','not_database_owner',
         'not_protected_owner','no_protected_ddl','no_protected_writes'], not unsafe)
    if unsafe:
        with pytest.raises(executor.Refused):
            executor.verify_privileges(connection)
    else:
        executor.verify_privileges(connection)


@pytest.fixture
def workflow(monkeypatch, plan, identity):
    """Simulate a future reviewed authorization only in this test process."""
    events = []
    write, read = Mock(), Mock()
    for connection in (write, read):
        connection.in_transaction.return_value = False
    write.begin.side_effect = lambda: events.append("begin") or write.transaction
    write.transaction.commit.side_effect = lambda: events.append("commit")
    write.transaction.rollback.side_effect = lambda: events.append("rollback")
    write.close.side_effect = lambda: events.append("close_write")
    read.close.side_effect = lambda: events.append("close_read")
    ports = executor.ExecutionPorts(Mock(), Mock(), Mock())
    ports.connect.side_effect = [write, read]
    monkeypatch.setattr(executor, "require_execution_authorization", lambda p: None)
    monkeypatch.setattr(executor, "validate_environment", lambda p, ports: events.append("attest"))
    monkeypatch.setattr(executor, "identify_postgresql", lambda c, p: {**identity, "read_only": "off" if c is write else "on"})
    monkeypatch.setattr(executor, "acquire_migration_lock", lambda c: events.append("lock"))
    before = executor.ObservedState(executor.DATABASE, executor.SYSTEM_IDENTIFIER,
        "livenet_m12b_migrator", "livenet_m12b_migrator", 160015,
        (executor.BASELINE,), (), frozenset({"public", "inventory", "audit"}), executor.BASELINE_TABLES)
    after = replace(before, schemas=before.schemas | {"security"},
        relations=before.relations | {("security", n) for n in TABLE_NAMES} | {("public", executor.VERSION_TABLE)},
        security_revisions=(executor.INITIAL_REVISION,))
    state = Mock(side_effect=[before, after, after])
    monkeypatch.setattr(executor, "read_database_state", state)
    monkeypatch.setattr(executor, "verify_privileges", lambda c: events.append("privileges"))
    fingerprint = Mock(side_effect=lambda c: events.append("fingerprint") or "protected")
    monkeypatch.setattr(executor, "protected_fingerprint", fingerprint)
    physical = Mock(side_effect=lambda c: events.append("physical"))
    monkeypatch.setattr(executor, "validate_physical_security", physical)
    def upgrade(config, revision):
        assert config.attributes["connection"] is write
        assert revision == executor.INITIAL_REVISION
        assert config.get_main_option("version_table") == "alembic_security_version"
        write.in_transaction.return_value = True
        events.append("alembic")
    ports.upgrade.side_effect = upgrade
    return ports, write, read, events, state, physical, fingerprint


def test_commit_order_new_connection_and_safe_report(plan, workflow):
    ports, write, read, events, state, physical, fingerprint = workflow
    report = executor.execute_security_migration(plan, ports)
    assert events.index("physical") < events.index("commit") < events.index("close_write")
    assert events.index("lock") < events.index("alembic")
    assert events.count("physical") == 2 and report["status"] == "verified"
    assert ports.connect.call_args_list[0].kwargs == {"read_only": False}
    assert ports.connect.call_args_list[1].kwargs == {"read_only": True}
    assert physical.call_args_list[1].args == (read,)
    write.transaction.rollback.assert_not_called()


@pytest.mark.parametrize("fault", ["lock", "alembic", "physical", "fingerprint", "baseline", "authorization", "security"])
def test_failures_before_commit_rollback(plan, workflow, monkeypatch, fault, capsys):
    ports, write, read, events, state, physical, fingerprint = workflow
    secret = "SENSITIVE-DRIVER-CONTENT"
    if fault == "lock":
        monkeypatch.setattr(executor, "acquire_migration_lock", Mock(side_effect=executor.Refused(secret)))
    elif fault == "alembic": ports.upgrade.side_effect = RuntimeError(secret)
    elif fault == "physical": physical.side_effect = RuntimeError(secret)
    elif fault == "fingerprint": fingerprint.side_effect = ["before", "different"]
    else:
        before = executor.ObservedState(executor.DATABASE, executor.SYSTEM_IDENTIFIER,
            "livenet_m12b_migrator", "livenet_m12b_migrator", 160015,
            (executor.BASELINE,), (), frozenset({"public", "inventory", "audit"}), executor.BASELINE_TABLES)
        if fault == "baseline": before = replace(before, application_revisions=("f067a01a7230",))
        elif fault == "authorization": before = replace(before, schemas=before.schemas | {"authorization"})
        else: before = replace(before, schemas=before.schemas | {"security"})
        state.side_effect = [before]
    with pytest.raises(executor.ExecutionFailed, match="rolled_back") as error:
        executor.execute_security_migration(plan, ports)
    assert secret not in str(error.value) and secret not in repr(error.value)
    assert secret not in str(capsys.readouterr()) and error.value.__context__ is None
    write.transaction.commit.assert_not_called()
    write.transaction.rollback.assert_called_once()
    assert ports.connect.call_count == 1


@pytest.mark.parametrize("fault", ["commit", "persistence", "same_connection", "same_driver", "post_physical", "close", "rollback"])
def test_uncertain_or_post_commit_failure_requires_reconciliation(plan, workflow, fault):
    ports, write, read, events, state, physical, fingerprint = workflow
    if fault == "commit": write.transaction.commit.side_effect = RuntimeError("sensitive")
    elif fault == "persistence": ports.connect.side_effect = [write, RuntimeError("sensitive")]
    elif fault == "same_connection": ports.connect.side_effect = [write, write]
    elif fault == "same_driver": read.connection.driver_connection = write.connection.driver_connection
    elif fault == "post_physical": physical.side_effect = [None, RuntimeError("sensitive")]
    elif fault == "rollback":
        ports.upgrade.side_effect = RuntimeError('sensitive')
        write.transaction.rollback.side_effect = RuntimeError('sensitive')
    else: read.close.side_effect = RuntimeError("sensitive")
    with pytest.raises(executor.ExecutionFailed, match="reconcile_required"):
        executor.execute_security_migration(plan, ports)
    assert write.transaction.commit.call_count == (0 if fault == 'rollback' else 1)
    assert ports.upgrade.call_count == 1  # No retries.


def test_no_environment_switch_or_adapter_can_activate_execution(plan, monkeypatch):
    monkeypatch.setenv("EXECUTION_ENABLED", "true")
    monkeypatch.setenv("M12B_EXECUTION_ENABLED", "true")
    ports = executor.ExecutionPorts(Mock(), Mock(), Mock())
    with pytest.raises(executor.Refused, match="bloqueada"):
        executor.execute_security_migration(plan, ports)
    for port in (ports.attest, ports.connect, ports.upgrade): port.assert_not_called()
    with pytest.raises(executor.Refused): executor.run_alembic(plan, Mock(), ports)
    ports.upgrade.assert_not_called()


def test_forged_or_stale_plan_is_rejected(plan):
    with pytest.raises(executor.Refused): executor.validate_plan(replace(plan, destination="head"))
    with pytest.raises(executor.Refused): executor.validate_plan(replace(plan, digest="forged"))


def test_environment_provenance_is_required(plan):
    ports = executor.ExecutionPorts(Mock(return_value={}), Mock(), Mock())
    with pytest.raises(executor.Refused): executor.validate_environment(plan, ports)


@pytest.fixture
def reflection(monkeypatch):
    metadata = security_metadata()
    inspector = Mock()
    inspector.get_table_names.return_value = sorted(TABLE_NAMES)
    def columns(name, schema):
        if schema == "public": return [dict(name="version_num", type=sa.String(32), nullable=False, default=None)]
        return [dict(name=c.name, type=c.type, nullable=c.nullable, default=None) for c in metadata.tables["security."+name].c]
    inspector.get_columns.side_effect = columns
    inspector.get_pk_constraint.side_effect = lambda name,schema: dict(name="pk_security_"+name,
        constrained_columns=["version_num"] if schema=="public" else list(metadata.tables['security.'+name].primary_key.c.keys()))
    def foreign(name, schema):
        return [] if name not in {'login_sessions','global_role_grants'} else [dict(
            name='fk_security_'+name+'_user_id_local_users', constrained_columns=['user_id'],
            referred_schema='security', referred_table='local_users', referred_columns=['id'], options={})]
    inspector.get_foreign_keys.side_effect = foreign
    inspector.get_unique_constraints.side_effect = lambda name,schema: [dict(name=c.name,column_names=list(c.columns.keys())) for c in metadata.tables['security.'+name].constraints if isinstance(c,sa.UniqueConstraint)]
    inspector.get_check_constraints.side_effect = lambda name,schema: [dict(name=c.name,sqltext=str(c.sqltext)) for c in metadata.tables['security.'+name].constraints if isinstance(c,sa.CheckConstraint)]
    inspector.get_indexes.side_effect = lambda name,schema: [dict(name=i.name,column_names=list(i.columns.keys()),unique=i.unique) for i in metadata.tables['security.'+name].indexes]
    monkeypatch.setattr(executor, 'inspect', lambda c: inspector)
    connection=Mock()
    connection.execute.return_value.scalar_one.side_effect=[0,0,0,0,True]
    return inspector,connection


def test_physical_schema_matches_models(reflection):
    inspector,connection=reflection
    executor.validate_physical_security(connection)


@pytest.mark.parametrize('fault', ['table','column','type','nullable','default','pk','fk','unique','check','index','rows','ownership'])
def test_physical_schema_rejects_drift(reflection,fault):
    inspector,connection=reflection
    if fault=='table': inspector.get_table_names.return_value=['unexpected']
    elif fault in {'column','type','nullable','default'}:
        original=inspector.get_columns.side_effect
        def changed(name,schema):
            columns=original(name,schema)
            if schema=='security':
                if fault=='column': columns[0]['name']='unexpected'
                elif fault=='type': columns[0]['type']=sa.Integer()
                elif fault=='nullable': columns[0]['nullable']=True
                else: columns[0]['default']='generated'
            return columns
        inspector.get_columns.side_effect=changed
    elif fault=='pk': inspector.get_pk_constraint.side_effect=lambda *a,**k: dict(name='wrong',constrained_columns=['wrong'])
    elif fault=='fk': inspector.get_foreign_keys.side_effect=lambda *a,**k: []
    elif fault=='unique': inspector.get_unique_constraints.side_effect=lambda *a,**k: []
    elif fault=='check': inspector.get_check_constraints.side_effect=lambda *a,**k: []
    elif fault=='index': inspector.get_indexes.side_effect=lambda *a,**k: []
    elif fault=='rows': connection.execute.return_value.scalar_one.side_effect=[1]
    else: connection.execute.return_value.scalar_one.side_effect=[0,0,0,0,False]
    with pytest.raises(executor.Refused): executor.validate_physical_security(connection)


@pytest.mark.parametrize('option', ['postgresql_where','postgresql_using','postgresql_include'])
def test_changed_index_semantics_are_rejected(reflection, option):
    inspector, connection = reflection
    original = inspector.get_indexes.side_effect
    def changed(name, schema):
        indexes = original(name, schema)
        for index in indexes:
            index['dialect_options'] = {option: 'changed'}
        return indexes
    inspector.get_indexes.side_effect = changed
    with pytest.raises(executor.Refused): executor.validate_physical_security(connection)


def test_incomplete_privilege_inspection_is_rejected():
    connection = Mock()
    connection.execute.return_value.mappings.return_value.one.return_value = {}
    with pytest.raises(executor.Refused): executor.verify_privileges(connection)


def test_authorization_identity_must_match_reviewed_contract(plan, monkeypatch):
    # Code substitution is confined to this offline test; no activation API exists.
    monkeypatch.setattr(executor, 'AUTHORIZATION', executor.ExecutionAuthorization(
        execution_enabled=True, system_identifier='wrong'))
    with pytest.raises(executor.Refused): executor.require_execution_authorization(plan)


def test_postgres_check_rendering_and_changed_semantics():
    assert executor.canonical_check("status IN ('active', 'disabled')") == executor.canonical_check(
        "((status)::text = ANY ((ARRAY['active'::character varying, 'disabled'::character varying])::text[]))")
    assert executor.canonical_check('attempts >= 1') != executor.canonical_check('attempts >= 0')
    assert executor.canonical_check("role = 'inventory_reader'") != executor.canonical_check("role = 'inventory_ reader'")
    assert executor.canonical_check("status = 'active'") != executor.canonical_check("status = 'ACTIVE'")
    with pytest.raises(executor.Refused): executor.canonical_check('a AND (b OR c)')
