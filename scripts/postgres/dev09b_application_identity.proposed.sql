-- PROPOSAL ONLY. Named identity for first rollback-only application trial.
-- Private SCRAM credential provisioning is a separate administrative step.
-- No execution, LOGIN, membership or grant is authorized by this file.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL search_path=pg_catalog;
SET LOCAL statement_timeout='5s';
SET LOCAL lock_timeout='1s';
DO $guard$
BEGIN
  IF current_database()<>'livenet_v2_dev' OR current_user<>'dev09b_trial_admin'
    OR (SELECT system_identifier::text FROM pg_catalog.pg_control_system())<>'7705421224394444834'
  THEN RAISE EXCEPTION 'DEV09B_TARGET_DIVERGENCE'; END IF;
END $guard$;
CREATE ROLE dev09b_trial_migrator NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
  NOREPLICATION NOBYPASSRLS NOINHERIT CONNECTION LIMIT 1 PASSWORD NULL;
COMMIT;
