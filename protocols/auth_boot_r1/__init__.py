"""R1-PROTO-01 structural validation, using a NOT-APPROVED candidate profile.

Successful parsing is not JCS validation, signature verification, eligibility,
identity attestation, an authorization, or permission to invoke an executor.
Only Python's standard library is used. No I/O is performed by this module.
"""

from dataclasses import dataclass, field
import json
import re
from types import MappingProxyType
from typing import Mapping


PAYLOAD_FIELDS = (
    "protocol_version", "signature_algorithm", "issuer_id", "key_id",
    "trust_policy_version", "approval_id", "request_id", "attempt_id",
    "approver_id", "requester_id", "executor_id", "audience", "environment",
    "vm_generation_id", "target_binding_sha256", "global_digest_sha256",
    "operation", "gate", "purpose", "execution_plan_sha256", "issued_at",
    "not_before", "expires_at", "authority_epoch", "revocation_epoch",
)
MAX_ENVELOPE_BYTES = 32 * 1024
MAX_PAYLOAD_BYTES = 16 * 1024
MAX_DEPTH = 8
SIGNING_DOMAIN = b"LiveNet/AUTH-BOOT-02-R1/approval/v1\x00"
CANDIDATE_PROFILE = "R1-PROTO-01-CANDIDATE-1"

_DIGEST_FIELDS = frozenset((
    "target_binding_sha256", "global_digest_sha256", "execution_plan_sha256",
))
_DECIMAL_FIELDS = frozenset((
    "trust_policy_version", "issued_at", "not_before", "expires_at",
    "authority_epoch", "revocation_epoch",
))
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_HEX128 = re.compile(r"[0-9a-f]{128}\Z")
_DECIMAL = re.compile(r"(?:0|[1-9][0-9]{0,19})\Z")
_TOKEN = re.compile(r"[\x21-\x7e]{1,128}\Z")


class StructuralError(ValueError):
    """Fixed code only; untrusted input is never included in diagnostics."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class ParsedCandidateEnvelope:
    """Structural data, deliberately without an authorization/valid flag."""

    payload: Mapping[str, str] = field(repr=False)
    signature_hex: str = field(repr=False)
    profile: str = field(default=CANDIDATE_PROFILE, init=False)

    def __post_init__(self):
        # Detach the result from mutable caller/decoder dictionaries.
        object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))


def _fail(code):
    raise StructuralError(code)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _fail("DUPLICATE_FIELD")
        result[key] = value
    return result


def _constant(_value):
    _fail("NON_JSON_CONSTANT")


def _check_depth(text):
    """Bound nesting before json.loads; braces inside strings do not count."""
    depth = 0
    quoted = escaped = False
    for char in text:
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in "[{":
            depth += 1
            if depth > MAX_DEPTH:
                _fail("DEPTH_LIMIT")
        elif char in "}]":
            depth -= 1
    # Full syntax (including mismatched brackets) is checked by the JSON parser.


def _check_unicode(value):
    if isinstance(value, str):
        if any(0xD800 <= ord(char) <= 0xDFFF for char in value):
            _fail("INVALID_UNICODE")
    elif isinstance(value, dict):
        for key, item in value.items():
            _check_unicode(key)
            _check_unicode(item)
    elif isinstance(value, list):
        for item in value:
            _check_unicode(item)


def _payload_wire_size(text):
    """Size of the original payload JSON value, without reserialization/JCS.

    Called only after syntax, duplicates, depth and root shape were checked.
    raw_decode handles escaped root property names and either property order.
    """
    decoder = json.JSONDecoder()
    pos = text.index("{") + 1
    while True:
        while text[pos] in " \t\r\n":
            pos += 1
        key, pos = decoder.raw_decode(text, pos)
        while text[pos] in " \t\r\n":
            pos += 1
        pos += 1  # colon, already syntax checked
        while text[pos] in " \t\r\n":
            pos += 1
        start = pos
        _, pos = decoder.raw_decode(text, pos)
        if key == "payload":
            return len(text[start:pos].encode("utf-8"))
        while text[pos] in " \t\r\n":
            pos += 1
        pos += 1  # comma; exact root keys guarantee payload is next


def parse_candidate_envelope(raw: bytes) -> ParsedCandidateEnvelope:
    """Parse UTF-8 wire bytes under the explicitly candidate structural profile.

    No canonicalization or signature check; no clock, trust store or I/O.
    Candidate-specific choices are listed in README.md beside this module.
    """
    if type(raw) is not bytes:
        _fail("BYTES_REQUIRED")
    if len(raw) > MAX_ENVELOPE_BYTES:
        _fail("ENVELOPE_LIMIT")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        raise StructuralError("INVALID_UTF8") from None
    _check_depth(text)
    try:
        value = json.loads(text, object_pairs_hook=_pairs, parse_constant=_constant)
    except StructuralError:
        raise
    except (ValueError, RecursionError):
        raise StructuralError("INVALID_JSON") from None
    _check_unicode(value)
    if type(value) is not dict or set(value) != {"payload", "signature_hex"}:
        _fail("ENVELOPE_FIELDS")
    payload = value["payload"]
    if type(payload) is not dict or set(payload) != set(PAYLOAD_FIELDS):
        _fail("PAYLOAD_FIELDS")
    if _payload_wire_size(text) > MAX_PAYLOAD_BYTES:
        _fail("PAYLOAD_LIMIT")
    signature = value["signature_hex"]
    if type(signature) is not str or not _HEX128.fullmatch(signature):
        _fail("SIGNATURE_HEX")
    if any(type(item) is not str for item in payload.values()):
        _fail("FIELD_TYPE")
    if payload["protocol_version"] != "1":
        _fail("PROTOCOL_VERSION")
    if payload["signature_algorithm"] != "Ed25519":
        _fail("SIGNATURE_ALGORITHM")
    for name in _DIGEST_FIELDS:
        if not _HEX64.fullmatch(payload[name]):
            _fail("DIGEST_HEX")
    for name in _DECIMAL_FIELDS:
        if not _DECIMAL.fullmatch(payload[name]):
            _fail("DECIMAL_FORMAT")
    for name in set(PAYLOAD_FIELDS) - _DIGEST_FIELDS - _DECIMAL_FIELDS - {
        "protocol_version", "signature_algorithm",
    }:
        if not _TOKEN.fullmatch(payload[name]):
            _fail("TOKEN_FORMAT")
    issued, not_before, expires = (
        int(payload[name]) for name in ("issued_at", "not_before", "expires_at")
    )
    if not (issued <= not_before < expires and expires - issued <= 900):
        _fail("TIME_RELATION")
    return ParsedCandidateEnvelope(payload, signature)
