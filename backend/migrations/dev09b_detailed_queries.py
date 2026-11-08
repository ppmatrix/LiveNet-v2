"""Additional SELECT facts missing from the historical query contract; PG16 only.

No connection, execution, settings changes or privilege escalation. Parameters
are values, never identifiers. Selection is restricted to source-declared system
objects and named roles; no inventory of unrelated infrastructure.
"""
from types import MappingProxyType
from .dev09b_inspection_queries import Query,SCOPE

DETAIL_QUERIES=MappingProxyType({
 'environment':Query("""SELECT d.datname AS database,pg_catalog.pg_encoding_to_char(d.encoding) AS encoding,
 d.datcollate AS collation,d.datctype AS ctype,d.datlocprovider::text AS locale_provider,
 pg_catalog.pg_get_userbyid(d.datdba) AS owner FROM pg_catalog.pg_database d WHERE d.datname=pg_catalog.current_database()""",
 tuple('database encoding collation ctype locale_provider owner'.split()),1),
 'role_details':Query("""SELECT rolname AS name,rolcanlogin AS login,rolsuper AS superuser,rolcreatedb AS createdb,
 rolcreaterole AS createrole,rolreplication AS replication,rolbypassrls AS bypassrls,rolinherit AS inherit
 FROM pg_catalog.pg_roles WHERE rolname=ANY(CAST(:role_names AS text[]))""",
 tuple('name login superuser createdb createrole replication bypassrls inherit'.split())),
 'role_edges':Query("""SELECT a.rolname AS role,b.rolname AS member,m.admin_option AS admin,
 m.inherit_option AS inherit,m.set_option AS set FROM pg_catalog.pg_auth_members m
 JOIN pg_catalog.pg_roles a ON a.oid=m.roleid JOIN pg_catalog.pg_roles b ON b.oid=m.member
 WHERE a.rolname=ANY(CAST(:role_names AS text[])) OR b.rolname=ANY(CAST(:role_names AS text[]))""",
 tuple('role member admin inherit set'.split())),
 'relation_types':Query("""SELECT n.nspname AS schema,c.relname AS relation,c.oid::bigint AS relation_oid,
 t.oid::bigint AS type_oid,t.typname AS row_type,a.oid::bigint AS array_oid,a.typname AS array_type
 FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
 JOIN pg_catalog.pg_type t ON t.oid=c.reltype JOIN pg_catalog.pg_type a ON a.oid=t.typarray WHERE """+SCOPE,
 tuple('schema relation relation_oid type_oid row_type array_oid array_type'.split())),
 'routine_semantics':Query("""SELECT n.nspname AS schema,p.proname AS name,
 CASE WHEN n.nspname='pg_catalog' THEN pg_catalog.oidvectortypes(p.proargtypes) ELSE pg_catalog.pg_get_function_identity_arguments(p.oid) END AS arguments,
 pg_catalog.pg_get_function_result(p.oid) AS returns,l.lanname AS language,p.prosrc AS body,
 p.provolatile::text AS volatility,p.proisstrict AS strict,p.proparallel::text AS parallel,
 p.prosecdef AS security_definer,p.proconfig AS config,pg_catalog.pg_get_userbyid(p.proowner) AS owner
 FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace
 JOIN pg_catalog.pg_language l ON l.oid=p.prolang WHERE p.prokind='f' AND ("""+SCOPE+"""
 OR (n.nspname||'.'||p.proname)=ANY(CAST(:system_routines AS text[])))""",
 tuple('schema name arguments returns language body volatility strict parallel security_definer config owner'.split())),
 'trigger_semantics':Query("""SELECT n.nspname AS schema,c.relname AS relation,t.tgname AS name,
 CASE WHEN (t.tgtype::int & 2)<>0 THEN 'BEFORE' WHEN (t.tgtype::int & 64)<>0 THEN 'INSTEAD OF' ELSE 'AFTER' END AS timing,
 ARRAY_REMOVE(ARRAY[CASE WHEN (t.tgtype::int & 4)<>0 THEN 'INSERT' END,
 CASE WHEN (t.tgtype::int & 16)<>0 THEN 'UPDATE' END,CASE WHEN (t.tgtype::int & 8)<>0 THEN 'DELETE' END,
 CASE WHEN (t.tgtype::int & 32)<>0 THEN 'TRUNCATE' END],NULL) AS events,
 (t.tgtype::int & 1)<>0 AS row,pn.nspname AS function_schema,p.proname AS function_name,
 pg_catalog.pg_get_function_identity_arguments(p.oid) AS function_arguments,
 t.tgenabled::text AS enabled,t.tgisinternal AS internal
 FROM pg_catalog.pg_trigger t JOIN pg_catalog.pg_class c ON c.oid=t.tgrelid
 JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace JOIN pg_catalog.pg_proc p ON p.oid=t.tgfoid
 JOIN pg_catalog.pg_namespace pn ON pn.oid=p.pronamespace WHERE """+SCOPE,
 tuple('schema relation name timing events row function_schema function_name function_arguments enabled internal'.split())),
 'fk_trigger_links':Query("""SELECT n.nspname AS schema,c.relname AS relation,t.tgname AS name,
 cn.nspname AS constraint_schema,co.conname AS constraint_name,
 sn.nspname AS child_schema,src.relname AS child_relation,dn.nspname AS parent_schema,dst.relname AS parent_relation,
 t.tgdeferrable AS deferrable,t.tginitdeferred AS initially_deferred,
 co.confupdtype::text AS update_action,co.confdeltype::text AS delete_action,co.confmatchtype::text AS match,
 co.condeferrable AS constraint_deferrable,co.condeferred AS constraint_initially_deferred,
 co.convalidated AS validated,(t.tgconstrrelid=CASE WHEN t.tgrelid=co.conrelid THEN co.confrelid ELSE co.conrelid END) AS opposite_relation,
 (t.tgnargs=0 AND t.tgargs=''::pg_catalog.bytea) AS no_arguments,t.tgqual IS NULL AS no_condition,
 t.tgattr=''::pg_catalog.int2vector AS no_columns,
 (t.tgoldtable IS NULL AND t.tgnewtable IS NULL AND t.tgparentid=0) AS no_transition
 FROM pg_catalog.pg_trigger t JOIN pg_catalog.pg_class c ON c.oid=t.tgrelid
 JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
 JOIN pg_catalog.pg_constraint co ON co.oid=t.tgconstraint AND co.contype='f'
 JOIN pg_catalog.pg_namespace cn ON cn.oid=co.connamespace
 JOIN pg_catalog.pg_class src ON src.oid=co.conrelid JOIN pg_catalog.pg_namespace sn ON sn.oid=src.relnamespace
 JOIN pg_catalog.pg_class dst ON dst.oid=co.confrelid JOIN pg_catalog.pg_namespace dn ON dn.oid=dst.relnamespace
 WHERE t.tgisinternal AND """+SCOPE,
 tuple('schema relation name constraint_schema constraint_name child_schema child_relation parent_schema parent_relation deferrable initially_deferred update_action delete_action match constraint_deferrable constraint_initially_deferred validated opposite_relation no_arguments no_condition no_columns no_transition'.split())),
 'language_details':Query("""SELECT l.lanname AS name,l.lanpltrusted AS trusted,
 l.lanplcallfoid::regprocedure::text AS handler,l.laninline::regprocedure::text AS inline,
 l.lanvalidator::regprocedure::text AS validator,pg_catalog.pg_get_userbyid(l.lanowner) AS owner
 FROM pg_catalog.pg_language l WHERE l.lanname=ANY(CAST(:language_names AS text[]))""",
 tuple('name trusted handler inline validator owner'.split())),
 'toast_semantics':Query('SELECT n.nspname AS schema,p.relname AS relation,t.relname AS name,t.relkind::text AS kind,t.relpersistence::text AS persistence,pg_catalog.pg_get_userbyid(t.relowner) AS owner,t.reloptions AS options FROM pg_catalog.pg_class p JOIN pg_catalog.pg_namespace n ON n.oid=p.relnamespace JOIN pg_catalog.pg_class t ON t.oid=p.reltoastrelid OR t.oid IN (SELECT indexrelid FROM pg_catalog.pg_index WHERE indrelid=p.reltoastrelid) WHERE '+SCOPE,
 tuple('schema relation name kind persistence owner options'.split())),
 'system_acl':Query("""SELECT 'routine'::text AS family,n.nspname AS schema,p.proname AS name,CASE WHEN n.nspname='pg_catalog' THEN pg_catalog.oidvectortypes(p.proargtypes) ELSE pg_catalog.pg_get_function_identity_arguments(p.oid) END AS arguments,
 pg_catalog.pg_get_userbyid(p.proowner) AS owner,pg_catalog.pg_get_userbyid(x.grantor) AS grantor,
 CASE WHEN x.grantee=0 THEN 'PUBLIC' ELSE pg_catalog.pg_get_userbyid(x.grantee) END AS grantee,
 x.privilege_type AS privilege,x.is_grantable AS grant_option FROM pg_catalog.pg_proc p
 JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace CROSS JOIN LATERAL pg_catalog.aclexplode(COALESCE(p.proacl,pg_catalog.acldefault('f',p.proowner))) x
 WHERE (n.nspname||'.'||p.proname)=ANY(CAST(:system_routines AS text[]))
 UNION ALL SELECT 'language','',l.lanname,'',pg_catalog.pg_get_userbyid(l.lanowner),pg_catalog.pg_get_userbyid(x.grantor),
 CASE WHEN x.grantee=0 THEN 'PUBLIC' ELSE pg_catalog.pg_get_userbyid(x.grantee) END,x.privilege_type,x.is_grantable
 FROM pg_catalog.pg_language l CROSS JOIN LATERAL pg_catalog.aclexplode(COALESCE(l.lanacl,pg_catalog.acldefault('l',l.lanowner))) x
 WHERE l.lanname=ANY(CAST(:language_names AS text[]))""",
 tuple('family schema name arguments owner grantor grantee privilege grant_option'.split())),
 'reference_catalog':Query("""SELECT 'pg_namespace' AS catalog,n.oid::bigint AS oid,''::text AS schema,n.nspname AS name,n.nspname AS display FROM pg_catalog.pg_namespace n WHERE n.oid=ANY(CAST(:reference_pg_namespace AS oid[]))
 UNION ALL SELECT 'pg_type',t.oid::bigint,n.nspname,t.typname,pg_catalog.format_type(t.oid,NULL) FROM pg_catalog.pg_type t JOIN pg_catalog.pg_namespace n ON n.oid=t.typnamespace WHERE t.oid=ANY(CAST(:reference_pg_type AS oid[]))
 UNION ALL SELECT 'pg_opfamily',f.oid::bigint,n.nspname,f.opfname,n.nspname||'.'||f.opfname||' USING '||a.amname FROM pg_catalog.pg_opfamily f JOIN pg_catalog.pg_namespace n ON n.oid=f.opfnamespace JOIN pg_catalog.pg_am a ON a.oid=f.opfmethod WHERE f.oid=ANY(CAST(:reference_pg_opfamily AS oid[]))
 UNION ALL SELECT 'pg_operator',o.oid::bigint,n.nspname,o.oprname,o.oid::regoperator::text FROM pg_catalog.pg_operator o JOIN pg_catalog.pg_namespace n ON n.oid=o.oprnamespace WHERE o.oid=ANY(CAST(:reference_pg_operator AS oid[]))
 UNION ALL SELECT 'pg_roles',r.oid::bigint,'',r.rolname,r.rolname FROM pg_catalog.pg_roles r WHERE r.oid=ANY(CAST(:reference_pg_roles AS oid[]))
 UNION ALL SELECT 'pg_class',c.oid::bigint,n.nspname,c.relname,n.nspname||'.'||c.relname FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE c.oid=ANY(CAST(:reference_pg_class AS oid[]))
 UNION ALL SELECT 'pg_am',a.oid::bigint,'',a.amname,a.amname FROM pg_catalog.pg_am a WHERE a.oid=ANY(CAST(:reference_pg_am AS oid[]))
 UNION ALL SELECT 'pg_collation',c.oid::bigint,n.nspname,c.collname,n.nspname||'.'||c.collname FROM pg_catalog.pg_collation c JOIN pg_catalog.pg_namespace n ON n.oid=c.collnamespace WHERE c.oid=ANY(CAST(:reference_pg_collation AS oid[]))""",
 tuple('catalog oid schema name display'.split())),

})

# Match the historical registry's explicit builtin/type qualification policy.
import re as _re
DETAIL_QUERIES=MappingProxyType({name:Query(
    _re.sub(r'(?<![\w.])array_remove\(', 'pg_catalog.array_remove(',
            query.sql.replace('::regprocedure','::pg_catalog.regprocedure')
                     .replace('::text','::pg_catalog.text').replace('::bigint','::pg_catalog.int8')
                     .replace(' AS text[])',' AS pg_catalog.text[])').replace(' AS oid[])',' AS pg_catalog.oid[])')),
    query.fields,query.maximum) for name,query in DETAIL_QUERIES.items()})


def _identity_query(catalog,alias,joins,scope,family,schema,name,arguments="''",relation="''"):
    return "SELECT '"+family+"'::pg_catalog.text AS family,"+schema+" AS schema,"+name+" AS name,"+arguments+" AS arguments,"+relation+" AS relation,i.type AS identify_type,i.identity AS identify_identity,"+\
        "EXISTS(SELECT 1 FROM pg_catalog.pg_depend dep WHERE dep.classid='pg_catalog."+catalog+"'::pg_catalog.regclass AND dep.objid="+alias+".oid AND dep.objsubid=0 AND dep.refclassid='pg_catalog.pg_namespace'::pg_catalog.regclass) AS direct_namespace "+\
        'FROM pg_catalog.'+catalog+' '+alias+' '+joins+" CROSS JOIN LATERAL pg_catalog.pg_identify_object('pg_catalog."+catalog+"'::pg_catalog.regclass,"+alias+".oid,0) i WHERE "+scope


_identity_parts=[
 _identity_query('pg_proc','p','JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace',"("+SCOPE+" OR (n.nspname||'.'||p.proname)=ANY(CAST(:system_routines AS pg_catalog.text[])))",'routine','n.nspname','p.proname',"CASE WHEN n.nspname='pg_catalog' THEN pg_catalog.oidvectortypes(p.proargtypes) ELSE pg_catalog.pg_get_function_identity_arguments(p.oid) END"),
 _identity_query('pg_type','t','JOIN pg_catalog.pg_namespace n ON n.oid=t.typnamespace',SCOPE,'type','n.nspname','t.typname'),
 _identity_query('pg_class','c','JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace',SCOPE,'relation','n.nspname','c.relname'),
 _identity_query('pg_constraint','co','JOIN pg_catalog.pg_namespace n ON n.oid=co.connamespace JOIN pg_catalog.pg_class t ON t.oid=co.conrelid',SCOPE,'constraint','n.nspname','co.conname',relation='t.relname'),
 _identity_query('pg_trigger','tg','JOIN pg_catalog.pg_class t ON t.oid=tg.tgrelid JOIN pg_catalog.pg_namespace n ON n.oid=t.relnamespace',SCOPE,'trigger','n.nspname','tg.tgname',relation='t.relname'),
 _identity_query('pg_operator','o','JOIN pg_catalog.pg_namespace n ON n.oid=o.oprnamespace',SCOPE,'operator','n.nspname','o.oprname',"(CASE WHEN o.oprleft=0 THEN '' ELSE pg_catalog.format_type(o.oprleft,NULL) END)||','||(CASE WHEN o.oprright=0 THEN '' ELSE pg_catalog.format_type(o.oprright,NULL) END)"),
 _identity_query('pg_opclass','o','JOIN pg_catalog.pg_namespace n ON n.oid=o.opcnamespace',SCOPE,'opclass','n.nspname','o.opcname'),
 _identity_query('pg_opfamily','o','JOIN pg_catalog.pg_namespace n ON n.oid=o.opfnamespace',SCOPE,'opfamily','n.nspname','o.opfname'),
 _identity_query('pg_extension','e','JOIN pg_catalog.pg_namespace n ON n.oid=e.extnamespace','true','extension','n.nspname','e.extname'),
 _identity_query('pg_language','l','',"l.lanname=ANY(CAST(:language_names AS pg_catalog.text[]))",'language',"''",'l.lanname'),
]
DETAIL_QUERIES=MappingProxyType({**DETAIL_QUERIES,
 'object_identities':Query(' UNION ALL '.join(_identity_parts),tuple('family schema name arguments relation identify_type identify_identity direct_namespace'.split())),
 'casts':Query("SELECT sn.nspname AS source_schema,s.typname AS source_type,tn.nspname AS target_schema,t.typname AS target_type FROM pg_catalog.pg_cast c JOIN pg_catalog.pg_type s ON s.oid=c.castsource JOIN pg_catalog.pg_namespace sn ON sn.oid=s.typnamespace JOIN pg_catalog.pg_type t ON t.oid=c.casttarget JOIN pg_catalog.pg_namespace tn ON tn.oid=t.typnamespace WHERE sn.nspname IN ('inventory','audit','security','public') OR tn.nspname IN ('inventory','audit','security','public')",tuple('source_schema source_type target_schema target_type'.split())),
 # Preserve UNKNOWN as NULL when the view/current_setting access is unavailable;
 # do not attempt the known forbidden read, nor copy an administrative value.
 'own_preload_settings':Query("SELECT wanted.name,CASE WHEN pg_catalog.pg_has_role(current_user,'pg_read_all_settings','USAGE') THEN pg_catalog.current_setting(wanted.name,true) ELSE NULL END AS setting FROM (VALUES ('shared_preload_libraries'),('session_preload_libraries')) wanted(name)",('name','setting'),2),
})

DETAIL_QUERIES=MappingProxyType({**DETAIL_QUERIES,'helper_preload_settings':Query('SELECT backend_pid,name,setting FROM public.dev09b_own_preload_settings()',('backend_pid','name','setting'),2)})

# Dedicated-owner metadata is separate from the application role inventory.
# All values are observations; the fixed helper policy validates them before
# invoking SECURITY DEFINER. No pg_authid/password access is given to the probe.
DETAIL_QUERIES=MappingProxyType({**DETAIL_QUERIES,
 'helper_owner_role':Query("""SELECT rolname AS name,rolcanlogin AS login,rolsuper AS superuser,rolcreatedb AS createdb,
 rolcreaterole AS createrole,rolreplication AS replication,rolbypassrls AS bypassrls,rolinherit AS inherit,
 rolconnlimit AS connection_limit,rolvaliduntil::pg_catalog.text AS valid_until
 FROM pg_catalog.pg_roles WHERE rolname='dev09b_trial_settings_owner'""",tuple('name login superuser createdb createrole replication bypassrls inherit connection_limit valid_until'.split()),1),
 'helper_owner_edges':Query("""SELECT parent.rolname AS role,child.rolname AS member,grantor.rolname AS grantor,
 m.admin_option AS admin,m.inherit_option AS inherit,m.set_option AS set FROM pg_catalog.pg_auth_members m
 JOIN pg_catalog.pg_roles parent ON parent.oid=m.roleid JOIN pg_catalog.pg_roles child ON child.oid=m.member
 JOIN pg_catalog.pg_roles grantor ON grantor.oid=m.grantor
 WHERE parent.rolname='dev09b_trial_settings_owner' OR child.rolname='dev09b_trial_settings_owner'""",tuple('role member grantor admin inherit set'.split())),
 'helper_security_flags':Query("""SELECT
 pg_catalog.pg_has_role(p.oid,o.oid,'MEMBER') AS probe_owner_member,
 pg_catalog.pg_has_role(p.oid,s.oid,'MEMBER') AS probe_settings_member,
 EXISTS(SELECT 1 FROM pg_catalog.pg_auth_members WHERE member=p.oid) AS probe_any_memberships,
 pg_catalog.has_schema_privilege(p.oid,n.oid,'CREATE') AS probe_create_public,
 (p.oid=n.nspowner OR pg_catalog.pg_has_role(p.oid,n.nspowner,'MEMBER')) AS probe_owns_public,
 p.oid=d.datdba AS probe_database_owner,
 EXISTS(SELECT 1 FROM pg_catalog.pg_namespace ns WHERE pg_catalog.has_schema_privilege(o.oid,ns.oid,'CREATE')) AS owner_create_schema,
 pg_catalog.has_database_privilege(o.oid,d.oid,'CREATE') AS owner_database_create,
 pg_catalog.has_database_privilege(o.oid,d.oid,'TEMPORARY') AS owner_database_temporary,
 o.oid=d.datdba AS owner_database_owner,
 EXISTS(SELECT 1 FROM pg_catalog.pg_db_role_setting WHERE setrole=o.oid) AS owner_role_settings,
 pg_catalog.pg_has_role(o.oid,s.oid,'USAGE') AS owner_settings_usage,
 pg_catalog.pg_has_role(o.oid,s.oid,'SET') AS owner_settings_set,
 (s.rolcanlogin OR s.rolsuper OR s.rolcreatedb OR s.rolcreaterole OR s.rolreplication OR s.rolbypassrls
 OR EXISTS(SELECT 1 FROM pg_catalog.pg_auth_members WHERE member=s.oid)) AS settings_role_excess,
 EXISTS(SELECT 1 FROM pg_catalog.pg_shdepend dep WHERE dep.refclassid='pg_catalog.pg_authid'::pg_catalog.regclass
 AND dep.refobjid=o.oid AND dep.deptype IN ('o','a','r')
 AND NOT ((dep.classid='pg_catalog.pg_proc'::pg_catalog.regclass
 AND dep.objid=pg_catalog.to_regprocedure('public.dev09b_own_preload_settings()')::pg_catalog.oid AND dep.dbid=d.oid)
 OR (dep.classid='pg_catalog.pg_auth_members'::pg_catalog.regclass AND dep.objid IN
 (SELECT oid FROM pg_catalog.pg_auth_members WHERE member=o.oid AND roleid=s.oid)))) AS owner_extra_dependency
 FROM pg_catalog.pg_roles p CROSS JOIN pg_catalog.pg_roles o CROSS JOIN pg_catalog.pg_roles s
 CROSS JOIN pg_catalog.pg_namespace n CROSS JOIN pg_catalog.pg_database d
 WHERE p.rolname='dev09b_trial_probe' AND o.rolname='dev09b_trial_settings_owner'
 AND s.rolname='pg_read_all_settings' AND n.nspname='public' AND d.datname=pg_catalog.current_database()""",
 tuple('probe_owner_member probe_settings_member probe_any_memberships probe_create_public probe_owns_public probe_database_owner owner_create_schema owner_database_create owner_database_temporary owner_database_owner owner_role_settings owner_settings_usage owner_settings_set settings_role_excess owner_extra_dependency'.split()),1),
})
