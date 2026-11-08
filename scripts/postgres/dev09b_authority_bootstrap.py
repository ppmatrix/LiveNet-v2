"""One-shot administrative load of an ALREADY signed, approved trial envelope.

No issuance, database creation, synthetic fixture promotion, reset, upsert or
service installation. Requires a separately provisioned TLS authority database,
root-controlled operational policy and explicit administrative invocation.
"""
from hashlib import sha256
import os
from pathlib import Path
from sqlalchemy import text
from scripts.dedicated.dev09b import codec as c
from scripts.dedicated.dev09b.tls import checked_file


OWNER='dev09b_authority_owner'
SERVICE='dev09b_authority_service'
DATABASE='dev09b_authority_dev'
ADMIN='dev09b_authority_admin'


def bootstrap(deployment):
    c.require(os.geteuid()==0)
    policy=deployment.policy;dest=policy['authority_destination']
    c.require(dest['database']==DATABASE and dest['principal']==SERVICE)
    c.require(dest['system_identifier']!=deployment.target['system_identifier'])
    schema=checked_file(policy['files']['authority_schema']).read_bytes()
    original=Path(policy['source_root'])/'scripts/postgres/dev09b_authority_schema.proposed.sql'
    c.require(schema==original.read_bytes())
    conn=tx=None
    try:
        conn=deployment.connections('authority_admin')();c.require(not conn.in_transaction())
        tx=conn.begin()
        for sql in ("SET LOCAL statement_timeout='5000ms'","SET LOCAL lock_timeout='1000ms'"):
            conn.execute(text(sql)).close()
        row=conn.execute(text("""SELECT current_database() AS database,session_user::text AS principal,
            current_user::text AS effective_principal,(pg_catalog.pg_control_system()).system_identifier::text AS sid""")).mappings().one()
        c.require((row['database'],row['principal'],row['effective_principal'],row['sid'])==
                  (DATABASE,ADMIN,ADMIN,dest['system_identifier']))
        for sql in (
            'REVOKE ALL ON DATABASE dev09b_authority_dev FROM PUBLIC',
            'REVOKE ALL ON SCHEMA public FROM PUBLIC',
            'CREATE ROLE dev09b_authority_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 0 PASSWORD NULL',
            'CREATE ROLE dev09b_authority_service NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 1 PASSWORD NULL',
        ):conn.execute(text(sql)).close()
        conn.exec_driver_sql(schema.decode()).close()
        for sql in (
            'ALTER SCHEMA dev09b_authority OWNER TO dev09b_authority_owner',
            *('ALTER TABLE dev09b_authority.'+name+' OWNER TO dev09b_authority_owner' for name in ('control','approvals','nonces','events')),
            'GRANT CONNECT ON DATABASE dev09b_authority_dev TO dev09b_authority_service',
            'GRANT USAGE ON SCHEMA dev09b_authority TO dev09b_authority_service',
            'GRANT SELECT ON dev09b_authority.control,dev09b_authority.approvals TO dev09b_authority_service',
            'GRANT UPDATE(last_time) ON dev09b_authority.control TO dev09b_authority_service',
            'GRANT UPDATE(state,session_json) ON dev09b_authority.approvals TO dev09b_authority_service',
            'GRANT INSERT ON dev09b_authority.nonces,dev09b_authority.events TO dev09b_authority_service',
            'GRANT USAGE ON SEQUENCE dev09b_authority.events_sequence_seq TO dev09b_authority_service',
            'GRANT EXECUTE ON FUNCTION pg_catalog.pg_control_system() TO dev09b_authority_service',
        ):conn.execute(text(sql)).close()
        p=deployment.payload
        conn.execute(text("""INSERT INTO dev09b_authority.control
          (singleton,authority_epoch,revocation_epoch,continuity_token,blocked,last_time)
          VALUES(true,:authority_epoch,:revocation_epoch,CAST(:token AS uuid),false,0)"""),
          dict(authority_epoch=p['authority_epoch'],revocation_epoch=p['revocation_epoch'],token=policy['continuity_token'])).close()
        values=dict(approval_id=p['approval_id'],attempt_id=p['attempt_id'],envelope=deployment.envelope,
            **{key:getattr(deployment.snapshot,key) for key in ('payload','target','executor','plan','semantic','physical','provenance')})
        conn.execute(text("""INSERT INTO dev09b_authority.approvals
          (approval_id,attempt_id,state,revoked,envelope,payload,target,executor,plan,semantic,physical,provenance)
          VALUES(CAST(:approval_id AS uuid),CAST(:attempt_id AS uuid),'AVAILABLE',false,
            :envelope,:payload,:target,:executor,:plan,:semantic,:physical,:provenance)"""),values).close()
        tx.commit()
        return dict(status='SIGNED_APPROVAL_LOADED_SERVICE_STILL_NOLOGIN',envelope_sha256=sha256(deployment.envelope).hexdigest())
    finally:
        try:
            if tx is not None and tx.is_active:tx.rollback()
        finally:
            if conn is not None:conn.close()
