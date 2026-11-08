"""verify-full PLUS leaf DER SHA256 on the very same psycopg/libpq session.

No extra TLS probe, certificate issuance, network connection on import, library
installation or system-libpq pointer mixing. Native providers are explicitly
pinned and checked with dladdr before accepting any PGconn pointer.
"""
import ctypes as ct
from hashlib import sha256
import os
from pathlib import Path

from . import codec as c


def checked_file(reference):
    c.closed(reference, {'path', 'sha256'})
    path=Path(reference['path']);c.require(path.is_absolute())
    for item in (path,*path.parents):c.require(not item.is_symlink())
    raw=path.read_bytes();c.require(sha256(raw).hexdigest()==reference['sha256'])
    return path


class NativePeerCertificate:
    """OpenSSL provider for the installed psycopg extension, all paths pinned."""
    def __init__(self, providers):
        c.closed(providers, {'extension','libpq','libssl','libcrypto'})
        paths={key:checked_file(value) for key,value in providers.items()}
        import psycopg
        import psycopg_binary.pq
        c.require(Path(psycopg_binary.pq.__file__).resolve()==paths['extension'])
        self.library=ct.CDLL(str(paths['extension']))
        class DlInfo(ct.Structure):
            _fields_=[('name',ct.c_char_p),('base',ct.c_void_p),('symbol',ct.c_char_p),('address',ct.c_void_p)]
        dladdr=ct.CDLL(None).dladdr
        dladdr.argtypes=[ct.c_void_p,ct.POINTER(DlInfo)];dladdr.restype=ct.c_int
        def function(name, provider, args, result):
            method=getattr(self.library,name);info=DlInfo()
            c.require(dladdr(ct.cast(method,ct.c_void_p),ct.byref(info))!=0)
            c.require(Path(os.fsdecode(info.name)).resolve()==paths[provider])
            method.argtypes=args;method.restype=result
            return method
        self.ssl=function('PQsslStruct','libpq',[ct.c_void_p,ct.c_char_p],ct.c_void_p)
        self.peer=function('SSL_get1_peer_certificate','libssl',[ct.c_void_p],ct.c_void_p)
        self.verify=function('SSL_get_verify_result','libssl',[ct.c_void_p],ct.c_long)
        self.encode=function('i2d_X509','libcrypto',[ct.c_void_p,ct.POINTER(ct.POINTER(ct.c_ubyte))],ct.c_int)
        self.free=function('X509_free','libcrypto',[ct.c_void_p],None)

    def der(self, driver):
        c.require(not driver.closed and driver.pgconn.ssl_in_use)
        ssl=self.ssl(driver.pgconn.pgconn_ptr,b'OpenSSL')
        c.require(bool(ssl) and self.verify(ssl)==0)
        cert=self.peer(ssl);c.require(bool(cert))
        try:
            size=self.encode(cert,None);c.require(0<size<=65536)
            output=(ct.c_ubyte*size)();cursor=ct.cast(output,ct.POINTER(ct.c_ubyte))
            c.require(self.encode(cert,ct.byref(cursor))==size)
            return bytes(output)
        finally:self.free(cert)


class PinnedConnections:
    """New unpooled SQLAlchemy connections, fixed role/address/CA/certificate.

    Native pin happens in the creator BEFORE SQLAlchemy's dialect setup SQL.
    Password is read only from the service's private file, never a URL/argv/log.
    """
    def __init__(self, *, endpoint, principal, password_file, native):
        self.endpoint,self.principal,self.password_file,self.native=endpoint,principal,Path(password_file),native
        self.engine=None

    def _driver(self):
        import psycopg
        import stat
        from ipaddress import ip_address
        t=self.endpoint
        try:ip_address(t['host'])
        except (ValueError,TypeError):raise c.Invalid('Single pinned address required') from None
        c.integer(t['port'],1,65535)
        c.digest_text(t['ca_sha256']);c.digest_text(t['server_certificate_sha256'])
        c.require(t['tls_server_name']=='dev09b-querytrial.internal' or t.get('authority') is True)
        checked_file(dict(path=t['ca_file'],sha256=t['ca_sha256']))
        fd=os.open(self.password_file,os.O_RDONLY|os.O_NOFOLLOW)
        with os.fdopen(fd,'rb') as handle:
            info=os.fstat(handle.fileno())
            c.require(info.st_uid==os.geteuid() and stat.S_ISREG(info.st_mode)
                      and stat.S_IMODE(info.st_mode)==0o600 and info.st_nlink==1)
            password=handle.read(4097);c.require(0<len(password)<=4096 and b'\x00' not in password)
        driver=None
        try:
            driver=psycopg.connect(host=t['tls_server_name'],hostaddr=t['host'],port=t['port'],
                dbname=t['database_name'],user=self.principal,password=password.decode().rstrip('\n'),
                sslmode='verify-full',sslrootcert=t['ca_file'],ssl_min_protocol_version='TLSv1.2',
                gssencmode='disable',connect_timeout=5,autocommit=False,
                options='-c search_path=pg_catalog,public -c timezone=UTC -c statement_timeout=5000 -c lock_timeout=1000 -c idle_in_transaction_session_timeout=60000')
            c.require(sha256(self.native.der(driver)).hexdigest()==t['server_certificate_sha256'])
            return driver
        except BaseException:
            if driver is not None:driver.close()
            raise

    def __call__(self):
        from sqlalchemy import create_engine
        from sqlalchemy.pool import NullPool
        if self.engine is None:
            self.engine=create_engine('postgresql+psycopg://',creator=self._driver,
                poolclass=NullPool,echo=False,hide_parameters=True)
        return self.engine.connect()
