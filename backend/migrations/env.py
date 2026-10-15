from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool

from app.core.database import get_database_url

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Os modelos serão registados nesta metadata
# depois da validação dos contratos de dados.
target_metadata = None


def run_migrations_offline():
    context.configure(
        url=get_database_url().render_as_string(
            hide_password=False
        ),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    from sqlalchemy import create_engine

    engine = create_engine(
        get_database_url(),
        poolclass=pool.NullPool,
    )

    try:
        with engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
            )

            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
