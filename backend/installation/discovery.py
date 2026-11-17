"""Journal binding and explicit network-free standard Discovery recovery."""
import hashlib
import json
from pathlib import Path

from app.discovery.journal import Journal,JournalError
from app.discovery.service import Repository,LEADER_KEY
from sqlalchemy import text
from sqlalchemy.orm import Session
from installation import Refused


def journal_for(settings):
    binding=hashlib.sha256(json.dumps(dict(database=settings.values['database'],
        runtime=settings.values['roles']['runtime'],state_dir=settings.values['state_dir']),sort_keys=True).encode()).hexdigest()
    return Journal(Path(settings.values['state_dir'])/'discovery',binding)


def recover(settings,*,previous=None):
    # Does not build a Flask app or import/start a Worker. Existing admin identity
    # pin is verified; all mutations are jobs/audit in the selected installation.
    from installation.runner import identity
    connection=settings.connect('admin');journal=journal_for(settings)
    class RecoverySession(Session):
        def __init__(self):
            self.owned=settings.connect('runtime')
            super().__init__(bind=self.owned,expire_on_commit=False,autoflush=False)
        def close(self):
            try:super().close()
            finally:self.owned.close()
    try:
        identity(connection,settings,'admin')
        connection.rollback()
        # Runtime can observe its own leaders; use a runtime election session so
        # the existing restricted role can verify backend_start without grants.
        connection.close();connection=settings.connect('runtime')
        if not connection.execute(text('SELECT pg_try_advisory_lock(:key)'),dict(key=LEADER_KEY)).scalar_one():
            raise JournalError('leadership_unavailable')
        lease=dict(connection.execute(text("SELECT pg_backend_pid() AS pid,(SELECT backend_start::text FROM pg_stat_activity WHERE pid=pg_backend_pid()) AS started")).mappings().one())
        connection.rollback()
        journal.acquire()
        return Repository(RecoverySession).recover(journal,lease,previous=previous)
    except JournalError as error:
        raise Refused(str(error)) from None
    finally:
        journal.release();connection.close()
