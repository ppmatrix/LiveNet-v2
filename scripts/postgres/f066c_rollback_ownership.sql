\set ON_ERROR_STOP on

-- LiveNet v2 / F0.66C
-- Reversao controlada da transferencia de propriedade.
-- EXECUCAO PROIBIDA sem autorizacao especifica.
-- Apenas na instancia PostgreSQL isolada F0.66C.

BEGIN;

DO $$
DECLARE
    table_count integer;
    function_count integer;
    schema_count integer;
BEGIN
    IF current_database() <> 'livenet_f0_test' THEN
        RAISE EXCEPTION 'F0.66C rollback: database not authorized';
    END IF;

    SELECT count(*) INTO schema_count
    FROM pg_namespace
    WHERE nspname IN ('inventory', 'audit')
      AND pg_get_userbyid(nspowner) = 'livenet_migrator';

    IF schema_count <> 2 THEN
        RAISE EXCEPTION 'F0.66C rollback: schema ownership mismatch';
    END IF;

    SELECT count(*) INTO table_count
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE (
        (n.nspname IN ('inventory', 'audit') AND c.relkind IN ('r', 'p'))
        OR (n.nspname = 'public' AND c.relname = 'alembic_version'
            AND c.relkind IN ('r', 'p'))
    )
      AND pg_get_userbyid(c.relowner) = 'livenet_migrator';

    IF table_count <> 14 THEN
        RAISE EXCEPTION 'F0.66C rollback: table ownership mismatch';
    END IF;

    SELECT count(*) INTO function_count
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname IN ('inventory', 'audit')
      AND pg_get_userbyid(p.proowner) = 'livenet_migrator';

    IF function_count <> 2 THEN
        RAISE EXCEPTION 'F0.66C rollback: function ownership mismatch';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_namespace
        WHERE nspname = 'inventory'
          AND nspowner = 'livenet_migrator'::regrole
    ) THEN
        RAISE EXCEPTION 'F0.66C: unexpected schema owner: inventory';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_namespace
        WHERE nspname = 'audit'
          AND nspowner = 'livenet_migrator'::regrole
    ) THEN
        RAISE EXCEPTION 'F0.66C: unexpected schema owner: audit';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_class
        WHERE oid = to_regclass('inventory.resources')
          AND relkind = 'r'
          AND relowner = 'livenet_migrator'::regrole
    ) THEN
        RAISE EXCEPTION 'F0.66C: unexpected table owner: inventory.resources';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_class
        WHERE oid = to_regclass('inventory.resource_identifiers')
          AND relkind = 'r'
          AND relowner = 'livenet_migrator'::regrole
    ) THEN
        RAISE EXCEPTION 'F0.66C: unexpected table owner: inventory.resource_identifiers';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_class
        WHERE oid = to_regclass('inventory.resource_relations')
          AND relkind = 'r'
          AND relowner = 'livenet_migrator'::regrole
    ) THEN
        RAISE EXCEPTION 'F0.66C: unexpected table owner: inventory.resource_relations';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_class
        WHERE oid = to_regclass('inventory.groups')
          AND relkind = 'r'
          AND relowner = 'livenet_migrator'::regrole
    ) THEN
        RAISE EXCEPTION 'F0.66C: unexpected table owner: inventory.groups';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_class
        WHERE oid = to_regclass('inventory.group_memberships')
          AND relkind = 'r'
          AND relowner = 'livenet_migrator'::regrole
    ) THEN
        RAISE EXCEPTION 'F0.66C: unexpected table owner: inventory.group_memberships';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_class
        WHERE oid = to_regclass('inventory.group_rules')
          AND relkind = 'r'
          AND relowner = 'livenet_migrator'::regrole
    ) THEN
        RAISE EXCEPTION 'F0.66C: unexpected table owner: inventory.group_rules';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_class
        WHERE oid = to_regclass('inventory.tags')
          AND relkind = 'r'
          AND relowner = 'livenet_migrator'::regrole
    ) THEN
        RAISE EXCEPTION 'F0.66C: unexpected table owner: inventory.tags';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_class
        WHERE oid = to_regclass('inventory.resource_tags')
          AND relkind = 'r'
          AND relowner = 'livenet_migrator'::regrole
    ) THEN
        RAISE EXCEPTION 'F0.66C: unexpected table owner: inventory.resource_tags';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_class
        WHERE oid = to_regclass('inventory.policies')
          AND relkind = 'r'
          AND relowner = 'livenet_migrator'::regrole
    ) THEN
        RAISE EXCEPTION 'F0.66C: unexpected table owner: inventory.policies';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_class
        WHERE oid = to_regclass('inventory.policy_versions')
          AND relkind = 'r'
          AND relowner = 'livenet_migrator'::regrole
    ) THEN
        RAISE EXCEPTION 'F0.66C: unexpected table owner: inventory.policy_versions';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_class
        WHERE oid = to_regclass('inventory.policy_assignments')
          AND relkind = 'r'
          AND relowner = 'livenet_migrator'::regrole
    ) THEN
        RAISE EXCEPTION 'F0.66C: unexpected table owner: inventory.policy_assignments';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_class
        WHERE oid = to_regclass('inventory.effective_configs')
          AND relkind = 'r'
          AND relowner = 'livenet_migrator'::regrole
    ) THEN
        RAISE EXCEPTION 'F0.66C: unexpected table owner: inventory.effective_configs';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_class
        WHERE oid = to_regclass('audit.events')
          AND relkind = 'r'
          AND relowner = 'livenet_migrator'::regrole
    ) THEN
        RAISE EXCEPTION 'F0.66C: unexpected table owner: audit.events';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_class
        WHERE oid = to_regclass('public.alembic_version')
          AND relkind = 'r'
          AND relowner = 'livenet_migrator'::regrole
    ) THEN
        RAISE EXCEPTION 'F0.66C: unexpected table owner: public.alembic_version';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_proc
        WHERE oid = to_regprocedure('audit.prevent_event_mutation()')
          AND proowner = 'livenet_migrator'::regrole
    ) THEN
        RAISE EXCEPTION 'F0.66C: unexpected function owner: audit.prevent_event_mutation()';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_proc
        WHERE oid = to_regprocedure('inventory.prevent_policy_version_mutation()')
          AND proowner = 'livenet_migrator'::regrole
    ) THEN
        RAISE EXCEPTION 'F0.66C: unexpected function owner: inventory.prevent_policy_version_mutation()';
    END IF;

END
$$;

-- Tabelas Inventory
ALTER TABLE inventory.resources OWNER TO livenet;
ALTER TABLE inventory.resource_identifiers OWNER TO livenet;
ALTER TABLE inventory.resource_relations OWNER TO livenet;
ALTER TABLE inventory.groups OWNER TO livenet;
ALTER TABLE inventory.group_memberships OWNER TO livenet;
ALTER TABLE inventory.group_rules OWNER TO livenet;
ALTER TABLE inventory.tags OWNER TO livenet;
ALTER TABLE inventory.resource_tags OWNER TO livenet;
ALTER TABLE inventory.policies OWNER TO livenet;
ALTER TABLE inventory.policy_versions OWNER TO livenet;
ALTER TABLE inventory.policy_assignments OWNER TO livenet;
ALTER TABLE inventory.effective_configs OWNER TO livenet;

-- Audit e Alembic
ALTER TABLE audit.events OWNER TO livenet;
ALTER TABLE public.alembic_version OWNER TO livenet;

-- Funcoes aplicacionais
ALTER FUNCTION audit.prevent_event_mutation() OWNER TO livenet;
ALTER FUNCTION inventory.prevent_policy_version_mutation() OWNER TO livenet;

-- Esquemas aplicacionais
ALTER SCHEMA inventory OWNER TO livenet;
ALTER SCHEMA audit OWNER TO livenet;

COMMIT;
