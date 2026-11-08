-- PROPOSAL ONLY; separate administrative action under the same exclusive window.
-- Apply AFTER COMMIT result reconciled independently or confirmed rollback.
-- If outcome is uncertain: contain/isolate, do not handoff/drop anything.
-- This file does NOT implement handoff or confer authorization by its presence.
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
  IF EXISTS(SELECT 1 FROM pg_catalog.pg_stat_activity WHERE usename='dev09b_trial_migrator')
  THEN RAISE EXCEPTION 'DEV09B_MIGRATOR_SESSION_STILL_OPEN'; END IF;
  IF EXISTS(SELECT 1 FROM pg_catalog.pg_prepared_xacts WHERE owner='dev09b_trial_migrator')
  THEN RAISE EXCEPTION 'DEV09B_PREPARED_TRANSACTION_PRESENT'; END IF;
END $guard$;
ALTER ROLE dev09b_trial_migrator NOLOGIN;
REVOKE EXECUTE ON FUNCTION public.dev09b_own_preload_settings() FROM dev09b_trial_migrator;
REVOKE EXECUTE ON FUNCTION pg_catalog.pg_control_system() FROM dev09b_trial_migrator;
REVOKE ALL ON SCHEMA public,inventory,audit FROM dev09b_trial_migrator;
REVOKE CONNECT ON DATABASE livenet_v2_dev FROM dev09b_trial_migrator;
COMMIT;
-- Revoking ACLs does NOT revoke ownership. The administrator must separately
-- hand off EACH exact approved object to the domain/ledger NOLOGIN owner and
-- prove absence of migrator-owned objects and memberships in CLOSED evidence.
-- Do not use DROP OWNED or a broad REASSIGN OWNED as an unreviewed shortcut.
-- Keep probe ledger SELECT(version_num) through independent confirmation;
-- CLOSED expects that specific read permission. No runtime grant is proposed.
