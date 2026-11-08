"""Source-bound independent rollback reconciliation, separate from admission.

The compared baseline is APP-ENTRY prefix zero with temporary powers still
present. Therefore rollback proof does not falsely imply privilege removal.
Containment remains possible with an unavailable authority or failed comparison.
"""
from dataclasses import asdict
from hashlib import sha256

from . import codec as c, detailed_catalog as d, physical as p
from .layers import read_snapshot, document_hash
from .evidence import OriginObservation


def expected_baseline(snapshot):
    payload,target,executor,plan,semantic,physical,provenance=read_snapshot(snapshot)
    c.require(payload['operation']=='application-base-to-f066a01a7230' and physical['schema_version']==2)
    return p.compile_profile('APP-ENTRY',target,physical['parameters'],
        d.migration_inputs(physical,semantic,provenance),prerequisite=0)


def validate(snapshot,session,evidence,*,cleaned=False):
    c.closed(evidence, {'schema_version','kind','collector_id','target_binding_sha256',
        'request_id','approval_id','attempt_id','subject_session','snapshot',
        'migrator_sessions','prepared_transactions'})
    c.integer(evidence['schema_version'],1,1)
    c.require(evidence['kind']==('ROLLBACK-CLEANED-V1' if cleaned else 'ROLLBACK-BASELINE-V1'))
    c.identifier(evidence['collector_id'])
    payload=read_snapshot(snapshot)[0]
    for field in ('target_binding_sha256','request_id','approval_id','attempt_id'):
        c.require(evidence[field]==payload[field])
    c.require(d.encode(evidence['subject_session'])==d.encode(asdict(session)))
    c.require(type(evidence['migrator_sessions']) is int and evidence['migrator_sessions']==0)
    c.require(type(evidence['prepared_transactions']) is int and evidence['prepared_transactions']==0)
    expected=expected_baseline(snapshot)
    if not cleaned:return p.compare_profile(expected,evidence['snapshot'])
    from .trial_policy import cleaned_snapshot
    wanted=cleaned_snapshot(d.parse(expected.json),read_snapshot(snapshot)[1]['migrator_role'])
    p.validate_snapshot(evidence['snapshot'])
    c.require(d.encode(wanted)==d.encode(evidence['snapshot']))
    return p.PhysicalComparison('APP-ENTRY',document_hash(wanted),document_hash(evidence['snapshot']))


class RemoteRollback:
    """Origin/independence from an exact-UID independent supervisor connection.

    No naked file, classification flag or caller-supplied digest authenticates.
    Evidence must be the exact response just obtained. Persistence is a separate
    RPC, after local comparison, to the independent durable window journal.
    """
    def __init__(self,rpc,collector_id):
        self.rpc,self.collector_id=rpc,collector_id
        self.raw=None;self.authenticated=False

    def collect(self):
        c.require(self.raw is None)
        result=self.rpc.call('rollback',{})
        self.raw=d.encode(result)
        return d.parse(self.raw)

    def inspect(self,raw):
        import os
        c.require(self.rpc.server_uid!=os.geteuid() and self.raw is not None and raw==self.raw)
        value=d.parse(raw);c.require(value['collector_id']==self.collector_id)
        self.authenticated=True
        return OriginObservation(document_hash(value),self.collector_id,'OPERATIONAL',True)

    def confirm(self,raw):
        c.require(self.authenticated and self.raw==raw)

    def persist(self,raw):
        self.confirm(raw)
        c.require(self.rpc.call('record_rollback',dict(evidence_sha256=sha256(raw).hexdigest())) is None)


class RollbackCollector:
    def __init__(self, *, connections,snapshot,session,profile_json,contract,verifier,source_root):
        self.connections,self.snapshot,self.session=connections,snapshot,session
        self.profile,self.contract,self.verifier,self.root=profile_json,contract,verifier,source_root
        self.cleaned=False

    def __call__(self):
        from sqlalchemy import text
        from migrations.dev09b_inspection import PreparedInspectionPort,_detailed_setup,collect_detailed_sql
        from migrations.dev09b_catalog_adapter import convert_results
        connection=transaction=None
        try:
            connection=self.connections();c.require(not connection.in_transaction())
            transaction=connection.begin()
            for statement in ('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY',
                              "SET LOCAL statement_timeout='5000ms'","SET LOCAL lock_timeout='1000ms'"):
                connection.execute(text(statement)).close()
            if hasattr(self,'contract_factory'):
                from migrations.dev09b_inspection_queries import QUERIES
                binding=dict(connection.execute(text(QUERIES['identity'].sql)).mappings().one())
                self.contract=self.contract_factory(binding)
            port=PreparedInspectionPort(connection,transaction,profile_verifier=self.verifier,
                contract_json=self.contract,source_root=self.root)
            # Authenticate full source context + inspector binding; compare the
            # active-window prefix zero below, not the closed DEV-BASE profile.
            contract,*_=_detailed_setup(port,self.profile,self.snapshot,phase='DEV-BASE',session=self.session)
            payload,target,*_=read_snapshot(self.snapshot)
            def absent():
                connection.execute(text('SELECT pg_catalog.pg_stat_clear_snapshot()')).close()
                row=connection.execute(text("""SELECT
                  (SELECT count(*) FROM pg_catalog.pg_stat_activity WHERE usename=:role) AS sessions,
                  (SELECT count(*) FROM pg_catalog.pg_stat_activity WHERE datname=current_database()
                    AND pid<>pg_backend_pid() AND backend_type='client backend') AS other_clients,
                  (SELECT count(*) FROM pg_catalog.pg_prepared_xacts) AS prepared"""),dict(role=target['migrator_role'])).mappings().one()
                c.require(row['sessions']==0 and row['prepared']==0 and row['other_clients']==0)
                return row
            absent()
            batch=collect_detailed_sql(connection,transaction,collector_id=contract['collector_id'],
                expected_binding=contract['binding'],approved_helpers=contract['context'].get('approved_helpers',[]),**contract['selections'])
            converted=convert_results(batch.historical,batch.supplemental,contract['context'],phase='APP-ENTRY',
                collector_id=batch.collector_id,session=asdict(self.session),ledger_rows=batch.ledger_rows)
            observed=d.parse(converted.rows_json)['snapshot'];counts=absent()
            result=dict(schema_version=1,kind='ROLLBACK-CLEANED-V1' if self.cleaned else 'ROLLBACK-BASELINE-V1',collector_id=contract['collector_id'],
                **{k:payload[k] for k in ('target_binding_sha256','request_id','approval_id','attempt_id')},
                subject_session=asdict(self.session),snapshot=observed,
                migrator_sessions=counts['sessions'],prepared_transactions=counts['prepared'])
            validate(self.snapshot,self.session,result,cleaned=self.cleaned)
            return result
        finally:
            try:
                if transaction is not None:transaction.rollback()
            finally:
                if connection is not None:connection.close()
