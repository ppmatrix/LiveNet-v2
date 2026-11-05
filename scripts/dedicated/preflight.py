"""Read-only validation of a rendered dedicated Compose plan, never deployment.

A policy file is an explicit candidate allocation, not evidence of human approval
or of firewall/routing enforcement. This command never connects to PostgreSQL.
"""
import argparse
import ipaddress as ip
import json
from pathlib import Path
import re
import stat

PRIVATE = tuple(ip.ip_network(n) for n in ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16'))
ORIGIN = 'https://livenet-v2.home.arpa:8443'


class InvalidPlan(ValueError):
    pass


def require(condition):
    if not condition:
        raise InvalidPlan('Dedicated plan refused; no activation authorized')


def internal(network):
    return network.version == 4 and any(network.subnet_of(n) for n in PRIVATE)


def read_json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result); result[key] = value
        return result
    return json.loads(Path(path).read_text(), object_pairs_hook=pairs,
                      parse_constant=lambda value: require(False))


def private_file(path, uid):
    p = Path(path)
    require(p.is_absolute() and '..' not in p.parts)
    require(all(not parent.is_symlink() for parent in (p, *p.parents)))
    st = p.lstat()
    require(stat.S_ISREG(st.st_mode) and st.st_uid == uid
            and stat.S_IMODE(st.st_mode) & 0o077 == 0 and 0 < st.st_size <= 16384)
    return (st.st_dev, st.st_ino)


def validate(plan, settings, policy, *, inspect_files=True):
    services = plan['services']
    require(set(services) == {'web', 'backend', 'db'})
    command=services['backend']['command']
    prefix=['gunicorn','--config','/app/gunicorn_container.conf.py']
    legacy=prefix+["dedicated_wsgi:create_app('/run/livenet/backend.json')"]
    secure=prefix+["dedicated_wsgi:create_tls_app('/run/livenet/backend.json')"]
    require(command in (legacy,secure))
    tls=command==secure
    keys={'ENVIRONMENT','DATABASE_HOST','DATABASE_PORT','DATABASE_NAME',
          'DATABASE_USER','DATABASE_PASSWORD_FILE','SECURITY_ENABLED',
          'SECURITY_CSRF_KEY_FILE','SECURITY_HTTPS_ORIGIN','PROXY_ENABLED','PROXY_PEERS'}
    require(set(settings) == keys | ({'DATABASE_SSLMODE','DATABASE_SSLROOTCERT_FILE'} if tls else set()))
    web, backend, db = (services[k] for k in ('web', 'backend', 'db'))
    require(set(web['networks']) == {'edge', 'api'}
            and set(backend['networks']) == {'api', 'data'}
            and set(db['networks']) == {'data'})
    require(not backend.get('ports') and not db.get('ports') and not backend.get('environment'))
    require('POSTGRES_PASSWORD' not in db['environment'])
    require(not any(v.get('external', False) for v in plan['volumes'].values()))
    require(re.fullmatch(r'[^\s]+@sha256:[0-9a-f]{64}', web['build']['args']['DEV05_CADDY_BASE_IMAGE']))
    for service in services.values():
        require(not any(k in service for k in ('network_mode', 'privileged', 'extends')))
        require(service['entrypoint'] == ['/bin/sh', '-c', 'exit 78'])
        require(re.fullmatch(r'(?:[^\s]+@)?sha256:[0-9a-f]{64}', service['image']))
    require(re.fullmatch(r'[^\s]+@sha256:[0-9a-f]{64}', backend['build']['args']['DEV04_PYTHON_IMAGE']))
    require(web['user'] == '10002:10002' and backend['user'] == '10001:10001')
    ports = web['ports']
    require(len(ports) == 1 and ports[0]['target'] == 8443
            and str(ports[0]['published']) == '8443' and ports[0]['protocol'] == 'tcp')
    bind = ip.ip_address(ports[0]['host_ip'])
    require(bind.version == 4 and any(bind in n for n in PRIVATE)
            and str(bind) in policy['allowed_bind_addresses'])
    raw_clients = web['environment']['LIVENET_ALLOWED_CLIENTS']
    clients = [ip.ip_network(n, strict=True) for n in raw_clients.split()]
    require(clients and len(set(clients)) == len(clients)
            and all(internal(n) for n in clients))
    require(set(map(str, clients)) == set(policy['allowed_client_networks']))
    nets = []
    for name in ('api', 'data'):
        spec = plan['networks'][name]
        require(spec['internal'] is True and spec['driver'] == 'bridge')
        require(len(spec['ipam']['config']) == 1)
        network = ip.ip_network(spec['ipam']['config'][0]['subnet'], strict=True)
        require(internal(network) and network.num_addresses >= 8)
        nets.append(network)
    require(not nets[0].overlaps(nets[1]))
    reserved = [ip.ip_network(n, strict=True) for n in policy['reserved_networks']]
    require(not any(a.overlaps(b) for a in nets for b in reserved + clients))
    peer = ip.ip_address(web['networks']['api']['ipv4_address'])
    gateway = ip.ip_address(plan['networks']['api']['ipam']['config'][0].get('gateway', str(nets[0].network_address + 1)))
    require(peer in nets[0] and peer not in (nets[0].network_address, nets[0].broadcast_address, gateway))
    require(settings['PROXY_PEERS'] == [str(peer)] and settings['PROXY_ENABLED'] is True
            and settings['SECURITY_ENABLED'] is True and settings['ENVIRONMENT'] == 'production'
            and settings['SECURITY_HTTPS_ORIGIN'] == ORIGIN)
    require(settings['DATABASE_HOST'] == 'db' and settings['DATABASE_PORT'] == 5432
            and settings['DATABASE_NAME'] == db['environment']['POSTGRES_DB']
            and settings['DATABASE_NAME'] not in ('livenet', 'postgres', 'template0', 'template1'))
    role = settings['DATABASE_USER']
    require(re.fullmatch(r'[a-z][a-z0-9_]{0,62}', role)
            and role != db['environment']['POSTGRES_USER'] and not role.startswith('pg_') and role != 'postgres')
    require(settings['DATABASE_PASSWORD_FILE'] == '/run/livenet/runtime_password'
            and settings['SECURITY_CSRF_KEY_FILE'] == '/run/livenet/csrf_key')
    if tls:
        require(settings['DATABASE_SSLMODE']=='verify-full'
                and settings['DATABASE_SSLROOTCERT_FILE']=='/run/livenet/ca.crt')
        mounts=[m for m in backend['volumes'] if m['target']=='/run/livenet/ca.crt']
        require(len(mounts)==1)
        ca=mounts[0]
        require(ca['type']=='bind' and ca['read_only'] is True and ca['bind']['create_host_path'] is False)
        if inspect_files:
            path=Path(ca['source'])
            require(path.is_absolute() and '..' not in path.parts and all(not p.is_symlink() for p in (path,*path.parents)))
            info=path.lstat()
            require(stat.S_ISREG(info.st_mode) and info.st_uid in (0,10001)
                    and stat.S_IMODE(info.st_mode)&0o022==0 and 0 < info.st_size <= 1048576)
            import ssl
            context=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.load_verify_locations(cadata=path.read_text('ascii'))
    identities, paths = [], []
    for service, expected in ((backend, {'/run/livenet/backend.json': 10001,
                                        '/run/livenet/runtime_password': 10001,
                                        '/run/livenet/csrf_key': 10001}),
                              (db, {'/run/postgres-bootstrap/password': 0})):
        mounts = {m['target']: m for m in service['volumes']}
        for target, uid in expected.items():
            m = mounts[target]
            require(m['type'] == 'bind' and m['read_only'] is True
                    and m['bind']['create_host_path'] is False)
            require(Path(m['source']).is_absolute())
            paths.append(m['source'])
            if inspect_files:
                identities.append(private_file(m['source'], uid))
    if inspect_files:
        config_mount = next(m for m in backend['volumes'] if m['target'] == '/run/livenet/backend.json')
        require(read_json(config_mount['source']) == settings)
    require(len(set(paths)) == 4 and (not inspect_files or len(set(identities)) == 4))
    for service in services.values():
        for m in service.get('volumes', []):
            if m['type'] == 'bind':
                require(m['read_only'] is True and m['bind']['create_host_path'] is False)
                p = Path(m['source'])
                require(p.is_absolute() and '..' not in p.parts)
                if inspect_files:
                    require(p.exists() and all(not x.is_symlink() for x in (p, *p.parents)))
    return {'configuration': 'valid', 'activation': 'blocked', 'network_enforcement': 'not_attested'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('plan', 'settings', 'policy'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    try:
        values = [read_json(getattr(args, n)) for n in ('plan', 'settings', 'policy')]
        print(json.dumps(validate(*values)))
    except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError, RecursionError):
        parser.exit(1, 'Dedicated preflight refused (details suppressed to protect configuration)\n')


if __name__ == '__main__':
    main()
