"""Trusted integration boundary for future authentication/RBAC.

No implementation authenticates callers here. Scope predicates must come from
server-side policy, never from request parameters or identity headers.
"""

from dataclasses import dataclass
from typing import Mapping, Protocol
from uuid import UUID

from sqlalchemy.sql.elements import ColumnElement


@dataclass(frozen=True)
class InventoryIdentity:
    actor_id: UUID
    actor_type: str = "user"

    def __post_init__(self):
        if not isinstance(self.actor_id, UUID):
            raise ValueError("Invalid actor identity")
        if (not isinstance(self.actor_type, str)
                or not self.actor_type.strip() or len(self.actor_type) > 32):
            raise ValueError("Invalid actor type")


class InventoryAccess(Protocol):
    def resolve_identity(self) -> InventoryIdentity | None:
        """Resolve the authenticated caller using the real identity integration."""
        ...

    def read_scope(self, identity: InventoryIdentity) -> ColumnElement | None:
        """SQL predicate restricting Resource rows; None denies read permission."""
        ...

    def can_create(self, identity: InventoryIdentity, data: Mapping) -> bool:
        """Evaluate creation permission against validated proposed data."""
        ...


class DenyInventoryAccess:
    def resolve_identity(self):
        return None

    def read_scope(self, identity):
        return None

    def can_create(self, identity, data):
        return False
