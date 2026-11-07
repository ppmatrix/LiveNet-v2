"""Read-only AST extraction for the fourteen fixed migrations. NEVER imports them.

This is a declaration normal form, not generated SQL or a PostgreSQL deparser.
Unknown syntax is Unsupported, not omitted. Implicit server objects are supplied
separately from a pinned distribution/template, never inferred from observation.
"""
import ast
from hashlib import sha256
import re
from pathlib import Path

from . import codec as c
from .layers import APP_REVISIONS


class MissingParameter(c.Unsupported):
    def __init__(self, path):
        self.path = path
        super().__init__("Missing approved parameter: " + path)


def exact(obj, fields, location):
    c.require(type(obj) is dict)
    missing = sorted(set(fields) - set(obj))
    if missing:
        raise MissingParameter(location + "." + missing[0])
    c.closed(obj, set(fields))


def literal(node):
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError):
        raise c.Unsupported("Nonliteral migration argument") from None


def call(node, expected=None):
    if not isinstance(node, ast.Call):
        raise c.Unsupported("Unsupported migration expression")
    func = ast.unparse(node.func)
    if expected is not None and func != expected:
        raise c.Unsupported("Unexpected migration constructor: " + func)
    if any(k.arg is None for k in node.keywords):
        raise c.Unsupported("Expanded migration keywords")
    return func, node.args, {k.arg:k.value for k in node.keywords}


def sql_expr(node):
    func,args,kw = call(node)
    c.require(not kw)
    if func == "sa.text" and len(args) == 1:
        value = literal(args[0]); c.require(type(value) is str)
        return value
    if not args and func in {"sa.func.now", "sa.true"}:
        return "now()" if func == "sa.func.now" else "true"
    raise c.Unsupported("Unsupported default/expression: " + func)


def data_type(node):
    func,args,kw = call(node)
    if func in {"sa.String", "sa.Numeric"}:
        values = [literal(x) for x in args]
        if kw:
            c.require(func == "sa.String" and not values and set(kw) == {"length"})
            values = [literal(kw["length"])]
        c.require(len(values) == (1 if func == "sa.String" else 2))
        for v in values: c.integer(v)
    elif func == "sa.DateTime":
        c.require(not args and set(kw) == {"timezone"} and literal(kw["timezone"]) is True)
        values = []
    elif func == "postgresql.UUID":
        c.require(not args and set(kw) == {"as_uuid"} and literal(kw["as_uuid"]) is True)
        values = []
    elif func in {"sa.Integer", "sa.Text", "sa.Boolean", "postgresql.JSONB"}:
        c.require(not args and not kw); values = []
    else:
        raise c.Unsupported("Unsupported migration type: " + func)
    return {"name":func, "arguments":values}


def object_record(family, identity, definition):
    return {"family":family,"identity":identity,"definition":definition}


def constraint(node, schema, table):
    func,args,kw = call(node)
    kinds = {"sa.PrimaryKeyConstraint":"p","sa.UniqueConstraint":"u","sa.ForeignKeyConstraint":"f",
             "sa.CheckConstraint":"c","postgresql.ExcludeConstraint":"x"}
    if func not in kinds: raise c.Unsupported("Unsupported table member: " + func)
    kind = kinds[func]
    c.require(set(kw) <= ({"name","using","where"} if kind=="x" else {"name"}))
    cols=[]; refs=[]; expression=None; operators=[]
    if kind in {"p","u"}: cols=[literal(a) for a in args]
    elif kind=="f":
        c.require(len(args)==2); cols=literal(args[0]); refs=literal(args[1])
    elif kind=="c":
        c.require(len(args)==1); expression=literal(args[0])
    else:
        for a in args:
            c.require(isinstance(a,ast.Tuple) and len(a.elts)==2)
            exp=sql_expr(a.elts[0]) if isinstance(a.elts[0],ast.Call) else literal(a.elts[0])
            operators.append({"expression":exp,"operator":literal(a.elts[1])})
        cols=[x["expression"] for x in operators]
    cname=literal(kw["name"]) if "name" in kw else table+("_pkey" if kind=="p" else "_"+"_".join(cols)+("_fkey" if kind=="f" else "_key"))
    if len(cname.encode())>63:
        raise c.Unsupported("Implicit constraint name requires reviewed PostgreSQL name resolution")
    definition=dict(kind=kind,columns=cols,references=refs,expression=expression,operators=operators,
                    using=literal(kw["using"]) if "using" in kw else None,
                    predicate=sql_expr(kw["where"]) if "where" in kw else None,
                    validated=True,deferrable=False,initially_deferred=False)
    return object_record("constraint",[schema,table,cname],definition)


def table_objects(node):
    _,args,kw=call(node,"op.create_table")
    c.require(set(kw)=={"schema"})
    schema=literal(kw["schema"]); table=literal(args[0])
    result=[object_record("table",[schema,table],dict(persistence="p",row_security=False,force_row_security=False))]
    primary=[]; constraints=[]; position=0
    for a in args[1:]:
        func,aa,kk=call(a)
        if func != "sa.Column":
            constraints.append(constraint(a,schema,table));continue
        c.require(set(kk)<={"nullable","primary_key","server_default"} and len(aa) in {2,3})
        position+=1; col=literal(aa[0])
        nullable=literal(kk["nullable"]) if "nullable" in kk else True
        pk=literal(kk["primary_key"]) if "primary_key" in kk else False
        c.require(type(nullable) is bool and type(pk) is bool)
        if pk: primary.append(col)
        result.append(object_record("column",[schema,table,col],dict(position=position,type=data_type(aa[1]),
                      nullable=nullable,default=sql_expr(kk["server_default"]) if "server_default" in kk else None,
                      identity="",generated="")))
        if len(aa)==3:
            _,fkargs,fkkw=call(aa[2],"sa.ForeignKey");c.require(len(fkargs)==1 and not fkkw)
            fake=ast.Call(func=ast.Attribute(value=ast.Name(id="sa"),attr="ForeignKeyConstraint"),
                          args=[ast.List(elts=[ast.Constant(col)]),ast.List(elts=[fkargs[0]])],keywords=[])
            constraints.append(constraint(fake,schema,table))
    if primary:
        fake=ast.Call(func=ast.Attribute(value=ast.Name(id="sa"),attr="PrimaryKeyConstraint"),
                      args=[ast.Constant(x) for x in primary],keywords=[])
        constraints.append(constraint(fake,schema,table))
    for co in constraints:
        result.append(co)
        if co["definition"]["kind"] in {"p","u","x"}:
            d=co["definition"]
            result.append(object_record("index",[schema,co["identity"][-1]],dict(table=table,columns=d["columns"],
                          unique=d["kind"] in {"p","u"},primary=d["kind"]=="p",method=d["using"] or "btree",
                          predicate=d["predicate"],constraint=co["identity"][-1],valid=True,ready=True)))
    # Type/array/TOAST and operator-class details must be resolved from the fixed
    # distribution's resolver inputs, not guessed from an observed database.
    return result


def ddl_objects(sql):
    c.require(type(sql) is str)
    clean=sql.strip().rstrip(";").strip()
    if re.match(r"CREATE\s+(?:EXTENSION|SCHEMA)\b",clean,re.I):
        raise c.Unsupported("DEV09B-PREPARED-1 forbids schema/extension provisioning in migrations")
    m=re.fullmatch(r"CREATE FUNCTION (inventory|audit)\.([a-z_]+)\(\)\s+RETURNS trigger\s+LANGUAGE plpgsql\s+(SECURITY INVOKER\s+)?AS (\$[a-z_]*\$)(.*?)\4",clean,re.S)
    if m:return [object_record("routine",[m[1],m[2],""],dict(returns="trigger",language="plpgsql",security_definer=False,
                      body=m[5].strip(),volatility="VOLATILE",strict=False,parallel="UNSAFE",config=[]))]
    m=re.fullmatch(r"CREATE TRIGGER ([a-z_]+)\s+BEFORE UPDATE OR DELETE\s+ON (inventory|audit)\.([a-z_]+)\s+FOR EACH ROW\s+EXECUTE FUNCTION (inventory|audit)\.([a-z_]+)\(\)",clean,re.S)
    if m:return [object_record("trigger",[m[2],m[3],m[1]],dict(timing="BEFORE",events=["UPDATE","DELETE"],
                      row=True,function=[m[4],m[5],""],enabled="O",internal=False))]
    raise c.Unsupported("Unrecognized migration DDL; no partial extraction")


def extract_sources(sources):
    """sources: ordered (repository-relative path, exact source bytes) pairs."""
    expected=(*APP_REVISIONS,"b12b01a7230")
    c.require(len(sources)==len(expected))
    objects=[]; inventory=[]; application=None
    previous=None
    for (path,raw),rev in zip(sources,expected):
        c.require(type(raw) is bytes)
        tree=ast.parse(raw.decode("utf-8"))
        assignments={}
        for x in tree.body:
            if isinstance(x,ast.Assign) and len(x.targets)==1 and isinstance(x.targets[0],ast.Name):
                if x.targets[0].id in {"revision","down_revision"}:assignments[x.targets[0].id]=literal(x.value)
            elif isinstance(x,ast.AnnAssign) and isinstance(x.target,ast.Name) and x.target.id in {"revision","down_revision"}:
                assignments[x.target.id]=literal(x.value)
        c.require(assignments=={"revision":rev,"down_revision":None if rev=="b12b01a7230" else previous})
        functions=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=="upgrade"]
        c.require(len(functions)==1)
        prerequisites={"af62df027d9d":("require_prepared_schema","inventory"),
                       "f066a01a7230":("require_prepared_schema","audit"),
                       "b12b01a7230":("require_prepared_schema","security"),
                       "ba06dd956da9":("require_prepared_extension","btree_gist"),
                       "9e1b7c42a630":("require_prepared_extension","btree_gist")}
        if rev in prerequisites:
            needed,value=prerequisites[rev]
            imports=[n for x in tree.body if isinstance(x,ast.ImportFrom) and x.module=="migrations.dev09b_prerequisites" for n in x.names]
            c.require(any(x.name==needed and x.asname is None for x in imports))
            body=[x for x in functions[0].body if not (isinstance(x,ast.Expr) and isinstance(x.value,ast.Constant) and type(x.value.value) is str)]
            if not body or not isinstance(body[0],ast.Expr):
                raise c.Unsupported("DEV09B prepared prerequisite must precede all migration effects")
            f,a,k=call(body[0].value)
            if f!=needed:raise c.Unsupported("Historical/provisioning migration incompatible with DEV09B-PREPARED-1")
            c.require(len(a)==1 and literal(a[0])==value and not k)
        for statement in functions[0].body:
            if isinstance(statement,ast.Expr) and isinstance(statement.value,ast.Constant) and type(statement.value.value) is str:continue
            if not isinstance(statement,ast.Expr):raise c.Unsupported("Migration control flow unsupported")
            func,args,kw=call(statement.value)
            if func in {"require_prepared_schema","require_prepared_extension"}:
                c.require(len(args)==1 and not kw)
                value=literal(args[0])
                required={"af62df027d9d":("require_prepared_schema","inventory"),
                          "f066a01a7230":("require_prepared_schema","audit"),
                          "b12b01a7230":("require_prepared_schema","security"),
                          "ba06dd956da9":("require_prepared_extension","btree_gist"),
                          "9e1b7c42a630":("require_prepared_extension","btree_gist")}
                c.require(required.get(rev)==(func,value))
            elif func=="op.create_table":objects+=table_objects(statement.value)
            elif func=="op.execute":
                c.require(len(args)==1 and not kw);objects+=ddl_objects(literal(args[0]))
            elif func=="op.create_index":
                c.require(len(args)==3 and set(kw)<={"schema","unique","postgresql_where"} and "schema" in kw)
                unique=literal(kw["unique"]) if "unique" in kw else False;c.require(type(unique) is bool)
                objects.append(object_record("index",[literal(kw["schema"]),literal(args[0])],dict(table=literal(args[1]),
                    columns=literal(args[2]),unique=unique,primary=False,method="btree",
                    predicate=sql_expr(kw["postgresql_where"]) if "postgresql_where" in kw else None,constraint=None,valid=True,ready=True)))
            else:raise c.Unsupported("Unsupported migration operation: "+func)
        inventory.append({"path":path,"sha256":sha256(raw).hexdigest()})
        if rev=="f066a01a7230":application=list(objects)
        previous=rev
    return {"application":application,"security":objects[len(application):],"sources":sorted(inventory,key=lambda x:x["path"])}


def load_repository_sources(root):
    """Focused local source read only. No migration imports, calls or SQL."""
    root=Path(root)
    result=[]
    for rev in (*APP_REVISIONS,"b12b01a7230"):
        directory="backend/security_migrations/versions" if rev=="b12b01a7230" else "backend/migrations/versions"
        paths=list((root/directory).glob(rev+"_*.py"))
        if len(paths)!=1:raise MissingParameter("migration_source."+rev)
        result.append((str(paths[0].relative_to(root)),paths[0].read_bytes()))
    return result
