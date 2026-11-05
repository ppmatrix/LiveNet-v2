"""Build/test the real frontend in a disposable Node container, not the host npm.

Copies no .env/.npmrc, uses empty npm configs and the checked-in package-lock.
Install may reach registry.npmjs.org; test/build use --network none. No ports.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid

ROOT=Path(__file__).resolve().parents[2]
NODE='node@sha256:55fb5f5a527ea2c5c4a95f963e48ef90aa38c7b346054fdc8ee9957a2b55d205'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-dir',required=True)
    args=parser.parse_args();evidence=Path(args.evidence_dir).resolve();evidence.mkdir(parents=True,exist_ok=True)
    source=ROOT/'frontend'
    if any(p.is_symlink() for p in source.rglob('*') if not any(x in p.parts for x in ('node_modules','dist'))):
        raise SystemExit('Refusing frontend source symlinks')
    work=Path(tempfile.mkdtemp(prefix='livenet-dev07-frontend-'))
    frontend=work/'frontend'
    shutil.copytree(source,frontend,ignore=shutil.ignore_patterns('node_modules','dist','.npm-cache','.npmrc','.env*'))
    source_hashes={str(p.relative_to(frontend)):hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in frontend.rglob('*') if p.is_file()}
    (frontend/'.npm-user.conf').write_text('');(frontend/'.npm-global.conf').write_text('')
    prefix='livenet-dev07-build-'+uuid.uuid4().hex[:10]
    active=None
    def docker(*command,**kwargs):
        return subprocess.run(['docker','--host','unix:///var/run/docker.sock',*map(str,command)],**kwargs)
    try:
        for stage,command in [('install',['ci','--ignore-scripts','--no-audit','--no-fund','--registry=https://registry.npmjs.org']),
                              ('test',['run','test']),('build',['run','build'])]:
            active=prefix+'-'+stage
            with (evidence/('frontend-'+stage+'.log')).open('w') as log:
                result=docker('run','--rm','--pull=never','--name',active,'--label','livenet.dev07='+prefix,
                              '--network','bridge' if stage=='install' else 'none','--user',f'{os.getuid()}:{os.getgid()}',
                              '--mount',f'type=bind,src={frontend},dst=/workspace','--workdir','/workspace','-e','CI=true',NODE,
                              'npm','--userconfig=/workspace/.npm-user.conf','--globalconfig=/workspace/.npm-global.conf',
                              '--cache=/workspace/.npm-cache',*command,stdout=log,stderr=subprocess.STDOUT,timeout=180)
            if result.returncode: raise RuntimeError('Isolated frontend '+stage+' failed; see local log')
            active=None
        result={'work_dir':str(work),'frontend_dist':str(frontend/'dist'),'node_image':NODE,
                'registry':'https://registry.npmjs.org','source_sha256':source_hashes,
                'dist_sha256':{str(p.relative_to(frontend/'dist')):hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in (frontend/'dist').rglob('*') if p.is_file()}}
        (evidence/'frontend-build-evidence.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result,indent=2))
    finally:
        if active:
            inspect=docker('inspect','--format','{{index .Config.Labels "livenet.dev07"}}',active,capture_output=True,text=True)
            if inspect.returncode==0 and inspect.stdout.strip()==prefix:docker('rm','-f',active,check=True,stdout=subprocess.DEVNULL)
        for name in ('node_modules','.npm-cache'):
            p=frontend/name
            if p.exists():shutil.rmtree(p)


if __name__=='__main__': main()
