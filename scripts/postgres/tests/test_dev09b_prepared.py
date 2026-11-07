"""Prepared installation preconditions/closure. No upgrade(), SQL or server."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json
import socket
import subprocess
import unittest
from unittest.mock import patch

from backend.migrations import dev09b_prerequisites as h
from scripts.dedicated.dev09b import bundle as b,codec as c,physical as p
from scripts.dedicated.dev09b import migration_catalog as m
from scripts.dedicated.dev09b import layers as l,profiles
from scripts.postgres.tests.test_dev09b_physical import params
from scripts.postgres.tests.test_dev09b_offline import fixture
from scripts.postgres.tests.test_dev09b_layers import bundle,observation,catalog

ROOT=Path(__file__).resolve().parents[3]


def records(operation="application-base-to-f066a01a7230"):
    profile=dict(profile=h.PROFILE,operation=operation,target_sha256="a"*64,bundle_sha256="b"*64,
                 source_inventory_sha256="c"*64,database="livenet_v2_dev",system_identifier="123",migrator="fixture_migrator",
                 schema_owners={s:"fixture_"+s+"_owner" for s in h.SCHEMAS},
                 btree_gist=dict(version="fixture-version",schema="public",owner="fixture_admin",members_sha256="d"*64,acl_sha256="e"*64))
    schemas=["inventory","audit","public"] if operation.startswith("application-") else ["security","public"]
    observed=dict(database=profile["database"],system_identifier=profile["system_identifier"],current_user=profile["migrator"],session_user=profile["migrator"],
                  database_create=False,database_temporary=False,database_owner=False,superuser=False,createdb=False,createrole=False,replication=False,bypassrls=False,
                  extension_install_power=False,memberships=[],schemas={s:dict(owner=o,owner_login=False) for s,o in profile["schema_owners"].items()},
                  extension=profile["btree_gist"],residual_objects=[],schema_create=schemas,schema_usage=schemas,
                  prior_application_confirmed=operation.startswith("security-"),source_inventory_sha256=profile["source_inventory_sha256"])
    return profile,observed


class PreparedTests(unittest.TestCase):
    def setUp(self):
        def denied(*a,**kw):raise AssertionError("External operation attempted")
        for owner,name in ((socket,"socket"),(socket,"create_connection"),(socket,"getaddrinfo"),(subprocess,"Popen"),(subprocess,"run")):
            g=patch.object(owner,name,denied);g.start();self.addCleanup(g.stop)
        self.profile,self.observed=records()

    def test_both_chains_require_no_database_create_and_exact_schema_scope(self):
        for op,requested in (("application-base-to-f066a01a7230","inventory"),("security-base-to-b12b01a7230","security")):
            profile,observed=records(op)
            h.decode_profile(json.dumps(profile).encode())
            h.validate_observation(profile,observed,requested)
            for key in ("database_create","database_temporary","database_owner","superuser","createdb","createrole","replication","bypassrls","extension_install_power"):
                for value in (True,0,1):
                    bad=dict(observed,**{key:value})
                    with self.subTest(op=op,key=key,value=value),self.assertRaises(h.PrerequisiteRefused):h.validate_observation(profile,bad,requested)

    def test_schema_extension_residues_owners_acl_and_baseline_divergence(self):
        changes=(lambda o:o["schemas"].pop("audit"),lambda o:o["schemas"]["inventory"].update(owner="wrong"),
                 lambda o:o["schemas"]["audit"].update(owner_login=True),lambda o:o["extension"].update(version="wrong"),
                 lambda o:o["extension"].update(acl_sha256="0"*64),lambda o:o.update(residual_objects=["unexpected"]),
                 lambda o:o.update(memberships=["owner"]),lambda o:o.update(schema_create=["inventory","audit","public","security"]),
                 lambda o:o.update(schema_usage=[]),lambda o:o.update(source_inventory_sha256="0"*64))
        for change in changes:
            observed=deepcopy(self.observed);change(observed)
            with self.assertRaises(h.PrerequisiteRefused):h.validate_observation(self.profile,observed,"inventory")
        profile,observed=records("security-base-to-b12b01a7230");observed["prior_application_confirmed"]=False
        with self.assertRaises(h.PrerequisiteRefused):h.validate_observation(profile,observed,"security")

    def test_missing_profile_and_live_port_cannot_be_replaced_by_flags(self):
        for value in (True,{"approved":True},"DEV09B-PREPARED-1"):
            with self.assertRaises(h.MissingParameter):h.require_prepared_schema("inventory",context=value)
        ctx=h.PreparedContext(json.dumps(self.profile).encode(),None)
        with self.assertRaisesRegex(h.MissingParameter,"live_prerequisite"):h.require_prepared_schema("inventory",context=ctx)
        class OfflinePort:
            def verify_approved_profile(self,raw):return h.ProfileAttestation(sha256(raw).hexdigest(),"a"*64,"b"*64,False,"SYNTHETIC")
            def observe(self,*args):raise AssertionError("Must refuse before observation")
        with self.assertRaises(h.PrerequisiteRefused):h.require_prepared_schema("inventory",context=h.PreparedContext(ctx.profile_json,OfflinePort()))

    def test_environment_gate_precedes_alembic_and_ledger_creation(self):
        import ast
        from types import SimpleNamespace
        with self.assertRaisesRegex(RuntimeError,"externa"):
            h.require_prepared_environment(SimpleNamespace(attributes={}))
        connection=SimpleNamespace(in_transaction=lambda:True,dialect=SimpleNamespace(name="postgresql"))
        with self.assertRaises(h.MissingParameter):h.require_prepared_environment(SimpleNamespace(attributes={"connection":connection}))
        for f in ("backend/migrations/env.py","backend/security_migrations/env.py"):
            tree=ast.parse((ROOT/f).read_text())
            guards=[x.lineno for x in ast.walk(tree) if isinstance(x,ast.Call) and isinstance(x.func,ast.Name) and x.func.id=="require_prepared_environment"]
            mutations=[x.lineno for x in ast.walk(tree) if isinstance(x,ast.Call) and isinstance(x.func,ast.Attribute) and x.func.attr in {"configure","run_migrations","create_engine"}]
            self.assertEqual(len(guards),1)
            self.assertTrue(all(guards[0]<line for line in mutations))

    def test_concrete_profile_fields_are_required_and_downgrade_refused(self):
        for key in self.profile:
            bad=dict(self.profile);del bad[key]
            with self.assertRaises(h.MissingParameter):h.decode_profile(json.dumps(bad).encode())
        for key in self.profile["btree_gist"]:
            bad=deepcopy(self.profile);del bad["btree_gist"][key]
            with self.assertRaises(h.MissingParameter):h.decode_profile(json.dumps(bad).encode())
        with self.assertRaises(h.PrerequisiteRefused):h.refuse_prepared_downgrade()

    def test_all_five_revised_sources_have_exact_prerequisite_not_provisioning(self):
        src=m.load_repository_sources(ROOT);m.extract_sources(src)
        wanted={"af62df027d9d":"schema","f066a01a7230":"schema","b12b01a7230":"schema","ba06dd956da9":"extension","9e1b7c42a630":"extension"}
        for path,raw in src:
            rev=Path(path).name.split('_')[0]
            if rev in wanted:
                text=raw.decode()
                self.assertNotIn('op.execute("CREATE SCHEMA',text)
                self.assertNotIn('op.execute("CREATE EXTENSION',text)
                self.assertIn("require_prepared_"+wanted[rev]+"(",text)
        # Old CREATE SCHEMA cannot be inserted behind a legitimate guard either.
        path,raw=src[0];bad=list(src)
        bad[0]=(path,raw.replace(b'require_prepared_schema("inventory")',b'require_prepared_schema("inventory")\n    op.execute("CREATE SCHEMA inventory")'))
        with self.assertRaises(c.Unsupported):m.extract_sources(bad)

    def test_new_candidate_checks_sources_locks_and_declares_missing_crypto_lock(self):
        candidate=b.build_candidate(ROOT);obs=b.verify_candidate(ROOT,candidate)
        self.assertGreater(obs.source_count,52)
        self.assertFalse(candidate["operational_authority"])
        self.assertEqual(candidate["status"],"CANDIDATE_NOT_APPROVED")
        self.assertIn("backend/migrations/dev09b_prerequisites.py",[x["path"] for x in candidate["sources"]])
        with self.assertRaisesRegex(m.MissingParameter,"cryptography"):b.require_complete_candidate(ROOT,candidate)
        for mutate in (lambda x:x["sources"].pop(),lambda x:x["sources"][0].update(sha256="0"*64),
                       lambda x:x["dependency_locks"][0].update(sha256="0"*64),lambda x:x.update(missing_parameters=[])):
            bad=deepcopy(candidate);mutate(bad)
            with self.assertRaises(c.Invalid):b.verify_candidate(ROOT,bad)

    def test_revised_physical_profiles_no_schema_handoff_or_database_create(self):
        _,target,*_=fixture();src=m.load_repository_sources(ROOT);ex=m.extract_sources(src);parameters=params(target,ex)
        for phase in p.PHASES:
            expected=p.compile_profile(phase,target,parameters,src)
            snapshot=c.parse(expected.json,maximum=len(expected.json))
            p.compare_profile(expected,snapshot)
            self.assertFalse(any(a["privilege"]=="CREATE" for a in snapshot["database_acl"]))
            for owner in snapshot["ownership"]:
                if owner["family"]=="schema":self.assertEqual(owner["owner"],parameters["roles"][owner["identity"][0]+"_owner"])

    def test_prepared_layer_references_without_relabelling_legacy_profiles(self):
        parts,subject=bundle()
        approval,target,executor,plan,semantic,physical,provenance=parts
        physical["before"].update(profile="dev09b-prepared-f066-v1",schemas=["audit","inventory","public","security"],
                    validator_inventory=profiles.validator_inventory("dev09b-prepared-f066-v1"),detailed_catalog={"profile":"dev09b-prepared-f066-v1"})
        physical["after"].update(profile="dev09b-prepared-b12-v1",validator_inventory=profiles.validator_inventory("dev09b-prepared-b12-v1"),detailed_catalog={"profile":"dev09b-prepared-b12-v1"})
        inventory={s["path"]:s["sha256"] for s in provenance["source_inventory"]};inventory.update(profiles.PREPARED_SOURCES)
        provenance["source_inventory"]=[dict(path=k,sha256=v) for k,v in sorted(inventory.items())]
        executor["source_inventory_sha256"]=l.document_hash(provenance["source_inventory"])
        plan["executor_binding_sha256"]=c.digest("executor",executor)
        for phase in ("before","after"):plan["expected_"+phase+"_sha256"]=l.expected_hash(semantic,physical,phase)
        approval["execution_plan_sha256"]=c.digest("plan",plan)
        approval["global_digest_sha256"]=c.digest("global",dict(schema_version=1,**{k+"_sha256":c.digest(k,obj) for k,obj in
                                      (("semantic",semantic),("physical",physical),("provenance",provenance))}))
        snapshot=l.freeze_expectations(*parts)
        bad=deepcopy(physical);bad["before"]["profile"]="m12b-f066-inventory-v1"
        with self.assertRaises(c.Invalid):l.freeze_expectations(approval,target,executor,plan,semantic,bad,provenance)
        self.assertIsInstance(snapshot,l.ExpectationSnapshot)


if __name__=="__main__":unittest.main()
