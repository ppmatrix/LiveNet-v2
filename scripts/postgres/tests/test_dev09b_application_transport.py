"""Application transport tests: actual Alembic graph, mocked dispatch only."""
from types import SimpleNamespace
from unittest.mock import Mock
import json,socket,subprocess

import pytest
from alembic.config import Config
import sqlalchemy

from migrations import dev09b_prerequisites as h
from scripts.postgres import dev09b_application_transport as t
from scripts.postgres.tests.test_dev09b_prepared import records
from scripts.dedicated.dev09b.model import OfflineObservation


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def denied(*a,**kw):raise AssertionError('No SQL, network, process, engine or actual Alembic migration')
    for owner,name in ((socket,'socket'),(socket,'create_connection'),(subprocess,'Popen'),(subprocess,'run'),(sqlalchemy,'create_engine')):
        monkeypatch.setattr(owner,name,denied)
    monkeypatch.setattr(t.command,'upgrade',denied)


def setup():
    tx=SimpleNamespace(is_active=True)
    conn=SimpleNamespace(closed=False,dialect=SimpleNamespace(name='postgresql'),_echo=False,
        engine=SimpleNamespace(echo=False,hide_parameters=True,logger=SimpleNamespace(isEnabledFor=lambda level:False)),
        in_transaction=lambda:True,get_transaction=lambda:tx)
    port=SimpleNamespace(assert_connection=Mock())
    profile,_=records()
    context=h.PreparedContext(json.dumps(profile).encode(),port)
    return conn,tx,context,t.ApplicationTransport(conn,tx,context)


class SynchronousTrustedBoundaryDouble:
    """Algorithm-only test controller; no production authority implementation."""
    def __init__(self):self.calls=[]
    def dispatch_original(self,**kw):self.calls.append(kw);kw['body']()


def test_inert_construction_and_missing_real_admission():
    conn,tx,ctx,work=setup()
    assert not ctx.port.assert_connection.called
    with pytest.raises(h.MissingParameter,match='live_original_admission'):work.apply_once(None)
    assert not ctx.port.assert_connection.called


def test_real_graph_fixed_command_and_exact_borrowed_transaction(monkeypatch):
    conn,tx,ctx,work=setup();calls=[]
    def upgrade(config,revision,sql=False):
        assert type(config) is Config and config.config_file_name is None
        assert config.attributes['connection'] is conn and config.attributes[h.ATTR] is ctx
        assert config.get_main_option('sqlalchemy.url') is None
        assert config.get_main_option('version_table_schema')=='public'
        assert revision=='f066a01a7230' and sql is False
        calls.append(config)
    monkeypatch.setattr(t.command,'upgrade',upgrade)
    controller=SynchronousTrustedBoundaryDouble()
    assert work.apply_once(controller) is None
    assert len(calls)==1 and len(controller.calls)==1
    assert controller.calls[0]['operation']==t.OPERATION
    assert controller.calls[0]['transaction'] is tx and controller.calls[0]['connection'] is conn
    assert tx.is_active and conn.get_transaction() is tx
    with pytest.raises(h.PrerequisiteRefused,match='no retry'):work.apply_once(controller)


@pytest.mark.parametrize('data',[True,{},b'approval','sha256',OfflineObservation('attempt','consume','nonce')])
def test_offline_results_do_not_dispatch(data):
    conn,tx,ctx,work=setup()
    with pytest.raises(h.PrerequisiteRefused,match='Offline data'):work.apply_once(data)


def test_return_value_is_not_permission_and_late_callback_refuses():
    conn,tx,ctx,work=setup()
    class NoDispatch:
        def dispatch_original(self,**kw):self.callback=kw['body'];return True
    controller=NoDispatch()
    with pytest.raises(h.PrerequisiteRefused,match='without completing'):work.apply_once(controller)
    with pytest.raises(h.PrerequisiteRefused,match='Late'):controller.callback()


def test_duplicate_callback_is_refused(monkeypatch):
    conn,tx,ctx,work=setup();upgrade=Mock();monkeypatch.setattr(t.command,'upgrade',upgrade)
    class Duplicate:
        def dispatch_original(self,**kw):kw['body']();kw['body']()
    with pytest.raises(h.PrerequisiteRefused,match='repeated'):work.apply_once(Duplicate())
    assert upgrade.call_count==1


@pytest.mark.parametrize('failure',['raise','replace_transaction','close'])
def test_failure_or_transaction_escape_not_retried(monkeypatch,failure):
    conn,tx,ctx,work=setup()
    def upgrade(*args,**kw):
        if failure=='raise':raise RuntimeError('synthetic failure')
        if failure=='replace_transaction':conn.get_transaction=lambda:object()
        if failure=='close':conn.closed=True
    mock=Mock(side_effect=upgrade);monkeypatch.setattr(t.command,'upgrade',mock)
    with pytest.raises((RuntimeError,h.PrerequisiteRefused)):work.apply_once(SynchronousTrustedBoundaryDouble())
    with pytest.raises(h.PrerequisiteRefused,match='no retry'):work.apply_once(SynchronousTrustedBoundaryDouble())
    assert mock.call_count==1


def test_binding_and_logging_refuse_before_alembic():
    conn,tx,ctx,work=setup();conn._echo=True
    with pytest.raises(ValueError,match='CLIENT_LOGGING_REFUSED'):work.apply_once(SynchronousTrustedBoundaryDouble())
    conn,tx,ctx,work=setup();tx.is_active=False
    with pytest.raises(h.PrerequisiteRefused,match='Transaction changed'):work.apply_once(SynchronousTrustedBoundaryDouble())


def test_security_operation_not_accepted():
    conn,tx,ctx,work=setup();profile=json.loads(ctx.profile_json)
    profile['operation']='security-base-to-b12b01a7230'
    work.context=h.PreparedContext(json.dumps(profile).encode(),ctx.port)
    with pytest.raises(h.PrerequisiteRefused,match='Application base-to-f066'):work.apply_once(SynchronousTrustedBoundaryDouble())


def test_foreign_module_context_identity_refuses():
    from backend.migrations.dev09b_prerequisites import PreparedContext as ForeignContext
    conn,tx,ctx,work=setup()
    assert ForeignContext is not h.PreparedContext
    work.context=ForeignContext(ctx.profile_json,ctx.port)
    with pytest.raises(h.PrerequisiteRefused,match='Canonical'):work.apply_once(SynchronousTrustedBoundaryDouble())


def test_controller_refusal_never_dispatches(monkeypatch):
    conn,tx,ctx,work=setup();upgrade=Mock();monkeypatch.setattr(t.command,'upgrade',upgrade)
    class Refuse:
        def dispatch_original(self,**kw):raise RuntimeError('authority/continuity unavailable')
    with pytest.raises(RuntimeError):work.apply_once(Refuse())
    assert upgrade.call_count==0 and tx.is_active
