"""FIX01: validated quarantine Compose and hash-bound, physically closed context.

No Docker/SQL/build/service runner. No operational image, approval issuer or
credential accepted. CLI only prints proposals/checks; temporary context is
removed before return. Historical/protected files are read, never changed.
"""
import difflib
import ast
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import shlex
import sys
import tempfile

from dev09a2_packaging import dockerignore

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = 'docs/operations/dev09a2-complementary.NOT-APPROVED.json'
CANDIDATE_SHA = 'bc0982d34e74c3c7838742cee9d3385225ddb749491b6c906cc04b55761f4db5'
AGGREGATE = 'docs/operations/proposals/dev09a2/protected-changes.NOT-APPROVED.patch'
AGGREGATE_SHA = 'ad2c67c2d9859e780e1c224610d19cc7345b170cbb8d24233a56e6334a0bbef5'
APP02_SECTION_SHA = '8b98ac7eaa012223bad8f6fde0b1d23c206ae00ce793d6263cb44758a507a76f'
DOCKERFILE = 'scripts/postgres/auth03_executor.Dockerfile'
IGNORE = DOCKERFILE + '.dockerignore'
APP02_COPY = 'docs/operations/proposals/dev09a2/scripts__postgres__auth03_executor.Dockerfile.proposed'
APP02_FILE_SHA = '666da86b54e81f0b7196eef55fac8d54ddfaab31c9f98e6d99727bb78c30b7b0'
MANIFEST = 'scripts/postgres/auth03_executor_integrity.json'
MANIFEST_SHA = '4819c697b7d12f7ab5cbb1fdfa9cf4c3fd0e98e93b53a60337296cc84036fc29'
LIMIT = 8 * 1024 * 1024


class Refused(ValueError):
    """Fixed codes; never print paths supplied by a caller or file contents."""


def require(condition, code):
    if not condition:
        raise Refused(code)


def path_parts(value):
    require(type(value) is str and bool(value), 'PATH_REFUSED')
    p = PurePosixPath(value)
    require(bool(p.parts) and not p.is_absolute() and value == p.as_posix()
            and all(part not in ('.', '..') and not part.startswith('.') for part in p.parts)
            and re.fullmatch(r'[A-Za-z0-9_./-]+', value) is not None, 'PATH_REFUSED')
    return p.parts


def read_bound(relative, digest):
    """Open every parent and leaf with NOFOLLOW; hash the bytes actually read."""
    parts = path_parts(relative)
    require(type(digest) is str and re.fullmatch('[0-9a-f]{64}', digest), 'DIGEST_REFUSED')
    descriptor = None
    try:
        descriptor = os.open(ROOT, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        for part in parts[:-1]:
            following = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = following
        leaf = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=descriptor)
        try:
            info = os.fstat(leaf)
            require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                    and info.st_uid == os.getuid() and info.st_size <= LIMIT, 'SOURCE_REFUSED')
            chunks, total = [], 0
            while True:
                chunk = os.read(leaf, 65536)
                if not chunk:
                    break
                total += len(chunk)
                require(total <= LIMIT, 'SOURCE_REFUSED')
                chunks.append(chunk)
            data = b''.join(chunks)
        finally:
            os.close(leaf)
    except OSError:
        raise Refused('SOURCE_UNAVAILABLE_OR_SYMLINK') from None
    finally:
        if descriptor is not None:
            os.close(descriptor)
    require(sha256(data).hexdigest() == digest, 'SOURCE_HASH_DIVERGENCE')
    return data


def frozen_inventory():
    """Historical candidate is frozen inventory evidence, NOT approval authority."""
    candidate = json.loads(read_bound(CANDIDATE, CANDIDATE_SHA))
    sources = candidate['executor_context_current_sources']
    manifest = json.loads(read_bound(MANIFEST, MANIFEST_SHA))
    require(len(manifest) == 52 and len(sources) == 66
            and set(sources) == set(manifest) | set(candidate['current_complementary_sources']) | {MANIFEST}
            and all(sources[p] == h for p, h in manifest.items())
            and sources[MANIFEST] == MANIFEST_SHA, 'INVENTORY_REFUSED')
    for p in sources:
        path_parts(p)
    aggregate = read_bound(AGGREGATE, AGGREGATE_SHA)
    sections = {part.splitlines()[0].decode(): b'--- a/' + part
                for part in aggregate.split(b'--- a/')[1:]}
    require(sha256(sections[DOCKERFILE]).hexdigest() == APP02_SECTION_SHA, 'APP02_SECTION_DIVERGENCE')
    read_bound(APP02_COPY, APP02_FILE_SHA)
    return dict(sources)


def context_inventory():
    result = frozen_inventory()
    result[DOCKERFILE] = APP02_FILE_SHA
    result[IGNORE] = sha256(proposed_ignore().encode()).hexdigest()
    return dict(sorted(result.items()))


def proposed_ignore():
    # NO ancestor-directory reinclusion. All exceptions identify literal files.
    return dockerignore((*frozen_inventory(), DOCKERFILE, IGNORE))


def verify_context(destination):
    """Independent physical walk+hash comparison; does NOT use the matcher."""
    destination = Path(destination)
    require(not destination.is_symlink() and destination.is_dir(), 'CONTEXT_REFUSED')
    actual = {}
    for folder, dirs, files in os.walk(destination, followlinks=False):
        for name in dirs:
            p = Path(folder) / name
            require(not p.is_symlink(), 'CONTEXT_SYMLINK')
        for name in files:
            p = Path(folder) / name
            require(not p.is_symlink() and stat.S_ISREG(p.lstat().st_mode)
                    and p.stat().st_nlink == 1, 'CONTEXT_LEAF_REFUSED')
            actual[p.relative_to(destination).as_posix()] = sha256(p.read_bytes()).hexdigest()
    require(actual == context_inventory(), 'CONTEXT_SET_OR_HASH_DIVERGENCE')
    return dict(sorted(actual.items()))


def verify_dependencies(snapshot):
    """Static COPY and Python import/lock closure, never imports target code.

    This is a source/dependency check, not a proof of a built image or dynamic
    import behavior. Pip's --require-hashes and pip check remain build controls.
    """
    copied = set()
    for line in snapshot[DOCKERFILE].decode().splitlines():
        if not line.startswith('COPY '):
            continue
        words = shlex.split(line)[1:]
        for source in words[:-1]:
            path_parts(source)
            matches = {p for p in snapshot if p == source or p.startswith(source + '/')}
            require(bool(matches), 'COPY_DEPENDENCY_MISSING')
            copied.update(matches)
    require(copied == set(snapshot) - {DOCKERFILE, IGNORE}, 'COPY_SOURCE_CLOSURE_DIVERGENCE')
    pins = set()
    for line in snapshot['scripts/postgres/dev09a2-executor.lock'].decode().splitlines():
        if not line or line.startswith('#'):
            continue
        match = re.fullmatch(r'([A-Za-z0-9_-]+)==[0-9][A-Za-z0-9.]* --hash=sha256:[0-9a-f]{64}', line)
        require(match is not None, 'LOCK_ENTRY_REFUSED')
        name = match.group(1).lower().replace('_', '-')
        require(name not in pins, 'LOCK_DUPLICATE')
        pins.add(name)
    require(len(pins) == 14, 'LOCK_CLOSURE_DIVERGENCE')
    local = {'app', 'security_migrations', 'g4'} | {
        PurePosixPath(p).stem for p in snapshot if p.startswith('scripts/postgres/') and p.endswith('.py')}
    imports = set()
    for path, data in snapshot.items():
        if not path.endswith('.py'):
            continue
        for node in ast.walk(ast.parse(data, filename=path)):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split('.')[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
                imports.add(node.module.split('.')[0])
    external = imports - local - set(sys.stdlib_module_names)
    require(all(name.lower().replace('_', '-') in pins for name in external), 'PYTHON_DEPENDENCY_MISSING')
    return {'copied_sources': len(copied), 'locked_distributions': len(pins),
            'external_import_roots': sorted(external), 'dynamic_imports_or_built_image': 'NOT_VERIFIED'}


def materialize_context(destination):
    """Write only into a NEW child of a caller-owned private directory outside repo."""
    destination = Path(destination)
    require(destination.is_absolute() and not destination.exists() and not destination.is_symlink(), 'DESTINATION_REFUSED')
    parent = destination.parent
    require(not parent.is_symlink() and parent.resolve() == parent
            and parent.is_dir() and parent.stat().st_uid == os.getuid()
            and stat.S_IMODE(parent.stat().st_mode) & 0o077 == 0
            and not destination.is_relative_to(ROOT), 'DESTINATION_REFUSED')
    sources = frozen_inventory()
    # Read and attest the complete snapshot before creating any context.
    snapshot = {p: read_bound(p, h) for p, h in sources.items()}
    snapshot[DOCKERFILE] = read_bound(APP02_COPY, APP02_FILE_SHA)
    snapshot[IGNORE] = proposed_ignore().encode()
    verify_dependencies(snapshot)
    destination.mkdir(mode=0o700)
    for relative, data in snapshot.items():
        p = destination.joinpath(*path_parts(relative))
        p.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        with p.open('xb') as stream:
            stream.write(data)
        p.chmod(0o400)
    return verify_context(destination)


def validated_ids(uid, gid):
    for value in (uid, gid):
        require(type(value) is str and re.fullmatch(r'[1-9][0-9]{0,9}', value)
                and int(value) <= 2**32 - 2, 'NONROOT_ID_REQUIRED')
    return uid + ':' + gid


def validated_image(image):
    require(type(image) is str and len(image) <= 300, 'IMMUTABLE_IMAGE_REQUIRED')
    # Named repository, optional registry port, no tag-only reference, variables,
    # whitespace, empty segments, URLs or implicit environment interpolation.
    require(re.fullmatch(r'(?:[a-z0-9]+(?:[.-][a-z0-9]+)*(?::[1-9][0-9]{0,4})?/)?'
                        r'[a-z0-9]+(?:[._-][a-z0-9]+)*(?:/[a-z0-9]+(?:[._-][a-z0-9]+)*)*'
                        r'@sha256:[0-9a-f]{64}', image), 'IMMUTABLE_IMAGE_REQUIRED')
    host = image.split('/')[0]
    if '/' in image and ':' in host:
        require(int(host.rsplit(':', 1)[1]) <= 65535, 'REGISTRY_PORT_REFUSED')
    return image


def compose_template():
    """Intentionally not runnable: no image, build context or user defaults.

    Compose rejects this source until the mandatory validator materializes
    explicit literal parameters. Even that output has no operational path:
    network none, no ports/mounts/secrets, fixed exit78 and no build entry.
    """
    return {'name': 'livenet-auth03-validation-required',
            'x-dev09fix01-state': 'NOT APPROVED; use dev09fix01_packaging validation; no execution authorization',
            'services': {'executor': {
                'profiles': ['dev09fix01-quarantine'], 'image': None, 'user': None,
                'pull_policy': 'never', 'restart': 'no', 'read_only': True,
                'cap_drop': ['ALL'], 'privileged': False,
                'security_opt': ['no-new-privileges:true'], 'pids_limit': 64, 'mem_limit': '256m',
                'tmpfs': ['/tmp:rw,noexec,nosuid,nodev,size=16m,mode=1777'],
                'entrypoint': ['/bin/sh', '-c', 'exit 78'], 'command': [], 'network_mode': 'none'}}}


def compose_document(*, project, image, uid, gid):
    require(type(project) is str and re.fullmatch(r'livenet-dev09b-[0-9a-f]{10}', project), 'PROJECT_REFUSED')
    document = compose_template()
    document['name'] = project
    document['services']['executor']['image'] = validated_image(image)
    document['services']['executor']['user'] = validated_ids(uid, gid)
    return document


def verify_compose(document):
    require(type(document) is dict, 'COMPOSE_REFUSED')
    try:
        service = document['services']['executor']
        user = service['user']
        require(type(user) is str and user.count(':') == 1, 'NONROOT_ID_REQUIRED')
        uid, gid = user.split(':')
        expected = compose_document(project=document['name'], image=service['image'], uid=uid, gid=gid)
        # Canonical JSON preserves type distinctions (False is not numeric 0).
        require(json.dumps(document, sort_keys=True, allow_nan=False)
                == json.dumps(expected, sort_keys=True, allow_nan=False), 'COMPOSE_POLICY_DIVERGENCE')
        # Values cannot be re-interpreted through Compose's $ interpolation.
        require('$' not in json.dumps(document), 'INTERPOLATION_REFUSED')
    except (KeyError, TypeError):
        raise Refused('COMPOSE_REFUSED') from None
    return document


def patch_for(which):
    require(which in ('APP-01', 'APP-03'), 'PATCH_REFUSED')
    path = 'compose.auth03-executor.yaml' if which == 'APP-01' else IGNORE
    proposed = json.dumps(compose_template(), indent=2) + '\n' if which == 'APP-01' else proposed_ignore()
    # Reuse frozen original preimage hashes, never autoaccept edited protected files.
    candidate = json.loads(read_bound(CANDIDATE, CANDIDATE_SHA))
    expected = candidate['proposed_changes']['entries'][path]['before_sha256']
    original = read_bound(path, expected).decode()
    return ''.join(difflib.unified_diff(original.splitlines(True), proposed.splitlines(True),
                                      fromfile='a/' + path, tofile='b/' + path))


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('check-context')
    render = commands.add_parser('compose')
    for arg in ('project', 'image', 'uid', 'gid'):
        render.add_argument('--' + arg, required=True)
    args = vars(parser.parse_args(argv))
    command = args.pop('command')
    try:
        if command == 'compose':
            print(json.dumps(verify_compose(compose_document(**args)), indent=2))
        else:
            with tempfile.TemporaryDirectory(prefix='livenet-dev09fix01-context-') as tmp:
                result = materialize_context(Path(tmp) / 'context')
            print(json.dumps({'status': 'PASS', 'files': result, 'count': len(result),
                              'temporary_context_removed': True, 'build_executed': False}, indent=2))
    except (Refused, OSError):
        print(json.dumps({'status': 'REFUSED', 'code': 'LOCAL_VALIDATION_FAILED'}))
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
