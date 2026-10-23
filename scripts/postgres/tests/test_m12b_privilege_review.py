"""Static review of inert Markdown SQL. Never imports DB/Alembic adapters."""

import ast
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import re

import pytest


ROOT = Path(__file__).resolve().parents[3]
DOCUMENT = ROOT / 'docs/specifications/f0/m12b-p2c2a-privilege-review.md'
TEXT = DOCUMENT.read_text()
PHASES = dict(re.findall(r'<!-- phase: (\w+) -->\s*```sql\n(.*?)```', TEXT, re.S))
AUTH_FILES = [
    'backend/migrations/env.py',
    'backend/migrations/versions/f067a01a7230_create_authorization_integrity_anchors.py',
    'backend/tests/test_authorization_anchor_integration.py',
    'backend/tests/test_authorization_anchor_migration.py',
    'backend/tests/test_authorization_anchor_safety.py',
    'compose.auth03-executor.yaml', 'compose.auth03-test.yaml',
    'docs/specifications/f0/auth03-alembic-executor.md',
    'docs/specifications/f0/auth03-integration-preparation.md',
    'scripts/postgres/auth03_alembic_executor.py',
    'scripts/postgres/auth03_executor.Dockerfile',
    'scripts/postgres/auth03_executor.Dockerfile.dockerignore',
    'scripts/postgres/auth03_executor.example.json',
    'scripts/postgres/auth03_executor_integrity.json',
    'scripts/postgres/tests/test_auth03_alembic_executor.py',
]


@pytest.fixture(scope='module', autouse=True)
def protect_auth_files():
    # Runtime side-effect sentinel; final task verification also compares earlier hashes.
    # AUTH-03 is a local, uncommitted bundle and is absent in a clean checkout.
    present = [p for p in AUTH_FILES if (ROOT / p).is_file()]
    before = {p: sha256((ROOT / p).read_bytes()).hexdigest() for p in present}
    yield
    assert before == {p: sha256((ROOT / p).read_bytes()).hexdigest() for p in present}


def normalized(phase):
    return ' '.join(PHASES[phase].upper().split())


def test_only_documented_sql_phases_exist():
    assert set(PHASES) == {'guard','provision','enable_login','window','handoff','harden_bootstrap','validate'}
    assert len(re.findall(r'```sql\n', TEXT)) == len(PHASES)
    assert 'nenhum bloco o ativa' in TEXT


def test_exact_identity_and_baseline_guard():
    guard = PHASES['guard']
    for value in ['livenet_m12b_test','livenet_m12b_bootstrap','7699783234487926818',
                  'f066a01a7230','authorization']:
        assert value in guard
    assert 'RAISE EXCEPTION' in guard and 'IS DISTINCT FROM' in guard


@pytest.mark.parametrize('role', ['migrator','app','security_owner','inspector'])
def test_new_roles_have_no_global_administration_or_initial_login(role):
    statement = next(s for s in PHASES['provision'].split(';') if 'CREATE ROLE livenet_m12b_'+role+' ' in s)
    for flag in ['NOLOGIN','NOINHERIT','NOSUPERUSER','NOCREATEDB','NOCREATEROLE','NOREPLICATION','NOBYPASSRLS']:
        assert flag in statement
    assert not re.search(r'(?<!NO)\b(SUPERUSER|CREATEDB|CREATEROLE|REPLICATION|BYPASSRLS)\b', statement)


def test_public_inheritance_and_explicit_connect():
    provision = normalized('provision')
    assert 'REVOKE CONNECT, TEMPORARY ON DATABASE LIVENET_M12B_TEST FROM PUBLIC' in provision
    assert 'GRANT CONNECT ON DATABASE LIVENET_M12B_TEST TO LIVENET_M12B_BOOTSTRAP, LIVENET_M12B_MIGRATOR, LIVENET_M12B_APP' in provision
    assert 'REVOKE USAGE' not in provision
    assert 'SET ROLE pode permitir escalada' in TEXT
    assert 'Não desconecta sessões já abertas' in TEXT


def test_create_window_is_scoped_and_later_revoked():
    grants = [s.strip() for s in PHASES['window'].split(';') if s.strip()]
    assert len(grants) == 3
    assert all('livenet_m12b_migrator' in s for s in grants)
    assert 'GRANT CREATE ON DATABASE livenet_m12b_test TO livenet_m12b_migrator' in grants
    assert 'GRANT CREATE ON SCHEMA public TO livenet_m12b_migrator' in grants
    closeout = normalized('handoff')
    assert 'REVOKE CREATE ON DATABASE LIVENET_M12B_TEST FROM LIVENET_M12B_MIGRATOR, LIVENET_M12B_SECURITY_OWNER' in closeout
    assert 'REVOKE CREATE ON SCHEMA PUBLIC FROM LIVENET_M12B_MIGRATOR, LIVENET_M12B_SECURITY_OWNER' in closeout


def test_no_app_ddl_or_grants_on_protected_domains_and_ledgers():
    for sql in PHASES.values():
        for statement in sql.split(';'):
            if statement.strip().startswith('GRANT'):
                if re.search(r'\b(inventory|audit)\.', statement) or 'ON SCHEMA public, inventory, audit' in statement:
                    assert statement.strip().endswith('TO livenet_m12b_inspector')
                    assert 'livenet_m12b_migrator' not in statement
                assert 'alembic_security_version' not in statement
                if 'livenet_m12b_app' in statement:
                    assert statement.strip().startswith('GRANT CONNECT ON DATABASE livenet_m12b_test')
    assert 'Não conceder DML nesta fase' in TEXT
    assert 'requisito R1 de migrator sem acesso' in TEXT


def test_explicit_ownership_handoff_not_just_revoke():
    handoff = normalized('handoff')
    assert 'ALTER SCHEMA SECURITY OWNER TO LIVENET_M12B_SECURITY_OWNER' in handoff
    for name in ['local_users','login_sessions','global_role_grants','login_throttles']:
        assert f'ALTER TABLE SECURITY.{name.upper()} OWNER TO LIVENET_M12B_SECURITY_OWNER' in handoff
    assert 'ALTER TABLE PUBLIC.ALEMBIC_SECURITY_VERSION OWNER TO LIVENET_M12B_SECURITY_OWNER' in handoff
    assert 'REASSIGN OWNED' not in handoff
    assert 'REVOKE CREATE na base/public não elimina' in TEXT
    assert 'depois dessas verificações' in TEXT


def test_no_destructive_or_secret_statements():
    for sql in PHASES.values():
        # Privilege names in has_table_privilege strings are read-only evidence.
        statements = re.sub(r"'(?:''|[^'])*'", "''", sql)
        assert not re.search(r'\b(DROP|TRUNCATE|DELETE|CASCADE)\b', statements, re.I)
        assert not re.search(r'\bPASSWORD\b|SCRAM-SHA-256\$|postgresql://', sql, re.I)
        assert not re.search(r'ALTER\s+(TABLE|SCHEMA)\s+(inventory|audit)\b', sql, re.I)


def effective_final_state():
    return dict(admin=False, memberships=set(), owners=set(), database={'CONNECT'},
                public_schema={'USAGE'}, protected=set(), ledgers=set(), routine_writes=False)


def validate_restricted_final(observation):
    # Contract model only, not a production PostgreSQL validator.
    expected = effective_final_state()
    if observation != expected:
        raise ValueError('Unexpected effective privileges; stop')


def test_final_minimal_login_model():
    validate_restricted_final(effective_final_state())


@pytest.mark.parametrize('field,value', [
    ('admin',True), ('memberships',{'pg_write_all_data'}), ('owners',{'security.local_users'}),
    ('database',{'CONNECT','TEMPORARY'}), ('database',{'CONNECT','CREATE'}),
    ('public_schema',{'USAGE','CREATE'}), ('protected',{'inventory.resources:SELECT'}),
    ('ledgers',{'public.alembic_version:UPDATE'}), ('routine_writes',True),
])
def test_effective_privilege_drift_fails_closed(field,value):
    observed = deepcopy(effective_final_state())
    observed[field] = value
    with pytest.raises(ValueError): validate_restricted_final(observed)


def test_missing_effective_observation_fails_closed():
    with pytest.raises(ValueError): validate_restricted_final({})


def test_bootstrap_hardening_and_incompatibilities_are_not_hidden():
    assert 'NOSUPERUSER NOCREATEDB NOCREATEROLE' in normalized('harden_bootstrap')
    for caveat in ['único administrador','não permite ativar o executor atual',
                   'UPDATE(updated_at)','não o contornar','rollback da migração não a revoga']:
        assert caveat in TEXT


def test_operation_gate_still_contains_mutation_block():
    path = ROOT/'scripts/postgres/auth03_alembic_executor.py'
    if not path.is_file():
        pytest.skip('Bundle AUTH-03 local ausente neste checkout')
    tree = ast.parse(path.read_text())
    gate = next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='operation_gate')
    assert any(isinstance(n,ast.Compare) and any(isinstance(op,ast.NotIn) for op in n.ops)
               and any(isinstance(v,ast.Name) and v.id=='MUTATIONS' for v in n.comparators)
               for n in ast.walk(gate))


def test_security_execution_contract_remains_disabled():
    tree = ast.parse((ROOT/'scripts/postgres/m12b_security_migration.py').read_text())
    contract = next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='ExecutionAuthorization')
    enabled = next(n for n in contract.body if isinstance(n,ast.AnnAssign) and n.target.id=='execution_enabled')
    assert ast.literal_eval(enabled.value) is False
