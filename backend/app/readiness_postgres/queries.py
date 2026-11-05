"""Fixed PG16 SELECT catalog. Templates have NOT been executed on PostgreSQL.

Each row is one JSON array named evidence. Values use named bind parameters;
identifiers are literals. An executor must stream ALL rows, never silently LIMIT.
"""
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class Query:
    name: str
    sql: str
    max_rows: int
    statement_ms: int = 500


SUBJECTS = """WITH subjects AS (
 SELECT oid, rolname FROM pg_catalog.pg_roles
 WHERE rolname IN (:runtime_role, :verifier_role)
) """


def select_array(expressions, source="", *, subjects=False):
    return ((SUBJECTS if subjects else "") +
            "SELECT pg_catalog.jsonb_build_array(" + expressions + ") AS evidence " + source)


_sql = {}
_sql["Q1"] = select_array("""pg_catalog.current_database(), current_user, session_user,
 pg_catalog.inet_server_addr()::text, pg_catalog.inet_server_port(),
 pg_catalog.current_setting('server_version_num'),
 pg_catalog.current_setting('transaction_read_only'),
 pg_catalog.current_setting('transaction_isolation'),
 pg_catalog.current_setting('search_path')""")
_sql["Q2"] = select_array("""rolname, rolcanlogin, rolsuper, rolcreatedb, rolcreaterole,
 rolreplication, rolbypassrls, oid::text""", "FROM pg_catalog.pg_roles WHERE rolname IN (:runtime_role, :verifier_role)")
_sql["Q3"] = select_array("""'path', s.rolname, r.rolname,
 pg_catalog.pg_has_role(s.oid,r.oid,'MEMBER'),
 pg_catalog.pg_has_role(s.oid,r.oid,'USAGE'),
 pg_catalog.pg_has_role(s.oid,r.oid,'SET')""", """FROM subjects s
 CROSS JOIN pg_catalog.pg_roles r WHERE r.oid <> s.oid""", subjects=True) + " UNION ALL " + select_array(
 "'edge', roleid::text, member::text, grantor::text, admin_option, inherit_option, set_option",
 "FROM pg_catalog.pg_auth_members")
_sql["Q4"] = select_array("""s.rolname,n.nspname,
 pg_catalog.has_schema_privilege(s.oid,n.oid,'USAGE'),
 pg_catalog.has_schema_privilege(s.oid,n.oid,'USAGE WITH GRANT OPTION'),
 pg_catalog.has_schema_privilege(s.oid,n.oid,'CREATE'),
 pg_catalog.has_schema_privilege(s.oid,n.oid,'CREATE WITH GRANT OPTION'),n.oid::text,n.nspowner::text""",
 "FROM subjects s CROSS JOIN pg_catalog.pg_namespace n", subjects=True)
_sql["Q5"] = select_array("""s.rolname,n.nspname,c.relname,p.priv,
 pg_catalog.has_table_privilege(s.oid,c.oid,p.priv),
 pg_catalog.has_table_privilege(s.oid,c.oid,p.priv || ' WITH GRANT OPTION')""", """FROM subjects s
 CROSS JOIN pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
 CROSS JOIN (VALUES ('SELECT'),('INSERT'),('UPDATE'),('DELETE'),('TRUNCATE'),('REFERENCES'),('TRIGGER')) p(priv)
 WHERE c.relkind IN ('r','p','v','m','f')""", subjects=True)
_sql["Q6"] = select_array("""s.rolname,n.nspname,c.relname,a.attname,p.priv,
 pg_catalog.has_column_privilege(s.oid,c.oid,a.attnum,p.priv),
 pg_catalog.has_column_privilege(s.oid,c.oid,a.attnum,p.priv || ' WITH GRANT OPTION')""", """FROM subjects s
 CROSS JOIN pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
 JOIN pg_catalog.pg_attribute a ON a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped
 CROSS JOIN (VALUES ('SELECT'),('INSERT'),('UPDATE'),('REFERENCES')) p(priv)
 WHERE c.relkind IN ('r','p','v','m','f')""", subjects=True)
_sql["Q7"] = select_array("""s.rolname,n.nspname,c.relname,p.priv,
 pg_catalog.has_sequence_privilege(s.oid,c.oid,p.priv),
 pg_catalog.has_sequence_privilege(s.oid,c.oid,p.priv || ' WITH GRANT OPTION')""", """FROM subjects s
 CROSS JOIN pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
 CROSS JOIN (VALUES ('USAGE'),('SELECT'),('UPDATE')) p(priv) WHERE c.relkind='S'""", subjects=True)

# Explicit owner catalogs cover pinned objects too; shdepend alone cannot do so.
_owners = (
    ('database', 'pg_database', 'datdba'), ('schema', 'pg_namespace', 'nspowner'),
    ('relation', 'pg_class', 'relowner'), ('routine', 'pg_proc', 'proowner'),
    ('type', 'pg_type', 'typowner'), ('extension', 'pg_extension', 'extowner'),
    ('language', 'pg_language', 'lanowner'), ('fdw', 'pg_foreign_data_wrapper', 'fdwowner'),
    ('server', 'pg_foreign_server', 'srvowner'), ('tablespace', 'pg_tablespace', 'spcowner'),
    ('largeobject', 'pg_largeobject_metadata', 'lomowner'),
    ('eventtrigger', 'pg_event_trigger', 'evtowner'), ('publication', 'pg_publication', 'pubowner'),
    ('subscription', 'pg_subscription', 'subowner'), ('conversion', 'pg_conversion', 'conowner'),
    ('collation', 'pg_collation', 'collowner'), ('opclass', 'pg_opclass', 'opcowner'),
    ('operator', 'pg_operator', 'oprowner'),
    ('opfamily', 'pg_opfamily', 'opfowner'), ('tsconfig', 'pg_ts_config', 'cfgowner'),
    ('tsdict', 'pg_ts_dict', 'dictowner'), ('statistics', 'pg_statistic_ext', 'stxowner'),
    ('defaultacl', 'pg_default_acl', 'defaclrole'),
)
OWNER_CLASSES = tuple(kind for kind, _, _ in _owners)
_sql["Q8"] = SUBJECTS + " UNION ALL ".join(select_array(
    f"s.rolname,'{kind}',o.oid::text,o.{owner}=s.oid,o.{owner}::text",
    f"FROM subjects s CROSS JOIN pg_catalog.{catalog} o")
    for kind, catalog, owner in _owners) + " UNION ALL " + " UNION ALL ".join(select_array(
    f"'coverage','{kind}',pg_catalog.count(*)", f"FROM pg_catalog.{catalog}")
    for kind, catalog, _ in _owners) + " UNION ALL " + select_array(
    "s.rolname,'dependency',d.classid::text || '/' || d.objid::text || '/' || d.objsubid::text,true,s.oid::text",
    """FROM subjects s JOIN pg_catalog.pg_shdepend d ON d.refobjid=s.oid
    WHERE d.refclassid='pg_catalog.pg_authid'::pg_catalog.regclass AND d.deptype='o'""")
_sql["Q9"] = select_array("""'database',s.rolname,d.datname,p.priv,
 pg_catalog.has_database_privilege(s.oid,d.oid,p.priv),
 pg_catalog.has_database_privilege(s.oid,d.oid,p.priv || ' WITH GRANT OPTION')""", """FROM subjects s
 CROSS JOIN pg_catalog.pg_database d CROSS JOIN (VALUES ('CONNECT'),('CREATE'),('TEMPORARY')) p(priv)
 WHERE d.datname=pg_catalog.current_database()""", subjects=True) + " UNION ALL " + select_array(
 """'parameter',s.rolname,a.parname,p.priv,
 pg_catalog.has_parameter_privilege(s.oid,a.parname,p.priv),
 pg_catalog.has_parameter_privilege(s.oid,a.parname,p.priv || ' WITH GRANT OPTION')""",
 "FROM subjects s CROSS JOIN pg_catalog.pg_parameter_acl a CROSS JOIN (VALUES ('SET'),('ALTER SYSTEM')) p(priv)")

# These ACL-bearing classes have no table/column privilege cells. Record their
# complete ACLs, including grants to other roles. Membership/ownership checks
# are separate. No invented has_largeobject_privilege() (absent in PG16).
_aux_acl_sources = (
    ('type', 'pg_type', 'typacl', 'typowner', 'T'),
    ('language', 'pg_language', 'lanacl', 'lanowner', 'l'),
    ('fdw', 'pg_foreign_data_wrapper', 'fdwacl', 'fdwowner', 'F'),
    ('server', 'pg_foreign_server', 'srvacl', 'srvowner', 'S'),
    ('tablespace', 'pg_tablespace', 'spcacl', 'spcowner', 't'),
    ('largeobject', 'pg_largeobject_metadata', 'lomacl', 'lomowner', 'L'),
)
_sql["Q9"] += " UNION ALL " + " UNION ALL ".join(select_array(
    f"'object_acl','{kind}',o.oid::text,x.grantor::text,x.grantee::text,x.privilege_type,x.is_grantable",
    f"FROM pg_catalog.{catalog} o CROSS JOIN LATERAL pg_catalog.aclexplode(COALESCE(o.{acl},pg_catalog.acldefault('{typ}',o.{owner}))) x")
    for kind, catalog, acl, owner, typ in _aux_acl_sources)

# Full provenance, including empty ACLs and the NULL/explicit distinction.
# Identities are arrays, not dotted strings (identifiers can themselves contain dots).
_acl_sources = (
    ('database', 'pg_catalog.jsonb_build_array(d.datname,d.oid::text)', 'd.datacl', "'d'", 'd.datdba', 'pg_catalog.pg_database d'),
    ('schema', 'pg_catalog.jsonb_build_array(n.nspname,n.oid::text)', 'n.nspacl', "'n'", 'n.nspowner', 'pg_catalog.pg_namespace n'),
    ('relation', 'pg_catalog.jsonb_build_array(n.nspname,c.relname,c.oid::text)', 'c.relacl',
     "CASE WHEN c.relkind='S' THEN 's'::pg_catalog.\"char\" ELSE 'r'::pg_catalog.\"char\" END", 'c.relowner',
     "(SELECT oid,relname,relnamespace,relacl,relkind,relowner FROM pg_catalog.pg_class WHERE relkind IN ('r','p','v','m','f','S')) c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace"),
    ('routine', 'pg_catalog.jsonb_build_array(n.nspname,p.proname,pg_catalog.pg_get_function_identity_arguments(p.oid),p.oid::text)',
     'p.proacl', "'f'", 'p.proowner', 'pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace'),
)
_acl_sources += tuple((kind, 'pg_catalog.jsonb_build_array(o.oid::text)', f'o.{acl}',
    f"'{typ}'", f'o.{owner}', f'pg_catalog.{catalog} o')
    for kind, catalog, acl, owner, typ in _aux_acl_sources)
_acl_parts = []
for kind, key, acl, typ, owner, source in _acl_sources:
    expanded = f"COALESCE({acl},pg_catalog.acldefault({typ},{owner}))"
    _acl_parts.extend((select_array(
        f"'object','{kind}',{key},{owner}::text,CASE WHEN {acl} IS NULL THEN 'default' ELSE 'explicit' END,pg_catalog.cardinality(ARRAY(SELECT 1 FROM pg_catalog.aclexplode({expanded})))",
        f"FROM {source}"), select_array(
        f"'grant','{kind}',{key},x.grantor::text,x.grantee::text,x.privilege_type,x.is_grantable",
        f"FROM {source} CROSS JOIN LATERAL pg_catalog.aclexplode({expanded}) x")))
_column_source = """FROM pg_catalog.pg_attribute a JOIN pg_catalog.pg_class c ON c.oid=a.attrelid
 JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace"""
_column_key = "pg_catalog.jsonb_build_array(n.nspname,c.relname,a.attname,c.oid::text,a.attnum)"
_acl_parts.extend((select_array(
    f"'object','column',{_column_key},c.relowner::text,CASE WHEN a.attacl IS NULL THEN 'default' ELSE 'explicit' END,pg_catalog.cardinality(ARRAY(SELECT 1 FROM pg_catalog.aclexplode(a.attacl)))",
    _column_source + " WHERE a.attnum>0 AND NOT a.attisdropped"), select_array(
    f"'grant','column',{_column_key},x.grantor::text,x.grantee::text,x.privilege_type,x.is_grantable",
    _column_source + " CROSS JOIN LATERAL pg_catalog.aclexplode(a.attacl) x WHERE a.attnum>0 AND NOT a.attisdropped")))
_sql["Q10"] = " UNION ALL ".join(_acl_parts)
# Parameters have ACLs but no owner column. NULL here is an unknown ACL, not
# permission to invent a bootstrap owner or positive default privileges.
_sql["Q10"] += " UNION ALL " + select_array(
    """'object','parameter',pg_catalog.jsonb_build_array(a.parname,a.oid::text),NULL,
    CASE WHEN a.paracl IS NULL THEN 'unknown' ELSE 'explicit' END,
    pg_catalog.cardinality(ARRAY(SELECT 1 FROM pg_catalog.aclexplode(a.paracl)))""",
    "FROM pg_catalog.pg_parameter_acl a") + " UNION ALL " + select_array(
    """'grant','parameter',pg_catalog.jsonb_build_array(a.parname,a.oid::text),
    x.grantor::text,x.grantee::text,x.privilege_type,x.is_grantable""",
    "FROM pg_catalog.pg_parameter_acl a CROSS JOIN LATERAL pg_catalog.aclexplode(a.paracl) x")
_sql["Q11"] = select_array("""s.rolname,n.nspname,p.oid::text,p.proname,
 pg_catalog.pg_get_function_identity_arguments(p.oid),p.prokind::text,p.proowner::text,
 p.prosecdef,l.lanname,p.proconfig,
 pg_catalog.has_function_privilege(s.oid,p.oid,'EXECUTE'),
 pg_catalog.has_function_privilege(s.oid,p.oid,'EXECUTE WITH GRANT OPTION'),
 CASE WHEN p.prokind IN ('f','p') THEN pg_catalog.encode(pg_catalog.sha256(
 pg_catalog.convert_to(pg_catalog.pg_get_functiondef(p.oid),'UTF8')),'hex') ELSE NULL END""",
 """FROM subjects s CROSS JOIN pg_catalog.pg_proc p
 JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace
 JOIN pg_catalog.pg_language l ON l.oid=p.prolang""", subjects=True)
_sql["Q12"] = select_array("""'default',a.defaclrole::text,a.defaclnamespace::text,a.defaclobjtype::text,a.oid::text,
 pg_catalog.cardinality(ARRAY(SELECT 1 FROM pg_catalog.aclexplode(a.defaclacl)))""", "FROM pg_catalog.pg_default_acl a") + " UNION ALL " + select_array("""'grant',a.defaclrole::text,a.defaclnamespace::text,a.defaclobjtype::text,a.oid::text,
 x.grantor::text,x.grantee::text,x.privilege_type,x.is_grantable""",
 "FROM pg_catalog.pg_default_acl a CROSS JOIN LATERAL pg_catalog.aclexplode(a.defaclacl) x")
_sql["Q13"] = select_array("""'relation',n.nspname,c.relname,c.relkind::text,c.relowner::text,c.relpersistence::text,c.oid::text""",
 "FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace") + " UNION ALL " + select_array(
 """'column',n.nspname,c.relname,a.attname,a.attnum,
 pg_catalog.format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity::text,
 a.attgenerated::text,pg_catalog.pg_get_expr(d.adbin,d.adrelid)""", """FROM pg_catalog.pg_class c
 JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
 JOIN pg_catalog.pg_attribute a ON a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped
 LEFT JOIN pg_catalog.pg_attrdef d ON d.adrelid=c.oid AND d.adnum=a.attnum""")
_sql["Q14"] = select_array("'constraint',oid::text,conrelid::text,conname,convalidated,pg_catalog.pg_get_constraintdef(oid,true),contype::text,conindid::text,conkey,confrelid::text,confkey",
 "FROM pg_catalog.pg_constraint") + " UNION ALL " + select_array(
 "'index',i.indexrelid::text,i.indrelid::text,i.indisvalid,i.indisready,pg_catalog.pg_get_indexdef(i.indexrelid),c.relname,i.indisunique,i.indisprimary,i.indkey::smallint[]",
 "FROM pg_catalog.pg_index i JOIN pg_catalog.pg_class c ON c.oid=i.indexrelid") + " UNION ALL " + select_array(
 "'trigger',oid::text,tgrelid::text,tgfoid::text,tgenabled::text,tgisinternal,pg_catalog.pg_get_triggerdef(oid,true),tgname,tgconstraint::text",
 "FROM pg_catalog.pg_trigger") + " UNION ALL " + select_array(
 "'rls',oid::text,relrowsecurity,relforcerowsecurity", "FROM pg_catalog.pg_class") + " UNION ALL " + select_array(
 """'policy',oid::text,polrelid::text,polname,polcmd::text,polpermissive,polroles,
 pg_catalog.pg_get_expr(polqual,polrelid),pg_catalog.pg_get_expr(polwithcheck,polrelid)""", "FROM pg_catalog.pg_policy") + " UNION ALL " + select_array(
 """'rule',n.nspname,c.relname,c.oid::text,r.oid::text,r.rulename,r.ev_type::text,
 r.is_instead,r.ev_enabled::text,pg_catalog.pg_get_ruledef(r.oid,false)""",
 """FROM pg_catalog.pg_rewrite r JOIN pg_catalog.pg_class c ON c.oid=r.ev_class
 JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace""") + " UNION ALL " + select_array(
 """'coverage',c.oid::text,
 (SELECT pg_catalog.count(*) FROM pg_catalog.pg_constraint x WHERE x.conrelid=c.oid),
 (SELECT pg_catalog.count(*) FROM pg_catalog.pg_index x WHERE x.indrelid=c.oid),
 (SELECT pg_catalog.count(*) FROM pg_catalog.pg_trigger x WHERE x.tgrelid=c.oid),
 (SELECT pg_catalog.count(*) FROM pg_catalog.pg_rewrite x WHERE x.ev_class=c.oid),
 (SELECT pg_catalog.count(*) FROM pg_catalog.pg_policy x WHERE x.polrelid=c.oid)""", "FROM pg_catalog.pg_class c")
_sql["Q14"] += " UNION ALL " + " UNION ALL ".join(select_array(
    f"'catalog','{kind}',pg_catalog.count(*)", f"FROM pg_catalog.{table}")
    for kind, table in (("constraint", "pg_constraint"), ("index", "pg_index"),
                        ("trigger", "pg_trigger"), ("rule", "pg_rewrite"), ("policy", "pg_policy")))
_sql["Q15"] = select_array("'application',version_num", "FROM public.alembic_version") + " UNION ALL " + select_array(
 "'security',version_num", "FROM public.alembic_security_version")
_sql["Q16"] = select_array("system_identifier::text,pg_control_version,catalog_version_no", "FROM pg_catalog.pg_control_system()")

_limits = {"Q1": 1, "Q2": 2, "Q3": 8192, "Q4": 256, "Q5": 262144,
           "Q6": 262144, "Q7": 262144, "Q8": 65536, "Q9": 65536,
           "Q10": 32768, "Q11": 16384, "Q12": 8192, "Q13": 65536,
           "Q14": 65536, "Q15": 2, "Q16": 1}
CATALOG = MappingProxyType({name: Query(name, sql, _limits[name],
    1000 if name in {"Q6", "Q8", "Q10", "Q11", "Q13", "Q14"} else 500)
    for name, sql in _sql.items()})
