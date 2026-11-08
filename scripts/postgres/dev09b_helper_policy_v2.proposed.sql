-- VERSION 2 / PROPOSAL ONLY. Design adopted; execution not yet authorized.
-- Body/owner/membership unchanged from dedicated-owner v1. Only one temporary ACL.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL search_path=pg_catalog;
SET LOCAL statement_timeout='5s';
SET LOCAL lock_timeout='1s';
DO $guard$
BEGIN
 IF current_database()<>'livenet_v2_dev' OR current_user<>'dev09b_trial_admin'
   OR (SELECT system_identifier::text FROM pg_catalog.pg_control_system())<>'7705421224394444834'
   OR (SELECT p.proowner FROM pg_catalog.pg_proc p WHERE p.oid='public.dev09b_own_preload_settings()'::pg_catalog.regprocedure)
      <>(SELECT oid FROM pg_catalog.pg_roles WHERE rolname='dev09b_trial_settings_owner')
 THEN RAISE EXCEPTION 'DEV09B_HELPER_POLICY_TARGET'; END IF;
END $guard$;
-- v1 body/config/ACL/owner/membership must be authenticated by the preflight first.
GRANT EXECUTE ON FUNCTION public.dev09b_own_preload_settings() TO dev09b_trial_migrator;
COMMIT;
-- Removal: REVOKE EXECUTE ON FUNCTION public.dev09b_own_preload_settings() FROM dev09b_trial_migrator;
