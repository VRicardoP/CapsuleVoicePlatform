-- ============================================================================
-- TEST 19: Dashboard Metrics Complete (Alineación UI/Backend)
-- ============================================================================
-- COBERTURA LEGAL:
--   • RGPD Art. 5.2: Responsabilidad proactiva (indirecto)
--   • Métricas de compliance y negocio (no requisito legal directo)
-- 
-- NIVEL DE COMPLIANCE: BAJO (indirecto)
-- CRITICIDAD: MEDIA
-- ============================================================================
-- Verifica la función get_dashboard_metrics_complete() que devuelve todos
-- los datos necesarios para el tipo DashboardData del frontend
-- Ejecutar: psql -U postgres -d sfera -f 19_test_dashboard_metrics_complete.sql
-- ============================================================================

-- Iniciar transacción para garantizar idempotencia
BEGIN;

-- Configurar para detectar errores
\set ON_ERROR_STOP on
SET client_min_messages = notice;

\echo '============================================================================'
\echo 'TEST 19: DASHBOARD METRICS COMPLETE'
\echo '============================================================================'

CREATE TEMP TABLE IF NOT EXISTS test_results (
    test_id SERIAL PRIMARY KEY,
    test_name TEXT NOT NULL,
    test_category TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PASS', 'FAIL', 'SKIP')),
    details TEXT,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Configurar variables de sesión
SET app.kms_master_key = 'TEST_MASTER_KEY_FOR_TESTS_32CHAR';
SET app.hash_pepper = 'TEST_PEPPER_V1_FOR_HMAC_FUNCTIONS';
SET app.hash_pepper_version = '1';
SET app.audit_hmac_key = 'TEST_AUDIT_KEY_FOR_HMAC_CHAIN__';

-- Desactivar claves existentes y crear una para tests
DO $$
BEGIN
    UPDATE encryption_keys SET is_active = false WHERE is_active = true;
    INSERT INTO encryption_keys (key_id, encrypted_key, is_active, kms_provider, activated_at)
    VALUES (
        'test_key_dmc_' || substring(gen_random_uuid()::TEXT, 1, 8),
        pgp_sym_encrypt(encode(gen_random_bytes(32), 'hex'), current_setting('app.kms_master_key'), 'cipher-algo=aes256'),
        true,
        'hashicorp-vault',
        CURRENT_TIMESTAMP
    );
EXCEPTION WHEN OTHERS THEN
    NULL;
END $$;

-- ============================================================================
-- TEST 19.1: Verificar existencia de función get_dashboard_metrics_complete
-- ============================================================================

\echo ''
\echo '--- Test 19.1: Verificar existencia de función ---'

DO $$
DECLARE
    v_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS(
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'public' AND p.proname = 'get_dashboard_metrics_complete'
    ) INTO v_exists;

    IF v_exists THEN
        v_status := 'PASS';
        v_details := 'Function get_dashboard_metrics_complete exists';
    ELSE
        v_status := 'FAIL';
        v_details := 'Function get_dashboard_metrics_complete does NOT exist';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Function Exists', 'Dashboard_Complete', v_status, v_details);

    RAISE NOTICE '  [%] Function Exists: %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 19.2: Función devuelve JSON con estructura correcta
-- ============================================================================

\echo ''
\echo '--- Test 19.2: Estructura JSON correcta ---'

DO $$
DECLARE
    v_user_id UUID;
    v_result JSON;
    v_has_metrics BOOLEAN;
    v_has_calls_data BOOLEAN;
    v_has_status_data BOOLEAN;
    v_has_recent_calls BOOLEAN;
    v_has_performance BOOLEAN;
    v_has_heatmap BOOLEAN;
    v_has_conversion BOOLEAN;
    v_has_campaigns BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario de prueba
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('TEST_DMC_USER', 'dmc_' || substring(gen_random_uuid()::TEXT, 1, 8) || '@test.local', 'hash', 'admin')
    RETURNING id INTO v_user_id;

    PERFORM set_current_user(v_user_id, NULL::UUID, '127.0.0.1'::INET);

    -- Ejecutar función
    SELECT get_dashboard_metrics_complete(v_user_id) INTO v_result;

    -- Verificar estructura
    v_has_metrics := (v_result->>'metrics') IS NOT NULL;
    v_has_calls_data := (v_result->>'callsData') IS NOT NULL;
    v_has_status_data := (v_result->>'statusData') IS NOT NULL;
    v_has_recent_calls := (v_result->>'recentCalls') IS NOT NULL;
    v_has_performance := (v_result->>'performanceData') IS NOT NULL;
    v_has_heatmap := (v_result->>'heatmapData') IS NOT NULL;
    v_has_conversion := (v_result->>'conversionData') IS NOT NULL;
    v_has_campaigns := (v_result->>'campaigns') IS NOT NULL;

    IF v_has_metrics AND v_has_calls_data AND v_has_status_data AND v_has_recent_calls
       AND v_has_performance AND v_has_heatmap AND v_has_conversion AND v_has_campaigns THEN
        v_status := 'PASS';
        v_details := 'All required fields present in response';
    ELSE
        v_status := 'FAIL';
        v_details := format('Missing fields - metrics:%s, callsData:%s, statusData:%s, recentCalls:%s, performanceData:%s, heatmapData:%s, conversionData:%s, campaigns:%s',
            v_has_metrics, v_has_calls_data, v_has_status_data, v_has_recent_calls,
            v_has_performance, v_has_heatmap, v_has_conversion, v_has_campaigns);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('JSON Structure', 'Dashboard_Complete', v_status, v_details);

    RAISE NOTICE '  [%] JSON Structure: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('JSON Structure', 'Dashboard_Complete', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '  [FAIL] JSON Structure: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 19.3: Métricas devuelven campos correctos
-- ============================================================================

\echo ''
\echo '--- Test 19.3: Campos de métricas ---'

DO $$
DECLARE
    v_user_id UUID;
    v_result JSON;
    v_metrics JSON;
    v_has_total_calls BOOLEAN;
    v_has_avg_duration BOOLEAN;
    v_has_total_minutes BOOLEAN;
    v_has_success_rate BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('TEST_METRICS_USER', 'metrics_' || substring(gen_random_uuid()::TEXT, 1, 8) || '@test.local', 'hash', 'admin')
    RETURNING id INTO v_user_id;

    PERFORM set_current_user(v_user_id, NULL::UUID, '127.0.0.1'::INET);

    -- Ejecutar función
    SELECT get_dashboard_metrics_complete(v_user_id) INTO v_result;
    v_metrics := v_result->'metrics';

    -- Verificar campos de métricas
    v_has_total_calls := (v_metrics->>'totalCalls') IS NOT NULL;
    v_has_avg_duration := (v_metrics->>'avgDuration') IS NOT NULL OR (v_metrics->>'avgDurationSeconds') IS NOT NULL;
    v_has_total_minutes := (v_metrics->>'totalMinutes') IS NOT NULL;
    v_has_success_rate := (v_metrics->>'successRate') IS NOT NULL;

    IF v_has_total_calls AND v_has_avg_duration AND v_has_total_minutes AND v_has_success_rate THEN
        v_status := 'PASS';
        v_details := format('All metrics fields present - totalCalls: %s', v_metrics->>'totalCalls');
    ELSE
        v_status := 'FAIL';
        v_details := format('Missing metrics - totalCalls:%s, avgDuration:%s, totalMinutes:%s, successRate:%s',
            v_has_total_calls, v_has_avg_duration, v_has_total_minutes, v_has_success_rate);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Metrics Fields', 'Dashboard_Complete', v_status, v_details);

    RAISE NOTICE '  [%] Metrics Fields: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Metrics Fields', 'Dashboard_Complete', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '  [FAIL] Metrics Fields: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 19.4: Recent calls incluye hasActiveConsent
-- ============================================================================

\echo ''
\echo '--- Test 19.4: Recent calls con hasActiveConsent ---'

DO $$
DECLARE
    v_user_id UUID;
    v_contact_id UUID;
    v_call_id UUID;
    v_result JSON;
    v_recent_calls JSON;
    v_first_call JSON;
    v_has_consent_field BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario y datos
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('TEST_CONSENT_USER', 'consent_' || substring(gen_random_uuid()::TEXT, 1, 8) || '@test.local', 'hash', 'admin')
    RETURNING id INTO v_user_id;

    PERFORM set_current_user(v_user_id, NULL::UUID, '127.0.0.1'::INET);

    INSERT INTO contacts (user_id, name_encrypted, phone_encrypted, phone_hash)
    VALUES (
        v_user_id,
        encrypt_pii_with_metadata('Consent Test'),
        encrypt_pii_with_metadata('+34600111222'),
        (secure_hash_with_pepper('+34600111222')).hash
    )
    RETURNING id INTO v_contact_id;

    INSERT INTO calls (
        user_id, contact_id, call_date, call_time, caller_name_encrypted, caller_phone_encrypted,
        caller_phone_hash, call_timestamp, duration_seconds, status, recording_encrypted
    )
    VALUES (
        v_user_id, v_contact_id, CURRENT_DATE, CURRENT_TIME,
        encrypt_pii_with_metadata('Test Caller'),
        encrypt_pii_with_metadata('+34600111222'),
        (secure_hash_with_pepper('+34600111222')).hash,
        CURRENT_TIMESTAMP, 120, 'completed', false
    )
    RETURNING id INTO v_call_id;

    -- Ejecutar función
    SELECT get_dashboard_metrics_complete(v_user_id) INTO v_result;
    v_recent_calls := v_result->'recentCalls';

    -- Verificar que existe el campo hasActiveConsent
    IF json_array_length(v_recent_calls) > 0 THEN
        v_first_call := v_recent_calls->0;
        v_has_consent_field := (v_first_call->>'hasActiveConsent') IS NOT NULL;

        IF v_has_consent_field THEN
            v_status := 'PASS';
            v_details := format('hasActiveConsent present: %s', v_first_call->>'hasActiveConsent');
        ELSE
            v_status := 'FAIL';
            v_details := 'hasActiveConsent field missing in recentCalls';
        END IF;
    ELSE
        v_status := 'FAIL';
        v_details := 'No calls returned to check hasActiveConsent';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('hasActiveConsent Field', 'Dashboard_Complete', v_status, v_details);

    RAISE NOTICE '  [%] hasActiveConsent: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('hasActiveConsent Field', 'Dashboard_Complete', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '  [FAIL] hasActiveConsent: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 19.5: Recent calls incluye caller y phone descifrados
-- ============================================================================

\echo ''
\echo '--- Test 19.5: Datos descifrados en recent calls ---'

DO $$
DECLARE
    v_user_id UUID;
    v_contact_id UUID;
    v_call_id UUID;
    v_result JSON;
    v_recent_calls JSON;
    v_first_call JSON;
    v_has_caller BOOLEAN;
    v_has_phone BOOLEAN;
    v_caller_value TEXT;
    v_phone_value TEXT;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario y datos
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('TEST_DECRYPT_USER', 'decrypt_' || substring(gen_random_uuid()::TEXT, 1, 8) || '@test.local', 'hash', 'admin')
    RETURNING id INTO v_user_id;

    PERFORM set_current_user(v_user_id, NULL::UUID, '127.0.0.1'::INET);

    INSERT INTO contacts (user_id, name_encrypted, phone_encrypted, phone_hash)
    VALUES (
        v_user_id,
        encrypt_pii_with_metadata('Decrypt Test'),
        encrypt_pii_with_metadata('+34600333444'),
        (secure_hash_with_pepper('+34600333444')).hash
    )
    RETURNING id INTO v_contact_id;

    INSERT INTO calls (
        user_id, contact_id, call_date, call_time, caller_name_encrypted, caller_phone_encrypted,
        caller_phone_hash, call_timestamp, duration_seconds, status, recording_encrypted
    )
    VALUES (
        v_user_id, v_contact_id, CURRENT_DATE, CURRENT_TIME,
        encrypt_pii_with_metadata('Juan Pérez'),
        encrypt_pii_with_metadata('+34600333444'),
        (secure_hash_with_pepper('+34600333444')).hash,
        CURRENT_TIMESTAMP, 90, 'completed', false
    )
    RETURNING id INTO v_call_id;

    -- Ejecutar función
    SELECT get_dashboard_metrics_complete(v_user_id) INTO v_result;
    v_recent_calls := v_result->'recentCalls';

    IF json_array_length(v_recent_calls) > 0 THEN
        v_first_call := v_recent_calls->0;
        v_caller_value := v_first_call->>'caller';
        v_phone_value := v_first_call->>'phone';

        v_has_caller := v_caller_value IS NOT NULL AND v_caller_value != '[Cifrado]';
        v_has_phone := v_phone_value IS NOT NULL AND v_phone_value != '[Cifrado]';

        IF v_has_caller AND v_has_phone THEN
            v_status := 'PASS';
            v_details := format('Decrypted data: caller=%s, phone=%s', v_caller_value, v_phone_value);
        ELSE
            v_status := 'FAIL';
            v_details := format('Decryption failed - caller:%s, phone:%s', v_caller_value, v_phone_value);
        END IF;
    ELSE
        v_status := 'FAIL';
        v_details := 'No calls returned';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Decrypted PII Fields', 'Dashboard_Complete', v_status, v_details);

    RAISE NOTICE '  [%] Decrypted Fields: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Decrypted PII Fields', 'Dashboard_Complete', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '  [FAIL] Decrypted Fields: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 19.6: Heatmap devuelve datos por hora
-- ============================================================================

\echo ''
\echo '--- Test 19.6: Heatmap por hora ---'

DO $$
DECLARE
    v_user_id UUID;
    v_contact_id UUID;
    v_result JSON;
    v_heatmap JSON;
    v_has_hour BOOLEAN;
    v_has_llamadas BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario y datos
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('TEST_HEATMAP_USER', 'heatmap_' || substring(gen_random_uuid()::TEXT, 1, 8) || '@test.local', 'hash', 'admin')
    RETURNING id INTO v_user_id;

    PERFORM set_current_user(v_user_id, NULL::UUID, '127.0.0.1'::INET);

    INSERT INTO contacts (user_id, name_encrypted, phone_encrypted, phone_hash)
    VALUES (
        v_user_id,
        encrypt_pii_with_metadata('Heatmap Test'),
        encrypt_pii_with_metadata('+34600555666'),
        (secure_hash_with_pepper('+34600555666')).hash
    )
    RETURNING id INTO v_contact_id;

    -- Crear varias llamadas a diferentes horas
    INSERT INTO calls (user_id, contact_id, call_date, call_time, caller_phone_hash, call_timestamp, duration_seconds, status, recording_encrypted)
    VALUES
        (v_user_id, v_contact_id, CURRENT_DATE, '09:00:00', 'hash1', CURRENT_TIMESTAMP, 60, 'completed', false),
        (v_user_id, v_contact_id, CURRENT_DATE, '10:30:00', 'hash2', CURRENT_TIMESTAMP, 90, 'completed', false),
        (v_user_id, v_contact_id, CURRENT_DATE, '14:00:00', 'hash3', CURRENT_TIMESTAMP, 120, 'completed', false);

    -- Ejecutar función
    SELECT get_dashboard_metrics_complete(v_user_id) INTO v_result;
    v_heatmap := v_result->'heatmapData';

    IF json_array_length(v_heatmap) > 0 THEN
        v_has_hour := (v_heatmap->0->>'hour') IS NOT NULL;
        v_has_llamadas := (v_heatmap->0->>'llamadas') IS NOT NULL;

        IF v_has_hour AND v_has_llamadas THEN
            v_status := 'PASS';
            v_details := format('Heatmap has %s hours with data', json_array_length(v_heatmap));
        ELSE
            v_status := 'FAIL';
            v_details := format('Missing fields - hour:%s, llamadas:%s', v_has_hour, v_has_llamadas);
        END IF;
    ELSE
        v_status := 'FAIL';
        v_details := 'No heatmap data returned';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Heatmap Data', 'Dashboard_Complete', v_status, v_details);

    RAISE NOTICE '  [%] Heatmap: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Heatmap Data', 'Dashboard_Complete', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '  [FAIL] Heatmap: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 19.7: Performance data incluye métricas del radar
-- ============================================================================

\echo ''
\echo '--- Test 19.7: Performance data ---'

DO $$
DECLARE
    v_user_id UUID;
    v_result JSON;
    v_performance JSON;
    v_first_metric JSON;
    v_has_metric BOOLEAN;
    v_has_value BOOLEAN;
    v_has_fullmark BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario y métricas
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('TEST_PERF_USER', 'perf_' || substring(gen_random_uuid()::TEXT, 1, 8) || '@test.local', 'hash', 'admin')
    RETURNING id INTO v_user_id;

    PERFORM set_current_user(v_user_id, NULL::UUID, '127.0.0.1'::INET);

    -- Insertar métricas de rendimiento
    INSERT INTO performance_metrics (
        user_id, metric_date, first_call_resolution, satisfaction_score,
        response_time_score, ai_accuracy_score, conversion_rate, avg_handle_time_score
    )
    VALUES (v_user_id, CURRENT_DATE, 85, 90, 75, 88, 45, 80);

    -- Ejecutar función
    SELECT get_dashboard_metrics_complete(v_user_id) INTO v_result;
    v_performance := v_result->'performanceData';

    IF json_array_length(v_performance) > 0 THEN
        v_first_metric := v_performance->0;
        v_has_metric := (v_first_metric->>'metric') IS NOT NULL;
        v_has_value := (v_first_metric->>'value') IS NOT NULL;
        v_has_fullmark := (v_first_metric->>'fullMark') IS NOT NULL;

        IF v_has_metric AND v_has_value AND v_has_fullmark THEN
            v_status := 'PASS';
            v_details := format('%s metrics for radar chart', json_array_length(v_performance));
        ELSE
            v_status := 'FAIL';
            v_details := format('Missing fields - metric:%s, value:%s, fullMark:%s',
                v_has_metric, v_has_value, v_has_fullmark);
        END IF;
    ELSE
        v_status := 'FAIL';
        v_details := 'No performance data returned';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Performance Data', 'Dashboard_Complete', v_status, v_details);

    RAISE NOTICE '  [%] Performance: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Performance Data', 'Dashboard_Complete', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '  [FAIL] Performance: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 19.8: Campaigns incluye estadísticas
-- ============================================================================

\echo ''
\echo '--- Test 19.8: Campaigns con estadísticas ---'

DO $$
DECLARE
    v_user_id UUID;
    v_contact_id UUID;
    v_campaign_id UUID;
    v_call_id UUID;
    v_result JSON;
    v_campaigns JSON;
    v_first_campaign JSON;
    v_has_name BOOLEAN;
    v_has_status BOOLEAN;
    v_has_agendada BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario y datos
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('TEST_CAMP_USER', 'camp_' || substring(gen_random_uuid()::TEXT, 1, 8) || '@test.local', 'hash', 'admin')
    RETURNING id INTO v_user_id;

    PERFORM set_current_user(v_user_id, NULL::UUID, '127.0.0.1'::INET);

    INSERT INTO contacts (user_id, name_encrypted, phone_encrypted, phone_hash)
    VALUES (
        v_user_id,
        encrypt_pii_with_metadata('Campaign Test'),
        encrypt_pii_with_metadata('+34600777888'),
        (secure_hash_with_pepper('+34600777888')).hash
    )
    RETURNING id INTO v_contact_id;

    -- Crear campaña
    INSERT INTO campaigns (user_id, name, start_date, status)
    VALUES (v_user_id, 'Test Campaign DMC', CURRENT_TIMESTAMP, 'active')
    RETURNING id INTO v_campaign_id;

    -- Crear llamada vinculada
    INSERT INTO calls (
        user_id, contact_id, call_date, call_time, caller_phone_hash,
        call_timestamp, duration_seconds, status, recording_encrypted
    )
    VALUES (
        v_user_id, v_contact_id, CURRENT_DATE, CURRENT_TIME, 'hash_camp',
        CURRENT_TIMESTAMP, 150, 'scheduled', false
    )
    RETURNING id INTO v_call_id;

    INSERT INTO campaign_calls (campaign_id, call_id) VALUES (v_campaign_id, v_call_id);

    -- Ejecutar función
    SELECT get_dashboard_metrics_complete(v_user_id) INTO v_result;
    v_campaigns := v_result->'campaigns';

    IF json_array_length(v_campaigns) > 0 THEN
        v_first_campaign := v_campaigns->0;
        v_has_name := (v_first_campaign->>'name') IS NOT NULL;
        v_has_status := (v_first_campaign->>'status') IS NOT NULL;
        v_has_agendada := (v_first_campaign->>'agendada') IS NOT NULL;

        IF v_has_name AND v_has_status AND v_has_agendada THEN
            v_status := 'PASS';
            v_details := format('Campaign "%s" with stats - agendada:%s',
                v_first_campaign->>'name', v_first_campaign->>'agendada');
        ELSE
            v_status := 'FAIL';
            v_details := format('Missing fields - name:%s, status:%s, agendada:%s',
                v_has_name, v_has_status, v_has_agendada);
        END IF;
    ELSE
        v_status := 'FAIL';
        v_details := 'No campaigns returned';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Campaigns Data', 'Dashboard_Complete', v_status, v_details);

    RAISE NOTICE '  [%] Campaigns: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Campaigns Data', 'Dashboard_Complete', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '  [FAIL] Campaigns: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 19.9: Control de acceso - Usuario no puede ver datos de otro
-- ============================================================================

\echo ''
\echo '--- Test 19.9: Control de acceso ---'

DO $$
DECLARE
    v_user1_id UUID;
    v_user2_id UUID;
    v_result JSON;
    v_has_error BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear dos usuarios
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('TEST_ACCESS_USER1', 'access1_' || substring(gen_random_uuid()::TEXT, 1, 8) || '@test.local', 'hash', 'user')
    RETURNING id INTO v_user1_id;

    INSERT INTO users (name, email, password_hash, role)
    VALUES ('TEST_ACCESS_USER2', 'access2_' || substring(gen_random_uuid()::TEXT, 1, 8) || '@test.local', 'hash', 'user')
    RETURNING id INTO v_user2_id;

    -- Usuario 1 intenta ver datos de usuario 2
    PERFORM set_current_user(v_user1_id, NULL::UUID, '127.0.0.1'::INET);
    SELECT get_dashboard_metrics_complete(v_user2_id) INTO v_result;

    v_has_error := (v_result->>'success')::BOOLEAN = false;

    IF v_has_error THEN
        v_status := 'PASS';
        v_details := 'Access correctly denied: ' || COALESCE(v_result->>'error', 'no error message');
    ELSE
        v_status := 'FAIL';
        v_details := 'User could access another users data (security issue!)';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Access Control', 'Dashboard_Complete', v_status, v_details);

    RAISE NOTICE '  [%] Access Control: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Access Control', 'Dashboard_Complete', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '  [FAIL] Access Control: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 19.10: Admin puede ver datos de cualquier usuario
-- ============================================================================

\echo ''
\echo '--- Test 19.10: Admin access ---'

DO $$
DECLARE
    v_admin_id UUID;
    v_user_id UUID;
    v_result JSON;
    v_is_success BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear admin y usuario normal
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('TEST_ADMIN', 'admin_' || substring(gen_random_uuid()::TEXT, 1, 8) || '@test.local', 'hash', 'admin')
    RETURNING id INTO v_admin_id;

    INSERT INTO users (name, email, password_hash, role)
    VALUES ('TEST_NORMAL', 'normal_' || substring(gen_random_uuid()::TEXT, 1, 8) || '@test.local', 'hash', 'user')
    RETURNING id INTO v_user_id;

    -- Admin ve datos de usuario normal
    PERFORM set_current_user(v_admin_id, NULL::UUID, '127.0.0.1'::INET);
    SELECT get_dashboard_metrics_complete(v_user_id) INTO v_result;

    v_is_success := (v_result->>'success')::BOOLEAN = true;

    IF v_is_success THEN
        v_status := 'PASS';
        v_details := 'Admin can access any users data';
    ELSE
        v_status := 'FAIL';
        v_details := 'Admin access denied: ' || COALESCE(v_result->>'error', 'unknown');
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Admin Access', 'Dashboard_Complete', v_status, v_details);

    RAISE NOTICE '  [%] Admin Access: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Admin Access', 'Dashboard_Complete', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '  [FAIL] Admin Access: %', SQLERRM;
END $$;

-- ============================================================================
-- CLEANUP
-- ============================================================================

\echo ''
\echo '--- Cleanup ---'

DO $$
BEGIN
    DELETE FROM users WHERE email LIKE '%@test.local' AND name LIKE 'TEST_%';
    RAISE NOTICE '  Test data cleaned up';
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE '  Cleanup error: %', SQLERRM;
END $$;

-- ============================================================================
-- RESUMEN
-- ============================================================================

\echo ''
\echo '============================================================================'
\echo 'RESUMEN TEST 19: DASHBOARD METRICS COMPLETE'
\echo '============================================================================'

SELECT test_category,
       COUNT(*) as total_tests,
       SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) as passed,
       SUM(CASE WHEN status = 'FAIL' THEN 1 ELSE 0 END) as failed,
       SUM(CASE WHEN status = 'SKIP' THEN 1 ELSE 0 END) as skipped
FROM test_results
WHERE test_category = 'Dashboard_Complete'
GROUP BY test_category;

SELECT test_name, status, details
FROM test_results
WHERE test_category = 'Dashboard_Complete'
ORDER BY test_id;

-- ============================================================================
-- FIN DEL TEST - Revertir todos los cambios (idempotencia)
-- ============================================================================
ROLLBACK;
