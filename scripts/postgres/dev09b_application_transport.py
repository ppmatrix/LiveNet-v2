"""DEV09B-PREPARED-1 application Alembic body, borrowed connection/transaction.

No engine, credentials, authority storage, consumption, commit or CLI.
A trusted operational admission controller must invoke the one-shot callback
inside its original consumed attempt after live checks. Offline observations,
signature results, digests and booleans cannot dispatch this body. Installing
this adapter does NOT open any gate or supply trusted operational adapters.
"""
from typing import Protocol
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

# Canonical namespace used by backend/migrations/env.py. Deliberately do not
# alias backend.migrations.* objects: duplicate module identities must refuse.
from migrations import dev09b_prerequisites as h
from migrations.dev09b_inspection_support import check_client_logging
from scripts.dedicated.dev09b.layers import APP_REVISIONS
from scripts.dedicated.dev09b.model import OfflineObservation,OfflineAttempt

ROOT=Path(__file__).resolve().parents[2]
OPERATION='application-base-to-f066a01a7230'
TARGET='f066a01a7230'


class OriginalAdmission(Protocol):
    """Trusted injection, not an approval-document parser or capability issuer.

    AdmissionController implements this callback boundary. It must durably consume/bind the
    attempt and check authority/time/continuity/exclusivity before permitting
    effects. Its callback invocation, NOT its return value, dispatches work.
    Commit/reconciliation and exact SQL-effect checkpoints belong to it too.
    """
    def dispatch_original(self, *, operation, connection, transaction, profile_json, body): ...


class ApplicationTransport:
    """One-shot low-level body; never a standalone authorized executor.

    Calls the actual Alembic command when its explicit trusted controller invokes
    the body. Does not use the permanently blocked historical AUTH-03 executor.
    This adapter checks transaction identity before/after; it does not claim to
    prevent every raw-driver escape or implement external-writer exclusion.
    """
    def __init__(self, connection, transaction, prepared_context):
        self.connection=connection
        self.transaction=transaction
        self.context=prepared_context
        self.attempted=False
        # Construction does not inspect a connection or invoke any port.

    def _bound(self):
        c=self.connection
        h.require(c is not None and c.closed is False and c.dialect.name=='postgresql','Explicit PostgreSQL connection required')
        h.require(c.in_transaction() is True and c.get_transaction() is self.transaction
                  and self.transaction is not None and self.transaction.is_active is True,'Transaction changed')
        check_client_logging(c)
        # A SQLAlchemy logical transaction in DBAPI AUTOCOMMIT mode cannot
        # provide the approved single-transaction migration guarantee.
        h.require(c.get_execution_options().get('isolation_level')!='AUTOCOMMIT'
                  and c.connection.driver_connection.autocommit is False
                  and c.get_isolation_level() in {'READ COMMITTED','REPEATABLE READ','SERIALIZABLE'},
                  'Real PostgreSQL transaction required; AUTOCOMMIT forbidden')
        h.require(type(self.context) is h.PreparedContext,'Canonical migrations.PreparedContext required')
        profile=h.decode_profile(self.context.profile_json)
        h.require(profile['operation']==OPERATION,'Application base-to-f066 only')
        h.require(callable(getattr(self.context.port,'assert_connection',None)),'Prepared binding port required')
        self.context.port.assert_connection(c)

    def _config(self):
        self._bound()
        # No .ini URL, logging sections/fileConfig, relative sys.path or fallback.
        config=Config()
        config.set_main_option('script_location',str(ROOT/'backend/migrations'))
        config.set_main_option('prepend_sys_path',str(ROOT/'backend'))
        config.set_main_option('path_separator','os')
        config.set_main_option('version_table','alembic_version')
        config.set_main_option('version_table_schema','public')
        config.attributes['connection']=self.connection
        config.attributes[h.ATTR]=self.context
        config.attributes['auth03_require_external_connection']=True
        graph=ScriptDirectory.from_config(config)
        chain=tuple(reversed(tuple(x.revision for x in graph.walk_revisions(base='base',head=TARGET))))
        h.require(chain==APP_REVISIONS,'Unexpected application chain')
        h.require(graph.get_revision(APP_REVISIONS[0]).down_revision is None,'Application source is not base')
        return config

    def apply_once(self, admission):
        h.require(not self.attempted,'Original body already attempted; no retry')
        # This local latch is NOT the authority's durable consumption record.
        self.attempted=True
        h.require(not isinstance(admission,(OfflineObservation,OfflineAttempt,dict,str,bytes,bool)),
                  'Offline data is not operational admission')
        method=getattr(admission,'dispatch_original',None)
        if not callable(method):raise h.MissingParameter('dev09b.live_original_admission_controller')
        config=self._config()
        active=True;invoked=False;returned=False
        def body():
            nonlocal invoked,returned
            h.require(active and not invoked,'Late or repeated dispatch refused')
            invoked=True  # A failure remains attempted; no release/retry.
            self._bound()
            h.require(config.attributes.get('connection') is self.connection
                      and config.attributes.get(h.ATTR) is self.context,'Alembic binding changed')
            h.require(config.config_file_name is None and config.get_main_option('sqlalchemy.url') is None
                      and config.get_main_option('script_location')==str(ROOT/'backend/migrations')
                      and config.get_main_option('version_locations') is None,'Alembic configuration changed')
            command.upgrade(config,TARGET,sql=False)
            self._bound()
            returned=True
        try:
            method(operation=OPERATION,connection=self.connection,transaction=self.transaction,
                   profile_json=self.context.profile_json,body=body)
            h.require(invoked and returned,'Admission returned without completing original body')
            self._bound()
        finally:
            active=False
        # None means command returned inside the borrowed transaction. It is NOT
        # commit success, independent confirmation, approval or a retry token.


def apply_authorized_application(*, connection, transaction, snapshot, session,
                                 authority, supervision, profile_json,
                                 profile_verifier, prerequisite_contracts,
                                 source_root):
    """Composition for an explicitly supplied, originally authorized attempt.

    No connection/factory discovery, synthetic receipt, commit or reconciliation.
    The caller owns containment of setup failures and the borrowed connection.
    On return the real AdmissionController owns the guarded uncommitted result;
    its commit_once() and independent reconciliation remain explicit next calls.
    """
    from scripts.dedicated.dev09b import codec as c
    from scripts.dedicated.dev09b.admission import AdmissionController
    from scripts.dedicated.dev09b.postgres_authority import AuthenticatedAuthorityClient
    from migrations.dev09b_inspection import PreparedInspectionPort
    c.require(type(authority) is AuthenticatedAuthorityClient)
    c.validate_layers(snapshot)
    h.require(authority.payload==snapshot.payload and authority.session==session
              and authority.profile_json==profile_json,'Authority/snapshot binding')
    c.require(profile_verifier is not None and supervision is not None)
    port=PreparedInspectionPort(connection,transaction,profile_verifier=profile_verifier,
        source_root=source_root,detailed_snapshot=snapshot,detailed_session=session,
        prerequisite_contracts=prerequisite_contracts)
    context=h.PreparedContext(profile_json,port)
    controller=AdmissionController(authority=authority,session=session,connection=connection,
        transaction=transaction,supervision=supervision,plan=snapshot.plan)
    transport=ApplicationTransport(connection,transaction,context)
    try:
        transport.apply_once(controller)
        h.require(port._cursor==5,'Incomplete prepared prerequisite sequence')
    except BaseException:
        if connection.closed is not True:controller.contain()
        raise
    return controller
