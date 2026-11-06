import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path('/home/paulo/projects/livenet-v2')
PREFIX = 'experiments/auth_boot_02_r2_dev02/'
CAPTURE = Path('/tmp/livenet-r2-dev02-01a17d23-preservation.json')


def git(*arguments):
    return subprocess.check_output(['git', '-C', str(ROOT), *arguments])


def snapshot():
    files = sorted(set(git('ls-files', '-z', '--cached', '--others', '--exclude-standard').split(b'\0')))
    hashes = {}
    for filename in files:
        if not filename:
            continue
        name = filename.decode()
        path = ROOT / name
        if not name.startswith(PREFIX) and path.is_file():
            hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    status = git('status', '--porcelain=v1', '--untracked-files=all').decode()
    status = '\n'.join(line for line in status.splitlines() if not line[3:].startswith(PREFIX))
    return dict(head=git('rev-parse', 'HEAD').decode().strip(), hashes=hashes,
                status=status, diff_sha256=hashlib.sha256(git('diff', '--binary', 'HEAD')).hexdigest())


if __name__ == '__main__':
    if sys.argv[1] == 'before':
        if CAPTURE.exists() or (ROOT / PREFIX).exists():
            raise RuntimeError('baseline or destination already exists')
        CAPTURE.write_text(json.dumps(snapshot(), indent=2) + '\n')
        print(json.dumps(dict(captured_files=len(json.loads(CAPTURE.read_text())['hashes']),
                              baseline=str(CAPTURE))))
    else:
        before = json.loads(CAPTURE.read_text())
        after = snapshot()
        changed = [name for name, digest in before['hashes'].items()
                   if after['hashes'].get(name) != digest]
        added = sorted(set(after['hashes']) - set(before['hashes']))
        result = dict(files_checked=len(before['hashes']), changed=changed, unexpected_added=added,
            head_unchanged=before['head'] == after['head'],
            status_unchanged=before['status'] == after['status'],
            diff_unchanged=before['diff_sha256'] == after['diff_sha256'],
            baseline_sha256=hashlib.sha256(CAPTURE.read_bytes()).hexdigest(), head=after['head'])
        (ROOT / PREFIX / 'preservation.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result))
        if changed or added or not all(result[key] for key in ['head_unchanged', 'status_unchanged', 'diff_unchanged']):
            sys.exit(1)
