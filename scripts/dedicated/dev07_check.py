"""Real React browser on the DEV-06 TLS harness; app migration gates stay closed."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from dev06_check import ROOT, run


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--frontend-dist',required=True)
    p.add_argument('--evidence-dir',required=True)
    p.add_argument('--image',default='livenet-dev07/backend:integration')
    p.add_argument('--browser-image',default='livenet-dev07/browser:integration')
    args=p.parse_args();dist=Path(args.frontend_dist).resolve();evidence=Path(args.evidence_dir).resolve()
    if not (dist/'index.html').is_file() or not list((dist/'assets').glob('*.js')):
        raise SystemExit('A real Vite build is required')
    evidence.mkdir(parents=True,exist_ok=True)
    browser_image=subprocess.check_output(['docker','--host','unix:///var/run/docker.sock','image','inspect',
                                           '--format','{{.Id}}',args.browser_image],text=True).strip()
    def browser_check(*,start,remove,helper,network,public,prefix):
        helper('evidence-owner',"import os;os.chown('/evidence',10001,10001);os.chmod('/evidence',0o755)",
               mounts=['--mount',f'type=bind,src={evidence},dst=/evidence'])
        output=start('browser',['--network',network,'--read-only','--cap-drop=ALL','--security-opt=no-new-privileges:true',
                               '--tmpfs','/tmp:mode=1777','--tmpfs','/home/browser:uid=10001,gid=10001,mode=700',
                               '--shm-size','256m','-e','NODE_EXTRA_CA_CERTS=/public/root.crt',
                               '--mount',f'type=bind,src={public},dst=/public,readonly',
                               '--mount',f'type=bind,src={ROOT}/scripts/dedicated/dev07_browser.mjs,dst=/browser/check.mjs,readonly',
                               '--mount',f'type=bind,src={evidence},dst=/evidence',browser_image,'/browser/check.mjs'],False)
        remove(prefix+'-browser')
        result=json.loads(output)
        result['bundle_sha256']={str(path.relative_to(dist)):hashlib.sha256(path.read_bytes()).hexdigest()
                                 for path in dist.rglob('*') if path.is_file()}
        return result
    run(args.image,frontend_dist=dist,browser_check=browser_check,run_tag='dev07')


if __name__=='__main__': main()
