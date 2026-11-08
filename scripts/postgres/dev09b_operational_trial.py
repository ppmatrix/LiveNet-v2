"""Explicit live-port composition for the first ROLLBACK-only trial.

No CLI discovers/approves missing policy, credentials, bindings or artifacts.
Call only from the reviewed executor bootstrap in the controlled window.
Constructing this composition does no socket, SQL or filesystem I/O.
"""
from scripts.dedicated.dev09b import codec as c
from scripts.dedicated.dev09b.layers import read_snapshot
from scripts.dedicated.dev09b.operational import (
    LocalRPC, AuthorityRPC, RemoteClock, RemoteContinuity, TrialSupervision,
)
from scripts.dedicated.dev09b.postgres_authority import AuthenticatedAuthorityClient
from scripts.postgres.dev09b_application_trial import ApplicationTrial, SID


def bind_trial(*, connection, transaction, snapshot, session, profile_json,
               profile_verifier, prerequisite_contracts, precommit_contract,
               source_root, authority_socket, authority_uid,
               supervisor_socket, supervisor_uid):
    c.validate_layers(snapshot)
    payload, target, *_ = read_snapshot(snapshot)
    c.require(target['system_identifier'] == SID)
    c.require(payload['operation'] == 'application-base-to-f066a01a7230')
    c.require(profile_verifier is not None and precommit_contract is not None)
    authority_rpc = AuthorityRPC(LocalRPC(authority_socket, authority_uid))
    supervisor_rpc = LocalRPC(supervisor_socket, supervisor_uid)
    authority = AuthenticatedAuthorityClient(endpoint=authority_rpc, verifier=authority_rpc,
        payload=payload, session=session, profile_json=profile_json,
        clock=RemoteClock(supervisor_rpc), continuity=RemoteContinuity(supervisor_rpc))
    supervision = TrialSupervision(rpc=supervisor_rpc, connection=connection,
        transaction=transaction, session=session, snapshot=snapshot, plan=snapshot.plan,
        profile_json=profile_json, profile_verifier=profile_verifier,
        precommit_contract=precommit_contract, source_root=source_root)
    return ApplicationTrial(connection=connection, transaction=transaction,
        snapshot=snapshot, session=session, authority=authority, supervision=supervision,
        profile_json=profile_json, profile_verifier=profile_verifier,
        prerequisite_contracts=prerequisite_contracts, source_root=source_root)


def run_rollback_trial(trial):
    """Consumes once, PRECOMMIT then mandatory containment, no persistence path.

    Driver rollback is not independent reconciliation. State remains UNKNOWN
    until a separately authenticated baseline collection confirms rollback.
    """
    try:
        trial.to_precommit()
    finally:
        trial.contain()
