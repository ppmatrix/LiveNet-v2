"""Security-only metadata and Alembic contract, without database access."""

from pathlib import Path

from sqlalchemy import MetaData

from app.security.models import GlobalRoleGrant, LocalUser, LoginSession, LoginThrottle


INITIAL_REVISION = "b12b01a7230"
VERSION_TABLE = "alembic_security_version"
VERSION_SCHEMA = "public"
TABLE_NAMES = frozenset({"local_users", "login_sessions", "global_role_grants", "login_throttles"})
SCRIPT_LOCATION = Path(__file__).resolve().parent


def security_metadata():
    # Copy rather than mutate Base.metadata, which may contain other domains.
    metadata = MetaData()
    for model in (LocalUser, LoginSession, GlobalRoleGrant, LoginThrottle):
        model.__table__.to_metadata(metadata)
    return metadata


def include_name(name, type_, parent_names):
    if type_ == "schema":
        return name == "security"
    if parent_names.get("schema_name") != "security":
        return False
    if type_ == "table":
        return name in TABLE_NAMES
    return parent_names.get("table_name") in TABLE_NAMES


def include_object(obj, name, type_, reflected, compare_to):
    table = obj if type_ == "table" else getattr(obj, "table", None)
    return (table is not None and table.schema == "security"
            and table.name in TABLE_NAMES)


def validate_configuration(config):
    location = config.get_main_option("script_location")
    if (not location or Path(location).resolve() != SCRIPT_LOCATION
            or config.get_main_option("version_table") != VERSION_TABLE
            or config.get_main_option("version_table_schema") != VERSION_SCHEMA
            or config.get_main_option("version_locations")
            or config.get_main_option("recursive_version_locations", "false").lower() != "false"
            or config.get_main_option("sqlalchemy.url")):
        raise RuntimeError("Configuracao Alembic security nao independente")


def configure_context(environment, config, connection):
    validate_configuration(config)
    if (connection is None or connection.in_transaction() is not True
            or connection.dialect.name != "postgresql"):
        raise RuntimeError("Security exige ligacao PostgreSQL externa e transacao explicita")
    environment.configure(
        connection=connection, target_metadata=security_metadata(),
        version_table=VERSION_TABLE, version_table_schema=VERSION_SCHEMA,
        include_schemas=True, include_name=include_name, include_object=include_object,
        transactional_ddl=True, transaction_per_migration=False,
        compare_type=True, compare_server_default=True,
    )
