-- PROPOSAL ONLY: new trusted SECURITY DEFINER exception; not authorized/applied.
-- Existing querytrial only. Requires explicit approval of this contract change
-- AND administrative execution. Never bootstrap this through a migration.
-- The existing owner/admin is retained; no new privileged identity/membership.
BEGIN;
SET LOCAL statement_timeout='5s';
SET LOCAL lock_timeout='1s';
DO $guard$
BEGIN
  IF pg_catalog.current_database()<>'livenet_v2_dev'
     OR current_user<>'dev09b_trial_admin'
     OR (SELECT system_identifier::pg_catalog.text FROM pg_catalog.pg_control_system())<>'7705421224394444834'
  THEN RAISE EXCEPTION 'WRONG_SETTINGS_TRIAL_TARGET'; END IF;
  IF pg_catalog.to_regprocedure('public.dev09b_own_preload_settings()') IS NOT NULL
  THEN RAISE EXCEPTION 'SETTINGS_HELPER_ALREADY_EXISTS'; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname='dev09b_trial_probe'
      AND NOT rolsuper AND NOT rolcreaterole AND NOT rolcreatedb AND NOT rolreplication AND NOT rolbypassrls)
  THEN RAISE EXCEPTION 'PROBE_ROLE_DIVERGENCE'; END IF;
END
$guard$;
CREATE FUNCTION public.dev09b_own_preload_settings()
RETURNS TABLE(backend_pid pg_catalog.int4,name pg_catalog.text,setting pg_catalog.text)
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path=pg_catalog
AS $body$
  SELECT pg_catalog.pg_backend_pid(),wanted.name,pg_catalog.current_setting(wanted.name)
  FROM (VALUES ('shared_preload_libraries'::pg_catalog.text),('session_preload_libraries'::pg_catalog.text)) wanted(name)
$body$;
REVOKE ALL ON FUNCTION public.dev09b_own_preload_settings() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.dev09b_own_preload_settings() TO dev09b_trial_probe;
COMMIT;
-- Does NOT authorize the migrator/runtime, additional settings, arbitrary SQL,
-- authority, receipt, catalog MATCHED, migrations, or changes to any gate.
-- Before applying, the versioned source profile must represent this EXACT
-- helper/body/owner/ACL and allow only this fixed executable-definer identity;
-- all other executable definers remain refused. The probe's backend PID and
-- transaction/identity must still match before/after. Values are observations.
