\set ON_ERROR_STOP on

BEGIN;

DO $$
DECLARE
    invalid_count integer;
BEGIN
    IF current_database() <> 'livenet_f0_test' THEN
        RAISE EXCEPTION 'F0.66C: unexpected database';
    END IF;

    SELECT count(*)
    INTO invalid_count
    FROM (
WITH expected(schema_name, function_name) AS (
    VALUES
        ('audit', 'prevent_event_mutation'),
        ('inventory', 'prevent_policy_version_mutation')
)
SELECT
    e.schema_name,
    e.function_name,
    p.oid,
    pg_get_userbyid(p.proowner) AS owner,
    EXISTS (
        SELECT 1
        FROM aclexplode(
            COALESCE(p.proacl, acldefault('f', p.proowner))
        ) a
        WHERE a.grantee = 0
          AND a.privilege_type = 'EXECUTE'
    ) AS public_execute
FROM expected e
LEFT JOIN pg_namespace n
    ON n.nspname = e.schema_name
LEFT JOIN pg_proc p
    ON p.pronamespace = n.oid
   AND p.proname = e.function_name
   AND p.pronargs = 0
) AS functions
    WHERE oid IS NULL
       OR owner IS DISTINCT FROM 'livenet_migrator'
       OR public_execute IS DISTINCT FROM true;

    IF invalid_count <> 0 THEN
        RAISE EXCEPTION
            'F0.66C: function ownership or initial ACL invalid (PUBLIC must initially have EXECUTE)';
    END IF;
END
$$;

REVOKE EXECUTE
ON FUNCTION audit.prevent_event_mutation()
FROM PUBLIC;

REVOKE EXECUTE
ON FUNCTION inventory.prevent_policy_version_mutation()
FROM PUBLIC;

DO $$
DECLARE
    invalid_count integer;
BEGIN
    SELECT count(*)
    INTO invalid_count
    FROM (
WITH expected(schema_name, function_name) AS (
    VALUES
        ('audit', 'prevent_event_mutation'),
        ('inventory', 'prevent_policy_version_mutation')
)
SELECT
    e.schema_name,
    e.function_name,
    p.oid,
    pg_get_userbyid(p.proowner) AS owner,
    EXISTS (
        SELECT 1
        FROM aclexplode(
            COALESCE(p.proacl, acldefault('f', p.proowner))
        ) a
        WHERE a.grantee = 0
          AND a.privilege_type = 'EXECUTE'
    ) AS public_execute
FROM expected e
LEFT JOIN pg_namespace n
    ON n.nspname = e.schema_name
LEFT JOIN pg_proc p
    ON p.pronamespace = n.oid
   AND p.proname = e.function_name
   AND p.pronargs = 0
) AS functions
    WHERE oid IS NULL
       OR owner IS DISTINCT FROM 'livenet_migrator'
       OR public_execute IS DISTINCT FROM false;

    IF invalid_count <> 0 THEN
        RAISE EXCEPTION
            'F0.66C: final function ACL contract violated';
    END IF;
END
$$;

COMMIT;
