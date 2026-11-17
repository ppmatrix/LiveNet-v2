"""A volatile, one-use grant and a durable pre-effect record per attempt."""
from threading import Event, RLock
import hashlib
import json
from uuid import UUID

from .journal import JournalError
from .service import Problem


class Coordinator:
    def __init__(self, repository, policy, journal):
        self.repository, self.policy, self.journal = repository, policy, journal
        self.lock = RLock()
        self.state, self.reason = 'STARTING', 'initializing'
        self.lease = None
        self.grants = set()
        self.cancel = Event()
        self.stop = Event()
        self.active_attempt = None

    def public(self):
        with self.lock:
            if self.stop.is_set() and self.state == 'READY':
                return dict(state='BLOCKED', reason='shutting_down')
            return dict(state=self.state, reason=self.reason)

    def block(self, reason='persistence_uncertain'):
        # Cancel first, before waiting for an executor or another transaction.
        self.cancel.set()
        with self.lock:
            self.state, self.reason = 'BLOCKED', reason
            self.grants.clear()

    def initialize(self, lease):
        with self.lock:
            try:
                if self.journal is None:
                    raise JournalError('journal_unavailable')
                self.lease = lease
                self.journal.acquire()
                if self.journal.read('attempt') or self.journal.read('recovery'):
                    raise JournalError('recovery_required')
                self.repository.bootstrap(self, lease)
                self.journal.establish_owner()
                self.state, self.reason = 'READY', None
            except BaseException as error:
                self.block(str(error) if isinstance(error, JournalError) else 'persistence_uncertain')
                raise

    def require_ready(self):
        if self.state != 'READY' or self.cancel.is_set() or self.stop.is_set() or self.lease is None:
            raise Problem(503, 'discovery_not_ready')

    def submit(self, target, identity):
        with self.lock:
            self.require_ready()
            self.policy.targets(target)  # Validation failure is not persistence uncertainty.
            try:
                self.repository.prune_grants(self.grants,self.lease)
                result = self.repository.enqueue(self.policy, target, identity, lease=self.lease)
                # Independent read confirms the durable row before publication.
                self.repository.confirm_admission(UUID(result['id']), self.policy, self.lease)
                self.grants.add(UUID(result['id']))
                return result
            except Problem:
                raise
            except BaseException:
                self.block()
                raise

    def begin_attempt(self, identifier):
        self.require_ready()
        if identifier not in self.grants:
            self.block('state_inconsistent')
            raise Problem(503, 'discovery_not_ready')
        # Consume before the claim; a failed claim never restores this grant.
        self.grants.remove(identifier)
        if self.journal.read('attempt') is not None:
            raise JournalError('recovery_required')
        self.active_attempt=self.journal.write('attempt', job_id=str(identifier),
                           policy_sha256=hashlib.sha256(json.dumps(self.policy.snapshot(),sort_keys=True).encode()).hexdigest())

    def network_allowed(self,identifier):
        if self.cancel.is_set() or self.stop.is_set() or self.state!='READY':return False
        try:
            record=self.journal.read('attempt')
            if (record is None or record!=self.active_attempt or record.get('job_id')!=str(identifier)
                    or record['owner']!=self.journal.identity):
                raise JournalError('journal_corrupt')
            return True
        except JournalError as error:
            self.block(str(error));return False

    def complete_attempt(self, identifier):
        if self.cancel.is_set() or self.state != 'READY':
            raise JournalError(self.reason or 'state_inconsistent')
        record = self.journal.read('attempt')
        if record is None or record.get('job_id') != str(identifier) or record['owner'] != self.journal.identity:
            raise JournalError('journal_corrupt')
        self.repository.confirm_terminal(identifier, self.lease)
        if self.cancel.is_set():
            raise JournalError(self.reason or 'state_inconsistent')
        self.journal.archive('attempt')
        self.active_attempt=None

    def close(self):
        self.block('shutting_down' if self.state != 'BLOCKED' else self.reason)
        if self.journal is not None:
            self.journal.release()
