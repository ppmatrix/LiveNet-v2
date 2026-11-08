"""Application-only detailed catalog v2; pure signed expectations and row normalizer.

No I/O, observation-derived policy, synthetic approval, operational collector or
security profile. A fixed, closed artifact declaration supplies system/extension/
implicit objects; its authorship/approval is an additional trusted policy check.
Normalized observation rows are a versioned collector interface, NOT raw pg_get_*
SQL text or the old 33-query row format. Unknown representations refuse.
"""
from hashlib import sha256
from functools import lru_cache
from types import MappingProxyType

from . import codec as c
from . import physical as p
from .layers import document_hash, sources
from .migration_catalog import MissingParameter, exact

PROFILE='dev09b-application-f066-catalog-v2'
OPERATION='application-base-to-f066a01a7230'
PHASES=MappingProxyType({'before':'DEV-BASE','entry':'APP-ENTRY',
                        'precommit':'APP-F066-PRECOMMIT','after':'APP-F066-PERSISTED',
                        'closed':'APP-F066-CLOSED'})
FIELDS={'schema_version','target_binding_sha256','privilege_plan_sha256','exclusivity_plan_sha256',
        'parameters','migration_sources','artifact','prepared_profile_sha256',*PHASES}
# Required properties of the artifact-resolved families supported in this profile.
# Other family declarations remain Unsupported, even though legacy projections can
# structurally represent their names. Definitions never become acceptable by hash.
PROPERTIES={
 'language':{'trusted','handler','inline','validator'},
 'composite_type':{'parent','category','kind'},
 'array_type':{'parent','element_schema','element_name','category','kind'},
 'toast':{'parent','kind','persistence','options'},
 'opclass':{'method','family_schema','family_name','input_type','key_type','default'},
 'opfamily':{'method','operators','functions'},
 'operator':{'left_type','right_type','result_type','function','commutator','negator',
             'restriction','join','merges','hashes'},
 'base_type':{'category','length','by_value','alignment','storage','input','output','receive','send',
              'delimiter','preferred','not_null','default','collation'},
}


def encode(obj):return c.canonical(obj,maximum_depth=32)
def parse(raw):return c.parse(raw,maximum=16*1024*1024,maximum_depth=32)


def artifact_projection(parameters):
    """Fixed artifact payload without self-referential source hash fields."""
    return dict(schema_version=1,
        distribution={k:v for k,v in parameters['distribution'].items()
                      if k not in {'template_sources','alembic_sources','sqlalchemy_sources'}},
        roles=parameters['roles'],administrative_roles=parameters['administrative_roles'],
        extension={k:v for k,v in parameters['btree_gist'].items() if k!='sources'},
        **{k:parameters[k] for k in ('system_objects','system_ownership','system_acls',
                                    'system_memberships','system_default_acl','resolver_objects')})


def artifact_object(obj):
    p.shape_object(obj)
    if obj['family']=='role':
        from . import own_settings
        c.require(encode(obj)==encode(own_settings.ROLE_OBJECT));return
    if obj['family'] in {'schema','table','column','constraint','index','routine','trigger'}:
        if obj['family']=='routine':
            for key in ('returns','language','body','volatility','parallel'):c.require(type(obj['definition'][key]) is str)
            c.require(obj['definition']['volatility'] in {'IMMUTABLE','STABLE','VOLATILE'})
            c.require(obj['definition']['parallel'] in {'SAFE','RESTRICTED','UNSAFE'})
            c.require(type(obj['definition']['config']) is list and all(type(x) is str for x in obj['definition']['config']))
        return
    family=obj['family']
    if family not in PROPERTIES:raise c.Unsupported('Unimplemented detailed artifact family: '+family)
    props={x['name']:x['value'] for x in obj['definition']['properties']}
    exact(props,PROPERTIES[family],'artifact.'+family)
    for key,value in props.items():
        if key in {'trusted','by_value','default','preferred','not_null','merges','hashes'} and not (family=='base_type' and key=='default'):
            c.require(type(value) is bool)
        elif key=='length':c.integer(value,-1,32767)
        else:c.require(type(value) is str or (value is None and key in {'options','default','collation','receive','send','commutator','negator','restriction','join','key_type'}))
        if key not in {'options','default','collation','receive','send','commutator','negator','restriction','join','key_type'} and type(value) is str:
            c.require(bool(value))
    if family in {'composite_type','array_type','toast'}:
        c.require(type(props['parent']) is str and '.' in props['parent'])
    if family=='composite_type':c.require(props['kind']=='c' and props['category']=='C')
    if family=='array_type':c.require(props['kind']=='b' and props['category']=='A')
    if family=='toast':c.require(props['kind'] in {'r','i'} and props['persistence']=='p')


def validate_artifact(physical,target,provenance):
    params=physical['parameters'];p.validate_parameters(params,target)
    c.integer(params['schema_version'],2,2)
    doc=physical['artifact'];exact(doc,{'path','sha256','content'},'artifact')
    sources([{'path':doc['path'],'sha256':doc['sha256']}])
    c.require(type(doc['content']) is str)
    raw=doc['content'].encode('utf8');c.require(sha256(raw).hexdigest()==doc['sha256'])
    decoded=parse(raw)
    # Closed field sets are determined by the versioned parameter schema, not by
    # an arbitrary observed document or a completeness boolean.
    c.require(encode(decoded)==encode(artifact_projection(params)))
    inventory={x['path']:x['sha256'] for x in provenance['source_inventory']}
    c.require(inventory.get(doc['path'])==doc['sha256'])
    refs=[*params['distribution']['template_sources'],*params['distribution']['alembic_sources'],
          *params['distribution']['sqlalchemy_sources'],*params['btree_gist']['sources']]
    for ref in refs:c.require(inventory.get(ref['path'])==ref['sha256'])
    # System/default/extension/implicit declarations are explicitly tied to this
    # fixed artifact, with no omitted manifest/resolver allowed.
    for refs in (params['distribution']['template_sources'],params['btree_gist']['sources']):
        c.require({'path':doc['path'],'sha256':doc['sha256']} in refs)
    system=params['system_objects'];members=params['btree_gist']['members']
    from .migration_catalog import FK_TRIGGER_FUNCTIONS
    routines={tuple(o['identity']):o['definition'] for o in system if o['family']=='routine'}
    for function,_,_ in FK_TRIGGER_FUNCTIONS.values():
        key=('pg_catalog',function,'')
        if key not in routines:raise MissingParameter('target_profile.system_objects.pg_catalog.'+function+'()')
        c.require(routines[key]==dict(returns='trigger',language='internal',body=function,security_definer=False,
            volatility='VOLATILE',strict=True,parallel='SAFE',config=[]))
    from . import own_settings
    for obj in system:
        if obj['family']=='routine' and obj['definition']['security_definer']:
            # Only the exact newly approved OFFLINE exception; installation and
            # target-profile approval still require their own trusted acts.
            c.require(encode(obj)==encode(own_settings.OBJECT))
            c.require(params['roles']['admin']==own_settings.ADMIN)
            c.require(target['system_identifier']==own_settings.TARGET_SID and target['database_name']==own_settings.DATABASE)
            c.require(any(encode(o)==encode(own_settings.ROLE_OBJECT) for o in system))
            c.require(inventory.get(own_settings.SOURCE)==own_settings.SOURCE_SHA256)
            owners=[x for x in params['system_ownership'] if x['family']=='routine' and x['identity']==own_settings.IDENTITY]
            permissions=[x for x in params['system_acls'] if x['family']=='routine' and x['identity']==own_settings.IDENTITY]
            allowed=[own_settings.declaration()['grants']]
            if inventory.get(own_settings.V2_SOURCE)==own_settings.trial_declaration()['amendment_sha256']:
                allowed.append(own_settings.trial_declaration()['grants'])
                if permissions and encode(permissions[0]['grants'])==encode(allowed[-1]):
                    c.require(params['roles']['migrator']==own_settings.MIGRATOR)
            c.require(len(owners)==len(permissions)==1 and owners[0]['owner']==own_settings.OWNER
                      and any(encode(permissions[0]['grants'])==encode(grants) for grants in allowed))
    # Prepared managed schemas/ledgers cannot be smuggled in as template objects.
    for obj in system:
        c.require(obj['identity'][0] not in {'inventory','audit','security'})
        c.require(not (obj['identity'][0]=='public' and len(obj['identity'])>1 and
                      obj['identity'][1].startswith(('alembic_version','alembic_security_version'))))
    for obj in members:c.require(obj['identity'][0]==params['btree_gist']['schema'])
    identities=[(o['family'],tuple(o['identity'])) for o in [*system,*members]]
    c.require(len(identities)==len(set(identities)))
    records=[*system,*members]
    for table,implicit in params['resolver_objects'].items():
        c.require(len([o for o in implicit if o['family']=='composite_type'])==1)
        c.require(len([o for o in implicit if o['family']=='array_type'])==1)
        for obj in implicit:
            artifact_object(obj)
            properties={x['name']:x['value'] for x in obj['definition']['properties']}
            c.require(properties['parent']==table)
            schema,name=table.split('.')
            if obj['family']=='composite_type':c.require(obj['identity']==[schema,name])
            if obj['family']=='array_type':
                c.require(obj['identity'][0]==schema and properties['element_schema']==schema and properties['element_name']==name)
            if obj['family']=='toast':c.require(obj['identity'][0]=='pg_toast')
        records+=implicit
    for obj in records:artifact_object(obj)


def migration_inputs(physical,semantic,provenance):
    docs=physical['migration_sources']
    c.require(type(docs) is list and len(docs)==len(semantic['installation_chain']))
    inventory={s['path']:s['sha256'] for s in provenance['source_inventory']};result=[]
    for doc,migration in zip(docs,semantic['installation_chain']):
        c.closed(doc,{'path','content'});c.require(type(doc['content']) is str)
        c.require(doc['path']==migration['source_path'])
        raw=doc['content'].encode('utf8');digest=sha256(raw).hexdigest()
        c.require(digest==migration['source_sha256']==inventory.get(doc['path']))
        result.append((doc['path'],raw))
    return tuple(result)


def catalog_from(expected,validator_inventory):
    snapshot=parse(expected.json)
    relations=[{'schema':o['identity'][0],'name':o['identity'][1],'kind':'r'}
               for o in snapshot['managed_objects'] if o['family']=='table']
    return dict(profile=PROFILE,validator_inventory=validator_inventory,
                schemas=['audit','inventory','public','security'],
                relations=sorted(relations,key=lambda r:(r['schema'],r['name'])),
                detailed_catalog=dict(schema_version=2,phase=expected.phase,snapshot=snapshot))


def validate_catalog(cat):
    c.require(cat['profile']==PROFILE)
    d=cat['detailed_catalog'];c.closed(d,{'schema_version','phase','snapshot'});c.integer(d['schema_version'],2,2)
    c.require(d['phase'] in PHASES.values());p.validate_snapshot(d['snapshot'])
    c.require(d['snapshot']['schema_version']==2 and d['snapshot']['phase']==d['phase'])
    c.require(cat['schemas']==['audit','inventory','public','security'])
    relations=[{'schema':o['identity'][0],'name':o['identity'][1],'kind':'r'}
               for o in d['snapshot']['managed_objects'] if o['family']=='table']
    c.require(encode(cat['relations'])==encode(sorted(relations,key=lambda r:(r['schema'],r['name']))))


def validate_contract(physical,target,semantic,provenance):
    return _validated_contract(encode(physical),encode(target),encode(semantic),encode(provenance))


@lru_cache(maxsize=8)
def _validated_contract(physical_raw,target_raw,semantic_raw,provenance_raw):
    # Only source-derived immutable declarations; not authentication/evidence.
    physical,target,semantic,provenance=map(parse,(physical_raw,target_raw,semantic_raw,provenance_raw))
    exact(physical,FIELDS,'detailed_physical');c.integer(physical['schema_version'],2,2)
    c.require(semantic['operation']==OPERATION)
    for field in ('target_binding_sha256','privilege_plan_sha256','exclusivity_plan_sha256','prepared_profile_sha256'):c.digest_text(physical[field])
    c.require(physical['target_binding_sha256']==c.digest('target',target))
    p.validate_parameters(physical['parameters'],target)
    migrations=migration_inputs(physical,semantic,provenance)
    from .migration_catalog import extract_sources
    managed=extract_sources(migrations,application_only=True)['application']
    tables={'.'.join(o['identity']) for o in managed if o['family']=='table'}|{'public.alembic_version'}
    actual=set(physical['parameters']['resolver_objects'])
    missing=sorted(tables-actual)
    if missing:raise MissingParameter('target_profile.resolver_objects.'+missing[0])
    c.require(actual==tables)
    validate_artifact(physical,target,provenance)
    expected={}
    for key,phase in PHASES.items():
        validate_catalog(physical[key])
        exp=p.compile_profile(phase,target,physical['parameters'],migrations)
        p.compare_profile(exp,physical[key]['detailed_catalog']['snapshot'])
        expected[phase]=exp
    return MappingProxyType(expected)


# Collector-normal-form interface. All observed fields are carried explicitly;
# metadata, object counts and ACL cannot be supplied from the expected snapshot.
OBJECT_SECTIONS={'system_objects':'system','managed_objects':'managed'}
LIST_SECTIONS=('system_ownership','system_acls','system_memberships','system_default_acl','extensions',
               'ownership','acls','roles','memberships','database_acl','public_acl',
               'inspection_column_grants','temporary_rights','control_system_acl','ledgers')
HEADER_FIELDS={'schema_version','profile','phase','target_binding_sha256','parameters_sha256','sources',
               'distribution','database_owner','public_owner'}


def normalize_observations(observation):
    """Closed rows from a collector; old/raw SQL representations refuse.

    Pure normalization, no comparison/authentication and no expected argument.
    Sorting never drops duplicates; comparison later checks every family/extras.
    Provenance in this observation is only a CLAIM until authenticated externally.
    """
    c.closed(observation,{'format','header','objects','inventories','subject_session','request_id','approval_id','attempt_id'})
    c.require(observation['format']=='DEV09B-PHASE-ROWS-1')
    from .evidence import session as validate_session
    ids=[observation[k] for k in ('request_id','approval_id','attempt_id')]
    if observation['subject_session'] is None:
        c.require(all(x is None for x in ids) and observation['header']['phase']=='DEV-BASE')
    else:
        validate_session(observation['subject_session'])
        for x in ids:c.uuid(x)
    header=observation['header'];c.closed(header,HEADER_FIELDS)
    c.require(header['schema_version']==2 and type(header['schema_version']) is int)
    c.require(header['phase'] in PHASES.values())
    rows=observation['objects'];c.require(type(rows) is list)
    inventories=observation['inventories'];c.closed(inventories,set(LIST_SECTIONS))
    result=dict(header);sections={'system':[],'managed':[]}
    for row in rows:
        c.closed(row,{'section','family','identity','definition'})
        c.require(row['section'] in sections)
        obj={k:row[k] for k in ('family','identity','definition')}
        p.shape_object(obj);sections[row['section']].append(obj)
    for field,section in OBJECT_SECTIONS.items():result[field]=p.sort_objects(sections[section])
    for field in LIST_SECTIONS:
        c.require(type(inventories[field]) is list)
        # Canonical row order preserves booleans, nulls and grant options.
        values=sorted(parse(encode(inventories[field])),key=encode)
        c.require(len({encode(v) for v in values})==len(values))
        result[field]=values
    # Validate before returning; list ordering is the phase contract ordering,
    # not lexicographic JSON order. Re-sort only sets whose key is specified.
    for field in ('system_acls','acls'):
        for row in result[field]:
            row['grants']=sorted(row['grants'],key=lambda x:(x['grantee'],x['privilege']))
    for field in ('system_ownership','system_acls','ownership','acls'):
        result[field]=sorted(result[field],key=lambda x:(x['family'],tuple(x['identity'])))
    result['roles']=sorted(result['roles'],key=lambda x:x['name'])
    for field in ('database_acl','public_acl','system_default_acl','control_system_acl'):
        result[field]=sorted(result[field],key=lambda x:(x['grantee'],x['privilege']))
    result['ledgers']=sorted(result['ledgers'],key=lambda x:x['chain'])
    for field in ('inspection_column_grants','temporary_rights'):
        result[field]=sorted(result[field],key=lambda x:(x['role'],x['schema'],x['relation'],x['column']))
    result['system_memberships']=sorted(result['system_memberships'],key=lambda x:(x['role'],x['member']))
    p.validate_snapshot(result)
    return result


def validate_subject(snapshot,phase,observation,session):
    from .layers import read_snapshot
    payload,target,executor,plan,semantic,physical,provenance=read_snapshot(snapshot)
    if session is None:
        c.require(phase=='DEV-BASE' and observation['subject_session'] is None)
    else:
        from dataclasses import asdict
        from .model import SessionBinding
        c.require(type(session) is SessionBinding);session.validate()
        c.require(encode(observation['subject_session'])==encode(asdict(session)))
        for key in ('request_id','approval_id','attempt_id'):c.require(observation[key]==payload[key])
        c.require(session.target_sha256==payload['target_binding_sha256'] and session.executor_sha256==plan['executor_binding_sha256']
                  and session.incarnation_id==executor['incarnation_id'])


def compare_observations(snapshot,phase,observation,*,session=None):
    """A comparison only; trusted origin and live session binding are separate."""
    from .layers import read_snapshot
    c.validate_layers(snapshot)
    payload,target,executor,plan,semantic,physical,provenance=read_snapshot(snapshot)
    validate_subject(snapshot,phase,observation,session)
    expected=validate_contract(physical,target,semantic,provenance)
    if phase not in expected:raise c.Unsupported('Unimplemented detailed application phase')
    return p.compare_profile(expected[phase],normalize_observations(observation))


def validate_profile_binding(snapshot,raw):
    """Exact signed prepared-profile bytes, with no raw/normalized digest equivalence."""
    from .layers import read_snapshot
    from migrations.dev09b_prerequisites import decode_profile
    payload,target,executor,plan,semantic,physical,provenance=read_snapshot(snapshot)
    c.require(type(raw) is bytes and sha256(raw).hexdigest()==physical['prepared_profile_sha256'])
    profile=decode_profile(raw);params=physical['parameters']
    c.require(profile['operation']==OPERATION and profile['target_sha256']==payload['target_binding_sha256'])
    c.require(profile['database']==target['database_name'] and profile['system_identifier']==target['system_identifier'])
    c.require(profile['migrator']==params['roles']['migrator'])
    c.require(profile['schema_owners']=={k:params['roles'][k+'_owner'] for k in ('inventory','audit','security')})
    for key in ('version','schema','owner'):c.require(profile['btree_gist'][key]==params['btree_gist'][key])
    c.require(profile['source_inventory_sha256']==document_hash(provenance['source_inventory']))
    # Legacy query-row member/ACL digests stay distinct from normalized object
    # hashes. Their exact bytes are signed above; operational policy must still
    # authenticate the profile and its independent artifact resolver.
