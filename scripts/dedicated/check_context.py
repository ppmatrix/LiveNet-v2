"""Verify Dockerignore with actual local BuildKit exports, no network or image.

Checks the real backend context and adversarial benign fixtures in a temporary
copy; does not create sentinel files inside the repository.
"""
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[2]
ALLOWED={'requirements.txt','requirements-dedicated.txt','requirements-container.constraints.txt',
         'requirements-container.lock','dedicated_wsgi.py','gunicorn_container.conf.py'}


def check(source,work,label):
    dockerfile=work/(label+'.Dockerfile')
    dockerfile.write_text('FROM scratch\nCOPY . /\n')
    shutil.copyfile(ROOT/'backend/Dockerfile.dedicated.dockerignore',str(dockerfile)+'.dockerignore')
    output=work/(label+'-export')
    subprocess.run(['docker','--host','unix:///var/run/docker.sock','build','--network=none','--progress=plain','--output','type=local,dest='+str(output),
                    '-f',str(dockerfile),str(source)],check=True,stdout=subprocess.DEVNULL)
    expected={p.relative_to(source).as_posix() for p in (source/'app').rglob('*.py') if p.is_file()}|ALLOWED
    actual={p.relative_to(output).as_posix() for p in output.rglob('*') if p.is_file()}
    assert actual==expected,(actual-expected,expected-actual)
    assert all(hashlib.sha256((source/p).read_bytes()).digest()==hashlib.sha256((output/p).read_bytes()).digest() for p in actual)
    print(label+': '+str(len(actual))+' exact files; byte hashes match; no extra files')


def main():
    endpoint=subprocess.check_output(['docker','context','inspect','--format','{{.Endpoints.docker.Host}}'],text=True).strip()
    if endpoint!='unix:///var/run/docker.sock': raise RuntimeError('Local Unix daemon required')
    with tempfile.TemporaryDirectory(prefix='livenet-dev05b-context-') as folder:
        work=Path(folder);check(ROOT/'backend',work,'real')
        source=work/'fixture';source.mkdir();shutil.copytree(ROOT/'backend/app',source/'app')
        for name in ALLOWED: shutil.copyfile(ROOT/'backend'/name,source/name)
        for name in ('app/secret.env','app/nested/private.pem','app/nested/bytecode.pyc','app/__pycache__/injected.pyc','root-secret.txt'):
            p=source/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('BENIGN TEST SENTINEL')
        p=source/'app/nested/deeper/required.py';p.parent.mkdir(parents=True);p.write_text('VALUE = 1\n')
        check(source,work,'adversarial')


if __name__=='__main__': main()
