"""Offline DEV09B acceptance. Fixtures are synthetic, never operational evidence.

Run with system Python for existing cryptography, or venv for explicit missing
dependency behavior. No package installation, DB, socket, runner or issuance.
"""
import builtins
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from hashlib import sha256
from threading import Barrier
import json
import socket
import subprocess
import unittest
from unittest.mock import patch
from uuid import UUID

from scripts.dedicated.dev09b import codec as c
from scripts.dedicated.dev09b.doubles import (
    MemoryAuthority, MemoryClock, IndependentContinuityDouble, MemoryExecutor,
)
from scripts.dedicated.dev09b.model import (
    ApprovalState as A, AttemptState as S, OfflineAttempt, SessionBinding,
    TimeSample, ContinuitySample,
)


def uid(n):
    return str(UUID(int=n))


def fixture(operation="application-base-to-f066a01a7230", number=1):
    t = dict(schema_version=1, environment="DEV", vm_generation_id=uid(1),
             cluster_generation_id=uid(2), database_name="livenet_v2_dev",
             system_identifier="123", host="db.dev.invalid", port=5432,
             tls_server_name="db.dev.invalid", ca_sha256="1"*64,
             server_certificate_sha256="2"*64, migrator_role="lnv2_dev_migrator",
             inspector_role="lnv2_dev_inspector", instance_id="fixture-instance",
             network_id="fixture-network", storage_id="fixture-storage", image_sha256="3"*64)
    e = dict(schema_version=1, executor_id="fixture-executor", incarnation_id=uid(3),
             image_sha256="4"*64, source_inventory_sha256="5"*64,
             dependency_lock_sha256="6"*64, configuration_sha256="7"*64,
             supervision_policy_sha256="8"*64)
    p = {k: "9"*64 for k in c.PLAN if k.endswith("_sha256")}
    p.update(schema_version=1, operation=operation,
             **dict(zip("application_from application_to security_from security_to".split(), c.OPS[operation])),
             target_binding_sha256=c.digest("target", t), executor_binding_sha256=c.digest("executor", e))
    approval = dict(protocol_version="DEV09B-1", signature_algorithm="Ed25519",
                    issuer_id="fixture-issuer", key_id="fixture-key", trust_policy_version="fixture-policy",
                    approval_id=uid(10+number), request_id=uid(100+number), attempt_id=uid(200+number),
                    approver_id="operator", requester_id="operator", executor_id=e["executor_id"],
                    audience="LiveNet/DEV09B/migration-executor", environment="DEV", vm_generation_id=t["vm_generation_id"],
                    target_binding_sha256=c.digest("target", t), global_digest_sha256="a"*64,
                    operation=operation, gate="DEV09B", purpose="DEV-MVP-PERSISTENCE",
                    execution_plan_sha256=c.digest("plan", p), issued_at=90, not_before=100,
                    expires_at=200, authority_epoch=1, revocation_epoch=1)
    s = SessionBinding(c.digest("target", t), c.digest("executor", e), e["incarnation_id"], 12, 80, "12345")
    return approval, t, e, p, s


class OfflineTests(unittest.TestCase):
    def setUp(self):
        # Selected Python transport/process APIs are forbidden during every test.
        # This is a test guard, not a sandbox against native or malicious code.
        def denied(*_a, **_k):
            raise AssertionError("External operation attempted")
        for owner, name in [(socket, "socket"), (socket, "create_connection"),
                            (socket, "getaddrinfo"), (subprocess, "Popen"), (subprocess, "run")]:
            p = patch.object(owner, name, denied)
            p.start()
            self.addCleanup(p.stop)
        self.p, self.t, self.e, self.plan, self.s = fixture()
        self.clock = MemoryClock()
        self.continuity = IndependentContinuityDouble(uid(900))
        self.a = MemoryAuthority(clock=self.clock, continuity=self.continuity)
        self.a.load_fixture(self.p, self.t, self.e, self.plan)
        self.n = 1000

    def nonce(self):
        self.n += 1
        return uid(self.n)

    def attempt(self, authority=None):
        return OfflineAttempt(authority or self.a, self.p["approval_id"], self.s, self.nonce())

    def test_available_is_not_terminal(self):
        self.assertFalse(A.AVAILABLE.terminal)
        self.assertTrue(all(s.terminal for s in (A.CONSUMED, A.REVOKED, A.EXPIRED)))

    def test_strict_json_parser(self):
        malformed = [b'{"x":1,"x":2}', b'{"x":{"a":1,"a":2}}', b'1.0', b'NaN',
                     b'Infinity', b'"\\ud800"', b'"\xff"', b'\xef\xbb\xbf{}', b'{} trailing',
                     b'['*10+b'0'+b']'*10, str(2**53).encode(), b' '*32769]
        for raw in malformed:
            with self.subTest(raw=raw[:40]), self.assertRaises(c.Invalid):
                c.parse(raw)

    def test_jcs_independent_literal_vector(self):
        # UTF-16 ordering puts U+1F600 before U+E000 (opposite Python codepoints).
        obj = {"\ue000": 2, "😀": 1, "a": "\b\t\n\f\r\x00\"\\/", "z": [True, None, -1]}
        expected = '{"a":"\\b\\t\\n\\f\\r\\u0000\\\"\\\\/","z":[true,null,-1],"😀":1,"\ue000":2}'.encode()
        self.assertEqual(c.canonical(obj), expected)
        self.assertNotEqual(c.canonical({"é": 1}), c.canonical({"e\u0301": 1}))
        with self.assertRaises(c.Invalid):
            c.canonical({"x": 1.0})

    def test_binding_digests_independent_serialization(self):
        # All keys/values ASCII and integer: sort_keys agrees with JCS on this vector.
        encoded = json.dumps(self.t, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(c.digest("target", self.t), sha256(b"LiveNet/DEV09B-1/target\0"+encoded).hexdigest())
        c.inspect_bindings(self.p, self.t, self.e, self.plan)

    def test_exact_signature_domain_and_bytes(self):
        expected = b"LiveNet/DEV09B/approval/v1\x00" + json.dumps(
            self.p, sort_keys=True, separators=(",", ":")).encode("ascii")
        self.assertEqual(c.signed_bytes(self.p), expected)

    def test_envelope_structure_and_signature_encoding(self):
        for obj in [dict(payload=self.p, signature_hex="A"*128),
                    dict(payload=self.p, signature_hex="0"*126),
                    dict(payload=self.p, signature_hex="0"*128, extra=True),
                    dict(signature_hex="0"*128)]:
            # Rejection must happen at schema parsing, not because the dummy
            # signature happens to be invalid (or cryptography is unavailable).
            with self.subTest(keys=list(obj)), patch.object(c, "verify_ed25519") as verifier:
                with self.assertRaises(c.Invalid):
                    c.verify_envelope(c.canonical(obj), bytes(32))
                verifier.assert_not_called()

    def test_incomplete_layers_never_supported(self):
        for kind in ("semantic", "physical", "provenance"):
            with self.subTest(kind=kind), self.assertRaises(c.Unsupported):
                c.digest(kind, {"hash": "a"*64})
        global_obj = dict(schema_version=1, semantic_sha256="a"*64, physical_sha256="b"*64, provenance_sha256="c"*64)
        self.assertEqual(len(c.digest("global", global_obj)), 64)
        with self.assertRaises(c.Unsupported):
            c.validate_layers(global_obj, matching_hash=True)

    def test_strict_payload(self):
        for key, value in [("protocol_version", "1"), ("protocol_version", "2"), ("gate", "G4"),
                           ("issued_at", True), ("expires_at", 1000), ("authority_epoch", 0),
                           ("signature_algorithm", "Ed25519ph"), ("approval_id", "ABC"),
                           ("target_binding_sha256", "A"*64), ("operation", "head"), ("environment", "PROD")]:
            with self.subTest(key=key, value=value), self.assertRaises(c.Invalid):
                c.validate_payload(dict(self.p, **{key: value}))
        for mutate in (lambda p: p.update(extra=1), lambda p: p.pop("gate")):
            p = dict(self.p)
            mutate(p)
            with self.assertRaises(c.Invalid):
                c.validate_payload(p)

    def test_closed_binding_schemas(self):
        for doc, validator in [(self.t, c.validate_target), (self.e, c.validate_executor), (self.plan, c.validate_plan)]:
            for key in doc:
                changed = dict(doc)
                del changed[key]
                with self.subTest(key=key), self.assertRaises(c.Invalid):
                    validator(changed)
            with self.assertRaises(c.Invalid):
                validator(dict(doc, unexpected="x"))

    def test_target_domains(self):
        for k, v in [("schema_version", True), ("port", True), ("port", 0), ("host", "127.1"),
                     ("host", "a,b"), ("host", "DB.invalid"), ("tls_server_name", "*.invalid"),
                     ("host", "fe80::1%eth0"), ("tls_server_name", "fe80::1%eth0"),
                     ("database_name", "livenet_v2_prod"), ("system_identifier", "0123"),
                     ("system_identifier", str(2**64)), ("migrator_role", "Admin")]:
            with self.subTest(k=k, v=v), self.assertRaises(c.Invalid):
                c.validate_target(dict(self.t, **{k:v}))

    def test_plan_exact_revisions_and_security_prerequisite(self):
        # Contract literals are independent of the production OPS mapping used
        # to build fixtures; an accidental revision change must fail this test.
        cases = {
            "application-base-to-f066a01a7230": ("base", "f066a01a7230", "base", "unchanged"),
            "security-base-to-b12b01a7230": ("f066a01a7230", "unchanged", "base", "b12b01a7230"),
        }
        self.assertEqual(set(c.OPS), set(cases))
        for op, revisions in cases.items():
            p, t, e, plan, s = fixture(op)
            self.assertEqual(tuple(plan[k] for k in "application_from application_to security_from security_to".split()), revisions)
            c.inspect_bindings(p, t, e, plan)
        for field, bad in [("application_to", "head"), ("security_from", "b12b01a7230"),
                           ("prerequisite_evidence_sha256", "")]:
            with self.subTest(field=field), self.assertRaises(c.Invalid):
                c.validate_plan(dict(self.plan, **{field:bad}))
        p2, *_ = fixture("security-base-to-b12b01a7230", 2)
        self.assertNotEqual(self.p["approval_id"], p2["approval_id"])
        # A digest of prerequisite evidence does not validate its meaning.
        with self.assertRaises(c.Unsupported):
            c.validate_layers({"prerequisite_evidence_sha256":"a"*64})

    def test_binding_tampering_and_initial_session_binding(self):
        for t, e, p in [(dict(self.t, port=5433), self.e, self.plan),
                        (self.t, dict(self.e, incarnation_id=uid(99)), self.plan),
                        (self.t, self.e, dict(self.plan, limits_sha256="f"*64))]:
            with self.assertRaises(c.Invalid):
                c.inspect_bindings(self.p, t, e, p)
        for changed in (replace(self.s, target_sha256="f"*64), replace(self.s, executor_sha256="f"*64),
                        replace(self.s, incarnation_id=uid(99))):
            with self.assertRaises(c.Invalid):
                self.a.consume(self.p["approval_id"], changed, self.nonce())

    def test_missing_crypto_has_no_fallback(self):
        original = builtins.__import__
        def unavailable(name, *args, **kwargs):
            if name.startswith("cryptography"):
                raise ImportError("synthetic missing dependency")
            return original(name, *args, **kwargs)
        with patch("builtins.__import__", unavailable), self.assertRaises(c.CryptoUnavailable):
            c.verify_ed25519(bytes(32), bytes(64), b"")

    def crypto(self):
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        except ImportError:
            self.skipTest("cryptography unavailable in this interpreter; no fallback")
        return Ed25519PrivateKey

    def test_ed25519_rfc8032_independent_vector(self):
        self.crypto()
        pk = bytes.fromhex("d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")
        sig = bytes.fromhex("e5564300c360ac729086e2cc806e828a"
                            "84877f1eb8e5d974d873e06522490155"
                            "5fb8821590a33bacc61e39701cf9b46bd"
                            "25bf5f0595bbe24655141438e7a100b")
        c.verify_ed25519(pk, sig, b"")
        with self.assertRaises(c.Invalid):
            c.verify_ed25519(pk, sig, b"tampered")

    def test_signed_envelope_and_cross_domain(self):
        private_type = self.crypto()
        # Public RFC8032 TEST seed, test-only in-memory fixture. No key files/issuance API.
        key = private_type.from_private_bytes(bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60"))
        pk = bytes.fromhex("d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")
        env = {"payload": self.p, "signature_hex": key.sign(c.signed_bytes(self.p)).hex()}
        result = c.verify_envelope(c.canonical(env), pk)
        self.assertIsInstance(result, c.SignatureObservation)
        self.assertFalse(hasattr(result, "authorize"))
        for domain in (b"LiveNet/AUTH-BOOT-02-R1/approval/v1\0", b"LiveNet/DEV09B-R2/approval/v1\0", b"G4-WF1\0"):
            bad = dict(env, signature_hex=key.sign(domain+c.canonical(self.p)).hex())
            with self.subTest(domain=domain), self.assertRaises(c.Invalid):
                c.verify_envelope(c.canonical(bad), pk)
        env["payload"] = dict(self.p, executor_id="other")
        with self.assertRaises(c.Invalid):
            c.verify_envelope(c.canonical(env), pk)

    def test_time_boundaries_and_clock_loss(self):
        for sample in (TimeSample(99,100,True), TimeSample(199,200,True),
                       TimeSample(100,100,False), TimeSample(101,100,True)):
            self.clock.value = sample
            with self.subTest(sample=sample), self.assertRaises(c.Invalid):
                self.attempt()
        self.assertIs(self.a.status(self.p["approval_id"], self.nonce())[0], A.AVAILABLE)
        self.clock.value = TimeSample(200,200,True)
        with self.assertRaises(c.Invalid): self.attempt()
        self.assertIs(self.a.status(self.p["approval_id"], self.nonce())[0], A.EXPIRED)

    def test_revoked_before_and_after_consume(self):
        self.a.revoke_fixture(self.p["approval_id"])
        with self.assertRaises(c.Invalid):
            self.attempt()
        self.assertIs(self.a.status(self.p["approval_id"], self.nonce())[0], A.REVOKED)
        p,t,e,plan,s = fixture(number=2)
        self.a.load_fixture(p,t,e,plan)
        attempt = OfflineAttempt(self.a,p["approval_id"],s,self.nonce())
        self.a.revoke_fixture(p["approval_id"])
        with self.assertRaises(c.Invalid):
            attempt.first_effect(s,self.nonce())
        self.assertIs(self.a.status(p["approval_id"],self.nonce())[0], A.CONSUMED)

    def test_key_issuer_policy_revocation_blocks_progression(self):
        for kind, field in (("key","key_id"),("issuer","issuer_id"),("policy","trust_policy_version")):
            auth=MemoryAuthority(clock=self.clock,continuity=self.continuity)
            auth.load_fixture(self.p,self.t,self.e,self.plan)
            a=self.attempt(auth)
            auth.revoke_identity_fixture(kind,self.p[field])
            with self.subTest(kind=kind),self.assertRaises(c.Invalid):
                a.first_effect(self.s,self.nonce())

    def test_modeled_concurrent_consume(self):
        start = Barrier(8)
        def consume(n):
            start.wait(timeout=5)
            try:
                self.a.consume(self.p["approval_id"], self.s, uid(3000+n))
                return True
            except c.Invalid:
                return False
        with ThreadPoolExecutor(max_workers=8) as pool:
            self.assertEqual(sum(pool.map(consume, range(8))), 1)

    def test_consumed_without_execution_stays_spent(self):
        a = self.attempt()
        a.abort()
        a.rollback_result(transaction_confirmed=True, independent_confirmed=True)
        self.assertIs(a.state,S.ROLLED_BACK_CONFIRMED)
        with self.assertRaises(c.Invalid):
            self.attempt()

    def test_one_attempt_cannot_consume_two_approvals(self):
        self.attempt()
        p,t,e,plan,s=fixture(number=2)
        p["attempt_id"]=self.p["attempt_id"]
        self.a.load_fixture(p,t,e,plan)
        with self.assertRaises(c.Invalid):
            self.a.consume(p["approval_id"],s,self.nonce())

    def test_clock_backwards_is_blocked(self):
        self.clock.value=TimeSample(150,150,True)
        a=self.attempt()
        # Both samples lie inside validity. Only the backwards-time guard can
        # explain rejection; not_before must not accidentally satisfy the test.
        self.clock.value=TimeSample(125,125,True)
        with self.assertRaises(c.Invalid): a.first_effect(self.s,self.nonce())

    def test_complete_reconciliation_needs_explicit_independent_confirmation(self):
        self.continuity.value=ContinuitySample(uid(901),True)
        with self.assertRaises(c.Invalid): self.attempt()
        self.continuity.value=ContinuitySample(uid(901),False)
        with self.assertRaises(c.Invalid): self.a.reconcile_fixture(complete=True)
        self.continuity.value=ContinuitySample(uid(901),True)
        self.a.reconcile_fixture(complete=True)
        self.attempt()  # Synthetic assertion that the entire history was reconciled.

    def test_consume_response_lost(self):
        class LostResponse(MemoryAuthority):
            def consume(self,*args):
                super().consume(*args)
                raise ConnectionError("synthetic lost response")
        a = LostResponse(clock=self.clock,continuity=self.continuity)
        a.load_fixture(self.p,self.t,self.e,self.plan)
        with self.assertRaises(ConnectionError):
            self.attempt(a)
        self.assertIs(a.status(self.p["approval_id"],self.nonce())[0],A.CONSUMED)
        with self.assertRaises(c.Invalid):
            a.consume(self.p["approval_id"],self.s,self.nonce())

    def test_session_transaction_incarnation_swaps(self):
        for changed in (replace(self.s,backend_pid=99),replace(self.s,backend_start=81),
                        replace(self.s,transaction_id="54321"),replace(self.s,incarnation_id=uid(7))):
            auth = MemoryAuthority(clock=self.clock,continuity=self.continuity)
            auth.load_fixture(self.p,self.t,self.e,self.plan)
            a = self.attempt(auth)
            with self.subTest(changed=changed), self.assertRaises(c.Invalid):
                a.first_effect(changed,self.nonce())
            self.assertIs(a.state,S.ABORTING)

    def test_authority_directly_rejects_session_swaps(self):
        self.attempt()
        for changed in (replace(self.s,backend_pid=99),replace(self.s,backend_start=81),
                        replace(self.s,transaction_id="54321"),replace(self.s,incarnation_id=uid(7)),
                        replace(self.s,target_sha256="f"*64),replace(self.s,executor_sha256="f"*64)):
            with self.subTest(changed=changed),self.assertRaises(c.Invalid):
                self.a.check(self.p["attempt_id"],"first_effect",changed,self.nonce())

    def test_authority_clock_revocation_loss_at_checkpoints(self):
        for phase in ("first_effect","before_commit","dispatch"):
            for failure in ("authority","clock","expiry","revocation","continuity"):
                auth = MemoryAuthority(clock=MemoryClock(),continuity=IndependentContinuityDouble(uid(900)))
                auth.load_fixture(self.p,self.t,self.e,self.plan)
                a = self.attempt(auth)
                if phase != "first_effect": a.first_effect(self.s,self.nonce())
                if phase == "dispatch": a.before_commit(self.s,self.nonce())
                if failure == "authority": auth.available=False
                elif failure == "clock": auth.clock.value=TimeSample(100,100,False)
                elif failure == "expiry": auth.clock.value=TimeSample(200,200,True)
                elif failure == "revocation": auth.revoke_fixture(self.p["approval_id"])
                else: auth.continuity.value=ContinuitySample(uid(900),False)
                action = {"first_effect":a.first_effect,"before_commit":a.before_commit,"dispatch":a.simulate_commit_dispatch}[phase]
                with self.subTest(phase=phase,failure=failure),self.assertRaises(c.Invalid):
                    action(self.s,self.nonce())
                a.abort()
                a.close()
                self.assertIs(a.state,S.UNKNOWN)
                self.assertFalse(a.commit_sent)

    def test_commit_intent_record_failure_aborts(self):
        a=self.attempt()
        a.first_effect(self.s,self.nonce())
        with patch.object(self.a,"record",side_effect=ConnectionError("synthetic loss")):
            with self.assertRaises(ConnectionError): a.before_commit(self.s,self.nonce())
        self.assertIs(a.state,S.ABORTING)

    def test_commit_uncertainty_and_independent_reconciliation(self):
        a=self.attempt()
        a.first_effect(self.s,self.nonce())
        a.before_commit(self.s,self.nonce())
        a.simulate_commit_dispatch(self.s,self.nonce())
        self.assertIs(a.state,S.UNKNOWN)
        self.a.available=False
        a.abort(); a.close()
        with self.assertRaises(c.Invalid):
            a.rollback_result(transaction_confirmed=True,independent_confirmed=True)
        with self.assertRaises(c.Invalid):
            a.reconcile(S.COMMITTED_CONFIRMED,independent_confirmed=False)
        a.reconcile(S.COMMITTED_CONFIRMED,independent_confirmed=True)
        self.assertIs(a.state,S.COMMITTED_CONFIRMED)
        with self.assertRaises(c.Invalid): a.first_effect(self.s,self.nonce())

    def test_rollback_requires_independent_confirmation(self):
        a=self.attempt(); a.abort()
        a.rollback_result(transaction_confirmed=True,independent_confirmed=False)
        self.assertIs(a.state,S.UNKNOWN)

    def test_containment_preserves_unknown_without_commit(self):
        a=self.attempt()
        a.close()
        self.assertFalse(a.commit_sent)
        self.a.available=False
        a.abort()
        self.assertIs(a.state,S.UNKNOWN)
        a.close()
        self.assertIs(a.state,S.UNKNOWN)
        with self.assertRaises(c.Invalid): a.first_effect(self.s,self.nonce())

    def test_independent_continuity_latch_and_epoch_not_proof(self):
        self.continuity.value=ContinuitySample(uid(900),False)
        with self.assertRaises(c.Invalid): self.attempt()
        self.a.authority_epoch += 1  # Restorable local field cannot open latch.
        self.continuity.value=ContinuitySample(uid(900),True)
        with self.assertRaises(c.Invalid): self.attempt()
        with self.assertRaises(c.Invalid): self.a.reconcile_fixture(complete=False)

    def test_incomplete_reconciliation_retires_all_old_approvals(self):
        self.continuity.value=ContinuitySample(uid(901),True)
        with self.assertRaises(c.Invalid): self.attempt()
        self.a.reconcile_fixture(complete=False)
        with self.assertRaises(c.Invalid): self.attempt()
        lost,t,e,plan,s=fixture(number=5)  # Not present in restored store, old epoch.
        with self.assertRaises(c.Invalid): self.a.load_fixture(lost,t,e,plan)
        new=dict(lost,authority_epoch=2)
        self.a.load_fixture(new,t,e,plan)
        self.a.consume(new["approval_id"],s,self.nonce())

    def test_payload_fixture_is_snapshot_and_nonce_not_reusable(self):
        self.p["executor_id"]="changed-after-load"
        nonce=self.nonce()
        self.a.consume(self.p["approval_id"],self.s,nonce)
        with self.assertRaises(c.Invalid): self.a.status(self.p["approval_id"],nonce)

    def test_memory_executor_is_inert(self):
        e=MemoryExecutor(self.s)
        self.assertEqual(e.prepare(c.canonical(self.plan)),self.s)
        observation=self.a.consume(self.p["approval_id"],self.s,self.nonce())
        e.run(observation)
        e.abort();e.close()
        self.assertEqual(e.events,["synthetic_prepare","synthetic_run","synthetic_rollback","synthetic_close"])
        with self.assertRaises(c.Invalid):
            e.run(c.SignatureObservation(c.canonical(self.p)))
        with self.assertRaises(c.Invalid): e.run(c.digest("target",self.t))


if __name__ == "__main__":
    unittest.main()
