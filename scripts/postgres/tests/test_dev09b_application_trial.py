"""Offline wiring tests only. Test ports never serve an operational run."""
from types import SimpleNamespace
from unittest.mock import Mock
from pathlib import Path
import pytest
from scripts.postgres import dev09b_application_trial as t
from scripts.dedicated.dev09b import codec as c


def setup():
    tx=SimpleNamespace(rollback=Mock());conn=SimpleNamespace(close=Mock())
    trial=t.ApplicationTrial(connection=conn,transaction=tx,snapshot=None,session=None,authority=None,supervision=None,
        profile_json=b'',profile_verifier=None,prerequisite_contracts=None,source_root=None)
    return trial,conn,tx


def test_construction_is_inert_and_bad_snapshot_always_contains():
    trial,conn,tx=setup();assert not conn.close.called and not tx.rollback.called
    with pytest.raises(c.Invalid):trial.to_precommit()
    conn.close.assert_called_once();tx.rollback.assert_called_once()
    with pytest.raises(c.Invalid):trial.to_precommit()


def test_precontroller_close_is_attempted_even_if_rollback_fails():
    trial,conn,tx=setup();tx.rollback.side_effect=OSError('not logged')
    with pytest.raises(c.Invalid):trial.to_precommit()
    conn.close.assert_called_once();assert trial.state.value=='UNKNOWN'


def test_no_implicit_commit_or_grants_or_configuration_discovery():
    trial,_,_=setup()
    with pytest.raises(c.Invalid):trial.commit_once(commit_authorizer=None)
    # Actual inert behavior, not a text search through implementation comments.
    trial.inputs['transaction'].commit=Mock()
    trial.inputs['connection'].execute=Mock()
    with pytest.raises(c.Invalid):trial.to_precommit()
    assert not trial.inputs['transaction'].commit.called and not trial.inputs['connection'].execute.called


def test_explicit_commit_authorization_cannot_be_a_boolean():
    trial,_,_=setup();trial.controller=SimpleNamespace(commit_once=Mock(),contain=Mock(),containment=[])
    with pytest.raises(AttributeError):trial.commit_once(commit_authorizer=True)
    assert not trial.controller.commit_once.called and trial.controller.contain.called


def test_current_sql_is_only_a_target_bound_review_proposal():
    root=Path(__file__).resolve().parents[3]
    for name in ('dev09b_application_grants.proposed.sql','dev09b_application_close.proposed.sql'):
        sql=(root/'scripts/postgres'/name).read_text()
        assert 'PROPOSAL ONLY' in sql and t.SID in sql and 'ON_ERROR_STOP' in sql
        assert 'PASSWORD' not in sql and 'CREATE EXTENSION' not in sql
    grants=(root/'scripts/postgres/dev09b_application_grants.proposed.sql').read_text()
    assert 'PENDING MATERIAL APPROVAL' in grants and 'GRANT SELECT(version_num)' in grants
    assert 'GRANT ALL' not in grants and 'GRANT pg_read_all_settings' not in grants


def test_procedure_candidate_includes_exact_scripts_without_approval():
    from scripts.dedicated.dev09b import bundle
    root=Path(__file__).resolve().parents[3]
    data=bundle.build_application_trial_candidate(root)
    assert data['status']=='CANDIDATE_NOT_APPROVED' and data['operational_authority'] is False
    assert data['trial_procedure']['commit']=='NOT_AUTHORIZED'
    files={row['path'] for row in data['sources']}
    assert {'scripts/postgres/dev09b_application_trial.py',
        'scripts/postgres/dev09b_application_grants.proposed.sql','scripts/postgres/dev09b_application_close.proposed.sql',
        'scripts/postgres/dev09b_application_handoff.proposed.sql'}<=files


def test_safe_diagnostic_and_failed_rollback_still_close_without_authority():
    trial,conn,tx=setup();tx.rollback.side_effect=OSError('SECRET SQL PARAMETER VALUE')
    with pytest.raises(c.Unsupported) as failure:trial.to_precommit()
    assert trial.failure==dict(phase='precommit',code='TRIAL_REFUSED',exception_class=type(failure.value).__name__)
    assert trial.containment==[dict(rollback='FAILED',rollback_exception='OSError',close='RETURNED')]
    assert trial.state.value=='UNKNOWN' and 'SECRET' not in str(trial.containment)
