"""Explicit PostgreSQL TLS trust for the opt-in DEV-06 factory, no connections.

Only verify-full is accepted. A CA is a trust input, not a password: it may be
readable by others, but must not be writable by group/others or symlinked.
"""
from dataclasses import dataclass
import os
from pathlib import Path
import ssl
import stat


class InvalidTLS(ValueError):
    def __init__(self):
        super().__init__('Invalid PostgreSQL TLS configuration')


@dataclass(frozen=True)
class PostgresTLS:
    root_cert_file: str

    @classmethod
    def from_mapping(cls, values):
        try:
            if (type(values) is not dict or set(values) != {'DATABASE_SSLMODE','DATABASE_SSLROOTCERT_FILE'}
                    or values['DATABASE_SSLMODE'] != 'verify-full'):
                raise ValueError()
            result = cls(values['DATABASE_SSLROOTCERT_FILE'])
            result.query()
            return result
        except (OSError, ValueError, TypeError, UnicodeError, ssl.SSLError):
            pass
        raise InvalidTLS()

    def query(self):
        fd = None
        try:
            path = Path(self.root_cert_file)
            if (not path.is_absolute() or '..' in path.parts
                    or any(p.is_symlink() for p in (path,*path.parents))):
                raise ValueError()
            fd = os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
            info = os.fstat(fd)
            if (not stat.S_ISREG(info.st_mode) or info.st_uid not in (0,os.getuid())
                    or stat.S_IMODE(info.st_mode)&0o022 or not 0 < info.st_size <= 1048576):
                raise ValueError()
            pem = os.read(fd,1048577).decode('ascii')
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.load_verify_locations(cadata=pem)
            # GSS encryption could otherwise take precedence over SSL in libpq.
            return {'sslmode':'verify-full','sslrootcert':str(path),
                    'gssencmode':'disable','connect_timeout':'2'}
        except (OSError, ValueError, TypeError, UnicodeError, ssl.SSLError):
            pass
        finally:
            if fd is not None:
                os.close(fd)
        raise InvalidTLS()
