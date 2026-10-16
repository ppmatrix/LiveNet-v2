"""Registo explícito dos modelos SQLAlchemy do LiveNet v2."""

from app.inventory.models import (
    Group,
    Resource,
    ResourceIdentifier,
    ResourceRelation,
)

__all__ = ["Group", "Resource", "ResourceIdentifier", "ResourceRelation"]
