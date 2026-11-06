from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import fields, replace
import json
import multiprocessing
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
import threading
import unittest

from laboratory import Approval, Authority, Binding, TimeInterval, WitnessDouble, connect


KEY = b"R2-DEV-01 public test fixture, never a production key"


def trusted_clock():
    return TimeInterval(120, 121)


def fixture_binding():
    return Binding(
        request_id="request-1", attempt_id="attempt-1", approver_id="approver-1",
        requester_id="requester-1", purpose="isolated laboratory",
        operation="LAB_FIXED_UPDATE", gate="CLOSED-LAB-ONLY", environment="temporary-test",
        execution_plan_sha256="1" * 64, global_digest_sha256="2" * 64,
        target_binding_sha256="3" * 64, audience="lab-target",
        vm_generation_id="generation-1", executor_id="executor-double",
        executor_incarnation="incarnation-1", protected_session="session-1",
        protected_transaction="transaction-1",
    )


def open_authority(directory, clock=trusted_clock, instance="instance-1", witness_type=WitnessDouble):
    directory = Path(directory)
    return Authority(directory / "authority.sqlite", witness_type(directory / "witness.sqlite", KEY), instance, clock, KEY)


def process_admit(directory, start, queue):
    start.wait(10)
    result = open_authority(directory).admit("approval-1", fixture_binding())
    queue.put((result.status, result.sequence, result.executable))


def process_crash(directory, phase, operation="admit"):
    authority = open_authority(directory)
    def crash(current):
        if current == phase:
            os._exit(73)
    if operation == "admit":
        authority.admit("approval-1", fixture_binding(), crash)
    else:
        authority.revoke("approval", "approval-1", crash)


class MissingWitness(WitnessDouble):
    def record(self, store_id, instance, event):
        raise OSError("independent copy unavailable")


class BadAcknowledgement(WitnessDouble):
    def record(self, store_id, instance, event):
        checkpoint, signature = super().record(store_id, instance, event)
        return checkpoint, "0" * 64


class LaboratoryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="r2-dev01-")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.binding = fixture_binding()
        self.approval = Approval("approval-1", self.binding)
        self.authority = Authority.create(
            self.directory / "authority.sqlite", WitnessDouble(self.directory / "witness.sqlite", KEY),
            "instance-1", trusted_clock, KEY,
        )
        self.assertEqual(self.authority.issue(self.approval).status, "RECORDED")

    def raw_state(self, authority=None):
        with closing(connect((authority or self.authority).path)) as connection:
            return json.loads(connection.execute("SELECT document FROM state").fetchone()[0])

    def events(self):
        with closing(connect(self.authority.path)) as connection:
            return [json.loads(row[0]) for row in connection.execute("SELECT event FROM events ORDER BY sequence")]

    def admit(self, authority=None, fault=None):
        return (authority or self.authority).admit("approval-1", self.binding, fault)

    def crash(self, phase, operation="admit"):
        process = multiprocessing.get_context("spawn").Process(target=process_crash, args=(str(self.directory), phase, operation))
        process.start()
        process.join(20)
        if process.is_alive():
            process.kill()
            process.join()
            self.fail("crash worker timeout")
        self.assertEqual(process.exitcode, 73)

    def test_c1_atomic_local_evidence_and_consumption(self):
        result = self.admit()
        self.assertEqual(result.status, "ADMITTED")
        event = self.events()[-1]
        self.assertEqual(event["kind"], "ADMITTED")
        self.assertEqual(event["details"], event["state"]["admissions"]["approval-1"])
        self.assertEqual(result.sequence, event["sequence"])
        self.assertTrue(event["details"]["consumed"])
        self.assertFalse(result.executable)
        with closing(connect(self.authority.witness.path)) as connection:
            witnessed = json.loads(connection.execute("SELECT event FROM events ORDER BY sequence DESC LIMIT 1").fetchone()[0])
        self.assertEqual(event, witnessed)

    def test_c1_32_threads_only_one_admission(self):
        barrier = threading.Barrier(32)
        def compete(worker):
            authority = open_authority(self.directory)
            barrier.wait(10)
            return self.admit(authority)
        with ThreadPoolExecutor(max_workers=32) as pool:
            results = list(pool.map(compete, range(32)))
        self.assertEqual(sum(result.status == "ADMITTED" for result in results), 1)
        self.assertEqual(sum(result.status == "DENIED" for result in results), 31)
        self.assertEqual(len(self.raw_state()["admissions"]), 1)

    def test_c1_8_processes_only_one_admission(self):
        context = multiprocessing.get_context("spawn")
        start, queue = context.Event(), context.Queue()
        processes = [context.Process(target=process_admit, args=(str(self.directory), start, queue)) for worker in range(8)]
        try:
            for process in processes:
                process.start()
            start.set()
            results = [queue.get(timeout=20) for process in processes]
            for process in processes:
                process.join(20)
                self.assertEqual(process.exitcode, 0)
            self.assertEqual(sum(status == "ADMITTED" for status, sequence, executable in results), 1)
            self.assertEqual(sum(status == "DENIED" for status, sequence, executable in results), 7)
            self.assertFalse(any(executable for status, sequence, executable in results))
        finally:
            for process in processes:
                if process.is_alive():
                    process.kill()
                    process.join()
            queue.close()

    def test_c1_actual_crash_before_commit_leaves_no_partial_consumption(self):
        self.crash("before_commit")
        self.assertEqual(open_authority(self.directory).status("approval-1").status, "NOT_ADMITTED")
        self.assertNotIn("approval-1", self.raw_state()["admissions"])
        self.assertEqual(len(self.events()), 1)

    def test_c2_interval_boundaries(self):
        for interval in (TimeInterval(99, 100), TimeInterval(120, 200), TimeInterval(200, 200)):
            with self.subTest(interval=interval):
                self.assertEqual(self.admit(open_authority(self.directory, lambda: interval)).status, "DENIED")
        self.assertEqual(self.admit(open_authority(self.directory, lambda: TimeInterval(100, 199))).status, "ADMITTED")

    def test_c2_invalid_lifetimes_and_900_second_boundary(self):
        invalid = (
            replace(self.approval, issued_at=101, not_before=100),
            replace(self.approval, expires_at=100),
            replace(self.approval, expires_at=1001),
            replace(self.approval, issued_at=True),
        )
        for index, approval in enumerate(invalid):
            with self.subTest(index=index):
                self.assertEqual(self.authority.issue(replace(approval, approval_id=f"bad-{index}")).status, "DENIED")
        self.assertEqual(self.authority.issue(replace(self.approval, approval_id="max", expires_at=1000)).status, "RECORDED")

    def test_c2_unknown_time_quarantines(self):
        self.assertEqual(self.admit(open_authority(self.directory, lambda: TimeInterval(120, 121, trusted=False))).status, "UNKNOWN/BLOCKED")
        self.assertEqual(self.admit().status, "UNKNOWN/BLOCKED")

    def test_c2_time_discontinuity_quarantines(self):
        self.assertEqual(self.admit(open_authority(self.directory, lambda: TimeInterval(120, 121, continuous=False))).status, "UNKNOWN/BLOCKED")

    def test_c2_malformed_interval_quarantines(self):
        self.assertEqual(self.admit(open_authority(self.directory, lambda: TimeInterval(121, 120))).status, "UNKNOWN/BLOCKED")

    def test_c2_time_rollback_between_admissions_blocks(self):
        self.assertEqual(self.admit().status, "ADMITTED")
        second_binding = replace(self.binding, attempt_id="attempt-2", request_id="request-2")
        self.authority.issue(replace(self.approval, approval_id="approval-2", binding=second_binding))
        result = open_authority(self.directory, lambda: TimeInterval(119, 120)).admit("approval-2", second_binding)
        self.assertEqual(result.status, "UNKNOWN/BLOCKED")

    def test_c2_A_is_sampled_after_acquiring_authoritative_lock(self):
        entered, release, sampled = threading.Event(), threading.Event(), threading.Event()
        current = [TimeInterval(120, 121)]
        def hold():
            with self.authority.locked():
                entered.set()
                self.assertTrue(release.wait(10))
        def clock():
            sampled.set()
            return current[0]
        with ThreadPoolExecutor(max_workers=2) as pool:
            holder = pool.submit(hold)
            self.assertTrue(entered.wait(10))
            contender = pool.submit(self.admit, open_authority(self.directory, clock))
            self.assertFalse(sampled.wait(0.05))
            current[0] = TimeInterval(200, 201)
            release.set()
            holder.result(timeout=10)
            self.assertEqual(contender.result(timeout=10).status, "DENIED")

    def test_c2_commit_can_follow_expiry_without_resampling_A(self):
        current = [TimeInterval(199, 199)]
        authority = open_authority(self.directory, lambda: current[0])
        def pass_expiry(phase):
            if phase == "before_commit":
                current[0] = TimeInterval(201, 201)
        result = self.admit(authority, pass_expiry)
        self.assertEqual(result.status, "ADMITTED")
        self.assertEqual(result.admission["interval"]["upper"], 199)

    def test_c3_all_revocation_scopes_precede_A(self):
        subjects = {"approval": "approval-1", "key": "lab-key", "authority": "lab-authority", "policy": "lab-policy"}
        for scope, subject in subjects.items():
            with self.subTest(scope=scope), tempfile.TemporaryDirectory() as directory:
                authority = Authority.create(Path(directory) / "authority.sqlite", WitnessDouble(Path(directory) / "witness.sqlite", KEY), "instance-1", trusted_clock, KEY)
                authority.issue(self.approval)
                revocation = authority.revoke(scope, subject)
                self.assertEqual(revocation.status, "EFFECTIVE")
                self.assertEqual(self.admit(authority).status, "DENIED")
                self.assertEqual(authority.status("approval-1").status, "NOT_ADMITTED")

    def test_c3_later_revocation_does_not_erase_admission(self):
        admitted = self.admit()
        revoked = self.authority.revoke("approval", "approval-1")
        self.assertLess(admitted.sequence, revoked.sequence)
        observation = open_authority(self.directory).status("approval-1")
        self.assertEqual(observation.admission, admitted.admission)
        self.assertFalse(observation.executable)
        self.assertEqual(self.admit().status, "DENIED")

    def test_c3_pending_is_never_reported_effective(self):
        before = self.events()
        self.assertEqual(self.authority.request_revocation("approval", "approval-1").status, "PENDING")
        self.assertEqual(self.events(), before)
        self.assertEqual(self.admit().status, "ADMITTED")

    def test_c3_concurrent_revocation_obeys_persisted_order(self):
        for iteration in range(16):
            with self.subTest(iteration=iteration), tempfile.TemporaryDirectory() as directory:
                authority = Authority.create(Path(directory) / "authority.sqlite", WitnessDouble(Path(directory) / "witness.sqlite", KEY), "instance-1", trusted_clock, KEY)
                authority.issue(self.approval)
                barrier = threading.Barrier(2)
                def admit():
                    barrier.wait(10)
                    return self.admit(open_authority(directory))
                def revoke():
                    barrier.wait(10)
                    return open_authority(directory).revoke("approval", "approval-1")
                with ThreadPoolExecutor(max_workers=2) as pool:
                    admission_future, revocation_future = pool.submit(admit), pool.submit(revoke)
                    admitted, revoked = admission_future.result(), revocation_future.result()
                self.assertEqual(revoked.status, "EFFECTIVE")
                if admitted.status == "ADMITTED":
                    self.assertLess(admitted.sequence, revoked.sequence)
                else:
                    self.assertEqual(admitted.status, "DENIED")
                    self.assertIsNone(authority.status("approval-1").admission)

    def test_c3_control_changes_share_order_and_invalidate_stale_epochs(self):
        changed = self.authority.change_control(2, 2, "lab-policy-2")
        self.assertEqual(changed.status, "RECORDED")
        self.assertEqual(self.admit().status, "DENIED")
        reopened = open_authority(self.directory)
        self.assertEqual(reopened.change_control(1, 1, "lab-policy").status, "DENIED")
        state = self.raw_state()
        self.assertEqual((state["authority_epoch"], state["revocation_epoch"], state["policy"]), (2, 2, "lab-policy-2"))

    def test_c3_policy_change_alone_blocks(self):
        self.authority.change_control(1, 1, "different-policy")
        self.assertEqual(self.admit().status, "DENIED")

    def test_c3_unconfirmed_revocation_blocks_new_admission(self):
        self.crash("after_commit", "revoke")
        self.assertEqual(self.admit(open_authority(self.directory)).status, "UNKNOWN/BLOCKED")
        self.assertEqual(self.raw_state()["revocations"][0]["scope"], "approval")

    def test_c4_each_binding_field_is_immutable(self):
        for field in fields(self.binding):
            with self.subTest(field=field.name):
                changed = replace(self.binding, **{field.name: getattr(self.binding, field.name) + "-other"})
                self.assertEqual(self.authority.admit("approval-1", changed).status, "DENIED")
        self.assertEqual(self.admit().status, "ADMITTED")

    def test_c4_approval_id_cannot_be_overwritten(self):
        self.assertEqual(self.authority.issue(self.approval).status, "DENIED")
        self.assertEqual(self.authority.issue(replace(self.approval, expires_at=201)).reason, "approval ID conflict")
        self.assertEqual(self.raw_state()["approvals"]["approval-1"]["expires_at"], 200)

    def test_c4_replay_after_expiration_timeout_and_restart_never_releases(self):
        self.assertEqual(self.admit().status, "ADMITTED")
        for interval in (TimeInterval(120, 121), TimeInterval(200, 201), TimeInterval(10000, 10001)):
            with self.subTest(interval=interval):
                result = self.admit(open_authority(self.directory, lambda: interval))
                self.assertEqual(result.status, "DENIED")
                self.assertFalse(result.executable)
        self.assertEqual(len(self.raw_state()["admissions"]), 1)

    def test_c4_caller_rollback_savepoint_cannot_release_authority_consumption(self):
        self.assertEqual(self.admit().status, "ADMITTED")
        with closing(sqlite3.connect(":memory:")) as caller:
            caller.execute("CREATE TABLE laboratory_effect (value INTEGER)")
            caller.execute("BEGIN")
            caller.execute("SAVEPOINT attempt")
            caller.execute("INSERT INTO laboratory_effect VALUES (1)")
            caller.execute("ROLLBACK TO attempt")
            caller.rollback()
        self.assertEqual(self.admit(open_authority(self.directory)).status, "DENIED")

    def test_c4_no_arbitrary_operation_is_accepted(self):
        approval = replace(self.approval, approval_id="arbitrary", binding=replace(self.binding, operation="DDL"))
        self.assertEqual(self.authority.issue(approval).status, "DENIED")

    def test_c5_lost_response_after_independent_confirmation_is_observation_only(self):
        self.crash("after_witness")
        reopened = open_authority(self.directory)
        observation = reopened.status("approval-1")
        self.assertEqual(observation.status, "OBSERVED")
        self.assertTrue(observation.admission["consumed"])
        self.assertFalse(observation.executable)
        self.assertEqual(self.admit(reopened).status, "DENIED")

    def test_c5_actual_crash_after_commit_preserves_consumption_and_blocks(self):
        self.crash("after_commit")
        self.assertTrue(self.raw_state()["admissions"]["approval-1"]["consumed"])
        reopened = open_authority(self.directory)
        self.assertEqual(reopened.status("approval-1").status, "UNKNOWN/BLOCKED")
        self.assertEqual(self.admit(reopened).status, "UNKNOWN/BLOCKED")
        self.assertEqual(self.admit().status, "UNKNOWN/BLOCKED")

    def test_c5_response_loss_returns_unknown_without_retry(self):
        def lose_response(phase):
            if phase == "after_witness":
                raise OSError("response lost")
        self.assertEqual(self.admit(fault=lose_response).status, "UNKNOWN/BLOCKED")
        count = len(self.events())
        self.assertEqual(self.authority.status("approval-1").status, "OBSERVED")
        self.assertEqual(self.admit().status, "UNKNOWN/BLOCKED")
        self.assertEqual(len(self.events()), count)

    def test_c6_missing_independent_confirmation_blocks_after_durable_consumption(self):
        result = self.admit(open_authority(self.directory, witness_type=MissingWitness))
        self.assertEqual(result.status, "UNKNOWN/BLOCKED")
        self.assertFalse(result.executable)
        self.assertTrue(self.raw_state()["admissions"]["approval-1"]["consumed"])
        self.assertEqual(self.admit().status, "UNKNOWN/BLOCKED")

    def test_c6_unauthenticated_ack_blocks(self):
        result = self.admit(open_authority(self.directory, witness_type=BadAcknowledgement))
        self.assertEqual(result.status, "UNKNOWN/BLOCKED")
        self.assertTrue(self.raw_state()["admissions"]["approval-1"]["consumed"])

    def test_c6_wrong_checkpoint_key_blocks(self):
        authority = Authority(self.authority.path, self.authority.witness, "instance-1", trusted_clock, b"wrong key")
        self.assertEqual(self.admit(authority).status, "UNKNOWN/BLOCKED")
        self.assertNotIn("approval-1", self.raw_state()["admissions"])

    def test_c6_old_snapshot_detected_by_external_head(self):
        snapshot = self.directory / "snapshot.sqlite"
        shutil.copyfile(self.authority.path, snapshot)
        self.assertEqual(self.admit().status, "ADMITTED")
        restored = Authority(snapshot, self.authority.witness, "instance-1", trusted_clock, KEY)
        self.assertEqual(self.admit(restored).status, "UNKNOWN/BLOCKED")
        self.assertNotIn("approval-1", self.raw_state(restored)["admissions"])
        self.assertTrue(self.raw_state()["admissions"]["approval-1"]["consumed"])

    def test_c6_clone_with_new_incarnation_quarantined(self):
        clone = self.directory / "clone.sqlite"
        shutil.copyfile(self.authority.path, clone)
        authority = Authority(clone, self.authority.witness, "instance-clone", trusted_clock, KEY)
        self.assertEqual(self.admit(authority).status, "UNKNOWN/BLOCKED")
        self.assertEqual(authority.change_control(999, 999, "new-policy").status, "UNKNOWN/BLOCKED")

    def test_limit_complete_clone_with_same_identity_is_not_detectable(self):
        with tempfile.TemporaryDirectory() as directory:
            clone_directory = Path(directory)
            shutil.copyfile(self.authority.path, clone_directory / "authority.sqlite")
            shutil.copyfile(self.authority.witness.path, clone_directory / "witness.sqlite")
            clone = open_authority(clone_directory)
            self.assertEqual(self.admit().status, "ADMITTED")
            self.assertEqual(self.admit(clone).status, "ADMITTED")
            self.assertFalse(self.authority.status("approval-1").executable)
            self.assertFalse(clone.status("approval-1").executable)

    def test_c6_missing_witness_never_bootstraps_recovery(self):
        self.authority.witness.path.unlink()
        self.assertEqual(self.admit().status, "UNKNOWN/BLOCKED")
        self.assertNotIn("approval-1", self.raw_state()["admissions"])

    def test_c6_tampered_state_is_quarantined(self):
        self.admit()
        state = self.raw_state()
        state["admissions"].clear()
        with closing(connect(self.authority.path)) as connection:
            connection.execute("UPDATE state SET document = ?", (json.dumps(state),))
        self.assertEqual(self.admit().status, "UNKNOWN/BLOCKED")

    def test_c6_recovery_preserves_revocation_bindings_order_and_epochs(self):
        self.admit()
        self.authority.revoke("key", "lab-key")
        self.authority.change_control(2, 3, "policy-2")
        before = self.raw_state()
        reopened = open_authority(self.directory)
        result = reopened.status("approval-1")
        self.assertEqual(result.status, "OBSERVED")
        self.assertFalse(result.executable)
        self.assertEqual(self.raw_state(reopened), before)
        self.assertEqual(self.admit(reopened).status, "DENIED")

    def test_c6_quarantine_survives_restart_and_epoch_increase(self):
        self.admit(open_authority(self.directory, lambda: TimeInterval(120, 121, continuous=False)))
        reopened = open_authority(self.directory)
        self.assertEqual(reopened.change_control(100, 100, "recovered").status, "UNKNOWN/BLOCKED")
        self.assertEqual(self.admit(reopened).status, "UNKNOWN/BLOCKED")

    def test_c7_v1_never_falls_back_to_r2(self):
        for version in ("1", "3", "", 2):
            with self.subTest(version=version):
                result = self.authority.issue(replace(self.approval, approval_id=f"version-{version}", protocol_version=version))
                self.assertEqual(result.status, "DENIED")
        self.assertEqual(self.admit().status, "ADMITTED")

    def test_c7_no_executable_capability_or_operational_envelope(self):
        result = self.admit()
        self.assertFalse(result.executable)
        self.assertNotIn("signature_hex", result.admission)
        self.assertNotIn("payload", result.admission)
        self.assertFalse(hasattr(self.authority, "execute"))
        self.assertFalse(hasattr(self.authority, "resume"))

    def test_provisioning_never_resets_existing_store(self):
        self.admit()
        with self.assertRaises(ValueError):
            Authority.create(self.authority.path, self.authority.witness, "new", trusted_clock, KEY)
        self.assertTrue(self.raw_state()["admissions"]["approval-1"]["consumed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
