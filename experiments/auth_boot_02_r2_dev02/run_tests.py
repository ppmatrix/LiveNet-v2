import hashlib
import io
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
import unittest

from test_laboratory import Experiments


if __name__ == '__main__':
    started = time.time()
    output = io.StringIO()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Experiments)
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    sources = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
               for path in Path(__file__).parent.glob('*.py')}
    evidence = dict(started_utc_epoch=started, duration_seconds=time.time() - started,
        python=platform.python_version(), tests=result.testsRun, failures=len(result.failures),
        errors=len(result.errors), skipped=len(result.skipped), success=result.wasSuccessful(),
        output=output.getvalue(), measurements=Experiments.measurements, source_sha256=sources,
        head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        cleanup=Experiments.harness.cleaned, ephemeral_root=str(Experiments.harness.root),
        executable=False, d09_confirmed=False, authenticated_utc=False, target_exclusive=False)
    Path('evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print(output.getvalue())
    print(json.dumps({key: evidence[key] for key in ['tests', 'failures', 'errors', 'cleanup', 'duration_seconds']}))
    sys.exit(0 if result.wasSuccessful() and evidence['cleanup'] else 1)
