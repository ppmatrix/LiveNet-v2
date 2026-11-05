"""Source/commit provenance only: never generates, accepts or replaces AUTH-03."""
import hashlib
import json
from pathlib import Path
import subprocess

from reconcile_contracts import ROOT, report


def git(*args):
    return subprocess.run(['git','-C',str(ROOT),*args],capture_output=True,check=True).stdout


def main():
    contracts=report();manifest=contracts['auth03'];tracked=set(git('ls-files').decode().splitlines())
    rows=[]
    for name in manifest['missing']+[item['path'] for item in manifest['mismatches']]:
        current=(ROOT/name).read_bytes();actual=hashlib.sha256(current).hexdigest()
        item={'path':name,'tracked':name in tracked,'current_sha256':actual,'attestation':'NOT_APPROVED_BY_MANIFEST'}
        if name in tracked:
            item['last_commit']=git('log','-1','--format=%H %s','--',name).decode().strip()
            item['matches_HEAD']=hashlib.sha256(git('show','HEAD:'+name)).hexdigest()==actual
            item['classification']='committed source without current manifest attestation' if item['matches_HEAD'] else 'working tree change requiring review'
            expected=next((x['manifest_sha256'] for x in manifest['mismatches'] if x['path']==name),None)
            matches=[]
            if expected:
                for commit in git('log','--format=%H','--',name).decode().splitlines():
                    content=subprocess.run(['git','-C',str(ROOT),'show',commit+':'+name],capture_output=True)
                    if content.returncode==0 and hashlib.sha256(content.stdout).hexdigest()==expected:matches.append(commit)
            item['expected_hash_matches_located_commits']=matches
        else:
            item['classification']='local artifact: prior report/request provenance, not a Git attestation'
        rows.append(item)
    print(json.dumps({'authority':'audit evidence and review proposal only; no execution or trust approval',
                      'head':git('rev-parse','HEAD').decode().strip(),'contracts':contracts,
                      'file_provenance':rows,'unauthorized_security_change':'NOT_ESTABLISHED; absence of attestation is not proof of unauthorized origin'},indent=2))


if __name__=='__main__': main()
