"""Offline historical coverage pinned to pre-PREPARED commit 2f86582.

Materializes Git objects in pytest's temporary directory; never checks out or
changes historical manifests. No database, network, subprocess runner or secrets.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

REVISION = "2f86582"
ROOT = Path(__file__).resolve().parents[3]


def git_bytes(*args):
    process = subprocess.Popen(["git", "-C", str(ROOT), *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = process.communicate()
    if process.returncode:
        raise AssertionError("Historical Git fixture unavailable: " + error.decode())
    return output


def load_module(name, path, monkeypatch):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    return module


def historical_tree(tmp_path):
    manifest_path = "scripts/postgres/auth03_executor_integrity.json"
    raw = git_bytes("show", REVISION + ":" + manifest_path)
    assert hashlib.sha256(raw).hexdigest() == "4819c697b7d12f7ab5cbb1fdfa9cf4c3fd0e98e93b53a60337296cc84036fc29"
    manifest = json.loads(raw)
    extra = git_bytes("ls-tree", "-r", "--name-only", REVISION, "backend/security_migrations", "backend/alembic-security.ini", "scripts/postgres/m12b_security_migration.py").decode().splitlines()
    for name in sorted(set(manifest) | set(extra) | {manifest_path}):
        data = git_bytes("show", REVISION + ":" + name)
        if name in manifest:
            assert hashlib.sha256(data).hexdigest() == manifest[name], name
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return tmp_path


def historical_auth(root, monkeypatch):
    module = load_module("_dev09b_historical_auth03", root / "scripts/postgres/auth03_alembic_executor.py", monkeypatch)
    assert len(module.verify_bundle()) == 64
    return module


def historical_security(root, monkeypatch):
    contract = load_module("_dev09b_historical_security_contract", root / "backend/security_migrations/contract.py", monkeypatch)
    module = load_module("_dev09b_historical_m12b", root / "scripts/postgres/m12b_security_migration.py", monkeypatch)
    # Bind the real archived validator to its archived script_location; no stub.
    monkeypatch.setattr(module, "validate_configuration", contract.validate_configuration)
    return module
