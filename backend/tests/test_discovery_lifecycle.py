"""Crash/race tests with durable files, SQLite transactions and NO real sockets."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import stat
from threading import Event,Thread
import time
from unittest.mock import Mock
from uuid import UUID,uuid4

import pytest
from sqlalchemy import select,func,true

from test_discovery import (store,policy,ready_worker,observe,
                            creation,prohibit_real_detection_sockets)
from app.discovery.coordinator import Coordinator
from app.discovery.journal import Journal,JournalError,instance_identity,instance_alive
from app.discovery.models import Job,Observation
from app.discovery.service import Problem,now
from app.audit.models import AuditEvent
from app import create_app
from types import SimpleNamespace


LEASE={'pid':7,'started':'fixture'}


def result(*args,**kwargs):
    return dict(outcome='no_response',evidence=dict(method='tcp_connect',ports=[]))


def recovery_journal(repo):
    return Journal(repo.journal_directory,'fixture-installation',identity=dict(pid=99999999,
        start_ticks='2',boot_id='00000000-0000-0000-0000-000000000001',instance=str(uuid4())))


def recover(repo,**kwargs):
    journal=recovery_journal(repo)
    journal.acquire()
    try:return repo.recover(journal,LEASE,**kwargs)
    finally:journal.release()


@pytest.mark.parametrize('state',['queued','running','cancelling','cancelled','completed','interrupted','failed','timed_out'])
@pytest.mark.parametrize('different_policy',[False,True])
def test_restart_never_authorizes_old_jobs(store,state,different_policy):
    repo,_,identity=store
    job=repo.enqueue(policy(),'10.42.0.1/32',identity)
    with repo.transaction() as session:
        row=session.get(Job,UUID(job['id']));row.status=state
        if state not in ('queued','running','cancelling'):row.finished_at=now()
    network=Mock(side_effect=AssertionError('old job must not probe'))
    try:
        worker=ready_worker(repo,policy(ports=[22]) if different_policy else policy(),network)
    except JournalError:
        worker=repo.workers[-1]
    expected='BLOCKED' if state in ('running','cancelling') else 'READY'
    assert worker.coordinator.state==expected
    if expected=='READY':assert worker.run_one() is False
    network.assert_not_called()
    assert repo.job(UUID(job['id']))['status']==('interrupted' if state=='queued' else state)


def test_queued_with_observations_is_not_assumed_unexecuted(store):
    repo,_,identity=store;observation=observe(repo,identity)
    with repo.transaction() as session:
        identifier=session.get(Observation,observation).job_id
        session.get(Job,identifier).status='queued'
    with pytest.raises(JournalError,match='recovery_required'):ready_worker(repo)
    assert repo.job(identifier)['status']=='queued'


def test_every_probe_has_confirmed_grant_and_durable_attempt(store):
    repo,_,identity=store;seen=[]
    worker=ready_worker(repo)
    def network(ip,p,cancel,**kwargs):
        record=worker.coordinator.journal.read('attempt')
        assert record and record['job_id']==job['id']
        assert UUID(job['id']) not in worker.coordinator.grants
        assert repo.job(UUID(job['id']))['status']=='running'
        assert not cancel();seen.append(ip);return result()
    worker.probe=network
    job=worker.coordinator.submit('10.42.0.1/32',identity)
    assert worker.run_one() is True and len(seen)==1
    assert worker.coordinator.journal.read('attempt') is None
    assert list(repo.journal_directory.glob('attempt-archived-*.json'))
    assert worker.run_one() is False
    assert len(seen)==1


def test_raw_queued_insert_cannot_reconstruct_permission(store):
    repo,_,identity=store;worker=ready_worker(repo)
    repo.enqueue(policy(),'10.42.0.1/32',identity)
    with pytest.raises(Problem):worker.run_one()
    assert worker.coordinator.state=='BLOCKED'
    worker.probe.assert_not_called()


def test_commit_confirmation_and_publication_are_serialized(store,monkeypatch):
    repo,_,identity=store;worker=ready_worker(repo,network=Mock(side_effect=result))
    committed,publish=Event(),Event();original=repo.confirm_admission;errors=[]
    def confirm(*args):
        original(*args);committed.set();assert publish.wait(2)
    monkeypatch.setattr(repo,'confirm_admission',confirm)
    def submit():
        try:worker.coordinator.submit('10.42.0.1/32',identity)
        except BaseException as e:errors.append(e)
    def execute():
        try:worker.run_one()
        except BaseException as e:errors.append(e)
    admission=Thread(target=submit);admission.start();assert committed.wait(2)
    running=Thread(target=execute);running.start();time.sleep(.05)
    worker.probe.assert_not_called()
    publish.set();admission.join(2);running.join(2)
    assert not errors and not admission.is_alive() and not running.is_alive()
    assert worker.probe.call_count==1


@pytest.mark.parametrize('where',['before_admission','after_admission','after_claim','after_terminal'])
def test_lost_commit_results_never_replay(store,monkeypatch,where):
    repo,_,identity=store;network=Mock(side_effect=result);worker=ready_worker(repo,network=network)
    if where in ('before_admission','after_admission'):
        original=repo.enqueue
        def uncertain(*args,**kwargs):
            if where=='after_admission':original(*args,**kwargs)
            raise RuntimeError('constructed lost admission result')
        monkeypatch.setattr(repo,'enqueue',uncertain)
        with pytest.raises(RuntimeError):worker.coordinator.submit('10.42.0.1/32',identity)
    else:
        job=worker.coordinator.submit('10.42.0.1/32',identity)
        target='confirm_running' if where=='after_claim' else 'confirm_terminal'
        monkeypatch.setattr(repo,target,Mock(side_effect=RuntimeError('constructed lost result')))
        with pytest.raises(RuntimeError):worker.run_one()
        assert (repo.journal_directory/'attempt.json').exists()
        assert repo.job(UUID(job['id']))['status']==('running' if where=='after_claim' else 'completed')
    assert worker.coordinator.state=='BLOCKED'
    assert network.call_count==(1 if where=='after_terminal' else 0)
    worker.close()
    if where in ('after_claim','after_terminal'):
        with pytest.raises(JournalError,match='recovery_required'):ready_worker(repo,network=network)
    else:
        fresh=ready_worker(repo,network=network);assert fresh.run_one() is False
    assert network.call_count==(1 if where=='after_terminal' else 0)


@pytest.mark.parametrize('fault',['present','corrupt','permissions'])
def test_journal_uncertainty_blocks_startup(store,fault):
    repo,_,_=store;worker=ready_worker(repo)
    worker.coordinator.journal.write('attempt',job_id=str(uuid4()),policy_sha256='a'*64)
    worker.close();path=repo.journal_directory/'attempt.json'
    if fault=='corrupt':path.write_text('{invalid')
    if fault=='permissions':path.chmod(0o000)
    with pytest.raises(JournalError):ready_worker(repo)
    assert repo.workers[-1].coordinator.state=='BLOCKED'
    repo.workers[-1].probe.assert_not_called()


@pytest.mark.parametrize('fault',['file_fsync','replace','directory_fsync'])
def test_attempt_not_durably_written_never_probes(store,monkeypatch,fault):
    repo,_,identity=store;worker=ready_worker(repo);worker.coordinator.submit('10.42.0.1/32',identity)
    if fault=='file_fsync':monkeypatch.setattr('app.discovery.journal.os.fsync',Mock(side_effect=OSError('constructed fsync failure')))
    elif fault=='replace':monkeypatch.setattr('app.discovery.journal.os.replace',Mock(side_effect=OSError('constructed replace failure')))
    else:monkeypatch.setattr(worker.coordinator.journal,'sync',Mock(side_effect=OSError('constructed directory fsync failure')))
    with pytest.raises(JournalError):worker.run_one()
    assert worker.coordinator.state=='BLOCKED'
    worker.probe.assert_not_called()


def test_journal_owner_alive_or_reused_pid_is_checked(store):
    repo,_,_=store;worker=ready_worker(repo)
    worker.coordinator.journal.identity=instance_identity()
    worker.coordinator.journal.establish_owner();worker.close()
    with pytest.raises(JournalError,match='previous_instance_alive'):ready_worker(repo)
    original=instance_identity();assert instance_alive(original)
    assert not instance_alive(dict(original,start_ticks=str(int(original['start_ticks'])+1)))


def test_two_workers_cannot_own_one_journal(store):
    repo,_,identity=store;first=ready_worker(repo,network=Mock(side_effect=result))
    with pytest.raises(JournalError,match='journal_in_use'):ready_worker(repo)
    first.coordinator.submit('10.42.0.1/32',identity);assert first.run_one()
    assert first.probe.call_count==1


@pytest.mark.parametrize('failure',['persistence','leadership'])
def test_failure_cancels_before_waiting_for_inflight_probes(store,monkeypatch,failure):
    repo,_,identity=store;entered,finish,cancelled=Event(),Event(),Event();calls=[];errors=[]
    def network(ip,p,cancel,**kwargs):
        calls.append(ip)
        if ip.endswith('.1'):
            assert entered.wait(2)
            if failure=='leadership':repo.lease_valid=False
            return result()
        entered.set()
        limit=time.monotonic()+2
        while not cancel() and time.monotonic()<limit:time.sleep(.005)
        if cancel():cancelled.set()
        return result()
    worker=ready_worker(repo,network=network)
    worker.coordinator.submit('10.42.0.1-10.42.0.4',identity)
    original=repo.transaction
    @contextmanager
    def failing(key=None):
        with original(key) as session:
            yield session
            if failure=='persistence' and any(isinstance(v,Observation) for v in session.new):
                raise RuntimeError('constructed persistence failure')
    monkeypatch.setattr(repo,'transaction',failing)
    def execute():
        try:worker.run_one()
        except BaseException as e:errors.append(e)
        finally:finish.set()
    thread=Thread(target=execute);thread.start();thread.join(3)
    assert finish.is_set() and errors and cancelled.is_set() and len(calls)==2
    assert worker.coordinator.state=='BLOCKED' and (repo.journal_directory/'attempt.json').exists()


@pytest.mark.parametrize('terminal_commit',[False,True])
def test_recovery_preserves_evidence_and_is_repeatable(store,monkeypatch,terminal_commit):
    repo,_,identity=store;worker=ready_worker(repo,network=Mock(side_effect=result))
    job=worker.coordinator.submit('10.42.0.1/32',identity)
    target='confirm_terminal' if terminal_commit else 'confirm_running'
    original=getattr(repo,target);monkeypatch.setattr(repo,target,Mock(side_effect=RuntimeError('lost commit response')))
    with pytest.raises(RuntimeError):worker.run_one()
    worker.close();monkeypatch.setattr(repo,target,original)
    before=repo.job(UUID(job['id']))
    first=recover(repo);assert first['state']=='RECOVERED'
    after=repo.job(UUID(job['id']))
    assert after['observations']==before['observations']
    assert after['status']==('completed' if terminal_commit else 'interrupted')
    with repo.transaction() as s:audits=s.scalar(select(func.count()).select_from(AuditEvent))
    assert recover(repo)['state']=='ALREADY_CLEAN'
    with repo.transaction() as s:assert s.scalar(select(func.count()).select_from(AuditEvent))==audits
    fresh=ready_worker(repo);assert fresh.run_one() is False;fresh.probe.assert_not_called()


def test_recovery_commit_uncertainty_is_idempotent(store,monkeypatch):
    repo,_,identity=store;worker=ready_worker(repo)
    worker.coordinator.submit('10.42.0.1/32',identity)
    monkeypatch.setattr(repo,'confirm_running',Mock(side_effect=RuntimeError('uncertain claim')))
    with pytest.raises(RuntimeError):worker.run_one()
    worker.close();original=repo.confirm_recovery
    monkeypatch.setattr(repo,'confirm_recovery',Mock(side_effect=RuntimeError('uncertain recovery')))
    with pytest.raises(RuntimeError):recover(repo)
    with repo.transaction() as s:before=s.scalar(select(func.count()).select_from(AuditEvent))
    monkeypatch.setattr(repo,'confirm_recovery',original)
    assert recover(repo)['state']=='RECOVERED'
    with repo.transaction() as s:assert s.scalar(select(func.count()).select_from(AuditEvent))==before


def test_corrupt_attempt_is_preserved_by_explicit_recovery(store,monkeypatch):
    repo,_,identity=store;worker=ready_worker(repo)
    worker.coordinator.submit('10.42.0.1/32',identity)
    monkeypatch.setattr(repo,'confirm_running',Mock(side_effect=RuntimeError('uncertain')))
    with pytest.raises(RuntimeError):worker.run_one()
    worker.close();(repo.journal_directory/'attempt.json').write_text('corrupt evidence')
    assert recover(repo)['state']=='RECOVERED'
    assert any(p.read_text()=='corrupt evidence' for p in repo.journal_directory.glob('attempt-archived-*.json'))


def test_api_exposes_readiness_and_keeps_history_available(store):
    repo,sessions,identity=store;worker=ready_worker(repo)
    access=SimpleNamespace(resolve_identity=lambda:identity,read_scope=lambda i:true(),can_create=lambda *a:True)
    app=create_app('testing',inventory_access=access,inventory_session_factory=sessions,discovery_policy=policy())
    app.extensions['discovery'].update(repository=repo,coordinator=worker.coordinator)
    client=app.test_client();worker.coordinator.block('recovery_required')
    config=client.get('/api/v1/discovery/config').json
    assert config['enabled'] is True and config['operational']=={'state':'BLOCKED','reason':'recovery_required'}
    assert client.post('/api/v1/discovery/jobs',json={'target':'10.42.0.1/32'}).status_code==503
    assert client.get('/api/v1/discovery/jobs').status_code==200
    with repo.transaction() as session:assert session.scalar(select(func.count()).select_from(Job))==0


def test_journal_permissions_and_integrity_envelope(store):
    repo,_,_=store;worker=ready_worker(repo);j=worker.coordinator.journal
    assert stat.S_IMODE(repo.journal_directory.stat().st_mode)==0o700
    for p in repo.journal_directory.iterdir():assert stat.S_IMODE(p.stat().st_mode)==0o600
    payload=json.loads((repo.journal_directory/'owner.json').read_text())
    payload['payload']['owner']['pid']+=1
    (repo.journal_directory/'owner.json').write_text(json.dumps(payload))
    with pytest.raises(JournalError,match='journal_corrupt'):j.read('owner')


@pytest.mark.parametrize('where',['before_claim','after_observation','before_recovery'])
def test_additional_commit_boundaries_preserve_evidence(store,monkeypatch,where):
    repo,_,identity=store;network=Mock(side_effect=result);worker=ready_worker(repo,network=network)
    job=worker.coordinator.submit('10.42.0.1/32',identity);original=repo.transaction
    fired=False
    original_transition=repo.transition;original_recovery=repo.apply_recovery
    def transition(*args,**kwargs):
        nonlocal fired
        value=original_transition(*args,**kwargs)
        if where=='before_claim' and not fired:
            fired=True;raise RuntimeError('constructed pre-claim-commit failure')
        return value
    def apply_recovery(*args,**kwargs):
        nonlocal fired
        value=original_recovery(*args,**kwargs)
        if where=='before_recovery' and not fired:
            fired=True;raise RuntimeError('constructed pre-recovery-commit failure')
        return value
    monkeypatch.setattr(repo,'transition',transition)
    monkeypatch.setattr(repo,'apply_recovery',apply_recovery)
    @contextmanager
    def fault(key=None):
        nonlocal fired
        observed=False
        with original(key) as session:
            yield session
            observed=any(isinstance(v,Observation) for v in session.new)
        if not fired and where=='after_observation' and observed:
            fired=True;raise RuntimeError('constructed lost observation commit result')
    if where=='before_recovery':
        confirm=repo.confirm_running
        monkeypatch.setattr(repo,'confirm_running',Mock(side_effect=RuntimeError('constructed lost claim result')))
        with pytest.raises(RuntimeError):worker.run_one()
        monkeypatch.setattr(repo,'confirm_running',confirm)
        worker.close();monkeypatch.setattr(repo,'transaction',fault)
        with pytest.raises(RuntimeError):recover(repo)
        assert (repo.journal_directory/'recovery.json').exists()
    else:
        monkeypatch.setattr(repo,'transaction',fault)
        with pytest.raises(RuntimeError):worker.run_one()
        assert worker.coordinator.state=='BLOCKED'
        worker.close()
    assert fired and (repo.journal_directory/'attempt.json').exists()
    monkeypatch.setattr(repo,'transaction',original)
    assert recover(repo)['state']=='RECOVERED'
    saved=repo.job(UUID(job['id']))
    assert saved['status']=='interrupted'
    assert saved['processed']==len(saved['observations'])==(1 if where=='after_observation' else 0)
    assert network.call_count==(1 if where=='after_observation' else 0)
    assert recover(repo)['state']=='ALREADY_CLEAN'


@pytest.mark.parametrize('damage',['missing_plan','duplicate_job','negative_progress','unknown_state','invalid_uuid'])
def test_checksummed_but_invalid_recovery_plan_is_refused(store,damage):
    from app.discovery.journal import canonical
    import hashlib
    repo,_,_=store;worker=ready_worker(repo);j=worker.coordinator.journal
    row=dict(id=str(uuid4()),before='running',processed=0,observations=0)
    j.write('recovery',plan=dict(audit_id=str(uuid4()),jobs=[row],reason='operator_reviewed'))
    path=repo.journal_directory/'recovery.json';envelope=json.loads(path.read_text())
    payload=envelope['payload']
    if damage=='missing_plan':del payload['plan']
    elif damage=='duplicate_job':payload['plan']['jobs'].append(dict(row))
    elif damage=='negative_progress':payload['plan']['jobs'][0].update(processed=-1,observations=-1)
    elif damage=='unknown_state':payload['plan']['jobs'][0]['before']='completed'
    else:payload['plan']['audit_id']='not-a-uuid'
    envelope['sha256']=hashlib.sha256(canonical(payload)).hexdigest();path.write_bytes(canonical(envelope))
    with pytest.raises(JournalError,match='journal_corrupt'):j.read('recovery')


def test_pending_recovery_cannot_hide_an_unplanned_active_job(store,monkeypatch):
    repo,_,identity=store;worker=ready_worker(repo)
    worker.coordinator.submit('10.42.0.1/32',identity)
    monkeypatch.setattr(repo,'confirm_running',Mock(side_effect=RuntimeError('constructed lost claim result')))
    with pytest.raises(RuntimeError):worker.run_one()
    worker.close();original=repo.confirm_recovery
    monkeypatch.setattr(repo,'confirm_recovery',Mock(side_effect=RuntimeError('constructed lost recovery result')))
    with pytest.raises(RuntimeError):recover(repo)
    extra=repo.enqueue(policy(),'10.42.0.2/32',identity)
    monkeypatch.setattr(repo,'confirm_recovery',original)
    with pytest.raises(JournalError,match='state_inconsistent'):recover(repo)
    assert repo.job(UUID(extra['id']))['status']=='queued'
    assert (repo.journal_directory/'attempt.json').exists()
    assert (repo.journal_directory/'recovery.json').exists()


def test_lost_leadership_refuses_admission_before_commit(store):
    repo,_,identity=store;worker=ready_worker(repo);repo.lease_valid=False
    with pytest.raises(JournalError,match='leadership_lost'):
        worker.coordinator.submit('10.42.0.1/32',identity)
    assert worker.coordinator.state=='BLOCKED' and not worker.coordinator.grants
    with repo.transaction() as session:assert session.scalar(select(func.count()).select_from(Job))==0
    worker.probe.assert_not_called()


def test_explicit_recovery_preserves_decisions_and_resources(store):
    repo,_,identity=store;worker=ready_worker(repo);observation=observe(repo,identity)
    resource=repo.decide(observation,creation(),identity,true(),lambda *a:True)['resource']
    with repo.transaction() as session:
        identifier=session.get(Observation,observation).job_id
        job=session.get(Job,identifier);job.status='running';job.processed=1;job.finished_at=None
    before=repo.candidate(observation,true())
    worker.coordinator.journal.write('attempt',job_id=str(identifier),policy_sha256='a'*64)
    worker.close()
    assert recover(repo)['state']=='RECOVERED'
    assert repo.job(identifier)['status']=='interrupted'
    assert repo.candidate(observation,true())==before
    assert repo.candidate(observation,true())['decision']['resource_id']==resource['id']


def test_api_persistence_failure_blocks_execution(store,monkeypatch):
    repo,sessions,identity=store;worker=ready_worker(repo)
    access=SimpleNamespace(resolve_identity=lambda:identity,read_scope=lambda i:true(),can_create=lambda *a:True)
    app=create_app('testing',inventory_access=access,inventory_session_factory=sessions,discovery_policy=policy())
    app.extensions['discovery'].update(repository=repo,coordinator=worker.coordinator)
    monkeypatch.setattr(repo,'cancel',Mock(side_effect=RuntimeError('constructed private diagnostic')))
    response=app.test_client().post('/api/v1/discovery/jobs/'+str(uuid4())+'/cancel')
    assert response.status_code==503 and 'private diagnostic' not in response.text
    assert worker.coordinator.state=='BLOCKED' and worker.coordinator.cancel.is_set()
