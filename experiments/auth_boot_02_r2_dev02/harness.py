import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid

import psycopg
from psycopg import sql

from laboratory import Laboratory, REF_SCHEMA


BIN = Path('/usr/lib/postgresql/16/bin')


class Cluster:
    def __init__(self, root, name):
        self.root = root / name
        self.root.mkdir(mode=0o700)
        self.data = self.root / 'data'
        self.socket = self.root / 'socket'
        self.socket.mkdir(mode=0o700)
        self.started = False
        self.command('initdb', '-D', str(self.data), '--no-locale', '--encoding=UTF8',
                     '--auth-local=peer', '--auth-host=reject')
        with (self.data / 'postgresql.conf').open('a') as config:
            config.write("\nlisten_addresses=''\nunix_socket_directories='" + str(self.socket)
                         + "'\nunix_socket_permissions=0700\nfsync=on\nsynchronous_commit=on"
                         + "\nfull_page_writes=on\nmax_connections=80\n")
        try:
            self.start()
        except BaseException:
            subprocess.run([str(BIN / 'pg_ctl'), '-D', str(self.data), '-m', 'fast', '-w', 'stop'],
                           capture_output=True)
            raise

    def command(self, name, *arguments):
        return subprocess.run([str(BIN / name), *arguments], check=True,
                              capture_output=True, text=True).stdout

    def dsn(self, database='postgres'):
        return psycopg.conninfo.make_conninfo(host=str(self.socket), dbname=database,
                                            user=os.environ['USER'], connect_timeout=2)

    def start(self):
        self.command('pg_ctl', '-D', str(self.data), '-l', str(self.root / 'server.log'), '-w', 'start')
        self.started = True

    def stop(self, mode='fast'):
        if self.started:
            self.command('pg_ctl', '-D', str(self.data), '-m', mode, '-w', 'stop')
            self.started = False

    def database(self):
        name = 'lab_' + uuid.uuid4().hex
        with psycopg.connect(self.dsn(), autocommit=True) as connection:
            connection.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
        return self.dsn(name)

    def dump(self, dsn):
        return self.command('pg_dump', '--dbname', dsn, '--no-owner', '--no-privileges')

    def restore(self, dump):
        dsn = self.database()
        subprocess.run([str(BIN / 'psql'), '-X', '-v', 'ON_ERROR_STOP=1', '--dbname', dsn],
                       input=dump, text=True, capture_output=True, check=True)
        return dsn


class Harness:
    def __init__(self):
        self.root = Path(tempfile.mkdtemp(prefix='ln-r2d02-')).resolve()
        self.clusters = []
        self.cleaned = False
        try:
            self.authority = Cluster(self.root, 'authority')
            self.clusters.append(self.authority)
            self.reference = Cluster(self.root, 'reference')
            self.clusters.append(self.reference)
            self.reference_dsn = self.reference.database()
            with psycopg.connect(self.reference_dsn) as connection:
                connection.execute(REF_SCHEMA)
        except BaseException:
            self.close()
            raise

    def laboratory(self):
        lab = Laboratory(self.authority.database(), self.reference_dsn, uuid.uuid4().hex)
        lab.bootstrap()
        return lab

    def clone(self, lab, dump=None):
        return Laboratory(self.authority.restore(dump if dump is not None else
                          self.authority.dump(lab.authority_dsn)), lab.reference_dsn, lab.namespace)

    def close(self):
        for cluster in reversed(self.clusters):
            cluster.stop()
        if self.root.parent != Path(tempfile.gettempdir()).resolve() or not self.root.name.startswith('ln-r2d02-'):
            raise RuntimeError('cleanup path validation failed')
        shutil.rmtree(self.root)
        self.cleaned = not self.root.exists()
