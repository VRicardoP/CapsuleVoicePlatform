# CapsuleCorp — Portfolio Showcase

Extracción sanitizada de una plataforma SaaS multi-tenant en producción que diseñé y
mantengo para varios clientes reales (sector salud/estética, inmobiliario, viajes,
telecomunicaciones). Este repositorio **no es el proyecto operativo** — es una versión
genericizada pensada para mostrar arquitectura y calidad de código en un portfolio.

## Qué se ha quitado y por qué

Antes de publicar se eliminaron o genericizaron:

- Nombres, dominios, IPs y credenciales de clientes e infraestructura de producción reales.
- Toda la documentación de integración específica de cliente y los prompts de los
  agentes de voz.
- Los módulos verticales construidos a medida para un cliente concreto (captación de
  leads inmobiliarios, llamadas outbound masivas, email marketing, calendario de
  reservas, catálogo de viajes): existen en el sistema real pero no aquí, por
  confidencialidad comercial. Se mantiene solo lo que es arquitectura genérica
  reutilizable entre clientes.

Lo que queda es el núcleo de la plataforma (auth/RBAC multi-tenant, sesiones BFF,
capas repository/service, cumplimiento RGPD, cola de trabajo en background) más un
módulo de producto completo (WhatsApp Business) como ejemplo end-to-end.

## Qué muestra este repo

**Backend** — FastAPI + SQLAlchemy async + PostgreSQL + Redis + ARQ.

- Autorización multi-tenant basada en permisos granulares (roles + grants/denies por
  usuario), ver [`backend/app/core/authorization.py`](backend/app/core/authorization.py).
- Sesiones BFF con cookie opaca + CSRF double-submit, y tokens de API con scope
  declarativo para integraciones server-to-server — ver
  [`docs/BFF_SESSIONS.md`](docs/BFF_SESSIONS.md).
- Capas separadas endpoints (thin handlers) → services (lógica de negocio) →
  repositories (acceso a datos), consistente en todo el backend.
- Cumplimiento RGPD/LOPDGDD integrado: consentimientos versionados, lista Robinson,
  auditoría, detección de brechas, exportación/olvido de datos.
- Integración con un agente de voz IA (Ultravox): webhooks firmados con HMAC-SHA256,
  funciones invocables por el agente, enrutado de eventos de llamada.
- Migraciones Alembic con cadena lineal verificada, suite de tests (unit + integración
  + endpoints) y CI en GitHub Actions.

**Módulo WhatsApp Business** — ejemplo completo de módulo de producto:
inbox en tiempo real (SSE), motor de campañas con A/B testing, flows de
automatización, plantillas de Meta, segmentación de contactos, control de SLA.
Ver [`docs/WHATSAPP_MODULE.md`](docs/WHATSAPP_MODULE.md).

**Frontend** — React 19 + TypeScript + Tailwind. Arquitectura por features
(`src/features/{modulo}/{pages,components,hooks,services}`), permisos vía
`AuthorizationContext` + `PermissionGate`, navegación declarativa por módulo
(`config/navigationConfig.ts`), polling consciente de visibilidad de pestaña.

## Qué NO es este repo

No está pensado para desplegarse tal cual: faltan credenciales, variables de entorno
de producción y los módulos verticales mencionados arriba. Es material de lectura y
evaluación de código, no un producto instalable.

## Stack

Python 3.12 · FastAPI · SQLAlchemy 2 (async) · PostgreSQL · Redis · ARQ ·
Alembic · React 19 · TypeScript · Vite · Tailwind CSS · Docker.

## Licencia

Ver [LICENSE](LICENSE).
