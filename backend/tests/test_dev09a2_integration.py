"""DEV09A2 offline: packaging proposals, local bridge, spec and backup integrity."""
import ast
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys

import pytest
from packaging.requirements import Requirement

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/dedicated'))
sys.path.insert(0,str(ROOT/'scripts/postgres'))
import dev09a2_integration as bridge
import dev09a2_packaging as pkg
import dev09fix01_packaging as fix
import dev09a2_target as target
import dev09a2_recovery as recovery

PROPOSALS=ROOT/'docs/operations/proposals/dev09a2'


def plan(**changes):
    values=dict(environment='DEV',profile='MVP',application='f066a01a7230',security='b12b01a7230',operation='upgrade')
    values.update(changes)
    return bridge.local.make_plan(**values)


def test_existing_protected_guards_are_invoked():
    result=bridge.prepare(plan())
    assert result['protected_guards']=={'AUTH03':'CLOSED','SECURITY':'CLOSED'}
    assert result['execution']=='BLOCKED' and result['migration_command'] is None
    assert len(result['audit_sha256'])==64
    assert result==bridge.prepare(plan())


def test_isolated_never_selects_security(monkeypatch):
    import m12b_security_migration as security
    monkeypatch.setattr(security,'require_execution_authorization',lambda *a:pytest.fail('security not selected'))
    result=bridge.prepare(plan(profile='AUTH03-ISOLATED',application='f067a01a7230',security=None))
    assert result['protected_guards']=={'AUTH03':'CLOSED'}
    assert result['plan']['security'] is None and result['execution']=='BLOCKED'


@pytest.mark.parametrize('change',[dict(application='head'),dict(operation='stamp'),dict(environment=''),dict(security='head'),dict(profile='unknown')])
def test_bad_requests_never_reach_guard(monkeypatch,change):
    monkeypatch.setattr(bridge,'continuity',lambda:pytest.fail('invalid request reached guard'))
    with pytest.raises(bridge.local.Refused):bridge.prepare(plan(**change))


def test_unexpected_open_guard_is_an_integrity_failure(monkeypatch):
    import auth03_alembic_executor as app
    monkeypatch.setattr(app,'operation_gate',lambda *a:None)
    with pytest.raises(bridge.local.Refused,match='UNEXPECTED_OPEN_GUARD'):bridge.prepare(plan())


def test_protected_hash_drift_is_refused(monkeypatch):
    monkeypatch.setattr(bridge,'PROTECTED',{**bridge.PROTECTED,'scripts/postgres/m12b_security_migration.py':'0'*64})
    with pytest.raises(bridge.local.Refused,match='PROTECTED_SOURCE_DIVERGENCE'):bridge.prepare(plan())


def test_cli_diagnostic_and_no_execution(capsys):
    args=['--environment','DEV','--profile','MVP','--application','f066a01a7230','--security','b12b01a7230','--operation','upgrade']
    assert bridge.main(args)==0
    assert json.loads(capsys.readouterr().out)['execution']=='BLOCKED'
    args[-1]='stamp'
    assert bridge.main(args)==2
    assert json.loads(capsys.readouterr().out)['decision']=='OPERATION_REFUSED'


def observations():
    t = bridge.local.Target('DEV','MVP','livenet_v2_dev_0123456789','7700691028849037338',
        'livenet-dev09a1-0123456789-db',5432,'a'*64,'verify-full','lnv2_dev_migrator',
        'b'*64,'c'*64,'d'*64,'tmpfs:0123456789',True,(),'livenet-dev09a1-0123456789')
    p = bridge.local.Privileges(t.role,False,False,False,False,False,False,True,(),
                                ('schema_create:synthetic',))
    return t,p


def test_local_identity_checks_feed_existing_closed_guards():
    t,p = observations()
    record = bridge.prepare_checked(plan(),t,t,p,p,forbidden=())
    assert record['local_validation']['local_consistency']=='PASS'
    assert record['local_validation']['authorization']=='ABSENT'
    assert record['protected_guards']=={'AUTH03':'CLOSED','SECURITY':'CLOSED'}
    assert record['execution']=='BLOCKED' and record['migration_command'] is None


def test_invalid_tls_never_reaches_protected_guard(monkeypatch):
    from dataclasses import replace
    t,p = observations();t = replace(t,sslmode='require')
    monkeypatch.setattr(bridge,'prepare',lambda *a:pytest.fail('invalid TLS reached guard'))
    with pytest.raises(bridge.local.Refused,match='TLS_REFUSED'):
        bridge.prepare_checked(plan(),t,t,p,p,forbidden=())


def test_privilege_substitution_never_reaches_protected_guard(monkeypatch):
    from dataclasses import replace
    t,p = observations()
    monkeypatch.setattr(bridge,'prepare',lambda *a:pytest.fail('invalid privileges reached guard'))
    with pytest.raises(bridge.local.Refused,match='PRIVILEGES_DIVERGE'):
        bridge.prepare_checked(plan(),t,t,replace(p,superuser=True),p,forbidden=())


def test_patch_is_unapplied_and_exact():
    index=json.loads((PROPOSALS/'proposal-index.json').read_text())
    assert index['applied'] is False and len(index['entries'])==6
    patch=(PROPOSALS/'protected-changes.NOT-APPROVED.patch').read_text()
    for path,entry in index['entries'].items():
        assert sha256((ROOT/path).read_bytes()).hexdigest()==entry['before_sha256']
        proposed=(PROPOSALS/entry['copy']).read_bytes()
        assert sha256(proposed).hexdigest()==entry['proposed_sha256']
        assert '--- a/'+path in patch and '+++ b/'+path in patch
        assert proposed!=(ROOT/path).read_bytes()
        if path.endswith('.py'):
            original=ast.parse((ROOT/path).read_text());new=ast.parse(proposed)
            functions={x.name:x for x in new.body if isinstance(x,(ast.FunctionDef,ast.ClassDef))}
            for node in original.body:
                if isinstance(node,(ast.FunctionDef,ast.ClassDef)):
                    assert ast.dump(node)==ast.dump(functions[node.name])
            seam=functions['prepare_dedicated_request']
            namespace={}
            exec(compile(ast.fix_missing_locations(ast.Module(body=[seam],type_ignores=[])),path,'exec'),namespace)
            assert namespace['prepare_dedicated_request'](plan())['execution']=='BLOCKED'


def test_exact_dockerignore_excludes_adversarial_content():
    allowed=tuple(fix.frozen_inventory())
    text=pkg.dockerignore(allowed)
    inventory=(*allowed,'backend/app/injected.py','backend/app/.env','backend/security_migrations/evil.py',
               'scripts/postgres/private.key','secrets/dev09b/password','.git/config','backend/app/__pycache__/x.pyc')
    assert pkg.selected_files(text,inventory)==set(allowed)
    assert pkg.selected_files(text,inventory[:-1])==set(allowed)
    assert pkg.selected_files(text,('secrets/private.pem',))==set()
    historical=(PROPOSALS/'scripts__postgres__auth03_executor.Dockerfile.dockerignore.proposed').read_text()
    assert text != historical
    # Historical parent exceptions include descendants under actual Moby
    # semantics. Preserve the proposal as evidence and detect its defect.
    assert 'backend/app/injected.py' in pkg.selected_files(historical,inventory)
    assert 'scripts/postgres/private.key' in pkg.selected_files(historical,inventory)


@pytest.mark.parametrize('path',['backend/app/**','backend/app/*.py','../secrets','/etc/passwd','file\n!secrets','folder/[x]','file?','!secret','a\\b'])
def test_wildcards_or_traversal_not_supported(path):
    with pytest.raises(ValueError):pkg.dockerignore([path])


@pytest.mark.parametrize('text',['!backend/app.py\n','**\n!backend/**\n','**\n!file\n!file\n','**\n*.pem\n'])
def test_broadened_ignore_grammar_refused(text):
    with pytest.raises(ValueError):pkg.selected_files(text,('file',))


def test_pinned_executor_image_and_no_operational_entrypoint():
    text=pkg.proposed_dockerfile()
    assert 'FROM '+pkg.PYTHON_REF in text
    assert '--require-hashes' in text and '--only-binary=:all:' in text
    assert 'COPY backend/security_migrations' in text
    assert 'exit 78' in text and 'alembic upgrade' not in text
    assert 'USER 10001:10001' in text
    assert text==(PROPOSALS/'scripts__postgres__auth03_executor.Dockerfile.proposed').read_text()
    compose=fix.compose_template()['services']['executor']
    assert compose['network_mode']=='none' and compose['entrypoint']==['/bin/sh','-c','exit 78']
    assert not any(k in compose for k in ('ports','secrets','volumes','networks','environment'))
    assert compose['read_only'] and compose['cap_drop']==['ALL'] and compose['pull_policy']=='never'


@pytest.mark.parametrize('name,code', [
    ('allowed_sources','HISTORICAL_SOURCE_API_DISABLED_USE_FIX01'),
    ('proposed_compose','HISTORICAL_COMPOSE_API_DISABLED_USE_FIX01'),
])
def test_historical_apis_refuse_before_io(name, code, monkeypatch):
    import socket
    import subprocess
    from alembic import command

    def forbidden(*args, **kwargs):
        pytest.fail('historical API attempted I/O or migration')

    for method in ('read_bytes','read_text','rglob'):
        monkeypatch.setattr(Path,method,forbidden)
    monkeypatch.setattr(subprocess,'Popen',forbidden)
    monkeypatch.setattr(socket,'create_connection',forbidden)
    for method in ('upgrade','downgrade','stamp'):
        monkeypatch.setattr(command,method,forbidden)
    with pytest.raises(ValueError,match='^'+code+'$'):
        getattr(pkg,name)()


def test_security_sentinel_cannot_expand_frozen_context(tmp_path, monkeypatch):
    inventory=fix.context_inventory()
    sources=fix.frozen_inventory()
    assert len(sources)==66 and len(inventory)==68
    repo=tmp_path/'repo';repo.mkdir(mode=0o700)
    for name in set(sources)|{fix.CANDIDATE,fix.AGGREGATE,fix.APP02_COPY}:
        p=repo/name;p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes((ROOT/name).read_bytes())
    sentinel='backend/security_migrations/unreviewed_attest02.py'
    (repo/sentinel).write_text('# BENIGN SYNTHETIC SENTINEL\n')
    monkeypatch.setattr(fix,'ROOT',repo)
    assert fix.frozen_inventory()==sources
    assert fix.context_inventory()==inventory
    actual=fix.materialize_context(tmp_path/'context')
    assert actual==inventory and sentinel not in actual
    assert fix.verify_context(tmp_path/'context')==inventory
    with pytest.raises(ValueError,match='HISTORICAL_SOURCE_API_DISABLED'):
        pkg.allowed_sources()


def test_current_compose_refuses_historical_promotion():
    historical=json.loads((PROPOSALS/'compose.auth03-executor.yaml.proposed').read_text())
    assert historical['services']['executor']['build']['context']=='.'
    with pytest.raises(fix.Refused):fix.verify_compose(historical)
    current=fix.compose_template()
    assert current['services']['executor']['image'] is None
    assert 'build' not in current['services']['executor']
    assert current['services']['executor']['entrypoint']==['/bin/sh','-c','exit 78']
    with pytest.raises(fix.Refused):fix.verify_compose(current)


def test_executor_lock_closed_and_consistent_with_approved_requirements():
    lock=(ROOT/'scripts/postgres/dev09a2-executor.lock').read_text()
    entries={}
    for line in lock.splitlines():
        if not line or line.startswith('#'):continue
        requirement,digest=line.split(' --hash=sha256:')
        req=Requirement(requirement)
        assert len(digest)==64 and all(x in '0123456789abcdef' for x in digest)
        entries[req.name.lower().replace('_','-')]=(req,digest)
    assert len(entries)==14 and 'gunicorn' not in entries
    for line in (ROOT/'backend/requirements.txt').read_text().splitlines():
        req=Requirement(line)
        pinned,_=entries[req.name.lower().replace('_','-')]
        assert next(iter(pinned.specifier)).version in req.specifier
    # Match prior wheel records without approving those runtime artifacts.
    provenance=json.loads((ROOT/'infra/dedicated/dependency-provenance.json').read_text())
    wheel_hashes={x['sha256'] for x in provenance['wheels']}
    assert all(h in wheel_hashes for _,h in entries.values())


def spec():return target.specification('livenet-dev09b-0123456789')


def test_spec_allocates_no_identity_or_authority():
    s=spec();assert target.validate(s)==s
    assert all(v is None for v in s['identity_pending'].values())
    assert s['migration_command'] is None and not s['executable_migrations']
    assert s['tls']['mode']=='verify-full' and not s['network']['published_ports']
    assert s['storage']['type']=='tmpfs'
    target.refuse_collisions(s,('existing-other-project','livenet-v1-db'))


@pytest.mark.parametrize('run',['','livenet_v2_dev','livenet-dev09b-123','livenet-dev09a2-0123456789','../dev09b',None])
def test_invalid_run(run):
    with pytest.raises(ValueError):target.specification(run)


@pytest.mark.parametrize('field,value',[('application','head'),('security',None),('environment','PROD-VM'),
    ('image_id','postgres:16'),('database','livenet_v2_prod'),('status','APPROVED'),('migration_command','alembic upgrade head')])
def test_spec_changes_refused(field,value):
    s=spec();s[field]=value
    with pytest.raises(ValueError):target.validate(s)


def test_any_invented_identity_or_unknown_field_refused():
    for mutate in (lambda s:s['identity_pending'].update(system_identifier='123'),lambda s:s.update(approved=True)):
        s=spec();mutate(s)
        with pytest.raises(ValueError):target.validate(s)


@pytest.mark.parametrize('name',['livenet-dev09b-0123456789','livenet-dev09b-0123456789-db','livenet-dev09b-0123456789-data'])
def test_resource_collisions_refused(name):
    with pytest.raises(ValueError):target.refuse_collisions(spec(),(name,))


def test_local_image_link():
    valid=dict(Id=target.PG_ID,RepoDigests=[target.PG_REF],Os='linux',Architecture='amd64')
    target.verify_image(valid)
    for field,value in [('Id','sha256:'+'0'*64),('RepoDigests',[]),('Os','windows'),('Architecture','arm64')]:
        with pytest.raises(ValueError):target.verify_image({**valid,field:value})


def test_backup_integrity_and_corruption_rejection():
    data=b'PGDMP'+b'x'*100;digest=sha256(data).hexdigest()
    assert recovery.checked_backup(data,digest)==data
    for candidate,expected in [(data+b'x',digest),(b'BROKEN'+data[6:],digest),(data,'0'*64),(b'PGDMP',digest),(None,digest)]:
        with pytest.raises(ValueError):recovery.checked_backup(candidate,expected)


def test_recovery_independent_no_migration_import_or_operational_input():
    tree=ast.parse((ROOT/'scripts/dedicated/dev09a2_recovery.py').read_text())
    imports=[n.module or '' for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
    imports += [a.name for n in ast.walk(tree) if isinstance(n,ast.Import) for a in n.names]
    assert not any(any(x in name for x in ('alembic','app.','executor','controlled','migration')) for name in imports)
    assert 'dev09a2_target' in imports
    assert list(__import__('inspect').signature(recovery.run).parameters)==[]
