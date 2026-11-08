-- PROPOSAL ONLY; no current authorization to execute this file.
-- Target: existing querytrial, SID 7705421224394444834, livenet_v2_dev.
-- Execute only AFTER named roles, TLS, approved profile, authenticated authority,
-- independent continuity and an external exclusive window are actually ready.
-- dev09b_trial_migrator is a PROPOSED new identity, not an existing binding.
-- Credentials are provisioned separately through a private administrative channel.
-- The helper grant below REQUIRES a separate approved helper-policy amendment;
-- the installed source policy currently allows only dev09b_trial_probe.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL search_path=pg_catalog;
SET LOCAL statement_timeout='5s';
SET LOCAL lock_timeout='1s';
DO $guard$
DECLARE m pg_catalog.pg_roles%ROWTYPE;
BEGIN
  IF current_database()<>'livenet_v2_dev' OR current_user<>'dev09b_trial_admin'
    OR (SELECT system_identifier::text FROM pg_catalog.pg_control_system())<>'7705421224394444834'
  THEN RAISE EXCEPTION 'DEV09B_TARGET_DIVERGENCE'; END IF;
  SELECT * INTO STRICT m FROM pg_catalog.pg_roles WHERE rolname='dev09b_trial_migrator';
  IF m.rolcanlogin OR EXISTS(SELECT 1 FROM pg_catalog.pg_stat_activity WHERE usename=m.rolname)
    OR m.rolsuper OR m.rolcreatedb OR m.rolcreaterole OR m.rolreplication OR m.rolbypassrls OR m.rolinherit
    OR EXISTS(SELECT 1 FROM pg_catalog.pg_auth_members WHERE member=m.oid OR roleid=m.oid)
    OR pg_catalog.has_database_privilege(m.oid,current_database(),'CREATE')
    OR pg_catalog.has_database_privilege(m.oid,current_database(),'TEMP')
  THEN RAISE EXCEPTION 'DEV09B_MIGRATOR_EXCESS_PRIVILEGES'; END IF;
END $guard$;
GRANT CONNECT ON DATABASE livenet_v2_dev TO dev09b_trial_migrator;
GRANT USAGE,CREATE ON SCHEMA public,inventory,audit TO dev09b_trial_migrator;
GRANT EXECUTE ON FUNCTION pg_catalog.pg_control_system() TO dev09b_trial_migrator;
-- PENDING MATERIAL APPROVAL + versioned helper policy/profile update:
GRANT EXECUTE ON FUNCTION public.dev09b_own_preload_settings() TO dev09b_trial_migrator;
-- LOGIN requires an already provisioned private credential; never embed it here.
ALTER ROLE dev09b_trial_migrator LOGIN CONNECTION LIMIT 1;
COMMIT;
-- No DATABASE CREATE/TEMP, security CREATE/USAGE, role memberships, runtime
-- grants, blanket extension grants or default ACLs are authorized/proposed.
-- Before migration COMMIT, the following exact owner-issued column grant is
-- REQUIRED for independent PERSISTED observation, but NOT installed here:
-- GRANT SELECT(version_num) ON TABLE public.alembic_version TO dev09b_trial_probe;
-- It needs a separately approved transaction step AND PRECOMMIT/PERSISTED
-- expectation update. before_commit only permits SELECT, so cannot add it there.
