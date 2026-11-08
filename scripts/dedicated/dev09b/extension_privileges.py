"""Read-only effective-privilege preparation; no speculative support grants.

The migrations use UUID equality, varchar/text equality and tstzrange overlap.
Internal GiST support calls are distinct from explicit SQL function execution.
Any unexpected permission failure requires a new named grant decision.
"""
from sqlalchemy import text
from . import codec as c

SQL="""SELECT
 pg_catalog.has_schema_privilege(current_user,'public','USAGE') AS public_usage,
 pg_catalog.has_schema_privilege(current_user,'inventory','CREATE') AS inventory_create,
 pg_catalog.has_type_privilege(current_user,'pg_catalog.uuid','USAGE') AS uuid_usage,
 pg_catalog.has_type_privilege(current_user,'pg_catalog.varchar','USAGE') AS varchar_usage,
 pg_catalog.has_type_privilege(current_user,'pg_catalog.text','USAGE') AS text_usage,
 pg_catalog.has_type_privilege(current_user,'pg_catalog.timestamptz','USAGE') AS timestamptz_usage,
 pg_catalog.has_type_privilege(current_user,'pg_catalog.tstzrange','USAGE') AS range_usage,
 pg_catalog.has_function_privilege(current_user,'pg_catalog.tstzrange(timestamp with time zone,timestamp with time zone,text)','EXECUTE') AS range_constructor,
 pg_catalog.has_function_privilege(current_user,'pg_catalog.now()','EXECUTE') AS now_function,
 (SELECT count(*) FROM pg_catalog.pg_opclass o
  JOIN pg_catalog.pg_am a ON a.oid=o.opcmethod
  JOIN pg_catalog.pg_namespace n ON n.oid=o.opcnamespace
  JOIN pg_catalog.pg_depend d ON d.classid='pg_catalog.pg_opclass'::pg_catalog.regclass AND d.objid=o.oid AND d.deptype='e'
  JOIN pg_catalog.pg_extension e ON d.refclassid='pg_catalog.pg_extension'::pg_catalog.regclass AND e.oid=d.refobjid
  WHERE n.nspname='public' AND a.amname='gist' AND e.extname='btree_gist' AND e.extversion='1.7'
    AND o.opcdefault AND ((o.opcname='gist_uuid_ops' AND o.opcintype='pg_catalog.uuid'::pg_catalog.regtype)
      OR (o.opcname='gist_text_ops' AND o.opcintype='pg_catalog.text'::pg_catalog.regtype))) AS opclasses,
 pg_catalog.has_type_privilege(current_user,'public.gbtreekey16','USAGE') AS internal_uuid_storage_usage,
 pg_catalog.has_type_privilege(current_user,'public.gbtreekey_var','USAGE') AS internal_text_storage_usage"""


def inspect(connection):
    row=dict(connection.execute(text(SQL)).mappings().one())
    required={'public_usage','inventory_create','uuid_usage','varchar_usage','text_usage',
              'timestamptz_usage','range_usage','range_constructor','now_function'}
    c.require(all(row[key] is True for key in required))
    c.require(type(row['opclasses']) is int and row['opclasses']==2)
    for key in ('internal_uuid_storage_usage','internal_text_storage_usage'):
        c.require(type(row[key]) is bool)
    return row  # Internal storage USAGE is reported, never silently granted.
