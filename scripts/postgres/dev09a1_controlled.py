"""Local planning/recovery only. No SQL, connection adapter or approval issuer.

Expected observations must come from independently reviewed deployment evidence.
Equality here is a consistency check, never authentication or authorization.
There is deliberately no Alembic transport or executable migration command.
"""
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import re


class Refused(ValueError):
    """Fixed, sanitized decision codes only."""


def require(condition, code):
    if not condition:
        raise Refused(code)


ENVIRONMENTS = {'DEV': ('dev', 'livenet_v2_dev'),
                'STAGING': ('staging', 'livenet_v2_staging'),
                'PROD-VM': ('prod', 'livenet_v2_prod'),
                'PROD-K8S': ('prod', 'livenet_v2_prod')}
LEDGERS = ('public.alembic_version', 'public.alembic_security_version')


@dataclass(frozen=True)
class Plan:
    environment: str
    profile: str
    application: str
    security: str | None
    application_ledger: str = LEDGERS[0]
    security_ledger: str = LEDGERS[1]


def make_plan(*, environment, profile, application, security, operation):
    require(type(environment) is str and environment in ENVIRONMENTS, 'ENVIRONMENT_REFUSED')
    require(operation == 'upgrade', 'OPERATION_REFUSED')
    require(type(profile) is str and profile in ('MVP', 'AUTH03-ISOLATED'), 'PROFILE_REFUSED')
    require((profile, application, security) in (
        ('MVP', 'f066a01a7230', 'b12b01a7230'),
        ('AUTH03-ISOLATED', 'f067a01a7230', None)), 'REVISION_REFUSED')
    return Plan(environment, profile, application, security)


def check_plan(plan):
    require(type(plan) is Plan, 'PLAN_REFUSED')
    expected = make_plan(environment=plan.environment, profile=plan.profile,
                         application=plan.application, security=plan.security, operation='upgrade')
    require(plan == expected, 'LEDGER_REFUSED')


@dataclass(frozen=True)
class Target:
    environment: str
    profile: str
    database: str
    system_identifier: str
    hostname: str
    port: int
    ca_sha256: str
    sslmode: str
    role: str
    container_id: str
    network_id: str
    image_id: str
    storage_identity: str
    isolated: bool
    published_ports: tuple
    disposable_run: str | None


@dataclass(frozen=True)
class Privileges:
    role: str
    superuser: bool
    createdb: bool
    createrole: bool
    replication: bool
    bypassrls: bool
    inherit: bool
    canlogin: bool
    memberships: tuple
    # Exact reviewed capability inventory, not SQL generated from these strings.
    capabilities: tuple


def validate_local(plan, expected, observed, privileges, expected_privileges, *, forbidden):
    """No I/O. No credential fields. Strict complete observations; no discovery.

    forbidden is an independently collected inventory of operational identities,
    with (database, SID, endpoint, container, network, storage) tuples. Completeness
    and freshness of every input remain external, unimplemented trust requirements.
    """
    check_plan(plan)
    require(type(expected) is Target and type(observed) is Target, 'TARGET_REFUSED')
    require(expected == observed, 'IDENTITY_DIVERGENCE')
    t = observed
    require(t.environment == plan.environment and t.profile == plan.profile, 'SCOPE_REFUSED')
    env, name = ENVIRONMENTS[plan.environment]
    for key in ('database', 'system_identifier', 'hostname', 'ca_sha256', 'role',
                'container_id', 'network_id', 'image_id', 'storage_identity'):
        require(type(getattr(t, key)) is str and bool(getattr(t, key)), 'IDENTITY_INCOMPLETE')
    require(type(t.port) is int and 1 <= t.port <= 65535, 'PORT_REFUSED')
    require(t.system_identifier.isascii() and t.system_identifier.isdecimal()
            and 0 < int(t.system_identifier) < 2**64, 'CLUSTER_REFUSED')
    require(t.system_identifier not in ('7698845469694267426', '7699783234487926818'),
            'HISTORICAL_TARGET_REFUSED')
    require(re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?', t.hostname)
            and '..' not in t.hostname, 'HOSTNAME_REFUSED')
    require(t.sslmode == 'verify-full', 'TLS_REFUSED')
    require(all(re.fullmatch(r'[0-9a-f]{64}', getattr(t, k))
                for k in ('ca_sha256', 'container_id', 'network_id', 'image_id')),
            'DIGEST_REFUSED')
    require(t.isolated is True and type(t.published_ports) is tuple and not t.published_ports,
            'NETWORK_REFUSED')
    if t.disposable_run is None:
        require(t.profile == 'MVP' and t.database == name, 'DATABASE_REFUSED')
    else:
        require(plan.environment == 'DEV' and type(t.disposable_run) is str
                and re.fullmatch(r'livenet-dev09a1-[0-9a-f]{10}', t.disposable_run),
                'DISPOSABLE_REFUSED')
        require(t.database == name + '_' + t.disposable_run.rsplit('-', 1)[1], 'DATABASE_REFUSED')
    require(t.role == 'lnv2_' + env + '_migrator', 'ROLE_REFUSED')
    require(type(forbidden) is tuple and all(type(v) is tuple and len(v) == 6
            and all(type(x) is str and x for x in v) for v in forbidden), 'COLLISION_INVENTORY_REFUSED')
    identity = (t.database, t.system_identifier, t.hostname, t.container_id,
                t.network_id, t.storage_identity)
    require(not any(any(a == b for a, b in zip(identity, other)) for other in forbidden),
            'OPERATIONAL_COLLISION')
    require(type(privileges) is Privileges and type(expected_privileges) is Privileges
            and privileges == expected_privileges and privileges.role == t.role, 'PRIVILEGES_DIVERGE')
    require(all(type(getattr(privileges, k)) is bool for k in (
        'superuser', 'createdb', 'createrole', 'replication', 'bypassrls', 'inherit', 'canlogin')),
        'PRIVILEGES_INCOMPLETE')
    require(not any((privileges.superuser, privileges.createdb, privileges.createrole,
                     privileges.replication, privileges.bypassrls, privileges.inherit))
            and privileges.canlogin is True and type(privileges.memberships) is tuple
            and not privileges.memberships, 'ESCALATION_REFUSED')
    require(type(privileges.capabilities) is tuple and bool(privileges.capabilities)
            and all(type(x) is str and re.fullmatch(r'[a-z_]+:[a-z_]+', x)
                    for x in privileges.capabilities)
            and len(set(privileges.capabilities)) == len(privileges.capabilities), 'CAPABILITIES_REFUSED')
    return _decision_record(plan, t)


def _decision_record(plan, target):
    """Sanitized local audit projection; digest is not a signature or authority."""
    check_plan(plan)
    require(type(target) is Target, 'TARGET_REFUSED')
    payload = {'plan': asdict(plan), 'target_digest': sha256(
        json.dumps(asdict(target), sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
        'local_consistency': 'PASS', 'authorization': 'ABSENT',
        'execution': 'BLOCKED', 'migration_command': None}
    payload['decision_sha256'] = sha256(json.dumps(payload, sort_keys=True,
        separators=(',', ':')).encode()).hexdigest()
    return payload


def execute(plan):
    """Hard refusal before imports/transports. No enable flag or callback port.

    Future reviewed integration must use preserved AUTH03/F02/G4/security gates;
    this planner neither invokes Alembic directly nor supplies external approval.
    """
    check_plan(plan)
    raise Refused('PROTECTED_GATES_CLOSED_NO_EXTERNAL_AUTHORITY')


@dataclass(frozen=True)
class Recovery:
    phase: str = 'BEFORE_VALIDATION'
    application_committed: bool = False
    security_committed: bool = False


def transition(state, event):
    """Synthetic recovery model, not a durable registry or operational runner.

    Terminal failures never transition to execution; independent inspection and a
    separately approved new operation are required even after confirmed rollback.
    Missing journal/commit acknowledgement is UNKNOWN, never permission to retry.
    """
    require(type(state) is Recovery and type(event) is str, 'RECOVERY_REFUSED')
    require(type(state.application_committed) is bool and type(state.security_committed) is bool
            and not (state.security_committed and not state.application_committed), 'RECOVERY_REFUSED')
    legal = {'BEFORE_VALIDATION': (False, False), 'VALIDATED': (False, False),
             'APPLICATION_TX': (False, False), 'APPLICATION_COMMITTING': (False, False),
             'BETWEEN_CHAINS': (True, False), 'SECURITY_TX': (True, False),
             'SECURITY_COMMITTING': (True, False), 'COMPLETE': (True, True)}
    terminal = ('STOPPED', 'ROLLED_BACK', 'PARTIAL', 'UNKNOWN', 'DRIFT')
    require(state.phase in legal or state.phase in terminal, 'RECOVERY_REFUSED')
    if state.phase in legal:
        require((state.application_committed, state.security_committed) == legal[state.phase],
                'RECOVERY_REFUSED')
    require(state.phase not in terminal and state.phase != 'COMPLETE', 'RETRY_REFUSED')
    a, s = state.application_committed, state.security_committed
    if event == 'revision_drift':
        return Recovery('DRIFT', a, s)
    if event == 'connection_lost' or event == 'journal_unknown':
        return Recovery('UNKNOWN', a, s)
    if event == 'fail':
        return Recovery('UNKNOWN' if state.phase.endswith(('COMMITTING', '_TX')) else
                        'PARTIAL' if a else 'STOPPED', a, s)
    if event == 'rollback_confirmed':
        require(state.phase in ('APPLICATION_TX', 'SECURITY_TX'), 'ROLLBACK_REFUSED')
        return Recovery('PARTIAL' if a else 'ROLLED_BACK', a, s)
    next_phase = {('BEFORE_VALIDATION', 'validated'): 'VALIDATED',
                  ('VALIDATED', 'begin_application'): 'APPLICATION_TX',
                  ('APPLICATION_TX', 'commit_requested'): 'APPLICATION_COMMITTING',
                  ('APPLICATION_COMMITTING', 'commit_ack'): 'BETWEEN_CHAINS',
                  ('BETWEEN_CHAINS', 'begin_security'): 'SECURITY_TX',
                  ('SECURITY_TX', 'commit_requested'): 'SECURITY_COMMITTING',
                  ('SECURITY_COMMITTING', 'commit_ack'): 'COMPLETE'}.get((state.phase, event))
    require(next_phase is not None, 'TRANSITION_REFUSED')
    return Recovery(next_phase, a or next_phase == 'BETWEEN_CHAINS', next_phase == 'COMPLETE')


def main(argv=None):
    """Explicit read-only planning CLI. No execute option, DSN or credentials."""
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ('environment', 'profile', 'application', 'security', 'operation'):
        parser.add_argument('--' + flag, required=True)
    values = vars(parser.parse_args(argv))
    if values['security'] == 'none':
        values['security'] = None
    try:
        selected = make_plan(**values)
    except Refused as error:
        print(json.dumps({'decision': str(error), 'execution': 'BLOCKED'}))
        return 2
    print(json.dumps({'plan': asdict(selected), 'local_validation': 'NOT_PERFORMED',
                      'authorization': 'ABSENT', 'execution': 'BLOCKED'}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
