"""Fixed PG16 SELECTs for PREPARED checkpoints; never executed on import.

Independent of G2's final-state policy. Names/values are bound, never SQL input.
Each query is completely drained; bounds are refusal thresholds, not LIMITs.
"""
from dataclasses import dataclass
from types import MappingProxyType
from .dev09b_inspection_support import SETTINGS_NAMES


@dataclass(frozen=True)
class Query:
    sql: str
    fields: tuple
    maximum: int = 65536


def query(expressions, fields, source='', maximum=65536):
    return Query('SELECT ' + expressions + ' ' + source, tuple(fields.split()), maximum)


SCOPE = "n.nspname IN ('inventory','audit','security','public')"
_sql = {}
_sql['identity'] = query("""current_database() AS database, current_user AS current_user,
 session_user AS session_user, s.system_identifier::text AS system_identifier,
 pg_backend_pid() AS pid, a.backend_start::text AS backend_start, a.xact_start::text AS xact_start,
 l.virtualxid::text AS virtualxid, host(inet_server_addr()) AS address, inet_server_port() AS port,
 current_setting('server_version_num')::integer AS server_version_num""",
 'database current_user session_user system_identifier pid backend_start xact_start virtualxid address port server_version_num',
 """FROM pg_catalog.pg_control_system() s CROSS JOIN pg_catalog.pg_stat_activity a
 CROSS JOIN pg_catalog.pg_locks l WHERE a.pid=pg_backend_pid() AND l.pid=a.pid
 AND l.locktype='virtualxid' AND l.granted""", 1)
_sql['privileges'] = query("""r.rolsuper AS superuser,r.rolcreatedb AS createdb,r.rolcreaterole AS createrole,
 r.rolreplication AS replication,r.rolbypassrls AS bypassrls,
 d.datdba=r.oid AS database_owner,
 has_database_privilege(r.oid,d.oid,'CREATE') AS database_create,
 has_database_privilege(r.oid,d.oid,'TEMPORARY') AS database_temporary""",
 'superuser createdb createrole replication bypassrls database_owner database_create database_temporary',
 'FROM pg_catalog.pg_roles r CROSS JOIN pg_catalog.pg_database d WHERE r.rolname=current_user AND d.datname=current_database()', 1)
_sql['memberships'] = query("""r.rolname AS role,pg_has_role(current_user,r.oid,'MEMBER') AS member,
 pg_has_role(current_user,r.oid,'USAGE') AS inherited,pg_has_role(current_user,r.oid,'SET') AS can_set""",
 'role member inherited can_set', 'FROM pg_catalog.pg_roles r WHERE r.rolname<>current_user')
_sql['schemas'] = query("""n.nspname AS name,r.rolname AS owner,r.rolcanlogin AS owner_login,
 has_schema_privilege(current_user,n.oid,'CREATE') AS can_create,
 has_schema_privilege(current_user,n.oid,'USAGE') AS can_use,
 has_schema_privilege(current_user,n.oid,'CREATE WITH GRANT OPTION') AS grant_create,
 has_schema_privilege(current_user,n.oid,'USAGE WITH GRANT OPTION') AS grant_use""",
 'name owner owner_login can_create can_use grant_create grant_use',
 'FROM pg_catalog.pg_namespace n JOIN pg_catalog.pg_roles r ON r.oid=n.nspowner')
_sql['schema_acl'] = query("""n.nspname AS name,pg_get_userbyid(x.grantor) AS grantor,
 CASE WHEN x.grantee=0 THEN 'PUBLIC' ELSE pg_get_userbyid(x.grantee) END AS grantee,
 x.privilege_type AS privilege,x.is_grantable AS grant_option""", 'name grantor grantee privilege grant_option',
 "FROM pg_catalog.pg_namespace n CROSS JOIN LATERAL pg_catalog.aclexplode(COALESCE(n.nspacl,pg_catalog.acldefault('n',n.nspowner))) x WHERE " + SCOPE)
_sql['extension'] = query('e.extname AS name,e.extversion AS version,n.nspname AS schema,pg_get_userbyid(e.extowner) AS owner',
 'name version schema owner', 'FROM pg_catalog.pg_extension e JOIN pg_catalog.pg_namespace n ON n.oid=e.extnamespace', 256)
_sql['extension_members'] = query("""e.extname AS extension,i.type AS type,i.schema AS schema,
 i.name AS name,i.identity AS identity,d.objsubid AS subid""", 'extension type schema name identity subid',
 """FROM pg_catalog.pg_depend d JOIN pg_catalog.pg_extension e ON e.oid=d.refobjid
 CROSS JOIN LATERAL pg_catalog.pg_identify_object(d.classid,d.objid,d.objsubid) i
 WHERE d.refclassid='pg_catalog.pg_extension'::regclass AND d.deptype='e'""")
# Dependency census captures namespace objects beyond the supported migration
# families too. An extra operator/type/view/etc cannot disappear through filtering.
_sql['namespace_objects'] = query('n.nspname AS schema,i.type AS type,i.identity AS identity',
 'schema type identity', """FROM pg_catalog.pg_depend d JOIN pg_catalog.pg_namespace n ON n.oid=d.refobjid
 CROSS JOIN LATERAL pg_catalog.pg_identify_object(d.classid,d.objid,d.objsubid) i
 WHERE d.refclassid='pg_catalog.pg_namespace'::regclass AND """ + SCOPE)
_sql['relations'] = query("""n.nspname AS schema,c.relname AS name,c.relkind::text AS kind,
 pg_get_userbyid(c.relowner) AS owner,c.relpersistence::text AS persistence,
 c.relrowsecurity AS row_security,c.relforcerowsecurity AS force_row_security,
 c.reloptions AS options,pg_get_expr(c.relpartbound,c.oid) AS partition_bound,
 CASE WHEN c.relkind IN ('v','m') THEN pg_get_viewdef(c.oid,false) ELSE NULL END AS view""",
 'schema name kind owner persistence row_security force_row_security options partition_bound view',
 'FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE ' + SCOPE)
_sql['columns'] = query("""n.nspname AS schema,c.relname AS relation,a.attname AS name,a.attnum::integer AS position,
 format_type(a.atttypid,a.atttypmod) AS type,a.attnotnull AS not_null,a.attidentity::text AS identity,
 a.attgenerated::text AS generated,pg_get_expr(d.adbin,d.adrelid) AS default""",
 'schema relation name position type not_null identity generated default', """FROM pg_catalog.pg_attribute a
 JOIN pg_catalog.pg_class c ON c.oid=a.attrelid JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
 LEFT JOIN pg_catalog.pg_attrdef d ON d.adrelid=c.oid AND d.adnum=a.attnum
 WHERE a.attnum>0 AND NOT a.attisdropped AND """ + SCOPE)
_sql['constraints'] = query("""n.nspname AS schema,c.conname AS name,c.conrelid::regclass::text AS relation,
 c.contype::text AS kind,c.convalidated AS validated,c.condeferrable AS deferrable,
 c.condeferred AS initially_deferred,pg_get_constraintdef(c.oid,false) AS definition""",
 'schema name relation kind validated deferrable initially_deferred definition',
 'FROM pg_catalog.pg_constraint c JOIN pg_catalog.pg_namespace n ON n.oid=c.connamespace WHERE ' + SCOPE)
_sql['indexes'] = query("""n.nspname AS schema,c.relname AS name,pg_get_indexdef(i.indexrelid) AS definition,
 i.indisvalid AS valid,i.indisready AS ready,i.indislive AS live""", 'schema name definition valid ready live',
 'FROM pg_catalog.pg_index i JOIN pg_catalog.pg_class c ON c.oid=i.indexrelid JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE ' + SCOPE)
_sql['routines'] = query("""n.nspname AS schema,p.proname AS name,pg_get_function_identity_arguments(p.oid) AS arguments,
 p.prokind::text AS kind,pg_get_userbyid(p.proowner) AS owner,p.prosecdef AS security_definer,
 p.proconfig AS config,CASE WHEN p.prokind IN ('f','p') THEN pg_get_functiondef(p.oid) ELSE NULL END AS definition""",
 'schema name arguments kind owner security_definer config definition',
 'FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace WHERE ' + SCOPE)
_sql['triggers'] = query("""n.nspname AS schema,c.relname AS relation,t.tgname AS name,t.tgenabled::text AS enabled,
 t.tgisinternal AS internal,pg_get_triggerdef(t.oid,false) AS definition""", 'schema relation name enabled internal definition',
 'FROM pg_catalog.pg_trigger t JOIN pg_catalog.pg_class c ON c.oid=t.tgrelid JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE ' + SCOPE)
_sql['types'] = query("""n.nspname AS schema,t.typname AS name,pg_get_userbyid(t.typowner) AS owner,
 t.typtype::text AS kind,t.typcategory::text AS category,t.typnotnull AS not_null,t.typdefault AS default,
 format_type(t.typbasetype,t.typtypmod) AS base,format_type(t.typelem,NULL) AS element""",
 'schema name owner kind category not_null default base element',
 'FROM pg_catalog.pg_type t JOIN pg_catalog.pg_namespace n ON n.oid=t.typnamespace WHERE ' + SCOPE)
_sql['policies'] = query("""n.nspname AS schema,c.relname AS relation,p.polname AS name,p.polcmd::text AS command,
 p.polpermissive AS permissive,p.polroles::text AS roles,pg_get_expr(p.polqual,c.oid) AS using,
 pg_get_expr(p.polwithcheck,c.oid) AS check""", 'schema relation name command permissive roles using check',
 'FROM pg_catalog.pg_policy p JOIN pg_catalog.pg_class c ON c.oid=p.polrelid JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE ' + SCOPE)
_sql['rules'] = query('n.nspname AS schema,c.relname AS relation,r.rulename AS name,pg_get_ruledef(r.oid,false) AS definition',
 'schema relation name definition', 'FROM pg_catalog.pg_rewrite r JOIN pg_catalog.pg_class c ON c.oid=r.ev_class JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE ' + SCOPE)
# Expanded grants, including PUBLIC and grant options; ownership kept separate.
parts = []
for family, source, key, owner, acl, kind in (
 ('relation', 'pg_catalog.pg_class o', 'o.relname', 'o.relowner', 'o.relacl', "CASE WHEN o.relkind='S' THEN 's'::\"char\" ELSE 'r'::\"char\" END"),
 ('routine', 'pg_catalog.pg_proc o', 'o.proname || pg_get_function_identity_arguments(o.oid)', 'o.proowner', 'o.proacl', "'f'"),
 ('type', 'pg_catalog.pg_type o', 'o.typname', 'o.typowner', 'o.typacl', "'T'")):
 ns = {'relation':'relnamespace','routine':'pronamespace','type':'typnamespace'}[family]
 parts.append(f"SELECT '{family}' AS family,n.nspname AS schema,{key} AS name,pg_get_userbyid(x.grantor) AS grantor,CASE WHEN x.grantee=0 THEN 'PUBLIC' ELSE pg_get_userbyid(x.grantee) END AS grantee,x.privilege_type AS privilege,x.is_grantable AS grant_option FROM {source} JOIN pg_catalog.pg_namespace n ON n.oid=o.{ns} CROSS JOIN LATERAL pg_catalog.aclexplode(COALESCE({acl},pg_catalog.acldefault({kind},{owner}))) x WHERE {SCOPE}")
_sql['object_acl'] = Query(' UNION ALL '.join(parts), tuple('family schema name grantor grantee privilege grant_option'.split()))
_sql['default_acl'] = query("""pg_get_userbyid(a.defaclrole) AS owner,n.nspname AS schema,a.defaclobjtype::text AS kind,
 pg_get_userbyid(x.grantor) AS grantor,CASE WHEN x.grantee=0 THEN 'PUBLIC' ELSE pg_get_userbyid(x.grantee) END AS grantee,
 x.privilege_type AS privilege,x.is_grantable AS grant_option""", 'owner schema kind grantor grantee privilege grant_option',
 'FROM pg_catalog.pg_default_acl a LEFT JOIN pg_catalog.pg_namespace n ON n.oid=a.defaclnamespace CROSS JOIN LATERAL pg_catalog.aclexplode(a.defaclacl) x')
# pg_settings omits superuser-only rows for the probe. Preserve their names
# with NULL values (not COALESCE to ''). PG16 lc_collate/lc_ctype are database
# attributes, absent from its GUC table; read their actual catalog values.
_wanted_settings = ','.join("('"+name+"')" for name in SETTINGS_NAMES)
_sql['settings'] = Query("SELECT wanted.name, CASE wanted.name "
    "WHEN 'lc_collate' THEN db.datcollate WHEN 'lc_ctype' THEN db.datctype "
    "ELSE s.setting END AS setting FROM (VALUES "+_wanted_settings+") AS wanted(name) "
    "CROSS JOIN pg_catalog.pg_database db LEFT JOIN pg_catalog.pg_settings s ON s.name=wanted.name "
    "WHERE db.datname=pg_catalog.current_database()", ('name','setting'), 32)
LEDGER_SQL = MappingProxyType({
 'application': 'SELECT version_num FROM public.alembic_version',
 'security': 'SELECT version_num FROM public.alembic_security_version',
})

# Additional derived objects; these cannot be reduced to relation names alone.
_sql['sequences'] = query('n.nspname AS schema,c.relname AS name,s.seqstart::text AS start,s.seqincrement::text AS increment,s.seqmax::text AS maximum,s.seqmin::text AS minimum,s.seqcache::text AS cache,s.seqcycle AS cycle',
 'schema name start increment maximum minimum cache cycle', 'FROM pg_catalog.pg_sequence s JOIN pg_catalog.pg_class c ON c.oid=s.seqrelid JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE ' + SCOPE)
_sql['inheritance'] = query('i.inhrelid::regclass::text AS child,i.inhparent::regclass::text AS parent,i.inhseqno AS position',
 'child parent position', 'FROM pg_catalog.pg_inherits i JOIN pg_catalog.pg_class c ON c.oid=i.inhrelid JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE ' + SCOPE)
_sql['extension_properties'] = query("""e.extname AS extension,i.identity AS identity,d.classid::regclass::text AS catalog,
 CASE d.classid WHEN 'pg_catalog.pg_operator'::regclass THEN (SELECT to_jsonb(o)-'oid' FROM pg_catalog.pg_operator o WHERE o.oid=d.objid)
 WHEN 'pg_catalog.pg_opclass'::regclass THEN (SELECT to_jsonb(o)-'oid' FROM pg_catalog.pg_opclass o WHERE o.oid=d.objid)
 WHEN 'pg_catalog.pg_opfamily'::regclass THEN (SELECT to_jsonb(o)-'oid' FROM pg_catalog.pg_opfamily o WHERE o.oid=d.objid)
 ELSE NULL END AS properties""", 'extension identity catalog properties',
 """FROM pg_catalog.pg_depend d JOIN pg_catalog.pg_extension e ON e.oid=d.refobjid
 CROSS JOIN LATERAL pg_catalog.pg_identify_object(d.classid,d.objid,d.objsubid) i
 WHERE d.refclassid='pg_catalog.pg_extension'::regclass AND d.deptype='e'""")
_sql['operator_members'] = query("""n.nspname AS schema,f.opfname AS family,'operator' AS kind,to_jsonb(m)-'oid' AS properties""",
 'schema family kind properties', 'FROM pg_catalog.pg_amop m JOIN pg_catalog.pg_opfamily f ON f.oid=m.amopfamily JOIN pg_catalog.pg_namespace n ON n.oid=f.opfnamespace WHERE ' + SCOPE)
_sql['operator_members'] = Query(_sql['operator_members'].sql + " UNION ALL SELECT n.nspname AS schema,f.opfname AS family,'function' AS kind,to_jsonb(m)-'oid' AS properties FROM pg_catalog.pg_amproc m JOIN pg_catalog.pg_opfamily f ON f.oid=m.amprocfamily JOIN pg_catalog.pg_namespace n ON n.oid=f.opfnamespace WHERE " + SCOPE, _sql['operator_members'].fields)
_sql['column_acl'] = query("""n.nspname AS schema,c.relname AS relation,a.attname AS name,
 pg_get_userbyid(x.grantor) AS grantor,CASE WHEN x.grantee=0 THEN 'PUBLIC' ELSE pg_get_userbyid(x.grantee) END AS grantee,
 x.privilege_type AS privilege,x.is_grantable AS grant_option""", 'schema relation name grantor grantee privilege grant_option',
 'FROM pg_catalog.pg_attribute a JOIN pg_catalog.pg_class c ON c.oid=a.attrelid JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace CROSS JOIN LATERAL pg_catalog.aclexplode(a.attacl) x WHERE a.attnum>0 AND NOT a.attisdropped AND ' + SCOPE)
# Effective execution of privileged wrappers is an additional installation path.
_sql['executable_definers'] = query('n.nspname AS schema,p.proname AS name,pg_get_function_identity_arguments(p.oid) AS arguments,pg_get_userbyid(p.proowner) AS owner,pg_get_functiondef(p.oid) AS definition',
 'schema name arguments owner definition', "FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace WHERE p.prosecdef AND p.prokind IN ('f','p') AND has_function_privilege(current_user,p.oid,'EXECUTE')")
_ext_acl = []
for _family, _catalog, _owner, _acl, _typ in (('routine','pg_proc','proowner','proacl','f'),('type','pg_type','typowner','typacl','T'),('relation','pg_class','relowner','relacl','r')):
    _ext_acl.append(f"SELECT e.extname AS extension,i.identity AS identity,pg_get_userbyid(x.grantor) AS grantor,CASE WHEN x.grantee=0 THEN 'PUBLIC' ELSE pg_get_userbyid(x.grantee) END AS grantee,x.privilege_type AS privilege,x.is_grantable AS grant_option FROM pg_catalog.pg_depend d JOIN pg_catalog.pg_extension e ON e.oid=d.refobjid JOIN pg_catalog.{_catalog} o ON o.oid=d.objid CROSS JOIN LATERAL pg_catalog.pg_identify_object(d.classid,d.objid,d.objsubid) i CROSS JOIN LATERAL pg_catalog.aclexplode(COALESCE(o.{_acl},pg_catalog.acldefault('{_typ}',o.{_owner}))) x WHERE d.refclassid='pg_catalog.pg_extension'::regclass AND d.deptype='e' AND d.classid='pg_catalog.{_catalog}'::regclass")
_sql['extension_acl'] = Query(' UNION ALL '.join(_ext_acl),tuple('extension identity grantor grantee privilege grant_option'.split()))

_sql['database_acl'] = query("d.datname AS name,pg_get_userbyid(d.datdba) AS owner,pg_get_userbyid(x.grantor) AS grantor,CASE WHEN x.grantee=0 THEN 'PUBLIC' ELSE pg_get_userbyid(x.grantee) END AS grantee,x.privilege_type AS privilege,x.is_grantable AS grant_option",
 'name owner grantor grantee privilege grant_option', "FROM pg_catalog.pg_database d CROSS JOIN LATERAL pg_catalog.aclexplode(COALESCE(d.datacl,pg_catalog.acldefault('d',d.datdba))) x WHERE d.datname=current_database()")
_sql['toast'] = query('n.nspname AS schema,p.relname AS relation,t.relname AS name,t.relkind::text AS kind,pg_get_userbyid(t.relowner) AS owner,t.reloptions AS options',
 'schema relation name kind owner options', 'FROM pg_catalog.pg_class p JOIN pg_catalog.pg_namespace n ON n.oid=p.relnamespace JOIN pg_catalog.pg_class t ON t.oid=p.reltoastrelid OR t.oid IN (SELECT indexrelid FROM pg_catalog.pg_index WHERE indrelid=p.reltoastrelid) WHERE '+SCOPE)

_sql['type_details'] = query("n.nspname AS schema,t.typname AS name,to_jsonb(t)-'oid' AS properties",
 'schema name properties', 'FROM pg_catalog.pg_type t JOIN pg_catalog.pg_namespace n ON n.oid=t.typnamespace WHERE '+SCOPE)
_sql['enum_labels'] = query('n.nspname AS schema,t.typname AS name,e.enumlabel AS label,e.enumsortorder::text AS sort_order',
 'schema name label sort_order', 'FROM pg_catalog.pg_enum e JOIN pg_catalog.pg_type t ON t.oid=e.enumtypid JOIN pg_catalog.pg_namespace n ON n.oid=t.typnamespace WHERE '+SCOPE)
_sql['ranges'] = query('n.nspname AS schema,t.typname AS name,to_jsonb(r) AS properties',
 'schema name properties', 'FROM pg_catalog.pg_range r JOIN pg_catalog.pg_type t ON t.oid=r.rngtypid JOIN pg_catalog.pg_namespace n ON n.oid=t.typnamespace WHERE '+SCOPE)
_sql['default_acl_objects'] = query('pg_get_userbyid(a.defaclrole) AS owner,n.nspname AS schema,a.defaclobjtype::text AS kind,cardinality(a.defaclacl) AS entries',
 'owner schema kind entries', 'FROM pg_catalog.pg_default_acl a LEFT JOIN pg_catalog.pg_namespace n ON n.oid=a.defaclnamespace')

# Qualify builtins regardless of supplied search_path. No SET or implicit state changes.
import re as _re
_functions = ('host','current_database','pg_backend_pid','inet_server_addr','inet_server_port','current_setting',
 'has_database_privilege','pg_has_role','has_schema_privilege','pg_get_userbyid','pg_get_expr','pg_get_viewdef',
 'format_type','pg_get_constraintdef','pg_get_indexdef','pg_get_function_identity_arguments','pg_get_functiondef',
 'pg_get_triggerdef','pg_get_ruledef','has_function_privilege','cardinality','to_jsonb')
for _key, _q in tuple(_sql.items()):
    _text = _q.sql
    for _fn in _functions:
        _text = _re.sub(r'(?<![\w.])'+_fn+r'\(', 'pg_catalog.'+_fn+'(', _text)
    _text = _text.replace('::regclass','::pg_catalog.regclass').replace('::text','::pg_catalog.text').replace('::integer','::pg_catalog.int4').replace('::\"char\"','::pg_catalog.\"char\"')
    _text = _text.replace("-'oid'", " OPERATOR(pg_catalog.-) 'oid'")
    _sql[_key] = Query(_text, _q.fields, _q.maximum)
QUERIES = MappingProxyType(_sql)
