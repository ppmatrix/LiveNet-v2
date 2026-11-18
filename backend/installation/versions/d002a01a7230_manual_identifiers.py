"""Additive INV-ID-01 constraints; refuse incompatible legacy data unchanged."""
from alembic import op
import sqlalchemy as sa
from installation import STANDARD_ATTR, require
from installation.runner import StandardScope
from app.inventory.identifiers import legacy_preflight
from app.inventory.identifier_contract import NAMESPACE_CHECK, OPEN_PREDICATE

revision = 'd002a01a7230'
down_revision = 'd001a01a7230'
branch_labels = None
depends_on = None


def upgrade():
    scope = op.get_context().config.attributes.get(STANDARD_ATTR)
    require(type(scope) is StandardScope, 'STANDARD_CONTEXT_REQUIRED')
    scope.require('inventory', op.get_bind())
    # Prevent concurrent legacy writers between SELECT preflight and DDL.
    op.execute('LOCK TABLE inventory.resource_identifiers IN SHARE ROW EXCLUSIVE MODE')
    counts = legacy_preflight(op.get_bind())
    require(not any(counts.values()), 'INV_ID_01_LEGACY_DATA_INCOMPATIBLE')
    op.create_check_constraint('ck_identifiers_manual_ipv4_namespace', 'resource_identifiers', NAMESPACE_CHECK, schema='inventory')
    op.create_index('uq_identifiers_manual_ipv4_open', 'resource_identifiers',
        ['resource_id','namespace','normalized_value'], unique=True, schema='inventory', postgresql_where=sa.text(OPEN_PREDICATE))


def downgrade():
    raise RuntimeError('No automatic identifier downgrade; preserve history and reconcile explicitly')
