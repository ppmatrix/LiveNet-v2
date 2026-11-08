"""Executable composition for the existing querytrial, with explicit live ports.

No CLI that discovers credentials/roles or supplies missing trusted adapters.
No SQL, connection, administrative grant, key creation or I/O on construction.
This is not currently runnable end-to-end: the operational ports and approvals
listed in the trial plan must be supplied independently. Tests model wiring only.
"""
import re
from scripts.dedicated.dev09b import codec as c
from scripts.dedicated.dev09b.model import AttemptState
from scripts.dedicated.dev09b.layers import read_snapshot
from scripts.postgres.dev09b_application_transport import apply_authorized_application

SID='7705421224394444834'


class ApplicationTrial:
    """Keep one borrowed connection/transaction through PRECOMMIT.

    authority is the authenticated PUBLIC client, never a consumption DB handle.
    supervision owns an already-established exclusive window including admin
    powers; assert_bound must not perform recursive SQL on the guarded session.
    No adapters/doubles, approval issuance, or privilege changes are constructed.
    """
    def __init__(self, *, connection,transaction,snapshot,session,authority,supervision,
                 profile_json,profile_verifier,prerequisite_contracts,source_root):
        self.inputs=dict(connection=connection,transaction=transaction,snapshot=snapshot,session=session,
            authority=authority,supervision=supervision,profile_json=profile_json,profile_verifier=profile_verifier,
            prerequisite_contracts=prerequisite_contracts,source_root=source_root)
        self.controller=None
        self.attempted=False
        self.failure=None
        self.containment=[]

    def to_precommit(self):
        c.require(not self.attempted);self.attempted=True
        try:
            c.validate_layers(self.inputs['snapshot'])
            payload,target,*_=read_snapshot(self.inputs['snapshot'])
            c.require(payload['operation']=='application-base-to-f066a01a7230' and target['system_identifier']==SID)
            c.require(self.inputs['supervision'] is not None and self.inputs['profile_verifier'] is not None)
            self.controller=apply_authorized_application(**self.inputs)
            self.controller.inspect_precommit()
            return self.controller  # still uncommitted; not permission to COMMIT
        except BaseException as exc:
            self._diagnostic(exc,'precommit')
            self.contain()
            raise

    def commit_once(self, *, commit_authorizer):
        """Separate explicit action; never called automatically after PRECOMMIT.

        authorize(snapshot,session) must check the actual human authorization
        for persistence, not a caller-supplied bool/hash or artifact approval.
        Existing controller checks time/revocation/continuity again on dispatch.
        Driver return remains UNKNOWN until confirm_persisted succeeds.
        """
        c.require(self.controller is not None)
        try:
            c.require(commit_authorizer is not None)
            c.require(commit_authorizer.authorize(self.inputs['snapshot'],self.inputs['session']) is None)
            self.controller.commit_once()
        except BaseException as exc:
            self._diagnostic(exc,'commit')
            self.contain()
            raise

    def confirm_persisted(self,primary,independent,*,authenticity,independence):
        c.require(self.controller is not None)
        try:
            return self.controller.confirm_persisted(self.inputs['snapshot'],primary,independent,
                authenticity=authenticity,independence=independence)
        except BaseException as exc:
            self._diagnostic(exc,'persisted');raise

    def confirm_rollback(self,evidence,*,authenticity,independence,journal):
        c.require(self.controller is not None)
        try:
            return self.controller.confirm_rollback(self.inputs['snapshot'],evidence,
                authenticity=authenticity,independence=independence,journal=journal)
        except BaseException as exc:
            self._diagnostic(exc,'rollback_reconciliation');self.contain();raise

    def contain(self):
        """No authority dependency, no retry or approval release, both closes tried."""
        if self.controller is not None:
            self.controller.contain()
            self.containment=self.controller.containment
            return
        # Driver return is diagnostic only, never independent rollback proof.
        result=dict(rollback='NOT_ATTEMPTED',close='NOT_ATTEMPTED');self.containment.append(result)
        try:
            self.inputs['transaction'].rollback();result['rollback']='RETURNED'
        except BaseException as exc:result['rollback']='FAILED';result['rollback_exception']=type(exc).__name__
        try:
            self.inputs['connection'].close();result['close']='RETURNED'
        except BaseException as exc:result['close']='FAILED';result['close_exception']=type(exc).__name__

    def _diagnostic(self,exc,phase):
        self.failure=dict(phase=phase,code='TRIAL_REFUSED',exception_class=type(exc).__name__)
        state=getattr(getattr(exc,'orig',None),'sqlstate',None)
        if type(state) is str and re.fullmatch('[0-9A-Z]{5}',state):self.failure['sqlstate']=state
        # No exception text/args, SQL, parameters, credential or row values.
        # A CLI caller must persist only this safe diagnostic, not print exc.

    @property
    def state(self):
        return AttemptState.UNKNOWN if self.controller is None else self.controller.state
