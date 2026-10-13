"""
Repositories for WhatsApp Business models.

Split into domain-specific modules:
- core: TenantSettings, Contact, Conversation, Message, Event
- contacts: Segment, Tag, InternalNote
- templates: Template
- campaigns: Campaign, CampaignRecipient
- commerce: PipelineStage, Deal, CatalogItem, Order
- automation: Macro, SlaPolicy, SlaBreach, WebhookConfig, WebhookLog,
              Survey, SurveyResponse, Flow, Integration, WidgetConfig
"""

from .automation import (
    WAFlowRepository,
    WAIntegrationRepository,
    WAMacroRepository,
    WASlaBreachRepository,
    WASlaPolicyRepository,
    WASurveyRepository,
    WASurveyResponseRepository,
    WAWebhookConfigRepository,
    WAWebhookLogRepository,
    WAWidgetConfigRepository,
)
from .campaigns import WACampaignRecipientRepository, WACampaignRepository
from .commerce import (
    WACatalogItemRepository,
    WADealRepository,
    WAOrderRepository,
    WAPipelineStageRepository,
)
from .contacts import (
    WAInternalNoteRepository,
    WASegmentRepository,
    WATagRepository,
)
from .core import (
    WAContactRepository,
    WAConversationRepository,
    WAEventRepository,
    WAMessageRepository,
    WATenantSettingsRepository,
)
from .templates import WATemplateRepository

__all__ = [
    # Core
    "WATenantSettingsRepository",
    "WAContactRepository",
    "WAConversationRepository",
    "WAMessageRepository",
    "WAEventRepository",
    # Contacts
    "WASegmentRepository",
    "WATagRepository",
    "WAInternalNoteRepository",
    # Templates
    "WATemplateRepository",
    # Campaigns
    "WACampaignRepository",
    "WACampaignRecipientRepository",
    # Commerce
    "WAPipelineStageRepository",
    "WADealRepository",
    "WACatalogItemRepository",
    "WAOrderRepository",
    # Automation
    "WAMacroRepository",
    "WASlaPolicyRepository",
    "WASlaBreachRepository",
    "WAWebhookConfigRepository",
    "WAWebhookLogRepository",
    "WASurveyRepository",
    "WASurveyResponseRepository",
    "WAFlowRepository",
    "WAIntegrationRepository",
    "WAWidgetConfigRepository",
]
