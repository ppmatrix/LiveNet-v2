"""Deterministic schedules: counterexamples are expected, not implementation bugs."""

from copy import deepcopy
from dataclasses import replace
from itertools import permutations
import unittest

from protocols.auth_boot_r1.initiation_model import (
    AuthorityState, Context, Interval, Mode, Model, Refused, Stage,
)


class InitiationModelTests(unittest.TestCase):
    def prepared(self):
        model = Model()
        context = Context()
        model.claim(context)
        receipt = model.consume(context)
        return model, context, receipt

    def test_claim_consumption_transitions_and_no_second_consumption(self):
        model = Model()
        context = Context()
        with self.assertRaises(Refused):
            model.consume(context)
        self.assertIs(model.authority.state, AuthorityState.ISSUED)
        model.claim(context)
        self.assertIs(model.authority.state, AuthorityState.CLAIMED)
        with self.assertRaises(Refused):
            model.consume(replace(context, session="substituted"))
        model.consume(context)
        self.assertIs(model.authority.state, AuthorityState.CONSUMED)
        with self.assertRaises(Refused):
            model.consume(context)

    def test_all_interleavings_two_claimants_have_one_winner(self):
        contexts = (Context(), replace(Context(), incarnation="incarnation-2", session="session-2"))
        schedules = 0
        for order in permutations(("claim0", "consume0", "claim1", "consume1")):
            if any(order.index("claim" + str(i)) > order.index("consume" + str(i)) for i in (0, 1)):
                continue
            schedules += 1
            model = Model()
            consumed = []
            for event in order:
                i = int(event[-1])
                try:
                    if event.startswith("claim"):
                        model.claim(contexts[i])
                    else:
                        consumed.append(model.consume(contexts[i]))
                except Refused:
                    pass
            with self.subTest(order=order):
                self.assertEqual(len(consumed), 1)
                self.assertEqual(consumed[0].context, model.authority.holder)
        self.assertEqual(schedules, 6)

    def test_revoked_expired_uncertain_or_partitioned_claim_refused(self):
        for change in ("revoked", "expired", "uncertain", "untrusted", "partition"):
            with self.subTest(change=change):
                model = Model()
                if change == "revoked":
                    model.revoke()
                elif change == "expired":
                    model.authority_time = Interval(900, 900)
                elif change == "uncertain":
                    model.authority_time = Interval(899, 900)
                elif change == "untrusted":
                    model.authority_time = Interval(0, 0, False)
                else:
                    model.connected = False
                with self.assertRaises(Refused):
                    model.claim(Context())
                self.assertIs(model.authority.state, AuthorityState.ISSUED)

    def test_revocation_between_claim_and_consumption_refused(self):
        model = Model()
        model.claim(Context())
        model.revoke()
        with self.assertRaises(Refused):
            model.consume(Context())

    def test_epochs_revalidated_at_claim_and_consumption(self):
        for name in ("authority_epoch", "revocation_epoch"):
            for after_claim in (False, True):
                model = Model()
                if after_claim:
                    model.claim(Context())
                setattr(model.authority, name, 2)
                with self.subTest(name=name, after_claim=after_claim), self.assertRaises(Refused):
                    if after_claim:
                        model.consume(Context())
                    else:
                        model.claim(Context())

    def test_expiry_revalidated_at_consumption(self):
        model = Model()
        model.claim(Context())
        model.authority_time = Interval(900, 900)
        with self.assertRaises(Refused):
            model.consume(Context())

    def test_receipt_binds_every_model_context_dimension(self):
        for name in Context.__dataclass_fields__:
            model, context, receipt = self.prepared()
            with self.subTest(name=name), self.assertRaises(Refused):
                model.dispatch(receipt, replace(context, **{name: "substituted"}), Mode.TARGET_LOCAL)
            self.assertFalse(model.effects)

    def test_epoch_change_before_dispatch_refuses_old_receipt(self):
        for name in ("authority_epoch", "revocation_epoch"):
            model, context, receipt = self.prepared()
            setattr(model.authority, name, 2)
            with self.subTest(name=name), self.assertRaises(Refused):
                model.dispatch(receipt, context, Mode.TARGET_LOCAL)

    def test_consumption_alone_does_not_prevent_double_initiation(self):
        model, context, receipt = self.prepared()
        left = model.dispatch(receipt, context, Mode.PRECHECK)
        right = model.dispatch(receipt, context, Mode.PRECHECK)
        model.first_effect(left)
        model.first_effect(right)
        self.assertEqual(len(model.effects), 2)  # GAP-001 counterexample
        self.assertIs(model.authority.state, AuthorityState.CONSUMED)

    def test_target_reservation_refuses_second_dispatch(self):
        for mode in (Mode.TARGET_LOCAL, Mode.IDEAL):
            model, context, receipt = self.prepared()
            first = model.dispatch(receipt, context, mode)
            with self.subTest(mode=mode), self.assertRaises(Refused):
                model.dispatch(receipt, context, mode)
            model.first_effect(first)
            self.assertEqual(len(model.effects), 1)

    def test_copied_queued_execution_cannot_bypass_target_start_marker(self):
        model, context, receipt = self.prepared()
        first = model.dispatch(receipt, context, Mode.TARGET_LOCAL)
        duplicate = deepcopy(first)
        model.first_effect(first)
        with self.assertRaises(Refused):
            model.first_effect(duplicate)
        self.assertEqual(len(model.effects), 1)

    def test_crash_before_dispatch_burns_approval_without_effect(self):
        model, context, _ = self.prepared()
        restarted = deepcopy(model)  # assumed persistence; no real storage
        with self.assertRaises(Refused):
            restarted.claim(context)
        with self.assertRaises(Refused):
            restarted.consume(context)
        self.assertFalse(restarted.effects)

    def test_crash_after_reservation_before_effect_cannot_resume_or_retry(self):
        model, context, receipt = self.prepared()
        execution = model.dispatch(receipt, context, Mode.TARGET_LOCAL)
        model.crash(execution)
        self.assertIs(execution.stage, Stage.BLOCKED)
        with self.assertRaises(Refused):
            model.first_effect(execution)
        with self.assertRaises(Refused):
            model.dispatch(receipt, context, Mode.TARGET_LOCAL)
        self.assertFalse(model.effects)
        self.assertEqual(len(model.target.reservations), 1)

    def test_crash_after_effect_is_unknown_and_replay_refused(self):
        model, context, receipt = self.prepared()
        execution = model.dispatch(receipt, context, Mode.TARGET_LOCAL)
        model.first_effect(execution)
        model.crash(execution)
        self.assertIs(execution.stage, Stage.UNKNOWN)
        with self.assertRaises(Refused):
            model.dispatch(receipt, context, Mode.TARGET_LOCAL)
        self.assertEqual(len(model.effects), 1)
        restarted = deepcopy(model)
        with self.assertRaises(Refused):
            restarted.dispatch(receipt, context, Mode.TARGET_LOCAL)
        self.assertEqual(len(restarted.effects), 1)

    def test_lost_commit_confirmation_does_not_authorize_retry(self):
        model, context, receipt = self.prepared()
        execution = model.dispatch(receipt, context, Mode.TARGET_LOCAL)
        model.first_effect(execution)
        model.finish(execution, committed=True, confirmation=False)
        self.assertIs(execution.stage, Stage.UNKNOWN)
        with self.assertRaises(Refused):
            model.dispatch(receipt, context, Mode.TARGET_LOCAL)

    def test_normal_transaction_rollback_does_not_release_consumption(self):
        model, context, receipt = self.prepared()
        execution = model.dispatch(receipt, context, Mode.TARGET_LOCAL)
        model.first_effect(execution)
        model.finish(execution, committed=False, confirmation=True)
        self.assertIs(execution.stage, Stage.ROLLED_BACK)
        self.assertIs(model.authority.state, AuthorityState.CONSUMED)
        with self.assertRaises(Refused):
            model.dispatch(receipt, context, Mode.TARGET_LOCAL)

    def test_naive_retry_after_rollback_repeats_initiation(self):
        model, context, receipt = self.prepared()
        first = model.dispatch(receipt, context, Mode.PRECHECK)
        model.first_effect(first)
        model.finish(first, committed=False, confirmation=True)
        second = model.dispatch(receipt, context, Mode.PRECHECK)
        model.first_effect(second)
        self.assertEqual(len(model.effects), 2)

    def test_snapshot_without_continuity_loses_anti_replay_marker(self):
        model, context, receipt = self.prepared()
        snapshot = model.snapshot()
        execution = model.dispatch(receipt, context, Mode.TARGET_LOCAL)
        model.first_effect(execution)
        model.unsafe_restore_negative_control(snapshot)
        replay = model.dispatch(receipt, context, Mode.TARGET_LOCAL)
        model.first_effect(replay)
        self.assertEqual(len(model.effects), 2)

    def test_safe_restore_blocks_old_approval_and_old_waiter(self):
        model, context, receipt = self.prepared()
        snapshot = model.snapshot()
        old_waiter = model.dispatch(receipt, context, Mode.TARGET_LOCAL)
        model.restore(snapshot)
        with self.assertRaises(Refused):
            model.dispatch(receipt, context, Mode.TARGET_LOCAL)
        with self.assertRaises(Refused):
            model.first_effect(old_waiter)
        self.assertFalse(model.effects)

    def test_authority_snapshot_before_consumption_can_erase_consumption(self):
        model = Model()
        snapshot = model.snapshot()
        for _ in range(2):
            model.claim(Context())
            receipt = model.consume(Context())
            execution = model.dispatch(receipt, Context(), Mode.TARGET_LOCAL)
            model.first_effect(execution)
            model.unsafe_restore_negative_control(snapshot)
        self.assertEqual(len(model.effects), 2)

    def test_clone_of_same_generation_can_start_twice(self):
        model, context, receipt = self.prepared()
        old_waiter = model.dispatch(receipt, context, Mode.TARGET_LOCAL)
        clone = model.unsafe_clone_negative_control()
        cloned_waiter = deepcopy(old_waiter)
        model.first_effect(old_waiter)
        clone.first_effect(cloned_waiter)
        self.assertEqual(len(model.effects), 2)

    def test_generation_change_blocks_old_waiter(self):
        model, context, receipt = self.prepared()
        waiter = model.dispatch(receipt, context, Mode.TARGET_LOCAL)
        model.target.generation = "generation-2"
        with self.assertRaises(Refused):
            model.first_effect(waiter)
        self.assertFalse(model.effects)

    def test_target_substitution_after_dispatch_blocks(self):
        model, context, receipt = self.prepared()
        waiter = model.dispatch(receipt, context, Mode.TARGET_LOCAL)
        model.target.name = "different-target"
        with self.assertRaises(Refused):
            model.first_effect(waiter)
        self.assertFalse(model.effects)

    def test_precheck_expires_during_lock_wait_but_still_starts(self):
        model, context, receipt = self.prepared()
        execution = model.dispatch(receipt, context, Mode.PRECHECK)
        model.target.locked = True
        self.assertFalse(model.first_effect(execution))
        self.assertFalse(model.effects)
        model.target_time = model.authority_time = Interval(900, 900)
        model.target.locked = False
        self.assertTrue(model.first_effect(execution))  # GAP-002 counterexample

    def test_target_rechecks_expiry_after_lock_wait(self):
        model, context, receipt = self.prepared()
        execution = model.dispatch(receipt, context, Mode.TARGET_LOCAL)
        model.target.locked = True
        self.assertFalse(model.first_effect(execution))
        model.target_time = Interval(899, 900)
        model.target.locked = False
        with self.assertRaises(Refused):
            model.first_effect(execution)
        self.assertFalse(model.effects)

    def test_precheck_revoke_after_dispatch_does_not_prevent_effect(self):
        model, context, receipt = self.prepared()
        execution = model.dispatch(receipt, context, Mode.PRECHECK)
        model.revoke()
        model.first_effect(execution)
        self.assertEqual(len(model.effects), 1)

    def test_target_local_stale_revocation_still_allows_effect(self):
        model, context, receipt = self.prepared()
        execution = model.dispatch(receipt, context, Mode.TARGET_LOCAL)
        model.revoke()  # notification delayed/lost, target epoch still 1
        model.first_effect(execution)
        self.assertEqual(len(model.effects), 1)
        self.assertNotEqual(model.target.revocation_epoch, model.authority.revocation_epoch)

    def test_delivered_revocation_blocks_target_effect(self):
        model, context, receipt = self.prepared()
        execution = model.dispatch(receipt, context, Mode.TARGET_LOCAL)
        model.revoke()
        model.deliver_revocation()
        with self.assertRaises(Refused):
            model.first_effect(execution)
        self.assertFalse(model.effects)

    def test_target_local_clock_rollback_can_allow_expired_effect(self):
        model, context, receipt = self.prepared()
        execution = model.dispatch(receipt, context, Mode.TARGET_LOCAL)
        model.authority_time = Interval(900, 900)
        model.target_time = Interval(5, 5)  # falsely declared trustworthy
        model.first_effect(execution)
        self.assertEqual(len(model.effects), 1)  # dependency on GAP-014

    def test_explicitly_untrusted_target_clock_blocks(self):
        model, context, receipt = self.prepared()
        execution = model.dispatch(receipt, context, Mode.TARGET_LOCAL)
        model.target_time = Interval(5, 5, False)
        with self.assertRaises(Refused):
            model.first_effect(execution)

    def test_partition_after_dispatch_local_starts_ideal_blocks(self):
        for mode in (Mode.TARGET_LOCAL, Mode.IDEAL):
            model, context, receipt = self.prepared()
            execution = model.dispatch(receipt, context, mode)
            model.connected = False
            if mode is Mode.IDEAL:
                with self.assertRaises(Refused):
                    model.first_effect(execution)
            else:
                model.first_effect(execution)
            self.assertEqual(len(model.effects), int(mode is Mode.TARGET_LOCAL))

    def test_all_ideal_schedules_order_against_revoke_expire_partition(self):
        for order in permutations(("effect", "revoke", "expire", "partition")):
            model, context, receipt = self.prepared()
            execution = model.dispatch(receipt, context, Mode.IDEAL)
            for event in order:
                if event == "revoke":
                    model.revoke()
                elif event == "expire":
                    model.target_time = model.authority_time = Interval(900, 900)
                elif event == "partition":
                    model.connected = False
                elif order[0] == "effect":
                    model.first_effect(execution)
                else:
                    with self.subTest(order=order), self.assertRaises(Refused):
                        model.first_effect(execution)
            self.assertEqual(len(model.effects), int(order[0] == "effect"))

    def test_revocation_after_first_effect_does_not_undo_commit(self):
        model, context, receipt = self.prepared()
        execution = model.dispatch(receipt, context, Mode.IDEAL)
        model.first_effect(execution)
        model.revoke()
        model.finish(execution, committed=True, confirmation=True)
        self.assertIs(execution.stage, Stage.COMMITTED)
        self.assertEqual(len(model.effects), 1)


if __name__ == "__main__":
    unittest.main()
