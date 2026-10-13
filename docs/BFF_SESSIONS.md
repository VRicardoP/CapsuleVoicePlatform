# BFF Sessions — Modelo de Autenticación

Fase 1 implementada el 2026-04-13 (commit `4205263`). Fase 1.5 (retirada del path JWT legacy) pendiente — ver [`DEUDA_TECNICA.md`](DEUDA_TECNICA.md).

## Qué cambió

Antes, el backend emitía JWTs (`access_token` + `refresh_token`) en el body de `/auth/login` y en cookies HttpOnly. El navegador no los leía pero los JS clients dependían del shape de la respuesta. Si se filtraban (XSS, logs mal configurados) bastaban para impersonar al usuario.

Ahora el navegador sólo ve una cookie opaca (`__Host-sferaai_session` en producción, `sferaai_session` en dev) que el backend resuelve contra la tabla `frontend_sessions`. Los JWTs no salen del proceso backend. Un robo de cookie sigue siendo crítico, pero:

- La cookie es `HttpOnly` (JS no la ve, XSS no la roba).
- Cada sesión tiene `idle_expires_at` (30 min sin actividad) + `absolute_expires_at` (12 h máx).
- CSRF se valida con doble capa: `Origin`/`Referer` + double-submit token (`sferaai_csrf` no-HttpOnly + header `X-CSRF-Token`).

## Tablas

### `frontend_sessions`

Una fila por sesión activa de navegador. Índice único por `cookie_hash` (SHA-256 del valor de la cookie). Apunta a un `user_sessions.id` (tabla backend existente). Guarda también `backend_session_token` plaintext — **server-only**, se replay-ea al GUC `app.secure_session_token` para que las RLS policies (`get_current_user()`) sigan funcionando bajo BFF.

Campos clave:
- `cookie_hash`, `csrf_token_hash` — lookups.
- `last_seen_at`, `idle_expires_at`, `absolute_expires_at` — sliding + absolute window.
- `recent_auth_at` + `auth_method` — para `require_recent_auth`.
- `upgraded_from_legacy` — true si vino de un auto-upgrade de cookie legacy.
- `is_revoked`, `revoked_reason` — logout / revocación.

### `api_tokens`

Tokens bearer para uso server-to-server (CI, automatizaciones). Formato `sferaai_at_<base64>`.

Campos clave:
- `token_hash` (único), `user_id`, `scope[]`, `description`, `expires_at`.
- `created_by_session_id` apunta a la sesión desde la que se emitió (auditoría).

## Flow por request

```
┌─────────┐     Cookie __Host-sferaai_session     ┌──────────────────┐
│ Browser │ ─────────────────────────────────────▶│ BFFMiddleware    │
└─────────┘                                        │ resuelve cookie  │
                                                   │  → frontend_sess │
                                                   │  → user_sessions │
                                                   └──────────────────┘
                                                            │
                                                            ▼
                                                   ┌──────────────────┐
                                                   │ request.state:   │
                                                   │  user_id         │
                                                   │  session_token   │
                                                   │  frontend_session│
                                                   │  auth_source=bff │
                                                   └──────────────────┘
                                                            │
                                                            ▼
                                                   ┌──────────────────┐
                                                   │ Dependencies     │
                                                   │ (get_current_*)  │
                                                   │ leen request.state│
                                                   └──────────────────┘
```

El middleware está en [`app/core/bff_middleware.py`](../backend/app/core/bff_middleware.py); las dependencies actualizadas en [`app/core/dependencies.py`](../backend/app/core/dependencies.py).

## Exclusiones del middleware

Rutas que **NO pasan por BFF** (se documentan en `EXCLUDED_PREFIXES` del middleware):

- `/health` y derivados.
- `/api/v1/auth/login` y `/api/v1/auth/passkey/login/*` — aún no hay sesión.
- Webhooks externos con HMAC propio: `/api/v1/whatsapp/webhooks/meta`, `/api/v1/captacion/webhooks/*`, `/api/v1/newsletter/webhooks/*`, `/api/v1/calendar/webhooks`, `/api/v1/ultravox/webhook`.
- `/api/v1/newsletter/unsubscribe/*` — público, RFC 8058.
- `/api/v1/marketplace` — público.
- `/docs`, `/redoc`, `/openapi.json`, `/media`.

Rutas con **API Key** (`X-API-Key`) o **bearer `sferaai_at_*`** también bypasean BFF porque no son cookie-based y por tanto no son CSRF-vulnerables.

## Flujos

### Login con password

```
POST /api/v1/auth/login
body: { email, password }
```

Respuesta: `200` con body `{ user: {...} }`. Sin tokens en el body (campos `access_token` y `refresh_token` llegan vacíos por compat — retirados en fase 1.5). Headers devueltos:

```
Set-Cookie: __Host-sferaai_session=<opaque>; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=43200
Set-Cookie: sferaai_csrf=<random>; Secure; SameSite=Lax; Path=/; Max-Age=43200
```

### Logout

```
POST /api/v1/auth/logout
body: { invalidate_all_sessions: false }
```

Requiere sesión activa. Revoca la `frontend_session` actual + el `user_session` asociado. Devuelve `204` y `Set-Cookie` borrando `__Host-sferaai_session`, `sferaai_csrf`, `access_token`, `refresh_token`.

Si `invalidate_all_sessions: true`, revoca todas las sesiones del usuario (logout en todos los dispositivos).

### Refresh shim

`POST /api/v1/auth/refresh` existe como shim de compatibilidad. Devuelve `204` si hay sesión BFF activa (el middleware ya sliding-refresca en cada request) o `401` si no. **No emite tokens en body.**

Clients nuevos NO deben llamar a `/refresh`. Clients legacy siguen funcionando sin romperse.

### Coexistencia legacy (fase 1)

Durante 7 días tras el rollout, el middleware acepta también la cookie `access_token` legacy y la auto-upgradea:

1. Detecta cookie `access_token` sin `__Host-sferaai_session`.
2. Valida el JWT contra `user_sessions`.
3. Adquiere `pg_advisory_xact_lock` por `backend_session_id` (key determinística con SHA-256, segura bajo multi-worker).
4. Re-verifica (double-checked locking) y crea la `frontend_session` sólo si no existe.
5. Encola los `Set-Cookie` en la respuesta.

El auto-upgrade es **idempotente**: dos requests concurrentes con la misma cookie legacy no crean dos filas.

### Operaciones sensibles: `require_recent_auth`

Ciertos endpoints requieren que la sesión tenga `recent_auth_at` dentro de una ventana de 5 minutos:

- `POST /users/me/password` — cambiar contraseña propia.
- `POST /users` — crear un usuario.
- `DELETE /users/{id}` — desactivar usuario.
- `PUT /users/{id}/permissions` — cambiar permisos.
- `POST /gdpr/erase` — derecho de supresión RGPD.
- `DELETE /auth/sessions/{id}` — revocar sesión remota.
- `POST /auth/api-token` — emitir API token.
- `DELETE /auth/api-tokens/{id}` — revocar API token.

Si la sesión está "fría" (ej. 10 min sin re-auth), el endpoint devuelve `401` con:

```
WWW-Authenticate: SferaAI re-auth-required
X-Reauth-Code: REAUTH_REQUIRED
```

El frontend detecta este código y muestra `PasswordReauthModal`. Tras re-auth, `recent_auth_at` se actualiza a NOW y el frontend reintenta la acción.

**API tokens NO pueden satisfacer `require_recent_auth`**. Estas operaciones son explícitamente de navegador.

## API tokens (automatización / CI)

### Emisión

```
POST /api/v1/auth/api-token
Requires: BFF session + role ∈ {superadmin, client_admin} + require_recent_auth
body: {
  description: "CI nightly backup",
  scope: ["calls.read", "leads.read"],
  ttl_hours: 24   // máx 168 = 7 días
}
```

Respuesta `201`:

```json
{
  "id": "uuid",
  "token": "sferaai_at_<base64>",
  "description": "CI nightly backup",
  "scope": ["calls.read", "leads.read"],
  "expires_at": "2026-04-14T...",
  "created_at": "..."
}
```

**El `token` se muestra una sola vez.** Guárdalo como secret.

Limites:
- Scope debe ser subset de los permisos del caller.
- Max 10 tokens activos por usuario.
- TTL ≤ 168 h (7 días).

### Uso

```
GET /api/v1/captacion/leads
Authorization: Bearer sferaai_at_<base64>
```

El token vale únicamente para los permisos declarados en `scope`. El issuer tenía `*` (superadmin), pero un token con `scope=["calls.read"]` sólo puede hacer llamadas que requieren `calls.read`. Esto se aplica en `get_current_principal` cuando `auth_source == "api_token"`.

### Restricciones

- **No acceden a endpoints con `get_db_with_rls`** — devuelven `403` explícito ("This endpoint requires a user session; API tokens cannot provide the required RLS context").
- **No pasan `require_recent_auth`**.
- **No pueden emitir otros API tokens** (el endpoint requiere `require_admin` que no acepta `role="api_token"`).
- **No pueden hacer logout ni cambiar password** del user dueño.

### Listado y revocación

```
GET /api/v1/auth/api-tokens          # list own tokens (metadata only)
DELETE /api/v1/auth/api-tokens/{id}  # revoke (require_recent_auth)
```

## CSRF

El middleware valida CSRF sólo para requests con cookie BFF y método mutador (POST/PUT/PATCH/DELETE):

1. **Origin/Referer check**: la URL debe venir del mismo host que la request. En desarrollo se permite `localhost:*`.
2. **Double-submit token**: `X-CSRF-Token` header debe coincidir con el valor de la cookie `sferaai_csrf` **Y** su hash debe coincidir con `frontend_sessions.csrf_token_hash`.

Fallos → `403 CSRF validation failed: <reason>`.

Las peticiones con `X-API-Key` o bearer `sferaai_at_*` bypasean CSRF.

## Parámetros configurables

En `settings.py`:

| Setting | Default | Qué hace |
|---|---|---|
| `bff_session_idle_minutes` | 30 | Sin actividad = cierra sesión |
| `bff_session_absolute_hours` | 12 | Sesión máxima desde login |
| `bff_session_sliding_throttle_seconds` | 60 | Sólo actualiza `last_seen_at` si pasó esto |
| `bff_recent_auth_window_seconds` | 300 | Ventana de `require_recent_auth` |
| `bff_api_token_max_ttl_hours` | 168 | TTL máximo de API tokens (7 días) |
| `bff_api_token_max_active_per_user` | 10 | Cuántos tokens activos permite por usuario |
| `bff_legacy_cookie_compat` | `True` | Aceptar cookies JWT legacy + auto-upgrade |

Para retirar el path legacy (fase 1.5), setear `bff_legacy_cookie_compat=false` en producción.

## Seguridad — threat model

**Cubre**:
- XSS-as-token-theft (JWTs no accesibles por JS).
- CSRF (doble capa).
- Token replay (session_token atado a una `user_sessions` row con backend-pid checks en SQL schema).
- Operaciones sensibles sin re-auth reciente.
- API tokens sobre-privilegiados (scope enforced).

**NO cubre, por diseño**:
- Compromiso del servidor backend: el token plaintext en `frontend_sessions.backend_session_token` es legible con acceso DB. Mismo nivel de riesgo que `password_hash` u otras PII. Si es insuficiente, la defensa en profundidad sería DPoP backend-to-backend (descartado hoy porque BFF y API corren en el mismo proceso — no aporta ganancia real).
- Robo de la cookie opaca misma (ej. via malware en el dispositivo del usuario). Mitigaciones: `HttpOnly`, `Secure`, `SameSite=Lax`, absolute window 12h.

## Tests

- `backend/tests/unit/test_bff_session_service.py` — 11 tests: hashing, expiry, recent-auth, cookie-name selection.
- `backend/tests/unit/test_bff_fixes.py` — 8 tests para los 5 hallazgos de auditoría.
- `backend/tests/test_endpoints/test_bff_endpoints.py` — 3 tests de endpoints (refresh shim, api-tokens, logout-cookies).

## Migraciones Alembic

1. `f7g8h9i0j1k2_bff_sessions_api_tokens.py` — crea tablas.
2. `g8h9i0j1k2l3_marketplace_permission.py` — añade permiso de marketplace (no es BFF pero se aplica en el mismo rollout).

## Rollout

- **Hoy**: Fase 1 en rama `main`, pendiente de rollout a un tenant canary primero.
- **+7 días**: Fase 1.5 — poner `bff_legacy_cookie_compat=false`, retirar path JWT en `dependencies.py`, segunda migración que dropee `user_sessions.refresh_token_hash` columna.
- **Fase 2 futura**: Passkeys / WebAuthn.
