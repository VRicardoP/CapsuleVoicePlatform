# Panel de Administracion Central - SferaAI

> **Estado:** Pendiente de implementacion (feature futura)
> **Ultima actualizacion:** 2026-04-14
> **Nota (2026-03-17):** Con 5 clientes desplegados, este panel es cada vez mas relevante. Especificacion valida para futura implementacion.
> **Nota (2026-04-09):** El sistema de permisos per-client ya esta implementado dentro de cada backend
> (3 roles: `superadmin`, `client_admin`, `user`; 55+ permisos; tablas via alembic).
> Feature flags controlan visibilidad de modulos; permisos controlan acceso granular por usuario.
> Este panel central complementaria el sistema existente con gestion multi-cliente.
> **Nota (2026-04-14):** Las rutas de auth aquí documentadas (`/api/auth/login`, `/api/auth/refresh`) corresponden
> a este panel central hipotético, **NO al backend de cliente**. El backend de cliente usa BFF con cookies opacas
> (`__Host-sferaai_session`); ver [`BFF_SESSIONS.md`](BFF_SESSIONS.md).

## Indice

1. [Resumen](#resumen)
2. [Problema que resuelve](#problema-que-resuelve)
3. [Arquitectura](#arquitectura)
4. [Gestion de modulos por cliente](#gestion-de-modulos-por-cliente)
5. [Health checks](#health-checks)
6. [Seguridad](#seguridad)
7. [Modelo de datos](#modelo-de-datos)
8. [Interfaz del panel](#interfaz-del-panel)
9. [Endpoints API](#endpoints-api)
10. [Despliegue](#despliegue)
11. [Escalabilidad](#escalabilidad)

---

## Resumen

Panel de administracion centralizado para gestionar todos los clientes de SferaAI desde un unico punto. Permite:

- Ver el estado (online/offline) de todos los clientes en tiempo real
- Activar y desactivar modulos del dashboard por cliente (sin reiniciar contenedores)
- Consultar que modulos tiene contratados cada cliente
- Auditar todos los cambios realizados

---

## Problema que resuelve

En la arquitectura single-tenant actual, cada cliente tiene su propio stack Docker (backend, dashboard, n8n, postgres). Sin un panel central:

- Hay que entrar en cada contenedor para gestionar modulos
- No hay visibilidad global del estado de los clientes
- No hay forma centralizada de saber que modulos tiene cada cliente
- Los cambios de modulos requieren modificar env vars y reiniciar contenedores

---

## Arquitectura

```
+-----------------------------------------------------------+
|              SFERAAI ADMIN PANEL                          |
|         admin.yourdomain.com (nuevo servicio)               |
+-----------------------------------------------------------+
|                                                           |
|  +--------------+   +--------------+   +--------------+   |
|  |   React UI   |   |  FastAPI     |   |  PostgreSQL  |   |
|  |  (frontend)  |-->|  (admin-api) |-->|  (admin-db)  |   |
|  +--------------+   +------+-------+   +--------------+   |
|                            |                              |
+----------------------------+------------------------------+
                             |
              +--------------+--------------+
              |              |              |
              v              v              v
     +--------------+ +--------------+ +--------------+
     |   Acme     | |  Cliente 2   | |  Cliente N   |
     |  Santander   | |              | |              |
     |  +--------+  | |  +--------+  | |  +--------+  |
     |  |backend |<-+-+  |backend |<-+-+  |backend |  |
     |  |:8000   |  | |  |:8000   |  | |  |:8000   |  |
     |  +--------+  | |  +--------+  | |  +--------+  |
     +--------------+ +--------------+ +--------------+
         red proxy         red proxy        red proxy
```

### Componentes

| Componente | Tecnologia | Funcion |
|------------|-----------|---------|
| Admin Frontend | React + TailwindCSS | Interfaz web del panel |
| Admin API | FastAPI (Python) | Logica de negocio, comunicacion con clientes |
| Admin DB | PostgreSQL | Almacena clientes, modulos, audit log |
| Cliente Backend | FastAPI (existente) | Recibe y aplica configuracion de modulos |

### Comunicacion

- **Admin API -> Cliente Backend**: HTTP interno via red Docker `proxy` (no expuesto a internet)
- **Admin Frontend -> Admin API**: HTTPS via Traefik (expuesto en `admin.yourdomain.com`)
- **Health checks**: HTTP polling cada 30 segundos a cada backend del cliente

---

## Gestion de modulos por cliente

### Filosofia: dos niveles de filtrado

```
ENABLED_MODULES (nivel cliente)     <-- Admin panel controla esto
        |
        v
visible_modules (nivel usuario)     <-- Cada usuario elige dentro de lo permitido
        |
        v
Modulos que ve el usuario final
```

- **Nivel cliente** (`enabled_modules`): Que modulos tiene contratados/activos el cliente. Controlado exclusivamente desde el admin panel.
- **Nivel usuario** (`visible_modules`): Dentro de los modulos activos del cliente, cada usuario puede personalizar cuales quiere ver. Almacenado en `user_preferences` del backend del cliente.

### Flujo de activacion/desactivacion

```
Admin Panel                Admin API              Cliente Backend
    |                          |                        |
    |  PUT /clients/{id}/      |                        |
    |  modules                 |                        |
    |  ["calls", "stats"]      |                        |
    |------------------------->|                        |
    |                          |                        |
    |                          |  1. Guardar en admin DB|
    |                          |                        |
    |                          |  2. POST /api/v1/      |
    |                          |  internal/sync-modules |
    |                          |  (firmado con HMAC)    |
    |                          |----------------------->|
    |                          |                        |
    |                          |                        | 3. Validar firma
    |                          |                        | 4. Guardar en BD local
    |                          |                        | 5. Responder OK
    |                          |                        |
    |                          |       200 OK           |
    |                          |<-----------------------|
    |                          |                        |
    |                          |  6. Registrar en       |
    |                          |     audit log          |
    |                          |                        |
    |   Modulos actualizados   |                        |
    |<-------------------------|                        |
```

### Efecto inmediato (sin reiniciar contenedores)

El dashboard del cliente consulta `GET /api/v1/config/modules` al cargar la pagina. El backend lee de su BD local que modulos estan activos. Cuando el admin cambia los modulos, el backend actualiza su BD y el siguiente refresh del dashboard ya muestra los cambios.

### Enforcement en backend del cliente

Ademas de no mostrar los modulos en el frontend, el backend debe rechazar peticiones a endpoints de modulos desactivados:

```python
# Middleware de verificacion de modulos
@router.get("/api/v1/dashboard/call-stats")
async def call_stats(modules=Depends(get_enabled_modules)):
    if "call_stats" not in modules:
        raise HTTPException(403, "Module not enabled for this client")
    # ... logica normal
```

Esto impide que alguien llame directamente a la API de un modulo desactivado.

---

## Health checks

### Metodo: HTTP polling (recomendado)

Cada backend del cliente ya expone `GET /health` que devuelve `200 OK` cuando el servicio esta operativo.

El admin-api hace polling cada 30 segundos:

```
http://acme-dental-backend:8000/health  -> 200 OK (healthy)
http://cliente2-backend:8000/health          -> 200 OK (healthy)
http://cliente3-backend:8000/health          -> timeout  (unhealthy)
```

### Ventajas sobre montar Docker socket

| Aspecto | Docker Socket | HTTP Health |
|---------|--------------|-------------|
| Acoplamiento | Alto (requiere acceso al daemon) | Bajo (HTTP estandar) |
| Multi-servidor | No funciona | Funciona igual |
| Seguridad | Acceso root equivalente | Solo lectura de health |
| Informacion | Estado del contenedor | Estado real de la aplicacion |

### Datos almacenados

```sql
-- En admin DB
UPDATE clients
SET last_health_check = now(),
    is_healthy = true,  -- o false si timeout/error
    health_response_ms = 45
WHERE id = 'acme-dental';
```

---

## Seguridad

### Principios generales

1. **Defensa en profundidad**: Multiples capas de seguridad independientes
2. **Zero trust**: Cada peticion se verifica, incluso en la red interna
3. **Minimo privilegio**: Cada componente solo tiene acceso a lo que necesita
4. **Auditoria completa**: Toda accion queda registrada e inmutable

### Capa 1: Restriccion de red

El admin panel solo es accesible desde IPs autorizadas.

**Opcion A - IP Whitelist en Traefik (simple):**

```yaml
# docker-compose del admin panel
labels:
  - "traefik.http.middlewares.admin-ipwhitelist.ipwhitelist.sourcerange=95.61.246.84/32,OTRA_IP/32"
  - "traefik.http.routers.admin.middlewares=admin-ipwhitelist"
```

**Opcion B - VPN WireGuard (mas segura):**

El admin panel solo escucha en la interfaz WireGuard (`10.0.0.0/24`). No es accesible desde internet publico.

### Capa 2: Autenticacion MFA obligatoria

| Aspecto | Configuracion |
|---------|--------------|
| Metodo | Email + contrasena + TOTP |
| TOTP | Google Authenticator / Authy (obligatorio, sin excepcion) |
| Contrasena minima | 12 caracteres |
| Hash | bcrypt con factor 12 |
| Registro | Solo pre-registrado (no hay signup publico) |

### Capa 3: Sesiones con tokens cortos

```
JWT Access Token:  15 min TTL
  - Almacenado en memoria del navegador (NO localStorage, NO cookies accesibles por JS)
  - Contiene: user_id, email, role, exp, iat

Refresh Token:  7 dias TTL
  - HttpOnly cookie
  - Secure flag (solo HTTPS)
  - SameSite=Strict
  - Rotacion en cada uso (el refresh token anterior se invalida)
```

### Capa 4: Roles y permisos (RBAC)

**Roles del Admin Panel (este documento):**

| Rol | Crear clientes | Activar/desactivar modulos | Ver estado | Ver audit log |
|-----|:-:|:-:|:-:|:-:|
| `superadmin` | Si | Si | Si | Si |
| `billing` | No | Si | Si | Si |
| `viewer` | No | No | Si | No |

**Roles per-client (ya implementados en cada backend):**

| Rol | Descripcion |
|-----|-------------|
| `super_admin` | Acceso total, gestion de usuarios y permisos |
| `client_admin` | Administrador del cliente, acceso a toda la configuracion |
| `agent` | Operador con acceso limitado segun permisos asignados |

> El sistema per-client usa 55 permisos granulares sobre 11 recursos.
> Tablas: `roles`, `permissions`, `role_permissions`, `user_roles` (creadas via alembic).

### Capa 5: Comunicacion Admin -> Cliente (firma HMAC)

La comunicacion entre el admin-api y los backends de los clientes usa firma HMAC-SHA256 con proteccion anti-replay.

**Cada cliente tiene su propia `ADMIN_SHARED_SECRET`** (64 caracteres aleatorios, generada al crear el cliente). No se comparte entre clientes. Si un secret se compromete, solo afecta a un cliente.

#### Estructura de la peticion firmada

```
POST /api/v1/internal/sync-modules HTTP/1.1
Host: acme-dental-backend:8000
Content-Type: application/json
X-Admin-Signature: <hmac_sha256>
X-Admin-Timestamp: <unix_timestamp>
X-Admin-Nonce: <uuid_unico>

{"enabled_modules": ["recent_calls", "call_stats", "ai_analytics"]}
```

#### Calculo de la firma (lado admin-api)

```python
import hmac, hashlib, time, uuid

def sign_request(body: bytes, secret: str) -> tuple[str, str, str]:
    timestamp = str(int(time.time()))
    nonce = str(uuid.uuid4())

    # Mensaje = timestamp.nonce.body
    message = f"{timestamp}.{nonce}.{body.decode()}".encode()
    signature = hmac.new(
        secret.encode(), message, hashlib.sha256
    ).hexdigest()

    return signature, timestamp, nonce
```

#### Verificacion (lado cliente backend)

```python
import hmac, hashlib, time

MAX_TIMESTAMP_DRIFT = 300  # 5 minutos
used_nonces: set = set()   # En produccion: Redis con TTL de 10 min

def verify_admin_request(signature: str, timestamp: str, nonce: str,
                         body: bytes, secret: str) -> bool:
    # 1. Verificar timestamp dentro de ventana (anti-replay)
    if abs(time.time() - int(timestamp)) > MAX_TIMESTAMP_DRIFT:
        return False  # Peticion expirada

    # 2. Verificar nonce no repetido (anti-replay doble capa)
    if nonce in used_nonces:
        return False  # Peticion duplicada
    used_nonces.add(nonce)

    # 3. Verificar firma HMAC
    expected = hmac.new(
        secret.encode(),
        f"{timestamp}.{nonce}.{body.decode()}".encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected)
```

#### Protecciones de la firma HMAC

| Ataque | Proteccion |
|--------|-----------|
| Interceptacion | El secret nunca viaja en la peticion, solo la firma |
| Modificacion del body | La firma incluye el body; cualquier cambio invalida la firma |
| Replay attack | Timestamp con ventana de 5 min + nonce unico |
| Fuerza bruta | HMAC-SHA256 con secret de 64 chars = computacionalmente inviable |
| Compromiso lateral | Secret independiente por cliente |

### Capa 6: Endpoint interno no expuesto

El path `/api/v1/internal/*` de los backends de los clientes **no esta expuesto a internet**. Solo es accesible desde la red Docker interna (`proxy`).

```yaml
# Traefik label del backend del cliente
# Solo expone /api/v1/* excepto /api/v1/internal/*
- "traefik.http.routers.${CLIENT_ID}-api.rule=Host(`${CLIENT_DOMAIN}`) && PathPrefix(`/api`) && !PathPrefix(`/api/v1/internal`)"
```

Desde internet, `https://dominio.com/api/v1/internal/sync-modules` devuelve 404 (Traefik no lo rutea). Solo el admin-api puede alcanzarlo via `http://acme-dental-backend:8000/api/v1/internal/sync-modules` dentro de Docker.

### Capa 7: Proteccion contra auto-activacion

Un cliente (o alguien con acceso a su dashboard) no puede activarse modulos:

1. **Red**: El endpoint `/internal/sync-modules` no es accesible desde internet
2. **Firma**: Aunque accediera, sin el `ADMIN_SHARED_SECRET` no puede firmar la peticion
3. **Backend enforce**: Incluso si manipulara el frontend, el backend rechaza peticiones a endpoints de modulos desactivados con 403
4. **Fuente de verdad**: La configuracion de modulos se almacena en la BD del admin (fuera del control del cliente)

### Capa 8: Auditoria inmutable

Toda accion en el admin panel queda registrada:

```sql
CREATE TABLE module_audit_log (
    id SERIAL PRIMARY KEY,
    client_id TEXT NOT NULL,
    module_id TEXT NOT NULL,
    action TEXT NOT NULL,            -- 'enabled' o 'disabled'
    performed_by TEXT NOT NULL,       -- email del admin
    performed_at TIMESTAMPTZ DEFAULT now(),
    ip_address INET,
    user_agent TEXT,
    previous_state BOOLEAN,
    new_state BOOLEAN,
    reason TEXT                       -- opcional: "Cliente contrato plan Pro"
);

-- Solo INSERT, nunca UPDATE ni DELETE
-- Politica de retencion: minimo 5 anios (requisito RGPD Art. 30)
```

### Resumen de capas de seguridad

```
Capa                              Protege contra
---------------------------------------------------------------
1. IP whitelist / VPN             Acceso no autorizado al admin
2. MFA obligatorio (TOTP)         Credenciales robadas
3. JWT corto (15 min)             Tokens comprometidos
4. Roles (superadmin/billing)     Escalacion de privilegios
5. HMAC por cliente               Peticiones falsificadas
6. /internal/* no expuesto        Acceso externo al endpoint
7. Backend enforce modules        Manipulacion del frontend
8. Audit log inmutable            Negacion de acciones
```

### Que NO hacer

- **No usar API keys simples** en headers para la comunicacion admin->cliente. Son estaticas, no protegen contra replay, y si se filtran dan acceso permanente.
- **No confiar en el frontend** para decidir que modulos mostrar. Siempre enforce en backend.
- **No compartir secrets entre clientes**. Un secret por cliente, rotable independientemente.
- **No exponer el admin panel sin restriccion de red**. MFA es necesario pero no suficiente como unica barrera.
- **No almacenar JWT en localStorage**. Vulnerable a XSS.

---

## Modelo de datos

### Base de datos del Admin Panel

```sql
-- Tabla de administradores del panel
CREATE TABLE admins (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    totp_secret TEXT,                -- Secret para TOTP (encriptado)
    totp_enabled BOOLEAN DEFAULT false,
    role TEXT NOT NULL DEFAULT 'viewer',  -- superadmin, billing, viewer
    is_active BOOLEAN DEFAULT true,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Tabla de clientes
CREATE TABLE clients (
    id TEXT PRIMARY KEY,             -- 'acme-dental'
    name TEXT NOT NULL,              -- 'Acme Dental'
    domain TEXT NOT NULL,            -- 'acmedental.dashboard.yourdomain.com'
    backend_internal_url TEXT,       -- 'http://acme-dental-backend:8000'
    admin_shared_secret TEXT NOT NULL, -- Secret HMAC (64 chars, unico por cliente)
    status TEXT DEFAULT 'active',    -- active, suspended, trial
    plan TEXT DEFAULT 'basic',       -- basic, pro, enterprise
    last_health_check TIMESTAMPTZ,
    is_healthy BOOLEAN DEFAULT true,
    health_response_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Tabla de modulos contratados por cliente
CREATE TABLE client_modules (
    client_id TEXT REFERENCES clients(id) ON DELETE CASCADE,
    module_id TEXT NOT NULL,          -- 'recent_calls', 'call_stats', etc.
    is_active BOOLEAN DEFAULT true,
    contracted_at TIMESTAMPTZ DEFAULT now(),
    expires_at TIMESTAMPTZ,           -- NULL = sin caducidad
    PRIMARY KEY (client_id, module_id)
);

-- Catalogo de modulos disponibles
CREATE TABLE modules (
    id TEXT PRIMARY KEY,              -- 'recent_calls'
    name TEXT NOT NULL,               -- 'Ultimas Llamadas'
    category TEXT NOT NULL,           -- 'calls', 'analytics', 'compliance', 'crm', 'settings'
    description TEXT,
    is_default BOOLEAN DEFAULT false, -- Incluido en todos los planes
    sort_order INTEGER DEFAULT 0
);

-- Audit log (inmutable: solo INSERT)
CREATE TABLE module_audit_log (
    id SERIAL PRIMARY KEY,
    client_id TEXT NOT NULL,
    module_id TEXT NOT NULL,
    action TEXT NOT NULL,
    performed_by TEXT NOT NULL,
    performed_at TIMESTAMPTZ DEFAULT now(),
    ip_address INET,
    user_agent TEXT,
    previous_state BOOLEAN,
    new_state BOOLEAN,
    reason TEXT
);
```

### Tabla en la BD de cada cliente

```sql
-- Añadir a la BD de cada cliente (acme-dental, etc.)
CREATE TABLE client_config (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Ejemplo de registro:
-- key: 'enabled_modules'
-- value: '["recent_calls", "call_stats", "ai_analytics", "appointments"]'
```

### Catalogo de modulos

Basado en los 15 modulos existentes en `dashboard/src/config/modulesConfig.ts`:

| ID | Nombre | Categoria | Plan default |
|----|--------|-----------|-------------|
| `recent_calls` | Ultimas Llamadas | calls | basic |
| `call_stats` | Estadisticas | calls | basic |
| `ai_analytics` | Analisis IA | analytics | pro |
| `call_volume` | Volumen Llamadas | analytics | pro |
| `sentiment_analysis` | Analisis Experiencia | analytics | pro |
| `appointments` | Citas del Dia | crm | basic |
| `appointment_calendar` | Calendario Citas | crm | pro |
| `customer_directory` | Directorio Clientes | crm | pro |
| `gdpr_summary` | Resumen RGPD | compliance | basic |
| `gdpr_metrics` | Metricas RGPD | compliance | pro |
| `gdpr_trends` | Tendencias RGPD | compliance | enterprise |
| `consent_management` | Gestion Consentimientos | compliance | pro |
| `recording_management` | Gestion Grabaciones | compliance | pro |
| `robinson_check` | Lista Robinson | compliance | enterprise |
| `kpi_dashboard` | KPIs Avanzados | analytics | enterprise |

---

## Interfaz del panel

### Vista principal: Lista de clientes

```
+-------------------------------------------------------+
|  SferaAI Admin                     admin@yourdomain.com |
+-------------------------------------------------------+
|                                                       |
|  Clientes activos (3)                     [+ Nuevo]   |
|  +---------------------------------------------------+
|  | Estado | Cliente            | Modulos | Plan       |
|  |--------|--------------------|---------|------------|
|  | OK     | Acme Dental   | 5 / 15  | Pro        |
|  | OK     | Cliente Madrid     | 3 / 15  | Basic      |
|  | ERROR  | Cliente Valencia   | 8 / 15  | Enterprise |
|  +---------------------------------------------------+
|                                                       |
+-------------------------------------------------------+
```

### Vista detalle: Modulos de un cliente

```
+-------------------------------------------------------+
|  SferaAI Admin > Acme Dental                     |
+-------------------------------------------------------+
|                                                       |
|  Estado: OK (45ms)    Plan: Pro    Desde: 2026-02-09  |
|                                                       |
|  -- Llamadas --                                       |
|  [x] Ultimas Llamadas              (basico)           |
|  [x] Estadisticas de Llamadas      (basico)           |
|                                                       |
|  -- Analitica --                                      |
|  [x] Analisis IA                   (pro)              |
|  [ ] Volumen de Llamadas           (pro)              |
|  [ ] Analisis de Experiencia       (pro)              |
|  [ ] KPIs Avanzados                (enterprise)       |
|                                                       |
|  -- CRM --                                            |
|  [x] Citas del Dia                 (basico)           |
|  [x] Calendario de Citas           (pro)              |
|  [ ] Directorio de Clientes        (pro)              |
|                                                       |
|  -- Compliance --                                     |
|  [ ] Resumen RGPD                  (basico)           |
|  [ ] Metricas RGPD                 (pro)              |
|  [ ] Tendencias RGPD               (enterprise)       |
|  [ ] Gestion Consentimientos       (pro)              |
|  [ ] Gestion Grabaciones           (pro)              |
|  [ ] Lista Robinson                (enterprise)       |
|                                                       |
|  Razon del cambio: [________________]                 |
|                                                       |
|  [Guardar cambios]    [Cancelar]                      |
|                                                       |
|  -- Historial reciente --                             |
|  2026-02-11 10:30  admin@yourdomain.com  +ai_analytics |
|  2026-02-09 15:00  admin@yourdomain.com  +recent_calls |
|  2026-02-09 15:00  admin@yourdomain.com  +call_stats   |
|                                                       |
+-------------------------------------------------------+
```

---

## Endpoints API

### Admin API (admin.yourdomain.com)

| Metodo | Path | Descripcion | Rol minimo |
|--------|------|-------------|-----------|
| POST | `/api/auth/login` | Login con email + password | - |
| POST | `/api/auth/verify-totp` | Verificar codigo TOTP | - |
| POST | `/api/auth/refresh` | Renovar access token | - |
| GET | `/api/clients` | Listar todos los clientes | viewer |
| GET | `/api/clients/{id}` | Detalle de un cliente | viewer |
| POST | `/api/clients` | Crear nuevo cliente | superadmin |
| PUT | `/api/clients/{id}/modules` | Actualizar modulos activos | billing |
| GET | `/api/clients/{id}/modules` | Ver modulos de un cliente | viewer |
| GET | `/api/clients/{id}/audit` | Ver historial de cambios | superadmin |
| GET | `/api/modules` | Catalogo de modulos disponibles | viewer |
| GET | `/api/health/all` | Estado de todos los clientes | viewer |

### Endpoint interno en cada backend de cliente

| Metodo | Path | Descripcion | Autenticacion |
|--------|------|-------------|--------------|
| POST | `/api/v1/internal/sync-modules` | Recibe modulos activos desde admin | HMAC signature |
| GET | `/api/v1/config/modules` | Devuelve modulos activos (usado por dashboard) | JWT del usuario |

---

## Despliegue

### Docker Compose del Admin Panel

```yaml
# /opt/sferaai/admin/docker-compose.yml
version: '3.8'

services:
  admin-db:
    image: postgres:16-alpine
    container_name: sferaai-admin-db
    restart: unless-stopped
    environment:
      POSTGRES_DB: sferaai_admin
      POSTGRES_USER: ${ADMIN_DB_USER}
      POSTGRES_PASSWORD: ${ADMIN_DB_PASSWORD}
    volumes:
      - ./data/postgres:/var/lib/postgresql/data
    networks:
      - admin-internal
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${ADMIN_DB_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  admin-api:
    image: sferaai-admin-api:latest
    container_name: sferaai-admin-api
    restart: unless-stopped
    environment:
      DATABASE_URL: postgresql+asyncpg://${ADMIN_DB_USER}:${ADMIN_DB_PASSWORD}@admin-db:5432/sferaai_admin
      JWT_SECRET: ${ADMIN_JWT_SECRET}
      HEALTH_CHECK_INTERVAL: 30
    depends_on:
      admin-db:
        condition: service_healthy
    networks:
      - admin-internal
      - proxy          # Para comunicarse con backends de clientes
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.admin-api.rule=Host(`admin.yourdomain.com`) && PathPrefix(`/api`)"
      - "traefik.http.routers.admin-api.entrypoints=https"
      - "traefik.http.routers.admin-api.tls=true"
      - "traefik.http.routers.admin-api.tls.certresolver=letsencrypt"
      - "traefik.http.routers.admin-api.priority=200"
      - "traefik.http.middlewares.admin-ipwhitelist.ipwhitelist.sourcerange=${ADMIN_ALLOWED_IPS}"
      - "traefik.http.routers.admin-api.middlewares=admin-ipwhitelist"
      - "traefik.http.services.admin-api.loadbalancer.server.port=8000"
      - "traefik.docker.network=proxy"

  admin-dashboard:
    image: sferaai-admin-dashboard:latest
    container_name: sferaai-admin-dashboard
    restart: unless-stopped
    networks:
      - proxy
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.admin-dashboard.rule=Host(`admin.yourdomain.com`)"
      - "traefik.http.routers.admin-dashboard.entrypoints=https"
      - "traefik.http.routers.admin-dashboard.tls=true"
      - "traefik.http.routers.admin-dashboard.tls.certresolver=letsencrypt"
      - "traefik.http.routers.admin-dashboard.priority=100"
      - "traefik.http.middlewares.admin-dashboard-ipwhitelist.ipwhitelist.sourcerange=${ADMIN_ALLOWED_IPS}"
      - "traefik.http.routers.admin-dashboard.middlewares=admin-dashboard-ipwhitelist"
      - "traefik.http.services.admin-dashboard.loadbalancer.server.port=80"
      - "traefik.docker.network=proxy"

networks:
  admin-internal:
    driver: bridge
  proxy:
    external: true
    name: proxy
```

### Cambios necesarios en el backend de cada cliente

1. **Nuevo endpoint** `POST /api/v1/internal/sync-modules` (protegido por HMAC)
2. **Nueva tabla** `client_config` en la BD del cliente
3. **Nuevo endpoint** `GET /api/v1/config/modules` (protegido por JWT)
4. **Middleware** de verificacion de modulos en cada endpoint de dashboard
5. **Nueva env var** `ADMIN_SHARED_SECRET` en el docker-compose del cliente
6. **Regla Traefik actualizada** para excluir `/api/v1/internal/*` de la exposicion publica

---

## Escalabilidad

### Situacion actual (1-5 clientes)

Todo en un servidor (YOUR_SERVER_IP). El admin panel se despliega como un stack mas en el mismo servidor.

### Escalado medio (5-20 clientes)

Mismo servidor pero con monitorizacion (Prometheus + Grafana opcional). El admin panel gestiona todos los clientes desde la red `proxy` compartida.

### Escalado alto (20+ clientes, multi-servidor)

- Los clientes pueden estar en servidores diferentes
- El health check pasa de HTTP interno a HTTPS publico (via dominio del cliente)
- La comunicacion admin->cliente pasa de red Docker interna a HTTPS con mutual TLS o VPN
- Considerar un message broker (Redis pub/sub) para propagacion de cambios

### Migracion progresiva

1. **Fase 1**: Implementar admin panel en el servidor actual
2. **Fase 2**: Añadir health monitoring y audit log
3. **Fase 3**: Cuando haya necesidad multi-servidor, migrar comunicacion a HTTPS publico con mTLS

---

## Referencias

- [Modulos del dashboard](../dashboard/src/config/modulesConfig.ts) - Catalogo de 15 modulos
- [Template docker-compose](../infraestructura/cliente-template/docker-compose.yml) - Plantilla de despliegue por cliente
