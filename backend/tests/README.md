# CapsuleCorp - Tests

**Total:** 284 tests | **Failures:** 0
**Última actualización:** 2026-02-17

---

## Estructura

```
backend/tests/
├── conftest.py                          # DB fixtures, test user, secure_keys setup
├── integration/                         # Tests con PostgreSQL real (89)
│   ├── test_user_repository.py          # 12 - Usuarios, sesiones, bloqueo
│   ├── test_gdpr_repository.py          # 16 - Derechos ARCO+PL, audit, brechas
│   ├── test_robinson_repository.py      # 12 - Lista Robinson, Orden ETD
│   ├── test_api_keys.py                 # 25 - API Keys M2M (CRUD, validación, rate limit)
│   ├── test_api_key_provision.py        # 11 - Provisión automática sin admin
│   └── test_client_error_logs.py        # 13 - Error reporting del agente IA
├── test_endpoints/                      # HTTP endpoint tests (27)
│   ├── conftest.py                      # httpx.AsyncClient + ASGITransport
│   ├── test_health.py                   # 2 - Health checks
│   ├── test_auth.py                     # 6 - Login, logout, refresh
│   ├── test_dashboard.py               # 5 - Métricas, KPIs
│   ├── test_calls.py                   # 6 - CRUD llamadas
│   ├── test_gdpr.py                    # 6 - Derechos RGPD
│   └── test_marketplace.py             # 2 - Marketplace módulos
├── test_services/                       # Service-level tests (7)
│   └── test_breach_detection.py         # 7 - Patrones bruta fuerza, exfiltración
└── unit/                                # Tests sin DB (161)
    ├── test_api_key_schemas.py          # 28 - Pydantic schemas API Keys
    ├── test_calendar_schemas.py         # 15 - Pydantic schemas Calendar
    ├── test_whatsapp_schemas.py         # 30 - Pydantic schemas WhatsApp
    ├── test_whatsapp_sse.py             # 11 - SSE broadcaster
    ├── test_whatsapp_service.py         # 13 - WhatsApp service logic
    └── test_whatsapp_phases_bf.py       # 64 - WhatsApp phases B-F schemas
```

---

## Ejecución

```bash
cd backend

# Todos los tests
PYTHONPATH=. python3 -m pytest tests/ -v

# Por categoría
PYTHONPATH=. python3 -m pytest tests/integration/ -v
PYTHONPATH=. python3 -m pytest tests/test_endpoints/ -v
PYTHONPATH=. python3 -m pytest tests/test_services/ -v
PYTHONPATH=. python3 -m pytest tests/unit/ -v
```

### Requisitos

- PostgreSQL en puerto **5433** (configurado en `conftest.py` como `TEST_DATABASE_URL`)
- Tablas `security_breaches` y `client_error_logs` creadas via SQL
- Roles `capsule_ai_agent`, `capsule_app` con GRANTs apropiados

---

## Convenciones

| Convención | Detalle |
|------------|---------|
| Trailing slash | Rutas sin `/` final. Tests usan `/api/v1/dashboard` (NO `/api/v1/dashboard/` → 307) |
| Encryption keys | `conftest.py` actualiza tabla `secure_keys` (no solo GUC vars) |
| asyncpg casts | `CAST(:param AS JSONB)` (NO `::JSONB` tras bind params) |
| audit_log INSERT | `entity_type` NOT NULL, acciones UPPERCASE, `user_id` con FK válida o NULL |
| calls INSERT | Campos required: `user_id`, `call_date`, `call_time`, `call_timestamp`, `duration_seconds`, `caller_phone_hash` |
| GDPR deadlines | Usar `interval '1 month'` (NO `interval '29 days'` — falla en febrero) |
| Breach detection | Testear `_detect_*` individuales, NO `run_detection_cycle()` |

---

## Cobertura Normativa

| Normativa | Artículos | Tests aprox |
|-----------|-----------|-------------|
| RGPD | Art. 5, 12, 15-22, 30, 32, 33, 34 | ~60 |
| LOPDGDD | Art. 33, 34 | ~15 |
| AI Act | Art. 12 | ~4 |
| Orden ETD/1286/2022 | Art. 4, 6 | ~12 |
| NIS2 | Art. 23 | ~7 |
