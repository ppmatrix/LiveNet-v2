"""DEV09B prepared candidate source closure. No builder, runner or approval.

Historical manifests/packaging remain immutable. Missing crypto lock is explicit;
installed cryptography or matching source hashes cannot complete/approve a bundle.
"""
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import re

from . import codec as c
from .migration_catalog import MissingParameter
from . import crypto_dependencies as crypto


DIRECTORIES=("backend/app","backend/migrations","backend/security_migrations","scripts/dedicated/dev09b","scripts/postgres/g4")
EXTRA=(crypto.LOCK,crypto.PROVENANCE,"backend/alembic.ini","backend/alembic-security.ini","backend/requirements.txt",
       "backend/requirements-container.lock","scripts/postgres/dev09a2-executor.lock",
       "scripts/postgres/auth03_alembic_executor.py","scripts/postgres/m12b_security_migration.py",
       "scripts/postgres/m12b_security_coordinator.py","scripts/postgres/m12b_security_adapters.py")
MANDATORY=("backend/migrations/dev09b_prerequisites.py","backend/app/dedicated.py",
           "backend/security_migrations/versions/b12b01a7230_create_security.py")
LOCKS=("backend/requirements-container.lock","scripts/postgres/dev09a2-executor.lock",crypto.LOCK)


def read(root,path):
    p=Path(path)
    c.require(not p.is_absolute() and all(x not in {".",".."} for x in p.parts))
    full=Path(root)/p
    for item in [full,*list(full.parents)[:len(p.parts)-1]]:
        c.require(not item.is_symlink())
    if not full.is_file():raise MissingParameter("bundle.source."+path)
    return full.read_bytes()


def source_paths(root):
    paths=set(EXTRA)
    for directory in DIRECTORIES:
        folder=Path(root)/directory
        if not folder.is_dir():raise MissingParameter("bundle.source_directory."+directory)
        c.require(not folder.is_symlink())
        paths.update(str(p.relative_to(root)) for p in folder.rglob("*.py"))
    c.require(set(MANDATORY)<=paths)
    return sorted(paths)


def dependency_inventory(root):
    packages={}
    for lock in LOCKS:
        for line in read(root,lock).decode().splitlines():
            if not line.strip() or line.startswith("#"):continue
            match=re.fullmatch(r"([A-Za-z0-9_-]+)==([^ ]+) --hash=sha256:([0-9a-f]{64})",line)
            c.require(match is not None)
            name,version,digest=match.groups();name=name.lower().replace("_","-")
            entry={"name":name,"version":version,"artifact_sha256":digest}
            c.require(name not in packages or packages[name]==entry)
            packages[name]=entry
    return [packages[k] for k in sorted(packages)]


def build_candidate(root):
    crypto_raw, crypto_provenance = crypto.metadata(root)  # effective transitive closure
    paths=source_paths(root)
    dependencies=dependency_inventory(root)
    return {"schema_version":1,"profile":"DEV09B-PREPARED-1","status":"CANDIDATE_NOT_APPROVED",
            "operational_authority":False,
            "sources":[{"path":p,"sha256":sha256(read(root,p)).hexdigest()} for p in paths],
            "dependency_locks":[{"path":p,"sha256":sha256(read(root,p)).hexdigest()} for p in LOCKS],
            "dependencies":dependencies,
            "missing_parameters":["dependencies.cryptography.approved_transitive_lock",
                                  "dependencies.cryptography.executor_compatibility",
                                  "dependencies.cryptography.artifact_availability"],
            "dependency_completeness":"INCOMPLETE",
            "crypto_dependency_state":{"lock_sha256":sha256(crypto_raw).hexdigest(),
                "provenance_sha256":sha256(read(root,crypto.PROVENANCE)).hexdigest(),
                "transitive_closure":"VERIFIED_FROM_CANDIDATE_METADATA",
                "artifact_integrity":"UNVERIFIED", "artifact_availability":"NOT_PROVIDED",
                "executor_compatibility":"UNKNOWN", "approval":"NOT_PROVIDED"}}


@dataclass(frozen=True)
class CandidateIntegrity:
    sha256: str
    source_count: int
    missing_parameters: tuple


def verify_candidate(root,candidate):
    # Exact recomputation checks closure, every byte, lock and declared limitation.
    # It does not write a manifest, update a historical anchor or approve sources.
    expected=build_candidate(root)
    c.require(c.canonical(candidate)==c.canonical(expected))
    return CandidateIntegrity(sha256(c.canonical(candidate)).hexdigest(),len(expected["sources"]),
                              tuple(expected["missing_parameters"]))


def require_complete_candidate(root,candidate):
    observation=verify_candidate(root,candidate)
    if observation.missing_parameters:raise MissingParameter(observation.missing_parameters[0])
    # No operational success/approval path is implemented by this utility.
    raise c.Unsupported("Candidate integrity is not operational approval")


def inspect_crypto_dependencies(root, **explicit_ports):
    """Actual artifact/metadata/tag inspection, separate from source integrity.

    Without an explicit environment and trusted approval verifier, neither
    compatibility nor approval can be inferred from candidate JSON or booleans.
    Never installs artifacts or enables a runner.
    """
    return crypto.inspect(root, **explicit_ports)
