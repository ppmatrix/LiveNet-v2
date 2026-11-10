"""Persistent observations and explicit, one-shot manual decisions."""
from contextlib import contextmanager
from datetime import datetime,timezone
from uuid import uuid4
from sqlalchemy import select,func,or_,text
from app.inventory import service as inventory
from app.inventory.models import Resource,ResourceIdentifier
from app.inventory.schemas import serialize_resource,validate_creation
from app.audit.service import record_audit_event
from .models import Job,Observation,Decision

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

    def enqueue(self,policy,target,identity):
        addresses=policy.targets(target)
        with self.transaction(ADMISSION_KEY) as session:
            active=session.scalar(select(func.count()).select_from(Job).where(Job.status.in_(ACTIVE)))
            if active>=policy.max_jobs:raise Problem(409,'discovery_busy')
            job=Job(id=uuid4(),actor_id=identity.actor_id,target=target.strip(),policy=policy.snapshot(),status='queued',
                total=len(addresses),processed=0,created_at=now(),finished_at=None)
            session.add(job)
            record_audit_event(session,actor_type=identity.actor_type,actor_id=identity.actor_id,action='discovery.job.started',
                entity_type='discovery.job',entity_id=job.id,outcome='success',changes={'target':job.target,'total':job.total,'policy':job.policy})
            session.flush()
            return self.job_public(job)

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
