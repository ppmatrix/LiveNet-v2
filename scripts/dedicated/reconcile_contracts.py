"""Read-only source reconciliation. Never updates or approves AUTH-03."""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def report(root=ROOT):
    manifest_path = root / 'scripts/postgres/auth03_executor_integrity.json'
    manifest = json.loads(manifest_path.read_text())
    expected = {str(p.relative_to(root)) for d in ('backend/app', 'backend/migrations')
                for p in (root / d).rglob('*.py')}
    expected |= {'backend/alembic.ini','backend/requirements.txt','scripts/postgres/auth03_alembic_executor.py'}
    mismatches = []
    for name, digest in sorted(manifest.items()):
        p = root / name
        actual = hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
        if actual != digest:
            mismatches.append({'path':name,'manifest_sha256':digest,'actual_sha256':actual})
    graphs = {}
    for label, folder in [('application','backend/migrations/versions'),('security','backend/security_migrations/versions')]:
        revisions = []
        for p in sorted((root / folder).glob('*.py')):
            values = {}
            for node in ast.parse(p.read_text()).body:
                if isinstance(node,(ast.Assign,ast.AnnAssign)):
                    for target in (node.targets if isinstance(node,ast.Assign) else [node.target]):
                        if isinstance(target,ast.Name) and target.id in ('revision','down_revision'):
                            values[target.id] = ast.literal_eval(node.value)
            if 'revision' in values:
                revisions.append({'path':str(p.relative_to(root)),**values,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
        graphs[label] = revisions
    return {'authority':'source evidence only; no approval or execution permission',
            'auth03':{'manifest_sha256':hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
                      'manifest_entries':len(manifest),'expected_entries':len(expected),
                      'missing':sorted(expected-set(manifest)),'extra':sorted(set(manifest)-expected),
                      'mismatches':mismatches},'migration_graphs':graphs}


if __name__ == '__main__':
    print(json.dumps(report(),indent=2))
