"""DEV09B-PREPARED-1 preconditions, never provisioning or execution authority.

No SQL, connection, environment discovery or positive operational adapter here.
The future guarded executor must inject a trusted live inspection/approval port.
An Alembic config string, digest or offline observation is NOT that port.
"""
from dataclasses import dataclass
from hashlib import sha256
import json
import re
from typing import Protocol


PROFILE = "DEV09B-PREPARED-1"
ATTR = "dev09b_prepared_context"
SCHEMAS = frozenset({"inventory", "audit", "security"})


class PrerequisiteRefused(ValueError):
    pass


class MissingParameter(PrerequisiteRefused):
    def __init__(self, path):
        self.path = path
        super().__init__("MissingParameter: " + path)


def require(condition, message="DEV09B prepared prerequisite divergence"):
    if not condition: raise PrerequisiteRefused(message)


@dataclass(frozen=True)
class ProfileAttestation:
    profile_sha256: str
    target_sha256: str
    bundle_sha256: str
    operationally_authenticated: bool
    classification: str


class PreparedPort(Protocol):
    """Trusted injection; a real implementation needs separate authorization."""
    def verify_approved_profile(self, profile_json: bytes) -> ProfileAttestation: ...
    def observe(self, profile_json: bytes, requested: str) -> dict: ...


@dataclass(frozen=True)
class PreparedContext:
    profile_json: bytes
    port: PreparedPort


def decode_profile(raw):
    require(type(raw) is bytes and len(raw)<=32768)
    def pairs(rows):
        d={}
        for k,v in rows:
            require(k not in d);d[k]=v
        return d
    try: p=json.loads(raw.decode("utf-8"),object_pairs_hook=pairs)
    except (UnicodeError,ValueError):raise PrerequisiteRefused("Invalid prepared profile") from None
    fields={"profile","operation","target_sha256","bundle_sha256","database","system_identifier","migrator",
            "schema_owners","btree_gist","source_inventory_sha256"}
    require(type(p) is dict)
    missing=sorted(fields-set(p))
    if missing:raise MissingParameter("prepared_profile."+missing[0])
    require(set(p)==fields and p["profile"]==PROFILE)
    require(p["operation"] in {"application-base-to-f066a01a7230","security-base-to-b12b01a7230"})
    require(p["database"]=="livenet_v2_dev")
    for k in ("target_sha256","bundle_sha256","source_inventory_sha256"):
        require(type(p[k]) is str and len(p[k])==64 and all(ch in "0123456789abcdef" for ch in p[k]))
    for k in ("system_identifier","migrator"):
        if type(p[k]) is not str or not p[k]:raise MissingParameter("prepared_profile."+k)
    require(re.fullmatch(r"[1-9][0-9]{0,19}",p["system_identifier"]) is not None and int(p["system_identifier"])<=2**64-1)
    require(re.fullmatch(r"[a-z_][a-z0-9_]{0,62}",p["migrator"]) is not None)
    require(type(p["schema_owners"]) is dict and set(p["schema_owners"])==SCHEMAS)
    for v in p["schema_owners"].values():require(type(v) is str and bool(v) and v!=p["migrator"])
    require(len(set(p["schema_owners"].values()))==3)
    ext=p["btree_gist"]
    require(type(ext) is dict)
    for k in ("version","schema","owner","members_sha256","acl_sha256"):
        if k not in ext or type(ext[k]) is not str or not ext[k]:raise MissingParameter("prepared_profile.btree_gist."+k)
    require(set(ext)=={"version","schema","owner","members_sha256","acl_sha256"} and ext["schema"]=="public" and ext["owner"]!=p["migrator"])
    for k in ("members_sha256","acl_sha256"):
        require(len(ext[k])==64 and all(ch in "0123456789abcdef" for ch in ext[k]))
    return p


def validate_observation(p,o,requested):
    """Pure supplied-record check; NEVER authenticates or authorizes execution."""
    require(type(o) is dict and set(o)=={"database","system_identifier","current_user","session_user","database_create",
            "database_temporary","database_owner","superuser","createdb","createrole","replication","bypassrls",
            "extension_install_power","memberships","schemas","extension","residual_objects",
            "schema_create","schema_usage","prior_application_confirmed","source_inventory_sha256"})
    require((o["database"],o["system_identifier"],o["current_user"],o["session_user"])==
            (p["database"],p["system_identifier"],p["migrator"],p["migrator"]))
    for k in ("database_create","database_temporary","database_owner","superuser","createdb","createrole","replication","bypassrls","extension_install_power"):
        require(o[k] is False,"DEV09B requires effective absence of database CREATE/TEMP/ownership/superuser")
    require(type(o["memberships"]) is list and not o["memberships"])
    require(type(o["residual_objects"]) is list and not o["residual_objects"])
    require(type(o["schemas"]) is dict and set(o["schemas"])==SCHEMAS)
    for name,owner in p["schema_owners"].items():
        row=o["schemas"][name]
        require(type(row) is dict and set(row)=={"owner","owner_login"})
        require(row["owner"]==owner and row["owner_login"] is False)
    require(type(o["extension"]) is dict and o["extension"]==p["btree_gist"])
    require(o["source_inventory_sha256"]==p["source_inventory_sha256"])
    require(type(o["schema_create"]) is list and all(type(x) is str for x in o["schema_create"])
            and len(set(o["schema_create"]))==len(o["schema_create"]))
    allowed={"inventory","audit","public"} if p["operation"].startswith("application-") else {"security","public"}
    require(set(o["schema_create"])==allowed)
    require(type(o["schema_usage"]) is list and all(type(x) is str for x in o["schema_usage"])
            and len(set(o["schema_usage"]))==len(o["schema_usage"]) and set(o["schema_usage"])==allowed)
    if p["operation"].startswith("security-"):
        require(o["prior_application_confirmed"] is True)
    else:require(o["prior_application_confirmed"] is False)
    if requested=="environment":return
    if requested in SCHEMAS:require(requested in allowed)
    else:require(requested=="btree_gist" and p["operation"].startswith("application-"))


def _require(requested, context=None):
    if context is None:
        from alembic import op
        context=op.get_context().config.attributes.get(ATTR)
    if type(context) is not PreparedContext:raise MissingParameter(ATTR)
    p=decode_profile(context.profile_json)
    if context.port is None or not all(callable(getattr(context.port,k,None)) for k in ("verify_approved_profile","observe")):
        raise MissingParameter("dev09b.live_prerequisite_and_approval_port")
    att=context.port.verify_approved_profile(context.profile_json)
    require(type(att) is ProfileAttestation and att.operationally_authenticated is True and att.classification=="OPERATIONAL",
            "Offline records/signatures/digests cannot approve a prepared migration profile")
    require(att.profile_sha256==sha256(context.profile_json).hexdigest() and att.target_sha256==p["target_sha256"]
            and att.bundle_sha256==p["bundle_sha256"])
    validate_observation(p,context.port.observe(context.profile_json,requested),requested)


def require_prepared_schema(schema, *, context=None):
    require(type(schema) is str and schema in SCHEMAS)
    _require(schema,context)


def require_prepared_extension(extension, *, context=None):
    require(extension=="btree_gist")
    _require(extension,context)


def require_prepared_environment(config):
    """Before Alembic configure/run_migrations (and automatic ledger creation)."""
    connection=config.attributes.get("connection")
    if connection is None:raise RuntimeError("DEV09B exige ligacao externa explicita e transacao ativa")
    require(connection.in_transaction() is True and connection.dialect.name=="postgresql")
    context=config.attributes.get(ATTR)
    if type(context) is not PreparedContext:raise MissingParameter(ATTR)
    _require("environment",context)


def refuse_prepared_downgrade():
    raise PrerequisiteRefused("DEV09B-PREPARED-1 initial installation only; downgrade is not authorized")
