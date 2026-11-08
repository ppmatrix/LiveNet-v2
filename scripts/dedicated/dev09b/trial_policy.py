"""Versioned source-only helper expectation amendment; no grant or observation."""
from copy import deepcopy
from . import codec as c,own_settings as h
from .layers import document_hash


def active_helper(parameters,context):
    params,ctx=deepcopy(parameters),deepcopy(context)
    c.require(params['roles']['migrator']==h.MIGRATOR and params['roles']['inspector']==h.PROBE)
    rows=[row for row in params['system_acls'] if row['family']=='routine' and row['identity']==h.IDENTITY]
    c.require(len(rows)==1 and rows[0]['grants']==h.declaration()['grants'])
    rows[0]['grants']=h.trial_declaration()['grants']
    ctx['approved_helpers']=[h.trial_declaration()]
    ctx['metadata']['parameters_sha256']=document_hash(params)
    ctx['metadata']['role_bindings']=dict(migrator=h.MIGRATOR,inspector=h.PROBE)
    return params,ctx


def cleaned_snapshot(active,migrator):
    """Only remove the enumerated temporary rights; never repair observations."""
    value=deepcopy(active)
    for key in ('database_acl','public_acl','control_system_acl'):
        value[key]=[g for g in value[key] if g['grantee']!=migrator]
    for row in value['acls']:
        if row['family']=='schema' and row['identity'][0] in {'public','inventory','audit'}:
            row['grants']=[g for g in row['grants'] if g['grantee']!=migrator]
    for row in value['system_acls']:
        if row['family']=='routine' and row['identity'] in (h.IDENTITY,['pg_catalog','pg_control_system','']):
            row['grants']=[g for g in row['grants'] if g['grantee']!=migrator]
    for role in value['roles']:
        if role['name']==migrator:role['login']=False
    return value
