"""
WhatsApp Business API endpoints.

Split into domain-specific sub-routers for maintainability:
- conversations: Webhook, SSE, messages, notes
- contacts: Contacts, segments, tags, agents
- templates: Template CRUD, sync, submit
- campaigns: Campaign CRUD, start/pause/cancel
- commerce: Pipeline, catalog, orders
- automation: Macros, SLA
- webhooks: Webhook config CRUD, logs, test
- surveys: Survey CRUD, responses
- flows: Flow CRUD, activate
- integrations: Integration CRUD, test
- admin: Dashboard, analytics, widget, audit, auto-assign
"""

from fastapi import APIRouter

from .admin import router as admin_router
from .automation import router as automation_router
from .campaigns import router as campaigns_router
from .commerce import router as commerce_router
from .contacts import router as contacts_router
from .conversations import router as conversations_router
from .flows import router as flows_router
from .functions import router as functions_router
from .integrations import router as integrations_router
from .surveys import router as surveys_router
from .templates import router as templates_router
from .webhooks import router as webhooks_router

router = APIRouter()

router.include_router(conversations_router)
router.include_router(contacts_router)
router.include_router(templates_router)
router.include_router(campaigns_router)
router.include_router(commerce_router)
router.include_router(automation_router)
router.include_router(webhooks_router)
router.include_router(surveys_router)
router.include_router(flows_router)
router.include_router(integrations_router)
router.include_router(admin_router)
router.include_router(functions_router)
