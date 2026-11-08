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


def build_application_candidate(root):
    """New source candidate, never rewrite/approve the historical prepared one.

    The image scripts are source declarations, not a complete target profile or
    observed catalog. Unresolved target parameters and conversion maps are kept
    explicit alongside the cryptographic dependency's independent limitations.
    """
    from . import fixed_catalog_sources as fixed
    from .migration_catalog import load_repository_sources
    root=Path(root);base=build_candidate(root)
    facts=fixed.source_declarations(root,load_repository_sources(root)[:-1])
    extra={'scripts/dedicated/dev09b/artifacts/pg16-source/sources.candidate.json',*(r['path'] for r in facts['postgres_sources']['sources']),'scripts/postgres/dev09b_own_settings.proposed.sql',fixed.MANIFEST,str(Path(fixed.MANIFEST).parent/'LICENSE.PostgreSQL'),
        'scripts/postgres/dev09b_application_transport.py',
        'scripts/postgres/dev09b_detailed_querytrial.py','scripts/postgres/dev09b_querytrial_launcher.py',
        'scripts/postgres/dev09b_query_trial.py',
        'scripts/postgres/dev09b_detailed_querytrial_inputs.proposed.json',
        'scripts/postgres/dev09b_detailed_querytrial_helper_inputs.proposed.json',
        *(r['path'] for r in facts['sources'])}
    paths={r['path'] for r in base['sources']}|extra
    base.update(profile='dev09b-application-f066-catalog-v2',
        sources=[dict(path=p,sha256=sha256(read(root,p)).hexdigest()) for p in sorted(paths)],
        source_declarations=facts,
        physical_profile_state='INCOMPLETE_TARGET_DECLARATIONS',
        missing_target_declarations=['target/executor bindings and role identities',
            'application checkpoint deparse and fixed catalog property maps; DEV-BASE querytrial technical context completed',
            'source-bound resolver declarations for row/array/TOAST objects',
            'trusted execution-session inspection contracts; own-session helper verified only for querytrial probe'])
    return base


def verify_application_candidate(root,candidate):
    expected=build_application_candidate(root)
    c.require(c.canonical(candidate,maximum_depth=32)==c.canonical(expected,maximum_depth=32))
    return CandidateIntegrity(sha256(c.canonical(candidate,maximum_depth=32)).hexdigest(),len(expected['sources']),
        tuple(expected['missing_parameters'])+tuple(expected['missing_target_declarations']))


def build_application_maps_candidate(root):
    """New candidate only; prior prepared/baseline JSON stays historical."""
    from . import application_catalog_context as app
    root=Path(root);_,manifest=app.load(root)
    candidate=build_application_candidate(root)
    paths={row['path'] for row in candidate['sources']}|{app.MANIFEST}
    paths.update(row['path'] for row in manifest['sources'])
    candidate['sources']=[dict(path=path,sha256=sha256(read(root,path)).hexdigest()) for path in sorted(paths)]
    candidate['missing_target_declarations']=['real target/executor bindings and role identities','independent PostgreSQL validation of candidate application deparse and implicit-object maps','authenticated source artifacts/profile and phase privilege plan','trusted execution-session inspection and independent persisted-ledger confirmation']
    candidate['application_maps']=dict(schema_version=1,scope='APPLICATION_ONLY',
        source_manifest_sha256=sha256(read(root,app.MANIFEST)).hexdigest(),
        postgres_execution='NOT_PERFORMED',operational_profile_approval='NOT_PROVIDED',
        parameter_binding='EXPLICIT_ROLES_AND_ENCODING_REQUIRED',
        dependent_type_acl='HUMAN_APPROVED_V2_ONLY_PUBLIC_USAGE_WITHOUT_GRANT_OPTION')
    return candidate


def verify_application_maps_candidate(root,candidate):
    expected=build_application_maps_candidate(root)
    c.require(c.canonical(candidate,maximum_depth=32)==c.canonical(expected,maximum_depth=32))
    return CandidateIntegrity(sha256(c.canonical(expected,maximum_depth=32)).hexdigest(),len(expected['sources']),
        tuple(expected['missing_parameters'])+tuple(expected['missing_target_declarations']))


def build_application_trial_candidate(root):
    """Procedure/source candidate only, never approval of grants or deployment."""
    root=Path(root);candidate=build_application_maps_candidate(root)
    paths={r['path'] for r in candidate['sources']}|{
        'scripts/postgres/dev09b_application_trial.py',
        'scripts/postgres/dev09b_application_grants.proposed.sql',
        'scripts/postgres/dev09b_application_close.proposed.sql',
        'scripts/postgres/dev09b_application_handoff.proposed.sql'}
    candidate['sources']=[dict(path=p,sha256=sha256(read(root,p)).hexdigest()) for p in sorted(paths)]
    candidate['trial_procedure']=dict(target_system_identifier='7705421224394444834',
        state='BLOCKED_OPERATIONAL_PORTS_PARAMETERS_AND_APPROVALS',
        authority_storage_trial_is_not_operational_authority=True,
        administrative_sql='PROPOSED_NOT_AUTHORIZED',commit='NOT_AUTHORIZED',
        trusted_adapters='NOT_IMPLEMENTED_BY_THIS_PROCEDURE')
    return candidate


def build_operational_candidate(root):
    """Separate candidate; leave earlier source manifests byte-for-byte intact."""
    root=Path(root);candidate=build_application_trial_candidate(root)
    paths={r['path'] for r in candidate['sources']}|{
        'scripts/postgres/dev09b_operational_trial.py',
        'scripts/postgres/dev09b_operational.proposed.json',
        'scripts/postgres/dev09b_application_identity.proposed.sql',
        'docs/operations/dev09b-first-application-trial.md'}
    candidate['sources']=[dict(path=p,sha256=sha256(read(root,p)).hexdigest()) for p in sorted(paths)]
    candidate['operational_adapters']=dict(state='IMPLEMENTED_OFFLINE_DEPLOYMENT_UNBOUND',
        control_channel='LINUX_AF_UNIX_SO_PEERCRED',
        target_tls='REQUIRED_NOT_DEPLOYED',
        continuity='SEPARATE_DURABLE_ONE_SHOT_WINDOW',
        supervision='INDEPENDENT_PROCESS_READ_ONLY_OBSERVER',
        first_trial='PRECOMMIT_THEN_ROLLBACK',
        approval='NOT_PROVIDED',administrative_changes='NOT_AUTHORIZED')
    candidate['trial_procedure']['trusted_adapters']='OFFLINE_IMPLEMENTED_LIVE_BINDINGS_REQUIRED'
    config=c.parse(read(root,'scripts/postgres/dev09b_operational.proposed.json'))
    candidate['missing_parameters'] += ['operational.'+name for name in config['unbound_required_inputs']]
    return candidate


def build_runtime_candidate(root):
    """Runtime preparation v2; historical operational-v1 is not regenerated."""
    root=Path(root);candidate=build_operational_candidate(root)
    paths={r['path'] for r in candidate['sources']}|{
        'scripts/postgres/dev09b_operational_cli.py',
        'scripts/postgres/dev09b_authority_bootstrap.py',
        'scripts/postgres/dev09b_authority_schema.proposed.sql',
        'scripts/postgres/dev09b_helper_policy_v2.proposed.sql',
        'scripts/postgres/dev09b_application_grants_v2.proposed.sql',
        'scripts/postgres/dev09b_trial_profile_roles.proposed.sql',
        'scripts/postgres/dev09b_runtime_policy.proposed.json',
        'scripts/postgres/dev09b_executor_configuration.proposed.json',
        'scripts/postgres/dev09b_trial.pg_hba.proposed.conf',
        'scripts/postgres/dev09b-runtime@.service.proposed',
        'compose.dev09b-querytrial-tls.proposed.yaml'}
    candidate['sources']=[dict(path=p,sha256=sha256(read(root,p)).hexdigest()) for p in sorted(paths)]
    candidate['runtime_preparation']=dict(state='IMPLEMENTED_OFFLINE_NOT_DEPLOYED',
        helper_policy=2,rollback_reconciliation='INDEPENDENT_FULL_PREFIX_ZERO_AND_DURABLE_JOURNAL',
        containment='INDEPENDENT_OF_RECONCILIATION_AND_AUTHORITY',
        final_verification='FULL_SOURCE_DERIVED_CLEANED_CATALOG',
        tls='VERIFY_FULL_AND_SAME_SESSION_DER_SHA256_PIN',
        storage='DISTINCT_DEVICE_MOUNT_AND_RESTORE_POLICY_REQUIRED',
        uid_collision_check='NO_MATCH_FOR_PROPOSED_NAMES_UIDS_GIDS_ON_PROGBOX_20261108',
        execution='NOT_AUTHORIZED',commit='NOT_AUTHORIZED',ledger_select=False)
    return candidate
