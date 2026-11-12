# CapsuleVoicePlatform

Multi-tenant voice-AI SaaS platform (FastAPI + React) — sanitized portfolio extraction.

This is a sanitized extraction of a production multi-tenant SaaS platform that I
designed and maintain for several real clients (healthcare/aesthetics, real
estate, travel, telecom). This repository **is not the operational project** —
it's a genericized version meant to showcase architecture and code quality in a
portfolio.

## What was removed and why

Before publishing, the following was removed or genericized:

- Names, domains, IPs, and credentials of real clients and production
  infrastructure.
- All client-specific integration documentation and voice agent prompts.
- The vertical modules built for a specific client (real-estate lead
  capture, mass outbound calling, email marketing, booking calendar, travel
  catalog): these exist in the real system but not here, for commercial
  confidentiality. Only the generic architecture shared across clients is
  kept.

What remains is the core of the platform (multi-tenant auth/RBAC, BFF
sessions, repository/service layers, GDPR compliance, background job queue)
plus one complete product module (WhatsApp Business) as an end-to-end
example.

## What this repo shows

**Backend** — FastAPI + async SQLAlchemy + PostgreSQL + Redis + ARQ.

- Multi-tenant authorization based on granular permissions (roles +
  per-user grants/denies), see
  [`backend/app/core/authorization.py`](backend/app/core/authorization.py).
- BFF sessions with an opaque cookie + double-submit CSRF, plus API tokens
  with a declarative scope for server-to-server integrations — see
  [`docs/BFF_SESSIONS.md`](docs/BFF_SESSIONS.md).
- Separated layers: endpoints (thin handlers) → services (business logic) →
  repositories (data access), consistent across the whole backend.
- Built-in GDPR/LOPDGDD compliance: versioned consents, Robinson list
  checks, auditing, breach detection, data export/erasure.
- Integration with an AI voice agent (Ultravox): HMAC-SHA256-signed
  webhooks, agent-invokable functions, call event routing.
- Alembic migrations with a verified linear chain, a test suite (unit +
  integration + endpoints), and CI on GitHub Actions.

**WhatsApp Business module** — a complete product module example:
real-time inbox (SSE), campaign engine with A/B testing, automation flows,
Meta templates, contact segmentation, SLA tracking.
See [`docs/WHATSAPP_MODULE.md`](docs/WHATSAPP_MODULE.md).

**Frontend** — React 19 + TypeScript + Tailwind. Feature-based architecture
(`src/features/{module}/{pages,components,hooks,services}`), permissions via
`AuthorizationContext` + `PermissionGate`, declarative per-module navigation
(`config/navigationConfig.ts`), visibility-aware polling.

## What this repo is NOT

It is not meant to be deployed as-is: it's missing credentials, production
environment variables, and the vertical modules mentioned above. This is
reading and code-evaluation material, not an installable product.

## Stack

Python 3.12 · FastAPI · SQLAlchemy 2 (async) · PostgreSQL · Redis · ARQ ·
Alembic · React 19 · TypeScript · Vite · Tailwind CSS · Docker.

## License

See [LICENSE](LICENSE). All rights reserved — this repository is published
for viewing and evaluation purposes only.
