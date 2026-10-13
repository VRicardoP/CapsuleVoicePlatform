"""
Data access repositories for SferaAI.
All database operations go through repositories for:
- Consistent query patterns
- Audit trail integration
- PII encryption handling
"""

from app.repositories.base import BaseRepository
from app.repositories.call_repository import CallRepository, TranscriptionRepository
from app.repositories.consent_repository import (
    CallConsentRepository,
    ConsentRepository,
    ConsentVersionRepository,
)
from app.repositories.gdpr_repository import (
    AuditLogRepository,
    BlockedDataRepository,
    DataSubjectRequestRepository,
    SecurityBreachRepository,
)
from app.repositories.robinson_repository import CampaignRepository, RobinsonCheckRepository
from app.repositories.user_repository import UserRepository, UserSessionRepository

__all__ = [
    # Base
    "BaseRepository",
    # User
    "UserRepository",
    "UserSessionRepository",
    # Call
    "CallRepository",
    "TranscriptionRepository",
    # Consent
    "ConsentRepository",
    "CallConsentRepository",
    "ConsentVersionRepository",
    # GDPR
    "DataSubjectRequestRepository",
    "BlockedDataRepository",
    "SecurityBreachRepository",
    "AuditLogRepository",
    # Robinson
    "RobinsonCheckRepository",
    "CampaignRepository",
]
