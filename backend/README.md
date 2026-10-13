# SferaAI Backend API

API REST para el sistema de Call Center con IA, con cumplimiento legal completo de RGPD, LOPDGDD, AI Act y NIS2.

## Stack Tecnológico

| Componente | Tecnología | Versión |
|------------|------------|---------|
| Lenguaje | Python | 3.12+ |
| Framework | FastAPI | 0.115+ |
| ORM | SQLAlchemy | 2.0+ (async) |
| Driver DB | asyncpg | 0.30+ |
| Autenticación | python-jose (JWT) | 3.3+ |
| Hashing | passlib (bcrypt) | 1.7+ |
| Validación | Pydantic | 2.10+ |
| Testing | pytest + pytest-asyncio | 8.3+ |
| Logging | structlog | 24.4+ |

---

## Arquitectura

### Estructura del Proyecto

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # Entry point FastAPI
│   ├── api/
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py       # Router principal v1
│   │       └── endpoints/      # Endpoints por dominio
│   │           ├── auth.py           # Login, sessions, API keys (856 líneas)
│   │           ├── users.py          # Perfil, preferencias
│   │           ├── calls.py          # CRUD, grabaciones, human review (885 líneas)
│   │           ├── consents.py       # Gestión consentimientos RGPD
│   │           ├── gdpr.py           # Derechos ARSOPL, export, compliance PDF (574 líneas)
│   │           ├── dashboard.py      # Métricas, KPIs, GDPR dashboard (1480 líneas)
│   │           ├── ultravox.py       # Webhooks, recordings, Zadarma (1491 líneas)
│   │           ├── whatsapp.py       # WhatsApp Business API
│   │           ├── marketplace.py    # Marketplace de módulos
│   │           └── contact.py        # Formulario de contacto
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py         # Pydantic Settings
│   │   └── database.py         # SQLAlchemy async
│   ├── core/
│   │   ├── __init__.py
│   │   ├── security.py         # JWT, password hashing
│   │   ├── dependencies.py     # FastAPI dependencies
│   │   └── middleware.py       # Audit, rate limit, security
│   ├── models/                 # SQLAlchemy Models
│   ├── schemas/                # Pydantic Schemas
│   │   ├── auth.py
│   │   └── common.py           # GDPR-compliant schemas
│   ├── services/               # Business logic
│   │   ├── auth_service.py
│   │   ├── encryption_service.py
│   │   ├── recording_service.py          # Descarga, transcoding, cifrado Fernet
│   │   ├── breach_detection.py           # Detección automática brechas (RGPD Art.33)
│   │   └── compliance_report_service.py  # PDF AEPD (WeasyPrint)
│   ├── templates/              # Plantillas HTML
│   │   └── compliance_report.html        # Template informe AEPD
│   ├── repositories/           # Data access
│   └── utils/
├── tests/
│   ├── conftest.py              # DB fixtures (db_session, test data)
│   ├── integration/             # Repository + DB integration tests (~100)
│   ├── test_endpoints/          # HTTP endpoint tests (27)
│   ├── test_services/           # Service-level tests (7)
│   └── unit/                    # Pure unit tests (~69)
├── .env.example
├── pyproject.toml
├── Dockerfile
└── README.md
```

### Arquitectura Multi-Cliente

El sistema soporta **tres tipos de clientes** con diferentes patrones de acceso:

```
┌───────────────────────────────────────────────────────────────────────────┐
│                           CLIENTES DEL SISTEMA                             │
├───────────────────────────────────────────────────────────────────────────┤
│  ┌────────────────┐   ┌────────────────────┐   ┌────────────────────────┐ │
│  │    FRONTEND    │   │    AGENTE IA       │   │   APPS CENTRALITA      │ │
│  │    (React)     │   │   (Conversacional) │   │   (CTI, IVR, PBX)      │ │
│  ├────────────────┤   ├────────────────────┤   ├────────────────────────┤ │
│  │ 90% LECTURA    │   │ 70% ESCRITURA      │   │ 80% ESCRITURA          │ │
│  │ Auth: JWT      │   │ Auth: API Key      │   │ Auth: API Key + IP     │ │
│  │ Rol: sfera_app │   │ Rol: sfera_ai_agent│   │ Rol: sfera_pbx         │ │
│  └───────┬────────┘   └─────────┬──────────┘   └───────────┬────────────┘ │
│          │                      │                          │              │
│          └──────────────────────┼──────────────────────────┘              │
│                                 ▼                                          │
│                    ┌─────────────────────────┐                            │
│                    │      BACKEND API        │                            │
│                    │       (FastAPI)         │                            │
│                    └───────────┬─────────────┘                            │
│                                ▼                                          │
│                    ┌─────────────────────────┐                            │
│                    │      PostgreSQL         │                            │
│                    │   (Cifrado + RLS)       │                            │
│                    └─────────────────────────┘                            │
└───────────────────────────────────────────────────────────────────────────┘
```

| Cliente | Autenticación | Rol PostgreSQL | Rate Limit |
|---------|---------------|----------------|------------|
| Frontend | JWT (usuario) | `sfera_app` | 100 req/min |
| Agente IA | API Key | `sfera_ai_agent` | 1000 req/min |
| Centralita | API Key + IP whitelist | `sfera_pbx` | 500 req/min |

Ver [docs/ARCHITECTURE_MULTICLIENTE.md](docs/ARCHITECTURE_MULTICLIENTE.md) para detalles completos.

### Arquitectura de Contenedores

```
┌─────────────────────────────────────────────────────────────────┐
│                        Docker Network                            │
│                      (sferaai-network)                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   postgres   │    │   backend    │    │   frontend   │       │
│  │              │    │              │    │              │       │
│  │ PostgreSQL   │◄───│   FastAPI    │◄───│ React+Nginx  │       │
│  │ + pgcrypto   │    │   Uvicorn    │    │              │       │
│  │              │    │              │    │              │       │
│  │ Puerto: 5432 │    │ Puerto: 8000 │    │ Puerto: 80   │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│         │                   │                   │                │
│         │                   │                   │                │
│    Volume:             Sin estado          Sin estado           │
│    postgres_data       (stateless)         (stateless)          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Comunicación entre contenedores:**

| Origen | Destino | Protocolo | Puerto |
|--------|---------|-----------|--------|
| frontend | backend | HTTP | 8000 |
| backend | postgres | PostgreSQL | 5432 |
| cliente | frontend | HTTPS | 80/443 |

---

## Seguridad y Cumplimiento Normativo

### Principio Fundamental

> **El backend NO maneja directamente claves de cifrado.** Todo el cifrado/descifrado se realiza en PostgreSQL mediante funciones `SECURITY DEFINER`.

### Flujo de Autenticación

```
┌─────────┐         ┌─────────┐         ┌─────────────┐
│ Cliente │         │ Backend │         │  PostgreSQL │
└────┬────┘         └────┬────┘         └──────┬──────┘
     │                   │                     │
     │ 1. Login          │                     │
     │ (email, password) │                     │
     │──────────────────►│                     │
     │                   │                     │
     │                   │ 2. Validar creds    │
     │                   │────────────────────►│
     │                   │                     │
     │                   │ 3. set_current_user()
     │                   │────────────────────►│
     │                   │                     │
     │                   │ 4. session_token    │
     │                   │◄────────────────────│
     │                   │                     │
     │ 5. JWT            │                     │
     │ (contiene         │                     │
     │  session_token)   │                     │
     │◄──────────────────│                     │
     │                   │                     │
```

### Gestión de Claves

| Clave | Ubicación | Acceso |
|-------|-----------|--------|
| `kms_master_key` | `secure_keys` (PostgreSQL) | Solo funciones SECURITY DEFINER |
| `audit_hmac_key` | `secure_keys` (PostgreSQL) | Solo funciones SECURITY DEFINER |
| `SECRET_KEY` (JWT) | `.env` (Backend) | Solo backend |

**Protección contra ataques:**
- ✅ SQLi no puede manipular claves (están en tabla, no en GUC)
- ✅ Tokens robados no funcionan (vinculados a `backend_pid`)
- ✅ RLS con FORCE impide bypass incluso por owner

### Cifrado de PII

```
┌──────────────────────────────────────────────────────────┐
│                    DATOS ENTRANTES                        │
├──────────────────────────────────────────────────────────┤
│ Cliente → Backend: JSON plaintext                         │
│ { "email": "user@example.com" }                          │
│                                                          │
│ Backend → PostgreSQL:                                     │
│ INSERT INTO users (email)                                 │
│ VALUES (encrypt_pii_with_metadata('user@example.com'))   │
│                                                          │
│ PostgreSQL almacena:                                      │
│ { "c": "base64...", "iv": "...", "tag": "...",           │
│   "alg": "AES-256-CBC+HMAC-SHA256", "kid": "key-1" }     │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│                    DATOS SALIENTES                        │
├──────────────────────────────────────────────────────────┤
│ PostgreSQL:                                               │
│ SELECT decrypt_pii_with_metadata(email) FROM users       │
│                                                          │
│ Backend ← PostgreSQL: "user@example.com"                  │
│                                                          │
│ Cliente ← Backend: JSON via HTTPS                         │
│ { "email": "user@example.com" }                          │
└──────────────────────────────────────────────────────────┘
```

### Cumplimiento por Normativa

#### RGPD (UE) 2016/679

| Artículo | Requisito | Implementación |
|----------|-----------|----------------|
| Art. 5.1.f | Integridad y confidencialidad | Cifrado via PostgreSQL, TLS 1.3, HMAC en audit |
| Art. 7 | Prueba de consentimiento | `consent_evidence_file` almacenado cifrado |
| Art. 12.3 | Respuesta en 1 mes | `RightsRequestResponse.response_due_date` |
| Art. 15 | Derecho de acceso | `export_user_data_gdpr_compliant()` |
| Art. 17 | Derecho de supresión | Bloqueo LOPDGDD Art. 33 antes de borrado |
| Art. 20 | Portabilidad | `GDPRDataExport` schema, JSON/CSV |
| Art. 22 | Decisiones automatizadas | `AIDecisionInfo` con explicación |
| Art. 30 | Registro de actividades | `AuditMiddleware` + `audit_log` PostgreSQL |
| Art. 32 | Seguridad del tratamiento | Cifrado AES-256, RLS, `secure_sessions` |
| Art. 33 | Notificación de brechas | `security_breaches` + detección automática |

#### LOPDGDD 3/2018

| Artículo | Requisito | Implementación |
|----------|-----------|----------------|
| Art. 5 | Confidencialidad | Claves en `secure_keys`, nunca en código |
| Art. 11 | Información por capas | Schemas separados para cada capa |
| Art. 33 | Bloqueo de datos | `BlockedDataInfo`, `blocked_data` tabla |
| Art. 34 | DPO obligatorio | Endpoints específicos con `require_dpo` |

#### AI Act (UE) 2024/1689

| Artículo | Requisito | Implementación |
|----------|-----------|----------------|
| Art. 12 | Trazabilidad | `ai_decision_logs` via `AIDecisionInfo` |
| Art. 14 | Supervisión humana | `human_review_required`, `human_override` |
| Art. 50 | Transparencia | `ai_disclosure_timestamp` obligatorio |
| Art. 86 | Derecho a explicación | `AIDecisionInfo.explanation` |

#### NIS2 (UE) 2022/2555

| Artículo | Requisito | Implementación |
|----------|-----------|----------------|
| Art. 20 | Gobernanza ciberseguridad | `BreachDetectionService` automático, audit_log inmutable |
| Art. 21 | Medidas gestión riesgos | Detección bruta fuerza, acceso anómalo, exfiltración |
| Art. 23 | Notificación incidentes | `security_breaches` + detección cada 5 min |

### Row Level Security (RGPD Art. 25, Art. 32)

PostgreSQL RLS habilitado con `FORCE` en todas las tablas con PII:
- Backend usa rol `sfera_app` (limitado)
- Incluso postgres no puede bypasear RLS
- Políticas basadas en `get_current_user()` que valida contra `secure_sessions`

### Detección Automática de Brechas (RGPD Art. 33, NIS2 Art. 23)

`BreachDetectionService` (`app/services/breach_detection.py`) escanea `audit_log` cada 5 minutos:

| Patrón | Umbral | Ventana | Severidad |
|--------|--------|---------|-----------|
| Fuerza bruta | >10 login fallidos/IP | 5 min | Alta |
| Acceso anómalo | >50 fallos/IP | 10 min | Media |
| Exfiltración datos | >20 exportaciones/usuario | 60 min | Crítica |

Deduplicación SHA-256 (no re-alerta en 24h). Background task en `main.py` lifespan.

### Grabaciones de Voz (RGPD Art. 28, 32)

Estrategia completa en `docs/RECORDING_STRATEGY.md`:

| Aspecto | Implementación |
|---------|----------------|
| Cifrado en reposo | Fernet (AES-128-CBC + HMAC), clave en `.env` por cliente |
| Procesamiento | Background task, `asyncio.Semaphore(2)` + `nice 19` |
| Retención | 3 días, limpieza automática diaria |
| Derecho supresión | Borrado archivo + `UPDATE calls SET recording_file_path = NULL` |

### Informes AEPD

`GET /gdpr/compliance/report/pdf` genera informe PDF con: puntuación RGPD, estado consentimientos, solicitudes ARCO, integridad audit log, brechas de seguridad, trazabilidad IA, datos bloqueados. Implementado en `ComplianceReportService` con WeasyPrint.

### Auditoría SQL

```sql
-- Accesos a datos de un usuario
SELECT * FROM audit_log WHERE entity_id = '<user_uuid>'::uuid ORDER BY created_at DESC;

-- Verificar integridad de audit log
SELECT * FROM validate_audit_log_integrity();

-- Sesiones activas
SELECT * FROM secure_sessions WHERE is_valid = true AND expires_at > NOW();
```

---

## Instalación y Configuración

### Requisitos Previos

- Python 3.12+
- PostgreSQL 16+ con extensiones: `uuid-ossp`, `pgcrypto`, `pg_trgm`
- Docker y Docker Compose (para despliegue)

### Desarrollo Local

```bash
# 1. Clonar y entrar al directorio
cd backend

# 2. Crear entorno virtual
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# 3. Instalar dependencias
pip install -e ".[dev]"

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus valores

# 5. Ejecutar
python -m uvicorn app.main:app --reload
```

### Configuración de PostgreSQL

```sql
-- 1. Como superuser, configurar claves
SET app.kms_master_key = 'tu_clave_maestra_32_caracteres__';
SET app.audit_hmac_key = 'tu_clave_hmac_32_caracteres____';

-- 2. Migrar claves a tabla segura
SELECT initialize_secure_keys();

-- 3. Crear clave de cifrado
INSERT INTO encryption_keys (
    key_id, encrypted_key, algorithm, is_active, activated_at
) VALUES (
    'key-2025-001',
    pgp_sym_encrypt(
        encode(gen_random_bytes(32), 'hex'),
        current_setting('app.kms_master_key'),
        'cipher-algo=aes256'
    ),
    'AES-256-GCM',
    true,
    NOW()
);
```

### Docker Compose

```bash
# Desde la raíz del proyecto (SferaAI/)
cp .env.example .env
# Editar .env

# Construir e iniciar
docker-compose up --build

# Verificar salud
curl http://localhost:8000/health/security
```

---

## Variables de Entorno

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `ENVIRONMENT` | Entorno de ejecución | `development`, `production` |
| `DEBUG` | Modo debug | `true`, `false` |
| `POSTGRES_HOST` | Host de PostgreSQL | `localhost`, `postgres` |
| `POSTGRES_PORT` | Puerto de PostgreSQL | `5432` |
| `POSTGRES_USER` | Usuario de PostgreSQL | `sfera_app` |
| `POSTGRES_PASSWORD` | Contraseña de PostgreSQL | `***` |
| `POSTGRES_DB` | Base de datos | `sfera` |
| `SECRET_KEY` | Clave para JWT | `token_urlsafe(32)` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Expiración token acceso | `30` |
| `CORS_ORIGINS` | Orígenes permitidos | `["http://localhost:3000"]` |
| `API_KEY_PROVISION_SECRET` | Secreto para provisión M2M | `openssl rand -hex 32` |
| `SMTP_HOST` | Servidor SMTP | `smtp.tuservidor.com` |
| `SMTP_PORT` | Puerto SMTP | `587` |
| `SMTP_USER` | Usuario SMTP | `usuario@tudominio.com` |
| `SMTP_PASSWORD` | Contraseña SMTP | `***` |
| `SMTP_TLS` | Usar TLS | `true` |
| `SMTP_FROM_EMAIL` | Email remitente | `noreply@tudominio.com` |
| `SMTP_FROM_NAME` | Nombre remitente | `Dashboard` |
| `CONTACT_EMAIL` | Email destino contacto | `contact@tudominio.com` |

**Nota:** `KMS_MASTER_KEY` y `AUDIT_HMAC_KEY` NO se configuran aquí. Están en `secure_keys` de PostgreSQL.

---

## API Endpoints

### Fase 1: Autenticación y Usuarios (BFF — ver [`docs/BFF_SESSIONS.md`](../docs/BFF_SESSIONS.md))

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/v1/auth/login` | Iniciar sesión — setea cookie `__Host-sferaai_session` |
| POST | `/api/v1/auth/refresh` | Shim 204 (BFF auto-refresca) |
| POST | `/api/v1/auth/logout` | Revoca sesión y borra cookie |
| GET | `/api/v1/auth/sessions` | Listar sesiones activas del usuario |
| DELETE | `/api/v1/auth/sessions/{id}` | Revocar sesión remota (require_recent_auth) |
| POST | `/api/v1/auth/validate` | Validar la sesión actual |
| GET | `/api/v1/users/me` | Perfil actual |
| PUT | `/api/v1/users/me` | Actualizar perfil |
| POST | `/api/v1/users/me/password` | Cambiar contraseña (require_recent_auth) |

### API Tokens (server-to-server / CI, scope-limited)

| Método | Endpoint | Auth | Descripción |
|--------|----------|------|-------------|
| POST | `/api/v1/auth/api-token` | BFF admin + require_recent_auth | Emitir token `sferaai_at_*` con scope acotado |
| GET | `/api/v1/auth/api-tokens` | BFF | Listar tokens propios (sin valor) |
| DELETE | `/api/v1/auth/api-tokens/{id}` | BFF + require_recent_auth | Revocar token |

### API Keys (Machine-to-Machine — voice agents, PBX)

Uso distinto a los API tokens: las API Keys son para servicios externos (Ultravox, PBX) y permanecen inmutables. Los API tokens son para scripts CI del propio cliente y rotan.

| Método | Endpoint | Auth | Descripción |
|--------|----------|------|-------------|
| POST | `/api/v1/auth/api-keys` | BFF admin | Crear API Key |
| GET | `/api/v1/auth/api-keys` | BFF admin | Listar API Keys |
| DELETE | `/api/v1/auth/api-keys/{id}` | BFF admin | Revocar API Key |
| POST | `/api/v1/auth/provision-api-key` | Secreto | Provisión automática sin admin |

**Provisión Automática:**

Permite a servicios obtener API Keys sin credenciales de admin usando un secreto pre-compartido:

```bash
curl -X POST /api/v1/auth/provision-api-key \
  -H "Content-Type: application/json" \
  -d '{
    "provision_secret": "<API_KEY_PROVISION_SECRET>",
    "client_type": "ai_agent",
    "service_name": "Voice Assistant",
    "service_id": "voice-001"
  }'
```

**Tipos de cliente:** `ai_agent`, `pbx`, `external`, `webhook`

**Uso de API Key:**
```bash
curl -X POST /api/v1/calls \
  -H "X-API-Key: sfera_ai_agent_..." \
  -H "Content-Type: application/json" \
  -d '{"direction": "inbound", "status": "initiated"}'
```

### Fase 2: Dashboard y Métricas

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/v1/dashboard/metrics` | Métricas generales |
| GET | `/api/v1/dashboard/calls` | Estadísticas llamadas |
| GET | `/api/v1/dashboard/agents` | Estado agentes |

### Fase 3: Llamadas y Grabaciones

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/v1/calls` | Listar llamadas |
| GET | `/api/v1/calls/{id}` | Detalle llamada |
| GET | `/api/v1/calls/{id}/transcript` | Transcripción |
| POST | `/api/v1/calls/{id}/sentiment` | Análisis sentimiento |

### Fase 4: Consentimientos RGPD

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/v1/consents` | Listar consentimientos |
| POST | `/api/v1/consents` | Registrar consentimiento |
| DELETE | `/api/v1/consents/{id}` | Retirar consentimiento |

### Fase 5: Derechos RGPD (ARSOPL)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/v1/gdpr/export` | Exportar datos (Art. 15, 20) |
| POST | `/api/v1/gdpr/rectify` | Rectificar datos (Art. 16) |
| POST | `/api/v1/gdpr/erase` | Suprimir datos (Art. 17) |
| POST | `/api/v1/gdpr/restrict` | Limitar tratamiento (Art. 18) |
| POST | `/api/v1/gdpr/object` | Oposición (Art. 21) |
| GET | `/api/v1/gdpr/compliance/report/pdf` | Informe cumplimiento PDF (AEPD) |

### Fase 6: Administración

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/v1/admin/audit-log` | Registro auditoría |
| GET | `/api/v1/admin/blocked-data` | Datos bloqueados |
| POST | `/api/v1/admin/key-rotation` | Rotar clave cifrado |

### Endpoints Agente IA (API Key: `ai_agent`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/v1/ai-agent/calls` | Crear nueva llamada |
| POST | `/api/v1/ai-agent/calls/{id}/transcription` | Guardar transcripción |
| POST | `/api/v1/ai-agent/calls/{id}/sentiment` | Registrar análisis sentimiento |
| POST | `/api/v1/ai-agent/decisions` | Registrar decisión IA (AI Act Art. 12) |
| GET | `/api/v1/ai-agent/customers/{id}/context` | Obtener contexto cliente |
| GET | `/api/v1/ai-agent/customers/{id}/consents` | Verificar consentimientos activos |
| POST | `/api/v1/ai-agent/calls/{id}/human-escalation` | Escalar a humano (Art. 14) |
| POST | `/api/v1/ai-agent/client-errors` | Reportar error del cliente (automático) |
| GET | `/api/v1/ai-agent/client-errors` | Consultar errores (DPO/admin) |

### Endpoints Centralita/PBX (API Key: `pbx`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/v1/pbx/calls` | Crear nueva llamada |
| PUT | `/api/v1/pbx/calls/{id}/status` | Actualizar estado llamada |
| POST | `/api/v1/pbx/calls/{id}/recording` | Registrar grabación |
| POST | `/api/v1/pbx/calls/{id}/ai-disclosure` | Registrar aviso IA (Art. 50) |
| GET | `/api/v1/pbx/robinson/check` | Verificar Lista Robinson |
| POST | `/api/v1/pbx/calls/{id}/consent` | Registrar consentimiento verbal |
| POST | `/api/v1/pbx/calls/{id}/end` | Finalizar llamada |

### Contacto

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/v1/contact/send` | Enviar mensaje de contacto (requiere autenticación) |

**Campos requeridos:**
- `subject`: Asunto del mensaje
- `message`: Contenido del mensaje

El email se envía a la dirección configurada en `CONTACT_EMAIL` incluyendo información del usuario autenticado.

---

## Endpoints de Salud

| Endpoint | Descripción |
|----------|-------------|
| `GET /` | Información API |
| `GET /health` | Health check básico |
| `GET /health/ready` | Readiness (conectividad DB) |
| `GET /health/security` | Estado de seguridad |

**Ejemplo `/health/security`:**
```json
{
  "status": "secure",
  "security": {
    "secure_keys_configured": true,
    "encryption_key_active": true,
    "secure_sessions_ready": true
  }
}
```

---

## Testing

**284 tests passing** (0 failures):

| Categoría | Tests | Descripción |
|-----------|-------|-------------|
| Integration | 89 | Repository CRUD, GDPR, encryption, audit, sessions, API keys, error logs |
| Endpoint | 27 | HTTP-level con httpx + ASGITransport (health, auth, dashboard, calls, gdpr, marketplace) |
| Service | 7 | Breach detection patterns contra DB real |
| Unit | 161 | WhatsApp (schemas, SSE, service, phases B-F), calendar schemas, API key schemas |

```bash
# Ejecutar todos los tests
pytest

# Con cobertura
pytest --cov=app --cov-report=html

# Solo endpoint tests
pytest tests/test_endpoints/

# Solo breach detection tests
pytest tests/test_services/

# Solo unit tests
pytest tests/unit/

# Solo integration tests
pytest tests/integration/
```

---

## Plan de Implementación

### Fase 1: Core ✅
- [x] Estructura de proyecto
- [x] Configuración (settings, database)
- [x] Seguridad (JWT, secure_sessions)
- [x] Middleware (audit, rate limit)
- [x] Schemas base
- [x] **Arquitectura multi-cliente** (roles, API keys)
- [x] **Schemas AI Agent** (`ai_agent.py`)
- [x] **Schemas PBX** (`pbx.py`)
- [x] **API Key Auth** (`api_key_auth.py`)
- [x] **SQLAlchemy Models** (User, Call, Consent, Audit, Robinson)
- [x] **Repositories** (BaseRepository, UserRepository, GDPRRepository, etc.)
- [x] Endpoint `/auth/login` (BFF: setea cookie opaca)
- [x] Endpoint `/auth/logout`
- [x] Endpoint `/auth/refresh` (shim 204 desde Fase 1 BFF)
- [x] Endpoint `/auth/sessions` + `/auth/sessions/{id}` (require_recent_auth)
- [x] Endpoint `/auth/api-token` + `/auth/api-tokens` (scoped CI tokens)
- [x] Endpoint `/users/me` + `/users/me/password` (require_recent_auth)

### Fase 2: Dashboard ✅
- [x] `get_dashboard_metrics()` wrapper
- [x] `get_dashboard_metrics_gdpr()` wrapper
- [x] `get_gdpr_executive_summary()` wrapper
- [x] `get_kpi_metrics()` wrapper
- [x] Endpoints dashboard completos

### Fase 3: Llamadas ✅
- [x] CRUD llamadas
- [x] Transcripciones
- [x] Detalle de llamada con transcripción
- [x] Revisión humana (AI Act Art. 14)

### Fase 4: Derechos RGPD ✅
- [x] Acceso (Art. 15) - `/gdpr/access`
- [x] Rectificación (Art. 16) - `/gdpr/rectify`
- [x] Supresión (Art. 17) - `/gdpr/erase` (con bloqueo LOPDGDD Art. 33)
- [x] Limitación (Art. 18) - `/gdpr/restrict`
- [x] Portabilidad (Art. 20) - `/gdpr/portability`
- [x] Oposición (Art. 21) - `/gdpr/object`
- [x] Decisiones automatizadas (Art. 22) - `/gdpr/automated-decisions`
- [x] Estado solicitudes - `/gdpr/requests`

### Fase 5: Endpoints Multi-Cliente ✅
- [x] Router `/api/v1/ai/` (Agente IA)
  - [x] POST `/ai/decisions` - Registro decisiones (AI Act Art. 12)
  - [x] POST `/ai/calls/{id}/transcription` - Guardar transcripción
  - [x] POST `/ai/calls/{id}/sentiment` - Análisis sentimiento
  - [x] POST `/ai/calls/{id}/human-escalation` - Escalar a humano
  - [x] GET `/ai/customers/{id}/context` - Contexto cliente
  - [x] GET `/ai/customers/{id}/consents` - Verificar consentimientos
  - [x] Bloqueo análisis emocional empleados (AI Act Art. 5.1.f)
- [x] Router `/api/v1/pbx/` (Centralita)
  - [x] POST `/pbx/calls` - Crear llamada
  - [x] PUT `/pbx/calls/{id}/status` - Actualizar estado
  - [x] POST `/pbx/calls/{id}/ai-disclosure` - Registrar aviso IA (Art. 50)
  - [x] POST `/pbx/calls/{id}/emotion-disclosure` - Aviso detección emociones
  - [x] POST `/pbx/calls/{id}/consent` - Consentimiento verbal
  - [x] POST `/pbx/calls/{id}/end` - Finalizar llamada
  - [x] GET `/pbx/robinson/check` - Verificación Lista Robinson
  - [x] GET `/pbx/traffic-data/{id}` - Datos de tráfico (LGT)

### Fase 6: Admin (Pendiente)
- [ ] Auditoría avanzada
- [ ] Gestión datos bloqueados
- [ ] Rotación de claves

### Fase 7: Testing ✅
- [x] Tests unitarios (schemas, models, services)
- [x] Tests de integración (PostgreSQL real: GDPR, encryption, audit, Robinson, sessions, API keys, error logs, security breaches)
- [x] Tests de endpoint (httpx + ASGITransport: health, auth, dashboard, calls, gdpr, marketplace)
- [x] Tests de servicios (breach detection contra DB real)
- **Total: 284 tests passing** (89 integration + 27 endpoint + 7 service + 161 unit, 0 failures)

### Fase 8: Detección Automática de Brechas ✅
- [x] `BreachDetectionService` — escaneo periódico de `audit_log`
- [x] Detección fuerza bruta (>10 FAILED_LOGIN/IP en 5min)
- [x] Detección acceso anómalo (>50 fallos/IP en 10min)
- [x] Detección exfiltración datos (>20 DATA_EXPORT/usuario en 1h)
- [x] Dedup SHA-256 (no re-alerta en 24h)
- [x] Background task en `main.py` lifespan (cada 5 minutos)
- [x] Registro automático en `security_breaches` via `SecurityBreachRepository`

---

## Próximos Pasos

1. **Admin endpoints**
   - Auditoría avanzada
   - Gestión de datos bloqueados
   - Rotación de claves de cifrado

2. **Frontend tests**
   - Infraestructura de testing (Vitest + React Testing Library)
   - Tests de componentes y hooks

---

## Licencia

MIT License - Ver archivo LICENSE en la raíz del proyecto.

---

*SferaAI Backend v1.3.0 - Febrero 2026*
*Última actualización: 2026-02-17*
*Estado: 284 tests passing, breach detection activo, despliegue producción*
*Features: API Keys, SMTP, PDF AEPD, Grabaciones (Fernet), WhatsApp, Marketplace, Breach Detection*
*Endpoints: 65+ (ver openapi.json)*
