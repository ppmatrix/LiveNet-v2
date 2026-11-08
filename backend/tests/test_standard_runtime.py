"""Standard origin/configuration and real login/Inventory services over test store."""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from installation.config import Settings
from installation import Refused
from installation.runtime import create_standard_app,runtime_connection
from installation.__main__ import main
from app.security.models import LocalUser,GlobalRoleGrant
from app.security.service import hash_password
from security_doubles import OfflineStore


def configuration(tmp_path):
    root=tmp_path/'private';root.mkdir(mode=0o700)
    for name in ('csrf','admin','migrator','runtime'):
        path=root/name;path.write_text('constructed_test_value_00000000000000000000000000');path.chmod(0o600)
    dist=tmp_path/'dist';dist.mkdir();(dist/'index.html').write_text('<html>Existing frontend fixture</html>')
    value=dict(version=1,environment='DEV',database=dict(host='127.0.0.1',port=5432,name='portable_dev',
        system_identifier='123',sslmode='disable',ca_file=None),roles=dict(admin='bootstrap',migrator='schema_writer',runtime='app_reader'),
        password_files={name:str(root/name) for name in ('admin','migrator','runtime')},state_dir=str(root/'operations'),
        csrf_key_file=str(root/'csrf'),frontend_dist=str(dist),
        https=dict(origin='https://product.test:9443',bind='127.0.0.1',port=9443,certificate=str(root/'server.crt'),key=str(root/'server.key')))
    path=root/'installation.json';path.write_text(json.dumps(value))
    return path,value


def test_login_and_inventory_persist_between_app_instances_without_machine_credentials(tmp_path):
    path,_=configuration(tmp_path);store=OfflineStore()
    user=LocalUser(id=uuid4(),login='operator',password_hash=hash_password('constructed-password-for-tests'),status='active')
    store.users[user.id]=user
    store.grants.append(GlobalRoleGrant(user_id=user.id,role='inventory_editor',scope_type='global',scope_id=None))
    def app():
        value=create_standard_app(path)
        value.extensions['inventory']._session_factory=store.factory
        value.extensions['security']._sessions=store.factory
        return value
    instance=app();client=instance.test_client();base='https://product.test:9443'
    assert instance.debug is False
    assert client.get('/api/v1/inventory/resources',base_url=base).status_code==401
    csrf=client.get('/api/v1/auth/csrf',base_url=base).json['csrf_token']
    response=client.post('/api/v1/auth/login',base_url=base,headers={'Origin':base,'X-CSRF-Token':csrf},
        json=dict(login='operator',password='constructed-password-for-tests'))
    assert response.status_code==200 and 'password' not in response.get_data(as_text=True)
    cookie=client.get_cookie('__Host-livenet_session',domain='product.test')
    csrf=client.get('/api/v1/auth/csrf',base_url=base).json['csrf_token']
    response=client.post('/api/v1/inventory/resources',base_url=base,headers={'Origin':base,'X-CSRF-Token':csrf},
        json=dict(resource_type='virtual_machine',display_name='Machine without credentials'))
    assert response.status_code==201 and len(store.resources)==1
    another=app().test_client();another.set_cookie('__Host-livenet_session',cookie.value,domain='product.test',secure=True)
    response=another.get('/api/v1/inventory/resources',base_url=base)
    assert response.status_code==200 and response.json['total']==1
    assert response.json['items'][0]['display_name']=='Machine without credentials'
    assert 'constructed-password' not in response.get_data(as_text=True)


def test_generic_origin_and_direct_https_transport_guards(tmp_path):
    path,_=configuration(tmp_path);client=create_standard_app(path).test_client()
    assert client.get('/api/v1/auth/csrf',base_url='http://product.test:9443').status_code==403
    assert client.get('/api/v1/auth/csrf',base_url='https://other.test:9443').status_code==403
    assert client.get('/api/v1/auth/csrf',base_url='https://product.test:9443',headers={'X-Forwarded-Proto':'https'}).status_code==403
    assert client.get('/login',base_url='https://product.test:9443').status_code==200


@pytest.mark.parametrize('fault',['same_roles','production_plaintext','inline_secret'])
def test_standard_configuration_refusals(tmp_path,fault):
    path,value=configuration(tmp_path)
    if fault=='same_roles':value['roles']['runtime']=value['roles']['migrator']
    if fault=='production_plaintext':value['environment']='PROD'
    if fault=='inline_secret':value['database']['password']='never accepted'
    path.write_text(json.dumps(value))
    with pytest.raises(Refused):Settings.load(path)


def test_runtime_refuses_a_migration_or_privileged_identity_and_closes():
    conn=Mock();conn.execute.return_value.mappings.return_value.one.return_value=dict(database='portable_dev',
        principal='schema_writer',effective_principal='schema_writer',elevated=False,memberships=False,ddl=True,
        ownership=True,database_power=False)
    settings=SimpleNamespace(values=dict(database=dict(name='portable_dev'),roles=dict(runtime='app_reader')),connect=lambda role:conn)
    with pytest.raises(Refused):runtime_connection(settings)
    conn.close.assert_called_once()


def test_cli_private_config_is_useful_and_does_not_print_generated_secrets(tmp_path,capsys):
    directory=tmp_path/'new-private'
    args=['init-config','--directory',str(directory),'--host','127.0.0.1','--database','portable_dev',
        '--admin-role','bootstrap','--admin-password-file',str(tmp_path/'existing-password'),
        '--frontend-dist',str(tmp_path/'dist'),'--system-identifier','123']
    assert main(args)==0
    output=capsys.readouterr().out
    values=Settings.load(directory/'installation.json').values
    assert values['roles']['runtime']!=values['roles']['migrator']
    for name in ('migrator_password','runtime_password','csrf_key','initial_password'):
        path=directory/name
        assert path.stat().st_mode & 0o777 == 0o600
        assert path.read_text() not in output
    assert main(args)==78  # no overwriting/rotation on repeat
