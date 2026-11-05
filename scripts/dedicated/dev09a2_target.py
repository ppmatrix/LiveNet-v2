"""Executable specification only: allocates no resources, reads no secret.

A reserved run name is not authorization. SID/CA/container/network evidence can
only be collected after separately authorized creation and independent review.
"""
import json
from pathlib import Path
import re
import uuid

PG_REF = 'postgres@sha256:f4610795587492cd4fb887c2dc3de301b813278bb6f616992061141b5f15ac36'
PG_ID = 'sha256:6a2e324ebe59af6031c4c1cd96c1d5072c2ebc36563d2196365e43b8297c062d'


def specification(run):
    if type(run) is not str or not re.fullmatch(r'livenet-dev09b-[0-9a-f]{10}',run):
        raise ValueError('RUN_REFUSED')
    suffix=run.rsplit('-',1)[1]
    return {'kind':'FUTURE_DEV09B_DISPOSABLE_SPEC','status':'NOT_APPROVED','executable_migrations':False,
      'run':run,'environment':'DEV','profile':'MVP','application':'f066a01a7230','security':'b12b01a7230',
      'image_reference':PG_REF,'image_id':PG_ID,'postgres_major':16,
      'database':'livenet_v2_dev_'+suffix,'hostname':run+'-db','port':5432,
      'network':{'name':run+'-data','internal':True,'ipv6':False,'members':['db','executor'],
                 'published_ports':[],'operational_connections':False},
      'storage':{'type':'tmpfs','path':'/var/lib/postgresql/data','persistent_volumes':False},
      'tls':{'mode':'verify-full','ca':'generate fresh synthetic CA after approval',
             'san':run+'-db','private_directory_mode':'0700','private_file_mode':'0600',
             'credentials':'generate per-run and per-role; never use operational inputs'},
      'roles':{'owners':'lnv2_dev_{db,inventory,audit,security}_owner NOLOGIN',
               'migrator':'lnv2_dev_migrator LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS',
               'runtime':'lnv2_dev_runtime non-owner, D05 only after separate grant approval',
               'inspector':'lnv2_dev_inspector catalogs/approved ledgers only',
               'recovery':'lnv2_dev_admin independent administration channel, never application runtime',
               'grants_status':'BLOCKED: concrete phase-specific matrix and btree_gist window need review'},
      'identity_pending':{'system_identifier':None,'ca_sha256':None,'container_id':None,'network_id':None},
      'precreation_checks':['verify local RepoDigest maps to image ID','refuse any matching existing run/container/network name',
                            'no existing volume/bind/operational credential accepted'],
      'postcreation_checks':['independent pg_controldata plus SQL SID/version/database/role and peer address',
                            'verify-full CA and SAN; exact image/container/network/storage evidence',
                            'exclusive members, no ports, no default route, fresh initdb',
                            'empty application/security ledgers and no application schemas',
                            'independent identity and authorization review before DDL'],
      'cleanup':['record new full resource IDs with run label; revalidate ownership before removal',
                 'remove own containers, verify empty owned network then remove it; no prune',
                 'refuse unexpected named/anonymous volumes; remove only own synthetic credentials',
                 'compare preexisting resource IDs and require zero own leftovers'],
      'migration_command':None,'approval_required':['source/patch approval','authenticated authority contract',
          'concrete target and grants/recovery approval','new explicit DEV09B execution authorization']}


def validate(spec):
    if type(spec) is not dict or spec != specification(spec.get('run')):
        raise ValueError('SPECIFICATION_DIVERGENCE')
    return spec


def verify_image(metadata):
    if (type(metadata) is not dict or metadata.get('Id')!=PG_ID
        or PG_REF not in (metadata.get('RepoDigests') or [])
        or metadata.get('Os')!='linux' or metadata.get('Architecture')!='amd64'):
        raise ValueError('LOCAL_IMAGE_DIVERGENCE')


def refuse_collisions(spec, existing_names):
    validate(spec)
    if type(existing_names) is not tuple or any(type(n) is not str for n in existing_names):
        raise ValueError('COLLISION_INVENTORY_REFUSED')
    if any(n==spec['run'] or n.startswith(spec['run']+'-') for n in existing_names):
        raise ValueError('RESOURCE_COLLISION')


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',required=True)
    a=p.parse_args()
    print(json.dumps(specification(a.run),indent=2))
