"""Offline proof-boundary tests, not operational origin/independence adapters.

Model a prior consumed+dispatched attempt. Never connect, migrate, produce an
operational approval or substitute these test ports into the trial procedure.
No catalog/layer/subject validator is patched; synthetic-origin rejection is real.
"""
from copy import deepcopy
from dataclasses import asdict
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from scripts.dedicated.dev09b import codec as c,physical as p,layers,detailed_catalog as d
from scripts.dedicated.dev09b.admission import AdmissionController
from scripts.dedicated.dev09b.postgres_authority import AuthenticatedAuthorityClient
from scripts.dedicated.dev09b.evidence import OriginObservation
from scripts.dedicated.dev09b.model import AttemptState
from scripts.postgres.tests.test_dev09b_detailed import detailed_fixture
from scripts.postgres.tests.test_dev09b_offline import uid


def setup():
    parts,session,profile=detailed_fixture();snapshot=layers.freeze_expectations(*parts)
    payload,target,_,_,semantic,phys,provenance=parts
    expected=d.validate_contract(phys,target,semantic,provenance)['APP-F066-PERSISTED']
    endpoint=SimpleNamespace(record=Mock())
    authority=AuthenticatedAuthorityClient(endpoint=endpoint,verifier=None,payload=payload,session=session,profile_json=profile,clock=None,continuity=None)
    ctl=AdmissionController(authority=authority,session=session,connection=SimpleNamespace(closed=True),transaction=None,supervision=None,plan=snapshot.plan)
    ctl.used=True;ctl.state=AttemptState.UNKNOWN;ctl.commit_sent=True;ctl.closed=True
    e=dict(schema_version=1,evidence_id=uid(501),classification='OPERATIONAL',collector_id='model-primary',phase='APP-F066-PERSISTED',
        target_binding_sha256=payload['target_binding_sha256'],request_id=payload['request_id'],approval_id=payload['approval_id'],attempt_id=payload['attempt_id'],
        subject_session=asdict(session),observed_interval=dict(lower=100,upper=101),snapshot=c.parse(expected.json,maximum=len(expected.json)))
    other=deepcopy(e);other['evidence_id']=uid(502);other['collector_id']='model-independent'
    class ModelOrigin:
        def inspect(self,raw):
            obj=d.parse(raw);return OriginObservation(layers.document_hash(obj),obj['collector_id'],'OPERATIONAL',True)
    return ctl,snapshot,e,other,ModelOrigin(),SimpleNamespace(confirm=Mock(return_value=True)),endpoint


def test_actual_synthetic_authenticator_never_promotes_operational_label():
    ctl,snapshot,e,other,_,independence,endpoint=setup()
    with pytest.raises(c.Invalid):ctl.confirm_persisted(snapshot,e,other,authenticity=p.SyntheticPhaseAuthenticity(),independence=independence)
    assert ctl.state is AttemptState.UNKNOWN and not endpoint.record.called


@pytest.mark.parametrize('fault',['same_collector','attempt','session','phase','catalog','independence','record'])
def test_mismatches_or_uncertain_record_leave_unknown(fault):
    ctl,snapshot,e,other,origin,independence,endpoint=setup()
    if fault=='same_collector':other['collector_id']=e['collector_id']
    if fault=='attempt':other['attempt_id']=uid(999)
    if fault=='session':other['subject_session']['backend_pid']+=1
    if fault=='phase':other['phase']='APP-F066-CLOSED'
    if fault=='catalog':other['snapshot']['managed_objects'].pop()
    if fault=='independence':independence.confirm.return_value=False
    if fault=='record':endpoint.record.side_effect=OSError('lost confirmation recording response')
    with pytest.raises((c.Invalid,OSError)):ctl.confirm_persisted(snapshot,e,other,authenticity=origin,independence=independence)
    assert ctl.state is AttemptState.UNKNOWN


def test_model_independent_proof_records_before_shared_state_transition():
    ctl,snapshot,e,other,origin,independence,endpoint=setup()
    endpoint.record.side_effect=lambda *args: c.require(ctl.state is AttemptState.UNKNOWN)
    ctl.confirm_persisted(snapshot,e,other,authenticity=origin,independence=independence)
    assert ctl.state is AttemptState.COMMITTED_CONFIRMED
    assert endpoint.record.call_args.args[1]=='independent_reconciliation'
    with pytest.raises(c.Invalid):ctl.confirm_persisted(snapshot,e,other,authenticity=origin,independence=independence)
