"""Fixed dedicated-owner own-session settings helper policy.

Administrative authorization is external to this module. A declaration,
source digest or successful observation is not operational authorization.
"""
from . import codec as c

SOURCE='scripts/postgres/dev09b_own_settings.proposed.sql'
SOURCE_SHA256='6cd4d512e4b383db2728040743f454e69ccc7c14495e5ffd04b8b071f4a508f4'
IDENTITY=['public','dev09b_own_preload_settings','']
TARGET_SID='7705421224394444834'
DATABASE='livenet_v2_dev'
ADMIN='dev09b_trial_admin'
OWNER='dev09b_trial_settings_owner'
PROBE='dev09b_trial_probe'
NAMES={'shared_preload_libraries','session_preload_libraries'}
BODY="""SELECT pg_catalog.pg_backend_pid(),wanted.name,pg_catalog.current_setting(wanted.name)
  FROM (VALUES ('shared_preload_libraries'::pg_catalog.text),('session_preload_libraries'::pg_catalog.text)) wanted(name)"""
OBJECT=dict(family='routine',identity=IDENTITY,definition=dict(returns='TABLE(backend_pid integer, name text, setting text)',language='sql',body=BODY,
    security_definer=True,volatility='STABLE',strict=False,parallel='UNSAFE',config=['search_path=pg_catalog']))

OWNER_ROLE=dict(name=OWNER,login=False,superuser=False,createdb=False,createrole=False,
    replication=False,bypassrls=False,inherit=False,connection_limit=0,valid_until=None)
OWNER_EDGE=dict(role='pg_read_all_settings',member=OWNER,grantor=ADMIN,admin=False,inherit=True,set=False)
SECURITY_FLAGS={name:False for name in (
    'probe_owner_member','probe_settings_member','probe_any_memberships','probe_create_public','probe_owns_public','probe_database_owner',
    'owner_create_schema','owner_database_create','owner_database_temporary','owner_database_owner','owner_role_settings',
    'owner_settings_set','settings_role_excess','owner_extra_dependency')}
SECURITY_FLAGS['owner_settings_usage']=True


def role_object(role,edge,flags):
    props={k:v for k,v in role.items() if k!='name'}
    props.update({'membership_'+k:v for k,v in edge.items() if k!='member'})
    props.update(flags)
    return dict(family='role',identity=[role['name']],definition=dict(properties=[dict(name=k,value=v) for k,v in sorted(props.items())]))

ROLE_OBJECT=role_object(OWNER_ROLE,OWNER_EDGE,SECURITY_FLAGS)


def declaration():
    # Produce a detached, typed SOURCE declaration, not a profile approval.
    return c.parse(c.canonical(dict(source_path=SOURCE,source_sha256=SOURCE_SHA256,target_system_identifier=TARGET_SID,database=DATABASE,owner=OWNER,
        object=OBJECT,owner_role=OWNER_ROLE,owner_membership=OWNER_EDGE,owner_security=SECURITY_FLAGS,owner_object=ROLE_OBJECT,grants=[dict(grantee=PROBE,privilege='EXECUTE',grant_option=False)])))


def validate(value):
    c.require(c.canonical(value)==c.canonical(declaration()))
    return value


def verify_observed(historical,supplemental):
    """Verify body/flags/owner/ACL BEFORE executing the elevated helper."""
    c.require(historical['identity'][0]['system_identifier']==TARGET_SID and historical['identity'][0]['database']==DATABASE)
    c.require(c.canonical(supplemental['helper_owner_role'])==c.canonical([OWNER_ROLE]))
    c.require(c.canonical(supplemental['helper_owner_edges'])==c.canonical([OWNER_EDGE]))
    c.require(c.canonical(supplemental['helper_security_flags'])==c.canonical([SECURITY_FLAGS]))
    routines=[r for r in supplemental['routine_semantics'] if [r['schema'],r['name'],r['arguments']]==IDENTITY]
    c.require(len(routines)==1);r=routines[0]
    observed=dict(returns=r['returns'],language=r['language'],body=r['body'].strip(),security_definer=r['security_definer'],
        volatility={'v':'VOLATILE','s':'STABLE','i':'IMMUTABLE'}[r['volatility']],strict=r['strict'],
        parallel={'s':'SAFE','r':'RESTRICTED','u':'UNSAFE'}[r['parallel']],config=r['config'] or [])
    c.require(c.canonical(observed)==c.canonical(OBJECT['definition']) and r['owner']==OWNER)
    raw=[x for x in historical['routines'] if [x['schema'],x['name'],x['arguments']]==IDENTITY]
    c.require(len(raw)==1 and raw[0]['security_definer'] is True and raw[0]['owner']==OWNER)
    definers=historical['executable_definers']
    if historical['identity'][0]['current_user']==PROBE:
        c.require(historical['identity'][0]['session_user']==PROBE)
        c.require(len(definers)==1 and [definers[0][k] for k in ('schema','name','arguments')]==IDENTITY
            and definers[0]['owner']==OWNER and definers[0]['definition']==raw[0]['definition'])
    else:c.require(not definers)
    grants=[]
    for row in historical['object_acl']:
        if (row['family'],row['schema'],row['name'])!=('routine',IDENTITY[0],IDENTITY[1]):continue
        c.require(row['grantor']==OWNER and row['privilege']=='EXECUTE')
        if row['grantee']!=OWNER:grants.append({k:row[k] for k in ('grantee','privilege','grant_option')})
    c.require(c.canonical(grants)==c.canonical(declaration()['grants']))
