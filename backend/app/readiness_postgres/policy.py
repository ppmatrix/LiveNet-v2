"""Immutable D05 contract. Approval is a trusted provisioning input, not a DB fact."""
from dataclasses import dataclass
from hashlib import sha256
from ipaddress import ip_interface
import json
import re
from types import MappingProxyType

from .queries import CATALOG


class Unavailable(RuntimeError):
    """No driver details or supplied values may reach callers."""
    def __init__(self):
        super().__init__("Readiness unavailable")


COLUMNS = MappingProxyType({
    "security.local_users": ("id", "login", "password_hash", "status", "created_at", "updated_at"),
    "security.login_sessions": ("id", "token_hash", "user_id", "created_at", "last_activity_at", "expires_at", "revoked_at"),
    "security.global_role_grants": ("id", "user_id", "role", "scope_type", "scope_id", "created_at"),
    "security.login_throttles": ("bucket_hash", "window_started_at", "attempts"),
    "audit.events": ("id", "occurred_at", "actor_type", "actor_id", "action", "entity_type", "entity_id", "correlation_id", "request_id", "outcome", "changes", "context"),
    "inventory.resources": ("id", "resource_type", "display_name", "description", "administrative_state", "attributes", "created_at", "updated_at", "archived_at", "row_version"),
})
_select = set(COLUMNS) - {"audit.events"}
_insert = {"security.login_sessions", "security.login_throttles", "audit.events"}
_update = {"security.local_users": ("updated_at",),
           "security.login_sessions": ("last_activity_at", "revoked_at"),
           "security.login_throttles": ("window_started_at", "attempts")}
MATRIX = frozenset((table, col, priv) for table, cols in COLUMNS.items() for col in cols
    for priv in ("SELECT", "INSERT", "UPDATE")
    if (priv == "SELECT" and table in _select) or (priv == "INSERT" and table in _insert)
    or (priv == "UPDATE" and col in _update.get(table, ())))
INVENTORY_TABLES = frozenset(("resources", "resource_identifiers", "resource_relations", "groups",
    "group_memberships", "group_rules", "tags", "resource_tags", "policies", "policy_versions",
    "policy_assignments", "effective_configs"))
BUSINESS_TABLES = frozenset({*("inventory." + t for t in INVENTORY_TABLES),
    *(t for t in COLUMNS if not t.startswith("inventory.")),
    "public.alembic_version", "public.alembic_security_version"})
TABLE_PRIVS = ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER")


REQUIRED_FOREIGN_KEYS = MappingProxyType({
    "security.login_sessions": ((("user_id",), "security.local_users", ("id",)),),
    "security.global_role_grants": ((("user_id",), "security.local_users", ("id",)),),
    "inventory.resource_identifiers": ((("resource_id",), "inventory.resources", ("id",)),),
    "inventory.resource_relations": ((("source_resource_id",), "inventory.resources", ("id",)), (("target_resource_id",), "inventory.resources", ("id",))),
    "inventory.group_memberships": ((("group_id",), "inventory.groups", ("id",)), (("resource_id",), "inventory.resources", ("id",))),
    "inventory.group_rules": ((("group_id",), "inventory.groups", ("id",)),),
    "inventory.resource_tags": ((("resource_id",), "inventory.resources", ("id",)), (("tag_id",), "inventory.tags", ("id",))),
    "inventory.policy_versions": ((("policy_id",), "inventory.policies", ("id",)),),
    "inventory.policy_assignments": ((("group_id",), "inventory.groups", ("id",)), (("policy_version_id",), "inventory.policy_versions", ("id",)), (("resource_id",), "inventory.resources", ("id",))),
    "inventory.effective_configs": ((("resource_id",), "inventory.resources", ("id",)),),
})

COLUMN_PRIVS = ("SELECT", "INSERT", "UPDATE", "REFERENCES")

# Only catalog columns read by the templates, never subconninfo/rolpassword.
VERIFIER_COLUMNS = MappingProxyType({
    "pg_roles": "oid rolname rolcanlogin rolsuper rolcreatedb rolcreaterole rolreplication rolbypassrls",
    "pg_auth_members": "roleid member grantor admin_option inherit_option set_option",
    "pg_namespace": "oid nspname nspowner nspacl",
    "pg_class": "oid relname relnamespace relkind relowner relacl relpersistence relrowsecurity relforcerowsecurity",
    "pg_attribute": "attrelid attnum attname attisdropped attacl atttypid atttypmod attnotnull attidentity attgenerated",
    "pg_proc": "oid proname pronamespace prokind proowner prosecdef prolang proconfig proacl",
    "pg_database": "oid datname datdba datacl",
    "pg_shdepend": "classid objid objsubid refobjid refclassid deptype",
    "pg_parameter_acl": "oid parname paracl",
    "pg_default_acl": "oid defaclrole defaclnamespace defaclobjtype defaclacl",
    "pg_attrdef": "adrelid adnum adbin",
    "pg_constraint": "oid conrelid conname convalidated contype conindid conkey confrelid confkey",
    "pg_index": "indexrelid indrelid indisvalid indisready indisunique indisprimary indkey",
    "pg_trigger": "oid tgrelid tgfoid tgenabled tgisinternal tgname tgconstraint",
    "pg_rewrite": "oid ev_class rulename ev_type is_instead ev_enabled",
    "pg_policy": "oid polrelid polname polcmd polpermissive polroles polqual polwithcheck",
    "pg_type": "oid typowner typacl",
    "pg_extension": "oid extowner",
    "pg_language": "oid lanname lanowner lanacl",
    "pg_foreign_data_wrapper": "oid fdwowner fdwacl",
    "pg_foreign_server": "oid srvowner srvacl",
    "pg_tablespace": "oid spcowner spcacl",
    "pg_largeobject_metadata": "oid lomowner lomacl",
    "pg_event_trigger": "oid evtowner",
    "pg_publication": "oid pubowner",
    "pg_subscription": "oid subowner",
    "pg_conversion": "oid conowner",
    "pg_collation": "oid collowner",
    "pg_opclass": "oid opcowner",
    "pg_operator": "oid oprowner",
    "pg_opfamily": "oid opfowner",
    "pg_ts_config": "oid cfgowner",
    "pg_ts_dict": "oid dictowner",
    "pg_statistic_ext": "oid stxowner",
})


# Minimum declarations reviewed against f066/b12 source; NOT observed evidence.
# columns, constraint kind counts, explicitly named constraints, explicit indexes.
REQUIRED_STRUCTURE = MappingProxyType({
    "audit.events": (
        ("id", "occurred_at", "actor_type", "actor_id", "action", "entity_type", "entity_id", "correlation_id", "request_id", "outcome", "changes", "context"),
        (("c", 6), ("f", 0), ("p", 1), ("u", 0), ("x", 0)),
        (("audit_events_pkey", "p"), ("ck_audit_events_action_not_empty", "c"), ("ck_audit_events_actor_type_not_empty", "c"), ("ck_audit_events_changes_object", "c"), ("ck_audit_events_context_object", "c"), ("ck_audit_events_entity_type_not_empty", "c"), ("ck_audit_events_outcome_not_empty", "c")),
        ("ix_audit_events_correlation", "ix_audit_events_entity", "ix_audit_events_occurred_at")),
    "inventory.effective_configs": (
        ("id", "resource_id", "policy_type", "resolved_config", "resolution_trace", "calculated_at", "revision"),
        (("c", 4), ("f", 1), ("p", 1), ("u", 1), ("x", 0)),
        (("ck_effective_configs_policy_type_not_empty", "c"), ("ck_effective_configs_resolution_trace_object", "c"), ("ck_effective_configs_resolved_config_object", "c"), ("ck_effective_configs_revision_positive", "c"), ("effective_configs_pkey", "p"), ("uq_effective_configs_resource_policy_type", "u")),
        ()),
    "inventory.group_memberships": (
        ("id", "group_id", "resource_id", "membership_source", "valid_from", "valid_until", "created_at"),
        (("c", 2), ("f", 2), ("p", 1), ("u", 0), ("x", 1)),
        (("ck_group_memberships_source", "c"), ("ck_group_memberships_validity", "c"), ("ex_group_memberships_no_overlap", "x")),
        ()),
    "inventory.group_rules": (
        ("id", "group_id", "rule_definition", "enabled", "created_at", "updated_at"),
        (("c", 2), ("f", 1), ("p", 1), ("u", 0), ("x", 0)),
        (("ck_group_rules_definition_object", "c"), ("ck_group_rules_timestamps", "c")),
        ()),
    "inventory.groups": (
        ("id", "name", "description", "group_type", "created_at", "updated_at", "archived_at"),
        (("c", 2), ("f", 0), ("p", 1), ("u", 0), ("x", 0)),
        (("ck_groups_timestamps", "c"), ("ck_groups_type", "c")),
        ("uq_groups_active_name",)),
    "inventory.policies": (
        ("id", "name", "policy_type", "description", "enabled", "created_at", "updated_at", "archived_at"),
        (("c", 4), ("f", 0), ("p", 1), ("u", 0), ("x", 0)),
        (("ck_policies_archived_at", "c"), ("ck_policies_name_not_empty", "c"), ("ck_policies_timestamps", "c"), ("ck_policies_type_normalized", "c")),
        ()),
    "inventory.policy_assignments": (
        ("id", "policy_version_id", "scope_type", "group_id", "resource_id", "priority", "valid_from", "valid_until", "created_at"),
        (("c", 2), ("f", 3), ("p", 1), ("u", 0), ("x", 3)),
        (("ck_policy_assignments_scope", "c"), ("ck_policy_assignments_validity", "c"), ("ex_policy_assignments_global_overlap", "x"), ("ex_policy_assignments_group_overlap", "x"), ("ex_policy_assignments_resource_overlap", "x")),
        ()),
    "inventory.policy_versions": (
        ("id", "policy_id", "version", "definition", "created_at", "created_by"),
        (("c", 2), ("f", 1), ("p", 1), ("u", 1), ("x", 0)),
        (("ck_policy_versions_definition_object", "c"), ("ck_policy_versions_version_positive", "c"), ("uq_policy_versions_policy_version", "u")),
        ()),
    "inventory.resource_identifiers": (
        ("id", "resource_id", "identifier_type", "identifier_value", "normalized_value", "namespace", "source_type", "source_instance", "first_seen_at", "last_seen_at", "verified_at", "verification_status", "confidence", "evidence", "valid_from", "valid_until", "created_at", "updated_at"),
        (("c", 4), ("f", 1), ("p", 1), ("u", 0), ("x", 0)),
        (("ck_resource_identifiers_confidence", "c"), ("ck_resource_identifiers_evidence_object", "c"), ("ck_resource_identifiers_seen_order", "c"), ("ck_resource_identifiers_validity", "c")),
        ("ix_resource_identifiers_lookup", "ix_resource_identifiers_resource_validity", "ix_resource_identifiers_source")),
    "inventory.resource_relations": (
        ("id", "source_resource_id", "target_resource_id", "relation_type", "source_type", "source_instance", "evidence", "valid_from", "valid_until", "created_at", "updated_at"),
        (("c", 4), ("f", 2), ("p", 1), ("u", 0), ("x", 0)),
        (("ck_resource_relations_evidence_object", "c"), ("ck_resource_relations_no_self", "c"), ("ck_resource_relations_timestamps", "c"), ("ck_resource_relations_validity", "c")),
        ("ix_resource_relations_source_type", "ix_resource_relations_target_type", "ix_resource_relations_type_validity")),
    "inventory.resource_tags": (
        ("id", "resource_id", "tag_id", "assignment_source", "valid_from", "valid_until", "created_at"),
        (("c", 2), ("f", 2), ("p", 1), ("u", 0), ("x", 1)),
        (("ck_resource_tags_source", "c"), ("ck_resource_tags_validity", "c"), ("ex_resource_tags_no_overlap", "x")),
        ("ix_resource_tags_resource_valid_until", "ix_resource_tags_tag_valid_until")),
    "inventory.resources": (
        ("id", "resource_type", "display_name", "description", "administrative_state", "attributes", "created_at", "updated_at", "archived_at", "row_version"),
        (("c", 4), ("f", 0), ("p", 1), ("u", 0), ("x", 0)),
        (("ck_resources_administrative_state", "c"), ("ck_resources_attributes_object", "c"), ("ck_resources_row_version", "c"), ("ck_resources_timestamps", "c")),
        ("ix_resources_type_state",)),
    "inventory.tags": (
        ("id", "key", "value", "description", "created_at", "updated_at"),
        (("c", 3), ("f", 0), ("p", 1), ("u", 1), ("x", 0)),
        (("ck_tags_key_normalized", "c"), ("ck_tags_timestamps", "c"), ("ck_tags_value_normalized", "c"), ("uq_tags_key_value", "u")),
        ()),
    "public.alembic_security_version": (
        ("version_num",),
        (("c", 0), ("f", 0), ("p", 1), ("u", 0), ("x", 0)),
        (),
        ()),
    "public.alembic_version": (
        ("version_num",),
        (("c", 0), ("f", 0), ("p", 1), ("u", 0), ("x", 0)),
        (),
        ()),
    "security.global_role_grants": (
        ("id", "user_id", "role", "scope_type", "scope_id", "created_at"),
        (("c", 2), ("f", 1), ("p", 1), ("u", 1), ("x", 0)),
        (("ck_global_role_grants_role", "c"), ("ck_global_role_grants_scope", "c"), ("fk_security_global_role_grants_user_id_local_users", "f"), ("pk_security_global_role_grants", "p"), ("uq_global_role_grants_user_role", "u")),
        ()),
    "security.local_users": (
        ("id", "login", "password_hash", "status", "created_at", "updated_at"),
        (("c", 3), ("f", 0), ("p", 1), ("u", 1), ("x", 0)),
        (("ck_local_users_login", "c"), ("ck_local_users_status", "c"), ("ck_local_users_timestamps", "c"), ("pk_security_local_users", "p"), ("uq_local_users_login", "u")),
        ()),
    "security.login_sessions": (
        ("id", "token_hash", "user_id", "created_at", "last_activity_at", "expires_at", "revoked_at"),
        (("c", 3), ("f", 1), ("p", 1), ("u", 1), ("x", 0)),
        (("ck_login_sessions_hash", "c"), ("ck_login_sessions_revoked", "c"), ("ck_login_sessions_times", "c"), ("fk_security_login_sessions_user_id_local_users", "f"), ("pk_security_login_sessions", "p"), ("uq_login_sessions_token_hash", "u")),
        ("ix_security_login_sessions_user_id",)),
    "security.login_throttles": (
        ("bucket_hash", "window_started_at", "attempts"),
        (("c", 1), ("f", 0), ("p", 1), ("u", 0), ("x", 0)),
        (("ck_login_throttles_attempts", "c"), ("pk_security_login_throttles", "p")),
        ()),
})



def freeze(value):
    """JSON scalars/arrays only; preserve bool/int distinction via canonical JSON."""
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) in (tuple, list):
        return tuple(freeze(v) for v in value)
    raise Unavailable()


def canonical(value):
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), allow_nan=False)


def normalize(rows, limit):
    if type(rows) not in (tuple, list) or len(rows) > limit:
        raise Unavailable()
    frozen = tuple(freeze(row) for row in rows)
    if any(type(row) is not tuple or not row for row in frozen):
        raise Unavailable()
    keys = tuple(canonical(row) for row in frozen)
    if len(set(keys)) != len(keys):
        raise Unavailable()
    return tuple(sorted(frozen, key=canonical))


def contract_digest(*, version, target, verifier_role, server_address, server_version,
                    system_identifier, manifest):
    """Pin identity and policy together. A hash is not an approval signature."""
    return sha256(canonical((version, target, verifier_role, server_address,
                            server_version, system_identifier, manifest)).encode()).hexdigest()


@dataclass(frozen=True)
class Policy:
    version: str
    target: tuple
    verifier_role: str
    server_address: str
    server_version: str
    system_identifier: str
    manifest: tuple  # (Q2..Q16 except Q15, ordered immutable normalized rows)
    approved_digest: str

    def __post_init__(self):
        try:
            if (self.version != "D05-G2-FIX1-v2" or type(self.target) is not tuple or len(self.target) != 4
                    or any(type(self.target[i]) is not str or not self.target[i] for i in (0, 2, 3))
                    or type(self.target[1]) is not int or not 1 <= self.target[1] <= 65535
                    or type(self.verifier_role) is not str or not self.verifier_role
                    or self.verifier_role == self.target[3]
                    or not all(re.fullmatch(r"[A-Za-z0-9_.:-]+", v)
                               for v in (*self.target[::2], self.target[3], self.verifier_role))
                    or type(self.server_version) is not str or not self.server_version.isdecimal()
                    or not 160000 <= int(self.server_version) < 170000
                    or type(self.system_identifier) is not str or not self.system_identifier.isdecimal()
                    or str(ip_interface(self.server_address).ip) != self.server_address
                    or "%" in self.server_address
                    or type(self.manifest) is not tuple
                    or freeze(self.manifest) != self.manifest
                    or contract_digest(version=self.version, target=self.target,
                        verifier_role=self.verifier_role, server_address=self.server_address,
                        server_version=self.server_version, system_identifier=self.system_identifier,
                        manifest=self.manifest) != self.approved_digest):
                raise Unavailable()
            expected = {f"Q{i}" for i in range(2, 17)} - {"Q15"}
            if len(self.manifest) != len(expected) or {q for q, _ in self.manifest} != expected:
                raise Unavailable()
            for q, rows in self.manifest:
                if type(rows) is not tuple or normalize(rows, CATALOG[q].max_rows) != rows:
                    raise Unavailable()
            # A digest never overrides the privilege contract.
            from .evaluate import validate_contract
            validate_contract(self, dict(self.manifest))
        except Exception:
            raise Unavailable() from None


@dataclass(frozen=True)
class Limits:
    connect_seconds: float = 2.0
    statement_ms: int = 500
    heavy_statement_ms: int = 1000
    lock_ms: int = 200
    idle_transaction_ms: int = 1000
    global_seconds: float = 4.0
    max_bytes: int = 32 * 1024 * 1024

    def __post_init__(self):
        ceilings = (2, 500, 1000, 200, 1000, 4, 32 * 1024 * 1024)
        for index, (value, ceiling) in enumerate(zip(self.__dict__.values(), ceilings)):
            types = (int, float) if index in (0, 5) else (int,)
            if type(value) not in types or not 0 < value <= ceiling:
                raise Unavailable()
