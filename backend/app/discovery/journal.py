"""Private, crash-conservative execution journal. No I/O on import.

Checksums detect accidental corruption, not a malicious process with the same
UID. One flock protects this installation on this host; PostgreSQL still elects
the worker. Archived records are retained rather than deleting evidence.
"""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
from uuid import UUID, uuid4


class JournalError(RuntimeError):
    pass


def instance_identity():
    pid = os.getpid()
    return dict(pid=pid, start_ticks=Path(f'/proc/{pid}/stat').read_text().split(') ', 1)[1].split()[19],
                boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(), instance=str(uuid4()))


def valid_identity(value):
    valid=(isinstance(value, dict) and set(value) == {'pid', 'start_ticks', 'boot_id', 'instance'}
            and type(value['pid']) is int and value['pid'] > 0
            and isinstance(value['start_ticks'], str) and value['start_ticks'].isdigit()
            and all(isinstance(value[k], str) and len(value[k]) == 36 for k in ('boot_id', 'instance')))
    if not valid:return False
    try:
        return all(str(UUID(value[k])) == value[k] for k in ('boot_id', 'instance'))
    except ValueError:return False


def instance_alive(value):
    if not valid_identity(value):
        raise JournalError('journal_corrupt')
    try:
        if value['boot_id'] != Path('/proc/sys/kernel/random/boot_id').read_text().strip():
            return False
        fields = Path(f"/proc/{value['pid']}/stat").read_text().split(') ', 1)[1].split()
        return fields[19] == value['start_ticks'] and fields[0] not in ('Z', 'X')
    except FileNotFoundError:
        return False
    except OSError:
        raise JournalError('previous_instance_unknown') from None


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def valid_uuid(value):
    return isinstance(value, str) and str(UUID(value)) == value


def validate_payload(payload, name, binding):
    """Validate meaning as well as checksum; never trust a partial plan."""
    common = {'version', 'binding', 'kind', 'owner', 'operation_id'}
    extra = {'owner': set(), 'attempt': {'job_id', 'policy_sha256'}, 'recovery': {'plan'}}
    if (name not in extra or set(payload) != common | extra[name]
            or type(payload['version']) is not int or payload['version'] != 1
            or payload['binding'] != binding or payload['kind'] != name
            or not valid_identity(payload['owner']) or not valid_uuid(payload['operation_id'])):
        raise ValueError()
    if name == 'attempt':
        digest = payload['policy_sha256']
        if (not valid_uuid(payload['job_id']) or not isinstance(digest, str)
                or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest)):
            raise ValueError()
    if name == 'recovery':
        plan = payload['plan']
        if (not isinstance(plan, dict) or set(plan) != {'audit_id', 'jobs', 'reason'}
                or not valid_uuid(plan['audit_id']) or not isinstance(plan['jobs'], list)
                or plan['reason'] not in ('operator_reviewed', 'previous_queue_without_execution')):
            raise ValueError()
        seen = set()
        for row in plan['jobs']:
            if (not isinstance(row, dict) or set(row) != {'id', 'before', 'processed', 'observations'}
                    or not valid_uuid(row['id']) or row['id'] in seen
                    or row['before'] not in ('queued', 'running', 'cancelling')
                    or type(row['processed']) is not int or row['processed'] < 0
                    or type(row['observations']) is not int or row['observations'] != row['processed']):
                raise ValueError()
            if plan['reason'] == 'previous_queue_without_execution' and (row['before'] != 'queued' or row['processed']):
                raise ValueError()
            seen.add(row['id'])


class Journal:
    def __init__(self, directory, binding, *, identity=None, alive=instance_alive):
        self.directory = Path(directory)
        self.binding = binding
        self.identity = identity or instance_identity()
        self.alive = alive
        self.fd = None
        self.previous = None

    def _directory(self):
        if not self.directory.is_absolute() or any(p.is_symlink() for p in (self.directory, *self.directory.parents)):
            raise JournalError('journal_unavailable')
        missing = [p for p in (self.directory, *self.directory.parents) if not p.exists()]
        for path in reversed(missing):
            path.mkdir(mode=0o700, exist_ok=True)
            # Persist each newly created directory entry, including state_dir
            # when absent. Fsync of a child alone does not persist its parent.
            fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        info = self.directory.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
            raise JournalError('journal_unavailable')

    @contextmanager
    def _io(self):
        try:
            yield
        except JournalError:
            raise
        except (OSError, ValueError, TypeError, KeyError):
            raise JournalError('journal_unavailable') from None

    def acquire(self):
        with self._io():
            if self.fd is not None:
                raise JournalError('journal_in_use')
            self._directory()
            fd = os.open(self.directory/'lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
            try:
                self._check(fd)
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    raise JournalError('journal_in_use') from None
                self.fd = fd
                owner = self.read('owner')
                self.previous = owner['owner'] if owner else None
                if self.previous and self.alive(self.previous):
                    raise JournalError('previous_instance_alive')
            except BaseException:
                if self.fd == fd:
                    self.fd = None
                os.close(fd)
                raise

    def release(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None

    def _check(self, fd):
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
            raise JournalError('journal_unavailable')

    def _require_lock(self):
        if self.fd is None:
            raise JournalError('journal_unavailable')

    def raw(self, name):
        self._require_lock()
        with self._io():
            try:
                fd = os.open(self.directory/(name+'.json'), os.O_RDONLY | os.O_NOFOLLOW)
            except FileNotFoundError:
                return None
            try:
                self._check(fd)
                if os.fstat(fd).st_size > 65536:
                    raise JournalError('journal_corrupt')
                with os.fdopen(fd, 'rb', closefd=False) as stream:
                    return stream.read(65537)
            finally:
                os.close(fd)

    def read(self, name):
        raw = self.raw(name)
        if raw is None:
            return None
        try:
            def pairs(items):
                result = {}
                for key, value in items:
                    if key in result:
                        raise ValueError()
                    result[key] = value
                return result
            envelope = json.loads(raw, object_pairs_hook=pairs)
            payload = envelope['payload']
            if (set(envelope) != {'payload', 'sha256'} or not isinstance(payload, dict)
                    or envelope['sha256'] != hashlib.sha256(canonical(payload)).hexdigest()
                    ):
                raise ValueError()
            validate_payload(payload, name, self.binding)
            return payload
        except (ValueError, KeyError, TypeError):
            raise JournalError('journal_corrupt') from None

    def sync(self):
        fd = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def write(self, name, **fields):
        self._require_lock()
        payload = dict(version=1, binding=self.binding, kind=name, owner=self.identity,
                       operation_id=str(uuid4()), **fields)
        with self._io():
            validate_payload(payload, name, self.binding)
            data = canonical(dict(payload=payload, sha256=hashlib.sha256(canonical(payload)).hexdigest()))
            if len(data) > 65536:
                raise JournalError('journal_unavailable')
            temp = self.directory/(str(uuid4())+'.tmp')
            fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            try:
                with os.fdopen(fd, 'wb') as output:
                    output.write(data); output.flush(); os.fsync(output.fileno())
                os.replace(temp, self.directory/(name+'.json'))
                self.sync()
            finally:
                temp.unlink(missing_ok=True)
        return payload

    def archive(self, name):
        self._require_lock()
        with self._io():
            path = self.directory/(name+'.json')
            if self.raw(name) is not None:
                os.replace(path, self.directory/(name+'-archived-'+str(uuid4())+'.json'))
                self.sync()

    def establish_owner(self):
        return self.write('owner')
