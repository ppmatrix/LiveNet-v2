"""Offline transaction/ordering counterexamples; no PostgreSQL or SQL execution."""

from dataclasses import replace
from itertools import permutations
import unittest

from protocols.auth_boot_r1.initiation_model import Context, Refused
from protocols.auth_boot_r1.postgres_boundary import (
    CheckEffectCounterexample, Marker, MarkerStudy, WouldWait,
)


class PostgresBoundaryTests(unittest.TestCase):
    def test_in_transaction_marker_is_lost_with_protected_rollback(self):
        ledger = MarkerStudy()
        marker = Marker("authority", Context())
        effects = 0  # independent observer, not a commit ledger
        for transaction in ("first", "replay"):
            ledger.reserve(transaction, marker)
            effects += 1
            ledger.rollback(transaction)
        self.assertEqual(effects, 2)
        self.assertFalse(ledger.committed)

    def test_separately_committed_burn_survives_protected_rollback(self):
        ledger = MarkerStudy()
        marker = Marker("authority", Context())
        ledger.reserve("control", marker)
        ledger.commit("control")
        ledger.rollback("protected")
        with self.assertRaises(Refused):
            ledger.reserve("replay", marker)
        self.assertEqual(ledger.committed, [marker])

    def test_unique_conflict_waits_then_refuses_after_commit(self):
        for first, second in permutations(("worker-1", "worker-2")):
            ledger = MarkerStudy()
            marker = Marker("authority", Context())
            ledger.reserve(first, marker)
            with self.assertRaises(WouldWait):
                ledger.reserve(second, marker)
            ledger.commit(first)
            with self.assertRaises(Refused):
                ledger.reserve(second, marker)
            self.assertEqual(len(ledger.committed), 1)

    def test_rollback_unblocks_competitor_showing_missing_durable_burn(self):
        ledger = MarkerStudy()
        marker = Marker("authority", Context())
        ledger.reserve("first", marker)
        with self.assertRaises(WouldWait):
            ledger.reserve("second", marker)
        ledger.rollback("first")
        ledger.reserve("second", marker)
        ledger.commit("second")
        self.assertEqual(len(ledger.committed), 1)

    def test_new_attempt_does_not_reuse_approval(self):
        ledger = MarkerStudy()
        marker = Marker("authority", Context())
        ledger.reserve("first", marker)
        ledger.commit("first")
        changed = Marker("authority", replace(marker.context, attempt="new-attempt"))
        with self.assertRaises(Refused):
            ledger.reserve("second", changed)

    def test_new_approval_does_not_reuse_attempt(self):
        ledger = MarkerStudy()
        marker = Marker("authority", Context())
        ledger.reserve("first", marker)
        ledger.commit("first")
        changed = Marker("authority", replace(marker.context, approval="new-approval"))
        with self.assertRaises(Refused):
            ledger.reserve("second", changed)

    def test_new_context_or_generation_does_not_change_unique_scope(self):
        for field in ("executor", "incarnation", "session", "transaction", "target", "generation", "plan"):
            ledger = MarkerStudy()
            marker = Marker("authority", Context())
            ledger.reserve("first", marker)
            ledger.commit("first")
            changed = Marker("authority", replace(marker.context, **{field: "changed"}))
            with self.subTest(field=field), self.assertRaises(Refused):
                ledger.reserve("second", changed)

    def test_crash_discards_only_uncommitted_model_writes(self):
        ledger = MarkerStudy()
        first = Marker("authority", Context())
        other = Marker("authority", replace(Context(), approval="other", attempt="other"))
        ledger.reserve("committed", first)
        ledger.commit("committed")
        ledger.reserve("pending", other)
        ledger.crash()
        self.assertEqual(ledger.committed, [first])
        self.assertFalse(ledger.pending)

    def test_committed_marker_does_not_stop_unmediated_sql(self):
        ledger = MarkerStudy()
        ledger.reserve("control", Marker("authority", Context()))
        ledger.commit("control")
        unmediated = CheckEffectCounterexample()
        unmediated.check()
        unmediated.first_effect_after_check()
        unmediated.first_effect_after_check()
        self.assertEqual(len(ledger.committed), 1)
        self.assertEqual(unmediated.effects, 2)

    def test_transaction_timestamp_can_be_stale_at_check_itself(self):
        model = CheckEffectCounterexample()
        model.now = 901
        model.check(transaction_timestamp=True)
        model.first_effect_after_check()
        self.assertEqual(model.effects, 1)
        with self.assertRaises(Refused):
            model.check(transaction_timestamp=False)

    def test_clock_timestamp_check_still_has_post_check_pause(self):
        model = CheckEffectCounterexample()
        model.now = 899
        model.check()  # even a fresh server clock observation
        model.now = 901  # suspension/lock wait before catalog/tuple change
        model.first_effect_after_check()
        self.assertEqual(model.effects, 1)

    def test_target_row_lock_only_orders_target_application_of_revocation(self):
        model = CheckEffectCounterexample()
        model.row_lock_held = True
        model.check()
        model.request_revocation()
        self.assertFalse(model.try_apply_revocation_at_target())
        model.first_effect_after_check()
        self.assertTrue(model.revocation_requested)
        self.assertFalse(model.target_revoked)
        self.assertEqual(model.effects, 1)
        model.row_lock_held = False
        self.assertTrue(model.try_apply_revocation_at_target())

    def test_target_applied_revocation_is_seen_by_later_local_check(self):
        model = CheckEffectCounterexample()
        model.request_revocation()
        self.assertTrue(model.try_apply_revocation_at_target())
        with self.assertRaises(Refused):
            model.check()


if __name__ == "__main__":
    unittest.main()
