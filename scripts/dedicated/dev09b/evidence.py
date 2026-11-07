"""Structural evidence comparison and abstract origin/independence ports.

OPERATIONAL is an untrusted document claim. No real collectors, authenticators
or independent confirmation implementation. Projections never confirm outcomes.
"""
from dataclasses import dataclass
from typing import Protocol

from . import codec as c
from .layers import (sources, catalog, ordered_set, revision, document_hash,
                     ExpectationSnapshot, freeze_expectations)
from .model import SessionBinding
from .profiles import validate_inventory_projection, require_complete_profile


RESULTS = {
    "BEFORE": frozenset({"NOT_STARTED"}),
    "PRECOMMIT": frozenset({"UNCOMMITTED"}),
    "POSTCOMMIT": frozenset({"COMMIT_REPORTED", "UNKNOWN"}),
    "ROLLBACK_CHECK": frozenset({"ROLLBACK_REPORTED", "UNKNOWN"}),
}
EVIDENCE_FIELDS = frozenset("schema_version evidence_id classification operation phase target_binding_sha256 request_id approval_id attempt_id collector_id collector_sources session_binding observed_interval catalog ledgers execution_result related_evidence".split())


def session(obj):
    c.closed(obj, set(SessionBinding.__dataclass_fields__))
    SessionBinding(**obj).validate()


def validate_evidence(e):
    c.closed(e, EVIDENCE_FIELDS)
    c.integer(e["schema_version"], 1, 1)
    c.uuid(e["evidence_id"])
    c.require(type(e["classification"]) is str and e["classification"] in {"SYNTHETIC","OPERATIONAL"})
    c.require(type(e["operation"]) is str and e["operation"] in c.OPS)
    c.require(type(e["phase"]) is str and e["phase"] in RESULTS)
    c.require(type(e["execution_result"]) is str and e["execution_result"] in RESULTS[e["phase"]])
    c.digest_text(e["target_binding_sha256"])
    c.identifier(e["collector_id"])
    sources(e["collector_sources"])
    c.require(bool(e["collector_sources"]))
    ids = [e[k] for k in ("request_id","approval_id","attempt_id")]
    initial = all(x is None for x in ids) and e["session_binding"] is None
    if initial:
        c.require(e["phase"] == "BEFORE")
    else:
        for v in ids: c.uuid(v)
        session(e["session_binding"])
        c.require(e["session_binding"]["target_sha256"] == e["target_binding_sha256"])
    c.closed(e["observed_interval"], {"lower","upper"})
    lower, upper = e["observed_interval"]["lower"], e["observed_interval"]["upper"]
    c.integer(lower); c.integer(upper); c.require(lower <= upper)
    catalog(e["catalog"])
    def ledger(l):
        c.closed(l, {"chain","presence","revisions"})
        c.require(type(l["chain"]) is str and l["chain"] in {"application","security"})
        c.require(type(l["presence"]) is str and l["presence"] in {"ABSENT","PRESENT"})
        ordered_set(l["revisions"], lambda x:x, revision)
        c.require(l["presence"] != "ABSENT" or l["revisions"] == [])
    ordered_set(e["ledgers"], lambda l:l["chain"], ledger)
    c.require([l["chain"] for l in e["ledgers"]] == ["application","security"])
    for row, table in zip(e["ledgers"], ("alembic_version","alembic_security_version")):
        relation = [r for r in e["catalog"]["relations"] if r["schema"] == "public" and r["name"] == table]
        c.require(bool(relation) == (row["presence"] == "PRESENT"))
        c.require(not relation or relation[0]["kind"] == "r")
    ordered_set(e["related_evidence"], lambda x:x, c.digest_text)
    c.require(document_hash(e) not in e["related_evidence"])
    c.canonical(e)


@dataclass(frozen=True)
class InventoryComparison:
    """Only a structural projection matched; NOT base/success/rollback confirmation."""
    evidence_sha256: str
    expectation_sha256: str


def compare_evidence(snapshot, evidence):
    c.require(type(snapshot) is ExpectationSnapshot)
    checked = freeze_expectations(*(c.parse(getattr(snapshot,k)) for k in
                   ("payload","target","executor","plan","semantic","physical","provenance")))
    validate_evidence(evidence)
    p, plan, ex = c.parse(checked.payload), c.parse(checked.plan), c.parse(checked.executor)
    c.require(evidence["operation"] == p["operation"])
    c.require(evidence["target_binding_sha256"] == p["target_binding_sha256"])
    c.require(plan["prerequisite_evidence_sha256"] in evidence["related_evidence"]
              or document_hash(evidence) == plan["prerequisite_evidence_sha256"])
    if evidence["request_id"] is not None:
        for key in ("request_id","approval_id","attempt_id"):
            c.require(evidence[key] == p[key])
        s = evidence["session_binding"]
        c.require(s["executor_sha256"] == plan["executor_binding_sha256"] and s["incarnation_id"] == ex["incarnation_id"])
    phase = "before" if evidence["phase"] in {"BEFORE","ROLLBACK_CHECK"} else "after"
    sem, phys = c.parse(checked.semantic), c.parse(checked.physical)
    # Canonical bytes preserve exact scalar types, including bool versus int.
    c.require(c.canonical(evidence["catalog"]) == c.canonical(phys[phase]))
    for row in evidence["ledgers"]:
        wanted = sem[phase][row["chain"]]
        c.require(row["presence"] == wanted["presence"])
        c.require(c.canonical(row["revisions"]) == c.canonical(wanted["revisions"]))
    validate_inventory_projection(evidence["catalog"])
    return InventoryComparison(document_hash(evidence), plan["expected_"+phase+"_sha256"])


@dataclass(frozen=True)
class OriginObservation:
    evidence_sha256: str
    collector_id: str
    classification: str
    authenticated: bool


class Authenticity(Protocol):
    def inspect(self, evidence_json: bytes) -> OriginObservation: ...


class Independence(Protocol):
    def confirm(self, primary_json: bytes, independent_json: bytes) -> bool: ...


class SyntheticAuthenticity:
    """Never authenticates an operational claim, even if relabelled by caller."""
    def inspect(self, evidence_json):
        e = c.parse(evidence_json)
        validate_evidence(e)
        return OriginObservation(document_hash(e), e["collector_id"], "SYNTHETIC", False)


class SyntheticIndependence:
    def confirm(self, primary_json, independent_json):
        return False


def check_operational_origin(evidence, authenticity):
    validate_evidence(evidence)
    c.require(evidence["classification"] == "OPERATIONAL")
    result = authenticity.inspect(c.canonical(evidence))
    c.require(type(result) is OriginObservation and result.authenticated is True
              and result.classification == "OPERATIONAL"
              and result.evidence_sha256 == document_hash(evidence)
              and result.collector_id == evidence["collector_id"])
    # This is an origin observation only, NEVER an admission/capability.
    return result


def check_independent_pair_structure(snapshot, evidence, independent):
    """Referential consistency only: different IDs are NOT independence proof."""
    compare_evidence(snapshot,evidence); compare_evidence(snapshot,independent)
    c.require(evidence["phase"] == independent["phase"] and evidence["phase"] in {"POSTCOMMIT","ROLLBACK_CHECK"})
    c.require(evidence["execution_result"] == independent["execution_result"] and evidence["execution_result"] != "UNKNOWN")
    for key in ("operation","target_binding_sha256","request_id","approval_id","attempt_id"):
        c.require(evidence[key] == independent[key])
    c.require(c.canonical(evidence["session_binding"]) == c.canonical(independent["session_binding"]))
    c.require(evidence["evidence_id"] != independent["evidence_id"] and evidence["collector_id"] != independent["collector_id"])


def confirm_outcome(snapshot, evidence, independent, authenticity, independence):
    check_independent_pair_structure(snapshot,evidence,independent)
    require_complete_profile(evidence["catalog"]["profile"])
    check_operational_origin(evidence,authenticity); check_operational_origin(independent,authenticity)
    c.require(independence.confirm(c.canonical(evidence),c.canonical(independent)) is True)
    # Even authenticated independent data cannot complete an incomplete profile.


def confirm_base(snapshot, evidence, authenticity):
    compare_evidence(snapshot,evidence)
    c.require(evidence["phase"] == "BEFORE")
    require_complete_profile(evidence["catalog"]["profile"])
    check_operational_origin(evidence,authenticity)
