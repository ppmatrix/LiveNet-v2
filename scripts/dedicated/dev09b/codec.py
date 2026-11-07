"""Closed DEV09B-1 schemas and a restricted, integer-only RFC 8785 domain.

Signature/integrity observations NEVER authorize an operation. Semantic,
physical and provenance layers lack complete schemas and are unsupported.
No R1/R2/G4 compatibility, approval issuance, secrets, I/O or fallback crypto.
"""
from dataclasses import dataclass
from hashlib import sha256
from ipaddress import ip_address
import json
import re
from uuid import UUID


class Invalid(ValueError):
    pass


class Unsupported(Invalid):
    pass


class CryptoUnavailable(Invalid):
    pass


MAX_INT = 2**53 - 1
DOMAIN = b"LiveNet/DEV09B/approval/v1\x00"
OPS = {
    "application-base-to-f066a01a7230": ("base", "f066a01a7230", "base", "unchanged"),
    "security-base-to-b12b01a7230": ("f066a01a7230", "unchanged", "base", "b12b01a7230"),
}
PAYLOAD = frozenset("protocol_version signature_algorithm issuer_id key_id trust_policy_version approval_id request_id attempt_id approver_id requester_id executor_id audience environment vm_generation_id target_binding_sha256 global_digest_sha256 operation gate purpose execution_plan_sha256 issued_at not_before expires_at authority_epoch revocation_epoch".split())
TARGET = frozenset("schema_version environment vm_generation_id cluster_generation_id database_name system_identifier host port tls_server_name ca_sha256 server_certificate_sha256 migrator_role inspector_role instance_id network_id storage_id image_sha256".split())
EXECUTOR = frozenset("schema_version executor_id incarnation_id image_sha256 source_inventory_sha256 dependency_lock_sha256 configuration_sha256 supervision_policy_sha256".split())
PLAN = frozenset("schema_version operation application_from application_to security_from security_to target_binding_sha256 executor_binding_sha256 migration_sources_sha256 expected_before_sha256 expected_after_sha256 privilege_plan_sha256 exclusivity_plan_sha256 recovery_plan_sha256 limits_sha256 prerequisite_evidence_sha256".split())
GLOBAL = frozenset("schema_version semantic_sha256 physical_sha256 provenance_sha256".split())


def require(ok):
    if not ok:
        raise Invalid("Invalid DEV09B-1 contract")


def integer(v, low=0, high=MAX_INT):
    require(type(v) is int and low <= v <= high)


def matching(v, pattern):
    require(type(v) is str and re.fullmatch(pattern, v, flags=re.ASCII) is not None)


def identifier(v):
    matching(v, r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")


def uuid(v):
    require(type(v) is str)
    try:
        require(str(UUID(v)) == v)
    except (ValueError, AttributeError):
        raise Invalid("Invalid UUID") from None


def digest_text(v):
    matching(v, r"[0-9a-f]{64}")


def decimal64(v):
    matching(v, r"[1-9][0-9]{0,19}")
    require(int(v) <= 2**64 - 1)


def closed(obj, fields):
    require(type(obj) is dict and set(obj) == fields)


def _tree(v, depth=0):
    require(depth <= 8)
    if type(v) is str:
        try:
            v.encode("utf-8", errors="strict")
        except UnicodeError:
            raise Invalid("Invalid Unicode") from None
    elif type(v) is int:
        integer(v, -MAX_INT)
    elif v is None or type(v) is bool:
        pass
    elif type(v) is list:
        for x in v:
            _tree(x, depth + 1)
    elif type(v) is dict:
        for k, x in v.items():
            require(type(k) is str)
            _tree(k, depth + 1)
            _tree(x, depth + 1)
    else:
        raise Invalid("Unsupported JSON type")


def canonical(obj):
    """JCS for the explicitly supported no-floats, safe-integer domain.

    UTF-16 code-unit property ordering is essential; Python sort_keys is NOT JCS.
    No Unicode normalization is performed.
    """
    _tree(obj)

    def encode(v):
        if type(v) is dict:
            keys = sorted(v, key=lambda k: k.encode("utf-16-be"))
            return "{" + ",".join(encode(k) + ":" + encode(v[k]) for k in keys) + "}"
        if type(v) is list:
            return "[" + ",".join(encode(x) for x in v) + "]"
        return json.dumps(v, ensure_ascii=False, allow_nan=False, separators=(",", ":"))

    return encode(obj).encode("utf-8")


def parse(raw, maximum=32768):
    require(type(raw) is bytes and len(raw) <= maximum)

    def pairs(items):
        result = {}
        for k, v in items:
            require(k not in result)
            result[k] = v
        return result

    def reject(_):
        raise Invalid("Floats and nonfinite values are unsupported")

    try:
        obj = json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=pairs,
                         parse_float=reject, parse_constant=reject)
        _tree(obj)
        return obj
    except (UnicodeError, ValueError, RecursionError):
        raise Invalid("Invalid DEV09B-1 JSON") from None


def validate_payload(p):
    closed(p, PAYLOAD)
    for k, v in {"protocol_version": "DEV09B-1", "signature_algorithm": "Ed25519",
                 "audience": "LiveNet/DEV09B/migration-executor", "environment": "DEV",
                 "gate": "DEV09B", "purpose": "DEV-MVP-PERSISTENCE"}.items():
        require(p[k] == v)
    for k in "issuer_id key_id trust_policy_version approver_id requester_id executor_id".split():
        identifier(p[k])
    for k in "approval_id request_id attempt_id vm_generation_id".split():
        uuid(p[k])
    for k in "target_binding_sha256 global_digest_sha256 execution_plan_sha256".split():
        digest_text(p[k])
    for k in "issued_at not_before expires_at".split():
        integer(p[k])
    for k in "authority_epoch revocation_epoch".split():
        integer(p[k], 1)
    require(type(p["operation"]) is str and p["operation"] in OPS)
    require(p["issued_at"] <= p["not_before"] < p["expires_at"]
            and p["expires_at"] - p["issued_at"] <= 900)
    require(len(canonical(p)) <= 16384)


def _hostname(v):
    require(type(v) is str and v.isascii() and v == v.lower() and len(v) <= 253 and "%" not in v)
    try:
        addr = ip_address(v)
    except ValueError:
        # Do not interpret malformed legacy numeric IP addresses as DNS names.
        require(not all(re.fullmatch(r"(?:[0-9]+|0x[0-9a-f]+)", x) for x in v.split(".")))
        require(all(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", x) for x in v.split(".")))
    else:
        require(str(addr) == v)


def validate_target(t):
    closed(t, TARGET)
    integer(t["schema_version"], 1, 1)
    require(t["environment"] == "DEV" and t["database_name"] == "livenet_v2_dev")
    for k in "vm_generation_id cluster_generation_id".split():
        uuid(t[k])
    decimal64(t["system_identifier"])
    integer(t["port"], 1, 65535)
    _hostname(t["host"])
    _hostname(t["tls_server_name"])
    for k in "ca_sha256 server_certificate_sha256 image_sha256".split():
        digest_text(t[k])
    for k in "migrator_role inspector_role".split():
        matching(t[k], r"[a-z_][a-z0-9_]{0,62}")
    for k in "instance_id network_id storage_id".split():
        require(type(t[k]) is str and 1 <= len(t[k]) <= 256 and t[k].isascii())
    canonical(t)


def validate_executor(e):
    closed(e, EXECUTOR)
    integer(e["schema_version"], 1, 1)
    identifier(e["executor_id"])
    uuid(e["incarnation_id"])
    for k in EXECUTOR - {"schema_version", "executor_id", "incarnation_id"}:
        digest_text(e[k])


def validate_plan(p):
    closed(p, PLAN)
    integer(p["schema_version"], 1, 1)
    require(type(p["operation"]) is str and p["operation"] in OPS)
    require(tuple(p[k] for k in "application_from application_to security_from security_to".split()) == OPS[p["operation"]])
    for k in PLAN:
        if k.endswith("_sha256"):
            digest_text(p[k])


def digest(kind, obj):
    validators = {"target": validate_target, "executor": validate_executor, "plan": validate_plan}
    if kind in {"semantic", "physical", "provenance"}:
        raise Unsupported("Layer schema incomplete; opaque hashes cannot establish support")
    if kind == "global":
        closed(obj, GLOBAL)
        integer(obj["schema_version"], 1, 1)
        for k in GLOBAL - {"schema_version"}:
            digest_text(obj[k])
    elif kind in validators:
        validators[kind](obj)
    else:
        raise Unsupported("Unsupported digest type")
    return sha256(b"LiveNet/DEV09B-1/" + kind.encode("ascii") + b"\x00" + canonical(obj)).hexdigest()


def signed_bytes(payload):
    validate_payload(payload)
    return DOMAIN + canonical(payload)


@dataclass(frozen=True)
class SignatureObservation:
    """Immutable signature observation, not trust, admission or execution permission."""
    payload_json: bytes


def verify_ed25519(public_key, signature, message):
    require(type(public_key) is bytes and len(public_key) == 32)
    require(type(signature) is bytes and len(signature) == 64 and type(message) is bytes)
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        from cryptography.exceptions import InvalidSignature
    except ImportError:
        raise CryptoUnavailable("cryptography unavailable; no cryptographic fallback") from None
    try:
        Ed25519PublicKey.from_public_bytes(public_key).verify(signature, message)
    except (InvalidSignature, ValueError):
        raise Invalid("Invalid signature") from None


def verify_envelope(raw, public_key):
    env = parse(raw)
    closed(env, {"payload", "signature_hex"})
    matching(env["signature_hex"], r"[0-9a-f]{128}")
    message = signed_bytes(env["payload"])
    verify_ed25519(public_key, bytes.fromhex(env["signature_hex"]), message)
    return SignatureObservation(canonical(env["payload"]))


def inspect_bindings(payload, target, executor, plan):
    """Integrity only. Does not validate catalog evidence or authorize anything."""
    validate_payload(payload)
    validate_target(target)
    validate_executor(executor)
    validate_plan(plan)
    require(digest("target", target) == payload["target_binding_sha256"] == plan["target_binding_sha256"])
    require(digest("executor", executor) == plan["executor_binding_sha256"])
    require(digest("plan", plan) == payload["execution_plan_sha256"])
    require(payload["executor_id"] == executor["executor_id"])
    require(payload["operation"] == plan["operation"])
    require(payload["vm_generation_id"] == target["vm_generation_id"])


def validate_layers(*_args, **_kwargs):
    raise Unsupported("Semantic/physical/provenance schemas incomplete; full manifest unsupported")
