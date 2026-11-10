"""Real Alembic/PG SQL compilation over a constructed catalog, no PostgreSQL I/O.

The model tests transaction/ledger orchestration, not PG durability or real locks.
Historical refusal tests use the unchanged historical environment entrypoints.
"""
from copy import deepcopy
from pathlib import Path
from threading import Event, Thread
from types import SimpleNamespace
import re

from sqlalchemy.engine.mock import MockConnection
from sqlalchemy.dialects.postgresql import dialect
from sqlalchemy.schema import CreateTable
from sqlalchemy.sql.dml import Insert, Update, Delete
from sqlalchemy.orm import Session
import pytest

from installation import Refused, APPLICATION_TARGET, SECURITY_TARGET
from installation import runner


class Rows:
    def __init__(self, rows=(), rowcount=1):self.rows=list(rows);self.rowcount=rowcount
    def __iter__(self):return iter(self.rows)
    def mappings(self):return self
    def one(self):assert len(self.rows)==1;return self.rows[0]
    def scalar_one(self):
        value=self.one()
        return next(iter(value.values())) if isinstance(value,dict) else value[0] if isinstance(value,tuple) else value
    def scalar_one_or_none(self):return self.scalar_one() if self.rows else None
    def scalars(self):return iter(next(iter(v.values())) if isinstance(v,dict) else v[0] if isinstance(v,tuple) else v for v in self.rows)
    def close(self):pass


class Database:
    def __init__(self):
        self.data=dict(tables=set(),ledgers={},roles=set(),schemas={s:'schema_writer' for s in ('inventory','audit','security','discovery')},grants=False,users={},user_grants=[],resources={})
        self.lock_owner=None;self.active=set();self.next_pid=100
        self.sql=[];self.commit_lost=False;self.fail_ddl=False;self.elevated=False;self.runtime_ddl=False
        self.entered=Event();self.release=Event();self.pause=False
    def connect(self,role):return Connection(self,role)


class Transaction:
    def __init__(self,conn):self.conn=conn;self.is_active=True
    def rollback(self):self.is_active=False;self.conn.tx=None;self.conn.working=deepcopy(self.conn.db.data)
    def commit(self):
        self.conn.db.data=deepcopy(self.conn.working);self.is_active=False;self.conn.tx=None
        if self.conn.db.commit_lost:raise OSError('CONSTRUCTED secret driver diagnostic')


class Connection(MockConnection):
    def __init__(self,db,role):
        self.db,self.role=db,role;self.tx=None;self.closed=False
        self.pid=db.next_pid;db.next_pid+=1;db.active.add(self.pid)
        self.working=deepcopy(db.data)
        pg=dialect();pg.has_table=lambda connection,name,schema=None,**kw:(schema or 'public',name) in self.working['tables']
        super().__init__(pg,self.dispatch)
        self.echo=False;self.hide_parameters=True
        self.connection=SimpleNamespace(driver_connection=SimpleNamespace(autocommit=False))
    def begin(self):assert self.tx is None;self.tx=Transaction(self);return self.tx
    def in_transaction(self):return self.tx is not None and self.tx.is_active
    def get_transaction(self):return self.tx
    def rollback(self):
        if self.tx:self.tx.rollback()
    def close(self):
        self.rollback();self.closed=True;self.db.active.discard(self.pid)
        if self.db.lock_owner==self.pid:self.db.lock_owner=None
    def get_execution_options(self):return {}
    def exec_driver_sql(self,sql,**kwargs):return self.dispatch(sql)
    def dispatch(self,statement,parameters=None,*args,**kwargs):
        if not self.in_transaction():self.begin()
        sql=str(statement.compile(dialect=self.dialect)) if hasattr(statement,'compile') else str(statement)
        values=dict(parameters or {})
        self.db.sql.append(sql)
        if sql.startswith('CREATE ROLE '):
            self.working['roles'].add(sql.split()[2]);return Rows()
        if sql.startswith('ALTER SCHEMA '):
            self.working['schemas'][sql.split()[2]]=sql.split()[-1];return Rows()
        if sql.startswith('CREATE SCHEMA discovery AUTHORIZATION '):
            self.working['schemas']['discovery']=sql.split()[-1];return Rows()
        if "SELECT json_build_object('owner',pg_catalog.pg_get_userbyid(nspowner)" in sql:
            owner=self.working['schemas'].get('discovery');return Rows([(dict(owner=owner,public_acl=False),)] if owner else [])
        if sql.startswith('GRANT '):
            if ' ON TABLE ' in sql:self.working['grants']=True
            return Rows()
        if 'SELECT rolname AS name' in sql:return Rows([dict(name=name) for name in sorted(self.working['roles'])])
        if 'SELECT count(*) FROM security.local_users' in sql:
            users=self.working['users']
            if 'id' in values:
                user=users.get(values['id']);return Rows([(int(user is not None and user.login==values['login'] and user.status=='active'),)])
            return Rows([(len(users),)])
        if 'SELECT count(*) FROM security.global_role_grants' in sql:
            return Rows([(sum(str(g.user_id)==values['id'] for g in self.working['user_grants']),)])
        if 'SELECT count(*) FROM inventory.resources' in sql:return Rows([(int(values['id'] in self.working['resources']),)])
        if 'n.nspname AS name,r.rolname AS owner' in sql:
            return Rows([dict(name=name,owner=owner) for name,owner in self.working['schemas'].items()])
        if 'has_table_privilege' in sql and ' AS resources_read' in sql:
            names=re.findall(r' AS ([a-z_]+)',sql)
            return Rows([{name:self.working['grants'] for name in names}])
        if 'current_database() AS database' in sql:
            return Rows([dict(database='product_dev',principal=self.role,effective_principal=self.role,sid='123',pid=self.pid,started='fixed',version=160015)])
        if 'pg_try_advisory_lock' in sql:
            allowed=self.db.lock_owner in (None,self.pid)
            if allowed:self.db.lock_owner=self.pid
            return Rows([(allowed,)])
        if 'pg_advisory_unlock' in sql:self.db.lock_owner=None;return Rows([(True,)])
        if 'pg_export_snapshot' in sql:return Rows([('constructed-snapshot',)])
        if "locktype='advisory'" in sql:return Rows([(self.db.lock_owner==self.pid,)])
        if 'AS elevated' in sql:
            return Rows([dict(elevated=self.db.elevated if 'WHERE r.rolname=current_user' in sql else False,
                database_power=False,memberships=False,**(dict(ddl=self.db.runtime_ddl,ownership=False) if ':runtime' in str(statement) else {}))])
        if 'SELECT c.relkind' in sql:
            name=values['name'];return Rows([('r',)] if ('public',name) in self.working['tables'] else [])
        if sql.startswith('SELECT version_num FROM public.') or 'SELECT public.alembic' in sql:
            table=sql.split('public.')[1].split()[0].split('.')[0]
            value=self.working['ledgers'].get(table)
            return Rows([] if value is None else [(value,)])
        if 'AS schema,c.relname AS name' in sql:
            return Rows([dict(schema=s,name=n) for s,n in sorted(self.working['tables']) if s!='public'])
        if 'FROM pg_catalog.pg_extension' in sql:return Rows([('public',)])
        if 'has_schema_privilege' in sql:return Rows([(True,)])
        if 'FROM pg_catalog.pg_stat_activity WHERE pid=' in sql:
            return Rows([(int(values['pid'] in self.db.active),)])
        if isinstance(statement,CreateTable):
            if self.db.pause:
                self.db.entered.set();assert self.db.release.wait(10)
            if self.db.fail_ddl:raise RuntimeError('CONSTRUCTED DDL failure with secret SQL')
            table=statement.element;self.working['tables'].add((table.schema or 'public',table.name))
            return Rows()
        if isinstance(statement,(Insert,Update,Delete)) and statement.table.name.startswith('alembic_'):
            params=statement.compile(dialect=self.dialect).params
            literal=re.search(r"(?:VALUES \(|SET version_num=)'([a-z0-9]+)'",sql)
            self.working['ledgers'][statement.table.name]=params.get('version_num') or (literal.group(1) if literal else None)
            return Rows()
        return Rows()


def settings(tmp_path,db):
    return SimpleNamespace(values=dict(database=dict(name='product_dev',system_identifier='123'),
        roles=dict(admin='bootstrap',migrator='schema_writer',runtime='app_reader'),state_dir=str(tmp_path/'state')),
        connect=lambda role:db.connect(dict(admin='bootstrap',migrator='schema_writer',runtime='app_reader')[role]))


def test_real_migrations_both_chains_positive(tmp_path):
    db=Database();config=settings(tmp_path,db)
    result=runner.migrate(config,expected_application='base',expected_security='base')
    assert result['state']=='CONFIRMED'
    assert db.data['ledgers']==dict(alembic_version=APPLICATION_TARGET,alembic_security_version=SECURITY_TARGET)
    assert ('inventory','resources') in db.data['tables'] and ('security','local_users') in db.data['tables']
    assert ('security','authorization_integrity_anchors') not in db.data['tables']
    assert any('EXCLUDE USING gist' in sql for sql in db.sql)
    assert any('CREATE TRIGGER trg_audit_events_immutable' in sql for sql in db.sql)
    assert not runner.Journal(config).marker.exists() and not db.active and db.lock_owner is None


@pytest.mark.parametrize('fault',['database','sid','revision','migrator_power','runtime_power'])
def test_wrong_destination_revision_and_privilege_separation(tmp_path,fault):
    db=Database();config=settings(tmp_path,db)
    if fault=='database':config.values['database']['name']='elsewhere'
    if fault=='sid':config.values['database']['system_identifier']='456'
    if fault=='migrator_power':db.elevated=True
    if fault=='runtime_power':db.runtime_ddl=True
    source=APPLICATION_TARGET if fault=='revision' else 'base'
    with pytest.raises(Refused):runner.migrate(config,expected_application=source,expected_security='base')
    assert not db.data['tables'] and not any(sql.startswith('CREATE') for sql in db.sql)
    assert not db.active


def test_ddl_failure_rolls_back_and_requires_explicit_reconciliation(tmp_path):
    db=Database();db.fail_ddl=True;config=settings(tmp_path,db)
    with pytest.raises(RuntimeError):runner.migrate(config,expected_application='base',expected_security='base')
    assert not db.data['tables'] and runner.Journal(config).marker.exists() and not db.active
    with pytest.raises(Refused,match='RECONCILE'):runner.migrate(config,expected_application='base',expected_security='base')
    db.fail_ddl=False
    result=runner.reconcile(config)
    assert result['state']=='RECONCILED_ROLLED_BACK' and not runner.Journal(config).marker.exists()


def test_lost_commit_response_reconciles_without_migrating_again(tmp_path):
    db=Database();db.commit_lost=True;config=settings(tmp_path,db)
    with pytest.raises(OSError):runner.migrate(config,expected_application='base',expected_security='base')
    assert db.data['ledgers']['alembic_security_version']==SECURITY_TARGET
    assert runner.Journal(config).marker.exists() and not db.active
    created=sum(sql.startswith('CREATE') for sql in db.sql)
    db.commit_lost=False
    result=runner.reconcile(config)
    assert result['state']=='RECONCILED_COMMITTED'
    assert sum(sql.startswith('CREATE') for sql in db.sql)==created


def test_concurrent_installers_on_different_clients_refuse(tmp_path):
    db=Database();db.pause=True;first=settings(tmp_path/'client1',db);second=settings(tmp_path/'client2',db)
    errors=[]
    def work():
        try:runner.migrate(first,expected_application='base',expected_security='base')
        except BaseException as exc:errors.append(exc)
    worker=Thread(target=work);worker.start();assert db.entered.wait(10)
    try:
        with pytest.raises(Refused,match='CONCURRENT'):runner.migrate(second,expected_application='base',expected_security='base')
    finally:db.release.set();worker.join(10)
    assert not errors and not worker.is_alive()


def test_historical_entry_still_requires_actual_prepared_context():
    from migrations.dev09b_prerequisites import require_prepared_environment,MissingParameter
    from installation import STANDARD_ATTR
    cfg=SimpleNamespace(attributes=dict(connection=SimpleNamespace(in_transaction=lambda:True,dialect=SimpleNamespace(name='postgresql')),
        **{STANDARD_ATTR:object()}))
    with pytest.raises(MissingParameter):require_prepared_environment(cfg)


def test_mixed_standard_historical_context_is_never_admitted(monkeypatch):
    from migrations import dev09b_prerequisites as h
    from alembic import op
    from installation import STANDARD_ATTR
    cfg=SimpleNamespace(attributes={STANDARD_ATTR:object(),h.ATTR:object()})
    monkeypatch.setattr(op,'get_context',lambda:SimpleNamespace(config=cfg))
    with pytest.raises(h.PrerequisiteRefused,match='Mixed'):h.require_prepared_schema('inventory')


def test_admin_provision_migrate_and_minimum_runtime_grants(tmp_path):
    from installation.admin import provision,grants,RUNTIME_GRANTS
    db=Database();config=settings(tmp_path,db)
    for schema in db.data['schemas']:db.data['schemas'][schema]='previous_owner'
    for role in ('migrator','runtime'):
        path=tmp_path/(role+'_password');path.write_text('synthetic_random_database_password_00000000000000000');path.chmod(0o600)
        config.values.setdefault('password_files',{})[role]=str(path)
    assert provision(config)['state']=='CONFIRMED'
    assert db.data['roles']=={'schema_writer','app_reader'}
    assert all(owner=='schema_writer' for owner in db.data['schemas'].values())
    assert runner.migrate(config,expected_application='base',expected_security='base')['state']=='CONFIRMED'
    assert grants(config)['state']=='CONFIRMED'
    assert any('UPDATE(updated_at)' in sql for sql in RUNTIME_GRANTS)
    assert any('UPDATE(resource_type,display_name,description,administrative_state,updated_at,row_version) ON TABLE inventory.resources' in sql for sql in RUNTIME_GRANTS)
    assert not any('ALL TABLES' in sql or 'PASSWORD' in sql or 'UPDATE ON' in sql for sql in RUNTIME_GRANTS)
    assert not any('synthetic_random_database_password' in sql for sql in db.sql)


@pytest.mark.parametrize('lost',[False,True])
def test_initial_account_hash_seed_and_uncertain_reconciliation(tmp_path,monkeypatch,lost):
    from installation import admin
    from app.security.models import LocalUser,GlobalRoleGrant
    from app.inventory.models import Resource
    from app.security.service import verify_password
    db=Database();config=settings(tmp_path,db)
    runner.migrate(config,expected_application='base',expected_security='base')
    # Model only ORM writes; real models/hash/journal/transactions/reconciliation.
    class ModelSession(Session):
        def __init__(self,bind,**kwargs):super().__init__();self.conn=bind
        def add(self,value):
            if isinstance(value,LocalUser):self.conn.working['users'][str(value.id)]=value
            elif isinstance(value,GlobalRoleGrant):self.conn.working['user_grants'].append(value)
            elif isinstance(value,Resource):self.conn.working['resources'][str(value.id)]=value
        def flush(self):pass
        def close(self):pass
    monkeypatch.setattr(admin,'Session',ModelSession)
    db.commit_lost=lost
    if lost:
        with pytest.raises(OSError):admin.initial_user(config,'operator','constructed-strong-password',resource_name='Minimum DEV resource')
        db.commit_lost=False
        assert runner.reconcile(config)['state']=='RECONCILED_COMMITTED'
    else:assert admin.initial_user(config,'operator','constructed-strong-password',resource_name='Minimum DEV resource')['state']=='CONFIRMED'
    user=next(iter(db.data['users'].values()))
    assert verify_password(user.password_hash,'constructed-strong-password')
    assert len(db.data['resources'])==1 and len(db.data['user_grants'])==2
    for path in Path(config.values['state_dir']).glob('*.json'):
        assert 'constructed-strong-password' not in path.read_text() and user.password_hash not in path.read_text()
    with pytest.raises(Refused,match='ALREADY_EXISTS'):admin.initial_user(config,'another','constructed-strong-password')


@pytest.mark.parametrize('failure',[False,True])
def test_proportional_backup_uses_private_pgpass_not_password_argv(tmp_path,monkeypatch,failure):
    from installation import admin
    import subprocess,os
    db=Database();config=settings(tmp_path,db)
    config.values['database'].update(host='127.0.0.1',port=5432,sslmode='disable')
    password=tmp_path/'admin_password';password.write_text('constructed:password\\value');password.chmod(0o600)
    config.values['password_files']=dict(admin=str(password))
    monkeypatch.setenv('PGPASSWORD','unrelated-constructed-value')
    monkeypatch.setattr('shutil.which',lambda name:'/usr/bin/pg_dump')
    def dump(argv,**kwargs):
        pgpass=Path(kwargs['env']['PGPASSFILE'])
        assert pgpass.stat().st_mode & 0o777==0o600
        assert 'PGPASSWORD' not in kwargs['env'] and password.read_text() not in str(argv)
        assert argv[-2:]==['--snapshot','constructed-snapshot']
        kwargs['stdout'].write(b'CONSTRUCTED DUMP BYTES')
        return SimpleNamespace(returncode=1 if failure else 0)
    monkeypatch.setattr(subprocess,'run',dump)
    output=tmp_path/'backups'/'before.dump'
    if failure:
        with pytest.raises(Refused,match='BACKUP_FAILED'):admin.backup(config,output)
        assert not output.exists()
    else:
        assert admin.backup(config,output)['state']=='BACKUP_SAVED'
        assert output.stat().st_mode & 0o777==0o600
        assert output.read_bytes()==b'CONSTRUCTED DUMP BYTES'
    assert not db.active and db.lock_owner is None


def old_standard_database(tmp_path):
    db=Database();config=settings(tmp_path,db)
    runner.migrate(config,expected_application='base',expected_security='base')
    db.data['ledgers']['alembic_version']='f066a01a7230'
    db.data['tables']={t for t in db.data['tables'] if t[0]!='discovery'}
    del db.data['schemas']['discovery']
    return db,config


def test_discovery_preparation_and_existing_f066_upgrade(tmp_path):
    from installation.admin import prepare_discovery
    db,config=old_standard_database(tmp_path)
    assert prepare_discovery(config)['state']=='CONFIRMED'
    result=runner.migrate(config,expected_application='f066a01a7230',expected_security=SECURITY_TARGET,chain='application')
    assert result['revisions']==dict(application=APPLICATION_TARGET,security=SECURITY_TARGET)
    assert {('discovery',name) for name in ('jobs','observations','decisions')}<=db.data['tables']
    assert not any('authorization_integrity_anchors' in str(t) for t in db.data['tables'])
    assert any('trg_discovery_immutable' in sql for sql in db.sql)


def test_discovery_migration_failure_preserves_old_revision_and_catalog(tmp_path):
    from installation.admin import prepare_discovery
    db,config=old_standard_database(tmp_path);prepare_discovery(config)
    before=deepcopy(db.data);db.fail_ddl=True
    with pytest.raises(Exception):runner.migrate(config,expected_application='f066a01a7230',expected_security=SECURITY_TARGET,chain='application')
    assert db.data==before
    assert runner.reconcile(config)['state']=='RECONCILED_ROLLED_BACK'
