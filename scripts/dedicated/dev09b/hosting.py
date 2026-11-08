"""Explicit Linux hosting and root-controlled deployment policy, direction B.

No installation or activation on import. A checked-in proposal cannot pass the
root-owned, exact-hash operational policy boundary. No fixture/factory imports.
"""
from copy import deepcopy
from dataclasses import asdict
from hashlib import sha256
import os
from pathlib import Path
import pwd
import select
import socket
import stat
import struct
import time

from sqlalchemy import text

from . import codec as c,detailed_catalog as d,own_settings
from .layers import ExpectationSnapshot,read_snapshot
from .operational import (AnchoredClock,DurableContinuity,PostgresWindowObserver,
    WindowDispatch,serve_one,LocalRPC)
from .tls import NativePeerCertificate,PinnedConnections,checked_file


def read_policy(path,digest):
    path=Path(path);c.require(path.is_absolute());c.digest_text(digest)
    for item in (path,*path.parents):
        info=item.lstat()
        c.require(not stat.S_ISLNK(info.st_mode) and info.st_uid==0 and not info.st_mode & 0o022)
    raw=path.read_bytes();c.require(sha256(raw).hexdigest()==digest)
    policy=d.parse(raw)
    c.require(policy['classification']=='AUTHORIZED_ROLLBACK_ONLY_DEPLOYMENT')
    c.require(type(policy['decision_reference']) is str and bool(policy['decision_reference']))
    c.require(policy['commit_allowed'] is False and policy['ledger_select'] is False)
    return policy


def assert_account(record):
    found=pwd.getpwnam(record['name'])
    c.require(found.pw_uid==record['uid']==os.geteuid() and found.pw_gid==os.getegid())
    c.require(found.pw_shell in {'/usr/sbin/nologin','/sbin/nologin','/bin/false'})
    c.require(set(os.getgroups()) <= {found.pw_gid})


def acl_bytes(owner_permissions,callers,caller_permissions):
    # Linux POSIX ACL xattr v2. No setfacl dependency/installation.
    entries=[(1,owner_permissions,0xffffffff)]
    entries.extend((2,caller_permissions,uid) for uid in sorted(set(callers)))
    entries += [(4,0,0xffffffff),(16,caller_permissions,0xffffffff),(32,0,0xffffffff)]
    return struct.pack('<I',2)+b''.join(struct.pack('<HHI',*e) for e in entries)


def bind_listener(path,caller_uid,*,directory_callers=None):
    path=Path(path);directory=path.parent
    c.require(directory.is_absolute() and not path.exists() and not path.is_symlink())
    for item in (directory,*directory.parents):c.require(not item.is_symlink())
    info=directory.stat();c.require(info.st_uid==os.geteuid() and stat.S_ISDIR(info.st_mode))
    allowed=os.getxattr(directory,'system.posix_acl_access')
    c.require(allowed==acl_bytes(7,directory_callers or [caller_uid],1))
    # Directory ACL may admit both exact service callers, but neither can write.
    version=struct.unpack('<I',allowed[:4])[0];c.require(version==2)
    entries=[struct.unpack('<HHI',allowed[i:i+8]) for i in range(4,len(allowed),8)]
    c.require((1,7,0xffffffff) in entries and (4,0,0xffffffff) in entries
              and (32,0,0xffffffff) in entries and (16,1,0xffffffff) in entries)
    c.require((2,1,caller_uid) in entries and all(tag!=2 or perm==1 for tag,perm,_ in entries))
    sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
    try:
        # umask is process-wide; host is single-threaded during creation.
        previous=os.umask(0o177)
        try:sock.bind(str(path))
        finally:os.umask(previous)
        os.setxattr(path,'system.posix_acl_access',acl_bytes(6,[caller_uid],6))
        c.require(os.getxattr(path,'system.posix_acl_access')==acl_bytes(6,[caller_uid],6))
        sock.listen(4)
        return sock
    except BaseException:
        sock.close();raise  # leave path; never unlink/rebind automatically


def verify_storage(config):
    """Prove different mounted devices; restore exclusions remain an admin act."""
    mount=Path(config['mountpoint'])
    c.require(type(config['restore_exclusion_reference']) is str and bool(config['restore_exclusion_reference']))
    c.require(mount.is_absolute() and os.path.ismount(mount) and not mount.is_symlink())
    device=mount.stat().st_dev
    c.require(device==config['device'] and config['excluded_from_authority_restore'] is True)
    c.require(len(config['authority_and_target_storage_paths'])==2)
    for other in config['authority_and_target_storage_paths']:
        c.require(Path(other).stat().st_dev!=device)
    lines=Path('/proc/self/mountinfo').read_text().splitlines()
    matches=[line for line in lines if line.split()[4]==str(mount)]
    c.require(len(matches)==1)
    fields=matches[0].split();separator=fields.index('-')
    # Mount IDs vary in systemd namespaces; backing identity does not.
    identity=dict(device=fields[2],root=fields[3],mountpoint=fields[4],
        fstype=fields[separator+1],source=fields[separator+2])
    c.require(sha256(d.encode(identity)).hexdigest()==config['mountinfo_sha256'])


class StorageContinuity(DurableContinuity):
    def __init__(self,directory,token,storage):
        super().__init__(directory,token);self.storage=storage
    def start(self):
        verify_storage(self.storage)
        c.require(self.directory.parent==Path(self.storage['mountpoint'])/'windows')
        super().start()
    def sample(self):
        verify_storage(self.storage)
        return super().sample()
    def block(self):
        self.active=False
        verify_storage(self.storage)
        super().block()


class Deployment:
    def __init__(self,policy):
        self.policy=policy
        c.closed(policy['accounts'],{'executor','authority','supervisor'})
        c.require(len({v['uid'] for v in policy['accounts'].values()})==3)
        self.snapshot=ExpectationSnapshot(*(checked_file(policy['files'][key]).read_bytes()
            for key in ('payload','target','executor','plan','semantic','physical','provenance')))
        c.validate_layers(self.snapshot)
        self.payload,self.target,self.executor,self.plan,*_=read_snapshot(self.snapshot)
        c.require(self.target['system_identifier']==own_settings.TARGET_SID)
        c.require(self.target['tls_server_name']=='dev09b-querytrial.internal')
        self.profile=checked_file(policy['files']['profile']).read_bytes()
        d.validate_profile_binding(self.snapshot,self.profile)
        self.envelope=checked_file(policy['files']['envelope']).read_bytes()
        self.key=bytes.fromhex(policy['issuer_public_key_hex'])
        signature=c.verify_envelope(self.envelope,self.key)
        c.require(signature.payload_json==self.snapshot.payload)
        for key in ('issuer_id','key_id','trust_policy_version','executor_id'):
            c.require(self.payload[key]==policy['trusted_identities'][key])
        # Root policy gives the approval provenance, not a digest completeness flag.
        for key in ('source_profile','dependency_lock','executor_compatibility','artifact_availability'):
            c.require(type(policy['approval_references'][key]) is str and bool(policy['approval_references'][key]))
        configuration=checked_file(policy['files']['executor_configuration']).read_bytes()
        c.require(sha256(configuration).hexdigest()==self.executor['configuration_sha256'])
        lock=checked_file(policy['files']['dependency_lock']).read_bytes()
        c.require(sha256(lock).hexdigest()==self.executor['dependency_lock_sha256'])
        supervision=checked_file(policy['files']['supervision_policy']).read_bytes()
        c.require(sha256(supervision).hexdigest()==self.executor['supervision_policy_sha256'])
        # Check all source bytes before any target connection; no learned source maps.
        for row in read_snapshot(self.snapshot)[6]['source_inventory']:
            file=Path(policy['source_root'])/row['path']
            for item in (file,*file.parents):c.require(not item.is_symlink())
            c.require(sha256(file.read_bytes()).hexdigest()==row['sha256'])
        self.configuration=d.parse(configuration)
        c.require(self.configuration==policy['configuration'])
        for key in ('source_root','accounts','native_providers','connections','sockets','storage','inspection_templates'):
            c.require(policy[key]==self.configuration[key])

    def connections(self,identity):
        conf=self.policy['connections'][identity]
        endpoint=dict(conf['endpoint'])
        if identity not in {'authority','authority_admin'}:
            for field in ('host','port','database_name','tls_server_name','ca_sha256','server_certificate_sha256'):
                c.require(endpoint[field]==self.target[field])
        return PinnedConnections(endpoint=endpoint,principal=conf['principal'],
            password_file=conf['password_file'],native=NativePeerCertificate(self.policy['native_providers']))


class ContainmentDeployment:
    """Only root-controlled target/admin/TLS policy, independent of admission.

    Missing approval envelope, catalog/profile, issuer or authority availability
    must not prevent administrative NOLOGIN/termination/revocation. Still pins
    the actual TLS connection and checks SID/admin before every transaction.
    """
    def __init__(self,policy):
        self.policy=policy
        conf=policy['connections']['admin']
        c.require(conf['principal']==own_settings.ADMIN)
        c.require(conf['endpoint']['database_name']==own_settings.DATABASE)
        self.target=dict(system_identifier=own_settings.TARGET_SID,database_name=own_settings.DATABASE,
            migrator_role=own_settings.MIGRATOR)
    def connections(self,identity):
        c.require(identity=='admin')
        conf=self.policy['connections']['admin']
        return PinnedConnections(endpoint=conf['endpoint'],principal=conf['principal'],
            password_file=conf['password_file'],native=NativePeerCertificate(self.policy['native_providers']))


class InspectionPolicy:
    """Root-approved source templates, fresh verified session bindings only.

    Catalog definitions/context are fixed before any observation. Only binding
    and subject-session fields are filled by this trusted host. Registered bytes
    cannot be supplied by an executor over RPC to obtain profile approval.
    """
    def __init__(self,deployment):
        self.deployment=deployment;self.registered={}

    def contract(self,name,binding,session):
        base=d.parse(checked_file(self.deployment.policy['inspection_templates'][name]).read_bytes())
        c.require(base['binding'] is None and base['subject_session'] is None)
        base['binding']=dict(binding);base['subject_session']=asdict(session)
        raw=d.encode(base)
        self.registered[sha256(raw).hexdigest()]=raw
        return raw

    def verify(self,profile_json,contract_json):
        from migrations.dev09b_inspection import InspectionApproval,digest
        from migrations.dev09b_prerequisites import ProfileAttestation,decode_profile
        dep=self.deployment
        c.require(profile_json==dep.profile and self.registered.get(sha256(contract_json).hexdigest())==contract_json)
        profile=decode_profile(profile_json);contract=d.parse(contract_json)
        return InspectionApproval(ProfileAttestation(sha256(profile_json).hexdigest(),profile['target_sha256'],
            profile['bundle_sha256'],True,'OPERATIONAL'),sha256(contract_json).hexdigest(),
            digest(contract['binding']),dep.policy['decision_reference'])


class FixedAuthorityTrust:
    def __init__(self,deployment):self.dep=deployment
    def public_key(self,payload,control):
        c.require(c.canonical(payload)==self.dep.snapshot.payload)
        return self.dep.key
    def validate_artifacts(self,snapshot,profile_json):
        c.require(snapshot==self.dep.snapshot and profile_json==self.dep.profile)
    def authorize_record(self,attempt_id,event):
        c.require(attempt_id==self.dep.payload['attempt_id'])
    def authorize_revocation(self,approval_id):
        raise c.Unsupported('Public host does not expose revocation')


def make_clock(policy):
    anchor=policy['clock_anchor']
    c.require(type(anchor['source_reference']) is str and bool(anchor['source_reference']))
    c.require(Path('/proc/sys/kernel/random/boot_id').read_text().strip()==anchor['boot_id'])
    clock=AnchoredClock(anchor['lower'],anchor['upper'],max_age=900,drift_ppm=100)
    # Use the approved sampling instant; startup delay consumes the lifetime.
    c.integer(anchor['monotonic_microseconds'],0)
    clock.started=anchor['monotonic_microseconds']/1000000
    clock.sample()
    return clock


def session_binding(connection,deployment):
    from migrations.dev09b_inspection_queries import QUERIES
    from .model import SessionBinding
    row=connection.execute(text("""SELECT (extract(epoch FROM backend_start)*1000000)::bigint AS started,
        pg_catalog.pg_current_xact_id()::text AS xid FROM pg_catalog.pg_stat_activity WHERE pid=pg_backend_pid()""")).mappings().one()
    binding=dict(connection.execute(text(QUERIES['identity'].sql)).mappings().one())
    target=deployment.target
    c.require(binding['database']==target['database_name'] and binding['system_identifier']==target['system_identifier']
              and binding['current_user']==binding['session_user']==target['migrator_role'])
    session=SessionBinding(deployment.payload['target_binding_sha256'],c.digest('executor',deployment.executor),
        deployment.executor['incarnation_id'],binding['pid'],row['started'],row['xid'])
    session.validate()
    return session,binding


def check_live_binding(connections,session,binding,target):
    """Independent numeric xid/virtualxid/start cross-representation check."""
    conn=tx=None
    try:
        conn=connections();tx=conn.begin()
        conn.execute(text('SET TRANSACTION READ ONLY')).close()
        row=conn.execute(text("""SELECT a.pid,a.backend_start::text AS backend_start,a.xact_start::text AS xact_start,
            (extract(epoch FROM a.backend_start)*1000000)::bigint AS started,a.usename,
            v.virtualtransaction AS virtualxid,x.transactionid::text AS xid
            FROM pg_catalog.pg_stat_activity a
            JOIN pg_catalog.pg_locks v ON v.pid=a.pid AND v.locktype='virtualxid' AND v.mode='ExclusiveLock' AND v.granted
            JOIN pg_catalog.pg_locks x ON x.pid=a.pid AND x.locktype='transactionid' AND x.mode='ExclusiveLock' AND x.granted
            WHERE a.pid=:pid"""),dict(pid=session.backend_pid)).mappings().one()
        c.require(row['started']==session.backend_start and row['xid']==str(int(session.transaction_id)%(2**32)))
        for key in ('pid','backend_start','xact_start','virtualxid'):c.require(row[key]==binding[key])
        c.require(row['usename']==target['migrator_role'])
    finally:
        try:
            if tx is not None:tx.rollback()
        finally:
            if conn is not None:conn.close()


class SupervisorHost:
    """Admissions stop on failure; reconciliation/containment listeners survive."""
    def __init__(self,deployment,continuity,clock,admin,probe):
        self.dep,self.continuity,self.clock=deployment,continuity,clock
        self.admin,self.probe=admin,probe
        self.window=None;self.session=None;self.binding=None;self.proof=None;self.failed=False
        self.inspection=InspectionPolicy(deployment)

    def tick(self):
        if self.failed:return
        try:
            if self.window is None:self.clock.sample();self.continuity.sample()
            else:self.window('sample',{})
        except BaseException:
            self.failed=True;self.continuity.block()

    def attach(self,args):
        from .model import SessionBinding
        c.closed(args,{'session','binding'})
        c.require(not self.failed and self.window is None)
        session=SessionBinding(**args['session']);session.validate();binding=args['binding']
        c.require((session.target_sha256,session.executor_sha256,session.incarnation_id)==
            (self.dep.payload['target_binding_sha256'],c.digest('executor',self.dep.executor),self.dep.executor['incarnation_id']))
        t=self.dep.target
        for field,expected in (('database',t['database_name']),('system_identifier',t['system_identifier']),
                               ('session_user',t['migrator_role']),('current_user',t['migrator_role'])):
            c.require(binding[field]==expected)
        check_live_binding(self.admin,session,binding,t)
        observed=dict(database=t['database_name'],system_identifier=t['system_identifier'],principal=own_settings.ADMIN,
            pid=session.backend_pid,usename=t['migrator_role'],**{k:binding[k] for k in ('backend_start','xact_start','virtualxid')})
        observer=PostgresWindowObserver(connections=self.admin,binding=observed)
        def observe():
            check_live_binding(self.admin,session,binding,t)
            observer()
        self.session,self.binding=session,binding
        self.window=WindowDispatch(continuity=self.continuity,clock=self.clock,session=session,plan=self.dep.snapshot.plan,observe=observe)
        self.window('sample',{})

    def executor_dispatch(self,method,args):
        if method=='attach':
            try:return self.attach(args)
            except BaseException:
                self.failed=True;self.continuity.block();raise
        if method in {'rollback','verify_final'}:
            c.closed(args,set());c.require(self.session is not None)
            if method=='rollback':c.require(self.proof is None)
            self.failed=True;self.continuity.block()  # closed even if collection fails
            from .rollback import RollbackCollector
            # A fresh collector binding is constructed inside its own transaction.
            collector=RollbackCollector(connections=self.probe,snapshot=self.dep.snapshot,session=self.session,
                profile_json=self.dep.profile,contract=None,verifier=self.inspection,source_root=self.dep.policy['source_root'])
            collector.cleaned=method=='verify_final'
            collector.contract_factory=lambda actual:self.inspection.contract('final' if collector.cleaned else 'rollback',actual,self.session)
            proof=collector()
            if method=='rollback':self.proof=proof
            else:
                verify_storage(self.dep.policy['storage'])
                self.continuity._write_new('CLEANED_VERIFIED',d.encode(proof))
            return proof
        if method=='record_rollback':
            c.closed(args,{'evidence_sha256'})
            c.require(self.proof is not None and args['evidence_sha256']==sha256(d.encode(self.proof)).hexdigest())
            verify_storage(self.dep.policy['storage'])
            self.continuity._write_new('ROLLBACK_CONFIRMED',d.encode(self.proof))
            return None
        if method=='contain':
            c.closed(args,set());self.failed=True
            blocked='DURABLE'
            try:self.continuity.block()
            except BaseException:blocked='UNCERTAIN'
            from .containment import contain_target
            result=contain_target(self.admin,self.dep.target)
            result['window_block']=blocked
            return result
        c.require(method in {'sample','time','assert_bound','block'})
        c.require(self.window is not None)
        return self.window(method,args)

    def authority_dispatch(self,method,args):
        c.require(method in {'sample','time','block'})
        return self.executor_dispatch(method,args)


def host_loop(listeners,*,tick=None):
    """One serialized process. No auto restart or replacement of socket paths."""
    try:
        while True:
            if tick is not None:tick()
            ready,_,_=select.select([s for s,_,_ in listeners],[],[],0.5)
            for sock,uid,dispatch in listeners:
                if sock in ready:serve_one(sock,caller_uid=uid,dispatch=dispatch,timeout=15.0)
    finally:
        for sock,_,_ in listeners:sock.close()
