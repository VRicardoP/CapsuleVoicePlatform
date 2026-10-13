-- ============================================================================
-- TEST 20: KPI METRICS (Punto 2 Auditoria)
-- ============================================================================
-- COBERTURA LEGAL:
--   • No verifica requisitos legales (KPIs de negocio)
-- 
-- NIVEL DE COMPLIANCE: N/A
-- CRITICIDAD: BAJA (técnico)
-- ============================================================================
-- Verifica la funcion get_kpi_metrics() que devuelve metricas avanzadas:
-- ROI, valor por llamada, leads calificados, tiempo de respuesta
-- Ejecutar: \i /path/to/20_test_kpi_metrics.sql

-- Iniciar transacción para garantizar idempotencia
BEGIN;

-- Configurar para detectar errores
\set ON_ERROR_STOP on
SET client_min_messages = notice;

CREATE TEMP TABLE IF NOT EXISTS test_results (
    test_id SERIAL PRIMARY KEY,
    test_name TEXT NOT NULL,
    test_category TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PASS', 'FAIL', 'SKIP')),
    details TEXT,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Configurar variables de sesion
SET app.kms_master_key = 'TEST_MASTER_KEY_FOR_TESTS_32CHAR';
SET app.hash_pepper = 'TEST_PEPPER_V1_FOR_HMAC_FUNCTIONS';
SET app.hash_pepper_version = '1';
SET app.audit_hmac_key = 'TEST_AUDIT_KEY_FOR_HMAC_CHAIN__';

-- Crear clave de cifrado temporal para tests
DO $$
BEGIN
    INSERT INTO encryption_keys (key_id, encrypted_key, is_active, kms_provider, activated_at)
    VALUES (
        'test_key_kpi_' || substring(gen_random_uuid()::TEXT, 1, 8),
        pgp_sym_encrypt(encode(gen_random_bytes(32), 'hex'), current_setting('app.kms_master_key'), 'cipher-algo=aes256'),
        true,
        'hashicorp-vault',
        CURRENT_TIMESTAMP
    );
EXCEPTION WHEN OTHERS THEN
    NULL;
END $$;

-- ============================================================================
-- TEST 20.1: Funcion get_kpi_metrics existe
-- ============================================================================

\echo ''
\echo '--- Test 20.1: Funcion get_kpi_metrics existe ---'

DO $$
DECLARE
    v_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS(
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'public' AND p.proname = 'get_kpi_metrics'
    ) INTO v_exists;

    IF v_exists THEN
        v_status := 'PASS';
        v_details := 'Function get_kpi_metrics exists';
    ELSE
        v_status := 'FAIL';
        v_details := 'Function get_kpi_metrics does not exist';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Function Exists', 'KPI_Metrics', v_status, v_details);

    RAISE NOTICE '  [%] Function Exists: %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 20.2: Estructura JSON correcta
-- ============================================================================

\echo ''
\echo '--- Test 20.2: Estructura JSON correcta ---'

DO $$
DECLARE
    v_user_id UUID;
    v_result JSON;
    v_has_success BOOLEAN;
    v_has_data BOOLEAN;
    v_has_kpis BOOLEAN;
    v_has_summary BOOLEAN;
    v_has_period BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario admin
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('KPI_TEST_USER', 'kpi_' || substring(gen_random_uuid()::TEXT, 1, 8) || '@test.local', 'hash', 'admin')
    RETURNING id INTO v_user_id;

    -- Configurar usuario actual
    PERFORM set_current_user(v_user_id, NULL::UUID, '127.0.0.1'::INET);

    -- Ejecutar funcion
    SELECT get_kpi_metrics(v_user_id) INTO v_result;

    -- Verificar estructura
    v_has_success := (v_result->>'success') IS NOT NULL;
    v_has_data := (v_result->'data') IS NOT NULL;
    v_has_kpis := (v_result->'data'->'kpis') IS NOT NULL;
    v_has_summary := (v_result->'data'->'summary') IS NOT NULL;
    v_has_period := (v_result->'data'->'period') IS NOT NULL;

    IF v_has_success AND v_has_data AND v_has_kpis AND v_has_summary AND v_has_period THEN
        v_status := 'PASS';
        v_details := 'All required JSON fields present (success, data, kpis, summary, period)';
    ELSE
        v_status := 'FAIL';
        v_details := format('Missing fields - success:%s, data:%s, kpis:%s, summary:%s, period:%s',
            v_has_success, v_has_data, v_has_kpis, v_has_summary, v_has_period);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('JSON Structure', 'KPI_Metrics', v_status, v_details);

    RAISE NOTICE '  [%] JSON Structure: %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 20.3: Campos KPI presentes
-- ============================================================================

\echo ''
\echo '--- Test 20.3: Campos KPI presentes ---'

DO $$
DECLARE
    v_user_id UUID;
    v_result JSON;
    v_kpis JSON;
    v_has_roi BOOLEAN;
    v_has_savings BOOLEAN;
    v_has_avg_value BOOLEAN;
    v_has_leads BOOLEAN;
    v_has_response BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario admin
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('KPI_FIELDS_USER', 'kpi_fields_' || substring(gen_random_uuid()::TEXT, 1, 8) || '@test.local', 'hash', 'admin')
    RETURNING id INTO v_user_id;

    PERFORM set_current_user(v_user_id, NULL::UUID, '127.0.0.1'::INET);

    SELECT get_kpi_metrics(v_user_id) INTO v_result;
    v_kpis := v_result->'data'->'kpis';

    -- Verificar campos KPI
    v_has_roi := (v_kpis->>'roiPercentage') IS NOT NULL AND (v_kpis->>'roiLabel') IS NOT NULL;
    v_has_savings := (v_kpis->>'estimatedSavings') IS NOT NULL AND (v_kpis->>'estimatedSavingsFormatted') IS NOT NULL;
    v_has_avg_value := (v_kpis->>'avgValuePerCall') IS NOT NULL AND (v_kpis->>'avgValuePerCallFormatted') IS NOT NULL;
    v_has_leads := (v_kpis->>'qualifiedLeads') IS NOT NULL AND (v_kpis->>'conversionRate') IS NOT NULL;
    v_has_response := (v_kpis->>'avgResponseTimeScore') IS NOT NULL AND (v_kpis->>'callsUnder2sPct') IS NOT NULL;

    IF v_has_roi AND v_has_savings AND v_has_avg_value AND v_has_leads AND v_has_response THEN
        v_status := 'PASS';
        v_details := format('All KPI fields present - ROI:%s, Savings:%s, AvgValue:%s',
            v_kpis->>'roiLabel', v_kpis->>'estimatedSavingsFormatted', v_kpis->>'avgValuePerCallFormatted');
    ELSE
        v_status := 'FAIL';
        v_details := format('Missing KPI fields - roi:%s, savings:%s, avgValue:%s, leads:%s, response:%s',
            v_has_roi, v_has_savings, v_has_avg_value, v_has_leads, v_has_response);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('KPI Fields Present', 'KPI_Metrics', v_status, v_details);

    RAISE NOTICE '  [%] KPI Fields: %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 20.4: Calculo de ROI con datos reales
-- ============================================================================

\echo ''
\echo '--- Test 20.4: Calculo de ROI con datos reales ---'

DO $$
DECLARE
    v_user_id UUID;
    v_contact_id UUID;
    v_call_id UUID;
    v_result JSON;
    v_roi NUMERIC;
    v_savings NUMERIC;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario admin
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('KPI_ROI_USER', 'kpi_roi_' || substring(gen_random_uuid()::TEXT, 1, 8) || '@test.local', 'hash', 'admin')
    RETURNING id INTO v_user_id;

    -- Crear contacto
    INSERT INTO contacts (user_id, name_encrypted, phone_encrypted, phone_hash)
    VALUES (
        v_user_id,
        encrypt_pii_with_metadata('ROI Test'),
        encrypt_pii_with_metadata('+34600999111'),
        (secure_hash_with_pepper('+34600999111')).hash
    )
    RETURNING id INTO v_contact_id;

    -- Crear llamada con valor y costo
    INSERT INTO calls (
        user_id, contact_id, call_date, call_time, caller_name_encrypted, caller_phone_encrypted,
        caller_phone_hash, call_timestamp, duration_seconds, status, recording_encrypted,
        call_value, call_cost
    )
    VALUES (
        v_user_id, v_contact_id, CURRENT_DATE, CURRENT_TIME,
        encrypt_pii_with_metadata('ROI Test'),
        encrypt_pii_with_metadata('+34600999111'),
        (secure_hash_with_pepper('+34600999111')).hash,
        CURRENT_TIMESTAMP, 300, 'completed', false,
        500.00, 10.00
    )
    RETURNING id INTO v_call_id;

    -- Crear conversion
    INSERT INTO conversions (call_id, user_id, conversion_date, conversion_value, conversion_type)
    VALUES (v_call_id, v_user_id, CURRENT_DATE, 1000.00, 'sale');

    PERFORM set_current_user(v_user_id, NULL::UUID, '127.0.0.1'::INET);

    SELECT get_kpi_metrics(v_user_id) INTO v_result;

    v_roi := (v_result->'data'->'kpis'->>'roiPercentage')::NUMERIC;
    v_savings := (v_result->'data'->'kpis'->>'estimatedSavings')::NUMERIC;

    -- ROI = ((1000 - 10) / 10) * 100 = 9900%
    -- Savings = (300/60) * 0.50 = 2.50
    IF v_roi > 0 AND v_savings > 0 THEN
        v_status := 'PASS';
        v_details := format('ROI calculated: %s%%, Savings: EUR %s', v_roi, v_savings);
    ELSE
        v_status := 'FAIL';
        v_details := format('Invalid ROI calculation - ROI:%s, Savings:%s', v_roi, v_savings);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('ROI Calculation', 'KPI_Metrics', v_status, v_details);

    RAISE NOTICE '  [%] ROI Calculation: %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 20.5: Leads calificados
-- ============================================================================

\echo ''
\echo '--- Test 20.5: Leads calificados ---'

DO $$
DECLARE
    v_user_id UUID;
    v_contact_id UUID;
    v_call_id UUID;
    v_result JSON;
    v_leads INTEGER;
    v_conversion_rate NUMERIC;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario admin
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('KPI_LEADS_USER', 'kpi_leads_' || substring(gen_random_uuid()::TEXT, 1, 8) || '@test.local', 'hash', 'admin')
    RETURNING id INTO v_user_id;

    -- Crear contacto
    INSERT INTO contacts (user_id, name_encrypted, phone_encrypted, phone_hash)
    VALUES (
        v_user_id,
        encrypt_pii_with_metadata('Leads Test'),
        encrypt_pii_with_metadata('+34600999222'),
        (secure_hash_with_pepper('+34600999222')).hash
    )
    RETURNING id INTO v_contact_id;

    -- Crear 3 llamadas, 1 con conversion (33.3% tasa)
    FOR i IN 1..3 LOOP
        INSERT INTO calls (
            user_id, contact_id, call_date, call_time, caller_name_encrypted, caller_phone_encrypted,
            caller_phone_hash, call_timestamp, duration_seconds, status, recording_encrypted
        )
        VALUES (
            v_user_id, v_contact_id, CURRENT_DATE, CURRENT_TIME,
            encrypt_pii_with_metadata('Leads Test ' || i),
            encrypt_pii_with_metadata('+34600999222'),
            (secure_hash_with_pepper('+34600999222')).hash,
            CURRENT_TIMESTAMP, 120, 'completed', false
        )
        RETURNING id INTO v_call_id;

        -- Solo la primera llamada tiene conversion
        IF i = 1 THEN
            INSERT INTO conversions (call_id, user_id, conversion_date, conversion_value, conversion_type)
            VALUES (v_call_id, v_user_id, CURRENT_DATE, 500.00, 'lead');
        END IF;
    END LOOP;

    PERFORM set_current_user(v_user_id, NULL::UUID, '127.0.0.1'::INET);

    SELECT get_kpi_metrics(v_user_id) INTO v_result;

    v_leads := (v_result->'data'->'kpis'->>'qualifiedLeads')::INTEGER;
    v_conversion_rate := (v_result->'data'->'kpis'->>'conversionRate')::NUMERIC;

    IF v_leads = 1 AND v_conversion_rate > 30 AND v_conversion_rate < 35 THEN
        v_status := 'PASS';
        v_details := format('Leads: %s, Conversion rate: %s%%', v_leads, v_conversion_rate);
    ELSE
        v_status := 'FAIL';
        v_details := format('Unexpected values - Leads:%s (expected 1), Rate:%s%% (expected ~33.3%%)', v_leads, v_conversion_rate);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Qualified Leads', 'KPI_Metrics', v_status, v_details);

    RAISE NOTICE '  [%] Qualified Leads: %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 20.6: Control de acceso - Usuario normal
-- ============================================================================

\echo ''
\echo '--- Test 20.6: Control de acceso ---'

DO $$
DECLARE
    v_admin_id UUID;
    v_normal_user_id UUID;
    v_result JSON;
    v_access_denied BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario admin
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('KPI_ADMIN', 'kpi_admin_' || substring(gen_random_uuid()::TEXT, 1, 8) || '@test.local', 'hash', 'admin')
    RETURNING id INTO v_admin_id;

    -- Crear usuario normal
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('KPI_NORMAL', 'kpi_normal_' || substring(gen_random_uuid()::TEXT, 1, 8) || '@test.local', 'hash', 'user')
    RETURNING id INTO v_normal_user_id;

    -- Usuario normal intenta acceder a datos del admin
    PERFORM set_current_user(v_normal_user_id, NULL::UUID, '127.0.0.1'::INET);

    SELECT get_kpi_metrics(v_admin_id) INTO v_result;

    v_access_denied := (v_result->>'success')::BOOLEAN = false AND
                       (v_result->>'error') LIKE '%Access denied%';

    IF v_access_denied THEN
        v_status := 'PASS';
        v_details := 'Access correctly denied: ' || (v_result->>'error');
    ELSE
        v_status := 'FAIL';
        v_details := 'Access should have been denied for normal user accessing other users data';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Access Control', 'KPI_Metrics', v_status, v_details);

    RAISE NOTICE '  [%] Access Control: %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 20.7: Admin puede acceder a cualquier usuario
-- ============================================================================

\echo ''
\echo '--- Test 20.7: Admin acceso total ---'

DO $$
DECLARE
    v_admin_id UUID;
    v_other_user_id UUID;
    v_result JSON;
    v_success BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear admin
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('KPI_SUPER_ADMIN', 'kpi_sadmin_' || substring(gen_random_uuid()::TEXT, 1, 8) || '@test.local', 'hash', 'admin')
    RETURNING id INTO v_admin_id;

    -- Crear otro usuario
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('KPI_OTHER', 'kpi_other_' || substring(gen_random_uuid()::TEXT, 1, 8) || '@test.local', 'hash', 'user')
    RETURNING id INTO v_other_user_id;

    -- Admin accede a datos de otro usuario
    PERFORM set_current_user(v_admin_id, NULL::UUID, '127.0.0.1'::INET);

    SELECT get_kpi_metrics(v_other_user_id) INTO v_result;

    v_success := (v_result->>'success')::BOOLEAN = true;

    IF v_success THEN
        v_status := 'PASS';
        v_details := 'Admin can access any users KPI data';
    ELSE
        v_status := 'FAIL';
        v_details := 'Admin should be able to access any users data: ' || COALESCE(v_result->>'error', 'no error');
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Admin Access', 'KPI_Metrics', v_status, v_details);

    RAISE NOTICE '  [%] Admin Access: %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 20.8: Summary fields presentes
-- ============================================================================

\echo ''
\echo '--- Test 20.8: Summary fields ---'

DO $$
DECLARE
    v_user_id UUID;
    v_result JSON;
    v_summary JSON;
    v_has_calls BOOLEAN;
    v_has_duration BOOLEAN;
    v_has_handle_time BOOLEAN;
    v_has_period BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('KPI_SUMMARY_USER', 'kpi_summary_' || substring(gen_random_uuid()::TEXT, 1, 8) || '@test.local', 'hash', 'admin')
    RETURNING id INTO v_user_id;

    PERFORM set_current_user(v_user_id, NULL::UUID, '127.0.0.1'::INET);

    SELECT get_kpi_metrics(v_user_id) INTO v_result;
    v_summary := v_result->'data'->'summary';

    v_has_calls := (v_summary->>'totalCalls') IS NOT NULL;
    v_has_duration := (v_summary->>'totalDurationMinutes') IS NOT NULL;
    v_has_handle_time := (v_summary->>'avgHandleTimeSeconds') IS NOT NULL;
    v_has_period := (v_summary->>'periodDays') IS NOT NULL;

    IF v_has_calls AND v_has_duration AND v_has_handle_time AND v_has_period THEN
        v_status := 'PASS';
        v_details := format('Summary: calls=%s, duration=%s min, handle=%s s, period=%s days',
            v_summary->>'totalCalls', v_summary->>'totalDurationMinutes',
            v_summary->>'avgHandleTimeSeconds', v_summary->>'periodDays');
    ELSE
        v_status := 'FAIL';
        v_details := format('Missing summary fields - calls:%s, duration:%s, handle:%s, period:%s',
            v_has_calls, v_has_duration, v_has_handle_time, v_has_period);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Summary Fields', 'KPI_Metrics', v_status, v_details);

    RAISE NOTICE '  [%] Summary Fields: %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 20.9: Filtro de fechas funciona
-- ============================================================================

\echo ''
\echo '--- Test 20.9: Filtro de fechas ---'

DO $$
DECLARE
    v_user_id UUID;
    v_result JSON;
    v_period JSON;
    v_start_date DATE;
    v_end_date DATE;
    v_status TEXT;
    v_details TEXT;
BEGIN
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('KPI_DATE_USER', 'kpi_date_' || substring(gen_random_uuid()::TEXT, 1, 8) || '@test.local', 'hash', 'admin')
    RETURNING id INTO v_user_id;

    PERFORM set_current_user(v_user_id, NULL::UUID, '127.0.0.1'::INET);

    -- Llamar con fechas especificas
    SELECT get_kpi_metrics(v_user_id, CURRENT_DATE - 7, CURRENT_DATE) INTO v_result;
    v_period := v_result->'data'->'period';

    v_start_date := (v_period->>'startDate')::DATE;
    v_end_date := (v_period->>'endDate')::DATE;

    IF v_start_date = CURRENT_DATE - 7 AND v_end_date = CURRENT_DATE THEN
        v_status := 'PASS';
        v_details := format('Date filter works: %s to %s', v_start_date, v_end_date);
    ELSE
        v_status := 'FAIL';
        v_details := format('Date filter failed - expected %s to %s, got %s to %s',
            CURRENT_DATE - 7, CURRENT_DATE, v_start_date, v_end_date);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Date Filter', 'KPI_Metrics', v_status, v_details);

    RAISE NOTICE '  [%] Date Filter: %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 20.10: Performance metrics integration
-- ============================================================================

\echo ''
\echo '--- Test 20.10: Performance metrics integration ---'

DO $$
DECLARE
    v_user_id UUID;
    v_result JSON;
    v_response_time NUMERIC;
    v_status TEXT;
    v_details TEXT;
BEGIN
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('KPI_PERF_USER', 'kpi_perf_' || substring(gen_random_uuid()::TEXT, 1, 8) || '@test.local', 'hash', 'admin')
    RETURNING id INTO v_user_id;

    -- Insertar metricas de performance
    INSERT INTO performance_metrics (user_id, metric_date, response_time_score, satisfaction_score)
    VALUES (v_user_id, CURRENT_DATE, 85, 90);

    PERFORM set_current_user(v_user_id, NULL::UUID, '127.0.0.1'::INET);

    SELECT get_kpi_metrics(v_user_id) INTO v_result;

    v_response_time := (v_result->'data'->'kpis'->>'avgResponseTimeScore')::NUMERIC;

    IF v_response_time = 85 THEN
        v_status := 'PASS';
        v_details := format('Performance metrics integrated: response_time_score=%s', v_response_time);
    ELSE
        v_status := 'FAIL';
        v_details := format('Performance metrics not integrated - expected 85, got %s', v_response_time);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Performance Integration', 'KPI_Metrics', v_status, v_details);

    RAISE NOTICE '  [%] Performance Integration: %', v_status, v_details;
END $$;

-- ============================================================================
-- RESUMEN DE RESULTADOS
-- ============================================================================

\echo ''
\echo '============================================================================'
\echo 'RESUMEN TEST 20: KPI METRICS'
\echo '============================================================================'

SELECT
    test_category,
    COUNT(*) as total_tests,
    COUNT(*) FILTER (WHERE status = 'PASS') as passed,
    COUNT(*) FILTER (WHERE status = 'FAIL') as failed,
    COUNT(*) FILTER (WHERE status = 'SKIP') as skipped
FROM test_results
WHERE test_category = 'KPI_Metrics'
GROUP BY test_category;

SELECT test_name, status, details
FROM test_results
WHERE test_category = 'KPI_Metrics'
ORDER BY test_id;

-- ============================================================================
-- FIN DEL TEST - Revertir todos los cambios (idempotencia)
-- ============================================================================
ROLLBACK;
