"""Standard-only Discovery persistence; branches from f066, never AUTH-03 f067."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg
from installation import STANDARD_ATTR,require
from installation.runner import StandardScope

revision='d001a01a7230'
down_revision='f066a01a7230'
branch_labels=None
depends_on=None


def upgrade():
    scope=op.get_context().config.attributes.get(STANDARD_ATTR)
    require(type(scope) is StandardScope,'STANDARD_CONTEXT_REQUIRED')
    scope.require('discovery',op.get_bind())
    op.create_table('jobs',
        sa.Column('id',pg.UUID(as_uuid=True),primary_key=True),sa.Column('actor_id',pg.UUID(as_uuid=True),nullable=False),
        sa.Column('target',sa.String(80),nullable=False),sa.Column('policy',pg.JSONB(),nullable=False),
        sa.Column('status',sa.String(24),nullable=False),sa.Column('total',sa.Integer(),nullable=False),sa.Column('processed',sa.Integer(),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),sa.Column('finished_at',sa.DateTime(timezone=True)),
        sa.CheckConstraint("status IN ('queued','running','cancelling','cancelled','completed','interrupted','failed','timed_out')",name='ck_discovery_job_status'),
        sa.CheckConstraint('processed >= 0 AND processed <= total AND total > 0',name='ck_discovery_job_progress'),schema='discovery')
    op.create_index('ix_discovery_jobs_status','jobs',['status','created_at'],schema='discovery')
    op.create_table('observations',
        sa.Column('id',pg.UUID(as_uuid=True),primary_key=True),sa.Column('job_id',pg.UUID(as_uuid=True),sa.ForeignKey('discovery.jobs.id'),nullable=False),
        sa.Column('ip',sa.String(15),nullable=False),sa.Column('outcome',sa.String(24),nullable=False),
        sa.Column('observed_at',sa.DateTime(timezone=True),nullable=False),sa.Column('source_type',sa.String(32),nullable=False),
        sa.Column('source_instance',sa.String(64),nullable=False),sa.Column('evidence',pg.JSONB(),nullable=False),
        sa.UniqueConstraint('job_id','ip',name='uq_discovery_observation_job_ip'),
        sa.CheckConstraint("outcome IN ('responded','no_response','error')",name='ck_discovery_observation_outcome'),schema='discovery')
    op.create_index('ix_discovery_observations_ip','observations',['ip','observed_at'],schema='discovery')
    op.create_table('decisions',
        sa.Column('id',pg.UUID(as_uuid=True),primary_key=True),
        sa.Column('observation_id',pg.UUID(as_uuid=True),sa.ForeignKey('discovery.observations.id'),nullable=False),
        sa.Column('resource_id',pg.UUID(as_uuid=True),sa.ForeignKey('inventory.resources.id'),nullable=False),
        sa.Column('actor_id',pg.UUID(as_uuid=True),nullable=False),sa.Column('mode',sa.String(16),nullable=False),
        sa.Column('decided_at',sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint('observation_id',name='uq_discovery_decision_observation'),
        sa.CheckConstraint("mode IN ('create','associate')",name='ck_discovery_decision_mode'),schema='discovery')
    op.execute("""CREATE FUNCTION discovery.prevent_evidence_mutation() RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER AS $$
      BEGIN RAISE EXCEPTION 'Discovery evidence and decisions are immutable'; END; $$""")
    op.execute('REVOKE ALL ON FUNCTION discovery.prevent_evidence_mutation() FROM PUBLIC')
    for table in ('observations','decisions'):
        op.execute('CREATE TRIGGER trg_discovery_immutable BEFORE UPDATE OR DELETE ON discovery.'+table+
            ' FOR EACH ROW EXECUTE FUNCTION discovery.prevent_evidence_mutation()')


def downgrade():
    raise RuntimeError('No destructive Discovery downgrade; reconcile and authorize recovery explicitly')
