"""Closed application-only source compiler; no observations or executable SQL.

Candidate PG16 deparse declarations are not independently confirmed evidence.
Only the fixed thirteen-application-migration grammar and pinned UTF8/amd64 build are
supported. Unknown expressions/types/layouts fail closed.
"""
import ast
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import re
from . import codec as c, physical as p, migration_catalog as m
from . import fixed_catalog_context as base, fixed_catalog_sources as image

MANIFEST='scripts/dedicated/dev09b/artifacts/pg16-application/sources.candidate.json'
FILES={'src/backend/catalog/toasting.c','src/backend/access/heap/heapam_handler.c','src/include/storage/bufpage.h',
       'src/include/storage/itemid.h','src/backend/parser/parse_expr.c','src/backend/parser/parse_coerce.c',
       'src/backend/parser/parse_oper.c','src/backend/utils/adt/numeric.c','src/include/parser/kwlist.h','pg_config.h'}


def load(root):
    root=Path(root);doc=c.parse((root/MANIFEST).read_bytes(),maximum=32768)
    c.closed(doc,{'schema_version','status','version','archive_sha256','image','sources','migration_sources','url'})
    c.require(type(doc['schema_version']) is int and doc['schema_version']==1 and doc['version']=='16.15'
              and doc['url']=='https://ftp.postgresql.org/pub/source/v16.15/postgresql-16.15.tar.bz2' and doc['status']=='CANDIDATE_NOT_APPROVED' and doc['archive_sha256']==base.ARCHIVE_SHA256 and doc['image']==image.IMAGE)
    files={}
    for row in doc['sources']:
        c.digest_text(row['sha256'])
        build='image_path' in row
        c.closed(row,{'path','sha256','image_path' if build else 'archive_path'})
        key='pg_config.h' if build else row['archive_path'].removeprefix('postgresql-16.15/')
        c.require(key in FILES and key not in files and row['path']==str(Path(MANIFEST).parent/key))
        if build:c.require(row['image_path']=='/usr/local/include/postgresql/server/pg_config.h')
        else:c.require(row['archive_path']=='postgresql-16.15/'+key)
        file=root/row['path'];c.require(not any(x.is_symlink() for x in (file,*file.parents)))
        data=file.read_bytes();c.require(sha256(data).hexdigest()==row['sha256']);files[key]=data.decode()
    c.require(set(files)==FILES)
    def macro(name):
        values=re.findall(r'^#define '+name+r' ([0-9]+)$',files['pg_config.h'],re.M)
        c.require(len(values)==1);return int(values[0])
    build={k:macro(k) for k in ('BLCKSZ','SIZEOF_VOID_P','MAXIMUM_ALIGNOF')}
    if build!={'BLCKSZ':8192,'SIZEOF_VOID_P':8,'MAXIMUM_ALIGNOF':8}:raise c.Unsupported('Unimplemented PostgreSQL build layout')
    c.require('return (tuple_length > TOAST_TUPLE_THRESHOLD)' in files['src/backend/access/heap/heapam_handler.c'])
    c.require('UNRESERVED_KEYWORD' in files['src/include/parser/kwlist.h'])
    c.require('numeric_digits = (precision + 2 * (DEC_DIGITS - 1)) / DEC_DIGITS' in files['src/backend/utils/adt/numeric.c'])
    base.load_sources(root)  # heap.c/pg_type.c/typecmds.c/ruleutils.c/format_type.c
    return build,doc


def ident(value):
    if not isinstance(value,str) or re.fullmatch('[a-z_][a-z0-9_]{0,62}',value) is None:raise c.Unsupported('Unsupported source identifier')
    # These keywords actually occur in the fixed source. Preserve PostgreSQL's
    # quote_identifier output; do not assume every identifier needs quoting.
    return value  # key/value are UNRESERVED_KEYWORD in pinned kwlist.h


def sql_type(t):
    c.closed(t,{'name','arguments'});args=t['arguments'];name=t['name']
    plain={'sa.Integer':'integer','sa.Text':'text','sa.Boolean':'boolean','postgresql.UUID':'uuid','postgresql.JSONB':'jsonb','sa.DateTime':'timestamp with time zone'}
    if name in plain:c.require(args==[]);return plain[name]
    if name=='sa.String':
        c.require(type(args) is list and len(args)==1);c.integer(args[0],1,10485760);return 'character varying('+str(args[0])+')'
    if name=='sa.Numeric':
        c.require(type(args) is list and len(args)==2);c.integer(args[0],1,1000);c.integer(args[1],0,args[0]);return 'numeric('+','.join(map(str,args))+')'
    raise c.Unsupported('Unsupported source column type')


class Expression:
    """Restricted parser for the actual CHECK/index expression grammar.

    Ports ruleutils.c's non-pretty expression parentheses/coercions. This is
    deliberately not a SQL parser and never accepts unconsumed input.
    """
    pattern=re.compile(r"\s*(?:(?P<s>'(?:[^']|'')*')|(?P<n>[0-9]+)|(?P<i>[a-z_][a-z0-9_]*)|(?P<k>AND|OR|IS|NOT|NULL|IN)|(?P<o><>|>=|<=|[=<>(),]))")
    def __init__(self,text,columns):
        self.tokens=[];pos=0;self.columns=columns
        while pos<len(text):
            x=self.pattern.match(text,pos)
            if not x:raise c.Unsupported('Unsupported source expression token')
            self.tokens.append((x.lastgroup,x.group(x.lastgroup)));pos=x.end()
        self.cursor=0
    def peek(self):return self.tokens[self.cursor][1] if self.cursor<len(self.tokens) else None
    def take(self,wanted=None):
        if self.cursor>=len(self.tokens):raise c.Unsupported('Incomplete source expression')
        token=self.tokens[self.cursor];self.cursor+=1
        if wanted is not None and token[1]!=wanted:raise c.Unsupported('Unexpected source expression token')
        return token
    def atom(self):
        if self.peek()=='(':
            self.take();node=self.boolean();self.take(')');return node
        kind,value=self.take()
        if kind=='s':return ('literal',value,'unknown')
        if kind=='n':return ('literal',value,'integer')
        if kind!='i':raise c.Unsupported('Unsupported source expression atom')
        if self.peek()=='(':
            self.take();args=[self.boolean()]
            while self.peek()==',':self.take();args.append(self.boolean())
            self.take(')')
            if value in {'length','lower','btrim'}:
                c.require(len(args)==1);args=[self.coerce(args[0],'text')];typ='integer' if value=='length' else 'text'
            elif value=='jsonb_typeof':c.require(len(args)==1 and args[0][-1]=='jsonb');typ='text'
            elif value=='tstzrange':
                c.require(len(args)==3 and all(x[-1]=='timestamp with time zone' for x in args[:2]));args[2]=self.coerce(args[2],'text');typ='tstzrange'
            else:raise c.Unsupported('Unsupported source function')
            return ('call',value,args,typ)
        if value not in self.columns:raise c.Unsupported('Unresolved source expression column')
        return ('column',ident(value),sql_type(self.columns[value]),)
    @staticmethod
    def coerce(node,typ):
        current=node[-1]
        if current==typ:return node
        if current=='unknown':return ('literal',node[1],typ)
        if (current.startswith('character varying') and typ=='text') or (current=='integer' and typ=='numeric'):
            return ('cast',node,typ)
        raise c.Unsupported('Unsupported source coercion')
    def comparison(self):
        left=self.atom();op=self.peek()
        if op=='IS':
            self.take();negative=self.peek()=='NOT'
            if negative:self.take()
            self.take('NULL');return ('null',left,negative,'boolean')
        if op=='IN':
            self.take();self.take('(');items=[self.atom()]
            while self.peek()==',':self.take();items.append(self.atom())
            self.take(')')
            if not (left[-1].startswith('character varying') and all(x[0]=='literal' and x[-1]=='unknown' for x in items)):raise c.Unsupported('Unsupported source IN operand types')
            return ('in',self.coerce(left,'text'),items,'boolean')
        if op in {'=','<>','>=','>','<','<='}:
            self.take();right=self.atom();lt,rt=left[-1],right[-1]
            typ='text' if lt.startswith('character varying') or rt.startswith('character varying') else lt if rt=='unknown' else rt if lt=='unknown' else 'numeric' if lt.startswith('numeric') or rt.startswith('numeric') else lt
            if lt.startswith('numeric'):lt='numeric';left=(*left[:-1],lt)
            if rt.startswith('numeric'):rt='numeric';right=(*right[:-1],rt)
            left=self.coerce(left,typ);right=self.coerce(right,typ)
            c.require(left[-1]==right[-1]);return ('binary',op,left,right,'boolean')
        return left
    def boolean(self,level=0):
        if level==2:return self.comparison()
        wanted=('OR','AND')[level];args=[self.boolean(level+1)]
        while self.peek()==wanted:self.take();args.append(self.boolean(level+1))
        return args[0] if len(args)==1 else ('bool',wanted,args,'boolean')
    def render(self,node):
        kind=node[0]
        if kind=='column':return node[1]
        if kind=='literal':return node[1]+('::'+node[-1] if node[-1] not in {'unknown','integer'} else '')
        if kind=='cast':return '('+self.render(node[1])+')::'+node[-1]
        if kind=='call':return node[1]+'('+', '.join(self.render(x) for x in node[2])+')'
        if kind=='null':return '('+self.render(node[1])+(' IS NOT NULL)' if node[2] else ' IS NULL)')
        if kind=='binary':return '('+self.render(node[2])+' '+node[1]+' '+self.render(node[3])+')'
        if kind=='bool':return '('+(' '+node[1]+' ').join(self.render(x) for x in node[2])+')'
        if kind=='in':return '('+self.render(node[1])+' = ANY ((ARRAY['+', '.join(x[1]+'::character varying' for x in node[2])+'])::text[]))'
        raise c.Unsupported('Unsupported source expression node')
    def result(self):
        node=self.boolean()
        if self.cursor!=len(self.tokens):raise c.Unsupported('Unconsumed source expression tokens')
        return self.render(node),node[-1]


def expr(text,columns):return Expression(text,columns).result()[0]


def needs_toast(columns,*,encoding,build):
    if encoding!='UTF8':raise c.Unsupported('Source TOAST compiler supports UTF8 only')
    c.require(build=={'BLCKSZ':8192,'SIZEOF_VOID_P':8,'MAXIMUM_ALIGNOF':8})
    length=0;unknown=False;toastable=False
    for col in columns:
        t=col['definition']['type'];name=t['name'];args=t['arguments'];sql_type(t)
        if name in {'sa.Integer','sa.Boolean','postgresql.UUID','sa.DateTime'}:
            width,align={'sa.Integer':(4,4),'sa.Boolean':(1,1),'postgresql.UUID':(16,1),'sa.DateTime':(8,8)}[name]
        else:
            align=4;toastable=True
            if name=='sa.String':width=args[0]*4+4
            elif name=='sa.Numeric':
                # numeric.c: DEC_DIGITS=4, NumericDigit=int16, HDRSZ=8.
                width=8+((args[0]+6)//4)*2
            else:width=0;unknown=True
        length=(length+align-1)//align*align+width
    if not toastable:return False
    if unknown:return True
    tuple_length=((23+(len(columns)+7)//8+7)//8)*8+((length+7)//8)*8
    threshold=((build['BLCKSZ']-((24+4*4+7)//8)*8)//4)//8*8
    return tuple_length>threshold


def relation_types(schema,table,owner):
    namespace=base.ref('',schema);owned=base.ref('',owner);parent=schema+'.'+table;type_display=table if schema=='public' else parent
    result=[]
    for array in (False,True):
        name=('_' if array else '')+table
        result.append(dict(schema=schema,name=name,properties=dict(typname=name,typnamespace=namespace,typowner=owned,typlen=-1,typbyval=False,
            typtype='b' if array else 'c',typcategory='A' if array else 'C',typispreferred=False,typisdefined=True,typdelim=',',
            typrelid=None if array else base.ref(schema,table,parent),typsubscript='array_subscript_handler' if array else '-',
            typelem=base.ref(schema,table,type_display) if array else None,typarray=None if array else base.ref(schema,'_'+table,type_display+'[]'),
            typinput='array_in' if array else 'record_in',typoutput='array_out' if array else 'record_out',
            typreceive='array_recv' if array else 'record_recv',typsend='array_send' if array else 'record_send',typmodin='-',typmodout='-',
            typanalyze='array_typanalyze' if array else '-',typalign='d',typstorage='x',typnotnull=False,typbasetype=None,typtypmod=-1,typndims=0,
            typcollation=None,typdefaultbin=None,typdefault=None,typacl=None)))
    return result


def records_for(root,phase,prerequisite):
    inputs=m.load_repository_sources(root)[:-1]
    declared=c.parse((Path(root)/MANIFEST).read_bytes(),maximum=32768)['migration_sources']
    c.require(declared==[dict(path=path,sha256=sha256(raw).hexdigest()) for path,raw in inputs])
    extracted=m.extract_sources(inputs,application_only=True)
    if phase=='DEV-BASE':c.require(prerequisite is None);records=[]
    elif phase=='APP-ENTRY':
        c.integer(prerequisite,0,4)
        revision=(None,None,'da34876e4210','7c4e2a91b605','f065d01a7230')[prerequisite]
        records=(p.ledger('alembic_version') if prerequisite else [])+(extracted['application_progress'][revision] if revision else [])
    elif phase in {'APP-F066-PRECOMMIT','APP-F066-PERSISTED','APP-F066-CLOSED'}:
        c.require(prerequisite is None);records=extracted['application']+p.ledger('alembic_version')
    else:raise c.Unsupported('Application-only source maps')
    return inputs,records


def compile_maps(root,*,phase,roles,encoding=None,prerequisite=None):
    """Source fragment for the existing signed context schema; no new profile."""
    build,manifest=load(root);inputs,records=records_for(root,phase,prerequisite)
    if roles is None:raise m.MissingParameter('application_context.roles')
    required={'migrator','inventory_owner','audit_owner','security_owner','application_ledger_owner'}
    for role in sorted(required):
        if role not in roles or roles[role] is None:raise m.MissingParameter('application_context.roles.'+role)
        p.name(roles[role])
    if encoding is None:raise m.MissingParameter('application_context.encoding')
    if encoding!='UTF8':raise c.Unsupported('Source application compiler supports UTF8 only')
    columns={}
    for obj in records:
        if obj['family']=='column':columns.setdefault(tuple(obj['identity'][:2]),[]).append(obj)
    for values in columns.values():values.sort(key=lambda x:x['definition']['position'])
    deparse=dict(constraints=[],indexes=[],index_columns=[],routines=[],triggers=[])
    implicit=[];properties=[];resolver={}
    for table,cols in columns.items():
        owner=p.role_for(next(o for o in records if o['family']=='table' and o['identity']==list(table)),phase,roles)
        properties+=relation_types(*table,owner)
        resolver['.'.join(table)]=[
            m.object_record('composite_type',list(table),base.props(dict(parent='.'.join(table),kind='c',category='C'))),
            m.object_record('array_type',[table[0],'_'+table[1]],base.props(dict(parent='.'.join(table),kind='b',category='A',element_schema=table[0],element_name=table[1])))]
        if needs_toast(cols,encoding=encoding,build=build):
            for kind in ('r','i'):
                identity=['pg_toast','@toast:'+'.'.join(table),kind]
                implicit.append(dict(schema=table[0],relation=table[1],kind=kind,identity=identity))
                resolver['.'.join(table)].append(m.object_record('toast',identity,base.props(dict(parent='.'.join(table),kind=kind,persistence='p',options=None))))
        resolver['.'.join(table)]=p.sort_objects(resolver['.'.join(table)])
    def table_columns(schema,table):return {o['identity'][2]:o['definition']['type'] for o in columns[schema,table]}
    gist_classes=image.extension_member_declarations(image.load_sources(root)[0]) if any(o['family']=='index' and o['definition']['method']=='gist' for o in records) else []
    for obj in records:
        family=obj['family'];identity=obj['identity'];d=obj['definition'];schema=identity[0]
        if family=='constraint':
            cols=table_columns(*identity[:2]);kind=d['kind']
            if kind in {'p','u'}:sql=('PRIMARY KEY' if kind=='p' else 'UNIQUE')+' ('+', '.join(map(ident,d['columns']))+')'
            elif kind=='f':
                refs=[x.split('.') for x in d['references']];c.require(all(x[:2]==refs[0][:2] for x in refs))
                sql='FOREIGN KEY ('+', '.join(map(ident,d['columns']))+') REFERENCES '+'.'.join(map(ident,refs[0][:2]))+'('+', '.join(ident(x[2]) for x in refs)+')'
            elif kind=='c':sql='CHECK ('+expr(d['expression'],cols)+')'
            elif kind=='x':
                parts=[(ident(x['expression']) if x['expression'] in cols else expr(x['expression'],cols))+' WITH '+x['operator'] for x in d['operators']]
                sql='EXCLUDE USING '+d['using']+' ('+', '.join(parts)+')'
                if d['predicate']:sql+=' WHERE ('+expr(d['predicate'],cols)+')'
            else:raise c.Unsupported('Unimplemented source constraint')
            deparse['constraints'].append(dict(schema=schema,name=identity[2],sql=sql,identity=identity,definition=d))
        elif family=='index':
            cols=table_columns(schema,d['table']);rendered=[ident(x) if x in cols else expr(x,cols) for x in d['columns']]
            sql='CREATE '+('UNIQUE ' if d['unique'] else '')+'INDEX '+ident(identity[1])+' ON '+ident(schema)+'.'+ident(d['table'])+' USING '+d['method']+' ('+', '.join(rendered)+')'
            if d['predicate']:sql+=' WHERE '+expr(d['predicate'],cols)
            deparse['indexes'].append(dict(schema=schema,name=identity[1],sql=sql,identity=identity,definition=d))
            for i,column in enumerate(d['columns'],1):
                if column in cols:typ=sql_type(cols[column]);name=column
                else:_,typ=Expression(column,cols).result();name=column.split('(',1)[0]
                if d['method']=='gist':
                    input_type='character varying' if typ.startswith('character varying') else typ
                    matches=[x for x in gist_classes if x['default'] and image.sql_type(x['input_type'][1])==('text' if input_type=='character varying' else input_type)]
                    if matches:typ=matches[0]['storage_type'][1]
                    elif typ!='tstzrange':raise c.Unsupported('Unresolved source GiST key type')
                deparse['index_columns'].append(dict(schema=schema,relation=identity[1],name=name,position=i,type=typ,not_null=False,identity='',generated='',default=None))
    # Preserve the EXACT function dollar body from literal op.execute source,
    # including leading/trailing whitespace; the semantic AST uses stripped body.
    active={tuple(o['identity']) for o in records if o['family']=='routine'}
    for _,raw in inputs:
        tree=ast.parse(raw)
        upgrade=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='upgrade')
        for node in ast.walk(upgrade):
            if not isinstance(node,ast.Call) or ast.unparse(node.func)!='op.execute':continue
            sql=m.literal(node.args[0]);routine=re.search(r'CREATE FUNCTION (inventory|audit)\.([a-z_]+)\(\).*?AS (\$[a-z_]*\$)(.*?)\3',sql,re.S)
            if routine and (routine[1],routine[2],'') in active:
                definition=next(o['definition'] for o in records if o['family']=='routine' and o['identity']==[routine[1],routine[2],''])
                deparse['routines'].append(dict(schema=routine[1],name=routine[2],arguments='',sql=base.function_deparse([routine[1],routine[2],''],definition,body=routine[4])))
    for o in records:
        if o['family']=='trigger':
            d=o['definition'];schema,table,name=o['identity']
            # Trigger event order follows PG's fixed INSERT/DELETE/UPDATE/TRUNCATE
            # bits, not the spelling/order of CREATE TRIGGER in the source.
            events=[x for x in ('INSERT','DELETE','UPDATE','TRUNCATE') if x in d['events']]
            sql='CREATE TRIGGER '+name+' '+d['timing']+' '+' OR '.join(events)+' ON '+schema+'.'+table+' FOR EACH ROW EXECUTE FUNCTION '+'.'.join(d['function'][:2])+'()'
            deparse['triggers'].append(dict(schema=schema,relation=table,name=name,sql=sql))
    for value in deparse.values():value.sort(key=c.canonical)
    return dict(deparse=deparse,implicit_objects=sorted(implicit,key=c.canonical),type_details=sorted(properties,key=c.canonical),resolver_objects=resolver,
        migration_sources=[dict(path=path,sha256=sha256(raw).hexdigest()) for path,raw in inputs],source_manifest=manifest)


def extend_context(root,context,*,phase,roles,encoding=None,prerequisite=None):
    """Add the source maps to the existing adapter context, before observation."""
    fragment=compile_maps(root,phase=phase,roles=roles,encoding=encoding,prerequisite=prerequisite)
    result=deepcopy(context)
    for key in fragment['deparse']:result['deparse'][key]+=fragment['deparse'][key]
    result['implicit_objects']+=fragment['implicit_objects']
    result['fixed_properties']['type_details']+=fragment['type_details']
    for value in result['deparse'].values():value.sort(key=c.canonical)
    result['fixed_properties']['type_details'].sort(key=c.canonical)
    keys={'constraints':lambda r:(r['schema'],r['name']),'indexes':lambda r:(r['schema'],r['name']),
          'index_columns':lambda r:(r['schema'],r['relation'],r['position']),
          'routines':lambda r:(r['schema'],r['name'],r['arguments']),'triggers':lambda r:(r['schema'],r['relation'],r['name'])}
    for key,fn in keys.items():
        values=result['deparse'][key];c.require(len({fn(row) for row in values})==len(values))
    rows=result['fixed_properties']['type_details'];c.require(len({(r['schema'],r['name']) for r in rows})==len(rows))
    rows=result['implicit_objects'];c.require(len({(r['schema'],r['relation'],r['kind']) for r in rows})==len(rows))
    return result
