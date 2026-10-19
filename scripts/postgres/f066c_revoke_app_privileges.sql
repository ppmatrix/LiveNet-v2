\set ON_ERROR_STOP on

-- LiveNet v2 / F0.66C
-- Reversao dos privilegios operacionais de livenet_app.
-- Apenas para a instancia PostgreSQL isolada F0.66C.
-- EXECUCAO PROIBIDA sem autorizacao especifica.

BEGIN;

DO $$
BEGIN
    IF current_database() <> 'livenet_f0_test' THEN
        RAISE EXCEPTION 'F0.66C: database not authorized';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_roles
        WHERE rolname = 'livenet_app'
          AND NOT rolcanlogin
          AND NOT rolsuper
          AND NOT rolcreatedb
          AND NOT rolcreaterole
          AND NOT rolreplication
          AND NOT rolbypassrls
    ) THEN
        RAISE EXCEPTION 'F0.66C: application role invalid';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_namespace
        WHERE nspname = 'inventory'
          AND nspowner = 'livenet_migrator'::regrole
    ) OR NOT EXISTS (
        SELECT 1
        FROM pg_namespace
        WHERE nspname = 'audit'
          AND nspowner = 'livenet_migrator'::regrole
    ) THEN
        RAISE EXCEPTION 'F0.66C: application schema ownership mismatch';
    END IF;
END
$$;

REVOKE SELECT, INSERT, UPDATE, DELETE
ON TABLE
    inventory.resources,
    inventory.resource_identifiers,
    inventory.resource_relations,
    inventory.groups,
    inventory.group_memberships,
    inventory.group_rules,
    inventory.tags,
    inventory.resource_tags,
    inventory.policies,
    inventory.policy_versions,
    inventory.policy_assignments,
    inventory.effective_configs
FROM livenet_app;

REVOKE SELECT, INSERT
ON TABLE audit.events
FROM livenet_app;

REVOKE USAGE ON SCHEMA inventory FROM livenet_app;
REVOKE USAGE ON SCHEMA audit FROM livenet_app;

COMMIT;
