"""Local consistency and recovery, never operational authorization."""
from dataclasses import replace
import importlib.util
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('dev09a1_controlled', ROOT / 'scripts/postgres/dev09a1_controlled.py')
c = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = c
SPEC.loader.exec_module(c)


def plan(**changes):
    args = dict(environment='DEV', profile='MVP', application='f066a01a7230',
                security='b12b01a7230', operation='upgrade')
    args.update(changes)
    return c.make_plan(**args)


def fixture():
    target = c.Target('DEV', 'MVP', 'livenet_v2_dev_0123456789', '7700691028849037338',
        'livenet-dev09a1-0123456789-db', 5432, 'a'*64, 'verify-full', 'lnv2_dev_migrator',
        'b'*64, 'c'*64, 'd'*64, 'tmpfs:0123456789', True, (), 'livenet-dev09a1-0123456789')
    priv = c.Privileges(target.role, False, False, False, False, False, False, True, (),
                        ('schema_create:synthetic',))
    return target, priv


def validate(t=None, p=None, observed=None, priv=None, forbidden=()):
    base, rights = fixture()
    t, priv = t or base, priv or rights
    return c.validate_local(p or plan(), t, observed or t, priv, priv, forbidden=forbidden)


@pytest.mark.parametrize('env', c.ENVIRONMENTS)
def test_profiles(env):
    p = plan(environment=env)
    assert (p.application, p.security) == ('f066a01a7230', 'b12b01a7230')
    isolated = plan(environment=env, profile='AUTH03-ISOLATED', application='f067a01a7230', security=None)
    assert isolated.security is None and isolated.application_ledger != isolated.security_ledger


@pytest.mark.parametrize('change', [dict(application='head'), dict(application='heads'),
    dict(application='f067a01a7230'), dict(security='head'), dict(security=None),
    dict(operation='stamp'), dict(operation='downgrade'), dict(environment='production'),
    dict(profile=''), dict(profile='AUTH03-ISOLATED'), dict(application='base'),
    dict(environment=None), dict(profile=None)])
def test_invalid_plans(change):
    with pytest.raises(c.Refused): plan(**change)


def test_consistency_is_not_authorization():
    result = validate()
    assert result['local_consistency'] == 'PASS'
    assert result['execution'] == 'BLOCKED' and result['authorization'] == 'ABSENT'
    assert result['migration_command'] is None
    assert 'password' not in str(result) and len(result['decision_sha256']) == 64
    assert result == validate()


@pytest.mark.parametrize('field,value', [
    ('environment','STAGING'), ('profile','AUTH03-ISOLATED'), ('database','livenet_v2_prod'),
    ('system_identifier','0'), ('system_identifier','7698845469694267426'),
    ('system_identifier','x'), ('hostname','host other'), ('hostname','host..other'),
    ('ca_sha256','bad'), ('sslmode','require'), ('sslmode','verify-ca'), ('role','lnv2_dev_admin'),
    ('network_id',''), ('container_id','bad'), ('storage_identity',''), ('port',True),
    ('isolated',False), ('published_ports',(5432,)), ('published_ports',[]),
    ('disposable_run','livenet-dev09a-0123456789'), ('disposable_run',None)])
def test_invalid_target_even_if_both_inputs_agree(field, value):
    t, _ = fixture()
    with pytest.raises(c.Refused): validate(t=replace(t, **{field:value}))


@pytest.mark.parametrize('field', ['system_identifier','hostname','ca_sha256','role',
                                  'image_id','network_id','container_id','storage_identity'])
def test_identity_substitution(field):
    t, _ = fixture()
    with pytest.raises(c.Refused, match='IDENTITY_DIVERGENCE'):
        validate(observed=replace(t, **{field:'different'}))


@pytest.mark.parametrize('field', ['superuser','createdb','createrole','replication','bypassrls','inherit'])
def test_escalation(field):
    _, p = fixture()
    with pytest.raises(c.Refused, match='ESCALATION_REFUSED'):
        validate(priv=replace(p, **{field:True}))


@pytest.mark.parametrize('change', [dict(canlogin=False), dict(memberships=('owner',)),
    dict(capabilities=()), dict(capabilities=('all',)), dict(superuser=0)])
def test_insufficient_or_ambiguous_privileges(change):
    _, p = fixture()
    with pytest.raises(c.Refused): validate(priv=replace(p, **change))


def test_reviewed_privilege_divergence():
    t, p = fixture()
    with pytest.raises(c.Refused, match='PRIVILEGES_DIVERGE'):
        c.validate_local(plan(), t, t, replace(p, capabilities=('schema_create:other',)), p, forbidden=())


@pytest.mark.parametrize('index', range(6))
def test_each_operational_collision(index):
    t, _ = fixture()
    values = [t.database,t.system_identifier,t.hostname,t.container_id,t.network_id,t.storage_identity]
    other = ['different']*6
    other[index] = values[index]
    with pytest.raises(c.Refused, match='OPERATIONAL_COLLISION'): validate(forbidden=(tuple(other),))


def test_tampered_plan_ledgers_and_execution_gate():
    p = plan()
    with pytest.raises(c.Refused, match='LEDGER_REFUSED'):
        c.execute(replace(p, security_ledger=p.application_ledger))
    for p in (p, plan(profile='AUTH03-ISOLATED',application='f067a01a7230',security=None)):
        with pytest.raises(c.Refused, match='PROTECTED_GATES_CLOSED'): c.execute(p)


def states():
    s = c.Recovery()
    result = [s]
    for event in ('validated','begin_application','commit_requested','commit_ack',
                  'begin_security','commit_requested','commit_ack'):
        s = c.transition(s,event)
        result.append(s)
    return result


@pytest.mark.parametrize('index,expected', [(0,'STOPPED'),(1,'STOPPED'),(2,'UNKNOWN'),
    (3,'UNKNOWN'),(4,'PARTIAL'),(5,'UNKNOWN'),(6,'UNKNOWN')])
def test_failure_boundaries_and_no_retry(index, expected):
    failed = c.transition(states()[index], 'fail')
    assert failed.phase == expected
    with pytest.raises(c.Refused, match='RETRY_REFUSED'): c.transition(failed,'begin_application')


@pytest.mark.parametrize('index', range(7))
@pytest.mark.parametrize('event,expected', [('connection_lost','UNKNOWN'),
    ('journal_unknown','UNKNOWN'),('revision_drift','DRIFT')])
def test_unknown_or_drift_never_replays(index,event,expected):
    failed = c.transition(states()[index],event)
    assert failed.phase == expected
    with pytest.raises(c.Refused): c.transition(failed,'validated')


def test_rollback_limits_and_complete_no_replay():
    ss = states()
    assert c.transition(ss[2],'rollback_confirmed').phase == 'ROLLED_BACK'
    assert c.transition(ss[5],'rollback_confirmed').phase == 'PARTIAL'
    assert ss[-1] == c.Recovery('COMPLETE',True,True)
    for i in (0,1,3,4,6,7):
        with pytest.raises(c.Refused): c.transition(ss[i],'rollback_confirmed')
    with pytest.raises(c.Refused): c.transition(c.Recovery('BETWEEN_CHAINS'),'begin_security')
    with pytest.raises(c.Refused): c.transition(c.Recovery(),'commit_ack')


def test_explicit_cli(capsys):
    args = ['--environment','DEV','--profile','MVP','--application','f066a01a7230',
            '--security','b12b01a7230','--operation','upgrade']
    assert c.main(args) == 0
    assert 'NOT_PERFORMED' in capsys.readouterr().out
    args[5] = 'head'
    assert c.main(args) == 2
    assert 'REVISION_REFUSED' in capsys.readouterr().out
    with pytest.raises(SystemExit): c.main([])


def test_incomplete_observation_and_collision_inventory():
    t,p = fixture()
    with pytest.raises(c.Refused): c.validate_local(plan(),None,t,p,p,forbidden=())
    with pytest.raises(c.Refused): validate(forbidden=None)
    with pytest.raises(c.Refused): validate(priv=replace(p,capabilities=([],)))
