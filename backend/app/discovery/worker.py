"""One PostgreSQL-elected worker per database, bounded target threads per job.

Never resumes running jobs after restart or retries a failed persistence/commit.
"""
from concurrent.futures import ThreadPoolExecutor,wait,FIRST_COMPLETED
from threading import Event,Thread
import logging
import time
from uuid import uuid4
from sqlalchemy import select,text
from .models import Job,Observation
from .service import now,LEADER_KEY
from .network import probe


class Worker:
    def __init__(self,repository,policy,leader_factory,network_probe=probe):
        self.repository,self.policy,self.leader_factory,self.probe=repository,policy,leader_factory,network_probe
        self.stop=Event();self.thread=None
        self.leader_connection=None;self.current_cancel=None

    def guard(self):
        if self.leader_connection is None:return  # Direct offline runner tests.
        try:
            held=self.leader_connection.execute(text("""SELECT EXISTS(SELECT FROM pg_catalog.pg_locks
                WHERE locktype='advisory' AND pid=pg_backend_pid() AND granted
                AND classid::bigint=0 AND objid::bigint=:key AND objsubid=1)"""),dict(key=LEADER_KEY)).scalar_one()
            self.leader_connection.rollback()
            if held is not True:raise RuntimeError('Discovery leader lock lost')
        except BaseException:
            self.stop.set()
            if self.current_cancel is not None:self.current_cancel.set()
            raise

    def start(self):
        self.thread=Thread(target=self.loop,name='livenet-discovery',daemon=True);self.thread.start()

    def loop(self):
        connection=None
        try:
            connection=self.leader_factory()
            if not connection.execute(text('SELECT pg_catalog.pg_try_advisory_lock(:key)'),dict(key=LEADER_KEY)).scalar_one():return
            connection.rollback()
            self.leader_connection=connection
            with self.repository.transaction() as session:
                for job in session.scalars(select(Job).where(Job.status.in_(('running','cancelling'))).with_for_update()):
                    job.status='interrupted';job.finished_at=now()
            while not self.stop.is_set():
                self.guard()
                if not self.run_one():self.stop.wait(.5)
        except Exception:
            # SQL/commit uncertainty stops the worker; no automatic job/network retry.
            logging.getLogger(__name__).error('Discovery worker stopped; inspect persisted job state before restart')
        finally:
            if connection is not None:connection.close()
            self.leader_connection=None

    def run_one(self):
        self.guard()
        with self.repository.transaction() as session:
            job=session.scalar(select(Job).where(Job.status=='queued').order_by(Job.created_at,Job.id).limit(1).with_for_update())
            if job is None:return False
            if job.policy!=self.policy.snapshot():
                job.status='interrupted';job.finished_at=now();return True
            identifier=job.id;addresses=self.policy.targets(job.target);job.status='running'
        cancel=Event();deadline=time.monotonic()+self.policy.job_timeout
        self.current_cancel=cancel
        addresses=iter(addresses);inflight={};exhausted=False;final='completed'
        # A bounded batch is submitted at a time; no unbounded futures queue.
        with ThreadPoolExecutor(max_workers=self.policy.concurrency,thread_name_prefix='discovery-target') as pool:
            while True:
                self.guard()
                with self.repository.transaction() as session:
                    current=session.get(Job,identifier)
                    if current.status not in ('running','cancelling'):raise RuntimeError('Discovery job state changed; no retry')
                    stopping=current.status=='cancelling'
                if stopping or self.stop.is_set():final='cancelled' if stopping else 'interrupted';cancel.set()
                elif time.monotonic()>=deadline:final='timed_out';cancel.set()
                while not exhausted and not cancel.is_set() and len(inflight)<self.policy.concurrency:
                    try:ip=next(addresses)
                    except StopIteration:exhausted=True;break
                    inflight[pool.submit(self.probe,ip,self.policy,cancel.is_set,deadline=deadline)]=ip
                if not inflight:break
                done,_=wait(inflight,timeout=.1,return_when=FIRST_COMPLETED)
                for future in done:
                    ip=inflight.pop(future)
                    try:result=future.result()
                    except Exception:result=dict(outcome='error',evidence=dict(method='tcp_connect',ports=[],error='probe_failed'))
                    observed=now()
                    self.guard()
                    with self.repository.transaction() as session:
                        job=session.scalar(select(Job).where(Job.id==identifier).with_for_update())
                        if job.status not in ('running','cancelling'):raise RuntimeError('Discovery job state changed; no retry')
                        session.add(Observation(id=uuid4(),job_id=identifier,ip=ip,outcome=result['outcome'],observed_at=observed,
                            source_type='tcp_connect',source_instance=str(identifier),evidence=result['evidence']))
                        job.processed+=1
            with self.repository.transaction() as session:
                job=session.scalar(select(Job).where(Job.id==identifier).with_for_update())
                job.status='cancelled' if job.status=='cancelling' else final;job.finished_at=now()
        return True
