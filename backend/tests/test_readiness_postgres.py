"""G2 synthetic catalog evidence only. No sockets, drivers, DDL or real secrets."""
from dataclasses import FrozenInstanceError, replace
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from unittest.mock import Mock
import ast
import socket
import uuid

import pytest

from app.readiness import ReadinessObservation, _privileges_valid
from app.readiness_postgres.adapter import (Batch, DisabledPostgresExecutor,
                                           OfflineExecutor, OfflineReadinessAdapter)
from app.readiness_postgres.evaluate import identity
from app.readiness_postgres.policy import (BUSINESS_TABLES, COLUMNS, COLUMN_PRIVS,
    MATRIX, TABLE_PRIVS, Limits, Policy, Unavailable, contract_digest, normalize)
from app.readiness_postgres.queries import CATALOG


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Network access forbidden in G2")
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)


# Literal oracle captured from reviewed migration/model declarations, not imported
# from the policy under test. Synthetic definitions/OIDs are NOT a real manifest.
LITERAL_STRUCTURE = {
  "audit.events": {
    "columns": [
      "id",
      "occurred_at",
      "actor_type",
      "actor_id",
      "action",
      "entity_type",
      "entity_id",
      "correlation_id",
      "request_id",
      "outcome",
      "changes",
      "context"
    ],
    "counts": {
      "c": 6,
      "f": 0,
      "p": 1,
      "u": 0,
      "x": 0
    },
    "indexes": [
      "ix_audit_events_entity",
      "ix_audit_events_occurred_at",
      "ix_audit_events_correlation"
    ],
    "names": [
      [
        "audit_events_pkey",
        "p"
      ],
      [
        "ck_audit_events_actor_type_not_empty",
        "c"
      ],
      [
        "ck_audit_events_action_not_empty",
        "c"
      ],
      [
        "ck_audit_events_entity_type_not_empty",
        "c"
      ],
      [
        "ck_audit_events_outcome_not_empty",
        "c"
      ],
      [
        "ck_audit_events_changes_object",
        "c"
      ],
      [
        "ck_audit_events_context_object",
        "c"
      ]
    ]
  },
  "inventory.effective_configs": {
    "columns": [
      "id",
      "resource_id",
      "policy_type",
      "resolved_config",
      "resolution_trace",
      "calculated_at",
      "revision"
    ],
    "counts": {
      "c": 4,
      "f": 1,
      "p": 1,
      "u": 1,
      "x": 0
    },
    "indexes": [],
    "names": [
      [
        "effective_configs_pkey",
        "p"
      ],
      [
        "uq_effective_configs_resource_policy_type",
        "u"
      ],
      [
        "ck_effective_configs_policy_type_not_empty",
        "c"
      ],
      [
        "ck_effective_configs_resolved_config_object",
        "c"
      ],
      [
        "ck_effective_configs_resolution_trace_object",
        "c"
      ],
      [
        "ck_effective_configs_revision_positive",
        "c"
      ]
    ]
  },
  "inventory.group_memberships": {
    "columns": [
      "id",
      "group_id",
      "resource_id",
      "membership_source",
      "valid_from",
      "valid_until",
      "created_at"
    ],
    "counts": {
      "c": 2,
      "f": 2,
      "p": 1,
      "u": 0,
      "x": 1
    },
    "indexes": [],
    "names": [
      [
        "ck_group_memberships_source",
        "c"
      ],
      [
        "ck_group_memberships_validity",
        "c"
      ],
      [
        "ex_group_memberships_no_overlap",
        "x"
      ]
    ]
  },
  "inventory.group_rules": {
    "columns": [
      "id",
      "group_id",
      "rule_definition",
      "enabled",
      "created_at",
      "updated_at"
    ],
    "counts": {
      "c": 2,
      "f": 1,
      "p": 1,
      "u": 0,
      "x": 0
    },
    "indexes": [],
    "names": [
      [
        "ck_group_rules_definition_object",
        "c"
      ],
      [
        "ck_group_rules_timestamps",
        "c"
      ]
    ]
  },
  "inventory.groups": {
    "columns": [
      "id",
      "name",
      "description",
      "group_type",
      "created_at",
      "updated_at",
      "archived_at"
    ],
    "counts": {
      "c": 2,
      "f": 0,
      "p": 1,
      "u": 0,
      "x": 0
    },
    "indexes": [
      "uq_groups_active_name"
    ],
    "names": [
      [
        "ck_groups_type",
        "c"
      ],
      [
        "ck_groups_timestamps",
        "c"
      ]
    ]
  },
  "inventory.policies": {
    "columns": [
      "id",
      "name",
      "policy_type",
      "description",
      "enabled",
      "created_at",
      "updated_at",
      "archived_at"
    ],
    "counts": {
      "c": 4,
      "f": 0,
      "p": 1,
      "u": 0,
      "x": 0
    },
    "indexes": [],
    "names": [
      [
        "ck_policies_name_not_empty",
        "c"
      ],
      [
        "ck_policies_type_normalized",
        "c"
      ],
      [
        "ck_policies_timestamps",
        "c"
      ],
      [
        "ck_policies_archived_at",
        "c"
      ]
    ]
  },
  "inventory.policy_assignments": {
    "columns": [
      "id",
      "policy_version_id",
      "scope_type",
      "group_id",
      "resource_id",
      "priority",
      "valid_from",
      "valid_until",
      "created_at"
    ],
    "counts": {
      "c": 2,
      "f": 3,
      "p": 1,
      "u": 0,
      "x": 3
    },
    "indexes": [],
    "names": [
      [
        "ck_policy_assignments_scope",
        "c"
      ],
      [
        "ck_policy_assignments_validity",
        "c"
      ],
      [
        "ex_policy_assignments_global_overlap",
        "x"
      ],
      [
        "ex_policy_assignments_group_overlap",
        "x"
      ],
      [
        "ex_policy_assignments_resource_overlap",
        "x"
      ]
    ]
  },
  "inventory.policy_versions": {
    "columns": [
      "id",
      "policy_id",
      "version",
      "definition",
      "created_at",
      "created_by"
    ],
    "counts": {
      "c": 2,
      "f": 1,
      "p": 1,
      "u": 1,
      "x": 0
    },
    "indexes": [],
    "names": [
      [
        "ck_policy_versions_version_positive",
        "c"
      ],
      [
        "ck_policy_versions_definition_object",
        "c"
      ],
      [
        "uq_policy_versions_policy_version",
        "u"
      ]
    ]
  },
  "inventory.resource_identifiers": {
    "columns": [
      "id",
      "resource_id",
      "identifier_type",
      "identifier_value",
      "normalized_value",
      "namespace",
      "source_type",
      "source_instance",
      "first_seen_at",
      "last_seen_at",
      "verified_at",
      "verification_status",
      "confidence",
      "evidence",
      "valid_from",
      "valid_until",
      "created_at",
      "updated_at"
    ],
    "counts": {
      "c": 4,
      "f": 1,
      "p": 1,
      "u": 0,
      "x": 0
    },
    "indexes": [
      "ix_resource_identifiers_lookup",
      "ix_resource_identifiers_resource_validity",
      "ix_resource_identifiers_source"
    ],
    "names": [
      [
        "ck_resource_identifiers_seen_order",
        "c"
      ],
      [
        "ck_resource_identifiers_validity",
        "c"
      ],
      [
        "ck_resource_identifiers_evidence_object",
        "c"
      ],
      [
        "ck_resource_identifiers_confidence",
        "c"
      ]
    ]
  },
  "inventory.resource_relations": {
    "columns": [
      "id",
      "source_resource_id",
      "target_resource_id",
      "relation_type",
      "source_type",
      "source_instance",
      "evidence",
      "valid_from",
      "valid_until",
      "created_at",
      "updated_at"
    ],
    "counts": {
      "c": 4,
      "f": 2,
      "p": 1,
      "u": 0,
      "x": 0
    },
    "indexes": [
      "ix_resource_relations_type_validity",
      "ix_resource_relations_source_type",
      "ix_resource_relations_target_type"
    ],
    "names": [
      [
        "ck_resource_relations_no_self",
        "c"
      ],
      [
        "ck_resource_relations_validity",
        "c"
      ],
      [
        "ck_resource_relations_evidence_object",
        "c"
      ],
      [
        "ck_resource_relations_timestamps",
        "c"
      ]
    ]
  },
  "inventory.resource_tags": {
    "columns": [
      "id",
      "resource_id",
      "tag_id",
      "assignment_source",
      "valid_from",
      "valid_until",
      "created_at"
    ],
    "counts": {
      "c": 2,
      "f": 2,
      "p": 1,
      "u": 0,
      "x": 1
    },
    "indexes": [
      "ix_resource_tags_tag_valid_until",
      "ix_resource_tags_resource_valid_until"
    ],
    "names": [
      [
        "ck_resource_tags_source",
        "c"
      ],
      [
        "ck_resource_tags_validity",
        "c"
      ],
      [
        "ex_resource_tags_no_overlap",
        "x"
      ]
    ]
  },
  "inventory.resources": {
    "columns": [
      "id",
      "resource_type",
      "display_name",
      "description",
      "administrative_state",
      "attributes",
      "created_at",
      "updated_at",
      "archived_at",
      "row_version"
    ],
    "counts": {
      "c": 4,
      "f": 0,
      "p": 1,
      "u": 0,
      "x": 0
    },
    "indexes": [
      "ix_resources_type_state"
    ],
    "names": [
      [
        "ck_resources_administrative_state",
        "c"
      ],
      [
        "ck_resources_attributes_object",
        "c"
      ],
      [
        "ck_resources_timestamps",
        "c"
      ],
      [
        "ck_resources_row_version",
        "c"
      ]
    ]
  },
  "inventory.tags": {
    "columns": [
      "id",
      "key",
      "value",
      "description",
      "created_at",
      "updated_at"
    ],
    "counts": {
      "c": 3,
      "f": 0,
      "p": 1,
      "u": 1,
      "x": 0
    },
    "indexes": [],
    "names": [
      [
        "ck_tags_key_normalized",
        "c"
      ],
      [
        "ck_tags_value_normalized",
        "c"
      ],
      [
        "ck_tags_timestamps",
        "c"
      ],
      [
        "uq_tags_key_value",
        "u"
      ]
    ]
  },
  "public.alembic_security_version": {
    "columns": [
      "version_num"
    ],
    "counts": {
      "c": 0,
      "f": 0,
      "p": 1,
      "u": 0,
      "x": 0
    },
    "indexes": [],
    "names": []
  },
  "public.alembic_version": {
    "columns": [
      "version_num"
    ],
    "counts": {
      "c": 0,
      "f": 0,
      "p": 1,
      "u": 0,
      "x": 0
    },
    "indexes": [],
    "names": []
  },
  "security.global_role_grants": {
    "columns": [
      "id",
      "user_id",
      "role",
      "scope_type",
      "scope_id",
      "created_at"
    ],
    "counts": {
      "c": 2,
      "f": 1,
      "p": 1,
      "u": 1,
      "x": 0
    },
    "indexes": [],
    "names": [
      [
        "pk_security_global_role_grants",
        "p"
      ],
      [
        "fk_security_global_role_grants_user_id_local_users",
        "f"
      ],
      [
        "uq_global_role_grants_user_role",
        "u"
      ],
      [
        "ck_global_role_grants_role",
        "c"
      ],
      [
        "ck_global_role_grants_scope",
        "c"
      ]
    ]
  },
  "security.local_users": {
    "columns": [
      "id",
      "login",
      "password_hash",
      "status",
      "created_at",
      "updated_at"
    ],
    "counts": {
      "c": 3,
      "f": 0,
      "p": 1,
      "u": 1,
      "x": 0
    },
    "indexes": [],
    "names": [
      [
        "pk_security_local_users",
        "p"
      ],
      [
        "uq_local_users_login",
        "u"
      ],
      [
        "ck_local_users_login",
        "c"
      ],
      [
        "ck_local_users_status",
        "c"
      ],
      [
        "ck_local_users_timestamps",
        "c"
      ]
    ]
  },
  "security.login_sessions": {
    "columns": [
      "id",
      "token_hash",
      "user_id",
      "created_at",
      "last_activity_at",
      "expires_at",
      "revoked_at"
    ],
    "counts": {
      "c": 3,
      "f": 1,
      "p": 1,
      "u": 1,
      "x": 0
    },
    "indexes": [
      "ix_security_login_sessions_user_id"
    ],
    "names": [
      [
        "pk_security_login_sessions",
        "p"
      ],
      [
        "fk_security_login_sessions_user_id_local_users",
        "f"
      ],
      [
        "uq_login_sessions_token_hash",
        "u"
      ],
      [
        "ck_login_sessions_hash",
        "c"
      ],
      [
        "ck_login_sessions_times",
        "c"
      ],
      [
        "ck_login_sessions_revoked",
        "c"
      ]
    ]
  },
  "security.login_throttles": {
    "columns": [
      "bucket_hash",
      "window_started_at",
      "attempts"
    ],
    "counts": {
      "c": 1,
      "f": 0,
      "p": 1,
      "u": 0,
      "x": 0
    },
    "indexes": [],
    "names": [
      [
        "pk_security_login_throttles",
        "p"
      ],
      [
        "ck_login_throttles_attempts",
        "c"
      ]
    ]
  }
}
LITERAL_FOREIGN_KEYS = {
  "audit.events": [],
  "security.local_users": [],
  "security.login_sessions": [
    [
      [
        "user_id"
      ],
      "security.local_users",
      [
        "id"
      ]
    ]
  ],
  "security.global_role_grants": [
    [
      [
        "user_id"
      ],
      "security.local_users",
      [
        "id"
      ]
    ]
  ],
  "security.login_throttles": [],
  "inventory.resources": [],
  "inventory.resource_identifiers": [
    [
      [
        "resource_id"
      ],
      "inventory.resources",
      [
        "id"
      ]
    ]
  ],
  "inventory.resource_relations": [
    [
      [
        "source_resource_id"
      ],
      "inventory.resources",
      [
        "id"
      ]
    ],
    [
      [
        "target_resource_id"
      ],
      "inventory.resources",
      [
        "id"
      ]
    ]
  ],
  "inventory.groups": [],
  "inventory.group_memberships": [
    [
      [
        "group_id"
      ],
      "inventory.groups",
      [
        "id"
      ]
    ],
    [
      [
        "resource_id"
      ],
      "inventory.resources",
      [
        "id"
      ]
    ]
  ],
  "inventory.group_rules": [
    [
      [
        "group_id"
      ],
      "inventory.groups",
      [
        "id"
      ]
    ]
  ],
  "inventory.tags": [],
  "inventory.resource_tags": [
    [
      [
        "resource_id"
      ],
      "inventory.resources",
      [
        "id"
      ]
    ],
    [
      [
        "tag_id"
      ],
      "inventory.tags",
      [
        "id"
      ]
    ]
  ],
  "inventory.policies": [],
  "inventory.policy_versions": [
    [
      [
        "policy_id"
      ],
      "inventory.policies",
      [
        "id"
      ]
    ]
  ],
  "inventory.policy_assignments": [
    [
      [
        "group_id"
      ],
      "inventory.groups",
      [
        "id"
      ]
    ],
    [
      [
        "policy_version_id"
      ],
      "inventory.policy_versions",
      [
        "id"
      ]
    ],
    [
      [
        "resource_id"
      ],
      "inventory.resources",
      [
        "id"
      ]
    ]
  ],
  "inventory.effective_configs": [
    [
      [
        "resource_id"
      ],
      "inventory.resources",
      [
        "id"
      ]
    ]
  ]
}
LITERAL_CATALOG_COLUMNS = {
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
  "pg_statistic_ext": "oid stxowner"
}
LITERAL_FUNCTIONS = ["acldefault","aclexplode","cardinality","convert_to","count","current_database","current_setting","encode","format_type","has_column_privilege","has_database_privilege","has_function_privilege","has_parameter_privilege","has_schema_privilege","has_sequence_privilege","has_table_privilege","inet_server_addr","inet_server_port","jsonb_build_array","pg_control_system","pg_get_constraintdef","pg_get_expr","pg_get_function_identity_arguments","pg_get_functiondef","pg_get_indexdef","pg_get_ruledef","pg_get_triggerdef","pg_has_role"]
LITERAL_RIGHTS = {
    "security.local_users": {"SELECT": "id login password_hash status created_at updated_at", "UPDATE": "updated_at"},
    "security.login_sessions": {"SELECT": "id token_hash user_id created_at last_activity_at expires_at revoked_at", "INSERT": "id token_hash user_id created_at last_activity_at expires_at revoked_at", "UPDATE": "last_activity_at revoked_at"},
    "security.global_role_grants": {"SELECT": "id user_id role scope_type scope_id created_at"},
    "security.login_throttles": {"SELECT": "bucket_hash window_started_at attempts", "INSERT": "bucket_hash window_started_at attempts", "UPDATE": "window_started_at attempts"},
    "audit.events": {"INSERT": "id occurred_at actor_type actor_id action entity_type entity_id correlation_id request_id outcome changes context"},
    "inventory.resources": {"SELECT": "id resource_type display_name description administrative_state attributes created_at updated_at archived_at row_version"},
}
LITERAL_OWNERS = ("database", "schema", "relation", "routine", "type", "extension",
    "language", "fdw", "server", "tablespace", "largeobject", "eventtrigger", "publication",
    "subscription", "conversion", "collation", "opclass", "operator", "opfamily", "tsconfig",
    "tsdict", "statistics", "defaultacl")


def raw_catalog(runtime="runtime", verifier="verifier", database="synthetic_lab"):
    return deepcopy(_literal_catalog(runtime, verifier, database))


@lru_cache(maxsize=8)
def _literal_catalog(runtime, verifier, database):
    """Complete synthetic topology with independent literal privilege oracle.

    OIDs, types and deparsed definitions are synthetic; no physical approval is
    implied. Coverage and mandatory objects must nevertheless be consistent.
    """
    roles = (runtime, verifier)
    role_ids = {runtime: "1001", verifier: "1002"}
    data = {f"Q{i}": [] for i in range(2, 17)}
    data["Q2"] = [[r, True, False, False, False, False, False, role_ids[r]] for r in roles]
    data["Q3"] = [["path", r, t, False, False, False] for r in roles for t in roles if r != t]
    schema_ids = {n: str(200 + i) for i, n in enumerate(
        ("security", "inventory", "audit", "public", "pg_catalog", "information_schema", "pg_toast"))}
    for r in roles:
        for n, ident in schema_ids.items():
            usage = n in {"public", "pg_catalog", "information_schema"} or (r == runtime and n in {"security", "inventory", "audit"})
            data["Q4"].append([r, n, usage, False, False, False, ident, "100"])
    relations = {}
    def relation(schema, table, cols, kind="r"):
        ident = str(10000 + len(relations))
        relations[schema + "." + table] = (ident, kind, tuple(cols))
        data["Q13"].append(["relation", schema, table, kind, "100", "p", ident])
        for number, col in enumerate(cols, 1):
            data["Q13"].append(["column", schema, table, col, number, "text", True, "", "", None])
        return ident
    for name, spec in sorted(LITERAL_STRUCTURE.items()):
        relation(*name.split("."), spec["columns"])
    for name, cols in sorted(LITERAL_CATALOG_COLUMNS.items()):
        relation("pg_catalog", name, cols.split())
    view = relation("pg_catalog", "synthetic_view", ("value",), "v")
    function_ids = {}
    functions = [(n, "pg_catalog", "internal", True) for n in LITERAL_FUNCTIONS]
    functions += [("RI_FKey_check_ins", "pg_catalog", "internal", True),
                  ("prevent_event_mutation", "audit", "plpgsql", False),
                  ("prevent_policy_version_mutation", "inventory", "plpgsql", False)]
    for i, (name, schema, lang, execute) in enumerate(functions):
        ident = str(50000 + i); function_ids[(schema, name)] = ident
        for r in roles:
            allowed = execute and (name != "pg_control_system" or r == verifier)
            data["Q11"].append([r, schema, ident, name, "", "f", "100", False,
                                lang, None, allowed, False, "a" * 64])
    counter = 70000
    def index(parent, name, keys, unique=False, primary=False):
        nonlocal counter
        rid, _, cols = relations[parent]
        ident = relation(parent.split(".")[0], name, tuple(cols[n - 1] for n in keys), "i")
        data["Q14"].append(["index", ident, rid, True, True, "SYNTHETIC INDEX " + name,
                            name, unique, primary, list(keys)])
        return ident
    primary_indexes = {}
    constraints = []
    for name, spec in sorted(LITERAL_STRUCTURE.items()):
        rid, _, cols = relations[name]
        for kind, count in sorted(spec["counts"].items()):
            if kind == "f": continue
            named = [n for n, k in spec["names"] if k == kind]
            for number in range(count):
                counter += 1
                cname = named[number] if number < len(named) else name.split(".")[1] + "_pkey"
                if kind == "p": keys = [1]
                elif kind in ("u", "x"): keys = [1, 2] if len(cols) > 1 else [1]
                else: keys = []
                backing = index(name, cname, keys, kind in ("p", "u"), kind == "p") if kind in ("p", "u", "x") else "0"
                if kind == "p": primary_indexes[name] = backing
                row = ["constraint", str(counter), rid, cname, True, "SYNTHETIC CONSTRAINT " + cname,
                        kind, backing, keys, "0", None]
                constraints.append(row)
        for iname in spec["indexes"]: index(name, iname, [1], iname.startswith("uq_"))
    for name, spec in sorted(LITERAL_STRUCTURE.items()):
        rid, _, cols = relations[name]
        explicit = [n for n, k in spec["names"] if k == "f"]
        for num, (local, remote, distant) in enumerate(LITERAL_FOREIGN_KEYS.get(name, ())):
            counter += 1
            rrid, _, rcols = relations[remote]
            cname = explicit[num] if num < len(explicit) else name.split(".")[1] + "_" + local[0] + "_fkey"
            fk = ["constraint", str(counter), rid, cname, True, "SYNTHETIC FK " + cname,
                  "f", primary_indexes[remote], [cols.index(c) + 1 for c in local], rrid,
                  [rcols.index(c) + 1 for c in distant]]
            constraints.append(fk)
            for target in (rid, rrid):
                for j in range(2):
                    counter += 1
                    data["Q14"].append(["trigger", str(counter), target,
                        function_ids[("pg_catalog", "RI_FKey_check_ins")], "O", True,
                        "SYNTHETIC FK TRIGGER", "RI_" + str(counter), fk[1]])
    data["Q14"].extend(constraints)
    for qualified, name, schema, function in (
        ("audit.events", "trg_audit_events_immutable", "audit", "prevent_event_mutation"),
        ("inventory.policy_versions", "trg_policy_versions_immutable", "inventory", "prevent_policy_version_mutation")):
        counter += 1
        data["Q14"].append(["trigger", str(counter), relations[qualified][0],
            function_ids[(schema, function)], "O", False, "SYNTHETIC TRIGGER " + name, name, "0"])
    data["Q14"].append(["rule", "pg_catalog", "synthetic_view", view, "80000", "_RETURN", "1", True, "O", "SYNTHETIC VIEW RULE"])
    for rid, _, _ in relations.values():
        data["Q14"].append(["rls", rid, False, False])
        counts = [sum((r[3] if k == "rule" else r[2]) == rid for r in data["Q14"] if r[0] == k)
                  for k in ("constraint", "index", "trigger", "rule", "policy")]
        data["Q14"].append(["coverage", rid, *counts])
    for kind in ("constraint", "index", "trigger", "rule", "policy"):
        data["Q14"].append(["catalog", kind, sum(r[0] == kind for r in data["Q14"])])

    # Independent effective cells, all permitted app operations spelled literally.
    for name, (rid, kind, cols) in relations.items():
        schema, table = name.split(".")
        if kind not in ("r", "p", "v", "m", "f"): continue
        for r in roles:
            for p in ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER"):
                data["Q5"].append([r, schema, table, p, False, False])
            for col in cols:
                for p in ("SELECT", "INSERT", "UPDATE", "REFERENCES"):
                    allowed = col in LITERAL_RIGHTS.get(name, {}).get(p, "").split() if r == runtime else (
                        p == "SELECT" and (schema == "pg_catalog" or name in ("public.alembic_version", "public.alembic_security_version")))
                    data["Q6"].append([r, schema, table, col, p, allowed, False])
    data["Q9"] = [["database", r, database, p, p == "CONNECT", False]
                  for r in roles for p in ("CONNECT", "CREATE", "TEMPORARY")]
    owner_objects = {k: {} for k in LITERAL_OWNERS}
    owner_objects["database"] = {"1": "100"}
    owner_objects["schema"] = {i: "100" for i in schema_ids.values()}
    owner_objects["relation"] = {rid: "100" for rid, _, _ in relations.values()}
    owner_objects["routine"] = {i: "100" for i in function_ids.values()}
    owner_objects["type"] = {str(90000 + i): "100" for i, (_, kind, _) in enumerate(relations.values()) if kind in ("r", "v")}
    owner_objects["language"] = {"5": "100"}; owner_objects["tablespace"] = {"6": "100"}
    for kind, objects in owner_objects.items():
        for r in roles:
            data["Q8"].extend([r, kind, ident, False, owner] for ident, owner in objects.items())
        data["Q8"].append(["coverage", kind, len(objects)])

    # Full ACL headers prove even NULL/empty ACL objects were visited.
    acl_objects = {}; grants = {}
    def acl(kind, key, entries=(), mode="explicit"):
        frozen = tuple(key); acl_objects[(kind, frozen)] = mode
        grants[(kind, frozen)] = list(entries)
    acl("database", (database, "1"), [("100", role_ids[r], "CONNECT", False) for r in roles])
    for schema, ident in schema_ids.items():
        entries = []
        if schema in {"public", "pg_catalog", "information_schema"}: entries = [("100", "0", "USAGE", False)]
        elif schema in {"security", "inventory", "audit"}: entries = [("100", "1001", "USAGE", False)]
        acl("schema", (schema, ident), entries)
    for name, (rid, kind, cols) in relations.items():
        schema, table = name.split(".")
        if kind in ("r", "p", "v", "m", "f", "S"): acl("relation", (schema, table, rid))
        for number, col in enumerate(cols, 1):
            entries = [("100", role_ids[r[0]], r[4], False) for r in data["Q6"]
                       if r[1:4] == [schema, table, col] and r[5] is True]
            acl("column", (schema, table, col, rid, number), entries, "explicit" if entries else "default")
    for r in data["Q11"]:
        permissions = [x for x in data["Q11"] if x[2] == r[2]]
        entries = ([("100", "0", "EXECUTE", False)] if all(x[10] for x in permissions) else
                   [("100", role_ids[x[0]], "EXECUTE", False) for x in permissions if x[10]])
        acl("routine", (r[1], r[3], r[4], r[2]), entries)
    for kind in ("type", "language", "fdw", "server", "tablespace", "largeobject"):
        for ident in owner_objects[kind]: acl(kind, (ident,))
    for key, mode in acl_objects.items():
        entries = grants[key]
        data["Q10"].append(["object", key[0], list(key[1]), "100", mode, len(entries)])
        data["Q10"].extend(["grant", key[0], list(key[1]), *e] for e in entries)
    data["Q15"] = [["application", "f066a01a7230"], ["security", "b12b01a7230"]]
    data["Q16"] = [["7699783234487926818", 1300, 202307071]]
    return data


def make_policy(data=None, **changes):
    # Unique logical endpoint isolates shared latches between tests, not DB I/O.
    data = raw_catalog() if data is None else data
    values = dict(version="D05-G2-FIX1-v2", target=("offline-" + uuid.uuid4().hex, 5432, "synthetic_lab", "runtime"),
        verifier_role="verifier", server_address="172.26.0.2", server_version="160010",
        system_identifier="7699783234487926818",
        manifest=tuple((q, normalize(rows, CATALOG[q].max_rows)) for q, rows in sorted(data.items()) if q != "Q15"))
    values.update(changes)
    return Policy(**values, approved_digest=contract_digest(**values))


class Connection:
    def __init__(self):
        self.events = []
        self.options = None
        self.failure = None

    def begin(self, **options):
        self.events.append("begin"); self.options = options
        if self.failure == "begin":
            raise RuntimeError("sensitive synthetic driver detail")

    def rollback(self):
        self.events.append("rollback")
        if self.failure == "rollback":
            raise RuntimeError("sensitive synthetic rollback detail")

    def close(self):
        self.events.append("close")
        if self.failure == "close":
            raise RuntimeError("sensitive synthetic close detail")


class Clock:
    def __init__(self):
        self.value = 100.0
    def __call__(self):
        return self.value


def harness(policy=None, data=None):
    policy = policy or make_policy()
    data = data or {q: rows for q, rows in policy.manifest}
    batches = {("verifier", q): Batch(tuple(rows)) for q, rows in data.items()}
    batches[("verifier", "Q15")] = Batch((("application", "f066a01a7230"), ("security", "b12b01a7230")))
    for subject, role in (("runtime", policy.target[3]), ("verifier", policy.verifier_role)):
        batches[(subject, "Q1")] = Batch(((policy.target[2], role, role, policy.server_address,
            policy.target[1], policy.server_version, "on", "repeatable read", "pg_catalog"),))
    runtime, verifier = Connection(), Connection()
    clock = Clock()
    executor = OfflineExecutor(batches)
    adapter = OfflineReadinessAdapter(policy, runtime_factory=Mock(return_value=runtime),
        verifier_factory=Mock(return_value=verifier), executor=executor, clock=clock)
    return adapter, batches, runtime, verifier, clock


def install_batches(adapter, batches):
    adapter._executor = OfflineExecutor(batches)


def test_positive_synthetic_contract_and_limits():
    adapter, batches, runtime, verifier, clock = harness()
    obs = adapter()
    assert type(obs) is ReadinessObservation
    assert _privileges_valid(obs.privileges, adapter.policy.target)
    assert obs.observed_at == 100 and obs.read_only is True
    assert obs.schemas >= {"security", "audit", "inventory"}
    assert runtime.events == verifier.events == ["begin", "rollback", "close"]
    assert runtime.options == verifier.options == dict(read_only=True, isolation="REPEATABLE READ",
        search_path="pg_catalog", statement_timeout_ms=500, lock_timeout_ms=200,
        idle_transaction_timeout_ms=1000, deadline=104)
    assert adapter._runtime_factory.call_args.kwargs["target"][-1] == "runtime"
    assert adapter._verifier_factory.call_args.kwargs["target"][-1] == "verifier"
    assert adapter._runtime_factory.call_args.kwargs["connect_timeout"] == 2


def test_exact_matrix_is_immutable_and_column_limited():
    assert {c for t, c, p in MATRIX if t == "security.local_users" and p == "UPDATE"} == {"updated_at"}
    assert {c for t, c, p in MATRIX if t == "security.login_sessions" and p == "UPDATE"} == {"last_activity_at", "revoked_at"}
    assert {c for t, c, p in MATRIX if t == "security.login_throttles" and p == "UPDATE"} == {"window_started_at", "attempts"}
    assert all(p == "SELECT" for t, c, p in MATRIX if t.startswith("inventory."))
    assert all(p == "INSERT" for t, c, p in MATRIX if t == "audit.events")
    assert not any(p in {"DELETE", "TRUNCATE", "REFERENCES", "TRIGGER"} for t, c, p in MATRIX)
    with pytest.raises(TypeError):
        COLUMNS["audit.events"] = ()
    with pytest.raises(FrozenInstanceError):
        make_policy().version = "other"


@pytest.mark.parametrize("table,col,priv", sorted(MATRIX))
def test_each_required_column_privilege_must_be_observed(table, col, priv):
    adapter, batches, *_ = harness()
    rows = [list(r) for r in batches[("verifier", "Q6")].rows]
    row = next(r for r in rows if r[:5] == ["runtime", *table.split("."), col, priv])
    row[5] = False
    batches[("verifier", "Q6")] = Batch(tuple(rows)); install_batches(adapter, batches)
    with pytest.raises(Unavailable):
        adapter()


@pytest.mark.parametrize("table,col,priv", [
    ("security.local_users", "password_hash", "UPDATE"),
    ("security.local_users", "login", "UPDATE"),
    ("security.local_users", "id", "INSERT"),
    ("security.login_sessions", "token_hash", "UPDATE"),
    ("security.login_sessions", "expires_at", "UPDATE"),
    ("security.global_role_grants", "role", "UPDATE"),
    ("security.login_throttles", "bucket_hash", "UPDATE"),
    ("inventory.resources", "id", "INSERT"),
    ("audit.events", "id", "SELECT"),
    ("audit.events", "context", "UPDATE"),
    ("public.alembic_version", "version_num", "SELECT"),
])
def test_manifest_cannot_approve_forbidden_column_rights(table, col, priv):
    data = raw_catalog()
    row = next(r for r in data["Q6"] if r[:5] == ["runtime", *table.split("."), col, priv])
    row[5] = True
    with pytest.raises(Unavailable):
        make_policy(data)


@pytest.mark.parametrize("family", [f"Q{i}" for i in range(2, 17)])
@pytest.mark.parametrize("mutation", ["missing", "extra", "null", "duplicate", "truncated"])
def test_every_family_requires_complete_exact_evidence(family, mutation):
    adapter, batches, *_ = harness()
    key = ("verifier", family)
    batch = batches[key]
    rows = list(batch.rows)
    if mutation == "missing":
        del batches[key]
    elif mutation == "extra":
        batches[key] = Batch(tuple(rows + [("unexpected",)]))
    elif mutation == "null":
        batches[key] = Batch(((None,),))
    elif mutation == "duplicate":
        batches[key] = Batch(tuple(rows + [rows[0] if rows else ("unexpected",)]))
    else:
        batches[key] = replace(batch, complete=False)
    install_batches(adapter, batches)
    with pytest.raises(Unavailable):
        adapter()


@pytest.mark.parametrize("family,index", [("Q2", 2), ("Q2", 3), ("Q2", 4), ("Q2", 5), ("Q2", 6),
    ("Q3", 3), ("Q3", 4), ("Q3", 5), ("Q4", 4), ("Q8", 3), ("Q9", 5), ("Q11", 11)])
def test_negative_capabilities_cannot_be_approved(family, index):
    data = raw_catalog(); data[family][0][index] = True
    with pytest.raises(Unavailable):
        make_policy(data)


@pytest.mark.parametrize("family", ["Q4", "Q5", "Q6", "Q8", "Q9", "Q11", "Q13", "Q14", "Q16"])
def test_empty_manifest_is_not_positive_proof(family):
    data = raw_catalog(); data[family] = []
    with pytest.raises(Unavailable):
        make_policy(data)


@pytest.mark.parametrize("row", [
    ["relation", "inventory", "extra", "r", "100"],
    ["relation", "authorization", "anchors", "r", "100"],
    ["column", "security", "local_users", "extra", 7, "text", True, "", "", None],
])
def test_extra_objects_and_columns_fail_even_in_manifest(row):
    data = raw_catalog(); data["Q13"].append(row)
    with pytest.raises(Unavailable):
        make_policy(data)


@pytest.mark.parametrize("field,value", [(0, "other_db"), (1, "bootstrap"), (2, "bootstrap"),
    (3, "172.26.0.3"), (3, "invalid"), (3, "::ffff:172.26.0.2"), (3, None),
    (4, 5433), (4, 5432.0), (5, "150010"), (6, "off"), (7, "read committed"), (8, "public")])
@pytest.mark.parametrize("subject", ["runtime", "verifier"])
def test_both_connection_identities_are_mandatory(field, value, subject):
    adapter, batches, *_ = harness()
    row = list(batches[(subject, "Q1")].rows[0]); row[field] = value
    batches[(subject, "Q1")] = Batch((row,)); install_batches(adapter, batches)
    with pytest.raises(Unavailable):
        adapter()


@pytest.mark.parametrize("address", ["172.26.0.2", "172.26.0.2/32"])
def test_address_normalization(address):
    adapter, batches, *_ = harness()
    row = list(batches[("runtime", "Q1")].rows[0]); row[3] = address
    identity(adapter.policy, [row], "runtime")


def test_acl_change_latches_across_instances_until_explicit_revalidation():
    policy = make_policy()
    first, batches, *_ = harness(policy)
    first()
    batches[("verifier", "Q10")] = Batch((("schema", "public", "100", "CREATE", False),))
    install_batches(first, batches)
    with pytest.raises(Unavailable): first()
    second, *_ = harness(policy)
    with pytest.raises(Unavailable): second()
    second.revalidate(policy)
    assert second().connected


def test_positive_observations_are_never_cached():
    adapter, batches, *_ = harness()
    first = adapter()
    batches[("verifier", "Q15")] = Batch((("application", "f067a01a7230"), ("security", "b12b01a7230")))
    install_batches(adapter, batches)
    with pytest.raises(Unavailable): adapter()
    assert first.application_revision == "f066a01a7230"


@pytest.mark.parametrize("error", ["begin", "rollback", "close"])
def test_cleanup_attempts_independent_and_exceptions_sanitized(error):
    adapter, batches, runtime, verifier, clock = harness()
    verifier.failure = error
    with pytest.raises(Unavailable) as caught:
        adapter()
    assert str(caught.value) == "Readiness unavailable"
    assert caught.value.__context__ is None and caught.value.__cause__ is None
    assert runtime.events[-2:] == verifier.events[-2:] == ["rollback", "close"]


def test_partial_connection_failure_closes_first_and_never_retries():
    adapter, batches, runtime, verifier, clock = harness()
    adapter._verifier_factory.side_effect = TimeoutError("synthetic-sensitive")
    with pytest.raises(Unavailable) as caught: adapter()
    assert runtime.events == ["begin", "rollback", "close"]
    assert adapter._verifier_factory.call_count == 1
    assert caught.value.__context__ is None


def test_same_connection_for_both_roles_is_rejected():
    adapter, batches, runtime, verifier, clock = harness()
    adapter._verifier_factory.return_value = runtime
    with pytest.raises(Unavailable): adapter()
    assert runtime.events == ["begin", "rollback", "close"]


@pytest.mark.parametrize("phase", ["connect", "statement", "cleanup"])
def test_global_deadline_includes_every_phase(phase, monkeypatch):
    adapter, batches, runtime, verifier, clock = harness()
    if phase == "connect":
        def slow(**kwargs): clock.value += 4; return runtime
        adapter._runtime_factory.side_effect = slow
    elif phase == "statement":
        original = OfflineExecutor.execute
        def slow(self, *args, **kwargs):
            clock.value += 0.3
            assert kwargs["timeout_ms"] <= 1000
            return original(self, *args, **kwargs)
        monkeypatch.setattr(OfflineExecutor, "execute", slow)
    else:
        def slow(): runtime.events.append("close"); clock.value += 4
        runtime.close = slow
    with pytest.raises(Unavailable): adapter()
    assert runtime.events[-2:] == ["rollback", "close"]


def test_single_inflight_shared_between_instances():
    policy = make_policy(); first, *_ = harness(policy); second, *_ = harness(policy)
    assert first._scope.lock.acquire(blocking=False)
    try:
        with pytest.raises(Unavailable): second()
        with pytest.raises(Unavailable): second.revalidate(policy)
        assert not second._runtime_factory.called
    finally:
        first._scope.lock.release()


@pytest.mark.parametrize("value", [None, True, 0, "false", float("nan"), {}, [1]])
def test_required_boolean_is_not_coerced(value):
    adapter, batches, *_ = harness()
    rows = [list(r) for r in batches[("verifier", "Q2")].rows]; rows[0][2] = value
    batches[("verifier", "Q2")] = Batch(rows); install_batches(adapter, batches)
    with pytest.raises(Unavailable): adapter()


def test_default_executor_blocks_before_any_factory_and_no_config_switch():
    policy = make_policy(); factory = Mock(side_effect=AssertionError("Must not connect"))
    adapter = OfflineReadinessAdapter(policy, runtime_factory=factory, verifier_factory=factory)
    with pytest.raises(Unavailable): adapter()
    assert not factory.called
    with pytest.raises(Unavailable): DisabledPostgresExecutor().execute()


def test_cardinality_byte_limits_and_bound_policy_digest():
    with pytest.raises(Unavailable): normalize([("a",)] * 3, 2)
    with pytest.raises(Unavailable): normalize([("a",), ("a",)], 2)
    adapter, *_ = harness(); adapter._limits = Limits(max_bytes=1)
    with pytest.raises(Unavailable): adapter()
    policy = make_policy()
    with pytest.raises(Unavailable): replace(policy, server_address="172.26.0.3")
    with pytest.raises(Unavailable): replace(policy, manifest=())


@pytest.mark.parametrize("name", CATALOG)
def test_sql_catalog_is_fixed_select_only_with_no_silent_limit(name):
    query = CATALOG[name]
    import re
    # Strip SQL literals before checking command words (UPDATE etc are privilege labels).
    text = re.sub(r"'(?:''|[^'])*'", "''", query.sql).upper()
    assert not re.search(r"\b(INSERT|UPDATE|DELETE|TRUNCATE|CREATE|ALTER|DROP|GRANT|REVOKE|CALL|DO|COPY|LIMIT)\b", text)
    assert ";" not in text and "--" not in text
    assert query.sql.startswith(("SELECT ", "WITH subjects AS ("))
    assert "FOR UPDATE" not in query.sql and query.max_rows > 0
    assert query.statement_ms in (500, 1000)
    assert "password_hash" not in query.sql and "token_hash" not in query.sql
    if name not in ("Q1", "Q15", "Q16"):
        assert "pg_catalog." in query.sql


def test_no_import_or_factory_activation_paths():
    root = Path(__file__).resolve().parents[1] / "app"
    assert "readiness_postgres" not in (root / "dedicated.py").read_text()
    assert "readiness_postgres" not in (root / "__init__.py").read_text()
    for path in (root / "readiness_postgres").glob("*.py"):
        tree = ast.parse(path.read_text())
        imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
        assert not any(any(word in ast.unparse(n) for word in ("psycopg", "sqlalchemy", "subprocess", "docker", "alembic")) for n in imports)


@pytest.mark.parametrize("field", ["connect_seconds", "statement_ms", "heavy_statement_ms", "lock_ms", "idle_transaction_ms", "global_seconds", "max_bytes"])
def test_limits_cannot_be_weakened(field):
    with pytest.raises(Unavailable): Limits(**{field: 999999999})
    with pytest.raises(Unavailable): Limits(**{field: False})


@pytest.mark.parametrize("family,row", [
    ("Q3", ["edge", "1001", "7000", "100", False, False, False]),
    ("Q3", ["edge", "7000", "1002", "100", False, False, True]),
    ("Q10", ["schema", "public", "100", "CREATE", False]),
    ("Q10", ["schema", "security", "100", "USAGE", False]),
    ("Q10", ["relation", "audit.events", "100", "SELECT", False]),
    ("Q10", ["column", "security.local_users.password_hash", "100", "UPDATE", False]),
    ("Q10", ["database", "synthetic_lab", "100", "TEMPORARY", False]),
    ("Q12", ["100", "0", "r", "100", "0", "SELECT", False]),
    ("Q12", ["100", "0", "r", "100", "1001", "INSERT", False]),
])
def test_public_and_default_acls_or_membership_cannot_override_contract(family, row):
    data = raw_catalog(); data[family].append(row)
    with pytest.raises(Unavailable): make_policy(data)


@pytest.mark.parametrize("family,mutate", [
    ("Q11", lambda r: r[:7] + [True] + r[8:]),
    ("Q12", lambda r: ["100", "0", "r", "100", "9000", "SELECT", False]),
    ("Q13", lambda r: ["relation", "inventory", "resources", "v", "100"]),
    ("Q14", lambda r: ["rls", "1", True, False]),
    ("Q16", lambda r: ["1111111111111111111", 1300, 202307071]),
])
def test_routine_default_acl_structure_rls_and_physical_identity_drift(family, mutate):
    adapter, batches, *_ = harness()
    batch = batches[("verifier", family)]
    rows = [list(row) for row in batch.rows]
    if rows: rows[0] = mutate(rows[0])
    else: rows.append(mutate([]))
    batches[("verifier", family)] = Batch(rows); install_batches(adapter, batches)
    with pytest.raises(Unavailable): adapter()


def test_f066_trigger_routine_requires_pinned_safe_signature_and_hash():
    data = raw_catalog()
    for r in data["Q11"]:
        if r[1] == "audit": r[10] = True
    header = next(r for r in data["Q10"] if r[0] == "object" and r[1] == "routine" and r[2][0] == "audit")
    header[5] = 1
    data["Q10"].append(["grant", "routine", header[2], "100", "0", "EXECUTE", False])
    policy = make_policy(data)
    adapter, *_ = harness(policy)
    assert adapter().connected
    next(r for r in data["Q11"] if r[1] == "audit")[7] = True
    with pytest.raises(Unavailable): make_policy(data)


@pytest.mark.parametrize("cause", ["clock_nan", "clock_backwards", "query_timeout", "too_many_rows"])
def test_other_fail_closed_paths(cause, monkeypatch):
    adapter, batches, runtime, verifier, clock = harness()
    if cause == "clock_nan": clock.value = float("nan")
    elif cause == "clock_backwards":
        adapter._clock = Mock(side_effect=[100, 99, 99])
    elif cause == "query_timeout":
        monkeypatch.setattr(OfflineExecutor, "execute", Mock(side_effect=TimeoutError("synthetic-sensitive")))
    else:
        batches[("runtime", "Q1")] = Batch(tuple((str(i),) for i in range(2)))
        install_batches(adapter, batches)
    with pytest.raises(Unavailable): adapter()


def test_ddl_broad_table_grants_and_grant_options_refused():
    for family, index in (("Q4", 5), ("Q5", 5), ("Q6", 6)):
        data = raw_catalog(); data[family][0][index] = True
        with pytest.raises(Unavailable): make_policy(data)
    data = raw_catalog()
    row = next(r for r in data["Q5"] if r[:4] == ["runtime", "security", "local_users", "UPDATE"])
    row[4] = True
    with pytest.raises(Unavailable): make_policy(data)


def test_missing_coverage_refused_even_if_manifest_digest_matches():
    for family in ("Q5", "Q6"):
        data = raw_catalog(); data[family].pop()
        with pytest.raises(Unavailable): make_policy(data)


def test_query_shapes_include_pg16_specific_evidence():
    assert all(t in CATALOG["Q3"].sql for t in ("inherit_option", "set_option", "'MEMBER'", "'SET'"))
    assert "acldefault" in CATALOG["Q10"].sql
    assert "aclexplode(a.attacl)" in CATALOG["Q10"].sql
    assert "sha256" in CATALOG["Q11"].sql and "ELSE NULL" in CATALOG["Q11"].sql
    assert "pg_shdepend" in CATALOG["Q8"].sql and "pg_namespace" in CATALOG["Q8"].sql
    assert "pg_control_system()" in CATALOG["Q16"].sql
    assert "THEN 's'::pg_catalog.\"char\"" in CATALOG["Q10"].sql
    assert "has_largeobject_privilege" not in CATALOG["Q9"].sql


@pytest.mark.parametrize("kind,priv", [("server", "USAGE"), ("fdw", "USAGE"),
    ("largeobject", "SELECT"), ("largeobject", "UPDATE"), ("tablespace", "CREATE")])
@pytest.mark.parametrize("grantee", ["1001", "1002", "0"])
def test_other_acl_classes_cannot_introduce_capabilities(kind, priv, grantee):
    data = raw_catalog()
    data["Q9"].append(["object_acl", kind, "77", "100", grantee, priv, False])
    with pytest.raises(Unavailable): make_policy(data)


@pytest.mark.parametrize("name", CATALOG)
def test_bind_parameters_compile_offline_without_a_driver(name):
    from sqlalchemy import text
    from sqlalchemy.dialects.postgresql import dialect
    compiled = text(CATALOG[name].sql).compile(dialect=dialect())
    assert set(compiled.params) <= {"runtime_role", "verifier_role"}
    if name in ("Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8", "Q9", "Q11"):
        assert set(compiled.params) == {"runtime_role", "verifier_role"}


@pytest.mark.parametrize("phase", ["connect", "statement"])
def test_individual_timeouts_fail_before_global_budget(phase, monkeypatch):
    adapter, batches, runtime, verifier, clock = harness()
    if phase == "connect":
        def slow(**kwargs): clock.value += 2.1; return runtime
        adapter._runtime_factory.side_effect = slow
    else:
        original = OfflineExecutor.execute
        def slow(self, *args, **kwargs):
            clock.value += 0.6
            return original(self, *args, **kwargs)
        monkeypatch.setattr(OfflineExecutor, "execute", slow)
    with pytest.raises(Unavailable): adapter()
    assert clock.value < 104
    assert runtime.events[-2:] == ["rollback", "close"]


def recount_structure(data):
    """Independent synthetic count oracle, also used to avoid merely testing EOF."""
    for row in data["Q14"]:
        if row[0] == "catalog":
            row[2] = sum(r[0] == row[1] for r in data["Q14"])
        elif row[0] == "coverage":
            row[2:] = [sum((r[3] if kind == "rule" else r[2]) == row[1]
                           for r in data["Q14"] if r[0] == kind)
                       for kind in ("constraint", "index", "trigger", "rule", "policy")]


@pytest.mark.parametrize("definition,instead,enabled", [
    ("SYNTHETIC INSERT REDIRECT", True, "O"),
    ("SYNTHETIC INSERT SUPPRESS", True, "O"),
    ("SYNTHETIC INSERT ALSO", False, "O"),
    ("SYNTHETIC DISABLED RULE", True, "D"),
])
def test_fix1_01_unapproved_audit_rules_fail_even_with_consistent_counts(definition, instead, enabled):
    data = raw_catalog()
    rel = next(r for r in data["Q13"] if r[:3] == ["relation", "audit", "events"])
    data["Q14"].append(["rule", "audit", "events", rel[6], "990001", "unexpected", "3", instead, enabled, definition])
    recount_structure(data)
    with pytest.raises(Unavailable): make_policy(data)


@pytest.mark.parametrize("mutation", ["definition", "disabled", "unknown_relation", "duplicate_oid", "duplicate_name", "missing", "null"])
def test_fix1_01_rule_provenance_and_view_rules(mutation):
    data = raw_catalog(); row = next(r for r in data["Q14"] if r[0] == "rule")
    if mutation == "definition":
        # Structurally valid, explicitly approved system view definitions can
        # differ, but cannot pass the previous approved observation comparison.
        adapter, batches, *_ = harness(make_policy(data))
        row[9] = "SYNTHETIC CHANGED VIEW DEFINITION"
        batches[("verifier", "Q14")] = Batch(data["Q14"]); install_batches(adapter, batches)
        with pytest.raises(Unavailable): adapter()
        return
    if mutation == "disabled": row[8] = "D"
    elif mutation == "unknown_relation": row[3] = "999999"
    elif mutation == "duplicate_oid": data["Q14"].append(list(row))
    elif mutation == "duplicate_name":
        other = list(row); other[4] = "999998"; data["Q14"].append(other)
    elif mutation == "missing": data["Q14"].remove(row)
    else: row[9] = None
    recount_structure(data)
    with pytest.raises(Unavailable): make_policy(data)


@pytest.mark.parametrize("mutation", ["database_ownership_only", "ownership_no_marker", "ownership_count", "ownership_contradiction",
    "rls_only", "relation_no_coverage", "global_count", "unknown_relkind", "no_catalog_usage", "missing_check", "missing_fk",
    "missing_trigger", "missing_index", "unknown_column", "extra_schema", "unknown_owner"])
def test_fix1_02_independent_partial_or_inconsistent_evidence(mutation):
    data = raw_catalog()
    if mutation == "database_ownership_only": data["Q8"] = [r for r in data["Q8"] if r[1] == "database"]
    elif mutation == "ownership_no_marker": data["Q8"] = [r for r in data["Q8"] if r[:2] != ["coverage", "fdw"]]
    elif mutation == "ownership_count": next(r for r in data["Q8"] if r[:2] == ["coverage", "type"])[2] += 1
    elif mutation == "ownership_contradiction": next(r for r in data["Q8"] if r[0] == "runtime")[4] = "1001"
    elif mutation == "rls_only": data["Q14"] = [next(r for r in data["Q14"] if r[0] == "rls")]
    elif mutation == "relation_no_coverage": data["Q14"].remove(next(r for r in data["Q14"] if r[0] == "coverage"))
    elif mutation == "global_count": next(r for r in data["Q14"] if r[:2] == ["catalog", "rule"])[2] = 0
    elif mutation == "unknown_relkind": next(r for r in data["Q13"] if r[0] == "relation")[3] = "X"
    elif mutation == "no_catalog_usage":
        for r in data["Q4"]:
            if r[1] == "pg_catalog": r[2] = False
    elif mutation in ("missing_check", "missing_fk"):
        row = next(r for r in data["Q14"] if r[0] == "constraint" and r[6] == ("c" if mutation == "missing_check" else "f"))
        data["Q14"].remove(row)
        if row[6] == "f": data["Q14"] = [r for r in data["Q14"] if not (r[0] == "trigger" and r[8] == row[1])]
        recount_structure(data)
    elif mutation == "missing_trigger":
        data["Q14"] = [r for r in data["Q14"] if not (r[0] == "trigger" and r[7] == "trg_audit_events_immutable")]
        recount_structure(data)
    elif mutation == "missing_index":
        data["Q14"] = [r for r in data["Q14"] if not (r[0] == "index" and r[6] == "ix_resources_type_state")]
        recount_structure(data)
    elif mutation == "unknown_column": data["Q13"].append(["column", "security", "local_users", "backdoor", 7, "text", True, "", "", None])
    elif mutation == "extra_schema":
        for subject in ("runtime", "verifier"): data["Q4"].append([subject, "authorization", False, False, False, False, "555", "100"])
    else: next(r for r in data["Q13"] if r[0] == "relation")[4] = "UNKNOWN"
    with pytest.raises(Unavailable): make_policy(data)


def add_redundant_acl(data, grantee="1001", grantor="9000", option=False):
    row = next(r for r in data["Q10"] if r[:2] == ["object", "column"] and r[2][:3] == ["security", "local_users", "login"])
    row[5] += 1
    data["Q10"].append(["grant", "column", list(row[2]), grantor, grantee, "SELECT", option])


@pytest.mark.parametrize("grantee,grantor", [("1001", "9000"), ("9001", "100")])
def test_fix1_03_redundant_non_public_acl_changes_fingerprint(grantee, grantor):
    original = raw_catalog(); policy = make_policy(original)
    changed = raw_catalog(); add_redundant_acl(changed, grantee, grantor)
    # Same effective D05 matrix, structurally complete provenance.
    other = make_policy(changed, target=policy.target)
    assert policy.approved_digest != other.approved_digest
    assert original["Q5"] == changed["Q5"] and original["Q6"] == changed["Q6"]
    adapter, batches, *_ = harness(policy)
    batches[("verifier", "Q10")] = Batch(changed["Q10"]); install_batches(adapter, batches)
    with pytest.raises(Unavailable): adapter()
    assert adapter._scope.invalidated


def test_fix1_03_null_vs_explicit_empty_acl_changes_fingerprint():
    data = raw_catalog(); policy = make_policy(data)
    header = next(r for r in data["Q10"] if r[0] == "object" and r[1] == "column" and r[4] == "default")
    assert header[5] == 0
    header[4] = "explicit"
    assert make_policy(data, target=policy.target).approved_digest != policy.approved_digest
    adapter, batches, *_ = harness(policy); batches[("verifier", "Q10")] = Batch(data["Q10"])
    install_batches(adapter, batches)
    with pytest.raises(Unavailable): adapter()


@pytest.mark.parametrize("kind", ["database", "schema", "relation", "column", "routine", "type", "language", "tablespace"])
def test_fix1_03_missing_acl_object_header_is_unknown(kind):
    data = raw_catalog()
    data["Q10"].remove(next(r for r in data["Q10"] if r[:2] == ["object", kind]))
    with pytest.raises(Unavailable): make_policy(data)


@pytest.mark.parametrize("mutation", ["grant_option", "duplicate", "missing_provenance", "header_count", "owner"])
def test_fix1_03_acl_provenance_is_not_replaced_by_effective_rights(mutation):
    data = raw_catalog()
    if mutation == "grant_option": add_redundant_acl(data, option=True)
    elif mutation == "duplicate":
        row = next(r for r in data["Q10"] if r[0] == "grant"); data["Q10"].append(list(row))
    elif mutation == "missing_provenance": next(r for r in data["Q10"] if r[0] == "grant")[3] = None
    elif mutation == "header_count": next(r for r in data["Q10"] if r[0] == "object")[5] += 1
    else: next(r for r in data["Q10"] if r[0] == "object")[3] = "999"
    with pytest.raises(Unavailable): make_policy(data)


def test_fix1_03_changed_default_acl_is_observed_even_for_other_roles():
    data = raw_catalog(); policy = make_policy(data)
    marker = next(r for r in data["Q8"] if r[:2] == ["coverage", "defaultacl"]); marker[2] = 1
    for subject in ("runtime", "verifier"): data["Q8"].append([subject, "defaultacl", "9900", False, "100"])
    data["Q12"] = [["default", "100", "0", "r", "9900", 1],
                   ["grant", "100", "0", "r", "9900", "100", "9000", "SELECT", False]]
    assert make_policy(data, target=policy.target).approved_digest != policy.approved_digest
    adapter, batches, *_ = harness(policy); batches[("verifier", "Q12")] = Batch(data["Q12"])
    install_batches(adapter, batches)
    with pytest.raises(Unavailable): adapter()


@pytest.mark.parametrize("role,method,exception", [("verifier", "rollback", KeyboardInterrupt),
    ("verifier", "close", KeyboardInterrupt), ("verifier", "rollback", SystemExit),
    ("runtime", "rollback", KeyboardInterrupt), ("runtime", "close", SystemExit)])
def test_fix1_04_interruptions_finish_cleanup_and_release_lock(role, method, exception):
    adapter, batches, runtime, verifier, clock = harness()
    resource = verifier if role == "verifier" else runtime
    interruption = exception("synthetic cancellation")
    def stop(): resource.events.append(method); raise interruption
    setattr(resource, method, stop)
    with pytest.raises(exception) as caught: adapter()
    assert caught.value is interruption
    assert runtime.events == verifier.events == ["begin", "rollback", "close"]
    assert not adapter._scope.lock.locked()


@pytest.mark.parametrize("phase", ["before_begin", "after_begin", "query"])
def test_fix1_04_original_interruption_survives_secondary_cleanup_failures(phase):
    adapter, batches, runtime, verifier, clock = harness()
    interruption = KeyboardInterrupt("original")
    runtime.failure = "rollback"; verifier.failure = "close"
    if phase == "before_begin": adapter._verifier_factory.side_effect = interruption
    elif phase == "after_begin":
        def begin(**options): verifier.events.append("begin"); raise interruption
        verifier.begin = begin
    else:
        # A cancellation in the injected clock occurs before query collection.
        adapter._clock = Mock(side_effect=[100] * 5 + [interruption] + [100] * 5)
    with pytest.raises(KeyboardInterrupt) as caught: adapter()
    assert caught.value is interruption
    assert runtime.events[-2:] == ["rollback", "close"]
    if phase == "after_begin": assert verifier.events[-2:] == ["rollback", "close"]
    assert not adapter._scope.lock.locked()


def test_fix1_04_consecutive_cleanup_interruptions_preserve_first():
    adapter, batches, runtime, verifier, clock = harness()
    first = KeyboardInterrupt("first")
    def stop(resource, method, error):
        def fail(): resource.events.append(method); raise error
        setattr(resource, method, fail)
    stop(verifier, "rollback", first); stop(verifier, "close", SystemExit("second"))
    stop(runtime, "rollback", RuntimeError("third")); stop(runtime, "close", SystemExit("fourth"))
    with pytest.raises(KeyboardInterrupt) as caught: adapter()
    assert caught.value is first
    assert runtime.events == verifier.events == ["begin", "rollback", "close"]
    assert not adapter._scope.lock.locked()


@pytest.mark.parametrize("value", ["u", "t", "X", None, ""])
@pytest.mark.parametrize("relation", [("security", "local_users"), ("audit", "events"), ("inventory", "resources")])
def test_fix1_05_required_tables_are_permanent(value, relation):
    data = raw_catalog()
    next(r for r in data["Q13"] if r[:3] == ["relation", *relation])[5] = value
    with pytest.raises(Unavailable): make_policy(data)


def test_fix1_05_absent_persistence_is_unknown():
    data = raw_catalog(); row = next(r for r in data["Q13"] if r[0] == "relation"); del row[5]
    with pytest.raises(Unavailable): make_policy(data)


def test_fix1_oracle_does_not_follow_wrong_policy(monkeypatch):
    import app.readiness_postgres.evaluate as evaluator
    data = raw_catalog()
    wrong = evaluator.MATRIX | {("audit.events", "id", "SELECT")}
    monkeypatch.setattr(evaluator, "MATRIX", wrong)
    with pytest.raises(Unavailable): make_policy(data)


def test_fix1_literal_columns_match_independent_orm_declarations():
    from app.core import model_registry
    from app.core.models import Base
    assert len(LITERAL_STRUCTURE) == 19
    for name, spec in LITERAL_STRUCTURE.items():
        if name.startswith("public."): continue
        assert spec["columns"] == [c.name for c in Base.metadata.tables[name].columns]


def test_fix1_catalog_sql_has_full_provenance_and_coverage():
    assert "pg_catalog.pg_rewrite" in CATALOG["Q14"].sql
    assert "pg_catalog.pg_get_ruledef" in CATALOG["Q14"].sql
    assert "relpersistence" in CATALOG["Q13"].sql
    assert "x.grantee=0" not in CATALOG["Q10"].sql
    assert "x.grantee::text" in CATALOG["Q10"].sql
    assert "'default' ELSE 'explicit'" in CATALOG["Q10"].sql
    assert "'coverage'" in CATALOG["Q8"].sql and "'coverage'" in CATALOG["Q14"].sql


@pytest.mark.parametrize("kind", LITERAL_OWNERS)
def test_fix1_02_every_owner_catalog_requires_an_explicit_coverage_marker(kind):
    data = raw_catalog(); data["Q8"] = [r for r in data["Q8"] if r[:2] != ["coverage", kind]]
    with pytest.raises(Unavailable): make_policy(data)


@pytest.mark.parametrize("table,column", [("pg_class", "oid"), ("pg_roles", "rolname"),
    ("pg_proc", "proacl"), ("pg_rewrite", "ev_class"), ("pg_subscription", "subowner")])
def test_fix1_02_verifier_needs_the_catalog_columns_actually_read(table, column):
    data = raw_catalog()
    next(r for r in data["Q6"] if r[:5] == ["verifier", "pg_catalog", table, column, "SELECT"])[5] = False
    header = next(r for r in data["Q10"] if r[:2] == ["object", "column"] and r[2][:3] == ["pg_catalog", table, column])
    header[5] -= 1
    data["Q10"] = [r for r in data["Q10"] if not (r[:2] == ["grant", "column"] and r[2] == header[2] and r[4] == "1002")]
    with pytest.raises(Unavailable): make_policy(data)


def test_fix1_03_consistent_schema_owner_transfer_invalidates_previous_manifest():
    original = raw_catalog(); policy = make_policy(original)
    changed = raw_catalog()
    ident = next(r[6] for r in changed["Q4"] if r[1] == "audit")
    for r in changed["Q4"]:
        if r[1] == "audit": r[7] = "9000"
    for r in changed["Q8"]:
        if r[0] in ("runtime", "verifier") and r[1:3] == ["schema", ident]: r[4] = "9000"
    for r in changed["Q10"]:
        if r[1] == "schema" and r[2] == ["audit", ident]: r[3] = "9000"
    assert make_policy(changed, target=policy.target).approved_digest != policy.approved_digest
    assert [r[:6] for r in original["Q4"]] == [r[:6] for r in changed["Q4"]]
    adapter, batches, *_ = harness(policy); batches[("verifier", "Q8")] = Batch(changed["Q8"])
    install_batches(adapter, batches)
    with pytest.raises(Unavailable): adapter()


def test_fix1_03_sequence_acl_is_inventoried_without_granting_runtime_rights():
    data = raw_catalog(); rid = "999000"; key = ["pg_catalog", "synthetic_sequence", rid]
    data["Q13"].append(["relation", "pg_catalog", "synthetic_sequence", "S", "100", "p", rid])
    for subject in ("runtime", "verifier"):
        data["Q8"].append([subject, "relation", rid, False, "100"])
        for privilege in ("SELECT", "UPDATE", "USAGE"):
            data["Q7"].append([subject, "pg_catalog", "synthetic_sequence", privilege, False, False])
    next(r for r in data["Q8"] if r[:2] == ["coverage", "relation"])[2] += 1
    data["Q10"].append(["object", "relation", key, "100", "explicit", 0])
    data["Q14"].extend([["rls", rid, False, False], ["coverage", rid, 0, 0, 0, 0, 0]])
    policy = make_policy(data); assert harness(policy)[0]().connected
    header = next(r for r in data["Q10"] if r[:3] == ["object", "relation", key]); header[5] = 1
    data["Q10"].append(["grant", "relation", key, "100", "9000", "USAGE", False])
    assert make_policy(data, target=policy.target).approved_digest != policy.approved_digest


def test_fix1_04_interruption_before_first_resource_still_releases_lock():
    adapter, batches, runtime, verifier, clock = harness()
    interruption = SystemExit("synthetic stop")
    adapter._runtime_factory.side_effect = interruption
    with pytest.raises(SystemExit) as caught: adapter()
    assert caught.value is interruption and runtime.events == verifier.events == []
    assert not adapter._scope.lock.locked()


@pytest.mark.parametrize("mutation", ["unknown_privilege", "unknown_constraint_index", "unknown_trigger_constraint", "noncanonical_oid"])
def test_fix1_unknown_identifiers_and_privileges_are_not_positive_evidence(mutation):
    data = raw_catalog()
    if mutation == "unknown_privilege":
        add_redundant_acl(data, grantee="9000")
        data["Q10"][-1][5] = "UNKNOWN"
    elif mutation == "unknown_constraint_index":
        next(r for r in data["Q14"] if r[0] == "constraint" and r[6] == "c")[7] = "UNKNOWN"
    elif mutation == "unknown_trigger_constraint":
        next(r for r in data["Q14"] if r[0] == "trigger" and not r[5])[8] = "UNKNOWN"
    else:
        data["Q2"][0][7] = "01001"
    with pytest.raises(Unavailable): make_policy(data)


def parameter_fixture(data):
    key = ["synthetic_parameter", "99100"]
    data["Q10"].extend([["object", "parameter", key, None, "explicit", 1],
                        ["grant", "parameter", key, "100", "9000", "SET", False]])
    for subject in ("runtime", "verifier"):
        for privilege in ("SET", "ALTER SYSTEM"):
            data["Q9"].append(["parameter", subject, key[0], privilege, False, False])
    return key


def test_fix1_03_parameter_acl_provenance_is_not_lost_when_rights_are_unchanged():
    data = raw_catalog(); parameter_fixture(data)
    policy = make_policy(data); assert harness(policy)[0]().connected
    header = next(r for r in data["Q10"] if r[:2] == ["object", "parameter"])
    header[5] += 1
    data["Q10"].append(["grant", "parameter", list(header[2]), "9001", "9000", "SET", False])
    assert make_policy(data, target=policy.target).approved_digest != policy.approved_digest
    adapter, batches, *_ = harness(policy); batches[("verifier", "Q10")] = Batch(data["Q10"])
    install_batches(adapter, batches)
    with pytest.raises(Unavailable): adapter()


@pytest.mark.parametrize("mutation", ["missing_header", "unknown_acl", "missing_effective_cell", "privileged_runtime", "invented_owner"])
def test_fix1_03_parameter_acl_requires_complete_known_provenance(mutation):
    data = raw_catalog(); key = parameter_fixture(data)
    header = next(r for r in data["Q10"] if r[:2] == ["object", "parameter"])
    if mutation == "missing_header": data["Q10"].remove(header)
    elif mutation == "unknown_acl": header[4] = "unknown"
    elif mutation == "missing_effective_cell": data["Q9"].remove(next(r for r in data["Q9"] if r[0] == "parameter"))
    elif mutation == "privileged_runtime": next(r for r in data["Q10"] if r[:2] == ["grant", "parameter"])[4] = "1001"
    else: header[3] = "100"
    with pytest.raises(Unavailable): make_policy(data)


class Fix2ReleaseFault:
    """In-memory lock fault: never claims recovery of a real threading.Lock."""
    def __init__(self, runtime, verifier, error, *, released=False):
        self.runtime, self.verifier, self.error = runtime, verifier, error
        self.released = released
        self.held = False
        self.releases = 0
        self.cleanup_at_release = None

    def acquire(self, *, blocking):
        assert blocking is False
        if self.held:
            return False
        self.held = True
        return True

    def release(self):
        self.releases += 1
        self.cleanup_at_release = (list(self.runtime.events), list(self.verifier.events))
        if self.released:
            self.held = False
        raise self.error


@pytest.mark.parametrize("primary_type", [KeyboardInterrupt, SystemExit, RuntimeError])
def test_fix2_scope_preserves_exact_primary_when_release_also_fails(primary_type):
    adapter, _, runtime, verifier, _ = harness()
    lock = Fix2ReleaseFault(runtime, verifier, RuntimeError("sensitive release detail"))
    adapter._scope.lock = lock
    primary = primary_type("synthetic primary")
    with pytest.raises(primary_type) as caught:
        with adapter._hold_scope():
            raise primary
    assert caught.value is primary
    assert caught.value.__notes__ == [
        "Readiness lock release failed; lock state is unknown; scope invalidated."]
    assert lock.releases == 1 and lock.held
    assert adapter._scope.invalidated
    assert "sensitive release detail" not in repr(caught.value.__notes__)


@pytest.mark.parametrize("primary_type", [KeyboardInterrupt, SystemExit])
@pytest.mark.parametrize("method", ["rollback", "close"])
def test_fix2_cleanup_interruption_survives_release_fault(primary_type, method):
    adapter, _, runtime, verifier, _ = harness()
    lock = Fix2ReleaseFault(runtime, verifier, RuntimeError("sensitive release detail"))
    adapter._scope.lock = lock
    primary = primary_type("synthetic cancellation")
    def fail():
        verifier.events.append(method)
        raise primary
    setattr(verifier, method, fail)
    with pytest.raises(primary_type) as caught:
        adapter()
    assert caught.value is primary
    assert "lock release failed" in caught.value.__notes__[0]
    assert lock.cleanup_at_release == (
        ["begin", "rollback", "close"], ["begin", "rollback", "close"])
    assert lock.releases == 1 and lock.held and adapter._scope.invalidated


@pytest.mark.parametrize("fault", ["operation", "rollback", "close", "both_resources"])
def test_fix2_common_failures_stay_sanitized_and_preserve_outward_primary(monkeypatch, fault):
    import app.readiness_postgres.adapter as module
    adapter, _, runtime, verifier, _ = harness()
    lock = Fix2ReleaseFault(runtime, verifier, RuntimeError("sensitive release detail"))
    adapter._scope.lock = lock
    primary = Unavailable()
    # Existing contract sanitizes ordinary driver exceptions before propagation.
    monkeypatch.setattr(module, "Unavailable", Mock(return_value=primary))
    if fault == "operation":
        verifier.failure = "begin"
    elif fault == "both_resources":
        runtime.failure = "rollback"
        verifier.failure = "close"
    else:
        verifier.failure = fault
    with pytest.raises(Unavailable) as caught:
        adapter()
    assert caught.value is primary
    assert str(caught.value) == "Readiness unavailable"
    assert "lock release failed" in caught.value.__notes__[0]
    assert caught.value.__cause__ is None and caught.value.__context__ is None
    assert lock.cleanup_at_release == (
        ["begin", "rollback", "close"], ["begin", "rollback", "close"])
    assert lock.releases == 1 and adapter._scope.invalidated


@pytest.mark.parametrize("secondary_type", [RuntimeError, KeyboardInterrupt, SystemExit])
def test_fix2_release_failure_without_primary_never_returns_observation(secondary_type):
    adapter, _, runtime, verifier, _ = harness()
    secondary = secondary_type("sensitive release detail")
    lock = Fix2ReleaseFault(runtime, verifier, secondary)
    adapter._scope.lock = lock
    expected = Unavailable if secondary_type is RuntimeError else secondary_type
    with pytest.raises(expected) as caught:
        adapter()
    if secondary_type is RuntimeError:
        assert str(caught.value) == "Readiness unavailable"
        assert caught.value.__cause__ is None and caught.value.__context__ is None
    else:
        assert caught.value is secondary
    assert caught.value.__notes__ == [
        "Readiness lock release failed; lock state is unknown; scope invalidated."]
    assert lock.cleanup_at_release == (
        ["begin", "rollback", "close"], ["begin", "rollback", "close"])
    assert lock.releases == 1 and adapter._scope.invalidated


@pytest.mark.parametrize("secondary_type", [KeyboardInterrupt, SystemExit])
def test_fix2_secondary_cancellation_does_not_replace_primary(secondary_type):
    adapter, _, runtime, verifier, _ = harness()
    adapter._scope.lock = Fix2ReleaseFault(runtime, verifier, secondary_type("secondary"))
    primary = KeyboardInterrupt("primary")
    with pytest.raises(KeyboardInterrupt) as caught:
        with adapter._hold_scope():
            raise primary
    assert caught.value is primary
    assert "lock release failed" in caught.value.__notes__[0]
    assert adapter._scope.lock.releases == 1


def test_fix2_released_then_failed_lock_still_invalidates_shared_scope():
    adapter, _, runtime, verifier, _ = harness()
    other, *_ = harness(adapter.policy)
    lock = Fix2ReleaseFault(runtime, verifier, RuntimeError("release failed"), released=True)
    adapter._scope.lock = lock
    with pytest.raises(Unavailable):
        adapter()
    assert not lock.held and lock.releases == 1
    assert other._scope is adapter._scope and other._scope.invalidated
    with pytest.raises(Unavailable):
        other()
    assert not other._runtime_factory.called and not other._verifier_factory.called
    assert lock.releases == 2  # One release per successful acquisition, no retry.


def test_fix2_failed_acquisition_does_not_release_someone_elses_lock():
    adapter, _, runtime, verifier, _ = harness()
    lock = Fix2ReleaseFault(runtime, verifier, RuntimeError("must not release"))
    adapter._scope.lock = lock
    lock.held = True
    with pytest.raises(Unavailable):
        adapter()
    assert lock.releases == 0 and lock.held
    assert not adapter._runtime_factory.called and not adapter._verifier_factory.called


def test_fix2_revalidation_release_failure_cannot_clear_failure_latch():
    adapter, _, runtime, verifier, _ = harness()
    adapter._scope.invalidated = True
    lock = Fix2ReleaseFault(runtime, verifier, RuntimeError("release failed"), released=True)
    adapter._scope.lock = lock
    with pytest.raises(Unavailable) as caught:
        adapter.revalidate(adapter.policy)
    assert adapter._scope.invalidated and lock.releases == 1
    assert "lock release failed" in caught.value.__notes__[0]
    assert not adapter._runtime_factory.called and not adapter._verifier_factory.called


def test_fix2_annotation_failure_cannot_mask_primary():
    class NoNotes(KeyboardInterrupt):
        def __setattr__(self, name, value):
            if name == "__notes__":
                raise RuntimeError("cannot annotate")
            super().__setattr__(name, value)
    adapter, _, runtime, verifier, _ = harness()
    adapter._scope.lock = Fix2ReleaseFault(runtime, verifier, RuntimeError("release failed"))
    primary = NoNotes("synthetic cancellation")
    with pytest.raises(NoNotes) as caught:
        with adapter._hold_scope():
            raise primary
    assert caught.value is primary and adapter._scope.lock.releases == 1
    assert adapter._scope.invalidated


def test_fix2_normal_lock_preserves_success_and_original_exception():
    adapter, _, runtime, verifier, _ = harness()
    primary = RuntimeError("synthetic primary")
    with pytest.raises(RuntimeError) as caught:
        with adapter._hold_scope():
            raise primary
    assert caught.value is primary and not hasattr(primary, "__notes__")
    assert not adapter._scope.lock.locked() and not adapter._scope.invalidated
    assert adapter().connected is True
    assert not adapter._scope.lock.locked()
