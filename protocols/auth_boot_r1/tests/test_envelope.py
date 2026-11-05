"""Offline structural/adversarial tests; no service or application fixtures."""

from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from protocols.auth_boot_r1 import (
    CANDIDATE_PROFILE, MAX_DEPTH, MAX_ENVELOPE_BYTES, MAX_PAYLOAD_BYTES,
    PAYLOAD_FIELDS, SIGNING_DOMAIN, StructuralError, parse_candidate_envelope,
)


EXPECTED_FIELDS = (
    "protocol_version", "signature_algorithm", "issuer_id", "key_id",
    "trust_policy_version", "approval_id", "request_id", "attempt_id",
    "approver_id", "requester_id", "executor_id", "audience", "environment",
    "vm_generation_id", "target_binding_sha256", "global_digest_sha256",
    "operation", "gate", "purpose", "execution_plan_sha256", "issued_at",
    "not_before", "expires_at", "authority_epoch", "revocation_epoch",
)


def wire(value):
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


class EnvelopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.example_raw = (Path(__file__).parents[1] / "example.json").read_bytes()

    def setUp(self):
        self.envelope = json.loads(self.example_raw)

    def refuse(self, raw, code=None):
        with self.assertRaises(StructuralError) as caught:
            parse_candidate_envelope(raw)
        if code:
            self.assertEqual(caught.exception.code, code)
        self.assertEqual(str(caught.exception), caught.exception.code)

    def payload_wire(self, size):
        payload = wire(self.envelope["payload"])
        padded = b"{" + b" " * (size - len(payload)) + payload[1:]
        self.assertEqual(len(padded), size)
        return b'{"payload":' + padded + b',"signature_hex":' + wire(self.envelope["signature_hex"]) + b'}'

    def test_approved_fields_and_domain(self):
        self.assertEqual(PAYLOAD_FIELDS, EXPECTED_FIELDS)
        self.assertEqual(len(set(PAYLOAD_FIELDS)), 25)
        self.assertEqual(SIGNING_DOMAIN, b"LiveNet/AUTH-BOOT-02-R1/approval/v1\x00")
        self.assertEqual((MAX_PAYLOAD_BYTES, MAX_ENVELOPE_BYTES, MAX_DEPTH), (16384, 32768, 8))

    def test_deterministic_example_is_structural_only(self):
        parsed = parse_candidate_envelope(self.example_raw)
        self.assertEqual(dict(parsed.payload), self.envelope["payload"])
        self.assertEqual(parsed.profile, CANDIDATE_PROFILE)
        # Fictitious signature is accepted structurally; not crypto validation.
        self.assertEqual(parsed.signature_hex, "0" * 128)
        self.assertFalse(hasattr(parsed, "authorized"))
        self.assertNotIn("example-human", repr(parsed))

    def test_result_is_immutable(self):
        parsed = parse_candidate_envelope(self.example_raw)
        with self.assertRaises(TypeError):
            parsed.payload["issuer_id"] = "replacement"
        with self.assertRaises(FrozenInstanceError):
            parsed.signature_hex = "f" * 128

    def test_wire_order_and_whitespace_need_not_be_canonical(self):
        reordered = dict(reversed(list(self.envelope.items())))
        self.assertEqual(dict(parse_candidate_envelope(b" \n" + wire(reordered) + b"\t").payload), self.envelope["payload"])

    def test_escaped_key_names_are_decoded(self):
        raw = wire(self.envelope).replace(b'"payload"', b'"paylo\\u0061d"')
        parse_candidate_envelope(raw)

    def test_bytes_only(self):
        for item in (self.example_raw.decode(), bytearray(self.example_raw), memoryview(self.example_raw), None, 1):
            with self.subTest(type=type(item).__name__):
                self.refuse(item, "BYTES_REQUIRED")

    def test_invalid_utf8(self):
        for raw in (b"\xff", b"\xc0\xaf", b"\xed\xa0\x80", b"\xf4\x90\x80\x80"):
            with self.subTest(raw=raw):
                self.refuse(raw, "INVALID_UTF8")

    def test_bom_and_non_json_syntax(self):
        for raw in (b"\xef\xbb\xbf" + self.example_raw, b"", b" ", b"{", b"[]}", b'{"a":1,}', b'{/*x*/}', self.example_raw + b"{}", b'{"x":"\x00"}'):
            with self.subTest(raw=raw[:20]):
                self.refuse(raw, "INVALID_JSON")

    def test_root_shape(self):
        for value in (None, True, 1, "text", [], {}, {"payload": {}}, {"signature_hex": "0" * 128}):
            with self.subTest(value=value):
                self.refuse(wire(value), "ENVELOPE_FIELDS")
        self.envelope["extra"] = "ignored?"
        self.refuse(wire(self.envelope), "ENVELOPE_FIELDS")

    def test_each_missing_payload_field(self):
        for name in EXPECTED_FIELDS:
            with self.subTest(name=name):
                value = json.loads(self.example_raw)
                del value["payload"][name]
                self.refuse(wire(value), "PAYLOAD_FIELDS")

    def test_payload_shape_and_extra_field(self):
        for value in (None, [], "text", 1, {**self.envelope["payload"], "extra": "x"}):
            with self.subTest(value=type(value).__name__):
                self.envelope["payload"] = value
                self.refuse(wire(self.envelope), "PAYLOAD_FIELDS")

    def test_duplicate_root_keys_even_with_escapes(self):
        raw = wire(self.envelope)
        for name in (b'"payload"', b'"paylo\\u0061d"'):
            with self.subTest(name=name):
                self.refuse(raw[:-1] + b"," + name + b":{} }", "DUPLICATE_FIELD")
        self.refuse(raw[:-1] + b',"signature_hex":"x"}', "DUPLICATE_FIELD")

    def test_duplicate_payload_keys_equal_or_different(self):
        raw = wire(self.envelope)
        for name, val in ((b'"issuer_id"', b'"example-authority"'), (b'"issuer_id"', b'"other"'), (b'"issuer_\\u0069d"', b'"other"')):
            with self.subTest(name=name, val=val):
                self.refuse(raw.replace(b'"payload":{', b'"payload":{' + name + b":" + val + b","), "DUPLICATE_FIELD")

    def test_non_json_constants(self):
        for value in (b"NaN", b"Infinity", b"-Infinity"):
            with self.subTest(value=value):
                self.refuse(wire(self.envelope).replace(b'"protocol_version":"1"', b'"protocol_version":' + value), "NON_JSON_CONSTANT")

    def test_unpaired_surrogates_in_keys_values_and_lists(self):
        for raw in (b'{"\\ud800":1}', b'{"x":"\\udfff"}', b'{"x":["\\ud800"]}'):
            with self.subTest(raw=raw):
                self.refuse(raw, "INVALID_UNICODE")

    def test_valid_non_ascii_is_not_invalid_utf8(self):
        self.envelope["payload"]["issuer_id"] = "ação"
        self.refuse(wire(self.envelope), "TOKEN_FORMAT")
        self.envelope["payload"]["issuer_id"] = "\U0001f600"
        self.refuse(wire(self.envelope), "TOKEN_FORMAT")

    def test_each_field_requires_string_candidate(self):
        for name in EXPECTED_FIELDS:
            for value in (None, True, 1, 1.5, [], {}):
                with self.subTest(name=name, value=value):
                    e = json.loads(self.example_raw)
                    e["payload"][name] = value
                    self.refuse(wire(e), "FIELD_TYPE")

    def test_version_and_algorithm_no_fallback(self):
        for name, code, values in (
            ("protocol_version", "PROTOCOL_VERSION", ("", "01", "2", "1 ")),
            ("signature_algorithm", "SIGNATURE_ALGORITHM", ("ed25519", "Ed25519ph", "Ed25519ctx", "RSA", "")),
        ):
            for value in values:
                with self.subTest(name=name, value=value):
                    e = json.loads(self.example_raw)
                    e["payload"][name] = value
                    self.refuse(wire(e), code)

    def test_signature_representation(self):
        for value in (None, 0, "", "0" * 127, "0" * 129, "A" * 128, "g" * 128, "0x" + "0" * 126, "0" * 127 + "\n"):
            with self.subTest(value=value):
                self.envelope["signature_hex"] = value
                self.refuse(wire(self.envelope), "SIGNATURE_HEX")

    def test_digest_representation(self):
        for name in ("target_binding_sha256", "global_digest_sha256", "execution_plan_sha256"):
            for value in ("", "0" * 63, "0" * 65, "A" * 64, "z" * 64, "0" * 63 + "\n"):
                with self.subTest(name=name, value=value):
                    e = json.loads(self.example_raw)
                    e["payload"][name] = value
                    self.refuse(wire(e), "DIGEST_HEX")

    def test_decimal_candidate_representation(self):
        for name in ("trust_policy_version", "authority_epoch", "revocation_epoch", "issued_at", "not_before", "expires_at"):
            for value in ("", "01", "-1", "+1", "1.0", "1e2", " 1", "١", "1" * 21, "1\n"):
                with self.subTest(name=name, value=value):
                    e = json.loads(self.example_raw)
                    e["payload"][name] = value
                    self.refuse(wire(e), "DECIMAL_FORMAT")

    def test_token_boundaries_and_escaping(self):
        for value in ("a", "a" * 128, 'braces{}[]quote"slash\\'):
            self.envelope["payload"]["issuer_id"] = value
            parse_candidate_envelope(wire(self.envelope))
        for value in ("", "a" * 129, "a b", "a\t", "\x7f", "a\n"):
            self.envelope["payload"]["issuer_id"] = value
            self.refuse(wire(self.envelope), "TOKEN_FORMAT")

    def test_decimal_max_and_zero_candidate(self):
        for name in ("trust_policy_version", "authority_epoch", "revocation_epoch"):
            for value in ("0", "9" * 20):
                self.envelope["payload"][name] = value
                parse_candidate_envelope(wire(self.envelope))

    def test_temporal_relations_without_clock(self):
        for issued, start, end in ((0, 0, 1), (0, 0, 900), (0, 899, 900), (1700000000, 1700000000, 1700000900)):
            with self.subTest(times=(issued, start, end)):
                for name, val in zip(("issued_at", "not_before", "expires_at"), (issued, start, end)):
                    self.envelope["payload"][name] = str(val)
                parse_candidate_envelope(wire(self.envelope))
        for issued, start, end in ((1, 0, 2), (0, 1, 1), (0, 2, 1), (0, 0, 901)):
            with self.subTest(times=(issued, start, end)):
                for name, val in zip(("issued_at", "not_before", "expires_at"), (issued, start, end)):
                    self.envelope["payload"][name] = str(val)
                self.refuse(wire(self.envelope), "TIME_RELATION")

    def test_exact_envelope_limit_and_one_byte_over(self):
        raw = wire(self.envelope)
        exact = raw + b" " * (MAX_ENVELOPE_BYTES - len(raw))
        parse_candidate_envelope(exact)
        self.refuse(exact + b" ", "ENVELOPE_LIMIT")

    def test_exact_payload_limit_and_one_byte_over(self):
        parse_candidate_envelope(self.payload_wire(MAX_PAYLOAD_BYTES))
        self.refuse(self.payload_wire(MAX_PAYLOAD_BYTES + 1), "PAYLOAD_LIMIT")

    def test_payload_limit_is_original_bytes_in_both_root_orders(self):
        raw = self.payload_wire(MAX_PAYLOAD_BYTES)
        # Same decoded value; escaping an ASCII character adds five wire bytes.
        escaped = raw.replace(b"example-authority", b"exampl\\u0065-authority")
        self.refuse(escaped, "PAYLOAD_LIMIT")
        signature = wire(self.envelope["signature_hex"])
        payload = raw[len(b'{"payload":'):-len(b',"signature_hex":' + signature + b'}')]
        reverse = b'{"signature_hex":' + signature + b',"paylo\\u0061d":' + payload + b'}'
        parse_candidate_envelope(reverse)

    def test_depth_checked_before_shape_and_deserialization(self):
        self.refuse(b"[" * 8 + b"0" + b"]" * 8, "ENVELOPE_FIELDS")
        self.refuse(b"[" * 9 + b"0" + b"]" * 9, "DEPTH_LIMIT")
        self.refuse(b"[" * 1000 + b"0" + b"]" * 1000, "DEPTH_LIMIT")

    def test_errors_do_not_reflect_untrusted_fields(self):
        self.envelope["payload"]["issuer_id"] = "sensitive value"
        with self.assertRaises(StructuralError) as caught:
            parse_candidate_envelope(wire(self.envelope))
        self.assertEqual(str(caught.exception), "TOKEN_FORMAT")
        self.assertNotIn("sensitive", repr(caught.exception))

    def test_parsing_needs_no_files_network_commands_or_clock(self):
        with patch("builtins.open", side_effect=AssertionError("file I/O")), \
             patch("socket.socket", side_effect=AssertionError("network I/O")), \
             patch("subprocess.Popen", side_effect=AssertionError("command")), \
             patch("os.system", side_effect=AssertionError("command")), \
             patch("time.time", side_effect=AssertionError("clock")):
            parse_candidate_envelope(self.example_raw)


if __name__ == "__main__":
    unittest.main()
