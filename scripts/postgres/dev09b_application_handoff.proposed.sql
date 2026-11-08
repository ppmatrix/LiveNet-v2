-- PROPOSAL ONLY; requires confirmed PERSISTED outcome and separate admin authorization.
-- Same external exclusive window; no migration/COMMIT or authority bypass.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL search_path=pg_catalog;
SET LOCAL lock_timeout='1s';
DO $guard$ BEGIN
 IF current_database()<>'livenet_v2_dev' OR current_user<>'dev09b_trial_admin'
 OR (SELECT system_identifier::text FROM pg_catalog.pg_control_system())<>'7705421224394444834'
 THEN RAISE EXCEPTION 'DEV09B_TARGET_DIVERGENCE'; END IF;
 IF EXISTS(SELECT 1 FROM pg_catalog.pg_stat_activity WHERE usename='dev09b_trial_migrator')
 THEN RAISE EXCEPTION 'DEV09B_MIGRATOR_SESSION_STILL_OPEN'; END IF;
 IF (SELECT pg_catalog.array_agg(version_num ORDER BY version_num) FROM public.alembic_version)
 IS DISTINCT FROM ARRAY['f066a01a7230']::varchar[]
 THEN RAISE EXCEPTION 'DEV09B_PERSISTED_REVISION_DIVERGENCE'; END IF;
END $guard$;
ALTER TABLE inventory.resources OWNER TO dev09b_trial_inventory_owner;
ALTER TABLE inventory.resource_identifiers OWNER TO dev09b_trial_inventory_owner;
ALTER TABLE inventory.resource_relations OWNER TO dev09b_trial_inventory_owner;
ALTER TABLE inventory.groups OWNER TO dev09b_trial_inventory_owner;
ALTER TABLE inventory.group_memberships OWNER TO dev09b_trial_inventory_owner;
ALTER TABLE inventory.group_rules OWNER TO dev09b_trial_inventory_owner;
ALTER TABLE inventory.tags OWNER TO dev09b_trial_inventory_owner;
ALTER TABLE inventory.resource_tags OWNER TO dev09b_trial_inventory_owner;
ALTER TABLE inventory.policies OWNER TO dev09b_trial_inventory_owner;
ALTER TABLE inventory.policy_versions OWNER TO dev09b_trial_inventory_owner;
ALTER TABLE inventory.policy_assignments OWNER TO dev09b_trial_inventory_owner;
ALTER TABLE inventory.effective_configs OWNER TO dev09b_trial_inventory_owner;
ALTER TABLE audit.events OWNER TO dev09b_trial_audit_owner;
ALTER FUNCTION inventory.prevent_policy_version_mutation() OWNER TO dev09b_trial_inventory_owner;
ALTER FUNCTION audit.prevent_event_mutation() OWNER TO dev09b_trial_audit_owner;
ALTER TABLE public.alembic_version OWNER TO dev09b_trial_application_ledger_owner;
GRANT USAGE ON SCHEMA inventory,audit TO dev09b_trial_probe;
GRANT SELECT(id) ON TABLE inventory.resources TO dev09b_trial_probe;
GRANT SELECT(id) ON TABLE inventory.resource_identifiers TO dev09b_trial_probe;
GRANT SELECT(id) ON TABLE inventory.resource_relations TO dev09b_trial_probe;
GRANT SELECT(id) ON TABLE inventory.groups TO dev09b_trial_probe;
GRANT SELECT(id) ON TABLE inventory.group_memberships TO dev09b_trial_probe;
GRANT SELECT(id) ON TABLE inventory.group_rules TO dev09b_trial_probe;
GRANT SELECT(id) ON TABLE inventory.tags TO dev09b_trial_probe;
GRANT SELECT(id) ON TABLE inventory.resource_tags TO dev09b_trial_probe;
GRANT SELECT(id) ON TABLE inventory.policies TO dev09b_trial_probe;
GRANT SELECT(id) ON TABLE inventory.policy_versions TO dev09b_trial_probe;
GRANT SELECT(id) ON TABLE inventory.policy_assignments TO dev09b_trial_probe;
GRANT SELECT(id) ON TABLE inventory.effective_configs TO dev09b_trial_probe;
GRANT SELECT(id) ON TABLE audit.events TO dev09b_trial_probe;
GRANT SELECT(version_num) ON TABLE public.alembic_version TO dev09b_trial_probe;
COMMIT;
-- ALTER TABLE ownership covers its dependent row/array types, indexes and TOAST.
-- Temporary powers must already be revoked by dev09b_application_close.proposed.sql.
-- These SELECT/USAGE grants are the existing CLOSED inspection rights, not runtime rights.
-- Verify ALL owners/ACLs independently against CLOSED before releasing exclusivity.
-- No runtime grants; do not use DROP OWNED or substitute broad REASSIGN OWNED.
