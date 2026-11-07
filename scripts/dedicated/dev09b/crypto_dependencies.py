"""Candidate wheel inspection; no installation, network or approval issuer."""
from dataclasses import dataclass
from email.parser import BytesParser
from hashlib import sha256
from pathlib import Path
import os
import io
import platform
import zipfile

from . import codec as c

LOCK = 'scripts/postgres/dev09b-crypto-candidate.lock'
PROVENANCE = 'scripts/postgres/dev09b-crypto-candidate.json'


def metadata(root):
    raw = (Path(root) / LOCK).read_bytes()
    p = c.parse((Path(root) / PROVENANCE).read_bytes())
    c.closed(p, {'schema_version', 'status', 'target', 'artifacts'})
    c.require(type(p['schema_version']) is int and p['schema_version'] == 1)
    c.require(p['status'] == 'CANDIDATE_NOT_APPROVED')
    c.require(p['target'] == 'CPython-3.12-linux-x86_64-glibc')
    c.require(type(p['artifacts']) is list and len(p['artifacts']) == 3)
    rows = []
    for a in p['artifacts']:
        c.closed(a, {'name', 'version', 'filename', 'url', 'sha256', 'requires_python', 'requires_dist', 'tags'})
        for key in ('name', 'version', 'filename', 'url', 'requires_python'):
            c.require(type(a[key]) is str and bool(a[key]))
        c.digest_text(a['sha256'])
        for key in ('requires_dist', 'tags'):
            c.require(type(a[key]) is list and all(type(x) is str for x in a[key]))
        c.require(a['url'].startswith('https://files.pythonhosted.org/packages/') and a['url'].endswith('/' + a['filename']))
        rows.append(f"{a['name']}=={a['version']} --hash=sha256:{a['sha256']}")
    actual = [x for x in raw.decode().splitlines() if x and not x.startswith('#')]
    c.require(actual == rows)
    c.require([a['name'] for a in p['artifacts']] == ['cryptography', 'cffi', 'pycparser'])
    # Evaluate markers for the FIXED proposed executor, never the host's markers.
    from packaging.markers import default_environment
    from packaging.requirements import Requirement
    from packaging.version import Version
    from packaging.specifiers import SpecifierSet
    env = default_environment()
    env.update(python_version='3.12', python_full_version='3.12.0', implementation_name='cpython',
               platform_python_implementation='CPython', sys_platform='linux', platform_system='Linux',
               platform_machine='x86_64', extra='')
    versions = {a['name']: a['version'] for a in p['artifacts']}
    for a in p['artifacts']:
        c.require(Version('3.12.0') in SpecifierSet(a['requires_python']))
        for line in a['requires_dist']:
            r = Requirement(line)
            if r.marker is None or r.marker.evaluate(env):
                c.require(r.url is None and r.name in versions and Version(versions[r.name]) in r.specifier)
    return raw, p


@dataclass(frozen=True)
class RuntimeEnvironment:
    identity: str
    python: str
    implementation: str
    machine: str
    glibc: str
    tags: tuple


def current_runtime(identity):
    """Explicit local observation only; does not identify a different image."""
    from packaging.tags import sys_tags
    return RuntimeEnvironment(identity, platform.python_version(), platform.python_implementation(),
                              platform.machine(), os.confstr('CS_GNU_LIBC_VERSION') or '', tuple(map(str, sys_tags())))


@dataclass(frozen=True)
class ArtifactResult:
    name: str
    availability: str
    integrity: str
    compatibility: str


@dataclass(frozen=True)
class LockInspection:
    lock_sha256: str
    provenance_sha256: str
    environment_identity: str | None
    artifacts: tuple
    approval: str
    approval_reference: str | None


@dataclass(frozen=True)
class LockApproval:
    """Only returned by an explicitly trusted approval verifier, not metadata."""
    lock_sha256: str
    provenance_sha256: str
    artifact_sha256s: tuple
    decision_reference: str


def inspect(root, artifact_paths=None, environment=None, approval_verifier=None):
    raw, p = metadata(root)
    paths = artifact_paths or {}
    results = []
    from packaging.specifiers import SpecifierSet
    from packaging.version import Version
    for a in p['artifacts']:
        available, integrity, compatibility = 'MISSING', 'UNVERIFIED', 'UNKNOWN'
        path = paths.get(a['name'])
        if path is not None and Path(path).is_file():
            data = Path(path).read_bytes()
            c.require(sha256(data).hexdigest() == a['sha256'])
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                names = z.namelist()
                m = [n for n in names if n.endswith('.dist-info/METADATA')]
                w = [n for n in names if n.endswith('.dist-info/WHEEL')]
                c.require(len(m) == len(w) == 1 and m[0].rsplit('/', 1)[0] == w[0].rsplit('/', 1)[0])
                c.require(all(z.getinfo(n).file_size <= 1024*1024 for n in (m[0],w[0])))
                meta, wheel = BytesParser().parsebytes(z.read(m[0])), BytesParser().parsebytes(z.read(w[0]))
                c.require(meta['Name'].lower() == a['name'] and meta['Version'] == a['version'])
                c.require(meta['Requires-Python'] == a['requires_python'])
                c.require((meta.get_all('Requires-Dist') or []) == a['requires_dist'])
                c.require((wheel.get_all('Tag') or []) == a['tags'])
            available, integrity = 'AVAILABLE', 'VERIFIED'
        if environment is not None:
            c.require(type(environment) is RuntimeEnvironment and bool(environment.identity))
            compatible = (environment.implementation == 'CPython' and environment.machine == 'x86_64'
                          and environment.python.startswith('3.12.') and environment.glibc.startswith('glibc ')
                          and Version(environment.python) in SpecifierSet(a['requires_python'])
                          and bool(set(a['tags']) & set(environment.tags)))
            # Tags must agree with the observed glibc too, not just a supplied
            # list containing a manylinux tag from another environment.
            if compatible:
                libc = Version(environment.glibc.split(' ',1)[1])
                import re
                floors = [Version(m[1]+'.'+m[2]) for tag in a['tags'] for m in [re.search(r'manylinux_(\d+)_(\d+)_',tag)] if m]
                compatible = not floors or libc >= min(floors)
            compatibility = 'COMPATIBLE' if compatible else 'INCOMPATIBLE'
        results.append(ArtifactResult(a['name'], available, integrity, compatibility))
    lock_hash = sha256(raw).hexdigest()
    prov_hash = sha256((Path(root) / PROVENANCE).read_bytes()).hexdigest()
    approval, reference = 'NOT_PROVIDED', None
    if approval_verifier is not None:
        # Verification policy/authentication/revocation belongs to trusted caller.
        result = approval_verifier.verify(raw, (Path(root) / PROVENANCE).read_bytes())
        c.require(type(result) is LockApproval)
        c.require(result.lock_sha256 == lock_hash and result.provenance_sha256 == prov_hash
                  and result.artifact_sha256s == tuple(a['sha256'] for a in p['artifacts'])
                  and type(result.decision_reference) is str and bool(result.decision_reference))
        approval, reference = 'VERIFIED_BY_TRUSTED_PORT', result.decision_reference
    return LockInspection(lock_hash, prov_hash, None if environment is None else environment.identity,
                          tuple(results), approval, reference)
