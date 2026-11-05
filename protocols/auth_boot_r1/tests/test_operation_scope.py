"""Scope regressions: arbitrary SQL and incomplete metadata are never promoted."""

from dataclasses import replace
import unittest

from protocols.auth_boot_r1.operation_scope import (
    CANDIDATE_OPERATION, LabFacts, OperationClass, assess_lab_candidate,
)


def synthetic_candidate():
    return LabFacts(
        operation_id=CANDIDATE_OPERATION,
        operation_class=OperationClass.DML,
        statement_count=1,
        fixed_update_only=True,
        primary_key_and_version_predicate=True,
        preexisting_local_logged_table=True,
        no_triggers_rules_or_generated_columns=True,
        no_defaults_sequences_or_user_functions=True,
        no_foreign_keys_cascades_or_rls=True,
        no_partitions_inheritance_or_foreign_tables=True,
        fixed_typed_parameters_no_client_sql=True,
        exclusive_entrypoint_no_direct_dml=True,
    )


class OperationScopeTests(unittest.TestCase):
    def test_minimum_candidate_is_only_a_lab_candidate(self):
        result = assess_lab_candidate(synthetic_candidate())
        self.assertEqual(result.classification, "LAB_CANDIDATE")
        self.assertEqual(result.reasons, ())
        self.assertFalse(result.operationally_supported)

    def test_every_unknown_false_or_truthy_fact_excludes(self):
        facts = synthetic_candidate()
        for name in LabFacts.__dataclass_fields__:
            if name in {"operation_id", "operation_class", "statement_count"}:
                continue
            for value in (None, False, 1, "true"):
                with self.subTest(name=name, value=value):
                    result = assess_lab_candidate(replace(facts, **{name: value}))
                    self.assertEqual(result.classification, "EXCLUDED")
                    self.assertIn(name.upper(), result.reasons)

    def test_no_other_class_can_be_promoted_by_its_name(self):
        for kind in OperationClass:
            if kind is OperationClass.DML:
                continue
            with self.subTest(kind=kind):
                result = assess_lab_candidate(replace(synthetic_candidate(), operation_class=kind))
                self.assertEqual(result.classification, "EXCLUDED")

    def test_sql_text_or_real_operations_are_not_allowlisted(self):
        for name in ("UPDATE cell SET value=1", "upgrade-auth03", "login", "create_resource", "lab.single_row_compare_and_set.v2"):
            with self.subTest(name=name):
                result = assess_lab_candidate(replace(synthetic_candidate(), operation_id=name))
                self.assertEqual(result.classification, "EXCLUDED")

    def test_multi_statement_and_unknown_counts_are_excluded(self):
        for count in (None, 0, 2, True, 1.0, "1"):
            with self.subTest(count=count):
                result = assess_lab_candidate(replace(synthetic_candidate(), statement_count=count))
                self.assertEqual(result.classification, "EXCLUDED")

    def test_dml_label_alone_cannot_satisfy_scope(self):
        facts = LabFacts(CANDIDATE_OPERATION, OperationClass.DML)
        result = assess_lab_candidate(facts)
        self.assertEqual(result.classification, "EXCLUDED")
        self.assertFalse(result.operationally_supported)

    def test_string_class_and_arbitrary_objects_are_not_accepted(self):
        for facts in (None, {}, replace(synthetic_candidate(), operation_class="DML")):
            with self.subTest(facts=facts):
                self.assertEqual(assess_lab_candidate(facts).classification, "EXCLUDED")


if __name__ == "__main__":
    unittest.main()
