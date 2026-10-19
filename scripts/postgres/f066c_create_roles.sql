\set ON_ERROR_STOP on

-- LiveNet v2 / F0.66C
-- Provisionamento inicial de roles.
-- Executar apenas na instancia PostgreSQL isolada F0.66C.
--
-- PRECONDICOES:
-- 1. Ligacao a livenet_f0_test.
-- 2. Instancia validada pelo executor Docker F0.66C.
-- 3. Execucao administrativa autorizada.
--
-- Este script NAO concede privilegios nem altera proprietarios.

BEGIN;

DO $$
BEGIN
    IF current_database() <> 'livenet_f0_test' THEN
        RAISE EXCEPTION
            'F0.66C: database not authorized';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_roles
        WHERE rolname IN ('livenet_app', 'livenet_migrator')
    ) THEN
        RAISE EXCEPTION
            'F0.66C: target roles already exist';
    END IF;
END
$$;

CREATE ROLE livenet_migrator
    NOLOGIN
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOREPLICATION
    NOBYPASSRLS
    NOINHERIT;

CREATE ROLE livenet_app
    NOLOGIN
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOREPLICATION
    NOBYPASSRLS
    NOINHERIT;

COMMIT;
