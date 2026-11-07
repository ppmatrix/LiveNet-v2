"""Pinned, versioned inventory projections; NOT full migration profiles.

No import/execution of operational validators. The projections below reuse
their compatible inventory predicates only. Full base/ACL/ownership/catalog
coverage is incomplete and cannot confirm base, success or rollback.
"""
from types import MappingProxyType

from .codec import Unsupported, canonical, require


SOURCES = MappingProxyType({
    "scripts/postgres/auth03_alembic_executor.py": "66c18319414c29f49ae163ef86b098924592102b566cd894fd4824933704d00b",
    "scripts/postgres/m12b_security_migration.py": "c2608a2c8d0391dc3e5960fe797d4c8f77be5165475cb0058de4f66dd51ed9fe",
    "backend/security_migrations/contract.py": "0a29cbc074907a4b9023709a7a8770ea5a48e1d000bcd0197255d4dcf49fb41b",
    "backend/app/readiness_postgres/evaluate.py": "0137f9343672a95fc0138b9e6ac5207fdb23b468162dce65b5867fd2758210d5",
    "backend/app/readiness_postgres/policy.py": "7dc4100d063e4cb3c09957e8fb117f2b84fddc7b5b28f73f57422061042bff81",
    "backend/app/readiness_postgres/queries.py": "9ddad5dc61f2c5f81ca5db8e410064e506b9a93607b3f2cde3add86c3ad1ed2b",
})
PROFILES = MappingProxyType({
    "auth03-base-inventory-v1": ("scripts/postgres/auth03_alembic_executor.py",),
    "m12b-f066-inventory-v1": ("scripts/postgres/m12b_security_migration.py", "backend/security_migrations/contract.py"),
    "m12b-b12-inventory-v1": ("scripts/postgres/m12b_security_migration.py", "backend/security_migrations/contract.py"),
    "g2-f066-b12-d05-v1": ("backend/app/readiness_postgres/evaluate.py", "backend/app/readiness_postgres/policy.py", "backend/app/readiness_postgres/queries.py"),
})
INVENTORY = frozenset("resources resource_identifiers resource_relations groups group_memberships group_rules tags resource_tags policies policy_versions policy_assignments effective_configs".split())
SECURITY = frozenset("local_users login_sessions global_role_grants login_throttles".split())


def validator_inventory(profile):
    if type(profile) is not str or profile not in PROFILES:
        raise Unsupported("Unknown or unversioned DEV09B catalog profile")
    return [{"path": p, "sha256": SOURCES[p]} for p in sorted(PROFILES[profile])]


def validate_profile_reference(catalog):
    require(canonical(catalog["validator_inventory"]) == canonical(validator_inventory(catalog["profile"])))
    require(catalog["detailed_catalog"] == {"profile": catalog["profile"]})


def validate_inventory_projection(catalog):
    """Validate only the compatible inventory predicate, never full coverage."""
    from .layers import catalog as validate_catalog
    validate_catalog(catalog)
    validate_profile_reference(catalog)
    profile = catalog["profile"]
    schemas = {"public"}
    relations = set()
    if profile != "auth03-base-inventory-v1":
        schemas |= {"inventory", "audit"}
        relations |= {("inventory", n, "r") for n in INVENTORY}
        relations |= {("audit", "events", "r"), ("public", "alembic_version", "r")}
    if profile in {"m12b-b12-inventory-v1", "g2-f066-b12-d05-v1"}:
        schemas.add("security")
        relations |= {("security", n, "r") for n in SECURITY}
        relations.add(("public", "alembic_security_version", "r"))
    if profile == "g2-f066-b12-d05-v1":
        # G2's inventory projection includes these system schemas; the M1.2B
        # readers above explicitly filter them. They are not interchangeable.
        schemas |= {"pg_catalog", "information_schema", "pg_toast"}
    require(catalog["schemas"] == sorted(schemas))
    require({(r["schema"], r["name"], r["kind"]) for r in catalog["relations"]} == relations)


def require_complete_profile(profile):
    validator_inventory(profile)
    raise Unsupported("Detailed catalog/defaults/extensions/ownership/ACL profile not complete; cannot confirm migration")
