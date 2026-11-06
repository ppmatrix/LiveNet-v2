import hashlib
import io
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
import unittest

from test_experiment import Experiments


if __name__ == '__main__':
    started = time.time()
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(Experiments))
    harness = getattr(Experiments, 'harness', None)
    sources = list(Path(__file__).parent.glob('*.py'))
    sources += [Path(__file__).parent.parent / 'auth_boot_02_r2_dev02' / name
                for name in ('harness.py', 'laboratory.py')]
    evidence = dict(started_utc_epoch=started, timestamp_authenticated=False,
        duration_seconds=time.time() - started, python=platform.python_version(),
        postgres=subprocess.check_output(['/usr/lib/postgresql/16/bin/postgres', '--version'], text=True).strip(),
        psycopg=__import__('psycopg').__version__, tests=result.testsRun,
        failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped),
        success=result.wasSuccessful(), output=output.getvalue(),
        measurements=Experiments.measurements,
        source_sha256={str(path.relative_to(Path(__file__).parent.parent)):
            hashlib.sha256(path.read_bytes()).hexdigest() for path in sources},
        head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        cleanup=bool(harness and harness.cleaned),
        ephemeral_root=str(harness.root) if harness else None,
        executable=False, d09_confirmed=False, authenticated_utc=False,
        operational_target_exclusivity=False,
        trusted_broker_required=True, unique_reference_and_target_required=True)
    Path(__file__).with_name('evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print(output.getvalue())
    print(json.dumps({key: evidence[key] for key in
                     ('tests', 'failures', 'errors', 'cleanup', 'duration_seconds')}))
    sys.exit(0 if result.wasSuccessful() and evidence['cleanup'] else 1)
