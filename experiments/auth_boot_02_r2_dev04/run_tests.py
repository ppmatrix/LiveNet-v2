import hashlib
import io
import json
from pathlib import Path
import platform
import subprocess
import time
import unittest

import psycopg

from test_experiment import Experiments


if __name__ == '__main__':
    started = time.time()
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(Experiments))
    lab = getattr(Experiments, 'lab', None)
    root = Path(__file__).parent
    evidence = dict(started_utc_epoch=started, timestamp_authenticated=False,
        duration_seconds=time.time() - started, python=platform.python_version(), psycopg=psycopg.__version__,
        postgres=subprocess.check_output(['/usr/lib/postgresql/16/bin/postgres', '--version'], text=True).strip(),
        tests=result.testsRun, failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped),
        success=result.wasSuccessful(), output=output.getvalue(), measurements=Experiments.measurements,
        source_sha256={path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in root.glob('*.py')},
        head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        cleanup=bool(lab and lab.cleaned), ephemeral_root=str(lab.root) if lab else None,
        executable=False, d09_independence_demonstrated=False, authenticated_utc=False,
        endpoint_authentication='local kernel SO_PEERCRED + pinned socket path/device/inode/pid/uid/gid; same OS administrator',
        unconditional_fencing=False, effect_tests_use_explicit_fixture=True)
    (root / 'evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print(output.getvalue())
    print(json.dumps({key: evidence[key] for key in ('tests', 'failures', 'errors', 'cleanup', 'duration_seconds')}))
    raise SystemExit(0 if result.wasSuccessful() and evidence['cleanup'] else 1)
