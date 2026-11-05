"""Generate an inert packaging proposal, never build or apply it.

FIX01 corrects ancestor reinclusion: only leaf exceptions are generated. The
subset matcher includes parent matching; physical context verification remains
independent of this matcher. Historical proposal files are never rewritten here.

allowed_sources() and proposed_compose() are disabled historical APIs. Current
inventory and quarantine proposals belong to dev09fix01_packaging. Historical
descriptors remain available as archived proposal files, never as a fallback.
"""
from hashlib import sha256
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[2]
PYTHON_REF='python@sha256:dc9e92fcdc085ad86dda976f4cfc58856dba33a438a16db37ff00151b285c8ca'


def allowed_sources():
    """No discovery or approval authority; use FIX01's hash-bound inventory."""
    raise ValueError('HISTORICAL_SOURCE_API_DISABLED_USE_FIX01')


def dockerignore(paths):
    allowed=set()
    for path in paths:
        if type(path) is not str or not path:
            raise ValueError('LITERAL_PATH_REQUIRED')
        p=Path(path)
        if (type(path) is not str or not path or path != p.as_posix()
                or path != path.strip() or p.is_absolute() or '..' in p.parts
                or any(c in path for c in '*?[]!\\\n\r')):
            raise ValueError('LITERAL_PATH_REQUIRED')
        allowed.add(path)
    return '**\n'+'\n'.join('!'+p for p in sorted(allowed))+'\n'


def selected_files(text, inventory):
    """Moby's ancestor matching for ** followed by literal ! exceptions only.

    A directory exception includes descendants. This is deliberately NOT an
    exact-name membership oracle and does not implement arbitrary Docker globs.
    """
    lines=text.splitlines()
    if not lines or lines[0]!='**': raise ValueError('DENY_ALL_REQUIRED')
    literals=[]
    for line in lines[1:]:
        if not line.startswith('!'): raise ValueError('LITERAL_PATH_REQUIRED')
        p=line[1:]
        dockerignore([p.rstrip('/')])
        literals.append(p.rstrip('/'))
    if len(set(literals))!=len(literals): raise ValueError('DUPLICATE_RULE')
    return {p for p in inventory if not p.endswith('/') and any(
        p == literal or p.startswith(literal + '/') for literal in literals)}


def proposed_dockerfile():
    return f'''# DEV09A2 proposal NOT APPROVED: no build or deployment authorization.
FROM {PYTHON_REF}
WORKDIR /opt/auth03
COPY scripts/postgres/dev09a2-executor.lock /tmp/executor.lock
RUN pip install --index-url https://pypi.org/simple --only-binary=:all: --require-hashes --no-cache-dir --no-compile -r /tmp/executor.lock
RUN pip check
COPY backend/app backend/app
COPY backend/migrations backend/migrations
COPY backend/security_migrations backend/security_migrations
COPY backend/alembic.ini backend/alembic-security.ini backend/requirements.txt backend/
COPY scripts/postgres/auth03_alembic_executor.py scripts/postgres/auth03_executor_integrity.json scripts/postgres/
COPY scripts/postgres/dev09a1_controlled.py scripts/postgres/dev09a2_integration.py scripts/postgres/
COPY scripts/postgres/m12b_security_migration.py scripts/postgres/m12b_security_coordinator.py scripts/postgres/m12b_security_adapters.py scripts/postgres/
COPY scripts/postgres/g4 scripts/postgres/g4
ENV PYTHONPATH=/opt/auth03/backend:/opt/auth03/scripts/postgres PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER 10001:10001
# Source diagnostics only. Historical guards remain closed; no Alembic CLI.
ENTRYPOINT ["/bin/sh", "-c", "exit 78"]
CMD ["python", "-c", "raise SystemExit('DEV09B authorization required')"]
'''


def proposed_compose():
    """Never regenerate the historical root-context descriptor for current use."""
    raise ValueError('HISTORICAL_COMPOSE_API_DISABLED_USE_FIX01')
