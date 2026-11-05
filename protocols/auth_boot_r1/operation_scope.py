"""R1-PROTO-04: advisory lab-scope classifier, never an authorization gate.

Facts are synthetic/review inputs, NOT attested PostgreSQL metadata. This module
does not parse SQL, consult catalogs, prove time/revocation or execute anything.
Even a LAB_CANDIDATE remains operationally unsupported under current R1 gates.
"""

from dataclasses import dataclass
from enum import Enum


class OperationClass(str, Enum):
    READ_ONLY = "READ_ONLY"
    DML = "DML"
    DDL = "DDL"
    ALEMBIC = "ALEMBIC"
    ARBITRARY_SQL = "ARBITRARY_SQL"
    NON_TRANSACTIONAL = "NON_TRANSACTIONAL"


CANDIDATE_OPERATION = "lab.single_row_compare_and_set.v1"


@dataclass(frozen=True)
class LabFacts:
    operation_id: str
    operation_class: OperationClass
    statement_count: int | None = None
    fixed_update_only: bool | None = None
    primary_key_and_version_predicate: bool | None = None
    preexisting_local_logged_table: bool | None = None
    no_triggers_rules_or_generated_columns: bool | None = None
    no_defaults_sequences_or_user_functions: bool | None = None
    no_foreign_keys_cascades_or_rls: bool | None = None
    no_partitions_inheritance_or_foreign_tables: bool | None = None
    fixed_typed_parameters_no_client_sql: bool | None = None
    exclusive_entrypoint_no_direct_dml: bool | None = None


@dataclass(frozen=True)
class Assessment:
    classification: str
    reasons: tuple[str, ...]

    @property
    def operationally_supported(self):
        return False


def assess_lab_candidate(facts: LabFacts) -> Assessment:
    """Unknown facts fail closed for *lab selection*, not security enforcement."""
    if type(facts) is not LabFacts:
        return Assessment("EXCLUDED", ("UNKNOWN_FACTS",))
    reasons = []
    if facts.operation_id != CANDIDATE_OPERATION:
        reasons.append("OPERATION_NOT_IN_LAB_ALLOWLIST")
    if facts.operation_class is not OperationClass.DML:
        reasons.append("CLASS_NOT_SINGLE_ROW_DML")
    if type(facts.statement_count) is not int or facts.statement_count != 1:
        reasons.append("STATEMENT_COUNT_NOT_ONE")
    for name in LabFacts.__dataclass_fields__:
        if name in {"operation_id", "operation_class", "statement_count"}:
            continue
        if getattr(facts, name) is not True:
            reasons.append(name.upper())
    return Assessment("EXCLUDED" if reasons else "LAB_CANDIDATE", tuple(reasons))
