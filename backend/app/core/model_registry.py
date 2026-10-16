"""Registo explícito dos modelos SQLAlchemy do LiveNet v2."""

from app.inventory.models import (
    Group,
    GroupMembership,
    GroupRule,
    Resource,
    ResourceIdentifier,
    ResourceRelation,
    ResourceTag,
    Tag,
)

__all__ = ["Group", "GroupMembership", "GroupRule", "Resource", "ResourceIdentifier", "ResourceRelation", "ResourceTag", "Tag"]
