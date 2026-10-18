"""Registo explícito dos modelos SQLAlchemy do LiveNet v2."""

from app.inventory.models import (
    EffectiveConfig,
    Group,
    GroupMembership,
    GroupRule,
    Policy,
    PolicyVersion,
    PolicyAssignment,
    Resource,
    ResourceIdentifier,
    ResourceRelation,
    ResourceTag,
    Tag,
)

__all__ = ["EffectiveConfig", "Group", "GroupMembership", "GroupRule", "Policy", "PolicyVersion", "PolicyAssignment", "Resource", "ResourceIdentifier", "ResourceRelation", "ResourceTag", "Tag"]
