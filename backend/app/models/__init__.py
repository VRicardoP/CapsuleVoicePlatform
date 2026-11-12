"""
SQLAlchemy models for CapsuleCorp.
All models map to tables in capsulecorp.sql schema.

Compliance coverage:
- RGPD: Art. 5-7, 15-22, 30, 32-34
- LOPDGDD: Art. 5-6, 33-34
- AI Act: Art. 5, 9-17, 50, 86
- LGT: Art. 66-68
- NIS2: Art. 21, 23
"""

from app.models.ai_decision import AIDecisionLog
from app.models.audit import (
    AuditLog,
    BlockedData,
    DataSubjectRequest,
    SecurityBreach,
)
from app.models.base import Base, SoftDeleteMixin, TimestampMixin
from app.models.bff_session import ApiToken, FrontendSession
from app.models.call import Call, CallTrafficData
from app.models.consent import (
    CallProcessingConsent,
    ConsentVersion,
    ContactConsent,
    DataConsent,
    DataProcessingPurpose,
)
from app.models.contact import Contact
from app.models.marketplace import MarketplaceModule
from app.models.organization import Organization, OrganizationSettings
from app.models.permission import (
    PermissionCatalog,
    RolePermissionTemplate,
    UserPermission,
)
from app.models.robinson import Campaign, RobinsonCheck
from app.models.transcription import Transcription
from app.models.user import User, UserSession
from app.models.voice_quota import VoiceMonthlyUsage
from app.models.whatsapp import (
    WAContact,
    WAConversation,
    WAEvent,
    WAMessage,
    WATenantSettings,
)

__all__ = [
    # Base
    "Base",
    "TimestampMixin",
    "SoftDeleteMixin",
    # User
    "User",
    "UserSession",
    # Contact
    "Contact",
    # Call
    "Call",
    "CallTrafficData",
    # Transcription
    "Transcription",
    # AI Decision
    "AIDecisionLog",
    # Consent
    "DataProcessingPurpose",
    "ConsentVersion",
    "DataConsent",
    "ContactConsent",
    "CallProcessingConsent",
    # Audit
    "AuditLog",
    "SecurityBreach",
    "BlockedData",
    "DataSubjectRequest",
    # Robinson
    "RobinsonCheck",
    "Campaign",
    # Organization
    "Organization",
    "OrganizationSettings",
    # WhatsApp
    "WATenantSettings",
    "WAContact",
    "WAConversation",
    "WAMessage",
    "WAEvent",
    # Marketplace
    "MarketplaceModule",
    # Permissions
    "PermissionCatalog",
    "RolePermissionTemplate",
    "UserPermission",
    # BFF (Backend-for-Frontend) sessions
    "FrontendSession",
    "ApiToken",
    # Voice quota
    "VoiceMonthlyUsage",
]
