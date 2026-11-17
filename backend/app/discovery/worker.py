"""One elected worker; old rows never create volatile execution permissions."""
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from threading import Event, Thread
import logging
import time
from uuid import uuid4
from sqlalchemy import select, text

from .models import Job, Observation
from .service import now, LEADER_KEY, ADMISSION_KEY, ACTIVE
from .network import probe
from .coordinator import Coordinator
from .journal import JournalError


class Worker:
    def __init__(self, repository, policy, leader_factory, network_probe=probe, *, coordinator=None):
        self.repository, self.policy = repository, policy
        self.leader_factory, self.probe = leader_factory, network_probe
        self.coordinator = coordinator or Coordinator(repository, policy, None)
        self.stop = self.coordinator.stop
        self.thread = None
        self.leader_connection = None
        self.current_cancel = None

    def guard(self):
        try:
            if self.leader_connection is None:
                raise JournalError('leadership_lost')
            row = self.leader_connection.execute(text("""SELECT pg_backend_pid() AS pid,
              (SELECT backend_start::text FROM pg_stat_activity WHERE pid=pg_backend_pid()) AS started,
              EXISTS(SELECT FROM pg_catalog.pg_locks WHERE locktype='advisory'
              AND pid=pg_backend_pid() AND granted AND classid::bigint=0
              AND objid::bigint=:key AND objsubid=1) AS held"""),dict(key=LEADER_KEY)).mappings().one()
            self.leader_connection.rollback()
            if row['held'] is not True:
                raise JournalError('leadership_lost')
            return dict(pid=row['pid'],started=row['started'])
        except BaseException:
            self.coordinator.block('leadership_lost')
            self.stop.set()
            if self.current_cancel is not None:self.current_cancel.set()
            raise

    def start(self):
        with self.coordinator.lock:
            if self.thread is not None:raise JournalError('worker_already_started')
            self.thread = Thread(target=self.loop,name='livenet-discovery',daemon=True)
            self.thread.start()

    def acquire(self):
        if self.leader_factory is None:raise JournalError('leadership_unavailable')
        self.leader_connection = self.leader_factory()
        if not self.leader_connection.execute(text('SELECT pg_catalog.pg_try_advisory_lock(:key)'),dict(key=LEADER_KEY)).scalar_one():
            raise JournalError('leadership_unavailable')
        self.leader_connection.rollback()
        self.coordinator.initialize(self.guard())

    def loop(self):
        try:
            self.acquire()
            while not self.stop.is_set() and self.coordinator.state=='READY':
                self.guard()
                if not self.run_one():self.stop.wait(.5)
        except Exception as error:
            reason=str(error) if isinstance(error,JournalError) else 'persistence_uncertain'
            self.coordinator.block(reason)
            logging.getLogger(__name__).error('Discovery blocked; explicit recovery may be required')
        finally:
            self.close()

    def close(self):
        self.coordinator.close()
        if self.leader_connection is not None:
            self.leader_connection.close()
            self.leader_connection=None

    def run_one(self):
        cancel=Event();pool=None
        self.current_cancel=cancel
        try:
            self.guard()
            with self.coordinator.lock:
                self.coordinator.require_ready()
                self.repository.prune_grants(self.coordinator.grants,self.coordinator.lease)
                with self.repository.transaction(ADMISSION_KEY) as session:
                    self.repository.ensure_lease(session,self.coordinator.lease)
                    jobs=list(session.scalars(select(Job).where(Job.status.in_(ACTIVE))
                              .order_by(Job.created_at,Job.id).with_for_update()))
                    if not jobs:return False
                    if any(j.status!='queued' for j in jobs):raise JournalError('state_inconsistent')
                    job=jobs[0];identifier=job.id
                    self.coordinator.begin_attempt(identifier)
                    if job.policy!=self.policy.snapshot():
                        self.repository.transition(session,job,'interrupted','policy_changed')
                        changed=True
                    else:
                        addresses=self.policy.targets(job.target)
                        audit_id=self.repository.transition(session,job,'running','attempt_admitted')
                        changed=False
                if changed:
                    self.coordinator.complete_attempt(identifier)
                    return True
                self.repository.confirm_running(identifier,audit_id,self.coordinator.lease)
            deadline=time.monotonic()+self.policy.job_timeout
            addresses=iter(addresses);inflight={};exhausted=False;final='completed'
            pool=ThreadPoolExecutor(max_workers=self.policy.concurrency,thread_name_prefix='discovery-target')

            def cancelled():
                return cancel.is_set() or not self.coordinator.network_allowed(identifier)

            def attempt(ip):
                if cancelled():return None
                return self.probe(ip,self.policy,cancelled,deadline=deadline)

            while True:
                self.guard()
                if self.coordinator.state!='READY':raise JournalError(self.coordinator.reason)
                with self.repository.transaction() as session:
                    current=session.get(Job,identifier)
                    if current is None or current.status not in ('running','cancelling'):
                        raise JournalError('state_inconsistent')
                    stopping=current.status=='cancelling'
                if stopping or self.stop.is_set():
                    final='cancelled' if stopping else 'interrupted';cancel.set()
                elif time.monotonic()>=deadline:
                    final='timed_out';cancel.set()
                while not exhausted and not cancelled() and len(inflight)<self.policy.concurrency:
                    try:ip=next(addresses)
                    except StopIteration:exhausted=True;break
                    inflight[pool.submit(attempt,ip)]=ip
                if not inflight:break
                done,_=wait(inflight,timeout=.1,return_when=FIRST_COMPLETED)
                for future in done:
                    ip=inflight.pop(future)
                    try:result=future.result()
                    except Exception:result=dict(outcome='error',evidence=dict(method='tcp_connect',ports=[],error='probe_failed'))
                    if result is None:continue
                    self.guard()
                    if self.coordinator.state!='READY':raise JournalError(self.coordinator.reason)
                    with self.repository.transaction() as session:
                        job=session.scalar(select(Job).where(Job.id==identifier).with_for_update())
                        if job.status not in ('running','cancelling'):raise JournalError('state_inconsistent')
                        session.add(Observation(id=uuid4(),job_id=identifier,ip=ip,outcome=result['outcome'],observed_at=now(),
                            source_type='tcp_connect',source_instance=str(identifier),evidence=result['evidence']))
                        job.processed+=1
            with self.coordinator.lock:
                if self.coordinator.state!='READY' or self.coordinator.cancel.is_set():
                    raise JournalError(self.coordinator.reason or 'state_inconsistent')
                with self.repository.transaction() as session:
                    self.repository.ensure_lease(session,self.coordinator.lease)
                    job=session.scalar(select(Job).where(Job.id==identifier).with_for_update())
                    terminal='cancelled' if job.status=='cancelling' else final
                    self.repository.transition(session,job,terminal,terminal)
                self.coordinator.complete_attempt(identifier)
            return True
        except BaseException as error:
            cancel.set()
            reason=str(error) if isinstance(error,JournalError) else 'persistence_uncertain'
            self.coordinator.block(reason)
            raise
        finally:
            if pool is not None:pool.shutdown(wait=True,cancel_futures=True)
