"""Offline lock/ZIP metadata/tag tests. Synthetic wheels are never installed."""
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
import json
import socket
import zipfile

import pytest

from scripts.dedicated.dev09b import codec as c
from scripts.dedicated.dev09b import crypto_dependencies as d
from scripts.dedicated.dev09b import bundle

ROOT=Path(__file__).resolve().parents[3]


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args,**kwargs):raise AssertionError('No network or package installation')
    monkeypatch.setattr(socket,'socket',denied)
    monkeypatch.setattr(socket,'create_connection',denied)


def candidate(root,mutate=None):
    provenance=json.loads((ROOT/d.PROVENANCE).read_bytes())
    paths={}
    for a in provenance['artifacts']:
        path=root/a['filename']
        with zipfile.ZipFile(path,'w') as z:
            prefix=a['name']+'-'+a['version']+'.dist-info/'
            metadata='Metadata-Version: 2.1\nName: '+a['name']+'\nVersion: '+a['version']+'\nRequires-Python: '+a['requires_python']+'\n'
            metadata+=''.join('Requires-Dist: '+r+'\n' for r in a['requires_dist'])
            z.writestr(prefix+'METADATA',metadata)
            z.writestr(prefix+'WHEEL','Wheel-Version: 1.0\n'+''.join('Tag: '+t+'\n' for t in a['tags']))
        a['sha256']=sha256(path.read_bytes()).hexdigest()
        paths[a['name']]=path
    if mutate:mutate(provenance)
    (root/d.LOCK).parent.mkdir(parents=True,exist_ok=True)
    (root/d.LOCK).write_text(''.join(f"{a['name']}=={a['version']} --hash=sha256:{a['sha256']}\n" for a in provenance['artifacts']))
    (root/d.PROVENANCE).write_text(json.dumps(provenance))
    return paths,provenance


def environment():
    return d.RuntimeEnvironment('SYNTHETIC-executor-image','3.12.3','CPython','x86_64','glibc 2.39',
        ('cp311-abi3-manylinux_2_34_x86_64','cp312-cp312-manylinux_2_17_x86_64','py3-none-any'))


def test_real_candidate_closure_and_missing_artifacts_approval_environment():
    raw,p=d.metadata(ROOT)
    assert len(p['artifacts'])==3
    result=bundle.inspect_crypto_dependencies(ROOT)
    assert result.approval=='NOT_PROVIDED' and result.environment_identity is None
    assert all(x.availability=='MISSING' and x.integrity=='UNVERIFIED' and x.compatibility=='UNKNOWN' for x in result.artifacts)
    built=bundle.build_candidate(ROOT)
    assert built['status']=='CANDIDATE_NOT_APPROVED' and built['dependency_completeness']=='INCOMPLETE'
    assert d.LOCK in {x['path'] for x in built['dependency_locks']}


def test_available_verified_compatible_does_not_mean_approved(tmp_path):
    paths,p=candidate(tmp_path)
    result=d.inspect(tmp_path,paths,environment())
    assert all(x.availability=='AVAILABLE' and x.integrity=='VERIFIED' and x.compatibility=='COMPATIBLE' for x in result.artifacts)
    assert result.approval=='NOT_PROVIDED'


@pytest.mark.parametrize('mutate',[lambda p:p['artifacts'][0].update(version='0.0'),
    lambda p:p['artifacts'][1].update(requires_dist=['missing-dependency>=1']),
    lambda p:p.update(status='APPROVED'),lambda p:p['artifacts'][0].update(tags=['wrong-tag'])])
def test_metadata_or_closure_divergence_refused(tmp_path,mutate):
    paths,p=candidate(tmp_path,mutate)
    with pytest.raises(c.Invalid):d.inspect(tmp_path,paths,environment())


def test_hash_tamper_and_unsupported_runtime(tmp_path):
    paths,p=candidate(tmp_path)
    paths['cffi'].write_bytes(paths['cffi'].read_bytes()+b'tamper')
    with pytest.raises(c.Invalid):d.inspect(tmp_path,paths,environment())
    paths,p=candidate(tmp_path)
    result=d.inspect(tmp_path,paths,replace(environment(),tags=('py3-none-any',),glibc='glibc 2.17'))
    assert result.artifacts[0].compatibility=='INCOMPATIBLE'
    assert result.environment_identity=='SYNTHETIC-executor-image'


def test_approval_requires_explicit_verifier_bound_to_exact_artifacts(tmp_path):
    paths,p=candidate(tmp_path)
    with pytest.raises(c.Invalid):d.inspect(tmp_path,paths,environment(),SimpleNamespace(verify=lambda *args:True))
    class TrustedBoundaryDouble:
        def verify(self,raw,provenance):
            return d.LockApproval(sha256(raw).hexdigest(),sha256(provenance).hexdigest(),
                       tuple(a['sha256'] for a in p['artifacts']),'SYNTHETIC-DECISION-DOUBLE')
    result=d.inspect(tmp_path,paths,None,TrustedBoundaryDouble())
    assert result.approval=='VERIFIED_BY_TRUSTED_PORT'
    assert all(x.compatibility=='UNKNOWN' for x in result.artifacts)
    class WrongBinding:
        def verify(self,*args):return d.LockApproval('0'*64,'0'*64,(),'SYNTHETIC')
    with pytest.raises(c.Invalid):d.inspect(tmp_path,paths,environment(),WrongBinding())
