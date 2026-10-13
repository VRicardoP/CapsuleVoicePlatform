"""
WhatsApp Business models for SferaAI.

Split into domain-specific modules:
- core: WATenantSettings, WAContact, WAConversation, WAMessage, WAEvent
- inbox: WASegment, WAContactSegment, WAInternalNote, WATag, WAContactTag
- templates: WATemplate
- campaigns: WACampaign, WACampaignRecipient
- commerce: WAPipelineStage, WADeal, WACatalogItem, WAOrder, WAOrderItem
- automation: WAMacro, WASlaPolicy, WASlaBreach, WAWebhookConfig, WAWebhookLog,
              WASurvey, WASurveyResponse, WAFlow, WAIntegration, WAWidgetConfig
"""

from .automation import (
    WAFlow,
    WAIntegration,
    WAMacro,
    WASlaBreach,
    WASlaPolicy,
    WASurvey,
    WASurveyResponse,
    WAWebhookConfig,
    WAWebhookLog,
    WAWidgetConfig,
)
from .campaigns import WACampaign, WACampaignRecipient
from .commerce import WACatalogItem, WADeal, WAOrder, WAOrderItem, WAPipelineStage
from .core import WAContact, WAConversation, WAEvent, WAMessage, WATenantSettings
from .inbox import WAContactSegment, WAContactTag, WAInternalNote, WASegment, WATag
from .templates import WATemplate

__all__ = [
    # Core
    "WATenantSettings",
    "WAContact",
    "WAConversation",
    "WAMessage",
    "WAEvent",
    # Inbox
    "WASegment",
    "WAContactSegment",
    "WAInternalNote",
    "WATag",
    "WAContactTag",
    # Templates
    "WATemplate",
    # Campaigns
    "WACampaign",
    "WACampaignRecipient",
    # Commerce
    "WAPipelineStage",
    "WADeal",
    "WACatalogItem",
    "WAOrder",
    "WAOrderItem",
    # Automation
    "WAMacro",
    "WASlaPolicy",
    "WASlaBreach",
    "WAWebhookConfig",
    "WAWebhookLog",
    "WASurvey",
    "WASurveyResponse",
    "WAFlow",
    "WAIntegration",
    "WAWidgetConfig",
]
