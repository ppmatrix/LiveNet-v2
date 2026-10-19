\set ON_ERROR_STOP on

-- LiveNet v2 / F0.66C
-- Privilegios operacionais minimos para livenet_app.
-- Apenas para a instancia PostgreSQL isolada F0.66C.
-- EXECUCAO PROIBIDA sem autorizacao especifica.

BEGIN;

DO $$
DECLARE
    actual_tables integer;
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

    SELECT count(*)
    INTO actual_tables
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'inventory'
      AND c.relkind = 'r'
      AND c.relowner = 'livenet_migrator'::regrole;

    IF actual_tables <> 12 THEN
        RAISE EXCEPTION
            'F0.66C: expected 12 Inventory tables, found %',
            actual_tables;
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_class
        WHERE oid = 'audit.events'::regclass
          AND relowner = 'livenet_migrator'::regrole
    ) THEN
        RAISE EXCEPTION 'F0.66C: audit.events ownership mismatch';
    END IF;
END
$$;

GRANT USAGE ON SCHEMA inventory TO livenet_app;
GRANT USAGE ON SCHEMA audit TO livenet_app;

GRANT SELECT, INSERT, UPDATE, DELETE
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
TO livenet_app;

GRANT SELECT, INSERT
ON TABLE audit.events
TO livenet_app;

COMMIT;
