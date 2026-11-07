"""Synthetic normalized profiles: no SQL, server, real baseline or collectors."""
from copy import deepcopy
from dataclasses import asdict,replace
from pathlib import Path
import socket
import subprocess
import unittest
from unittest.mock import patch

from scripts.dedicated.dev09b import codec as c
from scripts.dedicated.dev09b import physical as p
from scripts.dedicated.dev09b import migration_catalog as m
from scripts.postgres.tests.test_dev09b_offline import fixture,uid


ROOT=Path(__file__).resolve().parents[3]


def params(target,extracted):
    roles={k:"fixture_"+k for k in p.ROLE_KEYS}
    roles.update(migrator=target["migrator_role"],inspector=target["inspector_role"])
    def administrative(key):
        return dict(name=roles[key],login=True,superuser=True,createdb=False,createrole=False,
                    replication=False,bypassrls=False,inherit=False)
    src=[dict(path="fixtures/approved-artifact",sha256="a"*64)]
    system=p.sort_objects([m.object_record("language",["plpgsql"],dict(properties=[dict(name="trusted",value=True)])),
             m.object_record("routine",["pg_catalog","pg_control_system",""],dict(returns="record",language="internal",
                security_definer=False,body="fixture-symbol",volatility="STABLE",strict=False,parallel="UNSAFE",config=[]))])
    ext=p.sort_objects([m.object_record("opclass",["public","fixture_uuid_ops"],dict(properties=[dict(name="method",value="gist")]))])
    def access(records,owner):
        return ([dict(family=x["family"],identity=x["identity"],owner=owner) for x in records],
                [dict(family=x["family"],identity=x["identity"],grants=[]) for x in records])
    sysowners,sysacls=access(system,roles["database_owner"])
    extowners,extacls=access(ext,roles["database_owner"])
    resolver={}
    tables=[x for x in extracted["application"]+extracted["security"] if x["family"]=="table"]
    tables += [m.object_record("table",["public",n],{}) for n in ("alembic_version","alembic_security_version")]
    for table in tables:
        schema,name=table["identity"]
        resolver[schema+"."+name]=p.sort_objects([
            m.object_record(kind,[schema,name if kind=="composite_type" else "_"+name],
                dict(properties=[dict(name="parent",value=schema+"."+name)]))
            for kind in ("composite_type","array_type")])
    return dict(schema_version=1,target_binding_sha256=c.digest("target",target),roles=roles,
                administrative_roles=[administrative("admin"),administrative("recovery")],
                distribution=dict(image_sha256=target["image_sha256"],server_version_num=160015,
                    template_name="fixture_template",template_sources=src,alembic_sources=src,sqlalchemy_sources=src,
                    encoding="UTF8",collation="fixture_C",ctype="fixture_C",settings=dict(search_path="public",
                    session_replication_role="origin",row_security="on",standard_conforming_strings="on",
                    shared_preload_libraries="",session_preload_libraries="",local_preload_libraries="")),
                btree_gist=dict(version="fixture-version",schema="public",owner=roles["database_owner"],sources=src,members=ext,ownership=extowners,acls=extacls,acl=[]),
                system_objects=system,system_ownership=sysowners,system_acls=sysacls,system_memberships=[],system_default_acl=[],resolver_objects=resolver)


class PhysicalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources=m.load_repository_sources(ROOT)
        cls.extracted=m.extract_sources(cls.sources)

    def setUp(self):
        def denied(*args,**kwargs):raise AssertionError("External operation attempted")
        for owner,name in ((socket,"socket"),(socket,"create_connection"),(socket,"getaddrinfo"),(subprocess,"Popen"),(subprocess,"run")):
            g=patch.object(owner,name,denied);g.start();self.addCleanup(g.stop)
        _,self.target,*_=fixture()
        self.parameters=params(self.target,self.extracted)

    def compile(self,phase):return p.compile_profile(phase,self.target,self.parameters,self.sources)

    def decode(self,expected):return c.parse(expected.json,maximum=len(expected.json))

    def test_seven_prepared_profiles_without_database_create(self):
        phases={"DEV-BASE","APP-F066-PRECOMMIT","APP-F066-PERSISTED","APP-F066-CLOSED",
                "SEC-B12-PRECOMMIT","SEC-B12-PERSISTED","SEC-B12-CLOSED"}
        self.assertEqual(set(p.PHASES),phases)
        for phase in sorted(phases):
            exp=self.compile(phase);obs=self.decode(exp)
            self.assertEqual(p.compare_normalized(exp,obs).phase,phase)
            with self.subTest(phase=phase):
                self.assertIsInstance(p.compare_profile(exp,obs),p.PhysicalComparison)
                self.assertFalse(any(a["privilege"]=="CREATE" for a in obs["database_acl"]))
                self.assertEqual({tuple(o["identity"]) for o in obs["managed_objects"] if o["family"]=="schema"},
                                 {("inventory",),("audit",),("security",)})

    def test_source_derived_known_columns_defaults_and_routines(self):
        app=self.extracted["application"]
        tables={tuple(x["identity"]) for x in app if x["family"]=="table"}
        self.assertEqual(len(tables),13)
        bykey={(x["family"],tuple(x["identity"])):x["definition"] for x in app}
        self.assertEqual(bykey["column",("inventory","resources","administrative_state")]["default"],"'active'")
        self.assertEqual(bykey["column",("audit","events","changes")]["default"],"'{}'::jsonb")
        self.assertFalse(bykey["routine",("audit","prevent_event_mutation","")]["security_definer"])
        self.assertIn(("trigger",("inventory","policy_versions","trg_policy_versions_immutable")),bykey)
        self.assertEqual({tuple(x["identity"]) for x in self.extracted["security"] if x["family"]=="table"},
                         {("security",n) for n in ("local_users","login_sessions","global_role_grants","login_throttles")})
        self.assertTrue(all(x["definition"]["default"] is None for x in self.extracted["security"] if x["family"]=="column"))

    def test_source_change_changes_expectations_not_hidden(self):
        changed=list(self.sources)
        path,raw=changed[0]
        changed[0]=(path,raw.replace(b"'active'",b"'disabled'"))
        self.assertNotEqual(self.compile("APP-F066-CLOSED").json,
                            p.compile_profile("APP-F066-CLOSED",self.target,self.parameters,changed).json)
        # Caller must compare source inventory against approval; no claim of
        # authenticity follows from deterministic extraction alone.

    def test_unknown_migration_syntax_and_missing_source_are_refused(self):
        for replacement in (b"op.execute('CREATE VIEW public.bad AS SELECT 1')",b"raise RuntimeError('not run')"):
            changed=list(self.sources);path,raw=changed[0]
            changed[0]=(path,raw.replace(b'require_prepared_schema("inventory")',replacement))
            with self.assertRaises(c.Unsupported):m.extract_sources(changed)
        with self.assertRaises(c.Invalid):m.extract_sources(self.sources[:-1])

    def test_missing_target_parameters_identify_exact_value(self):
        for keys,wanted in [(("btree_gist","version"),"target_profile.btree_gist.version"),
                            (("distribution","template_sources"),"target_profile.distribution.template_sources"),
                            (("roles","application_ledger_owner"),"target_profile.roles.application_ledger_owner")]:
            bad=deepcopy(self.parameters);del bad[keys[0]][keys[1]]
            with self.subTest(keys=keys),self.assertRaises(m.MissingParameter) as ctx:
                p.compile_profile("DEV-BASE",self.target,bad,self.sources)
            self.assertEqual(ctx.exception.path,wanted)
        self.parameters["resolver_objects"].pop("inventory.resources")
        with self.assertRaisesRegex(m.MissingParameter,"inventory.resources"):
            self.compile("APP-F066-CLOSED")

    def test_owner_handoff_domain_functions_and_separate_ledgers(self):
        r=self.parameters["roles"]
        for phase in ("APP-F066-PRECOMMIT","APP-F066-PERSISTED","APP-F066-CLOSED","SEC-B12-PRECOMMIT","SEC-B12-CLOSED"):
            snap=self.decode(self.compile(phase))
            owners={(x["family"],tuple(x["identity"])):x["owner"] for x in snap["ownership"]}
            with self.subTest(phase=phase):
                appowner=r["inventory_owner"] if phase.endswith("CLOSED") or phase.startswith("SEC-") else r["migrator"]
                self.assertEqual(owners["routine",("inventory","prevent_policy_version_mutation","")],appowner)
                if phase=="SEC-B12-CLOSED":
                    self.assertEqual(owners["table",("public","alembic_version")],r["application_ledger_owner"])
                    self.assertEqual(owners["table",("public","alembic_security_version")],r["security_ledger_owner"])
                    self.assertEqual(owners["array_type",("public","_alembic_security_version")],r["security_ledger_owner"])
                    self.assertNotIn(r["migrator"],owners.values())
                    self.assertFalse(next(x for x in snap["roles"] if x["name"]==r["migrator"])["login"])

    def test_no_runtime_grants_public_connect_temp_or_permanent_memberships(self):
        for phase in p.PHASES:
            s=self.decode(self.compile(phase));runtime=self.parameters["roles"]["runtime"]
            self.assertEqual(s["memberships"],[])
            self.assertTrue(all(a["grantee"]!=runtime for a in s["database_acl"]+s["public_acl"]))
            self.assertFalse(any(a["grantee"]=="PUBLIC" for a in s["database_acl"]))
            self.assertFalse(any(a["grantee"]=="PUBLIC" for x in s["acls"] for a in x["grants"]) if phase.endswith("CLOSED") else False)
            if phase.endswith("CLOSED"):
                self.assertEqual(s["temporary_rights"],[])
                self.assertEqual(len(s["inspection_column_grants"]),14)

    def test_extras_truncation_type_substitution_and_acl_mutations_fail(self):
        exp=self.compile("SEC-B12-CLOSED")
        changes=(lambda s:s["managed_objects"].pop(),lambda s:s["ownership"].pop(),
                 lambda s:s["roles"][0].update(superuser=1),lambda s:s["ledgers"][0].update(revisions=[]),
                 lambda s:s["database_acl"].append(p.grant("PUBLIC","CREATE")),
                 lambda s:s["managed_objects"][0]["definition"].update(properties=[]))
        for change in changes:
            s=self.decode(exp);change(s)
            with self.subTest(change=change),self.assertRaises(c.Invalid):p.compare_normalized(exp,s)
        s=self.decode(exp)
        extra=m.object_record("view",["inventory","unapproved_view"],dict(properties=[dict(name="query",value="fixture")]))
        s["managed_objects"]=p.sort_objects(s["managed_objects"]+[extra])
        with self.assertRaises(c.Invalid):p.compare_normalized(exp,s)

    def test_base_does_not_mean_empty_postgres_cluster(self):
        s=self.decode(self.compile("DEV-BASE"))
        self.assertEqual({o["family"] for o in s["managed_objects"]},{"schema"})
        self.assertEqual(len(s["managed_objects"]),3)
        self.assertTrue(s["system_objects"])
        self.assertEqual(s["extensions"][0]["name"],"btree_gist")
        self.assertEqual([x["presence"] for x in s["ledgers"]],["ABSENT","ABSENT"])

    def test_generation_distribution_extension_and_resolver_inputs_bound(self):
        exp=self.compile("APP-F066-CLOSED")
        for fn in (lambda s:s["distribution"].update(server_version_num=160016),
                   lambda s:s["extensions"][0].update(version="other"),
                   lambda s:s.update(target_binding_sha256="0"*64),
                   lambda s:s["system_objects"].clear()):
            s=self.decode(exp);fn(s)
            with self.assertRaises(c.Invalid):p.compare_profile(exp,s)
        self.parameters["roles"]["security_ledger_owner"]=self.parameters["roles"]["application_ledger_owner"]
        with self.assertRaises(c.Invalid):self.compile("DEV-BASE")

    def test_closed_profile_is_not_persisted_and_no_operational_permission(self):
        closed=self.compile("SEC-B12-CLOSED");persisted=self.decode(self.compile("SEC-B12-PERSISTED"))
        with self.assertRaises(c.Invalid):p.compare_profile(closed,persisted)
        result=p.compare_profile(closed,self.decode(closed))
        self.assertFalse(hasattr(result,"authorize"))
        self.assertFalse(hasattr(result,"confirmed"))

    def test_system_extension_owner_acl_and_membership_coverage(self):
        for key in ("system_ownership","system_acls"):
            bad=deepcopy(self.parameters);bad[key]=[]
            with self.subTest(key=key),self.assertRaises(c.Invalid):
                p.compile_profile("DEV-BASE",self.target,bad,self.sources)
        bad=deepcopy(self.parameters);bad["btree_gist"]["acls"]=[]
        with self.assertRaises(c.Invalid):p.compile_profile("DEV-BASE",self.target,bad,self.sources)

    def test_mutation_or_observation_cannot_rewrite_expectations(self):
        exp=self.compile("APP-F066-CLOSED");obs=self.decode(exp)
        obs["database_acl"].append(p.grant("PUBLIC","CREATE"))
        forged=replace(exp,json=c.canonical(obs))
        with self.assertRaises(c.Invalid):p.compare_normalized(forged,obs)
        self.parameters["system_objects"]=[]
        p.compare_normalized(exp,self.decode(exp))

    def test_independence_not_inferred_from_operational_label(self):
        from scripts.dedicated.dev09b.evidence import SyntheticIndependence,OriginObservation
        exp=self.compile("SEC-B12-CLOSED")
        _,_,_,_,subject=fixture()
        ev=dict(schema_version=1,evidence_id=uid(40),classification="OPERATIONAL",collector_id="primary",
                phase="SEC-B12-CLOSED",target_binding_sha256=c.digest("target",self.target),request_id=uid(41),
                approval_id=uid(42),attempt_id=uid(43),subject_session=asdict(subject),
                observed_interval=dict(lower=100,upper=101),snapshot=self.decode(exp))
        other=deepcopy(ev);other.update(evidence_id=uid(44),collector_id="secondary")
        with self.assertRaises(c.Invalid):
            p.compare_independent_pair(exp,ev,other,p.SyntheticPhaseAuthenticity(),SyntheticIndependence())
        class FixtureOrigin:
            def inspect(self,raw):
                from scripts.dedicated.dev09b.layers import document_hash
                obj=c.parse(raw,maximum=len(raw))
                return OriginObservation(document_hash(obj),obj["collector_id"],"OPERATIONAL",True)
        with self.assertRaises(c.Invalid):p.compare_independent_pair(exp,ev,other,FixtureOrigin(),SyntheticIndependence())
        other["subject_session"]["transaction_id"]="99"
        with self.assertRaises(c.Invalid):p.compare_independent_pair(exp,ev,other,FixtureOrigin(),SyntheticIndependence())
        bad=deepcopy(self.parameters)
        bad["system_memberships"]=[dict(role=self.parameters["roles"]["inventory_owner"],member=self.parameters["roles"]["migrator"],admin=False,inherit=False,set=True)]
        with self.assertRaises(c.Invalid):p.compile_profile("DEV-BASE",self.target,bad,self.sources)


if __name__=="__main__":unittest.main()
