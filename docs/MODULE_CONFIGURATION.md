# Configuracion de Modulos - SferaAI

> Documento estandar para configurar cualquier modulo en cualquier cliente.
> Cada seccion es autocontenida: no es necesario consultar configuraciones de otros clientes.
> Ultima actualizacion: 2026-04-14

---

## Indice

1. [Modulo Voz IA (Ultravox + Zadarma)](#1-modulo-voz-ia-ultravox--zadarma)
2. [Modulo WhatsApp Business](#2-modulo-whatsapp-business)
3. [Modulo Calendario (Cal.com)](#3-modulo-calendario-calcom)
4. [Modulo Captacion](#4-modulo-captacion)
5. [Modulo Newsletter](#5-modulo-newsletter)
6. [Referencia: Feature Flags](#6-referencia-feature-flags)

---

## 1. Modulo Voz IA (Ultravox + Zadarma)

### Descripcion

Permite llamadas entrantes y salientes con agentes de voz IA. Ultravox gestiona la IA conversacional. Zadarma proporciona el trunk SIP (numero de telefono + originar llamadas).

### Variables de entorno

#### En `.env`

```env
VOICE_PROVIDER=ultravox

# Ultravox (OBLIGATORIO para voz IA)
ULTRAVOX_API_KEY=              # Panel Ultravox > Settings > API Keys
ULTRAVOX_WEBHOOK_SECRET=       # Panel Ultravox > Settings > Webhooks

# Zadarma (OBLIGATORIO para telefonia)
ZADARMA_API_KEY=               # Panel Zadarma > Settings > API
ZADARMA_API_SECRET=            # Panel Zadarma > Settings > API
```

#### En `docker-compose.yml` (backend)

```yaml
environment:
  VOICE_PROVIDER: ${VOICE_PROVIDER:-ultravox}
  ULTRAVOX_API_KEY: ${ULTRAVOX_API_KEY:-}
  ULTRAVOX_WEBHOOK_SECRET: ${ULTRAVOX_WEBHOOK_SECRET:-}
  ZADARMA_API_KEY: ${ZADARMA_API_KEY:-}
  ZADARMA_API_SECRET: ${ZADARMA_API_SECRET:-}
```

#### En `docker-compose.yml` (worker)

```yaml
environment:
  ULTRAVOX_API_KEY: ${ULTRAVOX_API_KEY:-}
  ZADARMA_API_KEY: ${ZADARMA_API_KEY:-}
  ZADARMA_API_SECRET: ${ZADARMA_API_SECRET:-}
```

#### Variables opcionales (llamadas salientes con SIP directo)

```env
ZADARMA_SIP_USER=              # Usuario SIP para originar llamadas
ZADARMA_SIP_PASSWORD=          # Password SIP
ZADARMA_SIP_SERVER=sip.zadarma.com
ZADARMA_CALLER_ID=             # Numero que ve el destinatario (+34XXXXXXXXX)
ULTRAVOX_AGENT_ID=             # ID del agente Ultravox (para outbound via worker)
```

### Configuracion de Ultravox

1. Ir a https://app.ultravox.ai
2. Crear un agente de voz con el prompt adecuado para el negocio del cliente
3. Activar `recordingEnabled: true` si se quieren grabaciones
4. Configurar webhook:
   - URL: `https://{dominio}/api/v1/ultravox/webhook`
   - Evento: `call.ended`
   - Secret: el valor de `ULTRAVOX_WEBHOOK_SECRET`
5. Anotar el `Agent ID` (necesario para llamadas salientes)

### Configuracion de Zadarma

1. Crear numero virtual en Zadarma para el cliente
2. Configurar redireccion del numero a Ultravox SIP
3. Anotar API Key y API Secret

### Deteccion automatica de direccion

El backend detecta la direccion de cada llamada automaticamente desde los datos SIP:

- `sip.incoming` → llamada entrante (inbound)
- `sip.outgoing` → llamada saliente (outbound)
- Sin SIP → inbound por defecto

No requiere configuracion adicional.

### Grabaciones

Las grabaciones se habilitan con:

```env
RECORDING_ENABLED=true
RECORDING_ENCRYPTION_KEY=      # Generar con: python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
RECORDING_CLIENT_ID={client_id}
RECORDINGS_BASE_PATH=/opt/sferaai/data/recordings
RECORDING_RETENTION_DAYS=3     # Dias antes de auto-eliminar (default: 3)
```

Volumenes necesarios en `docker-compose.yml` (backend + worker):

```yaml
volumes:
  - ./data/recordings:/opt/sferaai/data/recordings
```

Permisos en el servidor:

```bash
chown -R 999:999 /opt/sferaai/clientes/{client_id}/data/recordings
```

### Verificacion

```bash
# Verificar que el webhook responde
curl -s https://{dominio}/api/v1/ultravox/webhook -X POST \
  -H "Content-Type: application/json" -d '{}' 2>&1
# Debe devolver error de firma (no 404)

# Verificar llamada de prueba
# Realizar una llamada al numero Zadarma del cliente
# Verificar en dashboard que aparece la llamada
```

---

## 2. Modulo WhatsApp Business

### Descripcion

Modulo completo de mensajeria WhatsApp: inbox, contactos, templates, campanas, segmentos. Usa la API Cloud de Meta (v21.0) con SSE para real-time.

### Requisitos previos del cliente

El cliente necesita proporcionar o crear:

1. **Meta Business Account** verificada
   - Crear en https://business.facebook.com/
   - Completar verificacion del negocio

2. **App de Meta** tipo Business
   - Crear en https://developers.facebook.com/apps/
   - Agregar el producto WhatsApp

3. **Numero de WhatsApp**
   - NO puede estar registrado en WhatsApp personal
   - Se puede usar numero nuevo o migrar existente

4. **System User Token** (no expira)
   - Meta Business Suite > Settings > Users > System Users
   - Crear System User con rol Admin
   - Generate New Token con permisos:
     - `whatsapp_business_messaging`
     - `whatsapp_business_management`
   - Copiar token (empieza por `EAA...`)

5. **App Secret**
   - Meta for Developers > App > Settings > Basic > Show
   - String hexadecimal de 32 caracteres

6. **Phone Number ID**
   - Meta > App > WhatsApp > API Setup > seccion "From"

7. **Business Account ID (WABA)**
   - Visible en la URL o seccion "WhatsApp Business Account"

### Variables de entorno

#### En `.env`

```env
# Generar verify token:  openssl rand -hex 16
WHATSAPP_WEBHOOK_VERIFY_TOKEN=
# Obtener de Meta > App > Settings > Basic
WHATSAPP_APP_SECRET=
```

#### En `docker-compose.yml` (backend)

```yaml
environment:
  WHATSAPP_WEBHOOK_VERIFY_TOKEN: ${WHATSAPP_WEBHOOK_VERIFY_TOKEN:-}
  WHATSAPP_APP_SECRET: ${WHATSAPP_APP_SECRET:-}
```

### Volumenes adicionales (docker-compose.yml, backend)

Para servir imagenes de templates con header IMAGE:

```yaml
volumes:
  - ./data/media:/opt/sferaai/data/media:ro
```

### Labels Traefik adicionales (docker-compose.yml, backend)

Ruta `/media` para servir imagenes de templates:

```yaml
labels:
  # ... labels existentes de /api ...
  - "traefik.http.routers.{client_id}-media.rule=Host(`{dominio}`) && PathPrefix(`/media`)"
  - "traefik.http.routers.{client_id}-media.tls=true"
  - "traefik.http.routers.{client_id}-media.entrypoints=https"
  - "traefik.http.routers.{client_id}-media.tls.certresolver=letsencrypt"
  - "traefik.http.routers.{client_id}-media.service={client_id}-api"
  - "traefik.http.routers.{client_id}-media.priority=200"
```

### Feature flag

Activar WhatsApp en la organizacion:

```sql
UPDATE organizations
SET settings = settings || '{"whatsapp_enabled": true}'::jsonb
WHERE slug = '{client_id}';
```

O al crear la organizacion, incluir `"whatsapp_enabled": true` en el campo `settings`.

### Configuracion en base de datos

Insertar fila en `wa_tenant_settings`:

```sql
-- Obtener Organization ID
SELECT id FROM organizations WHERE slug = '{client_id}';

-- Insertar configuracion WhatsApp
INSERT INTO wa_tenant_settings (
    id, tenant_id, phone_number_id, business_account_id,
    api_token_enc, webhook_verify_token, app_secret,
    display_phone, display_name, quality_rating, messaging_limit,
    is_active, created_at, updated_at
) VALUES (
    gen_random_uuid(),
    '{ORG_ID}',                      -- Organization ID obtenido arriba
    '{PHONE_NUMBER_ID}',             -- De Meta > API Setup
    '{BUSINESS_ACCOUNT_ID}',         -- De Meta > WABA
    '{SYSTEM_USER_TOKEN}',           -- Token EAA... generado
    '{WEBHOOK_VERIFY_TOKEN}',        -- El mismo del .env
    '{APP_SECRET}',                  -- El mismo del .env
    '{+34 XXX XX XX XX}',            -- Numero con formato internacional
    '{Nombre del negocio}',          -- Nombre que se muestra en WhatsApp
    'GREEN',                         -- Rating inicial
    'TIER_1K',                       -- Limite inicial (1000 msgs/dia)
    true,
    NOW(),
    NOW()
);
```

### Registrar webhook en Meta

1. Meta for Developers > App > WhatsApp > Configuration
2. Seccion Webhook > Edit
3. Rellenar:
   - **Callback URL**: `https://{dominio}/api/v1/whatsapp/webhooks/meta`
   - **Verify token**: el valor de `WHATSAPP_WEBHOOK_VERIFY_TOKEN` del `.env`
4. Click "Verify and Save"
5. Suscribirse a eventos:
   - `messages` (OBLIGATORIO): mensajes entrantes + delivery/read status
   - `message_template_status_update` (OBLIGATORIO): aprobacion/rechazo de plantillas
   - `messaging_handovers` (recomendado): traspasos entre agentes

### Sincronizar templates

Desde el dashboard: seccion WhatsApp > Plantillas > boton "Sincronizar desde Meta"

O via API.

**Automatización / scripts CI** (recomendado): usar un API token emitido desde el dashboard. Ver [`BFF_SESSIONS.md`](BFF_SESSIONS.md#api-tokens-automatización--ci) para cómo emitirlo.

```bash
# Token emitido una vez desde el panel (POST /auth/api-token), guardado como secret
export SFERAAI_API_TOKEN=sferaai_at_xxxxxxxxxxxxx

curl -s -X POST "https://{dominio}/api/v1/whatsapp/templates/sync" \
  -H "Authorization: Bearer ${SFERAAI_API_TOKEN}"
```

**Sesión interactiva (curl con cookies)**: si necesitas un shell "one-shot" sin emitir un API token, el flujo BFF se puede recorrer con `curl -c` / `-b`:

```bash
# Login — guarda las cookies (__Host-sferaai_session + sferaai_csrf) en un jar
curl -s -c /tmp/sfera-cookies.txt -X POST "https://{dominio}/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"{admin_email}","password":"{admin_password}"}' >/dev/null

# Para requests mutadores hay que enviar también el header X-CSRF-Token
# (el valor se lee de la cookie `sferaai_csrf` guardada por el login)
CSRF=$(awk '$6=="sferaai_csrf"{print $7}' /tmp/sfera-cookies.txt)
curl -s -b /tmp/sfera-cookies.txt -X POST "https://{dominio}/api/v1/whatsapp/templates/sync" \
  -H "X-CSRF-Token: ${CSRF}"
```

> **No uses el antiguo `python3 -c "...access_token..."`**: el campo `access_token` del body de `/auth/login` está vacío desde Fase 1 del BFF y desaparecerá en Fase 1.5.

### Templates con imagenes (header IMAGE)

Las URLs de Meta CDN (`scontent.whatsapp.net`) son temporales y expiran. Para templates con imagen en header:

1. Descargar la imagen del template
2. Subirla al servidor:
   ```bash
   scp imagen.png root@YOUR_SERVER_IP:/opt/sferaai/clientes/{client_id}/data/media/templates/
   ```
3. Actualizar `header_content` en DB:
   ```sql
   UPDATE wa_templates
   SET header_content = 'https://{dominio}/media/templates/imagen.png'
   WHERE name = '{template_name}' AND tenant_id = '{ORG_ID}';
   ```
4. Verificar accesibilidad:
   ```bash
   curl -sI "https://{dominio}/media/templates/imagen.png" | head -5
   # Debe devolver HTTP/2 200
   ```

### Renovar token

Los System User Tokens no expiran. Si se necesita rotar:

1. Meta Business > System Users > Generate New Token
2. Actualizar en DB:
   ```sql
   UPDATE wa_tenant_settings
   SET api_token_enc = '{NUEVO_TOKEN}'
   WHERE tenant_id = '{ORG_ID}';
   ```
3. No es necesario reiniciar el backend

### Verificacion

```bash
# 1. Verificar que webhook responde
curl -s "https://{dominio}/api/v1/whatsapp/webhooks/meta?hub.mode=subscribe&hub.verify_token={VERIFY_TOKEN}&hub.challenge=test123"
# Debe devolver: test123

# 2. Verificar token contra Meta API
curl -s "https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}?access_token={TOKEN}"
# Debe devolver datos del numero

# 3. Enviar mensaje de prueba (template hello_world)
curl -s -X POST "https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages" \
  -H "Authorization: Bearer {TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"messaging_product":"whatsapp","to":"{NUMERO_DESTINO}","type":"template","template":{"name":"hello_world","language":{"code":"en_US"}}}'
```

### Limites de Meta

- **Ventana 24h**: fuera de ella solo se pueden enviar templates
- **TIER_1K**: 1.000 mensajes/dia (tier inicial)
- **Subir tier**: mantener quality GREEN durante 7 dias con volumen
- **Quality ratings**: GREEN (ok) → YELLOW (algunos reportes) → RED (restriccion)

---

## 3. Modulo Calendario (Cal.com)

### Descripcion

Gestion de citas via Cal.com. Acceso directo a DB de Cal.com (NO via API). Cal.com se despliega como contenedor Docker adicional.

### Variables de entorno

#### En `.env`

```env
# Generados automaticamente por new-client.sh
CALCOM_NEXTAUTH_SECRET=        # openssl rand -hex 32
CALCOM_ENCRYPTION_KEY=         # openssl rand -hex 32
CALCOM_WEBHOOK_SECRET=         # openssl rand -hex 32
# Se genera en el admin de Cal.com tras primer arranque
CALCOM_API_KEY=
```

### DNS adicional

```
cal.{dominio} → YOUR_SERVER_IP
```

### Servicio en docker-compose.yml

Anadir el servicio `calcom`:

```yaml
  calcom:
    image: calcom/cal.com:v4.7.8
    container_name: {client_id}-calcom
    restart: unless-stopped
    environment:
      DATABASE_URL: postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/calcom
      DATABASE_DIRECT_URL: postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/calcom
      NEXTAUTH_SECRET: ${CALCOM_NEXTAUTH_SECRET}
      CALENDSO_ENCRYPTION_KEY: ${CALCOM_ENCRYPTION_KEY}
      NEXT_PUBLIC_WEBAPP_URL: https://cal.${CLIENT_DOMAIN}
      NEXT_PUBLIC_API_V2_URL: https://cal.${CLIENT_DOMAIN}/api/v2
      NEXTAUTH_URL: https://cal.${CLIENT_DOMAIN}
      NEXT_PUBLIC_LICENSE_CONSENT: agree
      LICENSE: ""
      REDIS_URL: redis://redis:6379
      NEXT_PUBLIC_DEFAULT_TIMEZONE: Europe/Madrid
      NEXT_PUBLIC_COMPANY_NAME: ${CLIENT_NAME}
      NEXT_PUBLIC_SUPPORT_MAIL_ADDRESS: soporte@yourdomain.com
      NEXT_PUBLIC_DISABLE_SIGNUP: "true"
      CALCOM_TELEMETRY_DISABLED: "1"
      CALCOM_WEBHOOK_SECRET: ${CALCOM_WEBHOOK_SECRET}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - internal
      - proxy
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.{client_id}-calcom.rule=Host(`cal.${CLIENT_DOMAIN}`)"
      - "traefik.http.routers.{client_id}-calcom.entrypoints=https"
      - "traefik.http.routers.{client_id}-calcom.tls=true"
      - "traefik.http.routers.{client_id}-calcom.tls.certresolver=letsencrypt"
      - "traefik.http.services.{client_id}-calcom.loadbalancer.server.port=3000"
      - "traefik.docker.network=proxy"
```

### Crear base de datos Cal.com

Cal.com usa su propia DB `calcom` (NO la DB `sfera`):

```bash
docker exec {client_id}-postgres psql -U sfera_{client_id} -d postgres -c "CREATE DATABASE calcom;"
```

> Cal.com ejecuta Prisma migrations automaticamente en el primer boot. La imagen es ~1.1GB.

### Feature flag

```sql
UPDATE organizations
SET settings = settings || '{"calendar_enabled": true}'::jsonb
WHERE slug = '{client_id}';
```

### Crear usuario admin Cal.com

Al acceder a `https://cal.{dominio}` por primera vez se inicia el wizard de setup. Alternativamente:

```bash
docker exec -it {client_id}-calcom npx prisma db seed
```

### Variables backend (calendario)

Anadir en `docker-compose.yml` (backend):

```yaml
environment:
  CALCOM_BASE_URL: http://calcom:3000
  CALCOM_API_KEY: ${CALCOM_API_KEY:-}
  CALCOM_WEBHOOK_SECRET: ${CALCOM_WEBHOOK_SECRET:-}
```

### Verificacion

```bash
# Cal.com accesible
curl -s -o /dev/null -w "%{http_code}" https://cal.{dominio}
# Debe devolver 200

# Endpoints del calendario en API
curl -s https://{dominio}/api/v1/calendar/event-types \
  -H "Authorization: Bearer {JWT_TOKEN}"
```

---

## 4. Modulo Captacion

### Descripcion

Scraping automatico de leads desde portales inmobiliarios (Fotocasa, Idealista, Habitaclia) + pipeline de llamadas automaticas con analisis IA.

### Variables de entorno

#### En `.env`

```env
# Apify (scraping)
APIFY_API_TOKEN=               # https://console.apify.com > Settings > API

# OpenAI (analisis de llamadas)
OPENAI_API_KEY=                # https://platform.openai.com > API Keys
OPENAI_MODEL=gpt-4.1-mini     # Modelo para analisis

# SMTP (notificaciones por email)
SMTP_HOST=smtp.ionos.es        # O el servidor SMTP del cliente
SMTP_PORT=587
SMTP_USER=                     # Email de envio
SMTP_PASSWORD=                 # Password SMTP
SMTP_TLS=true
SMTP_FROM_EMAIL=               # Remitente (ej: leads@empresa.com)
CONTACT_EMAIL=                 # Email que recibe notificaciones
CAPTACION_EMAIL_CC=            # CC opcional
```

#### En `docker-compose.yml` (backend + worker)

```yaml
environment:
  # Captacion
  APIFY_API_TOKEN: ${APIFY_API_TOKEN}
  OPENAI_API_KEY: ${OPENAI_API_KEY}
  OPENAI_MODEL: ${OPENAI_MODEL:-gpt-4.1-mini}
  CAPTACION_DISPATCH_INTERVAL_SEC: 100      # Segundos entre llamadas
  CAPTACION_BUSINESS_HOURS_START: "09:00"   # Inicio horario llamadas
  CAPTACION_BUSINESS_HOURS_END: "21:30"     # Fin horario llamadas
  CAPTACION_BUSINESS_DAYS: "[1,2,3,4,5]"   # Lunes a viernes
  CAPTACION_MAX_CONCURRENT_CALLS: 2         # Llamadas simultaneas
  CAPTACION_MAX_RETRIES: 4                  # Reintentos por lead
  CAPTACION_RETENTION_DAYS: 90              # Dias antes de eliminar datos

  # SMTP
  SMTP_HOST: ${SMTP_HOST:-smtp.ionos.es}
  SMTP_PORT: ${SMTP_PORT:-587}
  SMTP_USER: ${SMTP_USER:-}
  SMTP_PASSWORD: ${SMTP_PASSWORD:-}
  SMTP_TLS: "true"
  SMTP_FROM_EMAIL: ${SMTP_FROM_EMAIL}
  CONTACT_EMAIL: ${CONTACT_EMAIL}
  CAPTACION_EMAIL_CC: ${CAPTACION_EMAIL_CC:-}
```

### Feature flag

```sql
UPDATE organizations
SET settings = settings || '{"captacion": true}'::jsonb
WHERE slug = '{client_id}';
```

### Requisitos adicionales

El modulo captacion requiere:

- Agente Ultravox configurado para llamadas de captacion (prompt especifico)
- Zadarma con numero para originar llamadas
- Las variables de Voz IA (ULTRAVOX_API_KEY, ZADARMA_*) deben estar configuradas

### Configurar scrapers

Insertar configuraciones en `cap_scraper_configs`:

```sql
INSERT INTO cap_scraper_configs (
    id, tenant_id, portal, property_type, location, max_price,
    is_active, schedule_cron, created_at, updated_at
) VALUES (
    gen_random_uuid(),
    '{ORG_ID}',
    'fotocasa',           -- Portal: fotocasa, idealista, habitaclia
    'alquiler',           -- Tipo: alquiler, venta
    'ponferrada',         -- Ubicacion
    1200,                 -- Precio maximo (null = sin limite)
    true,
    '0 8 * * 1-5',       -- Cron: 8:00 L-V
    NOW(), NOW()
);
```

### Crons de scraping y dispatch

Los crons de scraping y dispatch estan configurados en `worker.py`. Verificar que estan activos:

```bash
docker logs {client_id}-worker 2>&1 | grep -i "captacion\|scraper\|dispatch"
```

### Verificacion

```bash
# Test scraping manual (via API)
curl -s -X POST "https://{dominio}/api/v1/captacion/scraper/run" \
  -H "Authorization: Bearer {JWT_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"portal": "fotocasa"}'

# Verificar leads en dashboard
curl -s "https://{dominio}/api/v1/captacion/leads" \
  -H "Authorization: Bearer {JWT_TOKEN}"
```

---

## 5. Modulo Newsletter

### Descripcion

Campanas de email marketing via Amazon SES con tracking de opens/clicks.

### Variables de entorno

#### En `.env`

```env
# AWS SES
AWS_REGION=eu-north-1
AWS_ACCESS_KEY_ID=             # IAM user con permisos SES
AWS_SECRET_ACCESS_KEY=

# Newsletter
NL_FROM_NAME={client_name}
NL_FROM_EMAIL=news@{client_id}.newsletters.yourdomain.com
NL_REPLY_TO=                   # Email de respuesta
NL_SENDING_DOMAIN={client_id}.newsletters.yourdomain.com
NL_SENDING_REGION=eu-north-1
NEWSLETTER_APP_URL=https://{dominio}
```

#### En `docker-compose.yml` (backend + worker)

```yaml
environment:
  AWS_REGION: ${AWS_REGION:-eu-north-1}
  AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID:-}
  AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY:-}
  NL_FROM_NAME: ${NL_FROM_NAME}
  NL_FROM_EMAIL: ${NL_FROM_EMAIL}
  NL_REPLY_TO: ${NL_REPLY_TO:-}
  NL_SENDING_DOMAIN: ${NL_SENDING_DOMAIN}
  NL_SENDING_REGION: ${NL_SENDING_REGION:-eu-north-1}
  NEWSLETTER_APP_URL: ${NEWSLETTER_APP_URL}
```

### DNS para newsletter

Registros DNS necesarios para el dominio de envio `{client_id}.newsletters.yourdomain.com`:

- **DKIM**: 3 registros CNAME (proporcionados por SES al verificar identidad)
- **SPF/MX**: para bounce subdomain
- **DMARC**: registro TXT

### Amazon SES

1. Crear identidad SES para `{client_id}.newsletters.yourdomain.com`
2. Crear Configuration Set: `newsletter-{client_id}` con tracking open/click
3. Crear SNS Topic: `ses-newsletter-{client_id}` + suscripcion webhook
4. Salir de sandbox (si es cuenta SES nueva)

### Feature flag

```sql
UPDATE organizations
SET settings = settings || '{"newsletter_enabled": true}'::jsonb
WHERE slug = '{client_id}';
```

### Verificacion

```bash
# Test envio
curl -s -X POST "https://{dominio}/api/v1/newsletter/campaigns/{campaign_id}/send-test" \
  -H "Authorization: Bearer {JWT_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"test_emails": ["test@example.com"]}'
```

> Guia completa de deliverability: `docs/NEWSLETTER_DELIVERY_TRACKING.md`

---

## 6. Referencia: Feature Flags

Los feature flags se almacenan en el campo `settings` (JSONB) de la tabla `organizations`.

### Flags disponibles

```json
{
  "whatsapp_enabled": true,
  "calendar_enabled": true,
  "captacion": true,
  "newsletter_enabled": true
}
```

### Consultar flags actuales

```sql
SELECT slug, settings FROM organizations WHERE slug = '{client_id}';
```

### Activar un flag

```sql
UPDATE organizations
SET settings = settings || '{"whatsapp_enabled": true}'::jsonb
WHERE slug = '{client_id}';
```

### Desactivar un flag

```sql
UPDATE organizations
SET settings = settings || '{"whatsapp_enabled": false}'::jsonb
WHERE slug = '{client_id}';
```

### Como se consumen los flags

- **Frontend**: `useTenant().hasFeature('{flag}')` — el sidebar muestra/oculta modulos automaticamente
- **Backend**: los endpoints verifican el flag antes de ejecutar logica de negocio
- **No requieren restart**: los flags se leen en cada request desde la DB

### Relacion con el sistema de permisos

Los feature flags y el sistema de permisos son complementarios:

| Capa | Que controla | Donde se configura |
|------|-------------|-------------------|
| **Feature flags** | Visibilidad de modulos completos | `organizations.settings` (JSONB) |
| **Permisos** | Acceso granular por usuario dentro del modulo | Tablas `permission_catalog`, `role_permission_templates`, `user_permissions` |

**Flujo de acceso:**
1. Feature flag activo? → Si no, el modulo no aparece en el sidebar
2. Usuario tiene permiso? → Si no, el endpoint devuelve 403

**Roles disponibles:**
- `superadmin`: Acceso total (wildcard `*`)
- `client_admin`: Administrador del cliente (todos los permisos contratados)
- `user`: Operador con permisos explicitos

**Resolucion de permisos efectivos para rol `user`:**

```
efectivos = (role_template ∪ grants) \ denies
```

Donde:
- **role_template**: permisos por defecto del rol, filtrados por features contratadas
- **grants**: permisos adicionales asignados al usuario (`user_permissions.granted = TRUE`)
- **denies**: permisos del rol revocados al usuario (`user_permissions.granted = FALSE`)

Esto permite que un admin asigne permisos extra A un usuario concreto y tambien que revoque permisos concretos que el rol daria por defecto. En el UI de "Permisos de usuario" cada checkbox es interactivo: si el rol lo marca por defecto, desmarcarlo crea un deny; si el rol no lo marca, activarlo crea un grant.

Las tablas de permisos se crean via `alembic upgrade head` (no con `Base.metadata.create_all`).

### Activar multiples flags a la vez

```sql
UPDATE organizations
SET settings = settings || '{"whatsapp_enabled": true, "calendar_enabled": true}'::jsonb
WHERE slug = '{client_id}';
```
