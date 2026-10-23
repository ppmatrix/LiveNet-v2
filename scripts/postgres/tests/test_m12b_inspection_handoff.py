"""Offline protocol tests; all PostgreSQL statements terminate at mocks."""

from dataclasses import replace
from unittest.mock import Mock
import ast
from pathlib import Path

import pytest

import m12b_security_migration as executor


@pytest.fixture
def plan():
    return executor.prepare_plan(dict(project=executor.PROJECT,database=executor.DATABASE,
        host='db',port=5432,system_identifier=executor.SYSTEM_IDENTIFIER,
        migration_user='livenet_m12b_migrator',application_user='livenet_m12b_app'),
        confirmed_baseline=executor.BASELINE)


@pytest.fixture
def session(monkeypatch, plan):
    connection = Mock()
    connection.in_transaction.return_value = False
    connection.execute.return_value.scalar_one.return_value = True
    monkeypatch.setattr(executor,'identify_postgresql',Mock(return_value={'read_only':'on'}))
    fingerprint = Mock(return_value='catalog-fingerprint')
    monkeypatch.setattr(executor,'inspect_compliance',fingerprint)
    clock = Mock(return_value=100.0)
    monkeypatch.setattr(executor.time,'monotonic',clock)
    return executor._ComplianceSession(connection,plan), connection, fingerprint, clock


def test_single_use_local_evidence_and_order(session, plan):
    authority, connection, fingerprint, clock = session
    evidence = authority.issue()
    authority.consume(evidence,plan)
    authority.verify_unchanged(installed=False)
    authority.verify_unchanged(installed=True)
    assert fingerprint.call_count == 4
    assert fingerprint.call_args.kwargs == {'installed':True}
    queries = [str(call.args[0]) for call in connection.execute.call_args_list]
    assert 'pg_try_advisory_lock(1295073858, 6601)' in queries[0]
    assert all('pg_locks' in q for q in queries[1:])
    with pytest.raises(executor.Refused): authority.consume(evidence,plan)
    assert connection.begin.return_value.rollback.call_count == 4
    authority.close()
    connection.close.assert_called_once()
    assert 'pg_advisory_unlock' in str(connection.execute.call_args.args[0])


@pytest.mark.parametrize('forgery', [True,False,{},'receipt',None])
def test_caller_values_are_not_evidence(session,plan,forgery):
    authority,connection,fingerprint,clock = session
    authority.issue()
    with pytest.raises(executor.Refused): authority.consume(forgery,plan)
    assert fingerprint.call_count == 1


def test_copy_or_other_authority_evidence_rejected(session,plan):
    authority,connection,fingerprint,clock = session
    evidence=authority.issue()
    with pytest.raises(executor.Refused): authority.consume(replace(evidence),plan)
    other=executor._ComplianceSession(Mock(),plan)
    with pytest.raises(executor.Refused): other.consume(evidence,plan)


@pytest.mark.parametrize('clock_value',[99.0,106.0])
def test_expired_or_wrong_temporal_context(session,plan,clock_value):
    authority,connection,fingerprint,clock=session
    evidence=authority.issue()
    clock.return_value=clock_value
    with pytest.raises(executor.Refused): authority.consume(evidence,plan)


@pytest.mark.parametrize('field,value', [('destination','head'),('application_revision','f067a01a7230'),
    ('version_schema','security'),('digest','forged')])
def test_wrong_revision_or_context_rejected(session,plan,field,value):
    authority,connection,fingerprint,clock=session
    evidence=authority.issue()
    with pytest.raises(executor.Refused): authority.consume(evidence,replace(plan,**{field:value}))


@pytest.mark.parametrize('field,value',[('database','livenet'),('system_identifier','999'),
    ('project','other'),('migration_user','livenet_m12b_bootstrap'),('host','other'),('port',5433)])
def test_wrong_target_rejected(session,plan,field,value):
    authority,connection,fingerprint,clock=session
    evidence=authority.issue()
    wrong=replace(plan,target=replace(plan.target,**{field:value}))
    with pytest.raises(executor.Refused): authority.consume(evidence,wrong)


def test_state_drift_rejected_before_ddl(session,plan):
    authority,connection,fingerprint,clock=session
    evidence=authority.issue()
    fingerprint.return_value='changed'
    with pytest.raises(executor.Refused,match='alterado'): authority.consume(evidence,plan)


def test_long_reinspection_expiration_rejected(session,plan):
    authority,connection,fingerprint,clock=session
    evidence=authority.issue()
    clock.side_effect=[101.0,106.0]
    with pytest.raises(executor.Refused): authority.consume(evidence,plan)


@pytest.mark.parametrize('fault',['lock','lost_lock','read_write','inspection'])
def test_inspector_failure_closes_snapshot_without_migration(session,plan,monkeypatch,fault):
    authority,connection,fingerprint,clock=session
    if fault=='lock': connection.execute.return_value.scalar_one.return_value=False
    elif fault=='lost_lock': connection.execute.return_value.scalar_one.side_effect=[True,False]
    elif fault=='read_write': monkeypatch.setattr(executor,'identify_postgresql',Mock(return_value={'read_only':'off'}))
    else: fingerprint.side_effect=executor.Refused('inconsistent')
    with pytest.raises(executor.Refused): authority.issue()
    connection.begin.return_value.rollback.assert_called_once()


def test_unlock_failure_is_not_reported_as_success(session):
    authority,connection,fingerprint,clock=session
    authority.issue()
    connection.execute.return_value.scalar_one.return_value=False
    with pytest.raises(executor.Refused): authority.close()
    connection.close.assert_called_once()


@pytest.mark.parametrize('field',['limited','no_memberships','no_database_ddl','owns_no_database',
    'owns_no_routine','no_schema_ddl','no_writes','no_excess_reads','no_row_security'])
def test_inspector_effective_privileges_must_be_read_only(field):
    fields=['limited','no_memberships','no_database_ddl','owns_no_database','owns_no_routine','no_schema_ddl','no_writes','no_excess_reads','no_row_security']
    connection=Mock()
    connection.execute.return_value.mappings.return_value.one.return_value={**dict.fromkeys(fields,True),field:False}
    with pytest.raises(executor.Refused): executor.verify_inspector_privileges(connection)


def test_inspector_privileges_accept_minimal_observation():
    fields=['limited','no_memberships','no_database_ddl','owns_no_database','owns_no_routine','no_schema_ddl','no_writes','no_excess_reads','no_row_security']
    connection=Mock()
    connection.execute.return_value.mappings.return_value.one.return_value=dict.fromkeys(fields,True)
    executor.verify_inspector_privileges(connection)


def test_migrator_has_no_direct_calls_to_protected_row_reader():
    source=Path(executor.__file__).read_text()
    tree=ast.parse(source)
    for name in ['execute_security_migration','read_database_state','validate_physical_security']:
        function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
        assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name)
                       and n.func.id=='protected_fingerprint' for n in ast.walk(function))
    for sql in ['no_protected_reads','no_protected_usage','has_any_column_privilege']:
        assert sql in source


def test_inspector_adapter_is_explicit_and_not_bootstrap(plan):
    ports=executor.ExecutionPorts(Mock(),Mock(),Mock(),Mock(return_value=Mock()))
    authority=executor._open_compliance(plan,ports)
    assert authority.plan is plan
    assert ports.inspector_connect.call_args.kwargs=={'identity':'livenet_m12b_inspector','read_only':True}
    ports.connect.assert_not_called()


def test_no_handoff_can_activate_disabled_executor(plan):
    ports=executor.ExecutionPorts(Mock(),Mock(),Mock(),Mock())
    with pytest.raises(executor.Refused): executor.execute_security_migration(plan,ports)
    for adapter in [ports.attest,ports.connect,ports.upgrade,ports.inspector_connect]:
        adapter.assert_not_called()


@pytest.mark.parametrize('installed',[False,True])
def test_compliance_reader_uses_only_catalog_baseline_ledger_and_inspector(plan,monkeypatch,installed):
    connection=Mock()
    identify=Mock(return_value={'read_only':'on'})
    monkeypatch.setattr(executor,'identify_postgresql',identify)
    monkeypatch.setattr(executor,'verify_inspector_privileges',Mock())
    monkeypatch.setattr(executor,'protected_fingerprint',Mock(return_value='fingerprint'))
    schemas,relations,revision=Mock(),Mock(),Mock()
    expected_schemas={'public','inventory','audit'}
    expected_relations=set(executor.BASELINE_TABLES)
    if installed:
        expected_schemas.add('security')
        expected_relations|={('security',n) for n in executor.TABLE_NAMES}|{('public',executor.VERSION_TABLE)}
    schemas.scalars.return_value=expected_schemas
    relations.__iter__=Mock(return_value=iter(expected_relations))
    revision.scalars.return_value=[executor.BASELINE]
    connection.execute.side_effect=[schemas,relations,revision]
    assert executor.inspect_compliance(connection,plan,installed=installed)=='fingerprint'
    identify.assert_called_once_with(connection,plan,inspector=True)
    queries=[str(c.args[0]) for c in connection.execute.call_args_list]
    assert all('FROM security.' not in q and 'FROM inventory.' not in q and 'FROM audit.' not in q for q in queries)
    assert 'public.alembic_version' in queries[-1]


@pytest.mark.parametrize('field',['no_protected_reads','no_protected_usage','no_protected_writes','no_protected_ddl','no_temporary'])
def test_migrator_protected_privileges_are_rejected(field):
    fields=['limited_role','no_memberships','create_schema','create_ledger','not_database_owner',
        'not_protected_owner','no_protected_ddl','no_protected_writes','no_protected_usage','no_protected_reads','no_temporary']
    connection=Mock()
    connection.execute.return_value.mappings.return_value.one.return_value={**dict.fromkeys(fields,True),field:False}
    with pytest.raises(executor.Refused): executor.verify_privileges(connection)
