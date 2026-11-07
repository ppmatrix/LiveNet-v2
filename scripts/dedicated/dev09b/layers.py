"""Closed outer layer schemas and fixed expectation snapshots, offline only.

Structural hashes are not approved expectations. Full catalog support remains
Unsupported. No opaque detailed-catalog payload or observation-derived policy.
"""
from dataclasses import dataclass
from hashlib import sha256

from . import codec as c
from .profiles import validate_profile_reference, validate_inventory_projection, require_complete_profile


APP_REVISIONS = ("af62df027d9d", "4f625db33d6d", "38d641dcd780", "da34876e4210", "ba06dd956da9",
                 "44e7eb855b5a", "7c4e2a91b605", "9e1b7c42a630", "c4a91e7b205d", "e65b01a7c230",
                 "f065c01a7230", "f065d01a7230", "f066a01a7230")
LEDGERS = {"application": "alembic_version", "security": "alembic_security_version"}


def name(value):
    c.matching(value, r"[a-z_][a-z0-9_]{0,62}")


def revision(value):
    c.matching(value, r"[a-z0-9]{1,32}")


def path(value):
    c.require(type(value) is str and value.isascii() and bool(value))
    c.require(not value.startswith("/") and "\\" not in value)
    c.require(all(part not in {"", ".", ".."} for part in value.split("/")))
    c.require(not any(ord(ch) < 32 or ord(ch) == 127 for ch in value))


def ordered_set(values, key, validator):
    c.require(type(values) is list)
    for value in values:
        validator(value)
    keys = [key(v) for v in values]
    c.require(len(keys) == len(set(keys)) and keys == sorted(keys))


def source(s):
    c.closed(s, {"path", "sha256"})
    path(s["path"])
    c.digest_text(s["sha256"])


def sources(values):
    ordered_set(values, lambda s: s["path"], source)


def document_hash(obj):
    """Reference to a closed document: SHA256 of its DEV09B canonical bytes."""
    return sha256(c.canonical(obj)).hexdigest()


def revision_state(s, chain):
    c.closed(s, {"ledger_schema", "ledger_name", "presence", "revisions"})
    c.require(s["ledger_schema"] == "public" and s["ledger_name"] == LEDGERS[chain])
    c.require(type(s["presence"]) is str and s["presence"] in {"ABSENT", "PRESENT"})
    ordered_set(s["revisions"], lambda x: x, revision)
    c.require(s["presence"] != "ABSENT" or not s["revisions"])


def state(s):
    c.closed(s, {"application", "security"})
    for chain in LEDGERS:
        revision_state(s[chain], chain)


def validate_semantic(s):
    c.closed(s, {"schema_version", "operation", "before", "after", "installation_chain"})
    c.integer(s["schema_version"], 1, 1)
    c.require(type(s["operation"]) is str and s["operation"] in c.OPS)
    for phase in ("before", "after"):
        state(s[phase])
    # Exact approved origins/destinations; PRESENT-empty remains structurally
    # distinct but cannot be used as an expected migration origin here.
    expected = ({"before": (None, None), "after": ("f066a01a7230", None)}
                if s["operation"].startswith("application-") else
                {"before": ("f066a01a7230", None), "after": ("f066a01a7230", "b12b01a7230")})
    for phase, revisions in expected.items():
        for chain, rev in zip(LEDGERS, revisions):
            row = s[phase][chain]
            c.require(row["presence"] == ("ABSENT" if rev is None else "PRESENT"))
            c.require(row["revisions"] == ([] if rev is None else [rev]))
    chain = "application" if s["operation"].startswith("application-") else "security"
    wanted = APP_REVISIONS if chain == "application" else ("b12b01a7230",)
    c.require(type(s["installation_chain"]) is list and len(s["installation_chain"]) == len(wanted))
    paths = set()
    previous = None
    for migration, rev in zip(s["installation_chain"], wanted):
        c.closed(migration, {"chain", "revision", "down_revision", "source_path", "source_sha256"})
        c.require(migration["chain"] == chain and migration["revision"] == rev and migration["down_revision"] == previous)
        path(migration["source_path"])
        c.digest_text(migration["source_sha256"])
        c.require(migration["source_path"] not in paths)
        paths.add(migration["source_path"])
        previous = rev


def relation(r):
    c.closed(r, {"schema", "name", "kind"})
    name(r["schema"]); name(r["name"])
    c.require(type(r["kind"]) is str and r["kind"] in {"r", "p", "v", "m", "S", "f"})


def catalog(cat):
    c.closed(cat, {"profile", "validator_inventory", "schemas", "relations", "detailed_catalog"})
    sources(cat["validator_inventory"])
    ordered_set(cat["schemas"], lambda x: x, name)
    ordered_set(cat["relations"], lambda r: (r["schema"], r["name"]), relation)
    c.require(all(r["schema"] in cat["schemas"] for r in cat["relations"]))
    c.closed(cat["detailed_catalog"], {"profile"})
    validate_profile_reference(cat)


def validate_physical(p):
    c.closed(p, {"schema_version", "target_binding_sha256", "before", "after", "privilege_plan_sha256", "exclusivity_plan_sha256"})
    c.integer(p["schema_version"], 1, 1)
    for key in ("target_binding_sha256", "privilege_plan_sha256", "exclusivity_plan_sha256"):
        c.digest_text(p[key])
    for phase in ("before", "after"):
        catalog(p[phase])
        validate_inventory_projection(p[phase])


def validate_provenance(p):
    c.closed(p, {"schema_version", "producer_id", "producer_version", "producer_sha256", "source_inventory", "tool_inventory", "generation_id"})
    c.integer(p["schema_version"], 1, 1)
    c.identifier(p["producer_id"]); c.identifier(p["producer_version"])
    c.digest_text(p["producer_sha256"]); c.uuid(p["generation_id"])
    sources(p["source_inventory"])
    def tool(t):
        c.closed(t, {"name", "version", "artifact_sha256"})
        c.identifier(t["name"]); c.identifier(t["version"]); c.digest_text(t["artifact_sha256"])
    ordered_set(p["tool_inventory"], lambda t: t["name"], tool)


def expected_hash(semantic, physical, phase):
    c.require(phase in {"before", "after"})
    return document_hash({"state": semantic[phase], "catalog": physical[phase]})


@dataclass(frozen=True)
class ExpectationSnapshot:
    """Immutable supplied expectations, NOT proof of prior human approval."""
    payload: bytes
    target: bytes
    executor: bytes
    plan: bytes
    semantic: bytes
    physical: bytes
    provenance: bytes


def freeze_expectations(payload, target, executor, plan, semantic, physical, provenance):
    """No observation argument: retain independent, immutable expected bytes.

    The caller must supply previously approved expectations. This pure check
    cannot prove their authorship, approval or chronology.
    """
    c.inspect_bindings(payload, target, executor, plan)
    validate_semantic(semantic); validate_physical(physical); validate_provenance(provenance)
    c.require(semantic["operation"] == payload["operation"])
    c.require(physical["target_binding_sha256"] == payload["target_binding_sha256"])
    for key in ("privilege_plan_sha256", "exclusivity_plan_sha256"):
        c.require(physical[key] == plan[key])
    wanted_profiles = (("auth03-base-inventory-v1", "m12b-f066-inventory-v1")
                       if semantic["operation"].startswith("application-") else
                       ("m12b-f066-inventory-v1", "m12b-b12-inventory-v1"))
    prepared_profiles=(("dev09b-prepared-base-v1","dev09b-prepared-f066-v1")
                       if semantic["operation"].startswith("application-") else
                       ("dev09b-prepared-f066-v1","dev09b-prepared-b12-v1"))
    c.require(tuple(physical[k]["profile"] for k in ("before", "after")) in {wanted_profiles,prepared_profiles})
    for phase in ("before", "after"):
        c.require(plan["expected_"+phase+"_sha256"] == expected_hash(semantic, physical, phase))
    c.require(plan["migration_sources_sha256"] == document_hash(semantic["installation_chain"]))
    c.require(executor["source_inventory_sha256"] == document_hash(provenance["source_inventory"]))
    inventory = {s["path"]: s["sha256"] for s in provenance["source_inventory"]}
    for migration in semantic["installation_chain"]:
        c.require(inventory.get(migration["source_path"]) == migration["source_sha256"])
    for phase in ("before", "after"):
        for s in physical[phase]["validator_inventory"]:
            c.require(inventory.get(s["path"]) == s["sha256"])
    global_doc = {"schema_version": 1, **{k+"_sha256": c.digest(k, obj) for k, obj in
                  (("semantic", semantic), ("physical", physical), ("provenance", provenance))}}
    c.require(c.digest("global", global_doc) == payload["global_digest_sha256"])
    return ExpectationSnapshot(*(c.canonical(x) for x in (payload,target,executor,plan,semantic,physical,provenance)))


def validate_complete_layers(snapshot):
    c.require(type(snapshot) is ExpectationSnapshot)
    # Revalidate hashes even if someone constructs a snapshot directly.
    freeze_expectations(*(c.parse(getattr(snapshot,k)) for k in
                          ("payload","target","executor","plan","semantic","physical","provenance")))
    physical = c.parse(snapshot.physical)
    for phase in ("before", "after"):
        require_complete_profile(physical[phase]["profile"])
