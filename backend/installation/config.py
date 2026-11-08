"""Environment configuration and private secret files; no connection on import."""
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re

from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.pool import NullPool

from app.dedicated import _database_host, _secret, _check_libpq_environment
from app.security.policy import origin_of
from installation import require, Refused


@dataclass(frozen=True, repr=False)
class Settings:
    values: dict

    @classmethod
    def load(cls, path):
        def pairs(items):
            result = {}
            for key, value in items:
                require(key not in result, 'DUPLICATE_CONFIGURATION_KEY')
                result[key] = value
            return result
        try:
            value = json.loads(Path(path).read_text(), object_pairs_hook=pairs)
            return cls.from_mapping(value)
        except Refused:
            raise
        except (OSError, ValueError, TypeError, KeyError):
            raise Refused('INVALID_CONFIGURATION') from None

    @classmethod
    def from_mapping(cls,value):
        try:
            require(set(value) == {'version','environment','database','roles','password_files',
                'state_dir','https','csrf_key_file','frontend_dist'}, 'CONFIGURATION_FIELDS')
            require(type(value['version']) is int and value['version'] == 1, 'CONFIGURATION_VERSION')
            require(value['environment'] in {'DEV','STAGING','PROD'}, 'ENVIRONMENT')
            db = value['database']
            require(set(db) == {'host','port','name','system_identifier','sslmode','ca_file'}, 'DATABASE_FIELDS')
            _database_host(db['host'])
            require(type(db['port']) is int and 1 <= db['port'] <= 65535, 'DATABASE_PORT')
            for name in [db['name'], *value['roles'].values()]:
                require(type(name) is str and re.fullmatch('[a-z_][a-z0-9_]{0,62}', name), 'DATABASE_IDENTIFIER')
            require(set(value['roles']) == set(value['password_files']) == {'admin','migrator','runtime'}, 'ROLE_FIELDS')
            require(len(set(value['roles'].values())) == 3, 'SEPARATE_DATABASE_ROLES_REQUIRED')
            require(db['sslmode'] in {'disable','verify-full'}, 'DATABASE_TLS')
            require(value['environment'] == 'DEV' or db['sslmode'] == 'verify-full', 'DATABASE_TLS_REQUIRED')
            require(db['system_identifier'] is None or re.fullmatch('[1-9][0-9]{0,19}', db['system_identifier']), 'SYSTEM_IDENTIFIER')
            require(origin_of(value['https']['origin']) is not None, 'HTTPS_ORIGIN')
            require(set(value['https']) == {'origin','bind','port','certificate','key'}, 'HTTPS_FIELDS')
            _database_host(value['https']['bind'])
            require(type(value['https']['port']) is int and 1 <= value['https']['port'] <= 65535, 'HTTPS_PORT')
            paths = [value['state_dir'], value['csrf_key_file'], value['frontend_dist'],
                value['https']['certificate'], value['https']['key'], *value['password_files'].values()]
            if db['sslmode'] == 'verify-full': paths.append(db['ca_file'])
            require(all(type(p) is str and Path(p).is_absolute() for p in paths), 'ABSOLUTE_PATHS_REQUIRED')
            source_root=Path(__file__).resolve().parents[2]
            for path in [value['state_dir'],value['csrf_key_file'],value['https']['key'],*value['password_files'].values()]:
                location=Path(path).resolve()
                require(location!=source_root and source_root not in location.parents,'SECRETS_OUTSIDE_SOURCE_REQUIRED')
            return cls(value)
        except Refused:
            raise
        except (OSError, ValueError, TypeError, KeyError):
            raise Refused('INVALID_CONFIGURATION') from None

    def connect(self, role):
        """One connection, no pool reconnect/retry or implicit DB fallback."""
        require(role in self.values['roles'], 'UNKNOWN_ROLE')
        _check_libpq_environment()
        db = self.values['database']
        options = dict(sslmode='disable', gssencmode='disable', connect_timeout='5')
        if db['sslmode'] == 'verify-full':
            from app.postgres_tls import PostgresTLS
            options = PostgresTLS(db['ca_file']).query()
        url = URL.create('postgresql+psycopg', username=self.values['roles'][role],
            password=_secret(self.values['password_files'][role]), host=db['host'], port=db['port'],
            database=db['name'], query=options)
        engine = create_engine(url, poolclass=NullPool, echo=False, hide_parameters=True,
            connect_args={'options':'-c search_path=pg_catalog,public -c statement_timeout=30000 -c lock_timeout=5000 -c idle_in_transaction_session_timeout=60000'})
        try:
            connection = engine.connect()
        except BaseException:
            engine.dispose()
            raise
        return connection  # NullPool closes the DBAPI connection on close().


def private_directory(path):
    path = Path(path)
    require(path.is_absolute() and not any(p.is_symlink() for p in (path,*path.parents)), 'PRIVATE_DIRECTORY')
    path.mkdir(parents=True, mode=0o700, exist_ok=True)
    info = path.stat()
    require(info.st_uid == os.getuid() and info.st_mode & 0o777 == 0o700, 'PRIVATE_DIRECTORY')
    return path
