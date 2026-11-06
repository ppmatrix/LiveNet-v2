import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path('/home/paulo/projects/livenet-v2')
PREFIX = 'experiments/auth_boot_02_r2_dev03/'
BASELINE = Path('/tmp/livenet-r2-dev03-01a17d34-baseline.json')


def git(*arguments):
    return subprocess.check_output(['git', '-C', str(ROOT), *arguments])


def snapshot():
    names = git('ls-files', '-z', '--cached', '--others', '--exclude-standard').split(b'\0')
    hashes = {}
    for raw in sorted(set(names)):
        name = raw.decode()
        path = ROOT / name
        if name and not name.startswith(PREFIX) and path.is_file():
            hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    status = git('status', '--porcelain=v1', '--untracked-files=all').decode()
    return dict(head=git('rev-parse', 'HEAD').decode().strip(), hashes=hashes,
                status='\n'.join(line for line in status.splitlines()
                                 if not line[3:].startswith(PREFIX)),
                diff_sha256=hashlib.sha256(git('diff', '--binary', 'HEAD')).hexdigest())


if __name__ == '__main__':
    if sys.argv[1] == 'before':
        if BASELINE.exists() or (ROOT / PREFIX).exists():
            raise RuntimeError('destination or baseline exists; refusing overwrite')
        BASELINE.write_text(json.dumps(snapshot(), indent=2) + '\n')
        print(json.dumps(dict(files=len(json.loads(BASELINE.read_text())['hashes']))))
    else:
        before = json.loads(BASELINE.read_text())
        after = snapshot()
        changed = [name for name, digest in before['hashes'].items()
                   if after['hashes'].get(name) != digest]
        added = sorted(set(after['hashes']) - set(before['hashes']))
        result = dict(files_checked=len(before['hashes']), changed=changed,
                      unexpected_added=added, head_unchanged=before['head'] == after['head'],
                      status_unchanged=before['status'] == after['status'],
                      diff_unchanged=before['diff_sha256'] == after['diff_sha256'],
                      baseline_sha256=hashlib.sha256(BASELINE.read_bytes()).hexdigest(),
                      head=after['head'])
        (ROOT / PREFIX / 'preservation.baseline.json').write_bytes(BASELINE.read_bytes())
        (ROOT / PREFIX / 'preservation.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result))
        sys.exit(0 if not changed and not added and all(result[key] for key in
                 ('head_unchanged', 'status_unchanged', 'diff_unchanged')) else 1)
