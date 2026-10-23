"""External-connection-only environment. P1 coordinator never invokes this.

No engine, database URL, secret reading, logging config or application fallback.
An executor must supply the validated target connection in an outer transaction.
"""

from alembic import context

from security_migrations.contract import configure_context


config = context.config
if context.is_offline_mode():
    raise RuntimeError("Security exige ligacao externa; modo SQL offline nao permitido")

connection = config.attributes.get("connection")
configure_context(context, config, connection)

with context.begin_transaction():
    context.run_migrations()
