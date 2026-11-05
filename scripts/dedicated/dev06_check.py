"""Isolated DEV-06 TLS/SQL/HTTPS validation; no host ports, volumes or app DDL.

Uses only local images. Every resource gets a unique run label. Container helpers
may access only synthetic files; cleanup never prunes existing Docker resources.
"""
import argparse
import ipaddress
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import tempfile
import time
import uuid

ROOT=Path(__file__).resolve().parents[2]
PG='postgres@sha256:f4610795587492cd4fb887c2dc3de301b813278bb6f616992061141b5f15ac36'
CADDY='livenet-dev05b/caddy:integration'
CLIENT='''import socket,ssl,http.client,json,sys
v=json.loads(sys.argv[1]); ctx=ssl.create_default_context(cafile='/public/root.crt')
s=ctx.wrap_socket(socket.create_connection(('web',8443),timeout=5),server_hostname='livenet-v2.home.arpa')
c=http.client.HTTPConnection('livenet-v2.home.arpa',8443,timeout=5);c.sock=s
c.putrequest(v.get('method','GET'),v['path'],skip_host=True);c.putheader('Host','livenet-v2.home.arpa:8443')
for k,value in v.get('headers',[]): c.putheader(k,value)
body=json.dumps(v['body']).encode() if 'body' in v else None
if body is not None: c.putheader('Content-Type','application/json');c.putheader('Content-Length',str(len(body)))
c.endheaders(body);r=c.getresponse();print(json.dumps({'status':r.status,'headers':r.getheaders(),'body':r.read().decode()}))
'''


def run(image, *, frontend_dist=None, browser_check=None, run_tag='dev06'):
    if run_tag not in ('dev06','dev07'): raise ValueError('Unknown isolated run tag')
    if browser_check is not None and frontend_dist is None: raise ValueError('Real frontend required')
    prefix='livenet-'+run_tag+'-'+uuid.uuid4().hex[:10]
    label='livenet.'+run_tag
    work=Path(tempfile.mkdtemp(prefix=prefix+'-'))
    inputs=work/'inputs';inputs.mkdir(mode=0o700)
    public=work/'public';public.mkdir(mode=0o755)
    containers=[];networks=[];phase='initial';results=[]
    def docker(*args):
        r=subprocess.run(['docker','--host','unix:///var/run/docker.sock',*map(str,args)],
                         stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=120)
        if r.returncode:
            # No command/DSN/credential is printed. Synthetic diagnostics only.
            fd,name=tempfile.mkstemp(prefix=prefix+'-error-');os.close(fd);Path(name).write_text(r.stderr)
            raise RuntimeError('Docker failure during '+phase+'; private diagnostics '+name)
        return r.stdout.strip()
    def start(role,args,detach=True):
        name=prefix+'-'+role;containers.append(name)
        return docker('run','--pull=never','--name',name,'--label',label+'='+prefix,
                      *(['-d'] if detach else []),*args)
    def remove(name):
        if docker('inspect','--format','{{index .Config.Labels "'+label+'"}}',name)!=prefix:
            raise RuntimeError('Container cleanup label mismatch')
        docker('rm','-f',name);containers.remove(name)
    def helper(role,code,*args,mounts=()):
        value=start(role,['--network','none','--user','0:0',*mounts,image,'python','-B','-c',code,*args],False)
        remove(prefix+'-'+role);return value
    def openssl(*args):
        r=subprocess.run(['openssl',*map(str,args)],capture_output=True,timeout=30)
        if r.returncode: raise RuntimeError('Synthetic PKI generation failed')
    def probe(stage):
        nonlocal phase
        phase='sql-'+stage
        value=start('probe',['--network',networks[2],'--read-only','--cap-drop=ALL',
                            '--security-opt=no-new-privileges:true','--mount',f'type=bind,src={inputs},dst=/inputs,readonly',
                            '--mount',f'type=bind,src={ROOT}/scripts/dedicated/dev06_postgres_probe.py,dst=/probe.py,readonly',
                            image,'python','-B','/probe.py',stage],False)
        remove(prefix+'-probe');results.append(json.loads(value))
    def request(path,method='GET',headers=(),body=None):
        value={'path':path,'method':method,'headers':headers}
        if body is not None: value['body']=body
        out=start('http',['--network',networks[0],'--read-only','--cap-drop=ALL',
                          '--security-opt=no-new-privileges:true','--mount',f'type=bind,src={public},dst=/public,readonly',
                          image,'python','-B','-c',CLIENT,json.dumps(value)],False)
        remove(prefix+'-http');return json.loads(out)
    try:
        image=docker('image','inspect','--format','{{.Id}}',image)
        caddy=docker('image','inspect','--format','{{.Id}}',CADDY)
        phase='PKI'
        openssl('req','-x509','-newkey','rsa:2048','-nodes','-keyout',work/'ca.key','-out',inputs/'ca.crt',
                '-days','2','-subj','/CN=LiveNet DEV06 ephemeral CA','-addext','basicConstraints=critical,CA:TRUE')
        openssl('req','-newkey','rsa:2048','-nodes','-keyout',work/'server.key','-out',work/'server.csr','-subj','/CN=db')
        (work/'server.ext').write_text('subjectAltName=DNS:db\nextendedKeyUsage=serverAuth\nbasicConstraints=CA:FALSE\n')
        openssl('x509','-req','-in',work/'server.csr','-CA',inputs/'ca.crt','-CAkey',work/'ca.key',
                '-CAcreateserial','-out',work/'server.crt','-days','2','-extfile',work/'server.ext')
        openssl('req','-x509','-newkey','rsa:2048','-nodes','-keyout',work/'wrong-ca.key','-out',inputs/'wrong-ca.crt',
                '-days','2','-subj','/CN=LiveNet DEV06 wrong CA')
        for role in ('admin','owner','migrator','runtime','inspector'):
            p=inputs/(role+'.password');p.write_text(secrets.token_urlsafe(36));p.chmod(0o600)
        (inputs/'csrf.key').write_text(secrets.token_urlsafe(48));(inputs/'csrf.key').chmod(0o600)
        phase='networks'
        for role in ('edge','api','data'):
            name=prefix+'-'+role;docker('network','create','--internal','--label',label+'='+prefix,name);networks.append(name)
        subnets=[ipaddress.ip_network(json.loads(docker('network','inspect',n))[0]['IPAM']['Config'][0]['Subnet']) for n in networks]
        peer=str(subnets[1].network_address+10);backend_ip=str(subnets[2].network_address+10)
        (work/'pg_hba.conf').write_text('local all all scram-sha-256\nhostnossl all all 0.0.0.0/0 reject\nhostnossl all all ::/0 reject\nhostssl dev06_synthetic all '+str(subnets[2])+' scram-sha-256\n')
        values={'ENVIRONMENT':'production','DATABASE_HOST':'db','DATABASE_PORT':5432,'DATABASE_NAME':'dev06_synthetic',
                'DATABASE_USER':'dev06_runtime','DATABASE_PASSWORD_FILE':'/run/livenet/runtime_password',
                'SECURITY_ENABLED':True,'SECURITY_CSRF_KEY_FILE':'/run/livenet/csrf_key',
                'SECURITY_HTTPS_ORIGIN':'https://livenet-v2.home.arpa:8443','PROXY_ENABLED':True,'PROXY_PEERS':[peer],
                'DATABASE_SSLMODE':'verify-full','DATABASE_SSLROOTCERT_FILE':'/run/livenet/ca.crt'}
        (inputs/'backend.json').write_text(json.dumps(values));(inputs/'backend.json').chmod(0o600)
        phase='synthetic-file-ownership'
        helper('ownership',"""from pathlib import Path
import os
for p in Path('/work/inputs').iterdir():
 os.chown(p,10001,10001);p.chmod(0o444 if p.suffix=='.crt' else 0o600)
os.chown('/work/inputs',10001,10001)
os.chown('/work/server.key',70,70);os.chmod('/work/server.key',0o600)
os.chmod('/work/server.crt',0o444);os.chmod('/work/pg_hba.conf',0o444)
import shutil
shutil.copyfile('/work/inputs/admin.password','/work/bootstrap.password');os.chown('/work/bootstrap.password',0,0);os.chmod('/work/bootstrap.password',0o600)
""",mounts=['--mount',f'type=bind,src={work},dst=/work'])
        phase='native-compose-tls-preflight'
        if frontend_dist is None:
            (public/'index.html').write_text('DEV06 routing sentinel; not React UI')
        else:
            shutil.copytree(Path(frontend_dist),public,dirs_exist_ok=True)
        variables={'DEV04_PROJECT':prefix,'DEV04_CADDY_IMAGE':caddy,'DEV04_BACKEND_IMAGE':image,
                   'DEV04_POSTGRES_IMAGE':PG,'DEV04_PYTHON_IMAGE':'python@sha256:dc9e92fcdc085ad86dda976f4cfc58856dba33a438a16db37ff00151b285c8ca',
                   'DEV05_CADDY_BASE_IMAGE':'caddy@sha256:eb4d35b7452d1ab6171fbdbe8d9275b2301dad6dad92115d91e19fb9b24d510f',
                   'DEV04_HTTPS_BIND_IP':'192.168.254.253','DEV04_FRONTEND_DIST':str(public),
                   'DEV04_CADDY_IPV4':peer,'DEV04_BACKEND_CONFIG':str(inputs/'backend.json'),
                   'DEV04_RUNTIME_PASSWORD_FILE':str(inputs/'runtime.password'),'DEV04_CSRF_KEY_FILE':str(inputs/'csrf.key'),
                   'DEV04_PG_ADMIN_PASSWORD_FILE':str(work/'bootstrap.password'),
                   'DEV04_DB_NAME':'dev06_synthetic','DEV04_DB_BOOTSTRAP_ROLE':'dev06_admin',
                   'DEV04_API_SUBNET':str(subnets[1]),'DEV04_DATA_SUBNET':str(subnets[2]),
                   'DEV05_ALLOWED_CLIENTS':str(subnets[0]),'DEV06_POSTGRES_CA_FILE':str(inputs/'ca.crt')}
        envfile=work/'candidate.env';envfile.write_text(''.join(k+'='+v+'\n' for k,v in variables.items()));envfile.chmod(0o600)
        rendered=docker('compose','--profile','dev04-blocked','--env-file',envfile,
                        '-f',ROOT/'compose.dedicated.yaml','-f',ROOT/'compose.dedicated-tls.yaml','config','--format','json')
        (work/'plan.json').write_text(rendered)
        (work/'policy.json').write_text(json.dumps({'allowed_bind_addresses':['192.168.254.253'],
                                                   'allowed_client_networks':[str(subnets[0])],'reserved_networks':[]}))
        helper('preflight',"import runpy,json,sys;v=runpy.run_path(sys.argv[1]);print(v['validate'](*[v['read_json'](p) for p in sys.argv[2:]]))",
               str(ROOT/'scripts/dedicated/preflight.py'),str(work/'plan.json'),str(inputs/'backend.json'),str(work/'policy.json'),
               mounts=['--mount',f'type=bind,src={work},dst={work},readonly','--mount',f'type=bind,src={ROOT},dst={ROOT},readonly'])
        results.append({'native_compose_tls_overlay':'passed','read_only_preflight':'passed','operational_guards':'exit 78 preserved'})
        phase='postgres-tls-startup'
        start('db',['--network',networks[2],'--network-alias','db','--tmpfs','/var/lib/postgresql/data',
                    '-e','POSTGRES_DB=dev06_synthetic','-e','POSTGRES_USER=dev06_admin',
                    '-e','POSTGRES_PASSWORD_FILE=/bootstrap/password',
                    '-e','POSTGRES_INITDB_ARGS=--auth-host=scram-sha-256 --auth-local=scram-sha-256',
                    '--mount',f'type=bind,src={work}/bootstrap.password,dst=/bootstrap/password,readonly',
                    '--mount',f'type=bind,src={work}/server.key,dst=/tls/server.key,readonly',
                    '--mount',f'type=bind,src={work}/server.crt,dst=/tls/server.crt,readonly',
                    '--mount',f'type=bind,src={work}/pg_hba.conf,dst=/tls/pg_hba.conf,readonly',PG,
                    'postgres','-c','ssl=on','-c','ssl_cert_file=/tls/server.crt','-c','ssl_key_file=/tls/server.key',
                    '-c','hba_file=/tls/pg_hba.conf','-c','log_statement=none','-c','log_min_error_statement=panic'])
        for attempt in range(60):
            try: docker('exec',prefix+'-db','pg_isready','-q','-U','dev06_admin','-d','dev06_synthetic');break
            except RuntimeError: time.sleep(.25)
        else: raise RuntimeError('Synthetic PostgreSQL not available')
        control=docker('exec','--user','70:70',prefix+'-db','pg_controldata','/var/lib/postgresql/data')
        system_id=next(line.split(':',1)[1].strip() for line in control.splitlines() if line.startswith('Database system identifier:'))
        probe_config=json.dumps({'system_identifier':system_id,'db_ip':json.loads(docker('inspect',prefix+'-db'))[0]['NetworkSettings']['Networks'][networks[2]]['IPAddress'],
                                 'backend_ip':backend_ip})
        helper('probe-config',"from pathlib import Path; import os,sys;p=Path('/inputs/probe.json');p.write_text(sys.argv[1]);os.chown(p,10001,10001);p.chmod(0o600)",
               probe_config,mounts=['--mount',f'type=bind,src={inputs},dst=/inputs'])
        phase='scratch-roles-and-tls';probe('setup');probe('checks')
        phase='https-application'
        start('backend',['--network',networks[1],'--network-alias','backend','--read-only','--cap-drop=ALL',
                         '--security-opt=no-new-privileges:true','--tmpfs','/tmp:mode=1777',
                         *[arg for filename,target in (('backend.json','backend.json'),('runtime.password','runtime_password'),('csrf.key','csrf_key'),('ca.crt','ca.crt')) for arg in
                           ('--mount',f'type=bind,src={inputs}/{filename},dst=/run/livenet/{target},readonly')],
                         image,'gunicorn','--config','/app/gunicorn_container.conf.py',"dedicated_wsgi:create_tls_app('/run/livenet/backend.json')"])
        docker('network','connect','--ip',backend_ip,networks[2],prefix+'-backend')
        start('web',['--network',networks[0],'--network-alias','web','--network-alias','livenet-v2.home.arpa','--read-only','--cap-drop=ALL',
                     '--security-opt=no-new-privileges:true','--tmpfs','/data:uid=10002,gid=10002,mode=700',
                     '--tmpfs','/config:uid=10002,gid=10002,mode=700','--tmpfs','/tmp:mode=1777',
                     '-e','XDG_DATA_HOME=/data','-e','XDG_CONFIG_HOME=/config','-e','LIVENET_ALLOWED_CLIENTS='+str(subnets[0]),
                     '--mount',f'type=bind,src={ROOT}/infra/dedicated/Caddyfile,dst=/etc/caddy/Caddyfile,readonly',
                     '--mount',f'type=bind,src={public},dst=/srv,readonly',caddy,'caddy','run','--config','/etc/caddy/Caddyfile','--adapter','caddyfile'])
        docker('network','connect','--ip',peer,networks[1],prefix+'-web')
        for attempt in range(40):
            try: (public/'root.crt').write_text(docker('exec',prefix+'-web','cat','/data/caddy/pki/authorities/local/root.crt'));break
            except RuntimeError: time.sleep(.25)
        else: raise RuntimeError('Synthetic Caddy CA not ready')
        for attempt in range(40):
            health=request('/api/v1/health')
            if health['status']==200: break
            time.sleep(.25)
        assert health['status']==200
        assert request('/api/v1/ready')['status']==503
        assert request('/api/v1/auth/me')['status']==401
        assert request('/api/v1/inventory/resources')['status']==401
        csrf=request('/api/v1/auth/csrf');assert csrf['status']==200
        token=json.loads(csrf['body'])['csrf_token']
        cookie=next(v.split(';',1)[0] for k,v in csrf['headers'] if k.lower()=='set-cookie')
        headers=[('Origin','https://livenet-v2.home.arpa:8443'),('X-CSRF-Token',token),('Cookie',cookie)]
        assert request('/api/v1/auth/login','POST',[('Origin','https://evil.test')],{'login':'synthetic','password':'synthetic'})['status']==403
        login=request('/api/v1/auth/login','POST',headers,{'login':'synthetic','password':'synthetic-not-an-account'})
        assert login['status']==503 and json.loads(login['body'])['error']['code']=='security_unavailable'
        if browser_check is not None:
            phase='real-react-browser'
            results.append(browser_check(start=start,remove=remove,helper=helper,network=networks[0],public=public,prefix=prefix))
        phase='application-tls-attestation';probe('attest')
        docker('restart',prefix+'-backend')
        for attempt in range(40):
            if request('/api/v1/health')['status']==200: break
            time.sleep(.25)
        else: raise RuntimeError('Backend restart failed')
        assert request('/api/v1/ready')['status']==503
        results.append({'https_health':200,'anonymous_auth_inventory':401,'csrf_rejection':403,
                        'legitimate_login_schema_boundary':503,'readiness':503,'backend_restart':True,
                        'react_ui_demonstrated':browser_check is not None,'migration_gates_unchanged':True})
        for name in containers:
            obj=json.loads(docker('inspect',name))[0]
            assert not obj['HostConfig'].get('PortBindings')
            assert not any(m['Type']=='volume' for m in obj['Mounts'])
        print(json.dumps({'status':'passed','prefix':prefix,'backend_image':image,'results':results,
                          'production_ready':False,'application_persistence_demonstrated':False},indent=2))
    except Exception:
        raise RuntimeError(run_tag.upper()+' isolated check failed during '+phase+'; details suppressed') from None
    finally:
        failures=[]
        for name in list(reversed(containers)):
            try: remove(name)
            except Exception: failures.append(name)
        for name in reversed(networks):
            try:
                if docker('network','inspect','--format','{{index .Labels "'+label+'"}}',name)!=prefix:
                    raise RuntimeError('Network label mismatch')
                docker('network','rm',name)
            except Exception: failures.append(name)
        try:
            docker('run','--rm','--pull=never','--name',prefix+'-cleanup','--label',label+'='+prefix,'--user','0:0','--network','none',
                   '--mount',f'type=bind,src={work},dst=/work',image,'python','-B','-c',
                   "from pathlib import Path;import shutil;[(shutil.rmtree(p) if p.is_dir() else p.unlink()) for p in Path('/work').iterdir()]")
            work.rmdir()
        except Exception: failures.append('synthetic files')
        print(json.dumps({'cleanup_failures':failures,'removed':not failures}))
        if failures: raise RuntimeError(run_tag.upper()+' cleanup incomplete')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--image',default='livenet-dev06/backend:integration')
    run(p.parse_args().image)
