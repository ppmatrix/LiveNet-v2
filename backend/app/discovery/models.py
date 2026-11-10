"""Observations and immutable manual decisions, separate from Inventory."""
from sqlalchemy import Column,Table,String,Integer,DateTime,ForeignKey,UniqueConstraint,CheckConstraint,JSON
from sqlalchemy.dialects.postgresql import UUID,JSONB
from app.core.models import Base

json_type=JSON().with_variant(JSONB(),'postgresql')


class Job(Base):
    __table__=Table('jobs',Base.metadata,
        Column('id',UUID(as_uuid=True),primary_key=True),Column('actor_id',UUID(as_uuid=True),nullable=False),
        Column('target',String(80),nullable=False),Column('policy',json_type,nullable=False),
        Column('status',String(24),nullable=False),Column('total',Integer,nullable=False),Column('processed',Integer,nullable=False),
        Column('created_at',DateTime(timezone=True),nullable=False),Column('finished_at',DateTime(timezone=True)),
        CheckConstraint("status IN ('queued','running','cancelling','cancelled','completed','interrupted','failed','timed_out')",name='ck_discovery_job_status'),
        CheckConstraint('processed >= 0 AND processed <= total AND total > 0',name='ck_discovery_job_progress'),schema='discovery')


class Observation(Base):
    __table__=Table('observations',Base.metadata,
        Column('id',UUID(as_uuid=True),primary_key=True),Column('job_id',UUID(as_uuid=True),ForeignKey('discovery.jobs.id'),nullable=False),
        Column('ip',String(15),nullable=False),Column('outcome',String(24),nullable=False),
        Column('observed_at',DateTime(timezone=True),nullable=False),Column('source_type',String(32),nullable=False),
        Column('source_instance',String(64),nullable=False),Column('evidence',json_type,nullable=False),
        UniqueConstraint('job_id','ip',name='uq_discovery_observation_job_ip'),
        CheckConstraint("outcome IN ('responded','no_response','error')",name='ck_discovery_observation_outcome'),schema='discovery')


class Decision(Base):
    __table__=Table('decisions',Base.metadata,
        Column('id',UUID(as_uuid=True),primary_key=True),
        Column('observation_id',UUID(as_uuid=True),ForeignKey('discovery.observations.id'),nullable=False,unique=True),
        Column('resource_id',UUID(as_uuid=True),ForeignKey('inventory.resources.id'),nullable=False),
        Column('actor_id',UUID(as_uuid=True),nullable=False),Column('mode',String(16),nullable=False),
        Column('decided_at',DateTime(timezone=True),nullable=False),
        CheckConstraint("mode IN ('create','associate')",name='ck_discovery_decision_mode'),schema='discovery')
