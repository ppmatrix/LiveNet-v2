\set ON_ERROR_STOP on

-- LiveNet v2 / F0.66C
-- Preflight exclusivamente de leitura.
-- Execucao autorizada apenas em livenet_f0_test.

DO $$
BEGIN
    IF current_database() <> 'livenet_f0_test' THEN
        RAISE EXCEPTION
            'F0.66C preflight restricted to livenet_f0_test';
    END IF;
END
$$;

SELECT
    current_database() AS database_name,
    current_user AS connected_user;

-- Identidades envolvidas na separacao de privilegios.
SELECT
    expected.role_name,
    COALESCE(r.rolcanlogin, false) AS exists_with_login,
    COALESCE(r.rolsuper, false) AS is_superuser,
    COALESCE(r.rolcreaterole, false) AS can_create_roles,
    r.oid IS NOT NULL AS role_exists
FROM (
    VALUES
        ('livenet'),
        ('livenet_app'),
        ('livenet_migrator')
) AS expected(role_name)
LEFT JOIN pg_roles r ON r.rolname = expected.role_name
ORDER BY expected.role_name;

-- Proprietarios dos esquemas.
SELECT
    nspname AS schema_name,
    pg_get_userbyid(nspowner) AS owner
FROM pg_namespace
WHERE nspname IN ('public', 'inventory', 'audit')
ORDER BY nspname;

-- Tabelas e sequencias aplicacionais.
SELECT
    n.nspname AS schema_name,
    c.relname AS object_name,
    c.relkind AS object_type,
    pg_get_userbyid(c.relowner) AS owner
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE (
        n.nspname IN ('inventory', 'audit')
        OR (
            n.nspname = 'public'
            AND c.relname = 'alembic_version'
        )
    )
    AND c.relkind IN ('r', 'p', 'S', 'v', 'm')
ORDER BY n.nspname, c.relname;

-- Funcoes proprias da aplicacao.
-- Exclui explicitamente membros de extensoes.
SELECT
    n.nspname AS schema_name,
    p.proname AS function_name,
    pg_get_userbyid(p.proowner) AS owner,
    p.prosecdef AS security_definer
FROM pg_proc p
JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname IN ('inventory', 'audit')
  AND NOT EXISTS (
      SELECT 1
      FROM pg_depend d
      WHERE d.classid = 'pg_proc'::regclass
        AND d.objid = p.oid
        AND d.deptype = 'e'
  )
ORDER BY n.nspname, p.proname;

-- Extensoes instaladas.
SELECT
    extname,
    extversion
FROM pg_extension
ORDER BY extname;

-- Privilegios predefinidos explicitos.
SELECT
    pg_get_userbyid(d.defaclrole) AS role_name,
    COALESCE(n.nspname, '(global)') AS schema_name,
    d.defaclobjtype AS object_type,
    d.defaclacl AS privileges
FROM pg_default_acl d
LEFT JOIN pg_namespace n ON n.oid = d.defaclnamespace
ORDER BY role_name, schema_name;
