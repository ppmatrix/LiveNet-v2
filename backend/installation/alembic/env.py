"""Only the explicitly selected standard MVP runner may use this environment."""
from alembic import context
from installation import STANDARD_ATTR, require
from installation.runner import StandardScope

config = context.config
scope = config.attributes.get(STANDARD_ATTR)
require(type(scope) is StandardScope, 'STANDARD_CONTEXT_REQUIRED')
require(not context.is_offline_mode(), 'EXPLICIT_CONNECTION_REQUIRED')
require('dev09b_prepared_context' not in config.attributes, 'MIXED_INSTALLATION_PATHS')
scope.assert_bound(config.attributes.get('connection'))
require(config.attributes.get('standard_chain') == scope.chain, 'CHAIN_BINDING')
context.configure(connection=scope.connection, target_metadata=None,
    version_table=scope.ledger, version_table_schema='public', transactional_ddl=True,
    transaction_per_migration=False)
with context.begin_transaction():
    context.run_migrations()
