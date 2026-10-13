# Arquitectura Multi-Cliente SferaAI

## Visión General

El sistema SferaAI tiene **tres tipos de clientes** que interactúan con la API, cada uno con diferentes patrones de acceso y requisitos de seguridad:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CLIENTES DEL SISTEMA                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────┐   ┌────────────────────┐   ┌────────────────────────┐   │
│  │    FRONTEND    │   │    AGENTE IA       │   │   APPS CENTRALITA      │   │
│  │    (React)     │   │   (Conversacional) │   │   (CTI, IVR, etc.)     │   │
│  ├────────────────┤   ├────────────────────┤   ├────────────────────────┤   │
│  │ • Dashboard    │   │ • Procesar llamada │   │ • Iniciar llamada      │   │
│  │ • Gestión      │   │ • Transcribir      │   │ • Registrar eventos    │   │
│  │ • Reportes     │   │ • Analizar sent.   │   │ • Enrutar llamada      │   │
│  │ • GDPR rights  │   │ • Decisiones IA    │   │ • Grabar audio         │   │
│  ├────────────────┤   ├────────────────────┤   ├────────────────────────┤   │
│  │ 90% LECTURA    │   │ 70% ESCRITURA      │   │ 80% ESCRITURA          │   │
│  │ 10% ESCRITURA  │   │ 30% LECTURA        │   │ 20% LECTURA            │   │
│  └───────┬────────┘   └─────────┬──────────┘   └───────────┬────────────┘   │
│          │                      │                          │                │
│          │     Autenticación    │      Autenticación       │                │
│          │     Usuario/JWT      │      API Key/Service     │                │
│          │                      │                          │                │
│          └──────────────────────┼──────────────────────────┘                │
│                                 │                                            │
│                                 ▼                                            │
│                    ┌─────────────────────────┐                              │
│                    │      BACKEND API        │                              │
│                    │       (FastAPI)         │                              │
│                    ├─────────────────────────┤                              │
│                    │ • Autenticación         │                              │
│                    │ • Autorización (RBAC)   │                              │
│                    │ • Rate Limiting         │                              │
│                    │ • Auditoría             │                              │
│                    └───────────┬─────────────┘                              │
│                                │                                            │
│                                ▼                                            │
│                    ┌─────────────────────────┐                              │
│                    │      PostgreSQL         │                              │
│                    │   (Cifrado + RLS)       │                              │
│                    └─────────────────────────┘                              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Tipos de Cliente

### 1. Frontend (React Dashboard)

**Uso principal:** Supervisores, administradores, DPO

| Operación | Frecuencia | Ejemplo |
|-----------|------------|---------|
| LECTURA | 90% | Dashboard, métricas, listados |
| ESCRITURA | 10% | Configuración, gestión usuarios |

**Autenticación:** JWT con sesión de usuario (secure_sessions)

**Endpoints principales:**
- `GET /api/v1/dashboard/*` - Métricas y estadísticas
- `GET /api/v1/calls` - Listado de llamadas
- `GET /api/v1/users` - Gestión de usuarios
- `POST /api/v1/gdpr/*` - Derechos RGPD

---

### 2. Agente IA (Conversacional)

**Uso principal:** Procesamiento de llamadas en tiempo real

| Operación | Frecuencia | Ejemplo |
|-----------|------------|---------|
| LECTURA | 30% | Contexto cliente, historial |
| ESCRITURA | 70% | Transcripciones, decisiones IA, sentimiento |

**Autenticación:** API Key de servicio + Client Certificate (mTLS)

**Características especiales:**
- Alta frecuencia de operaciones
- Baja latencia requerida (<100ms)
- Debe registrar TODAS las decisiones (AI Act Art. 12)
- Debe verificar consentimiento antes de analizar sentimiento

**Endpoints principales:**
```
POST /api/v1/ai/calls/{id}/transcription     # Guardar transcripción
POST /api/v1/ai/calls/{id}/sentiment         # Registrar análisis sentimiento
POST /api/v1/ai/decisions                     # Registrar decisión IA
GET  /api/v1/ai/customers/{id}/context       # Obtener contexto cliente
GET  /api/v1/ai/customers/{id}/consents      # Verificar consentimientos
POST /api/v1/ai/calls/{id}/human-escalation  # Escalar a humano (Art. 14)
```

---

### 3. Aplicaciones de Centralita (CTI, IVR, PBX)

**Uso principal:** Gestión del ciclo de vida de llamadas

| Operación | Frecuencia | Ejemplo |
|-----------|------------|---------|
| LECTURA | 20% | Verificar cliente, obtener configuración |
| ESCRITURA | 80% | Crear llamada, actualizar estado, grabar |

**Autenticación:** API Key de servicio + IP whitelist

**Características especiales:**
- Operaciones síncronas críticas
- Debe crear registros ANTES de iniciar grabación
- Debe registrar `ai_disclosure_timestamp` (AI Act Art. 50)
- Debe verificar Lista Robinson antes de llamadas salientes

**Endpoints principales:**
```
POST /api/v1/pbx/calls                       # Crear nueva llamada
PUT  /api/v1/pbx/calls/{id}/status           # Actualizar estado
POST /api/v1/pbx/calls/{id}/recording        # Registrar grabación
POST /api/v1/pbx/calls/{id}/ai-disclosure    # Registrar aviso IA
GET  /api/v1/pbx/robinson/check              # Verificar Lista Robinson
POST /api/v1/pbx/calls/{id}/consent          # Registrar consentimiento verbal
```

---

## Modelo de Autenticación

### Matriz de Autenticación por Cliente

| Cliente | Método Primario | Método Secundario | Rol PostgreSQL |
|---------|-----------------|-------------------|----------------|
| Frontend | JWT (usuario) | - | `sfera_app` |
| Agente IA | API Key | mTLS (opcional) | `sfera_ai_agent` |
| Centralita | API Key | IP Whitelist | `sfera_pbx` |

### Flujo de Autenticación - Frontend (Usuario)

```
┌──────────┐         ┌─────────┐         ┌────────────┐
│ Frontend │         │ Backend │         │ PostgreSQL │
└────┬─────┘         └────┬────┘         └─────┬──────┘
     │                    │                    │
     │ POST /auth/login   │                    │
     │ {email, password}  │                    │
     │───────────────────►│                    │
     │                    │                    │
     │                    │ validate_user()    │
     │                    │───────────────────►│
     │                    │                    │
     │                    │ set_current_user() │
     │                    │───────────────────►│
     │                    │                    │
     │                    │◄─ session_token ───│
     │                    │                    │
     │◄─── JWT ───────────│                    │
     │ (con session_token)│                    │
     │                    │                    │
```

### Flujo de Autenticación - Servicios (API Key)

```
┌───────────┐         ┌─────────┐         ┌────────────┐
│ Agente IA │         │ Backend │         │ PostgreSQL │
└─────┬─────┘         └────┬────┘         └─────┬──────┘
      │                    │                    │
      │ POST /ai/decision  │                    │
      │ X-API-Key: xxx     │                    │
      │ X-Service-ID: ai-1 │                    │
      │───────────────────►│                    │
      │                    │                    │
      │                    │ validate_api_key() │
      │                    │───────────────────►│
      │                    │                    │
      │                    │ set_service_context()
      │                    │───────────────────►│
      │                    │                    │
      │                    │ INSERT ai_decision │
      │                    │───────────────────►│
      │                    │                    │
      │◄─── 201 Created ───│                    │
      │                    │                    │
```

---

## Roles de Base de Datos

### Roles Existentes

```sql
-- Aplicación web (frontend)
sfera_app          -- SELECT, INSERT, UPDATE (limitado)

-- Solo lectura (reportes)
sfera_readonly     -- SELECT only

-- Auditor/DPO
sfera_auditor      -- SELECT en audit_log, blocked_data

-- Operaciones privilegiadas
sfera_ops          -- Rotación de claves, mantenimiento

-- Gestor de sesiones
sfera_session_manager  -- Solo set_current_user()

-- Autoridades judiciales (LOPDGDD Art. 33)
sfera_judicial_authority  -- Acceso a blocked_data
```

### Roles Nuevos Necesarios

```sql
-- Agente IA conversacional
CREATE ROLE sfera_ai_agent WITH LOGIN;
COMMENT ON ROLE sfera_ai_agent IS 'Agente IA: escritura intensiva en transcripciones, decisiones IA';

-- Permisos específicos
GRANT SELECT ON customers, contacts, calls, consents TO sfera_ai_agent;
GRANT INSERT ON transcriptions, ai_decision_logs TO sfera_ai_agent;
GRANT UPDATE ON calls (sentiment, sentiment_score, ai_summary) TO sfera_ai_agent;
GRANT EXECUTE ON FUNCTION log_ai_decision TO sfera_ai_agent;
GRANT EXECUTE ON FUNCTION check_consent_for_sentiment TO sfera_ai_agent;

-- Aplicaciones de centralita (PBX, CTI)
CREATE ROLE sfera_pbx WITH LOGIN;
COMMENT ON ROLE sfera_pbx IS 'Centralita: gestión ciclo de vida llamadas';

-- Permisos específicos
GRANT SELECT ON customers, contacts, robinson_checks TO sfera_pbx;
GRANT INSERT ON calls, call_recordings, consents TO sfera_pbx;
GRANT UPDATE ON calls (status, end_time, duration) TO sfera_pbx;
GRANT EXECUTE ON FUNCTION check_robinson_list TO sfera_pbx;
GRANT EXECUTE ON FUNCTION register_ai_disclosure TO sfera_pbx;
```

---

## Rate Limiting por Tipo de Cliente

| Cliente | Límite | Ventana | Justificación |
|---------|--------|---------|---------------|
| Frontend | 100 req | 1 min | Uso humano interactivo |
| Agente IA | 1000 req | 1 min | Alta frecuencia, llamadas simultáneas |
| Centralita | 500 req | 1 min | Eventos de llamada |

**Implementación:**

```python
# En middleware o dependency
async def get_rate_limit(request: Request) -> int:
    client_type = request.state.client_type

    limits = {
        "frontend": 100,
        "ai_agent": 1000,
        "pbx": 500,
    }

    return limits.get(client_type, 100)
```

---

## Endpoints por Tipo de Cliente

### Prefijos de API

```
/api/v1/           # Endpoints generales (frontend)
/api/v1/ai/        # Endpoints específicos agente IA
/api/v1/pbx/       # Endpoints específicos centralita
/api/v1/admin/     # Endpoints administración
/api/v1/gdpr/      # Endpoints derechos RGPD
```

### Matriz de Permisos por Endpoint

| Endpoint | Frontend | Agente IA | Centralita |
|----------|----------|-----------|------------|
| `GET /dashboard/*` | ✅ | ❌ | ❌ |
| `GET /calls` | ✅ | ❌ | ❌ |
| `GET /calls/{id}` | ✅ | ✅ (contexto) | ✅ |
| `POST /ai/transcription` | ❌ | ✅ | ❌ |
| `POST /ai/decisions` | ❌ | ✅ | ❌ |
| `POST /pbx/calls` | ❌ | ❌ | ✅ |
| `PUT /pbx/calls/{id}` | ❌ | ❌ | ✅ |
| `GET /gdpr/export` | ✅ | ❌ | ❌ |

---

## Cumplimiento Normativo por Cliente

### Agente IA - AI Act

| Artículo | Requisito | Implementación |
|----------|-----------|----------------|
| Art. 12 | Trazabilidad | Todo en `ai_decision_logs` |
| Art. 14 | Supervisión humana | Endpoint `/human-escalation` |
| Art. 50.1 | Informar interacción IA | Verificar `ai_disclosure_timestamp` |
| Art. 50.3 | Informar análisis emociones | Verificar consentimiento SENTIMENT_ANALYSIS |

**Validaciones obligatorias antes de análisis de sentimiento:**

```python
async def validate_sentiment_analysis(call_id: str, db: AsyncSession):
    """Verificar cumplimiento AI Act antes de analizar sentimiento."""

    # 1. Verificar que se informó de IA (Art. 50.1)
    result = await db.execute(
        text("""
            SELECT ai_disclosure_timestamp
            FROM calls
            WHERE id = :call_id
        """),
        {"call_id": call_id}
    )
    call = result.fetchone()

    if not call.ai_disclosure_timestamp:
        raise ComplianceError(
            "AI Act Art. 50.1: ai_disclosure_timestamp not set"
        )

    # 2. Verificar consentimiento para análisis emocional
    result = await db.execute(
        text("""
            SELECT check_active_consent(
                (SELECT customer_id FROM calls WHERE id = :call_id),
                'SENTIMENT_ANALYSIS'
            )
        """),
        {"call_id": call_id}
    )

    if not result.scalar():
        raise ComplianceError(
            "AI Act Art. 50.3: No consent for emotion detection"
        )
```

### Centralita - RGPD/LOPDGDD

| Artículo | Requisito | Implementación |
|----------|-----------|----------------|
| RGPD Art. 7 | Consentimiento grabación | Endpoint `/consent` antes de grabar |
| LOPDGDD Art. 33 | Lista Robinson | Verificar antes de llamada saliente |
| RGPD Art. 13 | Información previa | `recording_informed_timestamp` |

**Flujo obligatorio al crear llamada:**

```python
async def create_call(call_data: CallCreate, db: AsyncSession):
    """Crear llamada con verificaciones de cumplimiento."""

    # 1. Si es llamada saliente comercial, verificar Robinson
    if call_data.direction == "outbound" and call_data.purpose == "commercial":
        robinson_ok = await check_robinson(call_data.phone_number, db)
        if not robinson_ok:
            raise ComplianceError(
                "LOPDGDD: Phone number in Lista Robinson"
            )

    # 2. Crear llamada con timestamps de compliance
    call = await db.execute(
        text("""
            INSERT INTO calls (
                customer_id,
                direction,
                status,
                ai_disclosure_timestamp,  -- Se establece cuando el IVR lo anuncia
                created_at
            ) VALUES (...)
            RETURNING id
        """)
    )

    return call
```

---

## Configuración de API Keys

### Estructura de API Key

```
sfera_{client_type}_{random_32_chars}

Ejemplos:
- sfera_ai_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
- sfera_pbx_q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2
```

### Tabla de API Keys

```sql
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key_hash TEXT NOT NULL,  -- bcrypt hash, nunca almacenar en claro
    client_type VARCHAR(20) NOT NULL CHECK (client_type IN ('ai_agent', 'pbx', 'external')),
    service_name VARCHAR(100) NOT NULL,
    description TEXT,
    allowed_ips INET[],  -- Whitelist de IPs
    rate_limit_override INTEGER,
    permissions JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true,
    created_by UUID REFERENCES users(id)
);

CREATE INDEX idx_api_keys_hash ON api_keys(key_hash) WHERE is_active = true;
```

---

## Diagrama de Secuencia: Llamada Entrante Completa

```
┌────────┐  ┌────────┐  ┌─────────┐  ┌──────────┐  ┌────────────┐
│  PBX   │  │Backend │  │PostgreSQL│ │ Agente IA│  │  Frontend  │
└───┬────┘  └───┬────┘  └────┬─────┘ └────┬─────┘  └─────┬──────┘
    │           │            │            │              │
    │ 1. POST /pbx/calls     │            │              │
    │   (llamada entrante)   │            │              │
    │──────────────────────►│            │              │
    │           │            │            │              │
    │           │ INSERT call│            │              │
    │           │───────────►│            │              │
    │           │            │            │              │
    │◄── call_id ───────────│            │              │
    │           │            │            │              │
    │ 2. PUT /pbx/calls/{id}/ai-disclosure               │
    │   (IVR anuncia IA)     │            │              │
    │──────────────────────►│            │              │
    │           │            │            │              │
    │           │ UPDATE ai_disclosure_timestamp         │
    │           │───────────►│            │              │
    │           │            │            │              │
    │ 3. POST /pbx/calls/{id}/consent    │              │
    │   (cliente acepta)     │            │              │
    │──────────────────────►│            │              │
    │           │            │            │              │
    │           │ INSERT consent          │              │
    │           │───────────►│            │              │
    │           │            │            │              │
    │           │            │            │              │
    │           │   4. GET /ai/calls/{id}/context        │
    │           │◄───────────────────────│              │
    │           │            │            │              │
    │           │ SELECT customer, history│              │
    │           │───────────►│            │              │
    │           │            │            │              │
    │           │────────────────────────►│              │
    │           │   (contexto cliente)    │              │
    │           │            │            │              │
    │           │   5. POST /ai/transcription            │
    │           │◄───────────────────────│              │
    │           │   (cada segmento)       │              │
    │           │            │            │              │
    │           │ INSERT transcription    │              │
    │           │───────────►│            │              │
    │           │            │            │              │
    │           │   6. POST /ai/decisions │              │
    │           │◄───────────────────────│              │
    │           │            │            │              │
    │           │ INSERT ai_decision_logs │              │
    │           │───────────►│            │              │
    │           │            │            │              │
    │ 7. PUT /pbx/calls/{id} │            │              │
    │   (llamada finaliza)   │            │              │
    │──────────────────────►│            │              │
    │           │            │            │              │
    │           │ UPDATE call (end_time)  │              │
    │           │───────────►│            │              │
    │           │            │            │              │
    │           │            │            │   8. GET /dashboard
    │           │            │            │◄─────────────│
    │           │            │            │              │
    │           │ SELECT metrics          │              │
    │           │───────────►│            │              │
    │           │            │            │              │
    │           │─────────────────────────────────────►│
    │           │            │            │  (métricas)  │
    │           │            │            │              │
```

---

## Estado de Implementación

### Completado en `sferaai.sql` (líneas 13445-13961)

#### 1. Roles Multi-Cliente

```sql
-- Rol para Agente IA (líneas 13471-13507)
CREATE ROLE sfera_ai_agent WITH LOGIN;

-- Permisos:
GRANT SELECT ON contacts, calls, data_consents, call_processing_consents, contact_consents TO sfera_ai_agent;
GRANT INSERT ON transcriptions, ai_decision_logs TO sfera_ai_agent;
GRANT UPDATE ON calls TO sfera_ai_agent;
GRANT EXECUTE ON FUNCTION encrypt_pii_with_metadata(TEXT) TO sfera_ai_agent;

-- Rol para PBX/Centralita (líneas 13517-13549)
CREATE ROLE sfera_pbx WITH LOGIN;

-- Permisos:
GRANT SELECT ON contacts, robinson_checks, calls, data_consents, call_processing_consents, contact_consents TO sfera_pbx;
GRANT INSERT ON calls, data_consents, call_processing_consents, robinson_checks TO sfera_pbx;
GRANT UPDATE ON calls TO sfera_pbx;
GRANT EXECUTE ON FUNCTION encrypt_pii_with_metadata(TEXT) TO sfera_pbx;
```

#### 2. Seguridad (líneas 13551-13596)

```sql
-- Revocar acceso a tablas sensibles
REVOKE ALL ON secure_sessions, secure_keys, blocked_data, users FROM sfera_ai_agent;
REVOKE ALL ON secure_sessions, secure_keys, blocked_data, users FROM sfera_pbx;

-- sfera_pbx NO puede escribir transcripciones ni decisiones IA
REVOKE ALL ON transcriptions, ai_decision_logs FROM sfera_pbx;

-- Revocar funciones críticas de cifrado
REVOKE EXECUTE ON FUNCTION rotate_encryption_key(VARCHAR) FROM sfera_ai_agent, sfera_pbx;
REVOKE EXECUTE ON FUNCTION re_encrypt_all_pii(...) FROM sfera_ai_agent, sfera_pbx;
REVOKE EXECUTE ON FUNCTION get_secure_key(TEXT) FROM sfera_ai_agent, sfera_pbx;
```

#### 3. Tabla `api_keys` (líneas 13606-13662)

```sql
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key_prefix VARCHAR(20) NOT NULL,  -- Para identificación en logs
    key_hash TEXT NOT NULL,           -- bcrypt hash (NUNCA en claro)
    client_type VARCHAR(20) NOT NULL CHECK (client_type IN ('ai_agent', 'pbx', 'external', 'webhook')),
    service_name VARCHAR(100) NOT NULL,
    service_id VARCHAR(50) UNIQUE,
    allowed_ips INET[],               -- Whitelist de IPs
    rate_limit_override INTEGER,       -- Override del límite por defecto
    permissions JSONB DEFAULT '{}',
    expires_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true,
    ...
);
```

#### 4. Tabla `api_key_usage_log` (líneas 13673-13691)

```sql
CREATE TABLE api_key_usage_log (
    id BIGSERIAL PRIMARY KEY,
    api_key_id UUID NOT NULL REFERENCES api_keys(id),
    endpoint TEXT NOT NULL,
    method VARCHAR(10) NOT NULL,
    client_ip INET,
    response_status INTEGER,
    response_time_ms INTEGER,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

#### 5. Tabla `client_error_logs` (líneas 13977-14032)

Permite a los desarrolladores del backend recibir errores automáticamente desde el cliente Python:

```sql
CREATE TABLE client_error_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    api_key_id UUID REFERENCES api_keys(id) ON DELETE SET NULL,
    client_version VARCHAR(20) NOT NULL,
    environment VARCHAR(20),  -- dev, staging, prod
    error_type VARCHAR(100) NOT NULL,
    error_message TEXT NOT NULL,
    stack_trace TEXT,
    method VARCHAR(10),
    endpoint VARCHAR(255),
    request_payload JSONB,  -- Sanitizado, sin PII
    response_status INTEGER,
    response_body TEXT,
    call_id UUID REFERENCES calls(id) ON DELETE SET NULL,
    reported_from_ip INET,
    error_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    reported_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolved_by UUID REFERENCES users(id),
    resolution_notes TEXT
);

-- Permisos
GRANT INSERT ON client_error_logs TO sfera_ai_agent;
GRANT SELECT, UPDATE ON client_error_logs TO sfera_app;
```

**Endpoints asociados:**

| Método | Endpoint | Auth | Descripción |
|--------|----------|------|-------------|
| POST | `/api/v1/ai-agent/client-errors` | API Key (ai_agent) | Reportar error desde cliente |
| GET | `/api/v1/ai-agent/client-errors` | JWT (DPO/admin) | Consultar errores para debugging |

#### 6. Funciones de API Key (líneas 13724-13961)

| Función | Descripción | Acceso |
|---------|-------------|--------|
| `validate_api_key(key, ip)` | Valida API key, devuelve info servicio + rate limit | `sfera_app` |
| `create_api_key(type, name, ...)` | Crea nueva API key (devuelve texto plano UNA VEZ) | Solo `postgres` |
| `revoke_api_key(id, reason)` | Revoca API key existente | Solo `postgres` |

**Ejemplo de uso:**

```sql
-- Crear API key para agente IA
SELECT * FROM create_api_key('ai_agent', 'AI Agent Principal', 'ai-agent-1');
-- Resultado: sfera_ai_agent_3e9d5e6570dd8fbc2b6a631ad7bcbccd (guardar inmediatamente)

-- Crear API key para PBX con IP whitelist
SELECT * FROM create_api_key('pbx', 'Asterisk PBX', 'pbx-main', NULL, ARRAY['10.0.0.0/8'::INET]);

-- Validar API key
SELECT * FROM validate_api_key('sfera_ai_agent_3e9d5e6570dd8fbc2b6a631ad7bcbccd', '192.168.1.100');
-- Resultado: is_valid=true, client_type=ai_agent, rate_limit=1000
```

### Rate Limits por Defecto

| Tipo de Cliente | Límite | Ventana |
|-----------------|--------|---------|
| `ai_agent` | 1000 req/min | Alta frecuencia, llamadas simultáneas |
| `pbx` | 500 req/min | Eventos de llamada |
| `external` | 100 req/min | Integraciones externas |
| `webhook` | 200 req/min | Callbacks |

### Backend FastAPI

Implementado en `backend/app/core/api_key_auth.py`:

```python
# Dependencias pre-configuradas
ai_agent_auth = APIKeyAuth(allowed_client_types=["ai_agent"])
pbx_auth = APIKeyAuth(allowed_client_types=["pbx"])
ai_or_pbx_auth = APIKeyAuth(allowed_client_types=["ai_agent", "pbx"])
any_service_auth = APIKeyAuth()

# Uso en endpoints
@router.post("/ai/decisions")
async def create_ai_decision(
    identity: Annotated[ServiceIdentity, Depends(require_ai_agent)],
    ...
):
    # Solo accesible por agente IA
    pass
```

Schemas en:
- `backend/app/schemas/ai_agent.py` - Transcripciones, decisiones IA, sentimiento
- `backend/app/schemas/pbx.py` - Llamadas, consentimientos, grabaciones, Robinson

---

## Próximos Pasos

1. **Crear routers específicos**
   - `/api/v1/ai/` para agente IA
   - `/api/v1/pbx/` para centralita

2. **Implementar validaciones de compliance**
   - Verificación AI Act antes de sentiment
   - Verificación Robinson antes de llamada saliente
   - Verificación consentimiento antes de grabación

3. **Tests de integración**
   - Test de autenticación por API key
   - Test de rate limiting diferenciado
   - Test de permisos por rol
