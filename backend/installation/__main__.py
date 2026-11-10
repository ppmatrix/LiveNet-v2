"""Explicit administrative installer and DEV HTTPS server. No work on import."""
import argparse
import getpass
import json
import logging
import os
from pathlib import Path
import secrets

from app.dedicated import _secret
from installation import Refused,require
from installation.config import Settings,private_directory
from installation.runner import identity,revisions,validate_tables,migrate,reconcile


def init_config(args):
    directory=Path(args.directory).resolve()
    root=Path(__file__).resolve().parents[2]
    require(directory!=root and root not in directory.parents,'SECRETS_OUTSIDE_GIT_REQUIRED')
    directory=private_directory(directory)
    require(not any(directory.iterdir()),'NEW_PRIVATE_DIRECTORY_REQUIRED')
    value=dict(version=1,environment='DEV',
        database=dict(host=args.host,port=args.port,name=args.database,system_identifier=args.system_identifier,sslmode='disable',ca_file=None),
        roles=dict(admin=args.admin_role,migrator=args.migrator_role,runtime=args.runtime_role),
        password_files=dict(admin=str(Path(args.admin_password_file).resolve()),
            migrator=str(directory/'migrator_password'),runtime=str(directory/'runtime_password')),
        state_dir=str(directory/'operations'),csrf_key_file=str(directory/'csrf_key'),
        frontend_dist=str(Path(args.frontend_dist).resolve()),https=dict(origin=args.origin,bind=args.bind,port=args.https_port,
            certificate=str(directory/'server.crt'),key=str(directory/'server.key')))
    path=directory/'installation.json'
    Settings.from_mapping(value)
    for name in ('migrator_password','runtime_password','csrf_key','initial_password'):
        fd=os.open(directory/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'w') as output:output.write(secrets.token_urlsafe(48))
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as output:json.dump(value,output,indent=2);output.write('\n')
    Settings.load(path)
    return dict(state='CONFIGURATION_CREATED',configuration=str(path))


def inspect(settings):
    connection=settings.connect('admin')
    try:
        target=identity(connection,settings,'admin',require_pin=False)
        state=revisions(connection)
        return dict(state='OBSERVED',database=target['database'],system_identifier=target['sid'],
            server_version_num=target['version'],revisions=state)
    finally:connection.close()


def serve(settings,config_file):
    from ipaddress import ip_address
    from werkzeug.serving import run_simple
    from installation.runtime import create_standard_app
    require(settings.values['environment']=='DEV','USE_PRODUCTION_WSGI_SERVER_OUTSIDE_DEV')
    https=settings.values['https'];address=ip_address(https['bind'])
    require((address.is_private or address.is_loopback) and not address.is_unspecified and not address.is_multicast,'INTERNAL_BIND_REQUIRED')
    # Validate the private key file's ownership/mode without returning its bytes.
    _secret(https['key'])
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    run_simple(str(address),https['port'],create_standard_app(config_file),
        ssl_context=(https['certificate'],https['key']),use_debugger=False,use_reloader=False)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    init=commands.add_parser('init-config',help='Create only private configuration/secret files, never a database')
    init.add_argument('--directory',required=True);init.add_argument('--host',required=True)
    init.add_argument('--port',type=int,default=5432);init.add_argument('--database',required=True)
    init.add_argument('--admin-role',required=True);init.add_argument('--admin-password-file',required=True)
    init.add_argument('--migrator-role',default='livenet_migrator');init.add_argument('--runtime-role',default='livenet_runtime')
    init.add_argument('--system-identifier');init.add_argument('--origin',default='https://localhost:8443')
    init.add_argument('--bind',default='127.0.0.1');init.add_argument('--https-port',type=int,default=8443)
    init.add_argument('--frontend-dist',required=True)
    for name in ('inspect','backup','provision','migrate','reconcile','grant-runtime','prepare-discovery','initial-user','install','serve'):
        command=commands.add_parser(name)
        command.add_argument('--config',required=True)
        if name=='backup':command.add_argument('--output',required=True)
        if name=='migrate':
            command.add_argument('--application-from',required=True)
            command.add_argument('--security-from',required=True)
            command.add_argument('--chain',choices=('all','application','security'),default='all')
        if name in {'initial-user','install'}:
            command.add_argument('--login',required=True);command.add_argument('--password-file')
            command.add_argument('--resource-name')
    args=parser.parse_args(argv)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    try:
        if args.command=='init-config':result=init_config(args)
        else:
            settings=Settings.load(args.config)
            if args.command=='inspect':result=inspect(settings)
            elif args.command=='migrate':result=migrate(settings,expected_application=args.application_from,expected_security=args.security_from,chain=args.chain)
            elif args.command=='reconcile':result=reconcile(settings)
            elif args.command=='serve':serve(settings,args.config);return 0
            else:
                from installation.admin import provision,grants,initial_user,backup,prepare_discovery
                if args.command=='backup':result=backup(settings,args.output)
                elif args.command=='provision':result=provision(settings)
                elif args.command=='grant-runtime':result=grants(settings)
                elif args.command=='prepare-discovery':result=prepare_discovery(settings)
                else:
                    if args.password_file:password=_secret(args.password_file)
                    else:
                        password=getpass.getpass('Initial account password: ')
                        require(password==getpass.getpass('Confirm password: '),'PASSWORD_CONFIRMATION_FAILED')
                    if args.command=='install':
                        provisioned=provision(settings)
                        migrated=migrate(settings,expected_application='base',expected_security='base')
                        granted=grants(settings)
                        seeded=initial_user(settings,args.login,password,resource_name=args.resource_name)
                        result=dict(state='CONFIRMED',provision=provisioned,migrate=migrated,runtime=granted,initial_user=seeded)
                    else:result=initial_user(settings,args.login,password,resource_name=args.resource_name)
        print(json.dumps(result,sort_keys=True));return 0
    except BaseException as exc:
        result=dict(state='REFUSED_OR_UNCERTAIN',exception_class=type(exc).__name__)
        if type(exc) is Refused:result['code']=str(exc)
        print(json.dumps(result,sort_keys=True));return 78


if __name__=='__main__':raise SystemExit(main())
