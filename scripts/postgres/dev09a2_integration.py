"""Read-only bridge to existing refusal guards. Never calls a migration adapter.

No approval, flag, callback or config can turn this diagnostic into execution.
Source continuity is checked before importing protected guard implementations.
"""
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path

import dev09a1_controlled as local

ROOT = Path(__file__).resolve().parents[2]
PROTECTED = {
    'scripts/postgres/auth03_alembic_executor.py': '66c18319414c29f49ae163ef86b098924592102b566cd894fd4824933704d00b',
    'scripts/postgres/m12b_security_migration.py': 'c2608a2c8d0391dc3e5960fe797d4c8f77be5165475cb0058de4f66dd51ed9fe',
    'scripts/postgres/m12b_security_coordinator.py': '33415d4b4c51dbb03a6f67332cc77c63aebc87b7a8f90ba20da1abd79d7a012c',
    'scripts/postgres/g4/contracts.py': '04531a6b9f2a33d2c6334dc025ef18b750014305716a9283e81db44dad257ffc',
}
MANIFEST = '4819c697b7d12f7ab5cbb1fdfa9cf4c3fd0e98e93b53a60337296cc84036fc29'


def continuity():
    paths = {**PROTECTED, 'scripts/postgres/auth03_executor_integrity.json': MANIFEST}
    for path, expected in paths.items():
        p = ROOT / path
        if p.is_symlink() or not p.is_file() or sha256(p.read_bytes()).hexdigest() != expected:
            raise local.Refused('PROTECTED_SOURCE_DIVERGENCE')


def prepare(plan):
    """Return an auditable refusal after invoking existing first-action guards.

    This is not a gate evaluation for a live target or an execution request.
    G4/F02/G2 cannot grant authority here and remain explicit unmet requirements.
    """
    local.check_plan(plan)
    continuity()
    import auth03_alembic_executor as app
    import m12b_security_migration as security
    if app.verify_bundle() != MANIFEST:
        raise local.Refused('APPROVED_BUNDLE_DIVERGENCE')
    guards = [('AUTH03', lambda: app.operation_gate('upgrade-baseline'), app.Refused)]
    if plan.security is not None:
        guards.append(('SECURITY', lambda: security.require_execution_authorization(None), security.Refused))
    results = {}
    for name, guard, refusal in guards:
        try:
            guard()
        except refusal:
            results[name] = 'CLOSED'
        else:
            # Unexpected gate state is an integrity failure, never readiness.
            raise local.Refused('UNEXPECTED_OPEN_GUARD')
    record = {'plan': asdict(plan), 'protected_guards': results,
              'source_hashes': dict(PROTECTED), 'AUTH03': MANIFEST,
              'F02_G4': 'CLOSED_NO_AUTHENTICATED_AUTHORITY', 'G2': 'UNCHANGED_NO_OPERATIONAL_EVIDENCE',
              'target_validation': 'REQUIRED_BEFORE_ANY_FUTURE_EXECUTION',
              'execution': 'BLOCKED', 'migration_command': None}
    record['audit_sha256'] = sha256(json.dumps(record,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return record


def prepare_checked(plan, expected, observed, privileges, expected_privileges, *, forbidden):
    """Connect existing local identity checks to the protected refusal diagnostic.

    Complete consistent local observations do not authenticate a target. This
    still always returns BLOCKED and has no connection or mutation capability.
    Invalid observations are refused before touching a protected guard.
    """
    validation = local.validate_local(plan, expected, observed, privileges,
                                       expected_privileges, forbidden=forbidden)
    record = prepare(plan)
    record['local_validation'] = validation
    del record['audit_sha256']
    record['audit_sha256'] = sha256(json.dumps(record, sort_keys=True,
        separators=(',', ':')).encode()).hexdigest()
    return record


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ('environment','profile','application','security','operation'):
        parser.add_argument('--'+field,required=True)
    values=vars(parser.parse_args(argv))
    if values['security']=='none': values['security']=None
    try:
        record=prepare(local.make_plan(**values))
    except local.Refused as error:
        print(json.dumps({'execution':'BLOCKED','decision':str(error)}))
        return 2
    print(json.dumps(record,sort_keys=True))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
