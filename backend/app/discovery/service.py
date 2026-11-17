"""Persistent observations and explicit, one-shot manual decisions."""
from contextlib import contextmanager
from datetime import datetime,timezone
from uuid import UUID,uuid4
from sqlalchemy import select,func,or_,text
from app.inventory import service as inventory
from app.inventory.models import Resource,ResourceIdentifier
from app.inventory.schemas import serialize_resource,validate_creation
from app.audit.service import record_audit_event
from .models import Job,Observation,Decision
from app.audit.models import AuditEvent
from .journal import JournalError,valid_identity

ACTIVE=('queued','running','cancelling')
ADMISSION_KEY=701030112
LEADER_KEY=701030113


def now():return datetime.now(timezone.utc)


def timestamp(value):return value.replace(tzinfo=value.tzinfo or timezone.utc).isoformat()


class Problem(Exception):
    def __init__(self,status,code):self.status,self.code=status,code


class Repository:
    def __init__(self,sessions):self.sessions=sessions

    @contextmanager
    def transaction(self,key=None):
        with self.sessions() as session:
            with session.begin():
                if key is not None:session.execute(text('SELECT pg_catalog.pg_advisory_xact_lock(:key)'),{'key':key})
                yield session

    def enqueue(self,policy,target,identity,*,lease=None):
        addresses=policy.targets(target)
        with self.transaction(ADMISSION_KEY) as session:
            if lease is not None:self.ensure_lease(session,lease)
            active=session.scalar(select(func.count()).select_from(Job).where(Job.status.in_(ACTIVE)))
            if active>=policy.max_jobs:raise Problem(409,'discovery_busy')
            job=Job(id=uuid4(),actor_id=identity.actor_id,target=target.strip(),policy=policy.snapshot(),status='queued',
                total=len(addresses),processed=0,created_at=now(),finished_at=None)
            session.add(job)
            record_audit_event(session,actor_type=identity.actor_type,actor_id=identity.actor_id,action='discovery.job.started',
                entity_type='discovery.job',entity_id=job.id,outcome='success',changes={'target':job.target,'total':job.total,'policy':job.policy})
            session.flush()
            return self.job_public(job)

    def ensure_lease(self,session,lease):
        if lease is None or session.scalar(text("""SELECT EXISTS(SELECT FROM pg_catalog.pg_locks l
          JOIN pg_catalog.pg_stat_activity a ON a.pid=l.pid WHERE l.locktype='advisory'
          AND l.granted AND l.classid::bigint=0 AND l.objid::bigint=:key AND l.objsubid=1
          AND l.pid=:pid AND a.backend_start::text=:started AND a.datname=current_database())"""),
          dict(key=LEADER_KEY,pid=lease['pid'],started=lease['started'])) is not True:
            raise JournalError('leadership_lost')

    def confirm_admission(self,identifier,policy,lease):
        with self.transaction() as session:
            self.ensure_lease(session,lease)
            job=session.get(Job,identifier)
            if job is None or job.status!='queued' or job.processed!=0 or job.policy!=policy.snapshot():
                raise JournalError('state_inconsistent')

    def observation_count(self,session,identifier):
        return session.scalar(select(func.count()).select_from(Observation).where(Observation.job_id==identifier))

    def confirm_terminal(self,identifier,lease):
        with self.transaction() as session:
            self.ensure_lease(session,lease)
            job=session.get(Job,identifier)
            if (job is None or job.status not in ('completed','cancelled','interrupted','failed','timed_out')
                    or job.finished_at is None or job.processed!=self.observation_count(session,identifier)
                    or (job.status=='completed' and job.processed!=job.total)):
                raise JournalError('state_inconsistent')

    def transition(self,session,job,status,reason):
        before=job.status
        allowed={'queued':{'running','interrupted'},'running':{'completed','interrupted','timed_out'},
                 'cancelling':{'cancelled','interrupted'}}
        if status not in allowed.get(before,set()):raise JournalError('state_inconsistent')
        if status=='completed' and job.processed!=job.total:raise JournalError('state_inconsistent')
        job.status=status
        if status!='running':job.finished_at=now()
        event=record_audit_event(session,actor_type='system',action='discovery.job.transition',
            entity_type='discovery.job',entity_id=job.id,outcome='success',
            changes={'before':before,'after':status},context={'reason':reason})
        event.id=uuid4()
        session.flush()
        return event.id

    def confirm_running(self,identifier,audit_id,lease):
        with self.transaction() as session:
            self.ensure_lease(session,lease)
            job=session.get(Job,identifier)
            if (job is None or job.status not in ('running','cancelling')
                    or session.scalar(select(AuditEvent.id).where(AuditEvent.id==audit_id)) is None):
                raise JournalError('state_inconsistent')

    def prune_grants(self,grants,lease):
        with self.transaction() as session:
            self.ensure_lease(session,lease)
            for identifier in tuple(grants):
                job=session.get(Job,identifier)
                if job is None or job.status in ('running','cancelling'):raise JournalError('state_inconsistent')
                if job.status!='queued':grants.remove(identifier)

    def recovery_plan(self,session,jobs,reason):
        rows=[]
        for job in jobs:
            count=self.observation_count(session,job.id)
            if job.processed!=count:raise JournalError('state_inconsistent')
            rows.append(dict(id=str(job.id),before=job.status,processed=job.processed,observations=count))
        return dict(audit_id=str(uuid4()),jobs=rows,reason=reason)

    def apply_recovery(self,session,plan):
        audit_id=UUID(plan['audit_id'])
        if session.scalar(select(AuditEvent.id).where(AuditEvent.id==audit_id)) is not None:return
        for row in plan['jobs']:
            job=session.scalar(select(Job).where(Job.id==UUID(row['id'])).with_for_update())
            if (job is None or job.status!=row['before'] or job.processed!=row['processed']
                    or self.observation_count(session,job.id)!=row['observations']):raise JournalError('state_inconsistent')
            job.status='interrupted';job.finished_at=now()
        event=record_audit_event(session,actor_type='operator' if plan['reason']=='operator_reviewed' else 'system',
            action='discovery.recovery.confirmed',entity_type='discovery.recovery',entity_id=audit_id,
            outcome='success',changes={'jobs':[r['id'] for r in plan['jobs']]},context={'reason':plan['reason']})
        event.id=audit_id
        session.flush()

    def confirm_recovery(self,plan,lease):
        with self.transaction() as session:
            self.ensure_lease(session,lease)
            if session.scalar(select(AuditEvent.id).where(AuditEvent.id==UUID(plan['audit_id']))) is None:
                raise JournalError('persistence_uncertain')
            for row in plan['jobs']:
                job=session.get(Job,UUID(row['id']))
                if (job is None or job.status!='interrupted' or job.finished_at is None
                        or job.processed!=row['processed'] or self.observation_count(session,job.id)!=row['observations']):
                    raise JournalError('state_inconsistent')

    def bootstrap(self,coordinator,lease):
        journal=coordinator.journal;plan=None
        with self.transaction(ADMISSION_KEY) as session:
            self.ensure_lease(session,lease)
            jobs=list(session.scalars(select(Job).where(Job.status.in_(ACTIVE)).with_for_update()))
            if any(j.status!='queued' or j.processed!=0 or j.finished_at is not None
                   or self.observation_count(session,j.id)!=0 for j in jobs):
                raise JournalError('recovery_required')
            if jobs:
                journal.establish_owner()
                plan=self.recovery_plan(session,jobs,'previous_queue_without_execution')
                journal.write('recovery',plan=plan)
                self.apply_recovery(session,plan)
        if plan:
            self.confirm_recovery(plan,lease)
            journal.archive('recovery')

    def recover(self,journal,lease,*,previous=None):
        """Caller owns both PostgreSQL election and journal lock; never probes."""
        attempt=None;corrupt=False
        try:attempt=journal.read('attempt')
        except JournalError as error:
            if str(error)!='journal_corrupt':raise
            corrupt=True
        pending=journal.read('recovery')
        owners=[v for v in (journal.previous,attempt['owner'] if attempt else None,pending['owner'] if pending else None,previous) if v is not None]
        if any(not valid_identity(v) or journal.alive(v) for v in owners):raise JournalError('previous_instance_alive')
        with self.transaction(ADMISSION_KEY) as session:
            self.ensure_lease(session,lease)
            jobs=list(session.scalars(select(Job).where(Job.status.in_(ACTIVE)).with_for_update()))
            if attempt:
                try:attempt_id=UUID(attempt['job_id'])
                except (KeyError,ValueError,TypeError):raise JournalError('journal_corrupt') from None
                job=session.get(Job,attempt_id)
                if (job is None or job.processed!=self.observation_count(session,attempt_id)
                        or (job.status not in ACTIVE and job.finished_at is None)
                        or (job.status=='completed' and job.processed!=job.total)):
                    raise JournalError('state_inconsistent')
            if (jobs or attempt or corrupt or pending) and not owners:raise JournalError('previous_instance_unknown')
            if not jobs and not attempt and not corrupt and not pending:return dict(state='ALREADY_CLEAN',jobs=0)
            if pending:
                plan=pending['plan']
                # A persisted audit only confirms this exact plan. Unexpected
                # active rows cannot be hidden by replaying an older recovery.
                if {str(j.id) for j in jobs} - {r['id'] for r in plan['jobs']}:
                    raise JournalError('state_inconsistent')
            else:
                plan=self.recovery_plan(session,jobs,'operator_reviewed')
                journal.establish_owner()
                journal.write('recovery',plan=plan)
            self.apply_recovery(session,plan)
        self.confirm_recovery(plan,lease)
        journal.archive('attempt');journal.archive('recovery')
        return dict(state='RECOVERED',jobs=len(plan['jobs']))

    def job_public(self,job):
        return dict(id=str(job.id),target=job.target,status=job.status,total=job.total,processed=job.processed,
            created_at=timestamp(job.created_at),finished_at=timestamp(job.finished_at) if job.finished_at else None,policy=job.policy)

    def jobs(self):
        with self.transaction() as session:
            return [self.job_public(j) for j in session.scalars(select(Job).order_by(Job.created_at.desc(),Job.id).limit(50))]

    def job(self,identifier):
        with self.transaction() as session:
            job=session.get(Job,identifier)
            if job is None:raise Problem(404,'not_found')
            result=self.job_public(job)
            decisions={d.observation_id:d for d in session.scalars(select(Decision).join(Observation).where(Observation.job_id==identifier))}
            result['observations']=[self.observation_public(o,decisions.get(o.id)) for o in session.scalars(
                select(Observation).where(Observation.job_id==identifier).order_by(Observation.observed_at,Observation.id))]
            return result

    def observation_public(self,o,decision=None):
        return dict(id=str(o.id),ip=o.ip,outcome=o.outcome,hostname=None,observed_at=timestamp(o.observed_at),
            first_seen_at=timestamp(o.observed_at),last_seen_at=timestamp(o.observed_at),source_type=o.source_type,
            source_instance=o.source_instance,confidence=None,verification_status='unverified',evidence=o.evidence,
            decision=dict(mode=decision.mode,resource_id=str(decision.resource_id),decided_at=timestamp(decision.decided_at)) if decision else None)

    def resource_history(self,identifier,scope,*,page=1,per_page=20):
        with self.transaction() as session:
            # Authorize the resource before accessing its observation history.
            # IP coincidence without an explicit persisted decision is excluded.
            if inventory.get_resource(session,scope,identifier) is None:raise Problem(404,'not_found')
            total=session.scalar(select(func.count()).select_from(Decision).where(Decision.resource_id==identifier))
            rows=session.execute(select(Observation,Decision).join(Decision,Decision.observation_id==Observation.id)
                .where(Decision.resource_id==identifier).order_by(Observation.observed_at.desc(),Observation.id)
                .offset((page-1)*per_page).limit(per_page)).all()
            return dict(resource_id=str(identifier),items=[dict(self.observation_public(o,d),job_id=str(o.job_id)) for o,d in rows],
                total=total,page=page,per_page=per_page)

    def cancel(self,identifier,identity):
        with self.transaction() as session:
            job=session.scalar(select(Job).where(Job.id==identifier).with_for_update())
            if job is None:raise Problem(404,'not_found')
            if job.status in ('queued','running'):
                job.status='cancelled' if job.status=='queued' else 'cancelling'
                if job.status=='cancelled':job.finished_at=now()
                record_audit_event(session,actor_type=identity.actor_type,actor_id=identity.actor_id,action='discovery.job.cancelled',
                    entity_type='discovery.job',entity_id=job.id,outcome='success',changes={})
            return self.job_public(job)

    def _matches(self,session,observation,scope):
        # Hints only: network identifiers and prior explicit decisions, never identity proof.
        known=select(Decision.resource_id).join(Observation).where(Observation.ip==observation.ip)
        identifiers=select(ResourceIdentifier.resource_id).where(ResourceIdentifier.identifier_type.in_(('ipv4','IPv4')),
            ResourceIdentifier.normalized_value==observation.ip)
        resources=session.scalars(select(Resource).where(scope,or_(Resource.id.in_(known),Resource.id.in_(identifiers))).order_by(Resource.id).limit(21)).all()
        return [dict(id=str(r.id),display_name=r.display_name,administrative_state=r.administrative_state) for r in resources[:20]],len(resources)>20

    def candidate(self,identifier,scope):
        with self.transaction() as session:
            observation=session.get(Observation,identifier)
            if observation is None or observation.outcome!='responded':raise Problem(404,'not_found')
            decision=session.scalar(select(Decision).where(Decision.observation_id==identifier))
            result=self.observation_public(observation,decision)
            result['possible_matches'],result['matches_truncated']=self._matches(session,observation,scope)
            result['previous_observations']=[dict(id=str(o.id),job_id=str(o.job_id),observed_at=timestamp(o.observed_at),outcome=o.outcome)
                for o in session.scalars(select(Observation).where(Observation.ip==observation.ip,Observation.id!=identifier)
                    .order_by(Observation.observed_at.desc()).limit(20))]
            return result

    def decide(self,identifier,payload,identity,scope,can_create):
        if not isinstance(payload,dict):raise Problem(400,'invalid_request')
        mode=payload.get('mode')
        if mode=='create' and set(payload)=={'mode','resource','confirm_distinct'}:
            data=validate_creation(payload['resource'])
            if data.get('administrative_state','active')!='active' or type(payload['confirm_distinct']) is not bool:raise Problem(400,'invalid_request')
            if can_create(identity,data) is not True:raise Problem(403,'forbidden')
        elif mode=='associate' and set(payload)=={'mode','resource_id'}:
            from app.inventory.schemas import validate_resource_id
            resource_id=validate_resource_id(payload['resource_id'])
        else:raise Problem(400,'invalid_request')
        # Serialize manual decisions so concurrent observations recheck new hints.
        key=701030114
        with self.transaction(key) as session:
            observation=session.get(Observation,identifier)
            if observation is None or observation.outcome!='responded':raise Problem(404,'not_found')
            previous=session.scalar(select(Decision).where(Decision.observation_id==identifier))
            if previous:
                resource=inventory.get_resource(session,scope,previous.resource_id)
                if resource is None:raise Problem(404,'not_found')
                return dict(resource=serialize_resource(resource),already_decided=True)
            if mode=='create':
                matches,truncated=self._matches(session,observation,scope)
                if (matches or truncated) and not payload['confirm_distinct']:raise Problem(409,'discovery_matches_review')
                resource=inventory.create_resource(session,data,identity)
            else:
                resource=inventory.get_resource(session,scope,resource_id)
                if resource is None:raise Problem(404,'not_found')
            decision=Decision(id=uuid4(),observation_id=identifier,resource_id=resource.id,actor_id=identity.actor_id,mode=mode,decided_at=now())
            session.add(decision)
            record_audit_event(session,actor_type=identity.actor_type,actor_id=identity.actor_id,action='discovery.candidate.decided',
                entity_type='discovery.observation',entity_id=identifier,outcome='success',
                changes={'mode':mode,'resource_id':str(resource.id),'confirm_distinct':payload.get('confirm_distinct',False)})
            session.flush()
            return dict(resource=serialize_resource(resource),already_decided=False)
