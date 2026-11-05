"""DEV-05B native packaging check. Local Docker, cached images, no host ports.

Creates only uniquely labelled disposable containers/internal networks. PostgreSQL
uses tmpfs, a synthetic bootstrap credential and NO application migrations/users.
No real checker is supplied: readiness MUST remain 503. No operational activation.
"""
import argparse
import ipaddress
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
CADDY_SOURCE = 'caddy@sha256:eb4d35b7452d1ab6171fbdbe8d9275b2301dad6dad92115d91e19fb9b24d510f'
CADDY = 'livenet-dev05b/caddy:integration'
POSTGRES = 'postgres@sha256:f4610795587492cd4fb887c2dc3de301b813278bb6f616992061141b5f15ac36'
PYTHON = 'python@sha256:dc9e92fcdc085ad86dda976f4cfc58856dba33a438a16db37ff00151b285c8ca'
HOST = 'livenet-v2.home.arpa'
ECHO = '''from http.server import BaseHTTPRequestHandler,HTTPServer
import json
class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  body=json.dumps({'headers':list(self.headers.items()),'path':self.path,'peer':self.client_address[0]}).encode(); self.send_response(200); self.end_headers(); self.wfile.write(body)
 def log_message(self,*args): pass
HTTPServer(('0.0.0.0',8000),Handler).serve_forever()
'''
CLIENT = '''import socket,ssl,http.client,json,sys
args=json.loads(sys.argv[1]); ctx=ssl.create_default_context(cafile='/public/root.crt')
raw=socket.create_connection(('web',8443),timeout=5)
s=ctx.wrap_socket(raw,server_hostname='livenet-v2.home.arpa')
c=http.client.HTTPConnection('livenet-v2.home.arpa',8443,timeout=5); c.sock=s
c.putrequest(args.get('method','GET'),args['path'],skip_host=True)
c.putheader('Host',args.get('host','livenet-v2.home.arpa:8443'))
for k,v in args.get('headers',[]): c.putheader(k,v)
c.endheaders(); r=c.getresponse(); print(json.dumps({'status':r.status,'headers':r.getheaders(),'body':r.read().decode()}))
'''


def run_check(image):
    prefix = 'livenet-dev05b-' + uuid.uuid4().hex[:10]
    containers, networks, checks = [], [], []
    work = Path(tempfile.mkdtemp(prefix=prefix + '-'))
    public = work / 'public'; public.mkdir(mode=0o755)
    work.chmod(0o755)
    def docker(*args, input=None):
        result = subprocess.run(['docker','--host','unix:///var/run/docker.sock', *map(str,args)], input=input, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120,
                                env={k:v for k,v in os.environ.items() if not k.startswith(('DEV04_','DEV05_'))})
        if result.returncode:
            # Do not echo commands, config, credentials or arbitrary Docker logs.
            fd, filename = tempfile.mkstemp(prefix=prefix+'-docker-error-'); os.close(fd); error_path = Path(filename); error_path.write_text(result.stderr)
            raise RuntimeError('Docker step failed: ' + str(args[0]) + ' (private diagnostics: '+str(error_path)+')')
        return (result.stdout + (result.stderr if args[0]=='logs' else '')).strip()
    def start(role, args, *, detach=True):
        name = prefix + '-' + role
        containers.append(name)
        command = ['run', '--pull=never', '--name',name,'--label','livenet.dev05b='+prefix]
        if detach: command.append('-d')
        return docker(*command,*args)
    def remove_name(name):
        owner = docker('inspect','--format','{{index .Config.Labels "livenet.dev05b"}}',name)
        if owner != prefix:
            raise RuntimeError('Refusing cleanup of a container without this run label')
        docker('rm','-f',name)
    def remove(role):
        name=prefix+'-'+role; remove_name(name); containers.remove(name)
    def request(path, *, headers=(), method='GET', host=None, denied=False):
        args={'path':path,'headers':headers,'method':method}
        if host: args['host']=host
        result=start('request',['--network',networks[0],'--ip',str(edge.network_address+(11 if denied else 10)),
                  '--read-only','--cap-drop=ALL','--security-opt=no-new-privileges:true',
                  '--mount',f'type=bind,src={public},dst=/public,readonly',image,'python','-B','-c',CLIENT,json.dumps(args)],detach=False)
        remove('request')
        return json.loads(result)
    try:
        endpoint=docker('context','inspect','--format','{{.Endpoints.docker.Host}}')
        if endpoint != 'unix:///var/run/docker.sock':
            raise RuntimeError('Local Unix Docker daemon required')
        # Require exact local image content, never an implicit pull.
        image=docker('image','inspect','--format','{{.Id}}',image)
        for role in ('edge','api','data'):
            name=prefix+'-'+role
            docker('network','create','--internal','--label','livenet.dev05b='+prefix,name)
            networks.append(name)
        edge, api, data = [ipaddress.ip_network(json.loads(docker('network','inspect',n))[0]['IPAM']['Config'][0]['Subnet']) for n in networks]
        peer=str(api.network_address+10)
        values={'ENVIRONMENT':'production','DATABASE_HOST':'db','DATABASE_PORT':5432,
                'DATABASE_NAME':'dev05b_synthetic','DATABASE_USER':'dev05b_runtime',
                'DATABASE_PASSWORD_FILE':'/run/livenet/runtime_password','SECURITY_ENABLED':True,
                'SECURITY_CSRF_KEY_FILE':'/run/livenet/csrf_key','SECURITY_HTTPS_ORIGIN':'https://'+HOST+':8443',
                'PROXY_ENABLED':True,'PROXY_PEERS':[peer]}
        # Write only synthetic files; ownership must match the actual runtime UID.
        setup="""import os,json,pathlib,sys
p=pathlib.Path('/work'); values=json.loads(sys.argv[1])
for name,value,uid in [('backend.json',json.dumps(values),10001),('runtime_password','synthetic-not-provisioned',10001),('csrf_key','synthetic-csrf-only-'+('x'*40),10001),('admin_password','synthetic-admin-only-'+('y'*32),0)]:
 q=p/name; q.write_text(value); q.chmod(0o600); os.chown(q,uid,uid)
"""
        start('setup',['--user','0:0','--network','none','--mount',f'type=bind,src={work},dst=/work',image,'python','-B','-c',setup,json.dumps(values)],detach=False)
        remove('setup')
        (public/'index.html').write_text('DEV05B synthetic UI sentinel')
        (public/'echo.py').write_text(ECHO)
        env={'DEV04_PROJECT':prefix,'DEV04_CADDY_IMAGE':docker('image','inspect','--format','{{.Id}}',CADDY),'DEV05_CADDY_BASE_IMAGE':CADDY_SOURCE,'DEV04_BACKEND_IMAGE':image,
             'DEV04_POSTGRES_IMAGE':POSTGRES,'DEV04_PYTHON_IMAGE':PYTHON,
             'DEV04_HTTPS_BIND_IP':'192.168.254.253','DEV04_FRONTEND_DIST':str(public),
             'DEV04_CADDY_IPV4':peer,'DEV04_BACKEND_CONFIG':str(work/'backend.json'),
             'DEV04_RUNTIME_PASSWORD_FILE':str(work/'runtime_password'),
             'DEV04_CSRF_KEY_FILE':str(work/'csrf_key'),'DEV04_PG_ADMIN_PASSWORD_FILE':str(work/'admin_password'),
             'DEV04_DB_NAME':values['DATABASE_NAME'],'DEV04_DB_BOOTSTRAP_ROLE':'dev05b_bootstrap',
             'DEV04_API_SUBNET':str(api),'DEV04_DATA_SUBNET':str(data),
             'DEV05_ALLOWED_CLIENTS':str(edge.network_address+10)+'/32'}
        envfile=work/'candidate.env'; envfile.write_text(''.join(k+'='+v+'\n' for k,v in env.items())); envfile.chmod(0o600)
        plan=json.loads(docker('compose','--profile','dev04-blocked','--env-file',envfile,'-f',ROOT/'compose.dedicated.yaml','config','--format','json'))
        (work/'plan.json').write_text(json.dumps(plan)); (work/'policy.json').write_text(json.dumps({'allowed_bind_addresses':['192.168.254.253'],'allowed_client_networks':[env['DEV05_ALLOWED_CLIENTS']],'reserved_networks':[]}))
        # Read-only preflight runs as root solely to stat/read synthetic UID-10001
        # mount sources. It starts no services and never reads password contents.
        start('preflight',['--user','0:0','--network','none','--mount',f'type=bind,src={work},dst={work},readonly',
             '--mount',f'type=bind,src={ROOT},dst={ROOT},readonly',image,'python','-B','-c',
             "import runpy,json,sys; ns=runpy.run_path(sys.argv[1]); print(ns['validate'](*[json.load(open(p)) for p in sys.argv[2:]]))",
             ROOT/'scripts/dedicated/preflight.py',work/'plan.json',work/'backend.json',work/'policy.json'],detach=False)
        remove('preflight'); checks.append('native-compose-and-private-mount-preflight')
        caddyargs=['--user','10002:10002','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges:true',
                  '--tmpfs','/data:uid=10002,gid=10002,mode=700','--tmpfs','/config:uid=10002,gid=10002,mode=700',
                  '--tmpfs','/tmp:mode=1777','-e','XDG_DATA_HOME=/data','-e','XDG_CONFIG_HOME=/config',
                  '-e','LIVENET_ALLOWED_CLIENTS='+env['DEV05_ALLOWED_CLIENTS'],
                  '--mount',f'type=bind,src={ROOT}/infra/dedicated/Caddyfile,dst=/etc/caddy/Caddyfile,readonly',
                  '--mount',f'type=bind,src={public},dst=/srv,readonly']
        start('validate',['--network','none',*caddyargs,CADDY,'caddy','validate','--config','/etc/caddy/Caddyfile','--adapter','caddyfile'],detach=False)
        remove('validate')
        missing_env=work/'missing-clients.env'
        missing_env.write_text(envfile.read_text().replace('DEV05_ALLOWED_CLIENTS='+env['DEV05_ALLOWED_CLIENTS'],'DEV05_ALLOWED_CLIENTS='))
        missing_env.chmod(0o600)
        try:
            docker('compose','--profile','dev04-blocked','--env-file',missing_env,'-f',ROOT/'compose.dedicated.yaml','config','--format','json')
        except RuntimeError:
            pass
        else:
            raise AssertionError('Compose must refuse missing client CIDRs')
        checks.append('native-caddy-validation-and-compose-missing-clients-refusal')
        start('backend',['--network',networks[1],'--network-alias','backend','--user','10001:10001',
              '--mount',f'type=bind,src={public},dst=/public,readonly',image,'python','-B','/public/echo.py'])
        start('web',['--network',networks[0],'--network-alias','web',*caddyargs,CADDY,'caddy','run','--config','/etc/caddy/Caddyfile','--adapter','caddyfile'])
        docker('network','connect','--ip',peer,networks[1],prefix+'-web')
        for attempt in range(40):
            try:
                (public/'root.crt').write_text(docker('exec',prefix+'-web','cat','/data/caddy/pki/authorities/local/root.crt')); break
            except RuntimeError:
                time.sleep(0.25)
        else:
            fd, filename=tempfile.mkstemp(prefix=prefix+'-caddy-log-');os.close(fd);Path(filename).write_text(docker('logs',prefix+'-web'))
            raise RuntimeError('Synthetic Caddy CA not available; private log '+filename)
        claims=[('Forwarded','for=203.0.113.1'),('x-forwarded-for','evil'),('X-Forwarded-For','evil-again'),
                ('x-FoRwArDeD-Proto','http'),('X-Forwarded-Host','evil.test'),('X-Forwarded-Unknown','evil'),
                ('Origin','https://evil.test'),('Referer','https://evil.test/login')]
        for attempt in range(30):
            r=request('/api/v1/health',headers=claims)
            if r['status']==200: break
            time.sleep(.25)
        assert r['status']==200
        assert json.loads(r['body'])['peer']==peer
        headers=json.loads(r['body'])['headers']; forwarded={k.lower():v for k,v in headers if k.lower().startswith('x-forwarded-')}
        assert forwarded=={'x-forwarded-for':str(edge.network_address+10),'x-forwarded-host':HOST+':8443','x-forwarded-proto':'https','x-forwarded-port':'8443'}, forwarded
        assert not any(k.lower()=='forwarded' for k,v in headers)
        assert len([k for k,v in headers if k.lower()=='x-forwarded-for'])==1
        assert dict(headers)['Origin']=='https://evil.test' and dict(headers)['Referer']=='https://evil.test/login'
        assert request('/api/v1/health',denied=True)['status']==403
        assert request('/api/v1/health',host='evil.test')['status']!=200
        assert request('/login')['body']=='DEV05B synthetic UI sentinel'
        assert request('/api/v1/not-found')['body']!='DEV05B synthetic UI sentinel'
        checks.append('real-caddy-tls-headers-duplicates-case-origin-client-acl-and-routing')
        remove('backend')
        backendargs=['--network',networks[1],'--network-alias','backend','--read-only','--cap-drop=ALL',
                     '--security-opt=no-new-privileges:true','--tmpfs','/tmp:mode=1777',
                     '--mount',f'type=bind,src={work}/backend.json,dst=/run/livenet/backend.json,readonly',
                     '--mount',f'type=bind,src={work}/runtime_password,dst=/run/livenet/runtime_password,readonly',
                     '--mount',f'type=bind,src={work}/csrf_key,dst=/run/livenet/csrf_key,readonly',image]
        start('backend',backendargs); docker('network','connect',networks[2],prefix+'-backend')
        for attempt in range(40):
            r=request('/api/v1/health',headers=claims)
            if r['status']==200: break
            time.sleep(.25)
        assert r['status']==200, (r['status'],r['body'],docker('logs',prefix+'-backend'))
        assert json.loads(r['body'])=={'service':'livenet-api','status':'ok'}
        direct = start('direct-probe',['--network',networks[1],image,'python','-B','-c',
                    "import http.client; c=http.client.HTTPConnection('backend',8000,timeout=5); c.request('GET','/api/v1/health',headers={'Host':'livenet-v2.home.arpa:8443','X-Forwarded-Host':'livenet-v2.home.arpa:8443','X-Forwarded-Proto':'https','X-Forwarded-For':'192.168.1.1'}); print(c.getresponse().status)"],detach=False)
        remove('direct-probe'); assert direct=='403'
        assert request('/api/v1/ready')['status']==503
        assert request('/api/v1/auth/me')['status']==401
        assert request('/api/v1/inventory/resources')['status']==401
        assert request('/api/v1/auth/logout',method='POST',headers=[('Origin','https://evil.test')])['status']==403
        csrf=request('/api/v1/auth/csrf'); assert csrf['status']==200
        cookie=next(v for k,v in csrf['headers'] if k.lower()=='set-cookie')
        assert all(v in cookie for v in ('Secure','HttpOnly','SameSite=Lax'))
        checks.append('real-gunicorn-factory-health-csrf-anonymous-auth-inventory-readiness-negative')
        # Dedicated tmpfs-only PostgreSQL; no volume and no migrations/ACL changes.
        start('db',['--network',networks[2],'--network-alias','db','--tmpfs','/var/lib/postgresql/data',
                    '-e','POSTGRES_DB=dev05b_synthetic','-e','POSTGRES_USER=dev05b_bootstrap',
                    '-e','POSTGRES_PASSWORD_FILE=/run/bootstrap/password',
                    '-e','POSTGRES_INITDB_ARGS=--auth-host=scram-sha-256 --auth-local=scram-sha-256',
                    '--mount',f'type=bind,src={work}/admin_password,dst=/run/bootstrap/password,readonly',POSTGRES])
        for attempt in range(60):
            try:
                docker('exec',prefix+'-db','pg_isready','-q','-U','dev05b_bootstrap','-d','dev05b_synthetic'); break
            except RuntimeError: time.sleep(.25)
        else: raise RuntimeError('Synthetic PostgreSQL did not start')
        # First app DB access is impossible at startup: no database existed then.
        assert request('/api/v1/ready')['status']==503
        assert request('/api/v1/health')['status']==200
        docker('restart',prefix+'-backend')
        for attempt in range(40):
            r=request('/api/v1/health')
            if r['status']==200: break
            time.sleep(.25)
        assert r['status']==200 and request('/api/v1/ready')['status']==503
        checks.append('synthetic-pg16-tmpfs-and-backend-restart-no-migrations-no-positive-readiness')
        for name in containers:
            obj=json.loads(docker('inspect',name))[0]
            assert not obj['HostConfig'].get('PortBindings')
        checks.append('all-runtime-containers-have-no-host-port-bindings')
        print(json.dumps({'checks':checks,'resources_prefix':prefix,'work_directory':str(work),
                          'image':image,'status':'passed','production_readiness':False},indent=2))
    finally:
        failed=[]
        for name in reversed(containers):
            try: remove_name(name)
            except RuntimeError: failed.append(name)
        for name in reversed(networks):
            try:
                owner=docker('network','inspect','--format','{{index .Labels "livenet.dev05b"}}',name)
                if owner != prefix: raise RuntimeError('Refusing cleanup without run label')
                docker('network','rm',name)
            except RuntimeError: failed.append(name)
        # Remove synthetic private files through a container-owned, narrowly
        # mounted directory. Keep only public test evidence on the host.
        try:
            docker('run','--rm','--pull=never','--user','0:0','--network','none',
                   '--mount',f'type=bind,src={work},dst=/work',image,'python','-B','-c',
                   "from pathlib import Path; [p.unlink() for p in Path('/work').iterdir() if p.is_file()]")
        except RuntimeError: failed.append('synthetic-files:'+str(work))
        print(json.dumps({'cleanup_failures':failed,'disposable_resources_removed':not failed}))
        if failed: raise RuntimeError('Temporary cleanup incomplete')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image',default='livenet-dev05b/backend:integration')
    run_check(parser.parse_args().image)
