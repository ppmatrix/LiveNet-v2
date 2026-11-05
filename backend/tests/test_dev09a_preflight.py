"""Offline refusal tests for the disposable harness, never operational gates."""
from pathlib import Path

import pytest

from scripts.dedicated import dev09a_preflight as probe


@pytest.fixture
def identity():
    return {'run': 'livenet-dev09a-0123456789', 'database': 'livenet_v2_dev_0123456789',
            'hostname': 'livenet-dev09a-0123456789-db', 'system_identifier': '7700000000000000000',
            'network_id': 'a' * 64, 'container_id': 'b' * 64, 'ca_sha256': 'c' * 64,
            'runtime_role': 'lnv2_dev_runtime'}


@pytest.mark.parametrize('field,value', [
    ('database', 'livenet'), ('database', 'livenet_v2_prod'),
    ('database', 'livenet_v2_dev_9876543210'), ('hostname', 'db'),
    ('system_identifier', '7698845469694267426'), ('network_id', 'd' * 64),
    ('container_id', 'e' * 64), ('ca_sha256', 'f' * 64),
    ('runtime_role', 'lnv2_dev_admin'), ('run', 'livenet-dev09a-9876543210'),
])
def test_fixture_rejects_foreign_or_replaced_target(identity, field, value):
    with pytest.raises(ValueError, match='Fixture identity refused'):
        probe.require_identity(identity, identity | {field: value})


@pytest.mark.parametrize('fault', ['extra', 'missing', 'empty', 'malformed', 'not_dict'])
def test_fixture_rejects_unbound_identity(identity, fault):
    changed = dict(identity)
    if fault == 'extra':
        changed['approved'] = 'yes'
    elif fault == 'missing':
        changed.pop('network_id')
    elif fault == 'empty':
        changed['ca_sha256'] = ''
    elif fault == 'malformed':
        changed['system_identifier'] = 'untrusted'
    else:
        changed = list(changed.values())
    with pytest.raises(ValueError):
        probe.require_identity(changed, changed)


def test_local_observation_is_not_execution_authority(identity):
    assert probe.require_identity(identity, dict(identity)) is None
    plan = probe.static_plan()
    assert plan['migration_execution_authorized'] is False
    assert plan['dev09b_executable_command'] is None
    assert plan['mvp_application_path'][-1] == 'f066a01a7230'
    assert 'f067a01a7230' not in plan['mvp_application_path']
    assert plan['security']['chain'] == ['b12b01a7230']


def test_ast_reader_supports_annotations_without_importing_code(tmp_path, monkeypatch):
    monkeypatch.setattr(probe, 'ROOT', tmp_path)
    versions = tmp_path / 'versions'
    versions.mkdir()
    (versions / 'one.py').write_text(
        "revision: str = 'one'\ndown_revision = None\ndepends_on = None\n"
        "raise RuntimeError('must never import revision sources')\n")
    (versions / 'two.py').write_text("revision='two'\ndown_revision='one'\ndepends_on=None\n")
    assert probe.graph(versions)['chain'] == ['one', 'two']


@pytest.mark.parametrize('declarations', [
    [('a', None), ('b', None)],  # two roots
    [('a', 'b'), ('b', 'a')],  # cycle
    [('a', None), ('b', 'unknown')],  # disconnected
    [('a', None), ('a', None)],  # duplicate id
])
def test_ast_reader_refuses_ambiguous_history(tmp_path, monkeypatch, declarations):
    monkeypatch.setattr(probe, 'ROOT', tmp_path)
    for index, (revision, previous) in enumerate(declarations):
        (tmp_path / f'{index}.py').write_text(
            f'revision={revision!r}\ndown_revision={previous!r}\ndepends_on=None\n')
    with pytest.raises(ValueError):
        probe.graph(tmp_path)


def test_dedicated_factory_validation_is_not_full_environment_attestation():
    from app.dedicated import ConfigurationError, DedicatedSettings
    values = {'ENVIRONMENT': 'production', 'DATABASE_HOST': 'dev09a-db', 'DATABASE_PORT': 5432,
              'DATABASE_NAME': 'livenet_v2_prod', 'DATABASE_USER': 'lnv2_dev_runtime',
              'DATABASE_PASSWORD_FILE': '/synthetic/password'}
    # Existing protected behavior: syntactic acceptance is NOT proof of authorization.
    assert DedicatedSettings.from_mapping(values).database_name == 'livenet_v2_prod'
    with pytest.raises(ConfigurationError):
        DedicatedSettings.from_mapping(values | {'DATABASE_NAME': 'livenet'})
