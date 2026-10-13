# Modulo WhatsApp Business — SferaAI

> **Estado:** Completo. Desplegado en producción desde 2026-02-26.

## Arquitectura

Feature-app integrada en el monolito (NO microservicio). SSE para real-time.

### Backend

```
backend/app/
├── models/whatsapp/          # 6 ficheros, 28 modelos ORM
├── schemas/whatsapp/         # 6 ficheros, 73 schemas Pydantic
├── repositories/whatsapp_repository/  # 6 ficheros, 25 repos
├── api/v1/endpoints/whatsapp/         # 10 sub-routers, 110 rutas
│   ├── conversations.py, contacts.py, campaigns.py
│   ├── commerce.py, automation.py, admin.py
│   ├── webhooks.py, surveys.py, flows.py, integrations.py
├── services/
│   ├── whatsapp_service.py              # Meta Graph API client
│   ├── whatsapp_campaign_service.py     # Batch sending + SSE
│   ├── whatsapp_webhook_service.py      # Inbound message processing
│   ├── whatsapp_messaging_service.py    # Outbound send text/template
│   ├── whatsapp_contact_import_service.py  # CSV import
│   ├── whatsapp_flow_engine.py          # Automation flows
│   └── whatsapp_sse.py                  # Per-tenant SSE broadcaster
```

### Frontend

```
dashboard/src/features/whatsapp/
├── WhatsAppInbox.tsx           # Module router (18 routes)
├── pages/                      # 9 pages (Templates, Campaigns, Contacts, etc.)
├── hooks/                      # 8 hooks (useConversations, useMessages, useSSE, etc.)
├── components/                 # ChatView, ConversationList, MessageBubble, etc.
├── services/whatsappApi/       # 9 domain API files
├── context/WhatsAppContext.tsx
└── types.ts
```

### Meta API

- Cloud API v21.0
- Auth: System User permanent token
- Webhook: HMAC-SHA256 con `app_secret`
- Template IMAGE headers: self-hosted URLs (CDN URLs expiran)
- Template sync: `POST /templates/sync` con paginacion cursor

### SSE Events

| Event | Payload | Trigger |
|-------|---------|---------|
| `message.new` | `{conversationId, message}` | Inbound message |
| `message.status` | `{messageId, status}` | sent/delivered/read/failed |
| `conversation.updated` | `{conversationId, changes}` | Assignment, close |
| `campaign.progress` | `{campaignId, sent, failed, total}` | Campaign sending |

### Feature Flag

`whatsapp_enabled: true` en `organizations.settings` JSONB.
Sidebar: boton verde 💬 con sub-nav condicional.
