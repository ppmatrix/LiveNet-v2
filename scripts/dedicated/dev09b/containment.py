"""Administrative containment independent of successful outcome reconciliation.

Only for the fixed disposable/role under the adopted trusted-admin direction B.
Never drops, reassigns or repairs objects; never clears UNKNOWN/window block.
No I/O until explicitly invoked by the separately authorized supervisor host.
"""
from sqlalchemy import text
from . import codec as c,own_settings as h


DISABLE='ALTER ROLE dev09b_trial_migrator NOLOGIN'
TERMINATE="SELECT pg_catalog.pg_terminate_backend(pid,5000) FROM pg_catalog.pg_stat_activity WHERE usename='dev09b_trial_migrator'"
REVOKES=(
    'REVOKE EXECUTE ON FUNCTION public.dev09b_own_preload_settings() FROM dev09b_trial_migrator',
    'REVOKE EXECUTE ON FUNCTION pg_catalog.pg_control_system() FROM dev09b_trial_migrator',
    'REVOKE ALL ON SCHEMA public,inventory,audit FROM dev09b_trial_migrator',
    'REVOKE CONNECT ON DATABASE livenet_v2_dev FROM dev09b_trial_migrator',
)
VERIFY="""SELECT r.rolcanlogin AS login,
 (SELECT count(*) FROM pg_catalog.pg_stat_activity WHERE usename=r.rolname) AS sessions,
 (SELECT count(*) FROM pg_catalog.pg_prepared_xacts WHERE owner=r.rolname) AS prepared,
 pg_catalog.has_database_privilege(r.oid,current_database(),'CONNECT') AS connect,
 pg_catalog.has_database_privilege(r.oid,current_database(),'CREATE') AS database_create,
 pg_catalog.has_database_privilege(r.oid,current_database(),'TEMP') AS temporary,
 pg_catalog.has_function_privilege(r.oid,'public.dev09b_own_preload_settings()','EXECUTE') AS helper,
 pg_catalog.has_function_privilege(r.oid,'pg_catalog.pg_control_system()','EXECUTE') AS control,
 EXISTS(SELECT FROM pg_catalog.pg_namespace n WHERE n.nspname IN ('public','inventory','audit','security')
   AND pg_catalog.has_schema_privilege(r.oid,n.oid,'CREATE')) AS schema_create,
 (SELECT count(*) FROM pg_catalog.pg_auth_members WHERE member=r.oid OR roleid=r.oid) AS memberships,
 (SELECT count(*) FROM pg_catalog.pg_shdepend WHERE refclassid='pg_catalog.pg_authid'::pg_catalog.regclass
   AND refobjid=r.oid AND deptype='o') AS ownership,
 pg_catalog.to_regclass('public.alembic_version') IS NOT NULL AS ledger_present
 FROM pg_catalog.pg_roles r WHERE r.rolname='dev09b_trial_migrator'"""


def admin_action(connections,target,action,*,readonly=False):
    connection=transaction=None
    try:
        c.require(target['system_identifier']==h.TARGET_SID and target['database_name']==h.DATABASE
                  and target['migrator_role']==h.MIGRATOR)
        connection=connections();c.require(not connection.in_transaction())
        c.require(connection.connection.driver_connection.autocommit is False)
        transaction=connection.begin()
        if readonly:connection.execute(text('SET TRANSACTION READ ONLY')).close()
        for sql in ("SET LOCAL statement_timeout='7000ms'","SET LOCAL lock_timeout='1000ms'"):
            connection.execute(text(sql)).close()
        row=connection.execute(text("""SELECT current_database() AS database,session_user::text AS principal,
            current_user::text AS effective_principal,(pg_catalog.pg_control_system()).system_identifier::text AS sid""")).mappings().one()
        c.require((row['database'],row['principal'],row['effective_principal'],row['sid'])==
                  (h.DATABASE,h.ADMIN,h.ADMIN,h.TARGET_SID))
        result=action(connection)
        if readonly:transaction.rollback()
        else:transaction.commit()
        return result
    finally:
        try:
            if transaction is not None and transaction.is_active:transaction.rollback()
        finally:
            if connection is not None:connection.close()


def verify_target(connections,target):
    result=admin_action(connections,target,lambda conn:dict(conn.execute(text(VERIFY)).mappings().one()),readonly=True)
    c.require(all(type(v) in {int,bool} for v in result.values()))
    return result


def verification_safe(value):
    if type(value) is not dict:return False
    booleans={'login','connect','database_create','temporary','helper','control','schema_create','ledger_present'}
    counts={'sessions','prepared','memberships','ownership'}
    return (set(value)==booleans|counts and all(value[k] is False for k in booleans)
            and all(type(value[k]) is int and value[k]==0 for k in counts))


def contain_target(connections,target):
    result={}
    # Separate transactions: NOLOGIN survives a later timeout; no dependence on
    # authority, interlock availability, successful rollback proof or a receipt.
    for phase,action in (
        ('disable_login',lambda conn:conn.execute(text(DISABLE)).close()),
        ('terminate_sessions',lambda conn:list(conn.execute(text(TERMINATE)))),
        ('revoke',lambda conn:[conn.execute(text(sql)).close() for sql in REVOKES]),
    ):
        try:
            admin_action(connections,target,action)
            result[phase]='RETURNED'
        except BaseException as exc:
            result[phase]='UNCERTAIN';result[phase+'_exception']=type(exc).__name__
    try:
        result['verification']=verify_target(connections,target)
    except BaseException as exc:
        result['verification']='UNAVAILABLE';result['verification_exception']=type(exc).__name__
    return result
