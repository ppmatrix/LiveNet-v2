"""Registo explícito dos modelos SQLAlchemy do LiveNet v2."""

from app.audit.models import AuditEvent
from app.security.models import GlobalRoleGrant, LocalUser, LoginSession, LoginThrottle

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

__all__ = ["AuditEvent", "EffectiveConfig", "Group", "GroupMembership", "GroupRule", "Policy", "PolicyVersion", "PolicyAssignment", "Resource", "ResourceIdentifier", "ResourceRelation", "ResourceTag", "Tag", "GlobalRoleGrant", "LocalUser", "LoginSession", "LoginThrottle"]
