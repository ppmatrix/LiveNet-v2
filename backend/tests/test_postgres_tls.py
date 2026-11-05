"""Offline TLS boundary and factory tests; the certificate is public test data.

The fixed CA fixture is parsed only, never used as operational trust. Native
certificate validity, hostname and TLS negotiation are tested in dev06_check.py.
"""
import json
from pathlib import Path
from unittest.mock import Mock

import pytest
from sqlalchemy.dialects.postgresql.psycopg import PGDialect_psycopg

import dedicated_wsgi
from app.dedicated import ConfigurationError, create_dedicated_app
from app.postgres_tls import InvalidTLS, PostgresTLS
from test_dedicated_entrypoint import configuration, no_services, request


@pytest.fixture
def tls_values(tmp_path):
    path=tmp_path/'ca.crt'
    path.write_bytes((Path(__file__).parent/'fixtures/dev06-parsing-only-ca.crt').read_bytes())
    path.chmod(0o444)
    return {'DATABASE_SSLMODE':'verify-full','DATABASE_SSLROOTCERT_FILE':str(path)}


@pytest.fixture
def tls_configuration(configuration,tls_values):
    path,values=configuration
    path.write_text(json.dumps(values|tls_values))
    return path,values|tls_values


def test_tls_entrypoint_is_explicit_and_keeps_legacy_configuration_closed(tls_configuration):
    path,_=tls_configuration
    with pytest.raises(ConfigurationError): dedicated_wsgi.create_app(str(path))
    app=dedicated_wsgi.create_tls_app(str(path))
    assert request(app.test_client(),'/api/v1/health').status_code==200
    assert request(app.test_client(),'/api/v1/ready').status_code==503


def test_legacy_entrypoint_does_not_silently_select_tls(configuration):
    path,_=configuration
    with pytest.raises(ConfigurationError): dedicated_wsgi.create_tls_app(str(path))
    assert request(dedicated_wsgi.create_app(str(path)).test_client(),'/api/v1/health').status_code==200


@pytest.mark.parametrize('missing',['DATABASE_SSLMODE','DATABASE_SSLROOTCERT_FILE'])
def test_tls_keys_are_required_and_have_no_environment_fallback(tls_configuration,missing,monkeypatch):
    path,values=tls_configuration
    monkeypatch.setenv(missing,str(values.pop(missing)))
    path.write_text(json.dumps(values))
    with pytest.raises(ConfigurationError): dedicated_wsgi.create_tls_app(str(path))


@pytest.mark.parametrize('mode',['disable','allow','prefer','require','verify-ca','',None,True])
def test_weaker_modes_are_rejected(tls_values,mode):
    with pytest.raises(InvalidTLS): PostgresTLS.from_mapping(tls_values|{'DATABASE_SSLMODE':mode})


@pytest.mark.parametrize('extra',['hostaddr','PGSERVICE','DATABASE_SSLKEY_FILE'])
def test_connection_overrides_are_not_accepted_as_tls_settings(tls_values,extra):
    with pytest.raises(InvalidTLS): PostgresTLS.from_mapping(tls_values|{extra:'untrusted'})


@pytest.mark.parametrize('fault',['missing','relative','symlink','parent_symlink','writable','directory','fifo','empty','invalid','large'])
def test_untrusted_ca_files_are_refused_without_driver(tls_values,tmp_path,fault):
    p=Path(tls_values['DATABASE_SSLROOTCERT_FILE'])
    if fault=='missing': p=p.with_name('absent')
    elif fault=='relative': p=Path('relative.crt')
    elif fault=='symlink':
        q=p.with_name('link');q.symlink_to(p);p=q
    elif fault=='parent_symlink':
        q=tmp_path/'dir-link';q.symlink_to(tmp_path,target_is_directory=True);p=q/p.name
    elif fault=='writable': p.chmod(0o664)
    elif fault=='directory': p=tmp_path
    elif fault=='fifo':
        import os
        p=tmp_path/'fifo';os.mkfifo(p,0o600)
    else:
        p.chmod(0o600);p.write_bytes({'empty':b'','invalid':b'not a CA','large':b'x'*1048577}[fault])
    with pytest.raises(InvalidTLS) as failure:
        PostgresTLS.from_mapping(tls_values|{'DATABASE_SSLROOTCERT_FILE':str(p)})
    assert failure.value.__context__ is None
    assert str(p) not in str(failure.value)


def test_tls_reaches_final_driver_and_auth_inventory_share_lazy_sessions(tls_configuration,monkeypatch):
    path,values=tls_configuration
    for name,value in {'PGSSLMODE':'disable','PGSSLROOTCERT':'untrusted','PGGSSENCMODE':'require'}.items():
        monkeypatch.setenv(name,value)
    engine=Mock();make_engine=Mock(return_value=engine);session=Mock()
    monkeypatch.setattr('app.dedicated.create_engine',make_engine)
    monkeypatch.setattr('app.dedicated.create_session_factory',Mock(return_value=Mock(return_value=session)))
    app=dedicated_wsgi.create_tls_app(str(path));make_engine.assert_not_called()
    runtime=app.extensions['security'];inventory=app.extensions['inventory']
    assert runtime.service(runtime.policy()).sessions==inventory.open_session
    assert inventory.open_session() is session
    args,params=PGDialect_psycopg().create_connect_args(make_engine.call_args.args[0])
    assert args==[]
    assert params['sslmode']=='verify-full' and params['sslrootcert']==values['DATABASE_SSLROOTCERT_FILE']
    assert params['gssencmode']=='disable' and params['connect_timeout']=='2'
    assert params['host']==values['DATABASE_HOST'] and params['user']==values['DATABASE_USER']
    assert make_engine.call_args.kwargs=={'pool_pre_ping':True,'hide_parameters':True,'echo':False}


def test_ca_is_revalidated_before_session_not_only_at_startup(tls_configuration,monkeypatch):
    path,values=tls_configuration
    app=dedicated_wsgi.create_tls_app(str(path))
    Path(values['DATABASE_SSLROOTCERT_FILE']).chmod(0o666)
    with pytest.raises(InvalidTLS): app.extensions['inventory'].open_session()


def test_duplicate_tls_key_is_not_accepted(tls_configuration):
    path,values=tls_configuration
    path.write_text(json.dumps(values)[:-1]+',"DATABASE_SSLMODE":"disable"}')
    with pytest.raises(ConfigurationError): dedicated_wsgi.create_tls_app(str(path))


def test_arbitrary_transport_callback_is_not_a_configuration_escape(configuration):
    with pytest.raises(ConfigurationError): create_dedicated_app(configuration[1],database_tls=Mock())
