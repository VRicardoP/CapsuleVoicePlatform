# SferaAI Dashboard

Frontend dashboard para el sistema SferaAI - Gestión de centralita con IA y cumplimiento GDPR.

## Stack Tecnológico

| Tecnología | Versión | Descripción |
|------------|---------|-------------|
| React | 19.x | Biblioteca UI |
| TypeScript | 5.9.x | Tipado estático |
| Vite | 7.x | Build tool |
| Tailwind CSS | 3.4.x | Framework CSS |
| Recharts | 3.x | Visualización de datos |
| Driver.js | 1.x | Tour guiado / Onboarding |

## Estructura del Proyecto

```
dashboard/src/
├── components/
│   ├── auth/                  # Autenticación
│   │   └── LoginScreen.tsx
│   ├── layout/                # Layout principal
│   │   ├── AppLayout.tsx      # Layout con Outlet + Sidebar persistente
│   │   ├── Dashboard.tsx      # Orquestador (providers + modales)
│   │   ├── DashboardView.tsx  # Vista del dashboard (módulos)
│   │   └── Sidebar.tsx        # Navegación lateral
│   ├── modals/                # Modales y paneles
│   │   ├── CallDetailModal.tsx
│   │   ├── ContactModal.tsx           # Formulario de contacto
│   │   ├── MarketplaceModal.tsx       # Marketplace de integraciones
│   │   ├── ModuleSettingsPanel.tsx
│   │   └── PrivacySettingsPanel.tsx   # Derechos ARCO (RGPD Art. 15-21)
│   ├── modules/               # Módulos del dashboard (todos con React.memo)
│   │   ├── MetricsOverviewModule.tsx
│   │   ├── CallStatsModule.tsx
│   │   ├── GdprComplianceScoreModule.tsx
│   │   ├── GdprPendingRequestsModule.tsx
│   │   ├── GdprBreachAlertsModule.tsx
│   │   └── ... (14 módulos total)
│   └── ui/                    # Componentes reutilizables
├── features/
│   └── whatsapp/              # Feature-app WhatsApp (lazy-loaded)
│       └── WhatsAppInbox.tsx
├── services/
│   └── api.ts                 # Cliente API seguro + JWT
├── context/
│   ├── DashboardContext.tsx    # Estado de módulos visibles (useMemo)
│   ├── DataContext.tsx         # 4 contextos de datos con polling independiente
│   ├── CallSelectionContext.tsx # Selección de llamada (local a DashboardView)
│   └── TenantContext.tsx       # Feature flags por tenant
├── hooks/
│   ├── useRBAC.ts             # Control de acceso por rol
│   ├── useDashboardData.ts    # Wrapper → DashboardDataContext
│   ├── useCallStats.ts        # Wrapper → CallStatsContext
│   ├── useGdprData.ts         # Wrapper → GdprDataContext
│   ├── useKpiData.ts          # Wrapper → KpiDataContext
│   └── useOnboarding.ts       # Tour guiado (driver.js)
├── types/
│   └── index.ts               # Tipos TypeScript
├── utils/
│   └── privacy.ts             # Utilidades GDPR/privacidad
└── config/
    ├── modulesConfig.ts       # Configuración de módulos
    └── pollingConfig.ts       # Intervalos de polling centralizados
```

## Configuración

### Variables de Entorno

```bash
# .env (Producción - Docker con nginx proxy)
VITE_USE_MOCK_DATA=false         # Usar API real
VITE_API_URL=/api/v1             # URL relativa para nginx proxy
VITE_API_TIMEOUT=30000           # Timeout API (ms)

# .env (Desarrollo local)
VITE_USE_MOCK_DATA=true          # Usar datos mock
VITE_API_URL=http://localhost:8000/api/v1  # Backend local directo
VITE_API_TIMEOUT=30000           # Timeout API (ms)
```

**Importante:** En producción Docker, usar `VITE_API_URL=/api/v1` permite que nginx haga proxy al backend. El Dockerfile también debe tener `ARG VITE_API_URL=/api/v1`.

### Desarrollo

```bash
# Instalar dependencias
npm install

# Iniciar servidor de desarrollo
npm run dev

# Build para producción
npm run build

# Preview build
npm run preview
```

## Integración con Backend

### Endpoints API Consumidos

#### Autenticación — BFF (cookie opaca `__Host-sferaai_session`)

Ver [`docs/BFF_SESSIONS.md`](../docs/BFF_SESSIONS.md) para el modelo completo (CSRF, API tokens, `require_recent_auth`).

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/auth/login` | Emite cookie BFF |
| POST | `/auth/logout` | Revoca la sesión y borra la cookie |
| POST | `/auth/refresh` | Shim (204) — el BFF auto-refresca cada request |
| GET | `/auth/sessions` | Listar sesiones activas |
| DELETE | `/auth/sessions/{id}` | Revocar sesión (modal de re-auth) |

#### Permisos

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/permissions/me` | Principal actual (role, features, permissions) |
| GET | `/permissions/catalog` | Catálogo de permisos para panel admin |

El front filtra el sidebar y las rutas con `navigationConfig.ts` + `<PermissionGate>`. Un usuario sin `dashboard` es redirigido a su primer módulo accesible por `firstAccessibleRoute()` (ver [`App.tsx`](src/App.tsx)).

#### Dashboard
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/dashboard/metrics` | Métricas completas |
| GET | `/dashboard/kpi` | KPIs de negocio |
| GET | `/dashboard/gdpr-summary` | Resumen GDPR ejecutivo |
| GET | `/dashboard/trends` | Tendencias temporales |
| GET | `/dashboard/alerts` | Alertas activas |

#### Llamadas
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/calls` | Listar llamadas |
| GET | `/calls/{id}` | Detalle de llamada |
| GET | `/calls/{id}/transcription` | Transcripción |
| POST | `/calls/{id}/human-review` | Revisión humana |

#### Derechos GDPR (Art. 15-22)
| Método | Endpoint | Artículo |
|--------|----------|----------|
| GET | `/gdpr/export` | Art. 15/20 - Acceso/Portabilidad |
| GET | `/gdpr/requests` | Lista de solicitudes |
| POST | `/gdpr/requests` | Nueva solicitud |
| POST | `/gdpr/rectify` | Art. 16 - Rectificación |
| POST | `/gdpr/erase` | Art. 17 - Supresión |
| POST | `/gdpr/restrict` | Art. 18 - Limitación |
| POST | `/gdpr/object` | Art. 21 - Oposición |

## Características de Seguridad

### Autenticación JWT
- Tokens almacenados en cookies HttpOnly (backend)
- Refresh automático antes de expiración (5 min)
- Logout automático en 401
- Validación de email (RFC 5322)

### Rate Limiting
- 60 requests/minuto por cliente
- Timeout de 30 segundos
- Reintentos automáticos

### Protección de Datos
- Anonimización de PII según rol
- Detección automática de datos sensibles
- Logging de acceso a PII (Art. 32 RGPD)

## Control de Acceso (RBAC)

| Rol | Nivel | Permisos |
|-----|-------|----------|
| admin | 4 | Acceso completo, gestión de consents |
| user | 3 | Acceso a PII, exportación |
| viewer | 2 | Solo visualización |
| auditor | 1 | Solo logs de auditoría |

## Módulos GDPR

### GdprComplianceScoreModule
- Gauge de cumplimiento global (0-100%)
- Métricas: consents, retención, respuesta, brechas

### GdprPendingRequestsModule
- Gestión de solicitudes ARCO
- Prioridades: Vencida, Urgente, Próxima, Normal
- Plazos según Art. 12.3 RGPD (30 días)

### GdprBreachAlertsModule
- Alertas de brechas de seguridad
- Notificación Art. 33 (72 horas)
- Información de afectados

### PrivacySettingsPanel
- Gestión de consentimientos
- Formulario de derechos ARCO
- Información legal del tratamiento

## Tour Guiado / Onboarding

El dashboard incluye un tour guiado interactivo para nuevos usuarios, implementado con **Driver.js**.

### Características

- **Auto-inicio**: Se activa automáticamente la primera vez que un usuario accede al dashboard
- **Persistencia**: El estado se guarda en `localStorage` (`sfera_onboarding_completed`)
- **Repetible**: Botón "Ayuda" en el sidebar para repetir el tour en cualquier momento
- **Tema oscuro**: Estilos personalizados que coinciden con el tema del dashboard

### Pasos del Tour (14 pasos)

| # | Elemento | Descripción |
|---|----------|-------------|
| 1 | Sidebar | Navegación principal y módulos activos |
| 2 | Configurar Módulos | Personalización de módulos visibles |
| 3 | Privacidad RGPD | Gestión de consentimientos y derechos ARCO |
| 4 | Contacto | Formulario de contacto con la empresa |
| 5 | Marketplace | Marketplace de integraciones adicionales |
| 6 | Métricas Principales | KPIs: llamadas, duración, tasa de éxito |
| 7 | Evolución Semanal | Gráfico de tendencias |
| 8 | Distribución de Estados | Resultados de llamadas |
| 9 | Últimas Llamadas | Historial con transcripciones |
| 10 | Performance IA | Radar de rendimiento del asistente |
| 11 | Mapa de Calor | Actividad por horas/días |
| 12 | Cumplimiento RGPD | Score de conformidad |
| 13 | Solicitudes ARCO | Gestión de derechos |
| 14 | Alertas de Brechas | Incidentes de seguridad |

### Archivos Relacionados

| Archivo | Descripción |
|---------|-------------|
| `hooks/useOnboarding.ts` | Hook principal con lógica del tour |
| `index.css` | Estilos personalizados (`.sfera-tour-popover`) |

### Resetear el Tour (Desarrollo)

```javascript
// En la consola del navegador
localStorage.removeItem('sfera_onboarding_completed')
// Recargar la página para ver el tour
```

---

## Marketplace de Integraciones

El dashboard incluye un **Marketplace de Integraciones** que permite a los usuarios solicitar módulos adicionales para ampliar las capacidades de su asistente virtual.

### Características

- **Modal superpuesto**: Se abre sobre el dashboard con fondo oscurecido (igual que Contacto)
- **Selección múltiple**: Los usuarios pueden seleccionar varios módulos a la vez
- **Integración con Contacto**: Al pulsar "Solicitar", se abre el formulario de contacto pre-rellenado con los módulos seleccionados

### Módulos Disponibles

| Módulo | Categoría | Descripción |
|--------|-----------|-------------|
| Integración WhatsApp | Comunicación | Conecta con WhatsApp Business |
| Sincronización CRM | Integraciones | Sync con Salesforce, HubSpot, Zoho |
| Análisis de Sentimiento Avanzado | Analytics | IA avanzada para análisis emocional |
| Soporte Multiidioma | Expansión | Inglés, francés, alemán, italiano, portugués |
| Biometría de Voz | Seguridad | Verificación de identidad por voz |
| Programador de Citas | Productividad | Integración con Google Calendar y Outlook |

### Flujo de Solicitud

1. Usuario accede al Marketplace desde el botón en el sidebar
2. Selecciona los módulos de interés (checkboxes)
3. Pulsa "Solicitar"
4. Se abre el formulario de contacto con:
   - **Asunto**: "Solicitud de módulos"
   - **Mensaje**: Texto estándar con lista de módulos seleccionados
5. Usuario revisa y envía el formulario

### Archivos Relacionados

| Archivo | Descripción |
|---------|-------------|
| `modals/MarketplaceModal.tsx` | Componente principal del marketplace |
| `modals/ContactModal.tsx` | Formulario de contacto (recibe props iniciales) |
| `layout/Dashboard.tsx` | Gestión de estado y callbacks |
| `layout/Sidebar.tsx` | Botón de acceso al marketplace |

---

## Cumplimiento Normativo

| Normativa | Implementación |
|-----------|----------------|
| RGPD Art. 7 | Gestión de consentimientos |
| RGPD Art. 15-21 | Panel de derechos ARCO |
| RGPD Art. 30 | Logging de acceso |
| RGPD Art. 32 | Anonimización, cifrado |
| RGPD Art. 33 | Alertas de brechas (72h) |
| LOPDGDD 3/2018 | Cumplimiento español |
| OWASP Top 10 | Seguridad web |

---

## Optimizaciones de Rendimiento

### Contextos React (DataContext split)

El `DataContext` se divide en 4 contextos independientes para evitar re-renders cruzados entre dominios:

| Contexto | Datos | Polling | Hook público |
|----------|-------|---------|-------------|
| DashboardDataContext | Métricas, llamadas recientes | 5s | `useDashboardData()` |
| CallStatsContext | Estadísticas por período | 5s | `useCallStats()` |
| GdprDataContext | GDPR summary, trends, metrics | 30s | `useGdprData()` |
| KpiDataContext | KPIs avanzados | 60s | `useKpiData()` |

### React.memo

Los 14 módulos están envueltos con `React.memo()` para bloquear re-renders del padre. Al no recibir props, la comparación es trivialmente igual.

### Code-splitting (Vite manualChunks)

Dependencias pesadas extraídas a chunks separados para reducir el bundle principal:

| Chunk | Tamaño |
|-------|--------|
| `index.js` (principal) | 313 KB |
| `recharts.js` | 399 KB |
| `driver.js` | 20.7 KB |
| `DashboardView.js` | 16.4 KB (lazy) |
| `WhatsAppInbox.js` | 14.9 KB (lazy) |

### Otras optimizaciones

- **CallSelectionContext**: `selectedCall` es estado local de DashboardView, no global
- **useMemo en DashboardContext**: El value del contexto es estable entre renders
- **Constantes a module scope**: Objetos estáticos fuera de componentes React
- **Paginación con ventana**: Máx. 5 botones visibles + ellipsis en RecentCallsModule

---

*SferaAI Dashboard v1.2.0 - Febrero 2026*
*Última actualización: 2026-02-14*
