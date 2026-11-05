"""Audit output is evidence, never manifest regeneration or approval."""
import hashlib
import json
from pathlib import Path
import runpy

ROOT=Path(__file__).resolve().parents[2]
report=runpy.run_path(str(ROOT/'scripts/dedicated/reconcile_contracts.py'))['report']


def test_audit_detects_omissions_and_hash_changes_without_writing(tmp_path):
    names={'backend/app/source.py':'VALUE=1\n',
           'backend/migrations/versions/first.py':"revision: str = 'one'\ndown_revision: str | None = None\n",
           'backend/migrations/versions/second.py':"revision='two'\ndown_revision='one'\n",
           'backend/security_migrations/versions/security.py':"revision='independent'\ndown_revision=None\n",
           'backend/alembic.ini':'synthetic','backend/requirements.txt':'synthetic',
           'scripts/postgres/auth03_alembic_executor.py':'# synthetic\n'}
    for name,value in names.items():
        p=tmp_path/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(value)
    manifest={'backend/app/source.py':'0'*64}
    path=tmp_path/'scripts/postgres/auth03_executor_integrity.json';path.write_text(json.dumps(manifest))
    before={str(p):p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    result=report(tmp_path)
    assert len(result['auth03']['missing'])==5
    assert result['auth03']['mismatches'][0]['actual_sha256']==hashlib.sha256(b'VALUE=1\n').hexdigest()
    assert [(r['revision'],r['down_revision']) for r in result['migration_graphs']['application']]==[('one',None),('two','one')]
    assert result['migration_graphs']['security'][0]['revision']=='independent'
    assert before=={str(p):p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
