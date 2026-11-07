-- PROPOSAL ONLY: next disposable query trial, not an operational DEV09B profile.
-- Do not execute without explicit authorization. No migrations/runtime grants.
-- Administrative channel: existing dev09b_trial_admin on the SAME disposable.
-- Required psql input: -v confirmed_system_identifier=7705421224394444834
-- Version 1.7 read from btree_gist.control in the pinned, STOPPED PG16 image:
-- postgres@sha256:f4610795587492cd4fb887c2dc3de301b813278bb6f616992061141b5f15ac36
-- Proposed new role names/ACL below still require approval before execution.
\set ON_ERROR_STOP on
\if :{?confirmed_system_identifier}
\else
\quit 3
\endif
SELECT (pg_catalog.current_database()='livenet_v2_dev'
    AND current_user='dev09b_trial_admin'
    AND system_identifier::pg_catalog.text=:'confirmed_system_identifier'
    AND EXISTS (SELECT 1 FROM pg_catalog.pg_available_extension_versions
                WHERE name='btree_gist' AND version='1.7')
    AND NOT EXISTS (SELECT 1 FROM pg_catalog.pg_extension WHERE extname<>'plpgsql')
    AND NOT EXISTS (SELECT 1 FROM pg_catalog.pg_namespace
                    WHERE pg_catalog.substr(nspname,1,3)<>'pg_'
                      AND nspname NOT IN ('public','information_schema'))
    AND NOT EXISTS (SELECT 1 FROM pg_catalog.pg_depend d
                    JOIN pg_catalog.pg_namespace n ON n.oid=d.refobjid
                    WHERE d.refclassid='pg_catalog.pg_namespace'::pg_catalog.regclass
                      AND n.nspname='public')) AS correct_empty_target
FROM pg_catalog.pg_control_system() \gset
\if :correct_empty_target
\else
\quit 3
\endif
BEGIN;
SET LOCAL search_path=pg_catalog;
SET LOCAL statement_timeout='10s';
SET LOCAL lock_timeout='500ms';
CREATE ROLE dev09b_trial_inventory_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS;
CREATE ROLE dev09b_trial_audit_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS;
CREATE ROLE dev09b_trial_security_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS;
CREATE SCHEMA inventory AUTHORIZATION dev09b_trial_inventory_owner;
CREATE SCHEMA audit AUTHORIZATION dev09b_trial_audit_owner;
CREATE SCHEMA security AUTHORIZATION dev09b_trial_security_owner;
REVOKE ALL ON SCHEMA inventory,audit,security FROM PUBLIC,dev09b_trial_probe;
-- public ownership is unchanged. Existing probe CONNECT/pg_control_system remain.
CREATE EXTENSION btree_gist WITH SCHEMA public VERSION '1.7';
-- Extension owner: separate bootstrap administration, not any future migrator.
-- No ACL exists ON EXTENSION itself: restrict the ACL-bearing members instead.
DO $acl$
DECLARE o record;
BEGIN
  FOR o IN SELECT p.oid FROM pg_catalog.pg_depend d
    JOIN pg_catalog.pg_extension e ON e.oid=d.refobjid
    JOIN pg_catalog.pg_proc p ON p.oid=d.objid
    WHERE d.refclassid='pg_catalog.pg_extension'::pg_catalog.regclass
      AND d.classid='pg_catalog.pg_proc'::pg_catalog.regclass
      AND d.deptype='e' AND e.extname='btree_gist'
  LOOP
    EXECUTE pg_catalog.format('REVOKE ALL ON FUNCTION %s FROM PUBLIC,dev09b_trial_probe',o.oid::pg_catalog.regprocedure);
  END LOOP;
  -- Only direct extension members; do not ALTER automatic array-type ACLs.
  FOR o IN SELECT t.oid FROM pg_catalog.pg_depend d
    JOIN pg_catalog.pg_extension e ON e.oid=d.refobjid
    JOIN pg_catalog.pg_type t ON t.oid=d.objid
    WHERE d.refclassid='pg_catalog.pg_extension'::pg_catalog.regclass
      AND d.classid='pg_catalog.pg_type'::pg_catalog.regclass
      AND d.deptype='e' AND e.extname='btree_gist'
  LOOP
    EXECUTE pg_catalog.format('REVOKE ALL ON TYPE %s FROM PUBLIC,dev09b_trial_probe',o.oid::pg_catalog.regtype);
  END LOOP;
END
$acl$;
-- ACL scope is this initial inspection checkpoint, not a permanent prohibition.
-- The extension owner (dev09b_trial_admin) retains ownership/grant authority.
-- Later, ONLY after a distinct authorization and phase ACL expectation change:
--   GRANT USAGE ON SCHEMA public TO <authorized_role>;
--   GRANT USAGE ON TYPE <exact_qualified_extension_type> TO <authorized_role>;
--   GRANT EXECUTE ON FUNCTION <exact_qualified_signature> TO <authorized_role>;
-- These are documentation templates, NOT executed statements in this script.
-- PostgreSQL has no GRANT ON OPERATOR CLASS / OPERATOR FAMILY. Their future use
-- must be checked with explicit schema/type/function privileges as applicable,
-- and CREATE only in the authorized managed schema, never CREATE on the database.
-- Do not restore PUBLIC privileges, grant ALL FUNCTIONS/TYPES IN SCHEMA, or add
-- membership/ownership of the extension as a shortcut. Index support functions
-- called internally do not imply a blanket requirement for EXECUTE on every
-- extension routine: determine the signatures needed by the actual operation.
-- The owner-only assertions below apply only now; this bootstrap is not rerun
-- after approved phase-specific grants (nor does it install a recurring guard).
DO $verify$
BEGIN
  IF EXISTS (
    SELECT 1 FROM (VALUES
      ('inventory','dev09b_trial_inventory_owner'),('audit','dev09b_trial_audit_owner'),
      ('security','dev09b_trial_security_owner')) expected(schema_name,owner_name)
    LEFT JOIN pg_catalog.pg_namespace n ON n.nspname=expected.schema_name
    LEFT JOIN pg_catalog.pg_roles r ON r.oid=n.nspowner
    WHERE r.rolname IS DISTINCT FROM expected.owner_name OR r.rolcanlogin
      OR r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication OR r.rolbypassrls OR r.rolinherit
  ) THEN RAISE EXCEPTION 'OWNER_PROFILE_DIVERGENCE'; END IF;
  IF EXISTS (
    SELECT 1 FROM pg_catalog.pg_auth_members m JOIN pg_catalog.pg_roles r
    ON r.oid=m.roleid OR r.oid=m.member
    WHERE r.rolname IN ('dev09b_trial_inventory_owner','dev09b_trial_audit_owner','dev09b_trial_security_owner')
  ) THEN RAISE EXCEPTION 'OWNER_MEMBERSHIP_DIVERGENCE'; END IF;
  IF EXISTS (
    SELECT 1 FROM pg_catalog.pg_namespace n
    CROSS JOIN LATERAL pg_catalog.aclexplode(COALESCE(n.nspacl,pg_catalog.acldefault('n',n.nspowner))) a
    WHERE n.nspname IN ('inventory','audit','security') AND a.grantee<>n.nspowner
  ) THEN RAISE EXCEPTION 'SCHEMA_ACL_DIVERGENCE'; END IF;
  IF EXISTS (
    SELECT 1 FROM pg_catalog.pg_depend d JOIN pg_catalog.pg_namespace n ON n.oid=d.refobjid
    WHERE d.refclassid='pg_catalog.pg_namespace'::pg_catalog.regclass
      AND n.nspname IN ('inventory','audit','security')
  ) THEN RAISE EXCEPTION 'MANAGED_SCHEMA_NOT_EMPTY'; END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_catalog.pg_extension e JOIN pg_catalog.pg_namespace n ON n.oid=e.extnamespace
    WHERE e.extname='btree_gist' AND e.extversion='1.7' AND n.nspname='public'
      AND pg_catalog.pg_get_userbyid(e.extowner)='dev09b_trial_admin'
  ) THEN RAISE EXCEPTION 'EXTENSION_DIVERGENCE'; END IF;
  IF EXISTS (
    SELECT 1 FROM pg_catalog.pg_depend d JOIN pg_catalog.pg_extension e ON e.oid=d.refobjid
    JOIN pg_catalog.pg_proc p ON p.oid=d.objid
    CROSS JOIN LATERAL pg_catalog.aclexplode(COALESCE(p.proacl,pg_catalog.acldefault('f',p.proowner))) a
    WHERE d.refclassid='pg_catalog.pg_extension'::pg_catalog.regclass
      AND d.classid='pg_catalog.pg_proc'::pg_catalog.regclass AND d.deptype='e'
      AND e.extname='btree_gist' AND a.grantee<>p.proowner
  ) OR EXISTS (
    SELECT 1 FROM pg_catalog.pg_depend d JOIN pg_catalog.pg_extension e ON e.oid=d.refobjid
    JOIN pg_catalog.pg_type t ON t.oid=d.objid
    CROSS JOIN LATERAL pg_catalog.aclexplode(COALESCE(t.typacl,pg_catalog.acldefault('T',t.typowner))) a
    WHERE d.refclassid='pg_catalog.pg_extension'::pg_catalog.regclass
      AND d.classid='pg_catalog.pg_type'::pg_catalog.regclass AND d.deptype='e'
      AND e.extname='btree_gist' AND a.grantee<>t.typowner
  ) THEN RAISE EXCEPTION 'EXTENSION_MEMBER_ACL_DIVERGENCE'; END IF;
  IF pg_catalog.has_database_privilege('dev09b_trial_probe',pg_catalog.current_database(),'CREATE')
     OR pg_catalog.has_database_privilege('dev09b_trial_probe',pg_catalog.current_database(),'TEMPORARY')
     OR EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname='dev09b_trial_probe'
                AND (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls))
  THEN RAISE EXCEPTION 'PROBE_POWER_DIVERGENCE'; END IF;
END
$verify$;
COMMIT;
-- After commit: reconfirm SID independently, run a new read-only trial/report,
-- compare ownership/expanded ACLs/membership and extension members. Positive
-- catalog data is not yet a complete physical-profile or migration proof.
