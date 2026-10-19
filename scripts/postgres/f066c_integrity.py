"""Manifesto de integridade dos SQL administrativos F0.66C."""

from hashlib import sha256
from pathlib import Path

APPROVED_HASHES = {'f066c_create_roles.sql': 'c37e364ee9c48b7b9667f43364cb2bfd887d2406c0b48a9abc3382f414029425', 'f066c_transfer_ownership.sql': '3b8796eaf21b42a8c46bd771e3ed3c0e944d8175c2fba90cb5ee31023c981f12', 'f066c_rollback_ownership.sql': 'cabe6dc19371a05d6d67d78cae149cdb27bb782cba694e4c78408f51295035f4', 'f066c_grant_app_privileges.sql': 'c1d2d573423552a1d369520b8abc63d24827f3263540eda547ee188fb8043dcd', 'f066c_revoke_app_privileges.sql': '232a79634fd5919d37380daf3cbf4b3929ddc93dd7ab85da2585585e8bfa5a26', 'f066c_revoke_public_function_execute.sql': 'e58cd04b7cd5cd3e4a6c8d5df687532c41d013b4969aa0e9769edd01108f3247', 'f066c_restore_public_function_execute.sql': 'b1c80230e84413080b4f6e938195d76492741d7115b8329d7b4d4899290d5401'}

APPROVED_GUARD_HASH = '1eb88c5cc171d7ee41fcd8f70a0d73575c5bc71fc7d53a32756b3a538a4d2537'


def load_verified_guard(path: Path) -> str:
    """Le a guarda SQL uma vez e valida a sua integridade."""
    raw = path.read_bytes()

    if sha256(raw).hexdigest() != APPROVED_GUARD_HASH:
        raise ValueError("Integridade SQL da guarda divergente")

    guard = raw.decode("utf-8")

    if guard.count("DO $f066c_guard$") != 1:
        raise ValueError("Guarda de sessao inesperada")

    return guard


def verify_sql_integrity(path: Path) -> None:
    expected = APPROVED_HASHES.get(path.name)
    if expected is None:
        raise ValueError('Ficheiro SQL nao autorizado')
    actual = sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise ValueError('Integridade SQL divergente')
