"""Explicit operational CLI. Import/check never activate a service or target.

Operational commands require an exact-hash root-controlled authorized policy,
all existing signed layer validators and the configured segregated UID. The
checked-in proposed configuration is deliberately not an accepted deployment.
"""
import argparse
from dataclasses import asdict
from hashlib import sha256
import os
from pathlib import Path
import signal
import sys

# Direct invocation through -m from the source root; canonical Alembic imports.
ROOT=Path(__file__).resolve().parents[2]
if str(ROOT/'backend') not in sys.path:sys.path.insert(0,str(ROOT/'backend'))

from scripts.dedicated.dev09b import codec as c,detailed_catalog as d
from scripts.dedicated.dev09b.hosting import (read_policy,Deployment,ContainmentDeployment,InspectionPolicy,
    SupervisorHost,StorageContinuity,FixedAuthorityTrust,assert_account,make_clock,
    bind_listener,host_loop,session_binding)
from scripts.dedicated.dev09b.operational import (LocalRPC,RemoteClock,RemoteContinuity,
    AuthorityDispatch,LocalReceiptChannel)
from scripts.dedicated.dev09b.postgres_authority import PostgresConsumptionService,AuthorityDestination
from scripts.dedicated.dev09b.rollback import RemoteRollback
from scripts.dedicated.dev09b.containment import contain_target,verify_target,verification_safe
from scripts.postgres.dev09b_operational_trial import bind_trial


def executor(dep):
    policy=dep.policy;assert_account(policy['accounts']['executor'])
    rpc=LocalRPC(policy['sockets']['supervisor_executor'],policy['accounts']['supervisor']['uid'],timeout=30.0)
    connection=transaction=trial=None
    result=dict(state='UNKNOWN',window='BLOCKED_REQUIRED',rollback='NOT_ATTEMPTED',containment='NOT_ATTEMPTED')
    try:
        connection=dep.connections('migrator')();transaction=connection.begin()
        session,binding=session_binding(connection,dep)
        rpc.call('attach',dict(session=asdict(session),binding=binding))
        verifier=InspectionPolicy(dep)
        prereqs=tuple(verifier.contract('prerequisite_'+str(i),binding,session) for i in range(5))
        precommit=verifier.contract('precommit',binding,session)
        trial=bind_trial(connection=connection,transaction=transaction,snapshot=dep.snapshot,session=session,
            profile_json=dep.profile,profile_verifier=verifier,prerequisite_contracts=prereqs,
            precommit_contract=precommit,source_root=policy['source_root'],
            authority_socket=policy['sockets']['authority_public'],authority_uid=policy['accounts']['authority']['uid'],
            supervisor_socket=policy['sockets']['supervisor_executor'],supervisor_uid=policy['accounts']['supervisor']['uid'])
        from scripts.dedicated.dev09b.extension_privileges import inspect
        # Fixed SELECT-only preparation on the actual borrowed session.
        result['extension_privileges']=inspect(connection)
        try:
            trial.to_precommit()
            result['precommit']='MATCHED'
        except BaseException as exc:
            result['application_failure_class']=type(exc).__name__
        finally:trial.contain()
        result['rollback']='ATTEMPTED'
        proof=RemoteRollback(rpc,policy['rollback_collector_id'])
        evidence=proof.collect()
        trial.confirm_rollback(evidence,authenticity=proof,independence=proof,journal=proof)
        result['state']=trial.state.value
    except BaseException as exc:
        result['failure_class']=type(exc).__name__
        if trial is not None:result['state']=trial.state.value
    finally:
        # No trust, authority or successful proof is required for local closing.
        try:
            if trial is not None:trial.contain()
            else:
                try:
                    if transaction is not None:transaction.rollback()
                finally:
                    if connection is not None:connection.close()
        except BaseException as exc:result['local_close_exception']=type(exc).__name__
        # Independent admin containment is attempted even after reconciliation,
        # clock, authority or interlock failure. No retry of migration/admission.
        try:
            result['containment']=rpc.call('contain',{})
            result['powers_removed']=verification_safe(result['containment'].get('verification'))
            result['window']='BLOCKED' if result['containment'].get('window_block')=='DURABLE' else 'BLOCK_UNCERTAIN'
        except BaseException as exc:result['containment_exception']=type(exc).__name__
        try:
            final=rpc.call('verify_final',{})
            result['final_catalog_sha256']=sha256(d.encode(final)).hexdigest()
        except BaseException as exc:result['final_verification_exception']=type(exc).__name__
    return result


def supervisor(dep):
    p=dep.policy;assert_account(p['accounts']['supervisor'])
    continuity=StorageContinuity(p['window_directory'],p['continuity_token'],p['storage'])
    continuity.start();listeners=[]
    try:
        host=SupervisorHost(dep,continuity,make_clock(p),dep.connections('admin'),dep.connections('probe'))
        for endpoint,account,dispatch in (
            ('supervisor_executor','executor',host.executor_dispatch),
            ('supervisor_authority','authority',host.authority_dispatch)):
            uid=p['accounts'][account]['uid']
            listeners.append((bind_listener(p['sockets'][endpoint],uid,
                directory_callers=[p['accounts'][name]['uid'] for name in ('executor','authority')]),uid,dispatch))
        host_loop(listeners,tick=host.tick)
    finally:
        try:continuity.block()
        finally:
            for sock,_,_ in listeners:sock.close()
            # Never dependent on successful proof; only the fixed dedicated role.
            contain_target(dep.connections('admin'),dep.target)


def authority(dep):
    p=dep.policy;assert_account(p['accounts']['authority'])
    rpc=LocalRPC(p['sockets']['supervisor_authority'],p['accounts']['supervisor']['uid'],timeout=30.0)
    destination=AuthorityDestination(**p['authority_destination'])
    c.require(destination.system_identifier!=dep.target['system_identifier'])
    c.require(p['connections']['authority']['principal']==destination.principal)
    service=PostgresConsumptionService(connections=dep.connections('authority'),destination=destination,
        trust=FixedAuthorityTrust(dep),clock=RemoteClock(rpc),continuity=RemoteContinuity(rpc),channel=LocalReceiptChannel())
    uid=p['accounts']['executor']['uid']
    listener=bind_listener(p['sockets']['authority_public'],uid)
    host_loop([(listener,uid,AuthorityDispatch(service))])


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('check','supervisor','authority','executor','contain','verify','authority-bootstrap'))
    parser.add_argument('--policy',required=True)
    parser.add_argument('--policy-sha256',required=True)
    args=parser.parse_args(argv)
    # Suppress third-party logging; safe fixed diagnostics are emitted below.
    import logging
    logging.disable(logging.CRITICAL)
    result=None
    try:
        policy=read_policy(args.policy,args.policy_sha256)
        dep=ContainmentDeployment(policy) if args.command in {'contain','verify'} else Deployment(policy)
        if args.command=='check':result=dict(status='POLICY_INTEGRITY_VALID',operational_authorization='EXTERNAL_ROOT_POLICY_REQUIRED')
        elif args.command=='executor':result=executor(dep)
        elif args.command=='supervisor':supervisor(dep)
        elif args.command=='authority':authority(dep)
        elif args.command=='authority-bootstrap':
            from scripts.postgres.dev09b_authority_bootstrap import bootstrap
            result=bootstrap(dep)
        else:
            assert_account(policy['accounts']['supervisor'])
            # External command remains usable if the supervisor listener is lost.
            continuity=StorageContinuity(policy['window_directory'],policy['continuity_token'],policy['storage'])
            if args.command=='contain':
                try:continuity.block()
                finally:result=contain_target(dep.connections('admin'),dep.target)
            else:result=verify_target(dep.connections('admin'),dep.target)
        if result is not None:print(d.encode(result).decode())
        if args.command=='executor' and (result.get('state')!='ROLLED_BACK_CONFIRMED'
            or result.get('precommit')!='MATCHED'
            or result.get('powers_removed') is not True or result.get('window')!='BLOCKED'
            or 'final_catalog_sha256' not in result):return 78
        if args.command=='verify' and not verification_safe(result):return 78
        return 0
    except BaseException as exc:
        print(d.encode(dict(status='REFUSED',exception_class=type(exc).__name__)).decode())
        return 78


if __name__=='__main__':
    def stop(signum,frame):raise SystemExit(128+signum)
    for name in ('SIGTERM','SIGINT'):signal.signal(getattr(signal,name),stop)
    raise SystemExit(main())
