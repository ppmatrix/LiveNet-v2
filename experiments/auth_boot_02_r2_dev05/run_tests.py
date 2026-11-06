import hashlib
import io
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
import unittest

import psycopg

from test_resource import Experiments


if __name__ == '__main__':
    root = Path(__file__).resolve().parent
    started = time.time()
    baseline_code = """
import json, unittest
from test_experiment import Experiments
names = ['test_anchor_connection_loss_before_sql_counterexample',
         'test_anchor_connection_loss_in_flight_counterexample']
suite = unittest.TestSuite(Experiments(name) for name in names)
result = unittest.TextTestRunner(verbosity=2).run(suite)
print(json.dumps(dict(measurements=Experiments.measurements, cleanup=Experiments.lab.cleaned)))
raise SystemExit(0 if result.wasSuccessful() and Experiments.lab.cleaned else 1)
"""
    baseline = subprocess.run([sys.executable, '-B', '-c', baseline_code], cwd=root.parent / 'auth_boot_02_r2_dev04',
                              capture_output=True, text=True)
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(Experiments))
    lab = getattr(Experiments, 'lab', None)
    evidence = dict(started_utc_epoch=started, timestamp_authenticated=False,
        duration_seconds=time.time() - started, python=platform.python_version(), psycopg=psycopg.__version__,
        postgres=subprocess.check_output(['/usr/lib/postgresql/16/bin/postgres', '--version'], text=True).strip(),
        baseline_dev04=dict(exit_code=baseline.returncode, stdout=baseline.stdout, stderr=baseline.stderr, tests=2),
        tests=result.testsRun, failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped),
        success=result.wasSuccessful() and baseline.returncode == 0, output=output.getvalue(),
        measurements=Experiments.measurements,
        source_sha256={path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in root.glob('*.py')},
        reused_source_sha256={str(path.relative_to(root.parent)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (root.parent / 'auth_boot_02_r2_dev04').glob('*.py')},
        head=subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip(),
        cleanup=bool(lab and lab.cleaned), ephemeral_root=str(lab.root) if lab else None,
        executable=False, d09_independence_demonstrated=False, authenticated_utc=False,
        unconditional_fencing=False, distributed_cessation_proven=False, effect_tests_use_explicit_fixture=True)
    (root / 'evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print(baseline.stderr)
    print(output.getvalue())
    print(json.dumps({key: evidence[key] for key in ('tests', 'failures', 'errors', 'cleanup', 'duration_seconds')}))
    raise SystemExit(0 if evidence['success'] and evidence['cleanup'] else 1)
