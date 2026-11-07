"""Block two: schemas/projections only. No real observations or collectors."""
from copy import deepcopy
from dataclasses import asdict, replace
from hashlib import sha256
from pathlib import Path
import socket
import subprocess
import unittest
from unittest.mock import patch

from scripts.dedicated.dev09b import codec as c
from scripts.dedicated.dev09b import layers as l
from scripts.dedicated.dev09b import profiles as p
from scripts.dedicated.dev09b import evidence as e
from scripts.postgres.tests.test_dev09b_offline import fixture, uid


def catalog(profile):
    schemas={"public"}
    relations=[]
    if profile != "auth03-base-inventory-v1":
        schemas |= {"inventory","audit"}
        relations=[{"schema":"inventory","name":n,"kind":"r"} for n in
                   "resources resource_identifiers resource_relations groups group_memberships group_rules tags resource_tags policies policy_versions policy_assignments effective_configs".split()]
        relations += [{"schema":"audit","name":"events","kind":"r"},
                      {"schema":"public","name":"alembic_version","kind":"r"}]
    if profile in {"m12b-b12-inventory-v1","g2-f066-b12-d05-v1"}:
        schemas.add("security")
        relations += [{"schema":"security","name":n,"kind":"r"} for n in
                      "local_users login_sessions global_role_grants login_throttles".split()]
        relations += [{"schema":"public","name":"alembic_security_version","kind":"r"}]
    if profile == "g2-f066-b12-d05-v1": schemas |= {"pg_catalog","information_schema","pg_toast"}
    return dict(profile=profile,validator_inventory=p.validator_inventory(profile),schemas=sorted(schemas),
                relations=sorted(relations,key=lambda r:(r["schema"],r["name"])),detailed_catalog={"profile":profile})


def revision_state(chain, rev):
    return dict(ledger_schema="public",ledger_name=l.LEDGERS[chain],
                presence="ABSENT" if rev is None else "PRESENT",revisions=[] if rev is None else [rev])


def bundle(operation="security-base-to-b12b01a7230"):
    approval,target,executor,plan,session=fixture(operation)
    application=operation.startswith("application-")
    before=(None,None) if application else ("f066a01a7230",None)
    after=("f066a01a7230",None) if application else ("f066a01a7230","b12b01a7230")
    chain="application" if application else "security"
    revisions=l.APP_REVISIONS if application else ("b12b01a7230",)
    migrations=[]
    prev=None
    for rev in revisions:
        migrations.append(dict(chain=chain,revision=rev,down_revision=prev,source_path="tests/migrations/"+rev+".py",source_sha256="c"*64))
        prev=rev
    semantic=dict(schema_version=1,operation=operation,
                  before={ch:revision_state(ch,rev) for ch,rev in zip(l.LEDGERS,before)},
                  after={ch:revision_state(ch,rev) for ch,rev in zip(l.LEDGERS,after)},installation_chain=migrations)
    physical=dict(schema_version=1,target_binding_sha256=approval["target_binding_sha256"],
                  before=catalog("auth03-base-inventory-v1" if application else "m12b-f066-inventory-v1"),
                  after=catalog("m12b-f066-inventory-v1" if application else "m12b-b12-inventory-v1"),
                  privilege_plan_sha256=plan["privilege_plan_sha256"],exclusivity_plan_sha256=plan["exclusivity_plan_sha256"])
    source_map={m["source_path"]:m["source_sha256"] for m in migrations}
    for phase in ("before","after"):
        source_map.update({s["path"]:s["sha256"] for s in physical[phase]["validator_inventory"]})
    provenance=dict(schema_version=1,producer_id="fixture",producer_version="v1",producer_sha256="f"*64,
                    source_inventory=[dict(path=k,sha256=v) for k,v in sorted(source_map.items())],
                    tool_inventory=[dict(name="fixture-tool",version="v1",artifact_sha256="d"*64)],generation_id=uid(400))
    executor["source_inventory_sha256"]=l.document_hash(provenance["source_inventory"])
    plan["executor_binding_sha256"]=c.digest("executor",executor)
    plan["migration_sources_sha256"]=l.document_hash(migrations)
    for phase in ("before","after"): plan["expected_"+phase+"_sha256"]=l.expected_hash(semantic,physical,phase)
    approval["execution_plan_sha256"]=c.digest("plan",plan)
    global_doc=dict(schema_version=1,**{k+"_sha256":c.digest(k,obj) for k,obj in
                    (("semantic",semantic),("physical",physical),("provenance",provenance))})
    approval["global_digest_sha256"]=c.digest("global",global_doc)
    return (approval,target,executor,plan,semantic,physical,provenance),replace(session,executor_sha256=c.digest("executor",executor))


def observation(parts,session,phase="BEFORE",result=None):
    approval,target,executor,plan,semantic,physical,provenance=parts
    expected="before" if phase in {"BEFORE","ROLLBACK_CHECK"} else "after"
    result=result or {"BEFORE":"NOT_STARTED","PRECOMMIT":"UNCOMMITTED","POSTCOMMIT":"COMMIT_REPORTED","ROLLBACK_CHECK":"ROLLBACK_REPORTED"}[phase]
    return dict(schema_version=1,evidence_id=uid(500),classification="SYNTHETIC",operation=approval["operation"],phase=phase,
                target_binding_sha256=approval["target_binding_sha256"],request_id=approval["request_id"],
                approval_id=approval["approval_id"],attempt_id=approval["attempt_id"],collector_id="synthetic-primary",
                collector_sources=[dict(path="tests/collector.py",sha256="e"*64)],session_binding=asdict(session),
                observed_interval=dict(lower=110,upper=111),catalog=deepcopy(physical[expected]),
                ledgers=[dict(chain=chain,presence=s["presence"],revisions=list(s["revisions"])) for chain,s in semantic[expected].items()],
                execution_result=result,related_evidence=[plan["prerequisite_evidence_sha256"]])


class LayerTests(unittest.TestCase):
    def setUp(self):
        def denied(*args,**kwargs): raise AssertionError("External operation attempted")
        for owner,name in ((socket,"socket"),(socket,"create_connection"),(socket,"getaddrinfo"),(subprocess,"Popen"),(subprocess,"run")):
            guard=patch.object(owner,name,denied);guard.start();self.addCleanup(guard.stop)
        self.parts,self.session=bundle()
        self.snapshot=l.freeze_expectations(*self.parts)

    def test_both_operations_have_closed_structural_layers_not_full_support(self):
        for op in ("application-base-to-f066a01a7230","security-base-to-b12b01a7230"):
            parts,s=bundle(op);snapshot=l.freeze_expectations(*parts)
            for phase in e.RESULTS:
                evidence=observation(parts,s,phase)
                self.assertIsInstance(e.compare_evidence(snapshot,evidence),e.InventoryComparison)
            with self.assertRaises(c.Unsupported): c.validate_layers(snapshot)

    def test_strict_types_not_python_bool_int_equality(self):
        for index in (4,5,6):
            broken=list(deepcopy(self.parts));broken[index]["schema_version"]=True
            with self.subTest(layer=index),self.assertRaises(c.Invalid): l.freeze_expectations(*broken)
        for field in ("schema_version","observed_interval","session_binding"):
            ev=observation(self.parts,self.session)
            if field=="schema_version": ev[field]=True
            elif field=="observed_interval": ev[field]["lower"]=True
            else: ev[field]["backend_pid"]=True
            with self.subTest(field=field),self.assertRaises(c.Invalid): e.validate_evidence(ev)

    def test_all_layer_objects_closed(self):
        validators=(l.validate_semantic,l.validate_physical,l.validate_provenance)
        for obj,validator in zip(self.parts[4:],validators):
            for key in obj:
                bad=deepcopy(obj);del bad[key]
                with self.subTest(key=key),self.assertRaises(c.Invalid): validator(bad)
            with self.assertRaises(c.Invalid): validator(dict(obj,observations={}))

    def test_every_phase_result_combination(self):
        results={"NOT_STARTED","UNCOMMITTED","COMMIT_REPORTED","ROLLBACK_REPORTED","UNKNOWN"}
        for phase,allowed in e.RESULTS.items():
            for result in results:
                ev=observation(self.parts,self.session,phase,result)
                with self.subTest(phase=phase,result=result):
                    if result in allowed: e.validate_evidence(ev)
                    else:
                        with self.assertRaises(c.Invalid): e.validate_evidence(ev)

    def test_null_matrix_and_partial_nulls(self):
        for phase in e.RESULTS:
            for mask in range(16):
                ev=observation(self.parts,self.session,phase)
                for i,key in enumerate(("request_id","approval_id","attempt_id","session_binding")):
                    if mask & (1<<i): ev[key]=None
                with self.subTest(phase=phase,mask=mask):
                    if mask==0 or (mask==15 and phase=="BEFORE"): e.validate_evidence(ev)
                    else:
                        with self.assertRaises(c.Invalid): e.validate_evidence(ev)

    def test_ledger_absent_present_empty_and_revision_are_distinct(self):
        # PRESENT-empty is structurally valid, never silently treated as ABSENT.
        row=revision_state("security",None);l.revision_state(row,"security")
        row["presence"]="PRESENT";l.revision_state(row,"security")
        row["revisions"]=["b12b01a7230"];l.revision_state(row,"security")
        ev=observation(self.parts,self.session,"POSTCOMMIT")
        ev["ledgers"][1]["revisions"]=[]
        e.validate_evidence(ev)
        with self.assertRaises(c.Invalid): e.compare_evidence(self.snapshot,ev)
        ev["ledgers"][1]["presence"]="ABSENT"
        with self.assertRaises(c.Invalid): e.validate_evidence(ev)
        row=revision_state("security",None);row["presence"]=[]
        with self.assertRaises(c.Invalid): l.revision_state(row,"security")

    def test_truncated_residual_catalog_and_ledger_lies_rejected(self):
        mutations=(lambda x:x["catalog"]["relations"].pop(),
                   lambda x:x["catalog"]["schemas"].append("zombie"),
                   lambda x:x["ledgers"][0]["revisions"].append("f067a01a7230"))
        for mutate in mutations:
            ev=observation(self.parts,self.session);mutate(ev)
            with self.assertRaises(c.Invalid): e.compare_evidence(self.snapshot,ev)

    def test_order_uniqueness_and_path_traversal(self):
        for mutate in (lambda x:x["source_inventory"].append(x["source_inventory"][0]),
                       lambda x:x["source_inventory"].reverse(),
                       lambda x:x["source_inventory"][0].update(path="../outside"),
                       lambda x:x["tool_inventory"].append(x["tool_inventory"][0])):
            prov=deepcopy(self.parts[6]);mutate(prov)
            with self.assertRaises(c.Invalid): l.validate_provenance(prov)
        parts,s=bundle("application-base-to-f066a01a7230")
        parts[4]["installation_chain"].reverse()
        with self.assertRaises(c.Invalid): l.validate_semantic(parts[4])

    def test_version_and_exact_validator_sources(self):
        root=Path(__file__).resolve().parents[3]
        for path,expected in p.SOURCES.items():
            self.assertEqual(sha256((root/path).read_bytes()).hexdigest(),expected)
        for profile in p.PROFILES:
            cat=catalog(profile);l.catalog(cat);p.validate_inventory_projection(cat)
            with self.assertRaises(c.Unsupported): p.require_complete_profile(profile)
        bad=catalog("m12b-f066-inventory-v1")
        bad["validator_inventory"][0]["sha256"]="0"*64
        with self.assertRaises(c.Invalid): l.catalog(bad)
        bad["profile"]="m12b-f066-inventory"
        with self.assertRaises(c.Unsupported): l.catalog(bad)

    def test_opaque_details_never_accepted(self):
        bad=deepcopy(self.parts[5]);bad["after"]["detailed_catalog"]["sha256"]="0"*64
        with self.assertRaises(c.Invalid): l.validate_physical(bad)

    def test_envelope_plan_layer_source_references(self):
        for index,key in ((0,"global_digest_sha256"),(3,"expected_before_sha256"),(3,"expected_after_sha256"),
                          (3,"migration_sources_sha256"),(5,"privilege_plan_sha256"),(5,"target_binding_sha256")):
            bad=list(deepcopy(self.parts));bad[index][key]="0"*64
            if index==3:
                # Preserve the outer plan binding: exercise the inner reference,
                # rather than merely failing its envelope hash.
                bad[0]["execution_plan_sha256"]=c.digest("plan",bad[3])
            with self.subTest(key=key),self.assertRaises(c.Invalid): l.freeze_expectations(*bad)
        bad=list(deepcopy(self.parts));bad[6]["source_inventory"][0]["sha256"]="0"*64
        with self.assertRaises(c.Invalid): l.freeze_expectations(*bad)

    def test_evidence_references_and_no_expectations_inline(self):
        for key in ("operation","target_binding_sha256","request_id","approval_id","attempt_id"):
            ev=observation(self.parts,self.session)
            ev[key]="application-base-to-f066a01a7230" if key=="operation" else ("0"*64 if key.endswith("sha256") else uid(999))
            with self.subTest(key=key),self.assertRaises(c.Invalid): e.compare_evidence(self.snapshot,ev)
        ev=observation(self.parts,self.session);ev["expected"]=self.parts[5]["before"]
        with self.assertRaises(c.Invalid): e.validate_evidence(ev)
        ev=observation(self.parts,self.session);ev["related_evidence"]=[]
        with self.assertRaises(c.Invalid): e.compare_evidence(self.snapshot,ev)

    def test_cannot_reconstruct_expectations_under_fixed_approval(self):
        ev=observation(self.parts,self.session)
        ev["catalog"]["relations"][0]["name"]="changed"
        with self.assertRaises(c.Invalid): e.compare_evidence(self.snapshot,ev)
        bad=list(deepcopy(self.parts));bad[5]["before"]=deepcopy(ev["catalog"])
        with self.assertRaises(c.Invalid): l.freeze_expectations(*bad)
        # Mutation after freezing cannot rewrite the immutable expected bytes.
        self.parts[5]["before"]["relations"].clear()
        goodparts,s=bundle()
        e.compare_evidence(self.snapshot,observation(goodparts,s))

    def test_synthetic_cannot_be_promoted_by_classification(self):
        ev=observation(self.parts,self.session);ev["classification"]="OPERATIONAL"
        e.validate_evidence(ev)  # Merely a structurally valid claim.
        with self.assertRaises(c.Invalid): e.check_operational_origin(ev,e.SyntheticAuthenticity())
        self.assertFalse(e.SyntheticIndependence().confirm(c.canonical(ev),c.canonical(ev)))

    def test_origin_response_must_bind_document_and_collector(self):
        ev=observation(self.parts,self.session);ev["classification"]="OPERATIONAL"
        class Forged:
            def inspect(self,raw): return e.OriginObservation("0"*64,"other","OPERATIONAL",True)
        with self.assertRaises(c.Invalid): e.check_operational_origin(ev,Forged())

    def test_no_profile_can_confirm_base_success_or_rollback(self):
        for phase in ("BEFORE","POSTCOMMIT","ROLLBACK_CHECK"):
            primary=observation(self.parts,self.session,phase);primary["classification"]="OPERATIONAL"
            independent=deepcopy(primary);independent.update(evidence_id=uid(501),collector_id="independent")
            # No invocation of origin/independence can upgrade missing coverage.
            with self.subTest(phase=phase),self.assertRaises(c.Unsupported):
                if phase=="BEFORE": e.confirm_base(self.snapshot,primary,None)
                else: e.confirm_outcome(self.snapshot,primary,independent,None,None)

    def test_independent_pair_must_refer_to_same_execution(self):
        primary=observation(self.parts,self.session,"POSTCOMMIT")
        independent=deepcopy(primary);independent.update(evidence_id=uid(501),collector_id="independent")
        e.check_independent_pair_structure(self.snapshot,primary,independent)
        independent["session_binding"]["transaction_id"]="999"
        with self.assertRaises(c.Invalid): e.check_independent_pair_structure(self.snapshot,primary,independent)
        independent=deepcopy(primary)
        with self.assertRaises(c.Invalid): e.check_independent_pair_structure(self.snapshot,primary,independent)
        independent.update(evidence_id=uid(501),collector_id="independent",execution_result="UNKNOWN")
        with self.assertRaises(c.Invalid): e.check_independent_pair_structure(self.snapshot,primary,independent)

    def test_duplicate_sets_and_cross_catalog_mismatch(self):
        for key in ("schemas","relations"):
            ev=observation(self.parts,self.session);ev["catalog"][key].append(ev["catalog"][key][0])
            with self.subTest(key=key),self.assertRaises(c.Invalid): e.validate_evidence(ev)
        ev=observation(self.parts,self.session)
        ev["related_evidence"]*=2
        with self.assertRaises(c.Invalid): e.validate_evidence(ev)


if __name__ == "__main__": unittest.main()
