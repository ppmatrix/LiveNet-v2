"""Versioned offline phase profiles, source-derived catalog and minimal ACL.

No SQL, collectors, authority or operational permission. Inputs are normalized
declarations, NOT arbitrary pg_get_* SQL strings. Missing distribution/resolver
inputs are refused. Legacy G2 completeness claims are deliberately not reused.
"""
from dataclasses import dataclass
from types import MappingProxyType

from . import codec as c
from .layers import document_hash, name, source, sources, ordered_set
from .migration_catalog import MissingParameter, exact, extract_sources, object_record


PHASES = MappingProxyType({
    "DEV-BASE": (False,False,False),
    "APP-ENTRY": (False,False,False),
    "APP-F066-PRECOMMIT": (True,False,False),
    "APP-F066-PERSISTED": (True,False,False),
    "APP-F066-CLOSED": (True,False,True),
    "SEC-B12-PRECOMMIT": (True,True,False),
    "SEC-B12-PERSISTED": (True,True,False),
    "SEC-B12-CLOSED": (True,True,True),
})
ROLE_KEYS=frozenset("database_owner inventory_owner audit_owner security_owner application_ledger_owner security_ledger_owner admin recovery migrator inspector runtime".split())
FAMILIES=frozenset("schema table column constraint index routine trigger composite_type array_type base_type toast sequence view materialized_view foreign_table policy rule partition extension operator opclass opfamily cast collation language role".split())
PARAMS=frozenset("schema_version target_binding_sha256 distribution roles administrative_roles btree_gist system_objects system_ownership system_acls system_memberships system_default_acl resolver_objects".split())


def ace(a):
    c.closed(a,{"grantee","privilege","grant_option"})
    if a["grantee"]!="PUBLIC":name(a["grantee"])
    c.require(type(a["privilege"]) is str and a["privilege"] in {
        "CONNECT","CREATE","TEMPORARY","USAGE","EXECUTE","SELECT","INSERT","UPDATE","DELETE","TRUNCATE","REFERENCES","TRIGGER"})
    c.require(type(a["grant_option"]) is bool)


def acl(values):
    ordered_set(values,lambda x:(x["grantee"],x["privilege"]),ace)


def grant(who,privilege):return {"grantee":who,"privilege":privilege,"grant_option":False}


def shape_object(o):
    c.closed(o,{"family","identity","definition"})
    c.require(type(o["family"]) is str and o["family"] in FAMILIES)
    c.require(type(o["identity"]) is list and 1<=len(o["identity"])<=3)
    for value in o["identity"]:c.require(type(value) is str and value.isascii() and len(value)<=128)
    d=o["definition"];c.require(type(d) is dict)
    # Source-defined objects have closed typed definitions, not opaque hashes.
    fields={
        "schema":set(),
        "table":{"persistence","row_security","force_row_security"},
        "column":{"position","type","nullable","default","identity","generated"},
        "constraint":{"kind","columns","references","expression","operators","using","predicate","validated","deferrable","initially_deferred"},
        "index":{"table","columns","unique","primary","method","predicate","constraint","valid","ready"},
        "routine":{"returns","language","security_definer","body","volatility","strict","parallel","config"},
        "trigger":{"timing","events","row","function","enabled","internal"},
    }
    if o["family"] in fields:
        c.closed(d,fields[o["family"]])
        if o["family"]=="column":
            c.integer(d["position"],1);c.closed(d["type"],{"name","arguments"})
            c.require(type(d["type"]["name"]) is str and type(d["type"]["arguments"]) is list)
            for v in d["type"]["arguments"]:c.integer(v)
        for k in ("row_security","force_row_security","nullable","validated","deferrable","initially_deferred",
                  "unique","primary","valid","ready","security_definer","strict","row","internal"):
            if k in d:c.require(type(d[k]) is bool)
    else:
        # Distribution-owned server objects: fixed property normal form from
        # a separately approved artifact resolver. It cannot assert completeness.
        c.closed(d,{"properties"})
        ordered_set(d["properties"],lambda x:x["name"],property_record)
    c.canonical(o)


def property_record(p):
    c.closed(p,{"name","value"});c.identifier(p["name"])
    c.require(p["value"] is None or type(p["value"]) in {str,int,bool})
    c.canonical(p)


def objects(values):
    ordered_set(values,lambda x:(x["family"],tuple(x["identity"])),shape_object)


def access_inventory(owned,permissions,records):
    """Every selected object must have explicit owner AND expanded ACL coverage."""
    def identity(x,fields):
        c.closed(x,fields)
        c.require(type(x["family"]) is str and type(x["identity"]) is list
                  and all(type(v) is str for v in x["identity"]))
    def owner(x):
        identity(x,{"family","identity","owner"});name(x["owner"])
    def permission(x):
        identity(x,{"family","identity","grants"});acl(x["grants"])
    key=lambda x:(x["family"],tuple(x["identity"]))
    ordered_set(owned,key,owner);ordered_set(permissions,key,permission)
    wanted={key(x) for x in records if x["family"]!="role"}
    c.require({key(x) for x in owned}==wanted and {key(x) for x in permissions}==wanted)


def sort_objects(values):
    result=sorted(values,key=lambda x:(x["family"],tuple(x["identity"])))
    objects(result)
    return result


def validate_parameters(p,target):
    exact(p,PARAMS,"target_profile");c.integer(p["schema_version"],1,2)
    c.validate_target(target)
    c.require(p["target_binding_sha256"]==c.digest("target",target))
    r=p["roles"];exact(r,ROLE_KEYS,"target_profile.roles")
    for v in r.values():name(v)
    role_values=list(r.values())
    if p['schema_version']==2 and r['database_owner']==r['admin']:
        # Existing querytrial admin owns its DB; this alias adds no powers.
        role_values=[value for key,value in r.items() if key!='database_owner']
    c.require(len(set(role_values))==len(role_values))
    c.require(r["migrator"]==target["migrator_role"] and r["inspector"]==target["inspector_role"])
    c.require(type(p["administrative_roles"]) is list)
    if not p["administrative_roles"]:raise MissingParameter("target_profile.administrative_roles")
    c.require({x.get("name") for x in p["administrative_roles"]}=={r["admin"],r["recovery"]})
    for role in p["administrative_roles"]:validate_role(role)
    d=p["distribution"]
    distribution_fields={"image_sha256","server_version_num","template_name","template_sources","alembic_sources","sqlalchemy_sources","encoding","collation","ctype","settings"}
    if p["schema_version"] == 2:distribution_fields.add("locale_provider")
    exact(d,distribution_fields,"target_profile.distribution")
    if p["schema_version"] == 2:
        if not d["locale_provider"]:raise MissingParameter("target_profile.distribution.locale_provider")
        if d["locale_provider"] != "libc":raise c.Unsupported("Detailed application profile supports libc only")
    c.digest_text(d["image_sha256"]);c.require(d["image_sha256"]==target["image_sha256"])
    c.integer(d["server_version_num"],160000,169999)
    for k in ("template_name","encoding","collation","ctype"):
        if type(d[k]) is not str or not d[k]:raise MissingParameter("target_profile.distribution."+k)
    sources(d["template_sources"])
    if not d["template_sources"]:raise MissingParameter("target_profile.distribution.template_sources")
    for k in ("alembic_sources","sqlalchemy_sources"):
        sources(d[k])
        if not d[k]:raise MissingParameter("target_profile.distribution."+k)
    exact(d["settings"],{"search_path","session_replication_role","row_security","standard_conforming_strings",
          "shared_preload_libraries","session_preload_libraries","local_preload_libraries"},"target_profile.distribution.settings")
    c.require(d["settings"]["session_replication_role"]=="origin" and d["settings"]["row_security"]=="on"
              and d["settings"]["standard_conforming_strings"]=="on")
    for v in d["settings"].values():c.require(type(v) is str)
    ext=p["btree_gist"]
    exact(ext,{"version","schema","owner","sources","members","ownership","acls","acl"},"target_profile.btree_gist")
    if type(ext["version"]) is not str or not ext["version"]:raise MissingParameter("target_profile.btree_gist.version")
    name(ext["schema"]);name(ext["owner"])
    if ext["schema"]!="public":raise c.Unsupported("Existing migration search_path requires reviewed btree_gist schema visibility")
    c.require(ext["owner"] not in {r["migrator"],r["runtime"]})
    sources(ext["sources"]);objects(ext["members"]);acl(ext["acl"])
    access_inventory(ext["ownership"],ext["acls"],ext["members"])
    for key in ("sources","members"):
        if not ext[key]:raise MissingParameter("target_profile.btree_gist."+key)
    objects(p["system_objects"]);acl(p["system_default_acl"])
    if not any(o["family"]=="routine" and o["identity"]==["pg_catalog","pg_control_system",""] for o in p["system_objects"]):
        raise MissingParameter("target_profile.system_objects.pg_catalog.pg_control_system()")
    access_inventory(p["system_ownership"],p["system_acls"],p["system_objects"])
    def membership(edge):
        c.closed(edge,{"role","member","admin","inherit","set"})
        name(edge["role"]);name(edge["member"])
        for k in ("admin","inherit","set"):c.require(type(edge[k]) is bool)
        c.require(not {edge["role"],edge["member"]}&{r["migrator"],r["runtime"]})
    ordered_set(p["system_memberships"],lambda x:(x["role"],x["member"]),membership)
    if not p["system_objects"]:raise MissingParameter("target_profile.system_objects")
    # Every table's implicit type/array/TOAST/index resolver output is needed.
    c.require(type(p["resolver_objects"]) is dict)
    for table,values in p["resolver_objects"].items():
        c.require(type(table) is str);objects(values)
    return p


def ledger(table):
    return [object_record("table",["public",table],dict(persistence="p",row_security=False,force_row_security=False)),
            object_record("column",["public",table,"version_num"],dict(position=1,type={"name":"sa.String","arguments":[32]},nullable=False,default=None,identity="",generated="")),
            object_record("constraint",["public",table,table+"_pkc"],dict(kind="p",columns=["version_num"],references=[],expression=None,operators=[],using=None,predicate=None,validated=True,deferrable=False,initially_deferred=False)),
            object_record("index",["public",table+"_pkc"],dict(table=table,columns=["version_num"],unique=True,primary=True,method="btree",predicate=None,constraint=table+"_pkc",valid=True,ready=True))]


def role_for(o,phase,r):
    app,sec,closed=PHASES[phase]
    schema=o["identity"][0]
    if o["family"]=="schema":return r[schema+"_owner"]
    if schema=="public":
        table=o["definition"].get("table",o["identity"][1])
        if table.startswith("alembic_security_version"):
            return r["security_ledger_owner"] if closed else r["migrator"]
        return r["application_ledger_owner"] if closed or sec else r["migrator"]
    if schema=="security":return r["security_owner"] if closed else r["migrator"]
    return r[schema+"_owner"] if closed or sec else r["migrator"]


def compile_profile(phase,target,parameters,migrations,*,prerequisite=None):
    if type(phase) is not str or phase not in PHASES:raise c.Unsupported("Unknown physical phase profile")
    validate_parameters(parameters,target)
    if phase=="APP-ENTRY" and parameters["schema_version"]!=2:
        raise c.Unsupported("APP-ENTRY requires versioned detailed parameters")
    if parameters["schema_version"]==2 and PHASES[phase][1]:
        raise c.Unsupported("Detailed v2 security profiles are not implemented")
    m=extract_sources(migrations,application_only=parameters["schema_version"]==2)
    app,sec,closed=PHASES[phase];r=parameters["roles"]
    managed=[object_record("schema",[s],{}) for s in ("inventory","audit","security")]
    owner_overrides={}
    if app:managed+=m["application"]+ledger("alembic_version")
    if sec:managed+=m["security"]+ledger("alembic_security_version")
    if prerequisite is not None:
        c.require(phase=='APP-ENTRY' and parameters['schema_version']==2)
        c.integer(prerequisite,0,4)
        prior=(None,None,'da34876e4210','7c4e2a91b605','f065d01a7230')[prerequisite]
        if prerequisite:managed+=ledger('alembic_version')
        if prior is not None:managed+=m['application_progress'][prior]
    if (app or prerequisite is not None) and parameters['schema_version']==2:
        from .migration_catalog import foreign_key_triggers
        managed+=foreign_key_triggers(managed)
    for table in [".".join(x["identity"]) for x in managed if x["family"]=="table"]:
        if table not in parameters["resolver_objects"]:raise MissingParameter("target_profile.resolver_objects."+table)
        implicit=parameters["resolver_objects"][table]
        if not {"composite_type","array_type"}<={x["family"] for x in implicit}:
            raise MissingParameter("target_profile.resolver_objects."+table+".row_and_array_types")
        # Resolver records are source inputs for implicit server objects only.
        c.require(all(x["family"] in {"composite_type","array_type","toast"} for x in implicit))
        parent=next(x for x in managed if x["family"]=="table" and ".".join(x["identity"])==table)
        for obj in implicit:owner_overrides[(obj["family"],tuple(obj["identity"]))]=role_for(parent,phase,r)
        managed+=implicit
    managed=sort_objects(managed)
    ownership=[];acls=[]
    for o in managed:
        owner=owner_overrides.get((o["family"],tuple(o["identity"]))) or role_for(o,phase,r)
        ownership.append({"family":o["family"],"identity":o["identity"],"owner":owner})
        values=[grant("PUBLIC","EXECUTE")] if o["family"]=="routine" and not (closed or sec) else []
        if parameters["schema_version"]==2 and o["family"] in {"composite_type","array_type"}:
            # Explicit human approval: represent acldefault('T') for dependent
            # types whose typacl is NULL (pg_type.c / acl.c). No GRANT is issued;
            # underlying table/schema/function/runtime ACLs are unchanged.
            values=[grant("PUBLIC","USAGE")]
        if (closed or sec) and o["family"]=="schema" and o["identity"][0] in {"inventory","audit"}:
            values=[grant(r["inspector"],"USAGE")]
        # No runtime grants, no broad default privileges. Inherited owner rights
        # are represented by ownership, not confused with an empty ACL.
        acls.append({"family":o["family"],"identity":o["identity"],"grants":values})
    window=(app or phase=="APP-ENTRY") and not closed
    db_acl=[grant(r[k],"CONNECT") for k in ("admin","recovery","inspector","migrator")]
    if parameters['schema_version']==2:
        # An explicitly inert NOLOGIN recovery identity in a rollback-only
        # declaration needs no dormant CONNECT grant. Legacy v1 is unchanged.
        inert={role['name'] for role in parameters['administrative_roles'] if role['login'] is False}
        db_acl=[a for a in db_acl if a['grantee'] not in inert]
        if r['database_owner']==r['admin']:
            db_acl=[a for a in db_acl if a['grantee']!=r['admin']]
    public_acl=[grant("PUBLIC","USAGE")]
    if window:
        public_acl.append(grant(r["migrator"],"CREATE"))
        public_acl.append(grant(r["migrator"],"USAGE"))
        needed={"security"} if sec else {"inventory","audit"}
        for row in acls:
            if row["family"]=="schema" and row["identity"][0] in needed:
                row["grants"]=sorted(row["grants"]+[grant(r["migrator"],"CREATE"),grant(r["migrator"],"USAGE")],
                                     key=lambda x:(x["grantee"],x["privilege"]))
    def sort_acl(x):return sorted(x,key=lambda a:(a["grantee"],a["privilege"]))
    rights=[]
    if closed or sec:
        for o in managed:
            if o["family"]=="table" and o["identity"][0] in {"inventory","audit"}:
                rights.append(dict(role=r["inspector"],schema=o["identity"][0],relation=o["identity"][1],column="id",privilege="SELECT"))
        rights.append(dict(role=r["inspector"],schema="public",relation="alembic_version",column="version_num",privilege="SELECT"))
    if sec and not closed:
        rights.append(dict(role=r["migrator"],schema="public",relation="alembic_version",column="version_num",privilege="SELECT"))
    rights.sort(key=lambda x:(x["role"],x["schema"],x["relation"],x["column"]))
    control_acl=[grant(r["inspector"],"EXECUTE")]
    if window:control_acl.append(grant(r["migrator"],"EXECUTE"))
    system_acls=[]
    for row in parameters["system_acls"]:
        system_acls.append({**row,"grants":sort_acl(control_acl)} if row["family"]=="routine"
                           and row["identity"]==["pg_catalog","pg_control_system",""] else row)
    roles=[]
    for key,rolname in sorted(r.items()):
        if key in {"admin","recovery"}:continue
        if parameters['schema_version']==2 and key=='database_owner' and rolname==r['admin']:continue
        roles.append({"name":rolname,"login":key in {"admin","recovery","inspector"} or (key=="migrator" and window),
                      "superuser":False,"createdb":False,"createrole":False,"replication":False,"bypassrls":False,"inherit":False})
    roles+=parameters["administrative_roles"]
    roles.sort(key=lambda x:x["name"])
    # Administrative recovery powers are outside migrator/runtime identities.
    # Their exact trusted mechanism must be separately fixed, never silently
    # inferred from these NOSUPERUSER role records.
    result=dict(schema_version=parameters["schema_version"],profile="dev09b-prepared-"+phase.lower()+"-v"+str(parameters["schema_version"]),phase=phase,target_binding_sha256=c.digest("target",target),
                parameters_sha256=document_hash(parameters),sources=m["sources"],distribution=parameters["distribution"],
                system_objects=parameters["system_objects"],system_ownership=parameters["system_ownership"],
                system_acls=system_acls,system_memberships=parameters["system_memberships"],system_default_acl=parameters["system_default_acl"],
                extensions=[dict(name="btree_gist",**parameters["btree_gist"])],managed_objects=managed,
                ownership=ownership,acls=acls,roles=roles,memberships=[],database_owner=r["database_owner"],
                public_owner="pg_database_owner",database_acl=sort_acl(db_acl),public_acl=sort_acl(public_acl),
                inspection_column_grants=[x for x in rights if x["role"]==r["inspector"]],
                temporary_rights=[x for x in rights if x["role"]==r["migrator"]],
                control_system_acl=sort_acl(control_acl),
                ledgers=[{"chain":"application","presence":"PRESENT" if app else "ABSENT","revisions":["f066a01a7230"] if app else []},
                         {"chain":"security","presence":"PRESENT" if sec else "ABSENT","revisions":["b12b01a7230"] if sec else []}])
    if prerequisite is not None:
        result['ledgers'][0]=dict(chain='application',presence='PRESENT' if prerequisite else 'ABSENT',revisions=[prior] if prior else [])
    validate_snapshot(result)
    return PhaseExpectation(phase,c.canonical(result),c.canonical(target),c.canonical(parameters),tuple(migrations),prerequisite)


@dataclass(frozen=True)
class PhaseExpectation:
    phase: str
    json: bytes
    target_json: bytes
    parameters_json: bytes
    migration_sources: tuple
    prerequisite: int | None = None


@dataclass(frozen=True)
class PhysicalComparison:
    phase: str
    expectation_sha256: str
    observation_sha256: str
    # Pure normalized-data equality, never authentication or permission.


def validate_snapshot(s):
    c.closed(s,{"schema_version","profile","phase","target_binding_sha256","parameters_sha256","sources","distribution",
                "system_objects","system_ownership","system_acls","system_memberships","system_default_acl","extensions","managed_objects","ownership","acls","roles","memberships",
                "database_owner","public_owner","database_acl","public_acl","inspection_column_grants","temporary_rights","control_system_acl","ledgers"})
    c.integer(s["schema_version"],1,2)
    c.require(type(s["phase"]) is str and s["phase"] in PHASES)
    c.require(s["profile"]=="dev09b-prepared-"+s["phase"].lower()+"-v"+str(s["schema_version"]))
    c.digest_text(s["target_binding_sha256"]);c.digest_text(s["parameters_sha256"]);sources(s["sources"])
    objects(s["managed_objects"]);objects(s["system_objects"])
    access_inventory(s["ownership"],s["acls"],s["managed_objects"])
    access_inventory(s["system_ownership"],s["system_acls"],s["system_objects"])
    for key in ("database_acl","public_acl","system_default_acl"):acl(s[key])
    acl(s["control_system_acl"])
    c.require(type(s["roles"]) is list)
    ordered_set(s["roles"],lambda x:x["name"],validate_role)
    c.canonical(s)


def validate_role(role):
    c.closed(role,{"name","login","superuser","createdb","createrole","replication","bypassrls","inherit"});name(role["name"])
    for k,v in role.items():
        if k!="name":c.require(type(v) is bool)


def compare_normalized(expected,observed):
    c.require(type(expected) is PhaseExpectation)
    # Regenerate from fixed inputs, never repair the expectation from observation.
    regenerated=compile_profile(expected.phase,c.parse(expected.target_json,maximum=len(expected.target_json)),
                                c.parse(expected.parameters_json,maximum=len(expected.parameters_json)),expected.migration_sources,prerequisite=expected.prerequisite)
    c.require(expected.json==regenerated.json)
    # Validating before equality prevents bool/int substitution even where a
    # Python dict comparison would accept it. Canonical bytes are authoritative.
    validate_snapshot(observed)
    c.require(expected.json==c.canonical(observed))
    return PhysicalComparison(observed["phase"],document_hash(c.parse(expected.json,maximum=len(expected.json))),document_hash(observed))


def compare_profile(expected,observed):
    result=compare_normalized(expected,observed)
    c.require(not any(x["privilege"] in {"CREATE","TEMPORARY"} for x in observed["database_acl"]))
    # Built-in/extension implicit object resolver and independent provenance
    # are required source inputs, not proven by comparing supplied records.
    return result


def validate_phase_evidence(e):
    """Subject session is the execution observed, not the collector connection."""
    from .evidence import session
    c.closed(e,{"schema_version","evidence_id","classification","collector_id","phase","target_binding_sha256",
                "request_id","approval_id","attempt_id","subject_session","observed_interval","snapshot"})
    c.integer(e["schema_version"],1,1);c.uuid(e["evidence_id"]);c.identifier(e["collector_id"])
    c.require(type(e["classification"]) is str and e["classification"] in {"SYNTHETIC","OPERATIONAL"})
    c.require(type(e["phase"]) is str and e["phase"] in PHASES)
    c.digest_text(e["target_binding_sha256"])
    ids=[e[k] for k in ("request_id","approval_id","attempt_id")]
    initial=all(x is None for x in ids) and e["subject_session"] is None
    if initial:c.require(e["phase"]=="DEV-BASE")
    else:
        for x in ids:c.uuid(x)
        session(e["subject_session"])
        c.require(e["subject_session"]["target_sha256"]==e["target_binding_sha256"])
    c.closed(e["observed_interval"],{"lower","upper"})
    for x in e["observed_interval"].values():c.integer(x)
    c.require(e["observed_interval"]["lower"]<=e["observed_interval"]["upper"])
    validate_snapshot(e["snapshot"])
    c.require(e["snapshot"]["phase"]==e["phase"] and e["snapshot"]["target_binding_sha256"]==e["target_binding_sha256"])


class SyntheticPhaseAuthenticity:
    def inspect(self,raw):
        from .evidence import OriginObservation
        e=c.parse(raw,maximum=len(raw));validate_phase_evidence(e)
        return OriginObservation(document_hash(e),e["collector_id"],"SYNTHETIC",False)


def compare_independent_pair(expected,primary,independent,authenticity,independence):
    """Trusted future ports required; no production authenticators here.

    PRECOMMIT is deliberately excluded: another connection cannot observe
    uncommitted migration DDL. Neither a label nor two hashes prove independence.
    """
    from .evidence import OriginObservation
    for e in (primary,independent):
        validate_phase_evidence(e);compare_normalized(expected,e["snapshot"])
    c.require(primary["phase"].endswith(("PERSISTED","CLOSED")))
    for key in ("phase","target_binding_sha256","request_id","approval_id","attempt_id","subject_session"):
        c.require(c.canonical(primary[key])==c.canonical(independent[key]))
    c.require(primary["collector_id"]!=independent["collector_id"] and primary["evidence_id"]!=independent["evidence_id"])
    for e in (primary,independent):
        c.require(e["classification"]=="OPERATIONAL")
        result=authenticity.inspect(c.canonical(e,maximum_depth=32))
        c.require(type(result) is OriginObservation and result.authenticated is True and result.classification=="OPERATIONAL"
                  and result.evidence_sha256==document_hash(e) and result.collector_id==e["collector_id"])
    c.require(independence.confirm(c.canonical(primary,maximum_depth=32),c.canonical(independent,maximum_depth=32)) is True)
    return compare_profile(expected,primary["snapshot"])
