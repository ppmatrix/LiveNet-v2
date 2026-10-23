"""M1.2B-P1 preparation only: no connections, SQL or migration execution.

Target configuration and supplied observations are NOT execution authorization.
P2 must collect observations on the validated connection and implement the
transaction, locking, physical inspection and operational approval separately.
"""

import ast
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
import re

from alembic.config import Config

from security_migrations.contract import (
    INITIAL_REVISION, TABLE_NAMES, VERSION_SCHEMA, VERSION_TABLE, validate_configuration,
)


ROOT = Path(__file__).resolve().parents[2]
PROJECT = "livenetv2-m12b-test"
DATABASE = "livenet_m12b_test"
BASELINE = "f066a01a7230"
FORBIDDEN_DATABASES = frozenset({"livenet", "livenet_f0_test", "livenet_auth03_test"})
BASELINE_TABLES = frozenset(
    {("inventory", name) for name in (
        "resources", "resource_identifiers", "resource_relations", "groups", "group_memberships",
        "group_rules", "tags", "resource_tags", "policies", "policy_versions",
        "policy_assignments", "effective_configs",
    )} | {("audit", "events"), ("public", "alembic_version")}
)


class Refused(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Refused(message)


@dataclass(frozen=True)
class Target:
    project: str
    database: str
    host: str
    port: int
    system_identifier: str
    migration_user: str
    application_user: str


@dataclass(frozen=True)
class PreparationPlan:
    target: Target
    application_revision: str
    source: None
    destination: str
    version_table: str
    version_schema: str
    required_search_path: tuple[str, ...]
    sources: tuple[tuple[str, str], ...]
    digest: str


@dataclass(frozen=True)
class ObservedState:
    """P2 inspection interface. P1 only validates supplied deterministic data."""

    database: str
    system_identifier: str
    current_user: str
    session_user: str
    server_version_num: int
    application_revisions: tuple[str, ...]
    security_revisions: tuple[str, ...]
    schemas: frozenset[str]
    relations: frozenset[tuple[str, str]]


def validate_target(config):
    keys = {"project", "database", "host", "port", "system_identifier", "migration_user", "application_user"}
    require(isinstance(config, dict) and set(config) == keys, "Configuracao de destino incompleta ou desconhecida")
    require(all(isinstance(config[k], str) for k in keys - {"port"}), "Tipos de configuracao invalidos")
    require(config["database"] not in FORBIDDEN_DATABASES, "Destino proibido")
    require(config["project"] == PROJECT and config["database"] == DATABASE,
            "Identidade de teste M1.2B obrigatoria")
    require(config["host"] == "db" and type(config["port"]) is int and config["port"] == 5432,
            "Endpoint de teste inesperado")
    identifier = config["system_identifier"]
    require(isinstance(identifier, str) and re.fullmatch(r"[1-9][0-9]{0,19}", identifier)
            and int(identifier) <= 2**64 - 1,
            "Identificador PostgreSQL explicito obrigatorio")
    require(config["migration_user"] == "livenet_m12b_migrator"
            and config["application_user"] == "livenet_m12b_app", "Identidades separadas obrigatorias")
    return Target(**config)


def validate_security_graph(sources):
    # Parse revision declarations without importing/executing migration modules.
    require(len(sources) == 1, "P1 exige uma unica revisao security")
    fields = {}
    for node in ast.parse(sources[0]).body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name) and target.id in {"revision", "down_revision", "branch_labels", "depends_on"}:
                    require(target.id not in fields, "Declaracao de revisao duplicada")
                    fields[target.id] = ast.literal_eval(node.value)
    require(fields == {"revision": INITIAL_REVISION, "down_revision": None,
                       "branch_labels": None, "depends_on": None}, "Grafo security nao independente")


def security_configuration():
    config = Config(str(ROOT / "backend/alembic-security.ini"))
    validate_configuration(config)
    files = sorted((ROOT / "backend/security_migrations/versions").glob("*.py"))
    validate_security_graph([path.read_text() for path in files])
    return config


def prepare_plan(config, *, confirmed_baseline=None):
    target = validate_target(config)
    require(confirmed_baseline == BASELINE, "Confirmacao explicita de f066 obrigatoria")
    security_configuration()
    paths = [ROOT / "backend/alembic-security.ini", ROOT / "backend/app/security/models.py",
             Path(__file__).resolve(), *sorted((ROOT / "backend/security_migrations").rglob("*.py"))]
    require(all(not p.is_symlink() and p.is_file() for p in paths), "Fonte de preparacao irregular")
    sources = tuple((str(p.relative_to(ROOT)), sha256(p.read_bytes()).hexdigest()) for p in paths)
    content = {"target": asdict(target), "application_revision": BASELINE,
               "source": None, "destination": INITIAL_REVISION,
               "version_table": VERSION_TABLE, "version_schema": VERSION_SCHEMA,
               "required_search_path": ("pg_catalog", "public"), "sources": sources}
    digest = sha256(json.dumps(content, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return PreparationPlan(**{**content, "target": target}, digest=digest)


def validate_observation(plan, observed, *, phase):
    """Pure pre/post identity/version/inventory checks. Not a live inspection."""
    require(isinstance(plan, PreparationPlan) and isinstance(observed, ObservedState), "Contrato de observacao invalido")
    require(phase in {"before", "after"}, "Fase desconhecida")
    target = plan.target
    require((observed.database, observed.system_identifier, observed.current_user, observed.session_user)
            == (target.database, target.system_identifier, target.migration_user, target.migration_user),
            "Identidade da sessao inesperada")
    require(type(observed.server_version_num) is int and 160000 <= observed.server_version_num < 170000,
            "PostgreSQL 16 obrigatorio")
    require(observed.application_revisions == (BASELINE,), "Baseline divergente ou AUTH-03 presente")
    schemas = {"public", "inventory", "audit"}
    tables = set(BASELINE_TABLES)
    revisions = ()
    if phase == "after":
        schemas.add("security")
        tables |= {("security", name) for name in TABLE_NAMES} | {(VERSION_SCHEMA, VERSION_TABLE)}
        revisions = (INITIAL_REVISION,)
    require(observed.security_revisions == revisions, "Revisao security inesperada")
    require(observed.schemas == schemas and observed.relations == tables, "Inventario de origem/destino inesperado")
    return observed


def execution_contract(plan):
    require(isinstance(plan, PreparationPlan), "Plano de preparacao obrigatorio")
    return {"execution_enabled": False, "outer_transaction_required": True,
            "same_connection_required": True, "advisory_lock_required": True,
            "verify_before_and_after": True, "explicit_commit_after_physical_validation": True,
            "automatic_retry": False, "operational_approval_required": True,
            "uncertain_commit_requires_reconciliation": True,
            "application_credentials_are_authorization": False}


def execute_security_migration(*args, **kwargs):
    raise Refused("Execucao bloqueada em M1.2B-P1; integracao PostgreSQL exige M1.2B-P2 autorizada")


if __name__ == "__main__":
    raise SystemExit("M1.2B-P1 apenas prepara contratos; nao existe CLI operacional")
