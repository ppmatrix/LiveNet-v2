from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import platform
import subprocess
import sys
import unittest


class EvidenceResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.passed = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.passed.append(test.id())


def main():
    directory = Path(__file__).resolve().parent
    stream = io.StringIO()
    suite = unittest.defaultTestLoader.discover(str(directory), pattern="test_*.py")
    result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=EvidenceResult).run(suite)
    output = stream.getvalue()
    print(output, end="")
    evidence = {
        "task": "R2-DEV-01", "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "repository": str(directory.parent.parent),
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=directory, text=True).strip(),
        "runtime": sys.version, "platform": platform.platform(),
        "tests_run": result.testsRun, "passed": result.passed,
        "failures": [(test.id(), detail) for test, detail in result.failures],
        "errors": [(test.id(), detail) for test, detail in result.errors],
        "skipped": [(test.id(), reason) for test, reason in result.skipped],
        "successful": result.wasSuccessful(), "output": output,
        "source_sha256": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(directory.glob("*.py"))},
        "authority_backend": "temporary SQLite, synchronous=FULL, DELETE journal; Linux flock",
        "witness": "separate SQLite test double, test HMAC key, same host and administrator",
        "target_effects": 0, "executable_capabilities": 0,
        "operational_validation": False,
    }
    (directory / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
