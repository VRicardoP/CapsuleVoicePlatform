-- ============================================================================
-- TEST 14: Dashboard Metrics RGPD (Art. 5, 24 - Responsabilidad Proactiva)
-- ============================================================================
-- COBERTURA LEGAL:
--   • RGPD Art. 5.2: Responsabilidad proactiva (métricas compliance)
--   • RGPD Art. 24.1: Medidas técnicas y organizativas (monitorización)
--   • Indirecta: métr icas de negocio no son requisito legal directo
-- 
-- NIVEL DE COMPLIANCE: BAJO (indirecto)
-- CRITICIDAD: MEDIA
-- REQUISITOS NORMATIVA.MD: N/A directo
-- ============================================================================
-- Verifica las vistas y funciones de métricas del dashboard RGPD
-- Incluye tests para:
--   - Vistas especializadas de cumplimiento
--   - Función get_dashboard_metrics_gdpr()
--   - Función get_gdpr_executive_summary()
--   - Función get_gdpr_trends()
--   - Control de acceso basado en roles
-- ============================================================================

-- Iniciar transacción para garantizar idempotencia
BEGIN;

-- Configurar para detectar errores
\set ON_ERROR_STOP on
SET client_min_messages = notice;

\echo '============================================================================'
\echo 'TEST 14: Dashboard Metrics RGPD'
\echo '============================================================================'
\echo ''

-- Crear tabla de resultados si no existe
CREATE TABLE IF NOT EXISTS test_results (
    id SERIAL PRIMARY KEY,
    test_name VARCHAR(200) NOT NULL,
    test_category VARCHAR(50) NOT NULL,
    status VARCHAR(10) NOT NULL CHECK (status IN ('PASS', 'FAIL', 'SKIP')),
    details TEXT,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Limpiar resultados anteriores de esta categoría
DELETE FROM test_results WHERE test_category = 'Dashboard_Metrics';

-- Configurar variables de sesión para tests
SET app.kms_master_key = 'TEST_MASTER_KEY_FOR_TESTS_32CHAR';
SET app.hash_pepper = 'TEST_PEPPER_V1_FOR_HMAC_FUNCTIONS';
SET app.hash_pepper_version = '1';
SET app.audit_hmac_key = 'TEST_AUDIT_KEY_FOR_HMAC_CHAIN_32';

-- Variables de test
DO $$ BEGIN PERFORM set_config('test.admin_user_id', '', false); END $$;
DO $$ BEGIN PERFORM set_config('test.dpo_user_id', '', false); END $$;
DO $$ BEGIN PERFORM set_config('test.normal_user_id', '', false); END $$;

-- ============================================================================
-- SETUP: Crear usuarios de prueba
-- ============================================================================

\echo 'Setup: Creando usuarios de prueba...'

DO $$
DECLARE
    v_admin_id UUID;
    v_dpo_id UUID;
    v_normal_id UUID;
BEGIN
    -- Crear usuario admin de prueba
    INSERT INTO users (name, email, password_hash, password_algorithm, role, is_active)
    VALUES (
        'TEST_DASHBOARD_ADMIN',
        'test_dashboard_admin_' || gen_random_uuid()::TEXT || '@test.local',
        'test_hash',
        'bcrypt',
        'admin',
        true
    )
    RETURNING id INTO v_admin_id;

    PERFORM set_config('test.admin_user_id', v_admin_id::TEXT, false);

    -- Crear usuario Auditor de prueba (rol con permisos GDPR)
    INSERT INTO users (name, email, password_hash, password_algorithm, role, is_active)
    VALUES (
        'TEST_DASHBOARD_AUDITOR',
        'test_dashboard_auditor_' || gen_random_uuid()::TEXT || '@test.local',
        'test_hash',
        'bcrypt',
        'auditor',
        true
    )
    RETURNING id INTO v_dpo_id;

    PERFORM set_config('test.dpo_user_id', v_dpo_id::TEXT, false);

    -- Crear usuario normal de prueba
    INSERT INTO users (name, email, password_hash, password_algorithm, role, is_active)
    VALUES (
        'TEST_DASHBOARD_USER',
        'test_dashboard_user_' || gen_random_uuid()::TEXT || '@test.local',
        'test_hash',
        'bcrypt',
        'user',
        true
    )
    RETURNING id INTO v_normal_id;

    PERFORM set_config('test.normal_user_id', v_normal_id::TEXT, false);

    -- Establecer contexto de admin
    PERFORM set_current_user(v_admin_id, NULL::UUID, '127.0.0.1'::INET);

    RAISE NOTICE 'Setup: Usuarios creados - Admin: %, DPO: %, Normal: %', v_admin_id, v_dpo_id, v_normal_id;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Setup FAILED: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 14.1: Verificar existencia de vista v_gdpr_compliance_summary
-- ============================================================================

\echo '  [TEST 14.1] Verificar existencia de vista v_gdpr_compliance_summary'

DO $$
DECLARE
    v_exists BOOLEAN;
    v_status VARCHAR(10);
    v_details TEXT;
BEGIN
    SELECT EXISTS(
        SELECT 1 FROM information_schema.views
        WHERE table_schema = 'public' AND table_name = 'v_gdpr_compliance_summary'
    ) INTO v_exists;

    IF v_exists THEN
        v_status := 'PASS';
        v_details := 'Vista v_gdpr_compliance_summary existe';
    ELSE
        v_status := 'FAIL';
        v_details := 'Vista v_gdpr_compliance_summary NO existe';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Vista v_gdpr_compliance_summary existe', 'Dashboard_Metrics', v_status, v_details);

    RAISE NOTICE '    [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 14.2: Verificar existencia de vista v_pending_requests
-- ============================================================================

\echo '  [TEST 14.2] Verificar existencia de vista v_pending_requests'

DO $$
DECLARE
    v_exists BOOLEAN;
    v_status VARCHAR(10);
    v_details TEXT;
BEGIN
    SELECT EXISTS(
        SELECT 1 FROM information_schema.views
        WHERE table_schema = 'public' AND table_name = 'v_pending_requests'
    ) INTO v_exists;

    IF v_exists THEN
        v_status := 'PASS';
        v_details := 'Vista v_pending_requests existe';
    ELSE
        v_status := 'FAIL';
        v_details := 'Vista v_pending_requests NO existe';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Vista v_pending_requests existe', 'Dashboard_Metrics', v_status, v_details);

    RAISE NOTICE '    [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 14.3: Verificar existencia de vista v_breach_alerts
-- ============================================================================

\echo '  [TEST 14.3] Verificar existencia de vista v_breach_alerts'

DO $$
DECLARE
    v_exists BOOLEAN;
    v_status VARCHAR(10);
    v_details TEXT;
BEGIN
    SELECT EXISTS(
        SELECT 1 FROM information_schema.views
        WHERE table_schema = 'public' AND table_name = 'v_breach_alerts'
    ) INTO v_exists;

    IF v_exists THEN
        v_status := 'PASS';
        v_details := 'Vista v_breach_alerts existe';
    ELSE
        v_status := 'FAIL';
        v_details := 'Vista v_breach_alerts NO existe';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Vista v_breach_alerts existe', 'Dashboard_Metrics', v_status, v_details);

    RAISE NOTICE '    [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 14.4: Verificar existencia de vista v_consent_status
-- ============================================================================

\echo '  [TEST 14.4] Verificar existencia de vista v_consent_status'

DO $$
DECLARE
    v_exists BOOLEAN;
    v_status VARCHAR(10);
    v_details TEXT;
BEGIN
    SELECT EXISTS(
        SELECT 1 FROM information_schema.views
        WHERE table_schema = 'public' AND table_name = 'v_consent_status'
    ) INTO v_exists;

    IF v_exists THEN
        v_status := 'PASS';
        v_details := 'Vista v_consent_status existe';
    ELSE
        v_status := 'FAIL';
        v_details := 'Vista v_consent_status NO existe';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Vista v_consent_status existe', 'Dashboard_Metrics', v_status, v_details);

    RAISE NOTICE '    [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 14.5: Verificar existencia de vista v_retention_alerts
-- ============================================================================

\echo '  [TEST 14.5] Verificar existencia de vista v_retention_alerts'

DO $$
DECLARE
    v_exists BOOLEAN;
    v_status VARCHAR(10);
    v_details TEXT;
BEGIN
    SELECT EXISTS(
        SELECT 1 FROM information_schema.views
        WHERE table_schema = 'public' AND table_name = 'v_retention_alerts'
    ) INTO v_exists;

    IF v_exists THEN
        v_status := 'PASS';
        v_details := 'Vista v_retention_alerts existe';
    ELSE
        v_status := 'FAIL';
        v_details := 'Vista v_retention_alerts NO existe';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Vista v_retention_alerts existe', 'Dashboard_Metrics', v_status, v_details);

    RAISE NOTICE '    [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 14.6: Verificar existencia de vista v_recent_audit_activity
-- ============================================================================

\echo '  [TEST 14.6] Verificar existencia de vista v_recent_audit_activity'

DO $$
DECLARE
    v_exists BOOLEAN;
    v_status VARCHAR(10);
    v_details TEXT;
BEGIN
    SELECT EXISTS(
        SELECT 1 FROM information_schema.views
        WHERE table_schema = 'public' AND table_name = 'v_recent_audit_activity'
    ) INTO v_exists;

    IF v_exists THEN
        v_status := 'PASS';
        v_details := 'Vista v_recent_audit_activity existe';
    ELSE
        v_status := 'FAIL';
        v_details := 'Vista v_recent_audit_activity NO existe';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Vista v_recent_audit_activity existe', 'Dashboard_Metrics', v_status, v_details);

    RAISE NOTICE '    [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 14.7: Verificar existencia de función get_dashboard_metrics_gdpr
-- ============================================================================

\echo '  [TEST 14.7] Verificar existencia de función get_dashboard_metrics_gdpr'

DO $$
DECLARE
    v_exists BOOLEAN;
    v_status VARCHAR(10);
    v_details TEXT;
BEGIN
    SELECT EXISTS(
        SELECT 1 FROM information_schema.routines
        WHERE routine_schema = 'public'
        AND routine_name = 'get_dashboard_metrics_gdpr'
        AND routine_type = 'FUNCTION'
    ) INTO v_exists;

    IF v_exists THEN
        v_status := 'PASS';
        v_details := 'Función get_dashboard_metrics_gdpr existe';
    ELSE
        v_status := 'FAIL';
        v_details := 'Función get_dashboard_metrics_gdpr NO existe';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Función get_dashboard_metrics_gdpr existe', 'Dashboard_Metrics', v_status, v_details);

    RAISE NOTICE '    [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 14.8: Verificar existencia de función get_gdpr_executive_summary
-- ============================================================================

\echo '  [TEST 14.8] Verificar existencia de función get_gdpr_executive_summary'

DO $$
DECLARE
    v_exists BOOLEAN;
    v_status VARCHAR(10);
    v_details TEXT;
BEGIN
    SELECT EXISTS(
        SELECT 1 FROM information_schema.routines
        WHERE routine_schema = 'public'
        AND routine_name = 'get_gdpr_executive_summary'
        AND routine_type = 'FUNCTION'
    ) INTO v_exists;

    IF v_exists THEN
        v_status := 'PASS';
        v_details := 'Función get_gdpr_executive_summary existe';
    ELSE
        v_status := 'FAIL';
        v_details := 'Función get_gdpr_executive_summary NO existe';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Función get_gdpr_executive_summary existe', 'Dashboard_Metrics', v_status, v_details);

    RAISE NOTICE '    [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 14.9: Verificar existencia de función get_gdpr_trends
-- ============================================================================

\echo '  [TEST 14.9] Verificar existencia de función get_gdpr_trends'

DO $$
DECLARE
    v_exists BOOLEAN;
    v_status VARCHAR(10);
    v_details TEXT;
BEGIN
    SELECT EXISTS(
        SELECT 1 FROM information_schema.routines
        WHERE routine_schema = 'public'
        AND routine_name = 'get_gdpr_trends'
        AND routine_type = 'FUNCTION'
    ) INTO v_exists;

    IF v_exists THEN
        v_status := 'PASS';
        v_details := 'Función get_gdpr_trends existe';
    ELSE
        v_status := 'FAIL';
        v_details := 'Función get_gdpr_trends NO existe';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Función get_gdpr_trends existe', 'Dashboard_Metrics', v_status, v_details);

    RAISE NOTICE '    [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 14.10: Vista v_gdpr_compliance_summary retorna datos correctos
-- ============================================================================

\echo '  [TEST 14.10] Vista v_gdpr_compliance_summary retorna datos correctos'

DO $$
DECLARE
    v_record RECORD;
    v_status VARCHAR(10);
    v_details TEXT;
BEGIN
    SELECT * INTO v_record FROM v_gdpr_compliance_summary LIMIT 1;

    IF v_record IS NOT NULL
       AND v_record.active_consents IS NOT NULL
       AND v_record.pending_deletion_requests IS NOT NULL
       AND v_record.pending_exports IS NOT NULL
       AND v_record.active_breaches IS NOT NULL
       AND v_record.generated_at IS NOT NULL
    THEN
        v_status := 'PASS';
        v_details := format('Consents: %s, Deletions: %s, Exports: %s, Breaches: %s',
            v_record.active_consents, v_record.pending_deletion_requests,
            v_record.pending_exports, v_record.active_breaches);
    ELSE
        v_status := 'FAIL';
        v_details := 'Vista no retorna campos esperados';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Vista compliance_summary retorna datos', 'Dashboard_Metrics', v_status, v_details);

    RAISE NOTICE '    [%] %', v_status, v_details;
EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Vista compliance_summary retorna datos', 'Dashboard_Metrics', 'FAIL', 'Error: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Error: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 14.11: Función get_dashboard_metrics_gdpr retorna JSON válido (Admin)
-- ============================================================================

\echo '  [TEST 14.11] Función get_dashboard_metrics_gdpr retorna JSON válido (Admin)'

DO $$
DECLARE
    v_admin_id UUID;
    v_result JSON;
    v_status VARCHAR(10);
    v_details TEXT;
BEGIN
    v_admin_id := current_setting('test.admin_user_id')::UUID;
    PERFORM set_current_user(v_admin_id, NULL::UUID, '127.0.0.1'::INET);

    SELECT get_dashboard_metrics_gdpr(
        p_user_id := v_admin_id,
        p_include_calls := true,
        p_include_gdpr := true
    ) INTO v_result;

    -- La función devuelve directamente el objeto con callMetrics, gdprCompliance, metadata, etc.
    IF v_result IS NOT NULL
       AND v_result->'gdprCompliance' IS NOT NULL
       AND v_result->'metadata' IS NOT NULL
       AND (v_result->'metadata'->>'includesGdpr')::BOOLEAN = true
    THEN
        v_status := 'PASS';
        v_details := 'Admin puede obtener métricas GDPR completas';
    ELSE
        v_status := 'FAIL';
        v_details := 'Resultado incompleto o sin métricas GDPR';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('get_dashboard_metrics_gdpr (Admin)', 'Dashboard_Metrics', v_status, v_details);

    RAISE NOTICE '    [%] %', v_status, v_details;
EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('get_dashboard_metrics_gdpr (Admin)', 'Dashboard_Metrics', 'FAIL', 'Error: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Error: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 14.12: Función get_dashboard_metrics_gdpr retorna JSON válido (Auditor)
-- ============================================================================

\echo '  [TEST 14.12] Función get_dashboard_metrics_gdpr retorna JSON válido (Auditor)'

DO $$
DECLARE
    v_auditor_id UUID;
    v_result JSON;
    v_status VARCHAR(10);
    v_details TEXT;
BEGIN
    v_auditor_id := current_setting('test.dpo_user_id')::UUID;
    PERFORM set_current_user(v_auditor_id, NULL::UUID, '127.0.0.1'::INET);

    SELECT get_dashboard_metrics_gdpr(
        p_user_id := v_auditor_id,
        p_include_calls := true,
        p_include_gdpr := true
    ) INTO v_result;

    -- La función devuelve directamente el objeto con callMetrics, gdprCompliance, metadata, etc.
    IF v_result IS NOT NULL
       AND v_result->'gdprCompliance' IS NOT NULL
       AND v_result->'metadata' IS NOT NULL
       AND (v_result->'metadata'->>'includesGdpr')::BOOLEAN = true
    THEN
        v_status := 'PASS';
        v_details := 'Auditor puede obtener métricas GDPR completas';
    ELSE
        v_status := 'FAIL';
        v_details := 'Resultado incompleto o sin métricas GDPR';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('get_dashboard_metrics_gdpr (Auditor)', 'Dashboard_Metrics', v_status, v_details);

    RAISE NOTICE '    [%] %', v_status, v_details;
EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('get_dashboard_metrics_gdpr (Auditor)', 'Dashboard_Metrics', 'FAIL', 'Error: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Error: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 14.13: Usuario normal NO recibe métricas GDPR
-- ============================================================================

\echo '  [TEST 14.13] Usuario normal NO recibe métricas GDPR'

DO $$
DECLARE
    v_normal_id UUID;
    v_result JSON;
    v_has_gdpr BOOLEAN;
    v_status VARCHAR(10);
    v_details TEXT;
BEGIN
    v_normal_id := current_setting('test.normal_user_id')::UUID;
    PERFORM set_current_user(v_normal_id, NULL::UUID, '127.0.0.1'::INET);

    SELECT get_dashboard_metrics_gdpr(
        p_user_id := v_normal_id,
        p_include_calls := true,
        p_include_gdpr := true
    ) INTO v_result;

    -- Usuario normal no debe recibir datos GDPR detallados (includesGdpr debe ser false)
    -- La función devuelve gdprCompliance vacío {} y metadata.includesGdpr = false
    v_has_gdpr := v_result IS NOT NULL
                  AND v_result->'metadata' IS NOT NULL
                  AND (v_result->'metadata'->>'includesGdpr')::BOOLEAN = true;

    IF NOT v_has_gdpr THEN
        v_status := 'PASS';
        v_details := 'Usuario normal NO recibe métricas GDPR (correcto)';
    ELSE
        v_status := 'FAIL';
        v_details := 'Usuario normal puede ver métricas GDPR (incorrecto)';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Usuario normal sin acceso GDPR', 'Dashboard_Metrics', v_status, v_details);

    RAISE NOTICE '    [%] %', v_status, v_details;
EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Usuario normal sin acceso GDPR', 'Dashboard_Metrics', 'FAIL', 'Error: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Error: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 14.14: Función get_gdpr_executive_summary retorna score de cumplimiento
-- ============================================================================

\echo '  [TEST 14.14] Función get_gdpr_executive_summary retorna score de cumplimiento'

DO $$
DECLARE
    v_admin_id UUID;
    v_result JSON;
    v_score INTEGER;
    v_status VARCHAR(10);
    v_details TEXT;
BEGIN
    v_admin_id := current_setting('test.admin_user_id')::UUID;
    PERFORM set_current_user(v_admin_id, NULL::UUID, '127.0.0.1'::INET);

    SELECT get_gdpr_executive_summary() INTO v_result;

    -- La función devuelve {success, complianceScore, complianceStatus, ...} directamente
    IF v_result IS NOT NULL
       AND (v_result->>'success')::BOOLEAN = true
       AND v_result->>'complianceScore' IS NOT NULL
    THEN
        v_score := (v_result->>'complianceScore')::INTEGER;

        IF v_score >= 0 AND v_score <= 100 THEN
            v_status := 'PASS';
            v_details := format('Score de cumplimiento: %s/100', v_score);
        ELSE
            v_status := 'FAIL';
            v_details := format('Score fuera de rango: %s', v_score);
        END IF;
    ELSE
        v_status := 'FAIL';
        v_details := 'No se pudo obtener score de cumplimiento: ' || COALESCE(v_result->>'error', 'desconocido');
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Executive summary con score', 'Dashboard_Metrics', v_status, v_details);

    RAISE NOTICE '    [%] %', v_status, v_details;
EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Executive summary con score', 'Dashboard_Metrics', 'FAIL', 'Error: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Error: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 14.15: Función get_gdpr_executive_summary retorna estado de cumplimiento
-- ============================================================================

\echo '  [TEST 14.15] Función get_gdpr_executive_summary retorna estado de cumplimiento'

DO $$
DECLARE
    v_admin_id UUID;
    v_result JSON;
    v_compliance_status TEXT;
    v_valid_statuses TEXT[] := ARRAY['excellent', 'good', 'needs_attention', 'critical'];
    v_status VARCHAR(10);
    v_details TEXT;
BEGIN
    v_admin_id := current_setting('test.admin_user_id')::UUID;
    PERFORM set_current_user(v_admin_id, NULL::UUID, '127.0.0.1'::INET);

    SELECT get_gdpr_executive_summary() INTO v_result;

    -- La función devuelve complianceStatus directamente en el objeto raíz
    v_compliance_status := v_result->>'complianceStatus';

    IF v_compliance_status = ANY(v_valid_statuses) THEN
        v_status := 'PASS';
        v_details := format('Estado de cumplimiento: %s', v_compliance_status);
    ELSE
        v_status := 'FAIL';
        v_details := format('Estado inválido: %s', COALESCE(v_compliance_status, 'NULL'));
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Executive summary con estado válido', 'Dashboard_Metrics', v_status, v_details);

    RAISE NOTICE '    [%] %', v_status, v_details;
EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Executive summary con estado válido', 'Dashboard_Metrics', 'FAIL', 'Error: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Error: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 14.16: Función get_gdpr_trends retorna datos de tendencias
-- ============================================================================

\echo '  [TEST 14.16] Función get_gdpr_trends retorna datos de tendencias'

DO $$
DECLARE
    v_admin_id UUID;
    v_result JSON;
    v_trends JSON;
    v_status VARCHAR(10);
    v_details TEXT;
BEGIN
    v_admin_id := current_setting('test.admin_user_id')::UUID;
    PERFORM set_current_user(v_admin_id, NULL::UUID, '127.0.0.1'::INET);

    SELECT get_gdpr_trends(7) INTO v_result;

    -- La función devuelve {success, period, trends} directamente
    IF v_result IS NOT NULL
       AND (v_result->>'success')::BOOLEAN = true
       AND v_result->'trends' IS NOT NULL
    THEN
        v_trends := v_result->'trends';
        v_status := 'PASS';
        v_details := format('Tendencias generadas para %s días',
            json_array_length(v_trends));
    ELSE
        v_status := 'FAIL';
        v_details := 'No se pudieron obtener tendencias: ' || COALESCE(v_result->>'error', 'desconocido');
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('get_gdpr_trends retorna datos', 'Dashboard_Metrics', v_status, v_details);

    RAISE NOTICE '    [%] %', v_status, v_details;
EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('get_gdpr_trends retorna datos', 'Dashboard_Metrics', 'FAIL', 'Error: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Error: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 14.17: Vista v_pending_requests muestra solicitudes ordenadas
-- ============================================================================

\echo '  [TEST 14.17] Vista v_pending_requests estructura correcta'

DO $$
DECLARE
    v_has_columns BOOLEAN;
    v_status VARCHAR(10);
    v_details TEXT;
BEGIN
    -- Verificar que la vista tiene las columnas esperadas
    SELECT EXISTS(
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'v_pending_requests'
        AND column_name IN ('request_type', 'request_id', 'priority', 'created_at')
        GROUP BY table_name
        HAVING COUNT(*) >= 4
    ) INTO v_has_columns;

    IF v_has_columns THEN
        v_status := 'PASS';
        v_details := 'Vista v_pending_requests tiene estructura correcta';
    ELSE
        v_status := 'FAIL';
        v_details := 'Vista v_pending_requests falta columnas requeridas';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Vista pending_requests estructura', 'Dashboard_Metrics', v_status, v_details);

    RAISE NOTICE '    [%] %', v_status, v_details;
EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Vista pending_requests estructura', 'Dashboard_Metrics', 'FAIL', 'Error: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Error: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 14.18: Vista v_breach_alerts calcula urgencia
-- ============================================================================

\echo '  [TEST 14.18] Vista v_breach_alerts estructura correcta'

DO $$
DECLARE
    v_has_columns BOOLEAN;
    v_status VARCHAR(10);
    v_details TEXT;
BEGIN
    -- Verificar columnas de urgencia
    SELECT EXISTS(
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'v_breach_alerts'
        AND column_name IN ('id', 'severity', 'status', 'hours_since_detection', 'urgency')
        GROUP BY table_name
        HAVING COUNT(*) >= 5
    ) INTO v_has_columns;

    IF v_has_columns THEN
        v_status := 'PASS';
        v_details := 'Vista v_breach_alerts tiene columnas de urgencia';
    ELSE
        v_status := 'FAIL';
        v_details := 'Vista v_breach_alerts falta columnas de urgencia';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Vista breach_alerts con urgencia', 'Dashboard_Metrics', v_status, v_details);

    RAISE NOTICE '    [%] %', v_status, v_details;
EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Vista breach_alerts con urgencia', 'Dashboard_Metrics', 'FAIL', 'Error: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Error: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 14.19: get_dashboard_metrics_gdpr con filtro de fechas
-- ============================================================================

\echo '  [TEST 14.19] get_dashboard_metrics_gdpr con filtro de fechas'

DO $$
DECLARE
    v_admin_id UUID;
    v_result JSON;
    v_status VARCHAR(10);
    v_details TEXT;
BEGIN
    v_admin_id := current_setting('test.admin_user_id')::UUID;
    PERFORM set_current_user(v_admin_id, NULL::UUID, '127.0.0.1'::INET);

    -- Llamar con rango de fechas específico
    SELECT get_dashboard_metrics_gdpr(
        p_user_id := v_admin_id,
        p_include_calls := true,
        p_include_gdpr := true,
        p_start_date := CURRENT_DATE - 7,
        p_end_date := CURRENT_DATE
    ) INTO v_result;

    -- La función devuelve objeto con metadata que contiene dateRange
    IF v_result IS NOT NULL
       AND v_result->'metadata' IS NOT NULL
       AND v_result->'metadata'->'dateRange' IS NOT NULL
    THEN
        v_status := 'PASS';
        v_details := format('Función acepta filtro de fechas: %s a %s',
            v_result->'metadata'->'dateRange'->>'start',
            v_result->'metadata'->'dateRange'->>'end');
    ELSE
        v_status := 'FAIL';
        v_details := 'Error con filtro de fechas';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Filtro de fechas funciona', 'Dashboard_Metrics', v_status, v_details);

    RAISE NOTICE '    [%] %', v_status, v_details;
EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Filtro de fechas funciona', 'Dashboard_Metrics', 'FAIL', 'Error: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Error: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 14.20: get_gdpr_executive_summary contiene resumen textual
-- ============================================================================

\echo '  [TEST 14.20] get_gdpr_executive_summary contiene resumen textual'

DO $$
DECLARE
    v_admin_id UUID;
    v_result JSON;
    v_summary JSON;
    v_status VARCHAR(10);
    v_details TEXT;
BEGIN
    v_admin_id := current_setting('test.admin_user_id')::UUID;
    PERFORM set_current_user(v_admin_id, NULL::UUID, '127.0.0.1'::INET);

    SELECT get_gdpr_executive_summary() INTO v_result;

    -- La función devuelve summary directamente en el objeto raíz
    v_summary := v_result->'summary';

    IF v_summary IS NOT NULL
       AND v_summary->>'pendingDeletions' IS NOT NULL
       AND v_summary->>'pendingExports' IS NOT NULL
       AND v_summary->>'activeBreaches' IS NOT NULL
    THEN
        v_status := 'PASS';
        v_details := format('Resumen: deletions=%s, exports=%s, breaches=%s',
            v_summary->>'pendingDeletions',
            v_summary->>'pendingExports',
            v_summary->>'activeBreaches');
    ELSE
        v_status := 'FAIL';
        v_details := 'Resumen incompleto o ausente: ' || COALESCE(v_result->>'error', 'desconocido');
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Executive summary con resumen', 'Dashboard_Metrics', v_status, v_details);

    RAISE NOTICE '    [%] %', v_status, v_details;
EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Executive summary con resumen', 'Dashboard_Metrics', 'FAIL', 'Error: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Error: %', SQLERRM;
END $$;

-- ============================================================================
-- CLEANUP: Eliminar datos de prueba
-- ============================================================================

\echo ''
\echo 'Cleanup: Eliminando datos de prueba...'

DO $$
DECLARE
    v_admin_id UUID;
    v_dpo_id UUID;
    v_normal_id UUID;
BEGIN
    v_admin_id := current_setting('test.admin_user_id', true)::UUID;
    v_dpo_id := current_setting('test.dpo_user_id', true)::UUID;
    v_normal_id := current_setting('test.normal_user_id', true)::UUID;

    -- Restablecer admin para limpieza
    IF v_admin_id IS NOT NULL THEN
        PERFORM set_current_user(v_admin_id, NULL::UUID, '127.0.0.1'::INET);
    END IF;

    -- Eliminar usuarios de prueba
    DELETE FROM users WHERE id IN (v_admin_id, v_dpo_id, v_normal_id);
    DELETE FROM users WHERE email LIKE 'test_dashboard_%@test.local';

    RAISE NOTICE '    Datos de prueba eliminados';
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE '    Error en cleanup: %', SQLERRM;
END $$;

-- ============================================================================
-- RESUMEN DE RESULTADOS
-- ============================================================================

\echo ''
\echo '============================================================================'
\echo 'RESUMEN DE RESULTADOS - Dashboard Metrics RGPD'
\echo '============================================================================'

SELECT
    status,
    COUNT(*) as total
FROM test_results
WHERE test_category = 'Dashboard_Metrics'
GROUP BY status
ORDER BY status;

\echo ''
\echo 'Detalle de tests:'
SELECT
    test_name,
    status,
    details
FROM test_results
WHERE test_category = 'Dashboard_Metrics'
ORDER BY id;

\echo ''
\echo '============================================================================'
\echo 'FIN DE TESTS - Dashboard Metrics RGPD'
\echo '============================================================================'

-- ============================================================================
-- FIN DEL TEST - Revertir todos los cambios (idempotencia)
-- ============================================================================
ROLLBACK;
