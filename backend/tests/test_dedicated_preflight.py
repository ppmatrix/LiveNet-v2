"""Read-only candidate plan validation; no daemon, database or real secrets."""
import json
import os
from pathlib import Path
import re
import runpy

import pytest

ROOT = Path(__file__).resolve().parents[2]
ns = runpy.run_path(str(ROOT / 'scripts/dedicated/preflight.py'))
validate, InvalidPlan = ns['validate'], ns['InvalidPlan']


@pytest.fixture
def candidate():
    values = dict(DEV04_PROJECT='dev05b-test', DEV05_CADDY_BASE_IMAGE='caddy@sha256:'+'e'*64, DEV04_CADDY_IMAGE='caddy@sha256:'+'a'*64,
                  DEV04_POSTGRES_IMAGE='postgres@sha256:'+'b'*64, DEV04_BACKEND_IMAGE='sha256:'+'c'*64,
                  DEV04_PYTHON_IMAGE='python@sha256:'+'d'*64, DEV04_HTTPS_BIND_IP='192.168.50.20',
                  DEV04_CADDY_IPV4='172.30.240.10', DEV04_API_SUBNET='172.30.240.0/24',
                  DEV04_DATA_SUBNET='172.30.241.0/24', DEV05_ALLOWED_CLIENTS='192.168.50.0/24',
                  DEV04_DB_NAME='dev05b_synthetic', DEV04_DB_BOOTSTRAP_ROLE='bootstrap',
                  DEV04_FRONTEND_DIST='/private/frontend',DEV04_BACKEND_CONFIG='/private/backend.json',
                  DEV04_RUNTIME_PASSWORD_FILE='/private/password', DEV04_CSRF_KEY_FILE='/private/csrf',
                  DEV04_PG_ADMIN_PASSWORD_FILE='/private/admin')
    plan=json.loads(re.sub(r'\$\{([A-Z0-9_]+):\?[^}]*\}',lambda m:values[m[1]],(ROOT/'compose.dedicated.yaml').read_text()))
    plan['services']['web']['volumes'][1]['source']=str(ROOT/'infra/dedicated/Caddyfile')
    settings=dict(ENVIRONMENT='production',DATABASE_HOST='db',DATABASE_PORT=5432,DATABASE_NAME='dev05b_synthetic',
                  DATABASE_USER='runtime',DATABASE_PASSWORD_FILE='/run/livenet/runtime_password',
                  SECURITY_CSRF_KEY_FILE='/run/livenet/csrf_key',SECURITY_ENABLED=True,PROXY_ENABLED=True,
                  PROXY_PEERS=['172.30.240.10'],SECURITY_HTTPS_ORIGIN='https://livenet-v2.home.arpa:8443')
    policy=dict(allowed_bind_addresses=['192.168.50.20'],allowed_client_networks=['192.168.50.0/24'],reserved_networks=['10.0.0.0/8'])
    return plan,settings,policy


def test_valid_candidate_remains_blocked_and_does_not_attest_firewall(candidate):
    assert validate(*candidate,inspect_files=False)==dict(configuration='valid',activation='blocked',network_enforcement='not_attested')


@pytest.mark.parametrize('address',['0.0.0.0','127.0.0.1','::','8.8.8.8','192.168.50.99'])
def test_public_wildcard_loopback_and_unallocated_bind_refused(candidate,address):
    candidate[0]['services']['web']['ports'][0]['host_ip']=address
    with pytest.raises(InvalidPlan): validate(*candidate,inspect_files=False)


@pytest.mark.parametrize('clients',['0.0.0.0/0','8.8.8.8/32','192.168.51.0/24','192.168.50.0/24 192.168.50.0/24'])
def test_client_ranges_must_match_explicit_internal_policy(candidate,clients):
    candidate[0]['services']['web']['environment']['LIVENET_ALLOWED_CLIENTS']=clients
    with pytest.raises(InvalidPlan): validate(*candidate,inspect_files=False)


@pytest.mark.parametrize('peer',['172.30.240.0','172.30.240.1','172.30.240.255','172.30.241.10','172.30.240.11'])
def test_proxy_peer_must_be_usable_and_match_configuration(candidate,peer):
    candidate[0]['services']['web']['networks']['api']['ipv4_address']=peer
    with pytest.raises(InvalidPlan): validate(*candidate,inspect_files=False)


@pytest.mark.parametrize('subnet',['172.30.240.0/24','10.5.0.0/24','192.168.50.0/24','8.8.8.0/24'])
def test_network_overlap_reserved_client_and_public_subnets_refused(candidate,subnet):
    candidate[0]['networks']['data']['ipam']['config'][0]['subnet']=subnet
    with pytest.raises(InvalidPlan): validate(*candidate,inspect_files=False)


@pytest.mark.parametrize('change',[{'DATABASE_HOST':'existing-db'},{'DATABASE_NAME':'livenet'},
    {'DATABASE_USER':'bootstrap'},{'DATABASE_USER':'postgres'},{'PROXY_ENABLED':False},
    {'SECURITY_ENABLED':False},{'SECURITY_HTTPS_ORIGIN':'http://evil.test'},
    {'DATABASE_PASSWORD_FILE':'/private/password'}])
def test_runtime_identity_and_security_contracts_are_not_relaxed(candidate,change):
    candidate[1].update(change)
    with pytest.raises(InvalidPlan): validate(*candidate,inspect_files=False)


def test_shared_secret_sources_refused(candidate):
    mounts=candidate[0]['services']['backend']['volumes']; mounts[2]['source']=mounts[1]['source']
    with pytest.raises(InvalidPlan): validate(*candidate,inspect_files=False)


@pytest.mark.parametrize('mode',[0o644,0o640,0o666])
def test_private_file_rejects_group_and_world_access(tmp_path,mode):
    p=tmp_path/'synthetic';p.write_text('synthetic');p.chmod(mode)
    with pytest.raises(InvalidPlan): ns['private_file'](str(p),os.getuid())


def test_private_file_rejects_symlink_owner_and_relative_path(tmp_path):
    p=tmp_path/'synthetic';p.write_text('synthetic');p.chmod(0o600)
    assert ns['private_file'](str(p),os.getuid())
    link=tmp_path/'link';link.symlink_to(p)
    for path,uid in [(str(link),os.getuid()),(str(p),os.getuid()+1),('relative',os.getuid())]:
        with pytest.raises(InvalidPlan): ns['private_file'](path,uid)


def test_hash_lock_covers_exact_candidate_set():
    pins={}
    for line in (ROOT/'backend/requirements-container.constraints.txt').read_text().splitlines():
        if line and not line.startswith('#'):
            name,version=line.split('==');pins[name.lower().replace('_','-')]=version
    locked={}
    for line in (ROOT/'backend/requirements-container.lock').read_text().splitlines():
        if line and not line.startswith('#'):
            match=re.fullmatch(r'([\w-]+)==([\w.]+) --hash=sha256:([0-9a-f]{64})',line)
            assert match;locked[match[1].lower().replace('_','-')]=match[2]
    assert pins==locked and len(locked)==15


def tls_candidate(candidate):
    plan,settings,policy=candidate
    plan['services']['backend']['command'][-1]="dedicated_wsgi:create_tls_app('/run/livenet/backend.json')"
    plan['services']['backend']['volumes'].append({'type':'bind','source':'/private/ca.crt',
        'target':'/run/livenet/ca.crt','read_only':True,'bind':{'create_host_path':False}})
    settings.update(DATABASE_SSLMODE='verify-full',DATABASE_SSLROOTCERT_FILE='/run/livenet/ca.crt')
    return plan,settings,policy


def test_tls_candidate_is_explicit_and_remains_blocked(candidate):
    assert validate(*tls_candidate(candidate),inspect_files=False)['activation']=='blocked'


@pytest.mark.parametrize('fault',['mode','missing_ca','unsafe_mount','wrong_target','missing_key','legacy_command'])
def test_tls_candidate_refusals(candidate,fault):
    plan,settings,policy=tls_candidate(candidate)
    if fault=='mode': settings['DATABASE_SSLMODE']='require'
    elif fault=='missing_ca': plan['services']['backend']['volumes'].pop()
    elif fault=='unsafe_mount': plan['services']['backend']['volumes'][-1]['read_only']=False
    elif fault=='wrong_target': settings['DATABASE_SSLROOTCERT_FILE']='/untrusted/ca.crt'
    elif fault=='missing_key': settings.pop('DATABASE_SSLROOTCERT_FILE')
    else: plan['services']['backend']['command'][-1]="dedicated_wsgi:create_app('/run/livenet/backend.json')"
    with pytest.raises(InvalidPlan): validate(plan,settings,policy,inspect_files=False)
