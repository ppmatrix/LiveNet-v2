\set ON_ERROR_STOP on

-- LiveNet v2 / F0.66C
-- Transferencia controlada de propriedade.
-- EXECUCAO PROIBIDA sem autorizacao especifica.
-- Apenas na instancia PostgreSQL isolada F0.66C.

BEGIN;

DO $$
DECLARE
    actual_tables integer;
    actual_functions integer;
    actual_schemas integer;
    actual_alembic integer;
BEGIN
    IF current_database() <> 'livenet_f0_test' THEN
        RAISE EXCEPTION 'F0.66C: database not authorized';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_roles
        WHERE rolname = 'livenet_migrator'
          AND NOT rolcanlogin
          AND NOT rolsuper
    ) THEN
        RAISE EXCEPTION 'F0.66C: migrator role invalid';
    END IF;

    SELECT count(*)
    INTO actual_schemas
    FROM pg_namespace
    WHERE nspname IN ('inventory', 'audit')
      AND pg_get_userbyid(nspowner) = 'livenet';

    IF actual_schemas <> 2 THEN
        RAISE EXCEPTION
            'F0.66C: expected 2 schemas owned by livenet, found %',
            actual_schemas;
    END IF;

    SELECT count(*)
    INTO actual_alembic
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public'
      AND c.relname = 'alembic_version'
      AND c.relkind = 'r'
      AND pg_get_userbyid(c.relowner) = 'livenet';

    IF actual_alembic <> 1 THEN
        RAISE EXCEPTION
            'F0.66C: alembic_version ownership mismatch';
    END IF;

    SELECT count(*)
    INTO actual_tables
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname IN ('inventory', 'audit')
      AND c.relkind IN ('r', 'p')
      AND pg_get_userbyid(c.relowner) = 'livenet';

    IF actual_tables <> 13 THEN
        RAISE EXCEPTION
            'F0.66C: expected 13 application tables, found %',
            actual_tables;
    END IF;

    SELECT count(*)
    INTO actual_functions
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname IN ('inventory', 'audit')
      AND pg_get_userbyid(p.proowner) = 'livenet';

    IF actual_functions <> 2 THEN
        RAISE EXCEPTION
            'F0.66C: expected 2 application functions, found %',
            actual_functions;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_namespace
        WHERE nspname = 'inventory'
          AND nspowner = 'livenet'::regrole
    ) THEN
        RAISE EXCEPTION 'F0.66C: unexpected schema owner: inventory';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_namespace
        WHERE nspname = 'audit'
          AND nspowner = 'livenet'::regrole
    ) THEN
        RAISE EXCEPTION 'F0.66C: unexpected schema owner: audit';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_class
        WHERE oid = to_regclass('inventory.resources')
          AND relkind = 'r'
          AND relowner = 'livenet'::regrole
    ) THEN
        RAISE EXCEPTION 'F0.66C: unexpected table owner: inventory.resources';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_class
        WHERE oid = to_regclass('inventory.resource_identifiers')
          AND relkind = 'r'
          AND relowner = 'livenet'::regrole
    ) THEN
        RAISE EXCEPTION 'F0.66C: unexpected table owner: inventory.resource_identifiers';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_class
        WHERE oid = to_regclass('inventory.resource_relations')
          AND relkind = 'r'
          AND relowner = 'livenet'::regrole
    ) THEN
        RAISE EXCEPTION 'F0.66C: unexpected table owner: inventory.resource_relations';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_class
        WHERE oid = to_regclass('inventory.groups')
          AND relkind = 'r'
          AND relowner = 'livenet'::regrole
    ) THEN
        RAISE EXCEPTION 'F0.66C: unexpected table owner: inventory.groups';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_class
        WHERE oid = to_regclass('inventory.group_memberships')
          AND relkind = 'r'
          AND relowner = 'livenet'::regrole
    ) THEN
        RAISE EXCEPTION 'F0.66C: unexpected table owner: inventory.group_memberships';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_class
        WHERE oid = to_regclass('inventory.group_rules')
          AND relkind = 'r'
          AND relowner = 'livenet'::regrole
    ) THEN
        RAISE EXCEPTION 'F0.66C: unexpected table owner: inventory.group_rules';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_class
        WHERE oid = to_regclass('inventory.tags')
          AND relkind = 'r'
          AND relowner = 'livenet'::regrole
    ) THEN
        RAISE EXCEPTION 'F0.66C: unexpected table owner: inventory.tags';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_class
        WHERE oid = to_regclass('inventory.resource_tags')
          AND relkind = 'r'
          AND relowner = 'livenet'::regrole
    ) THEN
        RAISE EXCEPTION 'F0.66C: unexpected table owner: inventory.resource_tags';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_class
        WHERE oid = to_regclass('inventory.policies')
          AND relkind = 'r'
          AND relowner = 'livenet'::regrole
    ) THEN
        RAISE EXCEPTION 'F0.66C: unexpected table owner: inventory.policies';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_class
        WHERE oid = to_regclass('inventory.policy_versions')
          AND relkind = 'r'
          AND relowner = 'livenet'::regrole
    ) THEN
        RAISE EXCEPTION 'F0.66C: unexpected table owner: inventory.policy_versions';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_class
        WHERE oid = to_regclass('inventory.policy_assignments')
          AND relkind = 'r'
          AND relowner = 'livenet'::regrole
    ) THEN
        RAISE EXCEPTION 'F0.66C: unexpected table owner: inventory.policy_assignments';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_class
        WHERE oid = to_regclass('inventory.effective_configs')
          AND relkind = 'r'
          AND relowner = 'livenet'::regrole
    ) THEN
        RAISE EXCEPTION 'F0.66C: unexpected table owner: inventory.effective_configs';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_class
        WHERE oid = to_regclass('audit.events')
          AND relkind = 'r'
          AND relowner = 'livenet'::regrole
    ) THEN
        RAISE EXCEPTION 'F0.66C: unexpected table owner: audit.events';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_class
        WHERE oid = to_regclass('public.alembic_version')
          AND relkind = 'r'
          AND relowner = 'livenet'::regrole
    ) THEN
        RAISE EXCEPTION 'F0.66C: unexpected table owner: public.alembic_version';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_proc
        WHERE oid = to_regprocedure('audit.prevent_event_mutation()')
          AND proowner = 'livenet'::regrole
    ) THEN
        RAISE EXCEPTION 'F0.66C: unexpected function owner: audit.prevent_event_mutation()';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_proc
        WHERE oid = to_regprocedure('inventory.prevent_policy_version_mutation()')
          AND proowner = 'livenet'::regrole
    ) THEN
        RAISE EXCEPTION 'F0.66C: unexpected function owner: inventory.prevent_policy_version_mutation()';
    END IF;

END
$$;

-- Esquemas aplicacionais
ALTER SCHEMA inventory OWNER TO livenet_migrator;
ALTER SCHEMA audit OWNER TO livenet_migrator;

-- Inventory
ALTER TABLE inventory.resources OWNER TO livenet_migrator;
ALTER TABLE inventory.resource_identifiers OWNER TO livenet_migrator;
ALTER TABLE inventory.resource_relations OWNER TO livenet_migrator;
ALTER TABLE inventory.groups OWNER TO livenet_migrator;
ALTER TABLE inventory.group_memberships OWNER TO livenet_migrator;
ALTER TABLE inventory.group_rules OWNER TO livenet_migrator;
ALTER TABLE inventory.tags OWNER TO livenet_migrator;
ALTER TABLE inventory.resource_tags OWNER TO livenet_migrator;
ALTER TABLE inventory.policies OWNER TO livenet_migrator;
ALTER TABLE inventory.policy_versions OWNER TO livenet_migrator;
ALTER TABLE inventory.policy_assignments OWNER TO livenet_migrator;
ALTER TABLE inventory.effective_configs OWNER TO livenet_migrator;

-- Audit
ALTER TABLE audit.events OWNER TO livenet_migrator;

-- Alembic
ALTER TABLE public.alembic_version OWNER TO livenet_migrator;

-- Funcoes aplicacionais
ALTER FUNCTION audit.prevent_event_mutation()
    OWNER TO livenet_migrator;

ALTER FUNCTION inventory.prevent_policy_version_mutation()
    OWNER TO livenet_migrator;

COMMIT;
