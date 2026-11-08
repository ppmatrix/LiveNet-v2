-- Authorized one-time querytrial installation only; not a migration/profile approval.
-- Dedicated NOLOGIN owner, exactly pg_read_all_settings; no temporary CREATE.
BEGIN;
SET LOCAL statement_timeout='5s';
SET LOCAL lock_timeout='1s';
SET LOCAL search_path=pg_catalog;
DO $guard$
DECLARE probe_oid oid; owner_oid oid; settings_oid oid; public_oid oid;
BEGIN
  IF pg_catalog.current_database()<>'livenet_v2_dev' OR current_user<>'dev09b_trial_admin'
     OR (SELECT system_identifier::pg_catalog.text FROM pg_catalog.pg_control_system())<>'7705421224394444834'
  THEN RAISE EXCEPTION 'WRONG_SETTINGS_TRIAL_TARGET'; END IF;
  SELECT oid INTO STRICT probe_oid FROM pg_catalog.pg_roles WHERE rolname='dev09b_trial_probe';
  SELECT oid INTO STRICT settings_oid FROM pg_catalog.pg_roles WHERE rolname='pg_read_all_settings';
  SELECT oid INTO STRICT public_oid FROM pg_catalog.pg_namespace WHERE nspname='public';
  IF EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE oid=probe_oid AND
      (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls))
     OR EXISTS (SELECT 1 FROM pg_catalog.pg_auth_members WHERE member=probe_oid)
     OR pg_catalog.has_schema_privilege(probe_oid,public_oid,'CREATE')
     OR pg_catalog.has_database_privilege(probe_oid,pg_catalog.current_database(),'CREATE')
     OR pg_catalog.has_database_privilege(probe_oid,pg_catalog.current_database(),'TEMPORARY')
     OR EXISTS (SELECT 1 FROM pg_catalog.pg_database WHERE datname=pg_catalog.current_database() AND datdba=probe_oid)
     OR pg_catalog.pg_has_role(probe_oid,(SELECT nspowner FROM pg_catalog.pg_namespace WHERE oid=public_oid),'MEMBER')
     OR pg_catalog.pg_has_role(probe_oid,settings_oid,'MEMBER')
  THEN RAISE EXCEPTION 'PROBE_POWER_DIVERGENCE'; END IF;
  IF EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE oid=settings_oid AND
      (rolcanlogin OR rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls))
     OR EXISTS (SELECT 1 FROM pg_catalog.pg_auth_members WHERE member=settings_oid)
  THEN RAISE EXCEPTION 'SETTINGS_ROLE_DIVERGENCE'; END IF;
  -- Refuse any preexisting same-name overload; never replace an existing object.
  IF EXISTS (SELECT 1 FROM pg_catalog.pg_proc WHERE pronamespace=public_oid AND proname='dev09b_own_preload_settings')
  THEN RAISE EXCEPTION 'SETTINGS_HELPER_PREEXISTS'; END IF;
  SELECT oid INTO owner_oid FROM pg_catalog.pg_roles WHERE rolname='dev09b_trial_settings_owner';
  IF owner_oid IS NOT NULL THEN
    IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_authid WHERE oid=owner_oid
        AND NOT rolcanlogin AND NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole
        AND NOT rolreplication AND NOT rolbypassrls AND NOT rolinherit
        AND rolconnlimit=0 AND rolpassword IS NULL AND rolvaliduntil IS NULL
        AND NOT EXISTS (SELECT 1 FROM pg_catalog.pg_db_role_setting WHERE setrole=owner_oid))
       OR (SELECT count(*) FROM pg_catalog.pg_auth_members WHERE member=owner_oid OR roleid=owner_oid)<>1
       OR NOT EXISTS (SELECT 1 FROM pg_catalog.pg_auth_members WHERE member=owner_oid AND roleid=settings_oid
          AND NOT admin_option AND inherit_option AND NOT set_option
          AND grantor=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user))
    THEN RAISE EXCEPTION 'SETTINGS_OWNER_PREEXISTS_INCOMPATIBLE'; END IF;
  ELSE
    CREATE ROLE dev09b_trial_settings_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
      NOREPLICATION NOBYPASSRLS NOINHERIT CONNECTION LIMIT 0;
    GRANT pg_read_all_settings TO dev09b_trial_settings_owner WITH ADMIN FALSE, INHERIT TRUE, SET FALSE;
    SELECT oid INTO STRICT owner_oid FROM pg_catalog.pg_roles WHERE rolname='dev09b_trial_settings_owner';
  END IF;
  IF pg_catalog.pg_has_role(probe_oid,owner_oid,'MEMBER')
     OR EXISTS (SELECT 1 FROM pg_catalog.pg_auth_members WHERE roleid=owner_oid)
     OR EXISTS (SELECT 1 FROM pg_catalog.pg_shdepend WHERE refclassid='pg_catalog.pg_authid'::pg_catalog.regclass
         AND refobjid=owner_oid AND deptype IN ('o','a','r')
         AND NOT (classid='pg_catalog.pg_auth_members'::pg_catalog.regclass AND objid IN
           (SELECT oid FROM pg_catalog.pg_auth_members WHERE member=owner_oid AND roleid=settings_oid)))
     OR EXISTS (SELECT 1 FROM pg_catalog.pg_namespace WHERE pg_catalog.has_schema_privilege(owner_oid,oid,'CREATE'))
     OR pg_catalog.has_database_privilege(owner_oid,pg_catalog.current_database(),'CREATE')
     OR pg_catalog.has_database_privilege(owner_oid,pg_catalog.current_database(),'TEMPORARY')
     OR NOT pg_catalog.pg_has_role(owner_oid,settings_oid,'USAGE')
     OR pg_catalog.pg_has_role(owner_oid,settings_oid,'SET')
  THEN RAISE EXCEPTION 'SETTINGS_OWNER_POWER_DIVERGENCE'; END IF;
END
$guard$;
CREATE FUNCTION public.dev09b_own_preload_settings()
RETURNS TABLE(backend_pid pg_catalog.int4,name pg_catalog.text,setting pg_catalog.text)
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path=pg_catalog
AS $body$
  SELECT pg_catalog.pg_backend_pid(),wanted.name,pg_catalog.current_setting(wanted.name)
  FROM (VALUES ('shared_preload_libraries'::pg_catalog.text),('session_preload_libraries'::pg_catalog.text)) wanted(name)
$body$;
REVOKE ALL ON FUNCTION public.dev09b_own_preload_settings() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.dev09b_own_preload_settings() TO dev09b_trial_probe;
ALTER FUNCTION public.dev09b_own_preload_settings() OWNER TO dev09b_trial_settings_owner;
DO $verify$
DECLARE owner_oid oid; probe_oid oid; settings_oid oid; function_oid oid;
BEGIN
  SELECT oid INTO STRICT owner_oid FROM pg_catalog.pg_roles WHERE rolname='dev09b_trial_settings_owner';
  SELECT oid INTO STRICT probe_oid FROM pg_catalog.pg_roles WHERE rolname='dev09b_trial_probe';
  SELECT oid INTO STRICT settings_oid FROM pg_catalog.pg_roles WHERE rolname='pg_read_all_settings';
  SELECT 'public.dev09b_own_preload_settings()'::pg_catalog.regprocedure::oid INTO function_oid;
  IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_authid WHERE oid=owner_oid
      AND NOT rolcanlogin AND NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole
      AND NOT rolreplication AND NOT rolbypassrls AND NOT rolinherit AND rolconnlimit=0
      AND rolpassword IS NULL AND rolvaliduntil IS NULL
        AND NOT EXISTS (SELECT 1 FROM pg_catalog.pg_db_role_setting WHERE setrole=owner_oid))
     OR (SELECT count(*) FROM pg_catalog.pg_auth_members WHERE member=owner_oid OR roleid=owner_oid)<>1
     OR NOT EXISTS (SELECT 1 FROM pg_catalog.pg_auth_members WHERE member=owner_oid AND roleid=settings_oid
        AND NOT admin_option AND inherit_option AND NOT set_option
        AND grantor=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user))
     OR EXISTS (SELECT 1 FROM pg_catalog.pg_auth_members WHERE member=probe_oid)
     OR pg_catalog.pg_has_role(probe_oid,owner_oid,'MEMBER')
     OR pg_catalog.pg_has_role(probe_oid,settings_oid,'MEMBER')
     OR NOT pg_catalog.pg_has_role(owner_oid,settings_oid,'USAGE')
     OR pg_catalog.pg_has_role(owner_oid,settings_oid,'SET')
     OR EXISTS (SELECT 1 FROM pg_catalog.pg_namespace WHERE pg_catalog.has_schema_privilege(owner_oid,oid,'CREATE'))
     OR pg_catalog.has_schema_privilege(probe_oid,'public','CREATE')
     OR pg_catalog.has_database_privilege(owner_oid,pg_catalog.current_database(),'CREATE')
     OR pg_catalog.has_database_privilege(owner_oid,pg_catalog.current_database(),'TEMPORARY')
     OR NOT EXISTS (SELECT 1 FROM pg_catalog.pg_proc WHERE oid=function_oid AND proowner=owner_oid
         AND prosecdef AND pronargs=0 AND proconfig=ARRAY['search_path=pg_catalog'])
     OR EXISTS (SELECT 1 FROM pg_catalog.pg_shdepend WHERE refclassid='pg_catalog.pg_authid'::pg_catalog.regclass
         AND refobjid=owner_oid AND deptype IN ('o','a','r')
         AND NOT ((classid='pg_catalog.pg_proc'::pg_catalog.regclass AND objid=function_oid
             AND dbid=(SELECT oid FROM pg_catalog.pg_database WHERE datname=pg_catalog.current_database()))
           OR (classid='pg_catalog.pg_auth_members'::pg_catalog.regclass AND objid IN
             (SELECT oid FROM pg_catalog.pg_auth_members WHERE member=owner_oid AND roleid=settings_oid))))
  THEN RAISE EXCEPTION 'SETTINGS_OWNER_FINAL_DIVERGENCE'; END IF;
  IF EXISTS (SELECT 1 FROM pg_catalog.pg_proc p CROSS JOIN LATERAL pg_catalog.aclexplode(p.proacl) a
      WHERE p.oid=function_oid AND (a.grantor<>owner_oid OR a.grantee NOT IN (owner_oid,probe_oid)
          OR a.privilege_type<>'EXECUTE' OR a.is_grantable))
     OR (SELECT count(*) FROM pg_catalog.pg_proc p CROSS JOIN LATERAL pg_catalog.aclexplode(p.proacl) a
         WHERE p.oid=function_oid AND a.grantee=probe_oid AND a.privilege_type='EXECUTE')<>1
     OR NOT pg_catalog.has_function_privilege(probe_oid,function_oid,'EXECUTE')
  THEN RAISE EXCEPTION 'SETTINGS_HELPER_ACL_DIVERGENCE'; END IF;
END
$verify$;
COMMIT;
