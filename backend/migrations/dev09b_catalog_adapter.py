"""Strict PG16 result adapter for application-f066-catalog-v2, no SQL execution.

Rows are observations; source metadata and fixed-property declarations are
separate, previously fixed inputs. Missing coverage is a refusal, not a projection
silently presented as complete. Fixtures are not evidence of PostgreSQL execution.
"""
from dataclasses import dataclass
from types import MappingProxyType
import re

from . import dev09b_prerequisites as h
from .dev09b_inspection_queries import QUERIES
from .dev09b_detailed_queries import DETAIL_QUERIES
from .dev09b_inspection_support import row_mapping
from scripts.dedicated.dev09b import codec as c,physical as p,detailed_catalog as d
from scripts.dedicated.dev09b.migration_catalog import MissingParameter


# Every historical query has an explicit consumer/absence check. No catch-all skip.
MATRIX=MappingProxyType({
 'identity':'collector binding before/after', 'privileges':'effective privilege refusal',
 'memberships':'effective memberships refusal','schemas':'schema/ownership/public_owner',
 'schema_acl':'schema ACL/public_acl','extension':'extension header',
 'extension_members':'extension completeness census','namespace_objects':'namespace completeness census',
 'relations':'table/ownership; unsupported relation kinds refuse',
 'columns':'column/type/default','constraints':'constraint (fixed deparse resolution)',
 'indexes':'index (fixed deparse resolution)','routines':'routine census/config/owner',
 'triggers':'trigger census (internal unresolved triggers refuse)',
 'types':'base/composite/array type','policies':'absence required','rules':'absence required',
 'object_acl':'expanded ACL; ownership separate','default_acl':'absence required',
 'settings':'distribution/settings, complete nominal coverage',
 'sequences':'absence required','inheritance':'absence required',
 'extension_properties':'operator/opclass/opfamily, resolved references/full property check',
 'operator_members':'opfamily operators/functions/full property check','column_acl':'column grants',
 'executable_definers':'absence required','extension_acl':'extension ACL cross-check',
 'database_acl':'database owner/ACL','toast':'TOAST, fixed persistence property required',
 'type_details':'type details/resolved references/full property check',
 'enum_labels':'absence required','ranges':'absence required','default_acl_objects':'absence required',
})
ABSENT=('policies','rules','sequences','inheritance','default_acl','default_acl_objects','enum_labels','ranges','executable_definers')
PROPERTY_QUERIES=('extension_properties','operator_members','type_details')
BOOL_FIELDS=set('login superuser createdb createrole replication bypassrls inherit admin set strict security_definer row internal grant_option trusted deferrable initially_deferred constraint_deferrable constraint_initially_deferred validated opposite_relation no_arguments no_condition no_columns no_transition direct_namespace'.split())
OID_FIELDS={
 'typnamespace':'pg_namespace','typowner':'pg_roles','typrelid':'pg_class','typelem':'pg_type',
 'typarray':'pg_type','typbasetype':'pg_type','typcollation':'pg_collation',
 'oprnamespace':'pg_namespace','oprowner':'pg_roles','oprleft':'pg_type','oprright':'pg_type',
 'oprresult':'pg_type','oprcom':'pg_operator','oprnegate':'pg_operator',
 'opcmethod':'pg_am','opcnamespace':'pg_namespace','opcowner':'pg_roles','opcfamily':'pg_opfamily',
 'opcintype':'pg_type','opckeytype':'pg_type','opfmethod':'pg_am','opfnamespace':'pg_namespace','opfowner':'pg_roles',
 'amopfamily':'pg_opfamily','amoplefttype':'pg_type','amoprighttype':'pg_type','amopopr':'pg_operator',
 'amopmethod':'pg_am','amopsortfamily':'pg_opfamily','amprocfamily':'pg_opfamily',
 'amproclefttype':'pg_type','amprocrighttype':'pg_type',
}


@dataclass(frozen=True)
class ConvertedObservation:
    rows_json: bytes
    collector_id: str
    collector_binding_json: bytes
    # No operational attestation/capability or implicit independent confirmation.


def require(ok,code='DETAILED_RESULT_DIVERGENCE'):h.require(ok,code)


def supplemental_rows(name,values):
    query=DETAIL_QUERIES[name]
    require(type(values) is list and len(values)<=query.maximum,'SUPPLEMENTAL_COVERAGE:'+name)
    result=[]
    for value in values:
        r=row_mapping(value);require(set(r)==set(query.fields),'SUPPLEMENTAL_FIELDS:'+name)
        for key,cell in r.items():
            if name=='helper_security_flags':require(type(cell) is bool,'HELPER_SECURITY_FLAG')
            elif name=='helper_owner_role' and key=='connection_limit':require(type(cell) is int and cell>=-1,'HELPER_ROLE_LIMIT')
            elif name=='helper_owner_role' and key=='valid_until':require(cell is None or type(cell) is str,'HELPER_ROLE_VALID_UNTIL')
            elif key in BOOL_FIELDS:require(type(cell) is bool,'SUPPLEMENTAL_BOOL:'+name+'.'+key)
            elif name=='own_preload_settings' and key=='setting':require(cell is None or type(cell) is str,'SUPPLEMENTAL_SETTING')
            elif key in {'oid','relation_oid','type_oid','array_oid','backend_pid'}:require(type(cell) is int and cell>0,'SUPPLEMENTAL_OID:'+name+'.'+key)
            elif key in {'events','config','options'}:require(cell is None or type(cell) is list and all(type(v) is str for v in cell))
            else:require(type(cell) is str,'SUPPLEMENTAL_STRING:'+name+'.'+key)
        result.append(r)
    result.sort(key=d.encode)
    require(len({d.encode(r) for r in result})==len(result),'SUPPLEMENTAL_DUPLICATE:'+name)
    return result


def needed_references(batch):
    result=set()
    for name in PROPERTY_QUERIES:
        for row in batch[name]:
            for key,value in (row.get('properties') or {}).items():
                if key in OID_FIELDS:
                    require(type(value) is int and value>=0,'REFERENCE_TYPE:'+key)
                    if value:result.add((OID_FIELDS[key],value))
    return sorted(result)


def needed_oids(batch):return sorted({oid for catalog,oid in needed_references(batch)})


def keyed(values,key,label):
    result={}
    for row in values:
        identity=key(row);require(identity not in result,'DUPLICATE_IDENTITY:'+label)
        result[identity]=row
    return result


def data_type(raw):
    simple={'integer':'sa.Integer','text':'sa.Text','boolean':'sa.Boolean','uuid':'postgresql.UUID',
            'jsonb':'postgresql.JSONB','timestamp with time zone':'sa.DateTime'}
    if raw in simple:return dict(name=simple[raw],arguments=[])
    match=re.fullmatch(r'character varying\(([1-9][0-9]*)\)',raw)
    if match:return dict(name='sa.String',arguments=[int(match[1])])
    match=re.fullmatch(r'numeric\(([1-9][0-9]*),([0-9]+)\)',raw)
    if match:return dict(name='sa.Numeric',arguments=list(map(int,match.groups())))
    raise c.Unsupported('Unimplemented PostgreSQL type representation')


def default(raw):
    if raw is None:return None
    if raw in {'now()','true','1',"'{}'::jsonb"}:return raw
    if raw in {"'active'::character varying","'active'::text","'active'"}:return "'active'"
    raise c.Unsupported('Unimplemented PostgreSQL default representation')


def ace(row):
    value={k:row[k] for k in ('grantee','privilege','grant_option')};p.ace(value);return value


def reference_map(details):
    refs=keyed(details['reference_catalog'],lambda r:(r['catalog'],r['oid']),'reference_catalog')
    def resolve(catalog,oid,nullable=False):
        require(type(oid) is int and oid>=0,'REFERENCE_OID')
        if oid==0 and nullable:return None
        if (catalog,oid) not in refs:raise MissingParameter('sql_reference.'+catalog+'.'+str(oid))
        return refs[(catalog,oid)]
    return resolve


def resolved_properties(batch,resolve):
    """All property cells are checked, including those not in the phase projection.

    Source-fixed declarations use symbolic references, so incidental OIDs are not
    learned as expected values or silently discarded. Missing declarations refuse.
    """
    output={}
    for name in PROPERTY_QUERIES:
        output[name]=[]
        for row in batch[name]:
            value={k:v for k,v in row.items() if k!='properties'}
            props=row['properties']
            if props is not None:
                props=dict(props)
                for key,cell in props.items():
                    if key in OID_FIELDS:
                        ref=resolve(OID_FIELDS[key],cell,nullable=True)
                        props[key]=None if ref is None else {k:ref[k] for k in ('schema','name','display')}
            value['properties']=props;output[name].append(value)
        output[name].sort(key=d.encode)
    return output


def convert_results(batch,details,context,*,phase,collector_id,session=None,ledger_rows=None):
    """Convert complete SQL batches; NO expected phase snapshot argument.

    context is authenticated source/provenance, never inferred from this batch:
    header metadata, fixed_properties and deparse declarations must be fixed
    before collection and bound to the inspection contract/source inventory.
    """
    from .dev09b_inspection import rows
    require(set(MATRIX)==set(QUERIES),'ADAPTER_QUERY_COVERAGE')
    require(type(batch) is dict and set(batch)==set(QUERIES),'MISSING_OR_EXTRA_QUERY')
    require(type(details) is dict and set(details)==set(DETAIL_QUERIES),'MISSING_OR_EXTRA_SUPPLEMENT')
    c.require(type(context) is dict)
    c.closed(context,{'metadata','fixed_properties','deparse','implicit_objects'}|({'approved_helpers'} if 'approved_helpers' in context else set()))
    details={name:supplemental_rows(name,details[name]) for name in DETAIL_QUERIES}
    helper_facts={name:[row_mapping(v) for v in batch[name]] for name in ('identity','routines','object_acl','executable_definers')}
    helpers=context.get('approved_helpers',[])
    require(type(helpers) is list and len(helpers)<=1,'Fixed helper scope')
    if helpers:
        from scripts.dedicated.dev09b import own_settings
        own_settings.validate(helpers[0]);own_settings.verify_observed(helper_facts,details,helpers[0])
        helper_rows=keyed(details['helper_preload_settings'],lambda r:r['name'],'helper_preload_settings')
        require((set(helper_rows)==own_settings.NAMES if helper_facts['identity'][0]['current_user'] in own_settings.callers(helpers[0]) else not helper_rows) and all(type(r['backend_pid']) is int and r['backend_pid']==row_mapping(batch['identity'][0])['pid'] for r in helper_rows.values()),'HELPER_SESSION_BINDING')
    else:
        require(not details['helper_preload_settings'],'UNEXPECTED_HELPER_OBSERVATION');helper_rows={}
    direct=keyed(details['own_preload_settings'],lambda r:r['name'],'own_preload_settings')
    require(set(direct)=={'shared_preload_libraries','session_preload_libraries'},'OWN_PRELOAD_COVERAGE')
    for key,value in helper_rows.items():
        require(direct[key]['setting'] is None or direct[key]['setting']==value['setting'],'HELPER_SETTING_DIVERGENCE')
        direct[key]={'name':key,'setting':value['setting']}
    require(set(direct)=={'shared_preload_libraries','session_preload_libraries'},'OWN_PRELOAD_COVERAGE')
    settings_rows=[row_mapping(x) for x in batch['settings']]
    for row in settings_rows:
        if row['name'] in direct:
            measured=direct[row['name']]['setting']
            if measured is None:raise MissingParameter('own_session.'+row['name']+'.trusted_observation')
            require(row['setting'] is None or row['setting']==measured,'OWN_PRELOAD_DIVERGENCE')
        # Preserve exact nominal validation below, including missing/duplicate
        # names. Only an actual same-session observation fills a hidden value.
    settings_rows=[{**r,'setting':direct[r['name']]['setting']} if r['name'] in direct else r for r in settings_rows]
    observed={name:rows(name,settings_rows if name=='settings' else [row_mapping(x) for x in batch[name]]) for name in QUERIES}
    require(phase in d.PHASES.values(),'APPLICATION_PHASE_ONLY');c.identifier(collector_id)
    meta=context['metadata'];c.closed(meta,{'target_binding_sha256','parameters_sha256','sources','distribution_sources',
                                         'image_sha256','template_name','extension_sources','role_bindings','request_id','approval_id','attempt_id'})
    for key in ('target_binding_sha256','parameters_sha256','image_sha256'):c.digest_text(meta[key])
    from scripts.dedicated.dev09b.layers import sources
    sources(meta['sources'])
    require(bool(meta['sources']),'SOURCE_PROVENANCE_REQUIRED')
    c.closed(meta['distribution_sources'],{'template_sources','alembic_sources','sqlalchemy_sources'})
    for values in meta['distribution_sources'].values():sources(values);require(bool(values),'DISTRIBUTION_PROVENANCE_REQUIRED')
    require(not details['casts'],'UNSUPPORTED_NONEMPTY_FAMILY:casts')
    identities=keyed(details['object_identities'],lambda r:(r['identify_type'],r['identify_identity']),'object_identities')
    identity_keys={}
    for key,row in identities.items():
        family=row['family']
        require(family in {'routine','type','relation','constraint','trigger','operator','opclass','opfamily','extension','language'},'UNSUPPORTED_IDENTITY_FAMILY')
        require(row['relation']!='' if family in {'constraint','trigger'} else row['relation']=='','OBJECT_LINK_PARENT_FIELD')
        if family not in {'routine','operator'}:require(row['arguments']=='','OBJECT_LINK_ARGUMENT_FIELD')
        allowed={'routine':{'function'},'type':{'type'},'relation':{'table','index'},'constraint':{'table constraint'},'trigger':{'trigger'},'operator':{'operator'},'opclass':{'operator class'},'opfamily':{'operator family'},'extension':{'extension'},'language':{'language'}}
        require(row['identify_type'] in allowed[family],'OBJECT_LINK_FAMILY')
        if family=='language':alias=('language',row['name'])
        elif family=='trigger':alias=('trigger',row['schema'],row['relation'],row['name'])
        elif family=='routine':alias=('routine',row['schema'],row['name'],row['arguments'])
        elif family=='operator':alias=('operator',row['schema'],row['name'],row['arguments'])
        else:alias=(family,row['schema'],row['name'])
        require(alias not in identity_keys,'DUPLICATE_OBJECT_LINK')
        identity_keys[alias]=row
    identity=observed['identity'];require(len(identity)==1,'ONE_COLLECTOR_IDENTITY')
    binding=identity[0]
    require(len(observed['privileges'])==1 and all(v is False for v in observed['privileges'][0].values()),'EXCESSIVE_EFFECTIVE_PRIVILEGES')
    require(not any(r[k] for r in observed['memberships'] for k in ('member','inherited','can_set')),'EFFECTIVE_MEMBERSHIP')
    for name in ABSENT:require((bool(helpers) and name=='executable_definers') or not observed[name],'UNSUPPORTED_NONEMPTY_FAMILY:'+name)
    require({(r['catalog'],r['oid']) for r in details['reference_catalog']}==set(needed_references(observed)),'REFERENCE_COVERAGE')
    resolve=reference_map(details)
    properties=resolved_properties(observed,resolve)
    c.closed(context['fixed_properties'],set(PROPERTY_QUERIES)|{'template_extensions','session_settings'})
    for name in PROPERTY_QUERIES:
        require(d.encode(properties[name])==d.encode(context['fixed_properties'][name]),'FIXED_PROPERTY_DIVERGENCE:'+name)
    require(len(details['environment'])==1,'ONE_DATABASE_ENVIRONMENT')
    env=details['environment'][0]
    require(env['database']==binding['database'],'DATABASE_IDENTITY')
    require(env['locale_provider']=='c','UNSUPPORTED_LOCALE_PROVIDER')
    settings={r['name']:r['setting'] for r in observed['settings']}
    session_settings=context['fixed_properties']['session_settings']
    c.closed(session_settings,{'transaction_isolation','transaction_read_only'})
    require(d.encode({k:settings[k] for k in session_settings})==d.encode(session_settings),'SESSION_SETTINGS_DIVERGENCE')
    distribution=dict(image_sha256=meta['image_sha256'],server_version_num=binding['server_version_num'],
        template_name=meta['template_name'],encoding=env['encoding'],collation=env['collation'],ctype=env['ctype'],locale_provider='libc',
        settings={k:settings[k] for k in ('search_path','session_replication_role','row_security','standard_conforming_strings',
                  'shared_preload_libraries','session_preload_libraries','local_preload_libraries')},**meta['distribution_sources'])
    require(settings['lc_collate']==env['collation'] and settings['lc_ctype']==env['ctype'] and settings['server_encoding']==env['encoding'],'DATABASE_SETTINGS_CROSSCHECK')
    objects=[];owners={};aliases={};extension_objects={};extension_names={}
    schema_names={'inventory','audit','security','public'}
    def add(section,family,identity,definition,owner=None,alias=None,extension=None):
        obj=dict(family=family,identity=identity,definition=definition);p.shape_object(obj)
        key=(family,tuple(identity));require(key not in owners,'DUPLICATE_NORMALIZED_OBJECT')
        owners[key]=owner
        if section:objects.append(dict(section=section,**obj))
        if alias:
            require(alias not in aliases,'AMBIGUOUS_SQL_OBJECT');aliases[alias]=key
        if extension:
            extension_objects.setdefault(extension,[]).append(obj);extension_names[key]=extension
        return key
    schemas=keyed(observed['schemas'],lambda r:r['name'],'schemas')
    for name in schema_names:require(name in schemas,'MISSING_MANAGED_SCHEMA:'+name)
    for name in ('inventory','audit','security'):add('managed','schema',[name],{},schemas[name]['owner'],('schema',name))
    relations=keyed(observed['relations'],lambda r:(r['schema'],r['name']),'relations')
    for (schema,name),r in relations.items():
        require(schema in schema_names,'RELATION_SCOPE')
        if r['kind']=='i':
            require(r['persistence']=='p' and r['row_security'] is False and r['force_row_security'] is False
                    and r['options'] is None and r['partition_bound'] is None and r['view'] is None,'UNSUPPORTED_INDEX_RELATION_PROPERTIES')
            continue  # fully consumed and cross-checked in indexes below
        require(r['kind']=='r','UNSUPPORTED_RELATION_KIND')
        require(r['options'] is None and r['partition_bound'] is None and r['view'] is None,'UNSUPPORTED_RELATION_PROPERTIES')
        add('managed','table',[schema,name],{k:r[k] for k in ('persistence','row_security','force_row_security')},r['owner'],('relation',schema,name))
    for r in observed['columns']:
        require((r['schema'],r['relation']) in relations,'UNRESOLVED_COLUMN_PARENT')
        if relations[(r['schema'],r['relation'])]['kind']=='i':continue  # index columns checked against fixed properties below
        require(r['identity']=='' and r['generated']=='','UNSUPPORTED_GENERATED_COLUMN')
        add('managed','column',[r['schema'],r['relation'],r['name']],dict(position=r['position'],type=data_type(r['type']),
            nullable=not r['not_null'],default=default(r['default']),identity=r['identity'],generated=r['generated']),
            relations[(r['schema'],r['relation'])]['owner'],('column',r['schema'],r['relation'],r['name']))
    # Deparse maps are closed, source-fixed typed resolution. Exact SQL text is
    # required; no unsafe whitespace/parenthesis stripping or guessed equivalence.
    for query,family in (('constraints','constraint'),('indexes','index')):
        declarations=keyed(context['deparse'].get(query,[]),lambda r:(r['schema'],r['name']),query+'_deparse')
        for r in observed[query]:
            key=(r['schema'],r['name'])
            if key not in declarations:raise MissingParameter('sql_deparse.'+query+'.'+'.'.join(key))
            declaration=declarations[key];c.closed(declaration,{'schema','name','sql','identity','definition'})
            require(r['definition']==declaration['sql'],'UNRECOGNIZED_SQL_DEFINITION:'+query)
            definition=declaration['definition']
            # Scalar facts are taken from rows AND checked against the source form.
            for name in ('kind','validated','deferrable','initially_deferred') if query=='constraints' else ('valid','ready'):
                require(type(r[name]) is type(definition[name]) and r[name]==definition[name],'DEPARSE_SCALAR_DIVERGENCE')
            if query=='indexes':require(r['live'] is True and key in relations and relations[key]['kind']=='i','INDEX_CENSUS')
            if query=='constraints':
                observed_parent=r['relation'].split('.')
                if len(observed_parent)==1:observed_parent=[r['schema'],observed_parent[0]]
                require(observed_parent==declaration['identity'][:2] and declaration['identity'][-1]==r['name'],'CONSTRAINT_PARENT_IDENTITY')
            else:require(declaration['identity']==[r['schema'],r['name']],'INDEX_IDENTITY')
            parent=declaration['identity'][:2] if query=='constraints' else [r['schema'],definition['table']]
            require(tuple(parent) in relations,'UNRESOLVED_OBJECT_PARENT')
            if query=='indexes':require(relations[key]['owner']==relations[tuple(parent)]['owner'],'INDEX_OWNER')
            add('managed',family,declaration['identity'],definition,relations[tuple(parent)]['owner'],('index' if query=='indexes' else 'constraint',*key))
        require(set(declarations)=={(r['schema'],r['name']) for r in observed[query]},'DEPARSE_EXTRA_DECLARATION')
    require({k for k,v in relations.items() if v['kind']=='i'}=={(r['schema'],r['name']) for r in observed['indexes']},'INDEX_RELATION_COVERAGE')
    # Raw index-column metadata is also source-fixed; it may not disappear.
    c.closed(context['deparse'],{'constraints','indexes','index_columns','routines','triggers'})
    index_columns=[r for r in observed['columns'] if relations[(r['schema'],r['relation'])]['kind']=='i']
    require(d.encode(index_columns)==d.encode(context['deparse']['index_columns']),'INDEX_COLUMN_COVERAGE')
    routines=keyed(observed['routines'],lambda r:(r['schema'],r['name'],r['arguments']),'routines')
    semantics=keyed(details['routine_semantics'],lambda r:(r['schema'],r['name'],r['arguments']),'routine_semantics')
    routine_forms=keyed(context['deparse']['routines'],lambda r:(r['schema'],r['name'],r['arguments']),'routine_forms')
    require(set(routine_forms)==set(routines),'ROUTINE_DEPARSE_COVERAGE')
    for key,r in routines.items():
        c.closed(routine_forms[key],{'schema','name','arguments','sql'})
        require(r['definition']==routine_forms[key]['sql'],'ROUTINE_DEPARSE_DIVERGENCE')
        require(r['kind']=='f' and key in semantics,'UNSUPPORTED_OR_MISSING_ROUTINE')
        s=semantics[key]
        require((r['owner'],r['security_definer'],r['config'])==(s['owner'],s['security_definer'],s['config']),'ROUTINE_CROSSCHECK')
    vol={'v':'VOLATILE','s':'STABLE','i':'IMMUTABLE'};parallel={'u':'UNSAFE','r':'RESTRICTED','s':'SAFE'}
    for key,s in semantics.items():
        require(s['volatility'] in vol and s['parallel'] in parallel,'ROUTINE_FLAGS')
        # Membership resolution is completed after catalog objects exist.
        add('system' if helpers and list(key)==own_settings.IDENTITY else 'managed' if key in routines else 'system','routine',list(key),dict(returns=s['returns'],language=s['language'],
            body=s['body'].strip(),security_definer=s['security_definer'],volatility=vol[s['volatility']],strict=s['strict'],parallel=parallel[s['parallel']],config=s['config'] or []),s['owner'],('routine',*key))
    trigger_semantics=keyed(details['trigger_semantics'],lambda r:(r['schema'],r['relation'],r['name']),'trigger_semantics')
    trigger_forms=keyed(context['deparse']['triggers'],lambda r:(r['schema'],r['relation'],r['name']),'trigger_forms')
    require(set(trigger_forms)=={key for key,row in trigger_semantics.items() if not row['internal']},'TRIGGER_DEPARSE_COVERAGE')
    fk_links=keyed(details['fk_trigger_links'],lambda r:(r['schema'],r['relation'],r['name']),'fk_trigger_links')
    require(set(fk_links)=={key for key,row in trigger_semantics.items() if row['internal']},'FK_LINK_COVERAGE')
    from scripts.dedicated.dev09b.migration_catalog import foreign_key_triggers,FK_TRIGGER_FUNCTIONS
    source_constraints=[dict(family='constraint',identity=x['identity'],definition=x['definition']) for x in context['deparse']['constraints']]
    expected_fk=keyed(foreign_key_triggers(source_constraints),lambda r:tuple(r['identity']),'source_fk_triggers')
    seen_fk=set()
    for r in observed['triggers']:
        key=(r['schema'],r['relation'],r['name']);require(key in trigger_semantics,'MISSING_TRIGGER_SEMANTICS')
        s=trigger_semantics[key]
        require((r['enabled'],r['internal'])==(s['enabled'],s['internal']),'TRIGGER_CROSSCHECK')
        fn=(s['function_schema'],s['function_name'],s['function_arguments']);require(fn in semantics,'UNRESOLVED_TRIGGER_ROUTINE')
        require(key[:2] in relations,'UNRESOLVED_TRIGGER_PARENT')
        definition=dict(timing=s['timing'],events=s['events'],row=s['row'],function=list(fn),enabled=s['enabled'],internal=s['internal'])
        identity=list(key)
        if r['internal']:
            link=fk_links[key]
            require(re.fullmatch(r'RI_ConstraintTrigger_[ac]_[1-9][0-9]*',r['name']) is not None,'FK_ALLOCATED_NAME')
            require(all(link[k] is False for k in ('deferrable','initially_deferred','constraint_deferrable','constraint_initially_deferred'))
                    and all(link[k] is True for k in ('validated','opposite_relation','no_arguments','no_condition','no_columns','no_transition')),'FK_TRIGGER_FLAGS')
            require(link['update_action']==link['delete_action']=='a' and link['match']=='s','FK_ACTIONS')
            source_id=[link['constraint_schema'],link['child_relation'],link['constraint_name']]
            candidates=[co for co in source_constraints if co['identity']==source_id and co['definition']['kind']=='f']
            require(len(candidates)==1 and link['child_schema']==source_id[0],'FK_CONSTRAINT_REFERENCE')
            reference=candidates[0]['definition']['references'][0].split('.')[:2]
            require(reference==[link['parent_schema'],link['parent_relation']],'FK_PARENT_REFERENCE')
            suffixes=[k for k,v in FK_TRIGGER_FUNCTIONS.items() if v[0]==fn[1]]
            require(len(suffixes)==1 and fn[0]=='pg_catalog' and fn[2]=='','FK_FUNCTION_REFERENCE')
            suffix=suffixes[0];side=FK_TRIGGER_FUNCTIONS[suffix][2]
            require(r['name'].startswith('RI_ConstraintTrigger_'+('c' if side=='child' else 'a')+'_'),'FK_TRIGGER_SIDE')
            identity=[*key[:2],'@fk:'+'.'.join(source_id)+':'+suffix]
            symbol=tuple(identity)
            require(symbol in expected_fk and symbol not in seen_fk,'FK_TRIGGER_COMPLETENESS')
            require(d.encode(definition)==d.encode(expected_fk[symbol]['definition']),'FK_TRIGGER_SEMANTICS')
            seen_fk.add(symbol)
        else:
            c.closed(trigger_forms[key],{'schema','relation','name','sql'})
            require(r['definition']==trigger_forms[key]['sql'],'TRIGGER_DEPARSE_DIVERGENCE')
        add('managed','trigger',identity,definition,relations[key[:2]]['owner'],('trigger',*key))
    require(seen_fk==set(expected_fk),'FK_TRIGGER_COMPLETENESS')
    require(set(trigger_semantics)=={(r['schema'],r['relation'],r['name']) for r in observed['triggers']},'EXTRA_TRIGGER_SEMANTICS')
    relation_types=keyed(details['relation_types'],lambda r:(r['schema'],r['relation']),'relation_types')
    require(set(relation_types)=={key for key,r in relations.items() if r['kind']=='r'},'RELATION_TYPE_COVERAGE')
    types=keyed(observed['types'],lambda r:(r['schema'],r['name']),'types')
    type_props=keyed(observed['type_details'],lambda r:(r['schema'],r['name']),'type_details')
    require(set(types)==set(type_props),'TYPE_DETAILS_COVERAGE')
    implicit_names={}
    for parent,r in relation_types.items():
        for kind,key in (('composite_type','row_type'),('array_type','array_type')):
            name=(r['schema'],r[key]);require(name in types and name not in implicit_names,'IMPLICIT_TYPE_REFERENCE')
            implicit_names[name]=(kind,parent,r)
    for key,r in types.items():
        props=type_props[key]['properties']
        require(props is not None and props['typname']==r['name'] and props['typtype']==r['kind'] and props['typcategory']==r['category']
                and props['typnotnull']==r['not_null'] and props['typdefault']==r['default'],'TYPE_CROSSCHECK')
        require(r['base']==('-' if not props['typbasetype'] else resolve('pg_type',props['typbasetype'])['display'])
                and r['element']==('-' if not props['typelem'] else resolve('pg_type',props['typelem'])['display']),'TYPE_DISPLAY_REFERENCE')
        require(resolve('pg_namespace',props['typnamespace'])['name']==r['schema'] and
                resolve('pg_roles',props['typowner'])['name']==r['owner'],'TYPE_OWNER_REFERENCE')
        if key in implicit_names:
            kind,parent,link=implicit_names[key]
            if kind=='composite_type':
                require(props['typrelid']==link['relation_oid'] and r['kind']=='c' and r['category']=='C','ROW_TYPE_REFERENCE')
                values=dict(parent='.'.join(parent),kind=r['kind'],category=r['category'])
            else:
                require(props['typelem']==link['type_oid'] and r['kind']=='b' and r['category']=='A','ARRAY_TYPE_REFERENCE')
                values=dict(parent='.'.join(parent),kind=r['kind'],category=r['category'],element_schema=parent[0],element_name=link['row_type'])
            add('managed',kind,list(key),dict(properties=[dict(name=k,value=v) for k,v in sorted(values.items())]),r['owner'],('type',*key))
        elif r['kind']=='b' and r['category']=='A':
            element=resolve('pg_type',props['typelem'])
            require((element['schema'],element['name']) in types,'UNRESOLVED_ARRAY_ELEMENT')
            values=dict(parent=element['schema']+'.'+element['name'],kind=r['kind'],category=r['category'],element_schema=element['schema'],element_name=element['name'])
            add('managed','array_type',list(key),dict(properties=[dict(name=k,value=v) for k,v in sorted(values.items())]),r['owner'],('type',*key))
        else:
            require(r['kind']=='b' and r['category']!='A','UNSUPPORTED_TYPE_FAMILY')
            values=dict(category=props['typcategory'],length=props['typlen'],by_value=props['typbyval'],alignment=props['typalign'],storage=props['typstorage'],
                input=props['typinput'],output=props['typoutput'],receive=props['typreceive'],send=props['typsend'],delimiter=props['typdelim'],
                preferred=props['typispreferred'],not_null=props['typnotnull'],default=props['typdefault'],
                collation=None if not props['typcollation'] else resolve('pg_collation',props['typcollation'])['display'])
            add('managed','base_type',list(key),dict(properties=[dict(name=k,value=v) for k,v in sorted(values.items())]),r['owner'],('type',*key))
    toast=keyed(details['toast_semantics'],lambda r:(r['schema'],r['relation'],r['name']),'toast_semantics')
    require(set(toast)=={(r['schema'],r['relation'],r['name']) for r in observed['toast']},'TOAST_COVERAGE')
    for raw in observed['toast']:
        key=(raw['schema'],raw['relation'],raw['name']);r=toast[key]
        require(all(raw[k]==r[k] and type(raw[k]) is type(r[k]) for k in raw),'TOAST_CROSSCHECK')
        require(key[:2] in relations and r['kind'] in {'r','i'},'TOAST_PARENT')
        # Fixed symbolic resolver identity; never guess an allocated OID/name.
        aliases_for_toast=context['implicit_objects']
        symbolic=[x for x in aliases_for_toast if x.get('schema')==r['schema'] and x.get('relation')==r['relation'] and x.get('kind')==r['kind']]
        if len(symbolic)!=1:raise MissingParameter('sql_resolver.toast.'+'.'.join(key[:2])+'.'+r['kind'])
        c.closed(symbolic[0],{'schema','relation','kind','identity'})
        values=dict(parent='.'.join(key[:2]),kind=r['kind'],persistence=r['persistence'],options=None if r['options'] is None else d.encode(r['options']).decode())
        add('managed','toast',symbolic[0]['identity'],dict(properties=[dict(name=k,value=v) for k,v in sorted(values.items())]),r['owner'],('toast',*key))
    require(len(context['implicit_objects'])==len(toast),'EXTRA_IMPLICIT_RESOLVER')
    if helpers:
        role=own_settings.role_object(details['helper_owner_role'][0],details['helper_owner_edges'][0],details['helper_security_flags'][0])
        add('system','role',role['identity'],role['definition'])
    languages=keyed(details['language_details'],lambda r:r['name'],'language_details')
    for r in languages.values():
        values={k:r[k] for k in ('trusted','handler','inline','validator')}
        add('system','language',[r['name']],dict(properties=[dict(name=k,value=v) for k,v in sorted(values.items())]),r['owner'],('language',r['name']))
    ext=keyed(observed['extension'],lambda r:r['name'],'extension')
    require(set(ext)=={'btree_gist','plpgsql'},'UNSUPPORTED_EXTENSION_CENSUS')
    require(d.encode([ext['plpgsql']])==d.encode(context['fixed_properties']['template_extensions']),'TEMPLATE_EXTENSION_HEADER')
    # plpgsql is template-owned: its member coverage is included in fixed
    # properties/census; no user extension other than btree_gist is admitted.
    ext_props=keyed(observed['extension_properties'],lambda r:(r['extension'],r['catalog'],r['identity']),'extension_properties')
    member_catalogs={'function':'pg_proc','procedure':'pg_proc','type':'pg_type','language':'pg_language',
                     'operator':'pg_operator','operator class':'pg_opclass','operator family':'pg_opfamily'}
    def member_key(row):
        require(row['type'] in member_catalogs,'UNSUPPORTED_EXTENSION_MEMBER_TYPE')
        catalog='pg_catalog.'+member_catalogs[row['type']]
        return (row['extension'],catalog,row['identity'])
    members=keyed(observed['extension_members'],member_key,'extension_members')
    require(set(ext_props)==set(members),'EXTENSION_PROPERTY_COVERAGE')
    member_keys={};opfamilies={};declared_extension_objects={}
    for member_key,r in members.items():
        require(r['extension'] in ext,'EXTENSION_HEADER_REFERENCE')
        require(r['subid']==0,'UNSUPPORTED_EXTENSION_SUBOBJECT')
        prop=ext_props[member_key];family=prop['catalog'].removeprefix('pg_catalog.')
        if family in {'pg_opclass','pg_opfamily','pg_operator'}:
            value=prop['properties'];require(value is not None,'MISSING_EXTENSION_PROPERTIES')
            if family=='pg_opclass':
                schema=resolve('pg_namespace',value['opcnamespace'])['name'];fam=resolve('pg_opfamily',value['opcfamily'])
                values=dict(method=resolve('pg_am',value['opcmethod'])['name'],family_schema=fam['schema'],family_name=fam['name'],
                    input_type=resolve('pg_type',value['opcintype'])['display'],key_type=None if not value['opckeytype'] else resolve('pg_type',value['opckeytype'])['display'],default=value['opcdefault'])
                require(r['type']=='operator class' and r['schema']==schema and r['name']==value['opcname']
                        and r['identity']==schema+'.'+value['opcname']+' USING '+values['method'],'OPCLASS_IDENTITY_REFERENCE')
                key=add(None,'opclass',[schema,value['opcname']],dict(properties=[dict(name=k,value=v) for k,v in sorted(values.items())]),resolve('pg_roles',value['opcowner'])['name'])
            elif family=='pg_opfamily':
                schema=resolve('pg_namespace',value['opfnamespace'])['name']
                rows_for_family=[x for x in properties['operator_members'] if x['schema']==schema and x['family']==value['opfname']]
                values=dict(method=resolve('pg_am',value['opfmethod'])['name'],operators=d.encode([x['properties'] for x in rows_for_family if x['kind']=='operator']).decode(),
                            functions=d.encode([x['properties'] for x in rows_for_family if x['kind']=='function']).decode())
                require(r['type']=='operator family' and r['schema']==schema and r['name']==value['opfname']
                        and r['identity']==schema+'.'+value['opfname']+' USING '+values['method'],'OPFAMILY_IDENTITY_REFERENCE')
                key=add(None,'opfamily',[schema,value['opfname']],dict(properties=[dict(name=k,value=v) for k,v in sorted(values.items())]),resolve('pg_roles',value['opfowner'])['name'])
                opfamilies[(schema,value['opfname'])]=key
            else:
                schema=resolve('pg_namespace',value['oprnamespace'])['name']
                values=dict(left_type=None if not value['oprleft'] else resolve('pg_type',value['oprleft'])['display'],right_type=None if not value['oprright'] else resolve('pg_type',value['oprright'])['display'],
                    result_type=resolve('pg_type',value['oprresult'])['display'],function=value['oprcode'],commutator=None if not value['oprcom'] else resolve('pg_operator',value['oprcom'])['display'],
                    negator=None if not value['oprnegate'] else resolve('pg_operator',value['oprnegate'])['display'],restriction=value['oprrest'],join=value['oprjoin'],merges=value['oprcanmerge'],hashes=value['oprcanhash'])
                link=identities.get((r['type'],r['identity']))
                require(link is not None and link['family']=='operator' and r['schema']==schema and r['name'] is None
                        and link['schema']==schema and link['name']==value['oprname']
                        and link['arguments']==','.join(x or '' for x in (values['left_type'],values['right_type'])),'OPERATOR_IDENTITY_REFERENCE')
                key=add(None,'operator',[schema,value['oprname'],','.join(x or '' for x in (values['left_type'],values['right_type']))],dict(properties=[dict(name=k,value=v) for k,v in sorted(values.items())]),resolve('pg_roles',value['oprowner'])['name'])
        elif r['type'] in {'function','procedure'}:
            link=identities.get((r['type'],r['identity']))
            require(link is not None and link['family']=='routine' and r['name'] is None and r['schema']==link['schema'],'UNRESOLVED_EXTENSION_ROUTINE')
            alias=('routine',link['schema'],link['name'],link['arguments'])
            require(alias in aliases,'UNRESOLVED_EXTENSION_ROUTINE');key=aliases[alias]
        elif r['type']=='type':
            candidates=[k for alias,k in aliases.items() if alias[0]=='type' and r['identity']==alias[1]+'.'+alias[2]]
            require(len(candidates)==1 and r['name']==candidates[0][1][1] and r['schema']==candidates[0][1][0],'UNRESOLVED_EXTENSION_TYPE');key=candidates[0]
        elif r['type']=='language':
            require(r['extension']=='plpgsql' and r['identity'] in languages and r['name']==r['identity'] and r['schema'] is None,'UNRESOLVED_TEMPLATE_LANGUAGE');key=('language',(r['identity'],))
        else:raise c.Unsupported('Unimplemented extension member family: '+r['type'])
        require(key not in member_keys.values(),'DUPLICATE_EXTENSION_OBJECT')
        member_keys[member_key]=key
        if family in {'pg_opclass','pg_opfamily','pg_operator'}:
            declared_extension_objects[key]=dict(family=key[0],identity=list(key[1]),definition=dict(properties=[dict(name=k,value=v) for k,v in sorted(values.items())]))
        if r['extension']=='btree_gist':
            item=next((o for o in objects if (o['family'],tuple(o['identity']))==key),None)
            if item:objects.remove(item);obj={k:item[k] for k in ('family','identity','definition')}
            else:
                # Operator-class/family/operator objects were deliberately held
                # outside the managed-object section until membership resolved.
                obj=declared_extension_objects[key]
            extension_objects.setdefault('btree_gist',[]).append(obj);extension_names[key]='btree_gist'
    # PostgreSQL array types may be internally dependent rather than direct
    # extension members. Resolve their element explicitly, preserve their ACLs.
    for obj in list(objects):
        if obj['family']=='array_type':
            props={x['name']:x['value'] for x in obj['definition']['properties']}
            element=('base_type',(props['element_schema'],props['element_name']))
            if element in extension_names:
                objects.remove(obj);key=(obj['family'],tuple(obj['identity']))
                extension_names[key]=extension_names[element]
                extension_objects.setdefault(extension_names[element],[]).append({k:obj[k] for k in ('family','identity','definition')})
    require(all((r['schema'],r['family']) in opfamilies for r in observed['operator_members']),'UNRESOLVED_OPERATOR_FAMILY')
    for row in observed['operator_members']:
        field='amopfamily' if row['kind']=='operator' else 'amprocfamily'
        family=resolve('pg_opfamily',row['properties'][field])
        require((family['schema'],family['name'])==(row['schema'],row['family']),'OPERATOR_MEMBER_REFERENCE')
    # Complete cross-query identity coverage, including implicit objects which
    # have an INTERNAL dependency on a relation rather than a direct namespace
    # dependency. The phase comparator still fixes the full object inventory.
    expected_aliases=set(aliases)
    for key in owners:
        if key[0] in {'opclass','opfamily'}:expected_aliases.add((key[0],*key[1]))
        if key[0]=='operator':expected_aliases.add(('operator',*key[1]))
    expected_aliases|={('extension',row['schema'],row['name']) for row in ext.values()}
    for alias,normalized_key in aliases.items():
        if alias[0]=='constraint':
            link=identity_keys.get(alias)
            require(link is not None and link['relation']==normalized_key[1][1],'CONSTRAINT_IDENTITY_PARENT')
    linked_aliases=set(identity_keys)
    # Indexes use the same pg_class catalog as relations.
    expected_aliases={('relation',*a[1:]) if a[0]=='index' else a for a in expected_aliases if a[0] not in {'schema','toast','column'}}
    require(linked_aliases==expected_aliases,'OBJECT_IDENTITY_COVERAGE')
    observed_census={(r['schema'],r['type'],r['identity']) for r in observed['namespace_objects']}
    linked_census={(r['schema'],r['identify_type'],r['identify_identity']) for r in identities.values() if r['direct_namespace'] and r['schema'] in schema_names}
    require(observed_census==linked_census,'NAMESPACE_CENSUS_DIVERGENCE')
    grants={key:[] for key in owners};schema_acl=observed['schema_acl']
    for row in schema_acl:
        key=('schema',(row['name'],))
        require(row['name'] in schema_names,'SCHEMA_ACL_SCOPE')
        if row['name']=='public':continue
        require(key in owners and row['grantor']==owners[key],'SCHEMA_GRANTOR')
        if row['grantee']!=owners[key]:grants[key].append(ace(row))
    for row in observed['object_acl']:
        family=row['family'];schema=row['schema'];name=row['name']
        if family=='routine':
            possible=[k for alias,k in aliases.items() if alias[0]=='routine' and alias[1]==schema and alias[2]+alias[3]==name]
            require(len(possible)==1,'UNRESOLVED_ROUTINE_ACL');key=possible[0]
        else:
            alias=('type' if family=='type' else 'relation',schema,name)
            if alias not in aliases and family=='relation':alias=('index',schema,name)
            require(alias in aliases,'UNRESOLVED_OBJECT_ACL');key=aliases[alias]
        require(row['grantor']==owners[key],'OBJECT_GRANTOR')
        if row['grantee']!=owners[key]:grants[key].append(ace(row))
    for row in details['system_acl']:
        alias=('language',row['name']) if row['family']=='language' else ('routine',row['schema'],row['name'],row['arguments'])
        require(alias in aliases,'UNRESOLVED_SYSTEM_ACL')
        key=aliases[alias];require(row['owner']==owners[key] and row['grantor']==owners[key],'SYSTEM_GRANTOR')
        if row['grantee']!=owners[key]:grants[key].append(ace(row))
    # Owner powers are represented separately in PHASE-ROWS, but their rows
    # cannot simply disappear from a SQL result. The queries explicitly expand
    # acldefault when an ACL is NULL: require the complete nominal owner vector.
    def owner_vector(values,owner,wanted,label):
        selected=[r for r in values if r['grantee']==owner]
        require(len(selected)==len(wanted) and {(r['privilege'],r['grant_option']) for r in selected}=={(x,False) for x in wanted},'ACL_OWNER_COVERAGE:'+label)
    for name in schema_names:
        owner_vector([r for r in schema_acl if r['name']==name],schemas[name]['owner'],{'USAGE','CREATE'},'schema')
    for alias,key in aliases.items():
        if alias[0] not in {'relation','index','routine','type'}:continue
        if alias[1] not in schema_names:continue
        family='relation' if alias[0] in {'relation','index'} else alias[0]
        label=alias[2]+alias[3] if alias[0]=='routine' else alias[2]
        matching=[r for r in observed['object_acl'] if r['family']==family and r['schema']==alias[1] and r['name']==label]
        wanted={'SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER'} if family=='relation' else {'EXECUTE'} if family=='routine' else {'USAGE'}
        owner_vector(matching,owners[key],wanted,'object')
    for alias,key in aliases.items():
        if alias[0]=='language':matching=[r for r in details['system_acl'] if r['family']=='language' and r['name']==alias[1]];wanted={'USAGE'}
        elif alias[0]=='routine' and alias[1] not in schema_names:
            matching=[r for r in details['system_acl'] if r['family']=='routine' and (r['schema'],r['name'],r['arguments'])==alias[1:]];wanted={'EXECUTE'}
        else:continue
        owner_vector(matching,owners[key],wanted,'system')
    public=[ace(row) for row in schema_acl if row['name']=='public' and row['grantee']!=schemas['public']['owner']]
    require(all(row['grantor']==schemas['public']['owner'] for row in schema_acl if row['name']=='public'),'PUBLIC_SCHEMA_GRANTOR')
    db_rows=observed['database_acl'];require(bool(db_rows),'MISSING_DATABASE_ACL')
    require(all(r['name']==binding['database'] and r['owner']==env['owner'] and r['grantor']==env['owner'] for r in db_rows),'DATABASE_ACL_OWNER')
    database_acl=[ace(r) for r in db_rows if r['grantee']!=env['owner']]
    # Owner powers are represented by database_owner, not duplicated as grants.
    rights=[]
    for row in observed['column_acl']:
        require(('column',row['schema'],row['relation'],row['name']) in aliases,'UNRESOLVED_COLUMN_ACL')
        owner=relations[(row['schema'],row['relation'])]['owner'];require(row['grantor']==owner and row['grant_option'] is False,'COLUMN_GRANTOR')
        if row['grantee']==owner:continue
        rights.append(dict(role=row['grantee'],schema=row['schema'],relation=row['relation'],column=row['name'],privilege=row['privilege']))
    # Extension ACL query must corroborate the object ACL expansion exactly.
    expected_ext=[]
    for r in observed['extension_acl']:
        matching=[k for k in member_keys if k[0]==r['extension'] and k[2]==r['identity']]
        require(len(matching)==1,'UNRESOLVED_EXTENSION_ACL')
        key=member_keys[matching[0]];require(r['grantor']==owners[key],'EXTENSION_GRANTOR')
        if r['grantee']!=owners[key]:expected_ext.append((key,d.encode(ace(r))))
    direct_members=set(member_keys.values())
    # The query expands function/type/relation ACLs for EVERY extension,
    # including the template's plpgsql functions. Do not omit template grants,
    # nor invent a language ACL row in a query which never selects languages.
    acl_member_families={'routine','base_type','array_type','composite_type'}
    actual_ext=[(key,d.encode(g)) for key in direct_members if key[0] in acl_member_families for g in grants[key]]
    require(sorted(expected_ext)==sorted(actual_ext),'EXTENSION_ACL_DIVERGENCE')
    role_values=details['role_details'];role_names={r['name'] for r in role_values}
    require(set(s['owner'] for s in schemas.values() if s['name'] in schema_names and s['owner']!='pg_database_owner')<=role_names,'UNRESOLVED_SCHEMA_OWNER')
    role_map={r['name']:r for r in role_values}
    for name,row in schemas.items():
        if name not in schema_names:
            require(not row['can_create'] and not row['grant_create'],'EXTERNAL_SCHEMA_CREATE')
            continue
        owner_login=False if row['owner']=='pg_database_owner' else role_map[row['owner']]['login']
        require(row['owner_login'] is owner_login,'SCHEMA_OWNER_LOGIN')
        applicable=[r for r in schema_acl if r['name']==name and r['grantee'] in {'PUBLIC',binding['current_user']}]
        for privilege,can,grant in (('CREATE','can_create','grant_create'),('USAGE','can_use','grant_use')):
            owner=row['owner']==binding['current_user']
            require(row[can] is (owner or any(r['privilege']==privilege for r in applicable))
                    and row[grant] is (owner or any(r['privilege']==privilege and r['grant_option'] for r in applicable)),
                    'SCHEMA_EFFECTIVE_ACL')
    for row in observed['memberships']:require(row['role'] in role_names or not any(row[k] for k in ('member','inherited','can_set')),'MEMBERSHIP_ROLE_SCOPE')
    for r in details['role_edges']:require(r['role'] in role_names and r['member'] in role_names,'UNRESOLVED_ROLE_EDGE')
    sys_owned=[];sys_acl=[];owned=[];acls=[]
    for section,owned_list,acl_list in (('system',sys_owned,sys_acl),('managed',owned,acls)):
        for obj in [o for o in objects if o['section']==section and o['family']!='role']:
            key=(obj['family'],tuple(obj['identity']));owned_list.append(dict(family=key[0],identity=list(key[1]),owner=owners[key]))
            acl_list.append(dict(family=key[0],identity=list(key[1]),grants=sorted(grants[key],key=lambda r:(r['grantee'],r['privilege']))))
    member_objects=p.sort_objects(extension_objects.get('btree_gist',[]));require(bool(member_objects),'EMPTY_BTREE_GIST')
    ext_owners=[];ext_acls=[]
    for obj in member_objects:
        key=(obj['family'],tuple(obj['identity']));ext_owners.append(dict(family=key[0],identity=list(key[1]),owner=owners[key]));ext_acls.append(dict(family=key[0],identity=list(key[1]),grants=grants[key]))
    require(type(ledger_rows) is dict and set(ledger_rows)=={'application','security'},'LEDGER_QUERY_COVERAGE')
    table_names={(r['schema'],r['name']) for r in relations.values() if r['kind']=='r'}
    ledgers=[]
    # Ledger contents are separately read by the port, never inferred from a row
    # count or supplied by a phase expectation.
    for chain,name in (('application','alembic_version'),('security','alembic_security_version')):
        present=('public',name) in table_names
        values=ledger_rows[chain]
        if not present:
            require(values is None,'ABSENT_LEDGER_WITH_ROWS')
            ledgers.append(dict(chain=chain,presence='ABSENT',revisions=[]))
        else:
            require(type(values) is list and len(values)<=2,'LEDGER_BOUND')
            revisions=[]
            for item in values:
                row=row_mapping(item);c.closed(row,{'version_num'});c.require(type(row['version_num']) is str and bool(row['version_num']))
                revisions.append(row['version_num'])
            require(len(set(revisions))==len(revisions),'DUPLICATE_LEDGER_REVISION')
            ledgers.append(dict(chain=chain,presence='PRESENT',revisions=sorted(revisions)))
    header=dict(schema_version=2,profile='dev09b-prepared-'+phase.lower()+'-v2',phase=phase,
        target_binding_sha256=meta['target_binding_sha256'],parameters_sha256=meta['parameters_sha256'],sources=meta['sources'],distribution=distribution,
        database_owner=env['owner'],public_owner=schemas['public']['owner'])
    source_ext=meta['extension_sources'];sources(source_ext);require(bool(source_ext),'EXTENSION_SOURCE_PROVENANCE')
    ext_row=ext['btree_gist']
    inventories=dict(system_ownership=sys_owned,system_acls=sys_acl,system_memberships=details['role_edges'],system_default_acl=[],
        extensions=[dict(version=ext_row['version'],schema=ext_row['schema'],owner=ext_row['owner'],name='btree_gist',sources=source_ext,
            members=member_objects,ownership=ext_owners,acls=ext_acls,acl=[])],ownership=owned,acls=acls,roles=role_values,memberships=[],
        database_acl=database_acl,public_acl=public,inspection_column_grants=[],temporary_rights=[],
        control_system_acl=[],ledgers=ledgers)
    # Separate column permissions and pg_control_system privileges using observed
    # role identities supplied in authenticated metadata (no guessed role names).
    c.closed(meta['role_bindings'],{'migrator','inspector'})
    for role,name in meta['role_bindings'].items():
        if name is None:
            require(role=='migrator' and phase=='DEV-BASE' and session is None and all(meta[k] is None for k in ('request_id','approval_id','attempt_id')),
                    'ABSENT_MIGRATOR_SCOPE')
        else:p.name(name);require(name in role_names,'ROLE_CLASSIFICATION_REFERENCE')
    for row in rights:
        if row['role']==meta['role_bindings']['inspector']:inventories['inspection_column_grants'].append(row)
        elif row['role']==meta['role_bindings']['migrator']:inventories['temporary_rights'].append(row)
        else:raise c.Unsupported('Unimplemented column grant principal')
    control=('routine',('pg_catalog','pg_control_system',''))
    if control in grants:inventories['control_system_acl']=grants[control]
    value=dict(format='DEV09B-PHASE-ROWS-1',header=header,objects=objects,inventories=inventories,
               subject_session=None if session is None else session,
               **{k:meta[k] for k in ('request_id','approval_id','attempt_id')})
    d.normalize_observations(value)
    return ConvertedObservation(d.encode(value),collector_id,c.canonical(binding))


def source_context(root,context,*,phase,roles,encoding,prerequisite=None):
    """Producer-side fixed-source builder for this adapter's existing format.

    Called before collecting observations; has no connection argument and never
    rewrites a supplied signed context during conversion or admission.
    Authorship, artifact approval and the real verifier remain external.
    """
    from scripts.dedicated.dev09b.application_catalog_context import extend_context
    return extend_context(root,context,phase=phase,roles=roles,encoding=encoding,prerequisite=prerequisite)
