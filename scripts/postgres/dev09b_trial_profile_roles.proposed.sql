-- PROPOSAL ONLY: four inert logical identities required by the existing v2
-- parameter schema. None is used to authorize recovery/runtime/handoff here.
-- Separate material item for joint approval; no silent creation or grants.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL search_path=pg_catalog;
DO $guard$
BEGIN
 IF current_database()<>'livenet_v2_dev' OR current_user<>'dev09b_trial_admin'
 OR (SELECT system_identifier::text FROM pg_catalog.pg_control_system())<>'7705421224394444834'
 THEN RAISE EXCEPTION 'DEV09B_TARGET_DIVERGENCE'; END IF;
END $guard$;
CREATE ROLE dev09b_trial_application_ledger_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 0 PASSWORD NULL;
CREATE ROLE dev09b_trial_security_ledger_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 0 PASSWORD NULL;
CREATE ROLE dev09b_trial_runtime NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 0 PASSWORD NULL;
CREATE ROLE dev09b_trial_recovery NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 0 PASSWORD NULL;
COMMIT;
