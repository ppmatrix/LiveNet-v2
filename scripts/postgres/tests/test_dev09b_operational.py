"""Constructed offline tests: real local kernel channel, no PostgreSQL or grants."""
from dataclasses import asdict
import os
import socket
from threading import Thread
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from scripts.dedicated.dev09b import codec as c
from scripts.dedicated.dev09b import operational as o
from scripts.dedicated.dev09b.model import SessionBinding


def test_real_unix_channel_and_request_response(tmp_path):
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    path = str(tmp_path / 'control.sock')
    listener.bind(path)
    listener.listen(1)
    errors = []
    def run():
        try:
            o.serve_one(listener, caller_uid=os.getuid(), dispatch=lambda m, a: dict(method=m, arguments=a))
        except BaseException as exc: errors.append(exc)
    worker = Thread(target=run)
    worker.start()
    try:
        assert o.LocalRPC(path, os.getuid()).call('sample', {}) == dict(method='sample', arguments={})
    finally:
        worker.join(3)
        listener.close()
    assert not worker.is_alive() and not errors


def test_wrong_peer_uid_refused_before_request():
    left, right = socket.socketpair()
    try:
        with pytest.raises(c.Invalid): o._peer(left, os.getuid() + 1)
    finally:
        left.close(); right.close()


def test_oversized_or_truncated_frame_refused():
    left, right = socket.socketpair()
    try:
        right.sendall(o.struct.pack('!I', o.MAX_FRAME + 1))
        with pytest.raises(c.Invalid): o._read(left)
        right.sendall(o.struct.pack('!I', 10) + b'{}')
        right.shutdown(socket.SHUT_WR)
        with pytest.raises(c.Invalid): o._read(left)
    finally:
        left.close(); right.close()


def test_authenticated_receipt_is_one_use_and_cannot_be_mutated():
    rpc = SimpleNamespace(call=Mock(return_value={'phase': 'consume'}))
    endpoint = o.AuthorityRPC(rpc)
    session = SessionBinding('0'*64, '1'*64, str(uuid4()), 1, 0, '1')
    raw = endpoint.consume(str(uuid4()), session, str(uuid4()), profile_json=b'{}')
    raw['phase'] = 'forged'
    assert endpoint.authenticate(raw) == {'phase': 'consume'}
    with pytest.raises(c.Invalid): endpoint.authenticate(raw)
    with pytest.raises(c.Invalid): endpoint.authenticate({'phase': 'consume'})
    with pytest.raises(c.Invalid): endpoint.authenticate(None)


def test_public_dispatch_has_no_admin_or_reset_methods():
    service = Mock()
    dispatch = o.AuthorityDispatch(service)
    for method in ('revoke', 'load', 'reset', '__class__'):
        with pytest.raises(c.Invalid): dispatch(method, {})
    assert not service.mock_calls


def test_clock_bounds_and_deadline_are_conservative():
    mono = Mock(return_value=10.0)
    clock = o.AnchoredClock(100, 102, max_age=60, drift_ppm=100, monotonic=mono)
    with pytest.raises(c.Invalid): clock.sample()
    clock.start()
    mono.return_value = 11.5
    assert asdict(clock.sample()) == dict(lower=101, upper=104, trustworthy=True)
    mono.return_value = 9
    with pytest.raises(c.Invalid): clock.sample()
    mono.return_value = 71
    with pytest.raises(c.Invalid): clock.sample()


def test_durable_start_blocks_reuse_even_after_clean_stop(tmp_path):
    tmp_path.chmod(0o700)
    token = str(uuid4())
    first = o.DurableContinuity(tmp_path, token)
    first.start()
    assert first.sample().token == token
    with pytest.raises(FileExistsError): o.DurableContinuity(tmp_path, token).start()
    first.block()
    with pytest.raises(c.Invalid): first.sample()
    assert (tmp_path / 'BLOCKED').read_bytes() == b'BLOCKED\n'
    first.block()


def test_continuity_does_not_create_directory_or_follow_symlinks(tmp_path):
    missing = o.DurableContinuity(tmp_path / 'missing', str(uuid4()))
    with pytest.raises(FileNotFoundError): missing.start()
    link = tmp_path / 'link'; link.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(c.Invalid): o.DurableContinuity(link, str(uuid4())).start()


def test_supervisor_latches_block_on_independent_observer_failure(tmp_path):
    tmp_path.chmod(0o700)
    continuity = o.DurableContinuity(tmp_path, str(uuid4())); continuity.start()
    clock = o.AnchoredClock(100, 100, max_age=10, drift_ppm=100); clock.start()
    session = SessionBinding('0'*64, '1'*64, str(uuid4()), 1, 0, '1')
    observer = Mock(side_effect=OSError('PRIVATE'))
    dispatch = o.WindowDispatch(continuity=continuity, clock=clock, session=session, plan=b'plan', observe=observer)
    with pytest.raises(OSError): dispatch('sample', {})
    with pytest.raises(c.Invalid): continuity.sample()
    assert (tmp_path / 'BLOCKED').exists()


def test_supervisor_refuses_changed_plan_before_observation(tmp_path):
    tmp_path.chmod(0o700)
    continuity = o.DurableContinuity(tmp_path, str(uuid4())); continuity.start()
    clock = Mock(); observer = Mock()
    session = SessionBinding('0'*64, '1'*64, str(uuid4()), 1, 0, '1')
    dispatch = o.WindowDispatch(continuity=continuity, clock=clock, session=session, plan=b'plan', observe=observer)
    with pytest.raises(c.Invalid):
        dispatch('assert_bound', dict(session=asdict(session), plan_sha256='0'*64))
    assert not observer.called and not clock.sample.called
    with pytest.raises(c.Invalid): continuity.sample()


def test_supervision_guard_does_no_sql():
    conn = Mock(); tx = Mock()
    session = SessionBinding('0'*64, '1'*64, str(uuid4()), 1, 0, '1')
    rpc = SimpleNamespace(call=Mock(return_value=dict(token=str(uuid4()), confirmed=True)))
    supervision = o.TrialSupervision(rpc=rpc, connection=conn, transaction=tx,
        session=session, snapshot=None, plan=b'plan', profile_json=b'',
        profile_verifier=None, precommit_contract=None, source_root=None)
    assert supervision.assert_bound(conn, tx, session, b'plan') is None
    assert not conn.mock_calls and not tx.mock_calls
    with pytest.raises(c.Invalid): supervision.assert_bound(conn, tx, session, b'changed')


def test_observer_cleanup_even_when_identity_refused():
    conn = Mock(); tx = Mock()
    conn.in_transaction.return_value = False
    conn.dialect.name = 'postgresql'
    conn.connection.driver_connection.autocommit = False
    conn.begin.return_value = tx
    conn.execute.return_value.mappings.return_value.one.return_value = dict(
        database='wrong', system_identifier='wrong', principal='wrong')
    observer = o.PostgresWindowObserver(connections=lambda: conn,
        binding=dict(database='livenet_v2_dev'))
    with pytest.raises(c.Invalid): observer()
    tx.rollback.assert_called_once(); conn.close.assert_called_once()


@pytest.mark.parametrize('fault', [None, 'tls', 'concurrent_admin', 'transaction', 'prepared'])
def test_independent_observer_enforces_window_and_always_closes(fault):
    conn = Mock(); tx = Mock()
    conn.in_transaction.return_value = False
    conn.dialect.name = 'postgresql'
    conn.connection.driver_connection.autocommit = False
    conn.begin.return_value = tx
    binding = dict(database='livenet_v2_dev', system_identifier='7705421224394444834',
        principal='dev09b_trial_admin', pid=123, usename='dev09b_trial_migrator',
        backend_start='fixed-backend', xact_start='fixed-xact', virtualxid='4/12')
    subject = {k: binding[k] for k in ('pid', 'usename', 'backend_start', 'xact_start', 'virtualxid')}
    subject.update(ssl=True, tls_version='TLSv1.3')
    if fault == 'tls': subject['ssl'] = False
    if fault == 'transaction': subject['virtualxid'] = '4/13'
    rows = [subject]
    if fault == 'concurrent_admin': rows.append(dict(subject, pid=124, usename='dev09b_trial_admin'))
    identity = Mock(); identity.mappings.return_value.one.return_value = dict(
        database=binding['database'], system_identifier=binding['system_identifier'],
        principal=binding['principal'], effective_principal=binding['principal'], observer_pid=321)
    activity = Mock(); activity.mappings.return_value = rows
    prepared = Mock(); prepared.scalar_one.return_value = 1 if fault == 'prepared' else 0
    conn.execute.side_effect = [None, None, None, identity, activity, prepared]
    observer = o.PostgresWindowObserver(connections=lambda: conn, binding=binding)
    if fault is None: assert observer() is None
    else:
        with pytest.raises(c.Invalid): observer()
    tx.rollback.assert_called_once(); conn.close.assert_called_once()


def test_independent_supervisor_loop_stops_and_closes_on_failure():
    dispatch = Mock(side_effect=OSError('private'))
    listener = Mock()
    with pytest.raises(OSError): o.supervise_window(listeners=[(listener, 123)], dispatch=dispatch)
    dispatch.continuity.block.assert_called_once(); listener.close.assert_called_once()


def test_rollback_wrapper_always_contains_and_has_no_commit_path():
    from scripts.postgres.dev09b_operational_trial import run_rollback_trial
    trial = Mock()
    assert run_rollback_trial(trial) is None
    trial.to_precommit.assert_called_once(); trial.contain.assert_called_once()
    assert not trial.commit_once.called
    trial = Mock(); trial.to_precommit.side_effect = OSError('private')
    with pytest.raises(OSError): run_rollback_trial(trial)
    trial.contain.assert_called_once(); assert not trial.commit_once.called


def test_operational_candidate_is_separate_and_keeps_live_gaps():
    from pathlib import Path
    from scripts.dedicated.dev09b.bundle import build_operational_candidate
    root = Path(__file__).resolve().parents[3]
    candidate = build_operational_candidate(root)
    assert candidate['status'] == 'CANDIDATE_NOT_APPROVED'
    assert candidate['operational_authority'] is False
    assert candidate['operational_adapters']['approval'] == 'NOT_PROVIDED'
    assert candidate['trial_procedure']['commit'] == 'NOT_AUTHORIZED'
    assert 'operational.actual_service_uids_and_restricted_socket_directories' in candidate['missing_parameters']
    paths = {r['path'] for r in candidate['sources']}
    assert {'scripts/dedicated/dev09b/operational.py', 'scripts/postgres/dev09b_operational_trial.py',
        'scripts/postgres/dev09b_operational.proposed.json'} <= paths
