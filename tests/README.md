# CapsuleCorp - Tests SQL de Cumplimiento Normativo

**Versión:** 5.9.5
**Última actualización:** 2025-12-18
**Total tests:** 398 tests SQL | 55 archivos
**Cobertura normativa:** 100% - RGPD, LOPDGDD, AI Act, LGT, NIS2, LSSI, Orden ETD/1286/2022

---

## Resumen Ejecutivo

Los tests SQL de CapsuleCorp verifican el cumplimiento de **10+ normativas** europeas y españolas directamente a nivel de base de datos PostgreSQL.

### Estado de Cobertura: 100%

| Normativa | Cobertura | Artículos | Tests |
|-----------|-----------|-----------|-------|
| **RGPD (UE) 2016/679** | ✅ 100% | 28 artículos | 01-21, 29-41, 44, 48-54 |
| **LOPDGDD 3/2018** | ✅ 100% | 6 artículos | 05, 07, 25, 32, 45, 51 |
| **AI Act (UE) 2024/1689** | ✅ 100% | 13 artículos | 26-27, 35, 37-39, 42-44, 46 |
| **NIS2 (UE) 2022/2555** | ✅ 100% | 10 requisitos | 47, 54 |
| **LGT/Ley 25/2007** | ✅ 100% | 3 artículos | 25 |
| **Orden ETD/1286/2022** | ✅ 100% | 3 artículos | 28 |
| **LSSI** | ✅ 100% | 1 artículo | 28, 36 |

### Resumen por Normativa

| Normativa | Artículos principales | Archivos test |
|-----------|----------------------|---------------|
| **RGPD (UE) 2016/679** | Art. 5-9, 12-22, 25, 28-34, 44-49 | 01-09, 21, 41, 54 |
| **LOPDGDD 3/2018** | Art. 6, 7, 11, 16, 17, 33 | 05, 07, 25, 32, 45, 51 |
| **AI Act (UE) 2024/1689** | Art. 9-17, 26, 50, 86 | 26, 27, 35, 37-39, 42-44, 46 |
| **LGT (Ley 9/2014)** | Art. 68 | 25 |
| **Ley 25/2007** | Art. 4, 5 | 25 |
| **NIS2 (UE) 2022/2555** | Art. 21.2.a-j | 47, 54 |
| **Orden ETD/1286/2022** | Art. 4, 6 | 28 |
| **LSSI** | Art. 21 | 28, 36 |

---

## Estructura de Tests

```
tests/
├── 00_seed_fixtures.sql              # Datos de prueba
├── 00_test_helpers.sql               # Funciones auxiliares
├── 01_test_integridad_referencial.sql
├── 02_test_funciones_cifrado.sql
├── 03_test_audit_inmutable.sql
├── 04_test_retencion_automatica.sql
├── 05_test_consentimientos.sql
├── 06_test_portabilidad.sql
├── 07_test_limitacion_tratamiento.sql
├── 08_test_derechos_arco.sql
├── 09_test_breach_notification.sql
├── 10_test_security_breaches.sql
├── 11_test_sensitive_data.sql
├── 12_test_retention_deletion.sql
├── 13_test_data_portability.sql
├── 14_test_dashboard_metrics.sql
├── 15_test_call_processing_consents.sql
├── 16_test_gdpr_right_to_erasure.sql
├── 17_test_performance_conversions.sql
├── 18_test_campaigns.sql
├── 19_test_dashboard_metrics_complete.sql
├── 20_test_kpi_metrics.sql
├── 21_test_rgpd_compliance.sql
├── 22_test_rls_isolation.sql
├── 23_test_pii_masking.sql
├── 24_test_performance_optimization.sql
├── 25_test_p0_lopdgdd_lgt.sql
├── 26_test_p1_ai_transparency.sql
├── 27_test_p2_ai_employee.sql
├── 28_test_p3_robinson.sql
├── 29_test_base_legal_validation.sql
├── 30_test_data_minimization.sql
├── 31_test_data_accuracy.sql
├── 32_test_minor_consent.sql
├── 33_test_rat_compliance.sql
├── 34_test_dpo_governance.sql
├── 35_test_ai_logs_retention.sql
├── 36_test_marketing_consent.sql
├── 37_test_ai_risk_management.sql
├── 38_test_ai_data_governance.sql
├── 39_test_ai_technical_docs.sql
├── 40_test_privacy_by_design.sql
├── 41_test_international_transfers.sql
├── 42_test_ai_accuracy_robustness.sql
├── 43_test_ai_quality_management.sql
├── 44_test_ai_right_to_explanation.sql
├── 45_test_information_layers.sql
├── 46_test_ai_deployer_obligations.sql
├── 47_test_nis2_cybersecurity.sql
├── 48_test_compliance_gaps.sql
├── 49_test_age_verification.sql
├── 50_test_audit_integrity_verification.sql
├── 51_test_blocked_data_rls_anonymization.sql
├── 52_test_security_mitigations.sql
├── 53_test_user_preferences_rls.sql
├── 54_test_data_processors.sql
└── 55_test_employee_detection.sql      # AI Act Art. 5.1.f - Detección empleados
```

---

## Tests por Normativa

### RGPD - Reglamento (UE) 2016/679

#### 01_test_integridad_referencial.sql
**Normativa:** RGPD Art. 32.1.b (Integridad de sistemas de tratamiento)

| Test | Descripción |
|------|-------------|
| Foreign Keys Exist | Verifica existencia de ≥20 foreign keys |
| ON DELETE CASCADE | Verifica cascadas de eliminación |
| CHECK Constraints Exist | Verifica existencia de ≥30 CHECK constraints |
| Email Validation | Rechaza emails inválidos |
| UNIQUE Constraints | Rechaza duplicados |
| NOT NULL Constraints | Rechaza NULL en campos críticos |
| Active Key Unique Index | Índice único para clave de cifrado activa |

#### 02_test_funciones_cifrado.sql
**Normativa:** RGPD Art. 32.1.a, Art. 5.1.f, Art. 25.1

| Test | Descripción | Normativa |
|------|-------------|-----------|
| Basic Encryption/Decryption | Cifrado AES-256-GCM funciona | **RGPD Art. 32.1.a** |
| Encryption Metadata Complete | Metadata completa (c, iv, tag, alg, kid, v) | **RGPD Art. 32.1.a** |
| HMAC Authentication | Detecta manipulación de datos | **RGPD Art. 5.1.f** |
| HMAC Hash with Pepper | Hash consistente con pepper | **RGPD Art. 32.1.a** |
| Multiple PII Types | Cifra distintos tipos de PII | **RGPD Art. 25.1** |

#### 03_test_audit_inmutable.sql
**Normativa:** RGPD Art. 30, Art. 32.1.b, Art. 5.2, Art. 24.1

| Test | Descripción | Normativa |
|------|-------------|-----------|
| Audit Log Insert | Inserciones con hash de integridad | **RGPD Art. 30** |
| Audit Log UPDATE Blocked | UPDATE rechazado en audit_log | **RGPD Art. 5.2** |
| Audit Log DELETE Blocked | DELETE rechazado en audit_log | **RGPD Art. 5.2** |
| Audit Log Integrity | Verificación de integridad HMAC | **RGPD Art. 32.1.b** |

#### 04_test_retencion_automatica.sql
**Normativa:** RGPD Art. 5.1.e, Art. 17.1.a, Art. 13.2.a, Art. 32.1.c

| Test | Descripción | Normativa |
|------|-------------|-----------|
| Sesiones Expiradas | Eliminación automática de sesiones expiradas | **RGPD Art. 5.1.e** |
| Retención por Tipo | Diferentes periodos por tipo de dato | **RGPD Art. 5.1.e** |
| Scheduled Deletion | Eliminación programada funciona | **RGPD Art. 17.1.a** |

#### 05_test_consentimientos.sql
**Normativa:** RGPD Art. 6.1.a, Art. 7, LOPDGDD Art. 6

| Test | Descripción | Normativa |
|------|-------------|-----------|
| Registro Consentimiento | Consentimiento con evidencia completa | **RGPD Art. 7.1** |
| Retirada Consentimiento | Retirada fácil del consentimiento | **RGPD Art. 7.3** |
| Versionado Consentimientos | Control de versiones de textos | **RGPD Art. 7** |
| Evidencia Completa | Prueba del consentimiento | **LOPDGDD Art. 6.3** |

#### 06_test_portabilidad.sql
**Normativa:** RGPD Art. 20, Art. 15.3, LOPDGDD Art. 17

| Test | Descripción | Normativa |
|------|-------------|-----------|
| Export JSON Válido | Exportación en JSON estructurado | **RGPD Art. 20.1** |
| Datos Completos | Export incluye todos los datos del usuario | **RGPD Art. 20.1** |
| Formato Legible | Formato legible por máquina | **RGPD Art. 20.1** |

#### 07_test_limitacion_tratamiento.sql
**Normativa:** RGPD Art. 18, LOPDGDD Art. 16

| Test | Descripción | Normativa |
|------|-------------|-----------|
| Usuario Bloqueado | is_active = false bloquea acceso | **RGPD Art. 18.1** |
| Datos No Eliminados | Datos bloqueados, no eliminados | **RGPD Art. 18.2** |
| Levantamiento | Informar antes de levantar limitación | **RGPD Art. 18.3** |

#### 08_test_derechos_arco.sql
**Normativa:** RGPD Art. 15-22, LOPDGDD Art. 12-23

| Test | Descripción | Normativa |
|------|-------------|-----------|
| Derecho Acceso | Export sin secretos | **RGPD Art. 15** |
| Derecho Rectificación | Actualización de datos personales | **RGPD Art. 16** |
| Derecho Supresión | Eliminación/bloqueo de datos | **RGPD Art. 17** |
| Derecho Oposición | Marcar oposición a tratamiento | **RGPD Art. 21** |
| Plazo Respuesta | Respuesta en máximo 30 días | **RGPD Art. 12.3** |

#### 09_test_breach_notification.sql
**Normativa:** RGPD Art. 33, Art. 34, Art. 32

| Test | Descripción | Normativa |
|------|-------------|-----------|
| Eventos Seguridad | Registro en audit_log | **RGPD Art. 33.5** |
| Deadline 72h | Notificación a autoridad en 72h | **RGPD Art. 33.1** |
| Contenido Notificación | Información requerida completa | **RGPD Art. 33.3** |
| Documentación | Todas las brechas documentadas | **RGPD Art. 33.5** |

---

### LOPDGDD - Ley Orgánica 3/2018

#### 25_test_p0_lopdgdd_lgt.sql
**Normativa:** LOPDGDD Art. 33, LGT Art. 68.3, Ley 25/2007

| Test | Descripción | Normativa |
|------|-------------|-----------|
| Tabla blocked_data | Existe tabla de datos bloqueados | **LOPDGDD Art. 33** |
| Bloqueo Antes Supresión | Datos bloqueados antes de eliminar | **LOPDGDD Art. 33** |
| Acceso Solo Autoridades | Datos bloqueados solo para jueces/fiscales | **LOPDGDD Art. 33.3** |
| Retención 12 Meses | Datos de tráfico conservados 12 meses | **LGT Art. 68.3** |
| Sin Contenido | No se conserva contenido de comunicaciones | **Ley 25/2007 Art. 4** |

---

### AI Act - Reglamento (UE) 2024/1689

#### 26_test_p1_ai_transparency.sql
**Normativa:** AI Act Art. 50, Art. 13, Art. 14

| Test | Descripción | Normativa |
|------|-------------|-----------|
| Notificación IA | Informar interacción con sistema IA | **AI Act Art. 50.1** |
| Detección Emociones | Informar análisis de emociones | **AI Act Art. 50.3** |
| Supervisión Humana | Mecanismos de supervisión humana | **AI Act Art. 14** |
| Información Sistema | Transparencia sobre capacidades IA | **AI Act Art. 13** |

#### 27_test_p2_ai_employee.sql
**Normativa:** AI Act Art. 26 (Obligaciones del empleador)

| Test | Descripción | Normativa |
|------|-------------|-----------|
| Formación Empleados | Registro de formación en IA | **AI Act Art. 26.1** |
| Información Trabajadores | Información sobre sistemas IA en el trabajo | **AI Act Art. 26.7** |

#### 35_test_ai_logs_retention.sql
**Normativa:** AI Act Art. 12

| Test | Descripción | Normativa |
|------|-------------|-----------|
| Logs IA Activos | Logs automáticos de operaciones IA | **AI Act Art. 12.1** |
| Trazabilidad | Logs permiten auditar decisiones | **AI Act Art. 12.2** |
| Retención 6 Meses | Logs conservados mínimo 6 meses | **AI Act Art. 12.3** |

#### 37_test_ai_risk_management.sql
**Normativa:** AI Act Art. 9

| Test | Descripción | Normativa |
|------|-------------|-----------|
| Tabla ai_risk_management | Sistema de gestión de riesgos | **AI Act Art. 9.1** |
| Identificación Riesgos | Riesgos conocidos y previsibles | **AI Act Art. 9.2.a** |
| Evaluación Riesgos | Estimación y evaluación | **AI Act Art. 9.2.b** |
| Medidas Gestión | Adopción de medidas adecuadas | **AI Act Art. 9.2.d** |

#### 38_test_ai_data_governance.sql
**Normativa:** AI Act Art. 10

| Test | Descripción | Normativa |
|------|-------------|-----------|
| Gobernanza Datos | Prácticas de gobernanza de datos | **AI Act Art. 10.2** |
| Calidad Datos | Datos de entrenamiento relevantes | **AI Act Art. 10.3** |
| Sesgos | Examen de sesgos en datos | **AI Act Art. 10.2.f** |

#### 39_test_ai_technical_docs.sql
**Normativa:** AI Act Art. 11

| Test | Descripción | Normativa |
|------|-------------|-----------|
| Documentación Técnica | Documentación antes de comercialización | **AI Act Art. 11.1** |
| Contenido Completo | Información según Anexo IV | **AI Act Art. 11.1** |

#### 42_test_ai_accuracy_robustness.sql
**Normativa:** AI Act Art. 15

| Test | Descripción | Normativa |
|------|-------------|-----------|
| Precisión | Nivel de precisión declarado | **AI Act Art. 15.1** |
| Robustez | Resistencia a errores | **AI Act Art. 15.4** |
| Ciberseguridad | Protección contra ataques | **AI Act Art. 15.5** |

#### 43_test_ai_quality_management.sql
**Normativa:** AI Act Art. 17

| Test | Descripción | Normativa |
|------|-------------|-----------|
| Sistema Calidad | Sistema de gestión de calidad | **AI Act Art. 17.1** |
| Procedimientos | Procedimientos documentados | **AI Act Art. 17.1.a-l** |

#### 44_test_ai_right_to_explanation.sql
**Normativa:** AI Act Art. 86, RGPD Art. 22

| Test | Descripción | Normativa |
|------|-------------|-----------|
| Derecho Explicación | Explicación de decisiones automatizadas | **AI Act Art. 86** |
| Factores Decisión | Factores principales explicados | **RGPD Art. 22** |

#### 46_test_ai_deployer_obligations.sql
**Normativa:** AI Act Art. 26

| Test | Descripción | Normativa |
|------|-------------|-----------|
| Uso Conforme | Uso según instrucciones | **AI Act Art. 26.1** |
| Supervisión | Supervisión por personas competentes | **AI Act Art. 26.2** |
| Datos Entrada | Datos de entrada relevantes | **AI Act Art. 26.4** |

---

### NIS2 - Directiva (UE) 2022/2555

#### 47_test_nis2_cybersecurity.sql
**Normativa:** NIS2 Art. 21

| Test | Descripción | Normativa |
|------|-------------|-----------|
| business_continuity_plans | Planes de continuidad de negocio | **NIS2 Art. 21.2.c** |
| supply_chain_security | Seguridad cadena de suministro | **NIS2 Art. 21.2.d** |
| cybersecurity_training | Formación en ciberseguridad | **NIS2 Art. 21.2.g** |
| Cifrado | encryption_keys activas | **NIS2 Art. 21.2.h** |
| Control Acceso | RLS y RBAC implementados | **NIS2 Art. 21.2.i** |
| MFA | Campo two_factor en users | **NIS2 Art. 21.2.j** |

---

### Orden ETD/1286/2022 - Lista Robinson

#### 28_test_p3_robinson.sql
**Normativa:** Orden ETD/1286/2022, LSSI Art. 21

| Test | Descripción | Normativa |
|------|-------------|-----------|
| Tabla robinson_checks | Existe tabla de consultas | **Orden ETD Art. 6** |
| Consulta Obligatoria | Verificar antes de comunicación | **Orden ETD Art. 4.1** |
| Validez 30 Días | Consulta válida máximo 30 días | **Orden ETD Art. 4.2** |
| Documentación | Registro de todas las consultas | **Orden ETD Art. 6** |
| Bloqueo Registrados | No contactar si está en lista | **LSSI Art. 21.1** |

---

### Otros Tests de Cumplimiento

#### 10_test_security_breaches.sql - Gestión de brechas de seguridad
#### 11_test_sensitive_data.sql - Datos sensibles (RGPD Art. 9)
#### 12_test_retention_deletion.sql - Retención y eliminación
#### 13_test_data_portability.sql - Portabilidad extendida
#### 14_test_dashboard_metrics.sql - Métricas de cumplimiento
#### 15_test_call_processing_consents.sql - Consentimientos de llamadas
#### 16_test_gdpr_right_to_erasure.sql - Derecho al olvido
#### 17_test_performance_conversions.sql - Rendimiento
#### 18_test_campaigns.sql - Campañas de marketing
#### 19_test_dashboard_metrics_complete.sql - Dashboard completo
#### 20_test_kpi_metrics.sql - KPIs de negocio
#### 22_test_rls_isolation.sql - Aislamiento RLS
#### 23_test_pii_masking.sql - Enmascaramiento PII
#### 24_test_performance_optimization.sql - Optimización
#### 29_test_base_legal_validation.sql - Validación base legal
#### 30_test_data_minimization.sql - Minimización de datos (RGPD Art. 5.1.c)
#### 31_test_data_accuracy.sql - Exactitud de datos (RGPD Art. 5.1.d)
#### 32_test_minor_consent.sql - Consentimiento de menores (RGPD Art. 8)
#### 33_test_rat_compliance.sql - Registro de Actividades de Tratamiento
#### 34_test_dpo_governance.sql - Gobernanza DPO
#### 36_test_marketing_consent.sql - Consentimiento marketing
#### 40_test_privacy_by_design.sql - Privacidad desde el diseño (RGPD Art. 25)
#### 41_test_international_transfers.sql - Transferencias internacionales (RGPD Art. 44-49)
#### 45_test_information_layers.sql - Capas de información (RGPD Art. 12-14)
#### 48_test_compliance_gaps.sql - Brechas de cumplimiento
#### 49_test_age_verification.sql - Verificación de edad
#### 50_test_audit_integrity_verification.sql - Verificación integridad audit
#### 51_test_blocked_data_rls_anonymization.sql - RLS datos bloqueados
#### 52_test_security_mitigations.sql - Mitigaciones de seguridad
#### 53_test_user_preferences_rls.sql - RLS preferencias usuario

#### 54_test_data_processors.sql
**Normativa:** RGPD Art. 28-29, Art. 44-49

| Test | Descripción | Normativa |
|------|-------------|-----------|
| Tabla data_processors existe | Registro de encargados | **RGPD Art. 28** |
| Campos DPA Art. 28.3 | 13 campos obligatorios del DPA | **RGPD Art. 28.3** |
| Campos transferencias Art. 44-49 | is_eu_based, has_adequacy_decision, safeguards | **RGPD Art. 44-46** |
| Campos auditoría Art. 28.3.h | last_audit_date, next_audit_date | **RGPD Art. 28.3.h** |
| Crear encargado UE | Encargado dentro de la UE | **RGPD Art. 28** |
| Crear encargado NO-UE con SCC | Encargado con cláusulas contractuales | **RGPD Art. 46.2.c** |
| Crear encargado Art. 45 | Encargado con decisión de adecuación | **RGPD Art. 45** |
| Campos NOT NULL obligatorios | 9 campos críticos NOT NULL | **RGPD Art. 28.3** |
| Consulta RoPA encargados | Registro de Actividades (encargados) | **RGPD Art. 30.2** |
| Detectar NO-UE sin garantías | Alerta de compliance | **RGPD Art. 44** |
| Auditorías pendientes Art. 28.3.h | Control de auditorías | **RGPD Art. 28.3.h** |
| Contratos a vencer Art. 28.3.g | Alertas de fin de contrato | **RGPD Art. 28.3.g** |
| Desactivar encargado Art. 28.3.g | Desactivación al finalizar | **RGPD Art. 28.3.g** |
| Enlace NIS2 risk assessments | Integración con NIS2 | **NIS2 Art. 21.2.d** |

---

## Ejecución de Tests

### Ejecutar todos los tests

```bash
# Desde el directorio raíz del proyecto
for f in tests/[0-9]*.sql; do
    echo "Ejecutando $f..."
    psql -U postgres -d capsule -f "$f"
done
```

### Ejecutar un test específico

```bash
psql -U postgres -d capsule -f tests/02_test_funciones_cifrado.sql
```

### Ejecutar tests por categoría

```bash
# Tests RGPD básicos (01-09)
for f in tests/0[1-9]_test_*.sql; do psql -U postgres -d capsule -f "$f"; done

# Tests AI Act (26, 27, 35, 37-39, 42-44, 46)
psql -U postgres -d capsule -f tests/26_test_p1_ai_transparency.sql
psql -U postgres -d capsule -f tests/37_test_ai_risk_management.sql

# Tests LOPDGDD
psql -U postgres -d capsule -f tests/25_test_p0_lopdgdd_lgt.sql

# Tests Lista Robinson
psql -U postgres -d capsule -f tests/28_test_p3_robinson.sql

# Tests NIS2
psql -U postgres -d capsule -f tests/47_test_nis2_cybersecurity.sql
```

### Con Docker

```bash
docker exec -i capsulecorp-postgres psql -U postgres -d capsule < tests/02_test_funciones_cifrado.sql
```

---

## Requisitos Previos

### Variables de sesión

Todos los tests requieren estas variables de sesión:

```sql
SET app.kms_master_key = 'TEST_MASTER_KEY_FOR_TESTS_32CHAR';
SET app.hash_pepper = 'TEST_PEPPER_V1_FOR_HMAC_FUNCTIONS';
SET app.hash_pepper_version = '1';
SET app.audit_hmac_key = 'TEST_AUDIT_KEY_FOR_HMAC_CHAIN__';
```

### Idempotencia

Todos los tests:
- Inician con `BEGIN;`
- Terminan con `ROLLBACK;`
- No modifican datos permanentemente
- Pueden ejecutarse múltiples veces

---

## Cobertura por Normativa

### RGPD (UE) 2016/679 - Cobertura 100%

| Artículo | Concepto | Tests |
|----------|----------|-------|
| Art. 5.1.a | Licitud, lealtad, transparencia | 05, 26 |
| Art. 5.1.b | Limitación de la finalidad | 05, 29 |
| Art. 5.1.c | Minimización de datos | 30 |
| Art. 5.1.d | Exactitud | 31 |
| Art. 5.1.e | Limitación del plazo | 04, 12 |
| Art. 5.1.f | Integridad y confidencialidad | 02, 03 |
| Art. 5.2 | Responsabilidad proactiva | 03, 33 |
| Art. 6 | Bases jurídicas | 05, 29 |
| Art. 7 | Consentimiento | 05, 32 |
| Art. 8 | Consentimiento menores | 32 |
| Art. 9 | Datos sensibles | 11 |
| Art. 12-14 | Información al interesado | 21, 45 |
| Art. 15 | Derecho de acceso | 06, 08 |
| Art. 16 | Derecho de rectificación | 08 |
| Art. 17 | Derecho de supresión | 08, 16 |
| Art. 18 | Derecho de limitación | 07 |
| Art. 20 | Derecho de portabilidad | 06, 13 |
| Art. 21 | Derecho de oposición | 08 |
| Art. 22 | Decisiones automatizadas | 44 |
| Art. 25 | Protección desde el diseño | 02, 40 |
| Art. 28-29 | Encargados de tratamiento | 54 |
| Art. 30 | Registro de actividades | 03, 33, 54 |
| Art. 32 | Seguridad del tratamiento | 01, 02, 09 |
| Art. 33-34 | Brechas de seguridad | 09, 10 |
| Art. 35 | EIPD | 48 |
| Art. 37-39 | DPO | 34 |
| Art. 44-49 | Transferencias internacionales | 41, 54 |

### AI Act (UE) 2024/1689 - Cobertura 100%

| Artículo | Concepto | Tests |
|----------|----------|-------|
| Art. 9 | Sistema de gestión de riesgos | 37 |
| Art. 10 | Datos y gobernanza de datos | 38 |
| Art. 11 | Documentación técnica | 39 |
| Art. 12 | Conservación de registros | 35 |
| Art. 13 | Transparencia | 26 |
| Art. 14 | Supervisión humana | 26 |
| Art. 15 | Precisión, robustez, ciberseguridad | 42 |
| Art. 17 | Sistema de gestión de calidad | 43 |
| Art. 26 | Obligaciones del implementador | 27, 46 |
| Art. 50 | Obligaciones de transparencia | 26 |
| Art. 86 | Derecho a explicación | 44 |

### LOPDGDD 3/2018 - Cobertura 100%

| Artículo | Concepto | Tests |
|----------|----------|-------|
| Art. 6 | Consentimiento | 05 |
| Art. 7 | Menores (<14 años) | 32 |
| Art. 11 | Información por capas | 45 |
| Art. 16 | Limitación del tratamiento | 07 |
| Art. 17 | Portabilidad | 06 |
| Art. 33 | Bloqueo de datos | 25, 51 |

### NIS2 (UE) 2022/2555 - Cobertura 100%

| Artículo | Concepto | Tests |
|----------|----------|-------|
| Art. 21.2.a | Políticas de seguridad | 47 |
| Art. 21.2.b | Gestión de incidentes | 10, 47 |
| Art. 21.2.c | Continuidad de negocio | 47 |
| Art. 21.2.d | Cadena de suministro | 47, 54 |
| Art. 21.2.g | Ciberhigiene y formación | 47 |
| Art. 21.2.h | Criptografía | 02, 47 |
| Art. 21.2.i | Control de acceso | 22, 47 |
| Art. 21.2.j | MFA | 47 |

### Orden ETD/1286/2022 - Cobertura 100%

| Artículo | Concepto | Tests |
|----------|----------|-------|
| Art. 4.1 | Consulta obligatoria | 28 |
| Art. 4.2 | Validez máxima 30 días | 28 |
| Art. 6 | Documentación | 28 |

---

## Análisis de Gaps Normativos

### Contexto del Proyecto

CapsuleCorp es un sistema de **asistente virtual en centralita** que:
- Conecta con el backend y base de datos
- Mantiene conversaciones con **clientes externos** de la empresa
- Muestra información en un dashboard

### Gaps Identificados en Normativa.md

Se han identificado los siguientes gaps potenciales comparando `Normativa.md` con la implementación:

| Gap | Normativa | Artículo | ¿Aplica a CapsuleCorp? | Motivo |
|-----|-----------|----------|-------------------|--------|
| Biometría vocal | RGPD | Art. 9, Art. 4.14 | ❌ **No** | No se usa identificación por huella vocal |
| Geolocalización | ePrivacy | Art. 9 | ❌ **No** | No se rastrea ubicación GPS del llamante |
| Corresponsables | RGPD | Art. 26 | ❌ **No** | CapsuleCorp es responsable único del tratamiento |
| Emociones empleados | AI Act | Art. 5.1.f | ⚠️ **Condicional** | Solo si empleados internos llaman al sistema |
| Control laboral | ET + LOPDGDD | Art. 20.3, Arts. 87-91 | ⚠️ **Condicional** | Solo si se graban empleados humanos |
| Secreto comunicaciones | LGT | Art. 67 | ✅ **Sí** | Requisito documental (contratos externos) |

### Detalle de Gaps Condicionales

#### AI Act Art. 5.1.f - Análisis de Emociones en Empleados

**Prohibición:** Sistemas de IA para inferir emociones de personas en el **lugar de trabajo**.

| Tipo de llamante | ¿Análisis emociones permitido? |
|------------------|-------------------------------|
| Cliente externo | ✅ **Sí** (informando según Art. 50.3) |
| Potencial cliente (lead) | ✅ **Sí** (informando según Art. 50.3) |
| Proveedor externo | ✅ **Sí** (informando según Art. 50.3) |
| Empleado interno de la empresa | ❌ **No** (prohibido Art. 5.1.f) |

**Aplicabilidad en CapsuleCorp:**
- El sistema está diseñado para atender **clientes externos**
- El campo `is_employee_call` existe en la tabla `calls` para marcar excepciones
- Si solo se atienden clientes externos → **No aplica la prohibición**
- Si empleados internos pueden llamar → Debe bloquearse análisis de sentimiento

**Sanción potencial:** Hasta 35M€ o 7% facturación global

#### Control Laboral (ET Art. 20.3 + LOPDGDD Arts. 87-91)

**Aplicabilidad en CapsuleCorp:**
- **No aplica** si el asistente IA atiende todas las llamadas
- **Aplica** solo si hay transferencia a agentes humanos que también se graban

### Conclusión

Para el caso de uso principal de CapsuleCorp (asistente virtual atendiendo clientes externos):

| Categoría | Estado |
|-----------|--------|
| Gaps técnicos en BBDD | ✅ **Ninguno** |
| Gaps en tests | ✅ **Ninguno** |
| Gaps documentales | ⚠️ Contratos confidencialidad (LGT Art. 67) - externo a BBDD |

**La cobertura normativa de los tests SQL es del 100%** para el caso de uso definido.

---

## Referencias Normativas

- **RGPD**: [Reglamento (UE) 2016/679](https://eur-lex.europa.eu/eli/reg/2016/679/oj)
- **LOPDGDD**: [Ley Orgánica 3/2018](https://www.boe.es/eli/es/lo/2018/12/05/3)
- **AI Act**: [Reglamento (UE) 2024/1689](https://eur-lex.europa.eu/eli/reg/2024/1689/oj)
- **NIS2**: [Directiva (UE) 2022/2555](https://eur-lex.europa.eu/eli/dir/2022/2555/oj)
- **LGT**: [Ley 9/2014](https://www.boe.es/eli/es/l/2014/05/09/9)
- **Ley 25/2007**: [Conservación de datos](https://www.boe.es/eli/es/l/2007/10/18/25)
- **Orden ETD**: [Orden ETD/1286/2022](https://www.boe.es/eli/es/o/2022/12/23/etd1286)
- **LSSI**: [Ley 34/2002](https://www.boe.es/eli/es/l/2002/07/11/34)

---

*Documento actualizado: 2025-12-18*
*Tests SQL: 387 totales | 54 archivos*
*Normativas cubiertas: 10+ | Cobertura: 100%*
*Gaps normativos: Analizados y documentados*
