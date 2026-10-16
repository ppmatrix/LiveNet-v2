"""Registo explícito dos modelos SQLAlchemy do LiveNet v2."""

from app.inventory.models import (
    Resource,
    ResourceIdentifier,
    ResourceRelation,
)

__all__ = ["Resource", "ResourceIdentifier", "ResourceRelation"]
