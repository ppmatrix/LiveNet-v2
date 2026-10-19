\set ON_ERROR_STOP on

-- LiveNet v2 / F0.66C
-- Rollback do provisionamento inicial de roles.
--
-- Executar exclusivamente atraves do executor Docker validado.
-- Aplicavel apenas antes da atribuicao de privilegios
-- ou transferencia de propriedade de objetos.

BEGIN;

DO $$
DECLARE
    role_name text;
BEGIN
    IF current_database() <> 'livenet_f0_test' THEN
        RAISE EXCEPTION
            'F0.66C rollback: database not authorized';
    END IF;

    FOREACH role_name IN ARRAY ARRAY[
        'livenet_app',
        'livenet_migrator'
    ]
    LOOP
        IF EXISTS (
            SELECT 1
            FROM pg_roles
            WHERE rolname = role_name
              AND (
                  rolcanlogin
                  OR rolsuper
                  OR rolcreatedb
                  OR rolcreaterole
                  OR rolreplication
                  OR rolbypassrls
              )
        ) THEN
            RAISE EXCEPTION
                'F0.66C rollback: unexpected attributes for %',
                role_name;
        END IF;

        IF EXISTS (
            SELECT 1
            FROM pg_auth_members m
            JOIN pg_roles r ON r.oid = m.member
            JOIN pg_roles p ON p.oid = m.roleid
            WHERE r.rolname = role_name
               OR p.rolname = role_name
        ) THEN
            RAISE EXCEPTION
                'F0.66C rollback: role % has memberships',
                role_name;
        END IF;
    END LOOP;
END
$$;

-- DROP ROLE verifica tambem dependencias e propriedade
-- de objetos em todo o cluster PostgreSQL.
-- Qualquer falha provoca rollback da transacao.

DROP ROLE IF EXISTS livenet_app;
DROP ROLE IF EXISTS livenet_migrator;

COMMIT;
