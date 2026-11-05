"""DEV-09A disposable fixture orchestrator. Never executes application migrations.

No operational configuration or credentials accepted. Only local pinned images,
new labelled resources, synthetic inputs and tmpfs; cleanup is ownership checked.
This harness and its observations are NOT an AUTH-03/G2/G4 approval mechanism.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
PG_IMAGE = 'sha256:6a2e324ebe59af6031c4c1cd96c1d5072c2ebc36563d2196365e43b8297c062d'
CLIENT_IMAGE = 'sha256:b16b93e9ab02616547158eabe0064475e705207d1a6d7f01af9b50aa25568238'
MANIFEST_SHA256 = '4819c697b7d12f7ab5cbb1fdfa9cf4c3fd0e98e93b53a60337296cc84036fc29'
LABEL = 'livenet.dev09a'


def require_identity(expected, observed):
    """Fixture comparison only; does not issue or authenticate an authorization."""
    fields = {'run', 'database', 'hostname', 'system_identifier', 'network_id',
              'container_id', 'ca_sha256', 'runtime_role'}
    if (type(expected) is not dict or type(observed) is not dict
            or set(expected) != fields or set(observed) != fields
            or any(type(v) is not str or not v for v in expected.values())
            or expected != observed
            or not re.fullmatch(r'livenet-dev09a-[0-9a-f]{10}', expected['run'])
            or expected['database'] != 'livenet_v2_dev_' + expected['run'].rsplit('-', 1)[1]
            or expected['hostname'] != expected['run'] + '-db'
            or not expected['system_identifier'].isascii() or not expected['system_identifier'].isdecimal()
            or any(not re.fullmatch(r'[0-9a-f]{64}', expected[k])
                   for k in ('network_id', 'container_id', 'ca_sha256'))
            or expected['runtime_role'] != 'lnv2_dev_runtime'):
        raise ValueError('Fixture identity refused')


def graph(directory):
    nodes = {}
    for path in sorted(directory.glob('*.py')):
        values = {}
        for node in ast.parse(path.read_bytes(), filename=str(path)).body:
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else (node.target,)
                for target in targets:
                    if isinstance(target, ast.Name) and target.id in ('revision', 'down_revision', 'depends_on'):
                        values[target.id] = ast.literal_eval(node.value)
        revision = values.get('revision')
        if not revision or revision in nodes or values.get('depends_on') is not None:
            raise ValueError('Unexpected revision graph')
        nodes[revision] = {'down_revision': values.get('down_revision'),
                           'path': str(path.relative_to(ROOT)),
                           'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    result = []
    previous = None
    while True:
        following = [r for r, data in nodes.items() if data['down_revision'] == previous]
        if not following:
            break
        if len(following) != 1 or following[0] in result:
            raise ValueError('Ambiguous or cyclic revision graph')
        previous = following[0]
        result.append(previous)
    if len(result) != len(nodes):
        raise ValueError('Disconnected revision graph')
    return {'chain': result, 'nodes': nodes}


def static_plan():
    manifest = ROOT / 'scripts/postgres/auth03_executor_integrity.json'
    if hashlib.sha256(manifest.read_bytes()).hexdigest() != MANIFEST_SHA256:
        raise ValueError('Approved manifest changed')
    mapping = json.loads(manifest.read_text())
    expected = {str(p.relative_to(ROOT)) for d in ('backend/app', 'backend/migrations')
                for p in (ROOT / d).rglob('*.py')} | {
                    'backend/alembic.ini', 'backend/requirements.txt',
                    'scripts/postgres/auth03_alembic_executor.py'}
    if set(mapping) != expected or len(mapping) != 52:
        raise ValueError('Approved source set changed')
    for name, digest in mapping.items():
        path = ROOT / name
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError('Approved source changed')
    app = graph(ROOT / 'backend/migrations/versions')
    security = graph(ROOT / 'backend/security_migrations/versions')
    if (len(app['chain']) != 14 or app['chain'][-2:] != ['f066a01a7230', 'f067a01a7230']
            or security['chain'] != ['b12b01a7230']):
        raise ValueError('Approved destinations diverge')
    return {'status': 'STATIC_PASS_EXECUTION_BLOCKED', 'application': app,
            'security': security, 'mvp_application_path': app['chain'][:-1],
            'mvp_destinations': ['f066a01a7230', 'b12b01a7230'],
            'ledgers': ['public.alembic_version', 'public.alembic_security_version'],
            'auth03_only': 'f067a01a7230', 'migration_execution_authorized': False,
            'dev09b_executable_command': None,
            'blockers': ['Existing executors pin historical targets and keep mutations disabled.',
                         'F02/G4 authority and complementary artifact attestation remain absent.']}


def run_disposable():
    plan = static_plan()
    run = 'livenet-dev09a-' + uuid.uuid4().hex[:10]
    database = 'livenet_v2_dev_' + run.rsplit('-', 1)[1]
    hostname = run + '-db'
    work = Path(tempfile.mkdtemp(prefix=run + '-'))
    inputs = work / 'inputs'
    inputs.mkdir(mode=0o700)
    network = run + '-data'
    created_containers = {}
    created_network = None
    phase = 'initial'
    result = None
    failure = None
    cleanup_errors = []
    native_failure = None

    def docker(*args):
        proc = subprocess.run(['docker', '--host', 'unix:///var/run/docker.sock', *map(str, args)],
                              capture_output=True, text=True, timeout=90)
        if proc.returncode:
            # Do not disclose raw Docker/driver/SQL output or command arguments.
            raise RuntimeError('Docker refused phase ' + phase)
        return proc.stdout.strip()

    def inspect_container(ident):
        obj = json.loads(docker('inspect', ident))[0]
        if obj['Config']['Labels'].get(LABEL) != run:
            raise RuntimeError('Container ownership refused')
        return obj

    def remove_container(ident):
        obj = inspect_container(ident)
        if any(m['Type'] == 'volume' for m in obj['Mounts']):
            raise RuntimeError('Refusing implicit volume cleanup; investigate ownership')
        docker('rm', '-f', ident)
        created_containers.pop(ident)

    def create(role, args):
        name = run + '-' + role
        ident = docker('create', '--pull=never', '--name', name, '--label', LABEL + '=' + run, *args)
        created_containers[ident] = name
        return ident

    def start_once(role, args):
        ident = create(role, args)
        output = docker('start', '-a', ident)
        obj = inspect_container(ident)
        if obj['State']['ExitCode'] != 0:
            raise RuntimeError('Fixture refused phase ' + phase)
        remove_container(ident)
        return output

    def openssl(*args):
        proc = subprocess.run(['openssl', *map(str, args)], capture_output=True, timeout=30)
        if proc.returncode:
            raise RuntimeError('Synthetic PKI refused')

    try:
        for image in (PG_IMAGE, CLIENT_IMAGE):
            if docker('image', 'inspect', '--format', '{{.Id}}', image) != image:
                raise RuntimeError('Pinned local image unavailable')
        phase = 'synthetic-pki'
        openssl('req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', work / 'ca.key',
                '-out', inputs / 'ca.crt', '-days', '2', '-subj', '/CN=' + run + '-CA',
                '-addext', 'basicConstraints=critical,CA:TRUE')
        openssl('req', '-newkey', 'rsa:2048', '-nodes', '-keyout', work / 'server.key',
                '-out', work / 'server.csr', '-subj', '/CN=' + hostname)
        (work / 'server.ext').write_text('subjectAltName=DNS:' + hostname + '\n'
                                       'extendedKeyUsage=serverAuth\nbasicConstraints=CA:FALSE\n')
        openssl('x509', '-req', '-in', work / 'server.csr', '-CA', inputs / 'ca.crt',
                '-CAkey', work / 'ca.key', '-CAcreateserial', '-out', work / 'server.crt',
                '-days', '2', '-extfile', work / 'server.ext')
        openssl('req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', work / 'wrong-ca.key',
                '-out', inputs / 'wrong-ca.crt', '-days', '2', '-subj', '/CN=' + run + '-wrong-CA')
        for role in ('admin', 'db_owner', 'migrator', 'runtime', 'inspector'):
            path = inputs / (role + '.password')
            path.write_text(secrets.token_urlsafe(36))
            path.chmod(0o600)
        shutil.copyfile(inputs / 'admin.password', work / 'bootstrap.password')
        (work / 'bootstrap.password').chmod(0o600)
        (work / 'server.key').chmod(0o600)
        for path in (inputs / 'ca.crt', inputs / 'wrong-ca.crt', work / 'server.crt'):
            path.chmod(0o444)
        phase = 'synthetic-file-ownership'
        # CHOWN only two newly created synthetic files, with no network.
        start_once('file-owner', ['--network', 'none', '--read-only', '--user', '0:0',
                                '--cap-drop=ALL', '--cap-add=CHOWN',
                                '--security-opt=no-new-privileges:true',
                                '--tmpfs', '/var/lib/postgresql/data:uid=70,gid=70,mode=0700',
                                '--mount', f'type=bind,src={work}/server.key,dst=/owned/server.key',
                                '--mount', f'type=bind,src={work}/bootstrap.password,dst=/owned/bootstrap.password',
                                '--entrypoint', 'chown', PG_IMAGE, '70:70',
                                '/owned/server.key', '/owned/bootstrap.password'])
        phase = 'private-network'
        created_network = docker('network', 'create', '--internal', '--label', LABEL + '=' + run, network)
        net = json.loads(docker('network', 'inspect', created_network))[0]
        subnet = net['IPAM']['Config'][0]['Subnet']
        (work / 'pg_hba.conf').write_text(
            'local all all scram-sha-256\nhostnossl all all 0.0.0.0/0 reject\n'
            'hostnossl all all ::/0 reject\nhostssl ' + database + ' all ' + subnet + ' scram-sha-256\n')
        (work / 'pg_hba.conf').chmod(0o444)
        phase = 'postgres16-new-initdb'
        db = create('db', ['--network', created_network, '--network-alias', hostname,
                          '--user', '70:70', '--read-only', '--cap-drop=ALL',
                          '--security-opt=no-new-privileges:true',
                          '--tmpfs', '/var/lib/postgresql/data:uid=70,gid=70,mode=0700',
                          '--tmpfs', '/var/run/postgresql:uid=70,gid=70,mode=0770',
                          '--tmpfs', '/tmp:mode=1777',
                          '-e', 'POSTGRES_DB=' + database, '-e', 'POSTGRES_USER=lnv2_dev_admin',
                          '-e', 'POSTGRES_PASSWORD_FILE=/bootstrap/password',
                          '-e', 'POSTGRES_INITDB_ARGS=--auth-host=scram-sha-256 --auth-local=scram-sha-256',
                          '--mount', f'type=bind,src={work}/bootstrap.password,dst=/bootstrap/password,readonly',
                          '--mount', f'type=bind,src={work}/server.key,dst=/tls/server.key,readonly',
                          '--mount', f'type=bind,src={work}/server.crt,dst=/tls/server.crt,readonly',
                          '--mount', f'type=bind,src={work}/pg_hba.conf,dst=/tls/pg_hba.conf,readonly',
                          PG_IMAGE, 'postgres', '-c', 'ssl=on', '-c', 'ssl_cert_file=/tls/server.crt',
                          '-c', 'ssl_key_file=/tls/server.key', '-c', 'hba_file=/tls/pg_hba.conf',
                          '-c', 'log_statement=none', '-c', 'log_min_error_statement=panic'])
        docker('start', db)
        for _ in range(80):
            ready = subprocess.run(['docker', '--host', 'unix:///var/run/docker.sock', 'exec', db,
                                    'pg_isready', '-q', '-U', 'lnv2_dev_admin', '-d', database],
                                   capture_output=True, timeout=5)
            if ready.returncode == 0:
                break
            time.sleep(.25)
        else:
            raise RuntimeError('Disposable PostgreSQL did not become ready')
        control = docker('exec', db, 'pg_controldata', '/var/lib/postgresql/data')
        sid = next(line.split(':', 1)[1].strip() for line in control.splitlines()
                   if line.startswith('Database system identifier:'))
        db_obj = inspect_container(db)
        db_ip = db_obj['NetworkSettings']['Networks'][network]['IPAddress']
        ca_sha = hashlib.sha256((inputs / 'ca.crt').read_bytes()).hexdigest()
        identity = {'run': run, 'database': database, 'hostname': hostname,
                    'system_identifier': sid, 'network_id': created_network,
                    'container_id': db, 'ca_sha256': ca_sha, 'runtime_role': 'lnv2_dev_runtime'}
        require_identity(identity, dict(identity))
        config = {**identity, 'db_ip': db_ip}
        (inputs / 'fixture.json').write_text(json.dumps(config))
        (inputs / 'fixture.json').chmod(0o600)
        phase = 'fixture-sql-only'
        probe = create('probe', ['--network', created_network, '--read-only',
                                '--user', f'{os.getuid()}:{os.getgid()}', '--cap-drop=ALL',
                                '--security-opt=no-new-privileges:true', '--tmpfs', '/tmp:mode=1777',
                                '--mount', f'type=bind,src={inputs},dst=/inputs,readonly',
                                '--mount', f'type=bind,src={ROOT}/scripts/dedicated/dev09a_fixture_probe.py,dst=/probe.py,readonly',
                                CLIENT_IMAGE, 'python', '-B', '/probe.py'])
        docker('start', probe)
        probe_obj = inspect_container(probe)
        net = json.loads(docker('network', 'inspect', created_network))[0]
        if (not net['Internal'] or net['EnableIPv6']
                or set(net['Containers']) != {db, probe}):
            raise RuntimeError('Unexpected network membership or isolation')
        for obj in (db_obj, probe_obj):
            if (obj['HostConfig']['NetworkMode'] != created_network
                    or obj['HostConfig']['PortBindings'] or obj['HostConfig']['PublishAllPorts']
                    or obj['HostConfig']['Privileged']
                    or any(m['Type'] == 'volume' for m in obj['Mounts'])
                    or len(obj['NetworkSettings']['Networks']) != 1):
                raise RuntimeError('Unexpected container exposure/storage')
        if '/var/lib/postgresql/data' not in db_obj['HostConfig']['Tmpfs']:
            raise RuntimeError('Non-disposable PostgreSQL data')
        (inputs / 'fixture-start').write_text('isolation-verified\n')
        docker('wait', probe)
        output = docker('logs', probe)
        after = inspect_container(probe)
        if after['State']['ExitCode'] != 0:
            native_failure = json.loads(output)
            raise RuntimeError('Native fixture failed')
        sql_result = json.loads(output)
        require_identity(identity, {**identity, 'system_identifier': sql_result['system_identifier'],
                                    'database': sql_result['database']})
        result = {'status': 'PASS', 'identity': identity, 'database_ip': db_ip,
                  'postgres_image': PG_IMAGE, 'probe_image': CLIENT_IMAGE,
                  'network': {'name': network, 'id': created_network, 'internal': True,
                              'subnet': subnet, 'ports_published': False, 'members': 2},
                  'storage': 'new initdb on tmpfs; zero named/anonymous volumes',
                  'sql': sql_result, 'plan': {'targets': plan['mvp_destinations'],
                                            'execution': 'BLOCKED_NO_AUTHORIZATION'},
                  'migrations_executed': False}
    except Exception as error:
        failure = {'status': 'FAIL', 'phase': phase, 'type': type(error).__name__}
        if native_failure is not None:
            failure['native_failure'] = native_failure
    finally:
        phase = 'cleanup'
        for ident in list(reversed(created_containers)):
            try:
                remove_container(ident)
            except Exception:
                cleanup_errors.append('container ' + ident)
        if created_network:
            try:
                obj = json.loads(docker('network', 'inspect', created_network))[0]
                if obj['Labels'].get(LABEL) != run or obj['Containers']:
                    raise RuntimeError('Network cleanup ownership refused')
                docker('network', 'rm', created_network)
            except Exception:
                cleanup_errors.append('network ' + created_network)
        try:
            shutil.rmtree(work)
        except Exception:
            cleanup_errors.append('synthetic work directory')
        # Never prune or enumerate another project's resources for removal.
        remaining_containers = docker('ps', '-aq', '--filter', 'label=' + LABEL + '=' + run)
        remaining_networks = docker('network', 'ls', '-q', '--filter', 'label=' + LABEL + '=' + run)
        if remaining_containers or remaining_networks:
            cleanup_errors.append('labelled resource still present')
    outcome = failure or result
    outcome['cleanup'] = {'run': run, 'removed': not cleanup_errors,
                          'errors': cleanup_errors, 'synthetic_pki_credentials_removed': not work.exists()}
    print(json.dumps(outcome, indent=2))
    return 1 if failure or cleanup_errors else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-disposable', action='store_true')
    args = parser.parse_args(argv)
    if args.run_disposable:
        return run_disposable()
    print(json.dumps(static_plan(), indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
