"""Candidate catalog declarations from pinned PG16 sources, never observations.

Restricted to the already prepared querytrial baseline and btree_gist 1.7.
No operational profile, signature, authority, connection or SQL execution.
"""
from pathlib import Path
from hashlib import sha256
import re
from . import codec as c, fixed_catalog_sources as f, own_settings as helper
from .migration_catalog import object_record

SOURCE_MANIFEST='scripts/dedicated/dev09b/artifacts/pg16-source/sources.candidate.json'
ARCHIVE_SHA256='c1575341fa7bd40f5274ea465b34390f4dc64cdd0770af327005caaeb9f6b7ed'
SOURCE_FILES=frozenset(('COPYRIGHT','src/backend/commands/typecmds.c','src/backend/catalog/pg_type.c','src/backend/utils/adt/ruleutils.c',
'src/backend/catalog/heap.c','src/backend/catalog/index.c','src/backend/commands/tablecmds.c','src/backend/access/heap/heaptoast.c',
'src/include/catalog/pg_type.h','src/backend/utils/adt/acl.c','src/include/pg_config_manual.h','src/backend/utils/adt/format_type.c',
'src/backend/utils/adt/regproc.c','src/include/access/htup_details.h','src/include/access/heaptoast.h'))


def load_sources(root):
    root=Path(root);path=root/SOURCE_MANIFEST;doc=c.parse(path.read_bytes(),maximum=32768)
    c.closed(doc,{'schema_version','status','version','url','archive_sha256','provenance','sources'})
    c.integer(doc['schema_version'],1,1)
    c.require(doc['status']=='CANDIDATE_NOT_APPROVED' and doc['version']=='16.15' and doc['archive_sha256']==ARCHIVE_SHA256
              and doc['url']=='https://ftp.postgresql.org/pub/source/v16.15/postgresql-16.15.tar.bz2'
              and doc['provenance']=='PG_VERSION_AND_PG_SHA256_OF_PINNED_QUERYTRIAL_IMAGE')
    result={}
    for row in doc['sources']:
        c.closed(row,{'path','archive_path','sha256'});c.digest_text(row['sha256'])
        name=row['archive_path'].removeprefix('postgresql-16.15/')
        c.require(name in SOURCE_FILES and name not in result and row['archive_path']=='postgresql-16.15/'+name
                  and row['path']==str(Path(SOURCE_MANIFEST).parent/name))
        p=root/row['path'];c.require(not any(x.is_symlink() for x in (p,*p.parents)))
        raw=p.read_bytes();c.require(sha256(raw).hexdigest()==row['sha256']);result[name]=raw.decode('utf8')
    c.require(set(result)==SOURCE_FILES)
    # Bind this deliberately small compiler to the upstream implementation it
    # describes; source integrity does not by itself confer profile approval.
    for name,fragments in {
        'src/backend/commands/typecmds.c':('alignment = TYPALIGN_INT','storage = TYPSTORAGE_PLAIN','F_ARRAY_SUBSCRIPT_HANDLER','TYPSTORAGE_EXTENDED'),
        'src/backend/catalog/pg_type.c':('isDependentType = isImplicitArray','values[Anum_pg_type_typisdefined - 1] = BoolGetDatum(true)'),
        'src/backend/utils/adt/ruleutils.c':('pg_get_functiondef(PG_FUNCTION_ARGS)',' IMMUTABLE',' PARALLEL SAFE',' SECURITY DEFINER','CREATE OR REPLACE %s %s('),
    }.items():
        c.require(all(fragment in result[name] for fragment in fragments))
    return result,doc


def ref(schema,name,display=None):return dict(schema=schema,name=name,display=name if display is None else display)
def props(values):return dict(properties=[dict(name=k,value=v) for k,v in sorted(values.items())])


def qualified_type(t):
    # format_type.c keyword productions are deliberately NOT schema qualified,
    # even with FORMAT_TYPE_FORCE_QUALIFY. Other types retain their catalog name.
    keywords={'bit','bool','bpchar','float4','float8','int2','int4','int8','numeric','interval',
              'time','timetz','timestamp','timestamptz','varbit','varchar'}
    if t['schema']=='pg_catalog' and t['name'] in keywords:return f.sql_type(t['name'])
    name='"char"' if t['name']=='char' else t['name']
    return t['schema']+'.'+name


def function_deparse(identity,definition,*,library=None,body=None):
    """Closed ruleutils.c pg_get_functiondef subset used by these fixed sources."""
    schema,name,args=identity
    c.require(re.fullmatch('[a-z_][a-z0-9_]*',schema) is not None and re.fullmatch('[a-z_][a-z0-9_]*',name) is not None)
    c.require(definition['language'] in {'c','sql'} and definition['volatility'] in {'IMMUTABLE','STABLE','VOLATILE'}
              and definition['parallel'] in {'SAFE','UNSAFE'} and definition['config'] in ([],['search_path=pg_catalog']))
    text='CREATE OR REPLACE FUNCTION '+schema+'.'+name+'('+args+')\n RETURNS '+definition['returns']+'\n LANGUAGE '+definition['language']+'\n'
    options=''
    if definition['volatility']!='VOLATILE':options+=' '+definition['volatility']
    if definition['parallel']=='SAFE':options+=' PARALLEL SAFE'
    if definition['strict']:options+=' STRICT'
    if definition['security_definer']:options+=' SECURITY DEFINER'
    if options:text+=options+'\n'
    if definition['config']:text+=" SET search_path TO 'pg_catalog'\n"
    body=definition['body'] if body is None else body
    delimiter='$function'
    while delimiter in body:delimiter+='x'
    delimiter+='$'
    c.require(library is None or library in {'$libdir/btree_gist','$libdir/plpgsql'})
    return text+'AS '+('' if library is None else "'"+library+"', ")+delimiter+body+delimiter+'\n'


def declarations(root,*,owner):
    """Full extension properties and source-fixed routine deparse for DEV-BASE.

    Allocated OIDs are represented by catalog-bound symbolic references. No
    table/TOAST deparse is claimed here: this is the prepared empty baseline.
    """
    root=Path(root);_,manifest=load_sources(root);src,image_manifest=f.load_sources(root)
    c.require("default_version = '1.0'" in src['extension/plpgsql.control'].decode() and 'schema = pg_catalog' in src['extension/plpgsql.control'].decode())
    plpgsql=src['extension/plpgsql--1.0.sql'].decode()
    functions=re.findall(r'CREATE FUNCTION ([a-z_]+)\(([^()]*)\) RETURNS ([a-z_]+)\s+(STRICT )?LANGUAGE c AS',plpgsql)
    c.require(functions==[('plpgsql_call_handler','','language_handler',''),('plpgsql_inline_handler','internal','void','STRICT '),('plpgsql_validator','oid','void','STRICT ')])
    c.require('CREATE TRUSTED LANGUAGE plpgsql' in plpgsql and 'ALTER LANGUAGE plpgsql OWNER TO @extowner@;' in plpgsql)
    ext=f.extension_declarations(src);families=f.extension_member_declarations(src);bki=f.bki_catalogs(src['postgres.bki'])
    c.require(owner==helper.ADMIN)  # This target's bootstrap, no environment-wide approval.
    type_rows={r['oid']:r for r in bki['pg_type'] if r['typnamespace']==11}
    types={f.sql_type(r['typname']):ref('pg_catalog',r['typname'],f.sql_type(r['typname'])) for r in type_rows.values()}
    for name in ext['types']:
        types[name]=ref('public',name,name);types['_'+name]=ref('public','_'+name,name+'[]')
    typ=lambda name:types[f.sql_type(name)]
    namespace=ref('','public');owned=ref('',owner);method=ref('','gist')
    fixed=dict(extension_properties=[],operator_members=[],type_details=[],
               template_extensions=[dict(name='plpgsql',version='1.0',schema='pg_catalog',owner=owner)],
               session_settings=dict(transaction_isolation='read committed',transaction_read_only='on'))
    members=[]
    def member_property(identity,catalog,value,extension='btree_gist'):
        fixed['extension_properties'].append(dict(extension=extension,identity=identity,catalog='pg_catalog.'+catalog,properties=value))
    for routine in ext['routines']:
        name,args=routine['identity'][1:]
        # pg_identify_object always qualifies user argument types.
        arg_names=[a for a in f.split_items(args) if a]
        full_args=','.join(qualified_type(typ(a)) for a in arg_names)
        member_property('public.'+name+'('+full_args+')','pg_proc',None)
        members.append(routine)
    for name,decl in ext['types'].items():
        for array in (False,True):
            current=('_' if array else '')+name
            values=dict(typname=current,typnamespace=namespace,typowner=owned,typlen=-1 if array or decl['INTERNALLENGTH']=='VARIABLE' else int(decl['INTERNALLENGTH']),
                typbyval=False,typtype='b',typcategory='A' if array else 'U',typispreferred=False,typisdefined=True,typdelim=',',typrelid=None,
                typsubscript='array_subscript_handler' if array else '-',typelem=typ(name) if array else None,typarray=None if array else typ('_'+name),
                typinput='array_in' if array else decl['INPUT'],typoutput='array_out' if array else decl['OUTPUT'],
                typreceive='array_recv' if array else '-',typsend='array_send' if array else '-',typmodin='-',typmodout='-',
                typanalyze='array_typanalyze' if array else '-',typalign='i',typstorage='x' if array or decl.get('STORAGE')=='EXTENDED' else 'p',
                typnotnull=False,typbasetype=None,typtypmod=-1,typndims=0,typcollation=None,typdefaultbin=None,typdefault=None,
                typacl=None if array else [owner+'=U/'+owner])
            fixed['type_details'].append(dict(schema='public',name=current,properties=values))
            if array:
                definition=props(dict(parent='public.'+name,kind='b',category='A',element_schema='public',element_name=name))
                members.append(object_record('array_type',['public',current],definition))
            else:
                member_property('public.'+name,'pg_type',values)
                definition=props(dict(category='U',length=values['typlen'],by_value=False,alignment='i',storage=values['typstorage'],
                    input=values['typinput'],output=values['typoutput'],receive='-',send='-',delimiter=',',preferred=False,not_null=False,default=None,collation=None))
                members.append(object_record('base_type',['public',name],definition))
    for family in families:
        name=family['identity'][1];famref=ref('public',name,'public.'+name+' USING gist')
        family_props=dict(opfmethod=method,opfname=name,opfnamespace=namespace,opfowner=owned)
        member_property('public.'+name+' USING gist','pg_opfamily',family_props)
        cls=dict(opcmethod=method,opcname=name,opcnamespace=namespace,opcowner=owned,opcfamily=famref,
            opcintype=typ(family['input_type'][1]),opcdefault=family['default'],opckeytype=typ(family['storage_type'][1]))
        member_property('public.'+name+' USING gist','pg_opclass',cls)
        operators=[];functions=[]
        for item in family['members']:
            left=typ(item['left'][1]);right=typ(item['right'][1]);r=item['reference']
            if item['kind']=='operator':
                opname=r[1];opref=ref(r[0],opname,opname+'('+typ(r[2])['display']+','+typ(r[3])['display']+')')
                order=item['ordering_family'];ordering=None if order is None else ref(order[0],order[1],order[0]+'.'+order[1]+' USING '+order[2])
                values=dict(amopfamily=famref,amoplefttype=left,amoprighttype=right,amopstrategy=item['number'],amoppurpose='s' if order is None else 'o',
                            amopopr=opref,amopmethod=method,amopsortfamily=ordering)
                operators.append(values)
            else:
                values=dict(amprocfamily=famref,amproclefttype=left,amprocrighttype=right,amprocnum=item['number'],amproc=r[1]);functions.append(values)
            fixed['operator_members'].append(dict(schema='public',family=name,kind=item['kind'],properties=values))
        operators.sort(key=c.canonical);functions.sort(key=c.canonical)
        members.append(object_record('opclass',['public',name],props(dict(method='gist',family_schema='public',family_name=name,
            input_type=cls['opcintype']['display'],key_type=cls['opckeytype']['display'],default=family['default']))))
        members.append(object_record('opfamily',['public',name],props(dict(method='gist',operators=c.canonical(operators).decode(),functions=c.canonical(functions).decode()))))
    routines={tuple(r['identity'][1:]):r for r in ext['routines']}
    for op in ext['operators']:
        name,left,right=op['name'],op['left_type'],op['right_type'];function=op['clauses']['PROCEDURE']
        routine=routines[function,left+', '+right]
        display=name+'('+typ(left)['display']+','+typ(right)['display']+')'
        value=dict(oprname=name,oprnamespace=namespace,oprowner=owned,oprkind='b',oprcanmerge=False,oprcanhash=False,oprleft=typ(left),oprright=typ(right),
            oprresult=typ(routine['definition']['returns']),oprcom=ref('public',name,display),oprnegate=None,oprcode=function,oprrest='-',oprjoin='-')
        identity='public.'+name+'('+qualified_type(typ(left))+','+qualified_type(typ(right))+')'
        member_property(identity,'pg_operator',value)
        members.append(object_record('operator',['public',name,left+','+right],props(dict(left_type=left,right_type=right,result_type=routine['definition']['returns'],
            function=function,commutator=display,negator=None,restriction='-',join='-',merges=False,hashes=False))))
    # Template plpgsql members are specified by its installation script/BKI.
    # Its functions are selected independently by the collector, never part of
    # the public managed-routine deparse inventory.
    for name,args in [('plpgsql_call_handler',''),('plpgsql_inline_handler','internal'),('plpgsql_validator','oid')]:
        member_property('pg_catalog.'+name+'('+('pg_catalog.'+args if args else '')+')','pg_proc',None,'plpgsql')
    member_property('plpgsql','pg_language',None,'plpgsql')
    body=re.search(r'AS \$body\$(.*?)\$body\$;', (root/helper.SOURCE).read_text(),re.S)
    c.require(body is not None and body[1].strip()==helper.BODY)
    forms=[dict(schema=r['identity'][0],name=r['identity'][1],arguments=r['identity'][2],sql=function_deparse(r['identity'],r['definition'],library='$libdir/btree_gist')) for r in ext['routines']]
    forms.append(dict(schema='public',name=helper.IDENTITY[1],arguments='',sql=function_deparse(helper.IDENTITY,helper.OBJECT['definition'],body=body[1])))
    for values in fixed.values():
        if type(values) is list:values.sort(key=c.canonical)
    return dict(fixed_properties=fixed,deparse=dict(constraints=[],indexes=[],index_columns=[],routines=forms,triggers=[]),implicit_objects=[],
                extension_objects=sorted(members,key=lambda x:(x['family'],tuple(x['identity']))),source_manifest=manifest,image_manifest=image_manifest)


def querytrial_inputs(root):
    """A fixed-source, target-scoped TECHNICAL baseline, not a signed profile.

    All source inputs are read here before collection. A different target,
    migration phase, principal, locale or new helper needs another explicit
    declaration; no server observations are accepted by this compiler.
    """
    from . import physical as p, detailed_catalog as d
    root=Path(root);decl=declarations(root,owner=helper.ADMIN)
    target=dict(project='livenetv2-dev09b-querytrial',database=helper.DATABASE,system_identifier=helper.TARGET_SID,image=f.IMAGE)
    paths={f.MANIFEST,SOURCE_MANIFEST,helper.SOURCE,'scripts/postgres/dev09b_querytrial_schemas.proposed.sql',
           'scripts/postgres/dev09b_querytrial_launcher.py','compose.dev09b-querytrial.yaml',
           'scripts/dedicated/dev09b/fixed_catalog_sources.py','scripts/dedicated/dev09b/fixed_catalog_context.py',
           'scripts/dedicated/dev09b/physical.py','scripts/dedicated/dev09b/migration_catalog.py','scripts/dedicated/dev09b/detailed_catalog.py',
           'scripts/dedicated/dev09b/codec.py','backend/migrations/dev09b_catalog_adapter.py','backend/migrations/dev09b_inspection.py',
           'backend/migrations/dev09b_inspection_queries.py','backend/migrations/dev09b_detailed_queries.py','scripts/postgres/dev09b_detailed_querytrial.py'}
    paths.update(r['path'] for r in decl['source_manifest']['sources']);paths.update(r['path'] for r in decl['image_manifest']['sources'])
    source_refs=[dict(path=name,sha256=sha256((root/name).read_bytes()).hexdigest()) for name in sorted(paths)]
    # The locale values were expressly approved for this disposable, not inferred
    # from LANG or from its capture. Session options come from probe preparation
    # and the READ ONLY collector's SET statements. READ COMMITTED is explicit.
    distribution=dict(image_sha256=f.IMAGE.split('sha256:')[1],server_version_num=160015,template_name='template1',encoding='UTF8',
        collation='en_US.utf8',ctype='en_US.utf8',locale_provider='libc',settings=dict(search_path='pg_catalog, public',
        session_replication_role='origin',row_security='on',standard_conforming_strings='on',shared_preload_libraries='',
        session_preload_libraries='',local_preload_libraries=''),**{k:source_refs for k in ('template_sources','alembic_sources','sqlalchemy_sources')})
    # This technical baseline has no Alembic/SQLAlchemy-created objects. These
    # lists describe the collector/compiler sources, not approval of execution.
    parameter_hash=sha256(c.canonical(dict(scope='QUERYTRIAL_PREPARED_SOURCE_BASELINE_V1',target=target,distribution=distribution))).hexdigest()
    metadata=dict(target_binding_sha256=sha256(c.canonical(target)).hexdigest(),parameters_sha256=parameter_hash,sources=source_refs,
        distribution_sources={k:distribution[k] for k in ('template_sources','alembic_sources','sqlalchemy_sources')},
        image_sha256=distribution['image_sha256'],template_name=distribution['template_name'],extension_sources=source_refs,
        role_bindings=dict(migrator=None,inspector=helper.PROBE),request_id=None,approval_id=None,attempt_id=None)
    context=dict(metadata=metadata,**{k:decl[k] for k in ('fixed_properties','deparse','implicit_objects')},approved_helpers=[helper.declaration()])
    system=f.builtin_routines(f.load_sources(root)[0]['postgres.bki'],['pg_control_system','RI_FKey_check_ins','RI_FKey_check_upd','RI_FKey_noaction_del','RI_FKey_noaction_upd'])
    # plpgsql--1.0.sql: three C functions, plus trusted language. Function owner
    # remains bootstrap admin; ALTER LANGUAGE sets the same extension owner.
    for name,args,returns,strict in [('plpgsql_call_handler','','language_handler',False),('plpgsql_inline_handler','internal','void',True),('plpgsql_validator','oid','void',True)]:
        system.append(object_record('routine',['pg_catalog',name,args],dict(returns=returns,language='c',body=name,
            security_definer=False,volatility='VOLATILE',strict=strict,parallel='UNSAFE',config=[])))
    system.append(object_record('language',['plpgsql'],props(dict(trusted=True,handler='plpgsql_call_handler()',inline='plpgsql_inline_handler(internal)',validator='plpgsql_validator(oid)'))))
    system.extend([helper.OBJECT,helper.ROLE_OBJECT]);system=p.sort_objects(system)
    sysowned=[];sysacl=[]
    for obj in system:
        if obj['family']=='role':continue
        owner=helper.OWNER if obj==helper.OBJECT else helper.ADMIN
        base=dict(family=obj['family'],identity=obj['identity'])
        sysowned.append(dict(**base,owner=owner))
        if obj==helper.OBJECT:grants=[p.grant(helper.PROBE,'EXECUTE')]
        elif obj['family']=='language':grants=[p.grant('PUBLIC','USAGE')]
        elif obj['identity'][1]=='pg_control_system':grants=[p.grant(helper.PROBE,'EXECUTE')]
        else:grants=[p.grant('PUBLIC','EXECUTE')]
        sysacl.append(dict(**base,grants=grants))
    managed=p.sort_objects([object_record('schema',[name],{}) for name in ('inventory','audit','security')])
    ownership=[dict(family='schema',identity=o['identity'],owner='dev09b_trial_'+o['identity'][0]+'_owner') for o in managed]
    acls=[dict(family='schema',identity=o['identity'],grants=[]) for o in managed]
    roles=[]
    for name in [helper.ADMIN,helper.PROBE,*[x['owner'] for x in ownership]]:
        admin=name==helper.ADMIN
        roles.append(dict(name=name,login=admin or name==helper.PROBE,superuser=admin,createdb=admin,createrole=admin,replication=admin,bypassrls=admin,inherit=admin))
    extobjects=decl['extension_objects'];extacls=[]
    for obj in extobjects:
        # Implicit arrays have typacl NULL (pg_type.c dependent types). The SQL
        # intentionally revokes only DIRECT members, so PUBLIC USAGE remains
        # visible in acldefault for those arrays. No grant is executed here.
        grants=[p.grant('PUBLIC','USAGE')] if obj['family']=='array_type' else []
        extacls.append(dict(family=obj['family'],identity=obj['identity'],grants=grants))
    expected=dict(schema_version=2,profile='dev09b-prepared-dev-base-v2',phase='DEV-BASE',
        target_binding_sha256=metadata['target_binding_sha256'],parameters_sha256=parameter_hash,sources=source_refs,distribution=distribution,
        database_owner=helper.ADMIN,public_owner='pg_database_owner',system_objects=system,system_ownership=sysowned,system_acls=sysacl,
        system_memberships=[],system_default_acl=[],managed_objects=managed,ownership=ownership,acls=acls,roles=sorted(roles,key=lambda r:r['name']),memberships=[],
        database_acl=[p.grant(helper.PROBE,'CONNECT')],public_acl=[p.grant('PUBLIC','USAGE')],inspection_column_grants=[],temporary_rights=[],
        control_system_acl=[p.grant(helper.PROBE,'EXECUTE')],ledgers=[dict(chain=x,presence='ABSENT',revisions=[]) for x in ('application','security')],
        extensions=[dict(name='btree_gist',version='1.7',schema='public',owner=helper.ADMIN,sources=source_refs,members=extobjects,
            ownership=[dict(family=o['family'],identity=o['identity'],owner=helper.ADMIN) for o in extobjects],acls=extacls,acl=[])])
    # Reuse the phase shape/order validator; no PhaseExpectation or authorization
    # is fabricated for the operational eleven-role profile.
    for key in ('system_ownership','system_acls'):expected[key].sort(key=lambda r:(r['family'],tuple(r['identity'])))
    p.validate_snapshot(expected)
    selections=dict(role_names=[helper.ADMIN,helper.PROBE,*[x['owner'] for x in ownership]],
        system_routines=['.'.join(o['identity'][:2]) for o in system if o['family']=='routine' and o['identity'][0]=='pg_catalog'],language_names=['plpgsql'])
    inputs=dict(schema_version=1,status='PROPOSED_READ_ONLY_INPUTS',collector_id='querytrial-prepared-source-baseline',selections=selections,
        context=context,approved_helpers=[helper.declaration()],comparison_profile='querytrial-prepared-source-baseline-v1')
    return inputs,expected


def compare_querytrial_baseline(root,inputs,observation):
    """Exact technical equality only; cannot be passed as operational evidence."""
    from . import detailed_catalog as d, physical as p
    fixed,expected=querytrial_inputs(root)
    c.require(c.canonical(inputs,maximum_depth=32)==c.canonical(fixed,maximum_depth=32))
    normalized=d.normalize_observations(observation);p.validate_snapshot(expected)
    c.require(c.canonical(normalized,maximum_depth=32)==c.canonical(expected,maximum_depth=32))
    return 'SOURCE_BASELINE_EQUAL_TECHNICAL_ONLY'
