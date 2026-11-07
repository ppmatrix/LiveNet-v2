-- CANDIDATE. Single disposable database only; no LiveNet, extension or helper.
-- Launcher substitutes SCRAM verifiers over private stdin, never argv/logs.
BEGIN;
SET LOCAL statement_timeout='5s';
SET LOCAL lock_timeout='2s';
DO $$ BEGIN
 IF current_database() <> 'dev09b_authority_trial'
 OR session_user <> 'dev09b_authority_trial_admin' THEN
  RAISE EXCEPTION 'AUTHORITY_TRIAL_TARGET_REFUSED';
 END IF;
END $$;
REVOKE ALL ON DATABASE dev09b_authority_trial FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
CREATE ROLE dev09b_authority_trial_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE dev09b_authority_trial_service LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD '__SERVICE_SCRAM__';
CREATE ROLE dev09b_authority_trial_revoker LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD '__REVOKER_SCRAM__';
CREATE ROLE dev09b_authority_trial_observer LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD '__OBSERVER_SCRAM__';
GRANT CONNECT ON DATABASE dev09b_authority_trial TO dev09b_authority_trial_service, dev09b_authority_trial_revoker, dev09b_authority_trial_observer;
-- Exact reviewed schema inserted here by launcher after digest verification.
__AUTHORITY_SCHEMA__
ALTER SCHEMA dev09b_authority OWNER TO dev09b_authority_trial_owner;
ALTER TABLE dev09b_authority.control OWNER TO dev09b_authority_trial_owner;
ALTER TABLE dev09b_authority.approvals OWNER TO dev09b_authority_trial_owner;
ALTER TABLE dev09b_authority.nonces OWNER TO dev09b_authority_trial_owner;
ALTER TABLE dev09b_authority.events OWNER TO dev09b_authority_trial_owner;
-- Identity sequence changes ownership with its table; no permanent memberships.
GRANT USAGE ON SCHEMA dev09b_authority TO dev09b_authority_trial_service, dev09b_authority_trial_revoker, dev09b_authority_trial_observer;
GRANT SELECT ON dev09b_authority.control, dev09b_authority.approvals TO dev09b_authority_trial_service, dev09b_authority_trial_revoker;
GRANT UPDATE(last_time) ON dev09b_authority.control TO dev09b_authority_trial_service, dev09b_authority_trial_revoker;
GRANT UPDATE(state,session_json) ON dev09b_authority.approvals TO dev09b_authority_trial_service;
GRANT UPDATE(state,revoked) ON dev09b_authority.approvals TO dev09b_authority_trial_revoker;
GRANT INSERT ON dev09b_authority.nonces, dev09b_authority.events TO dev09b_authority_trial_service;
GRANT USAGE ON SEQUENCE dev09b_authority.events_sequence_seq TO dev09b_authority_trial_service;
GRANT SELECT ON dev09b_authority.control, dev09b_authority.nonces, dev09b_authority.events TO dev09b_authority_trial_observer;
GRANT SELECT(approval_id,attempt_id,state,revoked,session_json) ON dev09b_authority.approvals TO dev09b_authority_trial_observer;
-- Read cluster identity only, explicitly in this disposable authority cluster.
GRANT EXECUTE ON FUNCTION pg_catalog.pg_control_system() TO dev09b_authority_trial_service, dev09b_authority_trial_revoker, dev09b_authority_trial_observer;
INSERT INTO dev09b_authority.control(singleton,authority_epoch,revocation_epoch,continuity_token,blocked,last_time)
 VALUES(true,1,1,'00000000-0000-0000-0000-000000000384',false,0);
COMMIT;
