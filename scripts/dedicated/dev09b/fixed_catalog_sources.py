"""Offline facts from the fixed querytrial image files, never server observations.

This parser is deliberately restricted to the shipped BKI and btree_gist 1.2
through 1.7 scripts. It does not execute SQL, approve artifacts or select target
roles. Source identity/closure and operational approval remain separate.
"""
from hashlib import sha256
from pathlib import Path
import re
import shlex
from . import codec as c
from .migration_catalog import MissingParameter,object_record,foreign_key_triggers,extract_sources

MANIFEST='scripts/dedicated/dev09b/artifacts/pg16-querytrial/sources.candidate.json'
IMAGE='postgres:16-alpine@sha256:f4610795587492cd4fb887c2dc3de301b813278bb6f616992061141b5f15ac36'
EXTENSION_FILES=['extension/btree_gist--1.2.sql']+['extension/btree_gist--1.'+str(i)+'--1.'+str(i+1)+'.sql' for i in range(2,7)]
FILES={'postgres.bki','extension/btree_gist.control','system_functions.sql','extension/plpgsql--1.0.sql','extension/plpgsql.control',*EXTENSION_FILES}


def load_sources(root):
    root=Path(root);doc=c.parse((root/MANIFEST).read_bytes(),maximum=16384)
    c.closed(doc,{'schema_version','status','image','origin','sources'})
    c.integer(doc['schema_version'],1,1)
    c.require(doc['status']=='CANDIDATE_NOT_APPROVED' and doc['image']==IMAGE and doc['origin']=='FIXED_IMAGE_FILES_NOT_DATABASE_OBSERVATIONS')
    base=Path(MANIFEST).parent;result={};seen=set()
    for row in doc['sources']:
        c.closed(row,{'path','image_path','sha256'});c.digest_text(row['sha256'])
        name=str(Path(row['path']).relative_to(base))
        c.require(name in FILES and name not in seen and row['image_path']=='/usr/local/share/postgresql/'+name)
        path=root/row['path'];c.require(not any(p.is_symlink() for p in (path,*path.parents)))
        raw=path.read_bytes();c.require(sha256(raw).hexdigest()==row['sha256'])
        result[name]=raw;seen.add(name)
    c.require(seen==FILES)
    c.require("default_version = '1.7'" in result['extension/btree_gist.control'].decode())
    return result,doc


def bki_catalogs(raw):
    text=raw.decode('utf8');c.require(text.startswith('# PostgreSQL 16\n'))
    output={}
    pattern=r'create (pg_[a-z_]+) [^\n]*\n \(\n(.*?)\n \)\n(.*?)\nclose \1'
    for match in re.finditer(pattern,text,re.S):
        name,header,body=match.groups()
        if name not in {'pg_proc','pg_type','pg_operator','pg_namespace','pg_am','pg_opfamily'}:continue
        columns=re.findall(r'^ ([a-z0-9_]+) = ([a-z0-9_]+)',header,re.M)
        rows=[]
        for line in body.splitlines():
            if not line.startswith('insert ( '):continue
            c.require(line.endswith(' )'))
            tokens=shlex.split(line[9:-2],posix=True);c.require(len(tokens)==len(columns))
            row={}
            for (field,kind),value in zip(columns,tokens):
                if value=='_null_':value=None
                elif kind=='bool':
                    if value=='FLOAT8PASSBYVAL':value={'build_constant':value}
                    else:c.require(value in {'t','f'});value=value=='t'
                elif kind in {'oid','int2','int4','int8'}:
                    if value in {'NAMEDATALEN','SIZEOF_POINTER'}:value={'build_constant':value}
                    else:c.require(re.fullmatch('-?[0-9]+',value) is not None);value=int(value)
                row[field]=value
            rows.append(row)
        output[name]=rows
    c.require({'pg_proc','pg_type','pg_operator','pg_namespace','pg_am','pg_opfamily'}<=set(output))
    return output


def sql_type(name):
    name=' '.join(name.split())
    aliases={'bpchar':'character','varchar':'character varying','varbit':'bit varying','int2':'smallint','int4':'integer','int8':'bigint','float4':'real','float8':'double precision','bool':'boolean',
             'timestamp':'timestamp without time zone','timestamptz':'timestamp with time zone','time':'time without time zone','timetz':'time with time zone','char':'"char"'}
    return aliases.get(name,name)


def builtin_routines(raw,names):
    catalogs=bki_catalogs(raw);types={r['oid']:r['typname'] for r in catalogs['pg_type']}
    result=[]
    for name in names:
        rows=[r for r in catalogs['pg_proc'] if r['proname']==name and r['pronamespace']==11 and r['pronargs']==0]
        c.require(len(rows)==1);r=rows[0]
        c.require(r['prolang']==12 and r['prokind']=='f' and r['proconfig'] is None and r['proargtypes']=='')
        result.append(object_record('routine',['pg_catalog',name,''],dict(returns=sql_type(types[r['prorettype']]),language='internal',body=r['prosrc'],
            security_definer=r['prosecdef'],volatility={'v':'VOLATILE','s':'STABLE','i':'IMMUTABLE'}[r['provolatile']],strict=r['proisstrict'],
            parallel={'s':'SAFE','r':'RESTRICTED','u':'UNSAFE'}[r['proparallel']],config=[])))
    return sorted(result,key=lambda r:tuple(r['identity']))


def split_items(text):
    # The fixed scripts contain no procedural bodies. Quotes protect semicolons
    # and commas; parentheses protect argument lists. Reject unbalanced input.
    result=[];start=0;depth=0;quote=None;i=0
    while i<len(text):
        ch=text[i]
        if quote:
            if ch==quote:
                if i+1<len(text) and text[i+1]==quote:i+=1
                else:quote=None
        elif ch in "'\"":quote=ch
        elif ch=='(':depth+=1
        elif ch==')':depth-=1;c.require(depth>=0)
        elif ch==',' and depth==0:result.append(text[start:i].strip());start=i+1
        i+=1
    c.require(depth==0 and quote is None);result.append(text[start:].strip())
    return result


def extension_declarations(sources):
    """Complete statement census with typed C-routine and base-type declarations.

    Operator/class/family declarations preserve their closed source clauses;
    numeric OIDs and permissions are not inferred or invented from a capture.
    """
    routines={};types={};operators={};classes={};families={};inventory=[]
    for path in EXTENSION_FILES:
        raw=sources[path].decode();clean=re.sub(r'/\*.*?\*/|--[^\n]*|^\\[^\n]*','',raw,flags=re.S|re.M)
        for statement in clean.split(';'):
            statement=' '.join(statement.split())
            if not statement:continue
            inventory.append(dict(source=path,statement=statement))
            function=re.fullmatch(r"CREATE FUNCTION ([a-z0-9_]+)\((.*?)\) RETURNS (.*?) AS 'MODULE_PATHNAME'(?:, '([a-z0-9_]+)')? LANGUAGE C IMMUTABLE STRICT( PARALLEL SAFE)?",statement)
            if function:
                name,args,returns,symbol,parallel=function.groups();args=', '.join(sql_type(x) for x in split_items(args) if x)
                key=(name,args);c.require(key not in routines)
                routines[key]=object_record('routine',['public',name,args],dict(returns=sql_type(returns),language='c',body=symbol or name,
                    security_definer=False,volatility='IMMUTABLE',strict=True,parallel='SAFE' if parallel else 'UNSAFE',config=[]));continue
            alter=re.fullmatch(r'ALTER FUNCTION ([a-z0-9_]+)\((.*?)\) PARALLEL SAFE',statement)
            if alter:
                name,args=alter.groups();key=(name,', '.join(sql_type(x) for x in split_items(args) if x));
                if key not in routines:raise c.Unsupported('Fixed extension ALTER refers to unknown signature '+repr(key))
                routines[key]['definition']['parallel']='SAFE';continue
            type_match=re.fullmatch(r'CREATE TYPE ([a-z0-9_]+) \((.*)\)',statement)
            if type_match:
                name,body=type_match.groups();c.require(name not in types)
                props={}
                for item in split_items(body):
                    pair=re.fullmatch(r'([A-Z]+) = ([a-z0-9_A-Z]+)',item);c.require(pair is not None)
                    key,value=pair.groups();c.require(key not in props);props[key]=value
                c.require({'INTERNALLENGTH','INPUT','OUTPUT'}<=set(props) and set(props)<={'INTERNALLENGTH','INPUT','OUTPUT','STORAGE'})
                types[name]=props;continue
            operator=re.fullmatch(r'CREATE OPERATOR ([^ ]+) \((.*)\)',statement)
            if operator:
                name,body=operator.groups();props={}
                for item in split_items(body):
                    pair=re.fullmatch(r"([A-Z]+) = '?([^']+)'?",item);c.require(pair is not None)
                    key,value=pair.groups();c.require(key not in props);props[key]=value
                c.require(set(props)=={'LEFTARG','RIGHTARG','PROCEDURE','COMMUTATOR'})
                key=(name,sql_type(props['LEFTARG']),sql_type(props['RIGHTARG']));c.require(key not in operators);operators[key]=props;continue
            opclass=re.fullmatch(r'CREATE OPERATOR CLASS ([a-z0-9_]+) (DEFAULT )?FOR TYPE ([a-z0-9_\"]+) USING gist AS (.*)',statement)
            if opclass:
                name,default,input_type,body=opclass.groups();c.require(name not in classes and name not in families)
                clauses=split_items(body);c.require(all(re.match(r'(OPERATOR|FUNCTION|STORAGE)\s',x) for x in clauses))
                classes[name]=dict(name=name,default=bool(default),input_type=sql_type(input_type),clauses=clauses);families[name]=list(clauses);continue
            family=re.fullmatch(r'ALTER OPERATOR FAMILY ([a-z0-9_]+) USING gist ADD (.*)',statement)
            if family:
                name,body=family.groups();c.require(name in families)
                clauses=split_items(body);c.require(all(re.match(r'(OPERATOR|FUNCTION)\s',x) for x in clauses));families[name]+=clauses;continue
            raise c.Unsupported('Unimplemented fixed extension statement in '+path)
    return dict(routines=sorted(routines.values(),key=lambda x:tuple(x['identity'])),types=types,
        operators=[dict(name=k[0],left_type=k[1],right_type=k[2],clauses=v) for k,v in sorted(operators.items())],
        classes=[classes[k] for k in sorted(classes)],families=[dict(name=k,clauses=families[k]) for k in sorted(families)],statements=inventory)


def extension_member_declarations(sources):
    """Resolve every explicit extension member against pinned SQL/BKI sources.

    These are source declarations, not pg_get_* output or inferred catalog
    defaults. Unimplemented PostgreSQL creation semantics remain unsupported.
    """
    ext=extension_declarations(sources);bki=bki_catalogs(sources['postgres.bki'])
    builtin_types={r['oid']:r for r in bki['pg_type'] if r['typnamespace']==11}
    type_names={sql_type(r['typname']):['pg_catalog',r['typname']] for r in builtin_types.values()}
    for name in ext['types']:c.require(name not in type_names);type_names[name]=['public',name]
    def typ(name):
        name=sql_type(name)
        if name not in type_names:raise c.Unsupported('Unresolved source type '+name)
        return type_names[name]
    routines={(x['identity'][1],x['identity'][2]):x['identity'] for x in ext['routines']}
    operators={}
    for r in bki['pg_operator']:
        if r['oprnamespace']!=11 or r['oprleft'] not in builtin_types or r['oprright'] not in builtin_types:continue
        key=(r['oprname'],sql_type(builtin_types[r['oprleft']]['typname']),sql_type(builtin_types[r['oprright']]['typname']))
        c.require(key not in operators);operators[key]=['pg_catalog',*key]
    for r in ext['operators']:
        key=(r['name'],r['left_type'],r['right_type']);c.require(key not in operators)
        operators[key]=['public',*key]
    methods={r['oid']:r['amname'] for r in bki['pg_am']}
    families={(r['opfname'],methods[r['opfmethod']]):['pg_catalog',r['opfname'],methods[r['opfmethod']]] for r in bki['pg_opfamily'] if r['opfnamespace']==11}
    classes={x['name']:x for x in ext['classes']};result=[]
    for family in ext['families']:
        cls=classes[family['name']];input_type=cls['input_type'];members=[];keys=set();storage=None
        for clause in family['clauses']:
            match=re.fullmatch(r'STORAGE ([a-z0-9_]+)',clause)
            if match:
                c.require(storage is None);storage=typ(match[1]);continue
            match=re.fullmatch(r'OPERATOR ([0-9]+) ([^ ()]+)(?: \(([^()]*)\))?(?: FOR ORDER BY pg_catalog\.([a-z0-9_]+))?',clause)
            if match:
                number,name,args,order=match.groups();args=split_items(args) if args is not None else [input_type,input_type]
                c.require(len(args)==2);left,right=[sql_type(x) for x in args];key=(name,left,right)
                if key not in operators:raise c.Unsupported('Unresolved source operator '+repr(key))
                ordering=None
                if order:
                    if (order,'btree') not in families:raise c.Unsupported('Unresolved ordering family '+order)
                    ordering=families[order,'btree']
                member=dict(kind='operator',number=int(number),left=typ(left),right=typ(right),reference=operators[key],ordering_family=ordering)
            else:
                match=re.fullmatch(r'FUNCTION ([0-9]+)(?: \(([^()]*)\))? ([a-z0-9_]+) \(([^()]*)\)',clause)
                if match is None:raise c.Unsupported('Unimplemented extension member clause '+clause)
                number,pair,name,args=match.groups();pair=split_items(pair) if pair is not None else [input_type,input_type]
                c.require(len(pair)==2);left,right=[sql_type(x) for x in pair]
                key=(name,', '.join(sql_type(x) for x in split_items(args)))
                if key not in routines:raise c.Unsupported('Unresolved source support function '+repr(key))
                member=dict(kind='function',number=int(number),left=typ(left),right=typ(right),reference=routines[key])
            c.require(member['number']>0)
            key=(member['kind'],member['number'],tuple(member['left']),tuple(member['right']))
            c.require(key not in keys);keys.add(key);members.append(member)
        c.require(storage is not None)
        result.append(dict(identity=['public',family['name'],'gist'],input_type=typ(input_type),storage_type=storage,
            default=cls['default'],members=sorted(members,key=lambda r:(r['kind'],r['number'],r['left'],r['right']))))
    return result


def source_declarations(root,migrations):
    sources,manifest=load_sources(root)
    from .fixed_catalog_context import load_sources as load_postgres_sources
    _,postgres_manifest=load_postgres_sources(root)
    from .fixed_catalog_context import querytrial_inputs
    trial_inputs,trial_expected=querytrial_inputs(root)
    from .migration_catalog import FK_TRIGGER_FUNCTIONS
    records=extract_sources(migrations,application_only=True)['application']
    from . import own_settings
    c.require(sha256((Path(root)/own_settings.SOURCE).read_bytes()).hexdigest()==own_settings.SOURCE_SHA256)
    return dict(schema_version=1,status='CANDIDATE_NOT_APPROVED',operational_authority=False,
        image=IMAGE,sources=manifest['sources'],postgres_sources=postgres_manifest,
        prepared_querytrial_comparison=dict(profile=trial_inputs['comparison_profile'],scope='DEV-BASE_ONLY',operational_authorization=False,
            inputs_sha256=sha256(c.canonical(trial_inputs,maximum_depth=32)).hexdigest(),expected_sha256=sha256(c.canonical(trial_expected,maximum_depth=32)).hexdigest()),own_session_helper=own_settings.declaration(),own_session_helper_administrative_application='EXTERNAL_TARGET_ACT_REQUIRED',migration_sources=[dict(path=p,sha256=sha256(raw).hexdigest()) for p,raw in migrations],
        foreign_key_triggers=foreign_key_triggers(records),
        foreign_key_routines=builtin_routines(sources['postgres.bki'],[v[0] for v in FK_TRIGGER_FUNCTIONS.values()]),
        extension=extension_declarations(sources),extension_members=extension_member_declarations(sources))
